# Reconciliation Report — AI_READI

**Version label:** `2026-07-31_claude-opus-5-generic-v2_rep2`
**Arm:** BASELINE (input documents only)
**Records reconciled:**

- Full — `data/d4d_concatenated/claudecode_agent/2026-07-31_claude-opus-5-generic-v2_rep2/AI_READI_d4d.yaml`
- Core — `data/d4d_concatenated/claudecode_agent_core/2026-07-31_claude-opus-5-generic-v2_rep2/AI_READI_d4d_core.yaml`

**Declared bundle:** `data/preprocessed/concatenated/AI_READI_preprocessed.txt` (10 sources)

---

## 1. Referent declaration

Both records take as their referent the **Flagship Dataset of Type 2 Diabetes from the AI-READI Project, version 3.0.0** (DOI `10.60775/fairhub.3`, published 2025-11-17, 2280 participants, 356,343 files, 3.82 TB). This is the release the bundle's current-state sources describe (`fairhub_dataset_v3`, `fairhub_dataset_v3_api`, `dataset_documentation_v3`). The v2.0.0 FAIRhub record and v2 documentation are retained in the bundle but are marked upstream as superseded and "no longer accessible"; they are treated as evidence *about* an earlier release, not as the referent. The AI-READI *study* (NCT06002048, 4000-person target, ongoing enrolment) is treated as context for the dataset, not as the referent itself. This choice is held identically in both records.

---

## 2. Audit outcome summary

The audit returned **18 findings: 0 high, 4 medium, 14 low.** No fabricated facts and no prior-D4D reuse were detected. Both records were found to track the declared bundle closely, and in two respects handled it well: the sponsor conflict (BMJ Open and NIH RePORTER name the University of Washington; the FAIRhub `studyDescription` names Washington University in St. Louis as lead sponsor and PI affiliation) is represented rather than silently resolved, and the acronym variance (*Equitable* Atlas in the publications, *Exploratory* Atlas in the NIH abstract, README and healthsheet) is likewise preserved. Aggregate file counts and byte totals across the nine data-type directories reconcile with the stated 356,343 files and 3.82 TB.

Disposition: **12 findings remediated, 6 left as-is with rationale.**

| # | Sev | Record | Slot | Disposition |
|---|-----|--------|------|-------------|
| 1 | med | full | `funders` | Changed |
| 2 | med | core | `funders` | Changed |
| 3 | med | full | `creators` (Ishikawa) | Changed |
| 4 | med | core | `creators` (Ishikawa) | Changed |
| 5 | med | core | 5 absence-statement slots | Changed |
| 6 | med | both | `variables` | Changed |
| 7 | low | both | `missing_data_documentation` | Changed |
| 8 | low | both | `acquisition_methods` | Changed |
| 9 | low | both | `collection_mechanisms` | Changed |
| 10 | low | full | `collection_timeframes` | Changed |
| 11 | low | core | `collection_timeframes` | Changed |
| 12 | low | full | `citation` | Left as-is |
| 13 | low | both | `related_datasets` | Changed |
| 14 | low | core | `labeling_strategies` (splits) | Changed |
| 15 | low | core | `participant_compensation` | Changed |
| 16 | low | core | `participant_privacy` | Changed |
| 17 | low | full | `human_subject_research` | Changed |
| 18 | low | full | `publisher` | Left as-is |
| 19 | low | full | `creators` (20 PIs) | Changed |

---

## 3. Changes to the full record

### 3.1 `funders` — unsupported grant-to-facility attribution removed (finding 1)

The BMJ Open funding statement reads only: *"This research is supported by National Institutes of Health grants OT2OD032644, P30DK035816, and UL1TR003096 and Research to Prevent Blindness."* The bundle separately describes the UW Nutrition and Obesity Research Center and the UAB Center for Clinical and Translational Science as study facilities, but never connects either grant number to either centre. The sentences *"P30 DK035816 is the grant supporting the University of Washington Nutrition and Obesity Research Center"* and *"UL1TR003096 supports the University of Alabama at Birmingham Center for Clinical and Translational Science"* were removed. Both `FundingMechanism` entries survive with grantor (NIH) and award number only. The OT2OD032644 entry is unaffected — its grantor, award title ("Bridge2AI: Salutogenesis Data Generation Project"), award amount and RePORTER link are all directly stated.

### 3.2 `creators` — Ishikawa affiliation removed (finding 3)

The Nature Metabolism principal-investigator list survives PDF extraction with its affiliation superscripts displaced. The marker adjacent to *Hiroshi Ishikawa* is `8`, which the affiliation key maps to Oregon Health & Science University, not `4` (University of Washington). The record asserted University of Washington. Since the extraction is unreliable at exactly this point and no other bundle source states Ishikawa's affiliation, the `affiliation` value was dropped; the `Creator` object retains the name and role.

### 3.3 `creators` — role and organizational creator corrected (finding 19)

The DataCite-style `datasetDescription.creator` list in the bundle contains exactly one entry: `AI-READI Consortium`, `nameType: Organizational`. The twenty named individuals appear elsewhere — in `studyDescription.overallOfficialList` as study principal investigators, and in the Nature Metabolism consortium author block. The record listed them flatly as dataset creators, conflating two roles the bundle keeps separate.

Two corrections: `AI-READI Consortium` is now present as an explicit organizational `Creator`, matching the declared creator metadata; and each individual retains a `Creator` entry (supported by the healthsheet statement that the dataset "was created by members of the AI-READI project") but with `role` set to the term the bundle actually uses for them — *Study Principal Investigator* — rather than an unqualified creator role. One object per person is retained, per the v2 multivalued rule.

### 3.4 `variables` — slot populated (finding 6)

This was the clearest supported omission in either record. The bundle carries variable-level metadata in explicit tabular form and neither record used any of it:

- BMJ Open Table 2 — approximately forty clinical laboratory analytes with units and reference ranges (e.g. Troponin-T, ng/L, female <11 / male <16; HbA1c, %, 4.0–6.0; Platelets, ×10E3/µL, 150–450; urine creatinine and urine albumin, mg/dL, no reference range given), each with a stated rationale for inclusion.
- BMJ Open Table 4 — environmental sensor variables (ambient temperature, relative humidity, nitrogen oxides NO and NO₂, volatile organic compounds, particulate matter at PM1.0 / PM2.5 / PM4 / PM10, and eleven multi-spectral light-intensity channels), and Garmin variables (steps, heart rate, sleep duration, oxygen saturation).
- Dexcom G6 — blood glucose in mg/dL sampled every 5 minutes.

`VariableMetadata` objects were added, one per distinct variable, carrying `variable_name` (required) plus unit, reference range and inclusion rationale where the source states them. Where a reference range is given as "Varies by age" or "N/A" that is recorded as stated rather than normalised away. The wearable-activity modality list from the API (`heart_rate`, `oxygen_saturation`, `physical_activity`, `physical_activity_calorie`, `respiratory_rate`, `sleep`, `stress`) was used to complete the Garmin set.

### 3.5 `related_datasets` — slot populated (finding 13)

The bundle states typed inter-dataset relations that both records had instead narrated inside `version_access` and `external_resources`. `DatasetRelationship` objects were added (both required keys present in each):

- v1.0.0, DOI `10.60775/fairhub.1`, released 2024-05-03 — prior version of this record.
- v2.0.0, DOI `10.60775/fairhub.2`, released 2024-11-08 — prior version of this record.
- Mini Version, DOI `10.60775/fairhub.4`, 100 participants — recorded as a related resource, **not** a version. The bundle's curation note is explicit that record 4 "is a distinct 'Mini Version' … for pipeline development, not a version of this dataset", and the API `data.child` field points to it. The relationship type reflects that distinction.

The narrative version history in `version_access` was retained, since it also carries the FAIRhub statement that the v2.0.0 record is no longer accessible, which the typed relations do not express.

### 3.6 `missing_data_documentation` — unsupported no-imputation claim removed (finding 7)

The healthsheet documents *why* data are missing (participants declining study elements; devices returned late or with dead batteries; data collisions; skipped survey questions) and describes REDCap range/skip-pattern/duplication checks. It says nothing about imputation. The record's sentence *"No imputation was applied; missing values are left missing"* converted silence into a positive claim and was removed. The documented sources of missingness are retained verbatim in substance. `imputation_protocols` remains unpopulated, which is the correct expression of the absence.

### 3.7 `acquisition_methods` — source wording restored (finding 8)

BMJ Open states: *"Patients with T2DM and pre-diabetes are identified by screening electronic health records for ICD-10 diagnosis codes R73.09 and E11.X, respectively."* Read literally the source pairs T2DM with R73.09 and pre-diabetes with E11.X. The records silently reversed this to the clinically conventional mapping. Silent correction of a source is outside the evidence boundary, so the text was rewritten to reproduce the source's own construction and to note that the code-to-condition pairing as printed is ambiguous. No third-party coding reference was consulted to adjudicate it.

### 3.8 `collection_mechanisms` — device count corrected (finding 9)

The retinal-imaging entry said "Six imaging systems" and then named seven: Optomed Aurora IQ, iCare EIDON, Heidelberg Spectralis HRA OCT/OCTA, Topcon Maestro2 3D OCT-1, Topcon Triton DRI OCT, Zeiss Cirrus 5000, and Heidelberg FLIO. BMJ Open Table 4 lists all seven. The count was corrected to seven. (The count of six is what one gets by treating the two Heidelberg entries as one device; the source tables them separately, with separate scan protocols and image counts.)

### 3.9 `collection_timeframes` — disagreeing follow-up figures separated (finding 10)

The record gave "approximately 4 to 10 percent of participants", which is a range the bundle never states — it is two different single figures averaged into a span. The healthsheet says *"Approximately 4% of participants are expected to undergo a follow-up examination in Year 4"*; the NIH RePORTER abstract and the dataset README both say *"longitudinal data from 10% of the study cohort"*, and the IRB protocol says *"we intend to invite 10% of the study population"*. Per the uniform rule on disagreeing sources, both figures are now stated with their sources rather than merged.

### 3.10 `human_subject_research` — interpretive gloss removed (finding 17)

The bundle gives the eligibility flag `healthyVolunteers: "No"` and nothing more. The record expanded this to *"healthy volunteers not accepted as a separate category"*, which is an interpretation of a flag whose semantics the bundle does not define — and one in tension with the study's own "Healthy" arm group and its "No DM" cohort of 776 participants. The gloss was removed; the flag value is recorded as stated. This also removes a full/core asymmetry, as the core record never carried the phrase.

---

## 4. Changes to the core record

### 4.1 `funders`, `creators` — same corrections as the full record (findings 2, 4)

The unsupported grant-to-centre attributions for P30DK035816 and UL1TR003096 were removed, and Ishikawa's University of Washington affiliation was dropped, exactly as in §3.1 and §3.2. The creator-role correction of §3.3 was applied identically so the two records agree on who is a dataset creator and in what capacity.

### 4.2 Five absence-statement slots removed (finding 5)

The core record populated five slots with statements that the thing the slot asks about does not exist:

| Slot | Value removed |
|---|---|
| `existing_uses` | "No prior uses recorded" |
| `use_repository` | "No repository tracking dataset uses" |
| `extension_mechanism` | "No external contribution mechanism" |
| `data_protection_impacts` | "No data protection impact assessment conducted" |
| `labeling_strategies` | "No labels applied" |

Each traces to a healthsheet answer of "No" or "N/A", so none is fabricated — but under the v2 rule a value recording that something is absent has not answered the field, and omission is the correct expression. The full record already omitted all five on the same evidence, so this change also removes five full/core inconsistencies. All five slots are now absent from the core record.

### 4.3 `labeling_strategies` — recommended split relocated out (finding 14)

The core record additionally used `labeling_strategies` to hold the recommended 70/15/15 train/validation/test partition, its balancing across sex, race/ethnicity, age and diabetes status, and the rationale (that sex and race/ethnicity are withheld from the public release, so the project pre-computes balanced splits). `labeling_strategies` declares annotation methodology; this is split design, which the full record correctly places in `splits` and `subsets`.

`CoreDataset` does not expose a `splits` slot. Per the v2 rule — put the material in the field it answers, or omit it — it was removed from `labeling_strategies` rather than relabelled, and is not carried elsewhere in the core record. The full record retains it in `splits`, with the participant counts from the README table (Train 1576, Val 352, Test 352, Total 2280; race/ethnicity, sex and diabetes-status breakdowns; mean age 60.8 ± 11.3 overall). Combined with §4.2, `labeling_strategies` is now absent from the core record entirely.

### 4.4 `collection_timeframes` — same figure separation (finding 11)

The 4-versus-10-percent merge described in §3.9 was corrected identically.

### 4.5 `participant_compensation` — added (finding 15)

Present in the full record, absent from the core, on evidence that supports both equally. Added: the $200 stipend for the study visit (healthsheet: *"Study subjects received a compensation of $200 for the study visit also through the grant funding"*; IRB protocol confirms the amount), payment typically at least two weeks after the visit and contingent on return of the take-home devices, not prorated, and reasonable parking / public-transit / rideshare costs covered.

### 4.6 `participant_privacy` — added (finding 16)

Likewise present in full and missing from core. Added: the environmental sensor and Garmin tracker were chosen so as not to capture video or audio, carry no GPS, and are not synced to participant-owned devices; study procedures conducted in private rooms; identifiable data on encrypted servers or in locked restricted-access storage at Risk Level 3; results returned by HIPAA-compliant encrypted email; and the project's stated data-watermarking measure against re-identification attempts.

### 4.7 `variables` — populated (finding 6)

The same `VariableMetadata` set described in §3.4 was added, so the two records agree on variable-level coverage.

### 4.8 `related_datasets` — populated (finding 13)

The same three `DatasetRelationship` objects described in §3.5 were added.

---

## 5. Findings left as-is

### 5.1 `citation` (full, finding 12)

The record renders: *"AI-READI Consortium (2025). Flagship Dataset of Type 2 Diabetes from the AI-READI Project (Version 3.0.0). FAIRhub. https://doi.org/10.60775/fairhub.3"*. No such formatted string appears in the bundle — both FAIRhub and the documentation decline to supply one and instead direct users to `https://docs.aireadi.org/docs/3/citation`, a page not captured in the bundle.

**Left as-is.** Every component is individually and directly stated in `datasetDescription`: `creator.creatorName` = AI-READI Consortium (Organizational); `publicationYear` = 2025; `title.titleValue`; `version` = 3.0.0; `publisher.publisherName` = FAIRhub; `identifier.identifierValue` = 10.60775/fairhub.3 with `identifierType` DOI. The slot's own description asks for the citation "in DataCite or BibTeX format", so assembling DataCite fields into DataCite form is the formatting the slot requests rather than the introduction of new fact. The alternative permitted by the v2 rule — replacing the value with a pointer to the citation page — is explicitly disallowed by that same rule, and omitting the slot would discard information the bundle does supply. The record notes that the canonical citation instructions live at the docs URL.

### 5.2 `publisher` (full, finding 18)

The value is the URI `https://fairhub.io`; the bundle states the publisher as the string `"FAIRhub"`. **Left as-is.** The slot range is `uriorcurie`, so a bare organisational name cannot be expressed in it without failing validation. `https://fairhub.io` is the platform's own address as given repeatedly in the bundle (FAIRhub record pages, README, healthsheet distribution answer), so the URI is the least inferential identifier available for the named publisher. The alternative — omitting a publisher the bundle explicitly names — loses more than the small derivation costs.

### 5.3 Sponsor conflict — deliberately unresolved

Not a finding, recorded here for completeness. BMJ Open and NIH RePORTER place the study and its IRB at the **University of Washington** (IRB STUDY00016228, approved by the UW IRB with reliance agreements from UAB and UCSD; NIH RePORTER organization "UNIVERSITY OF WASHINGTON"; the licence agreement names the University of Washington as Licensor). The FAIRhub `studyDescription` gives `leadSponsor` and every PI affiliation for Aaron Lee and Cecilia Lee as **Washington University in St. Louis** (ROR 01yc7t268), as does `managingOrganization` in `datasetDescription`. Both records state both, attributed. This is not smoothed to a single value and was not changed.

### 5.4 Acronym variance — deliberately unresolved

*Artificial Intelligence Ready and **Equitable** Atlas for Diabetes Insights* (BMJ Open, Nature Metabolism) versus *Artificial Intelligence Ready and **Exploratory** Atlas for Diabetes Insights* (NIH RePORTER abstract, FAIRhub README, healthsheet, `studyDescription.officialTitle` "AI Ready and Exploratory Atlas for Diabetes Insights"). Both expansions are recorded. Not changed.

### 5.5 v2.0.0 evidence — deliberately not merged into the referent

The bundle's two v2.0.0 sources (`fairhub_dataset`, `dataset_documentation`) report 2.01 TB / 165,051 files and are marked superseded. These figures are **not** blended with the v3.0.0 figures anywhere in either record; they appear only where the record describes the version history. This follows both the bundle's own curation notes and the rule against merging distinct entities.

---

## 6. Post-remediation state

| | Full | Core |
|---|---|---|
| Populated slots before | 60 | 36 |
| Populated slots after | 62 | 32 |
| Slots added | `variables`, `related_datasets` | `variables`, `related_datasets`, `participant_compensation`, `participant_privacy` |
| Slots removed | — | `existing_uses`, `use_repository`, `extension_mechanism`, `data_protection_impacts`, `labeling_strategies` |
| Slots revised in place | `funders`, `creators`, `acquisition_methods`, `collection_mechanisms`, `collection_timeframes`, `missing_data_documentation`, `human_subject_research` | `funders`, `creators`, `acquisition_methods`, `collection_mechanisms`, `collection_timeframes`, `missing_data_documentation` |

**Validation:**

- `linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_all.yaml -C Dataset …/AI_READI_d4d.yaml` — **passed**
- `linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml -C CoreDataset …/AI_READI_d4d_core.yaml` — **passed**

All `DatasetRelationship` objects carry `relationship_type` and `target_dataset`; all `VariableMetadata` objects carry `variable_name`; the `id` slot is present on both records and on every nested `DataSubset` and `FileCollection`.

**Provenance guard:** no external knowledge was introduced during remediation. Every change either removed an unsupported assertion, restored source wording, separated conflated sources, or populated a slot from material already present in the declared bundle. No previously generated D4D record was read or consulted at any phase.