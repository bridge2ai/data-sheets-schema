# AI_READI full/core reconciliation — 2026-07-28_claude-opus-5-generic_rep2

- **Arm:** HEALTHSHEET-ONLY (single structured upstream source)
- **Prompt:** `src/download/prompts/d4d_generic_arm_prompt.md` (identical text for all projects)
- **Runtime / model:** Claude Code, Anthropic, `claude-opus-5[1m]`, temperature 0.0
- **Declared input bundle:** `data/preprocessed/concatenated/AI_READI_healthsheet_only.txt`
- **Source manifest:** not used; this arm declares its single source bundle explicitly
- **Full:** `data/d4d_concatenated/claudecode_agent_healthsheet/2026-07-28_claude-opus-5-generic_rep2/AI_READI_d4d.yaml`
- **Core:** `data/d4d_concatenated/claudecode_agent_healthsheet_core/2026-07-28_claude-opus-5-generic_rep2/AI_READI_d4d_core.yaml`

## Dataset referent

`Dataset` admits one referent. The declared bundle describes exactly one: the
**Flagship Dataset of Type 2 Diabetes from the AI-READI Project, version 3**
(DOI `10.60775/fairhub.3`), covering data collected 2023-07-19 to 2025-05-01 from
2280 participants. Versions 1 and 2 are represented as typed
`related_datasets` (`is_new_version_of`) in the full record rather than as
alternative referents, and the public and controlled-access tiers are represented
as `subsets` of the single referent. This choice is held consistently across both
records.

## Phase 3 — source and provenance audit

### Provenance boundary

- Factual inputs read: the declared bundle only.
- Structural inputs read: `data_sheets_schema_all.yaml` (class `Dataset`) and
  `data_sheets_schema_core_all.yaml` (class `CoreDataset`), both traversed with
  LinkML `SchemaView` rather than by example.
- No prior D4D record, from any arm, label, or date, was read, searched, or
  consulted. Nothing under `data/d4d_concatenated/` other than this run's own two
  output paths was opened, and no `*_crate_d4d.yaml` or `*_crate_mapped_d4d.yaml`
  was opened. No web content was fetched. No evaluation or reconciliation report
  from an earlier run was consulted.
- Phase 2 read the exact same-run Phase 1 full record, which carries this run's
  label in its path.

### Findings and corrections

Six findings; all corrected in the full record first, then re-projected into core.

1. **Silently reconciled source inconsistency (corrected).** The bundle's
   composition section states the dataset "contains data from all participants who
   have been enrolled during the **first year** of data collection for AI-READI",
   while its versioning, composition, and collection sections state that version 3
   covers 2023-07-19 to 2025-05-01, i.e. through the end of the **second** year.
   The first draft paraphrased this away as "the data collection period".
   `sampling_strategies` now carries the source sentence as written and states
   explicitly that the two statements disagree.

2. **URL scheme altered (corrected).** `publisher` and
   `distribution_formats.access_urls` had been normalised to `https://fairhub.io/`.
   The source states `http://fairhub.io/`. Both reverted to the source form.

3. **Unsupported enum classification (corrected).** `maintainers.role` had been set
   to `academic_institution`. The bundle names the maintainer as "the AI-READI team"
   and never classifies it. The slot was removed; the maintainer text is unchanged.

4. **Unsupported enum classification (corrected).**
   `license_and_use_terms.data_use_permission` had been set to
   `general_research_use`. The bundle states only that the license "enable[s] reuse
   ... for commercial or research purpose" with "strong requirements around data
   usage, security, and secondary sharing", and does not reproduce the license text.
   The enum was removed and replaced with an explicit statement that the specific
   permitted and restricted uses are not enumerated in the source.

5. **Over-strong identifiability claim (corrected).**
   `is_deidentified.identifiable_elements_present` had been set to `false`. The
   bundle leaves both de-identification questions unanswered and elsewhere states
   "there is a theoretical risk of future re-identification". The boolean was
   removed; the details now record the no-PII statement, the internal PII review,
   the theoretical re-identification risk, and the fact that the de-identification
   questions were unanswered.

6. **Omitted source fact (corrected).** "In which countries was the data collected?
   A: USA" was not represented in any slot shared with core. It was added to
   `collection_mechanisms` ("General collection procedures").

### Source conflicts represented rather than resolved

- **Grant number.** The bundle renders the NIH award as `OT2ODO32644` (motivation
  section) and `OT2OD032644` (collection section). `funders.grants[0].grant_number`
  carries `OT2OD032644` and the grant description records both renderings verbatim
  and states that they were not silently reconciled.
- **Enrollment period covered by version 3.** See finding 1; both statements are
  preserved in `sampling_strategies`.

### Source coverage gaps preserved

The bundle marks 3 of its 84 questions unanswered. Two concern de-identification
(pre-processing for de-identification; measures against re-identification) and one
concerns errata. The de-identification gaps are stated explicitly in
`is_deidentified` and `preprocessing_strategies`. No `errata` slot was emitted,
because an unanswered question is absent evidence and omission is the correct
representation.

### Internal consistency checks

- Participant counts agree everywhere they appear: v1 = 204, v2 = 1067 (= 204 + 863
  additional), v3 = 2280 (`instances.counts`, `version_access.versions_available`,
  `related_datasets`, `description`, `splits`).
- Version identity agrees across `version`, `doi`, `status`, `version_access`,
  `distribution_dates`, and `description` (version 3, DOI `10.60775/fairhub.3`,
  distributed November 2025).
- Collection window agrees across `collection_timeframes.start_date`/`end_date`
  (2023-07-19 / 2025-05-01), `status`, and `known_limitations`.
- License URL (`https://doi.org/10.5281/zenodo.17555036`) is identical in `license`,
  `discouraged_uses`, `prohibited_uses`, `ip_restrictions`,
  `regulatory_restrictions`, and `license_and_use_terms`.
- The three sites (UAB, UCSD, UW) are named consistently in `creators.affiliations`,
  `known_biases`, `sampling_strategies`, and `raw_data_sources`; UW is the IRB site
  in both `ethical_reviews` and `human_subject_research`.

### Structural notes

- `funders.grantor` is a non-inlined reference of range `Grantor` (an identified
  class), so it carries the CURIE `d4d:organization-nih`; NIH is named in the
  surrounding `FundingMechanism` description and grant description. Likewise
  `ethical_reviews.reviewing_organization` references
  `d4d:organization-university-of-washington`, which is defined inline under
  `creators.affiliations`.
- `Instance.missing_information` and `Creator.affiliations` are inlined per their
  schema-declared ranges; no nested shape was assumed from any example.
- No `d4d:docExample` annotation value was copied into either record.

## Phase 4 — strict full/core reconciliation

The shared-slot inventory was derived at run time with LinkML `SchemaView` from
class `Dataset` (full schema) and class `CoreDataset` (core schema); no hand-written
field list was used. All 50 nested classes used by the two records were compared
across the two schemas and have **identical induced slot inventories**, so no
nested shape differs between layers.

Core was produced as the schema-derived projection of the Phase 3-audited full
record: every key present in the full record whose slot name is in the induced
`CoreDataset` inventory was carried over with its parsed value unchanged. This makes
deep identity structural rather than a post-hoc repair, so `--sync-core` was not
needed and was not run.

- **Schema-identical shared slots checked:** 76 — all present-in-both or
  absent-in-both, with deeply identical parsed YAML values including nested mapping
  values and list order. Narrative fields were carried verbatim; nothing was
  condensed, paraphrased, reordered, or omitted in core.
- **Projected slots:** `resources` (range `Dataset` in full, `CoreDataset` in core) —
  absent from both records, so coverage is trivially equal.
- **Full-only slots dropped from core** (12, none of which `CoreDataset` declares):
  `citation`, `related_datasets`, `subsets`, `relationships`, `splits`,
  `direct_collection`, `collection_notifications`, `collection_consents`,
  `consent_revocations`, `participant_privacy`, `participant_compensation`,
  `third_party_sharing`.
- **Core-only slots not emitted:** `distributions`, `dialect`. The bundle is a
  healthsheet and contains no file-level facts — no paths, formats, byte counts,
  checksums, encodings, or dialect — so `CoreDistribution` and `FormatDialect` have
  no supported content. `file_collections`, `total_file_count`, and
  `total_size_bytes` are absent from the full record for the same reason, so there is
  no `file_collections` → `distributions` mapping to review and no scope comparison
  to make. `is_tabular` is absent from both: the bundle states the dataset mixes
  tabular, imaging, and waveform data, which supports neither boolean value.
- **Related-content review.** Because both layers' file-level and dialect content is
  empty, the only related (non-identical) content is the full-only set above. Each
  item was checked against its core-side counterpart for contradiction:
  `citation` ↔ `intended_uses.usage_notes` (both state citation to
  `https://docs.aireadi.org` is required); `subsets` (public/controlled tiers) ↔
  `sensitive_elements` and `license_and_use_terms` (same tiering, same items under
  controlled access); `splits` ↔ `subpopulations.distribution` (same 70/15/15
  balanced split rationale); `consent_revocations`/`collection_consents` ↔
  `informed_consent` (same consent and withdrawal statements);
  `participant_privacy` ↔ `is_deidentified` (same no-PII, internal-review, and
  theoretical-re-identification statements); `third_party_sharing` ↔
  `distribution_formats` (same public distribution via FAIRhub);
  `related_datasets` ↔ `version_access.versions_available` (same v1/v2/v3 counts and
  healthsheet URLs). No contradictions found.
- **Unresolved contradictions:** none.

## Commands run

```bash
poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_all.yaml \
  -C Dataset data/d4d_concatenated/claudecode_agent_healthsheet/2026-07-28_claude-opus-5-generic_rep2/AI_READI_d4d.yaml
poetry run linkml-term-validator validate-data \
  data/d4d_concatenated/claudecode_agent_healthsheet/2026-07-28_claude-opus-5-generic_rep2/AI_READI_d4d.yaml \
  --schema src/data_sheets_schema/schema/data_sheets_schema_all.yaml --target-class Dataset
poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml \
  -C CoreDataset data/d4d_concatenated/claudecode_agent_healthsheet_core/2026-07-28_claude-opus-5-generic_rep2/AI_READI_d4d_core.yaml
poetry run linkml-term-validator validate-data \
  data/d4d_concatenated/claudecode_agent_healthsheet_core/2026-07-28_claude-opus-5-generic_rep2/AI_READI_d4d_core.yaml \
  --schema src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml --target-class CoreDataset
poetry run python -m data_sheets_schema.d4d_pair_consistency \
  --full data/d4d_concatenated/claudecode_agent_healthsheet/2026-07-28_claude-opus-5-generic_rep2/AI_READI_d4d.yaml \
  --core data/d4d_concatenated/claudecode_agent_healthsheet_core/2026-07-28_claude-opus-5-generic_rep2/AI_READI_d4d_core.yaml
poetry run d4d provenance record --project AI_READI --method claudecode_agent_healthsheet \
  --label 2026-07-28_claude-opus-5-generic_rep2 \
  --input-bundle data/preprocessed/concatenated/AI_READI_healthsheet_only.txt
```

Both validation pairs were re-run after the Phase 3 corrections and again after the
core header gained `Phase 4 reconciliation: completed`.

## Files changed

- `data/d4d_concatenated/claudecode_agent_healthsheet/2026-07-28_claude-opus-5-generic_rep2/AI_READI_d4d.yaml` (created, then 6 Phase 3 corrections)
- `data/d4d_concatenated/claudecode_agent_healthsheet_core/2026-07-28_claude-opus-5-generic_rep2/AI_READI_d4d_core.yaml` (created, re-projected after Phase 3)
- `data/d4d_concatenated/claudecode_agent_healthsheet_core/2026-07-28_claude-opus-5-generic_rep2/AI_READI_reconciliation.md` (this report)
- `data/d4d_concatenated/claudecode_agent_healthsheet_core/2026-07-28_claude-opus-5-generic_rep2/AI_READI_provenance.yaml` (live provenance record)

## Final results

| Check | Result |
|---|---|
| Full — `linkml-validate` (`Dataset`) | pass |
| Full — `linkml-term-validator` | pass |
| Core — `linkml-validate` (`CoreDataset`) | pass |
| Core — `linkml-term-validator` | pass |
| `d4d_pair_consistency` (no `--sync-core`) | PASS, 76 schema-identical slots |
| Provenance record `record_mode` | `live` |
| Full top-level slots populated | 70 |
| Core top-level slots populated | 58 |
| Unresolved discrepancies | none |
