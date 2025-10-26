#!/bin/bash

# Lucid Hybrid Base Image Approach - Build Verification Script
# This script verifies that the hybrid approach is correctly implemented

set -e

echo "🔍 Lucid Hybrid Base Image Approach - Build Verification"
echo "========================================================"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    local status=$1
    local message=$2
    case $status in
        "SUCCESS")
            echo -e "${GREEN}✅ $message${NC}"
            ;;
        "ERROR")
            echo -e "${RED}❌ $message${NC}"
            ;;
        "WARNING")
            echo -e "${YELLOW}⚠️  $message${NC}"
            ;;
        "INFO")
            echo -e "${BLUE}ℹ️  $message${NC}"
            ;;
    esac
}

# Function to check if Dockerfile uses correct base image
check_dockerfile_base() {
    local dockerfile=$1
    local expected_base=$2
    local service_name=$3
    
    if [ ! -f "$dockerfile" ]; then
        print_status "ERROR" "Dockerfile not found: $dockerfile"
        return 1
    fi
    
    if grep -q "FROM $expected_base" "$dockerfile"; then
        print_status "SUCCESS" "$service_name uses correct base image: $expected_base"
        return 0
    else
        print_status "ERROR" "$service_name does not use expected base image: $expected_base"
        return 1
    fi
}

echo ""
echo "📋 Verifying Foundation Services (Direct Distroless Images)"
echo "--------------------------------------------------------"

# Check Foundation Services use direct distroless images
foundation_services=(
    "infrastructure/containers/storage/Dockerfile.mongodb|gcr.io/distroless/base-debian12|MongoDB"
    "infrastructure/containers/storage/Dockerfile.redis|gcr.io/distroless/base-debian12|Redis"
    "infrastructure/containers/storage/Dockerfile.elasticsearch|gcr.io/distroless/base-debian12|Elasticsearch"
)

foundation_success=0
for service in "${foundation_services[@]}"; do
    IFS='|' read -r dockerfile expected_base service_name <<< "$service"
    if check_dockerfile_base "$dockerfile" "$expected_base" "$service_name"; then
        ((foundation_success++))
    fi
done

echo ""
echo "📋 Verifying Application Services (Direct Distroless Images)"
echo "----------------------------------------------------------"

# Check Application Services use direct distroless images
application_services=(
    "03-api-gateway/Dockerfile|gcr.io/distroless/python3-debian12|API Gateway"
    "auth/Dockerfile|gcr.io/distroless/python3-debian12|Auth Service"
    "blockchain/Dockerfile.engine|gcr.io/distroless/python3-debian12|Blockchain Engine"
    "sessions/Dockerfile.api|gcr.io/distroless/python3-debian12|Session API"
    "RDP/Dockerfile.controller|gcr.io/distroless/python3-debian12|RDP Controller"
)

application_success=0
for service in "${application_services[@]}"; do
    IFS='|' read -r dockerfile expected_base service_name <<< "$service"
    if check_dockerfile_base "$dockerfile" "$expected_base" "$service_name"; then
        ((application_success++))
    fi
done

echo ""
echo "📋 Verifying GitHub Actions Workflow Configuration"
echo "------------------------------------------------"

# Check if GitHub Actions workflow includes base image build
if [ -f ".github/workflows/build-phase1.yml" ]; then
    if grep -q "build-base-images:" ".github/workflows/build-phase1.yml"; then
        print_status "SUCCESS" "GitHub Actions workflow includes base image build job"
    else
        print_status "ERROR" "GitHub Actions workflow missing base image build job"
    fi
    
    if grep -q "needs:.*build-base-images" ".github/workflows/build-phase1.yml"; then
        print_status "SUCCESS" "Foundation services depend on base image build"
    else
        print_status "ERROR" "Foundation services missing dependency on base image build"
    fi
else
    print_status "ERROR" "GitHub Actions workflow file not found"
fi

echo ""
echo "📋 Verifying Docker Compose Configuration"
echo "----------------------------------------"

# Check if docker-compose.pi.yml uses correct image names
if [ -f "docker-compose.pi.yml" ]; then
    if grep -q "pickme/lucid-mongodb:latest-arm64" "docker-compose.pi.yml"; then
        print_status "SUCCESS" "Docker Compose uses custom MongoDB image"
    else
        print_status "ERROR" "Docker Compose not using custom MongoDB image"
    fi
    
    if grep -q "pickme/lucid-redis:latest-arm64" "docker-compose.pi.yml"; then
        print_status "SUCCESS" "Docker Compose uses custom Redis image"
    else
        print_status "ERROR" "Docker Compose not using custom Redis image"
    fi
else
    print_status "ERROR" "Docker Compose file not found"
fi

echo ""
echo "📋 Verifying Documentation"
echo "-------------------------"

# Check if documentation exists
if [ -f "docs/architecture/HYBRID_BASE_IMAGE_APPROACH.md" ]; then
    print_status "SUCCESS" "Hybrid approach documentation exists"
else
    print_status "ERROR" "Hybrid approach documentation missing"
fi

echo ""
echo "📊 Verification Summary"
echo "====================="

total_foundation=${#foundation_services[@]}
total_application=${#application_services[@]}

print_status "INFO" "Foundation Services: $foundation_success/$total_foundation correct"
print_status "INFO" "Application Services: $application_success/$total_application correct"

if [ $foundation_success -eq $total_foundation ] && [ $application_success -eq $total_application ]; then
    print_status "SUCCESS" "All services using correct base images!"
    echo ""
    print_status "SUCCESS" "🎉 Hybrid Base Image Approach Implementation Complete!"
    echo ""
    echo "Next Steps:"
    echo "1. Build custom base images: docker build -f infrastructure/containers/base/Dockerfile.base -t pickme/lucid-base:latest-arm64 ."
    echo "2. Build foundation services: docker build -f infrastructure/containers/storage/Dockerfile.mongodb -t pickme/lucid-mongodb:latest-arm64 ."
    echo "3. Build application services: docker build -f 03-api-gateway/Dockerfile -t pickme/lucid-api-gateway:latest-arm64 ."
    echo "4. Test deployment: docker-compose -f docker-compose.pi.yml up -d"
    exit 0
else
    print_status "ERROR" "Some services not using correct base images"
    exit 1
fi
