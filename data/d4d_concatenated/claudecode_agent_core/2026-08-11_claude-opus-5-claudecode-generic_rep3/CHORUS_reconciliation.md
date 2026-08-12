# CHORUS full/core reconciliation

- **Run label:** `2026-08-11_claude-opus-5-claudecode-generic_rep3`
- **Arm:** BASELINE (input documents only)
- **Mode:** four-phase project agent, generic prompt
- **Runtime / provider / model:** Claude Code / Anthropic / claude-opus-5
- **Declared input bundle:** `data/preprocessed/concatenated/CHORUS_preprocessed.txt` (4 source documents)
- **Full:** `data/d4d_concatenated/claudecode_agent/2026-08-11_claude-opus-5-claudecode-generic_rep3/CHORUS_d4d.yaml`
- **Core:** `data/d4d_concatenated/claudecode_agent_core/2026-08-11_claude-opus-5-claudecode-generic_rep3/CHORUS_d4d_core.yaml`

## Referent

`Dataset` admits one referent. The record is about **the CHoRUS dataset** — the
multi-center, multimodal critical care dataset assembled by the Patient-Focused
Collaborative Hospital Repository Uniting Standards (CHoRUS) for Equitable AI project —
identified by `https://chorus4ai.org/`, matching the manifest declaration
(`referent: CHoRUS dataset`, `referent_id: https://chorus4ai.org/`,
`related_but_distinct: []`). No dataset DOI, accession, or version identifier appears in
any document in the bundle, so the project site URL is the identifier the sources
themselves use. The same referent and the same `id` are held in both records.

Material about the **AIM-AHEAD Bridge2AI for Clinical Care Training Program** occupies
most of one source document. It is not the referent. It was used only where it makes a
claim about the dataset — existing uses, access and registration requirements, the
modality table, the August 2025 size statement, and the CHoRUS leadership team. Program
facts that are about trainees rather than about the data (the $8,000 trainee stipend,
travel allowances, eligibility and citizenship rules, curriculum topics) were deliberately
not recorded; in particular the trainee stipend was **not** written into
`participant_compensation`, which concerns data subjects.

## Phase 3 — source and provenance audit

### Provenance boundary

No prior full or core D4D record was read, searched, grepped or consulted, from any arm,
label or date. Nothing under `data/d4d_concatenated/` was opened other than the two
outputs of this run, and no `*_crate_d4d.yaml` or `*_crate_mapped_d4d.yaml` under
`data/ro-crate_packages/` was opened. Factual inputs were the declared bundle and the
manifest `scope:` block only; structural inputs were the two LinkML schemas, resolved at
runtime with `SchemaView` rather than from any example record. `d4d download scope
--check` was run as a completion gate; it reports aggregate verdicts and exposed no
content of any other record.

Phase 2 read the declared bundle plus the exact same-run Phase 1 full record at the path
above, which carries this run's version label. No older core was consulted, as a template
or otherwise.

### Source disagreements — represented, not merged

The bundle contains four documents that do not agree on the dataset's current size. Each
statement is recorded as the source states it, attributed and separated, rather than
reconciled into one number:

| Claim | Source | Where recorded |
|---|---|---|
| 50,000 patient admissions (ICU, PICU, NICU), "Current Released Dataset" | `chorus4ai_org_row11` | `instances[0]`, `counts: 50000` |
| "over 45K unique admissions" across 14 hospitals, as of August 2025 | `cohort_2_webinar` | `instances[1]`, no `counts` — the source states a bound, not a figure |
| 7,642 admissions with radiology data | `chorus4ai_org_row11` | `instances[3]`, `counts: 7642` |
| "currently 1000 images available with de-id in process for larger cohort" | `cohort_2_webinar` | `instances[4]`, `counts: 1000`, caveated as a different unit |
| 100,000 patient admissions / 9 modalities / 14 hospitals, "Anticipated Final Dataset" | `chorus4ai_org_row11` | `instances[6]`, marked as a target |
| "more than 100,000 critically ill patients" | `nih_reporter_project` | `instances[6]` description, noted as a different unit (patients vs admissions) |

None of these was chosen over another and none was averaged or rounded together. The
webinar's "over 45K" was not written as `counts: 45000`, because that would convert a
bound into a measurement. The website's "23 Tb Waveform data" was **not** written to
`total_size_bytes`, because the source does not disambiguate terabits from terabytes; it
is recorded as an instance description with the ambiguity named.

Two further disagreements of scope rather than value:

- **License.** The GitHub organization states "This project is licensed under the MIT
  License" and individual repositories carry MIT or Apache-2.0 badges. That governs the
  project's *software*. No license is stated for the *data*, which are controlled-access
  under a signed licensing agreement. The top-level `license` slot is therefore left
  absent, and the distinction is stated explicitly in
  `license_and_use_terms.description`. Writing `license: MIT` would have been the
  available wrong answer.
- **HIPAA / GDPR.** These appear in the bundle only as topics of a training curriculum
  ("HIPAA/GDPR compliance for OMOP/FHIR data"). No compliance determination is made about
  the dataset, so `regulatory_restrictions.hipaa_compliant` is left absent and the point
  is stated in that object's `source_caveats`.

### Evidence quality findings

- The Cohort 2 webinar's modality table was extracted from a PDF and its rows and columns
  are interleaved in the preprocessed text. The modality names, data standards and
  metadata-schema names are legible; the row-to-column *pairing* of each data type with
  its access-control and metadata status is reconstructed. This is recorded in the
  dataset-level `source_caveats` and again on the affected `known_limitations` entry,
  rather than being presented at the same confidence as the rest.
- The NIH abstract is truncated mid-clause: "and label data for ;". The labeling purpose
  it was about to state is unrecoverable, and this is noted on
  `labeling_strategies[0].source_caveats` rather than completed by inference.
- The project website prints the program manager's address as `cmccrary@mgh.havard.edu`.
  The domain appears misspelled at the source. It is transcribed verbatim with the
  observation recorded in `source_caveats`, not silently corrected.
- The website carries a banner: "This repoitory is under review for potential modification
  in compliance with Administration directives" (spelling as published). Recorded in
  top-level `notes`, in `external_resources[0].restrictions`, and as a
  `future_use_impacts` entry, because it bears on future availability.

### Omissions — absent evidence recorded as absence

No IRB, ethics review board, consent procedure, consent revocation mechanism, collection
notification, or data-subject compensation is described anywhere in the bundle. The
corresponding slots (`informed_consent`, `collection_consents`, `consent_revocations`,
`collection_notifications`, `participant_compensation`, `human_subject_research.irb_approval`,
`human_subject_research.ethics_review_board`) are left absent and the gap is named in
`ethical_reviews[0].source_caveats`, `human_subject_research.source_caveats` and
`at_risk_populations.source_caveats`. The Ethics pillar *is* described — community-facing
focus groups, legal and regulatory analysis — and is recorded under `ethical_reviews`
without being upgraded into a claim of IRB review.

Likewise absent and left absent: dataset DOI, version string, citation, release dates,
retention limits, update frequency, file-level manifests or checksums, download URLs,
variable-level metadata, inter-annotator agreement, imputation, discouraged and prohibited
uses, and any calendar range for the retrospective clinical coverage.
`collection_timeframes` was deliberately **not** populated with the NIH project period
(2022-09-01 to 2026-11-30): that is the award period, not the period the clinical data
cover. It is recorded instead on the grant.

### Shape and slot-filling audit

Checked, with no violations found: no prose in a slot whose range is a list; no enum value
outside its schema definition (`limitation_type`, `confidentiality_level`,
`role`/`CreatorOrMaintainerEnum` all checked against the induced enums); no commentary
embedded inside a name, identifier or affiliation value; structured slots filled ahead of
prose (`funders[].grantor` and `.grants[].grant_number` rather than a grant number inside
a description; `creators[].affiliations` as `Organization` objects rather than institution
names inside `description`; `human_subject_research.special_populations` as a list);
narrative in `description`; evidence commentary confined to `source_caveats` and never
placed in `notes`; no sibling slot restated. `notes` is used exactly once, at the top
level, for the site banner — content that is about the published source rather than about
the dataset's content and that `description` should not hold.

`used_software` was left empty throughout rather than populated with constructed GitHub
URLs: `Software` requires an `id`, the bundle gives repository *names* under
`https://github.com/chorus-ai` but not repository URLs, and minting them would have been
inference. The tooling is instead named in `preprocessing_strategies`,
`collection_mechanisms` and `external_resources[1]`, where it needs no invented
identifier. For the same reason `resources`, `subsets` and `file_collections` are absent:
each entry would have required an invented `id` for a sub-dataset the sources never
identify. The holdout test set is carried in `splits`, whose class needs no identifier.

### Back-ports from Phase 2

None. Phase 2 read the same bundle and found no fact that the full record had missed or
stated differently, so no correction was made to the full record and no source-supported
value exists in core that is absent from full.

## Phase 4 — strict full/core reconciliation

Shared slots were derived at runtime from `Dataset` and `CoreDataset` with LinkML
`SchemaView`; no hand-written field list was used. `CoreDataset` induces 81 attributes.

**Schema-derived shared-slot count: 78 schema-identical slots** (validator's own count).
`resources` is the single projected slot (`Dataset` in full, `CoreDataset` in core); it is
absent from both records, so the projection is vacuous and coverage is trivially equal.

### Result

```
PASS: 78 schema-identical slots; projected slots=['resources']
```

Every schema-identical shared slot is present in both records or absent from both, and
every present one is deeply identical, including nested mapping values and list order.
Nothing was condensed, paraphrased, reordered or omitted in core: the core record was
produced by projecting the audited full record onto the `CoreDataset` slot inventory, so
narrative fields (`description`, every `*.response`, every `*_details`, every
`source_caveats`) are byte-for-byte the same text in both files. The `--sync-core` pass
changed no content; it appended the `# Phase 4 reconciliation: completed` header line.

### Full-only slots (no `CoreDataset` home)

Four populated slots exist in `Dataset` and not in `CoreDataset`, and are therefore absent
from core by schema, not by editorial choice:

| Slot | Content | Related core content — checked for conflict |
|---|---|---|
| `splits` | Holdout test set for external model validation | Same holdout is referred to in `purposes` and `tasks`, present identically in both. No conflict. |
| `direct_collection` | `is_direct: false` — data taken from hospital records, not from individuals | `acquisition_methods` and `raw_data_sources` (both in core) state the same retrospective extraction. Consistent. |
| `participant_privacy` | Tokenization, re-identification-limiting transforms, privacy tooling | `is_deidentified` is in core and carries the same de-identification account. Consistent, not contradictory; core loses detail, not correctness. |
| `data_governance` | Registration and access-review process, access contacts, stewardship roles | `license_and_use_terms.license_terms` is in core and states the registration form, signed licensing agreement and `.edu` requirement. Consistent; the access-request email addresses appear only in the full record. |

### Semantically related content — reviewed

- **`file_collections` → `distributions`:** both absent. The bundle contains no file
  manifest, path, format-level checksum, byte count or download URL, so neither
  representation is populated and there is nothing to conflict.
- **`total_file_count` / `total_size_bytes` versus distribution-level values:** both
  absent in full, consistent with the deliberate refusal to convert "23 Tb".
- **`dialect`, formats, `is_tabular`:** `is_tabular` is absent from both — the dataset is
  multimodal (tabular OMOP alongside DICOM imaging, WFDB and EDF+/Persyst waveforms), and
  a single boolean would misstate it. `dialect` (core-only) is absent. The five
  `distribution_formats` entries are identical in both records.
- **Top-level identity, version and access facts versus the rest of the record:** `id`,
  `name`, `title` and `page` agree with `external_resources[0]` and with the NIH RePORTER
  title. `version`, `doi` and `citation` are absent, which agrees with
  `version_access.version_details` stating that the sources assign no version identifier or
  DOI. Access statements agree across `license_and_use_terms`, `regulatory_restrictions`,
  `intended_uses.usage_notes`, `raw_data_sources[].access_details` ("Controlled access"
  throughout) and `confidential_elements`.
- **Historical versus current release:** the "Anticipated Final Dataset" figures, the
  "Current Released Dataset" figures and the August 2025 webinar snapshot are three
  different scopes, each labelled with its scope in place. They are not treated as
  contradictions and no attempt was made to make them agree.

**Unresolved contradictions within or between the two records: none.**

## Validation

```bash
poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_all.yaml \
  -C Dataset data/d4d_concatenated/claudecode_agent/2026-08-11_claude-opus-5-claudecode-generic_rep3/CHORUS_d4d.yaml
# No issues found

poetry run linkml-term-validator validate-data \
  data/d4d_concatenated/claudecode_agent/2026-08-11_claude-opus-5-claudecode-generic_rep3/CHORUS_d4d.yaml \
  --schema src/data_sheets_schema/schema/data_sheets_schema_all.yaml --target-class Dataset
# Validation passed

poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml \
  -C CoreDataset data/d4d_concatenated/claudecode_agent_core/2026-08-11_claude-opus-5-claudecode-generic_rep3/CHORUS_d4d_core.yaml
# No issues found

poetry run linkml-term-validator validate-data \
  data/d4d_concatenated/claudecode_agent_core/2026-08-11_claude-opus-5-claudecode-generic_rep3/CHORUS_d4d_core.yaml \
  --schema src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml --target-class CoreDataset
# Validation passed

poetry run d4d download scope --check --project CHORUS
# none is about a dataset its project declares distinct

poetry run python -m data_sheets_schema.d4d_pair_consistency --full <full> --core <core> --sync-core
# PASS: 78 schema-identical slots; projected slots=['resources']

poetry run python -m data_sheets_schema.d4d_pair_consistency --full <full> --core <core>
# PASS: 78 schema-identical slots; projected slots=['resources']
```

All four validations passed, before and after the `--sync-core` pass.

## Files changed

- `data/d4d_concatenated/claudecode_agent/2026-08-11_claude-opus-5-claudecode-generic_rep3/CHORUS_d4d.yaml` (created, Phase 1; unchanged by Phases 3 and 4)
- `data/d4d_concatenated/claudecode_agent_core/2026-08-11_claude-opus-5-claudecode-generic_rep3/CHORUS_d4d_core.yaml` (created, Phase 2; header line appended in Phase 4)
- `data/d4d_concatenated/claudecode_agent_core/2026-08-11_claude-opus-5-claudecode-generic_rep3/CHORUS_reconciliation.md` (this report)

Nothing outside these three paths was written.

## Counts (informational, not a quality gate)

| | full | core |
|---|---|---|
| top-level slots populated | 46 | 42 |
| populated slots including nested | 326 | 308 |
| lines | 843 | 596 |

There is no target slot count and no expected relationship to any other arm, project or
replicate; these are observations of what four source documents totalling 35,920 bytes
supported.

## Provenance record

Not written by this agent, by instruction: the launcher writes the live provenance record
for this run. The command the run's specification names is

```bash
poetry run d4d provenance record --project CHORUS --method claudecode_agent \
  --label 2026-08-11_claude-opus-5-claudecode-generic_rep3 \
  --input-bundle data/preprocessed/concatenated/CHORUS_preprocessed.txt
```

Reasoning effort is not asserted anywhere in these artifacts: this run was not launched
with a named effort that the agent can observe, so the honest outcome is for the recorder
to leave the field absent and name the gap, per #397.
