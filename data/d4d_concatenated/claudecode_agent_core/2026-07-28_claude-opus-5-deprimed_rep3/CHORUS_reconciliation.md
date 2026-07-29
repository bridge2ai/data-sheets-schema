# CHORUS full/core reconciliation — 2026-07-28_claude-opus-5-deprimed_rep3

- **Project:** CHORUS
- **Version label:** `2026-07-28_claude-opus-5-deprimed_rep3`
- **Arm:** BASELINE (input documents only)
- **Mode:** four-phase project agent, de-primed
- **Runtime / provider / model:** Claude Code / Anthropic / `claude-opus-5[1m]`
- **Temperature:** 0.0

## Inputs

| Role | Path |
|---|---|
| Source bundle (only factual source) | `data/preprocessed/concatenated/CHORUS_preprocessed.txt` |
| Source manifest (provenance only) | `data/preprocessed/source_manifest.yaml` |
| Full schema | `src/data_sheets_schema/schema/data_sheets_schema_all.yaml` (`Dataset`) |
| Core schema | `src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml` (`CoreDataset`) |

## Outputs

| Role | Path |
|---|---|
| Full | `data/d4d_concatenated/claudecode_agent/2026-07-28_claude-opus-5-deprimed_rep3/CHORUS_d4d.yaml` |
| Core | `data/d4d_concatenated/claudecode_agent_core/2026-07-28_claude-opus-5-deprimed_rep3/CHORUS_d4d_core.yaml` |
| Report | `data/d4d_concatenated/claudecode_agent_core/2026-07-28_claude-opus-5-deprimed_rep3/CHORUS_reconciliation.md` |

---

## Phase 3 — Source and provenance audit

### Provenance boundary

Complete list of files read during this run:

- `.claude/agents/d4d-provenance-guard.md`, `.claude/commands/d4d-full-core.md`,
  `.claude/commands/d4d-agent.md` (repository generation instructions)
- `data/preprocessed/concatenated/CHORUS_preprocessed.txt` (the declared bundle)
- `data/preprocessed/source_manifest.yaml` (CHORUS entries)
- `data/data_sheets_schema_all.yaml` and `data_sheets_schema_core_all.yaml` under
  `src/data_sheets_schema/schema/`, read directly and through `SchemaView`

**No prior generated D4D record was read, opened, grepped, or consulted** — from any
arm, label, or date. Nothing under `data/d4d_concatenated/` was read other than the
two files this run wrote. No evaluation report, reconciliation report, test fixture,
or schema example supplied any dataset fact. `d4d:docExample` annotations were treated
as illustrations only and none of their values appear in either output.

Structure was derived exclusively from the schemas via `SchemaView.class_induced_slots`,
not from any template. This surfaced three shapes that a template-driven guess would
have got wrong, and all three were corrected against the schema before validation
passed: `Creator.principal_investigator`, `FundingMechanism.grantor`, and
`LicenseAndUseTerms.contact_person` are **non-inlined** `Person`/`Grantor` references
and therefore take identifier strings, not nested objects.

### Source coverage

All four manifest-selected documents contributed content:

| Source ID | Type | Contribution |
|---|---|---|
| `nih_reporter_project` | NIH project page | Award identity, PI, awardee org, project period, award amount, motivation, gaps, pillars, methods |
| `cohort_2_webinar` | tutorial (2025-09-09) | Nine-modality table (standard / access control / metadata / published schema), August 2025 status, access process, leadership team, existing uses |
| `project_documentation` | documentation (chorus4ai.org) | Current released vs anticipated final dataset counts, consortium size, project components, contact, site notice |
| `github_organization_overview` | historical documentation (captured 2025-11-14) | Network scope, tooling and repositories, SOPs, mappings, contribution routes, MIT/Apache licensing of code, access-request contacts |

The GitHub overview is a historical supplement explicitly retained by the current
manifest with a curation note, so it is an allowed source. Its content is used for
repository, SOP, standards, contributor-role, and software-tooling detail, consistent
with the stated reason for retention.

### Source disagreements resolved

1. **Admission count.** The project website reports a current released dataset of
   **50,000 patient admissions**; the September 2025 webinar reports **over 45,000
   unique admissions as of August 2025**. Resolved by *scope and date*, not by picking
   a winner: 50,000 is carried as the current figure in `instances[0].counts`, and the
   45,000 figure is retained with explicit August 2025 scoping in
   `instances[0].missing_information`, `collection_timeframes[1]`, and
   `version_access.version_details`. Neither figure is presented as superseding the
   other silently.

2. **Patients vs. admissions at the 100,000 mark.** The NIH abstract says "more than
   100,000 critically ill **patients**"; the website says an anticipated final dataset
   of "100,000 **patient admissions**". These are different units and are kept in their
   own wording in `purposes` / `human_subject_research` (patients) and `updates` /
   `version_access` (admissions). They are not conflated into one number.

3. **License scope — the significant finding of this audit.** The GitHub overview
   states "This project is licensed under the MIT License", and individual repositories
   are marked MIT (`chorus_waveform`, `chorus-extract-upload`, `UF-Geocoding`) or
   Apache-2.0 (`Chorus_SOP`). That statement governs **project code**, not the dataset:
   every one of the nine data modalities is marked "Controlled" access, and access
   requires a signed licensing agreement plus a `.edu` email address. Top-level
   `license` is therefore **deliberately left unpopulated in both records**, and the
   MIT/Apache facts are stated with explicit code-versus-data scoping inside
   `license_and_use_terms.license_terms` and `ip_restrictions.restrictions`. Setting
   `license: MIT` at dataset level would have been a mis-scoped assertion.

### Mis-scoping avoided (recorded so the omissions are not read as gaps)

- **`participant_compensation` omitted.** The `$8,000` stipend in the bundle is paid to
  AIM-AHEAD *trainees*, not to data subjects. It is not participant compensation.
- **`regulatory_restrictions.hipaa_compliant` omitted.** HIPAA appears in the bundle
  only as a *training curriculum topic* ("HIPAA/GDPR compliance for OMOP/FHIR data"),
  never as a compliance claim about this dataset. Asserting any
  `ComplianceStatusEnum` value would have been fabrication.
- **`collection_consents`, `consent_revocations`, `informed_consent` omitted.** The
  bundle describes community-facing ethics focus groups but says nothing about
  patient-level consent or its revocation. The focus groups are recorded under
  `ethical_reviews` and `data_protection_impacts` instead.
- **`ethical_reviews[*].reviewing_organization` / IRB fields omitted.** No IRB approval
  for this dataset appears anywhere in the bundle.
- **Dataset-level dates omitted.** `created_on`, `issued`, and `last_updated_on` are
  unset because the only dates available are the *award* period; those are carried in
  `collection_timeframes[0]` with the description stating explicitly that they are the
  funding period, not the clinical coverage window.

### Corrections applied during Phase 3

| # | Slot | Correction |
|---|---|---|
| 1 | `data_protection_impacts[0].impact_details` and `used_software` | "CTP-based de-identification repository" → "de-identification repository named CTP-deid". The bundle lists the repository name with no description; expanding "CTP" would have imported outside knowledge. |
| 2 | `human_subject_research.description` | Reworded so the "more than 100,000 critically ill patients" figure is attributed as the project's stated target scale, alongside the current 50,000-admission release, rather than described as what the dataset already contains. |
| 3 | `existing_uses[0].examples` | Tense fixed ("ran" → "runs"); Cohort 2 ends 2026-07-31, which has not yet passed as of the generation date. |

### Internal consistency check (each record against itself)

Repeated values were checked for agreement across every slot in which they appear:
50,000 admissions (6 sites), 45,000 / August 2025 (4 sites), 14 hospitals, 20 academic
centers, 9 modalities (matching exactly 9 `resources` entries), ~1,000 images (6
sites), 7,642 radiology admissions, 1.6 billion OMOP rows, 23 Tb waveform, award
`OT2OD032701` and period 2022-09-01 → 2026-11-30. No internal contradiction found in
either file.

### Source-side artifacts reproduced verbatim, not silently corrected

- The website contact address is published as `cmccrary@mgh.havard.edu` (the source
  spells the domain "havard"). It is reproduced as published and flagged in
  `license_and_use_terms.license_terms` with "address reproduced as published".
  Correcting it would have invented a fact.
- The site notice "This repoitory is under review for potential modification in
  compliance with Administration directives" is quoted with the source's spelling.
- The webinar's nine-modality table is OCR-scrambled in the column that assigns
  "OMOP schema **with extensions**" to one of the five structured-EHR domains. The
  column alignment does not identify which domain, so no per-modality guess was made;
  the fact is stated at the aggregate level in `distribution_formats[0].description`
  and in the dataset `description`.

### Phase 2 discoveries back-ported to full

**None.** The Phase 2 source re-read against `CoreDataset` found no fact that the
Phase 1 full record had missed and no core field that the full record left empty but
the bundle supports. No back-port was required.

---

## Phase 4 — Strict full/core reconciliation

### Shared-slot derivation

Shared slots were derived at runtime from `Dataset` and `CoreDataset` with LinkML
`SchemaView`; no hand-written field list was used.

- `CoreDataset` induced slot inventory: **79**
- Schema-identical shared slots checked by the validator: **76**
- Projected slots: **1** (`resources`)
- Full top-level slots populated: **61**
- Core top-level slots populated: **55**

### Core construction method

Core was produced as a **schema-derived projection** of the Phase 3-audited full
record: for every `CoreDataset` slot present in the full record, the parsed value was
carried over unchanged, with top-level key order preserved from the full file. This
makes deep identity structural rather than transcribed, so no shared value was
condensed, paraphrased, reordered, or dropped to make core shorter. Nested class
shapes were confirmed identical between the two schemas for every class used
(`Purpose`, `Task`, `AddressingGap`, `Creator`, `FundingMechanism`, `Grant`,
`Instance`, `MissingInfo`, `DatasetBias`, `DatasetLimitation`, `RawDataSource`,
`CollectionTimeframe`, `DataCollector`, `LicenseAndUseTerms`, `ExternalResource`,
`Software`, and the rest).

### Full-only slots (present in full, absent from core because `CoreDataset` has no such slot)

`subsets`, `splits`, `direct_collection`, `participant_privacy`,
`third_party_sharing`, `related_datasets`.

This is schema-mandated omission, not content loss by choice. The substance of the
dropped slots survives in core through slots that do exist there: the sequestered
holdout test set appears in `purposes`, `tasks`, `future_use_impacts` and
`known_limitations`; de-identification and privacy technique detail appears in
`is_deidentified` and `data_protection_impacts`; controlled third-party sharing
appears in `license_and_use_terms` and `regulatory_restrictions`.

### `resources` projection

Full `resources` has range `Dataset`; core `resources` has range `CoreDataset`.
Matched by `id`, coverage is **equal — 9 of 9** modality sub-resources present in both:

`demographics`, `medication-administration`, `procedures`, `nursing-flowsheets`,
`diagnoses`, `clinical-notes`, `imaging`, `waveform-telemetry`, `waveform-eeg`.

Every nested slot used on these sub-resources (`id`, `name`, `description`,
`conforms_to`, `status`, `is_tabular`) exists on both `Dataset` and `CoreDataset` and
is deeply identical in both files. **No full-only nested slot was dropped from the
projection** — the projection is lossless for this record.

### Related, non-identical representations — semantic review

| Relationship | Finding |
|---|---|
| full `file_collections` → core `distributions` | Both absent. The bundle gives no file paths, file counts, byte counts, checksums, or download URLs; it describes modalities and volumes, not file collections. Nothing to map, no conflict. |
| `total_file_count` / `total_size_bytes` vs distribution-level values | Both absent from full by design. The only volume figure, "23 Tb", is **waveform-only** and would have been a mis-scoped dataset total; it is stated in the waveform-telemetry resource description and `version_access` instead. |
| `dialect` (core-only, `FormatDialect`) vs formats and `is_tabular` | `dialect` unpopulated — no delimiter/quote/header information exists in the bundle. `is_tabular: false` is identical in both records and is consistent with the mixed modality set; the five OMOP sub-resources carry `is_tabular: true` (supported by "1.6 Billion Rows of EHR OMOP data") and the notes/imaging/waveform/EEG sub-resources carry `false`. Formats in `distribution_formats` (OMOP, OHNLP, DICOM, WFDB, EDF+/Persyst) agree one-to-one with the nine `resources` entries and with `conforms_to`. No contradiction. |
| Top-level identity/version/access vs resources and repeated statements | `id`, `name`, `title`, `page`, `publisher`, `status`, `conforms_to`, `keywords` identical in both. Access statements agree across `license_and_use_terms`, `regulatory_restrictions`, `confidential_elements`, and all nine resource `status` values — all nine say controlled access. |
| Historical vs current release | Treated as distinct scopes, not a contradiction: the August 2025 webinar snapshot (14 hospitals, >45,000 admissions, ~1,000 images, EEG extraction in process) and the website's current released dataset (50,000 admissions, 1.6B OMOP rows, 7,642 radiology admissions, 23 Tb waveform) are both retained with their scope stated, alongside the anticipated final dataset (100,000 admissions). |

**Unresolved contradictions within or between the two records: none.**

### Commands run

```bash
poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_all.yaml \
  -C Dataset data/d4d_concatenated/claudecode_agent/2026-07-28_claude-opus-5-deprimed_rep3/CHORUS_d4d.yaml

poetry run linkml-term-validator validate-data \
  data/d4d_concatenated/claudecode_agent/2026-07-28_claude-opus-5-deprimed_rep3/CHORUS_d4d.yaml \
  --schema src/data_sheets_schema/schema/data_sheets_schema_all.yaml --target-class Dataset

poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml \
  -C CoreDataset data/d4d_concatenated/claudecode_agent_core/2026-07-28_claude-opus-5-deprimed_rep3/CHORUS_d4d_core.yaml

poetry run linkml-term-validator validate-data \
  data/d4d_concatenated/claudecode_agent_core/2026-07-28_claude-opus-5-deprimed_rep3/CHORUS_d4d_core.yaml \
  --schema src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml --target-class CoreDataset

poetry run python -m data_sheets_schema.d4d_pair_consistency \
  --full data/d4d_concatenated/claudecode_agent/2026-07-28_claude-opus-5-deprimed_rep3/CHORUS_d4d.yaml \
  --core data/d4d_concatenated/claudecode_agent_core/2026-07-28_claude-opus-5-deprimed_rep3/CHORUS_d4d_core.yaml

poetry run d4d provenance record --project CHORUS --method claudecode_agent \
  --label 2026-07-28_claude-opus-5-deprimed_rep3 \
  --input-bundle data/preprocessed/concatenated/CHORUS_preprocessed.txt
```

`--sync-core` was **not** required. Core was already deeply identical to the audited
full record on the first independent check, because it was built as a projection of
that record rather than transcribed.

### Files changed

- `CHORUS_d4d.yaml` — created in Phase 1; three Phase 3 corrections applied (table above).
- `CHORUS_d4d_core.yaml` — created in Phase 2, regenerated after the Phase 3 corrections.
- `CHORUS_reconciliation.md` — this report.

### Final results

| Check | Result |
|---|---|
| Full — LinkML schema validation (`Dataset`) | **PASS** (No issues found) |
| Full — ontology term validation | **PASS** |
| Core — LinkML schema validation (`CoreDataset`) | **PASS** (No issues found) |
| Core — ontology term validation | **PASS** |
| Full/core pair consistency (no `--sync-core`) | **PASS** — 76 schema-identical slots; projected slots = `['resources']` |
| Prior-D4D factual reuse | **None** |
| Unresolved contradictions | **None** |

Informational metadata only, not a quality gate: full 1481 lines / 61 top-level slots;
core 1089 lines / 55 top-level slots.

### Note on identifiers

The dataset `id` is the project's own landing page, `https://chorus4ai.org/`, and the
grant `id` is the NIH RePORTER record `https://reporter.nih.gov/project-details/10472824`
— both attested in the bundle. Identifiers required by the schema but not attested in
any source (nine modality sub-resources, the holdout subset, `Person`, `Organization`,
`Grantor`, and `Software` references) are **minted for this record** under the
`https://chorus4ai.org/d4d/` path. They are record-scoped identifiers, not claims that
those URLs resolve, and they carry no factual content beyond the names already stated
in the bundle.
