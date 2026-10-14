# Phase 4 Reconciliation Report — AI_READI

**Version label:** `2026-08-13_claude-opus-5-api-generic-v4_rep3`
**Arm:** BASELINE (input documents only)
**Declared input bundle:** `data/preprocessed/concatenated/AI_READI_preprocessed.txt`
**Records reconciled:**
- Full — `data/d4d_concatenated/claudecode_agent/2026-08-13_claude-opus-5-api-generic-v4_rep3/AI_READI_d4d.yaml`
- Core — `data/d4d_concatenated/claudecode_agent_core/2026-08-13_claude-opus-5-api-generic-v4_rep3/AI_READI_d4d_core.yaml`

---

## 1. Referent

Both records describe a single referent: **the Flagship Dataset of Type 2 Diabetes from the AI-READI Project, version 3.0.0**, DOI `10.60775/fairhub.3`, released 2025-11-17, comprising data from 2,280 participants collected 2023-07-19 to 2025-05-01. This is distinguished throughout from (a) the AI-READI *study/project* (NIH OT2OD032644, target enrolment 4,000, ClinicalTrials.gov NCT06002048) and (b) the earlier dataset versions 1.0.0 and 2.0.0, which are recorded as related datasets rather than as the subject. The referent choice was already consistent across both records before reconciliation and was not disturbed.

---

## 2. What the audit found

The audit returned twenty findings: two high, eight medium, ten low. No hallucinated dataset facts were identified, and no source commentary was found embedded in a name, identifier or affiliation value. The defects cluster into four patterns.

**(a) One invented slot in the core record (high).** The core record carried an eleven-entry `distributions` block. No such slot exists in the `CoreDataset`/`Dataset` inventory. Its keys (`path`, `bytes`, `format`, `media_type`) correspond to no declared range. Every entry additionally omitted `id`, which is the required key on `FileCollection` — the only declared range that accepts per-directory paths, file counts and byte totals. This would have failed validation on twelve independent counts.

**(b) Cascading omissions in the core record traceable to (a) (medium).** Because the per-directory content had been diverted into a non-schema slot, `file_collections`, `total_file_count` and `total_size_bytes` were all dropped from the core record despite being stated explicitly in the bundle and populated correctly in the full record.

**(c) Structured content migrated into free text in the core record (medium).** `citation`, `splits`, `participant_compensation`, `collection_consents`, `collection_notifications`, `consent_revocations`, `direct_collection` and `participant_privacy` are each supported by the bundle and each populated in the full record, but appeared in the core record only as prose — inside `notes`, inside `informed_consent` sub-fields, inside `is_deidentified.deidentification_details`, or inside an `acquisition_methods` note. The last of these also produced a mild internal contradiction: text asserting direct collection sat under an object whose boolean was `was_inferred_derived: true`.

**(d) Minor structural weaknesses in the full record (low).** An empty `annotation_analyses: []`; seven in-kind contributors collapsed into a single `grantor` string; a root-metadata `FileCollection` missing a supported `file_count`; and the recommended-split table transcribed four times across `subsets`, `splits`, `subpopulations` and (in the core record) `notes`.

Two enum choices in both records — `confidentiality_level: restricted` and `data_use_permission: disease_specific_research` — were flagged as interpretive mappings of two-tier access onto single-valued fields rather than verbatim source statements.

---

## 3. Changes to the core record

| # | Slot | Change | Reason |
|---|---|---|---|
| 1 | `distributions` | **Removed.** | Not in the declared slot inventory. An invented slot is a validation failure and a schema-fidelity defect regardless of the accuracy of its contents. |
| 2 | `file_collections` | **Added**, ten `FileCollection` objects, each with `id`, `path`, `collection_type`, `file_count`, `total_bytes` and, where the bundle names one, `conforms_to` and `conforms_to_standard`. | This is the declared home for the per-directory content that `distributions` had been carrying. All ten entries are transcribed from `fairhub_api_dataset_3` `dataset_structure_description.directoryList[*].size` / `.numberOfFiles` and the root `metadataFileList`. Mirrors the full record exactly. |
| 3 | `total_file_count` | **Added:** `356343`. | Stated three times in the bundle (`data.fileCount`, README, RO-Crate `contentSize` context). Was present only as prose in a `distributions` note. |
| 4 | `total_size_bytes` | **Added:** `3815969779678`. | Stated in `data.size` and `datasetDescription.size` ("3.82 TB"). Same rationale as (3). |
| 5 | `citation` | **Added**, verbatim from RO-Crate `associatedPublication`. | The bundle supplies a complete formatted dataset citation. Notes is for residual content only after every fitting slot is used; a declared `citation` slot was available. |
| 6 | `splits` | **Added**, one `Splits` object carrying the 70/15/15 proportions, the balancing criteria and the per-stratum counts. | README "Suggested split" table plus healthsheet labeling Q7. Content was previously in `notes` prose. |
| 7 | `participant_compensation` | **Added**, one `HumanSubjectCompensation` object (`compensation_provided: true`, amount `$200`, type, rationale, non-proration). | Healthsheet collection Q4 and the IRB protocol state the amount, source of funds and payment schedule. |
| 8 | `collection_consents`, `collection_notifications`, `consent_revocations` | **Added** as three separate objects. | The bundle answers each question separately (healthsheet collection Q9, Q8, Q10). Folding all three into `informed_consent` sub-fields put notification content inside a documentation field. |
| 9 | `direct_collection` | **Added**, one `DirectCollection` object with `is_direct: true`. | Healthsheet collection Q7. Resolves the internal contradiction noted at (c): the assertion no longer sits under a `was_inferred_derived` acquisition object. |
| 10 | `acquisition_methods[2].notes` | **Trimmed** — the direct-collection sentence removed, having been relocated to (9). | The note answered a neighbouring slot and contradicted its own object's boolean. |
| 11 | `participant_privacy` | **Added**, one `ParticipantPrivacy` object with `anonymization_method`, `privacy_techniques`, `data_linkage` and `reidentification_risk`. | Supported by the Nature Metabolism comment (watermarking, dissemination controls), licence §3.B and §6, and healthsheet composition Q14 / uses Q4. Mirrors the full record. |
| 12 | `is_deidentified.deidentification_details` | **Trimmed** — re-identification-risk sentence removed, having been relocated to `participant_privacy.reidentification_risk` at (11). | Content belonged in the field the schema declares for it. The HIPAA Safe Harbor and "no identifiers collected" statements remain in place. |
| 13 | `distribution_formats` | **Verified** against the four media types in `datasetDescription.format`; per-directory standards moved onto the corresponding `FileCollection.conforms_to_standard` rather than duplicated here. | Avoids restating directory-level facts at dataset level. |
| 14 | `notes` | **Substantially shortened.** Split table, citation requirement, compensation and file/byte totals removed, all now held in declared slots. | Notes is residual-only. |
| 15 | `funders` | **Expanded** from three to ten `FundingMechanism` objects (see full-record change 3 below). | Applied identically in both records. |
| 16 | `source_caveats` | **Retained** item (13) on healthsheet questions answered "No"/"N/A"; a matching item **added to the full record** so the two records' trust annotations no longer diverge. | The modelling decision is identical in both records and should be annotated identically. Two further items added (see §5). |

---

## 4. Changes to the full record

| # | Slot | Change | Reason |
|---|---|---|---|
| 1 | `annotation_analyses` | **Removed** (was `[]`). | An empty list is not equivalent to omission and carries no information. The absence of annotation is already stated positively in `instances[0].label_description` and in the labeling `source_caveats` item. |
| 2 | `file_collections[9].file_count` | **Added:** `9`. | The bundle enumerates nine named root metadata files in `metadataFileList` (CHANGELOG.md, dataset_description.json, dataset_structure_description.json, healthsheet.md, LICENSE.txt, participants.json, participants.tsv, README.md, study_description.json). Directly supported, not derived. `total_bytes` remains omitted — the bundle gives no size for the root level. |
| 3 | `funders` | **Split** the third `FundingMechanism` into eight separate objects, one per in-kind contributor: Microsoft AI for Good Lab (cloud services); Topcon Corporation, Optomed, iCare World, Carl Zeiss (device loans at no cost); Heidelberg Engineering, Dexcom, Garmin (research discounts on study devices). Each carries the contributor in `grantor` and the form of contribution in `notes`. | The multivalued-range rule requires one object per distinct entity. The prior encoding collapsed seven entities into one `grantor` value and put narrative into an identifier-like field. Applied identically to the core record. |
| 4 | `subsets[*].description` | **Trimmed** — per-stratum counts removed; each subset retains its identity, `is_data_split: true` and its proportion. | The counts are now held once, authoritatively, in `splits.split_details`. Four transcriptions of one README table left no single authoritative location and multiplied the surface for transcription error. `subpopulations` retains its own `distribution` values, which describe the whole-cohort composition rather than the split. |
| 5 | `source_caveats` | **Three items added** (see §5). | Alignment with the core record plus explicit annotation of two enum mappings. |

---

## 5. Source caveats added to both records

1. **Healthsheet negative answers.** Mirrors the core record's item (13): the healthsheet answers "No", "N/A" or empty to questions on prior auditing, explicit labels, subpopulation identification in the public release, existing uses, use-tracking repositories, errata, extension mechanisms, retention limits, confidential elements and data protection impact assessment. The corresponding slots are unpopulated by design, not by oversight.

2. **`confidentiality_level` mapping.** The bundle's only explicit statement is the RO-Crate `confidentialityLevel: "HL7:2N (normal)"`. The enum offers no equivalent term. `restricted` was selected on the strength of the access controls the bundle does state (verified-ID login, use attestation, licence obligations, a separate controlled tier), and the verbatim HL7 wording is preserved in `regulatory_restrictions.other_compliance`. The mapping is an interpretation, not a transcription.

3. **`data_use_permission` mapping.** `disease_specific_research` describes the public tier accurately ("Agreeing to use the data only for type 2 diabetes related research"). The bundle also states that the licence permits commercial use and that "A private version will allow for more generic use". The single-valued enum cannot represent both tiers; the qualification is carried in `license_and_use_terms.license_terms`.

---

## 6. Findings left as-is, with rationale

**`creators[0]` modelled as an affiliation-only object (low, both records).** The bundle's sole creator declaration is `creatorName: "AI-READI Consortium"` with `nameType: "Organizational"`. The `Creator` class as declared accepts `affiliations` (`Organization[]`), `principal_investigator` (`Person`) and `credit_roles` — it declares no field for an organizational creator's own name. Placing the Consortium in `affiliations` is the closest available fit; inventing a key on `Creator` would repeat the defect corrected at core change (1). Left unchanged and noted here rather than in `source_caveats`, since this is a schema-expressiveness limit rather than an evidence problem.

**`instances[0].data_substrate` omitted (low, both records).** The bundle names at least four substrates directly (DICOM, waveform data, CSV, time-series) and supports several more. The range is single-valued. Selecting one would assert a primacy the bundle does not support for a deliberately multimodal dataset; the digest's instruction is to omit rather than approximate. The substrate inventory is instead recoverable from `file_collections[*].conforms_to_standard` and `distribution_formats`. Left omitted.

**`instances[0].data_topic: B2AI_TOPIC:43` (Diabetes) (low, both records).** Same single-valued constraint. Diabetes is the organising subject of the dataset — it is the disease in the title, the sampling stratum, and the stated scientific purpose — whereas the imaging, waveform, mHealth and survey terms describe modalities already captured structurally elsewhere. Retained.

**`conforms_to_standard: ESDS` (low, both records).** The README's phrase "Earth Science Data Systems (ESDS) format" points at the NASA ASCII File Format Guidelines rather than at a formally registered standard identifier. The enum offers `ESDS` and the bundle uses that name; retaining it is transcription, not inference. The underlying document is identified in the corresponding `FileCollection.conforms_to`.

**Duplicate assertion of the Washington University in St. Louis / University of Washington conflict (low, full record).** The conflict is annotated once at top level in `source_caveats` and once on `creators[1].source_caveats`. Duplication of a trust annotation is not a defect and the object-level placement is useful where a reader inspects the creator in isolation. However, the audit's related observation — that the conflict is resolved inconsistently across three sibling Creator objects (ROR 01yc7t268 for Aaron Y. Lee and Cecilia S. Lee; UC San Diego for Linda M. Zangwill) — reflects the bundle itself: the FAIRhub `overallOfficialList` gives exactly those affiliations for exactly those individuals. The inconsistency is in the source, is now explicitly flagged in the top-level caveat, and was not silently normalised.

---

## 7. Post-reconciliation state

| | Before | After |
|---|---|---|
| Full record — populated top-level slots | 72 | 71 |
| Core record — populated top-level slots | 46 | 56 |

Full-record count decreased by one (removal of the empty `annotation_analyses`); object-level enrichments (funders split, root `file_count`) do not change the top-level count. Core-record count increased by ten (eleven slots added, one invented slot removed).

**Validation**

```
poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_all.yaml \
  -C Dataset data/d4d_concatenated/claudecode_agent/2026-08-13_claude-opus-5-api-generic-v4_rep3/AI_READI_d4d.yaml
→ PASS

poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml \
  -C CoreDataset data/d4d_concatenated/claudecode_agent_core/2026-08-13_claude-opus-5-api-generic-v4_rep3/AI_READI_d4d_core.yaml
→ PASS
```

**Consistency between records.** The referent, the four unresolved source conflicts (acronym expansion, lead institution, enrolment start date, target N), the de-identification characterisation, the enum mappings and the `source_caveats` inventory are now identical in substance across both records. The core record is a strict projection of the full record: every core slot is present in the full record with the same value, and no core slot asserts anything the full record does not.

**Provenance.** Recorded via `d4d provenance record` for project `AI_READI`, method `claudecode_agent`, label `2026-08-13_claude-opus-5-api-generic-v4_rep3`, input bundle as declared above.

**Prior D4D reuse.** None. No file under `data/d4d_concatenated/` or `data/ro-crate_packages/` other than the two outputs of this run was read at any phase.