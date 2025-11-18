# Deterministic D4D Extraction Script

## Overview

`process_d4d_deterministic.py` is a standalone Python script for generating Datasheet for Datasets (D4D) YAML files from concatenated documents using the Claude Code framework with deterministic settings.

This script implements the automated approach described in `notes/DETERMINISM.md`, providing reproducible metadata extraction via the Anthropic API.

## Features

### Automation
- **Single Command Execution**: Process all projects with `--all` flag
- **Minimal Dependencies**: Only requires `anthropic` and `pyyaml` packages (no aurelian submodule needed)
- **Comprehensive Metadata**: Automatically generates metadata files with SHA-256 hashes
- **Batch Processing**: Process all projects (AI_READI, CHORUS, CM4AI, VOICE) in one run
- **Error Handling**: Graceful handling of encoding issues and API errors
- **Progress Tracking**: Real-time progress indicators and status updates

### Deterministic Settings
- **Temperature**: 0.0 (maximum determinism, eliminates randomness)
- **Model**: claude-sonnet-4-5-20250929 (date-pinned to prevent model updates)
- **Schema**: Local version-controlled file (`src/data_sheets_schema/schema/data_sheets_schema_all.yaml`)
- **Prompts**: External version-controlled files (`src/download/prompts/d4d_concatenated_*.txt`)
- **Provenance**: SHA-256 hashes of all inputs stored in metadata

## Usage

### Prerequisites

```bash
# 1. Install required Python packages
pip install anthropic pyyaml

# 2. Set API key
export ANTHROPIC_API_KEY='your-anthropic-api-key'

# 3. Ensure input files exist (run preprocessing if needed)
make concat-extracted
```

### Basic Usage

```bash
# Process all projects
python3 src/download/process_d4d_deterministic.py --all

# Process single project
python3 src/download/process_d4d_deterministic.py \
    -i data/preprocessed/concatenated/AI_READI_concatenated.txt \
    -o data/d4d_concatenated/claudecode/AI_READI_d4d.yaml \
    -p AI_READI

# Using make targets (recommended)
make extract-d4d-concat-claude PROJECT=AI_READI
make extract-d4d-concat-all-claude
```

### Command-Line Arguments

```
-i, --input INPUT     Input concatenated file path
-o, --output OUTPUT   Output D4D YAML file path
-p, --project PROJECT Project name (AI_READI, CHORUS, CM4AI, VOICE)
--all                 Process all projects automatically
```

## Output Files

For each project, the script generates two files:

1. **D4D YAML** (`{PROJECT}_d4d.yaml`)
   - Complete dataset metadata in D4D format
   - Valid LinkML YAML conforming to schema
   - Synthesized from concatenated input documents

2. **Metadata YAML** (`{PROJECT}_d4d_metadata.yaml`)
   - Generation timestamp and git commit
   - Model settings (temperature, max_tokens, model version)
   - SHA-256 hashes of all inputs (concatenated file, schema, prompts)
   - API usage statistics (tokens, elapsed time)
   - Reproducibility command

### Example Metadata File

```yaml
generation_info:
  tool: process_d4d_deterministic.py
  timestamp: '2025-11-17T10:30:45.123456'
  git_commit: abc123def456...

model_settings:
  model: claude-sonnet-4-5-20250929
  temperature: 0.0
  max_tokens: 16000
  framework: anthropic-python-sdk

input_files:
  concatenated_input:
    path: data/preprocessed/concatenated/AI_READI_concatenated.txt
    sha256: 74238db95ebc8c3344954d65823f68e2ddce382efa9ffbd500e69d68cc475116
    size_chars: 16678
  schema:
    path: src/data_sheets_schema/schema/data_sheets_schema_all.yaml
    sha256: e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855
  system_prompt:
    path: src/download/prompts/d4d_concatenated_system_prompt.txt
    sha256: ...
  user_prompt_template:
    path: src/download/prompts/d4d_concatenated_user_prompt.txt
    sha256: ...

output_info:
  project: AI_READI
  valid_yaml: true
  size_chars: 10403
  output_sha256: ...

api_usage:
  input_tokens: 45000
  output_tokens: 2500
  total_tokens: 47500
  elapsed_seconds: 78.7

reproducibility:
  command: python src/download/process_d4d_deterministic.py -i data/preprocessed/concatenated/AI_READI_concatenated.txt -o data/d4d_concatenated/claudecode/AI_READI_d4d.yaml -p AI_READI
  notes: Requires ANTHROPIC_API_KEY environment variable. Temperature=0.0 ensures deterministic output.
```

## Limitations

### 1. API Key Required
- **Limitation**: Requires `ANTHROPIC_API_KEY` environment variable
- **Impact**: Cannot run without API access
- **Workaround**: Use Claude Code assistant direct synthesis approach (see Alternative Approach below)

### 2. API Costs
- **Limitation**: Each run incurs Anthropic API charges
- **Impact**: Processing all 4 projects costs ~$5-10 (approximate, based on current pricing)
- **Estimation**: Typical usage per project:
  - Input: ~15K-30K tokens (concatenated docs + schema + prompts)
  - Output: ~2K-5K tokens (D4D YAML)
  - Cost: ~$1-3 per project with Claude Sonnet 4.5
- **Workaround**: Use direct synthesis for development/testing, API for production runs

### 3. Network Connectivity
- **Limitation**: Requires internet connection to reach Anthropic API
- **Impact**: Cannot run offline
- **Workaround**: Use cached results or direct synthesis approach

### 4. Rate Limits
- **Limitation**: Anthropic API has rate limits (typically 50 requests/min, 40K tokens/min)
- **Impact**: Batch processing may need throttling
- **Current Status**: Script processes sequentially, unlikely to hit limits with 4 projects
- **Workaround**: Script handles rate limit errors gracefully; retry after cooldown

### 5. Model Availability
- **Limitation**: Relies on specific model version (claude-sonnet-4-5-20250929)
- **Impact**: If model is deprecated, script needs updating
- **Mitigation**: Date-pinned models typically available for 6+ months
- **Workaround**: Update MODEL_NAME constant if model changes

### 6. Non-Interactive
- **Limitation**: Cannot ask clarifying questions during extraction
- **Impact**: May produce less comprehensive metadata than interactive assistant
- **Trade-off**: Automation and reproducibility vs. human oversight
- **Workaround**: Use direct synthesis with Claude Code assistant for complex cases

### 7. Fixed Prompts
- **Limitation**: Uses static prompts from external files
- **Impact**: Cannot dynamically adjust extraction strategy per project
- **Benefit**: Ensures reproducibility and consistency
- **Workaround**: Edit prompt files if different approach needed (version controlled)

### 8. YAML-Only Output
- **Limitation**: Only generates YAML output (not JSON, RDF, etc.)
- **Impact**: Additional conversion needed for other formats
- **Workaround**: Use LinkML conversion tools: `linkml-convert -s schema.yaml input.yaml -o output.json`

## Alternative Approach: Direct Synthesis

For scenarios where API access is limited or unavailable, use **Claude Code assistant direct synthesis**:

### Process
1. Claude Code assistant reads concatenated input files directly from repository
2. Follows the same external prompt files (`src/download/prompts/d4d_concatenated_*.txt`)
3. References the same local schema file
4. Synthesizes D4D YAML following deterministic guidelines
5. Generates metadata files with SHA-256 hashes

### Benefits
- **No API Key**: Doesn't require ANTHROPIC_API_KEY
- **No API Costs**: Free to run (uses Claude Code subscription)
- **Offline Capable**: Can work with local files
- **Interactive**: Can ask clarifying questions
- **Same Principles**: Follows same deterministic framework

### Trade-offs
- **Manual Process**: Requires interactive Claude Code session
- **Less Automated**: Cannot run as single command
- **Documentation Required**: Must document synthesis decisions in conversation

### When to Use Each Approach

| Criterion | API-Based (`process_d4d_deterministic.py`) | Direct Synthesis (Claude Code) |
|-----------|-------------------------------------------|-------------------------------|
| **Reproducibility** | ✅ Fully automated, identical results | ✅ Same inputs/prompts, manual execution |
| **Cost** | ❌ API charges per run | ✅ Free with subscription |
| **Speed** | ✅ Automated batch processing | ⚠️ Manual per-project |
| **API Access** | ❌ Requires ANTHROPIC_API_KEY | ✅ No API key needed |
| **Offline** | ❌ Requires internet | ✅ Can work offline |
| **Interactivity** | ❌ Non-interactive | ✅ Interactive |
| **Documentation** | ✅ Auto-generated metadata | ⚠️ Manual documentation |
| **CI/CD Integration** | ✅ Easy to automate | ❌ Manual process |

**Recommendation**:
- **Production/CI**: Use API-based script for reproducible automated runs
- **Development/Exploration**: Use direct synthesis for iterative improvement
- **No API Access**: Use direct synthesis as complete alternative

## How It Works

### Processing Flow

1. **Load Configuration**
   - Load external prompt files from `src/download/prompts/`
   - Load local schema from `src/data_sheets_schema/schema/data_sheets_schema_all.yaml`
   - Compute SHA-256 hashes of all inputs

2. **Read Input**
   - Read concatenated document with encoding fallbacks (UTF-8 → UTF-8-sig → latin-1)
   - Compute input file SHA-256 hash

3. **Prepare Prompts**
   - Insert schema into system prompt template
   - Insert project name, filename, and content into user prompt template
   - Compute prompt hashes for metadata

4. **Call Claude API**
   - Initialize Anthropic client with API key
   - Call with deterministic settings:
     - Model: claude-sonnet-4-5-20250929
     - Temperature: 0.0
     - Max tokens: 16000
   - Track API usage (input/output tokens, elapsed time)

5. **Process Response**
   - Extract YAML from response (handle markdown code blocks)
   - Validate YAML syntax
   - Save validated YAML to output file

6. **Generate Metadata**
   - Collect all provenance information
   - Create comprehensive metadata dictionary
   - Save metadata to separate YAML file

7. **Report Status**
   - Display progress indicators
   - Show token usage and costs
   - Report success/failure for each project

### Key Implementation Details

- **Encoding Fallback**: Tries UTF-8, UTF-8-sig, then latin-1 for file reading
- **YAML Extraction**: Handles both `yaml` and unmarked code blocks
- **Hash Computation**: SHA-256 used for all file integrity checking
- **Git Integration**: Captures current commit hash for reproducibility
- **Error Handling**: Graceful handling of API errors with informative messages

## Integration with Makefile

The script integrates with project Makefile for convenient execution:

```makefile
# Single project
extract-d4d-concat-claude:
    @python3 src/download/process_d4d_deterministic.py \
        -i $(PREPROCESSED_CONCAT_DIR)/$(PROJECT)_concatenated.txt \
        -o $(D4D_CONCAT_DIR)/claudecode/$(PROJECT)_d4d.yaml \
        -p $(PROJECT)

# All projects
extract-d4d-concat-all-claude:
    @python3 src/download/process_d4d_deterministic.py --all
```

Usage:
```bash
make extract-d4d-concat-claude PROJECT=AI_READI
make extract-d4d-concat-all-claude
```

## Comparison with Other Approaches

### vs. Aurelian-based Script (`process_concatenated_d4d_claude.py`)
- **✅ Standalone**: No aurelian submodule dependency
- **✅ Simpler**: Fewer dependencies (just anthropic + pyyaml)
- **✅ Maintainable**: All code in single file
- **✅ Documented**: Comprehensive inline documentation
- **=** Same API (Anthropic)
- **=** Same deterministic settings

### vs. GPT-5 Extraction (`process_concatenated_d4d.py`)
- **Different Model**: Claude Sonnet 4.5 vs GPT-5
- **Same Purpose**: Both extract D4D from concatenated docs
- **Same Determinism**: Both use temperature=0.0
- **Different API**: Anthropic vs OpenAI

### vs. Direct Claude Code Assistant Synthesis
- **More Automated**: Single command vs interactive session
- **API-Based**: Requires ANTHROPIC_API_KEY vs no key needed
- **Costs Money**: API charges vs free
- **Non-Interactive**: Cannot ask questions vs interactive
- **Easier CI/CD**: Scriptable vs manual

## Troubleshooting

### Error: ANTHROPIC_API_KEY not set
```bash
export ANTHROPIC_API_KEY='your-key-here'
```

### Error: Input file not found
```bash
# Generate concatenated files first
make concat-extracted PROJECT=AI_READI
```

### Error: ModuleNotFoundError: No module named 'anthropic'
```bash
pip install anthropic pyyaml
```

### Error: API rate limit exceeded
- Wait 60 seconds and retry
- For batch processing, script handles this automatically

### Error: Invalid YAML generated
- Check debug output saved to `*_debug.txt`
- Review Claude's response for formatting issues
- May need to adjust prompts in `src/download/prompts/`

## Future Enhancements

Potential improvements for maximum automation:

1. **Retry Logic**: Automatic retry with exponential backoff for transient errors
2. **Parallel Processing**: Process multiple projects concurrently (within rate limits)
3. **Caching**: Cache API responses to avoid duplicate calls
4. **Diff Mode**: Show differences from existing files before overwriting
5. **Validation Integration**: Automatically validate with LinkML before saving
6. **Cost Estimation**: Show estimated API costs before running
7. **Progress Bar**: Visual progress indicator for long-running operations
8. **Streaming Output**: Display generated YAML as it's created

## References

- **DETERMINISM.md** (`notes/DETERMINISM.md`): Complete documentation of deterministic approach
- **External Prompts**: `src/download/prompts/d4d_concatenated_*.txt`
- **Schema**: `src/data_sheets_schema/schema/data_sheets_schema_all.yaml`
- **Anthropic API Docs**: https://docs.anthropic.com/
- **LinkML Documentation**: https://linkml.io/

## License

Same as parent repository (see top-level LICENSE file).

## Support

For issues or questions:
1. Check this README and `notes/DETERMINISM.md`
2. Review script help: `python3 src/download/process_d4d_deterministic.py --help`
3. Open GitHub issue with error details and metadata file
