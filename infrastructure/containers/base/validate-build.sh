#!/bin/bash
# infrastructure/containers/base/validate-build.sh
# File: /app/configs/base/validate-build.sh
# x-lucid-file-path: /app/configs/base/validate-build.sh
# x-lucid-file-directory: /app/configs/base
# x-lucid-file-type: shell
# Validate distroless base image builds
# Ensures all required files and configurations are present

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🔍 Validating Lucid Base Images Build Environment${NC}"
echo -e "${BLUE}===============================================${NC}"

# Track validation results
VALIDATION_PASSED=true

# Function to check file existence
check_file() {
    local file="$1"
    local description="$2"
    
    if [ -f "$file" ]; then
        echo -e "${GREEN}✅ $description: $file${NC}"
        return 0
    else
        echo -e "${RED}❌ $description: $file (MISSING)${NC}"
        VALIDATION_PASSED=false
        return 1
    fi
}

# Function to check directory existence
check_dir() {
    local dir="$1"
    local description="$2"
    
    if [ -d "$dir" ]; then
        echo -e "${GREEN}✅ $description: $dir${NC}"
        return 0
    else
        echo -e "${RED}❌ $description: $dir (MISSING)${NC}"
        VALIDATION_PASSED=false
        return 1
    fi
}

# Function to check command availability
check_command() {
    local cmd="$1"
    local description="$2"
    
    if command -v "$cmd" >/dev/null 2>&1; then
        echo -e "${GREEN}✅ $description: $cmd${NC}"
        return 0
    else
        echo -e "${RED}❌ $description: $cmd (NOT FOUND)${NC}"
        VALIDATION_PASSED=false
        return 1
    fi
}

echo -e "${YELLOW}📋 Checking Required Files...${NC}"

# Check Docker files
check_file "Dockerfile.python-base" "Python Dockerfile"
check_file "Dockerfile.java-base" "Java Dockerfile"

# Check dependency files
check_file "requirements.txt" "Python requirements"
check_file "pom.xml" "Maven configuration"
check_file "build.gradle" "Gradle configuration"
check_file "gradle.properties" "Gradle properties"

# Check build scripts
check_file "build-base-images.sh" "Build script"
check_file "docker-compose.base.yml" "Docker Compose"

# Check configuration files
check_file "env.template" "Environment template"
check_file "build.config.yml" "Build configuration"
check_file ".dockerignore" "Docker ignore"
check_file "README.md" "Documentation"

echo -e "${YELLOW}📋 Checking Required Commands...${NC}"

# Check Docker
check_command "docker" "Docker"
check_command "docker" "Docker Buildx"

# Check if Docker is running
if docker info >/dev/null 2>&1; then
    echo -e "${GREEN}✅ Docker is running${NC}"
else
    echo -e "${RED}❌ Docker is not running${NC}"
    VALIDATION_PASSED=false
fi

# Check Docker Buildx
if docker buildx version >/dev/null 2>&1; then
    echo -e "${GREEN}✅ Docker Buildx is available${NC}"
else
    echo -e "${RED}❌ Docker Buildx is not available${NC}"
    VALIDATION_PASSED=false
fi

# Check Git
check_command "git" "Git"

echo -e "${YELLOW}📋 Checking Build Environment...${NC}"

# Check if we're in the right directory
if [ -f "Dockerfile.python-base" ] && [ -f "Dockerfile.java-base" ]; then
    echo -e "${GREEN}✅ In correct build directory${NC}"
else
    echo -e "${RED}❌ Not in correct build directory${NC}"
    echo -e "${YELLOW}💡 Please run this script from infrastructure/containers/base/${NC}"
    VALIDATION_PASSED=false
fi

# Check Docker Buildx builder
if docker buildx ls | grep -q "lucid-builder"; then
    echo -e "${GREEN}✅ Docker Buildx builder 'lucid-builder' exists${NC}"
else
    echo -e "${YELLOW}⚠️  Docker Buildx builder 'lucid-builder' not found${NC}"
    echo -e "${YELLOW}💡 Will be created during build process${NC}"
fi

echo -e "${YELLOW}📋 Checking File Permissions...${NC}"

# Check script permissions
if [ -x "build-base-images.sh" ]; then
    echo -e "${GREEN}✅ Build script is executable${NC}"
else
    echo -e "${YELLOW}⚠️  Build script is not executable${NC}"
    echo -e "${YELLOW}💡 Run: chmod +x build-base-images.sh${NC}"
fi

# Check if we can write to current directory
if [ -w "." ]; then
    echo -e "${GREEN}✅ Write permissions to current directory${NC}"
else
    echo -e "${RED}❌ No write permissions to current directory${NC}"
    VALIDATION_PASSED=false
fi

echo -e "${YELLOW}📋 Checking Network Connectivity...${NC}"

# Check if we can reach GitHub Container Registry
if curl -s --connect-timeout 5 https://ghcr.io >/dev/null 2>&1; then
    echo -e "${GREEN}✅ GitHub Container Registry is reachable${NC}"
else
    echo -e "${YELLOW}⚠️  GitHub Container Registry is not reachable${NC}"
    echo -e "${YELLOW}💡 Check your network connection${NC}"
fi

# Check if we can reach Google Container Registry
if curl -s --connect-timeout 5 https://gcr.io >/dev/null 2>&1; then
    echo -e "${GREEN}✅ Google Container Registry is reachable${NC}"
else
    echo -e "${YELLOW}⚠️  Google Container Registry is not reachable${NC}"
    echo -e "${YELLOW}💡 Check your network connection${NC}"
fi

echo -e "${YELLOW}📋 Checking Docker Images...${NC}"

# Check if base images exist locally
if docker images lucid-python-base:latest --format "table {{.Repository}}" | grep -q "lucid-python-base"; then
    echo -e "${GREEN}✅ Python base image exists locally${NC}"
else
    echo -e "${YELLOW}⚠️  Python base image not found locally${NC}"
fi

if docker images lucid-java-base:latest --format "table {{.Repository}}" | grep -q "lucid-java-base"; then
    echo -e "${GREEN}✅ Java base image exists locally${NC}"
else
    echo -e "${YELLOW}⚠️  Java base image not found locally${NC}"
fi

echo ""
echo -e "${BLUE}📊 Validation Summary${NC}"
echo -e "${BLUE}===================${NC}"

if [ "$VALIDATION_PASSED" = true ]; then
    echo -e "${GREEN}🎉 All validations passed! Ready to build base images.${NC}"
    echo ""
    echo -e "${BLUE}🚀 Next Steps:${NC}"
    echo -e "  1. Run: ./build-base-images.sh"
    echo -e "  2. Or run: ./scripts/foundation/build-distroless-base-images.sh"
    echo -e "  3. Verify images in GitHub Container Registry"
    exit 0
else
    echo -e "${RED}❌ Some validations failed. Please fix the issues above.${NC}"
    echo ""
    echo -e "${BLUE}🔧 Common Fixes:${NC}"
    echo -e "  • Install Docker and Docker Buildx"
    echo -e "  • Start Docker service"
    echo -e "  • Check network connectivity"
    echo -e "  • Verify file permissions"
    echo -e "  • Run from correct directory"
    exit 1
fi
