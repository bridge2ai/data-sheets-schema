#!/bin/bash
# Prerequisites validation script for GitHub D4D Assistant
#
# Validates that all required files and resources are available before D4D generation.
# FAILS FAST if prerequisites are not met to save time and API costs.
#
# Exit codes:
#   0 - All prerequisites validated
#   1 - Prerequisites validation failed
#
# Usage:
#   ./src/github/validate_prerequisites.sh --dataset mydataset --mode file
#   ./src/github/validate_prerequisites.sh --dataset mydataset --mode url --urls "url1 url2"
#
# Author: Claude Code
# Version: 1.0.0
# Last Updated: 2025-02-10

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Parse arguments
DATASET=""
MODE=""
URLS=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --dataset)
            DATASET="$2"
            shift 2
            ;;
        --mode)
            MODE="$2"
            shift 2
            ;;
        --urls)
            URLS="$2"
            shift 2
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

echo "🔍 Validating Prerequisites"
echo "============================"
echo ""

# Track validation status
VALIDATION_FAILED=0

# Check schema exists
echo -n "📋 Checking schema file... "
SCHEMA_PATH="src/data_sheets_schema/schema/data_sheets_schema_all.yaml"
if [ -f "$SCHEMA_PATH" ]; then
    echo -e "${GREEN}✓ Found${NC}"
else
    echo -e "${RED}✗ Not found${NC}"
    echo "   Expected: $SCHEMA_PATH"
    VALIDATION_FAILED=1
fi

# Check system prompt exists
echo -n "📝 Checking system prompt... "
SYSTEM_PROMPT="src/download/prompts/d4d_concatenated_system_prompt.txt"
if [ -f "$SYSTEM_PROMPT" ]; then
    echo -e "${GREEN}✓ Found${NC}"
else
    echo -e "${RED}✗ Not found${NC}"
    echo "   Expected: $SYSTEM_PROMPT"
    VALIDATION_FAILED=1
fi

# Check user prompt exists
echo -n "📝 Checking user prompt... "
USER_PROMPT="src/download/prompts/d4d_concatenated_user_prompt.txt"
if [ -f "$USER_PROMPT" ]; then
    echo -e "${GREEN}✓ Found${NC}"
else
    echo -e "${RED}✗ Not found${NC}"
    echo "   Expected: $USER_PROMPT"
    VALIDATION_FAILED=1
fi

# Check config file exists
echo -n "⚙️  Checking config file... "
CONFIG_FILE=".github/workflows/d4d_assistant_deterministic_config.yaml"
if [ -f "$CONFIG_FILE" ]; then
    echo -e "${GREEN}✓ Found${NC}"
else
    echo -e "${YELLOW}⚠ Not found (optional)${NC}"
    echo "   Expected: $CONFIG_FILE"
fi

# Mode-specific checks
if [ "$MODE" = "file" ]; then
    echo -n "📁 Checking input files (file mode)... "
    INPUT_DIR="data/sheets_d4dassistant/inputs/${DATASET}"
    if [ -d "$INPUT_DIR" ]; then
        file_count=$(ls "$INPUT_DIR" 2>/dev/null | wc -l)
        if [ "$file_count" -eq 0 ]; then
            echo -e "${RED}✗ No files${NC}"
            echo "   Directory exists but contains no files: $INPUT_DIR"
            VALIDATION_FAILED=1
        else
            echo -e "${GREEN}✓ Found $file_count file(s)${NC}"
        fi
    else
        echo -e "${RED}✗ Directory not found${NC}"
        echo "   Expected: $INPUT_DIR"
        VALIDATION_FAILED=1
    fi

elif [ "$MODE" = "url" ]; then
    echo "🌐 Checking URLs accessibility (url mode)..."
    if [ -z "$URLS" ]; then
        echo -e "   ${RED}✗ No URLs provided${NC}"
        VALIDATION_FAILED=1
    else
        for url in $URLS; do
            echo -n "   $url ... "
            # Try to fetch HTTP status with timeout
            status=$(curl -sI -m 10 "$url" 2>/dev/null | head -1 | cut -d' ' -f2)
            if [ "$status" = "200" ]; then
                echo -e "${GREEN}✓ Accessible${NC}"
            elif [ -z "$status" ]; then
                echo -e "${YELLOW}⚠ Connection timeout${NC}"
                echo "      Warning: URL may not be accessible"
            else
                echo -e "${YELLOW}⚠ Status: $status${NC}"
                echo "      Warning: URL returned non-200 status"
            fi
        done
    fi
fi

# Check Python dependencies
echo -n "🐍 Checking Python dependencies... "
if python3 -c "import yaml, anthropic" 2>/dev/null; then
    echo -e "${GREEN}✓ Available${NC}"
else
    echo -e "${RED}✗ Missing${NC}"
    echo "   Required: pyyaml, anthropic"
    echo "   Install with: pip install pyyaml anthropic"
    VALIDATION_FAILED=1
fi

# Check ANTHROPIC_API_KEY
echo -n "🔑 Checking API key... "
if [ -n "$ANTHROPIC_API_KEY" ]; then
    echo -e "${GREEN}✓ Set${NC}"
else
    echo -e "${RED}✗ Not set${NC}"
    echo "   Required: ANTHROPIC_API_KEY environment variable"
    echo "   Export with: export ANTHROPIC_API_KEY=sk-ant-..."
    VALIDATION_FAILED=1
fi

# Check output directory
echo -n "📂 Checking output directory... "
OUTPUT_DIR="data/sheets_d4dassistant"
if [ -d "$OUTPUT_DIR" ]; then
    echo -e "${GREEN}✓ Exists${NC}"
else
    echo -e "${YELLOW}⚠ Creating${NC}"
    mkdir -p "$OUTPUT_DIR"
    echo "   Created: $OUTPUT_DIR"
fi

# Summary
echo ""
echo "============================"
if [ $VALIDATION_FAILED -eq 0 ]; then
    echo -e "${GREEN}✅ All prerequisites validated${NC}"
    echo ""
    echo "Ready to proceed with D4D generation."
    exit 0
else
    echo -e "${RED}❌ Prerequisites validation failed${NC}"
    echo ""
    echo "Please fix the issues above before proceeding."
    echo "D4D generation cannot continue until prerequisites are met."
    exit 1
fi
