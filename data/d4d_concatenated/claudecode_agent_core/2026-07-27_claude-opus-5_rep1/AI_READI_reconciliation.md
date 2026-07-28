# AI_READI full/core reconciliation — 2026-07-27_claude-opus-5_rep1

Arm: BASELINE (document corpus only).

- Agent runtime: Claude Code
- Provider: Anthropic
- Model: claude-opus-5[1m]
- Mode: four-phase project agent
- Temperature: 0.0
- Generated: 2026-07-27

## Run inputs

Factual input (sole source of dataset facts):

- `data/preprocessed/concatenated/AI_READI_preprocessed.txt` (6,229 lines, 10 source
  documents: BMJ Open protocol publication, Nature Metabolism comment, NIH RePORTER
  project page, dataset documentation v2.0.0 and v3.0.0, AI-READI-LICENSE-v1.0,
  FAIRhub HTML records for datasets 2 and 3, FAIRhub API record for dataset 3, UW
  IRB protocol)

Structure and selection references (not fact sources):

- `data/preprocessed/source_manifest.yaml`
- `src/data_sheets_schema/schema/data_sheets_schema_all.yaml` (class `Dataset`)
- `src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml` (class `CoreDataset`)
- `src/data_sheets_schema/schema/D4D_Core.yaml` (via the merged core schema)

Outputs:

- Full: `data/d4d_concatenated/claudecode_agent/2026-07-27_claude-opus-5_rep1/AI_READI_d4d.yaml`
- Core: `data/d4d_concatenated/claudecode_agent_core/2026-07-27_claude-opus-5_rep1/AI_READI_d4d_core.yaml`
- This report

No pre-existing file was overwritten; both output directories were created for this run.

## Phase 1 — full record

Structure was derived at runtime from class `Dataset` in the full schema using LinkML
`SchemaView` (induced slots, ranges, cardinality, inlining, enum permissible values,
and identifier status for every nested class). The JSON Schema projection was
inspected to confirm the wire shape of non-inlined class-ranged slots
(`principal_investigator`, `contact_person`, `reviewing_organization`, `grantor`,
`governance_committee_contact` are identifier strings; `affiliations` and `grants`
are inlined object lists). No prior D4D record was read, searched, globbed, or cited.

81 top-level slots populated, including 9 `file_collections` (the CDS datatype
directories), 3 `subsets` (the recommended splits), 10 `variables`, and 17 `creators`.

## Phase 2 — core record

The core record is the semantic exchange-layer subset of the same-run full record, not
an independent extraction. The `CoreDataset` field inventory and nested class shapes
were derived from `data_sheets_schema_core_all.yaml`. For every shared slot the full
value was taken as the starting point; the source bundle was then re-checked for core
fields the full record left empty and for anything the full extraction missed.

Findings from that re-check:

- The only core-only slot with source support is `distributions`, projected from
  `file_collections` (see Phase 4).
- `dialect` (`FormatDialect`) is omitted: the source documents state file format
  standards but never a CSV/TSV delimiter, quote character, header convention, or
  comment prefix.
- No fact was found in the sources that the full record had missed, so no back-port
  into full was required on this ground.

## Phase 3 — source and provenance audit

### Provenance

- Every factual input path is on the Phase 1/2/3 allowlist. No file under
  `data/d4d_concatenated/` or `data/d4d_individual/` was read other than this run's own
  two outputs. No RO-Crate artifact was read. No live web content was fetched. No prior
  evaluation or reconciliation report was consulted.
- Both file headers state `Prior D4D factual reuse: prohibited`. The core header names
  both its source-document bundle and the exact same-run full YAML path, which carries
  this run's version label `2026-07-27_claude-opus-5_rep1`.
- The corpus includes the FAIRhub API record containing an 84-question Healthsheet.
  Per the arm note it was used as evidence like any other cited source. Because the
  Healthsheet is itself a datasheet-style artifact, a substantial share of the
  motivation, composition, collection, preprocessing, labeling, uses, distribution, and
  maintenance content in this record is closer to transcription than to extraction.

### Source conflicts resolved

1. **Lead/managing organization.** The FAIRhub study description records the lead
   sponsor, the managing organization, and the affiliation of the responsible-party
   principal investigator (Aaron Lee) and of Cecilia Lee as *Washington University in
   St. Louis*, ROR `https://ror.org/01yc7t268`. This is contradicted by the NIH
   RePORTER award record (awardee organization: University of Washington), the BMJ Open
   protocol publication (University of Washington IRB, UW author affiliations), the
   Nature Metabolism comment (University of Washington, Seattle), the data license
   agreement (Licensor: University of Washington), and the site list inside the same
   FAIRhub study description (University of Washington, Seattle, ROR
   `https://ror.org/00cvxb145`). **Resolution:** University of Washington, on the basis
   of five independent higher-authority sources against one field cluster in a single
   record. The conflict is disclosed verbatim in the record itself, in the AI-READI
   Consortium creator description.

2. **Dataset v2.0.0 vs v3.0.0 documentation.** The manifest selects the v2
   documentation and the v2 FAIRhub record, and adds the v3 documentation, the v3
   FAIRhub HTML record, and the v3 FAIRhub API record as current. The two documentation
   pages are near-identical in prose; the v3 page adds mini-subset and Azure Storage
   access to the Preliminary Information section. **Resolution:** the record describes
   version 3.0.0 throughout (2,280 participants, 356,343 files, 3.82 TB, DOI
   `10.60775/fairhub.3`, released 2025-11-17). All v2.0.0 facts retained (1,067
   participants, 165,051 files, 2.01 TB, DOI `10.60775/fairhub.2`, released 2024-11-08,
   marked on FAIRhub as no longer accessible) are explicitly scoped to v2.0.0 inside
   `related_datasets` and `version_access`, so the differing values are a version
   history rather than a contradiction.

3. **Target enrollment: 4,000 vs 4,600.** The UW IRB protocol summary states 4,600
   while its own subject-group table sums to 4,000 (1,000 per diabetes status group).
   The BMJ Open protocol publication (2025), the Nature Metabolism comment (2024), and
   the FAIRhub study description all state 4,000 anticipated. **Resolution:** 4,000. The
   IRB figure is both older and internally inconsistent within its own document; it is
   not carried into the record.

4. **Enrolment start date: 18 July 2023 vs 19 July 2023.** BMJ Open states enrolment
   began 18 July 2023; the FAIRhub study description records an actual start date of
   2023-07-19 and a collected range of 2023-07-19/2025-05-01, matching the Healthsheet.
   **Resolution:** both are kept with explicit scope — the v3.0.0 collection-window
   `CollectionTimeframe` uses 2023-07-19 to 2025-05-01 (dataset-level authority), and
   the overall-study `CollectionTimeframe` uses 2023-07-18 to 2026-11-30 (study-level
   authority), with both figures stated in `timeframe_details`.

5. **Licence version.** FAIRhub records the current licence as *AI-READI custom license
   v2.0*, `https://doi.org/10.5281/zenodo.17555036`. The licence text in the corpus is
   *AI-READI-LICENSE-v1.0*, `https://doi.org/10.5281/zenodo.10642459`. **Resolution:**
   `license` and `license_and_use_terms` name v2.0 as current, and every quoted clause
   is explicitly attributed to AI-READI-LICENSE-v1.0 with its section number, together
   with a statement that the v2.0 text is not among the source documents and that
   clause-level differences between the versions are therefore not represented.

6. **De-identification framing.** Nature Metabolism states the public set is stripped
   of PHI via the HIPAA Safe Harbor method plus sex and race/ethnicity; the FAIRhub
   dataset description records de-identification type `NoDeIdentification` with the
   explanation that no identifiers were collected so no active de-identification was
   necessary, only a HIPAA check. **Resolution:** both statements are reproduced in
   `is_deidentified.method` and `deidentification_details`; the boolean
   `identifiable_elements_present: false` is supported by both.

7. **NIH RePORTER identifier for award OT2OD032644.** The corpus contains two
   project-details identifiers for the same award: 10471118 (the NIH RePORTER document
   in the corpus, and the acknowledgement link in the FAIRhub readme) and 10885481 (the
   FAIRhub dataset and study descriptions). **Resolution:** 10471118 is used as the
   `Grant.id`; 10885481 is recorded in the grant description as an alternative
   identifier for the same award.

### Unsupported or mis-scoped assertions corrected in the full record

All of the following were found by the Phase 3 audit and fixed in
`AI_READI_d4d.yaml` before Phase 4:

| # | Issue | Correction |
|---|---|---|
| 1 | `created_on` was set to `2025-11-17T00:00:00+00:00`, derived from the FAIRhub `created_at` epoch value, which actually resolves to 08:00Z; the sources give a publication date, not a creation datetime | slot removed |
| 2 | `keywords` contained `Type 2 Diabetes` (a `resourceTypeValue`) and `Salutogenesis` (never a stated keyword) | both removed; the 9 remaining keywords are exactly the union of the FAIRhub subject list and the study keyword list |
| 3 | `VariableMetadata.minimum_value` / `maximum_value` were populated with clinical laboratory reference ranges; the schema defines these as the minimum/maximum value the variable can take | removed from all 9 laboratory variables (reference ranges retained as prose in `description`); retained only `maximum_value: 30.0` for the MoCA total score, which is a genuine value bound |
| 4 | `ExternalResource.archival` was set on four entries; the schema defines it as whether official archival versions are included in the dataset, which no source states | all four removed; a `future_guarantees` entry was added recording that the sources state no availability commitment |
| 5 | `updates.update_details` said v1.0.0 was "released 5 May 2024 per the FAIRhub version list date of 3 May 2024", implying a discrepancy that does not exist (the readme's `5/3/2024` is US-format 3 May 2024, matching FAIRhub) | corrected to "released 3 May 2024" |
| 6 | The Mini Version relationship asserted `target_dataset: 10.60775/fairhub.4` and a 100-participant count, both of which come only from the manifest curation note, not from the corpus | `target_dataset` changed to `FAIRhub dataset record 4` (the FAIRhub API `child` value) and the description reduced to what the FAIRhub HTML and API state |
| 7 | Licence clause quotations were attributed to "the University of Washington data license agreement published with the dataset" without naming the version | scoped to AI-READI-LICENSE-v1.0 with section numbers in `license_and_use_terms`, `prohibited_uses`, and `discouraged_uses` |
| 8 | Eligibility criteria and the 85-year maximum age were absent from the record entirely | added as `sampling_strategies.strategies` entries, together with the per-group recruitment targets |
| 9 | The consortium affiliation list read as exhaustive | description now states it covers the named study PIs' affiliations, notes the eight-institution figure from NIH RePORTER, and names further affiliations from the Nature Metabolism author list |

Nothing discovered in Phase 2 required back-porting into full, and no correction
changed a value in a direction that the core record had introduced.

### Internal consistency checks (all passed)

- Participant totals: `instances.counts` 2,280 = train 1,576 + validation 352 + test 352.
- Split demographics reconcile in every dimension: race/ethnicity 380+545+519+836 =
  2,280; sex 951+1,329 = 2,280; diabetes status 776+560+686+258 = 2,280; each per-split
  row also sums to its split total.
- Version progression: 204 (v1.0.0) + 863 (year 2) + 1,213 (year 3) = 2,280 (v3.0.0);
  and 204 + 863 = 1,067 (v2.0.0), matching the Healthsheet.
- Byte counts: the 9 datatype directories sum to 3,815,969,360,064 bytes against a
  dataset `total_size_bytes` of 3,815,969,779,678 — a residual of 419,614 bytes.
- File counts: the 9 datatype directories sum to 356,334 files against a
  `total_file_count` of 356,343 — a residual of 9 files.
  Both residuals are consistent with the root-level files the sources describe as
  included (README, LICENSE, `participants.tsv`, `dataset_description.json`,
  `study_description.json`, `dataset_structure_description.json`, CHANGELOG). The
  dataset totals are a superset scope of the directory totals, so this is not a
  contradiction.
- Repeated identifiers agree across the record: DOI `10.60775/fairhub.3`, version
  `3.0.0`, issue date 2025-11-17, IRB `STUDY00016228`, award `OT2OD032644`,
  ClinicalTrials.gov `NCT06002048`, and the ORCID iDs of the 15 study PIs.

### Deliberate omissions

`imputation_protocols`, `annotation_analyses`, `machine_annotation_tools`, `errata`,
`compression`, `conforms_to_class`, `created_by`, `modified_by`, `last_updated_on`,
`was_derived_from`, and `resources` are absent from **both** records. The sources
provide no evidence for any of them: no imputation is described, no labeling was
performed (so no annotation analysis or machine annotation tooling exists), and the
Healthsheet erratum question is returned unanswered. `CoreDistribution.format` and
`media_type` are omitted because the schema enums cannot express DICOM, WFDB, Open
mHealth, or NASA ESDS, and the sources state media types only at dataset level.

## Phase 4 — strict full/core reconciliation

### Schema-derived shared slots

Shared slots were derived at runtime from `Dataset` and `CoreDataset` with LinkML
`SchemaView`; no hand-written field list was used.

- **76 schema-identical slots** (same induced range, cardinality, required status, and
  inlining): 65 present in both records, 11 absent from both. No slot is present in
  only one record.
- **1 projected slot**: `resources` (`Dataset` in full, `CoreDataset` in core). It is
  absent from both records, so the projection is vacuous and coverage is trivially
  equal.
- **16 full-only slots** (no `CoreDataset` counterpart): `citation`,
  `collection_consents`, `collection_notifications`, `consent_revocations`,
  `direct_collection`, `file_collections`, `participant_compensation`,
  `participant_privacy`, `related_datasets`, `relationships`, `splits`, `subsets`,
  `third_party_sharing`, `total_file_count`, `total_size_bytes`, `variables`.
- **1 core-only slot**: `distributions`. (`dialect` is core-only in the schema but is
  unpopulated here.)

Every schema-identical slot has deeply identical parsed YAML content, including nested
mapping values and list order. No narrative field was condensed, paraphrased,
reordered, or dropped in core: `description`, all `purposes`, `tasks`,
`addressing_gaps`, `known_biases`, `known_limitations`, `license_and_use_terms`, and
`human_subject_research` are byte-for-byte the same values in both records.

### Related-content mapping and semantic review

`file_collections` (full) → `distributions` (core). The validator reports 9
deterministic matches and 0 unmatched core distributions; the warning it emits marks
this content as requiring the semantic review recorded below, and is not itself
evidence that the review occurred.

| Full `FileCollection` | Core `CoreDistribution` | Review |
|---|---|---|
| `cardiac_ecg` (4,515 files, 302,931,703 B, WFDB) | same id/name/path, `bytes` 302,931,703 | agree |
| `clinical_data` (7 files, 176,182,781 B, OMOP CDM) | same id/name/path, `bytes` 176,182,781 | agree |
| `environment` (2,232 files, 55,625,676,514 B, NASA ESDS) | same id/name/path, `bytes` 55,625,676,514 | agree |
| `retinal_flio` (7,969 files, 1,069,466,876,718 B, DICOM) | same id/name/path, `bytes` 1,069,466,876,718 | agree |
| `retinal_oct` (56,478 files, 1,317,625,293,027 B, DICOM) | same id/name/path, `bytes` 1,317,625,293,027 | agree |
| `retinal_octa` (173,721 files, 1,155,908,809,724 B, DICOM) | same id/name/path, `bytes` 1,155,908,809,724 | agree |
| `retinal_photography` (93,921 files, 174,381,046,406 B, DICOM) | same id/name/path, `bytes` 174,381,046,406 | agree |
| `wearable_activity_monitor` (15,245 files, 38,313,536,220 B, Open mHealth) | same id/name/path, `bytes` 38,313,536,220 | agree |
| `wearable_blood_glucose` (2,246 files, 4,169,006,971 B, Open mHealth) | same id/name/path, `bytes` 4,169,006,971 | agree |

Field-by-field review of the related representations:

- **Names, descriptions, paths**: identical strings in both records for all 9 pairs.
- **Byte counts**: every `CoreDistribution.bytes` equals the matched
  `FileCollection.total_bytes`. Their sum versus `total_file_count` /
  `total_size_bytes` is reconciled above; the scopes differ (datatype directories
  versus whole dataset including root-level files), so no conflict exists.
- **Formats**: full carries the format standard in `conforms_to` (WFDB, OMOP CDM, NASA
  ESDS, DICOM, Open mHealth). Core's `format` and `media_type` enums cannot represent
  any of these, so they are left unset rather than approximated. No conflicting format
  assertion exists between the two records.
- **Compression**: unset in both records at dataset, file-collection, and distribution
  level. The sources describe no archive or compression scheme.
- **Checksums**: `hash`, `md5`, and `sha256` are unset — the sources publish no
  per-directory or per-file checksums.
- **Access URLs**: access is described only at dataset level, identically in both
  records via `download_url`, `distribution_formats.access_urls`, and
  `version_access.latest_version_doi`. No distribution-level access URL is asserted in
  either record.
- **Release scope**: all 9 collections and all 9 distributions describe version 3.0.0
  and no other release. Version 1.0.0 and 2.0.0 facts live only in `distribution_dates`,
  `version_access`, and `related_datasets`, each explicitly labelled with its version.
- **`is_tabular` and dialect**: `is_tabular: false` is a schema-identical slot and is
  identical in both records; it is consistent with a corpus that mixes tabular CSV,
  DICOM imaging, and WFDB waveform data. `dialect` is unset in core, so it cannot
  conflict with anything in full.
- **Top-level identity/version/access facts** agree with `version_access`,
  `distribution_dates`, `distribution_formats`, and the repeated statements in
  `updates` and `related_datasets`: `id`/`doi` `10.60775/fairhub.3`, `version` `3.0.0`,
  `issued` 2025-11-17, `download_url` `https://fairhub.io/datasets/3`, `license`
  AI-READI custom license v2.0.

Zero unresolved contradictions within or between the two records.

## Commands run

```bash
poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_all.yaml \
  -C Dataset data/d4d_concatenated/claudecode_agent/2026-07-27_claude-opus-5_rep1/AI_READI_d4d.yaml

poetry run linkml-term-validator validate-data \
  data/d4d_concatenated/claudecode_agent/2026-07-27_claude-opus-5_rep1/AI_READI_d4d.yaml \
  --schema src/data_sheets_schema/schema/data_sheets_schema_all.yaml --target-class Dataset

poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml \
  -C CoreDataset data/d4d_concatenated/claudecode_agent_core/2026-07-27_claude-opus-5_rep1/AI_READI_d4d_core.yaml

poetry run linkml-term-validator validate-data \
  data/d4d_concatenated/claudecode_agent_core/2026-07-27_claude-opus-5_rep1/AI_READI_d4d_core.yaml \
  --schema src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml --target-class CoreDataset

poetry run python -m data_sheets_schema.d4d_pair_consistency \
  --full data/d4d_concatenated/claudecode_agent/2026-07-27_claude-opus-5_rep1/AI_READI_d4d.yaml \
  --core data/d4d_concatenated/claudecode_agent_core/2026-07-27_claude-opus-5_rep1/AI_READI_d4d_core.yaml \
  --sync-core

poetry run python -m data_sheets_schema.d4d_pair_consistency \
  --full data/d4d_concatenated/claudecode_agent/2026-07-27_claude-opus-5_rep1/AI_READI_d4d.yaml \
  --core data/d4d_concatenated/claudecode_agent_core/2026-07-27_claude-opus-5_rep1/AI_READI_d4d_core.yaml
```

## Files changed

- created `data/d4d_concatenated/claudecode_agent/2026-07-27_claude-opus-5_rep1/AI_READI_d4d.yaml`
- created `data/d4d_concatenated/claudecode_agent_core/2026-07-27_claude-opus-5_rep1/AI_READI_d4d_core.yaml`
- created `data/d4d_concatenated/claudecode_agent_core/2026-07-27_claude-opus-5_rep1/AI_READI_reconciliation.md`

No existing repository file was modified.

## Final results

| Check | Result |
|---|---|
| Full — `linkml-validate` against `Dataset` | No issues found |
| Full — `linkml-term-validator` | Validation passed |
| Core — `linkml-validate` against `CoreDataset` | No issues found |
| Core — `linkml-term-validator` | Validation passed |
| Pair consistency (after `--sync-core`) | PASS — 76 schema-identical slots, projected slots `['resources']` |
| Pair consistency (independent re-run, no sync) | PASS — 76 schema-identical slots, projected slots `['resources']` |

The only validator output that is not a pass is the `semantic-review-required` warning
on `$.file_collections <-> $.distributions`, which is the marker for the Phase 4
semantic review; that review is recorded in full above.

Informational metadata (not a quality gate): full 2,862 lines / 81 top-level slots;
core 1,691 lines / 66 top-level slots.
