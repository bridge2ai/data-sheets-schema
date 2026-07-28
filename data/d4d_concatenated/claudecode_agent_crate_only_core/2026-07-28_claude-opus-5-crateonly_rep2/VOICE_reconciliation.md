# VOICE full/core reconciliation — crate-only arm, rep2

| | |
|---|---|
| Run label | `2026-07-28_claude-opus-5-crateonly_rep2` |
| Arm | CRATE-ONLY (one structured source, no documents) |
| Agent runtime | Claude Code |
| Provider | Anthropic |
| Model | `claude-opus-5[1m]` |
| Mode | four-phase project agent, crate-only |
| Temperature | 0.0 |
| Generated | 2026-07-28 |
| Full | `data/d4d_concatenated/claudecode_agent_crate_only/2026-07-28_claude-opus-5-crateonly_rep2/VOICE_d4d.yaml` |
| Core | `data/d4d_concatenated/claudecode_agent_crate_only_core/2026-07-28_claude-opus-5-crateonly_rep2/VOICE_d4d_core.yaml` |
| Provenance | `data/d4d_concatenated/claudecode_agent_crate_only_core/2026-07-28_claude-opus-5-crateonly_rep2/VOICE_provenance.yaml` (`record_mode: live`) |

## Evidence boundary

The single factual input was
`data/preprocessed/concatenated/VOICE_crate_only.txt` (320,923 bytes, md5
`e0da1c226b05e944a617e2b0cdf9b6a0`), containing two artifacts:
`VOICE_crate_metadata_reduced.json` (75-entity RO-Crate JSON-LD graph) and
`ai_ready_score.json` (AI-readiness self-assessment).

No other VOICE material was opened. Specifically not read: the `_preprocessed`
or `_with_crate` bundles, `data/preprocessed/individual/VOICE/`,
`data/raw/VOICE/`, `data/preprocessed/source_manifest.yaml`, the crate's own
`ro-crate-datasheet.html` / `ro-crate-preview.html` /
`ro-crate-croissant.json` / `VOICE_crate_mapped_d4d.yaml`, any prior D4D record
or evaluation, and any live web content. No prior D4D factual content entered
this run from the parent conversation.

Two incidental notes, recorded for completeness rather than because they
affected the output:

- The shared scratchpad contained a stale build script from another agent's
  **CM4AI** run, opened while creating a working file. It contains no VOICE
  facts and was not used; the working script was renamed to avoid the
  collision.
- `d4d provenance record` hashes `data/preprocessed/source_manifest.yaml`
  automatically as an environment fingerprint. The manifest was not read as a
  factual input and is not the source of any value in either record.

Structure came only from the LinkML schemas, resolved at runtime with
`SchemaView`: `Dataset` in `data_sheets_schema_all.yaml` (94 induced slots) and
`CoreDataset` in `data_sheets_schema_core_all.yaml` (79 induced slots). No
prior YAML was used as a template, and no `d4d:docExample` value was copied.

## Referent

**The subject is the Bridge2AI-Voice v3.0.0 feature-only public release
distributed through PhysioNet, packaged as RO-Crate
`ark:59853/rocrate-b2ai-voice-3.0.0`** — not the Bridge2AI-Voice project, and
not the controlled-access raw-audio tier.

The crate settles this itself. Its root entity is the only node carrying a
name, description, DOI, licence, and access conditions, and that description
scopes the object explicitly: *"Bridge2AI-Voice v3.0 contains data for 833
participants across five sites in North America… The release contains data
considered low risk, including derivations such as spectrograms but not the
original voice recordings."* Every one of the 15 documented data entities
carries `version: 3.0.0`, and `rai:dataCollectionRawData` draws the boundary a
second time by placing the raw audio behind "a separate controlled-access
process". Choosing the project as referent would have required importing scope
the crate does not assert; choosing the raw-audio tier would describe data the
crate explicitly excludes.

The record therefore keeps the ongoing project visible only where the crate
itself frames it as context (enrolment toward ~3,000 participants by November
2026, planned Spanish-language protocols), always inside `known_limitations`,
`collection_timeframes`, or `updates` where the forward-looking scope is
explicit.

## Phase 1 — full record

Built directly from the crate graph. Values were extracted programmatically
from the JSON rather than retyped, so identifiers, digests, byte counts, and
the 117-name author list are exact.

68 top-level slots populated. Notable structural decisions:

- **File entities → `file_collections` (15 entries).** `Dataset.resources`
  was left unused; each crate data entity became one `FileCollection` keyed by
  its ARK, carrying `path`, `file_count`, `total_bytes`, `conforms_to_schema`,
  `issued`, and `version`.
- **Placeholder descriptions dropped.** Every crate file entity carries the
  literal text `"a datafile description"` or `"A Dataset description"`.
  Copying those forward would have manufactured the appearance of
  documentation, so per-file `description` is omitted and the placeholder is
  recorded as a finding under `anomalies` instead.
- **Author list.** The crate gives 117 names with no affiliation or role, and
  repeats the identical list on all 15 files. Emitting 117 name-only `Creator`
  objects would inflate both records without adding information, so `creators`
  holds two entries: the principal investigator, and an authors entry whose
  description carries all 117 names verbatim. Every name was verified present.
- **Date encoding.** The crate's `datePublished` values are date-only
  (`12/16/2025`); LinkML `issued` is a `datetime`, so they are encoded as
  `2025-12-16T00:00:00Z`. The midnight component is an encoding artefact, not
  a claim.

Validation: clean on first run.

## Phase 2 — core record

Inputs: the same crate bundle plus the validated Phase 1 file at its exact
same-run path. No older core was consulted; the `CoreDataset` field inventory
was derived from the merged core schema at runtime.

Core carries 59 slots: every core-eligible slot the full record populates,
copied by value, plus the core-only `distributions`.

Ten populated full slots have no `CoreDataset` counterpart and are absent from
core by schema, not by omission: `citation`, `file_collections`,
`relationships`, `splits`, `direct_collection`, `collection_consents`,
`participant_privacy`, `third_party_sharing`, `variables`, `related_datasets`.

Phase 2 surfaced one asymmetry worth naming: **`FileCollection` has no checksum
slot, but `CoreDistribution` has `sha256`.** The crate's 11 SHA-256 digests
therefore survive only in core. This is a schema limitation, not a
full/core inconsistency — full has nowhere to put them.

## Phase 3 — source and provenance audit

A dedicated audit script re-derived every factual assertion from the crate and
compared it to both records: identity scalars, the DOI, licence and access
URLs, publisher, version, keywords, citation, the 117 author names, the 833
participant count, all 15 file paths, byte counts, SHA-256 digests, versions
and publication dates, the b2aiprep software record, and every `rai:*` prose
list. **All checked assertions matched.** A second pass flagged all 191 record
strings of ≥60 characters and tested each for verbatim presence in the crate;
115 were exact, and each of the remaining 76 was reviewed by hand.

### Corrections applied (full first, then core re-derived)

1. **Scope drift in `cleaning_strategies[0].cleaning_details[1].`** The draft
   read "Tabular phenotype and questionnaire files were audited…", narrowing
   the crate's "*The data release team audited the combined phenotype **and
   feature** tables*". Restored to the crate's scope.
2. **Second `associatedPublication` recovered.** The crate lists two associated
   publications: the dataset citation (already in `citation`) and PhysioNet's
   own resource paper (Goldberger et al., 2000, RRID:SCR_007345). The second
   had no home; it was added to `external_resources`, which already records
   PhysioNet-hosted dependencies. Being a shared identity slot, it propagated
   to core.

No value in either record originates from anything other than the crate
bundle. Both files were re-validated after each correction.

### Internal contradictions found *in the crate* and how they were resolved

These are recorded in the record itself under `anomalies` (entry
`d4d:voice-3.0.0-anomaly-crate-metadata`), because a consumer of the
distributed package will hit them:

| Observation | Resolution |
|---|---|
| `…dataset-feature-sparc-periodicity` is **named** `sparc_loudness.parquet` but its `contentUrl`, ARK and schema all say *periodicity* | Three-to-one within the crate; the file path supplies the name |
| `…dataset-feature-torchaudio-pitch` is **named** `torchaudio_spectrogram.parquet` but its `contentUrl`, ARK and schema all say *pitch* | Same resolution |
| `…phenotype-questionnaire` and `…phenotype-task` share the name "VOICE Questionnaire Tables" | Both kept, distinguished by ARK |
| Two different schemas share the id `…schema-phenotype-confounders` (one Confounders, one Demographics); `…schema-phenotype-voice-perception` is declared twice | Recorded as an anomaly; neither is referenced by a data entity |
| `computation-b2ai-voice-features-processing` has `dateCreated 01/29/2026`, **after** the 12/16/2025 publication of the files it generated | Both dates recorded as stated; contradiction reported, not silently reconciled |
| `copyrightNotice` says 2026; the release is dated 2025-12-16 | Copyright text recorded verbatim in `ip_restrictions` |
| `sparc-pitch` carries `datePublished 08/18/2025` while every other file carries 12/16/2025 | Per-file date preserved as stated |
| `ppgs` records its size under `size`; all others use `contentSize` | Both keys read; value identical in meaning |
| 46 phenotype column schemas are documented but linked from no data entity, unlike the 9 feature schemas | `conforms_to_schema` set only where the crate actually links it |
| `participant_id` is typed `string` by the 9 feature schemas and `integer` by the Static Features Schema | `data_type` omitted; conflict recorded in `variables[0].quality_notes` |
| The 9 Parquet schemas declare a comma separator; the 46 phenotype schemas declare a tab | Core `dialect` left empty (see below) |
| A Static Features Schema is declared with no corresponding data entity | Recorded as an anomaly |
| `irbProtocolId`, `completeness`, and every feature file's `additionalType`/`format` are present but empty | Left empty; not inferred |

### Aggregate figures that could not be reconciled

The crate declares `contentSize: "12.9 GB"`. The sum of the 11 stated per-file
sizes is **13,789,023,450 bytes**, which is 12.84 GiB or 13.79 GB — matching
neither the binary nor the decimal reading of "12.9 GB", and in any case
excluding the four multi-file table entities that carry no size at all.
`total_size_bytes` was therefore left empty rather than published as a number
the crate does not support.

Likewise `total_file_count`: the crate documents 15 dataset entities (four of
which are unsized multi-file groups), while the AI-readiness self-assessment
reports checksums for "11 of 17" *files*. 15 and 17 count different things and
neither is a file count for the release. Left empty; both stated figures are
preserved verbatim in `distribution_formats[0].description`.

## Phase 4 — strict full/core reconciliation

Shared slots were derived at runtime with `SchemaView`, not from any
hand-maintained list.

- **76 schema-identical slots**, all deeply identical and identically present
  in both records, narrative fields included. Core condenses, paraphrases,
  reorders, and omits nothing. This is structural: core was generated by
  copying values from the Phase 1 full record, and was regenerated from the
  corrected full record after the Phase 3 edits.
- **1 projected slot** (`resources`, `Dataset` → `CoreDataset`) — unused in
  both records, so absent from both.

### Related-content review (`file_collections` ↔ `distributions`)

The validator matched **15 of 15 distributions deterministically by ARK, with
zero unmatched**. Semantic review of each pair:

- `name`, `path`, and byte counts are equal in all 15 pairs
  (`FileCollection.total_bytes` ≡ `CoreDistribution.bytes`); verified
  independently of the validator.
- `compression` is absent from both sides — the crate declares none.
- **SHA-256** appears on the 11 crate-supplied digests in core only, because
  `FileCollection` has no checksum slot. Not a conflict.
- **Format**: the 6 TSV-declared entities carry `format: TSV` and
  `media_type: text/tab-separated-values` in core. The 9 Parquet files carry
  neither, because `FormatEnum` and `MediaTypeEnum` have no Parquet member —
  so the format of the nine largest files (13.79 of 13.79 GB of sized content)
  is not machine-encodable in either record. Recorded in prose in
  `distribution_formats[0].description`.
- **Release scope** is consistent: every collection and every distribution
  belongs to v3.0.0, matching top-level `version: 3.0.0`, `version_access`
  (`latest_version_doi` = the top-level DOI, `versions_available` 1.0 → 3.0.0),
  and `distribution_dates`, which lists v3.0.0 at 2025-12-16 — the same date as
  top-level `issued`. Historical releases appear only inside version history and
  are not treated as contradicting the current release.
- `is_tabular: true` agrees across both records and is consistent with the
  crate's 55 column schemas and TSV media types.
- Top-level identity facts (`id`, `doi`, `licence`, `publisher`, `version`) are
  identical across full, core, and the crate.

`dialect` (core-only) was **left empty deliberately**: the crate declares
per-file dialects that disagree (46 schemas tab-delimited, 9 comma-delimited,
all with headers), and a single top-level `FormatDialect` cannot represent a
mixed-format release without asserting something false.

**Zero unresolved contradictions within or between the two records.**

## What the crate could NOT support at all

These D4D areas are empty because the crate contains no evidence for them.
This is the finding, not a gap to be filled.

**Wholly unsupported top-level slots**

| Slot | Note |
|---|---|
| `subsets` | No declared subsets or splits |
| `content_warnings` | Nothing stated |
| `collection_notifications` | No statement about notifying individuals |
| `consent_revocations` | No revocation or withdrawal mechanism |
| `participant_compensation` | Nothing stated |
| `at_risk_populations` | No vulnerable-population protections; only "adult cohort" |
| `data_protection_impacts` | No DPIA named; ethics review ≠ DPIA |
| `existing_uses` | No downstream use or publication is recorded |
| `use_repository` | None |
| `other_tasks` | None beyond the stated use cases |
| `extension_mechanism` | No contribution mechanism |
| `parent_datasets` | None |
| `total_file_count`, `total_size_bytes` | Irreconcilable aggregates (above) |
| `compression` | Not stated |
| `created_by`, `modified_by`, `status`, `page`, `download_url`, `was_derived_from`, `created_on`, `last_updated_on` | Not stated |

**Populated areas with unsupported sub-fields**

- `informed_consent`: consent is confirmed, but `consent_type`,
  `consent_documentation` beyond one sentence, `withdrawal_mechanism`, and
  `consent_scope` are absent.
- `human_subject_research.irb_approval`: the reviewing IRB is named in full
  (with address and contact), but `irbProtocolId` is present-and-empty, so no
  protocol number exists.
- `annotation_analyses`: `inter_annotator_agreement_score` and
  `agreement_metric` are absent — the crate explicitly says per-annotator
  disagreement statistics are *not* included.
- `license_and_use_terms.data_use_permission`: the crate describes registered
  access and a DUA in prose but states no DUO-style permission code, so no
  enum value was asserted.
- `regulatory_restrictions.hipaa_compliant`: not stated. `fdaRegulated: false`
  and `deidentified: true` are recorded; HIPAA status is not inferred from them.
- `updates.frequency`: no schedule — updates are "planned as additional
  participants are enrolled".
- `retention_limit.retention_period`: no period; only "older versions remain
  accessible".
- `collection_timeframes.start_date` / `end_date`: only "roughly between 2023
  and 2025", too coarse for a date.
- `instances[1].counts`: the number of recordings, sessions, or feature rows is
  never stated. Only the 833-participant count exists.
- `subpopulations[*].distribution`: **the single largest gap.** The crate names
  21 disease cohorts and confirms coarsened age/sex/country variables exist,
  but reports no count, proportion, or demographic breakdown for any of them.
  A reader learns the dataset has 833 participants and cannot learn how many
  are in any cohort or demographic group.
- `variables`: the crate documents 55 column schemas, but 36 are collapsed
  summaries and the columns carry generated descriptions ("Column
  participant_id"). Only the three cross-file keys (`participant_id`,
  `session_id`, `task_name`) were recorded; the remainder are names and types
  without semantics.

**Facts the crate has but the D4D schema cannot hold**

- `evi:merkleRootHash`, `fairscapeVersion` (1.0.24), the EVI provenance-graph
  link, and the CC-BY-4.0 licence on the 55 column schemas (distinct from the
  dataset's PhysioNet licence) have no slot in either record.
- Per-file SHA-256 survives only in core (`FileCollection` lacks a checksum
  slot).
- Parquet cannot be expressed in `FormatEnum` / `MediaTypeEnum`.
- Date-only crate values must be widened to `datetime`.

## Commands

```bash
FULL=data/d4d_concatenated/claudecode_agent_crate_only/2026-07-28_claude-opus-5-crateonly_rep2/VOICE_d4d.yaml
CORE=data/d4d_concatenated/claudecode_agent_crate_only_core/2026-07-28_claude-opus-5-crateonly_rep2/VOICE_d4d_core.yaml

poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_all.yaml -C Dataset "$FULL"
poetry run linkml-term-validator validate-data "$FULL" \
  --schema src/data_sheets_schema/schema/data_sheets_schema_all.yaml --target-class Dataset
poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml -C CoreDataset "$CORE"
poetry run linkml-term-validator validate-data "$CORE" \
  --schema src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml --target-class CoreDataset
poetry run python -m data_sheets_schema.d4d_pair_consistency --full "$FULL" --core "$CORE" --sync-core
poetry run python -m data_sheets_schema.d4d_pair_consistency --full "$FULL" --core "$CORE"
poetry run d4d provenance record --project VOICE --method claudecode_agent_crate_only \
  --label 2026-07-28_claude-opus-5-crateonly_rep2 \
  --input-bundle data/preprocessed/concatenated/VOICE_crate_only.txt
```

## Results

| Check | Result |
|---|---|
| Full — schema validation | PASS |
| Full — ontology term validation | PASS |
| Core — schema validation | PASS |
| Core — ontology term validation | PASS |
| Pair consistency (`--sync-core`) | PASS — 76 identity slots |
| Pair consistency (final independent) | PASS — 76 identity slots |
| Distribution relation | 15/15 matched, 0 unmatched (warning is the mandatory review prompt, discharged above) |
| Provenance record | present, `record_mode: live` |

Informational only, never a quality gate: full 1,102 lines / 68 top-level
slots; core 906 lines / 59 top-level slots.
