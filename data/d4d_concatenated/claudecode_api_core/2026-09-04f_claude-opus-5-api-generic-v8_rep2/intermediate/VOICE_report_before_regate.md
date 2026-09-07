# Phase 4 Reconciliation Report — VOICE

## Scope

The audit returned sixteen findings against the full record: one major, fourteen minor, two informational (one finding, `regulatory_restrictions`, covers two adjacent slots). No finding alleged a fabricated fact; the audit's own summary confirms that every quantitative claim it checked — participant counts, per-feature record counts, FFT parameters, phenotype directory contents, release history, DOIs, compensation amounts, retention terms, AI-readiness scores — matches the bundle for version 3.1.0. The findings fall into four groups: subject drift from the umbrella IRB protocol and sibling artifacts into the referent's own slots; earlier-release state presented as current; fields answered with an absence or a pointer instead of content; and shape defects in `related_datasets`.

The referent was and remains the adult feature-only PhysioNet release at version 3.1.0. Every disposition below was decided against that referent.

---

## Changes made to the full record

### 1. `at_risk_populations.guardian_consent` — removed (major)

The audit is correct and this was the one finding that misstated a fact about the referent. The record's own `guardian_consent` text conceded "Pediatric enrollment is outside this adult dataset" while nonetheless asserting a guardian-consent provision as a property of a dataset whose stated eligibility is 18 to 120 years. The provision belongs to the umbrella IRB protocol's pediatric arm, which governs the separately released pediatric dataset. The field is gone from the reconciled full record. The pediatric dataset's own ethics approval (Research Ethics Board at the Hospital for Sick Children) was already carried in `related_datasets`, where it belongs, and remains there.

### 2. `at_risk_populations.special_protections` — changed

Bullet 1 described the umbrella protocol's assent provisions for children and for adults unable to consent, which is not a statement about this release's protections. It was removed. The surviving text is the age-restriction statement, which is a fact about the adult release.

### 3. `at_risk_populations.at_risk_groups_included` — retained, caveat not added

The audit asked for either removal or an explicit `source_caveats`. The value is retained without one. The reasoning: `human_subject_research.special_populations` already enumerates the same cohorts — neurological and neurodegenerative diagnoses including cognitive impairment, and mood and psychiatric diagnoses — and does so in the slot the schema provides for exactly that statement. The boolean in `at_risk_populations` is the same reading of the same evidence and is not a second, independent claim. I judged an additional caveat redundant against a neighbouring slot that already carries the substance. This is a defensible-but-unstated inference and a reader may reasonably disagree.

### 4. `content_warnings` — changed

The audit is correct that the boolean asserted a superseded state. The record's own caveat noted the conflict while `content_warnings_present: true` continued to state it. Reconciled: `content_warnings_present` is now `false`, and the warning text has been rewritten to record what the healthsheet says, to attribute it to the healthsheet, and to state plainly that version 3.1.0 does not distribute the free speech content the warning concerns — transcripts removed at 1.1, and spectrograms, Mel spectrograms, MFCCs, PPGs, EMAs and transcriptions from open-response prompts excluded at 3.0.0 and 3.1.0. The `source_caveats` that formerly held this reasoning was folded into the warning itself, since it is now the substance rather than a trust annotation.

### 5. `related_datasets[*].target_dataset` — changed (all four entries)

All four values were descriptive prose in a slot the audit reads as taking an identifier. Reduced to identifiers: `10.13026/h995-bt35`, `10.13026/k81f-qr68`, `10.13026/37yb-1t42`, `syn72370534`. Every displaced sentence moved into the entry's `notes`, including a `notes` newly added to the third entry, which previously had none. No factual content was lost.

### 6. `preprocessing_strategies[2]` — removed, content relocated to `raw_sources[0]`

The BIDS v1.9.0 conversion describes the audio dataset's folder layout, not a preprocessing step of this feature-only release. The third `preprocessing_strategies` entry is gone. Rather than discard the fact, its substance now appears at the end of `raw_sources[0].raw_data_details`, explicitly scoped: the conversion "describes the audio dataset's folder layout rather than this feature-only release." This is the correct home — `raw_sources` is where the record already describes the audio artifact that is not part of this release.

### 7. `ethical_reviews[1]` — removed

The Canadian REB entry described the umbrella protocol's Canadian arm and the separate genomic sub-protocol, neither of which governs this release; the entry's own text conceded the genomic work "is not part of this release." The tier-1 source states only USF IRB approval. The entry is gone; `ethical_reviews` now holds one entry.

Consequentially, `human_subject_research.regulatory_compliance` was trimmed: the clause "with separate research ethics board review for the Canadian sites" was removed, leaving HIPAA, the Certificate of Confidentiality, and the Single IRB process for United States sites.

### 8. `collection_timeframes[0]` — changed (caveat added)

`timeframe_details` is unchanged. A `source_caveats` was added recording that the twelve-month figure comes from documentation written against earlier releases, that the 3.1.0 cohort accumulated across releases from 306 participants at v1.0 to 833 at v3.0.0, and that no tier-1 source states a collection period.

### 9. `license_and_use_terms` — changed

`license_terms` was rewritten to scope the access model to version 3.1.0 explicitly ("For version 3.1.0 the access policy is credentialed") and to drop the registered-access sentences that described an earlier release. A `source_caveats` was added recording the change across releases: PhysioNet gives v1.1 as restricted access for registered users, and 3.0.0 and 3.1.0 as credentialed access.

### 10. `splits[0].split_details` — changed

The negative half ("No recommended train, validation or test splits are supplied") was removed from the slot and the actionable half retained: researchers construct their own splits. The negative statement was moved to the record-level `notes`, whose final sentence now reads "No recommended train, validation or test splits are supplied with the release."

### 11. `external_resources[0].future_guarantees` — changed

Replaced the report of what the healthsheet answers ("not applicable") with the substantive position: no guarantee of persistence is offered, and these are supporting materials rather than dependencies, the dataset being self-contained.

### 12. `existing_uses[0].notes` — changed

The coined name "Bridge2AI Voice Scholars program" was replaced with the source's own framing and URL: "The project documentation lists training opportunities for using the dataset at https://www.b2aivoicescholars.org/".

### 13. `maintainers[1]` — changed

Two edits. `role` moved from `academic_institution` to `other`, which is the closer enum value for an access-compliance office. `maintainer_details` dropped the unsupported "Curates the dataset" — the healthsheet's curator contact is redacted in the bundle — leaving the attested function: reviews access requests for raw audio, receives access questions at DACO@b2ai-voice.org.

### 14. `regulatory_restrictions.confidentiality_level` and `.hipaa_compliant` — retained, caveat added

Both enum values are retained. A `source_caveats` was added stating that neither term is used verbatim by any source, that `restricted` is this record's reading of the credentialed access policy and signed DUA, and that `compliant` is this record's reading of the healthsheet's "Yes" to applying HIPAA de-identification rules together with the protocol's account of HIPAA-compliant collection and STRIDES storage.

### 15. `conforms_to` / `conforms_to_standard` — left omitted, decision documented (info)

Both remain absent. The audit judged the omission defensible; the reconciliation makes it legible by recording the reasoning in the record-level `source_caveats`, which now states that the BIDS v1.9.0 conversion concerns the audio dataset's folder layout, is noted in `raw_sources` rather than asserted as a property of this release, "which is why conforms_to and conforms_to_standard are omitted."

### 16. `creators` — retained, granularity documented (info)

The three-entry institution-and-consortium representation is retained. A `source_caveats` was added to `creators[2]` recording that the PhysioNet record enumerates roughly 120 individual authors and that authorship is represented at institution and consortium granularity with the two co-PIs named, rather than one Creator per listed author.

---

## Additional edits not arising from audit findings

Three shape corrections were made during reconciliation, visible in the comparison:

- `sampling_strategies[0].strategies` — converted from a three-item list to a single prose string.
- `missing_data_documentation[0].missing_data_patterns` and `.missing_data_causes` — converted from lists to prose strings.
- `machine_annotation_tools[0].tool_descriptions` — converted from a seven-item list to a single prose string.
- `is_deidentified.identifiers_removed` — converted from an eighteen-item list to a semicolon-delimited string.
- `participant_privacy[0].privacy_techniques` — converted from a four-item list to prose.
- `instances[*].missing_information[*].missing` — each scalar string converted to a single-item list.

No factual content was added or removed by any of these.

---

## Changes made to the core record

The core record was re-derived by projection from the reconciled full record. Every change above that touches a slot the core schema declares is reflected there identically: `at_risk_populations` is gone entirely from the core record (its only remaining content after reconciliation was the age-restriction bullet, and the projection dropped the object); `content_warnings`, `related_datasets`, `license_and_use_terms`, `splits` (absent from core), `external_resources`, `existing_uses`, `maintainers`, `regulatory_restrictions`, `collection_timeframes`, `creators`, `ethical_reviews`, `human_subject_research`, `raw_sources`, `preprocessing_strategies`, `notes` and `source_caveats` all carry the reconciled text.

The core record's `# Phase 4 reconciliation: completed` line was written only after this phase ran.

Note: `at_risk_populations` is absent from the reconciled core record although the full record retains a one-bullet `special_protections` and the `at_risk_groups_included` boolean. This is a projection asymmetry, not a decision recorded above; the core schema declares the slot and the full record still carries it.

---

## Validation

Both records were validated after reconciliation:

- Full: `linkml-validate -s data_sheets_schema_all.yaml -C Dataset` — passed.
- Core: `linkml-validate -s data_sheets_schema_core_all.yaml -C CoreDataset` — passed.

---

## Dispositions

| slot | disposition | record | reason |
|---|---|---|---|
| `at_risk_populations.guardian_consent` | removed | full | Guardian-consent provision governs the umbrella protocol's pediatric arm, not this adult release (eligibility 18–120). Asserting it as a property of the referent misstates who consented. |
| `at_risk_populations.special_protections` | changed | full | Bullet describing the protocol's assent provisions for children and adults unable to consent removed; the age-restriction bullet, a fact about this release, retained. |
| `at_risk_populations.at_risk_groups_included` | retained | full | Inference from cohort composition, but `human_subject_research.special_populations` already states the same cohorts in the slot the schema provides for it; a duplicate caveat judged redundant. |
| `content_warnings[0].content_warnings_present` | changed | both | Changed `true` to `false`. Free-speech transcripts removed at v1.1 and dense free-speech features excluded at 3.0.0 and 3.1.0, so the boolean asserted a superseded release's state. |
| `content_warnings[0].warnings` | changed | both | Rewritten to attribute the warning to the healthsheet and state that v3.1.0 does not distribute the content it concerns; the former `source_caveats` folded in as substance. |
| `related_datasets[0].target_dataset` | changed | both | Prose reduced to the identifier `10.13026/h995-bt35`; descriptive material moved to `notes`. |
| `related_datasets[1].target_dataset` | changed | both | Prose reduced to `10.13026/k81f-qr68`; title and release date moved to `notes`. |
| `related_datasets[2].target_dataset` | changed | both | Prose reduced to `10.13026/37yb-1t42`; a `notes` added to carry the descriptive text. |
| `related_datasets[3].target_dataset` | changed | both | Prose reduced to the Synapse identifier `syn72370534`; access route and URL moved to `notes`. |
| `preprocessing_strategies[2]` | removed | both | BIDS v1.9.0 conversion describes the audio dataset's folder layout, not a preprocessing step of this feature-only release. |
| `raw_sources[0].raw_data_details` | changed | both | Extended to carry the BIDS conversion fact, explicitly scoped to the audio dataset rather than this release. |
| `ethical_reviews[1]` | removed | both | Described the Canadian arm of the umbrella protocol and the separate genomic sub-protocol; neither governs this release, and the entry conceded the genomic work is not part of it. |
| `human_subject_research.regulatory_compliance` | changed | both | Consequential to the above: clause about separate Canadian REB review removed. |
| `collection_timeframes[0].source_caveats` | added | both | Records that the twelve-month figure comes from documentation written against earlier releases and that the cohort accumulated across releases; no tier-1 source states a period. |
| `license_and_use_terms.license_terms` | changed | both | Scoped to v3.1.0's credentialed policy; registered-access sentences describing an earlier release removed. |
| `license_and_use_terms.source_caveats` | added | both | Records that the access model changed across releases — restricted at v1.1, credentialed at 3.0.0 and 3.1.0. |
| `splits[0].split_details` | changed | full | Negative statement about absent splits removed from the slot; actionable half (researchers construct their own) retained. Core schema does not declare `splits`. |
| `notes` | changed | both | Absorbed the statement that no recommended splits are supplied, displaced from `splits`. |
| `external_resources[0].future_guarantees` | changed | both | Replaced the report of the healthsheet's "not applicable" with the substantive position: no persistence guarantee offered; resources are supporting materials, not dependencies. |
| `existing_uses[0].notes` | changed | both | Coined name "Bridge2AI Voice Scholars program" replaced with the source's own framing and the URL it gives. |
| `maintainers[1].role` | changed | both | `academic_institution` replaced with `other`; an access-compliance office is not an academic institution. |
| `maintainers[1].maintainer_details` | changed | both | Unsupported "Curates the dataset" removed — the healthsheet's curator contact is redacted in the bundle. |
| `regulatory_restrictions.confidentiality_level` | retained | both | Value `restricted` retained as a supportable reading of the credentialed access policy; derivation now recorded in `source_caveats`. |
| `regulatory_restrictions.hipaa_compliant` | retained | both | Value `compliant` retained as a supportable reading of the healthsheet and protocol; derivation now recorded in `source_caveats`. |
| `regulatory_restrictions.source_caveats` | added | both | Records that neither enum term is used verbatim by a source and names what each was derived from. |
| `conforms_to` | retained | both | Left omitted. Attested BIDS statement concerns the audio dataset, not this feature-only release; reasoning now documented in the record-level `source_caveats`. |
| `conforms_to_standard` | retained | both | Left omitted for the same reason; decision made legible in `source_caveats`. |
| `creators[2].source_caveats` | added | both | Records that PhysioNet enumerates roughly 120 authors and that authorship is represented at institution and consortium granularity. |
| `source_caveats` | changed | both | Extended to state the referent explicitly, to record that protocol facts governing only the pediatric arm, the pediatric dataset, the raw audio or the Canadian genomic sub-protocol are excluded, and to document the `conforms_to` omission. |
| `sampling_strategies[0].strategies` | changed | both | List collapsed to a single prose string to match the declared scalar range. |
| `missing_data_documentation[0].missing_data_patterns` | changed | both | List collapsed to prose to match the declared scalar range. |
| `missing_data_documentation[0].missing_data_causes` | changed | both | List collapsed to prose to match the declared scalar range. |
| `machine_annotation_tools[0].tool_descriptions` | changed | both | List collapsed to prose to match the declared scalar range. |
| `is_deidentified.identifiers_removed` | changed | both | List collapsed to a semicolon-delimited string to match the declared scalar range. |
| `participant_privacy[0].privacy_techniques` | changed | both | List collapsed to prose to match the declared scalar range. |
| `instances[0].missing_information[0].missing` | changed | both | Scalar converted to a single-item list to match the declared multivalued range. |
| `instances[0].missing_information[1].missing` | changed | both | Scalar converted to a single-item list to match the declared multivalued range. |
| `instances[0].missing_information[2].missing` | changed | both | Scalar converted to a single-item list to match the declared multivalued range. |