# Phase 4 Reconciliation Report — AI_READI

## Scope

The Phase 3 audit returned 24 findings against the full record: 1 high (withdrawn on re-check by the auditor itself, plus one further high finding about `distribution_formats`), 2 medium requiring repair, several medium/low observations, and a block of informational entries confirming that supported omissions were correctly handled. This report records what changed in each record, and what did not.

## Findings that produced changes

### 1. `prohibited_uses[*].description` — undeclared key (medium, repaired)

The audit found that `ProhibitedUse`, per the schema digest, accepts only `notes`, `prohibition_reason` and `source_caveats` (plus `id` and `used_software`). The original record placed the substance of each prohibition in a `description` key and the rationale in `prohibition_reason`.

**Change (full and core):** all six entries were rewritten to carry the prohibition statement and its rationale together in `prohibition_reason`, and `description` was dropped from every entry. No prohibition text was lost; each entry now reads as a single statement of what is not permitted and why. This is the only repair that altered the shape of a list rather than its content.

### 2. `sensitive_elements[0].notes` — evidence boundary (medium, repaired)

The note described the composition of the controlled-access distribution (5-digit zip code, sex, race, ethnicity, genetic sequencing data, past health records, medications, traffic and accident reports). That is a different distribution from the referent release.

**Change (full and core):** the `notes` key was removed from the `sensitive_elements` entry. `sensitive_elements_present` and `sensitivity_details` are unchanged and still state what the referent release carries. The controlled-access material remains represented where it belongs — in `known_limitations` (as a scope limitation of this release, reworded from "The public release excludes…" to "This public release excludes…") and in `instances[0].missing_information[1].why_missing`, which was likewise reworded to attribute the statement to the release documentation rather than asserting a live controlled-access holding.

### 3. `missing_data_documentation` — supported omission (low, added)

The audit identified this as clearly supported: the healthsheet and RO-Crate state causes, patterns and handling explicitly, and the content sat only in `instances[0].missing_information` and `anomalies`.

**Addition (full and core):** a new `missing_data_documentation` entry with `missing_data_patterns`, `missing_data_causes` and `handling_strategy`, drawn from the healthsheet composition and preprocessing answers and the RO-Crate `rai:dataCollectionMissingData` and `completeness` fields. The pre-existing `instances[0].missing_information` and `anomalies` entries were retained: they answer different questions (what is missing from an instance; what errors and noise the data carry) and the overlap is deliberate rather than duplicative.

### 4. `extension_mechanism` — supported omission (low, added)

The healthsheet states a definite governance position rather than leaving the question unanswered.

**Addition (full and core):** `extension_mechanism.extension_details` recording that there is currently no mechanism for others to extend or augment the dataset outside the project.

### 5. `related_datasets[2]` — unstated derivation direction (medium, changed)

The entry asserted `is_source_of` for the mini-subset. The bundle states only that a smaller version is available for pipeline development, and the FAIRhub API records the version 3 entry as having `child: 4`.

**Change (full and core):** `relationship_type` changed from `is_source_of` to `has_part`, matching the parent/child containment the FAIRhub API records rather than a derivation the sources do not state. A `source_caveats` was added noting that the bundle supplies no identifier for the mini-subset, that the prose label is therefore the only available `target_dataset` value, and why containment was chosen over derivation. The prose label itself was retained: no identifier exists in the bundle to replace it.

### 6. `distribution_formats[0]` — inconsistent shape (high, changed)

Entry 0 carried a media type in `format` with `media_type` empty, unlike its three siblings.

**Change (full and core):** all four entries were normalized so that `format` carries a format label (`DICOM`, `CSV`, `JSON`, `Markdown`) and `media_type` carries the media type (`application/dicom`, `text/csv`, `application/json`, `text/markdown`). Entry 0 now has both keys populated like its siblings.

### 7. `file_collections[9].file_count` — undisclosed derivation (medium, changed)

The count of 9 is this record's own enumeration of the root metadata files, not a figure any source states.

**Change (full):** a `source_caveats` was added to the `root_metadata` collection naming all nine files and stating that no source gives a count for this directory. The count itself is unchanged. **Change (core):** the same `source_caveats` was carried onto the corresponding core `distributions` entry, even though the core schema's distribution shape does not carry `file_count` — the caveat explains a figure the reader of the full record will encounter and costs nothing in the core.

### 8. `funders[0]` — source-ranking not stated (low, changed)

The original `notes` recorded that the publication lists three grants while the tier-1 sources record one, but did not say which was preferred.

**Change (full and core):** `notes` was replaced by `source_caveats`, which now names the tiers explicitly, states that the tier-1 FAIRhub/RO-Crate funding reference (OT2OD032644) was preferred and is recorded first, and explains why the two publication-only grants are retained (they are stated as support for the research and are not contradicted by the tier-1 sources).

### 9. `purposes[3]` — workforce aim (low, changed)

The audit flagged the "recruiting and training personnel" clause as a project aim from tier-4 NIH RePORTER rather than a purpose for which the dataset was created.

**Change (full and core):** the clause was removed. The entry now reads only "To create a model for developing large scalable datasets, sharing a blueprint that future data generation projects can follow…", which the tier-1 RO-Crate and tier-3 Nature comment both support as a dataset purpose.

### 10. `subpopulations` — presence flag versus distribution (low, changed)

`subpopulation_elements_present: false` paired with a populated `distribution` read as internally contradictory.

**Change (full and core):** the two entries with `false` (race/ethnicity, biological sex) now say in `identification` that the variable is not released *as a participant-level variable*, and their `distribution` values are prefaced with "Although the variable is not released per participant, the release summary table reports aggregate counts…". The two entries with no flag (diabetes status, age) were given `subpopulation_elements_present: true`, which the bundle supports since both are released. No count changed.

### 11. Structural corrections found while editing

Three range corrections were made that the audit did not raise but which the schema digest requires, and which are visible in the comparison:

- `instances[0].missing_information[*].missing` — changed from a scalar string to a single-item list in both records.
- `distribution_dates[*].release_dates` — changed from a scalar string to a single-item list in both records.
- `informed_consent[0].withdrawal_mechanism` — added in both records, carrying the withdrawal statement that `consent_revocations` already held in the full record. `consent_revocations` is retained in the full record; the core schema does not declare it, so the withdrawal fact would otherwise have been absent from the core entirely.

## Findings left as-is

**`conforms_to_standard` (withdrawn by the auditor).** The finding was raised and then withdrawn on re-checking the enum, which admits all seven values used. No change; the value list is identical in both records.

**`total_file_count` / `total_size_bytes` (informational).** The audit confirmed the derivation is disclosed with its inputs named in `source_caveats`. Both figures and the caveat are unchanged.

**`external_resources[*]` (low).** The audit noted that entries carry only `name` and `description`, and that `ExternalResource` declares no URL field so prose is the only place for URLs. One change was made: the documentation entry's `description` now also records the healthsheet's statement that the dataset is self-contained but relies on this documentation, which is the closest the class comes to an archival/future-guarantees answer. The remaining entries are unchanged.

**`instances[0].data_substrate` (informational).** Correctly omitted; multiple substrates, no single fitting term. Still absent.

**`annotation_analyses` / `labeling_strategies` / `machine_annotation_tools` (informational).** Correctly omitted; the healthsheet states no labeling was performed. Still absent from both records.

**`errata` (informational).** The healthsheet's erratum question has an empty response. Still absent.

**`use_repository` / `existing_uses` (informational).** Both answered "No" in the healthsheet. Still absent.

**`data_protection_impacts` (informational).** The healthsheet states no DPIA was conducted. Still absent — an absence correctly represented by omission rather than by a statement of absence.

**`imputation_protocols` (part of finding 14).** No imputation is described in the bundle. Still absent; the handling that *is* described now sits in `missing_data_documentation.handling_strategy`.

**`created_on` / `last_updated_on` (informational).** The FAIRhub `created_at` corresponds to the date already in `issued`. Still absent.

**`was_derived_from` (informational).** Version lineage is carried in `related_datasets`. Still absent.

**`discouraged_uses` (informational).** Correctly routed to `prohibited_uses`. Still absent.

**`data_governance.notes` (informational).** The audit found the future-tense statements acceptable as written. Unchanged in both records.

**`license` (informational).** The audit confirmed the disagreement is disclosed with both values and the preference stated. Unchanged.

**`publisher` (low).** A URL in a `uriorcurie` slot where no declared prefix fits; the fallback the rules permit. Unchanged in both records.

**`instances[0].data_topic` (informational).** `B2AI_TOPIC:43` is single-valued and diabetes is the study's subject. Unchanged.

## Referent

Both records describe the same referent throughout: version 3.0.0 of the Flagship Dataset of Type 2 Diabetes from the AI-READI Project, DOI 10.60775/fairhub.3, the public release of 2280 participants. The controlled-access distribution and the prior versions are represented as other things — in `related_datasets`, in `known_limitations`, and in the caveats — not as facts about the referent.

## Dispositions

| slot | disposition | record | reason |
|---|---|---|---|
| `prohibited_uses[*].description` | removed | both | Key not declared on `ProhibitedUse` in the schema digest; text folded into `prohibition_reason`. |
| `prohibited_uses[*].prohibition_reason` | changed | both | Now carries both the prohibition and its rationale, so no license term was lost when `description` was dropped. |
| `sensitive_elements[0].notes` | removed | both | Described the composition of the controlled-access distribution, a different referent. |
| `sensitive_elements[0].sensitivity_details` | retained | both | States what the referent release carries; unaffected by the boundary problem. |
| `missing_data_documentation` | added | both | Bundle states causes, patterns and handling explicitly; previously only implicit in `instances` and `anomalies`. |
| `extension_mechanism` | added | both | Healthsheet states a definite governance position, not an absent answer. |
| `related_datasets[2].relationship_type` | changed | both | `is_source_of` asserted a derivation the bundle does not state; `has_part` matches the FAIRhub parent/child field. |
| `related_datasets[2].source_caveats` | added | both | Records that no identifier exists for the mini-subset and why containment was chosen over derivation. |
| `related_datasets[2].target_dataset` | retained | both | Bundle supplies no identifier; the descriptive label is the only available value. |
| `distribution_formats[0].format` | changed | both | Held a media type; now a format label, matching siblings. |
| `distribution_formats[0].media_type` | added | both | Previously empty while siblings populated it. |
| `distribution_formats[1].format` | changed | both | Normalized from media type to format label for consistency across the list. |
| `distribution_formats[2].format` | changed | both | Normalized from media type to format label for consistency across the list. |
| `distribution_formats[3].format` | changed | both | Normalized from media type to format label for consistency across the list. |
| `file_collections[9].source_caveats` | added | full | Discloses that `file_count: 9` is this record's own enumeration, not a figure any source states. |
| `distributions[9].source_caveats` | added | core | Same disclosure carried onto the corresponding core distribution entry. |
| `file_collections[9].file_count` | retained | full | The enumeration is correct; only its provenance needed disclosing. |
| `funders[0].notes` | removed | both | Replaced by `source_caveats`, which the disagreement properly belongs in. |
| `funders[0].source_caveats` | added | both | Names the source tiers, states that the tier-1 single-grant reference was preferred, and explains why the publication-only grants are retained. |
| `funders[0].grants` | retained | both | All three grant numbers kept; the tier-1 award is recorded first and the caveat explains the rest. |
| `purposes[3].response` | changed | both | Workforce-training clause was a project aim from a tier-4 source, not a dataset purpose. |
| `subpopulations[0].identification` | changed | both | Clarifies that race/ethnicity is unreleased *as a participant-level variable*, resolving the apparent conflict with `distribution`. |
| `subpopulations[0].distribution` | changed | both | Prefaced to mark the counts as aggregate figures from the release summary table. |
| `subpopulations[1].identification` | changed | both | Same clarification for biological sex. |
| `subpopulations[1].distribution` | changed | both | Same prefacing for the sex counts. |
| `subpopulations[2].subpopulation_elements_present` | added | both | Diabetes status is released; the flag was previously unset. |
| `subpopulations[3].subpopulation_elements_present` | added | both | Age is released; the flag was previously unset. |
| `known_limitations[2].limitation_description` | changed | both | Reworded from "The public release excludes…" to "This public release excludes…" to keep the statement about the referent. |
| `instances[0].missing_information[*].missing` | changed | both | Declared range is multivalued; changed from scalar to list. |
| `instances[0].missing_information[1].why_missing` | changed | both | Reworded to attribute the controlled-access list to the release documentation rather than asserting it as a current holding. |
| `distribution_dates[*].release_dates` | changed | both | Declared range is multivalued; changed from scalar to list. |
| `informed_consent[0].withdrawal_mechanism` | added | both | Declared field left empty while the fact sat only in `consent_revocations`, which the core schema does not declare. |
| `consent_revocations` | retained | full | Still supported and still the fuller statement; the core carries the same fact via `withdrawal_mechanism`. |
| `external_resources[0].description` | changed | both | Now records the healthsheet's self-containment statement, the closest supported answer to the class's archival fields. |
| `conforms_to_standard` | retained | both | Audit finding withdrawn on re-check; all seven values are permitted by the enum. |
| `total_file_count` | retained | full | Stated by FAIRhub; the divergent derived sum is already disclosed with its inputs in `source_caveats`. |
| `total_size_bytes` | retained | full | Same as above. |
| `source_caveats` | retained | both | Already names both values and the preference for each of the four cross-source conflicts. |
| `publisher` | retained | both | URL is the permitted fallback where no declared prefix fits the publisher name. |
| `instances[0].data_topic` | retained | both | Single-valued slot; diabetes is the study's subject. |
| `data_governance.notes` | retained | both | Future-tense statements correctly confined to `notes`; audit found them acceptable. |
| `license` | retained | both | Tier-1 disagreement already disclosed with both values and the preference. |