# Complete Rubric10 Evaluation Guide

## Overview

This guide shows how to evaluate ALL D4D files (individual and concatenated) across all 4 projects and all generation methods using the rubric10 LLM-as-judge approach within Claude Code.

**Total files to evaluate:** 127 D4D files
- **Individual files:** 111 (AI_READI, CHORUS, CM4AI, VOICE across gpt5, claudecode_agent, claudecode_assistant)
- **Concatenated files:** 16 (AI_READI, CHORUS, CM4AI, VOICE across curated, gpt5, claudecode, claudecode_agent, claudecode_assistant)

## Prerequisites

✅ D4D files generated (individual and concatenated)
✅ Rubric10 agent available (`.claude/agents/d4d-rubric10.md`)
✅ Claude Code session active

## Step 1: Generate File Inventory and Evaluation Plan

```bash
# Run the inventory script
python3 scripts/evaluate_all_d4ds_rubric10.py
```

**Output:**
- `data/evaluation_llm/rubric10/file_inventory.json` - Complete list of all files to evaluate
- `data/evaluation_llm/rubric10/evaluation_plan.md` - Detailed evaluation plan

**What this does:**
- Scans all D4D directories
- Identifies 127 files to evaluate
- Creates structured evaluation plan

## Step 2: Review the Files to Evaluate

```bash
# View the inventory
cat data/evaluation_llm/rubric10/file_inventory.json | jq '.metadata'

# View the evaluation plan
cat data/evaluation_llm/rubric10/evaluation_plan.md | head -50
```

**File breakdown:**
- AI_READI: ~42 files (14 + 14 + 14 individual + 4 concatenated)
- CHORUS: ~30 files (12 + 6 + 6 individual + 4 concatenated)
- CM4AI: ~30 files (12 + 6 + 6 individual + 4 concatenated)
- VOICE: ~25 files (9 + 9 + 9 individual + 4 concatenated)

## Step 3: Use Claude Code Conversational Evaluation

### The Prompt

Copy and paste this prompt into Claude Code:

```
Using the d4d-rubric10 agent, evaluate all files listed in
data/evaluation_llm/rubric10/file_inventory.json and save results
according to the evaluation plan at data/evaluation_llm/rubric10/evaluation_plan.md

For each file:
1. Read the D4D YAML file
2. Apply rubric10 quality assessment (10 elements, 50 sub-elements)
3. Generate JSON evaluation with scores, evidence, recommendations
4. Save to data/evaluation_llm/rubric10/{type}/{project}_{method}_evaluation.json

Settings:
- Temperature: 0.0 (fully deterministic)
- Model: claude-sonnet-4-5-20250929
- Rubric: data/rubric/rubric10.txt

Process all 127 files systematically and report progress.
```

### What Happens

The d4d-rubric10 agent will:

1. **Load the file inventory** from JSON
2. **Iterate through all 127 files** systematically
3. **For each file:**
   - Read D4D YAML using Read tool
   - Apply rubric10 criteria (10 elements × 5 sub-elements = 50 points max)
   - Score each sub-element (0 or 1)
   - Provide evidence quotes from the D4D file
   - Generate strengths, weaknesses, recommendations
4. **Save JSON results** for each evaluation:
   - Individual: `data/evaluation_llm/rubric10/individual/{project}_{method}_{file}_evaluation.json`
   - Concatenated: `data/evaluation_llm/rubric10/concatenated/{project}_{method}_evaluation.json`
5. **Report progress** after each batch

### Expected Duration

- **Per file:** ~30-60 seconds
- **Total time:** ~1.5-2 hours for all 127 files
- **No API key required** - pure conversational evaluation within Claude Code

## Step 4: Monitor Progress

During evaluation, you'll see output like:

```
✅ Evaluating [1/127]: AI_READI / gpt5 / individual
   File: data/d4d_individual/gpt5/AI_READI/file1_d4d.yaml
   Score: 18/50 (36.0%)

✅ Evaluating [2/127]: AI_READI / gpt5 / individual
   File: data/d4d_individual/gpt5/AI_READI/file2_d4d.yaml
   Score: 22/50 (44.0%)

...

✅ Evaluating [127/127]: VOICE / claudecode_assistant / concatenated
   File: data/d4d_concatenated/claudecode_assistant/VOICE_d4d.yaml
   Score: 42/50 (84.0%)

✅ All 127 evaluations complete!
```

## Step 5: Generate Summary Tables and Reports

After all evaluations complete, run the summary script:

```bash
# Generate summary tables and reports
python3 scripts/summarize_rubric10_results.py
```

**Output files:**
1. **`data/evaluation_llm/rubric10/all_scores.csv`** - CSV with all scores
2. **`data/evaluation_llm/rubric10/summary_table.md`** - Markdown comparison table
3. **`data/evaluation_llm/rubric10/summary_report.md`** - Detailed analysis report

## Step 6: View Results

### View Summary Table

```bash
cat data/evaluation_llm/rubric10/summary_table.md
```

**Expected format:**

| Project | Method | Score | Percentage | Elements Passing | Top Element | Weakest Element |
|---------|--------|-------|------------|------------------|-------------|-----------------|
| AI_READI | curated | 42/50 | 84.0% | 8/10 | Discovery (5/5) | Provenance (2/5) |
| AI_READI | gpt5 | 18/50 | 36.0% | 3/10 | Access (4/5) | Integration (0/5) |
| AI_READI | claudecode_agent | 38/50 | 76.0% | 7/10 | Ethics (5/5) | Funding (2/5) |
| AI_READI | claudecode_assistant | 40/50 | 80.0% | 8/10 | Ethics (5/5) | Provenance (3/5) |
| ... | ... | ... | ... | ... | ... | ... |

### View Detailed Report

```bash
cat data/evaluation_llm/rubric10/summary_report.md
```

Shows:
- Overall statistics
- Method comparison
- Project comparison
- Top performers
- Common strengths/weaknesses

### Open CSV in Spreadsheet

```bash
# macOS
open data/evaluation_llm/rubric10/all_scores.csv

# Linux
xdg-open data/evaluation_llm/rubric10/all_scores.csv
```

## Expected Results Format

### Individual Evaluation JSON

Each evaluation produces a JSON file like:

```json
{
  "rubric": "rubric10",
  "version": "1.0",
  "d4d_file": "data/d4d_concatenated/claudecode/VOICE_d4d.yaml",
  "project": "VOICE",
  "method": "claudecode",
  "type": "concatenated",
  "evaluation_timestamp": "2025-12-06T10:30:00Z",
  "model": {
    "name": "claude-sonnet-4-5-20250929",
    "temperature": 0.0,
    "evaluation_type": "llm_as_judge"
  },
  "overall_score": {
    "total_points": 38.5,
    "max_points": 50,
    "percentage": 77.0
  },
  "elements": [
    {
      "id": 1,
      "name": "Dataset Discovery and Identification",
      "element_score": 5,
      "element_max": 5,
      "sub_elements": [
        {
          "name": "Persistent Identifier",
          "score": 1,
          "evidence": "doi: https://doi.org/10.13026/249v-w155",
          "quality_note": "DOI present and properly formatted"
        },
        ...
      ]
    },
    ...
  ],
  "assessment": {
    "strengths": [
      "Comprehensive ethical documentation",
      "Clear access mechanisms"
    ],
    "weaknesses": [
      "Missing funding details",
      "Limited version history"
    ],
    "recommendations": [
      "Add funding_and_acknowledgements section",
      "Include release notes"
    ]
  }
}
```

## Deterministic Evaluation Settings

✅ **Temperature:** 0.0 (fully deterministic)
✅ **Model:** claude-sonnet-4-5-20250929 (date-pinned)
✅ **Rubric:** Version-controlled in `data/rubric/rubric10.txt`
✅ **Prompt:** Version-controlled in `.claude/agents/d4d-rubric10.md`

**Reproducibility guarantee:** Same D4D file → Same quality score every time

## Comparison with Existing Evaluation

This LLM-based rubric10 evaluation complements the existing field-presence detection:

| Aspect | Presence Detection | LLM Rubric10 |
|--------|-------------------|--------------|
| **Method** | Python script | Conversational LLM-as-judge |
| **Speed** | ~1 second/file | ~30-60 seconds/file |
| **Cost** | Free | Free (within Claude Code) |
| **What it checks** | IF fields exist | HOW WELL fields are filled |
| **Insight** | "Field missing" | "Field present but generic/incomplete/excellent" |
| **Evidence** | None | Quotes, reasoning, context |
| **Use case** | Quick validation | Deep quality assessment |

## Troubleshooting

### Issue: Agent times out

**Solution:** Process files in batches:

```
Evaluate the first 30 files from data/evaluation_llm/rubric10/file_inventory.json
```

Then continue with next batches.

### Issue: Some files not found

**Solution:** Check file paths in inventory match actual file locations:

```bash
# Verify files exist
cat data/evaluation_llm/rubric10/file_inventory.json | jq -r '.concatenated_files[]' | while read file; do
  [ -f "$file" ] || echo "Missing: $file"
done
```

### Issue: Validation errors in D4D files

**Solution:** The rubric10 evaluation will note validation errors in the "weaknesses" section. These don't prevent evaluation - they inform the quality score.

## Next Steps After Evaluation

1. **Identify best methods** - Which generation method produces highest quality?
2. **Find gaps** - What metadata is commonly missing?
3. **Improve prompts** - Use weaknesses to enhance D4D generation prompts
4. **Compare with rubric20** - Run same evaluation with d4d-rubric20 agent
5. **Track improvements** - Re-evaluate after making enhancements

## Complete Workflow Summary

```bash
# Step 1: Generate inventory and plan
python3 scripts/evaluate_all_d4ds_rubric10.py

# Step 2: Review what will be evaluated
cat data/evaluation_llm/rubric10/evaluation_plan.md

# Step 3: Run conversational evaluation in Claude Code
# (Use the prompt provided above)

# Step 4: Generate summary tables
python3 scripts/summarize_rubric10_results.py

# Step 5: View results
cat data/evaluation_llm/rubric10/summary_table.md
cat data/evaluation_llm/rubric10/summary_report.md
open data/evaluation_llm/rubric10/all_scores.csv
```

## Files Created

After completing all steps:

```
data/evaluation_llm/rubric10/
├── file_inventory.json          # List of all files to evaluate
├── evaluation_plan.md           # Detailed evaluation plan
├── all_scores.csv               # CSV with all scores
├── summary_table.md             # Comparison table
├── summary_report.md            # Detailed report
├── individual/                  # Individual file evaluations
│   ├── AI_READI_gpt5_*.json
│   ├── AI_READI_claudecode_agent_*.json
│   ├── AI_READI_claudecode_assistant_*.json
│   ├── CHORUS_gpt5_*.json
│   ├── ... (111 files)
└── concatenated/                # Concatenated file evaluations
    ├── AI_READI_curated_evaluation.json
    ├── AI_READI_gpt5_evaluation.json
    ├── AI_READI_claudecode_evaluation.json
    ├── ... (16 files)
```

**Total:** 127 evaluation JSONs + 4 summary files

## Cost and Time Estimates

- **API costs:** $0 (conversational within Claude Code)
- **Time:** ~1.5-2 hours for 127 files
- **Reproducibility:** 100% (temperature 0.0, date-pinned model)
