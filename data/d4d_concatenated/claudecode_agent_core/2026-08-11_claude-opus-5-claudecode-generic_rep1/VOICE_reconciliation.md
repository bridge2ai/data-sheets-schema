# VOICE — full/core reconciliation

- **Version label:** `2026-08-11_claude-opus-5-claudecode-generic_rep1`
- **Arm:** BASELINE (input documents only)
- **Mode:** four-phase project agent, generic prompt condition
- **Runtime / provider / model:** Claude Code / Anthropic / claude-opus-5
- **Declared input bundle:** `data/preprocessed/concatenated/VOICE_preprocessed.txt`
- **Manifest:** `data/preprocessed/source_manifest.yaml`
- **Full record:** `data/d4d_concatenated/claudecode_agent/2026-08-11_claude-opus-5-claudecode-generic_rep1/VOICE_d4d.yaml`
- **Core record:** `data/d4d_concatenated/claudecode_agent_core/2026-08-11_claude-opus-5-claudecode-generic_rep1/VOICE_d4d_core.yaml`

## Referent

`Dataset` admits one referent. The referent chosen is the **Bridge2AI-Voice adult
dataset**, identified by the PhysioNet project-level DOI
`https://doi.org/10.13026/37yb-1t42`, described as of **version 3.1.0** (published
1 May 2026, per-version DOI `10.13026/8xbn-nq66`). This is the referent the manifest
declares for VOICE, and it is the dataset that seven of the eleven bundle documents
are about.

The bundle also contains the PhysioNet page for the **Bridge2AI-Voice Pediatric
Dataset** v1.1.0 (`physionet_pediatric_1_1_0`). The manifest declares that dataset
related but distinct, to be expressed through `related_datasets`. It is recorded in
exactly that slot in the full record and nowhere else: no pediatric identifier or URL
appears in `resources`, `distribution_formats[].access_urls`,
`file_collections[].download_url`, `doi`, `page`, or `version_access`. The same
referent is held in the core record, which is byte-identical to the full record on
`id`, `title`, `name`, `description`, `doi`, `version`, `page`, `publisher` and
`version_access`.

`related_datasets` is not a `CoreDataset` slot, so the pediatric relation is carried
in the full record only. That is a schema consequence, not a divergence.

---

## Phase 3 — source and provenance audit

### 3.1 Validation (re-run)

| check | full | core |
|---|---|---|
| `linkml-validate` | No issues found | No issues found |
| `linkml-term-validator validate-data` | Validation passed | Validation passed |

### 3.2 Provenance boundary

No prior full or core D4D record was read, opened, grepped or consulted at any phase.
Nothing under `data/d4d_concatenated/`, `data/d4d_individual/`, or any
`*_crate_d4d.yaml` / `*_crate_mapped_d4d.yaml` under `data/ro-crate_packages/` was
used as evidence. The factual inputs were exactly:

- `data/preprocessed/concatenated/VOICE_preprocessed.txt` (the declared bundle,
  read in full: all eleven source documents);
- `data/preprocessed/source_manifest.yaml`, read only for the `scope:` block;
- `src/data_sheets_schema/schema/data_sheets_schema_all.yaml` and
  `data_sheets_schema_core_all.yaml` for structure;
- `.claude/agents/d4d-provenance-guard.md`, `.claude/commands/d4d-full-core.md` and
  `.claude/commands/d4d-agent.md` for method.

Phase 2 read the declared bundle plus the exact same-run Phase 1 full record at the
path carrying this run's version label. No older core was consulted, as a template or
otherwise.

One incidental exposure is recorded rather than hidden: `d4d download scope --check`
prints, for the whole corpus, the offending values found in other runs' records. Its
output was read only for this run's verdict; no value from another record entered
either output file, and the reported paths in other records (`resources[1].doi`,
`file_collections[0].download_url` and so on) are not slots this record populates with
pediatric values.

Prompt condition: `d4d api prompts check --strict` reports 10 prompt files, 0 not at
their pin — the generic condition text is at its canonical pin, so this run was made
under a published version of its condition.

### 3.3 Source disagreements resolved, and how

The bundle documents four releases of one project plus a healthsheet written for
v2.0.0. Where sources disagree, the record states what the evidence states and marks
the disagreement in the relevant object's `source_caveats` rather than silently
picking a winner.

| # | Disagreement | Resolution |
|---|---|---|
| 1 | **Participant count.** Healthsheet (v2.0.0-era): "around 833 instances". PhysioNet v3.0.0 and v3.1.0: 833 participants. PhysioNet v1.1: 12,523 recordings for 306 participants in v1.0. | `instances[0].counts: 833` for the current release; the v1.0 figures are recorded as historical in `version_access.versions_available` and flagged in `instances[0].source_caveats`. |
| 2 | **Distribution platform.** Healthsheet and documentation site: Health Data Nexus, DOI-resolvable metadata, published end of November 2024. PhysioNet pages: PhysioNet registered access, five versions Jan 2025 – May 2026. | Both recorded as separate `distribution_formats` entries. Health Data Nexus is marked as the earlier release channel; the caveat is on `distribution_formats[2].source_caveats`. |
| 3 | **Confidentiality.** Healthsheet: "No" confidential data. Data Transfer and Use Agreement: the Data is Personally Identifiable Information under OMB M-07-16, covered by a Certificate of Confidentiality. | Both retained. `confidential_elements[0].confidential_elements_present: false` describes the registered-access feature release; the DTUA statement is recorded in `source_caveats` there and in `regulatory_restrictions`, which is where the controlled-access raw audio is governed. The two describe different distributions. |
| 4 | **Free-speech transcriptions.** Healthsheet: the dataset includes transcriptions of free speech tasks. v1.1: transcripts of free speech audio were removed. v3.0.0/v3.1.0: transcriptions from open-response prompts removed. | The content warning is retained because the healthsheet asserts the content; `content_warnings[0].source_caveats` records that the later releases say those transcriptions were removed and that the sources do not settle it. |
| 5 | **Cleaning.** Healthsheet: no pre-processing for cleaning, no instances excluded. v3.0.0/v3.1.0: recordings and features removed for privacy. | Both recorded in `cleaning_strategies[0]`, with the caveat that the removals were privacy exclusions rather than quality cleaning, which is consistent with both statements read narrowly. |
| 6 | **Grant number.** Five renderings: `OT2OD032720`, `3OT2OD032720-01S1`, `3OT2OD032720-01S3`, `1OT2OD032720-01`, plus two corrupted strings (`3TF-OT2ActfOD032720Projectf01S1`, `Award #3Tf-OTOD03272001S2`). | The four well-formed numbers are recorded as four `Grant` objects, since they identify the parent award and distinct supplements rather than being variants of one number. The two corrupted strings are not recorded as grant numbers; `funders[0].source_caveats` names them. |
| 7 | **Ravitsky affiliation.** Documentation site and white paper: The Hastings Center. Feasibility publication: University of Montreal. | The Hastings Center recorded (two sources, both current); the disagreement is in that creator's `source_caveats`. |
| 8 | **Rudzicz affiliation and spelling.** Documentation site / IRB / white paper: University of Toronto. Feasibility publication: Dalhousie University. Documentation site spells the surname "Rudzizc". | University of Toronto and the spelling "Rudzicz" recorded (PhysioNet author list and publications); disagreement in `source_caveats`. |
| 9 | **Institution count.** Documentation site: 12 collaborators. White paper: 50 experts from 12 institutions. Feasibility publication: 14 institutions for app development. IRB Annex C: a partly different list adding Massachusetts Eye and Ear and Emory University. | The twelve institutions named on the documentation site are recorded as the consortium's affiliations; the other counts are in `creators[0].source_caveats`. |
| 10 | **Phenotype layout.** v3.0.0 places `adhd_adult`, `psychiatric_history` and `ptsd_adult` under `diagnosis/`; v3.1.0 places them under `questionnaire/`. | v3.1.0 layout followed, because v3.1.0 is the described release and its release notes state that phenotypic files were rearranged. Recorded in the diagnosis collection's `source_caveats`. |
| 11 | **Update cadence.** Healthsheet: semi-annual. PhysioNet history: five releases in sixteen months. | Both in `updates`: the stated cadence in `frequency`, the observed cadence beside it, and the tension in `source_caveats`. |
| 12 | **Spectrogram parameters.** v1.1: 512-point FFT, 513xN. v3.0.0/v3.1.0: 400-point FFT, 201xT. | Current values used throughout; the v1.1 values recorded explicitly as historical at the end of `preprocessing_strategies[1].preprocessing_details`. |
| 13 | **Feature record counts.** Differ between v3.0.0 and v3.1.0 and between files within one release. | v3.1.0 counts stated per file, with the v3.0.0 count given in parentheses for the spectrogram file; the divergence between files is recorded as an anomaly with its stated cause. |

Facts present in the bundle but attributable to a **different study** were deliberately
not attributed to this dataset: the app feasibility study (PMC12037532, 47 participants,
USF IRB 004890, no financial incentive, CRediT roles for that article's authors) is a
usability study of the collection application, not of the dataset. Its IRB number,
participant count and compensation statement are absent from the record; its
description of the app and of the acoustic-task inventory is used only where it
corroborates the collection documentation.

### 3.4 Unsupported / stale / mis-scoped assertions found and corrected

- **`is_tabular`** was considered and omitted from both records. The evidence supports
  both readings — dense Parquet tensors and one-row-per-participant TSVs — and a
  boolean would force a choice the sources do not make. Omission over inference.
- **`data_topic` and `data_substrate`** (range `uriorcurie`, `values_from`
  `B2AI_TOPIC` / `B2AI_SUBSTRATE`) were omitted: no registry term could be verified
  from the declared inputs, and the slot descriptions say to prefer omission and use
  `instance_type` for prose. `instances[0].instance_type` carries the prose.
- **`total_file_count`, `total_size_bytes`, `file_count`, `total_bytes`, checksums**
  omitted throughout: no source states a file count or a byte size, and counting the
  published listing would assert a number the sources do not.
- **`imputation_protocols`, `annotation_analyses`** omitted: no imputation and no
  inter-annotator agreement analysis is described (a single labeller per item makes
  agreement uncomputable, which is stated in `labeling_strategies[0].labeling_details`).
- **`download_url`** omitted at dataset level: every distribution is behind
  credentialing, and no direct download URL exists in the sources.
- **`contact_person` / `governance_committee_contact`** were populated only where the
  bundle names a person. `DACO@b2ai-voice.org` is an office, not a person, so it is
  recorded in prose rather than forced into a `Person`-ranged slot; the healthsheet's
  curator and platform emails are redacted in the preprocessed source as
  `[email protected]` and are not recorded at all.

### 3.5 Shape audit

Checked against the same contract as the API pipeline's audit phase.

- **Prose in a list-ranged slot:** one found and fixed —
  `external_resources[0].restrictions` was written as a single string against a
  multivalued slot, and was split into two list entries.
- **Object where the schema wants a reference:** three found and fixed.
  `Creator.principal_investigator` and `EthicalReview.contact_person` are ranged
  `Person`, whose `id` is an identifier, so LinkML renders them as scalar references,
  not inlined objects. The slot descriptions ask for a person's name; the values are
  now name strings, and the structured detail that would have lived in the `Person`
  object (degrees, department, email, telephone) was moved into the enclosing object's
  `description` / `review_details` rather than dropped.
- **Datetime format:** `issued` required RFC3339; `2026-05-01T00:00:00` was corrected
  to `2026-05-01T00:00:00+00:00`.
- **Enum values:** all `bias_type`, `limitation_type`, `collection_type`, `file_type`,
  `format`, `media_type`, `credit_roles`, `role`, `data_use_permission`,
  `hipaa_compliant`, `confidentiality_level` and `relationship_type` values are drawn
  from the schema's permissible values. Parquet files carry **no** `format` or
  `media_type` because `FormatEnum` and `MediaTypeEnum` define no Parquet value;
  the format is stated in the collection `description` instead of being coerced into a
  wrong enum member.
- **Slot-filling order:** `notes` is used **zero** times in either record. Narrative
  lives in `description`; structured content lives in structured slots
  (`Creator.affiliations`, `FundingMechanism.grants`, `Grant.grant_number`,
  `HumanSubjectResearch.irb_approval`, `IPRestrictions.restrictions`,
  `VersionAccess.versions_available`, `FileCollection.resources`); all evidence
  commentary is in `source_caveats` (16 occurrences in the full record) and nowhere
  else.
- **Commentary inside a name or identifier:** none. Names are plain names; affiliation
  values are institution names or named departments within them.
- **Identifier syntax (#402):** audited with `data_sheets_schema.identifiers`. Full
  record: 205 identifier-ranged values, 9 absolute URIs, 196 declared-prefix CURIEs,
  **0 undeclared CURIEs, 0 bare tokens**. Core record: 182 values, 9 URIs, 173
  declared CURIEs, 0 unresolvable. One convention throughout: absolute URIs where the
  entity has one (DOIs, GitHub repositories, Synapse, PhysioNet), `d4d:` CURIEs
  otherwise. The three repeated ids (`https://github.com/sensein/b2aiprep`,
  `.../senselab`, `https://github.com/eipm/bridge2ai-redcap`) are the same `Software`
  entity referenced from more than one `used_software` list — agreement by reference,
  which is what the audit exists to make possible.

### 3.6 Internal consistency of repeated facts

Cross-checked and consistent within each file and between them:

- **Identifiers.** `id` = `https://doi.org/10.13026/37yb-1t42` (project-level) =
  `version_access.latest_version_doi`. `doi` = `10.13026/8xbn-nq66` (v3.1.0-specific)
  = the DOI in `citation` = the v3.1.0 entry of `versions_available`. These two DOIs
  are deliberately different and the distinction is stated in
  `version_access.version_details`: the project DOI resolves to the latest version,
  the per-version DOI identifies this release.
- **Version.** `version: 3.1.0` agrees with `page`, `issued`
  (2026-05-01 = the v3.1.0 publication date), `citation`, `distribution_dates` and the
  last entry of `versions_available`.
- **Licence and access.** `license`, `license_and_use_terms.license_terms`,
  `distribution_formats[0].description`, `regulatory_restrictions.confidentiality_level`
  and `third_party_sharing.description` all say the same thing: Bridge2AI Voice
  Registered Access License, Registered Access Agreement, credentialed users only, no
  training, no fees.
- **Counts.** 833 participants appears in `description`, `instances[0].counts` and
  `instances[0].description`, and nowhere contradicts itself. Five sites appears in
  `description`, `known_biases[0]`, `known_limitations[2]` and `sampling_strategies[0]`.
- **People and organizations.** The 16 `Creator` entries use one spelling per person
  and one affiliation name per institution, matching the twelve institutions listed in
  `creators[0].affiliations`.

### 3.7 Phase 2 discoveries back-ported to full

None. Phase 2 found no fact in the bundle that the full record had missed and no value
the bundle contradicts, so no back-port was required and the full record was not
edited after Phase 1 validation except for the shape fixes in §3.5 and the
`conforms_to_class` removal in §4.2, both of which were re-validated.

---

## Phase 4 — strict full/core reconciliation

### 4.1 Schema-derived shared slots

Derived at runtime with LinkML `SchemaView` via `load_pair_schema()`; no hand-written
field list.

- **Schema-identical slots: 78.** Deep identity required and achieved.
- **Projected slots: 1** — `resources` (`Dataset` in full, `CoreDataset` in core).
  Absent from both records, so the projection is vacuous and passes on presence.
- **Full-only slots populated:** `file_collections`, `citation`, `related_datasets`,
  `splits`, `relationships`, `direct_collection`, `collection_notifications`,
  `collection_consents`, `consent_revocations`, `participant_privacy`,
  `participant_compensation`, `variables`. `CoreDataset` declares none of these, so
  they cannot appear in core.
- **Core-only slots:** `distributions` (populated, see §4.3), `dialect` (omitted, see
  §4.4), `resources` (absent).

`d4d_pair_consistency` result, run first with `--sync-core` and then again
independently — both **PASS**, identical output:

```
PASS: 78 schema-identical slots; projected slots=['resources']
WARNING [semantic-review-required] $.file_collections <-> $.distributions:
  Phase 4 must semantically review related distribution content;
  deterministic matches=55 (1 at collection level, 54 at nested resource level),
  unmatched core distributions=[]
```

The `--sync-core` pass changed nothing: the core file's parsed content was identical
before and after, because core was constructed by copying the 78 schema-identical
slots from the Phase-3-audited full record rather than by re-extraction. That is the
intended relationship — core is the semantic exchange layer subset, not a second
opinion.

### 4.2 One slot that cannot be correct in both records: `conforms_to_class`

**Finding.** `conforms_to_class` has an identical induced signature in `Dataset` and
`CoreDataset`, so `load_pair_schema()` classifies it as schema-identical and
`_append_identity_errors` requires the two records to carry the same value. Its own
schema description says the opposite: "`Dataset` for a full datasheet, `CoreDataset`
for a core one". The slot is therefore specified to differ between the two records and
validated to be the same in both. It cannot satisfy both.

**Action taken.** The slot is **omitted from both records**. Writing `Dataset` in the
core record would be a false statement about what the core record instantiates;
writing `CoreDataset` there fails the Phase 4 gate; writing it in full only fails the
same gate on presence. Omission is the only option that asserts nothing false. The
sibling slot `conforms_to_schema` is unaffected and carries
`https://w3id.org/bridge2ai/data-sheets-schema` identically in both.

This is a schema/validator defect, not a property of this dataset, and it will recur
for every project until either the slot's description or its treatment in
`d4d_pair_consistency` changes. It is reported here rather than worked around
silently.

### 4.3 Related-content mapping: `file_collections` → `distributions`

`FileCollection` is collection-level (`file_count`, `total_bytes`, `collection_type`);
`CoreDistribution` is file-level (`bytes`, `hash`, `md5`, `sha256`, `path`,
`media_type`). The core record therefore enumerates **one distribution per file**,
plus one per collection that has no enumerated files.

| full `file_collections` entry | files | core `distributions` | match level |
|---|---|---|---|
| `features/` | 11 | 11 | nested resource |
| `metadata/` | 0 (described, not enumerated) | 1 | collection |
| `phenotype/demographics/` | 1 | 1 | nested resource |
| `phenotype/confounders/` | 1 | 1 | nested resource |
| `phenotype/enrollment/` | 3 | 3 | nested resource |
| `phenotype/diagnosis/` | 18 | 18 | nested resource |
| `phenotype/questionnaire/` | 13 | 13 | nested resource |
| `phenotype/task/` | 7 | 7 | nested resource |
| **total** | **54 files + 1 collection** | **55** | 54 nested + 1 collection |

Coverage is complete in both directions: every core distribution matched (unmatched
= `[]`), and every full collection is represented either by its files or by itself.

Semantic review of the mapped fields, as required by the warning:

- **Identifiers.** Each distribution carries the same `id` as its counterpart, so
  matching is by `id` rather than by the weaker `path` or `name` fallback.
- **Names and paths.** Identical strings, projected field-for-field. Zero `path`
  conflicts reported.
- **Formats.** The 43 tab-separated members carry `format: TSV` and
  `media_type: text/tab-separated-values` in both records. The 9 Parquet members and
  the `metadata/` collection carry neither, in both records, because no enum member
  exists for Parquet — the absence agrees, and it agrees for a stated reason rather
  than by accident.
- **Compression.** Absent everywhere in both. No source describes any collection as a
  compressed archive; zero conflicts reported.
- **Checksums and byte counts.** Absent everywhere in both. No source publishes a
  checksum or a size. `bytes` vs `total_bytes` therefore has nothing to conflict over,
  and the validator reported no size conflict.
- **Descriptions.** The eleven feature files and the `metadata/` collection carry the
  same descriptions in both records, including the per-file record counts
  (29,278 / 32,522 / 28,640 / 31,855 / 31,872 / 29,289). The phenotype files carry no
  per-file description in either record.
- **Release scope.** Every file name and every record count comes from the v3.1.0
  page, so the two records describe the same release. The one place a v3.0.0 figure
  appears (29,020 spectrograms) is explicitly labelled as such in the same string in
  both records.

### 4.4 Other related, non-identical representations

- **`total_file_count` / `total_size_bytes` vs distribution-level values.** All four
  are absent. Nothing to compare, nothing in conflict. Had they been present, the
  scopes would have differed anyway: the collection totals cover only the enumerated
  files, and the sources enumerate data files without their JSON data dictionaries.
- **`dialect` (core-only) vs formats and `is_tabular`.** `dialect` is **omitted**. The
  evidence for a tab delimiter and a header row is explicit (`pd.read_csv(...,
  sep="\t", header=0)`, "tab delimited file with one row per unique participant"), but
  a single dataset-level `FormatDialect` would assert a delimiter for the nine Parquet
  members too, which have none. `FormatDialect` carries no scoping or description slot
  that would let the claim be limited to the TSV members. `is_tabular` is omitted from
  both for the same reason (§3.4). The three therefore agree by all being absent.
- **Top-level identity/version/access facts vs `versions_available`,
  `distribution_dates` and `distribution_formats`.** Checked in §3.6; consistent, with
  the project DOI / per-version DOI distinction stated rather than left implicit.
- **Historical vs current release.** Distinguished, not treated as contradiction, in
  four places: the v1.0 recording and participant counts, the v1.1 FFT size and
  spectrogram dimensions, the v3.0.0 feature record count, and the v3.0.0 phenotype
  layout. Each is labelled with the release it describes in the same string as the
  current value.

### 4.5 Scope check

```
d4d download scope --check --project VOICE --strict     → exit 0
```

77 records checked corpus-wide; none is about a dataset its project declares distinct,
including both records from this run. The 32 records flagged for placing a
related-but-distinct dataset outside its declared slot (143 values) are all from
earlier runs; **neither record from this run appears in that list**. The pediatric
dataset appears in this run in exactly one place, `related_datasets[0]` of the full
record, with `relationship_type: is_supplemented_by` and a description stating that it
is a distinct dataset with its own DOI, protocol, ethics approval, cohort and site and
is not a version of the adult dataset.

`is_supplemented_by` is the closest available member of
`DatasetRelationshipTypeEnum` for a companion release by the same consortium covering
a distinct cohort. It is a judgement, recorded here as one: the enum offers no term for
"sibling dataset within the same programme", and `is_part_of`, `derives_from` and
`is_version_of` would each be more wrong.

### 4.6 Files changed

| file | change |
|---|---|
| `.../claudecode_agent/{label}/VOICE_d4d.yaml` | created (Phase 1); shape fixes §3.5; `conforms_to_class` removed §4.2 |
| `.../claudecode_agent_core/{label}/VOICE_d4d_core.yaml` | created (Phase 2) from the audited full record; rewritten unchanged by `--sync-core` |
| `.../claudecode_agent_core/{label}/VOICE_reconciliation.md` | this report |

No file outside the three declared output paths was written.

### 4.7 Commands run

```bash
# Phase 1 / Phase 3 — full
poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_all.yaml \
  -C Dataset .../claudecode_agent/{label}/VOICE_d4d.yaml
poetry run linkml-term-validator validate-data .../claudecode_agent/{label}/VOICE_d4d.yaml \
  --schema src/data_sheets_schema/schema/data_sheets_schema_all.yaml --target-class Dataset

# Phase 2 / Phase 3 — core
poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml \
  -C CoreDataset .../claudecode_agent_core/{label}/VOICE_d4d_core.yaml
poetry run linkml-term-validator validate-data .../claudecode_agent_core/{label}/VOICE_d4d_core.yaml \
  --schema src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml --target-class CoreDataset

# Phase 3 — provenance and identifier audit
poetry run d4d api prompts check --strict
poetry run python -c "from data_sheets_schema.identifiers import audit_record, ..."

# Phase 4 — pair consistency
poetry run python -m data_sheets_schema.d4d_pair_consistency \
  --full .../VOICE_d4d.yaml --core .../VOICE_d4d_core.yaml --sync-core
poetry run python -m data_sheets_schema.d4d_pair_consistency \
  --full .../VOICE_d4d.yaml --core .../VOICE_d4d_core.yaml

# Phase 4 — scope
poetry run d4d download scope --check --project VOICE --strict
```

### 4.8 Final results

| measure | value |
|---|---|
| Full record top-level slots | **81** |
| Core record top-level slots | **69** |
| Full schema validation | **pass** |
| Full ontology-term validation | **pass** |
| Core schema validation | **pass** |
| Core ontology-term validation | **pass** |
| Schema-identical shared slots | **78**, all deeply identical, identical presence |
| Projected slots | 1 (`resources`), absent from both |
| Pair consistency | **PASS**, 0 errors, 1 semantic-review warning (reviewed in §4.3) |
| `distributions` ↔ `file_collections` | 55 matched, 0 unmatched, 0 conflicts |
| Scope check | **in scope**, 0 out-of-slot values |
| Identifier audit (full / core) | 205 / 182 values, **0 unresolvable** in either |
| Unresolved contradictions | **none** |

Line counts are informational metadata and not a quality gate. Slot counts are
observations of what the evidence supported, not targets: no target count, expected
density, or relationship to any other arm or project was applied.

### 4.9 Outstanding items for the launcher

The live provenance record is written by the launcher, not by this agent, so it is not
present at the time of writing and `d4d runs check --strict` has not been run for this
run. Once `d4d provenance record` and `d4d runs validate` have been run for label
`2026-08-11_claude-opus-5-claudecode-generic_rep1`, the artifacts named above are final
and will hash to what they contained when this report was written.
