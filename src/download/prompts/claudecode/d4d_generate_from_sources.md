# D4D Generation from Source Documents

Generate new D4D datasheets using Claude Code directly from source documents.

## Overview

This approach does **not** use an API but rather relies on Claude Code and its environment in this repository to generate D4D records from input documents.

## Input Sources

### Concatenated Source Documents
Location: `data/preprocessed/concatenated/sources/`
- `AI_READI_sources_concatenated.txt`
- `CHORUS_sources_concatenated.txt`
- `CM4AI_sources_concatenated.txt`
- `VOICE_sources_concatenated.txt`

**Important**: Use the **source documents** (preprocessed text from original URLs), NOT the individual D4D YAML records. The concatenated files in `data/preprocessed/concatenated/sources/` contain the raw preprocessed content from websites, PDFs, and APIs.

### Individual Source Documents
Location: `data/preprocessed/individual/{PROJECT}/`
- Contains individual preprocessed files (`.txt`, `.json`, etc.) from each source URL

## Output Locations

### Concatenated D4Ds
Location: `data/d4d_concatenated/claudecode/`
- `{PROJECT}_d4d.yaml` - One comprehensive D4D per project

### Individual D4Ds
Location: `data/d4d_individual/claudecode/{PROJECT}/`
- `{source_file}_d4d.yaml` - One D4D per source document

## Schema Reference

Use the full merged schema: `src/data_sheets_schema/schema/data_sheets_schema_all.yaml`

Key points:
- Dataset class requires `id` and `name`
- Use renamed multivalued fields (e.g., `mechanism_details` not `description` for multivalued content)
- Validate output with: `poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_all.yaml -C Dataset <file>`

## Generation Process

1. **Read source document(s)** from `data/preprocessed/concatenated/sources/` or `data/preprocessed/individual/`
2. **Read schema** from `src/data_sheets_schema/schema/data_sheets_schema_all.yaml`
3. **Extract metadata** following D4D question categories:
   - Motivation (purposes, tasks, gaps addressed)
   - Composition (instances, subsets, sampling, anomalies)
   - Collection (acquisition, mechanisms, collectors, timeframes)
   - Preprocessing (strategies, cleaning, labeling)
   - Uses (existing, future impacts, discouraged/intended/prohibited)
   - Distribution (formats, dates, licenses)
   - Maintenance (maintainers, updates, versions)
   - Human Subjects (if applicable: IRB, consent, privacy)
4. **Generate valid YAML** conforming to schema
5. **Validate** before finalizing
6. **Save** to appropriate output location

## Deterministic Settings

- Temperature: 0.0 (maximum determinism)
- Follow schema strictly - only use defined fields
- Prefer `null` or omission for unknown values
- Use exact field names from schema

## Example Command

```
Generate a D4D datasheet for AI_READI from the source documents in
data/preprocessed/concatenated/sources/AI_READI_sources_concatenated.txt

Save output to: data/d4d_concatenated/claudecode/AI_READI_d4d.yaml
Validate against: src/data_sheets_schema/schema/data_sheets_schema_all.yaml
```
