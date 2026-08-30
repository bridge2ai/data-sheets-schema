# CHoRUS Reconciliation Report

**Project:** CHORUS
**Version label:** 2026-08-28b_claude-opus-5-api-generic-v7_rep1
**Records reconciled:** full (`Dataset`) and core (`CoreDataset`)
**Referent:** the CHoRUS multicenter critical-care dataset (not the CHoRUS project, network, or GitHub organization). Held consistently across both records.

---

## 1. Audit summary

The audit returned 17 findings: 1 high, 7 medium, 9 low. It found no fabricated organization or person identifiers, no undeclared enum values, and no collapsing of distinct entities into single multivalued objects. It confirmed that the 50,000 / 45K / 100,000 admission-count disagreement was handled correctly by preferring the tier-2 project documentation and recording the lower-ranked figures in `source_caveats`.

The substantive defects were role and structure misassignments plus two inferred booleans, not invented content.

---

## 2. Changes made

All repairs were made in the full record and carried through to the core record by projection. No repair originated in the core record.

### 2.1 `maintainers[0].maintainer_details` — commentary moved out (high)

**Before:**
> `... website contact (cmccrary@mgh.havard.edu, as printed on the project site).`

**After:**
> `... website contact, at cmccrary@mgh.havard.edu.`
> plus a new sibling `source_caveats`: *"The contact address is transcribed exactly as printed on the project website, where the domain appears as \"mgh.havard.edu\"."*

The address itself is attested and was kept verbatim, including the misspelled domain. The gloss about transcription is a trust annotation about the sibling value, which is what `source_caveats` is for; the digest describes `source_caveats` as "a trust annotation about the sibling slots, not dataset content." Same change applied in both records.

### 2.2 `creators` — five `principal_investigator` assertions withdrawn (medium)

The five leadership-team members who are not named as PIs anywhere in the bundle no longer occupy `principal_investigator`. Each Creator object now carries only `affiliations` and a `notes` value naming the individual and stating the constraint:

> `Azra Bihorac, listed by the cohort_2_webinar under the Bridge2AI CHoRUS Leadership Team. The Creator class provides no slot for naming an individual other than a principal investigator, and the bundle does not state a principal investigator role for her.`

The same treatment is applied to Xiaoqian Jiang, Yulia Strekalova, Parisa Rashidi and Manlik Kwong. All six Creator objects are retained — none was deleted — so the leadership team is still represented, but the record no longer asserts a role for five of them that the bundle does not state. Rosenthal keeps `principal_investigator`, which NIH RePORTER supports directly, and his `source_caveats` gains the clause *"He is the only individual the bundle identifies as a principal investigator."* Same change in both records.

### 2.3 `id` — no longer identical to `page` (medium)

`id` changed from `https://chorus4ai.org/` to `https://chorus4ai.org/#chorus-dataset` in both records. `page` remains `https://chorus4ai.org/`. The fragment is minted on the only persistent locator the bundle supplies, per the minting rule, and the top-level `source_caveats` now records this:

> `The dataset identifier above is a fragment minted on the project website URL, which is the only persistent locator the bundle supplies; the bare website URL is recorded separately as the landing page.`

### 2.4 `at_risk_populations` — slot removed (medium)

The slot is gone from both records. The bundle names PICU and NICU care settings but never characterizes any population as at-risk, and the original object's own caveat conceded that no protections, assent procedures or guardian consent are described. A boolean asserting an at-risk determination the bundle does not make is worse than omission. The PICU/NICU facts remain in `description`, `instances[0].instance_type` and `subpopulations[0].identification`, which are all still present.

### 2.5 `human_subject_research` — slot removed (medium)

Removed from both records. The object carried only `involves_human_subjects: true` plus a caveat admitting that the bundle names no IRB approval, ethics review board or regulatory determination — that is, the object's entire content was an inference plus a disclaimer of it. Its factual residue was moved into `ethical_reviews[0].source_caveats`, which is new:

> `The bundle describes the consortium's ethics activities but names no institutional review board approval or ethics committee determination covering the dataset. IRB protocol drafting and HIPAA/GDPR compliance appear in the bundle only as topics in the associated training curriculum.`

The top-level `source_caveats` also now ends its list of absences with *"no IRB determination and no human-subjects determination for the dataset itself."*

### 2.6 `data_governance.committee_contact` — removed (medium)

The `committee_contact: {name: Jared Houghtaling}` object is gone from both records. The two access-request addresses remain, unchanged, inside `access_review_process`, which is where the bundle actually places them. The object's `source_caveats` was rewritten to explain the placement:

> `... so the two access-request email addresses given on the CHoRUS GitHub overview are recorded as part of the access review process rather than as committee contacts.`

### 2.7 `data_governance.accountable_organization` — removed (medium)

Removed from both records. The rewritten `source_caveats` preserves the underlying fact and marks the gap:

> `Massachusetts General Hospital is the NIH award recipient organization, but the bundle does not state which organization is accountable for the data over time.`

MGH remains attested elsewhere in both records — in `funders[0].notes`, `creators[0].affiliations` and `maintainers[0].maintainer_details`.

### 2.8 `instances` — imaging double-count resolved (medium)

The former `instances[3]` (1000 individual radiologic images, tier 4) was removed. The record now carries seven Instance objects rather than eight. The admission-level entry absorbs the disagreement:

- `instance_type` now reads `Admission with associated radiology data drawn from hospital PACS in DICOM format`
- a new `source_caveats` records both figures, notes that the units differ, and states which was preferred:
  > `... The tier-4 cohort_2_webinar instead counts images rather than admissions, stating that 1000 images were currently available with de-identification in process for a larger cohort; the two figures use different units and are not directly comparable, and the higher-ranked admission-level figure is used here.`

The 1000-image figure also survives unchanged in `is_deidentified.deidentification_details`, `missing_data_documentation[0].missing_data_patterns` and `known_limitations[0].limitation_description`.

### 2.9 `notes` — banner moved to `source_caveats` (low)

The top-level `notes` slot is removed from the full record. The banner text is now the closing sentence of the top-level `source_caveats` in both records, with its consequence stated:

> `At the time of capture the project website carried a banner reading "This repoitory is under review for potential modification in compliance with Administration directives." (spelling as in the source), so the described release state may change.`

The source's misspelling is preserved verbatim, as it is quoted material.

### 2.10 `distribution_formats` — format values unloaded (low)

Each of the five objects now carries a bare format designation in `format` with the scope description moved to a sibling `notes`. For example:

**Before:** `format: OMOP Common Data Model tables for demographics, medication administration, procedures, nursing flowsheets (OMOP schema with extensions) and diagnoses`

**After:** `format: OMOP Common Data Model, with schema extensions for nursing flowsheet data` plus `notes: Used for demographics, medication administration, provider-documented procedures and diagnoses, and high-frequency nursing flowsheets; published metadata schema available.`

The `notes` values also now carry the published-metadata-schema status per modality (available for OMOP, planned for OHNLP, DICOM and EDF+/Persyst), which the webinar table states. `media_type`, `access_urls` and `download_url` remain absent because the bundle supplies none. Same change in both records.

### 2.11 `collection_timeframes[0]` — award dates removed from prose (low)

**Before:** `... The funded project period runs from 2022-09-01 to 2026-11-30, and as of August 2025 the dataset covered 14 hospitals. ...`

**After:** `... As of August 2025 the dataset covered 14 contributing hospitals. The bundle does not state the calendar span of the clinical encounters included, and the dates it does state are those of the funding award rather than of data collection.`

`start_date` and `end_date` remain empty, correctly: the award period is not a collection period. The award dates remain in `funders[0].notes`, which is the field that asks for them. Same change in both records.

---

## 3. Findings left as-is

### 3.1 `conforms_to_standard` includes bare `OTHER` (low)

Unchanged in both records. `OTHER` is a permitted enum value and the digest offers no mechanism for annotating which standard it stands for. The prose `conforms_to` names OHNLP, EDF+ and Persyst, so the mapping is recoverable, as the audit itself noted. Dropping `OTHER` would lose the signal that standards beyond the three enumerated ones apply.

### 3.2 `keywords` mixes subject terms with `Bridge2AI` (low)

Unchanged. `Bridge2AI` is a program name the bundle uses throughout and is a plausible discovery term for this dataset. The audit judged it acceptable; no repair was warranted.

### 3.3 `citation` omitted (low)

Unchanged — still absent. The bundle states no recommended citation. The audit raised this only to record that the omission was checked, and the top-level `source_caveats` states it explicitly.

### 3.4 `license` scalar omitted (low)

Unchanged — still absent from both records. No license governs the data itself; the MIT and Apache-2.0 licenses named in the bundle govern the CHoRUS GitHub organization's software repositories. That distinction is stated in both `license_and_use_terms.license_terms` and `ip_restrictions.restrictions`, both of which remain present and unchanged. Populating the scalar with a software license would misattribute it to the data.

### 3.5 `subpopulations[0]` thin (low)

Unchanged in both records. `subpopulation_elements_present: true` is directly supported — the bundle states admissions from ICU, PICU and NICU and that demographics are captured in OMOP. `distribution` stays absent because the bundle supplies no figures, and the object's `source_caveats` says so. Structurally thin, but every value present is attested and the absence is documented.

### 3.6 `total_size_bytes` omitted (low)

Unchanged — still absent. The 23 Tb figure covers waveform data only, not the dataset as a whole, and remains in `instances` (now index 3) under `notes`. Aggregating it to a dataset-wide total would be an invented figure.

---

## 4. Full-to-core consistency

The core record is a projection of the reconciled full record. Every change in §2 that touches a slot the core schema carries appears identically in the core file. Slots removed from the full record (`at_risk_populations`, `human_subject_research`, `notes`, `data_governance.committee_contact`, `data_governance.accountable_organization`, `instances[3]`) are absent from the core record. The core header retains its four distinguishing lines, including `# Sources:` pointing at the full record and `# Phase 4 reconciliation: completed`.

Two core-only header/field differences are intentional and not defects: `conforms_to_class: CoreDataset` and `conforms_to_schema: src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml`, both of which describe the core record itself rather than the data.

---

## 5. Outcome

Reconciliation complete. All 8 medium-and-above findings and 3 of 9 low findings repaired; the remaining 6 low findings were assessed and left as-is with reasons recorded above. Both records state the same facts about the same referent, and no value in either record lacks a receipt in the declared bundle.