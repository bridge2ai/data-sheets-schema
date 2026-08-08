# CHORUS — D4D Reconciliation Report

**Version label:** `2026-08-06_claude-opus-5-1m-generic-v3-schema2_rep1`
**Arm:** BASELINE (input documents only)
**Source bundle:** `data/preprocessed/concatenated/CHORUS_preprocessed.txt`
**Records reconciled:**
- Full — `data/d4d_concatenated/claudecode_agent/2026-08-06_claude-opus-5-1m-generic-v3-schema2_rep1/CHORUS_d4d.yaml`
- Core — `data/d4d_concatenated/claudecode_agent_core/2026-08-06_claude-opus-5-1m-generic-v3-schema2_rep1/CHORUS_d4d_core.yaml`

---

## 1. Dataset referent

`Dataset` admits one referent. The referent held across both records is **the CHoRUS multimodal critical-care dataset** — the AI-ready data resource assembled by the CHoRUS Data Generation Project, not the CHoRUS project, not the CHoRUS GitHub software organization, and not the AIM-AHEAD training program.

Consequences of that choice, applied consistently in Phase 4:

- The **MIT license** stated in the GitHub README governs the CHoRUS *software packages*, not the dataset. It is therefore not promoted to the top-level `license` slot as a bare value (see §3.4).
- The **AIM-AHEAD Bridge2AI for Clinical Care Training Program** (stipends, eligibility, application deadlines, mentorship) is not dataset content. It appears only where it bears on the dataset — as an existing use and as the access route.
- The **NIH award** (OT2OD032701, $5,880,300, 2022-09-01 to 2026-11-30) is funding for the project that produces the dataset; it populates `funders` and is *not* used as a dataset collection timeframe (see §3.6).

---

## 2. Audit outcome summary

The audit returned **30 findings**: 2 high, 10 medium, 18 low.

No fabricated institutions, awards, counts, identifiers, or URLs were found in either record. Source disagreements were, in most cases, surfaced rather than suppressed. The transcription error in the MGH contact address was reproduced verbatim with annotation, which is correct handling.

The findings cluster into five kinds:

| Kind | Count | Disposition |
|---|---|---|
| A. Declared fields empty, substance in `notes` (v3 defect) | 8 | **Fixed** |
| B. Multivalued slot collapsed into one object | 2 | **Fixed** |
| C. Silent selection among disagreeing sources | 3 | **Fixed** |
| D. Over-reach beyond the evidence | 4 | **Fixed** |
| E. Supported slots omitted | 4 | **Fixed (3), left as-is (1)** |
| F. Confirmations / defensible-as-written | 9 | **Left as-is** |

---

## 3. Changes made

### 3.1 `creators` — declared fields populated, aggregate pseudo-entity removed
*(findings: high ×2, medium ×2)*

**Before.** Six Creator objects each carried a name, role, and institution inside free-text `notes`, with `principal_investigator`, `credit_roles`, and `affiliations` all empty. A seventh object read "The CHoRUS consortium as a whole: 60+ members across 20 different institutions."

**After.** Each of the six named individuals now populates the fields the Creator class declares:

- `affiliations` — Massachusetts General Hospital (Rosenthal), University of Florida (Bihorac, Strekalova, Rashidi), UTHealth Houston (Jiang), Tufts University (Kwong). All six affiliations are stated verbatim on the webinar leadership slide.
- `principal_investigator: true` on the Rosenthal entry. This is the one entry the bundle supports it for: NIH RePORTER names `ROSENTHAL, ERIC S.` as Principal Investigator on application 10472824. It is set `false` on no one else — the field is simply omitted for the other five, because the bundle identifies them as "Bridge2AI CHoRUS Leadership Team" without stating their PI status either way.
- `credit_roles` — **not populated for any creator.** The webinar slide lists names and institutions under a leadership heading; it does not assign CRediT taxonomy roles. Selecting `supervision` or `project_administration` from the enum would be an inference about role content the bundle never makes.

The seventh object was **removed**. It named no entity, and its content ("60+ CHoRUS consortium members across 20 different institutions") duplicates a fact already carried at dataset level. That fact is retained once, in the top-level `notes`.

Applied identically to the core record.

### 3.2 `distribution_formats` — one object per format
*(findings: medium ×2)*

**Before.** A single DistributionFormat object whose `notes` recited nine formats plus the enclave access route.

**After.** Nine objects, one per distinct format named in the webinar modality table: OMOP (demographics, medication administration, procedures, nursing flowsheets, diagnoses), OHNLP (tokenized clinical notes), DICOM (imaging), WFDB / PhysioNet-schema-extended (waveform telemetry), EDF+ and Persyst (waveform EEG).

`access_urls` is **left empty on all nine.** The bundle gives no per-format download URL. Access is via a controlled cloud enclave following registration and a signed licensing agreement — that is an access *route*, not a format URL, and it belongs in `license_and_use_terms` and `notes`, where it now sits. Putting the enclave description into `access_urls` would answer a neighbouring field rather than the one asked.

Applied identically to the core record.

### 3.3 `instances` and `file_collections` — disagreeing counts no longer silently resolved
*(findings: medium ×3)*

**Before.** `instances[0].counts: 50000`, while the same object's `notes` recorded three incompatible figures. `file_collections` imaging entry carried `file_count: 1000` against a note reporting 7,642 admissions with radiology data.

**After.** Both structured numeric assertions were **removed**. The bundle carries three admission figures from two sources that do not agree:

- **50,000** — chorus4ai.org, "Current Released Dataset," patient admissions from ICU, PICU, and NICU
- **over 45,000** — cohort-2 webinar, "as of August 2025," unique admissions across 14 hospitals
- **100,000** — chorus4ai.org "Anticipated Final Dataset," and the NIH abstract's "more than 100,000 critically ill patients" (a project target)

Promoting any one of these to `counts` selects a winner among disagreeing sources. All three are now stated, each attributed to its source and its as-of framing, in `instances[0].notes`.

The imaging figures are likewise both retained and both attributed: the webinar states "currently 1000 images available with de-id in process for larger cohort"; the website states 7,642 admissions with radiology data. These count different things (images vs. admissions) at different times, and the bundle does not reconcile them. Neither is asserted as `file_count`.

The declared fields the evidence *does* support were populated: `instance_type` (patient hospital admission) and `data_substrate` (multimodal clinical record — structured EHR, tokenized text, imaging, waveform).

`collection_type` was set on the nine FileCollection objects. All nine are processed, standards-conformant extracts derived from source clinical systems, so `processed_data` is used throughout; `raw_data` is not used, because the bundle describes the raw hospital source systems as remaining at the contributing sites.

Applied identically to the core record.

### 3.4 `license` — populated with explicit scope
*(finding: medium)*

The GitHub README states "This project is licensed under the MIT License." Under the referent chosen in §1, this governs software, not data. Two responses were available: omit, or populate with the scope stated.

**Populated**, as `MIT (CHoRUS software and tooling; the dataset itself is controlled-access and governed by a separate signed licensing agreement)`. The reason for preferring this over omission: the bundle states the license fact plainly, and a reader of the record who finds `license` empty would reasonably conclude no license information exists in the sources. The scoping clause prevents the value from being read as a dataset license, and the dataset's actual governance is carried in `license_and_use_terms`.

### 3.5 `license_and_use_terms.data_use_permission` — enum populated
*(finding: low)*

Set to `institution_specific`. The bundle states, in the training-program eligibility section, "In order to gain access to the dataset, you will need to have a '.edu' email address." That is an institutional gate on dataset access, which is what the enum value names. `ethics_approval_required` was considered and **rejected**: the bundle requires a signed licensing agreement, not documented ethics approval, and the two are not the same instrument.

### 3.6 `collection_timeframes` — structured dates deliberately withheld, prose clarified
*(finding: medium, ambiguous)*

`start_date` and `end_date` remain **unset**. The audit flagged this as ambiguous, and the ambiguity resolves against populating: 2022-09-01 and 2026-11-30 are the NIH award's project start and end. The dataset is described as **retrospective** data collection, so the clinical records it contains predate and do not coincide with the award period. Writing the award dates into `start_date`/`end_date` would assert a data-collection window the bundle never states.

`timeframe_details` was rewritten to say exactly this: that collection is retrospective, that the award period runs 2022-09-01 to 2026-11-30, that a released-data snapshot is reported as of August 2025, and that the date range of the underlying clinical records is not stated in the sources.

### 3.7 `human_subject_research.special_populations` and `at_risk_populations` — added
*(findings: low ×2)*

The website states the current released dataset comprises "50,000 Patient admissions from ICU, **PICU**, and **NICU**." Pediatric and neonatal intensive care admissions are minors and neonates. This is direct evidence, not inference.

- `human_subject_research.special_populations` now records that the released cohort includes pediatric and neonatal ICU admissions, i.e. minors including neonates.
- `at_risk_populations` was added with `at_risk_groups_included` naming the same. Its other declared fields — `special_protections`, `assent_procedures`, `guardian_consent` — are **left empty**: the bundle describes no assent or guardian-consent procedure, and inventing one would be a serious fabrication in exactly the area where fabrication does most harm.

Applied to the core record for `special_populations`; `at_risk_populations` is added only where the core schema declares it.

### 3.8 `is_deidentified` — declared fields populated
*(finding: low)*

`method` now records the two de-identification mechanisms the bundle names: OHNLP-toolkit tokenization of clinical notes, and a CTP-deid process applied to imaging ("1000 images available with de-id in process for larger cohort"). `identifiable_elements_present` is set true — the bundle states clinical notes are "stored locally except tokens," which asserts identifiable content exists and is withheld. `identifiers_removed` is **left empty**: no source enumerates which identifiers are stripped.

### 3.9 `external_resources` and `maintainers` — declared fields populated
*(findings: low ×4)*

- `external_resources[].external_resources` now carries the three URLs directly: `https://chorus4ai.org/`, `https://github.com/chorus-ai`, `https://reporter.nih.gov/project-details/10472824`. They are no longer only embedded in prose. `archival`, `restrictions`, and `future_guarantees` remain empty — the bundle makes no archival or persistence commitment about any of the three.
- `maintainers[].role` set to `academic_institution` on all three entries (MGH program manager, and the two named access contacts at Emory and Tufts Medicine). All three are individuals acting for academic medical institutions, which is the closest enum value the bundle supports.

### 3.10 `existing_uses[].examples` — populated
*(finding: low)*

The AIM-AHEAD Bridge2AI for Clinical Care Training Program Cohort 2 is a concrete named instance of dataset use, and now sits in `examples` rather than only in `notes`. The webinar's statement that "Datasets are being used for training activities and publications" remains in `notes` as the general claim.

### 3.11 Over-reach corrected
*(findings: low ×4)*

- **`known_limitations` — "all located in the United States" removed.** The bundle places the GitHub organization in "United States of America" and restricts *training-program applicants* to US persons. Neither statement is about where the 20 academic centers are. The limitation now reads only what is supported: 14 contributing hospitals within a 20-center academic consortium, which bounds generalizability.
- **`known_biases[].bias_type` — enum removed.** The bundle says the project will "manage privacy and bias" and seeks a "diverse, ... balanced" cohort. It never identifies a bias type present in the data. `representation_bias` was a categorization the sources do not make; the entry now carries `bias_description` and `mitigation_strategy` describing bias as an acknowledged open concern the project is designed to address, with no type asserted.
- **`sampling_strategies.is_sample` — removed.** "Federated access **will enable** sampling methods to ensure a balanced and diverse cohort" is forward-looking design intent. Asserting `is_sample: true` states it as a realized property of released data. `strategies` now records the intent as intent. `is_random` and `is_representative` remain unset for the same reason.

Applied identically to the core record for all four.

### 3.12 `status` — aligned with `notes`
*(finding: low)*

The chorus4ai.org banner — "This repoitory is under review for potential modification in compliance with Administration directives" (typo in source) — is a status-bearing statement. It appeared only in `notes`, leaving `status` empty and the two fields telling different stories. `status` now records that the resource is under review for potential modification, with the banner quoted verbatim in `notes`.

### 3.13 `maintainers` contact address — annotation made consistent
*(finding: low)*

`cmccrary@mgh.havard.edu` is reproduced verbatim in both `notes` and `maintainers`. The "havard" typo annotation, previously only on the `notes` instance, is now on both. The address is **not** silently corrected to "harvard" — that would be an edit to source data, and the correct institutional domain is not independently established by the bundle.

---

## 4. Left as-is, with reasons

### 4.1 `citation` — remains omitted
*(finding: low, confirmation)*

The bundle supplies no recommended citation, DOI, or dataset identifier. The NIH award number OT2OD032701 identifies the grant, not the dataset. Omission is the correct answer; the audit finding was a confirmation that the absence had been checked.

### 4.2 `ethical_reviews` — remains prose-only
*(finding: low)*

`reviewing_organization` and `contact_person` stay empty. The bundle describes ethics *activity* in substance — community-facing ethics focus groups to determine what data is appropriate for public sharing, analysis of the legal and regulatory landscape, a dedicated Ethics pillar — but names no IRB, no ethics committee, and no ethics contact. `review_details` carries what is stated. Populating `reviewing_organization` with "CHoRUS consortium" would manufacture an oversight body from a work-stream description.

### 4.3 `creators[].credit_roles` — remains empty
Reasoning given in §3.1. The enum is available; the evidence for it is not.

### 4.4 `distribution_formats[].access_urls` — remains empty
Reasoning given in §3.2.

### 4.5 `core.notes` block content — retained, itemized
*(finding: low)*

The core `notes` field absorbs facts displaced from full-record slots the core schema does not declare. The audit asked that this be justified slot-by-slot rather than as a block. Itemized:

| Displaced fact | Full-record slot | Why in core `notes` |
|---|---|---|
| Holdout test set sequestered for external model validation | `subsets` (DataSubset, `is_data_split: true`) | Core schema declares no split-typed subset construct |
| Third-party sharing: controlled enclave, no onward redistribution | `third_party_sharing` | Slot not declared in core |
| Direct collection: retrospective extraction from hospital systems, not collected from individuals | `direct_collection` | Slot not declared in core |
| Consortium scale: 60+ members, 20 institutions, 14 contributing hospitals | dataset-level `notes` (both) | Retained in both; not displaced |

### 4.6 `core.resources` — holdout test set relocated
*(finding: medium)*

The audit noted that the core record folded the holdout test set into `resources` alongside the nine modality collections, losing the `is_data_split: true` distinction the full record carries.

**Resolved by removal, not by re-typing.** The holdout set is no longer listed among `core.resources` — it is not a component data resource of the same kind as the nine modality collections, and listing it there asserted a parity the full record correctly denies. Its description is retained in `core.notes` (see §4.5), explicitly labelled as a data split sequestered for external validation. `core.resources` now contains the nine modality collections only, matching the nine `file_collections` in the full record one-for-one.

---

## 5. Cross-record consistency

Checked after all edits:

- **Referent** — identical in both records (§1).
- **Creators** — six entries, same six individuals, same affiliations, `principal_investigator` on Rosenthal only, in both.
- **Counts** — no admission count and no image count is asserted as a structured value in either record; the three-way and two-way disagreements are stated with attribution in both.
- **Formats** — nine DistributionFormat objects in both, same nine formats.
- **Modality collections** — nine in full `file_collections`, nine in `core.resources`, one-for-one.
- **Holdout split** — typed DataSubset in full; in core, described in `notes` and absent from `resources`, with the asymmetry recorded here.
- **Corrected over-reach** — the US-location claim, the `representation_bias` enum, and `is_sample` are absent from both records.
- **PICU/NICU special populations** — present in both.

---

## 6. Result

| | Full | Core |
|---|---|---|
| Populated slots | **61** | **34** |
| Schema validation | **pass** | **pass** |

Validation commands run:

```
poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_all.yaml -C Dataset \
  data/d4d_concatenated/claudecode_agent/2026-08-06_claude-opus-5-1m-generic-v3-schema2_rep1/CHORUS_d4d.yaml

poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml -C CoreDataset \
  data/d4d_concatenated/claudecode_agent_core/2026-08-06_claude-opus-5-1m-generic-v3-schema2_rep1/CHORUS_d4d_core.yaml
```

**Reconciliation outcome: reconciled.** All 30 audit findings dispositioned — 21 fixed, 9 left as-is with reasons recorded above. No unresolved conflicts between the two records.