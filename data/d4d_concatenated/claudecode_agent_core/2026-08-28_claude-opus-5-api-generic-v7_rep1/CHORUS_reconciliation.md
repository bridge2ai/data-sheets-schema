# CHoRUS D4D Reconciliation Report

**Project:** CHORUS
**Version label:** 2026-08-28_claude-opus-5-api-generic-v7_rep1
**Records reconciled:** full (`CHORUS_d4d.yaml`) and core (`CHORUS_d4d_core.yaml`)
**Audit findings addressed:** 19 (4 high, 7 medium, 8 low)

---

## 1. Scope and referent

The `Dataset` referent held constant across both records and across all four phases: **the CHoRUS released clinical care dataset** — the multicenter, multimodal, controlled-access critical care data collection described by the project website and the Cohort 2 webinar — not the CHoRUS project, not the OT2OD032701 award, and not the chorus-ai software organization. Award facts are carried under `funders`; software repositories are carried under `external_resources` and `extension_mechanism`. This choice was already consistent in the Phase 1 record and was not disturbed.

---

## 2. High-severity findings

### 2.1 `id` reused the landing-page URL and collided with `page` — **CHANGED**

**Original (both records):**
```yaml
id: https://chorus4ai.org/
page: https://chorus4ai.org/
```

**Reconciled (both records):**
```yaml
id: https://chorus4ai.org/#chorus-dataset
page: https://chorus4ai.org/
```

The bundle publishes no persistent identifier for the dataset — no DOI, no accession, no registry entry. Under the minting rule, an identifier naming a part of this record with no external referent may be minted as a fragment on an attested URI; the project website URL is attested verbatim in `chorus4ai_org_row11.txt` and in the GitHub overview. The fragment resolves the collision with `page` while keeping the label traceable to something the bundle states. A note explaining the minting was added to the trailing `source_caveats` of both records:

> "The dataset identifier is minted as a fragment on the attested project website URL because no persistent dataset identifier is published."

The award identifier was considered as an alternative and rejected: OT2OD032701 identifies the funding award, not the dataset, and using it would assert an identity the bundle does not make.

### 2.2 `is_deidentified.method` listed imaging de-identification as an applied method — **CHANGED**

**Original (both records):**
```yaml
method: >-
  Tokenization of unstructured clinical text with the OHNLP toolkit; transformation of data using
  approaches that limit re-identification; de-identification of imaging (in process for the larger
  imaging cohort as of August 2025).
```

**Reconciled (both records):**
```yaml
method: >-
  Tokenization of unstructured clinical text with the OHNLP toolkit, and transformation of data
  using approaches that limit re-identification.
deidentification_details: >-
  Clinical notes are not released; only tokens leave the contributing site. For imaging, 1000
  images were available as of August 2025 with de-identification described as in process for a
  larger cohort, so de-identification of the wider imaging cohort was not reported as complete.
  Supporting tooling ...
```

The bundle states only "1000 images available with de-id in process for larger cohort." Imaging de-identification is therefore in progress, not an applied method of the dataset. It was removed from `method` and restated in `deidentification_details` in terms that match what the source says. The consequential downstream edits are noted in §4.

### 2.3 `at_risk_populations.at_risk_groups_included: true` was inferred — **CHANGED (object removed)**

**Original (both records):**
```yaml
at_risk_populations:
  at_risk_groups_included: true
  source_caveats: >-
    The inclusion of minors is inferred from the reported composition ...
```

**Reconciled (both records):** the `at_risk_populations` slot is absent entirely.

The boolean was derived from the presence of PICU and NICU admissions, and the object's own caveat conceded the inference. No source in the bundle characterizes the cohort as including at-risk populations, describes assent procedures, guardian consent, or special protections. With the boolean removed the object would have carried only a caveat about its own absence, which is a pointer rather than an answer, so the slot was omitted. The PICU/NICU composition remains recorded where the bundle supports it, under `subpopulations`, which continues to state the care-unit populations without making a protected-population claim.

### 2.4 `human_subject_research.involves_human_subjects: true` was unstated — **CHANGED (boolean removed, object retained)**

**Original (both records):**
```yaml
human_subject_research:
  involves_human_subjects: true
  regulatory_compliance: [...]
  source_caveats: The sources do not report an IRB approval number ...
```

**Reconciled (both records):**
```yaml
human_subject_research:
  regulatory_compliance:
  - The project established a legal framework for collecting data at scale ...
  source_caveats: >-
    The sources do not report an IRB approval number, an ethics review board of record, or any
    human subjects research determination for the dataset, so no such determination is asserted here.
```

Unlike 2.3, the object retains attested content: the legal-framework statement in the NIH RePORTER abstract and the controlled-access/licensing-agreement condition are directly stated, and `regulatory_compliance` is the field they answer. Only the unsupported boolean was dropped, and the caveat was rewritten to say that no determination is asserted rather than merely that none was found.

---

## 3. Medium-severity findings

### 3.1 `creators` collapsed six named people into one object — **CHANGED**

**Original:** one Creator for Eric S. Rosenthal, with the other five named only in `description` prose.

**Reconciled:** six Creator objects — Eric S. Rosenthal (Massachusetts General Hospital), Azra Bihorac (University of Florida), Xiaoqian Jiang (UTHealth Houston), Yulia Strekalova (University of Florida), Parisa Rashidi (University of Florida), Manlik Kwong (Tufts University) — each with an `affiliations` entry carrying the organization name, and each with a `source_caveats` recording that the webinar lists them on the Bridge2AI CHoRUS Leadership Team without stating a credit role.

Two secondary corrections travelled with this:

- **`principal_investigator` is now a scalar string.** In the original it was written as a nested object (`principal_investigator: {name: Eric S. Rosenthal}`). The reconciled records write the name directly. This also affects the reading of the Rosenthal caveat, which now records both the RePORTER PI attribution and the webinar leadership listing.
- **The leadership roster was removed from `description`** in both records, per the audit's low finding on duplication. The final sentence of the original description ("The leadership team named in project materials comprises Eric Rosenthal ... Manlik Kwong (Tufts University).") does not appear in the reconciled description.

No `credit_roles` values were added: the bundle names the team but assigns no CRediT roles, and the enum would have had to be guessed.

### 3.2 `maintainers[*].role` was empty on every object — **CHANGED**

`role` on Maintainer is enum-constrained. The reconciled records populate it on all four objects: `academic_institution` for the three institutional contacts (Ciera McCrary at MGH, dbold@emory.edu, jared.houghtaling@tuftsmedicine.org), and `other` for the chorus-ai GitHub organization, which none of the enum's institutional categories fits. The `maintainer_details` prose was retained unchanged apart from the caveat edit noted in §5.3, since the class declares no name, email, or organization fields to move it into.

### 3.3 `data_collectors[*].role` — **LEFT AS-IS (no defect)**

The audit recorded this for contrast only. `role` on DataCollector is a plain string in the schema digest, with no enum. The values `data contributing site` and `site data manager` are unchanged in both records, and no enum was imposed on them.

### 3.4 `license_and_use_terms.data_use_permission` omitted — **LEFT AS-IS, omission now justified**

The slot remains unpopulated in both records. On review, the `.edu` email requirement and the organization-eligibility list in the webinar are stated as conditions of the **AIM-AHEAD Bridge2AI for Clinical Care training program**, not as general terms of dataset access; the webinar even notes the requirement "is not a barrier to acceptance into the program." Selecting `institution_specific` or `project_specific` would have generalized a program condition into a dataset-wide permission category. The audit asked that the omission be justified rather than left silent, and it now is, in `license_and_use_terms.source_caveats`:

> "No permission category is recorded for data_use_permission: the institutional ('.edu') email requirement and the eligibility rules are stated for the AIM-AHEAD Bridge2AI for Clinical Care training program rather than as general terms of dataset access ..."

### 3.5 `regulatory_restrictions.hipaa_compliant` omitted — **LEFT AS-IS, guard note added**

No value was added. The bundle's only HIPAA mention is the AI-LEARN workshop topic "HIPAA/GDPR compliance for OMOP/FHIR data," which is a fact about coursework. A caveat was added to `regulatory_restrictions` in both records recording exactly that, so a later pass does not mistake the omission for an oversight and populate it from that line.

### 3.6 `collection_timeframes[0]` carried no structured date — **CHANGED (prose corrected, dates still omitted)**

`start_date` and `end_date` remain empty, and correctly so: the award period is the project period, not the collection period, and the bundle nowhere states the calendar range of the encounters. What changed is that the award dates were **removed from `timeframe_details`**, where they were misleading, and the caveat now states explicitly where they live instead:

> "The award period (2022-09-01 to 2026-11-30) is a project period rather than a data collection period and is recorded under funders."

The object was retained rather than dropped because it still answers the field with attested content — the collection is retrospective, acquisition was ongoing, contents reported as of August 2025.

### 3.7 `instances[3]` caveat framed a units mismatch as a source conflict — **CHANGED**

**Original:** "...the two figures count different units (images versus admissions) and the sources do not reconcile them" — phrased as an unresolved source disagreement.

**Reconciled:** "This figure counts individual images available as of August 2025 (cohort_2_webinar), whereas the 7,642 figure recorded above counts admissions with radiology data ... The two figures measure different units and the sources do not relate them to one another."

The rewrite attributes each figure to its source and states plainly that the two measure different things, removing the implication of a conflict the bundle does not contain.

---

## 4. Consequential edits following 2.2

Two further passages described imaging as de-identified where the source says de-identification is in process. Both were corrected for consistency with the repaired `is_deidentified`:

- `missing_data_documentation[0].missing_data_patterns` — "imaging was limited to a small **de-identified** subset" became "imaging was limited to a small subset."
- `known_limitations[0].limitation_description` — "imaging was limited to a small de-identified subset" became "imaging was limited to **1000 images**", which is what the source states.

The `instances[3].instance_type` string "De-identified radiology image available in the enclave" was retained: the webinar's "1000 images available with de-id in process for larger cohort" does support the 1000 images themselves being de-identified, and the adjacent caveat makes the scope clear.

---

## 5. Low-severity findings

### 5.1 `status` was a sentence, not a status token — **CHANGED**

`Initial dataset released under controlled access; data acquisition and modality expansion ongoing.` → `released` in both records. The substance was already present in `updates.update_details`, which is unchanged.

### 5.2 `conforms_to_standard` includes a bare `OTHER` — **LEFT AS-IS**

`OTHER` covers three unlisted standards (EDF+, Persyst, OHNLP), all named in `conforms_to` prose and in `distribution_formats`. The enum offers no finer term and admits no repetition that would distinguish them. Imprecise but traceable; unchanged in both records.

### 5.3 `funders[0].grants` empty — **LEFT AS-IS, reasoning recorded**

The award identifiers remain in `notes`. The schema digest supplied for this task declares `grants` with range `Grant[]` but does not enumerate the Grant class's own fields, so constructing a Grant object would have meant guessing its shape. A caveat was added to the funder object recording this rather than leaving the choice unexplained. This is the one repair where a structural finding was answered with an explanation instead of a restructure.

### 5.4 `doi` omitted — **LEFT AS-IS**

No DOI appears anywhere in the bundle. Confirmed deliberate and noted in the trailing `source_caveats`.

### 5.5 `total_file_count` / `total_size_bytes` omitted — **LEFT AS-IS**

"23 Tb Waveform data" is one modality's size in ambiguous units; "1.6 Billion Rows" is a row count, not bytes. No dataset-wide total is stated. The reasoning is now recorded in the trailing `source_caveats` of both records rather than left silent.

### 5.6 `language` omitted — **LEFT AS-IS, guard note added**

The "Working command of English" line is an applicant eligibility requirement, not a statement about dataset content. The trailing `source_caveats` now says so explicitly, guarding against a later pass populating the slot from it.

### 5.7 Misspelled maintainer email preserved — **LEFT AS-IS, guard strengthened**

`cmccrary@mgh.havard.edu` is transcribed exactly as the website publishes it. The caveat was extended from noting the apparent misspelling to stating that no correction is substituted here, so the address is not "fixed" into one the bundle does not contain.

### 5.8 `description` duplicated the leadership roster — **CHANGED**

Removed, as described in §3.1.

### 5.9 `is_tabular` omitted — **LEFT AS-IS**

No single boolean is true of a dataset spanning OMOP tables, DICOM, waveforms, and tokenized text. Reasoning recorded in the trailing `source_caveats`.

---

## 6. Range corrections found during reconciliation

Three multivalued slots held a bare string where the schema declares a list. Corrected in both records:

| Slot | Original | Reconciled |
|---|---|---|
| `machine_annotation_tools[0].tools` | scalar `OHNLP toolkit` | one-item list |
| `distribution_dates[0].release_dates` | scalar string | one-item list |
| `existing_uses[*].examples` | scalar string | one-item lists |
| `external_resources[*].external_resources` | scalar string | one-item lists |

These were not in the audit findings but are validation-relevant; the reconciled records carry the list forms.

---

## 7. Cross-record consistency

Every change above was applied identically to both records wherever the slot exists in `CoreDataset`. The core record is a projection of the reconciled full record: `id`, `name`, `title`, `description`, `status`, `creators`, `funders`, `instances`, `is_deidentified`, `human_subject_research`, `license_and_use_terms`, `regulatory_restrictions`, `maintainers`, `collection_timeframes`, and the trailing `source_caveats` all match their full-record counterparts. `at_risk_populations` is absent from both. `conforms_to_class` and `conforms_to_schema` differ by design, naming `CoreDataset` and the core schema path respectively. Slots the core schema does not declare — `page` aside, which it does — were not carried across.

---

## 8. Findings not acted on

None. Of the 19 findings, 11 produced edits and 8 were left as-is with the reasoning recorded in the record itself (5 of those 8 were recorded by the audit specifically to confirm a deliberate omission or transcription and to prevent its disturbance).

## 9. Outcome

Reconciliation complete. Four high-severity findings resolved: one identifier collision repaired by minting a fragment on an attested URI, three unsupported assertions withdrawn (imaging de-identification as applied method, at-risk-population inclusion, human-subjects determination) with the attested content around them preserved. Seven medium findings: five structural repairs (creators expanded six-fold, maintainer roles populated, timeframe prose corrected, instance caveat rewritten, permission omission justified), two omissions confirmed with reasoning. Eight low findings: three edits, five confirmations. No slot value in either reconciled record now rests on inference the bundle does not state, and no identifier not present in the bundle was supplied from outside it.