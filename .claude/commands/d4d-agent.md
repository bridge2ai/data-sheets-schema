Generate full D4D datasheets using a schema-grounded, model-neutral agentic
approach.

> **Paired full + core generation**: this command produces FULL D4D records only.
> When the goal is a full D4D **and** a D4D-core record for a project, use
> `/d4d-full-core` instead. It runs this method in one fresh generation pass,
> then starts a second pass that derives core from the input docs + completed
> full D4D, audits both against current sources in Phase 3, and performs strict
> schema-derived full/core reconciliation in Phase 4.

Before generation, read and enforce **both**:

- `.claude/agents/d4d-provenance-guard.md` — the evidence boundary;
- `.claude/commands/d4d-uniform-rules.md` — the uniform decision rules that
  apply to every condition, every project and both runtimes.

The rules are not restated here. Until #563 they lived only in
`d4d-full-core.md`, so a run entered through this command — which is a complete
standalone method for full records — followed none of them: not
omission-over-inference, not identifier-from-evidence, not CURIE form. Every
record in the corpus happens to have been generated through `/d4d-full-core`,
which reads them and delegates extraction here, so nothing on disk is affected.
The gap was in what this file permitted, not in what it produced.

## Task Overview

Generate comprehensive D4D datasheets for all Bridge2AI projects using fresh
project-agent contexts. The workflow is portable across Claude Code and
Codex/GPT; provider-specific execution details must not change the evidence
boundary or output semantics.

## Input Sources (Preprocessed Documents)

### Concatenated Sources (for comprehensive D4Ds - RECOMMENDED)
Location: data/preprocessed/concatenated/
- AI_READI_preprocessed.txt (238K, 7 source files)
- CHORUS_preprocessed.txt (35K, 4 source files)
- CM4AI_preprocessed.txt (287K, 9 source files)
- VOICE_preprocessed.txt (295K, 9 source files)

The source inventory and document order are defined in
`data/preprocessed/source_manifest.yaml`. Use the concatenated files to generate
ONE comprehensive D4D per project.

### Individual Sources (for per-document D4Ds)
Location: data/preprocessed/individual/{PROJECT}/

Example files:
- AI_READI: `bmjopen-2024-097449_row2.txt`, `fairhub_dataset_2_row12.txt`, `gdrive_1rJsa5kySlBRRNhsO_WY7N3bfSKtqDi-Q_row13.txt`
- CHORUS: `reporter_nih_gov_project-details-10472824_row7.txt`, `bridge2ai-for-clinical-care-informational-webinar-cohort-2_row9.txt`, `chorus4ai_org_row11.txt`, `github_chorus_ai_overview_2025-11-14.txt`
- CM4AI: `www_nature_com_articles-s41586-025-08878-3_row2.txt`, `cm4ai_org_data-releases_row11.txt`, `dataverse_10.18130_V3_B35XWX_row16.txt`, `dataverse_10.18130_V3_F3TD5R_row19.txt`, `dataverse_10.18130_V3_K7TGEM_row16.txt`
- VOICE: `physionet_b2ai-voice_1.1_row17.txt`, `gdrive_1z4zZ_Z_Jb017IoVZn5btJnSLKdEOHZPA_row14.txt`, `github_eipm_bridge2ai-docs_README_row22.txt`

Use individual files to generate separate D4D per source document.

## Output Locations

- Concatenated: data/d4d_concatenated/claudecode_agent/{VERSION}/{PROJECT}_d4d.yaml
- Individual: data/d4d_individual/claudecode_agent/{VERSION}/{PROJECT}/{source_file}_d4d.yaml

Use a `{YYYY-MM-DD}_{model}` version label and never overwrite a prior version
directory.

The `claudecode_agent` path is retained as a repository convention and does not
assert which provider generated a particular version. Record the runtime,
provider, and model in the version label and YAML header.

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

1. **Launch one fresh agent per project.**
   - Claude Code: use a fresh Task/subagent context and pass the exact source,
     schema, and target paths.
   - Codex/GPT: use one fresh `codex exec` invocation per project and pass the
     exact source, schema, and target paths.
   - These are outer-orchestrator instructions. An agent already running in its
     fresh project context performs the work directly and does not launch a
     nested copy of its own runtime.
   - Do not pass older generated D4D content through the parent conversation or
     prompt.

2. **Build and constrain structure exclusively from the schema**:
   - Do not read prior full or core D4D YAML as a template.
   - Resolve every top-level and nested slot through the `Dataset` class,
     inherited classes, slot ranges, and `slot_usage`.
   - Derive exact names, ranges, required fields, cardinality, inlining,
     enums, and nested-object shapes from the schema.
   - Do not assume that similarly named classes have the same shape.

3. **Read schema and extract field definitions**:
   - Path: `src/data_sheets_schema/schema/data_sheets_schema_all.yaml`
   - Start at class `Dataset`; follow `is_a`, `mixins`, `slots`,
     `attributes`, `slot_usage`, and each slot's class or enum range.
   - For each class used, extract exact field names and constraints.
   - **Critical**: Do NOT invent field names or object shapes based on
     semantics.

4. **Schema `d4d:docExample` annotations are illustrations, NOT defaults**: The schema YAML may contain `annotations: {"d4d:docExample": "..."}` on fields. These are documentation only — do NOT copy them into D4D records. All values in generated D4D YAML must come from the source documents.

5. **Do not use hard-coded object templates**:
   - A slot name that sounds plausible is invalid unless the schema declares it
     for the class.
   - A nested object must contain only slots allowed by its schema range.
   - If an older record or documentation example conflicts with the schema, the
     schema wins.

6. **Read only allowed factual sources**:
   - Current concatenated source bundle for the project
   - Current `data/preprocessed/source_manifest.yaml`
   - Never read older D4D YAML during full generation
   - A historical source document is allowed only if the current manifest
     selects it

7. **Extract metadata** using the checklist above

8. **Generate valid YAML** conforming to schema:
   - Use ONLY field names found in schema
   - Include every field required by the applicable class
   - Respect scalar versus multivalued and inlined-object constraints
   - Follow schema ranges for nested structures and enum values
   - **Slot-filling order** (same contract as the API pipeline's phase
     instructions): a class's structured slots first — `name`, `id`,
     `affiliations`, `grants` and kin must not sit empty while their content
     sits in prose — then `description` as the default home for narrative,
     then `notes` only for content `description` cannot hold. Evidence
     commentary (source conflicts, what a value was transcribed from,
     questions the sources leave unanswered) goes in `source_caveats`,
     never in `notes`. Never restate a sibling slot's value, and never
     invent a key.
   - **Shape check before writing**: a value must match its slot's range —
     no prose where the schema requires a list, no enum values the schema
     does not define, no commentary embedded inside a name, identifier or
     affiliation value.

9. **REQUIRED validation** (NON-SKIPPABLE):
   ```bash
   poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_all.yaml -C Dataset <file>
   ```
   - If validation fails: analyze errors, fix field names, re-validate
   - DO NOT proceed without passing validation

10. **Validate ontology terms**:
   ```bash
   poetry run linkml-term-validator validate-data <file> \
     --schema src/data_sheets_schema/schema/data_sheets_schema_all.yaml \
     --target-class Dataset
   ```

11. **Verify output**:
    - Do not use line count as a completeness or quality metric
    - Confirm every source-supported applicable schema section is populated
    - Omit unsupported optional fields instead of adding filler to reach a size target
    - Verify no invented field names used

12. **Save** to output location

13. **Run the provenance audit** in
    `.claude/agents/d4d-provenance-guard.md`.

## Merging Multiple Sources

When multiple sources describe the same dataset:
1. Merge complementary information from all sources
2. Prefer more detailed and specific information over generic descriptions
3. Resolve conflicts using authority and recency metadata within the current
   source bundle
4. Never consult an older generated D4D to fill a gap or break a tie

## Runtime Cases

### Claude Code

- Use Task/subagents for isolated project contexts.
- Use the selected Claude model and record its exact name.
- Treat any old D4D facts visible in the parent conversation as forbidden.

### Codex / GPT

- The outer orchestrator uses a fresh `codex exec` context for each project.
- A project worker already inside that context executes directly; it does not
  invoke another `codex exec`.
- Record the GPT model, reasoning effort, and service mode.
- Do not search D4D output directories for examples or prior facts.

## File Header

```yaml
# D4D Datasheet for {PROJECT} Dataset
# Generation Method: schema-grounded agentic, phase 1
# Agent runtime: {Claude Code|Codex CLI}
# Provider: {Anthropic|OpenAI}
# Model: {MODEL}
# Reasoning effort: {EFFORT}
# Mode: {MODE}
# Source bundle: data/preprocessed/concatenated/{PROJECT}_preprocessed.txt
# Source manifest: data/preprocessed/source_manifest.yaml
# Schema: src/data_sheets_schema/schema/data_sheets_schema_all.yaml
# Prior D4D factual reuse: prohibited
# Temperature: 0.0
# Generated: {DATE}
```

## Settings

- Temperature: 0.0
- Follow schema strictly - only use defined fields
- Prefer null or omission for unknown values
- DataSubset inherits from Dataset (requires id field)
- Do not use prior generated YAML as factual evidence or as a template

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
