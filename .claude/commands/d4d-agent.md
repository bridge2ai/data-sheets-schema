Generate D4D datasheets using the Claude Code Agent deterministic approach.

## Task Overview

Generate comprehensive D4D datasheets for all Bridge2AI projects using the Task tool
with specialized agents for parallel processing.

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

- Concatenated: data/d4d_concatenated/claudecode_agent/{PROJECT}_d4d.yaml
- Individual: data/d4d_individual/claudecode_agent/{PROJECT}/{source_file}_d4d.yaml

## Extraction Checklist

Extract these key elements from source documents:

- **Dataset identity**: id, name, title, and comprehensive description
- **Creators and contributors**: names, affiliations, roles (CRediT taxonomy), contact information
- **Purpose and intended uses**: primary objectives, motivations, and recommended applications
- **Tasks and gaps addressed**: specific research questions, problems solved, unmet needs
- **Data composition**: types of instances, relationships, structural details, splits
- **Collection methodology**: mechanisms, sampling strategies, timeframes, data sources
- **Collection team**: who collected the data, affiliations, roles
- **Preprocessing and cleaning**: steps taken, software/tools used, raw data availability
- **Distribution information**: file formats, data structure, access methods, download locations
- **Licensing and terms of use**: copyright, license type, restrictions, compliance requirements
- **Maintenance information**: update schedule, versioning, retention policies, contact
- **Access requirements**: authentication, approval processes, costs, barriers
- **Funding and grants**: sponsors, grant identifiers, acknowledgments
- **Ethics and human subjects**: IRB approval, consent, privacy protections, vulnerable populations
- **Recommended and discouraged uses**: appropriate and inappropriate applications
- **Known limitations**: biases, noise, missingness, quality issues, caveats
- **Distribution formats**: file types, compression, structure, documentation

## Generation Process

For each project (AI_READI, CM4AI, VOICE, CHORUS):

1. **Launch Task agents in parallel** using Task tool with subagent_type='general-purpose'
2. **Read source documents** from preprocessed locations
3. **Read schema** from src/data_sheets_schema/schema/data_sheets_schema_all.yaml
4. **Extract metadata** using the checklist above
5. **Generate valid YAML** conforming to schema
6. **Validate schema compliance** with: poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_all.yaml -C Dataset <file>
7. **Validate ontology terms** with: poetry run linkml-term-validator validate-data <file> --schema src/data_sheets_schema/schema/data_sheets_schema_all.yaml
8. **Save** to output location

## Merging Multiple Sources

When multiple sources describe the same dataset:
1. Merge complementary information from all sources
2. Prefer more detailed and specific information over generic descriptions
3. Resolve conflicts by choosing the most authoritative or recent source

## File Header

```yaml
# D4D Datasheet for {PROJECT} Dataset
# Generation Method: Claude Code Agent Deterministic
# Source: data/preprocessed/concatenated/{PROJECT}_preprocessed.txt
# Schema: src/data_sheets_schema/schema/data_sheets_schema_all.yaml
# Temperature: 0.0
# Generated: {DATE}
```

## Settings

- Temperature: 0.0
- Follow schema strictly - only use defined fields
- Prefer null or omission for unknown values
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
