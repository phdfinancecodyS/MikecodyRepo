"""
Crisis detection for the Clinical Conversation Engine.
Scans free-text input for indicators that require immediate escalation.
"""
import re

# Phrases that indicate active crisis / imminent danger
# Note: ['\u2019] handles both straight and curly apostrophes
CRISIS_PATTERNS = [
    r"\b(kill|killing)\s+(my|him|her|them)\s*self\b",
    r"\bsuicid(e|al|ally)\b",
    r"\bend(?:ing)?\s+(my|this)\s+life\b",
    r"\bend(?:ing)?\s+it\s+all\b",
    r"\b(want|wanting|wanna|need|gonna|going)\s+to\s+die\b",
    r"\bdon['\u2019]?t\s+want\s+to\s+(be\s+here|live|exist|wake\s+up)\b",
    r"\b(hurt|harm|cut)\s+(my|him|her)\s*self\b",
    r"\b(no\s+reason|point)\s+(to|of)\s+(live|living|keep\s+going)\b",
    r"\bno\s+point\b.*\b(living|life|alive)\b",
    r"\bwhat['\u2019]?s\s+the\s+point\s+of\s+(living|life|going\s+on)\b",
    r"\bwhat['\u2019]?s\s+the\s+(point|purpose|use)\b",
    r"\bplan(ning)?\s+to\s+(die|end|hurt)\b",
    r"\bgoodbye\s+(forever|note|letter)\b",
    r"\b(giving|gave)\s+away\s+(?:(?:all|my|all\s+my)\s+)?(?:stuff|things|belongings)\b",
    r"\bsaying\s+(?:my\s+)?goodbye\b",
    r"\b(giving\s+up|given\s+up)\s+on\s+(life|living|everything)\b",
    r"\bcan['\u2019]?t\s+(go\s+on|take\s+it\s+anymore)\b",
    r"\b988\b",
    r"\bemergency\b",
    r"\boverdose\b",
    r"\bself\s*harm\b",
    r"\bdon['\u2019]?t\s+want\s+to\s+be\s+here\s+anymore\b",
    # "better off without me"
    r"\bbetter\s+off\s+(?:without\s+me|if\s+i)\b",
    r"\b(?:world|everyone|they|family)\s+(?:would\s+be\s+)?better\s+off\b",
    r"\bno\s*one\s+(?:would\s+)?(?:even\s+)?(?:care|notice|miss)\b",
    # "wish I was dead/gone/never born"
    r"\bwish(?:ed)?\s+(?:i\s+)?(?:was(?:n['\u2019]?t\s+(?:here|alive|born))|was\s+never\s+born|were\s+dead)\b",
    r"\bwish(?:ed)?\s+(?:i\s+)?could\s+(?:disappear|vanish|just\s+not\s+exist)\b",
    # TikTok censorship workarounds / coded crisis
    r"\bkm+s\b",
    r"\bkmy?\s*self\b",
    r"\bun\s*alive\b",
    r"\bsewerslide\b",
    r"\bsewer\s*slide\b",
    r"\bsu[i1]c[i1]de\b",
    r"\balt[- ]?f4\s+(?:my\s*self|myself)\b",
    r"\bctrl[- ]?z\s+(?:my\s*self|myself)\b",
    r"\b(?:final|forever|last|eternal|permanent)\s+(?:nap|sleep|rest|goodbye|peace)\b",
    r"\b(?:off|log\s*off|peace\s*out|check\s*out)\s+(?:my\s*self|myself|forever|permanently)\b",
    # "I'm done/finished with everything/life"
    r"\bi(?:['\u2019]?m)?\s+(?:done|finished|over)\s+(?:with\s+)?(?:everything|it\s+all|life|living)\b",
    # Plans / preparation
    r"\b(?:have|got|made)\s+a\s+plan\b",
    r"\bwrote\s+(?:a\s+)?(?:note|letter|goodbye)\b",
]

CRISIS_RE = re.compile("|".join(CRISIS_PATTERNS), re.IGNORECASE)

# Phrases that should force critical handling regardless of downstream score.
CRITICAL_OVERRIDE_PATTERNS = [
    r"\b(tonight|right\s+now|today)\b.*\b(kill\s+myself|end\s+my\s+life|suicide|kms|unalive)\b",
    r"\b(kill\s+myself|end\s+my\s+life|suicide|kms|unalive)\b.*\b(tonight|right\s+now|today)\b",
    r"\bi\s+have\s+a\s+plan\b",
    r"\bi['\u2019]?m?\s+(going|about)\s+to\s+(kill\s+myself|end\s+my\s+life|end\s+it\s+all|jump|shoot|hang)\b",
    r"\bi\s+am\s+going\s+to\s+(kill\s+myself|end\s+my\s+life|end\s+it)\b",
    r"\bi['\u2019]?m?\s+(going|about)\s+to\s+(kms|unalive|off\s+myself)\b",
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
