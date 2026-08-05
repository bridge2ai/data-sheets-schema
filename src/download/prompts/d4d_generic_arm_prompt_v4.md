# D4D generic-arm generation prompt — v4

**This is v3 plus one uniform decision rule, and nothing else.** The
substitution fields, outputs, header block, constraints, the four original rules
and the v2 and v3 additions are byte-identical to
`src/download/prompts/d4d_generic_arm_prompt_v3.md` apart from the version stamp;
a test asserts that the only difference is the block marked `ADDED IN v4`.

## Why v4 exists

v3 addressed hollow objects: a class-ranged slot whose declared fields sit empty
while the content is restated in a free-text `description`. That rule tells the
model to populate declared structure wherever it can.

It says nothing about where structure does *not* belong. `target_dataset` is
declared `range: string` and takes an identifier, and #297 established that
LinkML cannot express a string-or-inline-object range, so the schema cannot
refuse an object there — only validation can, after the fact.

All three 2026-07-31 VOICE replicates fail validation on `related_datasets`
(#292), and one fails precisely this way: an inline `Dataset` object placed in
`target_dataset`. `related_datasets` is class-ranged, so a model applying v3's
rule energetically has an obvious next step — populate the related dataset
properly, into the slot that names it.

v4 is therefore the companion v3 needs rather than a correction of it. The two
rules together say: populate declared structure where it is declared, and refer
by identifier where it is not.

## Why this addition is generic and not priming

Measured against the taxonomy in `.claude/commands/d4d-full-core.md`:

- it applies identically to every project, naming no project, dataset or input
  set;
- it states no target count, no expected density, and no expected relationship
  to any other arm — it is a decision rule, not an outcome expectation;
- it concerns the schema, which every arm shares.

## What is NOT in this file, deliberately

The prediction that this rule eliminates the inline-object failure without
suppressing legitimate object population. Writing it here would instruct the
model to produce the result the run is meant to test. It lives in
`notes/generic_v4_analysis_plan.md`, registered before any generation run.

## Relationship to earlier versions

None is superseded and none may be edited once run. The comparison that isolates
this rule is v3 against v4.

## Prompt body

Generate paired full and core D4D records for the {PROJECT} project.

READ FIRST, IN THIS ORDER, AND FOLLOW EXACTLY:

1. `.claude/agents/d4d-provenance-guard.md` — the factual evidence boundary.
   Enforce it in every phase.
2. `.claude/commands/d4d-full-core.md` — the four-phase playbook.

Execution mode: four-phase project agent. Phase 1 full generation, Phase 2 core
generation, Phase 3 source/provenance audit, Phase 4 strict reconciliation.
Phase 2 must wait for a validated Phase 1 file.

VERSION LABEL — use verbatim in every output path: {LABEL}

ARM: {ARM}

DECLARED INPUT BUNDLE — your only source of dataset facts:
    {BUNDLE}

Full schema: `src/data_sheets_schema/schema/data_sheets_schema_all.yaml` (class
`Dataset`)
Core schema: `src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml`
(class `CoreDataset`)

OUTPUTS — do not write outside these three:

- Full:   `data/d4d_concatenated/{METHOD}/{LABEL}/{PROJECT}_d4d.yaml`
- Core:   `data/d4d_concatenated/{METHOD}_core/{LABEL}/{PROJECT}_d4d_core.yaml`
- Report: `data/d4d_concatenated/{METHOD}_core/{LABEL}/{PROJECT}_reconciliation.md`

HEADER BLOCK — use exactly:

    # D4D Datasheet for {PROJECT} Dataset
    # Generation Method: schema-grounded agentic, phase 1
    # Agent runtime: {RUNTIME}
    # Provider: {PROVIDER}
    # Model: {MODEL}
    # Mode: four-phase project agent, generic-v4 prompt
    # Prompt: src/download/prompts/d4d_generic_arm_prompt_v4.md (identical for all projects)
    # Arm: {ARM}
    # Source bundle: {BUNDLE}
    {MANIFEST_LINE}
    # Schema: src/data_sheets_schema/schema/data_sheets_schema_all.yaml
    # Prior D4D factual reuse: prohibited
    # Temperature: 0.0
    # Generated: {DATE}

The core file uses "phase 2" and the core schema path in the corresponding lines.

AFTER Phase 4, write a LIVE provenance record:

    poetry run d4d provenance record --project {PROJECT} --method {METHOD} --label {LABEL} --input-bundle {BUNDLE}

VALIDATE both files before finishing:

    poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_all.yaml -C Dataset <full>
    poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml -C CoreDataset <core>

ABSOLUTE CONSTRAINT — do not read, open, grep, or consult any previously
generated D4D record, from any arm, any label, or any date. This includes
everything under `data/d4d_concatenated/` and any `*_crate_d4d.yaml` or
`*_crate_mapped_d4d.yaml` under `data/ro-crate_packages/`. Your only factual
inputs are the declared bundle above and the schema files. Prior-D4D reuse is a
defect under the provenance guard.

UNIFORM DECISION RULES — these apply identically to every project and every arm:

- Populate a slot only where the declared bundle supports it. Prefer omission
  over inference: an absent slot is a correct answer when the evidence is
  absent, and a plausible guess is not.
- Where the declared bundle contains sources that disagree, represent what the
  evidence states rather than silently selecting one. Do not merge distinct
  entities into a single claim.
- `Dataset` admits one referent. Choose the one the declared bundle best
  supports, state that choice in the reconciliation report, and hold to it
  consistently across both records.
- There is no target slot count, no expected density, and no expected
  relationship to any other arm or project. Apply your own judgment about what
  the evidence supports.

--- ADDED IN v2 ---

- When a slot's declared range is multivalued, emit one object per distinct
  entity. Collapsing several entities into a single object — several creators in
  one Creator, several uses in one intended_use — populates the slot without
  representing what it declares.
- Populate a slot with the information the field asks for, not with a pointer to
  where that information lives, and not with a statement that it is pending or
  absent. A value recording that documentation exists elsewhere has not answered
  the field; omit the slot instead.
- Read the slot's description before populating it. Where the evidence answers a
  neighbouring field — the access route rather than the distribution formats,
  the release cadence rather than the future-use impacts — put it in the field it
  answers, or omit it.

--- END ADDED IN v2 ---

--- ADDED IN v3 ---

- When a slot's declared range is a class, populate the fields that class
  declares. Placing the content in a free-text field such as `description` while
  the declared fields — a name, an identifier, dates, affiliations — stay empty
  produces an object of the correct shape holding none of the structure it
  exists to carry. Where the evidence answers a declared field, populate that
  field rather than restating it in prose.

--- END ADDED IN v3 ---
--- ADDED IN v4 ---

- Where a slot's declared range is a scalar, populate it with the identifier of
  the thing it refers to, not with the thing itself. An object placed in a
  string-ranged slot fails validation and loses the reference it was meant to
  record, even where that thing is richly described elsewhere in the record.

--- END ADDED IN v4 ---


RETURN: full slot count, core slot count, whether both validated, and the
reconciliation outcome. Return data, not prose.
