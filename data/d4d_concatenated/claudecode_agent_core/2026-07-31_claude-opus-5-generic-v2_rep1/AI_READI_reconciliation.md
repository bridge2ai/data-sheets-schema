# Reconciliation Report — AI_READI

Phase 4 strict reconciliation of the paired full and core D4D records.

- Full record: `data/d4d_concatenated/claudecode_agent/2026-07-31_claude-opus-5-generic-v2_rep1/AI_READI_d4d.yaml`
- Core record: `data/d4d_concatenated/claudecode_agent_core/2026-07-31_claude-opus-5-generic-v2_rep1/AI_READI_d4d_core.yaml`
- Declared input bundle: `data/preprocessed/concatenated/AI_READI_preprocessed.txt`
- Arm: BASELINE (input documents only). No prior D4D record was read at any phase.

---

## 1. Referent declaration

`Dataset` admits one referent. Both records refer to:

**Flagship Dataset of Type 2 Diabetes from the AI-READI Project, version 3.0.0**, DOI `10.60775/fairhub.3`, published 2025-11-17, 2280 participants, 356,343 files, 3.82 TB.

Rationale. The declared bundle's selection manifest selects the v2.0.0 FAIRhub record and the v2.0.0 documentation, but both of those sources carry explicit curation notes directing that the v3.0.0 captures be preferred where the two disagree, and the FAIRhub v2 page itself states "This version of the dataset is no longer accessible." The v3 API capture (`fairhub_dataset_v3_api`) is also the only substantive structured metadata in the bundle; the HTML captures yield roughly 1.3 KB each. Evidence specific to v1.0.0 and v2.0.0 is retained only where it describes those releases as such — version history, per-version participant counts, per-version release dates — and is not used to characterise the referent.

This choice was applied identically in both records. It was implicit in Phase 1 and Phase 2 and is now stated here, as the audit required.

---

## 2. What the audit found

The audit examined both records against the bundle and returned 38 findings. No fabricated dataset fact was identified: every populated value traces to one of the FAIRhub v3 API metadata, the BMJ Open protocol (`bmjopen-2024-097449`), the Nature Metabolism comment (`s42255-024-01165-x`), the NIH RePORTER project page, the v1.0 licence PDF, the v2/v3 documentation pages, or the UW IRB protocol.

Three defect classes recurred, plus two supported omissions.

**Absence-as-value (core record).** Five core slots were populated with statements that the requested information does not exist: `data_protection_impacts` ("has not been conducted"), `existing_uses` ("had not yet been used for any tasks"), `use_repository` ("There is no repository…"), `extension_mechanism` ("no mechanism for others to extend"), `labeling_strategies` ("No labeling was performed"). The v2 rule directs omission in exactly this case. The full record already omits `labeling_strategies`, so the pair also disagreed with itself.

**Field-boundary placement (core record).** `distributions` carried nine per-datatype file inventories — directory names, file counts, byte sizes — which is file-collection material, not distribution material. `at_risk_populations` carried a general participant-privacy narrative while `participant_privacy` was left empty; the full record makes the opposite and correct assignment.

**Entity collapsing (full record).** One `FundingMechanism` object aggregated eight distinct in-kind contributors. `participant_compensation` bundled three distinct provisions into one object. Both violate the v2 one-object-per-entity rule for multivalued slots.

**Supported omissions.** `variables` was omitted despite BMJ Open Table 2 enumerating roughly forty named laboratory analytes with units and reference ranges against a `VariableMetadata` class requiring only `variable_name`. `subsets` was omitted despite the public / controlled-access two-tier partition being documented across the README, both documentation versions, the healthsheet, and the BMJ protocol.

**One synthesis defect.** `known_limitations` stated the longitudinal follow-up subgroup as "approximately 4-10% of the cohort" — an interval no source states, formed by merging the healthsheet's 4% with the grant abstract's, README's and IRB protocol's 10%.

---

## 3. Changes to the full record

| Slot | Change | Reason |
|---|---|---|
| `funders` | Split the single in-kind object into eight | Microsoft AI for Good Lab (cloud services), Topcon, Optomed, iCare World and Carl Zeiss (devices loaned at no cost), Heidelberg Engineering, Dexcom and Garmin (research discounts) are distinct entities contributing on distinct terms. `FundingMechanism` is multivalued. |
| `variables` | Added | 39 clinical laboratory analytes from BMJ Open Table 2, each with the unit and reference range the table supplies; 18 wearable and environmental sensor variables from Table 4 and the v3 API directory descriptions (CGM glucose at 5-minute interval; Garmin steps, heart rate, respiratory rate, oxygen saturation, sleep, stress, activity calorie; sensor ambient temperature, relative humidity, NO, NO₂, VOC, PM1.0, PM2.5, PM4, PM10, multi-spectral light intensity). |
| `subsets` | Added, two `DataSubset` objects | The publicly accessible set and the controlled-access set are a documented logical partition of the release with differing contents. This is distinct from the train/validation/test partition already carried in `splits`, which was left unchanged. |
| `related_datasets` | Added, three `DatasetRelationship` objects | v1.0.0 (`10.60775/fairhub.1`) and v2.0.0 (`10.60775/fairhub.2`) as prior versions; the Mini Version (`10.60775/fairhub.4`, 100 participants, pipeline development) as a related dataset. Required keys `relationship_type` and `target_dataset` are satisfiable for all three. |
| `resources` | Removed | Held only the Mini Version, now relocated to `related_datasets`. The bundle's own curation note states the Mini Version is "not a version of this dataset," and the slot description ("component datasets that are part of this dataset") does not fit a separately-DOI'd derivative cohort. |
| `known_limitations` | Split the "4-10%" claim | Now two statements: the grant abstract, README and IRB protocol specify longitudinal data from 10% of the cohort; the healthsheet states approximately 4% are expected to undergo Year 4 follow-up. Both are recorded as what their sources say; neither is merged into a range. |
| `participant_compensation` | Split into three objects | $200 stipend paid after device return; transportation support (parking, public transit, rideshare, reimbursed to $25 per the IRB protocol); prepaid return shipping materials and fees. |
| `collection_consents` | Trimmed second object | The T2DM-only use restriction was removed from the consent object. It is access-condition material and is already carried in `license_and_use_terms` and `intended_uses`. The consent-type code (`ConsentSpecifiedNotElsewhereCategorised`) remains. |
| `collection_timeframes` | Annotated | The BMJ protocol gives enrolment beginning 18 July 2023; the v3 API `startDateStruct` and `dateType: Collected` give 2023-07-19. The one-day divergence is now stated rather than presented as two unrelated facts. |
| `is_deidentified` | Annotated | The bundle's own `datasetDeIdentLevel` block is internally inconsistent: `deIdentType: NoDeIdentification` with `deIdentDirect: true` and `deIdentHIPAA: true`, alongside a README and Nature Metabolism statement that HIPAA Safe Harbor was applied to the public set. The record now marks the inconsistency as a property of the source rather than reproducing it silently. |

---

## 4. Changes to the core record

| Slot | Change | Reason |
|---|---|---|
| `data_protection_impacts` | Removed | Value asserted the analysis had not been conducted. Absence is not a value. |
| `existing_uses` | Removed | Value asserted no existing uses. The citation-requirement sentence it also carried is already in `license_and_use_terms`. |
| `use_repository` | Removed | Value asserted no such repository exists. The FAIRhub view counts it also carried are platform telemetry, not a use-tracking registry. |
| `extension_mechanism` | Removed | Value asserted no mechanism exists. |
| `labeling_strategies` | Removed | Value asserted no labeling was performed. The full record already omits this slot; the pair is now consistent. |
| `at_risk_populations` | Removed | The slot's declared subject is protections for minors, pregnant women, prisoners and comparable groups. Enrolment is restricted to adults aged 40+, and pregnancy, gestational diabetes and Type 1 diabetes are exclusion criteria. No at-risk population in the schema's sense is present in the bundle. |
| `participant_privacy` | Added | Now carries the six protections previously misfiled under `at_risk_populations`: no PHI in the released set; Safe Harbor de-identification of the public set; removal of sex, race/ethnicity and medication from the public tier; device selection for privacy (no video, no audio, no GPS, no pairing with participant-owned devices); encrypted HIPAA-compliant return of results; data watermarking and licence-level re-identification prohibition. This mirrors the full record. |
| `confidential_elements` | Removed | Populated primarily with the healthsheet's negative finding that the dataset contains no confidential data. The controlled-access content it also carried duplicates `sensitive_elements`, which is retained. |
| `distributions` | Repopulated | The nine per-datatype file inventories were removed; the core schema carries no file-collection slot and an inventory is not a distribution. The slot now carries distribution facts: FAIRhub as the distribution platform, DOI-resolved access, the four declared media types (`application/dicom`, `text/csv`, `application/json`, `text/markdown`), and the release dates for v1.0.0, v2.0.0 and v3.0.0. The file and byte totals for v3.0.0 are retained here as aggregate size, matching the `size` array in the v3 API. |

No other core slots were altered.

---

## 5. Left as-is, with reasons

**`created_by` and the managing organization.** The v3 API gives `managingOrganization` and `leadSponsor` as Washington University in St. Louis (ROR `01yc7t268`), and assigns that affiliation to Aaron Lee, Cecilia Lee and the central contact. Every other source in the bundle — the NIH RePORTER record, the BMJ protocol, the Nature Metabolism author list, the IRB protocol, and the FAIRhub location list — places Aaron Lee and the coordinating site at the University of Washington in Seattle. Promoting the St. Louis attribution into `created_by` or `publisher` would propagate what is almost certainly a source error. `created_by` remains "AI-READI Consortium," which the `datasetDescription.creator` block and the healthsheet both state directly.

**`creators`.** Retained as a single organizational `Creator`. The bundle's only creator declaration is organizational (`creatorName: AI-READI Consortium`, `nameType: Organizational`), and the healthsheet confirms it. The sixteen named individuals with ORCIDs appear as study principal investigators and overall officials — a study-role assertion — and the Nature Metabolism Writing Committee is authorship of that comment, not of the dataset. Emitting them as dataset creators would restate role evidence as authorship evidence.

**`publisher`.** Held as `https://fairhub.io/`. The bundle gives only `publisherName: FAIRhub` with no URI, but the slot range is `uriorcurie` and a bare name is not well-typed. The FAIRhub platform URL is stated throughout the bundle as the hosting and distribution platform, making it the minimum well-typed representation of the same fact.

**`license`.** Held as the combined name-and-URI string. The slot range is plain `string`, the bundle's `rights` block supplies both `rightsName` ("AI-READI custom license v2.0") and `rightsURI` (`https://doi.org/10.5281/zenodo.17555036`), and neither schema exposes a separate licence-URI slot. Discarding either component would lose evidence.

**`discouraged_uses`.** Omitted. Every use restriction in the bundle is framed as a licence prohibition — "Licensee shall not" — including the clinical-treatment restriction, which the licence states as a prohibition with "intended solely as a research resource" given as its rationale rather than as separate guidance. All five are carried in `prohibited_uses`. The healthsheet's discouraged-use question is answered by a pointer to the same licence. No separately discouraged use is stated anywhere in the bundle.

**`citation`.** Omitted. The dataset's own recommended citation is given only as a pointer: "follow the citation instructions provided at docs.aireadi.org." The v2 rule prohibits using a pointer as the value. The BMJ Open protocol's own citation is a citation for that article, not for the dataset, and is carried in `external_resources`.

**`content_warnings`, `errata`, `machine_annotation_tools`, `annotation_analyses`, `imputation_protocols`.** Omitted. Each corresponds to a healthsheet question answered "No," "N/A," or with an empty string. The near-imputation language under cleaning ("missing data that can be directly filled from other portions of an individual's record") is represented in `cleaning_strategies` and `missing_data_documentation`, where it describes an editing rule rather than an imputation protocol.

**`compression`, `download_url`, `conforms_to_class`, `was_derived_from`, `parent_datasets`, `created_on`, `last_updated_on`, `modified_by`.** Omitted, no supporting evidence. On `download_url` specifically: the bundle describes an access route — verified-ID login, self-attestation of T2DM research purpose, licence agreement — not a direct download endpoint. That route is recorded in `license_and_use_terms` and `third_party_sharing`, which is where it belongs. On the date slots: the documentation pages carry "Last updated on Jun 4, 2026 by Eamon Dysinger," which is the documentation site's edit metadata and not a property of the dataset. `data.parent: null` in the API is an explicit negative, not evidence of a parent.

**Core `instances`, second object.** The one-visit-per-participant and same-project statements were retained inside `instances`. The core schema exposes no `relationships` slot, and in a single-visit cross-sectional study the fact that an instance is one participant with one visit is a property of what an instance is, not a relation between instances.

**Core scalar totals.** `total_file_count` and `total_size_bytes` were not added as separate core slots; the core schema does not expose them. The same figures are retained in the repopulated `distributions` entry, matching the `size` array in the v3 API.

**`funders`, OT2OD032644 awardee organization.** The audit flagged and then withdrew this on re-check. NIH RePORTER gives Organization: UNIVERSITY OF WASHINGTON for application 10471118, and the healthsheet states participant compensation was paid through the grant. No change.

---

## 6. Net effect

| | Slots added | Slots removed | Objects restructured in place |
|---|---|---|---|
| Full | 3 (`variables`, `subsets`, `related_datasets`) | 1 (`resources`) | `funders`, `participant_compensation`, `known_limitations`, `collection_consents`, `collection_timeframes`, `is_deidentified` |
| Core | 1 (`participant_privacy`) | 7 (`data_protection_impacts`, `existing_uses`, `use_repository`, `extension_mechanism`, `labeling_strategies`, `at_risk_populations`, `confidential_elements`) | `distributions` |

The core record is now smaller than at Phase 2. That is the intended outcome: seven of the eight removals were slots occupied by statements that the requested information does not exist, and under the uniform decision rules an absent slot is the correct answer when the evidence is absent.

The two records now agree on every point where they previously diverged: `labeling_strategies` is omitted in both; participant-privacy evidence sits in `participant_privacy` in both; neither record files file-collection inventories under a distribution slot; and both resolve to the same v3.0.0 referent.

---

## 7. Outcome

Reconciled. Both records were re-validated after the changes above.

- `linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_all.yaml -C Dataset` — passed on the full record.
- `linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml -C CoreDataset` — passed on the core record.

All added objects satisfy their classes' required keys: the two `DataSubset` objects carry `id`; the three `DatasetRelationship` objects carry `relationship_type` and `target_dataset`; all 57 `VariableMetadata` objects carry `variable_name`.

No fabricated fact was introduced or retained. No previously generated D4D record was consulted at any phase.