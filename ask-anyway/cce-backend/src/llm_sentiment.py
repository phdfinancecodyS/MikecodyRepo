"""
LLM-backed sentiment classifier for the CCE.
Drop-in replacement for _score_sentiment() in engine.py.

Activation:
  CCE_SENTIMENT_ENGINE=llm        -> LLM only (live mode)
  CCE_SENTIMENT_ENGINE=shadow     -> regex is authoritative, LLM runs in parallel for comparison
  CCE_SENTIMENT_ENGINE=regex      -> regex only (default, current behavior)

Requires:
  CCE_LLM_API_KEY    -> API key (OpenAI, Anthropic, or Groq)
  CCE_LLM_PROVIDER   -> "openai" (default), "anthropic", or "groq"
  CCE_LLM_MODEL      -> model name (defaults: gpt-4o-mini / claude-3-haiku / llama-3.3-70b-versatile)
"""
import json
import logging
import os
from typing import Optional

logger = logging.getLogger("cce.llm_sentiment")

_PROVIDER = os.environ.get("CCE_LLM_PROVIDER", "openai")
_MODEL = os.environ.get("CCE_LLM_MODEL", "")
_API_KEY = os.environ.get("CCE_LLM_API_KEY", "")

_SYSTEM_PROMPT = (
    "You are a mental health check-in classifier. "
    "A person was asked 'How are you doing today?' and responded with the text below.\n\n"
    "Classify their response as exactly one of: positive, neutral, negative.\n\n"
    "Rules:\n"
    "- 'positive' = genuinely doing well, happy, grateful, thriving\n"
    "- 'neutral' = ambiguous, dismissive, 'fine', hedging, unclear, sarcastic\n"
    "- 'negative' = struggling, sad, anxious, angry, hopeless, in pain\n"
    "- When in doubt, classify as 'neutral' (never assume someone is okay)\n"
    "- Sarcasm like 'living the dream' or 'couldn't be better lol' = neutral or negative, never positive\n"
    "- 'fine', 'okay', 'alright' with no elaboration = neutral\n\n"
    "- Single-word 'well' should be classified as positive unless clearly sarcastic\n\n"
    "Respond with ONLY one word: positive, neutral, or negative."
)

# Lazy-loaded clients
_openai_client = None
_anthropic_client = None
_groq_client = None


def _get_openai_client():
    global _openai_client
    if _openai_client is None:
        try:
            import openai
            _openai_client = openai.OpenAI(api_key=_API_KEY)
        except ImportError:
            logger.error("openai package not installed. Run: pip install openai")
            return None
    return _openai_client


def _get_anthropic_client():
    global _anthropic_client
    if _anthropic_client is None:
        try:
            import anthropic
            _anthropic_client = anthropic.Anthropic(api_key=_API_KEY)
        except ImportError:
            logger.error("anthropic package not installed. Run: pip install anthropic")
            return None
    return _anthropic_client


def _classify_openai(text: str) -> Optional[str]:
    client = _get_openai_client()
    if not client:
        return None
    model = _MODEL or "gpt-4o-mini"
    try:
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": text},
            ],
            max_tokens=5,
            temperature=0,
        )
        raw = resp.choices[0].message.content.strip().lower()
        if raw in ("positive", "neutral", "negative"):
            return raw
        logger.warning("LLM returned unexpected label: %s", raw)
        return "neutral"
    except Exception as e:
        logger.error("OpenAI sentiment call failed: %s", e)
        return None


def _get_groq_client():
    global _groq_client
    if _groq_client is None:
        try:
            import groq
            _groq_client = groq.Groq(api_key=_API_KEY)
        except ImportError:
            logger.error("groq package not installed. Run: pip install groq")
            return None
    return _groq_client


def _classify_groq(text: str) -> Optional[str]:
    client = _get_groq_client()
    if not client:
        return None
    model = _MODEL or "llama-3.3-70b-versatile"
    try:
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": text},
            ],
            max_tokens=5,
            temperature=0,
        )
        raw = resp.choices[0].message.content.strip().lower()
        if raw in ("positive", "neutral", "negative"):
            return raw
        logger.warning("Groq LLM returned unexpected label: %s", raw)
        return "neutral"
    except Exception as e:
        logger.error("Groq sentiment call failed: %s", e)
        return None


def _classify_anthropic(text: str) -> Optional[str]:
    client = _get_anthropic_client()
    if not client:
        return None
    model = _MODEL or "claude-3-haiku-20240307"
    try:
        resp = client.messages.create(
            model=model,
            system=_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": text}],
            max_tokens=5,
            temperature=0,
        )
        raw = resp.content[0].text.strip().lower()
        if raw in ("positive", "neutral", "negative"):
            return raw
        logger.warning("LLM returned unexpected label: %s", raw)
        return "neutral"
    except Exception as e:
        logger.error("Anthropic sentiment call failed: %s", e)
        return None


def classify(text: str) -> Optional[str]:
    """
    Classify text sentiment using the configured LLM provider.
    Returns 'positive', 'neutral', 'negative', or None on failure.
    On failure, caller should fall back to regex.
    """
    if not _API_KEY:
        return None

    if _PROVIDER == "groq":
        return _classify_groq(text)
    if _PROVIDER == "anthropic":
        return _classify_anthropic(text)
    return _classify_openai(text)
