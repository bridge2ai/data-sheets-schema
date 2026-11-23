# CM4AI reconciliation report — 2026-11-22b_claude-opus-5-5-claudecode-generic-v9_rep3

- Runtime: Claude Code; provider Anthropic; model claude-opus-5-5
- Mode: four-phase project agent, generic-v9 prompt; arm BASELINE (input documents only)
- Source bundle: `data/preprocessed/concatenated/CM4AI_preprocessed.txt` (md5 50037fc631eafda807e19f83f6579818, 28 chunks)
- Chunk manifest: `data/preprocessed/chunks/CM4AI_chunks.yaml`; source manifest: `data/preprocessed/source_manifest.yaml`
- Full: `data/d4d_concatenated/claudecode_agent/2026-11-22b_claude-opus-5-5-claudecode-generic-v9_rep3/CM4AI_d4d.yaml`
- Core: `data/d4d_concatenated/claudecode_agent_core/2026-11-22b_claude-opus-5-5-claudecode-generic-v9_rep3/CM4AI_d4d_core.yaml`
- Receipt: `data/d4d_concatenated/claudecode_agent_core/2026-11-22b_claude-opus-5-5-claudecode-generic-v9_rep3/CM4AI_coverage_receipt.yaml`
- Temperature: unknown (not observed from the agent runtime). Reasoning effort: not observed; none recorded.

## Referent

The manifest's scope declares the referent as "CM4AI (Cell Maps for Artificial
Intelligence) dataset" with `referent_id` https://cm4ai.org/ and no
related-but-distinct datasets; its note says the four Dataverse releases in the
bundle are releases of this dataset. Both records use `id: https://cm4ai.org/`
and describe the dataset as a release series. The four releases are entries
under `resources`, identified by their DOIs (doi:10.18130/V3/B35XWX March 2025,
doi:10.18130/V3/F3TD5R June 2025, doi:10.18130/V3/K7TGEM October 2025,
doi:10.18130/V3/HIGT4C June 2026). The June 2026 release is treated as the
current release. Governance, maintenance, intended uses, limitations,
prohibited uses, biases, creators and keywords come from its page. Facts from
the earlier releases stay inside their own `resources` entries.

The Nature article in the bundle (chunks c002–c009) describes a U2OS cell map
study. Nothing in the bundle says it describes a CM4AI data release, so it
supplied no values. Its chunks are receipted `nothing_relevant` with that
reason.

## Phase 1 — full generation

- Every chunk c001–c028 was read in manifest order with the file-reading tool.
  Five reads each covered two adjacent chunks in one window: c008–c009,
  c013–c014, c021–c022, c024–c025 and c027–c028. For those pairs, the entry
  for the first chunk was written after both chunks had been read, so the
  rule "write a chunk's entry before reading the next chunk" was not met for
  c008, c013, c021, c024 and c027. Both entries of each pair were still
  written before the next window was read. For every other chunk, the entry
  was written before the next read.
- Receipt corrections before Phase 2, within the Phase 1 correction loop. All
  used chunks already read. c002 was changed from `extracted` to
  `nothing_relevant`, because the Nature subject tags describe the article and
  not the dataset. Receipt paths in c011, c012, c014, c015, c018, c020, c023
  and c026 were re-addressed to the final record paths. Scalar-list slots were
  addressed without an index. Receipts were added for collection names and
  paths, the grant name of 5U54HG012513-02, copyright statements and the RO-Crate
  packaging sentence.
- Full validation: linkml-validate `No issues found`; term validation `Validation passed`.
- Strict receipt check before Phase 2: 28/28 chunks reviewed, 322/322 snippets
  verified, 476/476 leaves receipted, exit 0.

## Phase 2 — core derivation

Command: `derive core --full <full> --out <core>` (as registered). Output:

```json
{"derived": true, "rule": "shared slots copied from the full record; resources projected by id with full-only nested slots dropped; distributions built from file_collections (one per collection over the shared slots, total_bytes as bytes) and from each collection's File entries (one per file over the slots CoreDistribution and File share); dialect from the File entries when they agree on one value, else absent", "from": {"path": "data/d4d_concatenated/claudecode_agent/2026-11-22b_claude-opus-5-5-claudecode-generic-v9_rep3/CM4AI_d4d.yaml", "md5": "a2a9084395d84277e984bc4fcb5e3b18"}, "identity_slots": 79, "projected_slots": ["resources"], "distribution_slots": {"collection": ["compression", "conforms_to", "conforms_to_standard", "description", "id", "name", "notes", "path", "source_caveats"], "file": ["bytes", "compression", "conforms_to", "conforms_to_standard", "description", "encoding", "format", "hash", "id", "md5", "media_type", "name", "notes", "path", "sha256", "source_caveats"]}, "conditional": {"dialect": "derived only when every File-level dialect in the full record agrees on one value"}}
```

The derived core passed linkml-validate.

## Phase 3 — source and provenance audit

### Provenance

- Inputs read: the declared bundle, by chunk with the file-reading tool; the
  chunk manifest; the CM4AI sections of the source manifest; the full and core
  schemas; the schema digest from the repository's `schema_digest` module; the
  provenance guard, the playbook, the uniform rules and the d4d-agent method.
  No prior generated D4D record, evaluation or reconciliation report was
  opened, searched or listed. The only D4D files read are this run's own pair.
- Both records use the run's exact version label. The core's `# Sources:` line
  names this run's full record.

### Findings (entries)

| # | Slot(s) | Kind | Severity | Source (chunk) | Action |
|---|---|---|---|---|---|
| 1 | `distribution_formats` | supported omission | minor | June 2026 release file table, "Archive (10)" / "ZIP Archive" (c026) | Back-ported `distribution_formats[0]` (ZIP archives, application/zip) to the full record with its receipt in c026 |

Totals, counted from the table: 1 finding (minor 1, major 0, critical 0). One
finding required a change, and it was made in the full record. The audit found
no unsupported, stale, mis-scoped or wrongly shaped assertion in the full
record.

### Source observations retained without change

These are recorded in `source_caveats` in the record. No value was changed
because of them.

1. Release date of HIGT4C. The cm4ai.org data releases page (tier 2) says
   "Released on: June 17, 2025". The Dataverse page (tier 1) gives Publication
   Date 2026-06-17. The higher-ranked Dataverse value is used, and the
   disagreement is noted in `resources[3].source_caveats`.
2. IF image protein counts by source. The March 2025 release gives 563, the
   June and October 2025 releases give 464, and the data releases page gives
   523. These describe different releases or page snapshots, so they are not
   in conflict, and the record does not reconcile them.
3. The data releases page lists AP-MS for TNBC cells as "coming soon", while
   the June 2026 release includes AP-MS data for treated MDA-MB-468 cells. The
   page text reflects an earlier status.
4. The preprint cites release doi:10.18130/V3/DXWOS5 (V1). The bundle does not
   say whether this is the "May 2024 Data Release", so both are listed in
   `version_access.versions_available`.
5. The captured June 2025 (F3TD5R) page shows only the first 10 of 21 files.
   `total_file_count` is 21 and only the 10 listed files are described.
6. The Data Governance Committee contact "Jillian Parker" was matched to author
   "Parker J (University of California, San Diego)" and that author's ORCID, by
   name and institution. The match is stated in a caveat.
7. NIH RePORTER names "IDEKER, TREY" as principal investigator of the CM4AI
   Data Generation Project. This is recorded as `principal_investigator` on
   the Ideker T creator entry, using the ORCID from the Dataverse author list.
   No other person is designated PI.

### Phase 3 validation

After the back-port: linkml-validate `No issues found`; term validation
`Validation passed`; strict receipt check 28/28 chunks, 324/324 snippets,
479/479 leaves receipted, exit 0.

## Phase 4 — re-derivation, checks, report

- Re-derived the core with `derive core --phase4-complete` after the Phase 3
  correction. The new source md5 is 94410d5a30abb2f4f303f6123fe2b03c and the
  core passed linkml-validate.
- Pair consistency: `PASS: 79 schema-identical slots; projected slots=['resources'];
  per-record slots (exempt, must differ)=['conforms_to_class', 'conforms_to_schema']`.
  No `semantic-review-required` warning was emitted.
- Core validation: linkml-validate `No issues found`; term validation `Validation passed`.
- Grounding: `{'grounded': 43, 'minted_fragment': 0, 'absent': 0}`. No
  identifier in either record is absent from the bundle.
- Scope check (`download scope --check --strict` on the current pair): 2
  records checked; none identifies itself as a dataset the project declares
  distinct.
- Core header deviation, not corrected. The registered derive command writes
  `# Schema: src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml`,
  a repository-relative path, while the launch's CORE HEADER BLOCK gives the
  absolute path to the same file. The core is never edited by hand, and the
  registered command line carries no schema flags, so the derived spelling
  stands. Every other header line matches the block, in its order, including
  `# Sources:` and `# Phase 4 reconciliation: completed`.
- Repair: none of the step-2 checkers (grounding, report claims) and nothing
  in the final pair run reported a finding that required a change, so no
  repair phase ran.

## Claims

No slots were removed.

## Semantic review

- `file_collections` ↔ `distributions`: the pair checker emitted no warning. The full record has no top-level `file_collections`, so the core has no top-level `distributions`. Each release's `file_collections` sit inside its `resources` entry and are projected into that core resource's `distributions`. I checked that every collection and file id appears there for each of the four releases. **reviewed: consistent**
- Counts and sizes against the entries beneath them: `total_file_count` is 6 for B35XWX (6 files described), 8 for K7TGEM (8 described) and 10 for HIGT4C (10 described). F3TD5R has `total_file_count` 21 with 10 described, because its captured page lists only the first 10 files; this is stated in `resources[1].source_caveats`. `total_size_bytes` and file `bytes` are not populated, because the pages give only rounded sizes. **reviewed: consistent**
- `dialect` and `is_tabular` against the files: neither is populated in either record. The files are ZIP, JSON and HTML, and no passage gives a tabular dialect. **reviewed: consistent**
- Historical vs current release: facts from the March 2025, June 2025 and October 2025 releases are confined to `resources[0]` to `resources[2]`, whose descriptions label them historical or superseded. Top-level governance, maintenance, use, limitation and bias values come from the June 2026 release (`resources[3]`, the current release). Older counts and dates are not presented as current. **reviewed: consistent**

## Files changed

- Created the full record, the coverage receipt (edited in place during the
  Phase 1 correction loop and the Phase 3 back-port), the derived core (Phase 2,
  then re-derived in Phase 4) and this report.

## Commands

```
python -m data_sheets_schema.cli bundle chunk --bundle data/preprocessed/concatenated/CM4AI_preprocessed.txt --chunk-manifest data/preprocessed/chunks/CM4AI_chunks.yaml --manifest data/preprocessed/source_manifest.yaml --check --strict
python -m data_sheets_schema.cli download scope --manifest data/preprocessed/source_manifest.yaml --project CM4AI
python -m data_sheets_schema.cli download priority --project CM4AI
python -c 'from linkml.validator.cli import cli; cli()' -s <full schema> -C Dataset <full>
python -c 'from linkml_term_validator.cli import main; main()' validate-data <full> --schema <full schema> --target-class Dataset
python -m data_sheets_schema.cli --manifest data/preprocessed/source_manifest.yaml receipts check --method claudecode_agent --label 2026-11-22b_claude-opus-5-5-claudecode-generic-v9_rep3 --project CM4AI --bundle data/preprocessed/concatenated/CM4AI_preprocessed.txt --chunk-manifest data/preprocessed/chunks/CM4AI_chunks.yaml --strict
python -m data_sheets_schema.cli derive core --full <full> --out <core>
python -m data_sheets_schema.cli derive core --full <full> --out <core> --phase4-complete
python -m data_sheets_schema.d4d_pair_consistency --full <full> --core <core>
python -c 'from linkml.validator.cli import cli; cli()' -s <core schema> -C CoreDataset <core>
python -c 'from linkml_term_validator.cli import main; main()' validate-data <core> --schema <core schema> --target-class CoreDataset
python -c "...grounding.check_run(...)..."
python -m data_sheets_schema.cli download scope --manifest data/preprocessed/source_manifest.yaml --project CM4AI --check --record <full> --record <core> --strict
python -c "...report_claims.check_report(...)..."
```

`python` is `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/fast-d4d-20261121-rep3/.venv/bin/python`.

## Final results

- Full record: valid (schema and terms). 35 top-level slots populated.
- Core record: valid (schema and terms). 37 top-level slots populated (the 35
  shared slots plus `conforms_to_class` and `conforms_to_schema`).
- Pair consistency: PASS. Grounding: 0 absent. Scope: in scope.
- Receipts (strict): pass.
- Reconciliation outcome: one Phase 3 back-port (`distribution_formats`). No
  removals, no repair phase, and no conflicts between the full and core
  records.
