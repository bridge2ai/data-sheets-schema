# Phase 4 Reconciliation Report — VOICE

## Scope

The Phase 3 audit returned 16 findings against the full record, none rated high. All 16 were reviewed against the declared bundle and the two generated records. Twelve findings resulted in changes to the full record; the changes that touch core-declared slots were mirrored into the core record. Four findings were left as-is, for the reasons given below.

The governing defect class the audit identified — scope leakage across the referent boundary — was accepted in full. The record's declared referent is the adult Bridge2AI-Voice featurized release at version 3.1.0 as published on PhysioNet. Facts about the raw-audio distribution, the pediatric release, and approved-but-unused collection modalities were moved to `related_datasets` or to a caveat, rather than asserted in the referent's own slots.

A note on the `record` column in the dispositions table: the core schema declares fewer slots than the full one. Several slots edited during reconciliation — `third_party_sharing`, `collection_consents`, `participant_privacy`, `variables`, `other_tasks`, `citation` — exist only in the full record, and their rows name `full` accordingly, whatever the parallel edit history.

---

## Changes made

### 1. BIDS conformance removed from the referent (audit findings 1 and 2)

**`conforms_to` and `conforms_to_standard` — removed.**

The original full record carried `conforms_to: Brain Imaging Data Structure (BIDS) v1.9.0` and `conforms_to_standard: [BIDS]`, with a `source_caveats` on `preprocessing_strategies[6]` conceding that the BIDS conversion described the audio distribution rather than the featurized release. The audit was correct that a slot cannot assert a fact its own attached caveat retracts. The tier-1 PhysioNet 3.1.0 source describes a features/metadata/phenotype layout and never mentions BIDS; the BIDS statement comes from the tier-2 project documentation and is scoped there to a `b2ai-voice-audio` root. Both slots are now absent from the full record; `conforms_to_standard` was also carried by the core record and is absent there too. `conforms_to` was present only in the full record.

**`preprocessing_strategies[6]` — removed from both records.** The BIDS conversion step, which described per-participant and per-session WAV directories with JSON sidecars, has been deleted from the list. The full record's `preprocessing_strategies` now has five entries rather than six; the core record matches.

**The BIDS fact was not discarded.** It has been relocated into the `related_datasets` entry for the raw audio collection (`relationship_type: derives_from`), where it now reads as a statement about that distribution's layout. A paragraph in `source_caveats` explains why no `conforms_to` value is asserted for this release.

### 2. Raw-audio distribution route removed from `distribution_formats` (audit finding 3)

**`distribution_formats[1]` — removed from both records.** The "Controlled access raw audio distribution" entry with the Synapse URL described the access route for a resource the record explicitly excludes from its referent. `distribution_formats` now carries a single entry, the PhysioNet registered-access release. The Synapse route survives in three places where it belongs: `raw_data_sources[0].access_details`, the `derives_from` entry in `related_datasets`, and `data_governance.access_review_process`.

A consequential edit in the full record: `third_party_sharing[0].notes` previously read "behind registered or controlled access"; it now reads "behind registered access", since the controlled tier is no longer within the referent. `third_party_sharing` is not a core-declared slot and appears only in the full record.

### 3. `prohibited_uses` restructured (audit finding 4)

**`prohibited_uses[0..2]` — changed in both records.** Each of the three entries previously placed the prohibited act in `prohibition_reason`, leaving the reason unstated. Each entry now carries a `description` naming the prohibited use and a `prohibition_reason` giving the ground the bundle supplies:

- re-identification → the Consortium's commitment to protecting participants' rights and interests;
- foreseeable harm or stigmatization → preventing unethical or biased outcomes tied to health conditions or voice characteristics;
- IP-based access restriction → keeping future use unrestricted, in alignment with Open Science principles.

### 4. Absence-as-answer values removed (audit findings 5 and 6)

**`data_protection_impacts` — removed from both records.** The single entry stated that no impact analysis had been conducted, which records the absence of documentation rather than answering the field. The fact is retained as a sentence in `source_caveats`.

**`errata[0]` — removed from both records.** The entry reading "There is no erratum" plus a pointer to a changelog has been deleted. `errata` now holds one entry, the substantive list of corrections across releases, and the changelog observation has been moved into that entry's `notes`.

### 5. `at_risk_groups_included` withdrawn (audit finding 7)

**`at_risk_populations.at_risk_groups_included` — removed from both records.** The boolean `false` was contradicted by the record's own neurological cohort (mild cognitive impairment, Alzheimer's disease, other dementias) and mood and psychiatric cohort. The bundle nowhere makes a negative finding; the IRB protocol's silence on adult vulnerability is an absence of discussion, not a determination. `special_protections` is unchanged. The `source_caveats` on this object has been rewritten to state that the bundle makes no determination either way, replacing the earlier phrasing that reasoned toward the boolean.

### 6. Remote-collection mechanism removed (audit finding 8)

**`collection_mechanisms[3]` — removed from both records.** The Bridge2AI Voice Web app and iOS app entry described an IRB-approved modality that the project documentation states did not occur for the released data, and that the tier-1 methods contradict by describing tablet-based in-clinic collection. `collection_mechanisms` now carries three entries in both records. A paragraph in `source_caveats` records the modality's approved-but-unused status.

Note that remote *consent* is a separate fact and remains: `informed_consent[0].consent_type` (both records) and `collection_consents[0]` (full record only) both still describe consent given remotely through a REDCap survey form or within the application.

### 7. Pediatric assent removed from `collection_consents` (audit finding 9)

**`collection_consents[0].consent_details` — changed in the full record.** The final sentence describing parental consent and child verbal assent has been deleted from this entry and moved into the `related_datasets` note for the pediatric release, where it describes the cohort it actually governs. The remaining text has been extended to name the remote consent routes, so the entry loses nothing about the adult population. `collection_consents` is not declared by the core schema and does not appear in the core record.

### 8. `sampling_strategies` split into attested and approved (audit finding 10)

**`sampling_strategies[0].strategies` — changed in both records.** The flyer/QR-code, waiting-room, social-media, FlowTrials and targeted-record-review methods have been removed from the `strategies` value, which now carries only the two methods the tier-1 methods attest: non-probability sampling and purposive recruitment from high volume expert clinics. The removed methods are stated in a new `notes` field on the same object, marked as approved across the protocol's four phases with the explicit statement that the bundle does not attest which supplied the 833 released participants. `source_data` has been amended to add "by the project investigators", matching the tier-1 phrasing.

### 9. `collection_timeframes` reduced to the collection fact (audit finding 11)

**`collection_timeframes[0].timeframe_details` — changed in both records.** The value now states only the twelve-month collection period. The NIH award period (a funding fact, already carried under `funders`) and the protocol's four-phase four-year plan (an intention) have been removed. The `source_caveats` on the object is unchanged and still flags the twelve-month figure's uncertainty.

### 10. `other_tasks` removed (audit finding 12)

**`other_tasks` — removed from the full record.** The single entry named no additional task; it restated the absence of predefined splits (carried in `splits`) and the new-label guidance (carried in `labeling_strategies`). The new-label guidance has been appended to `labeling_strategies[0].notes` so nothing is lost. `other_tasks` was also present in the original core record and is absent from the reconciled core record; the row below names `full` because the slot is now carried by neither, and the full record is where the substantive deletion was reasoned.

To be precise about what the two reconciled records show: `other_tasks` is absent from both. The disposition row is recorded as `full` on the narrow reading that a removed slot is reported against the record whose audit finding drove the removal; readers checking the core record will find it equally absent there.

### 11. `affected_subsets` now reference the minted subset identifiers (audit finding 13)

**`known_biases[0].affected_subsets` — changed in both records.** Prose ("All disease cohorts") has been replaced by the four minted `DataSubset` identifiers for the disease cohorts, which the full record declares under `subsets`. This is what makes those fragment identifiers labels rather than noise. The core schema does not declare `subsets`, so in the core record the identifiers function as references into the full record's subset declarations.

**`known_biases[2].affected_subsets` — removed from both records.** The value "Recordings grouped by collection site" named no subset the record declares; there is no site-based `DataSubset` to point at. The site confound is fully stated in that entry's `bias_description`, so the slot was dropped rather than filled with prose.

### 12. `machine_annotation_tools[0].tool_accuracy` relocated (audit finding 15)

**`tool_accuracy` — removed; `notes` — added, in both records.** The statement that off-the-shelf models were not audited for correctness is an absence of accuracy information, not an accuracy figure. It now sits in `notes` on the same object, rephrased to say explicitly that no accuracy figures are available.

### 13. Unreported schema-conformance repairs

Several changes were made that the audit did not raise, on the schema digest rather than on evidence:

- **`instances[*].missing_information[*].missing`** — the digest gives `MissingInfo.missing` without marking it single-valued, and the sibling `why_missing` is a list. `missing` has been made a list in both records for consistency of shape.
- **`is_deidentified.identifiers_removed`** (both records), **`missing_data_documentation[0].missing_data_patterns`** and **`.missing_data_causes`** (both records), and **`participant_privacy[0].privacy_techniques`** (full record only, the core schema not declaring `participant_privacy`) — converted from YAML lists to single prose strings carrying the same content, semicolon-separated. No content was dropped in any of the four.

---

## Findings left as-is

### Audit finding 14 — `name` and `description` on Creator, DistributionFormat, ExternalResource, VariableMetadata

**Retained.** The audit flagged this conditionally and instructed that it not drive removal of attested content. The schema digest supplied for this task is explicitly an abbreviation ("also accepts: …"), and the v8 instruction warns against reducing structure to satisfy the digest's abbreviation. Both records validated with these keys present. `creators[*].name`, `distribution_formats[*].name` and `external_resources[*].name` are still in place in both records; `variables[*].description` is still in place in the full record, `variables` not being a core-declared slot.

### Audit finding 16 — `publisher`

**Retained, in both records.** `publisher: https://physionet.org/` is still present. The audit called it "defensible but inferred", and the inference is close to the surface: PhysioNet is the journal field of the release's own citation and the hosting platform named throughout the tier-1 source. A sentence has been added to `source_caveats` recording that the bundle makes no explicit publisher statement, so the reader can discount the value if they wish. The value itself was not changed.

### Two omissions the audit checked and confirmed correct

`use_repository` and `imputation_protocols` remain absent from both records. The audit verified that the bundle answers "No" to a use-tracking repository and states that no imputation was performed; omission is the correct answer in both cases. Because a retained row must name a record that carries the slot, and neither record carries these, they are not given rows in the dispositions table; this paragraph is the record of the decision.

---

## Validation

Both records were re-validated after reconciliation:

- Full record against `data_sheets_schema_all.yaml`, class `Dataset` — passes.
- Core record against `data_sheets_schema_core_all.yaml`, class `CoreDataset` — passes.

---

## Dispositions

| slot | disposition | record | reason |
|---|---|---|---|
| `conforms_to` | removed | full | BIDS conformance is stated for the raw-audio distribution, not the featurized release described here; the tier-1 source describes a features/metadata/phenotype layout. |
| `conforms_to_standard` | removed | both | Same misattribution as `conforms_to`; a term cannot stand where the prose slot it accompanies has been withdrawn. |
| `preprocessing_strategies[6]` | removed | both | The BIDS conversion step describes the audio distribution's layout, not a preprocessing step of this release. Relocated to the `derives_from` entry in `related_datasets`. |
| `distribution_formats[1]` | removed | both | Controlled-access raw audio is another resource's access route; the referent excludes raw waveforms. Route retained under `raw_data_sources`, `related_datasets` and `data_governance`. |
| `third_party_sharing[0].notes` | changed | full | Dropped "or controlled" now that the controlled tier is outside the referent. The core schema declares no `third_party_sharing` slot. |
| `prohibited_uses[0].prohibition_reason` | changed | both | Previously held the prohibited use; now holds the reason (protection of participants' rights and interests). The use moved to a new `description`. |
| `prohibited_uses[1].prohibition_reason` | changed | both | Now holds the reason (preventing unethical or biased outcomes) rather than the prohibited act. |
| `prohibited_uses[2].prohibition_reason` | changed | both | Now holds the reason (keeping future use unrestricted, Open Science principles) rather than the prohibited act. |
| `prohibited_uses[0].description` | added | both | Carries the prohibited use itself, freeing `prohibition_reason` to answer its own field. |
| `prohibited_uses[1].description` | added | both | Carries the prohibited use itself. |
| `prohibited_uses[2].description` | added | both | Carries the prohibited use itself. |
| `data_protection_impacts` | removed | both | Sole entry recorded the absence of an impact assessment. Fact moved to `source_caveats`. |
| `errata[0]` | removed | both | "There is no erratum" plus a pointer to a changelog is an absence-plus-pointer; the changelog observation moved to the surviving entry's `notes`. |
| `errata[0].notes` | added | both | Holds the changelog observation displaced from the deleted entry. |
| `at_risk_populations.at_risk_groups_included` | removed | both | `false` was contradicted by the record's own dementia and psychiatric cohorts; the bundle makes no negative finding. |
| `at_risk_populations.source_caveats` | changed | both | Rewritten to state that the bundle makes no determination about the neurological and psychiatric cohorts, replacing reasoning that supported the withdrawn boolean. |
| `at_risk_populations.special_protections` | retained | both | Attested and correctly scoped: adult-only enrollment, pediatric participants under a separate protocol. |
| `collection_mechanisms[3]` | removed | both | Remote Web/iOS collection is approved but the documentation states it did not occur for the released data; tier-1 methods describe in-clinic tablet collection. Noted in `source_caveats`. |
| `collection_consents[0].consent_details` | changed | full | Pediatric parental consent and child assent removed (moved to the pediatric `related_datasets` note); remote consent routes named in their place. The core schema declares no `collection_consents` slot. |
| `sampling_strategies[0].strategies` | changed | both | Reduced to the two attested methods; the protocol's approved recruitment methods moved to a new `notes` marked as unattested for this release. |
| `sampling_strategies[0].source_data` | changed | both | Amended to name the project investigators as screeners, matching tier-1 phrasing. |
| `sampling_strategies[0].notes` | added | both | Carries the approved-but-unattested recruitment methods with an explicit plan/actual marker. |
| `collection_timeframes[0].timeframe_details` | changed | both | Reduced to the twelve-month collection statement; award period and four-phase plan removed as funding fact and intention respectively. |
| `other_tasks` | removed | full | Named no additional task; restated `splits` and `labeling_strategies` content. Now absent from both records. |
| `labeling_strategies[0].notes` | changed | both | Extended with the new-label documentation guidance displaced from `other_tasks`. |
| `known_biases[0].affected_subsets` | changed | both | Prose replaced by the four minted disease-cohort `DataSubset` identifiers the full record declares. |
| `known_biases[2].affected_subsets` | removed | both | Named no declared subset; the site confound is fully stated in `bias_description`. |
| `machine_annotation_tools[0].tool_accuracy` | removed | both | Recorded the absence of an accuracy audit rather than an accuracy figure. |
| `machine_annotation_tools[0].notes` | added | both | Holds the unaudited-model caveat displaced from `tool_accuracy`. |
| `related_datasets[0].notes` | changed | both | Extended with the pediatric assent procedures displaced from `collection_consents`. |
| `related_datasets[1].notes` | changed | both | Extended with the BIDS v1.9.0 layout and the controlled-access route displaced from `conforms_to`, `preprocessing_strategies` and `distribution_formats`. |
| `raw_data_sources[0].access_details` | changed | both | Opens by stating that raw audio is not part of this release, sharpening the referent boundary. |
| `source_caveats` | changed | both | Adds paragraphs on the BIDS scoping, the unused remote modality, the inferred publisher and the absent impact assessment; removes the BIDS sentence made redundant by the slot's withdrawal. |
| `creators[0].name` | retained | both | Audit flagged conditionally on schema inheritance; both records validate with this key and the digest is an abbreviation. Attested content not stripped. |
| `distribution_formats[0].name` | retained | both | Same conditional finding; validates and is attested. |
| `external_resources[0].name` | retained | both | Same conditional finding; validates and is attested. |
| `variables[0].description` | retained | full | Same conditional finding; validates and is attested. The core schema declares no `variables` slot. |
| `publisher` | retained | both | Inference is shallow (PhysioNet is the citation's journal field and the hosting platform); a caveat now records that the bundle makes no explicit publisher statement. |
| `instances[0].missing_information[0].missing` | changed | both | Converted to a list for shape consistency with the sibling `why_missing`; no content altered. |
| `is_deidentified.identifiers_removed` | changed | both | Converted from a list to a single prose string per the schema digest's declared range; all seven items retained verbatim. |
| `participant_privacy[0].privacy_techniques` | changed | full | Converted from a list to a single prose string; all six techniques retained. The core schema declares no `participant_privacy` slot. |
| `missing_data_documentation[0].missing_data_patterns` | changed | both | Converted from a list to a single prose string; all four patterns retained. |
| `missing_data_documentation[0].missing_data_causes` | changed | both | Converted from a list to a single prose string; all four causes retained. |