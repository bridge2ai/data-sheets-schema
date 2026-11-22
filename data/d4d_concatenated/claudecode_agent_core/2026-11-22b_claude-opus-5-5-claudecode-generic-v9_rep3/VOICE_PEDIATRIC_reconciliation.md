# VOICE_PEDIATRIC reconciliation report

- Label: `2026-11-22b_claude-opus-5-5-claudecode-generic-v9_rep3`
- Runtime / provider / model: Claude Code / Anthropic / claude-opus-5-5
- Mode: four-phase project agent, generic-v9 prompt; arm BASELINE (input documents only)
- Temperature: unknown (not observed from the agent runtime). Reasoning effort: not observed; not asserted.
- Full: `data/d4d_concatenated/claudecode_agent/2026-11-22b_claude-opus-5-5-claudecode-generic-v9_rep3/VOICE_PEDIATRIC_d4d.yaml`
- Core: `data/d4d_concatenated/claudecode_agent_core/2026-11-22b_claude-opus-5-5-claudecode-generic-v9_rep3/VOICE_PEDIATRIC_d4d_core.yaml`
- Receipt: `data/d4d_concatenated/claudecode_agent_core/2026-11-22b_claude-opus-5-5-claudecode-generic-v9_rep3/VOICE_PEDIATRIC_coverage_receipt.yaml`

## Referent

The record describes one referent, the **Bridge2AI-Voice Pediatric Dataset**, as
the declared scope names it. Its `id` is `doi:10.13026/mf9s-5r03` and its `doi`
`10.13026/mf9s-5r03` — the PhysioNet "DOI (latest version)" stated in chunk c003.
Release-level values (`version` 1.1.0, `issued`, `citation`, file listing)
describe the current release 1.1.0, whose own DOI (10.13026/h995-bt35) is kept in
`version_access.version_details`; release 1.0.0 is described only in
`version_access` and `distribution_dates`. Both records hold this referent.

The declared related-but-distinct dataset, the Bridge2AI-Voice adult dataset, is
documented in the bundle (project documentation chunks c006–c009). Its facts —
the healthsheet answers, 833 participants, v2.0.0/v3.0.0 counts, the
de-identification and oversight answers, the Health Data Nexus distribution —
were kept out of every slot describing the referent. The bundle states only that
the adult dataset "is also available on PhysioNet" and that the two are
available "through separate PhysioNet links"; neither passage states a relation
from the schema's `relationship_type` vocabulary, so under the enumeration rule
no `related_datasets` entry is recorded and the relation is described in the
top-level `source_caveats` instead. The scope check reports neither record
identifies itself as the adult dataset.

## Phase 1 — full generation (summary)

- Chunk manifest check: `current`, 13 canonical chunks. Every chunk was read with
  the file-reading tool in manifest order and its receipt entry written before
  the next chunk was read.
- Receipt dispositions: 10 `extracted` (c002–c011) and 3 `nothing_relevant`
  (c001 concatenation preamble, c012 closing clauses of the DTUA template,
  c013 docs-repository README).
- Receipt corrections before Phase 2 (syntax and addressing only, no new reads):
  (1) every `slot` value was quoted, because unquoted paths containing `[` broke
  the YAML flow mappings and the first strict check could not parse the receipt;
  (2) four receipts were re-addressed from a leaf to its entry
  (`instances[0]`, `instances[1]`, `participant_privacy[0]`,
  `distribution_dates[0]`) and one added for `license_and_use_terms.name`, so the
  entry names were covered. The strict check then passed: 13/13 chunks,
  293/293 snippets, 326/326 receiptable slots.
- Full schema validation and term validation passed before Phase 2.

## Phase 2 — core derivation

Command output of the Phase 2 derivation (`derive core`, no model):

```json
{"derived": true, "rule": "shared slots copied from the full record; resources projected by id with full-only nested slots dropped; distributions built from file_collections (one per collection over the shared slots, total_bytes as bytes) and from each collection's File entries (one per file over the slots CoreDistribution and File share); dialect from the File entries when they agree on one value, else absent", "from": {"path": "data/d4d_concatenated/claudecode_agent/2026-11-22b_claude-opus-5-5-claudecode-generic-v9_rep3/VOICE_PEDIATRIC_d4d.yaml", "md5": "8000a77a536415434fe3538b04735385"}, "identity_slots": 79, "projected_slots": ["resources"], "distribution_slots": {"collection": ["compression", "conforms_to", "conforms_to_standard", "description", "id", "name", "notes", "path", "source_caveats"], "file": ["bytes", "compression", "conforms_to", "conforms_to_standard", "description", "encoding", "format", "hash", "id", "md5", "media_type", "name", "notes", "path", "sha256", "source_caveats"]}, "conditional": {"dialect": "derived only when every File-level dialect in the full record agrees on one value"}}
```

The derived core validated (`linkml-validate: No issues found`).

## Phase 3 — source and provenance audit

### Provenance

- Inputs read: the declared bundle (all 13 chunks, file-tool windows), the
  chunk manifest, `data/preprocessed/source_manifest.yaml` (scope, naming and
  priority entries), the full and core schemas (structure only; the class
  digest was printed with the package's own `schema_digest.digest_text`), and
  the playbook, provenance guard and uniform rules.
- No prior generated D4D record, evaluation or reconciliation report from any
  run was opened, searched or cited. The only generated YAML read is this run's
  own full/core pair. The manifest's curator `curation_note` was not used as a
  source of facts.
- Grounding: 1 grounded identifier, 16 minted fragments, 0 absent. Every minted
  fragment sits on the record's own id `doi:10.13026/mf9s-5r03`.

### Source findings (full record)

Findings recorded: 6 (2 moderate, 4 minor), counted from the entries below.

| # | Severity | Slot | Finding | Source | Action |
|---|---|---|---|---|---|
| F1 | moderate | `file_collections[0].resources` | `audio_quality_metrics.tsv` was listed in the `features` collection, but the page says only that "the features folder contains the following plain-text file" (static_features.tsv) and names audio_quality_metrics.tsv without a folder | c002 | File entry dropped from the collection; the fact moved to `description`; limitation stated in `file_collections[0].source_caveats` |
| F2 | moderate | `file_collections[2].description` | Wording implied the audio-quality metrics belong to the `metadata` collection; the release note does not place them | c003 | Description reduced to the per-recording metadata the note supports |
| F3 | minor | `funders[0].grantor` | Value merged the fund and the program ("NIH Common Fund (Bridge2AI Program)") | c007 | Set to "NIH Common Fund"; the program stays in `description` |
| F4 | minor | `distribution_formats` | Source-stated formats (Parquet binary files, plain-text TSV files, JSON data dictionaries) were omitted | c002, c003 | Back-ported three entries, each with receipts in the existing c002/c003 entries |
| F5 | minor | `file_collections[0].source_caveats` | Usage examples name `torchaudio_spectrogram.parquet`, `torchaudio_mel_spectrogram.parquet` and `torch_spectrogram.json`, differing from the listed file names | c002, c003 | Caveat added; the listed names are kept |
| F6 | minor | `collection_mechanisms[0].description` | Paraphrase said "participants" where the source says "patients" were assigned study numbers | c002 | Source wording restored |

Checks with no finding: identifiers, versions, dates and counts agree across
the record (23,533 recordings, 300 participants, per-file n values as stated);
no count is a derived figure; no negative current-state claim is made; the
Synapse raw-audio passage keeps its future tense ("will be made available") and
its date; privacy and consent statements taken from the multi-site IRB protocol
are labeled as protocol statements in their `source_caveats`; the principal
investigators are the persons the bundle designates with that title (Yael
Bensoussan: protocol PI, NIH RePORTER PI and project co-PI; Olivier Elemento:
project co-PI). The NIH RePORTER record (3OT2OD032720-01S3) and the docs footer
award (3Tf-OTOD03272001S2) differ from the grant the pediatric page names
(3OT2OD032720-01S1); these are different award records rather than a conflict
about one value, so only the pediatric page's number is recorded as the grant
and the others are noted in `funders[0].source_caveats`.

After the repairs the full record re-validated (schema and terms) and the strict
receipt check passed: 13/13 chunks, 302/302 snippets, 332/332 receiptable slots.

## Phase 4 — re-derivation, checks, report

- Core re-derived with `--phase4-complete` from the audited full record (full
  md5 `733b2c4bed4de2c7125dc5a8920c995e`); derivation facts as in Phase 2
  (`identity_slots` 79, `projected_slots` [resources]). Core schema and term
  validation passed.
- Pair checker: PASS, 79 schema-identical slots, projected `resources`,
  per-record exempt `conforms_to_class` and `conforms_to_schema`; one warning,
  `semantic-review-required` on `file_collections` ↔ `distributions`
  (14 deterministic matches: 3 collections, 11 files; no unmatched
  distribution).
- Grounding: `absent` 0.
- Scope check (`download scope --check --strict`): both records in scope.
- No checker finding required a change, so there was no repair phase.
- Header note: the derived core header writes
  `# Schema: src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml`
  (repository-relative), where the launch instruction's core header block gives
  the absolute path. The core is not edited by hand; the line is reported here.

## Claims

No slots were removed.

(A nested list entry, `file_collections[0].resources[10]`, was dropped in
Phase 3 as F1 describes; no top-level slot was removed from either record.)

## Semantic review

- `file_collections` ↔ `distributions` (pair-checker warning): the core has 14
  distributions — 3 for the collections (features, phenotype, metadata) and 11
  for their files (9 Parquet, static_features.tsv, demographics.tsv); ids, names
  and TSV format/media types match the full record entry for entry, and
  audio_quality_metrics.tsv appears in neither. **reviewed: consistent**
- `total_file_count` / `total_size_bytes` against the entries beneath them:
  neither record carries them and no collection carries `file_count` or
  `total_bytes`; the bundle states no file count or size. **reviewed: consistent**
- `dialect` / `is_tabular` against the files: no File carries a dialect, so the
  core derives none; `is_tabular` is absent from both records. **reviewed: consistent**
- Historical versus current release: version, issued date, citation, page and
  file listing describe release 1.1.0; release 1.0.0 appears only in
  `version_access` and `distribution_dates`; adult-dataset release facts
  (v2.0.0, v3.0.0, v3.1.0) are not used. **reviewed: consistent**

## Files changed

- Full record (written in Phase 1; Phase 3 edits F1–F6).
- Coverage receipt (written chunk by chunk in Phase 1; Phase 1 syntax and
  address corrections; Phase 3 receipts added in place to the c002 and c003 entries).
- Core record (derived in Phase 2; re-derived in Phase 4).
- This report.

## Commands

- `.venv/bin/python -m data_sheets_schema.cli bundle chunk --bundle data/preprocessed/concatenated/VOICE_PEDIATRIC_preprocessed.txt --chunk-manifest data/preprocessed/chunks/VOICE_PEDIATRIC_chunks.yaml --manifest data/preprocessed/source_manifest.yaml --check --strict`
- `.venv/bin/python -m data_sheets_schema.cli download scope --manifest data/preprocessed/source_manifest.yaml --project VOICE_PEDIATRIC`
- `.venv/bin/python -m data_sheets_schema.cli --manifest data/preprocessed/source_manifest.yaml download priority --project VOICE_PEDIATRIC`
- `.venv/bin/python -c 'from linkml.validator.cli import cli; cli()' -s …/data_sheets_schema_all.yaml -C Dataset <full>` (Phase 1, Phase 3)
- `.venv/bin/python -c 'from linkml_term_validator.cli import main; main()' validate-data <full> --schema …/data_sheets_schema_all.yaml --target-class Dataset` (Phase 1, Phase 3)
- `.venv/bin/python -m data_sheets_schema.cli --manifest data/preprocessed/source_manifest.yaml receipts check --method claudecode_agent --label 2026-11-22b_claude-opus-5-5-claudecode-generic-v9_rep3 --project VOICE_PEDIATRIC --bundle data/preprocessed/concatenated/VOICE_PEDIATRIC_preprocessed.txt --chunk-manifest data/preprocessed/chunks/VOICE_PEDIATRIC_chunks.yaml --strict` (failed once on receipt YAML syntax, then passed; re-run after Phase 3)
- `.venv/bin/python -m data_sheets_schema.cli derive core --full <full> --out <core>` (Phase 2) and the same with `--phase4-complete` (Phase 4)
- `.venv/bin/python -c 'from linkml.validator.cli import cli; cli()' -s …/data_sheets_schema_core_all.yaml -C CoreDataset <core>` and the core term validation
- `.venv/bin/python -m data_sheets_schema.d4d_pair_consistency --full <full> --core <core>`
- The grounding check (`grounding.check_run`) and the report-claims check (`report_claims.check_report`) as the playbook gives them
- `.venv/bin/python -m data_sheets_schema.cli download scope --manifest data/preprocessed/source_manifest.yaml --project VOICE_PEDIATRIC --check --record <full> --record <core> --strict`

## Final results

- Full record: 41 top-level slots; schema and term validation pass.
- Core record: 39 top-level slots; schema and term validation pass.
- Pair checker: pass (one semantic-review warning, reviewed above).
- Receipt: 13/13 chunks reviewed, 302/302 snippets verified, 332/332 receiptable slots covered.
- Grounding: 0 absent identifiers. Scope: in scope.
