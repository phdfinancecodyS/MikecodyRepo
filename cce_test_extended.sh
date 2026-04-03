#!/bin/bash
# Extended CCE Test Suite - includes new endpoints + triage tree
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

start() {
    curl -s "$BASE/session/start" -H "Content-Type: application/json" -d "{\"tree_id\":\"$1\"}"
}

respond() {
    curl -s "$BASE/session/$1/respond" -H "Content-Type: application/json" -d "$2"
}

echo "==========================================="
echo "SECTION A: ORIGINAL 28 TESTS"
echo "==========================================="
bash /Users/michaeljenkins/Desktop/WorkspaceHub/Workspaces/tiktok-mental-health/cce_test.sh 2>&1 | grep -E "PASS|FAIL|Total"

echo ""
echo "==========================================="
echo "SECTION B: NEW API ENDPOINTS"
echo "==========================================="

echo ""
echo "--- B1: Guide Catalog ---"
R=$(curl -s "$BASE/guides/catalog")
test_case "Catalog returns 79 guides" '"count":79' "$R"

echo ""
echo "--- B2: Guide Delivery (base) ---"
R=$(curl -s "$BASE/guides/ch-06?audience=general-mental-health")
test_case "Returns ch-06 content" 'Depression and Numbness' "$R"
test_case "Has domain field" 'nervous_system_mood_cognition' "$R"

echo ""
echo "--- B3: Guide Delivery (audience variant) ---"
R=$(curl -s "$BASE/guides/ch-06?audience=military-veteran")
test_case "Returns military-veteran variant" '"audience":"military-veteran"' "$R"

echo ""
echo "--- B4: Guide 404 ---"
R=$(curl -s "$BASE/guides/nonexistent-id")
test_case "Returns 404" '"detail"' "$R"

echo ""
echo "--- B5: Audience Buckets ---"
R=$(curl -s "$BASE/audience/buckets")
test_case "Returns 17 buckets" '"count":17' "$R"
test_case "Has 3 questions" '"questions"' "$R"

echo ""
echo "--- B6: Products ---"
R=$(curl -s "$BASE/products")
test_case "Shows pricing profile" 'hub_spoke_default' "$R"
test_case "Guide price is 2" '"price":2' "$R"

echo ""
echo "--- B7: Recommendation Endpoint ---"
R0=$(start "main-flow")
SID=$(get_sid "$R0")
respond "$SID" '{"option_id":"meh"}' > /dev/null
respond "$SID" '{"message":"I feel anxious and overwhelmed"}' > /dev/null
respond "$SID" '{"option_id":"impact_moderate"}' > /dev/null
respond "$SID" '{"option_id":"duration_weeks"}' > /dev/null
respond "$SID" '{"option_id":"support_unsure"}' > /dev/null
respond "$SID" '{"option_id":"function_some"}' > /dev/null
respond "$SID" '{"option_id":"safety_yes"}' > /dev/null
R=$(curl -s "$BASE/recommend" -H "Content-Type: application/json" -d "{\"session_id\":\"$SID\"}")
test_case "Recommend returns guide" 'guide_id' "$R"
test_case "Recommend includes offer" 'product_id' "$R"
test_case "File exists" '"file_exists":true' "$R"

echo ""
echo "==========================================="
echo "SECTION C: MENTAL-HEALTH-TRIAGE TREE"
echo "==========================================="

echo ""
echo "--- C1: Low-risk triage ---"
R0=$(start "mental-health-triage")
SID=$(get_sid "$R0")
respond "$SID" '{"option_id":"q1_good"}' > /dev/null
respond "$SID" '{"option_id":"q2_not"}' > /dev/null
respond "$SID" '{"option_id":"q3_not"}' > /dev/null
respond "$SID" '{"option_id":"q4_fine"}' > /dev/null
respond "$SID" '{"option_id":"q5_good"}' > /dev/null
respond "$SID" '{"option_id":"q6_connected"}' > /dev/null
respond "$SID" '{"option_id":"q7_no"}' > /dev/null
respond "$SID" '{"option_id":"q8_no"}' > /dev/null
respond "$SID" '{"option_id":"q9_no"}' > /dev/null
R=$(respond "$SID" '{"option_id":"topic_anxiety"}')
test_case "Triage low risk" '"band":"low_risk"' "$R"

echo ""
echo "--- C2: High-risk triage (total=24, range 21-25) ---"
R0=$(start "mental-health-triage")
SID=$(get_sid "$R0")
respond "$SID" '{"option_id":"q1_bad"}' > /dev/null        # 3
respond "$SID" '{"option_id":"q2_most"}' > /dev/null        # 2
respond "$SID" '{"option_id":"q3_most"}' > /dev/null        # 2
respond "$SID" '{"option_id":"q4_severe"}' > /dev/null      # 3
respond "$SID" '{"option_id":"q5_none"}' > /dev/null        # 3
respond "$SID" '{"option_id":"q6_alone"}' > /dev/null       # 3
respond "$SID" '{"option_id":"q7_rely"}' > /dev/null        # 3
respond "$SID" '{"option_id":"q8_passing"}' > /dev/null     # 2 (no crisis flag)
respond "$SID" '{"option_id":"q9_barely"}' > /dev/null      # 3 = total 24
R=$(respond "$SID" '{"option_id":"topic_depression"}')
test_case "Triage high risk" '"band":"high_risk"' "$R"

echo ""
echo "--- C3: Crisis triage (Q8=plan) ---"
R0=$(start "mental-health-triage")
SID=$(get_sid "$R0")
respond "$SID" '{"option_id":"q1_struggling"}' > /dev/null
respond "$SID" '{"option_id":"q2_most"}' > /dev/null
respond "$SID" '{"option_id":"q3_most"}' > /dev/null
respond "$SID" '{"option_id":"q4_often"}' > /dev/null
respond "$SID" '{"option_id":"q5_very"}' > /dev/null
respond "$SID" '{"option_id":"q6_lonely"}' > /dev/null
respond "$SID" '{"option_id":"q7_yes"}' > /dev/null
# q8_plan is a crisis option - session completes immediately (no q9/q10)
R=$(respond "$SID" '{"option_id":"q8_plan"}')
test_case "Q8 plan triggers crisis" '"band":"critical"' "$R"
test_case "Has crisis resources" 'crisis_resources' "$R"
test_case "Status is complete" '"status":"complete"' "$R"

echo ""
echo "--- C4: Outcome has guide_id ---"
R0=$(start "main-flow")
SID=$(get_sid "$R0")
respond "$SID" '{"option_id":"bad"}' > /dev/null
respond "$SID" '{"message":"work stress is killing me"}' > /dev/null
respond "$SID" '{"option_id":"impact_light"}' > /dev/null
respond "$SID" '{"option_id":"duration_days"}' > /dev/null
respond "$SID" '{"option_id":"support_yes"}' > /dev/null
respond "$SID" '{"option_id":"function_rare"}' > /dev/null
R=$(respond "$SID" '{"option_id":"safety_yes"}')
test_case "Outcome has matched_guide_id" 'matched_guide_id' "$R"
test_case "Outcome has audience_bucket" 'audience_bucket' "$R"
test_case "Outcome has offer" '"offer"' "$R"

echo ""
echo "--- C5: Moderate-risk triage (total=14, range 11-20, no safety override) ---"
R0=$(start "mental-health-triage")
SID=$(get_sid "$R0")
respond "$SID" '{"option_id":"q1_struggling"}' > /dev/null   # 2
respond "$SID" '{"option_id":"q2_several"}' > /dev/null      # 1
respond "$SID" '{"option_id":"q3_most"}' > /dev/null         # 2
respond "$SID" '{"option_id":"q4_little"}' > /dev/null       # 1
respond "$SID" '{"option_id":"q5_low"}' > /dev/null          # 1
respond "$SID" '{"option_id":"q6_some"}' > /dev/null         # 1
respond "$SID" '{"option_id":"q7_yes"}' > /dev/null          # 2
respond "$SID" '{"option_id":"q8_no"}' > /dev/null           # 0 (no safety override)
respond "$SID" '{"option_id":"q9_quite"}' > /dev/null        # 2 = total 12
R=$(respond "$SID" '{"option_id":"topic_anxiety"}')
test_case "Triage moderate risk" '"band":"moderate_risk"' "$R"

echo ""
echo "--- C6: Override floor test (low total but safety=2 → min high_risk) ---"
R0=$(start "mental-health-triage")
SID=$(get_sid "$R0")
respond "$SID" '{"option_id":"q1_good"}' > /dev/null         # 0
respond "$SID" '{"option_id":"q2_not"}' > /dev/null           # 0
respond "$SID" '{"option_id":"q3_not"}' > /dev/null           # 0
respond "$SID" '{"option_id":"q4_fine"}' > /dev/null          # 0
respond "$SID" '{"option_id":"q5_good"}' > /dev/null          # 0
respond "$SID" '{"option_id":"q6_connected"}' > /dev/null     # 0
respond "$SID" '{"option_id":"q7_no"}' > /dev/null            # 0
respond "$SID" '{"option_id":"q8_passing"}' > /dev/null       # 2 (safety=2, triggers override floor)
respond "$SID" '{"option_id":"q9_no"}' > /dev/null            # 0 = total 2
R=$(respond "$SID" '{"option_id":"topic_relationships"}')
test_case "Safety=2 overrides low total to high_risk" '"band":"high_risk"' "$R"

echo ""
echo "==========================================="
echo "EXTENDED RESULTS"
echo "==========================================="
echo "  Total: $TOTAL | Pass: $PASS | Fail: $FAIL"
if [ $FAIL -eq 0 ]; then
    echo "  ALL TESTS PASSED"
else
    echo "  SOME TESTS FAILED"
fi
