# AI_READI full/core reconciliation — 2026-07-28_claude-opus-5-generic_rep2

- **Arm**: BASELINE (input documents only)
- **Mode**: four-phase project agent, generic prompt
- **Prompt**: `src/download/prompts/d4d_generic_arm_prompt.md` (identical for all projects)
- **Runtime / provider / model**: Claude Code / Anthropic / claude-opus-5[1m], temperature 0.0
- **Declared input bundle**: `data/preprocessed/concatenated/AI_READI_preprocessed.txt`
- **Source manifest**: `data/preprocessed/source_manifest.yaml`
- **Full**: `data/d4d_concatenated/claudecode_agent/2026-07-28_claude-opus-5-generic_rep2/AI_READI_d4d.yaml`
- **Core**: `data/d4d_concatenated/claudecode_agent_core/2026-07-28_claude-opus-5-generic_rep2/AI_READI_d4d_core.yaml`

## Pinned referent

`Dataset` admits one referent. The referent chosen is **the AI-READI "Flagship Dataset of
Type 2 Diabetes from the AI-READI Project", version 3.0.0, FAIRhub record 3, DOI
10.60775/fairhub.3**. This is the release the bundle documents most completely: the FAIRhub API
capture carries its structured metadata, healthsheet, readme, study description and structure
description; the v3 documentation capture and the v3 FAIRhub HTML capture corroborate identity,
size, license and version list.

Consequences held consistently across both records:

- Top-level identity, version, size, count, date, license and access facts describe v3.0.0.
- Earlier releases (v1.0.0, v2.0.0) are **not** treated as parts of the referent. They are
  represented as explicitly scoped historical statements in `version_access.version_details`
  and `distribution_dates.release_dates`, and as `related_datasets` entries typed
  `is_new_version_of` in the full record.
- `resources` is empty in both records, so the `Dataset` → `CoreDataset` projection of that slot
  is vacuous.

## Phase 3 — source and provenance audit

### Provenance

- Factual inputs read during this run: the declared bundle, `source_manifest.yaml`, the full and
  core LinkML schemas, and the repository generation/validation instructions
  (`d4d_generic_arm_prompt.md`, `d4d-provenance-guard.md`, `d4d-full-core.md`, `d4d-agent.md`).
- **No prior generated D4D record was read**, from any arm, label or date. Nothing under
  `data/d4d_concatenated/` was opened other than the two files this run wrote, and no
  `*_crate_d4d.yaml` or `*_crate_mapped_d4d.yaml` under `data/ro-crate_packages/` was opened.
  Output directory *names* under `data/d4d_concatenated/claudecode_agent/` were listed once, to
  confirm the run label was unused; no contents were read.
- No evaluation report, reconciliation report, test fixture or schema example supplied a value.
- Phase 2 read exactly one generated file: the Phase 1 full record at this run's label.
- No live web content was fetched.

### Source disagreements — represented, not silently resolved

| Fact | Disagreement | Where represented |
|---|---|---|
| Managing organization / lead sponsor | FAIRhub study metadata: Washington University in St. Louis (ROR 01yc7t268). NIH RePORTER 10471118: University of Washington. License agreement: University of Washington as Licensor. | `creators[0].affiliations[0].description`, `creators` entry for Aaron Y. Lee |
| Target enrollment | 4000 (protocol publication, Nature Metabolism, study metadata `enrollmentCount`, 4×1000 group table) vs 4600 (IRB application) | `sampling_strategies[0].strategies` |
| Enrolment start | 18 July 2023 (protocol publication) vs 2023-07-19 (FAIRhub study metadata, actual) | `collection_timeframes[1].timeframe_details` |
| Longitudinal follow-up fraction | ~4% (protocol publication) vs ~10% (project design, IRB application) | `known_limitations` (cross-sectional design) |
| Blood volume drawn | 53 mL (protocol publication) vs 50–60 mL (IRB application) | `collection_mechanisms` (biospecimen) |
| Project end date | NIH RePORTER project end 2025-08-31; study metadata anticipated completion 2027-01-01; recruitment to 2026-11-30 (protocol publication) | `collection_timeframes[1].timeframe_details`, `funders[0].description` |
| Licence version | v3.0.0 metadata: "AI-READI custom license v2.0" (zenodo.17555036). Bundle carries AI-READI-LICENSE-v1.0 (zenodo.10642459). | `license`, `license_and_use_terms.license_terms` |
| Acronym expansion | "…Equitable Atlas…" / "…Equitable for…" (protocol publication) vs "…Exploratory Atlas…" (NIH RePORTER, readme, study title) | `description` |
| Release scope wording | Healthsheet composition Q4 says the release holds "all participants … enrolled during the first year"; the same healthsheet scopes v3.0.0 to 2023-07-19 → 2025-05-01 and 2280 participants | `sampling_strategies[1].strategies` |

### Superseded sources in the bundle

The manifest marks `dataset_documentation` (docs/2) and `fairhub_dataset` (FAIRhub record 2) as
superseded by their v3 counterparts, retained as the only surviving record of the v2.0.0 release.
Their figures — 2.01 TB across 165,051 files, and "This version of the dataset is no longer
accessible" — were **not** merged into the top-level totals. They are carried with explicit
historical scope in `version_access.version_details` and `related_datasets`. The top-level
`total_file_count` (356343) and `total_size_bytes` (3815969779678) come from the v3.0.0 FAIRhub
API capture only.

### Deliberate omissions

- `variables` — the bundle documents domains, devices and file-format standards, not per-variable
  metadata. The clinical laboratory table supplies *reference* ranges, which are not the observed
  minimum/maximum of the released values; mapping them onto `minimum_value` / `maximum_value`
  would misstate them, so the slot is omitted rather than filled.
- `dialect` (core-only) — the bundle gives no delimiter, quote or header conventions.
- `errata` — the healthsheet erratum question is answered with an empty string; the CHANGELOG is
  a version-change record, not an erratum.
- `imputation_protocols`, `annotation_analyses`, `machine_annotation_tools` — no labelling or
  annotation was performed; the one relevant statement (missing values filled from elsewhere in a
  participant's record under site-PI approval) is a data-editing rule and is recorded in
  `cleaning_strategies` and `missing_data_documentation.handling_strategy`.
- `parent_datasets`, `compression`, `created_on`, `last_updated_on`, `status`, `was_derived_from`,
  `conforms_to_class`, `conforms_to_schema`, `created_by`, `modified_by` — unsupported.
- `data_topic` / `data_substrate` on `Instance` and `unit` on `VariableMetadata` — these are
  `uriorcurie` ontology-term slots and the bundle names no term identifiers for them.

### Schema-enum projections (values derived from prose, flagged for transparency)

- `regulatory_restrictions.hipaa_compliant: compliant` — from "the public set is stripped of PHI
  as defined by the HIPAA Privacy Rule via the Safe Harbor method" and `deIdentHIPAA: true`.
- `regulatory_restrictions.confidentiality_level: restricted` — from
  `accessType: PublicDownloadSelfAttestationRequired` plus the separate controlled-access tier.
- `license_and_use_terms.data_use_permission: [disease_specific_research]` — the only permission
  enum the bundle states explicitly ("agreeing to use the data only for type 2 diabetes related
  research"). Commercial reuse is permitted by the licence and is recorded in prose rather than
  forced onto a non-matching enum value.
- `maintainers[0].role: academic_institution` — the AI-READI team is a multi-institution academic
  consortium; no closer enum value exists.
- `credit_roles` is left empty everywhere: the bundle records study roles ("Study Principal
  Investigator", "Writing Committee") that do not map cleanly to CRediT terms.

### Corrections made during Phase 3

One correction. The enrollment-target disagreement (4000 vs 4600) and the stale healthsheet
"first year" wording were not captured in the first Phase 1 draft; both were back-ported into the
full record's `sampling_strategies` and the core record was regenerated from the corrected full
record. No other fact changed. No fact was corrected in core-only direction, and no Phase 2
discovery required a back-port beyond this one.

### Structural corrections

`principal_investigator` (`Creator` → `Person`), `grantor` (`FundingMechanism` → `Grantor`) and
`reviewing_organization` (`EthicalReview` → `Organization`) are single-valued **non-inlined**
slots, so they take an identifier string, not a nested object. The first draft nested objects and
failed validation; the values were replaced with ORCID/ROR identifiers and the personal names,
degrees, affiliations and contact emails moved into the surrounding `Creator.description` text,
which the schema does permit.

## Phase 4 — strict full/core reconciliation

Shared slots were derived at runtime with LinkML `SchemaView` over `Dataset` and `CoreDataset`;
no hand-written field list was used.

- **Schema-identical shared slots: 76.** Every one is present in both records or absent from
  both, with deeply identical parsed YAML content including nested mapping values and list order.
  Narrative fields are byte-for-byte equal in content: core condenses nothing.
- **Populated top-level slots**: full 77, core 63.
- **Full-only slots (schema projection, 17 defined; 15 populated and therefore dropped in core)**:
  `citation`, `collection_consents`, `collection_notifications`, `consent_revocations`,
  `direct_collection`, `file_collections`, `participant_compensation`, `participant_privacy`,
  `related_datasets`, `relationships`, `splits`, `subsets`, `third_party_sharing`,
  `total_file_count`, `total_size_bytes`. (`parent_datasets` and `variables` are full-only in the
  schema but unpopulated here.) These are absences mandated by `CoreDataset`, not divergences.
- **Core-only slots**: `distributions` (populated), `dialect` (omitted — no evidence).
- **Projected slot with differing range**: `resources` (`Dataset` in full, `CoreDataset` in core).
  Empty in both; equal coverage trivially holds.

### Related-content mapping and semantic review

`file_collections` (full) ↔ `distributions` (core) — the validator reports 10 deterministic
matches and no unmatched core distributions. Reviewed field by field:

- **Identity**: 1:1 by `id`; the ten collection ids are reused verbatim as distribution ids, so
  the correspondence is machine-checkable. `name` and `description` are carried unchanged.
- **Paths**: the nine datatype directories (`cardiac_ecg`, `clinical_data`, `environment`,
  `retinal_flio`, `retinal_oct`, `retinal_octa`, `retinal_photography`,
  `wearable_activity_monitor`, `wearable_blood_glucose`) carry identical `path` values in both.
  The tenth entry (metadata and documentation files) has no single directory path in either
  record.
- **Formats**: `FileCollection.conforms_to` names the per-datatype standard (WFDB, OMOP CDM,
  ESDS ASCII, DICOM, Open mHealth, CDS v0.1.1). `CoreDistribution` has no `conforms_to`; it has
  `format` (`FormatEnum`) and `media_type` (`MediaTypeEnum`), neither of which admits DICOM,
  WFDB, OMOP CDM, ESDS or Open mHealth. `format`/`media_type` are therefore asserted only for
  `clinical_data` (`CSV` / `text/csv`), which the bundle states explicitly. The remaining
  standards are not lost: they are stated in the core record's `distribution_formats` and
  `conforms_to`. **No contradiction** — core asserts a strict subset of the full record's format
  claims.
- **Compression**: absent in both records and at both levels; the bundle states none.
- **Checksums and byte counts**: `bytes`, `hash`, `md5`, `sha256` are omitted from every
  distribution; the bundle publishes no per-directory sizes or checksums.
- **Counts vs distribution-level values**: `total_file_count` (356343) and `total_size_bytes`
  (3815969779678) are full-only and whole-dataset scoped. Core carries no distribution-level file
  counts or byte totals, so there is nothing at a matching scope to conflict with them.
- **`is_tabular`**: `false` in both (schema-identical, deeply equal). Consistent with the mixed
  tabular / DICOM imaging / waveform composition described in both records.
- **Release scope**: every distribution describes the v3.0.0 release. No distribution carries a
  historical-release claim, so the historical v2.0.0 figures held in `version_access` cannot
  collide with distribution content.

### Cross-record identity, version and access consistency

- `id` (`https://doi.org/10.60775/fairhub.3`), `doi` (`10.60775/fairhub.3`), `version` (`3.0.0`),
  `page`, `download_url`, `publisher`, `license`, `language`, `title`, `name` and `keywords` are
  schema-identical shared slots and are deeply equal in both records.
- `version_access.latest_version_doi` resolves to the same record as `id` and `doi`.
- `version_access.versions_available` (3.0.0 → 2025-11-17, 2.0.0 → 2024-11-08, 1.0.0 →
  2024-05-03) agrees with `distribution_dates.release_dates` in both records.
- `updates.frequency` ("approximately annually") agrees with `version_access.version_details`
  ("new versions approximately once a year") and with `retention_limit` ("no limits"). Both
  records state that the dataset is not updated in place.
- `human_subject_research.irb_approval` (STUDY00016228, 20 December 2022) agrees with
  `ethical_reviews[0].review_details` in both records.
- Participant counts are consistent everywhere they appear: `instances[0].counts` = 2280;
  `subsets` (full only) 1576 + 352 + 352 = 2280; `splits`/`subpopulations` aggregate counts sum to
  2280; `version_access.version_details` scopes 204 and 1067 to v1.0.0 and v2.0.0 respectively.
- **Known projection loss (not a contradiction)**: the v1.0.0/v2.0.0 `related_datasets` links and
  the recommended-split `subsets`/`splits` content exist only in the full record, because
  `CoreDataset` defines no counterpart slots. The core record still carries the version history
  through `version_access` and the split rationale through `labeling_strategies` and
  `future_use_impacts`.

**Unresolved contradictions within or between the two records: none.**

## Commands run

```bash
poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_all.yaml \
  -C Dataset data/d4d_concatenated/claudecode_agent/2026-07-28_claude-opus-5-generic_rep2/AI_READI_d4d.yaml
poetry run linkml-term-validator validate-data \
  data/d4d_concatenated/claudecode_agent/2026-07-28_claude-opus-5-generic_rep2/AI_READI_d4d.yaml \
  --schema src/data_sheets_schema/schema/data_sheets_schema_all.yaml --target-class Dataset

poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml \
  -C CoreDataset data/d4d_concatenated/claudecode_agent_core/2026-07-28_claude-opus-5-generic_rep2/AI_READI_d4d_core.yaml
poetry run linkml-term-validator validate-data \
  data/d4d_concatenated/claudecode_agent_core/2026-07-28_claude-opus-5-generic_rep2/AI_READI_d4d_core.yaml \
  --schema src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml --target-class CoreDataset

poetry run python -m data_sheets_schema.d4d_pair_consistency \
  --full data/d4d_concatenated/claudecode_agent/2026-07-28_claude-opus-5-generic_rep2/AI_READI_d4d.yaml \
  --core data/d4d_concatenated/claudecode_agent_core/2026-07-28_claude-opus-5-generic_rep2/AI_READI_d4d_core.yaml \
  --sync-core

poetry run python -m data_sheets_schema.d4d_pair_consistency \
  --full data/d4d_concatenated/claudecode_agent/2026-07-28_claude-opus-5-generic_rep2/AI_READI_d4d.yaml \
  --core data/d4d_concatenated/claudecode_agent_core/2026-07-28_claude-opus-5-generic_rep2/AI_READI_d4d_core.yaml

poetry run d4d provenance record --project AI_READI --method claudecode_agent \
  --label 2026-07-28_claude-opus-5-generic_rep2 \
  --input-bundle data/preprocessed/concatenated/AI_READI_preprocessed.txt
```

## Results

| Check | Result |
|---|---|
| Full schema validation (`Dataset`) | PASS — no issues found |
| Full ontology term validation | PASS |
| Core schema validation (`CoreDataset`) | PASS — no issues found |
| Core ontology term validation | PASS |
| Pair consistency, `--sync-core` | PASS — 76 schema-identical slots; sync was a no-op |
| Pair consistency, final independent run | PASS — 76 schema-identical slots; projected slots `['resources']` |
| Related-content warning | `file_collections` ↔ `distributions`, 10 matches, 0 unmatched — semantic review completed above |
| Provenance record | `AI_READI_provenance.yaml`, `record_mode: live` |

Files changed by this run (three, as declared; plus the provenance record the playbook requires):

- `data/d4d_concatenated/claudecode_agent/2026-07-28_claude-opus-5-generic_rep2/AI_READI_d4d.yaml`
- `data/d4d_concatenated/claudecode_agent_core/2026-07-28_claude-opus-5-generic_rep2/AI_READI_d4d_core.yaml`
- `data/d4d_concatenated/claudecode_agent_core/2026-07-28_claude-opus-5-generic_rep2/AI_READI_reconciliation.md`
- `data/d4d_concatenated/claudecode_agent_core/2026-07-28_claude-opus-5-generic_rep2/AI_READI_provenance.yaml`

Line counts (informational metadata only, never a quality gate): full 1959 lines / 102,384 bytes /
77 populated top-level slots; core 1295 lines / 86,125 bytes / 63 populated top-level slots.
