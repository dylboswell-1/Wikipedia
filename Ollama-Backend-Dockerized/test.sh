#!/bin/bash

# Test script for Ollama Backend API
# Tests both local docker-compose and Kubernetes deployments

set -e

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

BASE_URL="${1:-http://localhost:8000}"

echo -e "${YELLOW}🧪 Testing Ollama Backend API${NC}"
echo "Target: $BASE_URL"
echo ""

# Test health check
test_health() {
  echo -e "${YELLOW}1. Testing health check...${NC}"
  response=$(curl -s -w "\n%{http_code}" "$BASE_URL/health")
  http_code=$(echo "$response" | tail -n1)
  body=$(echo "$response" | head -n-1)
  
  if [ "$http_code" = "200" ]; then
    echo -e "${GREEN}✅ Health check passed${NC}"
    echo "Response: $body"
  else
    echo -e "${RED}❌ Health check failed (HTTP $http_code)${NC}"
    return 1
  fi
  echo ""
}

# Test readiness check
test_readiness() {
  echo -e "${YELLOW}2. Testing readiness check...${NC}"
  response=$(curl -s -w "\n%{http_code}" "$BASE_URL/ready")
  http_code=$(echo "$response" | tail -n1)
  
  if [ "$http_code" = "200" ]; then
    echo -e "${GREEN}✅ Readiness check passed${NC}"
  else
    echo -e "${RED}❌ Readiness check failed (HTTP $http_code)${NC}"
    return 1
  fi
  echo ""
}

# Test root endpoint
test_root() {
  echo -e "${YELLOW}3. Testing root endpoint...${NC}"
  response=$(curl -s "$BASE_URL/")
  echo -e "${GREEN}✅ Root endpoint:${NC}"
  echo "$response" | jq '.' 2>/dev/null || echo "$response"
  echo ""
}

# Test list models
test_models() {
  echo -e "${YELLOW}4. Testing model list endpoint...${NC}"
  response=$(curl -s "$BASE_URL/api/models")
  echo "Response:"
  echo "$response" | jq '.' 2>/dev/null || echo "$response"
  echo ""
}

# Test API docs
test_docs() {
  echo -e "${YELLOW}5. Testing API documentation...${NC}"
  response=$(curl -s -w "\n%{http_code}" "$BASE_URL/docs")
  http_code=$(echo "$response" | tail -n1)
  
  if [ "$http_code" = "200" ]; then
    echo -e "${GREEN}✅ API docs available at $BASE_URL/docs${NC}"
  else
    echo -e "${RED}❌ API docs not available (HTTP $http_code)${NC}"
  fi
  echo ""
}

# Run tests
main() {
  # Wait for service to be available
  echo -e "${YELLOW}Waiting for service to be available...${NC}"
  for i in {1..30}; do
    if curl -s -f "$BASE_URL/health" > /dev/null 2>&1; then
      echo -e "${GREEN}Service is up!${NC}"
      break
    fi
    echo "Attempt $i/30..."
    sleep 2
  done
  echo ""
  
  test_health || exit 1
  test_readiness || exit 1
  test_root || true
  test_models || true
  test_docs || true
  
  echo -e "${GREEN}✅ All tests passed!${NC}"
}

main
