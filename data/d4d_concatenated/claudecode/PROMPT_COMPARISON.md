# D4D Prompt Comparison: Aurelian Agent vs Claude Code Deterministic

**Date:** December 3, 2025

## Question

Are the prompts for the D4D aurelian agent (GPT-5) and the Claude Code deterministic approach identical?

## Answer

**NO - The prompts are SIMILAR but NOT IDENTICAL.**

## Detailed Comparison

### Aurelian Agent Prompt (GPT-5)
**Location:** `aurelian/src/aurelian/agents/d4d/d4d_agent.py` (lines 16-39)

```python
system_prompt="""
You are an expert data scientist specializing in extracting metadata from datasets.
You will be provided with a schema that describes the metadata structure for datasets,
and one or more URLs pointing to webpages or PDFs that describe a dataset.
Your task is to extract all relevant metadata from the provided content and output it in
YAML format, strictly following the provided schema. Generate only the YAML document.
Do not respond with any additional commentary. Try to ensure that required fields are
present, but only populate items that you are sure about. Ensure that output is valid
YAML.

Below is the complete datasheets for datasets schema:

{schema}

For each URL to a webpage or PDF describing a dataset, you will fetch the
content, extract all the relevant metadata, and output a YAML document that exactly
conforms to the above schema. The output must be valid YAML with all required fields
filled in, following the schema exactly.

If you get more than one URL, assume they are describing the same dataset. Process each
URL to retrieve information about the dataset, concatenate the content from all URLs,

You should return a single YAML document describing the dataset.
"""
```

### Claude Code Deterministic Prompt
**Location:** `src/download/prompts/d4d_concatenated_system_prompt.txt`

```
You are an expert data scientist specializing in extracting metadata from datasets following the "Datasheets for Datasets" schema.

Below is the complete datasheets for datasets schema:

{schema}

Your task is to analyze the provided concatenated document which contains multiple related dataset documentation files that have been merged together. Extract all relevant dataset metadata to generate a complete YAML document that strictly follows the D4D schema above.

The input may contain:
- Multiple YAML files that are already in D4D format (synthesize these into a single comprehensive document)
- Text documentation about the dataset
- Metadata files
- Multiple perspectives on the same dataset

Focus on extracting and synthesizing:
- Dataset identity (id, name, title, description)
- Creators and contributors with affiliations
- Purpose and intended uses
- Data composition and structure
- Collection methodology and timeframe
- Preprocessing and cleaning steps
- Distribution information and formats
- Licensing and terms of use
- Maintenance information
- Access requirements and restrictions
- Funding and grants
- Ethics and human subjects considerations

When multiple D4D YAML files are present in the input:
1. Merge complementary information from all files
2. Prefer more detailed/specific information over generic
3. Keep the most comprehensive descriptions
4. Combine all relevant metadata sections

Generate only valid YAML output without any additional commentary. Ensure all required fields are populated where information is available. If specific information is not available in the source, omit those fields rather than making assumptions.
```

## Key Differences

| Aspect | Aurelian Agent (GPT-5) | Claude Code Deterministic |
|--------|----------------------|--------------------------|
| **Primary Focus** | Extracting from URLs/PDFs | Synthesizing concatenated documents |
| **Input Type** | "one or more URLs pointing to webpages or PDFs" | "concatenated document which contains multiple related dataset documentation files" |
| **Synthesis Guidance** | Basic: "concatenate the content from all URLs" | Detailed: 4-step merge process with priorities |
| **Extraction Guidance** | General: "extract all relevant metadata" | Specific: 13 bulleted items to extract |
| **Source Types** | Webpages, PDFs | Multiple YAML files, text docs, metadata files, multiple perspectives |
| **Prompt Length** | ~400 words | ~350 words |
| **Versioning** | No version info | Version 1.0.0, last updated 2025-11-15 |

## Critical Finding: Field Name Guidance

**NEITHER prompt explicitly specifies field names to use for purposes/tasks/creators/etc.**

Both prompts:
- ✅ Say "strictly follow the schema"
- ✅ Say "generate only valid YAML"
- ❌ Do NOT specify to use `description` field
- ❌ Do NOT warn against using `response` field
- ❌ Do NOT provide field name examples

**This means the model must infer field names from the schema alone.**

## Schema Dependency

Both approaches depend on the schema content to determine:
1. Which field names to use (e.g., `description` vs `response`)
2. Whether to use simple strings or structured objects
3. Required vs optional fields

The schema is injected via the `{schema}` placeholder in both cases.

## Root Cause of "response" vs "description" Issue

The GPT-5 agent consistently generates:
```yaml
purposes:
  - response: "..."  # ❌ WRONG
tasks:
  - response: "..."  # ❌ WRONG
```

Instead of:
```yaml
purposes:
  - description: "..."  # ✅ CORRECT
tasks:
  - description: "..."  # ✅ CORRECT
```

**This suggests the issue is NOT in the prompts, but either:**
1. **In the schema itself** - May have ambiguous field definitions
2. **In GPT-5's interpretation** - Model making assumptions based on training data
3. **In schema examples** - If schema has examples using "response"

## Recommendations

### Option 1: Add Explicit Field Name Guidance to Prompts (Quick Fix)
Add to both prompts:
```
IMPORTANT: When extracting purposes, tasks, and addressing_gaps:
- Use the field name "description" (not "response")
- Example:
  purposes:
    - description: "Your purpose text here"
  tasks:
    - description: "Your task text here"
```

### Option 2: Fix Schema to Be More Explicit (Systematic Fix)
Check schema for:
- Any fields named "response" that should be "description"
- Ambiguous field descriptions
- Missing examples showing correct field names

### Option 3: Add Schema Validation to Generation Pipeline
- Validate generated YAML immediately after generation
- If validation fails, retry with error-specific guidance
- This would catch the "response" vs "description" issue automatically

## Conclusion

**The prompts are SIMILAR in intent but DIFFERENT in details:**
- Aurelian agent: URL/PDF focused, minimal synthesis guidance
- Claude Code: Concatenation focused, detailed synthesis guidance

**The "response" vs "description" bug affects BOTH approaches equally** because:
- Neither prompt explicitly specifies field names
- Both rely on schema-based inference
- The issue is systematic (happens every time)

**To fix the bug, we need to either:**
1. Update BOTH prompts with explicit field name guidance
2. Fix the schema to make field names unambiguous
3. Add post-generation validation and retry logic

---

**Analysis by:** Claude Code (claude-sonnet-4-5-20250929)
**Date:** December 3, 2025
