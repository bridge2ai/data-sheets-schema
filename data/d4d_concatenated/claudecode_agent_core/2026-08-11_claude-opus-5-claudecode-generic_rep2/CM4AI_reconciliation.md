# CM4AI full/core reconciliation — 2026-08-11_claude-opus-5-claudecode-generic_rep2

| | |
|---|---|
| Project | CM4AI |
| Arm | BASELINE (input documents only) |
| Version label | `2026-08-11_claude-opus-5-claudecode-generic_rep2` |
| Runtime / provider / model | Claude Code / Anthropic / claude-opus-5 |
| Mode | four-phase project agent, generic prompt |
| Declared input bundle | `data/preprocessed/concatenated/CM4AI_preprocessed.txt` |
| Full record | `data/d4d_concatenated/claudecode_agent/2026-08-11_claude-opus-5-claudecode-generic_rep2/CM4AI_d4d.yaml` |
| Core record | `data/d4d_concatenated/claudecode_agent_core/2026-08-11_claude-opus-5-claudecode-generic_rep2/CM4AI_d4d_core.yaml` |

## Referent

`Dataset` admits one referent. The referent chosen is **the CM4AI (Cell Maps for
Artificial Intelligence) dataset as a whole**, identified by `id:
https://cm4ai.org/`. This matches the declaration in the `scope:` block of
`data/preprocessed/source_manifest.yaml` (`referent_id: https://cm4ai.org/`;
`related_but_distinct: []`), and it is the reading the bundle best supports: the
bundle documents five quarterly Dataverse releases, and the manifest's
`referent_note` states that the Dataverse releases are releases of this dataset
rather than separate datasets.

Consequences held consistently across both records:

- The five releases are represented under `resources` (full: `Dataset`; core:
  `CoreDataset`), each carrying its own DOI, version, publication date and file
  count, rather than one release being promoted to be the record's subject.
- Top-level `doi`, `version`, `total_file_count` and `total_size_bytes` are left
  absent, because every candidate value in the bundle is scoped to one release.
  Release-scoped identifiers live on the release resources and in
  `version_access`.

### A scoping decision the bundle forces

The bundle's largest single document (131 KB of 313 KB) is the 2025 *Nature*
article "Multimodal cell maps as a foundation for structural and functional
genomics" (Schaffer et al., Nature 642:222–231, doi 10.1038/s41586-025-08878-3),
carried in the manifest as source id `nature_publication`. It acknowledges
Bridge2AI Program funding (OT2 OD032742) and uses the same multimodal mapping
approach, but it reports a map of **U2OS osteosarcoma cells** — a cell line that
appears nowhere in the CM4AI data releases, which cover MDA-MB-468 and KOLF2.1J
only. None of that study's data is in the Dataverse releases.

It is therefore recorded as an **external resource and companion study**, with its
portal, NDEx accessions, MassIVE/ProteomeXchange/ModelArchive identifiers and
publication history, and an explicit `source_caveats` saying so. Its counts
(5,100+ proteins, 275 assemblies, 111 heterodimeric structures, 2,174 AP-MS baits,
10,348 IF-stained proteins), its 34-author list, and its U2OS-specific methods
(DIA-NN, HiDeF, AlphaFold-Multimer, GSAI/GPT-4 annotation) are **not** carried
into this record's `instances`, `creators`, `collection_mechanisms` or
`preprocessing_strategies`. The manifest declares no `related_but_distinct`
entry for CM4AI, so no `related_datasets` claim is made about it either.

This is the single largest judgement in the record, and it is the one most likely
to differ between runs.

## Phase 3 — source and provenance audit

### Provenance

- Factual inputs read: `data/preprocessed/concatenated/CM4AI_preprocessed.txt`
  and `data/preprocessed/source_manifest.yaml` (the `scope:` block, via
  `d4d download scope --project CM4AI` and by reading the manifest).
- Structural inputs read: `data_sheets_schema_all.yaml` (class `Dataset`) and
  `data_sheets_schema_core_all.yaml` (class `CoreDataset`), introspected with
  LinkML `SchemaView` rather than by copying any record's shape.
- **No prior D4D record was read, opened, grepped or consulted.** Nothing under
  `data/d4d_concatenated/` other than this run's own two output paths was read;
  no `*_crate_d4d.yaml` or `*_crate_mapped_d4d.yaml` under
  `data/ro-crate_packages/` was read. The only directory listing taken of
  `data/d4d_concatenated/claudecode_agent/` was of *names*, to confirm the
  version label was new — permitted to the orchestrator by the playbook, and it
  put no prior content into context.
- Phase 2 read the exact same-run Phase 1 path, which carries this run's version
  label.
- Both headers state `Prior D4D factual reuse: prohibited`. The core header names
  both its document bundle and its same-run full record, and carries
  `Phase 4 reconciliation: completed`.

### Shape and evidence findings, and what was done

All findings were corrected in the full record first; the core record was then
regenerated from the corrected full record, so every correction is present in
both.

1. **`conforms_to_schema` / `conforms_to_class` cannot be filled correctly in a
   pair.** The slot descriptions say these describe *the record itself* —
   `Dataset` for a full datasheet, `CoreDataset` for a core one — and the two
   schemas carry different ids (`…/data-sheets-schema` and
   `…/data-sheets-schema/core-schema`). Both slots are nevertheless
   schema-identical shared slots, so `d4d_pair_consistency` requires deep
   identity, and any correct value in one record is a false statement in the
   other. **Both slots were removed from both records.** Filling them would have
   put a false self-description into the core file to satisfy an identity rule;
   omitting them loses a true statement from each. This is a schema/validator
   tension, not a content decision, and it is reported here rather than papered
   over.
2. **Evidence commentary sat in `notes`.** The top-level `notes` held a
   source disagreement about which institutions the collaboration comprises.
   That is `source_caveats` content by the schema's own definition. It was moved
   to the `source_caveats` of the new project-level `Creator`, whose
   `affiliations` it is commentary about, and top-level `notes` was dropped.
3. **A structured slot sat empty while its content sat in prose.**
   `Creator.principal_investigator` was unused, while the PI fact was stated in
   the prose of the Trey Ideker creator entry — which additionally pointed
   `principal_investigator` at its own `id`. A project-level `Creator` ("Cell
   Maps for Artificial Intelligence (CM4AI) project") was added carrying
   `principal_investigator` (Ideker's ORCID, from NIH RePORTER) and
   `affiliations` (the nine collaborating institutions); the self-reference was
   removed. The institution list was correspondingly removed from the top-level
   `description`, where it was duplicating a structured slot.
4. **Enum values asserted more than the evidence.** `Maintainer.role` was set to
   `academic_institution` for two named individuals and `researcher` for two
   others. The bundle gives their institutions and functions, not their
   entity kind. `role` was removed from all four individuals and retained only
   for the University of Virginia Dataverse, which is unambiguously an academic
   institution.
5. **Commentary embedded inside values.** Removed from three places:
   `funders[].name` ("University of Virginia (Frederick Thomas Fund)" → name
   `Frederick Thomas Fund`, grantor `University of Virginia`);
   `human_subject_research.regulatory_compliance` (`"Dataverse release metadata:
   FDA Regulated: No"` → `Not FDA regulated`, with the provenance moved to
   `source_caveats`); `ip_restrictions.restrictions` (copyright years differing
   between the 2024 preprint and the 2025 release pages were inlined in
   parentheses — years removed from the statements, disagreement moved to
   `source_caveats`).
6. **List values carrying parenthetical audit notes.**
   `version_access.versions_available` carried "(cited as V2; page header Version
   2.1)" inside each item. The items are now plain "release name: DOI" and the
   version-number disagreement moved to `version_access.source_caveats`; the
   page-header version is recorded on each release under `resources`.
   `distribution_dates.release_dates[0]` carried "(no date given in the bundle
   beyond the month)"; moved to the sibling `source_caveats`.
7. **A sibling value restated in prose.** `license_and_use_terms.description`
   named the Point of Contact whose ORCID is the sibling `contact_person`.
   Rewritten as `source_caveats` explaining what `contact_person` was
   transcribed from and why `data_use_permission` is `no_commercial_use` while
   the licence's Attribution and ShareAlike terms have no enumerated value.
8. **An inaccurate media type.** `distribution_formats[1].media_type` was
   `application/json` for an entry covering JSON-LD RO-Crate metadata *and* HTML
   provenance graphs; corrected to `application/ld+json, text/html`. The Croissant
   export, offered only on two of the four release pages, was moved out of the
   `format` string into the description.
9. **The same `Software` object described differently in two places.** The Cell
   Mapping Toolkit and FAIRSCAPE each appeared under
   `preprocessing_strategies[].used_software` with a description and under
   `external_resources[].used_software` without one. The objects were made
   identical wherever the same `id` appears.
10. **An empty list.** `variables: []` was removed; the bundle documents no
    variable-level metadata, and an absent slot is the correct answer.

### Source disagreements recorded rather than resolved

Every one of these is represented in `source_caveats` on the object it concerns,
with both readings stated. None was silently resolved.

| Disagreement | Sources | Where recorded |
|---|---|---|
| June 2026 release date: 2026-06-17 vs "Released on: June 17, 2025" | Dataverse `HIGT4C` page vs cm4ai.org data-releases page | `resources[4].source_caveats`, `distribution_dates[0].source_caveats` |
| Release version numbers: citation block V1/V2 vs page header 1.4/2.1/2.1/2.0 | Dataverse citation vs page header, all four releases | each `resources[n].source_caveats`, `version_access.source_caveats` |
| Andrej Sali's affiliation: UCSD vs UCSF | Dataverse author lists vs the CM4AI preprint and the Nature article | `creators[].source_caveats` (Sali A) |
| Project end: 2026-08-31 vs "November 2026" | NIH RePORTER vs Dataverse maintenance plan | `collection_timeframes[0].source_caveats` |
| Collaborating institutions: with vs without UT Austin; a third list in the preprint | cm4ai.org vs March 2025 release vs preprint | project-level `creators[].source_caveats` |
| Copyright year 2024 vs 2025 for the same two holders | preprint vs release descriptions | `ip_restrictions.source_caveats` |
| IF imaging protein counts 563 / 523 / 464 | March 2025 release vs cm4ai.org flagship summary vs June 2025 onward | `subsets[2].source_caveats` |
| Identically named IF archives with different MD5s across releases | October 2025 vs June 2026 file tables | `file_collections[0].resources[2].source_caveats` |
| "Data Creation Date 2025-02-27" carried identically on all four release pages | all Dataverse releases | `resources[1].source_caveats`; `created_on` left absent as a result |

### Facts checked against the bundle

Every DOI, ORCID, MD5, date and integer in the full record was matched
mechanically against the bundle text. The only non-matches were formatting
normalisations that are faithful transcriptions: prose dates rewritten to ISO
("03 June 2024" → 2024-06-03; "Published Oct 22, 2025" → 2025-10-22; "Published
Jul 15, 2026" → 2026-07-15) and two DOIs whose trailing sentence period the
regex captured. No value was found that the bundle does not support.

All four `instances[].counts` (53,788 images; 1,374 protein interactions; 7,023
proteins; 11,739 genes), all four release `total_file_count` values (6, 21, 8,
10) and the collection `file_count` (10) appear verbatim in the bundle.

### Content the bundle does not support, left absent

`variables`, `relationships`, `splits`, `imputation_protocols`,
`cleaning_strategies`, `annotation_analyses`, `data_protection_impacts`,
`informed_consent`, `at_risk_populations`, `collection_consents`,
`collection_notifications`, `consent_revocations`, `participant_privacy`,
`participant_compensation`, `content_warnings`, `extension_mechanism`,
`use_repository`, `parent_datasets`, `raw_sources`, `dialect` (core),
`language`, `created_on`, `created_by`, `modified_by`, `was_derived_from`,
`hipaa_compliant`, `confidentiality_level`, `irb_approval`,
`ethics_review_board`, and all `bytes`/`total_bytes` values (Dataverse reports
sizes only in rounded units such as "3.8 GB").

## Phase 4 — strict full/core reconciliation

The shared-slot inventory was derived at runtime with LinkML `SchemaView` over
`Dataset` and `CoreDataset`; no hand-written field list was used. The core record
was **generated by projection from the validated Phase 1 full record**, so
schema-identical content is identical by construction rather than by transcription.

| Category | Count |
|---|---|
| Schema-identical shared slots (same induced range and cardinality) | 78 |
| Projected shared slots (differing range) | 1 (`resources`) |
| Full-only slots | 18 |
| Core-only slots | 2 (`dialect`, `distributions`) |
| Top-level slots populated — full | 63 |
| Top-level slots populated — core | 57 |

### Schema-identical slots

All 78 satisfy identical presence and deep identity of parsed YAML content,
including every nested mapping value and list item in order. Narrative fields
(`description`, `source_caveats`, all `*_details` fields, `license_terms`) were
copied verbatim: **nothing was condensed, paraphrased, reordered or omitted to
make core shorter.** Verified by `d4d_pair_consistency`: `PASS: 78
schema-identical slots`.

### Projected slot: `resources` (`Dataset` → `CoreDataset`)

Five resources in full, five in core, matched by `id` with equal coverage and no
duplicates:

| `id` | Release |
|---|---|
| `https://doi.org/10.18130/V3/DXWOS5` | May 2024 |
| `https://doi.org/10.18130/V3/B35XWX` | March 2025 (Beta) |
| `https://doi.org/10.18130/V3/F3TD5R` | June 2025 (Beta) |
| `https://doi.org/10.18130/V3/K7TGEM` | October 2025 (Beta) |
| `https://doi.org/10.18130/V3/HIGT4C` | June 2026 (Beta) |

Every nested slot present in both classes (`id`, `name`, `title`, `description`,
`doi`, `version`, `page`, `publisher`, `issued`, `license`, `status`,
`source_caveats`) is deeply identical. The one full-only nested slot,
`total_file_count` (6 / 21 / 8 / 10), is omitted from the core projection because
`CoreDataset` does not define it.

### Related, non-identical representation: `file_collections` → `distributions`

Full holds one `FileCollection` (`https://doi.org/10.18130/V3/HIGT4C#files`, the
June 2026 release archives) containing ten `File` objects. Core holds ten
`CoreDistribution` objects. The deterministic matcher reports **10 matches at the
nested resource level, 0 unmatched core distributions**, and raises the expected
`semantic-review-required` warning. The semantic review the warning asks for was
performed:

- **Identity and order.** All ten `id` values match one-for-one and in the same
  order; each is the release DOI plus the archive filename.
- **Names.** Identical filenames on both sides (`cm4ai_apms_MDA-MB-468_*.zip`,
  `cm4ai_ifimages_MDA-MB-468_*.zip`, `cm4ai_mass-spec_*.zip`,
  `cm4ai_perturb-seq_KOLF2_*.zip`, `cm4ai_release_metadata.zip`).
- **Descriptions.** Carried verbatim, including the reported rounded size,
  publication date and download count for each archive.
- **Checksums.** All ten `md5` values are identical across the pair and match the
  bundle. `hash` and `sha256` are absent on both sides — Dataverse publishes MD5
  only.
- **Formats and compression.** `format: ZIP`, `media_type: application/zip`,
  `compression: zip` on both sides for all ten. `File.file_type: archive_file`
  is full-only (`CoreDistribution` has no `file_type`) and is dropped by the
  projection; it conflicts with nothing.
- **Byte counts.** Absent on both sides, for the same reason: Dataverse gives
  only rounded sizes. `total_file_count` / `total_size_bytes` are absent at the
  top level of the full record, and `CoreDataset` defines neither, so there is no
  aggregate to contradict.
- **Release scope.** Both sides describe exactly the June 2026 release and
  nothing else. No cross-release contamination: the one archive whose name
  recurs in the October 2025 release carries a different MD5 and says so.
- **`is_tabular` and `dialect`.** `is_tabular: false` in both. `dialect` is
  core-only and left absent, consistent with `is_tabular: false` — the data are
  image, mass-spectrometry and sequencing archives, and the bundle describes no
  tabular dialect.
- **`compression`.** Top-level `compression: zip` in both, consistent with every
  distribution's `compression: zip`.
- **Top-level identity against the resources.** `license: CC BY-NC-SA 4.0`,
  `publisher: https://dataverse.lib.virginia.edu/` and `status: Beta` at the top
  level agree with the same values on every release resource;
  `version_access.latest_version_doi` (`…/HIGT4C`) is the resource whose `issued`
  is latest; `last_updated_on: 2026-07-15` is the latest file publication date in
  that release. Historical releases are represented as releases with their own
  dates, not as contradictions of the current one.

### Content lost by the core projection

`CoreDataset` defines no slot for the following full-record content. It is listed
here so the loss is on the record rather than silent. Nothing was moved into an
ill-fitting core slot to avoid the loss, and nothing was invented to compensate.

| Full-only slot | Content lost from core |
|---|---|
| `citation` | The June 2026 release's recommended data citation |
| `subsets` | Four `DataSubset` records for the SEC-MS, AP-MS, IF-imaging and perturb-seq modalities, with their per-release protein and gene counts |
| `data_governance` | Data Access Committee, governance-committee contact, access review process (commercial use requires separate negotiation with UCSD/Stanford/UCSF), stewardship roles |
| `third_party_sharing` | Deposition of components in MassIVE, NCBI SRA/BioProject, Figshare and NDEx |
| `direct_collection` | The statement that data are generated directly by the project from cultured cell lines |
| `related_datasets` | `is_described_by` → the CM4AI project preprint |
| `file_collections` | Collection-level metadata: name, description, `collection_type: raw_data`, `file_count: 10`, `download_url`, `license`, and the caveat explaining why byte counts are absent |
| `total_file_count` (nested, on resources) | Per-release file counts 6 / 21 / 8 / 10 |

`ExportControlRegulatoryRestrictions.governance_committee_contact` exists in both
schemas and would have been the only partial home in core for the governance
contact. It was deliberately **not** used: filling it would restate
`data_governance.committee_contact` in the full record, which the slot-filling
rule forbids, and leaving it in core alone would break schema-identical deep
identity. The loss is recorded here instead.

## Commands run

```bash
# structure derived from the schemas, not from any record
poetry run python /tmp/introspect.py src/data_sheets_schema/schema/data_sheets_schema_all.yaml Dataset
poetry run python /tmp/introspect.py src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml CoreDataset

# scope declaration and check
poetry run d4d download scope --project CM4AI
poetry run d4d download scope --check --project CM4AI

# Phase 1 + Phase 3 validation (re-run after every correction)
poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_all.yaml \
  -C Dataset data/d4d_concatenated/claudecode_agent/2026-08-11_claude-opus-5-claudecode-generic_rep2/CM4AI_d4d.yaml
poetry run linkml-term-validator validate-data \
  data/d4d_concatenated/claudecode_agent/2026-08-11_claude-opus-5-claudecode-generic_rep2/CM4AI_d4d.yaml \
  --schema src/data_sheets_schema/schema/data_sheets_schema_all.yaml --target-class Dataset

# Phase 2 + Phase 3 validation
poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml \
  -C CoreDataset data/d4d_concatenated/claudecode_agent_core/2026-08-11_claude-opus-5-claudecode-generic_rep2/CM4AI_d4d_core.yaml
poetry run linkml-term-validator validate-data \
  data/d4d_concatenated/claudecode_agent_core/2026-08-11_claude-opus-5-claudecode-generic_rep2/CM4AI_d4d_core.yaml \
  --schema src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml --target-class CoreDataset

# Phase 4: one synchronization, then an independent check
poetry run python -m data_sheets_schema.d4d_pair_consistency \
  --full data/d4d_concatenated/claudecode_agent/2026-08-11_claude-opus-5-claudecode-generic_rep2/CM4AI_d4d.yaml \
  --core data/d4d_concatenated/claudecode_agent_core/2026-08-11_claude-opus-5-claudecode-generic_rep2/CM4AI_d4d_core.yaml \
  --sync-core
poetry run python -m data_sheets_schema.d4d_pair_consistency \
  --full data/d4d_concatenated/claudecode_agent/2026-08-11_claude-opus-5-claudecode-generic_rep2/CM4AI_d4d.yaml \
  --core data/d4d_concatenated/claudecode_agent_core/2026-08-11_claude-opus-5-claudecode-generic_rep2/CM4AI_d4d_core.yaml
```

The synchronization pass changed no content — the core file was structurally and
key-order identical before and after — because core was produced by projection
from the already-canonical full record. Its only effect was to add
`# Phase 4 reconciliation: completed` to the core header.

## Final results

| Check | Result |
|---|---|
| `linkml-validate` full (`Dataset`) | **No issues found** |
| `linkml-term-validator` full | **Validation passed** |
| `linkml-validate` core (`CoreDataset`) | **No issues found** |
| `linkml-term-validator` core | **Validation passed** |
| `d4d_pair_consistency` (final, no `--sync-core`) | **PASS: 78 schema-identical slots; projected slots=['resources']** |
| `d4d_pair_consistency` warnings | 1 × `semantic-review-required` on `file_collections` ↔ `distributions`; the review is above |
| `d4d download scope --check --project CM4AI` | in scope — the record does not identify itself as a dataset the manifest declares distinct |
| Prior-D4D reuse | none; no prior record was read |
| Full-record top-level slots | 63 (1,737 lines) |
| Core-record top-level slots | 57 (1,183 lines) |

Line counts are informational metadata, not a quality measure.

## Outstanding

- **Provenance record not written by this agent.** The launcher writes the live
  `d4d provenance record` for this run. Until it does, the run has no
  machine-readable provenance and `d4d runs check --strict` and
  `d4d runs validate` have not been run for it.
- **`conforms_to_schema` / `conforms_to_class` are absent from both records** for
  the reason in Phase 3 finding 1. This is a real gap in the pair: neither record
  declares the schema it is written in. Resolving it needs a change outside this
  run — either an exemption for these two slots in `d4d_pair_consistency`, or a
  decision that they are record-specific by design.
