# AI_READI full/core reconciliation

- **Run label:** `2026-08-07_claude-opus-5-claudecode-generic-v3_rep1`
- **Arm:** BASELINE (input documents only)
- **Mode:** four-phase project agent, generic prompt
- **Agent runtime / provider / model / reasoning effort:** Claude Code / Anthropic / claude-opus-5 / high
- **Temperature:** 0.0
- **Prompt:** `src/download/prompts/d4d_generic_arm_prompt.md`
- **Declared input bundle:** `data/preprocessed/concatenated/AI_READI_preprocessed.txt`
- **Source manifest:** `data/preprocessed/source_manifest.yaml`
- **Full record:** `data/d4d_concatenated/claudecode_agent/2026-08-07_claude-opus-5-claudecode-generic-v3_rep1/AI_READI_d4d.yaml`
- **Core record:** `data/d4d_concatenated/claudecode_agent_core/2026-08-07_claude-opus-5-claudecode-generic-v3_rep1/AI_READI_d4d_core.yaml`

## Pinned referent

`Dataset` admits one referent. The bundle describes both an ongoing study and a series of
dataset releases, and this record is pinned to **the dataset release "Flagship Dataset of Type 2
Diabetes from the AI-READI Project", version 3.0.0, DOI 10.60775/fairhub.3**, released
2025-11-17.

That choice was made because v3.0.0 is the release the current sources describe substantively:
the FAIRhub API capture (`fairhub_dataset_v3_api`) carries the v3.0.0 healthsheet, README,
dataset description, study description and full directory inventory, while the v2.0.0 sources
retained in the manifest carry only the v2.0.0 identity, size and file count and are marked
upstream as no longer accessible. The alternatives considered and rejected were (a) the AI-READI
study or programme as a whole, which is the referent of the BMJ Open protocol, the NIH RePORTER
record and the IRB application but is not a dataset, and (b) the release series across v1.0.0 to
v3.0.0, which would have required merging figures the sources keep separate.

The choice is held consistently across both records: `id`, `doi`, `version`, `page`,
`created_on`, `total_file_count`, `total_size_bytes` and every `file_collections` /
`distributions` entry describe v3.0.0 only. Facts specific to v1.0.0 and v2.0.0 appear only
inside `version_access.versions_available`, `distribution_dates.release_dates`,
`updates.update_details` and (full record only) `related_datasets`, in every case with the
version they belong to named in the same sentence. Study-level facts that are not release-level
facts — enrollment target, IRB approval, recruitment scheme, consent, compensation — are carried
in the collection, ethics and human-subject slots, which is where the schema puts them.

## Phase 3 — source and provenance audit

### Provenance boundary

No prior full or core D4D record was read, opened, grepped or consulted, from any arm, label or
date. The only files opened during the run were:

- `.claude/agents/d4d-provenance-guard.md`, `.claude/commands/d4d-full-core.md`,
  `.claude/commands/d4d-agent.md`, `src/download/prompts/d4d_generic_arm_prompt.md`
- `data/preprocessed/concatenated/AI_READI_preprocessed.txt` (the declared bundle)
- `data/preprocessed/source_manifest.yaml`
- `src/data_sheets_schema/schema/data_sheets_schema_all.yaml` and
  `src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml`, read through LinkML
  `SchemaView` rather than as text, plus `src/data_sheets_schema/schema/D4D_Motivation.yaml`,
  `D4D_Ethics.yaml` and `D4D_Data_Governance.yaml` to resolve three slot definitions
- `src/data_sheets_schema/d4d_pair_consistency.py`, to understand the Phase 4 contract
- this run's own two output YAMLs

Nothing under `data/d4d_concatenated/` other than this run's own label directory was read, and
no `*_crate_d4d.yaml` or `*_crate_mapped_d4d.yaml` was read. No prior-D4D content from the
parent conversation was used. Every emitted slot and nested object was derived from the two
schemas through `SchemaView`; no `d4d:docExample` value was copied.

### Source disagreements represented rather than resolved

Each of these is recorded in both records in the `source_caveats` of the object it affects, with
both readings stated:

| # | Disagreement | Sources | Where represented |
|---|---|---|---|
| 1 | Organizational attribution: "Washington University in St. Louis" (ROR 01yc7t268) as lead sponsor, managing organization and affiliation of Aaron and Cecilia Lee, versus University of Washington as awardee, author affiliation, IRB of record and license Licensor | FAIRhub v3.0.0 metadata vs NIH RePORTER, Nature Metabolism, license agreement, IRB protocol | record-level `source_caveats`; both organizations listed in `creators[0].affiliations` with their evidenced roles in `description` |
| 2 | Enrollment target 4,000 vs 4,600 | BMJ Open, Nature Metabolism, FAIRhub `enrollmentCount`, NIH RePORTER vs UW IRB application | record-level `source_caveats`; `known_limitations` "Release does not yet reflect full enrollment or balance" |
| 3 | Study start date 18 July 2023 vs 2023-07-19 | BMJ Open vs FAIRhub study description and collection window | `collection_timeframes[1].source_caveats` |
| 4 | End of enrolment 30 November 2026 vs anticipated completion 2027-01-01 vs award end 2025-08-31 | BMJ Open vs FAIRhub vs NIH RePORTER | `collection_timeframes[1].source_caveats` |
| 5 | Acronym expansion "Equitable" vs "Exploratory" Atlas for Diabetes Insights | BMJ Open, Nature Metabolism vs NIH RePORTER, FAIRhub, README | top-level `description` and record-level `source_caveats` |
| 6 | License identity: AI-READI-LICENSE-v1.0 (Zenodo 10642459, full text in bundle) vs "AI-READI custom license v2.0" (Zenodo 17555036, text not in bundle) vs "Health Data License" (FAIRhub page label) | license PDF and Nature Metabolism vs FAIRhub v3.0.0 metadata and README vs FAIRhub HTML | `license_and_use_terms.source_caveats`; clause summary explicitly attributed to v1.0 |
| 7 | De-identification: active HIPAA Safe Harbor stripping of PHI vs "no identifiers were collected so no active de-identification was necessary" | Nature Metabolism vs FAIRhub `datasetDeIdentLevel` | `is_deidentified.source_caveats` and `preprocessing_strategies[2].source_caveats` |
| 8 | Sampling: stratified wave-based recruitment vs healthsheet "The dataset contains all possible instances" and sampling strategy "N/A" | BMJ Open and IRB protocol vs healthsheet Composition Q4 and Preprocessing Q5 | `sampling_strategies[0].source_caveats` |
| 9 | Demographic subpopulations: healthsheet answers "No" while the README reports per-group counts | healthsheet Demographic Q1 vs README suggested-split table | two separate `subpopulations` entries plus `source_caveats` on the second |
| 10 | Follow-up share 10% vs approximately 4% | NIH RePORTER and IRB protocol vs healthsheet | `known_limitations` "Cross-sectional design" `source_caveats` |
| 11 | Blood volume 53 mL vs approximately 50-60 mL | BMJ Open vs IRB protocol | `collection_mechanisms` "Biospecimen collection" `source_caveats` |
| 12 | STUDY00016228 described as a "Clinicaltrials.org approval number" in one place and as the UW IRB approval number in two others; ClinicalTrials.gov identifier is NCT06002048 | BMJ Open abstract vs BMJ Open methods and healthsheet vs FAIRhub | `ethical_reviews[0].source_caveats` |
| 13 | Travel costs "reasonable costs covered" vs "not reimbursed if transportation fees exceed $25" | IRB protocol section 4.4 vs section 11 | `participant_compensation.source_caveats` (full record only; the slot has no core counterpart) |
| 14 | v2.0.0 and v3.0.0 documentation both describe their release as containing "data from the participants of the pilot study phase", contradicting the participant counts and collection windows in the same sources | docs v2 and v3 vs healthsheet and README | `version_access.source_caveats`; the counts are recorded and the phrase is not |

### Corrections applied during the audit

Six defects were found in the Phase 1 record and corrected in the full record first; the core
record was then rebuilt from the corrected full record.

1. **Mis-scoped instance removed.** A second `instances` entry described biorepository specimen
   aliquots. Biospecimens are not records in this data release — the healthsheet states plainly
   that each instance represents an individual patient — so the entry asserted composition the
   release does not have. Removed. The biorepository content it carried is retained in
   `collection_mechanisms` ("Biospecimen collection and laboratory testing"), `raw_data_sources`
   and `known_limitations` ("Finite biorepository samples"), where it is correctly scoped as
   study activity rather than dataset content.
2. **Date error.** `updates.update_details` stated v1.0.0 was "released 5 May 2024"; the FAIRhub
   version list and the README table both give 3 May 2024 (5/3/2024). Corrected, and the README
   table's US-format dates are now quoted explicitly so the reading is checkable.
3. **Duplicate keyword.** `keywords` carried both "Retinal imaging" and "Retinal Imaging", a
   case-variant of the same term arising from the dataset subject list and the study keyword
   list. The duplicate was dropped.
4. **Slot-filling violation.** Two `creators[0].affiliations` entries used `notes` to carry
   narrative about each organization's role. `description` is the default home for narrative and
   `notes` is residual-only, so both were moved to `description`.
5. **Shape violation.** `raw_data_sources[2].raw_data_format` held the prose ".csv results from
   the NORC laboratory." in a slot whose range is a format name. Set to `CSV`; the laboratory
   attribution was already present in the same object's `source_description`.
6. **Commentary embedded in a name.** The top-level `description` opened with "Artificial
   Intelligence Ready and Equitable/Exploratory Atlas for Diabetes Insights", a slash-merge of
   two conflicting expansions inside what reads as the project's name. Rewritten to state both
   expansions and which sources give each.

### Deliberate omissions

Recorded here so that absence is legible as a decision rather than an oversight. In every case
the underlying evidence is carried in a slot that does fit.

- **`subsets`** — the bundle clearly describes two access tiers, a publicly accessible set and a
  controlled-access set, but supplies no identifier for either and `DataSubset` requires one.
  Inventing two identifiers would assert resolvable entities that do not exist. The two tiers are
  described in `sensitive_elements`, `license_and_use_terms`, `regulatory_restrictions`,
  `participant_privacy` and `third_party_sharing`.
- **`used_software`** — omitted everywhere. `Software` requires an identifier, and the bundle
  names REDCap, the MoCA Duo application, Dexcom Clarity and the OMOP Data Quality Dashboard
  without supplying URLs or identifiers for them. All four are named in the prose of the
  `collection_mechanisms` and `cleaning_strategies` entries that use them.
- **`issued`** — the sources give the availability date 2025-11-17 without a time, and the slot
  requires a datetime. Rather than fabricate a time component, `created_on` was set to
  `2025-11-17T08:00:00Z`, transcribed exactly from the FAIRhub API integer field
  `"created_at": 1763366400`, and the availability date is carried in
  `distribution_dates.release_dates` and `version_access.versions_available`.
- **`variables`** — the IRB protocol refers to an uploaded list of variables that is not part of
  the captured document, and no source supplies a variable-level dictionary.
- **`errata`, `imputation_protocols`, `annotation_analyses`, `machine_annotation_tools`** — the
  healthsheet's erratum question is unanswered and its labeling questions all answer "N/A - no
  labels are provided"; no imputation, inter-annotator analysis or automated annotation tooling
  is described anywhere in the bundle.
- **`status`, `download_url`, `last_updated_on`, `modified_by`, `was_derived_from`,
  `compression`, `conforms_to_class`, `conforms_to_schema`** — no evidence.
- **`file_collections[9].total_bytes`** — the FAIRhub structure description reports no size for
  the nine root metadata files. It could have been derived by subtracting the nine datatype
  directories from the dataset total, but that would present a computed residual as a reported
  figure, so it was left unset and the arithmetic is recorded in this report instead.

### Constructed identifiers

`FileCollection` requires an `id` that the sources do not supply. The ten collection identifiers
were constructed mechanically as the dataset DOI URL plus the documented directory name as a
fragment, for example `https://doi.org/10.60775/fairhub.3#cardiac_ecg`. They assert nothing
beyond the directory names already recorded in `path`, and the same identifiers were carried
into the core `distributions` so that the two records match on `id`. This is stated in the
record-level `source_caveats` of both files.

### Internal consistency checks

All arithmetic in both records was checked against the sources and against itself:

- Participant totals: 2,280 in `description`, `instances[0].counts`, `subpopulations[1]` and
  `splits`. The `subpopulations` breakdowns each sum to 2,280 (race/ethnicity 380+545+519+836;
  sex 951+1,329; diabetes status 776+560+686+258).
- Split table: 1,576 + 352 + 352 = 2,280; each of the nine per-cell breakdowns in `splits` sums
  correctly both across the split and across the category, and the per-category totals match
  `subpopulations[1].distribution` exactly.
- Version counts: v2.0.0 total 1,067 = v1.0.0 204 + 863 added, as the healthsheet states.
- File counts: the nine datatype directories sum to 356,334 files; with the nine root metadata
  files this is 356,343, exactly the declared `total_file_count` and the README figure.
- Sizes: the nine datatype directories sum to 3,815,969,360,064 bytes against a declared
  `total_size_bytes` of 3,815,969,779,678, leaving 419,614 bytes for the nine unsized root
  metadata files — a small positive residual, consistent.
- Identifiers, versions, dates, license references and organization names were checked for
  internal agreement across every slot in each file; no internal contradiction remains.

### Post-correction validation (Phase 3)

```bash
poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_all.yaml \
  -C Dataset data/d4d_concatenated/claudecode_agent/2026-08-07_claude-opus-5-claudecode-generic-v3_rep1/AI_READI_d4d.yaml
# No issues found

poetry run linkml-term-validator validate-data \
  data/d4d_concatenated/claudecode_agent/2026-08-07_claude-opus-5-claudecode-generic-v3_rep1/AI_READI_d4d.yaml \
  --schema src/data_sheets_schema/schema/data_sheets_schema_all.yaml --target-class Dataset
# Validation passed

poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml \
  -C CoreDataset data/d4d_concatenated/claudecode_agent_core/2026-08-07_claude-opus-5-claudecode-generic-v3_rep1/AI_READI_d4d_core.yaml
# No issues found

poetry run linkml-term-validator validate-data \
  data/d4d_concatenated/claudecode_agent_core/2026-08-07_claude-opus-5-claudecode-generic-v3_rep1/AI_READI_d4d_core.yaml \
  --schema src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml --target-class CoreDataset
# Validation passed
```

## Phase 4 — strict full/core reconciliation

### Schema-derived shared slots

The shared slot set was derived at runtime from `Dataset` and `CoreDataset` with LinkML
`SchemaView` by `data_sheets_schema.d4d_pair_consistency`; no hand-written field list was used.

- **Schema-identical slots (same induced range and cardinality): 78.**
- **Projected slots: 1** — `resources`, which is `Dataset` in the full schema and `CoreDataset`
  in the core schema. Neither record populates it, so the projection is vacuously satisfied and
  the presence check passes.
- **Populated in both records: 64.** Every one has a deeply identical parsed YAML value,
  including every nested mapping value and list item in the same order. This includes all the
  narrative slots: no shared content was condensed, paraphrased, reordered or omitted in core.
- **Present in one record only: 0 of the schema-identical slots.** The 14 slots that differ in
  presence are all slots the two schemas do not share.

### Full-only and core-only slots

Thirteen slots are populated in the full record and have no counterpart in `CoreDataset`, so
their absence from core is a schema fact rather than a divergence:

`total_file_count`, `total_size_bytes`, `file_collections`, `relationships`, `splits`,
`direct_collection`, `collection_notifications`, `collection_consents`, `consent_revocations`,
`participant_privacy`, `participant_compensation`, `third_party_sharing`, `related_datasets`.

One slot is populated in the core record only: `distributions`, which is core-only in the schema
and is the projection of the full record's `file_collections` (see below). Core's other
core-only slot, `dialect` (`FormatDialect`), is unpopulated: the bundle documents the standards
each datatype follows but gives no delimiter, header, quote character, comment prefix or
double-quote convention, so there is nothing to fill it with. Leaving it empty creates no
conflict with the full record's `conforms_to`, which records a directory-organisation standard
rather than a tabular dialect.

### Related-content mapping and semantic review

**`file_collections` (full) → `distributions` (core).** All ten collections matched their
distribution deterministically, on `id`, with `path` and `name` agreeing as well; the validator
reports `deterministic matches=10, unmatched core distributions=[]`. Field by field:

| Full `FileCollection` field | Core `CoreDistribution` counterpart | Outcome |
|---|---|---|
| `id`, `name`, `description`, `path` | same slot names | carried across unchanged; deeply identical |
| `total_bytes` | `bytes` | carried across unchanged for the nine sized collections; the validator's dedicated `total_bytes`/`bytes` check passes |
| `source_caveats` | `source_caveats` | carried across unchanged (root metadata collection only) |
| `file_count` | *no counterpart* | full-only; omitted from the projection |
| `collection_type` (`FileCollectionTypeEnum`) | *no counterpart* | full-only; omitted from the projection |
| `conforms_to` (standard name, e.g. "Digital Imaging and Communications in Medicine (DICOM)") | `format` is restricted to `FormatEnum` | **not projected.** `FormatEnum` admits only CSV, TSV, XML, JSON, JSONL, YAML, HTML, PDF, DOCX, XLSX, PPTX, TXT, MD, ZIP, TAR, GZ, BZ2 and XZ; none of DICOM, WFDB, OMOP CDM, Open mHealth or ESDS is a member. Forcing a member value would have asserted a format the sources do not state. Core is therefore silent on format rather than contradictory, and the same standards are carried in core's `distribution_formats`, which is a shared identical slot. |
| `compression` | `compression` | neither populated in any collection; the sources describe no packaged archive. No conflict. |
| — | `encoding`, `media_type`, `hash`, `md5`, `sha256` | no evidence in the bundle; unpopulated in core. The bundle publishes no checksums for the AI-READI release. |

**Counts and sizes across representations.** `total_file_count` (356,343) and `total_size_bytes`
(3,815,969,779,678) exist only in the full record. Both reconcile with the distribution-level
values at the same scope: the ten collections' `file_count` values sum to exactly 356,343, and
the nine sized collections' `total_bytes` sum to 3,815,969,360,064, 419,614 bytes short of the
declared total, which is attributable to the nine root metadata files whose size the source does
not report. No conflict.

**`dialect`, formats and `is_tabular`.** `is_tabular` is `false` in both records (a
schema-identical slot, deeply identical). This agrees with the rest of both records: the
healthsheet states the release encompasses tabular, imaging and physiological signal or waveform
data, and seven of the ten collections are imaging or waveform. `distribution_formats` is
identical in both and names the same standards as the full record's per-collection `conforms_to`
values, with no contradiction between them. `dialect` is unpopulated, as noted above.

**Top-level identity, version and access facts against version history and distributions.**
`id`, `doi`, `version`, `page`, `publisher`, `license`, `created_by`, `created_on`, `language`,
`conforms_to` and `keywords` are schema-identical and deeply identical across the pair. Each
agrees with the version history and the distribution content: `doi` 10.60775/fairhub.3 equals
`version_access.latest_version_doi` and the DOI prefix of every collection and distribution
`id`; `version` "3.0.0" matches the first entry of `version_access.versions_available` and the
last date in `distribution_dates.release_dates`; `license` names the same v2.0 license and DOI
that `license_and_use_terms.license_terms` records, with the same v1.0/v2.0 caveat attached in
both records; `page` and `publisher` agree with the FAIRhub access description in
`distribution_formats[0].access_urls`.

**Historical versus current release.** v1.0.0 and v2.0.0 figures — 204 and 1,067 participants,
2.01 TB, 165,051 files, DOIs 10.60775/fairhub.1 and .2, release dates 2024-05-03 and 2024-11-08
— appear only where their version is named in the same sentence, in
`version_access.versions_available`, `updates.update_details`,
`distribution_dates.description` and (full record only) `related_datasets`. They are therefore
historical scope statements, not contradictions of the v3.0.0 figures. The core record loses the
two typed `is_new_version_of` relationships because `related_datasets` is full-only; the same
version history remains available to core through `version_access`, which is identical in both.

**Zero unresolved contradictions** remain within either record or between the two.

### Phase 4 commands and results

`--sync-core` was not needed. The core record was built in Phase 2 by projecting the
schema-derived `CoreDataset` slot set out of the validated Phase 1 full record, so every shared
slot was byte-identical from the outset; after the Phase 3 corrections the core record was
rebuilt the same way from the corrected full record. The validator was then run once, without
`--sync-core`, as an independent check:

```bash
poetry run python -m data_sheets_schema.d4d_pair_consistency \
  --full data/d4d_concatenated/claudecode_agent/2026-08-07_claude-opus-5-claudecode-generic-v3_rep1/AI_READI_d4d.yaml \
  --core data/d4d_concatenated/claudecode_agent_core/2026-08-07_claude-opus-5-claudecode-generic-v3_rep1/AI_READI_d4d_core.yaml
# PASS: 78 schema-identical slots; projected slots=['resources']
# WARNING [semantic-review-required] $.file_collections <-> $.distributions:
#   deterministic matches=10, unmatched core distributions=[]
```

The single warning is the validator's standing instruction that related distribution content
requires human-equivalent semantic review; that review is the "Related-content mapping and
semantic review" section above, and it found no conflict.

### Files changed

- `data/d4d_concatenated/claudecode_agent/2026-08-07_claude-opus-5-claudecode-generic-v3_rep1/AI_READI_d4d.yaml`
  — created in Phase 1, corrected in Phase 3 (six corrections listed above).
- `data/d4d_concatenated/claudecode_agent_core/2026-08-07_claude-opus-5-claudecode-generic-v3_rep1/AI_READI_d4d_core.yaml`
  — created in Phase 2, rebuilt in Phase 3 from the corrected full record, Phase 4 header line
  added.
- `data/d4d_concatenated/claudecode_agent_core/2026-08-07_claude-opus-5-claudecode-generic-v3_rep1/AI_READI_reconciliation.md`
  — this report.

No file outside these three was written.

## Outcome

| Measure | Value |
|---|---|
| Full record top-level slots populated | 77 |
| Core record top-level slots populated | 65 |
| Schema-identical shared slots (derived from `SchemaView`) | 78 |
| Shared slots populated in both records | 64 |
| Shared slots with differing parsed value | 0 |
| Shared slots present in one record only | 0 |
| Projected slots | 1 (`resources`, absent from both) |
| Related-content pairs reviewed | 10 of 10 `file_collections` ↔ `distributions` |
| Full schema validation | pass (both records) |
| Ontology term validation | pass (both records) |
| Pair consistency | PASS, 1 standing semantic-review warning, addressed above |
| Phase 3 corrections applied | 6 |
| Source disagreements represented rather than resolved | 14 |
| Unresolved contradictions | 0 |
