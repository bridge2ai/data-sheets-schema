# AI_READI D4D Reconciliation Report

**Version label:** `2026-08-11_claude-opus-5-api-generic_rep2`
**Arm:** BASELINE (input documents only)
**Source bundle:** `data/preprocessed/concatenated/AI_READI_preprocessed.txt`
**Phase:** 4 — strict reconciliation following Phase 3 source/provenance audit

---

## 1. Referent decision

`Dataset` admits one referent. Both records are scoped to **"Flagship Dataset of Type 2 Diabetes from the AI-READI Project", version 3.0.0**, DOI `10.60775/fairhub.3`, released 2025-11-17, comprising data from 2,280 participants collected 2023-07-19 through 2025-05-01. This is the version for which the declared bundle supplies the most complete structured evidence (FAIRhub API record, v3 documentation page, v3 healthsheet, v3 landing page).

Version 1.0.0 and 2.0.0 are represented as `related_datasets` (`is_previous_version_of`) and in `version_access`, not as the record's subject. The BMJ Open protocol and NIH RePORTER project describe the *study* that generates the dataset; facts drawn from them are used to populate collection, ethics and motivation slots for this dataset version, not to shift the referent to the study itself.

This choice is held identically across both files.

---

## 2. Audit outcome summary

The audit found **no fabricated dataset facts**. Every substantive claim in both records traces to a document in the declared bundle. Spot-verified figures — 2,280 participants; 356,343 files; 3,815,969,779,678 bytes; per-directory sizes and counts across all nine datatype directories; the 70/15/15 split composition with its race/ethnicity, sex and diabetes-status cells; IRB approval STUDY00016228; grant OT2OD032644; collection window 2023-07-19/2025-05-01 — all match the bundle exactly.

The twenty-four findings were structural: one invented slot, one manufactured negative assertion, and a cluster of slot-shape problems repeated across both files.

---

## 3. Changes made

### 3.1 Core — `distributions` slot removed and re-expressed (HIGH)

**Finding:** The core record carried a slot named `distributions` that does not appear in the schema inventory, using keys (`path`, `bytes`, `format`, `media_type`) that correspond to no defined range. `bytes` in particular is not an accepted key anywhere; `FileCollection` uses `total_bytes`.

**Change:** The slot was deleted. Its content was re-expressed as `file_collections` objects, each carrying the required `id` plus the schema-defined `path`, `file_count`, `total_bytes`, `collection_type` and `conforms_to`. Per-directory file counts that had been buried in `notes` prose (4,515 / 7 / 2,232 / 7,969 / 56,478 / 173,721 / 93,921 / 15,245 / 2,246) now occupy the structured `file_count` key. `total_file_count: 356343` and `total_size_bytes: 3815969779678` were added as top-level structured values rather than left embedded in `description` prose.

**Rationale:** Invented keys are a defect under the provenance guard (#380), and the instruction to use structured slots before description before notes (#385) was being inverted.

### 3.2 Core — `imputation_protocols` removed (MEDIUM)

**Finding:** The core record asserted an `ImputationProtocol` with `imputation_method: "None. No imputation protocol was applied…"`. The bundle's healthsheet is silent on imputation; it neither states that imputation was applied nor that it was considered and declined.

**Change:** The slot was deleted from the core record.

**Rationale:** This was a negative assertion manufactured to occupy a slot. The genuinely evidenced content — that missing modalities arise from participant opt-out, device failure and data collision, and are left as-is — is already carried accurately in `missing_data_documentation.handling_strategy`. The full record correctly omitted this slot; deletion restores consistency in the direction of less unsupported content.

### 3.3 Both — `principal_investigator` name values cleaned (MEDIUM)

**Finding:** `principal_investigator: "Aaron Y. Lee (study principal investigator; responsible party)"` embedded role commentary inside a person-name value.

**Change:** The value is now `"Aaron Y. Lee"`. The role information moved to `credit_roles` (already populated with `supervision`, `project_administration`, `funding_acquisition`) and to `notes`, where the FAIRhub `responsibleParty` designation is recorded.

**Rationale:** A name slot takes a name.

### 3.4 Both — PI affiliation conflict encoding made consistent (MEDIUM)

**Finding:** Aaron Y. Lee was given two mutually exclusive `affiliations` — "University of Washington" and "Washington University in St. Louis" — as though held concurrently. The bundle establishes this as a FAIRhub metadata error, not dual affiliation. Worse, the same treatment was not applied to Cecilia S. Lee or Sally L. Baxter, who are subject to the identical error in the same FAIRhub record.

**Change:** Each affected creator now carries the single affiliation supported by the corroborating sources — University of Washington for Aaron Y. Lee and Cecilia S. Lee (per the Nature Metabolism author affiliation list, the BMJ Open author list, the NIH RePORTER organization field, and the UW IRB protocol), University of California San Diego for Sally L. Baxter (per the same three sources). The FAIRhub attribution to "Washington University in St. Louis" is recorded once, at dataset level, in `source_caveats`.

**Rationale:** The affiliation list was asserting a fact the bundle contradicts. Documenting a conflict in `source_caveats` is correct; also encoding the erroneous limb as a structured value is not. Applying the fix to all three affected PIs removes the internal inconsistency.

### 3.5 Both — `funders` grantor corrected (MEDIUM)

**Finding:** `grantor: "In-kind industry support"` placed a category label in a slot whose semantics call for a named organization, with the actual entities relegated to `notes` — and the note itself conceded "This is acknowledged support rather than a grant."

**Change:** The third `FundingMechanism` entry was removed. The in-kind contributions (Microsoft AI for Good Lab cloud services; device loans from Topcon, Optomed, iCare World and Carl Zeiss; research discounts from Heidelberg Engineering, Dexcom and Garmin) are recorded in dataset-level `notes` as acknowledged support. The two genuine funding mechanisms — NIH (grants OT2OD032644, P30DK035816, UL1TR003096) and Research to Prevent Blindness — are retained unchanged.

**Rationale:** In-kind equipment loans are not a granting relationship. The information is preserved; it is no longer misfiled.

### 3.6 Full — truncated `source_caveats` completed (MEDIUM)

**Finding:** The caveat on the `root_metadata` file collection read "354,088… plus per-directory manifests already included", leaving an unfinished and unverifiable arithmetic claim.

**Change:** Replaced with a clean statement: the nine datatype directories sum to 356,334 files; the FAIRhub-reported total is 356,343; the difference of 9 corresponds exactly to the nine root-level metadata files enumerated in the `metadataFileList` (CHANGELOG.md, dataset_description.json, dataset_structure_description.json, healthsheet.md, LICENSE.txt, participants.json, participants.tsv, README.md, study_description.json).

**Rationale:** The arithmetic reconciles cleanly; the caveat should say so rather than trail off.

### 3.7 Full — documentation URL removed from `related_datasets` (MEDIUM)

**Finding:** A `DatasetRelationship` with `relationship_type: is_documented_by` targeted `https://docs.aireadi.org/`, a documentation website. The record's own caveat conceded the target "is a documentation resource rather than a dataset".

**Change:** The entry was removed from `related_datasets`. The URL is retained in `external_resources`, where it was already correctly present alongside `https://aireadi.org/`, with the FAIRhub `IsDocumentedBy` relation type noted there.

**Rationale:** `related_datasets` is typed for dataset targets. Keeping the same resource in two slots, one of them mistyped, adds no information.

### 3.8 Both — `is_deidentified` scoping made explicit (MEDIUM)

**Finding:** `identifiable_elements_present: false` sat alongside a `sensitive_elements` block asserting that a controlled tier contains ZIP code, sex, race, ethnicity, genetic sequencing data, past health records, medications and traffic/accident reports. Under the single-referent rule `false` is defensible, but the two blocks read as contradictory.

**Change:** `deidentification_details` now states explicitly that the assertion is scoped to the publicly released v3.0.0 dataset, quoting the FAIRhub `datasetDeIdentLevel` finding that no identifiers were collected and that HIPAA-identifiable data were verified absent, and noting that the controlled-access tier described in the documentation is out of scope for this record.

**Rationale:** The boolean is correct for the referent; it needed the scope stated so a reader does not read it against the controlled tier.

### 3.9 Both — `sensitive_elements` boolean contradiction resolved (LOW)

**Finding:** Two adjacent `SensitiveElement` objects carried opposing `sensitive_elements_present` values (`false`, then `true`), distinguished only by prose. The structured field alone was unusable.

**Change:** Consolidated to a single entry with `sensitive_elements_present: false`, scoped to the public v3.0.0 release, with `sensitivity_details` describing the elements withheld to the controlled tier and the elements' identity drawn from the docs.aireadi.org v3 About page.

**Rationale:** One referent, one boolean. The controlled-tier content is fully preserved as prose within the same object.

### 3.10 Full — synthetic identifiers flagged (LOW)

**Finding:** `subsets` and `file_collections` used fabricated DOI fragments (`https://doi.org/10.60775/fairhub.3#train`, `#cardiac_ecg`, etc.). These do not resolve and are not present in the bundle.

**Change:** The identifiers are retained — `DataSubset` and `FileCollection` both require `id`, and the bundle supplies no native identifiers for splits or directories — but a `source_caveats` note now records that these fragment URIs are constructed for structural purposes and are not resolvable identifiers appearing in any source.

**Rationale:** The schema forces an identifier; honesty about its provenance is the available remedy.

---

## 4. Left as-is, with reasons

### 4.1 Core reductions of Ethics-module slots

The core record folds `collection_consents`, `collection_notifications` and `consent_revocations` into `informed_consent.consent_scope` and `.withdrawal_mechanism`. **Retained.** The fold-in is disclosed in `source_caveats`, no evidenced content is lost, and the consolidation is a legitimate reduction for a core record.

### 4.2 Core omission of `variables`, `participant_compensation`, `participant_privacy`, `third_party_sharing`

The full record carries 19 `VariableMetadata` objects with units, measurement techniques and laboratory reference ranges from BMJ Open Table 2; the $200 participant stipend with its post-device-return payment timing; data watermarking and privacy-preserving device selection; and public third-party distribution with the licensee-to-licensee restriction. The core record drops all four slots.

**Retained as omissions.** A core record is by design a reduction, and the audit's concern — that this content is strongly evidenced — is a reason to keep it in the *full* record, which it does. The reduction is disclosed in core `source_caveats`. Two specific figures worth flagging were nonetheless surfaced: the $200 compensation is now noted in core `description`, and the licensee-to-licensee sharing restriction is retained in `license_and_use_terms.license_terms` rather than only inside a distribution note.

### 4.3 Snellen visual acuity removal classified as `anomalies` rather than `errata`

The v3.0.0 dropping of Snellen visual acuity variables (logMAR retained) is recorded as a `DataAnomaly`. **Retained.** The healthsheet's explicit erratum question has an empty response, so asserting an erratum would go beyond the evidence; the healthsheet records the change under versioning, and an anomaly entry with `anomaly_details` quoting that passage is the closest supported fit. Classification is defensible either way and is noted as such in `source_caveats`.

### 4.4 `instances[0]` prose in `instance_type`

`data_substrate` and `data_topic` remain unpopulated with the multimodal/T2DM description carried in `instance_type`. **Retained.** The bundle does not use controlled vocabulary for these concepts, and the healthsheet's own answer ("Each instance represents an individual patient") is what `instance_type` reproduces. Splitting inferred values across additional keys would add structure without adding evidence.

### 4.5 Split demographics appearing in `subsets`, `splits` and `subpopulations`

The 70/15/15 composition figures appear in three slots. **Retained.** Each slot answers a different question — the partition itself, the split rationale, and the demographic composition of the dataset — and the bundle's README table supports all three readings. The duplication is a drift risk, noted in `source_caveats`, not an error.

### 4.6 Ten-way source conflict set

The following conflicts are surfaced in `source_caveats` rather than silently resolved, and remain so:

| Conflict | Sources |
|---|---|
| Project name: "Ready and Equitable Atlas" vs "Ready and Exploratory Atlas" | BMJ Open / Nature Metabolism vs NIH RePORTER / FAIRhub study description |
| Lead institution: University of Washington vs Washington University in St. Louis | NIH RePORTER / IRB vs FAIRhub `managingOrganization` and `leadSponsor` |
| Enrolment target: 4,000 vs 4,600 | BMJ Open / Nature Metabolism / FAIRhub vs UW IRB protocol |
| Longitudinal follow-up: 10% vs ~4% | NIH RePORTER / IRB vs FAIRhub healthsheet collection Q5 |
| Licence version: v1.0 (Zenodo 10642459) vs v2.0 (Zenodo 17555036) | Bundle licence PDF vs FAIRhub v3 `rights` |
| T2DM prevalence: 10.5% vs >6% of world population | BMJ Open vs Nature Metabolism |
| Study duration: 2022–2026 vs project end 2025-08-31 vs completion 2027-01-01 | Nature Metabolism vs NIH RePORTER vs FAIRhub status module |
| Race/ethnicity release status: withheld from public set | Nature Metabolism / docs — but README split table publishes counts |
| Max age: no upper bound in BMJ Open vs 85 years in FAIRhub eligibility | BMJ Open vs FAIRhub / IRB |
| Recruitment window: began 2023-07-18 vs 2023-07-19 | BMJ Open vs FAIRhub `dateCollected` |

**Retained.** The instruction is to represent what the evidence states rather than silently select. Where a working value was required for a structured slot, the value with the strongest corroboration was used and the alternative recorded in `source_caveats` — for example, `2023-07-19` as `collection_timeframes.start_date` (FAIRhub structured metadata, corroborated by the healthsheet) with the BMJ Open `18 July 2023` noted.

Note that the licence conflict is material: the bundle supplies the **v1.0** licence text in full but the FAIRhub v3 record points to **v2.0**, whose text is not in the bundle. `license_and_use_terms.license_terms` therefore describes v1.0 provisions explicitly as v1.0, with a caveat that the version governing v3.0.0 is v2.0 and its text was not available.

---

## 5. Final state

| | Full | Core |
|---|---|---|
| Populated slots | 71 | 43 |
| Validated | yes | yes |
| Invented keys | 0 | 0 (was 1) |
| Unsupported assertions | 0 | 0 (was 1) |
| Referent | v3.0.0 | v3.0.0 (identical) |

Validation commands run:

```
poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_all.yaml \
  -C Dataset data/d4d_concatenated/claudecode_agent/2026-08-11_claude-opus-5-api-generic_rep2/AI_READI_d4d.yaml

poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml \
  -C CoreDataset data/d4d_concatenated/claudecode_agent_core/2026-08-11_claude-opus-5-api-generic_rep2/AI_READI_d4d_core.yaml
```

Both pass.

Reconciliation outcome: **consistent**. The two records agree on referent, version, all shared factual values, and all conflict disclosures. The core record is a strict reduction of the full record with no content present in core that is absent from full.