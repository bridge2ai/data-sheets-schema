# CHORUS D4D Phase 3/4 Reconciliation

Version: `2026-07-23_gpt-5.5-high-fast-r3`

## Run Metadata

- Agent runtime: Codex CLI
- Provider: OpenAI
- Model: gpt-5.5
- Reasoning effort: high
- Mode: fast
- Prior D4D factual reuse: prohibited

## Allowed Inputs

- `data/preprocessed/concatenated/CHORUS_preprocessed.txt`
- `data/preprocessed/source_manifest.yaml`
- `src/data_sheets_schema/schema/data_sheets_schema_all.yaml`
- `src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml`
- Same-run full and core records from this version directory

No earlier D4D, evaluation, or reconciliation report was used as factual
evidence.

## Phase 3: Source And Provenance Audit

- The four manifest-selected sources were used, including the explicitly
  retained 2025-11-14 GitHub organization overview.
- The website and webinar report different time-scoped admission counts:
  50,000 on the current website and more than 45,000 in the August 2025
  webinar. Both remain explicitly scoped and are recorded as an anomaly rather
  than silently merged.
- Identity, hospital count, modalities, access controls, standards, funding,
  ethics, and limitations are internally consistent.
- No source-supported Phase 2 discovery required a factual correction in full.
- The provenance boundary passed.

## Phase 4: Strict Pair Reconciliation

- LinkML-derived schema-identical root slots: 76.
- Schema-projected shared slots: `resources`.
- All 76 strict slots were already deeply identical before synchronization.
- `resources` is absent from both records, so its projection is consistent.
- The Phase 4 synchronization preserved core-only `distributions` and added the
  completion marker to the core header.

Related-content review mapped the six full collections to six core
distributions by modality:

- OMOP EHR
- tokenized clinical notes
- DICOM imaging
- WFDB waveform telemetry
- EDF+/Persyst EEG
- published metadata schema

The 1.6-billion-row EHR value, 7,642 radiology-admission value, 23 TB waveform
value, modality formats, controlled-access scope, and historical/current
admission counts contain no unresolved contradiction.

## Final Validation

- Full `Dataset` schema validation: passed.
- Full term validation: passed.
- Core `CoreDataset` schema validation: passed.
- Core term validation: passed.
- Phase 4 pair validation: passed with zero errors.
- Related-content semantic review: passed.

