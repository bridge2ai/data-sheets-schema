# Phase 4 Reconciliation Report — VOICE

## Scope

The Phase 3 audit returned fifteen findings against the full record: four medium and eleven low. No high-severity findings were raised. Each was assessed against the declared bundle and the schema digest, and the full and core records were revised together so that the pair stays consistent. The comparison below is against the original full and core records as supplied.

## Medium-severity findings

### `ethical_reviews[1].reviewing_organization` — "Bridge2AI-Voice ethics working group"

**Changed (entry removed; content relocated).** The audit is correct: no source in the bundle names any such body. The documentation attests a published memorandum on the ethical justification for controlled access, and separately that sensitive fields were "identified by a team of ethicists" — neither states a reviewing organization, and neither describes a review event. The second `ethical_reviews` entry has been removed from both records. Its substance was not discarded: the memorandum and the ethicists' role in identifying sensitive fields now appear in `data_governance.notes`, where they describe the governance structure rather than assert an ethics review by an invented committee. The remaining `ethical_reviews[0]` was extended with the IRB protocol's statement that Canadian institutions apply separately to their own research ethics boards, which is attested and belongs with the review record.

### `at_risk_populations.at_risk_groups_included` — asserted `false`

**Removed.** The audit is correct on both counts. No source states this conclusion, and the record's own content works against it: the adult cohorts include mild cognitive impairment, Alzheimer's disease and other dementias, and mood and psychiatric diagnoses; the IRB protocol lists "Obtaining Signed Assent for Children or Adults Unable to Consent" among the study's consent options. The boolean has been removed from both records rather than flipped, because no source draws either conclusion. What the sources do attest has been restructured: `special_protections` now carries three separate statements (adult-only enrollment for this cohort, the assent option in the protocol, and the discomfort warning for mood-cohort questions), `assent_procedures` was added from the protocol's documented assent provisions, and a `source_caveats` records what the sources leave unanswered — whether the released adult cohorts include participants enrolled through assent — together with the diagnoses present. A parallel `human_subject_research.special_populations` entry was added carrying the same attested facts.

### `conforms_to` / `conforms_to_standard` — BIDS v1.9.0

**Removed.** The audit's reasoning holds. The supporting passage describes conversion of "the raw audio files and the questionnaire data retrieved from ReproSchema-UI or exported from REDCap" into a `b2ai-voice-audio` tree of `dataset_description.json`, `phenotype`, and `sub-<id>/ses-<id>/audio`. The PhysioNet 3.1.0 release this record describes has a `features` / `metadata` / `phenotype` layout, as the record's own `file_collections` state, and its data description asserts no standard. Both `conforms_to` and `conforms_to_standard` have been removed from both records, and the discrepancy is now recorded in the top-level `source_caveats` of both, quoting the documentation passage and explaining why no standard is asserted for this release. This resolves the internal inconsistency the audit identified between the standard claim and `file_collections`.

### `data_governance.committee_contact` — an office in a `Person` slot

**Removed.** The audit is correct that the sources give a committee mailbox rather than an individual, and that a minted `#person-` fragment asserts a person who is not attested. The `committee_contact` object has been removed from both records. The mailbox is not lost: `DACO@b2ai-voice.org` already appears in `data_governance.access_review_process`, in `raw_data_sources[0].access_details`, and in `maintainers[2].maintainer_details`, and the new `data_governance.notes` states explicitly that the sources name an office rather than a named individual and gives the address.

## Low-severity findings

### `ethical_reviews[0].contact_person` — Yael Bensoussan

**Removed.** The bundle attests her as principal investigator and corresponding author; nothing attests her as the contact for the IRB review. The attribution was inferred and has been removed from both records. The `Person` object with the same identifier remains at `creators[15].principal_investigator`, where the evidence does support it.

### `at_risk_populations.guardian_consent` — "Not applicable to this cohort"

**Removed.** A statement that a field does not apply is not an answer to it. The key has been removed from both records. The protocol's pediatric guardian-permission language, which was the remainder of the value, concerns participants excluded from this referent and is not reintroduced elsewhere; the pediatric release is held in `related_datasets`.

### `preprocessing_strategies[7]` — the BIDS conversion step

**Removed.** Same scoping defect as `conforms_to`. The cited passage describes preparation of the raw-audio artifact, not the chain that produced the released features, metadata and phenotype tables. The entry, and its `source_caveats` acknowledging the mismatch, have been removed from both records. The remaining six preprocessing entries describe steps the PhysioNet 3.1.0 methods section states directly.

### `subsets` — empty list

**Removed.** An empty multivalued slot reads as populated while carrying nothing. Removed from the full record. The core schema does not declare `subsets`, so there was nothing to remove there.

### `creators[15].description` / `creators[15].source_caveats` — "roughly 120 named authors"

**Changed.** No source states an author total; the figure was obtained by counting the PhysioNet roster. Rather than restate it as the record's own computation, the count was dropped entirely — it carries no analytical weight and the qualitative statement is adequate. Both fields now read "a long author roster" and "a substantially longer author roster, whose length no source states as a figure" in both records.

### `updates.frequency` — "Semi-annual"

**Removed.** The scalar stated a plan as an observed cadence. The key has been removed from both records; `updates.update_details` retains the documentation's prospective wording and was extended to say explicitly that the statement "is a plan written against the Health Data Nexus platform and an earlier release, not an observed cadence." The version history in that field remains as the record of what has actually been published.

### `prohibited_uses[*].prohibition_reason` — restatements of the prohibition

**Changed.** Entries [0] and [1] restated what is forbidden rather than why. Both were rewritten in both records to give the reason the agreement states — the consortium's commitment to research practices that respect and protect the rights and interests of research participants. The prohibited act itself moved to `prohibited_uses[0].notes`. Entry [2] already carried a reason and was lightly extended to name the Open Science principles as "upheld by the consortium," matching the source wording.

### `related_datasets[*].target_dataset` — mixed identifier forms

**Changed.** The resolver URL for the Synapse raw-audio entry was replaced with the bare accession `syn72370534` in both records, so all four targets are now bare identifiers. The full URL is retained in that entry's `notes`, along with an explanation that the accession is used because no DOI is stated for it.

### `distribution_formats[2]` — missing `format`

**Changed.** `format: Parquet` was added to the entry in both records, matching the sibling TSV and JSON entries. `media_type` was not added: no source states an IANA media type for Parquet, and a `notes` field now records that. The description was also corrected to mention the per-recording metadata Parquet file, which the 3.1.0 data description places under `metadata`.

### `data_protection_impacts` — omitted attested negative

**Added.** The audit is right that this is an attested governance answer rather than absent evidence, and that the record carries other explicit negatives (`regulatory_restrictions`, `confidential_elements`, third-party IP). A single `data_protection_impacts` entry was added to both records recording the documentation's direct answer.

### `last_updated_on` — inferred from `issued`

**Removed.** No source states a modification date. Removed from both records; `issued` remains.

## Schema-shape changes made alongside the findings

Several values were reshaped where the schema digest's declared ranges made the original form questionable, in the same pass. These were not audit findings.

- `instances[0].missing_information[*].missing` — wrapped as single-item lists in both records, matching the shape of the sibling `why_missing`.
- `sampling_strategies[0].strategies`, `machine_annotation_tools[0].tool_descriptions`, `participant_privacy[0].privacy_techniques`, `ip_restrictions` list members, `external_resources[*].external_resources` — normalized so each multivalued or scalar attribute carries the form its range implies; content is unchanged in substance.
- `distribution_formats` `access_urls` entries were left as URLs, correctly: the digest declares that attribute `uri[]`.

## Findings left as-is

None of the fifteen findings was left unaddressed. Every one produced either a removal, a change, or an addition in both records where the core schema declares the slot.

## Record identity and consistency

The referent is unchanged: the adult Bridge2AI-Voice dataset at PhysioNet version 3.1.0 (`doi:10.13026/8xbn-nq66`), published 2026-05-01. The pediatric release, the superseded 3.0.0 release, the raw-audio Synapse deposit and the protocol publication remain in `related_datasets` rather than folded into the referent's own slots. All fragment identifiers minted in the full record (`#features`, `#phenotype`, `#metadata`, the eleven `#file-*` fragments, `#person-yael-bensoussan`) are pointed at by other values in the record; the one fragment that no longer has a referent — `#person-daco-access-committee` — was removed with its object.

Both records validate against their schemas.

## Dispositions

| slot | disposition | record | reason |
|---|---|---|---|
| `ethical_reviews[1].reviewing_organization` | removed | both | Named a body no source names; the entry converted a memorandum and an unnamed team of ethicists into a review by an invented organization. |
| `ethical_reviews[1].review_details` | removed | both | Removed with its parent entry; substance relocated to `data_governance.notes`. |
| `ethical_reviews[0].contact_person` | removed | both | Bensoussan is attested as PI and corresponding author, not as contact for the IRB review; the attribution was inferred. |
| `ethical_reviews[0].review_details` | changed | both | Extended with the protocol's attested statement that Canadian institutions apply separately to their own research ethics boards. |
| `at_risk_populations.at_risk_groups_included` | removed | both | Asserted `false` with no source support, and contradicted by the record's own cohort content and the protocol's assent option. |
| `at_risk_populations.special_protections` | changed | both | Split into three separate attested statements: adult-only enrollment, the assent option in the protocol, and the mood-cohort discomfort warning. |
| `at_risk_populations.guardian_consent` | removed | both | Opened "Not applicable to this cohort" — a statement that the field does not apply rather than an answer to it. |
| `at_risk_populations.assent_procedures` | added | both | The protocol documents assent procedures, including the under-seven exception; this is the field that asks for them. |
| `at_risk_populations.source_caveats` | added | both | Records that no source characterizes this release's population as including or excluding at-risk groups, and names the diagnoses present. |
| `human_subject_research.special_populations` | added | both | Carries the attested facts about assent options and the cognitive/psychiatric diagnoses in the adult cohorts. |
| `conforms_to` | removed | both | The supporting passage describes the raw-audio artifact's BIDS layout, not the released features/metadata/phenotype layout, and conflicted with `file_collections`. |
| `conforms_to_standard` | removed | both | Removed with `conforms_to` for the same scoping reason. |
| `preprocessing_strategies[7]` | removed | both | The BIDS-conversion step carries the same scoping defect; its own `source_caveats` acknowledged the mismatch rather than resolving it. |
| `source_caveats` | changed | both | Records the BIDS scoping discrepancy, quoting the documentation passage and stating why no standard is asserted for this release. |
| `data_governance.committee_contact` | removed | both | An office placed in a `Person`-ranged slot with a minted `#person-` fragment asserting an individual the sources do not attest. |
| `data_governance.notes` | added | both | Records that the sources name an office rather than an individual, gives the DACO mailbox, and holds the memorandum and ethicists content relocated from `ethical_reviews`. |
| `data_governance.access_review_process` | changed | both | Reworded to name the access committee explicitly alongside the mailbox. |
| `subsets` | removed | full | Emitted as an empty list, which reads as populated while carrying nothing; not declared in the core schema. |
| `creators[15].description` | changed | both | The "~120 named authors" figure was the record's own count of the roster and no source states it; replaced with a qualitative statement. |
| `creators[15].source_caveats` | changed | both | Same reason; now states that the roster's length is not given as a figure by any source. |
| `updates.frequency` | removed | both | Stated a prospective plan, written against an earlier release and a different platform, as a present cadence. |
| `updates.update_details` | changed | both | Extended to mark the semi-annual statement explicitly as a plan rather than an observed cadence. |
| `prohibited_uses[0].prohibition_reason` | changed | both | Restated the prohibition instead of giving its reason; now gives the consortium's stated commitment to participants' rights and interests. |
| `prohibited_uses[0].notes` | added | both | Holds the prohibited act displaced from `prohibition_reason`. |
| `prohibited_uses[1].prohibition_reason` | changed | both | Same defect as [0]; rewritten to state why the prohibition exists. |
| `prohibited_uses[2].prohibition_reason` | changed | both | Extended to attribute the Open Science principles to the consortium, matching source wording. |
| `related_datasets[1].target_dataset` | changed | both | Resolver URL replaced with the bare Synapse accession so all four targets share one identifier form; URL retained in `notes`. |
| `related_datasets[1].notes` | changed | both | Records the full Synapse URL and explains that the accession is used because no DOI is stated. |
| `distribution_formats[2].format` | added | both | The Parquet entry omitted `format` while sibling entries populated it; nothing in the digest constrains this attribute to an enum. |
| `distribution_formats[2].description` | changed | both | Corrected to include the per-recording metadata Parquet file. |
| `distribution_formats[2].notes` | added | both | Records that no source states an IANA media type for Parquet, so none is given. |
| `data_protection_impacts` | added | both | The documentation answers the DPIA question directly in the negative; other attested negatives are carried, so this one should be too. |
| `last_updated_on` | removed | both | No source states a modification date; the value duplicated `issued` by inference. |
| `instances[0].missing_information[0].missing` | changed | both | Reshaped as a list to match the declared range and the sibling `why_missing`. |
| `instances[0].missing_information[1].missing` | changed | both | Same reason. |
| `sampling_strategies[0].strategies` | changed | both | Reshaped to the form its declared range implies; content unchanged in substance. |
| `machine_annotation_tools[0].tool_descriptions` | changed | both | Same reason. |
| `participant_privacy[0].privacy_techniques` | changed | full | Same reason; `participant_privacy` is not declared in the core schema. |
| `external_resources[0].external_resources` | changed | both | Reshaped to the form its declared range implies. |
| `external_resources[1].external_resources` | changed | both | Same reason. |
| `external_resources[2].external_resources` | changed | both | Same reason. |
| `external_resources[3].external_resources` | changed | both | Same reason. |
| `external_resources[4].external_resources` | changed | both | Same reason. |
| `file_collections` | retained | full | Not questioned by the audit; the layout it records is what supported removing the BIDS claim. Not declared in the core schema, which carries `distributions` instead. |
| `instances[1].notes` | retained | both | Per-feature counts are transcribed rather than summed, with the record declining to compute a total; the audit named this a strength. |
| `funders[0].source_caveats` | retained | full | Award-identifier disagreement is recorded rather than silently resolved; the audit named this a strength. Present in core as well but reported at the slot the audit did not question. |