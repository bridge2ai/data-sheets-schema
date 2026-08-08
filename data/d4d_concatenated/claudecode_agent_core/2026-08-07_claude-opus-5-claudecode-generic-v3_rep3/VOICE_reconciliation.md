# VOICE — Phase 3/4 reconciliation report

Run label: `2026-08-07_claude-opus-5-claudecode-generic-v3_rep3`
Arm: BASELINE (input documents only)
Runtime: Claude Code · Provider: Anthropic · Model: `claude-opus-5` · Reasoning effort: `high` · Temperature 0.0
Mode: four-phase project agent, generic prompt
Prompt: `src/download/prompts/d4d_generic_arm_prompt.md`

Artifacts:

- Full: `data/d4d_concatenated/claudecode_agent/2026-08-07_claude-opus-5-claudecode-generic-v3_rep3/VOICE_d4d.yaml`
- Core: `data/d4d_concatenated/claudecode_agent_core/2026-08-07_claude-opus-5-claudecode-generic-v3_rep3/VOICE_d4d_core.yaml`

Declared factual input (the only source of dataset facts):

- `data/preprocessed/concatenated/VOICE_preprocessed.txt` (11 documents, listed in
  `data/preprocessed/source_manifest.yaml` under `VOICE`)

Schemas:

- Full: `src/data_sheets_schema/schema/data_sheets_schema_all.yaml`, class `Dataset`
- Core: `src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml`, class `CoreDataset`

---

## Phase 3 — source and provenance audit

### Provenance boundary

No prior generated D4D record was read, opened, grepped or consulted, from any arm, label
or date. Nothing under `data/d4d_concatenated/` was read other than this run's own two
output files, and no `*_crate_d4d.yaml` or `*_crate_mapped_d4d.yaml` under
`data/ro-crate_packages/` was touched. Structure was derived at runtime from the two
LinkML schemas via `SchemaView` (`class_induced_slots` over `Dataset` and `CoreDataset`),
not from any example record. No `d4d:docExample` value was copied. Every factual value in
both records traces to the declared bundle.

The bundle's tenth document (`physionet_b2ai-voice-pediatric_1.1.0_2026-07-24.txt`) is a
source document selected by the current manifest for the `VOICE` bundle, so reading it is
permitted; it was read only to establish that the pediatric dataset is a distinct dataset
and to obtain its identifier for the relationship slot. The separate
`VOICE_PEDIATRIC_preprocessed.txt` bundle was not read.

### Referent

`Dataset` admits one referent. The referent chosen is **the adult Bridge2AI-Voice flagship
dataset as published on PhysioNet, at its current version 3.1.0** (published 2026-05-01,
DOI `10.13026/8xbn-nq66`, 833 participants across five North American sites). This is the
referent the declared bundle best supports: seven of its eleven documents describe this
dataset or the protocol that produced it, and three of them are PhysioNet release records
for it. The same referent is held consistently across both records — identical `id`,
`name`, `title`, `version`, `doi`, `issued`, `page`, `publisher` and `license`.

### Relationship to the pediatric dataset

The Bridge2AI-Voice Pediatric Dataset is **not** represented as part of this dataset, and
no nested object anywhere in either record describes it. It appears only once, in the full
record's `related_datasets` list, as a `DatasetRelationship` with
`target_dataset: https://doi.org/10.13026/h995-bt35` and
`relationship_type: references` — the relationship the evidence directly supports, since
the PhysioNet record for the adult dataset carries an explicit cross-reference note to the
pediatric project. The accompanying `description` records what the bundle establishes about
the distinctness: a separate PhysioNet project rather than a version of this one, a distinct
cohort (participants aged 2–18 recruited at the Hospital for Sick Children), collected with
`reproschema-ui` under a pediatric protocol, approved by the Research Ethics Board at the
Hospital for Sick Children rather than the USF IRB, with its own DOI, and produced by the
same consortium under the same NIH award.

`related_datasets` is a full-only slot: `CoreDataset` does not declare it. The pediatric
dataset therefore does not appear in the core record at all, which is the correct projection
rather than an omission.

Statements in the bundle that describe pediatric collection (the `reproschema-ui` platform,
the pediatric acoustic tasks marked `Peds` in Table 2, the pediatric questionnaires in
Table 3, pediatric assent and guardian consent, the SickKids recruitment) were kept out of
this record's substantive slots, with two deliberate exceptions where the source states them
as provisions of the shared IRB protocol governing the adult study: `at_risk_populations`
records the protocol's rule that pediatric participants are enrolled only through the
pediatric sites and not at USF, and `known_limitations` records that this dataset is
adult-only. Both are scoped explicitly.

### Source disagreements represented rather than resolved

The bundle contains genuine disagreements. Each is represented as what the evidence states,
in `source_caveats` on the slot concerned, rather than silently collapsed:

| Subject | Disagreement | Where recorded |
|---|---|---|
| Grant number | `3OT2OD032720-01S3` (NIH RePORTER) vs `3OT2OD032720-01S1` (PhysioNet) vs `1OT2OD032720-01` (feasibility publication) vs core `OT2OD032720`, plus two corrupted renderings on the documentation site | `funders[0].grants` — four separate `Grant` objects; corrupted forms noted in `funders[0].source_caveats`, not recorded as grant numbers |
| Target enrollment | 10,000 (study metadata, documentation site) vs 30,000 (IRB protocol, audiomics white paper) | `sampling_strategies[0].source_caveats` |
| "High volume expert clinic" | >50 patients/month from the same disease category (documentation) vs >1000 patients/year (IRB protocol) | `sampling_strategies[0].source_caveats`; the documentation definition is in `strategies` |
| Collection timeframe | 12 months (healthsheet) vs 4-year prospective study (IRB) vs 2022-09-01 to 2026-11-30 award period (NIH RePORTER) | `collection_timeframes[0]`; no `start_date`/`end_date` asserted |
| Collaborating institutions | 12-institution collaborator list (documentation) vs IRB Annex C, which adds Massachusetts Eye and Ear and Emory University; protocol text variously says 11 other sites, 12 institutions, 14 institutions | `creators[0].source_caveats` |
| HIPAA status of the data | DTUA characterises the transferred data as PII "not covered under HIPAA"; documentation states the HIPAA de-identification rules were applied to the release | `regulatory_restrictions.source_caveats` — recorded as describing two different objects, not reconciled |
| Access policy wording | v1.1 "registered users who sign the specified data use agreement" vs v3.0.0/v3.1.0 "credentialed users who sign the DUA" | `distribution_formats[0].description` |
| Distribution platform | Documentation's healthsheet answer names Health Data Nexus; PhysioNet is the current channel | `distribution_formats[2].source_caveats`; top-level `source_caveats` |
| Participant counts | 306 (v1.0), +136 (v2.0), +391 (v3.0.0), 833 (v3.0.0 and v3.1.0) | `instances[0].source_caveats`; only the current 833 is asserted as `counts` |
| Recording total | Documentation site gives ~61,937 voice-derived recordings for v3.0; PhysioNet gives only per-feature row counts | top-level `source_caveats`; no aggregate recording count asserted |

### Stale, mis-scoped and unsupported assertions checked

- **IRB number 004890 is not this dataset's approval.** It belongs to the separate
  Bridge2AI-Voice *application feasibility study* run at the USF Health Voice Center between
  2023-06-05 and 2023-07-28. It is therefore **not** recorded as an IRB approval number; the
  fact and the reason are stated in `ethical_reviews[0].source_caveats`. The bundle gives no
  approval number for the data acquisition protocol itself, so none is asserted.
- **The feasibility publication's CRediT author contributions were not transplanted onto the
  dataset creators.** Those roles attach to that article, not to the dataset, so
  `credit_roles` is left empty on every `Creator` rather than filled by inference.
- **Version-scoped statements are kept scoped.** The documentation's study metadata says "The
  current v.2.0.0 dataset contains only adult populations" and gives Spanish protocol status
  "for v2.0.0"; these are represented as the release-history and limitation statements they
  are, not as claims about v3.1.0.
- **Per-feature row counts are v3.1.0 values**, taken from the 3.1.0 record (29278 / 32522 /
  28640 / 31855 / 31872 / 31872 / 29289), not the different 3.0.0 values. Each `File`
  description names the version the count belongs to.
- **Phenotype file inventory is the v3.1.0 inventory.** `adhd_adult`, `psychiatric_history`
  and `ptsd_adult` moved from `diagnosis` to `questionnaire` between 3.0.0 and 3.1.0; the
  3.1.0 placement is used and the move is noted on the `phenotype/diagnosis` collection.
- **Redacted contact addresses.** Preprocessing replaced e-mail addresses on the documentation
  capture with the literal placeholder `[email protected]`. No mailbox was invented; the only
  address recorded is `DACO@b2ai-voice.org`, which appears in full on the PhysioNet pages. The
  redaction is disclosed in the top-level `source_caveats` and in
  `maintainers[2].maintainer_details`.
- **Audio file naming** is reported exactly as the documentation renders it
  (`sub-<participant_id>/ses-<participant_id>/audio`) rather than normalised to the BIDS
  convention the reader might expect.

### Shape audit

Checked against the same contract as the API pipeline's audit phase:

- No prose where the schema requires a list. Every multivalued string slot
  (`irb_approval`, `special_populations`, `regulatory_compliance`, `special_protections`,
  `guardian_consent`, `warnings`, `restrictions`, `regulatory_restrictions`, `release_dates`,
  `versions_available`, `examples`, `tool_accuracy`, `annotator_demographics`,
  `external_resources`, `keywords`) holds discrete items.
- Every enum value is one the schema defines: `collection_type`, `file_type`, `format`,
  `media_type`, `bias_type`, `limitation_type`, `data_use_permission`, `hipaa_compliant`,
  `confidentiality_level`, `CreatorOrMaintainerEnum`, `DatasetRelationshipTypeEnum`,
  `VariableTypeEnum`.
- No commentary embedded in a name, identifier or affiliation value.
- Structured slots are filled before prose: `creators` carries `affiliations` as
  `Organization` objects and `principal_investigator` as a typed reference; `funders` carries
  four `Grant` objects rather than a sentence listing award numbers; software is carried in
  `used_software` objects rather than named only in prose.
- `notes` is unused in both records. Evidence commentary lives exclusively in
  `source_caveats`, on ten slots plus the record root.

Two shape defects were found and fixed during this phase:

1. `content_warnings[0]` carried evidence commentary (that the PhysioNet releases removed the
   free-speech transcripts the warning is about) in `description`. Moved to `source_caveats`.
2. Three `distribution_formats[*].format` values held prose rather than format strings
   (`"Apache Parquet binary feature files and tab-separated phenotype tables with JSON data
   dictionaries"`, `"Raw audio waveforms"`, `"Feature-only dataset accessible with cloud
   compute rather than by download"`). Shortened to `Apache Parquet, TSV, JSON` and
   `WAV audio`; the third was removed entirely, since it describes an access mode rather than
   a format, and its content was moved into that distribution's `description`.

Both fixes were applied to the **full** record first, which is canonical, and the core record
was then regenerated from it. Both files were re-validated after the corrections.

### Phase 2 back-port

Phase 2 surfaced no fact that was present in the sources but missing from the full record, so
no back-port into the full record was required on evidentiary grounds. The only content Phase 2
added is the core-only `distributions` slot, which has no full-schema counterpart.

---

## Phase 4 — strict full/core reconciliation

### Shared-slot derivation

Shared slots were derived at runtime with LinkML `SchemaView`, by intersecting the induced
slots of `Dataset` and `CoreDataset` and comparing induced range and cardinality. No
hand-written field list was used.

- **78** schema-identical shared slots (same induced range, same cardinality).
- **1** projected slot: `resources` — `Dataset` in full, `CoreDataset` in core.
- **2** core-only slots: `distributions`, `dialect`.
- **17** full-only slots.

### Identity of schema-identical slots

The core record was generated by copying each populated schema-identical slot's parsed value
from the Phase 3-audited full record, so parsed-YAML deep identity holds by construction,
including nested mapping values and list item order. Narrative fields were **not** condensed,
paraphrased, reordered or omitted in core.

- **64** schema-identical slots are populated, and are present in both records.
- **14** schema-identical slots are unpopulated, and are absent from both:
  `annotation_analyses`, `compression`, `conforms_to_class`, `conforms_to_schema`,
  `created_by`, `created_on`, `download_url`, `imputation_protocols`, `is_tabular`,
  `last_updated_on`, `modified_by`, `notes`, `status`, `was_derived_from`.

Presence therefore matches exactly in both directions.

### Projected slot

`resources` is `Dataset` in full and `CoreDataset` in core. It is unpopulated in both, so
coverage is trivially equal and there is nothing to match by `id`. The validator reports
`projected slots=['resources']` with no discrepancy.

### Related, non-identical content — semantic review

The validator's one warning is `semantic-review-required` on
`$.file_collections <-> $.distributions`, with 8 deterministic matches and no unmatched core
distributions. That warning marks work to be done, not work done, so the review is recorded
here.

Full `file_collections` (8 `FileCollection` objects) map one-to-one onto core `distributions`
(8 `CoreDistribution` objects). Matching is by `id`, and each pair shares `id`, `name`, `path`
and `description` verbatim:

| id | full `FileCollection` | core `CoreDistribution` | reviewed |
|---|---|---|---|
| `b2ai-voice:collection/features` | `collection_type: processed_data`, 11 `File` resources | same id/name/path/description; no `format` | consistent — the collection mixes Apache Parquet and TSV, so no single `format` is asserted in core; the per-file formats survive in full |
| `b2ai-voice:collection/metadata` | `collection_type: metadata`, no `File` resources | same id/name/path/description; no `format` | consistent — the source names one Parquet file and its dictionary but no file names, so neither record enumerates files |
| `b2ai-voice:collection/phenotype-demographics` | 1 TSV `File` | `format: TSV`, `media_type: text/tab-separated-values` | consistent |
| `b2ai-voice:collection/phenotype-confounders` | 1 TSV `File` | `format: TSV`, `media_type: text/tab-separated-values` | consistent |
| `b2ai-voice:collection/phenotype-diagnosis` | 18 TSV `File` | `format: TSV`, `media_type: text/tab-separated-values` | consistent |
| `b2ai-voice:collection/phenotype-enrollment` | 3 TSV `File` | `format: TSV`, `media_type: text/tab-separated-values` | consistent |
| `b2ai-voice:collection/phenotype-questionnaire` | 13 TSV `File` | `format: TSV`, `media_type: text/tab-separated-values` | consistent |
| `b2ai-voice:collection/phenotype-task` | 7 TSV `File` | `format: TSV`, `media_type: text/tab-separated-values` | consistent |

Core `format`/`media_type` were set only where every `File` in the corresponding full
collection carries that format, so no core value contradicts a full value. `CoreDistribution`
has no `collection_type` or nested `resources`, so the collection type and the per-file
inventory are full-only content, correctly dropped from the core projection rather than
flattened into prose.

Further related-content checks, all clean:

- **Counts.** `total_file_count` and `total_size_bytes` are unset in full, and no
  `CoreDistribution` asserts `bytes`. Nothing to compare, and no count is invented. Neither
  record asserts a file count or byte size anywhere, because the bundle states none.
- **Checksums.** No `md5`, `sha256` or `hash` is asserted in either record; the bundle
  publishes none.
- **Access URLs and release scope.** The three access channels are carried identically in the
  shared `distribution_formats` slot in both records (PhysioNet `.../b2ai-voice/3.1.0/`,
  Synapse `syn72370534`, Health Data Nexus), and the release dates are carried identically in
  the shared `distribution_dates` slot. The full record's `file_collections` and the core
  record's `distributions` both describe the v3.1.0 PhysioNet layout only, so their release
  scope agrees.
- **`dialect`, formats and `is_tabular`.** `dialect` is core-only and is deliberately
  **unset**: the release mixes Apache Parquet binaries with tab-delimited text, so a
  dataset-level dialect would over-claim. `is_tabular` is unset in both for the same reason,
  so there is no dialect/`is_tabular`/format disagreement to resolve.
- **Identity, version and access facts against version history.** `version: 3.1.0`, `doi`,
  `issued: 2026-05-01`, `page` and `license` agree with `version_access.versions_available`
  (which lists 3.1.0 at 2026-05-01 with DOI `10.13026/8xbn-nq66`), with
  `distribution_dates.release_dates`, and with `distribution_formats[0]`. All of these are
  schema-identical shared slots, so they are byte-identical between the two records.
  `version_access.latest_version_doi` is the PhysioNet project-level concept DOI
  (`10.13026/37yb-1t42`), which the source distinguishes from the version DOI; the two are
  not in conflict.
- **Historical vs current releases.** Statements about v1.0, v1.1, v2.0, v2.0.1 and v3.0.0 are
  carried only in `version_access.version_details`, `distribution_dates.release_dates`,
  `instances[0].source_caveats` and the full-only `related_datasets`, each with the version
  named. They are treated as history, not as contradictions of the current release values.

### Result

No divergence was found between the two records. Every schema-identical shared slot is
present in both or absent from both, with deeply identical parsed values; the one projected
slot is empty in both; and all related, non-identical content has been mapped and reviewed
with zero unresolved contradictions within or between the records.

---

## Commands run

```bash
# Phase 1 / Phase 3 — full record
poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_all.yaml \
  -C Dataset data/d4d_concatenated/claudecode_agent/2026-08-07_claude-opus-5-claudecode-generic-v3_rep3/VOICE_d4d.yaml
poetry run linkml-term-validator validate-data \
  data/d4d_concatenated/claudecode_agent/2026-08-07_claude-opus-5-claudecode-generic-v3_rep3/VOICE_d4d.yaml \
  --schema src/data_sheets_schema/schema/data_sheets_schema_all.yaml --target-class Dataset

# Phase 2 / Phase 3 — core record
poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml \
  -C CoreDataset data/d4d_concatenated/claudecode_agent_core/2026-08-07_claude-opus-5-claudecode-generic-v3_rep3/VOICE_d4d_core.yaml
poetry run linkml-term-validator validate-data \
  data/d4d_concatenated/claudecode_agent_core/2026-08-07_claude-opus-5-claudecode-generic-v3_rep3/VOICE_d4d_core.yaml \
  --schema src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml --target-class CoreDataset

# Phase 4 — schema-derived pair consistency
poetry run python -m data_sheets_schema.d4d_pair_consistency \
  --full data/d4d_concatenated/claudecode_agent/2026-08-07_claude-opus-5-claudecode-generic-v3_rep3/VOICE_d4d.yaml \
  --core data/d4d_concatenated/claudecode_agent_core/2026-08-07_claude-opus-5-claudecode-generic-v3_rep3/VOICE_d4d_core.yaml

# Provenance
poetry run d4d provenance record --project VOICE --method claudecode_agent \
  --label 2026-08-07_claude-opus-5-claudecode-generic-v3_rep3 \
  --input-bundle data/preprocessed/concatenated/VOICE_preprocessed.txt \
  --prompt src/download/prompts/d4d_generic_arm_prompt.md
poetry run d4d runs validate --label 2026-08-07_claude-opus-5-claudecode-generic-v3_rep3 --project VOICE
poetry run d4d runs check --strict --label 2026-08-07_claude-opus-5-claudecode-generic-v3_rep3
```

`--sync-core` was not needed: the core record was generated from the Phase 3-audited full
record, so schema-identical slots were already deeply identical, and the validator passed on
its first independent run.

## Final results

| Check | Result |
|---|---|
| Full — `linkml-validate` (`Dataset`) | No issues found |
| Full — `linkml-term-validator` | Validation passed |
| Core — `linkml-validate` (`CoreDataset`) | No issues found |
| Core — `linkml-term-validator` | Validation passed |
| Pair consistency | PASS — 78 schema-identical slots, projected slots `['resources']`, 1 semantic-review warning (reviewed above) |
| Full populated top-level slots | 77 |
| Core populated top-level slots | 65 |
| Shared populated slots | 64 |
| Full-only populated slots | 13 (`citation`, `collection_consents`, `collection_notifications`, `consent_revocations`, `direct_collection`, `file_collections`, `participant_compensation`, `participant_privacy`, `related_datasets`, `relationships`, `splits`, `third_party_sharing`, `variables`) |
| Core-only populated slots | 1 (`distributions`) |
| Divergence found | None |

Line counts, reported as informational metadata and not as a quality gate: full 1987 lines,
core 1143 lines.
