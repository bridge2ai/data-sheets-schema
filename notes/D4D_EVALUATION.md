# D4D Evaluation Framework

## Overview

This document describes the evaluation framework for comparing D4D (Datasheets for Datasets) metadata across three generation methods:

1. **Curated Comprehensive**: Manually curated datasheets in DatasetCollection format
2. **GPT-5**: Generated using GPT-5 API
3. **Claude Code Deterministic**: Generated using Claude Code assistant with direct synthesis (temperature=0.0)

## Evaluation Rubrics

Two rubrics are used for evaluation:

### Rubric10: Complex Proxy Rubric

- **Structure**: 10 hierarchical elements, each with 5 sub-elements
- **Scoring**: Binary (0/1) for each sub-element, summing to element score (0-5)
- **Maximum**: 50 points (10 elements × 5 points each)
- **Focus Areas**:
  1. Dataset Discovery and Identification
  2. Dataset Access and Retrieval
  3. Data Reuse and Interoperability
  4. Ethical Use and Privacy Safeguards
  5. Data Composition and Structure
  6. Data Provenance and Version Tracking
  7. Scientific Motivation and Funding Transparency
  8. Technical Transparency (Data Collection and Processing)
  9. Dataset Evaluation and Limitations Disclosure
  10. Cross-Platform and Community Integration

### Rubric20: Detailed Evaluation Rubric

- **Structure**: 20 questions in 4 categories
- **Scoring**: Quality-based (0-5 scale) or pass/fail
- **Maximum**: 84 points (varies by question type)
- **Categories**:
  1. Structural Completeness (5 questions)
  2. Metadata Quality & Content (5 questions)
  3. Technical Documentation (5 questions)
  4. FAIRness & Accessibility (5 questions)

## Scoring Methodology

### Field Extraction

The evaluation script extracts fields from D4D YAML using dot notation paths:
- Simple fields: `title`, `description`, `keywords`
- Nested fields: `license_and_use_terms.description`, `ethics.irb_approval`
- List/dict fields: Checked for non-empty presence

### Rubric10 Scoring

For each element:
1. Check each of 5 sub-elements for field presence
2. Score 1 if field exists and is non-empty, 0 otherwise
3. Sum sub-element scores for element score (0-5)
4. Sum all element scores for total (0-50)

### Rubric20 Scoring

For each question:
- **Pass/Fail questions**: 1 if field present, 0 otherwise
- **Numeric questions** (0-5): Currently uses simple heuristic:
  - 0 if field absent
  - 4 if field present (simplified for initial evaluation)
  - Future enhancement: Quality-based scoring using field content analysis

## Schema Format Compatibility

The evaluation script handles two schema formats:

1. **Flat D4D Schema** (used by GPT-5 and Claude Code):
   ```yaml
   id: "..."
   title: "..."
   description: "..."
   ```

2. **DatasetCollection Schema** (used by Curated):
   ```yaml
   DatasetCollection:
     resources:
       - id: "..."
         title: "..."
         description: "..."
   ```

The script automatically detects and extracts data from the first resource in DatasetCollection format.

## Evaluation Results Summary

Generated: 2025-11-17

### Overall Method Rankings

1. **Claude Code Deterministic** (BEST)
   - Rubric10: 37.5% average
   - Rubric20: 52.4% average

2. **Curated Comprehensive** (SECOND)
   - Rubric10: 21.3% average
   - Rubric20: 41.7% average

3. **GPT-5** (THIRD)
   - Rubric10: 11.5% average
   - Rubric20: 17.3% average

### Project-Specific Results

#### VOICE (Best Claude Code Performance)
- Claude Code: 78% (Rubric10), 81% (Rubric20) ⭐ **Exceptional**
- Curated: 26% (Rubric10), 46% (Rubric20)
- GPT-5: 10% (Rubric10), 17% (Rubric20)

#### AI_READI
- Curated: 22% (Rubric10), 49% (Rubric20)
- Claude Code: 24% (Rubric10), 46% (Rubric20)
- GPT-5: 10% (Rubric10), 17% (Rubric20)

#### CM4AI
- Claude Code: 26% (Rubric10), 45% (Rubric20) ⭐ **Best**
- GPT-5: 18% (Rubric10), 21% (Rubric20)
- Curated: 16% (Rubric10), 30% (Rubric20)

#### CHORUS
- Claude Code: 22% (Rubric10), 37% (Rubric20)
- GPT-5: 8% (Rubric10), 14% (Rubric20)
- Curated: N/A (no curated version available)

### Key Findings

1. **Claude Code Significantly Outperforms GPT-5**
   - 3.26× better on Rubric10
   - 3.03× better on Rubric20
   - Consistent advantage across all projects

2. **VOICE Dataset Shows Exceptional Quality**
   - Claude Code VOICE D4D scores 78-81% (highest across all evaluations)
   - Strong metadata coverage across all rubric elements
   - Well-documented ethics, composition, and technical details

3. **GPT-5 Generates "Thin" Metadata**
   - Consistently scores lowest across all projects
   - 8-18% on Rubric10, 14-21% on Rubric20
   - Missing critical fields for discovery, ethics, and interoperability

4. **Curated Files Have Mixed Performance**
   - Better than GPT-5 but generally below Claude Code
   - DatasetCollection schema format differs from D4D schema
   - May be missing some D4D-specific fields the rubrics expect

5. **Most Commonly Missing Elements** (across all methods):
   - Scientific motivation and funding details (Element 7)
   - Schema/ontology conformance (Element 3)
   - Deidentification methods (Element 4)

## Usage

### Run Full Evaluation
```bash
make evaluate-d4d
```

### Evaluate Single Project
```bash
make evaluate-d4d-project PROJECT=VOICE
```

### View Summary Report
```bash
make eval-summary
```

### View Detailed Report
```bash
make eval-details PROJECT=VOICE METHOD=claudecode
```

### Output Files

All evaluation results are written to `data/evaluation/`:

- `summary_report.md` - Executive summary with comparison tables
- `detailed_analysis/{PROJECT}_{METHOD}_evaluation.md` - Detailed breakdowns
- `scores.csv` - All scores in CSV format
- `scores.json` - All scores with full details in JSON

## Future Enhancements

1. **Enhanced Rubric20 Scoring**: Implement quality-based scoring that analyzes field content (e.g., string length, completeness, specificity)

2. **Visualization**: Generate charts comparing methods across projects and rubric elements

3. **Automated Recommendations**: Identify specific missing fields and suggest improvements

4. **Version Tracking**: Compare evaluations across D4D versions over time

5. **Custom Rubrics**: Support project-specific or domain-specific evaluation criteria

## References

- Rubric files: `data/rubric/rubric10.txt`, `data/rubric/rubric20.txt`
- Evaluation script: `src/evaluation/evaluate_d4d.py`
- D4D Schema: `src/data_sheets_schema/schema/data_sheets_schema_all.yaml`
- Datasheets for Datasets paper: Gebru et al., Communications of the ACM (2021)
