# D4D Rubric Agent Usage Examples

This guide provides practical examples for using the `d4d-rubric10` and `d4d-rubric20` quality evaluation agents in Claude Code.

## Quick Reference

**Invoke agents with conversational prompts:**
- "Evaluate [file] with rubric10"
- "Run rubric20 assessment on [file]"
- "Score [file] using rubric10"
- "Assess quality of [file] with rubric20"

**Agent Names:**
- `d4d-rubric10` - 10-element hierarchical quality rubric (50 points max)
- `d4d-rubric20` - 20-question detailed rubric (84 points max)

---

## Basic Usage Examples

### Example 1: Evaluate Single File with Rubric10

```
User: Evaluate data/d4d_concatenated/claudecode/VOICE_d4d.yaml with rubric10

Claude: I'll evaluate the VOICE D4D file using the rubric10 quality assessment.

[Agent reads file, applies rubric10 criteria, returns evaluation]

✅ Rubric10 Evaluation Complete

**Overall Score: 38.5/50 (77.0%)**

**Strengths:**
- Comprehensive ethical documentation with IRB approval and HIPAA Safe Harbor deidentification
- Clear access mechanisms via PhysioNet registered access with explicit DUA requirements
- Detailed preprocessing pipeline with specific tools (openSMILE, Parselmouth, Whisper)
- Well-documented version history with multiple releases and change notes
- Strong community integration via PhysioNet and Bridge2AI platforms

**Weaknesses:**
- Missing funding agency and award number details
- Limited documentation of collection site specifics
- No external publication DOIs or related dataset cross-references
- Sampling bias not discussed in limitations
- Processing code repositories not linked

**Recommendations:**
- Add funding_and_acknowledgements section with NIH grant details
- Include collection_process.setting with specific site names
- Link to related publications in references field
- Add limitations section discussing selection bias
- Provide GitHub repository links for preprocessing code

**Detailed Results:** data/evaluation_llm/rubric10/detailed_analysis/VOICE_claudecode_evaluation.json
```

---

### Example 2: Evaluate Single File with Rubric20

```
User: Run rubric20 assessment on data/d4d_concatenated/claudecode/CM4AI_d4d.yaml

Claude: I'll evaluate the CM4AI D4D file using the rubric20 detailed quality assessment.

[Agent reads file, applies rubric20 criteria across 4 categories]

✅ Rubric20 Evaluation Complete

**Overall Score: 68.2/84 (81.2%)**

**Category Breakdown:**
- Structural Completeness: 21/21 (100%)
- Metadata Quality & Content: 14/22 (63.6%)
- Technical Documentation: 16/25 (64.0%)
- FAIRness & Accessibility: 17/17 (100%)

**Top Strengths:**
- Perfect structural completeness with all mandatory fields populated
- Excellent FAIR compliance (100% on findability and accessibility)
- Comprehensive keyword diversity (12 unique keywords)
- Clear license terms and access mechanisms

**Critical Gaps:**
- No funding information (Question 7: 0/5)
- Missing associated publications (Question 14: 0/5)
- Limited interoperability documentation (Question 10: 3/5)
- No cross-platform interlinking (Question 20: 0/1)

**Detailed Results:** data/evaluation_llm/rubric20/detailed_analysis/CM4AI_claudecode_evaluation.json
```

---

### Example 3: Compare Multiple Methods

```
User: Can you evaluate all VOICE D4D files (curated, gpt5, claudecode) using rubric10 and compare the results?

Claude: I'll evaluate all three VOICE D4D files with rubric10 and provide a comparison.

[Agent evaluates 3 files sequentially]

✅ Rubric10 Comparison for VOICE Project

| Method | Score | Percentage | Rank |
|--------|-------|------------|------|
| claudecode | 38.5/50 | 77.0% | 🥇 Best |
| curated | 13.0/50 | 26.0% | 🥈 Second |
| gpt5 | 5.0/50 | 10.0% | 🥉 Third |

**Key Findings:**

**Claude Code (77.0%) - Best Performance:**
- Strong across all 10 elements
- Excels in ethics (5/5), access (5/5), composition (5/5)
- Weaknesses: motivation (3/5), provenance (3/5)

**Curated (26.0%) - Moderate Performance:**
- Good ethics documentation (4/5)
- Missing discovery metadata (2/5)
- Lacks technical transparency (1/5)

**GPT-5 (10.0%) - Poor Performance:**
- Minimal metadata coverage
- Only basic fields populated
- Missing most quality details

**Conclusion:** Claude Code generates significantly more comprehensive D4D metadata (7.7× better than GPT-5, 3× better than curated).

**Detailed Results:**
- data/evaluation_llm/rubric10/detailed_analysis/VOICE_claudecode_evaluation.json
- data/evaluation_llm/rubric10/detailed_analysis/VOICE_curated_evaluation.json
- data/evaluation_llm/rubric10/detailed_analysis/VOICE_gpt5_evaluation.json
```

---

### Example 4: Evaluate All Projects with Both Rubrics

```
User: Evaluate all four projects (AI_READI, CHORUS, CM4AI, VOICE) using both rubric10 and rubric20

Claude: I'll run comprehensive evaluation using both rubrics across all projects.

[Agent evaluates 4 projects × 3 methods × 2 rubrics = 24 evaluations]

✅ Complete Evaluation Finished

**Summary by Rubric10:**

| Project | claudecode | curated | gpt5 |
|---------|-----------|---------|------|
| AI_READI | 24% | 22% | 10% |
| CHORUS | 22% | N/A | 8% |
| CM4AI | 26% | 16% | 18% |
| VOICE | 77% | 26% | 10% |
| **Average** | **37.3%** | **21.3%** | **11.5%** |

**Summary by Rubric20:**

| Project | claudecode | curated | gpt5 |
|---------|-----------|---------|------|
| AI_READI | 46% | 49% | 17% |
| CHORUS | 37% | N/A | 14% |
| CM4AI | 45% | 30% | 21% |
| VOICE | 81% | 46% | 17% |
| **Average** | **52.3%** | **41.7%** | **17.3%** |

**Key Insights:**
- Claude Code outperforms GPT-5 by 3.24× (rubric10) and 3.03× (rubric20)
- VOICE dataset has exceptional quality across all methods
- Most common gaps: funding details, publications, version history

**All Results:** data/evaluation_llm/
```

---

## Advanced Usage Examples

### Example 5: Evaluate and Get Actionable Recommendations

```
User: Evaluate data/d4d_concatenated/claudecode/CHORUS_d4d.yaml with rubric20 and give me specific actions to improve the score

Claude: I'll evaluate CHORUS with rubric20 and identify specific improvement actions.

[Agent evaluates file and analyzes gaps]

✅ CHORUS Rubric20 Evaluation: 31.2/84 (37.1%)

**Immediate Actions to Improve Score:**

**Priority 1 - Add Missing Critical Fields (+15 points potential):**
1. Add `funding_and_acknowledgements.funding` with NIH grant OT2OD032720
   - Impact: Question 7 goes from 0→5 (+5 points)

2. Add `references` section with CHORUS publication DOIs
   - Impact: Question 14 goes from 0→5 (+5 points)

3. Add `version_access` with version history and release notes
   - Impact: Question 13 goes from 0→5 (+5 points)

**Priority 2 - Enhance Existing Fields (+12 points potential):**
4. Expand `collection_process.setting` with specific site names and locations
   - Current: "Multiple clinical sites"
   - Target: "Massachusetts General Hospital, University of Florida, UT Health..."
   - Impact: Question 12 goes from 2→5 (+3 points)

5. Add `software_and_tools` with version numbers and GitHub links
   - Current: Tool names only
   - Target: "openSMILE 3.0 (github.com/audeering/opensmile)"
   - Impact: Question 11 goes from 2→5 (+3 points)

6. Add `conforms_to` field with schema references
   - Target: "schema.org/Dataset, DCAT"
   - Impact: Question 10 goes from 1→4 (+3 points)

**Priority 3 - Add Quality Documentation (+8 points potential):**
7. Add `limitations` section discussing known biases
   - Impact: Question 9 from incomplete to complete

8. Add `external_resources` with cross-platform links
   - Impact: Question 20 goes from 0→1 (+1 point)

**Expected Score After All Improvements:** 31.2 + 15 + 12 + 8 = **66.2/84 (78.8%)**
```

---

### Example 6: Identify Quality vs Presence Gaps

```
User: I ran presence detection on VOICE and got 92% but you scored it 77% on rubric10. Why the difference?

Claude: I'll analyze the gap between presence detection and quality assessment for VOICE.

[Agent compares presence scores with quality scores]

✅ Presence vs Quality Gap Analysis for VOICE

**Overall Gap: 92% presence → 77% quality = -15 percentage points**

**Fields Where Presence ≠ Quality:**

1. **Funding Information (Element 7)**
   - Presence score: 1 (field exists)
   - Quality score: 0.6 (partial - 3/5 sub-elements)
   - Gap explanation:
     - `project` field mentions "Bridge2AI" ✓
     - `keywords` includes project name ✓
     - Missing: Funding agency name ✗
     - Missing: Grant award number ✗
     - Missing: Acknowledgements section ✗

2. **Version History (Element 6)**
   - Presence score: 1 (field exists)
   - Quality score: 0.6 (partial - 3/5 sub-elements)
   - Gap explanation:
     - `dataset_version` present ("1.1") ✓
     - Version list in `version_access` ✓
     - `release_notes` present ✓
     - Missing: Detailed change descriptions ✗
     - Missing: Update schedule/frequency ✗

3. **Technical Transparency (Element 8)**
   - Presence score: 1 (field exists)
   - Quality score: 0.6 (partial - 3/5 sub-elements)
   - Gap explanation:
     - `collection_process.setting` mentions "clinical sites" ✓
     - `software_and_tools` lists tools ✓
     - `preprocessing_and_derived_data` describes pipeline ✓
     - Missing: Specific site names and protocols ✗
     - Missing: GitHub repository links ✗

**The Lesson:**
Presence detection checks IF fields exist.
Quality assessment checks HOW WELL fields are filled.

Your VOICE file has good coverage (92% of fields present) but could have richer content in several areas to reach the full 100% quality score.
```

---

### Example 7: Evaluate Before Publication

```
User: I'm about to publish the CM4AI dataset. Can you run both rubrics and tell me if it's ready?

Claude: I'll perform a pre-publication quality check using both rubrics.

[Agent evaluates with both rubric10 and rubric20]

✅ CM4AI Pre-Publication Quality Check

**Rubric10 Score: 26% (13.0/50)**
**Rubric20 Score: 45% (37.8/84)**

**Publication Readiness Assessment: ⚠️ NOT READY**

**CRITICAL Issues (must fix before publication):**

❌ **No Funding Information**
- Missing: Funding agency, grant number, acknowledgements
- Impact: Fails NIH data sharing requirements
- Fix: Add funding_and_acknowledgements section

❌ **Missing License Terms**
- Missing: Clear reuse license (CC BY, CC0, etc.)
- Impact: Users don't know if they can reuse the data
- Fix: Add license_and_use_terms.description

❌ **No IRB/Ethics Documentation**
- Missing: IRB approval information
- Impact: Cannot verify ethical compliance
- Fix: Add ethics.irb_approval

❌ **Missing Persistent Identifier**
- Missing: DOI or other persistent ID
- Impact: Dataset cannot be reliably cited
- Fix: Register DOI via Zenodo/DataCite

**HIGH Priority Issues (should fix):**

⚠️ **Limited Access Documentation**
- Present but incomplete: access_policy field exists but lacks details
- Fix: Specify exact access mechanism (open/registered/restricted)

⚠️ **No Version History**
- Missing: Release notes and versioning
- Fix: Add version_access and release_notes

⚠️ **Missing Associated Publications**
- Missing: Links to papers describing the dataset
- Fix: Add references section with DOIs

**Recommended Publication Workflow:**

1. **Fix CRITICAL issues** → Re-run evaluation → Should reach ~65%
2. **Fix HIGH priority issues** → Re-run evaluation → Should reach ~75%
3. **Review rubric20 detailed report** → Address remaining gaps
4. **Final evaluation** → Target: ≥80% on both rubrics
5. **Publish** → Dataset meets quality standards

**Estimated Time to Publication-Ready:** 2-4 days

Want me to generate a checklist with specific field additions needed?
```

---

### Example 8: Track Improvements Over Time

```
User: I updated the AI_READI file based on your recommendations last week. Can you re-evaluate with rubric20 and compare to the previous score?

Claude: I'll evaluate the updated AI_READI file and compare to your baseline.

[Agent evaluates current file and compares to cached previous evaluation]

✅ AI_READI Improvement Tracking - Rubric20

**Previous Score (2025-11-20):** 38.7/84 (46.1%)
**Current Score (2025-12-06):** 52.3/84 (62.3%)

**Improvement: +13.6 points (+16.2 percentage points)** 🎉

**What Improved:**

✅ **Added Funding Information (+5 points)**
- Question 7: 0/5 → 5/5
- Added: NIH grant OT2OD032744, Bridge2AI program acknowledgement

✅ **Enhanced Version History (+3 points)**
- Question 13: 2/5 → 5/5
- Added: Detailed release notes with specific changes per version

✅ **Added Associated Publications (+4 points)**
- Question 14: 0/5 → 4/5
- Added: 2 publication DOIs in references field

✅ **Improved Collection Documentation (+2 points)**
- Question 12: 2/5 → 4/5
- Added: Specific collection sites and institutional affiliations

✅ **Minor improvements across other fields (+1.6 points)**
- Better keyword diversity
- More complete limitations documentation

**Remaining Gaps (to reach 80%+ target):**

Still Missing (17.7 points available):
- Schema conformance documentation (Question 10: currently 2/5)
- Cross-platform interlinking (Question 20: currently 0/1)
- Software version numbers (Question 11: currently 3/5)
- More detailed human subject representation (Question 15: currently 4/5)

**Next Steps to Reach 80%:**
Add these 4 items → Would reach 68.0/84 (81.0%)

Great progress! You've addressed the major gaps. Ready to tackle the remaining items?
```

---

## Agent Invocation Patterns

### Direct File Path
```
Evaluate data/d4d_concatenated/claudecode/VOICE_d4d.yaml with rubric10
```

### Relative Path
```
Run rubric20 on ./data/d4d_concatenated/gpt5/CM4AI_d4d.yaml
```

### Just Filename (if context is clear)
```
Score CHORUS_d4d.yaml using rubric10
```

### Multiple Files
```
Evaluate both AI_READI_d4d.yaml and CHORUS_d4d.yaml with rubric20
```

### Comparison Request
```
Compare claudecode vs gpt5 for VOICE using rubric10
```

### With Specific Output Request
```
Run rubric10 on VOICE and export results to JSON
```

---

## Understanding Agent Output

### Rubric10 Output Structure

```json
{
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
    "strengths": [...],
    "weaknesses": [...],
    "recommendations": [...]
  }
}
```

**Key Fields:**
- `overall_score.percentage` - Main quality metric (0-100%)
- `elements[].element_score` - Score for each of 10 elements (0-5)
- `sub_elements[].score` - Binary score per criterion (0 or 1)
- `evidence` - Actual field values from D4D file
- `quality_note` - Explanation of scoring decision

### Rubric20 Output Structure

```json
{
  "overall_score": {
    "total_points": 72.5,
    "max_points": 84,
    "percentage": 86.3
  },
  "categories": [
    {
      "name": "Structural Completeness",
      "category_score": 21,
      "category_max": 21,
      "questions": [
        {
          "id": 1,
          "name": "Field Completeness",
          "score_type": "numeric",
          "score": 5,
          "max_score": 5,
          "score_label": "≥90% fields populated",
          "evidence": "id, title, description, keywords, license all present",
          "quality_note": "All mandatory fields comprehensively populated"
        },
        ...
      ]
    },
    ...
  ]
}
```

**Key Differences from Rubric10:**
- `categories` instead of `elements` (4 categories vs 10 elements)
- `score_type` field ("numeric" or "pass_fail")
- `score_label` describing quality level
- Numeric questions use 0-5 scale (not binary 0/1)

---

## Common Questions

### Q: How long does evaluation take?
**A:** 30-60 seconds per file (LLM needs to read and assess ~100+ fields)

### Q: Can I evaluate multiple files at once?
**A:** Yes - the agent can evaluate multiple files sequentially and provide comparison tables

### Q: What if my D4D file is in a different format?
**A:** The agent handles both:
- Flat D4D schema (used by GPT-5 and Claude Code)
- DatasetCollection schema (used by curated files)

### Q: How do I interpret the percentage scores?
**A:** Quality levels:
- 80-100%: Excellent - Publication-ready
- 60-79%: Very Good - Minor improvements needed
- 40-59%: Good - Several gaps to address
- 20-39%: Fair - Significant work required
- 0-19%: Poor - Major revision needed

### Q: Why do rubric10 and rubric20 give different percentages?
**A:** They measure different things:
- **Rubric10**: Hierarchical coverage across 10 metadata dimensions
- **Rubric20**: Detailed FAIR compliance with quality gradations

Both are valid - rubric10 is simpler, rubric20 is more nuanced.

### Q: Can I save the evaluation results?
**A:** Yes - results are automatically saved to:
- JSON: `data/evaluation_llm/rubric*/detailed_analysis/{PROJECT}_{METHOD}_evaluation.json`
- Markdown: `data/evaluation_llm/rubric*/summary_report.md`
- CSV: `data/evaluation_llm/rubric*/scores.csv`

---

## Tips for Best Results

1. **Start with Rubric10** - Simpler, faster, good overview
2. **Use Rubric20 for deep dives** - More detailed, identifies specific gaps
3. **Evaluate before major releases** - Catch issues early
4. **Track improvements over time** - Re-evaluate after making changes
5. **Compare methods** - Evaluate curated, gpt5, and claudecode side-by-side
6. **Read the recommendations** - Agent provides specific, actionable fixes
7. **Check the evidence** - See exactly which fields were assessed

---

## Batch Processing (Makefile)

For systematic evaluation of many files, use Makefile commands:

```bash
# Evaluate all D4D files with rubric10
make evaluate-d4d-llm-rubric10

# Evaluate all D4D files with rubric20
make evaluate-d4d-llm-rubric20

# Evaluate with both rubrics
make evaluate-d4d-llm-both

# Compare LLM vs presence-based evaluation
make compare-evaluations

# View summary reports
make eval-llm-summary
```

See `CLAUDE.md` for complete Makefile documentation.
