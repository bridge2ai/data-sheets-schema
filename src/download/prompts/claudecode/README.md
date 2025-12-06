# Claude Code Deterministic Assistant Prompts

This directory contains instruction files for the D4D Deterministic Assistant using Claude Code with temperature=0.0 settings for reproducible D4D datasheet generation.

## Instruction Files

- **`d4d_deterministic_create.md`** - Instructions for creating new D4D datasheets
- **`d4d_deterministic_edit.md`** - Instructions for editing existing D4D datasheets

These files guide the Claude Code Deterministic Assistant through workflows for metadata extraction, YAML generation, validation, and file management.

## Key Features

### Deterministic Settings
- Temperature: 0.0 (maximum determinism)
- Model: Date-pinned Claude model version
- Schema: Local version-controlled file
- Prompts: External version-controlled files

### Output Location
All Claude Code-generated D4D datasheets are saved to:
```
data/d4d_concatenated/claudecode/
```

### Metadata Tracking
Each extraction generates a metadata record documenting:
- Input sources (URLs, files)
- Schema version used
- Model settings
- Timestamps
- SHA-256 hashes for reproducibility

## Usage

### Creating a New Datasheet
1. Provide URLs or content describing the dataset
2. Claude Code follows `d4d_deterministic_create.md` instructions
3. Extracts metadata and generates YAML
4. Validates against D4D schema
5. Saves to `data/d4d_concatenated/claudecode/`

### Editing an Existing Datasheet
1. Specify which datasheet to edit
2. Claude Code follows `d4d_deterministic_edit.md` instructions
3. Makes requested changes
4. Validates modified YAML
5. Updates the file

## Comparison with Other Approaches

| Approach | Location | Temperature | Use Case |
|----------|----------|-------------|----------|
| Claude Code Deterministic | `claudecode/` | 0.0 | Reproducible extraction |
| GPT-5 Assistant | `gpt5/` | Default | Alternative LLM |
| GitHub Actions Assistant | `.github/workflows/` | Default | Automated via issues |
| Curated | `curated/` | N/A | Manual curation |

## Related Files

- **Schema**: `src/data_sheets_schema/schema/data_sheets_schema_all.yaml`
- **Validation**: `make validate-d4d FILE=<file>`
- **HTML Preview**: `src/html/human_readable_renderer.py`
- **Determinism Documentation**: `notes/DETERMINISM.md`
