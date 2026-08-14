# Phase 4 Reconciliation — CHORUS

**Version label:** `2026-08-13_claude-opus-5-api-generic-v4_rep3`
**Arm:** BASELINE (input documents only)
**Bundle:** `data/preprocessed/concatenated/CHORUS_preprocessed.txt` (4 files: NIH RePORTER project 10472824; AIM-AHEAD Bridge2AI for Clinical Care Cohort 2 webinar; chorus4ai.org; chorus-ai GitHub organization overview, 2025-11-14)

**Records reconciled:**

- Full — `data/d4d_concatenated/claudecode_agent/2026-08-13_claude-opus-5-api-generic-v4_rep3/CHORUS_d4d.yaml`
- Core — `data/d4d_concatenated/claudecode_agent_core/2026-08-13_claude-opus-5-api-generic-v4_rep3/CHORUS_d4d_core.yaml`

---

## 1. Referent

`Dataset` admits one referent. Both records describe **the CHoRUS multi-modal critical-care dataset** — the controlled-access repository of ICU/PICU/NICU admission data assembled across 14 data-acquisition hospitals and standardised to OMOP, with waveform, imaging, EEG and tokenised-note modalities.

Two adjacent entities in the bundle are **not** the referent and were not merged into it:

- the `chorus-ai` GitHub organization and its 28 software repositories (MIT-licensed tooling), which are treated as `external_resources`, `machine_annotation_tools` and `preprocessing_strategies` evidence about the dataset, not as the dataset;
- the AIM-AHEAD Bridge2AI for Clinical Care Training Program (Cohort 2), which is a *consumer* of the dataset and is recorded under `existing_uses` and `data_governance`, not as dataset content. Trainee stipends, eligibility rules and application deadlines were excluded entirely as facts about the program, not about the data.

This choice is held identically in both records.

---

## 2. What the audit found

30 findings: 4 high, 12 medium, 14 low. Every core finding had a counterpart in full — the audit confirmed core introduced no facts absent from full. The findings clustered into four patterns:

1. **Enum and shape violations** — free prose in the enum-constrained `data_collectors[].role`.
2. **Constructed entities** — a reviewing organization name assembled from bundle fragments rather than transcribed.
3. **Inference asserted through structured fields while the sibling `source_caveats` conceded the inference** — the dominant pattern, affecting `creators[].principal_investigator`, `at_risk_populations`, `machine_annotation_tools`, and `instances[].data_substrate`.
4. **Internal inconsistency** — two booleans pulling opposite directions on the same underlying fact.

The audit found the two numeric conflicts in the bundle correctly surfaced rather than silently reconciled; those were left untouched (§5).

---

## 3. Changes applied

### 3.1 High severity — both records

**`data_collectors[].role`** — replaced `"Data contributing site"` and `"Central coordinating teams"` with permitted enum members. The 14 contributing hospitals now carry `role: academic_institution` (the bundle describes 20 academic centers, of which 14 contribute); the Standards / Data Acquisition / Tooling sub-teams carry `role: other`. The descriptive text was moved verbatim into `collector_details`, so nothing was lost — only relocated to the field that accepts prose.

**`ethical_reviews[].reviewing_organization`** — the value `"CHoRUS consortium Ethics pillar"` was deleted. The bundle names an Ethics pillar that runs community-facing focus groups and analyses the legal and regulatory landscape; it never states that any body reviewed this dataset, and no IRB, ethics committee or approval number appears anywhere in the four sources. The `EthicalReview` object was retained with `review_details` only, transcribing the ethics-pillar activity the bundle does describe, plus a `source_caveats` recording that no reviewing body, approval identifier or review date is named in the bundle. The object now reports what the evidence supports and is explicit about what it does not.

### 3.2 Medium severity — both records

**`creators[]` — principal-investigator over-assertion.** Only ROSENTHAL, ERIC S. is identified as Principal Investigator in the bundle (NIH RePORTER, project 1OT2OD032701-01, Massachusetts General Hospital). Bihorac, Jiang, Strekalova, Rashidi and Kwong appear only on a slide headed "Bridge2AI CHoRUS Leadership Team" with an institution and no role. `principal_investigator` was therefore removed from those five entries and retained for Rosenthal alone.

The five remain as distinct `Creator` objects — one per person, per the multivalued rule — each carrying `affiliations` as an `Organization` (University of Florida ×3, UTHealth Houston, Tufts University), which the bundle states directly. `Creator` declares no person-valued field other than `principal_investigator`, so the individual's name is carried in `notes` with the slide attribution. This is a class-shape constraint rather than a preference for prose: there is no declared field for a named non-PI creator, and inventing a role to make one fit would restate the defect being corrected.

**`at_risk_populations`** — object removed in full. The value `at_risk_groups_included: true` was reached by inferring minors and neonates from the website's "Patient admissions from ICU, PICU, and NICU". The bundle nowhere discusses at-risk populations, assent, guardian consent or special protections, and the object's own `source_caveats` said so. An absent slot is the correct answer here.

**`human_subject_research.source_caveats`** — rewritten. Two defects: "more than 100,000 critically ill patients" was presented as a description of current holdings when the NIH abstract gives it as an acquisition target ("acquiring an AI-ready data set from more than 100,000 critically ill patients"), and "identifiable" was the auditor's characterisation, contradicted by the bundle's own account of de-identification, tokenisation and transformation "using approaches that limit re-identification". The caveat now states the target figure as a target and drops the identifiability claim.

**`acquisition_methods[].was_directly_observed`** — omitted. It was set `true` while `direct_collection[].is_direct` was set `false` on the same fact, with the explanation that data are extracted retrospectively from existing hospital systems rather than observed for this project. The bundle does not distinguish clinical observation from project observation, so the boolean is unanswerable from the evidence. `is_direct: false` is retained with its `collection_details`, and the retrospective character of the collection is stated in `acquisition_details`.

**`machine_annotation_tools[]` — CTP-deid entry removed** in both records. The bundle lists `CTP-deid Public` in a repository index with no description, no language, no README text. Classifying it as a de-identification tool for clinical imaging is inference from the repository name. The remaining entries — the OHNLP toolkit (bundle: clinical notes "extracted and tokenized using OHNLP toolkit"), `privacy_scan_tool` ("A Privacy Scan tools for medical records"), and `UF-Geocoding` ("geocode OMOP Location entities via DeGauss") — are retained because each carries a source-supplied description.

**`instances[].data_substrate`** — `B2AI_SUBSTRATE:37` (Relational Database) removed from the three OMOP-derived instance types (OMOP row, admission with linked multi-modal data, demographics record). The bundle states the data standard is OMOP and that structured data sit in a cloud enclave; it never describes the physical substrate. For "admission with linked multi-modal data" no listed term fits at all. Per the digest's instruction, the slot was omitted rather than approximated. Substrate terms that the bundle does support were kept: `B2AI_SUBSTRATE:11` (DICOM) for imaging, `B2AI_SUBSTRATE:49` (Waveform Data) for telemetry and EEG, `B2AI_SUBSTRATE:43` (Text) for tokenised clinical notes.

### 3.3 Low severity

**`publisher`** — omitted in both. `https://chorus4ai.org/` is a valid URI but names a website, duplicating `page`, and the bundle's actual publishing organization (Massachusetts General Hospital, the awardee) has no URI or CURIE anywhere in the four sources. Rather than place a website URL in a slot asking for an organization, the slot was dropped; `page` retains the URL and MGH is recorded through `creators[].affiliations` and `data_governance.accountable_organization`.

**`status`** — reduced from a multi-sentence narrative to `partially released`. The website's distinction between "Anticipated Final Dataset" and "Current Released Dataset" supports this directly. The site banner — "This repository is under review for potential modification in compliance with Administration directives" — was moved to `notes`, where residual content belongs, with its date context.

**`distribution_formats[]`** — the enclave-delivery note was removed from the fifth format object, where it read as scoped to EDF+/Persyst alone. The constraint applies to all modalities (the webinar table marks every row "Controlled"), so it is now stated once at dataset level in `notes` and reflected in `data_governance.access_review_process`, which already described the registration-plus-licensing-agreement route.

**`subsets[]`** — `is_data_split` and `is_subpopulation` were removed from the "current release" subset. The bundle presents it as a temporal release state, not as a split or a subpopulation, and the flags asserted a classification the sources do not make. Both flags are retained on the holdout subset, where the NIH abstract states the project will "provision a holdout test set, accessible for model external validation" — a split the bundle names as such.

**Core `source_caveats`** — the closing sentence documenting which slots `CoreDataset` lacks was deleted. That is commentary on how the record was constructed, not on the evidence behind sibling values, and the core-to-full tie is already carried by the required `# Sources:` header line.

---

## 4. Left as-is, with reasons

| Item | Reason |
|---|---|
| Minted `id` values on `Creator`, `Person`, `Organization` | `id` is optional on these classes but serves as record-local identity, not as a factual claim about a resolvable resource. No ORCIDs, RORs or person URIs appear in the bundle; inventing external identifiers would be worse than minting local ones. Documented here rather than in the record. |
| `data_governance.committee_contact.id` = `mailto:cmccrary@mgh.havard.edu` | The misspelled domain is what the source prints. Silently correcting "havard" to "harvard" would substitute a guess for a transcription. The address is retained verbatim and the typo is flagged in `source_caveats`. |
| `created_by: CHoRUS Consortium` | Retained. The audit rated this weakly supported, but the website states "60+ CHoRUS consortium members across 20 different institutions" and the GitHub README describes the CHoRUS Network as the collective developing the dataset. Collective attribution to the consortium is the closest supported answer. |
| `license` omitted | The bundle's only licence statements attach to software: MIT for the GitHub organization, Apache-2.0 for `Chorus_SOP`. No licence is stated for the clinical data, which the bundle describes as controlled-access under a signed licensing agreement. The software licences are recorded against the repositories in `external_resources`; `license_and_use_terms` carries the data-access terms and its `source_caveats` marks the distinction. |
| `total_size_bytes` omitted | The website gives "23 Tb" of waveform data. Tb (terabit) versus TB (terabyte) is a factor-of-eight difference, and the figure covers one modality rather than the dataset. The string is preserved in prose; the integer slot is left empty rather than resolved by guess. |
| `third_party_sharing[]` with content in `notes` | `ThirdPartySharing` declares only `is_shared` plus prose fields. `is_shared: true` is a substantive structured answer supported by the training-program access route and the externally-accessible holdout set; the prose is the only place the class allows the qualifying detail to sit. |
| Both numeric conflicts | See §5. |

---

## 5. Conflicts preserved, not resolved

The bundle disagrees with itself twice. Both records represent the disagreement rather than selecting a value.

**Admission count.** The Cohort 2 webinar states that as of August 2025 the dataset "covers 14 different hospitals with over 45K unique admissions". chorus4ai.org lists a "Current Released Dataset" of "50,000 Patient admissions from ICU, PICU, and NICU". The sources are undated relative to each other beyond the webinar's August 2025 anchor. Both figures are carried, attributed to their source, in `instances[].counts` context and `source_caveats`; neither is presented as the count.

**100,000 — patients or admissions?** The NIH abstract describes acquiring data "from more than 100,000 critically ill patients". The website's "Anticipated Final Dataset" panel reads "100,000 Patient admissions". Patients and admissions are not interchangeable units for a critical-care cohort. Both readings are recorded with their source; no unit is asserted.

A third figure is reported without conflict: 7,642 admissions with radiology data (website), against the webinar's statement that imaging currently has "1000 images available with de-id in process for larger cohort". These describe different things — admissions with radiology in the assembled dataset versus images released — and are recorded separately rather than reconciled.

---

## 6. Slot counts

| | Before reconciliation | After |
|---|---|---|
| Full — populated top-level slots | 56 | 54 |
| Core — populated top-level slots | 35 | 33 |

Net removals in full: `at_risk_populations`, `publisher`. All other changes were within-object (field removals, enum corrections, relocations) and did not change top-level slot occupancy. Core removals mirror full.

---

## 7. Validation

Both records were re-validated after the edits above:

- Full — `linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_all.yaml -C Dataset` → **pass**
- Core — `linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml -C CoreDataset` → **pass**

The `data_collectors[].role` correction was the only finding that had been a live validation risk; the remainder were provenance and shape defects that validated but misrepresented the evidence.

## 8. Outcome

Reconciled. All 4 high-severity and all 12 medium-severity findings were remediated by correction or removal. Of the 14 low-severity findings, 7 were remediated and 7 were retained with the reasons recorded in §4. Core remains a strict projection of full: every fact in core appears in full, no fact was introduced during projection, and the referent choice, the two preserved conflicts and all remediation decisions are identical across the pair.