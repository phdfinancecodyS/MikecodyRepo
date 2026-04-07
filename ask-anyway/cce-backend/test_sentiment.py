"""Comprehensive sentiment classifier test suite."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))
os.chdir(os.path.dirname(__file__))

# We need to import without relative imports, so patch
import importlib, types

# Create a minimal src package so relative imports work
src_path = os.path.join(os.path.dirname(__file__), "src")
sys.path.insert(0, os.path.dirname(__file__))

from src.engine import _score_sentiment

tests = [
    # === 1. CRISIS (must always be negative) ===
    ("i want to die", "negative"),
    ("i dont want to be here anymore", "negative"),
    ("kms", "negative"),
    ("unalive myself", "negative"),
    ("whats the point of living", "negative"),
    ("better off without me", "negative"),
    ("wrote a goodbye letter", "negative"),
    ("im done with everything", "negative"),
    ("sewerslide", "negative"),
    ("final nap", "negative"),

    # === 2. SARCASM (should be negative) ===
    ("living the dream", "negative"),
    ("just great", "negative"),
    ("oh wonderful", "negative"),
    ("totally fine", "negative"),
    ("everything is fine", "negative"),
    ("couldnt be better", "negative"),
    ("never been better", "negative"),
    ("loving this for me", "negative"),
    ("this is fine", "negative"),
    ("truly blessed", "negative"),

    # === 3. DARK HUMOR (should be negative) ===
    ("fml", "negative"),
    ("dead inside", "negative"),
    ("im a mess", "negative"),
    ("lmao im dying", "negative"),
    ("kill me lol", "negative"),
    ("my life is a dumpster fire", "negative"),
    ("its giving depression", "negative"),
    ("crying lol", "negative"),

    # === 4. DISMISSIVE (should be negative) ===
    ("whatever", "negative"),
    ("idk", "negative"),
    ("meh", "negative"),
    ("idc", "negative"),
    ("nothing new", "negative"),
    ("it is what it is", "negative"),
    ("leave me alone", "negative"),

    # === 5. CONTRADICTION / MASKING (should be negative) ===
    ("im fine actually im not", "negative"),
    ("pretending to be happy", "negative"),
    ("putting on a brave face", "negative"),
    ("nobody knows how bad it is", "negative"),

    # === 6. SLANG / GEN Z (should be negative) ===
    ("lowkey not ok", "negative"),
    ("ngl struggling", "negative"),
    ("down bad", "negative"),
    ("in my sad era", "negative"),
    ("anxiety living rent free", "negative"),
    ("the vibes are off", "negative"),
    ("im literally falling apart", "negative"),
    ("deadass not doing well", "negative"),
    ("its giving anxiety", "negative"),
    ("tbh im not good", "negative"),

    # === 7. IDIOMATIC NEGATIVES (should be negative) ===
    ("ive been better", "negative"),
    ("seen better days", "negative"),
    ("hanging by a thread", "negative"),
    ("running on empty", "negative"),
    ("going through it", "negative"),
    ("barely holding on", "negative"),
    ("at the end of my rope", "negative"),
    ("falling apart", "negative"),
    ("burnt out", "negative"),
    ("in a dark place", "negative"),
    ("cant see the light", "negative"),
    ("just treading water", "negative"),
    ("ill be fine", "negative"),

    # === 8. IDIOMATIC NEUTRALS (should be neutral) ===
    ("could be worse", "neutral"),
    ("same as always", "neutral"),
    ("still here", "neutral"),
    ("up and down", "neutral"),
    ("getting there", "neutral"),
    ("working on it", "neutral"),
    ("not bad", "neutral"),
    ("its complicated", "neutral"),
    ("good days and bad days", "neutral"),
    ("depends on the day", "neutral"),

    # === GENUINE POSITIVES (should be positive) ===
    ("im doing great", "positive"),
    ("feeling really good", "positive"),
    ("much better", "positive"),
    ("really happy", "positive"),
    ("grateful today", "positive"),
    ("things are amazing", "positive"),
    ("im thriving", "positive"),
    ("feeling hopeful", "positive"),

    # === SOFT POSITIVES (should be neutral  - routes to check-in) ===
    ("im fine", "neutral"),
    ("im okay", "neutral"),
    ("alright", "neutral"),
    ("decent", "neutral"),

    # === GENUINE NEGATIVES (should be negative) ===
    ("im so sad", "negative"),
    ("feeling depressed", "negative"),
    ("really anxious today", "negative"),
    ("everything feels hopeless", "negative"),
    ("i feel worthless", "negative"),
    ("im exhausted", "negative"),
]

passed = 0
failed = []
for text, expected in tests:
    result = _score_sentiment(text)
    if result == expected:
        passed += 1
    else:
        failed.append((text, expected, result))

if failed:
    print("FAILURES:")
    for text, expected, result in failed:
        print(f'  FAIL: "{text}" -> {result} (expected {expected})')
    print()

print(f"{passed}/{len(tests)} passed ({len(failed)} failures)")
