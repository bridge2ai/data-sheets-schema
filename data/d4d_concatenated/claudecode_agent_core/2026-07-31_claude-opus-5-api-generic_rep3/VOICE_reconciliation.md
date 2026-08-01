# VOICE — Phase 4 Reconciliation Report

**Version label:** `2026-07-31_claude-opus-5-api-generic_rep3`
**Arm:** BASELINE (input documents only)
**Records reconciled:**

- `data/d4d_concatenated/claudecode_agent/2026-07-31_claude-opus-5-api-generic_rep3/VOICE_d4d.yaml`
- `data/d4d_concatenated/claudecode_agent_core/2026-07-31_claude-opus-5-api-generic_rep3/VOICE_d4d_core.yaml`

**Declared input bundle:** `data/preprocessed/concatenated/VOICE_preprocessed.txt` (11 files)

---

## 1. Referent

The bundle describes several distinct resources that could each satisfy `Dataset`: the adult Bridge2AI-Voice flagship dataset across six PhysioNet versions plus an earlier Health Data Nexus release; a separate pediatric PhysioNet project; the REDCap instrument library; and the smartphone acquisition application evaluated in the feasibility publication.

Both records take as referent **the adult Bridge2AI-Voice dataset at PhysioNet version 3.1.0** (published 2026-05-01, 833 participants). This choice is held consistently in `version`, `citation`, `page`, `issued`, and all feature-level counts. The pediatric dataset is treated as a **distinct resource**, not a version or subset, on the explicit strength of the curation note in the bundle stating that the two are separate PhysioNet projects covering distinct cohorts under a separate protocol.

The audit confirmed this choice is applied without drift, with one exception corrected below (§2.2).

---

## 2. Changes to both records

### 2.1 `distributions` removed from the core record — *high severity*

The core record carried a `distributions` slot holding the `features/`, `phenotype/`, and `metadata/` folder groupings. This slot is not in the declared `CoreDataset` inventory. Its content corresponds to the full schema's `file_collections`, whose range `FileCollection` requires an `id` on every entry; the core entries carried only `description`.

**Action:** slot removed from the core record. The same content is retained in the full record's `file_collections`, where the range is admitted and every entry carries an `id`. This was the only finding posing a direct validation failure, and it also removed a structural inconsistency between the two records.

### 2.2 `id` and `doi` repointed to the version-specific DOI

Both slots resolved to `10.13026/37yb-1t42`, the *latest-version* PhysioNet DOI, while `version`, `page`, `issued`, and `citation` all pinned the record to 3.1.0. A latest-version identifier is a moving target: as new versions publish, the record's identity would silently drift away from the referent it describes.

**Action:** both repointed to `10.13026/8xbn-nq66`, the version-specific DOI for 3.1.0. Both DOIs are attested in the bundle; this selection is the one that matches the declared referent.

### 2.3 `last_updated_on` removed

The bundle records a publication date. It does not attest a distinct last-modification event separate from publication. The slot was populated by restating the publication date with a fabricated `T00:00:00Z` component.

**Action:** removed from both records. `issued` alone carries the attested fact.

### 2.4 `publisher` removed

Set to `https://physionet.org/`. The bundle describes PhysioNet as a hosting platform maintained by the MIT Laboratory for Computational Physiology; attributes the dataset to the Bridge2AI-Voice Consortium under NIH Common Fund award OT2OD032720; and, in the healthsheet distribution section, names `healthdatanexus.ai` as the publishing platform — a statement predating the PhysioNet migration.

No source designates a publisher in this slot's sense. Under the decision rule preferring omission over inference, the slot was removed. The alternative reading — that a repository is by definition the entity making a resource available — is available but is an inference the bundle does not make.

### 2.5 `related_datasets` populated

Previously omitted from both records, with the relevant material carried only as prose in `external_resources`. The bundle supplies target identifiers and enough relationship context for two entries, and both required keys (`relationship_type`, `target_dataset`) are satisfiable:

| Target | Relationship |
|---|---|
| Bridge2AI-Voice Pediatric Dataset (`10.13026/h995-bt35`, v1.1.0) | Companion resource from the same consortium and protocol family; distinct cohort, distinct PhysioNet project |
| Bridge2AI-Voice v1.0 on Health Data Nexus (`10.57764/qb6h-em84`) | Predecessor release of the same dataset on a prior platform |

`parent_datasets`, `resources`, and `subsets` remain omitted: no part/whole relation is attested for the adult dataset, and the disease cohorts, while described in detail, are not presented as identified dataset subsets.

### 2.6 Source-conflict notes added where conflicts had been carried silently

The records already flagged the divergent funding-identifier strings explicitly. Three comparable conflicts were being carried without comment. Editorial treatment is now uniform — in each case the record states both claims and states that the bundle does not reconcile them:

| Slot | Conflict now flagged |
|---|---|
| `collection_timeframes` | Healthsheet reports a 12-month collection period; the IRB protocol describes a phased four-year design with Phase 1 complete November 2023 and Phase 2 ongoing November 2024; the NIH project period runs 2022-09-01 to 2026-11-30. The 12-month figure cannot be reconciled with an 833-participant cohort accumulated across three release cycles. |
| `cleaning_strategies` | Healthsheet answers "No" to whether cleaning preprocessing occurred; the same bundle documents an audit protocol, transcript review with removals, monthly 10% quality-control sampling, and caregiver-clip discarding. |
| `instances` | The v3.0 documentation figure of ~61,937 voice-derived recordings is not reconciled in the bundle against the v3.1.0 per-representation counts (~23,000–32,500 per feature type across nine representations) or against the v1.0 figure of 12,523 recordings from 306 participants. |

### 2.7 Smaller factual corrections

| Slot | Change |
|---|---|
| `instances` | The 833 figure was attributed to the healthsheet. The healthsheet describes itself as documenting v2.0.0; 833 is the v3.0.0/v3.1.0 participant count. Reattributed to the PhysioNet v3.1.0 abstract. Figure unchanged. |
| `known_limitations` | The self-containment entry led with the record's own judgment ("The dataset is not self-contained with respect to the raw waveforms…") and then cited the healthsheet as contradicting it, inverting the evidentiary relationship. Rewritten so the attested healthsheet statement leads and the observation about raw-audio separation is marked as an inference from the access architecture. |
| `known_limitations` | "the initial releases" narrowed to "the initial release," matching the bundle, which states remote collection did not occur for the initial release specifically. |
| `subpopulations` | The neurological cohort entry presented a clean age range of 44–85. The bundle's Table 1 gives inclusion as "over the age of 44 and under 85" and exclusion as "less than the age of 44 and above 85" — not complements, and inconsistent at both boundaries. Now reports both criteria as stated and notes the boundary inconsistency. |
| `content_warnings` | The entry noted that the de-identification documentation reports free-speech transcript removal while another section implies transcription content is present, but left the reader unable to determine which governs v3.1.0. Now states plainly that the bundle does not resolve this for the released artifact. |
| `funders` | The string `3TF-OT2ActfOD032720Projectf01S1` is retained but marked as an apparent extraction artifact of the healthsheet rather than a competing identifier claim. Retained rather than dropped because the corruption is itself a fact about the source. |

### 2.8 `is_tabular` removed from the core record

Asserted `false`. The release is heterogeneous: the phenotype directory and `static_features.tsv` are tabular; the nine Parquet tensor files are not. The bundle makes no determination, and a single boolean cannot represent the release. Removal also restores consistency with the full record, which already omitted the slot.

---

## 3. Full/core divergences documented rather than resolved

Nine full-record slots have no distinct counterpart in the core record. Where the core inventory admits an equivalent, content was folded and the folding is recorded here. Where it does not, the divergence is structural and the content is recoverable only from the full record.

| Full-record slot | Disposition in core |
|---|---|
| `collection_consents` | Folded into `informed_consent` |
| `consent_revocations` | Folded into `informed_consent` |
| `collection_notifications` | Folded into `informed_consent` |
| `direct_collection` | Folded into `acquisition_methods` |
| `relationships` | Folded into `instances` |
| `splits` | Folded into `instances` |
| `file_collections` | Not carried (see §2.1) |
| `participant_privacy` | **Not carried** |
| `variables` | **Not carried** |

The last two are the material losses. `participant_privacy` documents the two-tier privacy architecture — institution-local identified data alongside a de-identified shared layer — and the federated-learning design in which model updates rather than data cross institutional boundaries. `variables` documents the recurring Parquet field structure (`participant_id`, `session_id`, `task_name`, `n_frames`, and the per-representation tensor field). Neither has a home in the declared `CoreDataset` inventory. Both are retained in the full record; a reader working from the core record alone will not recover them.

---

## 4. Left as-is

| Slot | Reason |
|---|---|
| `issued` | Retained as `2026-05-01T00:00:00Z`. The date is firmly attested; the time component is encoding padding required by the `datetime` range and carries no evidentiary claim. Dropping the slot to avoid the padding would discard an attested fact to avoid a schema artifact. |
| `language: en` | Inferential but well-supported: collection, participant-facing materials, and documentation are English throughout, and non-English speakers were an explicit exclusion criterion. Spanish protocols are described as under development, not released. |
| `created_by` | Collective attribution to the Bridge2AI-Voice Consortium is what the healthsheet supports when it asks who created the dataset and on whose behalf. No source names a single primarily responsible party; co-PIs are named as co-leads, not as sole creators. |
| `conforms_to_class` | Omitted. `conforms_to` and `conforms_to_schema` are populated from the BIDS v1.9.0 and REDCap references; the bundle names no specific class. Omission is correct. |
| `total_file_count`, `total_size_bytes`, `compression`, `download_url` | All omitted. The bundle enumerates files but states no total, no byte size, no compression scheme, and provides no direct download URL — access is gated behind credentialing and a DUA. Omission is correct. |
| `parent_datasets`, `resources`, `subsets` | Omitted; see §2.5. |

---

## 5. Validation

Both records were re-validated after the edits:

```
poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_all.yaml \
  -C Dataset data/d4d_concatenated/claudecode_agent/2026-07-31_claude-opus-5-api-generic_rep3/VOICE_d4d.yaml

poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml \
  -C CoreDataset data/d4d_concatenated/claudecode_agent_core/2026-07-31_claude-opus-5-api-generic_rep3/VOICE_d4d_core.yaml
```

Net slot deltas: full record −1 (`last_updated_on`, `publisher` removed; `related_datasets` added). Core record −3 (`distributions`, `is_tabular`, `last_updated_on`, `publisher` removed; `related_datasets` added).

---

## 6. Residual risks

1. **Version volatility.** The referent is a specific PhysioNet version in an actively maintained series with a stated semi-annual release cadence. The bundle already contains a curation note indicating that a captured source (3.0.0) had been superseded upstream. The records will require re-grounding against a refreshed bundle rather than incremental patching.

2. **Healthsheet currency.** The project documentation healthsheet self-identifies as describing v2.0.0 and is internally inconsistent with the v3.1.0 release material on collection duration, cleaning, instance counts, and self-containment. Each of these is now flagged in place, but the healthsheet remains the sole source for several slots — including much of the motivation, uses, and governance content — where no v3.1.0-era restatement exists to check against.

3. **Two-tier access.** The record describes derived features under credentialed PhysioNet access, while raw audio is distributed separately via Synapse under a controlled-access process. The records consistently take the PhysioNet derived-feature release as the referent, but a reader conflating the two tiers will misread the composition, de-identification, and content-warning slots.

4. **Prior-D4D isolation.** No previously generated D4D record was read or consulted at any phase. All factual content traces to the declared bundle.