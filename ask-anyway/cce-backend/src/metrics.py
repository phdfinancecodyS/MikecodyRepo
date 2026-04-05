"""
Internal usage metrics for the CCE backend.
Thread-safe counters that accumulate in-memory and flush to a JSON log file.
Provides the data needed to know when regex sentiment is no longer sufficient
and LLM-backed classification should be activated.

Activate: always on (zero-cost counters).
View:     GET /admin/metrics (protected by ADMIN_KEY env var).
"""
import json
import os
import threading
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional


_lock = threading.Lock()

# ─── Counters ──────────────────────────────────────────────────────────────────

_counters: Dict[str, int] = defaultdict(int)
_daily: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
_sentiment_shadow: list = []  # LLM vs regex comparison log (capped)
_topic_shadow: list = []      # LLM vs regex topic comparison log (capped)
_unmatched_topics: list = []  # User inputs that matched no guide (demand tracking)
_llm_usage: list = []         # LLM token/cost telemetry (capped)
_SHADOW_CAP = 500
_UNMATCHED_CAP = 1000
_LLM_USAGE_CAP = 4000

# ─── Persistence ───────────────────────────────────────────────────────────────

_METRICS_DIR = Path(os.environ.get(
    "CCE_METRICS_DIR",
    Path(__file__).parent / "data" / ".metrics",
))
_METRICS_DIR.mkdir(parents=True, exist_ok=True)
_SNAPSHOT_PATH = _METRICS_DIR / "snapshot.json"
_boot_time = time.time()


def _today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


# ─── Public API ────────────────────────────────────────────────────────────────

def inc(name: str, amount: int = 1) -> None:
    """Increment a counter. Thread-safe, zero-allocation fast path."""
    with _lock:
        _counters[name] += amount
        _daily[_today()][name] += amount


def record_sentiment_shadow(
    text: str,
    regex_result: str,
    llm_result: Optional[str],
) -> None:
    """Log a regex-vs-LLM sentiment comparison for shadow analysis."""
    with _lock:
        if len(_sentiment_shadow) >= _SHADOW_CAP:
            _sentiment_shadow.pop(0)
        _sentiment_shadow.append({
            "ts": datetime.now(timezone.utc).isoformat(),
            "text": text[:200],
            "regex": regex_result,
            "llm": llm_result,
            "match": regex_result == llm_result if llm_result else None,
        })


def record_topic_shadow(
    text: str,
    regex_topics: list,
    llm_topics: Optional[list],
) -> None:
    """Log a regex-vs-LLM topic match comparison for shadow analysis."""
    with _lock:
        if len(_topic_shadow) >= _SHADOW_CAP:
            _topic_shadow.pop(0)
        # Compare: do the top matches agree?
        regex_top = regex_topics[0] if regex_topics else "none"
        llm_top = llm_topics[0] if llm_topics else "none"
        _topic_shadow.append({
            "ts": datetime.now(timezone.utc).isoformat(),
            "text": text[:200],
            "regex": regex_topics[:3],
            "llm": llm_topics[:3] if llm_topics else None,
            "top_match": regex_top == llm_top if llm_topics else None,
        })


def record_unmatched_topic(text: str, regex_fallback: str) -> None:
    """Log user input that didn't match any specific guide. Demand tracking."""
    with _lock:
        if len(_unmatched_topics) >= _UNMATCHED_CAP:
            _unmatched_topics.pop(0)
        _unmatched_topics.append({
            "ts": datetime.now(timezone.utc).isoformat(),
            "text": text[:300],
            "regex_fallback": regex_fallback,
        })


def record_llm_usage(
    provider: str,
    model: str,
    prompt_tokens: int,
    completion_tokens: int,
    lane: str,
    source: str,
) -> None:
    """Record LLM token usage for observability and cost estimation.

    lane: responder|sentiment|topic|meds|other
    source: primary|fallback|cache|shadow
    """
    with _lock:
        if len(_llm_usage) >= _LLM_USAGE_CAP:
            _llm_usage.pop(0)
        _llm_usage.append({
            "ts": datetime.now(timezone.utc).isoformat(),
            "provider": provider,
            "model": model,
            "prompt_tokens": max(int(prompt_tokens or 0), 0),
            "completion_tokens": max(int(completion_tokens or 0), 0),
            "total_tokens": max(int((prompt_tokens or 0) + (completion_tokens or 0)), 0),
            "lane": lane,
            "source": source,
        })


def _llm_usage_snapshot_unlocked() -> Dict[str, Any]:
    """Return a focused LLM usage/cost summary."""
    today = _today()
    in_per_m = float(os.environ.get("CCE_LLM_COST_INPUT_PER_1M", "0") or 0)
    out_per_m = float(os.environ.get("CCE_LLM_COST_OUTPUT_PER_1M", "0") or 0)

    all_prompt = sum(x["prompt_tokens"] for x in _llm_usage)
    all_completion = sum(x["completion_tokens"] for x in _llm_usage)
    all_total = all_prompt + all_completion

    today_rows = [x for x in _llm_usage if x["ts"].startswith(today)]
    today_prompt = sum(x["prompt_tokens"] for x in today_rows)
    today_completion = sum(x["completion_tokens"] for x in today_rows)
    today_total = today_prompt + today_completion

    est_all = ((all_prompt / 1_000_000) * in_per_m) + ((all_completion / 1_000_000) * out_per_m)
    est_today = ((today_prompt / 1_000_000) * in_per_m) + ((today_completion / 1_000_000) * out_per_m)

    by_provider: Dict[str, Dict[str, int]] = {}
    for row in _llm_usage:
        p = row["provider"]
        if p not in by_provider:
            by_provider[p] = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0, "calls": 0}
        by_provider[p]["prompt_tokens"] += row["prompt_tokens"]
        by_provider[p]["completion_tokens"] += row["completion_tokens"]
        by_provider[p]["total_tokens"] += row["total_tokens"]
        by_provider[p]["calls"] += 1

    return {
        "pricing": {
            "input_per_1m_tokens_usd": in_per_m,
            "output_per_1m_tokens_usd": out_per_m,
        },
        "totals": {
            "prompt_tokens": all_prompt,
            "completion_tokens": all_completion,
            "total_tokens": all_total,
            "estimated_cost_usd": round(est_all, 6),
            "calls": len(_llm_usage),
        },
        "today": {
            "date": today,
            "prompt_tokens": today_prompt,
            "completion_tokens": today_completion,
            "total_tokens": today_total,
            "estimated_cost_usd": round(est_today, 6),
            "calls": len(today_rows),
        },
        "by_provider": by_provider,
        "recent": _llm_usage[-30:],
    }


def llm_usage_snapshot() -> Dict[str, Any]:
    with _lock:
        return _llm_usage_snapshot_unlocked()


def _llm_tokens_in_window_unlocked(window_s: int, now_ts: float) -> int:
    cutoff = now_ts - window_s
    total = 0
    for row in _llm_usage:
        ts_raw = row.get("ts")
        if not ts_raw:
            continue
        try:
            ts = datetime.fromisoformat(ts_raw).timestamp()
        except Exception:
            continue
        if ts >= cutoff:
            total += int(row.get("total_tokens", 0) or 0)
    return total


def _headroom_level(pct_used: Optional[float]) -> str:
    if pct_used is None:
        return "disabled"
    if pct_used >= 100.0:
        return "critical"
    if pct_used >= 90.0:
        return "warning"
    if pct_used >= 75.0:
        return "watch"
    return "ok"


def llm_headroom_snapshot() -> Dict[str, Any]:
    """Return current LLM token budget headroom and warning levels."""
    with _lock:
        now_ts = time.time()

        cap_min = int(os.environ.get("CCE_LLM_BUDGET_TOKENS_PER_MINUTE", "0") or 0)
        cap_hour = int(os.environ.get("CCE_LLM_BUDGET_TOKENS_PER_HOUR", "0") or 0)
        cap_day = int(os.environ.get("CCE_LLM_BUDGET_TOKENS_PER_DAY", "0") or 0)

        used_min = _llm_tokens_in_window_unlocked(60, now_ts)
        used_hour = _llm_tokens_in_window_unlocked(3600, now_ts)
        used_day = _llm_tokens_in_window_unlocked(86400, now_ts)

        def row(cap: int, used: int) -> Dict[str, Any]:
            if cap <= 0:
                return {
                    "cap": 0,
                    "used": used,
                    "remaining": None,
                    "pct_used": None,
                    "level": "disabled",
                }
            pct = round((used / cap) * 100.0, 2)
            return {
                "cap": cap,
                "used": used,
                "remaining": max(cap - used, 0),
                "pct_used": pct,
                "level": _headroom_level(pct),
            }

        minute = row(cap_min, used_min)
        hour = row(cap_hour, used_hour)
        day = row(cap_day, used_day)

        levels = [x["level"] for x in (minute, hour, day) if x["level"] != "disabled"]
        if "critical" in levels:
            overall = "critical"
        elif "warning" in levels:
            overall = "warning"
        elif "watch" in levels:
            overall = "watch"
        else:
            overall = "ok"

        recommendation = {
            "critical": "switch_to_peak_now",
            "warning": "reduce_llm_steps_or_tokens",
            "watch": "monitor_every_15m",
            "ok": "keep_current_tier",
        }[overall]

        return {
            "ts": datetime.now(timezone.utc).isoformat(),
            "overall_level": overall,
            "recommendation": recommendation,
            "windows": {
                "minute": minute,
                "hour": hour,
                "day": day,
            },
        }


def llm_alerts_snapshot(min_level: str = "warning") -> Dict[str, Any]:
    """Return actionable LLM budget alerts at or above min_level.

    Levels in ascending order: ok < watch < warning < critical.
    """
    order = {"ok": 0, "watch": 1, "warning": 2, "critical": 3}
    threshold = order.get((min_level or "warning").strip().lower(), 2)

    snap = llm_headroom_snapshot()
    windows = snap.get("windows", {})
    alerts = []

    for name, info in windows.items():
        level = str(info.get("level", "ok")).lower()
        if level == "disabled":
            continue
        if order.get(level, 0) >= threshold:
            alerts.append({
                "window": name,
                "level": level,
                "used": info.get("used"),
                "cap": info.get("cap"),
                "remaining": info.get("remaining"),
                "pct_used": info.get("pct_used"),
            })

    return {
        "ts": snap.get("ts"),
        "overall_level": snap.get("overall_level", "ok"),
        "recommendation": snap.get("recommendation"),
        "min_level": "warning" if min_level is None else str(min_level),
        "has_alerts": len(alerts) > 0,
        "alerts": alerts,
    }


def snapshot() -> Dict[str, Any]:
    """Return the full metrics snapshot for the /admin/metrics endpoint."""
    with _lock:
        now = time.time()
        uptime_s = now - _boot_time
        today = _today()
        today_counts = dict(_daily.get(today, {}))

        # Compute derived metrics
        sessions_total = _counters.get("session_start", 0)
        sessions_complete = _counters.get("session_complete", 0)
        sessions_abandoned = sessions_total - sessions_complete
        crisis_triggers = _counters.get("crisis_trigger", 0)
        meds_redirects = _counters.get("meds_redirect", 0)
        clarifications = _counters.get("clarification_asked", 0)

        # Sentiment breakdown
        sentiment_pos = _counters.get("sentiment_positive", 0)
        sentiment_neu = _counters.get("sentiment_neutral", 0)
        sentiment_neg = _counters.get("sentiment_negative", 0)
        sentiment_total = sentiment_pos + sentiment_neu + sentiment_neg

        # Shadow comparison stats
        shadow_total = len(_sentiment_shadow)
        shadow_mismatches = sum(
            1 for s in _sentiment_shadow
            if s.get("match") is False
        )

        llm_snapshot = _llm_usage_snapshot_unlocked()

        return {
            "uptime_seconds": round(uptime_s),
            "collected_since": datetime.fromtimestamp(
                _boot_time, tz=timezone.utc
            ).isoformat(),
            "totals": dict(_counters),
            "today": today_counts,
            "derived": {
                "sessions_total": sessions_total,
                "sessions_complete": sessions_complete,
                "sessions_abandoned": sessions_abandoned,
                "completion_rate": (
                    round(sessions_complete / sessions_total, 3)
                    if sessions_total > 0 else 0
                ),
                "crisis_trigger_rate": (
                    round(crisis_triggers / sessions_total, 3)
                    if sessions_total > 0 else 0
                ),
                "meds_redirect_rate": (
                    round(meds_redirects / sessions_complete, 3)
                    if sessions_complete > 0 else 0
                ),
                "clarification_rate": (
                    round(clarifications / sessions_complete, 3)
                    if sessions_complete > 0 else 0
                ),
                "sentiment_distribution": {
                    "positive": sentiment_pos,
                    "neutral": sentiment_neu,
                    "negative": sentiment_neg,
                    "total": sentiment_total,
                },
            },
            "llm_shadow": {
                "comparisons": shadow_total,
                "mismatches": shadow_mismatches,
                "mismatch_rate": (
                    round(shadow_mismatches / shadow_total, 3)
                    if shadow_total > 0 else 0
                ),
                "recent_mismatches": [
                    s for s in _sentiment_shadow[-20:]
                    if s.get("match") is False
                ],
            },
            "topic_shadow": {
                "comparisons": len(_topic_shadow),
                "top_match_rate": (
                    round(
                        sum(1 for t in _topic_shadow if t.get("top_match") is True)
                        / len(_topic_shadow), 3
                    ) if _topic_shadow else 0
                ),
                "recent_mismatches": [
                    t for t in _topic_shadow[-20:]
                    if t.get("top_match") is False
                ],
            },
            "unmatched_topics": {
                "total": len(_unmatched_topics),
                "today": sum(
                    1 for u in _unmatched_topics
                    if u["ts"].startswith(today)
                ),
                "recent": _unmatched_topics[-25:],
            },
            "llm_switch_signals": _switch_signals(
                sessions_total, today_counts, shadow_mismatches, shadow_total
            ),
            "llm_usage": llm_snapshot,
        }


def _switch_signals(
    total: int,
    today: Dict[str, int],
    shadow_mismatches: int,
    shadow_total: int,
) -> Dict[str, Any]:
    """Evaluate whether conditions suggest switching from regex to LLM."""
    daily_sessions = today.get("session_start", 0)
    signals = {
        "daily_volume_over_50": daily_sessions >= 50,
        "daily_volume": daily_sessions,
        "shadow_mismatch_over_5pct": (
            (shadow_mismatches / shadow_total) > 0.05
            if shadow_total >= 20 else None  # not enough data
        ),
        "shadow_sample_size": shadow_total,
        "recommendation": "not_enough_data",
    }

    if shadow_total < 20:
        signals["recommendation"] = "not_enough_data"
    elif signals["shadow_mismatch_over_5pct"] and signals["daily_volume_over_50"]:
        signals["recommendation"] = "switch_to_llm"
    elif signals["shadow_mismatch_over_5pct"]:
        signals["recommendation"] = "monitor_closely"
    elif signals["daily_volume_over_50"]:
        signals["recommendation"] = "volume_warrants_llm"
    else:
        signals["recommendation"] = "regex_sufficient"

    return signals


def flush_to_disk() -> None:
    """Persist current snapshot to disk (call on shutdown or periodically)."""
    data = snapshot()
    try:
        _SNAPSHOT_PATH.write_text(
            json.dumps(data, indent=2, default=str),
            encoding="utf-8",
        )
    except OSError:
        pass  # non-critical
