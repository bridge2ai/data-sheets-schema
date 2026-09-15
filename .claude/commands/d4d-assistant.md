Generate D4D datasheets in the current assistant session, following the GitHub
Actions workflow methodology with preprocessed source documents. This mode can
run under Claude Code or Codex/GPT; record the actual runtime and model.

> Note: this command produces FULL D4D records only. For paired full + D4D-core
> generation, use `/d4d-full-core` (two ordered generation phases followed by a
> source/provenance audit and strict schema-derived pair reconciliation).

Before generation, read and enforce
`.claude/agents/d4d-provenance-guard.md`. In particular, do not read or borrow
facts from any prior generated D4D.

## Workflow Reference

First, read .github/workflows/d4d_assistant_create.md to understand the full workflow,
including schema loading, metadata extraction patterns, validation requirements, and
output formatting guidelines.

## Input Sources (Preprocessed Documents)

### Concatenated Sources (for comprehensive D4Ds - RECOMMENDED)
Location: data/preprocessed/concatenated/
- `{PROJECT}_preprocessed.txt`, one per project the selected manifest declares
  (`d4d download list-projects`; `d4d utils status` lists them with sizes)

The source inventory and document order are defined in the selected source
manifest (`data/preprocessed/source_manifest.yaml` by default). Use the
concatenated files to generate ONE comprehensive D4D per project.

### Individual Sources (for per-document D4Ds)
Location: data/preprocessed/individual/{PROJECT}/

One `{source}_row{N}.txt` per source the manifest declares for the project.
Use individual files to generate separate D4D per source document.

## Output Locations

- Concatenated: data/d4d_concatenated/claudecode_assistant/{VERSION}/{PROJECT}_d4d.yaml
- Individual: data/d4d_individual/claudecode_assistant/{VERSION}/{PROJECT}/{source_file}_d4d.yaml

Use a `{YYYY-MM-DD}_{model}` version label and never overwrite a prior version
directory.

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
   - Run: poetry run linkml-term-validator validate-data <file> --schema src/data_sheets_schema/schema/data_sheets_schema_all.yaml --target-class Dataset
   - Verifies enum values using ontology terms (DUO, AIO, etc.) are valid
   - See d4d-validator agent for detailed term validation guidance
   - Fix any term validation warnings

7. **Save** to output location

## File Header

```yaml
# D4D Datasheet for {PROJECT} Dataset
# Generation Method: schema-grounded assistant, in-session synthesis
# Agent runtime: {Claude Code|Codex CLI}
# Provider: {Anthropic|OpenAI}
# Model: {MODEL}
# Workflow: .github/workflows/d4d_assistant_create.md
# Source bundle: data/preprocessed/concatenated/{PROJECT}_preprocessed.txt
# Source manifest: data/preprocessed/source_manifest.yaml
# Schema: src/data_sheets_schema/schema/data_sheets_schema_all.yaml
# Prior D4D factual reuse: prohibited
# Temperature: unknown (not observed from the agent runtime)
# Generated: {DATE}
```

## Field Population Rules

- Required fields: MUST be populated (id, name)
- Optional fields: Only populate if information is explicitly available
- Multivalued fields: Use YAML list syntax
- Enum fields: Only use values defined in schema enums
- Dates: Use ISO 8601 format (YYYY-MM-DD)
- DataSubset inherits from Dataset (requires id field)
- Older generated full/core D4D records are forbidden factual inputs

## Validation

### Schema Validation (Required)
```bash
poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_all.yaml -C Dataset <file>
```

### Ontology Term Validation (Required)
```bash
poetry run linkml-term-validator validate-data <file> \
  --schema src/data_sheets_schema/schema/data_sheets_schema_all.yaml \
  --target-class Dataset
```

All D4Ds must pass both validations before completion.
For detailed validation guidance, see the `d4d-validator` agent.
