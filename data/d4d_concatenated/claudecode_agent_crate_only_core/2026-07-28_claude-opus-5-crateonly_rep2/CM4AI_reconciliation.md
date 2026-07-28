# CM4AI full/core reconciliation — crate-only arm, rep2

| | |
|---|---|
| Project | CM4AI |
| Arm | CRATE-ONLY (single structured source, no documents) |
| Run label | `2026-07-28_claude-opus-5-crateonly_rep2` |
| Agent runtime | Claude Code |
| Provider | Anthropic |
| Model | `claude-opus-5[1m]` |
| Mode | four-phase project agent, crate-only |
| Temperature | 0.0 |
| Generated | 2026-07-28 |

**Files**

- Full: `data/d4d_concatenated/claudecode_agent_crate_only/2026-07-28_claude-opus-5-crateonly_rep2/CM4AI_d4d.yaml`
- Core: `data/d4d_concatenated/claudecode_agent_crate_only_core/2026-07-28_claude-opus-5-crateonly_rep2/CM4AI_d4d_core.yaml`
- Provenance: `data/d4d_concatenated/claudecode_agent_crate_only_core/2026-07-28_claude-opus-5-crateonly_rep2/CM4AI_provenance.yaml` (`record_mode: live`)

**Sole factual input**

- `data/preprocessed/concatenated/CM4AI_crate_only.txt` — two artifacts:
  `CM4AI_crate_metadata_reduced.json` (62 `@graph` entries) and `ai_ready_score.json`.

Structure references only (never factual sources): `data_sheets_schema_all.yaml`
(class `Dataset`), `data_sheets_schema_core_all.yaml` (class `CoreDataset`),
`D4D_Core.yaml`.

---

## Referent chosen

**`https://fairscape.net/api/ark:59853/rocrate-cell-maps-for-artificial-intelligence-June-2026-data-release`**
— "Cell Maps for Artificial Intelligence - June 2026 Data Release (Beta)", version 1.0,
DOI `https://doi.org/10.18130/V3/HIGT4C`, published 2026-06-30.

Why this referent and not "the CM4AI project": the crate's own root descriptor
(`ro-crate-metadata.json`) declares `about` → this ARK, so the crate asserts that it
describes the June 2026 release, not the project. The release entity is also the only
entity in the graph that carries release-scoped identity (DOI, publisher, version,
`evi:*` totals, full author list, funders). The nine other `EVI#ROCrate` entities are its
components; the crate places them `isPartOf` the release, so they are modelled as the
release's `resources` rather than as alternative referents. The `isPartOf` links pointing
*up* from the release (`organization-…-university-of-california-san-diego`,
`project-cell-maps-for-artificial-intelligence`) are organization and project entities,
not datasets, and have no D4D `Dataset`-range home; they were not used.

---

## Phase 3 — source and provenance audit

### Provenance boundary

- Factual reads in this run: the crate bundle above, and (in Phase 2 onward) the exact
  same-run Phase 1 full record. Nothing else.
- No prior full or core D4D record, evaluation, reconciliation report, RO-Crate D4D
  mapping (`CM4AI_crate_d4d.yaml`, `ro-crate-linkml.yaml`), datasheet rendering, project
  corpus (`CM4AI_preprocessed*.txt`), individual/raw source directory, source manifest, or
  live web content was opened.
- No parent-conversation D4D content was used as evidence.
- Structure was derived at runtime with `SchemaView` over `Dataset` / `CoreDataset`; no
  `d4d:docExample` value was copied.

### Within-crate consistency findings

These are properties of the crate, surfaced by the audit. None was silently repaired.

1. **Two non-equivalent total-size figures.** The release states `contentSize: "19.9 TB"`
   and `evi:totalContentSizeBytes: 21051331945400`. 21051331945400 B is 21.05 TB decimal
   or 19.15 TiB binary; neither equals 19.9 TB. The 19.9 TB figure does reconcile with the
   sum of the nine component `contentSize` strings (≈19.88 TB). **Correction applied in
   Phase 3:** the full record's `distribution_formats` originally rendered these as one
   value ("19.9 TB (21051331945400 bytes)"); it now reports both figures separately and
   states that they are not numerically equivalent. `total_size_bytes` carries the exact
   integer `21051331945400` only.
2. **Component `rai:dataCollectionType` is release-level boilerplate.** Both EndoTag AP-MS
   component crates list `"Perturb-seq; IF imaging; SEC-MS"` — omitting AP-MS, which is
   what they contain. The release-level value (`"Perturb-seq; IF imaging; SEC-MS; AP-MS"`)
   is the correct-scope value and is the one recorded in `acquisition_methods`.
3. **Component `citation` strings are stale.** Every component crate inside the June 2026
   release cites the *March 2025* Data Release (DOIs `10.18130/V3/K7TGEM`,
   `10.18130/V3/B35XWX`). Only the release-level citation (which correctly names the June
   2026 release and DOI `10.18130/V3/HIGT4C`) was recorded, at the top level. Component
   citations were deliberately not copied into `resources`.
4. **Malformed `isPartOf` identifiers.** Component `isPartOf` arrays contain ARK strings
   with a trailing comma (`…-June-2026-data-release,`) alongside the well-formed ARK. Not
   used.
5. **Inconsistent author-string spelling.** `…rocrate-sra-data-for-perturbation-cell-atlas`
   lists `"Idkeker T"` where the sibling Perturb-Seq crate lists `"Ideker T"`. Both are
   preserved verbatim in their respective `resources[].creators`; neither was normalized.
6. **Ethical-review name spelling.** `ethicalReview` reads "Vardit Ravistky"; the Person
   entity reads "Ravitsky, V" (ORCID 0000-0002-7080-8801). The D4D `creators` entry uses
   the Person-entity spelling; the `ethical_reviews.review_details` quotes the
   `ethicalReview` string verbatim, so both spellings survive.
7. **Mixed date formats.** Release `datePublished` is `2026-06-30`; two AP-MS components
   and the KOLF2 SEC-MS component use ISO 8601 timestamps; the three IF components use
   `02/28/2025`. All are preserved verbatim as `distribution_dates.release_dates` strings.
   `issued` (LinkML `datetime`) was left empty rather than inventing a time component for
   the date-only release value.
8. **Self-containment tension.** `ai_ready_score.json` describes the package as "a
   self-contained RO-Crate, a standard designed for portability", while the component
   entities point at external hosts (MassIVE, FigShare, Dataverse, FTP). **Correction
   applied in Phase 3:** `external_resources.description` no longer asserts "not
   self-contained"; it states the linking fact and quotes the crate's own portability
   claim alongside it.
9. **Cross-artifact agreement (no conflict).** `ai_ready_score.json` and the crate JSON-LD
   agree on: 47 authors, 53877 datasets, 1976 computations, 6 software, 20 schemas,
   8/55859 entities with checksums, 19.9 TB, DOI `10.18130/V3/HIGT4C`, PI Trey Ideker,
   publisher `https://dataverse.lib.virginia.edu/`, licence CC BY-NC-SA 4.0.

### Interpretive steps taken (disclosed, not silent)

- **PI identity.** `principalInvestigator: "Trey Ideker"` (a bare string) was linked to the
  author `Ideker, T` / ORCID `0000-0002-1708-8454`. Recorded on that `creators` entry with
  the linkage stated in its `description`.
- **Institution-name variants merged.** "University of California, San Diego" ≡ "University
  of California San Diego", and "The University of Alabama at Birmingham" ≡ "University of
  Alabama at Birmingham". "University of Alabama" (Payne-Foster) was kept distinct.
- **Licence enum.** `data_use_permission: no_commercial_use` is read off the licence URI
  `…/licenses/by-nc-sa/4.0/`. No other permission enum was asserted.
- **Ontology-term placement.** Of the crate's 13 `about` terms, four were attached to
  `instances` where the release description ties a modality to a substrate: EDAM RNA-Seq +
  Cellosaurus KOLF2.1J (perturb-seq), EDAM Proteomics + KOLF2.1J (SEC-MS), EDAM Proteomics
  + MDA-MB-468 (AP-MS), MeSH Fluorescent Antibody Technique + MDA-MB-468 (IF).
- **Minted identifiers.** `Organization`, `Grantor`, `Grant`, and the Jilian Parker
  `Person` require an `id` the crate does not supply. Local, clearly non-authoritative URIs
  were minted under
  `https://w3id.org/bridge2ai/data-sheets-schema/cm4ai/june-2026-release/…`. No ARK or ROR
  identifier was fabricated. Names are carried in `name`, so no crate fact depends on a
  minted id.

### Phase 2 discoveries back-ported into full

A fresh pass over the bundle while building core surfaced three `ai_ready_score.json`
statements the Phase 1 extraction had not used. All three are source-supported and were
written into the full record first (Phase 3, step 4), then propagated to core in Phase 4:

| # | Fact | Full slot |
|---|---|---|
| D1 | "a self-contained RO-Crate, a standard designed for portability across systems" | `external_resources[0].description` |
| D2 | "All data, software, and computations are explicitly linked within the RO-Crate's provenance graph." | `preprocessing_strategies[1].preprocessing_details` |
| D3 | JSON-LD is machine-readable and publicly accessible by design; documentation via JSON-LD, an HTML datasheet, and Croissant RAI properties | `distribution_formats[1].description` |

No fact present in core was absent from both the full record and the crate.

---

## Phase 4 — strict full/core reconciliation

- Shared slots derived at runtime with `SchemaView`: **76 schema-identical**, **1 projected**
  (`resources`). No hand-written field list was used.
- Pre-sync check found exactly **one** divergence — `distribution_formats[2].description`,
  the Phase 3 size-figure correction that had not yet reached core (`shared-slot-content`).
  This is the expected signature of "full corrected first, then propagate".
- `--sync-core` copied the 76 identical slots and re-projected `resources`; the independent
  re-run passed with zero errors and zero warnings.

### Projected content: `resources`

`resources` is `Dataset` in full and `CoreDataset` in core. All 9 component ids match with
equal coverage:

| # | Component id (suffix of `ark:59853/`) |
|---|---|
| 1 | `rocrate-endotag-ap-ms-in-mda-mb-468-cells-paclitaxel` |
| 2 | `rocrate-endotag-ap-ms-in-mda-mb-468-cells-vorinostat` |
| 3 | `rocrate-untreated-if-data-release` |
| 4 | `rocrate-paclitaxel-if-data-release` |
| 5 | `rocrate-vorinostat-if-data-release` |
| 6 | `rocrate-sec-ms-characterization-of-kolf2-neuronal-and-cardiomyocyte-differentiation-cm4ai-yjftt2oec6c` |
| 7 | `rocrate-data-from-treated-human-cancer-cells-jan-26` |
| 8 | `rocrate-sra-data-for-perturbation-cell-atlas-58RmCGMQBj` |
| 9 | `rocrate-a-perturbation-cell-atlas-of-human-induced-pluripotent-stem-cells` |

Every slot used inside a resource (`id`, `name`, `description`, `version`, `license`,
`doi`, `publisher`, `page`, `download_url`, `keywords`, `creators`, `existing_uses`,
`distribution_dates`, `distribution_formats`) is on the schema-identical list, so the
projection is lossless in this record — nothing was dropped at the resource level. No
resource carries nested `resources`.

### Related, non-identical representations

- **`file_collections` ↔ `distributions`: absent from both, deliberately.** The crate's
  file inventories are collapsed in this bundle (`hasPart` reduced to
  `{_summarized_by: "d4d rocrate normalize", count, id_families, sample_ids}`), so no
  per-file path, format, byte count, or checksum is available. `FileCollection` also
  requires an `id` the crate does not supply per file. Emitting core `distributions`
  without full `file_collections` is a hard error in the pair validator, so neither side
  emits them. Consequence: the six **crate-level MD5 checksums** (components 3, 4, 5, 7, 8,
  9) have no home in the full `Dataset` tree — `md5`/`hash`/`sha256` exist only on class
  `File`, which is unreachable from `Dataset`. They are preserved verbatim inside the
  matching `resources[].distribution_formats[].description` so the evidence is not lost.
  This is a **schema representation gap**, not a source gap.
- **`total_file_count` vs component counts.** Left empty. `evi:datasetCount` (53877) counts
  *dataset entities in the provenance graph*, not files; equating them would be an
  inference. The counts are recorded as `instances` with explicit `instance_type` wording
  instead.
- **`total_size_bytes` vs distribution-level sizes.** Only the exact integer
  `21051331945400` is asserted. Component sizes are strings with 3–4 significant figures
  ("441.2 GB", "16.7TB"); converting them to `integer` would invent precision, so they are
  carried verbatim in `resources[].distribution_formats[].description`. See finding 1 for
  the release-level discrepancy.
- **`dialect`, `is_tabular`, formats.** `dialect` (core-only) and `is_tabular` are empty in
  both: the crate reports a heterogeneous format list (`.d`, `.tsv`, `.xml`, `csv`,
  `fastq.gz`, `h5`, `h5ad`, `image/jpeg`, `pdf`, `executable`, `unknown`) and never states
  that the release is tabular or gives a CSV dialect. No conflict.
- **Identity / version / access agreement.** DOI, version `1.0`, publisher, licence,
  copyright, conditions of access, confidentiality level, prohibited uses, ethical review,
  governance contact, and maintenance plan agree across `license_and_use_terms`,
  `ip_restrictions`, `regulatory_restrictions`, `version_access`, `updates`, `maintainers`,
  and the top-level scalars, in both records. Historical scope is kept explicit:
  `version_access.version_details` records that components carry independent version labels
  and membership in the earlier October 2025 / January 2026 releases; those are not treated
  as contradicting the June 2026 release values.

**Unresolved contradictions within or between the two records: none.**

---

## Primary result — what the crate could NOT support

This is the finding the arm exists to produce. 42 of the 94 induced `Dataset` slots are
empty; below they are grouped by whether the crate is silent, or the schema has nowhere to
put what the crate says.

### A. D4D areas with *no* crate support at all

| D4D area | Empty slots | Note |
|---|---|---|
| **Labeling & annotation** (entire module) | `labeling_strategies`, `annotation_analyses`, `machine_annotation_tools` | The crate never mentions annotation, annotators, protocols, or inter-annotator agreement. |
| **Cleaning & imputation** | `cleaning_strategies`, `imputation_protocols` | `rai:dataCollectionMissingData` states *that* data are missing; nothing states how missingness is handled. |
| **Data splits & subsets** | `splits`, `subsets` | No train/validation/test guidance, no defined subsets, despite the release being marketed as "AI-ready". |
| **Sampling** | `sampling_strategies` | No statement about whether the release is a sample of a larger population, nor representativeness. |
| **Variable-level metadata** | `variables` | 20 schemas are *counted* (`evi:schemaCount`) but none is described; no variable name, type, unit, or range is available. |
| **Consent machinery** | `collection_notifications`, `collection_consents`, `consent_revocations`, `participant_privacy`, `participant_compensation`, `direct_collection`, `retention_limit` | Genuinely inapplicable — the crate states no human subjects. But the crate gives no explicit negative for these either, so they are left empty rather than answered "N/A". |
| **Data protection impact** | `data_protection_impacts` | No DPIA statement. |
| **Errata & extension** | `errata`, `extension_mechanism` | No errata channel, no contribution mechanism, despite a quarterly update cadence. |
| **Use tracking** | `use_repository`, `other_tasks`, `discouraged_uses` | 4 associated publications are listed (→ `existing_uses`), but no registry of downstream use, no "other tasks", and no discouraged-use statement distinct from the prohibited-use clause. |
| **Content warnings & subpopulations** | `content_warnings`, `subpopulations` | No statement either way. |
| **Anomalies** | `anomalies` | No statement of errors, noise, or redundancy. The 8/55859 checksum coverage is recorded as an `instances` count, not silently reclassified as an anomaly. |
| **Lineage** | `parent_datasets`, `related_datasets`, `was_derived_from` | The crate references earlier releases only through component `isPartOf` strings (some malformed) and stale component citations. Asserting "June 2026 is a new version of March 2025" is not supported; left empty. |

### B. Crate says it, but the schema has nowhere to put it

| Crate content | Why it is unrepresented |
|---|---|
| Six component **MD5 checksums** | `md5`/`hash`/`sha256` live only on class `File`, unreachable from `Dataset`; `FileCollection` has no checksum slot. Carried as prose in `resources[].distribution_formats[].description`. |
| Nine component **`contentSize`** strings | Only `integer` byte slots exist; the crate gives rounded strings. Carried as prose. |
| Nine of the 13 **`about` subject terms** (MeSH Breast Neoplasms, Induced Pluripotent Stem Cells, CRISPR-Cas Systems, Mass Spectrometry, Paclitaxel, Vorinostat; EDAM Functional genomics, Machine learning) | `Dataset` has no subject/topic slot; the only ontology-term slots are `Instance.data_topic` / `data_substrate` / `VariableMetadata.unit`. Four terms were placed on `instances`; the rest have no home. |
| Release **`isPartOf`** organization and project ARKs | `parent_datasets` has range `Dataset`; an organization and a project are not datasets. |
| Release **`datePublished: 2026-06-30`** in `issued` | `issued` is LinkML `datetime` and rejects a date-only value; recorded as a `distribution_dates.release_dates` string instead. |
| Repository names **"MassIVE" / "FigShare"** at release level | Recorded on the two components whose crates state them (`publisher`); the release itself names only the Dataverse. |

### C. Areas the crate supports *well* (for contrast)

Licensing and copyright, conditions of access, prohibited uses, confidentiality level,
human-subjects exemption, ethical-review contacts, data-governance contact, funders and
grant numbers, the 47-person author roster with ORCIDs and affiliations, collection
timeframe, collection modalities, missing-data documentation, biases, limitations,
maintenance and preservation plan, versioning, associated publications, intended uses, and
the nine-component resource inventory. The Croissant `rai:*` block is what carries most of
the Motivation / Uses / Collection answers; without it this arm would be far thinner.

---

## Commands run

```bash
poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_all.yaml -C Dataset \
  data/d4d_concatenated/claudecode_agent_crate_only/2026-07-28_claude-opus-5-crateonly_rep2/CM4AI_d4d.yaml

poetry run linkml-term-validator validate-data \
  data/d4d_concatenated/claudecode_agent_crate_only/2026-07-28_claude-opus-5-crateonly_rep2/CM4AI_d4d.yaml \
  --schema src/data_sheets_schema/schema/data_sheets_schema_all.yaml --target-class Dataset

poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml -C CoreDataset \
  data/d4d_concatenated/claudecode_agent_crate_only_core/2026-07-28_claude-opus-5-crateonly_rep2/CM4AI_d4d_core.yaml

poetry run linkml-term-validator validate-data \
  data/d4d_concatenated/claudecode_agent_crate_only_core/2026-07-28_claude-opus-5-crateonly_rep2/CM4AI_d4d_core.yaml \
  --schema src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml --target-class CoreDataset

poetry run python -m data_sheets_schema.d4d_pair_consistency \
  --full data/d4d_concatenated/claudecode_agent_crate_only/2026-07-28_claude-opus-5-crateonly_rep2/CM4AI_d4d.yaml \
  --core data/d4d_concatenated/claudecode_agent_crate_only_core/2026-07-28_claude-opus-5-crateonly_rep2/CM4AI_d4d_core.yaml \
  --sync-core

poetry run python -m data_sheets_schema.d4d_pair_consistency \
  --full data/d4d_concatenated/claudecode_agent_crate_only/2026-07-28_claude-opus-5-crateonly_rep2/CM4AI_d4d.yaml \
  --core data/d4d_concatenated/claudecode_agent_crate_only_core/2026-07-28_claude-opus-5-crateonly_rep2/CM4AI_d4d_core.yaml

poetry run d4d provenance record --project CM4AI --method claudecode_agent_crate_only \
  --label 2026-07-28_claude-opus-5-crateonly_rep2 \
  --input-bundle data/preprocessed/concatenated/CM4AI_crate_only.txt
```

## Final results

| Check | Result |
|---|---|
| Full — schema validation | **PASS** (`No issues found`) |
| Full — ontology term validation | **PASS** |
| Core — schema validation | **PASS** (`No issues found`) |
| Core — ontology term validation | **PASS** |
| Pair consistency (pre-sync) | 1 error: `shared-slot-content` at `$.distribution_formats[2].description` |
| Pair consistency (post-sync, independent) | **PASS** — 76 schema-identical slots, 1 projected slot, 0 errors, 0 warnings |
| Provenance record | present, `record_mode: live` |

Informational metadata (not a quality gate): full 1287 lines / 52 of 94 `Dataset` slots
populated; core 1102 lines / 48 of 79 `CoreDataset` slots populated; 9 resources in both.
