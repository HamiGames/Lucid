#!/bin/bash
# LUCID Project Validation Script
# 
# This script runs comprehensive validation for the LUCID project
# including Python build alignment and Electron GUI alignment checks.
#
# Usage:
#   ./scripts/validation/validate-project.sh [--python-only] [--gui-only] [--verbose]
#
# Author: LUCID Project Team
# Version: 1.0.0

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
PYTHON_ONLY=false
GUI_ONLY=false
VERBOSE=false
PROJECT_ROOT="."

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --python-only)
            PYTHON_ONLY=true
            shift
            ;;
        --gui-only)
            GUI_ONLY=true
            shift
            ;;
        --verbose)
            VERBOSE=true
            shift
            ;;
        --project-root)
            PROJECT_ROOT="$2"
            shift 2
            ;;
        -h|--help)
            echo "LUCID Project Validation Script"
            echo ""
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --python-only     Run only Python build alignment validation"
            echo "  --gui-only        Run only Electron GUI alignment validation"
            echo "  --verbose         Enable verbose output"
            echo "  --project-root    Set project root directory (default: .)"
            echo "  -h, --help        Show this help message"
            echo ""
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Validate arguments
if [[ "$PYTHON_ONLY" == true && "$GUI_ONLY" == true ]]; then
    echo -e "${RED}Error: Cannot specify both --python-only and --gui-only${NC}"
    exit 1
fi

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Error: python3 not found. Please install Python 3.6 or higher.${NC}"
    exit 1
fi

# Check if we're in the right directory
if [[ ! -f "README.md" && ! -d "electron-gui" && ! -d "scripts" ]]; then
    echo -e "${YELLOW}Warning: This doesn't appear to be the LUCID project root directory${NC}"
    echo "Current directory: $(pwd)"
    echo "Expected to find: README.md, electron-gui/, scripts/"
    echo ""
    read -p "Continue anyway? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

echo -e "${BLUE}LUCID Project Validation Starting...${NC}"
echo "Project root: $PROJECT_ROOT"
echo "Python only: $PYTHON_ONLY"
echo "GUI only: $GUI_ONLY"
echo "Verbose: $VERBOSE"
echo ""

# Build command
CMD="python3 scripts/validation/run-complete-validation.py"
if [[ "$PYTHON_ONLY" == true ]]; then
    CMD="$CMD --python-only"
fi
if [[ "$GUI_ONLY" == true ]]; then
    CMD="$CMD --gui-only"
fi
if [[ "$VERBOSE" == true ]]; then
    CMD="$CMD --verbose"
fi
if [[ "$PROJECT_ROOT" != "." ]]; then
    CMD="$CMD --project-root $PROJECT_ROOT"
fi

echo -e "${BLUE}Running: $CMD${NC}"
echo ""

# Run the validation
if eval $CMD; then
    echo ""
    echo -e "${GREEN}🎉 All validations completed successfully!${NC}"
    echo -e "${GREEN}Your LUCID project is properly aligned with the build plan.${NC}"
    exit 0
else
    echo ""
    echo -e "${RED}❌ Some validations failed!${NC}"
    echo -e "${RED}Please review the output above and fix the issues.${NC}"
    echo ""
    echo -e "${YELLOW}For detailed information, check the validation-report.json file.${NC}"
    exit 1
fi
