# CHORUS full/core reconciliation — 2026-07-27_claude-opus-5_rep3

## Run identity

| Field | Value |
|---|---|
| Agent runtime | Claude Code |
| Provider | Anthropic |
| Model | claude-opus-5[1m] |
| Mode | four-phase project agent |
| Temperature | 0.0 |
| Generated | 2026-07-27 |
| Arm | BASELINE (document corpus only) |

## Inputs

Factual source (the only one used):

- `data/preprocessed/concatenated/CHORUS_preprocessed.txt` (36,184 bytes, 1,699 lines,
  4 source files)

Structure and selection references (not fact sources):

- `src/data_sheets_schema/schema/data_sheets_schema_all.yaml` (class `Dataset`)
- `src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml` (class `CoreDataset`)
- `data/preprocessed/source_manifest.yaml`

Source documents present in the bundle, per the manifest:

| Manifest id | Type | URL |
|---|---|---|
| `nih_reporter_project` | NIH project page | https://reporter.nih.gov/project-details/10472824 |
| `cohort_2_webinar` | tutorial | https://www.aim-ahead.net/media/jnzdnid3/bridge2ai-for-clinical-care-informational-webinar-cohort-2.pdf |
| `project_documentation` | documentation | https://chorus4ai.org/ |
| `github_organization_overview` | historical documentation (captured 2025-11-14) | https://github.com/chorus-ai#table-of-contents |

## Outputs

- Full: `data/d4d_concatenated/claudecode_agent/2026-07-27_claude-opus-5_rep3/CHORUS_d4d.yaml` (863 lines)
- Core: `data/d4d_concatenated/claudecode_agent_core/2026-07-27_claude-opus-5_rep3/CHORUS_d4d_core.yaml` (732 lines)

Line counts are informational metadata, not a quality gate. No pre-existing file was
overwritten; both version directories were empty before this run.

## Phase 3 — source and provenance audit

### Provenance

- Every factual value in both records traces to `CHORUS_preprocessed.txt`.
- No prior full or core D4D record, evaluation, reconciliation report, or RO-Crate
  artifact was read, searched, globbed, or cited. Nothing under
  `data/d4d_concatenated/` or `data/d4d_individual/` was read except this run's own
  outputs. No live web content was fetched.
- Structure was derived at runtime with LinkML `SchemaView` over `Dataset` and
  `CoreDataset` (induced slots, ranges, cardinality, inlining, required flags, enum
  permissible values). No prior YAML was used as a template and no `d4d:docExample`
  value was copied.
- The core header names both of its inputs: the source bundle and the exact same-run
  full record with the `2026-07-27_claude-opus-5_rep3` label. Both headers state
  `Prior D4D factual reuse: prohibited`.

### Source conflicts resolved

1. **Admission count: 45,000 vs 50,000.** The cohort 2 webinar states that "As of
   August 2025, [the dataset] covers 14 different hospitals with over 45K unique
   admissions." The project website's "Current Released Dataset" panel states 50,000
   patient admissions from ICU, PICU, and NICU. These are different capture points, not
   a contradiction. Resolution: both retained with explicit scope and date attribution.
   The website figure — the more recent project documentation — is used for the
   `instances` count (50000); the August 2025 webinar figure is recorded in the same
   description and in `collection_timeframes` and `distribution_dates` as a dated status
   report.

2. **100,000 patients vs 100,000 admissions.** The NIH abstract describes acquiring an
   AI-ready data set "from more than 100,000 critically ill patients"; the website's
   "Anticipated Final Dataset" panel states 100,000 patient admissions. Patients and
   admissions are not the same unit. Resolution: both phrasings are recorded verbatim
   with their source attributed, and neither is presented as the other.

3. **MIT License scope.** The chorus-ai GitHub organization README states "This project
   is licensed under the MIT License." This is the license of the GitHub software
   organization, not of the dataset — every dataset modality in the webinar table is
   listed with *Controlled* access control and requires a signed licensing agreement.
   Resolution: the top-level `license` slot was left unpopulated, and
   `license_and_use_terms.license_terms` states explicitly that MIT applies to the
   software project and that the sources state no license identifier for the dataset.

4. **Registration and `.edu` requirements are training-program scoped.** The
   registration form, licensing agreement, and `.edu` email requirement appear in the
   AIM-AHEAD Bridge2AI for Clinical Care Training Program webinar. Resolution: recorded
   in `license_and_use_terms` with that scope stated in the text, rather than asserted as
   universal dataset access policy.

5. **Trainee stipend is not participant compensation.** The webinar's $8,000 stipend and
   travel allowance are benefits to training-program trainees, not to data subjects.
   Resolution: `participant_compensation` was left unpopulated; the stipend is not
   recorded anywhere as a dataset fact.

6. **Website source anomalies transcribed, not corrected.** The project website's banner
   reads "This repoitory is under review…" (sic) and lists the program manager's address
   as `cmccrary@mgh.havard.edu` (apparent typo for `harvard`). Both are transcribed as
   printed, with the email annotated "as printed on the site". No correction was
   inferred.

### Deliberate omissions (prefer omission over inference)

CHoRUS has the smallest corpus of the four projects. The following schema sections were
left unpopulated because the bundle supports no value: `anomalies`, `known_biases`,
`content_warnings`, `collection_notifications`, `collection_consents`,
`consent_revocations`, `informed_consent`, `participant_compensation`,
`imputation_protocols`, `annotation_analyses`, `use_repository`, `other_tasks`,
`discouraged_uses`, `prohibited_uses`, `ip_restrictions`, `errata`, `retention_limit`,
`variables`, `citation`, `parent_datasets`, `related_datasets`, and the top-level
`doi`, `download_url`, `version`, `issued`, `created_on`, `license`, `publisher`,
`language`, and `is_tabular` slots.

Specific judgment calls:

- `data_topic` and `data_substrate` were omitted on all `Instance` objects because the
  bundle supplies no Bridge2AI standards-registry CURIEs.
- `hipaa_compliant` was omitted: HIPAA appears only as a *training curriculum topic*
  ("HIPAA/GDPR compliance for OMOP/FHIR data"), never as a compliance determination about
  the dataset.
- `data_use_permission` (DUO) was omitted: no permission taxonomy appears in the sources.
- `Creator.credit_roles` was omitted: the sources name a PI and a leadership team but
  assign no CRediT roles.
- `ethical_reviews` records the ethics focus groups and legal/regulatory analysis, and
  states explicitly that no IRB or IRB approval number appears in the sources. No IRB
  approval is claimed.
- `at_risk_populations.at_risk_groups_included` is set `true` on the stated basis that
  the released dataset includes PICU and NICU admissions; the record states that no
  group-specific protections, assent, or guardian-consent procedures appear in the
  sources.
- `regulatory_restrictions.confidentiality_level: restricted` maps the sources' uniform
  "Controlled" access-control designation onto the schema enum
  (`unrestricted`/`restricted`/`confidential`). The rationale is stated in the object's
  description.
- The webinar's modality table survives PDF extraction with its Metadata (Yes/Planned)
  column ambiguously interleaved. Rather than guess a row-to-value alignment, the
  records state per modality only what is unambiguous (data standard, controlled access,
  and the published metadata schemas listed), and note in
  `known_limitations` that metadata coverage is uneven across modalities.

### Phase 2 discoveries back-ported into the full record

Two source-supported facts surfaced during core generation and were corrected in the
full record first, per Phase 3 step 4:

1. **Alternate project website.** The GitHub organization README's Contact section lists
   `www.bridge2ai.org/chorus` as the project website. Added to
   `maintainers[0].maintainer_details` in full, alongside the `https://chorus4ai.org/`
   site already recorded as `page`.
2. **Collection directness.** `direct_collection` (is_direct: false — data come from
   hospital clinical systems, not from the individuals) has no CoreDataset slot. To avoid
   losing the fact in core, the equivalent statement was added to
   `acquisition_methods[0].acquisition_details`, which *is* a shared slot, in the full
   record. `direct_collection` is retained in full as well.

Both files were re-validated after the back-port. No other correction was required: no
unsupported, stale, or mis-scoped assertion was found in either record.

### Internal consistency check

Repeated identifiers, counts, and access facts agree within each file and across the
pair: `id` (`https://chorus4ai.org/`), award numbers (`1OT2OD032701-01` /
`OT2OD032701`, application ID 10472824, $5,880,300, 2022-09-01 to 2026-11-30), 50,000
admissions, 1.6 billion OMOP rows, 7,642 radiology admissions, ~1,000 images, 23 Tb of
waveform data, 14 contributing hospitals within 20 academic centers, 60+ consortium
members, 9 modalities, and uniform controlled access. The ~1,000-image figure appears
consistently as `instances[…].counts: 1000` and `file_collections[imaging].file_count: 1000`.

## Phase 4 — strict full/core reconciliation

### Schema-derived shared slots

Shared slots were derived at runtime from `Dataset` and `CoreDataset` via LinkML
`SchemaView`; no hand-written field list was used.

- **76 schema-identical slots** were compared. All are present in both records or absent
  from both, and every parsed YAML value is deeply identical, including nested mappings
  and list ordering. Verified independently of the validator: the set of shared top-level
  keys with differing values is empty.
- **Projected slots: `resources`.** Range differs (`Dataset` in full, `CoreDataset` in
  core). Neither record populates it, so coverage is trivially equal.
- Narrative fields were **not** condensed, paraphrased, reordered, or omitted in core.

### Full-only content (schema-mandated, not divergence)

Seven top-level slots appear in full and not in core. Each was confirmed by `SchemaView`
to be absent from `CoreDataset`:

`direct_collection`, `file_collections`, `participant_privacy`, `relationships`,
`splits`, `subsets`, `third_party_sharing`.

Semantic coverage of the dropped content in core:

| Full-only slot | Core coverage |
|---|---|
| `file_collections` | projected to `distributions` (below) |
| `direct_collection` | statement carried in the shared `acquisition_methods` |
| `participant_privacy` | tokenization/de-identification carried in shared `is_deidentified`; enclave and controlled access carried in `external_resources` and `license_and_use_terms` |
| `subsets`, `splits` (holdout test set) | carried in shared `tasks` (`d4d:chorus-task-external-validation`) and `intended_uses` |
| `third_party_sharing` | sharing beyond the consortium carried in shared `existing_uses`, `intended_uses`, and `license_and_use_terms` |
| `relationships` | multi-modal harmonization carried in shared `preprocessing_strategies` and `collection_mechanisms` |

### Related-content mapping: `file_collections` → `distributions`

The validator emits `WARNING [semantic-review-required]` for this pair. The review was
performed; the warning is not evidence of review, so the findings are recorded here.

Five `FileCollection` objects map one-to-one to five `CoreDistribution` objects, matched
by `id`. Deterministic matches = 5, unmatched core distributions = 0.

| id | name / description | Full-only nested slots dropped |
|---|---|---|
| `d4d:chorus-fc-structured-ehr-omop` | identical | `title`, `collection_type`, `conforms_to` |
| `d4d:chorus-fc-clinical-notes` | identical | `title`, `collection_type`, `conforms_to` |
| `d4d:chorus-fc-imaging` | identical | `title`, `collection_type`, `conforms_to`, `file_count` |
| `d4d:chorus-fc-waveform-telemetry` | identical | `title`, `collection_type`, `conforms_to` |
| `d4d:chorus-fc-waveform-eeg` | identical | `title`, `collection_type`, `conforms_to` |

Every dropped slot is absent from the `CoreDistribution` class (whose slots are `bytes`,
`hash`, `md5`, `sha256`, `path`, `format`, `encoding`, `compression`, `media_type`, `id`,
`name`, `description`, `used_software`), so each omission is schema-mandated rather than
a discrepancy. Core adds no key that full lacks.

Conflict checks across the related representations:

- **Names, descriptions, paths:** `name` and `description` are byte-identical for all
  five pairs. No `path` is asserted in either record.
- **Formats:** the `CoreDistribution.format` enum (CSV/TSV/XML/JSON/… ZIP/TAR/GZ) contains
  no value for OMOP, OHNLP, DICOM, WFDB, or EDF+/Persyst, so `format`, `media_type`, and
  `encoding` were left unset rather than forced onto an inapplicable value. The format
  information survives in the identical `description` text of each distribution and in
  `conforms_to` on the full side. No conflict.
- **Compression:** unset in both records; the sources state none.
- **Checksums and byte counts:** the sources supply no `hash`, `md5`, `sha256`, or byte
  counts, so `bytes` is unset. The one reported size, "23 Tb waveform data", is
  ambiguous between terabits and terabytes in the source and was deliberately not
  converted to an integer byte count; it is carried as text in the telemetry
  distribution's description, `version_access`, and `distribution_dates`.
- **`total_file_count` / `total_size_bytes`:** unpopulated in full; `CoreDataset` has no
  counterpart. Scopes are therefore trivially consistent. The imaging `file_count: 1000`
  has no CoreDistribution counterpart, but the same 1,000-image fact is present in core
  via the shared `instances` list, so no fact is lost.
- **`dialect` / `is_tabular`:** both unset in core; `is_tabular` unset in full. The
  dataset is multimodal and the sources make no tabular claim. Consistent.
- **Access URLs and release scope:** `distribution_formats.access_urls`
  (`https://chorus4ai.org/`, `https://github.com/chorus-ai`) and `distribution_dates` are
  schema-identical shared slots and are byte-identical across the pair.
- **Identity/version/access facts:** `id`, `name`, `title`, `page`, `status`, and
  `keywords` are identical across the pair and agree with `version_access`,
  `distribution_dates`, `license_and_use_terms`, and `regulatory_restrictions`. The
  "Current Released Dataset" and "Anticipated Final Dataset" figures are consistently
  labelled as current versus anticipated in both records, and are not treated as
  contradictory values for the same quantity.

**Result: zero unresolved contradictions within or between the two records.**

## Commands run

```bash
poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_all.yaml \
  -C Dataset data/d4d_concatenated/claudecode_agent/2026-07-27_claude-opus-5_rep3/CHORUS_d4d.yaml

poetry run linkml-term-validator validate-data \
  data/d4d_concatenated/claudecode_agent/2026-07-27_claude-opus-5_rep3/CHORUS_d4d.yaml \
  --schema src/data_sheets_schema/schema/data_sheets_schema_all.yaml --target-class Dataset

poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml \
  -C CoreDataset data/d4d_concatenated/claudecode_agent_core/2026-07-27_claude-opus-5_rep3/CHORUS_d4d_core.yaml

poetry run linkml-term-validator validate-data \
  data/d4d_concatenated/claudecode_agent_core/2026-07-27_claude-opus-5_rep3/CHORUS_d4d_core.yaml \
  --schema src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml --target-class CoreDataset

poetry run python -m data_sheets_schema.d4d_pair_consistency \
  --full data/d4d_concatenated/claudecode_agent/2026-07-27_claude-opus-5_rep3/CHORUS_d4d.yaml \
  --core data/d4d_concatenated/claudecode_agent_core/2026-07-27_claude-opus-5_rep3/CHORUS_d4d_core.yaml \
  --sync-core

poetry run python -m data_sheets_schema.d4d_pair_consistency \
  --full data/d4d_concatenated/claudecode_agent/2026-07-27_claude-opus-5_rep3/CHORUS_d4d.yaml \
  --core data/d4d_concatenated/claudecode_agent_core/2026-07-27_claude-opus-5_rep3/CHORUS_d4d_core.yaml
```

## Files changed

| File | Change |
|---|---|
| `…/claudecode_agent/2026-07-27_claude-opus-5_rep3/CHORUS_d4d.yaml` | created (Phase 1); two Phase 3 back-ports applied |
| `…/claudecode_agent_core/2026-07-27_claude-opus-5_rep3/CHORUS_d4d_core.yaml` | created (Phase 2); rewritten once by `--sync-core` in Phase 4 |
| `…/claudecode_agent_core/2026-07-27_claude-opus-5_rep3/CHORUS_reconciliation.md` | this report |

## Final results

| Check | Result |
|---|---|
| `linkml-validate` — full, class `Dataset` | No issues found |
| `linkml-term-validator` — full, class `Dataset` | Validation passed |
| `linkml-validate` — core, class `CoreDataset` | No issues found |
| `linkml-term-validator` — core, class `CoreDataset` | Validation passed |
| `d4d_pair_consistency` (final, no `--sync-core`) | PASS: 76 schema-identical slots; projected slots=`['resources']` |
| Semantic review of `file_collections` ↔ `distributions` | completed; 5/5 matched, 0 unmatched, 0 conflicts |
