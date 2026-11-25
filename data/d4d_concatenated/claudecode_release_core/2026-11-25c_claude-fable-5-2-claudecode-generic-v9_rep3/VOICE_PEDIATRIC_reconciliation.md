# VOICE_PEDIATRIC reconciliation report

- Version label: `2026-11-25c_claude-fable-5-2-claudecode-generic-v9_rep3`
- Method: `claudecode_release`; arm: BASELINE (input documents only)
- Mode: four-phase project agent, generic-v9 prompt
- Agent runtime: Claude Code (release); provider: Anthropic; model: claude-fable-5-2
- Temperature: unknown (not observed from the agent runtime). No sampling setting was inferred from the prompt, the model name or an effort level.
- Full record: `data/d4d_concatenated/claudecode_release/2026-11-25c_claude-fable-5-2-claudecode-generic-v9_rep3/VOICE_PEDIATRIC_d4d.yaml`
- Core record: `data/d4d_concatenated/claudecode_release_core/2026-11-25c_claude-fable-5-2-claudecode-generic-v9_rep3/VOICE_PEDIATRIC_d4d_core.yaml`
- Coverage receipt: `data/d4d_concatenated/claudecode_release_core/2026-11-25c_claude-fable-5-2-claudecode-generic-v9_rep3/VOICE_PEDIATRIC_coverage_receipt.yaml`
- Source bundle: `data/preprocessed/concatenated/VOICE_PEDIATRIC_preprocessed.txt` (md5 `0350223711484a63c21b2dd57af6f4c9`, 13 chunks)
- Chunk manifest: `data/preprocessed/chunks/VOICE_PEDIATRIC_chunks.yaml` (`bundle chunk --check --strict`: current, 13 canonical chunks)
- Source manifest: `data/preprocessed/source_manifest.yaml`

## Referent

The declared scope names the referent as the Bridge2AI-Voice Pediatric Dataset (project-level DOI `https://doi.org/10.13026/mf9s-5r03`) and declares the adult Bridge2AI-Voice dataset distinct, to be expressed through `related_datasets`.

The record describes **release 1.1.0 of the Bridge2AI-Voice Pediatric Dataset as published on PhysioNet**, the release the highest-ranked source in the bundle documents. Its `id` is the release DOI the PhysioNet page states for version 1.1.0, written as the declared CURIE `doi:10.13026/h995-bt35`; the project-level DOI is carried in `version_access.latest_version_doi`. Both records hold to this referent. The adult dataset appears only in `related_datasets[0]`.

Consequence for the evidence: three of the six sources in the bundle (the documentation site, the data acquisition protocol, the data transfer and use agreement) are about the Bridge2AI-Voice project or its adult dataset rather than about the pediatric release. From those sources only passages that name the pediatric cohort, pediatric participants or pediatric data, or that designate roles and funding for the project that produced the dataset, were used; each such value says in its own text which document states it. The documentation's datasheet-style sections describe the adult dataset (versions 2.0.0 and 3.0) and were not used for the referent's slots.

## Phase 1 - full generation

- Structure derived from class `Dataset` in `src/data_sheets_schema/schema/data_sheets_schema_all.yaml`.
- Every chunk was read with the file-reading tool in manifest order and its receipt entry written before the next chunk was read. Slot paths in the receipt were then aligned with the drafted record, and receipts for composed entry names were added after the draft; those are post-draft receipts.
- Chunk dispositions: 10 `extracted` (c002 to c011), 3 `nothing_relevant` (c001 preamble, c012 closing clauses of the agreement template, c013 documentation-repository README).
- Schema validation: `No issues found`. Term validation: passed.
- Strict receipt check before Phase 2: 13/13 chunks reviewed, 443/443 snippets verified, 355/355 slots with a receipt (34 exempt), exit 0.

## Phase 2 - core derivation

Derived by `derive core` from the validated Phase 1 full record; no model judgment. JSON emitted by the first derivation:

```json
{"derived": true, "rule": "shared slots copied from the full record; resources projected by id with full-only nested slots dropped; distributions built from file_collections (one per collection over the shared slots, total_bytes as bytes) and from each collection's File entries (one per file over the slots CoreDistribution and File share); dialect from the File entries when they agree on one value, else absent", "from": {"path": "data/d4d_concatenated/claudecode_release/2026-11-25c_claude-fable-5-2-claudecode-generic-v9_rep3/VOICE_PEDIATRIC_d4d.yaml", "md5": "4de86064200bbe2c05b1b26a737846be"}, "identity_slots": 79, "projected_slots": ["resources"], "distribution_slots": {"collection": ["compression", "conforms_to", "conforms_to_standard", "description", "id", "name", "notes", "path", "source_caveats"], "file": ["bytes", "compression", "conforms_to", "conforms_to_standard", "description", "encoding", "format", "hash", "id", "md5", "media_type", "name", "notes", "path", "sha256", "source_caveats"]}, "conditional": {"dialect": "derived only when every File-level dialect in the full record agrees on one value"}}
```

The derived core validated against `CoreDataset` (`No issues found`).

## Phase 3 - source and provenance audit

### Provenance boundary

- Factual inputs read: the declared bundle, the chunk manifest, the source manifest (scope, ranking and naming declarations), the two schema files, and the repository instructions (`.claude/agents/d4d-provenance-guard.md`, `.claude/commands/d4d-full-core.md` through its executable view, `.claude/commands/d4d-uniform-rules.md`, `.claude/commands/d4d-agent.md`, `notes/receipts_pattern_2026-08-27.md`).
- No prior full or core D4D record, evaluation or reconciliation report was read, opened or searched. Nothing under `data/d4d_concatenated/` was read other than this run's own three outputs and its receipt.
- No web content was fetched.
- The source manifest declares no `naming` entry for VOICE_PEDIATRIC; proper nouns are written as the sources write them.

### Source conflicts and their handling

| Subject | What the sources state | Handling |
|---|---|---|
| Recording count | Abstract: 23,533 recordings; five Parquet files `n=23533`, four `n=23532` | Not a conflict: the page states some files could not generate certain features. `instances[0].counts` carries 23533; both per-file figures are kept in the file descriptions and in `missing_data_documentation` and `source_caveats`, as the record's own count of four and five |
| Principal investigator | Protocol title page and NIH RePORTER: Yael Bensoussan; documentation: Bensoussan and Olivier Elemento are co-principal investigators for the project | Compatible. Both are recorded under `principal_investigator`, each with the sources named in `source_caveats` |
| Affiliation of Jordan Lerner-Ellis | Protocol: Mount Sinai Hospital; documentation: Sinai Health (same manifest rank) | Both recorded as separate `affiliations` entries |
| Grant number | PhysioNet: 3OT2OD032720-01S1; NIH RePORTER page: 3OT2OD032720-01S3, core OT2OD032720 | Not a conflict: different supplements of one core project. The grant the dataset page cites is recorded; the other is named in `funders[0].source_caveats` |
| File names | Data Description: `torchaudio_spectrograms.parquet`, `torchaudio_mel_spectrograms.parquet`; Usage Notes: `torchaudio_spectrogram.parquet`, `torchaudio_mel_spectrogram.parquet` | Same source. The Data Description names are used; the difference is in `source_caveats` |

### Findings

Seven findings were recorded against the Phase 1 full record. Severity subtotals, counted from the entries below: 1 medium, 6 low, 0 high.

| # | Severity | Slot | Finding | Correction |
|---|---|---|---|---|
| 1 | medium | `participant_compensation[0]` | The only supporting passage (protocol, "Compensation will be provided to the adult population only") is about the adult population and supports an entry for this dataset only by inferring an absence | Entry removed from the full record; its receipt removed |
| 2 | low | `participant_privacy[0].privacy_techniques` | The sentence on the unique study identification number is not attested by the source in a privacy role | Sentence deleted from this value (the fact stays in `collection_consents[0].consent_details`); its receipt removed |
| 3 | low | `intended_uses[0].description` | Added the qualifier "in pediatric voice and speech", which the passage does not state | Trimmed to the passage's own reach |
| 4 | low | `preprocessing_strategies[1].preprocessing_details` | "time-varying features" is the wording of a documentation passage about the consortium's feature-only dataset, not of the pediatric page | Reworded to "The Parquet feature files comprise" |
| 5 | low | `missing_data_documentation[0].missing_data_patterns`, `source_caveats` | The counts of four and five files were stated without marking them as the record's own computation | Restated as the record's own count with the files named; each input passage receipted |
| 6 | low | `raw_sources[0].raw_data_details` | Evidence commentary about the agreement template sat in a content field, and the template does not name the pediatric cohort | Sentence moved from `raw_sources[0].raw_data_details` to `raw_sources[0].source_caveats`, with the limitation stated; receipts re-addressed |
| 7 | low | `file_collections[0].resources[7].description` | Named `torchaudio_pitch` as the referent of the source's "than before" | Reworded to keep the source's own reach |

No source-supported omission was back-ported. After the corrections the full record re-validated (schema: `No issues found`; terms: passed) and the strict receipt check passed (13/13 chunks, 451/451 snippets verified, 354/354 slots with a receipt, 34 exempt).

### Considered and left out

These were examined against the bundle and deliberately not populated:

- `publisher`: the sources name PhysioNet and give its RRID, but the schema declares no prefix for that identifier and no source states an identifier in a declared form for PhysioNet as an organization.
- `is_deidentified`, `sensitive_elements`, `confidential_elements`, `discouraged_uses`, `prohibited_uses`, `known_biases`, `known_limitations`, `updates`, `retention_limit`, `maintainers`, `existing_uses`, `collection_timeframes`, `labeling_strategies`: the only passages are in the documentation's sections about the adult dataset, or in the footer of the PhysioNet site about the platform itself.
- `data_collectors`: the sources state where participants were enrolled and that pediatric collection happens only at pediatric sites, but no passage names who collected the data.
- `raw_data_sources.raw_data_format`, `conforms_to`, `is_tabular`, `language`, `total_file_count`, `total_size_bytes`: no passage states them for the release.
- `related_datasets[0].relationship_type`: no source names the relation between the two datasets. The value `references` records the one relation the evidence shows, the pediatric page's note pointing to the adult dataset; this is stated in the entry's `source_caveats`.
- Affiliations for creators the protocol lists on continuation rows without an institution (Alexander Gelbard) and for a documentation name whose spelling differs from the author list (Jennifer Sui / Jennifer Siu).
- The terms of the data transfer and use agreement template: it governs controlled-access data and does not name the pediatric cohort.

## Phase 4 - re-derivation, checks, report

### Re-derivation

`derive core --phase4-complete` on the corrected full record (md5 `2f6d7c205bce61a12d0879c8a10b12cc`): derived, `linkml-validate: No issues found`. The core header carries `# Sources:` naming the same-run full record and `# Phase 4 reconciliation: completed`.

### Deterministic checks

| Check | Result |
|---|---|
| Full schema validation (`Dataset`) | No issues found |
| Full term validation | passed |
| Core schema validation (`CoreDataset`) | No issues found |
| Core term validation | passed |
| Pair consistency | PASS: 79 schema-identical slots; projected slots `resources`; per-record slots `conforms_to_class`, `conforms_to_schema`; 1 warning (`semantic-review-required`) |
| Identifier grounding | grounded 2, minted_fragment 22, absent 0 |
| Scope check (`--strict`) | 2 records checked; none is about a dataset its project declares distinct |
| Strict receipt check | 13/13 chunks reviewed, 451/451 snippets verified, 354/354 slots with a receipt (34 exempt) |

No checker reported a finding that required a change, so no repair phase ran.

## Claims

| Slot | Action | Reason |
|---|---|---|
| `participant_compensation` | Removed | Phase 3 finding 1: the supporting passage is about the adult population |

## Semantic review

- `file_collections` <-> `distributions` (pair checker warning `semantic-review-required`, 15 deterministic matches: 3 collections, 12 files, no unmatched core distribution): each core distribution carries the id, name, description, path, format and media type of the collection or file it was projected from, and no distribution states content the full record lacks. reviewed: consistent
- `total_file_count` and `total_size_bytes` against the entries beneath them: neither is populated, and no collection carries `file_count` or `total_bytes`, because the sources state no totals; the page names eleven feature files and one phenotype file and says each has a JSON data dictionary, which is not a file total. reviewed: consistent
- `dialect` and `is_tabular` against the files: no file carries a `dialect`, the core derives none, and `is_tabular` is not asserted for a release that mixes Parquet tensor files with tab-separated files. reviewed: consistent
- Historical versus current release: the record's own slots describe release 1.1.0; release 1.0.0 appears only in `version_access.versions_available` and `distribution_dates`, each labeled with its version, and the documentation's statements about adult releases 2.0.0, 3.0 and 3.1.0 appear only in `related_datasets[0]`. reviewed: consistent
- Subject of each kept value (uniform rule on the referent): every value taken from the protocol or the documentation names its source in its own text and is limited to passages about the pediatric cohort or about the project that produced the dataset; Phase 3 findings 1, 4 and 6 are the corrections this review produced. reviewed: corrected

## Files changed

- Written: the full record, the core record (derived twice, never edited by hand), the coverage receipt, this report.
- A scratch copy of the executable playbook view was written under `.temp/` for reading.

## Commands

```
.venv/bin/python -m data_sheets_schema.cli agents playbook --relative-toolchain
.venv/bin/python -m data_sheets_schema.cli bundle chunk --bundle data/preprocessed/concatenated/VOICE_PEDIATRIC_preprocessed.txt --chunk-manifest data/preprocessed/chunks/VOICE_PEDIATRIC_chunks.yaml --manifest data/preprocessed/source_manifest.yaml --check --strict
.venv/bin/python -m data_sheets_schema.cli download scope --manifest data/preprocessed/source_manifest.yaml --project VOICE_PEDIATRIC
.venv/bin/python -m data_sheets_schema.cli --manifest data/preprocessed/source_manifest.yaml download priority --project VOICE_PEDIATRIC
.venv/bin/python -c 'from linkml.validator.cli import cli; cli()' -s src/data_sheets_schema/schema/data_sheets_schema_all.yaml -C Dataset <full>
.venv/bin/python -c 'from linkml_term_validator.cli import main; main()' validate-data <full> --schema src/data_sheets_schema/schema/data_sheets_schema_all.yaml --target-class Dataset
.venv/bin/python -m data_sheets_schema.cli --manifest data/preprocessed/source_manifest.yaml receipts check --method claudecode_release --label 2026-11-25c_claude-fable-5-2-claudecode-generic-v9_rep3 --project VOICE_PEDIATRIC --bundle data/preprocessed/concatenated/VOICE_PEDIATRIC_preprocessed.txt --chunk-manifest data/preprocessed/chunks/VOICE_PEDIATRIC_chunks.yaml --strict
.venv/bin/python -m data_sheets_schema.cli derive core --full <full> --out <core>
.venv/bin/python -m data_sheets_schema.cli derive core --full <full> --out <core> --phase4-complete
.venv/bin/python -c 'from linkml.validator.cli import cli; cli()' -s src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml -C CoreDataset <core>
.venv/bin/python -c 'from linkml_term_validator.cli import main; main()' validate-data <core> --schema src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml --target-class CoreDataset
.venv/bin/python -m data_sheets_schema.d4d_pair_consistency --full <full> --core <core>
.venv/bin/python -c "... data_sheets_schema.grounding.check_run ..."   (the playbook's identifier grounding program)
.venv/bin/python -m data_sheets_schema.cli download scope --manifest data/preprocessed/source_manifest.yaml --project VOICE_PEDIATRIC --check --record <full> --record <core> --strict
```

## Final results

- Full record: valid against `Dataset`; 44 populated top-level slots; 817 lines (informational).
- Core record: valid against `CoreDataset`; 40 populated top-level slots; 637 lines (informational).
- Reconciliation outcome: Phase 3 recorded 7 findings (1 medium, 6 low), all corrected in the full record; the core was re-derived; the pair checker passed with its one semantic-review warning reviewed; no repair phase was needed.
- Not measured by this run: sampling temperature, token usage and timing. The run did not observe them and states none.
