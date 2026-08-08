# CM4AI full/core reconciliation — 2026-08-07_claude-opus-5-claudecode-generic-v3_rep2

- **Project:** CM4AI
- **Arm:** BASELINE (input documents only)
- **Runtime / provider / model:** Claude Code / Anthropic / claude-opus-5
- **Reasoning effort:** high (observed value of `$CLAUDE_EFFORT`)
- **Mode:** four-phase project agent, generic prompt
- **Prompt:** `src/download/prompts/d4d_generic_arm_prompt.md`
- **Declared input bundle:** `data/preprocessed/concatenated/CM4AI_preprocessed.txt`
- **Source manifest:** `data/preprocessed/source_manifest.yaml`
- **Full:** `data/d4d_concatenated/claudecode_agent/2026-08-07_claude-opus-5-claudecode-generic-v3_rep2/CM4AI_d4d.yaml`
- **Core:** `data/d4d_concatenated/claudecode_agent_core/2026-08-07_claude-opus-5-claudecode-generic-v3_rep2/CM4AI_d4d_core.yaml`

## Referent decision

`Dataset` admits one referent. The declared bundle describes two things that could be taken
as the CM4AI dataset, and they are not the same entity:

1. The **CM4AI data release programme** — the quarterly Beta data releases published in the
   "Cell Maps for Artificial Intelligence" collection of LibraData, the University of
   Virginia's Dataverse instance. Five releases are evidenced: May 2024
   (doi:10.18130/V3/DXWOS5), March 2025 (B35XWX), June 2025 (F3TD5R), October 2025 (K7TGEM)
   and June 2026 (HIGT4C, current).
2. The **U2OS multimodal cell map** of Schaffer et al., *Nature* 642:222–231 (2025), which the
   bundle carries as its first source document.

**The release programme is the pinned referent.** The bundle's project-level sources
(cm4ai.org, the Data Releases page, NIH RePORTER, the CM4AI project preprint) and four of its
ten documents describe that programme; the release pages themselves state that CM4AI "will
deliver … quarterly data releases of map-input data streams" and that each release "will be
regularly updated and augmented through the end of the project". Individual releases are
enumerated under `resources`, so the record describes the series without collapsing it into
any single release.

The U2OS cell map was **not** merged into the record. It is a distinct dataset: a different
cell line (U2OS osteosarcoma rather than MDA-MB-468 and KOLF2.1J), deposited in NDEx, the EBI
Protein Complex Portal, MassIVE (MSV000097168), ProteomeXchange (PXD052362) and ModelArchive
rather than in the UVA Dataverse collection, with a partly different author set. Its
acknowledgements cite the same Bridge2AI award (OT2 OD032742), which is the only stated
connection, and that is not enough to assert a typed dataset relationship. It is therefore
recorded in the top-level `source_caveats` and given **no** `related_datasets` entry — the
bundle states no relationship, and inventing one would be inference. The same choice is held
in both records.

## Phase 3 — source and provenance audit

### Provenance boundary

No prior generated D4D record was read, opened, grepped or consulted, from any arm, label or
date. Nothing under `data/d4d_concatenated/` other than this run's own two outputs was
accessed, and no `*_crate_d4d.yaml` or `*_crate_mapped_d4d.yaml` under
`data/ro-crate_packages/` was accessed. The complete factual input set for this run was:

- `data/preprocessed/concatenated/CM4AI_preprocessed.txt` (read in full; only the Nature
  article's numbered reference list and the nature.com site chrome were skimmed)
- `data/preprocessed/source_manifest.yaml` (CM4AI entries)
- `src/data_sheets_schema/schema/data_sheets_schema_all.yaml` and
  `data_sheets_schema_core_all.yaml`, read through `SchemaView` to derive class shapes, ranges,
  cardinalities and enum permissible values
- repository instructions: `.claude/agents/d4d-provenance-guard.md`,
  `.claude/commands/d4d-full-core.md`, `.claude/commands/d4d-agent.md`,
  `src/download/prompts/d4d_generic_arm_prompt.md`
- `src/data_sheets_schema/d4d_pair_consistency.py`, read to understand the Phase 4 contract

Structure was derived from the schemas only. No `d4d:docExample` value was copied.

### Mechanical verification against the bundle

A verification script re-extracted every identifier from the bundle and compared it to the
record:

- **34 of 34 MD5 checksums** written into `file_collections[].resources[].md5` occur verbatim
  in the bundle (31 distinct values; three IF-image checksums recur across the June 2025 and
  October 2025 releases, which is itself evidenced).
- **47 of 47 ORCIDs** used as `creators[].id` occur in the bundle.
- The `creators` list matches the Dataverse citation author block of the June 2026 release
  **exactly, in source order** — 47 names, no additions, no omissions.
- Every numeric and identifier claim spot-checked (1,374 / 53,788 / 7,023 / 11,739 / 21.4 TB;
  award 5289382; 1OT2OD032742-01; 5U54HG012513-02; 3OT2OD032742-01S2; application 11211616;
  RRID:CVCL_0419; RRID:CVCL_B5P3; the five release DOIs; 10.1101/2024.05.21.589311;
  10.1101/2024.11.03.621734; PMC11580897; download counts 302/256/405/181; protein counts
  563/464/523; 2026-07-15T20:28:19Z; the five contact addresses) occurs verbatim in the
  bundle.

### Source disagreements — represented, not silently resolved

Each of the following is recorded in a `source_caveats` slot at the level where it applies,
rather than resolved by preferring one source:

| Disagreement | Where recorded |
|---|---|
| cm4ai.org labels DOI HIGT4C the "June 2026 Data Release" but displays "Released on: June 17, 2025"; Dataverse gives publication date 2026-06-17 and version 2 released 2026-07-15T20:28:19Z | top-level `source_caveats`, HIGT4C resource `source_caveats` |
| Project end: NIH RePORTER 2026-08-31 vs. release maintenance plans "the end of the project in November 2026" | top-level `source_caveats`; both recorded as separate `collection_timeframes` entries with their own `source_caveats` |
| Collaborating institutions: Data Releases page includes UT Austin, Dataverse release descriptions omit it; the preprint adds U. Alabama and U. Montreal and omits the Hastings Center | top-level `source_caveats` |
| Sali A affiliated to UCSD in the Dataverse author list, UCSF in the preprint and in *Nature* | top-level `source_caveats` |
| Ravitsky V listed as University of Montreal while the ethics contact address is at the Hastings Center | top-level `source_caveats` |
| June 2026 page substitutes ROR `https://ror.org/0153tk833` for the University of Virginia affiliation name that the three earlier pages give | top-level `source_caveats`; the named form is used in `creators[].affiliations` |
| Copyright year 2024 (preprint) vs. 2025 (March 2025 and later releases) | top-level `source_caveats`; `ip_restrictions.restrictions` records both scopes |
| IF-image protein counts: 523 (Data Releases page) vs. 563 (March 2025 files) vs. 464 (June 2025, October 2025, June 2026 files) vs. "100 chromatin regulators … another 500 pending" (2024 preprint) | top-level `source_caveats`; per-release counts kept on the individual `File` descriptions |
| AP-MS: present in the June 2026 release, still "coming soon" on the Data Releases page | TNBC `subsets[].source_caveats`, `missing_data_documentation` |
| Dataverse page version indicator vs. citation version (2.0 vs V2, 1.4 vs V1, 2.1 vs V2) | `version_access.source_caveats` and each resource's `source_caveats` |

### Scoping and staleness

- The MuSIC integration pipeline and its LLM assembly-naming step are described, but each
  description states explicitly that the computed cell maps they produce **are not included in
  the releases documented here** (`preprocessing_strategies`, `machine_annotation_tools`).
- The "data are currently being QCed" statement is a Year-1 status claim from the May 2024
  preprint; it is retained with its date and scope stated in the value itself
  (`cleaning_strategies`), per the rule that historical values are kept only when their
  historical scope is explicit.
- The May 2024 release resource carries a `source_caveats` recording that the bundle supplies
  only its DOI, citation and version — no page capture, so no date, composition or file
  inventory is asserted for it.

### Corrections made during Phase 3

Five unsupported or mis-shaped values were found in the Phase 1 full record and corrected
before Phase 4:

1. `funders[0].grants[0]` description read "5,289,382 USD". NIH RePORTER states the bare
   figure `5289382` with no currency. Changed to state the figure and note that the source does
   not give a currency.
2. `citation` spelled the author as "Belisle-Pipon J-C"; the source citation reads
   "Bélisle-Pipon J-C". Corrected to match the source.
3. All four `external_resources` entries carried an `archival` boolean. The bundle makes no
   archival statement about MassIVE, NCBI BioProject/SRA, Figshare or the embargoed items, so
   `archival` was removed from all four rather than guessed.
4. `maintainers[2].role` (Zhandos Sembay, listed on cm4ai.org for website support and updates)
   was `researcher`; changed to `other`, since the source describes a website-support function
   rather than a research role.
5. `use_repository[1].repository_url` pointed at the June 2026 dataset page while the entry is
   named for the collection. Changed to the Dataverse root and the release URL moved into
   `repository_details`, with a note that the bundle gives no separate collection URL.

Two further shape corrections were required by the schema during Phase 1 and are recorded here
because they changed how facts are held:

- `principal_investigator`, `contact_person` and `governance_committee_contact` have range
  `Person` but are **not inlined**, so the schema requires a string reference. Each now holds
  the person's ORCID URI, and the person's name, address and affiliation were moved into the
  containing object's `description` / `review_details` so no fact was lost.
- `issued` and `created_on` have range `datetime`; the bundle supplies date-only values
  (2025-03-03, 2025-07-01, 2025-10-31, 2026-06-17, 2025-02-27). Rather than fabricate a
  midnight time, those slots were left unpopulated and each release's publication date is
  carried exactly as an ISO date string in that resource's `distribution_dates.release_dates`.
  `last_updated_on` on the June 2026 release is populated, because the bundle supplies a real
  timestamp (`2026-07-15T20:28:19Z`).

### Slot-filling and shape audit

Every populated value was checked against its slot's range: no prose in a slot requiring a
list, no enum value outside the schema's permissible values (`representation_bias`,
`scope_limitation`, `coverage_limitation`, `integration_limitation`,
`methodological_limitation`, `no_commercial_use`, `unrestricted`, `researcher`,
`academic_institution`, `other`, `is_described_by`, `zip`, `ZIP`, `JSON`, `HTML`,
`application/zip`, `application/json`, `text/html` were each confirmed against the enum
definitions), and no commentary embedded inside a name, identifier or affiliation value.
Evidence commentary is confined to `source_caveats`; `notes` is used once, at top level, for
the project's own definitions of AI-readiness and of a cell map, which no sibling slot holds.
Top-level `notes` was rewritten during Phase 3 because its first draft restated the
de-identification content already held by `is_deidentified`, `confidential_elements`,
`sensitive_elements` and `human_subject_research`.

### Phase 2 findings back-ported to full

None. Phase 2 derived core from `CoreDataset` and re-consulted the bundle for every core slot
the full record left empty. `CoreDataset` exposes exactly two slots that `Dataset` does not —
`distributions` and `dialect`. `distributions` is populated as the projection described below.
`dialect` (`FormatDialect`: comment prefix, delimiter, double quote, header, quote char) has no
support anywhere in the bundle — the releases are ZIP archives, JSON and HTML, not delimited
text — and is correctly absent from both records. No fact was discovered in Phase 2 that the
full record was missing, so nothing needed back-porting.

## Phase 4 — strict full/core reconciliation

Shared slots were derived at run time from `Dataset` and `CoreDataset` with LinkML
`SchemaView`; no hand-written field list was used.

- **Schema-identical shared slots: 78.** All 78 have identical presence and deeply identical
  parsed YAML content in the two records, including every narrative field. Core condenses,
  paraphrases, reorders and omits nothing.
- **Projected shared slots: 1** — `resources`.
- **Full top-level slots populated: 64. Core top-level slots populated: 58.**
- Full-only (7): `citation`, `subsets`, `relationships`, `direct_collection`,
  `third_party_sharing`, `file_collections`, `related_datasets`. Core-only (1):
  `distributions`. Every one of these is a schema difference between the two classes, not a
  content difference.

### `resources` projection

Five releases, matched by `id`, equal coverage in both records, no id missing from either
side:

| Resource id | full slots | core slots |
|---|---|---|
| `https://doi.org/10.18130/V3/DXWOS5` | 9 | 9 |
| `https://doi.org/10.18130/V3/B35XWX` | 12 | 12 |
| `https://doi.org/10.18130/V3/F3TD5R` | 12 | 12 |
| `https://doi.org/10.18130/V3/K7TGEM` | 12 | 12 |
| `https://doi.org/10.18130/V3/HIGT4C` | 13 | 13 |

Every nested schema-identical slot is deeply identical. No full-only nested slot was used
inside a resource, so the counts coincide; the projection is lossless here.

### Related, non-identical content: `file_collections` ↔ `distributions`

The full record holds four `FileCollection` objects, one per documented release, each with a
nested `File` list carrying per-file name, path, format, media type, MD5 and a description
that includes the repository's displayed size. Core holds four `CoreDistribution` objects with
the **same four ids and names**. The validator matched 4 of 4 by `id` with zero unmatched core
distributions and reported no field conflict.

Semantic review of the mapping, field by field:

- **names** — identical strings on both sides.
- **descriptions** — identical strings on both sides; no paraphrase.
- **paths** — absent on both sides. A release is not a path; per-file paths live only on the
  `File` objects in full. No conflict is possible.
- **formats** — set to `ZIP` on the two core distributions whose releases are wholly ZIP
  archives (K7TGEM, 8 archives; HIGT4C, 10 archives) and omitted for B35XWX and F3TD5R, whose
  inventories mix ZIP, JSON and HTML. `FileCollection` has no `format` slot, so full carries
  format only per file; those per-file values (`ZIP`/`JSON`/`HTML`) are consistent with the
  core release-level values.
- **compression** — `zip` on both sides for K7TGEM and HIGT4C; absent on both sides for the two
  mixed releases. Values agree where both are present.
- **checksums** — held per file in full (34 MD5s) and not at release level in core.
  `CoreDistribution.md5` is single-valued and a release has no single checksum, so it is left
  unpopulated rather than filled with one of its files' values. This is a **granularity
  difference, not a conflict**: core carries no checksum that full contradicts.
- **byte counts** — absent on both sides. Dataverse displays rounded sizes only ("3.8 GB",
  "31.1 KB"), so no integer `bytes` or `total_bytes` is asserted anywhere; displayed sizes are
  quoted verbatim in the per-file descriptions and the rounding is flagged in each
  collection's `source_caveats`.
- **access URLs** — `FileCollection.download_url` gives each release's Dataverse page.
  `CoreDistribution` has no URL slot, so none is projected. The Data Access API base
  (`https://dataverse.lib.virginia.edu/api/access/datafile/`) is recorded once in
  `distribution_formats[0].access_urls`, which is a schema-identical slot and therefore
  present identically in both records.
- **release scope** — each pair covers exactly one release DOI, and the descriptions on both
  sides name it. Historical releases (March 2025, June 2025, October 2025) are distinguished
  from the current release (June 2026) in every description and in `version_access`; their
  differing file inventories are a version history, not a contradiction. In particular, the
  three IF-image archives that share names and displayed sizes between October 2025 and June
  2026 but carry different MD5s are recorded as an `anomalies` entry and in the June 2026
  collection's `source_caveats`, not silently unified.

### Cross-record consistency of repeated facts

Checked and consistent within and between the two records: the five release DOIs; the release
versions (V1/V2 and the page indicators 1.4/2.1/2.1/2.0); the publication dates 2025-03-03,
2025-07-01, 2025-10-31 and 2026-06-17 as they appear in top-level `distribution_dates`, in
each resource's own `distribution_dates`, and in each `file_collections` description; the
single licence value `CC BY-NC-SA 4.0` at top level, on every resource and in
`license_and_use_terms`; the publisher `https://dataverse.lib.virginia.edu/`; the award numbers
1OT2OD032742-01 and 5U54HG012513-02; `status: Beta`; and the four Data Insights counts. Both
records omit `total_file_count`, `total_size_bytes` and `is_tabular`, which the bundle does not
support at programme level.

## Outcome

**Nothing diverged.** After the five Phase 3 corrections were made to the full record and
synchronised into core, the schema-derived validator passes with zero errors on all 78
schema-identical slots and on the `resources` projection. The single warning is the
validator's standing instruction that the `file_collections` ↔ `distributions` relation
requires human-level semantic review; that review is written out above and found no conflict.

## Commands run

```bash
echo "$CLAUDE_EFFORT"                     # -> high

poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_all.yaml \
  -C Dataset data/d4d_concatenated/claudecode_agent/2026-08-07_claude-opus-5-claudecode-generic-v3_rep2/CM4AI_d4d.yaml
poetry run linkml-term-validator validate-data \
  data/d4d_concatenated/claudecode_agent/2026-08-07_claude-opus-5-claudecode-generic-v3_rep2/CM4AI_d4d.yaml \
  --schema src/data_sheets_schema/schema/data_sheets_schema_all.yaml --target-class Dataset

poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml \
  -C CoreDataset data/d4d_concatenated/claudecode_agent_core/2026-08-07_claude-opus-5-claudecode-generic-v3_rep2/CM4AI_d4d_core.yaml
poetry run linkml-term-validator validate-data \
  data/d4d_concatenated/claudecode_agent_core/2026-08-07_claude-opus-5-claudecode-generic-v3_rep2/CM4AI_d4d_core.yaml \
  --schema src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml --target-class CoreDataset

poetry run python -m data_sheets_schema.d4d_pair_consistency \
  --full data/d4d_concatenated/claudecode_agent/2026-08-07_claude-opus-5-claudecode-generic-v3_rep2/CM4AI_d4d.yaml \
  --core data/d4d_concatenated/claudecode_agent_core/2026-08-07_claude-opus-5-claudecode-generic-v3_rep2/CM4AI_d4d_core.yaml \
  --sync-core

poetry run python -m data_sheets_schema.d4d_pair_consistency \
  --full data/d4d_concatenated/claudecode_agent/2026-08-07_claude-opus-5-claudecode-generic-v3_rep2/CM4AI_d4d.yaml \
  --core data/d4d_concatenated/claudecode_agent_core/2026-08-07_claude-opus-5-claudecode-generic-v3_rep2/CM4AI_d4d_core.yaml

poetry run d4d provenance record --project CM4AI --method claudecode_agent \
  --label 2026-08-07_claude-opus-5-claudecode-generic-v3_rep2 \
  --input-bundle data/preprocessed/concatenated/CM4AI_preprocessed.txt \
  --prompt src/download/prompts/d4d_generic_arm_prompt.md
poetry run d4d runs validate --label 2026-08-07_claude-opus-5-claudecode-generic-v3_rep2 --project CM4AI
poetry run d4d runs check --strict --label 2026-08-07_claude-opus-5-claudecode-generic-v3_rep2
```

## Final results

| Check | Result |
|---|---|
| `linkml-validate` full (`Dataset`) | No issues found |
| `linkml-term-validator` full | Validation passed |
| `linkml-validate` core (`CoreDataset`) | No issues found |
| `linkml-term-validator` core | Validation passed |
| `d4d_pair_consistency` (final, no `--sync-core`) | PASS — 78 schema-identical slots, projected slots `['resources']`, 1 semantic-review warning |
| Full top-level slots populated | 64 (1804 lines, informational only) |
| Core top-level slots populated | 58 (1155 lines, informational only) |
| Prior-D4D reuse | none; boundary held in all four phases |
