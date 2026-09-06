# Phase 4 Reconciliation Report — AI_READI

## Scope

The Phase 3 audit returned seventeen findings against the full record: four medium, thirteen low. No high-severity defects, no evidence of prior-D4D factual reuse, and no arithmetic or identifier defects. Phase 4 reviewed each finding against the declared bundle and applied changes to the full record, then re-projected the affected slots into the core record. Fifteen findings produced changes; two were left as-is with reasons given below.

---

## Findings acted on

### 1. `known_biases[2].mitigation_strategy` — unsupported attribution of practice (medium)

The original read: "Recruitment materials were tailored and a personalized, participatory approach was used; if sample balancing on race and ethnicity emerges as a challenge, new recruitment strategies will be implemented to overcome the imbalance." The BMJ Open protocol paper attributes tailored materials and the personalized, participatory approach to strategies "Researchers have identified" in the literature — it does not state AI-READI adopted them.

**Changed** in both records. The mitigation now carries only the conditional clause the bundle supports, framed in the source's own voice: "The protocol paper states that if sample balancing on race and ethnicity emerges as a challenge in AI-READI, new recruitment strategies will be implemented to overcome the imbalance." A new sibling `source_caveats` records the literature-derived strategies and states explicitly that the source attributes them to other researchers, so they are not recorded as mitigations applied here.

### 2. `sensitive_elements` — unrecorded tier-1 conflict (medium)

The original carried a single entry with `sensitive_elements_present: false` on the healthsheet answer alone. The RO-Crate — tier 1, equal rank to the FAIRhub API that carries the healthsheet — enumerates six categories under `rai:personalSensitiveInformation`. Equal rank means the ranking cannot decide, and the uniform rule requires representing what the evidence states rather than selecting one.

**Changed** in both records. `sensitive_elements` is now a two-entry list. Entry 0 keeps the healthsheet answer, with its `sensitivity_details` re-attributed ("The healthsheet states that...") and a new `source_caveats` naming the conflict and explaining that both are represented. Entry 1 is new: `sensitive_elements_present: true` with the RO-Crate's six categories enumerated verbatim (EHR, Wearable Monitoring, ECG, Environmental Sensor, Continuous glucose monitor, Wearable accelerometer) and a `source_caveats` stating that neither source is preferred. The dataset-level `source_caveats` also gained a sentence recording this disagreement.

### 3. `prohibited_uses[*]` — field mismatch (medium)

Six of seven entries placed the prohibition text in `prohibition_reason`, which asks for the reason the use is prohibited.

**Changed** in both records. All seven entries were rewritten: `prohibition_reason` now carries the rationale the license or healthsheet supplies (participant protection, reserved IP and the separate publication license, tracing an unauthorized release, confining storage to environments the license's security standards reach), and a new sibling `notes` on each entry carries the prohibition text itself. Entry 0's reason was tightened from "Making clinical treatment decisions based on the Data is prohibited, as the Data are intended solely as a research resource" to just the reason clause.

### 4. `related_datasets[2].target_dataset` — prose in a required scalar reference (medium)

The value was the phrase "AI-READI mini-subset of version 3.0.0". The bundle attests the child only as FAIRhub API `data.child = 4` and the page note about a smaller version for pipeline development; no DOI or URL is stated.

**Changed** in both records: the entry was removed from `related_datasets`, which now holds two entries. The mini-subset facts were moved into the dataset-level `notes`, which records the internal child identifier 4, the page note verbatim, the v3 documentation coverage, and the explicit statement that no DOI or resolvable identifier is stated in the sources, so it is not recorded as a related dataset.

### 5. `distribution_formats[4]` — empty entry carrying schema commentary (low)

**Changed** in both records: the entry was removed, leaving four DistributionFormat entries. The DICOM content moved to a `source_caveats` on the `distribution_formats` slot in the full record, which records that FAIRhub declares `application/dicom`, that it is the format of the four imaging directories holding most of the release, and that no DICOM value exists in the schema's enumerations — with the conformance recorded instead in `conforms_to`, `conforms_to_standard` and the four imaging file collections. The core record simply carries the four entries without the caveat.

### 6. `external_resources[4]` — unrecorded tier-1/tier-3 title conflict (low)

**Changed** in both records. The RO-Crate's (tier-1) title form now appears in the citation — "AI-READI: rethinking data collection, preparation and sharing for propelling AI-based discoveries in diabetes research and beyond" — and a new `source_caveats` records that the article as published and the BMJ Open reference list title it differently, giving that form verbatim.

### 7. `maintainers[0].role` — unsupported enum mapping (low)

**Changed** in both records: `academic_institution` → `other`, with a new `source_caveats` explaining that the sources name only "the AI-READI team", a multi-institution consortium hosted on the FAIRhub platform, and that no enumerated value names that arrangement.

### 8. `regulatory_restrictions.hipaa_compliant` — undeclared mapping (low)

**Changed** in both records: the slot was removed. The underlying HIPAA statements were preserved verbatim in `other_compliance`, which now quotes the FAIRhub `deIdentHIPAA` flag and the detail string. The sibling `source_caveats` gained a sentence stating that no source asserts a HIPAA compliance status, so the slot is not populated.

### 9. `creators[0].affiliations[0]` — relationship not attested (low)

**Changed** in both records: the `affiliations` list was removed from the Creator. The `principal_investigator.affiliation` retains ROR:01yc7t268 (which FAIRhub does state as the PI's affiliation). The Creator's `source_caveats` now states explicitly that no affiliation is recorded for the consortium, because the sources attest WashU as managing organization, lead sponsor and Licensor — none of which is an affiliation.

### 10. Entity names conflated with source commentary in `notes` (low)

**Changed** in both records at three sites. `creators[0].notes` is now "AI-READI Consortium." with the commentary moved to `source_caveats`. `creators[0].principal_investigator.notes` is now "Aaron Lee, MD." with the FAIRhub/RO-Crate descriptions moved to a new `source_caveats` on the Person. `data_governance.accountable_organization.notes` is now "Washington University in St. Louis." with its commentary in a new `source_caveats`; `data_governance.committee_contact.notes` is now "Aaron Lee, MD." likewise.

### 11. `ip_restrictions.restrictions[0]` — trailing pointer (low)

**Changed** in both records. The single string was split into two: one on title and reserved rights, one on the publication limits. The trailing sentence pointing at the healthsheet moved to a new `source_caveats` on `ip_restrictions`, which notes the healthsheet answers by reference to the license and that the substantive terms are taken from the license text.

### 12. `preprocessing_strategies[7]` — watermarking is not preprocessing (low)

**Changed** in both records: the entry was removed, leaving seven. The fact remains at `participant_privacy.privacy_techniques` and `regulatory_restrictions.regulatory_restrictions`, where it answers the field asked.

### 13. `intended_uses[2]` — describes a use of the methodology, not the data (low)

**Changed** in both records: the entry was removed, leaving two. The blueprint, Zenodo community and GitHub organization remain recorded in `purposes[2]` and in `external_resources`.

### 14. `future_use_impacts[2].impact_details` — second half states design mitigations (low)

**Changed** in both records: the trailing clauses about multiple devices and documented device make/model were removed. The entry now states only the generalization-limiting factors. The device facts remain in `collection_mechanisms`.

### 15. `extension_mechanism` — defensible omission, but the evidence supports populating it (low)

**Added** to both records. The healthsheet answers the question directly and a closed contribution model is a substantive answer: `extension_details` now reads "There is currently no mechanism for others to extend or augment the AI-READI dataset outside of those who are involved in the project."

### 16. `subpopulations[1]` / `subpopulations[2]` — structurally contradictory (low)

**Changed** in both records. Both entries retain `subpopulation_elements_present: false`; the `distribution` slot was removed from each, and the counts moved into `notes`, framed as a documentation-level summary published in the README split table rather than a distribution present in the released data. Each `identification` now states explicitly that the variable is not released at participant level and is held under controlled access. `subpopulations[0]` (diabetes group) and `subpopulations[3]` (age) are unchanged: both are `true` and their distributions are consistent.

### 17. `description` / `version_access.version_details` — unrecorded tier-2 conflict (low)

**Changed** in both records at `version_access`. The record continues to follow the tier-1 figures, which is correct under the ranking; a new `source_caveats` on `version_access` records the v3 documentation page's "pilot study phase" statement verbatim and states that the tier-1 figures are used. The dataset-level `source_caveats` gained a matching sentence. `description` itself is unchanged — the tier-1 values it carries are correct and the conflict is now recorded twice elsewhere.

---

## Findings left as-is

Two findings produced no change beyond what is described above:

- **`description`** (finding 17, first half). The audit asked that the docs-v3 conflict be recorded; it is, at `version_access.source_caveats` and at the dataset-level `source_caveats`. The `description` text itself was correct and stays as written, since restating the caveat inside a description would duplicate a trust annotation into content.
- **`subpopulations[0]` and `subpopulations[3]`**. The audit named only entries 1 and 2; entries 0 and 3 are internally consistent and unchanged.

---

## Verified sound, not touched

The audit's summary confirmed and re-checking bore out: the nine `file_collections` counts and byte sizes match the FAIRhub API exactly; the split-table counts in `splits` and `subpopulations` reconcile to the stated totals; the two derived figures (root metadata `file_count: 9`, and the 419,614-byte residual) are correctly computed, correctly labelled as this record's own arithmetic, and carry their inputs in `file_collections[9].source_caveats`. All identifiers (ROR:01yc7t268, ORCID:0000-0002-7452-1648, the three FAIRhub DOIs, the grant numbers) are attested in the bundle. Forward-looking statements — the 4,000-participant target, the year-4 follow-up, the tribal consultation, the biorepository, the annual re-release cadence — remain framed in their sources' tense and outside the current-state slots. `data_protection_impacts`, `errata`, `labeling_strategies` and `annotation_analyses` remain omitted, since the only available answer would have been a statement of absence.

## Cross-record consistency

Every change above was applied to both records where the core schema declares the slot. `distribution_formats`'s `source_caveats` and the DICOM commentary appear only in the full record, since the core record's four entries carry no slot-level caveat. The `id`, referent (FAIRhub version 3.0.0, DOI 10.60775/fairhub.3), and all header lines are unchanged.

---

## Dispositions

| slot | disposition | record | reason |
|---|---|---|---|
| `known_biases[2].mitigation_strategy` | changed | both | Removed the assertion that AI-READI tailored materials and used a participatory approach; the protocol paper attributes those to the literature, not to this project. Retained only the conditional clause the source states. |
| `known_biases[2].source_caveats` | added | both | Records the literature-derived strategies and states the source attributes them to other researchers, so they are not recorded as mitigations applied here. |
| `sensitive_elements[0].sensitivity_details` | changed | both | Re-attributed to the healthsheet, so the entry reads as one source's answer rather than as an unqualified fact. |
| `sensitive_elements[0].source_caveats` | added | both | Records the equal-rank tier-1 conflict between the healthsheet answer and the RO-Crate enumeration, and states that both are represented. |
| `sensitive_elements[1]` | added | both | Represents the RO-Crate's `rai:personalSensitiveInformation` enumeration, which the ranking cannot subordinate to the healthsheet answer. |
| `prohibited_uses[0..6].prohibition_reason` | changed | both | Each now states the rationale the license or healthsheet gives, rather than restating the prohibition, which is what the field asks for. |
| `prohibited_uses[0..6].notes` | added | both | Carries the prohibition text displaced from `prohibition_reason`. |
| `related_datasets[2]` | removed | both | `target_dataset` is a required scalar reference and held prose; the bundle states no DOI or URL for the mini-subset. |
| `notes` | changed | both | Absorbed the mini-subset facts (FAIRhub child identifier 4, the page note, v3 documentation coverage) with an explicit statement that no resolvable identifier is stated. |
| `distribution_formats[4]` | removed | both | An entry with neither `format` nor `media_type`, carrying only commentary about the schema's enumerations. |
| `distribution_formats` (`source_caveats`) | added | full | Records the DICOM declaration, its scope across the four imaging directories, and why no DistributionFormat entry represents it. |
| `external_resources[4].external_resources` | changed | both | Adopted the tier-1 RO-Crate title form for the Nature Metabolism DOI, per the source ranking. |
| `external_resources[4].source_caveats` | added | both | Records the competing title given by the article as published and by the BMJ Open reference list. |
| `maintainers[0].role` | changed | both | `academic_institution` was a mapping the bundle does not support; `other` fits a multi-institution consortium on a shared platform. |
| `maintainers[0].source_caveats` | added | both | Explains why `other` was selected over the named enum values. |
| `regulatory_restrictions.hipaa_compliant` | removed | both | No source asserts HIPAA compliance as a status; the value was this record's own undeclared mapping from a de-identification flag. |
| `regulatory_restrictions.other_compliance` | changed | both | Now carries the underlying FAIRhub HIPAA statements verbatim, displaced from the removed enum. |
| `regulatory_restrictions.source_caveats` | changed | both | Extended to state that no HIPAA compliance status is asserted and that `hipaa_compliant` is therefore unpopulated. |
| `creators[0].affiliations` | removed | both | WashU is attested as managing organization, lead sponsor and Licensor — none of which is an affiliation of the consortium. |
| `creators[0].notes` | changed | both | Reduced to the entity name; the descriptive commentary moved to `source_caveats`. |
| `creators[0].source_caveats` | changed | both | Absorbed the consortium description and now states explicitly why no affiliation is recorded. |
| `creators[0].principal_investigator.notes` | changed | both | Reduced to the person's name; source descriptions moved to a sibling caveat. |
| `creators[0].principal_investigator.source_caveats` | added | both | Carries the FAIRhub and RO-Crate descriptions of the PI and the affiliation conflict between them. |
| `data_governance.accountable_organization.notes` | changed | both | Reduced to the organization name; the FAIRhub/license roles moved to a sibling caveat. |
| `data_governance.accountable_organization.source_caveats` | added | both | Records the managing-organization, lead-sponsor and Licensor roles the sources attest. |
| `data_governance.committee_contact.notes` | changed | both | Reduced to the person's name. |
| `data_governance.committee_contact.source_caveats` | added | both | Records how FAIRhub describes this contact. |
| `ip_restrictions.restrictions` | changed | both | Split into two restriction statements and stripped of the trailing pointer to where the healthsheet's answer lives. |
| `ip_restrictions.source_caveats` | added | both | Records that the healthsheet answers by reference to the license and that the terms are taken from the license text. |
| `preprocessing_strategies[7]` | removed | both | Watermarking is a dissemination and security control, not preprocessing; already carried at `participant_privacy` and `regulatory_restrictions`. |
| `intended_uses[2]` | removed | both | Described reuse of the project's methodology and blueprint, not a use of this dataset. |
| `future_use_impacts[2].impact_details` | changed | both | Dropped the device-diversity and documentation clauses, which state design mitigations already carried at `collection_mechanisms`. |
| `extension_mechanism.extension_details` | added | both | The healthsheet answers the question directly; a closed contribution model is a substantive answer, not an absent one. |
| `subpopulations[1].identification` | changed | both | Now states that race/ethnicity is not released at participant level and is held under controlled access. |
| `subpopulations[1].distribution` | removed | both | Contradicted `subpopulation_elements_present: false`; the counts are a README summary, not a distribution in the released data. |
| `subpopulations[1].notes` | changed | both | Absorbed the counts, framed as a documentation-level summary. |
| `subpopulations[2].identification` | changed | both | Now states that sex is not released at participant level and is held under controlled access. |
| `subpopulations[2].distribution` | removed | both | Same contradiction as entry 1. |
| `subpopulations[2].notes` | changed | both | Absorbed the counts, framed as a documentation-level summary. |
| `version_access.source_caveats` | added | both | Records the tier-2 v3 documentation page's "pilot study phase" statement and that the tier-1 figures are used. |
| `source_caveats` | changed | both | Extended to record the docs-v3 participant-count conflict and the tier-1 disagreement over sensitive data. |
| `description` | retained | both | The audit asked that the docs-v3 conflict be recorded, not that the description change; the tier-1 values it carries are correct and the conflict is recorded at `version_access.source_caveats` and dataset-level `source_caveats`. |
| `subpopulations[0].distribution` | retained | both | Not questioned by the audit; `subpopulation_elements_present` is `true` here, so distribution and flag are consistent. |
| `subpopulations[3].distribution` | retained | both | Not questioned by the audit; `subpopulation_elements_present` is `true` here, so distribution and flag are consistent. |
| `file_collections[9].source_caveats` | retained | full | Verified sound: the derived count of 9 and the 419,614-byte residual are correctly computed, labelled as this record's arithmetic, and cite their inputs. |