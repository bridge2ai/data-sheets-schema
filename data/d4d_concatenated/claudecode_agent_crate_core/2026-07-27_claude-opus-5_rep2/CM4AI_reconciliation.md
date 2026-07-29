# CM4AI full/core reconciliation — 2026-07-27_claude-opus-5_rep2

**Arm:** DE NOVO WITH CRATE (documents + RO-Crate evidence)
**Agent runtime:** Claude Code · **Provider:** Anthropic · **Model:** claude-opus-5[1m]
**Mode:** four-phase project agent · **Temperature:** 0.0 · **Generated:** 2026-07-27

| Artifact | Path |
|---|---|
| Full | `data/d4d_concatenated/claudecode_agent_crate/2026-07-27_claude-opus-5_rep2/CM4AI_d4d.yaml` |
| Core | `data/d4d_concatenated/claudecode_agent_crate_core/2026-07-27_claude-opus-5_rep2/CM4AI_d4d_core.yaml` |
| Report | `data/d4d_concatenated/claudecode_agent_crate_core/2026-07-27_claude-opus-5_rep2/CM4AI_reconciliation.md` |

**Allowed factual input (sole source of dataset facts):**
`data/preprocessed/concatenated/CM4AI_preprocessed_with_crate.txt` (11,647 lines; 10 documents +
`CM4AI_crate_metadata_reduced.json` + `ai_ready_score.json`).

**Structure/selection references (not fact sources):** `data_sheets_schema_all.yaml` (class
`Dataset`), `data_sheets_schema_core_all.yaml` (class `CoreDataset`), `D4D_Core.yaml`,
`data/preprocessed/source_manifest.yaml`, `data/ro-crate_packages/crate_manifest.yaml`.

---

## Phase 1 — Full record

Structure was derived at runtime from the LinkML schema with `SchemaView`
(`class_induced_slots('Dataset')` plus the induced slots of every nested class range and every
enum used). No prior D4D record, HTML rendering or `d4d:docExample` was consulted.

Three schema facts that shaped the record and were established by inspection, not assumption:

- Single-valued object slots (`Creator.principal_investigator`, `FundingMechanism.grantor`,
  `EthicalReview.contact_person`, `EthicalReview.reviewing_organization`,
  `LicenseAndUseTerms.contact_person`,
  `ExportControlRegulatoryRestrictions.governance_committee_contact`) are **not inlined**; they
  take an identifier string. The first draft inlined them and failed validation. The person and
  organization detail those objects would have carried was moved into the sibling `description`,
  `review_details`, `license_terms` and `other_compliance` fields so no evidence was lost.
- `DatasetBias` has only `bias_type`, `bias_description`, `mitigation_strategy`,
  `affected_subsets`. `scope_impact` and `recommended_mitigation` belong to `DatasetLimitation`
  only; the first draft used them on biases and failed validation.
- `dialect` exists on `CoreDataset` but **not** on `Dataset`. It is omitted from both records
  because the release is not tabular (`is_tabular: false`).

Objects whose `id` is schema-required but for which no external identifier exists in the sources
(Organizations other than UVA, Grantors, Grants, the governance-committee Person) carry
record-local IRIs minted under `https://w3id.org/bridge2ai/data-sheets-schema/CM4AI/…`. No
external identifier (ROR, ORCID, ARK, DOI) was invented; every ORCID, ARK, DOI and MassIVE
accession in the record is quoted from a source.

---

## Phase 2 — Core record

`CoreDataset` field inventory derived from `D4D_Core.yaml` and the merged core schema. The core is
the exchange-layer subset of the Phase 1 full record: 66 of the 76 schema-identical slots are
populated (the other 10 are unpopulated in both records), plus the `resources` projection and the
core-only `distributions`.

Four slots present in full are absent from `CoreDataset` and were correctly dropped:
`citation`, `related_datasets`, `relationships`, `third_party_sharing`. Within each projected
resource, `file_collections`, `total_file_count` and `citation` were dropped.

**Core-only enrichment.** `CoreDistribution` carries `md5`, `format`, `media_type` and `bytes`,
which `FileCollection` does not. Each core release resource therefore carries a `distributions`
list mirroring the full record's `file_collections` one-for-one, with the Dataverse MD5 checksums
promoted from the full record's `FileCollection.description` prose into the structured `md5`
field, and `format`/`media_type` set from the file extension (ZIP/`application/zip`,
JSON/`application/json`, HTML/`text/html`). Every one of those checksums is quoted from the
Dataverse file listings in the source bundle, so no fact enters core that is not in the full
record and the sources.

Phase 2 found nothing that the Phase 1 extraction had missed or got wrong, so no back-port to full
was required from this phase.

---

## Phase 3 — Source and provenance audit

### Provenance

- Every factual input path is on the allowlist. The only file read for dataset facts was
  `data/preprocessed/concatenated/CM4AI_preprocessed_with_crate.txt`.
- No prior D4D record, evaluation or reconciliation report was read. Nothing under
  `data/d4d_concatenated/` or `data/d4d_individual/` was opened other than this run's own outputs.
  A sibling agent's `CHORUS_d4d.yaml` exists in the same output directory and was not read.
- The five deliberately withheld crate artifacts (`CM4AI_crate_d4d.yaml`,
  `CM4AI_crate_mapped_d4d.yaml`, `ro-crate-linkml.yaml`, `ro-crate-datasheet.html`, any
  `ro-crate-preview.html`) were not read, globbed, or cited. No live web content was fetched.

### Corrections applied to the full record in Phase 3

1. **Added anomaly — institutional collaboration list.** The CM4AI data-releases page lists
   "UCSD, UCSF, Stanford, UVA, Yale, **UT Austin**, UA Birmingham, Simon Fraser University, and
   the Hastings Center"; the March 2025 release description and the June 2026 crate root
   description give the same list *without* UT Austin (verified: 3 occurrences of the short form,
   1 of the long form in the bundle). The preprint lists University of Texas at Austin among
   author affiliations, so the short list is an omission. The record uses the longer,
   preprint-corroborated list and documents the discrepancy.
2. **Added the CM4AI Data Insights counters** (1,374 protein interactions; 53,788 IF images;
   7,023 proteins investigated; 11,739 genes targeted; 21.4 TB) to `external_resources`, scoped
   explicitly as project-level rather than per-release, and noting that 21.4 TB matches neither
   crate total.
3. **Tightened a crate claim.** "the only one in the crate to list AP-MS" → "the only sub-crate
   whose `rai:dataCollectionType` lists AP-MS … the other eight sub-crates omit AP-MS"
   (root entity also lists AP-MS, so the original wording was wrong).

### Source-conflict resolutions recorded rather than silently chosen

| Conflict | Resolution |
|---|---|
| cm4ai.org shows "Released on: June 17, 2025" for HIGT4C; Dataverse gives 2026-06-17 | Dataverse metadata is authoritative for the release record; both recorded, discrepancy in `anomalies`. |
| Crate root `version: "1.0"`, `datePublished: "2026-06-30"` vs Dataverse `2.0` / `2026-06-17` | Dataverse values used for `version`/`issued`; crate values recorded in `anomalies`, `distribution_dates` and `version_access`. |
| Crate `contentSize "19.9 TB"` vs `evi:totalContentSizeBytes 21051331945400` vs site "21.4 TB" | None used as `total_size_bytes`; all three recorded as an anomaly and in the HIGT4C resource description. See scope note below. |
| Sali A at UCSD (all four releases) vs UCSF (Nature) | Release metadata used for the dataset creator list; publication affiliation recorded in the creator `description` and in `anomalies`. |
| Crate citation names Park S and Zhao X, omits Marquez C | Dataverse author list used for `creators`; divergence recorded in `anomalies` and in Marquez's creator description. |
| IF proteins per arm: 563 (Mar 2025) vs 464 (Jun/Oct 2025) vs 523 ("curated" on the website) | All three recorded with explicit release scoping; no single number asserted globally. |

### Scope decisions (deliberate omissions)

- **`total_size_bytes` is not populated anywhere.** The only exact byte figure available
  (21,051,331,945,400) covers the crate's whole logical graph including externally hosted MassIVE,
  Figshare and SRA data, while `total_file_count: 10` on the June 2026 release counts the
  Dataverse-hosted archives (~13 GB). Populating both would have created an internally
  inconsistent count/size pair, so the size is carried as prose in the resource description and in
  `external_resources` with its scope stated. `FileCollection.total_bytes` and
  `CoreDistribution.bytes` are likewise unpopulated because Dataverse reports only rounded display
  sizes ("3.8 GB"); converting those would invent precision.
- **Nature-paper funders excluded.** The Nature acknowledgements list Schmidt Futures, Cytoscape
  5U24HG012107, NDEx 5U24CA269436, CFI/Genome BC 374PRO, Wallenberg 2021.0346, Göran Gustafsson,
  Stanford HAI, Param Hansa, R01GM083960, P41GM109824, NHGRI U24 HG006673, Third Rock, Google
  Ventures, Interline and Xaira. These fund the U2OS cell-map *study*, not the CM4AI data
  releases, and are not in `funders`. U54CA274502 is included only because the crate's own funder
  string lists it for the release.
- **Nature-paper methods excluded from CM4AI method fields.** `preprocessing_strategies`,
  `cleaning_strategies`, `labeling_strategies` and `machine_annotation_tools` are drawn from the
  CM4AI project-description preprint (node2vec, HPA image model, contrastive co-embedding,
  community detection, LLM naming, FAIRSCAPE), not from the U2OS-specific Nature Methods section
  (DIA-NN parameters, HiDeF settings, CompPASS filtering, GSAI/GPT-4-1106-preview), which
  describes a different dataset.
- **The crate's `compression` mis-population does not affect this record.** The known defect
  (compression fields carrying `pdf`, `image/jpeg`, `h5ad`) lives in the withheld
  `ro-crate-linkml.yaml`; the reduced crate JSON in this bundle contains zero occurrences of
  `compression`. Every `compression: zip` in the record comes from the Dataverse file listings
  (`.zip` archives), and the crate's `evi:formats` list is recorded as a *format* inventory in
  `distribution_formats`, explicitly flagged as mixing extensions, media types and an "unknown"
  placeholder.
- **ORCID references resolved, not guessed.** The crate root `author` array is mostly bare ORCID
  `@id` references; the names were resolved from the `Person` entities in the same `@graph` and
  cross-checked against the Dataverse author lists, which agree. Nine authors have no ORCID in
  either source and are recorded with `name` only and an explicit note.

### The four Dataverse releases are kept distinct

| Release | DOI | Dataverse version | Publication date | Files |
|---|---|---|---|---|
| March 2025 (Beta) | 10.18130/V3/B35XWX | 1.4 | 2025-03-03 | 6 |
| June 2025 (Beta) | 10.18130/V3/F3TD5R | 2.1 | 2025-07-01 | 21 (10 enumerated upstream) |
| October 2025 (Beta) | 10.18130/V3/K7TGEM | 2.1 | 2025-10-31 | 8 |
| **June 2026 (Beta) — current** | 10.18130/V3/HIGT4C | 2.0 | 2026-06-17 (v2 released 2026-07-15T20:28:19Z) | 10 |

Each is a separate `resources` entry with its own DOI, version, dates, status, citation, download
metrics and complete file inventory with checksums. Supersession is stated in
`related_datasets` (`is_new_version_of` chain HIGT4C → K7TGEM → F3TD5R → B35XWX → DXWOS5). The
June 2025 release carries an unenumerated-remainder collection (`file_count: 11`) so that
`total_file_count: 21` is not contradicted by the ten files the captured page displays.

---

## Phase 4 — Strict full/core reconciliation

Shared slots derived at runtime by `data_sheets_schema.d4d_pair_consistency` via `SchemaView`:
**76 schema-identical slots**, **1 projected slot** (`resources`: `Dataset` in full,
`CoreDataset` in core). No hand-written field list was used.

- Every schema-identical slot is present in both records or absent from both, with deeply
  identical parsed YAML including nested mapping values and list order. This holds for the long
  narrative fields — core does not condense, paraphrase or reorder any shared content.
- `resources` projection: 4 top-level resources matched by `id` with equal coverage in both
  records; the June 2026 resource's 9 nested modality resources likewise matched recursively.
  Full-only nested slots (`citation`, `total_file_count`, `file_collections`) are absent from the
  core projection — verified programmatically, zero leakage.
- Top-level `file_collections` and `distributions` are both absent by design: files belong to
  releases, not to the CM4AI collection as a whole, so the deterministic distribution-relation
  check returns without a warning. The semantic review of related content was therefore performed
  manually and programmatically at the resource level.

### Related-content semantic review (`file_collections` ↔ `distributions`)

Checked per release for all 35 pairs:

| Release | `file_collections` | `distributions` | id coverage | `name`/`path`/`compression` | `md5` | count vs `total_file_count` |
|---|---|---|---|---|---|---|
| B35XWX | 6 | 6 | identical | identical | identical | 6 = 6 |
| F3TD5R | 11 | 11 | identical | identical | identical | Σ`file_count` 21 = 21 |
| K7TGEM | 8 | 8 | identical | identical | identical | 8 = 8 |
| HIGT4C | 10 | 10 | identical | identical | identical | 10 = 10 |

No conflicts. `bytes`/`total_bytes` are unpopulated on both sides (see scope decision above), so
no size contradiction is possible. `dialect`, format and `is_tabular` agree: `is_tabular: false`
in both records, no `dialect` in core, and `distribution_formats` describes archive/JSON-LD
formats consistent with a non-tabular release.

Top-level identity/version/access facts agree with the resources: top-level `license` equals every
release's `license`; top-level `last_updated_on` equals the current release's `last_updated_on`;
`version_access.latest_version_doi` equals the current release `id` and `doi`; `distribution_dates`
enumerate exactly the four release dates plus the crate date and the two earlier releases. The
historical releases are distinguished from the current one by explicit `status` strings, so their
differing values are historical scope rather than contradiction.

---

## Per-field crate attribution (the primary result of this arm)

### Fields populated ONLY from crate evidence

| Field | Crate-only content |
|---|---|
| `raw_data_sources` | MassIVE accessions **MSV000101915**, **MSV000101917**, **MSV000100676**, **MSV000098237**; MassIVE DOI **10.25345/C5348GV4S**; FTP `ftp://massive-ftp.ucsd.edu/v10/MSV000098237/`; task URL; Figshare item `https://figshare.com/s/ee85bb1880921326249b`. The Dataverse pages carry only unlabelled "MassIVE Repository" / "Figshare" link text. |
| `resources[HIGT4C].resources` (all 9) | The entire per-modality layer: ARK identifiers, titles, descriptions, versions, publication timestamps, per-modality content sizes (441.2 GB, 532.5 GB, 2.6/3.2/2.8 GB, 1.11 TB, 910 GB, 16.7 TB, 177.35 GB), per-modality licences, contacts (`emmalu@stanford.edu`, `nevan.krogan@ucsf.edu`, `pmali@ucsd.edu`), publishers, and the AP-MS author **Richa Tiwari** (a name absent from every document). |
| `funders` (6 of 7 entries) | R01HG012351, R01NS131560, U54CA274502, S10 OD026929, NCI P30CA023100, DoD W81XWH-22-1-0401, CIRM EDUC4-12804, NWO 019.231EN.013. Documents give only 1OT2OD032742-01 / OT2OD032742 / 3OT2OD032742-01S2 / 5U54HG012513-02. |
| `external_resources[0]` | ARK crate PID; `fairscapeVersion 1.1.3`; RO-Crate 1.2 conformance; EVI counters 53,877 datasets / 1,976 computations / 6 software / 20 schemas / 55,859 entities / 8 with checksums / 0 with summary stats; 21,051,331,945,400 bytes; MeSH, EDAM and Cellosaurus subject terms; the six-dimension AI-readiness self-assessment. |
| `distribution_formats[2]` | `evi:formats` inventory (`.d`, `.d directory group`, `.tsv`, `.xml`, `TSV`, `csv`, `executable`, `fastq.gz`, `h5`, `h5ad`, `image/jpeg`, `pdf`, `unknown`). |
| `collection_timeframes` | `rai:dataCollectionTimeframe` 9/1/2022–6/1/2026 and the per-sub-crate variants (1/31/2026, 10/13/25). Documents give only the NIH project period. |
| `informed_consent` | `d4d:informedConsent` — the only explicit consent statement anywhere in the evidence. |
| `at_risk_populations` | `d4d:atRiskPopulations` — likewise. |
| `human_subject_research.regulatory_compliance` | `humanSubjectExemption` wording ("Exempt — research with commercially available de-identified human cell lines does not constitute human subjects research"). Documents state only "Human Subjects: No". |
| `intended_uses` | The "Ma et al. 2018 (PMID 29505029) and Kuenzi et al. 2020 (PMID 33096023)" elaboration of `rai:dataUseCases`. |
| `collection_mechanisms[0]` (AP-MS batch design) | Four biological replicates; untagged parental control + 10 tagged lines + positive control per batch; DMSO vehicle control. |
| `existing_uses` (2 of 4 entries) | Schaffer et al. Nature 2025 and Qin et al. Nature 2021 as **associated publications of the release** (`associatedPublication` on the crate root). Neither appears in the Dataverse Related Publications. |
| `license_and_use_terms` (final term) | CC0 1.0 on the two AP-MS sub-crates and the SEC-MS iPSC sub-crate, against CC BY-NC-SA 4.0 at release level — licence heterogeneity invisible from the documents. |
| `conforms_to` / `conforms_to_schema` | RO-Crate 1.2 profile, EVI + Croissant RAI vocabularies, FAIRSCAPE 1.1.3. Documents say only "RO-Crate format using the FAIRSCAPE framework". |
| `keywords` (2 of 31) | `cell maps`, `CRISPR perturbation`. |
| `anomalies` (6 of 8 entries) | Stale sub-crate MD5s/sizes/dates; crate version/date disagreement; Park S / Zhao X in the crate citation; 8-of-55,859 checksum coverage; 19.9 TB vs 21,051,331,945,400; "Ravistky"/"Jilian" spellings, mixed date formats, trailing-comma identifiers. |

### Fields where the crate is REDUNDANT with the documents

The crate's entire governance and Responsible-AI layer reproduces the Dataverse release pages
**verbatim**, because both render the same underlying metadata record. For these fields the crate
added nothing:

`known_limitations` (`rai:dataLimitations` = the Limitations section), `known_biases`
(`rai:dataBiases` = Potential Sources of Bias), `intended_uses` core list (`rai:dataUseCases` =
Intended Use), `updates` (`rai:dataReleaseMaintenancePlan` = Maintenance Plan),
`missing_data_documentation` (`rai:dataCollectionMissingData` = Completeness),
`prohibited_uses` (`prohibitedUses`/`usageInfo` = Prohibited Uses), `ethical_reviews`
(`ethicalReview` = Ethical Review), `regulatory_restrictions` (`dataGovernanceCommittee`,
`confidentialityLevel`, FDA/human-subjects flags = Data Governance & Ethics),
`license_and_use_terms` main terms (`license`, `conditionsOfAccess`, `copyrightNotice`),
`is_deidentified`, `sensitive_elements`, `confidential_elements`, `retention_limit`,
`rai:dataCollection` (a pointer to the preprint already in the corpus).

Also redundant: `creators` (crate ORCIDs and affiliations match the Dataverse author list),
release identity, DOI, title, description, keywords (29 of 31), publisher, and the Cellosaurus
IDs CVCL_0419 / CVCL_B5P3 (already given as RRIDs in the preprint).

Fields drawn **only** from documents, with no crate contribution: `purposes`, `tasks`,
`addressing_gaps`, `subpopulations` (donor characteristics), `sampling_strategies`,
`preprocessing_strategies`, `cleaning_strategies`, `labeling_strategies`,
`machine_annotation_tools`, `data_collectors` (except Richa Tiwari), `maintainers`,
`extension_mechanism`, `errata`, `version_access`, `distribution_dates`, `use_repository`,
`instances` counts, `future_use_impacts`, `discouraged_uses`, and all four release
`file_collections`.

### Verdict for this arm

The CM4AI crate is **largely redundant** with the document corpus, as expected: its `rai:*` and
governance fields are byte-for-byte the same text that the Dataverse release pages already carry.
Its genuine contribution is narrow but real and falls into four buckets — (1) repository
accessions and per-modality packaging metadata that the release pages hide behind unlabelled
links, (2) an expanded funder list, (3) FAIRSCAPE/EVI provenance and AI-readiness counters, and
(4) a substantial crop of internal inconsistencies that only become visible when the crate is read
against the release pages, most notably that the crate's IF, SEC-MS and perturb-seq sub-crate
checksums, sizes and dates are those of the **March 2025** release carried unchanged into the
**June 2026** package. Nothing in the record was manufactured to make the crate look more
informative than it is.

---

## Commands run

```bash
# Phase 1 / 3 — full record
poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_all.yaml -C Dataset \
  data/d4d_concatenated/claudecode_agent_crate/2026-07-27_claude-opus-5_rep2/CM4AI_d4d.yaml
poetry run linkml-term-validator validate-data \
  data/d4d_concatenated/claudecode_agent_crate/2026-07-27_claude-opus-5_rep2/CM4AI_d4d.yaml \
  --schema src/data_sheets_schema/schema/data_sheets_schema_all.yaml --target-class Dataset

# Phase 2 / 3 — core record
poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml -C CoreDataset \
  data/d4d_concatenated/claudecode_agent_crate_core/2026-07-27_claude-opus-5_rep2/CM4AI_d4d_core.yaml
poetry run linkml-term-validator validate-data \
  data/d4d_concatenated/claudecode_agent_crate_core/2026-07-27_claude-opus-5_rep2/CM4AI_d4d_core.yaml \
  --schema src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml --target-class CoreDataset

# Phase 4 — pair reconciliation
poetry run python -m data_sheets_schema.d4d_pair_consistency \
  --full data/d4d_concatenated/claudecode_agent_crate/2026-07-27_claude-opus-5_rep2/CM4AI_d4d.yaml \
  --core data/d4d_concatenated/claudecode_agent_crate_core/2026-07-27_claude-opus-5_rep2/CM4AI_d4d_core.yaml \
  --sync-core
poetry run python -m data_sheets_schema.d4d_pair_consistency \
  --full data/d4d_concatenated/claudecode_agent_crate/2026-07-27_claude-opus-5_rep2/CM4AI_d4d.yaml \
  --core data/d4d_concatenated/claudecode_agent_crate_core/2026-07-27_claude-opus-5_rep2/CM4AI_d4d_core.yaml
```

## Final results

| Check | Result |
|---|---|
| Full — LinkML schema validation (`Dataset`) | **No issues found** |
| Full — ontology term validation | **Validation passed** |
| Core — LinkML schema validation (`CoreDataset`) | **No issues found** |
| Core — ontology term validation | **Validation passed** |
| Pair consistency with `--sync-core` | **PASS** — 76 schema-identical slots, projected `['resources']` |
| Pair consistency, independent re-run | **PASS** — 76 schema-identical slots, projected `['resources']` |
| Validator warnings | none emitted |
| Core header `Phase 4 reconciliation: completed` | present |

Line counts (informational metadata, not a quality gate): full **2,708** lines, core **2,077**
lines. Both records were re-validated after the Phase 3 corrections and after the Phase 4 sync.
