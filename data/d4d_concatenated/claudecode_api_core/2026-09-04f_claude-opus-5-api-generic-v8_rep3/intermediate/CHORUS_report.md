# Reconciliation Report — CHoRUS

## Scope

The Phase 3 audit returned 22 findings against the full record (no high severity: 12 medium, 10 low). Phase 4 applied repairs to the full record and re-projected the affected content into the core record. The comparison below is drawn from the original and reconciled records as supplied.

## Referent

Unchanged. Both records describe the CHoRUS critical care dataset assembled by the Bridge2AI CHoRUS data generation project under NIH award OT2OD032701 (`id: https://chorus4ai.org/`). The identifier, name, title and `conforms_to_*` values are the same in the original and reconciled records.

## Changes made

**Plans written as current state (findings 1, 2, and the `was_validated_verified` finding).**

- `labeling_strategies[0].labeling_details` was rewritten from "A visualization and annotation environment labels data with targets important for prediction; the project develops capabilities…" to "The project states that a visualization and annotation environment **will** label data … and that it **will** develop capabilities…", and a new `source_caveats` was added to that object noting the future tense in the award abstract and GitHub overview and that no labels in the released data are reported. Applied in both records.
- `existing_uses[0].examples` lost its second entry, the AIM-AHEAD Cohort 2 narrative. The surviving entry is the attested "As of August 2025, the datasets are being used for training activities and publications." The Cohort 2 material was not discarded: it now appears in `third_party_sharing[0].notes` in the full record, restated in announced/future tense ("its Cohort 2, announced for November 17, 2025 through July 31, 2026, will select up to 30 trainees"). Note that `third_party_sharing` is a full-record slot; the core record carries the trimmed `existing_uses` but not the relocated text.
- `acquisition_methods[0]` lost both `was_validated_verified: true` and the accompanying `notes` about validated semantic mappings. The mapping-validation content remains in `preprocessing_strategies[0]` and `labeling_strategies[0].data_annotation_protocol`. Applied in both records.

**Unsupported inferences (findings 3 and 11).**

- `relationships` was removed entirely from the full record. It was never present in the core record.
- `preprocessing_strategies[4].preprocessing_details` was rewritten from "Geocoding of OMOP Location entities via DeGauss, supporting contextual data elements such as geographic distance to the nearest hospital and other social determinants of health" to "Geocoding of OMOP Location entities via DeGauss, using the open source UF-Geocoding code maintained in the chorus-ai GitHub organization." The causal link to the abstract's contextual-factor example is gone. Applied in both records.

**Objects that did not answer their slot (findings 5 and 6).**

- `known_biases` was removed from both records. Its mitigation content was already duplicated in `sampling_strategies[0].strategies` and `known_limitations`, which are unchanged.
- `ethical_reviews[0].reviewing_organization` ("CHoRUS consortium ethics pillar (Ethical and Trustworthy AI)") was removed and replaced with a `source_caveats` stating that the bundle names no IRB, ethics committee or reviewing organization. The second entry's `reviewing_organization: CHoRUS consortium` was also removed. Both entries' `review_details` are retained unchanged. Applied in both records.

**Governance contact (findings 7 and 8).**

- `data_governance.committee_contact` was removed in full, taking the Jared Houghtaling `Person` object and the email-derived "Tufts Medicine" affiliation with it. His email remains where the bundle actually places it: inside `data_governance.access_review_process` and in `maintainers[1].maintainer_details`. Applied in both records.

**Unit inconsistency (finding 9).**

- `instances[8]` (originally listed as the radiology entry) had `instance_type` changed from "Radiology imaging study obtained from hospital PACS" to "Admission with radiology imaging data obtained from hospital PACS", so that `counts: 7642` now names the unit the website counts. Its `notes` and `source_caveats` were rephrased accordingly; both figures remain recorded. Applied in both records.

**Derived and rounded figures (findings 16 and 17).**

- `instances[1].notes` now states that the 1,600,000,000 integer "is this record's own expansion of that rounded figure, not a count reported exactly by any source," quoting the website's "1.6 Billion Rows of EHR OMOP data."
- `known_limitations[4].limitation_description` dropped "roughly half the anticipated final dataset" in favor of "smaller than the anticipated final dataset of 100,000 patient admissions", and a `source_caveats` was added naming the two website figures as the record's own juxtaposition. Applied in both records.

**Repository presence treated as applied method (finding 12).**

- `is_deidentified.method` no longer cites the privacy scan tool or CTP-deid. Those repositories are now named in `is_deidentified.source_caveats` with the explicit statement that the bundle does not say either was applied to the released data. Correspondingly, `participant_privacy[0].privacy_techniques` lost the "Automated privacy scanning of medical records" bullet (full record only; `participant_privacy` is not carried in the core record). Applied in the full record.

**Duplicated access-route text (findings 13 and 19).**

- `license_and_use_terms.license_terms` was cut back to the licensing-agreement requirement alone; the `.edu` and administrator-assistance sentences moved into `data_governance.access_review_process`, which now closes with them. Applied in both records.
- `distribution_formats[*].notes` lost the access-control clauses ("held under controlled access in the cloud enclave", "under controlled access") in entries 0, 2 and 3, and the `instances[*].notes` entries likewise dropped "controlled access". Those facts remain in `confidential_elements[1]` and `regulatory_restrictions`. Applied in both records.

**Creator hygiene (findings 15 and 16 on caveat scope).**

- All six `creators[*].id` fragments were removed. The nested `principal_investigator.id` fragments are retained, as the audit judged them correctly formed. Applied in both records.
- `creators[5].source_caveats` was removed from the entry and its content promoted, expanded, to the record-level `source_caveats`, where it now scopes the whole roster. Applied in both records.

**Omission the bundle supports (finding 12 on machine annotation).**

- `machine_annotation_tools` was added, with `tools: [OHNLP toolkit]` and a `tool_descriptions` sentence about automated extraction and tokenization of clinical notes. Applied in both records.

**Disclosure consistency (finding 18).**

- `description` now carries the webinar's competing figure inline: "a September 2025 training webinar instead reported over 45,000 unique admissions across 14 hospitals as of August 2025." The same sentence also softened "The project also intends to sequester" to "The project also states an intention to sequester". Applied in both records.

**Sibling projects (finding 21).**

- `related_datasets` was not added, since the bundle names no sibling dataset. Instead the record-level `source_caveats` now closes by stating that CHoRUS is one of four Bridge2AI data generation projects, that it collaborates with the other three, and that no sibling dataset is named, so no relationships are recorded. Applied in both records.

**Consequential edit not itemized by the audit.**

- `sensitive_elements[1].sensitivity_details` was rewritten from "derived in part from geocoded OMOP Location entities" to language attributing social determinants to the unified standards and contextual factors to what "the award abstract states data elements will feature". This follows from the same geocoding inference removed at `preprocessing_strategies[4]`. `other_tasks[0].task_details` was rewritten for the same reason, dropping the geocoding attribution.

## Left as-is

- **Finding 10, `cleaning_strategies[0].cleaning_details`.** Changed rather than retained: "before data are accepted" was removed and replaced with "site status tracking is used to identify and resolve blocking issues in the creation and curation of a site's data extract", tracking the source wording. Applied in both records.
- **Finding 20, `Organization.name`.** Left as-is. Every `Organization` object in both records still carries a `name` key — six `creators[*].affiliations[*].name`, six `principal_investigator.affiliation[*].name`, and `data_governance.accountable_organization.name`. The audit flagged this as a shape question requiring schema verification rather than a defect; the organization names are attested, and removing them would strip the objects of all content. Retained pending validation.

## Net effect

Full record: `relationships` and `known_biases` removed; `machine_annotation_tools` added; edits within `description`, `creators`, `instances`, `acquisition_methods`, `preprocessing_strategies`, `cleaning_strategies`, `labeling_strategies`, `is_deidentified`, `sensitive_elements`, `participant_privacy`, `ethical_reviews`, `known_limitations`, `license_and_use_terms`, `data_governance`, `distribution_formats`, `third_party_sharing`, `existing_uses`, `other_tasks` and record-level `source_caveats`.

Core record: same removals and addition where the core schema declares the slot; `participant_privacy` and `third_party_sharing` edits have no core counterpart because those slots are not carried in the core record.

## Dispositions

| slot | disposition | record | reason |
|---|---|---|---|
| `relationships` | removed | full | Inter-instance linkage at admission level is not stated by any source; the bundle reports counts only. Not present in core. |
| `known_biases` | removed | both | The single entry recorded an intention to manage bias, not a bias; mitigation content already carried by `sampling_strategies` and `known_limitations`. |
| `machine_annotation_tools` | added | both | The OHNLP toolkit is attested as the automated tool extracting and tokenizing clinical notes; previously carried only as prose in other slots. |
| `labeling_strategies[0].labeling_details` | changed | both | Restated in the future tense the sources use; the annotation environment is a project aim, not a current capability. |
| `labeling_strategies[0].source_caveats` | added | both | Records that the annotation environment is described prospectively and that no labels in released data are reported. |
| `existing_uses[0].examples` | changed | both | The Cohort 2 example was removed as an unstarted program; the attested training-and-publications example remains. |
| `third_party_sharing[0].notes` | changed | full | Cohort 2 relocated here and restated in announced/future tense. Slot not carried in core. |
| `acquisition_methods[0].was_validated_verified` | removed | both | Validation statements concern mapping artifacts, not verification of acquired instances. |
| `acquisition_methods[0].notes` | removed | both | Removed with the boolean it supported; mapping validation retained in `preprocessing_strategies[0]` and `labeling_strategies[0].data_annotation_protocol`. |
| `preprocessing_strategies[4].preprocessing_details` | changed | both | Dropped the inferred link between DeGauss geocoding and the abstract's distance-to-hospital element. |
| `sensitive_elements[1].sensitivity_details` | changed | both | Consequential to the geocoding repair; contextual factors now attributed to the award abstract's own framing. |
| `other_tasks[0].task_details` | changed | both | Consequential to the geocoding repair; geocoding attribution removed. |
| `ethical_reviews[0].reviewing_organization` | removed | both | "CHoRUS consortium ethics pillar" is a body constructed by the record from a project pillar name. |
| `ethical_reviews[1].reviewing_organization` | removed | both | Same reason; no reviewing organization is named in the bundle. |
| `ethical_reviews[0].source_caveats` | added | both | States that no IRB, ethics committee or reviewing organization is named for the dataset. |
| `data_governance.committee_contact` | removed | both | No committee is named in the bundle; Houghtaling is attested only as an access-request contact. |
| `data_governance.access_review_process` | changed | both | Absorbed the `.edu` requirement and administrator-assistance sentences from `license_and_use_terms`. |
| `license_and_use_terms.license_terms` | changed | both | Reduced to the licensing-agreement requirement; access-route text moved to `data_governance`. |
| `instances[8].instance_type` | changed | both | Restated as an admission-with-radiology unit so that `counts: 7642` matches the unit the website counts. |
| `instances[8].notes` | changed | both | Rephrased for the corrected unit; access-control clause removed as duplicative. |
| `instances[8].source_caveats` | changed | both | Rephrased for the corrected unit; both source figures retained. |
| `instances[1].notes` | changed | both | Annotates 1,600,000,000 as this record's expansion of the website's rounded "1.6 Billion". |
| `instances[2..7,9,10].notes` | changed | both | "Controlled access" clauses removed as duplicative of `confidential_elements` and `regulatory_restrictions`. |
| `known_limitations[4].limitation_description` | changed | both | "Roughly half" replaced by a plain comparison of the two stated figures. |
| `known_limitations[4].source_caveats` | added | both | Names the comparison as the record's own juxtaposition of 50,000 and 100,000. |
| `is_deidentified.method` | changed | both | Privacy scan tool and CTP-deid removed; repository presence is not evidence of an applied method. |
| `is_deidentified.source_caveats` | changed | both | Now names those repositories and states the bundle does not say either was applied. |
| `participant_privacy[0].privacy_techniques` | changed | full | "Automated privacy scanning" bullet removed for the same reason. Slot not carried in core. |
| `cleaning_strategies[0].cleaning_details` | changed | both | "Before data are accepted" removed; no acceptance gate is stated by any source. |
| `distribution_formats[0].notes` | changed | both | Access-control clause removed as duplicative of the governance and regulatory slots. |
| `distribution_formats[2].notes` | changed | both | Same reason. |
| `distribution_formats[3].notes` | changed | both | Same reason. |
| `creators[0..5].id` | removed | both | Minted fragments that no value in either record points at; unreferenced identifiers are noise, not labels. |
| `creators[5].source_caveats` | removed | both | Roster-scoped commentary lodged on one entry; promoted to record-level `source_caveats`. |
| `description` | changed | both | Now discloses the webinar's competing admission figure inline, matching the caveat at `instances[0]`; holdout softened to a stated intention. |
| `source_caveats` | changed | both | Absorbed the roster caveat and added the statement about the four Bridge2AI data generation projects and the absence of named sibling datasets. |
| `related_datasets` | retained | full | Not added: the bundle names sibling projects, not sibling datasets. The relation is now recorded in record-level `source_caveats`. Slot absent from both records. |
| `creators[0].affiliations[0].name` | retained | both | Organization names are attested; the audit raised a shape question, not a factual defect. Retained pending schema validation. |
| `data_governance.accountable_organization.name` | retained | both | Same reason. |