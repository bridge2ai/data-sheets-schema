# CHORUS full/core reconciliation

Run label: `2026-07-23_gpt-5.6-sol-ultra-fast`

Runtime: Codex CLI; provider: OpenAI; model: `gpt-5.6-sol`; reasoning
effort: `ultra`; mode: `fast`; generated: `2026-07-23`.

## Evidence and provenance boundary

The only factual inputs read for this run were:

- `data/preprocessed/concatenated/CHORUS_preprocessed.txt`
- The `CHORUS` entries in `data/preprocessed/source_manifest.yaml`

The manifest-selected factual sources in the bundle were:

- `nih_reporter_project`, an NIH project page, used as the authority for the
  award identity, project identifiers, principal investigator, award
  organization, fiscal year, award amount, and project dates.
- `cohort_2_webinar`, a tutorial dated September 9, 2025, used for its
  explicitly dated August 2025 dataset, modality, processing, and
  controlled-access snapshot. Its registration, `.edu` email, and licensing
  agreement statements were treated as AIM-AHEAD training-program
  requirements, not universal access rules.
- `project_documentation`, the manifest-selected CHoRUS website, used as the
  source-bundle authority for the `Current Released Dataset` and
  `Anticipated Final Dataset` snapshots. The manifest supplies no capture
  date for this source.
- `github_organization_overview`, historical documentation captured on
  2025-11-14 and retained by the manifest specifically for repository, SOP,
  standards, contributor-role, and software-tooling detail. It was not used
  as current-release authority.

Structural and validation inputs were limited to the four required repository
instructions, the applicable LinkML schema files under
`src/data_sheets_schema/schema/`, normal project configuration needed to run
the validators, and
`src/data_sheets_schema/d4d_pair_consistency.py`. During Phase 2 and later,
the exact same-run full/core artifacts listed below were also read.

No prior-run full or core D4D, prior reconciliation report, evaluation output,
test-fixture facts, git history, web content, or model-memory facts were read
or used. Generated same-run YAML was treated only as the required phase
handoff, never as an independent factual source. Schema annotations and
examples supplied no facts or defaults.

## Phase 3 — source and provenance audit

### Authority, version, date, and scope findings

- NIH RePORTER supports application ID `10472824`, project number
  `1OT2OD032701-01`, core project/award number `OT2OD032701`, PI Eric S.
  Rosenthal, Massachusetts General Hospital, fiscal year `2022`, award amount
  `5880300` with no currency stated, and project dates
  `2022-09-01T00:00:00` through `2026-11-30T00:00:00`. The dates are recorded
  as project dates, not dataset release dates.
- The project website's `Current Released Dataset` snapshot reports 50,000
  ICU/PICU/NICU patient admissions, 1.6 Billion EHR OMOP rows, 7,642
  admissions with radiology data, and 23 Tb of waveform data.
- The same website labels 100,000 patient admissions, 9 modalities, and 14
  data-contributing hospitals as an anticipated final state. These values
  were not merged with current-release counts.
- The webinar's `over 45K unique admissions` and 1,000 available images are
  explicitly scoped to August 2025. The current website's 50,000 admissions
  and 7,642 admissions with radiology data have different dates and/or units,
  so they are not contradictions. The 1,000-image value was not rewritten as
  an admission count.
- NIH's planned dataset of more than 100,000 critically ill patients was not
  collapsed into the website's anticipated 100,000 patient admissions because
  patients and admissions are different units.
- The NIH goal of future public availability and the dated controlled-access
  evidence describe different lifecycle scopes. Controlled-access assertions
  in the YAML are explicitly tied to August 2025; historical access contacts
  are explicitly tied to the 2025-11-14 capture.
- The historical GitHub MIT statement and individual MIT/Apache-2.0
  repository licenses apply to project/software material, not to the clinical
  dataset. No dataset license was inferred.
- The bundle supplies no dataset DOI, accession, semantic version, release
  date, direct data-download URL, universal access procedure, exact collection
  date range, file inventory, checksum, exact byte total, physical
  serialization metadata, update schedule, retention policy, IRB identifier,
  consent details, or HIPAA determination. Those fields were omitted.

### Corrections

Corrections were applied to the full record first and then to the core record
where the core schema permits the field:

1. Removed the five non-PI webinar leadership members from `creators`. The
   webinar establishes leadership membership, but only Eric S. Rosenthal is
   explicitly identified as principal investigator by the authoritative NIH
   record.
2. Reworded undated controlled-access assertions so they are scoped to the
   August 2025 webinar. Added the two access-request addresses only as
   historical contacts from the 2025-11-14 GitHub capture, with an explicit
   statement that the bundle does not establish them as current.
3. Removed community-facing ethics focus groups from
   `participant_privacy.privacy_techniques` in the full record. The focus
   groups are source-supported ethics activity, but they are not a technical
   privacy-preserving procedure for that schema slot.

Phase 2 identified no additional source-supported core fact that was missing
from the full record, so no other back-port was needed. Repeated identifiers,
names, dates, counts, access statements, people, organizations, and license
statements were reviewed after the corrections. No unsupported assertion or
unresolved within-record contradiction remained.

### Phase 3 validation

The following commands were run before and after corrections as required:

```text
poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_all.yaml -C Dataset data/d4d_concatenated/claudecode_agent/2026-07-23_gpt-5.6-sol-ultra-fast/CHORUS_d4d.yaml
poetry run linkml-term-validator validate-data data/d4d_concatenated/claudecode_agent/2026-07-23_gpt-5.6-sol-ultra-fast/CHORUS_d4d.yaml --schema src/data_sheets_schema/schema/data_sheets_schema_all.yaml --target-class Dataset
poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml -C CoreDataset data/d4d_concatenated/claudecode_agent_core/2026-07-23_gpt-5.6-sol-ultra-fast/CHORUS_d4d_core.yaml
poetry run linkml-term-validator validate-data data/d4d_concatenated/claudecode_agent_core/2026-07-23_gpt-5.6-sol-ultra-fast/CHORUS_d4d_core.yaml --schema src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml --target-class CoreDataset
```

Each schema command reported `No issues found`; each term command reported
`Validation passed`.

## Phase 4 — strict full/core reconciliation

The schema-derived validator reported **76 schema-identical shared slots** and
one projected slot, `resources`.

The synchronization command was run exactly once after the Phase 3 full record
became canonical:

```text
poetry run python -m data_sheets_schema.d4d_pair_consistency --full data/d4d_concatenated/claudecode_agent/2026-07-23_gpt-5.6-sol-ultra-fast/CHORUS_d4d.yaml --core data/d4d_concatenated/claudecode_agent_core/2026-07-23_gpt-5.6-sol-ultra-fast/CHORUS_d4d_core.yaml --sync-core
```

Result:

```text
PASS: 76 schema-identical slots; projected slots=['resources']
```

The command emitted no warnings. The required semantic review was still
performed:

- Full `file_collections` and core `distributions` are both absent. The source
  bundle does not support file paths, physical file identities, checksums,
  compression, exact per-distribution byte counts, or a physical
  serialization from the core `FormatEnum`; creating distribution objects
  would therefore add unsupported facts.
- The five shared `distribution_formats` entries are deeply identical after
  synchronization. They preserve the source-supported representations and
  standards—OMOP, OHNLP, DICOM, WFDB with a PhysioNet-extended schema, and
  EDF+/Persyst—without pretending that those domain standards are supported
  physical `CoreDistribution.format` enum values.
- Full `total_file_count` and `total_size_bytes` and core distribution
  `bytes` are absent. The 1.6 Billion figure is a row count, and the reported
  23 Tb is waveform-component scope with the source's original unit spelling;
  neither was converted into a dataset-wide byte total.
- No distribution access URL or top-level `download_url` is emitted because
  the bundle supplies no direct data-access URL. The shared project `page` is
  identical, and controlled access, training-specific agreement terms, and
  historical contacts retain their explicit temporal/audience scope.
- Full and core `is_tabular` are absent, and core `dialect` is absent. The
  dataset is multimodal and the bundle supplies no single tabular truth value
  or delimiter/header/quoting dialect for the dataset as a whole.
- `version`, `issued`, and `distribution_dates` are absent in both records.
  Current, anticipated-final, August 2025 historical, and project-award scopes
  are distinguished in the shared narratives and instance/limitation
  objects.
- `resources` is absent in both records, so projected coverage is equal.
- Identity, status, purpose, creator, funding, counts, modality descriptions,
  access terms, and de-identification statements were reviewed for repeated
  facts. The current, anticipated, and historical values remain explicitly
  scoped and non-contradictory.
- Full-only `participant_privacy` is consistent with the shared
  preprocessing and `is_deidentified` statements: transformations are
  described as intended to limit re-identification, while larger-cohort
  imaging de-identification is explicitly historical and in process as of
  August 2025.

The core header contains:

```text
# Phase 4 reconciliation: completed
```

The final independent pair command was:

```text
poetry run python -m data_sheets_schema.d4d_pair_consistency --full data/d4d_concatenated/claudecode_agent/2026-07-23_gpt-5.6-sol-ultra-fast/CHORUS_d4d.yaml --core data/d4d_concatenated/claudecode_agent_core/2026-07-23_gpt-5.6-sol-ultra-fast/CHORUS_d4d_core.yaml
```

Result:

```text
PASS: 76 schema-identical slots; projected slots=['resources']
```

The same four schema and term validation commands listed in Phase 3 were run
again after the final pair check. Both schema validations reported
`No issues found`, and both term validations reported `Validation passed`.

## Changed artifacts and final status

- `data/d4d_concatenated/claudecode_agent/2026-07-23_gpt-5.6-sol-ultra-fast/CHORUS_d4d.yaml`
- `data/d4d_concatenated/claudecode_agent_core/2026-07-23_gpt-5.6-sol-ultra-fast/CHORUS_d4d_core.yaml`
- `data/d4d_concatenated/claudecode_agent_core/2026-07-23_gpt-5.6-sol-ultra-fast/CHORUS_reconciliation.md`

Final status: both YAML files parse and pass their applicable schema and term
validators; the final pair validator passes; every schema-identical shared
slot is deeply identical; the projected and related fields received semantic
review; there were no validator warnings; and there are **zero unresolved
contradictions**.
