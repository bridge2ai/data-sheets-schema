# Reconciliation Report — CHoRUS D4D (full + core)

Version label: `2026-09-04f_claude-opus-5-api-generic-v8_rep3`
Records reconciled: full (`CHORUS_d4d.yaml`) and core (`CHORUS_d4d_core.yaml`)

## 1. What the audit found

The Phase 3 audit returned 22 findings against the full record, none at high severity. They clustered into five kinds:

1. **Plan or announcement stated as current state** — `labeling_strategies[0].labeling_details` (a future-tense annotation environment written in the present), `existing_uses[0].examples[1]` (the Cohort 2 training program, which had not begun at the latest bundle capture), and `acquisition_methods[0].was_validated_verified` (a boolean set from statements about mapping artifacts, not about acquired instances).
2. **Unsupported inferences** — `relationships[0].relationship_details` (instance-level linkage the bundle never describes) and `preprocessing_strategies[4].preprocessing_details` (a causal link between the geocoding tool and the abstract's "distance to the nearest hospital" example).
3. **Objects occupying a slot without answering it** — `known_biases[0]` (an intention to manage bias, not a bias) and `ethical_reviews[0].reviewing_organization` / `data_governance.committee_contact` (bodies and roles the record constructed).
4. **Unit and derivation hygiene** — the imaging instance's `counts` (an admissions figure on an imaging-study instance), the OMOP-rows instance's `counts` (a rounded figure expanded silently), `known_limitations[4]` ("roughly half" computed by the record), and `description` (a disputed figure stated flatly where it is caveated elsewhere).
5. **Low-severity tidying** — unreferenced minted creator ids, a roster-scoped caveat lodged on one entry, an email-domain-derived affiliation, duplicated access-route prose across `license_and_use_terms` and `data_governance`, access-control prose inside `distribution_formats[*].notes`, an omitted `machine_annotation_tools` entry, and an omitted `related_datasets` observation.

One finding asked for schema verification of `Organization.name`; one asked whether `related_datasets` should be added.

## 2. Changes made — full record

**Plan-as-current corrected.**
`labeling_strategies[0].labeling_details` was rewritten from "A visualization and annotation environment labels data…" to "The project states that a visualization and annotation environment **will** label data…", and a `source_caveats` was added noting that the environment is described in the future tense and that the bundle reports no labels present in the released data.

`existing_uses[0].examples` lost its second item (the Cohort 2 trainee narrative); the slot now carries only the attested "As of August 2025, the datasets are being used for training activities and publications." The training-program content was not discarded: it moved to `third_party_sharing[0].notes`, restated in the announcement's own tense ("announced for November 17, 2025 through July 31, 2026, **will** select up to 30 trainees").

`acquisition_methods[0].was_validated_verified` and its accompanying `notes` were removed; the entry now carries `acquisition_details` alone. The mapping-validation content remains in `preprocessing_strategies[0]` and `labeling_strategies[0].data_annotation_protocol`.

**Unsupported inferences removed.**
The whole `relationships` slot was deleted from the full record.
`preprocessing_strategies[4].preprocessing_details` was rewritten to state only what the repository description states — geocoding of OMOP Location entities via DeGauss using the UF-Geocoding code — dropping the claim that this supplies the distance-to-hospital element.

**Non-answering objects removed or re-scoped.**
`known_biases` was deleted in full.
`ethical_reviews[0].reviewing_organization` was removed and replaced with a `source_caveats` recording that the bundle names no review board or reviewing organization; `ethical_reviews[1].reviewing_organization` ("CHoRUS consortium") was also removed. Both `review_details` values are unchanged.
`data_governance.committee_contact` was removed entirely. The two access contacts remain, as prose, in `data_governance.access_review_process` and in `maintainers[1]`, which is where the bundle's own framing ("Request access: …") puts them.

**Unit and derivation corrected.**
`instances[8]` (the imaging entry) had its `instance_type` changed from "Radiology imaging study obtained from hospital PACS" to "Admission with radiology imaging data obtained from hospital PACS", so the unit of `counts: 7642` matches the unit of the instance; `notes` and `source_caveats` were adjusted accordingly.
`instances[1].notes` now says the integer 1600000000 "is this record's own expansion of that rounded figure, not a count reported exactly by any source".
`known_limitations[4].limitation_description` replaced "roughly half the anticipated final dataset" with "smaller than the anticipated final dataset", and a `source_caveats` was added naming the two website figures (50,000 and 100,000) as the record's own juxtaposition.
`description` now carries the webinar's competing figure ("a September 2025 training webinar instead reported over 45,000 unique admissions across 14 hospitals as of August 2025") and softens "The project also intends to sequester" to "The project also states an intention to sequester".

**Tidying.**
All six `creators[*].id` fragments were removed; the nested `principal_investigator.id` fragments are retained, since they name a distinct referent.
`creators[5].source_caveats` was removed from the Manlik Kwong entry; its content was rewritten and moved to the record-level `source_caveats`, which now also records the "four Bridge2AI data generation projects, no sibling dataset named" observation.
`license_and_use_terms.license_terms` was trimmed to the licensing-agreement requirement alone; the `.edu` and administrator-assistance text now lives only in `data_governance.access_review_process`, which absorbed it.
Access-control prose was removed from two of the five `distribution_formats[*].notes` entries — `[0]` ("held under controlled access in the cloud enclave") and `[2]` ("under controlled access"); the other three format entries are unchanged. The same prose was removed from the `notes` of the nine modality instances `instances[2]`–`instances[10]`. Those facts remain in `confidential_elements` and `regulatory_restrictions`.
`is_deidentified.method` no longer names CTP-deid or the privacy scan tool; a `source_caveats` now states that both repositories exist in the GitHub organization but that the bundle does not state either was applied to the released data. `participant_privacy[0].privacy_techniques` correspondingly dropped "Automated privacy scanning of medical records".
`sensitive_elements[1].sensitivity_details` and `other_tasks[0].task_details` were rewritten to drop the geocoding-derivation claim.
`machine_annotation_tools` was **added**, with one entry naming the OHNLP toolkit.

**Range-shape corrections made during reconciliation.** Several multivalued-looking values were emitted as YAML lists in the original where the schema digest declares them as scalars: `sampling_strategies[0].strategies`, `participant_privacy[0].privacy_techniques`, and each `external_resources[*].external_resources`. In the reconciled full record `strategies` and `privacy_techniques` are single strings; `external_resources[*].external_resources` was made a one-item list. These were shape repairs, not audit findings.

## 3. Changes made — core record

The core record was re-projected from the reconciled full record, so it carries every change above for the slots the core schema declares. Concretely: `known_biases` is absent; `creators[*].id` fragments are gone; `creators[5].source_caveats` is gone; `ethical_reviews[*].reviewing_organization` is gone; `data_governance.committee_contact` is gone; `acquisition_methods[0].was_validated_verified` and its `notes` are gone; `machine_annotation_tools` is present; `instances[8]` is the admission-unit restatement; `labeling_strategies`, `preprocessing_strategies[4]`, `cleaning_strategies`, `license_and_use_terms`, `is_deidentified`, `description`, `source_caveats`, `sampling_strategies`, `other_tasks`, `sensitive_elements[1]`, `distribution_formats`, `known_limitations[4]` and the modality `instances` notes all match the reconciled full text.

Three slots the full record carries are absent from the core record and were left absent: `direct_collection`, `splits` and `third_party_sharing`. `participant_privacy` and `relationships` are likewise not present in the core record — the former was never projected, the latter no longer exists in the full record.

The core header carries `# Phase 4 reconciliation: completed`.

## 4. Left as-is, and why

**`creators[*].affiliations[*].name` and `*.affiliation[*].name` (Organization shape).** The audit asked for schema verification because the supplied digest lists only `id`, `notes` and `source_caveats` under Organization. The `name` keys are retained in both records: `name` is a top-level slot in the inventory and the digest's per-class listings are required keys plus a partial "also accepts", not an exhaustive attribute list. The organization names are attested, and removing them would empty the objects of the structure they exist to carry. Both records validated.

**`data_governance.committee_contact.affiliation[0].name` ("Tufts Medicine").** Not handled as a separate decision — the whole `committee_contact` object was removed, so the email-domain-derived affiliation went with it.

**`related_datasets`.** Not added. The bundle names no sibling dataset, only sibling *projects*; `DatasetRelationship` requires a `target_dataset`, and there is none to name. The slot is therefore absent from both records, and the observation is recorded in the record-level `source_caveats` instead.

**`distribution_formats[4].notes`.** Compared against the original and found identical — the EDF+/Persyst entry never carried controlled-access prose, so nothing was removed there.

**`existing_uses[1]` (CHoRUSReports characterization reports).** Untouched; the audit did not question it and it is attested in the present tense.

**`instances[0].source_caveats`.** Retained unchanged; the audit's complaint was that `description` disagreed with it, which was fixed at `description`.

## Dispositions

| slot | disposition | record | reason |
|---|---|---|---|
| `labeling_strategies[0].labeling_details` | changed | both | Restated in the source's future tense. |
| `labeling_strategies[0].source_caveats` | added | both | Records that the annotation environment is a stated plan, not observed state. |
| `existing_uses[0].examples` | changed | both | Second example (Cohort 2 trainee use) removed as an unstarted program; only the attested August 2025 statement remains. |
| `third_party_sharing[0].notes` | changed | full | Absorbed the Cohort 2 program content, restated in the announcement's own future tense. The core record does not carry `third_party_sharing`. |
| `relationships` | removed | full | Instance-linkage claim not supported by the bundle. The core record did not carry it. |
| `instances[8].instance_type` | changed | both | Restated as "Admission with radiology imaging data" so the unit matches `counts: 7642`. |
| `instances[8].notes` | changed | both | Adjusted to the corrected unit. |
| `instances[8].source_caveats` | changed | both | Trimmed to the retained unit disagreement between website and webinar. |
| `instances[1].counts` | retained | both | Value kept; the derivation is now disclosed in the sibling `notes`. |
| `instances[1].notes` | changed | both | Names 1600000000 as this record's expansion of "1.6 Billion", not a source-reported exact count. |
| `instances[2].notes` | changed | both | Access-control prose removed; it answers governance, not composition. |
| `instances[3].notes` | changed | both | Same. |
| `instances[4].notes` | changed | both | Same. |
| `instances[5].notes` | changed | both | Same. |
| `instances[6].notes` | changed | both | Same. |
| `instances[7].notes` | changed | both | Same. |
| `instances[9].notes` | changed | both | Same. |
| `instances[10].notes` | changed | both | Same. |
| `instances[0].source_caveats` | retained | both | Unchanged; the disclosure inconsistency was repaired at `description`. |
| `known_biases` | removed | both | Recorded an intention to manage bias, not a bias; content already carried by `sampling_strategies` and `known_limitations`. |
| `ethical_reviews[0].reviewing_organization` | removed | both | Constructed body; the abstract names a project pillar, not a reviewing organization. |
| `ethical_reviews[0].source_caveats` | added | both | States that no IRB, ethics committee or reviewing organization is named in the bundle. |
| `ethical_reviews[1].reviewing_organization` | removed | both | Same reason; "CHoRUS consortium" is not attested as a reviewing body. |
| `data_governance.committee_contact` | removed | both | No committee is named in the bundle; the contact is an access-request contact, retained in `access_review_process` and `maintainers`. |
| `data_governance.access_review_process` | changed | both | Absorbed the `.edu` requirement and administrator-assistance text from `license_and_use_terms`. |
| `acquisition_methods[0].was_validated_verified` | removed | both | Set from statements about mapping artifacts, not about acquired instances. |
| `acquisition_methods[0].notes` | removed | both | Carried the same mapping-validation justification; content remains in `preprocessing_strategies[0]`. |
| `cleaning_strategies[0].cleaning_details` | changed | both | Dropped the unsupported "before data are accepted" acceptance gate. |
| `preprocessing_strategies[4].preprocessing_details` | changed | both | Restated to the repository description alone; the geocoding-to-distance-element link was the record's inference. |
| `is_deidentified.method` | changed | both | CTP-deid and the privacy scan tool removed as applied methods. |
| `is_deidentified.source_caveats` | changed | both | Now records that both repositories exist but are not stated to have been applied to the released data. |
| `participant_privacy[0].privacy_techniques` | changed | full | Dropped automated privacy scanning; also emitted as a scalar to match the declared range. The core record does not carry `participant_privacy`. |
| `machine_annotation_tools` | added | both | OHNLP toolkit is attested as the automated extraction and tokenization tool. |
| `license_and_use_terms.license_terms` | changed | both | Trimmed to the licensing-agreement requirement; access-route text moved to `data_governance`. |
| `creators[0].id` | removed | both | Minted fragment no value in the record points at. |
| `creators[1].id` | removed | both | Same. |
| `creators[2].id` | removed | both | Same. |
| `creators[3].id` | removed | both | Same. |
| `creators[4].id` | removed | both | Same. |
| `creators[5].id` | removed | both | Same. |
| `creators[5].source_caveats` | removed | both | Roster-scoped commentary lodged on one entry; moved to record-level `source_caveats`. |
| `creators[0].affiliations[0].name` | retained | both | `name` is a declared top-level slot; the digest's per-class list is required keys plus a partial "also accepts". The organization names are attested and both records validated. |
| `known_limitations[4].limitation_description` | changed | both | "roughly half" replaced by "smaller than"; the ratio was the record's own computation. |
| `known_limitations[4].source_caveats` | added | both | Names the two inputs (50,000 and 100,000) and states neither source gives a completion fraction. |
| `description` | changed | both | Now carries the webinar's competing admission figure and softens the holdout-set claim to a stated intention. |
| `source_caveats` | changed | both | Absorbed the creator-roster caveat and the "four data generation projects, no sibling dataset named" observation. |
| `distribution_formats[0].notes` | changed | both | Access-control prose removed; it answers governance, not format. |
| `distribution_formats[2].notes` | changed | both | Same. |
| `distribution_formats[4].notes` | retained | both | Compared against the original and found identical; it carried no access-control prose to remove. |
| `sensitive_elements[1].sensitivity_details` | changed | both | Restated to what the abstract says; geocoding-derivation claim dropped. |
| `other_tasks[0].task_details` | changed | both | Same reason. |
| `sampling_strategies[0].strategies` | changed | both | Emitted as a scalar to match the declared range; content unchanged in substance. |
| `external_resources` | changed | both | Each entry's `external_resources` emitted as a list to match the declared range; text unchanged. |
| `related_datasets` | removed | both | Audit raised the sibling-project relation as a possible addition; no `DatasetRelationship` was added and the slot is absent from both records, since the bundle names sibling projects rather than datasets and `target_dataset` is required. |
| `existing_uses[1].examples` | retained | both | Attested in the present tense; not questioned by the audit. |