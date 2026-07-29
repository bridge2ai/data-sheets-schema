# VOICE full/core reconciliation — crate-only arm, replicate 1

| | |
|---|---|
| Run label | `2026-07-28_claude-opus-5-crateonly_rep1` |
| Arm | CRATE-ONLY (one structured upstream source) |
| Agent runtime | Claude Code |
| Provider / model | Anthropic / `claude-opus-5[1m]` |
| Mode | four-phase project agent, crate-only |
| Temperature | 0.0 |
| Generated | 2026-07-28 |
| Full | `data/d4d_concatenated/claudecode_agent_crate_only/2026-07-28_claude-opus-5-crateonly_rep1/VOICE_d4d.yaml` |
| Core | `data/d4d_concatenated/claudecode_agent_crate_only_core/2026-07-28_claude-opus-5-crateonly_rep1/VOICE_d4d_core.yaml` |
| Provenance | `data/d4d_concatenated/claudecode_agent_crate_only_core/2026-07-28_claude-opus-5-crateonly_rep1/VOICE_provenance.yaml` (`record_mode: live`) |

## Referent

The crate's `about` target is `ark:59853/rocrate-b2ai-voice-3.0.0`, named *B2AI Voice: An
ethically-sourced, diverse voice dataset linked to health information*, version 3.0.0, published by
PhysioNet on 2025-12-16 under DOI `https://doi.org/10.13026/k81f-qr68`.

**The subject settled on is that specific release object** — the de-identified, feature-only
Bridge2AI-Voice v3.0.0 PhysioNet snapshot. Not the wider Bridge2AI-Voice project, and not the
controlled-access raw-audio tier. The crate itself forces this choice: its payload is nine derived
Parquet feature files plus six phenotype table entities, its `contentSize`, checksums, licence and
conditions-of-access all attach to the 3.0.0 snapshot, and its own prose says "the release contains
data considered low risk, including derivations such as spectrograms but not the original voice
recordings". Statements about the wider project (ongoing enrolment toward ~3,000 participants,
planned Spanish protocols, earlier versions) are recorded in the datasheet only where the schema has
a forward-looking or historical slot for them — `updates`, `version_access`, `related_datasets`,
`collection_timeframes` — not as properties of the release itself.

## Evidence boundary as actually exercised

Factual input read: `data/preprocessed/concatenated/VOICE_crate_only.txt` only (md5
`e0da1c226b05e944a617e2b0cdf9b6a0`, 320,923 bytes) — comprising
`VOICE_crate_metadata_reduced.json` and `ai_ready_score.json`.

Structural input read: `data_sheets_schema_all.yaml` (class `Dataset`),
`data_sheets_schema_core_all.yaml` (class `CoreDataset`), both resolved with LinkML `SchemaView`
rather than by reading an example record.

Not read, at any phase: `VOICE_preprocessed.txt`, `VOICE_preprocessed_with_crate.txt`, anything under
`data/preprocessed/individual/VOICE/` or `data/raw/VOICE/`, `source_manifest.yaml`,
`VOICE_crate_mapped_d4d.yaml`, `ro-crate-datasheet.html`, `ro-crate-preview.html`,
`ro-crate-croissant.json`, any file under `data/d4d_concatenated/` or `data/d4d_individual/` other
than this run's own two outputs, any evaluation or reconciliation report, and any live web content.
No prior D4D content from the parent conversation was used.

One caveat worth stating plainly: the `d4d provenance record` tool writes an `inputs.source_manifest`
block with an md5 for `data/preprocessed/source_manifest.yaml`. That hash is computed by the tool
itself; the manifest was **not** read or used as evidence in this run, and this arm is defined by the
crate-only bundle rather than by the manifest.

---

## Phase 3 — source and provenance audit

### Method

Every string value of length ≥ 45 characters in both records was tested for a verbatim window
against the decoded crate bundle. 109 strings in the full record and 82 in the core record had no
45-character verbatim window; each was inspected individually. All of them fall into three
categories, none of which introduces a dataset fact:

1. **Slot labels** I composed as an index into crate content (`purposes[0].name`,
   `tasks[1].name`, …). The crate supplies no titles for these assertions.
2. **Statements about what the crate does or does not record** (`"The crate carries an
   irbProtocolId field but leaves it empty"`, `"the crate leaves this entity's format field
   empty"`). These are facts about the evidence, deliberately kept in the record rather than
   silently dropped.
3. **Re-assemblies of crate values** (`"ark:59853/b2ai-voice-schema-ppgs (PPGs Schema)"` joins a
   crate `@id` to that entity's crate `name`; `"Licence: https://…"` prefixes a crate URL with a
   label).

### Corrections made (full corrected first, then core re-derived)

| # | Location | Was | Now | Why |
|---|---|---|---|---|
| 1 | `variables[0].description` (full only) | "string in nine of the ten feature schemas and as integer in the Torchaudio Spectrogram schema" | "string in eight of the ten feature schemas and as integer in the Torchaudio Spectrogram and Static Features schemas" | Re-counted directly: `participant_id` is typed `integer` in **two** feature schemas (`torchaudio-spectrogram`, `static-features`), not one. |
| 2 | `instances[1].description` (shared) | "stores one dense tensor per recording, keyed by participant, session and task identifiers" | "stores dense tensors keyed by participant, session and acoustic task identifiers" | The crate keys feature rows by participant/session/task; it never states a one-row-per-recording cardinality. The original wording asserted a cardinality the crate does not support. |

Correction 2 touches a shared slot, so the core record was regenerated from the corrected full
rather than patched. No Phase 2 discovery required back-porting into the full record: the only
core-exclusive content (`distributions`, `dialect`) has no full-schema counterpart.

### Internal consistency of the two records

Checked and consistent: `id` / `doi` / `version_access.latest_version_doi` all
`https://doi.org/10.13026/k81f-qr68`; `version` `3.0.0` at top level and on all 15 resources;
`issued` `2025-12-16` matching the crate `datePublished`, the v3.0.0 release date in
`distribution_dates`, and the `VOICE Phenotype Ingest` `dateCreated`; licence and conditions-of-access
URLs identical wherever repeated; `Satrajit Ghosh` consistently the governance contact in
`regulatory_restrictions`, `maintainers` and `creators`; `Vardit Ravitsky` consistently the ethical
reviewer in `ethical_reviews` and `creators`; 833 participants stated once, in `instances`.

### Defects found *inside the crate* and how each was handled

These are recorded in the datasheet itself, not suppressed, because they are properties of the
evidence a consumer of this crate would encounter.

1. **Two feature entities carry the wrong file name.**
   `…dataset-feature-sparc-periodicity` has `name: "sparc_loudness.parquet"` but
   `contentUrl: file:///features/sparc_periodicity.parquet`. `…dataset-feature-torchaudio-pitch` has
   `name: "torchaudio_spectrogram.parquet"` but `contentUrl: …/torchaudio_pitch.parquet`. Both name
   fields duplicate a *different* entity's name. Handled: crate `name` kept verbatim, with the
   conflict stated in the resource `description` and again in the corresponding core `distribution`.
2. **Two phenotype entities share a name.** `…phenotype-questionnaire` and `…phenotype-task` are
   both named "VOICE Questionnaire Tables". Recorded in the `…phenotype-task` description.
3. **Two schema entities share one ARK.** `ark:59853/b2ai-voice-schema-phenotype-confounders`
   appears twice — once as "Phenotype Confounders Schema" and once as "Phenotype Demographics
   Schema" — with an identical 547-column list. The crate therefore contains **no distinct column
   inventory for `demographics.tsv`**. `ark:59853/b2ai-voice-schema-phenotype-voice-perception` is
   likewise duplicated. Neither ARK was used as a `conforms_to_schema` value.
4. **`static_features.tsv` has a schema but no file.** The crate documents a 135-column
   "Static Features Schema" and `rai:dataPreprocessingProtocol` says the file is provided, but no
   corresponding dataset entity exists in the graph. Stated in `variables[12].description`.
5. **Per-file descriptions are placeholders.** Every feature entity reads "a datafile description"
   and every phenotype entity "A Dataset description". These carry no information and were **not**
   propagated; the `description` slot on each resource is used instead to record what is genuinely
   known or genuinely conflicting.
6. **Stated size does not match summed sizes.** `contentSize` is "12.9 GB"; the eleven byte counts
   the crate does state sum to 13,789,023,450 bytes = 12.84 GiB. Both figures are recorded in
   `distribution_formats[0].description` rather than being silently reconciled. Note the units are
   almost certainly GiB, not GB.
7. **One feature file has a different publication date.** `sparc_pitch.parquet` records
   `datePublished 08/18/2025` — the v2.0.1 release date — while every other file and the release
   itself record 12/16/2025. Kept verbatim in that resource's `issued`, with the discrepancy noted.
8. **Provenance dates run backwards.** `VOICE Features Processing` records
   `dateCreated 01/29/2026` — six weeks *after* the 2025-12-16 publication of the files it is
   recorded as generating. Recorded in `preprocessing_strategies[3]`.
9. **Attribution is thin at the point of processing.** Both computations record
   `runBy: "Alastair"` — a bare first name with no affiliation or identifier. Recorded verbatim.
10. **IRB contact fields are mis-typed.** The IRB `contactPoint.contactType` holds the telephone
    number `"(813) 974-5638"` rather than a contact type. `irbProtocolId` is present but empty.
    Both recorded in `ethical_reviews[1].review_details`.
11. **Four phenotype entities enumerate no files.** `…phenotype-{diagnosis,enrollment,questionnaire,task}`
    have empty `contentUrl` lists, no byte counts and no checksums. They therefore appear as
    `resources` but have no core `distribution`, and the phenotype `file_collection` carries no
    `file_count`.

### Interpretive mappings (stated so a reviewer can disagree)

Four values are enum or boolean mappings rather than transcriptions:

- `regulatory_restrictions.confidentiality_level: restricted` ← crate "Limited dataset available with
  Data Use Agreement".
- `license_and_use_terms.data_use_permission: [health_medical_biomedical_research, user_specific]`
  ← the registered-access DUA restricting use to authorized researchers for the health research use
  cases the crate enumerates.
- `is_tabular: true` ← every one of the 15 dataset entities is bound to a tabular schema with a
  header row and a column list.
- `known_biases[*].bias_type` and `known_limitations[*].limitation_type` ← the crate's own bias and
  limitation headings ("Sampling bias" → `sampling_bias`, "Device and environment bias" →
  `measurement_bias`, and so on).

`hipaa_compliant` was deliberately **not** set: "limited dataset" and "deidentified: true" are
suggestive but the crate never asserts HIPAA status.

### Validation re-run after Phase 3 corrections

```
poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_all.yaml \
  -C Dataset  data/d4d_concatenated/claudecode_agent_crate_only/2026-07-28_claude-opus-5-crateonly_rep1/VOICE_d4d.yaml
    -> No issues found
poetry run linkml-term-validator validate-data \
  data/d4d_concatenated/claudecode_agent_crate_only/2026-07-28_claude-opus-5-crateonly_rep1/VOICE_d4d.yaml \
  --schema src/data_sheets_schema/schema/data_sheets_schema_all.yaml --target-class Dataset
    -> Validation passed
poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml \
  -C CoreDataset data/d4d_concatenated/claudecode_agent_crate_only_core/2026-07-28_claude-opus-5-crateonly_rep1/VOICE_d4d_core.yaml
    -> No issues found
poetry run linkml-term-validator validate-data \
  data/d4d_concatenated/claudecode_agent_crate_only_core/2026-07-28_claude-opus-5-crateonly_rep1/VOICE_d4d_core.yaml \
  --schema src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml --target-class CoreDataset
    -> Validation passed
```

---

## Phase 4 — strict full/core reconciliation

### Shared-slot inventory (derived at runtime from `SchemaView`, not hand-maintained)

- `Dataset` induced slots: 94. `CoreDataset` induced slots: 79.
- Shared slot names: 77. Of these, **76 are schema-identical** and 1 (`resources`) is a projection
  (`Dataset` in full, `CoreDataset` in core).
- Full-only slots (17): `citation`, `collection_consents`, `collection_notifications`,
  `consent_revocations`, `direct_collection`, `file_collections`, `parent_datasets`,
  `participant_compensation`, `participant_privacy`, `related_datasets`, `relationships`, `splits`,
  `subsets`, `third_party_sharing`, `total_file_count`, `total_size_bytes`, `variables`.
- Core-only slots (2): `dialect`, `distributions`.

### Deterministic result

```
poetry run python -m data_sheets_schema.d4d_pair_consistency --full <full> --core <core> --sync-core
  PASS: 76 schema-identical slots; projected slots=['resources']
  WARNING [semantic-review-required] $.file_collections <-> $.distributions

poetry run python -m data_sheets_schema.d4d_pair_consistency --full <full> --core <core>
  PASS: 76 schema-identical slots; projected slots=['resources']
  WARNING [semantic-review-required] $.file_collections <-> $.distributions
```

`--sync-core` changed nothing: the core record was already deeply identical on every
schema-identical slot because it was generated by copying those slots from the Phase 3-corrected
full record rather than by re-extracting them. Narrative fields were copied verbatim — core does not
condense, paraphrase, reorder or omit any shared content.

### `resources` projection review

15 resources in full, 15 in core, same ids in the same order. Every nested slot present in the core
projection is byte-identical to its full counterpart. Exactly one full-only nested slot was dropped
from the projection: `total_size_bytes`, present on the 11 resources for which the crate states a
size and absent from `CoreDataset`. Zero unexpected divergences.

### `file_collections` ↔ `distributions` semantic review

The validator reports 0 deterministic matches because the two representations are deliberately at
different granularities: full groups the payload into 2 directory-level collections, core enumerates
11 per-file distributions. That is the intended mapping, and it reconciles exactly:

| full `file_collections` | path | `file_count` | `total_bytes` | matching core `distributions` | Σ `bytes` | agree |
|---|---|---|---|---|---|---|
| Derived acoustic feature files | `features/` | 9 | 13,788,089,083 | 9 | 13,788,089,083 | yes |
| Phenotype and questionnaire tables | `phenotype/` | *(absent)* | 934,367 | 2 | 934,367 | yes |

Field-by-field check across the two representations:

- **Names** — every core `distribution.name` equals the crate `name` of the entity with the same
  `@id`, which is also the `name` of the corresponding full `resource`. The two crate name defects
  (defect 1 above) appear identically in both records, with the same explanatory text.
- **Paths** — core `path` is the crate `contentUrl` with the `file:///` scheme stripped; each falls
  under exactly one full collection's `path` prefix.
- **Formats and compression** — core sets `format: TSV` / `media_type: text/tab-separated-values`
  only for the two entities the crate types that way. The nine Parquet entities carry no `format`,
  because the crate leaves their format empty and Parquet has no `FormatEnum` or `MediaTypeEnum`
  value. `compression` is unset in both records; the crate states none. No conflict.
- **Checksums and byte counts** — 11 `sha256` values and 11 `bytes` values, carried only in core
  because `FileCollection` has no checksum slot. Nothing in full contradicts them; the two
  collection-level `total_bytes` figures are exactly the sums shown above.
- **Access URLs and release scope** — one access URL in both records
  (`distribution_formats[0].access_urls` = the dataset DOI), and one release scope (v3.0.0,
  2025-12-16) consistent across `issued`, `distribution_dates`, `version_access` and every resource.
- **Coverage** — 11 of 15 resources have a distribution. The 4 that do not are precisely the
  phenotype group entities whose `contentUrl` lists the crate leaves empty (defect 11). This is
  under-coverage in the crate, not a full/core divergence.
- **`total_file_count` / `total_size_bytes`** — both left unset in full. The crate's only aggregate
  size statement is the string "12.9 GB", which cannot be converted to an exact integer without
  choosing GB vs GiB, and the crate never states a file count (its 15 dataset entities include 4
  groups and 2 duplicate names). Both figures are described in prose in
  `distribution_formats[0].description` instead. Nothing to contradict.
- **`dialect`** — core-only, no full counterpart. Set to `delimiter: "\t"`, `header: "true"` from
  the phenotype schemas, which are the release's only delimited-text files. The comma separator the
  crate records on the Parquet feature schemas is spurious (Parquet is binary) and was not used;
  this is stated in `distribution_formats[1].description`.
- **`is_tabular`** — `true` in both.

### Result

Zero unresolved contradictions within either record or between them.

---

## Which D4D areas the crate could not support at all

Populated: **68 of 94** `Dataset` slots, **60 of 79** `CoreDataset` slots.

Left empty because the crate says nothing that supports them:

| Area | Empty slots | What the crate offers instead |
|---|---|---|
| **Prior use** | `existing_uses`, `use_repository`, `other_tasks` | Nothing. The crate has no field for papers, models or systems that have used the data. This is the single largest gap: the whole "Uses / has it been used" branch of the Gebru questionnaire is unsupported. |
| **Vulnerable populations** | `at_risk_populations` | Only "This version only includes an adult cohort", which excludes children but says nothing about protections, assent or guardian consent. Recorded under `human_subject_research.special_populations`. |
| **Consent lifecycle** | `consent_revocations`, `collection_notifications` | The crate states consent was obtained, but nothing about whether participants were notified of collection or can withdraw. |
| **Participant compensation** | `participant_compensation` | Nothing. |
| **Contribution / extension** | `extension_mechanism` | The b2aiprep GitHub URL is a *software* location, not a mechanism for third parties to extend the dataset, so it was not repurposed. |
| **Discouraged-but-permitted uses** | `discouraged_uses` | The crate draws only a hard prohibition line ("explicitly not intended for…"), captured in `prohibited_uses`. There is no middle category. |
| **Content warnings** | `content_warnings` | Nothing about distressing content in what is retained; the crate only lists what was removed. |
| **Cohort-level composition** | `subsets`, `subpopulations[].distribution` | 21 disease-specific schemas are named, so cohorts are *identifiable*, but the crate gives no per-cohort or per-demographic participant counts, and no cohort-level file entities. |
| **Aggregate size and file count** | `total_file_count`, `total_size_bytes` | Only the string "12.9 GB", plus a graph in which 4 of 15 dataset entities enumerate no files. |
| **Instance ontology grounding** | `Instance.data_topic`, `Instance.data_substrate` | No ontology or registry identifiers of any kind — the crate uses schema.org and EVI terms only. |
| **Inter-annotator agreement** | `annotation_analyses.inter_annotator_agreement_score`, `.agreement_metric` | The crate affirmatively states these do not exist ("per-annotator disagreement statistics … are not presently included"), which is itself recorded. |
| **HIPAA status** | `regulatory_restrictions.hipaa_compliant` | "Limited dataset" and `deidentified: true` are suggestive but not an assertion of HIPAA compliance. |
| **Creator detail** | `Creator.affiliations`, `Person.orcid`, `Person.email` | 117 author names as bare strings, no affiliations, no ORCIDs, no e-mail addresses. Only one e-mail appears anywhere in the crate, and it belongs to the IRB. |
| **Dublin-Core housekeeping** | `created_by`, `created_on`, `last_updated_on`, `modified_by`, `status`, `page`, `language`, `compression`, `conforms_to_class` | Not present. `language` in particular is *not* inferable: the crate's only language statements concern participant eligibility ("fluent English speakers") and future Spanish protocols, not the released artefacts. |
| **Publisher as an identifier** | `publisher` | The crate says "PhysioNet" as a bare string; the slot range is `uriorcurie` and the crate supplies no PhysioNet URI. Rather than mint one, PhysioNet is recorded as a `maintainer` and in `distribution_formats`. |

Two further gaps are worth calling out as *shape* rather than absence:

- **Per-file descriptions are worthless.** All 15 dataset entities carry placeholder text. A crate
  can be structurally complete and still convey nothing at file level.
- **Column-level detail is uneven.** The crate documents 55 tabular schemas, but in this bundle only
  the ten feature schemas and nine small phenotype schemas retain per-column type detail; the rest
  are collapsed to name:type lists totalling well over 1,500 columns, dominated by
  `confounders`/`demographics` (547 columns, duplicated under one ARK) and `winograd` (282). Rather
  than transcribe thousands of columns or pick an arbitrary sample, `variables` is scoped to the
  identifier and payload columns of the feature layer (14 entries), which are the columns that
  describe the actual released feature tensors. That scoping decision is deliberate and is recorded
  here so it can be reversed by a reviewer who wants full column coverage.

## What the crate supports unusually well

For balance: the Croissant `rai:*` block is where this crate earns its keep. Bias, limitations,
preprocessing, annotation protocol, imputation, missing-data handling, sensitive information,
social impact and the maintenance plan are all present as substantive prose, and they populate
`known_biases`, `known_limitations`, `preprocessing_strategies`, `cleaning_strategies`,
`labeling_strategies`, `imputation_protocols`, `missing_data_documentation`, `sensitive_elements`,
`future_use_impacts` and `updates` without any inference at all. Ethics and governance are similarly
well served: IRB, ethical reviewer, governance committee, de-identification method, confidentiality
level and the registered-access licence are all explicit. The crate is strong on *how the data was
made and how it may be used*, and weak on *who made it, what has been done with it, and how much of
it there is*.

## Commands run

```bash
poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_all.yaml -C Dataset <full>
poetry run linkml-term-validator validate-data <full> \
  --schema src/data_sheets_schema/schema/data_sheets_schema_all.yaml --target-class Dataset
poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml -C CoreDataset <core>
poetry run linkml-term-validator validate-data <core> \
  --schema src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml --target-class CoreDataset
poetry run python -m data_sheets_schema.d4d_pair_consistency --full <full> --core <core> --sync-core
poetry run python -m data_sheets_schema.d4d_pair_consistency --full <full> --core <core>
poetry run d4d provenance record --project VOICE --method claudecode_agent_crate_only \
  --label 2026-07-28_claude-opus-5-crateonly_rep1 \
  --input-bundle data/preprocessed/concatenated/VOICE_crate_only.txt
```

## Files changed

| File | Change |
|---|---|
| `…/claudecode_agent_crate_only/2026-07-28_claude-opus-5-crateonly_rep1/VOICE_d4d.yaml` | created (Phase 1), then 2 Phase 3 corrections |
| `…/claudecode_agent_crate_only_core/2026-07-28_claude-opus-5-crateonly_rep1/VOICE_d4d_core.yaml` | created (Phase 2), regenerated after Phase 3 correction 2 |
| `…/claudecode_agent_crate_only_core/2026-07-28_claude-opus-5-crateonly_rep1/VOICE_provenance.yaml` | created (live record) |
| `…/claudecode_agent_crate_only_core/2026-07-28_claude-opus-5-crateonly_rep1/VOICE_reconciliation.md` | this file |

No pre-existing file was overwritten.

## Final status

- Full: schema validation **passed**, term validation **passed**. 68/94 `Dataset` slots populated,
  1,118 lines.
- Core: schema validation **passed**, term validation **passed**. 60/79 `CoreDataset` slots
  populated, 1,057 lines.
- Pair consistency: **PASS**, 76 schema-identical slots deeply identical, 1 projected slot
  (`resources`) verified, 1 related-content warning semantically reviewed above.
- Provenance record present, `record_mode: live`.

Line counts are reported as metadata, not as a quality measure.
