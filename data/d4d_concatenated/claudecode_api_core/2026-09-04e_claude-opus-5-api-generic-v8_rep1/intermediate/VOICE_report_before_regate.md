# Phase 4 Reconciliation Report — VOICE

## Scope

The Phase 3 audit returned fourteen findings against the full record: four medium and ten low. No finding alleged a fabrication, and none required withdrawal of a substantive claim. The reconciliation therefore consisted of re-scoping four claims to what the bundle actually supports, moving content out of fields it did not answer, adding structure the schema declares and the bundle supplies, and recording two source conflicts that had gone unstated. Both records were regenerated; the core record was re-derived by projection so that every change to a shared slot propagates.

## Changes made to the full record

### `description` — controls substituted for the pediatric cohort (medium)

The original description enumerated "five cohort categories: voice disorders, neurological and neurodegenerative disorders, mood and psychiatric disorders, respiratory disorders, and controls." No source supports that list. Both the tier-1 PhysioNet 3.1.0 page and the tier-2 project documentation give the fifth category as *Pediatric Voice and Speech Disorders*; controls are an additional recruitment group, not one of the five. The description now names the five categories as the sources define them and then states separately that version 3.1.0 covers "the four adult categories together with control participants who do not have the conditions of interest." This distinguishes the consortium's taxonomy from what this release contains.

### `purposes` — unrecorded 10,000-vs-30,000 conflict (medium)

The original record carried only the 30,000-voice target from the audiomics white paper (tier 3) and the IRB protocol (tier 2), and did not mention the project documentation's (tier 2) figure of 10,000 voices with an anticipated 2027 enrollment of 10,000. A new `purposes` entry now states the 10,000 figure, and both entries carry `source_caveats` naming the other figure. A paragraph was added to the dataset-level `source_caveats` recording the disagreement, the sources on each side, and the fact that the IRB protocol itself separately describes a phased plan cumulatively reaching 5,000 participants. The ranking does not settle this — documentation and IRB protocol are both tier 2 — so both values are represented rather than one selected.

### `prohibited_uses` — prohibition statements in `prohibition_reason` (medium)

All four entries put the prohibition itself into `prohibition_reason`. Each entry now carries the prohibition in `notes` and a reason in `prohibition_reason`, drawn from the bundle: the consortium's "commitment to advancing ethical and trustworthy research practices that respect and protect the rights and interests of research participants" for the first two, the Open Science alignment for the IP restriction, and the DUA's control-and-safeguards obligation for the redistribution ban.

### `conforms_to` / `conforms_to_standard` — BIDS scoped to the wrong artifact (medium)

The BIDS v1.9.0 claim rests solely on the project documentation's Data Pre-Processing section, whose folder listing (`b2ai-voice-audio`, `sub-<participant_id>/ses-.../audio/*.wav`) describes the audio-containing distribution, not the feature-only PhysioNet release that is this record's referent. Neither PhysioNet page mentions BIDS. The values were retained — the documentation does state the conversion, and the phenotype layout is shared across distributions — but a paragraph in `source_caveats` now scopes the claim to the audio distribution and the phenotype folder structure and notes the PhysioNet silence.

### `regulatory_restrictions.hipaa_compliant` — unreconciled tier-2 tension (low)

The slot held `compliant`, sourced from the documentation's "Does this dataset apply the HIPAA de-identification rules? Yes". Attachment 2 of the DUA, an equally ranked source, states the transferred data "is Personally Identifiable Information … and not covered under HIPAA, FERPA, or similar laws." The enum admits one value and the two sources concern different distributions, so the slot was **removed** and a `source_caveats` note added to `regulatory_restrictions` explaining why, quoting both. A corresponding paragraph was added to the dataset-level `source_caveats`. Everything else in the object — `confidentiality_level`, `regulatory_restrictions`, `other_compliance` — is unchanged.

### `creators` — an entry naming no entity (low)

The sixteenth `Creator` carried only `notes` about "over 50 other investigators." It was removed from `creators`; the content now appears in the dataset-level `source_caveats`, which also notes the hundred-plus PhysioNet author list and states that those contributors are not individually recorded. Fifteen `Creator` entries remain, each naming a person and an affiliation.

### `cleaning_strategies`, `splits`, `data_protection_impacts` — objects stating an absence (low)

- `cleaning_strategies[0]` ("No pre-processing for cleaning the data was performed") was removed. The audit-protocol entry remains and now carries a `notes` field recording the healthsheet's contrary answer and observing that the audit checks and characterizes rather than alters.
- `splits[0]` was rewritten to drop the bare negative and keep the substance: researchers create their own splits, and details of predefined tasks and labeling are in the dataset.
- `data_protection_impacts` was removed entirely; its single entry said only that no impact analysis had been conducted.

### `machine_annotation_tools` — preprocessing tools listed as annotation tools (low)

`b2aiprep` and `SenseLab` were removed from `tools` and from `tool_descriptions`; the bundle describes them as organizing/preprocessing and audio-processing toolkits. A new `preprocessing_strategies` entry records both, including that b2aiprep v3.0.0 generated this release. `tool_descriptions` was also converted from a list to a single prose string, since the schema declares it a scalar.

### `distribution_dates` — version 1.0 missing (low)

The release list ran 1.1 through 3.1.0 while `version_access.versions_available` included 1.0. A line for version 1.0, published on the Health Data Nexus at the end of November 2024, was added, removing the internal inconsistency.

### `errata[0].erratum_url` — landing page in an erratum slot (low)

The URL pointed at the release landing page, not an erratum. It was removed. The `source_caveats` on `errata[2]` was extended to record that the corrections were transcribed from the Release Notes section of the PhysioNet release pages and that the bundle supplies no separate erratum document or URL.

### `tasks[1]` — interpolated reference to the pediatric release (low)

The clause "including pediatric voice disorders in the companion pediatric release" was not in the healthsheet sentence it derived from and imported a sibling dataset into the referent's own slot. The entry now follows the source: "including vocal pathologies and neurological, psychiatric, respiratory and pediatric voice disorders." The pediatric release remains in `related_datasets`.

### `file_collections[1]` and `[2]` — inventories held as prose (low)

The phenotype and metadata collections had their contents narrated in `description` while `resources` stayed empty. Both now carry `resources`: six `File` entries for phenotype (confounders, demographics, diagnosis, enrollment, questionnaire, task) and two for metadata (the Parquet file and its dictionary), each with an `id`, a name, a `file_type` and a description. The collection descriptions were shortened accordingly.

### `subsets` — unpopulated despite per-condition partitioning (low)

Five `DataSubset` entries were added, one per cohort — voice disorders, respiratory, neurological, mood and psychiatric, and controls — each with a minted fragment id, `is_subpopulation: true`, and a description naming the per-condition diagnosis tables it covers, the inclusion criteria and the gold-standard validation methods.

### `extension_mechanism.extension_details` — platform generalized away (low)

The derivative-dataset route was stated without the platform. "on the Health Data Nexus" was restored and a `source_caveats` added noting that the bundle does not say whether an equivalent route exists on PhysioNet.

## Incidental schema corrections

Three scalar-ranged slots held lists and were converted to prose strings: `participant_privacy[0].privacy_techniques`, `sampling_strategies[0].strategies`, and `missing_data_documentation[0].missing_data_patterns` / `.missing_data_causes`. `instances[0].missing_information[0].missing` was converted from a scalar to a single-element list. These were not audit findings; they were caught while editing adjacent content.

## Changes to the core record

The core record was re-derived from the reconciled full record. Every change above that touches a slot the core schema declares is reflected: the description, the two `purposes` entries and their caveats, the restructured `prohibited_uses`, the removed `hipaa_compliant`, the fifteen-entry `creators` list, the revised `cleaning_strategies` and `splits`, the absent `data_protection_impacts`, the shortened `machine_annotation_tools` and the new `preprocessing_strategies` entry, the six-line `distribution_dates`, the `errata` without its URL, the corrected `tasks[1]`, the extended dataset-level `source_caveats`, the scoped `extension_mechanism`, and the scalar corrections.

Two structural differences follow from the core schema. The core record has no `subsets` slot, so the five cohort subsets appear only in the full record. The core record's `distributions` slot flattens the full record's `file_collections` hierarchy, so the eight new phenotype and metadata `File` entries appear there as top-level distribution entries rather than nested under their collections.

The core header now carries `# Phase 4 reconciliation: completed`.

## Left as-is

The audit questioned no value that was retained without change. Every finding produced either an edit or a caveat. Findings where the substantive claim survived — BIDS conformance and the `errata` content — are recorded above as caveat-only or partial changes rather than as untouched.

## Dispositions

| slot | disposition | record | reason |
|---|---|---|---|
| `description` | changed | both | Five cohort categories restated as the sources define them; controls described separately as an additional recruitment group. |
| `purposes[3]` | added | both | The project documentation's 10,000-voice target, previously unrecorded, with a caveat naming the conflicting figure. |
| `purposes[4].source_caveats` | added | both | Records that the 30,000 figure comes from lower-ranked sources and that the IRB also describes a 5,000-participant phased plan. |
| `source_caveats` | changed | both | Three paragraphs added: the target-size conflict, the BIDS scoping, and the HIPAA-coverage tension; plus the relocated note about the 50-plus additional contributors. |
| `prohibited_uses` | changed | both | All four entries restructured so the prohibition sits in `notes` and a reason drawn from the bundle sits in `prohibition_reason`. |
| `conforms_to` | retained | both | Value kept; scoped in `source_caveats` to the audio distribution and shared phenotype layout. |
| `conforms_to_standard` | retained | both | Same scoping as `conforms_to`. |
| `regulatory_restrictions.hipaa_compliant` | removed | both | Two equally ranked sources characterize HIPAA coverage differently for different distributions; the enum admits one value. |
| `regulatory_restrictions.source_caveats` | added | both | Explains the removal and quotes both sources. |
| `creators` | changed | both | Sixteenth entry, which named no entity, removed; its content moved to dataset-level `source_caveats`. |
| `cleaning_strategies` | changed | both | Bare-negative entry removed; audit-protocol entry retained and given a `notes` field recording the healthsheet's contrary answer. |
| `splits[0].split_details` | changed | both | Rewritten to state what users should do rather than what the release lacks. |
| `data_protection_impacts` | removed | both | Sole entry recorded only that no impact analysis was conducted. |
| `machine_annotation_tools[0].tools` | changed | both | b2aiprep and SenseLab removed; they are preprocessing toolkits, not annotation tools. |
| `machine_annotation_tools[0].tool_descriptions` | changed | both | Corresponding descriptions removed; converted from list to prose for the declared scalar range. |
| `preprocessing_strategies` | changed | both | New entry recording b2aiprep and SenseLab, including the b2aiprep version that generated this release. |
| `distribution_dates[0].release_dates` | changed | both | Version 1.0 added, resolving inconsistency with `version_access.versions_available`. |
| `errata[0].erratum_url` | removed | both | Pointed at the release landing page, not an erratum; the bundle supplies no erratum URL. |
| `errata[2].source_caveats` | changed | both | Records that corrections were transcribed from the Release Notes and that no erratum document exists. |
| `tasks[1].response` | changed | both | Interpolated reference to the companion pediatric release removed; wording follows the healthsheet. |
| `file_collections[1].resources` | added | full | Six `File` entries for the phenotype subfolders, replacing narrative inventory in `description`. |
| `file_collections[1].description` | changed | full | Shortened now that the inventory is structured. |
| `file_collections[2].resources` | added | full | Two `File` entries for the metadata Parquet file and its data dictionary. |
| `file_collections[2].description` | changed | full | Shortened now that the inventory is structured. |
| `subsets` | added | full | Five cohort subsets with minted fragment ids, inclusion criteria and gold-standard validation methods. |
| `extension_mechanism.extension_details` | changed | both | "on the Health Data Nexus" restored. |
| `extension_mechanism.source_caveats` | added | both | Notes that the bundle does not state whether an equivalent route exists on PhysioNet. |
| `participant_privacy[0].privacy_techniques` | changed | full | Converted from list to prose for the declared scalar range. |
| `sampling_strategies[0].strategies` | changed | both | Converted from list to prose for the declared scalar range. |
| `missing_data_documentation[0].missing_data_patterns` | changed | both | Converted from list to prose for the declared scalar range. |
| `missing_data_documentation[0].missing_data_causes` | changed | both | Converted from list to prose for the declared scalar range. |
| `instances[0].missing_information[0].missing` | changed | both | Converted from scalar to single-element list for the declared multivalued range. |
| `subpopulations[1].identification` | changed | both | Cohort enumeration removed in favor of a general statement, consistent with the `description` correction; the per-cohort detail now lives in `subsets`. |
| `distributions` | changed | core | Eight new phenotype and metadata file entries projected in as top-level distributions, the core schema having no nested collection structure. |