# AI-READI D4D Reconciliation Report

Version label: `2026-09-04g_claude-opus-5-api-generic-v8_rep3`
Records: full (`AI_READI_d4d.yaml`), core (`AI_READI_d4d_core.yaml`)

## What the audit found

The Phase 3 audit returned fourteen findings against the full record: one high severity, two medium, eleven low. It found no fabricated identifiers — every ROR CURIE, ORCID CURIE, DOI, grant number, device make and model, participant count and byte figure in the record traces to the declared bundle — and it verified the record's one derived arithmetic figure (nine root metadata files, obtained as 356,343 minus the nine data-type directory counts summing to 356,334) as sound and correctly labeled as the record's own computation.

The high-severity finding was a structural defect: an invented, empty key `accountable_organization_notes` under `data_governance`, outside the key set the schema digest lists for `DataGovernance` and carrying a null value. The two medium findings were shape defects: three split categories collapsed into a single list element, and a scalar supplied to the multivalued `distribution_dates[0].release_dates`. The eleven low findings concerned framing, provenance discipline and slot-fit rather than fabrication.

## What was changed, and why

### Full record

**`data_governance.accountable_organization_notes` — removed.** The key is absent from the reconciled full record. It was outside the `DataGovernance` key list in the schema digest and held no value; its apparent purpose (recording the tier-1 disagreement about the accountable organization) is already discharged by `data_governance.source_caveats`, which is unchanged.

**`variables[recommended_split].categories` — changed.** The single element `Train; Val; Test` was split into three list entries, `Train`, `Val` and `Test`, matching the three column headers of the README split table. `categories` is multivalued; three attested categories are three entities.

**`distribution_dates[0].release_dates` — changed.** `"2025-11-17"` became a one-item list. The slot is declared multivalued and a scalar there is a shape defect; the content is unchanged and remains supported by the FAIRhub `dateType: Available` entry.

**`variables[participant_id].description` and `variables[recommended_split].description` — changed to `notes`.** `description` is not among the keys the schema digest lists for `VariableMetadata`; `notes` is. Both texts were moved verbatim into `notes` on their respective variable objects. No content was lost.

**`creators[0].affiliations` — removed.** The eight ROR-identified organizations were deleted from the creator object. The bundle records them as study sponsors, collaborators and locations in the FAIRhub `sponsorCollaboratorsModule` and `locationList`, not as affiliations of the consortium-as-creator; the FAIRhub `creator` block records only `creatorName: "AI-READI Consortium"` with `nameType: Organizational`. The list was also incomplete relative to its own source (University of Utah, University of Massachusetts Lowell, Meharry Medical College and Portland State University appear in the same roster and were absent). `creators[0].source_caveats` was rewritten to state that no affiliations are asserted and to name the institutions the bundle does record in that capacity, so the information is retained as a provenance note rather than as a claim. The ROR CURIEs on `principal_investigator.affiliation`, `data_governance.accountable_organization` and the individual person object are untouched — those are attested in their respective roles.

**`known_biases[selection_bias].mitigation_strategy` — removed.** The bundle frames wave adjustment as a means of achieving demographic balance, not as a mitigation of volunteer bias; the BMJ Open protocol presents volunteer bias as an unmitigated limitation. A sentence was added to `bias_description` recording that the protocol states the bias and describes no measure taken against it. The three other `known_biases` entries keep their `mitigation_strategy` values, each of which is framed as mitigation in the source.

**`preprocessing_strategies[2]` — changed.** The entry previously carried a cross-version comparison ("version 1.0.0 was produced by custom, ad hoc processing, while versions 2.0.0 and 3.0.0…") in `preprocessing_details`, a slot whose subject is the referent's own preprocessing. `preprocessing_details` now states only the v3.0.0 fact; the cross-version comparison moved to `notes` on the same entry, attributed to the CHANGELOG summary table.

**`regulatory_restrictions.notes` — changed.** The note now states plainly that the only confidentiality level the sources give is the RO-Crate's `HL7:2N (normal)`, that the enum offers no HL7 mapping, and that `restricted` is this record's substitution which does not reproduce and on its face contradicts the source term. The enum value itself was retained (see below).

**`data_protection_impacts[0].impact_details` — changed.** Rewritten to state explicitly that this is a negative answer the project's own datasheet records, rather than reading as a bare absence occupying a slot that collects assessments.

**`extension_mechanism.extension_details` — changed.** Same treatment: a sentence added noting the project's datasheet records this as an explicit negative answer.

**`sampling_strategies[0].source_caveats` — changed.** Rewritten to name the two equally ranked tier-1 sources that disagree, to say the record carries the tension rather than resolving it, and to tell the reader to read `is_sample: false` as scoped to enrollment completeness only. The boolean fields are unchanged.

**`created_by` — added.** Set to `AI-READI Consortium`. The audit noted the slot was omitted although two tier-1 sources attest the value (RO-Crate `author` and `publisher`; FAIRhub `creator`). The slot's range is `string`, so the name is the correct form here.

**`source_caveats` (top level) — changed.** The publisher sentence was expanded to state that the FAIRhub source gives the bare `publisherName` "FAIRhub" and that this record substitutes the platform URL in the `uriorcurie`-ranged slot, so the substitution is visible to a reader.

**`related_datasets[2].notes` and `related_datasets[3].notes` — changed.** Each now says explicitly that the bundle supplies no DOI or other identifier for the target and that the target is therefore named in prose. No repair to `target_dataset` was possible from the evidence.

### Core record

The core record is a projection of the full record. Every change above that touches a slot the core schema declares was propagated: `distribution_dates[0].release_dates` (now a list), `creators[0].affiliations` (removed) with the rewritten `creators[0].source_caveats`, `known_biases[0]` (mitigation removed, description extended), `preprocessing_strategies[2]` (narrowed, `notes` added), `regulatory_restrictions.notes`, `data_protection_impacts[0]`, `extension_mechanism`, `sampling_strategies[0].source_caveats`, `created_by` (added), and the top-level `source_caveats`. `data_governance.accountable_organization_notes` — which the core record also carried, with an empty-string value — is absent from the reconciled core record.

Two full-record changes have no core counterpart because the core schema does not declare the slot: `variables` (both the `description`→`notes` moves) and `related_datasets[*].notes` — the latter is declared, and the two notes were propagated. `variables` is not present in the core record at all.

The core header now carries `# Phase 4 reconciliation: completed`.

## What was left as-is, and why

**`regulatory_restrictions.confidentiality_level` — retained as `restricted`.** The audit flagged that the chosen enum value contradicts the attested `HL7:2N (normal)`. There is no enum member corresponding to the HL7 term, and omitting the slot would lose the fact that access is gated. The value was kept and the disclosure in `notes` sharpened instead, so a reader sees both the source term and the substitution.

**`publisher` — retained as `https://fairhub.io/`.** The slot's range is `uriorcurie`, which admits a URI; the substitution of the platform URL for the attested `publisherName` string is now disclosed in the top-level `source_caveats`. Recording the bare name would not satisfy the range.

**`sampling_strategies[0].is_sample`, `is_random`, `is_representative` — retained.** The tension the audit identified is inherited from a genuine disagreement between two same-tier sources, which the uniform decision rules require to be represented rather than silently resolved. Adjusting the boolean would resolve it silently. The caveat was strengthened instead.

**`related_datasets[2].target_dataset` and `related_datasets[3].target_dataset` — retained as prose.** No identifier exists in the bundle for either target; supplying one would be fabrication. The notes now say so.

**`data_protection_impacts` and `extension_mechanism` as objects recording absence — retained.** In both cases the absence is the substantive answer the project's datasheet gives to a question the slot exists to record, and omitting the slot would lose that answer. Both were re-worded to make the negative explicit.

## Validation

Both files validate: the full record against `data_sheets_schema_all.yaml` class `Dataset`, the core record against `data_sheets_schema_core_all.yaml` class `CoreDataset`.

## Dispositions

| slot | disposition | record | reason |
|---|---|---|---|
| `data_governance.accountable_organization_notes` | removed | both | Invented key, not in the `DataGovernance` key list in the schema digest, and null/empty-valued; its content is already carried by `data_governance.source_caveats`. |
| `variables[1].categories` | changed | full | Three attested categories collapsed into one list element; split into `Train`, `Val`, `Test`. Core does not declare `variables`. |
| `distribution_dates[0].release_dates` | changed | both | Scalar supplied to a multivalued slot; emitted as a one-item list. |
| `variables[0].notes` | added | full | Text moved from a `description` key not listed for `VariableMetadata` into `notes`, which is listed. |
| `variables[1].notes` | added | full | Same: `description` moved to `notes`. |
| `creators[0].affiliations` | removed | both | Bundle records these ROR-identified institutions as sponsors, collaborators and locations, not as affiliations of the consortium-as-creator; list was also incomplete relative to its own source. |
| `creators[0].source_caveats` | changed | both | Rewritten to state that no affiliations are asserted and to name the institutions the bundle records in sponsor/collaborator/location roles. |
| `known_biases[0].mitigation_strategy` | removed | both | Sources do not frame wave adjustment or EHR-driven recruitment as mitigating volunteer bias; the protocol states volunteer bias as unmitigated. |
| `known_biases[0].bias_description` | changed | both | Sentence added recording that the protocol states this bias and describes no measure against it. |
| `preprocessing_strategies[2].preprocessing_details` | changed | both | Narrowed to the referent's own release; the cross-version comparison was off-subject for this slot. |
| `preprocessing_strategies[2].notes` | added | both | Cross-version processing comparison relocated here, attributed to the CHANGELOG summary table. |
| `regulatory_restrictions.confidentiality_level` | retained | both | No enum member maps to the attested `HL7:2N (normal)`; substitution kept and disclosure sharpened rather than the slot dropped. |
| `regulatory_restrictions.notes` | changed | both | Now states the source term, the absence of an enum mapping, and that `restricted` is the record's own substitution contradicting "normal". |
| `data_protection_impacts[0].impact_details` | changed | both | Re-worded so the value reads as an explicit negative answer from the project's datasheet rather than an absence filling a slot. |
| `extension_mechanism.extension_details` | changed | both | Same treatment: explicit negative answer flagged as such. |
| `sampling_strategies[0].is_sample` | retained | both | Tension traces to a genuine same-tier source disagreement; the decision rules require representation, not silent resolution. |
| `sampling_strategies[0].source_caveats` | changed | both | Rewritten to name the disagreeing sources and to scope `is_sample` to enrollment completeness for the reader. |
| `created_by` | added | both | Attested by two tier-1 sources (RO-Crate author/publisher; FAIRhub creator block); slot range is `string`, so the name is the correct form. |
| `publisher` | retained | both | Range is `uriorcurie`, which admits the URI; the substitution for the attested `publisherName` is now disclosed in top-level `source_caveats`. |
| `source_caveats` | changed | both | Publisher sentence expanded to disclose that the platform URL stands in for the bare name the source gives. |
| `related_datasets[2].target_dataset` | retained | both | No identifier for the mini-subset exists in the bundle; supplying one would be fabrication. |
| `related_datasets[2].notes` | changed | both | Now states that no DOI or identifier is given in the declared sources, so the target is named in prose. |
| `related_datasets[3].target_dataset` | retained | both | No identifier for the controlled-access release exists in the bundle. |
| `related_datasets[3].notes` | changed | both | Same disclosure added. |