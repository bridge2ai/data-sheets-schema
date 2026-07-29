# CM4AI full/core reconciliation — 2026-07-28_claude-opus-5-generic_rep1

- Project: CM4AI
- Arm: BASELINE (input documents only)
- Prompt: `src/download/prompts/d4d_generic_arm_prompt.md` (identical text for all projects)
- Runtime / provider / model: Claude Code / Anthropic / claude-opus-5[1m], temperature 0.0
- Mode: four-phase project agent, phases executed sequentially in one context
- Declared input bundle: `data/preprocessed/concatenated/CM4AI_preprocessed.txt`
- Manifest: `data/preprocessed/source_manifest.yaml`
- Full: `data/d4d_concatenated/claudecode_agent/2026-07-28_claude-opus-5-generic_rep1/CM4AI_d4d.yaml`
- Core: `data/d4d_concatenated/claudecode_agent_core/2026-07-28_claude-opus-5-generic_rep1/CM4AI_d4d_core.yaml`

## Referent choice

`Dataset` admits one referent. The declared bundle contains ten documents describing several
distinguishable things: the CM4AI project as a funded programme (NIH RePORTER, cm4ai.org, the
project preprint), five separately DOI'd CM4AI data releases in the University of Virginia
Dataverse, and one unrelated-in-scope publication (a U2OS cell map study).

The referent chosen is **the CM4AI data release programme** — the quarterly, publicly archived
CM4AI data releases in LibraData / University of Virginia Dataverse — with each individual
release enumerated under `resources`. This is what the bundle best supports: four of the ten
documents are release records, the release page and the project documentation both describe the
releases as a continuing quarterly series, and no single release accounts for the programme-level
statements (mission, cell lines, governance, licensing, quarterly cadence) that most of the bundle
carries. The same referent is held consistently in both records.

The Nature article "Multimodal cell maps as a foundation for structural and functional genomics"
(Schaffer et al. 2025) is in the bundle and acknowledges the same Bridge2AI core award
(OT2 OD032742), but it reports a U2OS osteosarcoma cell map, whereas every CM4AI release describes
MDA-MB-468 and KOLF2.1J. These are distinct entities. It is therefore represented as an
`external_resources` entry (with its own data-availability identifiers) and a `related_datasets`
`references` link, and none of its factual content — protein counts, assembly counts, methods,
repository accessions — is merged into the CM4AI release descriptions.

## Phase 3 — source and provenance audit

### Provenance

- Factual inputs used: the declared bundle and `data/preprocessed/source_manifest.yaml` only.
- Structural inputs: `data_sheets_schema_all.yaml` (class `Dataset`) and
  `data_sheets_schema_core_all.yaml` (class `CoreDataset`), enumerated at runtime with LinkML
  `SchemaView`; no prior record was used as a template.
- No file under `data/d4d_concatenated/`, `data/d4d_individual/`, or any `*_crate_d4d.yaml` /
  `*_crate_mapped_d4d.yaml` was read, opened, grepped, or consulted. The only directory listing
  performed against `data/d4d_concatenated/` was of directory names, to confirm the run label was
  not already in use.
- No evaluation report, test fixture, schema example value, or `d4d:docExample` supplied a value.
- No live web content was fetched.

### Source disagreements found and how they are represented

Each of these is recorded as stated by each source rather than resolved to one value.

1. **Collaborating institutions.** The CM4AI data-releases page lists "UCSD, UCSF, Stanford, UVA,
   Yale, UT Austin, UA Birmingham, Simon Fraser University, and the Hastings Center"; the Dataverse
   release descriptions give the same list without UT Austin. Both are quoted in the top-level
   `description`, and the release-level list is quoted verbatim inside the March 2025 resource.
2. **June 2026 release date.** Dataverse citation metadata gives Publication Date 2026-06-17 (with
   a version 2 release time of 2026-07-15T20:28:19Z recorded in the manifest); the CM4AI
   data-releases page labels the same DOI "June 2026 Data Release (Beta)" but displays "Released
   on: June 17, 2025". Both appear in the June 2026 resource description and in
   `distribution_dates.description`.
3. **Project end date.** NIH RePORTER records project end 2026-08-31; the release maintenance plan
   states updates "through the end of the project in November 2026". Both appear in
   `collection_timeframes`.
4. **Immunofluorescence protein coverage.** March 2025 file descriptions say 563 proteins per
   condition; June 2025, October 2025 and June 2026 say 464; the data-releases page says "IF images
   for 523 proteins". All three figures are attributed to their source in the IF `instances` entry
   and in the per-file descriptions.
5. **Production location.** The March 2025 release lists "University of California San Francisco"
   twice; later releases list it once. Recorded as given per release.

### Unsupported, stale, or mis-scoped assertions checked for

- Portal "Data Insights" figures (1,374 protein interactions; 53,788 IF images; 7,023 proteins;
  11,739 genes; 21.4 TB) are attributed to the portal and not restated as per-release counts.
  `total_size_bytes` was left unset rather than converting "21.4 TB" to a byte count.
- `issued` / `created_on` (range `datetime`) were left unset because the sources give calendar
  dates, not timestamps; the one exact timestamp available (2026-07-15T20:28:19Z) is recorded in
  `last_updated_on` on the June 2026 resource.
- The June 2025 release page shows only the first 10 of its 21 files. `total_file_count: 21` is
  recorded and the resource description states explicitly that the file inventory listed is
  partial. No files were invented to fill the gap.
- The DXWOS5 release (cited in the preprint) and the "May 2024 Data Release" listed in the
  data-releases archive are **not** asserted to be the same object; DXWOS5 is enumerated as a
  resource with only the metadata the preprint supplies, and the archive listing is noted
  separately in `distribution_dates.description`.
- Historical releases are retained with explicit historical scope (each carries its own DOI,
  version, publication date and file inventory); the current release is identified through
  `version_access.latest_version_doi`.

### Internal consistency checks

- Trey Ideker's ORCID (0000-0002-1708-8454) is identical everywhere it appears; likewise the
  ORCIDs used as `contact_person` references for ethical review.
- CC BY-NC-SA 4.0 is the license on every release and at programme level; the license URL is
  identical in `license`, `license_and_use_terms` and each resource.
- Grant identifiers are consistent: 1OT2OD032742-01, core OT2OD032742, supplement
  3OT2OD032742-01S2, plus 5U54HG012513-02 for the Bridge Center.
- MD5 checksums: the three IF image archives carry identical MD5s in the June 2025 and October
  2025 releases (0d972b80…, a98affcc…, ad4e68cc…) and different MD5s in June 2026 (6c1a8652…,
  6d066e6b…, df796327…). This is what the sources show and is recorded without alteration.

### Phase 2 discoveries back-ported into the full record

Two additions were made to the full record during Phase 3, both supported by the declared bundle:

- `cleaning_strategies` — the preprint's statement that the Year 1 CRISPR screen data "are
  currently being QCed", together with the FAIRSCAPE validation step in the Standards Module.
- `status: Beta` and `created_by: 'Niestroy, Justin'` on each of the four Dataverse release
  resources, from the release titles and the Dataverse Depositor field.

Both files were regenerated and re-validated after these corrections.

## Phase 4 — strict full/core reconciliation

The shared-slot inventory was derived at runtime from `Dataset` and `CoreDataset` with LinkML
`SchemaView`; no hand-written field list was used.

- **Schema-identical shared slots: 76.** All are present-in-both or absent-in-both and deeply
  identical, including every narrative field. Core condenses, paraphrases, reorders and omits
  nothing.
- **Projected slots: `resources`.** Full range `Dataset`, core range `CoreDataset`. The five
  releases match by `id` with equal coverage, and every schema-identical nested slot is deeply
  identical.
- **Full-only slots (6), omitted from core because `CoreDataset` does not declare them:**
  `citation`, `collection_consents`, `direct_collection`, `related_datasets`, `relationships`,
  `third_party_sharing`. Their content is not lost silently: the consent/sourcing statements also
  appear in `human_subject_research` and `is_deidentified`, the modality-relationship statements
  also appear in `missing_data_documentation` and `preprocessing_strategies`, and the distribution
  statements also appear in `distribution_formats` and `external_resources` — all of which are
  shared slots and therefore identical in both records.

### Related, non-identical representations — semantic review

- **`file_collections` (full) → `distributions` (core).** 40 file entries across four releases were
  mapped one-to-one, preserving `id`, `name`, `path`, `compression` and `description` verbatim.
  Core additionally carries `md5` (lifted from the checksum recorded in each full description),
  `format` and `media_type` (derived from the file extension: `.zip` → ZIP / application/zip,
  `.json` → JSON / application/json, `.html` → HTML / text/html). No name, path, checksum,
  compression value or release scope conflicts between the two representations. `bytes` was left
  unset in core because the sources report sizes as rounded human-readable values ("3.8 GB"), not
  byte counts.
- **`total_file_count` (full) vs distribution-level counts (core).** The declared counts (6, 21, 8,
  10) match the number of distributions per release except for the June 2025 release, where the
  count is 21 and 10 distributions are listed. That gap is the source's own partial listing, is
  stated in the resource description, and is not a contradiction between the two records.
- **`is_tabular` / `dialect` / formats.** Neither record asserts `is_tabular`; `dialect` is unset in
  core. The released artefacts are ZIP archives, JSON metadata and HTML documents, consistent with
  the `format` values assigned in core and with `distribution_formats` in both records.
- **Top-level identity, version and access facts** agree with the resource-level entries: the
  programme-level `license`, `publisher` and `page` match every release's values, and
  `version_access.latest_version_doi` (10.18130/V3/HIGT4C) matches the release enumerated as the
  current one.
- **Historical vs current release.** The four dated releases are represented as distinct resources
  with their own DOIs and version strings rather than as conflicting values of one release.

## Commands run

```bash
poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_all.yaml \
  -C Dataset data/d4d_concatenated/claudecode_agent/2026-07-28_claude-opus-5-generic_rep1/CM4AI_d4d.yaml

poetry run linkml-term-validator validate-data \
  data/d4d_concatenated/claudecode_agent/2026-07-28_claude-opus-5-generic_rep1/CM4AI_d4d.yaml \
  --schema src/data_sheets_schema/schema/data_sheets_schema_all.yaml --target-class Dataset

poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml \
  -C CoreDataset data/d4d_concatenated/claudecode_agent_core/2026-07-28_claude-opus-5-generic_rep1/CM4AI_d4d_core.yaml

poetry run linkml-term-validator validate-data \
  data/d4d_concatenated/claudecode_agent_core/2026-07-28_claude-opus-5-generic_rep1/CM4AI_d4d_core.yaml \
  --schema src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml --target-class CoreDataset

poetry run python -m data_sheets_schema.d4d_pair_consistency \
  --full data/d4d_concatenated/claudecode_agent/2026-07-28_claude-opus-5-generic_rep1/CM4AI_d4d.yaml \
  --core data/d4d_concatenated/claudecode_agent_core/2026-07-28_claude-opus-5-generic_rep1/CM4AI_d4d_core.yaml \
  --sync-core

poetry run python -m data_sheets_schema.d4d_pair_consistency \
  --full data/d4d_concatenated/claudecode_agent/2026-07-28_claude-opus-5-generic_rep1/CM4AI_d4d.yaml \
  --core data/d4d_concatenated/claudecode_agent_core/2026-07-28_claude-opus-5-generic_rep1/CM4AI_d4d_core.yaml

poetry run d4d provenance record --project CM4AI --method claudecode_agent \
  --label 2026-07-28_claude-opus-5-generic_rep1 \
  --input-bundle data/preprocessed/concatenated/CM4AI_preprocessed.txt
```

## Files changed

- `data/d4d_concatenated/claudecode_agent/2026-07-28_claude-opus-5-generic_rep1/CM4AI_d4d.yaml` (new)
- `data/d4d_concatenated/claudecode_agent_core/2026-07-28_claude-opus-5-generic_rep1/CM4AI_d4d_core.yaml` (new)
- `data/d4d_concatenated/claudecode_agent_core/2026-07-28_claude-opus-5-generic_rep1/CM4AI_reconciliation.md` (this file)
- `data/d4d_concatenated/claudecode_agent_core/2026-07-28_claude-opus-5-generic_rep1/CM4AI_provenance.yaml` (live provenance record)

Nothing outside these four paths was written.

## Result

| Check | Result |
|---|---|
| Full schema validation (`Dataset`) | pass |
| Full ontology term validation | pass |
| Core schema validation (`CoreDataset`) | pass |
| Core ontology term validation | pass |
| Schema-identical shared slots | 76, all deeply identical |
| Projected slots | `resources` — 5 releases, equal coverage, deeply identical nested content |
| Pair consistency validator (final, no `--sync-core`) | PASS |
| Unresolved contradictions within or between records | none |
| Prior-run D4D content consulted | none |

Top-level populated slots: full 60, core 54 (informational only, not a quality gate).
Line counts: full 1995, core 1499 (informational only).
