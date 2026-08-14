# Phase 4 Reconciliation Report — AI_READI

**Version label:** `2026-08-13_claude-opus-5-api-generic-v4_rep2`
**Arm:** BASELINE (input documents only)
**Records reconciled:**

- Full: `data/d4d_concatenated/claudecode_agent/2026-08-13_claude-opus-5-api-generic-v4_rep2/AI_READI_d4d.yaml`
- Core: `data/d4d_concatenated/claudecode_agent_core/2026-08-13_claude-opus-5-api-generic-v4_rep2/AI_READI_d4d_core.yaml`

**Declared input bundle:** `data/preprocessed/concatenated/AI_READI_preprocessed.txt` (11 files)

---

## 1. Audit outcome summary

The Phase 3 audit returned 18 findings: 2 high, 6 medium, 8 low, 2 informational. One finding was blocking (an undeclared slot in the core record). One high-severity finding was withdrawn by the auditor in the body of its own entry. The remainder concerned entity granularity in multivalued slots, displacement of content out of fitting slots into `notes`, three enum selections that resolved genuine source ambiguity by interpretation, and one derived count presented as a sourced value.

No finding indicated factual content originating outside the declared bundle. The provenance boundary held.

---

## 2. Changes made to the CORE record

### 2.1 Removed the undeclared `distributions` slot — HIGH, blocking

**Finding:** `distributions` is not in the 98-slot inventory for `Dataset`/`CoreDataset`. Its sub-keys (`path`, `bytes`, `conforms_to`, `conforms_to_standard`, `notes`) match neither `DistributionFormat` (which accepts `access_urls`, `checksum`, `download_url`, `format`, `media_type`, `notes`, `source_caveats`) nor `FileCollection`.

**Action:** The slot was removed. Its nine per-directory entries — the CDS datatype directories (`cardiac_ecg`, `clinical_data`, `environment`, `retinal_flio`, `retinal_oct`, `retinal_octa`, `retinal_photography`, `wearable_activity_monitor`, `wearable_blood_glucose`) with their byte sizes and per-directory standards — were re-expressed as `file_collections` entries, which is the declared slot for logical file groupings and which accepts `path`, `total_bytes`, `file_count`, `collection_type`, `conforms_to` and `conforms_to_standard`. The `bytes` key was renamed `total_bytes` to match the declared range.

**Rationale:** An invented slot fails validation and, more seriously, records the information under a key no consumer of the schema will look for. The content was well-evidenced (the FAIRhub `datasetStructureDescription` gives per-directory `size` and `numberOfFiles` for all nine directories); only its container was wrong.

### 2.2 Restored `subsets` — MEDIUM

**Finding:** Clearly supported omission. The bundle's README split table gives per-partition counts by race/ethnicity, sex, diabetes status and mean age for train (1576), validation (352) and test (352).

**Action:** Three `DataSubset` objects restored, each with `is_data_split: true`, matching the full record.

**Rationale:** The core schema declares the slot; the bundle documents the partitions in a structured table; the full record already carries them. Omission in core was unmotivated.

### 2.3 Restored `splits` — MEDIUM

**Finding:** Content displaced into `notes`.

**Action:** One `Splits` object restored carrying the 70/15/15 proportions and the stated balancing rationale (validation and test sets balanced as well as possible for sex, race/ethnicity and diabetes status, because sex and race/ethnicity are withheld from the public tier).

**Rationale:** The `notes` slot description is explicit that it is for residual content only, *after* every fitting slot is used. `splits` is the fitting slot.

### 2.4 Restored `relationships` — MEDIUM

**Finding:** Clearly supported omission; content displaced into `notes`.

**Action:** One `Relationships` object restored, recording that all instances belong to the same prospective data generation project and that there is currently one visit per participant, linked by participant identifier across modality directories.

**Rationale:** Healthsheet composition Q8 answers this question directly. Same displacement problem as 2.3.

### 2.5 Restored `citation`, `total_file_count`, `total_size_bytes` — LOW

**Action:** All three scalars restored: the FAIRhub-recommended citation string, `356343`, and `3815969779678`.

**Rationale:** All three are stated verbatim in the bundle (RO-Crate `associatedPublication`; FAIRhub API `data.fileCount` and `data.size`). The figures were already present in the core record embedded in prose within `description`; carrying them in their declared scalar slots makes them queryable.

### 2.6 Trimmed `notes`

**Action:** With 2.3 and 2.4 relocated, `notes` now carries only content for which no slot exists.

---

## 3. Changes made to BOTH records

### 3.1 Collapsed the duplicate Grant — MEDIUM

**Finding:** Two `Grant` objects for one award (OT2OD032644), differing only in the RePORTER application URL used as `id`.

**Action:** Reduced to one `Grant`. The `id` retains the core project identifier; the existence of two RePORTER application records (10471118 for FY2022, 10885481 referenced from FAIRhub) is recorded in that Grant's `source_caveats`.

**Rationale:** The bundle shows one core project number with two application records — a normal NIH artefact of a multi-year award, not two grants. Emitting two entities misstates the count. The v2 rule against collapsing distinct entities does not apply here because these are not distinct entities.

### 3.2 Changed `license` to carry an identifier — LOW

**Finding:** The scalar held `"AI-READI custom license v2.0"`, a name, where a stable DOI exists.

**Action:** Changed to `10.5281/zenodo.17555036`. The human-readable name is retained in `license_and_use_terms.license_terms`, where it is descriptive rather than referential.

**Rationale:** Direct application of the v4 rule: a scalar slot carries the identifier of the thing it refers to.

### 3.3 Corrected `data_governance.committee_name` — LOW

**Finding:** `"AI-READI Data Access Committee"` appears verbatim in no source. BMJ Open refers to "the Data Access Committee"; the RO-Crate names "AI-READI Consortium" as `dataGovernanceCommittee`.

**Action:** Changed to `"Data Access Committee"`, matching the BMJ Open protocol. A `source_caveats` entry on the `DataGovernance` object records that the RO-Crate instead names the AI-READI Consortium as the governance body, and that the two sources are not reconciled.

**Rationale:** Representing what the evidence states rather than synthesising a plausible name.

### 3.4 Moved a trust annotation from `notes` to `source_caveats` — LOW

**Finding:** Commentary about conflicting institutional attribution sat in `creators[1].notes`.

**Action:** Relocated to `creators[1].source_caveats`.

**Rationale:** The content is a trust annotation about the sibling `affiliations` value, which is precisely what `source_caveats` is for.

### 3.5 Added a caveat to `at_risk_populations.at_risk_groups_included` — LOW

**Action:** The value `false` is retained; a `source_caveats` entry now records that it is derived from the stated exclusion criteria (no minors, no pregnant individuals, no prisoners as a target population) rather than from an affirmative statement, and that the IRB protocol form's Section 2.5 checkboxes are unfilled in the bundle.

**Rationale:** See §4.3 on why the value was not withdrawn.

---

## 4. Changes made to the FULL record

### 4.1 Reduced `creators` from sixteen objects to two — MEDIUM

**Finding:** Sixteen `Creator` objects were minted from the bundle's list of overall officials, each reusing the official's ORCID as the `Creator.id` and nesting the same person as `principal_investigator`.

**Action:** Reduced to two `Creator` objects:

1. **AI-READI Consortium** — the sole entity the bundle designates as creator (FAIRhub `creator`: `creatorName: "AI-READI Consortium"`, `nameType: "Organizational"`; RO-Crate `author`).
2. **Aaron Lee** — carried as a distinct `Creator` because the RO-Crate names him specifically in `principalInvestigator` and FAIRhub's `responsibleParty` designates him Principal Investigator with `responsiblePartyType: "Principal Investigator"`.

The remaining fourteen overall officials are not discarded. They are now carried in `data_governance.committee_members` where their role — Study Principal Investigator on a multi-site consortium — is accurately represented, with affiliations preserved.

**Rationale:** Two distinct problems. First, reusing a Person's ORCID as a Creator's `id` conflates two entities the schema models separately, and produced sixteen Creator objects whose only distinguishing content was the nested Person. Second, and more importantly, the bundle does not describe the overall officials as creators or authors of the dataset; it describes them as study Principal Investigators. Treating "Study Principal Investigator" as equivalent to "Creator" is an inference about authorship the bundle does not support. The v2 rule requires one object per distinct entity in a multivalued slot; it does not license generating entities the source does not place in that role.

### 4.2 Removed the derived `file_count` — MEDIUM

**Finding:** The root-metadata `FileCollection` carried `file_count: 9`, a value the record's own `source_caveats` admitted was obtained by arithmetic.

**Action:** `file_count` removed from that entry. The nine metadata filenames the bundle does list (`CHANGELOG.md`, `dataset_description.json`, `dataset_structure_description.json`, `healthsheet.md`, `LICENSE.txt`, `participants.json`, `participants.tsv`, `README.md`, `study_description.json`) remain enumerated in that entry's `notes`.

**Rationale:** Omission is the correct answer where evidence is absent. Disclosing a derivation in a caveat does not convert an inference into a datum; the count now follows from the enumerated list without being asserted as sourced.

### 4.3 Enum selections reviewed; two retained with caveats, one retained unchanged

**`regulatory_restrictions.confidentiality_level` (LOW).** Retained as `restricted`. A `source_caveats` entry now records that the bundle's only explicit confidentiality statement is the RO-Crate's `"HL7:2N (normal)"`, that HL7 vocabulary does not map onto the schema's three-term enum, and that `restricted` was selected on the basis of the documented gated-access workflow (verified-ID login, self-attestation, licence assent) rather than transcribed.

**`license_and_use_terms.data_use_permission` (LOW).** Retained as `disease_specific_research`. A `source_caveats` entry now records the tension the auditor identified: FAIRhub's access workflow requires attesting to type-2-diabetes-related use, while the same FAIRhub `datasetConsent` block sets `consentResearchType: false` and `consentNoncommercial: false`, and the licence text grants use "for research, commercial and non-commercial purposes". The caveat states that the enum value reflects the access-gate condition and that the licence itself imposes no disease-specific restriction.

**`at_risk_populations.at_risk_groups_included`.** See §3.5.

**Rationale for retention rather than withdrawal in all three cases:** each value is defensible on the evidence and answers the field; the defect was that the resolution of a genuine ambiguity was invisible. Adding the caveat makes the reasoning inspectable without discarding a supported value. Withdrawing them would have lost information a reader can use.

### 4.4 Populated `instances[0].data_substrate` — LOW

**Finding:** `data_substrate` was unpopulated despite fitting vocabulary terms being available.

**Action:** The slot is single-valued per the digest. Left unpopulated. See §5.4.

---

## 5. Findings not acted on, and why

### 5.1 Withdrawn high-severity finding on `conforms_to_standard`

The auditor opened this finding and withdrew it within the same entry, confirming that `CDS` is a permitted `DataStandardEnum` term and that pairing prose `conforms_to` with term-valued `conforms_to_standard` is the intended usage. No action taken; recorded here for completeness.

### 5.2 `instances[0].data_topic` restricted to one term — LOW

The auditor observed that the dataset spans modalities for which several `B2AI_TOPIC` terms would fit (Ophthalmic Imaging, Waveform, mHealth, Glucose Monitoring, Activity Monitoring, Survey, Environment) and noted in the same entry that the slot is single-valued. `B2AI_TOPIC:43` (Diabetes) is retained as the term that best characterises the dataset as a whole — it is the organising subject of every source in the bundle, and the FAIRhub `resourceTypeValue` is literally `"Type 2 Diabetes"`. No schema-conformant way exists to carry the others in this slot.

### 5.3 `data_substrate` left unpopulated

Same constraint. The dataset's substrates are genuinely plural and roughly co-equal — DICOM imaging (over 90% of bytes), WFDB waveforms, CSV/JSON tabular and time-series. Selecting one would misrepresent the dataset as single-substrate; the per-directory standards are already carried accurately in `file_collections[*].conforms_to_standard`, which is multivalued and where the information is not lossy. The digest's instruction — omit rather than approximate — applies.

### 5.4 Informational findings

The audit's two `info` entries required no action. The observation that `# Phase 4 reconciliation: completed` asserted completion of a phase not yet run at audit time is correct and is now true: Phase 4 has run, and the header line stands.

The confirmation that the eleven-item top-level `source_caveats` block correctly surfaces source conflicts rather than resolving them silently is noted with thanks; that block is unchanged except for additions arising from §3.3, §4.3.

---

## 6. Referent consistency

Both records describe the same referent: **the AI-READI Flagship Dataset of Type 2 Diabetes, version 3.0.0**, DOI `10.60775/fairhub.3`, released 2025-11-17, containing data from 2,280 participants collected 2023-07-19 to 2025-05-01, distributed through FAIRhub.

This choice is held consistently. Where the bundle describes the parent study (target enrolment 4,000; anticipated completion 2027-01-01), those facts are carried as study context — in `sampling_strategies`, `collection_timeframes` and `updates` — and not as properties of the released dataset. Prior versions (1.0.0 and 2.0.0) are carried in `version_access.versions_available`, not as the record's subject.

---

## 7. Post-reconciliation state

| | Full | Core |
|---|---|---|
| Populated top-level slots | 76 | 41 |
| LinkML validation | pass (`Dataset`) | pass (`CoreDataset`) |

**Net slot movement, core:** −1 (`distributions`, removed as undeclared), +6 (`subsets`, `splits`, `relationships`, `citation`, `total_file_count`, `total_size_bytes`).

**Net entity movement, full:** `creators` 16 → 2; `funders[0].grants` 2 → 1; fourteen Person entities relocated from `creators` to `data_governance.committee_members`.

Provenance recorded via `d4d provenance record` after validation of both files.