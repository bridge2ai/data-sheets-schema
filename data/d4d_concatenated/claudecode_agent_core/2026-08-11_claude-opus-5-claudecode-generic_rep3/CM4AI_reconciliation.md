# CM4AI full/core reconciliation

Run label: `2026-08-11_claude-opus-5-claudecode-generic_rep3`
Arm: BASELINE (input documents only)
Runtime: Claude Code · Provider: Anthropic · Model: claude-opus-5 · Temperature 0.0
Mode: four-phase project agent, generic prompt
Prompt: `src/download/prompts/d4d_generic_arm_prompt.md`

Artifacts:

- Full: `data/d4d_concatenated/claudecode_agent/2026-08-11_claude-opus-5-claudecode-generic_rep3/CM4AI_d4d.yaml`
- Core: `data/d4d_concatenated/claudecode_agent_core/2026-08-11_claude-opus-5-claudecode-generic_rep3/CM4AI_d4d_core.yaml`
- This report

Declared inputs: `data/preprocessed/concatenated/CM4AI_preprocessed.txt` (10 source
documents), `data/preprocessed/source_manifest.yaml`, and the full and core LinkML
schemas.

## Referent

`Dataset` admits one referent. The record is about the **CM4AI (Cell Maps for
Artificial Intelligence) dataset**, identified by `https://cm4ai.org/`, which is the
referent the manifest's `scope:` block declares for this project and the identifier
the bundle's own documentation pages use. CM4AI has no single minted dataset DOI; the
five data releases in the bundle each have their own University of Virginia Dataverse
DOI and are represented as `resources` (sub-datasets) of the one referent, not as
separate datasets. The manifest declares no related-but-distinct dataset for CM4AI,
and the record asserts none. The same choice is held in both records: core carries
the identical `id`, `name`, `title` and the same five projected resources.

`d4d download scope --check --project CM4AI` reports the record in scope.

## Phase 3 — source and provenance audit

### Provenance boundary

No prior full or core D4D record was read, from any arm, label or date. Nothing
under `data/d4d_concatenated/` was opened, and no `*_crate_d4d.yaml` or
`*_crate_mapped_d4d.yaml` under `data/ro-crate_packages/` was opened. The only
directory listing taken was of `data/d4d_concatenated/claudecode_agent/`, to confirm
the version label was unused; file *names* only, no content. Factual inputs were the
declared bundle and the manifest; structural inputs were the two schemas, read via
`SchemaView` rather than from any example record. No `d4d:docExample` value was
copied.

### Structure derived from the schema

Every emitted slot and nested object shape was resolved at runtime from class
`Dataset` (full) and `CoreDataset` (core) with `SchemaView`, following `is_a`,
`slots`, `slot_usage`, ranges, cardinality, inlining and enums. Three shape
corrections were forced by validation and made against the schema, not against a
template:

1. `principal_investigator`, `contact_person` and `committee_contact` have range
   `Person` but are **not inlined**, so they take an identifier string, not a nested
   object. They now carry `https://orcid.org/0000-0002-1708-8454` (Ideker, whose ORCID
   is in the release author lists) and `mailto:` URIs built from the contact addresses
   printed on the release records. The people's names stay in the surrounding
   `description` / `review_details`, so no fact was lost. `mailto:` was chosen over an
   ORCID for the ethics and governance contacts because matching "Vardit Ravitsky
   (ravitskyv@thehastingscenter.org)" to the author-list entry "Ravitsky V (University
   of Montreal)" would be a cross-source identity claim the bundle does not make.
2. `issued` and `created_on` are `datetime`; the schema's JSON Schema rejects a bare
   date. Dates published by Dataverse are encoded as `YYYY-MM-DDT00:00:00Z`. The date
   is the source's; the time component is an encoding artefact of the slot's range and
   asserts nothing.
3. Enum values were taken only from the schema's permissible values
   (`representation_bias`, `scope_limitation`, `integration_limitation`,
   `no_commercial_use`, `academic_institution`, `raw_data`, `processed_data`,
   `metadata`, `ZIP`, `zip`, `application/zip`, `archive_file`).

Slot-filling order was audited: structured slots are filled before prose, narrative
sits in `description`, `notes` is unused anywhere in either record, and all evidence
commentary (source conflicts, transcription notes, what the bundle does not say) sits
in `source_caveats`. No sibling value is restated in another slot.

### Mechanical verification against the bundle

All 38 ORCID identifiers, all 10 MD5 checksums and every DOI in the full record were
checked for literal presence in the declared bundle: **no misses**. Reported figures
(1,374 / 53,788 / 7,023 / 11,739 / 21.4 TB), the award amount 5289382, the project
period 2022-09-01 to 2026-08-31, RRIDs CVCL_0419 and CVCL_B5P3, the 953.7 MB download
limit and both grant numbers verify likewise. Per-release file counts (6, 21, 8, 10)
match the "1 to N of N Files" and file-type filter counts on each release page.

### Source disagreements — represented, not silently resolved

The bundle's sources conflict in several places. In each case both readings are
carried, in `source_caveats` on the object they concern:

| Disagreement | Where recorded |
|---|---|
| June 2026 release: CM4AI page says "Released on: June 17, 2025"; Dataverse gives publication date 2026-06-17 and citation year 2026 | `distribution_dates.source_caveats`, `resources[HIGT4C].source_caveats` |
| Displayed "Version 1.4 / 2.1 / 2.1 / 2.0" vs data citation "V1 / V2 / V2 / V2" on the same pages | `version_access.source_caveats` and each release's `source_caveats` |
| Project end: release maintenance plan says "November 2026"; NIH RePORTER says 2026-08-31 | `updates.source_caveats`, `collection_timeframes.source_caveats` |
| Collaborating institutions: data-releases page includes UT Austin, March 2025 release description omits it | `creators[0].source_caveats` |
| Sali A affiliated to UCSD on the release records, to UCSF in the project preprint | that creator's `source_caveats` |
| IF images cover 563 proteins (March 2025) vs 464 proteins (June 2025, October 2025, June 2026) | each release's `description` / `source_caveats` |
| Identically named IF archives in October 2025 and June 2026 have different MD5s | `resources[HIGT4C].source_caveats` |
| Copyright year 2025 (March 2025 record) vs 2024 (project preprint) | `ip_restrictions.restrictions` |
| Marquez C's ORCID printed without the `https://orcid.org/` prefix | that creator's `source_caveats` |

Files inside a release sometimes carry publication dates later than the release
itself (June 2025 files on 2025-10-22, October 2025 files on 2025-12-22, June 2026 IF
archives on 2026-07-15). Recorded rather than smoothed.

### Scope: what was deliberately excluded

The bundle's largest document is Schaffer et al., *Multimodal cell maps as a
foundation for structural and functional genomics*, Nature 642:222–231 (2025). It
acknowledges the same Bridge2AI award (OT2 OD032742), but it reports a multimodal cell
map of **U2OS osteosarcoma** cells, deposited at NDEx, MassIVE (MSV000097168),
ProteomeXchange (PXD052362) and the ModelArchive — a different cell line and different
deposits from the MDA-MB-468 / KOLF2.1J releases that the CM4AI release pages
enumerate. No source in the bundle states that those deposits are part of the CM4AI
dataset. Merging them would have manufactured a relation; asserting a
`related_datasets` link would equally have asserted one the sources do not make. The
exclusion and its reason are stated in the record's top-level `source_caveats`, in
both files. Its methodological content (AP-MS, SEC-MS, IF, embedding, community
detection) is therefore *not* used as a description of CM4AI's own pipeline; the
pipeline description comes from the CM4AI project preprint, which describes CM4AI.

Two relations the sources *do* declare are recorded in `related_datasets`
(full only; `CoreDataset` has no such slot): the CM4AI project description preprint
(10.1101/2024.05.21.589311) and the perturbation cell atlas preprint
(10.1101/2024.11.03.621734), both listed as "Related Publication" on the release
records.

### Corrections made in Phase 3

Four assertions were corrected against the sources before reconciliation, all in the
full record, which was then re-projected into core:

1. `status` said "Every data release in the bundle is labelled (Beta)". The May 2024
   release cited in the preprint is not. Narrowed to the four releases that are.
2. `ip_restrictions` attributed the 2025 copyright statement to "the March 2025 and
   June 2025 records". Only the March 2025 description carries it.
3. `maintainers` quoted one repository notice for both venues; Dataverse says
   "This collection is under review…" and the CM4AI site "This repository is under
   review…". Both now quoted correctly.
4. `Bélisle-Pipon` was transcribed without its accent in the citation and creator
   name; restored to match the author list. The ethics-contact spelling stays
   unaccented because that is how the governance block prints it.

Nothing was back-ported *from* core to full: core introduced no fact that the full
record lacked, because every `CoreDataset` slot except `distributions` and `dialect`
also exists on `Dataset` and was populated in Phase 1 from the same bundle.

### Unsupported / omitted by design

Slots left absent because the bundle does not support them: `subsets`, `splits`,
`variables`, `anomalies`, `confidential_elements`, `content_warnings`,
`sensitive_elements`, `subpopulations`, `informed_consent`, `at_risk_populations`,
`participant_privacy`, `participant_compensation`, `collection_consents`,
`collection_notifications`, `consent_revocations`, `data_protection_impacts`,
`labeling_strategies`, `annotation_analyses`, `imputation_protocols`, `raw_sources`,
`raw_data_sources`, `existing_uses`, `use_repository`, `other_tasks`,
`future_use_impacts`, `discouraged_uses`, `errata`, `extension_mechanism`,
`parent_datasets`, `is_tabular`, `total_file_count` and `total_size_bytes` at dataset
level, `dialect`. Two specific judgements: the portal's "21.4 TB" is not written to
`total_size_bytes`, because converting an approximate figure to an integer byte count
would assert a precision the source does not have (it is quoted in `description`
instead); and displayed file sizes such as "3.8 GB" are quoted in each `File`'s
`description` rather than written to `bytes`, for the same reason.

## Phase 4 — strict full/core reconciliation

Shared slots were derived at runtime from `Dataset` and `CoreDataset` with
`SchemaView` (`load_pair_schema`), not from a hand-written list:

- **78 schema-identical slots** — must be present in both or neither, with deeply
  identical parsed YAML.
- **1 projected slot** — `resources`, whose range is `Dataset` in full and
  `CoreDataset` in core.

Result: **PASS, zero errors, zero warnings**, on both the synchronizing run and the
independent re-run.

```
poetry run python -m data_sheets_schema.d4d_pair_consistency --full <full> --core <core> --sync-core
PASS: 78 schema-identical slots; projected slots=['resources']

poetry run python -m data_sheets_schema.d4d_pair_consistency --full <full> --core <core>
PASS: 78 schema-identical slots; projected slots=['resources']
```

No `semantic-review-required` warning was raised, because neither record carries
`file_collections` / `distributions` at the top level — see the projection note below.

### Root slot counts

| | root slots |
|---|---|
| full | 50 |
| core | 44 |

The six full-only root slots are exactly those `CoreDataset` does not define:
`citation`, `data_governance`, `direct_collection`, `related_datasets`,
`relationships`, `third_party_sharing`. Nothing was condensed, paraphrased, reordered
or dropped to make core shorter: all 44 core root slots are byte-identical in parsed
content to their full counterparts.

### Projection: `resources`

Five releases, matched by `id`, equal coverage in both records:

| id | release |
|---|---|
| `https://doi.org/10.18130/V3/DXWOS5` | Cell Maps for Artificial Intelligence - Data Release (V1) |
| `https://doi.org/10.18130/V3/B35XWX` | March 2025 Data Release (Beta) |
| `https://doi.org/10.18130/V3/F3TD5R` | June 2025 Data Release (Beta) |
| `https://doi.org/10.18130/V3/K7TGEM` | October 2025 Data Release (Beta) |
| `https://doi.org/10.18130/V3/HIGT4C` | June 2026 Data Release (Beta) |

Every schema-identical nested slot is deeply identical across the projection. Two
full-only nested slots are correctly omitted from the core projection because
`CoreDataset` does not define them: `total_file_count` (6, 21, 8, 10 on the four
Dataverse releases) and `file_collections`.

### Related, non-identical content: `file_collections` ↔ `distributions`

Semantically reviewed by hand, since the deterministic matcher only inspects the top
level and both records place this content one level down, inside the June 2026
release resource where it belongs — the ten files are that release's files, not the
programme's.

Full carries six `FileCollection` objects (AP-MS ×2, IF images ×3, SEC-MS ×2,
perturb-seq atlas ×1, perturb-seq raw ×1, release metadata ×1) with ten nested `File`
objects. Core carries ten `CoreDistribution` objects, one per file — the correct
granularity, since `FileCollection` is collection-level (`file_count`,
`collection_type`) while `CoreDistribution` is file-level (`md5`, `media_type`,
`bytes`).

Reviewed field by field across all ten pairs, matched on `id`:

- `name` — identical filenames in both (`cm4ai_apms_MDA-MB-468_paclitaxel.zip` …).
- `md5` — identical 32-hex values in both; all ten verified against the bundle.
- `format` / `compression` — `ZIP` / `zip` in both. Core adds `media_type:
  application/zip`, which `File` in the full schema also permits but which was left to
  the collection-level `distribution_formats` entry there; no conflict, since
  `application/zip` is the media type of a `ZIP`-format file.
- `description` — core restates the same repository-displayed size and publication
  date as full, and prefixes the modality (e.g. "AP-MS data for paclitaxel-treated
  MDA-MB-468 cells; repository-displayed size 113.3 KB, published Jun 17, 2026"),
  which in full is carried by the enclosing collection's `description`. Same facts,
  no divergent claim.
- `bytes` / `total_bytes` — absent in both, deliberately (see above). No size
  contradiction is possible.
- `path`, `hash`, `sha256`, `encoding`, `conforms_to` — absent in both.

`total_file_count` (10) on the June 2026 release in full agrees with the ten core
distributions and with the release page's "1 to 10 of 10 Files". `is_tabular` and
`dialect` are absent from both records; the releases distribute ZIP archives, JSON and
HTML, and the bundle states no tabular dialect.

Zero unresolved contradictions within or between the two records.

## Validation

All non-skippable checks, re-run after the final edits:

```
poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_all.yaml \
  -C Dataset data/d4d_concatenated/claudecode_agent/2026-08-11_claude-opus-5-claudecode-generic_rep3/CM4AI_d4d.yaml
→ No issues found

poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml \
  -C CoreDataset data/d4d_concatenated/claudecode_agent_core/2026-08-11_claude-opus-5-claudecode-generic_rep3/CM4AI_d4d_core.yaml
→ No issues found

poetry run linkml-term-validator validate-data <full> \
  --schema src/data_sheets_schema/schema/data_sheets_schema_all.yaml --target-class Dataset
→ ✅ Validation passed

poetry run linkml-term-validator validate-data <core> \
  --schema src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml --target-class CoreDataset
→ ✅ Validation passed

poetry run d4d download scope --check --project CM4AI
→ ✓ none is about a dataset its project declares distinct
```

## Header note

Both headers use the launch instruction's block verbatim, with the core file
substituting "phase 2" and the core schema path. The core file carries two additional
header lines that the block does not contain but the playbook and the provenance guard
require: `# Full D4D input: …` (the guard requires core to name its exact same-run full
record) and `# Phase 4 reconciliation: completed` (a completion criterion, appended by
`--sync-core`). Flagged here rather than left silent, since the launch text said to use
the block exactly.

## Files changed

- `data/d4d_concatenated/claudecode_agent/2026-08-11_claude-opus-5-claudecode-generic_rep3/CM4AI_d4d.yaml` (created, Phase 1; corrected in Phase 3)
- `data/d4d_concatenated/claudecode_agent_core/2026-08-11_claude-opus-5-claudecode-generic_rep3/CM4AI_d4d_core.yaml` (created, Phase 2; synchronized in Phase 4)
- `data/d4d_concatenated/claudecode_agent_core/2026-08-11_claude-opus-5-claudecode-generic_rep3/CM4AI_reconciliation.md` (this report)

Nothing outside these three paths was written.
