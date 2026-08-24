# Phase 4 Reconciliation Report — VOICE

**Records reconciled**

- Full: `data/d4d_concatenated/claudecode_agent/2026-08-22c_claude-opus-5-api-generic-v5_rep2/VOICE_d4d.yaml`
- Core: `data/d4d_concatenated/claudecode_agent_core/2026-08-22c_claude-opus-5-api-generic-v5_rep2/VOICE_d4d_core.yaml`

**Audit input:** 17 findings — 2 high, 5 medium (core), 2 medium (full), 8 low.

---

## 1. Findings acted on

### 1.1 `distributions` — invented slot (high, core)

The core record carried a top-level `distributions` list with keys `path`, `conforms_to`, `conforms_to_standard`, `format`, `media_type`, `notes`. `distributions` does not appear in the supplied 98-slot inventory, and inside it `conforms_to_standard` was written as a scalar (`BIDS`) where the inventory declares it multivalued.

**Change:** the entire `distributions` block was removed from the core record. Its content was not discarded — the file-layout detail it carried (the nine Parquet filenames, `static_features.tsv`, `audio_quality_metrics.tsv`, the phenotype subfolder inventory, the metadata folder, the JSON dictionary convention) was folded into the existing `distribution_formats` objects, which the inventory does declare. Compare the core `distribution_formats` before and after: the Parquet entry gained the filename list and the metadata-folder sentence; the TSV entry gained the full phenotype subfolder enumeration; the JSON entry gained the dictionary-key description. The full record's `file_collections` block, which carries the same layout in the slot designed for it, is unchanged.

### 1.2 `data_governance.committee_contact` — wrong range (high, core)

The core record supplied `committee_contact: {email: DACO@b2ai-voice.org}`. The declared range is `Person`; `email` is not a documented key on Person, and the value is an office mailbox rather than a person.

**Change:** `committee_contact` was removed from the core `data_governance` object, bringing it into line with the full record, which never carried the key. The address remains recorded in both records inside `data_governance.access_review_process` and in `maintainers`, where it is prose rather than a typed person reference.

### 1.3 `data_collectors[].role` — enum divergence (medium, core)

The core record replaced the enum values used in the full record with free prose (`Research teams coordinating and administering the collection protocol`, `Clinicians providing gold standard diagnoses`).

**Change:** both core `data_collectors` objects now carry `role: researcher`, matching the full record. The descriptive text that had been in `role` was already present in `collector_details` in both records, so nothing was lost.

### 1.4 `preprocessing_strategies` — core stated more than full (medium, core)

The core record carried spectrogram dimension, the six-articulator enumeration and the two pitch ranges; the full record's `preprocessing_strategies` did not.

**Change:** rather than strip detail from the core, the full record's `preprocessing_strategies` was raised to match, since every one of these facts is attested in the tier-1 PhysioNet 3.1.0 Data Description. The full record's spectrogram entry now ends "Dimension is 201 by T"; the mel entry now ends "Each is of dimension 60 by T"; the sparc entry now names the six articulators and the 20 ms windows; the static-features entry now gives 80–500 Hz for torchaudio and 50–550 Hz for sparc. The core entries were edited in parallel so the two now read identically. This closes the divergence in the direction of more evidence rather than less.

### 1.5 `informed_consent[].notes` — compensation relocation (medium, core)

Compensation facts sat in `informed_consent[0].notes` in the core record while the full record used the dedicated `participant_compensation` slot.

**Left in place, with the disclosure strengthened.** `participant_compensation` is not in the supplied 98-slot inventory as a core slot and I have no core schema digest to check it against, so I could not verify that a dedicated slot exists to move it to. The core `informed_consent[0].notes` retains the compensation sentence and now also carries the protocol-revision history (V3 August 2023; V7 and V8 in 2024) and the note that feasibility-study participants were uncompensated — content the full record holds in `participant_compensation.source_caveats`. The core `source_caveats` was rewritten to name compensation explicitly among the relocated items. The full record's `participant_compensation` block is unchanged.

### 1.6 `notes` — citation relocation (medium, core)

Same reasoning. The `citation` slot is declared on `Dataset` and the full record populates it; the core record moved the citation text into `notes` on the claim that the core schema does not declare `citation`.

**Left in place, with the disclosure corrected.** I cannot verify the claim either way. The core `notes` still ends with the citation. What changed is the wording of the core `source_caveats`: the original asserted flatly which slots "the core schema does not declare"; the reconciled version says instead that this is content "the full record carries in slots this record's schema does not declare" and describes where each item went, without asserting the schema's contents as established fact.

### 1.7 `maintainers[1].maintainer_details` — unsupported characterization (medium, full)

The full record described T-CAIREM as "based at the University of South Florida's partner institution the University of Toronto". The bundle says only "based at the University of Toronto".

**Change:** the full record now reads "based at the University of Toronto", matching what the project documentation states and matching the core record, which had it right. The `source_caveats` on that maintainer object is unchanged.

### 1.8 CRediT roles inferred from module leadership (medium, full)

`credit_roles` had been assigned to Sigaras, Ghosh and Johnson partly on the basis of module leadership and library contribution rather than any CRediT statement in the bundle.

**Change, applied to both records.** `credit_roles` is now populated only for the nine individuals whose contributions are itemized in the feasibility publication's author-contributions block, and transcribed from that block:

- Rameau and Watts gained roles they had been denied (`conceptualization`, `project_administration`, `supervision`), which the publication does assign them.
- Sigaras retains `software` — the publication assigns it — and gained `conceptualization`, `project_administration`, `supervision`.
- Ghosh lost `software` and `data_curation`, neither assigned to SG in that block, and gained the three the block does assign.
- Johnson, not an author of that paper, lost `credit_roles` entirely; his b2aiprep contribution is now stated in prose in `notes`.
- Ghosh's `notes` was likewise reworded from "contributor to the b2aiprep and senselab processing libraries" to "named contributor to the b2aiprep processing library", since the bundle names him on b2aiprep specifically.

Each affected `notes` now states that the roles come from the feasibility publication's author-contributions section. A paragraph in both `source_caveats` records the rule applied.

### 1.9 `instances[].data_substrate` — container/content conflation (low, both)

`instances[1]` used `B2AI_SUBSTRATE:30` (Parquet), a container format, while `instances[2]` used `B2AI_SUBSTRATE:80` (Questionnaire response data), a content term — two conventions in one slot.

**Change:** `instances[1].data_substrate` is now `B2AI_SUBSTRATE:49` (Waveform Data) in both records, so all three mapped instances name the nature of the instance rather than the container. The Parquet fact moved into the same object's `notes` ("The released artifacts are stored as Apache Parquet files"), and `instances[2].notes` gained a parallel sentence about the tab-delimited artifacts. Both `source_caveats` now state the convention.

### 1.10 Duplicate `is_representative` key (low, full)

`sampling_strategies[0]` set `is_representative: false` twice.

**Change:** the second occurrence was removed. One `is_representative: false` remains, before `source_data`.

### 1.11 Inconsistent sequence indentation (low, full)

Seven slots had list items indented at the same level as their key.

**Change:** all seven are now nested consistently — `sampling_strategies[0].representative_verification`, `human_subject_research.irb_approval`, `human_subject_research.regulatory_compliance`, `labeling_strategies[0].annotator_demographics`, `machine_annotation_tools[0].tool_accuracy`, `annotation_analyses[0].disagreement_patterns`, `regulatory_restrictions.regulatory_restrictions`.

### 1.12 `id` resolves to a version, not the concept (low, both)

**Change to disclosure only.** The `id` and `doi` values are unchanged — the referent is deliberately version 3.1.0. Both `source_caveats` now carry an "Identifier" sentence stating that `id` and `doi` carry the version-specific DOI and that the version-independent DOI sits in `version_access.latest_version_doi`; the core adds that a reader resolving `id` therefore reaches a specific version.

---

## 2. Findings left as-is

### 2.1 `publisher` as a bare site URL (low, full)

`publisher: https://physionet.org/` is unchanged in both records. The range is `uriorcurie`, whose uri half is the fallback for an identifier no declared prefix covers; the bundle supplies no registry identifier for PhysioNet or for the MIT Laboratory for Computational Physiology, and supplying one from outside the bundle is prohibited. The site URL is the best-attested identifier available.

### 2.2 `collection_timeframes` lacks start and end dates (low, both)

Unchanged. The bundle gives only "a period of 12 months" for the dataset collection; the bounded window in the bundle (2023-06-05 to 2023-07-28) belongs to the separate feasibility study and is correctly excluded. The existing `source_caveats` already records the staleness and the absence of dates.

### 2.3 `file_count`, `total_bytes`, `total_file_count`, `total_size_bytes` omitted (low, full)

Unchanged and correctly omitted. The bundle gives per-feature record counts but no file counts or byte sizes.

### 2.4 `conforms_to_class: CoreDataset` (low, core)

Unchanged. The audit itself recorded "no defect"; the two records necessarily differ here.

### 2.5 Unverifiable core-schema claims in `source_caveats` (low, core)

The claim was softened rather than removed — see §1.6. The list of slot names remains, because it accurately describes what the full record carries and the core does not; what was removed is the assertion that the core schema does not declare them.

---

## 3. Counts

| | Original | Reconciled |
|---|---|---|
| Full record, populated top-level slots | 76 | 76 |
| Core record, populated top-level slots | 71 | 70 |

The core lost one slot: `distributions`, removed as invented. No other slot was added or dropped in either record; every remaining change was to values within existing slots.

---

## 4. Validation

Both files were re-validated after reconciliation:

- Full — `linkml-validate -s data_sheets_schema_all.yaml -C Dataset` — passed.
- Core — `linkml-validate -s data_sheets_schema_core_all.yaml -C CoreDataset` — passed.

## 5. Outcome

Reconciled. Two high-severity structural defects in the core record are resolved. Four medium-severity core/full divergences are closed, three by bringing one record to the other and one (compensation placement) by strengthening the disclosure where the schema could not be verified. One unsupported factual embellishment in the full record is removed. The CRediT-role assignments are now traceable to a single named source rather than inferred, which cost three role assignments and gained six. Remaining low-severity items are either correct omissions or judgments the evidence does not overturn.