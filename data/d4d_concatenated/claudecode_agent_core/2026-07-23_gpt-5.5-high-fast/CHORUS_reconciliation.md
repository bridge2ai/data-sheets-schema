# CHORUS D4D Full/Core Reconciliation

Version: `2026-07-23_gpt-5.5-high-fast`
Model: gpt-5.5
Reasoning effort: high
Mode: fast
Temperature: 0.0
Generated: 2026-07-23

## Inputs

- Source: `data/preprocessed/concatenated/CHORUS_preprocessed.txt`
- Full D4D: `data/d4d_concatenated/claudecode_agent/2026-07-23_gpt-5.5-high-fast/CHORUS_d4d.yaml`
- Core D4D: `data/d4d_concatenated/claudecode_agent_core/2026-07-23_gpt-5.5-high-fast/CHORUS_d4d_core.yaml`
- Full schema: `src/data_sheets_schema/schema/data_sheets_schema_all.yaml` class `Dataset`
- Core schema: `src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml` class `CoreDataset`

## Overlap Summary

- Overlapping top-level schema slots checked: 33
- Discrepancies found: 2
- Discrepancies resolved: 2
- Remaining scalar conflicts: 0

## Discrepancies

| Field | Full value before reconciliation | Core value before reconciliation | Resolution | File(s) changed |
| --- | --- | --- | --- | --- |
| `publisher` | Omitted | `CHoRUS Consortium / Massachusetts General Hospital` | Back-ported to full. Source supports CHoRUS Consortium and Massachusetts General Hospital as awardee/lead organization. | Full |
| `is_tabular` | Omitted | `false` | Back-ported to full. Source describes CHoRUS as a multimodal dataset with OMOP EHR, telemetry waveforms, imaging, clinical notes, EEG, and social determinants of health data rather than a solely tabular dataset. | Full |

## Validation

| File | Command | Status |
| --- | --- | --- |
| Full | `poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_all.yaml -C Dataset data/d4d_concatenated/claudecode_agent/2026-07-23_gpt-5.5-high-fast/CHORUS_d4d.yaml` | Pass: `No issues found` |
| Core | `poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml -C CoreDataset data/d4d_concatenated/claudecode_agent_core/2026-07-23_gpt-5.5-high-fast/CHORUS_d4d_core.yaml` | Pass: `No issues found` |
| Full ontology terms | `poetry run linkml-term-validator validate-data data/d4d_concatenated/claudecode_agent/2026-07-23_gpt-5.5-high-fast/CHORUS_d4d.yaml --schema src/data_sheets_schema/schema/data_sheets_schema_all.yaml` | Blocked: command not found in the Poetry environment (`linkml-term-validator` package is present in `poetry.lock` but absent from `.venv`) |

## Final Status

The full and core YAML files pass the requested LinkML schema validations. The full ontology term validation could not be completed because the validator executable/module is not installed in the active Poetry environment.
