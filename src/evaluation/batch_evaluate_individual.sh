#!/bin/bash
#
# Batch LLM Evaluation Script for Individual D4D Files
#
# This script performs reproducible LLM-as-judge quality evaluation
# on individual D4D YAML files (extracted from single source documents)
# using Claude Sonnet 4.5.
#
# Requirements:
#   - ANTHROPIC_API_KEY environment variable must be set
#   - Poetry environment with anthropic package
#
# Usage:
#   ./src/evaluation/batch_evaluate_individual.sh [OPTIONS]
#
# Options:
#   --output-dir DIR    Output directory (default: data/evaluation_llm_individual)
#   --rubric RUBRIC     Which rubric: rubric10, rubric20, both (default: both)
#   --method METHOD     Evaluate only specific method (gpt5, claudecode_agent, claudecode_assistant)
#   --project PROJECT   Evaluate only specific project (AI_READI, CHORUS, CM4AI, VOICE)
#   --dry-run           Show what would be evaluated without running
#   --help              Show this help message
#
# Reproducibility:
#   - Temperature: 0.0 (fully deterministic)
#   - Model: claude-sonnet-4-5-20250929 (date-pinned)
#   - Same D4D file → Same quality score every time
#
# Warning: This evaluates ~85 individual files and may take 2+ hours and cost ~$34
#
# Author: Claude Code
# Date: 2025-12-06

set -e

# Default configuration
OUTPUT_DIR="data/evaluation_llm_individual"
RUBRIC="both"
FILTER_METHOD=""
FILTER_PROJECT=""
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
        --method)
            FILTER_METHOD="$2"
            shift 2
            ;;
        --project)
            FILTER_PROJECT="$2"
            shift 2
            ;;
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --help)
            head -n 35 "$0" | grep "^#" | sed 's/^# \?//'
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
echo "D4D LLM EVALUATION - Individual Files"
echo "═══════════════════════════════════════════════════════════"
echo ""
echo "Configuration:"
echo "  Output directory: $OUTPUT_DIR"
echo "  Rubric: $RUBRIC"
echo "  Model: claude-sonnet-4-5-20250929"
echo "  Temperature: 0.0 (fully deterministic)"
echo "  Dry run: $DRY_RUN"
if [ -n "$FILTER_METHOD" ]; then
    echo "  Filter method: $FILTER_METHOD"
fi
if [ -n "$FILTER_PROJECT" ]; then
    echo "  Filter project: $FILTER_PROJECT"
fi
echo ""

# Create output directory
mkdir -p "$OUTPUT_DIR"

# Define methods and projects
METHODS=("gpt5" "claudecode_agent" "claudecode_assistant")
PROJECTS=("AI_READI" "CHORUS" "CM4AI" "VOICE")

# Find all individual D4D files
ALL_FILES=()
for METHOD in "${METHODS[@]}"; do
    # Skip if filtering by method
    if [ -n "$FILTER_METHOD" ] && [ "$METHOD" != "$FILTER_METHOD" ]; then
        continue
    fi

    for PROJECT in "${PROJECTS[@]}"; do
        # Skip if filtering by project
        if [ -n "$FILTER_PROJECT" ] && [ "$PROJECT" != "$FILTER_PROJECT" ]; then
            continue
        fi

        DIR="data/d4d_individual/${METHOD}/${PROJECT}"
        if [ -d "$DIR" ]; then
            while IFS= read -r -d '' file; do
                ALL_FILES+=("$file|$PROJECT|$METHOD")
            done < <(find "$DIR" -name "*_d4d.yaml" -print0)
        fi
    done
done

TOTAL_FILES=${#ALL_FILES[@]}

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
echo "  Time: ~${ESTIMATED_MINUTES} minutes (~$((ESTIMATED_MINUTES / 60))h ${((ESTIMATED_MINUTES % 60))}m)"
echo "  Cost: ~\$${ESTIMATED_COST} (at \$0.20/evaluation avg)"
echo ""

if [ "$TOTAL_FILES" -eq 0 ]; then
    echo "❌ No files found matching criteria"
    exit 1
fi

if [ "$DRY_RUN" = true ]; then
    echo "═══════════════════════════════════════════════════════════"
    echo "DRY RUN - Files that would be evaluated:"
    echo "═══════════════════════════════════════════════════════════"
    echo ""

    for entry in "${ALL_FILES[@]}"; do
        IFS='|' read -r file project method <<< "$entry"
        echo "✓ $project / $method"
        echo "  $file"
    done

    echo ""
    echo "To run actual evaluation, remove --dry-run flag"
    exit 0
fi

# Confirm before proceeding
echo "═══════════════════════════════════════════════════════════"
echo "⚠️  WARNING: This will evaluate $TOTAL_FILES files"
echo "   Estimated time: ~${ESTIMATED_MINUTES} minutes"
echo "   Estimated cost: ~\$${ESTIMATED_COST}"
echo ""
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
for entry in "${ALL_FILES[@]}"; do
    IFS='|' read -r file project method <<< "$entry"

    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "📊 Evaluating [$((EVALUATED + 1))/$TOTAL_FILES]: $project / $method"
    echo "   File: $file"
    echo "   Rubric: $RUBRIC"
    echo ""

    EVALUATED=$((EVALUATED + 1))

    # Run evaluation
    if poetry run python src/evaluation/evaluate_d4d_llm.py \
        --file "$file" \
        --project "$project" \
        --method "$method" \
        --rubric "$RUBRIC" \
        --output-dir "$OUTPUT_DIR"; then
        echo "✅ Success"
        SUCCESS=$((SUCCESS + 1))
    else
        echo "❌ Failed"
        FAILED=$((FAILED + 1))
    fi
    echo ""
done

# Calculate elapsed time
END_TIME=$(date +%s)
ELAPSED_SECONDS=$((END_TIME - START_TIME))
ELAPSED_HOURS=$((ELAPSED_SECONDS / 3600))
ELAPSED_MINUTES=$(((ELAPSED_SECONDS % 3600) / 60))
ELAPSED_SECONDS_REMAINDER=$((ELAPSED_SECONDS % 60))

echo "═══════════════════════════════════════════════════════════"
echo "EVALUATION COMPLETE"
echo "═══════════════════════════════════════════════════════════"
echo ""
echo "Summary:"
echo "  Files evaluated: $EVALUATED"
echo "  Successful: $SUCCESS"
echo "  Failed: $FAILED"
echo "  Elapsed time: ${ELAPSED_HOURS}h ${ELAPSED_MINUTES}m ${ELAPSED_SECONDS_REMAINDER}s"
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

if [ $FAILED -gt 0 ]; then
    exit 1
fi
