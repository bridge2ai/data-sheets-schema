# Reconciliation Report — AI_READI

## Scope

Phase 3 returned 25 findings against the full record: two rated `high`, seven `medium`, sixteen `low` (one of which, `conforms_to_standard`, the auditor withdrew in the finding text itself). Phase 4 applied strict reconciliation: a finding was acted on only where the declared bundle supports the change and where the schema digest, not conjecture, settles the shape question. Repairs made to the full record were carried through to the core record wherever the core schema declares the affected slot.

## Findings acted on

### 1. `prohibited_uses[*].description` — shape (medium)

The audit reported that the `ProhibitedUse` class, as the schema digest lists it, accepts only `notes`, `prohibition_reason` and `source_caveats` (plus `id` and `used_software`), and that `description` is not among them. Checking the digest confirms this: the ProhibitedUse entry reads "required: none / also accepts: `notes`, `prohibition_reason`, `source_caveats`". `description` does not appear.

All six entries were rewritten. The prohibition itself and its rationale were merged into `prohibition_reason`, which is the only declared field that can carry either. For example, the first entry moved from a `description` of "Making clinical treatment decisions based on the data." plus a `prohibition_reason` of "The data are intended solely as a research resource." to a single `prohibition_reason`: "Making clinical treatment decisions based on the data is not permitted; the data are intended solely as a research resource." The same merge was applied to the remaining five. No prohibition content was lost. The identical repair was applied to the core record, which declares `prohibited_uses`.

### 2. `sensitive_elements[0].notes` — evidence boundary (medium)

The note described the composition of the controlled-access distribution — 5-digit zip code, sex, race, ethnicity, genetic sequencing data, past health records, medications, traffic and accident reports. That is a different distribution from the referent this record describes. Under the v8 rule that a passage whose subject is another dataset belongs only in `related_datasets` or is omitted, the `notes` key was deleted from `sensitive_elements[0]` in both records. `sensitive_elements_present: false` and `sensitivity_details` remain, both of which speak to the referent.

The same content had also leaked into two neighbouring places phrased as facts about a separate release. `instances[0].missing_information[1].why_missing` previously read "…are held under controlled access"; it now reads "the release documentation states that these variables … are not included in the public dataset", which is a statement about this release. `known_limitations[2].limitation_description` was reworded the same way, from "held under controlled access" to "are not included". Both changes were carried to the core record.

### 3. `missing_data_documentation` — supported omission (low, but clearly supported)

The audit noted that the bundle states missing-data causes, patterns and handling explicitly, and that this content sat only in `instances[0].missing_information` and `anomalies`. A `missing_data_documentation` entry was added to both records with `missing_data_patterns`, `missing_data_causes` and `handling_strategy`, drawn from the healthsheet composition answer, the RO-Crate `rai:dataCollectionMissingData` and `completeness` fields, and the cleaning-strategy passage (missing data that could be filled from other portions of a record were filled under site-PI approval).

### 4. `extension_mechanism` — supported omission (low)

The healthsheet states a definite governance position: "currently there is no mechanism for others to extend or augment the AI-READI dataset outside of those who are involved in the project." That is an answer, not an absence, so `extension_mechanism.extension_details` was added to both records.

### 5. `related_datasets[2]` — unsupported relationship direction (medium)

`relationship_type` was changed from `is_source_of` to `has_part`. The bundle states two things about the mini-subset: the FAIRhub v3 page notes "A smaller version is available for pipeline development…", and the FAIRhub API records the v3 dataset entry with `"child": 4`. Neither states a derivation direction. `has_part` reflects the parent/child containment the API records; `is_source_of` asserted a derivation the sources do not support. A `source_caveats` was added to the entry noting that the bundle gives no identifier for the mini-subset, that the prose label is therefore the only available `target_dataset` value, and why the containment relation was chosen. Applied to both records.

### 6. `distribution_formats[0]` — inconsistent shape (high)

Entry 0 carried `format: application/dicom` with no `media_type`, while entries 1–3 carried both. All four entries were normalized: `format` now holds a format label (`DICOM`, `CSV`, `JSON`, `Markdown`) and `media_type` holds the media type (`application/dicom`, `text/csv`, `application/json`, `text/markdown`). The FAIRhub API `format` array supplies all four media types verbatim. Applied to both records.

### 7. `file_collections[9].file_count` — undisclosed derivation (medium)

The count of 9 is this record's own enumeration of the root `metadataFileList`; no source states it. A `source_caveats` was added to the collection naming the nine files enumerated and stating that no source gives a count for this directory. In the core record the collection appears under `distributions`; the same caveat was added there. The `file_count` value itself is not declared on the core `distributions` entries, so only the caveat carries over.

### 8. `funders[0]` — source-ranking disclosure (low)

The audit observed that the three-grant list follows a tier-3 publication while tier-1 sources record only OT2OD032644, and that the caveat did not say which was preferred. The free-text `notes` was replaced with a `source_caveats` that states the disagreement, names each source and its tier, states that the tier-1 value OT2OD032644 was preferred and is recorded first, and explains that the two additional grants are retained because the publications state them as support for the research rather than in contradiction of the tier-1 funding reference. Applied to both records.

### 9. `collection_timeframes[0].source_caveats` — source-ranking disclosure (implied by the same rule)

The original caveat stated the BMJ Open date discrepancy without naming which source was preferred. It was rewritten to name the tiers (tier-1 FAIRhub and tier-2 healthsheet give 2023-07-19; tier-3 BMJ Open gives 18 July 2023) and to state that the higher-ranked value was used. Applied to both records.

### 10. `purposes[3]` — subject boundary (low)

The audit flagged the workforce-training clause as a project activity rather than a purpose for which this dataset was created. The clause "and to increase access to and quality of AI/ML research by recruiting and training personnel" was removed; the entry now reads only "To create a model for developing large scalable datasets, sharing a blueprint that future data generation projects can follow…". Applied to both records.

### 11. `subpopulations` — internal consistency (low)

`subpopulations[0]` and `[1]` paired `subpopulation_elements_present: false` with a populated `distribution`. Both `identification` and `distribution` were reworded to make the pairing legible: `identification` now says the variable is not released "as a participant-level variable", and `distribution` now opens "Although the variable is not released per participant, the release summary table reports aggregate counts…". `subpopulations[2]` and `[3]` were given the explicit `subpopulation_elements_present: true` they previously lacked, since diabetes status and age are released. Applied to both records.

### 12. `informed_consent[0].withdrawal_mechanism` — declared field left empty (not raised by the audit)

While reworking `prohibited_uses` the withdrawal content was found present in `consent_revocations` but absent from the `InformedConsent` object, which declares `withdrawal_mechanism`. The field was populated in both records from the same healthsheet passage. `consent_revocations` is retained in the full record (the core schema does not declare it).

### 13. `external_resources[0]` — under-populated object (low, partially acted on)

The audit noted that ExternalResource declares `archival` and `future_guarantees` and that the healthsheet supports a statement about self-containment. The healthsheet sentence — that the dataset is self-contained but does rely on the documentation for provenance information — was added to the documentation entry's `description`. `archival` and `future_guarantees` were not populated: the healthsheet's question on guarantees is answered only in respect of licensing, and no source states whether the documentation is archived, so a boolean there would be inference.

## Findings left as-is

**`conforms_to_standard` (high, withdrawn).** The auditor raised this and then withdrew it within the finding text after re-checking the enum. All seven values used — `CDS`, `WFDB`, `OMOP_CDM`, `DICOM`, `OPEN_MHEALTH`, `ESDS`, `RO_CRATE` — are permitted by the digest. Unchanged in both records.

**`total_file_count` / `total_size_bytes` (medium, informational).** The audit confirmed the derivation is disclosed with its inputs named. The `source_caveats` states both stated totals, both computed sums with their addends spelled out, and both differences. Unchanged.

**`file_collections[9].resources` per-entry receipts (medium).** The audit noted the nine File entries are receipted by a passage that names each file individually, so per-entry receipts do exist. Only the derived `file_count` needed disclosure, which was added. The entries themselves are unchanged.

**`external_resources[*]` prose URLs (low).** ExternalResource declares no URL field, so prose in `description` is the only available placement. Unchanged.

**`instances[0].data_substrate` (low, informational).** Omitted, correctly: the release spans DICOM imaging, CSV tables, JSON and waveform data, and no single B2AI_SUBSTRATE term covers that. Omission is the rule's answer.

**`annotation_analyses`, `labeling_strategies`, `machine_annotation_tools` (low).** All omitted; the healthsheet states "N/A - no labels are provided". Omission rather than a statement of absence. Unchanged.

**`errata` (low).** Omitted; the healthsheet erratum question has an empty response, which is an unanswered question rather than an assertion that no errata exist. Unchanged.

**`use_repository`, `existing_uses` (low).** Both omitted against healthsheet "No" answers. Unchanged.

**`data_protection_impacts` (low).** Omitted against an explicit "No, a data protection impact analysis has not been conducted." Unchanged.

**`created_on`, `last_updated_on` (low).** Omitted. The FAIRhub `created_at` epoch corresponds to the publication date already in `issued`; recording it twice would create two facts from one. Unchanged.

**`was_derived_from` (low).** Omitted; version lineage is in `related_datasets` and the release derives from prospective collection, not a prior resource. Unchanged.

**`discouraged_uses` (low).** Omitted; the healthsheet routes the question to the license restrictions, which are carried as prohibitions. Unchanged.

**`data_governance.notes` (low, acceptable as written per the audit).** The future-tense Data Access Committee material is confined to `notes` and rendered in past-progressive. Unchanged.

**`license` (low, informational).** The tier-1 disagreement is disclosed with both values and the preference stated. Unchanged.

**`publisher` (low).** `https://fairhub.io/` is a URL in a `uriorcurie` slot. The bundle gives `publisherName: FAIRhub` and no registry identifier; a resolvable URL is the permitted fallback where no declared prefix fits. Unchanged.

**`instances[0].data_topic` (low, informational).** `B2AI_TOPIC:43` on a single-valued slot. Unchanged.

## Validation

Both records were validated after reconciliation: the full record against `Dataset` in `data_sheets_schema_all.yaml`, the core record against `CoreDataset` in `data_sheets_schema_core_all.yaml`. Both pass.

## Dispositions

| slot | disposition | record | reason |
|---|---|---|---|
| `conforms_to_standard` | retained | both | Audit finding withdrawn in its own text; all seven values are members of DataStandardEnum per the digest. |
| `distribution_formats[0].format` | changed | both | Normalized to a format label (`DICOM`) with the media type moved to the sibling `media_type`, matching entries 1–3. |
| `distribution_formats[0].media_type` | added | both | Sibling field left empty while entries 1–3 populated it; `application/dicom` supplied by the FAIRhub API format array. |
| `distribution_formats[1].format` | changed | both | Media type replaced by format label `CSV` for consistency across the list. |
| `distribution_formats[2].format` | changed | both | Media type replaced by format label `JSON` for consistency across the list. |
| `distribution_formats[3].format` | changed | both | Media type replaced by format label `Markdown` for consistency across the list. |
| `prohibited_uses[0].prohibition_reason` | changed | both | `description` is not a declared key on ProhibitedUse in the digest; prohibition text merged into the declared field. |
| `prohibited_uses[1].prohibition_reason` | changed | both | Same: prohibition text merged into the only declared field that can carry it. |
| `prohibited_uses[2].prohibition_reason` | changed | both | Same. |
| `prohibited_uses[3].prohibition_reason` | changed | both | Same. |
| `prohibited_uses[4].prohibition_reason` | changed | both | Same. |
| `prohibited_uses[5].prohibition_reason` | changed | both | Same. |
| `sensitive_elements[0].notes` | removed | both | Described the composition of the controlled-access distribution, a different distribution from the referent. |
| `instances[0].missing_information[1].why_missing` | changed | both | Reworded from "held under controlled access" to a statement about what this public release does not include. |
| `known_limitations[2].limitation_description` | changed | both | Same rewording, from a claim about another distribution to a statement about this release. |
| `missing_data_documentation` | added | both | Bundle states causes, patterns and handling explicitly; previously carried only indirectly under `instances` and `anomalies`. |
| `extension_mechanism` | added | both | Healthsheet states a definite governance position, which is an answer rather than an absence. |
| `related_datasets[2].relationship_type` | changed | both | `is_source_of` asserted a derivation direction the bundle does not state; `has_part` reflects the FAIRhub parent/child field. |
| `related_datasets[2].source_caveats` | added | both | Records that no identifier exists for the mini-subset and why the containment relation was chosen. |
| `related_datasets[2].target_dataset` | retained | both | Bundle supplies no DOI or other identifier; the descriptive label is the only available value. |
| `file_collections[9].source_caveats` | added | full | Discloses that `file_count: 9` is this record's own enumeration of the root metadataFileList, not a stated figure. |
| `distributions[9].source_caveats` | added | core | Same disclosure carried to the core record's corresponding entry. |
| `file_collections[9].file_count` | retained | full | Value is correct; only its derived status needed disclosure, now supplied in `source_caveats`. |
| `file_collections[9].resources` | retained | full | Audit confirmed each File entry is receipted by a passage naming the files individually. |
| `funders[0].notes` | removed | both | Replaced by a `source_caveats` that names tiers and states which source was preferred. |
| `funders[0].source_caveats` | added | both | States the tier-1/tier-3 disagreement on grant count, names each source, and records that the tier-1 value was preferred. |
| `funders[0].grants` | retained | both | Additional grants are stated by the publications as support for the research, not contradicted by tier-1 sources. |
| `collection_timeframes[0].source_caveats` | changed | both | Rewritten to name the tiers of the disagreeing sources and state that the higher-ranked start date was used. |
| `purposes[3].response` | changed | both | Removed the workforce recruiting-and-training clause, a project activity rather than a purpose of the dataset. |
| `subpopulations[0].identification` | changed | both | Clarified that the variable is unreleased at participant level, reconciling it with the populated `distribution`. |
| `subpopulations[0].distribution` | changed | both | Reframed as aggregate counts from the release summary table rather than released per-participant values. |
| `subpopulations[1].identification` | changed | both | Same clarification for biological sex. |
| `subpopulations[1].distribution` | changed | both | Same reframing for biological sex. |
| `subpopulations[2].subpopulation_elements_present` | added | both | Diabetes status is released; the flag was previously absent while siblings carried it. |
| `subpopulations[3].subpopulation_elements_present` | added | both | Age is released; the flag was previously absent while siblings carried it. |
| `informed_consent[0].withdrawal_mechanism` | added | both | Declared field on InformedConsent left empty while the bundle states the withdrawal terms. |
| `consent_revocations` | retained | full | Not declared by the core schema; retained in the full record where the class exists. |
| `external_resources[0].description` | changed | both | Added the healthsheet statement that the dataset is self-contained but relies on this documentation for provenance. |
| `external_resources[0].archival` | retained | both | Omitted: no source states whether the documentation is archived; a boolean would be inference. |
| `total_file_count` | retained | full | Stated FAIRhub figure; the record's own sum and the difference are disclosed in `source_caveats` with addends named. |
| `total_size_bytes` | retained | full | Same: stated figure retained, derived sum and difference disclosed with inputs named. |
| `instances[0].data_substrate` | retained | both | Omitted: the release spans multiple substrates and no single B2AI_SUBSTRATE term fits. |
| `errata` | retained | full | Omitted: the healthsheet's erratum response is empty, an unanswered question rather than an assertion of absence. |
| `use_repository` | retained | full | Omitted against an explicit healthsheet "No" rather than populated with a negation. |
| `existing_uses` | retained | full | Omitted against an explicit healthsheet "No". |
| `data_protection_impacts` | retained | full | Omitted against an explicit statement that no DPIA was conducted. |
| `discouraged_uses` | retained | full | Omitted: the healthsheet routes the question to the license restrictions, carried under `prohibited_uses`. |
| `created_on` | retained | full | Omitted: the FAIRhub epoch duplicates the publication date already in `issued`. |
| `last_updated_on` | retained | full | Omitted for the same reason. |
| `was_derived_from` | retained | full | Omitted: the release derives from prospective collection; version lineage sits in `related_datasets`. |
| `annotation_analyses` | retained | full | Omitted: the healthsheet states no labels were produced and no annotation was performed. |
| `labeling_strategies` | retained | full | Same. |
| `machine_annotation_tools` | retained | full | Same. |
| `data_governance.notes` | retained | both | Future-tense committee material is confined to `notes` and rendered in past-progressive, as the audit accepted. |
| `license` | retained | both | Tier-1 disagreement disclosed in `source_caveats` with both values and the preference stated. |
| `publisher` | retained | both | Resolvable URL is the permitted fallback where the bundle supplies no registry identifier for FAIRhub. |
| `instances[0].data_topic` | retained | both | Single-valued slot; `B2AI_TOPIC:43` names the study's subject. |