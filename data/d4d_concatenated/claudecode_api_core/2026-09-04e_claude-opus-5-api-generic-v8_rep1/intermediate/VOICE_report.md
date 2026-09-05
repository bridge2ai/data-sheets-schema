# Phase 4 Reconciliation Report — VOICE

## 1. Audit outcome in summary

The Phase 3 audit returned fourteen findings against the full record: four medium, ten low. None alleged a fabrication — no finding claimed the record asserted something the bundle does not support in any form. The findings clustered into four kinds of defect:

1. **Content misplaced relative to the slot's declared meaning** (`prohibited_uses`, `machine_annotation_tools`, `errata[0].erratum_url`, `tasks[1]`).
2. **Structure held as prose where the schema declares fields for it** (`file_collections[1].resources`, `file_collections[2].resources`, `subsets` unpopulated).
3. **Objects that state an absence rather than answering the field** (`cleaning_strategies[0]`, `data_protection_impacts[0]`, `splits[0]`, `creators[15]`).
4. **Source disagreements left unrecorded** (`purposes` 10,000 vs 30,000; `regulatory_restrictions.hipaa_compliant`; `conforms_to` scoping; `distribution_dates` internal inconsistency).

Twelve findings produced changes. Two were left as-is, one wholly and one in part, for reasons given below.

---

## 2. Changes made to the full record

### 2.1 `description` — the five cohort categories (medium)

**Finding:** the description enumerated the five cohort categories as ending in "controls," substituting controls for the pediatric category that both tier-1 and tier-2 sources name.

**Change:** the sentence was rewritten. It now states the consortium's five categories as the sources give them — voice disorders, neurological and neurodegenerative, mood and psychiatric, respiratory, and pediatric voice and speech disorders — and then separately states that version 3.1.0 covers "the four adult categories together with control participants who do not have the conditions of interest." The taxonomy and the release's actual coverage are now two distinct statements rather than one conflated one. The same correction was carried into `subpopulations[1].identification`, which previously enumerated the same five-with-controls list and now describes cohort assignment without enumerating a taxonomy that would need the same qualification.

### 2.2 `purposes` — the target-size disagreement (medium)

**Finding:** the record carried the 30,000-voice target from the white paper and IRB protocol but not the 10,000-voice target from the project documentation, a higher-ranked source, and recorded no disagreement.

**Change:** a new `purposes` entry was added stating the 10,000-voice target and the anticipated 2027 enrollment count, carrying a `source_caveats` pointing at the conflicting entry. The existing 30,000 entry gained its own `source_caveats` naming where that figure comes from and noting the IRB protocol's separate phased plan reaching 5,000. A paragraph was added to the dataset-level `source_caveats` setting out the conflict in full.

Both figures are stated rather than one being selected. The ranking rule prefers the higher-ranked source when a single value must be chosen; here the two figures are project *aspirations* stated at different times by different documents, and neither is the dataset's current state. Recording both with attribution is more faithful than silently promoting one.

### 2.3 `prohibited_uses` — reason vs prohibition (medium)

**Finding:** all four entries placed the prohibition statement itself in `prohibition_reason`.

**Change:** all four entries were restructured. The prohibition now sits in `notes`; `prohibition_reason` carries the reason the bundle supplies. For the first two entries the reason is the consortium's stated commitment to "advancing ethical and trustworthy research practices that respect and protect the rights and interests of research participants." For the third it is the Open Science rationale the bundle gives verbatim. For the fourth the reason is drawn from the DUA's control-and-safeguards clause.

### 2.4 `conforms_to` / `conforms_to_standard` — scoping (medium)

**Finding:** BIDS conformance was asserted for the feature-only PhysioNet referent, but the only supporting passage describes the audio-containing distribution.

**Change:** the slots were retained; a paragraph was added to the dataset-level `source_caveats` scoping the claim. It names the folder listing the claim rests on, notes that neither the 3.1.0 nor the 3.0.0 release page mentions BIDS, and states that the claim covers the audio distribution and the shared phenotype layout rather than the published feature-only release.

Retention over removal: the conformance is attested by a tier-2 source about a distribution of this dataset, and `preprocessing_strategies` independently records the BIDS conversion step. Removing the slots would lose an attested fact; the caveat records exactly what the fact covers.

### 2.5 `creators[15]` — the Creator naming no entity (low)

**Finding:** the final Creator object carried only `notes` about "over 50 other investigators" and named no entity.

**Change:** the object was removed from `creators`. Its content was moved into the dataset-level `source_caveats`, which now records the additional contributors and the hundred-plus author list, and states that they are not individually recorded.

### 2.6 `regulatory_restrictions.hipaa_compliant` (low)

**Finding:** set to `compliant` on the documentation's evidence, with the DUA's contrary framing unrecorded.

**Change:** the enum value was removed. A `source_caveats` was added to `regulatory_restrictions` explaining why: two equally ranked tier-2 sources characterize the data's HIPAA status differently because they govern different distributions, and the ranking cannot settle between them. A parallel note was added to the dataset-level `source_caveats`.

Removal rather than a different enum value: no enum member expresses "two sources, two distributions, no reconciliation available." Omission plus caveat is the honest answer.

### 2.7 `cleaning_strategies` / `data_protection_impacts` / `splits` — absence-stating objects (low)

**Changes, differing by slot:**

- `cleaning_strategies[0]` ("No pre-processing for cleaning the data was performed") was removed as a standalone entry. The healthsheet's denial is preserved as a `notes` on the surviving audit-protocol entry, where it reads as context for why that entry describes checking rather than altering.
- `data_protection_impacts` was removed entirely. Its single entry stated only that no impact assessment was conducted.
- `splits[0]` was rewritten to drop the leading "There are no predefined recommended data splits" and retain the substantive guidance: researchers create their own splits, and task and labeling details are in the dataset.

### 2.8 `machine_annotation_tools` (low)

**Finding:** b2aiprep and SenseLab listed as annotation tools when the bundle describes them as preprocessing toolkits.

**Change:** both were removed from the `tools` list and their descriptions from `tool_descriptions`. A ninth `preprocessing_strategies` entry was added recording both toolkits, their functions as the bundle states them, and that b2aiprep v3.0.0 generated this release. Nothing was lost; the content moved to the field it answers.

### 2.9 `distribution_dates` (low)

**Finding:** version 1.0 missing from `release_dates` while present in `version_access.versions_available`.

**Change:** `"Version 1.0: published on the Health Data Nexus at the end of November 2024"` was prepended to the list, using the date the documentation gives. The two slots now agree.

### 2.10 `errata[0].erratum_url` (low)

**Change:** the slot was removed — it held the release landing page, not an erratum document. The existing `source_caveats` on `errata[2]` was extended to state that the corrections were transcribed from the Release Notes section of the PhysioNet release pages and that the bundle supplies no separate erratum document or URL.

### 2.11 `tasks[1]` (low)

**Change:** the clause "including pediatric voice disorders in the companion pediatric release" was replaced with the healthsheet's own wording, "including vocal pathologies and neurological, psychiatric, respiratory and pediatric voice disorders." The interpolated cross-reference to the sibling dataset is gone; the pediatric release remains in `related_datasets` where it belongs.

### 2.12 `file_collections[1].resources` and `file_collections[2].resources` (low)

**Change:** both collections gained `resources` lists. The phenotype collection now carries six File objects — confounders, demographics, and the diagnosis, enrollment, questionnaire and task subfolders — each with a minted fragment id, a `file_type`, and where applicable `format` and `media_type`; the inventory detail moved out of the collection `description` into the per-file descriptions. The metadata collection gained two File objects for the Parquet file and its dictionary. Each collection `description` was trimmed to what describes the collection as a whole.

### 2.13 `subsets` (low)

**Change:** five `DataSubset` objects were added, one per cohort partition the release ships as diagnosis tables: voice disorders, respiratory, neurological, mood and psychiatric, and controls. Each carries a minted fragment id, `is_subpopulation: true`, and a description naming the per-condition tables it covers and the gold-standard validation method the bundle states for that cohort.

### 2.14 `extension_mechanism.extension_details` (low)

**Change:** "may publish a derivative dataset that references the original source" was restored to the platform-specific form the bundle uses — "may publish a derivative dataset on the Health Data Nexus." A `source_caveats` was added noting that the bundle does not state whether an equivalent route exists on PhysioNet.

---

## 3. Findings left as-is

**None of the fourteen findings was left wholly unaddressed.** Every finding produced at least a caveat.

Two findings were addressed by annotation rather than by altering the value, and both are recorded above as changes to `source_caveats` rather than to the slot in question:

- **`conforms_to` / `conforms_to_standard`** (§2.4): the values are unchanged in the reconciled record. `conforms_to` still reads "Brain Imaging Data Structure (BIDS) v1.9.0" and `conforms_to_standard` still lists `BIDS`. Only the scoping caveat is new.
- **`splits`** (§2.7): the slot survives with one entry rather than being removed. Comparing the two records, `splits[0].split_details` changed text; the slot itself is retained.

---

## 4. Changes to the core record

The core record was regenerated by projection from the reconciled full record. Every change above that touches a slot the core schema declares is reflected there:

- `description`, `source_caveats`, `subpopulations[1]`, `purposes`, `tasks[1]`, `prohibited_uses`, `creators`, `cleaning_strategies`, `machine_annotation_tools`, `preprocessing_strategies`, `distribution_dates`, `errata`, `extension_mechanism`, `regulatory_restrictions` — all projected in their reconciled form.
- `data_protection_impacts` was removed from the core record as it was from the full one.
- `distributions` — the core's projection of `file_collections` — gained eight new entries corresponding to the newly structured phenotype and metadata File objects, and the two parent collection descriptions were updated to their trimmed form.

Two divergences are structural rather than substantive:

- **`subsets`** is not declared on `CoreDataset`; the five new subset objects appear only in the full record.
- **`splits`**, `relationships`, `variables`, `citation`, `consent_revocations`, `collection_notifications`, `collection_consents`, `participant_privacy`, `participant_compensation`, `direct_collection`, `third_party_sharing` are likewise full-only and were not projected.

The core header block carries `# Phase 4 reconciliation: completed`, now accurate.

---

## 5. Referent

Unchanged and consistent across both records: the Bridge2AI-Voice **adult** dataset as published on PhysioNet at version 3.1.0 (1 May 2026). The pediatric release remains confined to `related_datasets`. The superseded 3.0.0 page was not used to settle any value.

---

## Dispositions

| slot | disposition | record | reason |
|---|---|---|---|
| `description` | changed | both | Five-cohort enumeration corrected: pediatric category restored, controls stated separately as an additional recruitment group rather than one of the five. |
| `source_caveats` | changed | both | Four paragraphs added: target-size disagreement (10,000 vs 30,000), the additional 50-plus contributors displaced from `creators`, BIDS scoping, HIPAA-coverage tension between documentation and DUA. |
| `purposes` | changed | both | New entry added for the 10,000-voice documentation target; `source_caveats` added to both the new entry and the existing 30,000 entry. |
| `tasks[1]` | changed | both | Interpolated reference to the companion pediatric release replaced with the healthsheet's own wording. |
| `prohibited_uses` | changed | both | All four entries restructured: prohibition moved to `notes`, `prohibition_reason` now carries the reason the bundle supplies. |
| `creators` | changed | both | Sixteenth entry naming no entity removed; its content relocated to dataset-level `source_caveats`. Fifteen named lead investigators retained. |
| `subpopulations[1].identification` | changed | both | Same taxonomy correction as `description`: the five-with-controls enumeration replaced with a description of cohort assignment. |
| `subsets` | added | full | Five `DataSubset` objects added, one per cohort partition the release ships as per-condition diagnosis tables. Not declared on `CoreDataset`. |
| `splits[0].split_details` | changed | full | Leading absence-statement dropped; substantive guidance on user-created splits retained. Full-only slot. |
| `cleaning_strategies` | changed | both | Absence-stating entry removed as a standalone object; healthsheet denial preserved as `notes` on the surviving audit-protocol entry. |
| `data_protection_impacts` | removed | both | Single entry stated only that no impact assessment was conducted; recorded an absence rather than answering the field. |
| `machine_annotation_tools` | changed | both | b2aiprep and SenseLab removed from `tools` and `tool_descriptions`; they are preprocessing toolkits, not annotation tools. |
| `preprocessing_strategies` | changed | both | Ninth entry added recording b2aiprep and SenseLab, receiving the content displaced from `machine_annotation_tools`. |
| `conforms_to` | retained | both | Attested by a tier-2 source about a distribution of this dataset; scoping recorded in dataset-level `source_caveats` rather than removing an attested fact. |
| `conforms_to_standard` | retained | both | Retained with `conforms_to` for the same reason; both scoped by the new caveat. |
| `regulatory_restrictions.hipaa_compliant` | removed | both | Two equally ranked tier-2 sources characterize HIPAA coverage differently for different distributions; no enum member expresses an unresolved conflict. |
| `regulatory_restrictions.source_caveats` | added | both | Records why `hipaa_compliant` is unpopulated and what each source states. |
| `distribution_dates[0].release_dates` | changed | both | Version 1.0 (end of November 2024, Health Data Nexus) prepended, resolving the inconsistency with `version_access.versions_available`. |
| `errata[0].erratum_url` | removed | both | Held the release landing page, not an erratum document; the bundle supplies no erratum URL. |
| `errata[2].source_caveats` | changed | both | Extended to state that corrections were transcribed from the PhysioNet Release Notes and that no separate erratum document exists. |
| `file_collections[1].resources` | added | both | Six File objects added for the phenotype subfolders; inventory detail moved out of the collection `description`. Projected into core `distributions`. |
| `file_collections[2].resources` | added | both | Two File objects added for the metadata Parquet file and its dictionary. Projected into core `distributions`. |
| `extension_mechanism.extension_details` | changed | both | Platform-specific wording restored ("on the Health Data Nexus"). |
| `extension_mechanism.source_caveats` | added | both | Notes that the bundle does not state whether an equivalent derivative-dataset route exists on PhysioNet. |