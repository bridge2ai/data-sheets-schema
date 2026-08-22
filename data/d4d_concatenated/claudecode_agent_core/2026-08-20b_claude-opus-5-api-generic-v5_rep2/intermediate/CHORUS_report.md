# CHORUS D4D Reconciliation Report

**Version label:** `2026-08-20b_claude-opus-5-api-generic-v5_rep2`
**Arm:** BASELINE (input documents only)
**Records reconciled:** full (`CHORUS_d4d.yaml`, class `Dataset`) and core (`CHORUS_d4d_core.yaml`, class `CoreDataset`)
**Referent:** the CHoRUS multicenter critical care dataset assembled by the Bridge2AI CHoRUS data generation project — held consistently across both records.

---

## 1. Audit summary

The audit returned 17 findings: 0 high, 5 medium, 12 low. No fabricated external identifiers, no invalid enum values, no prose in list-ranged slots, and no prior-D4D reuse were found. The defects were predominantly structural — role over-assignment, structured content held as prose, and a training-program-specific access route generalized into dataset-level governance — rather than fabrications of fact.

---

## 2. Changes made

### 2.1 `creators` — role over-assignment (medium, both records)

**Before:** six `Creator` objects, each with a populated `principal_investigator` field: Rosenthal, Bihorac, Jiang, Strekalova, Rashidi, Kwong. Five carried a caveat conceding "the sources do not state a formal award role."

**After:** a single `Creator` for Eric S. Rosenthal, the only individual the bundle attests as principal investigator (NIH RePORTER, award OT2OD032701). The remaining five leadership-team members are now recorded in dataset-level `notes`, naming each with their listed institution, and stating explicitly that apart from Rosenthal the sources state no role for them in creating the dataset.

**Why:** a caveat that concedes a field is unsupported does not license populating it. The names and affiliations are attested and are preserved; only the role claim is withdrawn. `notes` is the correct home under the residual-content rule — no other declared slot holds "people listed on a leadership slide with no stated dataset role."

Also added to `notes` in the same edit: the attested "60+ CHoRUS consortium members across 20 different institutions."

### 2.2 `data_governance.access_review_process` — scope correction (medium, both)

**Before:** presented the registration form, licensing agreement, compute provisioning, and `.edu` email requirement as the general dataset access process.

**After:** the process is now attributed. It opens with the GitHub-attested general route ("request access by contacting dbold@emory.edu or jared.houghtaling@tuftsmedicine.org") and then scopes the registration/licensing/`.edu` requirements explicitly to "participants in the AIM-AHEAD Bridge2AI for Clinical Care Training Program." A new `source_caveats` on `data_governance` states that these describe the training program route and that the bundle does not state they apply to all users.

**Why:** the webinar states these requirements for its own cohort. Generalizing them asserted a governance rule the bundle does not support. This edit also recovers `dbold@emory.edu`, which the original records dropped entirely (finding 2.4 below).

### 2.3 `data_governance.committee_contact` — removed (medium, both)

**Before:** a `Person` object for Ciera McCrary with `id: mailto:cmccrary@mgh.havard.edu`.

**After:** `committee_contact` is removed. Ciera McCrary's attested role — MGH Program Manager and project contact — now appears as the first entry in `stewardship_roles`, with the email reproduced parenthetically as published. The added `source_caveats` states the bundle names no access review committee, no membership, and no committee contact.

**Why:** the bundle attests a program manager, not a committee contact. Populating `committee_contact` while `committee_name` and `committee_members` stayed empty asserted a governance structure that does not appear in the sources. This edit also disposes of the low finding about the `mailto:` identifier encoding the source's apparent typographical error: no identifier is now minted from the misspelled address, though the string itself is still reproduced as published in `stewardship_roles` and in `source_caveats`.

`stewardship_roles` was also split from one long entry into three distinct entries (program management, sub-teams, site managers), matching the multivalued-slot rule.

### 2.4 `license_and_use_terms.contact_person` — removed (medium, both)

**Before:** a `Person` for Jared Houghtaling with `id: mailto:jared.houghtaling@tuftsmedicine.org`.

**After:** removed. Both access-request contacts (Bold and Houghtaling) are now named in `data_governance.access_review_process`, which is the field their content answers. `license_terms` was also rescoped in the same edit — "All users must sign a licensing agreement" became "Training program participants must sign a licensing agreement... and an institutional ('.edu') email address is required for that route."

**Why:** an access-request contact is not an attested license contact, and treating one of two co-equal contacts as the license contact both misplaced the fact and silently dropped the other.

### 2.5 `funders[].notes` — left as prose (medium, both) — **not changed**

The award number, NIH application ID, award amount, and project period remain in `notes` on the single `FundingMechanism`. The finding is acknowledged and **left as-is**.

**Why:** the schema digest supplied to this generation lists `FundingMechanism` as accepting `grantor`, `grants`, `notes`, `source_caveats`, with `grants` of range `Grant[]` — but it does not enumerate the required or accepted keys of the `Grant` class itself. Emitting a `Grant` object without knowing its declared field names risks inventing keys, which the residual-content rule forbids outright. Leaving attested facts in `notes` is the lesser defect. This is the one medium finding not remedied, and it is recorded here as an open structural gap.

### 2.6 `instances[0].label` / `label_description` — removed (low, both)

**Before:** `label: true` with a `label_description` describing the annotation environment.

**After:** both removed. `instances[0].source_caveats` now states that the sources describe labeling as an activity the project will perform through a visualization and annotation environment and do not state that released instances carry labels.

Correspondingly, `labeling_strategies[0].labeling_details` was reworded from "A visualization and annotation environment **is used to** label data" to "The project **develops** a visualization and annotation environment to label data," and a `source_caveats` was added noting no labeling output is reported for the released admissions. The `tasks` entry was likewise softened from "a visualization and annotation environment developed by the project" to "**being** developed by the project."

**Why:** the bundle uses future/in-development phrasing ("A visualization and annotation environment **will** label data with targets important for prediction"). `label: true` asserted a property of released data that no source states.

### 2.7 `subpopulations` / `human_subject_research` — "adult" removed (low, both)

**Before:** "adult intensive care units, pediatric intensive care units (PICU), and neonatal intensive care units (NICU)"; `special_populations` read "alongside adult ICU admissions."

**After:** "intensive care units (ICU), pediatric intensive care units (PICU), and neonatal intensive care units (NICU)"; `special_populations` reads "alongside general intensive care unit (ICU) admissions." The `description` in both records was changed from "50,000 patient admissions from adult, pediatric, and neonatal intensive care units" to "50,000 patient admissions from ICU, PICU, and NICU settings."

**Why:** the bundle says "ICU, PICU, and NICU." "Adult" was an inference not present in the source.

### 2.8 `at_risk_populations` — added (low, both)

Newly populated with `at_risk_groups_included: true` and `notes` recording that PICU and NICU admissions mean the released dataset covers minors, and that the sources describe no assent procedures, guardian consent, or special protections for these groups.

**Why:** the declared object exists to carry exactly this fact, which was previously reachable only as prose under `human_subject_research.special_populations`. The negative statement about protections is a scope statement about the group, not a pointer to absent documentation.

### 2.9 `is_deidentified.identifiable_elements_present` — added (low, both)

Set to `true`, with a new `source_caveats` explaining the basis: clinical notes withheld from the enclave and retained locally, imaging de-identification still in process as of August 2025, and a maintained privacy scan tool for medical records — and stating that the sources make no overall de-identification determination.

**Why:** the bundle supports the value and the caveat makes the inferential step visible rather than silent.

### 2.10 `distribution_formats` — added (low, both)

Five `DistributionFormat` objects, one per modality: OMOP CDM tables (with the nursing-flowsheet extension noted), OHNLP tokenized note output, DICOM imaging, WFDB telemetry with extended PhysioNet metadata, EDF+/Persyst EEG.

**Why:** the bundle names concrete per-modality delivery formats. These were previously carried only through `conforms_to` / `conforms_to_standard`, leaving a slot with direct evidence empty. `access_urls` and `download_url` are omitted — the bundle publishes no direct download endpoint.

### 2.11 `updates.frequency` — removed (low, both)

**Before:** `frequency: ongoing, with regular status updates from data contributing sites`.

**After:** `frequency` removed; `updates` now holds `update_details` only, with a closing sentence stating that the sources state no release or versioning cadence for the dataset itself. The site-status-reporting content is retained in `update_details`, where it correctly describes project management activity.

**Why:** site progress reporting to project management is not a dataset release cadence.

### 2.12 `ethical_reviews[0].reviewing_organization` — removed (low, both)

**Before:** `reviewing_organization: CHoRUS consortium ethics pillar` — a label the bundle does not use.

**After:** the field is removed. `review_details` now quotes the NIH abstract's actual wording, "Ethics (Ethical and Trustworthy AI)," and a `source_caveats` states that this records the project's ethics research and governance program and that the bundle states no IRB approval, ethics committee review, or reviewing organization for the dataset.

**Why:** the label was coined by the record. The underlying ethics-program content is attested and is retained.

### 2.13 `file_collections[].collection_type` — made consistent (low, full only)

**Before:** `processed_data` on the OMOP EHR and tokenized-notes collections; omitted on imaging, waveform telemetry, and EEG.

**After:** `processed_data` on all five.

**Why:** the same evidence describes all five as extracted, converted, standardized, or de-identified. The inconsistency was internal, not evidential. (The core record has no `file_collections`; see 2.15.)

### 2.14 `known_limitations[2]` — caveat added (low, both)

The limitation text is retained, softened to "were **reported as** planned rather than available," and a `source_caveats` was added recording that the per-modality metadata table in the webinar is badly garbled in the concatenated text, making the assignment of "Yes"/"Planned" values to individual modalities uncertain. A matching sentence was added to the dataset-level `source_caveats` in both records.

**Why:** the claim is supportable but the evidence is degraded; the trust annotation belongs in `source_caveats`.

### 2.15 Core projection differences (low, core only) — **partially changed**

- **Holdout test set:** the full record keeps it in `subsets` with `is_data_split: true`; the core record still carries it in `resources` without a split designation. **Left as-is** — the core schema class is `CoreDataset`, and the projection into `resources` was the available route. The description still identifies it as a sequestered holdout for external validation, so the substance survives.
- **`direct_collection`:** the full record retains its own `DirectCollection` object with `is_direct: false`; the core record still folds "rather than collected directly from patients" into `acquisition_methods[0]` prose. **Left as-is**, same reason.

No facts differ between the two records as a result; only declared structure available in the full schema is not mirrored.

### 2.16 `description` — access-route conflation corrected (low, both)

**Before:** closed with "Data are accessed through the Bridge2AI AI/ML for Clinical Care Collaborative Cloud enclave after registration and signature of a licensing agreement."

**After:** that sentence is removed. The description now states "held under controlled access" and, separately, the attested storage fact: "OMOP data and telemetry are held in a cloud enclave; clinical notes are stored locally at contributing sites, with only tokens shared." Access mechanics live in `data_governance.access_review_process`, correctly scoped.

**Why:** the original conflated a general storage statement with a training-program-specific access route.

---

## 3. Findings left as-is, with reasons

| Finding | Disposition |
|---|---|
| `funders[].grants` not structured (2.5) | Left as prose in `notes`. The digest does not enumerate `Grant`'s field names; emitting the object risked inventing keys. Open gap. |
| Core `resources` vs full `subsets` for the holdout set (2.15) | Left as-is. Projection artifact of the core schema; no fact lost. |
| Core `acquisition_methods` absorbing `direct_collection` (2.15) | Left as-is. Same reason. |

---

## 4. Items deliberately still omitted from both records

The following remain unpopulated because the bundle does not support them, and their absence is a correct answer rather than an oversight: `doi`, `citation`, `license`, `version`, `issued`, `created_on`, `download_url`, `total_file_count`, `total_size_bytes`, `known_biases`, `collection_consents`, `informed_consent`, `consent_revocations`, `participant_compensation`, `data_protection_impacts`, `errata`, `retention_limit`, `version_access`, `splits`, `relationships`, `anomalies`, `variables`, `content_warnings`, `prohibited_uses`, `discouraged_uses`, `other_tasks`, `use_repository`, `related_datasets`, `parent_datasets`, `imputation_protocols`, `missing_data_documentation`, `annotation_analyses`, `machine_annotation_tools`, `ip_restrictions`, `distribution_dates`, `compression`, `is_deidentified.identifiers_removed`.

`third_party_sharing` is present in the full record only; the core record does not carry it.

---

## 5. Outcome

- **Medium findings:** 5 raised, 4 remedied, 1 (`funders[].grants`) documented as an open structural gap with a stated reason.
- **Low findings:** 12 raised, 9 remedied, 3 left as-is with reasons (two core projection artifacts, one already dissolved by the `committee_contact` removal).
- **Net slot movement (full):** removed `license_and_use_terms.contact_person`, `data_governance.committee_contact`, `ethical_reviews[0].reviewing_organization`, `updates.frequency`, `instances[0].label`, `instances[0].label_description`; added `at_risk_populations`, `distribution_formats`, `is_deidentified.identifiable_elements_present`, plus four new `source_caveats` (on `data_governance`, `ethical_reviews[0]`, `is_deidentified`, `labeling_strategies[0]`, `known_limitations[2]`); `creators` reduced from six objects to one.
- **Referent:** unchanged and consistent across both records.
- **Provenance:** no prior D4D record consulted; all facts trace to the declared bundle. Tier-2 over tier-4 preference applied to the admission-count and imaging-availability conflicts, with both values reported in `source_caveats` as required.