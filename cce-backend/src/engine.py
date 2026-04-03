"""
Conversation engine for the Clinical Conversation Engine.
Manages sessions, tree navigation, topic detection, scoring, and outcome generation.
"""
import json
import os
import re
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .crisis import is_crisis_option, is_crisis_text, is_critical_override_text
from .config import (
    get_guide_for_topic, get_offer_for_risk, get_offer_for_guide, resolve_guide_path,
    GUIDES_BY_ID, AUDIENCE_BUCKETS, AUDIENCE_QUESTIONS,
    QUIZ_SCORING_RANGES, QUIZ_SCORING_OVERRIDES,
)
from .models import (
    Clarification, CrisisResource, GuideItem, Outcome,
    PolicyNotice, Prompt, PromptOption, SessionState,
)

# ─── Data loading ──────────────────────────────────────────────────────────────

DATA_DIR = Path(__file__).parent / "data"

def _load(filename: str) -> dict:
    with open(DATA_DIR / filename, encoding="utf-8") as f:
        return json.load(f)

TREES: Dict[str, Any] = _load("trees.json")
CONTENT: Dict[str, Any] = _load("content.json")
TOPICS: Dict[str, Any] = CONTENT["topics"]
BANDS: Dict[str, Any] = CONTENT["triage_bands"]

# ─── In-memory session store ───────────────────────────────────────────────────

_SESSIONS: Dict[str, SessionState] = {}


# ─── Sentiment ─────────────────────────────────────────────────────────────────

POS_WORDS = {
    "good","great","well","fine","happy","grateful","better","amazing","okay",
    "alright","positive","blessed","thankful","improving","hopeful","excited",
    "love","wonderful","fantastic","relief","relieved","stable","managing",
}
NEG_WORDS = {
    "bad","terrible","awful","horrible","worst","sad","depressed","anxious",
    "scared","overwhelming","overwhelmed","hopeless","exhausted","lonely",
    "miserable","struggling","suffering","broken","lost","empty","numb","stuck",
    "angry","frustrated","hurt","stressed","worried","afraid","panic","grief",
    "crying","dark","heavy","drained","worthless","failure","useless",
}
NEGATORS = {"not","no","never","don't","doesn't","can't","cannot","nor","ain't",
            "don\u2019t","doesn\u2019t","can\u2019t"}


def _score_sentiment(text: str) -> str:
    """Return 'positive', 'neutral', or 'negative'."""
    words = re.findall(r"[\w\u2019]+", text.lower())
    score = 0
    negate = False
    for w in words:
        if w in NEGATORS:
            negate = True
            continue
        if w in POS_WORDS:
            score += -1 if negate else 1
        elif w in NEG_WORDS:
            score += 1 if negate else -1
        negate = False
    if score >= 1:
        return "positive"
    if score <= -1:
        return "negative"
    return "neutral"


# ─── Topic detection ───────────────────────────────────────────────────────────

def _detect_topics(text: str) -> List[str]:
    """Return list of matched topic IDs (most specific first)."""
    lower = text.lower()
    matched: List[Tuple[str, int]] = []
    for tid, tdata in TOPICS.items():
        hits = sum(1 for kw in tdata.get("keywords", []) if kw in lower)
        if hits > 0:
            matched.append((tid, hits))
    matched.sort(key=lambda x: x[1], reverse=True)
    return [m[0] for m in matched] or ["general"]


# ─── Policy trigger ────────────────────────────────────────────────────────────

POLICY_RE = re.compile(
    r"\b(diagnos|prescri|medic(at|in)|am\s+i\s+(depressed|anxious|bipolar)|"
    r"what\s+disease|what disorder|what\s+do\s+i\s+have|treat(ment|ing)|therapy\s+for)\b",
    re.IGNORECASE,
)


def _is_policy_trigger(text: str) -> bool:
    return bool(POLICY_RE.search(text))


# ─── Tree helpers ──────────────────────────────────────────────────────────────

def _get_tree(tree_id: str) -> Dict[str, Any]:
    if tree_id not in TREES:
        raise ValueError(f"Unknown tree_id: {tree_id}")
    return TREES[tree_id]


def _step_to_prompt(step: Dict[str, Any]) -> Prompt:
    options = None
    if step.get("type") == "choice":
        options = [PromptOption(id=o["id"], text=o["text"]) for o in step.get("options", [])]
    return Prompt(
        question=step["prompt"],
        type=step["type"],
        options=options,
    )


def _adaptive_screener_next(
    current_step_id: str,
    scores: Dict[str, int],
    option_id: Optional[str],
) -> Optional[str]:
    """Return next screener step id, or CRITICAL_NOW for immediate crisis completion."""
    if option_id == "safety_cannot_commit":
        return "CRITICAL_NOW"

    safety_total = (
        scores.get("safety_now", 0)
        + scores.get("safety_plan", 0)
        + scores.get("safety_access", 0)
        + scores.get("safety_intent", 0)
        + scores.get("safety_commitment", 0)
    )

    # Low signal after first question: still continue, but skip one detail step.
    if current_step_id == "suicide_screener_q1" and scores.get("safety_now", 0) == 0:
        return "suicide_screener_q3"

    # Low cumulative signal: shorten screener and move to commitment question.
    if current_step_id == "suicide_screener_q2" and safety_total <= 2:
        return "suicide_screener_q5"
    if current_step_id == "suicide_screener_q3" and safety_total <= 3:
        return "suicide_screener_q5"

    # High cumulative signal by intent step: route immediately to crisis outcome.
    if current_step_id == "suicide_screener_q4" and safety_total >= 9:
        return "CRITICAL_NOW"

    return None


# ─── Outcome builder ───────────────────────────────────────────────────────────

def _build_outcome(session: SessionState) -> Outcome:
    # Crisis always overrides
    if session.is_crisis:
        band_data = BANDS["critical"]
        cr_list = [CrisisResource(**r) for r in band_data.get("crisis_resources", [])]
        primary_topic = (session.detected_topics or ["general"])[0]

        # Config-driven guide recommendation
        guide_entry = get_guide_for_topic(primary_topic)
        free_res = None
        if guide_entry:
            audience = getattr(session, 'audience_bucket', None) or "general-mental-health"
            free_res = GuideItem(
                title=guide_entry["title"],
                url=f"/guides/{guide_entry['guide_id']}/{audience}",
                description=f"Matched guide for {primary_topic}",
            )

        return Outcome(
            band="critical",
            summary=band_data["summary"],
            disclaimer=band_data["disclaimer"],
            next_step=band_data["next_step"],
            matched_topics=session.detected_topics,
            audience_bucket=audience,
            matched_guide_id=guide_entry["guide_id"] if guide_entry else None,
            free_resource=free_res,
            upsell=[],
            crisis_resources=cr_list,
        )

    # Triage score to band
    score = session.total_score
    band_key = "low_risk"

    # Tree-aware banding: mental-health-triage uses quiz-content.json ranges
    if session.tree_id == "mental-health-triage" and QUIZ_SCORING_RANGES:
        # Step 1: Determine band from total score ranges
        for r in QUIZ_SCORING_RANGES:
            if r["min"] <= score <= r["max"]:
                band_key = r["riskLevel"]
                break

        # Step 2: Apply overrides (force or minimum floor)
        rank = {"low_risk": 0, "moderate_risk": 1, "high_risk": 2, "critical": 3}
        for override in QUIZ_SCORING_OVERRIDES:
            qid = override.get("questionId", "")
            override_score = override.get("score")
            actual_score = session.scores.get(
                # Map q5 -> safety (the score_key for Q8/Q5 in trees.json)
                {"q5": "safety", "q8": "safety"}.get(qid, qid),
                None
            )
            if actual_score is not None and actual_score >= override_score:
                forced_level = override.get("riskLevel")
                min_level = override.get("minimumRiskLevel")
                if forced_level:
                    band_key = forced_level
                    break
                if min_level and rank.get(band_key, 0) < rank.get(min_level, 0):
                    band_key = min_level
    else:
        # Main-flow uses content.json triage bands
        for key, bdata in BANDS.items():
            lo, hi = bdata["threshold"]
            if lo <= score <= hi:
                band_key = key
                break

    band_data = BANDS[band_key]
    primary_topic = (session.detected_topics or ["general"])[0]
    audience = getattr(session, 'audience_bucket', None) or "general-mental-health"

    # Config-driven guide lookup
    guide_entry = get_guide_for_topic(primary_topic)
    free_res = None
    matched_gid = guide_entry["guide_id"] if guide_entry else None
    if guide_entry:
        free_res = GuideItem(
            title=guide_entry["title"],
            url=f"/guides/{guide_entry['guide_id']}?audience={audience}",
            description=f"Matched guide for {primary_topic}",
        )

    # Per-guide offer routing (uses GUIDE-OFFER-MAPPING.csv + Etsy links)
    offer = get_offer_for_guide(matched_gid, band_key) if matched_gid else get_offer_for_risk(band_key)
    upsell = []
    if not offer.get("hide_paid_above_fold"):
        upsell_url = offer.get("etsy_url") or f"/checkout/{offer['product_id']}"
        upsell_item = GuideItem(
            title=offer["label"],
            price=offer.get("etsy_price") or offer.get("price"),
            description=offer["description"],
            url=upsell_url,
        )
        upsell.append(upsell_item)

    cr_list = None
    if band_key in ("critical", "high_risk"):
        cr_list = [CrisisResource(**r) for r in BANDS.get("critical", {}).get("crisis_resources", [])]

    return Outcome(
        band=band_key,
        summary=band_data["summary"],
        disclaimer=band_data["disclaimer"],
        next_step=band_data["next_step"],
        matched_topics=session.detected_topics,
        audience_bucket=audience,
        matched_guide_id=matched_gid,
        free_resource=free_res,
        upsell=upsell,
        crisis_resources=cr_list,
        offer=offer,
    )


# ─── Public API ────────────────────────────────────────────────────────────────

def create_session(tree_id: str) -> Tuple[SessionState, Prompt]:
    tree = _get_tree(tree_id)
    entry_id = tree["entry"]
    entry_step = tree["steps"][entry_id]

    session = SessionState(
        session_id=str(uuid.uuid4()),
        tree_id=tree_id,
        current_step=entry_id,
    )
    _SESSIONS[session.session_id] = session
    return session, _step_to_prompt(entry_step)


def get_session(session_id: str) -> Optional[SessionState]:
    return _SESSIONS.get(session_id)


def process_response(
    session_id: str,
    option_id: Optional[str],
    message: Optional[str],
) -> Dict[str, Any]:
    """
    Process a user response and advance the session.
    Returns a dict matching the RespondResponse shape.
    """
    session = _SESSIONS.get(session_id)
    if not session:
        raise ValueError(f"Session not found: {session_id}")

    tree = _get_tree(session.tree_id)
    steps = tree["steps"]
    current_step = steps[session.current_step]

    policy_notice: Optional[PolicyNotice] = None

    # ── Clarification shortcut ─────────────────────────────────────
    if session.awaiting_clarification:
        if option_id and session.clarification_options:
            # Map clarification option back to topic
            for opt in session.clarification_options:
                if opt.id == option_id:
                    session.detected_topics = [option_id.replace("clarify_", "")]
                    break
        session.awaiting_clarification = False
        session.clarification_options = None
        # Continue to terminal / outcome
        session.is_complete = True
        session.outcome = _build_outcome(session)
        return {
            "status": "complete",
            "outcome": session.outcome,
            "policy_notice": policy_notice,
        }

    # ── Record input ───────────────────────────────────────────────
    session.history.append({
        "step": session.current_step,
        "option_id": option_id,
        "message": message,
    })

    # ── Policy notice ──────────────────────────────────────────────
    if message and _is_policy_trigger(message):
        policy_notice = PolicyNotice()

    # ── Score option (triage) ──────────────────────────────────────
    if option_id and current_step.get("type") == "choice":
        for opt in current_step.get("options", []):
            if opt["id"] == option_id:
                sc = opt.get("score", 0)
                session.scores[current_step.get("score_key", "misc")] = sc
                session.total_score += sc
                if opt.get("topic") and opt["topic"] not in session.detected_topics:
                    session.detected_topics.append(opt["topic"])
                break

    # ── Sentiment & topic from free text ──────────────────────────
    if message:
        session.sentiment = _score_sentiment(message)
        detected = _detect_topics(message)
        for t in detected:
            if t not in session.detected_topics:
                session.detected_topics.append(t)

    # ── Safety screener trigger (always for safety language) ───────
    if message and is_critical_override_text(message):
        session.total_score += 12
        session.is_crisis = True
        session.is_complete = True
        session.outcome = _build_outcome(session)
        _SESSIONS[session_id] = session
        return {
            "status": "complete",
            "outcome": session.outcome,
            "policy_notice": policy_notice,
        }

    if message and is_crisis_text(message):
        if "crisis" not in session.detected_topics:
            session.detected_topics.append("crisis")

        has_screener = "suicide_screener_q1" in steps
        in_screener = session.current_step.startswith("suicide_screener_")

        if has_screener and not in_screener:
            session.safety_screener_active = True
            session.current_step = "suicide_screener_q1"
            _SESSIONS[session_id] = session
            return {
                "status": "in_progress",
                "next_prompt": _step_to_prompt(steps["suicide_screener_q1"]),
                "policy_notice": policy_notice,
            }

    # ── Crisis check (option) ──────────────────────────────────────
    if option_id and is_crisis_option(option_id):
        session.is_crisis = True

    if session.is_crisis:
        session.is_complete = True
        session.outcome = _build_outcome(session)
        _SESSIONS[session_id] = session
        return {
            "status": "complete",
            "outcome": session.outcome,
            "policy_notice": policy_notice,
        }

    # ── Adaptive screener flow control ─────────────────────────────
    if current_step["id"].startswith("suicide_screener_") and option_id:
        screener_next = _adaptive_screener_next(current_step["id"], session.scores, option_id)
        if screener_next == "CRITICAL_NOW":
            session.is_crisis = True
            session.is_complete = True
            session.outcome = _build_outcome(session)
            _SESSIONS[session_id] = session
            return {
                "status": "complete",
                "outcome": session.outcome,
                "policy_notice": policy_notice,
            }
        if screener_next and screener_next in steps:
            session.current_step = screener_next
            _SESSIONS[session_id] = session
            return {
                "status": "in_progress",
                "next_prompt": _step_to_prompt(steps[screener_next]),
                "policy_notice": policy_notice,
            }

    # ── Determine next step ────────────────────────────────────────
    routing = current_step.get("routing")

    if routing == "sentiment":
        next_step_id = "good_probe" if session.sentiment == "positive" else "not_good_probe"
    elif routing == "sentiment_branch":
        sentiment_map = {"good": "good_what", "meh": "not_good_what", "bad": "not_good_what"}
        next_step_id = sentiment_map.get(option_id or "", "not_good_what")
    elif routing == "topic_match":
        if len(session.detected_topics) == 0 or session.detected_topics == ["general"]:
            clarify_options = [
                PromptOption(id="clarify_anxiety", text="Anxiety or constant worry"),
                PromptOption(id="clarify_depression", text="Low mood or feeling empty"),
                PromptOption(id="clarify_relationships", text="Relationships or loneliness"),
                PromptOption(id="clarify_work", text="Work or life stress"),
                PromptOption(id="clarify_grief", text="Grief or loss"),
                PromptOption(id="clarify_family", text="Family stress"),
                PromptOption(id="clarify_trauma", text="Past trauma or difficult memories"),
                PromptOption(id="clarify_recovery", text="Substance use or recovery"),
            ]
            session.awaiting_clarification = True
            session.clarification_options = clarify_options
            _SESSIONS[session_id] = session
            return {
                "status": "needs_clarification",
                "clarification": Clarification(
                    text="Can you help me understand a bit better - which of these feels closest to what you\u2019re going through?",
                    options=clarify_options,
                ),
                "policy_notice": policy_notice,
            }

        next_step_id = current_step.get("next", None) or (
            "topic_followup" if "topic_followup" in steps else None
        ) or (
            "topic_depth" if "topic_depth" in steps else None
        )

        if next_step_id is None:
            session.is_complete = True
            session.outcome = _build_outcome(session)
            _SESSIONS[session_id] = session
            return {
                "status": "complete",
                "outcome": session.outcome,
                "policy_notice": policy_notice,
            }
    else:
        next_step_id = current_step.get("next")

    # ── Terminal step? ────────────────────────────────────────────
    if current_step.get("terminal") or next_step_id is None or next_step_id not in steps:
        session.is_complete = True
        session.outcome = _build_outcome(session)
        _SESSIONS[session_id] = session
        return {
            "status": "complete",
            "outcome": session.outcome,
            "policy_notice": policy_notice,
        }

    # ── Advance to next step ──────────────────────────────────────
    session.current_step = next_step_id
    next_step = steps[next_step_id]
    _SESSIONS[session_id] = session

    return {
        "status": "in_progress",
        "next_prompt": _step_to_prompt(next_step),
        "policy_notice": policy_notice,
    }


def get_outcome(session_id: str) -> Optional[Outcome]:
    session = _SESSIONS.get(session_id)
    if not session:
        return None
    if not session.is_complete or not session.outcome:
        return None
    return session.outcome
