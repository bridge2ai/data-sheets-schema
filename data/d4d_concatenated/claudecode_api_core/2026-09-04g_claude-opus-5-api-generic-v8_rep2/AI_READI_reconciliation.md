# Reconciliation Report — AI_READI

## Scope

The audit returned seventeen findings against the full record: one unrecorded tier-1 conflict, two neighbouring-field placements, two absence-statements standing in for answers, one referent breach, one internal inconsistency, two under-caveated interpretive enum values, one standards-scope question, three misplacements or coinages, two commentary-in-value cases, and three supported omissions. No fabrication was found. All seventeen were adjudicated; fourteen produced changes to the full record and, where the core schema declares the slot, to the core record by re-projection. Three were left as-is with reasons.

## Findings acted on

### 1. Unrecorded tier-1 disagreement on `publisher` (medium)

The FAIRhub API records `publisher.publisherName = "FAIRhub"`; the RO-Crate, at the same tier, records `"publisher": "AI-READI Consortium"`. The original record selected FAIRhub silently. Same-tier sources cannot be settled by the ranking, so the disagreement must be represented.

**Changed.** The `publisher` value itself is unchanged (`https://fairhub.io/`), but a new leading paragraph was added to the top-level `source_caveats` in both records naming both attributions, identifying the slot's value as the FAIRhub form, and recording that the RO-Crate's attribution to the AI-READI Consortium is preserved in the caveat rather than discarded. The conflict now sits alongside the five already documented there.

### 2. `prohibited_uses[*].prohibition_reason` carrying the prohibition (medium)

All eight entries stated the forbidden act where the schema asks why it is forbidden. The `ProhibitedUse` class accepts `notes` in addition to `prohibition_reason`.

**Changed.** All eight entries were restructured in both records: the forbidden use moved to `notes`, and `prohibition_reason` now carries the reason drawn from the license text — "The Data are intended solely as a research resource"; "To prevent harm or injury to any Data Subject…"; "Onward recipients must themselves be bound by the same terms…"; "The watermarking identifies the licensee for security purposes"; and so on. Entry [0], which previously trailed its reason behind a restatement, now carries the reason alone.

### 3. `extension_mechanism` stating absence (medium)

The value said no mechanism exists rather than describing one.

**Removed.** The `extension_mechanism` slot is absent from both reconciled records. Its content — no mechanism for outside extension, no formal guidelines for new labels or tasks — was folded into the top-level `notes`, joining the other negative healthsheet findings already parked there (no external audit, no DPIA, no use repository).

### 4. `sensitive_elements[1]` describing the controlled-access tier (medium)

The second entry set `sensitive_elements_present: true` for a distinct release, contradicting entry [0] for the declared referent and conceding in its own notes that the material is not part of the public release.

**Removed and merged.** `sensitive_elements` now holds a single entry with `sensitive_elements_present: false` in both records; the withheld variables (racial and ethnic origins, 5-digit zip code, motor vehicle accident reports, genetic sequencing data, past health records, medications) are named within that entry's `sensitivity_details` as material held in the separate controlled-access version. The referent now carries one boolean, and the fact about the other tier survives as context rather than as a competing claim.

### 5. `sampling_strategies[0].is_sample` contradicting its siblings (medium)

`is_sample: false` sat beside a named study base, four sampling strategies, and a registered `samplingMethod: "Non-Probability Sample"`.

**Changed.** `is_sample` is now `true` in both records. A `source_caveats` was added to the entry setting out the internal conflict in full: the healthsheet's "all possible instances" and "N/A" answers on one side; the same-tier FAIRhub registration and the protocol publication's wave-sampled, EHR-screened contact pools on the other; and the reasoning for preferring `true`, with the healthsheet reading construed as a claim about completeness within the release window. The former `notes` recording the healthsheet answer was absorbed into that caveat.

### 6. `regulatory_restrictions` enum values under-caveated (low)

`confidentiality_level: restricted` and `hipaa_compliant: compliant` are the record's own mappings; the only stated level is the RO-Crate's "HL7:2N (normal)".

**Changed.** Both values are retained, but the entry's `notes` was replaced by a `source_caveats` that states explicitly that both are this record's mapping onto the schema vocabulary rather than values the bundle states, names the RO-Crate value, and gives the basis for each choice. This moves a trust annotation out of prose into the slot the schema provides for it.

### 7. `conforms_to_standard: RO_CRATE` (low)

The RO-Crate is a metadata package describing the release, obtained from a separate download, and does not appear among the nine root-level metadata files.

**Changed.** `RO_CRATE` was removed from `conforms_to_standard` in both records, leaving six values (CDS, WFDB, OMOP_CDM, ESDS, DICOM, OPEN_MHEALTH). The RO-Crate description remains in the `conforms_to` prose, and a sentence in the top-level `notes` now explains why it is recorded there rather than as a standard the dataset's own layout follows.

### 8. `distribution_formats[4]` carrying an access route (low)

The entry's substance was access conditions already stated in `data_governance.access_review_process`.

**Changed.** The entry survives but was rewritten in both records: the access-condition sentences (verified-ID login, self-attestation, license acceptance) were dropped, the self-classifying opening ("Access method rather than file format") was replaced by "Delivery of the release", and the `access_urls` list was reduced to the access page alone. The mini-subset and Azure Storage delivery routes, which are genuinely about how the release is obtained and are not duplicated elsewhere, were kept.

### 9. `distribution_formats[3].format` left empty for DICOM (low)

**Changed.** The DICOM entry was promoted to first position in both records and now carries `media_type: application/dicom` — the value the FAIRhub `format` array states — plus an `access_urls` entry. `format` remains unset with a note explaining that DICOM is not among the schema's enumerated `FormatEnum` values (which are CSV, TSV, XML, JSON, JSONL, YAML, HTML, PDF, DOCX, XLSX, PPTX, TXT, MD, ZIP, TAR, GZ, BZ2, XZ), so the media type is the only typed value available.

### 10. `funders[2]` recording in-kind cloud support as a grantor (low)

**Removed.** The Microsoft AI for Good Lab entry is absent from `funders` in both reconciled records; the slot now holds two entries. The acknowledgment was moved to the top-level `notes` alongside the device loans (Topcon, Optomed, iCare World, Carl Zeiss) and research discounts (Heidelberg, Dexcom, Garmin), which the original had also excluded from `funders` — the treatment is now consistent across all in-kind support.

### 11. `ethical_reviews[1].reviewing_organization` coining a body name (low)

**Changed.** "AI-READI ethics and bioethics team" was removed; the entry now carries no `reviewing_organization`. Its `review_details` names the four individuals the RO-Crate lists (Camille Nebeker, Debra Mathews, Kadija Ferryman, Nicholas Evans) as named individuals, and a `source_caveats` records that no organization is given because the bundle attaches no body name to them.

### 12. `participant_compensation[0].retention_incentives` holding access accommodations (low)

**Removed.** The `retention_incentives` key is absent from the entry in both records. Transport reimbursement and rideshare assistance moved into the entry's `notes`, described as cost coverage and accessibility measures rather than incentives, matching how the IRB protocol frames them.

### 13. `related_datasets[*].target_dataset` carrying descriptive matter (low)

**Changed and expanded.** Entry [0]'s target is now the bare identifier `doi:10.60775/fairhub.2`, with the title, release date and participant count moved to `notes`. Entry [2] (the mini subset) is now `AI-READI mini subset for pipeline development`, with the FAIRhub child-dataset detail in `notes` and an explicit statement that no DOI is given for it. A new entry was **added** for version 1.0.0 (`doi:10.60775/fairhub.1`), since the bundle names it with its own DOI, date and count and the original recorded only v2.0.0.

The same pattern in `was_derived_from` was also **changed**: the parenthesised identifiers were removed, leaving the study name alone, and a new `external_resources` entry was **added** for the ClinicalTrials.gov registration NCT06002048 so that the identifier is not lost.

### 14. `subpopulations[2].subpopulation_elements_present` unset (low)

**Added.** The diabetes-severity entry now carries `subpopulation_elements_present: true` in both records, with a note explaining the asymmetry: the healthsheet withholds only sex, race and ethnicity, and the README split table reports diabetes status publicly.

### 15. `raw_data_sources[0].access_details` stating absence (low)

**Removed.** The key is absent from entry [0] in both records; the entry now carries `source_description` and `source_type` only. Entry [1]'s `access_details` was **changed** to state the access route positively — obtainable by entering into a data use agreement — rather than only recording exclusion from the public release.

### 16. Sixteen study PIs and seven collaborator organizations omitted (low)

**Changed.** The omission is retained — the bundle names the AI-READI Consortium as the dataset's sole creator, and the fifteen further individuals and seven organizations are recorded as study personnel and collaborators rather than as dataset creators. But the omission is now disclosed: `creators[0].source_caveats` was extended to name all fifteen additional PIs and all seven collaborator organizations, and to state why they are not carried as separate `Creator` entries.

### 17. Second NIH RePORTER project identifier not noted (low)

**Added.** A `source_caveats` was added to `funders[0].grants[0]` in both records recording that two project-detail identifiers appear in the bundle (10885481 in the dataset's own funding reference and the healthsheet; 10471118 in the README acknowledgment and the tier-4 RePORTER page), that the award number OT2OD032644 is identical across both, and that only the per-year project-detail record differs. A summarising sentence was also added to the top-level `source_caveats`.

## Findings left as-is

**The `publisher` value itself.** The audit questioned the silent selection, not the value. `https://fairhub.io/` is retained in both records: FAIRhub is the platform that publishes the release and mints its DOIs, and the RO-Crate's competing attribution is now recorded in `source_caveats` rather than substituted.

**`confidentiality_level` and `hipaa_compliant` enum values.** Both retained. The audit asked for the interpretation to be marked in `source_caveats` rather than only in prose, which was done; it did not argue the mappings are wrong, and no better-fitting enum value exists for either.

**`distribution_formats[4]` as an entry.** Retained rather than deleted. Once the duplicated access conditions were stripped, what remains — the mini-subset and Azure Storage delivery routes, and the note that no specialist software is required — is genuinely about how the release is obtained and appears nowhere else in the record.

## Structural side-effects of reconciliation

Several multivalued string slots were serialised as single concatenated strings rather than YAML lists during re-projection: `is_deidentified.identifiers_removed`, `sampling_strategies[0].strategies`, `missing_data_documentation[0].missing_data_patterns` and `.missing_data_causes`, `participant_privacy[0].privacy_techniques`, and `license_and_use_terms.license_terms`. `instances[0].missing_information[0].missing` moved in the opposite direction, from a scalar to a single-item list. The semantic content is unchanged in each case; only the serialisation differs from the original.

## Core record

The core record was re-projected from the reconciled full record. Every change above propagates to the core where the core schema declares the slot. `citation`, `total_file_count`, `total_size_bytes`, `consent_revocations`, `collection_consents`, `collection_notifications`, `direct_collection`, `relationships`, `splits`, `subsets`, `variables`, `file_collections` (as `distributions`), `third_party_sharing` and `participant_compensation` behave as before: those the core schema does not declare are absent from it, and `file_collections` remains projected into `distributions` with `total_bytes` rendered as `bytes` and `file_count` dropped.

Two changes are full-only because the core schema does not declare the slot: the `extension_mechanism` removal (the slot is absent from both, but the core never carried it) is in fact reflected in both, and `participant_compensation[0].retention_incentives` is full-only.

## Dispositions

| slot | disposition | record | reason |
|---|---|---|---|
| `publisher` | retained | both | Tier-1 conflict with the RO-Crate now recorded in top-level `source_caveats`; FAIRhub value kept as the platform that publishes and mints DOIs. |
| `source_caveats` | changed | both | New leading paragraph records the publisher conflict; sampling and RePORTER-identifier conflicts summarised. |
| `prohibited_uses[0].prohibition_reason` | changed | both | Prohibition moved to `notes`; reason ("intended solely as a research resource") now stands alone. |
| `prohibited_uses[0].notes` | added | both | Carries the forbidden act displaced from `prohibition_reason`. |
| `prohibited_uses[1].prohibition_reason` | changed | both | Now states the reason (preventing harm to Data Subjects) rather than the prohibition. |
| `prohibited_uses[1].notes` | added | both | Carries the forbidden act. |
| `prohibited_uses[2].prohibition_reason` | changed | both | Now states the license's protective rationale for the model-vendor restriction. |
| `prohibited_uses[2].notes` | added | both | Carries the forbidden act. |
| `prohibited_uses[3].prohibition_reason` | changed | both | Now states why onward transfer is bounded. |
| `prohibited_uses[3].notes` | added | both | Carries the forbidden act. |
| `prohibited_uses[4].prohibition_reason` | changed | both | Now states that bulk publication falls outside the granted license. |
| `prohibited_uses[4].notes` | added | both | Carries the forbidden act. |
| `prohibited_uses[5].prohibition_reason` | changed | both | Now states the consent and access basis for the T2DM restriction. |
| `prohibited_uses[5].notes` | added | both | Carries the forbidden use. |
| `prohibited_uses[6].prohibition_reason` | changed | both | Now states that watermarking identifies the licensee. |
| `prohibited_uses[6].notes` | added | both | Carries the forbidden act. |
| `prohibited_uses[7].prohibition_reason` | changed | both | Now cites the NIH GDS Policy security standards. |
| `prohibited_uses[7].notes` | added | both | Carries the forbidden act. |
| `extension_mechanism` | removed | both | Value stated the absence of the mechanism; content moved to top-level `notes`. |
| `sensitive_elements[1]` | removed | both | Described the controlled-access tier, not the declared referent; content merged into the single remaining entry. |
| `sensitive_elements[0].sensitivity_details` | changed | both | Now names the withheld sensitive variables as held in the separate controlled-access version. |
| `sampling_strategies[0].is_sample` | changed | both | Set `true` on the registered "Non-Probability Sample" method and documented wave sampling. |
| `sampling_strategies[0].source_caveats` | added | both | Records the healthsheet-versus-registration conflict and the basis for preferring `true`. |
| `sampling_strategies[0].notes` | removed | both | Content absorbed into the new `source_caveats`. |
| `regulatory_restrictions.confidentiality_level` | retained | both | No better-fitting enum value; interpretive basis now marked in `source_caveats`. |
| `regulatory_restrictions.hipaa_compliant` | retained | both | Inference retained; basis now marked in `source_caveats`. |
| `regulatory_restrictions.source_caveats` | added | both | States that both enum values are this record's mapping, not stated values. |
| `regulatory_restrictions.notes` | removed | both | Superseded by `source_caveats`. |
| `conforms_to_standard` | changed | both | `RO_CRATE` removed; the RO-Crate describes the release rather than governing its layout. |
| `distribution_formats[0]` | added | both | DICOM entry promoted to first position with `media_type: application/dicom`. |
| `distribution_formats[4]` | changed | both | Duplicated access conditions stripped; retained for the mini-subset and Azure delivery routes. |
| `funders[2]` | removed | both | Microsoft in-kind cloud support is not grant funding; moved to top-level `notes`. |
| `funders[0].grants[0].source_caveats` | added | both | Records the two RePORTER project-detail identifiers for one award. |
| `creators[0].source_caveats` | changed | both | Extended to disclose the fifteen further study PIs and seven collaborator organizations, and why they are not Creator entries. |
| `ethical_reviews[1].reviewing_organization` | removed | both | Coined body name; the bundle names only four individuals. |
| `ethical_reviews[1].source_caveats` | added | both | Explains the absent organization name. |
| `participant_compensation[0].retention_incentives` | removed | full | Transport reimbursement and rideshare assistance are access accommodations, not retention incentives; moved to `notes`. |
| `participant_compensation[0].notes` | changed | full | Absorbs the displaced transport and accessibility content. |
| `related_datasets[0].target_dataset` | changed | both | Reduced to the bare DOI; descriptive matter moved to `notes`. |
| `related_datasets[1]` | added | both | Version 1.0.0 (`doi:10.60775/fairhub.1`), previously omitted though named with DOI, date and count. |
| `related_datasets[2].target_dataset` | changed | both | Parenthesised FAIRhub child-dataset detail moved to `notes`. |
| `was_derived_from` | changed | both | Embedded NCT and award identifiers removed; study name alone retained. |
| `external_resources[6]` | added | both | ClinicalTrials.gov NCT06002048 preserved as a typed external resource. |
| `subpopulations[2].subpopulation_elements_present` | added | both | Set `true`; diabetes status is released publicly, unlike sex and race/ethnicity. |
| `raw_data_sources[0].access_details` | removed | both | Stated that access details do not exist rather than supplying them. |
| `raw_data_sources[1].access_details` | changed | both | Now states the data-use-agreement route positively. |
| `notes` | changed | both | Absorbs the extension-mechanism absence, the RO-Crate scope explanation, and the in-kind support acknowledgments. |