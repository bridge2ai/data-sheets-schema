# Reconciliation Report — CHORUS

**Version label:** `2026-07-31_claude-opus-5-api-generic_rep2`
**Arm:** BASELINE (input documents only)
**Declared input bundle:** `data/preprocessed/concatenated/CHORUS_preprocessed.txt` (4 source files)
**Records reconciled:**
- Full — `data/d4d_concatenated/claudecode_agent/2026-07-31_claude-opus-5-api-generic_rep2/CHORUS_d4d.yaml`
- Core — `data/d4d_concatenated/claudecode_agent_core/2026-07-31_claude-opus-5-api-generic_rep2/CHORUS_d4d_core.yaml`

---

## 1. Referent decision

`Dataset` admits one referent. The declared bundle describes three closely related things: the CHoRUS **project/consortium** (NIH RePORTER, chorus4ai.org), the CHoRUS **software organization** (GitHub), and the CHoRUS **dataset** itself.

**Chosen referent: the CHoRUS multi-modal critical care dataset** — the controlled-access, OMOP-standardized clinical data resource assembled by the CHoRUS Data Generation Project. This is the referent the bundle best supports: three of four sources describe the dataset directly (the webinar's modality table, the website's dataset snapshot, the NIH abstract's dataset goals), and the GitHub source describes tooling *for* that dataset.

Consequences held consistently across both records:
- The **MIT license** on the GitHub organization is recorded as applying to CHoRUS *software*, not to the dataset. The dataset's own terms are recorded as controlled access under a signed licensing agreement. `license` at the dataset level is left unpopulated.
- The **$8,000 trainee stipend** is a training-program benefit, not compensation to data subjects. `participant_compensation` is left unpopulated in both records.
- GitHub repositories are recorded as tooling context, not as dataset file collections.

---

## 2. Audit findings and dispositions

The Phase 3 audit returned 21 findings (0 high, 7 medium, 14 low). No fabrication was found. The recurring defect class was **low-grade inferential enrichment**: supported facts extended with unstated consequence clauses, entity attributes reconstructed rather than quoted, and repository *existence* treated as evidence of executed pipeline steps.

### 2.1 Changed — unsupported claims removed or narrowed

| Slot | Finding | Change made |
|---|---|---|
| `publisher` | `https://www.bridge2ai.org/chorus` derived from a *contact link*; no source names a publishing entity, and the scheme was added | **Removed** from both records. No entity in the bundle is designated as responsible for making the dataset available. The bridge2ai.org URL is retained verbatim (without added scheme) in `external_resources`. |
| `subpopulations` | "Adult intensive care unit (ICU) admissions" — "adult" inferred by contrast with PICU/NICU | **Narrowed** to "ICU admissions" in both records. The bundle says only "admissions from ICU, PICU, and NICU." |
| `known_biases` | Site-composition bias asserted as a *known* bias of the data; bundle only describes bias as a managed workstream | **Rewritten** in both records. Now states that the sources describe managing privacy and bias and pursuing a balanced, diverse cohort via federated sampling, and that no specific bias present in the released data is identified in the sources. The prior causal claim about cohort reflecting contributing-institution populations was removed. |
| `at_risk_populations` | Decisional-capacity claim appears nowhere in the bundle | **Trimmed** in both records to the supported portion: PICU and NICU admissions indicate minors and neonates are represented. The capacity clause was deleted. |
| `preprocessing_strategies` | DeGauss geocoding linked to an executed step and to SDoH derivation | **Rewritten** in both records to state only what the bundle shows: a forked `UF-Geocoding` repository exists in the chorus-ai organization described as open-source code to geocode OMOP Location entities via DeGauss. The claim that it was applied to this dataset, and the link to distance-to-nearest-hospital, were removed. The NIH abstract's mention of contextual factors is retained separately under `purposes`, where it is a stated goal rather than a completed step. |
| `machine_annotation_tools` | Slot-fit error: privacy scanning, de-identification, and characterization reporting are not annotation | **Reduced** in both records to the OHNLP toolkit (extraction and tokenization of clinical notes), which the webinar table attests directly. `privacy_scan_tool` and `CTP-deid` moved to `is_deidentified` context; `CHoRUSReports` moved to `cleaning_strategies` as a site-return characterization report. Duplicated entries were collapsed rather than left in two places. |
| `existing_uses` | Curriculum sessions claimed as dataset uses | **Trimmed** in both records. Retained: "Datasets are being used for training activities and publications" (verbatim support) and the AIM-AHEAD Bridge2AI for Clinical Care Training Program's stated purpose of expanding access to CHoRUS data. Removed: the enumerated lecture list, which the bundle presents as generic curriculum without stating dataset use. |
| `creators` | "D. Bold (Emory)" reconstructed from `dbold@emory.edu`; also an access contact, not a creator | **Removed** from `creators` in both records. Both access contacts (`dbold@emory.edu`, `jared.houghtaling@tuftsmedicine.org`) are now carried only where the bundle places them — as access-request contacts, under `maintainers`. Named creators retained are those the bundle attributes in a creator/leadership role: the PI and the six named CHoRUS leadership-team members. |
| `other_tasks` | "Exposome-oriented analyses" derived from an upstream fork name | **Narrowed** to geospatial analysis in both records, and even that is qualified as tooling-implied rather than a stated supported task. The word "exposome" was removed. |
| `funders` | "USD" not stated | **Changed** to `award_amount: 5880300` with no currency assertion, matching the source string. |
| `created_by` | "Led from Massachusetts General Hospital" inferred | **Restated** in both records as: principal investigator Eric S. Rosenthal, organization Massachusetts General Hospital (per NIH RePORTER). The leadership claim about the consortium was removed. |
| `cleaning_strategies` | Site status tracking is project management, not data cleaning | **Removed** from `cleaning_strategies` in both records. The content already exists, correctly placed, under `updates`. |
| `known_limitations` | Consequence clauses appended to supported facts | **Trimmed** in both records. Now: "Data collection is retrospective" and "Access is controlled and requires a signed licensing agreement." The inferential clauses about study designs and constrained access populations were deleted. |
| `ethical_reviews` | Slot-fit stretch: describes an ethics research pillar, not review of this dataset | **Rewritten** in both records so the slot carries only the explicit negative finding — the sources describe ethics research, legal-framework development, and community-facing focus groups, but do not describe an IRB determination or ethics-committee review of the dataset. The substantive ethics-pillar content moved to `purposes` and `data_protection_impacts`, where it fits. |
| `description` | Conflated "14 academic centers will contribute" (future tense, GitHub) with "14 data contributing hospitals" (website) | **Amended** in both records to state the 14 figure and note the source difference: the GitHub overview describes 14 of 20 academic centers as future Data Acquisition contributors, while the website and the August 2025 webinar report 14 contributing hospitals. This now matches the treatment already given to the admissions-count discrepancy. |

### 2.2 Changed — cross-record structural consistency

| Slot | Finding | Change made |
|---|---|---|
| `subsets` / `resources` | Nine modality partitions plus holdout carried as `subsets` in full but `resources` in core, with identical ids | **Resolved and documented.** `CoreDataset` does not expose `subsets`; it exposes `resources` (range `Dataset`). The remap is therefore schema-forced, not a modeling drift. Ids and descriptions are held identical across both records so the partitions are traceable one-to-one. Recorded here as a deliberate reconciliation decision. |

### 2.3 Left as-is — with reasons

| Slot | Finding | Why unchanged |
|---|---|---|
| `is_tabular: false` | Judgment call the bundle does not settle | Retained. The referent is explicitly multi-modal across nine modalities (waveform, imaging, EDF+/Persyst EEG, DICOM, tokenized text). The OMOP component is tabular, but the dataset as a whole is not, and a single boolean must characterize the whole. The `subsets` entries carry per-modality format detail, so no information is lost by the coarse boolean. |
| `splits` (absent in core) | Present in full, absent in core | Confirmed as a **core-schema absence**: `CoreDataset` does not define `splits`. The sequestered holdout partition is preserved in core via the corresponding `resources` entry. No fact dropped. |
| `direct_collection` (absent in core) | Present in full, absent in core | Confirmed as a **core-schema absence**. The fact — data obtained retrospectively from hospital systems rather than directly from individuals — is well supported and is preserved in core within `acquisition_methods`. |
| `participant_privacy` (absent in core) | Present in full, absent in core | Confirmed as a **core-schema absence**. The underlying facts (tokenization, clinical notes stored locally, controlled access, de-identification in process for imaging) are preserved in core under `is_deidentified` and `sensitive_elements`. |
| `third_party_sharing` (absent in core) | Present in full, absent in core | Confirmed as a **core-schema absence**. The controlled-access model, training-program access expansion, holdout-for-external-validation purpose, and Bridge2AI collaboration are preserved in core under `license_and_use_terms`, `purposes`, and `related_datasets`. |

---

## 3. Discrepancies deliberately preserved, not merged

The bundle contains sources that disagree. Per the uniform decision rules, these are represented rather than resolved:

1. **Admission count.** The September 2025 webinar states "as of August 2025, covers 14 different hospitals with over 45K unique admissions." The project website reports a Current Released Dataset of 50,000 patient admissions and an Anticipated Final Dataset of 100,000. All three figures are carried in `instances` with their sources and dates attached. No single number is presented as the count.
2. **Contributing-site framing.** GitHub: 20 academic centers, 14 of which *will* contribute (future tense). Website: 14 data contributing hospitals, 60+ consortium members across 20 institutions. Webinar: 14 different hospitals. Both framings are recorded in `description` and `data_collectors`.
3. **Imaging availability.** The webinar (Aug 2025) reports 1,000 images available with de-identification in process; the website reports 7,642 admissions with radiology data. Both are carried in the imaging subset entry with source attribution.
4. **Verbatim reproduction of a source defect.** The website contact address `cmccrary@mgh.havard.edu` is reproduced exactly as printed, including the apparent misspelling of "harvard." Correcting it would be an inference about intent.

---

## 4. Traps correctly avoided (verified, no change needed)

- MIT license scoped to software, not dataset.
- `$8,000` stipend not recorded as participant compensation.
- HIPAA/GDPR left out of `regulatory_restrictions` — appears only as a workshop topic title, not as a compliance claim about the dataset.
- `doi`, `download_url`, `version`, `total_size_bytes`, `total_file_count`, `issued`, `citation` all left unpopulated. The 23 Tb waveform figure is carried as prose in the waveform subset rather than converted to `total_size_bytes`, since it covers one modality and is not a total.
- No `informed_consent`, `collection_consents`, `consent_revocations`, or `collection_notifications` populated — the bundle describes community focus groups on what data is appropriate for sharing, which is not consent evidence.

---

## 5. Outcome

**Reconciliation: PASS with corrections.** 15 slots amended for evidence overreach or slot fit, 1 structural difference documented as schema-forced, 5 core-record omissions confirmed as core-schema absences with content preserved elsewhere. Both records now assert only what the declared bundle supports, hold the same referent, and preserve rather than resolve inter-source disagreement.

| | Full | Core |
|---|---|---|
| Slots populated | 61 | 47 |
| Validated | yes | yes |

No prior D4D record was read or consulted at any phase.