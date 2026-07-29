# VOICE full/core reconciliation — 2026-07-27_claude-opus-5_rep3

Arm: **de novo with crate** (documents + RO-Crate evidence).

| Item | Value |
|---|---|
| Agent runtime | Claude Code |
| Provider | Anthropic |
| Model | claude-opus-5[1m] |
| Mode | four-phase project agent |
| Temperature | 0.0 |
| Generated | 2026-07-27 |
| Full | `data/d4d_concatenated/claudecode_agent_crate/2026-07-27_claude-opus-5_rep3/VOICE_d4d.yaml` |
| Core | `data/d4d_concatenated/claudecode_agent_crate_core/2026-07-27_claude-opus-5_rep3/VOICE_d4d_core.yaml` |
| Full schema | `src/data_sheets_schema/schema/data_sheets_schema_all.yaml`, class `Dataset` |
| Core schema | `src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml`, class `CoreDataset` |

---

## Phase 3 — source and provenance audit

### Allowed inputs actually read

Factual sources (the only ones):

- `data/preprocessed/concatenated/VOICE_preprocessed_with_crate.txt` — read in full, both the
  11-document corpus and the two included crate artifacts
  (`VOICE_crate_metadata_reduced.json`, `ai_ready_score.json`).

Structure / selection references (not fact sources):

- `src/data_sheets_schema/schema/data_sheets_schema_all.yaml` (class `Dataset`)
- `src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml` (class `CoreDataset`)
- `data/preprocessed/source_manifest.yaml`
- `data/ro-crate_packages/crate_manifest.yaml`
- `.claude/agents/d4d-provenance-guard.md`, `.claude/commands/d4d-full-core.md`,
  `.claude/commands/d4d-agent.md`

Structure for every emitted slot was derived at runtime with LinkML `SchemaView`
(`class_induced_slots`) rather than from any example record. Slot names, ranges,
cardinality, inlining behaviour and enum permissible values all come from the schemas.

### Provenance boundary — confirmed clean

- **No prior D4D record, evaluation, or reconciliation report was read.** Nothing under
  `data/d4d_concatenated/` or `data/d4d_individual/` was opened, globbed, or listed for
  content; the only directory listing performed was of the two output parent directories,
  and only to confirm that `2026-07-27_claude-opus-5_rep3` did not already exist.
- **The deliberately withheld crate artifacts were not read**:
  `VOICE_crate_mapped_d4d.yaml`, `ro-crate-datasheet.html`, `ro-crate-preview.html`,
  `ro-crate-croissant.json`. They were never opened, searched, or cited. The crate JSON-LD
  used is the reduced copy embedded in the bundle, extracted from the bundle itself (bundle
  lines 5786–16802) to a scratchpad file for parsing; no file under
  `data/ro-crate_packages/VOICE/` was accessed.
- No live web content was fetched. No prior D4D content was inherited from the parent
  conversation.
- Both file headers carry `Prior D4D factual reuse: prohibited`; the core header names both
  its document bundle and the exact same-run full record, and carries
  `Phase 4 reconciliation: completed`.

### Version scoping — hazard 1 (crate describes 3.0.0, corpus prefers 3.1.0)

The crate root entity is `ark:59853/rocrate-b2ai-voice-3.0.0`, version `3.0.0`, date published
`12/16/2025`, identifier `https://doi.org/10.13026/k81f-qr68`. The document corpus prefers
PhysioNet **v3.1.0**, published 2026-05-01, DOI `10.13026/8xbn-nq66`, a minor update over
3.0.0 with no new participants.

Scoping decision applied throughout both records:

- **Top level is v3.1.0.** `id`, `doi`, `version`, `issued`, `page`, `download_url` and
  `citation` are all 3.1.0 values. Feature record counts at the top level
  (spectrogram 29,278; mel 29,278; MFCC 29,278; torchaudio pitch 32,522; sparc EMA 28,640;
  loudness 31,855; periodicity 31,872; sparc pitch 31,872; PPGs 29,289) are the 3.1.0 figures.
- **Every crate-derived packaging fact is carried on a nested `resources` entry explicitly
  labelled release 3.0.0** (`https://doi.org/10.13026/k81f-qr68`, `version: 3.0.0`,
  `status: superseded`): total content size 12.9 GB, the `ppgs.parquet` byte size
  1,924,570,748, the presence of SHA-256 checksums on the nine feature entities, the ARK
  identifier namespace, the Merkle root hash
  `f1663e1069a9894b21202ebf05f4839b9fb82b79ba5b337df54dd18f36d3be47`, the FAIRSCAPE version
  `1.0.24`, the versioned license URL `.../view-license/3.0.0/`, the versioned DUA URL
  `.../view-dua/3.0.0/`, the copyright notice, and the crate keyword list. That resource's
  `description` states in so many words that these facts are crate-derived and scoped to
  3.0.0 rather than to 3.1.0.
- **Crate governance content that is version-neutral is carried at the top level** (biases,
  limitations, collection protocol, preprocessing, sensitive information, maintenance plan,
  ethical review, data governance committee). Where such a statement is itself
  version-bearing, it is attributed inline — for example the crate's release timeline
  (v1.0 in 2024 through v3.0.0 on 2025-12-16) appears in `collection_timeframes` prefixed
  "The upstream RO-Crate for release 3.0.0 records…", and the crate's software version
  (B2AIPrep 3.0.2) is recorded alongside, not in place of, the 3.1.0 release statement that
  the release was generated with b2aiprep v3.0.0.
- No conflict was resolved *in favour of* the crate. The two disagree on nothing that both
  assert about the same release; where they describe different releases, both values are
  retained with explicit scope.

### Cohort scoping — hazard 2 (adult vs pediatric)

The adult `b2ai-voice` dataset and the pediatric `b2ai-voice-pediatric` dataset are separate
PhysioNet projects covering distinct cohorts under separate protocols and separate ethics
approvals. The records treat them accordingly:

- The **top-level record is the adult flagship dataset**. Every top-level count (833
  participants, five North American sites, the per-feature record counts) is an adult figure.
- The **pediatric dataset is a distinct nested `resources` entry**
  (`https://doi.org/10.13026/h995-bt35`, version 1.1.0, 300 participants aged 2-18, 23,533
  derived recordings, SickKids REB, reproschema-ui collection, Synapse `syn73617068` for raw
  audio), whose description states explicitly that it is a separate PhysioNet project and not
  a version of the adult dataset. A `related_datasets` entry records the same linkage with
  `relationship_type: references` — deliberately *not* `is_version_of` or `is_new_version_of`.
- **No crate fact is attached to the pediatric cohort.** The crate describes the adult
  dataset only; the pediatric resource carries no ARK identifier, no checksum, no Merkle
  hash, no crate keyword list, and no crate governance text.
- Pediatric-specific protocol material that appears in shared slots (pediatric acoustic tasks,
  pediatric questionnaires C-VHI-10 / PVOS / PVRQOL / PHQ-A, pediatric assent and guardian
  consent, the pediatric disease cohort category) is labelled as pediatric in situ.

### Fields populated ONLY from crate evidence

These have no counterpart anywhere in the VOICE document corpus and come solely from
`VOICE_crate_metadata_reduced.json` and `ai_ready_score.json`:

| Slot | Crate source |
|---|---|
| `known_biases` (all six entries: sampling, geographic/cultural, clinical spectrum, device/environment, machine-annotation, temporal shift) | `rai:dataBiases`, with the device/site detail corroborated by the documents |
| `known_limitations` — `limitation_no_raw_audio`, `limitation_adult_only`, `limitation_deidentification_tradeoff`, `limitation_no_splits_or_uncertainty`, `limitation_governance_friction` | `rai:dataLimitations` |
| `imputation_protocols` (entire object) | `rai:dataImputationProtocol` |
| `preprocessing_strategies.preprocessing_strategy_deidentification` — the "transformed to reduce re-identification risk" framing and the sensitive-record/audio-check filtering rationale | `rai:dataManipulationProtocol` |
| `machine_annotation_tools` (tool inventory, descriptions, and the unaudited-fairness caveat) | `rai:machineAnnotationTools` |
| `labeling_strategies.data_annotation_platform` (four-platform inventory) | `rai:datannotationPlatform` |
| `labeling_strategies.annotator_demographics` (the two crate paragraphs) | `rai:annotatorDemographics` |
| `annotation_analyses` (analysis method, no inter-rater scheme, absent label-uncertainty measures) | `rai:dataAnnotationAnalysis` |
| `future_use_impacts` — the social-impact paragraph on privacy loss, voice-biometric misuse and algorithmic harms | `rai:dataSocialImpact` |
| `updates` — the static-versioning / coordinated-release / Spanish-protocol maintenance plan | `rai:dataReleaseMaintenancePlan` |
| `sensitive_elements` — the four-part crate characterisation of sensitive content | `rai:personalSensitiveInformation` |
| `ethical_reviews.ethical_review_bioethics_oversight` (Vardit Ravitsky at The Hastings Center for Bioethics) | `ethicalReview` |
| `regulatory_restrictions.governance_committee_contact` (Satrajit Ghosh) and `maintainers` governance note | `dataGovernanceCommittee` |
| IRB postal address, email `RSCH-IRB@usf.edu`, telephone `(813) 974-5638`, and the empty `irbProtocolId` | `irb` |
| `fdaRegulated: false`, `deidentified: true`, `humanSubjectExemption: No` | crate root entity |
| `confidentiality_level` evidence "Limited dataset available with Data Use Agreement" | `confidentialityLevel` |
| `contact` `https://b2ai-voice.org/contact-us/` | `contact` |
| Crate-scoped packaging facts on the v3.0.0 resource (12.9 GB, ppgs byte size, checksums, ARK ids, Merkle root, FAIRSCAPE 1.0.24, versioned license/DUA URLs, copyright notice, 55 EVI:Schema data dictionaries, 15 registered dataset entities, 117 authors) | crate root + entity graph + `ai_ready_score.json` |
| `preprocessing_strategies` computation provenance: "VOICE Features Processing" (dateCreated 01/29/2026) and "VOICE Phenotype Ingest" (dateCreated 12/16/2025), both run by "Alastair", both using B2AIPrep 3.0.2 | crate `EVI#Computation` entities |
| `creators` — the 117-author count for release 3.0.0 | `ai_ready_score.json` provenance section |

The arm note's expectation held: the crate is **genuinely additive** for VOICE. Its RAI
governance block (sampling bias, data limitations, collection protocol, sensitive-information
handling, maintenance plan, ethical review) has no counterpart in the document corpus, which
covers ethics through the IRB protocol and the DUA but never states dataset-level bias or
limitation inventories.

### Fields populated ONLY from documents

Everything not listed above, including: dataset identity and all 3.1.0 version/DOI/date facts;
`purposes`, `tasks`, `addressing_gaps`; the full `creators` roster and institutional
affiliations; `funders` (NIH RePORTER project 3OT2OD032720-01S3, core OT2OD032720, award
$4,660,942, project window 2022-09-01 to 2026-11-30; PhysioNet platform grants U24EB037545 and
R01EB030362); `instances` counts; `anomalies`; `confidential_elements`; `content_warnings`;
`subpopulations`; `relationships`; `splits`; the entire IRB-derived block (protocol title,
version history V1–V13, single-IRB arrangement, Canadian REBs, HIPAA partial waiver, STRIDES
hosting, federated learning, participant privacy, compensation, consent and withdrawal
mechanics, retention limits); `participant_compensation`; `distribution_formats` and access
mechanics; the DUA terms in `license_and_use_terms` and `ip_restrictions`; `version_access`;
`errata`; `extension_mechanism`; `variables`; `is_deidentified`; and the pediatric resource in
full.

Several fields are **corroborated by both** and were written from the documents with the crate
agreeing: the collection protocol (`rai:dataCollection` vs. the healthsheet and PhysioNet
methods section), the preprocessing pipeline (`rai:dataPreprocessingProtocol` vs. the 3.1.0
methods section), missing-data handling (`rai:dataCollectionMissingData` vs. the healthsheet),
raw-data description (`rai:dataCollectionRawData` vs. the DUA Attachment 1), use cases
(`rai:dataUseCases` vs. the healthsheet uses section), and the discouraged-use list.

### Corrections made during Phase 3

Two corrections were applied to the full record first and then propagated to core:

1. **`is_tabular` changed from `false` to `true`.** The released artefacts are Parquet — which
   the 3.1.0 documentation itself describes as "an open-source column-oriented data file
   format" — plus tab-delimited phenotype and static-feature tables. Marking the dataset
   non-tabular contradicted the core `dialect` object and the TSV distribution. Corrected for
   source fidelity and cross-record agreement.
2. **`archival` dropped from both `ExternalResource` objects.** The healthsheet answers "NA",
   not "No", to whether official archival versions of the complete dataset exist, and the crate
   makes no archival assertion. Emitting a boolean asserted more than the sources support, so
   the slot was omitted. The `future_guarantees` text retains the "NA" answers verbatim.

No fact was omitted because a source was silent and no gap was filled by inference. Fields with
no support — `total_file_count`, `total_size_bytes` and `compression` at the top level,
`subsets`, `parent_datasets`, ontology CURIEs for `Instance.data_topic` and
`Instance.data_substrate` — were left unpopulated rather than guessed.

### Internal consistency checks performed

- Repeated identifiers: `10.13026/8xbn-nq66` (3.1.0) appears in `doi`, `citation`,
  `version_access.versions_available`; `10.13026/k81f-qr68` (3.0.0) in the nested resource id,
  its `doi`, its `citation`, `version_access` and `related_datasets` — consistent everywhere.
  `10.13026/37yb-1t42` is used only as `version_access.latest_version_doi`, matching PhysioNet's
  "DOI (latest version)". `10.13026/h995-bt35`, `10.13026/mf9s-5r03`, `10.13026/249v-w155` and
  `10.57764/qb6h-em84` each appear with their correct scope.
- Release dates: 1.1 → 2025-01-17, 2.0.0 → 2025-04-16, 2.0.1 → 2025-08-18, 3.0.0 → 2025-12-16,
  3.1.0 → 2026-05-01, pediatric 1.0.0 → 2025-12-17, pediatric 1.1.0 → 2026-05-01. Identical in
  `distribution_dates`, `version_access`, the nested resources' `issued`, and the crate-derived
  timeline paragraph.
- Counts: 833 participants appears in `description`, `instances`, `sampling_strategies` context
  and the 3.0.0 resource description, always for the adult cohort; 300 / 23,533 / ages 2-18
  appear only on the pediatric resource; 391 (3.0.0 increment) and 136 (2.0 increment) appear
  only in `version_access` and `errata`.
- Enrollment targets: the three different figures in the corpus — 10,000 by 2027 (study
  metadata), ~3,000 by November 2026 (crate), 30,000 (IRB protocol and white paper) — are each
  attributed to their source in `sampling_strategies.source_data` and
  `instances.sampling_strategies.source_data`, so they read as differently scoped targets
  rather than as a contradiction.
- Access tier: PhysioNet labels the 3.1.0 page "Credentialed Access" while the licence is named
  the "Bridge2AI Voice Registered Access License", and the v1.1 page used "registered users".
  Both wordings are present in the corpus and both are recorded in `license_and_use_terms`; the
  record does not assert that one supersedes the other.
- Contacts: `DACO@b2ai-voice.org` and `https://b2ai-voice.org/contact-us/` are used
  consistently; email addresses redacted in the source capture were not reconstructed.

---

## Phase 4 — strict full/core reconciliation

### Schema-derived shared slots

Shared slots were derived at runtime from `Dataset` and `CoreDataset` via LinkML `SchemaView`;
no hand-written field list was used. The core record was **generated programmatically** from the
validated Phase 1 full record by selecting `CoreDataset`-induced slots and copying the parsed
YAML values unchanged, which makes deep identity structural rather than incidental.

- **76 schema-identical slots**, all present-in-both or absent-in-both, all deeply identical
  including every nested mapping value and list item in order. Narrative fields were **not**
  condensed, paraphrased, reordered, or omitted in core.
- **Projected slot: `resources`** (`Dataset` in full, `CoreDataset` in core). All three
  resources match by `id` with equal coverage:
  `https://doi.org/10.13026/k81f-qr68`, `https://www.synapse.org/Synapse:syn72370534/`,
  `https://doi.org/10.13026/h995-bt35`. Every schema-identical nested slot is deeply identical.
  Full-only nested slots dropped from the projection: `citation` and `file_collections`
  (the latter re-expressed as `distributions`, reviewed below).
- **Full-only top-level slots**, correctly absent from core because `CoreDataset` does not
  declare them: `file_collections`, `relationships`, `splits`, `direct_collection`,
  `collection_notifications`, `collection_consents`, `consent_revocations`,
  `participant_privacy`, `participant_compensation`, `third_party_sharing`, `variables`,
  `citation`, `related_datasets`.
- **Core-only slots**: `distributions`, `dialect`.

### Related-content mapping and semantic review

The validator emitted one warning, which marks content requiring review rather than a defect:

```
WARNING [semantic-review-required] $.file_collections <-> $.distributions:
Phase 4 must semantically review related distribution content;
deterministic matches=3, unmatched core distributions=[]
```

Review performed, top level (`FileCollection` → `CoreDistribution`):

| full `file_collections` | core `distributions` | Verdict |
|---|---|---|
| `file_collection_features` — path `features/`, `collection_type: [processed_data]`, `file_count: 11` | `distribution_features` — path `features/` | Names, paths and descriptions match verbatim except that core, which has no `file_count` slot, states "The folder holds 11 files in total" in prose. Per-feature record counts identical. No conflict. |
| `file_collection_phenotype` — path `phenotype/`, `collection_type: [processed_data, metadata]` | `distribution_phenotype` — path `phenotype/`, `format: TSV`, `media_type: text/tab-separated-values` | Descriptions identical. Core adds format and media type, both consistent with full's "tab-delimited phenotype tables". No conflict. |
| `file_collection_metadata` — path `metadata/`, `collection_type: [metadata]` | `distribution_metadata` — path `metadata/` | Descriptions identical. No conflict. |

Review performed, nested v3.0.0 resource:

| full | core | Verdict |
|---|---|---|
| `file_collection_v300_features` — `file_count: 9`, `total_bytes: 1924570748` | `distribution_v300_features` — `bytes: 1924570748` | `total_bytes` and `bytes` agree exactly; the nine-file count is preserved in the core description alongside the byte figure. No conflict. |
| `file_collection_v300_phenotype` — `file_count: 6` | `distribution_v300_phenotype` — `format: TSV`, `media_type: text/tab-separated-values` | Descriptions identical; both state six EVI Dataset entities of media type `text/tab-separated-values`, matching the crate. No conflict. |

Other checks required by the Phase 4 procedure:

- **`total_file_count` / `total_size_bytes` vs. distribution-level values** — both slots are
  unpopulated in the full record (no source states a 3.1.0 total), so there is nothing to
  contradict. The only byte figure anywhere in either record is the crate's `ppgs.parquet` size,
  which is scoped to 3.0.0 in both files and identical across them.
- **`dialect`, formats and `is_tabular` agree** — `dialect` (core-only) declares a tab delimiter
  and column names in the first row; `distribution_phenotype` declares `TSV` /
  `text/tab-separated-values`; the full record's phenotype description says "tab-delimited";
  `is_tabular: true` in both. All four agree, and all four match the documented usage
  `pd.read_csv("demographics.tsv", sep="\t", header=0)`.
- **Compression** — asserted nowhere in either record; no conflict.
- **Access URLs and release scope** — access URLs live in `distribution_formats`, a
  schema-identical slot that is byte-identical across the pair; `distributions` carry paths
  only, so no URL can diverge between the two representations.
- **Top-level identity/version facts vs. resources, version history and distributions** —
  top-level 3.1.0 / `10.13026/8xbn-nq66` / 2026-05-01 agrees with the `version_access` 3.1.0
  entry; resource 3.0.0 / `10.13026/k81f-qr68` / 2025-12-16 agrees with the `version_access`
  3.0.0 entry, the `related_datasets` `is_new_version_of` link and the crate's own
  `datePublished`; the pediatric resource 1.1.0 / `10.13026/h995-bt35` / 2026-05-01 agrees with
  its `version_access` entry.
- **Historical vs. current releases distinguished, not treated as contradictions** — v3.0.0
  carries `status: superseded`; the HealthDataNexus v1.0 distribution is described as "an
  earlier version"; the healthsheet's "published at the end of November 2024" statement and its
  "current v.2.0.0 dataset" study-population wording are both explicitly attributed to that
  earlier release rather than presented as facts about 3.1.0.

**Zero unresolved contradictions within or between the two records.**

### Commands run

```bash
poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_all.yaml \
  -C Dataset data/d4d_concatenated/claudecode_agent_crate/2026-07-27_claude-opus-5_rep3/VOICE_d4d.yaml

poetry run linkml-term-validator validate-data \
  data/d4d_concatenated/claudecode_agent_crate/2026-07-27_claude-opus-5_rep3/VOICE_d4d.yaml \
  --schema src/data_sheets_schema/schema/data_sheets_schema_all.yaml --target-class Dataset

poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml \
  -C CoreDataset data/d4d_concatenated/claudecode_agent_crate_core/2026-07-27_claude-opus-5_rep3/VOICE_d4d_core.yaml

poetry run linkml-term-validator validate-data \
  data/d4d_concatenated/claudecode_agent_crate_core/2026-07-27_claude-opus-5_rep3/VOICE_d4d_core.yaml \
  --schema src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml --target-class CoreDataset

poetry run python -m data_sheets_schema.d4d_pair_consistency \
  --full data/d4d_concatenated/claudecode_agent_crate/2026-07-27_claude-opus-5_rep3/VOICE_d4d.yaml \
  --core data/d4d_concatenated/claudecode_agent_crate_core/2026-07-27_claude-opus-5_rep3/VOICE_d4d_core.yaml \
  --sync-core

poetry run python -m data_sheets_schema.d4d_pair_consistency \
  --full data/d4d_concatenated/claudecode_agent_crate/2026-07-27_claude-opus-5_rep3/VOICE_d4d.yaml \
  --core data/d4d_concatenated/claudecode_agent_crate_core/2026-07-27_claude-opus-5_rep3/VOICE_d4d_core.yaml
```

### Files changed

- `data/d4d_concatenated/claudecode_agent_crate/2026-07-27_claude-opus-5_rep3/VOICE_d4d.yaml`
  — created in Phase 1; two Phase 3 corrections applied (`is_tabular`, `archival`).
- `data/d4d_concatenated/claudecode_agent_crate_core/2026-07-27_claude-opus-5_rep3/VOICE_d4d_core.yaml`
  — created in Phase 2, regenerated from the corrected full record in Phase 3. `--sync-core`
  in Phase 4 made no changes.
- `data/d4d_concatenated/claudecode_agent_crate_core/2026-07-27_claude-opus-5_rep3/VOICE_reconciliation.md`
  — this report.

No pre-existing file was overwritten; the version directory did not exist before this run.

### Final results

| Check | Result |
|---|---|
| Full — LinkML schema validation (`Dataset`) | PASS — no issues found |
| Full — ontology term validation | PASS |
| Core — LinkML schema validation (`CoreDataset`) | PASS — no issues found |
| Core — ontology term validation | PASS |
| Pair consistency, `--sync-core` | PASS — 76 schema-identical slots; projected `resources`; 1 semantic-review warning |
| Pair consistency, final independent run | PASS — 76 schema-identical slots; projected `resources`; 1 semantic-review warning, reviewed above |
| Semantic review of related content | Complete — 3 top-level and 2 nested distribution mappings reviewed, zero conflicts |
| Provenance audit | Clean — no prior generated YAML read; no withheld crate artifact read; no live web content |

Line counts (informational metadata only, not a quality gate): full 2,358 lines; core 1,636 lines.
