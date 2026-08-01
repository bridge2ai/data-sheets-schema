# VOICE — Phase 4 Reconciliation Report

**Project:** VOICE (Bridge2AI-Voice)
**Version label:** `2026-07-31_claude-opus-5-api-generic_rep2`
**Arm:** CRATE-ONLY (RO-Crate evidence alone; document corpus withheld)
**Declared input bundle:** `data/preprocessed/concatenated/VOICE_crate_only.txt`
**Records reconciled:**
`data/d4d_concatenated/claudecode_agent_crate_only/2026-07-31_claude-opus-5-api-generic_rep2/VOICE_d4d.yaml` (full)
`data/d4d_concatenated/claudecode_agent_crate_only_core/2026-07-31_claude-opus-5-api-generic_rep2/VOICE_d4d_core.yaml` (core)

---

## 1. Referent

Both records describe a single referent, held consistently:

> **The Bridge2AI-Voice v3.0.0 feature-only public release**, distributed by PhysioNet under DOI `10.13026/k81f-qr68` and packaged in the crate as `ark:59853/rocrate-b2ai-voice-3.0.0`.

This is the de-identified, derived-feature tier — spectrograms, mel spectrograms, MFCCs, SPARC articulatory/pitch/loudness/periodicity features, phonetic posteriorgrams, static openSMILE/Praat summaries, and tabular phenotype TSVs with JSON data dictionaries. The underlying raw voice waveforms are **not** the referent: the bundle states they are withheld from this release and reachable only through a separate controlled-access process. They are described in the records as a raw source and as an access tier, never as dataset content.

The prior static snapshots (v1.0, v1.1, v2.0.0, v2.0.1) are likewise not the referent; they are described only within the maintenance/versioning narrative.

---

## 2. What the audit found

Seventeen findings, **none critical**: one medium, thirteen low, three informational.

The audit confirmed that the substantive body of both records is traceable to the declared bundle. Specifically verified against source: the 833-participant scope across five North American sites; the `rai:*` blocks covering limitations, biases, use cases, collection, preprocessing, imputation, manipulation, annotation protocol and annotation analysis; the nine feature Parquet entities with their byte-exact `contentSize` and `sha256` values; the phenotype table families and their column inventories; the two `b2aiprep`-driven computations (`VOICE Features Processing`, `VOICE Phenotype Ingest`); the USF IRB record with contact and address; the Hastings Center ethical review; the PhysioNet licence and DUA URLs; the confidentiality level; and the full five-release version history.

No fabricated entities were found. No evidence of prior-D4D reuse was found. All required object keys were populated in every object instance (`DataSubset.id`, `FileCollection.id`, `VariableMetadata.variable_name`, `RawDataSource.source_description`, `Dataset.id`).

Positive verification worth recording: every entry under the full record's `anomalies` slot corresponds to a real defect in the crate JSON-LD and was re-checked line by line — the duplicated `name` values (`sparc_loudness.parquet` used for both the loudness and periodicity entities; `torchaudio_spectrogram.parquet` used for both the pitch and spectrogram entities), the duplicated `@id` `ark:59853/b2ai-voice-schema-phenotype-confounders` carrying two different schema names and identical column lists, the duplicated `VOICE Questionnaire Tables` name across the questionnaire and task group entities, the inconsistent `participant_id` typing (`string` in most feature schemas, `integer` in the spectrogram and phenotype schemas), the string/number typing drift across checkbox columns, and the placeholder `"a datafile description"` / `"A Dataset description"` values alongside empty `completeness` and `irbProtocolId`. These are documented anomalies of the metadata record, correctly scoped as such rather than as data-content anomalies.

The remaining findings cluster into four kinds: (a) scalars carrying an inference the bundle does not state; (b) one file-level property promoted to dataset level; (c) one unsupported boolean that also created a full/core contradiction; (d) cross-record asymmetries.

---

## 3. Changes made

### Full record

| Slot | Action | Reason |
|---|---|---|
| `status` | **Removed** (`published`) | Not stated anywhere in the bundle. The crate supplies `datePublished`, a PhysioNet publisher, and `"published": true` on the per-file `EVI:Schema` entities — none of which is a dataset lifecycle status. Under *prefer omission over inference*, an unstated status is correctly absent. |
| `conforms_to_schema` | **Removed** (`https://json-schema.org/draft/2020-12/schema`) | This `$schema` value belongs to the packaged per-file column schemas, not to the dataset. Promoting a file-level property to the dataset level misattributes it. The dataset-level conformance that *is* stated — RO-Crate 1.2 — remains recorded in `conforms_to`. |
| `relationships` | **Reworded** | The original text asserted the participant→session→task→recording hierarchy was "one-to-many at each level". The bundle supports the existence of the linkage (`participant_id`, `session_id`, `recording_acoustic_task_id`, `recording_session_id`, `session_assigned_tasks`) and explicitly supports multiple sessions per participant ("a subset completing repeated sessions"; "participants may have repeated visits with differing responses"). It never states cardinality at the other levels. The entry now describes the identifier-based linkage and the stated repeat-session fact, and drops the unstated cardinality claim. |
| `at_risk_populations` | **Reworded** | The original conflated two tables. Corrected attribution: `ef_any_cognitive_challeges`, `ef_any_hearing_related_req`, `ef_any_vision_related_req`, `ef_any_physical_challenges`, the `ef_*_a11y_options___*` sets and `ef_completed_by___*` sit on the **Enrollment form**; `session_completed_by___just_me` / `___someone_else` sit on the **Session** table. Both facts survive; only the source attribution changed. |

**Net effect on the full record: two slots removed, two slot values reworded.**

### Core record

| Slot | Action | Reason |
|---|---|---|
| `is_tabular` | **Removed** (`true`) | The single medium-severity finding. The bundle never asserts tabularity, and the release is mixed: the phenotype and `static_features.tsv` files are genuinely tabular, while the nine feature Parquet files store dense multi-frame tensors serialised into a single column alongside `n_frames`. Asserting `true` flattens that distinction. Removal also resolves a full/core contradiction, since the full record already omitted the slot. |
| `page` | **Removed** (`https://b2ai-voice.org/contact-us/`) | The crate records this URL under `contact`, not as a landing page. The full record omitted it; the core record populated it. Harmonised downward to the conservative reading. |
| `conforms_to_schema` | **Removed** | Same reason as the full record; removed in both to keep the pair consistent. |

**Net effect on the core record: three slots removed.**

---

## 4. What was left as-is, and why

**`language: en` (both records).** Retained. The bundle does not declare a language metadata field, but it states the inclusion criterion "fluent English speakers", states that "early releases focus on English, with Spanish protocols planned but not yet fully represented", and carries `ef_primary_language`, `ef_select_language` and `selected_language` columns. This is a claim about the content the dataset actually contains, supported by two independent statements in `rai:dataBiases`, rather than a guess. Retained in both records identically.

**`publisher` coerced to `https://physionet.org` (both records).** Retained. The bundle gives the literal string `"PhysioNet"` plus PhysioNet content, licence and DUA URLs, but not this bare origin URI. The slot range is `uriorcurie`, so a string cannot be carried verbatim. The coercion resolves to the correct, unambiguous entity and is recorded here as a coercion rather than a source quotation.

**`keywords` including `clinical` and `phenotype` (both records).** Retained. Both terms appear verbatim in the bundle, on the keyword lists of the feature and phenotype file entities rather than on the root dataset. Since those files are constituents of the referent and keywords serve discovery, the promotion is low-risk and was applied identically to both records.

**`total_size_bytes` (omitted, full).** Left omitted. The crate states `contentSize: "12.9 GB"`, which is not byte-precise, and the eleven byte-exact file sizes do not sum to the whole release. Converting "12.9 GB" to an integer byte count would require choosing a decimal or binary interpretation the bundle does not specify. The stated figure is preserved as narrative text rather than as a fabricated integer.

**`total_file_count` (omitted, full).** Left omitted. The bundle offers two counts at two different scopes — `ai_ready_score.json` reports "11/17" files for checksum coverage and separately "15 dataset(s) documented", while the crate's `EVI#outputs` summary reports `count: 15`. Seventeen crate-registered file entities, fifteen output entities and an unknown number of physical files inside the group entities (`VOICE Diagnosis Tables`, `VOICE Enrollment Tables`, `VOICE Questionnaire Tables`) cannot be reconciled into one defensible integer. Omission is the correct answer.

**`related_datasets` (omitted, both).** Left omitted. `DatasetRelationship` requires `target_dataset`, and the bundle gives no identifiers for the prior snapshots — only version strings (1.0, 1.1, 2.0.0, 2.0.1) and the general statement that each has an associated DOI. The v3.0.0 DOI is the only one actually present. The controlled-access raw-audio tier likewise has no identifier. Rather than mint targets, the version lineage and the two-tier access structure are carried in the maintenance, version-access and third-party-sharing narratives of the full record.

**`participant_privacy`, `direct_collection`, `third_party_sharing` (present in full, absent from core).** Left as-is. These three were checked against the `CoreDataset` slot inventory in `data_sheets_schema_core_all.yaml`; they are not part of it. The asymmetry is therefore structural to the core schema, not an omission defect. Their substance is fully carried in the full record, and the core record retains the privacy-relevant content that its own inventory admits — `is_deidentified` and `sensitive_elements` together preserve the de-identification procedures, the residual re-identification risk, the biometric status of the withheld raw audio, and the DUA-encoded prohibitions.

**`creators` representation difference.** Left as-is. The full record enumerates all 117 authors as individual `Creator` objects; the core record collapses them into two `Creator` objects — a summary entry and one carrying the complete list — as a density adaptation appropriate to a core record. Both are faithful to the crate `author` array and both are traceable. The uniform decision rule on consistency governs the *referent*, not the structural granularity of a repeated slot, so no change was forced.

**`anomalies` (full).** Left as-is after line-by-line re-verification against the crate JSON-LD. All six entries are real and correctly scoped as metadata defects.

**`is_deidentified`, `sensitive_elements`, `ethical_reviews`, `human_subject_research`, `license_and_use_terms`, `known_biases`, `known_limitations`, `preprocessing_strategies`, `machine_annotation_tools`, `annotation_analyses`, `missing_data_documentation`, `imputation_protocols`.** Left as-is. Each maps directly onto a named `rai:*` field or an explicit crate property (`ethicalReview`, `irb`, `humanSubjectResearch`, `humanSubjectExemption`, `fdaRegulated`, `deidentified`, `confidentialityLevel`, `dataGovernanceCommittee`, `license`, `conditionsOfAccess`, `copyrightNotice`). No inference was involved.

---

## 5. Cross-record consistency after reconciliation

- Same referent in both records, stated identically.
- No slot now carries contradictory values across the two records. The former `is_tabular` contradiction (core `true` vs. full omitted) and the `page` asymmetry are resolved by removal from the core record.
- `conforms_to_schema` is now absent from both.
- Remaining full/core differences are (a) slots the core schema does not define, and (b) the deliberate `creators` granularity difference — both documented above.

---

## 6. Validation

Both records were re-validated after the Phase 4 edits:

```
poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_all.yaml \
  -C Dataset data/d4d_concatenated/claudecode_agent_crate_only/2026-07-31_claude-opus-5-api-generic_rep2/VOICE_d4d.yaml

poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml \
  -C CoreDataset data/d4d_concatenated/claudecode_agent_crate_only_core/2026-07-31_claude-opus-5-api-generic_rep2/VOICE_d4d_core.yaml
```

Both pass. No required key was disturbed by the removals; every edited slot was optional, and the two reworded values are free-text fields within objects whose required keys are unchanged.

---

## 7. Outcome

**Reconciled.** Five slot removals (two full, three core) and two rewordings in the full record, all in the direction of removing unstated inference or correcting misattribution. Eleven findings were adjudicated as leave-as-is with the reasoning recorded above. No finding required adding content, and no finding indicated fabrication, referent drift, or prior-D4D contamination.