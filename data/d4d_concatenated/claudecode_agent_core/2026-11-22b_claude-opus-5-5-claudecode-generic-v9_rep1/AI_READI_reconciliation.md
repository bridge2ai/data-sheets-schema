# AI_READI reconciliation report — 2026-11-22b_claude-opus-5-5-claudecode-generic-v9_rep1

- Runtime: Claude Code · Provider: Anthropic · Model: claude-opus-5-5
- Mode: four-phase project agent, generic-v9 prompt · Arm: BASELINE (input documents only)
- Temperature: unknown (not observed from the agent runtime). Reasoning effort: not observed; not asserted.
- Declared input bundle: `data/preprocessed/concatenated/AI_READI_preprocessed.txt` (md5 `1a58ad7be37d4b08ebd9d94e6ad173a3`, 25 chunks)
- Chunk manifest: `data/preprocessed/chunks/AI_READI_chunks.yaml` · Source manifest: `data/preprocessed/source_manifest.yaml`
- Full: `data/d4d_concatenated/claudecode_agent/2026-11-22b_claude-opus-5-5-claudecode-generic-v9_rep1/AI_READI_d4d.yaml`
- Core: `data/d4d_concatenated/claudecode_agent_core/2026-11-22b_claude-opus-5-5-claudecode-generic-v9_rep1/AI_READI_d4d_core.yaml`
- Receipt: `data/d4d_concatenated/claudecode_agent_core/2026-11-22b_claude-opus-5-5-claudecode-generic-v9_rep1/AI_READI_coverage_receipt.yaml`

## Referent

The record describes **version 3.0.0 of the AI-READI dataset**, "Flagship Dataset of Type 2
Diabetes from the AI-READI Project", identified as `doi:10.60775/fairhub.3` (the manifest's
declared referent, `https://doi.org/10.60775/fairhub.3`, written as the declared `doi:` CURIE).
The FAIRhub dataset metadata (tier 1) are the best-supported description of that release.
Versions 1.0.0 (`fairhub.1`) and 2.0.0 (`fairhub.2`) are recorded only as version history in
`version_access`, per the manifest's referent note; no related-but-distinct dataset is declared.
Both records hold this referent.

## Phase 1 — full generation

- All 25 chunks were opened with the file-reading tool in manifest order; one receipt entry was
  written per chunk before the next was read (c001 and c008 `nothing_relevant`, the rest
  `extracted`).
- Structure came from class `Dataset` via the repository's schema digest
  (`data_sheets_schema.schema_digest.digest_text`) and `SchemaView` induced slots; no prior D4D
  record or schema example was used as a template.
- Correction loop before Phase 2 (receipt addresses only, from chunks already read): slot paths
  were re-addressed after the record's lists were re-indexed (collection mechanisms split one
  instrument per entry; NIH grants split into the dataset-funding entry and the publication
  funding entry; principal investigators placed one per creator entry); two paths that did not
  exist in the record were corrected; receipts were added for leaves that had none (keywords
  list, creator names and descriptions, instance name, ethics review board, de-identification
  fields). One short snippet ("Level 3") was lengthened to an attesting one.
- First strict receipt check: exit 1 (2 × `slot_not_in_record`). After correction: exit 0,
  chunks 25/25, snippets 548/548, slots 602/602 with a receipt.
- Full record schema validation: No issues found. Term validation: passed.

## Phase 2 — core derivation

Command output (`derive core`, Phase 2 run):

```json
{"derived": true, "rule": "shared slots copied from the full record; resources projected by id with full-only nested slots dropped; distributions built from file_collections (one per collection over the shared slots, total_bytes as bytes) and from each collection's File entries (one per file over the slots CoreDistribution and File share); dialect from the File entries when they agree on one value, else absent", "identity_slots": 79, "projected_slots": ["resources"], "conditional": {"dialect": "derived only when every File-level dialect in the full record agrees on one value"}}
```

Core validated against `CoreDataset`: No issues found. 28 distributions were built (10 from
file collections, 18 from File entries).

## Phase 3 — source and provenance audit

Provenance: the only factual inputs read were the declared bundle (through its 25 chunk
windows), the source manifest, the chunk manifest and the two schemas. No prior full or core
D4D, evaluation or reconciliation report was opened; the only access to
`data/d4d_concatenated/` beyond this run's own paths was a directory-name listing to confirm
the label was unused.

Recorded findings (3 total: 1 moderate, 2 minor), all corrected in the full record with
receipts added to the existing chunk entries:

| # | Severity | Slot | Source (chunk) | Finding | Correction |
|---|---|---|---|---|---|
| F1 | minor | `preprocessing_strategies[1]` | BMJ Open Table 4 (c005) | Attributed the `.FIT` export to the Garmin device although the extracted table text does not make cell ownership explicit | Formats no longer attributed to devices; limitation stated in the entry's `source_caveats` |
| F2 | moderate | `license_and_use_terms.description` | Nature Metabolism comment (c007) | "allows reuse for any purpose" describes the license under which the *first* public version was shared (November 2024), but was written as a statement about the current license | Sentence now carries its version scope; v3.0.0 license named as Version 2.0 |
| F3 | minor | `is_deidentified.source_caveats` | IRB protocol (c023) | The FAIRhub statement that no identifiers were collected could be read as a statement about the study's records; the IRB protocol states the study team obtains identifiers, stored separately with a code link | Caveat added limiting the FAIRhub statement to the released dataset's content |

Other checks with no change:

- Source conflicts were tested for comparability before ranking (project-name expansions;
  v3 documentation's "pilot study phase" sentence vs. tier-1 FAIRhub metadata; enrollment start
  18 vs. 19 July 2023; planned enrollment 4000 / 4,000+ / 4600 and follow-up 10% / ~4%;
  license label "Health Data License" vs. "AI-READI custom license v2.0"; license purposes vs.
  T2DM-only access condition; Safe Harbor stripping vs. no identifiers collected; 53 mL vs.
  50–60 mL blood). Each is recorded in the top-level or entry-level `source_caveats`; plans are
  not recorded as current facts.
- Principal investigators: each person the FAIRhub study description designates "Study
  Principal Investigator" (16) is recorded under `creators[n].principal_investigator` with the
  ORCID and affiliation ROR the bundle states. The Nature Metabolism author list also has a
  "Principal Investigators" heading, but its PDF extraction interleaves names and affiliations,
  so it was not used. Recording study PIs as creator entries is a judgement: the schema's only
  principal-investigator slot is on `Creator`.
- Statements of absence (no confidential data, no DPIA, no retention limits, no extension
  mechanism, no labels, no exclusions at preprocessing, no demographic sub-populations
  identified, no prior uses) are kept in `source_caveats`, not as entries.
- Composite inventories checked member by member: the v3.0.0 documentation's controlled-access
  list (including genetic sequencing data) is attributed to that document; the IRB protocol's
  whole genome sequencing is recorded as planned, funding permitted.
- Count/type ownership: subpopulation counts were checked against the README split table rows
  and columns (each split sums to its stated total).

Full record re-validated after the corrections: schema No issues found; term validation passed;
strict receipt check exit 0 (snippets 552/552, slots 602/602).

## Phase 4 — re-derivation, checks, report

1. Core re-derived from the corrected full record with `--phase4-complete`; core validation:
   No issues found.
2. Pair checker: `PASS: 79 schema-identical slots; projected slots=['resources']; per-record
   slots (exempt, must differ)=['conforms_to_class', 'conforms_to_schema']`, with one warning,
   `semantic-review-required` on `file_collections` ↔ `distributions` (28 deterministic matches,
   no unmatched core distributions).
3. Identifier grounding: `{'grounded': 27, 'minted_fragment': 28, 'absent': 0}`.
4. Scope check (`download scope --check --strict`): 2 records checked; none is about a dataset
   the project declares distinct.
5. Header note: the launch instruction's core header gives the core `# Schema:` line as an
   absolute path; `derive core` writes the repository-relative path
   `src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml` even when given explicit
   absolute `--full-schema`/`--core-schema` paths. The core is not hand-edited, so the derived
   line stands; the schema file is the same one.

## Claims

No slots were removed.

## Semantic review

- `file_collections` ↔ `distributions` (checker warning): each of the 10 file collections maps
  to one distribution with the same id, name, description, conforms_to and byte total, and each
  of the 18 File entries maps to one distribution with the same id, format and media type —
  reviewed: consistent
- `total_file_count` against the entries beneath it: the 9 data-type collections sum to
  356,334 files; the stated total is 356,343; the difference of 9 equals the 9 root metadata
  files, which carry no file count (this record's computation from the stated per-directory
  `numberOfFiles` values and the stated `fileCount`) — reviewed: consistent
- `total_size_bytes` against the entries beneath it: the 9 data-type collections sum to
  3,815,969,360,064 bytes; the stated total is 3,815,969,779,678 bytes; the remaining
  419,614 bytes are not attributed by any source (root metadata files carry no size) and
  neither figure was adjusted (this record's computation) — reviewed: consistent
- `dialect` against the files: no File entry carries a dialect and the core has none —
  reviewed: consistent
- `is_tabular` against the files: absent in both records; the sources describe tabular, imaging
  and waveform data, so no single value is supported — reviewed: consistent
- Historical vs. current release: identity, counts, dates, sizes, license and formats describe
  version 3.0.0; v1.0.0 and v2.0.0 facts appear only in `version_access` and caveats, and the
  November 2024 license statement now carries its version scope (F2) — reviewed: corrected

## Files changed

- Full record (created in Phase 1; Phase 3 edits F1–F3).
- Coverage receipt (created in Phase 1; Phase 1 address corrections; Phase 3 back-port
  receipts added to entries c005, c007, c023).
- Core record (derived in Phase 2; re-derived in Phase 4).
- This report.
- Helper scripts (read-only diagnostics): `scripts/adhoc/list_unreceipted_slots.py`,
  `scripts/adhoc/sum_file_collections.py`, `scripts/adhoc/count_top_level_slots.py`.

## Commands

```bash
PY=/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/fast-d4d-20261121/.venv/bin/python
$PY -m data_sheets_schema.cli bundle chunk --bundle data/preprocessed/concatenated/AI_READI_preprocessed.txt --chunk-manifest data/preprocessed/chunks/AI_READI_chunks.yaml --manifest data/preprocessed/source_manifest.yaml --check --strict
$PY -m data_sheets_schema.cli download scope --manifest data/preprocessed/source_manifest.yaml --project AI_READI
$PY -m data_sheets_schema.cli agents playbook
$PY -c 'from linkml.validator.cli import cli; cli()' -s <abs full schema> -C Dataset <full>
$PY -c 'from linkml_term_validator.cli import main; main()' validate-data <full> --schema <abs full schema> --target-class Dataset
$PY -m data_sheets_schema.cli --manifest data/preprocessed/source_manifest.yaml receipts check --method claudecode_agent --label 2026-11-22b_claude-opus-5-5-claudecode-generic-v9_rep1 --project AI_READI --bundle data/preprocessed/concatenated/AI_READI_preprocessed.txt --chunk-manifest data/preprocessed/chunks/AI_READI_chunks.yaml --strict
$PY -m data_sheets_schema.cli derive core --full <full> --out <core>
$PY -m data_sheets_schema.cli derive core --full <full> --out <core> --phase4-complete
$PY -c 'from linkml.validator.cli import cli; cli()' -s <abs core schema> -C CoreDataset <core>
$PY -m data_sheets_schema.d4d_pair_consistency --full <full> --core <core>
$PY -c "...grounding.check_run(...)"
$PY -m data_sheets_schema.cli download scope --manifest data/preprocessed/source_manifest.yaml --project AI_READI --check --record <full> --record <core> --strict
```

## Final results

- Full: schema valid, term validation passed; 64 populated top-level slots (informational).
- Core: schema valid; 56 populated top-level slots (informational); header carries
  `# Sources:` and `# Phase 4 reconciliation: completed`.
- Receipt: strict check passes (25/25 chunks, 552/552 snippets, 602/602 slots).
- Pair checker: pass, one semantic warning reviewed above. Grounding: 0 absent identifiers.
- Phase 3 findings: 3 recorded, 3 corrected.
- Report-claims check: 0 findings, 0 claims checked (the checker does not yet read the
  "No slots were removed." sentinel, #684). Grounding, pair and report-claims checks reported
  nothing requiring a change, so no repair phase was run.
- Not run by this agent: the orchestrator transcript audit (`agentic_observed`) and
  `provenance annotate-observed`; this run had no observing orchestrator, and a phase agent
  does not estimate its own token or timing accounting.
