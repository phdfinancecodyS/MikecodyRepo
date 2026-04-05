"""
LLM-backed topic matcher for the CCE.
Strictly constrained: can ONLY return guide IDs from the catalog.

What the LLM is allowed to do:
  - Read user text describing what they're going through
  - Return 1-3 guide_ids from the closed catalog (79 guides)
  - Return "no_match" if nothing fits
  - Return "crisis" if safety language is detected (belt-and-suspenders)

What the LLM is NOT allowed to do:
  - Give advice, therapy, or opinions
  - Answer general knowledge questions
  - Generate free-form text responses
  - Diagnose conditions
  - Recommend medications or treatments
  - Act as a chatbot or conversational partner

The LLM is a classification function, not a conversationalist.

Activation:
  CCE_TOPIC_ENGINE=llm       -> LLM primary, regex fallback on failure
  CCE_TOPIC_ENGINE=shadow    -> regex authoritative, LLM runs for comparison
  CCE_TOPIC_ENGINE=regex     -> regex only (default, current behavior)

Requires:
    CCE_LLM_API_KEY   -> same key used by llm_sentiment.py
    CCE_LLM_PROVIDER  -> "openai" (default), "anthropic", or "groq"
"""
import json
import logging
import os
import re
from typing import List, Optional

logger = logging.getLogger("cce.llm_topic_matcher")

_PROVIDER = os.environ.get("CCE_LLM_PROVIDER", "openai")
_MODEL = os.environ.get("CCE_LLM_TOPIC_MODEL", "") or os.environ.get("CCE_LLM_MODEL", "")
_API_KEY = os.environ.get("CCE_LLM_API_KEY", "")

# ---- Closed guide catalog (built at import time from config) ----

_GUIDE_CATALOG_PROMPT: Optional[str] = None
_VALID_IDS: set = set()


def _build_catalog_prompt() -> str:
    """Build the guide catalog section of the system prompt from config."""
    global _VALID_IDS
    try:
        from .config import GUIDES_BY_ID
        lines = []
        by_domain: dict = {}
        for gid, g in GUIDES_BY_ID.items():
            _VALID_IDS.add(gid)
            domain = g.get("domain", "other")
            if domain not in by_domain:
                by_domain[domain] = []
            tags = ", ".join(g.get("tags", []))
            by_domain[domain].append(f"  {gid}: {g['title']}" + (f" [{tags}]" if tags else ""))

        for domain, entries in by_domain.items():
            lines.append(f"\n{domain}:")
            lines.extend(entries)

        return "\n".join(lines)
    except Exception as e:
        logger.error("Failed to build guide catalog prompt: %s", e)
        return ""


def _get_catalog_prompt() -> str:
    global _GUIDE_CATALOG_PROMPT
    if _GUIDE_CATALOG_PROMPT is None:
        _GUIDE_CATALOG_PROMPT = _build_catalog_prompt()
    return _GUIDE_CATALOG_PROMPT


_SYSTEM_PROMPT = """You are a mental health guide matcher for Ask Anyway, a psychoeducation platform.

YOUR ONLY JOB: Read what a person is going through and return the best-matching guide IDs from the catalog below. You are a classifier, not a therapist, not a chatbot.

RULES (non-negotiable):
1. Return ONLY a JSON object: {"guide_ids": ["id1", "id2"], "confidence": "high|medium|low"}
2. Return 1-3 guide_ids, most relevant first
3. guide_ids MUST come from the catalog below. No invented IDs.
4. If the input describes active suicidal ideation or imminent self-harm, return {"guide_ids": ["crisis"], "confidence": "high"}
5. If nothing in the catalog fits, return {"guide_ids": ["no_match"], "confidence": "low"}
6. Do NOT give advice, diagnose, recommend treatment, or generate conversation
7. Do NOT answer questions about medications, dosages, or medical topics
8. Do NOT respond to off-topic inputs (politics, weather, recipes, coding, etc.) - return no_match
9. Match based on what the person is EXPERIENCING, not clinical labels they might use
10. "I can't focus" matches attention/cognition guides, not just ADHD
11. "My marriage is falling apart" matches relationship guides even without the word "relationship"

GUIDE CATALOG:
{catalog}

Respond with ONLY the JSON object. No explanation, no preamble, no conversation."""


def _parse_response(raw: str) -> Optional[List[str]]:
    """Extract guide_ids from LLM response. Strict validation."""
    raw = raw.strip()
    # Try to extract JSON from the response
    json_match = re.search(r'\{[^}]+\}', raw)
    if not json_match:
        logger.warning("LLM topic response not JSON: %s", raw[:100])
        return None

    try:
        data = json.loads(json_match.group())
    except json.JSONDecodeError:
        logger.warning("LLM topic response invalid JSON: %s", raw[:100])
        return None

    ids = data.get("guide_ids", [])
    if not isinstance(ids, list) or len(ids) == 0:
        return None

    # Validate: only allow known guide IDs, "crisis", or "no_match"
    catalog = _get_catalog_prompt()  # ensures _VALID_IDS is populated
    valid = _VALID_IDS | {"crisis", "no_match"}
    validated = [gid for gid in ids if gid in valid]

    if not validated:
        logger.warning("LLM returned no valid guide IDs: %s", ids)
        return None

    return validated


# ---- Provider calls (reuse lazy clients from llm_sentiment) ----

def _classify_openai(text: str) -> Optional[List[str]]:
    try:
        from .llm_sentiment import _get_openai_client
    except ImportError:
        return None

    client = _get_openai_client()
    if not client:
        return None

    model = _MODEL or "gpt-4o-mini"
    # Preserve literal JSON braces in the prompt while injecting only catalog text.
    system = _SYSTEM_PROMPT.replace("{catalog}", _get_catalog_prompt())

    try:
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": text},
            ],
            max_tokens=80,
            temperature=0,
        )
        return _parse_response(resp.choices[0].message.content or "")
    except Exception as e:
        logger.error("OpenAI topic match failed: %s", e)
        return None


def _classify_anthropic(text: str) -> Optional[List[str]]:
    try:
        from .llm_sentiment import _get_anthropic_client
    except ImportError:
        return None

    client = _get_anthropic_client()
    if not client:
        return None

    model = _MODEL or "claude-3-haiku-20240307"
    # Preserve literal JSON braces in the prompt while injecting only catalog text.
    system = _SYSTEM_PROMPT.replace("{catalog}", _get_catalog_prompt())

    try:
        resp = client.messages.create(
            model=model,
            system=system,
            messages=[{"role": "user", "content": text}],
            max_tokens=80,
            temperature=0,
        )
        return _parse_response(resp.content[0].text or "")
    except Exception as e:
        logger.error("Anthropic topic match failed: %s", e)
        return None


def _classify_groq(text: str) -> Optional[List[str]]:
    try:
        from .llm_sentiment import _get_groq_client
    except ImportError:
        return None

    client = _get_groq_client()
    if not client:
        return None

    model = _MODEL or "llama-3.3-70b-versatile"
    # Preserve literal JSON braces in the prompt while injecting only catalog text.
    system = _SYSTEM_PROMPT.replace("{catalog}", _get_catalog_prompt())

    try:
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": text},
            ],
            max_tokens=80,
            temperature=0,
        )
        return _parse_response(resp.choices[0].message.content or "")
    except Exception as e:
        logger.error("Groq topic match failed: %s", e)
        return None


def classify(text: str) -> Optional[List[str]]:
    """
    Classify text into guide IDs from the closed catalog.
    Returns list of guide_ids, ["crisis"], ["no_match"], or None on failure.
    On failure, caller falls back to regex keyword matching.
    """
    if not _API_KEY:
        return None

    if _PROVIDER == "groq":
        return _classify_groq(text)
    if _PROVIDER == "anthropic":
        return _classify_anthropic(text)
    return _classify_openai(text)
