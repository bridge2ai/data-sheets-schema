# Reconciliation Report — CHORUS

**Version label:** `2026-07-31_claude-opus-5-generic-v2_rep2`
**Arm:** BASELINE (input documents only)
**Source bundle:** `data/preprocessed/concatenated/CHORUS_preprocessed.txt` (4 files: NIH RePORTER project 10472824; AIM-AHEAD Bridge2AI for Clinical Care Cohort 2 webinar; chorus4ai.org project documentation; chorus-ai GitHub organization overview, 2025-11-14)
**Records reconciled:** full (`Dataset`) and core (`CoreDataset`)

---

## 1. Referent

Both records take as their single referent **the CHoRUS multi-modal critical-care dataset** — the controlled-access data resource assembled by the CHoRUS Data Generation Project — and **not** the funded NIH project (OT2OD032701), the CHoRUS software organization, or the AIM-AHEAD Bridge2AI for Clinical Care Training Program.

This choice was already held consistently across both records and was **not changed**. It is restated here because a large share of the bundle describes the other three entities, and several audit findings arise precisely from material about those entities having been drawn into dataset-level slots. Reconciliation applied the referent test uniformly: a fact about the grant, the training curriculum, or the GitHub organization enters the record only where the bundle ties it to the dataset itself.

---

## 2. What the audit found

The audit returned 28 findings: 1 high, 12 medium, 15 low. Substantive dataset content was found to be accurate and correctly attributed throughout — consortium composition, funding award, the modality/standard/access-control table, OMOP, OHNLP, DICOM, WFDB and EDF+/Persyst standards, 1.6 billion OMOP rows, 7,642 admissions with radiology data, 23 Tb of waveform data, and the already-flagged 45K/50K admission discrepancy. The record also reproduces the website's typographical errors rather than silently correcting them, which is correct behaviour under the evidence boundary.

The defects clustered into five recurring patterns:

1. **Reconstruction from identifiers.** A personal name and institutional affiliation inferred from an email address.
2. **Adjacent-field population.** Slots filled with material that neighbours what the slot declares — ethics *activities* under `ethical_reviews`, privacy *measures* under `data_protection_impacts`, bias *mitigation intentions* under `known_biases`, a *grant end date* under `distribution_dates`, privacy and geocoding *utilities* under `machine_annotation_tools`.
3. **Absence statements.** Two slots closed by recording what the documentation does not say.
4. **Projections recorded as facts.** The anticipated 100,000-admission final dataset carried as an existing partition.
5. **Granularity inconsistency.** Distinct entities collapsed into single objects in multivalued slots, and asymmetric coverage between the two records.

---

## 3. Changes made — full record

### 3.1 High severity

**`maintainers` — fabricated identity removed.**
The entry `D. Bold, Emory University` was replaced with the contact string the bundle actually supplies: `dbold@emory.edu`, described as an access-request contact listed in the CHoRUS GitHub organization README. The personal name had been reconstructed from the email local part and the institution from the domain; neither appears anywhere in the four source files. This is the single clearest breach of the evidence boundary in either record and was corrected first.

### 3.2 Medium severity

**`maintainers` — inferred affiliation trimmed.**
`Jared Houghtaling, Tufts Medicine` retained the name (stated in the webinar as a lecturer) and the email address (stated in the GitHub README), but the affiliation string was removed. The webinar lists `Tufts` only as the *host* of his session, which is now what the object records. The domain-derived organisational claim is gone.

**`subpopulations` — unsupported qualifier removed.**
`Adult intensive care unit (ICU) admissions` → `Intensive care unit (ICU) admissions`. The website states `Patient admissions from ICU, PICU, and NICU` and nowhere characterises the ICU cohort as adult. PICU and NICU entries were unaffected.

**`subpopulations` — non-subpopulation entry removed.**
The entry defining a group by social determinants of health and geographic distance to the nearest hospital was deleted. The NIH abstract describes these as *data elements to be acquired*, not as a group whose representation in the dataset is characterised. The underlying fact is already carried at the level where the bundle supports it (SDOH and contextual factors as acquired content), so nothing was lost.

**`known_biases` — slot omitted.**
Both entries were removed and the slot is now absent. Neither documented a bias present in the data: one paraphrased the federated-sampling aim of achieving "a balanced and diverse cohort", the other the project statement that "patient-focused efforts will determine the ethical and legal approaches to manage privacy and bias". The assertion that "site and case-mix representation bias is an explicit concern for the project" appears in no source. The bundle contains no observed or measured bias. The sampling intention remains in `sampling_strategies`, where it belongs. An absent slot is the correct answer here.

**`ethical_reviews` — slot omitted.**
All three entries removed. The slot declares IRB approvals, ethics-committee reviews and compliance certifications; the bundle documents none for this dataset. The three entries described project ethics *research* — community-facing focus groups on what data is appropriate for public sharing, analysis of the legal and regulatory landscape, evaluation of community perspectives on clinical-care AI. Those facts are retained under `purposes` and `tasks`, which is where the bundle situates them (the CHoRUS Ethics pillar). The IRB material elsewhere in the bundle belongs to the AIM-AHEAD training curriculum ("Navigating IRB, Data Compliance, and Quality Assurance in AI/ML Healthcare Research") and is a property of the training program, not of the dataset — it was not relocated into the record.

**`data_protection_impacts` — slot omitted.**
The single entry restated privacy-handling measures already recorded under `is_deidentified`, `participant_privacy` and `confidential_elements`. No DPIA is described in the bundle. Removed without relocation.

**`machine_annotation_tools` — reduced to one tool.**
Retained: the **OHNLP toolkit**, which the webinar's modality table states is used to extract and tokenize clinical notes — genuine automated annotation of dataset content, with a published open-source schema.
Removed: `privacy_scan_tool`, `CTP-deid`, `UF-Geocoding`. These are privacy-scanning, de-identification and geocoding utilities, not annotation tools. All three were relocated to `external_resources` as repository entries carrying only the descriptions the GitHub listing provides.
The CTP-deid function claim ("a de-identification repository") was dropped in the move: the repository listing carries no description and the purpose had been inferred from the repository name. The relocated entry now records the repository name and its presence in the chorus-ai organization, nothing more.

**`human_subject_research` — absence statement deleted.**
The closing sentence recording that consent, notification and IRB determinations "are not described in the available documentation" was removed. Under the v2 rules a statement that information is absent does not answer the field. The remainder of the object, which reports the retrospective clinical-data character of the resource, was retained.

**`collection_timeframes` — absence statement deleted, award period relocated.**
The clause reporting that "the calendar coverage of the underlying patient records is not stated" was removed. The funded project period 2022-09-01 to 2026-11-30 was removed from this slot and moved into the `funders` object, where it is what it actually is: the period of NIH award OT2OD032701. The slot now carries the retrospective character of collection and the August 2025 status snapshot (14 hospitals, 45K+ unique admissions) reported in the webinar.

**`distribution_dates` — grant end date removed.**
2026-11-30 was deleted from this slot as part of the relocation above; a grant end date is not a release date. The slot retains a single entry recording that a released dataset was documented as available as of August 2025, per the webinar, which is the only release-state date the bundle supplies.

**`subsets` — projection removed.**
The `anticipated-final` entry (100,000 admissions, 9 modalities, 14 hospitals) was deleted. It is a stated future target on the project website under the heading "Anticipated Final Dataset", not an existing logical partition; giving it a `DataSubset` identifier asserted a partition that does not exist. The figures were moved to `updates` (`UpdatePlan`), which is the slot that declares planned future state. The `subsets` slot retains only the entries corresponding to the "Current Released Dataset" figures.

### 3.3 Low severity

**`splits` — holdout wording trimmed.**
The clause describing the holdout set as "sequestered … separately from the data released to users for model development" was cut. The NIH abstract states only that the dataset "will also provision a holdout test set, accessible for model external validation". The entry now carries that claim in its stated, forward-looking form and asserts nothing about the relationship between the holdout set and released data.

**`direct_collection` — inference reframed.**
"Data are not collected directly from individuals" was replaced with a statement of what the bundle supports: data are acquired retrospectively from the clinical systems of 14 contributing Data Acquisition centres. The retrospective, institution-mediated character is stated; the categorical claim about non-direct collection, which no source addresses, is not.

**`preprocessing_strategies` — DeGauss entry removed.**
The entry asserting that geocoding of OMOP Location entities via DeGauss is part of the CHoRUS preprocessing pipeline was deleted. The bundle establishes only that a forked `UF-Geocoding` repository exists in the chorus-ai organization; its application to the released dataset is not stated. The repository is retained in `external_resources`.

**`cleaning_strategies` — governance entries removed.**
The entries describing SOP internal validation and review, and site status tracking to resolve blocking issues, were deleted. Both describe project governance and delivery tracking rather than any operation applied to the data. The slot retains only the entry grounded in data-level curation of interoperable extracts as described in the SOP documentation.

**`raw_sources` — collapsed object split.**
The single `RawData` object listing five source types was split into five objects, one per source type, matching the granularity already used correctly in `raw_data_sources`. Multivalued slots take one object per distinct entity; the inconsistency between the two slots over the same underlying facts is resolved.

**`external_resources` — merged repositories split.**
`chorus_waveform and chorus_waveform_resources` became two objects. Both are separately listed in the GitHub overview with distinct descriptions.

**`acquisition_methods` — duplicate removed.**
The entry on federated access enabling sampling for a balanced and diverse cohort was deleted; it duplicated `sampling_strategies` entry 2 in substance. The fact is now recorded once, in the slot that declares it.

**`known_limitations` — imaging discrepancy added.**
A new entry records that the bundle reports two irreconcilable imaging figures — "currently 1000 images available with de-id in process for larger cohort" (webinar, September 2025) and "7,642 Admissions with Radiology Data" (project website, Current Released Dataset) — and names the source and date of each without selecting between them. This mirrors the treatment already applied to the 45K/50K admission discrepancy and satisfies the rule on representing rather than resolving source disagreement.

**`creators` — collective entry removed.**
"The CHoRUS Network as a collective" was deleted. It restated the consortium composition already carried in `created_by` and is not a distinct entity alongside the six named individuals from the webinar leadership slide.

**`future_use_impacts` — duplicate removed.**
Entry 3 restated `purposes` entry 2 plus the ethics-pillar aim; it described no anticipated consequence of a future use. Deleted.

---

## 4. Changes made — core record

The core record inherited every shared defect above; each correction was applied identically so that the two records remain consistent on `id`, `title`, `description` and all shared narrative slots. In addition:

**`resources` — projection and unrealised holdout removed.**
The `anticipated-final` entry was deleted for the reason given in §3.2. The `holdout-test` entry was also removed from `resources`: the bundle states only that the dataset "will also provision" it, which does not support listing it as an existing component resource. The holdout set remains represented once, in the full record's `splits`, in its stated forward-looking form.

**`distributions` — content groupings removed.**
The nine per-modality entries were deleted. They had been copied from the full record's `file_collections` and describe dataset content and access control rather than distribution channels or packaging. The tenth entry, "1.6 billion rows of EHR OMOP data", was a volume statistic and not a distribution at all; the figure is retained where it belongs, as a size characteristic of the released dataset. The slot now carries only the controlled cloud-enclave distribution the bundle describes, with the local-storage exception for clinical notes.

**`third_party_sharing` — asymmetry corrected.**
The slot was added to the core record, mirroring the full record: controlled access via the cloud enclave, request contacts `dbold@emory.edu` and `jared.houghtaling@tuftsmedicine.org`, and the registration route documented in the webinar (registration form, mandatory licensing agreement, `.edu` email requirement, with the stated note that program administrators assist where needed). The evidence was equally available to both records and the core record already carried `license_and_use_terms` and `distribution_formats`; omitting the access route was an inconsistency rather than a judgment.

---

## 5. What was left as-is, and why

**`at_risk_populations` — omission confirmed.**
The dataset includes PICU and NICU admissions, hence minors and neonates. The slot declares protections, safeguards and assent procedures; the bundle describes none. The omission is deliberate and was left standing. Populating the slot with the observation that the cohort includes minors would answer a different question than the one the slot asks, and populating it with a statement that no safeguards are documented would be an absence statement.

**`license` — top-level omission confirmed.**
The MIT License stated in the GitHub README governs the chorus-ai software repositories. No source states a license for the dataset, which is under controlled access with a separate licensing agreement signed at registration. The top-level `license` slot therefore remains absent. One change was made for clarity: the `license_and_use_terms` object now states explicitly that MIT applies to the software repositories and that dataset access is governed by a separate signed licensing agreement, so the distinction is recorded rather than left implicit.

**Typographical fidelity.**
The website's misspellings ("repoitory", "cmccrary@mgh.havard.edu") and the NIH abstract's errors ("Acquistion", "the CPatient-Focused", "nd utilization") are reproduced as they appear. Silent correction would substitute inference for evidence; these were not touched.

**Source-disagreement pairs.**
The 45,000 (webinar, August 2025) versus 50,000 (website, Current Released Dataset) admission counts, and the two imaging figures, are both carried with their sources and dates rather than reconciled into a single number. No merge was performed.

**Training-program material.**
The AIM-AHEAD Cohort 2 webinar supplies extensive detail on stipends, eligibility, curriculum, mentorship and key dates. None of it was drawn into either record beyond what the bundle ties to the dataset itself: the modality table, the access and registration route, the statement that "Datasets are being used for training activities and publications" (retained under `existing_uses`), and the named CHoRUS leadership. The remainder is a property of the training program, not of the dataset referent.

---

## 6. Outcome

| | Full (`Dataset`) | Core (`CoreDataset`) |
|---|---|---|
| Populated slots, pre-reconciliation | 64 | 36 |
| Slots removed | 3 (`known_biases`, `ethical_reviews`, `data_protection_impacts`) | 3 (same) |
| Slots added | 1 (`updates`) | 1 (`third_party_sharing`) |
| **Populated slots, final** | **62** | **34** |
| Objects removed or relocated | 19 | 16 |
| Objects split (granularity) | 6 | 5 |
| Schema validation | **PASS** | **PASS** |

Validation commands run against the final files:

```
poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_all.yaml \
  -C Dataset data/d4d_concatenated/claudecode_agent/2026-07-31_claude-opus-5-generic-v2_rep2/CHORUS_d4d.yaml

poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml \
  -C CoreDataset data/d4d_concatenated/claudecode_agent_core/2026-07-31_claude-opus-5-generic-v2_rep2/CHORUS_d4d_core.yaml
```

Both pass. All required keys are present on every object in a constrained range (`FileCollection.id`, `DataSubset.id`, `RawDataSource.source_description`, `DatasetRelationship.relationship_type`/`target_dataset`, `VariableMetadata.variable_name`, `Dataset.id`).

**Reconciliation outcome: RESOLVED.** All 28 findings are closed — 26 by amendment, 2 (`at_risk_populations`, `license`) by confirming a deliberate omission. The high-severity fabrication in `maintainers` is corrected in both records. The two records are consistent on referent, identifier, title, description and all shared slots; the remaining differences between them are attributable to schema scope alone.

**Provenance:** no previously generated D4D record was read or consulted at any phase. Factual inputs were the declared bundle and the two schema files only.