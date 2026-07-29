# CM4AI full/core reconciliation — crate-only arm, rep3

- **Run label:** `2026-07-28_claude-opus-5-crateonly_rep3`
- **Agent runtime:** Claude Code
- **Provider:** Anthropic
- **Model:** claude-opus-5[1m]
- **Mode:** four-phase project agent, crate-only
- **Temperature:** 0.0
- **Generated:** 2026-07-28
- **Full:** `data/d4d_concatenated/claudecode_agent_crate_only/2026-07-28_claude-opus-5-crateonly_rep3/CM4AI_d4d.yaml`
- **Core:** `data/d4d_concatenated/claudecode_agent_crate_only_core/2026-07-28_claude-opus-5-crateonly_rep3/CM4AI_d4d_core.yaml`
- **Provenance:** `data/d4d_concatenated/claudecode_agent_crate_only_core/2026-07-28_claude-opus-5-crateonly_rep3/CM4AI_provenance.yaml` (`record_mode: live`)

## Arm definition and evidence boundary

The only source of dataset facts for this run was
`data/preprocessed/concatenated/CM4AI_crate_only.txt`, which contains two
artifacts: `CM4AI_crate_metadata_reduced.json` (the release RO-Crate JSON-LD with
per-file inventories collapsed) and `ai_ready_score.json` (an AI-readiness
self-assessment). No publication, project website, Dataverse page, licence page,
source manifest, prior D4D record, evaluation, or live web content was read.
The schemas were used for structure only.

## Subject of the record

The record describes **the CM4AI June 2026 Data Release (Beta)** — the crate root
entity `https://fairscape.net/api/ark:59853/rocrate-cell-maps-for-artificial-intelligence-June-2026-data-release`,
DOI `10.18130/V3/HIGT4C`, version 1.0, published 2026-06-30.

That referent was chosen because it is the only entity the crate itself asserts
the package is *about*: `ro-crate-metadata.json` declares `about` pointing at it,
and every other Dataset-typed node in the graph declares `isPartOf` it. The
alternative referents the crate mentions — the CM4AI *project*
(`ark:59853/project-cell-maps-for-artificial-intelligence-qTdsTBd3FtA`) and the
Bridge2AI *program* — are named but not described by the crate, so choosing
either would have required facts the crate does not carry. The nine component
crates are represented as `resources` (and, on the packaging side, as
`file_collections`/`distributions`) rather than as the subject.

## Phase 1 — full record

Structure was derived from `Dataset` in `data_sheets_schema_all.yaml` via
`SchemaView` (induced slots, ranges, cardinality, required flags, enums). Two
schema facts changed the shape of the record relative to a naive reading:

- Single-valued object-ranged slots (`Creator.principal_investigator`,
  `FundingMechanism.grantor`, `EthicalReview.contact_person`,
  `LicenseAndUseTerms.contact_person`,
  `ExportControlRegulatoryRestrictions.governance_committee_contact`) are **not**
  inlined and must carry an identifier string, not a nested object. Names,
  emails and ORCIDs for those people were therefore preserved in the adjacent
  narrative slots (`review_details`, `license_terms`, `other_compliance`,
  `maintainer_details`).
- Multivalued object-ranged slots (`Creator.affiliations`,
  `FundingMechanism.grants`, `DatasetProperty.used_software`) are inlined as
  lists and do carry nested objects.

Result: 58 of 94 `Dataset` slots populated.

**Surrogate identifiers.** `Organization.id`, `Grant.id` and `Software.id` are
required by the schema but the crate supplies affiliations, funders, grant
numbers and tool names as bare strings. Surrogate `d4d:`-prefixed identifiers
were minted for these (`d4d:organization-…`, `d4d:grant-…`, `d4d:software-…`,
`d4d:person-jilian-parker`, and `d4d:cm4ai-june-2026-release/…` for
`FileCollection.id`). These are structural keys only; they assert no external
identity. Every non-surrogate identifier in the record (ORCIDs, DOIs, ARKs,
repository URLs) is verbatim from the crate.

## Phase 2 — core record

`CoreDataset` field inventory derived from
`data_sheets_schema_core_all.yaml` / `D4D_Core.yaml`: 79 slots, 55 populated.
Core started from the Phase 1 full values for every shared slot, and the crate
was re-read for the two areas where core's shape differs from full:

- `distributions` (`CoreDistribution`) has an `md5` slot that `FileCollection`
  does not. The crate's five component-level MD5 values were taken from the
  bundle into core, and the same five strings are also carried verbatim in the
  shared `description` text on both sides, so the pair does not disagree.
- `dialect` (`FormatDialect`) was left empty: the crate declares no tabular
  dialect and `is_tabular` is `false`.

No fact was found in Phase 2 that the full record had missed, so no back-port
into full was required from this step.

## Phase 3 — source and provenance audit

**Provenance.** Read history for this run contains only: the three instruction
files, `CM4AI_crate_only.txt`, the two schema files (via `SchemaView`),
`src/data_sheets_schema/d4d_pair_consistency.py`, and this run's own outputs. No
prior full or core D4D, no evaluation, no reconciliation report, no web content.
Confirmed against the Phase 1/2/3 allowlists.

**String-level check.** Every string leaf in the full record was compared
against the whitespace-normalised source bundle. All direct quotations matched
verbatim; the remaining values are either surrogate identifiers, or narrative
written by this run that was then individually checked against the crate.

**Corrections made during Phase 3** (all applied to full first, then re-derived
into core):

1. `acquisition_methods[0].description` said component crates recorded the
   release's four-modality `rai:dataCollectionType` list "several of them
   omitting AP-MS". Recount against the crate: **eight of nine** components
   record `Perturb-seq; IF imaging; SEC-MS` without AP-MS, and the only one that
   records the four-modality list is the SEC-MS KOLF2 differentiation package,
   which contains no AP-MS data itself. Corrected and the oddity stated.
2. `confidential_elements[0]` said "every component crate that states it".
   Verified: **all nine** components state `confidentialityLevel: Unrestricted`.
   Hedge removed.
3. `license_and_use_terms.license_terms` mis-counted the CC0 components as "two
   … and the …". Verified: **three** components (EndoTag AP-MS paclitaxel,
   EndoTag AP-MS vorinostat, SEC-MS KOLF2 differentiation) declare CC0 1.0; the
   other six declare CC BY-NC-SA 4.0 `deed.en`; the release root declares CC
   BY-NC-SA 4.0 without `deed.en`.
4. Following (3), `prohibited_uses` for commercial use was over-broad. The
   release-level CC BY-NC-SA licence does **not** propagate to the three CC0
   components, and the record now says so rather than asserting a blanket
   non-commercial restriction.

**Internal inconsistencies found in the crate and recorded rather than
resolved** (the crate gives no basis for choosing between the alternatives):

- `contentSize` is `"19.9 TB"` while `evi:totalContentSizeBytes` is
  `21051331945400`. Those are not equal under decimal (21.05 TB) or binary
  (19.15 TiB) reading. Recorded as a `DataAnomaly`; `total_size_bytes` carries
  the machine-readable figure.
- The ethics contact is spelled `Vardit Ravistky` in `ethicalReview` and
  `Ravitsky, V` in the author records; the contact email is at
  `thehastingscenter.org` while the author record gives the affiliation as
  University of Montreal. Both recorded in `ethical_reviews[0].review_details`.
- `dataGovernanceCommittee` is `"Jilian Parker"`; the author list contains
  `"Parker, J"` (ORCID 0000-0003-4535-3486, UCSD). The crate does not link them,
  so they were **not** merged; the governance contact carries a surrogate id and
  an explicit note that the crate supplies no identifier.
- The author list carries two spellings of UCSD (`University of California San
  Diego` and `University of California, San Diego`); both are kept verbatim as
  `Organization.name` and share one surrogate id.
- Three components declare `isPartOf` two different releases (January 2026 and
  June 2026), and the EndoTag AP-MS components carry a `citation` for the **March
  2025** release under DOI `10.18130/V3/K7TGEM`, not for this release. Recorded
  in `version_access.version_details` and `related_datasets` as references, not
  as version lineage, because the crate does not state a lineage.
- `funder` string `"Dutch Research Council: NWO, 019.231EN.013"` is ambiguous
  between "NWO" as a second award token and as the funder's acronym. Read as the
  acronym (`Dutch Research Council (NWO)`, grant `019.231EN.013`). Flagged here
  as an interpretive call.

**Scope discipline.** Where the crate asserts a value only for a component, the
record says so (component-level release dates, versions, licences, collection
timeframes, publishers). Release-level and component-level values are never
merged.

## Phase 4 — strict full/core reconciliation

Shared slots were derived at run time from `Dataset` and `CoreDataset` with
`SchemaView` by the repository validator, not from a hand-written list.

- **Schema-identical shared slots: 76.** All present-or-absent identically and
  deeply equal, including every narrative field. Core condenses nothing.
- **Projected slots: `resources`.** 9 component crates on both sides, matched by
  `id` with equal coverage; every schema-identical nested slot deeply equal.
  Full-only nested content dropped from the core projection is `citation` (each
  component's Dataverse citation string), which `CoreDataset` does not define.
- **Full-only top-level slots:** `citation`, `file_collections`,
  `related_datasets`, `total_size_bytes`.
- **Core-only top-level slot:** `distributions`. (`dialect` left empty.)

**Related-content semantic review (`file_collections` ↔ `distributions`).**
Reviewed all nine pairs individually, not merely by the validator's
deterministic match:

| Component path | name | description | declared size | MD5 |
|---|---|---|---|---|
| `AP-MS/apms-paclitaxel-rocrate/` | equal | equal | 441.2 GB | none in crate; absent both sides |
| `AP-MS/apms-vorinostat-rocrate/` | equal | equal | 532.5 GB | none in crate; absent both sides |
| `Images/paclitaxel/` | equal | equal | 2.6 GB | `9422486c…` in core `md5` and in both descriptions |
| `Images/untreated/` | equal | equal | 3.2 GB | `0b4d129f…` likewise |
| `Images/vorinostat/` | equal | equal | 2.8 GB | `ac577109…` likewise |
| `mass-spec/iPSCs/` | equal | equal | 1.11 TB | none in crate; absent both sides |
| `mass-spec/cancer-cells/` | equal | equal | 910 GB | `cb67e774…` likewise |
| `Perturb-Seq/sra/` | equal | equal | 16.7 TB | `cbdb263b…` likewise |
| `Perturb-Seq/cell-atlas/` | equal | equal | 177.35 GB | `1cafefa3…` likewise |

Paths, names and descriptions are identical across the pair. `FileCollection`
carries `collection_type`, `version`, `license`, `doi` and `id`, which
`CoreDistribution` does not define; `CoreDistribution` carries `md5`, which
`FileCollection` does not. No value contradicts its counterpart.

- `total_file_count` is absent from both, and no distribution carries `bytes`:
  the bundle collapsed per-file inventories, so no file count or per-file byte
  count exists to reconcile.
- `total_size_bytes` (full-only) does not conflict with any distribution value
  because none is stated at that level.
- `is_tabular: false` in both; `dialect` correctly empty in core.
- Top-level identity, version and access facts (`id`, `doi`, `version`,
  `license`, `publisher`, `version_access`, `distribution_dates`,
  `external_resources`) agree with the component `resources` and with each
  other; component-level divergences in licence, version and release date are
  stated as component-level facts rather than contradicting the release level.

**Zero unresolved contradictions within or between the two records.**

## What the crate could NOT support at all

This is the primary result of the arm. 36 of 94 `Dataset` slots and 24 of 79
`CoreDataset` slots are empty because the crate carries no evidence for them.
Grouped by D4D area:

**Human-subject / consent machinery (D4D_Human, D4D_Ethics) — vacuously empty.**
`collection_notifications`, `collection_consents`, `consent_revocations`,
`participant_privacy`, `participant_compensation`, `data_protection_impacts`.
The crate states the release is exempt (commercially available de-identified
cell lines, no human subjects), so these are genuinely inapplicable rather than
undocumented. The crate *does* support the determination itself
(`human_subject_research`, `informed_consent`, `at_risk_populations`,
`is_deidentified`), including two `d4d:`-namespaced fields the packager added.

**Composition structure (D4D_Composition) — substantively empty.**
`subsets`, `splits`, `relationships`, `subpopulations`, `content_warnings`,
`variables`, `parent_datasets`. The crate names its component datasets and their
sizes but never describes instance-level structure: no train/test splits, no
relationships between instances, no variable-level metadata, no schema of the
tabular components. `evi:schemaCount: 20` asserts that twenty schemas exist
inside the package, but the reduced bundle does not contain them, so nothing can
be said about any variable. This is the largest single gap.

**Preprocessing and labelling (D4D_Preprocessing) — almost entirely empty.**
`cleaning_strategies`, `labeling_strategies`, `imputation_protocols`,
`annotation_analyses`, `machine_annotation_tools`. Only one
`preprocessing_strategies` entry could be written, and it comes from free text
inside a single component crate's `description` (Bruker timsTOF acquisition,
Spectronaut processing, R/MSstats downstream), not from any structured field.
`rai:dataCollection` points at a publication for method detail rather than
stating it — and that publication is outside this arm's boundary.

**Uses (D4D_Uses) — partly empty.** `discouraged_uses`, `use_repository`. The
crate states prohibited uses and intended uses but never distinguishes
discouraged-but-permitted uses, and lists no repository of works using the data.

**Maintenance (D4D_Maintenance) — partly empty.** `errata`,
`extension_mechanism`. The crate has a maintenance plan and a retention
commitment but no errata channel and no mechanism for third-party contribution
or extension.

**Distribution and packaging metadata.** `total_file_count`, `compression`,
`download_url`, `page`, `issued`, `created_on`, `last_updated_on`,
`created_by`, `modified_by`, `was_derived_from`, `conforms_to_class`,
`conforms_to_schema`. Several of these are absent only because the bundle
collapsed the file inventories; `datePublished` was captured as
`distribution_dates` rather than `issued` because the crate mixes ISO dates
(`2026-06-30`, `2026-05-22T13:23:35+00:00`) with US-format dates (`02/28/2025`,
`10/13/25`) that a `datetime`-ranged slot cannot hold without silently
normalising a source string.

**Third-party sharing / direct collection.** `third_party_sharing`,
`direct_collection` — no statement either way in the crate.

## Crate content that D4D has no slot for

The converse gap, recorded here because it is part of the same measurement:

- **13 subject annotations** in the crate's `about` array — 7 MeSH terms (Breast
  Neoplasms D001943, Induced Pluripotent Stem Cells D057026, CRISPR-Cas Systems
  D064113, Mass Spectrometry D013058, Fluorescent Antibody Technique D005453,
  Paclitaxel D017239, Vorinostat D000077337), 4 EDAM topics (Proteomics
  topic_0121, RNA-Seq topic_3170, Functional genomics topic_3320, Machine
  learning topic_3474) and 2 Cellosaurus cell lines (MDA-MB-468 CVCL_0419,
  KOLF2.1J CVCL_B5P3). `Dataset` has no dataset-level subject/topic slot;
  `Instance.data_topic` and `Instance.data_substrate` are single-valued and
  scoped to an instance type. Only the two Cellosaurus identifiers survive, in
  prose inside `sampling_strategies[0].source_data`. The other eleven identifiers
  are lost; their labels partly overlap `keywords`, which the crate supplies
  separately as untyped strings.
- **`fairscapeVersion: 1.1.3`** — the packaging tool version. `conforms_to`
  carries the RO-Crate 1.2 profile, but there is no slot for the generating
  framework's version.
- **The AI-readiness self-assessment as a structure.** Its 24 findable /
  accessible / interoperable / reusable / provenance / characterisation /
  ethics / sustainability / computability assertions have no D4D home. Only its
  quantitative observations were retained (checksum coverage 8/55859, 0 entities
  with summary statistics, 20 schemas, 6 software instances, 1976 computations,
  53877 datasets), as `instances` and `anomalies`.
- **The provenance graph itself.** `localEvidenceGraph` links and the
  `EVI#inputs`/`EVI#outputs` edges (samples, instruments, experiments,
  computations) that make this an EVI provenance package are counted but not
  representable — D4D has no slot for a computational provenance graph.

## Commands run

```bash
poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_all.yaml \
  -C Dataset data/d4d_concatenated/claudecode_agent_crate_only/2026-07-28_claude-opus-5-crateonly_rep3/CM4AI_d4d.yaml
poetry run linkml-term-validator validate-data \
  data/d4d_concatenated/claudecode_agent_crate_only/2026-07-28_claude-opus-5-crateonly_rep3/CM4AI_d4d.yaml \
  --schema src/data_sheets_schema/schema/data_sheets_schema_all.yaml --target-class Dataset
poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml \
  -C CoreDataset data/d4d_concatenated/claudecode_agent_crate_only_core/2026-07-28_claude-opus-5-crateonly_rep3/CM4AI_d4d_core.yaml
poetry run linkml-term-validator validate-data \
  data/d4d_concatenated/claudecode_agent_crate_only_core/2026-07-28_claude-opus-5-crateonly_rep3/CM4AI_d4d_core.yaml \
  --schema src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml --target-class CoreDataset
poetry run python -m data_sheets_schema.d4d_pair_consistency \
  --full .../CM4AI_d4d.yaml --core .../CM4AI_d4d_core.yaml --sync-core
poetry run python -m data_sheets_schema.d4d_pair_consistency \
  --full .../CM4AI_d4d.yaml --core .../CM4AI_d4d_core.yaml
poetry run d4d provenance record --project CM4AI --method claudecode_agent_crate_only \
  --label 2026-07-28_claude-opus-5-crateonly_rep3 \
  --input-bundle data/preprocessed/concatenated/CM4AI_crate_only.txt
```

## Final results

| Check | Result |
|---|---|
| Full — LinkML schema validation | No issues found |
| Full — ontology term validation | Validation passed |
| Core — LinkML schema validation | No issues found |
| Core — ontology term validation | Validation passed |
| Pair consistency (`--sync-core`) | PASS: 76 schema-identical slots; projected `resources` |
| Pair consistency (independent re-run) | PASS: 76 schema-identical slots; projected `resources` |
| Related-content warning | `file_collections` ↔ `distributions`, 9 deterministic matches, 0 unmatched — semantically reviewed above, no contradictions |
| Provenance record | present, `record_mode: live` |

`--sync-core` changed nothing: core had been derived from the Phase 3-audited
full record, so the independent re-run is a genuine second check rather than a
confirmation of its own edit.

Files changed by this run: only the three outputs plus the provenance record.
No repository file outside the two run directories was modified.

Line counts (informational metadata only, not a quality gate): full 1,367 lines
/ 66,107 bytes; core 1,201 lines / 56,580 bytes.
