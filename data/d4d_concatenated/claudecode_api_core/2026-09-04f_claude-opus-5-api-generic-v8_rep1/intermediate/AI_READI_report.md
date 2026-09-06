# Reconciliation Report — AI_READI

Version label: `2026-09-04f_claude-opus-5-api-generic-v8_rep1`
Records reconciled: full (`AI_READI_d4d.yaml`) and core (`AI_READI_d4d_core.yaml`)

## What the audit found

The Phase 3 audit returned seventeen findings against the full record: four medium and thirteen low, with no high-severity defects and no evidence of prior-D4D factual reuse. The audit separately verified as sound the nine `file_collections` file counts and byte sizes, the split-table arithmetic, both derived figures (the root metadata `file_count` of 9 and the 419,614-byte residual, each correctly labeled as this record's own computation with its inputs named), and every identifier in the record as attested by the bundle.

The four medium findings were: an unsupported attribution of practice in `known_biases[2].mitigation_strategy`; an unrecorded tier-1 conflict between the healthsheet's `sensitive_elements_present: false` and the RO-Crate's `rai:personalSensitiveInformation` enumeration; six `prohibited_uses` entries carrying the prohibition text rather than the reason; and a prose value in the scalar-ranged, required `related_datasets[2].target_dataset`.

The thirteen low findings clustered into three patterns: enum values inferred rather than attested; values answering a neighbouring field or drifting from the slot's declared subject; and unrecorded lower-order source disagreements.

## What was changed, and why

### Medium findings

**`known_biases[2].mitigation_strategy` (full and core) — changed.** The original read "Recruitment materials were tailored and a personalized, participatory approach was used; if sample balancing on race and ethnicity emerges as a challenge, new recruitment strategies will be implemented to overcome the imbalance." The BMJ Open protocol paper attributes tailoring of printed materials and the personalized, participatory approach to strategies *researchers have identified* in the literature, not to AI-READI's own practice. The reconciled value keeps only the conditional clause the source supports, in the source's own tense: "The protocol paper states that if sample balancing on race and ethnicity emerges as a challenge in AI-READI, new recruitment strategies will be implemented to overcome the imbalance." A new `source_caveats` sibling on the same entry records the literature attribution and why it is not carried as an applied mitigation.

**`sensitive_elements` (full and core) — changed, with a second entry added.** The original carried a single entry asserting `sensitive_elements_present: false` on the healthsheet answer alone. The RO-Crate, a tier-1 source of equal rank, enumerates six categories under `rai:personalSensitiveInformation` for this same release. The ranking cannot settle a disagreement between equally ranked sources, so both are now represented: the first entry retains the healthsheet answer and gains a `source_caveats` naming the conflict; a second entry with `sensitive_elements_present: true` carries the RO-Crate's six categories verbatim, with its own `source_caveats` noting that neither source is preferred. The dataset-level `source_caveats` also gained a sentence recording this conflict.

**`prohibited_uses` (full and core) — changed.** All seven entries were restructured. Each now carries the *reason* in `prohibition_reason` and the prohibition text in `notes`. Entry 0 already had a reason and was tightened. The other six gained reasons drawn from the license: protection of Data Subjects' confidentiality and privacy; the license's security and secondary-sharing requirements for AI/ML reuse; the confinement of access to parties who have accepted the same obligations; the Licensor's retained title and reserved right to license separately for publication; the tracing function of the watermark; and the confinement of storage to environments covered by institutional controls or a HIPAA BAA.

**`related_datasets[2]` (full and core) — removed.** `target_dataset` is a required scalar reference and held the prose phrase "AI-READI mini-subset of version 3.0.0". The bundle attests the child only as the FAIRhub API `data.child = 4` and the page note "A smaller version is available for pipeline development"; no DOI or resolvable identifier is stated. The relationship was dropped and the substance moved into the dataset-level `notes`, which now records the child identifier, the page note and the v3.0.0 documentation coverage, and states explicitly that no identifier is available so the subset is not recorded as a related dataset.

### Low findings

**`distribution_formats[4]` (full and core) — removed.** The entry carried neither `format` nor `media_type`, only commentary that the schema enumerations contain no DICOM value. That is meta-commentary about the schema, not a distribution format. In the full record the substance moved to the `source_caveats` block that follows `distribution_formats`, which now records FAIRhub's declaration of `application/dicom`, its use across the four imaging directories, and where the conformance is recorded instead. The core record carries no dataset-level `source_caveats` at that position; the entry was simply removed there and the same facts remain available through `conforms_to`, `conforms_to_standard` and the four imaging distributions.

**`external_resources[4].external_resources` (full and core) — changed.** The Nature Metabolism title now follows the tier-1 RO-Crate's form ("rethinking data collection, preparation and sharing for propelling AI-based discoveries in diabetes research and beyond"), with a `source_caveats` recording that the published article and the BMJ Open reference list give a different title for the same DOI.

**`maintainers[0].role` (full and core) — changed.** `academic_institution` was replaced with `other`, with a `source_caveats` explaining that the sources name the maintaining body only as "the AI-READI team", a multi-institution consortium hosted on FAIRhub, and that no enumerated value names that arrangement.

**`regulatory_restrictions.hipaa_compliant` (full and core) — removed.** No source asserts HIPAA compliance as a status. The underlying statements — the `NoDeIdentification` type, the `deIdentHIPAA` flag and the verbatim FAIRhub detail — were moved into `other_compliance`, and `source_caveats` now records why the slot is unpopulated.

**`creators[0].affiliations` (full and core) — removed.** `ROR:01yc7t268` was recorded as an affiliation of the AI-READI Consortium, but the bundle attests Washington University in St. Louis as FAIRhub managing organization, study lead sponsor and license Licensor — none of which is an affiliation of the consortium. The slot was dropped; the `source_caveats` on the creator now states what the sources do attest and why no affiliation is recorded. The identifier remains where it is attested: on the principal investigator's `affiliation`, on `data_governance.accountable_organization` and on `data_governance.committee_contact.affiliation`.

**`creators[0].notes`, `creators[0].principal_investigator.notes`, `data_governance.accountable_organization.notes`, `data_governance.committee_contact.notes` (full and core) — changed.** Each `notes` now carries the entity name alone ("AI-READI Consortium.", "Aaron Lee, MD.", "Washington University in St. Louis."), with the source commentary moved to the sibling `source_caveats` on the same object.

**`ip_restrictions.restrictions` (full and core) — changed.** The single entry was split into two — the ownership term and the publication term — and the trailing pointer sentence ("The healthsheet states that questions … are answered by reference to the license") was moved to a new `source_caveats` on the object.

**`preprocessing_strategies[7]` (full and core) — removed.** The watermarking entry described a dissemination and security control rather than a preprocessing step. The same fact remains at `participant_privacy[0].privacy_techniques`, `participant_privacy[0].reidentification_risk` and `regulatory_restrictions.regulatory_restrictions[0]`.

**`intended_uses[2]` (full and core) — removed.** The "Methodological demonstration of AI-ready clinical data preparation" entry described reuse of the project's blueprint, standards, Zenodo community and GitHub organization. The Nature Metabolism source presents these as project outputs for other Data Generation Projects to follow, not as uses of this dataset. Those resources remain in `external_resources`, and the blueprint aim remains in `purposes[2]`, where it is a purpose of creation rather than a use of the data.

**`future_use_impacts[2].impact_details` (full and core) — changed.** The second half, which restated design mitigations already recorded under `collection_mechanisms`, was cut. Only the clause describing the generalization limitation remains.

**`extension_mechanism` (full and core) — added.** The healthsheet answers the question directly and in the negative: no mechanism exists for others to extend or augment the dataset outside the project. A closed contribution model is a substantive answer, distinguishable from an unanswered field, so `extension_details` now carries it.

**`version_access.source_caveats` (full and core) — added.** Records the tier-2 v3 documentation page's "pilot study phase" statement and its conflict with the tier-1 participant count and collection period, and states that the tier-1 figures are used. The dataset-level `source_caveats` gained a matching sentence.

## What was left as-is, and why

**`subpopulations[1]` and `subpopulations[2]` (low finding).** The audit observed that setting `subpopulation_elements_present: false` while populating `distribution` reads as contradictory. Rather than leave it, the reconciliation resolved it: `distribution` was removed from both entries, the "not released as a participant-level variable … held under controlled access" statement was folded into `identification`, and the aggregate counts were moved into `notes` framed explicitly as a documentation-level summary from the README split table rather than a distribution present in the released data. This is recorded below as `changed`, not `retained`.

Every other finding produced a change. No finding was dismissed.

Two things the audit verified were deliberately left untouched. The derived figures in `file_collections[9].source_caveats` — the count of 9 and the 419,614-byte residual — remain exactly as written, labeled as this record's own arithmetic with their inputs named and the disagreement with the stated totals recorded rather than resolved. And the forward-looking statements throughout (`notes` on the 4,000-participant target, the year-4 follow-up, the biorepository, the tribal consultation; `human_subject_research.notes`) remain in their sources' own tense and outside the current-state slots.

## Core-record consistency

Every change above was applied to the core record wherever the core schema declares the slot. The core record does not declare `distribution_formats`' sibling dataset-level `source_caveats` position used in the full record for the DICOM note, so that content was not carried across; the core record's own dataset-level `source_caveats` carries the same set of conflicts as the full record's, including the two added in this phase. `file_collections` projects to `distributions` in the core record and the byte figures are carried on `bytes`; no change in this phase touched those values.

Both records validated after reconciliation.

## Dispositions

| slot | disposition | record | reason |
|---|---|---|---|
| `known_biases[2].mitigation_strategy` | changed | both | Removed the clause asserting AI-READI tailored materials and used a participatory approach; the source attributes those to the literature, not to this project. Kept the conditional clause in the source's tense. |
| `known_biases[2].source_caveats` | added | both | Records the literature attribution and why it is not carried as an applied mitigation. |
| `sensitive_elements[0].source_caveats` | added | both | Records the equal-rank tier-1 disagreement between the healthsheet answer and the RO-Crate enumeration. |
| `sensitive_elements[1]` | added | both | Represents the RO-Crate's `rai:personalSensitiveInformation` enumeration, which the ranking cannot subordinate to the healthsheet answer. |
| `sensitive_elements[0].sensitive_elements_present` | retained | both | The healthsheet answer stands as one side of an unresolvable equal-rank conflict; both sides are now represented. |
| `prohibited_uses[0].prohibition_reason` | changed | both | Tightened to state the reason alone; the prohibition text moved to `notes`. |
| `prohibited_uses[1].prohibition_reason` | changed | both | Replaced the prohibition text with the reason: protection of Data Subjects' confidentiality and privacy. |
| `prohibited_uses[2].prohibition_reason` | changed | both | Replaced the prohibition text with the reason: the license's security and secondary-sharing requirements for AI/ML reuse. |
| `prohibited_uses[3].prohibition_reason` | changed | both | Replaced the prohibition text with the reason: access confined to parties bound by identical terms. |
| `prohibited_uses[4].prohibition_reason` | changed | both | Replaced the prohibition text with the reason: retained title and the Licensor's reserved publication licensing. |
| `prohibited_uses[5].prohibition_reason` | changed | both | Replaced the prohibition text with the reason: the watermark's tracing function. |
| `prohibited_uses[6].prohibition_reason` | changed | both | Replaced the prohibition text with the reason: storage confined to environments under the required security standards. |
| `related_datasets[2]` | removed | both | `target_dataset` is a required scalar reference and held prose; no identifier for the mini-subset is attested. Substance moved to dataset-level `notes`. |
| `notes` | changed | both | Added the mini-subset facts (child identifier 4, the page note, v3.0.0 documentation coverage) and the statement that no identifier is available for it. |
| `distribution_formats[4]` | removed | both | Carried neither `format` nor `media_type`, only commentary about the schema enumerations. |
| `distribution_formats` sibling `source_caveats` | added | full | Records FAIRhub's `application/dicom` declaration, its scope across the four imaging directories, and where the conformance is recorded instead. |
| `external_resources[4].external_resources` | changed | both | Adopted the tier-1 RO-Crate's title form for the Nature Metabolism DOI. |
| `external_resources[4].source_caveats` | added | both | Records that the published article and BMJ reference list title the same DOI differently. |
| `maintainers[0].role` | changed | both | `academic_institution` was an unsupported mapping; the sources name a multi-institution consortium, so `other`. |
| `maintainers[0].source_caveats` | added | both | Explains why no enumerated role value fits the attested arrangement. |
| `regulatory_restrictions.hipaa_compliant` | removed | both | No source asserts a HIPAA compliance status; the mapping was undeclared. |
| `regulatory_restrictions.other_compliance` | changed | both | Now carries the verbatim FAIRhub de-identification and HIPAA statements displaced from `hipaa_compliant`. |
| `regulatory_restrictions.source_caveats` | changed | both | Adds the reason `hipaa_compliant` is unpopulated. |
| `creators[0].affiliations` | removed | both | The sources attest WashU as managing organization, lead sponsor and Licensor — not as an affiliation of the consortium. |
| `creators[0].notes` | changed | both | Reduced to the entity name; commentary moved to `source_caveats`. |
| `creators[0].source_caveats` | changed | both | Now carries the consortium description and the statement of why no affiliation is recorded. |
| `creators[0].principal_investigator.notes` | changed | both | Reduced to "Aaron Lee, MD."; source commentary moved to the sibling `source_caveats`. |
| `creators[0].principal_investigator.source_caveats` | added | both | Carries the FAIRhub role description and the RO-Crate affiliation conflict. |
| `data_governance.accountable_organization.notes` | changed | both | Reduced to the organization name; commentary moved to `source_caveats`. |
| `data_governance.accountable_organization.source_caveats` | added | both | Records what FAIRhub and the license attest about this organization. |
| `data_governance.committee_contact.notes` | changed | both | Reduced to "Aaron Lee, MD."; commentary moved to `source_caveats`. |
| `data_governance.committee_contact.source_caveats` | added | both | Records the FAIRhub central-contact and study-official roles. |
| `ip_restrictions.restrictions` | changed | both | Split into two distinct restrictions; the trailing pointer sentence removed from the field. |
| `ip_restrictions.source_caveats` | added | both | Records that the healthsheet answers by reference to the license and that the terms are taken from the license text. |
| `preprocessing_strategies[7]` | removed | both | Watermarking is a dissemination and security control, already carried under `participant_privacy` and `regulatory_restrictions`. |
| `intended_uses[2]` | removed | both | Described reuse of the project's methodology and outputs, not a use of the data; the resources remain in `external_resources` and the aim in `purposes[2]`. |
| `future_use_impacts[2].impact_details` | changed | both | Removed the design-mitigation clause already recorded under `collection_mechanisms`; kept the generalization limitation. |
| `extension_mechanism` | added | both | The healthsheet answers the question in the negative; a closed contribution model is a substantive answer. |
| `version_access.source_caveats` | added | both | Records the tier-2 documentation page's "pilot study phase" statement and its conflict with the tier-1 figures. |
| `subpopulations[1].distribution` | removed | both | Contradicted `subpopulation_elements_present: false`; the counts are a README summary, not a distribution in the released data. |
| `subpopulations[1].identification` | changed | both | Now states that the variable is not released at participant level and is held under controlled access. |
| `subpopulations[1].notes` | changed | both | Carries the aggregate counts framed as a documentation-level summary. |
| `subpopulations[2].distribution` | removed | both | Same defect as `subpopulations[1].distribution`. |
| `subpopulations[2].identification` | changed | both | Now states that sex is not released at participant level and is held under controlled access. |
| `subpopulations[2].notes` | changed | both | Carries the aggregate counts framed as a documentation-level summary. |
| `source_caveats` | changed | both | Added the v3 documentation "pilot study phase" conflict and the sensitive-elements equal-rank conflict. |
| `file_collections[9].source_caveats` | retained | full | The derived count and residual are correctly labeled as this record's arithmetic with inputs named; the audit verified them and no change was warranted. |
| `distributions[9].source_caveats` | retained | core | Same derived figures as the full record's `file_collections[9]`; verified sound and unchanged. |