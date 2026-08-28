---
name: d4d-provenance-guard
description: |
  When to use: Before and after generating or reconciling D4D full/core records.
  Enforces the factual evidence boundary for a generation run and prevents
  leakage from older generated YAML.
model: inherit
color: yellow
---


> **The uniform decision rules are in `.claude/commands/d4d-uniform-rules.md`.**
> Read them with this file. The evidence boundary and the rule that an
> identifier must come from the evidence are the same principle applied to two
> kinds of value, and enforcing one without the other is how a run supplied
> correct RORs its bundle never stated (#547, #563).

# D4D Provenance Guard

Apply this policy to every D4D generation run, regardless of whether the runtime
is Claude Code, Codex CLI, or another agent host.

## Governing Rule

Generated D4D YAML is an output, never an independent factual source.

Do not borrow, copy, preserve, or infer a dataset fact from an older full or core
D4D record. This prohibition includes identifiers, names, descriptions, people,
organizations, dates, versions, URLs, licenses, access rules, counts, methods,
ethics statements, limitations, and all nested-object content.

If a fact appears only in an older generated record and not in an allowed source
for the current run, omit it. Do not use an older record to resolve a conflict or
fill a gap.

Historical source documents are different from historical generated YAML. A
historical document is allowed when it is explicitly selected by the current
`data/preprocessed/source_manifest.yaml` and included in the current source
bundle.

## Schema-Only Structure Rule

The applicable LinkML schemas are the sole authority for record structure:

- Full: `data_sheets_schema_all.yaml`, class `Dataset`
- Core: `data_sheets_schema_core_all.yaml`, class `CoreDataset`

For every populated slot, derive its name, range, required status, cardinality,
inlining behavior, inherited availability, enum constraints, and nested-object
shape from the schema. Follow `is_a`, `mixins`, `slots`, `attributes`,
`slot_usage`, and class ranges as applicable.

Do not infer structure from an older YAML record, a source document, a checklist,
a model's prior knowledge, or a `d4d:docExample`. Documentation examples may
illustrate intent but cannot add fields, alter ranges, or override schema
constraints.

## Allowed Inputs By Phase

### Phase 1: Full

Allowed:

- `data/preprocessed/concatenated/{PROJECT}_preprocessed.txt`
- `data/preprocessed/source_manifest.yaml`
- full D4D schema files under `src/data_sheets_schema/schema/`
- repository generation and validation instructions

Forbidden:

- every prior full or core D4D YAML, including records for the same project
- factual values from schema examples, test fixtures, evaluations, reports, or
  model memory
- live web content unless the user explicitly requested a source refresh

Construct and constrain structure from the schema. Do not read an older D4D as
a template.

### Phase 2: Core (derived, #694)

Allowed:

- the exact full D4D produced and validated in Phase 1 of the same run —
  the only input; `d4d derive core` projects it and reads nothing else
- core schema files (read by the command, not by an agent)

The bundle is not an input to this phase: a derived core cannot take a fact
from the bundle that the full record lacks. Such a fact is added to the full
record in Phase 3, with its receipt, and reaches the core on re-derivation.

Forbidden:

- every full D4D from another run
- every older core D4D, even as a template
- current-run full records for other projects as factual sources

The same-run full path must contain the current run's exact version label.

### Phase 3: Source and provenance audit

Allowed:

- the current source bundle and manifest
- the exact same-run full/core pair
- full and core schemas

Forbidden:

- all records from earlier runs
- all evaluation reports derived from earlier records

Resolve disagreements from the current source bundle. Never choose a value
because an older generated record agrees with it.

### Phase 4: Re-derivation, checks, report, repair

Allowed:

- the same allowed inputs as Phase 3
- Phase 3 findings for the exact same-run pair
- `d4d derive core --phase4-complete`, `data_sheets_schema.d4d_pair_consistency`,
  the grounding, report-claims and receipts checkers

Forbidden:

- records or reports from an earlier run
- evaluation artifacts as factual evidence
- editing the core record by hand, including `--sync-core`: every change is
  made to the full record and the core is re-derived from it

Nothing is copied from full to core by an agent: shared slots are identical
because the core is a projection, and the pair checker is the proof. What
remains for judgement is the semantic review of related content (the
checker's `semantic-review-required` warning and the unprompted count,
dialect and release-scope reviews the playbook names), written as rows of
the report's `## Semantic review` section.

## Runtime-Specific Controls

### Claude Code

- Launch a fresh project subagent where possible.
- Tell the subagent that prior D4D content in the parent conversation is
  forbidden evidence.
- Do not ask a subagent to search output directories for examples.
- Pass exact allowed input and output paths in the task.

### Codex / GPT

- The outer orchestrator starts a fresh `codex exec` context per project or per
  phase.
- A worker already running in that fresh context performs the assigned phase
  directly and must not recursively invoke `codex`.
- Instruct the agent not to search or read `data/d4d_concatenated/` or
  `data/d4d_individual/`, except for exact same-run paths allowed above.
- Pass exact allowed input and output paths in the prompt; do not use a glob to
  select an input D4D.

## Required Provenance Header

Every generated YAML must identify:

- agent runtime
- provider and model
- generation phase
- exact current source bundle
- exact schema
- for core only, exact same-run full D4D
- `Prior D4D factual reuse: prohibited`

## Completion Audit

Before declaring a record complete:

1. Confirm every factual input path is on the phase allowlist.
2. Confirm no prior generated YAML was read or cited.
3. Confirm every emitted slot and nested object is permitted by the applicable
   schema, including inherited and `slot_usage` constraints.
4. Confirm the core input full record has the same run label.
5. Confirm every value the Phase 3 audit back-ported or the Phase 4 repair
   changed is in the full record only, is supported by the current source
   bundle, and carries its receipt (`d4d receipts check --strict` passes).
6. Validate schema and ontology terms.
7. Run the schema-derived full/core pair validator.
8. Confirm all projected and related content received semantic review.
9. Record the Phase 3 provenance result and Phase 4 consistency result in the
   reconciliation report.
