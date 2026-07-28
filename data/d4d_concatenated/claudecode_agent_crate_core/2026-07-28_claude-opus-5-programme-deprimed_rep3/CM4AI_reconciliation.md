# CM4AI full/core reconciliation — 2026-07-28_claude-opus-5-programme-deprimed_rep3

Arm: DE NOVO WITH CRATE (documents + RO-Crate evidence).
Mode: four-phase project agent, pinned-referent. Phases 1–4 run strictly sequentially.

| Field | Value |
|---|---|
| Agent runtime | Claude Code |
| Provider | Anthropic |
| Model | claude-opus-5[1m] |
| Temperature | 0.0 |
| Generated | 2026-07-28 |
| Full | `data/d4d_concatenated/claudecode_agent_crate/2026-07-28_claude-opus-5-programme-deprimed_rep3/CM4AI_d4d.yaml` |
| Core | `data/d4d_concatenated/claudecode_agent_crate_core/2026-07-28_claude-opus-5-programme-deprimed_rep3/CM4AI_d4d_core.yaml` |
| Provenance | `data/d4d_concatenated/claudecode_agent_crate_core/2026-07-28_claude-opus-5-programme-deprimed_rep3/CM4AI_provenance.yaml` (`record_mode: live`) |

## Pinned referent

The subject of the datasheet is the **CM4AI data-release programme as an ongoing
quarterly release series**, not any single release.

1. **Top level = programme.** `id` is `https://cm4ai.org/data-releases/`, the
   programme's release page, not a release DOI. No `doi`, `version`, `issued`,
   `total_size_bytes` or `total_file_count` appears at top level. `status`
   describes the series ("Ongoing quarterly Beta release series ... the June 2026
   release is current and the March 2025, June 2025 and October 2025 releases are
   superseded").
2. **`resources` = the four quarterly releases**, in date order, each carrying its
   own `doi`, `version`, `issued`, `total_file_count`, `page`, `license`,
   `publisher` and `status`:
   - March 2025 — `10.18130/V3/B35XWX`, Dataverse version 1.4, issued 2025-03-03, 6 files — superseded
   - June 2025 — `10.18130/V3/F3TD5R`, version 2.1, issued 2025-07-01, 21 files — superseded
   - October 2025 — `10.18130/V3/K7TGEM`, version 2.1, issued 2025-10-31, 8 files — superseded
   - June 2026 — `10.18130/V3/HIGT4C`, version 2.0, issued 2026-06-17, `last_updated_on` 2026-07-15T20:28:19Z, 10 files — **current**
3. **`file_collections` = the current release's inventory.** Ten `FileCollection`
   entries, one per HIGT4C Dataverse ZIP, each with `path`, `compression: zip`,
   `collection_type`, `issued`, and MD5 plus published size in `description`.
4. **Modalities live inside the current release's composition**, as five
   `instances` on the HIGT4C resource (AP-MS, SEC-MS, IF imaging, CRISPRi
   Perturb-seq, release provenance metadata), plus the ten `file_collections`.
   No modality appears as a top-level `resource`. Programme-scope composition
   (1,374 protein interactions; 53,788 IF images; 7,023 proteins; 11,739 genes;
   the two cell systems) sits in top-level `instances`.

### What the programme framing made awkward to place

- **Programme-scope size.** The portal advertises 21.4 TB of data volume for the
  programme. `total_size_bytes` is an integer, and "21.4 TB" carries no exact
  byte count, so converting it would fabricate precision. It is recorded in the
  top-level `description` and in `anomalies`, not as a slot value.
- **The May 2024 release.** `cm4ai.org/data-releases` lists a May 2024 release in
  its Archive, and the project article cites `10.18130/V3/DXWOS5` for it. The
  pinned referent enumerates four resources, and the corpus contains no processed
  record for May 2024, so it is **not** a fifth resource. It is captured in
  `version_access.versions_available` and in `related_datasets` with
  `relationship_type: is_new_version_of`, with the omission stated explicitly.
- **Two different byte totals for the current release.** The HIGT4C Dataverse
  payload is ~16.6 GB of ZIPs; the crate reports 21,051,331,945,400 bytes across
  55,859 entities because the mass-spec, AP-MS and Perturb-seq archives are
  RO-Crate manifests pointing at MassIVE/SRA/Figshare payloads. Putting either
  number in `total_size_bytes` would mis-scope it, so `total_file_count: 10`
  (Dataverse) is set and `total_size_bytes` is omitted, with both figures
  explained in the resource description and recorded as an anomaly.
- **Sub-crates shared across releases.** The AP-MS and Perturb-seq sub-crates
  declare `isPartOf` against a January 2026 release *and* the June 2026 release.
  A release-as-resource model has no place for a sibling release that the corpus
  never otherwise documents, so this is recorded in `relationships` rather than
  invented as a resource.
- **No parent/child version chain.** Each quarterly release has its own DOI
  rather than being a version of one dataset, so `parent_datasets` is unused and
  the series structure is carried by `resources` order + `status` + `updates`.

## Phase 1 — full generation

Structure derived at runtime from class `Dataset` in
`src/data_sheets_schema/schema/data_sheets_schema_all.yaml` via `SchemaView`
(induced slots, ranges, cardinality, inlining, enums). No prior D4D record was
read as a template. Schema shape probes established, before authoring, that
`principal_investigator`, `grantor`, `contact_person`, `reviewing_organization`
and `governance_committee_contact` take identifier references while
`affiliations`, `grants` and nested `sampling_strategies` take inlined objects —
these are non-obvious and were verified, not assumed.

Populated: 62 top-level slots. Deliberately omitted for want of evidence:
`subsets`, `splits`, `variables`, `imputation_protocols`, `annotation_analyses`,
`participant_compensation`, `collection_notifications`, `collection_consents`,
`consent_revocations`, `parent_datasets`, and `dialect` (core-only, and no
tabular distribution is declared).

## Phase 2 — core generation

Core field inventory derived from `D4D_Core.yaml` and the merged core schema
(`CoreDataset`, 62 populated slots). Started from the Phase 1 values for every
shared slot, then dropped the seven top-level slots the core schema does not
declare — `citation`, `direct_collection`, `file_collections`,
`participant_privacy`, `related_datasets`, `relationships`,
`third_party_sharing` — and, inside `resources`, `citation` and
`total_file_count`.

Core's one genuine gain over full: `distributions` (`CoreDistribution`) has
structured `md5`, `format` and `media_type` slots, which `FileCollection` does
not. The ten HIGT4C checksums therefore appear as first-class values in core
where full can only carry them as prose.

No fact was found in the sources that the full record had missed, so nothing was
back-ported from Phase 2 to Phase 1.

## Phase 3 — source and provenance audit

**Provenance.** Factual input was exclusively
`data/preprocessed/concatenated/CM4AI_preprocessed_with_crate.txt`. Structure and
selection references: the two schemas, `D4D_Core.yaml`,
`data/preprocessed/source_manifest.yaml`, `data/ro-crate_packages/crate_manifest.yaml`.
No prior D4D record, evaluation or reconciliation report was read. The withheld
artifacts (`CM4AI_crate_d4d.yaml`, `CM4AI_crate_mapped_d4d.yaml`,
`ro-crate-linkml.yaml`, `ro-crate-datasheet.html`, any `ro-crate-preview.html`)
were not opened, globbed or cited. Output directory *names* under
`data/d4d_concatenated/` were listed once to confirm the target label was unused;
no contents were read. No live web content was fetched.

**Corrections made in Phase 3** (all to the full record first, then propagated):

1. `instances.protein_interactions_programme_total.data_topic` —
   `meshb…D064113` (CRISPR-Cas Systems) → `NCIT_C18469` (protein-protein
   interaction). The original term contradicted the instance it annotated.
2. `instances.genes_targeted_programme_total.data_topic` —
   `edamontology topic_3170` (RNA-Seq) → `meshb…D064113` (CRISPR-Cas Systems),
   which is what the corpus maps CRISPR/Cas9 perturbation to.
3. `resources[HIGT4C].instances.crispri_perturb_seq_kolf2.data_topic` —
   `topic_3170` → `EFO_0008860`, the term the release's own Dataverse keyword
   mapping assigns to perturb-seq / perturbation sequencing.

All three terms are drawn from mappings the corpus itself states. Both records
were re-validated after the corrections.

**Source conflicts resolved.** Every one is recorded in the records themselves
(mostly under `anomalies`), not silently resolved:

| Conflict | Resolution |
|---|---|
| cm4ai.org shows "Released on: June 17, 2025" for HIGT4C; Dataverse gives publication date 2026-06-17 | **Dataverse authoritative**, as instructed. The website's year is wrong. Recorded in `anomalies.release_date_conflict_june_2026`. |
| Crate root says `version: "1.0"`, `datePublished: "2026-06-30"`; Dataverse says Version 2.0, 2026-06-17 | Dataverse used for `version`/`issued`; the crate's values recorded as a crate-scoped package version in `version_access.version_details` and `anomalies`. |
| Crate citation for HIGT4C reads "…, 2025, … V1"; Dataverse citation reads "…, 2026, … V2" | Dataverse citation used verbatim on the resource; the crate's internal inconsistency recorded as an anomaly. |
| Crate sub-crate citations name the March 2025 release title against the October 2025 DOI, and IF sub-crates cite B35XWX | Recorded as an anomaly; not used as evidence for any release's identity. |
| IF protein coverage: 563 (March 2025) vs 464 (June 2025 onward) vs 523 (cm4ai.org summary) | 563 assigned to the March 2025 resource, 464 to the current release; 523 recorded as unattributable to a release. |
| Crate IF sub-crates carry 2.6/3.2/2.8 GB, March-2025 MD5s, `datePublished "02/28/2025"`, `version "0.1.0"` — while HIGT4C ships 3.8/4.6/4.2 GB with different MD5s | **Dataverse file table used** for the current release inventory; the crate's stale inheritance recorded in `anomalies.stale_if_subcrate_metadata`. |
| Crate `contentSize "19.9 TB"` vs `evi:totalContentSizeBytes 21051331945400` vs portal "21.4 TB" | None used as `total_size_bytes`; all three stated and flagged as unreconciled. |
| Licence: release is CC BY-NC-SA 4.0, but AP-MS (MSV000101915/101917) and KOLF2 SEC-MS (MSV000100676) sub-crates declare CC0 1.0 | Both recorded in `license_and_use_terms.license_terms` with a caution to check component-level licences. |
| Project end: NIH RePORTER 2026-08-31 vs maintenance plan "November 2026" | Both stated in `collection_timeframes`; not reconciled, and said so. |
| Collection timeframe: release crate 9/1/2022–6/1/2026; sub-crates end 1/31/2026 and 10/13/25 | Release-level range used; sub-crate variants recorded in `timeframe_details`. |
| Authorship: Dataverse lists 47 authors; crate citation omits Marquez C and adds Park, S and Zhao, X | Dataverse list used; the divergence recorded in `creators.release_author_list`. |
| Sali affiliation: UCSF (project article, Nature) vs UCSD (Dataverse, crate) | Both stated in the creator description. |
| Governance contact spelled "Jillian Parker" (Dataverse) vs "Jilian Parker" (crate) | Dataverse spelling used; the crate variant noted. |
| Ethics contact spelled "Vardit Ravitsky" (Dataverse) vs "Vardit Ravistky" (crate) | Dataverse spelling used; the crate variant noted. |
| cm4ai.org lists "AP-MS interactomes (coming soon!)" while HIGT4C already ships AP-MS | Page recorded as stale in `anomalies.stale_release_page_content`. |

**Scope trap handled.** The June 2026 crate lists Schaffer et al., *Nature* 642:222–231
(2025) and Qin et al., *Nature* 600:536–542 (2021) as associated publications.
Their measurements are in U2OS and HEK293 cells and their data live at NDEx,
MassIVE MSV000097168, ProteomeXchange PXD052362, the EBI Complex Portal, HPA v23
and ModelArchive — outside every CM4AI release. They are recorded as
`related_datasets` with `relationship_type: references` and explicitly described
as demonstrating the mapping approach rather than describing the released data.
Their funders (Schmidt Futures, Wallenberg, Göran Gustafsson, CFI/Genome BC,
NHGRI U24 HG006673, Third Rock, Google Ventures, Interline, Xaira) were **not**
imported into `funders`, which carries only funders the release metadata and
project article attribute to CM4AI itself.

## Phase 4 — strict full/core reconciliation

Shared slots derived at runtime with `SchemaView` from `Dataset` and
`CoreDataset`. **76 schema-identical slots**; **1 projected slot** (`resources`).

- All 76 identity slots: present in both or absent from both, with deeply
  identical parsed YAML including nested mappings and list order. No narrative
  field was condensed, paraphrased or reordered in core.
- `resources` projection: 4 resources, matched by `id`, equal coverage, deep
  identity on every nested schema-identical slot. Full-only nested slots omitted
  from the core projection: `citation`, `total_file_count`.
- **Related-content semantic review** (`file_collections` ↔ `distributions`), the
  review the validator's warning demands and cannot itself perform: all 10 pairs
  matched by `id`; `name`, `path`, `compression` and `description` verbatim
  identical; every core `md5` corroborated by the same checksum in the full
  record's `description`; `format: ZIP` and `media_type: application/zip`
  consistent with `compression: zip` and with Dataverse's "ZIP Archive" file
  type. No `bytes` value is asserted in core, matching the absence of
  `total_bytes` in full — the corpus publishes only rounded sizes ("3.8 GB"),
  and neither record fabricates a byte count.
- Scope agreement: 10 distributions ↔ HIGT4C `total_file_count: 10`; every
  distribution `id` anchored on `https://doi.org/10.18130/V3/HIGT4C#`, so the
  distribution set is unambiguously the current release, matching the referent.
- `dialect` absent and `is_tabular: false` in both — consistent, no tabular
  distribution is claimed.
- Cross-record identity/version/access facts checked: top-level `license`,
  `publisher` and licence terms agree with every resource's `license` and
  `publisher`; `version_access.latest_version_doi` agrees with the resource
  marked `status: current`; `distribution_dates` agree with each resource's
  `issued`; historical releases are marked `superseded` rather than treated as
  contradicting the current one.

**Result: zero unresolved contradictions within or between the two records.**

## Commands run

```bash
poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_all.yaml \
  -C Dataset data/d4d_concatenated/claudecode_agent_crate/2026-07-28_claude-opus-5-programme-deprimed_rep3/CM4AI_d4d.yaml

poetry run linkml-term-validator validate-data \
  data/d4d_concatenated/claudecode_agent_crate/2026-07-28_claude-opus-5-programme-deprimed_rep3/CM4AI_d4d.yaml \
  --schema src/data_sheets_schema/schema/data_sheets_schema_all.yaml --target-class Dataset

poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml \
  -C CoreDataset data/d4d_concatenated/claudecode_agent_crate_core/2026-07-28_claude-opus-5-programme-deprimed_rep3/CM4AI_d4d_core.yaml

poetry run linkml-term-validator validate-data \
  data/d4d_concatenated/claudecode_agent_crate_core/2026-07-28_claude-opus-5-programme-deprimed_rep3/CM4AI_d4d_core.yaml \
  --schema src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml --target-class CoreDataset

poetry run python -m data_sheets_schema.d4d_pair_consistency \
  --full .../CM4AI_d4d.yaml --core .../CM4AI_d4d_core.yaml --sync-core

poetry run python -m data_sheets_schema.d4d_pair_consistency \
  --full .../CM4AI_d4d.yaml --core .../CM4AI_d4d_core.yaml

poetry run d4d provenance record --project CM4AI --method claudecode_agent_crate \
  --label 2026-07-28_claude-opus-5-programme-deprimed_rep3 \
  --input-bundle data/preprocessed/concatenated/CM4AI_preprocessed_with_crate.txt
```

## Final results

| Check | Result |
|---|---|
| Full schema validation | No issues found |
| Full term validation | Validation passed |
| Core schema validation | No issues found |
| Core term validation | Validation passed |
| Pair consistency (`--sync-core`) | PASS — 76 identity slots, 1 projected |
| Pair consistency (independent re-run) | PASS — 76 identity slots, 1 projected |
| Semantic review of `file_collections` ↔ `distributions` | 10/10 matched, 0 conflicts |
| Live provenance record | Present, `record_mode: live` |
| Full line count (informational) | 2,675 |
| Core line count (informational) | 1,788 |

## Crate-only vs document-only evidence

**Populated only from crate evidence** (no document in the bundle supplies it):

- `funders` — the additional NIH awards R01HG012351, R01NS131560, U54CA274502,
  S10 OD026929, P30CA023100, and the non-NIH DoD W81XWH-22-1-0401, CIRM
  EDUC4-12804 and NWO 019.231EN.013. The Dataverse pages record only
  1OT2OD032742-01.
- `resources[HIGT4C].conforms_to` — RO-Crate 1.2 + EVI + Croissant RAI,
  FAIRSCAPE 1.1.3, ARK `ark:59853/rocrate-cell-maps-…-June-2026-data-release`.
- The entire sub-crate layer: MassIVE accessions MSV000101915, MSV000101917,
  MSV000100676, MSV000098237; DOI `10.25345/C5348GV4S`; the Figshare URL; the
  441.2 GB / 532.5 GB / 1.11 TB / 910 GB / 16.7 TB / 177.35 GB payload sizes;
  sub-crate part counts (560, 723, 867, 45, 16,845, 17,685); sub-crate authors
  (Richa Tiwari; Antoine Forget; Forget/Obernier/Krogan; the Lundberg-lab IF
  author list); sub-crate licences (CC0 vs CC BY-NC-SA) and per-component
  contact emails (nevan.krogan@ucsf.edu, pmali@ucsd.edu, emmalu@stanford.edu).
- Provenance counts: `evi:datasetCount` 53,877, `evi:computationCount` 1,976,
  `evi:softwareCount` 6, `evi:schemaCount` 20, `evi:totalEntities` 55,859,
  `evi:totalContentSizeBytes` 21,051,331,945,400, `evi:entitiesWithChecksums` 8.
- Declared format list (`.d`, `.d directory group`, `.tsv`, `.xml`, TSV, csv,
  executable, fastq.gz, h5, h5ad, image/jpeg, pdf, unknown).
- `d4d:informedConsent` and `d4d:atRiskPopulations` — the explicit
  "Not applicable" / "None" statements used in `informed_consent` and
  `at_risk_populations`.
- `humanSubjectExemption` — the exemption wording in `human_subject_research`.
- The SEC-MS iPSC experimental design (Bruker timsTOF, Spectronaut, R/MSstats,
  Parental 1-4 / NPC 1-2 / Neuron 1-3 / Cardio 1-2) and the AP-MS batch design
  (4 biological replicates, untagged parental control, 10 tagged lines, positive
  control, DMSO vehicle).
- MeSH / EDAM / Cellosaurus subject grounding used for `data_topic` and
  `data_substrate` on release-level instances.
- The AI-readiness self-assessment as a whole, including "0% of files have
  checksums (8/55859)" and the 47-author count.
- The stale-IF-metadata and citation-inconsistency anomalies — these are
  *detectable only* by comparing crate evidence against the Dataverse documents.

**Crate content judged already present in the documents** (crate corroborated, did
not add):

- Release title, description, keyword list, DOI, licence URL, publisher and
  copyright notice — all present verbatim on the Dataverse pages.
- Every `rai:` governance field: `dataLimitations`, `dataBiases`, `dataUseCases`,
  `dataReleaseMaintenancePlan`, `dataCollectionMissingData`, `completeness`,
  `prohibitedUses`, `usageInfo`, `conditionsOfAccess`. These are the same
  sentences the Dataverse pages publish under Limitations, Potential Sources of
  Bias, Intended Use, Maintenance Plan, Completeness and Prohibited Uses.
  `rai:dataUseCases` adds only the Ma 2018 / Kuenzi 2020 PMIDs.
- `ethicalReview`, `dataGovernanceCommittee`, `humanSubjectResearch`,
  `confidentialityLevel` — the Dataverse "Data Governance & Ethics" block carries
  the same content (with better spelling).
- `rai:dataCollection` — a pointer to the bioRxiv project article, which is
  itself in the bundle.
- `principalInvestigator`, `contactEmail`, author ORCIDs and affiliations —
  present on the Dataverse pages and in the preprint.
- `rai:dataCollectionTimeframe` start 9/1/2022 — matches the NIH RePORTER
  project start date.
- The IF image description (464 proteins, four-channel staining protocol) —
  identical text to the Dataverse file descriptions.

The crate's distinctive contribution to this arm is therefore **not** the
governance narrative, which is duplicated; it is the *provenance layer* — the
external repository accessions, payload sizes, sub-crate structure, per-component
licences and entity counts — plus the internal inconsistencies that only a
cross-check against the documents exposes.
