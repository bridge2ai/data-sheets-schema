#!/bin/bash
#
# Batch LLM Evaluation Script for Concatenated D4D Files
#
# This script performs reproducible LLM-as-judge quality evaluation
# on all concatenated D4D YAML files using Claude Sonnet 4.5.
#
# Requirements:
#   - ANTHROPIC_API_KEY environment variable must be set
#   - Poetry environment with anthropic package
#
# Usage:
#   ./src/evaluation/batch_evaluate_concatenated.sh [OPTIONS]
#
# Options:
#   --output-dir DIR    Output directory (default: data/evaluation_llm)
#   --rubric RUBRIC     Which rubric: rubric10, rubric20, both (default: both)
#   --dry-run           Show what would be evaluated without running
#   --help              Show this help message
#
# Reproducibility:
#   - Temperature: 0.0 (fully deterministic)
#   - Model: claude-sonnet-4-5-20250929 (date-pinned)
#   - Same D4D file → Same quality score every time
#
# Author: Claude Code
# Date: 2025-12-06

set -e

# Default configuration
OUTPUT_DIR="data/evaluation_llm"
RUBRIC="both"
DRY_RUN=false

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --output-dir)
            OUTPUT_DIR="$2"
            shift 2
            ;;
        --rubric)
            RUBRIC="$2"
            shift 2
            ;;
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --help)
            head -n 30 "$0" | grep "^#" | sed 's/^# \?//'
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Check requirements
if [ -z "$ANTHROPIC_API_KEY" ]; then
    echo "❌ ERROR: ANTHROPIC_API_KEY environment variable is not set"
    echo ""
    echo "Please set your Anthropic API key:"
    echo "  export ANTHROPIC_API_KEY=sk-ant-your-key-here"
    echo ""
    echo "Or add to your shell profile (.bashrc, .zshrc, etc.):"
    echo "  echo 'export ANTHROPIC_API_KEY=sk-ant-your-key' >> ~/.bashrc"
    echo ""
    exit 1
fi

# Check poetry environment
if ! command -v poetry &> /dev/null; then
    echo "❌ ERROR: Poetry not found"
    echo "Install with: curl -sSL https://install.python-poetry.org | python3 -"
    exit 1
fi

# Print configuration
echo "═══════════════════════════════════════════════════════════"
echo "D4D LLM EVALUATION - Concatenated Files"
echo "═══════════════════════════════════════════════════════════"
echo ""
echo "Configuration:"
echo "  Output directory: $OUTPUT_DIR"
echo "  Rubric: $RUBRIC"
echo "  Model: claude-sonnet-4-5-20250929"
echo "  Temperature: 0.0 (fully deterministic)"
echo "  Dry run: $DRY_RUN"
echo ""

# Create output directory
mkdir -p "$OUTPUT_DIR"

# Define projects and methods
PROJECTS=("AI_READI" "CHORUS" "CM4AI" "VOICE")
METHODS=("curated" "gpt5" "claudecode" "claudecode_agent" "claudecode_assistant")

# Count files
TOTAL_FILES=0
for PROJECT in "${PROJECTS[@]}"; do
    for METHOD in "${METHODS[@]}"; do
        FILE="data/d4d_concatenated/${METHOD}/${PROJECT}_d4d.yaml"
        if [ -f "$FILE" ]; then
            TOTAL_FILES=$((TOTAL_FILES + 1))
        fi
    done
done

# Calculate estimates
EVALUATIONS_PER_FILE=1
if [ "$RUBRIC" = "both" ]; then
    EVALUATIONS_PER_FILE=2
fi

TOTAL_EVALUATIONS=$((TOTAL_FILES * EVALUATIONS_PER_FILE))
ESTIMATED_MINUTES=$((TOTAL_EVALUATIONS * 45 / 60))
ESTIMATED_COST=$(echo "scale=2; $TOTAL_EVALUATIONS * 0.20" | bc)

echo "Scope:"
echo "  Files to evaluate: $TOTAL_FILES"
echo "  Total evaluations: $TOTAL_EVALUATIONS (${TOTAL_FILES} files × ${EVALUATIONS_PER_FILE} rubrics)"
echo ""
echo "Estimates:"
echo "  Time: ~${ESTIMATED_MINUTES} minutes"
echo "  Cost: ~\$${ESTIMATED_COST} (at \$0.20/evaluation avg)"
echo ""

if [ "$DRY_RUN" = true ]; then
    echo "═══════════════════════════════════════════════════════════"
    echo "DRY RUN - Files that would be evaluated:"
    echo "═══════════════════════════════════════════════════════════"
    echo ""

    for PROJECT in "${PROJECTS[@]}"; do
        for METHOD in "${METHODS[@]}"; do
            FILE="data/d4d_concatenated/${METHOD}/${PROJECT}_d4d.yaml"
            if [ -f "$FILE" ]; then
                echo "✓ $PROJECT / $METHOD"
                echo "  $FILE"
            else
                echo "⊘ $PROJECT / $METHOD (not found)"
            fi
        done
    done

    echo ""
    echo "To run actual evaluation, remove --dry-run flag"
    exit 0
fi

# Confirm before proceeding
echo "═══════════════════════════════════════════════════════════"
read -p "Proceed with evaluation? [y/N] " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Evaluation cancelled"
    exit 0
fi

echo "═══════════════════════════════════════════════════════════"
echo "Starting evaluation..."
echo "═══════════════════════════════════════════════════════════"
echo ""

# Counters
EVALUATED=0
SUCCESS=0
FAILED=0
START_TIME=$(date +%s)

# Evaluate each file
for PROJECT in "${PROJECTS[@]}"; do
    for METHOD in "${METHODS[@]}"; do
        FILE="data/d4d_concatenated/${METHOD}/${PROJECT}_d4d.yaml"

        # Skip if file doesn't exist
        if [ ! -f "$FILE" ]; then
            echo "⊘ Skipping $PROJECT/$METHOD (file not found)"
            continue
        fi

        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        echo "📊 Evaluating [$((EVALUATED + 1))/$TOTAL_FILES]: $PROJECT / $METHOD"
        echo "   File: $FILE"
        echo "   Rubric: $RUBRIC"
        echo ""

        EVALUATED=$((EVALUATED + 1))

        # Run evaluation
        if poetry run python src/evaluation/evaluate_d4d_llm.py \
            --file "$FILE" \
            --project "$PROJECT" \
            --method "$METHOD" \
            --rubric "$RUBRIC" \
            --output-dir "$OUTPUT_DIR"; then
            echo "✅ Success: $PROJECT/$METHOD"
            SUCCESS=$((SUCCESS + 1))
        else
            echo "❌ Failed: $PROJECT/$METHOD"
            FAILED=$((FAILED + 1))
        fi
        echo ""
    done
done

# Calculate elapsed time
END_TIME=$(date +%s)
ELAPSED_SECONDS=$((END_TIME - START_TIME))
ELAPSED_MINUTES=$((ELAPSED_SECONDS / 60))
ELAPSED_SECONDS_REMAINDER=$((ELAPSED_SECONDS % 60))

echo "═══════════════════════════════════════════════════════════"
echo "EVALUATION COMPLETE"
echo "═══════════════════════════════════════════════════════════"
echo ""
echo "Summary:"
echo "  Files evaluated: $EVALUATED"
echo "  Successful: $SUCCESS"
echo "  Failed: $FAILED"
echo "  Elapsed time: ${ELAPSED_MINUTES}m ${ELAPSED_SECONDS_REMAINDER}s"
echo ""
echo "Results saved to: $OUTPUT_DIR"
echo ""

if [ "$RUBRIC" = "both" ] || [ "$RUBRIC" = "rubric10" ]; then
    if [ -f "$OUTPUT_DIR/rubric10/summary_report.md" ]; then
        echo "📊 Rubric10 Summary: $OUTPUT_DIR/rubric10/summary_report.md"
    fi
fi

if [ "$RUBRIC" = "both" ] || [ "$RUBRIC" = "rubric20" ]; then
    if [ -f "$OUTPUT_DIR/rubric20/summary_report.md" ]; then
        echo "📊 Rubric20 Summary: $OUTPUT_DIR/rubric20/summary_report.md"
    fi
fi

echo ""
echo "View detailed results:"
echo "  make eval-llm-summary"
echo ""

if [ $FAILED -gt 0 ]; then
    exit 1
fi
