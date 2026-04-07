"""
LLM-powered blended-modality response generator for the CCE.

Uses MI (motivational interviewing) as the backbone, with SFBT (solution-focused
brief therapy) micro-moves for goal clarification and coaching-style bridges
to resource handoff. Matches the Ask Anyway voice: warm, direct, session-5 energy.

Falls back to template personalizer on any failure.
"""
import logging
import os
import re
import time
import hashlib
from typing import List, Optional
from . import metrics


def _strip_emoji(text: str) -> str:
    """Remove emoji and other non-text Unicode symbols from LLM output."""
    # Covers emoticons, dingbats, symbols, flags, supplemental symbols, etc.
    return re.sub(
        r'[\U0001F600-\U0001F64F'   # emoticons
        r'\U0001F300-\U0001F5FF'     # misc symbols & pictographs
        r'\U0001F680-\U0001F6FF'     # transport & map
        r'\U0001F1E0-\U0001F1FF'     # flags
        r'\U0001FA00-\U0001FA6F'     # chess symbols
        r'\U0001FA70-\U0001FAFF'     # symbols extended-A
        r'\U00002702-\U000027B0'     # dingbats
        r'\U0000FE00-\U0000FE0F'     # variation selectors
        r'\U0000200D'                # zero width joiner
        r'\U000024C2-\U0001F251'     # enclosed chars
        r'\U00002600-\U000026FF'     # misc symbols
        r'\U00002700-\U000027BF'     # dingbats
        r']+', '', text).strip()


def _strip_stale_openers(text: str) -> str:
    """Remove cliched counselor openers that the LLM falls back to despite prompting."""
    # Patterns: "I hear you.", "I hear you on X.", "It sounds like...",
    # "That sounds like...", "That must be really...", "I can only imagine...",
    # "I understand...", "I can see that..." (when followed by near-parrot of input)
    patterns = [
        r'^(?:I hear you(?:\s+on\s+[^.]*)?[.,]\s*)',
        r'^(?:It sounds like\s+[^.]*[.,]\s*)',
        r'^(?:That (?:sounds|must be)\s+(?:really\s+)?[^.]*[.,]\s*)',
        r'^(?:I (?:can\s+(?:only\s+)?imagine|understand|can\s+see\s+(?:that|how))\s+[^.]*[.,]\s*)',
        r'^(?:I[\'m\s]+so sorry\s+(?:to hear|you[\'re\s]+going through)\s+[^.]*[.,]\s*)',
        r'^(?:(?:First off|First of all),?\s+(?:thank you|I appreciate)\s+[^.]*[.,]\s*)',
        r'^(?:It takes (?:a lot of\s+)?(?:courage|guts|strength)\s+[^.]*[.,]\s*)',
    ]
    for pat in patterns:
        text = re.sub(pat, '', text, count=1, flags=re.I).strip()
    # Capitalize the first letter after stripping
    if text and text[0].islower():
        text = text[0].upper() + text[1:]
    return text


logger = logging.getLogger("cce.llm_responder")

_PROVIDER = os.environ.get("CCE_LLM_PROVIDER", "openai")
_MODEL = os.environ.get("CCE_LLM_MODEL", "")
_API_KEY = os.environ.get("CCE_LLM_API_KEY", "")
_MAX_TOKENS = int(os.environ.get("CCE_LLM_RESPONDER_MAX_TOKENS", "120"))
_TEMPERATURE = float(os.environ.get("CCE_LLM_RESPONDER_TEMPERATURE", "0.75"))
_GUIDANCE_MODE = os.environ.get("CCE_LLM_GUIDANCE_MODE", "full").strip().lower()
_CACHE_TTL_S = int(os.environ.get("CCE_LLM_RESPONDER_CACHE_TTL", "900"))
_CACHE_MAX = int(os.environ.get("CCE_LLM_RESPONDER_CACHE_MAX", "500"))
_TRAFFIC_TIER = os.environ.get("CCE_TRAFFIC_TIER", "core").strip().lower()
_GUIDANCE_RELOAD_S = int(os.environ.get("CCE_LLM_PERSISTENT_GUIDANCE_RELOAD_S", "15"))
_BUDGET_TOKENS_PER_MINUTE = int(os.environ.get("CCE_LLM_BUDGET_TOKENS_PER_MINUTE", "0"))
_BUDGET_TOKENS_PER_HOUR = int(os.environ.get("CCE_LLM_BUDGET_TOKENS_PER_HOUR", "0"))
_BUDGET_TOKENS_PER_DAY = int(os.environ.get("CCE_LLM_BUDGET_TOKENS_PER_DAY", "0"))
_BUDGET_BLOCK_COOLDOWN_S = int(os.environ.get("CCE_LLM_BUDGET_BLOCK_COOLDOWN_S", "180"))

_DEFAULT_STEP_BY_TIER = {
    "pilot": {"negative_probe", "deepening", "goal_clarify"},
    "core": {"negative_probe", "deepening", "goal_clarify"},
    "peak": {"deepening"},
}


def _resolve_enabled_steps() -> set:
    tier_env = os.environ.get(f"CCE_LLM_ENABLED_STEPS_{_TRAFFIC_TIER.upper()}", "").strip()
    if tier_env:
        return {s.strip() for s in tier_env.split(",") if s.strip()}
    env_steps = os.environ.get("CCE_LLM_ENABLED_STEPS", "").strip()
    if env_steps:
        return {s.strip() for s in env_steps.split(",") if s.strip()}
    return _DEFAULT_STEP_BY_TIER.get(_TRAFFIC_TIER, {"deepening"})


_ENABLED_STEPS = _resolve_enabled_steps()


def _resolve_provider_chain() -> List[str]:
    chain_raw = os.environ.get("CCE_LLM_PROVIDER_CHAIN", "").strip()
    if chain_raw:
        chain = [p.strip().lower() for p in chain_raw.split(",") if p.strip()]
    else:
        chain = [_PROVIDER]
    # Keep order while deduplicating and preserving supported providers only.
    out = []
    for p in chain:
        if p in {"groq", "openai", "anthropic"} and p not in out:
            out.append(p)
    return out or ["groq"]


_PROVIDER_CHAIN = _resolve_provider_chain()

# Cooldown guard per provider: skip temporarily after 429/rate-limit errors.
_PROVIDER_COOLDOWN = {p: 0.0 for p in _PROVIDER_CHAIN}
_RESPONSE_CACHE = {}
_CLIENT_CACHE = {}
_TOKEN_EVENTS = []
_BUDGET_BLOCK_UNTIL = 0.0

# ── System prompt: blended MI + SFBT + coaching ────────────────────────────────

_SYSTEM_PROMPT_FULL = """\
You are a warm, skilled conversational guide inside Ask Anyway, a mental health \
check-in app. You blend motivational interviewing (MI), solution-focused brief \
therapy (SFBT), and coaching micro-moves across a 5-turn chat that ends with a \
tailored resource.

SPIRIT (these matter more than technique):
- Partnership: you and the person are equals. They are the expert on their life.
- Evocation: draw out what is already in them. Do not insert ideas.
- Acceptance: absolute worth, accurate empathy, autonomy support, affirmation.
- Compassion: genuinely prioritize their wellbeing. Not performative.

CORE SKILLS (OARS):
- Open questions only. Never yes/no.
- Affirmations: name strengths and effort, not just feelings.
- Reflections: show you heard them. Complex > simple. Reflect FIRST, then ask.
- Summaries: weave threads together when transitioning.

REFLECTION RULES:
- Reflect-to-question ratio: at least 2:1. Most responses should lead with reflection.
- Simple reflection: rephrase what they said.
- Complex reflection: go underneath. Add the feeling or meaning they hinted at.
- "Continuing the paragraph": finish their unfinished thought.
- Prefer paraphrasing over mirroring. Reflect the meaning and emotional load in fresh language.
- Avoid copying long verbatim fragments from the user; preserve key facts, not exact phrasing.
- Never parrot their exact words back without adding meaning.

CHANGE TALK (DARN-CAT):
When you hear desire, ability, reasons, need, commitment, activation, or taking \
steps toward change, AMPLIFY it. Reflect it back. Ask for more.

SUSTAIN TALK:
When they argue against change ("nothing works," "it is not that bad"), do NOT \
argue. Come alongside it. Reflect the feeling underneath. Then gently explore \
the other side: "And yet you are here. What keeps that part of you going?"

ENERGY MATCHING:
- Casual/light: warm and slightly informal.
- Raw/emotional: gentle and grounded. Shorter sentences.
- Angry: validate the anger. Do not redirect it.
- Numb/flat: do not push for emotion. Meet the numbness.
- Minimizing: gently hold space for both. "You say it is fine. What about the parts that are not?"

NEVER DO:
- Diagnose, prescribe, minimize, or moralize
- Use clinical jargon the user did not use first
- Mention suicide/self-harm/safety unless THEY brought it up first
- Use emoji, exclamation marks, or generic reassurance cliches
- Repeat user profanity verbatim back to them
- Ask yes/no questions or jump to solutions before they feel heard

VOICE:
- Second person, contractions, short sentences.
- No em dashes. Use periods or commas.
- Warm but direct. Honesty over comfort.
- "Session 5 energy": you already have rapport. Be real, a little wry, not stiff.
- Aim for 20-50 words per response. Long enough to show you heard them, short enough to stay tight.
- Never start with "I hear you" or "It sounds like." Find a fresher way in.
- Vary your sentence openings. Do not start two sentences the same way.

You generate ONLY the response text. No preamble, no quotes, no explanation."""

_SYSTEM_PROMPT_COMPACT = """\
You are Ask Anyway's guide. Write one short response (20-50 words).

Style:
- Reflect first, then ask one open question.
- Warm, direct, second person, contractions.
- No em dashes, no emoji, no exclamation marks.
- Never start with "I hear you" or "It sounds like." Find a fresher opening.
- Vary your sentence openings.

Method:
- Use MI (reflective listening, affirm strengths, evoke their own words).
- For turn-4 prompts, use SFBT (small next-step, "a little better", scaling/future question).
- If user shows ambivalence or hopelessness, come alongside it. Do not argue.
- Reflect with paraphrase, not parrot. Name what they have not said yet.

Safety and boundaries:
- No diagnosis, no prescribing, no clinical jargon.
- Do not mention suicide/self-harm unless the user explicitly brought it up.
- Do not jump to resources before they feel heard.
- Do not mirror user profanity word-for-word; reflect intensity in clean language.

Output only the response text."""

_BASE_SYSTEM_PROMPT = _SYSTEM_PROMPT_COMPACT if _GUIDANCE_MODE == "compact" else _SYSTEM_PROMPT_FULL


def _load_persistent_guidance() -> str:
    """Load optional persistent teaching instructions from file."""
    path = os.environ.get("CCE_LLM_PERSISTENT_GUIDANCE_FILE", "").strip()
    if not path:
        return ""
    try:
        with open(path, "r", encoding="utf-8") as f:
            txt = f.read().strip()
        if not txt:
            return ""
        return "\n\nPERSISTENT GUIDANCE (VERSIONED, ALWAYS APPLY):\n" + txt
    except OSError as e:
        logger.warning("Could not load persistent guidance file %s: %s", path, e)
        return ""


_PERSISTENT_GUIDANCE_PATH = os.environ.get("CCE_LLM_PERSISTENT_GUIDANCE_FILE", "").strip()
_PERSISTENT_GUIDANCE_MTIME = 0.0
_PERSISTENT_GUIDANCE_TEXT = ""
_PERSISTENT_GUIDANCE_LAST_CHECK = 0.0


def _maybe_refresh_persistent_guidance(now: float) -> None:
    """Refresh persistent guidance on a timed interval when file changes."""
    global _PERSISTENT_GUIDANCE_MTIME, _PERSISTENT_GUIDANCE_TEXT, _PERSISTENT_GUIDANCE_LAST_CHECK

    if not _PERSISTENT_GUIDANCE_PATH:
        _PERSISTENT_GUIDANCE_TEXT = ""
        return
    if now - _PERSISTENT_GUIDANCE_LAST_CHECK < _GUIDANCE_RELOAD_S:
        return

    _PERSISTENT_GUIDANCE_LAST_CHECK = now
    try:
        mtime = os.path.getmtime(_PERSISTENT_GUIDANCE_PATH)
    except OSError:
        if _PERSISTENT_GUIDANCE_TEXT:
            logger.warning("Persistent guidance file unavailable: %s", _PERSISTENT_GUIDANCE_PATH)
        _PERSISTENT_GUIDANCE_MTIME = 0.0
        _PERSISTENT_GUIDANCE_TEXT = ""
        return

    if mtime == _PERSISTENT_GUIDANCE_MTIME:
        return

    _PERSISTENT_GUIDANCE_MTIME = mtime
    _PERSISTENT_GUIDANCE_TEXT = _load_persistent_guidance()
    logger.info("Persistent guidance reloaded from %s", _PERSISTENT_GUIDANCE_PATH)


def _effective_system_prompt(now: Optional[float] = None) -> str:
    ts = time.time() if now is None else now
    _maybe_refresh_persistent_guidance(ts)
    return _BASE_SYSTEM_PROMPT + _PERSISTENT_GUIDANCE_TEXT

# ── Turn-specific user templates ───────────────────────────────────────────────

_NEGATIVE_PROBE_TEMPLATE = """\
TURN CONTEXT: This is turn 2. The user was asked how they're doing and gave \
a negative or neutral response.

Your job: reflect the FEELING underneath what they said (not their exact words), \
then ask ONE open question that goes deeper. Name something they implied but \
didn't say directly.

Do NOT start with "I hear you" or "It sounds like." Find a warmer, more \
human way in. You might name the weight of it, or gently finish their \
unfinished thought.

User said: "{user_message}"

Generate one reflection + open question. 20-50 words."""

_DEEPENING_TEMPLATE = """\
TURN CONTEXT: This is turn 3 (MI deepening). The person has shared what's \
going on. Your job: weave together the emotional thread of everything \
they've said so far into one complex reflection, then ask what part has \
been hardest or what matters most right now.

Do NOT repeat phrases from your previous responses. Do NOT start with \
"I hear you" or "It sounds like." Name something they haven't said \
explicitly but clearly feel.

Conversation so far:
{history}

Detected topics: {topics}

Generate one complex reflection + open question. 20-50 words."""

_GOAL_CLARIFY_TEMPLATE = """\
TURN CONTEXT: This is turn 4 (SFBT pivot). The person has shared their \
struggle and you've reflected it back. Now shift from understanding the \
problem to imagining one small step forward. Use ONE of these SFBT moves:
- Future question: "If things got even a little better with this, what would \
you notice first?"
- Scaling: "On a 1-10, where are you with this right now? What would one \
number up look like?"
- Exception: "Has there been a moment recently where this felt even slightly \
more manageable? What was different?"

Do NOT repeat anything from previous turns. This response is forward-looking \
and hopeful without being fake. Acknowledge what they've shared, then pivot.

Conversation so far:
{history}

Detected topics: {topics}

Generate one SFBT-style forward question. 20-50 words."""


def _api_key_for(provider: str) -> str:
    if provider == "groq":
        return os.environ.get("CCE_LLM_API_KEY_GROQ", "") or (_API_KEY if _PROVIDER == "groq" else "")
    if provider == "openai":
        return (
            os.environ.get("CCE_LLM_API_KEY_OPENAI", "")
            or os.environ.get("CCE_OPENAI_API_KEY", "")
            or (_API_KEY if _PROVIDER == "openai" else "")
        )
    if provider == "anthropic":
        return (
            os.environ.get("CCE_LLM_API_KEY_ANTHROPIC", "")
            or os.environ.get("CCE_ANTHROPIC_API_KEY", "")
            or (_API_KEY if _PROVIDER == "anthropic" else "")
        )
    return ""


def _model_for(provider: str) -> str:
    if provider == "groq":
        return os.environ.get("CCE_LLM_MODEL_GROQ", "") or (_MODEL if _PROVIDER == "groq" else "") or "llama-3.3-70b-versatile"
    if provider == "openai":
        return os.environ.get("CCE_LLM_MODEL_OPENAI", "") or (_MODEL if _PROVIDER == "openai" else "") or "gpt-4o-mini"
    if provider == "anthropic":
        return os.environ.get("CCE_LLM_MODEL_ANTHROPIC", "") or (_MODEL if _PROVIDER == "anthropic" else "") or "claude-3-haiku-20240307"
    return _MODEL or "gpt-4o-mini"


def _get_client(provider: str):
    """Get a cached client for the specified provider."""
    if provider in _CLIENT_CACHE:
        return _CLIENT_CACHE[provider]

    key = _api_key_for(provider)
    if not key:
        return None

    if provider == "groq":
        try:
            import groq
            _CLIENT_CACHE[provider] = groq.Groq(api_key=key)
            return _CLIENT_CACHE[provider]
        except ImportError:
            logger.error("groq package not installed")
            return None
    if provider == "anthropic":
        try:
            import anthropic
            _CLIENT_CACHE[provider] = anthropic.Anthropic(api_key=key)
            return _CLIENT_CACHE[provider]
        except ImportError:
            logger.error("anthropic package not installed")
            return None
    if provider == "openai":
        try:
            import openai
            _CLIENT_CACHE[provider] = openai.OpenAI(api_key=key)
            return _CLIENT_CACHE[provider]
        except ImportError:
            logger.error("openai package not installed")
            return None
    return None


def _extract_usage(provider: str, resp) -> tuple:
    """Return (prompt_tokens, completion_tokens) when available."""
    try:
        if provider in {"groq", "openai"}:
            usage = getattr(resp, "usage", None)
            if usage:
                return int(getattr(usage, "prompt_tokens", 0) or 0), int(getattr(usage, "completion_tokens", 0) or 0)
        if provider == "anthropic":
            usage = getattr(resp, "usage", None)
            if usage:
                return int(getattr(usage, "input_tokens", 0) or 0), int(getattr(usage, "output_tokens", 0) or 0)
    except Exception:
        pass
    return (0, 0)


def _prune_token_events(now: float) -> None:
    cutoff = now - 86400
    while _TOKEN_EVENTS and _TOKEN_EVENTS[0][0] < cutoff:
        _TOKEN_EVENTS.pop(0)


def _tokens_in_window(now: float, seconds: int) -> int:
    cutoff = now - seconds
    return sum(tokens for ts, tokens in _TOKEN_EVENTS if ts >= cutoff)


def _record_token_event(now: float, total_tokens: int) -> None:
    if total_tokens <= 0:
        return
    _TOKEN_EVENTS.append((now, int(total_tokens)))
    _prune_token_events(now)


def _llm_budget_allows(estimated_tokens: int, now: float) -> bool:
    global _BUDGET_BLOCK_UNTIL
    if _BUDGET_BLOCK_UNTIL and now < _BUDGET_BLOCK_UNTIL:
        return False

    if not any((_BUDGET_TOKENS_PER_MINUTE, _BUDGET_TOKENS_PER_HOUR, _BUDGET_TOKENS_PER_DAY)):
        return True

    _prune_token_events(now)

    if _BUDGET_TOKENS_PER_MINUTE > 0:
        used = _tokens_in_window(now, 60)
        if used + estimated_tokens > _BUDGET_TOKENS_PER_MINUTE:
            _BUDGET_BLOCK_UNTIL = now + _BUDGET_BLOCK_COOLDOWN_S
            logger.warning("LLM responder minute token budget reached; using template fallback")
            return False

    if _BUDGET_TOKENS_PER_HOUR > 0:
        used = _tokens_in_window(now, 3600)
        if used + estimated_tokens > _BUDGET_TOKENS_PER_HOUR:
            _BUDGET_BLOCK_UNTIL = now + _BUDGET_BLOCK_COOLDOWN_S
            logger.warning("LLM responder hourly token budget reached; using template fallback")
            return False

    if _BUDGET_TOKENS_PER_DAY > 0:
        used = _tokens_in_window(now, 86400)
        if used + estimated_tokens > _BUDGET_TOKENS_PER_DAY:
            _BUDGET_BLOCK_UNTIL = now + _BUDGET_BLOCK_COOLDOWN_S
            logger.warning("LLM responder daily token budget reached; using template fallback")
            return False

    return True


def _call_llm(system_prompt: str, user_prompt: str) -> Optional[str]:
    """Make a chat completion call to the configured provider."""
    now = time.time()

    # Prompt-level memoization significantly reduces spend on repeated, similar turns.
    cache_key = hashlib.sha256(f"{_PROVIDER_CHAIN}|{system_prompt}|{user_prompt}".encode("utf-8")).hexdigest()
    cached = _RESPONSE_CACHE.get(cache_key)
    if cached and now < cached[1]:
        metrics.record_llm_usage("cache", "cache", 0, 0, "responder", "cache")
        return cached[0]

    estimated_tokens = max(16, min(_MAX_TOKENS + (len(user_prompt) // 6), 256))
    if not _llm_budget_allows(estimated_tokens, now):
        metrics.record_llm_usage("budget", "budget", 0, 0, "responder", "budget_block")
        return None

    for idx, provider in enumerate(_PROVIDER_CHAIN):
        if now < _PROVIDER_COOLDOWN.get(provider, 0):
            continue

        client = _get_client(provider)
        if not client:
            continue

        model = _model_for(provider)
        try:
            if provider == "anthropic":
                resp = client.messages.create(
                    model=model,
                    system=system_prompt,
                    messages=[{"role": "user", "content": user_prompt}],
                    max_tokens=_MAX_TOKENS,
                    temperature=_TEMPERATURE,
                )
                text = resp.content[0].text.strip()
            else:
                resp = client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    max_tokens=_MAX_TOKENS,
                    temperature=_TEMPERATURE,
                )
                text = resp.choices[0].message.content.strip()

            prompt_toks, completion_toks = _extract_usage(provider, resp)
            metrics.record_llm_usage(
                provider,
                model,
                prompt_toks,
                completion_toks,
                lane="responder",
                source="primary" if idx == 0 else "fallback",
            )

            observed_total = prompt_toks + completion_toks
            _record_token_event(now, observed_total if observed_total > 0 else estimated_tokens)

            # Strip any emoji the LLM sneaks in despite instructions
            text = _strip_emoji(text)
            # Strip stale openers the LLM falls back to despite instructions
            text = _strip_stale_openers(text)
            if len(_RESPONSE_CACHE) >= _CACHE_MAX:
                _RESPONSE_CACHE.pop(next(iter(_RESPONSE_CACHE)))
            _RESPONSE_CACHE[cache_key] = (text, now + _CACHE_TTL_S)
            return text

        except Exception as e:
            msg = str(e).lower()
            if "rate limit" in msg or "429" in msg or "rate_limit" in msg:
                _PROVIDER_COOLDOWN[provider] = time.time() + 480
                logger.warning("LLM responder provider %s rate-limited; trying fallback provider", provider)
                continue
            logger.error("LLM responder provider %s failed: %s", provider, e)
            continue

    return None


def _llm_enabled_for(step_name: str) -> bool:
    return step_name in _ENABLED_STEPS


def _build_history_text(history: List[dict]) -> Optional[str]:
    """Build compact readable conversation history for prompts."""
    lines = []
    for entry in history:
        role = entry.get("role", "user")
        msg = entry.get("message") or entry.get("response") or ""
        if msg:
            label = "User" if role == "user" else "Guide"
            lines.append(f"{label}: {msg}")

    if not lines:
        return None

    compact_lines = [ln[:300] for ln in lines[-6:]]
    return "\n".join(compact_lines)


def generate_deepening(history: List[dict], detected_topics: List[str]) -> Optional[str]:
    """Generate an MI-style deepening follow-up from conversation history.

    Returns the response text, or None on failure (caller falls back to templates).
    """
    if not _llm_enabled_for("deepening"):
        return None

    history_text = _build_history_text(history)
    if not history_text:
        return None

    topics_text = ", ".join(detected_topics) if detected_topics else "none detected yet"

    user_prompt = _DEEPENING_TEMPLATE.format(
        history=history_text,
        topics=topics_text,
    )

    return _call_llm(_effective_system_prompt(), user_prompt)


def generate_negative_probe(user_message: str) -> Optional[str]:
    """Generate an MI-style reflection for the initial negative check-in response.

    Returns the response text, or None on failure (caller falls back to templates).
    """
    if not _llm_enabled_for("negative_probe"):
        return None

    if not user_message or not user_message.strip():
        return None

    user_prompt = _NEGATIVE_PROBE_TEMPLATE.format(user_message=user_message)
    return _call_llm(_effective_system_prompt(), user_prompt)


def generate_goal_clarify(history: List[dict], detected_topics: List[str]) -> Optional[str]:
    """Generate an SFBT-style goal clarification prompt (turn 4 pivot)."""
    if not _llm_enabled_for("goal_clarify"):
        return None

    history_text = _build_history_text(history)
    if not history_text:
        return None

    topics_text = ", ".join(detected_topics) if detected_topics else "none detected yet"
    user_prompt = _GOAL_CLARIFY_TEMPLATE.format(
        history=history_text,
        topics=topics_text,
    )

    return _call_llm(_effective_system_prompt(), user_prompt)
