"""
Conversation engine for the Clinical Conversation Engine.
Manages sessions, tree navigation, topic detection, scoring, and outcome generation.

Q8/Q5 Safety Question Scoring Divergence:
  The safety/self-harm question appears in two contexts with different scoring:
  - CCE trees.json (Q8): [0, 2, 3, 4]  (score_key="safety", is_crisis_check=true)
  - Frontend quiz (Q5):  [0, 1, 2, 3]  (standard 0-3 scale, Q5 override rules apply)
  The override mapping at line ~232 normalizes both q5 and q8 to score_key "safety"
  so that QUIZ_SCORING_OVERRIDES fire correctly for either path.
"""
import json
import logging
import os
import re
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .crisis import is_crisis_option, is_crisis_text, is_critical_override_text
from . import metrics
from .config import (
    get_guide_for_topic, get_offer_for_risk, get_offer_for_guide, resolve_guide_path,
    GUIDES_BY_ID, AUDIENCE_BUCKETS, AUDIENCE_QUESTIONS,
    QUIZ_SCORING_RANGES, QUIZ_SCORING_OVERRIDES,
)
from .audience_matcher import (
    detect_audience_buckets, get_audience_question, get_audience_options,
    resolve_bucket, resolve_option_to_bucket,
)
from .personalizer import (
    personalize_negative_probe, personalize_positive_probe,
    personalize_clarification, personalize_deepening, personalize_goal_clarify,
    personalize_positive_deepening, personalize_positive_goal_clarify,
)
from .llm_responder import (
    generate_negative_probe, generate_deepening, generate_goal_clarify,
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

# ─── Session store (in-memory cache + file persistence) ────────────────────────

_SESSIONS: Dict[str, SessionState] = {}
_SESSION_DIR = Path(os.environ.get("CCE_SESSION_DIR", DATA_DIR / ".sessions"))
_SESSION_DIR.mkdir(parents=True, exist_ok=True)


def _save_session(session: SessionState) -> None:
    """Write session to in-memory cache and persist to disk."""
    _SESSIONS[session.session_id] = session
    path = _SESSION_DIR / f"{session.session_id}.json"
    path.write_text(session.model_dump_json(), encoding="utf-8")


def _load_session(session_id: str) -> Optional[SessionState]:
    """Load session from cache, falling back to disk."""
    if session_id in _SESSIONS:
        return _SESSIONS[session_id]
    path = _SESSION_DIR / f"{session_id}.json"
    if path.exists():
        session = SessionState.model_validate_json(path.read_text(encoding="utf-8"))
        _SESSIONS[session_id] = session
        return session
    return None



# ═══════════════════════════════════════════════════════════════════════════════
# SENTIMENT CLASSIFICATION
# Handles: clinical language, casual speech, slang, text speak, Gen Z / TikTok
# speak, sarcasm, dark humor, understatement, coded distress, deflection.
#
# Priority order (first match wins):
#   1. Crisis language        -> negative (safety-critical, always first)
#   2. Sarcasm / ironic pos   -> negative
#   3. Dark humor / gallows   -> negative
#   4. Dismissive / shutdown  -> negative
#   5. Contradiction / mask   -> negative
#   6. Slang / text negatives -> negative
#   7. Idiomatic negatives    -> negative
#   8. Idiomatic neutrals     -> neutral
#   9. Word-by-word scoring   -> positive / neutral / negative
# ═══════════════════════════════════════════════════════════════════════════════

# ─── Word lists ────────────────────────────────────────────────────────────────

POS_WORDS = {
    "good","great","well","happy","grateful","amazing",
    "positive","blessed","thankful","improving","hopeful","excited",
    "love","wonderful","fantastic","relief","relieved","stable","managing",
    "awesome","excellent","thriving","content","peaceful","strong",
    "proud","joyful","motivated","energized","optimistic","stoked",
    "pumped","hyped","confident","secure","supported","valued",
}

# Context-dependent positives: only score +1 when preceded by an amplifier.
# "better" alone is ambiguous ("been better" = negative, "much better" = positive).
CONTEXT_POS_WORDS = {"better"}
CONTEXT_POS_AMPLIFIERS = {
    "much","lot","so","way","really","actually","definitely",
    "feeling","doing","getting","significantly","truly","genuinely",
    "alot","tons","a",
}

# Words that sound positive but are often dismissive/neutral
SOFT_POS_WORDS = {"fine","okay","alright","ok","decent","surviving","hanging",
                  "coping","functioning","existing","aight","ight"}

NEG_WORDS = {
    # Core emotional states
    "bad","terrible","awful","horrible","worst","sad","depressed","anxious",
    "scared","overwhelming","overwhelmed","hopeless","exhausted","lonely",
    "miserable","struggling","suffering","broken","lost","empty","numb","stuck",
    "angry","frustrated","hurt","stressed","worried","afraid","panic","grief",
    "crying","dark","heavy","drained","worthless","failure","useless",
    "rough","tough","hard","difficult","painful","tired","sucks","hate",
    "drowning","crumbling","shattered","defeated","ruined","wrecked","dying",
    # Crisis / self-harm adjacent (individual words)
    "die","dead","kill","suicidal","trauma","traumatized","triggered",
    "paranoid","spiraling","panicking","hyperventilating","dissociating",
    "relapsing","relapsed","cutting","harming","burning",
    "sleepless","insomnia","nightmare","nightmares",
    # Social / relational pain
    "isolated","abandoned","rejected","betrayed","neglected","abused",
    "toxic","unbearable","insufferable","intolerable","agonizing",
    "devastated","destroyed","gutted","crushed","wasted","trashed",
    # Functional impairment
    "failing","sinking","suffocating","choking","screaming","sobbing",
    "shaking","trembling","frozen","paralyzed","shutdown","dissociated",
    # Informal / slang negative
    "crappy","shitty","trash","garbage","hellish","brutal",
    "heinous","godawful","horrendous","atrocious","pathetic",
    "wack","whack",
    # Expanded: anxiety / fear / panic
    "anxiety","nervous","uneasy","unsettled","dread","dreading","fearful",
    "terrified","petrified","panicked","hypervigilant","shaky","agitated",
    # Expanded: anger / frustration
    "mad","furious","livid","enraged","irritated","annoyed","bitter",
    "resentful","rageful","pissed",
    # Expanded: shame / guilt / worthlessness
    "ashamed","shameful","guilty","inadequate","powerless","helpless",
    # Expanded: sadness / grief / loss
    "unhappy","tearful","weepy","heartbroken","brokenhearted","grieving",
    "mourning","bereaved","melancholy","bummed","depressing",
    "sadder","saddest","cried","disappointed",
    # Expanded: overwhelm / burnout / fatigue
    "overloaded","swamped","buried","burnout","depleted",
    "fatigued","lethargic","sluggish","demotivated","unmotivated",
    # Expanded: loneliness / isolation / dismissal
    "alone","lonesome","excluded","disconnected","forgotten","invisible",
    "dismissed","invalidated","unseen","unheard","misunderstood",
    # Expanded: relational pain
    "manipulated","gaslighted","gaslit","backstabbed","unwanted",
    "unlovable","unworthy","used",
    # Expanded: trapped / stuck / cornered
    "trapped","cornered","pressured","uptight","stressing","stressful",
    # Expanded: functional / body
    "hurting","imploding","unraveling","slipping","numbed",
    "indifferent","apathetic","lifeless","confused",
    "nauseous","dizzy","headache","sick","freaking","worse",
    "loser","rundown",
}

NEGATORS = {"not","no","never","don't","doesn't","can't","cannot","nor","ain't",
            "don\u2019t","doesn\u2019t","can\u2019t","cant","dont","doesnt",
            "wont","won\u2019t","won't","barely","hardly","scarcely"}

# Hedging/uncertainty markers (signal person isn't truly positive)
HEDGE_WORDS = {"idk","dunno","maybe","kinda","sorta","ish","meh","whatever",
               "guess","suppose","shrug","eh","blah","tbh","honestly",
               "but","except","though","however","yet","ngl","lowkey","ion",
               "idrk","prolly","prob","possibly","apparently","supposedly"}

# ─── 1. CRISIS LANGUAGE (safety-critical, always checked first) ────────────────

CRISIS_RE = re.compile(
    r"(?:"
    # Direct suicidal ideation
    r"(?:i\s+)?(?:want|wanna|need|going|gonna|ready|planning|trying|about)"
    r"\s+(?:to\s+)?(?:die|end\s+(?:it|my\s+life|everything)|kill\s+my\s*self"
    r"|off\s+my\s*self|not\s+(?:be\s+)?(?:here|alive|around))"
    # "don't want to be here/alive/exist"
    r"|don['\u2019]?t\s+(?:want|wanna|deserve)\s+to\s+(?:be\s+(?:here|alive)|exist|live|wake\s+up)"
    r"|(?:wish|wished)\s+(?:i\s+)?(?:was(?:n['\u2019]?t\s+(?:here|alive|born))|were\s+dead"
    r"|could\s+(?:disappear|vanish|just\s+not\s+exist))"
    # "better off without me"
    r"|better\s+off\s+(?:without\s+me|if\s+i)"
    r"|(?:world|everyone|they|family)\s+(?:would\s+be\s+)?better\s+off"
    r"|no\s*one\s+(?:would\s+)?(?:care|notice|miss)"
    # "what's the point"
    r"|what['\u2019]?s\s+the\s+(?:point|purpose|use)"
    r"|(?:there\s*(?:is|'s)\s+)?no\s+(?:point|reason|purpose|hope)"
    # Plans / preparation
    r"|(?:have|got|made)\s+a\s+plan"
    r"|wrote\s+(?:a\s+)?(?:note|letter|goodbye)"
    r"|(?:giving|gave)\s+(?:away\s+)?(?:my\s+)?(?:stuff|things|belongings)"
    r"|(?:saying|said)\s+(?:my\s+)?goodbye"
    # Slang / coded crisis (TikTok censorship workarounds)
    r"|(?:km+s|kmy?self|unalive|un\s*alive|sewerslide|sewer\s*slide|su[i1]c[i1]de|seggs\s*cide)"
    r"|(?:gonna\s+)?(?:off|alt[- ]?f4|ctrl[- ]?z|log\s*off|peace\s*out|check\s*out)"
    r"\s+(?:my\s*self|myself|forever|for\s+good|permanently)"
    r"|(?:catch(?:ing)?\s+(?:the|a)\s+)?(?:bus|train)\s*(?:to\s+(?:heaven|the\s+other\s+side))?"
    r"|(?:final|forever|last|eternal|permanent)\s+(?:nap|sleep|rest|goodbye|peace)"
    r"|(?:i(?:['\u2019]?m)?\s+)?(?:done|finished|over)\s+(?:with\s+)?(?:everything|it\s+all|life|this|living)"
    r")",
    re.IGNORECASE,
)

# ─── 2. SARCASM / IRONIC POSITIVITY ───────────────────────────────────────────

SARCASM_RE = re.compile(
    r"(?:"
    # Classic sarcastic phrases
    r"living\s+the\s+dream"
    r"|just\s+(?:great|wonderful|fantastic|perfect|peachy|dandy|swell|lovely|splendid)"
    r"|couldn['\u2019]?t\s+be\s+better"
    r"|never\s+been\s+better"
    r"|oh?\s+(?:just\s+)?(?:great|wonderful|fantastic|perfect|lovely|joy)"
    r"|totally\s+(?:fine|great|amazing|awesome|normal|cool)"
    r"|absolutely\s+(?:fantastic|wonderful|amazing|thrilled|loving\s+(?:it|this|life))"
    r"|(?:fan-?tastic|won-?derful|amaz-?ing)\s*[\.!]{2,}"
    # Sarcastic "love" / "fun"
    r"|(?:love|loving)\s+(?:this|that|it)\s+(?:for\s+me|rn|right\s+now)"
    r"|(?:so\s+)?fun\s*[\.\!]"
    r"|what\s+(?:a\s+)?(?:joy|treat|delight|blast|time\s+to\s+be\s+alive)"
    # Laughter + "fine/good" combos
    r"|(?:lol|lmao|lmfao|haha|hehe|rofl)\s*(?:i['\u2019]?m\s+)?(?:fine|good|great|ok(?:ay)?|dead|dying)"
    r"|(?:fine|good|great|ok(?:ay)?)\s+(?:lol|lmao|lmfao|haha|hehe|rofl)"
    r"|(?:sure|yeah|yep|yup|mhm)\s+(?:fine|good|great|whatever)"
    # "everything is fine" (dog in burning room energy)
    r"|everything\s*(?:is|'s)?\s*(?:just\s+)?(?:fine|great|perfect|wonderful|normal)"
    r"|this\s+is\s+(?:fine|normal|great)"
    # "blessed" sarcasm
    r"|(?:truly|so)\s+blessed"
    r"|hashtag\s*blessed"
    # Gen Z sarcastic constructions
    r"|(?:it['\u2019]?s\s+)?giving\s+(?:main\s+character|protagonist|delusion|delusional|pick\s+me)"
    r"|not\s+me\s+(?:being|pretending|acting\s+like|thinking)"
    r"|me\s+(?:when|after|watching)\s+(?:my\s+)?(?:life|everything)\s+(?:fall|crash|burn)"
    r"|(?:real|very)\s+normal\s+(?:behavior|thing|stuff|response|reaction)"
    # Deadpan / flat delivery markers
    r"|(?:ha|cool|great|nice|neat|swell|super|wow)\s*\.\s*$"
    r")",
    re.IGNORECASE,
)

# ─── 3. DARK HUMOR / GALLOWS HUMOR ────────────────────────────────────────────

DARK_HUMOR_RE = re.compile(
    r"(?:"
    r"(?:kill(?:ing)?\s+(?:it|me)|dying\s+(?:here|inside|slowly|rn))"
    r"|(?:i(?:['\u2019]?m)?\s+)?dead\s+(?:inside|ass|serious|fr|for\s+real)"
    r"|(?:lol|lmao|haha)?\s*(?:i(?:['\u2019]?m)?\s+)?(?:crying|screaming|deceased|sobbing)"
    r"|(?:crying|screaming|sobbing)\s+(?:lol|lmao|haha|rn|fr)"
    r"|(?:someone|please|pls|plz)\s+(?:help|save)\s+me"
    r"|(?:send|need)\s+(?:help|prayers|thoughts|vibes)"
    r"|(?:this|my\s+life)\s+is\s+(?:a\s+)?(?:joke|disaster|dumpster\s+fire|train\s*wreck|mess|chaos)"
    r"|dumpster\s*fire"
    r"|train\s*wreck"
    r"|(?:clown|circus|joke)\s+(?:energy|vibes|hours|moment|era)"
    r"|(?:it['\u2019]?s\s+)?giving\s+(?:unhinged|unstable|chaotic|feral|fml|depression|anxiety|mental\s*(?:break|illness))"
    r"|(?:i(?:['\u2019]?m)?\s+)?(?:such\s+a\s+)?(?:mess|wreck|disaster|trainwreck|dumpster\s*fire)"
    r"|(?:haha|lol)?\s*(?:fml|kill\s+me|end\s+me|shoot\s+me)"
    r")",
    re.IGNORECASE,
)

# ─── 4. DISMISSIVE / SHUTDOWN ─────────────────────────────────────────────────

DISMISSIVE_RE = re.compile(
    r"(?:"
    # Single-word shutdowns
    r"^(?:idk|meh|whatever|eh|blah|nah|nope|no|k|nm|nth|nun|nothin|nada|zip|zilch)\s*$"
    # "don't know/care/wanna"
    r"|don['\u2019]?t\s+(?:know|care|wanna|want\s+to|feel\s+like)"
    r"|(?:i\s+)?(?:cant|can\u2019t|can't)\s+(?:even|deal|rn|anymore|today)"
    r"|who\s+(?:cares|knows|asked)"
    r"|does(?:n['\u2019]?t)?\s+(?:matter|make\s+a\s+difference)"
    # Stagnation
    r"|same\s+(?:old|shit|crap|stuff|bs)"
    r"|nothing\s+(?:new|special|good|matters|changed|ever\s+changes)"
    r"|it\s+is\s+what\s+it\s+is"
    r"|whatever\s+(?:happens|man|dude|bro|bruh)"
    # "leave me alone" energy
    r"|(?:just\s+)?(?:leave|let)\s+me\s+(?:alone|be)"
    r"|(?:i\s+)?(?:don['\u2019]?t|do\s+not)\s+(?:want\s+to\s+)?talk\s+(?:about\s+it|rn)"
    r"|not\s+(?:now|today|in\s+the\s+mood)"
    # Text speak dismissals
    r"|^(?:nm|nmu|nun|nth|nada|idc|idek|idfk|idgaf)\s*$"
    r")",
    re.IGNORECASE,
)

# ─── 5. CONTRADICTION / MASKING ───────────────────────────────────────────────

CONTRADICTION_RE = re.compile(
    r"(?:"
    r"on\s+the\s+outside.*on\s+the\s+inside"
    r"|no\s+(?:actually|wait|really)\s+i[''\u2019]?m?\s+not"
    r"|i[''\u2019]?m\s+(?:good|fine|great|ok(?:ay)?).*(?:actually|no|not\s+really)\s+i[''\u2019]?m?\s+not"
    r"|actually\s+(?:i[''\u2019]?m|things?\s+(?:are|is))\s+not"
    # "I say I'm fine but"
    r"|(?:i\s+)?(?:say|said|tell|told)\s+(?:everyone|people|them)?\s*(?:i[''\u2019]?m\s+)?(?:fine|ok(?:ay)?|good)\s+but"
    # Masking
    r"|(?:putting\s+on|wearing)\s+(?:a\s+)?(?:brave|happy|fake)\s+(?:face|mask|front)"
    r"|(?:fake|forced|plastic)\s+(?:smile|laugh|happy)"
    r"|(?:pretend(?:ing)?|act(?:ing)?)\s+(?:like\s+)?(?:i[''\u2019]?m\s+)?(?:fine|ok(?:ay)?|good|happy|normal)"
    r"|(?:pretend(?:ing)?|act(?:ing)?)\s+(?:to\s+be\s+)?(?:fine|ok(?:ay)?|good|happy|normal)"
    r"|(?:nobody|no\s*one)\s+(?:knows|sees|realizes)\s+(?:how\s+(?:bad|hard)|what)"
    r")",
    re.IGNORECASE,
)

# ─── 6. SLANG / TEXT SPEAK / GEN Z / TIKTOK ───────────────────────────────────

SLANG_NEGATIVE_RE = re.compile(
    r"(?:"
    # Text abbreviations signaling distress
    r"(?:^|\s)(?:fml|smh|smfh|jfc|omfg|bruh|ugh+|gah)\s*$"
    r"|(?:i(?:['\u2019]?m)?\s+)?(?:so\s+)?(?:over\s+(?:it|this|everything)|done|cooked)"
    # Gen Z / TikTok distress language
    r"|(?:it['\u2019]?s\s+)?(?:giving|very|lowkey|highkey|deadass|fr|no\s+cap)"
    r"\s+(?:sad|depressed|depressing|anxiety|anxious|trauma|pain|struggle|suffering"
    r"|hopeless|helpless|bleak|misery|miserable|exhausting|draining|death"
    r"|breakdown|meltdown|panic|stress|rough|bad|terrible|awful|dark|heavy)"
    # "lowkey/highkey" + negative
    r"|(?:lowkey|highkey|deadass|fr\s+fr|no\s+cap)\s+(?:not\s+(?:ok(?:ay)?|doing\s+(?:well|good))"
    r"|(?:struggling|dying|suffering|depressed|anxious|losing\s+it|falling\s+apart|breaking\s+down))"
    # "ngl" + negative state
    r"|ngl\s+(?:i(?:['\u2019]?m)?\s+)?(?:not\s+(?:ok(?:ay)?|doing\s+(?:well|good))"
    r"|(?:struggling|hurting|scared|worried|stressed|exhausted|miserable|sad|depressed|anxious"
    r"|having\s+a\s+(?:hard|rough|tough|bad)\s+(?:time|day|week|month|year)))"
    # "not gonna lie / ngl / tbh / real talk" + honesty signal
    r"|(?:not\s+(?:gonna|going\s+to)\s+lie|ngl|tbh|honestly|real\s+talk|fr)\s*[,:]?\s*"
    r"(?:(?:i(?:['\u2019]?m|\s+am)?\s+)?(?:not\s+(?:good|great|ok(?:ay)?|doing\s+well)"
    r"|(?:struggling|hurting|scared|messed\s+up|falling\s+apart|breaking)))"
    # "I'm literally/actually" + negative
    r"|(?:i(?:['\u2019]?m)?\s+)?(?:literally|actually|genuinely|legit|deadass|straight\s+up)"
    r"\s+(?:dying|dead|broken|shattered|falling\s+apart|losing\s+(?:it|my\s+mind)"
    r"|going\s+(?:crazy|insane|mental)|about\s+to\s+(?:snap|lose\s+it|break|crack))"
    # "vibes are off"
    r"|(?:the\s+)?(?:vibes?|energy|mood)\s+(?:is|are)\s+(?:off|bad|low|dark|heavy|dead|gone|not\s+it)"
    r"|(?:bad|dark|heavy|low|negative|off|weird|wrong)\s+(?:vibes?|energy)"
    # "in my ___ era" (negative version)
    r"|(?:in\s+)?my\s+(?:(?:villain|sad|depressed|crying|breakdown|flop|failure|isolation|hermit"
    r"|dark|rock\s+bottom|giving\s+up|burnt?\s+out|over\s+it)\s+era)"
    # "rent free" (negative things occupying mind)
    r"|(?:anxiety|depression|trauma|panic|dread|fear|worry|stress)\s+(?:living\s+)?rent\s+free"
    # General slang intensifiers + negative state
    r"|(?:big|huge|major|massive)\s+(?:sad|oof|yikes|ick|L|loss|fail)"
    r"|(?:that['\u2019]?s|this\s+is)\s+(?:an?\s+)?(?:L|loss|fail|oof|yikes)"
    r"|(?:caught|taking|catching)\s+(?:an?\s+)?(?:L|loss)"
    r"|down\s+(?:bad|horrendous|terrible|astronomical)"
    r"|(?:i(?:['\u2019]?m)?\s+)?(?:tweaking|spiraling|unraveling|imploding|crumbling)"
    r")",
    re.IGNORECASE,
)

# ─── 7. IDIOMATIC NEGATIVES ───────────────────────────────────────────────────

_IDIOM_NEGATIVE = re.compile(
    r"(?:"
    # "been better" family
    r"(?:i['\u2019]?ve\s+)?been\s+better"
    r"|could\s+(?:be|have\s+been)\s+better"
    r"|seen\s+better\s+days"
    r"|had\s+better\s+days"
    r"|known\s+better\s+days"
    # "not great/good"
    r"|not\s+(?:the\s+)?(?:great|best|greatest|good)"
    r"|not\s+(?:my|the)\s+best"
    # "hanging by a thread"
    r"|hanging\s+(?:by\s+a\s+thread|on\s+(?:by\s+a\s+thread|barely))"
    r"|barely\s+(?:holding|hanging|making|getting|keeping|functioning|surviving)"
    r"|just\s+barely"
    # "better than" deflections
    r"|better\s+than\s+(?:yesterday|last\s+(?:week|time|night)|nothing|dead|before)"
    # Survival language
    r"|just\s+(?:getting|trying\s+to\s+get)\s+(?:by|through)"
    r"|one\s+day\s+at\s+a\s+time"
    r"|taking\s+it\s+(?:one\s+)?day\s+(?:by|at)\s+(?:a\s+)?(?:day|time)"
    # Exhaustion idioms
    r"|running\s+on\s+(?:empty|fumes)"
    r"|(?:at|reached?)\s+(?:my|the)\s+(?:(?:end\s+of\s+(?:my|the)\s+)?(?:rope|wits?|tether|limit|breaking\s+point))"
    r"|end\s+of\s+my\s+rope"
    # "something's gotta give"
    r"|something['\u2019]?s\s+(?:gotta|got\s+to)\s+give"
    # "going through it"
    r"|going\s+through\s+(?:it|a\s+lot|some\s+stuff|something|hell|the\s+wringer)"
    r"|in\s+a\s+(?:rough|tough|bad|dark|hard|low|terrible|awful)\s+(?:patch|spot|place|way|space|headspace)"
    # "I'll be fine" / minimizing
    r"|i['\u2019]?ll\s+be\s+(?:fine|ok(?:ay)?|alright)"
    r"|i['\u2019]?ll\s+(?:get\s+(?:over|through)\s+it|manage|survive|live)"
    r"|(?:can['\u2019]?t|cant)\s+complain"
    # "at a loss" / "hit rock bottom"
    r"|(?:at|hit|reached?|rock)\s+(?:a\s+loss|rock\s+bottom|bottom|my\s+lowest)"
    r"|(?:rock|hit(?:ting)?)\s+bottom"
    # "falling apart"
    r"|(?:falling|coming|breaking|tearing)\s+(?:apart|undone|down|to\s+pieces)"
    r"|(?:held|holding|keeping)\s+(?:it\s+)?together\s+(?:barely|by\s+a\s+thread)"
    # Burnout idioms
    r"|(?:burning|burnt?|burned)\s+(?:out|the\s+candle)"
    r"|(?:spread|stretched|pulled)\s+(?:too\s+)?(?:thin|tight)"
    r"|(?:at\s+)?(?:my\s+)?(?:wits?|rope)['\u2019]?s?\s+end"
    # Darkness / weight metaphors
    r"|(?:dark|black|storm|grey|gray)\s+(?:cloud|clouds?|place|hole|pit|tunnel|fog)"
    r"|(?:can['\u2019]?t|cant)\s+(?:see\s+)?(?:the\s+)?light"
    r"|(?:in\s+)?(?:a\s+)?(?:fog|haze|funk|rut|hole|pit|spiral)"
    r"|(?:weight|world|everything)\s+(?:on\s+)?(?:my\s+)?shoulders"
    r"|carrying\s+(?:a\s+lot|too\s+much|the\s+weight|so\s+much)"
    # "don't worry about me"
    r"|don['\u2019]?t\s+worry\s+(?:about\s+me|i['\u2019]?m\s+(?:fine|ok))"
    # "I've had better"
    r"|i['\u2019]?ve\s+had\s+better"
    # "treading water"
    r"|(?:just\s+)?treading\s+water"
    r")",
    re.IGNORECASE,
)

# ─── 8. IDIOMATIC NEUTRALS ────────────────────────────────────────────────────

_IDIOM_NEUTRAL = re.compile(
    r"(?:"
    # "same as always"
    r"same\s+(?:as\s+(?:always|usual|ever)|old\s+same\s+old)"
    # "you know how it is"
    r"|you\s+know\s+how\s+it\s+(?:is|goes)"
    # "still here" (ambiguous)
    r"|(?:i['\u2019]?m\s+)?still\s+here"
    r"|still\s+(?:standing|breathing|kicking|going|alive)"
    # "not bad" (genuine middle ground)
    r"|not\s+(?:bad|terrible|awful|horrible|the\s+worst)"
    # "could be worse" (silver-lining, not positive)
    r"|could\s+(?:be|have\s+been)\s+worse"
    # "up and down"
    r"|up\s+and\s+down"
    r"|roller\s*coaster"
    r"|good\s+days\s+and\s+bad\s+days"
    r"|some\s+days\s+(?:are\s+)?(?:good|better|ok)"
    r"|mixed\s+(?:bag|feelings)"
    r"|depends\s+on\s+the\s+day"
    # Progress but not arrived
    r"|getting\s+there"
    r"|working\s+on\s+it"
    r"|(?:i['\u2019]?m\s+)?(?:trying|a\s+work\s+in\s+progress)"
    r"|taking\s+(?:it\s+)?(?:slow|easy|step\s+by\s+step)"
    # Noncommittal
    r"|(?:i\s+)?(?:don['\u2019]?t|do\s+not)\s+(?:even\s+)?know"
    r"|(?:hard|tough|difficult)\s+to\s+(?:say|tell|explain|describe)"
    r"|it['\u2019]?s\s+(?:complicated|complex|a\s+lot)"
    r")",
    re.IGNORECASE,
)


def _score_sentiment(text: str) -> str:
    """Return 'positive', 'neutral', or 'negative'.

    Handles clinical language, casual speech, slang, text speak, sarcasm,
    dark humor, Gen Z / TikTok language, coded distress, and idioms.

    When in doubt, defaults toward 'neutral' (routes to the not-good path).
    Only clearly positive language with no hedging/sarcasm routes positive.
    """
    lower = text.lower().strip()
    words = re.findall(r"[\w\u2019']+", lower)

    # 1. Crisis language (safety-critical, always first)
    if CRISIS_RE.search(lower):
        return "negative"

    # 2. Sarcasm / ironic positivity
    if SARCASM_RE.search(lower):
        return "negative"

    # 3. Dark humor / gallows humor
    if DARK_HUMOR_RE.search(lower):
        return "negative"

    # 4. Dismissive / shutdown
    if DISMISSIVE_RE.search(lower):
        return "negative"

    # 5. Contradiction / masking
    if CONTRADICTION_RE.search(lower):
        return "negative"

    # 6. Slang / text speak / Gen Z negatives
    if SLANG_NEGATIVE_RE.search(lower):
        return "negative"

    # 7. Idiomatic negatives (multi-word expressions)
    if _IDIOM_NEGATIVE.search(lower):
        return "negative"

    # 8. Idiomatic neutrals
    if _IDIOM_NEUTRAL.search(lower):
        return "neutral"

    # 9. Word-by-word scoring (fallback for direct/simple language)
    score = 0
    negate = False
    has_hedge = False
    has_soft_pos_only = False
    strong_pos_count = 0
    prev_word = ""

    for w in words:
        if w in NEGATORS:
            negate = True
            prev_word = w
            continue
        if w in HEDGE_WORDS:
            has_hedge = True
            prev_word = w
            continue
        if w in POS_WORDS:
            if negate:
                score -= 1
            else:
                score += 1
                strong_pos_count += 1
        elif w in CONTEXT_POS_WORDS:
            if prev_word in CONTEXT_POS_AMPLIFIERS:
                if negate:
                    score -= 1
                else:
                    score += 1
                    strong_pos_count += 1
        elif w in SOFT_POS_WORDS:
            if negate:
                score -= 1
            else:
                score += 0.5
                has_soft_pos_only = True
        elif w in NEG_WORDS:
            score += 1 if negate else -1
        negate = False
        prev_word = w

    # If hedging is present, require stronger positive signal
    if has_hedge and score > 0:
        score -= 0.5

    # Only soft positives (fine, okay, alright) with no strong positives -> neutral
    if has_soft_pos_only and strong_pos_count == 0 and score > 0:
        return "neutral"

    if score >= 1:
        return "positive"
    if score <= -1:
        return "negative"
    return "neutral"

# ─── Sentiment dispatcher (regex / llm / shadow) ──────────────────────────────

_SENTIMENT_ENGINE = os.environ.get("CCE_SENTIMENT_ENGINE", "regex")
logger = logging.getLogger("cce.engine")


def score_sentiment(text: str) -> str:
    """Route sentiment scoring through the configured engine.

    CCE_SENTIMENT_ENGINE values:
      regex  (default) - regex only
      llm              - LLM only, regex fallback on failure
      shadow           - regex authoritative, LLM runs for comparison logging
    """
    regex_result = _score_sentiment(text)

    # Deterministic short-positive guardrail for first-turn UX.
    # These terse acknowledgements should not be downgraded by LLM ambiguity.
    lower_compact = re.sub(r"[^a-z\s']", "", text.lower()).strip()
    if lower_compact in {
        "well",
        "im well",
        "i'm well",
        "doing well",
        "pretty well",
        "very well",
    }:
        return "positive"

    if _SENTIMENT_ENGINE == "regex":
        return regex_result

    # Import lazily so regex-only mode has zero import cost
    from . import llm_sentiment

    if _SENTIMENT_ENGINE == "llm":
        llm_result = llm_sentiment.classify(text)
        if llm_result is None:
            logger.warning("LLM sentiment failed, falling back to regex")
            return regex_result
        metrics.record_sentiment_shadow(text, regex_result, llm_result)
        return llm_result

    if _SENTIMENT_ENGINE == "shadow":
        llm_result = llm_sentiment.classify(text)
        metrics.record_sentiment_shadow(text, regex_result, llm_result)
        return regex_result  # regex stays authoritative

    return regex_result


# ─── Topic detection ───────────────────────────────────────────────────────────

def _detect_topics_regex(text: str) -> List[str]:
    """Return list of matched topic IDs via keyword matching (most specific first)."""
    lower = text.lower()
    matched: List[Tuple[str, int]] = []
    for tid, tdata in TOPICS.items():
        hits = sum(1 for kw in tdata.get("keywords", []) if kw in lower)
        if hits > 0:
            matched.append((tid, hits))
    matched.sort(key=lambda x: x[1], reverse=True)
    return [m[0] for m in matched] or ["general"]


_TOPIC_ENGINE = os.environ.get("CCE_TOPIC_ENGINE", "regex")


def detect_topics(text: str) -> List[str]:
    """Route topic detection through the configured engine.

    CCE_TOPIC_ENGINE values:
      regex  (default) - keyword matching only
      llm              - LLM primary, regex fallback on failure
      shadow           - regex authoritative, LLM runs for comparison logging
    """
    regex_result = _detect_topics_regex(text)

    if _TOPIC_ENGINE == "regex":
        # Track unmatched even in regex mode
        if regex_result == ["general"]:
            metrics.inc("topic_unmatched")
            metrics.record_unmatched_topic(text, "general")
        else:
            for t in regex_result:
                metrics.inc(f"topic_{t}")
        return regex_result

    from . import llm_topic_matcher

    if _TOPIC_ENGINE == "llm":
        llm_result = llm_topic_matcher.classify(text)
        if llm_result is None:
            logger.warning("LLM topic match failed, falling back to regex")
            if regex_result == ["general"]:
                metrics.inc("topic_unmatched")
                metrics.record_unmatched_topic(text, "general")
            return regex_result

        # LLM returned "no_match": log for demand tracking
        if llm_result == ["no_match"]:
            metrics.inc("topic_unmatched")
            metrics.record_unmatched_topic(text, regex_result[0] if regex_result else "general")
            return ["general"]

        # LLM returned "crisis": let the existing crisis detection handle it
        if llm_result == ["crisis"]:
            return ["crisis"]

        metrics.record_topic_shadow(text, regex_result, llm_result)
        for t in llm_result:
            metrics.inc(f"topic_{t}")
        return llm_result

    if _TOPIC_ENGINE == "shadow":
        llm_result = llm_topic_matcher.classify(text)
        metrics.record_topic_shadow(text, regex_result, llm_result)

        # Track unmatched from regex (authoritative in shadow mode)
        if regex_result == ["general"]:
            metrics.inc("topic_unmatched")
            metrics.record_unmatched_topic(text, "general")
        else:
            for t in regex_result:
                metrics.inc(f"topic_{t}")
        return regex_result  # regex stays authoritative

    return regex_result


# ─── Policy trigger ────────────────────────────────────────────────────────────

POLICY_RE = re.compile(
    r"\b(diagnos\w*|prescri\w*|medic(?:at|in)\w*|am\s+i\s+(?:depressed|anxious|bipolar)|"
    r"(?:do\s+i\s+have)\s+(?:anxiety|depression|bipolar|ptsd|adhd|ocd)\s*(?:disorder)?|"
    r"what\s+disease|what disorder|what\s+do\s+i\s+have|treat(?:ment|ing)\w*|therapy\s+for)\b",
    re.IGNORECASE,
)


def _is_policy_trigger(text: str) -> bool:
    return bool(POLICY_RE.search(text))


# ─── Parenting overload safety guard ─────────────────────────────────────────

PARENTING_OVERLOAD_RE = re.compile(
    r"(?:"
    r"(?:i\s+)?(?:fucking\s+)?hate\s+my\s+(?:kid|kids|child|children)"
    r"|i\s+can(?:not|'t)?\s+stand\s+my\s+(?:kid|kids|child|children)"
    r"|my\s+(?:kid|kids|child|children)\s+(?:are|is)\s+driving\s+me\s+(?:insane|crazy)"
    r"|i\s+(?:might|am\s+about\s+to|feel\s+like\s+i\s+might)\s+(?:snap|lose\s+it)\s+(?:at|on)\s+my\s+(?:kid|kids|child|children)"
    r"|i\s+want\s+to\s+(?:scream\s+at|yell\s+at)\s+my\s+(?:kid|kids|child|children)"
    r")",
    re.IGNORECASE,
)


def _is_parenting_overload(text: str) -> bool:
    return bool(PARENTING_OVERLOAD_RE.search(text))


def _parenting_overload_prompt() -> str:
    return (
        "That sounds like a really overloaded moment. "
        "Before anything else: are your kids safe with you right now, and do you feel like you might snap? "
        "If you can, step away for 60 seconds, put both feet on the floor, and take 10 slow breaths. "
        "Then tell me what happened right before this spiked."
    )


# ─── Medication question detection ─────────────────────────────────────────────

MEDS_RE = re.compile(
    r"\b(meds?|medication|medications|medicated|prescri\w+|pill|pills|dosage|"
    r"antidepress\w+|ssris?|snris?|benzo\w*|xanax|zoloft|lexapro|prozac|"
    r"wellbutrin|buspar|ativan|klonopin|seroquel|abilify|celexa|paxil|"
    r"effexor|cymbalta|trazodone|hydroxyzine|gabapentin|lithium|lamictal|"
    r"vyvanse|adderall|ritalin|concerta|strattera|stimulant|mood\s*stabiliz\w+)\b",
    re.IGNORECASE,
)

_MEDS_PROBE_OPTIONS = [
    PromptOption(id="meds_anxiety", text="Anxiety or constant worry"),
    PromptOption(id="meds_depression", text="Low mood or feeling empty"),
    PromptOption(id="meds_relationships", text="Relationships or loneliness"),
    PromptOption(id="meds_work", text="Work or life stress"),
    PromptOption(id="meds_grief", text="Grief or loss"),
    PromptOption(id="meds_family", text="Family stress"),
    PromptOption(id="meds_trauma", text="Past trauma or difficult memories"),
    PromptOption(id="meds_recovery", text="Substance use or recovery"),
]

_MEDS_REDIRECT_TEXT = (
    "That's a really important question, and I want to make sure you get the right answer. "
    "Medication questions are best handled by your primary care doctor or a psychiatrist "
    "who knows your full picture. "
    "What I can help with is the stuff underneath: what you're feeling day to day "
    "and some real tools to work with it. "
    "What's been weighing on you most?"
)


def _is_meds_question(text: str) -> bool:
    return bool(MEDS_RE.search(text))


_MEDS_ENGINE = os.environ.get("CCE_MEDS_ENGINE", "redirect")


def _handle_meds_question(text: str) -> Optional[str]:
    """Handle a medication question. Returns response text or None.

    CCE_MEDS_ENGINE values:
      redirect (default) - blanket prescriber redirect for all med questions
      llm               - factual answers for what-is/what-for, prescriber redirect for everything else
    """
    if _MEDS_ENGINE == "llm":
        from . import llm_meds
        result = llm_meds.classify(text)
        if result and result["is_med_question"]:
            answer = result.get("factual_answer", "")
            if result.get("needs_prescriber"):
                metrics.inc("meds_prescriber_redirect")
                return (
                    f"{answer}\n\n"
                    "What's been on your mind most lately?"
                )
            else:
                metrics.inc("meds_factual_answered")
                return (
                    f"{answer}\n\n"
                    "Your prescriber is the right person to decide if that's the best fit for you. "
                    "What's been on your mind most lately?"
                )
        # LLM didn't detect a med question or failed: fall through to regex check
        if _is_meds_question(text):
            metrics.inc("meds_redirect")
            return _MEDS_REDIRECT_TEXT
        return None

    # Default: regex detection + blanket redirect
    if _is_meds_question(text):
        metrics.inc("meds_redirect")
        return _MEDS_REDIRECT_TEXT
    return None


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


# ─── Audience-aware completion helper ──────────────────────────────────────────

def _complete_or_ask_audience(
    session: SessionState,
    policy_notice: Optional[PolicyNotice],
) -> Dict[str, Any]:
    """Complete the session, or intercept with audience question first.

    Rules (from audience-bucket-flow.json):
      - Critical: skip audience matching, complete immediately
      - Already has audience bucket: complete immediately
      - Otherwise: ask one conversational question, then complete on follow-up
    """
    # Crisis: never ask audience question
    if session.is_crisis:
        session.is_complete = True
        session.outcome = _build_outcome(session)
        _save_session(session)
        metrics.inc("session_complete")
        return {
            "status": "complete",
            "outcome": session.outcome,
            "policy_notice": policy_notice,
        }

    # Already resolved (from a previous pass or topic hint)
    if session.audience_bucket:
        session.is_complete = True
        session.outcome = _build_outcome(session)
        _save_session(session)
        metrics.inc("session_complete")
        return {
            "status": "complete",
            "outcome": session.outcome,
            "policy_notice": policy_notice,
        }

    # Try to infer audience from conversation history text
    all_messages = " ".join(
        h.get("message", "") for h in session.history if h.get("message")
    )
    if all_messages.strip():
        detection = detect_audience_buckets(all_messages)
        if detection.get("primary"):
            primary_topic = (session.detected_topics or ["general"])[0]
            session.audience_bucket = resolve_bucket(detection, primary_topic)
            session.audience_overlay_buckets = detection.get("overlays", [])
            metrics.inc(f"audience_{session.audience_bucket}")
            session.is_complete = True
            session.outcome = _build_outcome(session)
            _save_session(session)
            metrics.inc("session_complete")
            return {
                "status": "complete",
                "outcome": session.outcome,
                "policy_notice": policy_notice,
            }

    # No audience signal found: ask
    session.audience_matching_active = True
    _save_session(session)
    audience_opts = [
        PromptOption(id=o["id"], text=o["text"]) for o in get_audience_options()
    ]
    return {
        "status": "in_progress",
        "next_prompt": Prompt(
            question=get_audience_question(),
            type="audience_picker",
            options=audience_opts,
        ),
        "policy_notice": policy_notice,
    }


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
    _save_session(session)
    metrics.inc("session_start")
    return session, _step_to_prompt(entry_step)


def get_session(session_id: str) -> Optional[SessionState]:
    return _load_session(session_id)


def process_response(
    session_id: str,
    option_id: Optional[str],
    message: Optional[str],
) -> Dict[str, Any]:
    """
    Process a user response and advance the session.
    Returns a dict matching the RespondResponse shape.
    """
    session = _load_session(session_id)
    if not session:
        raise ValueError(f"Session not found: {session_id}")

    tree = _get_tree(session.tree_id)
    steps = tree["steps"]
    current_step = steps[session.current_step]

    policy_notice: Optional[PolicyNotice] = None

    # ── Clarification shortcut ─────────────────────────────────────
    if session.awaiting_clarification:
        if option_id and session.clarification_options:
            # Legacy: map clarification option back to topic
            for opt in session.clarification_options:
                if opt.id == option_id:
                    session.detected_topics = [option_id.replace("clarify_", "")]
                    break
        elif message:
            # Free-text clarification: detect topics from their response
            detected = detect_topics(message)
            session.detected_topics = detected
        session.awaiting_clarification = False
        session.clarification_options = None
        # MI-style: deepen before completing (if step available)
        if "ng_deepening" in steps and session.current_step != "ng_deepening":
            session.current_step = "ng_deepening"
            personalized = generate_deepening(session.history, session.detected_topics) or personalize_deepening(
                message,
                session.detected_topics,
            )
            _save_session(session)
            return {
                "status": "in_progress",
                "next_prompt": Prompt(
                    question=personalized,
                    type="free_text",
                    options=None,
                ),
                "policy_notice": policy_notice,
            }
        return _complete_or_ask_audience(session, policy_notice)

    # ── Meds redirect follow-up ────────────────────────────────────
    if session.meds_redirect_active:
        session.meds_redirect_active = False
        # Map the meds probe option or free text to a topic
        if option_id:
            topic = option_id.replace("meds_", "")
            session.detected_topics = [topic]
        elif message:
            detected = detect_topics(message)
            for t in detected:
                if t not in session.detected_topics:
                    session.detected_topics.append(t)
        # Go to audience question or outcome with matched guide
        return _complete_or_ask_audience(session, policy_notice)

    # ── Audience matching follow-up ────────────────────────────────
    if session.audience_matching_active:
        session.audience_matching_active = False
        if option_id and option_id != "other":
            # Direct button selection
            bucket = resolve_option_to_bucket(option_id)
            session.audience_bucket = bucket or "general-mental-health"
            if bucket:
                metrics.inc(f"audience_{session.audience_bucket}")
        elif message:
            detection = detect_audience_buckets(message)
            primary_topic = (session.detected_topics or ["general"])[0]
            session.audience_bucket = resolve_bucket(detection, primary_topic)
            session.audience_overlay_buckets = detection.get("overlays", [])
            metrics.inc(f"audience_{session.audience_bucket}")
        else:
            session.audience_bucket = "general-mental-health"
        # Now complete the session
        session.is_complete = True
        session.outcome = _build_outcome(session)
        _save_session(session)
        metrics.inc("session_complete")
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
        session.sentiment = score_sentiment(message)
        metrics.inc(f"sentiment_{session.sentiment}")
        detected = detect_topics(message)
        for t in detected:
            if t not in session.detected_topics:
                session.detected_topics.append(t)

    # ── Parenting overload safety check (children-safe stabilization first) ───
    if message and _is_parenting_overload(message):
        metrics.inc("parenting_overload_guard_trigger")
        _save_session(session)
        return {
            "status": "in_progress",
            "next_prompt": Prompt(
                question=_parenting_overload_prompt(),
                type="free_text",
                options=None,
            ),
            "policy_notice": policy_notice,
        }

    # ── Safety screener trigger (always for safety language) ───────
    if message and is_critical_override_text(message):
        session.total_score += 12
        session.is_crisis = True
        session.is_complete = True
        session.outcome = _build_outcome(session)
        _save_session(session)
        metrics.inc("critical_override")
        metrics.inc("crisis_trigger")
        metrics.inc("session_complete")
        return {
            "status": "complete",
            "outcome": session.outcome,
            "policy_notice": policy_notice,
        }

    if message and is_crisis_text(message):
        if "crisis" not in session.detected_topics:
            session.detected_topics.append("crisis")
        metrics.inc("crisis_trigger")

        has_screener = "suicide_screener_q1" in steps
        in_screener = session.current_step.startswith("suicide_screener_")

        if has_screener and not in_screener:
            session.safety_screener_active = True
            session.current_step = "suicide_screener_q1"
            _save_session(session)
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
        _save_session(session)
        metrics.inc("crisis_trigger")
        metrics.inc("session_complete")
        return {
            "status": "complete",
            "outcome": session.outcome,
            "policy_notice": policy_notice,
        }

    # ── Medication redirect (no crisis signal present) ─────────────
    if message and not session.meds_redirect_active:
        meds_response = _handle_meds_question(message)
        if meds_response:
            session.meds_redirect_active = True
            _save_session(session)
            return {
                "status": "in_progress",
                "next_prompt": Prompt(
                    question=meds_response,
                    type="free_text",
                    options=None,
                ),
                "policy_notice": policy_notice,
            }

    # ── Adaptive screener flow control ─────────────────────────────
    if current_step["id"].startswith("suicide_screener_") and option_id:
        screener_next = _adaptive_screener_next(current_step["id"], session.scores, option_id)
        if screener_next == "CRITICAL_NOW":
            session.is_crisis = True
            session.is_complete = True
            session.outcome = _build_outcome(session)
            _save_session(session)
            metrics.inc("critical_override")
            metrics.inc("crisis_trigger")
            metrics.inc("session_complete")
            return {
                "status": "complete",
                "outcome": session.outcome,
                "policy_notice": policy_notice,
            }
        if screener_next and screener_next in steps:
            session.current_step = screener_next
            _save_session(session)
            return {
                "status": "in_progress",
                "next_prompt": _step_to_prompt(steps[screener_next]),
                "policy_notice": policy_notice,
            }

    # ── Determine next step ────────────────────────────────────────
    routing = current_step.get("routing")

    if routing == "sentiment":
        if session.sentiment == "positive":
            next_step_id = "good_probe"
        else:
            next_step_id = "not_good_probe"
            # Personalize the follow-up based on what they actually said
            if message:
                personalized = generate_negative_probe(message) or personalize_negative_probe(message)
                session.current_step = next_step_id
                _save_session(session)
                return {
                    "status": "in_progress",
                    "next_prompt": Prompt(
                        question=personalized,
                        type="free_text",
                        options=None,
                    ),
                    "policy_notice": policy_notice,
                }
    elif routing == "sentiment_branch":
        # Support both option_id (legacy) and free-text sentiment
        if option_id:
            sentiment_map = {"good": "good_what", "meh": "not_good_what", "bad": "not_good_what"}
            next_step_id = sentiment_map.get(option_id, "not_good_what")
        else:
            next_step_id = "good_what" if session.sentiment == "positive" else "not_good_what"
        # Personalize the negative follow-up
        if next_step_id in ("not_good_what", "not_good_probe") and message:
            personalized = generate_negative_probe(message) or personalize_negative_probe(message)
            session.current_step = next_step_id
            _save_session(session)
            return {
                "status": "in_progress",
                "next_prompt": Prompt(
                    question=personalized,
                    type="free_text",
                    options=None,
                ),
                "policy_notice": policy_notice,
            }
    elif routing == "topic_match":
        is_positive_track = current_step["id"] in {"good_what", "gp_deepening", "gp_goal_clarify"}

        if len(session.detected_topics) == 0 or session.detected_topics == ["general"]:
            # Positive path mirrors negative depth before completion.
            if is_positive_track:
                if current_step["id"] == "good_what" and "gp_deepening" in steps:
                    session.current_step = "gp_deepening"
                    _save_session(session)
                    return {
                        "status": "in_progress",
                        "next_prompt": Prompt(
                            question=personalize_positive_deepening(message, session.detected_topics),
                            type="free_text",
                            options=None,
                        ),
                        "policy_notice": policy_notice,
                    }

                if current_step["id"] == "gp_deepening" and "gp_goal_clarify" in steps:
                    session.current_step = "gp_goal_clarify"
                    _save_session(session)
                    return {
                        "status": "in_progress",
                        "next_prompt": Prompt(
                            question=personalize_positive_goal_clarify(message, session.detected_topics),
                            type="free_text",
                            options=None,
                        ),
                        "policy_notice": policy_notice,
                    }

                return _complete_or_ask_audience(session, policy_notice)

            # Negative/neutral path: ask for clarification
            session.awaiting_clarification = True
            session.clarification_options = None
            metrics.inc("clarification_asked")
            _save_session(session)
            clarification_text = personalize_clarification(message) if message else (
                "I want to make sure I get this right. Can you tell me a little more about what's been on your mind?"
            )
            return {
                "status": "in_progress",
                "next_prompt": Prompt(
                    question=clarification_text,
                    type="free_text",
                    options=None,
                ),
                "policy_notice": policy_notice,
            }

        # Blended flow: MI deepening first, then SFBT goal clarification, then outcome.
        # Crisis text is caught independently above and routes to screener.
        has_crisis_signal = "crisis" in session.detected_topics
        is_negative_deepening_step = current_step["id"] == "ng_deepening"
        is_negative_goal_step = current_step["id"] == "ng_goal_clarify"
        is_positive_deepening_step = current_step["id"] == "gp_deepening"

        if not has_crisis_signal and is_positive_track:
            if current_step["id"] == "good_what" and "gp_deepening" in steps:
                session.current_step = "gp_deepening"
                _save_session(session)
                return {
                    "status": "in_progress",
                    "next_prompt": Prompt(
                        question=personalize_positive_deepening(message, session.detected_topics),
                        type="free_text",
                        options=None,
                    ),
                    "policy_notice": policy_notice,
                }

            if is_positive_deepening_step and "gp_goal_clarify" in steps:
                session.current_step = "gp_goal_clarify"
                _save_session(session)
                return {
                    "status": "in_progress",
                    "next_prompt": Prompt(
                        question=personalize_positive_goal_clarify(message, session.detected_topics),
                        type="free_text",
                        options=None,
                    ),
                    "policy_notice": policy_notice,
                }

        if not has_crisis_signal and not is_positive_track and not is_negative_deepening_step and not is_negative_goal_step and "ng_deepening" in steps:
            session.current_step = "ng_deepening"
            personalized = generate_deepening(session.history, session.detected_topics) or personalize_deepening(
                message,
                session.detected_topics,
            )
            _save_session(session)
            return {
                "status": "in_progress",
                "next_prompt": Prompt(
                    question=personalized,
                    type="free_text",
                    options=None,
                ),
                "policy_notice": policy_notice,
            }

        if not has_crisis_signal and is_negative_deepening_step and "ng_goal_clarify" in steps:
            session.current_step = "ng_goal_clarify"
            personalized = generate_goal_clarify(session.history, session.detected_topics) or personalize_goal_clarify(
                message,
                session.detected_topics,
            )
            _save_session(session)
            return {
                "status": "in_progress",
                "next_prompt": Prompt(
                    question=personalized,
                    type="free_text",
                    options=None,
                ),
                "policy_notice": policy_notice,
            }

        # After goal clarification (or if no blended steps available), move to outcome.
        if not has_crisis_signal:
            return _complete_or_ask_audience(session, policy_notice)

        # Crisis signal present: continue to screener chain if available
        next_step_id = current_step.get("next", None) or (
            "topic_followup" if "topic_followup" in steps else None
        ) or (
            "topic_depth" if "topic_depth" in steps else None
        )

        if next_step_id is None:
            return _complete_or_ask_audience(session, policy_notice)
    else:
        next_step_id = current_step.get("next")

    # ── Terminal step? ────────────────────────────────────────────
    if current_step.get("terminal") or next_step_id is None or next_step_id not in steps:
        return _complete_or_ask_audience(session, policy_notice)

    # ── Advance to next step ──────────────────────────────────────
    session.current_step = next_step_id
    next_step = steps[next_step_id]
    _save_session(session)

    return {
        "status": "in_progress",
        "next_prompt": _step_to_prompt(next_step),
        "policy_notice": policy_notice,
    }


def get_outcome(session_id: str) -> Optional[Outcome]:
    session = _load_session(session_id)
    if not session:
        return None
    if not session.is_complete or not session.outcome:
        return None
    return session.outcome
