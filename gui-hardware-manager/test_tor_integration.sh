#!/bin/bash
# Test Script for GUI Hardware Manager Tor Integration
# Path: gui-hardware-manager/test_tor_integration.sh
# Purpose: Verify Tor integration endpoints and functionality

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SERVICE_HOST="${SERVICE_HOST:-localhost}"
SERVICE_PORT="${SERVICE_PORT:-8099}"
BASE_URL="http://${SERVICE_HOST}:${SERVICE_PORT}"
API_PREFIX="/api/v1"

# Timeout for requests
TIMEOUT=10

echo -e "${BLUE}=== GUI Hardware Manager Tor Integration Test ===${NC}\n"

# Test 1: Basic health check
echo -e "${YELLOW}Test 1: Basic Health Check${NC}"
if response=$(curl -s -m "$TIMEOUT" -w "\n%{http_code}" "${BASE_URL}/health"); then
    http_code=$(echo "$response" | tail -n 1)
    body=$(echo "$response" | head -n -1)
    
    if [ "$http_code" = "200" ]; then
        echo -e "${GREEN}✓ Health check passed (HTTP 200)${NC}"
        echo "Response: $body" | head -n 2
    else
        echo -e "${RED}✗ Health check failed (HTTP $http_code)${NC}"
    fi
else
    echo -e "${RED}✗ Health check timeout or error${NC}"
fi
echo ""

# Test 2: Detailed health check
echo -e "${YELLOW}Test 2: Detailed Health Check${NC}"
if response=$(curl -s -m "$TIMEOUT" -w "\n%{http_code}" "${BASE_URL}${API_PREFIX}/health/detailed"); then
    http_code=$(echo "$response" | tail -n 1)
    
    if [ "$http_code" = "200" ]; then
        echo -e "${GREEN}✓ Detailed health check passed${NC}"
    else
        echo -e "${RED}✗ Detailed health check failed (HTTP $http_code)${NC}"
    fi
else
    echo -e "${RED}✗ Detailed health check timeout${NC}"
fi
echo ""

# Test 3: Tor status endpoint
echo -e "${YELLOW}Test 3: Tor Status Endpoint${NC}"
if response=$(curl -s -m "$TIMEOUT" -w "\n%{http_code}" "${BASE_URL}${API_PREFIX}/tor/status"); then
    http_code=$(echo "$response" | tail -n 1)
    body=$(echo "$response" | head -n -1)
    
    if [ "$http_code" = "200" ]; then
        echo -e "${GREEN}✓ Tor status endpoint available${NC}"
        echo "Response sample:"
        echo "$body" | head -n 3
    else
        echo -e "${RED}✗ Tor status endpoint failed (HTTP $http_code)${NC}"
    fi
else
    echo -e "${RED}✗ Tor status endpoint timeout${NC}"
fi
echo ""

# Test 4: Circuit info endpoint
echo -e "${YELLOW}Test 4: Tor Circuit Info Endpoint${NC}"
if response=$(curl -s -m "$TIMEOUT" -w "\n%{http_code}" "${BASE_URL}${API_PREFIX}/tor/circuit/info"); then
    http_code=$(echo "$response" | tail -n 1)
    
    if [ "$http_code" = "200" ]; then
        echo -e "${GREEN}✓ Tor circuit info endpoint available${NC}"
    elif [ "$http_code" = "503" ]; then
        echo -e "${YELLOW}⚠ Tor circuit info unavailable (service may be initializing)${NC}"
    else
        echo -e "${RED}✗ Tor circuit info failed (HTTP $http_code)${NC}"
    fi
else
    echo -e "${RED}✗ Tor circuit info timeout${NC}"
fi
echo ""

# Test 5: Anonymity verification endpoint
echo -e "${YELLOW}Test 5: Anonymity Verification Endpoint${NC}"
if response=$(curl -s -m "$TIMEOUT" -w "\n%{http_code}" "${BASE_URL}${API_PREFIX}/tor/anonymity/verify"); then
    http_code=$(echo "$response" | tail -n 1)
    body=$(echo "$response" | head -n -1)
    
    if [ "$http_code" = "200" ]; then
        echo -e "${GREEN}✓ Anonymity verification endpoint available${NC}"
        echo "Response sample:"
        echo "$body" | head -n 2
    else
        echo -e "${RED}✗ Anonymity verification failed (HTTP $http_code)${NC}"
    fi
else
    echo -e "${RED}✗ Anonymity verification timeout${NC}"
fi
echo ""

# Test 6: Exit IP endpoint
echo -e "${YELLOW}Test 6: Exit IP Endpoint${NC}"
if response=$(curl -s -m "$TIMEOUT" -w "\n%{http_code}" "${BASE_URL}${API_PREFIX}/tor/exit-ip"); then
    http_code=$(echo "$response" | tail -n 1)
    
    if [ "$http_code" = "200" ]; then
        echo -e "${GREEN}✓ Exit IP endpoint available${NC}"
    elif [ "$http_code" = "503" ]; then
        echo -e "${YELLOW}⚠ Exit IP unavailable (Tor not fully initialized)${NC}"
    else
        echo -e "${RED}✗ Exit IP endpoint failed (HTTP $http_code)${NC}"
    fi
else
    echo -e "${RED}✗ Exit IP endpoint timeout${NC}"
fi
echo ""

# Test 7: Hardware devices endpoint
echo -e "${YELLOW}Test 7: Hardware Devices Endpoint${NC}"
if response=$(curl -s -m "$TIMEOUT" -w "\n%{http_code}" "${BASE_URL}${API_PREFIX}/hardware/devices"); then
    http_code=$(echo "$response" | tail -n 1)
    
    if [ "$http_code" = "200" ]; then
        echo -e "${GREEN}✓ Hardware devices endpoint available${NC}"
    else
        echo -e "${RED}✗ Hardware devices endpoint failed (HTTP $http_code)${NC}"
    fi
else
    echo -e "${RED}✗ Hardware devices endpoint timeout${NC}"
fi
echo ""

# Test 8: Hardware status endpoint
echo -e "${YELLOW}Test 8: Hardware Status Endpoint${NC}"
if response=$(curl -s -m "$TIMEOUT" -w "\n%{http_code}" "${BASE_URL}${API_PREFIX}/hardware/status"); then
    http_code=$(echo "$response" | tail -n 1)
    
    if [ "$http_code" = "200" ]; then
        echo -e "${GREEN}✓ Hardware status endpoint available${NC}"
    else
        echo -e "${RED}✗ Hardware status endpoint failed (HTTP $http_code)${NC}"
    fi
else
    echo -e "${RED}✗ Hardware status endpoint timeout${NC}"
fi
echo ""

# Summary
echo -e "${BLUE}=== Test Summary ===${NC}"
echo -e "${GREEN}All critical endpoints tested${NC}"
echo ""
echo -e "${YELLOW}Notes:${NC}"
echo "- Some Tor endpoints may return 503 if Tor proxy is not fully initialized"
echo "- This is normal and the service will retry automatically"
echo "- Check logs with: docker logs lucid-gui-hardware-manager | grep -i tor"
echo ""

exit 0
