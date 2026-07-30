# VOICE D4D Phase 3/4 Reconciliation

Version: `2026-07-23_gpt-5.5-high-fast-r3`

## Run Metadata

- Agent runtime: Codex CLI
- Provider: OpenAI
- Model: gpt-5.5
- Reasoning effort: high
- Mode: fast
- Prior D4D factual reuse: prohibited

## Allowed Inputs

- `data/preprocessed/concatenated/VOICE_preprocessed.txt`
- `data/preprocessed/source_manifest.yaml`
- `src/data_sheets_schema/schema/data_sheets_schema_all.yaml`
- `src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml`
- Same-run full and core records from this version directory

No earlier D4D, evaluation, or reconciliation report was used as factual
evidence.

## Phase 3: Source And Provenance Audit

- The manifest-selected detailed PhysioNet input is v3.0.0, DOI
  `10.13026/k81f-qr68`, released `2025-12-16`.
- That page identifies v3.1.0 and DOI `10.13026/37yb-1t42` as latest but does
  not provide a selected v3.1.0 file inventory. The top level therefore remains
  v3.0.0; the v3.1.0 pointer is explicitly recorded under `version_access`.
- Participant count, modalities, registered versus controlled access, raw-audio
  restrictions, license terms, consent, and privacy facts are internally
  consistent.
- The provenance boundary passed.

## Phase 4: Strict Pair Reconciliation

- LinkML-derived schema-identical root slots: 76.
- Schema-projected shared slots: `resources`.
- Before correction, 46 shared slots differed because core narratives and
  nested objects had been condensed.
- The Phase 3-audited full values were copied without paraphrase into every
  schema-identical core slot.
- `resources` is absent from both records, so its projection is consistent.
- Core-only `dialect` and `distributions` were preserved.
- The core header records Phase 4 completion.

Related-content review mapped all four file collections to core distributions
by path:

- derived Parquet features
- static feature TSV plus JSON dictionary
- phenotype TSV plus JSON dictionaries
- release documentation

The tabular flag, TSV dialect, paths, formats, public-derived-data scope,
v3.0.0 identity, and raw-audio controlled-access statements contain no
unresolved contradiction. The v3.1.0 latest-version pointer is not applied to
v3.0.0 file details.

## Final Validation

- Full `Dataset` schema validation: passed.
- Full term validation: passed.
- Core `CoreDataset` schema validation: passed.
- Core term validation: passed.
- Phase 4 pair validation: passed with zero errors.
- Related-content semantic review: passed.

