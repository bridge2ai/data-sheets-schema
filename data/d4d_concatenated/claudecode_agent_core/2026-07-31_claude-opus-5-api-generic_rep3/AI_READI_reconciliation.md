# Reconciliation Report — AI_READI

**Version label:** `2026-07-31_claude-opus-5-api-generic_rep3`
**Arm:** BASELINE (input documents only)
**Declared input bundle:** `data/preprocessed/concatenated/AI_READI_preprocessed.txt`
**Referent:** Flagship Dataset of Type 2 Diabetes from the AI-READI Project, **version 3.0.0** (DOI `10.60775/fairhub.3`)

---

## 1. Referent selection

The declared bundle describes a single dataset across three released versions (v1.0.0, v2.0.0, v3.0.0) plus a distinct "Mini Version" (FAIRhub record 4). The `Dataset` class admits one referent.

**Chosen referent: v3.0.0.** Rationale drawn from the bundle itself:

- The FAIRhub v2.0.0 page states verbatim: *"This version of the dataset is no longer accessible. Please refer to the latest version."*
- The v2 documentation page carries the banner *"This documentation is for v2.0.0 of the dataset, which is no longer accessible."*
- The curation notes on both v3 sources instruct: *"prefer this over `fairhub_dataset` / `dataset_documentation` where the two disagree."*
- The FAIRhub API record (`fairhub_dataset_v3_api`) is the only substantive structured metadata in the bundle and describes v3.0.0 exclusively.

This choice is held consistently across both records. Where v2.0.0 figures appear (2.01 TB, 165,051 files, 1,067 participants), they are labelled as such and presented as superseded prior-version context, not as properties of the referent.

---

## 2. Changes made

### 2.1 Full record — `license_and_use_terms` (HIGH severity; corrected)

The audit found two `description` keys at the same level within the `license_and_use_terms` mapping. Duplicate keys in a YAML mapping are lossy: the parser retains only the last occurrence, silently discarding the substantive license text in favour of a placeholder note reading *"Duplicate key guard note: see the single description above."*

**Action:** collapsed to a single `description` key retaining the substantive license content. The placeholder note was removed entirely, as it described a condition that no longer exists.

This was the only defect requiring correction. No factual content was altered — the surviving text is the text that was intended to survive.

### 2.2 No other changes

All remaining audit findings were assessed and deliberately left as-is. Rationale below.

---

## 3. Left as-is, with reasoning

### 3.1 Structural omissions that the bundle arguably supports

**`related_datasets` / `resources` — the Mini Version (DOI `10.60775/fairhub.4`).**
The FAIRhub API record carries `data.child: 4`, an explicit parent/child link, and the v3 FAIRhub page notes *"A smaller version is available for pipeline development."* This is real evidence of a relationship. However, the bundle's own curation note states plainly that FAIRhub record 4 *"is a distinct 'Mini Version' (100 participants, DOI 10.60775/fairhub.4) for pipeline development, **not a version of this dataset**, and was not captured."* The bundle therefore contains both the link and an explicit instruction about how to read it. The Mini Version is described in prose under `external_resources` and `version_access` in both records, so the fact is present; expressing it as a typed `DatasetRelationship` would assert a relationship semantics the curation note disclaims. **Left unpopulated; the prose treatment stands.**

**`was_derived_from` — version lineage.**
v3.0.0 contains the v1.0.0 and v2.0.0 participants plus new enrolment (204 → 1,067 → 2,280). This is a genuine lineage. It is fully described under `version_access` and `updates`, including all three DOIs and release dates. The slot expects a single string identifying a source resource; the honest answer is a three-element chain that the prose already renders more accurately than the slot could. **Left unpopulated as a structural rather than factual gap.**

### 3.2 Blank healthsheet answers

Three healthsheet questions were submitted blank (empty string) in the v3 healthsheet: the erratum question, and two de-identification questions. A blank is an *unanswered* question, not a negative answer.

- The de-identification blanks are noted explicitly inside `is_deidentified`.
- The erratum blank is not noted anywhere, and `errata` is unpopulated.

Populating `errata` would require asserting either that errata exist (unsupported) or that none exist (also unsupported — the question was not answered). Omission is the correct representation of an unanswered question. **Left as-is.** The asymmetry with `is_deidentified` is noted here rather than papered over.

### 3.3 Arithmetic residues (verified, not errors)

Two totals were cross-checked against their components:

| Field | Declared (FAIRhub API) | Sum of `file_collections` | Residue |
|---|---|---|---|
| `total_file_count` | 356,343 | 356,334 | 9 |
| `total_size_bytes` | 3,815,969,779,678 | 3,815,824,059,254 | 145,720,424 (~0.004%) |

The nine-file residue corresponds exactly to the nine root-level metadata files enumerated in the API's `metadataFileList` (CHANGELOG.md, dataset_description.json, dataset_structure_description.json, healthsheet.md, LICENSE.txt, participants.json, participants.tsv, README.md, study_description.json). The byte residue is plausibly the same files, which the directory listing does not size. Both declared totals are taken verbatim from the source. **Internally coherent; no change.**

### 3.4 Conflicts surfaced rather than resolved

The bundle contains six genuine internal conflicts. Per the uniform decision rules, each is represented as disagreement rather than silently resolved:

| Conflict | Sources | Where surfaced |
|---|---|---|
| Managing organization: Washington University in St. Louis vs University of Washington | FAIRhub API (`managingOrganization`, `leadSponsor`, all PI affiliations) vs NIH RePORTER, license agreement, IRB protocol, publications | `creators` (annotation entry) |
| Collection start: 18 July 2023 vs 2023-07-19 | BMJ Open protocol vs FAIRhub API / README | `collection_timeframes` |
| Follow-up cohort: ~4% vs 10% | healthsheet vs NIH abstract, README, IRB protocol | `collection_timeframes`, `relationships` |
| STUDY00016228 as "Clinicaltrials.org approval number" vs UW IRB number | BMJ Open abstract vs BMJ Open Methods (same paper) | `ethical_reviews` |
| "Does the dataset identify demographic sub-populations?" answered **No** vs README split table giving per-group counts | healthsheet vs README | `subpopulations` |
| v2.0.0 accessible vs no longer accessible | v2 sources vs v3 sources and curation notes | `version_access` |

The README split table was verified internally consistent: race/ethnicity totals (380 + 545 + 519 + 836) = 2,280 and sex totals (951 + 1,329) = 2,280, both matching the declared participant count.

### 3.5 License version caveat

All four `prohibited_uses` entries derive from **AI-READI Data License Agreement v1.0** (Zenodo `10.5281/zenodo.10642459`), the only license text present in the bundle. The referent v3.0.0 is governed by **custom license v2.0** (`10.5281/zenodo.17555036`), whose text is *not* in the bundle — only its DOI and a one-sentence characterisation.

The caveat is stated explicitly in the final `prohibited_uses` entry and in `license_and_use_terms`. The audit notes it appears only on the last of four entries. Relocating or duplicating it was considered and rejected: repeating the caveat on each entry would add no information, and the entries are read as a list. **Left as-is**, with the placement recorded here so the limitation is discoverable outside the record.

### 3.6 Slot-semantics stretches (no unsupported facts)

Several entries use a slot's range to carry content adjacent to its stated purpose:

- `creators` entries 4 and 5 are a provenance annotation (institutional conflict) and a list of collaborating organizations, not creators.
- Core `data_collectors` entry 3 appends participant compensation to a who-collected-the-data slot, duplicating a fact also in `human_subject_research`. This mirrors the bundle, where a single healthsheet question answers both.

In each case the content is bundle-supported and no fact is invented. The alternative — dropping the institutional conflict, or forcing it into a slot with no annotation semantics — would lose information or assert a resolution the evidence does not support. **Left as-is.**

### 3.7 Correctly-empty slots (confirmed, no action)

- `imputation_protocols` — no imputation documented. Absence explicitly noted inside `missing_data_documentation`.
- `compression` — formats named (DICOM, CSV, JSON, Markdown, TSV) but no compression scheme.
- `created_on` / `last_updated_on` — `created_at: 1763366400` (2025-11-17) captured as `issued`. The docs pages' "Last updated on Jun 4, 2026" is the documentation page's edit date, not the dataset's.

### 3.8 Synthetic identifiers

Nine `file_collections` ids and five `subsets` ids are minted as fragment URIs on the dataset DOI (e.g. `#cardiac_ecg`). The bundle supplies directory names but no per-directory identifiers, and `id` is required on both ranges. The scheme is consistent and collision-free. **Retained.**

---

## 4. Full ↔ core consistency

The core schema lacks structured ranges for `file_collections`, `splits`, `subsets`, `collection_notifications`, `consent_revocations`, `participant_compensation`, and `participant_privacy`. These were consolidated into surviving core slots:

| Full record slot(s) | Core record destination |
|---|---|
| `file_collections` (9 entries) | `distributions` (9 per-directory + 1 whole-dataset summary, prose) |
| `is_deidentified` + `participant_privacy` | `is_deidentified` |
| `human_subject_research` + `participant_compensation` | `human_subject_research` |
| `collection_consents` + `collection_notifications` + `consent_revocations` + `informed_consent` | `informed_consent` (5 entries) |
| `at_risk_populations` (2 entries) | `at_risk_populations` (1 object) |

Exact file counts and byte sizes are preserved in the core prose rendering. No claim in the core record diverges from or contradicts the full record. Two minor losses in consolidation are noted: the core `human_subject_research` text drops the details that compensation is not prorated and is disbursed ~2 weeks post-visit on device return (both retained in the full record), and the compensation fact appears twice in the core record (`human_subject_research` and `data_collectors`).

Referent, institutional conflict handling, and the v1.0/v2.0 license caveat are identical across both files.

---

## 5. Outcome

| | |
|---|---|
| Full record slots populated | 74 |
| Core record slots populated | 38 |
| Full record validates (`Dataset`) | Yes |
| Core record validates (`CoreDataset`) | Yes |
| Defects corrected | 1 (duplicate `description` key in `license_and_use_terms`) |
| Findings reviewed and left as-is | 27 |
| Prior D4D records consulted | None |

**Reconciliation outcome: PASS with one correction.** The duplicate-key defect was a genuine validity problem and is fixed. All other findings were assessed as either correct-as-written, defensible-with-stated-reasoning, or structural gaps whose factual content is already carried in prose. No facts were added, removed, or altered during reconciliation beyond recovering the license text that the duplicate key would have discarded.