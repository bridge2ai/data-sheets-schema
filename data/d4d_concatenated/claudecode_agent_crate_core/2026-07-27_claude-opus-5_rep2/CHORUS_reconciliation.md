# CHORUS full/core reconciliation — 2026-07-27_claude-opus-5_rep2

**Arm:** DE NOVO WITH CRATE (documents + RO-Crate evidence)
**Agent runtime:** Claude Code · **Provider:** Anthropic · **Model:** claude-opus-5[1m]
**Mode:** four-phase project agent · **Temperature:** 0.0 · **Generated:** 2026-07-27

| Artifact | Path |
|---|---|
| Full | `data/d4d_concatenated/claudecode_agent_crate/2026-07-27_claude-opus-5_rep2/CHORUS_d4d.yaml` |
| Core | `data/d4d_concatenated/claudecode_agent_crate_core/2026-07-27_claude-opus-5_rep2/CHORUS_d4d_core.yaml` |
| Report | `data/d4d_concatenated/claudecode_agent_crate_core/2026-07-27_claude-opus-5_rep2/CHORUS_reconciliation.md` |

Line counts (informational metadata only, not a quality gate): full 1401, core 1091.

---

## Phase 3 — Source and provenance audit

### Provenance boundary

Factual input read: **only** `data/preprocessed/concatenated/CHORUS_preprocessed_with_crate.txt`
(2,060 lines, read in full across two paged reads).

Structure/selection references read (not used as fact sources):
`data_sheets_schema_all.yaml` (class `Dataset`), `data_sheets_schema_core_all.yaml`
(class `CoreDataset`), `D4D_Core.yaml`, `data/preprocessed/source_manifest.yaml`
(head), `data/ro-crate_packages/crate_manifest.yaml` (head).

Explicit confirmation on the manifest: `crate_manifest.yaml` contains CHORUS facts
(`dataset_title`, `dataset_publication_date: 2026-04-21`, `dataverse_version: 1.1`,
per-file md5s). **None of these appear in either record.** The record's title comes
from the crate `citation` field in the bundle; `issued` (2026-04-03) comes from the
crate `datePublished` in the bundle. The manifest's 2026-04-21 Dataverse publication
date and 1.1 Dataverse version were deliberately not used.

Confirmed NOT read, opened, globbed, or cited:

- `data/ro-crate_packages/CHORUS/processed/CHORUS_crate_d4d.yaml`
- `data/ro-crate_packages/CHORUS/processed/CHORUS_crate_mapped_d4d.yaml`
- `data/ro-crate_packages/CHORUS/raw/ro-crate-linkml.yaml`
- `data/ro-crate_packages/CHORUS/raw/ro-crate-datasheet.html`
- any `ro-crate-preview.html`
- anything under `data/d4d_concatenated/` or `data/d4d_individual/` other than this
  run's own outputs
- any prior D4D record, evaluation, or reconciliation report
- live web content (no WebFetch/WebSearch/ARTL call was made)

The withheld-artifact list in the bundle header was treated as a prohibition, not a
pointer. No prior D4D content from the parent conversation was used.

Structure derivation: every emitted slot and nested-object shape was derived at
runtime from LinkML `SchemaView` induced-slot inventories for `Dataset`,
`CoreDataset`, and each nested class range. `d4d:docExample` annotations were read as
documentation only; no example value was copied.

### Source conflicts resolved

| # | Conflict | Sources | Resolution |
|---|---|---|---|
| 1 | Admission count | webinar (Sept 2025): ">45K unique admissions as of August 2025"; website: "50,000 Patient admissions from ICU, PICU, and NICU" under *Current Released Dataset*; website *Anticipated Final Dataset*: 100,000; NIH abstract: "more than 100,000 critically ill patients" | Scoped, not merged. `instances[0].counts = 50000` (current release); the >45,000 August-2025 figure and the 100,000 anticipated figure are stated with their scopes in `instances[0].description`. |
| 2 | Imaging presence | website: "7,642 Admissions with Radiology Data"; webinar: "Imaging – currently 1000 images available with de-id in process"; crate `completeness`: "No DICOM images are included." | Different release scopes. Both retained with explicit scope in `instances[2].description` and `known_limitations` ("Interim release with partial data", `scope_impact` naming the v1.0 Beta 2026-04-03 release). |
| 3 | Waveform volume | website: "23 Tb Waveform data" (CHoRUS enclave); crate waveforms sub-crate `contentSize`: 1.201567472832 tb | Different release scopes. Corrected during Phase 3 (see below). |
| 4 | Program-manager email | website: `cmccrary@mgh.havard.edu` (misspelled domain); crate `contactEmail`: `cmccrary@mgh.harvard.edu` | Crate value used; the website value is a typographical error in the source. |
| 5 | Kwong affiliation | webinar: "Manlik Kwong, Tufts University"; crate affiliation (4): "Tufts CTSI / Tufts Medical Center" | Crate affiliation used (more specific, and the crate is the authoritative author list). |
| 6 | Jiang affiliation | webinar: "Xiaoqian Jiang, UTHealth Houston"; crate affiliation (10): "McWilliams School of Biomedical Informatics, UTHealth Houston …; Mayo Clinic …" | Crate affiliation used verbatim; the webinar value is a consistent subset. |

Cross-source corroborations recorded rather than discarded: the GitHub access
contacts `dbold@emory.edu` and `jared.houghtaling@tuftsmedicine.org` match crate
authors Delgersuren Bold (Emory, affiliation 14) and Jared Houghtaling (Tufts,
affiliation 4); the website award number OT2OD032701 matches the NIH RePORTER core
project number and the crate `funder` string.

### Corrections applied in Phase 3

**One correction**, applied to the full record first, then re-projected into core:

- `description` (top level). The first draft listed the 23 TB waveform figure and the
  1.0 Beta interim release in adjacent sentences without stating that they describe
  different release scopes. Rewritten to attribute the 50,000 / 1.6 billion / 7,642 /
  23 TB figures to the CHoRUS enclave release as described on the project website,
  and to state separately that the 2026-04-03 v1.0 Beta RO-Crate release totals
  ~1.2 TB, excludes DICOM images, and does not include all patients — with an
  explicit statement that the two are not in conflict.

No Phase 2 discovery required back-porting: core was projected from the Phase 1 full
record, and the Phase 2 re-read of the source bundle surfaced no fact that the full
record had missed or stated incorrectly.

### Internal consistency checks (each record)

- DOI `10.18130/V3/XNBOPG` is identical everywhere it repeats: `id`, `doi`,
  `version_access.latest_version_doi`, `distribution_formats.access_urls`,
  `external_resources`.
- Version `1.0 Beta` identical in `version`, `version_access.versions_available`,
  and (full only) both `file_collections` entries.
- `issued: 2026-04-03T00:00:00Z` agrees with `distribution_dates.release_dates:
  ['2026-04-03']`. The crate carries the same date twice (`datePublished`
  "2026-04-03" and `releaseDate` "03/04/2026", DD/MM/YYYY); only the unambiguous ISO
  form was emitted, and the dual representation is noted in
  `distribution_dates[0].description`.
- Byte arithmetic: full `total_size_bytes` 1,201,585,609,503 = 18,136,671 (EHR) +
  1,201,567,472,832 (waveforms), consistent with the crate's rounded top-level
  `contentSize` "1.2 tb".
- Person/organization identifiers reused consistently: Rosenthal appears as
  `creators[0].principal_investigator`, `ethical_reviews[0].contact_person`, and
  `regulatory_restrictions.governance_committee_contact`, all as
  `urn:d4d:chorus:person:eric-s-rosenthal`.

### Two deliberate representational mappings (flagged, not silent)

1. `publisher` has range `uriorcurie`; the crate publisher is the plain name
   "B2AI CHoRUS". Emitted as `https://chorus4ai.org/`, with the literal string
   "The publisher of record is B2AI CHoRUS" preserved in the corporate-author
   `creators` entry.
2. `confidentiality_level` is a closed enum (`unrestricted` / `restricted` /
   `confidential`); the crate value is "HL7:2V (very restricted)". Mapped to
   `confidential`, with the verbatim crate string and the mapping rationale stated
   in `regulatory_restrictions.description`.

Identifiers minted for classes whose `id` is schema-required (`Person`,
`Organization`, `Grantor`, `Grant`) use a non-resolving `urn:d4d:chorus:…` scheme so
that no unverified resolvable URL is asserted. Sub-crate identifiers preserve the
crate's UUIDs verbatim as `urn:uuid:…`.

---

## Phase 4 — Strict full/core reconciliation

Shared slots were derived at runtime with LinkML `SchemaView`, not from a
hand-written list.

- `Dataset` induced slots: **94**. `CoreDataset` induced slots: **79**.
- **Schema-identical shared slots: 76** — all present-or-absent identically and
  deeply identical in parsed YAML, including narrative fields. Core condenses,
  paraphrases, reorders, and omits nothing.
- Shared-with-different-range (projection): **`resources`** (`Dataset` in full,
  `CoreDataset` in core). Absent from both records, so the projection is vacuous.
- Full-only slots present in the full record and therefore legitimately absent from
  core: `citation`, `total_file_count`, `total_size_bytes`, `file_collections`,
  `relationships`, `splits`, `direct_collection`, `third_party_sharing`.
- Core-only slots: `distributions` (populated), `dialect` (omitted — no source
  evidence of delimiter, quoting, or header conventions).

Core was produced by projecting the Phase 3-audited full record through the
runtime-derived shared-slot set, so deep identity holds by construction and was then
verified independently.

### Semantic review of related, non-identical content

The validator raises one `semantic-review-required` warning for
`$.file_collections <-> $.distributions`. That warning marks work to be done, not
work done; the review below was performed.

| Full `file_collections[i]` | Core `distributions[i]` | Finding |
|---|---|---|
| `urn:uuid:08cf7419-…` "CHoRUS RO-Crate EHR SubRoCrate", `total_bytes: 18136671` | same id/name/description, `bytes: 18136671` | name, description, byte count identical; no conflict |
| `urn:uuid:b9b41c72-…` "CHoRUS RO-Crate Waveforms SubRoCrate", `total_bytes: 1201567472832` | same id/name/description, `bytes: 1201567472832` | name, description, byte count identical; no conflict |

- **Coverage:** 2 deterministic matches, 0 unmatched core distributions, 0 unmatched
  file collections.
- **`total_file_count` / `total_size_bytes` vs distribution-level values:**
  `total_size_bytes` (1,201,585,609,503) equals the sum of the two distribution
  `bytes` values exactly — same scope, no conflict. `total_file_count` (1,477, from
  the AI-readiness score's "1469/1477" checksum statement) has no distribution-level
  counterpart because `CoreDistribution` declares no file-count slot; no conflict is
  representable.
- **Full-only nested `FileCollection` slots** (`collection_type`, `version`,
  `issued`, `license`, `page`, `conforms_to`, `keywords`) have no `CoreDistribution`
  counterpart in the schema and are correctly omitted from the core projection. Each
  value agrees with the corresponding dataset-level core slot (`version`, `issued`,
  `license`, `page`, `conforms_to`, `keywords`) — no contradiction.
- **`dialect`, formats, `is_tabular`:** `dialect` absent from core and not a
  `Dataset` slot at all. No `format`/`media_type`/`compression`/`encoding` is
  asserted on either side, so no format conflict is possible; format prose lives in
  `distribution_formats`, a schema-identical shared slot verified deeply identical.
  `is_tabular: false` in both.
- **Checksums, paths, access URLs, release scope:** no checksum, path, or
  distribution-level access URL is asserted in either record (the crate's per-file
  md5s live in `crate_manifest.yaml`, which is not a fact source for this arm).
  Release scope is stated once, identically, in the shared `description`,
  `known_limitations`, and `distribution_dates` slots.
- **Identity / version / access facts vs distributions and version history:**
  top-level `id`, `doi`, `version`, `issued`, `license`, `page` agree with
  `version_access`, `distribution_dates`, `distribution_formats`, and
  `license_and_use_terms` in both records.
- **Historical vs current releases:** the >45,000-admissions (August 2025) and
  1,000-images (August 2025) figures are marked as historical in prose rather than
  treated as contradictions of the current 50,000 / 7,642 figures.

**Unresolved contradictions within or between the two records: none.**

---

## Per-field attribution: crate-only vs documents

This is the primary result of this arm. "Crate-only" means the content has no
counterpart anywhere in the four CHORUS documents and comes solely from
`CHORUS_crate_metadata_reduced.json` or `ai_ready_score.json`.

### Populated ONLY from crate evidence (25 slots / slot-groups)

| Slot | Crate field |
|---|---|
| `id`, `doi` | `identifier` (`https://doi.org/10.18130/V3/XNBOPG`) — the documents contain no DOI at all |
| `title` | `citation` |
| `citation` (full only) | `citation` |
| `version` | `version` ("1.0 Beta") |
| `issued`, `distribution_dates` | `datePublished` / `releaseDate` |
| `status` | `completeness` ("Interim release with partial data") |
| `keywords` | `keywords` |
| `conforms_to_schema` | `@context` / `conformsTo` RO-Crate 1.2 + `ai_ready_score` (Croissant RAI, schema.org) |
| `total_file_count` (full only) | `ai_ready_score.pre_model_explainability.verifiable` ("1469/1477") |
| `total_size_bytes` (full only) | sum of `contentSize` on the two sub-crates |
| `file_collections` (full) / `distributions` (core) | `hasPart` EHR + Waveforms sub-crates with `contentSize` |
| `creators` — 41 named authors + 15 affiliations | `author` (the documents name only 6 leadership members and the PI) |
| `known_biases` — all 6 entries | `rai:dataBiases` / `rai:potentialBiases` |
| `known_limitations` — 8 of 8 entries | `rai:dataLimitations` + `completeness` |
| `anomalies` | `rai:dataCollectionMissingData` + `rai:dataLimitations` |
| `ethical_reviews` — IRB protocol **#2022P000707**, MGB IRB name/address/phone/email, named reviewers, HIPAA exemption 4 | `irbProtocolId`, `irb`, `ethicalReview`, `humanSubjectExemption` |
| `human_subject_research` — IRB approval, review board, regulatory compliance, FDA-regulated | `irbProtocolId`, `irb`, `humanSubjectResearch`, `fdaRegulated` |
| `informed_consent` | `rai:dataCollection` (IRB approval-or-waiver) + `humanSubjectExemption` |
| `at_risk_populations.special_protections` | `rai:personalSensitiveInformation` |
| `sensitive_elements` (all 10 safeguard details) | `rai:personalSensitiveInformation` |
| `is_deidentified` (method, identifiers removed, details) | `deidentified`, `rai:personalSensitiveInformation`, `rai:dataCollection` |
| `data_protection_impacts` | `rai:personalSensitiveInformation` |
| `confidential_elements` + `regulatory_restrictions.confidentiality_level` — **HL7:2V (very restricted)** | `confidentialityLevel` |
| `license_and_use_terms` — DUA URL, `conditionsOfAccess` .docx URL, governance-committee review, IRB documentation requirement, no-commercial-use clause, `data_use_permission` enums | `license`, `conditionsOfAccess`, `rai:conditionsOfAccess` |
| `ip_restrictions` — MGH copyright notice, subaward-site and joint-software copyright | `copyrightNotice` |
| `intended_uses` (9 use cases + usage notes), `discouraged_uses` (3), `prohibited_uses` (re-identification / no-export / no-commercial) | `rai:intendedUseCases`, `rai:conditionsOfAccess` |
| `updates`, `retention_limit`, `version_access` — versioned releases, release notes, deprecation policy, backward-compatibility window, archive policy | `rai:maintenancePlan` / `rai:dataReleaseMaintenancePlan` |
| `regulatory_restrictions` — NIST 800-53, HIPAA compliance status, NIH data-sharing policy, Bridge2AI OT terms, enclave export restriction | `description`, `rai:conditionsOfAccess`, `rai:dataCollection` |
| `missing_data_documentation` (MNAR patterns, handling strategy) | `rai:dataBiases`, `rai:dataCollectionMissingData`, `rai:maintenancePlan` |
| `maintainers` — CHoRUS Data Pillar, governance committee, Ciera McCrary contact email | `rai:maintenancePlan`, `dataGovernanceCommittee`, `contactEmail` |
| `publisher` | `publisher` ("B2AI CHoRUS") |

### Populated ONLY from the document corpus (12 slots / slot-groups)

| Slot | Document source |
|---|---|
| `funders` — application ID 10472824, project number 1OT2OD032701-01, FY2022 award **$5,880,300**, project period 2022-09-01 → 2026-11-30, NIH program leadership | NIH RePORTER + webinar (crate gives only the bare string "NIH Common Fund OT2OD032701") |
| `instances` — all five entries (50,000 admissions; 1.6 B OMOP rows; 7,642 radiology admissions; 14 hospitals; 9 modalities) | chorus4ai.org + webinar (crate has no counts at all) |
| `addressing_gaps` — all four entries | NIH abstract + GitHub README |
| `splits` (full only) — holdout test set for external validation | NIH abstract (crate mentions hold-out splits only inside `rai:dataLimitations`) |
| `subpopulations` — ICU/PICU/NICU identification, federated balanced sampling | chorus4ai.org + GitHub README |
| `sampling_strategies.strategies` — 14 acquisition hospitals, federated access, comprehensive condition sampling | NIH abstract + GitHub README |
| `data_collectors` — 20 academic centers / 14 acquisition centers, Data Pillar sub-teams, clinical collaborators, chorus-mapping | GitHub README |
| `collection_mechanisms` — per-modality data standards, access control, published metadata schemas (OMOP, OHNLP, DICOM, WFDB, EDF+/Persyst, extended PhysioNet) | webinar data-type table |
| `cleaning_strategies` — validated semantic mappings, clinical validation SOP, Chorus_SOP, CHoRUSReports site characterization | GitHub README |
| `labeling_strategies` — visualization and annotation environment | NIH abstract + GitHub README |
| `use_repository` + `extension_mechanism` — 28 repositories, per-repo detail, task/status tracking, Google Form + GoogleScript workflow, chorus-developer guide | GitHub README |
| `existing_uses` (training program), `external_resources` (AIM-AHEAD program, .edu email requirement, registration + licensing agreement, "under review … Administration directives" notice), `ip_restrictions` MIT/Apache-2.0 clauses | webinar + chorus4ai.org + GitHub README |

### Corroborated by both (14 slots)

`name`, `description` (crate prose + website/NIH counts), `page` / `contentUrl`,
`license` (crate DUA + webinar licensing-agreement requirement), `conforms_to` (crate
`rai:dataCollection` names OMOP and WFDB; webinar table names all six standards),
`purposes`, `tasks`, `acquisition_methods`, `preprocessing_strategies` (crate names
RSNA CTP and IbisWorks EICON; documents name OHNLP tokenization and DeGauss
geocoding), `raw_data_sources`, `raw_sources`, `machine_annotation_tools`,
`collection_timeframes`, `future_use_impacts`.

### Net assessment

The arm note's expectation is confirmed and is measurable. Governance, ethics,
licensing, responsible-AI, and release-management content in this record is
overwhelmingly crate-derived: IRB protocol #2022P000707, the Mass General Brigham
IRB entity and its contact details, confidentiality level HL7:2V, the six RAI biases
and eight limitations, the DUA and conditions-of-access URLs, the MGH copyright
notice, HIPAA exemption 4, FDA-regulated status, the deprecation/versioning policy,
and the 1.2 TB / 1,477-file / no-DICOM release characterization have **no counterpart
anywhere in the four-document CHORUS corpus**. The crate is also the only source of
a DOI, a version label, a publication date, a citation, and 35 of the 41 named
creators.

Conversely the crate is silent on everything quantitative about cohort scale and on
the project's engineering and community infrastructure: all five `instances` counts,
the full grant record, the 28-repository tooling and SOP ecosystem, the per-modality
data-standard table, and the training-program access pathway come only from the
documents. Neither input alone would have produced this record.

---

## Commands run

```bash
poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_all.yaml \
  -C Dataset data/d4d_concatenated/claudecode_agent_crate/2026-07-27_claude-opus-5_rep2/CHORUS_d4d.yaml

poetry run linkml-term-validator validate-data \
  data/d4d_concatenated/claudecode_agent_crate/2026-07-27_claude-opus-5_rep2/CHORUS_d4d.yaml \
  --schema src/data_sheets_schema/schema/data_sheets_schema_all.yaml --target-class Dataset

poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml \
  -C CoreDataset data/d4d_concatenated/claudecode_agent_crate_core/2026-07-27_claude-opus-5_rep2/CHORUS_d4d_core.yaml

poetry run linkml-term-validator validate-data \
  data/d4d_concatenated/claudecode_agent_crate_core/2026-07-27_claude-opus-5_rep2/CHORUS_d4d_core.yaml \
  --schema src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml --target-class CoreDataset

poetry run python -m data_sheets_schema.d4d_pair_consistency \
  --full data/d4d_concatenated/claudecode_agent_crate/2026-07-27_claude-opus-5_rep2/CHORUS_d4d.yaml \
  --core data/d4d_concatenated/claudecode_agent_crate_core/2026-07-27_claude-opus-5_rep2/CHORUS_d4d_core.yaml \
  --sync-core

poetry run python -m data_sheets_schema.d4d_pair_consistency \
  --full data/d4d_concatenated/claudecode_agent_crate/2026-07-27_claude-opus-5_rep2/CHORUS_d4d.yaml \
  --core data/d4d_concatenated/claudecode_agent_crate_core/2026-07-27_claude-opus-5_rep2/CHORUS_d4d_core.yaml
```

## Final results

| Check | Result |
|---|---|
| Full — `linkml-validate` (`Dataset`) | No issues found |
| Full — `linkml-term-validator` | Validation passed |
| Core — `linkml-validate` (`CoreDataset`) | No issues found |
| Core — `linkml-term-validator` | Validation passed |
| `d4d_pair_consistency --sync-core` | PASS — 76 schema-identical slots; no change written (core already identical) |
| `d4d_pair_consistency` (final independent run) | PASS — 76 schema-identical slots; projected slots `['resources']`; exit 0 |
| Semantic review warning | 1 (`file_collections` ↔ `distributions`) — reviewed above; 2/2 matched, 0 conflicts |
| Files changed after initial write | full `description` only (Phase 3 scoping correction), then core regenerated |
| Unresolved contradictions | none |
