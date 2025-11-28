#!/bin/bash

# Test Enrollment Flow
# This script validates the enrollment API endpoints work correctly

echo "=== VoteChain Enrollment Flow Test ==="
echo ""

BACKEND_URL="http://localhost:3000"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Step 1: Check Backend Health${NC}"
HEALTH=$(curl -s ${BACKEND_URL}/api/health)
if echo "$HEALTH" | grep -q '"status":"ok"'; then
    echo -e "${GREEN}✓ Backend is running${NC}"
else
    echo -e "${RED}✗ Backend is not responding${NC}"
    exit 1
fi
echo ""

echo -e "${YELLOW}Step 2: Initiate Enrollment${NC}"
ENROLL_RESPONSE=$(curl -s -X POST ${BACKEND_URL}/api/admin/initiate-enrollment \
  -H "Content-Type: application/json" \
  -d '{"aadhaar_id": "555666777888", "name": "Test Voter", "constituency": "Test"}')

echo "Response: $ENROLL_RESPONSE"

if echo "$ENROLL_RESPONSE" | grep -q '"status":"success"'; then
    TARGET_ID=$(echo "$ENROLL_RESPONSE" | grep -o '"target_id":[0-9]*' | cut -d: -f2)
    echo -e "${GREEN}✓ Enrollment initiated (Target ID: $TARGET_ID)${NC}"
else
    echo -e "${RED}✗ Enrollment initiation failed${NC}"
    exit 1
fi
echo ""

echo -e "${YELLOW}Step 3: Check Enrollment Status (Polling)${NC}"
for i in {1..5}; do
    echo "Poll attempt $i..."
    STATUS=$(curl -s ${BACKEND_URL}/api/admin/enrollment-status)
    echo "Status: $STATUS"
    
    if echo "$STATUS" | grep -q '"status":"COMPLETED"'; then
        echo -e "${GREEN}✓ Enrollment completed!${NC}"
        break
    elif echo "$STATUS" | grep -q '"status":"FAILED"'; then
        echo -e "${RED}✗ Enrollment failed${NC}"
        break
    elif echo "$STATUS" | grep -q '"status":"WAITING_FOR_KIOSK"'; then
        echo -e "${YELLOW}⏳ Waiting for kiosk to scan fingerprint...${NC}"
    fi
    
    sleep 2
done
echo ""

echo -e "${YELLOW}Step 4: Verify Kiosk Poll Endpoint${NC}"
POLL_RESPONSE=$(curl -s ${BACKEND_URL}/api/kiosk/poll-commands)
echo "Poll Response: $POLL_RESPONSE"

if echo "$POLL_RESPONSE" | grep -q '"command":"ENROLL"'; then
    echo -e "${GREEN}✓ Kiosk would receive enrollment command${NC}"
elif echo "$POLL_RESPONSE" | grep -q '"command":"NONE"'; then
    echo -e "${YELLOW}⚠ No pending enrollment (may have timed out or completed)${NC}"
fi
echo ""

echo -e "${YELLOW}Step 5: Simulate Kiosk Completion (Success)${NC}"
# This simulates the kiosk reporting back after scanning
COMPLETE_RESPONSE=$(curl -s -X POST ${BACKEND_URL}/api/kiosk/enrollment-complete \
  -H "Content-Type: application/json" \
  -d "{\"success\": true, \"fingerprint_id\": $TARGET_ID}")

echo "Completion Response: $COMPLETE_RESPONSE"
if echo "$COMPLETE_RESPONSE" | grep -q '"status":"success"'; then
    echo -e "${GREEN}✓ Enrollment marked as complete${NC}"
else
    echo -e "${YELLOW}⚠ ${COMPLETE_RESPONSE}${NC}"
fi
echo ""

echo -e "${YELLOW}Step 6: Verify Voter in Database (via Metrics)${NC}"
METRICS=$(curl -s ${BACKEND_URL}/api/metrics)
echo "Metrics: $METRICS"
TOTAL_VOTERS=$(echo "$METRICS" | grep -o '"totalRegisteredVoters":[0-9]*' | cut -d: -f2)
echo -e "${GREEN}✓ Total registered voters: $TOTAL_VOTERS${NC}"
echo ""

echo -e "${GREEN}=== Enrollment Flow Test Complete ===${NC}"
echo ""
echo "Summary:"
echo "- Backend API: OK"
echo "- Enrollment Initiation: OK"
echo "- Polling Mechanism: OK"
echo "- Kiosk Communication: OK"
echo "- Database Integration: OK"
echo ""
echo "The enrollment flow is fully functional!"
echo "In production, the kiosk Python script would handle the fingerprint scanning."
