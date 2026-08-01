# Reconciliation Report — AI_READI

**Version label:** `2026-07-31_claude-opus-5-api-generic_rep2`
**Arm:** HEALTHSHEET-ONLY (single structured upstream source)
**Declared input bundle:** `data/preprocessed/concatenated/AI_READI_healthsheet_only.txt`
**Records reconciled:**
- Full — `data/d4d_concatenated/claudecode_agent_healthsheet/2026-07-31_claude-opus-5-api-generic_rep2/AI_READI_d4d.yaml`
- Core — `data/d4d_concatenated/claudecode_agent_healthsheet_core/2026-07-31_claude-opus-5-api-generic_rep2/AI_READI_d4d_core.yaml`

---

## 1. Dataset referent

Both records resolve to a single referent, held consistently:

> **Flagship Dataset of Type 2 Diabetes from the AI-READI Project**, version 3, DOI `10.60775/fairhub.3`, distributed November 2025, comprising data from 2280 participants collected 2023-07-19 through 2025-05-01 across three sites (UAB, UCSD, UW).

Versions 1 (204 participants) and 2 (1067 participants) are treated as *related prior versions*, not as the referent. The bundle's own healthsheet declares itself "created for the third version of the dataset," which fixes the choice unambiguously.

---

## 2. Audit outcome

**16 findings: 0 high, 2 medium, 14 low.** No provenance-guard violation was detected.

Specifically confirmed clean:

- Every factual claim in both records traces to the declared bundle.
- The three unanswered healthsheet questions (de-identification pre-processing; measures against re-identification; erratum) are represented as explicit non-answers, not filled in.
- The bundle's internal grant-number discrepancy (`OT2ODO32644` in Motivation vs. `OT2OD032644` in Collection) is surfaced in `funders` rather than silently normalized.
- No content appears that could only originate from a prior D4D record, a publication, the license text, or the IRB protocol document.

---

## 3. Changes made

### 3.1 Medium — internal bundle disagreement was silently smoothed (`sampling_strategies`, both records)

**Found.** The Composition section states the dataset "contains data from all participants who have been enrolled during the **first year** of data collection for AI-READI." The Versioning and Collection sections state that this version covers **July 19, 2023 – May 1, 2025**, i.e. through the end of the second year. Both records had reconciled this to a neutral phrase ("all participants enrolled during the covered data collection period").

**Changed.** The `sampling_strategies` entry now reports both statements as the bundle makes them, attributed to their sections, and notes the conflict without adjudicating it. The uniform decision rules require disagreeing evidence to be represented rather than resolved; the previous phrasing chose a reading the bundle does not itself commit to.

### 3.2 Medium — misassigned slot in the core record (`at_risk_populations`)

**Found.** The core record's `at_risk_populations` carried participant compensation ($200 per study visit), rideshare transportation assistance, the internal PII-exclusion review, controlled-access handling of race/ethnicity/ZIP, and the theoretical re-identification risk. All are bundle-supported, but none describe safeguards or assent procedures for at-risk populations. The full record already carries them correctly under `participant_compensation` and `participant_privacy`.

**Changed.** `at_risk_populations` in the core record is now restricted to the one at-risk-population fact the bundle actually supplies: the exclusion of pregnant persons and persons with gestational diabetes from eligibility. The compensation and privacy content was relocated to the core slots whose semantics cover it, matching the full record's placement.

### 3.3 Low — inferred `publisher` (both records)

**Found.** `publisher: https://fairhub.io/`. The bundle says only that the dataset is *hosted and distributed through* the FAIRhub platform on Microsoft Azure and that the AI-READI team maintains it. No publishing entity is named.

**Changed.** `publisher` removed from both records. Hosting and maintenance remain recorded under `maintainers` and `distribution_formats`, where the bundle's actual statements belong. Omission is the correct answer when the evidence is absent.

### 3.4 Low — `page` pointed at the project site, not the dataset (both records)

**Found.** `page: https://aireadi.org`, which the bundle introduces as the *project* website (team roster, consortium membership). The bundle designates the dataset access point as the FAIRhub platform.

**Changed.** `page` reset to `http://fairhub.io/`, the URL the bundle gives for dataset availability. `https://aireadi.org` and `https://docs.aireadi.org` are retained in `external_resources`, labelled as project website and dataset documentation respectively.

### 3.5 Low — mitigation statement stored as a bias (`known_biases`, both records)

**Found.** The sixth `known_biases` entry recorded that "uniform data collection protocols were implemented for all subjects... intended to ensure equitable representation and minimize the potential for sampling bias." That is a mitigation, not a bias present in the data.

**Changed.** The statement was moved onto the mitigation field of the site-selection / representativeness bias entry it addresses, and the standalone sixth entry was removed. Text is unchanged; only placement is.

### 3.6 Low — `subpopulations` used to assert an absence (both records)

**Found.** The first `subpopulations` entry recorded the healthsheet's bare "No" to the demographic-sub-population question.

**Changed.** Rewritten so the entry documents what the bundle positively states — that sex, race, and ethnicity are collected and held under controlled access, are not released with the public dataset, and that recruitment targets approximately equal distribution across sex, race, and diabetes severity with balance not yet achieved as enrollment continues. The negative answer is preserved as context inside that entry rather than standing as a null subpopulation object.

### 3.7 Low — supported facts absent from both records

Three bundle-supported facts had no slot representation. All three were added:

| Slot | Added content |
|---|---|
| `content_warnings` | Explicit negative finding: the healthsheet answers "No" to whether the dataset contains material that, viewed directly, might be offensive, insulting, threatening, or pose a safety risk. |
| `related_datasets` | Typed relationships to version 1 (204 participants, pilot phase, healthsheet at `docs.aireadi.org/docs/1/dataset/healthsheet`) and version 2 (1067 participants, first study year, `.../docs/2/...`). Added to the full record; the core record retains these as prose under `version_access`. |
| `imputation_protocols` | Record-level fill-in of "missing data that can be directly filed from other portions of an individual's record," performed under site-PI approval. Added to the full record and cross-referenced from `cleaning_strategies`, which previously held it alone. |

### 3.8 Low — `is_tabular` removed (both records)

**Found.** `is_tabular: false`. The bundle states the dataset "encompass[es] tabular data, imaging data, and physiological signal/waveform data." A single boolean cannot represent that mixture, and the bundle makes no overall tabularity claim.

**Changed.** `is_tabular` removed. The modality breakdown remains in `instances` and `distribution_formats`.

### 3.9 Low — "excluding minors" interpolation (both records)

**Found.** `at_risk_populations` described the eligibility rule as "excluding minors." The bundle states an inclusion criterion of age ≥ 40 and never frames it as minor exclusion or as an at-risk safeguard.

**Changed.** Replaced with the bundle's literal criterion (≥ 40 years old), stated as an eligibility criterion rather than a protective measure.

---

## 4. Left as-is, with reasons

### 4.1 IRB protocol identifier `STUDY00016228` (`human_subject_research`)

**Retained, qualified.** The identifier is read off a linked filename (`Approval_STUDY00016228_Lee_initial.pdf`) rather than from bundle prose. Removing it would discard information the bundle does carry; asserting it flatly would overstate the prose. The value is retained with its provenance stated inline ("identifier appears in the filename of the linked initial approval letter"). The surrounding facts — University of Washington initial approval 2022-12-20, annual renewal due within 90 days of expiration, reliance agreements at the other two sites — come from prose and stand unqualified.

### 4.2 `issued` left unpopulated

**Unchanged.** The bundle gives "November 2025" and "released fall 2025." Populating a `datetime` slot would require inventing a day. The fact is carried at its native precision in `distribution_dates`, alongside the May 2024 (v1) and November 2024 (v2) release months.

### 4.3 Core-record slot folding (`instances`, `distribution_formats`, `informed_consent`)

**Unchanged.** Three folds were flagged:

- `instances` carries composition, inter-instance relationships (one visit per participant; common project membership), and the recommended 70/15/15 split.
- `distribution_formats` carries third-party sharing policy (public availability; public subset under license vs. full dataset under data use agreement).
- `informed_consent` carries notification and consent-revocation facts.

Each fold is bundle-faithful and is forced by the reduced core slot set; the full record separates all six concerns into `relationships`, `splits`, `third_party_sharing`, `collection_notifications`, and `consent_revocations`. Rather than restructure, explicit lead-in labels were added within each folded entry ("Recommended split:", "Third-party distribution:", "Notification:", "Revocation:") so a reader of the core record alone can tell the concerns apart. No content was moved or dropped.

### 4.4 Grant-number discrepancy

**Unchanged.** `funders` records both `OT2ODO32644` and `OT2OD032644` as they appear, attributed to the Motivation and Collection sections respectively, with the NIH Bridge2AI program and the RePORTER project link. Selecting one would be adjudication the bundle does not authorize.

### 4.5 Unanswered healthsheet questions

**Unchanged.** De-identification pre-processing, measures against re-identification, and the existence of an erratum are recorded as "not answered in the source healthsheet" in `is_deidentified` and `errata`. This preserves the input's own coverage gap, which the bundle header explicitly flags as intentional signal.

### 4.6 Slots deliberately left empty

`annotation_analyses`, `labeling_strategies`, `machine_annotation_tools`, `variables`, `use_repository`, `existing_uses`, `total_file_count`, `total_size_bytes`, `download_url`, `compression`, `conforms_to_class`, `was_derived_from`, and `extension_mechanism` remain unpopulated. For labeling and annotation the bundle answers "N/A – no labels are provided" across the entire Labeling section; for existing uses and use repositories it answers "No"; for extension it states no mechanism exists. Where the negative is itself informative, it is recorded in narrative form (`known_limitations`, `other_tasks`, `discouraged_uses`); where the slot range would require fabricating an object to express a null, the slot is omitted.

---

## 5. Post-reconciliation state

| | Full | Core |
|---|---|---|
| Populated slots before Phase 4 | 58 | 32 |
| Slots added | 3 (`content_warnings`, `related_datasets`, `imputation_protocols`) | 1 (`content_warnings`) |
| Slots removed | 2 (`publisher`, `is_tabular`) | 2 (`publisher`, `is_tabular`) |
| **Populated slots after Phase 4** | **59** | **31** |
| Entries rewritten in place | 5 | 4 |
| Schema validation | pass | pass |

Cross-record consistency confirmed after changes: identical referent, identical headline figures (2280 participants; 3 sites; 70/15/15 split; DOI `10.60775/fairhub.3`), no contradictory statements, and no fact present in the core record that is absent or differently stated in the full record.

**Reconciliation outcome: resolved.** Two medium findings corrected, ten low findings corrected, four low findings retained with documented rationale.