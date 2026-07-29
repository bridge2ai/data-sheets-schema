# VOICE full/core reconciliation — crate-only arm, replicate 3

- **Run label**: `2026-07-28_claude-opus-5-crateonly_rep3`
- **Arm**: CRATE-ONLY (one structured source, no documents)
- **Agent runtime**: Claude Code · **Provider**: Anthropic · **Model**: `claude-opus-5[1m]`
- **Mode**: four-phase project agent, crate-only · **Temperature**: 0.0
- **Generated**: 2026-07-28

| Artifact | Path |
|---|---|
| Full | `data/d4d_concatenated/claudecode_agent_crate_only/2026-07-28_claude-opus-5-crateonly_rep3/VOICE_d4d.yaml` |
| Core | `data/d4d_concatenated/claudecode_agent_crate_only_core/2026-07-28_claude-opus-5-crateonly_rep3/VOICE_d4d_core.yaml` |
| Provenance | `data/d4d_concatenated/claudecode_agent_crate_only_core/2026-07-28_claude-opus-5-crateonly_rep3/VOICE_provenance.yaml` |

## Referent

The record describes **the Bridge2AI-Voice v3.0.0 feature-only public release as packaged
in FAIRSCAPE RO-Crate `ark:59853/rocrate-b2ai-voice-3.0.0`**.

This is the referent the crate itself supports, and it is narrower than "the Bridge2AI-Voice
project". The crate's root entity is a single versioned release with its own DOI
(`10.13026/k81f-qr68`), its own publisher (PhysioNet), its own inventory of 15 data entities,
and its own explicit scope statement: *"The release contains data considered low risk,
including derivations such as spectrograms but not the original voice recordings."* The
crate also describes an ongoing collection effort (≈3,000 participants targeted by November
2026) and a separate controlled-access raw-audio tier, but it documents neither as a dataset
it packages. Treating the release as the referent keeps every populated slot inside the
crate's own assertion boundary; program-level and raw-audio-tier facts are recorded only
where the crate states them as context about the release (limitations, raw data sources,
maintenance plan).

## Evidence boundary

**Sole factual input**: `data/preprocessed/concatenated/VOICE_crate_only.txt`
(320,923 bytes, md5 `e0da1c226b05e944a617e2b0cdf9b6a0`) — containing
`VOICE_crate_metadata_reduced.json` (75-entity JSON-LD graph) and `ai_ready_score.json`.

**Structure references only** (no facts drawn): `data_sheets_schema_all.yaml` (class
`Dataset`), `data_sheets_schema_core_all.yaml` (class `CoreDataset`), `D4D_Core.yaml`,
and the generated JSON Schema used to confirm inlining behaviour.

**Not read at any point in this run**: `VOICE_preprocessed.txt`,
`VOICE_preprocessed_with_crate.txt`, anything under `data/preprocessed/individual/VOICE/` or
`data/raw/VOICE/`, `data/preprocessed/source_manifest.yaml`, `VOICE_crate_mapped_d4d.yaml`,
`ro-crate-datasheet.html`, `ro-crate-preview.html`, `ro-crate-croissant.json`, any prior D4D
record, any evaluation or reconciliation report, and any live web content.

The only access to `data/d4d_concatenated/` outside this run's own outputs was a directory
listing (`ls`) taken before Phase 1 to confirm that the target paths did not already exist.
That listing returned file names only — it showed the rep3 directories held CM4AI artifacts
from another agent and no VOICE files. No prior D4D content entered context. No prior D4D
content from any parent conversation was used.

---

## Phase 3 — source and provenance audit

### 3.1 Validation re-run

Both records re-validated clean after every correction. Final results in §Commands.

### 3.2 Provenance check

Read history confirms no prior-run D4D, evaluation, or reconciliation report was used as
evidence. Confirmed against the allowlist in §Evidence boundary.

### 3.3 Source-fidelity audit

A programmatic audit compared every `rai:*` field and every prose field of the crate root
entity against the full record, first as whole strings and then sentence by sentence.

**Ten deviations found and corrected** (all in the full record, then propagated to core):

| # | Field | Deviation | Correction |
|---|---|---|---|
| 1 | `citation` | `Bélisle-Pipon` transcribed as `Belisle-Pipon` | restored accented form |
| 2 | `copyrightNotice` | `©` transcribed as `(c)` (2 occurrences) | restored `©` |
| 3 | `rai:dataLimitations` | `train–validation–test` (en dashes) flattened to hyphens (2 occurrences) | restored en dashes |
| 4 | `rai:dataCollection` | opening sentence merged with a semicolon and the screening sentence dropped from `direct_collection` | restored both sentences verbatim |
| 5 | `rai:dataCollection` | `collection_consents` shortened "structured voice and respiratory tasks **such as sustained vowels, coughs and reading passages** with demographic questions" | restored full clause |
| 6 | `rai:dataCollectionMissingData` | third `missing_data_patterns` item truncated after "for all recordings" | restored full sentence |
| 7 | `rai:dataImputationProtocol` | `imputation_validation` added the words "across the released tables", which the crate does not say | reduced to the crate's own wording |
| 8 | `rai:dataSocialImpact` | `purposes.response` opened with a paraphrase ("The dataset was created to support…") | restored "The project aims to create an ethically sourced, diverse voice dataset to support…" |
| 9 | `rai:dataSocialImpact` | `future_use_impacts` dropped the connective "At the same time," | restored |

(Rows 2 and 3 each cover two occurrences, giving eleven text substitutions for ten distinct
deviations.)

**Two residual sentence-level mismatches are accepted as legitimate slot splits**, with both
halves present verbatim:

- `rai:dataCollectionMissingData` — "No additional imputation is applied in the released
  files." appears as the leading clause of `missing_data_documentation.handling_strategy`.
- `rai:dataImputationProtocol` — the final sentence is split across
  `imputation_protocols.imputation_validation` ("The data release team audited missingness.")
  and `imputation_protocols.imputation_rationale` ("Users can implement study-specific
  imputation or complete-case strategies appropriate to their analyses.").

The five `rai:dataBiases` entries carry a leading label ("Sampling bias: …"). The label was
moved to the object's `name` and the body to `bias_description`, with the body's first letter
capitalised. This is a structural mapping, not a content change.

### 3.4 Assertions checked against the source

Verified directly against the crate: 833 participants; five North American sites; 117 authors
(counted programmatically, matching the AI-readiness self-assessment); version `3.0.0`; DOI
`https://doi.org/10.13026/k81f-qr68`; license and DUA URLs; copyright notice; award
`3Tf-OTOD03272001S2`; USF IRB name, address, email and telephone; `fdaRegulated: false`;
`deidentified: true`; `humanSubjectExemption: No`; data-governance contact Satrajit Ghosh;
ethical review by Vardit Ravitsky at the Hastings Center for Bioethics; confidentiality level;
b2aiprep v3.0.2 and its repository URL; both computation records (names, descriptions,
`runBy: Alastair`, dates 01/29/2026 and 12/16/2025); the nine feature file sizes and SHA-256
values; the release history v1.0 / v1.1 / v2.0.0 / v2.0.1 / v3.0.0 with dates; 55 declared
schemas; project contact URL; `RRID:SCR_007345`.

Internal consistency: `3.0.0` appears identically at top level, on all 15 resources, and in
`version_access.versions_available`; the DOI appears identically in `doi`,
`version_access.latest_version_doi`, `distribution_formats.access_urls` and
`external_resources`; all release dates agree across `distribution_dates`,
`collection_timeframes` and `version_access`.

### 3.5 Source disagreements found *inside* the crate

The crate contradicts itself in seven places. None were silently resolved; each is recorded
in the record's `anomalies` and, where file-specific, in the affected resource's description.

1. `…dataset-feature-sparc-periodicity` is **named** `sparc_loudness.parquet` but points at
   `features/sparc_periodicity.parquet` and declares the SPARC Periodicity Schema.
2. `…dataset-feature-torchaudio-pitch` is **named** `torchaudio_spectrogram.parquet` but
   points at `features/torchaudio_pitch.parquet` and declares the Torchaudio Pitch Schema.
3. Two phenotype entities share the name "VOICE Questionnaire Tables"
   (`…phenotype-questionnaire` and `…phenotype-task`).
4. Two distinct schema records share the identifier
   `ark:59853/b2ai-voice-schema-phenotype-confounders` — one named "Phenotype Confounders
   Schema", one "Phenotype Demographics Schema". 55 schema records, 54 distinct ids.
5. A "Static Features Schema" for `static_features.tsv` is declared and the preprocessing
   text says the file is provided, but no file entity for it exists in the inventory.
6. Release counts disagree: 15 documented data entities vs. the AI-readiness assessment's
   "65% of files have checksums (11/17)".
7. `features/sparc_pitch.parquet` declares `datePublished: 08/18/2025` — the v2.0.1 release
   date — while every other inventoried file declares `12/16/2025`.

Because the crate is the only permitted source, these were recorded rather than adjudicated.
The record uses the **content paths** (not the names) when describing what each file holds,
since the paths agree with the declared schemas in both mismatched cases.

Two further crate-quality findings, recorded in `anomalies`:

- Every per-file `description` is an unfilled placeholder — `"a datafile description"` for the
  nine feature files, `"A Dataset description"` for the six phenotype entities. No file-level
  prose documentation exists in the release. The record therefore carries no crate-authored
  file descriptions; each resource description states what the crate structurally asserts
  (path, generating computation, declared schema, checksum) and says the placeholder is empty.
- The nine Parquet feature files declare `format: ""`, i.e. no media type.

### 3.6 Deliberate omissions where the crate offers a value in the wrong shape

- **`total_size_bytes` and `total_file_count` (top level) left empty.** The crate's own
  `contentSize` is the string `"12.9 GB"`, and four of the fifteen inventoried entities declare
  no size at all. The sum of the eleven declared sizes is 13,789,023,450 bytes ≈ 12.84 GiB,
  consistent with the crate's figure but not identical to any value the crate states. Rather
  than assert a total whose scope the crate does not fix, the exact sum is recorded at the
  collection level (`file_collections[features].total_bytes = 13,788,089,083`, complete for
  that collection because all nine files declare sizes) and the phenotype collection declares
  no total, with its description saying why.
- **`data_use_permission` left empty.** `LicenseAndUseTerms.data_use_permission` takes DUO
  codes. The crate states "registered-access license", "Limited dataset available with Data
  Use Agreement", and a list of forbidden uses — but no DUO term. Mapping these to a DUO code
  would be inference.
- **`hipaa_compliant` left empty.** "Limited dataset available with Data Use Agreement" is
  HIPAA vocabulary, but the crate never names HIPAA or asserts a compliance status.
  `confidentiality_level: restricted` is set, which the crate's own wording does support.
- **`data_topic` / `data_substrate` left empty on all instances.** Both take ontology terms.
  The crate carries no ontology CURIEs.
- **`issued` / `created_on` / `last_updated_on` left empty.** These are `datetime`; the crate
  gives dates only (`12/16/2025`). Emitting a midnight timestamp would add precision the crate
  does not have. The dates are carried as strings in `distribution_dates.release_dates`.
- **`language` left empty.** The crate says inclusion focused on "fluent English speakers" and
  that Spanish protocols are "planned but not yet fully represented" — statements about
  recruitment and roadmap, not a declared dataset language. Both are recorded under
  `known_biases`.

### 3.7 Back-ports from Phase 2

**None.** Phase 2 derived core from the crate plus the completed full record and found no fact
that the full record had missed or stated differently. The only content core adds is
`distributions`, which carries per-file `bytes`, `sha256`, `path`, `format` and `media_type` —
data the crate does state but for which class `Dataset` has no slot (see §4.3).

---

## Phase 4 — strict full/core reconciliation

### 4.1 Schema-derived shared slots

Derived at runtime with `SchemaView` from `Dataset` and `CoreDataset`:

- **77** slot names shared between the two classes.
- **76** validated as schema-identical by `d4d_pair_consistency` (`resources` is handled as a
  projection because its range differs: `Dataset` in full, `CoreDataset` in core).
- **17** full-only slots: `citation`, `collection_consents`, `collection_notifications`,
  `consent_revocations`, `direct_collection`, `file_collections`, `parent_datasets`,
  `participant_compensation`, `participant_privacy`, `related_datasets`, `relationships`,
  `splits`, `subsets`, `third_party_sharing`, `total_file_count`, `total_size_bytes`,
  `variables`.
- **2** core-only slots: `distributions`, `dialect`.

Result: **PASS — 76 schema-identical slots; projected slots = ['resources']**. Every populated
shared slot is present in both files with deeply identical parsed content, including all
narrative fields. Core condenses, paraphrases, reorders and omits nothing.

Of the 17 full-only slots, 10 are populated in full and are expected projection losses in
core: `citation`, `collection_consents`, `direct_collection`, `file_collections`,
`participant_privacy`, `related_datasets`, `relationships`, `splits`, `third_party_sharing`,
`variables`.

### 4.2 `resources` projection

15 resources in full, 15 in core, matched one-to-one by `id`. Coverage is equal. Every nested
slot permitted by `CoreDataset` is deeply identical between the two. Exactly one nested slot
is dropped in the projection — **`total_size_bytes`**, which `Dataset` has and `CoreDataset`
does not. Its information is preserved in core as `distributions[].bytes`.

### 4.3 Related-content semantic review: `file_collections` ↔ `distributions`

The validator emitted `WARNING [semantic-review-required]` with 0 deterministic matches,
because full groups files into 2 collections while core lists 15 individual distributions.
That is the intended relationship, not a defect. Reviewed and verified:

| Check | Result |
|---|---|
| Distributions with `features/` paths | 9 — equals `file_collections[features].file_count` = 9 |
| Sum of those 9 `bytes` | 13,788,089,083 — equals `file_collections[features].total_bytes` exactly |
| Distributions with `phenotype/` paths | 2 (`confounders.tsv`, `demographics.tsv`) |
| Distributions with no path | 4 grouped entities — matches `file_collections[phenotype]` declaring no `file_count` and no `total_bytes` |
| Distribution `path` values vs full `resources[].download_url` | identical sets (11 each) after stripping the `file:///` scheme |
| Distribution names vs resource names | identical sets, including the two crate name/path mismatches, which are carried through unchanged in both files |
| Checksums | 11 distributions carry `sha256`, matching the 11 files the crate checksums; both `file_collections` descriptions state which files carry checksums and agree |
| Formats | phenotype distributions set `format: TSV` / `media_type: text/tab-separated-values`, matching the crate and the collection description; feature distributions set neither, matching `file_collections[features]`'s statement that no media type is recorded |
| Compression | unset in both files; the crate declares none |
| Release scope | all 15 entities declare `version: 3.0.0`; the single `08/18/2025` publication date is flagged in `anomalies` and in that resource's description in both files |

**No contradictions.**

`format`/`media_type` are left unset on the nine Parquet files because `FormatEnum` has no
`PARQUET` value and `MediaTypeEnum` has no Parquet media type. This is a schema gap, not
missing evidence; each affected distribution's description says so.

### 4.4 Counts vs distribution-level values

`total_file_count` and `total_size_bytes` are unset in full (see §3.6), so there is nothing to
contradict the distribution-level values. `CoreDataset` has neither slot.

### 4.5 `dialect`, formats, `is_tabular`

`is_tabular: true` in both files and on every resource in both files — the release is entirely
tabular (Parquet feature tables and TSV phenotype tables, with column-level schemas declaring
`header: true` for all 55).

**`dialect` (core-only) deliberately left unset.** The crate declares `separator: ","` on the
ten feature schemas and `separator: "\t"` on the phenotype schemas, so there is no single
dataset-level dialect. The `","` separator on binary Parquet files is itself a crate artefact.
Asserting one dialect would misdescribe half the release.

### 4.6 Identity, version and access cross-checks

Top-level identity, version and access facts agree with the resources, version history,
distributions and repeated statements: one DOI, one license URL, one DUA URL, one publisher,
one copyright holder, one governance contact, one version string, one release date — each
consistent everywhere it appears in both files.

---

## What the crate could NOT support at all

**Full record: 27 of 94 `Dataset` slots left empty.** Grouped by cause:

*No evidence in the crate — genuine documentation gaps in the source:*

| Slot | What the crate does not say |
|---|---|
| `content_warnings` | Never addresses whether remaining content could distress a user. It says traumatic-experience narratives were *removed*, which is not the same assertion. |
| `collection_notifications` | Whether individuals were notified that data were being collected about them. |
| `consent_revocations` | Any mechanism for withdrawing consent or removing data from a frozen snapshot. |
| `data_protection_impacts` | Any DPIA or equivalent formal impact analysis. |
| `at_risk_populations` | Whether vulnerable groups are included, and any special protections, assent or guardian-consent procedures. |
| `participant_compensation` | Whether participants were compensated, how, or how much. |
| `existing_uses` | Any paper, model or analysis that has used the dataset. |
| `use_repository` | Any registry or repository listing works that use the dataset. |
| `extension_mechanism` | Any route for third parties to contribute, extend or augment the release. |
| `subsets` | Any named split, subpopulation extract or derived subset with its own identity. |
| `parent_datasets` | Any parent; the crate's `isPartOf` is an empty list on every entity. |

*Additional gaps visible inside slots that were populated:*

- **Creators**: the crate lists 117 author names and one PI, and nothing else — no
  affiliations, no ORCIDs, no CRediT roles, no contact addresses. `Creator.affiliations` and
  `Creator.credit_roles` are therefore empty on the single creator object.
- **Subpopulations**: cohorts are identifiable from the disease-specific schemas, but the
  crate reports no participant count or percentage for any cohort or demographic stratum, so
  `Subpopulation.distribution` records only that absence.
- **Informed consent**: the crate confirms consent was obtained and nothing more — no consent
  instrument, no consent type, no documentation reference, no scope, no withdrawal route.
- **Ethical review**: no IRB protocol number (the crate's `irbProtocolId` field is present but
  empty), no review date, no review outcome.
- **Raw-audio tier**: repeatedly referenced but never given a URL, application route or
  contact point.
- **Annotation quality**: no inter-annotator agreement score and no named agreement metric.
- **Tool accuracy**: no accuracy figure for any of the eight machine-annotation tools.
- **Instance counts**: 833 participants is stated; the number of sessions, recordings and
  feature rows is not.
- **Errata**: release notes are said to exist and to document corrections, but no URL is given.
- **Retention**: no retention period, deprecation policy or end-of-life date.
- **Data collectors**: no statement of how collection personnel were engaged or compensated.

*Empty for shape or precision reasons rather than missing evidence* (see §3.6):
`total_file_count`, `total_size_bytes`, `issued`, `created_on`, `last_updated_on`, `language`.

*Not applicable to this release:* `compression` (no compression declared), `download_url`
(the crate's content URLs are in-crate `file:///` paths, carried on each resource; no
repository download endpoint is given), `page`, `status`, `created_by`, `modified_by`,
`conforms_to_class`, `conforms_to_schema` (set per-resource, not at top level),
`was_derived_from` (set per-resource).

**Core record: 21 of 79 `CoreDataset` slots left empty** — the same causes, plus `dialect`
(§4.5). Core loses no populated content relative to full except through the projection
described in §4.1 and §4.2.

### What the crate supported unusually well

For balance: the crate's Croissant `rai:*` block is dense and carries substantive prose for
areas that are frequently thin — biases (5 typed statements), limitations (5), collection
protocol, missing-data handling, imputation, de-identification method, preprocessing steps,
annotation protocol, annotator demographics, machine-annotation tooling, social impact, and a
release/maintenance plan. Nearly all of the ethics, preprocessing and uses sections of this
record come directly from that block. Provenance is also strong: 2 computations, 1 software
entity with version and repository URL, per-file generating-activity links, 11 SHA-256
checksums, and 55 column-level schemas.

The crate's weakest layer is its **file inventory**: placeholder descriptions everywhere, two
name/path mismatches, one duplicated name, one duplicated schema id, four entities with no
path, size or checksum, one schema with no file, and a `format` field left blank on every
Parquet file.

---

## Files changed in this run

| File | Action |
|---|---|
| `…/claudecode_agent_crate_only/2026-07-28_claude-opus-5-crateonly_rep3/VOICE_d4d.yaml` | created (Phase 1), corrected (Phase 3 §3.3) |
| `…/claudecode_agent_crate_only_core/2026-07-28_claude-opus-5-crateonly_rep3/VOICE_d4d_core.yaml` | created (Phase 2), regenerated from corrected full (Phase 3), header stamped (Phase 4) |
| `…/claudecode_agent_crate_only_core/2026-07-28_claude-opus-5-crateonly_rep3/VOICE_reconciliation.md` | created (Phase 4) |
| `…/claudecode_agent_crate_only_core/2026-07-28_claude-opus-5-crateonly_rep3/VOICE_provenance.yaml` | created (live record) |

No existing file was overwritten. The rep3 directories already contained CM4AI artifacts from
a separate agent; those were not read or modified.

## Commands

```bash
FULL=data/d4d_concatenated/claudecode_agent_crate_only/2026-07-28_claude-opus-5-crateonly_rep3/VOICE_d4d.yaml
CORE=data/d4d_concatenated/claudecode_agent_crate_only_core/2026-07-28_claude-opus-5-crateonly_rep3/VOICE_d4d_core.yaml

poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_all.yaml -C Dataset $FULL
poetry run linkml-term-validator validate-data $FULL \
  --schema src/data_sheets_schema/schema/data_sheets_schema_all.yaml --target-class Dataset

poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml -C CoreDataset $CORE
poetry run linkml-term-validator validate-data $CORE \
  --schema src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml --target-class CoreDataset

poetry run python -m data_sheets_schema.d4d_pair_consistency --full $FULL --core $CORE --sync-core
poetry run python -m data_sheets_schema.d4d_pair_consistency --full $FULL --core $CORE

poetry run d4d provenance record --project VOICE --method claudecode_agent_crate_only \
  --label 2026-07-28_claude-opus-5-crateonly_rep3 \
  --input-bundle data/preprocessed/concatenated/VOICE_crate_only.txt
```

## Final results

| Check | Result |
|---|---|
| `linkml-validate` — full, class `Dataset` | **No issues found** |
| `linkml-term-validator` — full | **Validation passed** |
| `linkml-validate` — core, class `CoreDataset` | **No issues found** |
| `linkml-term-validator` — core | **Validation passed** |
| `d4d_pair_consistency --sync-core` | **PASS** — 76 schema-identical slots; projected `['resources']`; core required no synchronisation edits |
| `d4d_pair_consistency` (independent re-run) | **PASS** — same result, exit 0 |
| Related-content semantic review (§4.3–4.6) | **Complete, no contradictions** |
| Provenance record `record_mode` | **live** |

Full: 67 of 94 `Dataset` slots populated, 1,468 lines. Core: 58 of 79 `CoreDataset` slots
populated, 1,104 lines. Line counts are informational metadata, not a quality gate.
