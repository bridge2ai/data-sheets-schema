# VOICE full/core reconciliation report

Run label: `2026-07-23_gpt-5.6-sol-ultra-fast`

Runtime: Codex CLI; provider: OpenAI; model: `gpt-5.6-sol`; reasoning
effort: `ultra`; mode: `fast`; generated: 2026-07-23.

## Evidence and provenance boundary

The only factual inputs read were:

- `data/preprocessed/concatenated/VOICE_preprocessed.txt`
- the VOICE block of `data/preprocessed/source_manifest.yaml`, which selects
  exactly nine sources: `feasibility_publication`, `audiomics_white_paper`,
  `nih_reporter_project`, `project_documentation`, `irb_protocol`,
  `data_transfer_use_agreement`, `physionet_1_1`, `physionet_3_0_0`, and
  `documentation_repository`
- from Phase 2 onward, the same-run full record
  `data/d4d_concatenated/claudecode_agent/2026-07-23_gpt-5.6-sol-ultra-fast/VOICE_d4d.yaml`
- from Phase 3 onward, the same-run core record
  `data/d4d_concatenated/claudecode_agent_core/2026-07-23_gpt-5.6-sol-ultra-fast/VOICE_d4d_core.yaml`

The full and core LinkML schemas were read only as structural authority.
`src/data_sheets_schema/d4d_pair_consistency.py` and normal project
configuration were read only to run and interpret validation.

No prior-run full or core D4D content, prior reconciliation report, evaluation
output, test-fixture fact, git history, web content, or model-memory fact was
used. No D4D output directory was searched or listed for prior content. The
only D4D YAML read was the exact same-run artifact permitted for the active
phase.

## Phase 3 — source and provenance audit

### Source authority and scope findings

- The exact selected PhysioNet version page is authoritative for the release
  identity: title `Bridge2AI-Voice: An ethically-sourced, diverse voice dataset
  linked to health information`, version `3.0.0`, DOI
  `10.13026/k81f-qr68`, publisher PhysioNet, and publication date
  2025-12-16.
- Version 3.0.0 is explicitly not latest. Version 3.1.0 was published on
  2026-05-01, and the latest-version DOI is separately recorded as
  `10.13026/37yb-1t42`. The selected v3.0.0 DOI was retained as the dataset ID;
  the latest DOI was used only in `version_access`.
- The current release count is 833 adult participants at five North American
  sites. The approximately 61,937 voice-derived recordings are explicitly
  described as approximate recording-level content. The 47-person feasibility
  cohort, the separate 300-person pediatric release, and the 10,000/30,000
  project targets were not treated as v3.0.0 participant counts.
- The release contains derived audio features and phenotype data, not original
  voice recordings. Adult raw audio is modeled as a separate controlled source
  and external resource available through Synapse, not as a PhysioNet v3.0.0
  file collection or core distribution.
- Exact v3.0.0 access is credentialed PhysioNet access plus a signed DUA. The
  data license is `Bridge2AI Voice Registered Access License`, and no training
  is required. The feasibility article's CC BY license and the MIT/Apache
  licenses for documentation or software were not assigned to the data.
- The exact feature inventory supports nine dense Parquet files, one static
  TSV file, and ten paired JSON dictionaries. The phenotype tree enumerates
  90 files, comprising 45 TSV/JSON pairs. These counts describe the five
  modeled logical collections; they are not asserted as an authoritative total
  for every ancillary release file.
- No source-supported exact aggregate file count, total byte size, archive
  size, checksum, compression value, exact v3.0.0 collection interval, exact
  names of the five release sites, or exact demographic distribution was
  found. Those optional fields were omitted rather than inferred.
- Creator names and affiliations were checked against the selected v3.0.0
  citation and current project documentation. Funding was reconciled by scope:
  the release acknowledgment cites `3OT2OD032720-01S1`; the selected FY2025
  NIH RePORTER application is `3OT2OD032720-01S3`; both are explicitly tied to
  core project `OT2OD032720`.
- Dates were kept in their source scopes: 2025-12-16 is the v3.0.0 release
  date; 2022-09-01 through 2026-11-30 are grant dates; pilot-study dates and
  the raw-DTUA template approval date were not used as dataset-release or
  collection dates.

### Corrections and back-port audit

- Phase 1 validation required ISO 8601 timezone suffixes. The full root and
  collection `issued` values were corrected from
  `2025-12-16T00:00:00` to `2025-12-16T00:00:00Z` before Phase 1 was accepted.
- A collaborator-access restriction had been generalized from the controlled
  raw-audio DTUA template to the registered feature release. Phase 3 removed
  that over-broad assertion from the full record first and then from core.
- An inferred warning about unvalidated clinical deployment was not an
  explicitly stated dataset-use restriction. It was removed from the full
  record first and then from core; the source-supported hiring, insurance, and
  surveillance restrictions remain.
- Core introduced no source-supported factual discovery absent from full, so
  no additional core-to-full back-port was required.
- Repeated identifiers, title, DOI, version, release date, license, access
  conditions, participant count, creator names, organizations, and grant
  numbers were checked within each file. Historical, current, pilot,
  pediatric, raw-audio, project-target, and software/documentation statements
  remain explicitly scoped.

### Phase 3 validation

All four commands were run after the corrections:

```text
poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_all.yaml -C Dataset data/d4d_concatenated/claudecode_agent/2026-07-23_gpt-5.6-sol-ultra-fast/VOICE_d4d.yaml
Result: PASS — No issues found

poetry run linkml-term-validator validate-data data/d4d_concatenated/claudecode_agent/2026-07-23_gpt-5.6-sol-ultra-fast/VOICE_d4d.yaml --schema src/data_sheets_schema/schema/data_sheets_schema_all.yaml --target-class Dataset
Result: PASS — Validation passed

poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml -C CoreDataset data/d4d_concatenated/claudecode_agent_core/2026-07-23_gpt-5.6-sol-ultra-fast/VOICE_d4d_core.yaml
Result: PASS — No issues found

poetry run linkml-term-validator validate-data data/d4d_concatenated/claudecode_agent_core/2026-07-23_gpt-5.6-sol-ultra-fast/VOICE_d4d_core.yaml --schema src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml --target-class CoreDataset
Result: PASS — Validation passed
```

Phase 3 result: the audited full record is canonical, every factual assertion
is supported and source-scoped, and there are zero unresolved within-record or
cross-record factual contradictions.

## Phase 4 — strict full/core reconciliation

### Schema-derived synchronization and identity result

The validator derived **76 schema-identical shared slots** and one projected
slot, `resources`. The required one-time synchronization was run:

```text
poetry run python -m data_sheets_schema.d4d_pair_consistency --full data/d4d_concatenated/claudecode_agent/2026-07-23_gpt-5.6-sol-ultra-fast/VOICE_d4d.yaml --core data/d4d_concatenated/claudecode_agent_core/2026-07-23_gpt-5.6-sol-ultra-fast/VOICE_d4d_core.yaml --sync-core
Result: PASS — 76 schema-identical slots; projected slots=['resources']
Warning: semantic-review-required; deterministic matches=5; unmatched core distributions=[]
```

Synchronization copied the Phase-3-audited full values into every
schema-identical core slot, preserved the five core distributions, and added
`# Phase 4 reconciliation: completed` to the core header.

### Semantic review of the warning and related content

Every full `file_collection` and core `distribution` was matched by identical
ID and reviewed:

| Logical mapping | Full file count | Core format/media type | Review |
|---|---:|---|---|
| Dense derived audio features | 9 | Parquet stated in identical name/description; no core enum value exists for Parquet | IDs, names, descriptions, `features/` path, and release scope agree |
| Static derived audio features | 1 | `TSV`; `text/tab-separated-values` | IDs, names, descriptions, and `features/static_features.tsv` path agree |
| Feature data dictionaries | 10 | `JSON`; `application/json` | IDs, names, descriptions, and `features/` path agree |
| Phenotype tables | 45 | `TSV`; `text/tab-separated-values` | IDs, names, descriptions, and `phenotype/` path agree |
| Phenotype dictionaries | 45 | `JSON`; `application/json` | IDs, names, descriptions, and `phenotype/` path agree |

The following related semantics were also reviewed:

- Parquet is retained in the shared `distribution_formats` value and in the
  matched collection/distribution narrative. It is not forced into
  `CoreDistribution.format` because the schema enum has no Parquet value.
- The source provides no compression, checksums, per-collection byte sizes, or
  aggregate byte size. Full and core omit those fields consistently.
- The five collection-level counts sum to 110 enumerated modeled files.
  `total_file_count` remains absent because the source does not assert that the
  modeled inventory is the complete ancillary release total. Recording counts
  and feature-element counts are different scopes and are not treated as file
  totals.
- PhysioNet access URLs are identical in the shared top-level
  `distribution_formats`, `page`, and external-resource content. Full
  collection `page`, version `3.0.0`, release datetime, and data license agree
  with the shared root facts. Core distributions have no access, version,
  release-date, license, or file-count slots, so those facts remain in their
  schema-supported shared locations.
- `dialect` is absent because the dataset mixes Parquet, TSV, and JSON and no
  single dataset-wide dialect is source-supported. `is_tabular` is identically
  `false` because the release is mixed-format and includes dense tensors as
  well as tables.
- `resources` is absent in both records, giving equal projected coverage.
  Controlled raw audio is deliberately represented as an external/raw source,
  not as a component of the v3.0.0 PhysioNet distribution.
- Repeated top-level and nested facts were reviewed: v3.0.0 DOI and immutable
  release date, not-latest status and v3.1.0 version history, registered
  feature access versus controlled raw-audio access, 833 participants versus
  approximate recording and physical-file counts, adult versus pediatric
  scope, and S1 versus S3 grant scope. No contradiction remains.

The warning is therefore fully semantically reviewed and resolved; it is an
expected reminder rather than an unresolved error.

### Final independent pair check

```text
poetry run python -m data_sheets_schema.d4d_pair_consistency --full data/d4d_concatenated/claudecode_agent/2026-07-23_gpt-5.6-sol-ultra-fast/VOICE_d4d.yaml --core data/d4d_concatenated/claudecode_agent_core/2026-07-23_gpt-5.6-sol-ultra-fast/VOICE_d4d_core.yaml
Result: PASS — 76 schema-identical slots; projected slots=['resources']
Warning: semantic-review-required; deterministic matches=5; unmatched core distributions=[]; semantically reviewed above
```

The final non-sync run proves identical presence and deeply identical parsed
content for all 76 schema-identical slots. There are no pair-validator errors.

### Final schema and term validation

After synchronization and semantic review, all four commands were rerun:

```text
Full linkml-validate: PASS — No issues found
Full linkml-term-validator: PASS — Validation passed
Core linkml-validate: PASS — No issues found
Core linkml-term-validator: PASS — Validation passed
```

### Changed artifacts and final result

Exactly these artifacts were created or changed:

- `data/d4d_concatenated/claudecode_agent/2026-07-23_gpt-5.6-sol-ultra-fast/VOICE_d4d.yaml`
- `data/d4d_concatenated/claudecode_agent_core/2026-07-23_gpt-5.6-sol-ultra-fast/VOICE_d4d_core.yaml`
- `data/d4d_concatenated/claudecode_agent_core/2026-07-23_gpt-5.6-sol-ultra-fast/VOICE_reconciliation.md`

Informational line counts after reconciliation: full 911 lines; core 620
lines. Line counts were not used as a completeness or quality gate.

Final result: both YAML documents parse and pass their applicable schema and
term validators; the pair validator passes; all warnings received documented
semantic review; shared values are deeply identical; and there are **zero
unresolved contradictions**.

Zero unresolved contradictions remain.
