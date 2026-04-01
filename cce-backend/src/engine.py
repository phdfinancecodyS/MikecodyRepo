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

from .crisis import is_crisis_text, is_crisis_option
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


# ─── Outcome builder ───────────────────────────────────────────────────────────

def _build_outcome(session: SessionState) -> Outcome:
    # Crisis always overrides
    if session.is_crisis:
        band_data = BANDS["critical"]
        cr_list = [CrisisResource(**r) for r in band_data.get("crisis_resources", [])]
        primary_topic = (session.detected_topics or ["general"])[0]
        topic_data = TOPICS.get(primary_topic, TOPICS["general"])
        return Outcome(
            band="critical",
            summary=band_data["summary"],
            disclaimer=band_data["disclaimer"],
            next_step=band_data["next_step"],
            matched_topics=session.detected_topics,
            free_resource=GuideItem(**topic_data.get("free_resource", {})) if topic_data.get("free_resource") else None,
            upsell=[],
            crisis_resources=cr_list,
        )

    # Triage score → band
    score = session.total_score
    band_key = "low_risk"
    for key, bdata in BANDS.items():
        lo, hi = bdata["threshold"]
        if lo <= score <= hi:
            band_key = key
            break

    band_data = BANDS[band_key]
    primary_topic = (session.detected_topics or ["general"])[0]
    topic_data = TOPICS.get(primary_topic, TOPICS["general"])

    free_res = None
    if topic_data.get("free_resource"):
        free_res = GuideItem(**topic_data["free_resource"])

    upsell = [GuideItem(**g) for g in topic_data.get("upsell", [])]

    cr_list = None
    if band_key == "critical":
        cr_list = [CrisisResource(**r) for r in band_data.get("crisis_resources", [])]

    return Outcome(
        band=band_key,
        summary=band_data["summary"],
        disclaimer=band_data["disclaimer"],
        next_step=band_data["next_step"],
        matched_topics=session.detected_topics,
        free_resource=free_res,
        upsell=upsell,
        crisis_resources=cr_list,
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

    # ── Crisis check (free text) ───────────────────────────────────
    if message and is_crisis_text(message):
        session.is_crisis = True

    # ── Crisis check (option) ──────────────────────────────────────
    if option_id and is_crisis_option(option_id):
        session.is_crisis = True

    if session.is_crisis:
        session.is_complete = True
        session.outcome = _build_outcome(session)
        return {"status": "complete", "outcome": session.outcome}

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
                # Topic pin from option
                if opt.get("topic"):
                    if opt["topic"] not in session.detected_topics:
                        session.detected_topics.append(opt["topic"])
                break

    # ── Sentiment & topic from free text ──────────────────────────
    if message:
        session.sentiment = _score_sentiment(message)
        detected = _detect_topics(message)
        for t in detected:
            if t not in session.detected_topics:
                session.detected_topics.append(t)

    # ── Determine next step ────────────────────────────────────────
    routing = current_step.get("routing")

    if routing == "sentiment":
        # psychoeducational-flow entry
        if session.sentiment == "positive":
            next_step_id = "good_probe"
        else:
            next_step_id = "not_good_probe"

    elif routing == "sentiment_branch":
        # main-flow emoji check-in
        sentiment_map = {"good": "good_what", "meh": "not_good_what", "bad": "not_good_what"}
        next_step_id = sentiment_map.get(option_id or "", "not_good_what")

    elif routing == "topic_match":
        # After probe: may need clarification or go to followup
        if len(session.detected_topics) == 0 or session.detected_topics == ["general"]:
            # Offer clarification
            clarify_options = [
                PromptOption(id="clarify_anxiety",      text="Anxiety or constant worry"),
                PromptOption(id="clarify_depression",   text="Low mood or feeling empty"),
                PromptOption(id="clarify_relationships",text="Relationships or loneliness"),
                PromptOption(id="clarify_work",         text="Work or life stress"),
                PromptOption(id="clarify_grief",        text="Grief or loss"),
                PromptOption(id="clarify_family",       text="Family stress"),
                PromptOption(id="clarify_trauma",       text="Past trauma or difficult memories"),
                PromptOption(id="clarify_recovery",     text="Substance use or recovery"),
            ]
            session.awaiting_clarification = True
            session.clarification_options = clarify_options
            _SESSIONS[session_id] = session
            return {
                "status": "needs_clarification",
                "clarification": Clarification(
                    text="Can you help me understand a bit better — which of these feels closest to what you\u2019re going through?",
                    options=clarify_options,
                ),
                "policy_notice": policy_notice,
            }
        else:
            # Move to followup depth question
            next_step_id = current_step.get("next", None) or (
                "topic_followup" if "topic_followup" in steps else None
            ) or (
                "topic_depth" if "topic_depth" in steps else None
            )
            if next_step_id is None:
                # terminal — no followup step in this tree
                session.is_complete = True
                session.outcome = _build_outcome(session)
                _SESSIONS[session_id] = session
                return {
                    "status": "complete",
                    "outcome": session.outcome,
                    "policy_notice": policy_notice,
                }
    else:
        # Explicit next pointer or terminal
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
