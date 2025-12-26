# Updated Rubric10-Semantic Evaluation Prompt

## Overview

Using the d4d-rubric10-semantic agent, evaluate the 4 claude code_agent concatenated D4D files with **strict schema compliance** to ensure consistent JSON structure and accurate scoring.

## Critical Requirements

⚠️ **IMPORTANT**: All evaluations MUST conform to the JSON schema specification:
- **Schema file**: `src/download/prompts/rubric10_semantic_schema.json`
- **Validation**: All outputs will be validated against this schema
- **Post-processing**: Score corrections applied via `fix_evaluation_scores.py`

## Input Files

Concatenated D4D files (claudecode_agent method only):
- `data/d4d_concatenated/claudecode_agent/AI_READI_d4d.yaml`
- `data/d4d_concatenated/claudecode_agent/CHORUS_d4d.yaml`
- `data/d4d_concatenated/claudecode_agent/CM4AI_d4d.yaml`
- `data/d4d_concatenated/claudecode_agent/VOICE_d4d.yaml`

## Required JSON Schema Fields

Every evaluation JSON MUST include these top-level fields:

```json
{
  "rubric": "rubric10-semantic",
  "version": "1.0",
  "d4d_file": "data/d4d_concatenated/claudecode_agent/{PROJECT}_d4d.yaml",
  "project": "{PROJECT}",  // AI_READI, CHORUS, CM4AI, or VOICE
  "method": "claudecode_agent",
  "evaluation_timestamp": "2025-12-23T...",  // ISO 8601 format
  "model": {
    "name": "claude-sonnet-4-5-20250929",
    "temperature": 0.0,
    "evaluation_type": "semantic_llm_judge"
  },
  "summary_scores": {
    "total_score": 0,  // Will be recalculated by fix script
    "total_max_score": 50,
    "overall_percentage": 0.0,  // Will be recalculated
    "grade": "A+"  // Optional
  },
  "element_scores": [...],  // 10 elements (see below)
  "semantic_analysis": {...},  // See below
  "recommendations": [...]  // Array of strings
}
```

## Element Scores Structure

**Exactly 10 elements**, each with **exactly 5 sub-elements** (binary 0/1 scoring):

```json
"element_scores": [
  {
    "id": 1,
    "name": "Dataset Discovery and Identification",
    "description": "Can a user or system discover and uniquely identify this dataset?",
    "sub_elements": [
      {
        "name": "Persistent Identifier (DOI, RRID, or URI)",
        "score": 1,  // MUST be 0 or 1 only
        "evidence": "doi: https://doi.org/...",
        "quality_note": "DOI present and properly formatted",
        "semantic_validation": "DOI format validated"  // Optional
      },
      // ... 4 more sub-elements
    ],
    "element_score": 5,  // Sum of sub-element scores (0-5)
    "element_max": 5  // Always 5
  },
  // ... 9 more elements (total 10)
]
```

## Semantic Analysis Structure

```json
"semantic_analysis": {
  "issues_detected": [
    {
      "type": "format_error",  // or inconsistency, missing_data, etc.
      "severity": "warning",  // critical, warning, info
      "description": "DOI format does not match standard pattern",
      "fields_involved": ["doi"],
      "recommendation": "Verify DOI resolves correctly"
    }
  ],
  "consistency_checks": {
    "passed": ["dates_chronological", "creator_affiliations_match"],
    "failed": ["funding_grant_mismatch"],
    "warnings": ["missing_orcid_for_creators"]
  },
  "correctness_validations": {
    "doi_format": "valid",  // valid, invalid, or missing
    "grant_format": "valid",
    "rrid_format": "missing",
    "url_validity": "all_valid"  // all_valid, some_invalid, or not_checked
  },
  "semantic_insights": "Comprehensive metadata with validated identifiers..."
}
```

## Evaluation Workflow

### For Each D4D File:

1. **Read the D4D YAML file**
   ```python
   with open(f"data/d4d_concatenated/claudecode_agent/{project}_d4d.yaml") as f:
       d4d_data = yaml.safe_load(f)
   ```

2. **Apply rubric10-semantic assessment**
   - **Standard**: 10 elements, 50 sub-elements (binary 0/1 scoring, max 50 points)
   - **Semantic enhancements**:
     - DOI/grant/RRID format validation
     - URL validity checking
     - Consistency checking (dates, affiliations, funding)
     - Content accuracy assessment

3. **Generate JSON evaluation conforming to schema**
   - **MUST** include ALL required fields
   - Use `summary_scores` (not `overall_score` or `overall_scores`)
   - Binary scoring only (0 or 1) for sub-elements
   - Include semantic_analysis with format validations

4. **Save to**: `data/evaluation_llm/rubric10_semantic/concatenated/{PROJECT}_claudecode_agent_evaluation.json`

### After Generating All 4 Files:

5. **Run score fixing script** (REQUIRED):
   ```bash
   poetry run python scripts/fix_evaluation_scores.py \
     --input-dir data/evaluation_llm/rubric10_semantic/concatenated
   ```

   This script:
   - Recalculates `summary_scores.total_score` by summing all sub-element scores
   - Fixes `summary_scores.overall_percentage`
   - Corrects any LLM calculation errors
   - Adds any missing required fields

6. **Validate against schema**:
   ```bash
   poetry run python scripts/validate_evaluation_schema.py \
     data/evaluation_llm/rubric10_semantic/concatenated/*_claudecode_agent_evaluation.json \
     --schema src/download/prompts/rubric10_semantic_schema.json
   ```

   All 4 files MUST validate successfully.

7. **Generate HTML for each evaluation**:
   ```bash
   poetry run python scripts/render_evaluation_html_rubric10_semantic.py \
     data/evaluation_llm/rubric10_semantic/concatenated/ \
     data/d4d_html/concatenated/claudecode_agent/
   ```

   Output files:
   - `data/d4d_html/concatenated/claudecode_agent/AI_READI_evaluation.html`
   - `data/d4d_html/concatenated/claudecode_agent/CHORUS_evaluation.html`
   - `data/d4d_html/concatenated/claudecode_agent/CM4AI_evaluation.html`
   - `data/d4d_html/concatenated/claudecode_agent/VOICE_evaluation.html`

8. **Generate summary report**:
   Create `data/evaluation_llm/rubric10_semantic/concatenated/summary_report.md` with:
   - Comparison table showing all 4 projects
   - Element-level performance breakdown
   - Semantic analysis highlights (issues by type)
   - Common strengths and weaknesses
   - Key insights and recommendations

## Settings

- **Temperature**: 0.0 (fully deterministic)
- **Model**: claude-sonnet-4-5-20250929
- **Agent**: d4d-rubric10-semantic
- **Rubric**: `data/rubric/rubric10.txt` + semantic enhancements
- **Schema**: `src/download/prompts/rubric10_semantic_schema.json`

## Expected Output Structure

```
data/evaluation_llm/rubric10_semantic/concatenated/
├── AI_READI_claudecode_agent_evaluation.json  ✅ Schema-compliant
├── CHORUS_claudecode_agent_evaluation.json    ✅ Schema-compliant
├── CM4AI_claudecode_agent_evaluation.json     ✅ Schema-compliant
├── VOICE_claudecode_agent_evaluation.json     ✅ Schema-compliant
└── summary_report.md

data/d4d_html/concatenated/claudecode_agent/
├── AI_READI_evaluation.html     (updated with corrected scores)
├── CHORUS_evaluation.html       (updated with corrected scores)
├── CM4AI_evaluation.html        (updated with corrected scores)
└── VOICE_evaluation.html        (updated with corrected scores)
```

## Quality Checklist

Before considering evaluation complete:

- [ ] All 4 JSON files conform to `rubric10_semantic_schema.json`
- [ ] `fix_evaluation_scores.py` has been run successfully
- [ ] All 4 files pass schema validation
- [ ] HTML files generated without errors
- [ ] HTML displays correct scores (matching summary_scores.total_score)
- [ ] summary_report.md created with all sections
- [ ] No "null" values in required fields
- [ ] All sub-element scores are 0 or 1 (binary)
- [ ] element_score equals sum of sub-element scores
- [ ] summary_scores.total_score equals sum of all element scores

## Key Differences from Previous Prompt

### ❌ OLD (Inconsistent):
- No schema specification → 4 different JSON structures
- `overall_scores` vs `overall_score` vs `overall_summary` confusion
- No post-processing step → math errors in scores
- No validation → missing fields

### ✅ NEW (Consistent):
- **Strict schema**: `rubric10_semantic_schema.json`
- **Consistent structure**: All use `summary_scores`
- **Post-processing**: `fix_evaluation_scores.py` corrects math
- **Validation**: Schema checking before HTML generation
- **Required fields**: All metadata must be present

## References

- **Schema**: `src/download/prompts/rubric10_semantic_schema.json`
- **Output Example**: `src/download/prompts/rubric10_output_format.json`
- **Rubric**: `data/rubric/rubric10.txt`
- **HTML Renderer**: `scripts/render_evaluation_html_rubric10_semantic.py`
- **Fix Script**: `scripts/fix_evaluation_scores.py`
- **Issue Report**: `RUBRIC10_ISSUES_REPORT.md` (explains why regeneration needed)

---

**Process all 4 files systematically and generate structured, schema-compliant evaluation outputs with semantic analysis for the latest improved D4D datasheets.**
