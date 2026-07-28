# CHORUS full/core reconciliation — 2026-07-28_claude-opus-5-deprimed_rep2

- Project: CHORUS
- Version label: `2026-07-28_claude-opus-5-deprimed_rep2`
- Arm: BASELINE (input documents only)
- Agent runtime: Claude Code; Provider: Anthropic; Model: `claude-opus-5[1m]`
- Mode: four-phase project agent, de-primed; Temperature 0.0
- Full: `data/d4d_concatenated/claudecode_agent/2026-07-28_claude-opus-5-deprimed_rep2/CHORUS_d4d.yaml`
- Core: `data/d4d_concatenated/claudecode_agent_core/2026-07-28_claude-opus-5-deprimed_rep2/CHORUS_d4d_core.yaml`

## Declared inputs

| Role | Path |
|---|---|
| Factual source bundle | `data/preprocessed/concatenated/CHORUS_preprocessed.txt` (4 documents, 1699 lines) |
| Provenance manifest | `data/preprocessed/source_manifest.yaml` (CHORUS block only) |
| Full structure authority | `src/data_sheets_schema/schema/data_sheets_schema_all.yaml`, class `Dataset` |
| Core structure authority | `src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml`, class `CoreDataset` |
| Phase 2 additional input | the same-run Phase 1 full record (path above) |

Manifest-selected CHORUS documents used as the only factual sources:

1. `nih_reporter_project` — NIH RePORTER project page, <https://reporter.nih.gov/project-details/10472824>
2. `cohort_2_webinar` — AIM-AHEAD Bridge2AI for Clinical Care cohort 2 informational webinar (tutorial)
3. `project_documentation` — <https://chorus4ai.org/>
4. `github_organization_overview` — <https://github.com/chorus-ai>, historical documentation captured 2025-11-14, retained by explicit curation note in the manifest

## Phase 3 — Source and provenance audit

### Provenance boundary

- No prior full or core D4D record was read, opened, grepped, or listed for content in
  any phase. The only directory listing performed under `data/d4d_concatenated/` was of
  directory **names**, to confirm that the target version label did not already exist;
  no file inside any prior version directory was opened.
- No evaluation report, reconciliation report, test fixture, schema `d4d:docExample`
  value, or model memory was used as a factual source.
- No live web content was fetched. This is a BASELINE arm run.
- Record structure was derived at runtime from the LinkML schemas with `SchemaView`
  (induced slots, ranges, cardinality, inlining, enum permissible values), not from any
  example record. Three structural facts derived this way and confirmed by validation:
  `Creator.principal_investigator`, `FundingMechanism.grantor` and
  `LicenseAndUseTerms.contact_person` are **references** (plain identifier strings), not
  inlined objects; `ExternalResource.future_guarantees` and `.restrictions` are
  multivalued.
- Source 4 is historical documentation (captured 2025-11-14). It is admissible because
  the current manifest explicitly selects it and records the curation rationale. Its
  content is used only for repository, SOP, standards, contributor-role and
  software-tooling detail, consistent with that rationale.

### Cross-source resolution

| Fact | Source disagreement | Resolution |
|---|---|---|
| Admission count | Website "Current Released Dataset: 50,000 patient admissions"; webinar "As of August 2025 … over 45K unique admissions"; NIH abstract "more than 100,000 critically ill patients"; website "Anticipated Final Dataset: 100,000" | Not a contradiction — three different scopes. `instances.counts = 50000` records the current released figure; the 45K August-2025 snapshot and the 100,000 anticipated/target figure are stated with their scope in `instances`, `status`, `known_limitations`, `version_access`, `collection_timeframes` and `distribution_dates`. |
| Number of centers | "14 data contributing hospitals" (website); "20 academic centers, of which 14 will contribute as Data Acquisition centers" (GitHub) | Consistent: 20-centre collaboration, 14 contributing sites. Both figures are carried together everywhere they appear. |
| Data modalities | Website "9 Different data modalities"; webinar table lists 9 data-type rows | Consistent. The nine data types are grouped into five `file_collections` (the five OMOP-standardized EHR types form one collection); the top-level `description` enumerates all nine. |
| Licensing | GitHub README "This project is licensed under the MIT License"; webinar "All participants must sign a licensing agreement" | Scope-separated. Top-level `license` is deliberately **left unset**: MIT/Apache-2.0 govern the CHoRUS software repositories, not the dataset. `license_and_use_terms` states both facts with their scope and records that no public dataset licence identifier is given. |
| Compensation | Webinar "$8,000 stipend" | Belongs to the AIM-AHEAD training programme trainees, not to research participants. `participant_compensation` is correctly **absent**; the stipend is not asserted anywhere. |
| HIPAA / GDPR | Webinar curriculum topic "HIPAA/GDPR compliance for OMOP/FHIR data" | Training-curriculum content, not a compliance statement about the dataset. `regulatory_restrictions.hipaa_compliant` is deliberately **unset**, with the reason recorded in that object's `description`. |

### Corrections applied during the audit

1. **Fabricated identifier removed.** The `Software` entry for the OHNLP toolkit had been
   given the id `https://github.com/chorus-ai#ohnlp-toolkit`, which implies the toolkit is
   hosted in the chorus-ai GitHub organization. The sources do not support that. Changed to
   the non-URL identifier `d4d:CHORUS_software_ohnlp_toolkit`. Full record corrected first,
   then core regenerated from the corrected full record and re-validated.
2. **Cardinality fixes** in `external_resources`: `future_guarantees` and `restrictions`
   converted from scalars to lists per the induced schema. Caught by `linkml-validate`.

No other fact required correction, and Phase 2 discovered no source-supported fact that
was missing from the full record, so no back-port to full was needed beyond item 1.

### Explicitly flagged inferences (source-grounded but not verbatim)

These are recorded here rather than silently absorbed:

- `is_tabular: false` — inferred from the nine-modality composition (DICOM imaging, WFDB
  and EDF+/Persyst waveforms alongside tabular OMOP data). The sources do not use the word
  "tabular".
- `creators[0].credit_roles` (`supervision`, `project_administration`,
  `funding_acquisition`) — inferred from the explicit NIH RePORTER designation of
  Eric S. Rosenthal as Principal Investigator. No CRediT roles are stated in the sources;
  no roles are assigned to any other named individual.
- `license_and_use_terms.data_use_permission` (`health_medical_biomedical_research`,
  `user_specific`) — a DUO mapping of the described access process. The mapping rationale
  is written into that object's `description` rather than presented as a source statement.
- `known_biases` (`representation_bias`) — the sources frame bias management as an ongoing
  patient-focused effort and do not assert a measured bias. The entry is phrased to record
  exactly that, with the sampling and SDOH mitigations quoted from the sources.
- GitHub repository URLs of the form `https://github.com/chorus-ai/<repo>` — mechanically
  derived from the org URL plus the repository names listed on the captured org page.
- `CTP-deid` placed under de-identification preprocessing on the basis of its repository
  name; the source listing gives no description, and the record says so explicitly.
- `id: https://chorus4ai.org/` — no DOI, accession, or persistent identifier for the
  dataset appears in any source, so the project website URL is used as the identifier.

### Deliberate omissions (unknown in the bundle)

`doi`, `version`, `license`, `publisher`, `created_by`, `created_on`, `issued`,
`last_updated_on`, `download_url`, `language`, `citation`, `compression`,
`anomalies`, `content_warnings`, `imputation_protocols`, `annotation_analyses`,
`use_repository`, `discouraged_uses`, `prohibited_uses`, `informed_consent`,
`collection_notifications`, `collection_consents`, `consent_revocations`,
`participant_compensation`, `ip_restrictions`, `errata`, `retention_limit`,
`variables`, `parent_datasets`, `related_datasets`, `resources`,
`total_file_count`, `total_size_bytes`, and per-collection `file_count` / `total_bytes`.

`23 Tb` of waveform data is reported as prose in `file_collections`, `version_access` and
the top-level `description` rather than converted to a `total_bytes` integer, because the
source does not disambiguate decimal from binary units.

### Validation after Phase 3

```bash
poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_all.yaml -C Dataset \
  data/d4d_concatenated/claudecode_agent/2026-07-28_claude-opus-5-deprimed_rep2/CHORUS_d4d.yaml
poetry run linkml-term-validator validate-data \
  data/d4d_concatenated/claudecode_agent/2026-07-28_claude-opus-5-deprimed_rep2/CHORUS_d4d.yaml \
  --schema src/data_sheets_schema/schema/data_sheets_schema_all.yaml --target-class Dataset
poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml -C CoreDataset \
  data/d4d_concatenated/claudecode_agent_core/2026-07-28_claude-opus-5-deprimed_rep2/CHORUS_d4d_core.yaml
poetry run linkml-term-validator validate-data \
  data/d4d_concatenated/claudecode_agent_core/2026-07-28_claude-opus-5-deprimed_rep2/CHORUS_d4d_core.yaml \
  --schema src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml --target-class CoreDataset
```

All four: `No issues found` / `✅ Validation passed`.

## Phase 4 — Strict full/core reconciliation

### Schema-derived shared slots

`CoreDataset` has **79** induced slots. **52** of them are populated in the full record and
were carried into core; core additionally carries the projected `distributions` slot, for
**53** populated core top-level slots against **59** populated full top-level slots.

Core was produced by mechanical projection from the validated Phase 1 full record, so
every schema-identical slot is byte-for-byte the same parsed structure — no condensing,
paraphrasing, reordering, or omission. The deterministic validator confirms this:

```
PASS: 76 schema-identical slots; projected slots=['resources']
```

(76 counts every schema-identical slot compared, including those absent from both records;
absence is required to match, and it does.)

### Full-only slots (absent from `CoreDataset` by schema)

`file_collections`, `subsets`, `relationships`, `splits`, `direct_collection`,
`participant_privacy`, `third_party_sharing`.

None of these are droppable content losses that create a contradiction:

- `subsets` (the holdout test set) and `splits` — the same fact is carried in core through
  `purposes` (`…_purpose_holdout_validation`) and `tasks` (`…_task_external_validation`),
  which are identical in both records. Core has no `subsets` or `splits` slot. The holdout
  set was deliberately **not** smuggled into core `resources`, since `resources` must have
  equal coverage across the pair and full has none.
- `direct_collection` (`is_direct: false`) — reinforced in core by
  `acquisition_methods[0].acquisition_details` and `raw_data_sources`, which state that
  data are extracted retrospectively from hospital clinical systems. No conflict.
- `participant_privacy` — its content is echoed in core by `is_deidentified`,
  `confidential_elements`, `sensitive_elements` and `at_risk_populations.special_protections`,
  all identical across the pair. No conflict.
- `third_party_sharing` (`is_shared: true`) — consistent with core `distribution_formats`,
  `existing_uses` and `license_and_use_terms`, which describe controlled external access.
- `relationships` — admission-level linkage; no core counterpart and no conflicting claim.

### Projection: `file_collections` → `distributions`

The validator reports `deterministic matches=5, unmatched core distributions=[]` and raises
the mandatory `semantic-review-required` warning. The semantic review required by step 4
was performed and is recorded here.

| Full `file_collections[].id` | Core `distributions[].id` | Name / description | Formats and standards |
|---|---|---|---|
| `d4d:CHORUS_fc_omop_structured_ehr` | `d4d:CHORUS_dist_omop_structured_ehr` | identical | OMOP CDM (+ CHoRUS extensions for nursing flowsheets) |
| `d4d:CHORUS_fc_clinical_notes` | `d4d:CHORUS_dist_clinical_notes` | identical | OHNLP open source schema |
| `d4d:CHORUS_fc_imaging` | `d4d:CHORUS_dist_imaging` | identical | DICOM |
| `d4d:CHORUS_fc_waveform_telemetry` | `d4d:CHORUS_dist_waveform_telemetry` | identical | WFDB, PhysioNet schema extended |
| `d4d:CHORUS_fc_waveform_eeg` | `d4d:CHORUS_dist_waveform_eeg` | identical | EDF+ and Persyst |

Review findings:

- `name` and `description` are character-identical between each pair; ids differ only by the
  `_fc_` → `_dist_` marker so the schema object type is legible from the identifier.
- `CoreDistribution.format` (enum: CSV, TSV, XML, JSON, JSONL, YAML, HTML, PDF, DOCX, XLSX,
  PPTX, TXT, MD, ZIP, TAR, GZ, BZ2, XZ) admits none of DICOM, WFDB, EDF+, Persyst or OMOP,
  so `format` is omitted rather than approximated. The standards are stated in the
  descriptions, and in full also in `conforms_to` / `conforms_to_schema` on each collection.
  This is an expressiveness gap in the core enum, not a disagreement between the records.
- `path`, `bytes`, `hash`, `md5`, `sha256`, `encoding`, `compression`, `media_type` are
  omitted in core because no source states them; the corresponding full slots (`path`,
  `total_bytes`, `file_count`, `compression`) are likewise absent. Presence is consistent.
- `total_file_count` and `total_size_bytes` are absent from full, so there is no aggregate
  to compare against distribution-level values. No scope mismatch is possible.
- `is_tabular: false` is identical in both records and agrees with the distribution mix
  (imaging and waveform collections alongside tabular OMOP data).
- `dialect` (core-only, `FormatDialect`) is omitted: it describes delimited-text parameters
  (delimiter, quote char, header, comment prefix) that no source states and that do not
  apply to a DICOM/WFDB/EDF+ collection.
- Access scope agrees across the pair: every collection description says "controlled
  access", matching `license_and_use_terms`, `regulatory_restrictions.confidentiality_level:
  restricted`, and `confidential_elements`, all of which are identical in both records.
- Release scope agrees: the current-release figures (50,000 admissions; 1.6 billion OMOP
  rows; 7,642 admissions with radiology; 23 Tb waveform) and the August-2025 snapshot
  (over 45,000 admissions; ~1,000 images; EEG extraction in process) appear with the same
  wording and the same scope labels in `description`, `status`, `instances`,
  `known_limitations`, `version_access` and `distribution_dates` in both records.

### Identity, version and access cross-checks

- Award identifiers are internally consistent everywhere they appear in both records:
  `1OT2OD032701-01` (project number, used as `grant_number`), `OT2OD032701` (core project
  number), application ID `10472824`, FY2022, award amount 5,880,300, period
  2022-09-01 → 2026-11-30. The project period in `funders` matches `collection_timeframes`
  `start_date`/`end_date` and the `updates.frequency` statement.
- No dataset `version` or `doi` is asserted in either record, so there is nothing to
  contradict `version_access`, which describes the current release and the anticipated final
  release as two scoped states rather than as conflicting values.
- Contacts are consistent: `license_and_use_terms.contact_person` references
  `d4d:CHORUS_person_jared_houghtaling`, one of the two access contacts listed by the
  GitHub organization; the maintainer entries carry the programme-manager and access
  contact addresses as printed in the sources (including the website's `havard` spelling,
  reproduced with an explicit note).

### Commands run in Phase 4

```bash
poetry run python -m data_sheets_schema.d4d_pair_consistency \
  --full data/d4d_concatenated/claudecode_agent/2026-07-28_claude-opus-5-deprimed_rep2/CHORUS_d4d.yaml \
  --core data/d4d_concatenated/claudecode_agent_core/2026-07-28_claude-opus-5-deprimed_rep2/CHORUS_d4d_core.yaml
```

`--sync-core` was **not** needed: core is generated by projection from the canonical full
record, so it was already in sync on first run. The command above was therefore run only in
its independent-check form, and passed.

Schema and term validation were re-run for both records after the Phase 3 correction and
after the core header update; all four checks pass (commands listed in the Phase 3 section).

### Outcome

**No divergence between the full and core records.** Every schema-identical shared slot is
present in both or absent from both and deeply identical in parsed content. The single
projected relationship (`file_collections` → `distributions`) was mapped one-to-one and
semantically reviewed with zero unresolved contradictions. The only Phase 3 factual
correction (the fabricated OHNLP identifier) was applied to the full record first and
propagated to core by regeneration.

## Files written by this run

- `data/d4d_concatenated/claudecode_agent/2026-07-28_claude-opus-5-deprimed_rep2/CHORUS_d4d.yaml`
- `data/d4d_concatenated/claudecode_agent_core/2026-07-28_claude-opus-5-deprimed_rep2/CHORUS_d4d_core.yaml`
- `data/d4d_concatenated/claudecode_agent_core/2026-07-28_claude-opus-5-deprimed_rep2/CHORUS_reconciliation.md`
- `data/d4d_concatenated/claudecode_agent_core/2026-07-28_claude-opus-5-deprimed_rep2/CHORUS_provenance.yaml` (live provenance record)
