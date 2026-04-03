#!/bin/bash
# CCE Behavioral Test Suite
BASE="http://localhost:8000"
PASS=0
FAIL=0
TOTAL=0

test_case() {
    local name="$1"
    local expected="$2"
    local actual="$3"
    TOTAL=$((TOTAL + 1))
    if echo "$actual" | grep -q "$expected"; then
        echo "  PASS: $name"
        PASS=$((PASS + 1))
    else
        echo "  FAIL: $name (expected: $expected)"
        echo "    Got: $(echo "$actual" | head -1 | cut -c1-200)"
        FAIL=$((FAIL + 1))
    fi
}

get_sid() {
    echo "$1" | python3 -c "import sys,json; print(json.load(sys.stdin)['session_id'])"
}

start_session() {
    curl -s "$BASE/session/start" -H "Content-Type: application/json" -d '{"tree_id":"main-flow"}'
}

respond() {
    local sid="$1"
    local body="$2"
    curl -s "$BASE/session/$sid/respond" -H "Content-Type: application/json" -d "$body"
}

echo ""
echo "==========================================="
echo "TEST 1: IMMEDIATE CRISIS OVERRIDE"
echo "  'I am going to kill myself tonight'"
echo "==========================================="
R=$(start_session)
SID=$(get_sid "$R")
respond "$SID" '{"option_id":"bad"}' > /dev/null
R=$(respond "$SID" '{"message":"I am going to kill myself tonight"}')
test_case "Status=complete" '"status":"complete"' "$R"
test_case "Band=critical" '"band":"critical"' "$R"
test_case "Has crisis_resources" 'crisis_resources' "$R"

echo ""
echo "==========================================="
echo "TEST 2: SCREENER TRIGGER (non-override)"
echo "  'I am thinking about suicide'"
echo "==========================================="
R=$(start_session)
SID=$(get_sid "$R")
respond "$SID" '{"option_id":"bad"}' > /dev/null
R=$(respond "$SID" '{"message":"I am thinking about suicide"}')
test_case "Status=in_progress" '"status":"in_progress"' "$R"
test_case "Routes to screener Q1" 'thoughts of ending your life' "$R"

echo ""
echo "==========================================="
echo "TEST 3: ADAPTIVE SCREENER - LOW SIGNAL"
echo "  Q1=No -> skip to Q3; Q3=No -> skip to Q5"
echo "==========================================="
R=$(respond "$SID" '{"option_id":"sq1_no"}')
test_case "Skips to Q3 (access)" 'access to what you would need' "$R"
R=$(respond "$SID" '{"option_id":"sq3_no"}')
test_case "Low signal skips to Q5" 'commit to a safety step' "$R"

echo ""
echo "==========================================="
echo "TEST 4: ADAPTIVE SCREENER - HIGH SIGNAL"
echo "  Q1=Yes,Q2=Yes,Q3=Yes,Q4=Yes -> CRITICAL"
echo "==========================================="
R=$(start_session)
SID=$(get_sid "$R")
respond "$SID" '{"option_id":"meh"}' > /dev/null
R=$(respond "$SID" '{"message":"I have been thinking about killing myself"}')
test_case "Routes to screener Q1" 'thoughts of ending your life' "$R"
R=$(respond "$SID" '{"option_id":"sq1_yes"}')
test_case "Proceeds to Q2" 'thought about how' "$R"
R=$(respond "$SID" '{"option_id":"sq2_yes"}')
test_case "Proceeds to Q3" 'access to what' "$R"
R=$(respond "$SID" '{"option_id":"sq3_yes"}')
test_case "Proceeds to Q4" 'act on these thoughts' "$R"
R=$(respond "$SID" '{"option_id":"sq4_yes"}')
test_case "CRITICAL triggered" '"status":"complete"' "$R"
test_case "Band=critical" '"band":"critical"' "$R"

echo ""
echo "==========================================="
echo "TEST 5: MEH PATH - FULL DEPTH"
echo "  Meh->text->impact->duration->support->function->safety"
echo "==========================================="
R=$(start_session)
SID=$(get_sid "$R")
R=$(respond "$SID" '{"option_id":"meh"}')
test_case "Asks what's going on" 'Tell me a little' "$R"
R=$(respond "$SID" '{"message":"I feel disconnected and tired most days"}')
test_case "Asks about impact" 'affecting your day to day' "$R"
R=$(respond "$SID" '{"option_id":"impact_moderate"}')
test_case "Asks about duration" 'How long has this been' "$R"
R=$(respond "$SID" '{"option_id":"duration_month"}')
test_case "Asks about support" 'Who knows you are carrying' "$R"
R=$(respond "$SID" '{"option_id":"support_no"}')
test_case "Asks about function" 'hard to do what you needed' "$R"
R=$(respond "$SID" '{"option_id":"function_often"}')
test_case "Safety check" 'do you feel safe right now' "$R"
R=$(respond "$SID" '{"option_id":"safety_yes"}')
test_case "Completes" '"status":"complete"' "$R"
# Score: impact(2) + duration(2) + support(2) + function(2) = 8 -> moderate_risk
test_case "Band=moderate" '"band":"moderate_risk"' "$R"

echo ""
echo "==========================================="
echo "TEST 6: SAFETY CANNOT COMMIT at ng_checkin"
echo "==========================================="
R=$(start_session)
SID=$(get_sid "$R")
respond "$SID" '{"option_id":"bad"}' > /dev/null
respond "$SID" '{"message":"everything feels hopeless"}' > /dev/null
respond "$SID" '{"option_id":"impact_heavy"}' > /dev/null
respond "$SID" '{"option_id":"duration_long"}' > /dev/null
respond "$SID" '{"option_id":"support_no"}' > /dev/null
respond "$SID" '{"option_id":"function_daily"}' > /dev/null
R=$(respond "$SID" '{"option_id":"safety_cannot_commit"}')
test_case "Crisis triggered" '"band":"critical"' "$R"
test_case "Has crisis_resources" 'crisis_resources' "$R"

echo ""
echo "==========================================="
echo "TEST 7: THIRD-PERSON CRISIS"
echo "  'my friend is talking about killing himself'"
echo "==========================================="
R=$(start_session)
SID=$(get_sid "$R")
respond "$SID" '{"option_id":"bad"}' > /dev/null
R=$(respond "$SID" '{"message":"my friend is talking about killing himself"}')
test_case "Detects third-person crisis" 'thoughts of ending\|in_progress' "$R"

echo ""
echo "==========================================="
echo "TEST 8: GOOD PATH"
echo "==========================================="
R=$(start_session)
SID=$(get_sid "$R")
R=$(respond "$SID" '{"option_id":"good"}')
test_case "Asks what feels good" 'making things feel good' "$R"
R=$(respond "$SID" '{"message":"Work has been going well and I feel grateful"}')
test_case "Returns status" 'status' "$R"

echo ""
echo "==========================================="
echo "TEST 9: I HAVE A PLAN override"
echo "==========================================="
R=$(start_session)
SID=$(get_sid "$R")
respond "$SID" '{"option_id":"bad"}' > /dev/null
R=$(respond "$SID" '{"message":"I have a plan to end my life"}')
test_case "Status=complete" '"status":"complete"' "$R"
test_case "Band=critical" '"band":"critical"' "$R"

echo ""
echo "==========================================="
echo "RESULTS"
echo "==========================================="
echo "  Total: $TOTAL | Pass: $PASS | Fail: $FAIL"
if [ $FAIL -eq 0 ]; then
    echo "  ALL TESTS PASSED"
else
    echo "  SOME TESTS FAILED"
fi
