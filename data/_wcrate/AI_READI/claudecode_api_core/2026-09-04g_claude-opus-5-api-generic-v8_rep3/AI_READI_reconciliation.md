# Phase 4 Reconciliation Report — AI_READI

## Scope

The Phase 3 audit returned thirteen findings against the paired full and core records (one high, two medium, ten low). This phase applied repairs to the full record and re-projected the affected slots into the core record, then re-validated both. The referent is unchanged: the publicly downloadable FAIRhub release of version 3.0.0, DOI 10.60775/fairhub.3.

## High-severity finding

### `data_governance.accountable_organization_notes` — removed (both records)

The audit found an invented key with a null value under `data_governance`. The schema digest lists the DataGovernance keys as `access_decision_timeframe`, `access_review_process`, `accountable_organization`, `appeal_process`, `committee_contact`, `committee_members`, `committee_name`, `notes`, `source_caveats` and `stewardship_roles`; `accountable_organization_notes` is not among them. It held no content in either record (an empty scalar in the full record, an empty string in the core record). The key has been deleted from both. The caveat it appeared to have been intended for — that Washington University in St. Louis is recorded as accountable organization while the RO-Crate names the AI-READI Consortium — was already carried in `data_governance.source_caveats` and remains there unchanged.

## Medium-severity findings

### `variables[recommended_split].categories` — changed (full only)

Three category values were collapsed into one list element, `"Train; Val; Test"`. `categories` is multivalued and each attested category is a distinct entity; the README split table gives Train, Val and Test as separate column headers. The single element has been replaced by three: `Train`, `Val`, `Test`. `variables` is not projected into the core record, so this repair is confined to the full record.

### `distribution_dates[0].release_dates` — changed (both records)

A scalar string was supplied to a slot the schema declares multivalued. The value is unchanged in content — `2025-11-17`, the FAIRhub `dateType: Available` date — but is now emitted as a one-item list in both records.

## Low-severity findings — repaired

### `variables[participant_id].description`, `variables[recommended_split].description` — changed to `notes` (full only)

`description` is not among the keys the schema digest lists for VariableMetadata. Both texts have been moved to `notes`, which the digest does list. The content is unchanged and remains bundle-supported: the participant folder naming convention for the first, participants.tsv carrying the split assignment for the second.

### `creators[0].affiliations` — removed (both records)

Eight ROR-identified organizations were asserted as affiliations of the AI-READI Consortium creator. The bundle names these institutions in the FAIRhub `sponsorCollaboratorsModule` and `locationList` as sponsors, collaborators and study locations; the creator block itself records only `creatorName: "AI-READI Consortium"` with `nameType: Organizational`. The roster was also incomplete relative to its source, omitting the University of Utah, the University of Massachusetts Lowell, Meharry Medical College and Portland State University, which appear in the same material. The slot has been removed from both records and `creators[0].source_caveats` rewritten to state explicitly that no affiliations are asserted and why, naming the institutions the bundle does list and the role in which it lists them. `creators[0].principal_investigator.affiliation` is untouched: that person-level affiliation is directly attested by the FAIRhub responsible-party block and the RO-Crate principal-investigator string.

### `known_biases[selection_bias].mitigation_strategy` — removed (both records)

The entry claimed EHR-driven personalized recruitment and wave adjustment as a mitigation of volunteer bias. The bundle attributes wave adjustment to demographic balancing, not to volunteer bias, and the BMJ Open protocol states volunteer bias as an unmitigated limitation. The `mitigation_strategy` key has been deleted from this entry in both records and a sentence appended to `bias_description` recording that the protocol states the limitation and describes no measure against it. The three other `known_biases` entries keep their mitigation strategies, each of which is directly attested.

### `regulatory_restrictions.confidentiality_level` — retained, `notes` changed (both records)

The enum value `restricted` stands in for the RO-Crate's attested `HL7:2N (normal)`, a term the enum cannot express. The value is retained because omission would leave the slot silent about a documented gating regime, but the `notes` text has been rewritten so the substitution is unambiguous: it now states that `HL7:2N (normal)` is the only level the sources give, that the enum offers no HL7 mapping, that `restricted` is this record's own substitution, and that the substitution does not reproduce and on its face contradicts the source term. The earlier wording gave the reasoning but did not flag the contradiction.

### `data_protection_impacts[0].impact_details` — changed (both records)

The object records the absence of an assessment. It is retained because the healthsheet's substantive answer to the question is that none was conducted, and an omitted slot would not carry that. The text has been rewritten to state plainly that this is an explicit negative answer rather than an omission, so a reader cannot mistake an empty finding for an unfilled field.

### `extension_mechanism.extension_details` — changed (both records)

Same pattern, same disposition. The text now states that the project's own datasheet records the absence of an extension mechanism as an explicit negative answer.

### `sampling_strategies[0].is_sample` — retained, `source_caveats` changed (both records)

The `is_sample: false` value sits in tension with a populated `strategies` field describing wave-based stratified selection and a populated `why_not_representative`. The tension is inherited from the sources rather than introduced by the record: the FAIRhub healthsheet answers that the dataset contains all possible instances and gives "N/A" for sampling strategy, while the FAIRhub study description records `samplingMethod: "Non-Probability Sample"` — both tier 1, so the ranking cannot decide between them. The boolean is retained and the caveat rewritten to say so directly: it now names the disagreement, states that the record carries the tension rather than resolving it, and tells the reader to treat `is_sample` as scoped to enrollment completeness only.

### `preprocessing_strategies[2].preprocessing_details` — changed (both records)

The entry's subject was partly earlier releases. `preprocessing_details` now states only the referent's own processing ("Version 3.0.0 was produced by a combination of automated and custom processing"), and the cross-version comparison drawn from the CHANGELOG summary table has been moved to the entry's `notes`.

### `publisher` — retained, top-level `source_caveats` changed (both records)

The slot holds `https://fairhub.io/` where the FAIRhub source states the `publisherName` string "FAIRhub". The slot range is `uriorcurie`, so a URI is permissible, and the value is retained. The top-level `source_caveats` already recorded the FAIRhub/RO-Crate publisher disagreement; it has been extended to state that the platform URL is this record's substitution for the bare name the source gives.

### `related_datasets[2].target_dataset`, `related_datasets[3].target_dataset` — retained, `notes` changed (both records)

Both targets are named in prose because the bundle supplies no identifier for either: the API records only `"child": 4` for the mini-subset, and the controlled-access release is never given a DOI. No repair is available from the evidence. Each entry's `notes` now states that no DOI or other identifier appears in the declared sources and that the target is therefore named in prose.

### `created_by` — added (both records)

The slot was omitted although two tier-1 sources attest the responsible party: the RO-Crate `author` and `publisher` fields and the FAIRhub creator block, both giving "AI-READI Consortium". The slot is declared in both the full and core schemas and has been added to both records with that value.

## Findings left as-is

No finding was dismissed outright. Four were resolved by strengthening a caveat or a note rather than by changing a value — `regulatory_restrictions.confidentiality_level`, `sampling_strategies[0].is_sample`, `publisher`, and the two `related_datasets` targets — because in each case the evidence does not support a different value and the defect is one of disclosure rather than of fact.

## Verification

Neither the referent nor any factual claim traceable to the bundle was altered except where a finding required it. Arithmetic was re-checked and is unchanged: the nine data-type file counts sum to 356,334 against a stated total of 356,343, and the derived figure of nine root metadata files remains labeled as this record's own computation with its inputs named in `file_collections[collection-root-metadata].source_caveats`. All ROR CURIEs remaining in the records (`ROR:01yc7t268` in `data_governance.accountable_organization` and in the principal investigator's affiliation list) are directly attested. The core record continues to name its source full record in the `# Sources:` header line, and its `# Phase 4 reconciliation: completed` line is now accurate.

## Dispositions

| slot | disposition | record | reason |
|---|---|---|---|
| `data_governance.accountable_organization_notes` | removed | both | Key not among those the schema digest lists for DataGovernance, and null-valued; the caveat it was intended for is already in `data_governance.source_caveats`. |
| `variables[1].categories` | changed | full | Three attested categories were collapsed into one list element; split into `Train`, `Val`, `Test`. |
| `distribution_dates[0].release_dates` | changed | both | Scalar supplied to a multivalued slot; emitted as a one-item list, content unchanged. |
| `variables[0].notes` | added | full | Text moved here from a `description` key not listed for VariableMetadata in the schema digest. |
| `variables[1].notes` | added | full | Text moved here from a `description` key not listed for VariableMetadata in the schema digest. |
| `creators[0].affiliations` | removed | both | Bundle lists these institutions as sponsors, collaborators and locations, not as affiliations of the consortium-as-creator; roster also incomplete relative to its source. |
| `creators[0].source_caveats` | changed | both | Rewritten to state that no affiliations are asserted, name the institutions the bundle lists, and give the role in which it lists them. |
| `known_biases[0].mitigation_strategy` | removed | both | Sources do not frame wave adjustment as a mitigation of volunteer bias; the protocol states the bias as unmitigated. |
| `known_biases[0].bias_description` | changed | both | Extended to record that the protocol states this limitation and describes no measure against it. |
| `regulatory_restrictions.confidentiality_level` | retained | both | Enum cannot express the attested `HL7:2N (normal)`; value kept so the gating regime is not left silent, with the substitution disclosed in `notes`. |
| `regulatory_restrictions.notes` | changed | both | Rewritten to state that `restricted` is this record's substitution and that it contradicts the source term. |
| `data_protection_impacts[0].impact_details` | changed | both | Rewritten to mark the absence of an assessment as an explicit negative answer rather than an unfilled field. |
| `extension_mechanism.extension_details` | changed | both | Rewritten to mark the absence of a mechanism as an explicit negative answer rather than an unfilled field. |
| `sampling_strategies[0].is_sample` | retained | both | Tension inherited from a genuine tier-1 source disagreement the ranking cannot decide; carried rather than resolved. |
| `sampling_strategies[0].source_caveats` | changed | both | Rewritten to name the disagreement and scope `is_sample` to enrollment completeness. |
| `preprocessing_strategies[2].preprocessing_details` | changed | both | Narrowed to the referent's own release; the cross-version comparison moved to the entry's `notes`. |
| `preprocessing_strategies[2].notes` | added | both | Holds the CHANGELOG cross-version processing comparison removed from `preprocessing_details`. |
| `publisher` | retained | both | `uriorcurie` range permits the platform URL; substitution for the attested `publisherName` string disclosed in the top-level caveat. |
| `source_caveats` | changed | both | Extended to record that the platform URL stands in for the bare publisher name the FAIRhub source states. |
| `related_datasets[2].notes` | changed | both | States that no identifier for the mini-subset appears in the declared sources, so the target is named in prose. |
| `related_datasets[3].notes` | changed | both | States that no identifier for the controlled-access release appears in the declared sources, so the target is named in prose. |
| `created_by` | added | both | Attested by two tier-1 sources (RO-Crate author/publisher; FAIRhub creator block) and declared in both schemas. |