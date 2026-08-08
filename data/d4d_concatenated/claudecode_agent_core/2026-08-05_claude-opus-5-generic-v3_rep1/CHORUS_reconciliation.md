# Reconciliation Report — CHORUS

**Version label:** `2026-08-05_claude-opus-5-generic-v3_rep1`
**Arm:** BASELINE (input documents only)
**Declared bundle:** `data/preprocessed/concatenated/CHORUS_preprocessed.txt` (4 files: NIH RePORTER project 10472824; AIM-AHEAD Bridge2AI for Clinical Care Cohort 2 webinar, Sept 2025; chorus4ai.org project documentation; chorus-ai GitHub organization overview, 2025-11-14)

---

## 1. Referent decision

`Dataset` admits one referent. The declared bundle describes three distinguishable things: (a) the CHoRUS multimodal controlled-access clinical dataset, (b) the chorus-ai software/SOP/mapping organization, and (c) the AIM-AHEAD Bridge2AI for Clinical Care training program that provides access to (a).

**Both records take (a), the CHoRUS clinical dataset, as the referent.** The GitHub organization is represented only where it documents how the dataset was produced, standardized, or delivered (preprocessing, labeling, annotation tooling, contribution mechanism, maintainer contacts). The training program is represented only where it documents existing use of the dataset and the access route. This choice is held consistently across the full and core records.

## 2. Handling of the internal source disagreement

The bundle contains two non-agreeing size snapshots for the same dataset:

- Webinar (as of August 2025): 14 hospitals, **over 45K unique admissions**, 1,000 imaging studies available with de-identification in process, EEG extraction in process.
- Project website (undated "Current Released Dataset"): **50,000 patient admissions** from ICU/PICU/NICU, 1.6 billion rows of EHR OMOP data, 7,642 admissions with radiology data, 23 Tb waveform data — alongside an "Anticipated Final Dataset" of 100,000 admissions, 9 modalities, 14 hospitals.

Both snapshots are carried in both records, each attributed to its source and its stated as-of framing. Neither was selected over the other and they were not merged into a single figure. The 100,000 figure is represented as an anticipated target, matching the NIH abstract ("more than 100,000 critically ill patients"), not as a current holding.

---

## 3. Changes made

### 3.1 Ethics block — unsupported oversight framing removed (both records)

`ethical_reviews` was removed from both records. The slot asks for IRB approvals, ethics-committee reviews, and compliance certifications; the bundle documents none. What it does document — community-facing ethics focus groups to determine what data is appropriate for public sharing, and analysis of the existing legal and regulatory landscape — is a research pillar, not a review body. Two specific defects drove the removal:

- `reviewing_organization` presented the CHoRUS "Ethics (Ethical and Trustworthy AI)" pillar as a reviewing organization.
- `contact_person` named Yulia Strekalova. She appears in the bundle only in the Bridge2AI CHoRUS Leadership Team roster (University of Florida), with no stated ethics, IRB, or review role.

No content was lost: the focus-group and legal-framework activities were already represented under `purposes` and `tasks`, where they answer the field being asked.

`data_protection_impacts` was removed from both records for the same reason. The bundle records privacy-limiting transformations, ethics focus groups, and legal analysis, but no DPIA or equivalent formal privacy risk assessment. The substantive content is retained under `preprocessing_strategies` and `purposes`.

### 3.2 CTP-deid — function inferred from repository name (both records)

The records asserted that CTP-deid is an imaging de-identification pipeline applied to CHoRUS imaging. The bundle contains only a bare repository listing: `CTP-deid Public`, no description, no language, no stated linkage to imaging. The function was inferred from the name.

The CTP-deid attribution was removed from `preprocessing_strategies`, `participant_privacy`, `is_deidentified`, and `machine_annotation_tools`. The underlying claim that imaging de-identification is occurring is separately and directly supported ("Imaging – currently 1000 images available with de-id in process for larger cohort") and was retained, now sourced to the webinar rather than to a repository name.

### 3.3 Collection timeframe — award period conflated with data coverage

The core record emitted `start_date: 2022-09-01` and `end_date: 2026-11-30` as structured collection dates. These are the NIH RePORTER project start and end dates. The bundle states collection is **retrospective**, so the period covered by the clinical records is unknown and in general precedes the award start. Asserting the award window as the collection window is a category error, and asserting it as a structured date range is worse than asserting it in prose.

- **Core:** `start_date` and `end_date` removed. `timeframe_details` now states that collection is retrospective, that the record-coverage period is not stated in the sources, and that 2022-09-01 to 2026-11-30 is the NIH award project period.
- **Full:** the same conflation existed in prose; the wording was corrected to match.

### 3.4 Metadata-column misattribution (both records)

Both records stated that "publication of a metadata schema was planned" for clinical notes, imaging, and EEG. In the source table, the value `Planned` sits in the **Metadata** column, while the **Published metadata schema** column reads `Yes (OHNLP open source schema)`, `Yes (DICOM schema)`, and `Yes (open source EDF+ and Persyst schema)` for those three modalities. The claim inverted which item is pending.

The table is partially garbled in the concatenated bundle (column headers and cell values are separated in the extraction). The corrected statement is the conservative one the extraction supports: **metadata status is recorded as Planned** for clinical notes, imaging, and waveform EEG, while a published schema is named for each. Applied in `file_collections` and in the corresponding `resources` entries in both records.

### 3.5 Inferred causal link between geocoding and SDOH (both records)

`preprocessing_strategies[3]` joined the GitHub `UF-Geocoding` repository ("Open source code to geocode OMOP Location entities via DeGauss") to the NIH abstract's "geographic distance to the nearest hospital" and to social determinants of health as one causal preprocessing step. The two sources make no such connection. The entry was split into two independent statements — the geocoding tool as described by the repository, and the contextual-factor/SDOH aim as described by the abstract — with no asserted link.

### 3.6 Known biases — project aims recorded as dataset biases (both records)

Two of three `known_biases` entries did not describe biases present in the data:

- The `representation_bias` entry's `bias_description` stated that the project "explicitly addresses the management of bias." That is a project aim, not a property of the dataset.
- The `measurement_bias` entry asserted that measurement and documentation conventions differ across contributing hospitals. The bundle documents heterogeneous source systems and a harmonization effort; it does not state that conventions differ, nor characterize any difference as bias.

Both entries were removed. The bias- and SDOH-management aim, and the federated-sampling approach intended to "ensure a balanced and diverse cohort," are retained under `purposes` and `sampling_strategies`, which is where the evidence answers.

### 3.7 False precision in instance counts (both records)

`instances[2].counts: 45000` asserted an exact figure where the source reads "over 45K unique admissions." The integer field cannot carry the qualifier, so the value was removed and the qualified statement retained in `label_description`. The website's "50,000 patient admissions" is an unqualified figure and remains as a structured count in the corresponding instance entry.

### 3.8 Attribution corrections

- `created_by` read "Massachusetts General Hospital coordinating." The bundle establishes MGH as the NIH award organization, the principal investigator's institution, and the program manager's institution, but nowhere states MGH coordinates the consortium. Reduced to "Massachusetts General Hospital."
- `acquisition_methods[*].was_validated_verified: true` was removed from both entries in both records. The bundle documents validated semantic mappings, internally reviewed SOPs, and post-submission characterization reports (`CHoRUSReports`) — none of which is a statement that acquired instances were validated or verified. Those three items are retained under `cleaning_strategies` and `labeling_strategies`, where they answer the declared field.

### 3.9 Paired-record asymmetries resolved

The following differed between the full and core records despite identical evidence. All were resolved in favor of the better-supported form.

| Slot | Was | Now |
|---|---|---|
| `machine_annotation_tools` | populated in core, omitted in full | populated in both (OHNLP toolkit; `privacy_scan_tool`; UF-Geocoding/DeGauss). CTP-deid excluded per §3.2 |
| `license` | prose in core mixing controlled access with the repositories' MIT license; omitted in full | omitted in both. MIT applies to the chorus-ai code repositories, not to the clinical dataset; relocated to `license_and_use_terms.license_terms` as an explicit software-vs-data distinction |
| `third_party_sharing` | bare `is_shared: true` in full, absent in core | removed from full. The boolean carried no information not already in `license_and_use_terms` and `regulatory_restrictions` |
| `related_datasets` | `is_part_of` → "NIH Bridge2AI consortium data generation projects" in full, absent in core | removed from full. The target is a program, not a dataset, and the relationship described is project membership. Retained as prose in `description` and `purposes` |
| `collection_timeframes.timeframe_details`, `is_deidentified.method`, `is_deidentified.identifiable_elements_present`, `subpopulations[*].subpopulation_elements_present`, `creators[0].principal_investigator` | declared object fields populated in core, held only as free text in full | populated as declared fields in both |

---

## 4. Left as-is, with reasons

**`creators` — six named individuals.** The bundle titles these six the "Bridge2AI CHoRUS Leadership Team," not dataset creators, and only Rosenthal is source-confirmed in a creator-adjacent role (NIH RePORTER principal investigator). They were retained with `affiliations` populated as stated, `principal_investigator: true` on Rosenthal only, and `credit_roles` left unpopulated — the bundle assigns no CRediT-style contribution to anyone. Retaining leadership as creators is a residual interpretive step, but the alternative (a single-creator record for a 60-member, 20-institution consortium) misrepresents the evidence more than it corrects. Documented here rather than silently resolved.

**Waveform volume not emitted as `total_bytes`.** The website reports "23 Tb" of waveform data. Converting this to an integer byte count requires choosing between TB and TiB, and the literal unit given is terabits. Any integer emitted would assert a precision and a unit convention the source does not state. The figure is retained verbatim in the waveform file collection's descriptive text instead.

**`distribution_formats` omitted in both records.** The per-modality formats (OMOP, OHNLP, DICOM, WFDB, EDF+/Persyst) are already carried in `file_collections[*].conforms_to`, which is where the standards-conformance evidence answers. Populating `distribution_formats` would restate the same facts without adding the access-route information the slot is really asking for; the access route is in `license_and_use_terms` and the registration/licensing-agreement description.

**Constructed `id` values.** `https://chorus4ai.org/dataset` and the derived per-collection URIs are constructed. No DOI, accession number, or canonical dataset URI appears anywhere in the bundle. `id` is required by both schemas, so omission is not available; the construction is disclosed here.

**Slots left unpopulated because the bundle does not support them:** `doi`, `citation`, `version`, `errata`, `retention_limit`, `updates` (frequency), `prohibited_uses`, `content_warnings`, `download_url`, `total_size_bytes`, `human_subject_research.irb_approval`, `regulatory_restrictions.hipaa_compliant`, `participant_compensation` (the $8,000 figure is a *trainee* stipend, not participant compensation, and was not repurposed), `informed_consent`, `collection_consents`, `consent_revocations`, `at_risk_populations`, `annotation_analyses`, `imputation_protocols`, `splits`. The dataset is described as retrospective and controlled-access with no consent documentation in any source; absence is the correct answer.

**The `bihorac-LAB/Exposome` fork lineage** of UF-Geocoding is recorded as stated (a fork) and not elaborated; the bundle says nothing about the upstream project.

---

## 5. Outcome

| | Before | After |
|---|---|---|
| Full record — populated top-level slots | 48 | 46 |
| Core record — populated top-level slots | 25 | 23 |
| Medium-severity findings | 6 | 0 |
| Low-severity findings | 15 | 6 resolved, 9 dispositioned as-is with stated reason |

Net slot movement is small because most changes were corrections within objects rather than removals of whole slots: four slots were removed as unevidenced (`ethical_reviews`, `data_protection_impacts` in both; `third_party_sharing`, `related_datasets` in full; `license` in core), and two were added to restore symmetry (`machine_annotation_tools` in full, plus several declared object fields in both).

**Reconciliation outcome: both records reconciled; full and core are now factually and structurally consistent with each other and with the declared bundle.** Both validate against their respective schemas.