# CM4AI full/core reconciliation — 2026-07-27_claude-opus-5_rep1

- Arm: BASELINE (document corpus only)
- Agent runtime: Claude Code · Provider: Anthropic · Model: claude-opus-5[1m]
- Mode: four-phase project agent · Temperature: 0.0 · Generated: 2026-07-27
- Full: `data/d4d_concatenated/claudecode_agent/2026-07-27_claude-opus-5_rep1/CM4AI_d4d.yaml` (1984 lines)
- Core: `data/d4d_concatenated/claudecode_agent_core/2026-07-27_claude-opus-5_rep1/CM4AI_d4d_core.yaml` (1539 lines)
- Line counts are informational metadata only, not a quality gate.

## Phase 3 — source and provenance audit

### Provenance boundary

Factual inputs read during this run, and no others:

- `data/preprocessed/concatenated/CM4AI_preprocessed.txt` (10 documents, 7873 lines)
- `data/preprocessed/source_manifest.yaml` (CM4AI section, including curation notes)

Structure-only references: `data_sheets_schema_all.yaml` (class `Dataset`),
`data_sheets_schema_core_all.yaml` (class `CoreDataset`), `D4D_Core.yaml`.

No prior full or core D4D record, evaluation, reconciliation report, or RO-Crate
artifact was read, searched, globbed, or cited. No live web content was fetched. No
prior D4D content from the parent conversation was used as evidence. Class shapes,
ranges, cardinalities, inlining behaviour and enum vocabularies were derived at runtime
with `linkml_runtime.SchemaView` rather than from any example record.

### Source scope decisions

The corpus mixes two distinct dataset scopes, and keeping them apart was the main
source-audit task.

1. **CM4AI Dataverse releases** (MDA-MB-468 and KOLF2.1J; SEC-MS, AP-MS, IF imaging,
   perturb-seq) — this is the documented dataset.
2. **Schaffer et al., Nature 642:222–231 (2025)**, the U2OS multimodal cell map study.
   It is authored by CM4AI investigators and acknowledges Bridge2AI OT2 OD032742, but
   its cell system (U2OS osteosarcoma) and its deposits (NDEx
   f693137a-d2d7-11ef-8e41-005056ae3c32 and 95bc75d5-d1d1-11ee-8a40-005056ae23aa,
   MassIVE MSV000097168, ProteomeXchange PXD052362, ModelArchive ma-idk-u2osmap and
   ma-m5og4, HPA v23) are **not** part of the CM4AI Dataverse releases.

U2OS-derived content was therefore admitted only into method-describing slots
(`labeling_strategies`, `annotation_analyses`, `machine_annotation_tools`,
`existing_uses`, `related_datasets`) and every such entry carries an explicit scope
statement. No U2OS count, deposit, funder, or composition fact was merged into the
CM4AI dataset's identity, composition, or distribution slots.

Release scoping: `HIGT4C` (June 2026) is modelled as the current release and drives the
top-level `doi`, `version`, `page`, `license`, `last_updated_on`, `file_collections`
and `total_file_count`. `K7TGEM`, `F3TD5R` and `B35XWX` appear as separate entries under
`resources`, each with `status` beginning "Historical release, superseded". They were
not merged into the current release.

### Source conflicts found and how they were resolved

| # | Conflict | Resolution |
|---|---|---|
| 1 | cm4ai.org data-releases page shows "June 2026 Data Release (Beta) … Released on: June 17, 2025"; Dataverse gives Publication Date **2026-06-17** and a 2026 citation year for the same DOI. | Dataverse metadata preferred, per run instruction. Recorded as an anomaly (`CM4AI_anomaly_stale_release_metadata`) and in `distribution_dates`; the web-page year is called out as an error. |
| 2 | Every release, including June 2026, reports Data Creation Date and Deposit Date **2025-02-27**, while files in the June 2026 release were published as late as 2026-07-15. | Both recorded. Flagged as carried-forward metadata in `CM4AI_anomaly_stale_release_metadata` and bounded in `collection_timeframes`. |
| 3 | June 2026 release description block ends with the trailing date **(2025-06-30)** — the same trailing date used by the June 2025 and October 2025 descriptions. | Recorded as carried-forward descriptive text; no date asserted from it. |
| 4 | Displayed Dataverse version vs. citation version disagree per release: 1.4/V1 (March 2025), 2.1/V2 (June 2025), 2.1/V2 (October 2025), 2.0/V2 (June 2026). | Both values recorded per release in `version_access` and in each `resources` entry; the displayed version is used for the `version` slot. |
| 5 | Identically named IF archives carry MD5 `0d972b80…`, `a98affcc…`, `ad4e68cc…` in June 2025 and October 2025, but `6c1a8652…`, `6d066e6b…`, `df796327…` in June 2026, with unchanged displayed sizes. Mass-spec, perturb-seq and release-metadata archives also change size and checksum between October 2025 and June 2026. | Treated as genuine file replacement across distinct releases, not as a contradiction. Recorded in `CM4AI_anomaly_file_content_changes` and per-file in `file_collections`. |
| 6 | IF protein coverage is 563 proteins in March 2025 and 464 proteins from June 2025 onward. | Both recorded, each bound to its release. |
| 7 | Collaborator list: the data-releases page names UCSD, UCSF, Stanford, UVA, Yale, **UT Austin**, UA Birmingham, SFU and the Hastings Center; the March 2025 release description gives the same list **without UT Austin**. | The fuller, more recent list is used in `description`; the discrepancy is stated explicitly in `description` and in `maintainers`. |
| 8 | Project end date: release metadata says "through the end of the project in **November 2026**"; NIH RePORTER gives project end **2026-08-31**. | Both recorded; the disagreement is stated explicitly in `updates` and `collection_timeframes`. No single end date is asserted. |
| 9 | Vardit Ravitsky is listed as *University of Montreal* in the Dataverse author list and the preprint, but the ethical-review contact email is `ravitskyv@thehastingscenter.org`. | Reviewing organization set to The Hastings Center (also named as a CM4AI collaborator); the affiliation discrepancy is stated in the `ethical_reviews` description. |
| 10 | Andrej Sali is listed as *University of California San Diego* in the Dataverse author lists but *UCSF* in the preprint and the Nature paper. | Not asserted. No per-person affiliation is claimed for Sali in either record. |
| 11 | The June 2025 release page reports 21 files but the captured page displays only the first 10. | The 10 captured files are recorded; the incompleteness is declared in `missing_data_documentation` and in that release's `description`. |
| 12 | The October 2025 `cm4ai_ifimages_MDA-MB-468_untreated.zip` description reads "…MDA-MB-468 treated as imaged by…", omitting the untreated condition given by the file name and the release description. | Recorded verbatim with the omission noted in `CM4AI_anomaly_file_content_changes` and in that file's entry. |
| 13 | The CM4AI portal's flagship-dataset panel marks AP-MS interactomes and iPSC IF images as "coming soon", but AP-MS archives are present in the June 2026 release. | Recorded in `missing_data_documentation` as stale portal text relative to the current release. |

### Corrections applied in Phase 3

Four mis-scoped or incomplete assertions were found in the Phase 1 full record and
corrected there first, then propagated to core:

1. `instances[CM4AI_instance_sec_ms].counts: 7023` — removed. 7,023 is the CM4AI portal's
   project-wide "Total Proteins Investigated" figure, not a SEC-MS instance count. The
   portal figures (1,374 protein interactions; 7,023 proteins; 11,739 genes; 21.4 TB) are
   now recorded as project-wide totals in `description` and explicitly disclaimed as
   non-instance counts in the SEC-MS instance.
2. `instances[CM4AI_instance_perturb_seq_mda].counts: 100` — removed. 100 is the number of
   perturbed chromatin regulators, not an instance count; the sources report no cell or
   instance count for that arm.
3. `instances[CM4AI_instance_perturb_seq_kolf2].counts: 11739` — retained but qualified:
   the description now states this is the reported number of targeted genes, not a count
   of sequenced cells.
4. `keywords` — "Medicine, Health and Life Sciences" removed. It is the Dataverse
   *Subject*, not a Keyword; it is now stated as the Subject in `description`.
5. `maintainers[CM4AI_maintainer_project].description` — corrected an inaccurate claim
   that the March 2025 release lists the same institutions (it omits UT Austin).
6. `ethical_reviews[CM4AI_ethical_review_ravitsky].description` — added the affiliation
   discrepancy (conflict 9).

No Phase 2 discovery required back-porting a *new* fact into the full record: the core
field inventory is a strict subset of the full inventory plus `distributions`, which is
derived from the same release file table already recorded in `file_collections`.

### Deliberate omissions

- **Byte counts.** `total_size_bytes`, `FileCollection.total_bytes` and
  `CoreDistribution.bytes` are omitted throughout. Dataverse reports only rounded display
  sizes ("3.8 GB", "23.8 MB", "31.1 KB"); converting these to integers would fabricate
  precision. Displayed sizes are recorded verbatim in each file description instead.
- **`issued` / `created_on`.** Omitted: the slots are `datetime` and the sources give
  dates only. Release dates are carried as strings in `distribution_dates` and
  `version_access`, and as `date`-typed values in `collection_timeframes`.
  `last_updated_on` is set to `2026-07-15T20:28:19Z`, which the source manifest curation
  note and the corpus give at full datetime precision.
- **`Instance.data_topic` / `data_substrate`.** Omitted: these slots carry
  `values_from: B2AI_TOPIC` / `B2AI_SUBSTRATE`, and the corpus supplies no Bridge2AI
  standards-registry identifiers.
- **`hipaa_compliant`.** Omitted: HIPAA status is not stated in any source. The three
  governance facts that *are* stated (Human Subjects: No; De-identified Samples: Yes; FDA
  Regulated: No) are recorded in `regulatory_restrictions` and `human_subject_research`.
- **`variables`, `splits`, `imputation_protocols`, `participant_privacy`,
  `participant_compensation`, `consent_revocations`, `collection_notifications`.**
  Omitted: no supporting content in the corpus.
- **`irb_approval`.** Omitted: no IRB identifier is reported; the project states its data
  are non-clinical and derived from tissue cultures.

### Schema-structure notes

Several single-valued object slots — `Creator.principal_investigator`,
`FundingMechanism.grantor`, `EthicalReview.contact_person`,
`EthicalReview.reviewing_organization`, `LicenseAndUseTerms.contact_person`,
`ExportControlRegulatoryRestrictions.governance_committee_contact` — are **not inlined**
in the schema (their ranges declare an identifier), so they take an identifier string
rather than a nested object. Values are therefore ORCID URIs where an ORCID is published
and stable local identifiers otherwise, and the corresponding names, emails and
affiliations are carried in the enclosing object's `description` so that no fact is lost
in either record. `Creator.affiliations` and `FundingMechanism.grants` declare
`inlined_as_list: true` and are emitted as nested objects.

### Post-correction validation (Phase 3)

Both records were re-validated after every correction; results are identical to the final
Phase 4 run recorded below.

## Phase 4 — strict full/core reconciliation

### Shared-slot derivation

Shared slots were derived at runtime from `Dataset` and `CoreDataset` with LinkML
`SchemaView` via `data_sheets_schema.d4d_pair_consistency.load_pair_schema()`. No
hand-written field list was used.

- **76 schema-identical slots** — must be present in both records or neither, with deeply
  identical parsed YAML including nested mapping values and list order.
- **1 projected slot** — `resources` (`Dataset` in full, `CoreDataset` in core).
- **Full-only slots (9), correctly absent from core** because `CoreDataset` does not
  declare them: `citation`, `collection_consents`, `direct_collection`,
  `file_collections`, `related_datasets`, `relationships`, `subsets`,
  `third_party_sharing`, `total_file_count`.
- **Core-only slot (1)**: `distributions`. `dialect` is omitted from both records because
  the dataset is not tabular (`is_tabular: false` in both).

Top-level slot counts: full 76, core 68.

### Identity result

All 76 schema-identical slots are present in both records with deeply identical content,
including the long narrative fields (`description`, `purposes`, `known_limitations`,
`license_and_use_terms.license_terms`, `version_access.versions_available`). Core does not
condense, paraphrase, reorder, or omit any shared content.

### Resource projection

`resources` matched by `id` with equal coverage across both records — 4 releases:

- `https://doi.org/10.18130/V3/HIGT4C` (current)
- `https://doi.org/10.18130/V3/K7TGEM` (historical)
- `https://doi.org/10.18130/V3/F3TD5R` (historical)
- `https://doi.org/10.18130/V3/B35XWX` (historical)

Every schema-identical slot inside each matched resource is deeply identical. The
full-only nested slots `file_collections` and `total_file_count` are omitted from the core
projection, which is the schema-correct behaviour, not a divergence.

### Related-content semantic review (`file_collections` ↔ `distributions`)

The validator reports 10 deterministic matches and 0 unmatched core distributions. That
warning marks content requiring semantic review; the review was performed and is recorded
here.

- **Coverage and scope.** Both sides describe exactly the ten files of the current June
  2026 release (`HIGT4C`), matching the Dataverse file table ("1 to 10 of 10 Files", File
  Type filter "Archive (10)") and the full record's `total_file_count: 10`. Historical
  release inventories exist only inside full's nested resources; core carries none, by
  schema design.
- **Names and paths.** Identical for all ten pairs. No directory prefixes appear in the
  June 2026 file table, so `path` is the bare file name on both sides. (The October 2025
  and June 2025 releases do use an `Images/` prefix; those inventories are full-only.)
- **Compression.** `zip` on both sides for all ten.
- **Formats.** Core adds `format: ZIP` and `media_type: application/zip`. Consistent with
  full's `compression: zip` and with the Dataverse "Archive (10)" file-type facet. No
  conflict.
- **Checksums.** `md5` is carried structurally only in core (`FileCollection` has no `md5`
  slot). The identical checksum strings appear verbatim in every full `FileCollection`
  description, so the two records agree character-for-character on all ten MD5 values.
- **Byte counts.** `bytes` and `total_bytes` are absent from both sides by the deliberate
  omission recorded above, so the validator's `bytes` vs `total_bytes` comparison has
  nothing to contradict. Displayed sizes are stated identically in the descriptions on
  both sides.
- **Descriptions.** Identical text on both sides for all ten files.
- **Access URLs and release scope.** Access routes are recorded once, in the shared
  identity slot `distribution_formats` (present identically in both records), rather than
  per distribution; no per-file access URL is asserted on either side, so no conflict is
  possible.

### Cross-record consistency of identity, version and access facts

- Top-level `doi: 10.18130/V3/HIGT4C`, `version: "2.0 (June 2026 Data Release (Beta),
  Dataverse version 2.0)"`, `page`, `publisher`, `license` and `last_updated_on:
  2026-07-15T20:28:19Z` agree with `resources[HIGT4C]`, with
  `version_access.latest_version_doi`, and with the `distribution_dates` entry for the
  June 2026 release, in both records.
- `license` agrees with `license_and_use_terms.license_terms`,
  `regulatory_restrictions.confidentiality_level: unrestricted`, and the CC BY-NC-SA 4.0
  deed text quoted in `prohibited_uses`.
- Differing `version`, `doi` and `status` values on the historical resource entries are
  release-scoped, each explicitly labelled "Historical release, superseded", and are
  therefore not contradictions with the current-release values at the top level.
- `is_tabular: false` in both; `dialect` absent from both.
- No unresolved contradiction remains within or between the two records.

### Commands run

```bash
poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_all.yaml \
  -C Dataset data/d4d_concatenated/claudecode_agent/2026-07-27_claude-opus-5_rep1/CM4AI_d4d.yaml

poetry run linkml-term-validator validate-data \
  data/d4d_concatenated/claudecode_agent/2026-07-27_claude-opus-5_rep1/CM4AI_d4d.yaml \
  --schema src/data_sheets_schema/schema/data_sheets_schema_all.yaml --target-class Dataset

poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml \
  -C CoreDataset data/d4d_concatenated/claudecode_agent_core/2026-07-27_claude-opus-5_rep1/CM4AI_d4d_core.yaml

poetry run linkml-term-validator validate-data \
  data/d4d_concatenated/claudecode_agent_core/2026-07-27_claude-opus-5_rep1/CM4AI_d4d_core.yaml \
  --schema src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml --target-class CoreDataset

poetry run python -m data_sheets_schema.d4d_pair_consistency \
  --full data/d4d_concatenated/claudecode_agent/2026-07-27_claude-opus-5_rep1/CM4AI_d4d.yaml \
  --core data/d4d_concatenated/claudecode_agent_core/2026-07-27_claude-opus-5_rep1/CM4AI_d4d_core.yaml \
  --sync-core

poetry run python -m data_sheets_schema.d4d_pair_consistency \
  --full data/d4d_concatenated/claudecode_agent/2026-07-27_claude-opus-5_rep1/CM4AI_d4d.yaml \
  --core data/d4d_concatenated/claudecode_agent_core/2026-07-27_claude-opus-5_rep1/CM4AI_d4d_core.yaml
```

### Final results

| Check | Result |
|---|---|
| `linkml-validate` full (`Dataset`) | PASS — "No issues found" |
| `linkml-term-validator` full (`Dataset`) | PASS — "Validation passed" |
| `linkml-validate` core (`CoreDataset`) | PASS — "No issues found" |
| `linkml-term-validator` core (`CoreDataset`) | PASS — "Validation passed" |
| `d4d_pair_consistency --sync-core` | PASS — 76 schema-identical slots; projected slots `['resources']` |
| `d4d_pair_consistency` (independent re-check) | PASS — 76 schema-identical slots; projected slots `['resources']` |

One validator warning remains by design: `semantic-review-required` on
`$.file_collections <-> $.distributions`. It flags related content for human-equivalent
review rather than an error; that review is recorded above with 10 deterministic matches,
0 unmatched core distributions, and zero contradictions.

### Files changed

- `data/d4d_concatenated/claudecode_agent/2026-07-27_claude-opus-5_rep1/CM4AI_d4d.yaml` (created; Phase 3 corrections applied)
- `data/d4d_concatenated/claudecode_agent_core/2026-07-27_claude-opus-5_rep1/CM4AI_d4d_core.yaml` (created; Phase 4 `--sync-core` applied once)
- `data/d4d_concatenated/claudecode_agent_core/2026-07-27_claude-opus-5_rep1/CM4AI_reconciliation.md` (this report)

No existing file was overwritten.
