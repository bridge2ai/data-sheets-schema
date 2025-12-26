# Rubric10-Semantic Evaluation Issues Report

## Summary

The rubric10-semantic evaluation JSON files have **severe structural inconsistencies** across different projects, making them incompatible with the HTML renderer and preventing accurate scoring validation.

## Issues Found

### 1. Inconsistent JSON Structure Across Projects

Each project uses a **different JSON schema**:

#### CM4AI (data/evaluation_llm/rubric10_semantic/concatenated/CM4AI_claudecode_agent_evaluation.json)
```json
{
  "evaluation_metadata": {...},
  "overall_scores": {
    "total_score": 42,
    "max_possible_score": 50,
    "percentage": 84.0,
    "element_scores": {...}
  },
  "element_evaluations": [...]
}
```
- ✅ Math is correct (42 = sum of element scores)
- ❌ Doesn't match HTML renderer expectations
- ❌ Missing required fields

#### AI_READI (data/evaluation_llm/rubric10_semantic/concatenated/AI_READI_claudecode_agent_evaluation.json)
```json
{
  "evaluation_metadata": {...},
  "overall_score": {
    "total_points": 37,
    "max_points": 50,
    "percentage": 74.0,
    "grade": "C+"
  },
  "element_scores": [...],
  "semantic_analysis": {...}
}
```
- ❓ Math not verified (different field names)
- ❌ Uses `total_points` instead of `total_score`
- ❌ Missing `summary_scores` field

#### CHORUS (data/evaluation_llm/rubric10_semantic/concatenated/CHORUS_claudecode_agent_evaluation.json)
```json
{
  "evaluation_metadata": {...},
  "element_scores": [...],
  "overall_summary": {...},
  "semantic_analysis": {...}
}
```
- ❌ **NO overall score field at all**
- ❌ Uses `overall_summary` instead
- ❌ Completely incompatible structure

#### VOICE (data/evaluation_llm/rubric10_semantic/concatenated/VOICE_claudecode_agent_evaluation.json)
```json
{
  "metadata": {...},
  "element_scores": [...],
  "overall_assessment": {...},
  "summary": {...},
  "strengths": [...],
  "weaknesses": [...],
  "recommendations": [...]
}
```
- ❌ **NO overall score field**
- ❌ Uses `metadata` instead of `evaluation_metadata`
- ❌ Uses `overall_assessment` instead of `overall_score`
- ❌ Most incompatible structure

### 2. HTML Renderer Expectations

The existing `scripts/render_evaluation_html_rubric10_semantic.py` expects:

```python
metadata = eval_data.get("evaluation_metadata", {})
element_scores = eval_data.get("element_scores", [])
summary = eval_data.get("summary_scores", {})  # ⚠️ NONE of the files have this!
semantic = eval_data.get("semantic_analysis", {})
recommendations = eval_data.get("recommendations", {})

total_score = summary.get("total_score", 0)
max_score = summary.get("total_max_score", 50)
percentage = summary.get("overall_percentage", 0)
```

**Result**: The HTML renderer cannot read scores from ANY of the current evaluation files!

### 3. Missing Required Fields

Comparing to rubric20-semantic schema (which works correctly), rubric10 evaluations are missing:

- `rubric`: "rubric10-semantic" (identification)
- `version`: "1.0" (schema version)
- `project`: "{PROJECT}" (required for validation)
- `method`: "claudecode_agent" (generation method)
- `d4d_file`: Full path to source D4D file
- `evaluation_timestamp`: ISO 8601 timestamp
- `model`: Object with name, temperature, evaluation_type

### 4. Score Calculation Verification

Only CM4AI could be verified (correct math). The other three files cannot be checked because they lack consistent field names or overall score fields entirely.

## Root Cause

The rubric10 evaluations were generated **without a JSON schema specification**, allowing the LLM to create arbitrary structures. Unlike rubric20-semantic which has `src/download/prompts/rubric20_semantic_schema.json`, there is no corresponding schema for rubric10.

## Impact

1. ❌ **Cannot validate scores** - Each file has different field names
2. ❌ **HTML rendering fails** - Renderer expects `summary_scores` which no file has
3. ❌ **Cannot compare across projects** - Inconsistent structures
4. ❌ **No post-processing possible** - `fix_evaluation_scores.py` cannot handle multiple schemas
5. ❌ **Manual validation required** - No automated schema checking

## Recommendation

**Complete regeneration required** with:

1. **Create `src/download/prompts/rubric10_semantic_schema.json`**
   - Based on rubric20 schema structure
   - Align with HTML renderer expectations
   - Include all required metadata fields

2. **Regenerate all 4 claudecode_agent evaluations**
   - Use strict schema validation
   - Ensure consistent structure
   - Verify math accuracy

3. **Update `scripts/fix_evaluation_scores.py`**
   - Add rubric10 support
   - Handle both rubric10 and rubric20 formats

4. **Validate HTML renderer**
   - Ensure it matches new schema
   - Test with regenerated files

5. **Update prompt**
   - Include schema reference
   - Specify required fields
   - Add post-processing step

## Comparison to Rubric20

Rubric20-semantic evaluations had:
- ✅ Consistent structure across all files
- ❌ Math errors (total_score 3-7 points too low)
- ❌ Missing optional fields (easily fixable)
- ✅ Compatible with HTML renderer
- ✅ Fixed with `fix_evaluation_scores.py`

Rubric10-semantic evaluations have:
- ❌ Completely inconsistent structures
- ❓ Math cannot be verified
- ❌ Incompatible with HTML renderer
- ❌ Cannot be fixed without regeneration

**Rubric10 is in much worse shape than rubric20 was.**

---

**Generated**: 2025-12-23
**Status**: Requires immediate attention before HTML generation
