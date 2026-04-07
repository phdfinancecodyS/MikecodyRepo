#!/usr/bin/env bash
BASE="https://mikecodyrepo-production.up.railway.app"

START=$(curl -s -X POST "$BASE/session/start" -H "Content-Type: application/json" -d '{"tree_id":"main-flow"}')
echo "START response: $START"
SID=$(echo "$START" | python3 -c "import sys,json; print(json.load(sys.stdin)['session_id'])")
echo "Session: $SID"
echo ""

echo "=== Normal profanity (should NOT trigger moderation) ==="
R1=$(curl -s -X POST "$BASE/session/$SID/respond" -H "Content-Type: application/json" -d "{\"message\":\"everything is so fucking hard right now\"}")
echo "$R1" | python3 -c "import sys,json; d=json.load(sys.stdin); print('Status:', d.get('status')); print('Response:', d.get('next_prompt',{}).get('question','N/A')[:120])"
echo ""

echo "=== Sexually explicit - 1st offense (should WARN) ==="
R2=$(curl -s -X POST "$BASE/session/$SID/respond" -H "Content-Type: application/json" -d "{\"message\":\"send nudes\"}")
echo "$R2" | python3 -c "import sys,json; d=json.load(sys.stdin); print('Status:', d.get('status')); print('Response:', d.get('next_prompt',{}).get('question','N/A')[:200])"
echo ""

echo "=== Directed abuse - 2nd offense (should DISCONNECT) ==="
R3=$(curl -s -X POST "$BASE/session/$SID/respond" -H "Content-Type: application/json" -d "{\"message\":\"fuck you\"}")
echo "$R3" | python3 -c "
import sys,json
d=json.load(sys.stdin)
print('Status:', d.get('status'))
mod = d.get('moderation_notice','')
if mod:
    print('MODERATION DISCONNECT:', mod[:300])
else:
    q = d.get('next_prompt',{}).get('question','') if d.get('next_prompt') else ''
    out = d.get('outcome',{}).get('summary','') if d.get('outcome') else ''
    print('Response:', (q or out or 'N/A')[:300])
"
