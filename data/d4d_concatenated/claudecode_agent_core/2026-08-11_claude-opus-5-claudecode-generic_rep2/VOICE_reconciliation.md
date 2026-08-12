# VOICE full/core reconciliation — 2026-08-11_claude-opus-5-claudecode-generic_rep2

| field | value |
|---|---|
| Project | VOICE |
| Version label | `2026-08-11_claude-opus-5-claudecode-generic_rep2` |
| Arm | BASELINE (input documents only) |
| Mode | four-phase project agent, generic prompt |
| Runtime / provider / model | Claude Code / Anthropic / claude-opus-5 |
| Declared input bundle | `data/preprocessed/concatenated/VOICE_preprocessed.txt` |
| Full record | `data/d4d_concatenated/claudecode_agent/2026-08-11_claude-opus-5-claudecode-generic_rep2/VOICE_d4d.yaml` |
| Core record | `data/d4d_concatenated/claudecode_agent_core/2026-08-11_claude-opus-5-claudecode-generic_rep2/VOICE_d4d_core.yaml` |
| Full top-level slots | 82 |
| Core top-level slots | 69 |
| Schema-identical shared slots proven | 78 |

Line and slot counts are informational metadata, not a quality gate.

## Referent

`Dataset` admits one referent. The referent chosen is the **Bridge2AI-Voice adult
dataset as a versioned PhysioNet project**, identified by the project-level DOI
`https://doi.org/10.13026/37yb-1t42`, which the PhysioNet pages record as "DOI (latest
version)". This is the referent the manifest declares for VOICE.

Version-specific top-level fields (`version: 3.1.0`, `page`, `issued`, `citation`)
describe the current release; the per-version DOIs `10.13026/8xbn-nq66` (3.1.0),
`10.13026/k81f-qr68` (3.0.0) and `10.13026/249v-w155` (1.1) are carried in `resources`
and `version_access` rather than at the top level. The choice is stated in the record's
own `source_caveats` so that it is legible without this report. It is held identically
across both records: `id`, `doi`, `version`, `page`, `issued`, `resources` and
`version_access` are schema-identical shared slots and are byte-equal after Phase 4.

The **Bridge2AI-Voice Pediatric Dataset** (`https://doi.org/10.13026/mf9s-5r03`) is
present in the bundle as source `physionet_pediatric_1_1_0` and is declared
related-but-distinct. It is expressed only through `related_datasets`, the slot the
manifest declares for it, with `relationship_type: is_supplemented_by`. It appears
nowhere in `resources`, `distribution_formats[].access_urls`,
`file_collections[].download_url` or `version_access`. The core record has no
`related_datasets` slot at all (core-absent), so the pediatric identifiers do not appear
in core in any form; the four occurrences of the word "pediatric" in core are prose in
`purposes`, `tasks` and `at_risk_populations` describing the *project's* disease-cohort
categories, not identifiers.

`d4d download scope --check --project VOICE` reports neither of this run's two records
under either heading: not `out_of_scope`, and not among the 32 records that place a
related-but-distinct dataset's identifiers outside the declared slot.

## Phase 3 — source and provenance audit

### Provenance

Factual inputs read during this run were, in full:

- `data/preprocessed/concatenated/VOICE_preprocessed.txt` (the declared bundle);
- `data/preprocessed/source_manifest.yaml`, via `d4d download scope --project VOICE`;
- `src/data_sheets_schema/schema/data_sheets_schema_all.yaml` and
  `data_sheets_schema_core_all.yaml`, read through `SchemaView` for class shapes, ranges,
  cardinality, inlining and enum permissible values;
- repository instructions: `.claude/agents/d4d-provenance-guard.md`,
  `.claude/commands/d4d-full-core.md`, `.claude/commands/d4d-agent.md`;
- for Phase 2 onward, the exact same-run full record at the label above.

**No prior D4D record was read**, from any arm, label or date; nothing under
`data/d4d_concatenated/` other than this run's own two output paths was opened, and no
`*_crate_d4d.yaml` or `*_crate_mapped_d4d.yaml` was opened. No evaluation report,
reconciliation report, test fixture or schema example supplied a value. No live web
content was fetched.

One thing worth naming rather than leaving implicit: `d4d download scope --check` prints
offending values from *other* records as part of its report, so its output included
pediatric DOIs quoted from prior runs. Those files were not opened and nothing from that
output entered either record — the pediatric identifiers used here were taken from the
bundle's `physionet_pediatric_1_1_0` source, which states them directly. The check was
run after both records were written, as verification.

### Evidence audit against the bundle

The bundle's eleven sources describe different releases and different scopes, and they
disagree. The disagreements were represented rather than silently resolved:

| disagreement | how it is represented |
|---|---|
| Hosting: the documentation healthsheet says the dataset is hosted by the Health Data Nexus (T-CAIREM, University of Toronto); the PhysioNet 3.0.0/3.1.0 pages say the resource is maintained by the MIT Laboratory for Computational Physiology | both recorded as separate `maintainers` entries, the Health Data Nexus entry carrying a `source_caveats` scoping it to the earlier feature-only release; also named in top-level `source_caveats` |
| Target collection size: 10,000 voices (documentation site, and anticipated 2027 enrolment count) vs 30,000 human voices (audiomics white paper) vs 5,000 at USF and 30,000 across institutions (IRB protocol) | all three stated, attributed to their source, in `purposes[0].description` and in top-level `source_caveats`; no single figure asserted |
| Grant identifiers: `3OT2OD032720-01S3` (NIH RePORTER) vs `3OT2OD032720-01S1` (PhysioNet acknowledgements) vs `OT2OD032720` (core project / organization study ID) vs `1OT2OD032720-01` (feasibility publication) | four distinct `Grant` objects with `grant_number` and a description saying which source states each and what it funds |
| Corrupted award strings on the documentation site: `3TF-OT2ActfOD032720Projectf01S1`, `Award #3Tf-OTOD03272001S2` | *not* transcribed as identifiers; named in top-level `source_caveats` as evidently corrupted |
| Feature filenames spelled two ways on the same 3.1.0 page (`torchaudio_spectrogram.parquet` in the folder inventory, `torchaudio_spectrograms.parquet` in the per-file description; likewise mel spectrogram) | inventory spelling used for `path`; the discrepancy recorded in `file_collections[0].source_caveats` |
| Contributor names: `Jennifer Sui` / `Frank Rudzizc` (documentation site) vs `Jennifer Siu` / `Frank Rudzicz` (PhysioNet author lists) | PhysioNet spellings used; both recorded in `creators[2].source_caveats` |
| Access policy wording: v1.1 "only registered users who sign the specified data use agreement" vs v3.x "only credentialed users who sign the DUA" | the v1.1 wording is kept on `resources[1.1].description` as a property of that historical release, not as a contradiction of the current policy |
| HIPAA: the healthsheet answers that HIPAA de-identification rules are applied; the Data Transfer and Use Agreement states the data is Personally Identifiable Information "not covered under HIPAA" | `regulatory_restrictions.hipaa_compliant: compliant` with the DTUA statement recorded verbatim in `other_compliance` |
| Publication date: "published and made available at the end of November, 2024" (healthsheet) vs the PhysioNet release dates from January 2025 onward | the November 2024 statement is kept in `distribution_dates[0].description`, scoped to the healthsheet section that describes Health Data Nexus distribution |

### Mis-scoped assertions caught and corrected

- **CRediT roles.** The bundle records CRediT contributor roles only for the authors of
  the 2025 app feasibility publication, which is about the data-collection application
  and not the dataset release. Assigning them as dataset-creation roles would have been
  inference, so `credit_roles` is left absent on every `Creator` and the reason is
  recorded in `creators[2].source_caveats`.
- **IRB number 004890.** This is the USF approval cited by the feasibility publication.
  The bundle states no IRB number for the "Bridge2AI Voice Data Acquisition" protocol.
  It is therefore not carried as the dataset's IRB approval; the scope limitation is
  recorded in `ethical_reviews[0].source_caveats`.
- **Pediatric provisions in the IRB protocol.** The protocol governs both adult and
  pediatric collection; its parental-permission, child-assent and HRP-416 provisions
  apply to the pediatric sites, whose data are a separate dataset. Recorded in
  `at_risk_populations.source_caveats`, with `at_risk_groups_included: false` resting on
  the stated 18-year eligibility floor.
- **`reproschema-ui`.** Named in the bundle as the pediatric collection tool; excluded
  from `collection_mechanisms` for this referent and mentioned only inside the
  `related_datasets` description of the pediatric dataset.
- **Redacted emails.** Contact addresses on the documentation site were replaced with a
  placeholder during preprocessing, so no address from that source is recorded. The two
  addresses that survive elsewhere in the bundle (the PI contact in the IRB protocol,
  the access-committee address on the PhysioNet notice) are recorded in prose because
  `Person` is a non-inlined reference range and cannot carry an email inline.

### Omissions, deliberate

`total_file_count`, `total_size_bytes`, `compression`, `download_url`, `is_tabular`,
`parent_datasets`, `imputation_protocols`, `EthicalReview.contact_person`,
`DataGovernance.committee_members`, `access_decision_timeframe`, `appeal_process`,
`Instance.data_topic`, `Instance.data_substrate`, per-cohort participant counts, and
per-file byte counts and checksums are all absent because the bundle does not state
them. `imputation_protocols` was written as an empty list during drafting and removed:
an empty list is not an answer.

### Shape audit

- Every multivalued slot holds a list, never prose: `keywords`, `irb_approval`,
  `special_populations`, `regulatory_compliance`, `restrictions`,
  `regulatory_restrictions`, `versions_available`, `release_dates`, `tools`,
  `tool_accuracy`, `examples`, `warnings`, `affected_subsets`, `annotator_demographics`,
  `stewardship_roles`, `access_urls`, `missing`, `why_missing`, `external_resources`.
- Every enum value is a declared permissible value (verified by `linkml-validate`):
  `BiasTypeEnum`, `LimitationTypeEnum`, `FileCollectionTypeEnum`, `FileTypeEnum`,
  `FormatEnum`, `MediaTypeEnum`, `VariableTypeEnum`, `DataUsePermissionEnum`,
  `ComplianceStatusEnum`, `ConfidentialityLevelEnum`, `CreatorOrMaintainerEnum`,
  `DatasetRelationshipTypeEnum`. Parquet has no `FormatEnum` member, so `format` is left
  absent on the Parquet files rather than filled with an undeclared value.
- Structured slots are filled before prose: `Grant.grant_number`,
  `Creator.affiliations`, `Creator.principal_investigator`, `UpdatePlan.frequency`,
  `RetentionLimits.retention_period`, `VersionAccess.latest_version_doi`,
  `LicenseAndUseTerms.data_use_permission`, `Instance.counts`,
  `LabelingStrategy.annotations_per_item`,
  `HumanSubjectCompensation.compensation_amount`, `FileCollection.file_count`.
- **`notes` is unused in both records.** All evidence commentary — source conflicts,
  transcription provenance, questions the sources leave open — is in `source_caveats`
  (8 occurrences in full). No sibling value is restated.
- No commentary is embedded inside a name, identifier or affiliation value.
- **Identifier syntax** (`data_sheets_schema.identifiers`): full = 53 identifiers,
  9 `uri` + 44 `curie_declared`, **0 bare tokens, 0 undeclared CURIEs**; core = 46,
  9 `uri` + 37 `curie_declared`, same. Every externally identified entity uses its real
  URI (DOIs, the NIH RePORTER project URL, GitHub and Zenodo URLs, the Synapse URL);
  every locally scoped entity uses a `d4d:` CURIE under a declared prefix.

### Corrections back-ported into full during Phase 3

1. `file_collections[0]` (features) gained `file_count: 11`, a `source_caveats` naming
   the two-way filename spelling, and eleven nested `File` resources enumerating the
   Parquet and plain-text feature files with their per-file dimensions and v3.1.0/v3.0.0
   element counts. This was discovered while deriving the core `distributions` shape:
   `FileCollection` is collection-level and `CoreDistribution` is file-level, so core
   needed file-level members that full did not yet enumerate. The content is bundle-
   supported (the 3.1.0 Data Description lists every file and its dimensions), so it was
   back-ported to full first and only then projected into core.
2. Top-level `source_caveats` gained the referent-identity paragraph explaining why
   `doi` is the project-level DOI while `version`, `page` and `citation` are 3.1.0.
3. `creators[2]` gained the contributor-name spelling note, and the name in its
   description was changed to the PhysioNet spelling `Jennifer Siu`.
4. `distribution_dates[0].description` was reworded from an interpretive "which refers
   to the earlier feature-only release" to a scoped "in a healthsheet section that
   describes distribution through the Health Data Nexus platform".

All four were applied to full first and reached core through the single Phase 4
synchronisation, which is why the pre-sync check listed exactly three shared-slot
differences (items 2–4; item 1 touches `file_collections`, which is full-only).

## Phase 4 — strict full/core reconciliation

Shared slots were derived at runtime from `Dataset` and `CoreDataset` with LinkML
`SchemaView`; no hand-written field list was used.

- `Dataset` induces 97 slots, `CoreDataset` 81; **79 are shared**.
- Full-only (18): `citation`, `collection_consents`, `collection_notifications`,
  `consent_revocations`, `data_governance`, `direct_collection`, `file_collections`,
  `parent_datasets`, `participant_compensation`, `participant_privacy`,
  `related_datasets`, `relationships`, `splits`, `subsets`, `third_party_sharing`,
  `total_file_count`, `total_size_bytes`, `variables`.
- Core-only (2): `distributions`, `dialect`.
- Of the 79 shared slots, 67 are populated in this pair and 12 are absent from both
  (`compression`, `created_by`, `created_on`, `conforms_to_class`, `conforms_to_schema`,
  `download_url`, `is_tabular`, `imputation_protocols`, `last_updated_on`,
  `modified_by`, `notes`, `was_derived_from`).

### Deterministic result

```
poetry run python -m data_sheets_schema.d4d_pair_consistency --full <full> --core <core>
FAIL: 78 schema-identical slots; projected slots=['resources']
  3 x ERROR [shared-slot-content]  ($.creators[2].description,
                                    $.distribution_dates[0].description,
                                    $.source_caveats)

poetry run python -m data_sheets_schema.d4d_pair_consistency --full <full> --core <core> --sync-core
PASS: 78 schema-identical slots; projected slots=['resources']

poetry run python -m data_sheets_schema.d4d_pair_consistency --full <full> --core <core>
PASS: 78 schema-identical slots; projected slots=['resources']
WARNING [semantic-review-required] $.file_collections <-> $.distributions:
  deterministic matches=13 (2 at collection level, 11 at nested resource level),
  unmatched core distributions=[]
```

The three pre-sync differences were the Phase 3 corrections listed above, which were
made canonical in full and copied once. Presence matches on every shared slot, and every
schema-identical value is deeply identical including nested mapping values and list order.
No narrative field was condensed, paraphrased, reordered or omitted in core.

### Projection: `resources`

`resources` is `Dataset` in full and `CoreDataset` in core. Coverage is equal — three
resources, matched by `id`:

| id | version | issued |
|---|---|---|
| `https://doi.org/10.13026/8xbn-nq66` | 3.1.0 | 2026-05-01 |
| `https://doi.org/10.13026/k81f-qr68` | 3.0.0 | 2025-12-16 |
| `https://doi.org/10.13026/249v-w155` | 1.1 | 2025-01-17 |

Every nested schema-identical slot (`name`, `title`, `version`, `doi`, `page`, `issued`,
`publisher`, `license`, `description`) is deeply identical. No resource carries a
full-only nested slot, so nothing was dropped in the projection.

### Semantic review: `file_collections` → `distributions`

Reviewed, not merely warned about. The 13 deterministic matches were checked field by
field:

- **11 resource-level matches.** Each core `CoreDistribution` matches a nested `File`
  under `file_collections[0].resources` by `id`. `name`, `path` and `description` are
  identical in every case; `format: TSV` and `media_type: text/tab-separated-values`
  are identical on the two matched TSV members and absent on both sides for the nine
  Parquet members, because `FormatEnum` declares no Parquet value. `bytes`, `hash`,
  `md5` and `sha256` are absent on both sides — PhysioNet publishes no per-file sizes or
  checksums for a restricted-access resource, so there is nothing to reconcile and
  nothing was invented. No conflict.
- **2 collection-level matches.** `metadata` and `phenotype` match by `id` with
  identical `name`, `path` and `description`. No conflict.
- The `features` collection itself has no core counterpart, which is correct rather than
  a gap: `FileCollection` carries collection-level facts (`collection_type`,
  `file_count`) that `CoreDistribution` has no slot for, and its eleven members are
  enumerated individually in core, which is what a file-level class is for.
- **Sizes and counts.** `total_file_count` and `total_size_bytes` are absent from full
  and no distribution carries `bytes`, so the cross-scope comparison the playbook asks
  for has no operands. `file_count: 11` on the features collection agrees with the
  eleven enumerated `File` members and with the eleven file-level core distributions.
- **`dialect`** is core-only and therefore has no full counterpart to contradict. Its
  values (`delimiter: "\t"`, `header: 'true'`) come from the 3.1.0 usage note
  `pd.read_csv("demographics.tsv", sep="\t", header=0)`. It describes the TSV members
  (`audio_quality_metrics.tsv`, `static_features.tsv` and the phenotype tables) and not
  the Parquet members; `is_tabular` is left absent in both records for the same reason —
  the release mixes tensor-bearing Parquet with flat tables and the bundle does not
  characterise it either way.
- **Formats across the pair.** The formats named in `distribution_formats` (Parquet,
  TSV, JSON, WAV) are consistent with the `File.format` values, the `dialect`, and the
  `file_collections` descriptions. The WAV entry is scoped to controlled-access raw
  audio distributed via Synapse and is explicitly stated not to be part of the PhysioNet
  release.

### Cross-record identity, version and access consistency

Checked and consistent in both records: `id` / `doi` / `version_access.latest_version_doi`
all resolve to `10.13026/37yb-1t42`; `version: 3.1.0` agrees with `page`, `issued`,
`citation` and `resources[0]`; the five releases listed in
`version_access.versions_available` agree in date with the five in
`distribution_dates[0].release_dates` and with the three dated `resources`; the licence
string is identical at top level and on every resource; 833 participants appears
identically in `description`, `instances[0].counts`, `resources[3.1.0]` and
`resources[3.0.0]`; five North American sites appears identically in `description`,
`known_biases` and `known_limitations`; the IRB statements in `ethical_reviews` and
`human_subject_research` agree; the compensation figures agree between the healthsheet
and the IRB protocol ($40 / $80 / $120 maximum).

Historical values are kept only with explicit historical scope: v1.0's 12,523 recordings
and 306 participants, v2.0's 136 added participants, v3.0.0's 391 added participants,
v1.1's 512-point FFT and 513xN spectrogram dimension, and v1.1's withdrawn files all sit
on the release they describe and are not presented as current facts.

## Prompt condition

The run belongs to the **generic** condition. `d4d api prompts check --strict` reports
10 prompt files, **0 not at their pin**; `src/download/prompts/d4d_generic_arm_prompt.md`
is `canonical`. Nothing in this run's instruction is project-specific: the scope
constraint distinguishing the adult dataset from the pediatric one was read from the
`scope:` block of `data/preprocessed/source_manifest.yaml`, not from the launch text.

## Provenance record

**Not written by this agent.** The launching agent's instruction explicitly reserved
`d4d provenance record` to the launcher, overriding that step of the rendered task file.
Everything else in the task file was executed as written. The live provenance record and
`d4d runs validate` / `d4d runs check --strict` therefore remain outstanding and are the
launcher's to run; until they do, this run has no recorded instruction and no validation
verdict.

## Commands run

```bash
poetry run d4d download scope --project VOICE
poetry run d4d download scope --check --project VOICE

poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_all.yaml \
  -C Dataset  data/d4d_concatenated/claudecode_agent/2026-08-11_claude-opus-5-claudecode-generic_rep2/VOICE_d4d.yaml
poetry run linkml-term-validator validate-data \
  data/d4d_concatenated/claudecode_agent/2026-08-11_claude-opus-5-claudecode-generic_rep2/VOICE_d4d.yaml \
  --schema src/data_sheets_schema/schema/data_sheets_schema_all.yaml --target-class Dataset

poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml \
  -C CoreDataset data/d4d_concatenated/claudecode_agent_core/2026-08-11_claude-opus-5-claudecode-generic_rep2/VOICE_d4d_core.yaml
poetry run linkml-term-validator validate-data \
  data/d4d_concatenated/claudecode_agent_core/2026-08-11_claude-opus-5-claudecode-generic_rep2/VOICE_d4d_core.yaml \
  --schema src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml --target-class CoreDataset

poetry run python -m data_sheets_schema.d4d_pair_consistency --full <full> --core <core>
poetry run python -m data_sheets_schema.d4d_pair_consistency --full <full> --core <core> --sync-core
poetry run python -m data_sheets_schema.d4d_pair_consistency --full <full> --core <core>

poetry run d4d api prompts check --strict
```

## Final results

| check | result |
|---|---|
| `linkml-validate` full (`Dataset`) | **No issues found** |
| `linkml-term-validator` full | **Validation passed** |
| `linkml-validate` core (`CoreDataset`) | **No issues found** |
| `linkml-term-validator` core | **Validation passed** |
| `d4d_pair_consistency` (final, no `--sync-core`) | **PASS**, 78 schema-identical slots, projected `resources` |
| `d4d download scope --check --project VOICE` | in scope; not among the records placing the pediatric dataset outside its declared slot |
| Identifier syntax audit | 0 bare tokens, 0 undeclared CURIEs, both records |
| `d4d api prompts check --strict` | 0 prompt files off their pin |
| Prior-D4D factual reuse | none; no prior record read |
| Divergence remaining between full and core | none |
