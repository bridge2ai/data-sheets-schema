# CHORUS full/core reconciliation — 2026-08-11_claude-opus-5-claudecode-generic_rep2

- **Project**: CHORUS
- **Arm**: BASELINE (input documents only)
- **Condition**: generic — `src/download/prompts/d4d_generic_arm_prompt.md`
- **Runtime / provider / model**: Claude Code / Anthropic / claude-opus-5
- **Mode**: four-phase project agent (Phases 1–4 run sequentially in one context)
- **Repo commit at run time**: `a48dcab2`
- **Declared input bundle**: `data/preprocessed/concatenated/CHORUS_preprocessed.txt`
  (4 documents, 1698 lines)
- **Full**: `data/d4d_concatenated/claudecode_agent/2026-08-11_claude-opus-5-claudecode-generic_rep2/CHORUS_d4d.yaml`
- **Core**: `data/d4d_concatenated/claudecode_agent_core/2026-08-11_claude-opus-5-claudecode-generic_rep2/CHORUS_d4d_core.yaml`

## Referent

`Dataset` admits one referent. The record is about the **CHoRUS dataset**, identified
by `https://chorus4ai.org/` — the referent and `referent_id` the source manifest
declares for this project, and the only identifier the bundle itself uses (no dataset
DOI appears in any CHORUS source). CHORUS declares no `related_but_distinct` dataset.

The bundle also contains substantial material about two things that are *not* the
referent, and neither was absorbed into it:

- the **AIM-AHEAD Bridge2AI for Clinical Care Training Program** (Cohort 2), which
  occupies most of the September 2025 webinar. Its trainee stipend, eligibility rules,
  application deadlines and curriculum are properties of a training program, not of the
  dataset. Only the statements the webinar makes *about the dataset* were used, plus the
  program's use of the data, recorded under `existing_uses`. In particular the $8,000
  trainee stipend was **not** recorded as participant compensation.
- the **chorus-ai GitHub software project**, whose MIT License is a software license.
  See "Licensing" below.

## Phase 3 — source and provenance audit

### Provenance

- Factual inputs were the declared bundle, `data/preprocessed/source_manifest.yaml`,
  and the full and core LinkML schemas. Nothing else was read as a factual source.
- **No prior D4D record was read, in any arm, label or date.** Nothing under
  `data/d4d_concatenated/` was opened except this run's own two outputs, and no
  `*_crate_d4d.yaml` or `*_crate_mapped_d4d.yaml` under `data/ro-crate_packages/`
  was opened. No evaluation report, rubric output or reconciliation report from an
  earlier run was consulted.
- Structure was derived at runtime from the schemas with `SchemaView`
  (`class_induced_slots` over `Dataset`, `CoreDataset` and every nested range used),
  not from any example record. `d4d:docExample` annotations were not copied.
- Phase 2 read only this run's Phase 1 file, whose path carries this run's exact label.
- `d4d api prompts check`: 10 prompt files, **0 not at their pin**; the condition's
  prompt `src/download/prompts/d4d_generic_arm_prompt.md` is canonical.

### Source disagreements — represented, not resolved

The four sources describe the dataset at different dates and different scopes. Each
disagreement is recorded on both sides with the scope that distinguishes them; none was
merged into a single figure.

| Fact | Project website | Sept 2025 webinar | NIH RePORTER | Where recorded |
|---|---|---|---|---|
| Cohort size | 50,000 admissions (current released) / 100,000 (anticipated final) | >45K unique admissions as of Aug 2025 | >100,000 critically ill patients (target) | `instances[patient admission]` — `counts: 50000`, other figures in `description` and `source_caveats` |
| Imaging volume | 7,642 admissions with radiology data | 1,000 images available, de-id in process | — | `instances[imaging]` — `counts: 1000`, both figures in `source_caveats` (images ≠ admissions) |
| Hospitals / centers | 14 contributing hospitals; 60+ members across 20 institutions | 14 hospitals | — | `creators[CHoRUS Network]`, `maintainers` (GitHub: 20 academic centers, 14 as Data Acquisition centers) |

### Shape and slot-filling audit

- No prose was placed in a slot whose range is a list; no enum value outside its
  schema-declared set (`limitation_type`, `confidentiality_level`, `role` all validate).
- **`notes` is unused in both records.** Narrative sits in `description`; evidence
  commentary sits in `source_caveats` (top level and on 8 nested objects). No
  `source_caveats` value restates a sibling.
- Organizations are name-only. `Organization.id` is optional and the identifier audit
  treats a bare token as worse than an absent identifier, so no identifier was invented
  for MGH, UF, UTHealth Houston or Tufts.
- **Identifier syntax** (`data_sheets_schema.identifiers`): full 93 identifier-ranged
  values — 1 URI, 92 declared-prefix CURIEs, **0 bare tokens, 0 undeclared prefixes**;
  core 87 — 1 URI, 86 declared CURIEs, 0 unresolvable. Dominant convention
  `curie_declared` in both.
- `d4d download scope --check --project CHORUS`: the record does not identify itself as
  a dataset the manifest declares distinct.

### Deliberate omissions (evidence absent, so the slot is absent)

`license` (top level), `doi`, `version`, `version_access`, `issued`/`created_on`/
`last_updated_on`, `total_file_count`, `total_size_bytes`, `is_tabular`, `citation`,
`file_collections`, `subsets`, `variables`, `parent_datasets`, `related_datasets`,
`distribution_dates`, `collection_consents`, `collection_notifications`,
`consent_revocations`, `informed_consent`, `participant_compensation`,
`data_protection_impacts`, `retention_limit`, `errata`, `anomalies`, `known_biases`,
`content_warnings`, `discouraged_uses`, `prohibited_uses`, `use_repository`,
`imputation_protocols`, `annotation_analyses`, `machine_annotation_tools`.

Four of these are worth naming explicitly, because a plausible value was available and
was rejected:

1. **Licensing.** The chorus-ai GitHub README states "This project is licensed under the
   MIT License"; one repository in the same listing carries Apache-2.0. That is the
   software project's license. No source in the bundle states a license for the dataset,
   which is governed instead by "a licensing agreement included in the registration
   form" whose text the bundle does not reproduce. `license` is therefore absent and the
   distinction is recorded in `license_and_use_terms.source_caveats`.
2. **Collection timeframe dates.** NIH RePORTER gives 2022-09-01 → 2026-11-30. That is
   the *award* period, not the span of the clinical records. `start_date` and `end_date`
   are left empty and the award period is described in `timeframe_details` with the
   distinction stated in `source_caveats`.
3. **HIPAA / GDPR.** The only mention in the bundle is a training-curriculum topic
   ("HIPAA/GDPR compliance for OMOP/FHIR data"). `hipaa_compliant` is left empty rather
   than asserted from a syllabus.
4. **Representativeness.** The bundle states the *aim* ("sampling methods to ensure a
   balanced and diverse cohort", "the most diverse ... data set") but no achieved
   property, so `is_representative` is empty and the aim sits in `strategies`.

### Back-ports from Phase 2 to Phase 1

**None.** Phase 2 found no core field that the source documents support and the full
record had left empty, and no value where the documents contradict the full record.
Core's two exclusive slots are unsupported by this bundle:

- `distributions` (`CoreDistribution`: bytes, hashes, path, format, encoding, media
  type) — the bundle names data standards but no files, paths, byte counts or checksums.
  The full record has no `file_collections` for the same reason, so there is no full →
  core distribution mapping to review.
- `dialect` (`FormatDialect`: delimiter, quote char, header) — no tabular dialect is
  described anywhere in the bundle.

### Known residual weakness

`principal_investigator`, `contact_person` and `committee_contact` have range `Person`,
which declares an identifier, so LinkML does **not** inline them: the slot carries a
reference string. In a single-root instance document there is nowhere to define the
referenced `Person`, so those three CURIEs
(`d4d:CHORUS-person-eric-s-rosenthal`, `d4d:CHORUS-person-jared-houghtaling`,
`d4d:CHORUS-person-ciera-mccrary`) do not resolve to an object within either record.
Each person's name, affiliation and (where given) email is therefore carried in the
enclosing object's `description`. This is a schema property, not a defect in this run,
and it is noted here rather than worked around by inventing a structure the schema does
not permit.

## Phase 4 — strict full/core reconciliation

Shared slots were derived at runtime from `Dataset` and `CoreDataset` with
`SchemaView`; no hand-written field list was used.

- **Schema-identical (identity) slots: 78.** Every one is present in both records or
  absent from both, with deeply identical parsed YAML — including the narrative fields.
  Core condenses, paraphrases, reorders and omits nothing.
- **Projected slots: 1** — `resources` (`Dataset` in full, `CoreDataset` in core).
  Neither record populates it, so the projection is vacuously equal.
- **Full-only top-level slots, dropped from core because `CoreDataset` does not declare
  them (6):** `relationships`, `splits`, `direct_collection`, `participant_privacy`,
  `third_party_sharing`, `data_governance`. Their content is not restated elsewhere in
  core and is not lost from the pair — it remains in the full record.
- **Related, non-identical representations:** none to reconcile. `file_collections` →
  `distributions` does not apply (both empty); `total_file_count` / `total_size_bytes`
  are absent from full so there is nothing to compare against distribution-level values;
  `dialect`, `is_tabular` and formats raise no cross-record conflict because the only
  format-bearing slot, `distribution_formats`, is an identity slot and is identical.
- **Historical vs current releases:** the "current released dataset" and "anticipated
  final dataset" figures are held apart with their scope stated, in the same words in
  both records, and are not treated as a contradiction.

### Slot counts (informational metadata, not a quality gate)

| | top-level slots | lines |
|---|---|---|
| full | 51 | 1046 |
| core | 45 | 779 |

### Corrections applied during the run

1. Phase 1 first validation run reported three type errors: `principal_investigator`,
   `contact_person` and `committee_contact` had been written as inlined `Person`
   objects. The schema does not inline them. Fixed by replacing each with its
   identifier reference and relocating the person's name, affiliation and email into
   the enclosing object's `description` (and the email-transcription caveat into
   `data_governance.source_caveats`). Re-validated clean.
2. `--sync-core` was run once after the Phase 3 audit and changed no value: the core
   body had been generated by projecting the audited full record through
   `CoreDataset`'s slot inventory, so synchronization was content-neutral. It appended
   the `# Phase 4 reconciliation: completed` header line.

### Files changed

- `data/d4d_concatenated/claudecode_agent/2026-08-11_claude-opus-5-claudecode-generic_rep2/CHORUS_d4d.yaml` (created)
- `data/d4d_concatenated/claudecode_agent_core/2026-08-11_claude-opus-5-claudecode-generic_rep2/CHORUS_d4d_core.yaml` (created, then synchronized)
- `data/d4d_concatenated/claudecode_agent_core/2026-08-11_claude-opus-5-claudecode-generic_rep2/CHORUS_reconciliation.md` (this file)

## Commands run

```bash
poetry run d4d download scope --project CHORUS

poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_all.yaml \
  -C Dataset  data/d4d_concatenated/claudecode_agent/2026-08-11_claude-opus-5-claudecode-generic_rep2/CHORUS_d4d.yaml
poetry run linkml-term-validator validate-data \
  data/d4d_concatenated/claudecode_agent/2026-08-11_claude-opus-5-claudecode-generic_rep2/CHORUS_d4d.yaml \
  --schema src/data_sheets_schema/schema/data_sheets_schema_all.yaml --target-class Dataset

poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml \
  -C CoreDataset data/d4d_concatenated/claudecode_agent_core/2026-08-11_claude-opus-5-claudecode-generic_rep2/CHORUS_d4d_core.yaml
poetry run linkml-term-validator validate-data \
  data/d4d_concatenated/claudecode_agent_core/2026-08-11_claude-opus-5-claudecode-generic_rep2/CHORUS_d4d_core.yaml \
  --schema src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml --target-class CoreDataset

poetry run d4d download scope --check --project CHORUS
poetry run d4d api prompts check

poetry run python -m data_sheets_schema.d4d_pair_consistency \
  --full .../CHORUS_d4d.yaml --core .../CHORUS_d4d_core.yaml --sync-core
poetry run python -m data_sheets_schema.d4d_pair_consistency \
  --full .../CHORUS_d4d.yaml --core .../CHORUS_d4d_core.yaml
```

## Final results

| check | result |
|---|---|
| `linkml-validate` full (`Dataset`) | **No issues found** |
| `linkml-term-validator` full | **passed** |
| `linkml-validate` core (`CoreDataset`) | **No issues found** (after sync) |
| `linkml-term-validator` core | **passed** (after sync) |
| `d4d_pair_consistency` (independent, no `--sync-core`) | **PASS** — 78 identity slots, 0 errors, 0 warnings |
| `d4d download scope --check` | in scope |
| identifier syntax audit | 0 unresolvable in either record |
| `d4d api prompts check` | canonical, 0 not at their pin |
| prior-D4D reuse | none |

**Reconciliation outcome: PASS with zero divergence.** No schema-identical slot differed
between the two records, no correction was required by the Phase 3 source audit, and no
value was back-ported from Phase 2 to Phase 1.

The live provenance record for this run is written by the launcher, not by this agent.
