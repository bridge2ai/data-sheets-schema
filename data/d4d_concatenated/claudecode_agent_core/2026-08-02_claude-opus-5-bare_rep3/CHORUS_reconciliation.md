# CHoRUS — Phase 4 Reconciliation Report

**Version label:** `2026-08-02_claude-opus-5-bare_rep3`
**Arm:** BASELINE (input documents only)
**Declared input bundle:** `data/preprocessed/concatenated/CHORUS_preprocessed.txt` (4 files: NIH RePORTER project page, AIM-AHEAD Cohort 2 webinar deck, chorus4ai.org project documentation, chorus-ai GitHub organization overview)
**Records reconciled:**
- Full — `data/d4d_concatenated/claudecode_agent/2026-08-02_claude-opus-5-bare_rep3/CHORUS_d4d.yaml`
- Core — `data/d4d_concatenated/claudecode_agent_core/2026-08-02_claude-opus-5-bare_rep3/CHORUS_d4d_core.yaml`

---

## 1. Referent decision

`Dataset` admits one referent. The declared bundle describes several candidate objects: the NIH data-generation *project* (`OT2OD032701`), the CHoRUS *network/consortium* (20 academic centers, 14 contributing), the chorus-ai *software organization* (28 repositories under MIT/Apache-2.0), the AIM-AHEAD *training program*, and the CHoRUS *dataset* itself.

**Chosen referent: the CHoRUS controlled-access multimodal critical care dataset** — the multicenter, multimodal, high-resolution retrospective clinical dataset assembled from 14 contributing hospitals and released under controlled access into the CHoRUS cloud enclave.

This choice is held identically in both records. Consequences enforced during Phase 4:

- The **MIT license** stated in the GitHub overview scopes to the chorus-ai *software*, not to the dataset. Neither record populates `license` for the dataset; the software licensing is recorded only where the bundle attaches it (repository-level).
- The **training program** (stipend, eligibility, application dates, curriculum) is not dataset content. It survives only where it evidences dataset access conditions (registration form, licensing agreement, `.edu` email requirement) — i.e. in access/use-terms slots, not as dataset properties.
- The **NIH award period** describes the project, not the data.

---

## 2. Source disagreements — how they were represented

The bundle contains two genuine internal disagreements. Neither was silently resolved.

| Disagreement | Sources | Treatment |
|---|---|---|
| Released admission count | chorus4ai.org: "50,000 Patient admissions from ICU, PICU, and NICU" vs. Cohort 2 webinar: "As of August 2025 … over 45K unique admissions" | Both figures retained with attribution and date qualifier in both records. No midpoint, no preference. |
| Total scale | chorus4ai.org "Anticipated Final Dataset: 100,000 Patient admissions" / NIH abstract "more than 100,000 critically ill patients" vs. current released 50,000 | Anticipated and current-release figures kept as distinct claims, explicitly labelled. |

Additionally, the hospital count (14 contributing) is consistent across chorus4ai.org, the webinar and GitHub, and was carried without qualification; the modality count (9) is stated by chorus4ai.org and corroborated by the webinar's nine-row data-type table.

---

## 3. Audit findings and dispositions

### 3.1 Changed — unsupported attribution of tooling to the dataset

**`machine_annotation_tools` (both records) — entries removed.**
`privacy_scan_tool`, `CTP-deid` and `UF-Geocoding` appear in the bundle only as repository names in the chorus-ai GitHub organization listing. The bundle never states these were applied to the CHoRUS dataset, and `UF-Geocoding` is itself flagged as a fork of `bihorac-LAB/Exposome`. Separately, privacy scanning, de-identification and geocoding are not annotation tools; the slot description asks for automated annotation tools used in dataset creation. Retained: the **OHNLP toolkit**, which the webinar's data-type table directly ties to the dataset ("Clinical notes (extracted and tokenized using OHNLP toolkit)", OHNLP data standard, OHNLP open-source schema).

**`preprocessing_strategies` (both records) — geocoding entry removed.**
The asserted step ("geocoding of OMOP Location entities via DeGauss … supporting contextual and social-determinant variables") rests on the same repository listing. The bundle does not state this was run over CHoRUS data, nor that it produced the SDoH/contextual variables. The remaining preprocessing entries — OMOP standardization, tokenization of unstructured notes, transformation "using approaches that limit re-identification", and de-identification in process for the larger imaging cohort — are stated directly in the NIH abstract and the webinar and were retained.

### 3.2 Changed — slot mismatch

**`ethical_reviews` (both records) — slot removed.**
The slot asks for IRB approvals, ethics committee reviews and compliance certifications. The value supplied described community-facing ethics focus groups, community-perspective evaluation and legal/regulatory landscape analysis — the project's ethics *pillar*, not a review of the dataset. The bundle contains no IRB or ethics-committee determination for CHoRUS; its only IRB mention is a curriculum topic in the AIM-AHEAD training deck ("Navigating IRB, Data Compliance, and Quality Assurance in AI/ML Healthcare Research"), which concerns trainees' own future research. The ethics-pillar content is bundle-supported as project intent and is retained under `purposes`, where the NIH abstract frames it as a goal ("perform community-facing ethics focus groups to determine what data is appropriate for public sharing").

**`distribution_dates` (both records) — slot removed.**
The single entry, 2025-11-17, is the training program start date from the webinar's Key Program Dates table. It answers a neighbouring question (when a cohort begins) rather than when the dataset was or will be released. The bundle gives no dataset release or distribution date; with the entry removed the slot has no supported content and was omitted rather than left with a placeholder.

**`data_collectors` (both records) — clinical-collaborator entry relocated.**
The bundle situates clinical collaborators in the semantic-mapping and clinical-validation workflow ("Clinical expertise is invaluable to semantic mapping and validation within CHoRUS … an associated clinical validation SOP"), not in data collection. Moved to `labeling_strategies`, where mapping and validation belong. `data_collectors` retains the 14 Data Acquisition centers and the site data managers described by the Chorus_SOP workflow.

### 3.3 Changed — inference presented as evidence

**`known_biases` (both records) — slot removed.**
The record asserted a `selection_bias` arising from the 14-center composition. The bundle nowhere identifies a bias present in the dataset. It states only forward-looking intent: "Patient-focused efforts will determine the ethical and legal approaches to manage privacy and bias" and "Federated access will enable sampling methods to ensure a balanced and diverse cohort". Characterising the center composition as a known bias was the record's own analysis. Omission is the correct answer where the evidence is absent.

**`at_risk_populations` (both records) — slot removed.**
The inference that minors are among data subjects follows from PICU/NICU admissions but is not stated. More decisively, the slot asks for *protections* — safeguards and assent procedures — and the bundle documents none.

**`is_tabular` (both records) — slot removed.**
Set to `false` by inference from the presence of imaging, waveform and text modalities. The bundle makes no statement about tabularity, and the dominant OMOP component is relational. The judgment is defensible but unsupported; omitted.

**`collection_timeframes` (both records) — narrowed.**
The entry converting the award period (2022-09-01 to 2026-11-30) into a data-collection window was removed: those are NIH project start and end dates, and the bundle gives no dates for either the collection activity or the retrospective clinical-record coverage period. Retained: the "As of August 2025" state-of-collection snapshot, which the webinar states directly.

### 3.4 Changed — tense conflation

Three slots rendered future-tense design statements as realized dataset properties. Each was re-tensed to match the source, and one claim was dropped.

| Slot | Source wording | Disposition |
|---|---|---|
| `sampling_strategies` | GitHub: "Federated access **will enable** sampling methods to ensure a balanced and diverse cohort"; NIH: "sampling to ensure comprehensive sets of patient conditions" | Retained as the project's stated sampling methodology, re-worded to preserve the design framing rather than assert a realized balanced cohort. |
| `labeling_strategies` | GitHub: "A visualization and annotation environment **will label** data with targets important for prediction" | Claim of an operating annotation environment removed. Retained: OHNLP tokenization of clinical notes (stated as done) and the clinical semantic-mapping/validation workflow relocated from `data_collectors`. |
| `acquisition_methods` | NIH: the project "**will develop** capabilities … to acquire, standardize, tokenize, store, visualize, and label data" | Re-worded so that realized acquisition (retrospective extraction from EHR, PACS, bedside monitors/gateway middleware, hospital EEG database via the Chorus_SOP extract-and-upload workflow) is separated from stated future capability. |

**`direct_collection` (full record) — re-worded.**
"Data are not collected directly from individuals" is a negative claim the bundle never makes. Replaced with the supported positive statement: retrospective collection from hospital source systems at 14 contributing centers, via site-managed data extracts. (In the core record this content sits inside `acquisition_methods`; see §4.)

**`subpopulations` (both records) — entry removed.**
The fourth entry restated a variable category and a diversity aspiration ("patients characterized by social determinants of health and contextual factors such as geographic distance to the nearest hospital") without naming a subpopulation or its representation. Removed. The ICU, PICU and NICU entries, which chorus4ai.org states directly, were retained.

**`created_by` (both records) — trimmed.**
Reduced to "CHoRUS Consortium", the phrase the bundle uses ("CHoRUS Consortium … 60+ CHoRUS consortium members across 20 different institutions"). The appended project-title expansion had been assembled by the record as an attribution and was dropped; the full project title remains in `title`.

### 3.5 Changed — non-verifiable table reconstruction

**`subsets` (full) / `resources` (core) — per-modality metadata status partially removed.**
The webinar's nine-row data-type table loses column alignment in the preprocessed text: access-control and metadata values appear as an unaligned run ("Controlled Controlled Yes Yes Yes Yes … Planned Yes"). Retained for all nine modalities, because they are unambiguous in the source: modality name, data standard (OMOP, OHNLP, DICOM, WFDB, EDF+/Persyst), and `Controlled` access. Removed: the metadata / published-metadata-schema `Yes`/`Planned` assignments for **imaging, waveform telemetry and EEG**, where the reconstruction is a defensible guess at column order rather than a reading. Where the source line pairs modality and metadata status unambiguously, the value was kept.

Also retained from the bundle's directly-stated modality facts, which do not depend on the table: clinical notes stored locally except tokens; ~1,000 images currently available with de-identification in process for a larger cohort; EEG extraction in process; 7,642 admissions with radiology data; 23 Tb waveform data; 1.6 billion rows of EHR OMOP data.

---

## 4. Left as-is, with reasons

**Core/full placement divergence for the modality entries.** The nine modality objects appear under `subsets` in the full record and `resources` in the core record. The core schema (`CoreDataset`) does not expose a `subsets` slot; `resources` is the nearest available range for component partitions. The divergence is schema-driven, not a content inconsistency, and is documented here rather than forced into alignment.

**`license_and_use_terms` asymmetry between records.** The core record's `license_and_use_terms` carries the access-request contacts (`dbold@emory.edu`, `jared.houghtaling@tuftsmedicine.org`); the full record places these in `third_party_sharing` and `maintainers`. The core schema does not expose `third_party_sharing`, so folding the access route into use terms is the only way to retain a bundle-supported fact. Both placements are supported; the asymmetry is retained deliberately and recorded here.

**`total_size_bytes` omitted.** The only volumetric figure is "23 Tb Waveform data" — unit-ambiguous (Tb vs TB) and covering one modality of nine. Converting it to a dataset-wide byte count would fabricate both a unit and a scope. The figure is retained verbatim in the waveform subset description and in the dataset description, where it is attributable.

**`maintainers` contact email retained verbatim as `cmccrary@mgh.havard.edu`.** This reproduces the bundle's apparent typo ("havard"). Under the evidence boundary the source string governs; silently correcting it to `harvard.edu` would assert an address the bundle does not contain. Noted here so downstream users are aware.

**`related_datasets` omitted.** The bundle states CHoRUS "is one data generation project of four in the … Bridge2AI consortium" and is "Collaborating with Bridge2AI and 3 other data generation projects". These are sibling *projects*, unnamed, not identified datasets. `DatasetRelationship` requires `target_dataset`; no target can be named without invention. The consortium relationship is captured in `description` and `funders` instead.

**Slots correctly left unpopulated — verified during audit, no fabrication found.** `doi`, `citation`, `version`, `download_url`, `issued`, `conforms_to_schema` (dataset-level), `retention_limit`, `regulatory_restrictions`, `collection_consents`, `informed_consent`, `consent_revocations`, `collection_notifications`, `data_protection_impacts`, `participant_compensation`, `human_subject_research`, `errata`, `imputation_protocols`, `annotation_analyses`, `missing_data_documentation`, `splits`, `variables`, `use_repository`. The bundle supports none of these. No IRB determination, consent procedure, retention policy, HIPAA/GDPR compliance status, or persistent identifier was invented. Note in particular that HIPAA/GDPR appear in the bundle only as a *training curriculum topic* ("HIPAA/GDPR compliance for OMOP/FHIR data") and were not read as a compliance claim about CHoRUS.

**Retained despite being a project-level artefact:** the "under review for potential modification in compliance with Administration directives" banner from chorus4ai.org is carried in `status`, as it is the only statement in the bundle bearing on the resource's current standing.

---

## 5. Outcome

| | Full (`Dataset`) | Core (`CoreDataset`) |
|---|---|---|
| Slots populated, Phase 1/2 | 43 | 26 |
| Slots removed in Phase 4 | 5 | 5 |
| Slots re-worded or narrowed | 8 | 7 |
| Objects removed from multivalued slots | 6 | 6 |
| Objects relocated between slots | 1 | 1 |
| **Slots populated, final** | **38** | **21** |

Slots removed entirely (both records): `known_biases`, `ethical_reviews`, `distribution_dates`, `at_risk_populations`, `is_tabular`.

**Validation:** both records pass `linkml-validate` against their respective schemas and classes (`Dataset`, `CoreDataset`).

**Reconciliation outcome: reconciled.** No high-severity fabrication was present in either Phase 1 or Phase 2 output. The defect class corrected in Phase 4 is inferential over-commitment — repository listings read as applied tooling, project intent read as dataset property, award dates read as collection dates, and future-tense design read as realized state — together with three slot mismatches and one non-verifiable table reconstruction. Both records now hold a single, consistent referent, report the bundle's two internal disagreements rather than resolving them, and populate no slot beyond what the four declared sources state.