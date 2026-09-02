# Reconciliation Report — CHoRUS

Project: CHORUS · Label: `2026-09-01_claude-opus-5-api-generic-v7_rep1` · Arm: BASELINE (input documents only)

Records compared: the original full record and original core record against the reconciled full record and completed core record, both supplied above.

---

## 1. Scope and method

Phase 3 returned 38 findings against the full record (7 high, 31 medium). Phase 4 applied changes to the full record where the declared bundle supported a different value, a different placement, or an omission, and then re-projected the core record so that every shared slot carries the reconciled wording. The core record is a projection: no fact appears in it that is not in the reconciled full record.

Dataset referent: the record describes **the CHoRUS dataset** — the multicenter, multimodal, controlled-access collection of acute and critical care hospital admissions — and not the CHoRUS project, the CHoRUS GitHub software organization, or the AIM-AHEAD training program. This choice was held consistently across both records. Where the bundle describes the project or the software (award period, MIT/Apache repository licensing, training-program curriculum), those facts were either recorded as context on the dataset or explicitly marked as governing something other than the data.

---

## 2. Changes made

### 2.1 Identity

**`id` (high).** The audit found `id` and `page` both set to `https://chorus4ai.org/`, collapsing the dataset and the website into one entity. Changed to `https://chorus4ai.org/#dataset` in both records; `page` retains `https://chorus4ai.org/`. The fragment is minted on an attested project URL, which is the permitted case: the thing named is a part of this record's subject and has no external identifier in the bundle.

### 2.2 Values not supported by the bundle

**`language` (medium).** `language: en` was removed from both records. The bundle states nothing about the language of the dataset content; the webinar's "Working command of English" is a trainee eligibility requirement. The top-level `source_caveats` now records that the bundle does not state the language of the dataset content.

**`creators[].credit_roles` (medium).** `project_administration` and `supervision` were removed from the Rosenthal entry. The bundle states only that he is principal investigator; CRediT roles were inferred from that title.

**`at_risk_populations` (high).** The whole slot, including `at_risk_groups_included: true`, was removed from both records. The bundle names PICU and NICU admissions but never characterizes any group as an at-risk population, and the original object's own caveat conceded the inference. The PICU/NICU fact survives in `human_subject_research.special_populations` and in `subpopulations`, where it is descriptive rather than a protection claim.

**`is_deidentified.identifiable_elements_present` (medium).** The boolean `true` was removed. `method` and `deidentification_details` are unchanged, and a new `source_caveats` on the object records that the bundle documents de-identification activity without stating whether identifiable elements remain in the release.

**`participant_privacy` — "clinical trials processor" (medium).** The expansion of the CTP-deid acronym was removed; the entry now reads "A de-identification component maintained in the CTP-deid repository," with a new `source_caveats` noting the repository carries no description in the bundle.

**`preprocessing_strategies` — DeGauss (medium).** The composed causal claim that geocoding allows distance-to-nearest-hospital to be attached to records was removed. The entry now records what the bundle states: UF-Geocoding geocodes OMOP Location entities via DeGauss, and it is a fork of `bihorac-LAB/Exposome`, which the original omitted.

**`known_limitations` — "in the United States" (medium).** Removed from the representativeness entry, which now reads "14 hospitals drawn from the 20 academic centers in the collaboration."

**`collection_timeframes` (medium).** The original equated the award period with the collection window. The wording was revised and a `source_caveats` added stating that 2022-09-01 to 2026-11-30 is the NIH project period, not the temporal coverage of the clinical data, and that retrospective extraction means the admissions likely predate the award. `start_date` and `end_date` remain unpopulated.

**`acquisition_methods` — clinical notes (medium).** `was_inferred_derived: true` was replaced with `was_directly_observed: true`; tokenization is a transformation of directly observed documentation, and it remains described in `acquisition_details` and in `preprocessing_strategies`.

**`description` — tense (medium).** "within a collaboration spanning 20 academic centers and more than 60 consortium members" was rewritten to "among the 20 academic centers in the collaboration, whose membership is given as more than 60 consortium members," removing the present-tense rendering of a future-tense GitHub claim about which centers will contribute.

### 2.3 Structure — evidence moved into the fields that declare it

**`creators` (high).** The single Creator object was expanded to six, one per leadership-team member named in the webinar: Rosenthal (Massachusetts General Hospital), Bihorac (University of Florida), Jiang (UTHealth Houston), Strekalova (University of Florida), Rashidi (University of Florida), Kwong (Tufts University). Each carries its own `affiliations` and its own `source_caveats` recording that the bundle does not state the person's role with respect to dataset creation. The five formerly buried in prose are now distinct entities in both records.

Note on shape: `principal_investigator` now carries a scalar name string in each entry rather than a nested object, matching the scalar-reference rule.

**`funders.grants` (high).** The declared `grants: Grant[]` field was populated with a Grant object (`id: https://reporter.nih.gov/project-details/10472824`, `name: OT2OD032701`). `notes` retains the project number, application ID, awardee, fiscal year, amount, and project period, which the Grant class has no declared field for. `grantor` was narrowed from "National Institutes of Health (NIH) Common Fund, Bridge2AI program" to "National Institutes of Health (NIH) Common Fund," with the Bridge2AI program moved into `notes`.

**`data_governance.committee_contact` (high).** Populated with `Jared Houghtaling`, attested in the GitHub README as one of two access-request addresses. A `source_caveats` on the object records that the bundle names no access committee, no membership, no decision timeframe and no appeal process, and does not state that he chairs or sits on any body — so `committee_name` and `committee_members` remain unpopulated.

**`data_governance.access_review_process` (medium).** The single fused paragraph was restructured to label the two distinct routes explicitly ("General route:" / "Training-program route:"), so a general researcher is not read as required to complete the training-program registration form.

**`license_and_use_terms` (medium).** The MIT and Apache-2.0 licenses were moved out of `license_terms` into a `notes` field that states they govern the CHoRUS software repositories and not the dataset. `license_terms` now covers only the controlled-access data terms. `data_use_permission` remains unpopulated — no enum value maps cleanly to a signed-agreement-plus-`.edu` requirement.

**`external_resources` (medium).** The four objects, each wrapping a one-item list, were consolidated into a single object with four entries. The `www.bridge2ai.org/chorus` entry now states explicitly that it is recorded as written in the source, without a URL scheme.

**`maintainers` (medium).** `role: academic_institution` was added to the second entry (the access-request contacts) for consistency with the first. The third entry, which describes the package status page rather than an organization, was left without a role.

### 2.4 Slot values reshaped

**`status` (medium).** The composed sentence "Partially released under controlled access, with an anticipated final dataset still in preparation" was replaced with the token `partially released`. The substance it carried is already in `description`, `updates`, `license_and_use_terms`, and `known_limitations`.

**`keywords` (medium).** Composed paraphrases were replaced with terms the bundle uses: "intensive care unit" → "critical illness"; "electronic health records" → "electronic health record"; "medical imaging" → "imaging"; "multimodal data" → "multimodality"; "AI-ready dataset" → "AI-ready data set". "critical care", "acute illness", "OMOP Common Data Model", "waveform telemetry", "electroencephalography", "clinical notes", "social determinants of health" and "Bridge2AI" were retained.

**`instances[0].data_substrate` (medium).** `B2AI_SUBSTRATE:37` (Relational Database) was removed from the patient-admission instance, where an admission is the unit of observation rather than a storage form. It was retained on the OMOP-row instance, where it fits.

**`sampling_strategies[].strategies` and `participant_privacy[].privacy_techniques` (shape).** Converted from YAML lists to single strings, matching the scalar ranges those fields declare.

### 2.5 Conflicting figures moved to the values they qualify

**`instances` — 50,000 vs 45K (high)** and **7,642 vs 1000 images (high).** Both instance objects now carry their own `source_caveats` naming both figures, their sources, and which was preferred (tier 2, `project_documentation`). The top-level `source_caveats` retains the overall statement and now adds that the conflict is also recorded on the individual values it affects.

**`known_limitations` — imaging inconsistency (high).** The coverage entry was rewritten so it attributes the 1000-image figure to the cohort 2 webinar's August 2025 snapshot and states alongside it that the project website reports 7,642 admissions with radiology data. A reader of `known_limitations` alone no longer sees a bare contradiction of `instances`.

### 2.6 Content added

**`known_biases` (medium).** The slot, omitted in the original, was added with one `DatasetBias` entry: `bias_type: representation_bias`, describing the project's treatment of cohort balance and diversity as a managed risk, with `mitigation_strategy` recording the federated-access sampling methods and sampling at scale.

**`notes` — funding statement and typo flag (medium).** The chorus4ai.org funding/disclaimer statement was added verbatim. The "repoitory" misspelling in the banner is now explicitly flagged as reproduced as published, matching the treatment of the "mgh.havard.edu" typo.

**`source_caveats` — enum collapse (high).** The top-level caveat now records that a single `OTHER` term stands for three distinct standards the registered enum does not cover (EDF+, Persyst, OHNLP open source schema), and that the WFDB entry covers a schema the source describes as extended. The enum list itself is unchanged; the qualification is now stated rather than only implied by `conforms_to`.

**`conforms_to` and `distribution_formats` (high).** "a PhysioNet schema, extended" was rewritten as "described in the source as a PhysioNet schema extended," attributing the characterization to the source.

**`existing_uses` (medium).** The trainee poster/abstract/manuscript example was removed from `existing_uses`, where it described planned outputs rather than existing uses, and folded into `intended_uses` under "Training and workforce development in clinical AI." The remaining Cohort 2 example was reworded to drop "develop use cases" in favor of the source's "conduct innovative research."

**`human_subject_research.source_caveats` (high).** Rewritten so the 100,000-patient figure is explicitly identified as the anticipated scale from the NIH abstract rather than a count of data collected.

---

## 3. Findings left as-is

**`created_by` (medium).** Left as `CHoRUS Consortium`. The string is attested on chorus4ai.org, and no source states who created the dataset in other terms. `data_governance.accountable_organization` continues to name Massachusetts General Hospital, which is a different claim.

**`ethical_reviews` — organization names (high).** The two invented `reviewing_organization` values were changed to `CHoRUS consortium` in both entries, and each entry gained a `source_caveats` stating that the content describes ethics activity rather than formal review, and that the bundle names no IRB, ethics committee, or approval identifier. The audit's alternative — that this may be the wrong slot entirely — was not acted on: the slot's description covers "ethics committee reviews" broadly, and moving community ethics work elsewhere would lose it. The caveat carries the qualification instead.

**`instances` — EEG `data_topic` (medium).** `B2AI_TOPIC:37` (Waveform) was retained for the EEG instance. The source's own heading is "Waveform EEG (hospital database)," so the term matches the source's characterization; the audit flagged this as low-confidence either way.

**`distribution_formats` — thin entries (medium).** No `media_type`, `access_urls` or `download_url` was added. The bundle states none, and the access route correctly stays in `data_governance`.

**`license` (medium).** Still omitted. The data carry no named license; writing MIT would misattribute the software license to the data. The omission is now explained in `license_and_use_terms.notes`.

**`collection_consents`, `discouraged_uses` (medium).** Still omitted. The bundle documents no patient consent process and no statement of discouraged use.

**`citation`, `version`, `doi`, `issued`, `distribution_dates` (medium).** Still omitted, consistent with the top-level caveat. The funding/disclaimer statement, which the audit noted was carried nowhere, is now in `notes` rather than in `citation` — it is an acknowledgment, not a recommended citation.

**`total_file_count`, `total_size_bytes`, `file_collections` (medium).** Still omitted. "23 Tb" covers one modality and its unit is ambiguous in the source; the figure remains in `instances[].notes` and in `description`.

**`splits` — no fragment identifier (medium).** The holdout test set remains prose in `splits`. No value in either record points at it structurally; under the v6 rule a part nothing points at is described, not labeled.

**`instances` — 23 Tb duplication (medium).** Retained in both `description` and the instance's `notes`. The Instance class declares no size field, and the description is a standalone summary; the duplication is redundant rather than wrong.

---

## 4. Outcome

| | Original | Reconciled |
|---|---|---|
| Full record — populated top-level slots | 47 | 47 |
| Core record — populated slots | 46 | 45 |

Slot counts are near-identical because the reconciliation was mostly redistribution rather than addition or deletion: `at_risk_populations` and `language` were removed, `known_biases` was added. The substantive change is in what the populated slots hold — six Creator objects rather than one, a populated `grants` field, a populated `committee_contact`, per-value conflict caveats on the two disputed counts, and eight inferred values withdrawn.

Both records validate against their declared schemas (`Dataset` and `CoreDataset` respectively). The core record carries the required `# Sources:` line and `# Phase 4 reconciliation: completed`. No previously generated D4D record was consulted at any phase.