#!/bin/bash
# Verification script for Lucid Session Docker images
# Verifies all session images are built correctly and ARM64 compatible

set -e

echo "=========================================="
echo "Verifying Lucid Session Docker Images"
echo "=========================================="
echo "Verification Date: $(date)"
echo ""

# Expected images
declare -a IMAGES=(
    "pickme/lucid-session-pipeline:latest-arm64"
    "pickme/lucid-session-recorder:latest-arm64"
    "pickme/lucid-chunk-processor:latest-arm64"
    "pickme/lucid-session-storage:latest-arm64"
    "pickme/lucid-session-api:latest-arm64"
)

# Expected ports
declare -A PORTS=(
    ["pickme/lucid-session-pipeline:latest-arm64"]="8083"
    ["pickme/lucid-session-recorder:latest-arm64"]="8084"
    ["pickme/lucid-chunk-processor:latest-arm64"]="8085"
    ["pickme/lucid-session-storage:latest-arm64"]="8086"
    ["pickme/lucid-session-api:latest-arm64"]="8087"
)

echo "Checking Docker images..."
echo ""

# Check if images exist
for image in "${IMAGES[@]}"; do
    echo "Verifying: $image"
    
    if docker image inspect "$image" >/dev/null 2>&1; then
        echo "  ✓ Image exists"
        
        # Check platform
        platform=$(docker image inspect "$image" --format '{{.Architecture}}')
        if [[ "$platform" == "arm64" ]]; then
            echo "  ✓ ARM64 architecture confirmed"
        else
            echo "  ✗ Wrong architecture: $platform (expected: arm64)"
        fi
        
        # Check size
        size=$(docker image inspect "$image" --format '{{.Size}}')
        size_mb=$((size / 1024 / 1024))
        echo "  ✓ Image size: ${size_mb}MB"
        
        # Check if image has required labels
        service_name=$(docker image inspect "$image" --format '{{index .Config.Labels "SERVICE_NAME"}}' 2>/dev/null || echo "")
        if [[ -n "$service_name" ]]; then
            echo "  ✓ Service name label: $service_name"
        else
            echo "  ⚠ No service name label found"
        fi
        
    else
        echo "  ✗ Image not found"
    fi
    
    echo ""
done

echo "Checking Docker Compose configuration..."
echo ""

# Check if docker-compose file exists and is valid
if [[ -f "build/docker-compose.session-images.yml" ]]; then
    echo "✓ Docker Compose file exists"
    
    # Validate docker-compose syntax
    if docker-compose -f build/docker-compose.session-images.yml config >/dev/null 2>&1; then
        echo "✓ Docker Compose syntax is valid"
    else
        echo "✗ Docker Compose syntax error"
    fi
else
    echo "✗ Docker Compose file not found"
fi

echo ""
echo "Checking build scripts..."
echo ""

# Check if build scripts exist and are executable
declare -a SCRIPTS=(
    "build/scripts/build-session-pipeline.sh"
    "build/scripts/build-session-recorder.sh"
    "build/scripts/build-chunk-processor.sh"
    "build/scripts/build-session-storage.sh"
    "build/scripts/build-session-api.sh"
    "build/scripts/build-all-session-images.sh"
)

for script in "${SCRIPTS[@]}"; do
    if [[ -f "$script" ]]; then
        echo "✓ $script exists"
        if [[ -x "$script" ]]; then
            echo "  ✓ Executable"
        else
            echo "  ✗ Not executable"
        fi
    else
        echo "✗ $script not found"
    fi
done

echo ""
echo "Checking Dockerfiles..."
echo ""

# Check if Dockerfiles exist
declare -a DOCKERFILES=(
    "sessions/Dockerfile.pipeline"
    "sessions/Dockerfile.recorder"
    "sessions/Dockerfile.processor"
    "sessions/Dockerfile.storage"
    "sessions/Dockerfile.api"
)

for dockerfile in "${DOCKERFILES[@]}"; do
    if [[ -f "$dockerfile" ]]; then
        echo "✓ $dockerfile exists"
        
        # Check if it's ARM64 compatible
        if grep -q "linux/arm64" "$dockerfile" || grep -q "platform.*arm64" "$dockerfile"; then
            echo "  ✓ ARM64 compatible"
        else
            echo "  ⚠ ARM64 compatibility not explicitly set"
        fi
        
        # Check if it uses distroless base
        if grep -q "distroless" "$dockerfile"; then
            echo "  ✓ Uses distroless base"
        else
            echo "  ⚠ Not using distroless base"
        fi
        
    else
        echo "✗ $dockerfile not found"
    fi
done

echo ""
echo "=========================================="
echo "Verification Summary"
echo "=========================================="

# Count successful verifications
total_checks=0
passed_checks=0

# Count images
for image in "${IMAGES[@]}"; do
    total_checks=$((total_checks + 1))
    if docker image inspect "$image" >/dev/null 2>&1; then
        passed_checks=$((passed_checks + 1))
    fi
done

# Count scripts
for script in "${SCRIPTS[@]}"; do
    total_checks=$((total_checks + 1))
    if [[ -f "$script" && -x "$script" ]]; then
        passed_checks=$((passed_checks + 1))
    fi
done

# Count dockerfiles
for dockerfile in "${DOCKERFILES[@]}"; do
    total_checks=$((total_checks + 1))
    if [[ -f "$dockerfile" ]]; then
        passed_checks=$((passed_checks + 1))
    fi
done

echo "Total checks: $total_checks"
echo "Passed checks: $passed_checks"
echo "Success rate: $(( (passed_checks * 100) / total_checks ))%"

if [[ $passed_checks -eq $total_checks ]]; then
    echo "✓ All verifications passed!"
    exit 0
else
    echo "✗ Some verifications failed!"
    exit 1
fi
