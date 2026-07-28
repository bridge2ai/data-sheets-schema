# CHORUS full/core reconciliation — 2026-07-27_claude-opus-5_rep2

- Agent runtime: Claude Code
- Provider: Anthropic
- Model: claude-opus-5[1m]
- Mode: four-phase project agent (Phases 1–4 run sequentially in one context)
- Temperature: 0.0
- Generated: 2026-07-27
- Arm: BASELINE (document corpus only)

## Files

| Role | Path | Lines |
|---|---|---|
| Full | `data/d4d_concatenated/claudecode_agent/2026-07-27_claude-opus-5_rep2/CHORUS_d4d.yaml` | 1295 |
| Core | `data/d4d_concatenated/claudecode_agent_core/2026-07-27_claude-opus-5_rep2/CHORUS_d4d_core.yaml` | 850 |

Line counts are informational metadata, not a quality gate.

## Phase 3 — Source and provenance audit

### Provenance boundary

Factual input for this run was exactly one file:
`data/preprocessed/concatenated/CHORUS_preprocessed.txt` (36,184 bytes, 4 sources),
selected by `data/preprocessed/source_manifest.yaml`. The four sources are
`nih_reporter_project`, `cohort_2_webinar`, `project_documentation`, and
`github_organization_overview` (historical supplement, captured 2025-11-14, explicitly
retained by the manifest).

Structure was derived only from `data_sheets_schema_all.yaml` (class `Dataset`) and
`data_sheets_schema_core_all.yaml` (class `CoreDataset`), read through LinkML
`SchemaView`.

No prior D4D record, evaluation, reconciliation report, or RO-Crate artifact was read,
searched, globbed, or cited. No live web content was fetched. No prior D4D content from
the parent conversation was used as evidence. The only generated YAML read during the
run was this run's own Phase 1 full record, consumed by Phase 2.

### Schema-shape findings that constrained Phase 1

`principal_investigator`, `contact_person`, `reviewing_organization`, `grantor`, and
`governance_committee_contact` are declared with class ranges but no `inlined` setting,
so LinkML treats them as identifier references, not nested objects. A probe against
`linkml-validate` confirmed nested dicts are rejected. These slots therefore carry
CURIE references, and the corresponding human-readable names are carried in the
enclosing object's `name`/`description`.

### Source conflicts resolved

1. **Admission counts.** `project_documentation` (chorus4ai.org, undated) reports a
   "Current Released Dataset" of 50,000 patient admissions from ICU, PICU, and NICU.
   `cohort_2_webinar` (September 2025) reports that, as of August 2025, the dataset
   covered 14 different hospitals with over 45,000 unique admissions. Resolved by
   scope rather than by overriding either source: `instances` carries `counts: 50000`
   for the released-dataset figure, and the August 2025 figure is retained in the same
   object's description with its explicit as-of date. Both are also stated with their
   scope in `status` and `known_limitations`. The two figures are not contradictory —
   they differ in date and in what is being counted.

2. **Imaging volume.** The website reports 7,642 admissions with radiology data;
   the webinar reports approximately 1,000 images available with de-identification in
   process. These are different units (admissions vs images) at different dates. Both
   retained as separate `Instance` entries with explicit scope; neither was converted
   into the other.

3. **Anticipated vs current scale.** 100,000 patient admissions (website "Anticipated
   Final Dataset"; also the RePORTER abstract's "more than 100,000 critically ill
   patients") versus the current released figures. Recorded as a stated target
   throughout (`description`, `addressing_gaps`, `updates`, `known_limitations`), never
   as a present-tense dataset size.

4. **Modality metadata table.** The webinar's modality table survives PDF text
   extraction with its column order scrambled. Only adjacent, unambiguous pairings were
   asserted: data type → data standard (Demographics/Medication administration/
   Procedures/Nursing flowsheets/Diagnoses → OMOP; Clinical notes → OHNLP; Imaging →
   DICOM; Waveform telemetry → WFDB; Waveform EEG → EDF+ and Persyst), and the
   Metadata column values Planned (clinical notes, imaging, EEG) and Yes (telemetry).
   The table records that one OMOP-standardized modality publishes an "OMOP schema with
   extensions", but the extraction does not preserve which row that annotation belongs
   to; this is stated explicitly in the nursing-flowsheets collection rather than
   assigned to a guessed row.

5. **License scope.** The GitHub organization README states "This project is licensed
   under the MIT License", and individual repositories carry MIT and Apache-2.0. The
   dataset itself is controlled-access behind an unnamed licensing agreement. Top-level
   `license` was therefore left unpopulated, and the MIT/Apache-2.0 facts are recorded
   in `license_and_use_terms` with explicit scoping to project software rather than the
   clinical dataset.

### Corrections applied in Phase 3

One correction, applied to the full record first and then propagated to core:

- The webinar table has separate "Metadata" (Yes/Planned) and "Published metadata
  schema" (Yes (...)) columns. Phase 1 conflated them, writing "a published metadata
  schema was listed as planned" for clinical notes, imaging, and waveform EEG. A
  published metadata schema is in fact named for every modality; it is the metadata
  itself that is Planned for those three. Corrected in three `file_collections`
  descriptions, in `known_limitations`
  (`d4d:CHORUS-limitation-metadata-schema-planned`, also renamed), and in `updates`.
  Both files were re-validated after the correction and core was rebuilt from the
  corrected full record.

### Unsupported assertions checked and omitted

No DOI, download URL, version identifier, release date, citation, file count, byte
count, IRB approval identifier, ethics review board name, consent or consent-revocation
procedure, retention limit, erratum, imputation protocol, annotation-agreement
analysis, or prohibited/discouraged use statement appears in the corpus. All
corresponding slots were left unpopulated rather than filled by inference. `23 Tb` of
waveform data is recorded as source text only; no `total_size_bytes` or
`CoreDistribution.bytes` was derived, because the source does not disambiguate the
unit. `is_tabular` was omitted because the dataset mixes tabular OMOP data with imaging
and waveform data and no source characterizes it either way.

Two source typos are transcribed verbatim and flagged here rather than silently
repaired: the website notice "This repoitory is under review…" and the program-manager
address `cmccrary@mgh.havard.edu` as printed on chorus4ai.org.

### Internal consistency check

Repeated values were verified consistent across every occurrence in each file:
award `OT2OD032701` / project number `1OT2OD032701-01` / application ID `10472824`;
project period 2022-09-01 to 2026-11-30; 14 data-contributing hospitals; 20 academic
centers / institutions; 60+ consortium members; 9 modalities (matching exactly 9
`file_collections` in full and 9 `distributions` in core); 50,000 / 45,000 / 100,000
admissions with their scope labels; 1,600,000,000 OMOP rows; 7,642 radiology
admissions; 1,000 imaging studies; 28 GitHub repositories.

### Validation after Phase 3

```bash
poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_all.yaml \
  -C Dataset data/d4d_concatenated/claudecode_agent/2026-07-27_claude-opus-5_rep2/CHORUS_d4d.yaml
poetry run linkml-term-validator validate-data \
  data/d4d_concatenated/claudecode_agent/2026-07-27_claude-opus-5_rep2/CHORUS_d4d.yaml \
  --schema src/data_sheets_schema/schema/data_sheets_schema_all.yaml --target-class Dataset
poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml \
  -C CoreDataset data/d4d_concatenated/claudecode_agent_core/2026-07-27_claude-opus-5_rep2/CHORUS_d4d_core.yaml
poetry run linkml-term-validator validate-data \
  data/d4d_concatenated/claudecode_agent_core/2026-07-27_claude-opus-5_rep2/CHORUS_d4d_core.yaml \
  --schema src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml --target-class CoreDataset
```

All four passed (`No issues found`, `✅ Validation passed`).

## Phase 4 — Strict full/core reconciliation

### Schema-derived shared slots

Derived at runtime with LinkML `SchemaView` from `Dataset` and `CoreDataset`:

- **76** schema-identical shared slots (same induced range and cardinality).
- **1** projected slot: `resources` (`Dataset` in full, `CoreDataset` in core).
  Unpopulated in both records, so coverage is trivially equal.
- **2** core-only slots: `distributions`, `dialect`.
- **17** full-only slots: `citation`, `collection_consents`,
  `collection_notifications`, `consent_revocations`, `direct_collection`,
  `file_collections`, `parent_datasets`, `participant_compensation`,
  `participant_privacy`, `related_datasets`, `relationships`, `splits`, `subsets`,
  `third_party_sharing`, `total_file_count`, `total_size_bytes`, `variables`.

### Identity result

47 shared slots are populated in both records, and every one is deeply identical —
same nested mapping values and same list items in the same order, including all
narrative fields. Nothing was condensed, paraphrased, reordered, or dropped in core.
Verified independently of the validator by parsing both files and comparing values.

Seven populated full-only slots are correctly absent from core because `CoreDataset`
does not declare them: `file_collections` (projected to `distributions`, below),
`subsets` (the holdout test set), `relationships`, `splits`, `direct_collection`,
`participant_privacy`, and `third_party_sharing`. Core-only `dialect` is unpopulated,
consistent with the absence of any documented delimited-text delivery.

### Related-content mapping and semantic review

`file_collections` → `distributions`: 9 deterministic matches, 0 unmatched core
distributions. Each pair was reviewed:

| Full `file_collections` id | Core `distributions` id | Modality |
|---|---|---|
| `d4d:CHORUS-fc-demographics` | `d4d:CHORUS-dist-demographics` | Demographics |
| `d4d:CHORUS-fc-medication-administration` | `d4d:CHORUS-dist-medication-administration` | Medication administration |
| `d4d:CHORUS-fc-procedures` | `d4d:CHORUS-dist-procedures` | Procedures |
| `d4d:CHORUS-fc-nursing-flowsheets` | `d4d:CHORUS-dist-nursing-flowsheets` | Nursing flowsheets |
| `d4d:CHORUS-fc-diagnoses` | `d4d:CHORUS-dist-diagnoses` | Diagnoses |
| `d4d:CHORUS-fc-clinical-notes` | `d4d:CHORUS-dist-clinical-notes` | Clinical notes |
| `d4d:CHORUS-fc-imaging` | `d4d:CHORUS-dist-imaging` | Imaging |
| `d4d:CHORUS-fc-waveform-telemetry` | `d4d:CHORUS-dist-waveform-telemetry` | Waveform telemetry |
| `d4d:CHORUS-fc-waveform-eeg` | `d4d:CHORUS-dist-waveform-eeg` | Waveform EEG |

Review findings:

- `name` is identical in every pair.
- `description` is identical in every pair, with one appended sentence in core carrying
  the `conforms_to` and `conforms_to_schema` values. `CoreDistribution` declares neither
  slot, so this is the only lossless projection available; no content is dropped and no
  content is altered.
- `FileCollection.collection_type: processed_data` has no `CoreDistribution` counterpart
  and is not representable; it is omitted from the projection rather than approximated.
- Paths, formats, compression, checksums, byte counts, and access URLs are absent from
  both sides. No format was assigned in core because `FormatEnum` (CSV/JSON/PDF/…) has
  no member matching OMOP, OHNLP, DICOM, WFDB, EDF+, or Persyst; asserting one would
  have been a fabrication.
- Release scope agrees: both sides carry the same as-of dates (August/September 2025 for
  imaging and EEG availability) and the same current-released-dataset figures.

Other related-content checks:

- `total_file_count` and `total_size_bytes` are unpopulated in full, and no
  `CoreDistribution.bytes` is populated in core. Nothing to compare, no conflict.
- `dialect`, `compression`, and `is_tabular` are unpopulated on both sides — consistent.
- Top-level identity, access, and version facts (`id`, `title`, `page`, `status`,
  `conforms_to`, `license_and_use_terms`, `regulatory_restrictions`, `version_access`,
  `updates`) are byte-identical across the pair and agree with the distribution-level
  statements: controlled access on every modality, no published version identifier or
  DOI, and a current release distinguished from an anticipated final release.
- No historical release is misrepresented as a current one. The single historical source
  in the bundle (GitHub organization overview, captured 2025-11-14) contributes
  organization, tooling, SOP, and contact facts, not release figures.

### Commands

```bash
poetry run python -m data_sheets_schema.d4d_pair_consistency \
  --full data/d4d_concatenated/claudecode_agent/2026-07-27_claude-opus-5_rep2/CHORUS_d4d.yaml \
  --core data/d4d_concatenated/claudecode_agent_core/2026-07-27_claude-opus-5_rep2/CHORUS_d4d_core.yaml \
  --sync-core

poetry run python -m data_sheets_schema.d4d_pair_consistency \
  --full data/d4d_concatenated/claudecode_agent/2026-07-27_claude-opus-5_rep2/CHORUS_d4d.yaml \
  --core data/d4d_concatenated/claudecode_agent_core/2026-07-27_claude-opus-5_rep2/CHORUS_d4d_core.yaml
```

Both runs reported:

```
PASS: 76 schema-identical slots; projected slots=['resources']
WARNING [semantic-review-required] $.file_collections <-> $.distributions: Phase 4 must
semantically review related distribution content; deterministic matches=9,
unmatched core distributions=[]
```

`--sync-core` produced no change, because core was built as a strict projection of the
Phase 3-corrected full record. The remaining warning marks related content requiring
review; that review is recorded above and found zero contradictions.

### Final validation

All four schema and term validations were re-run after Phase 4 and passed.

## Result

No divergence remains between the pair. The 47 populated shared slots are deeply
identical, the `resources` projection has equal (empty) coverage, and the nine
`file_collections` → `distributions` mappings are semantically consistent with zero
unresolved contradictions within or between the two records.
