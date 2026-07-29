# AI_READI full/core reconciliation — 2026-07-28_claude-opus-5-generic_rep1

**Arm:** BASELINE (input documents only)
**Method:** claudecode_agent
**Runtime / provider / model:** Claude Code / Anthropic / claude-opus-5[1m]
**Mode:** four-phase project agent, generic prompt
**Prompt:** `src/download/prompts/d4d_generic_arm_prompt.md` (identical for all projects)

## Files

| Role | Path |
|---|---|
| Full | `data/d4d_concatenated/claudecode_agent/2026-07-28_claude-opus-5-generic_rep1/AI_READI_d4d.yaml` |
| Core | `data/d4d_concatenated/claudecode_agent_core/2026-07-28_claude-opus-5-generic_rep1/AI_READI_d4d_core.yaml` |
| Provenance | `data/d4d_concatenated/claudecode_agent_core/2026-07-28_claude-opus-5-generic_rep1/AI_READI_provenance.yaml` |

## Declared inputs

- Source bundle: `data/preprocessed/concatenated/AI_READI_preprocessed.txt` (10 documents, 6229 lines)
- Source manifest: `data/preprocessed/source_manifest.yaml`
- Full schema: `src/data_sheets_schema/schema/data_sheets_schema_all.yaml`, class `Dataset`
- Core schema: `src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml`, class `CoreDataset`

## Pinned referent

`Dataset` admits one referent. The referent chosen is **the FAIRhub-published
"Flagship Dataset of Type 2 Diabetes from the AI-READI Project", with version
3.0.0 (DOI 10.60775/fairhub.3) as the current release**. The bundle supports this
choice most directly: the FAIRhub API capture, the FAIRhub landing pages and the
documentation site all describe a released, versioned, DOI-bearing dataset, and
the two publications and the IRB protocol describe the study that produced it.

Consequences held consistently across both records:

- Study-level facts (protocol, recruitment, IRB, consent, compensation) are
  recorded as *collection* properties of this dataset, not as a separate study
  referent.
- Versions 1.0.0 and 2.0.0 are represented as `related_datasets`
  (`is_new_version_of`) and in `version_access`, not as the referent.
- The FAIRhub "Mini Version" (record 4) is represented as a `has_part` relation,
  explicitly attributed to the manifest note, since it was not captured in the
  bundle.
- The `id` is the version 3.0.0 DOI, and `version`, `doi`, `page`, `publisher`
  and `total_*` all describe version 3.0.0.

## Phase 3 — source and provenance audit

### Provenance

- No prior generated D4D record was read. Reads were limited to: the declared
  bundle, the source manifest, the two schema files (dumped via `SchemaView`
  rather than read as YAML), the arm prompt, `.claude/commands/d4d-full-core.md`,
  `.claude/commands/d4d-agent.md`, `.claude/agents/d4d-provenance-guard.md`, and
  the same-run Phase 1 full record during Phase 2.
- `data/d4d_concatenated/` was inspected only to confirm the run label was unused.
  No prior record's contents were opened.
- Both headers state `Prior D4D factual reuse: prohibited`; the core header names
  both its document bundle and the exact same-run full record path.

### Source disagreements — represented, not merged

The bundle contains four substantive disagreements. In each case both readings
are carried with their scope stated, rather than one being silently selected.

1. **Lead institution of the responsible party.** The FAIRhub study metadata
   records Aaron Lee's affiliation, the lead sponsor and the managing
   organization as *Washington University in St. Louis* (ROR 01yc7t268). NIH
   RePORTER records the awardee organization for OT2OD032644 as *University of
   Washington*, and both publications give University of Washington affiliations
   for Aaron Lee and Cecilia Lee. Recorded in
   `creators[aireadi:creator_responsible_party]`, which names both and states
   that the sources disagree; both organizations appear in `affiliations` with
   the provenance of each.
2. **Target enrolment: 4000 vs 4600.** The study design publication, the Nature
   Metabolism comment, the FAIRhub `enrollmentInfo` and NIH RePORTER all give
   4000 (RePORTER: "4,000+"); the IRB protocol application gives 4600. Recorded
   in `known_limitations[aireadi:limitation_enrollment_ongoing]` with both
   figures attributed to their sources.
3. **Follow-up subgroup: 4% vs 10%.** The healthsheet states approximately 4% of
   participants are expected to undergo a year-4 follow-up; the protocol
   publication, the Nature Metabolism comment, NIH RePORTER and the IRB protocol
   state 10%. Both recorded in
   `collection_timeframes[aireadi:timeframe_study_overall]`.
4. **De-identification characterisation.** The Nature Metabolism comment states
   the public set is stripped of PHI via the HIPAA Safe Harbor method; the
   FAIRhub `datasetDeIdentLevel` records `NoDeIdentification` with the note that
   no identifiers were collected so no active de-identification was necessary,
   only a check that no HIPAA-identifiable data were present. Both are carried
   verbatim in `is_deidentified.method` and
   `participant_privacy[...].anonymization_method`, flagged as standing side by
   side.

Two further apparent conflicts were resolved as **scope differences, not
contradictions**, and are recorded as such:

- 2.01 TB / 165,051 files (v2.0.0) versus 3.82 TB / 356,343 files (v3.0.0) are
  different releases; only the v3.0.0 figures appear in `total_size_bytes` and
  `total_file_count`, with the v2.0.0 figures confined to `version_access` and
  `related_datasets`.
- The healthsheet answers "No" to identifying demographic sub-populations, while
  the README publishes a split table with race/ethnicity, sex and diabetes-status
  counts. This is a public-release-versus-controlled-release distinction. Both
  are recorded: the counts under
  `subpopulations[race_ethnicity|sex|diabetes_status]`, and the healthsheet's own
  answer under `subpopulations[aireadi:subpopulation_healthsheet_statement]` with
  its context.

### Corrections applied to the full record during Phase 3

Six assertions in the Phase 1 draft outran the evidence and were removed or
narrowed. The full record was corrected first, then core was regenerated from it.

| # | Slot | Correction |
|---|---|---|
| 1 | `ethical_reviews[0].contact_person` | Removed. The bundle names a central study contact (Aaron Lee, contact@aireadi.org) but never designates a contact for ethical-review questions. `reviewing_organization` (University of Washington) is explicit and was kept. |
| 2 | `license_and_use_terms.contact_person` | Removed. No licensing contact person is named; the licence directs users to docs.aireadi.org. |
| 3 | `regulatory_restrictions.governance_committee_contact` | Removed. No data-governance-committee contact person is named. |
| 4 | `human_subject_research.ethics_review_board` | Removed the UCSD Health Data Oversight Committee entry — mis-scoped, as HDOC oversees data sharing with other institutions, not ethics review. The statement is retained in `ethical_reviews[...].review_details` where it belongs. |
| 5 | `variables[MoCA].minimum_value` | Removed the value `0.0`. The bundle states the maximum score is 30; a floor of 0 is not stated. `maximum_value: 30.0` kept. |
| 6 | `related_datasets[mini].target_dataset` | Changed from a constructed URL `https://fairhub.io/datasets/4` to `10.60775/fairhub.4`, the identifier actually present in the manifest note. |

One further change was editorial rather than factual: the `SamplingStrategy`
object nested under `instances[...].sampling_strategies` was given the same `id`
and wording as the top-level `aireadi:sampling_released_dataset_completeness`
object, so that it reads as a reference to the same assertion rather than a
near-duplicate.

The `issued` slot was left unpopulated. The release date (2025-11-17) is stated
in the bundle as a date, but the slot's range is `datetime`; encoding it would
have required inventing a time of day. The date is carried losslessly in
`distribution_dates.release_dates`, `version_access.versions_available` and the
dataset `description`.

No Phase 2 discovery required back-porting into the full record: core was derived
by copying schema-identical slots from the audited full record, and the only
core-original content is the `distributions` projection described below.

### Internal consistency checks

Repeated identifiers, counts and dates were checked for internal agreement within
each file:

- DOI `10.60775/fairhub.3` appears in `id`, `doi`, `version_access.latest_version_doi`
  and `distribution_formats.access_urls` — consistent.
- `version: 3.0.0` agrees with `version_access`, `related_datasets` and the
  description.
- Participant counts are consistent: 204 (v1.0.0) + 863 (year 2) + 1213 (year 3)
  = 2280 (v3.0.0); v2.0.0 total 1067 = 204 + 863. The split totals
  1576 + 352 + 352 = 2280, and each split's race/ethnicity, sex and
  diabetes-status breakdowns sum to its own total.
- `total_file_count: 356343` and `total_size_bytes: 3815969779678` agree with the
  narrative "356,343 files ... around 3.82 TB" and with the core whole-dataset
  distribution.
- Collection window 2023-07-19 to 2025-05-01 agrees between
  `collection_timeframes`, the description and the dataset metadata.

## Phase 4 — strict full/core reconciliation

Shared slots were derived at runtime from `Dataset` and `CoreDataset` with LinkML
`SchemaView`; no hand-written field list was used.

- **Schema-identical shared slots: 76.** Every one is present in both records or
  absent from both, with deeply identical parsed YAML content. This holds by
  construction: the core builder copies these slots verbatim from the audited
  full record, including narrative fields, which are not condensed, paraphrased
  or reordered.
- **Full-only slots (17):** `citation`, `collection_consents`,
  `collection_notifications`, `consent_revocations`, `direct_collection`,
  `file_collections`, `parent_datasets`, `participant_compensation`,
  `participant_privacy`, `related_datasets`, `relationships`, `splits`,
  `subsets`, `third_party_sharing`, `total_file_count`, `total_size_bytes`,
  `variables`. These have no `CoreDataset` counterpart and are correctly absent
  from core.
- **Core-only slots (2):** `distributions`, `dialect`.
- **Projected slot:** `resources` (`Dataset` in full, `CoreDataset` in core).
  Absent from both records, so coverage is trivially equal.

### Related-content semantic review: `file_collections` → `distributions`

The validator reported 10 deterministic matches and one unmatched core
distribution. That distribution is intentional and was reviewed manually:

- The 10 matched entries preserve name and description verbatim from
  `file_collections`. Full-only nested slots (`conforms_to`, `collection_type`)
  are omitted from the core projection, as required.
- `media_type` was set only where the bundle states a format: `text/csv` for
  `clinical_data` ("Each CSV file in this directory is a one-to-one mapping to
  the OMOP CDM tables") and for `environment` (the protocol publication records
  the environmental sensor data format as `.csv`). The DICOM, WFDB and Open
  mHealth collections have no representable value in `FormatEnum` or
  `MediaTypeEnum` and were left unset rather than approximated.
- The unmatched entry, `aireadi:distribution_dataset_v3`, is the whole-release
  distribution. It exists because `CoreDataset` has no `total_file_count` or
  `total_size_bytes`; without it those two facts would be lost in the exchange
  layer. Its `bytes` value is copied from the full record's `total_size_bytes`
  (3815969779678) and its description restates the file count (356,343),
  matching `total_file_count` exactly. Its `path`
  (`https://fairhub.io/datasets/3`) matches the full record's `page` and one of
  `distribution_formats.access_urls`.
- Checked for conflicts and found none: no compression is asserted anywhere in
  either record; no checksums or byte counts are asserted at collection level in
  full, so none could conflict with the core distribution; `is_tabular: false` is
  identical in both and is consistent with a mixed DICOM/CSV/WFDB/mHealth
  distribution set; both records scope every distribution statement to release
  3.0.0.
- `dialect` was left unset. The dataset includes CSV and TSV files, but the
  bundle states no delimiter, header, quote or comment-prefix conventions, so
  every `FormatDialect` slot would have been a guess.

Top-level identity, version and access facts were compared against
`version_access`, `distribution_dates`, `distribution_formats` and the repeated
statements in `license_and_use_terms` and `regulatory_restrictions`. No
contradiction was found. Historical releases (1.0.0, 2.0.0) are consistently
marked as historical and are never presented as competing values for the current
release.

## Commands run

```bash
poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_all.yaml \
  -C Dataset data/d4d_concatenated/claudecode_agent/2026-07-28_claude-opus-5-generic_rep1/AI_READI_d4d.yaml

poetry run linkml-term-validator validate-data \
  data/d4d_concatenated/claudecode_agent/2026-07-28_claude-opus-5-generic_rep1/AI_READI_d4d.yaml \
  --schema src/data_sheets_schema/schema/data_sheets_schema_all.yaml --target-class Dataset

poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml \
  -C CoreDataset data/d4d_concatenated/claudecode_agent_core/2026-07-28_claude-opus-5-generic_rep1/AI_READI_d4d_core.yaml

poetry run linkml-term-validator validate-data \
  data/d4d_concatenated/claudecode_agent_core/2026-07-28_claude-opus-5-generic_rep1/AI_READI_d4d_core.yaml \
  --schema src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml --target-class CoreDataset

poetry run python -m data_sheets_schema.d4d_pair_consistency \
  --full data/d4d_concatenated/claudecode_agent/2026-07-28_claude-opus-5-generic_rep1/AI_READI_d4d.yaml \
  --core data/d4d_concatenated/claudecode_agent_core/2026-07-28_claude-opus-5-generic_rep1/AI_READI_d4d_core.yaml

poetry run d4d provenance record --project AI_READI --method claudecode_agent \
  --label 2026-07-28_claude-opus-5-generic_rep1 \
  --input-bundle data/preprocessed/concatenated/AI_READI_preprocessed.txt
```

`--sync-core` was not needed and was not run: core is generated from the audited
full record, so the schema-identical slots were already in sync when the
validator first ran.

## Results

| Check | Result |
|---|---|
| Full schema validation (`Dataset`) | No issues found |
| Full ontology term validation | Passed |
| Core schema validation (`CoreDataset`) | No issues found |
| Core ontology term validation | Passed |
| Schema-derived pair consistency | PASS — 76 schema-identical slots; projected slots `['resources']` |
| Related-content semantic review | Completed; 10 matched + 1 intentional whole-release distribution; zero contradictions |
| Provenance record | Written, `record_mode: live` |

Top-level slot counts (informational metadata, not a quality gate): full 79,
core 64.
