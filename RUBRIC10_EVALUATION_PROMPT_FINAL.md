# Rubric10-Semantic Evaluation: Schema-Compliant Workflow

Using the d4d-rubric10-semantic agent, evaluate the 4 claudecode_agent concatenated D4D files with **strict schema compliance** to ensure consistent JSON structure and accurate scoring.

## ⚠️ Critical Requirements

**All evaluations MUST conform to the JSON schema:**
- **Schema**: `src/download/prompts/rubric10_semantic_schema.json`
- **Post-processing**: Score corrections via `scripts/fix_evaluation_scores.py` (REQUIRED)
- **Validation**: All outputs validated against schema before HTML generation

## Scope

**Concatenated D4D files (claudecode_agent method only):**
- `data/d4d_concatenated/claudecode_agent/AI_READI_d4d.yaml`
- `data/d4d_concatenated/claudecode_agent/CHORUS_d4d.yaml`
- `data/d4d_concatenated/claudecode_agent/CM4AI_d4d.yaml`
- `data/d4d_concatenated/claudecode_agent/VOICE_d4d.yaml`

## For Each File

### 1. Read the D4D YAML File
```python
import yaml
with open(f"data/d4d_concatenated/claudecode_agent/{project}_d4d.yaml") as f:
    d4d_data = yaml.safe_load(f)
```

### 2. Apply Rubric10-Semantic Quality Assessment

**Standard**: 10 elements, 50 sub-elements (binary 0/1 scoring, max 50 points)

**Semantic Enhancements**:
- Correctness validation (DOI/grant/RRID formats)
- Consistency checking (dates, affiliations, funding)
- Semantic understanding (content accuracy)
- URL validity checking

### 3. Generate Schema-Compliant JSON Evaluation

**REQUIRED Top-Level Fields:**
```json
{
  "rubric": "rubric10-semantic",
  "version": "1.0",
  "d4d_file": "data/d4d_concatenated/claudecode_agent/{PROJECT}_d4d.yaml",
  "project": "{PROJECT}",
  "method": "claudecode_agent",
  "evaluation_timestamp": "2025-12-23T21:45:00Z",
  "model": {
    "name": "claude-sonnet-4-5-20250929",
    "temperature": 0.0,
    "evaluation_type": "semantic_llm_judge"
  },
  "summary_scores": {
    "total_score": 0,
    "total_max_score": 50,
    "overall_percentage": 0.0,
    "grade": "A+"
  },
  "element_scores": [...],
  "semantic_analysis": {...},
  "recommendations": [...]
}
```

**Element Scores Structure** (10 elements, each with 5 sub-elements):
```json
"element_scores": [
  {
    "id": 1,
    "name": "Dataset Discovery and Identification",
    "description": "Can a user or system discover and uniquely identify this dataset?",
    "sub_elements": [
      {
        "name": "Persistent Identifier (DOI, RRID, or URI)",
        "score": 1,
        "evidence": "doi: https://doi.org/...",
        "quality_note": "DOI present and properly formatted",
        "semantic_validation": "DOI format validated"
      }
      // ... 4 more sub-elements
    ],
    "element_score": 5,
    "element_max": 5
  }
  // ... 9 more elements
]
```

**Semantic Analysis Structure:**
```json
"semantic_analysis": {
  "issues_detected": [
    {
      "type": "format_error",
      "severity": "warning",
      "description": "...",
      "fields_involved": ["doi"],
      "recommendation": "..."
    }
  ],
  "consistency_checks": {
    "passed": ["dates_chronological"],
    "failed": ["funding_grant_mismatch"],
    "warnings": ["missing_orcid"]
  },
  "correctness_validations": {
    "doi_format": "valid",
    "grant_format": "valid",
    "rrid_format": "missing",
    "url_validity": "all_valid"
  },
  "semantic_insights": "..."
}
```

### 4. Save Evaluation JSON
**Output**: `data/evaluation_llm/rubric10_semantic/concatenated/{PROJECT}_claudecode_agent_evaluation.json`

## After Evaluating All 4 Files

### 5. Run Score Fixing Script (REQUIRED)

```bash
poetry run python scripts/fix_evaluation_scores.py \
  --input-dir data/evaluation_llm/rubric10_semantic/concatenated
```

**What This Does:**
- Recalculates `summary_scores.total_score` by summing all sub-element scores
- Fixes `summary_scores.overall_percentage`
- Corrects any LLM calculation errors
- Adds any missing required fields

### 6. Validate Against Schema

```bash
poetry run python scripts/validate_evaluation_schema.py \
  data/evaluation_llm/rubric10_semantic/concatenated/*_claudecode_agent_evaluation.json \
  --schema src/download/prompts/rubric10_semantic_schema.json
```

**All 4 files MUST validate successfully before proceeding.**

### 7. Generate HTML for Each Evaluation

```bash
poetry run python scripts/render_evaluation_html_rubric10_semantic.py \
  data/evaluation_llm/rubric10_semantic/concatenated/ \
  data/d4d_html/concatenated/claudecode_agent/
```

**Output Files:**
- `data/d4d_html/concatenated/claudecode_agent/AI_READI_evaluation.html`
- `data/d4d_html/concatenated/claudecode_agent/CHORUS_evaluation.html`
- `data/d4d_html/concatenated/claudecode_agent/CM4AI_evaluation.html`
- `data/d4d_html/concatenated/claudecode_agent/VOICE_evaluation.html`

### 8. Generate Summary Report

**Create**: `data/evaluation_llm/rubric10_semantic/concatenated/summary_report.md`

**Contents:**
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
├── AI_READI_claudecode_agent_evaluation.json  ✅ Schema-compliant, scores corrected
├── CHORUS_claudecode_agent_evaluation.json    ✅ Schema-compliant, scores corrected
├── CM4AI_claudecode_agent_evaluation.json     ✅ Schema-compliant, scores corrected
├── VOICE_claudecode_agent_evaluation.json     ✅ Schema-compliant, scores corrected
└── summary_report.md

data/d4d_html/concatenated/claudecode_agent/
├── AI_READI_evaluation.html     (updated with corrected scores)
├── CHORUS_evaluation.html       (updated with corrected scores)
├── CM4AI_evaluation.html        (updated with corrected scores)
└── VOICE_evaluation.html        (updated with corrected scores)
```

## Quality Checklist

Before considering evaluation complete, verify:

- [ ] All 4 JSON files conform to `rubric10_semantic_schema.json`
- [ ] `fix_evaluation_scores.py` completed successfully
- [ ] All 4 files pass schema validation
- [ ] HTML files generated without errors
- [ ] HTML displays correct scores (matching `summary_scores.total_score`)
- [ ] `summary_report.md` created with all sections
- [ ] No "null" values in required fields
- [ ] All sub-element scores are 0 or 1 (binary)
- [ ] `element_score` equals sum of sub-element scores
- [ ] `summary_scores.total_score` equals sum of all element scores

## Key Field Names (CRITICAL)

**Use EXACTLY these field names:**

✅ **CORRECT**: `summary_scores` (with `total_score`, `total_max_score`, `overall_percentage`)
❌ **WRONG**: `overall_scores`, `overall_score`, `overall_summary`, `overall_assessment`

✅ **CORRECT**: `element_scores` (array of 10 elements)
❌ **WRONG**: `elements`, `element_evaluations`

✅ **CORRECT**: `sub_elements` (array of 5 per element)
❌ **WRONG**: `sub_element_scores`, `subelements`

**Note**: Using incorrect field names will cause HTML generation to fail.

## References

- **Schema**: `src/download/prompts/rubric10_semantic_schema.json`
- **Output Example**: `src/download/prompts/rubric10_output_format.json`
- **Rubric**: `data/rubric/rubric10.txt`
- **HTML Renderer**: `scripts/render_evaluation_html_rubric10_semantic.py`
- **Fix Script**: `scripts/fix_evaluation_scores.py`
- **Issue Report**: `RUBRIC10_ISSUES_REPORT.md` (why regeneration needed)
- **Full Documentation**: `RUBRIC10_UPDATED_PROMPT.md`

---

Process all 4 files systematically and generate structured, schema-compliant evaluation outputs with semantic analysis for the latest improved D4D datasheets.
