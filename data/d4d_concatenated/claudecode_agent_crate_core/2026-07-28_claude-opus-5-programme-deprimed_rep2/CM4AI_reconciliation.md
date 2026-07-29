# CM4AI full/core reconciliation — 2026-07-28_claude-opus-5-programme-deprimed_rep2

- **Arm:** DE NOVO WITH CRATE (documents + RO-Crate evidence)
- **Agent runtime:** Claude Code — **Provider:** Anthropic — **Model:** claude-opus-5[1m]
- **Mode:** four-phase project agent, pinned-referent — **Temperature:** 0.0
- **Generated:** 2026-07-28

## Inputs

| Role | Path |
|---|---|
| Factual input (only) | `data/preprocessed/concatenated/CM4AI_preprocessed_with_crate.txt` |
| Structure — full | `src/data_sheets_schema/schema/data_sheets_schema_all.yaml` (class `Dataset`) |
| Structure — core | `src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml` (class `CoreDataset`), `src/data_sheets_schema/schema/D4D_Core.yaml` |
| Selection references | `data/preprocessed/source_manifest.yaml`, `data/ro-crate_packages/crate_manifest.yaml` |

## Outputs

| Artifact | Path | Lines |
|---|---|---|
| Full | `data/d4d_concatenated/claudecode_agent_crate/2026-07-28_claude-opus-5-programme-deprimed_rep2/CM4AI_d4d.yaml` | 2564 |
| Core | `data/d4d_concatenated/claudecode_agent_crate_core/2026-07-28_claude-opus-5-programme-deprimed_rep2/CM4AI_d4d_core.yaml` | 1702 |
| Report | this file | — |

Neither output overwrote an existing file; the version directory was created for this run.

---

## Pinned referent — how it was applied

The subject is the **CM4AI data-release programme as an ongoing quarterly release
series**, not any single release.

1. **Top level = programme.** `id: https://cm4ai.org/`, `title: Cell Maps for
   Artificial Intelligence (CM4AI) - quarterly data-release programme`. The
   record was checked mechanically to confirm that `doi`, `version`, `issued`,
   `total_size_bytes`, `total_file_count` and `download_url` are all **absent**
   at top level. Top-level `status` describes the series ("Active. Quarterly Beta
   releases … through the end of the project in November 2026"), and top-level
   `citation` is the programme's canonical bioRxiv citation, which the
   attribution terms require for every release.

2. **`resources` = the four quarterly releases**, in date order, each carrying
   its own identity:

   | Release | `id` / `doi` | `version` | `issued` | `total_file_count` | `status` |
   |---|---|---|---|---|---|
   | March 2025 | 10.18130/V3/B35XWX | 1.4 | 2025-03-03 | 6 | Superseded |
   | June 2025 | 10.18130/V3/F3TD5R | 2.1 | 2025-07-01 | 21 | Superseded |
   | October 2025 | 10.18130/V3/K7TGEM | 2.1 | 2025-10-31 | 8 | Superseded |
   | June 2026 | 10.18130/V3/HIGT4C | 2.0 | 2026-06-17 | 10 | **Current** |

3. **`file_collections` = the current release's inventory.** Ten `FileCollection`
   entries, one per HIGT4C archive, with `path`, `compression: zip`,
   `collection_type`, `file_count`, `issued` (2026-06-17 or 2026-07-15 per the
   landing page's per-file publication stamps), and the displayed size, MD5 and
   sub-crate context in the description.

4. **Modalities live in composition and file collections**, not as top-level
   resources: `instances` carries IF images, protein interactions, proteins
   investigated, genes targeted, cell lines, experimental conditions and crate
   entity counts; `collection_mechanisms` and `file_collections` carry the AP-MS
   / SEC-MS / IF / perturb-seq split.

### What the programme framing made awkward

- **`file_collections` is release-scoped while its parent is programme-scoped.**
  Following the instruction literally, the top-level `Dataset` describes the
  programme but its `file_collections` describe only HIGT4C. The scope is stated
  in every collection's description and in its `issued`/`page` fields, but a
  consumer reading `file_collections` as "the top-level dataset's files" will
  under-count the series. The prior releases' inventories are described in prose
  inside each release resource instead.
- **No place for release-level checksums in the full schema.** `FileCollection`
  has `path`, `compression`, `file_count` and `total_bytes` but no checksum slot.
  MD5s therefore appear structurally only in core `distributions`
  (`CoreDistribution.md5`) and in prose in the full record's descriptions. This
  is a full-schema gap, not a modelling choice.
- **`total_size_bytes` was deliberately left unset on HIGT4C.** The two available
  figures have incompatible scopes: the ten Dataverse archives sum to ~12.6 GB by
  their displayed sizes, while the crate's `evi:totalContentSizeBytes` is
  21,051,331,945,400 and covers 53,877 documented datasets, most of them hosted
  externally. Putting either number next to `total_file_count: 10` would create a
  false implicature, so both are stated with explicit scope in the resource
  description and in `anomalies` instead.
- **`created_by` / `created_on` were left unset.** Every release page records
  Data Creation Date 2025-02-27, Deposit Date 2025-02-27 and depositor "Niestroy,
  Justin" — identical across releases published from 2025-03 to 2026-06, i.e.
  carried forward and stale. Propagating 2025-02-27 onto the June 2026 release
  would assert something the corpus contradicts, so the fact is recorded as prose
  in `collection_timeframes.timeframe_details` and the slots left empty.
- **Programme-level aggregate counts have no scoped home.** cm4ai.org's "Data
  Insights" (1,374 protein interactions, 53,788 IF images, 7,023 proteins, 11,739
  genes, 21.4 TB) are genuinely programme-scoped; they were placed in `instances`
  with `counts`, except the 21.4 TB volume, which has no matching slot at
  programme level and is recorded in `external_resources` (CM4AI portal) and
  `anomalies`.

---

## Phase 1 — full generation

Structure derived at runtime from class `Dataset` via `SchemaView`
(`class_induced_slots`), including nested class shapes, enum inventories,
cardinality and inlining. No prior D4D record, evaluation, or reconciliation
report was read; no output directory was searched for examples. The three
withheld crate artifacts (`CM4AI_crate_d4d.yaml`,
`CM4AI_crate_mapped_d4d.yaml`, `ro-crate-linkml.yaml`,
`ro-crate-datasheet.html`, any `ro-crate-preview.html`) were not opened, globbed
or cited.

69 top-level slots populated.

Schema violations found and fixed before the record was accepted:

1. `issued` values required an RFC 3339 offset — rewritten as
   `YYYY-MM-DDT00:00:00+00:00`.
2. `principal_investigator`, `grantor`, `contact_person`,
   `reviewing_organization` and `governance_committee_contact` are non-inlined
   references — replaced inline objects with identifier strings.
3. `Organization` requires `id` — added identifiers for KTH and University of
   Alabama.
4. `scope_impact` is a `DatasetLimitation` slot, not a `DatasetBias` slot —
   removed from `known_biases`, text folded into `bias_description`.
5. **Fabricated identifiers caught by self-audit, not by the validator:** the
   first draft used real-world ROR IDs for UCSD, Stanford, UCSF, Yale, UT Austin,
   UAB, SFU, Montreal and NIH. None of those appear in the corpus — they came
   from model knowledge, which the provenance guard forbids. All were replaced
   with local `https://cm4ai.org/d4d/org/...` identifiers. `https://ror.org/0153tk833`
   (University of Virginia) was **kept**, because the HIGT4C landing page prints
   it verbatim as the affiliation of Clark T, Al Manir S and Levinson MA.

## Phase 2 — core generation

`CoreDataset`'s field inventory was derived at runtime from the merged core
schema. Core was then built by projecting the validated Phase 1 full record
through that inventory (guaranteeing deep identity for shared slots), dropping
full-only slots, and adding the core-only `distributions`.

- Shared and populated: **62** top-level slots.
- Full-only, dropped from core: `citation`, `file_collections`, `relationships`,
  `direct_collection`, `third_party_sharing`, `participant_privacy`,
  `related_datasets` — none of these exist on `CoreDataset`.
- Core-only added: `distributions` (10 `CoreDistribution` entries).
- Core slots left unpopulated, and why: `dialect` (nothing tabular is released);
  `compression` at top level (mixed — recorded per distribution); `content_warnings`,
  `imputation_protocols`, `annotation_analyses` (not documented anywhere in the
  corpus); `doi`, `version`, `issued`, `download_url` (release-scoped — excluded
  from top level by the pinned referent); `created_by`, `created_on`,
  `modified_by`, `last_updated_on`, `was_derived_from`, `conforms_to_class`,
  `conforms_to_schema` (see the stale-deposit-date note above).

Phase 2 re-read the source bundle for every core field the full record left
empty. **No new source-supported fact was found that the full record had missed**,
so nothing needed back-porting into the full record on factual grounds.

## Phase 3 — source and provenance audit

Both records re-validated (schema + terms) clean. Read history contains no prior
D4D output, evaluation, or reconciliation report.

### Source conflicts found and how they were resolved

| # | Conflict | Resolution |
|---|---|---|
| 1 | **Release date.** cm4ai.org shows "Released on: June 17, 2025" for HIGT4C while labelling it the June 2026 release; Dataverse citation metadata gives publication date **2026-06-17**. | Dataverse metadata treated as authoritative, per the run instruction. `issued: 2026-06-17T00:00:00+00:00`. The conflict is recorded twice in-record: `anomalies` → "Release date displayed inconsistently on the project website", and `errata` → "Release date shown incorrectly on the CM4AI release page". Corroborating evidence: the HIGT4C files themselves are stamped Published Jun 17, 2026 and Jul 15, 2026. |
| 2 | **Release size.** Crate `contentSize` = "19.9 TB"; crate `evi:totalContentSizeBytes` = 21,051,331,945,400 (≈21.05 TB decimal / 19.15 TiB); cm4ai.org programme volume = 21.4 TB; Dataverse archives sum to ≈12.6 GB. | Not resolved to a single number, because the four figures have three different scopes. All are recorded with explicit scope in the HIGT4C resource description and in `anomalies` → "Inconsistent size statements for the current release". No `total_size_bytes` asserted. |
| 3 | **Author roster.** The June 2026 crate's free-text `citation` string drops "Marquez C" and adds "Park, S" and "Zhao, X". The crate's *structured* `author` array (47 entries) agrees exactly with the Dataverse author list, including Marquez's ORCID 0000-0003-3960-420X. | The structured array + Dataverse roster (which agree) were used. The discrepancy is recorded in the Marquez creator entry's `description`. Park S and Zhao X are **not** listed as creators, since only the crate's free-text string names them. |
| 4 | **Sali A affiliation.** Dataverse roster and crate both give "University of California San Diego"; the CM4AI preprint and the Nature paper both place Sali at UCSF. | Release metadata used (UCSD), since these are the release's own authorship records, with the conflict stated in the creator entry's `description`. Flagged as the one place where the record likely propagates an upstream error. |
| 5 | **Ravitsky affiliation.** Dataverse gives "University of Montreal"; the ethical-review contact email is `ravitskyv@thehastingscenter.org` and the Hastings Center is listed among CM4AI institutions. | Dataverse affiliation used; the Hastings Center email and its role recorded in the creator description and in `ethical_reviews`. |
| 6 | **Governance contact spelling.** Release pages say "Jillian Parker"; the crate says "Jilian Parker". | Release-page spelling used; the crate variant noted in the creator entry and in `ethical_reviews`. |
| 7 | **Dataverse version numbering is non-monotonic.** October 2025 displays version 2.1, the later June 2026 displays 2.0. | Both recorded as printed. Explained in `version_access.version_details` as per-dataset rather than per-series numbering — a version-scope distinction, not a contradiction. |
| 8 | **Crate `datePublished` 2026-06-30 and crate `version` 1.0** vs Dataverse publication date 2026-06-17 and Dataverse version 2.0. | The Dataverse values populate the structured `issued`/`version` slots; the crate's own values are recorded in the HIGT4C description as crate-internal metadata. These describe different objects (the crate vs the Dataverse dataset), so this is a scope distinction, not a conflict. |
| 9 | **Sub-crate licences differ from the release licence.** The release is CC BY-NC-SA 4.0, but the two EndoTag AP-MS sub-crates and the KOLF2 SEC-MS sub-crate are CC0 1.0. | Both recorded: `license` remains CC BY-NC-SA 4.0 at every level the Dataverse states it, and `license_and_use_terms.license_terms` carries an explicit bullet that licensing is not uniform below the release level. |
| 10 | **Stale creation/deposit dates.** 2025-02-27 appears identically on all four releases. | Left out of structured slots; recorded as prose. See "awkward" section above. |

### Scoping traps avoided

- **The Nature paper is not CM4AI release content.** Schaffer et al. 2025
  (doi:10.1038/s41586-025-08878-3) describes the **U2OS** multimodal cell map,
  with data at NDEx, MassIVE MSV000097168, ProteomeXchange PXD052362 and
  ModelArchive — none of which is in the CM4AI Dataverse series (MDA-MB-468 and
  KOLF2.1J). Its methods, assemblies, annotation jamborees and GPT-4 naming
  procedure were therefore **not** imported into `instances`, `known_biases`, or
  `labeling_strategies`. It appears only in `related_datasets` with
  `relationship_type: references`, marked as methodological and scientific
  context. This is the single largest risk of over-claiming in the CM4AI corpus:
  the paper is ~2,900 lines of the bundle and describes a different dataset.
- **`labeling_strategies` describes the pipeline, not the released data.** Since
  computed cell maps are absent from every release, the entry explicitly states
  that released map-input streams are not label-annotated by that procedure.
- Programme statistics (cm4ai.org "Data Insights") were kept at programme level;
  per-release counts (563 vs 464 imaged proteins, 6/21/8/10 files) were kept on
  the releases.

### Internal consistency checks (both files)

- Release DOIs: all 4 unique, each appearing in `resources`, `distribution_formats`,
  `distribution_dates` and `version_access.versions_available` with the same
  version and date.
- `version_access.latest_version_doi` = `https://doi.org/10.18130/V3/HIGT4C` =
  the resource marked current.
- `license` and `publisher` identical at top level and on all 4 resources.
- Every DOI asserted in the record (11 distinct) verified present in the source
  bundle. Every MD5 asserted (10) verified present in the source bundle.
- Every MassIVE accession, grant number, ORCID, email, RRID, NDEx uuid and
  entity count asserted was string-matched back to the corpus.
- The only derived (non-quoted) quantity in either record is the ~12.6 GB sum of
  the ten HIGT4C displayed file sizes; it is labelled "summing to approximately
  … by their displayed per-file sizes" in both places it occurs.

No corrections to facts were required in Phase 3; the only Phase 3 edits were the
two wording changes that made the 12.6 GB figure explicitly derived.

## Phase 4 — strict full/core reconciliation

Shared slots derived at runtime from `Dataset` and `CoreDataset` by the
schema-derived validator; no hand-written field list was used.

```
poetry run linkml-validate -s .../data_sheets_schema_all.yaml -C Dataset <full>
poetry run linkml-term-validator validate-data <full> --schema .../data_sheets_schema_all.yaml --target-class Dataset
poetry run linkml-validate -s .../data_sheets_schema_core_all.yaml -C CoreDataset <core>
poetry run linkml-term-validator validate-data <core> --schema .../data_sheets_schema_core_all.yaml --target-class CoreDataset
poetry run python -m data_sheets_schema.d4d_pair_consistency --full <full> --core <core> --sync-core
poetry run python -m data_sheets_schema.d4d_pair_consistency --full <full> --core <core>
```

**Result: `PASS: 76 schema-identical slots; projected slots=['resources']`**, on
both the `--sync-core` pass and the independent final pass. `--sync-core` made no
factual change; it added the `# Phase 4 reconciliation: completed` header line.
Both files re-validated clean afterwards.

### Projected slot: `resources` (Dataset → CoreDataset)

Matched by `id`; coverage equal (4 ↔ 4). For each release, every slot present in
the core projection is byte-identical to the full record's value; the only
full-only nested slot is `total_file_count`, which `CoreDataset` does not define.

### Related content: `file_collections` ↔ `distributions` — semantic review

The validator emits `semantic-review-required` with 10 deterministic matches and
0 unmatched core distributions. The review it requires was performed:

| Dimension | Finding |
|---|---|
| Names | 10/10 identical. |
| `id` | 10/10 identical (`{HIGT4C DOI}#{filename}`). |
| Paths | 10/10 identical; each is the bare filename, matching the HIGT4C landing page, which lists no folder prefixes (unlike June/October 2025, which use `Images/` and `mass-spec/cancer-cells/`). |
| Descriptions | 10/10 identical strings. |
| Compression | 10/10 `zip` on both sides — consistent with `format: ZIP` and `media_type: application/zip` in core. |
| Formats | Core asserts `ZIP` / `application/zip`; full asserts `compression: zip` and no format slot exists on `FileCollection`. No conflict; core is strictly more specific. |
| Checksums | MD5 present in core only (`FileCollection` has no checksum slot). Each core MD5 was verified to also appear verbatim inside the corresponding full-record description, and all 10 were verified against the source bundle. No conflict. |
| Byte counts | Neither side asserts a byte count. Displayed sizes ("3.8 GB", "113.3 KB", …) are rounded on the landing page; converting them to `total_bytes`/`bytes` would fabricate precision, so both slots were left empty and the displayed value carried in prose on both sides. |
| Access URLs | `page` (full) points at the HIGT4C landing page; core `CoreDistribution` has no URL slot. No conflict. |
| Release scope | Both sides scope every entry to HIGT4C via the `id` prefix, the description text and (full only) `issued`/`license`/`page`. |
| `total_file_count` vs distribution count | `total_file_count: 10` on the HIGT4C resource equals the 10 `file_collections` and the 10 `distributions` — same scope, consistent. |
| `is_tabular` / `dialect` | `is_tabular: false` in both; `dialect` absent from core, consistent with a non-tabular release. |

**Zero unresolved contradictions** within or between the two records.

---

## Crate-vs-documents attribution

### Populated only from crate evidence (absent from the document corpus)

- **MassIVE accessions and the FTP path**: MSV000101915, MSV000101917,
  MSV000100676, MSV000098237, `ftp://massive-ftp.ucsd.edu/v10/MSV000098237/`,
  and doi:10.25345/C5348GV4S. The Dataverse pages link "MassIVE Repository"
  as bare anchor text with no accession. → `raw_data_sources`, `raw_sources`,
  `external_resources`, `distribution_formats`.
- **AP-MS data generator: Richa Tiwari**, named as author of both EndoTag AP-MS
  sub-crates. No CM4AI publication or landing page names an AP-MS data
  generator. → `data_collectors`.
- **AP-MS experimental design detail**: four biological replicates; each batch
  containing an untagged parental control, ten tagged chromatin-modifier lines
  and a positive control; DMSO vehicle controls. → `collection_mechanisms`.
- **Additional funding awards**: R01HG012351, R01NS131560, U54CA274502,
  S10 OD026929, DoD W81XWH-22-1-0401, CIRM EDUC4-12804, NWO 019.231EN.013,
  NCI P30CA023100. The Dataverse funding field lists only 1OT2OD032742-01. →
  `funders`.
- **Sub-crate inventory and per-modality sizes/versions/dates**: nine sub-crates
  with their own `contentSize`, `version`, `datePublished` and licences (441.2 GB,
  532.5 GB, 1.11 TB, 910 GB, 16.7 TB, 177.35 GB, and the three IF crates). →
  `file_collections` descriptions, `raw_sources`, `relationships`.
- **License heterogeneity below release level** (CC0 1.0 on three sub-crates). →
  `license_and_use_terms`.
- **Crate-scale provenance counts**: 53,877 datasets, 1,976 computations, 6
  software instances, 20 schemas, 55,859 entities, 8 entities with checksums,
  `evi:totalContentSizeBytes` 21,051,331,945,400, the declared format list, and
  `fairscapeVersion` 1.1.3. → `instances`, `anomalies`,
  `machine_annotation_tools`, HIGT4C description.
- **ARK identifiers**: the release crate ARK, the CM4AI project ARK
  (`project-cell-maps-for-artificial-intelligence-qTdsTBd3FtA`) and the UCSD
  organization ARK. → `external_resources`, `relationships`.
- **Ontology bindings on the release**: MeSH D001943/D057026/D064113/D013058/
  D005453/D017239/D000077337, EDAM topic_0121/3170/3320/3474, Cellosaurus
  CVCL_0419/CVCL_B5P3. → `instances.data_topic` / `data_substrate`,
  `labeling_strategies`.
- **Explicit human-subjects and consent framing**: `humanSubjectExemption`
  ("Exempt — research with commercially available de-identified human cell lines
  does not constitute human subjects research"), `humanSubjectResearch`,
  `d4d:informedConsent` and `d4d:atRiskPopulations`. The documents state "Human
  Subjects: No / De-identified Samples: Yes" but never the exemption rationale or
  a consent statement. → `human_subject_research`, `informed_consent`,
  `at_risk_populations`, `sensitive_elements`, `subpopulations`.
- **`conditionsOfAccess`, `copyrightNotice` with year 2026, `confidentialityLevel:
  Unrestricted`**. → `license_and_use_terms`, `regulatory_restrictions`.
- **The interpretable-ML use-case exemplars** Ma et al. 2018 (PMID 29505029) and
  Kuenzi et al. 2020 (PMID 33096023), named in `rai:dataUseCases` but not on the
  release pages. → `intended_uses`, `existing_uses`.
- **`ai_ready_score.json`** contributed the framing that only 8/55,859 files carry
  checksums and the FAIR/provenance/characterization/ethics/sustainability/
  computability self-assessment structure. → `anomalies`.
- **`rai:dataCollectionTimeframe` 9/1/2022 – 6/1/2026**, the only explicit
  collection window in the whole bundle. → `collection_timeframes.start_date` /
  `end_date`.

### Crate content judged already present in the documents

- **Release description, keywords, licence URL, publisher, DOI, PI and contact
  email** — all duplicate the Dataverse landing page verbatim.
- **`rai:dataLimitations`, `rai:dataBiases`, `rai:dataReleaseMaintenancePlan`,
  `completeness`, `prohibitedUses`, `usageInfo`, `ethicalReview`,
  `dataGovernanceCommittee`, `rai:dataCollectionMissingData`, most of
  `rai:dataUseCases`** — these are byte-for-byte the Limitations, Potential
  Sources of Bias, Maintenance Plan, Completeness, Prohibited Uses, Ethical
  Review, Data Governance Committee and Intended Use sections already printed on
  the June 2025, October 2025 and June 2026 landing pages. The crate adds
  presentation, not evidence, for this whole block.
- **`rai:dataCollection`** merely points at the bioRxiv preprint, which is in the
  document corpus in full.
- **The 47-author roster with ORCIDs and affiliations** duplicates the Dataverse
  citation metadata; the crate's structured array was used to *adjudicate* its own
  free-text citation string, not to add authors.
- **`associatedPublication`** lists four papers, three of which are already
  Related Publications on the landing pages; only the ordering differs.
- **IF sub-crate descriptions** are the same "spatial localization of 464 proteins
  … DAPI / calreticulin / tubulin / green channel" text already on the release
  file listings.

**Net assessment.** For this project the crate's contribution is concentrated in
*downstream pointers and provenance scale* — accessions, sub-crate inventory,
per-modality sizes, additional funders, licence heterogeneity, ARK identifiers,
ontology bindings and entity counts — plus three governance statements (exemption
rationale, informed consent, at-risk populations) that the documents never make.
Its `rai:*` block, which looks like the richest part of the crate, is almost
entirely a re-serialisation of text the Dataverse pages already publish. The
crate also *introduced* two of the ten source conflicts (the citation-string
author roster, and `contentSize` vs `evi:totalContentSizeBytes`), so it is not
uniformly a higher-authority source.

---

## Completion audit

- [x] Every factual input path on the Phase 1/2/3/4 allowlist; single factual
      source was `CM4AI_preprocessed_with_crate.txt`.
- [x] No prior generated YAML read or cited; withheld artifacts untouched.
- [x] Every emitted slot and nested object permitted by the applicable schema
      (validated).
- [x] Core's full input carries this run's exact version label.
- [x] No Phase 2 discovery required back-porting (none found).
- [x] Schema and ontology term validation pass on both files.
- [x] Schema-derived pair validator passes: 76 schema-identical slots.
- [x] Projected and related content reviewed semantically (tables above).
- [x] Phase 3 and Phase 4 results recorded here.
