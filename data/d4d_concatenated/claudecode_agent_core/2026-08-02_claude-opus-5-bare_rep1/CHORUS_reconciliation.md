# CHoRUS — D4D Reconciliation Report

**Version label:** `2026-08-02_claude-opus-5-bare_rep1`
**Arm:** BASELINE (input documents only)
**Source bundle:** `data/preprocessed/concatenated/CHORUS_preprocessed.txt` (4 documents: NIH RePORTER project 10472824; AIM-AHEAD Bridge2AI for Clinical Care Cohort 2 webinar; chorus4ai.org project documentation; chorus-ai GitHub organization overview, 2025-11-14 historical supplement)
**Records reconciled:**
- Full — `data/d4d_concatenated/claudecode_agent/2026-08-02_claude-opus-5-bare_rep1/CHORUS_d4d.yaml`
- Core — `data/d4d_concatenated/claudecode_agent_core/2026-08-02_claude-opus-5-bare_rep1/CHORUS_d4d_core.yaml`

---

## 1. Referent decision

`Dataset` admits one referent. Both records describe **the CHoRUS multimodal critical-care data resource** — the controlled-access clinical dataset assembled across the contributing hospitals — and not the NIH award `OT2OD032701`, not the `chorus-ai` GitHub software organization, and not the AIM-AHEAD Bridge2AI for Clinical Care training program.

The award, the software organization, and the training program all appear in the bundle and are represented only in the roles the schema gives them relative to the dataset: the award under `funders`, the software repositories under `external_resources` and `machine_annotation_tools`, and the training program under `existing_uses` and as the documented access route in `license_and_use_terms`. This choice is applied identically in both records.

## 2. Audit outcome at a glance

| | Full | Core |
|---|---|---|
| Slots before Phase 4 | 50 | 27 |
| Slots after Phase 4 | **46** | **28** |
| Slots removed | 5 | 3 |
| Slots added / restored | 1 | 4 |
| Slots edited in place | 9 | 7 |
| Slots renamed | 0 | 1 |
| Validates | **yes** | **yes** |

Twenty findings were raised: none high-severity, five medium, fifteen low. No fabricated entity, figure, date, licence, DOI, or citation was found. Every finding was resolved by editing or removing the affected value, except three that were deliberately left as-is and are documented in §5.

**Reconciliation outcome: resolved.** Both records validate and the paired records now agree on every fact they both carry.

---

## 3. Changes to the full record

### 3.1 Removed slots

**`relationships` — removed.** The slot declares relationships *between individual instances* (graph edges, ratings, links). The single entry, "Modality linkage to admissions," described modalities attached to one admission, which is instance composition rather than an inter-instance relationship, and generalised from the one figure the bundle actually states. The supported fact — `7,642 Admissions with Radiology Data` — is retained verbatim in `subsets`, where it already sat. Nothing evidential was lost.

**`ethical_reviews` — removed.** `EthicalReview` asks for IRB approvals, ethics-committee reviews, and compliance certifications. The bundle documents an Ethics pillar, community-facing ethics focus groups to determine what data is appropriate for public sharing, and analysis of the legal and regulatory landscape — but records no IRB or ethics-committee review of this dataset. Populating the slot with community ethics engagement answered a neighbouring field. Those activities remain where they belong, in `purposes` and `tasks`. Per the v2 rule, omission is the correct answer here rather than a pointer to adjacent work.

**`distribution_dates` — removed.** Two of the three entries carried no date at all, and the third inferred an anticipated release from the NIH award end date `2026-11-30`. The bundle states an award period, not a dataset release date. The award end date is retained under `funders`, and the August 2025 coverage snapshot is retained under `collection_timeframes`, which is the field it answers.

**`at_risk_populations` — removed.** Its only content inferred that minors are represented because PICU and NICU admissions are present. The bundle nowhere states participant ages, nowhere identifies minors as a protected population, and describes no assent procedure or minor-specific safeguard. The literal PICU/NICU fact survives unchanged in `subpopulations`.

**`conforms_to` — removed (superseded).** See §3.2.

### 3.2 Added and harmonised

**`conforms_to_schema` — added.** The core record carried this slot and the full record did not, both drawn from the same OMOP evidence. The two records now both carry `conforms_to_schema: "OMOP Common Data Model (OHDSI)"`, and the duplicate `conforms_to` was dropped from the full record so the same fact is not asserted twice under two slots. The per-modality standards (DICOM, WFDB, EDF+, Persyst, OHNLP) remain scoped to the individual entries in `file_collections`, which is where the webinar table scopes them.

### 3.3 Edits in place

**`subpopulations`** — "Adult intensive care unit admissions" → "Intensive care unit (ICU) admissions." The bundle says only "50,000 Patient admissions from ICU, PICU, and NICU." "Adult" was inferred by contrast with the paediatric and neonatal units and is not stated.

**`splits`** — tense corrected from "The dataset provisions a holdout test set" to the bundle's own forward-looking framing: the dataset *will* provision a holdout test set, accessible for model external validation, with holdout datasets *being sequestered* for that purpose.

**`machine_annotation_tools`** — "Open Health Natural Language Processing (OHNLP) toolkit" → "OHNLP toolkit." The expansion is external knowledge; the bundle uses only the acronym.

**`collection_mechanisms`** — "Picture Archiving and Communication Systems (PACS)" → "PACS." Same reason; the bundle says only "Imaging (from PACS)."

**`human_subject_research`** — the two population figures were being merged into one claim ("intensive care admissions from more than 100,000 critically ill patients"). They come from different documents in different units and are now stated separately and attributed: the NIH abstract's target of an AI-ready data set from *more than 100,000 critically ill patients*, and the project website's anticipated final dataset of *100,000 patient admissions*. Per the disagreement rule, the record represents both rather than silently selecting one.

**`funders`** — the attribution "Office of Strategic Coordination / NIH Common Fund Bridge2AI program" was trimmed to the NIH Common Fund Bridge2AI program with award `OT2OD032701` (project number `1OT2OD032701-01`, application ID `10472824`, amount `5880300`, period 2022-09-01 to 2026-11-30). The bundle links the Office of Strategic Coordination only to a named NIH staff member's affiliation on the webinar slide; the RePORTER record names no administering office.

**`cleaning_strategies`** — reduced to the one entry the field supports, restated literally: characterization reports are produced and returned to sites following their data submissions (`CHoRUSReports`). The added clause "allowing sites to identify and correct problems in their extracts" was inferred and is gone. The SOP entry was **relocated to `preprocessing_strategies`**, since the bundle describes SOPs as instructing contributing sites on best practices for curating and delivering interoperable datasets. The site status-tracking entry was **dropped**: it is project management, not a procedure applied to the data.

**`ip_restrictions`** — the sentence "The dataset itself is not distributed under an open license" was removed as an inference from the licensing-agreement requirement. The slot now states only what the bundle states: MIT and Apache-2.0 licences apply to named `chorus-ai` software repositories, explicitly scoped to software rather than to the data. The dataset-level `license` slot remains **unpopulated** — the bundle records that a licensing agreement must be signed but never names the licence.

---

## 4. Changes to the core record

**`distributions` → `file_collections` (renamed, ids restored).** `linkml-validate` rejected `distributions` as unknown on `CoreDataset`. The five modality groupings (OMOP structured EHR; tokenized clinical notes; DICOM imaging; WFDB waveform telemetry; EDF+/Persyst EEG) were re-expressed under `file_collections`, and the `id` values were restored to match the full record, which also satisfies the class's required key. This was the only validation-blocking defect found.

**`splits` — restored.** The sequestered holdout test set for external model validation is stated twice in the NIH abstract and was present in the full record but had survived in core only as prose inside `purposes` and `tasks`. It is now a first-class `splits` entry in both records, with the same forward-looking tense correction applied in §3.3.

**`direct_collection` — restored.** Indirect, retrospective collection from institutional records at the contributing hospitals, matching the full record. The webinar states "Retrospective data collection" and the extraction-and-contribution workflow; nothing justified carrying this in one record and not the other.

**`third_party_sharing` — restored.** Controlled access across all nine modalities, sharing beyond the contributing centres under a signed licensing agreement, and the AIM-AHEAD training-program access route with its registration form and `.edu` email requirement. These facts were only partially surviving via `license_and_use_terms`.

**`participant_privacy` — restored.** Tokenization of unstructured EHR text via the OHNLP toolkit, clinical notes stored locally with only tokens leaving the site, transformation using approaches that limit re-identification, de-identification in process for the larger imaging cohort, and the `privacy_scan_tool` and `CTP-deid` repositories.

**Edits mirrored from §3.3.** `ethical_reviews`, `distribution_dates`, and `at_risk_populations` were removed from core for the reasons given above. The OHNLP and PACS acronym expansions, the merged 100,000 figure, the Office of Strategic Coordination attribution, the inferred `ip_restrictions` sentence, and the `cleaning_strategies` edits were all applied identically.

---

## 5. Left as-is, with reasons

**`id` set to the project homepage URL (both records).** The bundle supplies no DOI, accession, or other persistent dataset identifier. `id` is required. Using the project homepage is the only bundle-supported URI available. This leaves `id` and `page` carrying the same string, which is not ideal, but the alternative — minting an identifier — would fabricate one. Flagged rather than changed.

**`related_datasets` omitted (both records).** The bundle states that CHoRUS is one of four Bridge2AI data generation projects and collaborates with the three others, but names none of them. `DatasetRelationship` requires `target_dataset`, and no target is identifiable from the evidence. The consortium relationship is stated in `description`, in the words the bundle uses. Omitting the typed slot is the correct answer when the relationship target is absent.

**The 45K / 50K admission-count disagreement (both records).** The webinar states "As of August 2025, covers 14 different hospitals with over 45K unique admissions"; the project website states a current released dataset of "50,000 Patient admissions from ICU, PICU, and NICU." Both figures are retained, each attributed to its source and its date, in `subsets` and `collection_timeframes`. Neither was preferred, averaged, or reconciled away. This is the disagreement rule working as intended, not a defect.

**Slots deliberately left unpopulated in both records.** `license`, `doi`, `citation`, `version`, `download_url`, `total_file_count`, `total_size_bytes` (the "23 Tb Waveform data" figure covers one modality, not the dataset, and is recorded on that `file_collections` entry instead), `collection_consents`, `consent_revocations`, `informed_consent`, `collection_notifications`, `data_protection_impacts`, `anomalies`, `content_warnings`, `known_biases`, `errata`, `variables`, `retention_limit`, `updates`, `version_access`, `imputation_protocols`, `missing_data_documentation`, `annotation_analyses`, `participant_compensation`, `regulatory_restrictions`, `prohibited_uses`, `discouraged_uses`, `future_use_impacts`, `use_repository`. In each case the bundle is silent, and an absent slot is the correct answer. Note in particular that the bundle discusses managing privacy and bias as project *aims* — it does not enumerate biases present in the data, so `known_biases` stays empty rather than being filled with the aim.

---

## 6. Post-reconciliation state

- Full record: **46 populated slots**, validates against `Dataset` in `data_sheets_schema_all.yaml`.
- Core record: **28 populated slots**, validates against `CoreDataset` in `data_sheets_schema_core_all.yaml`.
- No fact appears in one record and contradicts the other. Every fact carried by both is worded consistently.
- No prior D4D record was read or consulted at any phase. All dataset facts trace to the four documents in the declared bundle.
- Live provenance recorded via `d4d provenance record` for project `CHORUS`, method `claudecode_agent`, label `2026-08-02_claude-opus-5-bare_rep1`.