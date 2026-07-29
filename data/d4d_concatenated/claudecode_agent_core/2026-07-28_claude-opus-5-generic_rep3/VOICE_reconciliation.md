# VOICE full/core reconciliation - 2026-07-28_claude-opus-5-generic_rep3

Arm: BASELINE (input documents only)
Prompt: `src/download/prompts/d4d_generic_arm_prompt.md` (identical text for all projects)
Runtime: Claude Code / Anthropic / claude-opus-5[1m], temperature 0.0
Declared input bundle: `data/preprocessed/concatenated/VOICE_preprocessed.txt`
Manifest: `data/preprocessed/source_manifest.yaml`

Outputs:

- Full: `data/d4d_concatenated/claudecode_agent/2026-07-28_claude-opus-5-generic_rep3/VOICE_d4d.yaml`
- Core: `data/d4d_concatenated/claudecode_agent_core/2026-07-28_claude-opus-5-generic_rep3/VOICE_d4d_core.yaml`

## Pinned referent

`Dataset` admits one referent. The referent pinned for this run is **the Bridge2AI-Voice
adult dataset** - the PhysioNet project `b2ai-voice`, "Bridge2AI-Voice: An ethically-sourced,
diverse voice dataset linked to health information" - taken at its current release, v3.1.0
(published 2026-05-01, DOI 10.13026/8xbn-nq66). The stable top-level `id` is the
latest-version DOI `https://doi.org/10.13026/37yb-1t42`.

Rationale from the declared bundle: this entity is the one the bundle documents most
directly and from the most independent sources - three PhysioNet captures (v1.1, v3.0.0,
v3.1.0), the project documentation site with its healthsheet, the Data Transfer and Use
Agreement, the IRB protocol governing its collection, the NIH RePORTER project record, and
two publications describing protocol development and application feasibility.

Consequences held consistently across both records:

- Prior adult releases (v1.0 on Health Data Nexus, v1.1, v2.0.0, v2.0.1, v3.0.0) and the
  controlled-access raw-audio collection on Synapse are carried as `resources`, with their
  own identifiers, versions and dates.
- The **Bridge2AI-Voice Pediatric Dataset** (PhysioNet `b2ai-voice-pediatric` v1.1.0, DOI
  10.13026/h995-bt35, 300 participants aged 2-18, 23,533 recordings, SickKids) is a distinct
  PhysioNet project collected under a separate protocol and REB, not a version of the
  referent. It is represented in the full record as a `related_datasets` entry with
  `relationship_type: supplements`. `related_datasets` is not a `CoreDataset` slot, so this
  content is absent from core by schema design, not by omission.
- Facts that are explicitly pediatric-scoped in the sources (SickKids recruitment,
  reproschema-ui collection, guardian consent and assent, adult-only compensation) are
  recorded in the slots where the sources state them and carry their scope in the text.

## Phase 3 - source and provenance audit

### Provenance

No prior generated D4D record was read, searched, or cited. Factual inputs were the declared
bundle and the manifest only; structural inputs were `data_sheets_schema_all.yaml` (class
`Dataset`) and `data_sheets_schema_core_all.yaml` (class `CoreDataset`), traversed with
LinkML `SchemaView` rather than by copying any existing record. One directory listing of
`data/d4d_concatenated/claudecode_agent/` was produced incidentally while checking bundle
size; it returned version-directory names only and no record content was opened. No
evaluation report, test fixture, schema `d4d:docExample`, or live web content was consulted.

### Corrections applied to the full record, then re-projected into core

1. **Model-memory-derived identifiers removed.** Two `Organization.id` values in `creators`
   had been written as ROR URIs (`https://ror.org/032db5x82`, `https://ror.org/02r109517`).
   Neither appears anywhere in the declared bundle; they came from model memory, which the
   provenance guard forbids as a factual source. Replaced with local `d4d:` identifiers
   (`d4d:voice_org_usf_morsani`, `d4d:voice_org_wcm_englander`). A third such value on the
   funder had already been removed when `grantor` was converted to a schema-required string
   reference.

2. **Top-level `conforms_to` removed as mis-scoped.** The BIDS v1.9.0 statement in the
   project documentation describes the conversion of the raw audio files and questionnaire
   data (the `b2ai-voice-audio` tree), not the layout of the feature-only PhysioNet release,
   which is organised as `features/`, `phenotype/` and `metadata/`. Asserting it as a
   dataset-level conformance claim over-scoped it. The fact is retained, correctly scoped, in
   `preprocessing_strategies` (`d4d:voice_preprocessing_structure`).

3. **Enrollment-target disagreement represented rather than resolved.** The IRB protocol
   ("Sample Size 30 000 participants"; 5,000 at USF with the remainder from other
   institutions) and the audiomics white paper ("publicly available database of 30 000 human
   voices") disagree with the project documentation ("flagship ... dataset of 10,000 voices";
   "Enrollment Count (Anticipated by 2027): 10,000"). Both figures, with their sources, are
   now stated in `sampling_strategies`; neither was silently selected.

4. **Site-count wording corrected to the source's own inconsistency.** The IRB protocol says
   both "11 different academic sites across the US" (6.1) and "Data will be collected at USF
   and 11 other participating institutions" (6.2). The record previously asserted only the
   second reading; it now reports both formulations.

### Source disagreements identified and how they are represented

- **Hosting platform.** The healthsheet answers describe distribution and maintenance through
  Health Data Nexus (T-CAIREM, University of Toronto) at `healthdatanexus.ai`, while the
  PhysioNet captures show the current releases hosted by PhysioNet / MIT Laboratory for
  Computational Physiology. Both are recorded: Health Data Nexus as the v1.0 release resource
  and as a maintainer, PhysioNet as publisher, page, and maintainer of the current releases.
  No merge was performed.
- **Version scope inside one source.** The documentation page mixes version scopes in a single
  capture ("The current v.2.0.0 dataset contains only adult populations", a v2.0.0 citation
  block, "Methods of De-identification for v3.0.0", "no external data is released in this
  v3.0.0 release"). Version-specific statements are carried with their stated version;
  version-neutral de-identification and access statements are carried without a version claim.
- **Access tier wording.** PhysioNet v1.1 is labelled "Restricted Access" with a registered-user
  policy; v3.0.0 and v3.1.0 are labelled "Credentialed Access" with a credentialed-user policy;
  the documentation calls the feature-only tier "Registered Access". Each is recorded at the
  level where it is stated rather than normalised to one term.
- **Task counts.** Documentation reports 22 acoustic tasks in the adult protocol; the
  feasibility publication reports 29 questionnaires and tasks (34 when confounders are
  stratified) available in the app during June-July 2023. Different scopes; both retained with
  their scope, and the feasibility study is separately flagged as not contributing audio data.
- **Recording sites vs participating institutions.** "Five recording sites included in the
  dataset" (documentation, PhysioNet) is kept distinct from the 9-12 participating institutions
  named in the IRB protocol and documentation collaborator list.
- **Grant number variants.** Clean values `OT2OD032720`, `3OT2OD032720-01S1` and
  `3OT2OD032720-01S3` were used. Two corrupted extraction artefacts in the documentation
  capture (`3TF-OT2ActfOD032720Projectf01S1`, `Award #3Tf-OTOD03272001S2`) were not carried.

### Values deliberately omitted for lack of support

`total_file_count`, `total_size_bytes`, per-distribution byte counts and checksums,
`compression`, `is_tabular`, `status`, `created_by` / `modified_by`, `created_on` /
`last_updated_on`, `download_url`, `imputation_protocols`, `other_tasks`, `subsets`, and
ontology-term slots (`data_topic`, `data_substrate`, `unit`) are absent because the declared
bundle does not state them. Contact email addresses on the documentation site are redacted in
the preprocessed text (`[email protected]`) and were not reconstructed; only
`DACO@b2ai-voice.org`, which appears literally in the PhysioNet notices, is recorded.

`creators.credit_roles` for the two co-PIs is limited to `conceptualization`,
`funding_acquisition`, `project_administration` and `supervision` - the subset consistent both
with the CRediT statements in the feasibility publication's author-contributions section and
with the documentation's description of them as co-leads and co-principal investigators.

## Phase 4 - strict full/core reconciliation

Shared slots were derived at runtime from `Dataset` and `CoreDataset` with LinkML
`SchemaView`; no hand-written field list was used. Core was produced as a mechanical
projection of the Phase 3-audited full record - the full document was round-tripped and every
key not induced on `CoreDataset` was dropped - so deep identity of shared content holds by
construction rather than by later synchronisation. `--sync-core` was therefore not needed and
was not run.

Deterministic result:

```
PASS: 76 schema-identical slots; projected slots=['resources']
WARNING [semantic-review-required] $.file_collections <-> $.distributions:
  Phase 4 must semantically review related distribution content;
  deterministic matches=3, unmatched core distributions=[]
```

Slot counts (informational metadata, not a quality gate): full 75 populated top-level slots
(1393 lines); core 64 populated top-level slots (1232 lines).

Full-only slots, all absent from `CoreDataset` by schema: `citation`, `relationships`,
`splits`, `direct_collection`, `collection_notifications`, `collection_consents`,
`consent_revocations`, `participant_privacy`, `participant_compensation`,
`third_party_sharing`, `variables`, `file_collections`, `related_datasets`.

Core-only slots: `distributions` (projection of `file_collections`) and `dialect`.

### Projected slot: `resources`

`resources` is `Dataset` in full and `CoreDataset` in core. All six resource entries match by
`id` with equal coverage, and every nested slot used (`id`, `name`, `title`, `version`, `doi`,
`issued`, `page`, `publisher`, `license`, `description`) is induced on both classes, so the
projection is deeply identical with no full-only nested slots dropped.

### Semantic review of related content (resolves the validator warning)

`file_collections` -> `distributions`, three deterministic matches, no unmatched core entries:

| full `FileCollection` | core `CoreDistribution` | review |
|---|---|---|
| `features` (path `features`, `collection_type: [processed_data]`) | `features` (path `features`) | Names, paths and descriptions identical. Format unset in core: the folder mixes Parquet tensors with TSV, and `FormatEnum` has no Parquet member, so no format claim is made. `collection_type` is full-only and is dropped by the projection. No conflict. |
| `phenotype` (path `phenotype`, `collection_type: [processed_data, metadata]`) | `phenotype` (path `phenotype`, `format: TSV`, `media_type: text/tab-separated-values`) | Format and media type agree with the full record's own description ("Each TSV file is paired with a JSON data dictionary") and with the documented loader call `pd.read_csv("demographics.tsv", sep="\t", header=0)`. No conflict. |
| `metadata` (path `metadata`, `collection_type: [metadata]`) | `metadata` (path `metadata`) | Identical name, path and description; Parquet again unrepresentable in `FormatEnum`. No conflict. |

Cross-checks performed:

- `total_file_count` and `total_size_bytes` are absent from full and no distribution-level
  `bytes` value exists in core, so there is no scope mismatch to reconcile. The sources give
  per-feature record counts (29,278 spectrogram/Mel/MFCC, 32,522 torchaudio pitch, 28,640
  SPARC EMA, 31,855 loudness, 31,872 periodicity and pitch, 29,289 PPG for v3.1.0), which are
  record counts rather than file counts and are recorded in `instances`, not as file counts.
- `dialect` (tab delimiter, header present) is consistent with the TSV distribution and with
  the documented loader call; it does not contradict any full-record statement.
- `compression` is unset in both records and in every distribution; no source states one.
- Top-level identity, version and access facts (`id`, `doi` 10.13026/8xbn-nq66, `version`
  3.1.0, `issued` 2026-05-01, `page`, `publisher`, `license`) agree with `version_access`
  (latest-version DOI 10.13026/37yb-1t42, per-version list), with `distribution_dates`, with
  `distribution_formats`, and with the `resources` entries for the prior releases. The
  historical releases carry their own versions, DOIs and dates and are not treated as
  contradicting the current release.
- Repeated facts were checked for internal consistency within each file: 833 participants
  (abstract, healthsheet, `instances`); five recording sites; five disease cohort categories
  plus controls; compensation $40 / $80 / max $120; single labeler per instance; raw audio
  withheld from the registered-access release and distributed via Synapse under controlled
  access. No internal contradiction found in either record.

### Outcome

No divergence between the full and core records was found. Every schema-identical shared slot
is present in both with deeply identical parsed content, the one projected slot is fully
covered, and the one related-content mapping has been semantically reviewed with zero
unresolved contradictions.

## Commands run

```bash
poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_all.yaml \
  -C Dataset data/d4d_concatenated/claudecode_agent/2026-07-28_claude-opus-5-generic_rep3/VOICE_d4d.yaml
poetry run linkml-term-validator validate-data \
  data/d4d_concatenated/claudecode_agent/2026-07-28_claude-opus-5-generic_rep3/VOICE_d4d.yaml \
  --schema src/data_sheets_schema/schema/data_sheets_schema_all.yaml --target-class Dataset
poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml \
  -C CoreDataset data/d4d_concatenated/claudecode_agent_core/2026-07-28_claude-opus-5-generic_rep3/VOICE_d4d_core.yaml
poetry run linkml-term-validator validate-data \
  data/d4d_concatenated/claudecode_agent_core/2026-07-28_claude-opus-5-generic_rep3/VOICE_d4d_core.yaml \
  --schema src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml --target-class CoreDataset
poetry run python -m data_sheets_schema.d4d_pair_consistency \
  --full data/d4d_concatenated/claudecode_agent/2026-07-28_claude-opus-5-generic_rep3/VOICE_d4d.yaml \
  --core data/d4d_concatenated/claudecode_agent_core/2026-07-28_claude-opus-5-generic_rep3/VOICE_d4d_core.yaml
poetry run d4d provenance record --project VOICE --method claudecode_agent \
  --label 2026-07-28_claude-opus-5-generic_rep3 \
  --input-bundle data/preprocessed/concatenated/VOICE_preprocessed.txt
```

## Final results

| Check | Result |
|---|---|
| Full schema validation (`Dataset`) | pass |
| Full ontology term validation | pass |
| Core schema validation (`CoreDataset`) | pass |
| Core ontology term validation | pass |
| Schema-derived pair consistency | PASS, 76 schema-identical slots, projected `resources` |
| Related-content semantic review | complete, 3/3 mapped, 0 contradictions |
| Prior-D4D reuse | none |
