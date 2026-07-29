# CM4AI full/core reconciliation — 2026-07-27_claude-opus-5_rep1

Arm: **de novo WITH CRATE** (document corpus + RO-Crate evidence)

| Field | Value |
|---|---|
| Agent runtime | Claude Code |
| Provider | Anthropic |
| Model | claude-opus-5[1m] |
| Mode | four-phase project agent |
| Temperature | 0.0 |
| Generated | 2026-07-27 |
| Full record | `data/d4d_concatenated/claudecode_agent_crate/2026-07-27_claude-opus-5_rep1/CM4AI_d4d.yaml` |
| Core record | `data/d4d_concatenated/claudecode_agent_crate_core/2026-07-27_claude-opus-5_rep1/CM4AI_d4d_core.yaml` |
| Factual input | `data/preprocessed/concatenated/CM4AI_preprocessed_with_crate.txt` (11,647 lines, 490 KB) |
| Full schema | `data_sheets_schema_all.yaml`, class `Dataset` |
| Core schema | `data_sheets_schema_core_all.yaml`, class `CoreDataset` |

---

## Headline result: the CM4AI crate is almost entirely redundant with the documents

The arm note predicted the CM4AI crate would add little beyond the document corpus,
because the Dataverse release pages and the crate render the same underlying
governance record. That prediction is confirmed for the *narrative governance*
fields and refuted for a small, specific set of *structured* fields.

Every one of the following crate fields is byte-for-byte or near-byte-for-byte
identical to text already present on the Dataverse release pages in the document
bundle, and therefore contributed **nothing**:

`rai:dataLimitations`, `rai:dataBiases`, `rai:dataUseCases` (except one clause,
below), `rai:dataReleaseMaintenancePlan`, `rai:dataCollectionMissingData`,
`completeness`, `prohibitedUses`, `usageInfo`, `ethicalReview`,
`humanSubjectResearch`, `dataGovernanceCommittee`, `conditionsOfAccess`,
`license`, `identifier`, `name`, `description`, `keywords`.

The crate's real contribution is a short list of structured facts that the
Dataverse pages do not carry at all. That list is enumerated below and it is
short — which is the correct, expected outcome for this project.

---

## Per-field attribution: crate-only vs documents

### A. Populated ONLY from crate evidence (no document support)

| Full-record location | Value | Crate source |
|---|---|---|
| `total_size_bytes` | `21051331945400` | `evi:totalContentSizeBytes` |
| `conforms_to` | `https://w3id.org/ro/crate/1.2` | `ro-crate-metadata.json` → `conformsTo` |
| `conforms_to_schema` | `https://w3id.org/EVI#` | crate `@context` EVI namespace |
| `collection_timeframes[0].start_date` / `.end_date` | `2022-09-01` / `2026-06-01` | `rai:dataCollectionTimeframe` |
| `collection_timeframes[0].description` | per-modality end dates 2025-10-13 and 2026-01-31 | component-crate `rai:dataCollectionTimeframe` |
| `funders` — DoD, CIRM, NWO, and NIH grants R01HG012351, R01NS131560, U54CA274502, S10 OD026929, NCI P30CA023100 | grant numbers | crate root `funder` string |
| `regulatory_restrictions.confidentiality_level` | `unrestricted` | `confidentialityLevel: "Unrestricted"` |
| `human_subject_research.irb_approval[0]` | the exemption wording | `humanSubjectExemption` |
| `informed_consent[0].description` | the "not applicable" wording | `d4d:informedConsent` |
| `at_risk_populations.description` | the "None — no human subjects involved" wording | `d4d:atRiskPopulations` |
| `intended_uses.usage_notes` — the Ma 2018 (PMID 29505029) / Kuenzi 2020 (PMID 33096023) clause | PMIDs | `rai:dataUseCases` (this clause is absent from the Dataverse pages) |
| `known_limitations` — sparse-checksum limitation | 8 of 55,859 entities carry checksums | `evi:entitiesWithChecksums`, `evi:totalEntities`, `ai_ready_score.json` |
| `anomalies` — entity/computation/software/schema counts | 53,877 / 1,976 / 6 / 20 | `evi:*Count` fields |
| `resources` — all 9 component datasets: ARK ids, MassIVE accessions MSV000100676 / MSV000098237 / MSV000101915 / MSV000101917, DOI 10.25345/C5348GV4S, per-component contentSize, CC0 licensing of the MS sub-crates, component `datePublished`, component authors (Richa Tiwari, Antoine Forget) | whole block | component crate entities |
| `external_resources` — FAIRSCAPE root ARK id, `fairscapeVersion` 1.1.3, Figshare URL `https://figshare.com/s/ee85bb1880921326249b`, MassIVE FTP URL | identifiers | crate root + components |
| `data_collectors` — named per-modality contributors and contact emails (`emmalu@stanford.edu`, `nevan.krogan@ucsf.edu`, `pmali@ucsd.edu`) | contacts | component crate `contactEmail` / `author` |
| `instances` — MeSH `data_topic` CURIEs (D005453, D013058, D064113) | ontology terms | crate `about` DefinedTerm entities |
| `instances[cell lines]` — Cellosaurus CVCL_0419 / CVCL_B5P3 | *corroborating only* | crate `about`; the preprint already gives RRID:CVCL_0419 and RRID:CVCL_B5P3 |
| `distribution_formats` (technical) — the `evi:formats` list | format inventory | `evi:formats` |
| `anomalies` — crate/Dataverse version and date divergences | see below | comparison of crate against pages |

**Count: roughly 20 field groups populated only from the crate, out of ~70
populated slots.** Everything else came from the documents.

Two of these deserve emphasis because they are the only *substantive new dataset
facts*, as opposed to packaging metadata: the **data collection timeframe**
(2022-09-01 to 2026-06-01) and the **full funder list** (DoD W81XWH-22-1-0401,
CIRM EDUC4-12804, NWO 019.231EN.013, and five additional NIH awards). The
document corpus records only NIH 1OT2OD032742-01 and 5U54HG012513-02.

### B. Populated ONLY from documents (crate silent or less specific)

- The entire scientific and methodological body: cell-mapping definition, MuSIC
  pipeline stages, AP-MS / SEC-MS / IF / CRISPRi protocols, the 100-chromatin-
  modifier and 100-metabolic-enzyme design, endogenous tagging progress,
  DenseNet-121 / node2vec / HiDeF / DIA-NN / Sequest / CompPASS specifics,
  annotation jamborees, GPT-4 GSAI naming and its confidence statistics.
  Source: bioRxiv preprint and the Nature paper. The crate carries none of this
  beyond a pointer to the preprint.
- Cell-line provenance and donor demographics (MDA-MB-468 from a 51-year-old
  Black female with metastatic mammary adenocarcinoma; KOLF2.1J from a healthy
  male Northern European donor, HipSci, simple MTA). Preprint only.
- All four release histories with their DOIs, versions, publication dates, file
  inventories, and MD5s. Dataverse pages only — the crate's own file-level MD5s
  are *stale* (see anomalies).
- Project structure (three pillars, six modules), Teaming, Skills and Workforce
  Development, CodeFest attendance figures, DEI committee, U-BRITE portal.
- Portal statistics (1,374 protein interactions; 53,788 IF images; 7,023
  proteins; 11,739 genes; 21.4 TB).
- The CC BY-NC-SA 4.0 clause-level terms, the commercial-relicensing route
  (UCSD / Stanford / UCSF), the Data Access Committee, the Bridge2AI Code of
  Conduct, the BSD-3 / MIT software licensing.
- NIH RePORTER award facts (application 11211616, award $5,289,382, project
  period 2022-09-01 to 2026-08-31).
- The "repository under review for potential modification" notice.

### C. Both, in agreement

Every governance narrative listed in the headline section. Where the crate and
the pages state the same thing, the page wording was used because it is the
primary distribution surface; the crate wording is identical.

---

## Phase 3 — source and provenance audit

### Provenance boundary

Confirmed. The only factual input read was
`data/preprocessed/concatenated/CM4AI_preprocessed_with_crate.txt`. Structure was
derived from `data_sheets_schema_all.yaml`, `data_sheets_schema_core_all.yaml`,
and `D4D_Core.yaml` via LinkML `SchemaView`. `source_manifest.yaml` and
`crate_manifest.yaml` were read for selection/structure context only.

No prior D4D record, evaluation, or reconciliation report was opened. Nothing
under `data/d4d_concatenated/` or `data/d4d_individual/` was read other than the
two outputs of this run. **The withheld artifacts — `CM4AI_crate_d4d.yaml`,
`CM4AI_crate_mapped_d4d.yaml`, `ro-crate-linkml.yaml`, `ro-crate-datasheet.html`,
and any `ro-crate-preview.html` — were not read, globbed, opened, or cited.** No
live web content was fetched.

### Data-quality warnings handled as instructed

- **`compression` mis-population.** The reduced crate JSON in this bundle carries
  no `compression` field at all (verified by grep), so the mis-populated values
  never entered the record. `compression: zip` in both records is taken from the
  Dataverse file table, which lists all ten release items as *ZIP Archive*. The
  crate's `evi:formats` list (which does contain `pdf`, `image/jpeg`, `h5ad`) was
  used only in `distribution_formats`, explicitly labelled as a format inventory,
  never as a compression value.
- **ORCID-reference creators.** The crate's `author` array is mostly bare ORCID
  references. Names were resolved from the `Person` entities in the same crate
  graph and cross-checked against the Dataverse author lists. No name was taken
  from model memory.

### Four Dataverse releases kept distinct

| Release | DOI | Dataverse version | Publication date | Files |
|---|---|---|---|---|
| March 2025 (Beta) | 10.18130/V3/B35XWX | 1.4 | 2025-03-03 | 6 |
| June 2025 (Beta) | 10.18130/V3/F3TD5R | 2.1 | 2025-07-01 | 21 |
| October 2025 (Beta) | 10.18130/V3/K7TGEM | 2.1 | 2025-10-31 | 8 |
| **June 2026 (Beta) — current** | **10.18130/V3/HIGT4C** | **2.0** | **2026-06-17** | **10** |

The record's identity fields describe HIGT4C. The other three appear only in
`version_access`, `distribution_dates`, `related_datasets`, and `errata`, each
with explicit historical scope. Release-specific facts are never merged: the
563-protein image panel is attributed to March 2025 and the 464-protein panel to
June 2025 onward; AP-MS data are attributed to June 2026 as the first release
containing them.

### Corrections applied during Phase 3

1. **Misused `Instance.counts`.** `counts: 464` (proteins imaged) and
   `counts: 11739` (genes targeted) were removed — neither is an instance count.
   Both numbers were retained in the surrounding descriptions. `counts: 2` on the
   cell-line instance is correct and kept.
2. **`data_substrate` removed** from all instances. The slot asks for a data
   *substrate* from Bridge2AI standards; the only ontology terms in evidence are
   MeSH and EDAM *topics*. `data_topic` was kept, `data_substrate` dropped rather
   than filled with a topic term.
3. **`publisher` on four MassIVE-hosted resources** was changed from the
   per-accession query URL to `https://massive.ucsd.edu/` (the crate's own
   `publisher` value for these components is the string "MassIVE"). The
   accession-specific URL was kept in `page` / `download_url`.
4. **Scope collision between `total_file_count` and `total_size_bytes`.** These
   two figures come from different scopes: 10 files is the Dataverse deposit,
   21,051,331,945,400 bytes is the whole release including MassIVE, Figshare, and
   sequence-archive components. Rather than drop either, a paragraph was added to
   the top-level `description` stating both scopes explicitly, and both figures
   were retained. The ten Dataverse archives sum to roughly 12.7 GB.
5. **Manifest-only values removed.** `total_bytes: 1203765` and the Dataverse file
   id 120750 for `cm4ai_release_metadata.zip` originated in
   `crate_manifest.yaml`, which this run treats as a selection reference rather
   than a fact source. Both were dropped; the release page's "1.1 MB" was kept.
6. **May 2024 release identification softened.** The CM4AI archive index names a
   "May 2024 Data Release"; the preprint cites DOI 10.18130/V3/DXWOS5 for "Cell
   Maps for Artificial Intelligence - Data Release", V1. No source states that
   these are the same deposit, so the record now marks the identification as
   inferred.
7. **Nature-paper funders deliberately excluded.** The Schaffer et al. 2025
   acknowledgments name Schmidt Futures, the Cancer Cell Map Initiative,
   Cytoscape/NDEx programs, CFI/Genome BC, Wallenberg, Göran Gustafsson, Stanford
   HAI, Param Hansa, NIH R01GM083960 / P41GM109824 / U24 HG006673, and several
   companies. Those fund the U2OS study, not this Dataverse release, and were not
   added to `funders`.
8. **U2OS scope firewall.** The Nature paper's dataset (U2OS osteosarcoma cells,
   275 assemblies, NDEx map, MassIVE MSV000097168, ProteomeXchange PXD052362,
   ModelArchive) is a CM4AI-associated resource in a *different cell line* and is
   not part of this release. Every place it is used — `existing_uses`,
   `external_resources`, `related_datasets`, and the method details in
   `collection_mechanisms`, `preprocessing_strategies`, `cleaning_strategies`,
   `labeling_strategies`, `annotation_analyses` — carries an explicit "associated
   U2OS study" scope marker. No U2OS number was attributed to the CM4AI release.

### Internal consistency verified

DOI 10.18130/V3/HIGT4C, version 2.0, publication date 2026-06-17, last update
2026-07-15T20:28:19Z, license CC BY-NC-SA 4.0, publisher UVA Dataverse, PI Trey
Ideker, governance contact Jillian Parker, ethics contacts Ravitsky and
Bélisle-Pipon, and the "no human subjects / de-identified / not FDA regulated"
triple are each repeated in several slots and are identical in every occurrence
in both files.

### Contradictions found in the sources and recorded rather than resolved

These are genuine upstream inconsistencies, captured in `anomalies` and `errata`:

- The CM4AI releases page labels HIGT4C "June 2026" but displays "June 17, 2025";
  Dataverse gives 2026-06-17.
- Dataverse says version 2.0 / V2; the crate root says `version: "1.0"` and
  `datePublished: 2026-06-30`; the crate's own embedded citation says 2025 / V1.
- Several component crates cite the March 2025 (B35XWX) or October 2025 (K7TGEM)
  release rather than the June 2026 release they belong to.
- **The image component crates carry March 2025 file sizes and MD5s.** The
  paclitaxel image crate reports 2.6 GB / MD5 `9422486c80bc9e1d35b2fbbc72a5f043`,
  which is the March 2025 file, while its own description states the 464-protein
  scope of the later releases; the June 2026 Dataverse file is 3.8 GB / MD5
  `6c1a86520eec2696ec19444eb8a8b428`. The Dataverse values were used and the
  crate values recorded as an erratum.
- Several component `isPartOf` URIs are malformed with a trailing comma.
- Crate spells "Jilian Parker" and "Vardit Ravistky"; the pages spell "Jillian
  Parker" and "Vardit Ravitsky". Page spellings used; crate spellings noted.
- `contentSize: "19.9 TB"` versus `evi:totalContentSizeBytes: 21051331945400`
  (21.05 TB decimal / 19.15 TiB binary) versus the portal's "21.4 TB".
- `ai_ready_score.json` self-reports "0% of files have checksums (8/55859)" while
  scoring the verifiability criterion as satisfied.

---

## Phase 4 — strict full/core reconciliation

### Schema-derived shared slots

Derived at runtime with `SchemaView` from `Dataset` and `CoreDataset`:

- **76 schema-identical slots** — must be deeply identical and equally present.
- **1 projected slot** — `resources` (`Dataset` in full, `CoreDataset` in core).
- Full-only: `file_collections`, `total_file_count`, `total_size_bytes`,
  `subsets`, `relationships`, `splits`, `direct_collection`,
  `collection_notifications`, `collection_consents`, `consent_revocations`,
  `participant_privacy`, `participant_compensation`, `third_party_sharing`,
  `variables`, `citation`, `parent_datasets`, `related_datasets`.
- Core-only: `distributions` (`CoreDistribution`), `dialect` (`FormatDialect`).

### Identity check

All 76 identical slots present in both records with deeply equal parsed content,
including every narrative field. Core condenses, paraphrases, reorders, and omits
nothing. Of the 79 `CoreDataset` slots, 73 are populated; the six unpopulated —
`imputation_protocols`, `extension_mechanism`, `conforms_to_class`, `language`,
`modified_by`, `was_derived_from` — are absent from the full record too, because
the sources do not support them (no imputation is performed on these data, no
contribution mechanism is documented, and the release states no natural
language, schema class, or derivation source).

### Projection check — `resources`

9 resources in full, 9 in core, matched by `id` with equal coverage. Every slot
used in the full resources (`id`, `name`, `description`, `version`, `license`,
`issued`, `publisher`, `page`, `download_url`, `doi`, `status`, `keywords`)
exists on `CoreDataset`, so nothing was dropped in projection and every nested
value is deeply identical.

### Related-content review — `file_collections` ↔ `distributions`

The validator flags this pair for mandatory semantic review. Reviewed here:

- **Coverage**: 10 ↔ 10, matched one-to-one by `id`, zero unmatched on either
  side.
- **Names and paths**: identical in every pair.
- **Compression**: `zip` in both, on all ten.
- **Format / media type**: core adds `format: ZIP` and
  `media_type: application/zip`; consistent with the full record's
  `compression: zip` and with the Dataverse "ZIP Archive" file type. No conflict.
- **Checksums**: core carries `md5` structurally on all ten. Each value was
  verified programmatically to appear verbatim inside the corresponding full
  `file_collection.description`, so the pair states the same checksum, in prose
  in the full record and structurally in core. This is the one place core is
  *more* structured than full, which the schema intends: `FileCollection` has no
  checksum slot, `CoreDistribution` does.
- **Byte counts**: omitted in both. Dataverse publishes only rounded sizes
  ("3.8 GB"); no exact byte count is available per file, so none was invented.
  The rounded figures are recorded in the descriptions on both sides.
- **Release scope**: all ten are June 2026 release files; publication dates
  (2026-06-17 for eight, 2026-07-15 for the three image archives) appear in both
  records and agree.
- **`total_file_count` (10) vs distribution count (10)**: same scope, agree.
- **`total_size_bytes` (21.05 TB) vs the distributions**: *different* scopes, as
  documented in Phase 3 correction 4 and stated explicitly in the top-level
  description of both records. Not a contradiction.
- **`is_tabular` / `dialect` / formats**: `is_tabular: false` in both; `dialect`
  omitted in core, which is correct for a non-tabular release; the format
  statements in `distribution_formats` (shared, identical) and in
  `distributions` (core-only) agree.

Zero unresolved contradictions within or between the two records.

### Commands run

```bash
poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_all.yaml \
  -C Dataset data/d4d_concatenated/claudecode_agent_crate/2026-07-27_claude-opus-5_rep1/CM4AI_d4d.yaml

poetry run linkml-term-validator validate-data \
  data/d4d_concatenated/claudecode_agent_crate/2026-07-27_claude-opus-5_rep1/CM4AI_d4d.yaml \
  --schema src/data_sheets_schema/schema/data_sheets_schema_all.yaml --target-class Dataset

poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml \
  -C CoreDataset data/d4d_concatenated/claudecode_agent_crate_core/2026-07-27_claude-opus-5_rep1/CM4AI_d4d_core.yaml

poetry run linkml-term-validator validate-data \
  data/d4d_concatenated/claudecode_agent_crate_core/2026-07-27_claude-opus-5_rep1/CM4AI_d4d_core.yaml \
  --schema src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml --target-class CoreDataset

poetry run python -m data_sheets_schema.d4d_pair_consistency \
  --full data/d4d_concatenated/claudecode_agent_crate/2026-07-27_claude-opus-5_rep1/CM4AI_d4d.yaml \
  --core data/d4d_concatenated/claudecode_agent_crate_core/2026-07-27_claude-opus-5_rep1/CM4AI_d4d_core.yaml \
  --sync-core

poetry run python -m data_sheets_schema.d4d_pair_consistency \
  --full data/d4d_concatenated/claudecode_agent_crate/2026-07-27_claude-opus-5_rep1/CM4AI_d4d.yaml \
  --core data/d4d_concatenated/claudecode_agent_crate_core/2026-07-27_claude-opus-5_rep1/CM4AI_d4d_core.yaml
```

### Final results

| Check | Result |
|---|---|
| Full — schema validation | **No issues found** |
| Full — ontology term validation | **Validation passed** |
| Core — schema validation | **No issues found** |
| Core — ontology term validation | **Validation passed** |
| Pair consistency (final, no `--sync-core`) | **PASS: 76 schema-identical slots; projected slots=['resources']** |
| Remaining validator warnings | 1, `semantic-review-required` on `file_collections ↔ distributions` — reviewed above, 10 deterministic matches, 0 unmatched |

Files changed by this run (both newly created, nothing overwritten):

- `data/d4d_concatenated/claudecode_agent_crate/2026-07-27_claude-opus-5_rep1/CM4AI_d4d.yaml` — 2,706 lines
- `data/d4d_concatenated/claudecode_agent_crate_core/2026-07-27_claude-opus-5_rep1/CM4AI_d4d_core.yaml` — 1,879 lines

Line counts are informational metadata, not a quality gate. The core record is
shorter than the full record solely because it lacks the 17 full-only slots and
because it was serialized programmatically at a wider line width — not because
any shared content was condensed.

---

## Notes for the arm comparison

1. **The crate did not change the shape of this record.** Every major D4D section
   was populated from the documents; the crate refined roughly 20 field groups
   and added exactly two substantive new dataset facts (collection timeframe and
   the full funder list). A near-empty crate-only column was the predicted
   outcome and it is what happened.
2. **The crate's structured metrics are its real value, and they are unverified.**
   `evi:totalContentSizeBytes`, the entity counts, and the ARK/MassIVE/Figshare
   identifiers are things a document corpus simply cannot supply. But the crate's
   own self-assessment concedes that 8 of 55,859 entities carry checksums, and
   its file-level MD5s for the image archives are demonstrably stale.
3. **`variables` is empty in both records.** The crate reports
   `evi:schemaCount: 20`, so twenty data dictionaries exist, but the reduced crate
   JSON in this bundle does not carry their column definitions. A future run with
   the schema entities expanded would be able to populate `variables` from
   crate-only evidence — currently the single largest unfilled section.
4. **The crate is one release behind itself in places.** Component crates cite
   earlier release DOIs and carry earlier file checksums. Any deterministic
   crate-to-D4D mapping that trusts component-level `contentSize`, `MD5`, or
   `citation` will produce a record that describes March 2025 while claiming to
   describe June 2026.
