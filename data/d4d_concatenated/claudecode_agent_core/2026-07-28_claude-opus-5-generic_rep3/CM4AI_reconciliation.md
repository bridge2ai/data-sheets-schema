# CM4AI full/core reconciliation — 2026-07-28_claude-opus-5-generic_rep3

- Project: CM4AI
- Arm: BASELINE (input documents only)
- Method: claudecode_agent
- Runtime: Claude Code / Anthropic / claude-opus-5[1m], temperature 0.0
- Prompt: `src/download/prompts/d4d_generic_arm_prompt.md` (identical text for all projects)
- Declared input bundle: `data/preprocessed/concatenated/CM4AI_preprocessed.txt`
- Source manifest: `data/preprocessed/source_manifest.yaml`
- Full: `data/d4d_concatenated/claudecode_agent/2026-07-28_claude-opus-5-generic_rep3/CM4AI_d4d.yaml`
- Core: `data/d4d_concatenated/claudecode_agent_core/2026-07-28_claude-opus-5-generic_rep3/CM4AI_d4d_core.yaml`

## Phase 3 — source and provenance audit

### Provenance boundary

No prior generated D4D record was read, opened, grepped, or consulted. Nothing under
`data/d4d_concatenated/`, `data/d4d_individual/`, or `data/ro-crate_packages/` was
opened at any point. The only factual inputs were the declared bundle and the source
manifest; structure came exclusively from the two LinkML schemas resolved at runtime
with `SchemaView`. Output directory names were listed once, before generation, solely
to confirm that the label `2026-07-28_claude-opus-5-generic_rep3` did not already
exist; no file contents were read.

### Referent selection

`Dataset` admits one referent. The declared bundle documents, in order of weight: four
captured University of Virginia Dataverse release records (March 2025 B35XWX, June 2025
F3TD5R, October 2025 K7TGEM, June 2026 HIGT4C), the CM4AI data-releases page, the CM4AI
portal, the NIH RePORTER project record, the CM4AI project preprint, the CC BY-NC-SA 4.0
deed, and one unrelated research article.

The referent chosen is **the CM4AI data release programme** — the ongoing quarterly
release series deposited in LibraData — with the individual releases enumerated as
`resources`. This is the entity the bundle describes as a whole: no single release
accounts for the majority of the evidence, and the release-level facts (DOIs, versions,
file inventories, checksums) are exactly what `resources` exists to carry. The same
referent is held consistently in the core record.

### Source disagreements, represented rather than resolved away

1. **Release date of the current release.** The CM4AI data-releases page labels
   `doi.org/10.18130/V3/HIGT4C` the "June 2026 Data Release (Beta)" but displays
   "Released on: June 17, 2025", while the Dataverse record for the same DOI gives
   Publication Date 2026-06-17. Both statements are recorded (`anomalies`, `errata`,
   `distribution_dates`); neither was silently selected.
2. **Author affiliations.** Andrej Sali is listed at University of California San Diego
   in the Dataverse release metadata and at University of California San Francisco in
   the project preprint. The dataset's own authorship record (Dataverse) is used for
   `creators`, and the divergence is stated in that creator's description. The same
   treatment is applied to Vardit Ravitsky, whose release affiliation is University of
   Montreal while the ethical-review contact email is at The Hastings Center.
3. **Collaborator list.** The data-releases page names UCSD, UCSF, Stanford, UVA, Yale,
   UT Austin, UA Birmingham, Simon Fraser University and the Hastings Center; the
   March 2025 release description omits UT Austin; the preprint and release author
   affiliations add KTH, University of Alabama and University of Montreal. The union is
   recorded on the project-level creator with the provenance of each stated in prose.
4. **IF image protein coverage.** The March 2025 release states 563 proteins of interest
   per condition; the June 2025, October 2025 and June 2026 releases state 464. Both
   figures are recorded, each scoped to its release, in `instances` and
   `sampling_strategies`.
5. **Name variant.** The person recorded as "Parker J" / Jillian Parker in the Dataverse
   releases appears as "Jillian Mohan" in the project preprint author list. Both names
   are stated in that creator's description; they were not merged into a single claim.

### Distinct entities kept distinct

The largest document in the bundle is Schaffer et al., *Nature* 642:222-231 (2025),
"Multimodal cell maps as a foundation for structural and functional genomics", a study
of a U2OS osteosarcoma cell map built from AP-MS and immunofluorescence data for more
than 5,100 proteins. Its acknowledgements name the Bridge2AI Program (NIH Common Fund;
OT2 OD032742) among its funders, which links it to CM4AI, but it is **not** a CM4AI data
release: different cell line, different measurements, separate data deposits
(NDEx, MassIVE MSV000097168, ProteomeXchange PXD052362, ModelArchive ma-idk-u2osmap and
ma-m5og4, Complex Portal CLO:0009454). None of its counts, cell-line facts, methods
parameters, or composition statements were folded into the CM4AI record. It is recorded
as one clearly labelled `external_resources` entry that states in its description why it
is separate. This is the application of the uniform rule "Do not merge distinct entities
into a single claim."

### Corrections made during Phase 3, back-ported to full first

Two source-supported facts present in the bundle were absent from the initial Phase 1
draft. Both were added to the full record and the core record was then re-derived from
the corrected full record:

1. The project-level "Data Insights" figures published on both cm4ai.org and the CM4AI
   data-releases page — 1,374 protein interactions, 53,788 immunofluorescent images,
   7,023 total proteins investigated, 11,739 genes targeted, 21.4 TB data volume — added
   to the top-level `description`.
2. The Schaffer et al. 2025 study and its associated identifiers and tooling
   (Multiscale Integrated Cell portal, Cell Mapping Toolkit, NDEx, MassIVE,
   ProteomeXchange, ModelArchive, Complex Portal, HPA v23), added as a distinct
   `external_resources` entry with an explicit non-merger statement.

No fact was removed. No value was changed.

### Deliberate omissions

Preferring omission over inference, the following were left unpopulated because the
bundle does not support them: `total_size_bytes` and `CoreDistribution.bytes` (the
Dataverse pages give human-readable sizes such as "3.8 GB"; converting to a byte count
would be a guess); `issued` / `created_on` on the programme and on most releases (the
bundle gives dates, not datetimes — the one exception, HIGT4C `last_updated_on`
`2026-07-15T20:28:19Z`, is stated exactly in the manifest curation note carried in the
bundle header); `is_tabular` and `dialect`; `content_warnings`; `variables`;
`imputation_protocols`; `annotation_analyses`; `participant_compensation`;
`consent_revocations`; `collection_notifications`; `splits`; `extension_mechanism`; and
`hipaa_compliant`, since HIPAA is never mentioned in any source.

The June 2025 release file table is captured as "1 to 10 of 21 Files". The ten
enumerated files are recorded individually; the remaining eleven are recorded as one
explicitly labelled placeholder collection with `file_count: 11`, so that
`total_file_count: 21` reconciles without inventing filenames or checksums.

### Internal consistency checks

- Every DOI appears in exactly one form per role: `https://doi.org/…` for `id`,
  `download_url` and `related_datasets` targets; `doi:…` for the `doi` slot.
- Release `total_file_count` equals the number of enumerated `file_collections` for
  HIGT4C (10), K7TGEM (8) and B35XWX (6), and equals 10 enumerated + 11 placeholder = 21
  for F3TD5R.
- MD5 checksums are unchanged from the source text in all 34 recorded file entries that have one (35 file entries total; the June 2025 placeholder collection has no checksum in the bundle).
  Where the same archive appears in two releases with the same checksum (the three
  MDA-MB-468 IF image ZIPs shared by F3TD5R and K7TGEM), the identical checksum is
  reproduced rather than deduplicated; the June 2026 release carries different checksums
  for the same filenames, which is recorded as-is.
- The license is stated identically (CC BY-NC-SA 4.0) at programme level and on every
  release, matching all four Dataverse records and the preprint.
- Governance facts (Human Subjects: No; De-identified Samples: Yes; FDA Regulated: No)
  are stated once each in `regulatory_restrictions`, `human_subject_research` and
  `is_deidentified` without contradiction.
- Historical scope is explicit throughout: archived releases are labelled as such and
  carry `is_replaced_by` links, and the current release carries `replaces`.

### Validation, Phase 3

```
poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_all.yaml -C Dataset data/d4d_concatenated/claudecode_agent/2026-07-28_claude-opus-5-generic_rep3/CM4AI_d4d.yaml
poetry run linkml-term-validator validate-data data/d4d_concatenated/claudecode_agent/2026-07-28_claude-opus-5-generic_rep3/CM4AI_d4d.yaml --schema src/data_sheets_schema/schema/data_sheets_schema_all.yaml --target-class Dataset
poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml -C CoreDataset data/d4d_concatenated/claudecode_agent_core/2026-07-28_claude-opus-5-generic_rep3/CM4AI_d4d_core.yaml
poetry run linkml-term-validator validate-data data/d4d_concatenated/claudecode_agent_core/2026-07-28_claude-opus-5-generic_rep3/CM4AI_d4d_core.yaml --schema src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml --target-class CoreDataset
```

All four: `No issues found` / `✅ Validation passed`.

## Phase 4 — strict full/core reconciliation

### Shared-slot derivation

Shared slots were derived at runtime from `Dataset` (in `data_sheets_schema_all.yaml`)
and `CoreDataset` (in `data_sheets_schema_core_all.yaml`) using LinkML `SchemaView`. No
hand-written field list was used. `CoreDataset` induces 79 slots; the schema-derived
validator reports **76 schema-identical slots** plus one projected slot, `resources`.

The core record was produced by projecting the Phase 3-audited full record onto that
derived slot set, so schema-identical slots are byte-identical parsed values by
construction, including every narrative field. Nothing was condensed, paraphrased,
reordered, or dropped to make core shorter.

### Presence

Full carries 69 top-level slots, core 61. The eight full-only slots are exactly those
`CoreDataset` does not declare:

`citation`, `collection_consents`, `direct_collection`, `participant_privacy`,
`related_datasets`, `relationships`, `subsets`, `third_party_sharing`.

There are no core-only top-level slots. Every slot present in both is present in both,
never one and not the other.

### Projected slot: `resources`

`resources` is `Dataset` in full and `CoreDataset` in core. Coverage is equal: five
release resources in each, matched by `id`:

| id | full `file_collections` | core `distributions` |
|---|---|---|
| `https://doi.org/10.18130/V3/HIGT4C` | 10 | 10 |
| `https://doi.org/10.18130/V3/K7TGEM` | 8 | 8 |
| `https://doi.org/10.18130/V3/F3TD5R` | 11 | 11 |
| `https://doi.org/10.18130/V3/B35XWX` | 6 | 6 |
| `https://doi.org/10.18130/V3/DXWOS5` | 0 | 0 |

For every nested slot that is schema-identical between `Dataset` and `CoreDataset`
(`id`, `name`, `title`, `doi`, `version`, `license`, `publisher`, `download_url`,
`last_updated_on`, `status`, `description`, `compression`), the values are deeply
identical. Three nested full-only slots are omitted from the core projection because
`CoreDataset` does not declare them: `file_collections` (projected, see below),
`total_file_count`, and `related_datasets`.

### Related, non-identical representations — semantic review

**`file_collections` → `distributions`.** `FileCollection` and `CoreDistribution` are
different classes, so this mapping was reviewed rather than copied. Each
`FileCollection` maps to exactly one `CoreDistribution`, matched by `id`:

- `id`, `name`, `path`, `description`, `compression` carry across unchanged and were
  compared value-by-value; no contradiction.
- `md5` is populated in core from the checksum stated verbatim in the corresponding
  full-record description. 34 of the 35 distributions carry a checksum; all 34 were
  re-read against the file description text and every one matches. The one distribution
  without an `md5` is the June 2025 placeholder for the eleven files the captured page
  does not enumerate, for which no checksum exists in the bundle. Core therefore expresses structurally what full expresses in
  prose — an enrichment, not a divergence.
- `format` and `media_type` are core-only enum fields with no `FileCollection`
  counterpart. They were assigned from the file-type label the Dataverse page itself
  prints for each file: "ZIP Archive" → `ZIP` / `application/zip`, "JSON" and "RO-Crate
  metadata" → `JSON` / `application/json`, "HTML" → `HTML` / `text/html`. No file was
  assigned a format the source does not state.
- `collection_type` and `file_count` are full-only and are omitted from the projection.
- `bytes`, `hash`, `sha256`, `encoding` are left unpopulated: the sources give only
  human-readable sizes and MD5 digests.

**Scope comparisons.** `total_file_count` exists only in full and so has no core
counterpart to contradict. Within full it was checked against the enumerated
collections per release and agrees for all four captured releases. `total_size_bytes` is
absent from both records, so there is no scope mismatch to reconcile.

**Format and tabularity.** `is_tabular` and `dialect` are absent from both records. The
releases are archives of images, mass-spectrometry outputs, sequence bundles and
metadata documents; the sources make no tabular-structure claim, so neither record
asserts one. `compression` is `zip` at release level in both records wherever the source
labels the files ZIP archives, and agrees with the per-distribution `compression` values.

**Identity, version and access facts.** Programme-level `license`, `publisher`, `page`,
`status`, `language` and `keywords` were compared against the release-level values, the
`version_access` block, `distribution_dates`, `distribution_formats` and the repeated
statements inside `license_and_use_terms`, `ip_restrictions` and
`regulatory_restrictions`. All agree. `version_access.latest_version_doi`
(`https://doi.org/10.18130/V3/HIGT4C`) matches the resource the data-releases page names
as current and matches the `replaces` link on that resource.

**Historical versus current release.** The differing file inventories, checksums and
protein counts across B35XWX, F3TD5R, K7TGEM and HIGT4C are successive quarterly
releases, not contradictions. Each is scoped to its own resource, each archived release
carries `is_replaced_by` and the current release carries `replaces`, and the differing
IF-image protein counts (563 in March 2025, 464 thereafter) are attributed to their
respective releases in `instances` and `sampling_strategies`.

### Validator runs

```
poetry run python -m data_sheets_schema.d4d_pair_consistency \
  --full data/d4d_concatenated/claudecode_agent/2026-07-28_claude-opus-5-generic_rep3/CM4AI_d4d.yaml \
  --core data/d4d_concatenated/claudecode_agent_core/2026-07-28_claude-opus-5-generic_rep3/CM4AI_d4d_core.yaml \
  --sync-core
→ PASS: 76 schema-identical slots; projected slots=['resources']

poetry run python -m data_sheets_schema.d4d_pair_consistency \
  --full data/d4d_concatenated/claudecode_agent/2026-07-28_claude-opus-5-generic_rep3/CM4AI_d4d.yaml \
  --core data/d4d_concatenated/claudecode_agent_core/2026-07-28_claude-opus-5-generic_rep3/CM4AI_d4d_core.yaml
→ PASS: 76 schema-identical slots; projected slots=['resources']
```

The `--sync-core` pass made no changes; the independent pass that followed it reports
the same result. The validator emitted no warnings, and the related-content review in
the section above was performed on its own terms rather than inferred from the validator
result.

### Files changed in Phase 3 / Phase 4

- `CM4AI_d4d.yaml` — two Phase 3 additions (portal Data Insights figures in
  `description`; Schaffer et al. 2025 as a distinct `external_resources` entry).
- `CM4AI_d4d_core.yaml` — regenerated in full from the corrected full record after
  those additions.
- No other file was modified.

## Outcome

Nothing diverged. The pair is consistent: all 76 schema-identical slots hold deeply
identical parsed values with identical presence, the single projected slot `resources`
has equal coverage and deep identity on every schema-identical nested slot, and the one
related-but-non-identical representation (`file_collections` → `distributions`) was
mapped and reviewed field by field with zero unresolved contradictions.

| Check | Result |
|---|---|
| Full schema validation | pass |
| Full ontology-term validation | pass |
| Core schema validation | pass |
| Core ontology-term validation | pass |
| Schema-derived pair consistency (76 shared slots) | pass |
| Prior-D4D reuse | none |
| Phase 3 corrections | 2 additions, back-ported to full first |
| Unresolved contradictions | 0 |

Line counts, recorded as informational metadata only and not as a quality gate:
full 2,632 lines; core 1,845 lines.
