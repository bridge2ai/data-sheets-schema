# Phase 4 Reconciliation Report — VOICE

## What the audit found

The Phase 3 audit returned fifteen findings against the full record: four at medium severity and eleven at low. No high-severity findings were raised, and the audit noted several strengths worth preserving — per-feature record counts transcribed rather than summed, source disagreements recorded in `source_caveats` rather than silently resolved, the pediatric release and raw audio held in `related_datasets` rather than folded into the referent, and enum-valued slots drawing only on defined members.

The four medium findings were: an invented reviewing organization in `ethical_reviews[1]`; an unsupported and internally contradicted `at_risk_populations.at_risk_groups_included: false`; a BIDS conformance claim scoped to the raw-audio artifact rather than to the released features/metadata/phenotype layout; and an office placed in the Person-ranged `data_governance.committee_contact` with a minted `#person-` fragment.

## Changes to the full record

**`conforms_to`, `conforms_to_standard` — removed (medium).** Both slots are gone from the reconciled record. The passage supporting them describes the `b2ai-voice-audio` artifact, whose documented layout is `dataset_description.json` / `phenotype` / `sub-<id>/ses-<id>/audio`; the referent released at PhysioNet 3.1.0 has a `features` / `metadata` / `phenotype` layout, as `file_collections` in this same record states. The claim was therefore scoped to a different artifact and internally inconsistent. The reasoning is preserved in an expanded paragraph in the top-level `source_caveats`, which now quotes the documentation passage, describes both layouts, and states that no standard is asserted for this release.

**`preprocessing_strategies[7]` — removed (low).** The BIDS-conversion step carried the same scoping defect and has been deleted; the list now ends with the Whisper transcription step. The remaining six entries are unchanged.

**`ethical_reviews[1]` — removed (medium).** The entry named a "Bridge2AI-Voice ethics working group" that no source names, and its supporting evidence — a published memorandum on controlled access, and sensitive fields "identified by a team of ethicists" — describes documentation and an unnamed team rather than a review by a named body. The entry is gone. Its substance was not discarded: both the memorandum and the ethicist team now appear in a new `data_governance.notes` field, where they describe the governance structure rather than asserting a review event.

**`ethical_reviews[0].contact_person` — removed (low).** Yael Bensoussan is attested as principal investigator and corresponding author, not as the contact for the IRB review. The `Person` object is gone from that entry. In its place, `review_details` was extended with the protocol's own statement that Canadian participating institutions fall outside the Single IRB process and apply separately to their own research ethics boards — a fact the bundle does state about the review.

**`at_risk_populations` — restructured (medium and low).** `at_risk_groups_included: false` is removed: no source draws that conclusion, and the record's own content works against it. `guardian_consent` is removed as a "not applicable" non-answer. In their place the object now carries three `special_protections` entries (adult-only enrollment; the protocol's listing of assent for adults unable to consent; the note about discomfort in mood-cohort questioning), a populated `assent_procedures` field, and a `source_caveats` stating plainly that no source characterizes this release's population as including or excluding at-risk groups, while noting that the adult cohorts do include participants with cognitive impairment, dementias and psychiatric diagnoses.

**`human_subject_research.special_populations` — added.** A new key carrying the same evidence about adult-only enrollment, the assent option in the protocol's consent list, and the diagnostic composition of the adult cohorts. This puts the material in a field that asks for it directly, rather than leaving it only in a boolean the sources cannot settle.

**`data_governance.committee_contact` — removed; `data_governance.notes` — added (medium).** The `Person` object naming the Data Access Compliance Office, with its minted `#person-daco-access-committee` fragment, is gone. The mailbox is retained twice over: `access_review_process` was edited to read "directed to the access committee at DACO@b2ai-voice.org", and the new `notes` field states explicitly that the sources name an office rather than a named individual and gives the address. `maintainers[2]` already carried the same address and is unchanged.

**`data_protection_impacts` — added (low).** The documentation answers the DPIA question directly and negatively. The record now carries one entry stating that no analysis of the potential impact of the dataset and its use on data subjects has been conducted, consistent with how other explicit negatives (export controls, third-party IP restrictions, confidential elements) are already carried.

**`subsets` — removed (low).** The empty list is gone.

**`creators[15].description` and `creators[15].source_caveats` — changed (low).** "roughly 120 named authors" and "approximately 120 names" were counts the record obtained by enumerating the PhysioNet author list; no source states any total. Both now read as unquantified descriptions — "carries a long author roster" and "lists a substantially longer author roster, whose length no source states as a figure."

**`updates.frequency` — removed; `updates.update_details` — changed (low).** The scalar stated a plan as an observed cadence. It is gone. `update_details` now says the semi-annual statement "is a plan written against the Health Data Nexus platform and an earlier release, not an observed cadence," and retains the enumerated publication history.

**`prohibited_uses[0]` and `[1]`.prohibition_reason — changed (low).** Both now give reasons rather than restating the prohibition: entry [0] cites the consortium's commitment to research practices that respect and protect participants' rights and interests, entry [1] the protection of participants and populations from harm and stigmatization. Entry [0] additionally gained a `notes` field carrying the prohibition text itself. Entry [2] already supplied a reason and was left alone apart from a small wording change naming the consortium.

**`related_datasets[1].target_dataset` — changed (low).** The Synapse resolver URL was replaced with the bare accession `syn72370534`, bringing the slot's four values into one form (bare identifiers throughout). The full URL is preserved in the entry's `notes`, together with a statement that the accession is used because the sources give no DOI for that resource.

**`distribution_formats[2]` — changed (low).** The Parquet entry now populates `format: Parquet`, matching its TSV and JSON siblings, and carries a `notes` field recording that no IANA media type for Parquet is stated by the sources. Its `description` was also extended to mention the per-recording metadata file.

**`last_updated_on` — removed (low).** The value duplicated `issued` by inference; no source states a modification date. `issued` is unchanged.

## Changes to the core record

The core record was re-derived by projection from the reconciled full record, so every change above that touches a core-declared slot is carried through: `conforms_to` and `conforms_to_standard` are absent; `last_updated_on` is absent; `preprocessing_strategies` has six entries; `ethical_reviews` has one entry with no `contact_person`; `at_risk_populations` carries `special_protections`, `assent_procedures` and `source_caveats` and neither `at_risk_groups_included` nor `guardian_consent`; `human_subject_research.special_populations` and `data_protection_impacts` are present; `data_governance` has `notes` and no `committee_contact`; `updates` has no `frequency`; `creators[15]` carries the unquantified roster wording; `prohibited_uses`, `related_datasets[1].target_dataset` and `distribution_formats[2]` carry their reconciled forms; the top-level `source_caveats` carries the expanded BIDS paragraph.

Two housekeeping differences from the full record are structural rather than substantive and predate this phase: `conforms_to_class` is `CoreDataset` and `conforms_to_schema` names the core schema path, as the core header block requires. `citation`, `direct_collection`, `relationships`, `splits`, `variables`, `third_party_sharing`, `participant_privacy`, `participant_compensation`, `collection_consents`, `consent_revocations` and `collection_notifications` are not declared by the core schema and do not appear there; the core record's `distributions` slot holds the projection of the full record's `file_collections` and its nested `resources`. The `subsets` removal has no core counterpart, since the core record never carried that slot.

## What was left as-is

**`data_protection_impacts` was added rather than left absent**, so the audit's low finding there is resolved rather than deferred; it is listed above under changes.

No finding was left entirely unaddressed. Two were addressed by relocation rather than deletion of the underlying content — the ethics memorandum and ethicist team moved from `ethical_reviews[1]` into `data_governance.notes`, and the DACO mailbox moved from a `Person` object into `access_review_process` and `notes` — and this is recorded as `changed` on the receiving slots and `removed` on the source slots in the table below.

The audit's noted strengths were preserved without alteration: `instances[1].notes` still transcribes the nine per-feature counts and still states that "The release does not state a single recording total and none is computed here"; the version, award-identifier and platform disagreements remain in `source_caveats` at the top level, in `funders[0]`, in `creators[6]`, in `creators[12]`, in `maintainers[2]` and in `regulatory_restrictions`; the pediatric release and raw audio remain in `related_datasets`; and every enum-valued slot still draws on defined members.

## Dispositions

| slot | disposition | record | reason |
|---|---|---|---|
| `conforms_to` | removed | both | Claim scoped to the raw-audio artifact, whose layout differs from the released features/metadata/phenotype layout stated by this record's own `file_collections`. |
| `conforms_to_standard` | removed | both | Same scoping defect; the term followed the prose claim it encoded. |
| `source_caveats` | changed | both | Expanded to quote the BIDS passage, describe both layouts, and state that no standard is asserted for this release. |
| `preprocessing_strategies[7]` | removed | both | The BIDS-conversion step described preparation of the raw audio dataset, not the chain that produced the released features. |
| `ethical_reviews[1]` | removed | both | Named a reviewing organization no source names; converted documentation and an unnamed ethicist team into a review event. |
| `ethical_reviews[0].contact_person` | removed | both | Bensoussan is attested as PI and corresponding author, not as contact for the ethical review. |
| `ethical_reviews[0].review_details` | changed | both | Extended with the protocol's attested statement about Canadian institutions reviewing outside the Single IRB process. |
| `at_risk_populations.at_risk_groups_included` | removed | both | Asserted false without support and against the record's own content on cognitive, dementia and psychiatric cohorts. |
| `at_risk_populations.guardian_consent` | removed | both | Opened "Not applicable to this cohort" — a statement that the field does not apply rather than an answer. |
| `at_risk_populations.special_protections` | changed | both | Split into three attested entries: adult-only enrollment, the assent option in the protocol's consent list, and the discomfort note. |
| `at_risk_populations.assent_procedures` | added | both | The protocol states assent documentation and the under-seven exception; this field asks for it. |
| `at_risk_populations.source_caveats` | added | both | Records that no source characterizes this population as including or excluding at-risk groups, and notes the diagnostic composition. |
| `human_subject_research.special_populations` | added | both | Places the assent-option and cohort-composition evidence in a field that asks for it directly. |
| `data_governance.committee_contact` | removed | both | A Person-ranged slot held an office, with a minted `#person-` fragment asserting an individual the sources do not name. |
| `data_governance.access_review_process` | changed | both | Edited to name the access committee alongside the DACO mailbox, retaining the contact route. |
| `data_governance.notes` | added | both | Carries the office-not-individual statement, the mailbox, the ethics memorandum and the ethicist team. |
| `data_protection_impacts` | added | both | The documentation answers the DPIA question directly and negatively; consistent with other explicit negatives already carried. |
| `subsets` | removed | full | Empty multivalued list carrying no information while reading as a populated slot. Not declared in the core projection. |
| `creators[15].description` | changed | both | "roughly 120 named authors" was a count the record derived by enumeration; no source states a total. |
| `creators[15].source_caveats` | changed | both | "approximately 120 names" likewise derived; now states that no source gives the roster length as a figure. |
| `updates.frequency` | removed | both | Stated a prospective plan as a present cadence. |
| `updates.update_details` | changed | both | Now tenses the semi-annual statement as a plan written against an earlier release and platform. |
| `prohibited_uses[0].prohibition_reason` | changed | both | Restated the prohibition instead of giving the reason; now cites the consortium's participant-protection commitment. |
| `prohibited_uses[0].notes` | added | both | Holds the prohibition text displaced from `prohibition_reason`. |
| `prohibited_uses[1].prohibition_reason` | changed | both | Same defect; now states the protective purpose behind the bar. |
| `prohibited_uses[2].prohibition_reason` | retained | both | Already supplied a reason; minor wording change only to name the consortium. |
| `related_datasets[1].target_dataset` | changed | both | Resolver URL replaced with the bare Synapse accession, matching the bare-identifier form of the other three entries. |
| `related_datasets[1].notes` | changed | both | Retains the full Synapse URL and explains why the accession is used as the identifier. |
| `distribution_formats[2].format` | added | both | Parquet entry now populates `format` like its TSV and JSON siblings. |
| `distribution_formats[2].notes` | added | both | Records that no IANA media type for Parquet is stated by the sources. |
| `last_updated_on` | removed | both | Duplicated `issued` by inference; no source states a modification date. |
| `instances[1].notes` | retained | both | Audit-noted strength: transcribes per-feature counts and declines to compute a total. |
| `funders[0].source_caveats` | retained | both | Audit-noted strength: records the award-identifier disagreement rather than resolving it. |
| `regulatory_restrictions.source_caveats` | retained | both | Audit-noted strength: records the HIPAA/PII characterization conflict between the DUA and the documentation. |
| `related_datasets[2]` | retained | both | Audit-noted strength: the pediatric release is held here rather than folded into the referent. |