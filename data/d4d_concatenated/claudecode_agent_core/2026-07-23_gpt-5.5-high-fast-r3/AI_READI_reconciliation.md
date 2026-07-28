# AI_READI D4D Phase 3/4 Reconciliation

Version: `2026-07-23_gpt-5.5-high-fast-r3`

## Run Metadata

- Agent runtime: Codex CLI
- Provider: OpenAI
- Model: gpt-5.5
- Reasoning effort: high
- Mode: fast
- Prior D4D factual reuse: prohibited

## Allowed Inputs

- `data/preprocessed/concatenated/AI_READI_preprocessed.txt`
- `data/preprocessed/source_manifest.yaml`
- `src/data_sheets_schema/schema/data_sheets_schema_all.yaml`
- `src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml`
- Same-run full and core records from this version directory

No earlier D4D, evaluation, or reconciliation report was used as factual
evidence.

## Phase 3: Source And Provenance Audit

- The full and core identity, DOI, version, dates, counts, size, license, access
  rules, participant scope, and ethics content were checked against the current
  bundle.
- The current FAIRhub scope is internally consistent: version `3.0.0`, DOI
  `10.60775/fairhub.3`, 165,051 files, and 2.01 TB.
- `total_file_count` and `total_size_bytes` agree with the current
  `file_collections` entry and the core current-dataset distribution.
- No source-supported Phase 2 discovery required a factual correction in full.
- The provenance boundary passed.

## Phase 4: Strict Pair Reconciliation

- LinkML-derived schema-identical root slots: 76.
- Schema-projected shared slots: `resources`.
- All 76 strict slots were already deeply identical before synchronization.
- `resources` is absent from both records, so its projection is consistent.
- The Phase 4 synchronization preserved core-only `distributions` and added the
  completion marker to the core header.

Related-content review:

- Full `files-all` maps to the core current-dataset distribution.
- Public, controlled, documentation, and license collections map to their core
  distributions by scope and path.
- CSV and XML core distributions describe formats within the current dataset;
  they do not claim separate full-dataset counts or sizes.
- Counts, bytes, paths, access scope, formats, license facts, and version facts
  contain no unresolved contradiction.

## Final Validation

- Full `Dataset` schema validation: passed.
- Full term validation: passed.
- Core `CoreDataset` schema validation: passed.
- Core term validation: passed.
- Phase 4 pair validation: passed with zero errors.
- Related-content semantic review: passed.

