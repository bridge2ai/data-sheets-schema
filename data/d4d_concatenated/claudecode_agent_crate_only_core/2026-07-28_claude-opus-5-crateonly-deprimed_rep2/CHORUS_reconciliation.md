# CHORUS full/core reconciliation — 2026-07-28_claude-opus-5-crateonly-deprimed_rep2

- **Project:** CHORUS
- **Arm:** CRATE-ONLY (RO-Crate evidence alone; document corpus withheld)
- **Version label:** `2026-07-28_claude-opus-5-crateonly-deprimed_rep2`
- **Runtime / provider / model:** Claude Code / Anthropic / `claude-opus-5[1m]`
- **Mode:** four-phase project agent, crate-only, de-primed
- **Temperature:** 0.0

## Inputs

| Role | Path |
|---|---|
| Declared source bundle (only factual source) | `data/preprocessed/concatenated/CHORUS_crate_only.txt` |
| Full schema | `src/data_sheets_schema/schema/data_sheets_schema_all.yaml` (class `Dataset`) |
| Core schema | `src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml` (class `CoreDataset`) |
| Phase 2 additional input | `data/d4d_concatenated/claudecode_agent_crate_only/2026-07-28_claude-opus-5-crateonly-deprimed_rep2/CHORUS_d4d.yaml` (same-run Phase 1 full) |

`data/preprocessed/source_manifest.yaml` was **not** read: this arm declares a single
source bundle and the manifest plus the document corpus are withheld by design.

## Outputs

| Role | Path |
|---|---|
| Full | `data/d4d_concatenated/claudecode_agent_crate_only/2026-07-28_claude-opus-5-crateonly-deprimed_rep2/CHORUS_d4d.yaml` |
| Core | `data/d4d_concatenated/claudecode_agent_crate_only_core/2026-07-28_claude-opus-5-crateonly-deprimed_rep2/CHORUS_d4d_core.yaml` |
| Report | this file |

## Phase 3 — source and provenance audit

### Provenance boundary

No prior generated D4D record was read, opened, grepped, or consulted. Nothing under
`data/d4d_concatenated/` other than this run's own two output paths was accessed, and no
`*_crate_d4d.yaml` or `*_crate_mapped_d4d.yaml` under `data/ro-crate_packages/` was
accessed. Record structure was derived at runtime from the two LinkML schemas via
`SchemaView` (`class_induced_slots`), not from any example record. All dataset facts trace
to `CHORUS_crate_only.txt`.

The bundle itself declares that the D4D-shaped artifacts (`CHORUS_crate_d4d.yaml`,
`ro-crate-linkml.yaml`, `ro-crate-datasheet.html`) are withheld; this run honoured that and
extracted only from `CHORUS_crate_metadata_reduced.json` and `ai_ready_score.json`.

### Evidence assessment

The crate is a rich but uneven source. It is strong on governance, ethics, access control,
responsible-AI narrative (`rai:*` fields), licensing, and maintenance, and it carries a
complete author and affiliation roster. It is thin on composition: there are **no instance
counts, no cohort size, no demographic distributions, no collection date range, no
per-variable metadata, and no file-level inventory** (file inventories were deliberately
collapsed in the reduced JSON). Several optional schema sections were therefore left absent
rather than filled: `content_warnings`, `subpopulations`, `relationships`, `subsets`,
`file_collections`, `collection_timeframes`, `collection_notifications`,
`consent_revocations`, `cleaning_strategies`, `labeling_strategies`,
`imputation_protocols`, `annotation_analyses`, `existing_uses`, `use_repository`,
`other_tasks`, `errata`, `retention_limit`, `extension_mechanism`, `variables`,
`participant_compensation`, `at_risk_populations`, `is_tabular`, `compression`, `language`.

### Internal consistency checks against the bundle

| Check | Result |
|---|---|
| `version` across package, EHR sub-crate, waveforms sub-crate | consistent (`1.0 Beta`) |
| Publication dates | package and waveforms give ISO `2026-04-03`; EHR gives `03/04/2026` and top-level `releaseDate` gives `03/04/2026`. Read as DD/MM/YYYY, all four agree on 2026-04-03. Recorded as ISO `2026-04-03` with the DD/MM/YYYY variant noted in `distribution_dates[0].description`. Not a contradiction. |
| DOI vs citation | DOI `10.18130/V3/XNBOPG` and citation "Harvard Dataverse, Apr. 2026" agree in repository and month |
| `license` | package: "Data Use Agreement available at 'https://chorus4ai.org/dataset/'"; sub-crates: "See Data Use Agreement". Recorded verbatim per entity; different wording, same instrument, no conflict |
| `contentUrl` | package `http://chorus4ai.org/dataset`; sub-crates `https://chorus4ai.org/dataset/`. Recorded verbatim per entity |
| PI identity | `principalInvestigator` "Eric Rosenthal", sub-crates "PI Eric Rosenthal", author list "Eric S. Rosenthal(1)", `dataGovernanceCommittee` "Eric Rosenthal" — one person |
| `rai:dataBiases` vs `rai:potentialBiases` | byte-identical; recorded once under `known_biases` |
| `rai:dataReleaseMaintenancePlan` vs `rai:maintenancePlan` | byte-identical; recorded once under `updates` |
| Size figures | package `1.2 tb`; waveforms `1.201567472832 tb`; EHR `18.136671 mb`. Sub-crate figures converted decimally to exact byte counts (1201567472832 and 18136671) and placed on the corresponding `resources` entries. The package's own `1.2 tb` is a two-significant-figure restatement, so no top-level `total_size_bytes` was asserted rather than presenting a rounded or computed value as exact. |
| File counts | `total_file_count: 1477` from "99% of files have checksums (1469/1477)". The separate "1468 dataset(s) documented" figure counts crate dataset entities, a different scope; no contradiction, and it was not recorded as a file or instance count. |

### Corrections applied in Phase 3

Four defects were found in the Phase 1 record and corrected in the full record first; the
core record was then regenerated from the corrected full.

1. **Inconsistent person reference.** `regulatory_restrictions.governance_committee_contact`
   referenced `person_eric_rosenthal` while `creators[0].principal_investigator` referenced
   `person_eric_s_rosenthal`, for the same individual. Unified to
   `person_eric_s_rosenthal`.
2. **Mis-scoped `machine_annotation_tools`.** The entry listed RSNA Clinical Trial Processor
   and IbisWorks EICON alongside the OHNLP toolkit. Those two are de-identification tools,
   not automated annotation or labeling systems; the schema class covers NLP pipelines,
   computer vision models, and automated labeling systems. Narrowed to the OHNLP toolkit
   only. The de-identification tools remain documented under `preprocessing_strategies`,
   `participant_privacy`, and `is_deidentified`, where the bundle places them.
3. **Out-of-scope content in `instances`.** The instance description carried crate-inventory
   counts (files, schemas, computation steps, software instances), which describe the crate
   package rather than what a data instance represents. Removed; the file total is retained
   in `total_file_count`, and the "44 schemas / 2 computation steps / 1 software instance"
   provenance counts were dropped entirely as having no supported D4D slot.
4. **Over-escalated prohibition.** A `prohibited_uses` entry asserted that contact tracing
   and patient-level intervention are prohibited. The bundle lists those under
   `rai:dataLimitations` as "not appropriate", not as prohibitions; only re-identification is
   explicitly prohibited (`rai:personalSensitiveInformation`: "Prohibition of
   re-identification attempts"). Narrowed the entry to re-identification. Contact tracing and
   patient-level intervention remain under `known_limitations` with the source's own framing.

No Phase 2 discovery required back-porting into the full record: `CoreDataset` is a strict
slot subset of `Dataset` for every slot this bundle supports, so Phase 2 surfaced no fact
that the full record lacked.

### Interpretive mappings recorded (source value preserved verbatim)

These are the points where the schema required a controlled value and the source supplied
free text. Each is listed so the mapping can be audited.

| Slot | Source text | Recorded value |
|---|---|---|
| `regulatory_restrictions.confidentiality_level` | `HL7:2V (very restricted)` | `confidential` (verbatim source retained in `regulatory_restrictions.description`) |
| `regulatory_restrictions.hipaa_compliant` | "maintaining compliance with HIPAA" | `compliant` |
| `known_biases[].bias_type` | six free-text bullets | `selection_bias` (referral), `representation_bias` (socioeconomic/demographic), `measurement_bias` (note documentation), `sampling_bias` (MNAR acquisition), `annotation_bias` (differential care pathways affecting label assignment), `historical_bias` (temporal practice trends) |
| `known_limitations[].limitation_type` | eight free-text bullets | `methodological_limitation` ×3, `resolution_limitation`, `integration_limitation`, `representativeness_limitation`, `scope_limitation`, `coverage_limitation` |
| `license_and_use_terms.data_use_permission` | `rai:conditionsOfAccess` prose | `health_medical_biomedical_research`, `no_commercial_use`, `ethics_approval_required`, `project_specific`, `institution_specific` |
| `acquisition_methods[].was_reported_by_subjects` | "not through prospective research interactions with patient" | `false` |
| `sampling_strategies[].is_representative` | "Limited generalizability beyond participating hospitals" | `false` |
| `is_deidentified.identifiable_elements_present` | `"deidentified": true`, HIPAA Safe Harbor | `false` (residual re-identification risk retained in `deidentification_details`) |

## Phase 4 — strict full/core reconciliation

### Schema-derived shared slots

Derived at runtime with `data_sheets_schema.d4d_pair_consistency.load_pair_schema()`, which
compares induced slot signatures (range, multivalued, required, cardinality,
`inlined_as_list`) between `Dataset` and `CoreDataset`:

- **schema-identical slots: 76** — must be present in both or neither, with deeply identical
  parsed YAML including nested mapping values and list order.
- **projected slots: 1** — `resources` (`Dataset` in full, `CoreDataset` in core).

### Result

Deep identity holds for all 76 schema-identical slots. Presence matches in both directions.
No narrative field was condensed, paraphrased, reordered, or omitted in core.

### `resources` projection

Two sub-resources, matched by `id` with equal coverage:

- `urn:uuid:08cf7419-b94d-4508-8f64-c99c557351d7` — CHoRUS RO-Crate EHR SubRoCrate
- `urn:uuid:b9b41c72-0895-4ec2-9e39-8de2a83abcd6` — CHoRUS RO-Crate Waveforms SubRoCrate

Every schema-identical nested slot is deeply identical across the projection. Full-only
nested slots are omitted from the core projection, as the projection rule requires:
`total_size_bytes`, `citation`, and `related_datasets` have no counterpart in `CoreDataset`.

### Full-only top-level slots (schema-driven, not a discrepancy)

`CoreDataset` does not declare these slots, so their content exists only in the full record:
`total_file_count`, `citation`, `splits`, `direct_collection`, `participant_privacy`,
`third_party_sharing`.

### Related, non-identical representations — semantic review

- **`file_collections` ↔ `distributions`:** neither record populates either slot. The reduced
  crate JSON collapses file inventories, so there is no evidence of named file collections
  with paths, formats, checksums, or per-collection byte counts. The validator raised no
  distribution-relation issue because both sides are absent. Nothing to reconcile.
- **`total_file_count` / `total_size_bytes` vs distribution-level values:** no
  distribution-level values exist to compare against. `total_file_count: 1477` is asserted
  only in the full record and is consistent with the sub-resource byte totals in that the two
  figures describe different quantities (file count vs bytes) and neither contradicts the
  other.
- **`dialect`, formats, `is_tabular`:** `dialect` and `is_tabular` are unpopulated in both
  records; the bundle reports mixed formats (`.ipynb`, `text/tab-separated-values`, `wfdb`),
  which supports neither a tabular assertion nor a CSV/TSV dialect. Format evidence is carried
  narratively in `distribution_formats[0].description` in both records, identically.
- **Identity / version / access facts vs resources, version history, distributions:**
  `version` (`1.0 Beta`) agrees between the top level and both sub-resources in both records;
  `version_access.versions_available` ("1.0 Beta (published 2026-04-03)") agrees with
  `distribution_dates` (`2026-04-03`) and with `version_access.latest_version_doi`
  (`https://doi.org/10.18130/V3/XNBOPG`), which agrees with top-level `doi`
  (`10.18130/V3/XNBOPG`). Access statements agree across `external_resources.restrictions`,
  `license_and_use_terms.license_terms`, `prohibited_uses`, and
  `regulatory_restrictions.regulatory_restrictions`.
- **Historical vs current release:** only one release (1.0 Beta) is described. The maintenance
  plan's references to prior-version archiving are forward-looking policy, not a competing
  historical release, and were not treated as a contradiction.

Zero unresolved contradictions within or between the two records.

## Files changed

- `data/d4d_concatenated/claudecode_agent_crate_only/2026-07-28_claude-opus-5-crateonly-deprimed_rep2/CHORUS_d4d.yaml` (created Phase 1; four Phase 3 corrections)
- `data/d4d_concatenated/claudecode_agent_crate_only_core/2026-07-28_claude-opus-5-crateonly-deprimed_rep2/CHORUS_d4d_core.yaml` (created Phase 2; regenerated after Phase 3 corrections; Phase 4 `--sync-core`)
- `data/d4d_concatenated/claudecode_agent_crate_only_core/2026-07-28_claude-opus-5-crateonly-deprimed_rep2/CHORUS_reconciliation.md` (this file)

No previously populated version directory was overwritten.

## Commands

```bash
FULL=data/d4d_concatenated/claudecode_agent_crate_only/2026-07-28_claude-opus-5-crateonly-deprimed_rep2/CHORUS_d4d.yaml
CORE=data/d4d_concatenated/claudecode_agent_crate_only_core/2026-07-28_claude-opus-5-crateonly-deprimed_rep2/CHORUS_d4d_core.yaml

poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_all.yaml -C Dataset $FULL
poetry run linkml-term-validator validate-data $FULL \
  --schema src/data_sheets_schema/schema/data_sheets_schema_all.yaml --target-class Dataset

poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml -C CoreDataset $CORE
poetry run linkml-term-validator validate-data $CORE \
  --schema src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml --target-class CoreDataset

poetry run python -m data_sheets_schema.d4d_pair_consistency --full $FULL --core $CORE --sync-core
poetry run python -m data_sheets_schema.d4d_pair_consistency --full $FULL --core $CORE

poetry run d4d provenance record --project CHORUS --method claudecode_agent_crate_only \
  --label 2026-07-28_claude-opus-5-crateonly-deprimed_rep2 \
  --input-bundle data/preprocessed/concatenated/CHORUS_crate_only.txt
```

## Final results

| Check | Result |
|---|---|
| Full — `linkml-validate` (`Dataset`) | PASS ("No issues found") |
| Full — `linkml-term-validator` | PASS |
| Core — `linkml-validate` (`CoreDataset`) | PASS ("No issues found") |
| Core — `linkml-term-validator` | PASS |
| Pair consistency (with `--sync-core`) | PASS — 76 schema-identical slots; projected slots `['resources']` |
| Pair consistency (independent re-run) | PASS — 76 schema-identical slots; projected slots `['resources']` |
| Full top-level populated slots | 58 |
| Core top-level populated slots | 52 |
| Core header `Phase 4 reconciliation: completed` | present |
| Prior-D4D factual reuse | none |

## Run-environment note

This agent shared a session scratchpad directory with concurrently running sibling agents. A
sibling overwrote the generic scratchpad script path `mkcore.py` between two of this run's
commands, so one command in this run executed the sibling's script (targeting the
`...-deprimed_rep3` paths) instead of this run's. This run's own outputs were unaffected — the
core record was regenerated from the corrected full record using a uniquely named script
under `scratchpad/neutral_rep2_chorus/`, and the final validations above were all run against
this run's two files. The `-deprimed_rep3` outputs may have been written at an unintended
point in that sibling's sequence and are worth re-checking by whoever owns that run.
