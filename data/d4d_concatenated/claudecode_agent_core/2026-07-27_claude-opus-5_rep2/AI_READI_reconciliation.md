# AI_READI full/core reconciliation report

## Run identity

| Field | Value |
| --- | --- |
| Agent runtime | Claude Code |
| Provider | Anthropic |
| Model | claude-opus-5[1m] |
| Mode | four-phase project agent |
| Temperature | 0.0 |
| Generated | 2026-07-27 |
| Arm | BASELINE (document corpus only) |
| Version label | 2026-07-27_claude-opus-5_rep2 |

## Files

- Full: `data/d4d_concatenated/claudecode_agent/2026-07-27_claude-opus-5_rep2/AI_READI_d4d.yaml` (2,452 lines)
- Core: `data/d4d_concatenated/claudecode_agent_core/2026-07-27_claude-opus-5_rep2/AI_READI_d4d_core.yaml` (1,529 lines)
- Report: `data/d4d_concatenated/claudecode_agent_core/2026-07-27_claude-opus-5_rep2/AI_READI_reconciliation.md`

Line counts are informational metadata only, not a quality gate.

## Allowed inputs actually read

Factual source (the only one):

- `data/preprocessed/concatenated/AI_READI_preprocessed.txt` (10 documents, 6,229 lines)

Structure and selection references (not fact sources):

- `src/data_sheets_schema/schema/data_sheets_schema_all.yaml` (class `Dataset`)
- `src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml` (class `CoreDataset`)
- `src/data_sheets_schema/schema/D4D_Core.yaml`
- `data/preprocessed/source_manifest.yaml`
- `.claude/agents/d4d-provenance-guard.md`, `.claude/commands/d4d-full-core.md`, `.claude/commands/d4d-agent.md`

## Phase 3 — Source and provenance audit

### Provenance

- No prior full or core D4D record was read, searched, globbed, or cited. The output
  directories were listed once, before generation, only to confirm that the target version
  directory `2026-07-27_claude-opus-5_rep2` did not already exist. No file under
  `data/d4d_concatenated/`, `data/d4d_individual/`, or `data/ro-crate_packages/` was opened
  except the two files this run wrote.
- No evaluation report, reconciliation report, RO-Crate artifact, or live web content was used.
- No prior D4D content from the parent conversation was used as evidence.
- Every populated slot, nested class shape, cardinality, inlining behaviour, and enum value was
  derived at runtime from the LinkML schemas via `SchemaView`. No `d4d:docExample` value was
  copied into either record.

### Structure corrections made during Phase 1 validation

The following slots have object ranges but are **not** inlined in the schema, so they take
identifier strings rather than nested objects. The first draft emitted nested objects and
`linkml-validate` rejected them; the records were corrected to reference form and the
human-readable person/organization detail was moved into the enclosing object's `description`:

- `Creator.principal_investigator` (16 occurrences) → ORCID URI string
- `FundingMechanism.grantor` (2) → ROR URI / local CURIE string
- `EthicalReview.contact_person`, `EthicalReview.reviewing_organization` → identifier strings
- `LicenseAndUseTerms.contact_person`, `ExportControlRegulatoryRestrictions.governance_committee_contact` → ORCID URI strings

`Creator.affiliations` and `FundingMechanism.grants` **are** `inlined_as_list: true` and remain
nested objects. `issued` and `created_on` were changed to RFC 3339 form
(`2025-11-17T00:00:00+00:00`) to satisfy the `date-time` format check.

### Source conflicts identified and how they were resolved

| # | Conflict | Sources | Resolution |
| --- | --- | --- | --- |
| 1 | **Dataset version and release scope: v2.0.0 vs v3.0.0** | `dataset_documentation` and `fairhub_dataset` describe v2.0.0 (2.01 TB, 165,051 files); `dataset_documentation_v3`, `fairhub_dataset_v3` and `fairhub_dataset_v3_api` describe v3.0.0 (3.82 TB, 356,343 files, 2,280 participants, DOI 10.60775/fairhub.3) | Both records document **v3.0.0** as the current release, per the manifest's explicit instruction to prefer the v3 captures. The v2.0.0 figures are retained only inside `version_access.version_details`, explicitly scoped as the superseded release that FAIRhub marks "no longer accessible". |
| 2 | **Managing / lead organization** | `fairhub_dataset_v3_api` records `managingOrganization` and `leadSponsor` as "Washington University in St. Louis" (ROR `01yc7t268`), and gives that affiliation for Aaron Lee and Cecilia Lee. NIH RePORTER records the awardee organization as UNIVERSITY OF WASHINGTON; the license names the University of Washington as Licensor; the IRB of record is the UW IRB; the BMJ and Nature Metabolism author affiliations place both Lees at the University of Washington (`leeay@uw.edu`); the same FAIRhub `locationList` records University of Washington with ROR `00cvxb145`. | Resolved to **University of Washington** (ROR `00cvxb145`) on preponderance and authority. The string "Washington University in St. Louis" appears nowhere in either record. This is a probable data-entry error in the FAIRhub study metadata and is recorded here rather than propagated. |
| 3 | **Target enrollment: 4,000 vs 4,600** | `irb_protocol` (2022 application) states 4,600 people, but its own subject-group table sums to 4,000 (4 × 1,000). BMJ protocol (2025), Nature Metabolism (2024), the v3 healthsheet/README and the FAIRhub `enrollmentInfo` all state 4,000. | Resolved to **4,000** on recency and on the IRB document's own internal group table. The 4,600 figure is not asserted. |
| 4 | **Enrolment start: 18 vs 19 July 2023** | BMJ protocol: "Enrolment began on 18 July 2023". FAIRhub `startDateStruct` (Actual) and the v3 collection window: 2023-07-19. | Both retained with **explicit scope**: `collection_timeframes` carries a study-timeline entry starting 2023-07-18 (protocol publication, enrolment start) and a v3-release entry starting 2023-07-19 (FAIRhub "Collected" period). Neither is presented as contradicting the other. |
| 5 | **Longitudinal follow-up fraction: ~4% vs 10%** | Healthsheet: "Approximately 4% of participants are expected to undergo a follow-up examination in Year 4". NIH RePORTER and the IRB: longitudinal data from 10% of the cohort. | Both retained with attribution in `collection_timeframes` and `known_limitations`, phrased as an expected-versus-intended range rather than a single number. |
| 6 | **Acronym expansion** | BMJ: "Artificial Intelligence Ready and **Equitable** Atlas for Diabetes Insights". NIH RePORTER, healthsheet, README: "…Ready and **Exploratory** Atlas…". FAIRhub `officialTitle`: "AI Ready and Exploratory Atlas for Diabetes Insights". | The dataset `description` records "Equitable/Exploratory" so neither upstream expansion is silently dropped. |
| 7 | **License version** | The captured license document is AI-READI-LICENSE-**v1.0** (`10.5281/zenodo.10642459`, University of Washington as Licensor). The FAIRhub v3 record, healthsheet and README all point to the current license at `10.5281/zenodo.17555036`, named "AI-READI custom license v2.0". | The top-level `license` slot carries the **current** v2.0 URI. `license_and_use_terms.license_terms` carries the current-license statements first, then the detailed v1.0 clauses each explicitly labelled "Version 1.0 license section N", so the historical terms are never presented as the operative current terms. |
| 8 | **Visit duration: 2.5–4 h vs 3–4 h** | BMJ protocol: "a single visit lasting between 2.5 and 4 hours". Nature Metabolism Fig. 1 and the IRB: 3–4 hours. | The wider protocol-publication range (2.5–4 hours) is used in the dataset description; the narrower figure is not contradicted, and no per-source claim is asserted. |
| 9 | **Blood volume: 53 mL vs 50–60 mL** | BMJ: "Blood (53 mL) is collected". IRB: "approximately 50-60 ml of blood". | Both retained in `collection_mechanisms`, attributed ("approximately 50 to 60 mL, described in the protocol publication as 53 mL"). |
| 10 | **NIH RePORTER project link** | Healthsheet cites `project-details/10885481`; README cites `project-details/10471118`; the manifest-selected NIH RePORTER source is application 10471118. | The manifest-selected record (application ID 10471118, project number 1OT2OD032644-01) is cited in `funders`. Both point to core project OT2OD032644, so there is no factual conflict. |
| 11 | **Grant number transcription** | The healthsheet writes the grant as "OT2ODO32644" (letter O in place of a zero); every other source writes OT2OD032644. | **OT2OD032644** used throughout (8 occurrences in full, 7 in core). The healthsheet typo is not propagated. |

### Stale, unsupported or mis-scoped assertions rejected

- **Stale healthsheet text.** Healthsheet composition Q4 states the dataset "contains data from
  all participants who have been enrolled during the first year of data collection" — text
  carried over from the v2.0.0 datasheet and inconsistent with v3.0.0's own two-year collection
  window (2023-07-19 to 2025-05-01) and 2,280 participants. Neither record repeats "first year";
  `sampling_strategies.strategies` says "all participants enrolled during the covered data
  collection period".
- **Unanswered healthsheet questions were left empty, not filled.** Composition Q13
  (re-identification avoidance measures) and Preprocessing Q1 (de-identification pre-processing)
  have empty responses in the source; `is_deidentified.deidentification_details` records that they
  were left unanswered rather than substituting plausible content. The erratum question is
  likewise unanswered, so `errata.erratum_url` was **removed** during the audit — pointing it at
  the documentation site would have implied an erratum exists.
- **FAIRhub record 4 ("Mini Version").** The manifest states this is a distinct record that was
  not captured. It is mentioned in `version_access.version_details` only as "a smaller version is
  available for pipeline development" (wording present in the captured FAIRhub v3 HTML and v3
  documentation), with no DOI asserted and no `related_datasets` entry.
- **`data_topic` / `data_substrate` omitted.** These slots carry `values_from: B2AI_TOPIC` /
  `B2AI_SUBSTRATE`; the corpus supplies no Bridge2AI standards-registry identifiers, so the slots
  were omitted rather than populated with invented CURIEs.
- **`dialect` omitted from core.** No CSV dialect (delimiter, quote char, header) is described
  anywhere in the corpus.
- **Documentation-page metadata not attributed to the dataset.** The docs site footer records
  "Last updated on Jun 4, 2026 by Eamon Dysinger"; that is documentation-page provenance, not
  dataset provenance, so `last_updated_on` and `modified_by` are unset in both records.
- **`format` / `media_type` omitted for DICOM, WFDB, Open mHealth and ESDS distributions.**
  `FormatEnum` and `MediaTypeEnum` contain no `application/dicom` or equivalent member. Rather
  than mis-binning DICOM as another format, those fields are omitted and each core distribution
  description states explicitly why.

### Internal-consistency checks performed (all pass)

| Check | Result |
| --- | --- |
| Sum of `file_count` over 10 file collections == `total_file_count` | 356,343 == 356,343 ✔ |
| Sum of `total_bytes` over 9 data-type directories vs `total_size_bytes` | 3,815,969,360,064 vs 3,815,969,779,678; difference 419,614 bytes attributed to the 9 root metadata files ✔ |
| 356,334 files in data-type directories + 9 root metadata files | == 356,343 ✔ (this arithmetic is what justifies the 10th `file_collections` / `distributions` entry) |
| Train split: race, sex and diabetes-status counts each sum to 1,576 | ✔ |
| Validation split: each sums to 352 | ✔ |
| Test split: each sums to 352 | ✔ |
| 1,576 + 352 + 352 | == 2,280 ✔ |
| Per-category totals across splits | Hispanic 380 / Asian 545 / Black 519 / White 836; male 951 / female 1,329; no-DM 776 / lifestyle 560 / oral 686 / insulin 258 — all match the published totals ✔ |
| Version participant counts | 204 + 863 = 1,067; 1,067 + 1,213 = 2,280 ✔ |
| Repeated identifiers across both records | `10.60775/fairhub.3`, `10.5281/zenodo.17555036`, `OT2OD032644`, `NCT06002048`, `STUDY00016228` used consistently, with no competing spellings ✔ |

One nominal-versus-actual note, recorded here rather than treated as an error: the project
describes the split as "70%/15%/15%", while the published counts give 69.1% / 15.4% / 15.4%. Both
the stated proportions and the exact counts are carried in `splits.split_details` and the three
`subsets`, so a reader can see the rounding.

### Phase 2 discoveries back-ported to the full record

None required. Phase 2 derived `distributions` from the same evidence already captured in
`file_collections`, and the Phase 2 re-read of the corpus surfaced no fact that the full record had
missed or recorded differently. The only Phase 3 edit to the full record was the removal of
`errata.erratum_url` described above, applied before the core was built.

## Phase 4 — Strict full/core reconciliation

### Shared-slot derivation

Shared slots were derived at runtime from `Dataset` and `CoreDataset` with LinkML `SchemaView` via
`data_sheets_schema.d4d_pair_consistency`. No hand-written field list was used.

- **Schema-identical slots: 76.** Of these, 68 are populated in the full record and were copied to
  core with deep identity. The 8 identity slots absent from the full record are absent from core
  as well: `annotation_analyses`, `compression`, `conforms_to_class`, `imputation_protocols`,
  `last_updated_on`, `machine_annotation_tools`, `modified_by`, `was_derived_from`. Presence and
  absence therefore match on all 76.
- **Projected slots: 1** (`resources`, `Dataset` in full versus `CoreDataset` in core). It is
  populated in neither record, so the projection is vacuously satisfied.
- **Full-only slots** (correctly absent from core, since `CoreDataset` does not declare them):
  `file_collections`, `total_file_count`, `total_size_bytes`, `subsets`, `splits`, `relationships`,
  `direct_collection`, `collection_notifications`, `collection_consents`, `consent_revocations`,
  `participant_privacy`, `participant_compensation`, `third_party_sharing`, `variables`, `citation`,
  `related_datasets`.
- **Core-only slots**: `distributions` (populated) and `dialect` (omitted — unsupported).

No narrative field was condensed, paraphrased, reordered or dropped in core. Core carries the
identical text of every shared narrative slot, including the full `description`, all 17 `creators`,
the 12-item `license_and_use_terms.license_terms`, and every multi-paragraph collection/ethics/uses
section. The full record's 15 `variables` entries are full-only and have no core counterpart,
because `CoreDataset` does not declare `variables`.

### Related-content mapping and semantic review

The validator emits one warning by design, marking `file_collections` ↔ `distributions` as
requiring semantic review. That review was performed and is recorded here.

| Full `file_collections` | Core `distributions` | path | bytes | file count | format |
| --- | --- | --- | --- | --- | --- |
| cardiac_ecg | cardiac_ecg | cardiac_ecg | 302,931,703 | 4,515 | WFDB — no enum member, omitted in core, named in description |
| clinical_data | clinical_data | clinical_data | 176,182,781 | 7 | CSV / text/csv |
| environment | environment | environment | 55,625,676,514 | 2,232 | NASA ESDS ASCII — no enum member |
| retinal_flio | retinal_flio | retinal_flio | 1,069,466,876,718 | 7,969 | DICOM — no enum member |
| retinal_oct | retinal_oct | retinal_oct | 1,317,625,293,027 | 56,478 | DICOM — no enum member |
| retinal_octa | retinal_octa | retinal_octa | 1,155,908,809,724 | 173,721 | DICOM — no enum member |
| retinal_photography | retinal_photography | retinal_photography | 174,381,046,406 | 93,921 | DICOM — no enum member |
| wearable_activity_monitor | wearable_activity_monitor | wearable_activity_monitor | 38,313,536,220 | 15,245 | Open mHealth — no enum member |
| wearable_blood_glucose | wearable_blood_glucose | wearable_blood_glucose | 4,169,006,971 | 2,246 | Open mHealth — no enum member |
| root metadata files | root metadata files | (no path) | (not stated) | 9 | mixed MD/JSON/TSV/TXT |

Verified mechanically: the two name sets are equal (10 = 10); every `path` matches; every
`total_bytes` equals the corresponding `bytes`; and every full-side `file_count` appears verbatim
in the matching core description, because `CoreDistribution` has no `file_count` slot. Checksums
(`hash`, `md5`, `sha256`) are omitted from every distribution because the corpus supplies none.

Scope reconciliation of the related quantities:

- `total_file_count` (356,343) and `total_size_bytes` (3,815,969,779,678) in full describe the whole
  dataset. The core distributions describe the same scope decomposed by directory, and the two sum
  to the full totals exactly (see the arithmetic table above). No scope mismatch.
- `distribution_formats.access_urls` is a schema-identical slot and is byte-identical in both
  records; it lists the FAIRhub media types (`application/dicom`, `text/markdown`, `text/csv`,
  `application/json`) in its description, which is consistent with the per-directory format
  statements in the core distributions.
- `is_tabular` is `false` in both records and is consistent with the distribution mix: only
  `clinical_data` and the `participants.tsv` metadata file are tabular; the bulk of the dataset by
  both size and file count is imaging and waveform data.
- `dialect` is unset in core, so there is nothing to contradict `is_tabular` or any format claim.
- Top-level identity, version and access facts (`id`, `doi`, `version`, `issued`, `license`,
  `page`, `download_url`, `publisher`, `status`) agree between the two records by deep identity,
  and agree internally with `version_access`, `distribution_dates` and `license_and_use_terms`.
- Historical versus current release values are kept distinct rather than treated as contradictions:
  v1.0.0 (204 participants, 2024-05-03), v2.0.0 (1,067 participants, 2024-11-08, 2.01 TB / 165,051
  files, marked no longer accessible) and v3.0.0 (2,280 participants, 2025-11-17, 3.82 TB / 356,343
  files, current) each appear only inside version-scoped narrative.

**Unresolved contradictions within or between the two records: none.**

## Commands run

```bash
poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_all.yaml \
  -C Dataset data/d4d_concatenated/claudecode_agent/2026-07-27_claude-opus-5_rep2/AI_READI_d4d.yaml

poetry run linkml-term-validator validate-data \
  data/d4d_concatenated/claudecode_agent/2026-07-27_claude-opus-5_rep2/AI_READI_d4d.yaml \
  --schema src/data_sheets_schema/schema/data_sheets_schema_all.yaml --target-class Dataset

poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml \
  -C CoreDataset data/d4d_concatenated/claudecode_agent_core/2026-07-27_claude-opus-5_rep2/AI_READI_d4d_core.yaml

poetry run linkml-term-validator validate-data \
  data/d4d_concatenated/claudecode_agent_core/2026-07-27_claude-opus-5_rep2/AI_READI_d4d_core.yaml \
  --schema src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml --target-class CoreDataset

poetry run python -m data_sheets_schema.d4d_pair_consistency \
  --full data/d4d_concatenated/claudecode_agent/2026-07-27_claude-opus-5_rep2/AI_READI_d4d.yaml \
  --core data/d4d_concatenated/claudecode_agent_core/2026-07-27_claude-opus-5_rep2/AI_READI_d4d_core.yaml \
  --sync-core

poetry run python -m data_sheets_schema.d4d_pair_consistency \
  --full data/d4d_concatenated/claudecode_agent/2026-07-27_claude-opus-5_rep2/AI_READI_d4d.yaml \
  --core data/d4d_concatenated/claudecode_agent_core/2026-07-27_claude-opus-5_rep2/AI_READI_d4d_core.yaml
```

## Final results

| Check | Result |
| --- | --- |
| Full — `linkml-validate` against `Dataset` | PASS (no issues found) |
| Full — `linkml-term-validator` | PASS |
| Core — `linkml-validate` against `CoreDataset` | PASS (no issues found) |
| Core — `linkml-term-validator` | PASS |
| Pair consistency (`--sync-core`) | PASS — 76 schema-identical slots; sync was a no-op on content |
| Pair consistency (independent re-run) | PASS — 76 schema-identical slots; 1 semantic-review warning, reviewed above |
| Phase 3 provenance result | Clean — no prior generated D4D, evaluation, reconciliation report, RO-Crate artifact, or web content read or cited |
| Phase 4 consistency result | Clean — deep identity on all shared slots; projection and related content reconciled with zero unresolved contradictions |
