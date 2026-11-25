# VOICE reconciliation report

- Version label: `2026-11-25c_claude-fable-5-2-claudecode-generic-v9_rep1`
- Agent runtime: Claude Code (release); provider: Anthropic; model: claude-fable-5-2
- Mode: four-phase project agent, generic-v9 prompt; arm: BASELINE (input documents only)
- Source bundle: `data/preprocessed/concatenated/VOICE_preprocessed.txt` (md5 `9193c3cbe60b62a2fc0f704a2c4d23a3`, 22 chunks under `data/preprocessed/chunks/VOICE_chunks.yaml`)
- Source manifest: `data/preprocessed/source_manifest.yaml`
- Full record: `data/d4d_concatenated/claudecode_release/2026-11-25c_claude-fable-5-2-claudecode-generic-v9_rep1/VOICE_d4d.yaml`
- Core record: `data/d4d_concatenated/claudecode_release_core/2026-11-25c_claude-fable-5-2-claudecode-generic-v9_rep1/VOICE_d4d_core.yaml`
- Coverage receipt: `data/d4d_concatenated/claudecode_release_core/2026-11-25c_claude-fable-5-2-claudecode-generic-v9_rep1/VOICE_coverage_receipt.yaml`
- Temperature: unknown (not observed from the agent runtime). The workflow does not observe the native runtime's sampling settings; nothing in this report or in either record infers one.
- Reasoning effort: not observed by the agent; whatever the recorder writes comes from the launcher's specification, not from this run's own observation.

## Referent

The declared scope (`download scope --project VOICE`) names the referent as the
Bridge2AI-Voice dataset (adult), `https://doi.org/10.13026/37yb-1t42`, and
declares the Bridge2AI-Voice Pediatric Dataset
(`https://doi.org/10.13026/mf9s-5r03`) related but distinct, to be expressed as
`related_datasets`.

The record's one referent is the adult dataset as a PhysioNet project,
identified by the project-level DOI the bundle labels "DOI (latest version)"
(`id: doi:10.13026/37yb-1t42`), and described at its current release, 3.1.0
(published May 1, 2026). Both records hold to that choice:

- Facts from the PhysioNet 1.1 and 3.0.0 pages are stated as facts about those
  versions, under `version_access`, never as the current state.
- The pediatric PhysioNet page is used only for the `related_datasets` entry.
- The feasibility publication (47 participants at one site, no audio
  collected) describes a pilot study of the collection app, not the released
  dataset; none of its participant figures enter the record.
- The project documentation site's datasheet answers about distribution,
  hosting and maintenance describe an earlier release hosted on Health Data
  Nexus; they were not written as the current state. This is stated in the
  record's top-level `source_caveats`.

## Phase 1 - full generation

The chunk manifest check reported `current` (22 canonical chunks). All 22
chunks were read with the file-reading tool in manifest order, and the full
record validated against `Dataset` with schema and term validation.

Departures from the receipt protocol, stated because the transcript shows them:

- The receipt entries for chunks c001 to c021 were written as each chunk was
  read, with provisional slot paths, since the record did not yet exist. After
  the full record was written the receipt was rewritten once, whole, to align
  every path with the record as written. The first strict check, run before
  that rewrite, reported 5 `slot_not_in_record` findings and 21 of 22 chunks
  reviewed.
- The entry for c022 (`nothing_relevant`) was written during that rewrite, that
  is, after the chunk was read and after the full record's first write, not
  before the next step as the protocol asks.
- A second strict check passed with 749 of 762 receiptable slots covered. The
  13 uncovered leaves were list-valued slots receipted per index rather than
  at the list path; they were re-addressed after Phase 3 (see below).

Source disagreements and how they were handled:

- Funding numbers. The PhysioNet pages (tier 1) give NIH project number
  3OT2OD032720-01S1, the NIH RePORTER page (tier 4) gives 3OT2OD032720-01S3
  with core project number OT2OD032720, the project documentation (tier 2)
  gives OT2OD032720, and the feasibility publication (tier 3) cites
  1OT2OD032720-01 for that article. These are different project numbers under
  one core number, not incompatible claims, so no source-priority winner was
  chosen: the two project numbers the sources attach to the project are
  recorded as two grants and the rest is in `funders[0].source_caveats`.
- Spectrogram file names. The 3.1.0 page lists
  `torchaudio_spectrogram.parquet` and `torchaudio_mel_spectrogram.parquet`
  and describes them under the plural names. One source, so the ranking cannot
  decide; the listed names (also used by the page's usage note) are recorded
  and the difference is in `source_caveats`.
- Sensitive content. The documentation datasheet says the dataset includes
  race, sexual orientation, socioeconomic and health information, while the
  same documentation's de-identification section for version 3.0.0 says all
  sensitive fields were taken out. Same source and rank; both statements are
  recorded (`sensitive_elements[0]` and its `source_caveats`).
- Spellings of three creators differ between the PhysioNet author list and the
  project documentation (Siu/Sui, Rudzicz/Rudzizc, Donald/Don Bolser). The
  PhysioNet spelling (tier 1) is the name; the documentation's affiliation is
  attached with the spelling difference in that creator's `source_caveats`.

Slots deliberately left empty in the full record from its first write, each
because the bundle states an absence, a plan, or a fact about another version
(these are continued omissions, not removals): `collection_timeframes` (the
documentation's "12 months" is not tied to a release and predates the current
one), `content_warnings` (the datasheet's statement about free-speech
transcriptions conflicts with the documentation's own 3.0.0 de-identification
section), `cleaning_strategies` (the datasheet answers that none was applied),
`errata` (none exists), `splits` (none predefined), `external_resources` (the
datasheet says the dataset is self-contained), `maintainers`,
`data_protection_impacts`, `use_repository`, `language`, `conforms_to` and
`conforms_to_standard` (the Brain Imaging Data Structure statement is about a
conversion step and is recorded under `preprocessing_strategies`),
`raw_data_sources`, `total_file_count` and `total_size_bytes` (no file sizes
or totals are stated). Enumeration slots with no passage stating the category
stay empty: `bias_type`, `limitation_type`, `hipaa_compliant`, the phenotype
collection's `collection_type`, and `data_type` for two of four variables.

## Phase 2 - core derivation

The core was derived by the `derive core` command from the validated full
record; no model wrote any part of it. JSON printed by the first derivation:

```json
{"derived": true, "rule": "shared slots copied from the full record; resources projected by id with full-only nested slots dropped; distributions built from file_collections (one per collection over the shared slots, total_bytes as bytes) and from each collection's File entries (one per file over the slots CoreDistribution and File share); dialect from the File entries when they agree on one value, else absent", "from": {"path": "data/d4d_concatenated/claudecode_release/2026-11-25c_claude-fable-5-2-claudecode-generic-v9_rep1/VOICE_d4d.yaml", "md5": "bdb1e63641a286010b4da9116a212bba"}, "identity_slots": 79, "projected_slots": ["resources"], "distribution_slots": {"collection": ["compression", "conforms_to", "conforms_to_standard", "description", "id", "name", "notes", "path", "source_caveats"], "file": ["bytes", "compression", "conforms_to", "conforms_to_standard", "description", "encoding", "format", "hash", "id", "md5", "media_type", "name", "notes", "path", "sha256", "source_caveats"]}, "conditional": {"dialect": "derived only when every File-level dialect in the full record agrees on one value"}}
```

The command's own validation of the derived core reported no issues.

## Phase 3 - source and provenance audit

Provenance: the only files read for facts were the declared bundle, the source
manifest and the chunk manifest. Structure came from the two schema files and
the repository's playbook, guard and uniform-rules text; the receipt
validator's source (`src/data_sheets_schema/receipts.py`) was read to learn
its snippet normalization and path rules. No prior D4D record, evaluation or
reconciliation report from any arm, label or date was opened; output
directories were listed by name only, to confirm no VOICE file existed under
this label.

Findings on the full record, counted from the entries below: 4 in total, all
minor, all corrected in the full record. No finding concerned an unsupported
identifier, a wrong count, or a value about a dataset other than the referent.

| # | Severity | Slot | Finding | Correction |
|---|---|---|---|---|
| 1 | minor | `instances[0].description` | Ambiguous wording could be read as questionnaire responses being derived from audio. | Reworded: questionnaire responses together with features extracted from audio recordings. |
| 2 | minor | `ethical_reviews[0].review_details` | A protocol intention ("will apply for a separate REB") was restated in the present tense. | The protocol's future tense is kept and the statement stays attributed to the study protocol. |
| 3 | minor | `third_party_sharing[0].description` | The datasheet's future-tense statement ("will be distributed broadly") was restated as a present fact without its source. | Attributed to the datasheet in its own tense, with the PhysioNet access condition beside it. |
| 4 | minor | `description` | Source-supported omission: the countries of collection (USA and Canada). | Back-ported into `description`, receipted from c009. |

Receipts for the Phase 3 changes were added to the existing entries of the
chunks the passages sit in (c008, c009, c019). One back-port receipt was first
placed in c009 while its passage is in c008; the strict check reported it
(`snippet_adjacent_chunk`) and it was moved. At the same point the 13
list-valued leaves noted under Phase 1 were re-addressed at their list paths
(for example `keywords`, `version_access.versions_available`,
`ip_restrictions.restrictions`). These were receipt address corrections; no
record value changed with them.

Checks made in the audit that produced no finding:

- Counts and their units: 833 is the participant count the 3.1.0 page states
  for that release and is attached to an instance type of person; the
  per-file element counts are the 3.1.0 figures, not the 3.0.0 ones.
- Roles: `principal_investigator` is populated for the two people the
  documents designate with that title (the documentation names both as
  co-principal investigators; the NIH RePORTER page and the study protocol
  name one of them). Lead investigators are recorded as such in prose, not
  promoted.
- Plans kept as plans: raw audio "will be made available via Synapse", the
  semi-annual release plan, Spanish-language collection, and the protocol's
  retention period are all stated with their status and source.
- Privacy fields: `is_deidentified` rests on the 3.1.0 page's own
  de-identification steps (HIPAA Safe Harbor identifiers) and the
  documentation's de-identification level statement;
  `participant_privacy[0].privacy_techniques` rests on a passage that states
  feature extraction was done to limit re-identification.
- Identifiers: no ORCID, ROR or other registry identifier is stated in the
  bundle for any person or organization, and none was supplied.

After the corrections the full record passed schema and term validation again
and the strict receipt check reported 22/22 chunks reviewed, 561/561 snippets
verified and 762/762 receiptable slots with a receipt (114 exempt). The check
also reports, without gating, 3 snippets bearing on no token of their value
and 47 entry receipts overlapping one leaf.

## Phase 4 - re-derivation, checks, report

The core was re-derived from the corrected full record with
`--phase4-complete` (full record md5 `4e84d1ba2f18aab289f629580cc54327`); the
command's validation reported no issues. The full record has not changed since
that derivation; the receipt re-addressing described above came after it and
touched only the receipt file.

Results:

- Pair checker: `PASS: 79 schema-identical slots; projected
  slots=['resources']`, per-record slots `conforms_to_class` and
  `conforms_to_schema`, 0 errors, 1 warning (`semantic-review-required` on
  `file_collections` and `distributions`: 100 deterministic matches, 3 at
  collection level and 97 at nested resource level, no unmatched core
  distribution).
- Grounding check: `{'grounded': 1, 'minted_fragment': 108, 'absent': 0}`.
- Scope check: 2 records checked; neither is about a dataset the project
  declares distinct.
- Schema validation: full record against `Dataset` and core record against
  `CoreDataset`, no issues. Term validation: both passed.
- Report claims: checked after this report was written; see the provenance
  record's check block for the result.

No checker finding required a change to the full record, so no repair phase
ran. The reconcile step ran one derive-and-check pass.

## Claims

No slots were removed.

## Semantic review

- `file_collections` and `distributions` (the checker's `semantic-review-required` warning): the 3 collections and 97 files of the full record appear as 100 core distributions with the same ids, paths, formats, media types and descriptions; nothing in the core distribution list is absent from the full record. reviewed: consistent
- Counts and sizes against the entries beneath them: neither record states `total_file_count`, `total_size_bytes`, a collection `file_count` or any file `bytes`, because the bundle states no file sizes or totals; there is no stated total for the 97 listed files to disagree with, and the feature collection's description says further data dictionary files exist that the bundle does not name. reviewed: consistent
- `dialect` and `is_tabular` against the files: no file in the full record carries a `dialect`, so the core carries none; `is_tabular: true` agrees with the listed files, which are tab-separated tables with one row per participant visit or recording, Parquet files of per-recording elements, and JSON data dictionaries. reviewed: consistent
- Historical versus current release: top-level identity, counts, creators (the 122 authors of the 3.1.0 page), file names and per-file element counts are those of release 3.1.0; statements about versions 1.0, 1.1, 2.0, 2.0.1 and 3.0.0 sit only in `version_access` and in the second `related_datasets` entry, each with its version named. reviewed: consistent

## Related content

- `related_datasets[0]` is the declared related-but-distinct pediatric dataset, with `relationship_type: references`: the adult release page notes that the pediatric dataset is also available on PhysioNet and gives its address, which is the only relation the bundle states. Its target is the pediatric project-level DOI the pediatric page states. All facts taken from the pediatric page are in this entry's description.
- `related_datasets[1]` is version 1.0 of this dataset on Health Data Nexus, with `relationship_type: is_new_version_of`, from the release notes' statement that version 1.0 was the first release.

## Files changed

- Written: the full record, the coverage receipt, this report.
- Written by command: the core record (`derive core`, twice), and, after this report, the provenance record and its receipts block.
- No file outside this run's two output directories was written by the run, apart from a rendering of the executable playbook view under the repository's gitignored `.temp/` directory, made to read it.

## Commands

All run from the checkout root.

```
.venv/bin/python -m data_sheets_schema.cli agents playbook --relative-toolchain
.venv/bin/python -m data_sheets_schema.cli bundle chunk --bundle data/preprocessed/concatenated/VOICE_preprocessed.txt --chunk-manifest data/preprocessed/chunks/VOICE_chunks.yaml --manifest data/preprocessed/source_manifest.yaml --check --strict
.venv/bin/python -m data_sheets_schema.cli download scope --manifest data/preprocessed/source_manifest.yaml --project VOICE
.venv/bin/python -m data_sheets_schema.cli --manifest data/preprocessed/source_manifest.yaml download priority --project VOICE
.venv/bin/python -c 'from linkml.validator.cli import cli; cli()' -s src/data_sheets_schema/schema/data_sheets_schema_all.yaml -C Dataset data/d4d_concatenated/claudecode_release/2026-11-25c_claude-fable-5-2-claudecode-generic-v9_rep1/VOICE_d4d.yaml
.venv/bin/python -c 'from linkml_term_validator.cli import main; main()' validate-data data/d4d_concatenated/claudecode_release/2026-11-25c_claude-fable-5-2-claudecode-generic-v9_rep1/VOICE_d4d.yaml --schema src/data_sheets_schema/schema/data_sheets_schema_all.yaml --target-class Dataset
.venv/bin/python -m data_sheets_schema.cli --manifest data/preprocessed/source_manifest.yaml receipts check --method claudecode_release --label 2026-11-25c_claude-fable-5-2-claudecode-generic-v9_rep1 --project VOICE --bundle data/preprocessed/concatenated/VOICE_preprocessed.txt --chunk-manifest data/preprocessed/chunks/VOICE_chunks.yaml --strict
.venv/bin/python -m data_sheets_schema.cli derive core --full data/d4d_concatenated/claudecode_release/2026-11-25c_claude-fable-5-2-claudecode-generic-v9_rep1/VOICE_d4d.yaml --out data/d4d_concatenated/claudecode_release_core/2026-11-25c_claude-fable-5-2-claudecode-generic-v9_rep1/VOICE_d4d_core.yaml
.venv/bin/python -m data_sheets_schema.cli derive core --full data/d4d_concatenated/claudecode_release/2026-11-25c_claude-fable-5-2-claudecode-generic-v9_rep1/VOICE_d4d.yaml --out data/d4d_concatenated/claudecode_release_core/2026-11-25c_claude-fable-5-2-claudecode-generic-v9_rep1/VOICE_d4d_core.yaml --phase4-complete
.venv/bin/python -m data_sheets_schema.d4d_pair_consistency --full data/d4d_concatenated/claudecode_release/2026-11-25c_claude-fable-5-2-claudecode-generic-v9_rep1/VOICE_d4d.yaml --core data/d4d_concatenated/claudecode_release_core/2026-11-25c_claude-fable-5-2-claudecode-generic-v9_rep1/VOICE_d4d_core.yaml
.venv/bin/python -c "<grounding check_run program from the playbook, with this run's full, core and bundle paths>"
.venv/bin/python -m data_sheets_schema.cli download scope --manifest data/preprocessed/source_manifest.yaml --project VOICE --check --record data/d4d_concatenated/claudecode_release/2026-11-25c_claude-fable-5-2-claudecode-generic-v9_rep1/VOICE_d4d.yaml --record data/d4d_concatenated/claudecode_release_core/2026-11-25c_claude-fable-5-2-claudecode-generic-v9_rep1/VOICE_d4d_core.yaml --strict
.venv/bin/python -c 'from linkml.validator.cli import cli; cli()' -s src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml -C CoreDataset data/d4d_concatenated/claudecode_release_core/2026-11-25c_claude-fable-5-2-claudecode-generic-v9_rep1/VOICE_d4d_core.yaml
.venv/bin/python -c 'from linkml_term_validator.cli import main; main()' validate-data data/d4d_concatenated/claudecode_release_core/2026-11-25c_claude-fable-5-2-claudecode-generic-v9_rep1/VOICE_d4d_core.yaml --schema src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml --target-class CoreDataset
```

Two calls were made that are not prescribed commands: a `receipts check
--initial-structure` call, which the command refused for want of a native
shared selection and which changed nothing, and shell reads of the schema
files and of `receipts.py` (`sed`, `grep`, `awk`) to list class attributes,
enumeration values and the validator's rules. The bundle itself was read only
with the file-reading tool.

## Final results

- Full record: valid against `Dataset`; term validation passed.
- Core record: valid against `CoreDataset`; term validation passed; header carries `# Sources:` naming the same-run full record and `# Phase 4 reconciliation: completed`.
- Pair checker: PASS, 0 errors, 1 semantic-review warning, reviewed above.
- Grounding: 0 identifiers absent from the bundle.
- Scope: in scope.
- Receipts: 22/22 chunks reviewed, 561/561 snippets verified, 762/762 receiptable slots with a receipt.
- Phase 3 findings: 4 (4 minor), 4 corrected. Repair phase: none.

Not verified by this run: whether each verified snippet is sufficient support
for the value it sits under (the validator checks that a snippet is in its
chunk, not entailment), whether the chunks marked `nothing_relevant` held
nothing a different reader would have used, and the sampling temperature.
