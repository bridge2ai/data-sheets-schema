# D4D Assistant Generated Datasheets

This directory contains D4D (Datasheets for Datasets) YAML files created by the D4D Assistant via GitHub Actions.

## Purpose

- **Automated Extraction**: Datasheets generated from documentation URLs by the D4D Assistant
- **Review Staging**: All assistant-created datasheets saved here for human review before promotion
- **Separation of Concerns**: Keeps automated outputs separate from:
  - Manually curated examples (`src/data/examples/valid/`)
  - Project-specific extractions (`data/extracted_by_column/`)

## File Naming Convention

Files follow the pattern: `<dataset_name>_d4d.yaml`

Where `<dataset_name>` is:
- Lowercase
- Spaces replaced with underscores
- Derived from the dataset's official name or identifier

Examples:
- `cm4ai_d4d.yaml`
- `ai_readi_voice_d4d.yaml`
- `chorus_dataset_d4d.yaml`

## Workflow

1. **Creation**: D4D Assistant extracts metadata from documentation URLs
2. **Validation**: YAML validated against D4D schema before PR creation
3. **Review**: Human reviewers check accuracy and completeness
4. **Promotion**: After approval, files may be:
   - Moved to `src/data/examples/valid/` (if suitable as example)
   - Kept here as project documentation
   - Integrated into project-specific directories

## Related Documentation

- `.github/workflows/d4d_assistant_create.md` - Instructions for D4D Assistant
- `CLAUDE.md` - Project instructions and D4D guidance
- `src/data_sheets_schema/schema/data_sheets_schema_all.yaml` - Full D4D schema
