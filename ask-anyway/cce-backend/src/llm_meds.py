"""
LLM-backed medication question handler for the CCE.
Strictly constrained: factual psychoeducation only.

What the LLM is allowed to do (two questions ONLY):
  1. "What is this drug?" - drug class, brand vs generic name, correct misspellings
  2. "What is it prescribed for?" - commonly prescribed conditions
  - Clarify common drug-class distinctions (SSRI vs SNRI vs benzo)
  - Correct misspellings ("seroquil" -> seroquel)

What the LLM is NOT allowed to do (everything else -> prescriber):
  - Dosage questions ("how much", "what dose")
  - Side effects ("what are the side effects", "will it make me tired")
  - Interactions ("can I mix", "can I drink on")
  - Starting, stopping, or switching meds
  - Suggest specific medications for a person's situation
  - Replace a prescriber's judgment in any way
  - Provide opinions on whether someone should be medicated

Every response MUST include the prescriber disclaimer.
Every response MUST end with a topic probe to continue the conversation.

Activation:
  CCE_MEDS_ENGINE=llm       -> LLM handles med questions with factual answers
  CCE_MEDS_ENGINE=redirect   -> current behavior (blanket redirect to prescriber)
  Default: redirect
"""
import json
import logging
import os
import re
from typing import Optional

logger = logging.getLogger("cce.llm_meds")

_PROVIDER = os.environ.get("CCE_LLM_PROVIDER", "openai")
_MODEL = os.environ.get("CCE_LLM_MEDS_MODEL", "") or os.environ.get("CCE_LLM_MODEL", "")
_API_KEY = os.environ.get("CCE_LLM_API_KEY", "")

_SYSTEM_PROMPT = """You are a medication information assistant for Ask Anyway, a mental health psychoeducation platform founded by a Licensed Clinical Social Worker.

YOUR ONLY JOB: Answer factual medication questions the same way a Google search or pharmacy reference would. You are a reference tool, not a prescriber.

RULES (non-negotiable):
1. Return ONLY a JSON object with this exact shape:
   {"is_med_question": true/false, "med_name": "corrected name or null", "drug_class": "class or null", "factual_answer": "1-3 sentence factual response or prescriber redirect", "needs_prescriber": true/false, "detected_topic": "anxiety|depression|trauma|grief|relationships|family|work|recovery|loneliness|general"}
2. You answer ONLY two types of questions with factual information:
   a. "What is this drug?" (drug class, brand vs generic, correct misspellings)
   b. "What is it prescribed for?" (commonly prescribed conditions)
3. EVERYTHING ELSE gets a prescriber redirect. Set needs_prescriber=true and factual_answer to a warm redirect. This includes:
   - Dosage ("how much", "what dose", "how often")
   - Side effects ("what are the side effects", "will it make me tired/gain weight")
   - Interactions ("can I mix", "can I drink on", "can I take X with Y")
   - Starting, stopping, or switching ("should I take", "should I stop", "should I switch")
   - Comparisons ("which is better", "is X better than Y")
   - Personal fit ("which med is best for me", "what should I be on")
4. For misspelled medications ("seroquil", "zanax", "welbutrin"), correct the spelling. If they just asked what it is or what it's for, answer. Otherwise redirect.
5. If the input is NOT a medication question, return {"is_med_question": false} with null fields
6. Keep factual_answer to 1-3 sentences. Be direct, not clinical
7. detected_topic should reflect what underlying concern the medication relates to (e.g., Zoloft -> depression, Xanax -> anxiety)
8. When needs_prescriber is true, factual_answer should STILL name the drug and its class (so the user knows you understood them), then redirect. Example: "Xanax is a benzodiazepine. Dosing is really something to work through with your prescriber or pharmacist."

EXAMPLES of ALLOWED factual answers (needs_prescriber=false):
- "Is Zoloft for anxiety or depression?" -> "Zoloft (sertraline) is an SSRI. It's commonly prescribed for both depression and anxiety disorders."
- "what is zanax" -> "Xanax (alprazolam) is a benzodiazepine, commonly prescribed for short-term anxiety relief."
- "do ssris help with panic attacks" -> "SSRIs are one of the first-line treatments prescribed for panic disorder. They work by adjusting serotonin levels over several weeks."
- "what class is wellbutrin" -> "Wellbutrin (bupropion) is an NDRI (norepinephrine-dopamine reuptake inhibitor). It's commonly prescribed for depression and sometimes for smoking cessation."

EXAMPLES of PRESCRIBER REDIRECTS (needs_prescriber=true):
- "What are the side effects of Lexapro?" -> "Lexapro (escitalopram) is an SSRI used for depression and anxiety. Side effects are really something to go over with your prescriber or pharmacist since they depend on your full picture."
- "What dose of Xanax should I take?" -> "Xanax is a benzodiazepine. Dosing is something your prescriber determines based on your specific situation."
- "Can I drink on Zoloft?" -> "Zoloft is an SSRI. Interactions with alcohol are something to talk through with your prescriber."
- "Should I stop my meds?" -> "That's a really important decision to make with your prescriber, not on your own."
- "Is Lexapro better than Zoloft?" -> "Both are SSRIs commonly prescribed for depression and anxiety. Which one works better varies person to person, so that's a great question for your prescriber."

Respond with ONLY the JSON object. No explanation, no preamble."""


def _parse_response(raw: str) -> Optional[dict]:
    """Extract medication info from LLM response."""
    raw = raw.strip()
    json_match = re.search(r'\{[^{}]+\}', raw, re.DOTALL)
    if not json_match:
        logger.warning("LLM meds response not JSON: %s", raw[:100])
        return None
    try:
        data = json.loads(json_match.group())
    except json.JSONDecodeError:
        logger.warning("LLM meds response invalid JSON: %s", raw[:100])
        return None

    if not data.get("is_med_question"):
        return None

    return {
        "is_med_question": True,
        "med_name": data.get("med_name"),
        "drug_class": data.get("drug_class"),
        "factual_answer": data.get("factual_answer", ""),
        "needs_prescriber": bool(data.get("needs_prescriber", False)),
        "detected_topic": data.get("detected_topic", "general"),
    }


def classify(text: str) -> Optional[dict]:
    """
    Analyze text for medication questions and return factual info.
    Returns dict with factual_answer + detected_topic, or None on failure/non-med.
    """
    if not _API_KEY:
        return None

    if _PROVIDER == "groq":
        return _classify_groq(text)
    if _PROVIDER == "anthropic":
        return _classify_anthropic(text)
    return _classify_openai(text)


def _classify_groq(text: str) -> Optional[dict]:
    try:
        from .llm_sentiment import _get_groq_client
    except ImportError:
        return None

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
            max_tokens=200,
            temperature=0,
        )
        return _parse_response(resp.choices[0].message.content or "")
    except Exception as e:
        logger.error("Groq meds call failed: %s", e)
        return None


def _classify_openai(text: str) -> Optional[dict]:
    try:
        from .llm_sentiment import _get_openai_client
    except ImportError:
        return None

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
            max_tokens=200,
            temperature=0,
        )
        return _parse_response(resp.choices[0].message.content or "")
    except Exception as e:
        logger.error("OpenAI meds call failed: %s", e)
        return None


def _classify_anthropic(text: str) -> Optional[dict]:
    try:
        from .llm_sentiment import _get_anthropic_client
    except ImportError:
        return None

    client = _get_anthropic_client()
    if not client:
        return None

    model = _MODEL or "claude-3-haiku-20240307"
    try:
        resp = client.messages.create(
            model=model,
            system=_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": text}],
            max_tokens=200,
            temperature=0,
        )
        return _parse_response(resp.content[0].text or "")
    except Exception as e:
        logger.error("Anthropic meds call failed: %s", e)
        return None
