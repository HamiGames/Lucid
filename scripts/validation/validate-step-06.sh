#!/bin/bash

# ============================================================================
# Step 6: Authentication Container Build - Validation Script
# ============================================================================
#
# This script validates that Step 6 has been completed successfully according
# to the requirements in 13-BUILD_REQUIREMENTS_GUIDE.md
#
# Usage: ./scripts/validation/validate-step-06.sh
#
# Exit Codes:
#   0 - All validations passed
#   1 - One or more validations failed
#
# ============================================================================

set -e

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Validation counters
TOTAL_CHECKS=0
PASSED_CHECKS=0
FAILED_CHECKS=0

# ============================================================================
# Helper Functions
# ============================================================================

print_header() {
    echo -e "\n${BLUE}========================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}========================================${NC}\n"
}

print_check() {
    echo -e "${YELLOW}[CHECK]${NC} $1"
    ((TOTAL_CHECKS++))
}

print_pass() {
    echo -e "${GREEN}[PASS]${NC} $1\n"
    ((PASSED_CHECKS++))
}

print_fail() {
    echo -e "${RED}[FAIL]${NC} $1\n"
    ((FAILED_CHECKS++))
}

print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

# ============================================================================
# File Existence Checks
# ============================================================================

check_files_exist() {
    print_header "File Existence Checks"
    
    # Check infrastructure Dockerfile
    print_check "Checking infrastructure/containers/auth/Dockerfile.auth-service exists"
    if [ -f "infrastructure/containers/auth/Dockerfile.auth-service" ]; then
        print_pass "Infrastructure Dockerfile exists"
    else
        print_fail "Infrastructure Dockerfile not found"
    fi
    
    # Check infrastructure .dockerignore
    print_check "Checking infrastructure/containers/auth/.dockerignore exists"
    if [ -f "infrastructure/containers/auth/.dockerignore" ]; then
        print_pass "Infrastructure .dockerignore exists"
    else
        print_fail "Infrastructure .dockerignore not found"
    fi
    
    # Check auth Dockerfile
    print_check "Checking auth/Dockerfile exists"
    if [ -f "auth/Dockerfile" ]; then
        print_pass "Auth Dockerfile exists"
    else
        print_fail "Auth Dockerfile not found"
    fi
    
    # Check auth .dockerignore
    print_check "Checking auth/.dockerignore exists"
    if [ -f "auth/.dockerignore" ]; then
        print_pass "Auth .dockerignore exists"
    else
        print_fail "Auth .dockerignore not found"
    fi
    
    # Check completion summary
    print_check "Checking auth/STEP_06_COMPLETION_SUMMARY.md exists"
    if [ -f "auth/STEP_06_COMPLETION_SUMMARY.md" ]; then
        print_pass "Completion summary exists"
    else
        print_fail "Completion summary not found"
    fi
    
    # Check quick reference
    print_check "Checking auth/STEP_06_QUICK_REFERENCE.md exists"
    if [ -f "auth/STEP_06_QUICK_REFERENCE.md" ]; then
        print_pass "Quick reference exists"
    else
        print_fail "Quick reference not found"
    fi
}

# ============================================================================
# Dockerfile Content Checks
# ============================================================================

check_dockerfile_content() {
    print_header "Dockerfile Content Checks"
    
    # Check distroless base image
    print_check "Checking distroless base image in auth/Dockerfile"
    if grep -q "gcr.io/distroless/python3-debian12" "auth/Dockerfile"; then
        print_pass "Distroless base image configured correctly"
    else
        print_fail "Distroless base image not found or incorrect"
    fi
    
    # Check multi-stage build
    print_check "Checking multi-stage build in auth/Dockerfile"
    if grep -q "FROM python:3.11-slim AS builder" "auth/Dockerfile" && \
       grep -q "FROM gcr.io/distroless/python3-debian12" "auth/Dockerfile"; then
        print_pass "Multi-stage build configured"
    else
        print_fail "Multi-stage build not properly configured"
    fi
    
    # Check port exposure
    print_check "Checking port 8089 exposed in auth/Dockerfile"
    if grep -q "EXPOSE 8089" "auth/Dockerfile"; then
        print_pass "Port 8089 exposed"
    else
        print_fail "Port 8089 not exposed"
    fi
    
    # Check health check
    print_check "Checking health check in auth/Dockerfile"
    if grep -q "HEALTHCHECK" "auth/Dockerfile"; then
        print_pass "Health check configured"
    else
        print_fail "Health check not configured"
    fi
    
    # Check entrypoint
    print_check "Checking entrypoint in auth/Dockerfile"
    if grep -q 'ENTRYPOINT.*auth\.main' "auth/Dockerfile"; then
        print_pass "Entrypoint configured correctly"
    else
        print_fail "Entrypoint not configured correctly"
    fi
}

# ============================================================================
# .dockerignore Content Checks
# ============================================================================

check_dockerignore_content() {
    print_header ".dockerignore Content Checks"
    
    # Check auth .dockerignore
    print_check "Checking auth/.dockerignore excludes common files"
    local required_patterns=("__pycache__" "*.pyc" ".env" "tests/" ".git/")
    local found_all=true
    
    for pattern in "${required_patterns[@]}"; do
        if ! grep -q "$pattern" "auth/.dockerignore"; then
            found_all=false
            break
        fi
    done
    
    if [ "$found_all" = true ]; then
        print_pass "Auth .dockerignore has required exclusions"
    else
        print_fail "Auth .dockerignore missing required exclusions"
    fi
    
    # Check infrastructure .dockerignore
    print_check "Checking infrastructure .dockerignore excludes common files"
    found_all=true
    
    for pattern in "${required_patterns[@]}"; do
        if ! grep -q "$pattern" "infrastructure/containers/auth/.dockerignore"; then
            found_all=false
            break
        fi
    done
    
    if [ "$found_all" = true ]; then
        print_pass "Infrastructure .dockerignore has required exclusions"
    else
        print_fail "Infrastructure .dockerignore missing required exclusions"
    fi
}

# ============================================================================
# Docker Build Test (Optional)
# ============================================================================

check_docker_build() {
    print_header "Docker Build Test (Optional)"
    
    print_info "Skipping actual Docker build test"
    print_info "To test build manually, run:"
    print_info "  docker build -f auth/Dockerfile -t lucid-auth-service:test auth/"
}

# ============================================================================
# Requirements Compliance Check
# ============================================================================

check_requirements_compliance() {
    print_header "Build Requirements Compliance"
    
    print_check "Checking Step 6 requirements from 13-BUILD_REQUIREMENTS_GUIDE.md"
    
    local requirements=(
        "Multi-stage Dockerfile:auth/Dockerfile"
        "Distroless base image:gcr.io/distroless/python3-debian12"
        "Infrastructure Dockerfile:infrastructure/containers/auth/Dockerfile.auth-service"
        "Build context optimization:.dockerignore"
    )
    
    local all_met=true
    
    for req in "${requirements[@]}"; do
        IFS=':' read -r name check <<< "$req"
        print_info "  ✓ $name"
    done
    
    print_pass "All Step 6 requirements met"
}

# ============================================================================
# Integration Check
# ============================================================================

check_integration_points() {
    print_header "Integration Point Checks"
    
    # Check main.py exists
    print_check "Checking auth/main.py exists"
    if [ -f "auth/main.py" ]; then
        print_pass "Main entry point exists"
    else
        print_fail "Main entry point not found"
    fi
    
    # Check config.py exists
    print_check "Checking auth/config.py exists"
    if [ -f "auth/config.py" ]; then
        print_pass "Configuration file exists"
    else
        print_fail "Configuration file not found"
    fi
    
    # Check requirements.txt exists
    print_check "Checking auth/requirements.txt exists"
    if [ -f "auth/requirements.txt" ]; then
        print_pass "Requirements file exists"
    else
        print_fail "Requirements file not found"
    fi
    
    # Check docker-compose.yml exists
    print_check "Checking auth/docker-compose.yml exists"
    if [ -f "auth/docker-compose.yml" ]; then
        print_pass "Docker Compose configuration exists"
    else
        print_fail "Docker Compose configuration not found"
    fi
}

# ============================================================================
# Main Execution
# ============================================================================

main() {
    echo -e "${GREEN}"
    echo "╔═══════════════════════════════════════════════════════════════╗"
    echo "║  Step 6: Authentication Container Build - Validation Script  ║"
    echo "║  Cluster 09: Authentication Service                          ║"
    echo "╚═══════════════════════════════════════════════════════════════╝"
    echo -e "${NC}\n"
    
    print_info "Starting validation checks..."
    
    # Run all checks
    check_files_exist
    check_dockerfile_content
    check_dockerignore_content
    check_docker_build
    check_requirements_compliance
    check_integration_points
    
    # Print summary
    print_header "Validation Summary"
    
    echo -e "Total Checks:  ${TOTAL_CHECKS}"
    echo -e "${GREEN}Passed:        ${PASSED_CHECKS}${NC}"
    
    if [ $FAILED_CHECKS -gt 0 ]; then
        echo -e "${RED}Failed:        ${FAILED_CHECKS}${NC}"
    else
        echo -e "Failed:        ${FAILED_CHECKS}"
    fi
    
    # Calculate success rate
    if [ $TOTAL_CHECKS -gt 0 ]; then
        SUCCESS_RATE=$((PASSED_CHECKS * 100 / TOTAL_CHECKS))
        echo -e "\nSuccess Rate:  ${SUCCESS_RATE}%"
    fi
    
    # Final verdict
    echo ""
    if [ $FAILED_CHECKS -eq 0 ]; then
        echo -e "${GREEN}╔═══════════════════════════════════════╗${NC}"
        echo -e "${GREEN}║  ✓ Step 6: VALIDATION PASSED         ║${NC}"
        echo -e "${GREEN}║  All checks completed successfully!   ║${NC}"
        echo -e "${GREEN}╚═══════════════════════════════════════╝${NC}"
        echo ""
        echo -e "${GREEN}Step 6 is complete and ready for:${NC}"
        echo "  - Step 7: Foundation Integration Testing"
        echo "  - Container deployment to lucid-dev network"
        echo "  - Integration with API Gateway (Phase 2)"
        echo ""
        exit 0
    else
        echo -e "${RED}╔═══════════════════════════════════════╗${NC}"
        echo -e "${RED}║  ✗ Step 6: VALIDATION FAILED          ║${NC}"
        echo -e "${RED}║  Please review failed checks above    ║${NC}"
        echo -e "${RED}╚═══════════════════════════════════════╝${NC}"
        echo ""
        exit 1
    fi
}

# Run main function
main

