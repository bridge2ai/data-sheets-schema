# AI_READI full/core reconciliation — 2026-07-28_claude-opus-5-generic_rep3

- **Arm:** HEALTHSHEET-ONLY (single structured upstream source)
- **Prompt:** `src/download/prompts/d4d_generic_arm_prompt.md` (identical text for all projects)
- **Declared input bundle:** `data/preprocessed/concatenated/AI_READI_healthsheet_only.txt`
- **Source manifest:** not used; this arm declares its single source bundle explicitly
- **Runtime / provider / model:** Claude Code / Anthropic / `claude-opus-5[1m]`, temperature 0.0
- **Mode:** four-phase project agent, phases executed sequentially

## Files

| Role | Path |
|---|---|
| Full | `data/d4d_concatenated/claudecode_agent_healthsheet/2026-07-28_claude-opus-5-generic_rep3/AI_READI_d4d.yaml` |
| Core | `data/d4d_concatenated/claudecode_agent_healthsheet_core/2026-07-28_claude-opus-5-generic_rep3/AI_READI_d4d_core.yaml` |
| Provenance | `data/d4d_concatenated/claudecode_agent_healthsheet_core/2026-07-28_claude-opus-5-generic_rep3/AI_READI_provenance.yaml` |

## Phase 3 — Source and provenance audit

### Provenance boundary

No prior generated D4D record was read, opened, grepped, or consulted in any phase.
Nothing under `data/d4d_concatenated/` was read except the same-run full record
(Phase 2 input) and the same-run pair (Phases 3–4). Nothing under
`data/ro-crate_packages/` was read. The only factual input was the declared
bundle; structure came exclusively from the two LinkML schemas, resolved at run
time with `SchemaView` (induced slots of `Dataset` and of `CoreDataset`,
including inherited slots, ranges, cardinality, inlining, and enum
permissible values).

Directory listings under `data/d4d_concatenated/` were inspected once, for names
only, to confirm the run label was unused. No file contents were read.

### Chosen referent

`Dataset` admits one referent. The referent chosen is **the Flagship Dataset of
Type 2 Diabetes from the AI-READI Project, version 3** (DOI `10.60775/fairhub.3`,
2280 participants, distributed November 2025) — the version the bundle's own
Versioning section states this datasheet is for. Versions 1 and 2 are represented
as `related_datasets` (`is_new_version_of`) and in `version_access`, not as
alternative referents, and the same referent is held in both records.

### Source disagreements represented rather than resolved

The bundle is internally inconsistent in two places. Both are represented as the
evidence states them rather than silently reconciled:

1. **Grant number.** The Motivation section gives `OT2ODO32644`; the Collection
   section gives `OT2OD032644`. `funders[0].grants[0].grant_number` carries the
   Motivation form, and the grant `description` records both forms verbatim and
   states that neither was selected over the other. The Collection form also
   appears verbatim in `data_collectors[0].collector_details`, in the sentence
   where the bundle uses it.
2. **Enrollment window covered by this version.** The Composition section says
   the dataset "contains data from all participants who have been enrolled during
   the first year of data collection"; the Versioning and Collection sections say
   this version covers July 19, 2023 to May 1, 2025, i.e. through the end of the
   second year. `sampling_strategies[0].strategies` reproduces the Composition
   claim and appends a parenthetical stating the other figure, without choosing.
   `collection_timeframes[0]` carries the explicit dated window
   (2023-07-19 → 2025-05-01) that the bundle states for this version.

### Unanswered source questions

The bundle marks three questions unanswered. None was filled by inference:

- de-identification measures against re-identification — recorded as unanswered
  in `is_deidentified.deidentification_details`; `method` and
  `identifiers_removed` left unpopulated.
- preprocessing for de-identification — same treatment.
- erratum — the `errata` slot is omitted entirely from both records.

### Omissions taken deliberately

Slots left unpopulated because the bundle does not support them, rather than
filled with plausible values: `file_collections`, `total_file_count`,
`total_size_bytes`, `compression`, `keywords`, `language`, `issued`,
`created_on`, `last_updated_on`, `status`, `citation`, `conforms_to*`,
`variables`, `parent_datasets`, `imputation_protocols`, `annotation_analyses`,
`machine_annotation_tools`, `other_tasks`, `prohibited_uses`,
`at_risk_populations`, and the ontology-term slots `Instance.data_topic` /
`Instance.data_substrate`. Two enum-valued slots were left empty because the
bundle's wording does not map cleanly onto any permissible value:
`LicenseAndUseTerms.data_use_permission` (the license permits both commercial and
research reuse under conditions) and `Maintainer.role`.

### Internal consistency checks

Repeated facts were checked for agreement within each file and across the pair:
participant counts (204 / 1067 / 2280) agree between `instances[0].counts`,
`subsets`, `version_access.versions_available`, and `related_datasets`; the
dataset DOI agrees between `id`, `doi`, `download_url`, `distribution_formats`,
and `version_access.latest_version_doi`; the license DOI agrees between
`license`, `license_and_use_terms`, `ip_restrictions`, `regulatory_restrictions`,
and `discouraged_uses`; the release dates agree between `distribution_dates` and
`version_access`; the IRB date and letter URL agree between `ethical_reviews` and
`human_subject_research`; the consent form URL agrees between
`collection_consents` and `informed_consent`. Historical values (versions 1 and
2) are stated with explicit version scope everywhere they appear and are never
presented as current.

### Corrections made in Phase 3

None. The Phase 2 pass surfaced no source-supported fact that the full record had
missed or stated differently, so nothing was back-ported and no value in either
file was changed after its initial write.

### Validation re-run in Phase 3

Both files passed schema and term validation (commands and results below).

## Phase 4 — Strict full/core reconciliation

### Shared-slot derivation

Shared slots were derived at run time from `Dataset` and `CoreDataset` via
`SchemaView`, not from a hand-written list. The core record was produced by
projecting the Phase 3-canonical full record onto the `CoreDataset` induced-slot
inventory, so every schema-identical slot is byte-for-byte the same content, in
the same order, including all narrative text. No shared value was condensed,
paraphrased, reordered, or omitted in core.

**Result:** `PASS: 76 schema-identical slots; projected slots=['resources']`

`--sync-core` was not needed and was not run: the pair was already consistent on
its first independent check.

### Full-only slots (present in `Dataset`, absent from `CoreDataset`)

`subsets`, `relationships`, `splits`, `direct_collection`,
`collection_notifications`, `collection_consents`, `consent_revocations`,
`participant_privacy`, `participant_compensation`, `third_party_sharing`,
`related_datasets`.

These are schema-driven omissions, not content loss decisions. Their substance is
still reachable in core where the core schema has a home for it: consent and
withdrawal in `informed_consent`, participant compensation in
`data_collectors[0].collector_details`, re-identification risk in
`is_deidentified`, split design in `known_biases[0].mitigation_strategy` and
`instances[0]`, public/controlled-access division in `sensitive_elements` and
`license_and_use_terms`.

### Core-only slots

`distributions` (`CoreDistribution`) and `dialect` (`FormatDialect`) are omitted.
The bundle states no file-level property — no path, format, byte count,
checksum, encoding, or media type — and the full record correspondingly has no
`file_collections`. Emitting an empty distribution would assert coverage the
source does not support, and would break the full-`file_collections` →
core-`distributions` mapping that Phase 4 requires. Both sides are therefore
absent, which is the consistent state.

### Projected slots

`resources` is the only projected slot (range `Dataset` in full, `CoreDataset` in
core). It is absent from both records, so coverage is trivially equal and no
per-`id` matching was required.

### Related-content review

- `total_file_count` / `total_size_bytes` vs. distribution-level values: all
  absent on both sides; nothing to compare, no conflict.
- `dialect`, formats, `is_tabular`: `is_tabular: false` in both records, matching
  the bundle's statement that the data encompass tabular, imaging, and
  physiological signal/waveform data. `dialect` and format enums are unpopulated
  on both sides, so there is nothing for `is_tabular` to contradict.
- Top-level identity/version/access facts vs. `version_access`,
  `distribution_dates`, and repeated statements: checked and in agreement (see
  Phase 3 internal consistency checks). `version: "3"` is consistent with
  `latest_version_doi`, with the November 2025 release date, and with the 2280
  instance count.
- Historical vs. current release: versions 1 and 2 appear only with explicit
  version labels and their own participant counts and release dates. Their
  differing values are historical scope, not contradictions of the version 3
  values.

**Unresolved contradictions within or between the two records: none.**

### One structural note

`Grantor.id` is `required` in `data_sheets_schema_all.yaml` but not in
`data_sheets_schema_core_all.yaml`, so `funders[0].grantor` is a non-inlined
reference in the full schema and would admit an inlined object in core. The
single string form `d4d:national-institutes-of-health` validates against both
schemas and was used unchanged in both records, which keeps the slot deeply
identical across the pair. The grantor's human-readable identity is carried in
`funders[0].description`, which names the National Institutes of Health and the
Bridge2AI Program.

## Commands run

```bash
poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_all.yaml \
  -C Dataset data/d4d_concatenated/claudecode_agent_healthsheet/2026-07-28_claude-opus-5-generic_rep3/AI_READI_d4d.yaml
# -> No issues found

poetry run linkml-term-validator validate-data \
  data/d4d_concatenated/claudecode_agent_healthsheet/2026-07-28_claude-opus-5-generic_rep3/AI_READI_d4d.yaml \
  --schema src/data_sheets_schema/schema/data_sheets_schema_all.yaml --target-class Dataset
# -> Validation passed

poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml \
  -C CoreDataset data/d4d_concatenated/claudecode_agent_healthsheet_core/2026-07-28_claude-opus-5-generic_rep3/AI_READI_d4d_core.yaml
# -> No issues found

poetry run linkml-term-validator validate-data \
  data/d4d_concatenated/claudecode_agent_healthsheet_core/2026-07-28_claude-opus-5-generic_rep3/AI_READI_d4d_core.yaml \
  --schema src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml --target-class CoreDataset
# -> Validation passed

poetry run python -m data_sheets_schema.d4d_pair_consistency \
  --full data/d4d_concatenated/claudecode_agent_healthsheet/2026-07-28_claude-opus-5-generic_rep3/AI_READI_d4d.yaml \
  --core data/d4d_concatenated/claudecode_agent_healthsheet_core/2026-07-28_claude-opus-5-generic_rep3/AI_READI_d4d_core.yaml
# -> PASS: 76 schema-identical slots; projected slots=['resources']

poetry run d4d provenance record --project AI_READI --method claudecode_agent_healthsheet \
  --label 2026-07-28_claude-opus-5-generic_rep3 \
  --input-bundle data/preprocessed/concatenated/AI_READI_healthsheet_only.txt
# -> AI_READI_provenance.yaml written, record_mode: live
```

## Files changed

Three files created; none modified after creation, because no phase found a
correction to make:

- `.../claudecode_agent_healthsheet/2026-07-28_claude-opus-5-generic_rep3/AI_READI_d4d.yaml`
- `.../claudecode_agent_healthsheet_core/2026-07-28_claude-opus-5-generic_rep3/AI_READI_d4d_core.yaml`
- `.../claudecode_agent_healthsheet_core/2026-07-28_claude-opus-5-generic_rep3/AI_READI_reconciliation.md`

Plus the live provenance record `AI_READI_provenance.yaml`.

## Final result

| Check | Result |
|---|---|
| Full schema validation | pass |
| Full term validation | pass |
| Core schema validation | pass |
| Core term validation | pass |
| Pair consistency (76 schema-identical slots) | pass |
| Provenance record `record_mode` | live |
| Unresolved contradictions | none |

Top-level populated slots: **full 67**, **core 56** (informational metadata, not a
quality gate).
