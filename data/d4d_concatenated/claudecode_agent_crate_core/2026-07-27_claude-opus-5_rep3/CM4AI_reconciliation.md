# CM4AI full/core reconciliation — 2026-07-27_claude-opus-5_rep3

## Run identity

| Field | Value |
|---|---|
| Agent runtime | Claude Code |
| Provider | Anthropic |
| Model | claude-opus-5[1m] |
| Mode | four-phase project agent |
| Arm | DE NOVO WITH CRATE (documents + RO-Crate evidence) |
| Temperature | 0.0 |
| Generated | 2026-07-27 |
| Version label | 2026-07-27_claude-opus-5_rep3 |

**Files produced**

- Full: `data/d4d_concatenated/claudecode_agent_crate/2026-07-27_claude-opus-5_rep3/CM4AI_d4d.yaml` (2,474 lines)
- Core: `data/d4d_concatenated/claudecode_agent_crate_core/2026-07-27_claude-opus-5_rep3/CM4AI_d4d_core.yaml` (1,673 lines)
- This report

Line counts are informational metadata only, not a quality gate.

## Phase 3 — source and provenance audit

### Allowed inputs actually read

Factual source (the only one):

- `data/preprocessed/concatenated/CM4AI_preprocessed_with_crate.txt` — 10 document files plus
  the crate evidence section (`CM4AI_crate_metadata_reduced.json`, `ai_ready_score.json`)

Structure and selection references (not fact sources):

- `src/data_sheets_schema/schema/data_sheets_schema_all.yaml` (class `Dataset`)
- `src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml` (class `CoreDataset`)
- `src/data_sheets_schema/schema/D4D_Core.yaml`
- `data/preprocessed/source_manifest.yaml`
- `data/ro-crate_packages/crate_manifest.yaml`

Structure for both records was derived at runtime with LinkML `SchemaView` over the two
merged schemas rather than from any template. Every emitted slot, nested class shape, and
enum value was checked against the induced slot inventory of its class.

### Provenance confirmation

- No prior full or core D4D record was read, globbed, or cited. Nothing under
  `data/d4d_concatenated/` or `data/d4d_individual/` was opened except the two outputs of
  this run.
- The withheld crate artifacts were **not** read: `CM4AI_crate_d4d.yaml`,
  `CM4AI_crate_mapped_d4d.yaml`, `ro-crate-linkml.yaml`, `ro-crate-datasheet.html`, and all
  `ro-crate-preview.html` files. The bundle header's transparency listing of these names was
  treated as a prohibition, not a pointer.
- No live web content was fetched. No evaluation or reconciliation report from any run was
  consulted.
- No D4D content from the parent conversation was used.

### Source-audit findings

**Four Dataverse releases kept distinct.** The record treats B35XWX (March 2025, Dataverse
v1.4, published 2025-03-03, 6 files), F3TD5R (June 2025, v2.1, published 2025-07-01, 21
files, a revision adding RGB IF images and RO-Crate metadata corrections), K7TGEM (October
2025, v2.1, published 2025-10-31, 8 files) and HIGT4C (June 2026, v2.0, published
2026-06-17, 10 files) as separate deposits with separate DOIs. HIGT4C is the described
dataset; the other three appear as `related_datasets` with `relationship_type: replaces`,
and all four plus the May 2024 release (DOI 10.18130/V3/DXWOS5, named only in the project
preprint) appear in `version_access.versions_available` and `distribution_dates`.

**Divergences recorded rather than silently resolved** (all in `anomalies`):

1. Crate declares `version: 1.0` and `datePublished: 2026-06-30`; Dataverse reports version
   2.0, publication date 2026-06-17, version-2 release 2026-07-15T20:28:19Z. The record uses
   the Dataverse values for `version`, `issued`, and `last_updated_on` because Dataverse is
   the authoritative distribution record for the DOI, and states the crate's values in
   `anomalies` and `version_access.version_details`.
2. The CM4AI data releases page labels the release "June 2026" but displays "Released on:
   June 17, 2025".
3. The crate's own citation string gives the year as 2025.
4. **No component crate cites the release it belongs to.** All ten component citation strings
   name the "March 2025 Data Release (Beta)"; six point at B35XWX (correct for that label)
   and three — the two EndoTag AP-MS crates and the KOLF2 SEC-MS crate — point at K7TGEM,
   which is the October 2025 release.
5. Several `isPartOf` identifiers in the crate carry a trailing comma
   (`...-June-2026-data-release,`), so they do not match the crate's own release entity id.
6. Governance contact spelled "Jillian Parker" on Dataverse, "Jilian Parker" in the crate.
   The record uses the Dataverse spelling.
7. Three size figures for overlapping scopes: crate `evi:totalContentSizeBytes`
   21,051,331,945,400 (used for `total_size_bytes`), crate root `contentSize` "19.9 TB", and
   CM4AI portal "21.4 TB".
8. The three IF component crates carry MD5s and sizes (2.6 / 3.2 / 2.8 GB) identical to the
   **v0.6 beta archives of the March 2025 release**, while their descriptions state 464
   proteins — the count belonging to the later 3.8 / 4.6 / 4.2 GB archives actually
   distributed on the June 2026 record. The crate mixes stale archive identity with current
   content description. Recorded in `anomalies` and in each affected `resources` entry.
9. Only 8 of 55,859 crate entities carry checksums (0%), per the AI-readiness assessment.

**Corrections made during Phase 3** (full corrected first, then core regenerated):

| # | Correction | Reason |
|---|---|---|
| 1 | Removed the "953.7 MB download limit" clause from `distribution_formats` | That UI text appears only in the March 2025 capture, not the June 2026 capture — mis-scoped |
| 2 | Rewrote the component-crate citation anomaly | Original text said only the AP-MS/SEC-MS/perturb-seq crates cited K7TGEM; verification showed six cite B35XWX and three cite K7TGEM, and none cite HIGT4C |
| 3 | Rescoped the Dataverse software version statement in `maintainers` | "v. 6.6 build 1829-192cdc4" appears only on the March 2025 and June 2025 captures |
| 4 | Restored the diacritic in "Bélisle-Pipon" in `citation` and in the `creators` entry | Source spelling fidelity |

**Values deliberately omitted.** `total_file_count` was left empty: the only stated count for
the described scope is 10 Dataverse files, which does not share a scope with the crate's
21.05 TB `total_size_bytes`; the crate's 53,877 is a dataset-entity count, not a file count.
Exact byte counts for individual archives are not stated anywhere (Dataverse displays rounded
"3.8 GB" style figures), so `CoreDistribution.bytes` and `FileCollection.total_bytes` were
left empty rather than inferred. `dialect` was omitted (non-tabular multimodal content), as
were `imputation_protocols`, `annotation_analyses`, `variables`, `subsets`, and
`extension_mechanism`, for which the bundle carries no evidence.

**Crate data-quality warnings honoured.** The crate's `evi:formats` list (`.d`, `.tsv`,
`.xml`, `csv`, `fastq.gz`, `h5`, `h5ad`, `image/jpeg`, `pdf`, `unknown`, …) is a list of file
*formats*, not compression codecs; none of those values were written into any `compression`
slot. `compression` is set to `zip` at the dataset level and on all ten distributions, on the
basis of the Dataverse file table showing all ten files as ZIP archives. Creators appearing in
the crate only as bare ORCID references were resolved to names and affiliations using the
`Person` entities in the same crate graph and cross-checked against the Dataverse author list.

### Phase 3 re-validation

Both files re-validated clean after every correction (commands in the Phase 4 section).

## Phase 4 — strict full/core reconciliation

### Shared-slot derivation

Shared slots were derived at runtime from `Dataset` and `CoreDataset` via `SchemaView`; no
hand-written field list was used. The deterministic validator reports **76 schema-identical
slots**, all present-in-both or absent-from-both with deeply identical parsed YAML content,
including every narrative field. Core condenses, paraphrases, reorders, and omits nothing.

The core record was produced mechanically from the Phase-3-audited full record: shared slots
copied verbatim, then the two projections below applied. This guarantees byte-level semantic
identity for shared content by construction.

**Full-only slots dropped from core** (13, none permitted on `CoreDataset`):
`total_size_bytes`, `citation`, `relationships`, `splits`, `direct_collection`,
`collection_notifications`, `collection_consents`, `consent_revocations`,
`participant_privacy`, `participant_compensation`, `third_party_sharing`,
`related_datasets`, `file_collections`.

**Core-only slots:** `distributions` (populated, see below) and `dialect` (omitted).

### Projection 1 — `resources` (Dataset → CoreDataset)

Nine component datasets, matched by `id`, equal coverage, no unmatched entries in either
direction. Every nested slot used (`id`, `name`, `title`, `description`, `version`, `issued`,
`doi`, `license`, `publisher`, `download_url`, `keywords`, `creators`, `conforms_to`) exists
on `CoreDataset`, so nothing was dropped in the projection and all values are deeply
identical. Verified independently of the validator.

### Projection 2 — `file_collections` → `distributions` (semantic review)

Ten `FileCollection` entries map one-to-one onto ten `CoreDistribution` entries. Reviewed
field by field:

| Aspect | Result |
|---|---|
| Identity | Same 10 `id` values in the same order; no unmatched core distributions |
| Names | Identical in all 10 |
| Descriptions | Identical in all 10 (no condensation) |
| Paths | `CoreDistribution.path` set to the archive filename, equal to `FileCollection.name` in all 10 |
| Formats | `format: ZIP` and `media_type: application/zip` on all 10, consistent with the Dataverse file table listing all ten files as ZIP archives |
| Compression | `zip` in both representations for all 10, and equal to the dataset-level `compression: zip` |
| Checksums | `CoreDistribution.md5` populated for all 10, each equal to the MD5 stated in the corresponding `FileCollection.description` and to the Dataverse file table |
| Byte counts | Absent from both representations; no exact byte figure is stated in any source |
| Access URLs | Not carried per-distribution; the release-level access URLs in `distribution_formats` resolve to the same DOI as `id`, `doi`, and `version_access.latest_version_doi` |
| Release scope | All 10 belong to the June 2026 HIGT4C release; no file from an earlier release is mixed in |

No contradictions. `FileCollection.collection_type` (`raw_data` / `processed_data` /
`metadata` / `documentation`) has no counterpart on `CoreDistribution` and is therefore
full-only, not a conflict.

### Related-content cross-checks

- `total_file_count` and `total_size_bytes`: `total_file_count` is unset in both records, so
  no scope conflict with the crate-scoped `total_size_bytes` in full. The three competing size
  figures are documented in `anomalies` rather than reconciled into a single number.
- `is_tabular` (`false`) agrees with the format profile in both records, and with the absence
  of `dialect` in core.
- Identity, version, and access facts agree across both records and internally:
  `id` = `https://doi.org/10.18130/V3/HIGT4C`, `doi` = `10.18130/V3/HIGT4C`,
  `version` = `2.0`, `license` = CC BY-NC-SA 4.0, `issued` = 2026-06-17,
  `last_updated_on` = 2026-07-15T20:28:19+00:00, `version_access.latest_version_doi` = the
  same DOI, and the `distribution_formats` access URLs resolve to the same DOI.
- Historical releases are represented as historical throughout: `related_datasets` marks them
  `replaces`, `distribution_dates` and `version_access` date and version them explicitly, and
  the component-crate carryover of March-2025 archive identity is flagged as an anomaly rather
  than merged into the current release's figures. Different values across releases are not
  treated as contradictions.

### Commands run

```bash
poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_all.yaml \
  -C Dataset data/d4d_concatenated/claudecode_agent_crate/2026-07-27_claude-opus-5_rep3/CM4AI_d4d.yaml

poetry run linkml-term-validator validate-data \
  data/d4d_concatenated/claudecode_agent_crate/2026-07-27_claude-opus-5_rep3/CM4AI_d4d.yaml \
  --schema src/data_sheets_schema/schema/data_sheets_schema_all.yaml --target-class Dataset

poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml \
  -C CoreDataset data/d4d_concatenated/claudecode_agent_crate_core/2026-07-27_claude-opus-5_rep3/CM4AI_d4d_core.yaml

poetry run linkml-term-validator validate-data \
  data/d4d_concatenated/claudecode_agent_crate_core/2026-07-27_claude-opus-5_rep3/CM4AI_d4d_core.yaml \
  --schema src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml --target-class CoreDataset

poetry run python -m data_sheets_schema.d4d_pair_consistency \
  --full data/d4d_concatenated/claudecode_agent_crate/2026-07-27_claude-opus-5_rep3/CM4AI_d4d.yaml \
  --core data/d4d_concatenated/claudecode_agent_crate_core/2026-07-27_claude-opus-5_rep3/CM4AI_d4d_core.yaml --sync-core

poetry run python -m data_sheets_schema.d4d_pair_consistency \
  --full data/d4d_concatenated/claudecode_agent_crate/2026-07-27_claude-opus-5_rep3/CM4AI_d4d.yaml \
  --core data/d4d_concatenated/claudecode_agent_crate_core/2026-07-27_claude-opus-5_rep3/CM4AI_d4d_core.yaml
```

### Final results

| Check | Result |
|---|---|
| `linkml-validate` full (`Dataset`) | No issues found |
| `linkml-term-validator` full | Validation passed |
| `linkml-validate` core (`CoreDataset`) | No issues found |
| `linkml-term-validator` core | Validation passed |
| `d4d_pair_consistency --sync-core` | PASS: 76 schema-identical slots; projected slots=['resources'] |
| `d4d_pair_consistency` (final, independent) | PASS: 76 schema-identical slots; projected slots=['resources'] |

The only validator output beyond PASS is the standing
`WARNING [semantic-review-required] $.file_collections <-> $.distributions` (10 deterministic
matches, 0 unmatched). That review is recorded above; the warning marks content requiring
review, and the review was performed.

`--sync-core` produced no changes: the core record was already byte-identical to the
synchronized form because it was generated by projection from the audited full record.

## Per-field attribution: crate-only vs document-derived

This is the primary result this arm exists to produce.

### Fields populated ONLY from crate evidence

| Field / path | Crate-only content |
|---|---|
| `conforms_to` | `https://w3id.org/ro/crate/1.2` (crate `conformsTo`) |
| `total_size_bytes` | 21,051,331,945,400 (`evi:totalContentSizeBytes`) |
| `resources` (all 9 entries) | **The single largest crate contribution.** The entire component-dataset inventory: EndoTag AP-MS paclitaxel and vorinostat crates; the three IF image crates; the KOLF2 differentiation SEC-MS crate; the treated-cancer-cell SEC-MS crate; and the two perturbation cell atlas crates. Their names, descriptions, versions, content sizes, publication timestamps, licenses, MD5s, evidence-graph paths, and authorship exist nowhere in the documents. |
| `instances` → `documented_dataset_entities` | 53,877 datasets, 1,976 computations, 6 software, 20 schemas, 55,859 entities, 8 with checksums |
| `informed_consent` | Entire entry (`d4d:informedConsent`) |
| `at_risk_populations` | Entire entry (`d4d:atRiskPopulations`) |
| `human_subject_research.irb_approval` | The exemption wording ("Exempt — research with commercially available de-identified human cell lines does not constitute human subjects research") |
| `funders` | NCI P30CA023100; DoD W81XWH-22-1-0401; CIRM EDUC4-12804; NWO 019.231EN.013; NIH R01HG012351, R01NS131560, S10 OD026929 |
| `raw_data_sources`, `raw_sources` | MassIVE accessions MSV000101915, MSV000101917, MSV000100676, MSV000098237; DOI 10.25345/C5348GV4S; the MassIVE FTP path; the FigShare URL; and every per-deposition size (441.2 GB, 532.5 GB, 1.11 TB, 910 GB, 16.7 TB, 177.35 GB). The release pages link "MassIVE Repository" and "Figshare" as bare labels with no accessions. |
| `distribution_formats` → `external_repository_distribution` | All five external access URLs |
| `license_and_use_terms.license_terms` | The CC0 1.0 dedication on the two EndoTag AP-MS depositions (a different license from the release's CC BY-NC-SA 4.0) |
| `ip_restrictions.restrictions` | The 2026 copyright years (documents carry the 2025 wording) |
| `collection_mechanisms` | Bruker timsTOF acquisition with Spectronaut quantitation; the AP-MS four-biological-replicate design |
| `cleaning_strategies` | AP-MS batch composition (untagged parental control + 10 tagged lines + positive control, DMSO vehicle) |
| `relationships` | The AP-MS batch-structure bullet |
| `collection_timeframes` → `project_data_collection_window` | 9/1/2022–6/1/2026, plus the per-component windows ending 1/31/2026 and 10/13/25 |
| `preprocessing_strategies` | FAIRSCAPE version 1.1.3; "the June 2026 release crate documents 20 schemas" |
| `intended_uses.usage_notes` | The interpretable-ML goal citing Ma et al. 2018 (PMID 29505029) and Kuenzi et al. 2020 (PMID 33096023) |
| `missing_data_documentation` | The checksum-coverage bullet (8 of 55,859) |
| `external_resources` | FAIRSCAPE as the ARK minting and resolution service |
| `creators` | Richa Tiwari (AP-MS component author, no ORCID or affiliation given, absent from the Dataverse author list); Antoine Forget's authorship of the SEC-MS differentiation component |
| `anomalies` | Items 1, 3, 4, 5, 6, 8, 9 (the remainder arise from comparing crate against documents) |

### Fields where the crate is redundant with the documents

The arm note predicted redundancy, and it holds for the governance and use core. The crate's
`conditionsOfAccess`, `usageInfo`, `prohibitedUses`, `completeness`, `ethicalReview`,
`humanSubjectResearch`, `dataGovernanceCommittee`, `confidentialityLevel`,
`rai:dataLimitations`, `rai:dataBiases`, `rai:dataUseCases`,
`rai:dataReleaseMaintenancePlan`, `rai:dataCollection`, `rai:dataCollectionMissingData`,
`license`, `identifier`, `name`, `description`, `keywords`, `publisher`,
`principalInvestigator`, `contactEmail`, and `associatedPublication` are **verbatim or
near-verbatim** restatements of text already on the Dataverse release pages, because both
render the same underlying metadata record. Every one of the following fields is fully
supported by the documents alone, and the crate adds nothing:

`id`, `doi`, `title`, `name`, `description`, `version`, `status`, `language`, `publisher`,
`page`, `download_url`, `license`, `created_by`, `created_on`, `issued`, `last_updated_on`,
`citation`, `keywords`, `is_tabular`, `compression`, `purposes`, `tasks`, `addressing_gaps`,
`known_biases`, `known_limitations`, `confidential_elements`, `content_warnings`,
`subpopulations`, `sensitive_elements`, `splits`, `acquisition_methods`,
`sampling_strategies`, `data_collectors`, `direct_collection`, `collection_notifications`,
`collection_consents`, `consent_revocations`, `ethical_reviews`, `data_protection_impacts`,
`participant_privacy`, `participant_compensation`, `labeling_strategies`,
`machine_annotation_tools`, `existing_uses`, `use_repository`, `other_tasks`,
`future_use_impacts`, `discouraged_uses`, `prohibited_uses`, `distribution_dates`,
`third_party_sharing`, `regulatory_restrictions`, `maintainers`, `errata`, `updates`,
`retention_limit`, `version_access`, `is_deidentified`, `related_datasets`,
`file_collections` / `distributions`.

Notably, **the ten distributions came entirely from the Dataverse file table**: filenames,
sizes, publication dates, public-access status, and MD5s. The crate contributes no
file-level inventory for the release's own archives — its `hasPart` and `EVI#outputs` lists
were collapsed during reduction, and its component-crate checksums describe the March 2025
archives instead.

Substantive content also came from documents the crate does not touch at all: the CM4AI
project description preprint supplied the MuSIC pipeline, the FAIRSCAPE architecture, the
module structure, the cell-line provenance and RRIDs, and the ethics programme; NIH RePORTER
supplied the award identifiers and project period; the CM4AI portal supplied the headline
instance counts; the Nature paper supplied the annotation methodology and toolkit
attributions; and the Creative Commons deed supplied the license terms.

### Assessment for this arm

The prediction of near-total redundancy holds for **governance, ethics, use, and limitation
text** — the crate's `rai:*` block is a re-serialization of the Dataverse release page.
Where the crate is genuinely additive is in **provenance and component structure**: the nine
component sub-crates with their repository accessions, sizes, licenses, and evidence graphs,
plus the release-level EVI counts. That content has no document counterpart and drives most
of the `resources`, `raw_data_sources`, and `raw_sources` sections. Two smaller crate-only
contributions are the extra funding awards and the explicit `d4d:informedConsent` /
`d4d:atRiskPopulations` statements.

The crate is also the source of most of the recorded **inconsistencies**: it disagrees with
Dataverse on version and publication date, mis-cites its parent release in all ten component
citations, and carries stale March-2025 checksums for its image components. Nothing from the
crate was allowed to overwrite an authoritative Dataverse value; the disagreements are
recorded in `anomalies` instead.

## Completion audit

1. Every factual input path is on the phase allowlist. ✔
2. No prior generated YAML was read or cited; no withheld crate artifact was opened. ✔
3. Every emitted slot and nested object is permitted by the applicable schema, including
   inherited slots, `slot_usage`, cardinality, inlining, and enum constraints, all resolved
   with `SchemaView`. ✔
4. The core record's declared full input carries this run's exact version label. ✔
5. No Phase 2 discovery required back-porting: core was projected from the audited full
   record, so full remained canonical throughout. ✔
6. Schema and ontology term validation pass for both records. ✔
7. The schema-derived pair validator passes (76 schema-identical slots). ✔
8. All projected and related content received semantic review (both projections above). ✔
9. Phase 3 provenance result and Phase 4 consistency result recorded above. ✔
