#!/bin/bash
# LUCID Project Repair Script
# 
# This script automatically repairs failed validations from validate-project.sh
# It addresses Python build alignment issues and Electron GUI alignment issues.
#
# Usage:
#   ./scripts/validation/repair-project.sh [--python-only] [--gui-only] [--verbose] [--dry-run]
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
DRY_RUN=false
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
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --project-root)
            PROJECT_ROOT="$2"
            shift 2
            ;;
        -h|--help)
            echo "LUCID Project Repair Script"
            echo ""
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --python-only     Fix only Python build alignment issues"
            echo "  --gui-only        Fix only Electron GUI alignment issues"
            echo "  --verbose         Enable verbose output"
            echo "  --dry-run         Show what would be done without making changes"
            echo "  --project-root    Set project root directory (default: .)"
            echo "  -h, --help        Show this help message"
            echo ""
            echo "Examples:"
            echo "  $0                    # Fix all validation issues"
            echo "  $0 --python-only      # Fix only Python issues"
            echo "  $0 --dry-run          # Show what would be fixed"
            echo "  $0 --verbose          # Show detailed output"
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
if [[ ! -f "README.md" && ! -d "scripts" ]]; then
    echo -e "${YELLOW}Warning: This doesn't appear to be the LUCID project root directory${NC}"
    echo "Current directory: $(pwd)"
    echo "Expected to find: README.md, scripts/"
    echo ""
    read -p "Continue anyway? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

echo -e "${BLUE}LUCID Project Repair Starting...${NC}"
echo "Project root: $PROJECT_ROOT"
echo "Python only: $PYTHON_ONLY"
echo "GUI only: $GUI_ONLY"
echo "Verbose: $VERBOSE"
echo "Dry run: $DRY_RUN"
echo ""

# Build command
CMD="python3 scripts/validation/repair-validation-failures.py"
if [[ "$PYTHON_ONLY" == true ]]; then
    CMD="$CMD --python-only"
fi
if [[ "$GUI_ONLY" == true ]]; then
    CMD="$CMD --gui-only"
fi
if [[ "$VERBOSE" == true ]]; then
    CMD="$CMD --verbose"
fi
if [[ "$DRY_RUN" == true ]]; then
    CMD="$CMD --dry-run"
fi
if [[ "$PROJECT_ROOT" != "." ]]; then
    CMD="$CMD --project-root $PROJECT_ROOT"
fi

echo -e "${BLUE}Running: $CMD${NC}"
echo ""

# Run the repair
if eval $CMD; then
    echo ""
    echo -e "${GREEN}🎉 All repairs completed successfully!${NC}"
    echo -e "${GREEN}Your LUCID project validation issues have been fixed.${NC}"
    echo ""
    echo -e "${BLUE}Next steps:${NC}"
    echo "1. Run validation again to verify fixes:"
    echo "   ./scripts/validation/validate-project.sh"
    echo ""
    echo "2. If issues persist, check the repair report above for details"
    echo ""
    exit 0
else
    echo ""
    echo -e "${RED}❌ Some repairs failed!${NC}"
    echo -e "${RED}Please review the output above and fix the issues manually.${NC}"
    echo ""
    echo -e "${YELLOW}For detailed information, check the repair report above.${NC}"
    echo ""
    echo -e "${BLUE}Manual repair suggestions:${NC}"
    echo "1. Check file permissions and directory access"
    echo "2. Ensure all required dependencies are installed"
    echo "3. Verify project structure matches expected layout"
    echo "4. Run with --verbose for more detailed error information"
    echo ""
    exit 1
fi
