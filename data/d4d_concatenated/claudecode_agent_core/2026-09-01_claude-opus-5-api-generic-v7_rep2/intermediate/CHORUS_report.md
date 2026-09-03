# CHoRUS D4D Reconciliation Report

**Project:** CHORUS (CHoRUS, the Bridge2AI AI/ML for Clinical Care Grand Challenge)
**Label:** `2026-09-01_claude-opus-5-api-generic-v7_rep2`
**Arm:** BASELINE (input documents only)
**Records:** full (`Dataset`) and core (`CoreDataset`)
**Phase 4 status:** completed

---

## 1. Dataset referent

Both records describe a single referent: the CHoRUS multicenter critical care dataset produced by the CHoRUS data generation project, as described by the project documentation at chorus4ai.org and the NIH RePORTER entry for OT2OD032701. The AIM-AHEAD Bridge2AI for Clinical Care Training Program is treated throughout as a *user* of that dataset, not as the referent. Phase 4 sharpened this boundary in two slots (see §3.2), and the referent choice itself was not altered.

---

## 2. Audit summary

The Phase 3 audit returned 15 findings: 1 high, 5 moderate, 9 low. No schema-shape violations were reported — enums, CURIEs, `uri`-ranged values, integers, and list cardinality all conformed. The dominant defect class was **unsupported role or scope assertion**: the record asserted roles (principal investigator, committee member, accountable organization) and generalized program-specific procedures into dataset-wide policy. One structural finding concerned `FundingMechanism.grants` being empty while its content sat in `notes`. Two omissions were flagged as supportable additions.

---

## 3. Changes made

Every change below is present in both the full and the core record, since the core is a projection of the full.

### 3.1 `creators` — principal_investigator misassignment (high)

**Original:** all six Creator entries used `principal_investigator`, each of the five non-Rosenthal entries carrying an identical `source_caveats` sentence acknowledging that NIH RePORTER names only Rosenthal.

**Reconciled:** only `creators[0]` (Eric S. Rosenthal) retains `principal_investigator`, with a `notes` value recording both his RePORTER PI role and his Leadership Team membership. The five remaining entries now carry only `affiliations` plus a `notes` value naming the person and their attested role — for example, `notes: Azra Bihorac, member of the Bridge2AI CHoRUS Leadership Team.` The `principal_investigator` key is gone from those five entries.

**Why:** the slot asserted a role the higher-ranked NIH RePORTER source contradicts. Recording the person in `notes` preserves the attested fact (Leadership Team membership, institutional affiliation) without asserting the contradicted role.

**Side effect on finding 13 (repeated caveats, low):** the five identical `source_caveats` sentences are gone from the Creator entries. The disagreement is now stated once, at record level, in the top-level `source_caveats` — a new sentence reading "NIH RePORTER names Eric S. Rosenthal as the sole principal investigator of OT2OD032701; the five further individuals recorded as creators are named in the cohort 2 webinar only as members of the Bridge2AI CHoRUS Leadership Team, and no principal investigator role is asserted for them here."

### 3.2 `data_governance.access_review_process` and `license_and_use_terms.license_terms` — scope over-generalization (moderate ×2)

**Original (`access_review_process`):** "Access is controlled for every data type. Prospective users complete a registration form … A '.edu' email address is required to gain access to the dataset…" — stated as general dataset policy.

**Reconciled:** the dataset-wide portion is now confined to what the bundle supports ("Every data type in the dataset is released under controlled access and held in a cloud enclave, except clinical notes…"), and the registration form, licensing agreement, compute-provisioning email, and `.edu` requirement are explicitly scoped: "For the AIM-AHEAD Bridge2AI for Clinical Care Training Program (cohort 2), participants fill out a registration form…". The accompanying `source_caveats` now states that these requirements "are attested only for participants in the AIM-AHEAD Bridge2AI for Clinical Care Training Program and are described as such rather than as dataset-wide policy."

**Reconciled (`license_terms`):** rewritten in parallel — "Participants in the AIM-AHEAD Bridge2AI for Clinical Care Training Program must sign a licensing agreement, included in the program registration form…". Its `source_caveats` gained the sentence "The bundle states no general license for the data themselves and no access terms outside the training program context," ahead of the retained MIT/Apache-2.0 note about the software repositories.

### 3.3 `data_governance.committee_members` → `committee_contact` (moderate)

**Original:** two entries under `committee_members`, one bare `id: mailto:dbold@emory.edu` and one named entry for Jared Houghtaling.

**Reconciled:** `committee_members` is removed. The Houghtaling entry moved to `committee_contact` (declared range `Person`, singular). Both access-request addresses are recorded in `data_governance.notes`: "The chorus-ai GitHub organization page gives two access request contacts: dbold@emory.edu and jared.houghtaling@tuftsmedicine.org." The `source_caveats` now opens "The bundle names no data access committee, no committee membership…".

**Why:** the bundle prints these as access-request addresses, not as members of any body. `committee_contact` records a contact route without asserting a committee's composition.

### 3.4 `funders[0]` — structure (moderate)

**Original:** all award facts packed into `notes`, with `grants` unpopulated.

**Reconciled:** a `grants` entry now carries `id: https://reporter.nih.gov/project-details/10472824`, `name: OT2OD032701`, and a `description` holding the project number, application ID, awardee organization, fiscal year 2022 amount of USD 5,880,300, and the 2022-09-01 to 2026-11-30 project period. `notes` now retains only the NIH disclaimer sentence from the project website.

### 3.5 `data_governance.accountable_organization` — removed (moderate)

**Original:** `accountable_organization: {name: Massachusetts General Hospital}`.

**Reconciled:** the key is absent. The `source_caveats` records that "the bundle names … no organization formally accountable for the data over time." MGH remains attested elsewhere in both records where the bundle supports it — as Rosenthal's affiliation, in the grant description as awardee, and in `maintainers[0]` as the home of the program manager.

### 3.6 `at_risk_populations` — removed (low)

**Original:** an object with `at_risk_groups_included: true` plus `notes` and `source_caveats`, all resting on the ICU/PICU/NICU line.

**Reconciled:** the slot is absent from both records. The PICU and NICU observation survives in `human_subject_research.special_populations` and in `subpopulations[0].identification`, which state what the source states without characterizing the cohort as at-risk. No assent, guardian consent, or special protection was ever attested.

### 3.7 `preprocessing_strategies` — geocoding entry removed (low)

**Original:** a fifth entry asserting that UF-Geocoding/DeGauss geocoding of OMOP Location entities supports contextual elements such as distance to the nearest hospital.

**Reconciled:** that entry is gone; `preprocessing_strategies` now has four entries in both records. The UF-Geocoding repository is not separately re-stated, but the geographic-context theme remains where it is attested — in `intended_uses[3].usage_notes` (quoting the NIH abstract's contextual-factors language) and in `sensitive_elements[0]`.

### 3.8 `known_limitations[2]` — geography and access qualifier (low)

**Original:** "…at 14 contributing hospitals in the United States, and is available only under controlled access to registered users holding an institutional email address."

**Reconciled:** "…at 14 contributing hospitals, and is available only under controlled access." Both the US qualifier and the institutional-email condition (a training-program requirement, per §3.2) are dropped.

### 3.9 `maintainers[0].role` — removed (low)

**Original:** `role: academic_institution` on the MGH program-management entry.

**Reconciled:** the `role` key is absent from both maintainer entries; `maintainer_details` is unchanged. The bundle does not characterize the maintainer's organizational type, and the enum offered no fitting value.

### 3.10 `machine_annotation_tools` — added (low)

Added to both records: one entry with `tools: [OHNLP toolkit]` and a `tool_descriptions` value recording that clinical notes are extracted and tokenized with the toolkit and that the output follows the OHNLP open-source schema. The OHNLP toolkit is named in the cohort 2 webinar modality table and already appeared in `collection_mechanisms`, `preprocessing_strategies`, `instances`, and `distribution_formats`.

### 3.11 `external_resources` — added (low)

Added to both records: two entries. The first, `id: https://github.com/chorus-ai`, describes the 28-repository organization and names the repositories the bundle lists (chorus-mapping, Chorus_SOP, data_acq_SOP, chorus_waveform, chorus_waveform_resources, CTP-deid, privacy_scan_tool, chorus-extract-upload, chorus-container-apps, CHoRUSReports) along with the package status page and chorus-developer guide. The second, `id: https://www.bridge2ai.org/chorus`, records the alternate project page printed in the GitHub contact section.

### 3.12 Top-level `notes` folded into `status` (low)

**Original:** `notes` held only the website review banner; `status` read "Partially released under controlled access; data acquisition and curation ongoing."

**Reconciled:** the top-level `notes` slot is absent from both records. `status` now reads "Partially released under controlled access; data acquisition and curation ongoing. The project website carries the banner 'This repoitory is under review for potential modification in compliance with Administration directives.'" The banner's original misspelling is preserved as quoted source text.

### 3.13 `description` and `subpopulations` — "adult" removed (low)

**Original description:** "50,000 patient admissions from adult, pediatric, and neonatal intensive care units."
**Reconciled:** "50,000 patient admissions from intensive care units (ICU, PICU, and NICU)."

**Original `subpopulations[0].identification`:** "…drawn from adult intensive care units, pediatric intensive care units (PICU), and neonatal intensive care units (NICU)."
**Reconciled:** "Admissions in the released dataset are drawn from ICU, PICU, and NICU."

Both now track the source wording rather than expanding "ICU" into an age characterization the source does not make.

---

## 4. Findings left as-is

None. All 15 findings were acted on. The nine low-severity findings are each addressed above (§3.6–§3.13, with finding 13 handled as a side effect in §3.1); the two flagged omissions were added rather than declined, and the two flagged as judgment calls (`machine_annotation_tools`, `maintainers[0].role`) were resolved in the direction the audit suggested.

---

## 5. Content deliberately retained

- **Source disagreements** on admission counts (50,000 vs. 45K) and imaging (7,642 admissions vs. ~1,000 images) remain surfaced in per-instance `source_caveats`, with the higher-ranked project documentation preferred and the webinar figure reported alongside. The audit endorsed this handling.
- **The garbled webinar modality table** caveat is retained verbatim in the top-level `source_caveats`.
- **The `cmccrary@mgh.havard.edu` transcription**, with its apparent domain typo, is retained exactly as printed on chorus4ai.org, with the caveat flagging it.
- **The MIT / Apache-2.0 note** stays in `license_and_use_terms.source_caveats` as a statement about the software repositories, explicitly not about the data.

---

## 6. Core-record consistency

The core record was re-projected from the reconciled full record after Phase 4. Every change in §3 is reflected in it: the five Creator entries carry `notes` rather than `principal_investigator`; `funders[0].grants` is populated; `at_risk_populations`, `data_governance.accountable_organization`, `data_governance.committee_members`, `maintainers[*].role`, the geocoding preprocessing entry, and top-level `notes` are all absent; `machine_annotation_tools` and `external_resources` are present; and `status`, `description`, `subpopulations[0].identification`, `known_limitations[2]`, `data_governance`, `license_and_use_terms`, and the top-level `source_caveats` carry the reconciled text. The core header retains `# Sources:` pointing at the full record and now carries `# Phase 4 reconciliation: completed`.

---

## 7. Outcome

| | |
|---|---|
| Full record | reconciled, 47 top-level slots populated |
| Core record | re-projected, 45 top-level slots populated |
| Findings resolved | 15 of 15 (1 high, 5 moderate, 9 low) |
| Findings left as-is | 0 |
| Slots removed | `at_risk_populations`, top-level `notes` |
| Slots added | `machine_annotation_tools`, `external_resources` |
| Nested keys removed | `creators[1..5].principal_investigator`, `creators[1..5].source_caveats`, `data_governance.accountable_organization`, `data_governance.committee_members`, `maintainers[*].role` |
| Nested keys added | `funders[0].grants`, `data_governance.committee_contact`, `data_governance.notes`, `creators[*].notes` |
| Reconciliation outcome | strict; no finding deferred |