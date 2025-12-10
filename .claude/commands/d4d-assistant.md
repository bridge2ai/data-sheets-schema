Generate D4D datasheets using the Claude Code Assistant deterministic approach,
following the GitHub Actions workflow methodology with preprocessed source documents.

## Workflow Reference

First, read .github/workflows/d4d_assistant_create.md to understand the full workflow,
including schema loading, metadata extraction patterns, validation requirements, and
output formatting guidelines.

## Input Sources (Preprocessed Documents)

### Concatenated Sources (for comprehensive D4Ds - RECOMMENDED)
Location: data/preprocessed/concatenated/
- AI_READI_preprocessed.txt (245K, 13 source files)
- CHORUS_preprocessed.txt (70K, 6 source files)
- CM4AI_preprocessed.txt (161K, 8 source files)
- VOICE_preprocessed.txt (89K, 9 source files)

Use concatenated files to generate ONE comprehensive D4D per project.

### Individual Sources (for per-document D4Ds)
Location: data/preprocessed/individual/{PROJECT}/

Example files:
- AI_READI: `docs_aireadi_org_docs-2_row10.txt`, `fairhub_row12.json`, `e097449.full_row2.txt`
- CHORUS: `CHoRUS for Equitable AI.txt`, `aim-ahead-bridge2ai-for-clinical-care-informational-webinar_row7.txt`
- CM4AI: `dataverse_10.18130_V3_B35XWX_row13.txt`, `2024.05.21.589311v1.full.txt`
- VOICE: `physionet_b2ai-voice_1.1_row14.txt`, `B2AI-Voice_DTUA_2025.txt`

Use individual files to generate separate D4D per source document.

## Output Locations

- Concatenated: data/d4d_concatenated/claudecode_assistant/{PROJECT}_d4d.yaml
- Individual: data/d4d_individual/claudecode_assistant/{PROJECT}/{source_file}_d4d.yaml

## Generation Process

Follow the workflow in .github/workflows/d4d_assistant_create.md:

1. **Load the D4D Schema** (Step 1)
   - Read schema from src/data_sheets_schema/schema/data_sheets_schema_all.yaml
   - Understand all D4D classes, slots, and enums

2. **Gather Source Content** (Step 2 - adapted for preprocessed files)
   - Read preprocessed source documents using Read tool
   - Process all content to identify D4D-relevant information

3. **Extract Metadata** (Step 3)
   - Map information to appropriate D4D schema classes
   - Only populate fields you are confident about
   - Ensure required fields present (id, name)
   - Follow schema strictly for field names, types, structure
   - Use null or omit for missing information

4. **Generate Valid YAML** (Step 4)
   - Use proper YAML syntax with 2-space indentation
   - Include id and name as top-level Dataset fields
   - Structure nested objects per schema class definitions
   - Use lists where schema specifies multivalued: true

5. **Validate Schema Compliance** (Step 5a)
   - Run: poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_all.yaml -C Dataset <file>
   - Fix any validation errors before proceeding

6. **Validate Ontology Terms** (Step 5b)
   - Run: poetry run linkml-term-validator validate-data <file> --schema src/data_sheets_schema/schema/data_sheets_schema_all.yaml
   - Verifies enum values using ontology terms (DUO, AIO, etc.) are valid
   - See d4d-validator agent for detailed term validation guidance
   - Fix any term validation warnings

7. **Save** to output location

## File Header

```yaml
# D4D Datasheet for {PROJECT} Dataset
# Generation Method: Claude Code Deterministic ASSISTANT (in-session synthesis)
# Workflow: .github/workflows/d4d_assistant_create.md
# Source: data/preprocessed/concatenated/{PROJECT}_preprocessed.txt
# Schema: src/data_sheets_schema/schema/data_sheets_schema_all.yaml
# Temperature: 0.0
# Generated: {DATE}
```

## Field Population Rules

- Required fields: MUST be populated (id, name)
- Optional fields: Only populate if information is explicitly available
- Multivalued fields: Use YAML list syntax
- Enum fields: Only use values defined in schema enums
- Dates: Use ISO 8601 format (YYYY-MM-DD)
- DataSubset inherits from Dataset (requires id field)

## Validation

### Schema Validation (Required)
```bash
poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_all.yaml -C Dataset <file>
```

### Ontology Term Validation (Required)
```bash
poetry run linkml-term-validator validate-data <file> --schema src/data_sheets_schema/schema/data_sheets_schema_all.yaml
```

All D4Ds must pass both validations before completion.
For detailed validation guidance, see the `d4d-validator` agent.
