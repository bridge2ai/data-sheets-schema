# CHoRUS — Phase 4 Reconciliation Report

**Version label:** `2026-08-06_claude-opus-5-1m-generic-v3-schema2_rep2`
**Arm:** BASELINE (input documents only)
**Declared bundle:** `data/preprocessed/concatenated/CHORUS_preprocessed.txt` (4 files: NIH RePORTER project page, AIM-AHEAD Cohort 2 informational webinar, chorus4ai.org project documentation, CHoRUS GitHub organization overview)
**Records reconciled:** `CHORUS_d4d.yaml` (full, class `Dataset`) and `CHORUS_d4d_core.yaml` (core, class `CoreDataset`)

---

## 1. Referent decision

`Dataset` admits one referent. The declared bundle describes three separable things: the CHoRUS **data generation project** (NIH award OT2OD032701), the CHoRUS **software and SOP organization** on GitHub, and the CHoRUS **clinical dataset** itself.

The chosen referent is **the CHoRUS clinical dataset** — the multi-modal, controlled-access, multi-hospital collection of patient-admission records described under "CHoRUS Dataset" in the webinar deck and "Snapshot of the dataset" on the project website. This choice is held identically in both records.

Consequences of that choice, applied consistently:

- The **MIT License** in the bundle governs CHoRUS GitHub code, not the dataset. `license` is therefore omitted at dataset level in both records, and the MIT fact is carried only as an external-resource note about the code organization.
- The GitHub task-tracking and site-status projects track **data delivery**, not dataset use. They are not eligible for `use_repository`, which stays omitted.
- The NIH award is recorded under `funders`, not as the dataset itself.

**Identifier collision, retained and disclosed.** Both records use `https://chorus4ai.org/` as `id` and the same URI as `page`. The bundle supplies no dataset DOI, accession, or persistent identifier. Rather than mint one, the project homepage is used as the referent anchor; the collision with `page` is an acknowledged compromise, not an assertion that the dataset and the website are the same entity.

---

## 2. What the audit found

Fifty-two findings were returned. No finding identified a **factual** claim unsupported by the bundle. The defect distribution was:

| Class of defect | Count | Character |
|---|---|---|
| Structural under-fill (v3): declared class fields empty, substance in `notes` | 14 | Dominant failure mode |
| Entity collapse / non-entity in a multivalued slot (v2) | 5 | |
| Over-assertion beyond the evidence | 3 | `known_biases` enum, `variables`, dataset-level `conforms_to` |
| Source commentary embedded in identifier-bearing values | 4 | |
| Inter-record structural inconsistency | 6 | Full structures it, core prosifies it |
| Verified non-defects (correct omissions confirmed) | 20 | |

Three positive findings were recorded and are preserved unchanged: the 45K-vs-50,000 release-size disagreement is surfaced rather than silently resolved; the "OMOP schema with extensions" table-layout ambiguity is disclosed as unresolvable from the bundle; and three tempting adjacent facts were correctly kept out of dataset slots (MIT as dataset license, HIPAA from a curriculum slide, English from a trainee eligibility rule).

---

## 3. Changes to the full record

### 3.1 Non-entities and entity collapse

**`creators` — removed one entry, restructured six.**
The seventh entry ("The CHoRUS consortium comprises 60+ members across 20 different institutions") is a consortium headcount, not a creating entity. It was deleted from `creators` and the fact relocated to dataset-level `notes`.

The six named individuals (Rosenthal, Bihorac, Jiang, Strekalova, Rashidi, Kwong) are retained as one object each. `Creator` declares no name field, so identity necessarily remains in `notes`; each `notes` value was trimmed to identity and role only. Award-number and leadership-team commentary was moved out. `affiliations` is now populated per creator from the webinar leadership slide (Massachusetts General Hospital; University of Florida ×3; UTHealth Houston; Tufts University). `principal_investigator: true` is set on Rosenthal from the NIH RePORTER record.

**`machine_annotation_tools` — one object split into four.**
OHNLP toolkit, CTP-deid, privacy_scan_tool, and DeGauss (via UF-Geocoding) are separately sourced tools. Each now occupies its own object with `tools` and `tool_descriptions`. `tool_accuracy` remains empty on all four: the bundle reports no accuracy figures.

**`funders` — two grant strings collapsed to one award.**
`1OT2OD032701-01` and `OT2OD032701` identify the same NIH award (project number and core project number). `grants` now carries `OT2OD032701` alone; the fiscal-year-2022 project number and award amount are recorded in the funder `notes`. The NIH views disclaimer was moved from funder `notes` to dataset-level `notes`, where it belongs as source commentary rather than a funding fact.

### 3.2 Over-assertion

**`variables` — slot removed entirely.**
The sole `VariableMetadata` object described "geographic distance to the nearest hospital." The bundle mentions this only in the NIH abstract as an illustrative contextual factor the project *intends* data elements to feature. It is not documented as a named variable in the dataset. Populating `variables` from an aspirational example overstates the evidence. Removal also restores parity with the core record, which never carried it.

**`known_biases` — `bias_type` enum dropped.**
The bundle states that patient-focused efforts will *manage* privacy and bias and that federated sampling will *ensure* a balanced cohort. That is mitigation intent, not a reported finding of representation bias in the assembled data. `bias_type: representation_bias` asserted more than the prose beneath it. The `DatasetBias` object is retained with `bias_description` and `mitigation_strategy` only; `bias_type` is not a required key.

**`conforms_to` — removed at dataset level.**
Only five of nine modalities are standardised to OMOP; the remainder conform to OHNLP, DICOM, WFDB/PhysioNet-extended, and EDF+/Persyst. A single dataset-level assertion of OMOP over-generalises. The per-collection `conforms_to` values, which are correct and modality-specific, are retained.

### 3.3 Structural under-fill — declared fields now populated

| Slot | Declared field populated | Value source |
|---|---|---|
| `instances` | `counts` | 50,000 released patient admissions (project website); the 45K webinar figure retained in `notes` as a disclosed discrepancy |
| `acquisition_methods` | `was_directly_observed: true` | Clinical data recorded in hospital source systems during care |
| `sampling_strategies` | `is_sample: true` | Federated sampling to a balanced cohort from a larger patient population |
| `distribution_dates` | `release_dates` | `2025-08` — the "As of August 2025" availability anchor |
| `external_resources` | `external_resources` (URLs) | chorus4ai.org, github.com/chorus-ai, the AIM-AHEAD webinar PDF, reporter.nih.gov project page, www.bridge2ai.org/chorus |
| `labeling_strategies` | `data_annotation_platform`, `data_annotation_protocol` | The visualization and annotation environment; the clinical validation SOP in `chorus-mapping` |
| `is_deidentified` | `identifiable_elements_present: true` | De-identification in process; clinical notes held locally |
| `file_collections` | `regulatory_restrictions.confidentiality_level: restricted` per collection | The per-modality "Controlled" access-control column in the webinar table |

**`file_collections` — dataset-level aggregate removed.**
The waveform-telemetry collection's note repeated "23 Tb of waveform data," a dataset-level aggregate already recorded under `instances`. It was deleted from the collection. Per-modality metadata-status facts ("Yes" / "Planned") remain in each collection's `notes`: `FileCollection` declares no field that carries metadata-publication status, and the schema digest directs such content to `notes` rather than to invented keys.

`collection_type` remains unpopulated on all nine collections. The declared enum (`raw_data`, `processed_data`, `training_split`, `test_split`, `validation_split`, `documentation`, `metadata`, `code`, `supplementary`, `other`) does not describe modality partitions; forcing every collection to `other` would add shape without meaning. `file_count`, `total_bytes`, and `path` stay empty — the bundle gives none of them per modality.

### 3.4 Field-routing corrections

**`distribution_formats` — one entry removed.**
The sixth object described the Collaborative Cloud enclave and Azure container deployment. That is an access route, not a distribution format. It was deleted here and the substance folded into `third_party_sharing`, which already describes the enclave-mediated access process. `access_urls` remains empty across the five surviving format objects: the bundle supplies no per-format URL.

**`distribution_dates` — scope narrowed.**
The NIH project end date (2026-11-30) is an award period boundary, not a distribution date, and was removed. Metadata-publication status moved to `file_collections`. The object now carries `release_dates` plus a short `notes` on the released-versus-anticipated distinction.

**`license_and_use_terms.contact_person` — split by role.**
The bundle designates `dbold@emory.edu` and `jared.houghtaling@tuftsmedicine.org` under "Request access." Those two are retained in `contact_person`. Ciera McCrary (MGH Program Manager) is a general project contact and was moved to `maintainers`. The editorial parenthetical "(as printed on the project website)" was stripped from the value; the observation that the website prints `cmccrary@mgh.havard.edu` with an apparent typo is now a sentence in dataset-level `notes`.

**`maintainers` — one entry removed, two deduplicated.**
The third entry pointed at the CHoRUS package status page for "versions, maintainers and other metadata." A pointer to where maintainer information lives is not an answer to who maintains; per the v2 rule it was omitted rather than retained as a placeholder. The remaining two entries no longer repeat the contact-typo commentary.

**`status` — verbatim banner moved out.**
`status` now reads `under review for potential modification` without the typo-bearing quotation. The full banner text, including the source's "repoitory" spelling, is preserved verbatim in dataset-level `notes` as source commentary.

**`ethical_reviews` — `reviewing_organization` removed.**
"CHoRUS Ethics pillar (Ethical and Trustworthy AI)" is a project work package, not a reviewing body. Recording it in `reviewing_organization` risked reading as institutional oversight the bundle does not evidence. The object is retained with `review_details` describing the community-facing ethics focus groups and the legal/regulatory analysis, which the bundle does document. `contact_person` remains empty — no ethics contact is named.

---

## 4. Changes to the core record

All changes in §3 that touch slots the core schema declares were applied identically: the consortium-headcount `creators` entry removed; the enclave entry removed from `distribution_formats`; `release_dates` populated on `distribution_dates`; URLs moved into `external_resources.external_resources`; the four annotation tools separated; the one award de-duplicated in `funders`; `bias_type` dropped from `known_biases`; dataset-level `conforms_to` removed; the contact-typo and website-banner commentary moved from `contact_person` and `status` into `notes`; the pointer-only maintainer removed; `instances.counts` populated; `reviewing_organization` removed from `ethical_reviews`.

### 4.1 Inter-record inconsistencies — resolved by schema check

The audit flagged six slots structured in the full record but reduced to prose in the core record's `notes` block, and could not resolve them from the digest supplied. `data_sheets_schema_core_all.yaml` was checked directly:

| Slot | Declared on `CoreDataset`? | Resolution |
|---|---|---|
| `splits` | Yes | **Promoted.** The holdout test set now occupies a `Splits` object in the core record; the corresponding sentence was deleted from `notes`. |
| `third_party_sharing` | Yes | **Promoted.** `is_shared: true` with the enclave access process; the fragment appended to `license_and_use_terms.notes` was removed. |
| `direct_collection` | No | **Left in `notes`.** The full/core difference is a schema difference, not an inconsistency. |
| `relationships` | No | **Left in `instances.notes`.** Same reason; the 7,642 radiology-admission linkage figure stays there. |
| `variables` | Yes | **No action.** Removed from the full record instead (§3.2); both records now omit it. |
| `conforms_to` | Yes | **Removed from both** (§3.2). |

### 4.2 The core `notes` block

After promoting `splits` and `third_party_sharing`, the core `notes` field retains: the per-modality standards/access/metadata table content (no core slot carries it), the direct-collection fact, the 45K-vs-50,000 discrepancy, the OMOP-extensions ambiguity, the consortium headcount, the website banner, the contact-typo observation, and the NIH views disclaimer. This is content correctly routed to `notes` per the schema digest guidance, not prose collapse.

---

## 5. What was left as-is, and why

### 5.1 Correct omissions, confirmed and retained

| Slot(s) | Why omitted |
|---|---|
| `citation`, `doi`, `version`, `issued`, `download_url` | No dataset DOI, version identifier, formal citation, or direct download URL in the bundle; access is enclave-mediated. |
| `total_file_count`, `total_size_bytes` | "23 Tb waveform data" and "1.6 billion rows" are neither a total file count nor a total byte count across all collections. |
| `collection_consents`, `collection_notifications`, `consent_revocations`, `informed_consent` | The bundle describes community ethics focus groups and a legal framework for collection at scale, but says nothing about patient consent, notification, or revocation for this retrospective dataset. This is an evidence gap in the bundle, not a generation gap. |
| `anomalies`, `errata`, `missing_data_documentation`, `imputation_protocols` | No anomalies, errata, missing-data patterns, or imputation reported. |
| `discouraged_uses`, `prohibited_uses` | Access restrictions exist; no discouraged or prohibited use is stated. |
| `retention_limit`, `version_access` | Bundle silent on retention periods and version history. |
| `use_repository` | GitHub projects track data delivery, not dataset use (§1). |
| `other_tasks` | Trainee use-case development is already carried by `intended_uses` "Training and education"; a duplicate entry adds nothing. |
| `language` | "Working command of English" is a trainee eligibility rule, not a statement about the dataset's language of expression. |
| `human_subject_research.irb_approval`, `.ethics_review_board`, `.regulatory_compliance` | Bundle silent on all three; only `involves_human_subjects: true` is supported. |
| `subpopulations.distribution` | The 50,000 figure is aggregate across ICU/PICU/NICU with no breakdown. |
| `updates.frequency` | Sites give "regular status updates," but no dataset release cadence is stated. |
| `regulatory_restrictions.hipaa_compliant` | HIPAA appears only as an AI-LEARN curriculum topic. That is not a statement about this dataset's compliance status. |
| `license` (dataset level) | MIT governs the code, not the data (§1). |

### 5.2 Judgment calls retained, flagged here

**`license_and_use_terms.data_use_permission` — left unpopulated.**
Access is gated by a signed licensing agreement and a `.edu` institutional email. This is close to `institution_specific`, and arguably touches `ethics_approval_required`. The bundle does not state which permission regime applies, and selecting an enum value would convert a gating mechanism into a declared use-permission category. Omission preferred.

**`regulatory_restrictions.confidentiality_level: restricted` — retained.**
Every modality is marked "Controlled access." That maps plausibly to `restricted`; `confidential` is also defensible. `restricted` was kept as the weaker of the two claims. Recorded here as a judgment call rather than a direct bundle statement.

**`at_risk_populations` — retained with protection fields empty.**
`at_risk_groups_included` lists PICU and NICU patients and critically ill patients, supported by the released-dataset care settings. `special_protections`, `assent_procedures`, and `guardian_consent` are empty because the bundle evidences none. The object asserts group inclusion without protection detail; that is what the evidence supports.

**`acquisition_methods` — three of four booleans left empty.**
`was_directly_observed: true` was added (clinical recording in source systems). `was_inferred_derived`, `was_reported_by_subjects`, and `was_validated_verified` remain empty. Setting `was_reported_by_subjects: false` would be a safe inference from retrospective EHR extraction, but it is an inference, not a bundle statement.

**`sampling_strategies.is_representative` — left empty.**
"Balanced and diverse cohort" is a design aim, not a representativeness finding. `why_not_representative` and `representative_verification` likewise stay empty.

**`existing_uses` — both entries retained.**
The first carries only a `notes` assertion that datasets are in use for training activities and publications, with `examples` empty. It is thinly evidenced but directly stated in the bundle, and removing it would discard a supported fact.

**`intended_uses.use_category` free-text values retained.**
The schema declares no enum for `use_category`. "Model development," "External model validation," "Training and education," and "Innovative data-driven research" are permissible free text and were confirmed not to introduce undefined enum values.

**`id` / `page` collision retained.** See §1.

### 5.3 Disagreements preserved, not resolved

Per the uniform decision rules, where bundle sources disagree the records represent what the evidence states:

- **Released dataset size.** The webinar (September 2025) states "as of August 2025 … over 45K unique admissions"; the project website states "50,000 patient admissions from ICU, PICU, and NICU." `instances.counts` carries 50,000 as the project's own published release figure; `notes` in both records records the 45K webinar figure and the discrepancy explicitly. Neither figure was silently selected.
- **Contributing-hospital count.** Both sources say 14; the GitHub overview adds that 14 of 20 academic centers contribute data. Consistent, no conflict.
- **OMOP schema extensions.** The webinar table marks nursing flowsheets as "OMOP schema with extensions" without specifying the extension tables. Recorded as an unresolvable ambiguity in `notes`.
- **Released vs. anticipated figures.** 50,000 released against 100,000 anticipated admissions; both are carried, labelled by status, and not merged.

---

## 6. Post-reconciliation state

| | Full (`Dataset`) | Core (`CoreDataset`) |
|---|---|---|
| Populated slots before Phase 4 | 53 | 31 |
| Removed | `variables`, `conforms_to` | `conforms_to` |
| Added | — | `splits`, `third_party_sharing` |
| **Populated slots after Phase 4** | **51** | **32** |
| Objects removed from multivalued slots | 3 (1 creator, 1 distribution_format, 1 maintainer) | 2 (1 creator, 1 distribution_format) |
| Objects split | 1 → 4 (`machine_annotation_tools`) | 1 → 4 (`machine_annotation_tools`) |

**Consistency after reconciliation.** Every slot present in one record and absent from the other now traces to a schema difference between `Dataset` and `CoreDataset`, not to a difference in how the same evidence was read. The referent, the identifier, the release-size disagreement handling, the omission set, and every judgment call in §5.2 are identical across the two files.

**Validation.**

```
poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_all.yaml \
  -C Dataset data/d4d_concatenated/claudecode_agent/2026-08-06_claude-opus-5-1m-generic-v3-schema2_rep2/CHORUS_d4d.yaml
→ PASS

poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml \
  -C CoreDataset data/d4d_concatenated/claudecode_agent_core/2026-08-06_claude-opus-5-1m-generic-v3-schema2_rep2/CHORUS_d4d_core.yaml
→ PASS
```

**Provenance.** No previously generated D4D record was read, opened, grepped, or consulted in any phase. Factual inputs were the declared bundle and the two schema files only.

---

## 7. Residual evidence gaps

These are properties of the bundle, not of the records, and are listed so that a reader does not mistake omission for oversight:

1. No patient consent, notification, or revocation documentation for a retrospective human-subjects clinical dataset.
2. No IRB number, ethics committee, or named reviewing body — only a project ethics work package.
3. No persistent dataset identifier, version string, or recommended citation.
4. No per-modality file counts, byte totals, or paths; the only size figures are a waveform aggregate (23 Tb) and a row count (1.6 billion).
5. No de-identification method detail beyond "in process" for imaging and local-only storage for clinical notes; no enumeration of identifiers removed.
6. No inter-annotator agreement, annotation counts, or annotator demographics for the labeling work.
7. No reported data anomalies, errata, or missing-data characterisation.
8. No stated retention period or version-history access route.