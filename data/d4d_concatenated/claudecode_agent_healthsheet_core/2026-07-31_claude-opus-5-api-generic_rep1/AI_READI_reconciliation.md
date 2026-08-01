# Reconciliation Report — AI_READI

**Version label:** `2026-07-31_claude-opus-5-api-generic_rep1`
**Arm:** HEALTHSHEET-ONLY (single structured upstream source)
**Declared input bundle:** `data/preprocessed/concatenated/AI_READI_healthsheet_only.txt`
**Full record:** `data/d4d_concatenated/claudecode_agent_healthsheet/2026-07-31_claude-opus-5-api-generic_rep1/AI_READI_d4d.yaml`
**Core record:** `data/d4d_concatenated/claudecode_agent_healthsheet_core/2026-07-31_claude-opus-5-api-generic_rep1/AI_READI_d4d_core.yaml`
**Prior D4D consulted:** none. No file under `data/d4d_concatenated/` or `data/ro-crate_packages/` was opened at any phase.

---

## 1. Referent decision

`Dataset` admits one referent. The declared bundle describes a single versioned artifact and its predecessors. The referent selected and held across both records is:

> **Version 3 of the AI-READI Flagship Dataset of Type 2 Diabetes**, DOI `10.60775/fairhub.3`, comprising data collected 2023-07-19 through 2025-05-01, 2280 participants, distributed November 2025.

Versions 1 (204 participants) and 2 (1067 participants) are represented as version history within `version_access` and in the `description`, **not** as separate `Dataset` instances and **not** via `parent_datasets` or `related_datasets`. The bundle supplies datasheet URLs for v1 and v2 but no resolvable dataset identifiers, and `DatasetRelationship` requires both `relationship_type` and `target_dataset`; constructing identifiers for them would have been fabrication. This choice is applied identically in full and core.

---

## 2. Phase 3 audit — what was found

47 findings. No high-severity findings.

| Severity | Count | Character |
|---|---|---|
| High | 0 | — |
| Medium | 10 | Over-assertion in five scalar header slots, each mirrored in both records |
| Low | 21 | Interpretive framing, question-derived content, dropped qualifiers |
| Info | 16 | Omissions confirmed correct; core-schema compression confirmed non-contradictory |

**Clean on the dimensions that matter most.** No fabricated entities. No content traceable to any source outside the declared bundle. No evidence of prior-D4D reuse. Referent selection consistent across both files. All quantitative claims agree between full and core and match the bundle: 2280 instances; 204 / 1067 prior-version counts; 2023-07-19 to 2025-05-01 collection window; 70/15/15 split proportions.

**Correct handling of the bundle's own gaps.** The bundle declares 84 questions with 3 unanswered. All three were handled without backfill: the two de-identification questions are explicitly flagged as unanswered in `is_deidentified` and `preprocessing_strategies`, and the erratum question is reflected by omitting `errata` rather than asserting no errata exist.

**Correct handling of the bundle's internal inconsistency.** The bundle gives the grant number twice, differently: `OT2ODO32644` in the Motivation section and `OT2OD032644` in the Collection section. The full record surfaces both rather than silently selecting one. This is the required behavior under the decision rules and was preserved.

**The recurring defect is a single pattern.** Five scalar slots — `publisher`, `page`, `status`, `is_tabular`, `license` — each carried a value the bundle does not support, and each was mirrored identically in the core record. Because full and core shared the same defect, there was no full/core divergence to arbitrate; remediation was applied symmetrically to both.

---

## 3. Changes applied — full record

All changes below were applied identically to the core record (Section 4 records only core-specific consequences).

### 3.1 Slots removed

| Slot | Prior value | Why removed |
|---|---|---|
| `publisher` | `https://fairhub.io/` | The bundle says the dataset "will be available through the FAIRhub platform" and is "hosted on FAIRhub through Microsoft Azure." Hosting and distribution are not publication. No publishing entity is named anywhere in the bundle. Omission is the correct answer. |
| `page` | `https://fairhub.io/` | The bundle supplies a platform root and a DOI, never a dataset landing page. A platform root is not a page describing this dataset. |
| `status` | `published` | Not stated in the bundle. "Distributed in November 2025" is supported and is retained under `distribution_dates`; promoting that to a schema-vocabulary status term is inference. |
| `is_tabular` | `false` | Actively misleading. The bundle states the data "encompass tabular data, imaging data, and physiological signal/waveform data." A single boolean cannot represent a mixed-modality dataset, and `false` contradicts the explicit mention of tabular content. The modality description is retained in `description` and `instances`. |

### 3.2 Slots revised

**`license`** — the coined name "AI-READI dataset license" was removed. The bundle refers only to "the license file containing the terms for reusing the AI-READI dataset" at `https://doi.org/10.5281/zenodo.17555036`. The slot now carries the DOI pointer and the bundle's own characterization of the terms (tailored for commercial or research reuse with requirements around data usage, security, and secondary sharing) without asserting a license identifier that does not exist in the source.

**`conforms_to`** — the bundle's qualifier was restored. Prior text asserted conformance to OMOP CDM and DICOM; the bundle says data were "mapped to standardized terminologies **when possible**." The slot now states best-effort mapping to OMOP CDM and DICOM rather than conformance.

**`sampling_strategies`** — the bundle's literal wording was restored. The prior description generalized "all participants who have been enrolled during the first year of data collection for AI-READI" to "the covered data collection period," silently resolving a tension between that phrase and this record's 2023-07-25 collection window. The literal phrasing is now reproduced, with the tension left visible rather than smoothed away. The separate `N/A` answer to the sampling-strategy question is also noted.

**`known_limitations` — device and site heterogeneity** — polarity corrected. The bundle presents multi-device use affirmatively: "the study included multiple devices for one measure to enhance generalizability and represent the diverse range of equipment utilized in clinical settings." The entry no longer frames this as a limitation. What the bundle *does* state as generalization-limiting — predominantly urban and hospital-based recruitment, absence of Pacific Islander and Native American participants, pilot-phase imbalance across race/ethnicity, sex, and diabetes severity — is retained unchanged.

**`known_limitations` — withheld demographics** — the clause "which constrains direct fairness auditing on the public subset" was struck. The bundle states only that sex, race, and ethnicity are not released publicly and that balanced splits are therefore supplied. The downstream consequence is an analyst inference.

**`intended_uses`** — the enumeration "administrative, software, and research applications" was removed. Those categories appear in the healthsheet *question* as examples; the recorded *answer* is "downstream pseudotime manifolds and various applications in artificial intelligence." The slot now reflects the answer only. Importing a question's example list as dataset fact is a source-attribution error, not merely a framing one.

---

## 4. Changes applied — core record

Every change in Section 3 was applied to the core record with identical wording where the corresponding core slot exists. `publisher`, `page`, `status`, and `is_tabular` were removed; `license`, `conforms_to`, `sampling_strategies`, `known_limitations`, and `intended_uses` were revised.

One core-specific consequence was checked and required no further action: because the core schema folds `splits` into `subpopulations`, the split-balancing facts (70/15/15; balancing for age, sex, races/ethnicities, and study group) live in a slot nominally about population representation. This was verified as content-preserving against the full record's dedicated `splits` entry — no fact is lost, added, or altered in transit. See Section 5.3 for why it was not otherwise adjusted.

Post-remediation, no assertion in the core record contradicts, extends, or omits-in-a-misleading-way any assertion in the full record.

---

## 5. Left as-is, and why

### 5.1 Findings accepted as defensible

**`created_by` = "AI-READI Consortium."** The bundle names this entity directly and also says the dataset "is created and managed by the awardees of the grant." The slot is single-valued; the consortium naming is the more specific of the two and is what the bundle offers as an answer to "who created this dataset." The awardee framing is preserved in `funders`, so the distinction is not lost from the record as a whole.

**`keywords`.** The bundle contains no keyword list; these are curator-generated index terms (Bridge2AI, pseudotime manifold, salutogenesis, T2DM, device and modality terms). Every term is drawn from bundle prose and none introduces a claim. `keywords` is a discovery slot whose function is indexing rather than assertion, so curator derivation is appropriate. Retained.

**`funders` grant-number discrepancy.** Both variants remain visible. The parenthetical mildly privileges one form by presenting it as "the grant number," but collapsing to either variant, or picking one silently, would violate the rule against resolving source disagreement. The current form is the least-bad option available and was left alone.

**`subpopulations` framing.** The bundle answers "No" to whether the dataset identifies demographic sub-populations, and the record's first entry records exactly that answer. The subsequent entry describes diabetes-status strata that the bundle introduces only as split-balancing categories. Retaining both, in that order, represents the source's actual position better than dropping either: the negative answer is present and is not overridden by the strata entry that follows it.

**`at_risk_populations` MoCA caveat.** The MoCA education, socioeconomic, and mental-health scoring caveats appear in the bundle's Devices section as instrument limitations, not as participant safeguards. Placement is marginally off-slot. It was left in place because relocating it would have required inventing a framing the bundle does not supply, and because the content itself is verbatim-faithful and more discoverable here than it would be if dropped. Flagged rather than moved.

**`human_subject_research` study identifier.** `STUDY00016228` is inferred from the approval-letter filename `Approval_STUDY00016228_Lee_initial.pdf`. Filename-derived, but the filename is itself part of the declared bundle and the inference is mechanical rather than interpretive. The IRB date (2022-12-20), institution (University of Washington), reliance arrangement, and 90-day renewal requirement are all stated outright. Retained.

**`distribution_dates`.** Combines "distributed in November 2025" (Distribution section) with "released fall 2025" (Composition section). Both are in the bundle and they are compatible, not conflicting. No change.

### 5.2 Omissions confirmed correct

`citation` — required by the bundle but no citation string is supplied, only a pointer to documentation. `download_url` — no direct data URL exists in the bundle. `errata` — question explicitly unanswered. `total_file_count`, `total_size_bytes`, `file_collections`, `compression`, `variables` — no file inventory, sizes, compression, or per-variable metadata anywhere in the bundle. `annotation_analyses`, `machine_annotation_tools`, `imputation_protocols`, `labeling_strategies` — the bundle states repeatedly that no labeling was performed and describes no imputation or automated annotation. `prohibited_uses` — the bundle defers every use-restriction question to an external license file whose contents are not in the bundle; nothing specific can be enumerated, and what the bundle does support is captured in `discouraged_uses` as a pointer. `raw_data_sources` — omitted in favor of `raw_sources` to avoid a duplicate record; no inconsistency introduced.

### 5.3 Explicit negatives left unpopulated

The bundle answers "No" to: prior task use (`existing_uses`), existence of a use-tracking repository (`use_repository`), and offensive or distressing content (`content_warnings`). All three slots are list-valued, and an empty list is the natural encoding of a negative. Populating them with prose entries asserting absence would add records that describe nothing. Left omitted, and noted here so the negatives are on record even though the YAML does not carry them.

### 5.4 Core-schema compression accepted

Content from `subsets`, `splits`, `relationships`, `collection_consents`, `collection_notifications`, `consent_revocations`, `participant_compensation`, `participant_privacy`, `third_party_sharing`, and `direct_collection` is folded into the core slots `resources`, `subpopulations`, `instances`, `informed_consent`, `acquisition_methods`, `data_collectors`, and `distribution_formats`. This is the core schema working as designed. Each fold was checked for content preservation and none introduces a contradiction with the full record. Not treated as a defect and not altered.

---

## 6. Validation

| Record | Schema | Class | Result |
|---|---|---|---|
| Full | `src/data_sheets_schema/schema/data_sheets_schema_all.yaml` | `Dataset` | **pass** |
| Core | `src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml` | `CoreDataset` | **pass** |

Both validated after remediation. Removing four scalar slots from each file affected no required key; `id` is present in both, and every `DataSubset`, `FileCollection`, `DatasetRelationship`, and `RawDataSource` object in either file satisfies its required keys (or, in the case of `related_datasets` and `file_collections`, is absent entirely).

---

## 7. Slot counts

| Record | Populated before Phase 4 | Populated after Phase 4 | Delta |
|---|---|---|---|
| Full (`Dataset`, 94 slots) | 62 | 58 | −4 |
| Core (`CoreDataset`) | 38 | 34 | −4 |

The delta is entirely the four removed scalar slots per record. The six revised slots changed content, not count.

---

## 8. Outcome

**Reconciled.** Both records validate. Both hold the same referent — AI-READI flagship T2DM dataset v3, DOI `10.60775/fairhub.3` — with agreeing counts, dates, and version history. All ten medium-severity findings were remediated by removal or restatement, symmetrically across full and core. Seven of the twenty-one low-severity findings were remediated (device-heterogeneity polarity, fairness-auditing inference, question-derived application enumeration, `conforms_to` qualifier, and `sampling_strategies` literal wording, each counted once per record where applicable); the remainder were assessed as defensible and are documented in Section 5 rather than changed. All sixteen info findings confirmed existing handling as correct and required no action.

Residual known softness, disclosed rather than fixed: the `funders` grant-number parenthetical mildly privileges one variant of a discrepancy it otherwise correctly surfaces; the MoCA instrument caveat sits under `at_risk_populations` on placement grounds the bundle does not supply; the study identifier in `human_subject_research` is filename-derived; and three explicit "No" answers are encoded as omissions rather than as records. None of these introduces a claim the bundle does not support.

No prior D4D record from any arm, label, or date was read, opened, grepped, or consulted at any phase.