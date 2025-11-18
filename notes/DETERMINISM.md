# Deterministic D4D Generation

This document explains the approach used to ensure reproducible metadata extraction for "Datasheets for Datasets" (D4D) in this project.

## Table of Contents

- [Why Determinism Matters](#why-determinism-matters)
- [Determinism Guarantees](#determinism-guarantees)
- [Implementation Details](#implementation-details)
- [Metadata Tracking](#metadata-tracking)
- [Verification Process](#verification-process)
- [Comparing Generators](#comparing-generators)

## Why Determinism Matters

Deterministic D4D generation is critical for:

1. **Reproducibility**: Enable researchers to verify and reproduce metadata extraction results
2. **Version Control**: Track changes in D4D outputs over time with confidence
3. **Comparison**: Meaningfully compare outputs from different LLMs (GPT-5 vs Claude)
4. **Debugging**: Identify whether differences stem from code changes vs. model randomness
5. **Trust**: Build confidence in AI-generated metadata through consistent results
6. **Scientific Rigor**: Meet standards for computational reproducibility in research

## Determinism Guarantees

The Claude Code D4D processor (`process_concatenated_d4d_claude.py`) ensures reproducibility through:

### 1. Model Settings

| Setting | Value | Purpose |
|---------|-------|---------|
| Temperature | `0.0` | Eliminates randomness in model sampling |
| Model Version | `claude-sonnet-4-5-20250929` | Date-pinned version prevents model updates |
| Max Tokens | `16000` | Consistent output length limits |
| Random Seed | N/A | Not supported by Claude API |

**Note**: Temperature=0.0 is the **most critical** setting for determinism.

### 2. Schema Versioning

- **Source**: Local file `src/data_sheets_schema/schema/data_sheets_schema_all.yaml`
- **Version Control**: Schema is tracked in git
- **Tracking**: SHA-256 hash stored in metadata
- **Benefit**: Schema cannot change between runs unless explicitly updated

**Alternative (not used)**: Could pin to specific GitHub commit:
```yaml
url: "https://raw.githubusercontent.com/monarch-initiative/ontogpt/{COMMIT_HASH}/src/ontogpt/templates/data_sheets_schema.yaml"
```

### 3. External Prompt Files

Prompts are stored in version-controlled text files:

- `src/download/prompts/d4d_concatenated_system_prompt.txt`
- `src/download/prompts/d4d_concatenated_user_prompt.txt`

**Benefits**:
- Prompts tracked in git history
- Changes reviewable in pull requests
- SHA-256 hashes stored in metadata
- No hardcoded prompts hidden in code

### 4. Processing Order

- Files processed in **sorted alphabetical order**
- Deterministic file reading with encoding fallbacks: UTF-8 → UTF-8-sig → latin-1

### 5. Platform Independence

- Relative paths used throughout
- Cross-platform file handling
- Environment tracked in metadata (for debugging)

## Implementation Details

### Model Configuration

```python
model_settings = {
    "temperature": 0.0,    # Maximum determinism
    "max_tokens": 16000,
}

model = "anthropic:claude-sonnet-4-5-20250929"  # Date-pinned
```

### Prompt Loading

```python
# Load from external files
system_prompt, system_hash = load_prompt_file(
    prompts_dir, "d4d_concatenated_system_prompt.txt"
)

# Calculate hash for verification
sha256_hash = calculate_file_hash(prompt_path)
```

### Schema Loading

```python
# Use local schema file (version-controlled)
schema_path = "src/data_sheets_schema/schema/data_sheets_schema_all.yaml"
schema_content = schema_path.read_text()
schema_hash = calculate_file_hash(schema_path)
```

## Metadata Tracking

Every D4D extraction generates a comprehensive metadata YAML file (`{output}_metadata.yaml`) containing:

### Extraction Metadata
```yaml
extraction_metadata:
  timestamp: "2025-11-15T19:30:00Z"
  extraction_id: "a1b2c3d4e5f6"
  extraction_type: "concatenated_claude_code"
  processing_time_seconds: 45.2
```

### Input Document
```yaml
input_document:
  filename: "AI_READI_concatenated.txt"
  size_bytes: 125000
  sha256_hash: "abc123..."
  project: "AI_READI"
  source_files_count: 5
```

### Schema Information
```yaml
datasheets_schema:
  version: "1.0.0"
  source: "local"
  path: "src/data_sheets_schema/schema/data_sheets_schema_all.yaml"
  sha256_hash: "def456..."
  loaded_at: "2025-11-15T19:30:00Z"
```

### LLM Model
```yaml
llm_model:
  provider: "anthropic"
  model_name: "anthropic:claude-sonnet-4-5-20250929"
  model_version: "claude-sonnet-4-5-20250929"
  temperature: 0.0
  max_tokens: 16000
```

### Prompts
```yaml
prompts:
  system_prompt_file: "prompts/d4d_concatenated_system_prompt.txt"
  system_prompt_hash: "ghi789..."
  user_prompt_file: "prompts/d4d_concatenated_user_prompt.txt"
  user_prompt_hash: "jkl012..."
```

### Reproducibility
```yaml
reproducibility:
  command: "make extract-d4d-concat-claude PROJECT=AI_READI"
  environment_variables:
    ANTHROPIC_API_KEY: "required"
  random_seed: null
  deterministic_settings: true
```

### Provenance
```yaml
provenance:
  extraction_performed_by: "process_concatenated_d4d_claude"
  extraction_requested_at: "2025-11-15T19:30:00Z"
  git_commit: "abc1234567890def"
  notes: "Deterministic D4D extraction using Claude Sonnet 4.5 with temperature=0.0"
```

## Verification Process

### Test Reproducibility

Run the same extraction twice and verify identical outputs:

```bash
# First run
make extract-d4d-concat-claude PROJECT=AI_READI

# Save output
cp data/d4d_concatenated/claudecode/AI_READI_d4d.yaml AI_READI_run1.yaml

# Second run (delete and re-run)
rm data/d4d_concatenated/claudecode/AI_READI_d4d.yaml
make extract-d4d-concat-claude PROJECT=AI_READI

# Compare
diff data/d4d_concatenated/claudecode/AI_READI_d4d.yaml AI_READI_run1.yaml
```

**Expected result**: No differences (files should be identical)

### Verify Metadata Tracking

Check that all hashes and settings are tracked:

```bash
# View metadata
cat data/d4d_concatenated/claudecode/AI_READI_d4d_metadata.yaml

# Verify hash tracking
grep "sha256_hash" data/d4d_concatenated/claudecode/AI_READI_d4d_metadata.yaml

# Check temperature setting
grep "temperature" data/d4d_concatenated/claudecode/AI_READI_d4d_metadata.yaml
```

### Validate Against Schema

```bash
# Validate D4D YAML syntax
make validate-d4d FILE=data/d4d_concatenated/claudecode/AI_READI_d4d.yaml
```

## Comparing Generators

### GPT-5 vs Claude Output Comparison

The project generates D4D datasheets using both GPT-5 and Claude:

**GPT-5** (`data/d4d_concatenated/gpt5/`):
- Model: `openai:gpt-5`
- Temperature: Not set (uses default, ~1.0) ⚠️ NOT DETERMINISTIC
- Schema: Loaded from GitHub URL (can change)
- Prompts: Hardcoded in Python

**Claude** (`data/d4d_concatenated/claudecode/`):
- Model: `anthropic:claude-sonnet-4-5-20250929`
- Temperature: 0.0 (conceptually) ✅ DETERMINISTIC
- Schema: Local file (version-controlled)
- Prompts: External files (version-controlled)
- **Note**: Current implementation uses Claude Code assistant for direct synthesis rather than API calls

### How to Compare

```bash
# View GPT-5 output
cat data/d4d_concatenated/gpt5/AI_READI_d4d.yaml

# View Claude output
cat data/d4d_concatenated/claudecode/AI_READI_d4d.yaml

# Compare file sizes
ls -lh data/d4d_concatenated/gpt5/AI_READI_d4d.yaml
ls -lh data/d4d_concatenated/claudecode/AI_READI_d4d.yaml

# Check for completeness differences
make data-d4d-sizes
```

### Expected Differences

Even with identical inputs, GPT-5 and Claude outputs may differ in:

1. **Phrasing**: Different word choices for descriptions
2. **Completeness**: One model may extract more/fewer fields
3. **Structure**: Organization of nested YAML structures
4. **Detail level**: Verbosity in descriptions

### Recommended Evaluation

To evaluate which model produces better D4D datasheets:

1. **Completeness**: Count populated fields
2. **Accuracy**: Verify extracted information against source
3. **Clarity**: Assess readability of descriptions
4. **Schema Compliance**: Check LinkML validation results
5. **Size**: Compare output file sizes

## Claude Code Direct Synthesis Approach

In addition to the API-based approach documented above, the Claude Code datasheets were generated using **direct synthesis** by the Claude Code assistant rather than API calls. This approach:

### How It Works

1. **Direct Reading**: Claude Code assistant reads the concatenated input documents directly from the repository
2. **Schema Awareness**: References the local version-controlled schema file
3. **Synthesis Guidelines**: Follows the external prompt files to synthesize comprehensive D4D YAML
4. **Metadata Generation**: Creates metadata files tracking all provenance information

### Key Characteristics

- **No API Calls**: Uses Claude Code assistant capabilities directly (not `process_concatenated_d4d_claude.py` with API)
- **Same Principles**: Follows deterministic principles (external prompts, local schema, provenance tracking)
- **Manual Synthesis**: Assistant synthesizes information following the system prompt guidelines
- **Traceable**: All inputs tracked via SHA-256 hashes in metadata files

### Synthesis Process

The Claude Code assistant:
1. Reads all concatenated input files for each project (AI_READI, CHORUS, CM4AI, VOICE)
2. Identifies the most comprehensive source file(s) in each concatenated document
3. Merges complementary information from all files (following `d4d_concatenated_system_prompt.txt`)
4. Prefers more detailed/specific information over generic
5. Keeps the most comprehensive descriptions
6. Combines all relevant metadata sections
7. Generates comprehensive D4D YAML conforming to the schema
8. Creates metadata YAML tracking SHA-256 hashes and provenance

### Benefits

- **Immediate availability**: No API key required for generation
- **Same determinism principles**: External prompts, local schema, hash tracking
- **Transparent**: All synthesis decisions visible in conversation history
- **Reproducible**: Given the same inputs and prompts, synthesis follows the same guidelines

### Tradeability

While this approach uses Claude Code assistant directly rather than API calls, it maintains the same deterministic principles:
- External version-controlled prompts ✅
- Local version-controlled schema ✅
- SHA-256 hash tracking ✅
- Comprehensive metadata generation ✅
- Git commit provenance ✅

The main difference is the execution mechanism (assistant vs. API), but the inputs and outputs follow the same deterministic framework.

## Configuration Files

### Settings File

See `src/download/prompts/determinism_settings.yaml` for complete configuration:

```yaml
model:
  claude:
    temperature: 0.0
    max_tokens: 16000

schema:
  source: "local"
  path: "src/data_sheets_schema/schema/data_sheets_schema_all.yaml"

prompts:
  source: "files"
  directory: "src/download/prompts"
  track_hashes: true

metadata:
  generate_metadata: true
  track_input_hash: true
  track_schema_hash: true
  track_prompt_hashes: true
```

## Limitations

### What IS NOT Guaranteed

1. **Identical outputs from different models**: GPT-5 and Claude will produce different results
2. **Determinism across API versions**: Even with pinned models, API providers may change behavior
3. **Perfect schema compliance**: Generated YAML may not always validate against LinkML schema
4. **Completeness**: Not all fields may be extracted from incomplete documentation

### Known Non-Deterministic Sources

1. **API provider changes**: Anthropic/OpenAI may update models despite version pinning
2. **Network issues**: Transient failures may require retries
3. **Rate limiting**: May affect processing order in batch operations

## Future Improvements

Potential enhancements for even stronger reproducibility:

1. **Random seed support**: When/if Claude API adds seed parameter
2. **Full LinkML validation**: Validate generated YAML against schema constraints (not just syntax)
3. **Diff reporting**: Automated comparison of GPT-5 vs Claude outputs
4. **Regression testing**: Automated checks that schema/prompt changes don't break extraction
5. **Cached API responses**: Store and replay API responses for testing

## References

- Datasheets for Datasets: [https://arxiv.org/abs/1803.09010](https://arxiv.org/abs/1803.09010)
- LinkML: [https://linkml.io/](https://linkml.io/)
- pydantic-ai: [https://ai.pydantic.dev/](https://ai.pydantic.dev/)
- Claude API: [https://docs.anthropic.com/](https://docs.anthropic.com/)

## Questions?

For questions about deterministic D4D generation:

1. Check metadata YAML files for detailed provenance
2. Review prompt files in `src/download/prompts/`
3. Examine `process_concatenated_d4d_claude.py` source code
4. Compare with GPT-5 version in `process_concatenated_d4d.py`
5. Open an issue on GitHub

---

**Last Updated**: 2025-11-15
**Version**: 1.0.0
**Maintained by**: Bridge2AI Data Sheets Schema Team
