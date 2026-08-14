# Phase 4c — Reconciliation Report

**Project:** VOICE
**Version label:** `2026-08-13_claude-opus-5-api-generic-v4_rep1`
**Arm:** BASELINE (input documents only)
**Declared input bundle:** `data/preprocessed/concatenated/VOICE_preprocessed.txt`
**Full record:** `data/d4d_concatenated/claudecode_agent/2026-08-13_claude-opus-5-api-generic-v4_rep1/VOICE_d4d.yaml`
**Core record:** `data/d4d_concatenated/claudecode_agent_core/2026-08-13_claude-opus-5-api-generic-v4_rep1/VOICE_d4d_core.yaml`

---

## 1. Scope of the audit

The Phase 3 audit returned 21 findings against the paired records: 3 high, 7 medium, 11 low. The findings cluster into four groups:

1. **Schema violations** — slots or keys that do not exist in the target class, and a required key omitted.
2. **Projection loss and slot drift** — content present and correctly placed in the full record that was dropped, relocated to a worse-fitting slot, or collapsed into a single object during the Phase 2 core projection.
3. **Fields answered with the absence of an answer** — objects that occupy a slot while recording that the slot's subject does not exist.
4. **Evidence-bounded thinness and residual conflicts** — places where the record is as good as the bundle permits, flagged for transparency rather than repair.

Groups 1–3 were treated as defects and corrected. Group 4 was left as-is, with reasons given in §4.

---

## 2. Changes made to the core record

### 2.1 Removed the invented `distributions` slot (high)

**Finding:** The core record carried a `distributions` slot with 13 entries. No such slot exists in the `CoreDataset` / `Dataset` slot inventory. The inventory declares `distribution_formats` (range `DistributionFormat`) and `distribution_dates` (range `DistributionDate`). The keys used inside the invented objects — `path`, `format`, `media_type`, `conforms_to` — match no declared object range.

**Action:** Deleted the `distributions` slot in full.

**Consequence for the affected content:** The 13 entries described directory-level and file-level content already carried, correctly, in the full record's `file_collections`. That content was restored to the core record as `file_collections` (see 2.2). No factual content was lost by the deletion.

**Note on the accompanying `source_caveats`:** The removed entries carried a caveat asserting that "the declared `format` enumeration in the core schema offers no Parquet term." No `format` enumeration appears in the schema digest for `DistributionFormat.format`; the field is unconstrained. The caveat rationalised a constraint that does not exist, and in doing so recorded Parquet files as `ZIP` — a claim the bundle contradicts directly: *"Binary files are made available as Parquet, an open-source column-oriented data file format."* The caveat was removed with the slot. This was the most serious defect in either record: an invented structure, populated with values the bundle contradicts, defended by a fabricated schema constraint.

### 2.2 Restored `file_collections` to the core record (medium)

**Finding:** The full record populates three `FileCollection` entries (features, phenotype, metadata). The core record omitted the slot entirely, having substituted the invented `distributions` slot for it.

**Action:** Projected the three `FileCollection` entries from the full record into the core record, with `id`, `name`, `description`, `collection_type` and `path` as populated upstream.

`file_count` and `total_bytes` remain unpopulated on all three, and top-level `total_file_count` / `total_size_bytes` remain absent, matching the full record. The bundle reports per-feature record counts (e.g. `torchaudio_spectrogram.parquet (n=29278)`) but never file counts or byte sizes. Populating these would require inference the evidence does not support.

### 2.3 Restored `subsets` as five distinct objects (medium)

**Finding:** The full record populates `subsets` with five `DataSubset` objects, one per disease cohort. The core record dropped `subsets` and folded all five into a single `subpopulations` entry (`.../subpopulation/disease-cohorts`) as one prose `identification` block.

**Action:** Restored `subsets` with five separate `DataSubset` objects — voice disorders, respiratory, neurological/neurodegenerative, mood/psychiatric, controls — each with its own `id`, `name`, `description` and `is_subpopulation: true`.

**Rationale:** The uniform decision rules require one object per distinct entity in a multivalued slot. Five cohorts recruited under five distinct inclusion/exclusion criteria, validated against five distinct gold-standard methods, are five entities. Collapsing them populated the slot without representing what it declares, and discarded the per-cohort validation methods the bundle tabulates at length (Table 1).

The pre-existing single `subpopulations` entry was replaced by cohort-level `subsets`; `subpopulations` is now reserved for the demographic dimensions the bundle names under "Collection and use of demographic information" (age, gender, sex, ethnicity, socioeconomic status), which is what that slot's description asks for.

### 2.4 Restored `splits`; removed the misplaced limitation (medium)

**Finding:** The full record carries a `splits` entry recording that no predefined train/validation/test partitions are provided. The core record dropped `splits` and relocated the same fact into `known_limitations` with `limitation_type: methodological_limitation`.

**Action:** Restored `splits` to the core record with the `split_details` text from the full record. Removed the `.../limitation/no-predefined-splits` entry from `known_limitations`.

**Rationale:** Two problems compounded. First, the content answers `splits` and belongs there — the slot's description explicitly covers "recommended data splits... and the rationale for each split strategy," and "none are provided, users should construct their own" is a direct answer to that. Second, `methodological_limitation` misdescribes it: the bundle presents the absence of splits as a deliberate design choice ("Researchers are encouraged to create their own data splits based on their specific requirements"), not a methodological shortcoming.

### 2.5 Removed the vacuous `annotation_analyses` entry (medium)

**Finding:** The core record's single `AnnotationAnalysis` object populated `analysis_method` with a statement that no inter-annotator analysis was performed.

**Action:** Deleted the entry; `annotation_analyses` is now absent from the core record.

**Rationale:** A value recording that the slot's subject does not exist has not answered the field. The substantive facts — one labeller per instance, no agreement statistics possible — are already carried where they belong: `labeling_strategies[].annotations_per_item: 1`, and `known_biases[.../bias/single-labeler]`, which records the consequence for downstream users. The `annotation_analyses` entry added nothing the schema asks for.

### 2.6 Restored `variables` (low)

**Finding:** The full record populates 15 `VariableMetadata` entries; the core record omitted the slot. The underlying evidence is identical between the two records, so the omission was projection loss rather than an evidence-driven decision.

**Action:** Projected all 15 entries into the core record unchanged. A `source_caveats` was added marking the list as a partial selection (see 2.10).

### 2.7 Restored `relationships` (low)

**Finding:** The full record populates two `Relationships` entries — one describing the participant/session/recording key structure and the possibility of multiple sessions per participant, one recording that instances are otherwise unrelated. The core record omitted both.

**Action:** Projected both entries into the core record.

**Rationale:** The linkage structure is operationally significant for anyone joining feature files to phenotype files, and the bundle states it explicitly ("there may be more than one row per participant in the data files... there is no requirement the participant provide the same response for each visit"). It was recoverable from `variables` in the full record only by inference, and absent from core entirely.

### 2.8 Restored `citation` (medium)

**Finding:** The core record names 17 creators, states in a `source_caveats` that more than one hundred exist, and provided no route to the remainder. The full record's parallel caveat points to `citation`; the core caveat dropped that clause because `citation` was not populated.

**Action:** Populated `citation` in the core record with the PhysioNet v3.1.0 recommended citation as given in the bundle. Restored the "the complete list is carried in the citation" clause to the `creators` `source_caveats`, bringing it back into alignment with the full record.

### 2.9 Restored `collection_notifications` and `collection_consents` (low)

**Finding:** The core record retained `informed_consent` but dropped `collection_notifications` and `collection_consents`. The notification content — the IRB-approved consent process, the in-clinic explanation procedure, the requirement that potential participants restate their understanding to the research assistant — was not preserved elsewhere.

**Action:** Projected both slots from the full record.

Additionally, the satisfaction-survey detail from the full record's `consent_revocations` entry (withdrawing participants are offered an optional survey; no PHI collected) was restored to the core record's `informed_consent[0].withdrawal_mechanism`, which had carried a compressed version of the withdrawal text.

### 2.10 Resolved the `is_tabular` disagreement (low)

**Finding:** `is_tabular: false` was asserted in core and absent from full. The bundle describes a mixture: phenotype data is distributed as TSV with JSON dictionaries (tabular), while feature data is multidimensional tensors in Parquet (not tabular).

**Action:** Removed `is_tabular` from the core record.

**Rationale:** A single boolean is lossy in either direction here, and the two records disagreed by omission. The structural facts are carried accurately in `file_collections` (three collections with distinct `collection_type` values), `distribution_formats`, and `instances[].data_substrate`. Omitting the slot is the correct answer when the evidence does not support either value, per the uniform decision rules. Both records now omit it.

---

## 3. Changes made to the full record

### 3.1 Added required `id` to `related_datasets` entries (high)

**Finding:** Four `DatasetRelationship` entries in the full record carried `name` and `description` but omitted `id`. Per the digest, `DatasetRelationship` accepts the same slots as the top-level listing, where `id` is marked `[req]`. The core record supplied `id` on the same four entries; the full record did not.

**Action:** Added `id` to all four entries, using the identifiers already present in the core record so that the paired records agree. The four are:

- the v3.0.0 predecessor release (`is_previous_version_of`)
- the pediatric dataset (`is_supplemented_by`)
- the Health Data Nexus v1.0 release (`is_version_of`)
- the REDCap data dictionary Zenodo deposit (`is_documented_by`)

This was a validation-blocking defect in the full record and an internal inconsistency between the pair.

### 3.2 Added `source_caveats` to `variables` (low)

**Finding:** The 15 `VariableMetadata` entries cover feature-file columns only (`participant_id`, `session_id`, `task_name`, `n_frames`, and the nine feature tensors). No phenotype columns are covered, despite the bundle enumerating the full phenotype folder structure with per-column JSON dictionaries. The selection was defensible as a sample but was not signalled as one.

**Action:** Added a `source_caveats` to the record noting that `variables` covers the feature-file columns documented in the bundle's Data Description section, and that phenotype columns are documented in per-file JSON dictionaries within the distribution which the bundle enumerates by filename but does not transcribe.

The same caveat was carried into the core record alongside the restored `variables` slot (2.6).

---

## 4. Findings left unchanged, and why

### 4.1 `instances[].counts` on the recording-features instance (medium)

`counts: 29278` is retained for the "derived acoustic feature set for a single task recording" instance, together with the existing `source_caveats` enumerating all nine per-feature counts for v3.1.0 (28,640–32,522).

The audit is right that no single count exists in the bundle for a generically-typed recording feature set — the count varies by feature because different extraction pipelines failed on different files. But the alternatives are worse: splitting into nine instance objects would misrepresent nine views of the same recordings as nine kinds of instance, and omitting `counts` while the bundle states nine specific numbers would discard real quantitative evidence. The spectrogram count is retained as the representative value with the full spread disclosed in the caveat, which is the most honest available reading. **Left as-is; the caveat carries the uncertainty.**

### 4.2 Free-text `role` on `data_collectors` (low)

`research staff`, `clinician co-investigator` and `hospital support staff` are retained as free text. The digest declares no enumeration for `DataCollector.role` — unlike `Maintainer.role`, which is enumerated and where the records correctly use `researcher` and `academic_institution`. The apparent inconsistency between the two slots reflects a real difference in the schema, not an error in the records. Substituting enum terms from a different slot's enumeration would be a fabrication. **Left as-is.**

### 4.3 `human_subject_research.irb_approval` without an approval number (low)

The bundle gives IRB 004890 for the *feasibility study* only (a separate study of the data-collection app, reported in the Frontiers paper). It gives no approval number for the main Bridge2AI Voice Data Acquisition protocol, stating only that it was "Submitted and approved by the USF Single IRB and subsite IRBs through the Single IRB process," with the Canadian sites under separate REB. Attaching 004890 to the dataset protocol would be a category error. The prose description of the approval structure is the strongest reading the evidence supports. **Left as-is; flagged here so the absence is on record.**

### 4.4 `id` set to the version-specific DOI (low)

`id` is `10.13026/8xbn-nq66` (v3.1.0) while `version_access.latest_version_doi` is `10.13026/37yb-1t42` (version-agnostic). The record describes v3.1.0 specifically — its counts, its feature set, its release notes — so the version-specific DOI is the correct identifier for what the record documents. The version-agnostic DOI is available in the slot the schema provides for exactly that purpose. **Left as-is.**

### 4.5 Thin `existing_uses` entry (low)

The single `ExistingUse` object populates only `examples` (the Bridge2AI Summer School and hackathon, using a restricted version with raw audio). The bundle supports no more: it reports that use and separately answers "Is there a repository that links to any or all papers or systems that use the dataset?" with "No." Thinness here reflects the evidence, not the record. **Left as-is.**

### 4.6 `use_repository` omitted (low)

Correctly omitted. The bundle answers the corresponding healthsheet question with a flat "No." Recorded here to confirm the omission is deliberate rather than an oversight.

### 4.7 `file_collections` without counts or sizes (medium, informational)

Confirmed as evidence-driven, not an oversight. See 2.2.

---

## 5. Referent

Both records describe a single referent: **the Bridge2AI-Voice adult dataset as published on PhysioNet, version 3.1.0** (DOI 10.13026/8xbn-nq66, released 1 May 2026).

This choice is held consistently across both records and is worth stating explicitly because the bundle documents several closely related but distinct objects:

- the **pediatric dataset** (separate PhysioNet project, separate DOI, separate REB, 300 participants) — represented as a `related_datasets` entry with `relationship_type: is_supplemented_by`, not merged into the referent;
- the **raw audio corpus** (controlled access via Synapse, institutional sign-off, DTUA) — represented in `data_governance`, `confidential_elements` and `license_and_use_terms`, but not as the referent, since the PhysioNet release explicitly excludes it;
- **earlier versions** (v1.0 on Health Data Nexus, v1.1, v2.0.0, v2.0.1, v3.0.0) — represented in `version_access.versions_available` and, for v3.0.0 and the HDN v1.0, as `related_datasets` entries;
- the **REDCap instrument library and b2aiprep code** — represented as `external_resources` and `is_documented_by`, not as parts of the dataset.

The v3.1.0 figures are used throughout: 833 participants, the nine per-feature record counts in the 28,640–32,522 range, five North American collection sites.

---

## 6. Residual source conflicts disclosed in the records

These are conflicts within the declared bundle, not defects. They remain surfaced in `source_caveats` on the relevant slots rather than silently resolved:

| Conflict | Sources | Treatment |
|---|---|---|
| Participant count | 306 (v1.1) / 833 (v3.0.0, v3.1.0) / 10,000 anticipated by 2027 (study metadata) / 30,000 (IRB protocol, white paper) | v3.1.0 figure used as the referent's count; the target figures are recorded separately as project goals, not as dataset contents |
| Award number | `OT2OD032720` / `3OT2OD032720-01S1` / `3OT2OD032720-01S3` / `3Tf-OTOD03272001S2` / `3TF-OT2ActfOD032720Projectf01S1` | All variants noted in `funders` `source_caveats`; the core project number `OT2OD032720` used as the canonical form |
| Consortium size | 50 experts / 12 North American institutions (white paper) vs. 14 institutions (feasibility paper) vs. 10 other universities (documentation) vs. 9 participating institutions (IRB Annex C) | Noted in `creators` `source_caveats`; no single figure asserted |
| Collection timeframe | "12 months" (healthsheet) vs. four-year study period 2022-09-01 to 2026-11-30 (NIH RePORTER) vs. phased 4-year plan (IRB) | Both recorded in `collection_timeframes` with the discrepancy flagged |
| Affiliation of individuals | Satrajit Ghosh listed as MIT Cambridge and MIT Boston; Vardit Ravitsky as University of Montreal and The Hastings Center; James Anibal as USF (feasibility paper) though affiliated elsewhere in other sources | Noted in `creators` `source_caveats` |
| Distribution platform | Health Data Nexus (healthsheet, v1.0) vs. PhysioNet (v1.1 onward) vs. Synapse (raw audio) | All three recorded; the platform migration is described in `version_access` |

---

## 7. Outcome

| | Full record | Core record |
|---|---|---|
| Slots populated before reconciliation | 78 | 61 |
| Slots populated after reconciliation | 78 | 66 |
| Schema-invalid slots removed | 0 | 1 (`distributions`, 13 entries) |
| Required keys added | 4 (`id` on `related_datasets`) | 0 |
| Slots restored from full → core | — | 7 (`file_collections`, `subsets`, `splits`, `variables`, `relationships`, `citation`, `collection_notifications`, `collection_consents`) |
| Vacuous entries removed | 0 | 2 (`annotation_analyses`; `known_limitations` no-splits entry) |
| Objects de-collapsed | 0 | 1 → 5 (`subsets`) |
| Slots removed as unsupported | 0 | 1 (`is_tabular`) |
| `source_caveats` added | 1 (`variables`) | 1 (`variables`) |

**Validation:** both records validate against their respective schemas and classes.

**Provenance:** no previously generated D4D record was read, opened, grepped or consulted at any phase. All factual content derives from `data/preprocessed/concatenated/VOICE_preprocessed.txt` and the two schema files. The core record's `# Sources:` header names both the bundle and the Phase 1 full record, as required.

---

## 8. Assessment

The two records were, before reconciliation, well grounded in the bundle. Cohort structure, the two-tier access regime, de-identification procedure, feature-extraction parameters, version history and the ethics apparatus were all traceable to source, and the `source_caveats` blocks did honest work surfacing the participant-count, award-number and affiliation conflicts across the eleven input documents.

The defects were concentrated in the Phase 2 projection rather than in Phase 1 evidence handling. One invented slot in the core record displaced a correctly-populated schema slot and, in the process, asserted a fabricated enum constraint and recorded Parquet files as ZIP archives — a claim the bundle contradicts in plain text. Seven further slots were dropped or relocated during projection without evidentiary justification, and five distinct cohorts were collapsed into one prose block. The single high-severity defect in the full record was a missing required key that the core record had supplied, making the pair internally inconsistent as well as invalid.

All defects in groups 1–3 have been corrected. The seven findings left unchanged are cases where the bundle genuinely underdetermines the answer, and in each the record now carries either an explicit caveat or a deliberate omission rather than a guess.