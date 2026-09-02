# CHoRUS D4D Reconciliation Report

**Project:** CHORUS (CHoRUS — Bridge2AI AI/ML for Clinical Care Grand Challenge)
**Label:** 2026-09-01_claude-opus-5-api-generic-v7_rep1
**Arm:** BASELINE (input documents only)
**Bundle:** `data/preprocessed/concatenated/CHORUS_preprocessed.txt` (md5 9b2ef4b65d67957f79362266cab0bc7a)
**Phase:** 4 — strict reconciliation of Phase 1 (full) and Phase 2 (core) against the Phase 3 audit

---

## 1. Referent

The `Dataset` referent held across both records is **the CHoRUS dataset** — the multicenter, multimodal, controlled-access collection of acute and critical care hospital admissions assembled by the CHoRUS Network under NIH award OT2OD032701 — and *not* the CHoRUS project, the chorus-ai software organization, or the AIM-AHEAD training program. That choice was made in Phase 1 and is unchanged in Phase 4. Two reconciliation edits sharpen it: the dataset identifier is now distinct from the website identifier, and the MIT/Apache software licenses have been moved out of the dataset's license terms.

---

## 2. Audit findings and their disposition

### 2.1 Findings acted on — high severity

**`id` duplicated `page` (full + core).**
Both records set `id: https://chorus4ai.org/` and `page: https://chorus4ai.org/`, asserting one identity for the dataset and the project website. Changed in both records to `id: https://chorus4ai.org/#dataset`, a fragment minted on the attested project URL; `page` retains `https://chorus4ai.org/` unchanged. This is the minting case the v5/v6 rules permit — a label for a part of this record with no external referent, anchored to an attested URI.

**`creators` collapsed six attested people into one object (full + core).**
The original emitted a single `Creator` for Eric S. Rosenthal and relegated Azra Bihorac, Xiaoqian Jiang, Yulia Strekalova, Parisa Rashidi, and Manlik Kwong to a `source_caveats` prose string. Both records now carry **six** `Creator` objects, each with `principal_investigator.name` and `affiliations[].name` exactly as the cohort 2 webinar's Bridge2AI CHoRUS Leadership Team slide gives them (MGH; University of Florida; UTHealth Houston; University of Florida; University of Florida; Tufts University), each with its own `source_caveats` noting that the bundle does not state the person's role with respect to dataset creation.

**`funders` left the declared `grants` field empty (full + core).**
Every grant identifier sat in free-text `notes`. Both records now populate `grants` with one `Grant` object (`id: https://reporter.nih.gov/project-details/10472824`, `name: OT2OD032701`). The `notes` field is retained and still carries the project number, application ID, awardee, fiscal year, award amount, and project period, which the `Grant` range does not expose as declared keys here.

**`conforms_to_standard`: one `OTHER` for three standards, and WFDB-as-extended unflagged (full + core).**
The enum list is unchanged (`OMOP_CDM`, `DICOM`, `WFDB`, `OTHER`) because the registered enum offers no term for EDF+, Persyst, or the OHNLP schema and repeating `OTHER` would not distinguish them. What changed is disclosure: the top-level `source_caveats` in both records now states that the single `OTHER` stands for three distinct standards and that the WFDB entry covers a schema the source describes as extended. The `conforms_to` prose was also reworded from "WFDB (a PhysioNet schema, extended)" to "WFDB, described in the source as a PhysioNet schema extended," attributing the qualification to the source rather than asserting it.

**`instances`: disputed counts carried no local caveat (full + core).**
The 50,000-admission and 7,642-radiology-admission figures now each carry their own `source_caveats` on the instance object, naming the tier-2 value used, the tier-4 webinar's competing figure (over 45K admissions; 1000 images), and — for imaging — that the units differ. The top-level `source_caveats` retains the same explanation and now adds that the conflict is also recorded on the values it affects.

**`known_limitations` contradicted `instances` on imaging (full + core).**
The coverage_limitation entry asserted "imaging was limited to 1000 images" flatly. Rewritten in both records to attribute the 1000-image figure to the cohort 2 webinar's August 2025 snapshot and to state, in the same entry, that "The project website separately reports 7,642 admissions with radiology data in the current released dataset." A reader of `known_limitations` alone now sees both figures.

**`data_governance` left Person-ranged and committee fields empty (full + core).**
`committee_contact` is now populated with a `Person` object naming Jared Houghtaling, attested in the chorus-ai README as one of two access-request addresses. `committee_name` and `committee_members` remain empty — the bundle names no committee — and a new `source_caveats` on the object states exactly that, and states that the bundle does not say Houghtaling chairs or sits on any access body.

**`ethical_reviews` invented two organization names (full + core).**
`reviewing_organization` read "CHoRUS consortium Ethics pillar (Ethical and Trustworthy AI)" and "CHoRUS consortium legal and ethics workstream." Neither string appears in the bundle. Both entries now read `reviewing_organization: CHoRUS consortium`, an attested name. The first entry's `review_details` absorbs the pillar description as a quotation from the NIH abstract ("Ethics (Ethical and Trustworthy AI)"). Both entries gain `source_caveats` recording that this is ethics activity rather than ethics review, and that the bundle names no IRB, ethics committee, or approval identifier.

**`human_subject_research.source_caveats` read as if 100,000 described collected data (full + core).**
Rewritten in both records to state that the NIH abstract's "more than 100,000 critically ill patients" is the anticipated scale rather than a count of data already collected.

### 2.2 Findings acted on — medium severity

**`language: en` unsupported.** Removed from both records. The only English-related evidence is a trainee eligibility requirement, which is not a statement about dataset content. The top-level `source_caveats` in both records now notes that the bundle does not state the language of the dataset content.

**`status` carried a composed sentence.** Changed in both records from "Partially released under controlled access, with an anticipated final dataset still in preparation" to `partially released`, a token in the form the slot description asks for. The substance it carried remains in `description`, `updates`, and `license_and_use_terms`.

**`keywords` mixed composed paraphrases with source terms.** Both records now use terms as the sources write them: `critical illness` and `electronic health record` and `imaging` and `multimodality` and `AI-ready data set` replace `intensive care unit`, `electronic health records`, `medical imaging`, `multimodal data`, and `AI-ready dataset`. `acute illness`, `critical care`, `OMOP Common Data Model`, `waveform telemetry`, `electroencephalography`, `clinical notes`, `social determinants of health`, and `Bridge2AI` are unchanged.

**`creators.credit_roles` inferred from the PI title.** `credit_roles: [project_administration, supervision]` removed from the Rosenthal entry in both records; no other Creator carries the slot.

**`at_risk_populations.at_risk_groups_included: true` inferred.** The entire `at_risk_populations` slot has been removed from both records. The boolean rested on inference from ward names, and the object carried no other populated field beyond the caveat conceding the inference. The PICU/NICU fact it rested on survives in `human_subject_research.special_populations` and in `subpopulations`.

**`is_deidentified.identifiable_elements_present: true` stronger than evidence.** The boolean is removed in both records; `method` and `deidentification_details` are unchanged, and a new `source_caveats` states that the bundle documents de-identification activity but does not say whether identifiable elements remain in the release.

**"clinical trials processor" expanded an acronym the bundle never expands.** The `participant_privacy` technique now reads "A de-identification component maintained in the CTP-deid repository," and a new `source_caveats` on the object records that the repository is listed without a description.

**DeGauss causal join.** The preprocessing entry no longer asserts that geocoding allows distance-to-hospital to be attached to records. It now reads that OMOP Location entities are geocoded via DeGauss using the open source UF-Geocoding code, "a fork of bihorac-LAB/Exposome maintained in the chorus-ai GitHub organization" — adding the fork provenance the audit noted was missing.

**`license_and_use_terms` mixed software and data licenses.** `license_terms` in both records now covers only the controlled-access data terms. The MIT and Apache-2.0 statements move to a new `notes` field on the object, which states explicitly that they govern the CHoRUS software repositories and not the dataset.

**`collection_timeframes` conflated award period with clinical coverage.** `timeframe_details` now says data collection "is described as retrospective and is carried out over the NIH award period," and a new `source_caveats` states that these are project dates, not the clinical period the admissions are drawn from, and that the bundle does not give the data's temporal coverage.

**"in the United States" for the 14 hospitals.** Removed from the representativeness_limitation in both records, which now reads "14 hospitals drawn from the 20 academic centers in the collaboration."

**`known_biases` omitted despite supporting evidence.** Added to both records: one `DatasetBias` with `bias_type: representation_bias`, a description drawn from the privacy-and-bias management language and the diversity goal, and `mitigation_strategy` citing federated access enabling sampling for a balanced and diverse cohort.

**`acquisition_methods` clinical-notes entry set `was_inferred_derived: true`.** Changed in both records to `was_directly_observed: true`, with the tokenization retained in `acquisition_details`; the notes are provider documentation, and tokenization is a transformation rather than inference.

**Site-banner typo inconsistently flagged.** The full record's `notes` now states that the misspelling of "repository" is reproduced as published, matching the treatment already given to the "mgh.havard.edu" typo. Same change in core.

**Funding acknowledgment not carried anywhere.** The chorus4ai.org NIH funding/disclaimer statement is now quoted in `notes` in both records. `citation` remains omitted — the statement is an acknowledgment, not a recommended citation.

**`funders.grantor` conflated agency and program.** `grantor` now reads `National Institutes of Health (NIH) Common Fund`; the Bridge2AI program attribution moves to `notes`.

**`existing_uses` second entry mixed uses with planned trainee outputs.** The poster/abstract/manuscript example has been removed from `existing_uses` in both records; that material now appears in `intended_uses` under "Training and workforce development in clinical AI," where planned outputs belong. The remaining training-program example was reworded to "conduct research on the Bridge2AI Clinical Care Cloud platform."

**`external_resources` nested four single-item lists.** Collapsed in both records to a single `ExternalResource` object with four entries in its `external_resources` list. The scheme-less `www.bridge2ai.org/chorus` string is retained with an inline note that it is recorded as written in the source, without a URL scheme.

**`description`: future-tense GitHub claim rendered as present fact.** The phrase "within a collaboration spanning 20 academic centers and more than 60 consortium members" is now "among the 20 academic centers in the collaboration, whose membership is given as more than 60 consortium members," avoiding asserting that all 14 contribute presently in the GitHub sense.

**`data_governance.access_review_process` fused two access routes.** Rewritten in both records to label them separately — "General route:" and "Training-program route:" — and the ".edu" requirement is now scoped to the training-program route rather than stated as a blanket condition.

**`maintainers` inconsistent `role`.** The second entry (access-request contacts) now carries `role: academic_institution`, matching the first. The third (software package status page) still omits `role`; the bundle attributes it to no institution.

### 2.3 Findings acted on — instance substrate approximations

**`data_substrate: B2AI_SUBSTRATE:37` on the patient-admission instance.** Removed from that instance in both records; an admission is a unit of observation, not a storage form. Retained on the OMOP-row instance, where relational database is a defensible reading of the OMOP CDM.

**`data_topic: B2AI_TOPIC:37` on the EEG instance.** Left as-is. The audit itself rated this low-confidence and offered no clearly better term; the bundle labels the modality "Waveform EEG," which the Waveform topic fits directly.

### 2.4 Findings left as-is

- **`instances` waveform `notes` duplicating `description` (23 Tb).** Retained. `Instance` declares no size field, so `notes` is the correct residual location, and the audit graded the duplication as redundant rather than wrong. The wording was softened to "is reported as 23 Tb."
- **`distribution_formats` thin; no `media_type`, `access_urls`, `download_url`.** Unchanged. The audit concluded the omissions are correct — the bundle states no media types and the access route belongs in `data_governance`, where it sits.
- **`license` (top-level) omitted.** Unchanged. Recording MIT would misattribute the software license to the data; no data license is named.
- **`collection_consents`, `discouraged_uses`, `prohibited_uses` omitted.** Unchanged. The bundle documents no consent process and no discouraged or forbidden uses.
- **`total_file_count`, `total_size_bytes`, `file_collections` omitted.** Unchanged. The 23 Tb figure covers one modality and its unit is ambiguous in the source.
- **`version`, `doi`, `issued`, `distribution_dates`, `citation` omitted.** Unchanged, and consistent with the top-level `source_caveats`, which continues to state the bundle supplies none of these.
- **`splits` holdout set without a minted fragment.** Unchanged. Nothing in either record points at the holdout set by identifier; the references in `tasks` and `intended_uses` are textual. Under the v6 rule, a part nothing points at is described, not labeled.

---

## 3. Core record

The core record is a projection of the reconciled full record. Every change above is present in both files; no fact appears in core that is absent from full. The core header carries `# Sources:` naming the full record path and `# Phase 4 reconciliation: completed`. `conforms_to_class: CoreDataset` and `conforms_to_schema: src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml` distinguish the core record from the full one, which carries `Dataset` and the w3id schema URI.

---

## 4. Outcome

| | Full | Core |
|---|---|---|
| Top-level slots populated | 48 | 47 |
| Slots removed in reconciliation | `language`, `at_risk_populations` | `language`, `at_risk_populations` |
| Slots added in reconciliation | `known_biases` | `known_biases` |
| Validation | passed (`Dataset`) | passed (`CoreDataset`) |

Reconciliation outcome: **all high-severity findings resolved**; all medium-severity findings either resolved or explicitly retained with reasons recorded above; two findings (EEG topic term, waveform size note) left as-is on the audit's own low-confidence grading. Provenance recorded via `d4d provenance record`.