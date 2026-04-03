"""
Crisis detection for the Clinical Conversation Engine.
Scans free-text input for indicators that require immediate escalation.
"""
import re

# Phrases that indicate active crisis / imminent danger
CRISIS_PATTERNS = [
    r"\b(kill|killing)\s+(my|him|her|them)\s*self\b",
    r"\bsuicid(e|al|ally)\b",
    r"\bend\s+(my|this)\s+life\b",
    r"\b(want|wanting)\s+to\s+die\b",
    r"\bdon\u2019?t\s+want\s+to\s+(be\s+here|live|exist)\b",
    r"\b(hurt|harm|cut)\s+(my|him|her)\s*self\b",
    r"\b(no\s+reason|point)\s+to\s+(live|keep\s+going)\b",
    r"\bplan(ning)?\s+to\s+(die|end|hurt)\b",
    r"\bgoodbye\s+(forever|note|letter)\b",
    r"\b(giving\s+up|given\s+up)\s+on\s+(life|living|everything)\b",
    r"\bcan\u2019?t\s+(go\s+on|take\s+it\s+anymore)\b",
    r"\b988\b",                          # user already calling crisis line = crisis context
    r"\bemergency\b",
    r"\boverdose\b",
    r"\bself\s*harm\b",
]

CRISIS_RE = re.compile("|".join(CRISIS_PATTERNS), re.IGNORECASE)

# Phrases that should force critical handling regardless of downstream score.
CRITICAL_OVERRIDE_PATTERNS = [
    r"\b(tonight|right\s+now|today)\b.*\b(kill\s+myself|end\s+my\s+life|suicide)\b",
    r"\b(kill\s+myself|end\s+my\s+life|suicide)\b.*\b(tonight|right\s+now|today)\b",
    r"\bi\s+have\s+a\s+plan\b",
    r"\bi\s+am\s+going\s+to\s+(kill\s+myself|end\s+my\s+life)\b",
]

CRITICAL_OVERRIDE_RE = re.compile("|".join(CRITICAL_OVERRIDE_PATTERNS), re.IGNORECASE)

# Crisis option IDs from the triage tree
CRISIS_OPTION_IDS = {"q8_frequent", "q8_plan", "safety_cannot_commit"}


def is_crisis_text(text: str) -> bool:
    """Return True if the text contains crisis indicators."""
    if not text:
        return False
    return bool(CRISIS_RE.search(text))


def is_critical_override_text(text: str) -> bool:
    """Return True if text contains explicit high-immediacy phrases."""
    if not text:
        return False
    return bool(CRITICAL_OVERRIDE_RE.search(text))


def is_crisis_option(option_id: str) -> bool:
    """Return True if the selected option is a crisis-flagged option."""
    return option_id in CRISIS_OPTION_IDS
