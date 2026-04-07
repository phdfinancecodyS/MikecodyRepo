"""Stress test: extract_key_phrase and personalize_negative_probe across 80+ inputs."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from personalizer import extract_key_phrase, personalize_negative_probe

# (input_text, should_extract: True=must return phrase, False=must return None, None=either ok)
CASES = [
    # ── Standard English ──
    ("I feel really depressed", True),
    ("I am so anxious about everything", True),
    ("my husband left me", True),
    ("I lost my mom last month", True),
    ("work is killing me", True),
    ("I cant sleep at all", True),
    ("nothing ever gets better", True),
    ("everything feels pointless", True),
    ("I feel like a failure", True),
    ("I've been struggling with grief", True),
    ("I'm overwhelmed by everything", True),
    ("I feel worthless and empty", True),
    # ── Misspellings ──
    ("im depresed", True),
    ("im so anxous", True),
    ("i feel exausted", True),
    ("im so overly overwelmed", True),
    ("i feel hopless", True),
    ("im strugling", True),
    ("i feel worthles", True),
    ("im skared", True),
    ("im so frustated", True),
    ("i feel confuesd", True),
    ("i have trama from childhood", True),
    ("im misrable all the time", True),
    # ── Text speak / abbreviations ──
    ("im rly sad rn", True),
    ("ngl im not ok", True),
    ("tbh idk whats wrong w me", True),
    ("fml everything sucks", True),
    ("lowkey not doing good", True),
    ("deadass struggling", True),
    ("fr fr im tired", True),
    ("idek why im crying", True),
    ("sm stress rn", True),
    # ── Gen Z / TikTok slang ──
    ("im in my depressed era", True),
    ("down bad rn", True),
    ("giving depression vibes", True),
    ("mentally checked out", True),
    ("im so done", True),
    ("im literally falling apart", True),
    ("im tweaking", True),
    ("im unwell", True),
    ("im a wreck", True),
    ("im feral rn", True),
    # ── Relationship / family ──
    ("my girlfriend broke up with me", True),
    ("my mom is sick and im scared", True),
    ("my boss is toxic", True),
    ("my kid wont stop acting out", True),
    ("going through a divorce", True),
    ("my partner cheated on me", True),
    ("my dad has cancer", True),
    ("my best friend ghosted me", True),
    # ── Somatic / body ──
    ("my chest feels tight", True),
    ("i cant breathe right", True),
    ("havent slept in days", True),
    ("my stomach is in knots", True),
    ("i keep having nightmares", True),
    ("my heart wont stop racing", True),
    # ── Recovery / relapse ──
    ("im close to relapsing", True),
    ("i want to drink so bad", True),
    ("slipping back into old habits", True),
    ("i been clean for 6 months but tempted", True),
    # ── Idiomatic / indirect ──
    ("ive been better", True),
    ("just going through it", True),
    ("running on empty", True),
    ("at the end of my rope", True),
    ("hanging by a thread", True),
    ("treading water", True),
    # ── Minimal / short ──
    ("bad", True),
    ("sad", True),
    ("meh", True),
    ("not great", True),
    ("rough", True),
    ("struggling", True),
    ("anxious", True),
    ("tired", True),
    ("numb", True),
    # ── Mixed / complex ──
    ("honestly im not ok but i keep telling everyone im fine", True),
    ("i love my kids but im so burned out", True),
    ("work is stressful and my marriage is falling apart", True),
    ("idk man everything just feels heavy lately", True),
    ("like i wake up and i just dont want to do anything", True),
    ("not gonna lie this has been the worst year of my life", True),
    # ── Profanity / raw ──
    ("i feel like shit", True),
    ("everything is so fucking hard", True),
    ("this is bullshit", True),
    ("im so goddamn tired of this", True),
    # ── Edge cases (should NOT extract) ──
    ("", False),
    (".", False),
    ("a", False),
    ("   ", False),
    # ── Edge cases (either ok) ──
    ("hi", None),
    ("ok", None),
    ("lol", None),
    ("yeah", None),
]

passed = 0
failed = 0
results = []
for text, should_extract in CASES:
    phrase = extract_key_phrase(text)
    probe = personalize_negative_probe(text) if phrase else None
    ok = True
    if should_extract is True and phrase is None:
        ok = False
    elif should_extract is False and phrase is not None:
        ok = False

    if ok:
        passed += 1
        tag = "  OK"
    else:
        failed += 1
        tag = "FAIL"
    results.append((tag, text, phrase))

for tag, text, phrase in results:
    p = f'"{phrase}"' if phrase else "None"
    print(f'{tag}: "{text}" -> {p}')

print(f"\n{'='*60}")
print(f"RESULTS: {passed} passed, {failed} failed out of {len(CASES)}")
if failed:
    print(f"\nFAILED CASES:")
    for tag, text, phrase in results:
        if tag == "FAIL":
            p = f'"{phrase}"' if phrase else "None"
            print(f'  "{text}" -> {p}')
print(f"{'='*60}")
