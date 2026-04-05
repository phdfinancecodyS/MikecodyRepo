"""Operational alert delivery helpers (SMS via Twilio)."""

from __future__ import annotations

import json
import logging
import hashlib
import os
import threading
import time
from pathlib import Path
from typing import Any, Dict

import requests

from . import metrics


logger = logging.getLogger("cce.alerting")


_LOCK = threading.Lock()
_LAST_FINGERPRINT = ""
_LAST_SENT_TS = 0.0
_SCHEDULER_THREAD = None
_SCHEDULER_STOP = threading.Event()


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _dedupe_seconds() -> int:
    try:
        return max(0, int(os.getenv("CCE_ALERT_SMS_DEDUP_SECONDS", "900")))
    except Exception:
        return 900


def _autosend_enabled() -> bool:
    return _env_bool("CCE_ALERT_SMS_AUTOSEND_ENABLED", default=False)


def _autosend_min_level() -> str:
    return os.getenv("CCE_ALERT_SMS_AUTOSEND_MIN_LEVEL", "warning").strip() or "warning"


def _autosend_interval_seconds() -> int:
    try:
        hours = float(os.getenv("CCE_ALERT_SMS_INTERVAL_HOURS", "48") or 48)
    except Exception:
        hours = 48.0
    return max(300, int(hours * 3600))


def _state_file_path() -> Path:
    configured = os.getenv("CCE_ALERT_SMS_STATE_FILE", "").strip()
    if configured:
        return Path(configured)
    return Path(__file__).resolve().parent / "data" / ".metrics" / "alert_sms_state.json"


def _read_last_auto_run_ts() -> float:
    path = _state_file_path()
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        return float(payload.get("last_run_ts", 0.0) or 0.0)
    except Exception:
        return 0.0


def _write_last_auto_run_ts(ts: float) -> None:
    path = _state_file_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"last_run_ts": float(ts)}), encoding="utf-8")
    except Exception as exc:
        logger.warning("Could not write alert autosend state: %s", exc)


def _seconds_until_next_run(now_ts: float, interval_s: int) -> float:
    last = _read_last_auto_run_ts()
    if last <= 0:
        return 0.0
    return max((last + interval_s) - now_ts, 0.0)


def _run_autosend_cycle() -> Dict[str, Any]:
    now = time.time()
    result = send_llm_alerts_sms(min_level=_autosend_min_level(), force=False)
    _write_last_auto_run_ts(now)
    return result


def _scheduler_loop() -> None:
    while not _SCHEDULER_STOP.is_set():
        if not _autosend_enabled():
            _SCHEDULER_STOP.wait(60)
            continue

        interval_s = _autosend_interval_seconds()
        wait_s = _seconds_until_next_run(time.time(), interval_s)
        if wait_s > 0:
            _SCHEDULER_STOP.wait(min(wait_s, 60))
            continue

        try:
            result = _run_autosend_cycle()
            logger.info("LLM alert autosend cycle: %s", result.get("reason", "unknown"))
        except Exception as exc:
            logger.exception("LLM alert autosend cycle failed: %s", exc)

        _SCHEDULER_STOP.wait(5)


def start_sms_alert_scheduler() -> None:
    """Start background scheduler for periodic SMS alert checks."""
    global _SCHEDULER_THREAD

    if _SCHEDULER_THREAD and _SCHEDULER_THREAD.is_alive():
        return

    _SCHEDULER_STOP.clear()
    _SCHEDULER_THREAD = threading.Thread(
        target=_scheduler_loop,
        name="cce-alert-sms-scheduler",
        daemon=True,
    )
    _SCHEDULER_THREAD.start()


def stop_sms_alert_scheduler() -> None:
    """Stop background scheduler for periodic SMS alert checks."""
    global _SCHEDULER_THREAD

    _SCHEDULER_STOP.set()
    thr = _SCHEDULER_THREAD
    if thr and thr.is_alive():
        thr.join(timeout=2)
    _SCHEDULER_THREAD = None


def _format_alert_sms(alerts_snapshot: Dict[str, Any]) -> str:
    alerts = alerts_snapshot.get("alerts", [])
    lines = ["Ask Anyway LLM alerts:"]
    for alert in alerts:
        used_pct = alert.get("used_pct")
        pct = "n/a" if used_pct is None else f"{used_pct:.1f}%"
        lines.append(
            f"{alert.get('window', '?')} {str(alert.get('level', '?')).upper()} "
            f"used={pct} action={alert.get('recommended_action', 'review')}"
        )
    return "\n".join(lines)


def send_llm_alerts_sms(min_level: str = "warning", force: bool = False) -> Dict[str, Any]:
    """Send current LLM alerts via Twilio SMS (with dedupe cooldown)."""
    global _LAST_FINGERPRINT, _LAST_SENT_TS

    if not _env_bool("CCE_ALERT_SMS_ENABLED", default=False):
        return {
            "ok": True,
            "sent": False,
            "reason": "sms_disabled",
        }

    account_sid = os.getenv("TWILIO_ACCOUNT_SID", "").strip()
    auth_token = os.getenv("TWILIO_AUTH_TOKEN", "").strip()
    from_number = os.getenv("TWILIO_FROM_NUMBER", "").strip()
    to_number = os.getenv("CCE_ALERT_SMS_TO", "").strip()

    if not (account_sid and auth_token and from_number and to_number):
        return {
            "ok": False,
            "sent": False,
            "reason": "twilio_env_missing",
            "missing": [
                name
                for name, value in {
                    "TWILIO_ACCOUNT_SID": account_sid,
                    "TWILIO_AUTH_TOKEN": auth_token,
                    "TWILIO_FROM_NUMBER": from_number,
                    "CCE_ALERT_SMS_TO": to_number,
                }.items()
                if not value
            ],
        }

    snap = metrics.llm_alerts_snapshot(min_level=min_level)
    if not snap.get("has_alerts"):
        return {
            "ok": True,
            "sent": False,
            "reason": "no_alerts",
            "min_level": min_level,
        }

    body = _format_alert_sms(snap)
    fingerprint = hashlib.sha256(body.encode("utf-8")).hexdigest()
    now = time.time()
    dedupe_s = _dedupe_seconds()

    with _LOCK:
        if (
            not force
            and _LAST_FINGERPRINT == fingerprint
            and (now - _LAST_SENT_TS) < dedupe_s
        ):
            return {
                "ok": True,
                "sent": False,
                "reason": "deduped",
                "dedupe_seconds": dedupe_s,
            }

    url = f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}/Messages.json"
    try:
        resp = requests.post(
            url,
            auth=(account_sid, auth_token),
            data={
                "From": from_number,
                "To": to_number,
                "Body": body,
            },
            timeout=12,
        )
        resp.raise_for_status()
        payload = resp.json()
    except requests.RequestException as exc:
        return {
            "ok": False,
            "sent": False,
            "reason": "twilio_send_failed",
            "error": str(exc),
        }

    with _LOCK:
        _LAST_FINGERPRINT = fingerprint
        _LAST_SENT_TS = now

    return {
        "ok": True,
        "sent": True,
        "reason": "sent",
        "to": to_number,
        "message_sid": payload.get("sid"),
        "status": payload.get("status"),
        "alert_count": len(snap.get("alerts", [])),
    }
