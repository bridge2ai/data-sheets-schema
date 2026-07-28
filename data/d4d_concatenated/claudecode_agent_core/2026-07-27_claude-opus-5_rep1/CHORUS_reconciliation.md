# CHORUS full/core reconciliation — 2026-07-27_claude-opus-5_rep1

- Agent runtime: Claude Code
- Provider: Anthropic
- Model: claude-opus-5[1m]
- Mode: four-phase project agent (Phases 1–4 sequential, single agent context)
- Temperature: 0.0
- Arm: BASELINE (document corpus only)
- Generated: 2026-07-27

## Files

| Role | Path | Lines |
|---|---|---|
| Full | `data/d4d_concatenated/claudecode_agent/2026-07-27_claude-opus-5_rep1/CHORUS_d4d.yaml` | 1338 |
| Core | `data/d4d_concatenated/claudecode_agent_core/2026-07-27_claude-opus-5_rep1/CHORUS_d4d_core.yaml` | 908 |
| Report | `data/d4d_concatenated/claudecode_agent_core/2026-07-27_claude-opus-5_rep1/CHORUS_reconciliation.md` | — |

Line counts are informational metadata only, not a quality gate.

## Phase 3 — source and provenance audit

### Provenance boundary

Factual input was `data/preprocessed/concatenated/CHORUS_preprocessed.txt` (1699
lines, 36,184 bytes, 4 source files) and no other source of dataset facts.
Structure and selection references were the full schema (`Dataset`), the core
schema (`CoreDataset`), `D4D_Core.yaml`, and
`data/preprocessed/source_manifest.yaml`.

The four manifest-selected CHORUS sources, all present in the bundle:

1. `nih_reporter_project` — NIH RePORTER project 10472824
2. `cohort_2_webinar` — AIM-AHEAD Bridge2AI for Clinical Care Cohort 2 informational webinar (2025-09-09)
3. `project_documentation` — https://chorus4ai.org/
4. `github_organization_overview` — chorus-ai GitHub organization overview, historical supplement captured 2025-11-14

No prior full or core D4D record, evaluation, reconciliation report, or RO-Crate
artifact was read, searched, or cited. No live web content was fetched. Output
directory names under `data/d4d_concatenated/claudecode_agent/` were listed once
to confirm the run label `2026-07-27_claude-opus-5_rep1` was unused; no file under
those directories was opened. `Prior D4D factual reuse: prohibited` appears in
both file headers.

Structure was derived at runtime from the schemas with LinkML `SchemaView`
(induced slots for `Dataset` and `CoreDataset`, with ranges, cardinality,
inlining, and enum inventories), not from any prior record or documentation
example. No `d4d:docExample` value was carried into either record.

### Source conflicts and how they were resolved

Four disagreements or ambiguities were found within the current bundle. In every
case both readings were retained with explicit scope rather than one being
silently preferred; the bundle contains no authority or recency basis for
collapsing them.

1. **Admission counts, 50,000 vs "over 45K".** The project website reports
   50,000 patient admissions from ICU, PICU, and NICU under "Current Released
   Dataset"; the Cohort 2 webinar reports that "As of August 2025, [the dataset]
   covers 14 different hospitals with over 45K unique admissions". These are
   different capture dates and arguably different scopes (released vs covered).
   Both are recorded as separate `instances` entries with their source and date
   stated. The webinar's "over 45K" is recorded as `counts: 45000` with the
   description flagging it as the stated lower bound.
2. **100,000 admissions vs 100,000 patients.** The website's "Anticipated Final
   Dataset" is 100,000 patient admissions; the NIH RePORTER abstract describes
   acquiring data "from more than 100,000 critically ill patients". Patients and
   admissions are distinct units and the bundle does not reconcile them. Both are
   stated in the anticipated-final `instances` entry.
3. **"23 Tb" waveform data.** Transcribed verbatim. Because Tb/TB is ambiguous
   and the figure is scoped to waveform data rather than the dataset, it was not
   converted into `total_size_bytes` (omitted) or into any distribution `bytes`
   value; it appears only as prose in the waveform telemetry description in both
   records.
4. **MIT license scope.** The GitHub overview states "This project is licensed
   under the MIT License", and individual repositories list MIT (chorus_waveform,
   chorus-extract-upload, UF-Geocoding) and Apache-2.0 (Chorus_SOP). This is the
   software licence, not a dataset licence. Top-level `license` was therefore left
   unset in both records, and the MIT/Apache-2.0 facts are carried on `Software`
   objects and inside `license_and_use_terms.license_terms`, which states
   explicitly that no licence identifier is given for the dataset itself.

### Source artifacts transcribed rather than corrected

Verbatim transcription was preserved for published typographical artifacts, each
flagged in the surrounding `description`: "CPatient-Focused", "Data Acquistion",
"literacy nd utilization", "This repoitory is under review…", the truncated
abstract clause "and label data for ;", and the contact address
`cmccrary@mgh.havard.edu` (apparent misspelling of the domain, as published).

### Assessments distinguished from source facts

Four values are classifications applied to sourced facts rather than direct
transcriptions. Each states its basis in its own `description` so it can be
audited:

- `known_biases[0].bias_type: selection_bias` — the 14-of-20-centre contributing
  scope and ICU/PICU/NICU setting are sourced; the bias-type label is an
  assessment.
- `at_risk_populations.at_risk_groups_included: true` — basis is the sourced
  presence of PICU and NICU admissions.
- `sampling_strategies[0].is_sample: true` — basis is "sampling to ensure
  comprehensive sets of patient conditions and clinical treatment strategies" and
  "Federated access will enable sampling methods to ensure a balanced and diverse
  cohort".
- `direct_collection.is_direct: false` (full only) — basis is "Retrospective data
  collection" via data-contributing sites and provider/system-originated content.

### Sparse coverage — sections deliberately left empty

Consistent with the baseline arm's instruction to prefer omission over
inference, the following schema sections were omitted because the bundle
supports nothing: `informed_consent`, `participant_compensation`,
`imputation_protocols`, `annotation_analyses`, `anomalies`, `content_warnings`,
`errata`, `retention_limit`, `version_access`, `ip_restrictions`,
`use_repository`, `discouraged_uses`, `prohibited_uses`, `data_protection_impacts`,
`variables`, `relationships`, `distribution_dates`, `resources`, `dialect`.

Scalars omitted for the same reason: `license`, `version`, `doi`, `download_url`,
`created_on`, `issued`, `last_updated_on`, `language`, `citation`, `is_tabular`,
`total_file_count`, `total_size_bytes`. `data_topic` and `data_substrate` were
omitted from every `Instance` because the bundle supplies no B2AI standards
registry identifiers.

### Back-ports from Phase 2

None. Phase 2 derived core from the source bundle plus the Phase 1 full record
and discovered no source-supported fact missing from or contradicting the full
record, so no correction was applied to the full file.

### Validation after Phase 3

Both records passed schema and term validation unchanged.

## Phase 4 — strict full/core reconciliation

### Schema-derived shared slots

Shared slots were derived at runtime from `Dataset` and `CoreDataset` via
`data_sheets_schema.d4d_pair_consistency`; no hand-written field list was used.

- **Schema-identical slots: 76** — deeply identical parsed YAML content and
  identical presence across the pair.
- **Projected slots: 1** (`resources`, `Dataset` in full vs `CoreDataset` in
  core). Absent from both records, so coverage is trivially equal and there is no
  nested projection to check. The bundle describes no separately identified
  sub-dataset with its own identity.

The core record was produced by projecting the full record onto the induced
`CoreDataset` slot inventory, so shared-slot content is identical by
construction: no narrative field was condensed, paraphrased, reordered, or
omitted in core.

### Full-only slots dropped from core (not in `CoreDataset`)

`file_collections`, `subsets`, `splits`, `direct_collection`,
`participant_privacy`, `third_party_sharing`.

### Core-only slots

`distributions` (populated, 9 entries) and `dialect` (omitted — no tabular
dialect is described in the bundle).

### Related-content semantic review: `file_collections` ↔ `distributions`

The validator reported `semantic-review-required` with 9 deterministic matches
and 0 unmatched core distributions. That warning marks work to be done, not work
done; the review below was performed against the current source bundle.

Mapping (full `d4d:chorus_fc_*` → core `d4d:chorus_dist_*`), matched by name:
Demographics, Medication administration, Procedures, Nursing flowsheets,
Diagnoses, Clinical notes, Imaging, Waveform telemetry, Waveform EEG. These are
the nine data types tabulated in the Cohort 2 webinar; the website's "9 Different
data modalities" figure for the anticipated final dataset is consistent with that
count, and neither record asserts that the two enumerations are the same list.

| Property | Full | Core | Verdict |
|---|---|---|---|
| Names | 9 names | same 9 names | identical |
| Descriptions | per-modality | same text plus a trailing sentence restating `conforms_to` (and `file_count` for Imaging) | no conflict |
| Paths | not asserted | not asserted | consistent |
| Formats | `conforms_to` free string (OMOP, OHNLP, DICOM, WFDB, EDF+/Persyst) | `format` omitted — `FormatEnum` (CSV…XZ) has no applicable value | no conflict; the standards survive in the core description |
| Compression | absent | absent | consistent |
| Checksums (`hash`/`md5`/`sha256`) | n/a in `FileCollection` | omitted — bundle reports none | consistent |
| Byte counts | no `total_bytes` | no `bytes` | consistent; "23 Tb" retained as prose in both |
| Access URLs | none at collection level | none at distribution level | consistent; the single access URL lives on `distribution_formats`, an identity slot identical in both |
| Release scope | current-release snapshot with in-process modalities | same snapshot | consistent |

`total_file_count` and `total_size_bytes` are omitted from full and have no core
counterpart, so there is no scope comparison to make. The one collection-level
count, Imaging `file_count: 1000`, is restated in the core Imaging description
and is contradicted by no distribution-level total. `is_tabular` and `dialect`
are absent from both, so the tabularity and dialect statements cannot disagree.

Top-level identity, version, and access facts (`id`, `name`, `title`,
`description`, `page`, `publisher`, `status`, `conforms_to`, `keywords`) are
schema-identical slots and are byte-identical across the pair. `conforms_to`
enumerates exactly the standards named across the nine distributions, and the
controlled-access statement in `regulatory_restrictions`,
`confidential_elements`, `license_and_use_terms`, and every distribution
description agrees. Current-release figures, anticipated-final figures, and the
August 2025 webinar snapshot are carried as separately scoped statements, so
their differing values are not treated as contradictions.

**Unresolved contradictions within or between the two records: none.**

### Commands run

```bash
poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_all.yaml \
  -C Dataset data/d4d_concatenated/claudecode_agent/2026-07-27_claude-opus-5_rep1/CHORUS_d4d.yaml

poetry run linkml-term-validator validate-data \
  data/d4d_concatenated/claudecode_agent/2026-07-27_claude-opus-5_rep1/CHORUS_d4d.yaml \
  --schema src/data_sheets_schema/schema/data_sheets_schema_all.yaml --target-class Dataset

poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml \
  -C CoreDataset data/d4d_concatenated/claudecode_agent_core/2026-07-27_claude-opus-5_rep1/CHORUS_d4d_core.yaml

poetry run linkml-term-validator validate-data \
  data/d4d_concatenated/claudecode_agent_core/2026-07-27_claude-opus-5_rep1/CHORUS_d4d_core.yaml \
  --schema src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml --target-class CoreDataset

poetry run python -m data_sheets_schema.d4d_pair_consistency \
  --full data/d4d_concatenated/claudecode_agent/2026-07-27_claude-opus-5_rep1/CHORUS_d4d.yaml \
  --core data/d4d_concatenated/claudecode_agent_core/2026-07-27_claude-opus-5_rep1/CHORUS_d4d_core.yaml \
  --sync-core

poetry run python -m data_sheets_schema.d4d_pair_consistency \
  --full data/d4d_concatenated/claudecode_agent/2026-07-27_claude-opus-5_rep1/CHORUS_d4d.yaml \
  --core data/d4d_concatenated/claudecode_agent_core/2026-07-27_claude-opus-5_rep1/CHORUS_d4d_core.yaml
```

### Files changed during Phases 3–4

None. `--sync-core` found nothing to synchronize; the core record was already
identical to the full record on all 76 schema-identical slots, and the
independent check without `--sync-core` returned the same PASS.

### Final results

| Check | Result |
|---|---|
| Full — `linkml-validate` (`Dataset`) | PASS |
| Full — `linkml-term-validator` | PASS |
| Core — `linkml-validate` (`CoreDataset`) | PASS |
| Core — `linkml-term-validator` | PASS |
| Pair consistency (`--sync-core`) | PASS — 76 identity slots, 0 changes |
| Pair consistency (independent re-check) | PASS — 76 identity slots |
| Related-content semantic review | Completed — 9/9 distributions mapped, 0 conflicts |
| Provenance audit | PASS — no prior D4D, evaluation, report, or RO-Crate read |
