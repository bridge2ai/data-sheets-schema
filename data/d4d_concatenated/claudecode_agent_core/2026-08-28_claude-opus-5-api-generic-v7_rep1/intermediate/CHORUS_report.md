# Phase 4 Reconciliation Report — CHORUS

Version label: `2026-08-28_claude-opus-5-api-generic-v7_rep1`
Records reconciled: full (`CHORUS_d4d.yaml`, class `Dataset`) and core (`CHORUS_d4d_core.yaml`, class `CoreDataset`)
Arm: BASELINE (declared bundle only)

---

## 1. Audit summary

The Phase 3 audit returned nineteen findings against the full record: four high, seven medium, eight low. No finding alleged a value that the declared bundle contradicts outright, and no enum value outside a declared set was found. The high findings concerned one identity defect (`id` reusing the landing-page URL and colliding with `page`) and three assertions that converted inference into claim (`is_deidentified.method`, `at_risk_populations.at_risk_groups_included`, `human_subject_research.involves_human_subjects`). The medium findings were predominantly structural: collapsed multivalued slots, declared fields left empty while their content sat in free text, and one caveat that framed a units mismatch as a source conflict. Several low findings were recorded expressly to confirm that a deliberate omission or a deliberate verbatim transcription should survive repair untouched.

---

## 2. Changes made to the full record

### 2.1 `id` — high (changed)

Original: `https://chorus4ai.org/`, identical to `page`.
Reconciled: `https://chorus4ai.org/#chorus-dataset`.

The dataset now carries an identifier distinct from its landing page. It is minted as a fragment on the project website URL, which the bundle attests (`chorus4ai_org_row11.txt`, Source URL `https://chorus4ai.org/`), rather than on an identifier invented from outside the bundle. `page` is unchanged at `https://chorus4ai.org/`, so the collision is resolved by the change on `id` alone. A note recording this minting decision was appended to the top-level `source_caveats`: "The dataset identifier is minted as a fragment on the attested project website URL because no persistent dataset identifier is published."

### 2.2 `is_deidentified.method` — high (changed)

Original `method` listed three items, the third being "de-identification of imaging (in process for the larger imaging cohort as of August 2025)".

Reconciled `method` lists two: "Tokenization of unstructured clinical text with the OHNLP toolkit, and transformation of data using approaches that limit re-identification." The imaging statement was moved out of `method` and into `deidentification_details`, reworded to describe status rather than an applied method: "For imaging, 1000 images were available as of August 2025 with de-identification described as in process for a larger cohort, so de-identification of the wider imaging cohort was not reported as complete." The privacy-tooling sentence that previously opened `deidentification_details` is retained, now placed after that statement.

### 2.3 `at_risk_populations` — high (changed)

The entire slot was removed from the reconciled full record. The original carried `at_risk_groups_included: true` supported only by inference from the presence of PICU and NICU admissions, with an adjacent caveat conceding the inference. No source in the bundle characterizes the cohort as including at-risk populations, and the class declares no field that would carry the caveat alone in a way that answers the slot. The underlying attested fact — that the released dataset covers ICU, PICU, and NICU admissions — remains in `subpopulations[0].identification` and in `instances[0].instance_type`, so no evidence was lost.

### 2.4 `human_subject_research.involves_human_subjects` — high (changed)

The boolean was removed. The object is retained with `regulatory_compliance` (unchanged text) and a rewritten `source_caveats`: "The sources do not report an IRB approval number, an ethics review board of record, or any human subjects research determination for the dataset, so no such determination is asserted here." The original caveat conceded the absence of a determination while the boolean asserted one; the reconciled object states the absence without the assertion.

### 2.5 `creators` — medium (changed)

Original: one Creator object, for Eric S. Rosenthal, with the other five leadership-team members named in `description` prose and mentioned in the creator's `source_caveats`.

Reconciled: six Creator objects — Eric S. Rosenthal (Massachusetts General Hospital), Azra Bihorac (University of Florida), Xiaoqian Jiang (UTHealth Houston), Yulia Strekalova (University of Florida), Parisa Rashidi (University of Florida), Manlik Kwong (Tufts University) — matching the "Bridge2AI CHoRUS Leadership Team" roster and affiliations as the cohort_2_webinar lists them. Each of the five added objects carries a `source_caveats` noting that the source lists the person as a leadership-team member without stating a credit role. The Rosenthal caveat was rewritten to cite both the RePORTER PI designation and the webinar listing, dropping the clause that explained why the others were relegated to the description.

One residual defect is disclosed rather than concealed: all six objects use `principal_investigator` for the person. The schema digest declares `principal_investigator` (range `Person`) as the only person-valued field on Creator, so there is no alternative person field available for a non-PI collaborator; the caveats state that no credit role is attested for the five.

### 2.6 `description` — consequential to 2.5 (changed)

The closing sentence naming the leadership team was removed from `description`, since `creators` now carries that content in its declared fields. The rest of the description is unchanged word for word.

### 2.7 `maintainers[*].role` — medium (changed)

`role` was empty on all four objects in the original; the schema digest constrains Maintainer `role` to an enum. Reconciled: `academic_institution` on the three institutional contacts (McCrary/MGH, dbold@emory.edu, jared.houghtaling@tuftsmedicine.org) and `other` on the chorus-ai GitHub organization entry. The `maintainer_details` text is otherwise unchanged. Note that the audit's suggestion to move name/organization/email out of free text was only partially actionable: the Maintainer class as digested declares `maintainer_details`, `notes`, `role` and `source_caveats` and no name or affiliation fields, so the contact details remain in `maintainer_details`.

### 2.8 `instances[3].source_caveats` — medium (changed)

Rewritten so that it no longer frames the 1000-images and 7,642-admissions figures as a source conflict. It now states that the two figures measure different units and that the sources do not relate them to one another, attributing each figure to its source.

### 2.9 `collection_timeframes[0]` — medium (changed)

The award period was removed from `timeframe_details`, which now reads as retrospective collection from the contributing hospitals with contents reported as of August 2025. The `source_caveats` was extended to state explicitly why `start_date` and `end_date` remain empty and to point to `funders` as the location of the award period. Both date fields remain unpopulated, which is the correct outcome: the award period is a project period, not a collection period, and no encounter date range is stated anywhere in the bundle.

### 2.10 `license_and_use_terms.source_caveats` — medium (changed)

`data_use_permission` remains unpopulated, but the omission is now justified in the caveat rather than left silent, as the audit requested. The added text explains that the ".edu" email requirement and the eligibility rules are stated for the AIM-AHEAD training program rather than as general terms of dataset access, so the sources do not establish which permission category governs the dataset.

### 2.11 `regulatory_restrictions.source_caveats` — medium (changed)

A caveat was added recording that no HIPAA compliance determination is made, and why: the bundle mentions HIPAA only as a workshop topic ("HIPAA/GDPR compliance for OMOP/FHIR data"), which is a statement about coursework. `hipaa_compliant` remains unpopulated, as the audit advised.

### 2.12 `funders[0]` — low (partially changed)

`grants` remains empty and the identifiers remain in `notes`; a `source_caveats` was added explaining that placement. The audit's recommendation to move the grant identifier into the declared `grants` field could not be safely executed: the schema digest gives `grants` a range of `Grant[]` but does not list the Grant class among the object ranges with their required keys, so the field names that would carry the award number are not known from the material available. Rather than guess at a key, the record discloses the constraint.

### 2.13 `status` — low (changed)

Original: the sentence "Initial dataset released under controlled access; data acquisition and modality expansion ongoing." Reconciled: `released`. The substance that was removed is not lost — the controlled-access condition is in `license_and_use_terms.license_terms`, `regulatory_restrictions`, and `confidential_elements`, and the ongoing expansion is in `updates.update_details`.

### 2.14 Top-level `source_caveats` — consequential (extended)

Four sentences were appended, recording: that no DOI, total file count, or dataset-wide size is stated and that no single tabular characterization applies, so those slots are unpopulated; that the English-language requirement applies to training-program applicants and not to dataset content; and the identifier-minting rationale. This converts four silent omissions flagged as low findings into stated, reasoned ones.

### 2.15 Minor wording touched by the de-identification change

`missing_data_documentation[0].missing_data_patterns` now reads "imaging was limited to a small subset" where the original read "a small de-identified subset", consistent with 2.2. `known_limitations[0].limitation_description` now reads "imaging was limited to 1000 images with de-identification in process for a larger cohort", replacing "a small de-identified subset", which both sharpens the figure and drops the completed-de-identification implication. `participant_privacy[0].anonymization_method` dropped the trailing clause "with de-identification applied to imaging" for the same reason; `privacy_techniques` had "patient-focused work to determine" changed to "patient-focused efforts to determine".

---

## 3. Findings left as-is

| Finding | Slot | Disposition |
|---|---|---|
| medium | `data_collectors[*].role` | Left as-is, as the audit intended. The audit recorded no defect here and warned against adding an enum to DataCollector; the digest declares `role` on DataCollector as a plain string. Values `data contributing site` and `site data manager` are unchanged. |
| low | `conforms_to_standard` | Left as-is. `OTHER` still stands in for EDF+, Persyst and the OHNLP schema, all three of which are named in `conforms_to`. The enum offers no more precise term, and splitting one `OTHER` into three identical `OTHER` entries would add no information. |
| low | `doi` | Left omitted. Confirmed deliberate; the reason is now stated in the top-level `source_caveats`. |
| low | `total_file_count` / `total_size_bytes` | Left omitted. The 23 Tb figure covers one modality in ambiguous units and no dataset-wide total is given. The reasoning is now recorded in `source_caveats` rather than left silent. |
| low | `language` | Left omitted; the reason is now in `source_caveats`. |
| low | `maintainers[0].maintainer_details` | The address `cmccrary@mgh.havard.edu` is unchanged, exactly as the audit required. The adjacent caveat was extended with "and none is substituted here" to make the non-correction explicit for any future editor. |
| low | `is_tabular` | Left omitted; the reason is now in `source_caveats`. |
| medium (part) | `maintainers[*]` free-text contact details | Left as-is beyond the `role` addition, for the class-shape reason given in 2.7. |

---

## 4. Core record

The core record was re-derived by projection from the reconciled full record. Every change above propagated where the core schema carries the slot:

- `id` → `https://chorus4ai.org/#chorus-dataset`; `page` unchanged.
- `creators` → six objects, matching the full record.
- `description` → leadership-team sentence removed.
- `status` → `released`.
- `is_deidentified` → imaging moved from `method` to `deidentification_details`.
- `human_subject_research` → boolean removed, caveat rewritten.
- `at_risk_populations` → slot removed entirely.
- `maintainers` → `role` populated on all four.
- `instances[3].source_caveats`, `collection_timeframes[0]`, `funders[0].source_caveats`, `license_and_use_terms.source_caveats`, `regulatory_restrictions.source_caveats`, `missing_data_documentation`, `known_limitations[0]`, `participant_privacy[0]`, top-level `source_caveats` → all as in the full record.

The core header now carries `# Phase 4 reconciliation: completed`, and the `# Sources:` line pointing at the full record path is present as required. `conforms_to_class` is `CoreDataset` in the core and `Dataset` in the full record.

---

## 5. Referent

Both records describe a single referent: the CHoRUS released multimodal critical care dataset — the controlled-access collection of 50,000 ICU/PICU/NICU admissions with linked OMOP, imaging, waveform, EEG and tokenized-note data. The award (OT2OD032701), the training program, and the software organization appear as `funders`, `existing_uses` and `external_resources` respectively, not as the subject. This choice is held consistently across both records and is unchanged from Phase 1.

---

## 6. Source disagreement handling

Unchanged and correct as written. The 50,000 admissions figure (project_documentation, tier 2) is used over "over 45K unique admissions" (cohort_2_webinar, tier 4), with the disagreement, both values, and the preference recorded in the top-level `source_caveats` of both records. The 1000-images / 7,642-admissions pair was reclassified from a source conflict to a units difference (2.8), which is what the evidence supports.

---

## 7. Outcome

Nineteen findings; twelve produced a change to one or both records, seven were left as-is with the reasoning stated above. All four high findings were resolved. Two medium findings were resolved only partially — `funders[0].grants` and the Maintainer contact fields — in both cases because the class shape available in the schema digest does not offer the declared field the audit assumed; both are disclosed in `source_caveats` rather than papered over. No fact was added to either record that the declared bundle does not state, and no previously generated D4D record was consulted.