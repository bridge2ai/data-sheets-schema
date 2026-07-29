# AI_READI full/core reconciliation — 2026-07-28_claude-opus-5-deprimed_rep3

- Arm: HEALTHSHEET-ONLY (single structured upstream source)
- Runtime: Claude Code · Provider: Anthropic · Model: `claude-opus-5[1m]` · Temperature 0.0
- Mode: four-phase project agent, de-primed
- Declared input bundle: `data/preprocessed/concatenated/AI_READI_healthsheet_only.txt`
  (539 lines; 14 sections; 84 questions, 81 answered)
- Source manifest: not used; this arm declares its single source bundle explicitly
- Full: `data/d4d_concatenated/claudecode_agent_healthsheet/2026-07-28_claude-opus-5-deprimed_rep3/AI_READI_d4d.yaml`
- Core: `data/d4d_concatenated/claudecode_agent_healthsheet_core/2026-07-28_claude-opus-5-deprimed_rep3/AI_READI_d4d_core.yaml`

## Phase 3 — Source and provenance audit

### Provenance boundary

No prior generated D4D record was read, opened, grepped, or cited in any phase. The only
factual input was the declared bundle above. Structure was derived exclusively from
`Dataset` in `data_sheets_schema_all.yaml` and `CoreDataset` in
`data_sheets_schema_core_all.yaml`, resolved at runtime with LinkML `SchemaView`
(inherited slots, ranges, cardinality, inlining, `slot_usage`, enum permissible values).
No `d4d:docExample` annotation supplied a value. Output directory names were listed once,
only to confirm the target label directory did not already exist; no file under
`data/d4d_concatenated/` was opened other than this run's own outputs.

### Source disagreements found and how they were resolved

1. **Grant number rendered two ways.** The Motivation section gives `OT2ODO32644`; the
   Collection section gives `OT2OD032644`. Resolved in favour of `OT2OD032644` (the
   well-formed NIH activity-code form, and the form used in the answer that also states
   the funding mechanism for staff effort). The variant spelling is recorded verbatim in
   the `funders[0].grants[0].description` so the discrepancy is not silently erased.

2. **Scope of "all possible instances".** The Composition section says the dataset
   "contains data from all participants who have been enrolled during the first year of
   data collection for AI-READI", which contradicts the Versioning, Composition-count,
   and Collection sections, all of which scope version 3 to 2280 participants collected
   between July 19, 2023 and May 1, 2025 (through the end of the *second* year). The
   "first year" phrasing appears to be carried forward from the prior version's
   healthsheet. Resolved by recording the census claim without the stale year clause
   (`sampling_strategies[0].description`: "contains data from all participants enrolled
   during the data collection period covered by this version") and by recording the
   explicit dates in `collection_timeframes`. No fabricated reconciliation was inserted.

3. **"Released fall 2025" vs "distributed in November 2025".** Not a contradiction;
   November falls within the stated season. Both statements are retained in their
   respective slots (`instances[0].description`, `distribution_dates[0]`).

4. **Historical versions kept as explicitly historical.** v1 (204 participants, pilot,
   May 2024) and v2 (1067 total, first full year, November 2024) are recorded only in
   `version_access.versions_available` / `version_details` and `related_datasets`, always
   labelled by version, never as current-release facts.

### Unsupported / omitted assertions

The following were deliberately left absent because the declared bundle does not support
them: `keywords`, `issued` / `created_on` / `last_updated_on` (only month-level release
dates are given, which cannot be expressed as a datetime without inventing a day),
`download_url`, `file_collections`, `total_file_count`, `total_size_bytes`, `compression`,
`errata` (the erratum question has no response), `at_risk_populations`,
`imputation_protocols`, `annotation_analyses`, `machine_annotation_tools`,
`parent_datasets`, and — in core — `distributions` and `dialect`. The bundle contains no
file-level, format-level, checksum, or byte-count information at all, so the entire
physical-distribution layer is empty by evidence, not by oversight.
`license_and_use_terms.data_use_permission` was left unset: the license text itself is not
in the bundle, and no DUO permissible value can be asserted from the summary alone.
Three healthsheet questions carry no answer (de-identification pre-processing,
re-identification measures, erratum); the de-identification gap is recorded explicitly in
`is_deidentified.deidentification_details` rather than being papered over.

### Phase 2 discoveries back-ported into the full record

Phase 2 (core derivation plus a second pass over the bundle) surfaced four
source-supported items that Phase 1 had missed or had placed only in a full-only slot.
All four were corrected in the **full** record first, and the core record was then
re-projected from the corrected full record.

| # | Fact | Slot corrected in full |
|---|------|------------------------|
| 1 | "The dataset has not undergone any formal external audits. However, the dataset has been reviewed internally by AI-READI team members for quality checks…" — present in the bundle's General Information section, previously only partially reflected | `cleaning_strategies[0].cleaning_details` |
| 2 | Device make/model documentation for repeatability; multiple devices per measure to enhance generalizability; uniform protocols across sites | new `collection_mechanisms` entry `d4d:AI_READI_mechanism_device_documentation` |
| 3 | "The data relate to people… collected in the USA" existed only in `direct_collection`, which is a full-only slot and therefore invisible to core | added to `acquisition_methods[0].acquisition_details` (shared slot) |
| 4 | The 70%/15%/15% split proportions existed only in `splits`/`subsets`, both full-only slots | added to `subpopulations[0].description` (shared slot) |

Items 3 and 4 are placement corrections rather than new facts: the underlying evidence was
already extracted, but it sat in slots the core schema does not carry, so the core record
would have lost it. No fact was moved into core that is absent from the bundle.

### Re-validation after corrections

Both files were re-validated after every correction (commands below); all passes clean.

## Phase 4 — Strict full/core reconciliation

### Schema-derived shared-slot inventory

Computed at runtime from `Dataset` and `CoreDataset` with `SchemaView`, not from a
hand-written list:

- Core slot inventory: **79**
- Shared slots (present in both classes): **77**
- Schema-identical shared slots (same induced range and cardinality): **76**
- Projected shared slots (range differs): **1** — `resources` (`Dataset` in full,
  `CoreDataset` in core)
- Core-only slots: **2** — `distributions`, `dialect`
- Full-only slots: **17** — `citation`, `collection_consents`, `collection_notifications`,
  `consent_revocations`, `direct_collection`, `file_collections`, `parent_datasets`,
  `participant_compensation`, `participant_privacy`, `related_datasets`, `relationships`,
  `splits`, `subsets`, `third_party_sharing`, `total_file_count`, `total_size_bytes`,
  `variables`

### Identity result

`PASS: 76 schema-identical slots; projected slots=['resources']` — no warnings.

Every schema-identical shared slot has identical presence and deeply identical parsed YAML
content across the pair, including narrative fields. Core condenses, paraphrases,
reorders, and omits nothing that the two schemas share; it was produced by mechanical
projection of the audited full record, so identity is structural rather than
hand-maintained.

`resources` is absent from both records (the bundle describes no nested sub-datasets that
carry their own identity), so the projection is vacuously equal — coverage matches and
there are no nested objects to compare.

### Related, non-identical content — semantic review

The validator emits no warnings here because the related-content slots are empty on both
sides, but the review was performed rather than assumed:

- **`file_collections` → `distributions`.** Both empty. The bundle states only that "all
  modalities, file formats, and devices are detailed in the dataset documentation at
  https://docs.aireadi.org"; it enumerates no path, format, compression, checksum, byte
  count, or access URL. Nothing to map, and nothing to conflict.
- **`total_file_count` / `total_size_bytes` vs distribution-level values.** All absent on
  both sides; no scope mismatch is possible.
- **`dialect`, formats, `is_tabular`.** `dialect` is absent (no tabular dialect facts).
  `is_tabular: false` is identical in both records and is consistent with the bundle's
  statement that the modalities "encompass tabular data, imaging data, and physiological
  signal/waveform data" — i.e. the dataset is not exclusively tabular.
- **Identity / version / access facts vs version history and distributions.** `id`
  (`https://doi.org/10.60775/fairhub.3`), `doi` (`10.60775/fairhub.3`), `version` (`"3"`),
  `version_access.latest_version_doi`, the version-3 row of
  `version_access.versions_available`, `distribution_dates[0].release_dates`
  ("November 2025 (version 3)"), `distribution_formats[0].access_urls`, and `status` all
  agree with one another and are identical in full and core. Participant count 2280 is
  stated consistently in `instances[0].counts`, `instances[0].description`,
  `tasks[1].response`, and the version-3 row of `versions_available`. `license`
  (`https://doi.org/10.5281/zenodo.17555036`) agrees with
  `license_and_use_terms`, `ip_restrictions`, `regulatory_restrictions`, and
  `discouraged_uses`. Historical releases are carried only in explicitly version-labelled
  slots and are not treated as contradictions of the current release.

### Files changed in Phase 3/4

- `…/claudecode_agent_healthsheet/2026-07-28_claude-opus-5-deprimed_rep3/AI_READI_d4d.yaml`
  — four Phase 3 back-ports (table above).
- `…/claudecode_agent_healthsheet_core/2026-07-28_claude-opus-5-deprimed_rep3/AI_READI_d4d_core.yaml`
  — re-projected from the corrected full record; `--sync-core` then run once as prescribed
  (it introduced no content change, only the `Phase 4 reconciliation: completed` header
  line and formatting normalisation).

### Commands run

```bash
poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_all.yaml \
  -C Dataset data/d4d_concatenated/claudecode_agent_healthsheet/2026-07-28_claude-opus-5-deprimed_rep3/AI_READI_d4d.yaml

poetry run linkml-term-validator validate-data \
  data/d4d_concatenated/claudecode_agent_healthsheet/2026-07-28_claude-opus-5-deprimed_rep3/AI_READI_d4d.yaml \
  --schema src/data_sheets_schema/schema/data_sheets_schema_all.yaml --target-class Dataset

poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml \
  -C CoreDataset data/d4d_concatenated/claudecode_agent_healthsheet_core/2026-07-28_claude-opus-5-deprimed_rep3/AI_READI_d4d_core.yaml

poetry run linkml-term-validator validate-data \
  data/d4d_concatenated/claudecode_agent_healthsheet_core/2026-07-28_claude-opus-5-deprimed_rep3/AI_READI_d4d_core.yaml \
  --schema src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml --target-class CoreDataset

poetry run python -m data_sheets_schema.d4d_pair_consistency \
  --full …/AI_READI_d4d.yaml --core …/AI_READI_d4d_core.yaml --sync-core

poetry run python -m data_sheets_schema.d4d_pair_consistency \
  --full …/AI_READI_d4d.yaml --core …/AI_READI_d4d_core.yaml

poetry run d4d provenance record --project AI_READI --method claudecode_agent_healthsheet \
  --label 2026-07-28_claude-opus-5-deprimed_rep3 \
  --input-bundle data/preprocessed/concatenated/AI_READI_healthsheet_only.txt
```

### Final results

| Check | Result |
|---|---|
| Full schema validation (`Dataset`) | No issues found |
| Full term validation | Validation passed |
| Core schema validation (`CoreDataset`) | No issues found |
| Core term validation | Validation passed |
| Pair consistency (final, no `--sync-core`) | PASS — 76 schema-identical slots, projected `resources` |
| Provenance record | `AI_READI_provenance.yaml`, `record_mode: live` |
| Prior-D4D factual reuse | None |

Top-level populated slots: **74** in full, **61** in core (74 − 13 populated full-only
slots). Informational only, not a quality gate.

Unresolved contradictions within or between the two records: **none**.
