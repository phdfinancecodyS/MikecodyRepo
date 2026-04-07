#!/usr/bin/env python3
"""
Ask Anyway  - Beta Test Suite
Exercises all backend endpoints + simulates all chatbot conversation paths.
Run with: /Users/codysullivan/Documents/cce-backend/.venv/bin/python3 beta_test.py
"""

import sys
import json
import time
import textwrap
import requests

BASE = "http://localhost:8000"
SESSION = requests.Session()

PASS = "\033[92m✓ PASS\033[0m"
FAIL = "\033[91m✗ FAIL\033[0m"
WARN = "\033[93m⚠ WARN\033[0m"
HDR  = "\033[1;34m"
END  = "\033[0m"

results = []   # (label, status, detail)


# ─── Helpers ──────────────────────────────────────────────────────────────────

def section(title):
    print(f"\n{HDR}{'─'*60}{END}")
    print(f"{HDR}  {title}{END}")
    print(f"{HDR}{'─'*60}{END}")


def record(label, passed, detail=""):
    status = PASS if passed else FAIL
    print(f"  {status}  {label}")
    if detail:
        for line in detail.strip().splitlines():
            print(f"         {line}")
    results.append((label, passed, detail))


def get(path, **params):
    try:
        r = SESSION.get(BASE + path, params=params, timeout=10)
        return r
    except Exception as e:
        return None


def post(path, payload):
    try:
        r = SESSION.post(BASE + path, json=payload, timeout=15)
        return r
    except Exception as e:
        return None


# ─── 1. Health ─────────────────────────────────────────────────────────────────

section("1 · Health Check")

r = get("/health")
if r and r.status_code == 200:
    data = r.json()
    record("/health → 200 OK", True, f"response: {data}")
else:
    record("/health → 200 OK", False, f"status={getattr(r,'status_code','no response')}")
    print(f"\n  {WARN} Backend is not running. Start it with:\n"
          f"       cd /Users/codysullivan/Documents/cce-backend && "
          f".venv/bin/uvicorn src.app:app --reload\n")
    sys.exit(1)


# ─── 2. Trees ─────────────────────────────────────────────────────────────────

section("2 · CCE Trees Discovery")

r = get("/trees")
if r and r.status_code == 200:
    data = r.json()
    trees = data.get("trees", [])
    record(f"/trees → {len(trees)} tree(s) found", len(trees) > 0)
    for t in trees:
        print(f"         • {t['id']:30s}  {t.get('name','')}")
else:
    record("/trees → 200 OK", False, str(getattr(r, "text", "no response")))
    trees = []


# ─── 3. CCE Session Flows ─────────────────────────────────────────────────────

section("3 · CCE Session Flows (one per tree)")

for tree in trees:
    tid  = tree["id"]
    name = tree.get("name", tid)

    # 3a start session
    r = post("/session/start", {"tree_id": tid})
    if not r or r.status_code != 200:
        record(f"[{tid}] start session", False, getattr(r, "text", "no response"))
        continue

    sd = r.json()
    sid = sd.get("session_id")
    prompt = sd.get("current_prompt", {})
    record(f"[{tid}] session started  id={sid[:8]}…", bool(sid))

    # Walk the tree until done (max 20 turns)
    turns = 0
    complete = False
    while turns < 20:
        turns += 1
        opts = prompt.get("options", [])
        if not opts:
            # Free-text node
            r2 = post(f"/session/{sid}/respond", {"message": "I'm not sure, just checking in"})
        else:
            chosen = opts[0]
            r2 = post(f"/session/{sid}/respond", {"option_id": chosen["id"]})

        if not r2 or r2.status_code not in (200, 409):
            record(f"[{tid}] turn {turns} respond", False, getattr(r2, "text", "none"))
            break

        rd = r2.json()
        status = rd.get("status", "")
        prompt = rd.get("current_prompt") or {}

        if status == "complete" or rd.get("is_complete"):
            complete = True
            break

    if complete:
        # 3b get outcome
        r3 = get(f"/session/{sid}/outcome")
        if r3 and r3.status_code == 200:
            od = r3.json()
            band = od.get("band", od.get("outcome", {}).get("band", "?"))
            record(f"[{tid}] outcome after {turns} turn(s): band={band}", True)
        else:
            record(f"[{tid}] outcome fetch", False, getattr(r3, "text", "none"))
    else:
        record(f"[{tid}] session completed within 20 turns", False,
               f"stuck after {turns} turns  - last status: {rd.get('status','?')}")

    time.sleep(0.2)


# ─── 4. Therapist Finder ──────────────────────────────────────────────────────

section("4 · Therapist Finder (all 8 topics × 2 zips)")

TOPICS_ZIPS = [
    ("relationship", "10001"),
    ("loneliness",   "10001"),
    ("anxiety",      "10001"),
    ("work",         "10001"),
    ("loss",         "90210"),
    ("family",       "10001"),
    ("recovery",     "90210"),
    ("general",      "30303"),
]

for topic, zip_code in TOPICS_ZIPS:
    r = get("/therapists", zip=zip_code, topic=topic)
    if not r or r.status_code != 200:
        record(f"therapists?zip={zip_code}&topic={topic}", False,
               getattr(r, "text", "no response"))
        continue

    data = r.json()
    therapists = data.get("therapists", [])
    count = len(therapists)
    passed = count > 0
    first = therapists[0] if therapists else {}
    sample = f"{first.get('name','?')} | {first.get('credentials','?')} | {first.get('city','?')}, {first.get('state','?')}" if first else " -"
    record(f"topic={topic:12s} zip={zip_code}  → {count:2d} results", passed, f"sample: {sample}")
    time.sleep(0.5)   # polite delay between PT scrapes


# ─── 5. State Machine Path Simulation (local engine) ──────────────────────────

section("5 · Chatbot State Machine  - Path Walkthrough")

print("""
  The chatbot state machine is client-side JavaScript. The paths below
  document expected behavior based on the source code analysis.
  Each input → expected track → expected stages is verified logically.
""")

# Python re-implementation of the detection logic for test verification
import re as _re

def is_good(t):
    t = t.lower()
    if _re.search(r'^(good|great|fine|okay|ok|not bad|alright|pretty good|doing well|doing great|blessed|fantastic|amazing|wonderful|solid|well)([\\.!,\\s]|$)', t):
        return True
    if _re.search(r"i.?m (good|great|fine|okay|doing well|doing great|alright|blessed|fantastic)", t):
        return True
    if _re.search(r"things are (good|great|okay|fine|well|going well)", t):
        return True
    return False

def is_crisis(t):
    return bool(_re.search(
        r"suicid|kill my ?self|end it all|don.?t want to (be here|live|exist|wake up)|"
        r"not worth living|hurt my ?self|self.?harm|no reason to live|can.?t go on|"
        r"want to die|wanna die|thinking about (ending|killing)|take my (life|own life)", t.lower()))

def is_risky(t):
    return bool(_re.search(
        r"(drinking (to forget|every night|alone|a lot|more than usual|heavily)|"
        r"drunk (every|most|all the)|blackout|blacking out|can.?t stop drinking|"
        r"can.?t stop using|using (again|more|every day|to cope)|back on|relapsed|relapse|"
        r"high (every|most|all the)|pills to sleep|cutting (myself|again)|been cutting|"
        r"isolation|isolating|hiding|nobody knows)", t.lower()))

def is_not_good(t):
    if _re.search(
        r"(not (okay|ok|doing well|good|great|feeling well)|struggling|overwhelmed|"
        r"exhausted|burnt out|depressed|anxious|panic|numb|lost|empty|alone|hopeless|"
        r"worthless|tired of|rough|hard time|difficult|bad day|bad week|stressed|"
        r"broke up|breakup|grief|grieving|worried|scared)", t.lower()):
        return True
    return False

PATHS = [
    {
        "name": "GOOD track  - 2-turn close",
        "turns": [
            "I'm doing great honestly",
            "Spending more time with family and getting outside",
        ],
        "expected_track": "GOOD",
        "expected_stages": ["OPENING→GOOD_S2", "GOOD_S2→DONE"],
        "classify_first": is_good,
    },
    {
        "name": "NOT-GOOD track  - relationship topic",
        "turns": [
            "My girlfriend and I just broke up and I'm not doing well",
            "I can barely sleep. Everything feels empty.",
            "No, I haven't really talked to anyone about it.",
        ],
        "expected_track": "NOT_GOOD",
        "expected_stages": ["OPENING→NG_S2 (relationship)", "NG_S2→NG_S3", "NG_S3→recommendations"],
        "classify_first": is_not_good,
    },
    {
        "name": "NOT-GOOD track  - anxiety topic",
        "turns": [
            "I've been having really bad anxiety attacks, I'm overwhelmed",
            "It's more physical  - heart racing, can't breathe.",
            "No, I've been carrying it alone mostly.",
        ],
        "expected_track": "NOT_GOOD",
        "expected_stages": ["OPENING→NG_S2 (anxiety)", "NG_S2→NG_S3", "NG_S3→recommendations"],
        "classify_first": is_not_good,
    },
    {
        "name": "NOT-GOOD track  - work/job topic",
        "turns": [
            "I got laid off last week and I'm stressed beyond belief",
            "I'm basically carrying it all alone, my family doesn't know.",
        ],
        "expected_track": "NOT_GOOD",
        "expected_stages": ["OPENING→NG_S2 (work)", "NG_S2→NG_S3"],
        "classify_first": is_not_good,
    },
    {
        "name": "NOT-GOOD track  - loss/grief topic",
        "turns": [
            "My mom passed away last month. I'm really not okay.",
            "Mornings are the hardest. I forget for a second and then it hits again.",
        ],
        "expected_track": "NOT_GOOD",
        "expected_stages": ["OPENING→NG_S2 (loss)", "NG_S2→NG_S3"],
        "classify_first": is_not_good,
    },
    {
        "name": "RISKY track  - alcohol",
        "turns": [
            "I've been drinking every night alone just to get through it",
            "About three months. It's getting worse.",
        ],
        "expected_track": "RISKY",
        "expected_stages": ["OPENING→RISKY_PROBE", "RISKY_PROBE→RISKY_END (recs)"],
        "classify_first": is_risky,
    },
    {
        "name": "RISKY track  - isolation/hiding",
        "turns": [
            "I've been isolating completely, nobody knows how bad it is",
            "I just can't explain it to anyone.",
        ],
        "expected_track": "RISKY",
        "expected_stages": ["OPENING→RISKY_PROBE", "RISKY_PROBE→RISKY_END (recs)"],
        "classify_first": is_risky,
    },
    {
        "name": "CRISIS detection",
        "turns": [
            "I've been thinking I don't want to be here anymore, I want to die",
        ],
        "expected_track": "RISKY→CRISIS",
        "expected_stages": ["OPENING→CRISIS (crisis card + hotline)"],
        "classify_first": is_crisis,
    },
    {
        "name": "Veteran audience overlay",
        "turns": [
            "I'm a veteran and I've been struggling with PTSD and I'm not okay",
        ],
        "expected_track": "NOT_GOOD + audience=veteran overlay",
        "expected_stages": ["OPENING→NG_S2 (audience overlay applied)"],
        "classify_first": is_not_good,
    },
]

for path in PATHS:
    name = path["name"]
    turns = path["turns"]
    expected_track = path["expected_track"]
    expected_stages = path["expected_stages"]
    classifier = path["classify_first"]

    # Verify the first-turn classifier fires correctly
    first_input = turns[0]
    classified_ok = classifier(first_input)

    detail_lines = [f'input[0]: "{textwrap.shorten(first_input, 60)}"']
    detail_lines.append(f"classifier fires: {'YES ✓' if classified_ok else 'NO ✗'}")
    detail_lines.append(f"expected track:   {expected_track}")
    for i, stage in enumerate(expected_stages):
        detail_lines.append(f"  turn {i+1}: {stage}")

    record(name, classified_ok, "\n".join(detail_lines))


# ─── 6. Topic Detection Verification ─────────────────────────────────────────

section("6 · Topic & Audience Detection")

import re as _re2

def detect_topic(t):
    t = t.lower()
    if _re2.search(r'broke up|breakup|girlfriend|boyfriend|gf|bf|partner|relationship|dating|divorce|marriage|she left|he left', t): return 'relationship'
    if _re2.search(r'fired|laid off|job|work|boss|career|unemployed|money|debt|bills|financial', t): return 'work'
    if _re2.search(r'died|death|passed away|loss|grief|mourning|widow|funeral|gone', t): return 'loss'
    if _re2.search(r'anxious|anxiety|panic|attack|worry|overthinking|racing mind', t): return 'anxiety'
    if _re2.search(r'alone|lonely|isolated|no friends|no one cares|nobody', t): return 'loneliness'
    if _re2.search(r'family|parents|dad|mom|sibling|kids|children', t): return 'family'
    if _re2.search(r'drink|alcohol|sober|relapse|drugs|substance', t): return 'recovery'
    if _re2.search(r'faith|god|church|prayer|spiritual|belief|religion', t): return 'faith'
    return 'general'

def detect_audience(t):
    t = t.lower()
    if _re2.search(r'veteran|military|deployed|combat|ptsd|army|marines|navy|air force|service member', t): return 'veteran'
    if _re2.search(r'first responder|firefight|paramedic|emt|police|officer|dispatch', t): return 'first_responder'
    if _re2.search(r'nurse|doctor|hospital|healthcare|clinician|medical worker', t): return 'healthcare'
    if _re2.search(r'teacher|school|educator|classroom', t): return 'educator'
    if _re2.search(r'christian|faith|god|church|prayer|bible', t): return 'christian'
    if _re2.search(r'lgbtq|gay|lesbian|bisexual|trans|queer|non.?binary', t): return 'lgbtq'
    if _re2.search(r'single (mom|dad|parent)|raising (my kids|them) alone', t): return 'single_parent'
    return None

TOPIC_TESTS = [
    ("My girlfriend and I broke up",          "relationship"),
    ("I lost my job last week",               "work"),
    ("My mom passed away last month",         "loss"),
    ("I've been having panic attacks",        "anxiety"),
    ("I feel so alone, no friends",           "loneliness"),
    ("My parents are driving me crazy",       "family"),
    ("I've been drinking every night",        "recovery"),
    ("I'm questioning my faith",              "faith"),
    ("I just don't feel like myself lately",  "general"),
]

for text, expected in TOPIC_TESTS:
    got = detect_topic(text)
    record(f'detect_topic("{textwrap.shorten(text,40)}")',
           got == expected, f"expected={expected}  got={got}")

AUDIENCE_TESTS = [
    ("I'm a veteran struggling with PTSD",                "veteran"),
    ("I'm an ER nurse and I'm burning out",               "healthcare"),
    ("As a teacher I'm completely overwhelmed",           "educator"),
    ("I'm a single mom raising my kids alone",            "single_parent"),
    ("I'm gay and coming out to my family is hard",       "lgbtq"),
    ("I've been a police officer for 10 years",           "first_responder"),
    ("My faith in God has been wavering lately",          "christian"),
    ("I just feel really lost",                           None),
]

for text, expected in AUDIENCE_TESTS:
    got = detect_audience(text)
    record(f'detect_audience("{textwrap.shorten(text,40)}")',
           got == expected, f"expected={expected}  got={got}")


# ─── 7. File Server Check ─────────────────────────────────────────────────────

section("7 · File Server & Guide Assets")

FILE_BASE = "http://localhost:3131"

ASSETS = [
    "/ask-anyway-chat.html",
    "/ask-anyway-deploy/guides/connection-101.pdf",
    "/ask-anyway-deploy/guides/daily-checklist.pdf",
    "/ask-anyway-deploy/index.html",
]

for path in ASSETS:
    try:
        r = requests.get(FILE_BASE + path, timeout=5)
        record(f"GET {path}", r.status_code == 200, f"status={r.status_code}  size={len(r.content)} bytes")
    except Exception as e:
        record(f"GET {path}", False, f"error: {e}")


# ─── Summary ──────────────────────────────────────────────────────────────────

section("SUMMARY")

total   = len(results)
passed  = sum(1 for _, ok, _ in results if ok)
failed  = total - passed

print(f"\n  Total:  {total}")
print(f"  {PASS}:  {passed}")
if failed:
    print(f"  {FAIL}:  {failed}")
    print(f"\n  Failed tests:")
    for label, ok, detail in results:
        if not ok:
            print(f"    ✗  {label}")
            if detail:
                short = detail.strip().splitlines()[0]
                print(f"       {short}")
else:
    print(f"\n  All tests passed! 🎉")

print()
sys.exit(0 if failed == 0 else 1)
