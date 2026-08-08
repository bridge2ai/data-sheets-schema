# CHORUS full/core reconciliation

- Run label: `2026-08-07_claude-opus-5-claudecode-generic-v3_rep2`
- Arm: BASELINE (input documents only)
- Agent runtime: Claude Code — Provider: Anthropic — Model: claude-opus-5 — Reasoning effort: high
- Mode: four-phase project agent, generic prompt
- Prompt: `src/download/prompts/d4d_generic_arm_prompt.md`
- Declared input bundle: `data/preprocessed/concatenated/CHORUS_preprocessed.txt`
- Source manifest: `data/preprocessed/source_manifest.yaml`
- Full: `data/d4d_concatenated/claudecode_agent/2026-08-07_claude-opus-5-claudecode-generic-v3_rep2/CHORUS_d4d.yaml`
- Core: `data/d4d_concatenated/claudecode_agent_core/2026-08-07_claude-opus-5-claudecode-generic-v3_rep2/CHORUS_d4d_core.yaml`

## Referent

`Dataset` admits one referent. The declared bundle describes three separable things: the
CHoRUS data generation project (NIH award OT2OD032701), the CHoRUS clinical dataset it
produces, and the AIM-AHEAD Bridge2AI for Clinical Care Training Program that teaches
against that dataset.

**The pinned referent is the CHoRUS clinical care dataset** — the multicenter, multimodal
critical-care dataset described on chorus4ai.org as a "Current Released Dataset" and an
"Anticipated Final Dataset", and in the AIM-AHEAD Cohort 2 webinar as the "CHoRUS
Dataset". Project-level facts (award, pillars, consortium composition, tooling, SOPs) are
recorded only where they are properties of the dataset — its funders, creators,
collection mechanism, preprocessing, and maintenance. Training-program facts are recorded
only where they bear on dataset access: the registration form, the required licensing
agreement, and the `.edu` email requirement. The trainee stipend, travel allowance,
eligibility rules, application deadlines, and curriculum are properties of the program,
not of the dataset, and are deliberately excluded. In particular the $8,000 trainee
stipend was **not** recorded as `participant_compensation`; that slot concerns
compensation of the human subjects whose records comprise the dataset, about which the
bundle says nothing.

The referent is held identically across both records.

## Phase 3 — Source and provenance audit

### Provenance boundary

- Factual inputs read: `data/preprocessed/concatenated/CHORUS_preprocessed.txt` and
  `data/preprocessed/source_manifest.yaml`.
- Structural inputs read: `data_sheets_schema_all.yaml` (class `Dataset`) and
  `data_sheets_schema_core_all.yaml` (class `CoreDataset`), resolved through LinkML
  `SchemaView` for induced slots, ranges, cardinality, inlining and enum permissible
  values.
- Instruction files read: `.claude/agents/d4d-provenance-guard.md`,
  `.claude/commands/d4d-full-core.md`, `.claude/commands/d4d-agent.md`,
  `src/download/prompts/d4d_generic_arm_prompt.md`.
- No prior D4D record was read, opened, grepped or consulted, from any arm, label or
  date. Nothing under `data/d4d_concatenated/` was read other than this run's own two
  outputs. No `*_crate_d4d.yaml` or `*_crate_mapped_d4d.yaml` was read. No prior-D4D
  content entered this agent from the parent conversation. No evaluation report or
  reconciliation report from an earlier run was used.
- This run is a replicate. The corresponding earlier run's output was not inspected.

### Source disagreements, represented rather than resolved

1. **Admission count.** The AIM-AHEAD Cohort 2 webinar (September 2025 delivery,
   reporting status "as of August 2025") states the dataset "covers 14 different
   hospitals with over 45K unique admissions". chorus4ai.org states a "Current Released
   Dataset" of "50,000 Patient admissions from ICU, PICU, and NICU". These are the same
   quantity stated at different times, not two entities. The record carries 50,000 in
   `instances[patient admission, current released]` `counts` and records the August 2025
   figure in that instance's `source_caveats`, and again in `collection_timeframes`.
2. **Imaging.** The webinar states "currently 1000 images available with de-id in process
   for larger cohort"; the website states "7,642 Admissions with Radiology Data". These
   count different things — images versus admissions — and neither is derivable from the
   other. Both are recorded on the imaging instance, with the distinction stated in its
   `source_caveats`.
3. **Licence.** The CHoRUS GitHub organization README states "This project is licensed
   under the MIT License". That statement scopes to the GitHub organization's software.
   No source states a licence for the dataset. The top-level `license` slot is therefore
   left unset, `license_and_use_terms.license_terms` records only the signed licensing
   agreement and the `.edu` email requirement, and the scoping is stated explicitly in
   both `license_and_use_terms.source_caveats` and the record-level `source_caveats`.
   Individual repository licences (MIT, Apache-2.0) are recorded on the corresponding
   `Software` objects, where they belong.

### Corrections applied during Phase 3

Four defects were found in the Phase 1 record and corrected before Phase 4. The full
record was corrected first and the core record regenerated from it afterwards, so no
correction was applied to core independently.

| # | Slot | Defect | Correction |
|---|---|---|---|
| 1 | `funders[0].grantor` | Named Massachusetts General Hospital as part of the grantor. MGH is the recipient organization on the NIH RePORTER entry, not a funder — a misattribution. | `grantor` reduced to "National Institutes of Health (NIH) Common Fund, Bridge2AI program"; MGH moved to the `FundingMechanism.description` as recipient organization of record. |
| 2 | `title` | Read "Bridge2AI for Clinical Care Dataset (CHoRUS)", a composite of two separate slide headers presented as one title. | Set to the verbatim slide header "Bridge2AI for Clinical Care Dataset". `name` remains "CHoRUS Dataset", the other verbatim header. |
| 3 | `external_resources[CHoRUS project website].restrictions[0]` | Presented a normalised quotation as verbatim; the source text reads "This repoitory is under review…" (sic). | Rewritten as reported speech rather than a quotation, so no altered text is presented inside quotation marks. |
| 4 | `maintainers[0].maintainer_details` | Carried the evidence annotation "as printed on the site" inside the value, duplicating the object's own `source_caveats`. | Annotation removed from the value; it remains in `source_caveats`, which is its designated home. |

### Shape and slot-filling audit

- Structured slots are filled before prose: `principal_investigator`, `affiliations`,
  `grants`/`grant_number`, `counts`, `instance_type`, `start_date`/`end_date`,
  `limitation_type`, `confidentiality_level`, `role`, `contribution_url`,
  `used_software`, `examples`, `special_populations`, `special_protections` all carry
  their content structurally rather than in narrative.
- No prose sits in a slot whose range is a list, and no list carries a paragraph that
  belongs in `description`.
- Enum values used are all schema-declared: `limitation_type` ∈ {`coverage_limitation`,
  `scope_limitation`} (LimitationTypeEnum); `confidentiality_level` = `restricted`
  (ConfidentialityLevelEnum); `maintainers[0].role` = `academic_institution`
  (CreatorOrMaintainerEnum). `DataCollector.role` has range `string` and carries free
  text, as the schema permits.
- `credit_roles`, `data_use_permission` and `hipaa_compliant` were left unset. Each would
  have required mapping an unstated fact onto a controlled vocabulary: the sources state
  no CRediT roles, no DUO permission, and no HIPAA determination for the dataset (HIPAA
  appears only as the subject of a training-curriculum module, which is not a compliance
  statement about this dataset).
- `notes` is unused anywhere in either record. All evidence commentary — source conflicts,
  transcription decisions, unanswered questions — is in `source_caveats`, at record level
  and on seven nested objects.
- No commentary is embedded in any name, identifier, or affiliation value.
- No sibling slot's value is restated within the same object.
- `contact_person` and `principal_investigator` have range `Person`, which the schema
  treats as a non-inlined reference; they carry name strings, matching the slot
  description ("a person's name such as 'Aaron Lee'"). Inlined `Person` objects were
  rejected by schema validation and were replaced.

### Deliberate omissions

Slots left unset because the bundle does not support them, rather than by oversight:
`license`, `doi`, `version`, `download_url`, `issued`, `created_on`, `last_updated_on`,
`publisher`, `language`, `citation`, `is_tabular`, `compression`, `file_collections`,
`total_file_count`, `total_size_bytes`, `resources`, `parent_datasets`,
`related_datasets`, `anomalies`, `known_biases`, `content_warnings`,
`collection_notifications`, `collection_consents`, `consent_revocations`,
`informed_consent`, `participant_compensation`, `imputation_protocols`,
`annotation_analyses`, `machine_annotation_tools`, `use_repository`, `discouraged_uses`,
`prohibited_uses`, `distribution_dates`, `ip_restrictions`, `errata`, `retention_limit`,
`variables`.

Four of these deserve a note:

- **`known_biases`** — the sources describe *mitigation* of bias ("sampling methods to
  ensure a balanced and diverse cohort", "approaches to manage privacy and bias") but
  document no specific bias. Asserting a `BiasTypeEnum` value would have been an
  invention; the mitigation content is recorded under `sampling_strategies` instead.
- **`is_deidentified.identifiable_elements_present`** — the object is populated with
  `method` and `deidentification_details`, but the boolean is unset. The sources describe
  de-identification as in progress for imaging and note-text retention at sites, and do
  not state whether identifiable elements remain in the released data.
- **`is_tabular`** — the dataset is 1.6 billion rows of OMOP alongside DICOM imaging,
  WFDB and EDF+ waveforms, and tokenized text. Neither boolean value is true of it.
- **`total_size_bytes`** — the website prints "23 Tb Waveform data". Converting requires
  assuming both the unit (terabytes vs terabits) and the base; the figure is transcribed
  verbatim into the waveform instance's `description` instead.

### Internal consistency checks

Repeated facts were checked for agreement within each file and across the pair: award
number OT2OD032701 and project number 1OT2OD032701-01; project period 2022-09-01 to
2026-11-30 (appearing in `funders` and `collection_timeframes`); 14 data-contributing
hospitals and 20 academic centers (in `description`, `creators`, `collection_mechanisms`,
`sampling_strategies`, `updates`); 50,000 / 100,000 admissions (in `description`,
`instances`, `known_limitations`, `version_access`, `updates`); the nine data types and
their standards (in `instances`, `distribution_formats`, `missing_data_documentation`);
controlled access (in `confidential_elements`, `regulatory_restrictions`,
`distribution_formats`, `instances`). No disagreement was found.

### Re-validation after correction

Both files were re-validated after every correction. Results are in the commands section
below; all four validations pass.

## Phase 4 — Strict full/core reconciliation

### Schema-derived shared slots

Shared slots were derived at runtime from `Dataset` (full schema) and `CoreDataset` (core
schema) with LinkML `SchemaView`, comparing each slot's induced range, multivalued,
required, minimum/maximum cardinality and `inlined_as_list`. No hand-written field list
was used.

- **Schema-identical shared slots: 78.** Every one is present in both records or absent
  from both, with deeply identical parsed YAML — including narrative fields, which core
  does not condense, paraphrase or reorder.
- **Projected shared slots: 1** — `resources`, whose range is `Dataset` in full and
  `CoreDataset` in core. It is absent from both records, so the projection is empty and
  coverage is trivially equal.
- **Populated shared slots: 47** of the 78. These are exactly the 47 top-level slots of
  the core record.
- **Full-only populated slots: 6** — `relationships`, `splits`, `subsets`,
  `direct_collection`, `participant_privacy`, `third_party_sharing`. None of these exists
  in `CoreDataset`, so their absence from core is required by the schema, not a
  divergence.
- **Core-only slots: 2** — `distributions` (`CoreDistribution[]`) and `dialect`
  (`FormatDialect`). Both are unpopulated; see the related-content review below.

The core record was produced by projecting the Phase 3-corrected full record onto the
`CoreDataset` slot inventory derived from `SchemaView`, so deep identity holds by
construction and was then verified independently.

### Related, non-identical content — semantic review

The validator's projection rules do not cover semantically related fields with different
representations. Each was reviewed by hand:

| Relation | Finding |
|---|---|
| full `file_collections` → core `distributions` | Both absent. The bundle contains no file inventory, no paths, no checksums, no per-file byte counts. Nothing to map; no conflict possible. |
| `total_file_count` / `total_size_bytes` vs distribution-level counts | All absent in both records. The only volume figure in the bundle ("23 Tb") is unit-ambiguous and was not converted. Consistent. |
| `dialect` (core-only) / formats / `is_tabular` | `dialect` describes a tabular delimiter/quoting convention and is unsupported by the bundle; `is_tabular` is unset in both for the reason given above. `distribution_formats` is a schema-identical slot and is deeply identical across the pair: five entries (OMOP CDM, OHNLP, DICOM, WFDB, EDF+/Persyst). No conflict between the format statements and the unset `dialect`/`is_tabular`. |
| Top-level identity/version/access vs resources, version history, distributions | `resources` absent in both; no version history object beyond `version_access`, which is schema-identical and deeply equal. Top-level `status`, `page`, `conforms_to` agree with `version_access.version_details`, `regulatory_restrictions`, and `license_and_use_terms` in both files. |
| Historical vs current release | The August 2025 webinar snapshot and the website's current released figures are treated as one dataset described at two times, not as a contradiction. Both records carry both, in the same slots, with the same `source_caveats` text. |

Zero unresolved contradictions within either record or between the two.

### Divergences

**None.** After the four Phase 3 corrections were applied to the full record and core was
regenerated from it, no divergence remained between the pair. `--sync-core` was not
needed and was not run; the validator was run only in its independent checking mode.

## Files changed

- `data/d4d_concatenated/claudecode_agent/2026-08-07_claude-opus-5-claudecode-generic-v3_rep2/CHORUS_d4d.yaml` (created Phase 1, corrected Phase 3)
- `data/d4d_concatenated/claudecode_agent_core/2026-08-07_claude-opus-5-claudecode-generic-v3_rep2/CHORUS_d4d_core.yaml` (created Phase 2, regenerated from the corrected full record in Phase 3)
- `data/d4d_concatenated/claudecode_agent_core/2026-08-07_claude-opus-5-claudecode-generic-v3_rep2/CHORUS_reconciliation.md` (this file)

No file outside these three was written.

## Commands and results

```bash
poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_all.yaml \
  -C Dataset data/d4d_concatenated/claudecode_agent/2026-08-07_claude-opus-5-claudecode-generic-v3_rep2/CHORUS_d4d.yaml
# No issues found

poetry run linkml-term-validator validate-data \
  data/d4d_concatenated/claudecode_agent/2026-08-07_claude-opus-5-claudecode-generic-v3_rep2/CHORUS_d4d.yaml \
  --schema src/data_sheets_schema/schema/data_sheets_schema_all.yaml --target-class Dataset
# Validation passed

poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml \
  -C CoreDataset data/d4d_concatenated/claudecode_agent_core/2026-08-07_claude-opus-5-claudecode-generic-v3_rep2/CHORUS_d4d_core.yaml
# No issues found

poetry run linkml-term-validator validate-data \
  data/d4d_concatenated/claudecode_agent_core/2026-08-07_claude-opus-5-claudecode-generic-v3_rep2/CHORUS_d4d_core.yaml \
  --schema src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml --target-class CoreDataset
# Validation passed

poetry run python -m data_sheets_schema.d4d_pair_consistency \
  --full data/d4d_concatenated/claudecode_agent/2026-08-07_claude-opus-5-claudecode-generic-v3_rep2/CHORUS_d4d.yaml \
  --core data/d4d_concatenated/claudecode_agent_core/2026-08-07_claude-opus-5-claudecode-generic-v3_rep2/CHORUS_d4d_core.yaml
# PASS: 78 schema-identical slots; projected slots=['resources']

poetry run d4d provenance record --project CHORUS --method claudecode_agent \
  --label 2026-08-07_claude-opus-5-claudecode-generic-v3_rep2 \
  --input-bundle data/preprocessed/concatenated/CHORUS_preprocessed.txt \
  --prompt src/download/prompts/d4d_generic_arm_prompt.md

poetry run d4d runs validate --label 2026-08-07_claude-opus-5-claudecode-generic-v3_rep2 --project CHORUS

poetry run d4d runs check --strict --label 2026-08-07_claude-opus-5-claudecode-generic-v3_rep2
```

## Outcome

| Metric | Value |
|---|---|
| Full top-level populated slots | 53 |
| Core top-level populated slots | 47 |
| Schema-identical shared slots | 78 |
| Projected shared slots | 1 (`resources`, absent from both) |
| Full schema validation | pass |
| Full term validation | pass |
| Core schema validation | pass |
| Core term validation | pass |
| Pair consistency | PASS |
| Phase 3 corrections | 4 (all applied to full, then core regenerated) |
| Unresolved divergences | 0 |
