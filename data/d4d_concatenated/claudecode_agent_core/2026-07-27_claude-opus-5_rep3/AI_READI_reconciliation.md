# AI_READI full/core reconciliation — 2026-07-27_claude-opus-5_rep3

## Run identity

| Field | Value |
| --- | --- |
| Project | AI_READI |
| Arm | BASELINE (document corpus only) |
| Agent runtime | Claude Code |
| Provider | Anthropic |
| Model | claude-opus-5[1m] |
| Mode | four-phase project agent |
| Temperature | 0.0 |
| Generated | 2026-07-27 |
| Full record | `data/d4d_concatenated/claudecode_agent/2026-07-27_claude-opus-5_rep3/AI_READI_d4d.yaml` |
| Core record | `data/d4d_concatenated/claudecode_agent_core/2026-07-27_claude-opus-5_rep3/AI_READI_d4d_core.yaml` |
| Source bundle | `data/preprocessed/concatenated/AI_READI_preprocessed.txt` (10 documents) |
| Source manifest | `data/preprocessed/source_manifest.yaml` |
| Full schema | `src/data_sheets_schema/schema/data_sheets_schema_all.yaml`, class `Dataset` |
| Core schema | `src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml`, class `CoreDataset` |

Prior D4D factual reuse: prohibited, and not performed.

## Phase 3 — source and provenance audit

### Provenance

Factual inputs read during this run were limited to the phase allowlist:

- `data/preprocessed/concatenated/AI_READI_preprocessed.txt` (whole corpus; the
  `datasetStructureDescription` bulk was additionally parsed with a JSON reader to extract
  per-directory sizes and file counts and the root metadata-file list)
- `data/preprocessed/source_manifest.yaml`
- `src/data_sheets_schema/schema/data_sheets_schema_all.yaml` and
  `src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml`, read through LinkML
  `SchemaView` to derive induced slots, ranges, cardinality, inlining and enum values
- `project/jsonschema/data_sheets_schema.schema.json` (generated structural artifact, used only to
  confirm that `principal_investigator`, `grantor`, `contact_person`, `reviewing_organization` and
  `governance_committee_contact` serialise as reference strings rather than inline objects)
- `src/data_sheets_schema/d4d_pair_consistency.py` (Phase 4 validator)
- the three governing instruction files

No prior full or core D4D record, evaluation, reconciliation report, or RO-Crate artifact was
read, searched, globbed, or cited, and no live web content was fetched. Output directory *names*
under `data/d4d_concatenated/` were listed once, before generation, solely to confirm that the
`2026-07-27_claude-opus-5_rep3` label was unused; no file contents were opened.

### Source conflicts resolved

1. **Dataset version: v2.0.0 vs v3.0.0.** The corpus carries the sheet-selected v2.0.0
   documentation and FAIRhub record (2.01 TB, 165,051 files, 1,067 participants) alongside the
   current v3.0.0 documentation, FAIRhub record and API metadata (3.82 TB, 356,343 files, 2,280
   participants, DOI 10.60775/fairhub.3, published 2025-11-17). Per the manifest curation notes,
   v3.0.0 is canonical; the v2.0.0 FAIRhub page itself states the version is no longer accessible.
   Resolution: the record describes v3.0.0 throughout, and v1.0.0/v2.0.0 facts are confined to
   `version_access`, `distribution_dates` and `related_datasets`, each explicitly scoped to the
   historical release.

2. **Target enrolment: 4,000 vs 4,600.** The BMJ Open protocol publication, the Nature Metabolism
   comment and the FAIRhub `studyDescription.designModule.enrollmentInfo` all state 4,000
   (anticipated). The University of Washington IRB protocol form states 4,600 in three places.
   The IRB form is the earliest artifact (initial approval 2022-12-20) and predates the published
   protocol. Resolution: 4,000 recorded as the target in `sampling_strategies.strategies`, with
   the IRB's 4,600 figure recorded in the same statement as the earlier protocol-stage target.

3. **Lead organization: University of Washington vs Washington University in St. Louis.** The
   FAIRhub `studyDescription` records the lead sponsor, responsible-party affiliation, central
   contact affiliation and `datasetDescription.managingOrganization` as "Washington University in
   St. Louis" (ROR `01yc7t268`). NIH RePORTER records the awardee organization as UNIVERSITY OF
   WASHINGTON, the Nature Metabolism author list places both Aaron Y. Lee and Cecilia S. Lee at
   the University of Washington, Seattle, the IRB is the UW IRB, and the license agreement names
   the University of Washington as Licensor. The FAIRhub `locationList` separately gives ROR
   `00cvxb145` for the University of Washington site. Resolution: University of Washington used
   as the affiliation for both Lee investigators and as the ethical-review organization; the
   FAIRhub discrepancy is recorded verbatim in `creators[creator_aaron_lee].description` rather
   than silently dropped.

4. **License version: v1.0 vs v2.0.** The corpus contains the full text of the AI-READI Data
   License Agreement v1.0 (Zenodo `10.5281/zenodo.10642459`), while the v3.0.0 FAIRhub record and
   README cite "AI-READI custom license v2.0" at `10.5281/zenodo.17555036`. Resolution: the
   top-level `license` slot and `license_and_use_terms.license_terms[0]` name the v2.0 license
   applicable to v3.0.0; the substantive clause-level terms transcribed from the v1.0 text are
   carried in a separate, explicitly labelled `license_terms` entry rather than being presented
   as the current license text.

5. **Healthsheet text carried over from the previous version.** Composition question 4 in the
   v3.0.0 healthsheet answers that the dataset "contains data from all participants who have been
   enrolled during the first year of data collection", which contradicts the same record's stated
   2023-07-19 to 2025-05-01 collection window and 2,280 participants. Resolution: the
   census-coverage claim was retained (all instances in the covered period), the "first year"
   scoping was not propagated, and the staleness is documented inline in
   `sampling_strategies.strategies`.

6. **Documentation "About" page carried over from the previous version.** The v3.0.0 docs page
   states that the documentation "is associated with v3.0 of the dataset, which contains data from
   the participants of the pilot study phase", contradicting the README's v3.0.0 main-study
   description. Resolution: not propagated; documented inline in `version_access.version_details`.

7. **De-identification characterisation.** FAIRhub's `datasetDeIdentLevel` records
   `deIdentType: NoDeIdentification` with `deIdentDirect: true` and `deIdentHIPAA: true`, and the
   explanation that no identifiers were collected so no active de-identification was necessary,
   while the Nature Metabolism comment states the public set is stripped of PHI via the HIPAA
   Safe Harbor method. Resolution: both statements are recorded side by side in `is_deidentified`
   and `participant_privacy`; neither is presented as overriding the other.

8. **Follow-up subgroup size: ~10% vs ~4%.** The Nature comment, IRB protocol and FAIRhub study
   description all state that about 10% of the cohort will be invited to a year-4 follow-up
   visit; the healthsheet collection-timeframe answer states that approximately 4% of participants
   are expected to undergo a follow-up examination in year 4. Resolution: both figures are stated
   with attribution in `instances[0].description` and `known_limitations`.

9. **Study base window: 2020–2025 vs "past 2 years".** The BMJ Open protocol defines the study
   base as patients aged 40+ with a medical encounter at a site between 2020 and 2025; the
   healthsheet says recruitment pools came from patients with an encounter within the past two
   years. Resolution: both are stated with attribution in `direct_collection.collection_details`;
   the broader protocol definition is used in `sampling_strategies.source_data`.

10. **ICD-10 code assignment.** The BMJ Open protocol states that "Patients with T2DM and
    pre-diabetes are identified by screening electronic health records for ICD-10 diagnosis codes
    R73.09 and E11.X, respectively." Reading "respectively" literally inverts the conventional
    meaning of the two codes. Resolution: the codes are recorded without asserting a
    code-to-condition assignment, attributed to the protocol publication. Correcting the mapping
    would require knowledge outside the corpus and was therefore not done.

11. **Blood volume and visit duration.** Blood volume is 53 mL in the BMJ protocol and 50–60 mL in
    the IRB form; visit duration is 2.5–4 hours in the BMJ protocol, 3–4 hours in the IRB form and
    the Nature figure. Resolution: both blood-volume figures are given with attribution; the BMJ
    range is used for visit duration as the published protocol value.

### Phase 2 discoveries back-ported to full

Phase 2 was a schema-derived projection of the Phase 1 full record plus a source re-read; it
surfaced no fact present in the sources but missing from the full record, so no factual
back-port was required. Two Phase 3 audit findings were applied to the full record and then
re-projected into core:

- `file_collections[root_metadata]` gained `file_count: 9` and `total_bytes: 419614`. The 9 files
  are the root metadata-file list enumerated in `datasetStructureDescription.metadataFileList`
  (CHANGELOG.md, dataset_description.json, dataset_structure_description.json, healthsheet.md,
  LICENSE.txt, participants.json, participants.tsv, README.md, study_description.json). The byte
  figure is the residual between the dataset totals and the nine datatype directories; it is
  arithmetic over two source values, not an independent assertion.
- The target-enrolment, healthsheet-staleness, documentation-staleness and study-base statements
  described above were added or rewritten.

### Corrections applied during the audit

| Slot | Correction | Reason |
| --- | --- | --- |
| `license_and_use_terms.data_use_permission` | removed `publication_required` and `no_population_ancestry_research`, kept `disease_specific_research` | The corpus supports only the disease-specific restriction. FAIRhub's `datasetConsent` sets `consentNoncommercial`, `consentGeogRestrict`, `consentResearchType`, `consentGeneticOnly` and `consentNoMethods` all to false, and the license requires acknowledgement of the source, not publication. |
| `collection_mechanisms[mechanism_ehr_screening]` | removed the code-to-condition assignment for R73.09 / E11.X | See conflict 10. |
| `funders[funding_supporting_nih_grants].grants[*].id` | replaced fabricated `reporter.nih.gov/project-details/{grant number}` URLs with local identifiers `grant_P30DK035816` / `grant_UL1TR003096` | The corpus supplies the grant numbers but no RePORTER URL for these two awards; the constructed URLs were not source-supported. |
| `funders[funding_research_to_prevent_blindness].grantor` | `research_to_prevent_blindness` → `Research to Prevent Blindness` | Sources give the funder name only; no ROR identifier is available. |
| `creators[creator_bhavesh_patel].credit_roles` | `data_curation` → `writing_original_draft` | `data_curation` was an inference; Writing Committee membership is stated in the Nature author list. |
| `creators[creator_cecilia_lee]` | added Writing Committee membership and `writing_original_draft` | Stated in the Nature Metabolism Writing Committee list. |
| `created_on`, `issued` | `2025-11-17T00:00:00` → `2025-11-17T00:00:00Z` | LinkML `datetime` requires a timezone-qualified `date-time`. |

### Deliberate omissions

`variables`, `imputation_protocols`, `annotation_analyses`, `machine_annotation_tools`, `errata`,
`parent_datasets` and `resources` are omitted from both records: the corpus supplies no
source-supported content for them (the healthsheet erratum question is answered with an empty
string, and no labeling or imputation was performed). `Instance.data_topic` and
`Instance.data_substrate` are omitted because their `values_from: B2AI_TOPIC` binding cannot be
satisfied from the corpus. `dialect` is omitted from core because no source states the delimiter,
quoting or header conventions of the CSV files.

### Post-audit validation (Phase 3)

```bash
poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_all.yaml -C Dataset \
  data/d4d_concatenated/claudecode_agent/2026-07-27_claude-opus-5_rep3/AI_READI_d4d.yaml
poetry run linkml-term-validator validate-data \
  data/d4d_concatenated/claudecode_agent/2026-07-27_claude-opus-5_rep3/AI_READI_d4d.yaml \
  --schema src/data_sheets_schema/schema/data_sheets_schema_all.yaml --target-class Dataset
poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml -C CoreDataset \
  data/d4d_concatenated/claudecode_agent_core/2026-07-27_claude-opus-5_rep3/AI_READI_d4d_core.yaml
poetry run linkml-term-validator validate-data \
  data/d4d_concatenated/claudecode_agent_core/2026-07-27_claude-opus-5_rep3/AI_READI_d4d_core.yaml \
  --schema src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml --target-class CoreDataset
```

All four passed (`No issues found`, `✅ Validation passed`).

## Phase 4 — strict full/core reconciliation

### Schema-derived slot partition

Derived at runtime with `SchemaView` over `Dataset` and `CoreDataset`; no hand-written field list
was used.

- **Schema-identical shared slots: 76.** All are either present in both records or absent from
  both, with deeply identical parsed YAML content.
- **Projected shared slots: 1** (`resources`, `Dataset` in full and `CoreDataset` in core). Absent
  from both records, so no projection was required and coverage is trivially equal.
- **Full-only slots (17):** `citation`, `collection_consents`, `collection_notifications`,
  `consent_revocations`, `direct_collection`, `file_collections`, `parent_datasets`,
  `participant_compensation`, `participant_privacy`, `related_datasets`, `relationships`,
  `splits`, `subsets`, `third_party_sharing`, `total_file_count`, `total_size_bytes`,
  `variables`.
- **Core-only slots (2):** `distributions`, `dialect`.

### Related-content mapping and semantic review

`file_collections` (full) → `distributions` (core): 10 collections, 10 distributions, all matched
deterministically by `id`, with zero unmatched core distributions.

| id / name | path | file_count | total_bytes = bytes | format | media_type |
| --- | --- | --- | --- | --- | --- |
| cardiac_ecg | cardiac_ecg | 4,515 | 302,931,703 | — (WFDB) | — |
| clinical_data | clinical_data | 7 | 176,182,781 | CSV | text/csv |
| environment | environment | 2,232 | 55,625,676,514 | — (NASA ESDS ASCII) | — |
| retinal_flio | retinal_flio | 7,969 | 1,069,466,876,718 | — (DICOM) | — |
| retinal_oct | retinal_oct | 56,478 | 1,317,625,293,027 | — (DICOM) | — |
| retinal_octa | retinal_octa | 173,721 | 1,155,908,809,724 | — (DICOM) | — |
| retinal_photography | retinal_photography | 93,921 | 174,381,046,406 | — (DICOM) | — |
| wearable_activity_monitor | wearable_activity_monitor | 15,245 | 38,313,536,220 | — (Open mHealth) | — |
| wearable_blood_glucose | wearable_blood_glucose | 2,246 | 4,169,006,971 | — (Open mHealth) | — |
| root metadata files | / | 9 | 419,614 | — (mixed) | — |

Reviewed and found non-conflicting:

- **Names, descriptions, paths, byte counts.** Identical between each file collection and its
  matched distribution for every one of the 10 pairs.
- **Formats.** `CoreDistribution.format` and `media_type` are set only for `clinical_data`, the
  one collection whose source text explicitly states "Each CSV file in this directory". The
  remaining nine collections carry standards (DICOM, WFDB, Open mHealth, NASA ESDS ASCII, mixed
  metadata) that have no representable value in `FormatEnum` or `MediaTypeEnum`, so those fields
  are omitted rather than approximated. The standard for each is preserved in the shared
  `conforms_to` text of the file collection and in the identical distribution `description`.
  No format value therefore conflicts across the pair.
- **Compression.** Not asserted anywhere; absent from both `Dataset.compression`,
  `FileCollection.compression` and `CoreDistribution.compression`. No conflict.
- **Checksums and access URLs.** The corpus supplies no per-file or per-directory hashes,
  and no per-collection download URLs; `hash`, `md5`, `sha256` are therefore unset. Dataset-level
  access URLs live in the shared `distribution_formats` slot and are byte-identical across the
  pair.
- **Scope aggregation.** `total_file_count` (356,343) equals the sum of the 10 `file_count`
  values exactly, and `total_size_bytes` (3,815,969,779,678) equals the sum of the 10
  `total_bytes` values exactly. The nine datatype directories alone sum to 356,334 files and
  3,815,969,360,064 bytes; the 9-file / 419,614-byte remainder is exactly the root metadata-file
  collection, so the aggregate and per-collection scopes are the same and mutually consistent.
- **`is_tabular`.** `false` in both records, consistent with a distribution set dominated by DICOM
  imaging and waveform data in which only `clinical_data` is CSV.
- **Release scope.** Every file collection and distribution describes the v3.0.0 release only.
  Historical v1.0.0 and v2.0.0 figures appear solely in `version_access`, `distribution_dates`
  and `related_datasets` (full-only), each explicitly labelled with its version, so no historical
  value is presented as a current one.
- **Top-level identity, version and access facts.** `id`, `doi`, `version`, `title`, `license`,
  `publisher`, `download_url`, `issued`, `created_on` and `status` are identical in full and core
  and agree with `version_access.latest_version_doi`
  (`https://doi.org/10.60775/fairhub.3`), with `distribution_dates` (v3.0.0 released 2025-11-17),
  with `distribution_formats.access_urls`, and with the access steps stated in
  `license_and_use_terms`.

No unresolved contradiction was found within either record or between the two records.

### Commands and results

```bash
poetry run python -m data_sheets_schema.d4d_pair_consistency \
  --full data/d4d_concatenated/claudecode_agent/2026-07-27_claude-opus-5_rep3/AI_READI_d4d.yaml \
  --core data/d4d_concatenated/claudecode_agent_core/2026-07-27_claude-opus-5_rep3/AI_READI_d4d_core.yaml \
  --sync-core
# PASS: 76 schema-identical slots; projected slots=['resources']
# WARNING [semantic-review-required] $.file_collections <-> $.distributions:
#   deterministic matches=10, unmatched core distributions=[]

poetry run python -m data_sheets_schema.d4d_pair_consistency \
  --full data/d4d_concatenated/claudecode_agent/2026-07-27_claude-opus-5_rep3/AI_READI_d4d.yaml \
  --core data/d4d_concatenated/claudecode_agent_core/2026-07-27_claude-opus-5_rep3/AI_READI_d4d_core.yaml
# PASS: 76 schema-identical slots; projected slots=['resources']
# WARNING [semantic-review-required] ... (same warning; the review is recorded above)
```

The `--sync-core` pass made no content change to the core record beyond appending the
`# Phase 4 reconciliation: completed` header line, because the core record had already been
projected from the Phase 3-audited full record. All four schema and term validations were re-run
after synchronization and passed again.

### Files changed in Phase 3/4

- `data/d4d_concatenated/claudecode_agent/2026-07-27_claude-opus-5_rep3/AI_READI_d4d.yaml`
  (audit corrections listed above)
- `data/d4d_concatenated/claudecode_agent_core/2026-07-27_claude-opus-5_rep3/AI_READI_d4d_core.yaml`
  (regenerated from the corrected full record; `# Phase 4 reconciliation: completed` appended)
- `data/d4d_concatenated/claudecode_agent_core/2026-07-27_claude-opus-5_rep3/AI_READI_reconciliation.md`
  (this report)

## Result

| Check | Result |
| --- | --- |
| Full schema validation (`Dataset`) | PASS |
| Full ontology term validation | PASS |
| Core schema validation (`CoreDataset`) | PASS |
| Core ontology term validation | PASS |
| Pair consistency (76 identity slots, 1 projected) | PASS |
| Related-content semantic review | complete, 0 contradictions |
| Provenance audit | PASS — no prior generated D4D used |

Line counts (informational metadata, not a quality gate): full 1,451 lines; core 1,398 lines.
