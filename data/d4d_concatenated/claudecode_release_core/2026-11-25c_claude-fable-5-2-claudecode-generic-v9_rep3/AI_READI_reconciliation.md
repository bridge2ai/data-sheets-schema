# AI_READI reconciliation report

- Version label: `2026-11-25c_claude-fable-5-2-claudecode-generic-v9_rep3`
- Arm: BASELINE (input documents only)
- Mode: four-phase project agent, generic-v9 prompt
- Agent runtime: Claude Code (release); Provider: Anthropic; Model: claude-fable-5-2
- Temperature: unknown (not observed from the agent runtime). No sampling
  setting was inferred from the prompt, the model name or the effort level.
- Full record: `data/d4d_concatenated/claudecode_release/2026-11-25c_claude-fable-5-2-claudecode-generic-v9_rep3/AI_READI_d4d.yaml`
- Core record: `data/d4d_concatenated/claudecode_release_core/2026-11-25c_claude-fable-5-2-claudecode-generic-v9_rep3/AI_READI_d4d_core.yaml`
- Coverage receipt: `data/d4d_concatenated/claudecode_release_core/2026-11-25c_claude-fable-5-2-claudecode-generic-v9_rep3/AI_READI_coverage_receipt.yaml`
- Source bundle: `data/preprocessed/concatenated/AI_READI_preprocessed.txt` (md5 `1a58ad7be37d4b08ebd9d94e6ad173a3`, 25 chunks)
- Source manifest: `data/preprocessed/source_manifest.yaml`
- Chunk manifest: `data/preprocessed/chunks/AI_READI_chunks.yaml`

## Referent

The declared scope names one referent: the AI-READI dataset,
`https://doi.org/10.60775/fairhub.3`, and declares no related-but-distinct
dataset. Both records describe that referent: version 3.0.0 of the
"Flagship Dataset of Type 2 Diabetes from the AI-READI Project" as published
on FAIRhub. The record id is the DOI as a declared CURIE,
`doi:10.60775/fairhub.3`. Versions 1.0.0 and 2.0.0 are earlier releases of the
same dataset; what the bundle states about them is recorded as facts about
those versions under `version_access` and nowhere else. Passages whose subject
is the AI-READI study or project (the BMJ Open protocol, the Nature Metabolism
comment, the NIH RePORTER page, the IRB protocol) were used only for facts
about how this dataset was collected, consented, funded and governed, and
plans in them are stated as plans or omitted.

## Phase 1 - full generation

- The chunk manifest check reported `current` (25 canonical chunks) before any
  bundle read.
- All 25 chunks were read in manifest order with the file-reading tool, and a
  receipt entry was written for each chunk before the next chunk was read.
  Chunks c008 and c009 were covered by one read window (lines 2104 to 2196);
  both entries were written before c010 was read.
- The entries written while reading carried provisional slot addresses,
  because the record's list positions were not fixed until the last chunk had
  been read. After the full record was written, the receipt was re-addressed
  to the record's final paths before Phase 2, using only the chunks already
  read. The first strict check after re-addressing passed the registered
  floors with 422 of 431 slots receipted; the nine remaining were scalar
  lists receipted at an index, and were re-addressed to the list path, after
  which the check reported 431 of 431. The original writes and both
  corrections are preserved in the transcript.
- Schema validation of the first written full record reported three type
  errors (`issued`, `collection_timeframes[0].start_date` and `end_date`
  parsed as YAML dates rather than strings). The three values were quoted and
  the record then validated with no issues. No fact changed.

## Phase 2 - core derivation

The core was derived by projection from the validated full record
(`derive core`), with no model judgment. Facts printed by the command on the
final derivation:

```json
{"derived": true, "rule": "shared slots copied from the full record; resources projected by id with full-only nested slots dropped; distributions built from file_collections (one per collection over the shared slots, total_bytes as bytes) and from each collection's File entries (one per file over the slots CoreDistribution and File share); dialect from the File entries when they agree on one value, else absent", "from": {"path": "data/d4d_concatenated/claudecode_release/2026-11-25c_claude-fable-5-2-claudecode-generic-v9_rep3/AI_READI_d4d.yaml", "md5": "0d07c0e1fb764348784669ea785bd34e"}, "identity_slots": 79, "projected_slots": ["resources"], "distribution_slots": {"collection": ["compression", "conforms_to", "conforms_to_standard", "description", "id", "name", "notes", "path", "source_caveats"], "file": ["bytes", "compression", "conforms_to", "conforms_to_standard", "description", "encoding", "format", "hash", "id", "md5", "media_type", "name", "notes", "path", "sha256", "source_caveats"]}, "conditional": {"dialect": "derived only when every File-level dialect in the full record agrees on one value"}}
```

The first derivation (before the Phase 3 corrections) printed the same facts
with source md5 `fd17ae5984585c6d6db8e3627faa6423`; the core was re-derived
after Phase 3 and that earlier core no longer exists.

## Phase 3 - source and provenance audit

### Provenance

- Factual inputs read: the declared bundle only. Structural inputs read: the
  full schema, the chunk manifest, the source manifest (scope, naming and
  ranking), the provenance guard, the playbook, the uniform rules and
  `d4d-agent.md`.
- No previously generated D4D record, evaluation or reconciliation report was
  read, opened or searched, from any arm, label or date. Nothing under
  `data/d4d_concatenated/` was read other than this run's own three artifacts
  and its receipt; no `*_crate_d4d.yaml` or `*_crate_mapped_d4d.yaml` was
  opened.
- Curation notes in the source manifest that restate dataset figures were not
  used as evidence; every value in the record is receipted from a bundle
  chunk.
- Schema validation and term validation of the full record were re-run after
  the corrections below: no issues found; term validation passed.

### Findings

**Audit findings:** 3

3 findings: 0 high, 0 medium, 3 low.

| # | Severity | Slot | Finding | Source passage | Disposition |
|---|---|---|---|---|---|
| 1 | low | `sampling_strategies[0].strategies` | The record stated an adjustment of the participant composition as current practice; the source states it as an intention. | BMJ Open protocol (c002): "will be adjusted by under- and oversampling groups as needed" | Corrected in the full record to the source's tense. |
| 2 | low | `known_limitations[3].name` | The entry's name said balance was "not yet achieved"; the source says releases "may not have achieved" balanced distribution. | FAIRhub healthsheet (c018) and documentation (c011) | Name corrected to the source's reach. |
| 3 | low | `issued` | The schema's datetime format forces a time of day and UTC offset the sources do not state. | FAIRhub metadata (c015): date available 2025-11-17 | Value kept; the limitation is stated in `source_caveats` item 14. |

### Source conflicts and how they were handled

The manifest ranks the FAIRhub record and its API metadata first, the dataset
documentation, license and IRB protocol second, the two publications third
and the NIH RePORTER page fourth.

- De-identification: the FAIRhub dataset description states that no
  identifiers were collected so no active de-identification was necessary;
  the Nature Metabolism comment states that the public set is stripped of PHI
  by the HIPAA Safe Harbor method. The higher-ranked statement is recorded and
  no method is asserted; both statements are in `source_caveats`.
- License label: the FAIRhub page ("Health Data License") and the FAIRhub API
  ("AI-READI custom license v2.0") share the top rank; the API name is
  recorded in `license` and the page label in `source_caveats`.
- Principal investigator affiliation: NIH RePORTER (fiscal year 2022) gives
  University of Washington; the FAIRhub study description gives Washington
  University in St. Louis. The higher-ranked statement is recorded.
- Version 3 content: the documentation page says v3.0 contains pilot-phase
  data; the higher-ranked healthsheet says the third version includes data
  through the second year of the study. The healthsheet is followed.
- Enrollment target (4000 against the IRB protocol's 4600), the healthsheet's
  grant-number spelling, and the enrollment start date against the collection
  start date are compatible observations or transcription variants rather than
  conflicts between comparable claims; each is described in `source_caveats`.

### Judgments recorded for review

- Principal investigators: sixteen persons are recorded, each as a
  `principal_investigator` of its own `creators` entry, because the FAIRhub
  study description designates each as "Study Principal Investigator" and
  states an ORCID and an affiliation for each. The Nature Metabolism author
  list also has a "Principal Investigators" group; its extracted text is
  interleaved with other author groups and was not used to establish
  membership.
- Creator affiliations of the AI-READI Consortium entry follow the Nature
  Metabolism affiliation list; ROR identifiers are those the FAIRhub study
  description states for the same organizations. Two organizations in that
  list carry no identifier in the bundle and are recorded by name only. The
  two NIH institutes in the list were not recorded.
- Grants P30DK035816 and UL1TR003096 and the funder Research to Prevent
  Blindness are acknowledged by the publications as support for the research
  they report; the FAIRhub metadata names only OT2OD032644 as funding the
  creation of the dataset. All are recorded, with the distinction in
  `source_caveats`.
- Statements of absence in the healthsheet (no erratum, no retention limit, no
  extension mechanism, no data protection impact analysis, no prior uses, no
  use repository, no labels) were not turned into entries; they are listed in
  `source_caveats`. The slots `errata`, `retention_limit`,
  `extension_mechanism`, `data_protection_impacts`, `existing_uses`,
  `use_repository` and `labeling_strategies` are absent from both the first
  written record and the final record.
- The IRB protocol's table of planned variables was not used to populate
  `variables`: it lists planned domains, not columns of this release.
- Enumerations were populated only where a passage states the category:
  `bias_type` (the source says "selection bias"), one `limitation_type`
  (the source says the cohort "may not provide a comprehensive
  representation"), `data_use_permission` (the source restricts use to type 2
  diabetes related research), `collection_type` and `file_type` for files the
  source calls metadata files, and the named data standards. No `role` was
  set on either maintainer and no `collection_type` on the nine data
  directories.
- Record's own arithmetic: the nine data directories sum to 356,334 files and
  3,815,969,360,064 bytes against stated totals of 356,343 files and
  3,815,969,779,678 bytes; the differences are 9 files and 419,614 bytes.
  Both stated totals are recorded unadjusted and the computation is in
  `source_caveats` item 7.

## Phase 4 - re-derivation, checks, report

- Re-derivation: the core was re-derived from the corrected full record with
  `--phase4-complete`; the derived core validated with no issues.
- Pair checker: `PASS: 79 schema-identical slots; projected slots=['resources']; per-record slots (exempt, must differ)=['conforms_to_class', 'conforms_to_schema']`,
  with one warning, `semantic-review-required` on `file_collections` and
  `distributions` (deterministic matches=28, 10 at collection level and 18 at
  nested resource level, unmatched core distributions=[]).
- Grounding: `{'grounded': 27, 'minted_fragment': 28, 'absent': 0}`. No
  identifier in either record is absent from the bundle.
- Schema and term validation: full record, no issues found and term validation
  passed; core record, no issues found and term validation passed.
- Receipts (strict): chunks 25/25 reviewed, snippets 377/377 verified, slots
  431/431 with a receipt (32 exempt). Reported diagnostics, not gated: 7
  snippets bear on no token of their value (boolean-like or normalized values
  attested by a sentence, such as the format extensions and the
  representativeness statement), and 15 entry-level receipts overlap one leaf
  of their entry.
- No Phase 4 checker reported a finding that required a change, so no repair
  phase ran.

## Claims

No slots were removed.

## Semantic review

- `file_collections` and `distributions` (the pair checker's
  `semantic-review-required` warning): each of the ten file collections and
  each of the eighteen files beneath them appears in the core with the same
  id, name, description, path, standards, format and media type; no core
  distribution lacks a full-record counterpart. reviewed: consistent
- `total_file_count` and `total_size_bytes` against the entries beneath them:
  the stated totals (356,343 files; 3,815,969,779,678 bytes) exceed the sum of
  the nine directory collections by 9 files and 419,614 bytes; the tenth
  collection lists nine root-level metadata files for which the sources state
  no count and no size, so it carries neither. The stated totals are kept as
  stated and the computed difference is in `source_caveats`. reviewed: consistent
- `dialect` and `is_tabular` against the files: neither record sets either
  slot; the listed files are TSV, JSON, Markdown and plain-text metadata files
  with no stated dialect, and the dataset mixes tabular, imaging and waveform
  data. reviewed: consistent
- Historical against current release: figures for version 2.0.0 (2.01 TB,
  165,051 files) and the participant counts of versions 1 and 2 appear only in
  `version_access.version_details`; `distribution_dates`, `issued`, `version`,
  the totals and the instance count describe version 3.0.0 only. reviewed: consistent

## Files changed

- Written: the full record, the core record (derived), the coverage receipt
  and this report, all under this run's label.
- Also written, outside the declared outputs: `.temp/playbook_view.md` and
  `.temp/playbook_view.err`, the rendered executable playbook view the launch
  instruction asks to be read (the command's output was redirected to a file
  so it could be read with the file tool). They hold no dataset facts.
- One diagnostic was run inline and saved nowhere: a read-only listing of
  record leaves without a covering receipt, using the validator's own helper
  functions. It fed the receipt re-addressing described under Phase 1 and no
  value in either record.

## Commands

```bash
.venv/bin/python -m data_sheets_schema.cli agents playbook --relative-toolchain
.venv/bin/python -m data_sheets_schema.cli bundle chunk --bundle data/preprocessed/concatenated/AI_READI_preprocessed.txt --chunk-manifest data/preprocessed/chunks/AI_READI_chunks.yaml --manifest data/preprocessed/source_manifest.yaml --check --strict
.venv/bin/python -m data_sheets_schema.cli download scope --manifest data/preprocessed/source_manifest.yaml --project AI_READI
.venv/bin/python -m data_sheets_schema.cli --manifest data/preprocessed/source_manifest.yaml download priority --project AI_READI
.venv/bin/python -c 'from linkml.validator.cli import cli; cli()' -s src/data_sheets_schema/schema/data_sheets_schema_all.yaml -C Dataset data/d4d_concatenated/claudecode_release/2026-11-25c_claude-fable-5-2-claudecode-generic-v9_rep3/AI_READI_d4d.yaml
.venv/bin/python -c 'from linkml_term_validator.cli import main; main()' validate-data data/d4d_concatenated/claudecode_release/2026-11-25c_claude-fable-5-2-claudecode-generic-v9_rep3/AI_READI_d4d.yaml --schema src/data_sheets_schema/schema/data_sheets_schema_all.yaml --target-class Dataset
.venv/bin/python -m data_sheets_schema.cli --manifest data/preprocessed/source_manifest.yaml receipts check --method claudecode_release --label 2026-11-25c_claude-fable-5-2-claudecode-generic-v9_rep3 --project AI_READI --bundle data/preprocessed/concatenated/AI_READI_preprocessed.txt --chunk-manifest data/preprocessed/chunks/AI_READI_chunks.yaml --strict
.venv/bin/python -m data_sheets_schema.cli derive core --full data/d4d_concatenated/claudecode_release/2026-11-25c_claude-fable-5-2-claudecode-generic-v9_rep3/AI_READI_d4d.yaml --out data/d4d_concatenated/claudecode_release_core/2026-11-25c_claude-fable-5-2-claudecode-generic-v9_rep3/AI_READI_d4d_core.yaml
.venv/bin/python -m data_sheets_schema.cli derive core --full data/d4d_concatenated/claudecode_release/2026-11-25c_claude-fable-5-2-claudecode-generic-v9_rep3/AI_READI_d4d.yaml --out data/d4d_concatenated/claudecode_release_core/2026-11-25c_claude-fable-5-2-claudecode-generic-v9_rep3/AI_READI_d4d_core.yaml --phase4-complete
.venv/bin/python -m data_sheets_schema.d4d_pair_consistency --full data/d4d_concatenated/claudecode_release/2026-11-25c_claude-fable-5-2-claudecode-generic-v9_rep3/AI_READI_d4d.yaml --core data/d4d_concatenated/claudecode_release_core/2026-11-25c_claude-fable-5-2-claudecode-generic-v9_rep3/AI_READI_d4d_core.yaml
.venv/bin/python -c 'from linkml.validator.cli import cli; cli()' -s src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml -C CoreDataset data/d4d_concatenated/claudecode_release_core/2026-11-25c_claude-fable-5-2-claudecode-generic-v9_rep3/AI_READI_d4d_core.yaml
.venv/bin/python -c 'from linkml_term_validator.cli import main; main()' validate-data data/d4d_concatenated/claudecode_release_core/2026-11-25c_claude-fable-5-2-claudecode-generic-v9_rep3/AI_READI_d4d_core.yaml --schema src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml --target-class CoreDataset
```

The grounding check and the report-claims check were run as the inline
programs the playbook gives, with this run's three paths substituted.

## Final results

- Full record: schema validation, no issues found; term validation passed.
- Core record: schema validation, no issues found; term validation passed.
- Pair checker: PASS, no errors.
- Grounding: 0 absent identifiers.
- Receipts (strict): passed, 25/25 chunks, 377/377 snippets, 431/431 slots.
- Core header carries `# Sources:` naming the same-run full record and
  `# Phase 4 reconciliation: completed`.
- Reconciliation outcome: completed without repair. The three low-severity
  Phase 3 findings were resolved in the full record before re-derivation.
