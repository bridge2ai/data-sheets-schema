# AI_READI full/core reconciliation — 2026-07-28_claude-opus-5-deprimed_rep2

- Run label: `2026-07-28_claude-opus-5-deprimed_rep2`
- Arm: BASELINE (input documents only)
- Runtime / provider / model: Claude Code / Anthropic / `claude-opus-5[1m]`, temperature 0.0
- Mode: four-phase project agent, de-primed
- Full: `data/d4d_concatenated/claudecode_agent/2026-07-28_claude-opus-5-deprimed_rep2/AI_READI_d4d.yaml`
- Core: `data/d4d_concatenated/claudecode_agent_core/2026-07-28_claude-opus-5-deprimed_rep2/AI_READI_d4d_core.yaml`
- Input bundle: `data/preprocessed/concatenated/AI_READI_preprocessed.txt` (10 source files)
- Manifest: `data/preprocessed/source_manifest.yaml`

## Phase 3 — source and provenance audit

### Provenance

Factual inputs used were the declared bundle and the source manifest only. Structure was
derived at runtime from `Dataset` in `data_sheets_schema_all.yaml` and `CoreDataset` in
`data_sheets_schema_core_all.yaml` via LinkML `SchemaView`; no field list, template, or
example record was used. No prior generated D4D YAML, evaluation output, or reconciliation
report from any arm, label, or date was opened, searched, or cited. The only access to
`data/d4d_concatenated/` outside this run's own two output paths was a directory listing
(`ls`) used to confirm the version label was not already occupied, which the playbook
permits and which exposed no record content.

### Source disagreements resolved

The manifest's curation policy — prefer the current upstream release over the
sheet-selected one where the two disagree — governed every version-scoped fact. Version
3.0.0 is treated as current throughout; v2.0.0 and v1.0.0 facts appear only with explicit
historical scope.

1. **Managing organization.** The FAIRhub structured metadata for v3.0.0 records
   `managingOrganization`, `leadSponsor`, and the affiliations of Aaron Lee and Cecilia Lee
   as "Washington University in St. Louis" (ROR 01yc7t268). This is contradicted by five
   other sources in the same bundle: NIH RePORTER (awardee organization UNIVERSITY OF
   WASHINGTON), the IRB of record (University of Washington HSD, STUDY00016228), the data
   license agreement (Licensor: UNIVERSITY OF WASHINGTON), the study location list
   (University of Washington, Seattle, ROR 00cvxb145), and the Nature Metabolism author
   affiliations. Resolved to the University of Washington on preponderance and authority;
   the discrepancy is recorded in the consortium creator description so a reader comparing
   against the FAIRhub landing page is not misled.
2. **Acronym expansion.** "Equitable" (both peer-reviewed publications) versus
   "Exploratory" (NIH RePORTER, README, healthsheet, registered study title). Neither is
   stale; the project uses both. Both are recorded in `description`, with the registered
   official title named explicitly. Applied as a Phase 3 correction.
3. **License version.** The captured license document is AI-READI-LICENSE-v1.0
   (10.5281/zenodo.10642459); the v3.0.0 FAIRhub record cites "AI-READI custom license
   v2.0" (10.5281/zenodo.17555036). The current DOI is used for `license`; the v1.0 clause
   text is quoted in `license_and_use_terms` and `prohibited_uses` with its scope stated.
4. **Collection start date.** Protocol publication: enrolment began 18 July 2023. FAIRhub
   and the study record: collection window and actual start 19 July 2023. Structured
   `start_date` uses 2023-07-19 (the release's declared window); the 18 July enrolment
   start, the pilot window ending 30 November 2023, and the 1 December 2023 formal
   collection start are all retained as attributed narrative.
5. **Target enrollment.** 4000 in the protocol publication, Nature Metabolism, NIH
   RePORTER, and the registered study record; 4600 in the IRB application, which predates
   the released versions. Both recorded with attribution in `sampling_strategies`. Applied
   as a Phase 3 correction.
6. **Longitudinal follow-up fraction.** ~10% of the cohort (NIH RePORTER, README, IRB)
   versus ~4% expected to undergo a year-4 follow-up (healthsheet). Both retained with
   attribution rather than silently choosing one.
7. **Visit duration.** 2.5–4 hours (protocol publication) versus 3–4 hours (Nature
   Metabolism, IRB). Both recorded, with the IRB note that the visit may be split across
   two days. Applied as a Phase 3 correction.
8. **Stale documentation text not asserted.** The v3.0.0 docs "About" page states that
   v3.0 "contains data from the participants of the pilot study phase" — verbatim
   boilerplate carried over from the v2 page and contradicted by the healthsheet, README,
   and FAIRhub metadata (2280 participants, 19 July 2023 – 1 May 2025). Not asserted.
9. **Low-value bulk.** Per the manifest, `datasetStructureDescription` was treated as a
   file/directory inventory rather than descriptive evidence; only its per-directory
   descriptions, standards, byte sizes, and file counts were used.

### Internal consistency checks

- Version identity is consistent across `id`, `doi`, `version`, `download_url`, `page`,
  `version_access.latest_version_doi`, and `distribution_dates` (all 3.0.0 /
  10.60775/fairhub.3 / 17 November 2025).
- Participant counts reconcile: `instances.counts` 2280 = 1576 train + 352 validation + 352
  test across `subsets`; the version history (204 → 1067 → 2280) matches the README change
  table (204 + 863 + 1213 = 2280).
- `total_file_count` 356,343 exceeds the sum of the nine datatype directories (356,334) by
  9, and `total_size_bytes` 3,815,969,779,678 exceeds the directory sum
  (3,815,969,360,064) by 419,614 bytes. Different scopes, not a contradiction: the totals
  include root-level files (README, LICENSE, CHANGELOG, `participants.tsv`, and the four
  `*.json` metadata files), which are not inside any datatype directory.
- Historical v2.0.0 figures (2.01 TB, 165,051 files, 1067 participants) appear only inside
  explicitly version-scoped statements.

### Corrections applied to the full record

Four, all listed above: items 2, 5, 7, and the managing-organization note from item 1. No
Phase 2 discovery required back-porting a new fact, because core was derived from the
Phase 1 full record plus the same bundle rather than re-extracted independently. Core was
regenerated from the corrected full record after the corrections landed.

### Slots deliberately left absent

`imputation_protocols`, `annotation_analyses`, `machine_annotation_tools`, `errata`,
`parent_datasets`, `resources`, `status`, `created_by`, `created_on`, `modified_by`,
`compression`, `conforms_to_class` — absent from both records because the bundle supports
no value. The healthsheet erratum question is blank in the source and was not converted
into a "no erratum" assertion. Core `dialect` is absent because the bundle describes no
delimiter, quoting, or header conventions; `is_tabular: false` is asserted in both because
the healthsheet states the dataset mixes tabular, imaging, and waveform data.

## Phase 4 — strict full/core reconciliation

### Schema-derived shared-slot analysis

Shared slots were computed at runtime with `SchemaView` from the induced attributes of
`Dataset` and `CoreDataset`, comparing induced range and cardinality. No hand-written field
list was used.

- Schema-identical shared slots: **76**
- Of those, present in both records: **66**; absent from both: **10**. Presence is
  identical for every one.
- Projected slots (shared name, differing range): **1** — `resources` (`Dataset` in full,
  `CoreDataset` in core). Absent from both records, so the projection is vacuous.
- Core-only slots: `distributions`, `dialect`. Full-only slots: `file_collections`,
  `total_file_count`, `total_size_bytes`, `subsets`, `splits`, `relationships`,
  `direct_collection`, `collection_notifications`, `collection_consents`,
  `consent_revocations`, `participant_privacy`, `participant_compensation`,
  `third_party_sharing`, `variables`, `citation`, `parent_datasets`, `related_datasets`.

Every schema-identical shared slot has deeply identical parsed YAML content, including
nested mapping values and list order. Core was generated by copying those values from the
audited full record without paraphrase, condensation, reordering, or omission; no narrative
field was shortened for core.

### Related-content mapping and semantic review

`file_collections` (full) ↔ `distributions` (core), 9 pairs, matched by `id`, reviewed
field by field:

| Aspect | Full `FileCollection` | Core `CoreDistribution` | Finding |
|---|---|---|---|
| identity | `id`, `name` | `id`, `name` | identical for all 9 |
| path | `path` | `path` | identical for all 9 |
| size | `total_bytes` | `bytes` | equal for all 9 |
| file count | `file_count` | no core slot | preserved verbatim in the core `description` |
| description | narrative | same narrative + one appended count/size sentence | core is a superset; no conflicting claim |
| format | `conforms_to` (standard URI) | `format` / `media_type` (enums) | see below |
| compression | unset | unset | consistent |
| checksums | no slot | `hash`/`md5`/`sha256` unset | sources publish none |

`format` and `media_type` are set only for `clinical_data` (`CSV` / `text/csv`), the one
directory the README describes file-by-file as CSV. The remaining eight carry DICOM, WFDB,
Open mHealth, and NASA-ASCII payloads, none of which is a permissible value of `FormatEnum`
or `MediaTypeEnum`; the standards themselves are recorded in the full record's `conforms_to`
and in both records' narrative. Leaving them unset is a schema-vocabulary limit, not a
disagreement between the records.

Other related-content checks:

- **Totals vs distribution-level values.** `total_file_count` / `total_size_bytes` are
  full-only and cover the whole dataset; the distribution-level values cover the nine
  datatype directories. The 9-file / 419,614-byte gap is the root-level file set. Scopes
  differ, so the values are not comparable as equals and do not conflict.
- **Formats and access URLs.** `distribution_formats` is a schema-identical shared slot and
  is byte-identical in both, so declared media types (`application/dicom`, `text/markdown`,
  `text/csv`, `application/json`) and the four access URLs agree across the pair and with
  the `distributions` entries.
- **`dialect` / `is_tabular`.** `is_tabular: false` in both; `dialect` unset. Consistent.
- **Identity, version, and access.** Top-level identity and version facts agree with
  `version_access`, `distribution_dates`, and the repeated statements inside
  `license_and_use_terms`, `regulatory_restrictions`, and `is_deidentified` in both records.
  Historical releases are distinguished from the current release by explicit version
  labelling rather than treated as contradictions.

**Result: zero unresolved contradictions within or between the two records.**

### Commands run

```bash
poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_all.yaml \
  -C Dataset data/d4d_concatenated/claudecode_agent/2026-07-28_claude-opus-5-deprimed_rep2/AI_READI_d4d.yaml
poetry run linkml-term-validator validate-data \
  data/d4d_concatenated/claudecode_agent/2026-07-28_claude-opus-5-deprimed_rep2/AI_READI_d4d.yaml \
  --schema src/data_sheets_schema/schema/data_sheets_schema_all.yaml --target-class Dataset
poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml \
  -C CoreDataset data/d4d_concatenated/claudecode_agent_core/2026-07-28_claude-opus-5-deprimed_rep2/AI_READI_d4d_core.yaml
poetry run linkml-term-validator validate-data \
  data/d4d_concatenated/claudecode_agent_core/2026-07-28_claude-opus-5-deprimed_rep2/AI_READI_d4d_core.yaml \
  --schema src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml --target-class CoreDataset
poetry run python -m data_sheets_schema.d4d_pair_consistency \
  --full data/d4d_concatenated/claudecode_agent/2026-07-28_claude-opus-5-deprimed_rep2/AI_READI_d4d.yaml \
  --core data/d4d_concatenated/claudecode_agent_core/2026-07-28_claude-opus-5-deprimed_rep2/AI_READI_d4d_core.yaml
poetry run d4d provenance record --project AI_READI --method claudecode_agent \
  --label 2026-07-28_claude-opus-5-deprimed_rep2 \
  --input-bundle data/preprocessed/concatenated/AI_READI_preprocessed.txt
```

`--sync-core` was not needed: core was regenerated from the audited full record, so the
shared slots were already deeply identical when the validator first ran.

### Final results

| Check | Result |
|---|---|
| Full schema validation (`Dataset`) | No issues found |
| Full ontology term validation | Validation passed |
| Core schema validation (`CoreDataset`) | No issues found |
| Core ontology term validation | Validation passed |
| Pair consistency validator | PASS — 76 schema-identical slots; projected slots `['resources']` |
| Pair validator warnings | 1 — `file_collections` ↔ `distributions` semantic review required; performed above, 9/9 matched, 0 unmatched |
| Files changed | the two YAML records and this report only |

Informational size metadata (not a quality gate): full 2465 lines / 82 populated top-level
slots; core 1715 lines / 67 populated top-level slots.
