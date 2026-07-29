# AI_READI full/core reconciliation — 2026-07-28_claude-opus-5-generic_rep1

| Field | Value |
|---|---|
| Project | AI_READI |
| Arm | HEALTHSHEET-ONLY (single structured upstream source) |
| Method | claudecode_agent_healthsheet |
| Label | 2026-07-28_claude-opus-5-generic_rep1 |
| Prompt | `src/download/prompts/d4d_generic_arm_prompt.md` (identical text for all projects) |
| Agent runtime | Claude Code |
| Provider / model | Anthropic / claude-opus-5[1m] |
| Declared input bundle | `data/preprocessed/concatenated/AI_READI_healthsheet_only.txt` |
| Full record | `data/d4d_concatenated/claudecode_agent_healthsheet/2026-07-28_claude-opus-5-generic_rep1/AI_READI_d4d.yaml` |
| Core record | `data/d4d_concatenated/claudecode_agent_healthsheet_core/2026-07-28_claude-opus-5-generic_rep1/AI_READI_d4d_core.yaml` |

## Phase 3 — source and provenance audit

### Provenance boundary

Factual inputs read during this run were exactly:

- `data/preprocessed/concatenated/AI_READI_healthsheet_only.txt` (the declared bundle)
- `src/data_sheets_schema/schema/data_sheets_schema_all.yaml` (class `Dataset`, structure only)
- `src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml` (class `CoreDataset`, structure only)
- repository generation, provenance-guard, and validation instructions

No prior generated D4D record was read, opened, grepped, or consulted, from any arm, label, or
date. Nothing under `data/d4d_concatenated/` other than this run's own two output paths was read,
and no `*_crate_d4d.yaml` or `*_crate_mapped_d4d.yaml` under `data/ro-crate_packages/` was read. No
evaluation report, test fixture, or schema `d4d:docExample` supplied a factual value. Structure for
every emitted slot and nested object was derived at runtime from the two schemas via LinkML
`SchemaView` rather than from any example record.

The manifest was not consulted: this arm declares its single source bundle explicitly and does not
use `data/preprocessed/source_manifest.yaml`.

### Dataset referent

`Dataset` admits one referent. The declared bundle describes one dataset throughout: the AI-READI
flagship type 2 diabetes dataset, **version 3**, DOI `10.60775/fairhub.3`, comprising data collected
2023-07-19 to 2025-05-01 from 2280 participants. That is the referent chosen, and it is held
consistently across both records. Versions 1 and 2 are represented as related datasets and as
version-history entries in the full record rather than as alternative referents; the public and
controlled-access tiers are represented as `subsets` of the single referent rather than as separate
datasets.

### Internal source disagreement, recorded not resolved

The bundle renders the NIH award number two different ways:

- `OT2ODO32644` — in the answer to "Who funded the creation of the dataset?"
- `OT2OD032644` — in the answer to "Who was involved in the data collection process?"

Both statements describe the same NIH Bridge2AI award. The disagreement is recorded verbatim in
`funders[0].grants[0].description` in both records rather than silently resolved; `grant_number`
carries `OT2OD032644`. No external source was consulted to break the tie, since the bundle is the
only permitted factual input.

### Phase 2 discoveries back-ported to full

Phase 2 re-read the declared bundle against the Phase 1 record and found three source-supported facts
the Phase 1 extraction had missed. All three were corrected in the **full** record first, then
carried into core by regeneration of the projection:

1. **Country of collection** — "In which countries was the data collected? A: USA" was unrepresented.
   Added to `acquisition_methods[0].acquisition_details`.
2. **Participant communication and accessibility** — the INCLUSION section states English was used for
   communication with participants, that accessibility measurements were not specifically assessed,
   and that transportation assistance (rideshare services) was offered to participants who endorsed
   transport barriers. None of this was represented. Added as a new `collection_mechanisms` entry,
   "Participant communication and accessibility measures".
3. **Verbatim eligibility criteria** — the inclusion/exclusion criteria were referenced in prose but
   never listed. Added in full to `cleaning_strategies[1].cleaning_details`, which is where the bundle
   itself answers them (the preprocessing-exclusion question).

No fact discovered in Phase 2 was added to core without also being supported by the declared bundle
and present in full.

### Unsupported, stale, or mis-scoped assertions

None found. Spot checks performed against the bundle:

- **Counts** — 2280 (v3), 1067 (v2), 204 (v1) appear consistently in `instances[0].counts`,
  `instances[0].description`, `related_datasets`, and `version_access.versions_available`.
- **Dates** — collection window 2023-07-19 to 2025-05-01 appears as typed `start_date`/`end_date` and
  in prose in `collection_timeframes`, `known_limitations`, and the top-level `description`. Release
  dates May 2024 / November 2024 / November 2025 appear consistently in `distribution_dates` and
  `version_access`.
- **Identifiers** — DOI `10.60775/fairhub.3` used consistently as `id`, `doi`,
  `version_access.latest_version_doi`, and a `distribution_formats` access URL. License DOI
  `10.5281/zenodo.17555036` used consistently in `license`, `license_and_use_terms`,
  `ip_restrictions`, `regulatory_restrictions`, `discouraged_uses`, `prohibited_uses`, and
  `external_resources`.
- **Historical scope** — every value that belongs to an earlier version (204 and 1067 participants,
  Snellen visual acuity, prior release dates and prior healthsheet URLs) is explicitly labelled with
  the version it belongs to, so no historical value is presented as current.

### Input coverage gaps left unfilled (deliberate omissions)

The bundle marks three questions "(no response provided)". Consistent with the uniform rule that an
absent slot is a correct answer when evidence is absent, no value was invented for any of them:

| Unanswered source question | Handling |
|---|---|
| Was there any pre-processing for de-identification of the patients? | Gap recorded explicitly in `preprocessing_strategies[1]` and `is_deidentified.deidentification_details`; no method asserted. |
| If de-identified, were measures taken to avoid re-identification? | Gap recorded in `participant_privacy.reidentification_risk` (full) and `is_deidentified` (both). |
| Is there an erratum? | `errata` left unpopulated in both records. |

Other slots left unpopulated for absence of evidence rather than by oversight: `file_collections`,
`total_file_count`, `total_size_bytes`, `variables`, `imputation_protocols`, `annotation_analyses`,
`machine_annotation_tools`, `parent_datasets`, `download_url`, `issued`, `created_on`,
`last_updated_on`, `status`, `citation`. In particular no DUO `data_use_permission` enum value was
asserted: the bundle points to a license file for its terms and does not enumerate permissions, so
mapping to DUO would have been inference rather than extraction. Likewise `hipaa_compliant` was left
unset because the bundle never mentions HIPAA.

### Re-validation after corrections

Both files re-validated clean after every correction (commands and results in the final section).

## Phase 4 — strict full/core reconciliation

### Method

Core was not transcribed by hand. It was produced by loading the Phase 3-audited full record,
intersecting its populated top-level slots against the `CoreDataset` induced-slot inventory resolved
at runtime with LinkML `SchemaView`, and re-serialising the surviving values unchanged. Deep identity
for schema-identical slots is therefore structural rather than best-effort. No shared value was
condensed, paraphrased, reordered, or omitted to make core shorter.

### Shared-slot result

- Schema-identical slots compared by the validator: **76** — all present-in-both or absent-in-both,
  all deeply identical including every nested mapping value and list item order.
- Range-differing shared slots found by comparing induced ranges across `Dataset` and `CoreDataset`:
  **0**. Every slot populated in both records has the identical induced range and cardinality.
- Projected slots reported by the validator: `resources`. Unpopulated in both records (the bundle
  describes no component sub-datasets), so the projection is vacuously equal — no `id` matching or
  coverage check was required.
- Validator warnings: **none**.

### Full-only content (schema-driven, not divergence)

Eleven populated top-level slots exist in `Dataset` but not in `CoreDataset`, so they are absent from
core by schema design rather than by a reconciliation decision:

`related_datasets`, `subsets`, `relationships`, `splits`, `direct_collection`,
`collection_notifications`, `collection_consents`, `consent_revocations`, `participant_privacy`,
`participant_compensation`, `third_party_sharing`.

Where the underlying fact is also expressed through a shared slot, core retains it: the 70/15/15
recommended split proportions survive in `intended_uses[0].examples`; the balancing rationale survives
in `known_biases[0].mitigation_strategy` and `known_limitations[2].recommended_mitigation`; public
versus controlled-access tiering survives in `sensitive_elements` and `license_and_use_terms`; the
EHR-screening recruitment route survives in `sampling_strategies[1].source_data`. Content with no
shared-slot expression — participant compensation ($200 per study visit), consent and notification
procedure detail, consent-revocation terms, and participant-privacy detail — is full-only. This is
the designed core projection, not a loss to be repaired.

### Core-only slots

`distributions` and `dialect` exist in `CoreDataset` but not in `Dataset`. Both were left
unpopulated:

- `distributions` — the bundle gives no file-level path, format, byte count, checksum, media type, or
  encoding for any distribution. The distribution facts it does give (FAIRhub platform, dataset DOI)
  are already carried identically in both records by the shared `distribution_formats` slot.
  Populating `distributions` would have restated those two facts in a second shape while inventing
  the file-level fields the class exists to hold.
- `dialect` — the bundle states no CSV/TSV dialect parameters.

Because `file_collections` is unpopulated in full and `distributions` is unpopulated in core, the
full→core `file_collections`→`distributions` mapping is empty on both sides and there is nothing to
conflict. `total_file_count` and `total_size_bytes` are likewise unpopulated, so no scope comparison
against distribution-level values arises. `is_tabular` is `false` in both records, consistent with the
bundle's statement that the data encompass tabular, imaging, and physiological signal/waveform data;
no format list is asserted anywhere that could contradict it.

### Semantic review of related content

Reviewed and found free of contradiction within and between the two records:

- **Identity / version / access** — top-level `id`, `doi`, `version`, `license`, `page`, `publisher`
  agree with `version_access`, `distribution_dates`, `distribution_formats`, `license_and_use_terms`,
  and `updates`. The single-DOI-per-latest-version model is internally consistent: the bundle gives
  one DOI and identifies it as this (third, current) version's DOI.
- **Historical versus current release** — differing participant counts (204 / 1067 / 2280) and the
  dropped Snellen visual acuity variables are scoped to their versions everywhere they appear, and are
  treated as version history rather than as contradictions.
- **Update policy** — `updates.frequency` ("approximately once a year, as new static versions rather
  than in-place updates") does not contradict `updates.update_details` ("the dataset will not be
  updated"): the bundle distinguishes in-place update from new-version release, and both records
  preserve that distinction.
- **De-identification versus sensitivity** — `is_deidentified.identifiable_elements_present: false`
  and `confidential_elements[0].confidential_elements_present: false` coexist with
  `sensitive_elements[0].sensitive_elements_present: true` without conflict, because the bundle
  states the public tier holds no sensitive data while the controlled-access tier holds race,
  ethnicity, sex, zip code, genetic sequencing data, past health records, and accident reports. Both
  records state the tier distinction explicitly.
- **Subpopulations** — `subpopulation_elements_present: false` follows the bundle's own "No" answer;
  the nuance that diabetes-status strata drive the recommended splits and that demographics exist
  under controlled access is recorded in the same object's `description` rather than being allowed to
  silently contradict the boolean.

### Divergences requiring correction in Phase 4

**None.** No schema-identical slot differed in presence or value between the two records, so
`--sync-core` was not needed and was not run; the validator was run only as an independent check and
passed on the first invocation.

## Commands run

```bash
poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_all.yaml \
  -C Dataset data/d4d_concatenated/claudecode_agent_healthsheet/2026-07-28_claude-opus-5-generic_rep1/AI_READI_d4d.yaml
# -> No issues found

poetry run linkml-term-validator validate-data \
  data/d4d_concatenated/claudecode_agent_healthsheet/2026-07-28_claude-opus-5-generic_rep1/AI_READI_d4d.yaml \
  --schema src/data_sheets_schema/schema/data_sheets_schema_all.yaml --target-class Dataset
# -> Validation passed

poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml \
  -C CoreDataset data/d4d_concatenated/claudecode_agent_healthsheet_core/2026-07-28_claude-opus-5-generic_rep1/AI_READI_d4d_core.yaml
# -> No issues found

poetry run linkml-term-validator validate-data \
  data/d4d_concatenated/claudecode_agent_healthsheet_core/2026-07-28_claude-opus-5-generic_rep1/AI_READI_d4d_core.yaml \
  --schema src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml --target-class CoreDataset
# -> Validation passed

poetry run python -m data_sheets_schema.d4d_pair_consistency \
  --full data/d4d_concatenated/claudecode_agent_healthsheet/2026-07-28_claude-opus-5-generic_rep1/AI_READI_d4d.yaml \
  --core data/d4d_concatenated/claudecode_agent_healthsheet_core/2026-07-28_claude-opus-5-generic_rep1/AI_READI_d4d_core.yaml
# -> PASS: 76 schema-identical slots; projected slots=['resources']

poetry run d4d provenance record --project AI_READI --method claudecode_agent_healthsheet \
  --label 2026-07-28_claude-opus-5-generic_rep1 \
  --input-bundle data/preprocessed/concatenated/AI_READI_healthsheet_only.txt
```

## Files changed

- `data/d4d_concatenated/claudecode_agent_healthsheet/2026-07-28_claude-opus-5-generic_rep1/AI_READI_d4d.yaml` (created; 3 Phase 3 back-ports applied)
- `data/d4d_concatenated/claudecode_agent_healthsheet_core/2026-07-28_claude-opus-5-generic_rep1/AI_READI_d4d_core.yaml` (created)
- `data/d4d_concatenated/claudecode_agent_healthsheet_core/2026-07-28_claude-opus-5-generic_rep1/AI_READI_reconciliation.md` (this report)
- `data/d4d_concatenated/claudecode_agent_healthsheet_core/2026-07-28_claude-opus-5-generic_rep1/AI_READI_provenance.yaml` (live provenance record)

## Final results

| Result | Value |
|---|---|
| Full populated top-level slots | 73 |
| Core populated top-level slots | 62 |
| Full schema validation | pass |
| Full ontology-term validation | pass |
| Core schema validation | pass |
| Core ontology-term validation | pass |
| Schema-identical shared slots compared | 76 |
| Shared-slot divergences | 0 |
| Projected-slot divergences | 0 (`resources` unpopulated in both) |
| Semantic contradictions unresolved | 0 |
| Prior-D4D reuse detected | none |
