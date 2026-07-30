# CM4AI D4D Phase 3/4 Reconciliation

Version: `2026-07-23_gpt-5.5-high-fast-r3`

## Run Metadata

- Agent runtime: Codex CLI
- Provider: OpenAI
- Model: gpt-5.5
- Reasoning effort: high
- Mode: fast
- Prior D4D factual reuse: prohibited

## Allowed Inputs

- `data/preprocessed/concatenated/CM4AI_preprocessed.txt`
- `data/preprocessed/source_manifest.yaml`
- `src/data_sheets_schema/schema/data_sheets_schema_all.yaml`
- `src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml`
- Same-run full and core records from this version directory

No earlier D4D, evaluation, or reconciliation report was used as factual
evidence.

## Phase 3: Source And Provenance Audit

- The current top-level scope is the June 2026 HIGT4C release. The manifest
  resolves the project-page year anomaly with official Dataverse metadata:
  publication `2026-06-17`, version 2 update `2026-07-15T20:28:19Z`.
- March 2025, June 2025, and October 2025 releases remain explicitly historical
  resources and file collections.
- Phase 4 exposed one scope error missed by the earlier audit:
  `total_file_count: 8` described the October 2025 K7TGEM release but appeared
  unqualified at the June 2026 top level. It was removed from the top level and
  retained as `file_count: 8` only on the October 2025 collection.
- The provenance boundary passed.

## Phase 4: Strict Pair Reconciliation

- LinkML-derived schema-identical root slots: 76.
- Schema-projected shared slots: `resources`.
- Before correction, core contained condensed or incomplete values for 26
  shared slots, omitted the shared `anomalies` slot, and omitted the
  `resources` projection.
- The Phase 3-audited full values were copied without paraphrase into every
  schema-identical core slot.
- Four full `Dataset` resources were projected to `CoreDataset` resources with
  identical IDs and identical content for every compatible nested slot.
- Core-only `distributions` were preserved.
- The core header records Phase 4 completion.

Related-content review:

- Eight October 2025 core distributions map by exact ID to the eight
  file-level full collections.
- ZIP format, compression, MD5 values, data modality, treatment/cell context,
  and publication dates agree.
- The four release-level collections are not file-level distributions; their
  release/version facts are represented by the projected resources.
- June 2026 current-release facts and October 2025 historical distribution
  facts are explicitly scoped and do not conflict.

## Final Validation

- Full `Dataset` schema validation: passed.
- Full term validation: passed.
- Core `CoreDataset` schema validation: passed.
- Core term validation: passed.
- Phase 4 pair validation: passed with zero errors.
- Related-content semantic review: passed.

