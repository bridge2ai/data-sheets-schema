# VOICE reconciliation report

Run label: `2026-11-25c_claude-fable-5-2-claudecode-generic-v9_rep2`
Method: `claudecode_release` — four-phase project agent, generic-v9 prompt, BASELINE arm (input documents only).
Agent runtime: Claude Code (release). Provider: Anthropic. Model: claude-fable-5-2.
Temperature: unknown (not observed from the agent runtime). No sampling setting was inferred.

| Artifact | Path |
|---|---|
| Full record | `data/d4d_concatenated/claudecode_release/2026-11-25c_claude-fable-5-2-claudecode-generic-v9_rep2/VOICE_d4d.yaml` |
| Core record | `data/d4d_concatenated/claudecode_release_core/2026-11-25c_claude-fable-5-2-claudecode-generic-v9_rep2/VOICE_d4d_core.yaml` |
| Coverage receipt | `data/d4d_concatenated/claudecode_release_core/2026-11-25c_claude-fable-5-2-claudecode-generic-v9_rep2/VOICE_coverage_receipt.yaml` |
| This report | `data/d4d_concatenated/claudecode_release_core/2026-11-25c_claude-fable-5-2-claudecode-generic-v9_rep2/VOICE_reconciliation.md` |

Inputs: bundle `data/preprocessed/concatenated/VOICE_preprocessed.txt` (md5 `9193c3cbe60b62a2fc0f704a2c4d23a3`, 5742 lines, 22 chunks), chunk manifest `data/preprocessed/chunks/VOICE_chunks.yaml`, source manifest `data/preprocessed/source_manifest.yaml`, full schema `src/data_sheets_schema/schema/data_sheets_schema_all.yaml`, core schema `src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml`.

## Referent

The declared scope (`download scope --project VOICE`) names the referent as the Bridge2AI-Voice dataset (adult), project-level DOI 10.13026/37yb-1t42, and declares the Bridge2AI-Voice Pediatric Dataset (10.13026/mf9s-5r03) related but distinct, to be expressed in the related-datasets slot. The record holds to that choice in both files: its identifier is the project-level DOI as a CURIE, it describes the dataset at its current PhysioNet release 3.1.0, and every fact taken from the pediatric release page sits in the single related-dataset entry. Facts about earlier releases (1.0, 1.1, 2.0, 2.0.1, 3.0.0) are stated as facts about those versions in the version-access, distribution-date and errata entries.

Source ranking used where sources differ (`download priority --project VOICE`): tier 1 the four PhysioNet release pages; tier 2 the project documentation, IRB protocol, data transfer and use agreement and documentation repository; tier 3 the feasibility publication and the audiomics viewpoint; tier 4 the NIH RePORTER record. The manifest marks the 3.0.0 page as superseded by the 3.1.0 page.

## Phase 1 — full record and coverage receipt

- `bundle chunk --check --strict` reported the selected chunk manifest current (22 canonical chunks) before any reading.
- All 22 chunks were read with the file-reading tool in manifest order; chunk c011 (334 long lines) took two windows, 2588–2757 and 2758–2921. A receipt entry was written after each chunk and before the next was opened.
- The first-pass receipt entries were written while the record layout was still open, so their slot paths were provisional. After the record was written, and before Phase 2, the receipt was rewritten once to the record's final slot paths using the chunks already read, keeping an entry for every chunk; a second small edit then re-addressed five list-valued slots at the list path the validator reads. The earlier writes and both corrections are in the session transcript. This is a correction of addresses, not of reading order.
- Statuses: 20 chunks `extracted`, 2 chunks `nothing_relevant` (c001 preamble, c004 publication-page navigation).
- Structure came from class `Dataset` in the full schema through the repository's own schema digest (`data_sheets_schema.schema_digest`) and direct inspection of class attributes; no prior D4D record was read as a template.
- Schema validation and term validation of the first full record: both passed.
- Strict receipt check before Phase 2: 22/22 chunks reviewed, 576/576 snippets verified, 881/881 receiptable slots with a receipt (128 exempt).

## Phase 2 — core derivation

One command, no model judgment (`derive core`). JSON emitted on the first derivation:

```json
{"derived": true, "rule": "shared slots copied from the full record; resources projected by id with full-only nested slots dropped; distributions built from file_collections (one per collection over the shared slots, total_bytes as bytes) and from each collection's File entries (one per file over the slots CoreDistribution and File share); dialect from the File entries when they agree on one value, else absent", "from": {"path": "data/d4d_concatenated/claudecode_release/2026-11-25c_claude-fable-5-2-claudecode-generic-v9_rep2/VOICE_d4d.yaml", "md5": "8610917db4f72f61a21f8ce1a3cf7610"}, "identity_slots": 79, "projected_slots": ["resources"], "distribution_slots": {"collection": ["compression", "conforms_to", "conforms_to_standard", "description", "id", "name", "notes", "path", "source_caveats"], "file": ["bytes", "compression", "conforms_to", "conforms_to_standard", "description", "encoding", "format", "hash", "id", "md5", "media_type", "name", "notes", "path", "sha256", "source_caveats"]}, "conditional": {"dialect": "derived only when every File-level dialect in the full record agrees on one value"}}
```

The derived core validated (`linkml-validate: No issues found`).

## Phase 3 — source and provenance audit

### Provenance

- Read history of this session: the provenance guard, the uniform rules, the executable playbook view, `d4d-agent.md`, the chunk manifest, the source manifest, the declared bundle (all 22 chunks), the full schema (class attributes and the schema digest), and three repository modules consulted to understand checker behavior (`receipts.py`, `grounding.py`, `report_claims.py`).
- No prior-run D4D record, evaluation or reconciliation report was read. The run's output directories already held other projects' files of the same label; their names appeared in one directory listing and none of them was opened.
- Every factual value in the record traces to the declared bundle; the two vocabulary terms on the recording instance (`B2AI_TOPIC:36`, `B2AI_SUBSTRATE:30`) are schema vocabulary chosen for what the bundle states (voice recordings; Parquet).

### Findings

Thirteen findings were recorded against the Phase 1 full record. Counted from the rows below: 13 in total, 0 high, 5 medium, 8 low. All 13 were corrected in the full record; none was left open.

| # | Severity | Slot (Phase 1 path) | Finding | Source | Correction in the full record |
|---|---|---|---|---|---|
| F1 | medium | `preprocessing_strategies[2]` | One entry merged two derived data types the release page lists separately (MFCC; Mel spectrogram) | physionet_3_1_0, c019 | Split into two entries |
| F2 | medium | `preprocessing_strategies[4]` | One entry merged OpenSMILE acoustic features with Parselmouth/Praat phonetic and prosodic features, listed separately by the release page | physionet_3_1_0, c019 | Split into two entries, each with its own software |
| F3 | medium | `subpopulations[0]` | A collective entry ("Disease cohort categories") stood where the sources name four cohorts and a control group | physionet_3_1_0 c018, c019; irb_protocol c011 | One entry per cohort (voice, neurological, mood, respiratory disorders) and one for controls; the remark about unequal distribution describes the set, not a member, and stays in `known_limitations[0]` |
| F4 | medium | `intended_uses[1]` | One entry merged four uses (pretraining, fine-tuning, benchmarking, validation) | project_documentation, c008 | One entry per use |
| F5 | medium | `discouraged_uses[0]` | One entry merged three applications (hiring decisions, insurance premium adjustments, surveillance) | project_documentation, c008, c009 | One entry per application, each carrying the stated reason |
| F6 | low | `external_resources[4]` | One entry joined the documentation site and the project website | project_documentation c007; physionet_3_1_0 c019; documentation_repository c022 | Documentation (site and its source repository) and website are separate entries |
| F7 | low | `data_collectors[0]` | A collective role stood for three roles the healthsheet describes separately | project_documentation, c009, c007 | Three entries: research team member, clinician, hospital staff |
| F8 | low | `collection_mechanisms[1].name` | Entry label was a plural class name | project_documentation, c008 | Relabeled "Recording hardware"; content unchanged |
| F9 | low | `preprocessing_strategies[6]` | SenseLab was attached to an entry about export and merging, a step no passage ties it to | project_documentation, c009 | Entry reworded as the processing toolkits, quoting the documentation's statement that all processing uses b2aiprep and SenseLab |
| F10 | low | `creators[11]`, `creators[12]`, `creators[14]` | Affiliations rest on documentation spellings that differ from the release page (Don Bolser, Jennifer Sui, Frank Rudzizc); the trust note sat only at the top level | project_documentation c008; physionet_3_1_0 c018 | Per-entry `source_caveats` added |
| F11 | low | `collection_mechanisms[2]` | Omission: countries of data collection | project_documentation, c009 ("USA and Canada") | Back-ported, with its receipt |
| F12 | low | `sampling_strategies[1]` | Omission: study-metadata eligibility (minimum age 18 years, maximum age 120 years, healthy volunteers) | project_documentation, c008 | Back-ported, with its receipts |
| F13 | low | `is_deidentified.deidentification_details` | Two statements lost their version qualifier: the documentation gives them under "Methods of De-identification for v3.0.0" | project_documentation, c009 | Qualifier restored in the value |

### Checks made without a finding

- Counts and their units: 833 is a count of participants in release 3.1 (release page) and is entered on the participant instance only. The per-file element counts in the feature-file descriptions are the 3.1.0 page's figures (for example n=29278 for the spectrogram file), not the 3.0.0 page's (n=29020). The documentation's "~61,937 voice-derived recordings" is stated for version 3.0 and sits in the version details, attributed to that version. No figure in the record is computed by the record.
- Plans kept as plans: the 10,000-voice and 30 000-participant targets, the semi-annual cadence, remote collection, Spanish-language collection and the Canadian ethics review are each stated in the source's tense with the source named. None is entered as the current state of the dataset.
- Principal investigator: the documentation names Yael Bensoussan and Olivier Elemento as co-principal investigators for the project; the RePORTER record and the study protocol name Bensoussan as principal investigator. Both are recorded; lead investigators are recorded as creators with their stated affiliations and are not promoted.
- Identifiers: the record id, `doi`, the latest-version DOI and the related-dataset target are all stated in the bundle. No organization or person registry identifier is supplied; the bundle states none. Persons given as objects carry fragments on the record's own id. Software the bundle names without an identifier carries a minted label on the record id; b2aiprep and SenseLab carry the repository URLs the bundle states.
- Enumerations: `data_use_permission` (general research use) restates the documentation's "intended solely for commercial and non-commercial research purposes"; `confidentiality_level` (restricted) is the release page's own word; the metadata collection's type is the page's own heading; the two identifier variables are called unique identifiers by the page. Bias types, limitation types and the features and phenotype collection types are left empty because no passage states the category.
- Stated absences are not entries: no predefined splits, no use repository, no data-subject impact analysis, no export controls, no third-party IP restrictions and the healthsheet's "no erratum" are recorded only in `source_caveats`.

### Judgment calls a reviewer should look at

- **Related dataset relation.** No passage names a typed relation between the adult and pediatric datasets. The adult release page points to the pediatric dataset ("is also available on PhysioNet"), and the manifest declares the relation's slot. The entry is kept with relationship type `references`, and its `source_caveats` says the type is the nearest reading of a cross-reference rather than a stated relation. Omitting the entry was the alternative.
- **Standard the content follows.** `conforms_to` (Brain Imaging Data Structure v1.9.0) and `conforms_to_standard` (BIDS) come from the project documentation's statement about converting the raw audio files and questionnaire data. The 3.1.0 release page does not name the standard. The top-level `source_caveats` says so.
- **Creators.** The 122 authors of the 3.1.0 release are entered one per entry, each with its own receipt; affiliations are given only for the 15 investigators whose affiliation the documentation's healthsheet states.
- **Publisher.** Left empty. The bundle names PhysioNet as publisher of the release but states no identifier for it in a declared form (it gives an RRID, a prefix the schema does not declare), and the slot takes an identifier.
- **Sensitive and confidential elements.** The documentation's healthsheet and its de-identification section disagree at the same rank about sensitive fields, and the healthsheet and the data transfer and use agreement disagree about confidentiality. Both sides are represented, with the disagreement in `source_caveats`; no boolean is set for confidential elements or content warnings.
- **Errata.** Three corrections reported in the release notes (3.1.0 parquet repair, 2.0.1 authorship corrections, 2.0 spectrogram reprocessing) are entered as errata.

## Phase 4 — re-derivation, checks, semantic review

Re-derivation after the Phase 3 corrections (`derive core --phase4-complete`), JSON emitted:

```json
{"derived": true, "rule": "shared slots copied from the full record; resources projected by id with full-only nested slots dropped; distributions built from file_collections (one per collection over the shared slots, total_bytes as bytes) and from each collection's File entries (one per file over the slots CoreDistribution and File share); dialect from the File entries when they agree on one value, else absent", "from": {"path": "data/d4d_concatenated/claudecode_release/2026-11-25c_claude-fable-5-2-claudecode-generic-v9_rep2/VOICE_d4d.yaml", "md5": "93744edb0a58b69d9de270219ff611f1"}, "identity_slots": 79, "projected_slots": ["resources"], "distribution_slots": {"collection": ["compression", "conforms_to", "conforms_to_standard", "description", "id", "name", "notes", "path", "source_caveats"], "file": ["bytes", "compression", "conforms_to", "conforms_to_standard", "description", "encoding", "format", "hash", "id", "md5", "media_type", "name", "notes", "path", "sha256", "source_caveats"]}, "conditional": {"dialect": "derived only when every File-level dialect in the full record agrees on one value"}}
```

Pair checker (`data_sheets_schema.d4d_pair_consistency`), exit 0:

```
PASS: 79 schema-identical slots; projected slots=['resources']; per-record slots (exempt, must differ)=['conforms_to_class', 'conforms_to_schema']
WARNING [semantic-review-required] $.file_collections <-> $.distributions: Phase 4 must semantically review related distribution content; deterministic matches=100 (3 at collection level, 97 at nested resource level), unmatched core distributions=[]
```

Other checks on the final pair:

| Check | Result |
|---|---|
| Full record, schema validation (`Dataset`) | No issues found |
| Full record, term validation | Validation passed |
| Core record, schema validation (`CoreDataset`) | No issues found |
| Core record, term validation | Validation passed |
| Grounding (`grounding.check_run`) | distinct identifiers: 1 grounded, 108 minted fragments, 0 absent |
| Receipts (`receipts check --strict`) after the Phase 3 corrections | 22/22 chunks reviewed; 592/592 snippets verified; 914/914 receiptable slots with a receipt (131 exempt); exit 0 |
| Scope (`download scope --check --strict`, both records) | neither record is about a dataset the project declares distinct; exit 0 |
| Core header | carries `# Sources:` naming the same-run full record and `# Phase 4 reconciliation: completed` |

Receipt diagnostics that are reported but not gated: 5 snippets bear on no token of the value they sit under (they are question lines or headings whose answer is a single word, for example the healthsheet's question about direct collection), and 31 entry receipts overlap a leaf receipt.

No checker finding required a change after re-derivation, so there was no repair phase.

## Semantic review

- `file_collections` ↔ `distributions` (the pair checker's `semantic-review-required` warning): the 3 collections and 97 files of the full record appear as 100 core distributions with the same ids, names, paths, descriptions, formats and media types; no core distribution is unmatched; the features files carry the 3.1.0 counts and the phenotype tree is the 3.1.0 layout — **reviewed: consistent**
- `total_file_count` / `total_size_bytes` against the entries beneath them: neither is populated in either record, and no collection carries a file count or byte total, because the bundle states no file sizes and does not enumerate the features folder's data dictionary files; there is nothing to disagree — **reviewed: consistent**
- `dialect` and `is_tabular` against the files: no file in the full record carries a dialect, so the core derives none; `is_tabular` is not populated in either record because no passage states it — **reviewed: consistent**
- Historical versus current release: the record's version, issue date, citation, file inventory and counts are those of release 3.1.0; statements about releases 1.0 through 3.0.0 sit only in the version details, the release dates and the errata, each attributed to its version; one de-identification statement had lost its v3.0.0 qualifier and was requalified in Phase 3 (F13) — **reviewed: corrected**

## Claims

| Slot | Change | Reason |
|---|---|---|
| `subpopulations.distribution` | Removed | The unequal-distribution statement is a remark about the set of cohorts, not the distribution of one cohort; it remains in the known-limitations entry that already carried it. Gone from the full record in Phase 3 and from the core on re-derivation. |

No other slot left either record. The ten top-level slots present in the full record and not in the core (`citation`, `collection_consents`, `collection_notifications`, `consent_revocations`, `direct_collection`, `file_collections`, `participant_compensation`, `participant_privacy`, `third_party_sharing`, `variables`) are the projection's doing, not edits: the core is derived and was never edited by hand.

## Files changed

- Full record: written in Phase 1; edited in Phase 3 for findings F1–F13.
- Coverage receipt: written chunk by chunk in Phase 1; re-addressed once to final paths before Phase 2; edited in Phase 3 so that every corrected or back-ported value has its receipt in the existing entry of the chunk the passage sits in.
- Core record: derived in Phase 2; re-derived in Phase 4 with `--phase4-complete`. Never edited by hand.
- This report: written in Phase 4.

Scratch files outside the three declared outputs and the receipt, disclosed: `.temp/playbook_view_VOICE_rep2.md` (the executable playbook view, saved to read it in windows) and `.temp/schema_digest_Dataset_VOICE_rep2.txt` (the repository's schema digest for `Dataset`). Both are structural reading aids in the checkout's ignored scratch directory and hold no dataset facts. A few inline, unsaved inspections were run with the registered interpreter: printing class attributes and slot descriptions from the full schema, listing the leaves the receipt validator counted as lacking a receipt, and counting top-level slots.

## Commands

```
.venv/bin/python -m data_sheets_schema.cli agents playbook --relative-toolchain
.venv/bin/python -m data_sheets_schema.cli bundle chunk --bundle data/preprocessed/concatenated/VOICE_preprocessed.txt --chunk-manifest data/preprocessed/chunks/VOICE_chunks.yaml --manifest data/preprocessed/source_manifest.yaml --check --strict
.venv/bin/python -m data_sheets_schema.cli download scope --manifest data/preprocessed/source_manifest.yaml --project VOICE
.venv/bin/python -m data_sheets_schema.cli --manifest data/preprocessed/source_manifest.yaml download priority --project VOICE
.venv/bin/python -c 'from linkml.validator.cli import cli; cli()' -s src/data_sheets_schema/schema/data_sheets_schema_all.yaml -C Dataset <full>
.venv/bin/python -c 'from linkml_term_validator.cli import main; main()' validate-data <full> --schema src/data_sheets_schema/schema/data_sheets_schema_all.yaml --target-class Dataset
.venv/bin/python -m data_sheets_schema.cli --manifest data/preprocessed/source_manifest.yaml receipts check --method claudecode_release --label 2026-11-25c_claude-fable-5-2-claudecode-generic-v9_rep2 --project VOICE --bundle data/preprocessed/concatenated/VOICE_preprocessed.txt --chunk-manifest data/preprocessed/chunks/VOICE_chunks.yaml --strict
.venv/bin/python -m data_sheets_schema.cli derive core --full <full> --out <core>
.venv/bin/python -m data_sheets_schema.cli derive core --full <full> --out <core> --phase4-complete
.venv/bin/python -m data_sheets_schema.d4d_pair_consistency --full <full> --core <core>
.venv/bin/python -c 'from linkml.validator.cli import cli; cli()' -s src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml -C CoreDataset <core>
.venv/bin/python -c 'from linkml_term_validator.cli import main; main()' validate-data <core> --schema src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml --target-class CoreDataset
.venv/bin/python -m data_sheets_schema.cli download scope --manifest data/preprocessed/source_manifest.yaml --project VOICE --check --record <full> --record <core> --strict
grounding.check_run and report_claims.check_report, as the playbook's inline programs give them
```

One `download priority` call was first tried with a `--manifest` option the subcommand does not take and was re-run with the root `--manifest` option, as the launch instruction prescribes.

## Final results

- Full record: 70 populated top-level slots, 1736 lines (informational). Valid against `Dataset`; terms valid.
- Core record: 63 populated top-level slots, 1360 lines (informational). Valid against `CoreDataset`; terms valid.
- Pair consistency: PASS, 79 schema-identical slots, one semantic-review warning, reviewed above.
- Phase 3: 13 findings (0 high, 5 medium, 8 low), all corrected in the full record. Phase 4: no repair needed.
- Reconciliation outcome: completed; the core is the projection of the audited full record.

## Provenance record

After this report was first written, four steps were run in order, each exiting 0:

```
.venv/bin/python -m data_sheets_schema.cli provenance record --project VOICE --method claudecode_release --label 2026-11-25c_claude-fable-5-2-claudecode-generic-v9_rep2 ... (the registered line, with one --phase flag per phase performed)
.venv/bin/python -m data_sheets_schema.cli --manifest data/preprocessed/source_manifest.yaml receipts check ... --strict --write
.venv/bin/python -m data_sheets_schema.cli --manifest data/preprocessed/source_manifest.yaml runs validate --method claudecode_release --project VOICE --label 2026-11-25c_claude-fable-5-2-claudecode-generic-v9_rep2
.venv/bin/python -m data_sheets_schema.cli --manifest data/preprocessed/source_manifest.yaml runs check --method claudecode_release --label 2026-11-25c_claude-fable-5-2-claudecode-generic-v9_rep2 --project VOICE --strict
```

- Phases recorded: `generate_full`, `derive_core`, `source_audit`, `reconcile` (one re-derive and re-check pass), `report`. No `repair` or `report_after_repair` phase was recorded because none ran. No per-phase observation was recorded: one agent ran all four phases in one context.
- The recorder reported: pair ok, report findings 0, ungrounded identifiers 0, British spellings 0, receipts 22/22 chunks and 592/592 snippets. It recorded 70 slots for the full record and 63 for the core, `record_mode: live`, and `receipt_expected: true` from the registered specification.
- The recorder marks reasoning effort as asserted by the launcher, not observed, and temperature as not observed.
- `runs check --strict` first failed for want of a validation block, as the playbook describes for a run never validated; `runs validate` then recorded the run valid and the gate passed.

Because the provenance record pins this report's bytes, the four steps are run again after this section was added. The run's final message states the outcome of that second pass; this section describes the first.

## Limits of this report

- Temperature is unknown and was not observed. Reasoning effort is whatever the launcher's registered specification asserts; this agent did not observe it. Token usage and timing are not estimated here; the whole-run observation belongs to the orchestrator's transcript audit (`agentic_observed`), which this agent did not run.
- The receipt validator establishes that each snippet is verbatim in its chunk and that each populated leaf has a receipt. It does not establish that a snippet entails the value it sits under, or that the two chunks marked `nothing_relevant` held nothing; those remain review work.
- Whether `references` is an acceptable type for the related-dataset entry is a judgment this run made and flagged rather than settled.
