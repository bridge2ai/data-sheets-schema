# VOICE — Phase 3 / Phase 4 reconciliation

- **Version label:** `2026-07-28_claude-opus-5-crateonly-deprimed_rep3`
- **Arm:** CRATE-ONLY (RO-Crate evidence alone; document corpus withheld)
- **Runtime / provider / model:** Claude Code / Anthropic / `claude-opus-5[1m]`
- **Mode:** four-phase project agent, crate-only, de-primed; temperature 0.0
- **Declared input bundle (sole factual source):**
  `data/preprocessed/concatenated/VOICE_crate_only.txt` (320,923 bytes, md5
  `e0da1c226b05e944a617e2b0cdf9b6a0`)
- **Full record:**
  `data/d4d_concatenated/claudecode_agent_crate_only/2026-07-28_claude-opus-5-crateonly-deprimed_rep3/VOICE_d4d.yaml`
- **Core record:**
  `data/d4d_concatenated/claudecode_agent_crate_only_core/2026-07-28_claude-opus-5-crateonly-deprimed_rep3/VOICE_d4d_core.yaml`
- **Provenance record:** `VOICE_provenance.yaml` (`record_mode: live`)

---

## Phase 3 — Source and provenance audit

### 3.1 Provenance boundary

Factual inputs actually read during this run:

| Path | Role |
|---|---|
| `data/preprocessed/concatenated/VOICE_crate_only.txt` | sole factual source |
| `src/data_sheets_schema/schema/data_sheets_schema_all.yaml` | full structure (via `SchemaView`) |
| `src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml` | core structure (via `SchemaView`) |
| `.claude/agents/d4d-provenance-guard.md`, `.claude/commands/d4d-full-core.md`, `.claude/commands/d4d-agent.md` | method, no facts |

No prior full or core D4D record was read, searched, or cited, from any arm, label
or date. Nothing under `data/d4d_concatenated/` was opened other than this run's own
outputs. No `*_crate_d4d.yaml` or `*_crate_mapped_d4d.yaml` under
`data/ro-crate_packages/` was opened. `data/preprocessed/source_manifest.yaml` and
the document corpus were withheld by the arm definition and were not read; the
provenance tool records the manifest md5 automatically as repository state, not as a
consulted input. No web content was fetched.

Every structure emitted was derived from the LinkML schemas at runtime, not from any
example record. Two structural corrections were forced by validation and applied:
`principal_investigator`, `grantor`, `contact_person`, `reviewing_organization` and
`governance_committee_contact` are non-inlined references and required scalar
identifier values rather than inline objects.

### 3.2 What the crate bundle actually contains

The bundle holds two artifacts: `VOICE_crate_metadata_reduced.json` (RO-Crate 1.2 /
FAIRSCAPE `fairscapeVersion` 1.0.24 JSON-LD, 75 graph nodes) and
`ai_ready_score.json` (an AI-readiness self-assessment). The 75 nodes decompose as
1 metadata descriptor, 1 root dataset, 15 dataset entities, 55 `EVI:Schema` entities,
2 computations and 1 software entity.

Evidence density is very uneven. The root node is rich: it carries the full Croissant
`rai:*` block (limitations, biases, use cases, maintenance plan, collection, missing
data, raw data, timeframe, imputation, manipulation, preprocessing, annotation
protocol and analysis, sensitive information, social impact, annotator demographics,
machine annotation tools, annotation platforms) plus licence, DUA, copyright, IRB,
ethics review, governance contact, funder, citation, DOI, 117 authors and 18 keywords.
Nearly all of the record's narrative content comes from this single node.

By contrast the file-level entities are near-empty: every feature file carries the
literal description `"a datafile description"` and every phenotype file carries
`"A Dataset description"`. Their usable content is name, path, size, sha256, version,
date, generating computation and a link to a column schema. Of the 55 schema
entities, 19 are fully expanded with per-column names and types and 36 are collapsed
by the bundle's own normalizer into `columns: [name:type]` lists.

### 3.3 Facts verified against the bundle

Verified as stated in the crate root or the AI-ready score, and cross-checked for
internal consistency across every place they appear in the record: 833 participants;
five North American sites; version `3.0.0`; DOI `10.13026/k81f-qr68`; publisher
PhysioNet; PI Yael Bensoussan; 117 authors (count confirmed by enumeration and by the
AI-ready score's "117 authors"); licence and DUA URLs; copyright notice; funder string
and award number `3Tf-OTOD03272001S2`; USF IRB name, address, telephone and contact
address; Hastings Center ethical review; governance contact Satrajit Ghosh;
`fdaRegulated: false`; `deidentified: true`; `humanSubjectResearch: "Yes"`;
`humanSubjectExemption: "No"`; confidentiality level; release dates for v1.0, v1.1,
v2.0.0, v2.0.1 and v3.0.0; b2aiprep version 3.0.2 and repository URL; 15 documented
dataset entities; declared total content size 12.9 GB; Merkle root hash.

The AI-ready score contributed no independent facts. Every one of its `details`
strings is a restatement of a root-node field, so it was used only as a
cross-check — and it did corroborate the author count, the dataset count and the
checksum coverage.

### 3.4 Derived rather than quoted

Two values are arithmetic aggregates of stated facts, not quotations:

- `file_collections[features].total_bytes = 13,788,089,083` — the exact sum of the
  nine itemized feature-file sizes. Complete for that collection.
- `file_collections[features].file_count = 9` — count of feature entities that carry
  an individual `contentUrl`.

Deliberately **not** derived: top-level `total_size_bytes` and `total_file_count`.
The crate declares `contentSize: "12.9 GB"`, which matches the itemized sum only when
read as GiB (13,789,023,450 B = 12.84 GiB), and four phenotype entities are table
*groups* with no size and no enumerated member files. Converting either figure into a
single integer would assert a precision the crate does not support. The literal
"12.9 GB" is preserved as text in `distribution_formats` instead.

### 3.5 Findings recorded in the datasheet

Five internal inconsistencies in the crate were found by cross-checking entity
fields against each other, and are recorded under `anomalies` in both records:

1. `…dataset-feature-sparc-periodicity` is named `sparc_loudness.parquet` but its
   `contentUrl` is `features/sparc_periodicity.parquet`.
2. `…dataset-feature-torchaudio-pitch` is named `torchaudio_spectrogram.parquet` but
   its `contentUrl` is `features/torchaudio_pitch.parquet`.
3. `…dataset-phenotype-task` reuses the name "VOICE Questionnaire Tables" already
   used by `…dataset-phenotype-questionnaire`.
4. Two distinct schema entities share the identifier
   `…schema-phenotype-confounders`, named "Phenotype Confounders Schema" and
   "Phenotype Demographics Schema".
5. `…dataset-feature-sparc-pitch` carries `datePublished` 08/18/2025 while every
   other released entity carries 12/16/2025 — the v2.0.1 date on a v3.0.0 file.

Two further findings are recorded elsewhere in the record: the placeholder per-file
descriptions (`anomalies`), and the split declared type of the primary join key —
`participant_id` is `string` in the PPGs and SPARC schemas but `integer` in the
Torchaudio spectrogram schema and the phenotype schemas (`anomalies` and
`variables.quality_notes`).

The crate's own name for an entity was kept in `resources[].name` even where it is
wrong, with the true `contentUrl` path stated in the same entry's description. The
record reports what the crate says and where it contradicts itself, rather than
silently repairing it.

### 3.6 Findings with no schema slot (report only)

- **Copyright year.** `copyrightNotice` reads "Copyright © 2026 …" while
  `datePublished` is 12/16/2025 and the citation year is 2025. The notice is quoted
  verbatim in `ip_restrictions` and `license_and_use_terms`; the discrepancy is a
  property of the licence statement, not of the data, so no slot was altered.
- **Checksums.** The crate carries 11 per-file `sha256` digests. Class `Dataset` has
  no checksum slot at any level, so they are not representable in the full record.
  `CoreDistribution` does have `sha256`, but emitting per-file digests only in core
  would have created an 11-vs-2 granularity mismatch against `file_collections`, so
  checksums were omitted from both records rather than made asymmetric.
- **Merkle root.** `evi:merkleRootHash` has no slot; it is preserved as text in the
  `distribution_formats` RO-Crate entry, which is a shared slot and therefore
  deep-identical in both records.
- **`irbProtocolId`** is present but empty in the crate; the record states that no
  IRB protocol identifier is recorded rather than inventing one.

### 3.7 Slots deliberately left absent

`total_file_count`, `total_size_bytes` (§3.4); `language` — English dominance is
attested only indirectly ("fluent English speakers", "early releases focus on
English") and the Participant schema carries a `selected_language` column implying
per-participant variation; `page` and `download_url` — no landing-page or download
URL is stated, and the file-level `contentUrl` values are in-crate `file:///` paths;
`subsets` — the disease cohorts are documented as schemas, not as separately released
subsets, and are captured under `subpopulations`; `existing_uses` and
`use_repository` — the two `associatedPublication` entries are the dataset's own
citation and the PhysioNet platform paper, neither of which is a use of the data;
`content_warnings`, `at_risk_populations`, `participant_compensation`,
`collection_notifications`, `consent_revocations`, `extension_mechanism`,
`parent_datasets`, `compression`, `status`, `created_by`, `modified_by`,
`last_updated_on` — no supporting evidence in the bundle;
`Instance.data_topic` / `data_substrate` / `VariableMetadata.unit` — ontology-term
ranges with no term asserted in the crate.

### 3.8 Overall assessment of the crate as an evidence base

Strong on governance and responsible-AI narrative: ethics review, IRB, consent,
de-identification method, sensitive-element inventory, bias inventory, limitation
inventory, use and misuse boundaries, maintenance and versioning are all directly and
substantively answerable. Strong on identity: DOI, licence, DUA, copyright, funder,
citation, publisher, PI, full author list.

Weak on quantitative composition: only one count is stated anywhere in the bundle
(833 participants). There is no recording count, no session count, no per-cohort
count, no row count for any table, and no demographic distribution. This is why
`subpopulations.distribution` is absent and why `instances` carries a count for
participants only.

Weak on file-level documentation: placeholder descriptions, no format string on any
feature entity, and four table groups with no enumerated members, sizes or checksums.

The five naming/identifier collisions in §3.5 and the split `participant_id` type
mean the crate does not fully validate against itself.

### 3.9 Phase 2 back-porting

None required. Phase 2 surfaced no fact that the source supported and the full record
lacked. The two core-only structures — `dialect` and `distributions` — were both
evaluated against the bundle directly. `distributions` was populated; `dialect` was
not (see §4.4).

### 3.10 Validation after Phase 3

Both records re-validated clean against schema and ontology terms; see §4.6.

---

## Phase 4 — Strict full/core reconciliation

### 4.1 Shared-slot inventory (derived at runtime)

Derived with `SchemaView` from `Dataset` and `CoreDataset`; no hand-written list.

| Measure | Value |
|---|---|
| `Dataset` slots | 94 |
| `CoreDataset` slots | 79 |
| Shared slot names | 77 |
| Shared with identical induced range and cardinality | 76 |
| Shared with differing range (projection) | 1 — `resources` |
| Core-only slots | 2 — `distributions`, `dialect` |

### 4.2 Deterministic result

```
PASS: 76 schema-identical slots; projected slots=['resources']
WARNING [semantic-review-required] $.file_collections <-> $.distributions:
  Phase 4 must semantically review related distribution content;
  deterministic matches=2, unmatched core distributions=[]
```

`--sync-core` was **not** needed: the pair passed the independent check on the first
run, so no synchronization was performed and the reported PASS is an independent
result rather than a post-sync one.

Every schema-identical shared slot is present in both records or absent from both,
and every parsed value is deeply identical including nested mappings and list order.
No narrative field was condensed, paraphrased, reordered or omitted in core.

### 4.3 `resources` projection

15 entries in full, 15 in core, matched by `id` with identical id sets. Every slot
present in a core resource is deeply identical to its full counterpart. The single
full-only nested slot dropped from the core projection is `total_size_bytes`, which
`CoreDataset` does not declare. Verified programmatically, not by inspection.

### 4.4 Related-content semantic review (resolves the §4.2 warning)

**`file_collections` (full) ↔ `distributions` (core)** — 2 ↔ 2, matched by path.

| | `features/` | `phenotype/` |
|---|---|---|
| Name | identical in both | identical in both |
| Description | identical in both | identical in both |
| Path | `features/` = `features/` | `phenotype/` = `phenotype/` |
| Byte count | `total_bytes` 13,788,089,083 = `bytes` 13,788,089,083 | absent in both |
| File count | `file_count: 9` (full only — no such slot in `CoreDistribution`) | absent in both |
| Format | absent in both | full: no slot; core: `TSV` / `text/tab-separated-values` |
| Compression | absent in both | absent in both |
| Checksum | not representable in full; omitted in core by decision (§3.6) | same |
| Release scope | `version: "3.0.0"` on both collections; core distributions inherit the record-level version | same |

The one asymmetry is `format` / `media_type` on the phenotype distribution. This is
not a conflict: `FileCollection` declares no format or media-type slot, while
`CoreDistribution` does, and the value `text/tab-separated-values` is the literal
`format` recorded on the phenotype entities in the crate. The features distribution
carries no format in either record because Parquet is absent from both `FormatEnum`
and `MediaTypeEnum`.

**Scope comparison.** `total_file_count` and `total_size_bytes` are absent from the
full record (§3.4), so there is no top-level total to compare against the
distribution-level values, and no scope contradiction can arise. The features
collection's `total_bytes` is complete for its own scope (9 of 9 members itemized);
the phenotype collection asserts no total because 4 of its 6 members are unsized
groups.

**`is_tabular`.** `true` in both; a schema-identical slot, so identity is enforced
deterministically. Consistent with the declared formats (Parquet and TSV) and with
every resource entry, which also carries `is_tabular: true`.

**`dialect` (core-only).** Left absent by decision. The crate's delimited files are
consistently `separator: "\t"`, `header: true`, but the nine Parquet feature schemas
also carry `separator: ","`, which is meaningless for a columnar binary format. A
single record-level dialect would misdescribe the majority of the release by byte
volume, so none is asserted. No full-side counterpart exists, so this creates no
pair inconsistency.

**Identity, version and access facts.** Cross-checked between the top level,
`resources`, `version_access`, `distribution_dates` and the repeated statements in
`license_and_use_terms`, `regulatory_restrictions` and `ip_restrictions`:

- `version: "3.0.0"` at top level and on all 15 resources — consistent.
- `doi: 10.13026/k81f-qr68` (bare, per the slot's pattern) agrees with the DOI URL
  in `citation`, `version_access.latest_version_doi` and
  `distribution_formats[ro-crate].access_urls`.
- `issued: 2025-12-16` agrees with `distribution_dates` v3.0.0 and with 14 of 15
  resource `issued` values. The fifteenth, `…feature-sparc-pitch` at 2025-08-18, is
  the crate's own v2.0.1 date and is recorded as an anomaly rather than normalized —
  it is a historical value left visible with explicit scope, not a contradiction.
- Licence URL, DUA URL and copyright notice are identical everywhere they appear.
- The five release dates in `distribution_dates` match the five versions in
  `version_access.versions_available`.
- "833 participants" and "five sites" appear only where the crate states them;
  "approximately 3,000 participants by November 2026" appears in both
  `collection_timeframes` and `updates` with identical wording and forward-looking
  scope.

All of the above are schema-identical shared slots, so each is byte-for-byte the same
in the core record.

### 4.5 Corrections applied in Phase 4

None. No divergence, contradiction or omission was found between the two records.
The only content differences are the ten full-only populated slots and the one
core-only populated slot listed in §4.7, each of which is a schema consequence rather
than a discrepancy.

### 4.6 Commands run

```bash
poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_all.yaml \
  -C Dataset data/d4d_concatenated/claudecode_agent_crate_only/2026-07-28_claude-opus-5-crateonly-deprimed_rep3/VOICE_d4d.yaml
# -> No issues found

poetry run linkml-term-validator validate-data \
  data/d4d_concatenated/claudecode_agent_crate_only/2026-07-28_claude-opus-5-crateonly-deprimed_rep3/VOICE_d4d.yaml \
  --schema src/data_sheets_schema/schema/data_sheets_schema_all.yaml --target-class Dataset
# -> Validation passed

poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml \
  -C CoreDataset data/d4d_concatenated/claudecode_agent_crate_only_core/2026-07-28_claude-opus-5-crateonly-deprimed_rep3/VOICE_d4d_core.yaml
# -> No issues found

poetry run linkml-term-validator validate-data \
  data/d4d_concatenated/claudecode_agent_crate_only_core/2026-07-28_claude-opus-5-crateonly-deprimed_rep3/VOICE_d4d_core.yaml \
  --schema src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml --target-class CoreDataset
# -> Validation passed

poetry run python -m data_sheets_schema.d4d_pair_consistency \
  --full .../VOICE_d4d.yaml --core .../VOICE_d4d_core.yaml
# -> PASS: 76 schema-identical slots; projected slots=['resources']
# -> WARNING [semantic-review-required] file_collections <-> distributions (resolved in 4.4)

poetry run d4d provenance record --project VOICE --method claudecode_agent_crate_only \
  --label 2026-07-28_claude-opus-5-crateonly-deprimed_rep3 \
  --input-bundle data/preprocessed/concatenated/VOICE_crate_only.txt
# -> VOICE_provenance.yaml (record_mode: live)
```

### 4.7 Final state

| Metric | Full | Core |
|---|---|---|
| Top-level slots populated | 70 of 94 | 61 of 79 |
| Lines (informational only) | 1554 | 1160 |
| Schema validation | pass | pass |
| Ontology term validation | pass | pass |
| Resources | 15 | 15 |
| Creators | 117 | 117 |

Full-only populated slots (10, none available in `CoreDataset`): `citation`,
`collection_consents`, `direct_collection`, `file_collections`, `participant_privacy`,
`related_datasets`, `relationships`, `splits`, `third_party_sharing`, `variables`.

Core-only populated slot (1): `distributions`.

60 shared slots are populated in both and are deeply identical.

**Result: reconciled, zero unresolved contradictions within or between the two
records.**
