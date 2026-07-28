# CM4AI full/core reconciliation — 2026-07-28_claude-opus-5-programme-deprimed_rep2

- Agent runtime: Claude Code
- Provider: Anthropic
- Model: claude-opus-5[1m]
- Mode: four-phase project agent, pinned-referent
- Temperature: 0.0
- Generated: 2026-07-28
- Arm: BASELINE (document corpus only)
- Prior D4D factual reuse: prohibited

## Files

| Role | Path | Lines |
|------|------|-------|
| Full | `data/d4d_concatenated/claudecode_agent/2026-07-28_claude-opus-5-programme-deprimed_rep2/CM4AI_d4d.yaml` | 2086 |
| Core | `data/d4d_concatenated/claudecode_agent_core/2026-07-28_claude-opus-5-programme-deprimed_rep2/CM4AI_d4d_core.yaml` | 1485 |
| Provenance | `data/d4d_concatenated/claudecode_agent_core/2026-07-28_claude-opus-5-programme-deprimed_rep2/CM4AI_provenance.yaml` | `record_mode: live` |

Line counts are informational metadata, not a quality gate.

## Pinned referent — how it was applied

The subject of the record is the CM4AI data-release programme as an ongoing quarterly
release series.

1. **Top level is the programme.** `id: https://cm4ai.org/`. No `doi`, `version`, `issued`,
   `total_size_bytes` or `total_file_count` appears at the top level. Programme-level facts
   that do belong there are carried instead: `title`, `description`, `status` (ongoing Beta
   series through the stated end of project), `license`, `publisher`, `page`, `keywords`,
   `citation`, `conforms_to`, `is_tabular`, and `last_updated_on` (2026-07-15T20:28:19Z, the
   most recent release update).
2. **`resources` are the four quarterly releases**, in date order, each with its own `doi`,
   `version`, `issued`, `last_updated_on`, `page`, `total_file_count`, `license`, `citation`
   and `status`: March 2025 `10.18130/V3/B35XWX` (v1.4, 2025-03-03, 6 files, superseded);
   June 2025 `10.18130/V3/F3TD5R` (v2.1, 2025-07-01, 21 files, superseded); October 2025
   `10.18130/V3/K7TGEM` (v2.1, 2025-10-31, 8 files, superseded); June 2026
   `10.18130/V3/HIGT4C` (v2.0, 2026-06-17, 10 files, **current**). Supersession is expressed
   with `related_datasets` (`replaces` / `is_replaced_by`) chaining the four in order.
3. **`file_collections` describe the current release (HIGT4C)** as a ten-entry inventory, one
   entry per released ZIP archive, with `path`, `compression: zip`, `collection_type`,
   `file_count: 1`, `issued`, and MD5 checksum plus displayed size recorded in the
   description (`FileCollection` has no checksum or displayed-size slot).
4. **Modalities live inside the current release's composition and in the file inventory**, not
   as top-level `resources`. The HIGT4C resource carries five `instances` (IF imaging, SEC-MS,
   AP-MS, CRISPRi perturb-seq, release metadata/provenance package). Top-level `instances`
   carry only programme-scope composition: the four portal "Data Insights" totals (1,374
   protein interactions; 53,788 IF images; 7,023 proteins investigated; 11,739 genes
   targeted), the two cell lines, and the two portal "flagship dataset" descriptions.

### Content the programme framing made awkward to place

- **Programme data volume.** cm4ai.org reports "Data volume 21.4 TB". Under the referent,
  `total_size_bytes` may not sit at top level, and the figure is a rounded display value that
  cannot be converted to an exact byte count without fabricating precision. It is recorded in
  the top-level `description` instead.
- **A fifth, earlier release.** The project article's availability statement cites
  `10.18130/V3/DXWOS5` ("Cell Maps for Artificial Intelligence - Data Release", V1) and the
  cm4ai.org archive lists a May 2024 release. These belong to the programme but are outside
  the four pinned resources, so they are recorded in `version_access.versions_available`,
  `version_access.version_details`, and a top-level `related_datasets` entry with
  `relationship_type: has_part`.
- **The Nature 2025 multimodal cell map.** Schaffer, Hu et al., *Nature* 642:222-231 (2025)
  is Bridge2AI/CM4AI-funded (OT2 OD032742) but its U2OS dataset is distributed through NDEx,
  HPA, MassIVE (MSV000097168), ProteomeXchange (PXD052362) and ModelArchive — not through the
  quarterly releases. It is recorded as `existing_uses` and as an `is_referenced_by`
  `related_datasets` entry rather than as a resource.
- **Per-release file sizes.** Dataverse displays rounded sizes only ("3.8 GB", "113.3 KB"), so
  no `total_size_bytes` / `total_bytes` / `bytes` is asserted anywhere in the pair; the
  displayed strings are recorded verbatim in the file-inventory descriptions.
- **Release-scoped author list at programme level.** The 47-person author list is identical
  across all four releases, so it is modelled once as programme-level `creators` rather than
  repeated per resource.

## Phase 3 — source and provenance audit

### Provenance boundary

Factual inputs read: `data/preprocessed/concatenated/CM4AI_preprocessed.txt` and
`data/preprocessed/source_manifest.yaml` only. Structural references:
`data_sheets_schema_all.yaml`, `data_sheets_schema_core_all.yaml`, `D4D_Core.yaml` (via the
merged core schema), and `src/data_sheets_schema/d4d_pair_consistency.py`. Procedure
references: `.claude/agents/d4d-provenance-guard.md`, `.claude/commands/d4d-full-core.md`,
`.claude/commands/d4d-agent.md`.

No prior D4D record, evaluation, or reconciliation report was read, searched, or globbed; no
file under `data/d4d_concatenated/` or `data/d4d_individual/` other than this run's own
outputs was opened; nothing under `data/ro-crate_packages/` was touched; no live web content
was fetched. Every emitted slot and nested object shape was derived from the schemas via
`SchemaView`, not from any example record.

### Source conflicts and how they were resolved

1. **June 2026 release date (explicitly flagged in the task).** cm4ai.org labels the current
   release the "June 2026 Data Release (Beta)" but displays "Released on: June 17, 2025". The
   Dataverse record reports publication date 2026-06-17 and a version 2 release time of
   2026-07-15T20:28:19Z. **Resolved to the Dataverse metadata** as the authoritative
   repository of record (also the manifest's verification URL). The conflict is recorded
   explicitly in the HIGT4C resource `description` and in `distribution_dates.description`,
   in both full and core.
2. **Project end date — left unresolved by design.** NIH RePORTER gives project end
   2026-08-31; every release maintenance plan says data are augmented "through the end of the
   project in November 2026". These describe different things (award period vs data
   augmentation commitment), so no `end_date` is asserted in `collection_timeframes`; both
   statements are recorded in `timeframe_details`.
3. **Immunofluorescence protein counts differ by scope.** 563 proteins (March 2025 release
   file descriptions), 464 proteins (June 2025 and October 2025 release file descriptions),
   523 proteins (cm4ai.org flagship TNBC summary). Each figure is kept inside the scope of the
   source that states it rather than reconciled to a single number.
4. **Dataverse displayed version vs citation version.** Pages display 1.4 / 2.1 / 2.1 / 2.0
   while the data citations display V1 / V2 / V2 / V2. The displayed dataset version is used
   in `version`; the discrepancy is stated in each resource description and in
   `version_access.version_details`.
5. **Sali A affiliation.** Dataverse release metadata list University of California San Diego;
   the CM4AI project article and the Nature 2025 study list University of California San
   Francisco. The release metadata value is used (it is the authority for the release author
   list) and the discrepancy is stated in that creator's `description`.
6. **Collaborating institution list.** The March 2025 release description omits UT Austin; the
   cm4ai.org Data Releases page includes it. The more complete portal list is used.
7. **Award number forms.** `1OT2OD032742-01` (portal, all releases, project article),
   `3OT2OD032742-01S2` and core `OT2OD032742` (NIH RePORTER), `OT2 OD032742` (Nature
   acknowledgements). Recorded as three distinct `Grant` objects under one
   `FundingMechanism` rather than choosing between them.
8. **Copyright year.** The project article states copyright 2024; the March 2025 release states
   2025. No year is asserted in `ip_restrictions`; the holders are named without a year.
9. **The June 2025 release page states version 2.1 and notes "The 'DRAFT' version was not
   found. This is version '2.1'."** Treated as a Dataverse UI artefact, not a dataset fact;
   not recorded.

### Internal consistency checks (each file, against the sources)

- Release file counts asserted (6 / 21 / 8 / 10) match the Dataverse file-table counts and
  file-type tallies in the corpus (Archive 3 + Data 3; Text 12 + Data 5 + Archive 3 +
  Metadata 1; Archive 8; Archive 10).
- The single `license` string is identical at top level and on all four resources; all four
  releases state CC BY-NC-SA 4.0.
- `version_access.latest_version_doi` (HIGT4C) matches the only resource with
  `status: current`; the other three carry `status: superseded` and a matching
  `is_replaced_by`/`replaces` chain.
- `distribution_dates.release_dates` match each resource's `issued`, plus the version-2
  release timestamp.
- Per-file publication dates inside a release that post-date the release publication date
  (June 2025 images 2025-10-22; October 2025 files 2025-12-22; June 2026 images 2026-07-15)
  are recorded as such and drive each resource's `last_updated_on`.
- All 47 ORCIDs, affiliations, emails, grant numbers, MD5 checksums and DOIs were re-checked
  character by character against the corpus.

### Corrections made during Phase 3

- The HIGT4C resource description originally said the inventory was "recorded in the
  file_collections of this record"; since that slot exists only in the full schema and the
  string must be byte-identical in core, it was reworded to "recorded in the file inventory of
  this record". Applied to the full record first, then re-derived into core.
- The March 2025 statement that the SEC-MS data "will be uploaded to Pride when available" was
  found on re-reading and back-ported into `raw_data_sources[0].access_details`.
- No Phase 2 discovery required adding a fact that the full record lacked; the core record is a
  strict schema subset of the audited full record plus the `distributions` projection.

## Phase 4 — strict full/core reconciliation

Shared slots were derived at run time with LinkML `SchemaView` via
`data_sheets_schema.d4d_pair_consistency.load_pair_schema()`:

- **76 schema-identical slots**, of which 61 are populated in this pair and are deeply
  identical (same presence, same parsed YAML value, same list order, including every narrative
  string — core condenses nothing).
- **1 projected slot**: `resources` (`Dataset` in full, `CoreDataset` in core). All four
  release ids are present in both with equal coverage; every schema-identical nested slot is
  deeply identical. Full-only nested slots are omitted from the core projection as required:
  `total_file_count`, `citation`, `related_datasets`.
- **Full-only top-level slots** (no core counterpart, therefore dropped): `file_collections`
  (re-expressed as `distributions`), `citation`, `relationships`, `direct_collection`,
  `collection_consents`, `third_party_sharing`, `related_datasets`.
- **Core-only slot** `dialect` is omitted: the released material is ZIP-packaged imaging,
  mass-spectrometry and sequencing data, `is_tabular` is `false` in both records, and no
  tabular dialect is described anywhere in the corpus.

### Related-content semantic review: `file_collections` ↔ `distributions`

All ten core distributions matched a full file collection deterministically on `id`
(matches=10, unmatched=0). Reviewed field by field:

| Full `FileCollection` | Core `CoreDistribution` | Result |
|---|---|---|
| `id`, `name`, `path` | `id`, `name`, `path` | identical for all 10 |
| `compression: zip` | `compression: zip`, `format: ZIP`, `media_type: application/zip` | consistent; Dataverse lists all ten as "ZIP Archive", file type "Archive (10)" |
| MD5 in `description` | `md5` | identical checksum strings for all 10, verified against the release file table |
| displayed size in `description` | `bytes` omitted | no conflict; sizes are rounded display values only, so no byte count is asserted in either record |
| `file_count: 1` (×10) | — | consistent with `total_file_count: 10` on the HIGT4C resource and with the ten distributions |
| `issued` per file | — | core has no per-distribution date slot; dates remain in the shared `description` text |
| `collection_type` | — | core has no counterpart; modality role is carried in the shared description text |

Access URLs: the captured release page exposes no per-file download URL (only a generic Data
Access API pattern), so neither record asserts one; release-level access is carried on the
HIGT4C resource (`page`, `download_url`).

Release scope: every file collection and distribution belongs to HIGT4C only, matching the
pinned referent. Historical releases are represented as resources with their own file counts,
not as file inventories, so differing file counts across releases are version history rather
than contradictions.

Identity/version/access cross-check: no top-level identity, version or access assertion
conflicts with the resources, the version history, or the distributions in either record.
**Zero unresolved contradictions within or between the two files.**

## Commands run

```bash
poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_all.yaml \
  -C Dataset data/d4d_concatenated/claudecode_agent/2026-07-28_claude-opus-5-programme-deprimed_rep2/CM4AI_d4d.yaml
poetry run linkml-term-validator validate-data \
  data/d4d_concatenated/claudecode_agent/2026-07-28_claude-opus-5-programme-deprimed_rep2/CM4AI_d4d.yaml \
  --schema src/data_sheets_schema/schema/data_sheets_schema_all.yaml --target-class Dataset
poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml \
  -C CoreDataset data/d4d_concatenated/claudecode_agent_core/2026-07-28_claude-opus-5-programme-deprimed_rep2/CM4AI_d4d_core.yaml
poetry run linkml-term-validator validate-data \
  data/d4d_concatenated/claudecode_agent_core/2026-07-28_claude-opus-5-programme-deprimed_rep2/CM4AI_d4d_core.yaml \
  --schema src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml --target-class CoreDataset
poetry run python -m data_sheets_schema.d4d_pair_consistency \
  --full data/d4d_concatenated/claudecode_agent/2026-07-28_claude-opus-5-programme-deprimed_rep2/CM4AI_d4d.yaml \
  --core data/d4d_concatenated/claudecode_agent_core/2026-07-28_claude-opus-5-programme-deprimed_rep2/CM4AI_d4d_core.yaml --sync-core
poetry run python -m data_sheets_schema.d4d_pair_consistency \
  --full data/d4d_concatenated/claudecode_agent/2026-07-28_claude-opus-5-programme-deprimed_rep2/CM4AI_d4d.yaml \
  --core data/d4d_concatenated/claudecode_agent_core/2026-07-28_claude-opus-5-programme-deprimed_rep2/CM4AI_d4d_core.yaml
poetry run d4d provenance record --project CM4AI --method claudecode_agent \
  --label 2026-07-28_claude-opus-5-programme-deprimed_rep2 \
  --input-bundle data/preprocessed/concatenated/CM4AI_preprocessed.txt
```

## Results

| Check | Result |
|---|---|
| Full — LinkML schema validation (`Dataset`) | PASS (no issues found) |
| Full — ontology term validation | PASS |
| Core — LinkML schema validation (`CoreDataset`) | PASS (no issues found) |
| Core — ontology term validation | PASS |
| Pair consistency (after `--sync-core`) | PASS: 76 schema-identical slots; projected slots=['resources'] |
| Pair consistency (independent final run) | PASS: 76 schema-identical slots; projected slots=['resources'] |
| Validator warning | `semantic-review-required` on `$.file_collections <-> $.distributions`, matches=10, unmatched=[] — reviewed above |
| Provenance record | present, `record_mode: live` |

## Schema-shape notes (structure derived from the schemas, not from examples)

- `Creator.principal_investigator`, `EthicalReview.contact_person`,
  `LicenseAndUseTerms.contact_person`, `ExportControlRegulatoryRestrictions.governance_committee_contact`
  and `FundingMechanism.grantor` are **non-inlined** references and must be plain strings;
  `Person` objects cannot be nested, so ORCIDs are carried as `Creator.id` and emails in
  `Creator.description`.
- `Creator.affiliations` and `FundingMechanism.grants` are **inlined lists of objects** whose
  `id` is required. Organization ids use the corpus-supported ROR
  `https://ror.org/0153tk833` for the University of Virginia and local surrogate CURIEs
  (`data_sheets_schema:organization-*`) for the remaining institutions, which the corpus does
  not identify by ROR. Grant ids use `data_sheets_schema:grant-*` surrogates carrying the
  verbatim `grant_number`.
- `issued`, `created_on` and `last_updated_on` are `datetime` and reject bare dates, so
  date-only source values are written as `T00:00:00Z`; the exact source dates are additionally
  recorded verbatim in `distribution_dates.release_dates` and in descriptions.
