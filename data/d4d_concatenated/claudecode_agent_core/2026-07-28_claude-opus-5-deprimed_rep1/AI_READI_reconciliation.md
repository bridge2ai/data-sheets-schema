# AI_READI full/core reconciliation - 2026-07-28_claude-opus-5-deprimed_rep1

- Project: AI_READI
- Arm: BASELINE (input documents only)
- Version label: `2026-07-28_claude-opus-5-deprimed_rep1`
- Agent runtime: Claude Code; Provider: Anthropic; Model: `claude-opus-5[1m]`
- Mode: four-phase project agent, de-primed; Temperature 0.0
- Full: `data/d4d_concatenated/claudecode_agent/2026-07-28_claude-opus-5-deprimed_rep1/AI_READI_d4d.yaml`
- Core: `data/d4d_concatenated/claudecode_agent_core/2026-07-28_claude-opus-5-deprimed_rep1/AI_READI_d4d_core.yaml`

## Phase 3 - Source and provenance audit

### Provenance boundary

Factual inputs read during this run, in full:

- `data/preprocessed/concatenated/AI_READI_preprocessed.txt` (10 documents, 6,229 lines)
- `data/preprocessed/source_manifest.yaml` (curation guidance only)

Structural inputs: `src/data_sheets_schema/schema/data_sheets_schema_all.yaml`,
`src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml`, resolved at runtime with
LinkML `SchemaView`; and `src/data_sheets_schema/d4d_pair_consistency.py`.

Procedural inputs: `.claude/agents/d4d-provenance-guard.md`, `.claude/commands/d4d-full-core.md`,
`.claude/commands/d4d-agent.md`.

No prior full or core D4D record, from any label, arm or date, was read, opened, grepped or
cited. `data/d4d_concatenated/` was touched only by `mkdir -p` and one `ls` of the newly created
output directory, which returned a single filename for a different project (CHORUS) written by a
concurrent agent; that file was not opened. No evaluation report, reconciliation report, test
fixture, or schema example supplied any dataset fact. `d4d:docExample` annotations were not
consulted for values.

### Source-conflict resolutions

The bundle carries documentation and metadata for three released versions of the dataset
(v1.0.0, v2.0.0, v3.0.0) plus protocol and IRB material predating them. Per the manifest's
curation guidance, current upstream captures were preferred over sheet-selected but superseded
captures, and historical values were retained only with explicit historical scope.

| # | Conflict | Sources | Resolution |
|---|---|---|---|
| C1 | Release described by the record | `fairhub_dataset` (v2.0.0, 2.01 TB, 165,051 files) vs `fairhub_dataset_v3` / `fairhub_dataset_v3_api` (v3.0.0, 3.82 TB, 356,343 files) | Record describes **v3.0.0**, DOI `10.60775/fairhub.3`, published 2025-11-17. v2.0.0 and v1.0.0 retained only in `version_access`, `distribution_dates` and `related_datasets`, each explicitly scoped as an earlier release. FAIRhub's own "no longer accessible" notice on v2.0.0 is recorded. |
| C2 | Lead institution | FAIRhub `studyDescription` names "Washington University in St. Louis" (ROR `01yc7t268`) as lead sponsor, managing organization, and affiliation of Aaron Lee and Cecilia Lee | Contradicted within the same bundle by NIH RePORTER (`Organization: UNIVERSITY OF WASHINGTON`), the data license (Licensor: University of Washington), the BMJ protocol (UW IRB, UW affiliations), the Nature comment (Aaron Y. Lee, University of Washington, `leeay@uw.edu`), and FAIRhub's own `locationList` (University of Washington, Seattle, ROR `00cvxb145`). Recorded **University of Washington** (ROR `00cvxb145`); the WUSTL string is treated as a single-field data-entry error and is not asserted anywhere in the record. |
| C3 | Target enrollment | 4,000 (BMJ protocol, Nature comment, FAIRhub `enrollmentInfo`) vs 4,600 (IRB protocol application narrative, which nonetheless states 1,000 per group across four groups) | Recorded **4,000**, consistent with the four 1,000-participant group targets that appear in the IRB subject-count table itself. The 4,600 figure is earlier planning text and is not carried. |
| C4 | Enrollment start date | 2023-07-19 (FAIRhub `startDateStruct`, Actual; and the `Collected` range start) vs 18 July 2023 (BMJ) | `start_date` set to **2023-07-19** from the structured, more recently captured record; the BMJ date is retained verbatim in `collection_timeframes[1].timeframe_details` rather than discarded. |
| C5 | Study end date | 30 November 2026 (BMJ) vs 2027-01-01 anticipated completion (FAIRhub) vs "2022-2026" (Nature) | No `end_date` asserted for the overall study. All three statements retained in `timeframe_details` with their sources' scope made explicit. Only the v3.0.0 collection window (2023-07-19 to 2025-05-01) carries a hard `end_date`, and it is uncontested. |
| C6 | License identity | Bundle contains the full text of AI-READI LICENSE v1.0 (Zenodo `10.5281/zenodo.10642459`); v3.0.0 metadata names "AI-READI custom license v2.0" (`10.5281/zenodo.17555036`), and FAIRhub displays the label "Health Data License" | `license` set to **AI-READI custom license v2.0**, the license of the described release. The quoted clauses in `license_and_use_terms.license_terms` come from the v1.0 text present in the bundle, and `license_and_use_terms.description` states explicitly which document each identifier refers to. Both DOIs appear in `external_resources`. |
| C7 | De-identification method | Nature: public set "stripped of PHI ... via the Safe Harbor method" vs FAIRhub `datasetDeIdentLevel`: `deIdentType: NoDeIdentification` with "No identifiers were collected so no active de-identification was necessary" | Both statements recorded verbatim in `is_deidentified.deidentification_details`, followed by an explicit note that they differ in emphasis but agree the released dataset contains no PHI. `method` set to `HIPAA Safe Harbor`; `identifiable_elements_present: false`. No synthesis that erases the disagreement. |
| C8 | Documentation "About" page scope | Both `docs/2/about` and `docs/3/about` state the documentation is "associated with v3.0 [resp. v2.0] of the dataset, which contains data from the participants of the pilot study phase" | Treated as stale boilerplate carried across doc versions: it contradicts the healthsheet, readme and FAIRhub metadata for the same release (2,280 participants, 2023-07-19 to 2025-05-01) and it is self-inconsistent between the two doc versions. Participant scope taken from the structured metadata and healthsheet. Not carried into the record. |
| C9 | Version-year scope wording | Healthsheet: v3.0.0 "consists of data collected up through the end of the second year of the study"; readme change table labels v3.0.0 "main study" and adds a "year 3 data" column of 1,213 participants | The absolute figures agree (204 + 863 + 1,213 = 2,280) and are used. The relative "second year" phrasing is quoted only where the healthsheet is quoted; no year-index claim is asserted independently. |
| C10 | Blood volume collected | BMJ: "Blood (53 mL) is collected"; IRB: "approximately 50-60 ml" | Both retained in `raw_data_sources` for the clinical laboratory source, attributed to their respective documents. No single figure asserted. |
| C11 | Cohort completeness statement | Healthsheet composition Q4: "the dataset contains data from all participants who have been enrolled during the first year of data collection" | Stale for v3.0.0, whose collected range runs to 2025-05-01. Recorded as completeness "relative to participants enrolled through the release cut-off" in `sampling_strategies.description` rather than reproducing "first year". |
| C12 | Sub-population identification | Healthsheet: "Does the dataset identify any demographic sub-populations? No" vs readme, which publishes aggregate race/ethnicity, sex and diabetes-status counts, and `armGroupList`, which defines four diabetes-severity groups | `subpopulation_elements_present: false` follows the explicit answer; the nuance is carried in `identification` (diabetes study groups are design strata; sex/race/ethnicity are withheld from the public release) and `distribution` (the published aggregate counts). |
| C13 | Grant number typographic variants | Healthsheet motivation Q5 gives "OT2ODO32644" (letter O for zero); all other sources give `OT2OD032644`; NIH RePORTER gives project number `1OT2OD032644-01` | Recorded `OT2OD032644` as the core project number, with `1OT2OD032644-01` identified as the application-level project number inside the grant description. |
| C14 | Award period vs enrollment period | NIH RePORTER: project 2022-09-01 to 2025-08-31 for application 10471118 | Retained verbatim and scoped to that award record inside `funders[0].grants[0].description`; not used as a study or collection end date. |
| C15 | Access model | Healthsheet and docs describe a public set plus a controlled-access set requiring a data use agreement (largely in future tense) vs FAIRhub v3.0.0 `accessType: PublicDownloadSelfAttestationRequired` | The released v3.0.0 distribution is recorded as the public, self-attestation-gated release. The controlled-access set is recorded only as a described future/parallel release inside `sensitive_elements` and `missing_data_documentation`; no controlled-access distribution or resource is asserted to exist. |
| C16 | Acquisition mode | Healthsheet collection Q2 names only "directly observable" and "reported by subjects" | `was_inferred_derived` set to **true**, not false: BMJ Table 2 and the protocol document calculated variables (BMI, waist-hip ratio, calculated LDL, BUN/creatinine ratio, calculated globulin, A/G ratio). Basis recorded in `acquisition_methods.acquisition_details`. |

### Internal consistency checks (both records)

All arithmetic below was recomputed from the emitted YAML and agrees with the bundle.

- Participant totals: `instances[0].counts` = 2,280 = subsets 1,576 + 352 + 352.
- Split strata sum to their split totals in all three splits and across all three stratifications
  (race/ethnicity, sex, diabetes status): train 204+369+343+660 = 599+977 = 600+384+487+105 = 1,576;
  validation 88×4 = 176+176 = 88+88+109+67 = 352; test 88×4 = 176+176 = 88+88+90+86 = 352.
- Aggregate strata sum to 2,280: race/ethnicity 380+545+519+836; sex 951+1,329; diabetes status
  776+560+686+258.
- Version participant chain: 204 (v1.0.0) + 863 (year 2) + 1,213 (year 3) = 2,280 (v3.0.0);
  204 + 863 = 1,067 (v2.0.0). Both stated chains are consistent.
- `total_size_bytes` 3,815,969,779,678 = 3.816 TB, consistent with the declared "3.82 TB".
- `total_file_count` 356,343 vs the sum of the nine datatype directories' `file_count` = 356,334;
  `total_size_bytes` vs the sum of `total_bytes` = 3,815,969,360,064. Residual: **9 files,
  419,614 bytes**. This is not a contradiction: the bundle names root-level files that sit
  outside the datatype directories (README, LICENSE, CHANGELOG, `participants.tsv`,
  `dataset_description.json`, `study_description.json`,
  `dataset_structure_description.json`, `dqd`/healthsheet artefacts). The residual is small and
  of the right order. Both the aggregate totals and the per-directory figures are taken directly
  from the FAIRhub v3.0.0 metadata; neither was adjusted to force the sum.
- Identifiers repeat consistently: DOI `10.60775/fairhub.3` in `id`, `doi`,
  `version_access.latest_version_doi` and `third_party_sharing`; version `3.0.0` in `version`,
  `version_access.versions_available` and `conforms_to_schema` context; grant `OT2OD032644` in
  `funders`, `human_subject_research` and `data_collectors`; IRB number `STUDY00016228` in
  `ethical_reviews` and `human_subject_research`.

### Phase 2 discoveries back-ported to full

None. Phase 2 derived the core record from the Phase 1 full record's schema-identical slots plus
a schema-permitted projection of `file_collections` into `distributions`. Re-reading the bundle
during Phase 2 surfaced no fact that was missing from or contradicted in the full record, so no
back-port to full was required and no core-only fact was introduced.

### Corrections applied during Phase 1/3

Four structural corrections were made after the first validation pass; none changed a dataset
fact:

1. `Creator.principal_investigator`, `FundingMechanism.grantor`, `EthicalReview.reviewing_organization`
   and `LicenseAndUseTerms.contact_person` are non-inlined single-valued object slots, so they
   serialize as identifier references, not nested objects. Rewritten as ORCID/ROR/name strings.
   The person-level detail (degree, email, ORCID) was moved into the enclosing `Creator`
   `description` and into `license_and_use_terms.license_terms` so that no fact was lost.
2. `Person.affiliation` is a list of strings; organizations were relocated to
   `Creator.affiliations`, which is an inlined list of `Organization` objects.
3. `issued` requires a `date-time`; `2025-11-17T00:00:00` was rejected and replaced with
   `2025-11-17T00:00:00+00:00`.
4. No invented field names remained; every emitted slot and nested shape was resolved from
   `SchemaView.class_induced_slots` for its owning class.

### Phase 3 result

Both records re-validated clean against schema and ontology terms after every correction. No
unsupported, fabricated, or prior-D4D-derived assertion was found. Sixteen source disagreements
were resolved as tabulated; in every case where two current sources disagreed without one
clearly superseding the other (C5, C7, C10), both statements were retained with their scope
made explicit rather than one being silently chosen.

## Phase 4 - Strict full/core reconciliation

### Schema-derived shared slots

Derived at runtime with LinkML `SchemaView` over `Dataset` and `CoreDataset`; no hand-written
field list was used.

- Schema-identical shared slots: **76**
- Projected shared slots: **1** (`resources`)
- Full-only slots: 14 - `citation`, `collection_consents`, `collection_notifications`,
  `consent_revocations`, `direct_collection`, `file_collections`, `related_datasets`,
  `relationships`, `splits`, `subsets`, `third_party_sharing`, `total_file_count`,
  `total_size_bytes`, `variables`
- Core-only slots: 1 - `distributions`
- Full record top-level slots emitted: **78**
- Core record top-level slots emitted: **65** (64 shared-identity slots present in both + `distributions`)

### Identity check

All 76 schema-identical slots satisfy identical presence and deep value identity. Core was
constructed by copying the parsed value of each identity slot from the Phase 3-audited full
record without condensing, paraphrasing, reordering or truncating; narrative fields
(`description`, `known_biases`, `known_limitations`, `license_and_use_terms.license_terms`,
`human_subject_research`, `is_deidentified`, `version_access`) are byte-equivalent in parsed
form. `--sync-core` was **not** required: the pair validator passed on the first independent run.

`resources` is absent from both records. No sub-dataset decomposition is supported by the
bundle: the only candidate (a released controlled-access companion set) is described
prospectively rather than as an existing distribution (C15), so asserting it as a resource would
have been unsupported. The projection rule is therefore vacuously satisfied.

### Related-content semantic review

`file_collections` (full, 9 items) to `distributions` (core, 9 items). The validator matched all
nine deterministically on `path`; zero unmatched, zero ambiguous. Reviewed field by field:

| path | full `file_count` | full `total_bytes` = core `bytes` | standard (`conforms_to`) |
|---|---|---|---|
| `cardiac_ecg` | 4,515 | 302,931,703 | WFDB; CDS v0.1.1 |
| `clinical_data` | 7 | 176,182,781 | OMOP CDM; CDS v0.1.1 |
| `environment` | 2,232 | 55,625,676,514 | NASA ASCII/ESDS; CDS v0.1.1 |
| `retinal_flio` | 7,969 | 1,069,466,876,718 | DICOM; CDS v0.1.1 |
| `retinal_oct` | 56,478 | 1,317,625,293,027 | DICOM; CDS v0.1.1 |
| `retinal_octa` | 173,721 | 1,155,908,809,724 | DICOM; CDS v0.1.1 |
| `retinal_photography` | 93,921 | 174,381,046,406 | DICOM; CDS v0.1.1 |
| `wearable_activity_monitor` | 15,245 | 38,313,536,220 | Open mHealth; CDS v0.1.1 |
| `wearable_blood_glucose` | 2,246 | 4,169,006,971 | Open mHealth; CDS v0.1.1 |

Review findings:

- `name`, `path` and `description` are identical between each `FileCollection` and its matched
  `CoreDistribution`; `bytes` equals `total_bytes` in all nine cases. No conflicts.
- **Expected projection loss, not divergence:** `CoreDistribution` has no `file_count` and no
  `collection_type` or `conforms_to` slot, so per-directory file counts, the `processed_data`
  classification, and the format-standard strings exist only in full. This is a schema
  limitation of the exchange layer, not a content disagreement. The dataset-level counterparts
  `total_file_count` and `total_size_bytes` are likewise full-only by schema.
- `format`, `media_type`, `encoding` and `compression` were deliberately left unset on every
  distribution. The bundle declares media types at the dataset level
  (`application/dicom`, `text/markdown`, `text/csv`, `application/json`) but does not map them
  to individual directories, and several directory standards (WFDB, Open mHealth, DICOM) have no
  member in `FormatEnum`. Assigning them would have been inference, so they were omitted and the
  standards are stated in prose in each `description`. No `format`/`compression` conflict is
  therefore possible.
- Scope agreement: `total_file_count` (356,343) and `total_size_bytes` (3,815,969,779,678) in
  full describe the whole v3.0.0 release, whereas the nine distributions describe only the
  datatype directories. The scopes are deliberately different, the difference is explained above
  (9 root-level files, 419,614 bytes), and the two are consistent.
- `is_tabular` is `false` in both records and agrees with the mixed-modality composition
  (tabular, imaging, and physiological signal/waveform data) stated in the healthsheet.
- `dialect` was not set in core: no delimiter, quoting, header or comment-prefix convention is
  stated anywhere in the bundle for the CSV/TSV members.
- Identity/version/access facts agree across `id`, `doi`, `version`, `issued`, `license`,
  `page`, `publisher`, `status`, `version_access`, `distribution_dates`,
  `license_and_use_terms` and `regulatory_restrictions` in both records; historical releases
  (v1.0.0, v2.0.0) are labelled as such wherever they appear and are never presented as the
  current release.

### Commands run

```bash
poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_all.yaml \
  -C Dataset data/d4d_concatenated/claudecode_agent/2026-07-28_claude-opus-5-deprimed_rep1/AI_READI_d4d.yaml

poetry run linkml-term-validator validate-data \
  data/d4d_concatenated/claudecode_agent/2026-07-28_claude-opus-5-deprimed_rep1/AI_READI_d4d.yaml \
  --schema src/data_sheets_schema/schema/data_sheets_schema_all.yaml --target-class Dataset

poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml \
  -C CoreDataset data/d4d_concatenated/claudecode_agent_core/2026-07-28_claude-opus-5-deprimed_rep1/AI_READI_d4d_core.yaml

poetry run linkml-term-validator validate-data \
  data/d4d_concatenated/claudecode_agent_core/2026-07-28_claude-opus-5-deprimed_rep1/AI_READI_d4d_core.yaml \
  --schema src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml --target-class CoreDataset

poetry run python -m data_sheets_schema.d4d_pair_consistency \
  --full data/d4d_concatenated/claudecode_agent/2026-07-28_claude-opus-5-deprimed_rep1/AI_READI_d4d.yaml \
  --core data/d4d_concatenated/claudecode_agent_core/2026-07-28_claude-opus-5-deprimed_rep1/AI_READI_d4d_core.yaml

poetry run d4d provenance record --project AI_READI --method claudecode_agent \
  --label 2026-07-28_claude-opus-5-deprimed_rep1 \
  --input-bundle data/preprocessed/concatenated/AI_READI_preprocessed.txt
```

### Files changed

- `data/d4d_concatenated/claudecode_agent/2026-07-28_claude-opus-5-deprimed_rep1/AI_READI_d4d.yaml` (created, Phase 1; structurally corrected in Phase 3)
- `data/d4d_concatenated/claudecode_agent_core/2026-07-28_claude-opus-5-deprimed_rep1/AI_READI_d4d_core.yaml` (created, Phase 2; `Phase 4 reconciliation: completed` header added in Phase 4)
- `data/d4d_concatenated/claudecode_agent_core/2026-07-28_claude-opus-5-deprimed_rep1/AI_READI_reconciliation.md` (this report)
- `data/d4d_concatenated/claudecode_agent_core/2026-07-28_claude-opus-5-deprimed_rep1/AI_READI_provenance.yaml` (live provenance record)

No file outside this run's three declared outputs plus the provenance record was modified.

### Final results

- Full schema validation: **PASS** (`No issues found`)
- Full ontology term validation: **PASS**
- Core schema validation: **PASS** (`No issues found`)
- Core ontology term validation: **PASS**
- Pair consistency: **PASS** - 76 schema-identical slots, projected slots `['resources']`,
  zero errors. One warning, `semantic-review-required` on
  `$.file_collections <-> $.distributions`, which flags related content for human review; that
  review is recorded above with 9 deterministic matches and 0 unmatched distributions.
- Divergences between full and core requiring correction: **none**. Nothing diverged on any
  schema-identical slot, and every difference between the two records is an expected consequence
  of the `CoreDataset` field inventory, enumerated in "Full-only slots" and in the related-content
  review.
