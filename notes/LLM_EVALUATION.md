# LLM-Based D4D Evaluation Methodology

## Overview

This document describes the LLM-as-judge evaluation framework for assessing D4D (Datasheets for Datasets) quality using Claude Sonnet 4.5. This evaluation method **complements** the existing field-presence detection system by providing deep quality assessment of content rather than just checking if fields exist.

### Key Differences: Presence vs Quality Evaluation

| Aspect | Presence Detection | LLM Quality Assessment |
|--------|-------------------|----------------------|
| **What It Checks** | Field exists (not null/empty) | Content is complete, actionable, useful |
| **Speed** | ~1 second | ~30-60 seconds per file |
| **Cost** | Free | ~$0.10-0.30 per file |
| **Insight Level** | "Field missing" | "Field present but generic/incomplete/excellent" |
| **Evidence** | None | Quotes, reasoning, context |
| **Best Use Case** | CI/CD, quick checks | Deep analysis, comparison |
| **Reproducibility** | Fully deterministic | Fully deterministic |

### Evaluation Philosophy

**Presence-based evaluation asks:** "Is this field populated?"
**LLM quality assessment asks:** "Does this field provide meaningful, actionable information to dataset users?"

## LLM Configuration

### Model and Parameters

```python
model: claude-sonnet-4-5-20250929  # Date-pinned for consistency
temperature: 0.0                   # Fully deterministic evaluation
max_tokens: 8000                   # Sufficient for detailed evaluation
```

### Why Temperature 0.0?

**Full Determinism for Reproducible Quality Assessment**

1. **Reproducibility**: Same D4D file → Same quality score every time
2. **Consistency**: Multiple evaluations produce identical results
3. **Reliability**: No variance in quality assessments across runs
4. **Scientific Rigor**: Same measurement should give same result
5. **Rubric Provides Structure**: Clear criteria already defined ("meaningful, actionable information")

Like D4D generation (temperature=0.0), evaluation benefits from full determinism:
- Enables reliable before/after comparisons
- Supports tracking improvements over time
- Allows controlled experiments comparing D4D methods
- No "creativity" needed - just consistent application of rubric criteria

## Evaluation Rubrics

Both rubrics are used for comprehensive assessment:

### Rubric10: Hierarchical Quality Assessment

- **Structure**: 10 elements × 5 sub-elements = 50 total assessments
- **Scoring**: Binary (0/1) per sub-element based on quality criteria
- **Maximum**: 50 points
- **Approach**: Element-by-element systematic evaluation

**Quality Criteria for Score=1:**
- ✅ Field exists AND is non-empty
- ✅ Contains meaningful, non-trivial content
- ✅ Provides actionable information to dataset users
- ✅ Complete enough to support the sub-element's stated purpose

**Example Comparison:**

| Content | Presence Score | LLM Quality Score | Why? |
|---------|---------------|------------------|------|
| "Data collected from multiple sites" | 1 (exists) | 0 (insufficient) | Too generic, no actionable detail |
| "Data collected from 5 specialty clinics (MGH: voice disorders, UF: respiratory, UT Health: neurological, Tufts: mood disorders, Emory: cardiac) with full IRB approval" | 1 (exists) | 1 (excellent) | Specific, actionable, complete |

### Rubric20: Detailed Category-Based Evaluation

- **Structure**: 20 questions in 4 categories
- **Scoring**: Mixed (0-5 numeric scale OR pass/fail)
- **Maximum**: 84 points
- **Categories**:
  1. Structural Completeness (24 points max)
  2. Metadata Quality & Content (22 points max)
  3. Technical Documentation (25 points max)
  4. FAIRness & Accessibility (13 points max)

**Numeric Question Scoring (0-5 scale):**

| Score | Quality Level | Description |
|-------|--------------|-------------|
| 5 | Excellent | Comprehensive, detailed, actionable information |
| 4 | Very Good | Most information present with minor gaps |
| 3 | Good | Adequate information but lacking some detail |
| 2 | Fair | Minimal information, significant gaps |
| 1 | Poor | Very limited information, mostly incomplete |
| 0 | Absent | No relevant information found |

**Pass/Fail Question Scoring:**
- **Pass (1)**: Required information is present and meaningful
- **Fail (0)**: Required information is missing or insufficient

## Architecture

### Interactive Mode: Claude Agents

Two specialized agents for conversational use:

**`.claude/agents/d4d-rubric10.md`** - Quality-based rubric10 evaluation
```yaml
name: d4d-rubric10
description: Quality-based evaluation using 10-element hierarchical rubric
model: claude-sonnet-4-5-20250929
color: purple
```

**`.claude/agents/d4d-rubric20.md`** - Detailed rubric20 evaluation
```yaml
name: d4d-rubric20
description: Detailed quality evaluation using 20-question rubric
model: claude-sonnet-4-5-20250929
color: purple
```

### Batch Mode: Python Backend

**`src/evaluation/evaluate_d4d_llm.py`** - Main evaluation script

Key components:
- `D4DLLMEvaluator` class - Orchestrates evaluation
- System prompt templates - Define evaluation criteria
- Response parsing - Extracts JSON from LLM output
- Multi-format export - CSV, JSON, Markdown

## Prompt Engineering

### System Prompt Structure

Located in `src/download/prompts/`:
- `rubric10_system_prompt.md` - Instructions for rubric10 evaluation
- `rubric20_system_prompt.md` - Instructions for rubric20 evaluation

**Prompt Components:**

1. **Role Definition**: "You are an expert evaluator of dataset documentation quality"
2. **Task Description**: Quality-based assessment across rubric elements
3. **Scoring Criteria**: Clear definitions for each quality level
4. **Rubric Specification**: Complete rubric YAML embedded in prompt
5. **Output Format**: JSON schema with examples
6. **Evidence Requirements**: Must provide quotes and reasoning

### User Prompt Structure

```markdown
# D4D File to Evaluate

{FULL D4D YAML CONTENT}

# Your Task

Evaluate this D4D file using the rubric specification provided in the system prompt.
For each element/question:
1. Assess content quality (not just presence)
2. Provide evidence (quotes from the D4D file)
3. Assign score based on quality criteria
4. Include quality assessment note

Return your evaluation as JSON following the specified format.
```

## Output Format

### JSON Structure

Both rubrics return structured JSON with:

```json
{
  "rubric": "rubric10" | "rubric20",
  "version": "1.0",
  "d4d_file": "VOICE_d4d.yaml",
  "project": "VOICE",
  "method": "claudecode",
  "evaluation_timestamp": "2025-12-06T15:30:00Z",
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
  "elements": [...],  // or "categories": [...] for rubric20
  "assessment": {
    "strengths": ["...", "...", "..."],
    "weaknesses": ["...", "...", "..."],
    "recommendations": ["...", "...", "..."]
  },
  "metadata": {
    "evaluator_id": "<uuid>",
    "rubric_hash": "<sha256>",
    "d4d_file_hash": "<sha256>"
  }
}
```

### Export Formats

**CSV** (`scores.csv`):
```csv
Project,Method,Rubric,Score,Percentage
VOICE,claudecode,rubric10,38.5,77.0
VOICE,claudecode,rubric20,68.2,81.2
```

**Markdown** (`summary_report.md`):
- Executive summary with comparison tables
- Top strengths and weaknesses
- Recommendations for improvement
- Methodology explanation

**JSON** (`scores.json`):
- Complete hierarchical structure
- Full evidence and quality notes
- Metadata and provenance information

## Usage

### Interactive Usage (Agents)

```bash
# Launch Claude Code and invoke agent
> Can you evaluate data/d4d_concatenated/claudecode/VOICE_d4d.yaml using d4d-rubric10?

# Agent returns:
✅ Rubric10 Evaluation Complete
Overall Score: 38.5/50 (77%)

Strengths:
- Comprehensive ethical documentation with IRB approval
- Clear access mechanisms and licensing
- Detailed preprocessing pipeline

Weaknesses:
- Missing funding agency and award details
- Limited version history documentation
- No external publication links

[Full results saved to data/evaluation_llm/...]
```

### Batch Usage (Makefile)

```bash
# Evaluate single file
make evaluate-d4d-llm \
  FILE=data/d4d_concatenated/claudecode/VOICE_d4d.yaml \
  PROJECT=VOICE METHOD=claudecode RUBRIC=both

# Evaluate all files with rubric10
make evaluate-d4d-llm-rubric10

# Evaluate all files with rubric20
make evaluate-d4d-llm-rubric20

# Evaluate all files with both rubrics
make evaluate-d4d-llm-both

# View summary reports
make eval-llm-summary

# Compare LLM vs presence-based evaluation
make compare-evaluations
```

### Direct Script Usage

```bash
# Single file evaluation
poetry run python src/evaluation/evaluate_d4d_llm.py \
  --file data/d4d_concatenated/claudecode/VOICE_d4d.yaml \
  --project VOICE --method claudecode --rubric both \
  --output-dir data/evaluation_llm

# Batch evaluation
poetry run python src/evaluation/evaluate_d4d_llm.py \
  --all --rubric both \
  --output-dir data/evaluation_llm

# Script options:
#   --file PATH              Single D4D file to evaluate
#   --project NAME           Project name (AI_READI, CHORUS, CM4AI, VOICE)
#   --method NAME            Generation method (curated, gpt5, claudecode)
#   --rubric RUBRIC          Which rubric (rubric10, rubric20, both)
#   --all                    Evaluate all D4D files
#   --output-dir PATH        Output directory (default: data/evaluation_llm)
```

## Output Directory Structure

```
data/evaluation_llm/
  rubric10/
    summary_report.md              # Executive summary
    detailed_analysis/
      VOICE_claudecode_evaluation.md
      AI_READI_claudecode_evaluation.md
      CM4AI_gpt5_evaluation.md
      ...
    scores.csv                     # CSV format
    scores.json                    # Full JSON
  rubric20/
    summary_report.md
    detailed_analysis/
      ...
    scores.csv
    scores.json
  combined/
    comparison_report.md           # Compare both rubrics
    scores.csv
```

## Comparison with Presence-Based Evaluation

### Running Comparison

```bash
# Generate both evaluations
make evaluate-d4d                  # Presence-based
make evaluate-d4d-llm-both         # LLM quality assessment

# Compare results
make compare-evaluations

# Output: data/evaluation_comparison/
#   - comparison.csv               # Side-by-side scores
#   - comparison_report.md         # Analysis with insights
```

### Comparison Script Output

The comparison identifies:

1. **Cases Where LLM Scored Higher** (Quality > Presence)
   - Presence detection gave credit for incomplete fields
   - LLM detected higher quality content

2. **Cases Where Presence Scored Higher** (Presence > Quality)
   - Fields exist but quality is low
   - Content is generic, incomplete, or non-actionable
   - **Most important findings for improvement**

**Example Insight:**

```markdown
**VOICE - claudecode (rubric10): -15.2%**
- Fields exist (presence=92.0%) but quality is low (LLM=76.8%)
- Quality issues identified by LLM:
  - "Funding field present but lacks grant number and agency details"
  - "Version history lists dates but missing change descriptions"
  - "Tools listed without version numbers or repository links"
```

## Cost Estimates

### API Usage Costs

Based on Claude Sonnet 4.5 pricing (as of December 2025):

**Per File Evaluation:**
- Input tokens: ~6,000-8,000 (rubric + D4D content)
- Output tokens: ~2,000-3,000 (detailed JSON response)
- **Cost per file**: ~$0.10-0.30

**Batch Evaluation (typical project):**
- 4 projects × 3 methods = 12 files
- Both rubrics = 24 evaluations
- **Total cost**: ~$2.40-7.20

**Annual Monitoring (monthly checks):**
- 24 evaluations × 12 months = 288 evaluations/year
- **Annual cost**: ~$28.80-86.40

### Cost Optimization

1. **Use presence detection first** (free, fast) to catch missing fields
2. **Run LLM evaluation periodically** (monthly/quarterly) rather than continuously
3. **Focus LLM on quality gaps** identified by presence detection
4. **Cache rubric specifications** to reduce input tokens
5. **Use batch processing** to minimize API overhead

## Best Practices

### When to Use LLM Evaluation

✅ **Good Use Cases:**
- Deep quality assessment before publication
- Comparing D4D generation methods
- Identifying specific content improvements
- Quarterly quality audits
- Preparing datasets for community release

❌ **Poor Use Cases:**
- CI/CD validation (too slow, costs money)
- Real-time field validation
- Checking if required fields exist (use presence detection)
- Frequent iterative development

### Recommended Workflow

1. **Development Phase**: Use presence detection (`make evaluate-d4d`)
2. **Quality Check**: Run LLM evaluation before release (`make evaluate-d4d-llm-both`)
3. **Comparison**: Compare methods to identify best approach
4. **Improvement**: Use LLM recommendations to enhance metadata
5. **Monitoring**: Periodic LLM evaluation (monthly/quarterly)

### Interpreting Results

**High Presence, Low LLM Score:**
- Fields exist but content is generic or incomplete
- **Action**: Enhance content quality, add specific details

**Low Presence, Low LLM Score:**
- Fields missing entirely
- **Action**: Add missing fields first (presence detection will flag these)

**High Presence, High LLM Score:**
- Well-documented dataset with comprehensive metadata
- **Action**: Maintain quality standards

**Percentage Ranges:**

| Score Range | Quality Level | Interpretation |
|-------------|--------------|----------------|
| 80-100% | Excellent | Publication-ready, comprehensive documentation |
| 60-79% | Very Good | Solid documentation with minor gaps |
| 40-59% | Good | Adequate but needs improvement |
| 20-39% | Fair | Significant gaps, requires attention |
| 0-19% | Poor | Minimal documentation, extensive work needed |

## Troubleshooting

### Common Issues

**Issue: "anthropic module not found"**
```bash
# Solution: Install Anthropic Python SDK
poetry add anthropic
# or
pip install anthropic
```

**Issue: "ANTHROPIC_API_KEY environment variable not set"**
```bash
# Solution: Set API key
export ANTHROPIC_API_KEY=sk-ant-...
# Or add to .env file (not committed to git)
```

**Issue: "JSON parsing failed"**
- LLM sometimes returns JSON in markdown code blocks
- Parser automatically handles ```json ... ``` wrapping
- If persistent, check prompt template formatting

**Issue: "Rate limit exceeded"**
```bash
# Solution: Add delays between evaluations
poetry run python src/evaluation/evaluate_d4d_llm.py \
  --all --delay 2.0  # 2 second delay between files
```

**Issue: "Evaluation too expensive"**
```bash
# Solution 1: Evaluate fewer files
poetry run python src/evaluation/evaluate_d4d_llm.py \
  --project VOICE --method claudecode

# Solution 2: Use single rubric
make evaluate-d4d-llm-rubric10  # Cheaper than both

# Solution 3: Use presence detection for routine checks
make evaluate-d4d  # Free, fast
```

### Debugging

**Enable verbose output:**
```bash
poetry run python src/evaluation/evaluate_d4d_llm.py \
  --file data/d4d_concatenated/claudecode/VOICE_d4d.yaml \
  --verbose
```

**Check intermediate outputs:**
1. System prompt: `data/evaluation_llm/debug/system_prompt.txt`
2. User prompt: `data/evaluation_llm/debug/user_prompt.txt`
3. Raw LLM response: `data/evaluation_llm/debug/raw_response.json`

**Validate rubric loading:**
```python
from pathlib import Path
from src.evaluation.evaluate_d4d_llm import D4DLLMEvaluator

evaluator = D4DLLMEvaluator()
print(evaluator.rubric10)  # Should show rubric YAML
print(evaluator.rubric20)  # Should show rubric YAML
```

## Dependencies

### Required Environment Variables

```bash
export ANTHROPIC_API_KEY=sk-ant-...  # Required
```

### Python Packages

```toml
[tool.poetry.dependencies]
anthropic = "^0.39.0"  # Claude API
pyyaml = "^6.0.1"      # YAML parsing
```

Install with:
```bash
poetry add anthropic
# or
pip install anthropic pyyaml
```

## Future Enhancements

### Planned Improvements

1. **Custom Rubrics**: Support project-specific or domain-specific evaluation criteria
2. **Automated Recommendations**: Generate specific field-level improvement suggestions
3. **Trend Analysis**: Track quality improvements over time with version comparison
4. **Visualization**: Charts comparing methods across projects and rubric elements
5. **Multi-Model Comparison**: Compare Claude vs GPT-4 as judges
6. **Cost Tracking**: Built-in API usage monitoring and cost reporting
7. **Caching**: Cache LLM evaluations to avoid redundant API calls
8. **Incremental Evaluation**: Only re-evaluate changed sections
9. **Quality Thresholds**: Configurable pass/fail thresholds for CI/CD
10. **Human-in-the-Loop**: Interactive correction of LLM assessments

### Experimental Features

**Meta-Evaluation**: Evaluate the evaluator
- Compare LLM assessments with human expert judgments
- Calibrate scoring thresholds
- Identify systematic biases

**Adversarial Testing**: Generate edge cases
- Minimal valid D4D files
- Maximum valid D4D files
- Verify rubric coverage

**Multi-Rubric Synthesis**: Combine insights
- Weight different rubric elements
- Generate composite quality scores
- Identify cross-rubric patterns

## References

### Code Files
- LLM evaluation script: `src/evaluation/evaluate_d4d_llm.py`
- Comparison script: `src/evaluation/compare_evaluation_methods.py`
- Rubric10 agent: `.claude/agents/d4d-rubric10.md`
- Rubric20 agent: `.claude/agents/d4d-rubric20.md`
- System prompts: `src/download/prompts/rubric*_system_prompt.md`
- Output formats: `src/download/prompts/rubric*_output_format.json`

### Rubric Specifications
- Rubric10: `data/rubric/rubric10.txt` (10 elements, 5 sub-elements each)
- Rubric20: `data/rubric/rubric20.txt` (20 questions, 4 categories)

### Related Documentation
- D4D Schema: `src/data_sheets_schema/schema/data_sheets_schema_all.yaml`
- Presence-based evaluation: `notes/D4D_EVALUATION.md`
- User guide: `CLAUDE.md` (lines 808-945)
- Datasheets for Datasets paper: Gebru et al., Communications of the ACM (2021)

### External Resources
- Claude Sonnet 4.5 Documentation: https://docs.anthropic.com/en/docs/models-overview
- Anthropic Python SDK: https://github.com/anthropics/anthropic-sdk-python
- LLM-as-Judge: https://arxiv.org/abs/2306.05685
