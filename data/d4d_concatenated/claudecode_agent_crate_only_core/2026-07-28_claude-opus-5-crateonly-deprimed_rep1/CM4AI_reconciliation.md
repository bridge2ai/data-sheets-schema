# CM4AI full/core reconciliation — 2026-07-28_claude-opus-5-crateonly-deprimed_rep1

Run label: `2026-07-28_claude-opus-5-crateonly-deprimed_rep1`
Arm: CRATE-ONLY (RO-Crate evidence alone; document corpus withheld)
Runtime / provider / model: Claude Code / Anthropic / `claude-opus-5[1m]`, temperature 0.0
Mode: four-phase project agent, crate-only, de-primed, pinned-referent

Pinned referent: the CM4AI data-release programme as an ongoing quarterly release
series. Releases are `resources`; `file_collections` describe the current release.

## Files

| Role | Path |
|---|---|
| Full | `data/d4d_concatenated/claudecode_agent_crate_only/2026-07-28_claude-opus-5-crateonly-deprimed_rep1/CM4AI_d4d.yaml` |
| Core | `data/d4d_concatenated/claudecode_agent_crate_only_core/2026-07-28_claude-opus-5-crateonly-deprimed_rep1/CM4AI_d4d_core.yaml` |
| Report | `data/d4d_concatenated/claudecode_agent_crate_only_core/2026-07-28_claude-opus-5-crateonly-deprimed_rep1/CM4AI_reconciliation.md` |

## Declared inputs

Factual inputs, complete list:

- `data/preprocessed/concatenated/CM4AI_crate_only.txt` (the only declared source bundle)
- `src/data_sheets_schema/schema/data_sheets_schema_all.yaml` (class `Dataset`, structure only)
- `src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml` (class `CoreDataset`, structure only)

`data/preprocessed/source_manifest.yaml` and the document corpus were withheld by the
arm definition and were not read. Phase 2 additionally read the exact same-run Phase 1
full record named above.

---

# Phase 3 — source and provenance audit

## Provenance result

No prior full or core D4D record was read, from any arm, label, or date. Nothing under
`data/d4d_concatenated/` other than this run's own outputs was opened, and no
`*_crate_d4d.yaml` or `*_crate_mapped_d4d.yaml` under `data/ro-crate_packages/` was
opened. The bundle itself states that the D4D-shaped crate artifacts
(`CM4AI_crate_d4d.yaml`, `ro-crate-linkml.yaml`, `ro-crate-datasheet.html`) are
withheld; they were not sought out. No evaluation report, test fixture, or schema
example supplied a factual value. Structure was derived at runtime from the two LinkML
schemas via `SchemaView`; no prior record was used as a template.

## Evidence coverage check

Verified programmatically against the parsed crate JSON-LD in the bundle:

- 9 of 9 constituent RO-Crate sub-datasets are represented as `file_collections`; no
  extra collection was invented (`file_collections not in crate: []`).
- 47 of 47 authors in the release `author` array are represented as `creators`, with
  zero missing and zero extra. 38 carry ORCID identifiers and affiliations from the
  crate's `Person` nodes; the remaining 9 appear in the crate as bare name strings and
  are recorded with a synthetic creator id and an explicit note that the crate supplies
  no ORCID or affiliation for them.
- All entity counts (`evi:datasetCount` 53877, `evi:computationCount` 1976,
  `evi:softwareCount` 6, `evi:schemaCount` 20, `evi:totalEntities` 55859,
  `evi:entitiesWithChecksums` 8, `evi:entitiesWithSummaryStats` 0,
  `evi:totalContentSizeBytes` 21051331945400) transcribe exactly.

## Source disagreements found and how they were resolved

The crate is internally inconsistent in eight places. Every one was resolved from the
crate itself using authority (release-level statement outranks a value carried inside a
constituent collection), scope, and recency. None was resolved by consulting any other
artifact.

1. **Content size.** The release declares `contentSize: "19.9 TB"` and
   `evi:totalContentSizeBytes: 21051331945400`. These disagree under both decimal
   (21.05 TB) and binary (19.15 TiB) readings. Resolution: only the machine-readable
   byte count is asserted (`total_size_bytes`); the human-readable string is reported as
   an observation, not as a fact. Because the per-collection `contentSize` strings come
   from the same unreliable field, no `total_bytes` was derived for any collection.
2. **Total file count.** `evi:datasetCount` (53877) counts data-file entities, while
   `evi:totalEntities` (55859) counts entities of all types — yet the AI-readiness
   self-assessment uses 55859 as the denominator for checksum coverage ("8/55859"). The
   crate does not state which is the file count. Resolution: `total_file_count` is left
   absent, and both figures are recorded losslessly as separately labelled `instances`
   with the ambiguity stated.
3. **Stale citation strings.** Every constituent collection carries a `citation` naming
   "Cell Maps for Artificial Intelligence - March 2025 Data Release (Beta)" although all
   are part of the June 2026 release. Resolution: only the release-level citation (which
   names the June 2026 release) was used; no stale citation was propagated into any
   collection or resource.
4. **Two DOIs for one prior release title.** Those stale citation strings associate both
   `10.18130/V3/B35XWX` (6 occurrences) and `10.18130/V3/K7TGEM` (3 occurrences) with the
   identical title "March 2025 Data Release (Beta)". Resolution: the March 2025 release
   is **not** emitted as a `resources` entry, because asserting either DOI as its
   identity would assert a contradicted value and frequency is not evidence. It is
   recorded in `version_access.versions_available` and the conflict is stated verbatim
   in `version_access.version_details`.
5. **Stale collection-type lists.** The release declares four modalities
   ("Perturb-seq; IF imaging; SEC-MS; AP-MS"); several collections declare only three.
   Resolution: the release-level four-modality value was used.
6. **Stale collection end dates.** The release declares 9/1/2022–6/1/2026; collections
   carried forward from earlier releases declare 10/13/25 or 1/31/2026. Resolution:
   treated as historical release scopes, not contradictions. The current-release
   timeframe is asserted in `collection_timeframes.start_date`/`end_date`, and the
   historical variants are recorded explicitly in `timeframe_details` with their scope
   named.
7. **Trailing-comma ark identifiers.** The January 2026 and October 2025 release
   identifiers appear only as `...-data-release,`. The June 2026 identifier appears both
   with and without the comma, and the release's own `@id` has none. Resolution: the
   comma is a serialisation artefact; identifiers were normalised by stripping it, and
   the normalisation is recorded in `anomalies`.
8. **Malformed DOI.** The treated-cancer-cell SEC-MS collection records
   `https://doi.org/doi:10.25345/C5348GV4S`. Resolution: the DOI `10.25345/C5348GV4S` is
   recorded in the `doi` slot and the malformed source form is quoted in that
   collection's description.

Two further source defects were recorded rather than silently repaired: the CM4AI
project is referenced by two different ark identifiers
(`.../project-cell-maps-for-artificial-intelligence-qTdsTBd3FtA` at release level,
`.../project-cm4ai` inside constituent collections — the release-level form was chosen
as the record's `id`), and the raw sequence collection's author string spells the PI
"Idkeker T" where every other listing spells "Ideker T" (the collection's `created_by`
preserves the source string verbatim).

## Normalisation applied

- Affiliation strings were normalised to one organisation id per institution, merging
  "University of California, San Diego" with "University of California San Diego" and
  "The University of Alabama at Birmingham" with "University of Alabama at Birmingham".
  This was the only affiliation divergence found; no person's affiliation was changed.
  "University of Alabama" (Payne-Foster) was kept distinct from "University of Alabama at
  Birmingham", as written.

## Phase 2 discoveries back-ported into the full record

Phase 2 (core derivation) and the Phase 3 audit surfaced two source-supported items
absent from the Phase 1 full record. Both were corrected in **full first**, then
re-projected into core:

1. `anomalies` — a new entry recording the eight metadata-level inconsistencies listed
   above, scoped explicitly as anomalies in the packaged metadata rather than in the
   measured data.
2. `keywords` — the release's 13 `schema:about` controlled subject annotations
   (7 MeSH, 4 EDAM, 2 Cellosaurus terms) were appended alongside the 39 free-text
   keywords, since `keywords` is the only subject-descriptor slot on `Dataset`.

A third item required no back-port: core's `CoreDistribution.md5` surfaced six checksums
that `FileCollection` has no slot for. Those six MD5 values were already stated verbatim
in the corresponding full `file_collections` descriptions, so full lost nothing; this was
verified mechanically (every core `md5` is a substring of the matching full description).

## Deliberate omissions

Recorded so they read as decisions rather than gaps:

- `total_file_count` — omitted; see disagreement 2.
- `FileCollection.total_bytes` and `file_count` — omitted for all 9 collections; the
  crate's `contentSize` strings are demonstrably unreliable (disagreement 1) and the
  `hasPart` counts mix data files with schemas, samples, instruments and experiments.
  Both figures are quoted in each collection's description instead.
- `subsets` and `splits` — omitted. The modality decomposition is carried by
  `file_collections` under the pinned referent; emitting it a second time as `subsets`
  would duplicate rather than inform. No train/test/validation split is evidenced.
- `doi`, `version`, `issued` at top level — omitted. Under the pinned referent these are
  release-scoped facts and live on the June 2026 `resources` entry;
  `version_access.latest_version_doi` carries the current release DOI at top level.
- `related_datasets`, `parent_datasets` — omitted; the inter-release and
  release-to-collection relations are already structural under the pin.
- `collection_notifications`, `collection_consents`, `consent_revocations`,
  `participant_privacy`, `participant_compensation` — omitted; the no-human-subjects
  facts are carried once, in `human_subject_research`, `informed_consent`,
  `at_risk_populations` and `is_deidentified`.
- `dialect`, `compression`, `content_warnings`, `errata`, `extension_mechanism`,
  `variables`, `cleaning_strategies`, `labeling_strategies`, `imputation_protocols`,
  `annotation_analyses`, `machine_annotation_tools`, `data_protection_impacts` — no
  supporting evidence in the declared bundle.

## Assessment of the declared evidence

The crate is strong on identity, licensing, ethics, governance, funding, attribution and
provenance topology, and unusually strong on responsible-AI narrative (`rai:*` supplies
limitations, biases, use cases, missing data, collection method and maintenance plan
directly). It is weak on verifiability and quantitative characterisation: 8 of 55859
entities carry checksums, no entity carries summary statistics, sizes are reported in a
form that contradicts the byte count, and no variable-level metadata exists. It also
carries a consistent layer of stale, release-scoped values inside constituent collections
because those collections are carried forward across releases without their narrative
being refreshed.

## Validation after Phase 3 corrections

```bash
poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_all.yaml -C Dataset <full>          # No issues found
poetry run linkml-term-validator validate-data <full> --schema .../data_sheets_schema_all.yaml --target-class Dataset          # Validation passed
poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml -C CoreDataset <core> # No issues found
poetry run linkml-term-validator validate-data <core> --schema .../data_sheets_schema_core_all.yaml --target-class CoreDataset # Validation passed
```

---

# Phase 4 — strict full/core reconciliation

## Schema-derived shared-slot analysis

Shared slots were derived at runtime with LinkML `SchemaView` from `Dataset` and
`CoreDataset`; no hand-written field list was used.

- **Schema-identical shared slots (same induced range and cardinality): 76.**
  All 76 have identical presence and deeply identical parsed YAML content in both files,
  verified independently of the validator (`shared present slots differing: []`).
  Narrative fields are included: core does not condense, paraphrase, reorder or omit any
  shared content.
- **Projected slot: `resources`** (`Dataset` in full, `CoreDataset` in core).
- **Full-only slots present in the record:** `citation`, `direct_collection`,
  `file_collections`, `relationships`, `third_party_sharing`, `total_size_bytes`.
- **Core-only slot present in the record:** `distributions`.

Top-level populated slot counts: **full 60, core 55** (informational metadata only).

## `resources` projection

Coverage is equal: 3 releases matched by `id` in both files, no unmatched entries in
either direction. For every matched resource, every slot present in the core projection
is deeply identical to full. Full-only nested slots dropped from the projection, as the
schema requires: `citation` and `total_size_bytes` on the June 2026 release (neither slot
exists on `CoreDataset`). The two prior-release entries project without loss.

## Semantic review of related content: `file_collections` ↔ `distributions`

The pair validator emits `semantic-review-required` for this mapping with 9 deterministic
matches and 0 unmatched core distributions. That warning marks work to be done, not work
done; the review was performed and is recorded here.

- **Coverage:** 9 ↔ 9, matched by `id`, equal in both directions.
- **Names:** identical for all 9, verified mechanically.
- **Descriptions:** identical for all 9, verified mechanically. No condensation.
- **Paths:** identical for all 9 (`AP-MS/...`, `Images/...`, `mass-spec/...`,
  `Perturb-Seq/...`), taken from each collection's `ro-crate-metadata` location.
- **Checksums:** 6 of 9 distributions carry `md5`. `FileCollection` has no checksum slot,
  so these appear structurally in core only; each value was confirmed to be stated
  verbatim in the matching full description, so the pair does not disagree. The 3
  collections without an `md5` are the two EndoTag AP-MS collections and the SEC-MS
  KOLF2 differentiation collection, for which the crate publishes no MD5.
- **Byte counts:** absent on both sides by decision (Phase 3, disagreement 1). Full's
  `total_size_bytes` (21051331945400) is release-scoped and has no core counterpart
  slot; because no distribution-level byte count exists on either side, there is no
  scope mismatch to reconcile.
- **Formats / compression / encoding / media type:** absent on both sides.
  `CoreDistribution.format` is restricted to an enum (CSV, TSV, XML, JSON, …) that does
  not admit the release's actual formats (`.d` directory groups, `fastq.gz`, `h5ad`,
  `image/jpeg`), so populating it would have forced a false value. The format inventory
  is instead carried identically in both files by the shared
  `distribution_formats` entry `d4d:cm4ai-distribution-file-formats`.
- **Access URLs:** `CoreDistribution` has no access-URL slot, so the nine collections'
  `download_url` and `page` values are full-only. They do not conflict with core, because
  the same access points are carried identically in both files by the shared
  `distribution_formats` and `external_resources` entries (Dataverse, five MassIVE
  endpoints, FigShare). No access point is reachable from full only.
- **Release scope:** all 9 collections belong to the current (June 2026) release, per the
  pinned referent. Their individual `version` values (0.1.0 to 1.5) and publication dates
  (2025-02-28 to 2026-05-27) are collection-level, not release-level, and are stated as
  such in the descriptions carried by both files.
- **Other full-only per-collection slots dropped by the projection** (no `CoreDistribution`
  counterpart): `collection_type`, `created_by`, `doi`, `download_url`, `keywords`,
  `license`, `page`, `status`, `version`. Reviewed for conflict: none, since core makes
  no competing assertion about any of them. The one material loss is per-collection
  licensing — three collections are CC0 1.0 while the release is CC BY-NC-SA 4.0 — which
  is preserved in core through the shared `license_and_use_terms.license_terms`, so the
  CC0 nuance survives the projection.

## Cross-record identity, version and access consistency

- Top-level `id` is the release-level CM4AI project ark in both files, matching the
  identifier chosen in Phase 3.
- `version_access.latest_version_doi` (`10.18130/V3/HIGT4C`) equals the `doi` of the
  June 2026 `resources` entry in both files.
- Top-level `status` ("Ongoing release series; current release is a Beta interim
  release…") agrees with the June 2026 resource `status: Beta` and with
  `known_limitations` (interim release, embargo, no predicted cell maps).
- Top-level `license`, `publisher`, `page`, `conforms_to` agree between the two files and
  with the release-level crate values.
- Historical versus current releases are distinguished, not treated as contradictions:
  the June 2026 entry carries full release metadata; the January 2026 and October 2025
  entries carry only what the crate supplies for them and say so explicitly.
- `is_tabular: false` in both files, consistent with the declared format inventory.

## Commands run

```bash
poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_all.yaml -C Dataset \
  data/d4d_concatenated/claudecode_agent_crate_only/2026-07-28_claude-opus-5-crateonly-deprimed_rep1/CM4AI_d4d.yaml
poetry run linkml-term-validator validate-data \
  data/d4d_concatenated/claudecode_agent_crate_only/2026-07-28_claude-opus-5-crateonly-deprimed_rep1/CM4AI_d4d.yaml \
  --schema src/data_sheets_schema/schema/data_sheets_schema_all.yaml --target-class Dataset
poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml -C CoreDataset \
  data/d4d_concatenated/claudecode_agent_crate_only_core/2026-07-28_claude-opus-5-crateonly-deprimed_rep1/CM4AI_d4d_core.yaml
poetry run linkml-term-validator validate-data \
  data/d4d_concatenated/claudecode_agent_crate_only_core/2026-07-28_claude-opus-5-crateonly-deprimed_rep1/CM4AI_d4d_core.yaml \
  --schema src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml --target-class CoreDataset
poetry run python -m data_sheets_schema.d4d_pair_consistency --full <full> --core <core> --sync-core
poetry run python -m data_sheets_schema.d4d_pair_consistency --full <full> --core <core>
poetry run d4d provenance record --project CM4AI --method claudecode_agent_crate_only \
  --label 2026-07-28_claude-opus-5-crateonly-deprimed_rep1 \
  --input-bundle data/preprocessed/concatenated/CM4AI_crate_only.txt
```

## Final results

| Check | Result |
|---|---|
| Full schema validation (`Dataset`) | No issues found |
| Full term validation | Passed |
| Core schema validation (`CoreDataset`) | No issues found |
| Core term validation | Passed |
| Schema-derived pair consistency (independent run, no `--sync-core`) | `PASS: 76 schema-identical slots; projected slots=['resources']` |
| Schema-identical slots with differing content | 0 |
| `resources` projection coverage | 3 ↔ 3, equal, deep identity on all projected slots |
| `file_collections` ↔ `distributions` semantic review | 9 ↔ 9, reviewed above, 0 unresolved contradictions |
| Files changed during Phase 3/4 | full (added `anomalies`, extended `keywords`); core re-projected from the corrected full |
| Unresolved contradictions within or between the records | none |

The `--sync-core` pass made no content change beyond what the deterministic projection
had already produced; the subsequent independent run passes without it.
