# Phase 4 Reconciliation Report — CHORUS

Version label: `2026-09-01_claude-opus-5-api-generic-v7_rep3`
Records reconciled: full (`CHORUS_d4d.yaml`) and core (`CHORUS_d4d_core.yaml`)
Referent held constant across both records: the **CHoRUS dataset** — the multicenter, controlled-access critical care data collection assembled by the CHoRUS data generation project — not the project, the consortium, or the AIM-AHEAD training program.

---

## 1. Audit summary

The Phase 3 audit returned eleven findings against the full record: two high severity, four medium, five low. The findings clustered into four groups — invented identity (minted person/organization/creator identifiers), semantic misplacement (leadership team members asserted as principal investigators; access contacts held in prose while declared Person-ranged fields sat empty), inference beyond the evidence (`at_risk_populations`, a substrate term, a subpopulation recast from variables, a directly-observed boolean), and duplication (access procedure stated twice).

The audit found no enum violation and no range violation, and confirmed that the record's handling of the tier-2 vs. tier-4 disagreement over release size, and its omissions of `doi`, `citation`, `version`, `license`, `errata`, `retention_limit` and `known_biases`, were correct.

---

## 2. Changes made

### 2.1 `creators` — leadership team no longer asserted as principal investigators (findings 1, 2, 3) — CHANGED

The original full record carried **seven** Creator objects: six built around a single named person each, and one for the consortium. Five of those six placed a Bridge2AI CHoRUS leadership team member (Bihorac, Jiang, Strekalova, Rashidi, Kwong) into `principal_investigator`, with an embedded caveat conceding that only Rosenthal is named as PI by NIH RePORTER.

The reconciled full record carries **two** Creator objects:

1. Rosenthal, with `principal_investigator: "Eric S. Rosenthal"` and `affiliations: [{name: Massachusetts General Hospital}]` — the one PI the tier-4 NIH RePORTER source attests.
2. A consortium Creator, whose `notes` now names the five remaining leadership team members and their institutions in prose, with a `source_caveats` recording that they are leadership members rather than PIs and that no registry identifiers exist in the bundle.

This resolves finding 1 (the false PI assertion is gone) and finding 3 (the seven now-unreferenced `#creator-*` fragments are gone, since only two Creator objects remain and neither carries an `id`).

Note a range change that came with this edit: in the original, `principal_investigator` held an object (`{id: ..., name: Eric S. Rosenthal}`); in the reconciled record it holds the bare string `Eric S. Rosenthal`. The same shape change was applied identically in the core record.

### 2.2 Minted identifiers for external entities removed (finding 2) — CHANGED

Every `#person-*` and `#organization-*` fragment minted under `https://chorus4ai.org/` is gone from both records. Specifically removed:

- `#person-eric-s-rosenthal`, `#person-azra-bihorac`, `#person-xiaoqian-jiang`, `#person-yulia-strekalova`, `#person-parisa-rashidi`, `#person-manlik-kwong`
- `#organization-massachusetts-general-hospital` (in both `creators[0].affiliations[0]` and `data_governance.accountable_organization`), `#organization-university-of-florida`, `#organization-uthealth-houston`, `#organization-tufts-university`, `#organization-chorus-consortium`

Organizations that survive — Massachusetts General Hospital in `creators[0].affiliations[0]` and in `data_governance.accountable_organization`, CHoRUS Consortium in the second Creator — now carry `name` only. The bundle supplies no ORCID, ROR or equivalent for any of them, so no identifier replaces the removed fragments.

### 2.3 `funders[0].grants[0].id` (findings 3, 10) — CHANGED

The original carried `id: https://reporter.nih.gov/project-details/10472824` on the Grant object. That URL is the RePORTER landing page, not a grant identifier, and nothing in the record pointed at the Grant. The reconciled records carry `grants: [{name: OT2OD032701}]` with no `id`; the RePORTER URL has been moved into the funder's `notes` as prose, where it is a pointer rather than an identity claim. It also remains, unchanged, in `external_resources`.

### 2.4 `data_governance.committee_contact` and `license_and_use_terms.contact_person` (finding 4) — CHANGED

Both declared Person-ranged fields were empty in the original. In the reconciled records:

- `data_governance.committee_contact: "Jared Houghtaling"` — one of the two named access-request contacts from the GitHub organization overview. The added `source_caveats` states plainly that this is an access-request contact rather than an attested committee contact, and that the other contact appears only as the address `dbold@emory.edu` with no name attached.
- `license_and_use_terms.contact_person: "Ciera McCrary"` — the published program-manager contact, with a `source_caveats` noting that no source names a licensing-specific contact.

Both hold bare name strings; no person identifier was minted, consistent with §2.2.

`data_governance.stewardship_roles` also changed shape: the original held one long string bundling three distinct roles; the reconciled record splits it into three list entries (site data managers, clinical collaborators, program manager). Ciera McCrary's name and email remain in the third entry, so the prose contact information was not lost when it was also promoted to a declared field.

### 2.5 `at_risk_populations` removed (finding 5) — CHANGED

The original object carried `at_risk_groups_included: true` and a caveat conceding that the inference rested on the presence of PICU and NICU admissions and that no source describes assent, guardian consent or protections. The slot is absent from both reconciled records. The PICU/NICU composition remains stated in `description`, in `instances[0].instance_type`, and in `subpopulations[0].identification`, so no attested fact was lost.

### 2.6 `human_subject_research` (finding 6) — LEFT UNPOPULATED, NOW EXPLAINED

The audit asked that `at_risk_populations` and `human_subject_research` be decided on one standard, and preferred the stricter reading. Both slots are absent from both reconciled records. The change here is not a slot but a caveat: the top-level `source_caveats` in both records gained a sentence recording that no source states whether the dataset is governed as human subjects research, nor describes protections, assent or guardian consent for the pediatric and neonatal admissions, and that both slots are therefore left unpopulated. The inconsistency the audit identified is resolved by omission on both sides.

### 2.7 `instances[1].data_substrate` removed (finding 7) — CHANGED

`B2AI_SUBSTRATE:37` (Relational Database) has been dropped from the OMOP EHR-rows instance. The bundle states a row count and OMOP standardization but names no storage substrate. The instance retains `instance_type`, `counts: 1600000000` and `data_topic: B2AI_TOPIC:9`.

Substrate terms on the other instances were **not** touched: `B2AI_SUBSTRATE:43` (Text) on clinical notes, `B2AI_SUBSTRATE:11` (DICOM) on imaging, and `B2AI_SUBSTRATE:49` (Waveform Data) on telemetry and EEG all remain, since each is stated by the webinar's data-type table rather than inferred.

### 2.8 Third subpopulation removed (finding 8) — CHANGED

The original `subpopulations` list had three entries; the reconciled list has two (ICU/PICU/NICU setting; contributing hospital). The removed third entry recast SDoH and geographic data elements as a basis for distinguishing subgroups, which the bundle does not state. That content survives untouched in `sensitive_elements[1]` and in the `preprocessing_strategies` entry describing DeGauss geocoding of OMOP Location entities.

### 2.9 `acquisition_methods[0].was_directly_observed` removed (finding 9) — CHANGED

The boolean is gone; the entry now carries `acquisition_details` alone, describing retrospective extraction from hospital systems. The second entry's `was_inferred_derived: true` is unchanged, since tokenization and OMOP mapping are explicitly derivations.

### 2.10 Duplicated access procedure separated (finding 11) — CHANGED

The original stated the AIM-AHEAD registration-and-licensing procedure in near-identical prose in both `data_governance.access_review_process` and `license_and_use_terms.license_terms`. In the reconciled records the two are separated:

- `access_review_process` keeps the **process**: request contacts, registration form (name, email, institution), provisioning email. The clause "and sign a licensing agreement" was dropped from this field.
- `license_terms` keeps the **terms**: controlled access for all data types, signed licensing agreement required, `.edu` email required, administrator assistance available. It now opens "All data types are made available under controlled access only" rather than "Access to all data types is controlled. Users of the dataset through the ... must complete a registration form and sign a licensing agreement".

---

## 3. Incidental shape corrections found during reconciliation

These were not audit findings but were fixed while editing, and are visible in the comparison:

- **`machine_annotation_tools[*].tools`** — was a bare string in both original records (`tools: OHNLP toolkit`); is now a single-item list in both. Same for `UF-Geocoding`.
- **`existing_uses[*].examples`** and **`external_resources[*].external_resources`** — were bare strings in both originals; are now single-item lists.

`intended_uses[*].examples` was already a list in the original and is unchanged.

---

## 4. Left as-is

| Item | Why |
|---|---|
| Release-size disagreement handling | 50,000 admissions from the tier-2 project documentation is stated; 45K+ from the tier-4 webinar is recorded in `instances[0].source_caveats` and in the top-level `source_caveats`. The audit confirmed this is correct; unchanged in both records. |
| `doi`, `citation`, `version`, `license`, `issued`, `errata`, `retention_limit`, `known_biases`, `version_access`, `variables`, `file_collections` | Absent from both records. No support in the bundle; the top-level `source_caveats` records the absence. |
| `data_governance.accountable_organization` = Massachusetts General Hospital | Retained, with its original caveat that MGH is recorded as awardee institution and program-manager host and that no source names a formal access committee. Only the minted `id` was removed. |
| `is_deidentified`, `participant_privacy`, `ethical_reviews` | Unchanged in the full record. Each is grounded in the bundle (tokenization, imaging de-id, the privacy scan tool, the ethics pillar and focus groups) and each already carried an appropriate caveat. |
| `notes` (the "repoitory ... under review" banner) | Retained verbatim in both records with the "(spelling as published)" annotation, since it is a direct quotation from the tier-2 source. |
| `conforms_to_standard` enum list | `OMOP_CDM, DICOM, WFDB, OTHER` — unchanged. `OTHER` covers EDF+/Persyst and the OHNLP schema, which have no enum term. |

---

## 5. Core record

The core record was re-projected from the reconciled full record. Every change in §2 and §3 that touches a slot present in `CoreDataset` appears identically in the core: the two-Creator structure, the removal of all minted person/organization/creator/grant identifiers, the added `committee_contact` and `contact_person`, the removed `at_risk_populations`, the removed `data_substrate` on the OMOP-rows instance, the two-entry `subpopulations`, the removed `was_directly_observed`, the split governance/license prose, the three-entry `stewardship_roles`, the list-valued `tools` / `examples` / `external_resources`, and the extended top-level `source_caveats`.

Core-only header fields (`# Sources:`, `# Phase 4 reconciliation: completed`) are present, and `conforms_to_class` reads `CoreDataset` against the full record's `Dataset`. Slots present in the full record but not projected into the core — `direct_collection`, `splits`, `third_party_sharing`, `participant_privacy`, `funders` (present), and the descriptive header slots — follow the core schema's own inventory rather than any editorial choice made here.

---

## 6. Outcome

All eleven findings addressed: nine by editing the records, one (finding 6) by confirming the omission and documenting it in `source_caveats`, and one (finding 10) folded into the same edit as finding 3. No finding was set aside as unactionable. Full and core remain consistent with one another and describe one referent.