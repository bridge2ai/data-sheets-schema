# CM4AI full/core reconciliation — 2026-07-28_claude-opus-5-generic_rep2

Arm: BASELINE (input documents only)
Prompt: `src/download/prompts/d4d_generic_arm_prompt.md` (identical text for all projects)
Runtime: Claude Code · Provider: Anthropic · Model: claude-opus-5[1m] · Temperature 0.0
Mode: four-phase project agent

Files:

- Full: `data/d4d_concatenated/claudecode_agent/2026-07-28_claude-opus-5-generic_rep2/CM4AI_d4d.yaml`
- Core: `data/d4d_concatenated/claudecode_agent_core/2026-07-28_claude-opus-5-generic_rep2/CM4AI_d4d_core.yaml`

Declared input bundle (only source of dataset facts):
`data/preprocessed/concatenated/CM4AI_preprocessed.txt` (10 documents, 7,873 lines).

---

## Referent choice

`Dataset` admits one referent. The bundle was read as describing, most directly and in
most detail, **the CM4AI data release series published as a collection in the University
of Virginia Dataverse (LibraData)**. Four of the ten bundle documents are Dataverse
release pages, each with its own DOI, file inventory, checksums, version metadata,
governance block and limitations block; a fifth (`cm4ai.org/data-releases/`) describes the
series itself as a programme of quarterly releases and lists the archive of prior
releases.

Consequences held consistently across both records:

- Top-level identity is the series. `doi`, `version` and `issued` carry the current
  release (June 2026, `doi:10.18130/V3/HIGT4C`, Dataset Version 2.0, 2026-06-17), because
  that is the release the series currently resolves to.
- Each captured release is a nested entry under `resources` (`Dataset` in full,
  `CoreDataset` in core), carrying its own DOI, version, publication date, file inventory
  and download counts.
- The May 2024 release is named in `version_access` and `distribution_dates` with the DOI
  the project preprint gives (`doi:10.18130/V3/DXWOS5`) but is **not** a `resources` entry,
  because the bundle carries no processed record of its content.

## Phase 3 — source and provenance audit

### Provenance

- No prior generated D4D record was read, opened, grepped or consulted. Nothing under
  `data/d4d_concatenated/` was accessed other than writing this run's own three output
  files, and no `*_crate_d4d.yaml` or `*_crate_mapped_d4d.yaml` under
  `data/ro-crate_packages/` was accessed.
- Factual inputs used: the declared bundle only. Structural inputs: the LinkML schemas,
  enumerated at runtime with `SchemaView` rather than copied from any example.
- `data/preprocessed/source_manifest.yaml` was read for provenance context (which sources
  the bundle selects and why), not as a source of dataset facts.
- Both headers state `Prior D4D factual reuse: prohibited`; the core header names both its
  document bundle and the exact same-run full YAML path, which carries this run's label.

### Structure

Every emitted slot and nested object was derived from the schema at runtime:

- Full structure from `Dataset` in `data_sheets_schema_all.yaml` (117 induced slots).
- Core structure from `CoreDataset` in `data_sheets_schema_core_all.yaml` (79 induced
  slots).
- Slots whose class range carries an identifier and is not inlined were emitted as plain
  strings, per the schema, not as nested objects: `principal_investigator`,
  `contact_person`, `reviewing_organization`, `grantor`, `governance_committee_contact`.
- No `d4d:docExample` value was copied; every populated value traces to the bundle.

### Disagreements within the bundle — represented, not resolved

The uniform rule for this arm is to represent what the evidence states rather than
silently selecting one reading. Four disagreements were found and are carried explicitly:

1. **IF image protein counts.** March 2025 v0.6-beta archives state 563 proteins; the
   June 2025, October 2025 and June 2026 archives state 464; the `cm4ai.org/data-releases/`
   page states "IF images for 523 proteins"; the CM4AI portal reports 53,788 images in
   aggregate. `instances/d4d:CM4AI_instance_if_images` records 464 as `counts` (the current
   releases' figure) and names all four figures with their scopes in `description`.
2. **Perturb-seq gene counts for the TNBC arm.** The data-releases page states
   "Perturb-seq of 200 genes"; the project preprint describes screens perturbing 100
   chromatin regulators under three conditions. Both are recorded in
   `instances/d4d:CM4AI_instance_perturbseq_tnbc`.
3. **Project end date.** NIH RePORTER gives project end 2026-08-31; the Dataverse release
   metadata states augmentation "through the end of the project in November 2026". Both are
   recorded, attributed to their source, in `collection_timeframes` and `updates`.
4. **June 2026 release date.** The `cm4ai.org/data-releases/` page labels HIGT4C the
   June 2026 release while displaying "Released on: June 17, 2025"; the Dataverse citation
   metadata for the same DOI gives publication date 2026-06-17 and a 2026 citation year.
   Both statements are recorded in `distribution_dates`.

### Distinct entities kept distinct

The bundle's largest document is the Nature paper "Multimodal cell maps as a foundation
for structural and functional genomics" (Schaffer et al., Nature 642:222–231, 2025;
`doi:10.1038/s41586-025-08878-3`). It acknowledges the same Bridge2AI award (OT2 OD032742),
but it reports a **U2OS osteosarcoma** cell map built from Human Protein Atlas and BioPlex
source data and deposited in NDEx, MassIVE, ProteomeXchange, ModelArchive, the EBI Complex
Portal and HPA v23 — not in the CM4AI Dataverse collection, and not from the MDA-MB-468 or
KOLF2.1J lines that the CM4AI releases carry. It was therefore **not** merged into the
release-series referent. It appears as:

- `external_resources/d4d:CM4AI_ext_u2os_study`, listing that study's deposits with their
  scope stated explicitly; and
- `related_datasets/d4d:CM4AI_related_u2os` (`relationship_type: references`) — a full-only
  slot, so this entry is absent from core by schema projection.

Its shared methodological link to CM4AI (the Cell Mapping Toolkit implements the MuSIC
pipeline that CM4AI's Tools module maintains) is stated from the CM4AI preprint's own
account of the pipeline, not imported from the Nature methods.

### Corrections made during the audit

One item was found on re-check of the bundle and back-ported into the **full** record
first, then propagated to core by regeneration:

- `license_and_use_terms.license_terms` gained the Bridge2AI Open House Code of Conduct
  attestation requirement for accessing B2AI data including CM4AI datasets (CM4AI preprint,
  Ethics section), and an explicit statement that the captured release pages mark every
  file `File Access: Public` with no request-access step recorded.

No unsupported, stale or mis-scoped assertion was found requiring removal. Repeated
identifiers, DOIs, versions, dates, counts, licences, people and organizations were checked
for internal consistency within each file and agree.

### Values deliberately omitted

Omission was preferred over inference in these cases:

- `total_size_bytes` / `FileCollection.total_bytes` / `CoreDistribution.bytes`: sizes appear
  only as human-readable strings ("3.8 GB", "1000.1 KB", "21.4 TB"). Converting them would
  fabricate precision, so sizes are carried verbatim in descriptions instead.
- `hipaa_compliant`: the bundle records Human Subjects: No and FDA Regulated: No, but says
  nothing about HIPAA.
- `dialect` (core-only): no tabular dialect is described anywhere in the bundle.
- `data_topic` / `data_substrate`: no Bridge2AI standards-registry CURIEs appear in the
  bundle.
- Repository URLs that appear in the bundle only as link labels ("MassIVE Repository",
  "NCBI BioProject", "Figshare") are named as labels rather than emitted as invented URIs;
  `raw_sources.access_url` was left unset for those entries for the same reason.
- `subsets`: the cell-line/treatment arms are described through `instances`,
  `sampling_strategies` and `subpopulations` rather than duplicated as `DataSubset`
  objects.

## Phase 4 — strict full/core reconciliation

Shared slots were derived at runtime with `SchemaView`, not from a hand-written list.

- Shared slots between `Dataset` and `CoreDataset`: **77**
- Schema-identical (same induced range and cardinality): **76** — all verified deeply
  identical in parsed YAML, including every nested mapping value and list item in order.
  No narrative field was condensed, paraphrased, reordered or omitted in core.
- Projected slot: **1** (`resources`: `Dataset` in full, `CoreDataset` in core).
- Full-only slots present in the full record and correctly absent from core by projection:
  `citation`, `collection_consents`, `file_collections`, `related_datasets`,
  `relationships`, `third_party_sharing`, `total_file_count`.
- Core-only slots: `distributions` (populated), `dialect` (unpopulated — no evidence).

### `resources` projection

Coverage is equal and matched by `id`:

| Release | full `file_collections` | core `distributions` | ids match |
|---|---|---|---|
| `doi:10.18130/V3/HIGT4C` | 10 | 10 | yes |
| `doi:10.18130/V3/K7TGEM` | 8 | 8 | yes |
| `doi:10.18130/V3/F3TD5R` | 7 | 7 | yes |
| `doi:10.18130/V3/B35XWX` | 6 | 6 | yes |

Every schema-identical slot inside the matched resource pairs is deeply identical. The
full-only nested slots `file_collections` and `total_file_count` are omitted from the core
projection, as required.

### Related, non-identical representations — semantic review

`FileCollection` (full) → `CoreDistribution` (core) is the one related-content mapping in
this pair. It was reviewed field by field, not merely validated:

- `id`, `name`, `path`, `compression`, `description` are carried across unchanged, so no
  content is lost in the projection.
- `md5`: `CoreDistribution` has a dedicated `md5` slot that `FileCollection` lacks. The
  29 file entries whose Dataverse metadata gives exactly one MD5 checksum carry it as a
  structured value in core; in full the same checksums are carried verbatim in the
  `description` text. Both records therefore assert the same checksums, at different
  levels of structure. The two grouped entries that describe several files at once
  (`d4d:CM4AI_F3TD5R_prov_images`, `d4d:CM4AI_F3TD5R_massspec_cancer`) carry multiple MD5s
  and were left in description form only, since a single-valued `md5` slot cannot hold
  them without asserting a false mapping.
- `format` / `media_type`: derived from the file extension recorded in the file name
  (`.zip` → `ZIP` / `application/zip`; `.json` → `JSON` / `application/json`; `.html` →
  `HTML` / `text/html`). The two grouped entries have no single extension and carry neither.
- `bytes`, `hash`, `sha256`, `encoding`: unset — the bundle gives only MD5 and
  human-readable sizes.
- `file_count` appears only in full (`FileCollection.file_count`, set on the two grouped
  entries); `CoreDistribution` has no counterpart, so this is a projection loss, not a
  contradiction.

Scope checks: `total_file_count` per release (10 / 8 / 7 → the June 2025 release states 21
files of which the captured listing enumerates 7 / 6) agrees with the enumerated
collections except for the June 2025 release, where the source page paginates at 10 of 21
files and the remainder were not captured. That gap is stated in the record itself
(`d4d:CM4AI_F3TD5R_massspec_cancer.description`) rather than silently smoothed over.
`is_tabular: false` is consistent with the formats present (ZIP archives of images and
mass-spec data, JSON metadata, HTML). Top-level identity, version and access facts agree
with `resources`, `version_access`, `distribution_dates` and the repeated statements in
`license_and_use_terms` and `ip_restrictions`. Historical releases are marked as historical
in their `status`, so their differing figures are not treated as contradictions of the
current release.

### Commands run

```bash
poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_all.yaml \
  -C Dataset data/d4d_concatenated/claudecode_agent/2026-07-28_claude-opus-5-generic_rep2/CM4AI_d4d.yaml

poetry run linkml-term-validator validate-data \
  data/d4d_concatenated/claudecode_agent/2026-07-28_claude-opus-5-generic_rep2/CM4AI_d4d.yaml \
  --schema src/data_sheets_schema/schema/data_sheets_schema_all.yaml --target-class Dataset

poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml \
  -C CoreDataset data/d4d_concatenated/claudecode_agent_core/2026-07-28_claude-opus-5-generic_rep2/CM4AI_d4d_core.yaml

poetry run linkml-term-validator validate-data \
  data/d4d_concatenated/claudecode_agent_core/2026-07-28_claude-opus-5-generic_rep2/CM4AI_d4d_core.yaml \
  --schema src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml --target-class CoreDataset

poetry run python -m data_sheets_schema.d4d_pair_consistency \
  --full data/d4d_concatenated/claudecode_agent/2026-07-28_claude-opus-5-generic_rep2/CM4AI_d4d.yaml \
  --core data/d4d_concatenated/claudecode_agent_core/2026-07-28_claude-opus-5-generic_rep2/CM4AI_d4d_core.yaml

poetry run d4d provenance record --project CM4AI --method claudecode_agent \
  --label 2026-07-28_claude-opus-5-generic_rep2 \
  --input-bundle data/preprocessed/concatenated/CM4AI_preprocessed.txt
```

`--sync-core` was not needed and was not run: the pair passed on first check, because core
was derived from the validated full record by schema-driven projection rather than
re-authored.

### Results

| Check | Result |
|---|---|
| Full — LinkML schema validation (`Dataset`) | No issues found |
| Full — ontology term validation | Validation passed |
| Core — LinkML schema validation (`CoreDataset`) | No issues found |
| Core — ontology term validation | Validation passed |
| Schema-derived pair consistency | PASS — 76 schema-identical slots; projected slots = `['resources']` |
| Validator warnings | none |

### Files changed

- Created `data/d4d_concatenated/claudecode_agent/2026-07-28_claude-opus-5-generic_rep2/CM4AI_d4d.yaml`
- Created `data/d4d_concatenated/claudecode_agent_core/2026-07-28_claude-opus-5-generic_rep2/CM4AI_d4d_core.yaml`
- Created `data/d4d_concatenated/claudecode_agent_core/2026-07-28_claude-opus-5-generic_rep2/CM4AI_reconciliation.md`
- Created `data/d4d_concatenated/claudecode_agent_core/2026-07-28_claude-opus-5-generic_rep2/CM4AI_provenance.yaml`

No file outside this run's three declared output paths (plus the provenance record the
playbook requires) was modified.

### Divergence summary

Nothing diverged between the full and core records. Every schema-identical shared slot is
present in both with deeply identical parsed content; the single projected slot has equal
coverage and identity on every schema-identical nested slot; and the one related-content
mapping (`file_collections` → `distributions`) carries no contradiction, only the
structural differences documented above.

Informational size metadata (not a quality gate): full 1,760 lines / 63 top-level slots;
core 1,390 lines / 58 top-level slots.
