# CM4AI D4D Full/Core Reconciliation

Version: `2026-07-23_gpt-5.5-high-fast`
Model: gpt-5.5
Reasoning effort: high
Mode: fast
Temperature: 0.0
Generated: 2026-07-23

## Inputs

- Source: `data/preprocessed/concatenated/CM4AI_preprocessed.txt`
- Full D4D: `data/d4d_concatenated/claudecode_agent/2026-07-23_gpt-5.5-high-fast/CM4AI_d4d.yaml`
- Core D4D: `data/d4d_concatenated/claudecode_agent_core/2026-07-23_gpt-5.5-high-fast/CM4AI_d4d_core.yaml`
- Full schema: `src/data_sheets_schema/schema/data_sheets_schema_all.yaml` class `Dataset`
- Core schema: `src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml` class `CoreDataset`
- Core module: `src/data_sheets_schema/schema/D4D_Core.yaml`

## Overlap Summary

- Overlapping top-level schema slots checked: 35
- Discrepancies found: 6
- Discrepancies resolved: 6
- Remaining scalar conflicts: 0

## Discrepancies

| Field | Full value before reconciliation | Core value before reconciliation | Resolution | File(s) changed |
| --- | --- | --- | --- | --- |
| `doi` | Omitted | `10.18130/V3/DXWOS5` | Back-ported to full from core and source DOI record. | Full |
| `version` | Omitted | `"2.1"` | Back-ported to full from core and source Dataverse release records. | Full |
| `download_url` | Omitted | `https://doi.org/10.18130/V3/DXWOS5` | Back-ported to full from core and source data availability statement. | Full |
| `publisher` | Omitted | `University of California San Diego` | Reconciled to `University of Virginia Dataverse`, supported by the source DOI/Data Availability record identifying the data release publisher. | Full and core |
| `is_tabular` | Omitted | `false` | Back-ported to full. Source describes multimodal RO-Crate, image, SEC-MS, and perturb-seq data rather than a solely tabular dataset. | Full |
| Core distribution mirror | No full-schema `file_collections` entries for core distribution landing pages | `distributions` included primary, March 2025, June 2025, and October 2025 release landing pages | Added full-schema `file_collections` entries for the same release landing pages. Nested file entries were omitted because the current generated full-schema validator rejects `File` objects under `FileCollection.resources`. | Full |

## Validation

| File | Command | Status |
| --- | --- | --- |
| Full | `poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_all.yaml -C Dataset data/d4d_concatenated/claudecode_agent/2026-07-23_gpt-5.5-high-fast/CM4AI_d4d.yaml` | Pass: `No issues found` |
| Core | `poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml -C CoreDataset data/d4d_concatenated/claudecode_agent_core/2026-07-23_gpt-5.5-high-fast/CM4AI_d4d_core.yaml` | Pass: `No issues found` |
| Full ontology terms | `poetry run linkml-term-validator validate-data data/d4d_concatenated/claudecode_agent/2026-07-23_gpt-5.5-high-fast/CM4AI_d4d.yaml --schema src/data_sheets_schema/schema/data_sheets_schema_all.yaml` | Blocked: command not found in the Poetry environment (`linkml-term-validator` is present in `poetry.lock` but no executable or importable module is installed in the active environment) |

## Final Status

The full and core YAML files pass the requested LinkML schema validations. There are zero remaining scalar conflicts across overlapping fields. The additional full ontology term validation from the repository workflow could not be completed because the validator executable/module is absent from the active Poetry environment.
