#!/bin/bash
# LUCID Distroless Compliance Verification Script
# Verifies all Dockerfiles meet distroless standards

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Counters
TOTAL_DOCKERFILES=0
DISTROLESS_COMPLIANT=0
NON_DISTROLESS=0
ISSUES_FOUND=0

echo -e "${BLUE}🔍 LUCID Distroless Compliance Verification${NC}"
echo "=================================================="

# Function to check if Dockerfile is distroless compliant
check_distroless_compliance() {
    local dockerfile="$1"
    local issues=0
    
    echo -e "\n${BLUE}📋 Checking: $dockerfile${NC}"
    
    # Check for distroless base image in runtime stage
    if grep -q "FROM gcr.io/distroless" "$dockerfile"; then
        echo -e "  ✅ ${GREEN}Uses distroless base image${NC}"
    else
        echo -e "  ❌ ${RED}Missing distroless base image${NC}"
        ((issues++))
    fi
    
    # Check for multi-stage build
    if grep -q "FROM.*AS.*builder" "$dockerfile" && grep -q "FROM gcr.io/distroless" "$dockerfile"; then
        echo -e "  ✅ ${GREEN}Uses multi-stage build${NC}"
    else
        echo -e "  ❌ ${RED}Missing multi-stage build pattern${NC}"
        ((issues++))
    fi
    
    # Check for non-root user
    if grep -q "USER.*nonroot\|USER.*_[a-z]*_user" "$dockerfile"; then
        echo -e "  ✅ ${GREEN}Runs as non-root user${NC}"
    else
        echo -e "  ❌ ${RED}Missing non-root user execution${NC}"
        ((issues++))
    fi
    
    # Check for health check
    if grep -q "HEALTHCHECK" "$dockerfile"; then
        echo -e "  ✅ ${GREEN}Includes health check${NC}"
    else
        echo -e "  ❌ ${RED}Missing health check${NC}"
        ((issues++))
    fi
    
    # Check for proper metadata
    if grep -q "LABEL.*maintainer.*Lucid Development Team" "$dockerfile"; then
        echo -e "  ✅ ${GREEN}Includes proper metadata${NC}"
    else
        echo -e "  ❌ ${RED}Missing proper metadata${NC}"
        ((issues++))
    fi
    
    # Check for syntax directive
    if grep -q "# syntax=docker/dockerfile:1.7" "$dockerfile"; then
        echo -e "  ✅ ${GREEN}Uses correct syntax directive${NC}"
    else
        echo -e "  ❌ ${RED}Missing syntax directive${NC}"
        ((issues++))
    fi
    
    # Check for prohibited practices
    if grep -q "USER root" "$dockerfile"; then
        echo -e "  ❌ ${RED}Uses root user (security violation)${NC}"
        ((issues++))
    fi
    
    if grep -q "RUN.*apt-get\|RUN.*pip install\|RUN.*npm install" "$dockerfile" && grep -q "FROM gcr.io/distroless" "$dockerfile"; then
        echo -e "  ❌ ${RED}Installs packages in distroless runtime (security violation)${NC}"
        ((issues++))
    fi
    
    # Check for proper import pathways
    if grep -q "COPY --from=builder.*python3" "$dockerfile" || grep -q "COPY --from=builder.*node" "$dockerfile"; then
        echo -e "  ✅ ${GREEN}Uses proper import pathways${NC}"
    else
        echo -e "  ⚠️  ${YELLOW}Import pathways need verification${NC}"
    fi
    
    # Check for dynamic libraries
    if grep -q "COPY --from=builder.*lib.*libc.so" "$dockerfile"; then
        echo -e "  ✅ ${GREEN}Includes required dynamic libraries${NC}"
    else
        echo -e "  ⚠️  ${YELLOW}Dynamic libraries need verification${NC}"
    fi
    
    # Determine compliance status
    if [ $issues -eq 0 ]; then
        echo -e "  🎯 ${GREEN}DISTROLESS COMPLIANT${NC}"
        ((DISTROLESS_COMPLIANT++))
    else
        echo -e "  🚨 ${RED}NON-COMPLIANT ($issues issues)${NC}"
        ((NON_DISTROLESS++))
        ((ISSUES_FOUND += issues))
    fi
    
    return $issues
}

# Function to check import pathway consistency
check_import_pathways() {
    local dockerfile="$1"
    local pathway_issues=0
    
    echo -e "\n${BLUE}🔗 Import Pathway Analysis: $dockerfile${NC}"
    
    # Check Python import pathways
    if grep -q "FROM gcr.io/distroless/python3" "$dockerfile"; then
        if grep -q "COPY --from=builder /usr/local/lib/python3" "$dockerfile"; then
            echo -e "  ✅ ${GREEN}Python library path correct${NC}"
        else
            echo -e "  ❌ ${RED}Python library path missing${NC}"
            ((pathway_issues++))
        fi
        
        if grep -q "COPY --from=builder /usr/local/bin/python3" "$dockerfile"; then
            echo -e "  ✅ ${GREEN}Python binary path correct${NC}"
        else
            echo -e "  ❌ ${RED}Python binary path missing${NC}"
            ((pathway_issues++))
        fi
    fi
    
    # Check Node.js import pathways
    if grep -q "FROM gcr.io/distroless/nodejs" "$dockerfile"; then
        if grep -q "COPY --from=builder /usr/local/lib/node_modules" "$dockerfile"; then
            echo -e "  ✅ ${GREEN}Node.js modules path correct${NC}"
        else
            echo -e "  ❌ ${RED}Node.js modules path missing${NC}"
            ((pathway_issues++))
        fi
        
        if grep -q "COPY --from=builder /usr/local/bin/node" "$dockerfile"; then
            echo -e "  ✅ ${GREEN}Node.js binary path correct${NC}"
        else
            echo -e "  ❌ ${RED}Node.js binary path missing${NC}"
            ((pathway_issues++))
        fi
    fi
    
    # Check system utilities
    if grep -q "COPY --from=builder /usr/bin/curl\|COPY --from=builder /bin/nc\|COPY --from=builder /usr/bin/jq" "$dockerfile"; then
        echo -e "  ✅ ${GREEN}System utilities included${NC}"
    else
        echo -e "  ⚠️  ${YELLOW}System utilities may be missing${NC}"
    fi
    
    return $pathway_issues
}

# Main verification process
echo -e "${BLUE}🔍 Scanning for Dockerfiles...${NC}"

# Find all Dockerfiles
DOCKERFILES=$(find . -name "Dockerfile*" -type f | sort)

if [ -z "$DOCKERFILES" ]; then
    echo -e "${RED}❌ No Dockerfiles found${NC}"
    exit 1
fi

echo -e "${GREEN}Found $(echo "$DOCKERFILES" | wc -l) Dockerfiles${NC}"

# Process each Dockerfile
while IFS= read -r dockerfile; do
    ((TOTAL_DOCKERFILES++))
    
    # Skip if file doesn't exist or is empty
    if [ ! -f "$dockerfile" ] || [ ! -s "$dockerfile" ]; then
        echo -e "${YELLOW}⚠️  Skipping empty or missing file: $dockerfile${NC}"
        continue
    fi
    
    # Check distroless compliance
    check_distroless_compliance "$dockerfile"
    
    # Check import pathways
    check_import_pathways "$dockerfile"
    
done <<< "$DOCKERFILES"

# Generate summary report
echo -e "\n${BLUE}📊 COMPLIANCE SUMMARY${NC}"
echo "===================="
echo -e "Total Dockerfiles: ${BLUE}$TOTAL_DOCKERFILES${NC}"
echo -e "Distroless Compliant: ${GREEN}$DISTROLESS_COMPLIANT${NC}"
echo -e "Non-Compliant: ${RED}$NON_DISTROLESS${NC}"
echo -e "Total Issues Found: ${RED}$ISSUES_FOUND${NC}"

# Calculate compliance percentage
if [ $TOTAL_DOCKERFILES -gt 0 ]; then
    COMPLIANCE_PERCENT=$((DISTROLESS_COMPLIANT * 100 / TOTAL_DOCKERFILES))
    echo -e "Compliance Rate: ${BLUE}${COMPLIANCE_PERCENT}%${NC}"
fi

# Provide recommendations
echo -e "\n${BLUE}💡 RECOMMENDATIONS${NC}"
echo "=================="

if [ $NON_DISTROLESS -gt 0 ]; then
    echo -e "${YELLOW}⚠️  $NON_DISTROLESS Dockerfiles need conversion to distroless${NC}"
    echo -e "   - Use multi-stage builds with distroless base images"
    echo -e "   - Implement non-root user execution"
    echo -e "   - Add health checks and proper metadata"
    echo -e "   - Follow import pathway standards"
fi

if [ $ISSUES_FOUND -gt 0 ]; then
    echo -e "${RED}🚨 $ISSUES_FOUND total issues need resolution${NC}"
    echo -e "   - Review DISTROLESS_STANDARDS.md for guidance"
    echo -e "   - Use provided templates for new services"
    echo -e "   - Run this script regularly to maintain compliance"
fi

if [ $DISTROLESS_COMPLIANT -eq $TOTAL_DOCKERFILES ] && [ $TOTAL_DOCKERFILES -gt 0 ]; then
    echo -e "${GREEN}🎉 All Dockerfiles are distroless compliant!${NC}"
    echo -e "   - Excellent security posture maintained"
    echo -e "   - Minimal attack surface achieved"
    echo -e "   - Production-ready deployment standards met"
fi

# Exit with appropriate code
if [ $NON_DISTROLESS -gt 0 ]; then
    echo -e "\n${RED}❌ Compliance verification failed${NC}"
    exit 1
else
    echo -e "\n${GREEN}✅ Compliance verification passed${NC}"
    exit 0
fi
