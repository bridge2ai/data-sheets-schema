# CHORUS full/core reconciliation — 2026-07-28_claude-opus-5-generic_rep1

- **Arm**: BASELINE (input documents only)
- **Prompt**: `src/download/prompts/d4d_generic_arm_prompt.md` (identical text for all projects)
- **Runtime / provider / model**: Claude Code / Anthropic / `claude-opus-5[1m]`
- **Mode**: four-phase project agent, generic prompt
- **Declared input bundle**: `data/preprocessed/concatenated/CHORUS_preprocessed.txt`
- **Manifest**: `data/preprocessed/source_manifest.yaml`
- **Full**: `data/d4d_concatenated/claudecode_agent/2026-07-28_claude-opus-5-generic_rep1/CHORUS_d4d.yaml`
- **Core**: `data/d4d_concatenated/claudecode_agent_core/2026-07-28_claude-opus-5-generic_rep1/CHORUS_d4d_core.yaml`

## Referent selection

`Dataset` admits one referent. The referent chosen is **the CHoRUS dataset** — the
multi-center, multi-modal critical care dataset assembled by the CHoRUS data generation
project — not the CHoRUS project/network as an organization, not the chorus-ai GitHub
software organization, and not the AIM-AHEAD Bridge2AI for Clinical Care Training
Program. Both records hold to this referent.

Consequences of that choice, applied consistently:

- The chorus-ai GitHub repositories are recorded as `external_resources.used_software`
  and inside preprocessing/annotation-tool slots, not as the dataset itself.
- Training-program facts (trainee stipend of $8,000, citizenship and education
  eligibility, application deadlines, mentorship) are **not** recorded as dataset
  properties. `participant_compensation` is deliberately absent: the stipend is paid to
  trainees, not to the human subjects whose clinical records constitute the data. The
  program appears only in `existing_uses` (it is a documented use of the data) and in
  `license_and_use_terms` / `intended_uses.usage_notes` (the registration, licensing
  agreement and `.edu` email requirements are stated in the source as conditions of
  dataset access).

## Phase 3 — source and provenance audit

### Provenance

- Factual inputs used: the declared bundle and
  `data/preprocessed/source_manifest.yaml` only.
- Structural inputs used: `data_sheets_schema_all.yaml` (class `Dataset`) and
  `data_sheets_schema_core_all.yaml` (classes `CoreDataset`, `CoreDistribution`),
  resolved with LinkML `SchemaView` rather than by imitating any existing record.
- No prior D4D record from any arm, label or date was read, opened, grepped or cited.
  Nothing under `data/d4d_concatenated/` other than this run's own two output paths was
  accessed, and no `*_crate_d4d.yaml` / `*_crate_mapped_d4d.yaml` was accessed.
- No live web content was fetched.
- The manifest declares four CHORUS sources, all four present in the bundle:
  `nih_reporter_project`, `cohort_2_webinar`, `project_documentation`, and
  `github_organization_overview` (a manifest-selected historical supplement captured
  2025-11-14, therefore an allowed source).

### Source disagreements — represented, not merged

1. **Admission count.** The project website reports a "Current Released Dataset" of
   **50,000** patient admissions (ICU, PICU, NICU). The Cohort 2 informational webinar
   (2025-09-09) reports **over 45,000** unique admissions across 14 hospitals **as of
   August 2025**. Both figures are stated, with their sources and reporting dates, in
   `instances[chorus_instance_patient_admission].description` and in
   `version_access.version_details`. `Instance.counts` is scalar; it carries the website
   release figure (50000) and the description states explicitly that the webinar figure
   differs and that the two are not reconciled into one number.
2. **Target size.** The website gives an "Anticipated Final Dataset" of **100,000**
   patient admissions; the NIH RePORTER abstract speaks of "more than 100,000 critically
   ill patients". Both are recorded, and the released-versus-anticipated distinction is
   carried in `known_limitations`, `updates` and `version_access` rather than collapsed
   into a single current size.
3. **Hospital / institution counts.** No disagreement: 14 data contributing hospitals
   and 20 institutions are consistent across the website, the webinar and the GitHub
   overview ("20 academic centers, of which 14 will contribute as Data Acquisition
   centers"). 60+ consortium members comes from the website only and is attributed there.

### Scoping decisions made from the sources

- **License.** The top-level `license` slot is left **unset**. The MIT statement belongs
  to the chorus-ai GitHub organization README and describes the software project;
  individual repositories carry their own licenses (MIT for `chorus_waveform`,
  `chorus-extract-upload`, `UF-Geocoding`; Apache-2.0 for `Chorus_SOP`). The bundle
  states no license identifier for the data. This scoping is written out in
  `license_and_use_terms.license_terms`, so the MIT fact is preserved without being
  asserted of the dataset.
- **Dates.** 2022-09-01 and 2026-11-30 are the NIH project period, not a data-collection
  window. They appear in `funders[…].grants[…].description` and in
  `collection_timeframes.timeframe_details` labelled as the project period;
  `CollectionTimeframe.start_date` / `end_date` are deliberately left empty because the
  clinical period covered by the retrospective records is not stated anywhere in the
  bundle.
- **HIPAA.** Not asserted. HIPAA appears in the bundle only as a topic of a training
  workshop ("HIPAA/GDPR compliance for OMOP/FHIR data"), which is not a compliance
  determination for the dataset. `regulatory_restrictions.hipaa_compliant` is absent;
  `confidentiality_level: restricted` is set from the uniform "Controlled" access-control
  column of the webinar data-standards table.
- **IRB.** Not asserted. No IRB approval, review board name, or consent process for the
  data subjects appears in the bundle. `human_subject_research.irb_approval` and
  `ethics_review_board` are absent, and `informed_consent`, `collection_consents`,
  `collection_notifications` and `consent_revocations` are omitted entirely.
- **Verbatim source defects preserved.** The website contact email is recorded as
  `cmccrary@mgh.havard.edu` with a note that this is as printed in the source (the
  domain is misspelled there). The website banner "This repoitory is under review for
  potential modification in compliance with Administration directives." is quoted as
  printed inside `status`. `www.bridge2ai.org/chorus` is recorded without a scheme
  because the source prints it that way.
- **Ontology-valued slots.** `Instance.data_topic` and `Instance.data_substrate`
  (`values_from: B2AI_TOPIC`, range `uriorcurie`) and `VariableMetadata.unit` are left
  empty: the bundle supplies no ontology identifiers, and guessing one would be
  inference.

### Omitted for lack of evidence

`anomalies`, `content_warnings`, `imputation_protocols`, `annotation_analyses`,
`discouraged_uses`, `prohibited_uses`, `ip_restrictions`, `errata`, `retention_limit`,
`use_repository`, `variables`, `parent_datasets`, `related_datasets`, `citation`, `doi`,
`version`, `download_url`, `issued`, `created_on`, `language`, `publisher`,
`total_file_count`, `total_size_bytes`, `compression`. In each case the bundle says
nothing, and an absent slot is the correct answer.

`total_size_bytes` deserves a note: the website's "23 Tb" is waveform data only, not a
dataset total, so it is recorded on the waveform instance rather than promoted to a
dataset-level size.

### Phase 2 discoveries requiring back-port to full

**None.** Core is the semantic-exchange subset of `CoreDataset`; every core field that
the sources support was already populated in the Phase 1 full record. No source-supported
fact was found during core derivation that the full record lacked, so no correction was
applied to the full record and no re-validation cycle was needed.

### Validation after Phase 3

```bash
poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_all.yaml -C Dataset data/d4d_concatenated/claudecode_agent/2026-07-28_claude-opus-5-generic_rep1/CHORUS_d4d.yaml
poetry run linkml-term-validator validate-data data/d4d_concatenated/claudecode_agent/2026-07-28_claude-opus-5-generic_rep1/CHORUS_d4d.yaml \
  --schema src/data_sheets_schema/schema/data_sheets_schema_all.yaml --target-class Dataset
poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml -C CoreDataset data/d4d_concatenated/claudecode_agent_core/2026-07-28_claude-opus-5-generic_rep1/CHORUS_d4d_core.yaml
poetry run linkml-term-validator validate-data data/d4d_concatenated/claudecode_agent_core/2026-07-28_claude-opus-5-generic_rep1/CHORUS_d4d_core.yaml \
  --schema src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml --target-class CoreDataset
```

All four passed. One correction was required during Phase 1 before the record validated:
`MissingDataDocumentation.missing_data_causes` is multivalued and had been written as a
scalar; it was converted to a list. No factual content changed.

## Phase 4 — strict full/core reconciliation

### Shared-slot derivation

The shared slot set was derived at run time with LinkML `SchemaView` from `Dataset` and
`CoreDataset`; no hand-written field list was used. Core was built by projecting the
Phase 1 full record through the `CoreDataset` induced-attribute inventory, so
schema-identical slots are copies rather than re-drafts. No narrative field was
condensed, paraphrased, reordered or dropped in core.

### Deterministic result

```bash
poetry run python -m data_sheets_schema.d4d_pair_consistency \
  --full data/d4d_concatenated/claudecode_agent/2026-07-28_claude-opus-5-generic_rep1/CHORUS_d4d.yaml \
  --core data/d4d_concatenated/claudecode_agent_core/2026-07-28_claude-opus-5-generic_rep1/CHORUS_d4d_core.yaml
```

```
PASS: 76 schema-identical slots; projected slots=['resources']
WARNING [semantic-review-required] $.file_collections <-> $.distributions: Phase 4 must
semantically review related distribution content; deterministic matches=9,
unmatched core distributions=[]
```

The validator passed on its first run. `--sync-core` was **not** used and was not needed:
core was projected from the audited full record, so every schema-identical slot was
already deeply identical.

- Schema-identical slots checked: **76**, all deeply identical and identically present.
- Projected slot `resources` (`Dataset` in full, `CoreDataset` in core): empty in both,
  so coverage is trivially equal.

### Full-only slots (no core counterpart in the schema)

`file_collections`, `subsets`, `splits`, `relationships`, `direct_collection`,
`participant_privacy`, `third_party_sharing`. `CoreDataset` does not declare these, so
their absence from core is required by the schema, not a loss of reconciliation.

### Semantic review of related content — `file_collections` ↔ `distributions`

All 9 modality groupings map one-to-one by `id`; no unmatched core distribution, no
unmatched full collection. For each pair, `name` and `description` are byte-identical.

| id | full `conforms_to` (FileCollection-only) | standard also stated in the shared description |
|---|---|---|
| `chorus_collection_demographics` | OMOP Common Data Model | yes |
| `chorus_collection_medication_administration` | OMOP Common Data Model | yes |
| `chorus_collection_procedures` | OMOP Common Data Model | yes |
| `chorus_collection_nursing_flowsheets` | OMOP Common Data Model | yes |
| `chorus_collection_diagnoses` | OMOP Common Data Model | yes |
| `chorus_collection_clinical_notes` | OHNLP open source schema | yes |
| `chorus_collection_imaging` | DICOM | yes |
| `chorus_collection_waveform_telemetry` | WFDB (PhysioNet schema extended) | yes |
| `chorus_collection_waveform_eeg` | EDF+ and Persyst | yes |

`conforms_to` is a `FileCollection` slot and is not declared on `CoreDistribution`, so it
is correctly omitted from the core projection. The data standard is nevertheless carried
into core because each shared `description` states it, so no information about modality
standards is lost and nothing conflicts.

No `CoreDistribution` field capable of contradicting the full record is populated: `path`,
`bytes`, `hash`, `md5`, `sha256`, `format`, `encoding`, `compression` and `media_type` are
all empty, because the bundle supplies no paths, checksums, byte counts or media types.
The `FormatEnum` and `MediaTypeEnum` value sets do not contain OMOP, DICOM, WFDB, EDF+ or
Persyst, so forcing a value would have misstated the format rather than recorded it.

### Other related-content checks (Phase 4 step 4)

- **`total_file_count` / `total_size_bytes` vs distribution-level values**: all three
  absent in both records — no scope conflict to resolve.
- **`dialect`, formats, `is_tabular`**: `dialect` is core-only and empty (no delimited-text
  dialect is described); no distribution-level `format` is set; `is_tabular: false` in
  both records, consistent with a dataset spanning DICOM imaging, WFDB and EDF+ waveforms
  alongside OMOP tables.
- **Top-level identity / version / access facts vs resources, version history and
  distributions**: `id`, `name`, `title`, `page`, `status`, `conforms_to` and `keywords`
  are identical across the pair; `version`, `doi` and `license` are absent from both;
  `resources` is empty in both; `version_access`, `license_and_use_terms`,
  `regulatory_restrictions` and `updates` are deeply identical, and their access
  statements (controlled access, registration, signed licensing agreement, `.edu` email,
  provisioned compute) agree with `distribution_formats` and with the "Controlled" access
  column reflected in every distribution description.
- **Historical release vs current release**: the released-versus-anticipated distinction
  and the August 2025 webinar snapshot are treated as different scopes with explicit
  dates, not as contradictory values, in both records.

### Final validation after Phase 4

Schema and term validation were re-run for both records after the header update; all four
checks pass. Re-running the pair validator without `--sync-core` as the final independent
check returns the same `PASS: 76 schema-identical slots` result.

## Outcome

Reconciliation completed with **zero unresolved contradictions** within or between the two
records. No divergence was found that required correction: the deterministic check passed
on first run, and the single warning was the mandatory semantic-review prompt for
`file_collections` ↔ `distributions`, reviewed above.
