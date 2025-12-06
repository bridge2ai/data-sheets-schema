# GPT-5 Assistant Prompts

This directory contains instruction files for the D4D GPT-5 Assistant for D4D datasheet generation using OpenAI's GPT-5 model.

## Instruction Files

- **`d4d_assistant_create.md`** - Instructions for creating new D4D datasheets
- **`d4d_assistant_edit.md`** - Instructions for editing existing D4D datasheets

These files guide the GPT-5 Assistant through workflows for metadata extraction, YAML generation, validation, and file management.

## Key Features

### Model Configuration
- Model: GPT-5 (OpenAI API)
- Temperature: Default (configurable)
- Schema: Local version-controlled file

### Output Location
All GPT-5-generated D4D datasheets are saved to:
```
data/d4d_concatenated/gpt5/
```

### Available Tools
- **WebSearch**: Search for dataset documentation
- **WebFetch**: Fetch content from URLs
- **Europe PMC**: Search academic literature

## Usage

### Creating a New Datasheet
1. Provide URLs or content describing the dataset
2. GPT-5 follows `d4d_assistant_create.md` instructions
3. Extracts metadata and generates YAML
4. Validates against D4D schema
5. Saves to `data/d4d_concatenated/gpt5/`

### Editing an Existing Datasheet
1. Specify which datasheet to edit
2. GPT-5 follows `d4d_assistant_edit.md` instructions
3. Makes requested changes
4. Validates modified YAML
5. Updates the file

## Comparison with Other Approaches

| Approach | Location | Model | Use Case |
|----------|----------|-------|----------|
| GPT-5 Assistant | `gpt5/` | GPT-5 | Alternative LLM |
| Claude Code Deterministic | `claudecode/` | Claude | Reproducible extraction |
| GitHub Actions Assistant | `.github/workflows/` | Claude | Automated via issues |
| Curated | `curated/` | N/A | Manual curation |

## Related Files

- **Schema**: `src/data_sheets_schema/schema/data_sheets_schema_all.yaml`
- **Validation**: `make validate-d4d FILE=<file>`
- **HTML Preview**: `src/html/human_readable_renderer.py`
- **API Script**: `src/schema_extract/process_d4d_claude_API_temp0.py` (reference implementation)

## Requirements

- `OPENAI_API_KEY` environment variable must be set
- Python packages: `openai`, `pyyaml`
