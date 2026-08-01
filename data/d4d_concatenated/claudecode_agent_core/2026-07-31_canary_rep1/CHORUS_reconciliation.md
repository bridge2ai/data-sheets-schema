# CHORUS — Phase 4 Reconciliation Report

**Version label:** `2026-07-31_canary_rep1`
**Arm:** BASELINE (input documents only)
**Declared input bundle:** `data/preprocessed/concatenated/CHORUS_preprocessed.txt` (4 files: NIH RePORTER project page, AIM-AHEAD Cohort 2 informational webinar, chorus4ai.org project documentation, chorus-ai GitHub organization overview)
**Records reconciled:**
- Full — `data/d4d_concatenated/claudecode_agent/2026-07-31_canary_rep1/CHORUS_d4d.yaml`
- Core — `data/d4d_concatenated/claudecode_agent_core/2026-07-31_canary_rep1/CHORUS_d4d_core.yaml`

---

## 1. Referent declaration

`Dataset` admits one referent. Both records take the referent to be **the CHoRUS clinical care dataset** — the multi-modal, controlled-access critical-care data resource assembled by the CHoRUS Data Generation Project across 14 contributing hospitals — and **not** the CHoRUS project, the CHoRUS consortium, the chorus-ai software organization, or the AIM-AHEAD Bridge2AI for Clinical Care training program.

This choice is held consistently across both records. Its consequences are enforced throughout:

- The MIT License statement in the bundle attaches to the chorus-ai GitHub organization's software, not to the clinical data. It is therefore excluded from `license` and confined to `license_and_use_terms`, where the software/data distinction is stated explicitly.
- The AIM-AHEAD training program's eligibility rules, stipend, application deadlines and curriculum are properties of the training program, not of the dataset. They enter the records only where they describe dataset *access* (registration form, licensing agreement, `.edu` email requirement) or *existing use* (the dataset is used for training activities).
- The 28 chorus-ai repositories describe tooling built around the dataset. They are admitted as evidence of tooling only where the bundle describes what a repository does; repository names alone are not treated as evidence about the dataset.

---

## 2. What the audit found

Fourteen findings: one high, four medium, nine low. No fabricated identifiers, institutions, funding figures or dates were detected. Every numeric claim in both records traces to the bundle — award `OT2OD032701`, application ID `10472824`, `$5,880,300`, project period 2022-09-01 to 2026-11-30, 14 contributing hospitals, 20 institutions, 60+ consortium members, 50,000 / >45,000 / 100,000 admissions, 1.6 billion OMOP rows, 7,642 admissions with radiology data, 23 Tb of waveform data, 9 modalities, 1000 images, 28 repositories.

The defects clustered into four kinds:

1. **Slot-purpose drift** — content placed in a neighbouring field rather than the field it answers (core `version_access`).
2. **Target promoted to fact** — a stated project goal reported as an achieved property (`human_subject_research`).
3. **Repository name treated as evidence** — claims about applied processing inferred from a GitHub repo name or fork description (`preprocessing_strategies`, `is_deidentified`).
4. **Full/core divergence without cause** — slots supported equally by the bundle populated in one record and not the other.

---

## 3. Changes applied to the full record

### 3.1 `human_subject_research` — corrected (medium)

**Was:** "assembled retrospectively from the clinical records of more than 100,000 critically ill patients treated at 14 contributing hospitals."

**Now:** describes the released cohort — approximately 50,000 patient admissions from ICU, PICU and NICU, covering 14 hospitals and over 45,000 unique admissions as of August 2025 — and states the 100,000-admission figure separately and explicitly as the project's *anticipated final* dataset target.

**Why:** the bundle uses 100,000 in two places, both prospective. The NIH abstract frames it as a challenge the project addresses ("acquiring an AI-ready data set from more than 100,000 critically ill patients"); chorus4ai.org places it under the heading "Anticipated Final Dataset", directly beside a "Current Released Dataset" figure of 50,000. The record's own `description` and `known_limitations` already carried the smaller released figures, so the original text was both unsupported and internally inconsistent with the record it appeared in.

### 3.2 `preprocessing_strategies` — DeGauss geocoding entry removed (medium)

**Was:** an entry asserting that OMOP Location entities in the dataset are geocoded via DeGauss, linked to the abstract's mention of "geographic distance to the nearest hospital".

**Now:** removed. The remaining preprocessing entries — OMOP standardisation, OHNLP tokenisation of clinical notes, and the abstract's stated transformation "using approaches that limit re-identification" — are retained, as each is stated in the bundle as something done to the data.

**Why:** the only evidence was a repository listing: `UF-Geocoding`, *Forked from bihorac-LAB/Exposome*, "Open source code to geocode OMOP Location entities via DeGauss". That a forked repository exists in the organization is not evidence that the transformation was applied to this dataset. The entry additionally fused this with an unrelated abstract sentence about contextual data elements, manufacturing a causal link the bundle does not make. The abstract's own statement about geographic distance is retained where it belongs, in `purposes`.

### 3.3 `is_deidentified` — CTP-deid reference removed (low)

**Was:** cited `CTP-deid` as supporting de-identification tooling.

**Now:** the reference is dropped. The slot retains what the bundle states directly: data are transformed using approaches that limit re-identification; clinical notes are stored locally with only tokens shared; imaging de-identification is in process, with 1000 images currently available and a larger cohort pending.

**Why:** the bundle lists `CTP-deid` with an entirely empty description. The characterisation was read off the repository name.

### 3.4 `distribution_dates` — removed (low)

**Was:** a `DistributionDate` object stating "A partial dataset was already distributed under controlled access by August 2025."

**Now:** the slot is omitted. The August 2025 coverage snapshot is retained in `description` and in the subset descriptions, where it functions as a coverage statement rather than a release date.

**Why:** the bundle gives no distribution or release date for the dataset. "As of August 2025, covers 14 different hospitals with over 45K unique admissions" is a status report, and "Datasets are being used for training activities and publications" establishes use, not a distribution event. Per the omission rule, an absent slot is the correct answer here.

### 3.5 `known_biases` — narrowed (medium)

**Was:** one `DatasetBias` object mostly describing bias *management* — the patient-focused legal and ethical work on privacy and bias, and federated sampling "to ensure a balanced and diverse cohort".

**Now:** the object is confined to the one bias claim the bundle supports: the cohort is bounded by the 14 contributing academic hospitals, so representation reflects those institutions' patient populations. It is marked as inferred from the stated site count rather than enumerated by the creators. The mitigation content is relocated: federated sampling to `sampling_strategies`, and the ethical/legal privacy-and-bias work to `ethical_reviews` and `purposes`, where the bundle already supported it.

**Why:** the bundle nowhere enumerates a known bias in the data. A slot reporting what is being done about bias has not answered a slot asking what biases are present. Relocating rather than deleting preserves the evidence in the fields it actually answers.

### 3.6 `machine_annotation_tools` — wording tightened (low)

**Was:** OHNLP described as "an open source natural language processing toolkit".

**Now:** described as the OHNLP toolkit, used to extract and tokenize clinical notes, with an associated open-source schema — the bundle's own phrasing.

**Why:** the bundle says only "extracted and tokenized using OHNLP toolkit" and "OHNLP open source schema". Both the acronym expansion and the NLP characterisation were supplied from outside the bundle.

### 3.7 `file_collections` — reconstruction caveat added (low)

**Was:** nine per-modality entries carrying access-control and metadata-status values with no indication of source uncertainty.

**Now:** the entries are retained unchanged in substance, but each carries a note that its data-standard, access-control and metadata-status values derive from a webinar slide table whose columns are interleaved out of order in the preprocessed text, and that row-level attribution is a reconstruction.

**Why:** the table in the bundle is demonstrably misaligned — the Data type, Data standard, Access control and Metadata columns do not read in register. The modality-to-standard pairings (OMOP for demographics/medications/procedures/flowsheets/diagnoses, OHNLP for notes, DICOM for imaging, WFDB for telemetry, EDF+/Persyst for EEG) are strongly supported by adjacent prose and are retained. The per-row Yes/Planned metadata flags are weaker. Retaining the values while signalling the reconstruction is preferable to either silently asserting them or discarding well-supported modality structure.

### 3.8 `conforms_to_schema` — added (low)

**Now:** populated with the OMOP Common Data Model (OHDSI), matching the core record.

**Why:** the bundle supports it directly and repeatedly ("standardize data to the OMOP Common Data Model"; "Yes (OMOP schema)"). It was populated in core and omitted in full; the paired records diverged with no evidentiary basis for the difference.

### 3.9 Trailing comment lines — removed (low)

Two stray lines after the record body (`# (end of full record)` and a note disclaiming a trailing fragment) were deleted. They are generation artefacts, not part of the prescribed header block, and they signalled unresolved uncertainty about the record boundary.

---

## 4. Changes applied to the core record

### 4.1 `version_access` — removed (high — the principal defect)

**Was:** populated with the dataset access route: registration form capturing name, email and institution; a licensing agreement signed within that form; the `.edu` email requirement; email notification once access is granted and compute provisioned; the `dbold@emory.edu` / `jared.houghtaling@tuftsmedicine.org` access-request contacts; and the holdout set's availability for external validation.

**Now:** the slot is omitted.

**Why:** `version_access` asks about access to *different versions* — where older versions can be found, how version history is maintained. The bundle contains no version-history evidence for the dataset at all: no version identifiers, no release series, no archive policy. Every fact placed in the slot answers a different question, and the full record already places those same facts correctly — the request/licensing route in `license_and_use_terms` and `third_party_sharing`, the holdout provision in `third_party_sharing` and `subsets`. This was a pointer-to-where-access-lives standing in for version information the bundle does not contain. Under the omission rule the correct answer is an absent slot; under the neighbouring-field rule the content belongs where full already had it. Removing it also eliminates a full/core contradiction in which the same facts were asserted under two different slot meanings.

### 4.2 `distributions` → reconciled against the core schema (medium)

**Was:** a `distributions` slot carrying the nine per-modality entries that the full record places in `file_collections`, with the per-collection `id` values dropped.

**Now:** the payload is emitted under the slot name the core schema declares for grouped file content, and the nine per-collection `id` values are restored so that each core entry corresponds one-to-one with its full-record counterpart. The reconstruction caveat from §3.7 is carried across.

**Why:** `distributions` is not among the 94 slots in the `Dataset` inventory, and its presence in `CoreDataset` could not be confirmed from the declared inputs — an unverified slot name risks validation failure. Dropping the `id` values also broke cross-record correspondence for no reason, since the identifiers were already minted in Phase 1.

### 4.3 `human_subject_research`, `known_biases`, `preprocessing_strategies`, `is_deidentified`, `machine_annotation_tools`, `distribution_dates`

The corrections at §3.1, §3.5, §3.2, §3.3, §3.6 and §3.4 are applied identically to the core record. These defects were shared, and the paired records must not diverge on the underlying facts.

### 4.4 Slots present in full but absent from core — resolved

`direct_collection`, `participant_privacy` and `splits` were verified against the core schema and reinstated in core where the schema declares them, carrying the same content as full:

- `direct_collection` — collection is retrospective from existing hospital records, not direct from individuals.
- `participant_privacy` — re-identification-limiting transformations; clinical notes retained locally with only tokens shared; imaging de-identification in process.
- `splits` — the holdout test set sequestered for external model validation.

`third_party_sharing` was reinstated in core with the controlled-access enclave and holdout-provision content, replacing the material that had been misfiled under `version_access`.

**Why:** each is supported by the bundle and was already correct in full. The original core omissions were an artefact of the misfiling in §4.1, not a schema constraint.

### 4.5 `resources` → `subsets` (low)

The three `DataSubset` entries (current released dataset, radiology subset, holdout test set) were moved from `resources` to `subsets`, which the core schema declares.

**Why:** `resources` is scoped to sub-resources or component datasets; released / radiology / holdout are logical partitions of a single dataset, which is precisely what `subsets` describes. The substitution also created a structural mismatch with the full record and was not signalled anywhere in the file.

---

## 5. Left as-is, with reasons

**`is_tabular: false` — retained.** The audit correctly notes this forces a choice the bundle does not make: the dataset comprises 1.6 billion rows of relational OMOP data alongside DICOM imaging, WFDB waveforms and EDF+/Persyst EEG. But the slot's range is boolean and the description asks whether the data is structured as a table, offering images as the contrasting case. A resource whose defining characteristic is nine heterogeneous modalities including imaging and waveforms is not a table. `false` is the better of the two available answers; the modality breakdown in `file_collections` carries the nuance the boolean cannot.

**`license` — remains omitted in both records.** The bundle's only licence statement — "This project is licensed under the MIT License. See the LICENSE file for more details" — appears in the chorus-ai GitHub organization README and governs software. Individual repositories carry MIT and Apache-2.0. None of this attaches to the clinical data, which the bundle describes uniformly as controlled-access and gated behind a signed licensing agreement. The distinction is stated explicitly in `license_and_use_terms` in both records. Populating `license` with "MIT" would misattribute a software licence to a controlled-access clinical dataset — the most consequential single error available in this bundle.

**`citation`, `doi`, `version`, `download_url`, `total_file_count`, `total_size_bytes` — remain omitted.** The bundle gives no citation, no DOI, no version identifier and no download URL. `23 Tb` of waveform data is one modality's volume, not a dataset total, and no file counts appear anywhere.

**`collection_consents`, `consent_revocations`, `collection_notifications`, `informed_consent`, `at_risk_populations`, `participant_compensation` — remain omitted.** The dataset is retrospective. The bundle describes community-facing ethics focus groups "to determine what data is appropriate for public sharing" — a consultative process, not participant consent — and this is captured in `ethical_reviews` and `purposes`. The `$8,000` stipend is trainee compensation in the AIM-AHEAD program, not participant compensation, and is out of scope under the referent declaration in §1. No IRB approval, consent instrument, notification or revocation mechanism is described.

**`anomalies`, `errata`, `imputation_protocols`, `missing_data_documentation`, `annotation_analyses`, `variables`, `relationships`, `subpopulations` — remain omitted.** The bundle documents none of these. Note the distinction preserved in `known_limitations`: pending items the bundle *does* state (EEG extraction in process, imaging de-identification in process, metadata "Planned" for several modalities) are recorded as limitations of dataset completeness, not manufactured into anomalies or errata.

**`retention_limit`, `ip_restrictions`, `regulatory_restrictions`, `use_repository`, `extension_mechanism` — remain omitted.** No retention policy, IP terms, export-control or regulatory-compliance statement, use-tracking registry, or dataset contribution mechanism appears. The GitHub SOPs describe how contributing *sites* deliver data during construction, which is `acquisition_methods` and `data_collectors` content, not an extension mechanism for downstream users; it is recorded there.

**`creators` — seven objects retained.** Eric Rosenthal (MGH, PI), Azra Bihorac (UF), Xiaoqian Jiang (UTHealth Houston), Yulia Strekalova (UF), Parisa Rashidi (UF), Manlik Kwong (Tufts), and Massachusetts General Hospital as the awardee organization. One object per named entity, per the multivalued rule. Not collapsed, and not padded with the AIM-AHEAD or NIH leadership named in the bundle, who lead the training program and the funding programs respectively rather than creating the dataset.

**`purposes` (6), `raw_sources` (5), `file_collections` (9) — retained at full cardinality.** Each distinct purpose, source and modality is a separate object.

**`funders` — retained.** NIH Common Fund Bridge2AI program, award `OT2OD032701` (application `10472824`, project number `1OT2OD032701-01`), FY2022 award amount `5880300`, project period 2022-09-01 to 2026-11-30. All directly stated.

**The chorus4ai.org banner — deliberately not recorded as dataset status.** "This repoitory is under review for potential modification in compliance with Administration directives" [*sic*] appears twice on the project website. It describes a website/repository review, not a documented dataset status, version or retention decision. Placing it in `status`, `retention_limit` or `updates` would convert a site notice into a dataset property the bundle does not assert. It is not represented.

**Source disagreement on cohort size — represented, not resolved.** Three figures appear: >45,000 unique admissions as of August 2025 (webinar), 50,000 admissions from ICU/PICU/NICU (website, "Current Released Dataset"), and 100,000 (NIH abstract and website "Anticipated Final Dataset"). Following the disagreement rule, both records now state all three with their sources and dates rather than silently selecting one. The webinar and website figures are not merged.

---

## 6. Outcome

| | Full | Core |
|---|---|---|
| Top-level slots, pre-reconciliation | 52 | 50 |
| Added | 1 (`conforms_to_schema`) | 4 (`direct_collection`, `participant_privacy`, `splits`, `third_party_sharing`) |
| Removed | 1 (`distribution_dates`) | 2 (`version_access`, `distribution_dates`) |
| Renamed / relocated | 0 | 2 (`distributions` → declared slot; `resources` → `subsets`) |
| Corrected in place | 6 | 6 |
| Top-level slots, post-reconciliation | **52** | **52** |

**Validation**

```
poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_all.yaml \
  -C Dataset data/d4d_concatenated/claudecode_agent/2026-07-31_canary_rep1/CHORUS_d4d.yaml
→ PASS

poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml \
  -C CoreDataset data/d4d_concatenated/claudecode_agent_core/2026-07-31_canary_rep1/CHORUS_d4d_core.yaml
→ PASS
```

**Provenance record**

```
poetry run d4d provenance record --project CHORUS --method claudecode_agent \
  --label 2026-07-31_canary_rep1 \
  --input-bundle data/preprocessed/concatenated/CHORUS_preprocessed.txt
→ recorded
```

**Reconciliation status: RESOLVED.** All fourteen findings addressed — nine by correction or removal, five retained with the reasoning recorded above. The two records now agree on referent, on every shared factual claim, and on the treatment of the bundle's internal disagreements. No claim in either record derives from a source outside the declared bundle, and no previously generated D4D record was read or consulted at any phase.