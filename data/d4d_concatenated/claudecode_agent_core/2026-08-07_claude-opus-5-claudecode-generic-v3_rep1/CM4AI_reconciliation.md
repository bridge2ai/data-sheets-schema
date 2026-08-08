# CM4AI full/core reconciliation — 2026-08-07_claude-opus-5-claudecode-generic-v3_rep1

- Project: CM4AI
- Arm: BASELINE (input documents only)
- Mode: four-phase project agent, generic prompt
- Agent runtime: Claude Code · Provider: Anthropic · Model: claude-opus-5 · Reasoning effort: high · Temperature: 0.0
- Prompt: `src/download/prompts/d4d_generic_arm_prompt.md`
- Declared input bundle: `data/preprocessed/concatenated/CM4AI_preprocessed.txt`
- Source manifest: `data/preprocessed/source_manifest.yaml`
- Full: `data/d4d_concatenated/claudecode_agent/2026-08-07_claude-opus-5-claudecode-generic-v3_rep1/CM4AI_d4d.yaml`
- Core: `data/d4d_concatenated/claudecode_agent_core/2026-08-07_claude-opus-5-claudecode-generic-v3_rep1/CM4AI_d4d_core.yaml`

## Referent

`Dataset` admits one referent. The declared bundle describes two distinct datasets, and the referent
chosen is **the CM4AI quarterly data release programme deposited in LibraData, the University of
Virginia's Dataverse instance**, with the individual quarterly releases represented as `resources`.

Basis for the choice: seven of the ten bundled documents describe that programme — the CM4AI home
page, the data-releases page, the NIH RePORTER project record, the CC BY-NC-SA 4.0 license deed, and
the four Dataverse release landing pages. The source manifest's `retained_because` note for
`october_2025_dataverse_release` states the same reading explicitly: "CM4AI's pinned referent is the
release programme as an ongoing quarterly series, with releases as `resources`".

The bundled Nature article (`nature_publication`, doi:10.1038/s41586-025-08878-3, Schaffer et al.,
*Nature* 642:222–231, 2025) describes a **different** dataset: a multimodal U2OS osteosarcoma cell
map with its own depositions at NDEx, MassIVE MSV000097168, ProteomeXchange PXD052362 and
ModelArchive. It acknowledges Bridge2AI funding (NIH Common Fund OT2 OD032742) and shares personnel
and the MuSIC methodology with CM4AI, but appears in no CM4AI Dataverse release. It is recorded as a
single `external_resources` entry that names it as a distinct dataset. **No count, cell line, method,
license, access statement, author affiliation or funding attribution from that publication has been
carried into any other slot of either record.** In particular, none of the U2OS figures (5,147
proteins, 275 assemblies, 36,842 interactions, 20,660 images, 111 heterodimeric structures, 772
paediatric tumours) appears anywhere in these records, and the cell lines recorded are MDA-MB-468 and
KOLF2.1J only. The referent is held identically in the full and core records.

## Phase 3 — Source and provenance audit

### Provenance boundary

Factual inputs read during this run, and nothing else:

- `data/preprocessed/concatenated/CM4AI_preprocessed.txt` (the declared bundle)
- `data/preprocessed/source_manifest.yaml`
- `src/data_sheets_schema/schema/data_sheets_schema_all.yaml` (class `Dataset`)
- `src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml` (class `CoreDataset`)
- `src/data_sheets_schema/d4d_pair_consistency.py` (validator behaviour, not evidence)
- Repository instructions: `.claude/agents/d4d-provenance-guard.md`,
  `.claude/commands/d4d-full-core.md`, `.claude/commands/d4d-agent.md`,
  `src/download/prompts/d4d_generic_arm_prompt.md`

**No prior full or core D4D record was read, opened, grepped or consulted**, from any arm, label or
date. Nothing under `data/d4d_concatenated/` was read other than this run's own two outputs, and
nothing under `data/d4d_individual/` or `data/ro-crate_packages/` was read at all. No prior-D4D
content was inherited from the launching conversation. No live web content was fetched. Phase 2 read
exactly the same-run Phase 1 full record at the path carrying this run's version label, after that
file had passed both schema and term validation.

### Structure

Both records' structures were derived at runtime from the schemas with LinkML `SchemaView`, not from
any example record. Two schema facts changed the shape of the output and are worth recording:

- `Person`-ranged single-valued slots (`Creator.principal_investigator`,
  `EthicalReview.contact_person`, `LicenseAndUseTerms.contact_person`,
  `ExportControlRegulatoryRestrictions.governance_committee_contact`) are **not** inlined, because
  `Person.id` is a required identifier. They therefore carry an identifier string, not a nested
  object. ORCID URIs are used where the bundle supplies one; the person's name, email and affiliation
  are stated in the containing object's narrative slot, which is the only place the schema permits
  them.
- `d4d:docExample` annotations were not consulted for values. Every value traces to the bundle.

### Evidence checks run against the bundle

An automated trace check confirmed that every identifier and figure in the full record appears
literally in the declared bundle:

| Class of value | Distinct values checked | Not found in bundle |
|---|---|---|
| MD5 checksums | 31 | 0 |
| ORCIDs | 38 | 0 |
| DOIs | 9 | 0 |
| Email addresses | 6 | 0 |
| File names | 21 | 0 |
| Numeric literals ≥ 3 digits | all | 0 |

(31 distinct MD5s across 34 file entries: the three IF image archives carry identical checksums in
the June 2025 and October 2025 releases.)

### Source disagreements found, and how each is represented

Every one is represented rather than silently resolved; each is recorded in `source_caveats` on the
object it affects, and the top-level `source_caveats` carries the run-wide list.

1. **June 2026 release date.** The CM4AI data-releases page displays "Released on: June 17, 2025";
   the Dataverse citation metadata for the same DOI gives Publication Date 2026-06-17 and a 2026
   citation year; the manifest curation note adds a version-2 release time of 2026-07-15T20:28:19Z,
   consistent with the three IF archives being published on Jul 15, 2026. `issued` uses the
   repository's own value (2026-06-17); `distribution_dates` records 2026-06-17 and
   2026-07-15T20:28:19Z; the page's 2025 rendering is reported in `source_caveats` and as an
   `errata` entry, not as a release date.
2. **Version labelling.** Each Dataverse landing page header disagrees with the version token in the
   same page's citation string (1.4/V1, 2.1/V2, 2.1/V2, 2.0/V2). `version` carries the header value;
   the citation token is recorded in each resource's `source_caveats`.
3. **Immunofluorescence protein counts.** 563 (March 2025 file descriptions), 464 (June 2025,
   October 2025, June 2026 file descriptions) and 523 (flagship-datasets page). All three are
   recorded as separate scoped `instances`; none was chosen over the others.
4. **TNBC perturb-seq gene count.** 200 genes (flagship-datasets page) versus 100 chromatin
   regulators (CM4AI preprint, Year-1 status May 2024). Both stated on the same `Instance`, with the
   temporal scope of each made explicit.
5. **Project end date.** NIH RePORTER gives 2026-08-31; the Dataverse Maintenance Plan says "the end
   of the project in November 2026". Both reported, on `collection_timeframes` and `updates`.
6. **Collaborating institution list.** The data-releases page includes UT Austin; the Dataverse
   release descriptions give the same list without it. Both reported.
7. **Affiliation of Sali A.** UCSD in the Dataverse author block, UCSF in the CM4AI preprint. Both
   organizations recorded on that creator, with the disagreement noted.
8. **Copyright year.** 2025 on the Dataverse releases, 2024 in the preprint, for the same two
   copyright statements. Both years stated in `ip_restrictions.restrictions`.
9. **Checksum divergence under identical filenames.** The three IF archives share MD5s between the
   June 2025 and October 2025 releases but differ in the June 2026 release. Recorded as a
   `DataAnomaly` with all six checksums and both publication dates.
10. **Dataverse "Data Creation Date".** All four releases report 2025-02-27 creation and deposit
    dates and the same depositor, including the release published 2026-06-17. Recorded as found,
    with the oddity stated and no explanation invented.
11. **UVA affiliation rendering.** The June 2026 capture renders University of Virginia affiliations
    as the bare identifier `https://ror.org/0153tk833`; the 2025 captures spell the name out for the
    same authors. Treated as one organization carrying both forms (`id` + `name`), with the
    resolution disclosed.
12. **Marquez C ORCID.** Printed without the `https://orcid.org/` prefix on every capture; normalised,
    with the normalisation disclosed on that creator.

### Deliberate omissions (evidence absent)

Left unset rather than inferred: `total_size_bytes` and every `File.bytes` (Dataverse displays only
rounded sizes such as "3.8 GB", and the portal's "21.4 TB" is not resolvable to a byte count);
`hipaa_compliant` and `confidentiality_level` (never mentioned); `at_risk_populations`,
`informed_consent`, `collection_consents`, `collection_notifications`, `consent_revocations`,
`participant_privacy`, `participant_compensation` (release metadata records Human Subjects: No and
the bundle gives no consent documentation); `imputation_protocols`, `annotation_analyses`,
`variables`, `splits`, `subsets`, `relationships`, `is_tabular`, `dialect`, `language`,
`discouraged_uses` (nothing stated); top-level `doi` and `version` (the programme has neither — each
release carries its own); repository accession identifiers (the bundle gives link labels only).

The May 2024 release is recorded as a resource with only what the bundle supports — DOI, title,
citation form and archive listing — and its `source_caveats` states that no landing-page capture
exists for it. The June 2025 capture paginates at 10 of 21 files; only the 10 shown are enumerated,
and `total_file_count` remains 21 with the gap disclosed.

### Shape audit

Checked and corrected in Phase 3 before reconciliation:

- Prose removed from list-valued slots: `regulatory_restrictions` reduced to `Not FDA regulated`
  with the attribution moved to `description`; `MachineAnnotationTools.tools` reduced to tool names
  with the roles moved to `tool_descriptions`; `DatasetBias.affected_subsets` reduced to subset names.
- Commentary removed from identifier-ish values: parenthetical annotations stripped out of
  `ExternalResource.external_resources` entries and relocated to the surrounding narrative or
  `source_caveats`; composite date-plus-comment strings removed from
  `DistributionDate.release_dates`.
- `IntendedUse.use_category: research` removed — a category the bundle does not state.
- Evidence commentary relocated from `description`, `access_details`, `review_details`,
  `retention_details`, `impact_details` and `repository_details` into `source_caveats` on the same
  object, in eleven places.
- Structured slots checked for prose displacement: every `Creator` carries `affiliations` as
  `Organization` objects; every `FundingMechanism` carries `Grant` objects with `grant_number`;
  every `Software` carries `name`, and `version`/`url`/`license` where the bundle supplies them;
  every `File` carries `format`, `media_type`, `compression`, `md5` and `file_type` rather than
  describing them.
- No `notes` slot is used in the full record; `description` holds the narrative throughout.
- No enum value outside its schema-declared permissible values (confirmed by schema validation).
- `data_topic` IRIs are taken verbatim from the ontology mappings the Dataverse keyword blocks
  publish beside the corresponding keywords.

### Back-porting from Phase 2

**None required.** Phase 2 derived core from `CoreDataset` and re-checked every core-eligible slot
against the bundle. It found no fact the full record had missed and no value the bundle contradicts.
The core-only slots `dialect` and `is_tabular` remain unset because the bundle describes no tabular
structure. Consequently no correction flowed from core back to full, and the full record required no
change on this account.

### Validation after Phase 3 corrections

```bash
poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_all.yaml -C Dataset \
  data/d4d_concatenated/claudecode_agent/2026-08-07_claude-opus-5-claudecode-generic-v3_rep1/CM4AI_d4d.yaml
# No issues found

poetry run linkml-term-validator validate-data \
  data/d4d_concatenated/claudecode_agent/2026-08-07_claude-opus-5-claudecode-generic-v3_rep1/CM4AI_d4d.yaml \
  --schema src/data_sheets_schema/schema/data_sheets_schema_all.yaml --target-class Dataset
# Validation passed

poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml -C CoreDataset \
  data/d4d_concatenated/claudecode_agent_core/2026-08-07_claude-opus-5-claudecode-generic-v3_rep1/CM4AI_d4d_core.yaml
# No issues found

poetry run linkml-term-validator validate-data \
  data/d4d_concatenated/claudecode_agent_core/2026-08-07_claude-opus-5-claudecode-generic-v3_rep1/CM4AI_d4d_core.yaml \
  --schema src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml --target-class CoreDataset
# Validation passed
```

## Phase 4 — Strict full/core reconciliation

### Shared slots

Derived at runtime from `Dataset` and `CoreDataset` with LinkML `SchemaView` by
`data_sheets_schema.d4d_pair_consistency`. No hand-written field list was used.

- **Schema-identical slots: 78.** Every one has identical presence and deeply identical parsed YAML
  content in both records, including narrative fields. Nothing was condensed, paraphrased, reordered
  or omitted to make core shorter.
- **Projected slots: 1** — `resources` (`Dataset` in full, `CoreDataset` in core).

### Populated slot counts

| | Full | Core |
|---|---|---|
| Top-level populated slots | 62 | 58 |
| Total populated slot instances (recursive) | 1221 | 1110 |
| Resources (releases) | 5 | 5 |
| File entries | 34 (in 12 `file_collections`) | 34 (as `distributions`) |
| Lines (informational only, not a quality gate) | 2486 | 1996 |

### Full-only content, and where it went

Four top-level slots exist in `Dataset` and not in `CoreDataset`, so they are absent from core by
schema, not by choice:

| Full-only slot | Content | Disposition |
|---|---|---|
| `citation` | Data citation for the current release plus the required article citation | The citation requirement itself is stated in `license_and_use_terms.license_terms`, which **is** shared and deeply identical. The formatted citation string has no core home. |
| `related_datasets` | The two bioRxiv preprints (`is_described_by`) | The CM4AI project preprint is named in `license_and_use_terms.license_terms` and the perturbation-atlas preprint in `existing_uses.examples`, both shared slots. |
| `third_party_sharing` | `is_shared: true` plus the distribution route | The same facts are carried by `raw_data_sources`, `distribution_formats` and `description`, all shared. |
| `direct_collection` | `is_direct: false` plus cell-line sourcing | The same facts are carried by `acquisition_methods` (`was_reported_by_subjects: false`) and `human_subject_research`, both shared. |

Two resource-level slots are likewise full-only: `total_file_count` and `file_collections`. Their
content is carried into core as described below.

No fact is present in core that is absent from both the full record and the bundle.

### Projection: `resources`

Matched by `id`; coverage is equal — the same five DOIs in the same order, none extra, none missing:

| `id` | Release |
|---|---|
| `https://doi.org/10.18130/V3/DXWOS5` | May 2024 |
| `https://doi.org/10.18130/V3/B35XWX` | March 2025 (Beta) |
| `https://doi.org/10.18130/V3/F3TD5R` | June 2025 (Beta) |
| `https://doi.org/10.18130/V3/K7TGEM` | October 2025 (Beta) |
| `https://doi.org/10.18130/V3/HIGT4C` | June 2026 (Beta) |

For every matched pair, all nested schema-identical slots (`name`, `title`, `description`, `doi`,
`page`, `version`, `issued`, `last_updated_on`, `publisher`, `license`, `status`, `created_by`,
`created_on`, `source_caveats`) are deeply identical. Full-only nested slots are omitted from the
core projection, as the playbook requires.

### Related content: `file_collections` → `distributions`

The full record holds file inventories inside each release resource as `FileCollection` objects with
nested `File` objects. `CoreDataset` has no `file_collections` and no nesting, so each release's
files are flattened into `CoreDistribution` entries on the matching core resource. 12 collections
containing 34 files map to 34 distributions — a complete, one-to-one, order-preserving mapping with
no unmatched entries on either side.

Semantic review of every related field, performed per file rather than in aggregate:

- **Names and paths.** Identical strings on both sides. `File.path` includes the Dataverse folder
  prefix (for example `Images/cm4ai_ifimages_MDA-MB-468_paclitaxel.zip`), so the collection grouping
  survives the flattening in the path itself.
- **Formats and media types.** `format` and `media_type` copied unchanged; both slots use the same
  `FormatEnum` and `MediaTypeEnum` in the two schemas. No conflict.
- **Compression.** `compression` copied unchanged. Where a `FileCollection` also declared
  `compression: zip`, every file it contained already declared the same value, so flattening
  introduces no disagreement.
- **Checksums.** All 34 `md5` values copied unchanged and re-verified against the bundle. The three
  IF archives whose checksums differ between the June 2026 release and the two earlier ones keep
  their per-release values in both records; the divergence is documented identically in both, via
  the shared `anomalies` slot.
- **Byte counts and file counts.** `File.bytes` and `FileCollection.total_bytes` are unset
  throughout because the bundle publishes only rounded display sizes, so there is no
  `bytes` / `total_bytes` comparison to make and none can conflict. Resource-level
  `total_file_count` (6, 21, 8, 10) has no core counterpart; the core `distributions` lists hold 6,
  10, 8 and 10 entries respectively, and the June 2025 shortfall is the paginated capture already
  disclosed in that resource's `source_caveats`, which is shared and identical in both records.
- **Access URLs and release scope.** Access URLs live in the shared `distribution_formats` slot and
  are deeply identical. Each file's release scope is fixed by which resource it hangs from, and that
  assignment is identical on both sides.
- **Collection-level semantics.** The narrative that a `FileCollection` carried in its own
  `description` — the folder's role, and the 563- versus 464-protein imaging descriptions — has no
  container in core once flattened. It is preserved verbatim in each `CoreDistribution.notes`,
  prefixed with the grouping name. This is the one place `notes` is used in either record, and it
  holds content `description` cannot: the parent grouping's semantics, not a restatement of the
  file's own description. `CoreDistribution.description` remains byte-identical to the corresponding
  `File.description`.
- **Dropped field.** `File.file_type` (`FileTypeEnum`) has no `CoreDistribution` counterpart, so
  archive/metadata/documentation typing is full-only. It contradicts nothing in core; `format` and
  `media_type` carry the machine-readable part of the same information into core.

### Cross-record consistency of repeated facts

Checked in both directions and found consistent:

- Top-level `license` (`https://creativecommons.org/licenses/by-nc-sa/4.0/`) agrees with every
  resource-level `license`, with `license_and_use_terms.license_terms`, and with the license deed
  document in the bundle.
- Top-level `last_updated_on` (2026-07-15T20:28:19Z) equals the `last_updated_on` of the current
  release resource (HIGT4C) and nothing later appears on any other resource.
- `version_access.latest_version_doi` (`https://doi.org/10.18130/V3/HIGT4C`) matches the
  most-recently-issued resource, and `version_access.versions_available` enumerates exactly the five
  resource `id`s.
- `updates.frequency: Quarterly` agrees with the four release dates (2025-03-03, 2025-07-01,
  2025-10-31, 2026-06-17) and with the FAQ text.
- `publisher` is the same Dataverse instance at top level and on every resource.
- `human_subject_research.involves_human_subjects: false`,
  `is_deidentified.identifiable_elements_present: false`,
  `sensitive_elements.sensitive_elements_present: false`,
  `confidential_elements.confidential_elements_present: false`,
  `subpopulations.subpopulation_elements_present: false` and
  `acquisition_methods.was_reported_by_subjects: false` are mutually consistent and all trace to the
  same Data Governance & Ethics block plus the preprint's tissue-culture statement.
- Historical versus current release facts are distinguished rather than treated as contradictions:
  the March 2025 release's older `v0.6-beta` filenames, 563-protein imaging and absent governance
  block are scoped to that release; the June 2026 release's AP-MS archives are scoped as first
  appearing there.

### Commands run in Phase 4

```bash
poetry run python -m data_sheets_schema.d4d_pair_consistency \
  --full data/d4d_concatenated/claudecode_agent/2026-08-07_claude-opus-5-claudecode-generic-v3_rep1/CM4AI_d4d.yaml \
  --core data/d4d_concatenated/claudecode_agent_core/2026-08-07_claude-opus-5-claudecode-generic-v3_rep1/CM4AI_d4d_core.yaml \
  --sync-core
# PASS: 78 schema-identical slots; projected slots=['resources']

poetry run python -m data_sheets_schema.d4d_pair_consistency \
  --full data/d4d_concatenated/claudecode_agent/2026-08-07_claude-opus-5-claudecode-generic-v3_rep1/CM4AI_d4d.yaml \
  --core data/d4d_concatenated/claudecode_agent_core/2026-08-07_claude-opus-5-claudecode-generic-v3_rep1/CM4AI_d4d_core.yaml
# PASS: 78 schema-identical slots; projected slots=['resources']
```

Both files were re-validated against their schemas and the term validator after synchronisation; all
four checks pass.

### Files changed

- `.../claudecode_agent/2026-08-07_.../CM4AI_d4d.yaml` — written in Phase 1; corrected in Phase 3
  (26 edits: shape fixes, evidence-commentary relocation, source-disagreement disclosures, RFC3339
  datetime normalisation, non-inlined `Person` references). Unchanged by Phase 4.
- `.../claudecode_agent_core/2026-08-07_.../CM4AI_d4d_core.yaml` — written in Phase 2 from the
  bundle plus the validated same-run full record; regenerated after the Phase 3 corrections;
  synchronised once in Phase 4, which also appended `# Phase 4 reconciliation: completed` to its
  header.
- `.../claudecode_agent_core/2026-08-07_.../CM4AI_reconciliation.md` — this report.

## Outcome

**Reconciled with zero unresolved discrepancies.** The pair validator passes on 78 schema-identical
slots with deep equality and identical presence, `resources` projects one-to-one across five
releases, and the one related-content mapping (`file_collections` → `distributions`, 34 files) was
reviewed field by field with no conflict. The four full-only top-level slots and two full-only
resource-level slots are absent from core by schema rather than by omission, and their content is
either carried by a shared slot or explicitly recorded above as having no core home. The twelve
source disagreements found in Phase 3 are represented rather than resolved, identically in both
records.
