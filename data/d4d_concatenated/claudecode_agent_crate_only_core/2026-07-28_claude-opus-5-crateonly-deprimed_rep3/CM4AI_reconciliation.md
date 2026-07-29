# CM4AI full/core reconciliation — 2026-07-28_claude-opus-5-crateonly-deprimed_rep3

Arm: CRATE-ONLY (RO-Crate evidence alone; document corpus withheld)
Mode: four-phase project agent, de-primed, pinned referent
Pinned referent: the CM4AI data-release programme as an ongoing quarterly release series
Runtime: Claude Code / Anthropic / claude-opus-5[1m], temperature 0.0

## Files

- Full: `data/d4d_concatenated/claudecode_agent_crate_only/2026-07-28_claude-opus-5-crateonly-deprimed_rep3/CM4AI_d4d.yaml`
- Core: `data/d4d_concatenated/claudecode_agent_crate_only_core/2026-07-28_claude-opus-5-crateonly-deprimed_rep3/CM4AI_d4d_core.yaml`

## Declared inputs actually read

Factual inputs:

- `data/preprocessed/concatenated/CM4AI_crate_only.txt` (whole file, 2,208 lines)

Structural inputs:

- `src/data_sheets_schema/schema/data_sheets_schema_all.yaml` (class `Dataset`, resolved via `SchemaView`)
- `src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml` (class `CoreDataset`, resolved via `SchemaView`)

Procedural inputs: `.claude/agents/d4d-provenance-guard.md`, `.claude/commands/d4d-full-core.md`,
`.claude/commands/d4d-agent.md`.

Not read: `data/preprocessed/source_manifest.yaml` and the document corpus (withheld by the arm);
any prior generated D4D record from any arm, label, or date; any `*_crate_d4d.yaml` or
`*_crate_mapped_d4d.yaml`; any evaluation or reconciliation report from an earlier run. Output
directory names were listed once, to confirm the target label directory did not already exist.

## Phase 3 — source and provenance audit

### Provenance result

Clean. No prior generated D4D, evaluation artifact, or report entered the context. Every populated
slot traces to the declared bundle; every emitted structure was derived from the LinkML schemas at
run time rather than from any example record.

### Scoping decisions forced by the pinned referent

The bundle's root object is one release (June 2026, DOI 10.18130/V3/HIGT4C). The record's referent
is the programme. That forces three placements, applied consistently:

1. Top-level `id` is the crate's own project entity ARK
   (`.../project-cell-maps-for-artificial-intelligence-qTdsTBd3FtA`), not the release ARK.
2. Release-scoped identity facts (release DOI, release version `1.0`, release publication date,
   release status) sit on the June 2026 entry in `resources`, not at top level. The release DOI is
   additionally reachable at programme level through `version_access.latest_version_doi`, which is
   the slot the schema provides for exactly that.
3. `total_file_count` (53,877) and `total_size_bytes` (21,051,331,945,400) appear at top level as
   well as on the release resource. Justification from the bundle, not assumption: seven of the
   nine component crates declare `isPartOf` two or more successive releases, so releases are
   cumulative supersets, and the current release's holdings are the programme's holdings to date.

`file_collections` describes the current release, as pinned: all nine component crates in the
bundle declare membership in the June 2026 release.

### Source-internal contradictions found (recorded, not resolved)

The bundle does not contain enough evidence to adjudicate any of these. Each is documented inside
the records rather than silently resolved.

1. **Two DOIs for one named release.** Component crates retain citation blocks naming the "March
   2025 Data Release (Beta)". Six crates (three IF, SEC-MS treated cancer cells, perturb-seq raw
   sequence, perturb-seq cell atlas) cite DOI `10.18130/V3/B35XWX`; three crates (both AP-MS,
   SEC-MS KOLF2 differentiation) cite DOI `10.18130/V3/K7TGEM` for the identically titled release.
   Recorded in the March 2025 `resources` entry and in `version_access.versions_available`.
2. **Stale citations inside components.** Every component crate's `citation` names the March 2025
   release, not the release the component declares itself part of. Recorded in
   `version_access.version_details`; citation text inside components was therefore not used as a
   release-identity source.
3. **Two project entity identifiers.** The release root declares `isPartOf`
   `project-cell-maps-for-artificial-intelligence-qTdsTBd3FtA` and
   `organization-university-of-california-san-diego-T4a649a1RtE`; four component crates declare
   `project-cm4ai` and `organization-university-of-california-san-diego`. The record uses the
   root-level pair and does not assert the two project ARKs are the same entity.
4. **Author list vs citation string.** The structured `author` array holds 47 entries, matching
   the AI-readiness assessment's "47 authors". The root `citation` string additionally names
   "Park, S" and "Zhao, X" and omits "Marquez C" (who is in the author array and has a person
   record). `creators` follows the structured array; the two citation-only names were not promoted
   to creators.
5. **Size figures disagree.** Root `contentSize` is "19.9 TB"; `evi:totalContentSizeBytes` is
   21,051,331,945,400 bytes, which is 21.05 TB decimal or 19.15 TiB. Neither unit convention
   reconciles the two. "19.9 TB" does equal the decimal sum of the nine component `contentSize`
   labels (~19.88 TB), so the human-readable figure appears to be a label sum and the byte count
   an independent total. The record uses the exact byte count and never asserts "19.9 TB".
6. **Entity counts do not close.** Component `hasPart`/output data-entity counts sum to 53,697
   against the release-level `evi:datasetCount` of 53,877 — 180 entities unaccounted for. Both
   figures are recorded as given (per-collection `file_count`, top-level `total_file_count`); no
   figure was adjusted to force closure.
7. **Malformed identifier.** The SEC-MS treated cancer cell crate gives its identifier as
   `https://doi.org/doi:10.25345/C5348GV4S`. The DOI proper (`10.25345/C5348GV4S`) was recorded
   and the malformed source form noted in the same description.
8. **Empty manifest with populated provenance graph.** The perturb-seq raw sequence crate has
   `hasPart: []` yet records 192 sample inputs and 103 dataset outputs. `file_count` was taken
   from the outputs and the discrepancy stated in the description.
9. **Modality list disagreement.** The release records four collection types (Perturb-seq; IF
   imaging; SEC-MS; AP-MS). Only the SEC-MS KOLF2 differentiation crate repeats the four-modality
   list; the other seven, *including both AP-MS crates*, record a three-modality list omitting
   AP-MS. Corrected during this phase — a first-pass draft had asserted that no component listed
   AP-MS.
10. **Timeframe disagreement.** The release records collection 9/1/2022–6/1/2026. Only the SEC-MS
    KOLF2 differentiation crate matches; AP-MS, SEC-MS treated cancer cells and the cell atlas
    record 1/31/2026, and the three IF crates and raw sequence crate record 10/13/25. Recorded in
    `collection_timeframes.timeframe_details`; corrected in this phase to name the matching crate.
11. **Name spellings vary within the source.** "Ravistky" in `ethicalReview` vs "Ravitsky" in the
    person record; "Ballllosera Navarro F" in IF author lists vs "Ballllosero Navarro, F" in the
    person record; "Idkeker T" in the raw sequence crate's author list vs "Ideker T" elsewhere.
    Each was transcribed as it appears in the field being quoted, with the divergence noted where
    it affects a named contact.
12. **Publication metadata mismatch.** The second associated publication gives bioRxiv number
    2024.05.21.589311 with DOI 10.1101/2024.11.03.621734. Noted in `existing_uses.description`.

### Corrections applied during Phase 3

Two assertions in the Phase 1 draft were wrong against the bundle and were fixed in the full
record, then propagated to core by regeneration:

- `collection_mechanisms`: claimed all component crates omit AP-MS from their modality list. The
  SEC-MS KOLF2 differentiation crate does list AP-MS.
- `collection_timeframes`: did not state that the SEC-MS KOLF2 differentiation crate carries the
  release-level timeframe.

One structural correction was applied after schema validation: `principal_investigator`,
`contact_person` (×3) are `Person`-ranged slots that LinkML treats as identifier references, not
inlined objects. The nested person objects were replaced with ORCID references and the email and
affiliation detail moved into adjacent narrative slots, so no fact was lost.

### Evidence deliberately not asserted

- Structured `Organization` affiliations for the 38 creators with person records. The schema
  requires `Organization.id`; the bundle supplies organization names only. Affiliations were
  carried as creator `description` text rather than inventing organization identifiers.
- `Grantor` objects. Grant numbers are real identifiers and were used as `Grant.id`; funder names
  are not identifiers, so funders are named on `FundingMechanism` without a nested `Grantor`.
- `governance_committee_contact`. The bundle names "Jilian Parker" with no identifier. Matching
  that to author "Parker, J" (ORCID 0000-0003-4535-3486) would be an inference, so the name is
  recorded as text in `regulatory_restrictions` and the slot left empty.
- Per-distribution byte counts. Component sizes appear only as human-readable strings ("441.2
  GB", "16.7TB"). Converting them would fabricate both precision and a unit convention, so the
  strings are quoted in descriptions and `bytes` is left absent.
- `format` / `media_type` on core distributions. The release's formats (`.d`, `.d directory
  group`, `fastq.gz`, `h5`, `h5ad`, `image/jpeg`) have no faithful member in `FormatEnum` or
  `MediaTypeEnum`; the full format inventory is instead quoted verbatim in `distribution_formats`.
- `splits`, `variables`, `content_warnings`, `cleaning_strategies`, `labeling_strategies`,
  `imputation_protocols`, `annotation_analyses`, `machine_annotation_tools`, `errata`,
  `extension_mechanism`, `data_protection_impacts`, `use_repository`, `participant_privacy`,
  `participant_compensation`, `collection_notifications`, `collection_consents`,
  `consent_revocations`, `subsets`, `parent_datasets`: no support in the bundle, left absent.

### Assessment of the evidence itself

The crate is strong on identity, licensing, ethics posture, governance, funding, use terms,
maintenance plan, and provenance topology — the `rai:*` and `d4d:*` fields carry ready-made
answers to a large share of D4D's Motivation, Uses, Distribution, Maintenance and Ethics
questions, and the FAIRSCAPE graph supplies real per-component structure. It is weak on three
axes. First, verifiability: 8 of 55,859 entities carry checksums. Second, composition detail: no
variable-level or schema-level description reaches the record even though 20 schemas are declared,
and the collapsed `hasPart` inventories mean instance counts had to be read off provenance-graph
output counts. Third, internal consistency: the twelve contradictions above are almost all
artifacts of component crates being carried forward across releases without their release-scoped
fields being refreshed. The `rai:*` block is also near-verbatim duplicated into all nine
components, so its apparent redundancy is not independent corroboration.

## Phase 4 — strict full/core reconciliation

Shared slots derived at run time from `Dataset` and `CoreDataset` via `SchemaView`; no hand-written
field list was used.

- Shared slots: **77**
- Schema-identical (same induced range and cardinality): **76** — all deeply identical, identical
  presence, no condensation or paraphrase in core
- Projected (shared name, different range): **1** — `resources` (`Dataset` in full, `CoreDataset`
  in core)

Validator result, run without `--sync-core`:

```
PASS: 76 schema-identical slots; projected slots=['resources']
WARNING [semantic-review-required] $.file_collections <-> $.distributions: deterministic matches=9, unmatched core distributions=[]
```

`--sync-core` was not needed and was not run: core was generated by copying the Phase 3-audited
full record's shared slots verbatim, so the pair was identical on first check.

### Projected slot: `resources`

Four release entries, matched by `id`, equal coverage in both records. Every core-permitted key is
byte-identical to the full value. Full-only nested keys, omitted from the core projection because
`CoreDataset` does not declare them: `total_file_count`, `total_size_bytes` on the June 2026 entry.
No other resource carried a full-only key.

### Related-content review: `file_collections` ↔ `distributions`

Nine collections, nine distributions, matched by `id`, no unmatched entries on either side.
Reviewed dimensions:

- **Names, descriptions, paths**: verified programmatically identical across all nine.
- **Checksums**: `FileCollection` has no checksum slot, `CoreDistribution` has `md5`. The six
  crates that publish an MD5 carry it in `core.distributions[].md5` and in the shared description
  text of both records; verified each core `md5` string appears verbatim in the corresponding full
  description, and that no full description claims an MD5 the core omits. The three crates without
  a source MD5 (both AP-MS, SEC-MS KOLF2 differentiation) have neither.
- **Byte counts**: neither record asserts a numeric size per distribution; both carry the source's
  human-readable size in the shared description. No conflict.
- **Formats and compression**: no per-distribution format or compression is asserted in either
  record; the release-wide format inventory lives in the shared `distribution_formats`. No
  conflict.
- **Access URLs and licences**: full-only (`FileCollection.download_url`, `.license`,
  `.publisher`, `.version`, `.created_by`, `.keywords`, `.collection_type`, `.file_count`);
  `CoreDistribution` declares none of these, so their absence from core is schema-mandated, not
  omission.
- **Release scope**: all nine belong to the June 2026 release in both records; no historical
  component is mixed into the current-release scope.

### Cross-field consistency

- `total_file_count` (53,877, full only) vs summed `file_collections[].file_count` (53,697): a
  180-entity source gap, documented above and inside the record. Not a full/core divergence —
  `CoreDataset` declares neither slot.
- `is_tabular`: `false` in both, identical.
- `dialect`: absent from core (no evidence); `Dataset` declares no counterpart. No conflict.
- Identity, version and access facts at top level agree with the June 2026 `resources` entry,
  `version_access`, `distribution_dates` and `license_and_use_terms` in both records; the historical
  releases are labelled as historical and are not treated as contradicting the current release.

### Full-only top-level slots (all absent from `CoreDataset` by schema)

`citation`, `direct_collection`, `file_collections`, `related_datasets`, `relationships`,
`third_party_sharing`, `total_file_count`, `total_size_bytes`.

## Commands run

```bash
poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_all.yaml \
  -C Dataset data/d4d_concatenated/claudecode_agent_crate_only/2026-07-28_claude-opus-5-crateonly-deprimed_rep3/CM4AI_d4d.yaml

poetry run linkml-term-validator validate-data \
  data/d4d_concatenated/claudecode_agent_crate_only/2026-07-28_claude-opus-5-crateonly-deprimed_rep3/CM4AI_d4d.yaml \
  --schema src/data_sheets_schema/schema/data_sheets_schema_all.yaml --target-class Dataset

poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml \
  -C CoreDataset data/d4d_concatenated/claudecode_agent_crate_only_core/2026-07-28_claude-opus-5-crateonly-deprimed_rep3/CM4AI_d4d_core.yaml

poetry run linkml-term-validator validate-data \
  data/d4d_concatenated/claudecode_agent_crate_only_core/2026-07-28_claude-opus-5-crateonly-deprimed_rep3/CM4AI_d4d_core.yaml \
  --schema src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml --target-class CoreDataset

poetry run python -m data_sheets_schema.d4d_pair_consistency \
  --full  data/d4d_concatenated/claudecode_agent_crate_only/2026-07-28_claude-opus-5-crateonly-deprimed_rep3/CM4AI_d4d.yaml \
  --core  data/d4d_concatenated/claudecode_agent_crate_only_core/2026-07-28_claude-opus-5-crateonly-deprimed_rep3/CM4AI_d4d_core.yaml

poetry run d4d provenance record --project CM4AI --method claudecode_agent_crate_only \
  --label 2026-07-28_claude-opus-5-crateonly-deprimed_rep3 \
  --input-bundle data/preprocessed/concatenated/CM4AI_crate_only.txt
```

## Final results

| Item | Result |
|---|---|
| Full schema validation | pass |
| Full ontology term validation | pass |
| Core schema validation | pass |
| Core ontology term validation | pass |
| Schema-derived pair consistency | PASS (76 identical, 1 projected) |
| Full top-level slots | 60 |
| Core top-level slots | 53 |
| Component distributions reviewed | 9 of 9, 0 unresolved contradictions |
| Prior-D4D reuse | none |

Full/core divergence: none. Every schema-identical slot is deeply identical and identically
present; the single projected slot and the one related-content mapping were reviewed by hand and
by script with zero unresolved contradictions. All twelve inconsistencies listed above are
properties of the source crate, not of the pair, and are recorded inside the records rather than
resolved away.
