# AI_READI D4D full/core reconciliation — healthsheet-only arm, replicate 2

- **Agent runtime:** Claude Code
- **Provider:** Anthropic
- **Model:** claude-opus-5[1m]
- **Mode:** four-phase project agent (Phases 1-4 run sequentially in one context)
- **Temperature:** 0.0
- **Generated:** 2026-07-27
- **Arm:** HEALTHSHEET-ONLY (single structured upstream source)

## Files

| Role | Path |
|---|---|
| Source bundle (only factual input) | `data/preprocessed/concatenated/AI_READI_healthsheet_only.txt` |
| Full | `data/d4d_concatenated/claudecode_agent_healthsheet/2026-07-27_claude-opus-5_rep2/AI_READI_d4d.yaml` |
| Core | `data/d4d_concatenated/claudecode_agent_healthsheet_core/2026-07-27_claude-opus-5_rep2/AI_READI_d4d_core.yaml` |
| Full schema | `src/data_sheets_schema/schema/data_sheets_schema_all.yaml` (class `Dataset`) |
| Core schema | `src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml` (class `CoreDataset`) |

Line counts (informational metadata only, not a quality gate): full 1239, core 778.

## Phase 3 — Source and provenance audit

### Provenance boundary

The only factual input read was `AI_READI_healthsheet_only.txt` (539 lines, 14 sections,
84 questions, 81 answered). Structure was derived at runtime from the two LinkML schemas
via `SchemaView` (`class_induced_slots` over `Dataset` and `CoreDataset` and every nested
range class), plus `D4D_Core.yaml` to confirm that `CoreDataset` declares its fields via
`attributes`.

No prior full or core D4D record, evaluation, or reconciliation report was read, and no
prior D4D content from the parent conversation was used as evidence. The output parent
directories were listed once (`ls -d`) to confirm that the `_rep2` paths did not already
exist; the sibling `_rep1` directories were seen only as directory names and no file under
them was opened. The following forbidden inputs were not read at any point:
`AI_READI_preprocessed.txt`, `data/preprocessed/individual/AI_READI/`,
`data/raw/AI_READI/`, `data/preprocessed/source_manifest.yaml`, any other path under
`data/d4d_concatenated/` or `data/d4d_individual/`, and live web content.

`Source manifest:` in both headers is recorded as *not applicable* rather than pointing at
`data/preprocessed/source_manifest.yaml`, because the manifest does not govern this
single-source bundle and reading it was forbidden for this arm.

### Source-internal disagreements found and how they were resolved

1. **Grant number rendered two ways.** MOTIVATION gives `OT2ODO32644`; COLLECTION gives
   `OT2OD032644`. Resolved to `grant_number: OT2OD032644` (the form that parses as an NIH
   activity-code + institute + serial string, and the form used in the answer that
   describes how personnel effort was charged). The variant is recorded verbatim in the
   `Grant.description` so the discrepancy is not silently erased. No external source was
   consulted to break the tie.
2. **Enrollment window described as "the first year" inside a version-3 datasheet.**
   COMPOSITION states the dataset "contains data from all participants who have been
   enrolled during the first year of data collection for AI-READI", while VERSIONING and
   COLLECTION both scope this release to 2023-07-19 through 2025-05-01 and to the end of
   the second study year. The version- and date-scoped answers are more specific and are
   the current-version statements, so `sampling_strategies[0].strategies` records "all
   participants who have been enrolled during the data collection period covered by this
   version" rather than reproducing "first year". `collection_timeframes[0]` carries the
   explicit dates.
3. **"No demographic sub-populations" versus sensitive controlled-access demographics.**
   DEMOGRAPHIC INFORMATION answers "No", while GENERAL INFORMATION and COMPOSITION state
   that race, ethnicity, sex, and 5-digit zip code are held under controlled access, and
   LABELING describes splits balanced for sex and race/ethnicity. Resolved by access-tier
   scope, not by preferring one answer: `subpopulations[0].subpopulation_elements_present`
   is `false` (the dataset does not identify subpopulations) and the same object records
   that these variables are withheld from the public release and present in controlled
   access. `sensitive_elements[0]` carries the controlled-access detail.
4. **Balance statements scoped to the pilot.** CHALLENGE says "the pilot study is not
   balanced across these parameters" — a historical, pilot-scoped claim inside a version-3
   datasheet. It is retained verbatim in `known_biases[0].bias_description` with its
   original "pilot study" scope word intact, alongside the current-release statement that
   periodic updates "may not have achieved balanced distribution across groups".

### Internal consistency checks (each verified against the source)

- Participant counts: 204 (v1) + 863 additional (v2) = 1067 (v2 total); 2280 (v3). The
  arithmetic in the source is self-consistent. `instances[0].counts: 2280` agrees with
  COMPOSITION ("2280 instances in this current version"), with VERSIONING, and with
  `version_access.versions_available`.
- Version identity: `version: '3'`, `doi: 10.60775/fairhub.3`, `id` and
  `version_access.latest_version_doi` = `https://doi.org/10.60775/fairhub.3`. Mutually
  consistent; the DOI's trailing `3` is not used to infer anything the text does not say.
- Release dates: v1 May 2024, v2 November 2024, v3 November 2025 (DISTRIBUTION). COMPOSITION's
  "released fall 2025" is consistent with November 2025; no contradiction recorded.
- Collection window `2023-07-19`/`2025-05-01` appears identically in VERSIONING and
  COLLECTION.
- License URL `https://doi.org/10.5281/zenodo.17555036` is repeated in four answers
  (MOTIVATION, DISTRIBUTION x3) with no variation, and is used identically in
  `license`, `discouraged_uses`, `license_and_use_terms`, `ip_restrictions`, and
  `regulatory_restrictions`.
- Withdrawal/retention: `consent_revocations` ("data already shared or used stays in the
  dataset") and `retention_limit` ("no limits on retention") are consistent, not
  contradictory.
- Update policy: `updates.frequency` (annual new versions) and
  `version_access.version_details` (static versions, dataset itself never updated) agree.

### Judgment calls recorded for transparency

- `language: English` is derived from "English language was used for communication with
  study participants" plus the eligibility criterion "Must speak and read English". The
  healthsheet never states the language of the data files themselves.
- `publisher` and `page` are both set to `http://fairhub.io/`. The healthsheet names
  FAIRhub as the distribution platform and host ("hosted on FAIRhub through Microsoft
  Azure") but never names a formal publisher or a landing-page URL distinct from the
  platform.
- `is_tabular: false` follows from "These encompass tabular data, imaging data, and
  physiological signal/waveform data" — the dataset as a whole is not tabular.
- The three questions the source itself marks `(no response provided)` were left
  unanswered in both records rather than annotated inside the YAML; they are listed under
  Gaps below.

### Back-porting

Phase 2 produced no source-supported fact that the Phase 1 full record was missing, so no
back-port into the full record was required and no fact was corrected during Phase 3. The
core-only slots (`distributions`, `dialect`) were checked directly against the source: the
healthsheet contains no file paths, formats, byte counts, checksums, media types, or
delimiter/header information, so both remain empty.

## Phase 4 — Strict full/core reconciliation

Shared slots were derived at runtime with `SchemaView` rather than from any hand-written
list. Core was produced by projecting the audited full record onto the induced
`CoreDataset` slot inventory, so schema-identical slots are byte-for-byte the same parsed
content; no narrative field was condensed, paraphrased, reordered, or omitted in core.

**Result: `PASS: 76 schema-identical slots; projected slots=['resources']`** — no
divergence, on both the `--sync-core` run and the independent re-run without it.

### Full-only slots (present in `Dataset`, absent from `CoreDataset`) — 11

`subsets`, `relationships`, `splits`, `direct_collection`, `collection_notifications`,
`collection_consents`, `consent_revocations`, `third_party_sharing`,
`participant_privacy`, `participant_compensation`, `related_datasets`.

These are correctly absent from core (schema-driven omission, not data loss). Note that
this arm's consent, notification, revocation, compensation, and split content — some of
the healthsheet's richest material — lives entirely in these full-only slots and therefore
does not reach the exchange layer.

### Projected and related content

- `resources` (`Dataset` in full, `CoreDataset` in core): absent from both records, so the
  projection is trivially consistent. Coverage equal, no `id` matching required.
- `file_collections` → `distributions`: both empty. `total_file_count` and
  `total_size_bytes` are also empty, so there is no count/size scope to compare against
  distribution-level values. Reviewed and found non-conflicting because nothing is asserted
  on either side.
- `is_tabular` (`false`) is present and identical in both; `dialect` and `compression` are
  absent from both, consistent with a dataset that is not purely tabular and for which no
  packaging format is stated.
- Identity/version/access facts (`id`, `doi`, `version`, `license`, `publisher`, `page`,
  `distribution_formats.access_urls`, `version_access.latest_version_doi`,
  `distribution_dates.release_dates`) were compared across both records and against the
  version history; all agree, and the historical v1/v2 values are scoped as history rather
  than presented as current.

### Commands run

```bash
poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_all.yaml \
  -C Dataset data/d4d_concatenated/claudecode_agent_healthsheet/2026-07-27_claude-opus-5_rep2/AI_READI_d4d.yaml
poetry run linkml-term-validator validate-data \
  data/d4d_concatenated/claudecode_agent_healthsheet/2026-07-27_claude-opus-5_rep2/AI_READI_d4d.yaml \
  --schema src/data_sheets_schema/schema/data_sheets_schema_all.yaml --target-class Dataset
poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml \
  -C CoreDataset data/d4d_concatenated/claudecode_agent_healthsheet_core/2026-07-27_claude-opus-5_rep2/AI_READI_d4d_core.yaml
poetry run linkml-term-validator validate-data \
  data/d4d_concatenated/claudecode_agent_healthsheet_core/2026-07-27_claude-opus-5_rep2/AI_READI_d4d_core.yaml \
  --schema src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml --target-class CoreDataset
poetry run python -m data_sheets_schema.d4d_pair_consistency \
  --full data/d4d_concatenated/claudecode_agent_healthsheet/2026-07-27_claude-opus-5_rep2/AI_READI_d4d.yaml \
  --core data/d4d_concatenated/claudecode_agent_healthsheet_core/2026-07-27_claude-opus-5_rep2/AI_READI_d4d_core.yaml --sync-core
poetry run python -m data_sheets_schema.d4d_pair_consistency \
  --full data/d4d_concatenated/claudecode_agent_healthsheet/2026-07-27_claude-opus-5_rep2/AI_READI_d4d.yaml \
  --core data/d4d_concatenated/claudecode_agent_healthsheet_core/2026-07-27_claude-opus-5_rep2/AI_READI_d4d_core.yaml
```

### Final validation status

| Check | Full | Core |
|---|---|---|
| `linkml-validate` | No issues found | No issues found |
| `linkml-term-validator` | Validation passed | Validation passed |
| `d4d_pair_consistency` (no `--sync-core`) | PASS — 76 schema-identical slots | PASS |

Files changed after the initial write: only the core file, and only by the single permitted
`--sync-core` normalization pass (no content difference; the pair check already passed
before it ran).

## Gaps — what the healthsheet could NOT support (primary result of this arm)

Coverage: **69 of 94** induced `Dataset` slots populated. The 25 empty slots are listed
below, grouped by D4D area.

### Areas with no support whatsoever

1. **Distribution mechanics / file-level metadata.** `file_collections`,
   `total_file_count`, `total_size_bytes`, `download_url`, `compression`, and the core's
   `distributions` and `dialect` are all empty. The healthsheet names the platform
   (FAIRhub), the DOI, and the release dates, but never a file format, directory layout,
   file count, byte size, checksum, media type, or archive packaging. It repeatedly defers
   this to `https://docs.aireadi.org`, which this arm may not read. **This is the single
   largest gap and it removes the entire DCAT-facing half of the exchange layer.**
2. **Variable-level metadata.** `variables` is empty. Across 84 questions the healthsheet
   names exactly two variables (Snellen and logMAR visual acuity, and only to say Snellen
   was dropped in v3). No variable names, types, units, ranges, categories, or missing-value
   codes exist anywhere in the source, so `VariableMetadata` (which requires
   `variable_name`) cannot be instantiated even once.
3. **Named people and organizational identity.** No individual is named anywhere — no PI,
   no author, no maintainer, no contact person, no ORCID, no email. `Creator.affiliations`,
   `Creator.principal_investigator`, and `Creator.credit_roles` are therefore all empty, and
   `maintainers[0]` carries no `role`. Every people-related question defers to
   `https://aireadi.org/team` or to "the README file included with the dataset". The three
   study sites (UAB, UCSD, UW) appear only as *recording sites* in the CHALLENGE and
   COLLECTION answers, so they are recorded where the source puts them and are deliberately
   **not** promoted to creator affiliations.
4. **Citation.** `citation` is empty. The source says citation is required and points to
   `docs.aireadi.org` for the citable resources, but supplies no citation string, no
   reference, and no publication.
5. **Errata.** `errata` is empty — the erratum question is one of the three the source marks
   `(no response provided)`.
6. **At-risk population protections.** `at_risk_populations` is empty. The source states
   exclusion criteria (pregnancy, gestational diabetes, type 1 diabetes) and a minimum age
   of 40, which are recorded under `human_subject_research.special_populations`, but says
   nothing about special protections, assent procedures, or guardian consent.
7. **De-identification method.** Both de-identification questions are `(no response
   provided)`. `is_deidentified` is populated only with what other answers support ("no PII
   is included", internal review for accidental PII); `method` and `identifiers_removed`
   are empty and no de-identification technique is asserted.
8. **Annotation and imputation.** `imputation_protocols`, `annotation_analyses`, and
   `machine_annotation_tools` are all empty — consistent with, and fully explained by, the
   dataset having no labels at all.
9. **Machine-readable licence terms.** `LicenseAndUseTerms.data_use_permission` was left
   empty: the source describes the licence only in prose ("commercial or research purpose
   ... strong requirements around data usage, security, and secondary sharing") and no
   `DataUsePermissionEnum` value can be selected without inference. For the same reason
   `ExportControlRegulatoryRestrictions.hipaa_compliant` and `confidentiality_level` are
   empty — three of the four DISTRIBUTION licence questions answer only "Refer to license".
10. **Provenance and lifecycle timestamps.** `created_on`, `last_updated_on`, `issued`,
    `status`, `modified_by`, `was_derived_from`, `keywords`, `conforms_to_class`,
    `conforms_to_schema`, `parent_datasets`, `resources`. Release dates are given only at
    month precision ("November 2025"), which will not parse as a `datetime`, so `issued`
    was left empty rather than fabricated to day precision.
11. **Prohibited uses and other tasks.** `prohibited_uses` and `other_tasks` are empty. The
    source defers all use restrictions to the licence file without enumerating a single
    prohibited task, so only `discouraged_uses` (pointing at the licence) could be filled.

### Complete list of empty `Dataset` slots (25)

`annotation_analyses`, `at_risk_populations`, `citation`, `compression`,
`conforms_to_class`, `conforms_to_schema`, `created_on`, `download_url`, `errata`,
`file_collections`, `imputation_protocols`, `issued`, `keywords`, `last_updated_on`,
`machine_annotation_tools`, `modified_by`, `other_tasks`, `parent_datasets`,
`prohibited_uses`, `resources`, `status`, `total_file_count`, `total_size_bytes`,
`variables`, `was_derived_from`.

### Where the healthsheet is unusually strong

For contrast, and because it bears on what the restriction actually costs: the DEVICES
section supported 19 device-specific `CollectionMechanism` objects with per-device
operating protocols (21 in total, including REDCap electronic data capture and the
overall procedures entry), and the healthsheet fully supported ethics, consent, collection methodology,
preprocessing/cleaning, versioning, known biases and limitations, and access-tier
sensitivity. The arm's weakness is not narrative coverage — it is **everything
machine-actionable about the bits on disk**, plus every named person and organization.
