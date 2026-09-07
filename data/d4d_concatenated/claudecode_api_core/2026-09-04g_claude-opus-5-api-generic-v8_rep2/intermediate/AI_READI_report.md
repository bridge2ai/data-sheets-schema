# Reconciliation Report — AI_READI

## Scope

Phase 3 returned seventeen findings against the full record: one unrecorded tier-1 conflict, two neighbouring-field placements, two absence-statements standing in for answers, one referent breach, one internal inconsistency, two insufficiently caveated interpretive enum values, one scope question on a `conforms_to_standard` value, three misplacements or coinages, two commentary-in-value cases, and three supported omissions. The audit found no fabricated facts, and confirmed that the arithmetic, the enum values, the CURIE/URI discipline and the required object keys all held.

Phase 4 applied changes for fifteen of the seventeen; two were left as-is with reasons recorded below. The core record was re-projected from the reconciled full record so that every shared slot carries identical content.

---

## Changes applied

### 1. Unrecorded tier-1 publisher conflict (medium)

The FAIRhub API gives `publisher.publisherName = "FAIRhub"`; the RO-Crate, same tier, gives `"publisher": "AI-READI Consortium"`. The original record selected FAIRhub silently.

The `publisher` slot value is unchanged (`https://fairhub.io/`), but the top-level `source_caveats` now opens with a new paragraph recording the disagreement, naming both values and both sources, and stating that the shared tier means the ranking cannot decide, so the RO-Crate attribution is recorded rather than discarded. Applied to both records.

### 2. Prohibitions written into `prohibition_reason` (medium)

All eight `prohibited_uses` entries stated the prohibited act in the field that asks *why* the act is forbidden. Each entry was rewritten: the forbidden use moved to `notes`, and `prohibition_reason` now carries the reason the license gives or implies. For example, entry [0] now reads `notes: Making clinical treatment decisions based on the Data.` with `prohibition_reason: The Data are intended solely as a research resource.` Entry [7]'s storage restriction now cites the NIH Genomic Data Sharing Policy as its reason. Applied to both records; the slot still holds eight entries.

### 3. `extension_mechanism` as an absence-statement (medium)

The slot stated that no extension mechanism exists. It has been removed from both records, and the healthsheet's negative answer moved into the top-level `notes`, which already parked the other negative healthsheet findings (no external audit, no DPIA, no use repository). The "no formal guidelines for creating new labels or defining new tasks" clause moved with it.

### 4. `sensitive_elements[1]` describing the controlled-access tier (medium)

The second entry set `sensitive_elements_present: true` for a release that is not the declared referent, and its own notes conceded as much. The entry was removed. The material it carried — racial and ethnic origins, 5-digit zip code, motor vehicle accident reports, genetic sequencing data, past health records, medications — is now stated inside `sensitive_elements[0].sensitivity_details` as variables *withheld from this release and held in the separate controlled-access version*, which is a fact about the referent. The slot now holds one entry with `sensitive_elements_present: false`. Applied to both records.

### 5. `sampling_strategies[0].is_sample` internal inconsistency (medium)

`is_sample: false` sat beside a stated study base, four sampling strategies, a `why_not_representative` value and a tier-1 registered `samplingMethod: "Non-Probability Sample"`. The boolean was changed to `true`, and a `source_caveats` key added to the entry recording the healthsheet's "all possible instances" answer, the countervailing FAIRhub registration and protocol description, and the reasoning for the value chosen. The top-level `source_caveats` gained a one-line pointer to that entry. Applied to both records.

### 6. Interpretive enum values in `regulatory_restrictions` (low)

`confidentiality_level: restricted` and `hipaa_compliant: compliant` are both this record's mappings, not stated values. Both values are retained, but the explanation moved out of `notes` into a new `source_caveats` key on the object, which states plainly that neither value is stated by the bundle, that the only stated confidentiality level is "HL7:2N (normal)", and what each value was inferred from. The `notes` key was dropped as redundant. Applied to both records.

### 7. `conforms_to_standard: RO_CRATE` (low)

The RO-Crate is a metadata package describing the release, obtained separately, and absent from the nine root-level metadata files. `RO_CRATE` was removed from `conforms_to_standard` in both records. The `conforms_to` prose still describes the package, and the top-level `notes` gained a sentence explaining why it is recorded as prose rather than as a standard the dataset's own layout follows.

### 8. `distribution_formats` — access route and missing DICOM (low)

Two changes. First, a new entry was added at the head of the list carrying `media_type: application/dicom`, with a note explaining that DICOM leads the dataset's format list and governs all four retinal imaging directories, and that DICOM is not among the schema's enumerated `format` values so only the media type is recorded. Second, the trailing access-route entry was rewritten: its leading self-classification ("Access method rather than file format") was dropped, the access-condition text was removed as duplicative of `data_governance.access_review_process`, and it now records delivery of the release with one `access_urls` value. Applied to both records.

### 9. Microsoft AI for Good Lab as `grantor` (low)

The bundle states only in-kind cloud-services support, with no grant, contract or award, and the same acknowledgment paragraph thanks four device manufacturers and three others for discounts, none of which were recorded as funders. `funders[2]` was removed. The in-kind support — Microsoft, the loans from Topcon, Optomed, iCare World and Carl Zeiss, and the discounts from Heidelberg, Dexcom and Garmin — is now recorded together in the top-level `notes`. `funders` now holds two entries. Applied to both records.

### 10. Coined ethics-review body name (low)

"AI-READI ethics and bioethics team" is not a name the bundle uses; the RO-Crate lists four individuals with no organization attached. `ethical_reviews[1].reviewing_organization` was removed; the entry now carries only `review_details` (naming the four individuals explicitly) and a new `source_caveats` explaining that no organization is recorded because none is stated. Applied to both records.

### 11. Transport reimbursement as `retention_incentives` (low)

Neither value was stated as an incentive to remain in the study; the rideshare assistance appears in the IRB protocol under accessibility. `participant_compensation[0].retention_incentives` was removed, and its content folded into the entry's `notes` as cost coverage and accessibility measures, alongside the pre-existing USD 25 and year-4 follow-up material. Applied to both records.

### 12. Descriptive matter inside `target_dataset` (low)

`related_datasets[0].target_dataset` held a title with a parenthesised DOI, release date and participant count; entry [1] held a name with a FAIRhub child-dataset reference. Entry [0]'s target is now the bare `doi:10.60775/fairhub.2` with the descriptive matter moved to `notes`; entry [1] (now [2]) is now `AI-READI mini subset for pipeline development` with the FAIRhub child-dataset detail in `notes` and an explicit statement that no DOI is stated for it.

A third entry was also **added**: `is_new_version_of doi:10.60775/fairhub.1`, the v1.0.0 release, which the bundle attests and which the original record named only in `version_access`. `related_datasets` now holds three entries.

`was_derived_from` carried the same pattern and was also shortened to the study name alone; the ClinicalTrials.gov registration NCT06002048 that had been parenthesised inside it is now an `external_resources` entry with its registration URL, and the NIH award number is already carried by `funders`. Applied to both records.

### 13. Sixteen study PIs and seven collaborator organizations (low)

The audit is right that the FAIRhub study description lists sixteen individuals with role "Study Principal Investigator" and seven ROR-identified collaborator organizations, and that the original record noted none of the omission. The record's referent-level position is unchanged — the dataset's sole stated creator is the AI-READI Consortium, and those individuals and organizations are study personnel and collaborators rather than dataset creators — so no Creator entries were added. But the omission is now disclosed: `creators[0].source_caveats` was extended to enumerate all fifteen further named individuals and all seven organizations, and to state why they are not carried as separate Creator entries. Applied to both records.

### 14. `subpopulations[2].subpopulation_elements_present` (low)

The flag was unset while its two siblings were set false. Diabetes status *is* released publicly — the healthsheet withholds only sex, race and ethnicity, and the README split table reports diabetes counts. The flag was set to `true` and a `notes` key added recording that distinction. Applied to both records.

### 15. Second RePORTER project identifier (low)

Two project-detail records for core project OT2OD032644 appear in the bundle: 10885481 in the dataset's own funding reference and the healthsheet, 10471118 in the README acknowledgment and the tier-4 RePORTER page. A `source_caveats` key was added to `funders[0].grants[0]` recording both and noting that the award number is identical across them and only the per-year project-detail record differs; the top-level `source_caveats` gained a pointer. Applied to both records.

---

## Left as-is

### `raw_data_sources[0].access_details` (low) — retained, reworded

The audit flagged "Not separately accessible; the processed participant data constitute this dataset" as an absence-statement. The key was **removed** from entry [0] rather than reworded: for a raw source that is the participants themselves, there are no access details to give, and the relationship the clause described (the processed data *are* this dataset) is already carried by the surrounding record. Entry [1]'s `access_details` was retained and strengthened to state the route positively — the material is obtainable by entering into a data use agreement — rather than only stating that it is not in the public release.

### `distribution_formats[3].format` — the DICOM enum value

The audit asked that `format` be populated for the DICOM entry. It was not: the schema digest's `format` enum for File and DistributionFormat lists `CSV, TSV, XML, JSON, JSONL, YAML, HTML, PDF, DOCX, XLSX, PPTX, TXT, MD, ZIP, TAR, GZ, BZ2, XZ` and does not include DICOM. The new entry therefore carries `media_type: application/dicom` and states in its note why `format` is absent. This is a partial disposition of finding 8 rather than a rejection of it.

---

## Core record

The core record was re-projected from the reconciled full record. Every change above that touches a slot the core schema declares appears identically in both files. Four slots the core schema does not declare — `citation`, `total_file_count`, `total_size_bytes`, `consent_revocations`, and the others absent from the core projection — were unaffected. `extension_mechanism` is declared by the core schema and was removed from both. `file_collections`/`distributions` field-level differences (the core projection carries `bytes` where the full record carries `total_bytes` and omits `file_count`) are projection artifacts predating this reconciliation and were not altered.

Both records validate against their respective schemas.

---

## Dispositions

| slot | disposition | record | reason |
|---|---|---|---|
| `source_caveats` | changed | both | Added the unrecorded tier-1 publisher conflict (FAIRhub vs AI-READI Consortium), a pointer to the sampling-method conflict, and a pointer to the two RePORTER project identifiers. |
| `publisher` | retained | both | Value unchanged; the same-tier disagreement is now recorded in `source_caveats` rather than resolved silently. |
| `prohibited_uses[0..7].prohibition_reason` | changed | both | Each now states the reason for the prohibition; the prohibited act moved to the entry's `notes`. |
| `prohibited_uses[0..7].notes` | added | both | Carries the forbidden use that previously occupied `prohibition_reason`. |
| `extension_mechanism` | removed | both | Stated that no such mechanism exists rather than answering the field; content moved to top-level `notes`. |
| `sensitive_elements[1]` | removed | both | Described the controlled-access release, not the declared referent; its substance folded into `sensitive_elements[0].sensitivity_details` as material withheld from this release. |
| `sensitive_elements[0].sensitivity_details` | changed | both | Now names the sensitive variables collected by the study and states that they are withheld from this release. |
| `sampling_strategies[0].is_sample` | changed | both | Set true, consistent with the registered "Non-Probability Sample" method and the record's own documented wave sampling. |
| `sampling_strategies[0].source_caveats` | added | both | Records the healthsheet/FAIRhub conflict on whether the dataset is a sample, and the basis for the value chosen. |
| `sampling_strategies[0].notes` | removed | both | Its content (the healthsheet "all possible instances" reading) is now carried by `source_caveats`. |
| `regulatory_restrictions.source_caveats` | added | both | States that `confidentiality_level` and `hipaa_compliant` are this record's mappings, not stated values, and what each was inferred from. |
| `regulatory_restrictions.notes` | removed | both | Superseded by `source_caveats`. |
| `regulatory_restrictions.confidentiality_level` | retained | both | Value kept; the interpretive basis is now caveated rather than only noted. |
| `regulatory_restrictions.hipaa_compliant` | retained | both | Value kept; the interpretive basis is now caveated. |
| `conforms_to_standard` | changed | both | `RO_CRATE` removed: the RO-Crate describes the release, is distributed separately, and is absent from the root metadata file list. |
| `conforms_to` | retained | both | Prose unchanged; it correctly describes the RO-Crate as a separate metadata package. |
| `distribution_formats[0]` | added | both | New DICOM entry carrying `media_type: application/dicom`; DICOM leads the stated format list and governs all four retinal imaging directories. |
| `distribution_formats[0].format` | retained | both | Not populated: DICOM is not among the schema's enumerated `format` values, which the entry's note records. |
| `distribution_formats[4]` | changed | both | Rewritten as delivery of the release; the leading self-classification and the access conditions duplicated from `data_governance.access_review_process` were dropped, leaving one `access_urls` value. |
| `funders[2]` | removed | both | Microsoft AI for Good Lab is acknowledged for in-kind cloud services, not as a grantor; recorded in top-level `notes` alongside the device loans and discounts. |
| `funders[0].grants[0].source_caveats` | added | both | Records the two NIH RePORTER project-detail identifiers (10885481, 10471118) for the same award number. |
| `ethical_reviews[1].reviewing_organization` | removed | both | "AI-READI ethics and bioethics team" is a coinage; the RO-Crate names four individuals with no body attached. |
| `ethical_reviews[1].source_caveats` | added | both | States that no reviewing organization is recorded because the bundle names none. |
| `participant_compensation[0].retention_incentives` | removed | both | Transport reimbursement and rideshare assistance are cost coverage and accessibility measures, not retention incentives; moved to the entry's `notes`. |
| `participant_compensation[0].notes` | changed | both | Now carries the transport cost coverage and rideshare assistance, framed as the IRB protocol frames them. |
| `related_datasets[0].target_dataset` | changed | both | Reduced to the bare DOI `doi:10.60775/fairhub.2`; title, date and participant count moved to `notes`. |
| `related_datasets[1]` | added | both | The v1.0.0 release (`doi:10.60775/fairhub.1`), attested by the bundle and previously named only in `version_access`. |
| `related_datasets[2].target_dataset` | changed | both | Reduced to the subset's name; the FAIRhub child-dataset detail moved to `notes`, which also states that no DOI is given for it. |
| `was_derived_from` | changed | both | Reduced to the study name; the parenthesised ClinicalTrials.gov and NIH award identifiers moved to `external_resources` and `funders` respectively. |
| `external_resources[6]` | added | both | ClinicalTrials.gov registration NCT06002048, previously carried only inside `was_derived_from`. |
| `creators` | retained | both | Still one entry: the dataset's sole stated creator is the AI-READI Consortium. |
| `creators[0].source_caveats` | changed | both | Extended to enumerate the fifteen further named study PIs and the seven collaborator organizations, and to state why they are not carried as Creator entries. |
| `subpopulations[2].subpopulation_elements_present` | added | both | Set true: unlike sex and race/ethnicity, diabetes status is released publicly. |
| `subpopulations[2].notes` | added | both | Records the distinction from the two withheld sibling attributes. |
| `raw_data_sources[0].access_details` | removed | both | For the participants themselves there are no access details to state; the clause only asserted absence. |
| `raw_data_sources[1].access_details` | changed | both | Now states the route positively — obtainable by entering into a data use agreement — rather than only that the material is not in the public release. |
| `notes` | changed | both | Absorbed the extension-mechanism and labeling-guidelines negatives, the in-kind support paragraph, and the explanation for recording the RO-Crate in prose rather than in `conforms_to_standard`. |