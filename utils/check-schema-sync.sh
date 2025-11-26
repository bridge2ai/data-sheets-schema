#!/usr/bin/env bash
# Check if schema files are in sync
# Usage: ./utils/check-schema-sync.sh
#
# Verifies that:
# 1. data_sheets_schema_all.yaml (merged) is up to date with data_sheets_schema.yaml
# 2. data_sheets_schema.py (Python model) is up to date with data_sheets_schema.yaml
#
# Exit codes:
#   0 - Files are in sync
#   1 - Files are out of sync
#   2 - Error checking sync

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Get project root directory
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

# File paths
SOURCE_SCHEMA="src/data_sheets_schema/schema/data_sheets_schema.yaml"
MERGED_SCHEMA="src/data_sheets_schema/schema/data_sheets_schema_all.yaml"
PYTHON_MODEL="src/data_sheets_schema/datamodel/data_sheets_schema.py"

echo "Checking schema file synchronization..."
echo ""

# Check if files exist
if [[ ! -f "$SOURCE_SCHEMA" ]]; then
    echo -e "${RED}ERROR: Source schema not found: $SOURCE_SCHEMA${NC}"
    exit 2
fi

if [[ ! -f "$MERGED_SCHEMA" ]]; then
    echo -e "${YELLOW}WARNING: Merged schema not found: $MERGED_SCHEMA${NC}"
    echo "Run: make full-schema"
    exit 1
fi

if [[ ! -f "$PYTHON_MODEL" ]]; then
    echo -e "${YELLOW}WARNING: Python model not found: $PYTHON_MODEL${NC}"
    echo "Run: make gen-project"
    exit 1
fi

# Get modification times
SOURCE_TIME=$(stat -f %m "$SOURCE_SCHEMA" 2>/dev/null || stat -c %Y "$SOURCE_SCHEMA" 2>/dev/null || echo 0)
MERGED_TIME=$(stat -f %m "$MERGED_SCHEMA" 2>/dev/null || stat -c %Y "$MERGED_SCHEMA" 2>/dev/null || echo 0)
PYTHON_TIME=$(stat -f %m "$PYTHON_MODEL" 2>/dev/null || stat -c %Y "$PYTHON_MODEL" 2>/dev/null || echo 0)

# Check if module files are newer than source schema
MODULES_DIR="src/data_sheets_schema/schema"
NEWEST_MODULE_TIME=0
if [[ -d "$MODULES_DIR" ]]; then
    while IFS= read -r -d '' module_file; do
        MODULE_TIME=$(stat -f %m "$module_file" 2>/dev/null || stat -c %Y "$module_file" 2>/dev/null || echo 0)
        if [[ $MODULE_TIME -gt $NEWEST_MODULE_TIME ]]; then
            NEWEST_MODULE_TIME=$MODULE_TIME
            NEWEST_MODULE="$module_file"
        fi
    done < <(find "$MODULES_DIR" -name "D4D_*.yaml" -print0)
fi

# Use the newest timestamp between source and modules
if [[ $NEWEST_MODULE_TIME -gt $SOURCE_TIME ]]; then
    EFFECTIVE_SOURCE_TIME=$NEWEST_MODULE_TIME
    EFFECTIVE_SOURCE="$NEWEST_MODULE"
else
    EFFECTIVE_SOURCE_TIME=$SOURCE_TIME
    EFFECTIVE_SOURCE="$SOURCE_SCHEMA"
fi

# Status variables
OUT_OF_SYNC=0

# Check if merged schema is older than source/modules
if [[ $MERGED_TIME -lt $EFFECTIVE_SOURCE_TIME ]]; then
    echo -e "${RED}✗ Merged schema is out of date${NC}"
    echo "  Newest source:  $EFFECTIVE_SOURCE ($(date -r $EFFECTIVE_SOURCE_TIME))"
    echo "  Merged schema:  $MERGED_SCHEMA ($(date -r $MERGED_TIME))"
    echo "  Fix: make full-schema"
    echo ""
    OUT_OF_SYNC=1
else
    echo -e "${GREEN}✓ Merged schema is up to date${NC}"
fi

# Check if Python model is older than source/modules
if [[ $PYTHON_TIME -lt $EFFECTIVE_SOURCE_TIME ]]; then
    echo -e "${RED}✗ Python model is out of date${NC}"
    echo "  Newest source:  $EFFECTIVE_SOURCE ($(date -r $EFFECTIVE_SOURCE_TIME))"
    echo "  Python model:   $PYTHON_MODEL ($(date -r $PYTHON_TIME))"
    echo "  Fix: make gen-project"
    echo ""
    OUT_OF_SYNC=1
else
    echo -e "${GREEN}✓ Python model is up to date${NC}"
fi

# Summary
echo ""
if [[ $OUT_OF_SYNC -eq 0 ]]; then
    echo -e "${GREEN}All schema files are in sync ✓${NC}"
    exit 0
else
    echo -e "${RED}Schema files are OUT OF SYNC${NC}"
    echo ""
    echo "To fix, run:"
    echo "  make full-schema    # Regenerate merged schema"
    echo "  make gen-project    # Regenerate Python model and artifacts"
    echo ""
    echo "Or run both with:"
    echo "  make regen-all      # Force regenerate everything"
    exit 1
fi
