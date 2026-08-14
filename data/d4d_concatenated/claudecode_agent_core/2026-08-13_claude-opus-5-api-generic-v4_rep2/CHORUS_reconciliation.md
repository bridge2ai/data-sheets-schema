# CHoRUS — Phase 4 Reconciliation Report

**Project:** CHORUS
**Version label:** `2026-08-13_claude-opus-5-api-generic-v4_rep2`
**Arm:** BASELINE (input documents only)
**Declared bundle:** `data/preprocessed/concatenated/CHORUS_preprocessed.txt` (4 files: NIH RePORTER project page, AIM-AHEAD/Bridge2AI Cohort 2 webinar deck, chorus4ai.org, chorus-ai GitHub organization overview)

**Records reconciled:**

- Full — `data/d4d_concatenated/claudecode_agent/2026-08-13_claude-opus-5-api-generic-v4_rep2/CHORUS_d4d.yaml`
- Core — `data/d4d_concatenated/claudecode_agent_core/2026-08-13_claude-opus-5-api-generic-v4_rep2/CHORUS_d4d_core.yaml`

---

## 1. Referent

`Dataset` admits one referent. Both records describe **the CHoRUS released clinical dataset** — the multi-modal, controlled-access critical-care corpus assembled from 14 data-contributing hospitals — and **not** the OT2OD032701 award, the CHoRUS Network organization, or the AIM-AHEAD Bridge2AI for Clinical Care training program.

Consequences of that choice, applied consistently across both records and unchanged in Phase 4:

- Award facts (application ID 10472824, project number 1OT2OD032701-01, $5,880,300, 2022-09-01 to 2026-11-30) populate `funders` and are **not** treated as dataset collection dates or release dates.
- The training program's stipend, eligibility, application deadlines and curriculum are **not** dataset facts. They appear only where they bear on the dataset itself — the registration-form-plus-licensing-agreement access route, the `.edu` email requirement, and the fact that the data is in use for training activities.
- The GitHub organization's MIT license covers CHoRUS *software repositories*. It is recorded as such and is **not** asserted as the dataset license, which the bundle never states.

---

## 2. What the audit found

Nineteen findings: 2 high, 6 medium, 11 low.

The audit's overall verdict was that both records are broadly faithful — modality-by-modality standards (OMOP, OHNLP, DICOM, WFDB, EDF+/Persyst), the three conflicting admission counts, the notes-stay-local arrangement, the staged imaging and EEG release, and the enclave/licensing access route are all traceable to source, and source conflicts are surfaced rather than silently resolved. Enum usage is valid throughout; multivalued slots emit one object per entity; no object was placed in a scalar-ranged slot.

The defects clustered into three kinds:

1. **One fabricated identifier** (high, duplicated across records) — a constructed `mailto:` address for the principal investigator, self-declared as constructed in the record's own caveat.
2. **Assertion beyond the source** (medium) — five leadership-team members promoted to `principal_investigator`; an access-request contact promoted to licensing contact; an admission-level count filed under an imaging-study `instance_type`; a controlled-access qualifier dropped from four of five distribution formats.
3. **Placement and redundancy** (low) — an editorial gloss in `created_by`, a source banner triple-recorded, an inferred `archival: false`, and projection meta-commentary sitting in the core record's `source_caveats`.

---

## 3. Changes to the full record

### 3.1 Fabricated PI identifier — removed (finding 1, high)

`creators[0].principal_investigator.id` held `mailto:erosenthal@mgh.harvard.edu`. The bundle gives only `ROSENTHAL, ERIC S.` and `MASSACHUSETTS GENERAL HOSPITAL`. An email address assembled from a name and an institution is an invented fact, and a caveat admitting the invention does not license it.

Replaced with a project-scoped opaque identifier that asserts nothing outside the bundle:

```yaml
principal_investigator:
  id: chorus:person-rosenthal-eric-s
```

The name and the MGH affiliation remain, both attested by NIH RePORTER. No other `mailto:` in either record is constructed — the two access-request addresses and the program-manager address are transcribed verbatim from the bundle and were left untouched.

### 3.2 Principal-investigator overreach — removed for five people (finding 3, medium)

The webinar deck carries a slide headed *"Bridge2AI CHoRUS Leadership Team"* listing Rosenthal (MGH), Bihorac (UF), Jiang (UTHealth Houston), Strekalova (UF), Rashidi (UF) and Kwong (Tufts). It assigns no roles. NIH RePORTER names exactly one principal investigator.

`principal_investigator` is now populated for Rosenthal only. The other five remain as `Creator` entries — the leadership slide is evidence of responsibility for the project that generates the dataset — but each now carries:

- `affiliations`: the named institution as an `Organization` (structurally populated, per the v3 rule);
- `notes`: the individual's name as printed on the slide;
- `source_caveats`: that the bundle lists the person on a leadership-team slide without stating a role, and that NIH RePORTER names only one PI.

**Trade-off recorded explicitly:** `Creator` declares no person-valued field other than `principal_investigator`. Carrying these five names in `notes` is in tension with the rule preferring declared fields over free text. The alternative — leaving them in `principal_investigator` — states something the bundle does not. Accuracy of the assertion was preferred over structural placement, and the tension is logged here rather than hidden.

### 3.3 Licensing contact — removed (finding 5, medium)

`license_and_use_terms.contact_person` named Jared Houghtaling. The bundle lists that address under **"Request access"** on the GitHub page, and names him separately as a Tufts lecturer in the curriculum table. Neither is a licensing or use-terms contact. The slot is now omitted; the access-request role was already correctly held in `data_governance.stewardship_roles`, so nothing was lost.

### 3.4 Radiology count/unit mismatch — instance type corrected (finding 6, medium)

chorus4ai.org states **"7,642 Admissions with Radiology Data"**. The record filed `counts: 7642` under `instance_type: "Radiology imaging study"` — a count of admissions presented as a count of studies.

Corrected by changing the instance type to match the unit the source actually reports:

```yaml
instance_type: Hospital admission with associated radiology (DICOM) data
counts: 7642
```

The number was not changed and no study-level count was inferred. The separate webinar statement that "1000 images available with de-id in process for larger cohort" remains recorded as its own instance entry, with its own caveat that the two figures are not commensurable.

### 3.5 Controlled-access qualifier restored across all formats (finding 8, medium)

The webinar table marks **every** listed data type `Controlled` for access control, and adds that OMOP and telemetry sit "in enclave" while clinical notes are "stored locally except tokens". Only the first `distribution_formats` entry carried that qualifier. The OHNLP, DICOM, WFDB and EDF+/Persyst entries now each record controlled access, and the OHNLP entry records the local-storage/tokens-only arrangement. `download_url` and `access_urls` remain absent on all entries — the bundle publishes no direct data URL, and the registration/licensing route belongs in `data_governance`, where it already sits.

### 3.6 `created_by` gloss — trimmed (finding 9, low)

`"CHoRUS for Equitable AI Network (Bridge2AI data generation project)"` was a composed label. Replaced with **`CHoRUS for Equitable AI`**, the name as printed on the GitHub organization page and README. The Bridge2AI relationship is already carried in `description` and `related_datasets`.

### 3.7 `status` — banner removed, kept in two places not three (findings 10/11, low)

The chorus4ai.org banner ("This repoitory is under review for potential modification in compliance with Administration directives.", *sic*) was quoted verbatim in `status`, `regulatory_restrictions` and `source_caveats`. `status` is a short descriptor slot. It now reads as a plain status; the banner is retained verbatim in `regulatory_restrictions` (where it bears on access) and in `source_caveats` (where it warns that the source website may change), and the original spelling is preserved in both.

### 3.8 Inferred archival flag — removed (finding 16, low)

`external_resources` for the GitHub organization carried `archival: false`. The bundle says nothing about whether that repository space is archived. The field is now omitted on all six entries. The six entries themselves were left one-per-resource, as the audit confirmed correct.

---

## 4. Changes to the core record

The core record is a projection of the corrected full record. Every correction in §3 that has a `CoreDataset` counterpart was applied identically, with no independent re-derivation from the bundle:

| Full-record change | Applied to core |
|---|---|
| §3.1 fabricated PI `mailto:` → opaque id | Yes (finding 2) |
| §3.2 PI overreach for five leadership members | Yes (finding 4) |
| §3.3 licensing `contact_person` removed | Yes (finding 7) |
| §3.4 radiology instance type corrected | Yes (finding 8, core) |
| §3.7 banner removed from `status` | Yes (finding 11) |
| §3.5, §3.6, §3.8 | No counterpart slot in `CoreDataset`; not applicable |

### 4.1 Projection meta-commentary removed from `source_caveats` (finding 17, low)

The core record's `source_caveats` ended with a paragraph listing which full-record slots have no `CoreDataset` counterpart. `source_caveats` is a trust annotation about the evidence behind sibling values, not a description of the projection process. That paragraph was deleted from the record and is reproduced in §6 below, which is where mapping decisions belong.

The remainder of core `source_caveats` — the admission-count conflict, the software-vs-dataset license distinction, the administrative-review banner — is genuine evidence commentary and was retained.

### 4.2 Header

The core header carries `# Sources:` naming both the bundle and the full-record path, and `# Phase 4 reconciliation: completed` was written only after this phase ran.

---

## 5. What was left as-is, and why

| Finding | Slot | Decision and reasoning |
|---|---|---|
| 12/13 (low) | `data_governance.stewardship_roles` | **Unchanged.** The audit suggested promoting the two access-request contacts into `committee_members` (`Person[]`). Declined: the bundle offers only *"Request access: dbold@emory.edu or jared.houghtaling@tuftsmedicine.org"* on a GitHub README. Filing two email addresses as members of an access committee would assert a governance body the bundle never describes — the same class of overreach corrected in §3.2 and §3.3. `committee_name`, `committee_contact`, `committee_members` and `access_review_process` therefore stay empty. The addresses are verbatim from source, so recording them as role strings is faithful; only the redundant institutional restatement was trimmed. |
| 14 (low) | `data_collectors[*].role` | **Unchanged.** `DataCollector.role` carries no enum in the schema, so "Data Acquisition centers", "Consortium membership" and "Awardee organization" are permissible free text. The asymmetry with the enum-bound `Maintainer.role` (used correctly in `maintainers`) is a schema property, not a record defect. |
| 15 (low) | `at_risk_populations` | **Unchanged.** `at_risk_groups_included: true` is supported by the explicit "ICU, PICU, and NICU" statement. `special_protections`, `assent_procedures` and `guardian_consent` remain omitted because the bundle states nothing about them, and `source_caveats` says so. Omission is the correct answer where evidence is absent. |
| 18 (low) | `collection_timeframes[0].start_date` / `end_date` | **Unchanged.** Correctly omitted. The bundle gives an award period and an "as of August 2025" snapshot date, neither of which is a clinical-data collection span. The caveat distinguishing the two was retained. |
| 19 (low) | `total_size_bytes` | **Unchanged.** chorus4ai.org reports "23 Tb Waveform data". The unit is ambiguous (Tb vs TB) and covers waveforms only, not the whole dataset, so no byte total can be derived. The figure is recorded verbatim in `description` with the modality attached. |
| — | `is_deidentified` | **Unchanged.** Retained as stating de-identification is in process for imaging and that transformation approaches "limit re-identification"; the bundle does not claim completed de-identification, and the record does not either. |
| — | Admission-count conflict | **Unchanged.** Three figures appear: 100,000 (RePORTER goal and chorus4ai "Anticipated Final"), 45,000+ (webinar, as of August 2025), 50,000 (chorus4ai "Current Released"). All three are represented with their sources and dates rather than reconciled to one number. This is the correct handling under the disagreement rule and was left alone. |

---

## 6. Full → core slot mapping (relocated from core `source_caveats`)

Full-record content with no `CoreDataset` counterpart, and therefore present only in the full record:

- Modality-by-modality `distribution_formats` (OMOP / OHNLP / DICOM / WFDB / EDF+ and Persyst) with their per-format access qualifiers.
- `external_resources` (chorus4ai.org, chorus-ai GitHub, Chorus_SOP, chorus-mapping, chorus-developer, package status page).
- `data_collectors`, `collection_mechanisms`, `preprocessing_strategies`, `labeling_strategies`.
- `at_risk_populations`, `regulatory_restrictions`, `content_warnings`.
- `total_file_count` / `total_size_bytes` (both omitted in the full record as well — see §5).

Core-record slots are the intersection of what `CoreDataset` declares and what the corrected full record supports. No core slot carries a fact absent from the full record.

---

## 7. Validation

Both records were validated after the Phase 4 edits:

```
poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_all.yaml \
  -C Dataset data/d4d_concatenated/claudecode_agent/2026-08-13_claude-opus-5-api-generic-v4_rep2/CHORUS_d4d.yaml

poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml \
  -C CoreDataset data/d4d_concatenated/claudecode_agent_core/2026-08-13_claude-opus-5-api-generic-v4_rep2/CHORUS_d4d_core.yaml
```

Both pass. The identifier substitution in §3.1 preserves the `uriorcurie` range; the `principal_investigator` removals in §3.2 touch an optional slot; the omissions in §3.3 and §3.8 touch optional slots.

---

## 8. Outcome

**Reconciled.** Two high-severity findings resolved (one fabricated identifier, duplicated across records). Four medium findings resolved by narrowing assertions to what the bundle states and by aligning one count with its declared unit. Four low findings resolved by trimming redundancy and one inferred boolean. Six findings — five low, one recording a positive check — were examined and deliberately left as-is, with the reasoning recorded in §5; in two of those cases the audit's suggested improvement was declined because adopting it would have introduced a new inference.

Both records now assert nothing that the declared bundle does not support, and the two remain consistent with one another and with the single chosen referent.