# CM4AI — Phase 3 / Phase 4 reconciliation

- **Version label:** `2026-08-28_claude-opus-5-claudecode-generic-v6_rep3`
- **Arm:** BASELINE (input documents only)
- **Condition:** generic_v6 — `src/download/prompts/d4d_generic_arm_prompt_v6.md`
- **Runtime / provider / model:** Claude Code · Anthropic · claude-opus-5
- **Mode:** four-phase project agent (Phases 1–4 run sequentially in one context)
- **Declared bundle:** `data/preprocessed/concatenated/CM4AI_preprocessed.txt`
  (md5 `1dfd34e5610fed7c22bea1f09c0bc60c`, 7,866 lines, 28 chunks)
- **Full record:** `data/d4d_concatenated/claudecode_agent/2026-08-28_claude-opus-5-claudecode-generic-v6_rep3/CM4AI_d4d.yaml`
- **Core record:** `data/d4d_concatenated/claudecode_agent_core/2026-08-28_claude-opus-5-claudecode-generic-v6_rep3/CM4AI_d4d_core.yaml`
- **Coverage receipt:** `data/d4d_concatenated/claudecode_agent_core/2026-08-28_claude-opus-5-claudecode-generic-v6_rep3/CM4AI_coverage_receipt.yaml`

## Referent

`Dataset` admits one referent. The manifest's `scope:` block for CM4AI declares
the referent as the CM4AI (Cell Maps for Artificial Intelligence) dataset with
`referent_id: https://cm4ai.org/`, and notes that the four Dataverse releases in
the bundle "are releases of this dataset, not separate datasets". This record
therefore takes **the CM4AI dataset as an ongoing quarterly release programme**
as its referent, with `id: https://cm4ai.org/`, and enumerates the releases as
`resources` entries keyed by their DOIs:

| `resources` index | release | DOI |
|---|---|---|
| 0 | Cell Maps for Artificial Intelligence - Data Release (cited in the preprint) | `doi:10.18130/V3/DXWOS5` |
| 1 | March 2025 Data Release (Beta) | `doi:10.18130/V3/B35XWX` |
| 2 | June 2025 Data Release (Beta) | `doi:10.18130/V3/F3TD5R` |
| 3 | October 2025 Data Release (Beta) | `doi:10.18130/V3/K7TGEM` |
| 4 | June 2026 Data Release (Beta) — current | `doi:10.18130/V3/HIGT4C` |

The referent choice is held consistently in both records: the core is a
projection of the full record and carries the same `id` and the same five
`resources` entries.

**The associated Nature study is not the referent and is not merged into it.**
The bundle's highest-volume source is *Multimodal cell maps as a foundation for
structural and functional genomics* (Nature 642, 222–231, 2025), which reports a
multiscale map of U2OS osteosarcoma cells. U2OS is not among the cell lines the
CM4AI releases interrogate (MDA-MB-468 and KOLF2.1J), and the releases state
that computed cell maps are not included in them. That study is therefore
recorded as `external_resources[1]` with its own deposits and identifiers, and
its U2OS map as a `related_datasets` entry with `relationship_type: references`
— not as CM4AI composition. Every quantity belonging to that study (5,147
proteins in both modalities, 275 assemblies, 36,842 interactions among 7,543
proteins, 2,174 tagged baits, 10,348 imaged proteins / 20,660 images, SEC-MS
over 40 fractions) sits inside that entry's `description`, not in `instances`.
`d4d download scope --check --project CM4AI` confirms the record does not
identify itself as a dataset the project declares distinct.

## Phase 1 — full generation and coverage receipt

Every one of the manifest's 28 chunks was opened with the file-reading tool in
manifest order and receipted before the next chunk was read. Statuses: 19
`extracted`; 7 `nothing_relevant` (c001 the concatenation preamble and table of
contents, c006 the Nature bibliography, c009 the nature.com site footer, c013
the tail of the preprint bibliography, and c022, c025 and c028 the Dataverse
capture tails); 2 `redundant_with` (c021 and c027, the repeated Citation
Metadata blocks of the June 2025 and June 2026 Dataverse pages, whose facts are
already receipted from c018, c020, c023, c024 and c026).

`poetry run d4d receipts check --label … --project CM4AI --strict` reports:

```
chunks 28/28 reviewed · snippets 313/313 verified · slots 724/763 with a receipt (97 exempt)
```

with **no findings**. The 39 populated leaves without a receipt are, on
inspection, all labels this record composed rather than facts it took from the
bundle: `name` on nested objects (`purposes[*].name`, `collection_mechanisms[*].name`,
`funders[0].grants[*].name`, and so on) and the organization `name` strings
inside `creators[0].affiliations`. No factual value is unreceipted.

## Phase 2 — core derivation

`d4d derive core` was run on the validated Phase 1 file; no model judgement was
involved. The command printed:

```json
{"derived": true,
 "rule": "shared slots copied from the full record; resources projected by id with full-only nested slots dropped; distributions built from file_collections (one per collection over the shared slots, total_bytes as bytes) and from each collection's File entries (one per file over the slots CoreDistribution and File share); dialect from the File entries when they agree on one value, else absent",
 "from": {"path": "data/d4d_concatenated/claudecode_agent/2026-08-28_claude-opus-5-claudecode-generic-v6_rep3/CM4AI_d4d.yaml",
          "md5": "1817823fffae4d0cc51c5e799c8f18f2"},
 "identity_slots": 79,
 "projected_slots": ["resources"],
 "distribution_slots": {"collection": ["compression", "conforms_to", "conforms_to_standard", "description", "id", "name", "notes", "path", "source_caveats"],
                        "file": ["bytes", "compression", "conforms_to", "conforms_to_standard", "description", "encoding", "format", "hash", "id", "md5", "media_type", "name", "notes", "path", "sha256", "source_caveats"]},
 "conditional": {"dialect": "derived only when every File-level dialect in the full record agrees on one value"}}
```

The md5 above is the corrected full record as re-derived in Phase 4; the Phase 2
run before the Phase 3 corrections derived from md5 `4b7dd4fc81402150ab001a9c2669c441`.

## Phase 3 — source and provenance audit

### Provenance boundary

No prior full or core D4D record was read, from any arm, label or date. Nothing
under `data/d4d_concatenated/` other than this run's own three output paths was
opened, and no `*_crate_d4d.yaml` or `*_crate_mapped_d4d.yaml` under
`data/ro-crate_packages/` was opened. The factual inputs were the declared
bundle, `data/preprocessed/source_manifest.yaml`, the chunk manifest, and the
two LinkML schemas. Structure was derived from class `Dataset` in
`data_sheets_schema_all.yaml`; no `d4d:docExample` value was copied.

### Source disagreements resolved by the declared ranking

`source_priority` for CM4AI ranks: tier 1 data resource (`october_2025_dataverse_release`,
`june_2026_dataverse_release`), tier 2 documentation and license, tier 3
publication and preprint, tier 4 NIH project page, tier 5 historical data
release.

| # | Disagreement | Sources | Resolution |
|---|---|---|---|
| 1 | Date of the June 2026 release | data releases page (tier 2): "Released on: June 17, 2025"; HIGT4C Dataverse landing page (tier 1): "Publication Date 2026-06-17" | Tier 1 preferred. `resources[4].issued: 2026-06-17T00:00:00Z`; the page's date is recorded in the record's `source_caveats` and in `distribution_dates[0].description`. |
| 2 | End of the project / of dataset augmentation | NIH RePORTER (tier 4): "Project end: 2026-08-31"; Dataverse maintenance plan (tier 5 for the June 2025 capture, tier 1 for October 2025 and June 2026): "through the end of the project in November 2026" | The two statements are about different things — the award period and the augmentation horizon — so both are stated: `collection_timeframes[0]` carries the RePORTER dates with the divergence recorded in `timeframe_details`, and `updates.update_details` carries the November 2026 horizon. |
| 3 | Number of proteins imaged | releases page (tier 2): "IF images for 523 proteins"; March 2025 release: 563; June 2025, October 2025 and June 2026 releases: 464 | Not one contested value: each figure describes a different release. Each is stated where it applies (`subsets[0].instances[0].description`, and the per-release `file_collections` descriptions), and the record's `source_caveats` says so. |

### Assertions removed or not made

- **`regulatory_restrictions.regulatory_restrictions`** held the single entry
  `"FDA Regulated: No"`. That is the answer to a Dataverse form question, not a
  regulatory restriction applicable to the dataset, and the slot's declared
  meaning is the restrictions themselves. The entry was removed from the full
  record and the fact is stated in `regulatory_restrictions.description`.
- **`credit_roles: data_curation`** on `creators[1]` and `creators[2]` was
  removed. The bundle states that the Lundberg and Krogan laboratories
  *generated* the imaging and mass-spectrometry data, which supports
  `investigation`; it says nothing about curation.
- **`funders[0].grants[0].name`** was changed from "Bridge2AI Functional
  Genomics (Cell Maps for AI)" to "Bridge2AI Functional Genomics". "Cell Maps
  for AI" is a label variant; the manifest's `naming:` block declares **CM4AI**
  as the canonical label, and the variant survives in this record only inside
  the quoted NIH RePORTER project title.
- **`total_size_bytes`** was not populated. The CM4AI pages state a data volume
  of "21.4 TB" and the Dataverse file listings give sizes only in human-readable
  units ("3.8 GB", "203.5 KB"); converting either to an integer byte count would
  require choosing decimal or binary prefixes, which the bundle does not state.
  The stated figures are carried verbatim in the record's `description` and in
  each `File.description`.
- **`is_tabular`** was not populated. The releases distribute ZIP archives of
  images and sequence data alongside JSON and HTML metadata; neither `true` nor
  `false` is supported for the dataset as a whole.
- **`doi`**, **`issued`**, **`download_url`** and **`version`** were left absent
  at the top level. The referent is a release programme, not a single deposit;
  each release carries its own DOI, issuance date and version.
- **ORCIDs of named individuals** are not written into identifier slots.
  `Creator.principal_investigator`, `EthicalReview.contact_person`,
  `LicenseAndUseTerms.contact_person` and `DataGovernance.committee_contact` are
  all declared with a string range in this schema, and the first of these
  explicitly asks for a person's name. The ORCIDs the bundle supplies are stated
  in the neighbouring `description`, `review_details` and `source_caveats`.

### Values back-ported into the full record

Both were added with their receipts, into the existing entry of the chunk the
passage sits in, and `d4d receipts check --strict` was re-run.

| Slot | Value | Chunks |
|---|---|---|
| `sampling_strategies[0]` | The targeted panel — 100 chromatin modifiers and 100 metabolic enzymes involved in cancer, neuropsychiatric and cardiac disorders, with a shared protein list across cell types and conditions, and the Year 1 spatial-proteomics plan of 100 chromatin regulators plus 500 pending proteins | c010, c016, c023 |
| `errata[0]` | The June 2025 release as captured is a revision adding RGB immunofluorescent images, correcting RO-Crate metadata and changing naming conventions | c020 |

### Internal consistency

- Per-release `total_file_count` against the `file_collections[*].file_count`
  beneath it: 6 = 1+1+3+1 (March 2025); 8 = 2+2+1+3 (October 2025); 10 =
  2+3+2+2+1 (June 2026). The June 2025 release states 21 files while its capture
  lists only the first 10; `total_file_count: 21` is the release's own figure and
  `resources[2].source_caveats` records that the inventory is partial.
- Every MD5 in the record was transcribed from the release page that states it.
  Three MD5s recur across the June 2025 and October 2025 releases
  (`0d972b80…`, `a98affcc…`, `ad4e68cc…`, the three MDA-MB-468 image archives);
  the June 2026 release states different MD5s for archives of the same names
  (`6c1a8652…`, `6d066e6b…`, `df796327…`). Both are recorded as stated.
- `instances[2].counts` (11,739 genes targeted, from the CM4AI Data Insights
  panel) equals `subsets[1].instances[0].counts` (11,739 targeted genes in the
  CRISPRi Perturbation Cell Atlas).
- `license` (`CC BY-NC-SA 4.0`) is identical at the top level and on all four
  Dataverse releases; `resources[0]` carries the same license from the
  preprint's availability statement.

### Grounding

`grounding.check_run` over the full/core pair against the bundle:

```
{'grounded': 6, 'minted_fragment': 51, 'absent': 0}
```

**No identifier is `absent`.** The six grounded identifiers are the four release
DOIs, the preprint DOI and the University of Virginia ROR, each printed verbatim
in the bundle. The 51 minted fragments are all `#`-fragments on a release DOI
naming a `FileCollection` or `File` inside that release — parts of this dataset
with no referent outside this record, whose `id` the schema requires. No fragment
is hung on an organizational identifier, and no prefix outside the schema's
declared set was invented.

**On the ROR.** `ROR:0153tk833` is used for the University of Virginia in
`publisher`, `resources[*].publisher`, `creators[0].affiliations[0].id` and
`data_governance.accountable_organization.id`. The bundle prints it in the June
2026 Dataverse author block in the position where the March 2025, June 2025 and
October 2025 captures print the string "University of Virginia" for the same
four authors. The identification is this record's reading of those two captures,
and it is stated as such in the record's `source_caveats` and in
`creators[0].affiliations[0].source_caveats`.

### Prompt condition

`src/download/prompts/d4d_generic_arm_prompt_v6.md` is the rendered condition
text this run was launched with. No project-specific factual note was added to
it; the only project-specific inputs were the declared bundle and the manifest's
`scope:`, `naming:` and `source_priority` blocks, which every project has.

## Phase 4 — re-derivation, checks, repair

1. The core was re-derived from the corrected full record with
   `--phase4-complete`, which wrote the `# Phase 4 reconciliation: completed`
   header line. `--sync-core` was not used.
2. The pair checker was run as the independent proof:
   `PASS: 79 schema-identical slots; projected slots=['resources']; per-record slots (exempt, must differ)=['conforms_to_class', 'conforms_to_schema']`.
   It emitted **no** `semantic-review-required` warning: this record's
   `file_collections` sit under `resources`, so the top-level `distributions`
   block the warning concerns is empty. The projection produced
   10 / 14 / 12 / 15 `distributions` entries under `resources[1..4]`
   (one per collection plus one per file: 4+6, 4+10, 4+8, 5+10).
3. Schema and ontology-term validation was re-run for both records after every
   correction; all four passed.
4. Neither the grounding checker nor the report-claims checker reported a
   finding that required a change to either record, so **no `repair` phase was
   performed**.
5. `d4d runs check --strict` initially reported `mismatch` for this run: the
   first `d4d provenance record` call passed the raw condition file to
   `--prompt-text`, and the render gate compares the recorded instruction
   against what `d4d prompt render` produces for the run's spec. The instruction
   was re-rendered with
   `d4d prompt render --project CM4AI --label <label> --condition generic_v6 --runtime 'Claude Code'`
   (sha256 `d6a847b314179d73239b804d87bdb566d08d1755dbc5c6b9023a6fffe80e5efe`,
   11,183 bytes) and found **byte-identical** to the instruction this agent was
   actually sent; provenance was re-recorded with that file and the run then
   passes `d4d runs check --strict` with no finding. `d4d api prompts check
   --strict` reports `canonical` for
   `src/download/prompts/d4d_generic_arm_prompt_v6.md`. This changed the
   provenance record, not either D4D record.

## Claims

| Slot | Change | Reason |
|---|---|---|
| `regulatory_restrictions.regulatory_restrictions` | **Removed** | Removed from the full record in Phase 3. Its single entry, `"FDA Regulated: No"`, was the answer to a Dataverse form question rather than a regulatory restriction applicable to the dataset; the fact is stated in `regulatory_restrictions.description` instead. |

No other slot was removed from either record.

## Semantic review

- **`file_collections` ↔ `distributions`** — the pair checker emitted no
  `semantic-review-required` warning, because the full record's
  `file_collections` are nested under `resources` and the top-level
  `distributions` block is therefore empty. The per-release projection was
  reviewed by hand instead: each release's collections and files appear once
  each in `resources[i].distributions`, in collection order with each
  collection followed by its files, and the counts match the full record
  (4+6=10, 4+10=14, 4+8=12, 5+10=15). **reviewed: consistent**
- **`total_file_count` against the entries beneath it** — 6, 8 and 10 for the
  March 2025, October 2025 and June 2026 releases each equal the sum of the
  `file_count` values of their collections. The June 2025 release declares 21
  while its capture lists 10; the release's own figure is kept and the partial
  inventory is stated in `resources[2].source_caveats`. Top-level
  `total_file_count` is deliberately absent, because summing across releases
  would double-count archives that recur between them. **reviewed: consistent**
- **`total_size_bytes` against the entries beneath it** — absent at every level.
  The bundle states sizes only in human-readable units, and `File.bytes` was
  therefore left unpopulated throughout; the stated sizes are carried in each
  `File.description`. Nothing in the record asserts a byte count that the
  entries beneath it would have to sum to. **reviewed: consistent**
- **`dialect` against the files** — no `File` in the full record carries a
  `dialect`; the bundle states none. The derivation's conditional therefore left
  `dialect` absent on every core resource, which is the correct outcome and not
  a dropped value. **reviewed: consistent**
- **`is_tabular` against the files** — not asserted, and the files support no
  single answer: the releases distribute ZIP archives of confocal images and
  sequencing data alongside JSON metadata and HTML datasheets. **reviewed:
  consistent**
- **Historical release read as the current one** — the record enumerates five
  releases and marks exactly one as current: `resources[4]`
  (`doi:10.18130/V3/HIGT4C`) is described as "The current CM4AI data release",
  `version_access.latest_version_doi` is `doi:10.18130/V3/HIGT4C`, and the
  record's `citation` is that release's citation. The March 2025, June 2025 and
  October 2025 releases carry their own dates and versions and are not presented
  as current. The manifest marks `october_2025_dataverse_release` as
  `superseded_by: june_2026_dataverse_release`, which this ordering follows.
  **reviewed: consistent**
- **Related content across the pair** — `resources` is the only projected slot.
  Every projected entry keeps its `id`, and the two slots the projection drops
  from each resource (`file_collections`, `total_file_count`) are full-only by
  schema. **reviewed: consistent**

## Files changed

| Path | Phase |
|---|---|
| `data/d4d_concatenated/claudecode_agent/2026-08-28_claude-opus-5-claudecode-generic-v6_rep3/CM4AI_d4d.yaml` | 1 (written), 3 (corrected) |
| `data/d4d_concatenated/claudecode_agent_core/2026-08-28_claude-opus-5-claudecode-generic-v6_rep3/CM4AI_coverage_receipt.yaml` | 1 (written), 3 (back-port receipts added in place) |
| `data/d4d_concatenated/claudecode_agent_core/2026-08-28_claude-opus-5-claudecode-generic-v6_rep3/CM4AI_d4d_core.yaml` | 2 (derived), 4 (re-derived) |
| `data/d4d_concatenated/claudecode_agent_core/2026-08-28_claude-opus-5-claudecode-generic-v6_rep3/CM4AI_reconciliation.md` | 4 |
| `data/d4d_concatenated/claudecode_agent_core/2026-08-28_claude-opus-5-claudecode-generic-v6_rep3/CM4AI_provenance.yaml` | 4 |

## Commands

```bash
poetry run d4d bundle chunk --check --project CM4AI
poetry run d4d download scope --project CM4AI
poetry run d4d download priority --project CM4AI
poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_all.yaml -C Dataset \
  data/d4d_concatenated/claudecode_agent/2026-08-28_claude-opus-5-claudecode-generic-v6_rep3/CM4AI_d4d.yaml
poetry run linkml-term-validator validate-data \
  data/d4d_concatenated/claudecode_agent/2026-08-28_claude-opus-5-claudecode-generic-v6_rep3/CM4AI_d4d.yaml \
  --schema src/data_sheets_schema/schema/data_sheets_schema_all.yaml --target-class Dataset
poetry run d4d receipts check --label 2026-08-28_claude-opus-5-claudecode-generic-v6_rep3 --project CM4AI --strict
poetry run d4d derive core \
  --full data/d4d_concatenated/claudecode_agent/2026-08-28_claude-opus-5-claudecode-generic-v6_rep3/CM4AI_d4d.yaml \
  --out  data/d4d_concatenated/claudecode_agent_core/2026-08-28_claude-opus-5-claudecode-generic-v6_rep3/CM4AI_d4d_core.yaml
poetry run d4d download scope --check --project CM4AI
# Phase 4
poetry run d4d derive core --full <full> --out <core> --phase4-complete
poetry run python -m data_sheets_schema.d4d_pair_consistency --full <full> --core <core>
poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml -C CoreDataset <core>
poetry run linkml-term-validator validate-data <core> \
  --schema src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml --target-class CoreDataset
# grounding and report-claims checkers (see Phase 4 above)
poetry run d4d provenance record --project CM4AI --method claudecode_agent \
  --label 2026-08-28_claude-opus-5-claudecode-generic-v6_rep3 \
  --input-bundle data/preprocessed/concatenated/CM4AI_preprocessed.txt \
  --condition generic_v6 --runtime 'Claude Code' --provider Anthropic --receipt-expected \
  --prompt src/download/prompts/d4d_generic_arm_prompt_v6.md \
  --prompt-text <the file d4d prompt render wrote> \
  --phase '{"name":"generate_full",...}' --phase '{"name":"derive_core",...}' \
  --phase '{"name":"source_audit",...}' --phase '{"name":"reconcile",...}' \
  --phase '{"name":"report",...}'
poetry run d4d prompt render --project CM4AI --label <label> --condition generic_v6 \
  --runtime 'Claude Code' --out <rendered>
poetry run d4d receipts check --label <label> --project CM4AI --strict --write
poetry run d4d runs validate --project CM4AI --method claudecode_agent --label <label>
poetry run d4d runs check --strict
```

## Final results

| Check | Result |
|---|---|
| `linkml-validate` full (`Dataset`) | **pass** |
| `linkml-term-validator` full | **pass** |
| `linkml-validate` core (`CoreDataset`) | **pass** |
| `linkml-term-validator` core | **pass** |
| `d4d_pair_consistency` | **PASS** — 79 schema-identical slots, 0 errors, 0 warnings |
| `d4d receipts check --strict` | **pass** — 28/28 chunks, 313/313 snippets verified, 0 findings |
| `grounding.check_run` | 6 grounded, 51 minted_fragment, **0 absent** |
| `report_claims.check_report` | 0 findings (1 claim checked, 0 unnamed) |
| `d4d runs check --strict` | no finding for this run |
| `d4d api prompts check --strict` | `canonical` for the v6 condition file |
| `d4d download scope --check` | in scope |

Informational, never a quality gate: the full record is 1,775 lines with 59
populated top-level slots and 860 populated leaves; the core record is 1,280
lines with 55 populated top-level slots and 718 populated leaves.
