# CM4AI full/core reconciliation — 2026-07-28_claude-opus-5-programme-deprimed_rep3

Run identity (verbatim, as recorded in both file headers):

- Agent runtime: Claude Code
- Provider: Anthropic
- Model: claude-opus-5[1m]
- Mode: four-phase project agent, pinned-referent
- Temperature: 0.0
- Generated: 2026-07-28
- Arm: BASELINE (document corpus only)

Artifacts:

- Full: `data/d4d_concatenated/claudecode_agent/2026-07-28_claude-opus-5-programme-deprimed_rep3/CM4AI_d4d.yaml` (2327 lines)
- Core: `data/d4d_concatenated/claudecode_agent_core/2026-07-28_claude-opus-5-programme-deprimed_rep3/CM4AI_d4d_core.yaml` (1542 lines)
- Provenance: `data/d4d_concatenated/claudecode_agent_core/2026-07-28_claude-opus-5-programme-deprimed_rep3/CM4AI_provenance.yaml` (`record_mode: live`)

Line counts are informational metadata only, not a quality gate.

---

## Phase 3 — Source and provenance audit

### Provenance boundary

Factual input was restricted to a single file,
`data/preprocessed/concatenated/CM4AI_preprocessed.txt` (7,873 lines, 10 source
documents), with `data/preprocessed/source_manifest.yaml` read for source
identity, curation notes and selection policy. Structure was derived exclusively
from `Dataset` in `data_sheets_schema_all.yaml` and `CoreDataset` in
`data_sheets_schema_core_all.yaml`, resolved at runtime with LinkML `SchemaView`
(class slots, induced ranges, cardinality, inlining, enum permissible values).

No prior D4D record, evaluation, reconciliation report, RO-Crate package or live
web content was read. Nothing under `data/d4d_concatenated/`,
`data/d4d_individual/` or `data/ro-crate_packages/` was opened other than this
run's own three output paths. The only generated YAML read during Phase 2 was
this run's own Phase 1 full record, at the exact same-run label. No
`d4d:docExample` annotation value was copied into either record.

### Source coverage

All ten documents in the bundle were used:

| # | Source ID | Role in the record |
|---|-----------|--------------------|
| 1 | `nature_publication` | Methodology context, LLM annotation accuracy, U2OS map as a related (non-release) resource, Bridge2AI acknowledgement |
| 2 | `biorxiv_preprint` | Programme mission, pillars/modules, cell lines, MuSIC and FAIRSCAPE, licensing, copyright, ethics, funding, citation |
| 3 | `nih_reporter_project` | Award identifiers, PI, organization, award amount, project period, purpose and gap statements |
| 4 | `project_documentation` (cm4ai.org) | Programme-level "Data Insights" aggregates, funding award number, contacts, review notice |
| 5 | `data_release_documentation` (cm4ai.org/data-releases) | Quarterly-release framing, flagship dataset summaries, release archive list, current release label and DOI, release-date conflict |
| 6 | `dataset_license` (CC BY-NC-SA 4.0 deed) | Licence identity |
| 7 | `march_2025_dataverse_release` (B35XWX) | Release 1: DOI, version, dates, 6-file inventory, sizes, checksums, authorship, deposit metadata |
| 8 | `june_2025_dataverse_release` (F3TD5R) | Release 2: DOI, version, dates, 21-file inventory, revision note, governance/ethics/completeness/limitations blocks |
| 9 | `october_2025_dataverse_release` (K7TGEM) | Release 3: DOI, version, dates, 8-file inventory, sizes, checksums, embargo statements |
| 10 | `june_2026_dataverse_release` (HIGT4C) | Current release: DOI, version, dates, 10-file inventory, sizes, checksums, AP-MS addition, external links |

### Source disagreements resolved

1. **June 2026 release date.** `cm4ai.org/data-releases` labels the release
   "June 2026 Data Release (Beta)" with DOI `10.18130/V3/HIGT4C` but states
   "Released on: June 17, 2025". The LibraData record for the same DOI gives
   Publication Date `2026-06-17`, a 2026 citation year, and file publication
   dates of 2026-06-17 / 2026-07-15. **Resolved in favour of the Dataverse
   metadata** (authoritative repository record, internally corroborated by the
   file publication dates and the release label itself). `issued` on the
   `HIGT4C` resource is `2026-06-17T00:00:00Z`. The conflict is recorded
   explicitly in the resource `description`, in `anomalies`, in
   `distribution_dates`, and as an uncorrected item in `errata`.

2. **Version label vs citation version.** Every release page displays a version
   that differs from the version in its own recommended citation (page 1.4 /
   cited V1; 2.1 / V2; 2.1 / V2; 2.0 / V2). **Both retained**: `version` carries
   the displayed page version; the divergence is stated in each resource's
   `status` and in `version_access.version_details`.

3. **Project end date.** Release maintenance plans say "through the end of the
   project in November 2026"; NIH RePORTER gives the project period as
   2022-09-01 to 2026-08-31. **Neither overridden** — both are recorded, with
   attribution, in `collection_timeframes.timeframe_details` and flagged in
   `anomalies`.

4. **Institution list.** The release page lists nine collaborating institutions
   including UT Austin; the Dataverse dataset descriptions list eight and omit
   UT Austin. The fuller release-page list is used in the top-level
   `description`; the release-author affiliations (which include UT Austin,
   University of Alabama, University of Montreal and KTH) are recorded on the
   release author-group creator entry.

5. **Andrej Sali's affiliation.** The Dataverse author list records "Sali A
   (University of California San Diego)"; the preprint and the Nature paper
   place him at UCSF. UCSF is used, and the conflict is stated in that creator's
   `description`.

6. **IF-image protein counts.** 563 proteins (March 2025 archives) vs 464
   proteins (June 2025 and October 2025 archives) vs "IF images for 523
   proteins" on the portal's flagship-dataset summary. These are scoped
   statements about different artifacts and are recorded where they belong
   (per-release descriptions and the flagship-dataset `Instance`) rather than
   reconciled into a single number. The June 2026 archives carry no per-file
   description upstream; their checksums differ from the October 2025 archives,
   so no protein count is asserted for them.

7. **Archive sizes shrinking across releases.** `cm4ai_mass-spec_KOLF2.zip` is
   23.8 MB in October 2025 and 171.8 KB in June 2026 (different checksums);
   several other archives shrink similarly. The sources do not explain this, so
   both values are recorded as stated and the discrepancy is listed under
   `anomalies` rather than silently normalised.

8. **Deposit dates.** All four releases carry the same Data Creation Date and
   Deposit Date (2025-02-27), including the June 2026 release. Recorded per
   resource as `created_on` and `created_by`, with a note in `anomalies` that
   these deposit-level dates do not distinguish the releases.

### Values deliberately not asserted

- `total_size_bytes` / `total_bytes` / `bytes` are omitted everywhere. The
  repository reports only rounded display sizes ("3.8 GB", "113.3 KB");
  converting these to integers would fabricate precision. The displayed size is
  recorded verbatim in each file's description instead.
- `data_topic`, `data_substrate` and `unit` (ontology-typed `uriorcurie` slots)
  are omitted; the corpus supplies no term identifiers for them.
- The May 2024 release is named in the release-page archive but has no DOI or
  inventory in the corpus, so it appears in `distribution_dates` and
  `version_access.versions_available` but not as a `resources` entry (which
  requires an `id`).
- CRediT roles were assigned only where the corpus states a role directly (PI,
  depositor, program manager, named laboratory of record, structural-modelling
  lead); the 47-name release author list is recorded as a single creator entry
  with no role attribution because the release records assign none.

### Phase 2 discoveries back-ported to full

None required. Core was derived from the Phase 1 full record plus the same
source bundle; re-checking each core field against the sources surfaced no
source-supported fact that the full record had missed or misstated. One
presentation change was made to the full record during Phase 2 so that the
shared description text reads identically in both files: a sentence in the first
file-collection description explaining that `FileCollection` has no checksum slot
was removed, leaving the factual content (size, MD5, download count) unchanged.

---

## Phase 4 — Strict full/core reconciliation

### Schema-derived shared slots

Shared slots were derived at runtime from `Dataset` and `CoreDataset` by
`data_sheets_schema.d4d_pair_consistency` (no hand-written field list).

- **Schema-identical slots: 76.** All present in both records with deeply
  identical parsed YAML, including every narrative field. Core condenses,
  paraphrases, reorders and omits nothing.
- **Projected slots: 1** (`resources`: `Dataset` in full, `CoreDataset` in core).
- **Full-only root slots dropped from core** (absent from `CoreDataset`):
  `citation`, `direct_collection`, `file_collections`, `related_datasets`,
  `relationships`, `third_party_sharing`.
- **Core-only root slots**: `distributions` (populated), `dialect` (omitted — the
  releases are ZIP archives of images and mass-spectrometry / sequencing
  outputs, not delimited text, and no dialect is stated).

### `resources` projection

All four releases are matched by `id` with equal coverage:

| id | full-only nested slots dropped in core |
|----|----------------------------------------|
| `https://doi.org/10.18130/V3/B35XWX` | `total_file_count` |
| `https://doi.org/10.18130/V3/F3TD5R` | `total_file_count` |
| `https://doi.org/10.18130/V3/K7TGEM` | `total_file_count` |
| `https://doi.org/10.18130/V3/HIGT4C` | `total_file_count` |

Every other nested slot on every resource — `doi`, `version`, `issued`,
`created_on`, `last_updated_on`, `license`, `page`, `publisher`, `compression`,
`status`, `created_by`, `keywords`, `title`, `name`, `description`, and the
nested `instances` and `missing_data_documentation` objects on the current
release — is deeply identical between full and core. `total_file_count` is not a
`CoreDataset` slot, so it is a permitted projection loss, not a divergence.

### Related-content review: `file_collections` ↔ `distributions`

Reviewed semantically, not just counted. 10 full file collections matched 10
core distributions one-to-one by `id`; no unmatched core distribution.

- **Names, paths, descriptions**: byte-identical in all 10 pairs (verified
  programmatically).
- **Checksums**: `FileCollection` has no checksum slot in the full schema, so
  each MD5 is stated verbatim in the full description; `CoreDistribution.md5`
  carries the same 32-character digest. All 10 digests match the digest embedded
  in the corresponding full description.
- **Byte counts**: neither side asserts a count (see "values deliberately not
  asserted"); both record the same rounded display size in the description. No
  conflict.
- **Formats and compression**: full sets `compression: zip` on all 10; core sets
  `compression: zip`, `format: ZIP`, `media_type: application/zip`. Consistent
  with the repository's "ZIP Archive (10)" file-type facet for this release.
  `is_tabular` is absent from both; `dialect` is absent from core. No conflict.
- **Access URLs and release scope**: full-only slots `page`, `download_url`
  (unused), `was_derived_from`, `license`, `issued`, `status`, `title` and
  `collection_type` have no `CoreDistribution` counterpart and are omitted from
  core. Release scope is still explicit in core because every distribution
  description names `doi:10.18130/V3/HIGT4C`.
- **Counts vs distribution-level values**: the `HIGT4C` resource declares
  `total_file_count: 10` in full, matching 10 file collections and 10 core
  distributions. `CoreDataset` has no `total_file_count`, so there is nothing in
  core that could contradict it.
- **Historical vs current scope**: only the current release's files are
  inventoried. Earlier releases' inventories (file counts, sizes, checksummed
  archive names, protein counts) are preserved as scoped narrative in each
  superseded resource's `description`. Differences between a superseded
  release's file set and the current one are therefore recorded as version
  history, not as contradictions.

The validator's `semantic-review-required` warning on this pair is the expected
marker that this review was owed; the review above discharges it. Zero
unresolved contradictions within or between the two records.

### Commands run

```bash
poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_all.yaml \
  -C Dataset data/d4d_concatenated/claudecode_agent/2026-07-28_claude-opus-5-programme-deprimed_rep3/CM4AI_d4d.yaml

poetry run linkml-term-validator validate-data \
  data/d4d_concatenated/claudecode_agent/2026-07-28_claude-opus-5-programme-deprimed_rep3/CM4AI_d4d.yaml \
  --schema src/data_sheets_schema/schema/data_sheets_schema_all.yaml --target-class Dataset

poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml \
  -C CoreDataset data/d4d_concatenated/claudecode_agent_core/2026-07-28_claude-opus-5-programme-deprimed_rep3/CM4AI_d4d_core.yaml

poetry run linkml-term-validator validate-data \
  data/d4d_concatenated/claudecode_agent_core/2026-07-28_claude-opus-5-programme-deprimed_rep3/CM4AI_d4d_core.yaml \
  --schema src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml --target-class CoreDataset

poetry run python -m data_sheets_schema.d4d_pair_consistency \
  --full data/d4d_concatenated/claudecode_agent/2026-07-28_claude-opus-5-programme-deprimed_rep3/CM4AI_d4d.yaml \
  --core data/d4d_concatenated/claudecode_agent_core/2026-07-28_claude-opus-5-programme-deprimed_rep3/CM4AI_d4d_core.yaml \
  --sync-core

poetry run python -m data_sheets_schema.d4d_pair_consistency \
  --full data/d4d_concatenated/claudecode_agent/2026-07-28_claude-opus-5-programme-deprimed_rep3/CM4AI_d4d.yaml \
  --core data/d4d_concatenated/claudecode_agent_core/2026-07-28_claude-opus-5-programme-deprimed_rep3/CM4AI_d4d_core.yaml

poetry run d4d provenance record --project CM4AI --method claudecode_agent \
  --label 2026-07-28_claude-opus-5-programme-deprimed_rep3 \
  --input-bundle data/preprocessed/concatenated/CM4AI_preprocessed.txt
```

### Results

| Check | Result |
|-------|--------|
| Full — LinkML schema validation (`Dataset`) | No issues found |
| Full — ontology term validation | Validation passed |
| Core — LinkML schema validation (`CoreDataset`) | No issues found |
| Core — ontology term validation | Validation passed |
| Pair consistency (pre-sync) | PASS: 76 schema-identical slots; projected `resources` |
| Pair consistency (post-sync, independent re-run) | PASS: 76 schema-identical slots; projected `resources` |
| Semantic review warning | `file_collections` ↔ `distributions`, 10/10 matched, reviewed above |
| Live provenance record | Written, `record_mode: live` |

### Files changed

- `.../claudecode_agent/2026-07-28_claude-opus-5-programme-deprimed_rep3/CM4AI_d4d.yaml` (created; one description edited in Phase 2, see above)
- `.../claudecode_agent_core/2026-07-28_claude-opus-5-programme-deprimed_rep3/CM4AI_d4d_core.yaml` (created; rewritten once by `--sync-core`)
- `.../claudecode_agent_core/2026-07-28_claude-opus-5-programme-deprimed_rep3/CM4AI_reconciliation.md` (this file)
- `.../claudecode_agent_core/2026-07-28_claude-opus-5-programme-deprimed_rep3/CM4AI_provenance.yaml` (created)

No existing file was overwritten.

---

## How the pinned referent was applied

**Top level = the programme.** `id` is `https://cm4ai.org/data-releases/`, the
programme's own release page, not a release DOI. The top level carries no `doi`,
no `version`, no `issued`, no `total_size_bytes` and no `total_file_count`.
`status` describes the series ("Active, ongoing quarterly Beta release series"),
`citation` is the programme-level preprint citation the release terms direct
users to cite, and `updates.frequency` is "Quarterly".

**`resources` = the four quarterly releases**, in date order, each with its own
`doi`, `version`, `issued` and `total_file_count` exactly as the corpus states
them. June 2026 (`HIGT4C`) is marked current; the other three are marked
superseded in their `status`.

**`file_collections` = the current release's inventory**, all ten HIGT4C
archives, each with `path`, `compression`, `collection_type`, `issued`, MD5 in
the description, and `was_derived_from: doi:10.18130/V3/HIGT4C`. They are placed
at the top level rather than nested under the `HIGT4C` resource, because the
programme's currently distributed file inventory *is* the current release's
inventory; every entry names the release explicitly so the scope is
unambiguous either way. `total_file_count: 10` stays on the release resource, as
directed.

**Modalities are composition, not resources.** AP-MS, SEC-MS, IF imaging,
perturb-seq and the RO-Crate metadata package are five `Instance` entries on the
`HIGT4C` resource, plus the corresponding `file_collections`. No modality appears
as a top-level `resources` entry. Programme-level composition (portal aggregates,
the two flagship curated datasets) sits in top-level `instances`, which describes
the series rather than any one release.

### What the programme framing made awkward to place

1. **The U2OS multimodal cell map** (Nature 642:222–231, 2025) is CM4AI/Bridge2AI
   funded and uses the same toolkit, but it is built in U2OS osteosarcoma cells —
   not the programme's MDA-MB-468 / KOLF2.1J lines — and is distributed through
   NDEx, MassIVE, ProteomeXchange, ModelArchive and the EBI Complex Portal rather
   than through the quarterly series. Making it a `resources` entry would have
   implied it was a release. It is recorded in `existing_uses` (with an explicit
   scope note), in `related_datasets` with `relationship_type: references` and
   all five deposition identifiers, and its LLM-annotation accuracy figures are
   carried in `machine_annotation_tools.tool_accuracy` under an explicit scope
   caveat.

2. **The first LibraData deposit `doi:10.18130/V3/DXWOS5`**, cited in the
   preprint's availability statement, has no version, date or inventory anywhere
   in the corpus. It cannot be a well-formed `resources` entry, so it sits in
   `related_datasets` with `relationship_type: is_part_of`.

3. **Checksums have no home in the full schema.** `FileCollection` exposes
   `path`, `compression`, `file_count` and `total_bytes` but no checksum slot,
   while `CoreDistribution` has `md5`/`sha256`/`hash`. MD5s are therefore verbatim
   text in full and structured data in core — the one place where core carries a
   fact more precisely than full.

4. **Rounded sizes cannot fill integer byte slots**, so `total_size_bytes`,
   `total_bytes` and `bytes` are empty across both records despite the corpus
   listing a size for every file.

5. **Superseded releases' file inventories** are rich in the corpus (names, sizes,
   checksums, per-file descriptions, protein counts) but the referent scopes
   `file_collections` to the current release. Rather than discard that evidence,
   each superseded resource's `description` carries its inventory as scoped prose,
   and the current-release file descriptions cite the October 2025 checksums to
   show which archives changed.

6. **The May 2024 release** is named on the release page but has no identifier in
   the corpus, so it can be listed as a date and a version but cannot be a
   resource.

7. **Deposit-level dates are release-invariant.** `created_on` / `created_by`
   (2025-02-27, depositor Niestroy) are identical on all four releases, which
   reads oddly on a per-release object; kept as stated and flagged in `anomalies`.
