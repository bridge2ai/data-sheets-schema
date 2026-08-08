# CHORUS full/core reconciliation

- Run label: `2026-08-07_claude-opus-5-claudecode-generic-v3_rep1`
- Arm: BASELINE (input documents only)
- Mode: four-phase project agent, generic prompt
- Runtime / provider / model: Claude Code / Anthropic / claude-opus-5
- Reasoning effort: high
- Prompt: `src/download/prompts/d4d_generic_arm_prompt.md`
- Declared input bundle: `data/preprocessed/concatenated/CHORUS_preprocessed.txt`
- Source manifest: `data/preprocessed/source_manifest.yaml`
- Full: `data/d4d_concatenated/claudecode_agent/2026-08-07_claude-opus-5-claudecode-generic-v3_rep1/CHORUS_d4d.yaml`
- Core: `data/d4d_concatenated/claudecode_agent_core/2026-08-07_claude-opus-5-claudecode-generic-v3_rep1/CHORUS_d4d_core.yaml`

## Referent

`Dataset` admits one referent. The chosen referent is **the CHoRUS dataset** — the
multicenter, multimodal critical care dataset released under controlled access by the
CHoRUS data generation project — and not the funded project, the CHoRUS Network, or the
AIM-AHEAD Bridge2AI for Clinical Care Training Program. The bundle names the referent both
"CHoRUS Dataset" and "Bridge2AI for Clinical Care Dataset"; both appear in the record
(`name` and `title`) rather than one being silently preferred.

The referent choice drove three exclusions that would otherwise have looked like available
evidence:

- The AIM-AHEAD training programme's trainee terms (the $8,000 stipend, travel allowances,
  U.S. citizenship and W-9 requirements, application deadlines, mentorship matching) describe
  the programme, not the dataset, and are excluded. The programme's *dataset access*
  requirements — registration form, signed licensing agreement, `.edu` email — are recorded
  in `license_and_use_terms`, scoped to the programme context.
- The trainee stipend is **not** recorded as `participant_compensation`; that slot concerns
  compensation of human data subjects, and the bundle says nothing about it.
- The MIT licence statement applies to the CHoRUS GitHub project and its software. It is
  recorded on the software objects, not as the dataset's `license`, which the bundle never
  states.

The same referent is held in both records; core is a strict projection of full.

## Phase 3 — source and provenance audit

### Provenance

**Reasoning effort was observed, not asserted.** The value `high` in both file headers was
read from the `CLAUDE_EFFORT` environment variable at run time (`echo "$CLAUDE_EFFORT"` →
`high`), not copied from the prompt template and not inferred. This distinguishes it from
`Temperature: 0.0`, which the Claude Code runtime does not expose to the agent or to the
recorder: the temperature line restates the prompt template, and `provenance.py` correctly
flags it under `unverified` as asserted-rather-than-observed. The effort value carries no
such caveat because it is an actual runtime setting read from the environment. The
distinction matters beyond bookkeeping — `Reasoning effort` is one of the `PROCEDURE_FIELDS`
in `runs.py` that decide whether two runs are replicates of the same procedure, and
`runs.py` discards placeholder wordings (`default`, `n/a`, `not applicable`, …) as carrying
no procedural information. `high` is a real, discriminating value.

Factual inputs read during this run were the declared bundle, the CHORUS block of
`data/preprocessed/source_manifest.yaml`, and the two LinkML schemas (via `SchemaView`
introspection rather than by reading a record). No prior full or core D4D, from any arm,
label, or date, was read, opened, grepped, or consulted; nothing under
`data/d4d_concatenated/` other than this run's own two outputs was accessed, and no
`*_crate_d4d.yaml` or `*_crate_mapped_d4d.yaml` was accessed. No evaluation or
reconciliation report from an earlier run was used. Structure was derived exclusively from
class `Dataset` and class `CoreDataset` by runtime introspection; no `d4d:docExample` value
was copied.

### Source disagreements, represented rather than resolved

| Fact | Sources | Treatment |
|---|---|---|
| Admissions | NIH RePORTER: >100,000 critically ill patients (target). chorus4ai.org: 50,000 "Current Released Dataset" / 100,000 "Anticipated Final Dataset". Webinar: >45K unique admissions "as of August 2025". | `instances.counts = 50000` (the released-dataset figure, matching the referent). All three figures and their scopes recorded in the instance `description`; the ordering caveat in `source_caveats`, because chorus4ai.org carries no capture date and so cannot be ordered against the August 2025 snapshot with certainty. |
| Imaging volume | chorus4ai.org: 7,642 admissions with Radiology Data. Webinar: currently 1,000 images available, de-id in process. | No `counts` recorded — the two figures measure different things (admissions vs images) and neither counts imaging instances. Both recorded in `description`, with the reason in `source_caveats`. |
| Hospitals / centres | NIH RePORTER and webinar: 14 hospitals. GitHub overview: 20 academic centers, of which 14 contribute as Data Acquisition centers. chorus4ai.org: 14 data contributing hospitals, 60+ members across 20 institutions. | Not a conflict — 20 collaborating centres, 14 acquiring. Both figures recorded with their distinct roles. Recorded as a coverage limitation. |

### Unsupported / stale / mis-scoped assertions found and handled

- **No persistent dataset identifier exists in the bundle.** No DOI, accession, or
  repository record. The required `id` carries `https://chorus4ai.org/`, with the
  substitution stated in top-level `source_caveats`. This is the one slot where the record
  asserts an identifier the bundle does not supply as such.
- **The webinar's data-type table survives PDF text extraction with its columns
  interleaved.** Data type, data standard, access control, and published metadata schema can
  each be matched to rows by content, so those are recorded (9 `raw_data_sources`, 5
  `distribution_formats`). The per-row "Metadata" column (values Yes / Planned) *cannot* be
  reliably assigned to rows and is therefore **not** recorded at row level; only the
  existence of planned-but-unavailable metadata is recorded, as a limitation. The
  extraction defect is stated in top-level `source_caveats`.
- **NIH RePORTER "Preferred terms" are project-level index terms**, not dataset keywords.
  They are recorded in `keywords` with that scope stated in `source_caveats`, rather than
  silently attributed to the dataset or silently dropped.
- **`cmccrary@mgh.havard.edu`** is transcribed verbatim from chorus4ai.org including its
  apparent misspelling of the institutional domain; flagged in `source_caveats` on the
  maintainer and at top level. The bundle offers no corrected form, so none was invented.
- **The chorus4ai.org banner** ("This repoitory is under review for potential modification
  in compliance with Administration directives") is recorded verbatim in
  `regulatory_restrictions`, with a caveat that the bundle does not make clear whether
  "repository" means the data repository or the website, and its own spelling preserved.
- **The NIH award period (2022-09-01 – 2026-11-30) is not a collection timeframe.** It is
  recorded on the grant; `collection_timeframes` records no start or end date, with the
  reason stated. This is the mis-scoping the audit was most likely to have let through.

### Shape and slot-filling audit — corrections applied

The audit found one systematic slot-filling violation and one enum misuse. Both were fixed
in the **full** record first, which was then re-validated, and core was regenerated from the
corrected full.

1. **Evidence commentary in the wrong slot (14 sites).** Statements of the form "the
   declared bundle does not state X" were sitting inside `description` and `*_details`
   slots, where they read as dataset facts rather than as commentary on the evidence. All
   were moved to `source_caveats` on the same object: `creators[creator_chorus_network]`,
   `subpopulations`, `splits`, `sampling_strategies`, `collection_timeframes` (merged with
   its existing caveat), `data_protection_impacts`, `at_risk_populations`,
   `cleaning_strategies`, `labeling_strategies`, `raw_sources`, `machine_annotation_tools`,
   `updates`, `version_access`, `external_resources`. In `is_deidentified` the whole of
   `deidentification_details` was commentary, so the slot was removed and its content moved
   to `source_caveats`.
2. **`Maintainer.role` misapplied to individuals.** `academic_institution` had been set on
   three individual contacts (Ciera McCrary, the Emory access contact, Jared Houghtaling).
   `CreatorOrMaintainerEnum` has no value denoting an individual, and asserting an
   organisation type for a person is an inference the bundle does not support. `role` was
   removed from all three; it is retained only on the consortium entry, where it is correct.

No other shape defect was found: no prose stands where the schema requires a list, no enum
value outside its permissible set is used, and no commentary is embedded inside a name,
identifier, or affiliation value. Repeated identifiers, dates, counts, and organisation
names were checked for internal consistency within each file and agree.

### Phase 2 discoveries back-ported to full

None. Phase 2 re-read the declared bundle against the `CoreDataset` inventory and found no
fact the full extraction had missed and no core field the full record left empty that the
bundle could fill. Core therefore introduced no value absent from full, and no back-port was
required. Every Phase 3 correction listed above was applied to full first and propagated to
core by regeneration.

### Slots deliberately left empty

`known_biases`, `anomalies`, `content_warnings`, `informed_consent`,
`collection_consents`, `collection_notifications`, `consent_revocations`,
`participant_compensation`, `missing_data_documentation`, `imputation_protocols`,
`annotation_analyses`, `errata`, `retention_limit`, `ip_restrictions`, `use_repository`,
`discouraged_uses`, `prohibited_uses`, `distribution_dates`, `variables`, `subsets`,
`file_collections`, `parent_datasets`, `related_datasets`, `citation`, `is_tabular`,
`total_file_count`, `total_size_bytes`, `doi`, `version`, `license`, `publisher`,
`conforms_to`. Each is absent because the bundle does not support it, not because it was
overlooked. Two are worth naming:

- `known_biases` — the bundle repeatedly states an *intent* to manage privacy and bias and
  to assemble a balanced, diverse cohort. It never documents a bias present in the data.
  Recording a `DatasetBias` from a mitigation statement would have invented the bias.
- `is_tabular` — the dataset is deliberately multimodal (OMOP tables, DICOM imaging, WFDB
  and EDF+ waveforms, tokenized text). A single boolean would misrepresent it either way.

## Phase 4 — strict full/core reconciliation

Shared slots were derived at runtime with LinkML `SchemaView` from class `Dataset` and class
`CoreDataset`; no hand-written field list was used. The schemas share **79** slots, of which
**78** are schema-identical and **1** (`resources`, `Dataset` in full vs `CoreDataset` in
core) is a projection.

### Result

```
PASS: 78 schema-identical slots; projected slots=['resources']
```

- Every schema-identical slot is present in both records or absent from both, and every
  present one is deeply identical in parsed YAML — including nested mappings, list order,
  and every narrative field. Core condenses, paraphrases, reorders, and omits nothing.
- `resources` (the projection) is absent from both records. Coverage is trivially equal;
  there is no resource to match by `id`.

### Full-only slots

Five populated slots exist in `Dataset` and have no `CoreDataset` counterpart, so they are
correctly absent from core rather than dropped by choice:

`relationships`, `splits`, `direct_collection`, `participant_privacy`,
`third_party_sharing`.

Each was checked for a conflicting semantic counterpart in core, and none was found. Their
content overlaps core slots that are themselves schema-identical and deeply identical, so
core is weaker but never inconsistent: `splits` (holdout test set) is echoed in `purposes`,
`tasks`, and `other_tasks`; `participant_privacy` in `is_deidentified` and
`at_risk_populations`; `direct_collection` in `acquisition_methods`; `third_party_sharing`
in `license_and_use_terms` and `intended_uses`; `relationships` in `instances`.

Core-only slots `distributions` and `dialect` are both unpopulated.

### Related, non-identical representations — semantic review

- **`file_collections` (full) → `distributions` (core):** both absent. The bundle carries no
  file-level inventory — no paths, file counts, byte totals, checksums, or download URLs.
  The only volumetric figures are 1.6 billion OMOP rows and 23 Tb of waveform data, neither
  of which is a file-level fact, and both are recorded on `instances` in both records
  identically. Nothing to map; no conflict.
- **`total_file_count` / `total_size_bytes` vs distribution-level values:** all absent. The
  23 Tb figure is waveform-only and was deliberately not promoted to a dataset total, and
  "Tb" was not converted to bytes, since the bundle does not disambiguate Tb from TB.
- **`dialect`, formats, `is_tabular`:** `dialect` and `is_tabular` are absent from both.
  Format information lives only in `distribution_formats` and `raw_data_sources`, both
  schema-identical and deeply identical. The five standards (OMOP, OHNLP, DICOM, WFDB, EDF+
  and Persyst) agree between the two slots and across the two files.
- **Top-level identity / version / access facts:** `id`, `name`, `title`, `page`,
  `keywords`, `description`, and `source_caveats` are identical across the pair.
  `version_access`, `license_and_use_terms`, `regulatory_restrictions`, `maintainers`, and
  `updates` are schema-identical and deeply identical, and their contents agree with the
  top-level facts — the access story (controlled access on every data type, signed licensing
  agreement, `.edu` email) is stated consistently in `license_and_use_terms`,
  `regulatory_restrictions`, `confidential_elements`, and `raw_data_sources` without
  contradiction.
- **Historical vs current release:** the Current Released Dataset (50,000 admissions), the
  Anticipated Final Dataset (100,000 admissions), and the August 2025 snapshot (>45,000
  admissions) are recorded with their scopes explicit in both records. They are three
  differently-scoped statements, not a contradiction, and are treated as such.

**Zero unresolved contradictions within or between the two records.**

## Files changed

| File | Change |
|---|---|
| `.../claudecode_agent/2026-08-07_.../CHORUS_d4d.yaml` | Phase 1 written; Phase 3 corrections applied (14 `source_caveats` relocations, `is_deidentified.deidentification_details` removed, `Maintainer.role` removed from three individuals); `# Reasoning effort: high` added to the header |
| `.../claudecode_agent_core/2026-08-07_.../CHORUS_d4d_core.yaml` | Phase 2 written; regenerated from the Phase 3-corrected full; `# Phase 4 reconciliation: completed` appended by `--sync-core`; `# Reasoning effort: high` added to the header |
| `.../claudecode_agent_core/2026-08-07_.../CHORUS_reconciliation.md` | This report |

## Commands

```bash
# Phase 1 / Phase 3 — full
poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_all.yaml -C Dataset \
  data/d4d_concatenated/claudecode_agent/2026-08-07_claude-opus-5-claudecode-generic-v3_rep1/CHORUS_d4d.yaml
poetry run linkml-term-validator validate-data \
  data/d4d_concatenated/claudecode_agent/2026-08-07_claude-opus-5-claudecode-generic-v3_rep1/CHORUS_d4d.yaml \
  --schema src/data_sheets_schema/schema/data_sheets_schema_all.yaml --target-class Dataset

# Phase 2 / Phase 3 — core
poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml -C CoreDataset \
  data/d4d_concatenated/claudecode_agent_core/2026-08-07_claude-opus-5-claudecode-generic-v3_rep1/CHORUS_d4d_core.yaml
poetry run linkml-term-validator validate-data \
  data/d4d_concatenated/claudecode_agent_core/2026-08-07_claude-opus-5-claudecode-generic-v3_rep1/CHORUS_d4d_core.yaml \
  --schema src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml --target-class CoreDataset

# Phase 4 — pair consistency
poetry run python -m data_sheets_schema.d4d_pair_consistency \
  --full data/d4d_concatenated/claudecode_agent/2026-08-07_claude-opus-5-claudecode-generic-v3_rep1/CHORUS_d4d.yaml \
  --core data/d4d_concatenated/claudecode_agent_core/2026-08-07_claude-opus-5-claudecode-generic-v3_rep1/CHORUS_d4d_core.yaml \
  --sync-core
poetry run python -m data_sheets_schema.d4d_pair_consistency \
  --full data/d4d_concatenated/claudecode_agent/2026-08-07_claude-opus-5-claudecode-generic-v3_rep1/CHORUS_d4d.yaml \
  --core data/d4d_concatenated/claudecode_agent_core/2026-08-07_claude-opus-5-claudecode-generic-v3_rep1/CHORUS_d4d_core.yaml

# Provenance
poetry run d4d provenance record --project CHORUS --method claudecode_agent \
  --label 2026-08-07_claude-opus-5-claudecode-generic-v3_rep1 \
  --input-bundle data/preprocessed/concatenated/CHORUS_preprocessed.txt
poetry run d4d runs check --strict
```

## Final results

| Check | Result |
|---|---|
| Full — `linkml-validate` (`Dataset`) | No issues found |
| Full — `linkml-term-validator` | Validation passed |
| Core — `linkml-validate` (`CoreDataset`) | No issues found |
| Core — `linkml-term-validator` | Validation passed |
| Pair consistency (final, no `--sync-core`) | PASS — 78 schema-identical slots, projected `['resources']` |
| Unresolved contradictions | None |

Informational metadata, not a quality gate: full 50 populated top-level slots / 1103 lines;
core 45 populated top-level slots / 861 lines.

## Provenance re-record

Provenance was written once, then the `# Reasoning effort: high` header line was added to
both YAML files, which changed their bytes and made the first record stale. The record was
therefore **re-written after** the header edit, and `d4d runs validate` re-run after that,
so the hashes in `CHORUS_provenance.yaml` describe the bytes that actually shipped. No YAML
or report edit was made after the final `d4d provenance record`.
