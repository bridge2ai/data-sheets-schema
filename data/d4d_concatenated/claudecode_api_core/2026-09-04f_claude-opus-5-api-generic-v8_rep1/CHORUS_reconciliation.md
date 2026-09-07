# CHoRUS D4D Reconciliation Report

Version label: `2026-09-04f_claude-opus-5-api-generic-v8_rep1`
Records reconciled: full (`CHORUS_d4d.yaml`) and core (`CHORUS_d4d_core.yaml`)
Referent held constant across both records: the CHoRUS dataset itself — the multicenter, multimodal, controlled-access critical care dataset assembled by the CHoRUS data generation project — not the project, not the GitHub software organization, and not the AIM-AHEAD training program that provides one access route to it.

## What the audit found

The Phase 3 audit returned thirteen findings, none critical: four medium and nine low. Two were substantive content defects (`distribution_formats` carrying an access route in `format` and collapsing five per-modality formats into one entry; an `existing_uses` example that presented the prospective AIM-AHEAD cohort-2 program as a current use). Three were absence statements embedded in fields that should answer the question. One was an unsupported enum value. The remainder were shape and hygiene items: an over-long `status`, inconsistent Creator modeling, gratuitous minted identifiers, two multivalency risks, and one unmarked inference.

The audit also confirmed several things as correct, and those were left untouched: the handling of the 50,000 versus 45K admissions conflict and the 7,642-admissions versus 1000-images imaging counts (higher-ranked source preferred, both figures reported, disagreement recorded in `source_caveats`); the withholding of the MIT license from any dataset-level `license` slot, since the MIT statement is made about the GitHub code; the absence of any external registry identifier the bundle does not state; and the absence of prior-D4D reuse.

## What was changed, and why

### `distribution_formats` — rebuilt as five entries (both records)

The original carried a single entry with `format: Controlled-access cloud enclave`. That is the access route, not a distribution format, and the slot's declared range asks for one object per distinct format. The webinar's data-inventory table pairs each modality with a data standard. The reconciled records carry five entries, with `format` set to `OMOP Common Data Model`, `OHNLP`, `DICOM`, `WFDB`, and `EDF+ and Persyst` respectively. The enclave, Azure, Jupyter Notebook and OHDSI tool stack material was not discarded — it was moved into the `notes` of the OMOP and WFDB entries, which are the two modalities the bundle places inside the enclave. The training-program access route was already carried in `data_governance.access_review_process` and remains there unchanged; nothing was duplicated into a second location.

### `existing_uses[0].examples` — cohort-2 example removed (both records)

The original listed two examples. The second stated that cohort 2 "uses the data for hands-on coursework." The bundle dates the cohort-2 call for applications to 2025-09-02, notice of award to 2025-11-10, and program start to 2025-11-17 — all prospective relative to the webinar that describes them. The second example was removed from `examples`. The attested present-tense claim ("Datasets are being used for training activities and publications") remains as the sole example. A `source_caveats` was added to the same object recording that the cohort-2 program is prospective, giving the three dates, and stating that its curriculum is carried in `intended_uses` instead — where it already was, unchanged, as the third `intended_uses` entry.

### `updates.frequency` — removed; content redistributed (both records)

The original `frequency` read "Contributing sites provide regular status updates on their extract creation and curation progress; the documents do not state a release cadence for the dataset itself." Half of it was an absence statement and the other half was not a release cadence. In the reconciled records `frequency` is gone. The attested clause about site status updates was appended to `updates.update_details`, and the absence of a release cadence moved to a new `updates.source_caveats`.

### `splits[0].split_details` — absence clause moved to `source_caveats` (full record only)

The original ended with "The source documents describe this as a planned capability and do not report the size or availability of the holdout partition." The reconciled `split_details` retains only the attested plan, in the award abstract's own future tense. The planned-capability framing and the absence of size or availability information are now in `splits[0].source_caveats`. This change is confined to the full record: neither the original nor the reconciled core record carries a `splits` slot.

### `labeling_strategies[0].labeling_details` — absence clause moved to `source_caveats` (both records)

Same pattern, same treatment. `labeling_details` now ends at "capabilities being developed across the multi-center network"; the trailing statement about the future tense and about labels not being reported in the current release is in `labeling_strategies[0].source_caveats`.

### `instances[1].data_substrate` — removed (both records)

`B2AI_SUBSTRATE:37` (Relational Database) was an approximation. The bundle says the EHR data are standardized to the OMOP Common Data Model and reports 1.6 billion rows; it never names a storage substrate. The slot is omitted in both reconciled records. The other `data_substrate` values — `:11` DICOM for imaging, `:49` Waveform Data for telemetry and EEG, `:43` Text for tokenized notes — are directly attested and were retained.

### `status` — reduced to a token (both records)

The original was a two-sentence interpretive paragraph. Both reconciled records read `status: partially released`. Nothing was lost: the current-versus-anticipated distinction and the August 2025 imaging and EEG progress are carried in `description`, `updates.update_details`, and `known_limitations[0]`.

### `creators` — uniform shape, identifiers dropped (both records)

Every Creator now carries a `name`, including the Rosenthal entry, which previously had none and expressed the person only through the nested `principal_investigator`. That nested `Person` object is retained on the Rosenthal entry alone, since the PI designation is attested only there (NIH RePORTER), and it keeps its minted fragment id — a Person requires an `id`, no ORCID is stated anywhere in the bundle, and the fragment is minted on this record's own id as the rule directs. The Creator-level minted ids were dropped from all seven entries.

### Minted identifiers removed from optional-id objects (both records)

Fragment ids were removed from every entry under `instances`, `acquisition_methods`, `collection_mechanisms`, `subpopulations`, `creators`, `external_resources`, `intended_uses`, `existing_uses`, `ethical_reviews`, `preprocessing_strategies`, `cleaning_strategies`, `sampling_strategies`, `data_collectors`, `maintainers`, and `funders`. None of these classes requires `id` and no value in either record pointed at any of them. The five `file_collections` ids were kept — `FileCollection` requires `id` — and they are the same five ids the core record's `distributions` entries carry, so the two records still name the same five parts identically.

### `missing_information[*].missing` — corrected to a list (both records)

The two `MissingInfo` objects now express `missing` as a single-item list rather than a bare string, matching how `why_missing` is expressed alongside it. This was a shape correction made during reconciliation; both records validated afterward.

### `sampling_strategies[0].strategies` — collapsed to a single string (both records)

The original expressed `strategies` as a two-item list. It is now one string containing both sentences. The content is unchanged and the `source_caveats` marking both statements as intended rather than achieved is unchanged.

### `at_risk_populations` — inference marked (both records)

`at_risk_groups_included: true` is retained, since PICU and NICU admissions are attested. But it is an inference: the bundle never characterizes the cohort as at-risk. The `notes` field was trimmed to the attested fact, and a new `source_caveats` records that the boolean is inferred from the reported PICU and NICU admissions and that the documents describe no assent procedures, guardian consent, or special protections.

### `intended_uses[1]` — absence clause moved to `source_caveats` (both records)

Not flagged by the audit, but the same defect as three findings that were: `usage_notes` ended with "the source documents do not report that this holdout set has been released." That clause is now `intended_uses[1].source_caveats` and `usage_notes` carries only the attested plan.

## What was left as-is, and why

**`human_subject_research.special_populations` (multivalency risk).** The audit asked that this be verified and collapsed if single-valued. It remains a single-item list in both reconciled records. The schema digest does not state that it is single-valued, both records validated against their schemas, and the audit did not assert that the list form is wrong — only that it be checked. The content itself the audit accepted as supported.

**`regulatory_restrictions.regulatory_restrictions`** was raised in the same finding as a second multivalency risk. It remains a two-item list in both records, for the same reason, and validated.

**The 50,000 / 45K and 7,642 / 1000 source conflicts.** The audit confirmed these as correctly handled. The top-level `source_caveats` paragraph is identical between the original and reconciled records in both files.

**The MIT license.** The audit confirmed it is correctly withheld from any dataset-level `license` slot and carried only inside `license_and_use_terms.license_terms` with a `source_caveats` explaining that it is a statement about the code. Unchanged.

**`external_resources` entry contents.** The URLs inside the `external_resources` string lists are prose text within descriptive entries and were left exactly as written, including the bare `www.bridge2ai.org/chorus` form the GitHub organization uses. Only the minted `id` on each entry was removed.

**`data_governance.access_review_process`.** The audit noted this already carries the enclave/registration access route, and it does; it is unchanged in both records.

## Cross-record consistency

Every change above was applied identically to both records for the slots the core record carries. Two exceptions are matters of coverage rather than divergence: `splits` appears only in the full record, so its two edits are full-record only. The core record's `distributions` corresponds to the full record's `file_collections` and was unchanged, since neither the audit nor the reconciliation touched those five entries beyond confirming their ids. The core record's header carries `# Sources:` naming the full record path and `# Phase 4 reconciliation: completed`, written only after this phase ran.

## Dispositions

| slot | disposition | record | reason |
|---|---|---|---|
| `distribution_formats` | changed | both | Single entry carrying an access route replaced by five entries, one per bundle-attested per-modality format. |
| `distribution_formats[0].format` | changed | both | `Controlled-access cloud enclave` replaced by `OMOP Common Data Model`; enclave text moved to the entry's `notes`. |
| `existing_uses[0].examples` | changed | both | Prospective cohort-2 example removed; only the attested present-tense use remains. |
| `existing_uses[0].source_caveats` | added | both | Records that cohort 2 is prospective, with its three dates, and that its curriculum sits in `intended_uses`. |
| `updates.frequency` | removed | both | Value stated an absence and did not answer the field; attested clause moved to `update_details`. |
| `updates.update_details` | changed | both | Absorbed the attested site-status-update clause from the removed `frequency`. |
| `updates.source_caveats` | added | both | Holds the absence of a stated release cadence or versioning policy. |
| `splits[0].split_details` | changed | full | Trailing absence statement stripped; only the award abstract's planned capability retained. The core record carries no `splits` slot. |
| `splits[0].source_caveats` | added | full | Holds the planned-capability framing and the unreported holdout size and availability. The core record carries no `splits` slot. |
| `labeling_strategies[0].labeling_details` | changed | both | Trailing absence statement stripped. |
| `labeling_strategies[0].source_caveats` | added | both | Holds the future-tense framing and the absence of labels in the current release. |
| `instances[1].data_substrate` | removed | both | `B2AI_SUBSTRATE:37` unattested; bundle names no storage substrate for the OMOP rows. |
| `status` | changed | both | Interpretive paragraph reduced to the token `partially released`. |
| `creators[0].name` | added | both | PI entry previously had no Creator-level name, unlike the other six. |
| `creators[0].principal_investigator` | retained | both | PI designation attested only for Rosenthal; Person keeps its required minted id, no ORCID stated in the bundle. |
| `creators[*].id` | removed | both | Creator does not require `id` and nothing in either record pointed at these fragments. |
| `instances[*].id` | removed | both | Optional id, unreferenced. |
| `acquisition_methods[*].id` | removed | both | Optional id, unreferenced. |
| `collection_mechanisms[*].id` | removed | both | Optional id, unreferenced. |
| `subpopulations[*].id` | removed | both | Optional id, unreferenced. |
| `external_resources[*].id` | removed | both | Optional id, unreferenced. |
| `intended_uses[*].id` | removed | both | Optional id, unreferenced. |
| `existing_uses[*].id` | removed | both | Optional id, unreferenced. |
| `ethical_reviews[*].id` | removed | both | Optional id, unreferenced. |
| `preprocessing_strategies[*].id` | removed | both | Optional id, unreferenced. |
| `cleaning_strategies[*].id` | removed | both | Optional id, unreferenced. |
| `sampling_strategies[*].id` | removed | both | Optional id, unreferenced. |
| `data_collectors[*].id` | removed | both | Optional id, unreferenced. |
| `maintainers[*].id` | removed | both | Optional id, unreferenced. |
| `funders[*].id` | removed | both | Optional id, unreferenced. |
| `file_collections[*].id` | retained | full | `FileCollection` requires `id`; the same five ids appear on the core `distributions` entries. |
| `instances[2].missing_information[0].missing` | changed | both | Expressed as a list, matching the sibling `why_missing` shape; validated. |
| `instances[4].missing_information[0].missing` | changed | both | Same correction. |
| `instances[2].missing_information[0].why_missing` | retained | both | Left as a list; schema digest does not mark it single-valued and both records validated. |
| `instances[4].missing_information[0].why_missing` | retained | both | Same. |
| `sampling_strategies[0].strategies` | changed | both | Two-item list collapsed to one string; content unchanged. |
| `human_subject_research.special_populations` | retained | both | Left as a single-item list; digest does not mark it single-valued and both records validated. |
| `regulatory_restrictions.regulatory_restrictions` | retained | both | Left as a list, for the same reason. |
| `at_risk_populations.at_risk_groups_included` | retained | both | PICU/NICU admissions attested; the inference is now marked rather than removed. |
| `at_risk_populations.notes` | changed | both | Trimmed to the attested fact; absence material moved out. |
| `at_risk_populations.source_caveats` | added | both | Marks the boolean as inferred and records the absent assent, guardian consent and protections. |
| `intended_uses[1].usage_notes` | changed | both | Trailing absence statement stripped. |
| `intended_uses[1].source_caveats` | added | both | Holds the unreported release status of the holdout set. |
| `source_caveats` | retained | both | Source-conflict handling confirmed correct by the audit; unchanged. |
| `license_and_use_terms.license_terms` | retained | both | MIT correctly scoped to the code, with the caveat intact; unchanged. |
| `data_governance.access_review_process` | retained | both | Already carries the access route; unchanged. |