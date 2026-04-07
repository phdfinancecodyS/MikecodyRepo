"""
Smart template personalizer for CCE responses.

Extracts key phrases from user input and weaves them into template
responses so they feel personalized rather than canned.

No LLM needed. Pure regex/NLP extraction with template injection.
"""
import re
from typing import Optional


# ── Phrase extraction ──────────────────────────────────────────────────────────

# Strip filler/hedge words to find the core of what they said
_FILLER = re.compile(
    r"^(i(?:'?m| am|'ve been| have been| guess i(?:'?m| am))\s+|"
    r"(?:well|so|um|uh|like|honestly|basically|just|really|i think|i feel like|i don't know)\s*,?\s*)+",
    re.I
)

# Common opening phrases to strip
_OPENERS = re.compile(
    r"^(i(?:'?m| am| feel| have been| keep)\s+(?:feeling |having |dealing with |going through |struggling with |like )?)",
    re.I
)

# Extract the emotional/situational core
_EMOTION_PHRASES = [
    (re.compile(r"\b(lost|losing)\s+(my|a)\s+(\w+)", re.I), lambda m: f"losing your {m.group(3)}"),
    (re.compile(r"\b(worried|scared|terrified|afraid)\s+(about|of|for)\s+(.+?)(?:\.|$)", re.I),
     lambda m: f"{m.group(1).lower()} about {m.group(3).strip()}"),
    (re.compile(r"\b(struggling|dealing)\s+with\s+(.+?)(?:\.|$)", re.I),
     lambda m: m.group(2).strip()),
    (re.compile(r"\bcan(?:'t|not)\s+(sleep|eat|focus|stop|breathe|think)", re.I),
     lambda m: f"not being able to {m.group(1)}"),
    (re.compile(r"\b(marriage|relationship|partner|husband|wife|boyfriend|girlfriend)\s+(?:is\s+)?(.+?)(?:\.|$)", re.I),
     lambda m: f"what's going on with your {m.group(1).lower()}"),
    (re.compile(r"\b(my\s+(?:kid|child|son|daughter|mom|dad|parent|brother|sister|friend|boss))\b.*?(?:is|has been|keeps?|won'?t)\s+(.+?)(?:\.|$)", re.I),
     lambda m: f"what's happening with your {m.group(1).replace('my ', '')}"),
    (re.compile(r"\b(lonely|alone|isolated|empty|numb|exhausted|burned?\s*out|overwhelmed|anxious|depressed|stressed|angry|frustrated|hopeless|stuck|lost|sad|down|bad|hurt|broken|tired|drained|scared|miserable|defeated|worthless|helpless|confused|disconnected|flat|nothing|dead\s*inside)\b", re.I),
     lambda m: f"feeling {m.group(1).lower()}"),
    (re.compile(r"\b(work|job|school|money|finances?|debt|bills?)\b.*(?:stress|hard|difficult|killing|draining|toxic)", re.I),
     lambda m: f"the {m.group(1).lower()} stress"),
    (re.compile(r"(?:stress|hard|difficult|killing|draining|toxic).*\b(work|job|school|money|finances?|debt)\b", re.I),
     lambda m: f"the {m.group(1).lower()} stress"),
]


def extract_key_phrase(user_text: str) -> Optional[str]:
    """Pull the emotional/situational core from user input.

    Returns a short phrase like "losing your dad", "the work stress",
    "not being able to sleep", or None if nothing specific found.
    """
    if not user_text or len(user_text.strip()) < 3:
        return None

    text = user_text.strip()

    # Try structured extraction first
    for pattern, formatter in _EMOTION_PHRASES:
        m = pattern.search(text)
        if m:
            phrase = formatter(m)
            # Clean up and cap length
            phrase = phrase.strip().rstrip(".,!?")
            if len(phrase) > 60:
                phrase = phrase[:57] + "..."
            return phrase

    # Fallback: strip filler and use a shortened version of what they said
    cleaned = _FILLER.sub("", text).strip()
    cleaned = _OPENERS.sub("", cleaned).strip()

    if cleaned and len(cleaned) > 4:
        # Take first clause (before comma, period, or "and")
        clause = re.split(r"[,.]|\band\b", cleaned, maxsplit=1)[0].strip()
        if len(clause) > 4:
            clause = clause.rstrip(".,!?")
            if len(clause) > 50:
                clause = clause[:47] + "..."
            return clause.lower()

    return None


# ── Response personalization ──────────────────────────────────────────────────

# Templates with {phrase} slots. Multiple variants per category for variety.
_NEGATIVE_TEMPLATES = [
    "That sounds really heavy, especially {phrase}.\n\nTell me a little more about what's been going on.",
    "{phrase_cap} takes a toll.\n\nWhat's been the hardest part of that for you?",
    "Thank you for being honest about {phrase}.\n\nWhat's been the hardest part?",
    "{phrase_cap} is a lot to carry.\n\nTell me more about what's been happening.",
    "Glad you said something about {phrase}.\n\nWhat's that been like for you?",
]

_POSITIVE_TEMPLATES = [
    "That's really good to hear.\n\nWhat's been helping things feel that way?",
    "I'm glad things are going well.\n\nWhat's been making the biggest difference?",
    "That's great.\n\nAnything in particular that's been keeping things good?",
]

_CLARIFICATION_TEMPLATES = [
    "Want to make sure I point you to the right thing.\n\nWhen you say {phrase}, what's been weighing on you most?",
    "Got it. Can you tell me a little more about {phrase}? That'll help me find the right fit.",
    "Makes sense. What part of {phrase} has been the hardest to deal with?",
]

# Fallback (no phrase extracted) -- still warmer than the static templates
_NEGATIVE_FALLBACKS = [
    "That takes guts to say out loud.\n\nTell me a little more about what's been happening.",
    "That sounds really tough.\n\nWhat part of it has been weighing on you most?",
    "Glad you're talking about it.\n\nWhat's been the hardest part of all this?",
]

_CLARIFICATION_FALLBACKS = [
    "Want to make sure I get this right.\n\nCan you tell me a little more about what's been on your mind?",
    "Makes sense. What part of this has been weighing on you most?",
]

# Rotating index per session to avoid repeating the same variant
_variant_counter = 0


def _pick(templates: list) -> str:
    global _variant_counter
    _variant_counter += 1
    return templates[_variant_counter % len(templates)]


def personalize_negative_probe(user_text: str) -> str:
    """Personalize the 'not good' follow-up based on what the user said."""
    phrase = extract_key_phrase(user_text)
    if not phrase:
        return _pick(_NEGATIVE_FALLBACKS)

    template = _pick(_NEGATIVE_TEMPLATES)
    return template.format(
        phrase=phrase,
        phrase_cap=phrase[0].upper() + phrase[1:] if phrase else "",
    )


def personalize_positive_probe(user_text: str) -> str:
    """Personalize the 'good' follow-up. Less extraction needed here."""
    return _pick(_POSITIVE_TEMPLATES)


def personalize_clarification(user_text: str) -> str:
    """Personalize the clarification/topic-probe follow-up."""
    phrase = extract_key_phrase(user_text)
    if not phrase:
        return _pick(_CLARIFICATION_FALLBACKS)

    template = _pick(_CLARIFICATION_TEMPLATES)
    return template.format(phrase=phrase)


# ── MI-style deepening ────────────────────────────────────────────────────────

# Open-ended, reflective follow-ups that follow the user's lead.
# No predetermined pathway. Just curiosity about their experience.
_DEEPENING_TEMPLATES = [
    "That makes sense. What part of {phrase} has been hitting you the hardest?",
    "That lands different when you say it out loud. How has {phrase} been showing up day to day?",
    "Thank you for sharing that. What would make the biggest difference for you right now when it comes to {phrase}?",
    "That's real. What does support around {phrase} look like for you right now?",
    "Got it. If you could change one thing about {phrase}, what would it be?",
]

_DEEPENING_FALLBACKS = [
    "That makes sense. What part of this has been hitting you the hardest?",
    "That's a lot to sit with. What would make the biggest difference for you right now?",
    "Thank you for sharing that. What does support look like for you right now?",
    "That's real. If you could change one thing about this, what would it be?",
    "Got it. How has this been showing up in your day to day?",
]

_GOAL_CLARIFY_FALLBACKS = [
    "If this felt even a little better this week, what would you notice first?",
    "What would one small shift look like for you over the next few days?",
    "If you could move this one step in a better direction, what would change first?",
    "Has there been a recent moment where this felt even a little more manageable? What was different?",
    "On a scale from 0 to 10, where are you right now, and what would one step up look like?",
]

_POSITIVE_DEEPENING_FALLBACKS = [
    "Love hearing that. What do you think has been helping this feel steadier lately?",
    "That is a solid shift. What has been the biggest contributor to things feeling better?",
    "Really glad to hear this. What are you doing right now that you want to keep going?",
    "That is meaningful progress. What part of your routine has helped most?",
    "You have good momentum here. What has surprised you most about what is working?",
]

_POSITIVE_GOAL_CLARIFY_FALLBACKS = [
    "If you wanted to protect this progress this week, what is one thing you would keep doing?",
    "What would help you keep this momentum going over the next few days?",
    "If this kept improving a little more, what would you notice first?",
    "What is one small move that would help this continue in the right direction?",
    "What support would make it easier to keep this trend going?",
]


def personalize_deepening(user_text: str, detected_topics: list = None) -> str:
    """MI-style open-ended deepening. Follows the user's thread, not ours."""
    phrase = extract_key_phrase(user_text) if user_text else None
    if not phrase:
        return _pick(_DEEPENING_FALLBACKS)

    template = _pick(_DEEPENING_TEMPLATES)
    return template.format(phrase=phrase)


def personalize_goal_clarify(user_text: str = "", detected_topics: list = None) -> str:
    """SFBT-style pivot from problem exploration to first-step change."""
    return _pick(_GOAL_CLARIFY_FALLBACKS)


def personalize_positive_deepening(user_text: str = "", detected_topics: list = None) -> str:
    """Positive-track deepening that stays strengths-focused."""
    return _pick(_POSITIVE_DEEPENING_FALLBACKS)


def personalize_positive_goal_clarify(user_text: str = "", detected_topics: list = None) -> str:
    """Positive-track goal clarification to sustain progress."""
    return _pick(_POSITIVE_GOAL_CLARIFY_FALLBACKS)
