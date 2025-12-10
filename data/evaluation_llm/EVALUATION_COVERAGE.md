# D4D Evaluation Coverage Report

**Generated:** 2025-12-07
**Purpose:** Document which D4D files have been evaluated and which are pending

---

## Evaluation Status Summary

| Rubric | Concatenated | Individual | Total | Status |
|--------|--------------|------------|-------|--------|
| **Rubric10** | 16/20 possible (80%) | 111/111 (100%) | 127 | ⚠️ Missing curated |
| **Rubric20** | 16/20 possible (80%) | 111/111 (100%) | 127 | ⚠️ Missing curated |

---

## Concatenated Files Evaluation Status

### ✅ Evaluated (16 files)

| Project | gpt5 | claudecode | claudecode_agent | claudecode_assistant |
|---------|------|------------|------------------|----------------------|
| **AI_READI** | ✅ | ✅ | ✅ | ✅ |
| **CHORUS** | ✅ | ✅ | ✅ | ✅ |
| **CM4AI** | ✅ | ✅ | ✅ | ✅ |
| **VOICE** | ✅ | ✅ | ✅ | ✅ |

### ❌ Not Yet Evaluated (3-4 files)

| Project | curated | File Status |
|---------|---------|-------------|
| **AI_READI** | ❌ | File exists: `data/d4d_concatenated/curated/AI_READI_curated.yaml` |
| **CHORUS** | ❌ | File missing (may not exist) |
| **CM4AI** | ❌ | File exists: `data/d4d_concatenated/curated/CM4AI_curated.yaml` |
| **VOICE** | ❌ | File exists: `data/d4d_concatenated/curated/VOICE_curated.yaml` |

**Impact:** Curated files represent manually created comprehensive datasheets and would provide important baseline for comparison with automated methods.

---

## Individual Files Evaluation Status

### ✅ Fully Evaluated (111 files)

| Project | gpt5 | claudecode | claudecode_agent | claudecode_assistant |
|---------|------|------------|------------------|----------------------|
| **AI_READI** | 8 files | N/A* | 14 files | 14 files |
| **CHORUS** | 2 files | N/A* | 12 files | 12 files |
| **CM4AI** | 4 files | N/A* | 12 files | 12 files |
| **VOICE** | 3 files | N/A* | 9 files | 9 files |
| **Total** | 17 | 0 | 47 | 47 |

*N/A: "claudecode" method is concatenated-only (requires multi-source synthesis)

### Method Breakdown

| Method | Files Evaluated | Files Available | Coverage |
|--------|----------------|-----------------|----------|
| **gpt5** | 17 | 17 | 100% |
| **claudecode** | 0 (N/A) | 0 | N/A (concatenated-only) |
| **claudecode_agent** | 47 | 47 | 100% |
| **claudecode_assistant** | 47 | 47 | 100% |

---

## File Locations

### Evaluated Results

#### Rubric10
- **Concatenated:** `data/evaluation_llm/rubric10/concatenated/` (16 JSON files)
- **Individual:** `data/evaluation_llm/rubric10/individual/` (111 JSON files)
- **Summaries:**
  - `data/evaluation_llm/rubric10/all_scores.csv`
  - `data/evaluation_llm/rubric10/summary_table.md`
  - `data/evaluation_llm/rubric10/summary_report.md`
  - `data/evaluation_llm/rubric10/structured_summary.yaml`

#### Rubric20
- **Concatenated:** `data/evaluation_llm/rubric20/concatenated/` (16 JSON files)
- **Individual:** `data/evaluation_llm/rubric20/individual/` (111 JSON files)
- **Summaries:**
  - `data/evaluation_llm/rubric20/all_scores.csv`
  - `data/evaluation_llm/rubric20/summary_table.md`
  - `data/evaluation_llm/rubric20/summary_report.md`
  - `data/evaluation_llm/rubric20/structured_summary.yaml`

### Unevaluated D4D Files

#### Curated Concatenated Files (Not Evaluated)
- `data/d4d_concatenated/curated/AI_READI_curated.yaml`
- `data/d4d_concatenated/curated/CM4AI_curated.yaml`
- `data/d4d_concatenated/curated/VOICE_curated.yaml`
- Note: CHORUS curated file may not exist

---

## Recommendations for Complete Evaluation

### Priority 1: Evaluate Curated Files
```bash
# Evaluate AI_READI curated
python3 scripts/batch_evaluate_rubric10_hybrid.py \
  --file data/d4d_concatenated/curated/AI_READI_curated.yaml \
  --project AI_READI --method curated --type concatenated

python3 scripts/batch_evaluate_rubric20_hybrid.py \
  --file data/d4d_concatenated/curated/AI_READI_curated.yaml \
  --project AI_READI --method curated --type concatenated

# Repeat for CM4AI and VOICE
```

**Expected Impact:**
- Provide baseline comparison for manually curated vs automated methods
- Likely to achieve highest scores (expected 80-95%)
- Validate rubric effectiveness (if curated scores low, rubric may need adjustment)

### Priority 2: Create CHORUS Curated File (if desired)
```bash
# Check if CHORUS curated exists
ls data/d4d_concatenated/curated/CHORUS*.yaml
```

If CHORUS curated doesn't exist, it would need to be created manually before evaluation.

---

## Evaluation Completeness

| Component | Status | Completeness |
|-----------|--------|--------------|
| **Rubric10 - Automated Methods** | ✅ Complete | 16/16 concatenated + 111/111 individual |
| **Rubric10 - Curated Method** | ❌ Pending | 0/3-4 files |
| **Rubric20 - Automated Methods** | ✅ Complete | 16/16 concatenated + 111/111 individual |
| **Rubric20 - Curated Method** | ❌ Pending | 0/3-4 files |
| **Summary Reports** | ✅ Complete | All generated |
| **Structured Summaries (YAML)** | ✅ Complete | Both rubrics |
| **LinkML Schema** | ✅ Complete | D4D_Evaluation_Summary.yaml |

**Overall Completeness:** ~91% (127/140 possible evaluations)

---

## Data Quality Notes

### Known Issues
1. **VOICE/gpt5 (concatenated)** - Empty file (0% score)
   - Location: `data/d4d_concatenated/gpt5/VOICE_d4d.yaml`
   - Impact: Valid test of rubric's ability to handle empty/malformed inputs

2. **Individual AI_READI Files** - Some may have inconsistent naming
   - Example: "RePORT ⟩ RePORTER - AI-READI" vs "RePORT_RePORTER_AI_READI"
   - Impact: Minor, files were all evaluated successfully

### Validation
- All 127 evaluated files passed YAML parsing
- No evaluation errors encountered
- All scores within expected ranges (0-50 for rubric10, 0-84 for rubric20)

---

## Next Steps

1. **Evaluate Curated Files** (recommended)
   - Complete the evaluation of manually curated datasheets
   - Provide important baseline for comparison
   - Validate rubric effectiveness

2. **Generate Updated Summaries** (after curated evaluation)
   - Re-run summary scripts to include curated results
   - Update comparative analysis with curated baseline
   - Recalculate method rankings

3. **Consider Additional Analysis**
   - Inter-rater reliability (if multiple human evaluators available)
   - Correlation analysis between rubric10 and rubric20 scores
   - Identify specific D4D fields that drive high scores

---

**End of Coverage Report**
