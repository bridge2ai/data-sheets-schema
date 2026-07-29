# CM4AI full/core reconciliation — 2026-07-28_claude-opus-5-crateonly-deprimed_rep2

- Project: CM4AI
- Arm: CRATE-ONLY (RO-Crate evidence alone; document corpus withheld)
- Mode: four-phase project agent, de-primed, pinned referent
- Pinned referent: the CM4AI data-release programme as an ongoing quarterly release
  series (releases as `resources`; `file_collections` describing the current release)
- Runtime / provider / model: Claude Code / Anthropic / claude-opus-5[1m]
- Temperature: 0.0

## Inputs actually read

Factual input (one declared bundle):

- `data/preprocessed/concatenated/CM4AI_crate_only.txt`

Structural inputs:

- `src/data_sheets_schema/schema/data_sheets_schema_all.yaml` (class `Dataset`)
- `src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml` (class `CoreDataset`)

Governing instructions:

- `.claude/agents/d4d-provenance-guard.md`
- `.claude/commands/d4d-full-core.md`, `.claude/commands/d4d-agent.md`

Not read: `data/preprocessed/source_manifest.yaml` and the document corpus (withheld
by the arm definition); any file under `data/d4d_concatenated/`; any
`*_crate_d4d.yaml` or `*_crate_mapped_d4d.yaml` under `data/ro-crate_packages/`; any
evaluation or reconciliation artefact from any earlier run. Output directory names
under `data/d4d_concatenated/claudecode_agent_crate_only/` were listed once, without
reading any file, solely to confirm the assigned version label was unused.

## Outputs

- Full: `data/d4d_concatenated/claudecode_agent_crate_only/2026-07-28_claude-opus-5-crateonly-deprimed_rep2/CM4AI_d4d.yaml`
- Core: `data/d4d_concatenated/claudecode_agent_crate_only_core/2026-07-28_claude-opus-5-crateonly-deprimed_rep2/CM4AI_d4d_core.yaml`
- This report

---

## Phase 3 — source and provenance audit

### Provenance result

No prior generated D4D record, from any arm, label or date, was read, searched or
cited. The only factual source consulted was the declared crate-only bundle. Every
emitted slot and nested object was derived from the applicable LinkML schema via
`SchemaView` (induced slots, ranges, cardinality, inlining, `slot_usage`, enums); no
prior record and no `d4d:docExample` was used as a template. `PASS`.

### What the crate evidence supports, and what it does not

The bundle contains two artefacts: a reduced RO-Crate JSON-LD graph (61 nodes: the
release entity, 47-author person set, 13 defined terms, and nine component
collections) and an AI-readiness self-assessment. File inventories inside the crate
are collapsed to counts and `id_families` summaries, so the evidence supports
release- and collection-level description well and per-file description not at all.
Consequences carried into both records:

- No `file_count` is asserted on any collection. Entity typing is inconsistent across
  the component crates — the AP-MS and SEC-MS collections expose a `dataset` family
  in `hasPart` that matches their `EVI#outputs` count, while the IF collections
  expose only one `dataset` entity in `hasPart` and carry their per-image entities in
  the outputs list. Rather than pick one of two incompatible readings, the crate's own
  counts are reported verbatim in each collection description.
- No `total_bytes` is asserted on any collection. Only the release entity carries an
  exact byte count (`evi:totalContentSizeBytes`); component collections carry
  human-readable `contentSize` strings only, and those strings are demonstrably not
  derivable from the byte count (see the size anomaly below), so converting them
  would invent precision.
- `variables` is empty. The release declares 20 schemas but the reduced bundle does
  not carry their contents.

### Internal-consistency findings, all recorded in the records themselves

1. **Aggregate size statements disagree.** The release declares `contentSize`
   "19.9 TB" and `evi:totalContentSizeBytes` 21051331945400 (≈21.05 TB decimal,
   ≈19.15 TiB). Neither reading reconciles the two. The exact byte count is used for
   `total_size_bytes`; the discrepancy is recorded under `anomalies`.
2. **Stale and conflicting release citations.** Every component collection carries a
   citation naming the "March 2025 Data Release (Beta)" rather than the release it is
   declared part of, and those citations give two different DOIs for that same named
   release (`10.18130/V3/B35XWX` and `10.18130/V3/K7TGEM`). Neither DOI was used as a
   release identifier; both are reported under `version_access.version_details` and
   `anomalies`.
3. **Author list and recommended citation disagree.** The structured `author` array
   holds 47 entries and includes Marquez C; the recommended citation omits Marquez C
   and adds Park S and Zhao X. The structured array was used for `creators` (it is the
   only source of ORCIDs and affiliations); the citation is preserved verbatim in
   `citation`; the disagreement is recorded under `anomalies`.
4. **Trailing-comma identifier artefact.** Parent-release references frequently end in
   a literal comma (`...June-2026-data-release,`). The same identifiers also appear
   without the comma. The comma-free forms are used as `resources` ids; the artefact
   is recorded under `anomalies`.
5. **SEC-MS stage count.** The KOLF2 SEC-MS description announces "three distinct
   stages" and then enumerates four (Parental, NPC, Neuron, Cardio) with replicate
   counts for all four. The collection description now states the disagreement rather
   than silently choosing four; also recorded under `anomalies`.
6. **Typographic errors.** `ethicalReview` spells "Vardit Ravistky" where the person
   entity for the same ORCID gives "Ravitsky, V"; the perturb-seq raw author string
   ends "Idkeker T" where the atlas collection gives "Ideker T"; ORCID
   0000-0002-4180-422X appears as both "Ballllosero Navarro, F" and "Ballllosera
   Navarro F"; the treated-cancer-cell SEC-MS identifier is
   `https://doi.org/doi:10.25345/C5348GV4S`, doubling the DOI scheme. Person-entity
   spellings were preferred for `creators`; verbatim upstream strings were preserved
   in `created_by`; the DOI was normalised to `https://doi.org/10.25345/C5348GV4S`.
   All recorded under `anomalies`.
7. **Collection timeframes vary by collection lineage.** The release declares
   9/1/2022–6/1/2026; component collections declare the same start with earlier ends
   (1/31/2026 or 10/13/25). This is release lineage, not contradiction, and is stated
   as such in `collection_timeframes.timeframe_details`. Only the release-level
   timeframe is bound to `start_date` / `end_date`.
8. **Licence is not uniform.** The release declares CC BY-NC-SA 4.0; the two EndoTag
   AP-MS collections and the KOLF2.1J SEC-MS collection declare CC0 1.0. Both facts
   are carried — per-collection `license` on each collection, and an explicit
   statement of the split in `license_and_use_terms.license_terms`.
9. **Identity not asserted where the crate does not assert it.** "Jilian Parker"
   (data governance contact) is not merged with author "Parker, J" (ORCID
   0000-0003-4535-3486); the crate never equates them. The governance contact is given
   a minted local identifier and the name is preserved in
   `regulatory_restrictions.other_compliance`.
10. **Checksum coverage.** The AI-readiness assessment reports checksums for 8 of
    55,859 entities and summary statistics for 0. This is recorded as a coverage
    limitation. It does not conflict with the six collection-level MD5 values found in
    Phase 2 — six checksummed collection entities are consistent with a count of eight.

### Scoping decisions forced by the pinned referent

The pin makes the top-level record the programme, not a release. Accordingly:

- `id` is the crate's project entity ARK
  (`.../project-cell-maps-for-artificial-intelligence-qTdsTBd3FtA`), not the release
  ARK; the release ARK is the id of the first `resources` entry.
- `doi` is absent at programme level (the crate has no programme DOI); the release DOI
  appears on the release resource and as `version_access.latest_version_doi`.
- `version` is absent at programme level; release versions appear on the resources and
  in `version_access`.
- `total_file_count` and `total_size_bytes` are carried at programme level *and* on the
  June 2026 release resource with identical values. This is deliberate and evidence-
  supported: releases in this series are cumulative — component collections declare
  membership in the October 2025, January 2026 and June 2026 releases simultaneously —
  so the current release aggregate is the current programme aggregate.
- The January 2026 and October 2025 releases are emitted as `resources` with `id`,
  `name` and a description that states explicitly that the crate records them only as
  parent-release identifiers, with no descriptive metadata, DOI, size or date. The
  March 2025 release is *not* emitted as a resource: it exists in the evidence only
  inside citation strings, with two conflicting DOIs and no crate node.

### Corrections applied in Phase 3

- **Back-port from Phase 2:** six collection-level MD5 checksums
  (`0b4d129f…`, `9422486c…`, `ac577109…`, `cb67e774…`, `cbdb263b…`, `1cafefa3…`) were
  found while deriving `CoreDistribution.md5`. `FileCollection` has no checksum slot
  in the full schema, so each value was back-ported into the corresponding
  `file_collections[].description`, which is a schema-identical shared field and
  therefore propagates to core.
- The KOLF2 SEC-MS collection description was rewritten to state the crate's own
  three-versus-four stage disagreement instead of asserting four.
- The treated-cancer-cell SEC-MS description gained the control-experiment numbering
  (1, 2, 4) and the perturb-seq atlas description gained the two output variants.
- Two `anomalies` entries were added (SEC-MS stage count; typographic errors).

Both files were re-validated after every correction.

---

## Phase 4 — strict full/core reconciliation

### Shared-slot derivation

Shared slots were derived at runtime with LinkML `SchemaView` from `Dataset` and
`CoreDataset`; no hand-written field list was used. `Dataset` ∩ `CoreDataset` = **77
slots**. All nested classes used by this record (`Purpose`, `Task`, `Creator`,
`FundingMechanism`, `Instance`, `DataAnomaly`, `DatasetBias`, `DatasetLimitation`,
`SamplingStrategy`, `EthicalReview`, `LicenseAndUseTerms`,
`ExportControlRegulatoryRestrictions`, `VersionAccess`, `ExternalResource`, and the
rest) were verified to have byte-identical induced slot sets in the two schemas, so
their contents transfer without projection.

### Deterministic result

```
poetry run python -m data_sheets_schema.d4d_pair_consistency \
  --full  .../2026-07-28_claude-opus-5-crateonly-deprimed_rep2/CM4AI_d4d.yaml \
  --core  .../2026-07-28_claude-opus-5-crateonly-deprimed_rep2/CM4AI_d4d_core.yaml

PASS: 76 schema-identical slots; projected slots=['resources']
WARNING [semantic-review-required] $.file_collections <-> $.distributions:
  deterministic matches=9, unmatched core distributions=[]
```

`--sync-core` was **not** required and was not run: core was generated by projecting
the Phase 3-canonical full record, so every schema-identical slot was already deeply
identical on the first independent check.

### Presence and identity

- Full top-level slots populated: **62**. Core top-level slots populated: **55**.
- The 8 full-only top-level slots — `citation`, `direct_collection`,
  `file_collections`, `relationships`, `splits`, `third_party_sharing`,
  `total_file_count`, `total_size_bytes` — are each absent from `CoreDataset`, so
  their absence from core is required by the schema, not a divergence.
- The 1 core-only top-level slot — `distributions` — is the core projection of
  `file_collections`.
- `dialect` is absent from core, consistent with `is_tabular: false` in both records.
- Every remaining shared slot is present in both records with deeply identical parsed
  content, including narrative fields; nothing was condensed, paraphrased, reordered
  or omitted in core.

### Projection: `resources` (`Dataset` → `CoreDataset`)

Matched by `id`, coverage equal, 3 of 3:

| resource | full-only nested slots dropped |
|---|---|
| `…rocrate-cell-maps-for-artificial-intelligence-June-2026-data-release` | `citation`, `total_file_count`, `total_size_bytes` |
| `…rocrate-cell-maps-for-artificial-intelligence-January-2026-data-release` | none |
| `…rocrate-cell-maps-for-artificial-intelligence-october-2025-data-release` | none |

Every nested slot present in both is deeply identical. The three dropped slots are
absent from `CoreDataset` by schema.

### Semantic review: `file_collections` ↔ `distributions`

Nine collections, nine distributions, matched 1:1 by `id`; no unmatched entry on
either side. Verified field by field:

- **Names** — identical for all nine.
- **Descriptions** — identical for all nine, including every content-size string,
  entity count, replicate design, embargo statement and MD5 value.
- **Paths** — identical for all nine (`AP-MS/apms-paclitaxel-rocrate`,
  `AP-MS/apms-vorinostat-rocrate`, `Images/untreated`, `Images/paclitaxel`,
  `Images/vorinostat`, `mass-spec/iPSCs`, `mass-spec/cancer-cells`,
  `Perturb-Seq/sra`, `Perturb-Seq/cell-atlas`).
- **Checksums** — `CoreDistribution.md5` is populated for the six collections whose
  crate node carries an `MD5` property, and absent for the three that do not
  (both AP-MS collections and the KOLF2.1J SEC-MS collection). Each of the six values
  appears verbatim in the shared description text, so full and core state the same
  checksum through different mechanisms; this was checked programmatically.
- **Byte counts** — absent on both sides. `CoreDistribution.bytes` is left empty
  because no per-collection exact byte count exists in the evidence, matching the
  absence of `FileCollection.total_bytes` in full. No contradiction.
- **Formats and compression** — `CoreDistribution.format` (`FormatEnum`),
  `media_type`, `encoding` and `compression` are all left empty. The formats the
  crate declares (`.d`, `.d directory group`, `fastq.gz`, `h5`, `h5ad`,
  `image/jpeg`, `executable`, `unknown`) have no `FormatEnum` member, and the
  crate declares formats only at release level, not per collection. The release-level
  format list is carried instead in `distribution_formats`, which is a schema-identical
  shared slot and therefore identical in both records. `compression` is absent from
  both records at every level.
- **Access URLs and release scope** — full carries `download_url`, `page`, `doi`,
  `publisher`, `license`, `version`, `created_by`, `keywords`, `collection_type` and
  `external_resources` per collection; `CoreDistribution` declares none of these, so
  they are full-only by schema. The same access facts reach core through the shared
  `distribution_formats`, `external_resources` and `license_and_use_terms` slots,
  which are identical in both records. Checked for conflict: the MassIVE, FigShare,
  Dataverse and FTP endpoints named in core's shared slots agree exactly with the
  per-collection values in full, and the embargo on the perturb-seq raw sequence
  collection is stated identically in both records (in the shared description text,
  in `known_limitations`, in `raw_data_sources` and in `instances`).

### `total_file_count` / `total_size_bytes` versus distribution-level values

Not comparable, and therefore not a contradiction: `CoreDataset` declares neither
slot, and no distribution carries a byte count or file count on either side. The
programme-level values (53,877 files; 21,051,331,945,400 bytes) are stated once in
full, at programme level and on the June 2026 release resource with identical values,
and their cumulative-release justification is recorded above.

### Final validation

```
poetry run linkml-validate -s .../data_sheets_schema_all.yaml -C Dataset <full>          → No issues found
poetry run linkml-term-validator validate-data <full> -s .../data_sheets_schema_all.yaml \
  --target-class Dataset                                                                 → Validation passed
poetry run linkml-validate -s .../data_sheets_schema_core_all.yaml -C CoreDataset <core> → No issues found
poetry run linkml-term-validator validate-data <core> -s .../data_sheets_schema_core_all.yaml \
  --target-class CoreDataset                                                             → Validation passed
poetry run python -m data_sheets_schema.d4d_pair_consistency --full <full> --core <core>  → PASS
```

### Outcome

Reconciliation clean. Zero unresolved contradictions within either record or between
them. All divergence between full and core is schema-mandated: 8 full-only slots that
`CoreDataset` does not declare, and one projection (`file_collections` →
`distributions`) whose every shared field is identical and whose only core-side
addition (`md5`) is corroborated verbatim in the shared description text.
