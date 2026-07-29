# CM4AI full/core reconciliation — 2026-07-28_claude-opus-5-programme-deprimed_rep1

- **Project**: CM4AI
- **Arm**: BASELINE (document corpus only)
- **Agent runtime**: Claude Code · **Provider**: Anthropic · **Model**: claude-opus-5[1m]
- **Mode**: four-phase project agent, pinned-referent · **Temperature**: 0.0
- **Generated**: 2026-07-28
- **Full**: `data/d4d_concatenated/claudecode_agent/2026-07-28_claude-opus-5-programme-deprimed_rep1/CM4AI_d4d.yaml`
- **Core**: `data/d4d_concatenated/claudecode_agent_core/2026-07-28_claude-opus-5-programme-deprimed_rep1/CM4AI_d4d_core.yaml`

## Pinned referent

The subject of the record is the **CM4AI data-release programme as an ongoing
quarterly release series**, not any single release. Applied as follows:

1. **Top level = programme.** `id` is `https://cm4ai.org/data-releases/`, the
   programme's data-release page, not a release DOI. No `doi`, `version`,
   `issued`, `total_size_bytes` or `total_file_count` appears at top level.
   Programme-scope facts carried at top level: title, description, `page`,
   `publisher`, `license`, `status`, `conforms_to`, `citation`, `keywords`.
2. **`resources` = the quarterly releases**, one entry each, in date order:
   March 2025 `doi:10.18130/V3/B35XWX` (v1.4, issued 2025-03-03, 6 files);
   June 2025 `doi:10.18130/V3/F3TD5R` (v2.1, issued 2025-07-01, 21 files);
   October 2025 `doi:10.18130/V3/K7TGEM` (v2.1, issued 2025-10-31, 8 files);
   June 2026 `doi:10.18130/V3/HIGT4C` (v2.0, issued 2026-06-17,
   `last_updated_on` 2026-07-15T20:28:19Z, 10 files). Each release carries its
   own `doi`, `version`, `issued`, `total_file_count`, `page`, `license`,
   `publisher`, verbatim Dataverse `citation`, and a `status` marking June 2026
   as current and the other three as superseded.
3. **`file_collections` = the file inventory of the current release (HIGT4C)**,
   ten entries, one per published archive, with `path`, `compression: zip`,
   `issued`, `license`, `status: Public`, and per-file MD5 and displayed size in
   the description.
4. **Modalities live in composition, not in `resources`.** AP-MS, SEC-MS,
   IF imaging and Perturb-seq appear as `instances`, `collection_mechanisms`
   and `file_collections`, never as top-level resources.

### What the programme framing made awkward to place

- **Displayed sizes cannot become byte counts.** The corpus gives file sizes
  only as Dataverse display strings ("3.8 GB", "113.3 KB") and the portal gives
  programme volume only as "21.4 TB". Converting these requires choosing
  decimal or binary units, which the corpus does not state. `total_size_bytes`,
  `FileCollection.total_bytes` and `CoreDistribution.bytes` are therefore
  **omitted everywhere**, and the displayed strings are recorded verbatim in
  descriptions. The same applies to the programme-level "Data Insights" volume,
  which sits in the top-level description rather than in a size slot.
- **`FileCollection` has no checksum or format slot.** The full schema's
  `FileCollection` exposes `path`, `compression`, `collection_type`,
  `file_count`, `total_bytes` and the `Information` slots — but no `md5`,
  `hash`, `format` or `media_type`. Per-file MD5s and formats were therefore
  recorded in the full record only as description text, and carried as
  first-class fields in the **core** record's `distributions`
  (`md5`, `format: ZIP`, `media_type: application/zip`). This is the one place
  the core record is structurally richer than the full record.
- **`Person`, `Organization` and `Grantor` cannot be inlined.** In class
  `Dataset`, `Creator.principal_investigator`, `EthicalReview.contact_person`,
  `EthicalReview.reviewing_organization`,
  `LicenseAndUseTerms.contact_person`,
  `ExportControlRegulatoryRestrictions.governance_committee_contact` and
  `FundingMechanism.grantor` are **not inlined**, so they accept only an
  identifier string. Named individuals (Trey Ideker, Vardit Ravitsky,
  Jillian Parker) and their emails could not be expressed as objects; minted
  identifier strings are used and the underlying facts are carried in the
  neighbouring detail lists. ORCIDs were preserved by using the ORCID URI as
  each `Creator.id`.
- **A fifth release exists that the four-release referent does not cover.**
  The CM4AI project preprint's Data and Software Availability Statement cites
  "Cell Maps for Artificial Intelligence - Data Release",
  `https://doi.org/10.18130/V3/DXWOS5`, V1, and the data-releases page names a
  "May 2024 Data Release" in its Archive list. Neither is one of the four
  pinned releases. Rather than force them into `resources`, DXWOS5 is recorded
  as a `related_datasets` entry with `relationship_type: has_part`, and both
  appear in `version_access.versions_available`. The corpus does not state
  whether DXWOS5 *is* the May 2024 release, and the record does not assert it.
- **Per-release descriptive prose belongs to releases, not to the programme.**
  The structured Data Governance & Ethics / Completeness / Maintenance Plan /
  Intended Use / Limitations / Prohibited Uses / Potential Sources of Bias
  blocks appear on individual release records. They are stable across the June
  2025, October 2025 and June 2026 records, so they were promoted to
  programme-level slots (`anomalies`, `known_biases`, `known_limitations`,
  `intended_uses`, `prohibited_uses`, `updates`, `retention_limit`,
  `human_subject_research`, `regulatory_restrictions`) with the release-record
  provenance stated in the text.

## Phase 3 — source and provenance audit

### Provenance boundary

Factual inputs read during this run:

- `data/preprocessed/concatenated/CM4AI_preprocessed.txt` (10 documents)
- `data/preprocessed/source_manifest.yaml`

Structural inputs: `data_sheets_schema_all.yaml` (class `Dataset`),
`data_sheets_schema_core_all.yaml` (class `CoreDataset`),
`src/data_sheets_schema/d4d_pair_consistency.py`, and the three procedure
documents named in the task.

**No prior full or core D4D record, evaluation, RO-Crate package, reconciliation
report or live web page was read.** Output directory *names* were listed once,
solely to confirm the target version label did not already exist (permitted by
`/d4d-full-core`); no file under `data/d4d_concatenated/` or
`data/d4d_individual/` was opened other than this run's own two outputs. No
prior D4D content from the parent conversation was used. Structure was derived
from the schemas via `SchemaView`, not from any example record; `d4d:docExample`
annotations were not copied.

### Source verification performed

- Every MD5 (27 distinct), ORCID (38 distinct), DOI, RRID, grant number and
  comma-formatted count in both records was matched back to a literal
  occurrence in the source bundle. **All matched.**
- 60 further narrative and numeric claims (file-count strings, version labels,
  publication dates, award amount, project period, contact emails, licence
  clauses, repository notices, software versions) were matched literally.
  **All matched.**
- Both records are pure ASCII: the source's typographic punctuation
  (`’`, `–`) is normalised to ASCII (`'`, `-`) throughout, including inside
  quoted passages. This is a uniform transcription convention, applied
  consistently, and changes no fact.
- `issued` has range `datetime` and rejects date-only values. Dates stated in
  the corpus as calendar dates are recorded as `YYYY-MM-DDT00:00:00Z`; the
  time component is a format requirement, not a claim about time of day. The
  one true timestamp in the corpus, `2026-07-15T20:28:19Z`, is recorded as
  stated on `last_updated_on` of the HIGT4C resource.

### Source conflicts resolved

| # | Conflict | Resolution |
|---|---|---|
| 1 | **HIGT4C release date.** cm4ai.org displays "Released on: June 17, 2025" for the release it labels "June 2026 Data Release (Beta)". Dataverse metadata for `doi:10.18130/V3/HIGT4C` gives Publication Date **2026-06-17**, version 2 released 2026-07-15T20:28:19Z. | **Dataverse is authoritative** (per the task instruction and the manifest's `verification_url`). `issued: 2026-06-17T00:00:00Z`. The website date is recorded as a conflict in the resource's `status` and in `distribution_dates`, not adopted. |
| 2 | **Version label vs citation version.** B35XWX displays "Version 1.4" but its citation cites "V1"; F3TD5R and K7TGEM display "Version 2.1" but cite "V2". | Both recorded. `version` takes the Dataverse page label; the citation string is preserved verbatim in `citation`; the divergence is stated in each resource's `status` and in `version_access.version_details`. |
| 3 | **Project end date.** NIH RePORTER gives Project end **2026-08-31**; the release records' Maintenance Plan says augmentation continues "through the end of the project in **November 2026**". | Neither preferred — they describe different things (funded project period vs maintenance commitment). Both recorded in `collection_timeframes`, with the discrepancy stated. |
| 4 | **Collaborating institutions.** The data-releases page lists UCSD, UCSF, Stanford, UVA, Yale, **UT Austin**, UA Birmingham, SFU, Hastings Center; the Dataverse release descriptions give the same list **without UT Austin**. | Both recorded in the project-team `Creator` description; the affiliation list follows the release author list, which does include a UT Austin author. |
| 5 | **Sali A affiliation.** Dataverse release author list: University of California San Diego. CM4AI project preprint: University of California San Francisco. | Dataverse (the release metadata) used for `affiliations`; the preprint's differing affiliation noted in that creator's description. |
| 6 | **Ravitsky V affiliation vs contact.** Author list gives University of Montreal; the Ethical Review contact email is at the Hastings Center. | Both recorded; affiliation follows the author list, the contact email is preserved in `ethical_reviews`. |
| 7 | **Copyright year.** Release records say "Copyright (c) 2025 The Regents of the University of California"; the preprint says 2024. Dataverse page footers say 2025 (March/June 2025 captures) and 2026 (October 2025/June 2026 captures). | All recorded in `ip_restrictions`, each scoped to the source that states it. Not a contradiction — different release years. |
| 8 | **Website staleness on "coming soon" items.** cm4ai.org states "AP-MS interactomes (coming soon!)" for TNBC datasets, but the June 2026 release ships AP-MS archives for treated MDA-MB-468 cells. | The release record wins; the website text is recorded in `missing_data_documentation` as older than the June 2026 release. |
| 9 | **Data Creation / Deposit Date 2025-02-27 on all four releases.** | Recorded, with the explicit note that these values are repeated unchanged on later release records and therefore do not date those releases' contents. |
| 10 | **Production Location on B35XWX lists "University of California San Francisco" twice.** | Recorded verbatim as a source artefact in `data_collectors`. |

### Scope corrections applied (mis-scoping avoided)

The corpus contains one document that is *about CM4AI investigators' science but
not about the released data*: the Nature 2025 study "Multimodal cell maps as a
foundation for structural and functional genomics", which measures **U2OS
osteosarcoma cells** (5,147 proteins, 275 assemblies, 111 heterodimer
structures, 21 recurrently mutated assemblies). The CM4AI quarterly releases
contain **MDA-MB-468 and KOLF2.1J** data. Every use of that paper carries an
explicit scope note and it is placed in `existing_uses`, `external_resources`,
`annotation_analyses`, `machine_annotation_tools` and `cleaning_strategies` —
never in `instances`, `file_collections` or any composition slot.

Similarly, Year-1 status figures from the May 2024 project preprint (17 tagged
genes, 72/100 chromatin modifiers, >1,000 complexes, >700 iPSC complexes) are
labelled as preprint-stage snapshots and are **not** asserted as the composition
of any release.

### Corrections back-ported to the full record during Phase 3

Four corrections were made to the full record first, then re-derived into core:

1. Removed `language: en`. The corpus never declares a language for the data,
   and the released artefacts are ZIP archives of images and mass-spectrometry
   output. Unsupported assertion removed.
2. Removed `"Medicine, Health and Life Sciences"` from `keywords`. It is the
   Dataverse **Subject** field, not a keyword; conflating the two fields
   misreports the source. Moved to the top-level description as a Subject
   statement.
3. Strengthened `acquisition_methods.was_validated_verified: true` with
   release-scoped evidence — the March 2025 CRISPR Perturbation Cell Atlas
   states "We validated these findings via phenotypic, protein-interaction, and
   metabolic tracing assays" — rather than resting on the U2OS-scoped and
   in-progress QC statements alone.
4. Replaced the abbreviated author form "Schaffer LV, Hu M, Qian G" with the
   names as the source states them, and normalised the Nature citation to
   "Nature volume 642, pages 222-231 (2025)" in both places it appears.

### Phase 2 discoveries back-ported

Phase 2 found **no fact present in the sources but missing from the full
record**. The only content core carries that full does not is per-file `md5`,
`format` and `media_type`, which have no full-schema slot (see above); the
underlying values were already present in the full record's file-collection
descriptions, so no back-port was required.

## Phase 4 — strict full/core reconciliation

### Schema-derived shared slots

Derived at runtime with `SchemaView` over `Dataset` and `CoreDataset` — no
hand-written field list.

- **Schema-identical slots: 76.** Present in both or neither, deeply identical
  parsed content including nested mappings and list order. Narrative fields are
  **not** condensed, paraphrased, reordered or truncated in core.
- **Projected slots: 1** (`resources`, `Dataset` in full vs `CoreDataset` in
  core). Matched by `id`, equal coverage across all four releases, deep identity
  on every schema-identical nested slot. Full-only nested slots
  (`total_file_count`, `citation`) are correctly absent from the core
  projection.

### Full-only slots and where their content goes

| Full slot | Core status | Disposition |
|---|---|---|
| `file_collections` | no core equivalent | Related content, mapped to `distributions` — reviewed below |
| `citation` | not in `CoreDataset` | Full-only; release citations remain on full's `resources` |
| `relationships` | not in `CoreDataset` | Full-only |
| `direct_collection` | not in `CoreDataset` | Full-only; overlapping evidence also appears in `acquisition_methods`, which *is* shared and identical in both |
| `third_party_sharing` | not in `CoreDataset` | Full-only; the external repositories it names also appear in `external_resources`, which is shared and identical |
| `related_datasets` | not in `CoreDataset` | Full-only; the DXWOS5 release also appears in `version_access.versions_available`, which is shared and identical |

Content was **not** duplicated into shared slots to compensate, because shared
slots must stay deeply identical to full.

### Related-content semantic review (`file_collections` ↔ `distributions`)

The validator's `semantic-review-required` warning marks this work; it does not
perform it. Reviewed for all 10 pairs:

- **Coverage**: 10 file collections ↔ 10 distributions, ids identical, no
  unmatched item in either direction. Matches the HIGT4C resource's
  `total_file_count: 10`.
- **Names and paths**: identical in every pair.
- **Compression**: `zip` in both; consistent with `format: ZIP`,
  `media_type: application/zip` in core and with the corpus's "ZIP Archive".
- **Checksums**: each core `md5` is corroborated by the same MD5 appearing in
  the matched full collection's description. All 10 distinct; all verified
  against the source bundle.
- **Byte counts**: neither record asserts one. `total_bytes` and `bytes` are
  absent from every pair, so no scope mismatch is possible. Displayed sizes are
  stated identically in both descriptions.
- **Access**: `status: Public` and the CC BY-NC-SA licence on every full
  collection; `CoreDistribution` has no access or licence slot, so there is
  nothing to conflict.
- **Release scope**: every id is namespaced under `doi:10.18130/V3/HIGT4C`;
  both records describe the file inventory of the current release only, and both
  say so in the descriptions.
- **`dialect` / `is_tabular`**: `dialect` is omitted (no tabular distribution to
  describe); `is_tabular` is omitted from both records because the corpus does
  not state it — presence therefore matches.

### Cross-record identity, version and access consistency

- `license` is the single value `https://creativecommons.org/licenses/by-nc-sa/4.0/`
  at top level and on all four releases.
- `publisher` is `https://dataverse.lib.virginia.edu/` at top level and on all
  four releases.
- `version_access.latest_version_doi` = `https://doi.org/10.18130/V3/HIGT4C` =
  the one resource whose `status` marks it current; the other three are marked
  superseded.
- `distribution_dates.release_dates` agree with each resource's `issued`, and
  `version_access.versions_available` file counts agree with each resource's
  `total_file_count` (6 / 21 / 8 / 10).
- Historical releases are represented as superseded releases with explicit
  scope, not as contradictions of the current release.

### Commands run

```bash
FULL=data/d4d_concatenated/claudecode_agent/2026-07-28_claude-opus-5-programme-deprimed_rep1/CM4AI_d4d.yaml
CORE=data/d4d_concatenated/claudecode_agent_core/2026-07-28_claude-opus-5-programme-deprimed_rep1/CM4AI_d4d_core.yaml

poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_all.yaml -C Dataset $FULL
poetry run linkml-term-validator validate-data $FULL \
  --schema src/data_sheets_schema/schema/data_sheets_schema_all.yaml --target-class Dataset
poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml -C CoreDataset $CORE
poetry run linkml-term-validator validate-data $CORE \
  --schema src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml --target-class CoreDataset
poetry run python -m data_sheets_schema.d4d_pair_consistency --full $FULL --core $CORE --sync-core
poetry run python -m data_sheets_schema.d4d_pair_consistency --full $FULL --core $CORE
```

### Final results

| Check | Result |
|---|---|
| Full — LinkML schema validation (`Dataset`) | **No issues found** |
| Full — ontology term validation | **Validation passed** |
| Core — LinkML schema validation (`CoreDataset`) | **No issues found** |
| Core — ontology term validation | **Validation passed** |
| Pair consistency with `--sync-core` | **PASS** — 76 schema-identical slots, projected `resources` |
| Pair consistency, independent re-run | **PASS** — 76 schema-identical slots, projected `resources` |
| Related-content semantic review | **Completed**, 10/10 matched, 0 unresolved contradictions |
| Files changed after sync | none — the pre-sync core already satisfied identity; sync appended the Phase 4 header only |

Full: 2,560 lines (63 top-level slots). Core: 1,732 lines (58 top-level slots).
Line counts are informational metadata, not a quality gate.

### Provenance record

```bash
poetry run d4d provenance record --project CM4AI --method claudecode_agent \
  --label 2026-07-28_claude-opus-5-programme-deprimed_rep1 \
  --input-bundle data/preprocessed/concatenated/CM4AI_preprocessed.txt
```

Wrote `CM4AI_provenance.yaml` in this directory with `record_mode: live`,
agent runtime Claude Code, provider Anthropic, model `claude-opus-5[1m]`,
input bundle md5 `3694e188106bbf8b1871d44450925e9a`, and output hashes and
slot counts for both records.

The core header contains `Phase 4 reconciliation: completed`, and both headers
state `Prior D4D factual reuse: prohibited`.
