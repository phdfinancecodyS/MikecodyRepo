"""Live routing test - verifies sentiment drives correct conversation branch."""
import subprocess, json, sys

BASE = "http://localhost:8000"

tests = [
    ("i want to die", "negative", "crisis"),
    ("kms", "negative", "crisis-coded"),
    ("living the dream", "negative", "sarcasm"),
    ("this is fine", "negative", "sarcasm"),
    ("fml", "negative", "dark-humor"),
    ("dead inside", "negative", "dark-humor"),
    ("im a mess", "negative", "dark-humor"),
    ("whatever", "negative", "dismissive"),
    ("idk", "negative", "dismissive"),
    ("pretending to be happy", "negative", "contradiction"),
    ("lowkey not ok", "negative", "slang"),
    ("ngl struggling", "negative", "slang"),
    ("down bad", "negative", "slang"),
    ("its giving anxiety", "negative", "slang"),
    ("ive been better", "negative", "idiom-neg"),
    ("running on empty", "negative", "idiom-neg"),
    ("burnt out", "negative", "idiom-neg"),
    ("could be worse", "neutral", "idiom-neutral"),
    ("still here", "neutral", "idiom-neutral"),
    ("getting there", "neutral", "idiom-neutral"),
    ("im doing great", "positive", "positive"),
    ("much better", "positive", "positive"),
    ("feeling hopeful", "positive", "positive"),
    ("im fine", "neutral", "soft-pos"),
    ("im okay", "neutral", "soft-pos"),
    ("im so sad", "negative", "neg-direct"),
    ("feeling depressed", "negative", "neg-direct"),
]

POS_MARKERS = ["really good to hear", "glad to hear", "that's great", "that's awesome",
               "making things feel good"]
NEG_MARKERS = ["tough", "heavy", "carry", "hard", "going on", "been like",
               "honest about", "safety check", "said something", "lot to"]

def curl(method, url, data=None):
    cmd = ["curl", "-s", "--max-time", "5", "-X", method, url,
           "-H", "Content-Type: application/json"]
    if data:
        cmd += ["-d", json.dumps(data)]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
    return json.loads(r.stdout) if r.stdout.strip() else {}

def detect_route(text):
    t = text.lower()
    for m in POS_MARKERS:
        if m in t:
            return "positive"
    for m in NEG_MARKERS:
        if m in t:
            return "negative"
    return "neutral"

passed = 0
failed = []
for msg, expected, cat in tests:
    start = curl("POST", f"{BASE}/session/start", {"tree_id": "main-flow"})
    sid = start.get("session_id", "")
    if not sid:
        failed.append((msg, cat, expected, "NO_SESSION", ""))
        continue
    resp = curl("POST", f"{BASE}/session/{sid}/respond", {"message": msg})
    prompt = (resp.get("next_prompt") or {}).get("question", "")

    actual = detect_route(prompt)

    # Neutral routes through the "not-good" branch (same empathetic probe as negative)
    match = (actual == expected) or (expected == "neutral" and actual == "negative")

    if match:
        passed += 1
        print(f"  OK   [{cat:14s}] \"{msg}\" -> {actual}")
    else:
        failed.append((msg, cat, expected, actual, prompt[:90]))
        print(f"  FAIL [{cat:14s}] \"{msg}\" -> {actual} (expected {expected})")

print(f"\n{'='*60}")
print(f"LIVE ROUTING: {passed}/{len(tests)} correct")
if failed:
    print(f"\nFAILURES:")
    for msg, cat, exp, got, pr in failed:
        print(f'  [{cat}] "{msg}" -> {got} (expected {exp})')
        if pr:
            print(f'    "{pr}"')
else:
    print("All test inputs route correctly!")
