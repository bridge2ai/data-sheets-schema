# AI_READI full/core reconciliation — 2026-07-28_claude-opus-5-generic_rep3

- **Arm:** BASELINE (input documents only)
- **Prompt:** `src/download/prompts/d4d_generic_arm_prompt.md` (identical text for all projects)
- **Runtime / model:** Claude Code, Anthropic, `claude-opus-5[1m]`, temperature 0.0
- **Declared input bundle:** `data/preprocessed/concatenated/AI_READI_preprocessed.txt`
- **Source manifest:** `data/preprocessed/source_manifest.yaml`
- **Full:** `data/d4d_concatenated/claudecode_agent/2026-07-28_claude-opus-5-generic_rep3/AI_READI_d4d.yaml`
- **Core:** `data/d4d_concatenated/claudecode_agent_core/2026-07-28_claude-opus-5-generic_rep3/AI_READI_d4d_core.yaml`

## Phase 3 — source and provenance audit

### Provenance boundary

The only factual inputs read in this run were the declared bundle, the source manifest, and the
LinkML schema files. No file under `data/d4d_concatenated/`, `data/d4d_individual/`, or
`data/ro-crate_packages/` was read, searched, or listed for content; the two output directories
were checked only for prior existence of the run label (both absent, so nothing was overwritten).
No evaluation report, test fixture, or example record was consulted. Structure was derived at
runtime from `Dataset` and `CoreDataset` with LinkML `SchemaView` rather than from any prior
record.

### Choice of referent

`Dataset` admits one referent. The bundle describes both a study (AI-READI, an observational
cross-sectional study still enrolling) and a released dataset. The referent chosen is **the
released dataset, FAIRhub record 3, "Flagship Dataset of Type 2 Diabetes from the AI-READI
Project", version 3.0.0, DOI 10.60775/fairhub.3**. This is the best-supported referent: the
bundle contains that record's full structured metadata (`fairhub_dataset_v3_api`), its HTML
landing page, and its documentation, while the study-level sources describe the process that
produced it. Study-level facts (target enrolment, recruitment protocol, IRB, consent, devices)
are recorded in the slots that describe how the dataset came to be, with their study scope stated
in the text. The same referent is held consistently in both records.

### Source disagreements represented rather than resolved

1. **Managing organization / lead sponsor.** The FAIRhub study description names *Washington
   University in St. Louis* (ROR `01yc7t268`) as lead sponsor, managing organization, and the
   affiliation of Aaron Lee, Cecilia S. Lee and the central contact. NIH RePORTER names
   *University of Washington* as the awardee organization for OT2OD032644; the BMJ Open and
   Nature Metabolism author lists give University of Washington affiliations for the same
   investigators; and the AI-READI Data License Agreement v1.0 names the University of Washington
   as Licensor. Both organizations are carried as distinct `Organization` entries under
   `creators[0].affiliations`, each with the role its own source assigns, and the discrepancy is
   stated in the `creators` descriptions. Neither was silently selected and they were not merged.
2. **License version.** The FAIRhub v3.0.0 record names "AI-READI custom license v2.0"
   (`https://doi.org/10.5281/zenodo.17555036`); the license document actually contained in the
   bundle is the earlier University of Washington AI-READI Data License Agreement v1.0
   (`https://doi.org/10.5281/zenodo.10642459`). Both are recorded in `license` and
   `license_and_use_terms.license_terms` with their scope stated, and the v1.0 clauses quoted in
   `prohibited_uses` and `ip_restrictions` are attributed to v1.0 explicitly. The text of v2.0 is
   not in the bundle.
3. **Target enrolment.** 4000 (BMJ Open protocol, FAIRhub study description
   `enrollmentCount`, Nature Metabolism) versus 4600 (UW IRB protocol) versus "4,000+" (NIH
   RePORTER). The 4000 figure appears in the dataset-facing sources and the 4600 figure in the
   IRB application; both are retained where their source states them rather than being
   reconciled to one number. The realised count for this release (2280) is separate and is not
   in conflict with either.
4. **Collection start date.** FAIRhub records `2023-07-19`; the BMJ Open protocol states
   enrolment began 18 July 2023. `collection_timeframes.start_date` uses the dataset record's
   value and the narrative states the protocol's date alongside it.
5. **De-identification characterisation.** FAIRhub records `deIdentType: NoDeIdentification`
   with the explanation that no identifiers were collected, while the Nature Metabolism comment
   states the public set is stripped of PHI via HIPAA Safe Harbor. Both statements are recorded
   in `is_deidentified` and `participant_privacy` with attribution; they are complementary rather
   than contradictory (nothing to remove versus verification that nothing identifiable remains).
6. **Demographic subpopulations.** The healthsheet answers "No" to whether the dataset
   identifies demographic sub-populations, because sex and race/ethnicity were removed from this
   release; the README split table nevertheless reports race/ethnicity and sex counts, and the
   study design targets balanced groups. `subpopulations` carries
   `subpopulation_elements_present: false` for the released dataset and states the study-level
   design and split-table figures with their scope, rather than asserting a single answer.
7. **Documentation version.** The manifest retains the v2.0.0 documentation and the v2.0.0
   FAIRhub record as superseded sources, instructing that the v3 captures be preferred where they
   disagree. That instruction was followed: all identity, size, count, date, license and access
   facts are taken from the v3.0.0 sources, and v2.0.0 facts appear only in `version_access` and
   `related_datasets` where they are explicitly historical.

### Internal consistency checks performed

| Check | Result |
|---|---|
| Sum of `file_collections[].file_count` vs `total_file_count` | 356,334 vs 356,343; difference of 9 accounted for by the nine root metadata files, stated in the `root_metadata` collection description |
| Sum of `file_collections[].total_bytes` vs `total_size_bytes` | 3,815,969,360,064 vs 3,815,969,779,678; difference of 419,614 bytes likewise the root metadata files |
| Sum of `subsets[].instances[0].counts` vs `instances[0].counts` | 1576 + 352 + 352 = 2280 = 2280 |
| Split table row totals (race/ethnicity, sex, diabetes status) per split | each sums to its split total; cohort rows each sum to 2280 |
| Version participant counts across `updates`, `version_access`, `instances` | 204 (v1) + 863 (year 2) = 1067 (v2); 1067 + 1213 (year 3) = 2280 (v3); consistent everywhere |
| DOI/version repeated in `id`, `doi`, `version`, `version_access`, `related_datasets`, `distribution_formats` | `10.60775/fairhub.3` / `3.0.0` consistent throughout |
| Release dates in `distribution_dates` vs `version_access` vs `updates` | 2024-05-03, 2024-11-08, 2025-11-17 consistent |
| License URIs repeated in `license`, `license_and_use_terms`, `ip_restrictions`, `regulatory_restrictions`, `discouraged_uses`, `prohibited_uses` | v2.0 `zenodo.17555036` and v1.0 `zenodo.10642459` used consistently with scope |
| ORCIDs and ROR identifiers | each person/organization uses one identifier across all occurrences |

### Assertions deliberately omitted

- `issued`, `created_on`, `last_updated_on`: the slot range is `datetime` and LinkML rejects a
  date-only value (verified: `'2025-11-17' is not a 'date-time'`). The bundle supplies dates, not
  timestamps; supplying a time would be fabrication, so these slots are omitted and the dates are
  carried in `distribution_dates` and `version_access` where a string range is correct.
- `download_url`: access is gated behind verified-ID login and self-attestation; the bundle gives
  a landing page (`page`) but no direct download URL.
- `errata`: the healthsheet erratum question is blank in the source.
- `imputation_protocols`, `annotation_analyses`, `machine_annotation_tools`, `dialect`: no
  evidence in the bundle. The healthsheet states no labeling and no imputation were performed;
  the absence of labeling is recorded positively in `labeling_strategies` rather than left silent.
- `variables[].unit`, `minimum_value`, `maximum_value` for the laboratory analytes: BMJ Open
  Table 2 supplies units and laboratory reference ranges, but the PDF-to-text extraction
  interleaves the test-name, unit, reference-range and rationale columns so that per-analyte
  alignment cannot be established reliably; and a laboratory *reference range* is a normal-value
  interval, not the variable's permitted minimum and maximum, so mapping it to those slots would
  be a mis-scoped assertion. Units and the fact of a laboratory-provided reference range are
  therefore stated in each variable's `description` instead.
- `resources`, `parent_datasets`, `was_derived_from`, `compression`: not supported.

### Representation choices worth noting

- `publisher` has range `uriorcurie`; the bundle gives `publisherName: "FAIRhub"`, so the FAIRhub
  URI `https://fairhub.io/` is used.
- `status: published` describes the dataset release (DOI issued, `dateType: Available`
  2025-11-17), not the study, whose `overallStatus` is "Enrolling by invitation"; the study status
  is recorded in `collection_timeframes`.
- `regulatory_restrictions.confidentiality_level: restricted` reflects the recorded access type
  `PublicDownloadSelfAttestationRequired` plus the separate controlled-access set, not an
  unrestricted public download.

### Phase 2 discoveries requiring back-port

None. Core was derived from the Phase 1 full record plus the same bundle; no fact was found in
Phase 2 that the full record lacked or stated differently, so no correction was back-ported.

### Corrections made during Phase 3

One. `conforms_to_schema` initially named only
`https://schema.aireadi.org/v0.1.0/dataset_description.json`, which is the schema of the dataset
description metadata file rather than of the dataset as a whole. It was widened to name both
AI-READI metadata schemas declared in the FAIRhub record (`dataset_description.json` v0.1.0 and
`dataset_structure_description.json` v0.1.1) with their roles stated. The core record was
regenerated from the corrected full record and both files were re-validated.

## Phase 4 — strict full/core reconciliation

### Method

Shared slots were derived at runtime from `Dataset` and `CoreDataset` with LinkML `SchemaView`;
no hand-written field list was used. The core record was produced by projecting the Phase
3-audited full record: every schema-shared slot was carried across by parsed-value copy, so
schema-identical slots are byte-for-byte identical in content by construction, and the two
core-only slots were handled explicitly.

### Deterministic result

```
poetry run python -m data_sheets_schema.d4d_pair_consistency \
  --full data/d4d_concatenated/claudecode_agent/2026-07-28_claude-opus-5-generic_rep3/AI_READI_d4d.yaml \
  --core data/d4d_concatenated/claudecode_agent_core/2026-07-28_claude-opus-5-generic_rep3/AI_READI_d4d_core.yaml

PASS: 76 schema-identical slots; projected slots=['resources']
WARNING [semantic-review-required] $.file_collections <-> $.distributions:
  Phase 4 must semantically review related distribution content;
  deterministic matches=10, unmatched core distributions=[]
```

`--sync-core` was not needed and was not run: core was derived from the audited full record, so
there was nothing to synchronise. The command above is the independent final check.

- Schema-identical shared slots: **76**, all present-in-both or absent-in-both with deeply
  identical parsed values, including every narrative field. Core condenses, paraphrases, reorders
  and omits nothing from shared content.
- Projected slot `resources` (`Dataset` in full, `CoreDataset` in core): absent from both records,
  so coverage is trivially equal and there is nothing to match by `id`.

### Full-only slots (correctly absent from core)

`citation`, `total_file_count`, `total_size_bytes`, `file_collections`, `subsets`,
`relationships`, `splits`, `direct_collection`, `collection_notifications`,
`collection_consents`, `consent_revocations`, `participant_privacy`,
`participant_compensation`, `third_party_sharing`, `related_datasets`, `variables` — 16 slots,
none of which exists on `CoreDataset`.

### Core-only slots

- `distributions` (`CoreDistribution`): populated, see the semantic review below.
- `dialect` (`FormatDialect`): omitted. The bundle documents file formats and standards but never
  the delimiter, quote character, header row or comment prefix of the CSV/TSV files, so every
  slot of `FormatDialect` would have to be guessed.

### Semantic review of related content: `file_collections` → `distributions`

All ten collections matched one-to-one; no core distribution is unmatched and no full collection
is unrepresented.

| Aspect | Finding |
|---|---|
| Names | identical for all ten |
| `path` | identical where present; absent from both for the root metadata group, which is not a directory |
| Byte counts | `file_collections[].total_bytes` → `distributions[].bytes`, equal for the nine datatype directories; absent from both for the root metadata group, whose size the bundle does not state |
| File counts | `CoreDistribution` has no file-count slot, so each core description carries the count as an explicit sentence; every value equals the corresponding `file_collections[].file_count`. Sums reconcile with the full record's `total_file_count` as recorded in Phase 3 |
| Descriptions | core description = full description + file-count sentence + "Conforms to:" sentence. Additive only; no statement differs |
| Formats | `FormatEnum`/`MediaTypeEnum` do not contain DICOM, WFDB, Open mHealth or the NASA ASCII profile, so `format`/`media_type` are set only for `clinical_data` (`CSV` / `text/csv`), which the structure description and README both state is CSV. The remaining standards are carried in the `conforms_to` sentence of each description. No conflict with the full record's `conforms_to` values |
| Compression | absent in both; the bundle describes directory trees, not packaged archives |
| Checksums (`hash`, `md5`, `sha256`) | absent in both; the bundle supplies none |
| Access URLs | `CoreDistribution` has no access-URL slot; access points are carried by `distribution_formats.access_urls`, which is schema-identical in both files |
| Release scope | every collection describes v3.0.0; all counts and sizes come from the v3.0.0 structure description, matching the v3.0.0 totals |
| `is_tabular` consistency | `false` in both, consistent with a distribution set in which only `clinical_data` is tabular CSV |
| `total_file_count` / `total_size_bytes` vs distribution-level values | same scope, reconciled as in Phase 3 (difference = the nine root metadata files) |

No contradiction was found within either record or between them.

## Commands run

```bash
poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_all.yaml \
  -C Dataset data/d4d_concatenated/claudecode_agent/2026-07-28_claude-opus-5-generic_rep3/AI_READI_d4d.yaml
poetry run linkml-term-validator validate-data \
  data/d4d_concatenated/claudecode_agent/2026-07-28_claude-opus-5-generic_rep3/AI_READI_d4d.yaml \
  --schema src/data_sheets_schema/schema/data_sheets_schema_all.yaml --target-class Dataset
poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml \
  -C CoreDataset data/d4d_concatenated/claudecode_agent_core/2026-07-28_claude-opus-5-generic_rep3/AI_READI_d4d_core.yaml
poetry run linkml-term-validator validate-data \
  data/d4d_concatenated/claudecode_agent_core/2026-07-28_claude-opus-5-generic_rep3/AI_READI_d4d_core.yaml \
  --schema src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml --target-class CoreDataset
poetry run python -m data_sheets_schema.d4d_pair_consistency \
  --full .../AI_READI_d4d.yaml --core .../AI_READI_d4d_core.yaml
poetry run d4d provenance record --project AI_READI --method claudecode_agent \
  --label 2026-07-28_claude-opus-5-generic_rep3 \
  --input-bundle data/preprocessed/concatenated/AI_READI_preprocessed.txt
```

## Files changed

- `data/d4d_concatenated/claudecode_agent/2026-07-28_claude-opus-5-generic_rep3/AI_READI_d4d.yaml` (created)
- `data/d4d_concatenated/claudecode_agent_core/2026-07-28_claude-opus-5-generic_rep3/AI_READI_d4d_core.yaml` (created)
- `data/d4d_concatenated/claudecode_agent_core/2026-07-28_claude-opus-5-generic_rep3/AI_READI_reconciliation.md` (this file)
- `data/d4d_concatenated/claudecode_agent_core/2026-07-28_claude-opus-5-generic_rep3/AI_READI_provenance.yaml` (live provenance record)

## Final result

| Check | Result |
|---|---|
| Full schema validation (`Dataset`) | pass |
| Full ontology term validation | pass |
| Core schema validation (`CoreDataset`) | pass |
| Core ontology term validation | pass |
| Schema-derived pair consistency | PASS, 76 schema-identical slots |
| Semantic review of related content | completed, zero unresolved contradictions |
| Prior-run D4D reuse | none |
| Top-level slots populated: full / core | 80 / 65 |
