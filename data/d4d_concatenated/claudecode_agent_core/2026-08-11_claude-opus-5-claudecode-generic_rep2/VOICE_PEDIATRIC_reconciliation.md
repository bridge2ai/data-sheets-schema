# VOICE_PEDIATRIC full/core reconciliation

- **Version label:** `2026-08-11_claude-opus-5-claudecode-generic_rep2`
- **Arm:** BASELINE (input documents only)
- **Runtime / provider / model:** Claude Code / Anthropic / claude-opus-5
- **Mode:** four-phase project agent, generic prompt
- **Prompt:** `src/download/prompts/d4d_generic_arm_prompt.md`
- **Declared input bundle:** `data/preprocessed/concatenated/VOICE_PEDIATRIC_preprocessed.txt`
- **Source manifest:** `data/preprocessed/source_manifest.yaml`
- **Full record:** `data/d4d_concatenated/claudecode_agent/2026-08-11_claude-opus-5-claudecode-generic_rep2/VOICE_PEDIATRIC_d4d.yaml`
- **Core record:** `data/d4d_concatenated/claudecode_agent_core/2026-08-11_claude-opus-5-claudecode-generic_rep2/VOICE_PEDIATRIC_d4d_core.yaml`

| | value |
|---|---|
| Full top-level slots populated | 69 |
| Core top-level slots populated | 57 |
| Schema-derived shared slots (identity) | 78 |
| Schema-derived shared slots (projected) | 1 (`resources`) |
| Full schema validation | pass |
| Core schema validation | pass |
| Full term validation | pass |
| Core term validation | pass |
| Pair consistency (final, no `--sync-core`) | PASS |
| `d4d download scope --check --strict` | in scope |

## Referent

`Dataset` admits one referent. The record is about the **Bridge2AI-Voice
Pediatric Dataset**, the PhysioNet project whose current release is version
1.1.0. The record `id` is the project-level DOI
`https://doi.org/10.13026/mf9s-5r03`, which is also the `referent_id` the
manifest declares for this project. The release DOI for version 1.1.0,
`10.13026/h995-bt35`, is carried in `citation` and `version_access` rather than
as the record identifier, and the two-DOI arrangement is named in the record's
top-level `source_caveats`.

The Bridge2AI-Voice adult dataset is declared by the manifest as related but
distinct. It is expressed once, through `related_datasets`, with
`relationship_type: references` and a description stating that it is a separate
PhysioNet project from a distinct cohort under a different protocol and is not a
version of this dataset. No adult-scoped figure is asserted of this dataset
anywhere in either record.

## Phase 3 — source and provenance audit

### Provenance boundary

No prior full or core D4D record, from any arm, label or date, was read, opened,
grepped or consulted. Nothing under `data/d4d_concatenated/`,
`data/d4d_individual/` or `data/ro-crate_packages/` was read at any point. The
factual inputs were the declared bundle and the source manifest; the structural
inputs were `data_sheets_schema_all.yaml` (class `Dataset`) and
`data_sheets_schema_core_all.yaml` (class `CoreDataset`), read through
`SchemaView` so that names, ranges, cardinality, inlining and enum membership
came from the schema rather than from any example. No `d4d:docExample` value was
copied. No web content was fetched.

`d4d api prompts check --strict` reports 10 prompt files, 0 not at their pin;
the generic arm prompt this run was launched under is canonical.

### Scope discipline applied to the bundle

The bundle contains six documents. Only one — the PhysioNet paediatric release
page (`physionet_pediatric_1_1_0`) — is specific to this dataset. The other five
(the USF IRB protocol, the b2ai-voice.org documentation, the NIH RePORTER
capture, the data transfer and use agreement, and the documentation repository
README) describe the Bridge2AI-Voice programme, and the documentation in
particular was written around the adult cohort. The audit therefore separated
three categories:

1. **Paediatric-specific statements** — asserted directly (300 participants aged
   2-18, 23,533 recordings, SickKids enrolment, reproschema-ui on tablets, the
   feature file inventory, the v1.0.0/v1.1.0 release history, SickKids REB
   approval, the Synapse raw-audio route).
2. **Programme-level statements that the sources apply to the paediatric arm** —
   asserted with the attribution stated in the value (paediatric protocol age
   bands, paediatric questionnaires, the ReproSchema-UI → REDCap → BIDS pipeline,
   the registered/controlled access mechanisms, the access agreement's use
   restrictions, parental permission and assent, "compensation will be provided
   to the adult population only").
3. **Statements explicitly scoped to the adult release** — *not* asserted, and
   named in the record's top-level `source_caveats` so the omission is visible:
   833 participants, five recording sites, a 12-month collection window, iPad and
   Avid AE-36 microphone hardware, HIPAA de-identification answers, the Health
   Data Nexus distribution and semi-annual update cadence, dataset versions 2.0.0
   and 3.0.0, and the Bridge2AI Summer School use. `collection_timeframes`,
   `existing_uses`, `labeling_strategies`, `use_repository`,
   `data_protection_impacts` and `content_warnings` are consequently absent
   rather than filled from adult evidence.

### Source disagreements represented rather than resolved

| what | how it is represented |
|---|---|
| Two DOIs (project-level `mf9s-5r03`, release `h995-bt35`) | both recorded; project-level as `id`/`doi`, release DOI in `citation` and `version_access`; explained in top-level `source_caveats` |
| Three NIH identifiers (`3OT2OD032720-01S1` in the release acknowledgement, `OT2OD032720` in the documentation, `3OT2OD032720-01S3` in the RePORTER capture) | three separate `Grant` entries under one `FundingMechanism`, with a `source_caveats` stating they are not merged; the garbled documentation footer string is not transcribed |
| SickKids lead investigator: Jennifer Sui (documentation) vs Alistair Johnson (IRB Annex C) | both named in `creators` and `data_collectors`, with `source_caveats` stating the sources differ |
| Ethics review body: protocol revision V2 says the paediatric cohort came "under single IRB"; the same protocol's body and the release say the Canadian sites hold a separate REB approval | both recorded in `ethical_reviews.source_caveats` |
| Institution lists: the documentation's 12 collaborators vs Annex C's partially overlapping list | documentation list used for `affiliations`; the divergence stated in the consortium creator's `source_caveats` |
| Consortium affiliations vs PhysioNet platform support (NIBIB/NHLBI/OD, `U24EB037545`, `R01EB030362`) | a second `FundingMechanism` scoped to the platform, with a `source_caveats` stating it funds PhysioNet rather than this dataset |

### Shape and slot-filling audit

- Structured slots are filled before prose: `grants[].grant_number`,
  `affiliations[]`, `variables[].variable_name`, `distribution_dates[].release_dates`,
  `version_access.versions_available`, `at_risk_populations.guardian_consent`,
  `human_subject_research.special_populations` carry their content structurally
  rather than in narrative.
- Enum values were taken from the schema: `collection_type`,
  `relationship_type`, `bias_type`, `limitation_type`, `data_use_permission`,
  `confidentiality_level`, `role` (`CreatorOrMaintainerEnum`), `data_type`
  (`VariableTypeEnum`), `format` (`FormatEnum`), `media_type`
  (`MediaTypeEnum`). `FormatEnum` has no Parquet member, so the parquet files
  carry no `format` and are described instead; `DistributionFormat.format` is a
  plain string and does carry "Parquet".
- Evidence commentary is in `source_caveats` (18 occurrences in full, 15 in
  core after the full-only slots are dropped), never in `notes`; `notes` is
  unused in both records.
- `Creator.principal_investigator` has a non-inlined `Person` range, so it
  carries an identifier string; the person's affiliation is carried in the
  creator's own `affiliations`, and the identity in `name`/`description`. No
  commentary is embedded in any name, identifier or affiliation value.
- Identifier syntax (#402): every `id` is either an absolute IRI (the record id,
  `b2aiprep`) or a CURIE on the schema-declared `d4d:` prefix. No bare tokens
  and no undeclared prefixes.

### Internal consistency

Counts (300 participants; 23,533 recordings; per-file n=23533 vs n=23532),
versions and dates (1.0.0 on 2025-12-17, 1.1.0 on 2026-05-01), the licence and
data use agreement names, the access mechanisms, the SickKids REB, and the file
inventory are each stated once per slot and agree wherever they recur across
`description`, `instances`, `anomalies`, `missing_data_documentation`,
`distribution_dates`, `version_access`, `updates`, `license`,
`license_and_use_terms`, `regulatory_restrictions` and `data_governance`.

### Corrections made in Phase 3

Two, both applied to the full record first and then propagated to core:

1. `preprocessing_strategies[1].used_software[0]` (b2aiprep) carried a shorter
   entry than the same-`id` entry in `preprocessing_strategies[0]`. The two now
   describe the identical software identically, so an entity resolving on the
   b2aiprep id sees one description rather than two.
2. `ethical_reviews[0].source_caveats` was extended to record the single-IRB
   versus separate-REB tension described above, which the first pass noted only
   as a missing approval number.

No fact was changed and nothing was removed; both corrections are additions or
alignments. Neither record contains a value whose only support was the other
record.

## Phase 4 — strict full/core reconciliation

### Shared slots

Derived at runtime with `SchemaView` over `Dataset` and `CoreDataset`: **78
schema-identical slots** and **1 projected slot** (`resources`). No hand-written
field list was used.

All 78 identity slots are present in both records or absent from both, and every
one that is present has deeply identical parsed YAML content, including nested
mappings and list order. Narrative fields (`description`, every
`*_details`/`*_description` string, `source_caveats`) are byte-identical: core
condenses, paraphrases, reorders and omits nothing.

`resources` is populated in neither record, so the projection is vacuously
consistent; the dataset's components are carried as `file_collections` in full
and as `distributions` in core (below) rather than as sub-datasets.

### Full-only and core-only slots

13 populated full slots have no counterpart in `CoreDataset` and are correctly
absent from core: `citation`, `related_datasets`, `file_collections`,
`variables`, `relationships`, `direct_collection`, `collection_notifications`,
`collection_consents`, `consent_revocations`, `participant_privacy`,
`participant_compensation`, `third_party_sharing`, `data_governance`.

69 − 13 = 56 carried slots, plus core-only `distributions` = 57 core slots.
`dialect` is core-only and is left absent: the release mixes columnar Parquet,
tab-delimited text and JSON, so no single dialect is true of the dataset.

### Related-content mapping and semantic review

`file_collections` (full) → `distributions` (core). The validator reports 12
deterministic matches, 0 at collection level and 12 at nested resource level,
with no unmatched core distributions. The projection is deliberately
**file-level**: `CoreDistribution`'s slots (`path`, `bytes`, `md5`, `sha256`,
`format`, `encoding`, `media_type`) are properties of a file, and the three full
collections (`features`, `phenotype`, `metadata`) are folders rather than
downloadable forms. Folder membership is not lost — it is the leading path
segment of every distribution.

Semantic review of the mapping, performed rather than inferred from the warning:

- **Names and paths.** All 12 distributions carry the same `name` and `path` as
  the corresponding `File` in `file_collections[].resources[]`; 11 are under
  `features/` and 1 under `phenotype/`.
- **Descriptions.** Byte-identical to the full `File` descriptions, so the
  dimensions, window and hop sizes, FFT size, Mel-bin count, articulator list,
  frequency ranges, frame rate and per-file counts agree exactly between the
  records.
- **Formats.** `format: TSV` is carried on exactly the three plain-text tables in
  both records; the nine Parquet files carry no `format` in either, because
  `FormatEnum` declares no Parquet member. `is_tabular: true` is identical in
  both records and is consistent with columnar Parquet plus tab-delimited text.
- **Compression, checksums, byte counts, access URLs.** The bundle states none
  of these for any file, so all are absent from both records. No `compression`
  is claimed anywhere.
- **Counts and sizes.** `total_file_count` and `total_size_bytes` are absent from
  the full record because the bundle states neither, so there is no scope
  mismatch to reconcile against the distribution list. The `metadata/` folder
  contributes no distribution because the bundle names no file in it — the
  folder is described in full's `file_collections` and its content is not
  asserted in core.
- **Release scope.** Every distribution belongs to release 1.1.0. The
  `audio_quality_metrics.tsv` and per-recording metadata additions are attributed
  to version 1.1 identically in both records, and the historical 1.0.0 release is
  distinguished from the current one in `version_access` and `updates` rather
  than presented as a contradiction.

No contradiction was found within either record or between them.

### Commands run

```bash
poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_all.yaml \
  -C Dataset  data/d4d_concatenated/claudecode_agent/2026-08-11_claude-opus-5-claudecode-generic_rep2/VOICE_PEDIATRIC_d4d.yaml
poetry run linkml-term-validator validate-data \
  data/d4d_concatenated/claudecode_agent/2026-08-11_claude-opus-5-claudecode-generic_rep2/VOICE_PEDIATRIC_d4d.yaml \
  --schema src/data_sheets_schema/schema/data_sheets_schema_all.yaml --target-class Dataset
poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml \
  -C CoreDataset data/d4d_concatenated/claudecode_agent_core/2026-08-11_claude-opus-5-claudecode-generic_rep2/VOICE_PEDIATRIC_d4d_core.yaml
poetry run linkml-term-validator validate-data \
  data/d4d_concatenated/claudecode_agent_core/2026-08-11_claude-opus-5-claudecode-generic_rep2/VOICE_PEDIATRIC_d4d_core.yaml \
  --schema src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml --target-class CoreDataset
poetry run python -m data_sheets_schema.d4d_pair_consistency --full <full> --core <core> --sync-core
poetry run python -m data_sheets_schema.d4d_pair_consistency --full <full> --core <core>
poetry run d4d download scope --check --project VOICE_PEDIATRIC --strict
poetry run d4d api prompts check --strict
```

### Files changed

- `.../claudecode_agent/2026-08-11_claude-opus-5-claudecode-generic_rep2/VOICE_PEDIATRIC_d4d.yaml` (Phase 1, then the two Phase 3 corrections)
- `.../claudecode_agent_core/2026-08-11_claude-opus-5-claudecode-generic_rep2/VOICE_PEDIATRIC_d4d_core.yaml` (Phase 2, then one Phase 4 `--sync-core`, which also appended `# Phase 4 reconciliation: completed`)
- `.../claudecode_agent_core/2026-08-11_claude-opus-5-claudecode-generic_rep2/VOICE_PEDIATRIC_reconciliation.md` (this file)

### Final results

Both records pass schema and term validation. The pair passes
`d4d_pair_consistency` without `--sync-core` as an independent final check: 78
schema-identical slots agree deeply, and the one projected slot and the one
related-content mapping have been reviewed above with zero unresolved
contradictions.

### Not performed by this agent

The live provenance record (`d4d provenance record`) was **not** written by this
agent: the launch instruction directed that the launcher writes it. Consequently
`d4d runs validate` and `d4d runs check --strict` were also not run here, since
both operate on the provenance record. The two YAML artifacts and this report
are final as of the last command above; nothing has been written to them since.
