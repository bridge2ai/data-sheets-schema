# CM4AI full/core reconciliation — 2026-07-28_claude-opus-5-programme-deprimed_rep1

- Agent runtime: Claude Code
- Provider: Anthropic
- Model: claude-opus-5[1m]
- Mode: four-phase project agent, pinned-referent
- Temperature: 0.0
- Generated: 2026-07-28
- Arm: DE NOVO WITH CRATE (documents + RO-Crate evidence)

## Artifacts

| Role | Path |
| --- | --- |
| Full | `data/d4d_concatenated/claudecode_agent_crate/2026-07-28_claude-opus-5-programme-deprimed_rep1/CM4AI_d4d.yaml` |
| Core | `data/d4d_concatenated/claudecode_agent_crate_core/2026-07-28_claude-opus-5-programme-deprimed_rep1/CM4AI_d4d_core.yaml` |
| Report | `data/d4d_concatenated/claudecode_agent_crate_core/2026-07-28_claude-opus-5-programme-deprimed_rep1/CM4AI_reconciliation.md` |

## Pinned referent as applied

The subject of both records is the CM4AI data-release programme as an ongoing
quarterly release series.

1. **Top level is the programme.** `id` is `https://cm4ai.org/data-releases/`,
   the programme's canonical release page. No `doi`, `version`, `issued`,
   `total_size_bytes` or `total_file_count` appears at top level. `status`
   carries the programme's ongoing character ("Active. Quarterly releases are
   continuing …") rather than a release state.
2. **`resources` are the quarterly releases**, four entries in date order, each
   with its own `doi`, `version`, `issued`, `total_file_count`, `page`,
   `license`, `publisher` and `citation`:

   | Release | DOI | Dataverse version | Publication date | Files | Status |
   | --- | --- | --- | --- | --- | --- |
   | March 2025 | 10.18130/V3/B35XWX | 1.4 | 2025-03-03 | 6 | superseded |
   | June 2025 | 10.18130/V3/F3TD5R | 2.1 | 2025-07-01 | 21 | superseded |
   | October 2025 | 10.18130/V3/K7TGEM | 2.1 | 2025-10-31 | 8 | superseded |
   | June 2026 | 10.18130/V3/HIGT4C | 2.0 | 2026-06-17 | 10 | **current** |

   `total_size_bytes` appears on one resource only, the June 2026 release
   (21,051,331,945,400), because only that release's crate reports an exact byte
   count.
3. **`file_collections` is populated** with the ten-file inventory of the current
   release (HIGT4C): name, path, `collection_type`, `compression`, `license`,
   `issued`, `page`, and a description carrying the Dataverse-displayed size and
   the MD5 checksum.
4. **Modalities live inside the current release**, not at top level. The June
   2026 resource carries nine nested `resources`, one per RO-Crate sub-crate:
   two AP-MS (paclitaxel, vorinostat), three immunofluorescence (untreated,
   paclitaxel, vorinostat), two SEC-MS (KOLF2 differentiation series, treated
   MDA-MB-468) and two Perturb-seq (cell atlas, raw sequence data). Modality
   composition also appears in top-level `instances`, `collection_mechanisms`
   and `relationships` at programme scope.

### What the programme framing made awkward to place

- **`file_collections` at top level describes one release, not the programme.**
  The pinned referent requires this, and it is the only place in the record where
  a top-level slot is scoped to a single release. Every entry names the release
  explicitly in its description so the scope is not lost.
- **`is_tabular`, `compression` and `conforms_to` are release properties.**
  `compression: zip` and `conforms_to: https://w3id.org/ro/crate/1.2` were placed
  on the June 2026 resource rather than at top level. `is_tabular: false` was
  kept at top level because it holds across every release; its evidence is the
  crate's format inventory (`.d`, `.d directory group`, `fastq.gz`, `h5`, `h5ad`,
  `image/jpeg`, `pdf` alongside `.tsv`/`csv`), which is predominantly
  non-tabular. This is the one top-level scalar that rests on a reading of the
  evidence rather than a direct statement.
- **A fifth release is named but not represented.** The CM4AI archive list names
  a "May 2024 Data Release" and the project preprint cites an earlier deposit,
  `doi:10.18130/V3/DXWOS5`. Neither has a Dataverse record in the corpus, and
  neither is in the pinned four. They are recorded in
  `version_access.versions_available`, in `distribution_dates.description`, and
  DXWOS5 additionally as a `related_datasets` entry with relationship
  `is_referenced_by`.
- **Governance narratives are stated per release but are programme-wide.**
  Ethics, licence, prohibited uses, biases, limitations, maintenance and
  completeness statements are byte-identical across releases in the corpus, so
  they were placed once at programme level rather than duplicated onto four
  resources. Release-specific facts stayed on the resources.
- **`Person` and `Organization` are not inlinable** at `principal_investigator`,
  `contact_person`, `reviewing_organization`, `governance_committee_contact` or
  `grantor` — the schema types them as identifier references. Names, emails and
  ORCIDs therefore appear in the adjacent `description` / `*_details` text so no
  identifying information is lost. `Creator.affiliations` is the one place the
  schema does inline `Organization`, so those carry `id` + `name`.

## Phase 1 — full record

Structure derived at runtime from class `Dataset` in
`data_sheets_schema_all.yaml` via `SchemaView.class_induced_slots`, including
every nested class range and enum. No prior D4D was read as a template.

Validation failures found and fixed during Phase 1:

- `scope_impact` used on `DatasetBias`; the slot belongs to `DatasetLimitation`
  only. Removed from both bias entries.
- `Person` / `Organization` / `Grantor` supplied as inline objects at scalar
  reference slots. Replaced with identifier strings; names moved into
  surrounding prose.
- `Creator.affiliations` (multivalued `Organization`) requires inlined objects,
  unlike the scalar reference slots. Restored as `id` + `name` objects.

Slots deliberately left unpopulated because the corpus does not support them:
`content_warnings`, `data_protection_impacts`, `imputation_protocols`,
`annotation_analyses`, `participant_privacy`, `participant_compensation`,
`collection_notifications`, `collection_consents`, `consent_revocations`,
`splits`, `subsets`, `variables`, `parent_datasets`, and top-level `language`.
Asserting absence for these would have been an unsupported claim rather than a
recorded fact.

Numeric values not recorded: exact byte counts for individual files. Dataverse
displays rounded sizes ("3.8 GB", "113.3 KB") only, so `FileCollection.total_bytes`
and `CoreDistribution.bytes` are omitted and the displayed size is quoted in the
description instead.

## Phase 2 — core record

Structure derived from `CoreDataset` in `data_sheets_schema_core_all.yaml` and
`D4D_Core.yaml`. Runtime slot comparison: `Dataset` induces 94 slots,
`CoreDataset` 79, with 77 shared. `resources` is the only shared slot whose range
differs (`Dataset` vs `CoreDataset`). Core-only slots are `distributions` and
`dialect`.

- Every shared slot present in full was carried into core unchanged, including
  narrative fields. Nothing was condensed, paraphrased or reordered.
- The 17 full-only slots were dropped. Six of them were populated in full and are
  therefore core's only content loss: `citation`, `direct_collection`,
  `file_collections`, `related_datasets`, `relationships`, `third_party_sharing`.
- `distributions` was built from full's `file_collections` plus the Dataverse
  checksums, adding the file-level properties core has and full lacks: `md5`,
  `format`, `media_type`.
- `dialect` was left empty. The corpus says nothing about delimiters, quoting or
  headers, and the released data are not predominantly tabular.
- Phase 2 discovered no fact the documents support that Phase 1 had missed, so
  nothing was back-ported into full. The only content core adds — the ten MD5
  checksums — is already stated verbatim in full's `file_collections`
  descriptions, which was verified mechanically.

## Phase 3 — source and provenance audit

### Provenance

Factual inputs read: `data/preprocessed/concatenated/CM4AI_preprocessed_with_crate.txt`
only. Structure/selection references read: `data_sheets_schema_all.yaml`,
`data_sheets_schema_core_all.yaml`, `D4D_Core.yaml`,
`data/preprocessed/source_manifest.yaml`, `data/ro-crate_packages/crate_manifest.yaml`.
Procedure documents read: `.claude/agents/d4d-provenance-guard.md`,
`.claude/commands/d4d-full-core.md`, `.claude/commands/d4d-agent.md`.

No prior D4D record, evaluation or reconciliation report was read. Nothing under
`data/d4d_concatenated/` or `data/d4d_individual/` was read other than this run's
own outputs; the only inspection of those directories was a directory listing to
confirm the target version label did not already exist. None of the withheld
artifacts (`CM4AI_crate_d4d.yaml`, `CM4AI_crate_mapped_d4d.yaml`,
`ro-crate-linkml.yaml`, `ro-crate-datasheet.html`, any `ro-crate-preview.html`)
was opened. No live web content was fetched.

One boundary judgement: `crate_manifest.yaml` reports an exact byte size for
`cm4ai_release_metadata.zip` (1,203,765). Because the manifest is a
structure/selection reference and not a fact source, that number was **not**
used; the record carries the Dataverse-displayed "1.1 MB" instead.

### Mechanical verification against the corpus

- All 10 file names and all 10 MD5 checksums appear verbatim in the source
  bundle, and each core `md5` matches the checksum quoted in the corresponding
  full `file_collections` description. 0 mismatches.
- All DOIs, MassIVE accessions and ORCID identifiers asserted anywhere in either
  record appear verbatim in the source bundle. 0 unverified identifiers.
- All `Instance.counts` values (1,374; 53,788; 7,023; 11,739; 55,859) appear in
  the source bundle in the form the source uses.
- 138 narrative quoted spans were checked against the corpus. All trace to source
  text. Deviations are confined to normalization of PDF-extraction artifacts in
  the preprint — stray page numbers and single stray characters mid-sentence
  ("data,\nE\nsoftware"), hyphenated line breaks ("MDA-MB-\n468"), and superscript
  reference markers ("model31") — plus reassembly of the Creative Commons deed
  text, which the HTML capture fragments across footnote anchors. No factual
  content was altered.

### Source conflicts found, and how they were resolved

| # | Conflict | Resolution |
| --- | --- | --- |
| 1 | cm4ai.org labels HIGT4C the "June 2026 Data Release" but displays "Released on: June 17, 2025". Dataverse gives publication date 2026-06-17. | Dataverse authoritative, per instruction. Recorded as an error of one year in `errata` and in the June 2026 resource description. |
| 2 | HIGT4C version: Dataverse "Version 2.0"; release crate `version: "1.0"`; crate citation string says V1 and year 2025; manifest records version 2 released 2026-07-15T20:28:19Z. | Dataverse authoritative: `version: "2.0"`, `last_updated_on: 2026-07-15T20:28:19Z`. Crate values recorded in the resource description and in `version_access.version_details`. |
| 3 | HIGT4C date published: Dataverse 2026-06-17; crate `datePublished` 2026-06-30. | Dataverse authoritative. Crate value recorded in the resource description. |
| 4 | Release size: crate `contentSize` "19.9 TB"; crate `evi:totalContentSizeBytes` 21,051,331,945,400 (≈21.05 TB); cm4ai.org portal "Data volume 21.4 TB". | Machine-readable byte count used for `total_size_bytes`; all three figures recorded in the resource description, with the portal figure scoped to the programme rather than the release. |
| 5 | Number of proteins imaged by IF: 563 (March 2025 archives), 464 (June 2026 sub-crates), 523 (cm4ai.org flagship-datasets section). | Not resolved into one number. Each figure is attributed to its own scope in `instances`, and 464 is carried on the June 2026 IF file collections and sub-crates. |
| 6 | March 2025 version: landing page "Version 1.4"; recommended citation "V1". | Landing page used for `version`; both recorded in `version_access.version_details`. |
| 7 | Governance contact spelling: Dataverse "Jillian Parker"; crate "Jilian Parker". | Dataverse spelling used; crate spelling recorded in `regulatory_restrictions.description`. |
| 8 | Ethics contact spelling: Dataverse "Vardit Ravitsky"; crate "Vardit Ravistky". | Dataverse spelling used; crate spelling recorded in `ethical_reviews[0].review_details`. |
| 9 | Project end date: NIH RePORTER project end 2026-08-31; release maintenance plan says updates continue "through the end of the project in November 2026". | Both recorded in `collection_timeframes`, explicitly unreconciled — the corpus gives no basis to prefer one. |
| 10 | Data collection timeframe end: release crate "6/1/2026"; AP-MS sub-crates "1/31/2026". | Release-crate value used for the programme timeframe; the sub-crate value recorded as consistent with their earlier packaging for a January 2026 release. |
| 11 | Sub-crate licences: release is CC BY-NC-SA 4.0, but the two AP-MS sub-crates and the KOLF2 SEC-MS sub-crate are marked CC0 1.0. | Both recorded — release-level licence at programme and resource level, per-sub-crate licence on each nested resource, with the divergence called out in `license_and_use_terms.description`. |
| 12 | cm4ai.org marks AP-MS interactomes and iPSC IF images "coming soon", but the June 2026 release ships AP-MS. | Recorded in `missing_data_documentation` with an explicit note that the portal statement is stale with respect to the current release. |
| 13 | Ambiguous date formats: IF sub-crates `datePublished` "02/28/2025"; crate collection timeframe "9/1/2022"/"6/1/2026". | Read as month/day/year (28 cannot be a month; 9/1/2022 matches the RePORTER project start of 2022-09-01) and recorded as ISO dates, with the ambiguity stated in each description. |

One schema-format artifact, not a source conflict: the `issued`, `created_on`
and `last_updated_on` slots have range `datetime` and reject a bare date, so
Dataverse publication dates are written `YYYY-MM-DDT00:00:00Z`. The midnight time
component is a formatting requirement, not evidence. The exact source date is
restated in each resource description.

No unsupported, stale or mis-scoped assertion was found in either record during
the audit, and no correction to the facts was required. Internal consistency was
verified mechanically: repeated DOIs, versions, dates, counts, licence URLs and
contact identifiers agree within each file and between them.

## Phase 4 — strict full/core reconciliation

Shared slots derived at runtime with LinkML `SchemaView`; no hand-written field
list was used.

- **76 schema-identical slots** verified deeply identical and identically
  present/absent in both records.
- **1 projected slot**: `resources`. Coverage is equal — four release resources
  matched by `id`, and the June 2026 resource's nine nested sub-crate resources
  matched by `id`. Every nested schema-identical slot is deeply identical.
  Full-only nested slots (`total_file_count`, `total_size_bytes`, `citation`)
  are omitted from the core projection, as required.
- **Related-content review** for the one warning the validator raised,
  `$.file_collections` ↔ `$.distributions` (10 deterministic matches, 0 unmatched
  core distributions):
  - names and `path` identical for all 10;
  - descriptions identical for all 10, so the size and provenance narrative is
    the same on both sides;
  - `compression: zip` on both sides for all 10; core additionally carries
    `format: ZIP` and `media_type: application/zip`, consistent with the
    Dataverse file-type facet "Archive (10)";
  - each core `md5` is the checksum quoted in the matching full description;
  - byte counts are absent on both sides (`total_bytes` and `bytes`), so there is
    no numeric disagreement to reconcile;
  - scope agrees: all 10 entries describe the current release, and the June 2026
    resource's `total_file_count` of 10 equals the number of distributions and
    the number of file collections.
- `is_tabular` agrees (`false` in both). `dialect` is absent from core, and no
  format assertion in full contradicts its absence.
- Top-level identity and access facts agree between the two records and with the
  resources: `license`, `publisher`, `page`, `status` and `keywords` are
  identical; `version_access.latest_version_doi`
  (`https://doi.org/10.18130/V3/HIGT4C`) equals the `id` of the resource marked
  current; `distribution_dates.release_dates` lists exactly the four resource
  `issued` values plus the version-2 release timestamp.
- Historical versus current releases are distinguished by `status` on each
  resource rather than treated as contradictions. The differing composition
  statements across releases (AP-MS present in June 2026, absent in October
  2025; IF protein counts of 563 versus 464) are scoped to their own release and
  are not reconciled into a single value.

### Nothing diverged

After Phase 3 made the full record canonical, `--sync-core` produced no change to
the core file. The independent check without `--sync-core` passes. There is no
unresolved contradiction within either record or between them.

## Commands run

```bash
poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_all.yaml \
  -C Dataset data/d4d_concatenated/claudecode_agent_crate/2026-07-28_claude-opus-5-programme-deprimed_rep1/CM4AI_d4d.yaml

poetry run linkml-term-validator validate-data \
  data/d4d_concatenated/claudecode_agent_crate/2026-07-28_claude-opus-5-programme-deprimed_rep1/CM4AI_d4d.yaml \
  --schema src/data_sheets_schema/schema/data_sheets_schema_all.yaml --target-class Dataset

poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml \
  -C CoreDataset data/d4d_concatenated/claudecode_agent_crate_core/2026-07-28_claude-opus-5-programme-deprimed_rep1/CM4AI_d4d_core.yaml

poetry run linkml-term-validator validate-data \
  data/d4d_concatenated/claudecode_agent_crate_core/2026-07-28_claude-opus-5-programme-deprimed_rep1/CM4AI_d4d_core.yaml \
  --schema src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml --target-class CoreDataset

poetry run python -m data_sheets_schema.d4d_pair_consistency \
  --full data/d4d_concatenated/claudecode_agent_crate/2026-07-28_claude-opus-5-programme-deprimed_rep1/CM4AI_d4d.yaml \
  --core data/d4d_concatenated/claudecode_agent_crate_core/2026-07-28_claude-opus-5-programme-deprimed_rep1/CM4AI_d4d_core.yaml \
  --sync-core

poetry run python -m data_sheets_schema.d4d_pair_consistency \
  --full data/d4d_concatenated/claudecode_agent_crate/2026-07-28_claude-opus-5-programme-deprimed_rep1/CM4AI_d4d.yaml \
  --core data/d4d_concatenated/claudecode_agent_crate_core/2026-07-28_claude-opus-5-programme-deprimed_rep1/CM4AI_d4d_core.yaml

poetry run d4d provenance record --project CM4AI --method claudecode_agent_crate \
  --label 2026-07-28_claude-opus-5-programme-deprimed_rep1 \
  --input-bundle data/preprocessed/concatenated/CM4AI_preprocessed_with_crate.txt
```

## Crate evidence versus document evidence

The task asked which fields were populated only from crate evidence, and which
crate content was already present in the documents. Findings follow; there was no
expected answer.

### Populated only from crate evidence

These have no counterpart anywhere in the ten document sources:

| Field | Crate source | Value |
| --- | --- | --- |
| June 2026 resource `total_size_bytes` | `evi:totalContentSizeBytes` | 21,051,331,945,400 bytes. The documents give only the portal's "21.4 TB" for the whole programme. |
| June 2026 resource `conforms_to` | crate `conformsTo` | `https://w3id.org/ro/crate/1.2`; the preprint says releases are RO-Crate packaged but names no version. |
| Nine nested sub-crate resources | crate graph entities | Their `id` (ARK), `name`, `description`, `version`, `issued`, `license`, authorship, per-modality content sizes, MassIVE accessions and the `doi:10.25345/C5348GV4S` / FTP content URL for the treated-cancer-cell SEC-MS set. The Dataverse pages list ten opaque ZIP filenames and nothing about what is inside them. |
| `instances` entry for crate entities | `evi:*` counters | 55,859 total entities, 53,877 datasets, 1,976 computations, 6 software instances, 20 schemas, 8 entities with checksums. |
| `anomalies` checksum-coverage item | `ai_ready_score.json` | "0% of files have checksums (8/55859)". |
| `informed_consent.consent_documentation` | `d4d:informedConsent` | "Not applicable — data collected from commercially available de-identified human cell lines (KOLF2.1J iPSC and MDA-MB-468). No primary human subjects research conducted under this release." |
| `at_risk_populations.special_protections` | `d4d:atRiskPopulations` | "None — no human subjects involved; commercially sourced de-identified cell lines only." |
| `human_subject_research.regulatory_compliance` exemption clause | `humanSubjectExemption` | "Exempt — research with commercially available de-identified human cell lines does not constitute human subjects research." The Dataverse pages state "Human Subjects: No" but give no exemption rationale. |
| `regulatory_restrictions.confidentiality_level` | `confidentialityLevel` | `unrestricted`. No document states a confidentiality classification. |
| `funders` beyond the primary NIH award | crate `funder` string | R01HG012351, R01NS131560, U54CA274502, S10 OD026929, DoD W81XWH-22-1-0401, CIRM EDUC4-12804, NWO 019.231EN.013, NCI P30CA023100. Every Dataverse page records only "National Institutes of Health: 1OT2OD032742-01". |
| AP-MS experimental design | sub-crate descriptions | Four biological replicates; each batch comprising an untagged parental control, 10 chromatin-modifier tagged lines and a positive control line, with DMSO vehicle controls. |
| SEC-MS instrumentation and design | sub-crate description | Bruker timsTOF acquisition, Spectronaut quantitation, and replicate counts of Parental 4 / NPC 2 / Neuron 3 / Cardio 2. |
| `collection_timeframes` collection window | `rai:dataCollectionTimeframe` | 2022-09-01 to 2026-06-01. Documents give the funded project period, not a data-collection window. |
| `distribution_formats` format inventory | `evi:formats` | `.d`, `.d directory group`, `.tsv`, `.xml`, `TSV`, `csv`, `executable`, `fastq.gz`, `h5`, `h5ad`, `image/jpeg`, `pdf`, `unknown`. |

### Crate content already present in the documents

For these the crate adds nothing the documents do not already state, often
word-for-word — the Dataverse release pages and the crate's `rai:*` fields are
the same text:

- `rai:dataLimitations` = the Limitations list on every release page.
- `rai:dataBiases` = the Potential Sources of Bias list.
- `rai:dataUseCases` = the Intended Use list (the crate adds only the Ma 2018 /
  Kuenzi 2020 pointers).
- `rai:dataReleaseMaintenancePlan` = the Maintenance Plan block.
- `rai:dataCollectionMissingData` and `completeness` = the Completeness block.
- `prohibitedUses` and `usageInfo` = the Prohibited Uses statement.
- `ethicalReview`, `dataGovernanceCommittee`, `humanSubjectResearch` = the Data
  Governance & Ethics block (the crate misspells two of the three names).
- `license`, `identifier`, `citation`, `associatedPublication`, `keywords`,
  `publisher`, `principalInvestigator`, `contactEmail` = the Dataverse citation
  metadata.
- `copyrightNotice` and `conditionsOfAccess` = the copyright and attribution
  language already carried in the March 2025 release description and the
  project preprint.
- Author list and ORCID/affiliation pairs = the Dataverse author block.

### Reading

The crate's contribution to this record is structural and quantitative rather
than narrative. Everything the crate says *about* the data in prose is already in
the release pages, because both are generated from the same authored metadata.
What the crate adds that the documents cannot supply is the decomposition of ten
opaque ZIP filenames into nine named, versioned, separately licensed and
separately attributed modality datasets with their own accessions and sizes, plus
exact machine-readable counters. Without the crate, the June 2026 release is a
list of filenames; with it, the release has an internal structure that the
`resources` slot can actually hold.

Three crate fields — `d4d:informedConsent`, `d4d:atRiskPopulations` and
`humanSubjectExemption` — are D4D-shaped answers rather than crate-native
metadata, and material taken from them is closer to transcription than
extraction. They are flagged here for that reason. They account for two
`informed_consent` / `at_risk_populations` details and one clause of
`human_subject_research`; nothing else in the record derives from them.

## Validation results

| Check | Result |
| --- | --- |
| `linkml-validate` full (`Dataset`) | No issues found |
| `linkml-term-validator` full | Validation passed |
| `linkml-validate` core (`CoreDataset`) | No issues found |
| `linkml-term-validator` core | Validation passed |
| `d4d_pair_consistency --sync-core` | PASS: 76 schema-identical slots; projected slots=['resources']; no change written |
| `d4d_pair_consistency` (independent) | PASS: 76 schema-identical slots; projected slots=['resources'] |

One warning is emitted by the pair validator, `[semantic-review-required]
$.file_collections <-> $.distributions`. It marks related content requiring human
review; that review is recorded in the Phase 4 section above and found no
divergence.

## Completion audit

1. Every factual input path is on the phase allowlist. ✔
2. No prior generated YAML was read or cited. ✔
3. Every emitted slot and nested object is permitted by the applicable schema,
   including inherited and `slot_usage` constraints. ✔
4. The core record's input full record carries this run's exact label. ✔
5. No Phase 2 discovery required back-porting; none was invented. ✔
6. Schema and ontology term validation pass for both records. ✔
7. The schema-derived pair validator passes. ✔
8. All projected and related content received semantic review. ✔
9. Phase 3 provenance result and Phase 4 consistency result are recorded above. ✔
