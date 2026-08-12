# AI_READI full/core reconciliation

- **Run label:** `2026-08-11_claude-opus-5-claudecode-generic_rep3`
- **Arm:** BASELINE (input documents only)
- **Mode:** four-phase project agent, generic prompt
- **Runtime / provider / model:** Claude Code / Anthropic / claude-opus-5
- **Declared input bundle:** `data/preprocessed/concatenated/AI_READI_preprocessed.txt`
- **Manifest:** `data/preprocessed/source_manifest.yaml`
- **Full record:** `data/d4d_concatenated/claudecode_agent/2026-08-11_claude-opus-5-claudecode-generic_rep3/AI_READI_d4d.yaml`
- **Core record:** `data/d4d_concatenated/claudecode_agent_core/2026-08-11_claude-opus-5-claudecode-generic_rep3/AI_READI_d4d_core.yaml`

## Referent

`Dataset` admits one referent. The referent chosen is **the AI-READI dataset,
version 3.0.0, DOI `https://doi.org/10.60775/fairhub.3`** — the release the
FAIRhub API record, the v3 documentation page, the v3 FAIRhub landing page and
the v3 healthsheet all describe. This matches the manifest declaration
(`referent_id: https://doi.org/10.60775/fairhub.3`), whose `referent_note`
states that fairhub.1 and fairhub.2 are earlier releases of the same dataset
rather than separate datasets. Both records carry that same `id`, and versions
1.0.0 and 2.0.0 are represented through `version_access` (both records) and
`related_datasets` (full only, `is_new_version_of`) rather than as separate
dataset entities.

`d4d download scope --check --project AI_READI` reports the record in scope: it
does not identify itself as a dataset the manifest declares distinct.

## Phase 3 — source and provenance audit

### Provenance

No prior generated D4D record was read, searched, or cited. The complete set of
inputs opened during this run was: the launch specification
(`/tmp/d4d_launch/AI_READI_rep3.txt`), `.claude/agents/d4d-provenance-guard.md`,
`.claude/commands/d4d-full-core.md`, `.claude/commands/d4d-agent.md`, the
declared bundle, the manifest `scope:` block (via `d4d download scope`), the
full and core LinkML schemas (via `SchemaView`), and
`src/data_sheets_schema/provenance.py` (read to establish how slot counts are
measured, not for facts). Nothing under `data/d4d_concatenated/`,
`data/d4d_individual/` or `data/ro-crate_packages/` was opened, apart from the
two files this run itself wrote. Phase 2 read the exact same-run Phase 1 full
record, whose path carries this run's version label.

### Source disagreements identified and how each is represented

None was silently resolved; each is recorded in the applicable
`source_caveats` slot so that both readings survive in the record.

| # | Disagreement | Representation |
|---|---|---|
| 1 | **Project name.** BMJ Open and Nature Metabolism expand AI-READI as "Artificial Intelligence Ready and **Equitable** Atlas for Diabetes Insights"; NIH RePORTER, the FAIRhub healthsheet and the README expand it as "…**Exploratory** Atlas…"; the FAIRhub `studyDescription.officialTitle` is "AI Ready and Exploratory Atlas for Diabetes Insights". | All three in top-level `source_caveats`; `description` names both the Equitable and Exploratory expansions. |
| 2 | **Responsible organization.** FAIRhub records the managing organization and lead sponsor as *Washington University in St. Louis* (ROR `01yc7t268`); NIH RePORTER gives the awardee as *University of Washington*; the licence agreement names the University of Washington as Licensor; the IRB of record is the University of Washington. | Top-level `source_caveats`; `data_governance.accountable_organization` carries the FAIRhub value with its own `source_caveats`; the Aaron Y. Lee creator entry carries the same caveat. Neither value substituted for the other. |
| 3 | **De-identification.** FAIRhub records `deIdentType: NoDeIdentification` with the explanation that no identifiers were collected; Nature Metabolism describes the public set as stripped of PHI via HIPAA Safe Harbor. | Both recorded in `is_deidentified.source_caveats` and `participant_privacy[0].source_caveats`. |
| 4 | **Licence version.** The licence *text* in the bundle is AI-READI-LICENSE-v1.0 (UW Data License Agreement, Zenodo 10642459). FAIRhub records the rights for v3.0.0 as "AI-READI custom license v2.0" (`10.5281/zenodo.17555036`), whose text is **not** in the bundle. | `license` and `license_and_use_terms.name` carry v2.0 (the operative statement for this release). Every term transcribed from the v1.0 text — `license_and_use_terms.license_terms`, `ip_restrictions`, three `prohibited_uses` entries — carries a `source_caveats` naming its v1.0 provenance and stating it may not be operative for this release. |
| 5 | **Per-version participant counts.** Healthsheet: v1 204, v2 +863 → 1067 cumulative, v3 2280. README table: "v1.0.0 pilot" 204, "year 2 data" 863, "year 3 data" 1213, "v3.0.0 main study" 2280. | `version_access.source_caveats`, noting the two are arithmetically compatible (204+863+1213=2280) but label the middle column differently, and that the healthsheet elsewhere calls v3 "data collected up through the end of the second year". |
| 6 | **Collection start date.** BMJ Open: enrolment began 18 July 2023. FAIRhub/healthsheet/README: 19 July 2023. | `collection_timeframes[0].source_caveats`; `start_date` uses the dataset's own metadata value `2023-07-19`. |
| 7 | **Target enrolment.** BMJ Open, Nature Metabolism, NIH RePORTER, README and the FAIRhub study description give 4,000; the UW IRB protocol gives 4,600 twice while its own per-group table lists 1,000 × 4 = 4,000. | `sampling_strategies[0].source_caveats`. |
| 8 | **Longitudinal sub-cohort size.** Healthsheet: ~4% return in Year 4. NIH RePORTER, FAIRhub study description and IRB protocol: 10%. | `known_limitations` "Single cross-sectional visit per participant" `source_caveats`. |
| 9 | **Grant number transcription.** Healthsheet writes `OT2ODO32644`; RePORTER, FAIRhub and both publications write `OT2OD032644`. | `funders[0].source_caveats`; the record uses `OT2OD032644`. |
| 10 | **IRB vs trial registration.** The BMJ Open abstract labels `STUDY00016228` a "Clinicaltrials.org approval number"; the body of the same paper and the healthsheet call it the UW IRB approval number, and the trial registration is `NCT06002048`. | `ethical_reviews[0].source_caveats`. |
| 11 | **Demographic sub-populations.** The healthsheet answers "No" to identifying demographic sub-populations; the README tabulates race/ethnicity, sex and diabetes-status counts for the recommended splits. | `subpopulations[0].source_caveats`, with both the "No" answer (`identification`) and the counts (`distribution`) recorded. |
| 12 | **Sampling framing.** The healthsheet says the dataset "contains all possible instances" and answers "N/A" on sampling strategy; the FAIRhub study description records `samplingMethod: Non-Probability Sample`. | `sampling_strategies[0].source_caveats`. |

### Corrections made during Phase 3

Six edits were applied to the full record and the core record was regenerated
from the corrected full record afterwards.

1. **`sampling_strategies[0].source_data` — ICD-10 codes.** The Phase 1 draft
   wrote "ICD-10 diagnosis codes E11.X and R73.09 respectively" for "patients
   with T2DM and pre-diabetes", silently inverting the source's stated ordering
   to the clinically expected one. The BMJ Open protocol literally reads
   "…patients with T2DM and pre-diabetes are identified by screening electronic
   health records for ICD-10 diagnosis codes R73.09 and E11.X, respectively."
   Corrected to transcribe the codes in the source's order without asserting the
   mapping, with the discrepancy named in `source_caveats`. This is the one place
   where the Phase 1 draft had substituted a judgement for the evidence.
2. **Top-level `source_caveats` — project name.** Widened from two expansions to
   three, and the third variant re-attributed: the FAIRhub *study description*
   gives "AI Ready and Exploratory Atlas…", while the *healthsheet* and README
   give "Artificial Intelligence Ready and Exploratory Atlas…".
3. **`sampling_strategies[0].source_caveats`** — added disagreement #7 (target
   enrolment) and the ICD-code ordering note.
4–6. **`prohibited_uses`** — a pseudo-entry carrying only a `name` and a
   `source_caveats` (a shape defect: an entry in a list of prohibitions that was
   not a prohibition) was removed, and its licence-version scoping moved onto
   each of the three licence-derived prohibition entries as their own
   `source_caveats`.

No Phase 2 discovery required back-porting: the core record is a projection of
the Phase 1 full record, and re-reading the bundle for the core-only slots
(`distributions`, `dialect`, `resources`) surfaced no fact the full record was
missing. `dialect` and `resources` remain absent in core because the bundle
states no CSV dialect and the full record declares no nested `resources`.

### Internal consistency checks

- **File counts.** `total_file_count: 356343` (FAIRhub). The nine datatype
  `file_collections` sum to **356,334**; the root `metadataFileList` holds
  **9** entries (CHANGELOG.md, dataset_description.json,
  dataset_structure_description.json, healthsheet.md, LICENSE.txt,
  participants.json, participants.tsv, README.md, study_description.json).
  356,334 + 9 = 356,343 — exact. The root-metadata collection is recorded with
  `file_count: 9` and a `source_caveats` stating that 9 is the number of
  manifest entries rather than a count the bundle asserts.
- **Byte totals.** `total_size_bytes: 3815969779678` (FAIRhub, = "3.82 TB"). The
  nine directory `total_bytes` sum to **3,815,969,360,064**, leaving
  **419,614 bytes** unattributed — consistent with the nine root metadata files,
  for which the bundle states no size. `total_bytes` is therefore left absent on
  that collection rather than back-computed.
- **Split arithmetic.** 1576 + 352 + 352 = 2280 = `instances[0].counts`.
  Race/ethnicity totals 380+545+519+836 = 2280; sex 951+1329 = 2280; diabetes
  status 776+560+686+258 = 2280. Per-split race/ethnicity, sex and diabetes rows
  each sum to their split total. All consistent.
- **Version facts.** `id`, `doi`, `version`, `issued` and
  `version_access.latest_version_doi` all agree on v3.0.0 / `10.60775/fairhub.3`
  / 2025-11-17. `distribution_dates.release_dates`
  (2024-05-03, 2024-11-08, 2025-11-17) agree with `version_access.version_details`.
- **Licence facts.** `license`, `license_and_use_terms.name` and the licence DOI
  cited across `discouraged_uses`, `ip_restrictions` and `regulatory_restrictions`
  all name v2.0 at `10.5281/zenodo.17555036`.
- **Identifiers.** Every ORCID, ROR, DOI, NIH award, ClinicalTrials.gov and URL
  value in both records was matched back to a literal occurrence in the bundle.

### Shape audit

- No prose stands where the schema requires a list, and no list value carries
  embedded commentary. Multivalued slots (`irb_approval`,
  `regulatory_compliance`, `restrictions`, `regulatory_restrictions`,
  `release_dates`, `versions_available`, `keywords`, `examples`,
  `affected_subsets`, `stewardship_roles`, `external_resources`, `missing`,
  `why_missing`) are lists of atomic values.
- `versions_available` carries bare version labels (`1.0.0`, `2.0.0`, `3.0.0`);
  DOIs, dates and sizes live in `version_details`, so no identifier value has
  commentary inside it.
- Structured slots are filled before prose: `creators[].affiliations` and
  `funders[].grants` carry the organizations and awards rather than leaving them
  in narrative; `instances[].counts`, `file_collections[].file_count` /
  `total_bytes`, `collection_timeframes[].start_date` / `end_date`, and every
  boolean flag are populated.
- `Person`-ranged slots (`principal_investigator`, `contact_person`) are
  non-inlined in the induced schema, so they carry ORCID identifier references
  only; the person's name lives in the enclosing `Creator.name` /
  `EthicalReview.name` and the organization in `Creator.affiliations`.
- Evidence commentary is confined to `source_caveats` (17 occurrences in the
  full record). `notes` is used once, at top level, to state which release the
  record is about; it restates no sibling value.
- All enum-ranged values are drawn from the schema's permissible values
  (`BiasTypeEnum`, `LimitationTypeEnum`, `FileCollectionTypeEnum`,
  `DataUsePermissionEnum`, `ComplianceStatusEnum`, `ConfidentialityLevelEnum`,
  `CreatorOrMaintainerEnum`, `DatasetRelationshipTypeEnum`, `FormatEnum`,
  `MediaTypeEnum`). Standards that are not enum members — DICOM, WFDB, Open
  mHealth, the NASA ASCII guidelines — are carried in the free-text `conforms_to`
  and `format` slots rather than approximated onto an enum value.

### Slots deliberately left absent

`imputation_protocols`, `annotation_analyses`, `machine_annotation_tools`,
`errata`, `variables`, `parent_datasets`, `resources`, `compression`, `status`,
`download_url`, `created_on`, `last_updated_on`, `modified_by`,
`was_derived_from`, `conforms_to_class`, `dialect` (core), and
`Creator.credit_roles`. In each case the bundle carries no supporting evidence:
no labelling or imputation was performed, no variable-level dictionary is in the
bundle (the healthsheet points to `docs.aireadi.org`), the healthsheet's erratum
answer is empty, FAIRhub records `"parent": null`, and the study roles the bundle
names ("Study Principal Investigator", "Writing Committee", …) do not map onto
CRediT terms. Absence here is the answer, not an omission.

## Phase 4 — strict full/core reconciliation

Shared slots were derived at runtime from `Dataset` and `CoreDataset` with
LinkML `SchemaView`; no hand-written field list was used.

- **Schema-identical shared slots: 78.** 66 of the 78 are present in both
  records; the remaining 12 are absent from both.
- **Deep identity:** every schema-identical slot present in either record is
  present in both, with deeply identical parsed YAML content including nested
  mapping values and list item order. This holds for narrative fields too —
  core condenses, paraphrases, reorders and omits nothing. Identity is
  structural rather than asserted: the core record was *generated* by copying
  the parsed value of each schema-identical slot from the Phase 3-audited full
  record, so no independent re-wording could occur.
- **Projected slots: `resources`** (`Dataset` in full, `CoreDataset` in core).
  Absent from both records, so coverage is trivially equal.
- `--sync-core` was **not** needed and was not run: the pair passed the
  independent check on its first execution.

### Full-only slots (16)

Present in the full record and not carried to core because `CoreDataset` does
not declare them: `file_collections`, `subsets`, `total_file_count`,
`total_size_bytes`, `splits`, `relationships`, `collection_consents`,
`collection_notifications`, `consent_revocations`, `direct_collection`,
`participant_privacy`, `participant_compensation`, `data_governance`,
`citation`, `related_datasets`, `third_party_sharing`.

### Core-only slot

`distributions` (`CoreDistribution`), the projection of full `file_collections`.

### Semantic review of related, non-identical content

The validator's one warning
(`semantic-review-required $.file_collections <-> $.distributions`) is the
required prompt for the review below; it is not evidence that the review
happened. Ten collections matched ten distributions, with no unmatched core
distribution.

| Aspect | Finding |
|---|---|
| Names | Identical for all ten (`cardiac_ecg`, `clinical_data`, `environment`, `retinal_flio`, `retinal_oct`, `retinal_octa`, `retinal_photography`, `wearable_activity_monitor`, `wearable_blood_glucose`, `Root metadata files`). |
| Descriptions | Byte-identical for all ten. |
| Paths | Carried verbatim for the nine datatype directories; the root metadata collection has no path in either record. |
| Byte counts | Core `bytes` equals full `total_bytes` for all nine directories. Neither record states a byte total for the root metadata collection. |
| File counts | Full-only — `CoreDistribution` declares no file-count slot, so the projection omits it. Omission, not contradiction. |
| Formats | `format`/`media_type` are set only for `clinical_data` (`CSV` / `text/csv`), which `FormatEnum` and `MediaTypeEnum` admit and which the README supports ("Each CSV file in this directory is a one-to-one mapping to the OMOP CDM tables"). DICOM, WFDB, Open mHealth and the NASA ASCII guidelines are not enum members, so both records carry them in `conforms_to` and leave `format` absent rather than approximating. `conforms_to` agrees exactly between the pair. |
| Compression / checksums | Absent in both. The bundle publishes no checksums and states no compression. |
| Access URLs | Not carried at distribution level in either record; access URLs live in `distribution_formats[0].access_urls`, which is schema-identical and deeply identical across the pair. |
| Identifiers | Core distribution ids are the full collection ids with the fragment renamed (`…#cardiac_ecg` → `…#distribution-cardiac_ecg`), a 1:1 injective mapping with no collision. |
| Release scope | All ten describe version 3.0.0. Core's `version`, `doi`, `issued` and `version_access` are deeply identical to full's, so the release scope of the distributions is unambiguous in core. |

`total_file_count` / `total_size_bytes` versus distribution-level values: the
scopes are the same (the whole of v3.0.0), and the arithmetic reconciles as set
out under *Internal consistency checks* — 356,334 + 9 = 356,343 exactly, and the
419,614-byte residual is attributable to the nine root metadata files whose sizes
the bundle does not state. `is_tabular: false` is identical in both records and
agrees with the format picture (one tabular datatype directory among nine, plus
imaging and waveform data). Top-level identity, version and access facts agree
with `version_access`, `distribution_formats`, `distribution_dates` and the
repeated statements in `license_and_use_terms` and `regulatory_restrictions`.
Historical releases (1.0.0, 2.0.0) are distinguished from the current release by
explicit dating in `version_access.version_details` in both records, so their
differing sizes and participant counts are not contradictions of this release's
figures.

**Zero unresolved contradictions within or between the two records.**

## Prompt condition

The run was launched from a rendered instruction at
`/tmp/d4d_launch/AI_READI_rep3.txt` naming
`src/download/prompts/d4d_generic_arm_prompt.md` as the condition's prompt file,
and both headers record `Mode: four-phase project agent, generic prompt` and that
`Prompt:` path. The instruction file's decision rules are the uniform rules the
playbook lists for all conditions and all projects; nothing project-specific was
added. Whether the prompt file hashes to this repository's canonical pin is
established by the launcher's `d4d api prompts check` / `d4d runs check`, not by
this agent.

## Header note

The prompt specified a header block to be used exactly, and it contains no
`Phase 4 reconciliation` line. The playbook's completion criteria require the
core header to contain `Phase 4 reconciliation: completed`. That line was
appended to the core header only — it is uniform across every run of this
playbook rather than a condition-specific variation, and it records that Phase 4
ran rather than asserting anything about the model or its settings. No
`# Reasoning effort:` line was added to either header, per the playbook: this
agent does not know the effort the run was launched at, so the recorder is left
to name the gap.

## Files changed

- `data/d4d_concatenated/claudecode_agent/2026-08-11_claude-opus-5-claudecode-generic_rep3/AI_READI_d4d.yaml` (created, then corrected in Phase 3)
- `data/d4d_concatenated/claudecode_agent_core/2026-08-11_claude-opus-5-claudecode-generic_rep3/AI_READI_d4d_core.yaml` (created, regenerated after Phase 3 corrections)
- `data/d4d_concatenated/claudecode_agent_core/2026-08-11_claude-opus-5-claudecode-generic_rep3/AI_READI_reconciliation.md` (this file)

No file outside these three was written.

## Commands run

```bash
poetry run d4d download scope --project AI_READI

poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_all.yaml \
  -C Dataset data/d4d_concatenated/claudecode_agent/2026-08-11_claude-opus-5-claudecode-generic_rep3/AI_READI_d4d.yaml
poetry run linkml-term-validator validate-data \
  data/d4d_concatenated/claudecode_agent/2026-08-11_claude-opus-5-claudecode-generic_rep3/AI_READI_d4d.yaml \
  --schema src/data_sheets_schema/schema/data_sheets_schema_all.yaml --target-class Dataset

poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml \
  -C CoreDataset data/d4d_concatenated/claudecode_agent_core/2026-08-11_claude-opus-5-claudecode-generic_rep3/AI_READI_d4d_core.yaml
poetry run linkml-term-validator validate-data \
  data/d4d_concatenated/claudecode_agent_core/2026-08-11_claude-opus-5-claudecode-generic_rep3/AI_READI_d4d_core.yaml \
  --schema src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml --target-class CoreDataset

poetry run python -m data_sheets_schema.d4d_pair_consistency \
  --full data/d4d_concatenated/claudecode_agent/2026-08-11_claude-opus-5-claudecode-generic_rep3/AI_READI_d4d.yaml \
  --core data/d4d_concatenated/claudecode_agent_core/2026-08-11_claude-opus-5-claudecode-generic_rep3/AI_READI_d4d_core.yaml

poetry run d4d download scope --check --project AI_READI
```

## Final results

| Check | Result |
|---|---|
| Full: `linkml-validate -C Dataset` | **PASS** (no issues found) |
| Full: `linkml-term-validator` | **PASS** |
| Core: `linkml-validate -C CoreDataset` | **PASS** (no issues found) |
| Core: `linkml-term-validator` | **PASS** |
| Pair consistency (no `--sync-core`) | **PASS** — 78 schema-identical slots; projected slots `['resources']`; 1 semantic-review warning, reviewed above |
| `d4d download scope --check --project AI_READI` | **in scope** |
| Full top-level slot count | **82** |
| Core top-level slot count | **67** |
| Prior-D4D reuse | **none** |
| Unresolved contradictions | **none** |
