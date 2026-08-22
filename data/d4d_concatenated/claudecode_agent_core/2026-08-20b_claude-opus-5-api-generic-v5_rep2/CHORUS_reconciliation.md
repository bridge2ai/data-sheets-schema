# CHoRUS D4D Reconciliation Report

**Project:** CHORUS
**Version label:** `2026-08-20b_claude-opus-5-api-generic-v5_rep2`
**Arm:** BASELINE (input documents only)
**Records reconciled:** full (`Dataset`) and core (`CoreDataset`)
**Phase:** 4 — strict reconciliation following the Phase 3 source/provenance audit

---

## 1. Referent

The `Dataset` referent is unchanged from Phase 1: **the CHoRUS multicenter critical care dataset** assembled by the Patient-Focused Collaborative Hospital Repository Uniting Standards (CHoRUS) for Equitable AI project — not the CHoRUS project as an organizational entity, and not the AIM-AHEAD Bridge2AI for Clinical Care Training Program that consumes it. This choice is held consistently across both records. Material in the bundle that describes the training program (curriculum, stipend, eligibility, application dates, mentorship) is treated as evidence about *uses of* and *access routes to* the dataset, not as dataset content, and appears only where it bears on `existing_uses`, `intended_uses`, `data_governance`, and `third_party_sharing`.

---

## 2. Audit summary

The audit returned 17 findings: 5 medium, 12 low. No fabricated external identifiers, no invalid enum values, no prose in list-ranged slots, and no prior-D4D reuse were found. The defects were predominantly structural — role over-assignment, structured content held as prose, and generalization of a program-specific access route — rather than fabricated fact.

---

## 3. Changes made

### 3.1 `creators` — role over-assignment (medium, both records)

**Finding:** all six leadership-team members were emitted with `principal_investigator`; only Rosenthal is attested in that role.

**Change:** the `creators` list was reduced from six objects to one. Only Eric S. Rosenthal remains, with `principal_investigator: Eric S. Rosenthal` and `affiliations: [name: Massachusetts General Hospital]`. The five other leadership-team members (Bihorac, Jiang, Strekalova, Rashidi, Kwong) were moved into dataset-level `notes`, where they are recorded as the listed Bridge2AI CHoRUS leadership team with their institutions and an explicit statement that the sources state no dataset-creation role for them. The surviving `creators[0].source_caveats` was extended to point at that notes entry.

**Rationale:** the webinar attests membership of a leadership team, not authorship of the dataset. Recording membership as prose in `notes` preserves the fact without asserting a role the bundle does not support.

**Secondary correction visible in the same slot:** `principal_investigator` changed from a nested mapping (`principal_investigator:\n  name: Eric S. Rosenthal`) to the scalar string `Eric S. Rosenthal`. The audit did not raise this, but it was corrected in passing while rewriting the slot.

### 3.2 `data_governance.access_review_process` — program-specific route generalized (medium, both records)

**Finding:** the registration form, licensing signature, compute provisioning and `.edu` requirement are attested for the AIM-AHEAD training program, not for all users.

**Change:** the paragraph was rewritten. It now opens with the general fact ("Access to the dataset is controlled"), then states the GitHub-attested access-request route by name (`dbold@emory.edu` or `jared.houghtaling@tuftsmedicine.org`), then attributes the registration/licensing/compute/`.edu` sequence explicitly to "participants in the AIM-AHEAD Bridge2AI for Clinical Care Training Program." A `source_caveats` was added to `data_governance` recording that these requirements describe that program's route and that the bundle does not state they apply to all users, and that the bundle names no access review committee.

### 3.3 `data_governance.committee_contact` — unsupported governance role (medium, both records)

**Finding:** Ciera McCrary is attested as MGH Program Manager and website contact, not as an access-committee contact.

**Change:** the `committee_contact` object was removed entirely. Ciera McCrary now appears in `data_governance.stewardship_roles`, in a dedicated first entry naming her as Program Manager at Massachusetts General Hospital and project contact, with the email reproduced as published. `stewardship_roles` was also split from one long combined entry into three separate entries (program management; Standards/Data Acquisition/Tooling sub-teams; data site managers).

**Consequential resolution of finding 3.7 (low):** the `mailto:cmccrary@mgh.havard.edu` identifier, which encoded the source's apparent typo into an identity key, no longer exists in either record — it was removed together with the `committee_contact` object.

### 3.4 `license_and_use_terms.contact_person` — access contact in a license slot (medium, both records)

**Finding:** Jared Houghtaling is an access-request contact, not an attested license contact; the co-equal contact `dbold@emory.edu` was dropped.

**Change:** the `contact_person` object was removed from `license_and_use_terms`. Both access-request contacts now appear together in `data_governance.access_review_process` (§3.2), which is the field the evidence answers. `license_terms` was also narrowed: "All users must sign a licensing agreement" became "Training program participants must sign a licensing agreement … an institutional (\".edu\") email address is required for that route."

**Consequential resolution of the second half of finding 3.7:** the `mailto:jared.houghtaling@tuftsmedicine.org` identifier is likewise gone from both records.

### 3.5 `funders` — grant content as prose (medium, both records)

**Finding:** award number, application ID, amount and period are carried in `notes` while the declared `grants` field of range `Grant[]` stays empty.

**Change:** **none.** The `funders` block is byte-identical in the original and reconciled records of both files.

**Rationale for leaving it:** the schema digest supplied to this run lists `FundingMechanism` as accepting `grantor`, `grants`, `notes`, `source_caveats`, and gives the range of `grants` as `Grant[]` — but it does not enumerate the required or accepted keys of the `Grant` class itself. Rewriting the prose into a `Grant` object would have required guessing field names, and a guessed key is a validation failure under the digest's own warning against inventing keys. The finding is acknowledged as a real structural shortfall; it is left as-is because the material to fix it correctly was not available. This is recorded here rather than silently deferred.

### 3.6 `instances[0].label` — over-strong labeling claim (low, both records)

**Change:** `label: true` and `label_description` were both removed from `instances[0]`. A sentence was appended to `instances[0].source_caveats` stating that the sources describe labeling with prediction targets as an activity the project will perform through a visualization and annotation environment and do not state that released instances carry labels.

**Related change in `labeling_strategies` (not separately raised):** `labeling_details` was rephrased from "A visualization and annotation environment is used to label data" to "The project develops a visualization and annotation environment to label data", and a `source_caveats` was added noting the capability is planned work with no reported labeling output for released admissions. `tasks[4].response` was likewise softened from "developed by the project" to "being developed by the project."

### 3.7 `ethical_reviews[0].reviewing_organization` — invented label (low, both records)

**Change:** the `reviewing_organization: CHoRUS consortium ethics pillar` field was removed. `review_details` now quotes the NIH abstract's own wording — pillar "Ethics (Ethical and Trustworthy AI)" — instead of paraphrasing it into a body name. The `source_caveats` was rewritten to state plainly that this records the project's ethics research and governance program and that the bundle states no IRB approval, ethics committee review, or reviewing organization for the dataset.

### 3.8 `known_limitations[2]` — uncaveated reliance on garbled table (low, both records)

**Change:** a `source_caveats` was added to `known_limitations[2]` recording that the metadata-availability statement derives from a per-modality table in the cohort 2 webinar whose columns are badly garbled in the concatenated text, and that the assignment of "Yes" and "Planned" values to individual modalities is uncertain. The `limitation_description` was also hedged: "were planned rather than available" became "were reported as planned rather than available."

The same caveat was added as a final sentence to the dataset-level `source_caveats` in both records, since the garbled table also underpins the per-modality `conforms_to` values.

### 3.9 `subpopulations[0]` and `description` — "adult" inference (low, both records)

**Change:** "adult intensive care units, pediatric intensive care units (PICU), and neonatal intensive care units (NICU)" became "intensive care units (ICU), pediatric intensive care units (PICU), and neonatal intensive care units (NICU)" in `subpopulations[0].identification`. The `description` correspondingly changed "50,000 patient admissions from adult, pediatric, and neonatal intensive care units" to "50,000 patient admissions from ICU, PICU, and NICU settings". In `human_subject_research.special_populations`, "alongside adult ICU admissions" became "alongside general intensive care unit (ICU) admissions."

### 3.10 `at_risk_populations` — supportable slot omitted (low, both records)

**Change:** the slot was added to both records:

```yaml
at_risk_populations:
  at_risk_groups_included: true
  notes: >-
    The released dataset includes admissions from pediatric intensive care units (PICU)
    and neonatal intensive care units (NICU), and so covers minors. The sources describe
    no assent procedures, guardian consent arrangements, or special protections specific
    to these groups.
```

`assent_procedures`, `guardian_consent` and `special_protections` are left unpopulated because the bundle states nothing about them; the absence is recorded in `notes` rather than by inventing values.

### 3.11 `is_deidentified.identifiable_elements_present` — supportable value unset (low, both records)

**Change:** `identifiable_elements_present: true` was added, together with a `source_caveats` explaining the basis (notes withheld from the enclave and retained locally; imaging de-identification in process as of August 2025; a maintained privacy scan tool for medical records) and noting that the sources make no overall de-identification determination.

### 3.12 `distribution_formats` — supportable slot omitted (low, both records)

**Change:** the slot was added to both records with five `DistributionFormat` objects, one per delivery format the bundle names: OMOP CDM tables (with the flowsheet extension noted), OHNLP tokenized note output, DICOM imaging, WFDB telemetry with extended PhysioNet metadata, and EDF+/Persyst EEG. Only the `format` field is populated; `download_url`, `access_urls`, `checksum` and `media_type` are omitted because the bundle supplies none.

### 3.13 `updates.frequency` — wrong field (low, both records)

**Change:** the `frequency` field was removed. Its content (site status reporting) was already fully present in `update_details`, which retains it. A closing sentence was added to `update_details`: "The sources state no release or versioning cadence for the dataset itself."

### 3.14 `file_collections[].collection_type` — internal inconsistency (low, full record only)

**Change:** `collection_type: processed_data` was added to the three collections that lacked it — imaging, waveform telemetry, and EEG waveforms — so that all five collections now carry the same value. The evidence describes all five in equivalent terms (extracted, converted, standardized, de-identified).

### 3.15 `description` — access route conflated (low, both records)

**Change:** the closing sentence "Data are accessed through the Bridge2AI AI/ML for Clinical Care Collaborative Cloud enclave after registration and signature of a licensing agreement" was removed from `description` in both records. In its place, an evidence-faithful sentence about storage was inserted mid-paragraph: "OMOP data and telemetry are held in a cloud enclave; clinical notes are stored locally at contributing sites, with only tokens shared." The opening also changed from "made available under controlled access" to "held under controlled access". The access route is now stated once, in `data_governance.access_review_process`, with its program-specific scope attributed.

### 3.16 Core projection losses (low, core record)

**Finding:** the holdout test set moved from `subsets` (carrying `is_data_split: true`) into `resources`, losing the split designation; and the content of the full record's `direct_collection` object was folded into `acquisition_methods[0]` prose.

**Change:** **none for the holdout test set or `direct_collection` placement.** Both remain as they were: the core record still carries the holdout set as `resources[5]` without a split flag, and still carries the direct-collection statement inside `acquisition_methods[0].acquisition_details`.

**Rationale:** the core schema (`CoreDataset`) is a reduced projection of `Dataset`; `subsets`, `file_collections` and `direct_collection` are among the slots the core class does not carry, which is why the full record's `subsets` and `file_collections` entries were folded into core `resources` and the `direct_collection` content into `acquisition_methods` in the first place. The information is preserved in prose in each case. The audit correctly notes that declared structure is lost, but the loss is a property of the projection rather than a defect introduced by the generation, and no new facts were introduced by the fold. All other §3 changes were applied identically to both records, so the two remain aligned.

**One structural difference between the records persists by design:** the full record retains `subsets`, `file_collections`, `direct_collection` and `third_party_sharing`; the core record does not. Every fact in those full-record slots has a home in the core record (`resources`, `acquisition_methods`, `existing_uses`).

---

## 4. Findings left as-is

| Finding | Severity | Disposition |
|---|---|---|
| `funders[].grants` unpopulated (§3.5) | medium | Left as-is. The `Grant` class's accepted keys are not enumerated in the schema digest available to this run; populating it would require inventing keys. The award identifiers remain in `funders[0].notes`, complete and unaltered. |
| Core `resources` loses `is_data_split` on the holdout set (§3.16) | low | Left as-is — a property of the core projection, not an introduced defect. |
| Core folds `direct_collection` into `acquisition_methods` (§3.16) | low | Left as-is, same reason. Content preserved verbatim in prose. |

No other finding was left unaddressed.

---

## 5. Slots removed, added, and net effect

**Removed from both records:** five `creators` entries; `data_governance.committee_contact`; `license_and_use_terms.contact_person`; `ethical_reviews[0].reviewing_organization`; `instances[0].label`; `instances[0].label_description`; `updates.frequency`.

**Added to both records:** `at_risk_populations`; `distribution_formats`; `is_deidentified.identifiable_elements_present`; `is_deidentified.source_caveats`; `data_governance.source_caveats`; `labeling_strategies[0].source_caveats`; `known_limitations[2].source_caveats`.

**Added to the full record only:** `collection_type` on three `file_collections` entries.

**Top-level slot counts (populated slots on the root object):**

- Full record: **41 before, 43 after.** Net +2 (`at_risk_populations`, `distribution_formats` added; no top-level slot removed — every removal was to a sub-field or a list member).
- Core record: **39 before, 41 after.** Net +2, same two slots.

---

## 6. Validation

Both files were validated after reconciliation:

- Full: `linkml-validate -s data_sheets_schema_all.yaml -C Dataset` — **passed**
- Core: `linkml-validate -s data_sheets_schema_core_all.yaml -C CoreDataset` — **passed**

The `# Phase 4 reconciliation: completed` line in the core header is accurate as written: Phase 4 ran, and this report is its output. The `# Sources:` line in the core header names the bundle and the Phase 1 full record, tying the projection to its source.

---

## 7. Outcome

**Reconciled.** All five medium findings were addressed except `funders[].grants`, which is documented as unresolvable within this run's schema information rather than silently dropped. Eleven of twelve low findings were addressed; the two core-projection findings were examined and left as-is with reasons. The two records remain factually identical to one another, differing only in the slots the core class does not declare.