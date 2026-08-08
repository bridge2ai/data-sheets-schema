# CHoRUS D4D Reconciliation Report

**Version label:** `2026-08-06_claude-opus-5-1m-generic-v3-schema2_rep3`
**Arm:** BASELINE (input documents only)
**Source bundle:** `data/preprocessed/concatenated/CHORUS_preprocessed.txt`
**Records reconciled:**
- Full — `data/d4d_concatenated/claudecode_agent/2026-08-06_claude-opus-5-1m-generic-v3-schema2_rep3/CHORUS_d4d.yaml`
- Core — `data/d4d_concatenated/claudecode_agent_core/2026-08-06_claude-opus-5-1m-generic-v3-schema2_rep3/CHORUS_d4d_core.yaml`

---

## 1. Referent decision (restated and held)

`Dataset` admits one referent. The declared bundle describes both a *funded project* (NIH OT2OD032701, the CHoRUS data generation project) and a *data artifact* (the multi-modal ICU/PICU/NICU repository, 50,000 admissions, nine modalities, controlled-access enclave).

**The referent is the data artifact — the CHoRUS multi-modal critical care dataset.** Project-level facts (award number, PIs, training program, workforce development) are retained only where the schema declares a slot for them (`funders`, `creators`, `purposes`, `addressing_gaps`, `existing_uses`). This choice is held identically in both records; no slot in either file describes the training program as though it were the dataset.

Consequence carried through reconciliation: the AIM-AHEAD Bridge2AI for Clinical Care Training Program (stipend amounts, eligibility, application deadlines, curriculum tables) is **not** dataset content. It is represented only where it bears on the dataset — as an `existing_uses` entry, as an access route in `license_and_use_terms`, and as `third_party_sharing`. Trainee eligibility criteria, W-9 requirements and application dates were not imported into either record.

---

## 2. What the audit found

The audit returned 21 findings: 2 high, 7 medium, 8 low, 4 informational. No fabricated facts, no undefined enum values, and no collapsed-list defects were found in either record.

The dominant pattern was **pair inconsistency running in both directions**:

- The **full** record carried four slots where the range class declares specific fields, the bundle answers those fields, and the content was nonetheless placed in free-text `notes` / `*_details` while the declared fields stayed empty. This is precisely the v3 structure defect. The core record, from the same evidence, had populated those fields.
- The **core** record dropped five slots the full record populated from clearly supported evidence, and partially compensated by restating three of them as narrative inside the top-level `notes` — pointer-style prose rather than field population.

Neither record was treated as authoritative. Declared-field population was pushed from core into full; the dropped slots were pushed from full into core.

---

## 3. Changes to the FULL record

### 3.1 `funders` — declared fields populated (high)

`FundingMechanism` declares `grantor` and `grants`. Both were empty; the funding facts sat in `notes`.

**Changed to:**

```yaml
funders:
  - grantor: National Institutes of Health (NIH) Common Fund, Bridge2AI program
    grants:
      - OT2OD032701
    notes: >-
      Awarded to Massachusetts General Hospital. Award amount 5,880,300 USD
      for fiscal year 2022 (application ID 10472824, project number
      1OT2OD032701-01). The project website states the content is solely the
      responsibility of the authors and does not necessarily represent the
      official views of the NIH.
```

**Why:** the NIH RePORTER record and the project website both state the grantor and the core project number explicitly. `notes` was retained only for the residue the class declares no field for (award amount, application ID, disclaimer). This now matches the core record on the same fact.

### 3.2 `collection_timeframes` — dates lifted out of prose (high)

`start_date` and `end_date` were empty; the award period appeared only inside `timeframe_details`.

**Changed to:**

```yaml
collection_timeframes:
  - start_date: '2022-09-01'
    end_date: '2026-11-30'
    timeframe_details: >-
      Dates correspond to the NIH award period (project start 2022-09-01,
      project end 2026-11-30) rather than to a stated clinical-encounter
      window; the bundle does not state the range of admission dates
      covered by the retrospective extract.
```

**Why:** the dates are stated verbatim in the RePORTER record. The qualification that these are *award* dates rather than *encounter* dates was preserved, because the bundle nowhere states the clinical date range and the structured fields would otherwise overstate what is known.

### 3.3 `data_collectors` — `role` populated on all four objects (medium)

Role information existed as prose in `collector_details`. `role` is a free-text string on `DataCollector` (not enum-constrained), so the evidence transfers directly:

| object | `role` now set to |
|---|---|
| Data Acquisition centers | `data contributing site` |
| Data site managers | `site data manager` |
| CHoRUS sub-teams (Standards, Data Acquisition, Tooling) | `standards and tooling development` |
| Clinical collaborators | `semantic mapping and clinical validation` |

`collector_details` was trimmed of the duplicated role statement in each case.

### 3.4 `ethical_reviews` — `reviewing_organization` populated (medium)

Set to `CHoRUS consortium (Ethics pillar)`, matching the core record. `review_details` retains the substantive content: community-facing ethics focus groups to determine what data is appropriate for public sharing, and analysis of the existing legal and regulatory landscape.

**Not** populated: `contact_person`. The bundle names a program manager and two access contacts, none identified as an ethics contact. Omitted rather than guessed.

### 3.5 `status` — narrowed to the slot's intent (low)

Replaced the multi-sentence narrative (which duplicated `collection_timeframes`) with:

```yaml
status: active; partial release, collection ongoing
```

The award-period sentences were removed as duplication; the website's under-review banner remains in `notes` and `regulatory_restrictions.notes`, where it already sat.

### 3.6 `distribution_formats` — reallocated (low)

The sixth object described the enclave access route, not a format. It was removed from `distribution_formats` and the fact folded into `license_and_use_terms.license_terms`, which already describes controlled access. The five remaining objects (OMOP tabular, OHNLP token output, DICOM, WFDB, EDF+/Persyst) were left with `notes` only — the bundle gives no access URL per format, so `access_urls` stays empty rather than being filled with the generic site URL.

---

## 4. Changes to the CORE record

Each of the five restored slots is supported by the same bundle text that supports the full record's version; none required new interpretation.

### 4.1 `splits` — restored (medium)

```yaml
splits:
  - split_details: >-
      A holdout test set is sequestered and made accessible for external
      validation of models, intended to aid marketplace adoption of
      AI-developed models for implementation in acute and critical care.
      The bundle does not state the size of the holdout set or the
      partitioning criteria.
```

Stated twice in the RePORTER abstract. The prose restatement was removed from `notes`.

### 4.2 `third_party_sharing` — restored (medium)

```yaml
third_party_sharing:
  - is_shared: true
    notes: >-
      Access is extended beyond the contributing consortium: the holdout
      test set is accessible for external model validation, and trainees
      in the AIM-AHEAD Bridge2AI for Clinical Care Training Program are
      provisioned access to the CHoRUS dataset after signing a licensing
      agreement. Access remains controlled in all cases.
```

The boolean is the field the class exists to carry; it was previously recoverable only by reading narrative.

### 4.3 `direct_collection` — restored (medium)

```yaml
direct_collection:
  - is_direct: false
    collection_details: >-
      Retrospective data collection. Data is extracted from existing
      hospital systems (EHR, PACS, bedside monitors, hospital EEG
      database) at 14 data-contributing centers rather than collected
      directly from patients.
```

The sentence "obtained retrospectively … rather than collected directly from patients" was removed from `notes`, since it now lives in the field that declares it.

### 4.4 `participant_privacy` — restored (medium)

```yaml
participant_privacy:
  - anonymization_method: >-
      Tokenization of unstructured EHR text using the OHNLP toolkit;
      de-identification in process for imaging prior to release of the
      larger cohort; transformation of data using approaches that limit
      re-identification.
    privacy_techniques:
      - tokenization of clinical notes
      - local retention of clinical notes with only tokens transferred
      - de-identification of imaging (in process)
      - privacy scan tooling for medical records (privacy_scan_tool)
      - controlled-access cloud enclave
```

`reidentification_risk` and `data_linkage` were **not** populated: the bundle states that methods "limit re-identification" but makes no risk assessment and describes no linkage.

### 4.5 `file_collections` — restored, nine entries (medium)

The webinar's data-type table is the single most structured piece of evidence in the bundle and was surviving in the core record only as scattered prose. Nine `FileCollection` objects were restored, one per modality, each carrying `id`, `name`, `conforms_to`, and a `notes` field recording access control and metadata status:

| modality | `conforms_to` | metadata status per source |
|---|---|---|
| Demographics | OMOP | Yes |
| Medication administration | OMOP | Yes (OMOP schema) |
| Procedures | OMOP | Yes (OMOP schema) |
| Nursing flowsheets | OMOP | Yes (OMOP schema with extensions) |
| Diagnoses | OMOP | Yes (OMOP schema) |
| Clinical notes | OHNLP | Planned |
| Imaging (from PACS) | DICOM | Planned |
| Waveform telemetry | WFDB | Yes (PhysioNet schema extended) |
| Waveform EEG | EDF+ and Persyst | Yes |

All nine carry access control `Controlled`. `collection_type` was set to `raw_data` on none of them — the enum's members (`raw_data`, `processed_data`, `training_split` …) do not correspond to a modality partition, and forcing a value would assert something the bundle does not state. `file_count` and `total_bytes` were left empty except where the bundle gives a figure (see §5.3).

---

## 5. What was left as-is, and why

### 5.1 `id` reuses the project-site URL (low)

Both records set `id: https://chorus4ai.org/`, the same URI as `page`. **Left unchanged.** The bundle contains no DOI, no accession, and no dataset-specific persistent identifier. `id` is required. Minting a synthetic identifier would fabricate provenance; reusing the only stable project URI is the least-inventive available answer. The non-distinguishing overlap with `page` is a genuine consequence of the evidence, not a modelling error.

### 5.2 `creators` — names in `notes` (low)

Five of six `Creator` objects carry the person's name only inside `notes`. **Left unchanged.** Per the digest, `Creator` declares `affiliations`, `credit_roles`, `principal_investigator` and `notes` — and no generic name field. `principal_investigator` was set only for Eric Rosenthal, whom the RePORTER record identifies as PI; applying it to the other five leadership-team members would assert a role the bundle does not give them. `affiliations` is populated for all six. This is a schema limitation, correctly worked around rather than papered over.

### 5.3 `instances.counts: 50000` (low)

The two sources disagree: the webinar states "over 45K unique admissions" as of August 2025; the project website's "Current Released Dataset" panel states 50,000. **Left unchanged**, with the disagreement disclosed in both the instance-level `notes` and the top-level `notes`:

> Figures differ between sources: the project website states 50,000 admissions in the current released dataset, while the September 2025 webinar states over 45,000 unique admissions as of August 2025. The anticipated final dataset is stated as 100,000 patient admissions.

The structured integer necessarily selects one value; the website figure was chosen as the more recent and more specific release statement, and the alternative is preserved verbatim rather than discarded. This satisfies the disagreement rule — the record represents what the evidence states rather than silently collapsing it.

Related quantitative facts retained without conflict: 1.6 billion rows of EHR OMOP data, 7,642 admissions with radiology data, 23 Tb of waveform data, 1000 images currently available, 14 contributing hospitals, 20 institutions, 60+ consortium members, 9 modalities.

### 5.4 `conforms_to: OMOP Common Data Model (OHDSI)` (low)

`conforms_to` is single-valued but the dataset conforms to five standards by modality. **Left unchanged** in both records. OMOP is the dominant standard (five of nine modalities) and is the one the bundle names repeatedly as the harmonization target. With `file_collections` now restored to the core record, the per-modality standards are structurally present in *both* records rather than only the full one — which removes the audit's stated concern that the core record "loses that qualification entirely."

### 5.5 `maintainers` and the reproduced typo (low)

`Maintainer.role` is enum-constrained; `academic_institution` and `other` were used and remain valid. Named individuals stay in `maintainer_details` because `Maintainer` declares no name field.

The address `cmccrary@mgh.havard.edu` is **reproduced verbatim**, as is the banner typo "repoitory". Correcting either would silently diverge from the source. However, the audit's low-severity point about editorial commentary was acted on: the parenthetical "as printed on the site" was moved out of the value and into the object's `notes`, so the value field carries the datum and the commentary is separated from it.

### 5.6 `known_biases` and `known_limitations` — enum categorization retained (info)

`selection_bias` for the multi-center academic ICU sampling, and `coverage_limitation` / `scope_limitation` / `integration_limitation` for the three stated limitations. **Left unchanged.** The audit correctly notes these categorizations are interpretive — the bundle labels no bias by type. They were retained because each maps to explicitly stated bundle content (federated sampling "to ensure a balanced and diverse cohort" as a stated mitigation for selection; partial modality availability; ICU/PICU/NICU scope; enclave-only access), and because the enum is closed, so the alternative to a conservative reading is omitting slots the evidence plainly supports.

### 5.7 `regulatory_restrictions` (info)

`confidentiality_level: restricted` retained — all nine data types are marked "Controlled". `hipaa_compliant` remains **omitted**: HIPAA appears in the bundle only as a training-curriculum topic ("HIPAA/GDPR compliance for OMOP/FHIR data"), never as a compliance assertion about this dataset. Populating it, including with `under_review`, would manufacture a claim.

### 5.8 `external_resources` (low)

`archival`, `future_guarantees` and `restrictions` remain empty. The bundle supports none of them. Omission is the correct answer.

### 5.9 Slots deliberately absent from both records

Not populated anywhere, for want of evidence: `doi`, `download_url`, `version`, `total_file_count`, `total_size_bytes`, `compression`, `is_tabular` (the dataset is explicitly multi-modal, so a boolean would misdescribe it), `citation`, `imputation_protocols`, `annotation_analyses`, `errata`, `retention_limit`, `version_access`, `consent_revocations`, `collection_notifications`, `participant_compensation` (the $8,000 figure is a *trainee* stipend, not participant compensation — importing it would be a referent error), `at_risk_populations`, `subpopulations` (the bundle asserts diversity as a goal but gives no distribution).

---

## 6. Outcome

| | full | core |
|---|---|---|
| Slots populated before reconciliation | 61 | 48 |
| Slots populated after reconciliation | 61 | 53 |
| Slots restructured (content moved into declared fields) | 6 | 0 |
| Slots restored | 0 | 5 |
| Slots removed | 0 | 0 |
| Facts added from outside the bundle | 0 | 0 |

**Pair consistency:** the two records now agree on every fact they both express. The four declared-field divergences (`funders`, `collection_timeframes`, `data_collectors.role`, `ethical_reviews.reviewing_organization`) are resolved in favour of the structured form the core record already used. The five core omissions are resolved in favour of the full record's structured form. Where a fact appears in only one record, it is because the core schema declares no slot for it, not because the two disagree.

**Referent consistency:** confirmed — both records describe the CHoRUS multi-modal critical care dataset, not the CHoRUS project and not the AIM-AHEAD training program.

**Provenance:** all values trace to the four-file declared bundle. No prior D4D record of any arm, label or date was read, opened, grepped or consulted at any phase.