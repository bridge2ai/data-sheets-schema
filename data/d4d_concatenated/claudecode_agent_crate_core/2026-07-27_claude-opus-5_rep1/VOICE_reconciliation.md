# VOICE full/core reconciliation — 2026-07-27_claude-opus-5_rep1

Arm: **de novo with crate** (documents + RO-Crate evidence).

| | |
|---|---|
| Agent runtime | Claude Code |
| Provider | Anthropic |
| Model | claude-opus-5[1m] |
| Mode | four-phase project agent |
| Temperature | 0.0 |
| Generated | 2026-07-27 |
| Full | `data/d4d_concatenated/claudecode_agent_crate/2026-07-27_claude-opus-5_rep1/VOICE_d4d.yaml` |
| Core | `data/d4d_concatenated/claudecode_agent_crate_core/2026-07-27_claude-opus-5_rep1/VOICE_d4d_core.yaml` |
| Source bundle | `data/preprocessed/concatenated/VOICE_preprocessed_with_crate.txt` |
| Source manifest | `data/preprocessed/source_manifest.yaml` |
| Crate manifest | `data/ro-crate_packages/crate_manifest.yaml` |
| Full schema | `data_sheets_schema_all.yaml`, class `Dataset` |
| Core schema | `data_sheets_schema_core_all.yaml`, class `CoreDataset` |

Line counts, informational only and not a quality gate: full 3303, core 2178.

---

## Phase 1 — full D4D from the crate-augmented bundle

Structure was derived at runtime from class `Dataset` with LinkML `SchemaView`,
following `is_a`, `slots`, `attributes`, `slot_usage`, class ranges, cardinality
and inlining. No prior D4D record was read as a template or as evidence.

Two structural facts had to be recovered from the schema rather than assumed,
and both produced validation failures on the first pass:

- Class-ranged slots that are **scalar** (`Creator.principal_investigator`,
  `FundingMechanism.grantor`, `EthicalReview.contact_person`,
  `EthicalReview.reviewing_organization`, `LicenseAndUseTerms.contact_person`,
  `ExportControlRegulatoryRestrictions.governance_committee_contact`) are **not
  inlined**; they take an identifier string, not an embedded object. Only the
  multivalued class-ranged slots (`Creator.affiliations`,
  `FundingMechanism.grants`, `used_software`) and the `Dataset`-level slots that
  explicitly declare `inlined: true` take embedded objects. All embedded
  `Person`/`Organization` objects in those six positions were replaced with
  identifier references, and the biographical, postal and contact detail they
  carried was moved into the surrounding `description` / `*_details` text so
  that no evidence was lost.
- `recommended_mitigation` exists on `DatasetLimitation` but not on
  `DatasetBias`; the corresponding text was moved to
  `DatasetBias.mitigation_strategy`.

`data_topic` and `data_substrate` were left unpopulated: their `values_from`
prefixes (`B2AI_TOPIC`, `B2AI_SUBSTRATE`) resolve to the Bridge2AI standards
registry, and the allowed source bundle contains no registry term identifiers.

## Phase 2 — core D4D from the same sources plus the Phase 1 full

`CoreDataset`'s field inventory and every nested class shape were derived from
the core schema at runtime. Core was built by projecting the Phase 1 full record
across the shared slot set and then adding the two core-only slots,
`distributions` and `dialect`, from the source bundle.

Phase 2 found **no source-supported fact that was missing from the full record**
within core's field inventory, so nothing had to be back-ported on that account.
The one class of content that core carries and full cannot is the
distribution-level file inventory: `CoreDistribution` has `bytes`, `sha256`,
`md5`, `hash`, `path`, `format`, `media_type`, `encoding` and `compression`,
whereas full's `FileCollection` has only aggregate `file_count` and
`total_bytes`. The per-file byte counts and SHA-256 digests recorded in the
RO-Crate therefore appear at file granularity in core and in aggregate plus
prose in full.

`FormatEnum` and `MediaTypeEnum` have no Parquet member, so the nine Parquet
feature distributions carry `path`, `bytes` and `sha256` but no `format` or
`media_type`. This is a schema coverage gap, not missing evidence.

## Phase 3 — source and provenance audit

### Provenance

Every factual input path is on the Phase 1–4 allowlist. The only files read for
facts were the crate-augmented bundle, the source manifest and the crate
manifest. No prior full or core D4D, no evaluation report and no reconciliation
report from any earlier run was opened, globbed or cited. No live web content
was fetched.

The four deliberately withheld crate artifacts —
`VOICE_crate_mapped_d4d.yaml`, `ro-crate-datasheet.html`,
`ro-crate-preview.html` and `ro-crate-croissant.json` — were **not** read,
opened, globbed or cited. The bundle header names two of them in its
transparency listing; that listing was treated as a prohibition, not an index.

### Corrections applied to the full record, then re-projected into core

1. **`download_url` removed from the top level.** The schema states explicitly
   that `download_url` "is not the same as the landing page … this URL points
   directly to the data itself". The value was the PhysioNet project page, which
   is already carried by `page`. Removing it eliminates an assertion the sources
   do not support, since PhysioNet serves no direct file URL to unauthenticated
   users.
2. **`issued` removed from the Health Data Nexus v1.0 resource.** Documentation
   says only that the data "was published and made available at the end of
   November, 2024". `2024-11-30` was an invented precision; the phrase is
   retained verbatim in the resource description.
3. **b2aiprep version harmonized to 3.0.0 across the record.** The record
   previously carried version 3.0.2 in `external_resources.used_software` and
   3.0.0 in `preprocessing_strategies.used_software` for the same software
   identifier. The PhysioNet 3.0.0 and 3.1.0 release pages both state the
   release was generated with b2aiprep v3.0.0; the RO-Crate records 3.0.2 with
   `dateModified` 2026-01-06. The release-generating version is used as the
   value and the crate's differing figure is stated in the software
   description.
4. **Keywords rescoped.** "artificial intelligence" and "mobile application"
   were dropped; they are keywords of the app feasibility publication, not of
   the dataset. The remaining keywords are the crate's 18 plus PhysioNet's
   `health`, `biomarkers`, `bridge2ai` and `voice`.
5. **Interspeech 2024 citation discrepancy recorded.** Project documentation
   gives the protocol paper's first author as Bensoussan; the PhysioNet release
   pages give it as Rameau with Bensoussan last. `existing_uses` now states the
   disagreement rather than silently picking one.
6. **HIPAA statements disambiguated.** The DTUA's clause that the data it covers
   are personally identifiable information under OMB M-07-16 and "not covered
   under HIPAA" was scoped explicitly to the controlled-access transfer, so it
   no longer reads as a contradiction of `hipaa_compliant: compliant` on the
   de-identified public release.

### Source conflicts resolved, with the scoping used

- **3.0.0 vs 3.1.0.** The record's subject is the current adult release,
  **v3.1.0** (PhysioNet, published 2026-05-01, DOI `10.13026/8xbn-nq66`, 833
  participants). Every crate-derived fact is evidence about **v3.0.0** and is
  labelled as such in the text that carries it — the phrase "the upstream
  RO-Crate for release 3.0.0" appears throughout. v3.0.0 is additionally
  modelled as its own entry under `resources` with its own DOI
  (`10.13026/k81f-qr68`), page and publication date. Version-sensitive values
  that differ were taken from the documents: participant count 833 (unchanged
  between the two), per-feature row counts given for both releases side by side
  in `instances`, and the 3.1.0-only additions (`audio_quality_metrics.tsv`, the
  `metadata/` folder, the reorganized questionnaire/diagnosis file layout)
  recorded as 3.1.0 with an explicit note that the crate has no inventory for
  them.
- **Adult vs pediatric cohorts.** The two are separate PhysioNet projects, not
  versions of one another. No crate fact is attached to the pediatric cohort
  anywhere in either record. The pediatric dataset appears once under
  `resources` (DOI `10.13026/h995-bt35`, v1.1.0, 300 participants aged 2–18,
  23,533 derived recordings, SickKids REB approval, raw audio via Synapse
  `syn73617068`) and is referenced in `known_limitations` as the place to go for
  pediatric applications and in `at_risk_populations` for the assent and
  guardian-consent procedures. The adult release is stated as 18+ throughout.
- **Enrollment targets.** Four different figures appear across the corpus:
  10,000 voices (current documentation and study metadata, anticipated by 2027),
  30,000 (2024 white paper and IRB protocol), ~3,000 by November 2026 (crate),
  and the IRB's phased 180 / 600 / 3,000 / 5,000 ladder. All four are recorded
  in `purposes` with their source and scope rather than being reconciled to a
  single number.
- **Hosting platform.** The v1.0 healthsheet material describes the dataset as
  hosted by the Health Data Nexus (T-CAIREM, University of Toronto) with
  semi-annual updates. Current releases are on PhysioNet, maintained by the MIT
  Laboratory for Computational Physiology. Both maintainers are recorded, with
  the Health Data Nexus entry marked historical and scoped to v1.0.
- **Access tier wording.** PhysioNet describes v1.1 as "Restricted Access …
  registered users who sign the specified data use agreement" and v3.0.0/v3.1.0
  as "Credentialed Access … credentialed users who sign the DUA", while the
  project site says "registered access". Both wordings are recorded against
  their versions in `distribution_formats`.
- **Award-number renderings.** `OT2OD032720` appears as `3OT2OD032720-01S3`
  (RePORTER), `3OT2OD032720-01S1` (PhysioNet), `1OT2OD032720-01` (feasibility
  paper), `#3Tf-OTOD03272001S2` (project site and crate) and
  `3TF-OT2ActfOD032720Projectf01S1` (healthsheet). All are recorded in `funders`
  as transcription variants of the same core award.

### Internal-consistency verification

- Identity chain checks out: `id` = `https://doi.org/10.13026/8xbn-nq66`, `doi` =
  `10.13026/8xbn-nq66`, `version` = `3.1.0`, `page` = `.../b2ai-voice/3.1.0/`,
  `issued` = `2026-05-01`. `version_access.versions_available` lists 3.1.0 with
  the same DOI and 3.0.0 with `10.13026/k81f-qr68`, matching the `resources`
  entry; `latest_version_doi` = `10.13026/37yb-1t42` matches the "DOI (latest
  version)" field on every PhysioNet page in the bundle.
- `distribution_dates` release dates match `version_access.versions_available`
  and the PhysioNet version tables for all six adult releases and both pediatric
  releases.
- All 11 SHA-256 digests carried in core are distinct; each matches the crate
  entry for its `contentUrl` path.

### Defects found in the upstream crate, recorded rather than propagated

These are metadata defects in the RO-Crate itself, not defects in the released
data. Each is stated in the record at the point where it matters.

1. **`contentSize` disagrees with the crate's own file inventory.** The root
   entity declares `contentSize: "12.9 GB"` for release 3.0.0, but the nine
   feature files it inventories sum to **13,788,089,083 bytes ≈ 13.79 GB**, and
   that inventory is itself incomplete — the crate's own AI-readiness score
   reports checksums for 11 of 17 files. Neither figure was adopted as a
   dataset-level `total_size_bytes`; the verified sum is recorded on the feature
   `FileCollection` scoped to release 3.0.0, with the discrepancy stated.
2. **Two file entries carry names contradicting their own `contentUrl`.** The
   entry for `features/torchaudio_pitch.parquet` is named
   `torchaudio_spectrogram.parquet`; the entry for
   `features/sparc_periodicity.parquet` is named `sparc_loudness.parquet`. The
   `contentUrl` paths were treated as authoritative and the conflict is noted on
   the affected distributions and in `errata`.
3. **Duplicate entity identifier.** Two data-dictionary entities share
   `ark:59853/b2ai-voice-schema-phenotype-confounders` while carrying different
   names ("Phenotype Confounders Schema" and "Phenotype Demographics Schema").
4. **Duplicate aggregate label.** The entity
   `ark:59853/b2ai-voice-dataset-phenotype-task` is labelled "VOICE
   Questionnaire Tables", duplicating the label of the questionnaire aggregate.
   Core names it "VOICE Task Tables" after its identifier and records why.
5. **Inconsistent size property.** `ppgs.parquet` records its size under `size`;
   every other file uses `contentSize`.
6. **Tabular dialect asserted for Parquet files.** The EVI:Schema entities
   attached to the Parquet feature files declare `separator: ","` and
   `header: true`, neither of which is meaningful for Parquet. Only the
   TSV-backed schemas' `separator: "\t"` was used to populate core `dialect`.
7. **Ambiguous date format.** The crate's `datePublished` is `12/16/2025`, and
   `sparc_pitch.parquet` carries `08/18/2025` while every other feature entry
   carries `12/16/2025`. Dates in the record are written in ISO form and sourced
   from PhysioNet.
8. **Empty required-looking fields.** `irbProtocolId` and `completeness` are
   present but empty on the root entity; neither was populated by guesswork.
9. **Operator name.** Both computations are recorded as run by `"Alastair"`,
   which differs from the "Alistair Johnson" spelling used in every document
   source. Recorded as-is, with the discrepancy noted.
10. **AI-readiness self-assessments disagree.** The crate's
    `ai_ready_score.json` marks all 26 criteria as satisfied, while the project
    documentation's own AI-readiness table (Table 4) scores Data Quality,
    Domain-appropriate, Associated and Contextualized as 0, giving 80%
    characterization, 50% sustainability and 75% computability. Neither
    self-assessment was imported as a dataset fact; both are noted here only.

## Phase 4 — strict full/core reconciliation

Shared slots were derived at runtime from `Dataset` and `CoreDataset` via
`SchemaView`; no hand-maintained field list was used.

**Deterministic result: PASS — 76 schema-identical slots, projected slots =
`['resources']`.**

An independent deep comparison of the parsed YAML confirms the validator: of the
69 slots present in both files, **0 differ**, including every narrative field.
Core condenses, paraphrases, reorders and omits nothing.

Presence sets:

- Full-only (12 present, all absent from the `CoreDataset` schema): `citation`,
  `collection_consents`, `collection_notifications`, `consent_revocations`,
  `direct_collection`, `file_collections`, `participant_compensation`,
  `participant_privacy`, `relationships`, `splits`, `third_party_sharing`,
  `variables`.
- Core-only (2, both absent from `Dataset`): `distributions`, `dialect`.
- No shared slot is present in one file and absent from the other.

### Projected slot: `resources`

`resources` is `Dataset` in full and `CoreDataset` in core. All four resources
match by `id` with equal coverage: `10.13026/k81f-qr68` (release 3.0.0),
`syn72370534` (controlled-access raw audio), `10.13026/h995-bt35` (pediatric
1.1.0) and `10.57764/qb6h-em84` (Health Data Nexus v1.0). Every nested slot used
(`id`, `name`, `title`, `description`, `version`, `doi`, `license`, `page`,
`publisher`, `issued`, `conforms_to`) is an `Information`-level slot present on
both classes, so the projection is lossless and deeply identical; no full-only
nested slot had to be dropped.

### Related, non-identical content: `file_collections` ↔ `distributions`

The validator emits one `semantic-review-required` warning here, matching 1
entry deterministically by path and leaving 18 for review. That review was
performed; the mapping is one-to-many and complete in both directions.

| full `file_collections` | core `distributions` | verified agreement |
|---|---|---|
| `b2ai-voice-3.0.0-feature-parquet` (`features/`, 9 files, 13,788,089,083 B, v3.0.0) | the 9 `features/*.parquet` entries | file count 9 = 9; sum of core `bytes` = 13,788,089,083 = full `total_bytes`, verified arithmetically |
| `b2ai-voice-feature-tables` (`features/`, v3.1.0) | `static_features.tsv`, `audio_quality_metrics.tsv` | both TSV; release scope 3.1.0 for the audio-quality file stated in both |
| `b2ai-voice-phenotype-tables` (`phenotype/`, v3.1.0) | `confounders.tsv`, `demographics.tsv`, and the diagnosis / enrollment / questionnaire / task aggregates | paths nest under `phenotype/`; the two sized files carry the crate's byte counts and digests; the four aggregates carry no size, matching the crate, which records none |
| `b2ai-voice-recording-metadata` (`metadata/`, v3.1.0) | per-recording metadata entry (`metadata/`) | the one deterministic path match; both state it is 3.1.0-only and absent from the crate |
| `b2ai-voice-data-dictionaries` (CC BY 4.0, v3.0.0) | JSON data dictionaries entry | both record the 55 EVI:Schema entities and the CC BY 4.0 license distinct from the dataset's registered-access license |

No conflict was found on names, descriptions, paths, formats, compression,
checksums, byte counts, access URLs or release scope.

### Other related-content checks

- **`total_file_count` / `total_size_bytes`:** absent from full, and core has no
  top-level equivalent. The only aggregate count and size in either record are
  scoped inside one `FileCollection` to release 3.0.0's nine feature files, and
  they equal the sum over the corresponding core distributions. No cross-scope
  comparison is being made, so no contradiction is possible.
- **`dialect`, formats, `is_tabular`:** `dialect` is core-only and declares a tab
  delimiter with a header, agreeing with every TSV distribution and with the
  crate's tabular EVI:Schema entities; the crate's comma-separator declaration on
  the Parquet schemas is explicitly rejected in the record as not meaningful for
  Parquet. `is_tabular` is absent from both files, deliberately: the release
  mixes dense Parquet tensors with delimited text, so neither `true` nor `false`
  is supportable. No distribution declares `compression`, and `compression` is
  unset at the top level of both files.
- **Access URLs:** the shared `distribution_formats.access_urls` are identical in
  both records. Core's `path` values are release-internal file paths, not URLs,
  so the two do not collide.
- **Historical vs current releases:** v1.0 on Health Data Nexus, v1.1–v3.0.0 on
  PhysioNet and the current v3.1.0 are modelled as distinct releases with
  distinct DOIs and dates. Their differing participant counts (306 at v1.0, 833
  at v3.0.0 and v3.1.0) and differing recording counts are not treated as
  contradictions.

---

## Crate-only vs document-only field attribution

This is the arm's headline result. The VOICE crate is **genuinely additive**:
its responsible-AI governance content has no counterpart in the document corpus.

### Populated only from crate evidence

| Field | Crate source |
|---|---|
| `known_biases` (5 of 7 entries: sampling, geographic/cultural, clinical spectrum, device/environment, algorithmic annotation) | `rai:dataBiases` |
| `known_limitations` (5 of 7 entries: no raw audio, adult/English scope, de-identification cost, no splits, access governance) | `rai:dataLimitations` |
| `imputation_protocols` (entire slot) | `rai:dataImputationProtocol` |
| `annotation_analyses` (entire slot) | `rai:dataAnnotationAnalysis` |
| `machine_annotation_tools` (entire slot) | `rai:machineAnnotationTools` |
| `labeling_strategies.data_annotation_platform` | `rai:datannotationPlatform` (crate's own key is misspelled) |
| `labeling_strategies.annotations_per_item`, `.annotator_demographics` | `rai:annotationsPerItem`, `rai:annotatorDemographics` |
| `missing_data_documentation` (patterns and handling strategy) | `rai:dataCollectionMissingData` |
| `updates` (maintenance plan narrative) | `rai:dataReleaseMaintenancePlan` |
| `ethical_reviews` → Hastings Center bioethics review | `ethicalReview` |
| `regulatory_restrictions.confidentiality_level`, `.governance_committee_contact` | `confidentialityLevel`, `dataGovernanceCommittee` |
| `human_subject_research` IRB postal address, email, telephone; exemption status; `fdaRegulated`; empty `irbProtocolId` | `irb`, `humanSubjectExemption`, `fdaRegulated` |
| `distributions` per-file `bytes` and `sha256` (11 files); the crate Merkle root hash | file entities, `evi:merkleRootHash` |
| Data-dictionary CC BY 4.0 license; the 55 EVI:Schema entities | EVI:Schema entities |
| Provenance computations (VOICE Features Processing, VOICE Phenotype Ingest) and their operator | `EVI#Computation` entities |
| Copyright notice "Copyright © 2026 University of South Florida all rights reserved" | `copyrightNotice` |
| Contact point `https://b2ai-voice.org/contact-us/`; license and DUA URLs under `view-license/3.0.0/` and `view-dua/3.0.0/` | `contact`, `license`, `conditionsOfAccess` |

Verified by phrase search against the document portion of the bundle: none of
`rai:dataBiases`, `rai:dataLimitations`, `rai:dataImputationProtocol`,
`rai:dataAnnotationAnalysis`, `ethicalReview`, `dataGovernanceCommittee` or
`confidentialityLevel` has a counterpart in the documents.

### Populated only from document evidence

Everything about **v3.1.0** (existence, DOI, publication date, release notes,
per-feature row counts, `audio_quality_metrics.tsv`, the `metadata/` folder); the
**entire pediatric cohort**; the **IRB protocol** (13 revisions, consent
mechanics, withdrawal, vulnerable populations, phased plan, participating
institutions and per-site lead investigators); **participant compensation**
($40 / $80 / $120); the **DUA and DTUA** terms, DACO process and Certificate of
Confidentiality; **five recording sites** and the iPad / Avid AE-36 hardware;
the **22 acoustic tasks** and validated-questionnaire matrix; the **app
feasibility study**; **Synapse** raw-audio distribution (`syn72370534`,
`syn73617068`); the **Health Data Nexus v1.0** release; **NIH funding** detail
(RePORTER application 11376382, $4,660,942 FY2025, 2022-09-01 to 2026-11-30);
the **de-identification levels and consent Q&A**; and the supporting **REDCap /
b2aiprep / docs repositories** with their Zenodo DOIs and licenses.

### Corroborated by both

Dataset title, description, 833 participants, five North American sites, the
five disease cohorts, PhysioNet as publisher, Yael Bensoussan as PI, the
feature-only release rationale, the preprocessing pipeline and its toolchain,
the de-identification steps, the discouraged-use list, and the v3.0.0 DOI. Where
both sources carry a value, they agree; the crate's descriptions of collection,
preprocessing and manipulation are longer syntheses of what the PhysioNet pages
state in briefer form.

---

## Commands run

```bash
poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_all.yaml \
  -C Dataset data/d4d_concatenated/claudecode_agent_crate/2026-07-27_claude-opus-5_rep1/VOICE_d4d.yaml

poetry run linkml-term-validator validate-data \
  data/d4d_concatenated/claudecode_agent_crate/2026-07-27_claude-opus-5_rep1/VOICE_d4d.yaml \
  --schema src/data_sheets_schema/schema/data_sheets_schema_all.yaml --target-class Dataset

poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml \
  -C CoreDataset data/d4d_concatenated/claudecode_agent_crate_core/2026-07-27_claude-opus-5_rep1/VOICE_d4d_core.yaml

poetry run linkml-term-validator validate-data \
  data/d4d_concatenated/claudecode_agent_crate_core/2026-07-27_claude-opus-5_rep1/VOICE_d4d_core.yaml \
  --schema src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml --target-class CoreDataset

poetry run python -m data_sheets_schema.d4d_pair_consistency \
  --full data/d4d_concatenated/claudecode_agent_crate/2026-07-27_claude-opus-5_rep1/VOICE_d4d.yaml \
  --core data/d4d_concatenated/claudecode_agent_crate_core/2026-07-27_claude-opus-5_rep1/VOICE_d4d_core.yaml \
  --sync-core

poetry run python -m data_sheets_schema.d4d_pair_consistency \
  --full data/d4d_concatenated/claudecode_agent_crate/2026-07-27_claude-opus-5_rep1/VOICE_d4d.yaml \
  --core data/d4d_concatenated/claudecode_agent_crate_core/2026-07-27_claude-opus-5_rep1/VOICE_d4d_core.yaml
```

## Final results

| Check | Result |
|---|---|
| Full — schema validation | No issues found |
| Full — ontology term validation | Validation passed |
| Core — schema validation | No issues found |
| Core — ontology term validation | Validation passed |
| Pair consistency (`--sync-core`) | PASS, 76 schema-identical slots, projected `['resources']` |
| Pair consistency (final independent run) | PASS, 76 schema-identical slots, projected `['resources']` |
| Semantic review of related content | Performed; 1 warning on `file_collections` ↔ `distributions`, reviewed above, no contradictions |
| Prior D4D factual reuse | None; withheld crate artifacts not read |

Files changed by Phase 3 and Phase 4: the full record (six corrections listed
above) and the core record (re-projected from the corrected full). The
`--sync-core` run made no changes beyond that projection.
