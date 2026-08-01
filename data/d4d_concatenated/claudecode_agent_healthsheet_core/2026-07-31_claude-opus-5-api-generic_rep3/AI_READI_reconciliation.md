# Reconciliation Report — AI_READI D4D (full ↔ core)

- **Project:** AI_READI
- **Version label:** `2026-07-31_claude-opus-5-api-generic_rep3`
- **Arm:** HEALTHSHEET-ONLY (single structured upstream source)
- **Declared input bundle:** `data/preprocessed/concatenated/AI_READI_healthsheet_only.txt`
- **Full record:** `data/d4d_concatenated/claudecode_agent_healthsheet/2026-07-31_claude-opus-5-api-generic_rep3/AI_READI_d4d.yaml`
- **Core record:** `data/d4d_concatenated/claudecode_agent_healthsheet_core/2026-07-31_claude-opus-5-api-generic_rep3/AI_READI_d4d_core.yaml`
- **Prior D4D consulted:** none (prohibited; no file under `data/d4d_concatenated/` or any `*_crate_d4d.yaml` was opened)

---

## 1. Referent decision

`Dataset` admits one referent. The referent is fixed as:

> **Flagship Dataset of Type 2 Diabetes from the AI-READI Project, version 3** — DOI `10.60775/fairhub.3`, distributed November 2025, covering data collected 2023-07-19 through 2025-05-01 from 2,280 participants.

Versions 1 (204 participants) and 2 (1,067 participants) are treated as *prior states of the same referent*, not as separate `Dataset` entities. They are described in `version_access` and `updates` prose rather than instantiated as sibling records. This choice is held identically in the full and core records.

---

## 2. Slot counts and validation

| Record | Slots populated (Phase 1/2) | Slots populated (post-Phase 4) | Validation |
|---|---|---|---|
| Full (`Dataset`) | 59 | **62** | PASS |
| Core (`CoreDataset`) | 38 | **38** | PASS |

Both files validate cleanly against their declared schemas. No object in any multivalued slot is missing a required key (`DatasetRelationship.relationship_type`/`target_dataset`, `RawDataSource.source_description`, `VariableMetadata.variable_name`, `FileCollection.id`, `DataSubset.id` — none of these ranges are populated except where all required keys are present).

**Reconciliation outcome: RECONCILED WITH CHANGES.** Three slots were added to the full record; two slot values were rewritten in both records; the remainder of the audit findings were adjudicated as acceptable and left as-is with rationale recorded below.

---

## 3. What the audit found

The audit surfaced 19 findings: 0 high, 4 medium, 15 low. No provenance violation was found — every populated value in both records traces to text in the declared bundle, and no fact from outside the bundle was introduced.

Two structural patterns dominated the findings:

1. **Full/core asymmetry on negative findings.** The core record recorded three explicit "No" answers from the bundle that the full record had silently omitted. This is the inverse of the usual failure mode (core under-covering full) and made the pair disagree about which negative findings were on the record at all.
2. **Smoothing of a source-internal inconsistency.** The bundle's Composition section asserts completeness relative to "the first year of data collection," a claim carried over verbatim from an earlier version of the healthsheet, while the Versioning and Collection sections state a v3 window of 2023-07-19 to 2025-05-01. Phase 1 paraphrased this away rather than exposing it.

Everything else was low-severity inference at the margin: identifiers derived from filenames, slot values that are defensible readings rather than stated facts, and one clause carried over from an unanswered sub-prompt.

---

## 4. Changes made

### 4.1 Full record — three slots added

| Slot | Added value (summary) | Why |
|---|---|---|
| `existing_uses` | One `ExistingUse` recording that, as of this release, the dataset creators report no prior task-level use of the dataset. | The bundle answers this question directly and negatively ("Has the dataset been used for any tasks already? A: No"). A stated negative is evidence, not absence of evidence. The core record already carried it; omitting it from the full record made the pair inconsistent. |
| `use_repository` | One `UseRepository` recording that no repository tracking papers or systems using the dataset exists, and that citation of the resources listed at `https://docs.aireadi.org` is required of users. | Same reasoning. Two distinct facts from the Uses section — the absence of a use-tracking repository and the affirmative citation requirement — both belong here and both were present in core. |
| `content_warnings` | One `ContentWarning` recording the creators' assessment that the dataset contains no material that, viewed directly, would be offensive, insulting, threatening, or pose a psychological safety risk. | The Composition section poses and answers this question. Recording the negative assessment is materially different from leaving the slot empty, which would read as "not assessed." Core carried it; full did not. |

The full record now covers every question in the bundle that received a substantive answer, whether the answer is affirmative or negative.

### 4.2 Both records — `sampling_strategies` rewritten

The first `SamplingStrategy` entry previously read that the dataset "contains data from all participants enrolled during the covered data collection period." That phrasing was manufactured to reconcile two statements the bundle does not itself reconcile.

Replaced with a description that (a) quotes the source's completeness claim as given — all participants enrolled during the first year of data collection — and (b) notes that this claim sits alongside the separately stated v3 collection window of 2023-07-19 to 2025-05-01 and the participant count of 2,280, without asserting which is correct. Per the uniform decision rules, where the declared bundle contains statements that disagree, the record represents what the evidence states rather than selecting one.

The second `SamplingStrategy` entry (recruitment sampling targeting approximately equal distribution across sex, race, and diabetes severity; EHR screening of ICD-10 diabetes and prediabetes codes for patients with an encounter in the prior two years; the "N/A" answer to the probabilistic-sampling question) was not modified.

### 4.3 Both records — two clauses removed or qualified

| Slot | Change | Why |
|---|---|---|
| `known_limitations` | Removed the clause "distribution shifts over time." | The phrase appears in the bundle only as sub-prompt (d) of the Challenge question. The answer addresses site diversity, device diversity, urban/hospital-based recruitment, and absent racial/ethnic groups — it does not affirm distribution shift as a present factor. Retaining it would attribute to the creators a limitation they did not claim. The remaining limitations in this slot are all drawn from the answer text. |
| `human_subject_research` | The IRB study number `STUDY00016228` is retained but the description now attributes it explicitly to the filename of the linked approval letter (`Approval_STUDY00016228_Lee_initial.pdf`) rather than presenting it as a stated protocol identifier. | The identifier is real and recoverable from the bundle, so deletion would discard usable evidence; but the bundle never states it as a protocol number in prose. Attributing the derivation preserves the fact and its provenance. The approval date (2022-12-20), the reviewing institution (University of Washington), the annual renewal requirement, and the IRB reliance arrangement across the other two sites are all stated directly and were left unqualified. |

---

## 5. What was left as-is, and why

### 5.1 Inference judged sound and retained

| Slot | Finding | Adjudication |
|---|---|---|
| `at_risk_populations` | "so no minors were enrolled" is an entailment from the ≥40 inclusion criterion, not a statement. | Retained. The entailment is strict and the enrolment criterion is quoted alongside it, so the reader can check the reasoning. The bundle's other at-risk protections (pregnancy exclusion, gestational diabetes exclusion) are stated directly. |
| `publisher` | Set to `https://fairhub.io/`; the bundle names FAIRhub as distribution platform and host, and the AI-READI Consortium as creator/manager, but names no publisher. | Retained. FAIRhub is the entity "responsible for making the resource available" per the slot definition, and it is the only candidate the bundle supports. The Consortium's creating and managing role is separately and correctly recorded in `creators` and `maintainers`, so no entity is conflated. |
| `status` | `published`; inferred from the November 2025 v3 distribution. | Retained. The bundle states the third version was distributed in November 2025 and is available for public use; `published` is the only value in ordinary usage that this supports. |
| `page` | `https://docs.aireadi.org`. | Retained. The slot definition admits "a landing page **or** web page providing access to or information about the resource," and the documentation site is unambiguously the latter. The DOI and the FAIRhub platform are separately recorded in `doi` and `distribution_formats`, so the access point is not lost. |
| `is_tabular` | `false`, where the bundle says the data encompass tabular, imaging, and physiological signal/waveform components. | Retained. The slot is boolean and the dataset is not structured as a table; `false` is the correct answer for a mixed-modality dataset. The full modality breakdown is preserved in `instances` and `distribution_formats`, so the boolean does not carry the descriptive burden. |
| `conforms_to` | OMOP CDM and DICOM, where the bundle says mapping was done "when possible." | Retained with the existing "Where possible" hedge in the accompanying description. Dropping the slot would lose the two named standards, which are the most reusable single fact in the Preprocessing section. |
| `data_collectors` | "imaging staff" extrapolated from a passing mention of "the imaging team." | Retained. The mention is in the bundle (Spectralis HRA entry) and the extrapolation is to a role, not to an identity or a count. Clinical research coordinators, data managers, site PIs, and research staff are all named directly. |
| `keywords` | Agent-constructed; the bundle supplies no keyword field. | Retained. Every term is traceable to bundle prose (type 2 diabetes, salutogenesis, multimodal, retinal imaging, continuous glucose monitoring, wearable, OCT, Bridge2AI). The slot is a discovery aid whose construction from content is its normal use; no term asserts a fact not in the source. |

### 5.2 Structural decisions retained

**`related_datasets` left empty.** The audit correctly notes that v1 and v2 have participant counts and published healthsheet URLs, and could support typed `DatasetRelationship` entries. This was left as-is because of the referent decision in §1: v1 and v2 are prior states of the same referent, not distinct datasets, and instantiating them as relationship targets would contradict that decision. Their identities, counts, healthsheet URLs, and the v2→v3 field change (Snellen visual acuity dropped, logMAR retained) are all recorded in `version_access` and `updates`. No fact is lost; only its structural shape differs.

**Core consolidation retained.** Content that the full record separates across `direct_collection`, `splits`, `third_party_sharing`, `collection_notifications`, `consent_revocations`, and `participant_compensation` is, in the core record, folded into `acquisition_methods`, `sampling_strategies`, `distribution_formats`, `informed_consent`, and `data_collectors`. This is a consequence of the core schema's narrower slot inventory, not a loss of content, and the folding is faithful to the source text in each case. It is recorded here so that the full/core slot-count difference (62 vs 38) is not read as differential coverage.

**`participant_privacy` present in full, absent in core.** The full record carries the tiered public/controlled-access release model and the rationale for withholding raw data (possible PHI/PII in free-text fields, absent terminology mapping). In the core record the raw-data rationale is carried by `raw_sources` and the tiering by `distribution_formats`. The audit flags this as a partial gap. Reviewed and accepted: the two facts are present in core under different slots, and no third fact from the full `participant_privacy` entry is unrepresented.

**`subpopulations` tension retained.** The slot holds both the four diabetes-status study groups (no diabetes; prediabetes/lifestyle-controlled; oral-medication-controlled; insulin-controlled) and the bundle's flat "No" to identifying demographic sub-populations. Both are accurate to the source. The descriptions were left unchanged because the "No" answer's scope is already evident from its adjacent text — the bundle's follow-up sub-questions concern demographic *labels* and their regulatory availability, and the record reproduces that framing. Note for readers: the "No" concerns demographic labels in the public release, not the existence of study groups, and it coexists in the source with the stated recruitment goal of balance across sex, race, and diabetes severity.

**`citation` left empty.** Deliberate. The bundle imposes a citation *requirement* but supplies no citation string; it directs users to resources listed at `https://docs.aireadi.org`. That requirement is recorded in `use_repository` (added in §4.1). Fabricating a DataCite or BibTeX block from the DOI and creator list would be inference presented as a quotation.

### 5.3 Source gaps preserved as gaps

Three questions in the bundle received no response. None was filled by inference:

| Bundle question | Handling |
|---|---|
| De-identification measures taken to avoid re-identification (Composition) | `is_deidentified` records the stated facts only — no PII in the dataset, internal review by AI-READI team members to confirm no PII was accidentally included, and the creators' acknowledged "theoretical risk of future re-identification." The unanswered measures question is noted as unanswered. |
| Pre-processing for de-identification (Preprocessing) | No `PreprocessingStrategy` entry asserts de-identification preprocessing. The cleaning, range-check, and terminology-mapping steps that *are* described are recorded. |
| Erratum (Maintenance) | `errata` left empty. |

The grant number appears in the bundle in two forms — `OT2ODO32644` (Motivation) and `OT2OD032644` (Collection). Both are preserved in `funders` with a note that the source states them inconsistently. Neither was silently normalised.

---

## 6. Residual risk

Low. The principal residual items are the four slots in §5.1 whose values are defensible readings rather than direct quotations (`publisher`, `status`, `page`, `is_tabular`), and the filename-derived IRB identifier now explicitly attributed in `human_subject_research`. Each is flagged in situ in the record descriptions. The full and core records now agree on every fact either represents; where their slot shapes differ, the difference is attributable to the core schema's inventory and is enumerated in §5.2.