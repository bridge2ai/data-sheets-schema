# Rubric10 Fix Script Test Results

## Test Date: 2025-12-25

## Summary

Tested `scripts/fix_evaluation_scores.py` (updated to support rubric10 format) against 16 rubric10 evaluation files in `data/evaluation_llm/rubric10_semantic/concatenated/`.

**Results:**
- ✅ Successfully processed: 2/16 files (12.5%)
- ❌ Structural issues preventing fix: 14/16 files (87.5%)
- 🔥 Script crashed on: 1 file (CHORUS_claudecode_agent)

## Detailed Findings

### Files Successfully Processed (2/16)

Only files with correct `element_scores` list structure could be processed:

| File | Calculated Score | Status |
|------|------------------|--------|
| AI_READI_claudecode_agent | 32.0/50.0 (64%) | ✅ FIXED |
| VOICE_claudecode_agent | 47.0/50.0 (94%) | ✅ FIXED |

### Files with Structural Issues (14/16)

These files have incompatible structures and returned 0/0 or crashed:

#### Wrong Field Names (6 files)

**CM4AI_claudecode_agent** - Uses `element_evaluations` instead of `element_scores`
```json
{
  "overall_scores": {...},
  "element_evaluations": {...}  // Should be "element_scores": [...]
}
```

**AI_READI_gpt5** - No `element_scores` field at all
```json
{
  "scoring_summary": {...},
  "detailed_scores": {...}  // Completely different structure
}
```

Similar issues in:
- AI_READI_claudecode_assistant
- AI_READI_claudecode
- CM4AI_gpt5
- CM4AI_claudecode_assistant

#### Wrong Data Types (1 file)

**CHORUS_claudecode_agent** - `element_scores` is dict instead of list
```json
{
  "element_scores": {  // Should be array: [...]
    // ...
  }
}
```
**Error**: Script crashed with `AttributeError: 'str' object has no attribute 'get'`

#### Other Structural Variations (7 files)

Files that returned 0/0 due to missing or incompatible structures:
- CHORUS_claudecode_assistant
- CHORUS_claudecode
- CHORUS_gpt5
- CM4AI_claudecode
- VOICE_claudecode_assistant
- VOICE_claudecode
- VOICE_gpt5

## Field Name Variations Observed

Across 16 files, we found these different field names for the same concept:

### Overall Score Field
- `overall_score` (dict) - AI_READI_claudecode_agent
- `overall_scores` (dict) - CM4AI_claudecode_agent
- `overall_summary` (?) - CHORUS files
- `overall_assessment` (string) - VOICE_claudecode_agent
- `scoring_summary` (?) - AI_READI_gpt5
- **EXPECTED**: `summary_scores` (dict with total_score, total_max_score, overall_percentage)

### Element Scores Field
- `element_scores` (list) ✅ - 2 files (correct)
- `element_scores` (dict) ❌ - 1 file (CHORUS)
- `element_evaluations` ❌ - 1 file (CM4AI)
- `detailed_scores` ❌ - 1 file (AI_READI_gpt5)
- Missing entirely ❌ - 11 files

## Successful Structure Example

Only these 2 files had the correct structure:

```json
{
  "element_scores": [  // Must be array
    {
      "id": 1,
      "name": "Element Name",
      "sub_elements": [  // Must be array
        {
          "name": "Sub-element Name",
          "score": 1,  // Binary: 0 or 1
          "evidence": "...",
          "quality_note": "..."
        }
        // ... 4 more sub-elements
      ],
      "element_score": 5,
      "element_max": 5
    }
    // ... 9 more elements
  ]
}
```

## Conclusion

**The fix script CANNOT salvage these files.**

### Why?

1. **87.5% have incompatible structures** - Different field names, wrong data types
2. **Only 2 files can be processed** - AI_READI and VOICE claudecode_agent
3. **No consistent pattern** - Each generation method produces different structure
4. **Script would need 14 different structure handlers** - Not maintainable

### Recommendation

**Complete regeneration required** using the new schema-compliant prompt:
- Prompt: `RUBRIC10_EVALUATION_PROMPT_FINAL.md`
- Schema: `src/download/prompts/rubric10_semantic_schema.json`
- Post-processing: `scripts/fix_evaluation_scores.py` (for math errors only)
- Validation: `scripts/validate_evaluation_schema.py`

### What About the 2 Working Files?

Even the "working" files (AI_READI and VOICE claudecode_agent) have issues:
- Missing required schema fields (rubric, version, project, method, timestamp, model)
- Use `overall_score` or `overall_assessment` instead of `summary_scores`
- Cannot be rendered by HTML generator without fixing field names

**They should also be regenerated for consistency.**

## Comparison to Rubric20

Rubric20 situation was **much better**:
- All 4 files had identical structure
- Only issue: LLM math errors (summing scores incorrectly)
- Fix script corrected all 4 files successfully
- HTML generation worked perfectly after fix

Rubric10 situation is **much worse**:
- 16 different structures across 16 files
- Fundamental schema inconsistencies
- Fix script can only process 2 files
- HTML generation impossible without schema compliance

## Next Steps

1. ✅ Document findings (this report)
2. ⏭️ Proceed with regeneration using new prompt
3. ⏭️ Start with VOICE project (test case)
4. ⏭️ Validate against schema before HTML generation
5. ⏭️ Generate HTML from schema-compliant evaluations

---

**Testing Command Used:**
```bash
poetry run python scripts/fix_evaluation_scores.py \
  --input-dir data/evaluation_llm/rubric10_semantic/concatenated \
  --dry-run
```

**Script Version**: Updated 2025-12-25 to support both rubric10 and rubric20 formats
