# VOICE full/core reconciliation — 2026-07-28_claude-opus-5-crateonly-deprimed_rep1

- **Arm:** CRATE-ONLY (RO-Crate evidence alone; document corpus withheld)
- **Runtime / provider / model:** Claude Code / Anthropic / claude-opus-5[1m]
- **Mode:** four-phase project agent, crate-only, de-primed. Temperature 0.0.
- **Declared input bundle:** `data/preprocessed/concatenated/VOICE_crate_only.txt`
  (9,966 lines; `VOICE_crate_metadata_reduced.json` + `ai_ready_score.json`)
- **Source manifest:** not used — this arm declares a single source bundle.
- **Full:** `data/d4d_concatenated/claudecode_agent_crate_only/2026-07-28_claude-opus-5-crateonly-deprimed_rep1/VOICE_d4d.yaml`
- **Core:** `data/d4d_concatenated/claudecode_agent_crate_only_core/2026-07-28_claude-opus-5-crateonly-deprimed_rep1/VOICE_d4d_core.yaml`

## Phase 3 — source and provenance audit

### Provenance boundary

Factual inputs were the declared bundle only. Structure was derived at runtime
from `Dataset` in `data_sheets_schema_all.yaml` and `CoreDataset` in
`data_sheets_schema_core_all.yaml` via `SchemaView` (induced slots, ranges,
cardinality, inlining, enums), not from any example record.

No prior full or core D4D was read, from any arm, label or date. Nothing under
`data/d4d_concatenated/` was opened; only directory names were listed to confirm
the target version directory was free. No `*_crate_d4d.yaml` or
`*_crate_mapped_d4d.yaml` under `data/ro-crate_packages/` was read. No
evaluation report, test fixture, or `d4d:docExample` value was used. No live web
content was fetched. Schema `d4d:docExample` annotations were treated as
illustrations only.

Non-factual inputs read: `.claude/agents/d4d-provenance-guard.md`,
`.claude/commands/d4d-full-core.md`, `.claude/commands/d4d-agent.md`, both LinkML
schemas, and `src/data_sheets_schema/d4d_pair_consistency.py`.

### Literal verification against the bundle

Every scalar asserted in the two records was checked back against the crate JSON
programmatically:

| Check | Result |
| --- | --- |
| DOI, license URL, DUA URL, dataset name, version, citation, project contact, grant number, b2aiprep URL and version, Merkle root | all present verbatim in bundle |
| `creators` (117 entries) vs crate `author` roster | exact match, same order |
| `keywords` (18) vs crate root `keywords` | exact match |
| 15 `resources` ids / versions / `conforms_to_schema` / byte counts | 0 mismatches |
| 15 core `distributions` ids / paths / bytes / sha256 | 0 mismatches; 11 checksums present |
| verbatim `rai:*` blocks (sensitive info, timeframes, annotator demographics, annotation platforms, machine annotation tools) | byte-identical to source |
| feature-collection `total_bytes` = 13,788,089,083 | equals sum of the 9 feature files |
| `total_size_bytes` = 13,789,023,450 | equals sum of all 11 sized files |

### Source-supported content back-ported into full during Phase 3

Three items supported by the bundle were absent from the first Phase 1 draft and
were added to the full record, then re-projected into core:

1. `conforms_to: https://w3id.org/ro/crate/1.2` — the crate declares RO-Crate 1.2
   conformance and `ai_ready_score.json` describes the release as a
   self-contained RO-Crate.
2. `distribution_formats[0].description` — RO-Crate packaging and integrity facts
   from `ai_ready_score.json`: 15 data entities, 55 declared column schemas, 2
   computations, 1 software component, checksums on 11 of 17 counted files, and
   the package-level Merkle root hash.
3. `external_resources[0].description` — the PhysioNet platform reference
   (`associatedPublication[1]`, Goldberger et al. 2000), which the single scalar
   `citation` slot could not carry alongside the dataset citation.

No fact was removed. No value was changed on the basis of any generated record.

### Source disagreements resolved

| Finding | Resolution |
| --- | --- |
| `…dataset-feature-sparc-periodicity` has `name` "sparc_loudness.parquet" but `contentUrl` `features/sparc_periodicity.parquet` and a periodicity column schema | `@id` + `contentUrl` + schema agree against the lone `name`; used `sparc_periodicity.parquet`, and recorded the conflicting crate `name` in the resource description |
| `…dataset-feature-torchaudio-pitch` has `name` "torchaudio_spectrogram.parquet" but `contentUrl` `features/torchaudio_pitch.parquet` | same resolution; used `torchaudio_pitch.parquet`, conflict recorded in the description |
| `…dataset-phenotype-task` has `name` "VOICE Questionnaire Tables", duplicating the questionnaire entity | no `contentUrl` to arbitrate; the crate `name` was kept verbatim and the duplication flagged in the description. This is the one duplicate name among the 15 documented entities |
| `…dataset-feature-sparc-pitch` carries `datePublished` 08/18/2025 while the other 14 entities and the crate root carry 12/16/2025 | recorded as a per-file anomaly in that resource's description; the release date 2025-12-16 was kept as the 3.0.0 date, matching the crate root and the release history |
| Crate `contentSize` "12.9 GB" vs itemised sum 13,789,023,450 bytes | 13,789,023,450 bytes = 12.842 GiB, which rounds to the stated 12.9 under a GiB reading. The exact itemised sum was recorded in `total_size_bytes`; the crate's verbatim "12.9 GB" string was kept in `distribution_formats[0].description` |
| Two `EVI:Schema` entities share `@id` `…schema-phenotype-confounders` (one named Confounders, one named Demographics), and `…schema-phenotype-voice-perception` appears twice | not resolvable from the crate; recorded in the demographics resource description rather than guessing a column list |
| Both computations record `runBy` / `prov:wasAssociatedWith` "Alastair", an unqualified first name; the author roster contains "Alistair Johnson" (different spelling) | not mapped to any person or `data_collectors` entry — the crate supplies no identifier and the spellings differ. Left unasserted |
| `copyrightNotice` says "Copyright © 2026 University of South Florida" while `datePublished` is 12/16/2025; `computation-b2ai-voice-features-processing` has `dateCreated` 01/29/2026, after the release date | recorded verbatim in `license_and_use_terms` / `ip_restrictions` without reconciliation; these are internal inconsistencies of the source, not of the record |

### Evidence gaps deliberately left unpopulated

- Crate `hasPart` and `isPartOf` are empty arrays despite 15 documented data
  entities, and `prov:wasGeneratedBy`, `prov:wasDerivedFrom`, `derivedFrom` and
  `usedByComputation` are empty on every file while `generatedBy` is populated.
  Provenance was taken from `generatedBy` only.
- All 15 file entities carry placeholder descriptions ("a datafile description",
  "A Dataset description"). These were **not** copied. Resource descriptions were
  authored from the declared column schemas, paths, sizes, checksums and
  generating computations.
- `irbProtocolId` and `completeness` are empty strings; `format` is empty on all
  nine Parquet files. No IRB protocol number is asserted; Parquet is attributed
  to the file names and stated as such, and `format` is omitted on those
  distributions (`FormatEnum` has no Parquet member).
- `total_file_count` was left absent: four of the 15 entities are table *groups*
  with no file listing, and `ai_ready_score.json` implies a 17-file count, so no
  defensible file count exists.
- `dialect` was left absent from core: the phenotype schemas declare separator
  `\t` while the nine Parquet schemas declare `,`, so no single dataset-level
  dialect is supported.
- Omitted for want of evidence: `subsets`, `splits` counts, `existing_uses`,
  `use_repository`, `other_tasks`, `collection_notifications`,
  `consent_revocations`, `participant_compensation`, `content_warnings`,
  `extension_mechanism`, `data_use_permission`, `hipaa_compliant`,
  `language`, `issued`/`created_on`, `download_url`, per-cohort counts.

### Internal consistency

Version 3.0.0 is consistent across the crate root, all 15 file entities, the
license and DUA URLs, and the citation. `deidentified: true` agrees with
`is_deidentified.identifiable_elements_present: false`; `humanSubjectResearch:
Yes` agrees with `involves_human_subjects: true`; `confidentialityLevel`
"Limited dataset available with Data Use Agreement" maps to
`ConfidentialityLevelEnum: restricted` and agrees with the registered-access
statements in `rai:personalSensitiveInformation`. The 833 participants of release
3.0.0 and the ~3,000-participant target for November 2026 are different scopes,
not a contradiction, and are recorded as such.

## Phase 4 — strict full/core reconciliation

Shared slots were derived at runtime with `SchemaView` from `Dataset` and
`CoreDataset`; no hand-written field list was used.

- **Schema-identical shared slots: 76** — present in both records or absent from
  both, with deeply identical parsed YAML including narrative fields. Core
  condenses, paraphrases, reorders and omits nothing.
- **Projected slots: `resources`** — 15 items, `Dataset` in full and
  `CoreDataset` in core. Coverage is equal by `id` (all 15 ARK identifiers match)
  and every schema-identical nested slot is deeply identical
  (`id`, `name`, `description`, `version`, `is_tabular`, `conforms_to_schema`).
  The full-only nested slot `total_size_bytes` is omitted from the core
  projection, as the core schema requires.
- **Full-only top-level slots (not in `CoreDataset`):** `citation`,
  `collection_consents`, `direct_collection`, `file_collections`,
  `participant_privacy`, `related_datasets`, `relationships`, `splits`,
  `third_party_sharing`, `total_size_bytes`, `variables`.
- **Core-only slot populated:** `distributions` (15). `dialect` omitted, see above.

### Related-content semantic review: `file_collections` ↔ `distributions`

The validator reports 0 deterministic matches because the two representations are
at different granularities by design: full `file_collections` describes two
directory-level collections, core `distributions` describes the 15 individual
data entities. The mapping was reviewed field by field:

| Full `file_collections` | Core `distributions` | Result |
| --- | --- | --- |
| `features/`, `file_count: 9`, `total_bytes: 13,788,089,083` | 9 distributions with `path` under `features/` | count matches (9 = 9); byte sum matches exactly; all 9 carry sha256; `format`/`media_type` absent on both sides (Parquet unrepresentable in `FormatEnum`) |
| `phenotype/`, no `file_count`, no `total_bytes` | 6 distributions: 2 with `path` under `phenotype/`, bytes and sha256; 4 group entities with no path, bytes or checksum, `format: TSV`, `media_type: text/tab-separated-values` | consistent — the collection deliberately declares no count or total precisely because 4 of its 6 entities are unsized groups |

No conflicts in names, descriptions, paths, formats, compression, checksums, byte
counts, access URLs or release scope. `compression` is absent on both sides.
Distribution names and descriptions are identical to the corresponding
`resources` entries. `total_size_bytes` (13,789,023,450) equals the sum of all
distribution `bytes`. Release scope is uniform: every entity is version 3.0.0.
`is_tabular: true` agrees across full, core and all 15 nested resources, and is
consistent with the 55 declared column schemas.

### Commands

```bash
poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_all.yaml -C Dataset \
  data/d4d_concatenated/claudecode_agent_crate_only/2026-07-28_claude-opus-5-crateonly-deprimed_rep1/VOICE_d4d.yaml
poetry run linkml-term-validator validate-data \
  data/d4d_concatenated/claudecode_agent_crate_only/2026-07-28_claude-opus-5-crateonly-deprimed_rep1/VOICE_d4d.yaml \
  --schema src/data_sheets_schema/schema/data_sheets_schema_all.yaml --target-class Dataset
poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml -C CoreDataset \
  data/d4d_concatenated/claudecode_agent_crate_only_core/2026-07-28_claude-opus-5-crateonly-deprimed_rep1/VOICE_d4d_core.yaml
poetry run linkml-term-validator validate-data \
  data/d4d_concatenated/claudecode_agent_crate_only_core/2026-07-28_claude-opus-5-crateonly-deprimed_rep1/VOICE_d4d_core.yaml \
  --schema src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml --target-class CoreDataset
poetry run python -m data_sheets_schema.d4d_pair_consistency --full <full> --core <core> --sync-core
poetry run python -m data_sheets_schema.d4d_pair_consistency --full <full> --core <core>
poetry run d4d provenance record --project VOICE --method claudecode_agent_crate_only \
  --label 2026-07-28_claude-opus-5-crateonly-deprimed_rep1 \
  --input-bundle data/preprocessed/concatenated/VOICE_crate_only.txt
```

### Files changed

- `…/claudecode_agent_crate_only/2026-07-28_claude-opus-5-crateonly-deprimed_rep1/VOICE_d4d.yaml`
  (Phase 1, plus the three Phase 3 back-ports)
- `…/claudecode_agent_crate_only_core/2026-07-28_claude-opus-5-crateonly-deprimed_rep1/VOICE_d4d_core.yaml`
  (Phase 2, re-derived after the Phase 3 back-ports, then `--sync-core`)
- this report

No file outside the declared output directories was written.

## Results

| Check | Result |
| --- | --- |
| Full — `linkml-validate` (`Dataset`) | PASS |
| Full — `linkml-term-validator` | PASS |
| Core — `linkml-validate` (`CoreDataset`) | PASS |
| Core — `linkml-term-validator` | PASS |
| Pair consistency, `--sync-core` | PASS, 76 schema-identical slots |
| Pair consistency, final independent run | PASS, 76 schema-identical slots |
| Unresolved contradictions within or between the records | none |

`--sync-core` changed no value: the core record already carried the full
record's values byte-for-byte, and the run only re-serialised the file and
appended the `# Phase 4 reconciliation: completed` header line. The single
validator warning is the mandatory `semantic-review-required` marker for
`file_collections` ↔ `distributions`; that review is recorded above and found no
conflict.

Informational metadata (never a quality gate): full 1,110 lines / 70 top-level
slots; core 1,137 lines / 60 top-level slots. Core is longer than full despite
having fewer top-level slots because `distributions` adds a per-file view that
has no full-record counterpart, while `resources` is projected down.

## Assessment of the crate evidence

The RO-Crate is unusually rich on responsible-AI narrative: the `rai:*` block
alone supports biases, limitations, collection, preprocessing, annotation,
imputation, missingness, sensitive information, social impact and the
maintenance plan, largely verbatim. Identity, licensing, access, ethics
oversight, funding and versioning are all directly stated. File-level evidence is
strong for the nine Parquet features (paths, byte counts, checksums, column
schemas, generating computation) and weak for the phenotype side, where four of
six entities are unsized, unchecksummed groups.

The main quality defects in the source are placeholder file descriptions on all
15 entities, three name/`@id`/`contentUrl` conflicts, two duplicated schema
`@id`s, empty `hasPart`/`isPartOf`/`derivedFrom` wiring, an empty
`irbProtocolId`, and empty `format` fields on every Parquet file. None of these
blocked extraction, but each narrowed what could be asserted, and each is
recorded in the record itself rather than papered over.
