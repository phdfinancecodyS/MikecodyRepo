"""
Audience bucket matcher for the CCE.

Resolves user free-text into one of 17 audience buckets.
Keyword-based (default) with optional LLM support for ambiguous cases.

Rules from audience-bucket-flow.json:
  - Critical risk: skip audience matching entirely
  - Max 1 primary bucket, max 2 overlay buckets
  - No match or "general" -> general-mental-health
  - Allow explicit opt-out ("keep it general", "doesn't matter")
"""
import re
from typing import Dict, List, Optional, Tuple

# Keyword patterns for each bucket. Order matters: more specific first.
# Each entry: (bucket_id, compiled regex)
_BUCKET_PATTERNS: List[Tuple[str, re.Pattern]] = [
    ("military-veteran", re.compile(
        r"\b(military|veteran|vet\b|army|navy|marines?|air\s*force|coast\s*guard|"
        r"national\s*guard|deployed|deployment|combat|service\s*member|active\s*duty|"
        r"reserves?|va\b|ptsd.*(?:combat|service))\b", re.I)),
    ("first-responder", re.compile(
        r"\b(first\s*responder|firefight\w*|paramedic|emt\b|ems\b|"
        r"police\s*officer|law\s*enforcement|cop\b|dispatch\w*|"
        r"911\s*(?:operator|dispatch)|search\s*and\s*rescue)\b", re.I)),
    ("healthcare-workers", re.compile(
        r"\b(nurse|nursing|rn\b|lpn\b|cna\b|doctor|physician|surgeon|"
        r"healthcare\s*worker|hospital|icu\b|er\b|emergency\s*room|"
        r"medical\s*(?:field|profession)|pharmacist|radiolog\w*|"
        r"dental\s*hygien\w*|pa\-c|np\b|therapist|"
        r"surgical\s*tech|residency|attending|nursing\s*(?:student|school))\b", re.I)),
    ("educators", re.compile(
        r"\b(teacher|teaching|educator|professor|school\s*counselor|"
        r"principal|classroom|students?\b.*(?:teach|school)|"
        r"special\s*ed\w*|paraprofessional|tutor(?:ing)?)\b", re.I)),
    ("social-workers-counselors", re.compile(
        r"\b(social\s*worker|counselor|lcsw|lmsw|msw|lpc|lmft|"
        r"case\s*manager|case\s*load|mental\s*health\s*professional|"
        r"clinical\s*(?:work|practice)|therapist.*(?:myself|burnout)|"
        r"compassion\s*fatigue)\b", re.I)),
    ("christian", re.compile(
        r"\b(christian|church|pray\w*|god\b|jesus|faith.*(?:important|part)|"
        r"bible|scripture|pastor|minister|worship|believer)\b", re.I)),
    ("faith-beyond-christian", re.compile(
        r"\b(muslim|jewish|hindu|buddhist|sikh|spiritual|mosque|synagogue|"
        r"temple|meditation.*(?:practice|spiritual)|yoga.*spiritual|"
        r"faith\b(?!.*christian)|mindfulness|pagan|wiccan)\b", re.I)),
    ("lgbtq", re.compile(
        r"\b(lgbtq?\+?|gay|lesbian|bisexual|transgender|trans\b|"
        r"nonbinary|non[\-\s]binary|queer|coming\s*out|closeted|"
        r"gender\s*(?:identity|fluid|non\s*conform)|sexual\s*orientation|same[\-\s]sex|"
        r"partner.*(?:he|she|they)|pansexual|asexual|ace\s*spec|"
        r"deadname|they[/\-\s]them)\b", re.I)),
    ("neurodivergent", re.compile(
        r"\b(neurodivergent|adhd|autism|autistic|on\s*the\s*spectrum|"
        r"sensory\s*(?:overload|issues)|executive\s*(?:function|dysfunction)|"
        r"dyslexia|dyslexic|processing\s*(?:disorder|speed)|"
        r"neurospicy|spicy\s*brain|dopamine|hyperfocus|stimming)\b", re.I)),
    ("bipoc-racial-trauma", re.compile(
        r"\b(bipoc|racial\s*trauma|racism|microaggression|"
        r"black\s*(?:man|woman|person|community)|"
        r"person\s*of\s*color|poc\b|latinx?|"
        r"asian\s*(?:american|hate)|indigenous|native\s*american|"
        r"generational\s*trauma|systemic\s*racism)\b", re.I)),
    ("young-adult-gen-z", re.compile(
        r"\b(gen[\-\s]?z|college\s*student|university|dorm|campus|"
        r"just\s*graduated|twenties|early\s*20s|"
        r"high\s*school(?:er)?|freshman|sophomore|junior\s*year|senior\s*year|"
        r"i(?:'m|\s+am)\s*(?:18|19|2[0-5])|young\s*adult|"
        r"adulting|moved\s*back\s*(?:home|in\s*with)|gap\s*year)\b", re.I)),
    ("single-parent", re.compile(
        r"\b(single\s*(?:mom|dad|parent|mother|father)|"
        r"solo\s*parent|only\s*parent|co[\-\s]?parent|"
        r"(?:my|the)\s*kids?\s*(?:are|is)\s*(?:with\s*me|mine)|"
        r"doing\s*(?:it|this)\s*(?:alone|by\s*myself).*(?:kid|child|parent))\b", re.I)),
    ("addiction-recovery", re.compile(
        r"\b(recovery|sober|sobriety|clean\b.*(?:month|year|day)|"
        r"aa\b|na\b|12[\-\s]?step|relaps\w*|addict\w*|"
        r"substance\s*(?:use|abuse)|alcoholi\w*|"
        r"drinking\s*(?:problem|too\s*much)|"
        r"sober\s*curious|california\s*sober)\b", re.I)),
    ("grief-loss", re.compile(
        r"\b(grief|griev\w*|lost\s*(?:my|a)\s*(?:mom|dad|parent|child|son|daughter|"
        r"wife|husband|partner|friend|brother|sister|sibling|baby)|"
        r"death\s*of|passed\s*away|bereave\w*|"
        r"widow(?:er|ed)?|miscarriage|stillb\w*)\b", re.I)),
    ("chronic-illness-chronic-pain", re.compile(
        r"\b(chronic\s*(?:pain|illness|disease|fatigue|condition)|"
        r"fibromyalgia|autoimmune|lupus|crohn|ms\b|"
        r"multiple\s*sclerosis|endometriosis|endo\b|disabled|disability|"
        r"pain\s*(?:every\s*day|all\s*the\s*time|constant)|"
        r"spoon\s*theory|spoonie|flair[\-\s]?up|flare[\-\s]?up|"
        r"brain\s*fog|pots\b|ehlers|eds\b)\b", re.I)),
    ("high-stress-jobs", re.compile(
        r"\b(high[\-\s]?stress\s*(?:job|work|career)|corporate\s*burnout|"
        r"wall\s*street|finance\s*(?:job|work)|lawyer|attorney|"
        r"executive|ceo|startup|entrepreneur|"
        r"working\s*(?:80|60|70)\s*hours|burnout.*(?:work|job|career)|"
        r"type[\-\s]?a|grind\s*culture)\b", re.I)),
]

# Opt-out patterns: user explicitly wants general content
_GENERAL_OPT_OUT = re.compile(
    r"\b(keep\s*it\s*general|doesn(?:'t|t)\s*matter|no\s*preference|"
    r"just\s*general|none\s*of\s*(?:those|that|the\s*above)|"
    r"not\s*(?:really|particularly)|nah|nope|skip|whatever)\b", re.I
)

_AUDIENCE_QUESTION = (
    "One more thing so I can point you to the right version. "
    "Does any of this fit you?"
)

# Button options shown on the audience picker.
# "other" reveals a text input; "general" opts out.
AUDIENCE_OPTIONS = [
    {"id": "military-veteran",   "text": "Veteran / Military"},
    {"id": "first-responder",    "text": "First Responder"},
    {"id": "healthcare-workers", "text": "Healthcare Worker"},
    {"id": "single-parent",      "text": "Parent"},
    {"id": "faith",              "text": "Person of Faith"},
    {"id": "lgbtq",              "text": "LGBTQ+"},
    {"id": "addiction-recovery",  "text": "In Recovery"},
    {"id": "grief-loss",         "text": "Grief or Loss"},
    {"id": "other",              "text": "Something else"},
    {"id": "general",            "text": "Keep it general"},
]

# Direct mapping from button option_id -> bucket ID
OPTION_TO_BUCKET = {
    "military-veteran":   "military-veteran",
    "first-responder":    "first-responder",
    "healthcare-workers": "healthcare-workers",
    "single-parent":      "single-parent",
    "faith":              "christian",
    "lgbtq":              "lgbtq",
    "addiction-recovery":  "addiction-recovery",
    "grief-loss":         "grief-loss",
    "general":            "general-mental-health",
}


def detect_audience_buckets(text: str) -> Dict[str, any]:
    """Parse free text for audience bucket matches.

    Returns:
        {
            "primary": str or None (most specific match),
            "overlays": list of str (secondary matches, max 2),
            "opted_out": bool (user said 'keep it general' or equivalent),
        }
    """
    if _GENERAL_OPT_OUT.search(text):
        return {"primary": None, "overlays": [], "opted_out": True}

    matches: List[Tuple[str, int]] = []
    for bucket_id, pattern in _BUCKET_PATTERNS:
        found = pattern.findall(text)
        if found:
            matches.append((bucket_id, len(found)))

    if not matches:
        return {"primary": None, "overlays": [], "opted_out": False}

    # Sort by hit count descending
    matches.sort(key=lambda x: x[1], reverse=True)

    primary = matches[0][0]
    overlays = [m[0] for m in matches[1:3] if m[0] != primary]

    return {"primary": primary, "overlays": overlays, "opted_out": False}


def get_audience_question() -> str:
    """Return the conversational audience question text."""
    return _AUDIENCE_QUESTION


def get_audience_options() -> list:
    """Return the button options for the audience picker."""
    return AUDIENCE_OPTIONS


def resolve_option_to_bucket(option_id: str) -> Optional[str]:
    """Map a button option_id directly to a bucket ID. Returns None for unknown."""
    return OPTION_TO_BUCKET.get(option_id)


def resolve_bucket(detection: Dict, topic_hint: Optional[str] = None) -> str:
    """Resolve detection result to a final primary bucket ID.

    Falls back to topic-based inference, then general-mental-health.
    """
    if detection.get("primary"):
        return detection["primary"]

    # If they mentioned grief/loss/recovery as a topic, those double as audience buckets
    if topic_hint:
        topic_to_bucket = {
            "grief": "grief-loss",
            "recovery": "addiction-recovery",
        }
        if topic_hint in topic_to_bucket:
            return topic_to_bucket[topic_hint]

    return "general-mental-health"
