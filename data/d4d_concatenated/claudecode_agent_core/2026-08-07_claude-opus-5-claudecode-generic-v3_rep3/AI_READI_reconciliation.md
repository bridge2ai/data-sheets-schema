# AI_READI full/core reconciliation

- **Run label:** `2026-08-07_claude-opus-5-claudecode-generic-v3_rep3`
- **Arm:** BASELINE (input documents only)
- **Mode:** four-phase project agent, generic prompt
- **Agent runtime:** Claude Code · **Provider:** Anthropic · **Model:** claude-opus-5 ·
  **Reasoning effort:** high · **Temperature:** 0.0
- **Prompt:** `src/download/prompts/d4d_generic_arm_prompt.md`
- **Declared input bundle:** `data/preprocessed/concatenated/AI_READI_preprocessed.txt`
- **Source manifest:** `data/preprocessed/source_manifest.yaml`
- **Full record:**
  `data/d4d_concatenated/claudecode_agent/2026-08-07_claude-opus-5-claudecode-generic-v3_rep3/AI_READI_d4d.yaml`
- **Core record:**
  `data/d4d_concatenated/claudecode_agent_core/2026-08-07_claude-opus-5-claudecode-generic-v3_rep3/AI_READI_d4d_core.yaml`

## Referent

`Dataset` admits one referent. The referent chosen is **the AI-READI flagship type 2
diabetes dataset as published on FAIRhub, pinned to its current release, version 3.0.0**
(DOI `10.60775/fairhub.3`, made available 2025-11-17, 2280 participants, 356,343 files,
3.82 TB).

The declared bundle also carries the superseded version 2.0.0 FAIRhub record and version
2.0.0 documentation. Those are treated as **evidence about a historical release**, not as
a second referent: their figures appear only inside `version_access` and
`related_datasets`, explicitly scoped to v2.0.0, and never in the top-level identity,
size or count slots. The FAIRhub "Mini Version" (record 4, DOI `10.60775/fairhub.4`) is
recorded as a distinct related dataset rather than as a version of the referent, because
the manifest capture states it is a separate 100-participant record for pipeline
development. The same referent is held in both the full and core records; the core `id`,
`doi`, `version`, `title` and `name` are byte-identical to the full record's.

## Phase 3 — source and provenance audit

### Provenance boundary

- Factual inputs read: the declared bundle only, plus
  `data/preprocessed/source_manifest.yaml`.
- Structural inputs read: `data_sheets_schema_all.yaml` (class `Dataset`),
  `data_sheets_schema_core_all.yaml` (classes `CoreDataset`, `CoreDistribution`,
  `FormatDialect`) and their induced slot inventories and enums, resolved at runtime with
  LinkML `SchemaView`.
- Instruction inputs read: `.claude/agents/d4d-provenance-guard.md`,
  `.claude/commands/d4d-full-core.md`, `.claude/commands/d4d-agent.md`,
  `src/download/prompts/d4d_generic_arm_prompt.md`.
- **No prior D4D record was read, opened, grepped or consulted**, from any arm, label or
  date. Nothing under `data/d4d_concatenated/` was read except this run's own two output
  files, and nothing under `data/ro-crate_packages/` was touched. No evaluation or
  reconciliation report from any earlier run was read. No prior-D4D content entered this
  agent's context from the parent conversation.
- Phase 2 read exactly the same-run Phase 1 full record at the path above, which carries
  this run's exact version label.

### Structure derived from schema, not from example

Every emitted slot name, range, cardinality, inlining behaviour and enum value was taken
from the induced classes. Three points where the schema overrode the intuitive shape:

- `Creator.principal_investigator`, `LicenseAndUseTerms.contact_person` and the other
  `Person`-ranged slots are **not inlined**: the schema requires a bare identifier
  string. Person objects written inline failed validation and were replaced by ORCID
  references, with the name, degree and contact email retained in the surrounding
  `description`, which is the only slot that can carry them.
- `Organization` **is** inlined (it declares no identifier), so `affiliations` carries
  full objects with ROR-URL `id`s.
- `DataSubset` inherits from `Dataset` and therefore requires `id`; the three recommended
  splits carry synthetic fragment URIs under the dataset page.

`d4d:docExample` annotations were not used as values anywhere.

### Findings against the current sources

The bundle contains sources that disagree. Per the uniform decision rules these are
represented rather than silently resolved; nine are recorded in the record's top-level
`source_caveats`, and the local ones are attached to the slot they affect.

| # | Disagreement | How represented |
|---|---|---|
| 1 | v2.0.0 (2.01 TB, 165,051 files, "no longer accessible") vs v3.0.0 (3.82 TB, 356,343 files) | v3.0.0 values in top-level slots; v2.0.0 figures scoped inside `version_access` and `related_datasets` |
| 2 | Affiliation of Aaron Lee and Cecilia S. Lee: "Washington University in St. Louis" (FAIRhub study metadata, ROR 01yc7t268) vs University of Washington (BMJ Open, Nature Metabolism, NIH RePORTER) | Transcribed as FAIRhub states it, with a per-creator `source_caveats` naming the other three sources |
| 3 | Enrolment start 18 July 2023 (BMJ Open) vs 2023-07-19 (FAIRhub) | Both recorded, in two separate `collection_timeframes` entries with a caveat |
| 4 | Participant series 204 / 863 / 1213 increments (FAIRhub README) vs 204 / 1067 / 2280 cumulative (healthsheet) | Cumulative figures used in `instances`, with a caveat naming the README series |
| 5 | Licence v1.0 text in the bundle ("research and commercial purposes", UW as Licensor, Zenodo 10.5281/zenodo.10642459) vs v2.0 named by v3.0.0 metadata (Zenodo 10.5281/zenodo.17555036, access conditioned on T2DM-only research) | Both stated and attributed in `license_and_use_terms`; `data_use_permission` set to `disease_specific_research` from the access condition, with a caveat |
| 6 | Target enrolment 4,600 (IRB protocol) vs 4,000 (BMJ Open, Nature Metabolism, NIH RePORTER, FAIRhub) | Caveat only; no target-enrolment figure is asserted as a dataset fact |
| 7 | Acronym expansion "…Equitable Atlas…" (BMJ Open) vs "…Exploratory Atlas…" (NIH RePORTER, healthsheet, README) vs "AI Ready and Exploratory Atlas…" (FAIRhub official title) | Caveat; `title` uses the FAIRhub dataset title, which does not expand the acronym |
| 8 | De-identification: FAIRhub type `NoDeIdentification` ("no identifiers were collected") vs Nature Metabolism "stripped of PHI … via the Safe Harbor method" | Both in `is_deidentified.method`, with a caveat |
| 9 | Healthsheet says no demographic sub-populations are identified, while the README publishes aggregate race/ethnicity and sex counts | Both in `subpopulations`, distinguished as per-instance labels vs cohort summary statistics, with a caveat |

Two further points were handled by splitting a multivalued slot rather than merging:

- **Sensitivity.** `sensitive_elements` has two entries — public release
  (`sensitive_elements_present: false`) and controlled-access release (`true`) — because
  the healthsheet answer is different for each and merging them would assert something no
  source states.
- **Sampling.** `sampling_strategies` has two entries — study recruitment
  (`is_sample: true`, non-probability, not representative by design) and released
  composition (`is_sample: false`, all enrolled participants) — for the same reason.

### Corrections made in Phase 3

Four defects were found by auditing the Phase 1 draft against the bundle and the
slot-filling contract, and all were corrected in the full record first:

1. **Unsupported assertion removed.** `at_risk_populations.description` asserted that the
   IRB application answered "no" to active recruitment of Native American or non-US
   indigenous populations. The captured IRB form is a template whose checkbox selections
   were not preserved by text extraction, so no source supports that answer. Replaced
   with what the sources do state: the planned tribal consultation and Native Biodata
   Consortium engagement as separate activities, and the healthsheet's statement that the
   cohort does not include Native Americans or Pacific Islanders.
2. **Mis-attributed statement.** The "platform is currently in beta" note appears on the
   v2.0.0 FAIRhub capture, not the v3.0.0 capture; `maintainers` was re-attributed.
3. **Inferred boolean removed.** `external_resources.archival: false` was an inference —
   the healthsheet's answer does not address whether official archival versions exist.
   The flag was dropped and caveat (9) records the gap.
4. **Slot-filling violations.** `external_resources.future_guarantees` held evidence
   commentary ("no guarantee … is stated in the sources") rather than content; that
   commentary moved out and the substantive sentence moved to `description`. And
   `license_and_use_terms.description` restated the sibling `contact_person` ORCID; it now
   carries only the name and email that the bare reference cannot hold.

### Shape audit

- No prose in list-ranged slots: `keywords`, `versions_available`, `release_dates`,
  `restrictions`, `regulatory_restrictions`, `irb_approval`, `regulatory_compliance`,
  `special_protections`, `external_resources`, `affected_subsets`, `examples`,
  `access_urls`, `missing`, `why_missing` all carry lists of atomic items.
- No enum value outside its schema definition. Where the schema has no term for an
  observed value, the slot is omitted and the fact stated in `description` — this applies
  to DICOM (absent from core `FormatEnum` and `MediaTypeEnum`) and to
  `Maintainer.role` (no term fits a multi-institution academic consortium).
- No commentary embedded in a `name`, `id` or affiliation value; ORCID and ROR
  identifiers are bare URIs.
- Evidence commentary is confined to `source_caveats` at eight sites; `notes` is used once,
  at top level, to state the referent pinning, which is not a dataset fact `description`
  could hold.

### Deliberate omissions

Omitted for absence of evidence, per "prefer omission over inference":
`variables` (the bundle points to `docs.aireadi.org` and a REDCap forms PDF rather than
supplying a variable dictionary; the BMJ Open clinical-chemistry table gives normal
reference ranges, which are not the `minimum_value`/`maximum_value` of any released
variable, and its units are not URIs as the `unit` slot requires),
`imputation_protocols`, `annotation_analyses`, `machine_annotation_tools` (no labeling was
performed), `errata` (the healthsheet response is blank), `compression`, `status`,
`created_on`, `last_updated_on`, `modified_by`, `was_derived_from`, `conforms_to_class`,
`parent_datasets`, `resources`, and the ontology-bound `Instance.data_topic` and
`Instance.data_substrate` (no B2AI_TOPIC or B2AI_SUBSTRATE term is named in the bundle).

### Internal consistency checks

All arithmetic in the record was recomputed against the README split table:

- Splits sum to the whole: 1576 + 352 + 352 = 2280, matching `instances.counts`, the
  `description`, and the healthsheet.
- Train race/ethnicity 204 + 369 + 343 + 660 = 1576; sex 599 + 977 = 1576; diabetes status
  600 + 384 + 487 + 105 = 1576.
- Validation 88 × 4 = 352; 176 + 176 = 352; 88 + 88 + 109 + 67 = 352.
- Test 88 × 4 = 352; 176 + 176 = 352; 88 + 88 + 90 + 86 = 352.
- Totals 380 + 545 + 519 + 836 = 2280; 951 + 1329 = 2280; 776 + 560 + 686 + 258 = 2280.
- `total_size_bytes: 3815969779678` is the API's `size` field and is consistent with the
  README's "around 3.82 TB"; `total_file_count: 356343` matches the API `fileCount`, the
  README and the FAIRhub page.
- Repeated identifiers are consistent everywhere they appear: DOI `10.60775/fairhub.3`
  (`id`, `doi`, `version_access.latest_version_doi`, `third_party_sharing`), grant
  `OT2OD032644` (`funders`, `human_subject_research`, `data_collectors`), IRB
  `STUDY00016228` (`ethical_reviews`, `human_subject_research`), collection window
  2023-07-19/2025-05-01 (`description`, `collection_timeframes`), release date 2025-11-17
  (`issued`, `distribution_dates`, `version_access`), and Aaron Lee's ORCID (`creators`,
  `license_and_use_terms.contact_person`).

## Phase 4 — strict full/core reconciliation

### Shared slots, derived at runtime

Derived with LinkML `SchemaView` over `Dataset` and `CoreDataset`; no hand-written field
list was used.

- **Shared slots:** 79
- **Schema-identical (strict-identity) slots:** **78**
- **Projected slots:** 1 — `resources` (`Dataset` in full, `CoreDataset` in core)
- **Full-only slots:** 17 — `citation`, `collection_consents`, `collection_notifications`,
  `consent_revocations`, `direct_collection`, `file_collections`, `parent_datasets`,
  `participant_compensation`, `participant_privacy`, `related_datasets`, `relationships`,
  `splits`, `subsets`, `third_party_sharing`, `total_file_count`, `total_size_bytes`,
  `variables`
- **Core-only slots:** 2 — `distributions` (`CoreDistribution`), `dialect`
  (`FormatDialect`)

### Identity result

Of the 78 strict-identity slots, **67 are populated in both records and 11 are absent from
both**. Every populated one has deeply identical parsed YAML, including nested mapping
values and list item order; no narrative field was condensed, paraphrased, reordered or
omitted in core. Core was synchronized once from the Phase 3-audited full record with
`--sync-core`, then re-checked without it as an independent pass.

`resources` is absent from both records, so the projection is vacuously equal: no resource
`id` set to match, equal (empty) coverage.

### Related, non-identical content: `file_collections` → `distributions`

The validator emits a `semantic-review-required` warning here by construction. That
warning is not evidence that review occurred; the review was performed and is recorded
below. Ten full `file_collections` map one-to-one onto ten core `distributions`, matched
on `id`; there are no unmatched core distributions.

| `file_collections` `id` fragment | `path` | Standard | Core `format` / `media_type` |
|---|---|---|---|
| `#cardiac_ecg` | `cardiac_ecg` | WFDB | omitted — no enum term |
| `#clinical_data` | `clinical_data` | OMOP CDM, CSV files | `CSV` / `text/csv` |
| `#environment` | `environment` | ESDS ASCII; BMJ Open records `.csv` | `CSV` / `text/csv` |
| `#retinal_flio` | `retinal_flio` | DICOM (from `.sdt`) | omitted — no enum term |
| `#retinal_oct` | `retinal_oct` | DICOM | omitted — no enum term |
| `#retinal_octa` | `retinal_octa` | DICOM | omitted — no enum term |
| `#retinal_photography` | `retinal_photography` | DICOM (from `.fda`) | omitted — no enum term |
| `#wearable_activity_monitor` | `wearable_activity_monitor` | Open mHealth (from `.FIT`) | omitted — format not stated |
| `#wearable_blood_glucose` | `wearable_blood_glucose` | Open mHealth; BMJ Open records `.csv` | omitted — sources disagree on the released format |
| `#root-metadata` | *(no path)* | CDS v0.1.1 | omitted — mixed formats |

Review findings, checked for contradiction rather than restated:

- **Names, paths and descriptions agree.** Every core `path` equals the full `path`
  (the root-metadata collection has none in either record), and every core description
  preserves the full description's modality and device inventory. Where the full record
  carried the standard in `conforms_to` — a slot `CoreDistribution` does not have — the
  standard and its URL were carried into the core `description` rather than dropped. No
  statement was added that the full record does not make.
- **No conflict on formats.** The four `distribution_formats` entries, which are a
  strict-identity slot and therefore byte-identical in both records, list
  `application/dicom`, `text/csv`, `application/json` and `text/markdown`. The two core
  `format: CSV` assignments are consistent with that list. No core distribution asserts a
  format the full record contradicts. `is_tabular: false` is identical in both and is
  consistent with a distribution set that is mostly DICOM imaging and waveform data.
- **No byte counts, checksums or access URLs are asserted at distribution level**, in
  either record, because the bundle gives none per directory. `CoreDistribution.bytes`,
  `hash`, `md5` and `sha256` are therefore unset — an absence, not a disagreement.
- **Scope of the totals.** `total_file_count` (356,343) and `total_size_bytes`
  (3,815,969,779,678) exist only in the full record and describe the whole v3.0.0 release.
  No distribution-level counterpart exists at the same scope, so there is nothing to
  compare and no contradiction is possible. Deliberately, no synthetic whole-release
  distribution carrying those totals was added, because it would overlap the scope of the
  ten per-directory distributions and create a double count. Both figures survive in core
  regardless: they are stated in `description` and in
  `version_access.versions_available`, both strict-identity slots.
- **`dialect` is unset.** `FormatDialect` describes a delimited-text dialect
  (`delimiter`, `quote_char`, `header`, `comment_prefix`, `double_quote`). The bundle
  states none of these for any AI-READI file, so the slot is omitted rather than guessed.
- **Compression.** Unset in both records and in every distribution; no source describes
  the release as compressed.
- **Identity, version and access facts agree.** `id`, `doi`, `version`, `title`, `name`,
  `license`, `issued`, `publisher`, `page`, `download_url`, `version_access`,
  `distribution_dates`, `license_and_use_terms` and `regulatory_restrictions` are all
  strict-identity slots and are deeply identical, so the top-level identity, version and
  access story cannot diverge between the two records. All of them name v3.0.0 /
  `10.60775/fairhub.3` / 2025-11-17, and the historical v1.0.0 and v2.0.0 statements are
  confined to `version_access` and remain explicitly scoped as historical in both files.

### Content that core cannot carry

Fifteen populated full-only slots have no core home: `citation`, `collection_consents`,
`collection_notifications`, `consent_revocations`, `direct_collection`,
`file_collections`, `participant_compensation`, `participant_privacy`,
`related_datasets`, `relationships`, `splits`, `subsets`, `third_party_sharing`,
`total_file_count`, `total_size_bytes`. (`parent_datasets` and `variables` are unpopulated
in both.) This is a property of the `CoreDataset` schema, not a reconciliation failure;
nothing was invented in core to compensate, and nothing was removed from full to match.

## Commands run

```bash
poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_all.yaml \
  -C Dataset data/d4d_concatenated/claudecode_agent/2026-08-07_claude-opus-5-claudecode-generic-v3_rep3/AI_READI_d4d.yaml

poetry run linkml-term-validator validate-data \
  data/d4d_concatenated/claudecode_agent/2026-08-07_claude-opus-5-claudecode-generic-v3_rep3/AI_READI_d4d.yaml \
  --schema src/data_sheets_schema/schema/data_sheets_schema_all.yaml --target-class Dataset

poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml \
  -C CoreDataset data/d4d_concatenated/claudecode_agent_core/2026-08-07_claude-opus-5-claudecode-generic-v3_rep3/AI_READI_d4d_core.yaml

poetry run linkml-term-validator validate-data \
  data/d4d_concatenated/claudecode_agent_core/2026-08-07_claude-opus-5-claudecode-generic-v3_rep3/AI_READI_d4d_core.yaml \
  --schema src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml --target-class CoreDataset

poetry run python -m data_sheets_schema.d4d_pair_consistency \
  --full data/d4d_concatenated/claudecode_agent/2026-08-07_claude-opus-5-claudecode-generic-v3_rep3/AI_READI_d4d.yaml \
  --core data/d4d_concatenated/claudecode_agent_core/2026-08-07_claude-opus-5-claudecode-generic-v3_rep3/AI_READI_d4d_core.yaml \
  --sync-core

poetry run python -m data_sheets_schema.d4d_pair_consistency \
  --full data/d4d_concatenated/claudecode_agent/2026-08-07_claude-opus-5-claudecode-generic-v3_rep3/AI_READI_d4d.yaml \
  --core data/d4d_concatenated/claudecode_agent_core/2026-08-07_claude-opus-5-claudecode-generic-v3_rep3/AI_READI_d4d_core.yaml

poetry run d4d provenance record --project AI_READI --method claudecode_agent \
  --label 2026-08-07_claude-opus-5-claudecode-generic-v3_rep3 \
  --input-bundle data/preprocessed/concatenated/AI_READI_preprocessed.txt \
  --prompt src/download/prompts/d4d_generic_arm_prompt.md

poetry run d4d runs validate --label 2026-08-07_claude-opus-5-claudecode-generic-v3_rep3 --project AI_READI
poetry run d4d runs check --strict --label 2026-08-07_claude-opus-5-claudecode-generic-v3_rep3
```

## Files changed

- `data/d4d_concatenated/claudecode_agent/2026-08-07_claude-opus-5-claudecode-generic-v3_rep3/AI_READI_d4d.yaml`
  — created in Phase 1, corrected in Phase 3 (four corrections above), unchanged in Phase 4.
- `data/d4d_concatenated/claudecode_agent_core/2026-08-07_claude-opus-5-claudecode-generic-v3_rep3/AI_READI_d4d_core.yaml`
  — created in Phase 2, re-synchronized from the audited full record in Phase 4 and
  stamped `# Phase 4 reconciliation: completed`.
- `data/d4d_concatenated/claudecode_agent_core/2026-08-07_claude-opus-5-claudecode-generic-v3_rep3/AI_READI_reconciliation.md`
  — this report.

No file outside this run's three declared outputs was written.

## Final results

| Check | Result |
|---|---|
| Full — `linkml-validate` (`Dataset`) | **No issues found** |
| Full — `linkml-term-validator` | **Validation passed** |
| Core — `linkml-validate` (`CoreDataset`) | **No issues found** |
| Core — `linkml-term-validator` | **Validation passed** |
| Pair consistency | **PASS**, 78 schema-identical slots, projected slots `['resources']` |
| Semantic review of related content | Performed above; 10 deterministic `file_collections` ↔ `distributions` matches, 0 unmatched core distributions, 0 contradictions |
| Populated top-level slots | full **82**, core **68** |

**Reconciliation outcome: PASS with no unresolved divergence.** The only differences
between the two records are the ones the two schemas require: 15 populated full-only slots
that `CoreDataset` does not define, and the `file_collections` → `distributions`
projection reviewed above. Nothing diverged within the strict-identity set.
