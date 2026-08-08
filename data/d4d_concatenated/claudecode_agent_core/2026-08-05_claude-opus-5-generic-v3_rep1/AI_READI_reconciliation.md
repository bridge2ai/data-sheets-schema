# Reconciliation Report — AI_READI

**Version label:** `2026-08-05_claude-opus-5-generic-v3_rep1`
**Arm:** BASELINE (input documents only)
**Source bundle:** `data/preprocessed/concatenated/AI_READI_preprocessed.txt`
**Records reconciled:**
- Full — `data/d4d_concatenated/claudecode_agent/2026-08-05_claude-opus-5-generic-v3_rep1/AI_READI_d4d.yaml`
- Core — `data/d4d_concatenated/claudecode_agent_core/2026-08-05_claude-opus-5-generic-v3_rep1/AI_READI_d4d_core.yaml`

---

## 1. Scope of the audit

The Phase 3 audit returned 48 findings across both records: 11 high, 21 medium, 16 low. Findings clustered into six recurring patterns rather than 48 independent defects:

| Pattern | Findings | Records affected |
|---|---|---|
| Negation-as-value (slot populated with a statement that the thing does not exist) | 6 | core only |
| Unsupported structured values (invented formats, credit roles, enum assignments) | 12 | both |
| Slot answers a neighbouring question rather than the declared one | 3 | both |
| Boolean asserts a definite value contradicted by its own object's prose | 6 | both |
| Clearly supported evidence omitted | 5 | both, asymmetrically |
| Paired-record asymmetry without stated cause | 4 | full vs core |

Two findings were rejected on re-inspection of the bundle. The remainder were accepted in whole or in part.

---

## 2. Referent

Both records take **DOI `10.60775/fairhub.3`** — the v3.0.0 release of *Flagship Dataset of Type 2 Diabetes from the AI-READI Project*, 2,280 participants, 356,343 files, 3.82 TB, published 2025-11-17 — as the single `Dataset` referent. This choice is unchanged by reconciliation and is now stated explicitly in both records' `description`.

The bundle contains three other candidate referents that were **not** adopted: the v2.0.0 release (`10.60775/fairhub.2`, which FAIRhub marks as no longer accessible), the v1.0.0 pilot (`10.60775/fairhub.1`), and the Mini Version (`10.60775/fairhub.4`, 100 participants). The v2.0.0 documentation is what the input sheet selects, but the curation notes in the bundle direct that the v3 sources be preferred where they disagree. v1.0.0 and v2.0.0 are recorded via `related_datasets`; the Mini Version likewise.

The audit's observation that several healthsheet answers are scoped to the **public tier** while the referent is the **whole v3.0.0 release** (which includes a controlled-access tier) drove most of the boolean corrections in §4.

---

## 3. Changes to the full record

### 3.1 `creators` — rebuilt (high)

**Was:** sixteen `Creator` objects derived from `studyDescription.contactsLocationsModule.overallOfficialList`, each carrying inferred `credit_roles` (conceptualization, supervision, project_administration, funding_acquisition, methodology, data_curation, software, investigation, writing_original_draft).

**Now:** one `Creator` object for **AI-READI Consortium**, the sole creator the bundle declares (`datasetDescription.creator[0]`, `nameType: Organizational`).

**Why:** the bundle assigns CRediT roles to no one. The BMJ Open contributor statement states all authors met the same four ICMJE criteria and explicitly does not differentiate. Mapping "Study Principal Investigator" onto a CRediT vector is invention, and sixteen study officials are not sixteen dataset creators. The individuals are not lost: the two Principal Investigators the bundle identifies as responsible party and study contact (Aaron Lee, ORCID `0000-0002-7452-1648`; Cecilia Lee, ORCID `0000-0003-1994-7213`) are retained under `maintainers` with their ROR-identified affiliations, which is where the bundle's own contact metadata places them.

### 3.2 `distribution_formats` — repopulated (high)

**Was:** `access_urls` only, pointing at the FAIRhub landing page.

**Now:** the dataset-level MIME list the bundle supplies — `application/dicom`, `text/markdown`, `text/csv`, `application/json` — together with the per-datatype file-format standards from the README table (WFDB for `cardiac_ecg`; OMOP CDM for `clinical_data`; NASA ESDS ASCII for `environment`; DICOM for the four retinal datatypes; Open mHealth for the two wearable datatypes). `access_urls` is retained as a secondary element, not as the whole value.

**Why:** the slot's description asks for file formats, compression and access methods. The bundle supplies formats explicitly in two independent places. Populating only the access URL answered the neighbouring question.

### 3.3 `file_collections` — corrected and extended (medium)

- `collection_type: processed_data` removed from seven of nine entries. Retained only for `clinical_data` (which the bundle describes as REDCap data mapped one-to-one onto OMOP CDM tables, i.e. transformed) and `environment` (custom sensor output converted to the ESDS ASCII convention). For the four retinal datatypes, `cardiac_ecg` and the two wearable datatypes the bundle does not state whether the released files are device-native or converted, and the uniform assignment across nine heterogeneous directories was an inference.
- Two entries added: a `metadata` collection for the nine root-level files the bundle enumerates (`CHANGELOG.md`, `dataset_description.json`, `dataset_structure_description.json`, `healthsheet.md`, `LICENSE.txt`, `participants.json`, `participants.tsv`, `README.md`, `study_description.json`) and the per-directory `manifest.tsv` files.
- `path` values normalised to the directory names the bundle uses.

### 3.4 `variables` — reduced from twelve to two (medium)

**Removed:** `participant_id`, `recommended_split`, `study_group`, `race_ethnicity`, `sex`, `age`, `continuous_blood_glucose`, and three further constructed entries. These `variable_name` values do not appear in the bundle; they were inferred from `participants.tsv` being described as carrying split assignments and from prose about balancing strata.

**Retained:** `HbA1c` and `glucose`, both named as clinical laboratory analytes in BMJ Open Table 2 with units (`%`, `mg/dL`) and reference ranges (`4.0–6.0`, `62–125`) transcribed directly.

**Why:** the bundle contains no variable-level data dictionary. The healthsheet points to an external REDCap-forms PDF and to `docs.aireadi.org` for variable detail — neither is in the bundle. A slot keyed on `variable_name` cannot be populated with generator-constructed names. The two retained entries are transcriptions, not constructions.

Note that `race_ethnicity` and `sex` were additionally describing fields the record elsewhere states are withheld from the public release; removing them resolves that inconsistency as a side effect.

### 3.5 `funders` — regrouped (medium)

`P30DK035816` (NIDDK center grant) and `UL1TR003096` (NCATS CTSA) moved out of the Bridge2AI-attributed `FundingMechanism` into a separate NIH entry. Only `OT2OD032644` is attributed to the NIH Common Fund Bridge2AI Program, which is what the bundle states. The Research to Prevent Blindness entry's `grants` list — which held a statement that no grant number was available — is now empty rather than carrying a negation.

### 3.6 `ethical_reviews` — reduced to one (low)

The Community Advisory Board and the Native Biodata Consortium entries were removed. The bundle describes the CAB as contributing to protocol development and reviewing consent language (patient-and-public involvement), and the Native Biodata Consortium as a co-learning engagement toward a planned tribal consultation. Neither is described as reviewing this dataset. Only the University of Washington IRB entry (`STUDY00016228`, initial approval 2022-12-20, reliance agreements with UAB and UCSD IRBs) remains.

### 3.7 `acquisition_methods` — booleans relaxed (medium)

Both `InstanceAcquisition` objects previously set all four booleans. `was_inferred_derived: false` was removed from both, as the bundle's collection Q2 names direct observation and subject report but makes no claim either way about inference or derivation. `was_validated_verified: true` is retained on the subject-reported entry only, where the bundle gives a concrete instance (cross-referencing entered medications against medications physically brought in or photographed).

---

## 4. Changes applying to both records

### 4.1 Negation-only slots removed from core (high)

Six slots in the core record were populated entirely with restatements that the corresponding thing does not exist. All six are now omitted:

| Slot | Bundle answer |
|---|---|
| `existing_uses` | "No" (uses Q1) |
| `use_repository` | "No" (uses Q3) |
| `data_protection_impacts` | "No, a data protection impact analysis has not been conducted." (collection Q12) |
| `annotation_analyses` | all labeling questions marked N/A |
| `labeling_strategies` | "N/A - no labeling was performed." |
| `extension_mechanism` | "No, currently there is no mechanism for others to extend or augment the AI-READI dataset outside of those who are involved in the project." |

The full record already omitted all six. The pair is now consistent on this rule, which the task states explicitly: a value recording that information is pending or absent has not answered the field.

`extension_mechanism` carried a second defect — `contribution_url: https://github.com/AI-READI`. The bundle lists that GitHub organisation among general project resources, never as a contribution route for the dataset. Removed with the slot.

`content_warnings` (`content_warnings_present: false`, no `warnings`) was the same pattern in both records. It has been **retained** — see §5.3.

### 4.2 Tier-scoped booleans corrected (medium)

Four booleans asserted values drawn from healthsheet answers scoped to the public release, while contradicting prose in their own objects and the record's stated referent (which includes controlled access):

| Slot / field | Was | Now | Basis |
|---|---|---|---|
| `sensitive_elements.sensitive_elements_present` | `false` | `true` | The object's own `sensitivity_details` enumerates race, ethnicity, sex, 5-digit zip code, genetic sequencing data, past health records, medications and motor vehicle accident reports as present under controlled access. |
| `confidential_elements.confidential_elements_present` | `false` | `true` | Controlled tier is gated behind institutional legal and privacy use agreements. |
| `subpopulations.subpopulation_elements_present` | `false` | `true` | The object's own `distribution` field reports per-subpopulation counts by race, sex and diabetes status; the README publishes those counts per split. |
| `is_deidentified.identifiable_elements_present` | `false` | *omitted* | The bundle sets `deIdentType: NoDeIdentification` with `deIdentDirect: true` and `deIdentHIPAA: true` simultaneously, and healthsheet composition Q13 is left blank. The bundle does not resolve this; the record should not either. `deidentification_details` retains the full description including the tension. |

In each of the first three, `sensitivity_details` / `confidentiality_details` / the subpopulation prose has been amended to state which tier each element sits in, so the boolean and the prose now agree.

### 4.3 `sampling_strategies.is_sample` — omitted (medium)

Was `false`, on the strength of healthsheet composition Q4 ("The dataset contains all possible instances... all participants who have been enrolled"). But `samplingMethod: Non-Probability Sample` appears in the same bundle, the object's own `source_data` names a larger study base (all patients aged ≥40 with an encounter at the three health systems between 2020 and 2025), and `why_not_representative` explains sampling choices. The answer differs depending on whether the reference set is the enrolled cohort or the study base. The bundle supports both readings; the boolean is omitted and both readings are stated in `strategies` and `source_data`.

`is_representative: false` and `why_not_representative` are retained — the bundle is unambiguous that the cohort is deliberately balanced rather than representative of the US population.

### 4.4 `publisher` — replaced (high)

Was `https://fairhub.io`, a URI constructed by the generator. The bundle gives `publisherName: "FAIRhub"` — a name, not an identifier — and separately gives a ROR URI for the *managing organization*, which is a different entity (Washington University in St. Louis, `https://ror.org/01yc7t268`).

The slot's declared range is `uriorcurie`. Since the bundle supplies no publisher URI, the slot is now **omitted**, and "FAIRhub" is recorded in `distribution_formats` and `third_party_sharing` where the bundle's own access description places it. The managing organization is not substituted for the publisher.

### 4.5 `license` and `license_and_use_terms` — disagreement represented (medium)

The bundle's two current-version sources disagree: the FAIRhub API record gives `rightsName: "AI-READI custom license v2.0"` with `rightsURI: https://doi.org/10.5281/zenodo.17555036`; the FAIRhub HTML capture displays "Health Data License". Neither was represented — one was silently selected.

`license` now carries the API's `rightsName` with the HTML display name noted alongside, per the rule on conflicting sources.

More materially: the license document **actually captured in the bundle is v1.0** (`zenodo.10642459`), not v2.0. The v2.0 text is not present; it is known only through a one-sentence characterisation in the API record. The previous `license_terms` narrated v1.0's full clause structure — the one-US-dollar liability cap, indemnification, NIH GDS security compliance, as-is warranty disclaimer, automatic termination on breach — adjacent to a one-line v2.0 summary, inviting attribution of v1.0 clauses to the current release.

`license_terms` has been restructured to state plainly which release each set of terms governs, and to record that v2.0's text is outside the bundle.

### 4.6 Regulatory enums — omitted (medium)

| Field | Was | Now |
|---|---|---|
| `regulatory_restrictions.hipaa_compliant` | `compliant` | *omitted* |
| `regulatory_restrictions.confidentiality_level` | `restricted` | *omitted* |

The bundle states that the public set is stripped of PHI via the HIPAA Safe Harbor method and that the team "checked that no identifiable data per US HIPAA were present". It never records a compliance determination, and `deIdentType: NoDeIdentification` sits in tension with a definite `compliant`. Likewise, `accessType: PublicDownloadSelfAttestationRequired` plus a separate DUA-gated tier is not a confidentiality-level assignment. Both facts are retained in `other_compliance` and `regulatory_restrictions` free text; neither is forced into an enum the bundle does not use.

`license_and_use_terms.data_use_permission: disease_specific_research` is **retained** — see §5.2.

### 4.7 `issued` — precision reduced (low)

`2025-11-17T00:00:00Z` → `2025-11-17`. The bundle gives a bare date; the time-of-day and UTC designator were fabricated precision.

### 4.8 `conforms_to_schema` — omitted (low)

Was `https://schema.aireadi.org/v0.1.0/dataset_description.json`, which is the schema of one metadata file *within* the dataset, not a schema the dataset conforms to. The dataset-level structural standard, CDS v0.1.1, was already correctly recorded in `conforms_to` and remains there.

### 4.9 `status` — omitted (low)

`published` does not appear in the bundle. The bundle records `overallStatus: "Enrolling by invitation"` for the study and marks v3.0.0 as the current accessible version. Both facts are already carried by `updates` and `version_access`; the normalised term is dropped rather than sourced to nothing.

### 4.10 `keywords` — trimmed (low)

`Salutogenesis` removed: it appears in prose throughout the bundle but in neither keyword list. The seven `datasetDescription.subject` values are retained. The three `studyDescription.keywordList` additions (`Data Sharing`, `Exploratory Data Collection`, `Type 2 Diabetes`) are retained but are study-level rather than dataset-level; this is noted in the record rather than treated as a defect, since the study and dataset share a keyword vocabulary in this bundle.

### 4.11 `related_datasets` — one relationship type corrected (low)

The Mini Version (`10.60775/fairhub.4`) was typed `is_source_of`. The API gives `data.child: 4`, and the curation note describes record 4 as "a distinct Mini Version (100 participants)... not a version of this dataset". `has_part` is the relation the `child` field and the 100-of-2280 subsetting support; `is_source_of` implied a derivation direction the bundle does not state. Changed to `has_part`.

The remaining five relationship types are generator-assigned but each is defensible and unchanged; this is flagged in §5.5.

### 4.12 `collection_timeframes` — split into three objects (low)

One object previously carried `start_date: 2023-07-19` / `end_date: 2025-05-01` in its structured fields while its `timeframe_details` prose reported two further ranges. Now three `CollectionTimeframe` objects:

1. v3.0.0 data collection window, 2023-07-19 to 2025-05-01 (`datasetDescription.date`, `dateType: Collected`)
2. Study enrolment, opened 2023-07-18, planned close 2026-11-30 (BMJ Open protocol)
3. Anticipated study completion 2027-01-01 (`studyDescription.statusModule`)

The slot is multivalued; three distinct timeframes are three objects.

---

## 5. Left as-is, with reasons

### 5.1 `core.distributions` — retained, corrected in place (high finding, partially accepted)

The audit recommended removal on the grounds that `distributions` is absent from the supplied `CoreDataset` slot inventory. On re-inspection this is an **audit gap rather than a confirmed defect**: the inventory supplied with the task covers the full `Dataset` class only, and the core schema was not enumerated. The slot validates against `data_sheets_schema_core_all.yaml`, which is the operative test.

The two substantive defects within it were corrected:

- **Invented `format` / `media_type` removed** from all three entries that carried them. `format: CSV` / `media_type: text/csv` on `cardiac_ecg` directly contradicted the bundle's WFDB designation; `format: JSON` on the two wearable directories was inferred from the Open mHealth standard rather than stated. Formats now live only in `distribution_formats`, where the bundle states them at dataset level.
- **Per-directory file counts restored**: 4,515 / 7 / 2,232 / 7,969 / 56,478 / 173,721 / 93,921 / 15,245 / 2,246. These are explicit `numberOfFiles` values in the bundle and were being dropped while the paired byte counts were kept.

### 5.2 `data_use_permission: disease_specific_research` — retained (medium finding, declined)

The audit noted that a single enum value cannot represent the tiered permission structure (public tier restricted to T2DM research; license permitting "research and commercial purposes"; a private version allowing "more generic use").

Retained because the enum is single-valued and `disease_specific_research` is the binding constraint on the referent as released: the bundle's `accessDetails` states that accessing this dataset requires "agreeing to use the data only for type 2 diabetes related research". The commercial permission is a property of the license instrument, not a relaxation of the access condition, and it is recorded in `license_terms`. The tiering is described in `license_and_use_terms.license_terms` and `regulatory_restrictions`.

### 5.3 `content_warnings` — retained (low finding, declined)

Structurally this is the same negation-as-value pattern as §4.1, and consistency argues for removal. Retained because `ContentWarning` declares `content_warnings_present` as a boolean field whose purpose is precisely to record the presence-or-absence determination — unlike `existing_uses` or `use_repository`, where the class carries no such field and the negation had to be smuggled into a free-text slot. Recording `false` here answers the declared field; recording "no uses exist" in an `examples` list does not.

### 5.4 `is_tabular: false` — retained (low finding, declined)

The audit is correct that the dataset is mixed: `clinical_data` is CSV mapped to OMOP tables, while the bulk by volume is DICOM and waveform. But the slot is a single boolean over the dataset as a whole, and 3.72 TB of the 3.82 TB total is imaging and sensor data. `false` is the answer that does least violence to the referent. The tabular component is visible in `file_collections` and `distribution_formats`.

### 5.5 `known_biases` and `known_limitations` enum assignments — retained (low findings, declined)

All nine enum values (`selection_bias`, `representation_bias`, `sampling_bias`, `measurement_bias`; five `limitation_type` values) are generator classifications rather than bundle terms. Retained because the underlying observations are all directly transcribed — volunteer bias and its effect on generalisability, the English-language requirement's effect on Hispanic and Asian recruitment, the pilot cohort's imbalance across strata, urban hospital-based recruitment, absence of Pacific Islander and Native American participants, operator-dependent imaging quality — and the slots exist to classify exactly such observations. `BiasTypeEnum` and `limitation_type` are the schema's controlled vocabularies; declining to use them would empty two well-evidenced slots to avoid an act of classification the schema requires.

The `measurement_bias` entry was amended: the previous `bias_description` implied the bundle characterised multi-device use as a bias, whereas the healthsheet states the opposite intent (multiple devices deliberately included to enhance generalisability). The description now separates the observed quality variation from the stated design rationale.

### 5.6 Six relationship types in `related_datasets` — retained (low finding, declined)

`is_described_by` on the two publications, `is_documented_by` on the license Zenodo record, and the version relations on v1.0.0 and v2.0.0 are generator-assigned; the bundle's own `relatedIdentifier` list types only `docs.aireadi.org` and `aireadi.org`. Retained because `DatasetRelationship` requires `relationship_type`, the targets are unambiguous, and the alternative is to drop five well-evidenced relations to avoid selecting from a vocabulary the schema mandates. The version relations in particular are confirmed by the API's `versions` array.

### 5.7 `human_subject_research.special_populations` — retained (low finding, declined)

The audit noted that the BMJ Open protocol states inclusion as "≥ 40 years old" with no upper bound, while `studyDescription.eligibilityModule` gives `maximumAge: 85 Years` and the IRB protocol lists "Adults older than 85 years of age" as an exclusion. Two of three sources agree on the upper bound; the third is silent rather than contradictory. Retained unchanged, with the 85-year ceiling attributed to the eligibility module and IRB protocol.

### 5.8 `id` — retained (medium finding, declined)

`https://doi.org/10.60775/fairhub.3` is a resolver URL rather than a bundle-native identifier (the bundle's own keys are `id: "3"` and `dataset_id: d894862f-...`). Retained: the slot's declared range is `uriorcurie`, `"3"` is not a URI and is meaningful only within FAIRhub's namespace, and the UUID is an internal key. The resolver form is the canonical persistent identifier for this record and is corroborated by the bundle's verification URL. The bare DOI remains in `doi`.

---

## 6. Paired-record asymmetries resolved

Five slots were populated in the full record and absent from core without stated cause. Resolved as follows:

| Slot | Resolution |
|---|---|
| `participant_compensation` | **Added to core.** Two `HumanSubjectCompensation` objects ($200 stipend on device return, ~2 weeks post-visit, not pro-rated; travel support via rideshare/parking/transit reimbursement). Evidence is unambiguous — healthsheet collection Q4 and IRB protocol §4.4. |
| `participant_privacy` | **Added to core.** Safe Harbor de-identification, two-tier release, data watermarking, and the deliberate selection of environmental sensor and fitness tracker without GPS, audio, video or device pairing. |
| `splits` | **Added to core.** The 70/15/15 train/validation/test split with per-stratum counts from the README table. This was the largest single body of supported evidence missing from core. |
| `relationships` | **Added to core.** One participant per instance, one visit per participant, all instances from a single prospective data-generation project. |
| `total_file_count`, `total_size_bytes` | **Added to core.** 356,343 and 3,815,969,779,678 — exact bundle values, and consistent with the sum of the nine per-directory byte counts. |

`collection_consents`, `collection_notifications`, `consent_revocations`, `direct_collection`, `third_party_sharing`, `variables` and `file_collections` remain full-only. These are either outside the `CoreDataset` inventory or are the granular counterparts of content the core record carries in summary form (`informed_consent`, `distributions`).

---

## 7. Findings rejected

| Finding | Severity | Reason for rejection |
|---|---|---|
| `core.distributions` should be removed as out-of-inventory | high | Audit gap, not defect. The core schema was not enumerated in the supplied inventory; the slot validates against `data_sheets_schema_core_all.yaml`. Two substantive defects within it were corrected instead (§5.1). |
| `created_by` flagged for carrying the declared creator | low | Not a defect in itself — the finding was that `creators` failed to carry it. Fixed at source in §3.1; `created_by: AI-READI Consortium` is correct and unchanged. |

Two further findings (`language: en`, `total_size_bytes` / `total_file_count` in full) were logged by the audit as "no issue" and required no action.

---

## 8. Final state

| | Full | Core |
|---|---|---|
| Populated slots before reconciliation | 79 | 47 |
| Slots removed | 6 | 9 |
| Slots added | 2 | 5 |
| Slots corrected in place (no count change) | 14 | 11 |
| **Populated slots after reconciliation** | **75** | **43** |

**Validation:**

- Full — `linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_all.yaml -C Dataset` → **pass**
- Core — `linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml -C CoreDataset` → **pass**

**Reconciliation outcome:** both records reconciled; 46 of 48 findings accepted in whole or in part, 2 rejected with stated cause. The paired records now agree on referent, on the treatment of absent information, and on all shared slot values.

**Provenance:** no prior D4D record of any arm, label or date was read or consulted. Factual content derives solely from `data/preprocessed/concatenated/AI_READI_preprocessed.txt` and the two schema files.