#!/bin/bash
# Rate Limiter Testing Script
# Tests the 60 requests/minute limit per API key

echo "🧪 Rate Limiter Test Script"
echo "======================================"
echo ""

# Configuration
API_KEY="test-key-123"
URL="http://127.0.0.1:8000/products/SKU001"
LIMIT=60
TEST_REQUESTS=65

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if server is running
echo "📡 Checking if server is running..."
if ! curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8000/health > /dev/null 2>&1; then
    echo -e "${RED}❌ Server is not running!${NC}"
    echo "Please start the server first: uvicorn app.main:app --port 8000"
    exit 1
fi
echo -e "${GREEN}✅ Server is running${NC}"
echo ""

# Test 1: Request without API key
echo "Test 1: Request WITHOUT API key"
echo "--------------------------------"
response=$(curl -s -w "\nHTTP_CODE:%{http_code}" "$URL")
http_code=$(echo "$response" | grep "HTTP_CODE" | cut -d: -f2)

if [ "$http_code" == "401" ]; then
    echo -e "${GREEN}✅ PASS: Got 401 Unauthorized (expected)${NC}"
else
    echo -e "${RED}❌ FAIL: Expected 401, got $http_code${NC}"
fi
echo ""

# Test 2: Request with API key (should succeed)
echo "Test 2: Request WITH API key"
echo "--------------------------------"
response=$(curl -s -w "\nHTTP_CODE:%{http_code}" -H "x-api-key: $API_KEY" "$URL")
http_code=$(echo "$response" | grep "HTTP_CODE" | cut -d: -f2)
remaining=$(echo "$response" | grep -i "x-ratelimit-remaining" | head -1 | cut -d: -f2 | tr -d ' \r')

if [ "$http_code" == "200" ]; then
    echo -e "${GREEN}✅ PASS: Got 200 OK${NC}"
    echo "   Remaining requests: $remaining/$LIMIT"
else
    echo -e "${RED}❌ FAIL: Expected 200, got $http_code${NC}"
fi
echo ""

# Test 3: Rapid fire requests to hit rate limit
echo "Test 3: Rapid Fire - Testing Rate Limit"
echo "--------------------------------"
echo "Making $TEST_REQUESTS requests (limit is $LIMIT)..."
echo ""

success_count=0
rate_limited_count=0
first_rate_limit_at=0

for i in $(seq 1 $TEST_REQUESTS); do
    response=$(curl -s -w "\nHTTP_CODE:%{http_code}" -H "x-api-key: $API_KEY" "$URL" 2>/dev/null)
    http_code=$(echo "$response" | grep "HTTP_CODE" | cut -d: -f2)
    
    if [ "$http_code" == "200" ]; then
        success_count=$((success_count + 1))
        # Show progress every 10 requests
        if [ $((i % 10)) -eq 0 ]; then
            echo -e "  Request $i: ${GREEN}200 OK${NC}"
        fi
    elif [ "$http_code" == "429" ]; then
        rate_limited_count=$((rate_limited_count + 1))
        if [ $first_rate_limit_at -eq 0 ]; then
            first_rate_limit_at=$i
            echo -e "  Request $i: ${YELLOW}429 RATE LIMITED${NC} ⚠️"
            echo ""
            echo "  Rate limit response:"
            echo "$response" | grep -v "HTTP_CODE" | jq '.' 2>/dev/null || echo "$response" | grep -v "HTTP_CODE"
            echo ""
        else
            echo -e "  Request $i: ${YELLOW}429 RATE LIMITED${NC}"
        fi
    else
        echo -e "  Request $i: ${RED}Unexpected $http_code${NC}"
    fi
    
    # Small delay to avoid overwhelming the server
    sleep 0.01
done

echo ""
echo "======================================"
echo "📊 Test Results Summary"
echo "======================================"
echo ""
echo "Total requests made:     $TEST_REQUESTS"
echo -e "Successful (200):        ${GREEN}$success_count${NC}"
echo -e "Rate limited (429):      ${YELLOW}$rate_limited_count${NC}"
echo "First rate limit at:     Request #$first_rate_limit_at"
echo ""

# Validate results
echo "======================================"
echo "🎯 Validation"
echo "======================================"

if [ $success_count -le $LIMIT ] && [ $success_count -ge $((LIMIT - 5)) ]; then
    echo -e "${GREEN}✅ PASS: Success count ($success_count) is within expected range (~$LIMIT)${NC}"
else
    echo -e "${RED}❌ FAIL: Success count ($success_count) is outside expected range (~$LIMIT)${NC}"
fi

if [ $rate_limited_count -gt 0 ]; then
    echo -e "${GREEN}✅ PASS: Rate limiting is working (got $rate_limited_count rate-limited responses)${NC}"
else
    echo -e "${RED}❌ FAIL: No rate limiting detected${NC}"
fi

if [ $first_rate_limit_at -le $((LIMIT + 5)) ] && [ $first_rate_limit_at -ge $((LIMIT - 5)) ]; then
    echo -e "${GREEN}✅ PASS: First rate limit at request #$first_rate_limit_at (expected ~$LIMIT)${NC}"
else
    echo -e "${YELLOW}⚠️  WARNING: First rate limit at request #$first_rate_limit_at (expected ~$LIMIT)${NC}"
fi

echo ""
echo "======================================"
echo "✨ Test Complete!"
echo "======================================"
