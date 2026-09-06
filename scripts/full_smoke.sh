#!/usr/bin/env bash
set -euo pipefail

BASE="http://127.0.0.1:8000"
UNIQUE="smoke_$(date +%s)"
EMAIL="smoke+${UNIQUE}@example.com"
PW="strongpassword"
USERNAME="smoke_${UNIQUE}"

echo "=== REGISTER ==="
curl -s -X POST "$BASE/auth/register" -H "Content-Type: application/json" -d "{\"email\":\"${EMAIL}\",\"username\":\"${USERNAME}\",\"password\":\"${PW}\"}" -w "\n%{http_code}\n"

echo "=== LOGIN ==="
# Use URL-encoded form fields to preserve '+' in the email
LOGIN_RESP=$(curl -s -X POST "$BASE/auth/login" --data-urlencode "username=${EMAIL}" --data-urlencode "password=${PW}")
TOKEN=$(echo "$LOGIN_RESP" | jq -r .access_token)
if [ -z "$TOKEN" ] || [ "$TOKEN" = "null" ]; then
  echo "LOGIN FAILED: $LOGIN_RESP"
  exit 2
fi
AUTH="Authorization: Bearer ${TOKEN}"

echo "=== GOALS: CREATE ==="
G=$(curl -s -X POST "$BASE/goals/" -H "$AUTH" -H "Content-Type: application/json" -d '{"title":"Smoke Goal","description":"smoke test"}')
echo "$G" | jq .
GID=$(echo "$G" | jq -r .id)

echo "=== GOALS: UPDATE ==="
curl -s -X PATCH "$BASE/goals/$GID" -H "$AUTH" -H "Content-Type: application/json" -d '{"title":"Smoke Goal Updated"}' | jq .

echo "=== GOALS: LIST ==="
curl -s -X GET "$BASE/goals/" -H "$AUTH" | jq .

echo "=== GOALS: DELETE ==="
curl -s -X DELETE "$BASE/goals/$GID" -H "$AUTH" -w "\n%{http_code}\n"

echo "=== SKILLS: CREATE ==="
S=$(curl -s -X POST "$BASE/skills/" -H "$AUTH" -H "Content-Type: application/json" -d '{"name":"Smoke Skill","description":"desc"}')
echo "$S" | jq .
SID=$(echo "$S" | jq -r .id)

echo "=== SKILLS: UPDATE ==="
curl -s -X PATCH "$BASE/skills/$SID" -H "$AUTH" -H "Content-Type: application/json" -d '{"description":"updated"}' | jq .

echo "=== SKILLS: LIST ==="
curl -s -X GET "$BASE/skills/" -H "$AUTH" | jq .

echo "=== SKILLS: DELETE ==="
curl -s -X DELETE "$BASE/skills/$SID" -H "$AUTH" -w "\n%{http_code}\n"

echo "=== MEMORIES: CREATE ORIGINAL (slotA) ==="
M1=$(curl -s -X POST "$BASE/memories/" -H "$AUTH" -H "Content-Type: application/json" -d '{"content":"original memory","slot_key":"slotA"}')
echo "$M1" | jq .
MID1=$(echo "$M1" | jq -r .id)

echo "=== MEMORIES: CREATE CONFLICT (slotA) expecting 409 ==="
curl -s -X POST "$BASE/memories/" -H "$AUTH" -H "Content-Type: application/json" -d '{"content":"new candidate memory","slot_key":"slotA"}' -w "\n%{http_code}\n" > /tmp/mresp || true
cat /tmp/mresp | jq . 2>/dev/null || echo "RAW: $(cat /tmp/mresp)"

echo "=== MEMORIES: LIST ==="
curl -s -X GET "$BASE/memories/" -H "$AUTH" | jq .

echo "=== MEMORIES: LIST CONFLICTS ==="
curl -s -X GET "$BASE/memories/conflicts" -H "$AUTH" | jq .
CID=$(curl -s -X GET "$BASE/memories/conflicts" -H "$AUTH" | jq -r '.[0].id') || true
if [ -n "$CID" ] && [ "$CID" != "null" ]; then
  echo "=== RESOLVE CONFLICT keep_old (if exists) ==="
  curl -s -X POST "$BASE/memories/conflicts/$CID/resolve" -H "$AUTH" -H "Content-Type: application/json" -d '{"action":"keep_old"}' | jq .
else
  echo "No conflicts to resolve"
fi

echo "=== KNOWLEDGE: CREATE NODES ==="
N1=$(curl -s -X POST "$BASE/knowledge/nodes/" -H "$AUTH" -H "Content-Type: application/json" -d '{"node_type":"skill","label":"Smoke Skill Node"}')
echo "$N1" | jq .
N1ID=$(echo "$N1" | jq -r .id)
N2=$(curl -s -X POST "$BASE/knowledge/nodes/" -H "$AUTH" -H "Content-Type: application/json" -d '{"node_type":"skill","label":"Smoke Skill Node 2"}')
echo "$N2" | jq .
N2ID=$(echo "$N2" | jq -r .id)

echo "=== KNOWLEDGE: CREATE RELATIONSHIP ==="
R=$(curl -s -X POST "$BASE/knowledge/relationships/" -H "$AUTH" -H "Content-Type: application/json" -d "{\"source_node_id\":${N1ID},\"target_node_id\":${N2ID},\"relationship_type\":\"related_to\"}")
echo "$R" | jq .
RID=$(echo "$R" | jq -r .id)

echo "=== KNOWLEDGE: TRAVERSE from node ${N1ID} ==="
curl -s -G "$BASE/knowledge/traverse/" --data-urlencode "start=${N1ID}" --data-urlencode "depth=1" -H "$AUTH" | jq .

echo "=== CHAT /ai/test ==="
curl -s -X POST "$BASE/ai/test" -H "$AUTH" -H "Content-Type: application/json" -d '{"prompt":"Hello from smoke"}' | jq . || true

echo "SMOKE SCRIPT COMPLETE"
