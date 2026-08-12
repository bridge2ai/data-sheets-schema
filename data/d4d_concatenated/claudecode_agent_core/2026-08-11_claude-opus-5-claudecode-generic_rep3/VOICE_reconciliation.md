# VOICE — Phase 3 / Phase 4 reconciliation report

- **Run label:** `2026-08-11_claude-opus-5-claudecode-generic_rep3`
- **Arm:** BASELINE (input documents only)
- **Runtime / provider / model:** Claude Code / Anthropic / claude-opus-5
- **Mode:** four-phase project agent, generic prompt condition
- **Declared input bundle:** `data/preprocessed/concatenated/VOICE_preprocessed.txt`
- **Full record:** `data/d4d_concatenated/claudecode_agent/2026-08-11_claude-opus-5-claudecode-generic_rep3/VOICE_d4d.yaml`
  (md5 `452b0b3f281434b6bc866f78d8760d80`, 1834 lines, 82 populated top-level slots)
- **Core record:** `data/d4d_concatenated/claudecode_agent_core/2026-08-11_claude-opus-5-claudecode-generic_rep3/VOICE_d4d_core.yaml`
  (md5 `a25640d2448384452c46bd5bec04ca2e`, 1163 lines, 69 populated top-level slots)

## Referent

`Dataset` admits one referent. The referent chosen is the **adult Bridge2AI-Voice
dataset**, identified by its PhysioNet project-level DOI
`https://doi.org/10.13026/37yb-1t42` ("DOI (latest version)" on every PhysioNet page in
the bundle), described at its current release 3.1.0 of 1 May 2026. This is the choice the
declared bundle best supports: nine of its eleven documents are about the adult dataset,
its programme, its protocol or its access terms.

The bundle also contains one document about the **Bridge2AI-Voice Pediatric Dataset**
(`physionet_pediatric_1_1_0`). That is a different dataset — its own PhysioNet project and
DOI (`10.13026/mf9s-5r03`), its own release series, a distinct cohort of 300 participants
aged 2–18 recruited at the Hospital for Sick Children, a distinct age-appropriate protocol
collected through `reproschema-ui` rather than the Bridge2AI-Voice app, and separate
approval by the Research Ethics Board at the Hospital for Sick Children rather than the
USF single IRB. It is represented **only** through `related_datasets`
(`relationship_type: references`) in the full record, which is the slot the manifest's
scope block declares for it. No pediatric identifier appears in `resources`,
`file_collections`, `distribution_formats.access_urls`, `distributions` or any other slot
in either record. The choice is held identically across both records: the core record
carries the same `id`, `doi`, `version`, `title` and `description`, and `related_datasets`
is a full-only slot, so the pediatric relation is stated once and not duplicated.

The five disease cohorts are represented as `subsets` (`is_subpopulation: true`) of the
adult dataset, not as separate datasets, because the bundle presents them as cohort
categories within one collection protocol.

## Phase 3 — source and provenance audit

### Provenance boundary

No prior full or core D4D record, from any arm, label or date, was read, opened, grepped
or consulted. The complete list of files read during generation is:

- `/tmp/d4d_launch/VOICE_rep3.txt` (the task specification)
- `.claude/agents/d4d-provenance-guard.md`, `.claude/commands/d4d-full-core.md`,
  `.claude/commands/d4d-agent.md`
- `data/preprocessed/concatenated/VOICE_preprocessed.txt` (the declared bundle, read in
  full)
- `data/preprocessed/source_manifest.yaml` (scope block and VOICE source inventory, read
  via `d4d download scope --project VOICE` and targeted `grep`)
- `src/data_sheets_schema/schema/data_sheets_schema_all.yaml` and
  `src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml`, read through
  LinkML `SchemaView` and `JsonSchemaGenerator` rather than as text, to derive the induced
  slot inventory, ranges, cardinality, inlining behaviour, required fields and enum values
  for `Dataset`, `CoreDataset` and every nested class
- this run's own two output files

Two exposures are recorded rather than left implicit:

1. **Directory listing.** `ls data/d4d_concatenated/claudecode_agent/` was run once, to
   confirm the target version directory did not already exist. It returned directory and
   file *names* only; no prior record's contents were read. The playbook permits
   inspecting output directory names to choose a version label.
2. **Scope-checker output.** `d4d download scope --check --project VOICE` prints, for
   every record it checks, the offending values it finds. Running it therefore printed
   slot values drawn from 32 prior-run VOICE records into this agent's context. This
   happened **after** both records of this run were written and validated, so it could not
   have influenced generation, and none of those values was used as evidence. It is noted
   because the checker's report is a channel through which prior generated content reaches
   a generating agent, and a run that used `--check` earlier in its sequence would not be
   able to make this claim.

No structure was taken from any prior record. Every emitted slot name, nesting shape,
range and enum value was derived from the schemas. Two schema facts materially shaped the
output and are recorded because they are easy to get wrong from semantics alone:
`Creator.principal_investigator`, `EthicalReview.contact_person`,
`LicenseAndUseTerms.contact_person`, `DataGovernance.committee_contact` and
`ExportControlRegulatoryRestrictions.governance_committee_contact` have range `Person`,
which carries an identifier and is **not** inlined, so each is a plain identifier string
and not a nested object; and `Dataset`'s JSON Schema sets `additionalProperties: true`, so
`linkml-validate` would not have caught an invented top-level key — field names were
checked against the induced slot inventory directly.

### Scope check

```
poetry run d4d download scope --check --project VOICE --strict     # exit 0
```

Both records are in scope: neither identifies itself as a dataset the manifest declares
distinct. Neither appears among the 32 records the checker flags for placing pediatric
identifiers outside the declared slot.

### Source review and corrections applied

Nine corrections were made to the full record after the Phase 1 draft, and the core record
was regenerated from the corrected full record. Every correction moved in the direction of
removing an unsupported value.

| # | Slot | Finding | Action |
|---|---|---|---|
| 1 | `distribution_formats[0].media_type` | `application/vnd.apache.parquet, text/tab-separated-values, application/json` — no IANA media type appears anywhere in the bundle; this came from model knowledge, not evidence | removed; `source_caveats` now states that no media type is stated in the bundle |
| 2 | `file_collections[0].resources[*].media_type` | same defect on the two TSV files | removed; `format: TSV` retained, which the bundle supports ("tab delimited") |
| 3 | `human_subject_research.special_populations` | a bullet characterising participants with cognitive impairment and neurodegenerative disease as a special population — the bundle does not say this | removed |
| 4 | `at_risk_populations.at_risk_groups_included` | `false` was a judgement the bundle does not make; the only population it characterises as vulnerable is pediatric patients, who are not in this dataset | value withdrawn; the reason is recorded in `source_caveats` rather than guessed either way |
| 5 | `variables[3].description` | "added to the Parquet feature files from v3.0.0" inferred an addition from silence in the v1.1 page | reworded to "described in the v3.0.0 and v3.1.0 Parquet feature files" |
| 6 | `maintainers[2]`, `distribution_formats[2]` | "Temerty Centre" | corrected to "Temerty Center", the spelling the source uses |
| 7 | `creators` (Johnson) | affiliation conflict between sources | `source_caveats` added naming both |
| 8 | `file_collections[0]` | the release names the dense feature files in the singular in its folder listing and in the plural in the per-file descriptions that carry the counts | `source_caveats` added stating which form was used for names and which for counts |
| 9 | `related_datasets` (protocol paper) | the documentation and the PhysioNet releases cite the same paper with different first authors | `source_caveats` added |

Two empty lists (`imputation_protocols: []`, `other_tasks: []`) were also removed: an
absent slot is the correct representation of absent evidence, and an empty list asserts a
negative the bundle does not state.

### Source disagreements represented rather than resolved

The bundle is internally inconsistent in several places. Each is represented as what the
evidence states, in `source_caveats` at the level the disagreement belongs to, rather than
silently resolved:

- **Target size.** The project documentation states a flagship dataset of 10,000 voices
  and an anticipated enrollment of 10,000 by 2027; the audiomics white paper and the IRB
  protocol state 30,000. Both are aims and neither describes a release, so neither is used
  as a count anywhere in the record.
- **Recording counts.** The documentation states ~61,937 voice-derived recordings for v3.0
  from 833 participants; the PhysioNet v3.1.0 page gives per-feature counts from 28,640 to
  32,522. The two are not reconciled in the bundle, so `instances[1].counts` is left
  absent and both accounts are recorded.
- **Version currency.** Parts of the documentation are written against v2.0.0 (study
  population, language options) and parts against v3.0.0, while the PhysioNet pages cover
  v1.1, v3.0.0 and v3.1.0. Historical values are kept only where their version scope is
  explicit — `version_access.versions_available` and `distribution_dates.release_dates`
  label every value by version.
- **Access tier.** "Restricted Access / registered users" on v1.1 versus "Credentialed
  Access" on v3.0.0 and v3.1.0.
- **Distribution platform.** The healthsheet describes distribution through Health Data
  Nexus; v1.1 onward are published on PhysioNet. Both are recorded as distinct
  `distribution_formats` entries.
- **Confidentiality.** The healthsheet answers "No" to whether the dataset contains
  confidential data, while the Data Transfer and Use Agreement states the data is
  Personally Identifiable Information covered by a Certificate of Confidentiality. These
  are represented as **two** `confidential_elements` entries with opposite booleans, each
  scoped to the data it governs, rather than merged into one claim.
- **Content warnings.** The healthsheet says free-speech transcriptions are included; v1.1
  says free-speech transcripts were removed, and v3.0.0/v3.1.0 say free-speech-derived
  features were excluded.
- **Award identifiers.** Four distinct award strings for the same core project
  (`OT2OD032720`, `3OT2OD032720-01S1`, `3OT2OD032720-01S3`, `1OT2OD032720-01`) appear
  across the bundle; all four are recorded as transcribed. Two further strings in the
  documentation footer are garbled in the captured text and are named in `source_caveats`
  rather than used as grant numbers.
- **Person-level conflicts.** Sui/Siu, Ravitsky (University of Montreal vs The Hastings
  Center), Rudzicz (Dalhousie vs Toronto), Johnson (SickKids vs Toronto) — each recorded
  on the relevant creator.
- **Control cohort.** `control.tsv` is present in the v3.0.0 phenotype listing and absent
  from the v3.1.0 listing; the bundle does not explain the difference.

### Shape audit

- No prose stands where the schema requires a list; every multivalued slot
  (`irb_approval`, `special_protections`, `restrictions`, `regulatory_restrictions`,
  `warnings`, `examples`, `release_dates`, `versions_available`, `tools`, `keywords`,
  `stewardship_roles`, `affected_subsets`) holds discrete items.
- No enum value outside its schema definition; confirmed by `linkml-validate` and by
  reading the induced permissible values before writing (`CompressionEnum`, `FormatEnum`,
  `MediaTypeEnum`, `FileCollectionTypeEnum`, `BiasTypeEnum`, `LimitationTypeEnum`,
  `CRediTRoleEnum`, `DataUsePermissionEnum`, `ComplianceStatusEnum`,
  `ConfidentialityLevelEnum`, `CreatorOrMaintainerEnum`, `VariableTypeEnum`,
  `DatasetRelationshipTypeEnum`).
- No commentary is embedded in a name, identifier or affiliation value.
- Slot-filling order was followed: structured slots first, then `description`, then
  `notes`. **`notes` is unused in both records** — every piece of narrative found a
  `description` or a typed slot. Evidence commentary is in `source_caveats` throughout and
  nowhere else; no `source_caveats` value restates a sibling slot.
- `credit_roles` is deliberately empty on every creator: the only CRediT statements in the
  bundle attach to authorship of the feasibility publication, not to creation of the
  dataset. This is stated in the consortium creator's `source_caveats` rather than left
  silent.

### Phase 2 discoveries back-ported to full

None. The core record is the `CoreDataset` projection of the audited full record; Phase 2
found no core field that the sources support and the full record left empty, and no fact
the full extraction missed. All nine corrections above originated in the Phase 3 source
audit and were applied to the full record first, which was then re-validated before the
core record was regenerated from it.

### Validation after corrections

```
poetry run linkml-validate -s .../data_sheets_schema_all.yaml      -C Dataset     <full>   # No issues found
poetry run linkml-term-validator validate-data <full> --schema .../data_sheets_schema_all.yaml      --target-class Dataset      # passed
poetry run linkml-validate -s .../data_sheets_schema_core_all.yaml -C CoreDataset <core>   # No issues found
poetry run linkml-term-validator validate-data <core> --schema .../data_sheets_schema_core_all.yaml --target-class CoreDataset  # passed
```

## Phase 4 — strict full/core reconciliation

### Schema-derived shared-slot result

Shared slots were derived at runtime with `SchemaView` from `Dataset` and `CoreDataset`;
no hand-written field list was used. `Dataset` has 97 slots and `CoreDataset` 81; **79 are
shared**, of which **78 have identical induced range and cardinality** and one
(`resources`) is a projection (`Dataset` in full, `CoreDataset` in core). `resources` is
absent from both records, so the projection is empty and coverage is trivially equal.

```
poetry run python -m data_sheets_schema.d4d_pair_consistency --full <full> --core <core> --sync-core
poetry run python -m data_sheets_schema.d4d_pair_consistency --full <full> --core <core>
```

Both runs report:

```
PASS: 78 schema-identical slots; projected slots=['resources']
WARNING [semantic-review-required] $.file_collections <-> $.distributions:
  deterministic matches=3 (3 at collection level, 0 at nested resource level),
  unmatched core distributions=[]
```

`--sync-core` changed nothing: the core record is byte-identical before and after it, because
core was generated as a projection of the audited full record rather than as an independent
extraction. Every schema-identical slot is present in both records or absent from both, and
every parsed value is deeply identical, including narrative fields — `description`,
`source_caveats`, and every nested `description`, `response`, `*_details` and list item are
carried verbatim, in the same order. Nothing was condensed, paraphrased, reordered or omitted
to make core shorter.

**Full-only slots (15 populated):** `citation`, `collection_consents`,
`collection_notifications`, `consent_revocations`, `data_governance`, `direct_collection`,
`file_collections`, `participant_compensation`, `participant_privacy`, `related_datasets`,
`relationships`, `splits`, `subsets`, `third_party_sharing`, `variables`. These are not in
`CoreDataset` at all; their absence from core is a schema fact, not an omission.

**Core-only slots (2 populated):** `distributions`, `dialect`.

### Semantic review of related, non-identical content

The validator's warning marks content that requires review; the review itself is here.

**`file_collections` (full) → `distributions` (core).** Three collections, three
distributions, matched 1:1 with no unmatched entry on either side:

| full `file_collections[i]` | core `distributions[i]` | name | path | description |
|---|---|---|---|---|
| `d4d:voice_fc_features` | `d4d:voice_dist_features` | `features` | `features/` | verbatim identical |
| `d4d:voice_fc_phenotype` | `d4d:voice_dist_phenotype` | `phenotype` | `phenotype/` | verbatim identical |
| `d4d:voice_fc_metadata` | `d4d:voice_dist_metadata` | `metadata` | `metadata/` | verbatim identical |

- **Names, paths, descriptions:** identical strings, so no conflict is possible.
- **Formats:** neither side sets a format at the collection level, because each folder
  holds more than one format. Format is stated only on the full record's nested `File`
  objects (`format: TSV` on `static_features.tsv` and `audio_quality_metrics.tsv`), which
  `CoreDistribution` has no place for. No contradiction.
- **Compression, checksums (`hash`, `md5`, `sha256`), byte counts:** absent on both sides.
  The bundle states no checksum or byte count for any file, and `total_file_count` and
  `total_size_bytes` are absent from the full record for the same reason, so there is
  nothing to compare and nothing that disagrees.
- **Access URLs:** absent from both projections. Access URLs live in
  `distribution_formats`, which is schema-identical and therefore deeply identical in both
  records; the three entries there (PhysioNet, Synapse, Health Data Nexus) agree with the
  top-level `page` and with `version_access`.
- **Release scope:** the full record's collections carry `version: 3.1.0`;
  `CoreDistribution` has no `version` slot, so this is a full-only nested slot omitted from
  the projection, as the playbook prescribes. The core record still fixes the release
  through the top-level `version: 3.1.0`, which is schema-identical and equal.
- **Nested resource level:** the full record lists 11 `File` objects inside the `features`
  collection. `CoreDistribution` cannot nest files, and mixing file-level and
  collection-level entries in `distributions` would make the 1:1 mapping ambiguous.
  Per-file detail is therefore treated as full-only nested content and omitted from the
  core projection; the validator's "0 at nested resource level" reflects this by design,
  not a gap. No file-level fact appears in core in any other form, so no conflict exists.

**`dialect` (core-only) against full formats.** `dialect` is `delimiter: "\t"`,
`header: "true"`. The bundle supports both directly: the phenotype and static-feature files
are described as tab-delimited and are read with `sep="\t", header=0`. This does not
contradict anything in the full record — `File.dialect` is unused there, and the two `File`
entries that state a format state `TSV`. The dialect describes the dataset's tabular
portion; the dense feature files are Parquet, which has no delimiter, and the description
text carried identically in both records says so.

**`is_tabular`.** Absent from both records. The dataset is mixed Parquet and TSV and the
bundle makes no tabularity claim, so neither `true` nor `false` is supported; presence is
identical across the pair.

**Identity, version and access facts against the rest of both records.** `id`
(`https://doi.org/10.13026/37yb-1t42`) equals `version_access.latest_version_doi`;
`doi` (`10.13026/37yb-1t42`) is the bare form of the same identifier; `version: 3.1.0`
agrees with `page` (`.../b2ai-voice/3.1.0/`), with the last entry of
`distribution_dates.release_dates` and with the last entry of
`version_access.versions_available`; `license` agrees with
`license_and_use_terms.license_terms` and with the PhysioNet "License (for files)" line;
`publisher` agrees with the maintainer entry for the MIT Laboratory for Computational
Physiology. All of these are schema-identical slots and therefore hold identically in core.

**Historical versus current releases.** Every historical value is labelled with the
version it belongs to (v1.0's 12,523 recordings and 306 participants; v2.0's 136 added
participants; v3.0.0's 391 added participants and its 512-point-FFT predecessor; v1.1's
withdrawn files). None is treated as contradicting the current v3.1.0 values, and none is
carried at the top level where it would read as current.

### Note on the core header

The launch specification's `HEADER BLOCK` was used exactly, with the two substitutions it
names (`phase 1` → `phase 2`, full schema path → core schema path). Two lines were **added**
to the core header, and only to the core header, because the playbook's completion criteria
require them: `# Sources:` naming both the document bundle and the same-run full record, and
`# Phase 4 reconciliation: completed`. No specified line was altered, and no
`# Reasoning effort:` line was added — reasoning effort is established by the provenance
recorder, not by the header.

### Prompt condition

`d4d api prompts check --strict` reports all 10 prompt files at their canonical pins,
including `src/download/prompts/d4d_generic_arm_prompt.md`, the file this run's header
names. The run's condition is therefore **generic**, under a published version of that
condition's text; nothing `uncanonical` was found.

## Provenance record

**Not written by this agent.** The launching agent's instruction states that the launcher
writes the provenance record, which overrides the corresponding line of the rendered
specification. The `d4d provenance record` command was therefore not run, and
`d4d runs validate` / `d4d runs check --strict` have not yet been run for this label; they
remain the launcher's step. Both output files are final and hash to the md5 values recorded
at the top of this report, so a record written against them now will pin their final state.

## Outcome

**Reconciliation passed with no unresolved discrepancies.** 78 schema-identical shared
slots are deeply identical and identically present across the pair; the single projected
slot (`resources`) is empty on both sides; the one related-content mapping
(`file_collections` ↔ `distributions`) matches 3-for-3 with verbatim names, paths and
descriptions and no conflicting format, compression, checksum, byte-count, access-URL or
release-scope value. Both records pass schema and ontology-term validation, and both are
in scope under the manifest's declaration for VOICE.
