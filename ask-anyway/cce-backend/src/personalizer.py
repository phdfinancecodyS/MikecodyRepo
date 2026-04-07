"""
Smart template personalizer for CCE responses.

Extracts key phrases from user input and weaves them into template
responses so they feel personalized rather than canned.

No LLM needed. Pure regex/NLP extraction with template injection.
"""
import re
from typing import Optional


# ── Medication-question guard (prevent echoing drug names in templates) ────────

_MEDS_GUARD_RE = re.compile(
    r"\b("
    r"meds?|medication|medicated|prescri\w+|pill|pills|dosage|"
    r"antidepress\w+|ssris?|snris?|benzo\w*|"
    r"xanax|xanex|xanx|zanax|zanex|"
    r"zoloft|zolft|sertraline|lexapro|lexipro|prozac|prozak|"
    r"wellbutrin|welbutrin|buspar|ativan|ativn|"
    r"klonopin|klonipin|clonopin|clonazepam|valium|diazepam|"
    r"celexa|celxa|paxil|effexor|efexor|cymbalta|cymbalata|"
    r"trazodone|trazadone|seroquel|seraquil|seroquil|"
    r"abilify|risperdal|zyprexa|"
    r"lithium|lamictal|lamictel|depakote|"
    r"adderall|adderal|adderol|vyvanse|vyvans|"
    r"ritalin|ritilin|concerta|strattera|"
    r"hydroxyzine|gabapentin|gabapenton|ambien|neurontin"
    r")\b", re.IGNORECASE,
)

# ── Identity guard (never pathologize identity in templates) ──────────────────

_IDENTITY_GUARD_RE = re.compile(
    r"\b(?:i(?:'?m| am)\s+(?:an?\s+)?)"
    r"("
    # LGBTQ+
    r"gay|lesbian|bisexual|bi|trans|transgender|nonbinary|non[\-\s]?binary|"
    r"queer|lgbtq\+?|lgbtqia\+?|pansexual|asexual|ace|aromantic|aro|"
    r"two[\-\s]?spirit|intersex|genderqueer|genderfluid|gender[\-\s]?fluid|"
    # Race / ethnicity
    r"black|african[\-\s]?american|latino|latina|latinx|hispanic|"
    r"asian|indigenous|native|biracial|mixed[\-\s]?race|"
    r"pacific[\-\s]?islander|middle[\-\s]?eastern|south[\-\s]?asian|"
    # Religion / faith
    r"muslim|christian|jewish|hindu|buddhist|sikh|atheist|agnostic|"
    r"catholic|protestant|evangelical|mormon|lds|"
    # Neurodivergence
    r"autistic|neurodivergent|adhd|dyslexic|on the spectrum|"
    # Disability
    r"disabled|deaf|blind|wheelchair[\-\s]?user|chronically[\-\s]?ill|"
    # Professional identity
    r"veteran|nurse|teacher|cop|officer|firefighter|paramedic|emt|"
    r"social[\-\s]?worker|therapist|counselor|doctor|"
    # Family / life context
    r"single[\-\s]?(?:mom|dad|parent)|foster[\-\s]?(?:kid|child|parent)|"
    r"adopted|immigrant|refugee|undocumented|"
    # Recovery (identity, not crisis)
    r"in[\-\s]?recovery|sober|clean"
    r")\b", re.IGNORECASE,
)

# ── Phrase extraction ──────────────────────────────────────────────────────────

# ── 1. Normalize: fix common misspellings, contractions, text-speak ──────────

_NORMALIZE_MAP = {
    # Missing apostrophes ("im" → "i'm", "dont" → "don't", etc.)
    r"\bim\b": "i'm",
    r"\bdont\b": "don't",
    r"\bcant\b": "can't",
    r"\bwont\b": "won't",
    r"\bdoesnt\b": "doesn't",
    r"\bive\b": "i've",
    r"\bid\b(?!\s+\w+)": "i'd",  # "id" alone (not "id card")
    r"\bthats\b": "that's",
    r"\bwhats\b": "what's",
    r"\bhes\b": "he's",
    r"\bshes\b": "she's",
    r"\btheyre\b": "they're",
    r"\bwere\b(?=\s+(?:not|never|barely))": "we're",  # "were not" → "we're not"
    r"\byoure\b": "you're",
    # Common typos / phonetic spellings
    r"\bdepresed\b": "depressed",
    r"\bdepressd\b": "depressed",
    r"\bdeppressed\b": "depressed",
    r"\bdepresd\b": "depressed",
    r"\banxious\b": "anxious",
    r"\banxous\b": "anxious",
    r"\baxious\b": "anxious",
    r"\banxiosly\b": "anxiously",
    r"\boverwhemled\b": "overwhelmed",
    r"\boverwelmed\b": "overwhelmed",
    r"\boverwhelmd\b": "overwhelmed",
    r"\blonley\b": "lonely",
    r"\blonely\b": "lonely",
    r"\bmisrable\b": "miserable",
    r"\bmiserbale\b": "miserable",
    r"\bexhausted\b": "exhausted",
    r"\bexausted\b": "exhausted",
    r"\bexhasted\b": "exhausted",
    r"\bfrustated\b": "frustrated",
    r"\bfrusterated\b": "frustrated",
    r"\bhopless\b": "hopeless",
    r"\bhelpess\b": "helpless",
    r"\bworthles\b": "worthless",
    r"\bscared\b": "scared",
    r"\bskared\b": "scared",
    r"\bscaired\b": "scared",
    r"\bstrugling\b": "struggling",
    r"\bstuggling\b": "struggling",
    r"\bstressful\b": "stressful",
    r"\bstresful\b": "stressful",
    r"\bconfuesd\b": "confused",
    r"\bconfussed\b": "confused",
    r"\btrama\b": "trauma",
    r"\btramma\b": "trauma",
    r"\btramatized\b": "traumatized",
    r"\btraumatised\b": "traumatized",
    r"\bsuicidal\b": "suicidal",
    r"\bsuciidal\b": "suicidal",
    r"\bsuicidel\b": "suicidal",
    # Text-speak expansions
    r"\brly\b": "really",
    r"\brn\b": "right now",
    r"\bfr\b(?!\s+fr)": "for real",
    r"\btbh\b": "to be honest",
    r"\bngl\b": "not gonna lie",
    r"\bidk\b": "i don't know",
    r"\bidek\b": "i don't even know",
    r"\bidc\b": "i don't care",
    r"\bsmh\b": "shaking my head",
    r"\bfml\b": "frustrated",
    r"\bomg\b": "oh my god",
    r"\bwtf\b": "frustrated",
    r"\baf\b": "very",
    r"\blowkey\b": "lowkey",
    r"\bhighkey\b": "highkey",
    r"\bwanna\b": "want to",
    r"\bgonna\b": "going to",
    r"\bgotta\b": "got to",
    r"\bkinda\b": "kind of",
    r"\bsorta\b": "sort of",
    r"\bdunno\b": "don't know",
    r"\blemme\b": "let me",
    r"\bcuz\b": "because",
    r"\bcoz\b": "because",
    r"\bbc\b": "because",
    r"\btho\b": "though",
    r"\bthru\b": "through",
    r"\bnite\b": "night",
    r"\bppl\b": "people",
    r"\bw/o\b": "without",
    r"\bw/\b": "with",
    r"\bsm\b": "so much",
    r"\brn\b": "right now",
    r"\bv\b(?=\s+(?:sad|tired|stressed|anxious|depressed|overwhelmed|angry|hurt|bad|down|scared|lonely|frustrated|worried|confused|numb|empty|lost|stuck|broken|hopeless|helpless|worthless|exhausted|drained|miserable|defeated))": "very",
}

_NORMALIZE_COMPILED = [(re.compile(k, re.I), v) for k, v in _NORMALIZE_MAP.items()]


def _normalize_text(text: str) -> str:
    """Fix misspellings, expand text-speak, standardize contractions."""
    for pat, repl in _NORMALIZE_COMPILED:
        text = pat.sub(repl, text)
    return text


# ── 2. Strip filler/hedge preamble ───────────────────────────────────────────

_FILLER = re.compile(
    r"^("
    # "I'm / I am / I've been / I have been / I guess I'm"
    r"i(?:'?m| am|'ve been| have been| guess i(?:'?m| am)|'d say i(?:'?m| am))\s+"
    r"|"
    # Discourse markers: well, so, um, uh, like, honestly, basically, just, really...
    r"(?:well|so|um+|uh+|like|honestly|basically|just|really|truly|genuinely|"
    r"i think|i feel like|i don't know|i mean|look|okay so|ya know|you know|"
    r"not gonna lie|to be honest|for real|no cap|straight up|"
    r"at this point|i guess|i suppose|if i'm being honest|"
    r"i don't even know|it's just|it's like|idk|tbh|ngl|lol|omg|bro|bruh|dude|man|"
    r"low\s*key|dead\s*ass|no\s*cap)\s*,?\s*"
    r")+",
    re.I
)

# ── 3. Strip common sentence openers that restate "I feel X" ─────────────────

_OPENERS = re.compile(
    r"^("
    r"i(?:'?m| am| feel| have been| keep| been| was| got)\s+"
    r"(?:feeling |having |dealing with |going through |struggling with |like |"
    r"so |really |very |kinda |sorta |kind of |sort of |pretty |super |hella |mad |"
    r"lowkey |highkey |deadass |straight up |honestly |lately )?"
    r")",
    re.I
)

# ── 4. Emotion / state vocabulary ─────────────────────────────────────────────
# Organized by cluster so we can map to warm reflection language.
# Every word here produces "feeling {word}" as the extracted phrase.

_EMOTION_WORDS = (
    # ─── Sadness / grief ───
    "sad|sadder|saddest|unhappy|tearful|weepy|crying|cried|sobbing|"
    "heartbroken|brokenhearted|grief|grieving|mourning|bereaved|"
    "melancholy|blue|bummed|gutted|devastated|crushed|"
    # ─── Depression / low energy ───
    "depressed|depressing|low|down|flat|blah|meh|empty|hollow|void|"
    "numb|numbed|apathetic|indifferent|lifeless|zombie|dead inside|"
    "unmotivated|demotivated|lethargic|sluggish|"
    # ─── Anxiety / fear / panic ───
    "anxious|anxiety|worried|worrying|nervous|uneasy|unsettled|on edge|"
    "panicking|panicked|panic|freaking out|freaked out|"
    "scared|afraid|terrified|petrified|fearful|dread|dreading|paranoid|"
    "hypervigilant|jittery|shaky|tense|wound up|wired|"
    # ─── Anger / frustration ───
    "angry|mad|furious|livid|enraged|pissed|pissed off|irritated|"
    "frustrated|annoyed|agitated|bitter|resentful|rageful|snappy|short fuse|"
    "heated|fuming|seething|"
    # ─── Overwhelm / burnout ───
    "overwhelmed|overloaded|swamped|buried|drowning|suffocating|"
    "burned out|burnt out|burnout|exhausted|wiped|wiped out|"
    "spent|depleted|fried|cooked|done|over it|at capacity|maxed out|"
    "running on empty|running on fumes|spread thin|stretched thin|"
    # ─── Tiredness / fatigue ───
    "tired|fatigued|drained|beat|beaten down|weary|worn out|worn down|"
    "run down|rundown|sleepless|sleep deprived|"
    # ─── Loneliness / isolation ───
    "lonely|lonesome|alone|isolated|abandoned|forgotten|invisible|"
    "left out|excluded|disconnected|detached|withdrawn|"
    # ─── Shame / guilt / worthlessness ───
    "ashamed|shameful|guilty|worthless|useless|pathetic|inadequate|"
    "not good enough|not enough|failure|like a failure|loser|"
    "disgusted with myself|hate myself|self loathing|"
    # ─── Hopelessness / despair ───
    "hopeless|helpless|powerless|trapped|stuck|cornered|"
    "defeated|broken|shattered|destroyed|wrecked|ruined|"
    "lost|aimless|directionless|purposeless|"
    # ─── Hurt / betrayal ───
    "hurt|hurting|wounded|betrayed|backstabbed|used|manipulated|"
    "taken advantage of|let down|disappointed|"
    # ─── Stress / pressure ───
    "stressed|stressing|stressed out|under pressure|pressured|"
    "tense|strung out|uptight|freaking|stressful|"
    # ─── Confusion / disorientation ───
    "confused|lost|foggy|brain fog|scattered|spacey|dissociating|"
    "dissociated|out of it|zoned out|checked out|"
    # ─── Functional impairment ───
    "struggling|suffering|barely functioning|barely coping|"
    "falling apart|coming undone|unraveling|spiraling|sinking|"
    "crumbling|imploding|shutting down|shutdown|"
    # ─── Relational / social pain ───
    "rejected|neglected|unwanted|unlovable|unworthy|"
    "misunderstood|unseen|unheard|invalidated|dismissed|"
    "toxic|abused|gaslighted|gaslit|"
    # ─── Informal / slang ───
    "shitty|crappy|trash|garbage|awful|terrible|horrible|"
    "godawful|atrocious|horrendous|heinous|brutal|rough|tough|"
    "bad|worse|worst|like shit|like crap|like hell|"
    "in a funk|in a rut|in a hole|in a dark place|off|not right|"
    "not okay|not ok|not myself|not me|not great|not good|"
    # ─── Gen Z / TikTok / internet ───
    "unwell|feral|unhinged|chaotic|a mess|a wreck|a disaster|"
    "down bad|not it|giving depression|in my flop era|"
    "mentally checked out|over everything|so done|"
    # ─── Body / somatic ───
    "sick|nauseous|dizzy|headache|chest tight|can't breathe|"
    "heart racing|stomach in knots|can't eat|can't sleep|insomnia|"
    "nightmares|restless|agitated|crawling out of my skin|"
    # ─── Trauma / PTSD ───
    "traumatized|triggered|on guard|flashback|flashbacks|"
    "hyperaroused|hyperarousal|"
    # ─── Recovery / relapse ───
    "relapsing|relapsed|slipping|tempted|craving|"
    "close to using|want to drink|want to use|"
    # ─── Miscellanea ───
    "bored|restless|antsy|fidgety|distracted|"
    "regretful|nostalgic|homesick|jealous|envious|insecure|"
    "vulnerable|fragile|raw|tender|sensitive|"
    "weird|off|different|strange|out of sorts"
)

_EMOTION_RE = re.compile(
    r"\b(" + _EMOTION_WORDS + r")\b",
    re.I
)

# ── 5. Rephrase map for emotion catch-all ────────────────────────────────────
# Words that sound wrong with "feeling X" get remapped.

_REPHRASE = {
    # Gerunds that sound better as nouns
    "struggling": "the struggle",
    "crying": "the crying",
    "sobbing": "the sobbing",
    "slipping": "slipping",
    "relapsing": "the relapse risk",
    "spiraling": "the spiral",
    "unraveling": "unraveling",
    "crumbling": "crumbling",
    "imploding": "falling apart",
    "sinking": "sinking",
    "drowning": "drowning",
    "suffocating": "suffocating",
    "panicking": "the panic",
    "dissociating": "the dissociation",
    "trembling": "the shaking",
    "shaking": "the shaking",
    # Nouns that sound better with "the"
    "nightmares": "the nightmares",
    "flashbacks": "the flashbacks",
    "flashback": "the flashbacks",
    "insomnia": "the insomnia",
    "grief": "the grief",
    "burnout": "the burnout",
    "trauma": "the trauma",
    "dread": "the dread",
    "panic": "the panic",
    "anxiety": "the anxiety",
    "depression": "the depression",
    # Multi-word entries that need rephrasing
    "dead inside": "feeling dead inside",
    "a mess": "being a mess",
    "a wreck": "being a wreck",
    "a disaster": "being a disaster",
    "giving depression": "the depression",
    "down bad": "being down bad",
    "in my flop era": "this season",
    "running on empty": "running on empty",
    "running on fumes": "running on fumes",
    "crawling out of my skin": "crawling out of your skin",
    "stomach in knots": "the knots in your stomach",
    "heart racing": "your heart racing",
    "want to drink": "wanting to drink",
    "want to use": "wanting to use",
    "close to using": "being close to using",
    "like a failure": "feeling like a failure",
    "not good enough": "feeling not good enough",
    "not enough": "feeling not enough",
    "like shit": "feeling like shit",
    "like crap": "feeling like crap",
    "like hell": "feeling like hell",
    "worse": "things getting worse",
    "worst": "how hard things have been",
    "falling apart": "falling apart",
    "coming undone": "coming undone",
}


def _format_emotion(word: str) -> str:
    """Format an emotion word into a natural-sounding phrase."""
    if word in _REPHRASE:
        return _REPHRASE[word]
    # Already sounds ok with "feeling" for adjectives/states
    return f"feeling {word}"


# ── 6. Structured extraction patterns (ordered by specificity) ────────────────

_EMOTION_PHRASES = [
    # "lost/losing my ___" (grief, tangible loss)
    (re.compile(r"\b(?:lost|losing|lose)\s+(?:my|a)\s+(\w+(?:\s+\w+)?)", re.I),
     lambda m: f"losing your {m.group(1)}"),

    # "worried/scared/afraid about/of ___"
    (re.compile(r"\b(worried|worrying|scared|terrified|afraid|nervous|anxious|dreading|paranoid|freaking out)\s+(?:about|of|for|that)\s+(.+?)(?:[.,!?]|$)", re.I),
     lambda m: f"{m.group(1).lower()} about {m.group(2).strip().rstrip('.,!?')}"),

    # "struggling/dealing with ___"
    (re.compile(r"\b(?:struggling|dealing|coping|living)\s+with\s+(.+?)(?:[.,!?]|$)", re.I),
     lambda m: m.group(1).strip().rstrip(".,!?")),

    # "can't sleep/eat/focus/breathe/think/function/concentrate/relax/stop"
    (re.compile(r"\b(?:can't|cant|cannot|can not|couldn't|couldnt|unable to)\s+(sleep|eat|focus|breathe|think|function|concentrate|relax|stop\s+\w+|get\s+(?:up|out of bed)|move|work|study|leave\s+(?:the\s+)?(?:house|bed|room))", re.I),
     lambda m: f"not being able to {m.group(1).lower()}"),

    # "my [relationship person] is/has been ___"
    (re.compile(r"\b(?:my\s+)?(marriage|relationship|partner|husband|wife|boyfriend|girlfriend|gf|bf|fiancee?|spouse|ex|situationship)\s+(?:is|has been|keeps?|won't|just|recently)\s+(.+?)(?:[.,!?]|$)", re.I),
     lambda m: f"what's going on with your {m.group(1).lower()}"),

    # "my [family/person] is/has been ___"
    (re.compile(r"\b(?:my\s+)(kid|kids|child|children|son|daughter|mom|mother|dad|father|parent|parents|brother|sister|sibling|friend|best friend|boss|coworker|roommate|family)\b.*?(?:is|are|has been|have been|keeps?|won't|doesn't|doesn't)\s+(.+?)(?:[.,!?]|$)", re.I),
     lambda m: f"what's happening with your {m.group(1).lower()}"),

    # "going through ___"
    (re.compile(r"\bgoing\s+through\s+(.+?)(?:[.,!?]|$)", re.I),
     lambda m: f"going through {m.group(1).strip().rstrip('.,!?')}"),

    # "[work/school/money] stress" (bidirectional)
    (re.compile(r"\b(work|job|career|school|college|university|money|finances?|debt|bills?|rent|mortgage)\b.*(?:stress|hard|difficult|killing|draining|toxic|nightmare|hell|sucks|awful|terrible|unbearable)", re.I),
     lambda m: f"the {m.group(1).lower()} stress"),
    (re.compile(r"(?:stress|hard|difficult|killing|draining|toxic|nightmare|hell|sucks|awful|terrible|unbearable).*\b(work|job|career|school|college|university|money|finances?|debt|bills?|rent|mortgage)\b", re.I),
     lambda m: f"the {m.group(1).lower()} stress"),

    # "everything / nothing" existential statements
    (re.compile(r"\beverything\s+(?:is|feels?|seems?)\s+(pointless|meaningless|hopeless|too much|overwhelming|falling apart|wrong|broken)", re.I),
     lambda m: f"everything feeling {m.group(1).lower()}"),
    (re.compile(r"\bnothing\s+(?:is|feels?|seems?|ever)\s+(working|getting better|changing|worth it|right|good|okay|enough)", re.I),
     lambda m: f"nothing feeling like it's {m.group(1).lower()}"),

    # "keep/can't stop [negative thing]" -- restricted to known negative objects
    (re.compile(r"\b(?:i\s+)?(?:keep|keeps|can't stop|cant stop|won't stop|wont stop)\s+(?:having\s+)?(nightmares?|panic\s+attacks?|flashbacks?|breakdowns?|anxiety|bad\s+thoughts?|intrusive\s+thoughts?|crying|sobbing|screaming|shaking|trembling|thinking\s+about)", re.I),
     lambda m: f"the {m.group(1).strip().lower()}"),

    # "giving X vibes/energy" (Gen Z construction)
    (re.compile(r"\bgiving\s+(\w+)\s*(?:vibes?|energy|feels?)\b", re.I),
     lambda m: _format_emotion(m.group(1).lower())),

    # "why am I / why do I" (confusion about own state)
    (re.compile(r"\bwhy\s+(?:am|do|can't|cant)\s+i\s+(.+?)(?:[.,!?]|$)", re.I),
     lambda m: f"not knowing why you {m.group(1).strip().rstrip('.,!?').lower()}"),

    # "close to / about to [verb]ing" (relapse, breaking, etc.)
    (re.compile(r"\b(?:close to|about to|on the verge of|ready to|almost)\s+(\w+ing\b(?:\s+\w+)?)", re.I),
     lambda m: f"being close to {m.group(1).strip().lower()}"),

    # "don't want to [do anything/get up/move/etc.]" (functional impairment)
    (re.compile(r"\bdon't\s+want\s+to\s+(do\s+anything|get\s+(?:up|out\s+of\s+bed)|move|eat|go\s+(?:anywhere|outside|to\s+\w+)|talk\s+to\s+anyone|see\s+anyone|leave|be\s+around\s+(?:people|anyone))", re.I),
     lambda m: f"not wanting to {m.group(1).lower()}"),

    # Emotion word catch-all (the big vocabulary list)
    (_EMOTION_RE,
     lambda m: _format_emotion(m.group(1).lower())),
]


def extract_key_phrase(user_text: str) -> Optional[str]:
    """Pull the emotional/situational core from user input.

    Returns a short phrase like "losing your dad", "the work stress",
    "not being able to sleep", or None if nothing specific found.

    Handles:
    - Standard English, informal, text-speak, Gen Z slang
    - Common misspellings and missing apostrophes
    - Filler/hedge stripping
    - Structured extraction (relationships, loss, can't X, etc.)
    - 200+ emotion/state words as catch-all
    """
    if not user_text or len(user_text.strip()) < 2:
        return None

    text = user_text.strip()

    # Guard: if the message is primarily a medication question, return None
    # so we get a warm fallback instead of parroting drug names back.
    if _MEDS_GUARD_RE.search(text):
        return None

    # Guard: if the message is an identity statement, return None
    # so templates never pathologize who someone is.
    if _IDENTITY_GUARD_RE.search(text):
        return None

    # Normalize misspellings and text-speak before extraction
    text = _normalize_text(text)

    # Try structured extraction first (most specific patterns win)
    for pattern, formatter in _EMOTION_PHRASES:
        m = pattern.search(text)
        if m:
            phrase = formatter(m)
            phrase = phrase.strip().rstrip(".,!?")
            if len(phrase) > 60:
                phrase = phrase[:57] + "..."
            return phrase

    # Fallback: strip filler and use a shortened version
    cleaned = _FILLER.sub("", text).strip()
    cleaned = _OPENERS.sub("", cleaned).strip()

    if cleaned and len(cleaned) > 3:
        # Take first clause (before comma, period, or "and")
        clause = re.split(r"[,.]|\band\b", cleaned, maxsplit=1)[0].strip()
        if len(clause) > 3:
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
