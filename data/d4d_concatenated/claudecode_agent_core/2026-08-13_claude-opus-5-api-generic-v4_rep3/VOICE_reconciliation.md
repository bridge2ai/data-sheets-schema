# Phase 4 Reconciliation Report — VOICE

**Project:** VOICE (Bridge2AI-Voice)
**Version label:** `2026-08-13_claude-opus-5-api-generic-v4_rep3`
**Arm:** BASELINE (input documents only)
**Declared input bundle:** `data/preprocessed/concatenated/VOICE_preprocessed.txt`
**Full record:** `data/d4d_concatenated/claudecode_agent/2026-08-13_claude-opus-5-api-generic-v4_rep3/VOICE_d4d.yaml`
**Core record:** `data/d4d_concatenated/claudecode_agent_core/2026-08-13_claude-opus-5-api-generic-v4_rep3/VOICE_d4d_core.yaml`
**Date:** 2026-08-14

---

## 1. Referent declaration

`Dataset` admits one referent. Both records describe **the Bridge2AI-Voice flagship adult voice dataset as published on PhysioNet**, with the pediatric release (`b2ai-voice-pediatric`) represented as a *related dataset* rather than as part of the same record. This choice is held consistently across full and core.

Rationale: the declared bundle contains five PhysioNet-family source documents, of which three describe the adult release lineage (v1.1, v3.0.0, v3.1.0) and one describes the pediatric release as a separately DOI'd, separately access-gated project with its own participant cohort, its own REB (Hospital for Sick Children, not USF), and its own author list. The `docs.b2ai-voice.org` documentation likewise routes adult and pediatric access through distinct PhysioNet registrations. Treating them as one referent would have required merging two distinct ethics approvals, two consent regimes, and two participant populations into single-valued slots.

The latest adult version documented in the bundle, **v3.1.0 (published 1 May 2026)**, is the version described; earlier versions are represented through `version_access` and the release-note lineage rather than as separate referents.

---

## 2. Audit findings and disposition

The audit returned 20 findings: 3 high, 6 medium, 11 low. Disposition below, grouped by action taken.

### 2.1 Changed — high severity

#### F1. `distributions` slot removed from core record

**Finding:** The core record carried a `distributions` slot not declared in the schema digest, whose member objects mixed keys from two different declared classes — `path` (a `FileCollection` key) alongside `format` and `media_type` (`DistributionFormat` keys).

**Action:** The slot was deleted and its content redistributed into the two declared slots that actually carry it:

- Format and media-type content → `distribution_formats` (range `DistributionFormat`), matching the full record's existing block.
- Path content → `file_collections` (range `FileCollection`), matching the full record's existing block.

**Rationale:** A slot name absent from the schema is not a slot. The digest is explicit that structure is fixed by the schema and never by content, and a composite object drawn from two classes cannot validate against either. The full record already held both blocks correctly; the core record's divergence was a Phase 2 construction error, not a difference in evidence.

#### F2. `format: ZIP` removed

**Finding:** One core `distributions` entry carried `format: ZIP`, with a sibling `source_caveats` openly stating that ZIP was chosen as a placeholder because the enumeration offered no Parquet term. The bundle states Parquet throughout and never mentions ZIP.

**Action:** The value was removed. In the reconstructed `distribution_formats` block, `format` carries the free-text description of Apache Parquet that the full record already used. Where the schema offers `compression` as an enum (`gzip`, `bzip2`, `zip`, `tar`, `xz`, `lzma`, `compress`), that slot was left **unpopulated**, because the bundle nowhere states that the Parquet files are additionally compressed by any of those methods.

**Rationale:** This was the most serious defect in either record. Asserting a fact the sources contradict, in order to satisfy an enumeration, is a fabrication — and the caveat that acknowledged it does not license it. `DistributionFormat.format` has no enum constraint in the digest, so the free-text Parquet description validates and is true; the placeholder was never necessary. Where an enum genuinely has no fitting term, the correct action is omission, exactly as the digest instructs for `data_substrate` and `data_topic`.

#### F3. Disease cohorts returned from `resources` to `subsets`

**Finding:** Five disease-cohort entries (voice disorders, neurological/neurodegenerative, mood/psychiatric, respiratory, pediatric) appeared in the core record under `resources` (range `Dataset`), having been carried over from the full record's `subsets` (range `DataSubset`), where they were correctly flagged `is_subpopulation: true` / `is_data_split: false`.

**Action:** Moved back to `subsets` in the core record, preserving the `is_subpopulation` / `is_data_split` flags. `resources` is now unpopulated in both records.

**Rationale:** `resources` declares sub-resources or component datasets — separately constituted things that are part of this dataset. Disease cohorts are recruitment strata within a single dataset; the bundle describes them as "5 disease cohort categories" around which acquisition is centred, not as component datasets with their own identity. The digest's own guidance on `resources` (use `file_collections` for file groupings) signals that the slot is for genuine sub-resources. `DataSubset` exists precisely for demographic and clinical subgroups and carries the `is_subpopulation` flag that makes the distinction explicit.

Where a projection has no home for content, omission is correct; relocation into a slot with different declared meaning is not. In this case `subsets` was available, so the content is retained.

### 2.2 Changed — medium severity

#### F4. Rudzicz affiliation — "Halifax, Nova Scotia" removed

**Action:** `creators[*].affiliations` for Frank Rudzicz now carries "University of Toronto, Toronto, Ontario, Canada" and "Dalhousie University, Toronto, ON, Canada" — the latter transcribed exactly as the feasibility publication's group-member list gives it, including its apparent internal oddity. A `source_caveats` note records that the bundle gives Dalhousie with a Toronto location, which is geographically anomalous but is what the source says.

**Rationale:** "Halifax, Nova Scotia" is true of Dalhousie University in the world but appears nowhere in the declared bundle. Under the provenance guard the bundle is the only source of dataset facts; correcting a source's apparent error from outside knowledge is the same class of act as inventing a fact. The anomaly is surfaced in `source_caveats` rather than silently repaired.

#### F5. Ravitsky affiliation — "Garrison, NY" removed

**Action:** Now "The Hastings Center" (no location) and "University of Montreal, Montreal, Quebec, Canada".

**Rationale:** The bundle names The Hastings Center in the audiomics viewpoint's contributor list and in the documentation's collaborator list, in both cases without a location. The Montreal location for the University of Montreal *is* given, in the feasibility publication, and is retained.

#### F6. Ghosh affiliation conflict disclosed

**Action:** The Cambridge, MA form is retained as the primary value, and a `source_caveats` entry was added to the creators block recording that the same publication gives both "Cambridge, MA, United States" (author affiliation footnote) and "Boston, MA, USA" (consortium group-member list) for MIT.

**Rationale:** The audit was correct that silently resolving a within-bundle conflict is a defect even where the resolution is the better-attested one. The rule adopted across this record is that conflicts are represented rather than adjudicated. The value was not changed, because one of the two must be chosen for a scalar field; what changed is that the choice is now visible.

#### F7. `instances[1].counts` removed

**Action:** The integer `32522` was deleted from the acoustic-recording instance. The surrounding `notes` and `source_caveats` were rewritten to state the per-feature row counts the bundle actually gives (torchaudio_pitch 32,522; torchaudio_spectrogram 29,278; sparc_ema 28,640, etc. for v3.1.0) and to record that the bundle supplies no single recording total for the adult release, and that the project documentation's figure of ~61,937 voice-derived recordings for v3.0 is not reconcilable with the per-feature counts in the v3.0.0 PhysioNet description.

**Rationale:** A typed integer slot asserts a count. Populating it with a number that the record's own note disclaims as not being that count places an unsupported value in the field while appearing to answer it. The per-feature counts belong in prose because they answer a different question than `counts` asks.

The participant-level instance retains `counts: 833`, which the bundle states directly and repeatedly.

#### F8. CRediT roles removed

**Action:** `credit_roles` was removed from all creator entries in both records.

**Rationale:** The audit is right that the caveat mitigated but did not license these values. The bundle contains a CRediT-style contribution statement for the *feasibility app study* (a different artefact, with nine authors), and module-lead tables for the consortium. Neither is a CRediT assignment for the dataset. Mapping "Lead – Genomic data" to `data_curation`, or assigning `methodology` to bioethicists on the strength of their module membership, is generator inference presented in a controlled vocabulary that implies it was recorded. The roles are gone; the module-lead information they were derived from is retained as prose in each creator's `notes`, where it is true and attributable.

#### F9. `README.md` extension restored

**Action:** The `conforms_to` BIDS description now reads "dataset_description.json, CHANGES.md and README.md", matching the bundle's folder tree exactly.

### 2.3 Changed — low severity

#### F10. `issued` timezone offset removed

**Action:** `issued: '2026-05-01T00:00:00'` (was `'2026-05-01T00:00:00Z'`). A `source_caveats` note records that the bundle gives only a publication date, and that the time component is a schema artefact of the `datetime` range rather than evidence.

**Rationale:** The `datetime` range compels a time component; it does not compel a UTC assertion. Dropping `Z` removes the unevidenced claim while satisfying the type.

#### F11. `annotation_analyses` removed from core

**Action:** Deleted from the core record. The equivalent content remains in the full record's `labeling_strategies[0].inter_annotator_agreement`, which states that each instance carried a single clinician label and that no inter-annotator agreement was computed or reported.

**Rationale:** The core record is a projection of the full record. A slot appearing in the projection but not the source inverts that relationship and makes the pair incoherent. The content was already correctly placed in the full record.

#### F12. `splits` removed from full record

**Action:** Deleted. The bundle's statement that no recommended splits are provided and that researchers should construct their own is retained in `known_limitations` (as a `methodological_limitation` with `recommended_mitigation`), where it is a fact about the dataset rather than an empty structural slot.

**Rationale:** Populating `splits` with a statement that there are no splits is the anti-pattern the digest warns against — recording absence instead of omitting. The healthsheet's guidance to users is genuine content and has a proper home.

### 2.4 Left as-is, with reasons

#### F13. `conforms_to_class` pairing — no change

`Dataset` in the full record, `CoreDataset` in the core record. This is exactly what the digest prescribes. The audit flagged it for confirmation only; confirmed correct.

#### F14. `publisher: https://physionet.org` — retained, caveat added

The bundle states PhysioNet hosts the dataset and is maintained by the MIT Laboratory for Computational Physiology; it does not use the word "publisher". Retained because PhysioNet is unambiguously the entity making the resource available, which is what the slot declares. A `source_caveats` entry now records that the bundle describes PhysioNet as host and platform, not as publisher, and that Health Data Nexus (T-CAIREM, University of Toronto) served this role for v1.0.

#### F15. `language: en` — retained

The bundle states the protocol, communication with participants, and eligibility are English-only, with Spanish under development. The audit correctly notes this describes the data rather than the record. Retained: the metadata record is also in English, and the slot's description ("Language in which the information is expressed") is satisfied either way. A note in `known_limitations` covers the English-only coverage limitation, which is the substantive fact.

#### F16. `variables` coverage — no change

Thirteen `VariableMetadata` entries cover the derived-feature tensors and the join keys (`participant_id`, `session_id`, `task_name`, `n_frames`). Phenotype columns are not enumerated.

Left as-is. The bundle lists instrument *files* and states that each has a per-column JSON dictionary, but it does not reproduce the column names, types, ranges, or missing-value codes that `VariableMetadata` declares. Emitting entries per instrument would produce objects of the right shape holding none of the structure the class exists to carry — the exact defect the digest warns against. The instrument inventory is instead captured in `file_collections` and in the phenotype-folder description under `conforms_to`.

#### F17. `confidential_elements[0].confidential_elements_present: false` — retained

Faithfully transcribes the healthsheet's answer. The attached `source_caveats` records the tension with the withholding of raw audio under controlled access and with the memorandum on ethical justification for controlled access. Representing the source's answer and its tension is correct; overriding the source's own "No" would be adjudication.

#### F18. `distribution_formats[*].format` prose — retained

`format` carries no enum in the digest. The bundle describes formats in prose ("Apache Parquet, an open-source column-oriented data file format"), and `media_type` carries the machine-readable value where one is determinable. Splitting the prose further would not add evidenced structure.

#### F19. `file_count` / `total_bytes` / `total_file_count` / `total_size_bytes` — correctly omitted

The bundle gives per-feature *row* counts, never file counts or byte sizes. Confirmed as evidence-driven omission.

#### F20. `collection_timeframes[0]` date fields — correctly omitted

The bundle states the healthsheet's "data was collected over a period of 12 months" but gives no start or end date for the released cohort; the NIH RePORTER project window (2022-09-01 to 2026-11-30) is the award period, not the collection period, and is retained in `source_caveats` as context. `start_date` and `end_date` remain unpopulated.

---

## 3. Cross-record consistency after reconciliation

| Property | Full | Core |
|---|---|---|
| Referent | adult PhysioNet release, v3.1.0 | same |
| `id` | identical | identical |
| `conforms_to_class` | `Dataset` | `CoreDataset` |
| `conforms_to_schema` | `https://w3id.org/bridge2ai/data-sheets-schema` | same |
| `conforms_to_standard` | `BIDS` | `BIDS` |
| Creators | 17, no `credit_roles` | same 17, same affiliations |
| Cohort partitions | `subsets` (5, `is_subpopulation: true`) | `subsets` (5, identical flags) |
| Distribution | `distribution_formats` + `file_collections` | same two slots, no `distributions` |
| Pediatric release | `related_datasets`, `relationship_type: is_supplemented_by` | same |

No slot is now populated in the core record that is absent from the full record.

---

## 4. Validation

Both records were re-validated after the changes above:

```
poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_all.yaml \
  -C Dataset data/d4d_concatenated/claudecode_agent/2026-08-13_claude-opus-5-api-generic-v4_rep3/VOICE_d4d.yaml

poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml \
  -C CoreDataset data/d4d_concatenated/claudecode_agent_core/2026-08-13_claude-opus-5-api-generic-v4_rep3/VOICE_d4d_core.yaml
```

Both pass.

---

## 5. Standing source conflicts (represented, not resolved)

These remain visible in `source_caveats` on the relevant slots and were deliberately not adjudicated:

1. **Enrollment target** — 10,000 (documentation, study metadata) vs 30,000 (audiomics viewpoint, IRB protocol §12.1). Recorded on `purposes` and `sampling_strategies`.
2. **Award number** — `OT2OD032720` / `3OT2OD032720-01S1` / `3OT2OD032720-01S3` / `1OT2OD032720-01` / `3Tf-OTOD03272001S2` / `3TF-OT2ActfOD032720Projectf01S1`. Recorded on `funders`.
3. **Recording count** — ~61,937 voice-derived recordings for v3.0 (documentation) vs per-feature row counts of 28,640–32,522 (PhysioNet v3.0.0 / v3.1.0). Recorded on `instances`.
4. **Site count** — five recording sites (healthsheet, PhysioNet) vs nine or twelve participating institutions (IRB Annex C, documentation collaborator list) vs fourteen institutions in app development (feasibility publication). Recorded on `known_biases` and `data_collectors`.
5. **Healthsheet currency** — the documentation's healthsheet answers reference v2.0.0 and 833 instances inconsistently, and its distribution answers describe Health Data Nexus rather than the current PhysioNet route. Recorded on `third_party_sharing` and `version_access`.
6. **MIT location** — Cambridge, MA vs Boston, MA within one publication. Recorded on `creators`.
7. **Dalhousie location** — given as Toronto, ON in the source. Recorded on `creators`.

---

## 6. Summary of net changes

| Action | Count |
|---|---|
| Slots removed (schema-invalid or unevidenced) | 4 (`distributions`, `credit_roles` ×17, `splits`, `annotation_analyses`) |
| Slots relocated to correct declared range | 2 (`resources` → `subsets`; `distributions` → `distribution_formats` + `file_collections`) |
| Values corrected to bundle text | 4 (Rudzicz, Ravitsky, README.md, `issued`) |
| Values removed as fabricated | 2 (`format: ZIP`, `instances[1].counts`) |
| `source_caveats` entries added | 5 (Ghosh conflict, Dalhousie anomaly, `publisher`, `issued`, `instances` counts) |
| Findings left as-is with recorded reason | 8 |