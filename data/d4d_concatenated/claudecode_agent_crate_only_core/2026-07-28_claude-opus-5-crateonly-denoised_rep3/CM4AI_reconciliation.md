# CM4AI full/core reconciliation — crate-only arm

- Run label: `2026-07-28_claude-opus-5-crateonly-denoised_rep3`
- Agent runtime: Claude Code; Provider: Anthropic; Model: `claude-opus-5[1m]`
- Mode: four-phase project agent, crate-only; Temperature 0.0; Generated 2026-07-28
- Full: `data/d4d_concatenated/claudecode_agent_crate_only/2026-07-28_claude-opus-5-crateonly-denoised_rep3/CM4AI_d4d.yaml`
- Core: `data/d4d_concatenated/claudecode_agent_crate_only_core/2026-07-28_claude-opus-5-crateonly-denoised_rep3/CM4AI_d4d_core.yaml`
- Sole factual input: `data/preprocessed/concatenated/CM4AI_crate_only.txt`
- Structure authority: `data_sheets_schema_all.yaml` (`Dataset`), `data_sheets_schema_core_all.yaml` (`CoreDataset`), `D4D_Core.yaml`
- Prior D4D factual reuse: prohibited, and none occurred.

## Referent

The record documents the **RO-Crate root entity**:

- `https://fairscape.net/api/ark:59853/rocrate-cell-maps-for-artificial-intelligence-June-2026-data-release`
- "Cell Maps for Artificial Intelligence - June 2026 Data Release (Beta)", version 1.0,
  `datePublished` 2026-06-30, DOI `10.18130/V3/HIGT4C`.

This referent was chosen because it is the only entity the crate itself designates as the
subject: the `ro-crate-metadata.json` descriptor's `about` points at it, and every one of
the nine other `EVI#ROCrate` entities in the graph declares `isPartOf` it. The record is
therefore scoped to **one dated release**, not to the CM4AI project as a programme. The nine
component crates are carried as `resources` (full `Dataset` → core `CoreDataset` projection)
and their package directories as `file_collections` / `distributions`.

## Phase 3 — source and provenance audit

### Provenance

- Only `CM4AI_crate_only.txt` and the three schema files were read for content. No prior D4D
  record, evaluation, reconciliation report, publication, project page, Dataverse page,
  licence page, `CM4AI_preprocessed*.txt`, `data/preprocessed/individual/CM4AI/`,
  `data/raw/CM4AI/`, `source_manifest.yaml`, `CM4AI_crate_d4d.yaml`,
  `ro-crate-linkml.yaml`, `ro-crate-datasheet.html`, or `ro-crate-preview.html` was opened.
- No web content was fetched.
- Class shapes, ranges, cardinality, inlining and enum values were derived at runtime with
  `SchemaView` (`class_induced_slots`), not from any example record.

### Corrections made in Phase 3

1. **`instances[].counts` removed from the IF-imaging instance.** Phase 1 recorded
   `counts: 464`. The schema defines `counts` as "How many instances are there in total";
   the crate's 464 is the number of *proteins of interest imaged*, not a count of image
   instances. Mis-scoped value deleted; the 464 figure retained verbatim in the instance
   description. Both files re-validated.
2. **`issued` datetimes normalised to RFC3339.** The crate gives `datePublished` as
   `2026-06-30` (release) and `02/28/2025` (three IF crates). The schema range is `datetime`,
   which the validator enforces as RFC3339, so these were written as
   `2026-06-30T00:00:00+00:00` and `2025-02-28T00:00:00+00:00`. The time-of-day and UTC
   offset are formatting artefacts of the required range, not crate facts.

### Internal inconsistencies found *inside the crate* (recorded, not resolved)

These are properties of the source, and are preserved rather than smoothed over:

| Finding | Evidence |
|---|---|
| Size stated two ways | Root `contentSize` is `19.9 TB`; `evi:totalContentSizeBytes` is `21051331945400` (≈21.05 TB decimal / 19.15 TiB). Neither reading reproduces "19.9 TB". `total_size_bytes` uses the byte-precise field. |
| Entity vs file counts | `evi:datasetCount` 53877 + `evi:computationCount` 1976 + `evi:softwareCount` 6 = `evi:totalEntities` 55859. `ai_ready_score.json` calls 55859 "files" ("8/55859"). `total_file_count` uses 53877, the dataset-entity count. |
| Stale citations in component crates | Six component crates carry a `citation` naming the **March 2025** release (DOIs `10.18130/V3/B35XWX`, `10.18130/V3/K7TGEM`) while sitting inside the June 2026 release. Recorded under `version_access.version_details` with explicit historical scope; not promoted to the release-level `citation`. |
| Release-level citation year | The root `citation` for the June 2026 release is dated "2025". Kept verbatim. |
| Licence conflict across levels | Root licence is CC BY-NC-SA 4.0. The two EndoTag AP-MS crates and the SEC-MS KOLF2 crate declare CC0 1.0; the IF, SEC-MS cancer-cell and perturb-seq crates declare CC BY-NC-SA 4.0 `deed.en`. Both levels recorded — root in `license`, components in `license_and_use_terms.license_terms` and per-resource `license`. |
| Copyright conflict | Root: "Copyright (c) 2026 The Regents of the University of California…"; IF crates: "Copyright (c) 2025 by The Board of Trustees of the Leland Stanford Junior University". Both in `ip_restrictions.restrictions`. |
| Collection timeframe differs by level | Root `rai:dataCollectionTimeframe` 9/1/2022–6/1/2026; AP-MS and SEC-MS cancer-cell crates 9/1/2022–1/31/2026; IF and perturb-seq raw crates 9/1/2022–10/13/25. Root used for `collection_timeframes`; component values recorded in `timeframe_details` as historical scope. |
| Collection-type list differs by level | Root `rai:dataCollectionType` includes AP-MS; most component crates omit it. Noted in `collection_mechanisms`. |
| Malformed / dangling values | `identifier` on the SEC-MS cancer-cell crate is `https://doi.org/doi:10.25345/C5348GV4S` (double `doi:`); several `isPartOf` ARKs end in a stray comma; `conditionsOfAccess` refers to "the Related Publications below", which has no referent in the JSON. The DOI was normalised to `10.25345/C5348GV4S` to satisfy the schema pattern; the rest were left alone. |
| Name spelling | `ethicalReview` spells "Vardit Ravistky"; the author list has "Ravitsky, V". Quoted verbatim in `ethical_reviews.review_details`; no identifier merge was asserted. |

### Values that are derived rather than quoted

Flagged for transparency; each is a reading of a crate field, not outside knowledge:

- `is_tabular: false` — from `evi:formats` (`image/jpeg`, `fastq.gz`, `h5`, `h5ad`, `.d`, `pdf` …).
- `license_and_use_terms.data_use_permission: [no_commercial_use]` — from the NC clause of the
  stated CC BY-NC-SA 4.0 licence.
- `known_biases[].bias_type: representation_bias` and the four `known_limitations[].limitation_type`
  values — enum classification of verbatim `rai:dataBiases` / `rai:dataLimitations` / `completeness` text.
- `instances[].data_topic` — release-level `about` terms (EDAM/MeSH) assigned to the modality they name.
- `creators[Ideker].principal_investigator` — the crate's `principalInvestigator` is the plain
  string "Trey Ideker"; it was linked to ORCID `0000-0002-1708-8454` ("Ideker, T", UCSD) by
  same-document name match, corroborated by `contactEmail: tideker@health.ucsd.edu`.
- `resources[].page` for the MassIVE-backed components — taken from the crate's `sameAs`.
- `collection_mechanisms[0].mechanism_details` — the crate's single string
  "Perturb-seq; IF imaging; SEC-MS; AP-MS" split on its own delimiter into four items.

### Schema limitations encountered

- `Person`, `Organization`, `Grantor` and `Grant` carry required identifiers, so
  `principal_investigator`, `contact_person`, `governance_committee_contact` and `grantor`
  are **references, not inlined objects**, and a standalone `Dataset` instance has nowhere to
  define the referenced entity. Names and emails from the crate (Trey Ideker /
  tideker@health.ucsd.edu; Jilian Parker; the two ethics contacts) are therefore preserved in
  adjacent narrative slots (`review_details`, `maintainer_details`, `description`) and the
  reference ids are minted under
  `https://w3id.org/bridge2ai/data-sheets-schema/cm4ai-crate-only/…`. Minted ids are
  structural keys only; they assert nothing.
- The crate's per-package **MD5 checksums have no home in the full record**: `FileCollection`
  exposes no `hash`/`md5` slot and `Dataset` has no reachable `File`. They are carried in core
  `distributions[].md5` (`CoreDistribution` does have `md5`). This is the one fact the core
  record holds that the full record structurally cannot, and it was not back-ported because no
  correct full-schema slot exists.
- Component `contentSize` values ("441.2 GB", "16.7TB", …) were not converted to
  `total_bytes`/`bytes` integers, because converting would require assuming GB = 10⁹ vs 2³⁰.
  They are quoted verbatim in the collection/distribution descriptions.

## Phase 4 — strict full/core reconciliation

- Shared slots derived at runtime with `SchemaView`: **76 schema-identical**, **1 projected**
  (`resources`).
- Core was built by copying every identity slot from the Phase 3-audited full record verbatim
  (deep copy, list order preserved), so no narrative field was condensed, paraphrased or
  reordered.
- `resources` projection: 9 component crates, identical id sets in both files, deep-equal on
  every identity slot. No full-only nested slot was used inside `resources`, so nothing was
  dropped in the projection.
- Related-content review (`file_collections` ↔ `distributions`), the one warning the
  deterministic validator raises:
  - 9 file collections ↔ 9 distributions, matched 1:1 by `id`; no unmatched distributions.
  - `path` agrees exactly for all 9 (`AP-MS/apms-paclitaxel-rocrate/`, `Images/paclitaxel/`,
    `mass-spec/iPSCs/`, `Perturb-Seq/sra/`, …), derived from each component's
    `ro-crate-metadata` path.
  - `name` agrees exactly for all 9.
  - Content sizes are stated identically in both descriptions; no size is asserted numerically
    in either file, so no numeric conflict is possible.
  - MD5 appears in 6 of 9 distributions; the other 3 (both EndoTag AP-MS crates, SEC-MS KOLF2)
    state explicitly that the crate records no package checksum. No collection claims a
    checksum, so there is no full/core contradiction.
  - No compression, format, encoding or media type is asserted in either representation,
    because the crate reports formats only at release level.
  - Scope: `total_file_count` (53877) and `total_size_bytes` (21051331945400) are release-wide
    and are not the sum of the nine package sizes, which the crate never totals. The two scopes
    are different and are not in conflict.
- Top-level identity/version/access facts were re-checked against `resources` and
  `version_access`: the release DOI, version 1.0 and 2026-06-30 publication date are consistent
  everywhere they appear; the component versions (1.0, 0.1.0, 1.5, 0.6) and the March 2025 /
  October 2025 / January 2026 release references are recorded as historical, distinct from the
  current release.
- **Result: no unresolved contradiction within or between the two records.**

## Commands run

```bash
poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_all.yaml -C Dataset \
  data/d4d_concatenated/claudecode_agent_crate_only/2026-07-28_claude-opus-5-crateonly-denoised_rep3/CM4AI_d4d.yaml
poetry run linkml-term-validator validate-data \
  data/d4d_concatenated/claudecode_agent_crate_only/2026-07-28_claude-opus-5-crateonly-denoised_rep3/CM4AI_d4d.yaml \
  --schema src/data_sheets_schema/schema/data_sheets_schema_all.yaml --target-class Dataset
poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml -C CoreDataset \
  data/d4d_concatenated/claudecode_agent_crate_only_core/2026-07-28_claude-opus-5-crateonly-denoised_rep3/CM4AI_d4d_core.yaml
poetry run linkml-term-validator validate-data \
  data/d4d_concatenated/claudecode_agent_crate_only_core/2026-07-28_claude-opus-5-crateonly-denoised_rep3/CM4AI_d4d_core.yaml \
  --schema src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml --target-class CoreDataset
poetry run python -m data_sheets_schema.d4d_pair_consistency --full <full> --core <core> --sync-core
poetry run python -m data_sheets_schema.d4d_pair_consistency --full <full> --core <core>
poetry run d4d provenance record --project CM4AI --method claudecode_agent_crate_only \
  --label 2026-07-28_claude-opus-5-crateonly-denoised_rep3 \
  --input-bundle data/preprocessed/concatenated/CM4AI_crate_only.txt
```

## Final results

| Check | Result |
|---|---|
| Full — LinkML schema validation (`Dataset`) | No issues found |
| Full — ontology term validation | Validation passed |
| Core — LinkML schema validation (`CoreDataset`) | No issues found |
| Core — ontology term validation | Validation passed |
| Pair consistency (after sync) | PASS — 76 identity slots, 1 projected slot |
| Pair consistency (independent re-run) | PASS — 1 warning, semantically reviewed above |
| Provenance record | `CM4AI_provenance.yaml`, `record_mode: live` |

Files changed in this run: the full YAML, the core YAML, this report, and
`CM4AI_provenance.yaml`. Line counts (informational only, not a quality gate): full 1206,
core 1027.

## Primary result — D4D areas the crate could NOT support

This is what the arm exists to measure. Each item below is empty in **both** records because
`CM4AI_crate_only.txt` contains no evidence for it.

### Empty D4D areas

| D4D area | Slot(s) left empty | What the crate gives instead |
|---|---|---|
| Addressing gaps / motivation | `addressing_gaps` | Use cases and a "major goal", but no statement of an unmet need or a gap in existing datasets. |
| Sampling design | `sampling_strategies` | No statement of whether the data are a sample of a larger set, how instances were selected, or whether the selection is representative. |
| Data splits and instance relationships | `splits`, `relationships`, `subsets`, `variables` | Nothing. No train/val/test guidance, no inter-instance relationships, no variable/column dictionary — despite 20 `evi:schemaCount` schemas being *counted* but not described. |
| Anomalies / errors | `anomalies`, `errata` | Only the generic "not yet in completed final form" statement, which is recorded as a limitation, not as a specific anomaly. |
| Cleaning, labelling, imputation, annotation | `cleaning_strategies`, `labeling_strategies`, `imputation_protocols`, `annotation_analyses`, `machine_annotation_tools` | Nothing. Preprocessing is supported only for one component (Spectronaut + R/MSstats for SEC-MS KOLF2); the other eight components describe none. |
| Existing uses and use tracking | `existing_uses`, `use_repository`, `other_tasks`, `future_use_impacts` | Four `associatedPublication` entries, which state association, not use. Recorded as `external_resources`; no claim of use was manufactured from them. |
| Discouraged uses | `discouraged_uses` | Only an absolute prohibition (clinical decision-making), which is recorded in `prohibited_uses`. Nothing in the discouraged-but-permitted band. |
| Content warnings, subpopulations, sensitive elements | `content_warnings`, `subpopulations`, `sensitive_elements` | Nothing. Consistent with the "no human subjects" position, but not stated. |
| Consent workflow | `collection_consents`, `collection_notifications`, `consent_revocations`, `participant_privacy`, `participant_compensation`, `direct_collection` | Nothing. Declared not applicable at the top level via `d4d:informedConsent`, which is recorded in `informed_consent`. |
| Data protection impact assessment | `data_protection_impacts` | Nothing. |
| Extension / contribution mechanism | `extension_mechanism` | Nothing — no route for third parties to contribute or propose corrections. |
| Related datasets and parentage | `related_datasets`, `parent_datasets` | Root `isPartOf` points at an *organization* and a *project* ARK, not datasets, so neither slot is populated. Component-to-release membership is expressed through `resources` instead. |
| Dataset dialect | core `dialect` | Nothing. |
| Status, language, provenance dates | `status`, `language`, `created_on`, `created_by`, `last_updated_on`, `modified_by`, `was_derived_from`, `download_url` (release level) | The crate gives `datePublished` only. There is no release-level download URL, landing page, creation date, or modification date. |

### Areas the crate supports only thinly

- **Ethics.** Two named ethics contacts and an exemption statement — but no IRB or ethics
  committee, no protocol number, no review date, no determination letter. `ethical_reviews`
  is populated with contacts only.
- **Collection methodology.** `rai:dataCollection` delegates entirely to an external preprint
  ("Data collection processes are generally described in Clark T et al. (2024) …"), which this
  arm may not read. `acquisition_methods` therefore records the delegation, not a method.
- **Governance.** `dataGovernanceCommittee` is one name, "Jilian Parker", with no charter,
  membership or contact address.
- **Verifiability.** The crate's own AI-readiness score records checksums on 8 of 55859
  entities (0%) and summary statistics on 0 entities.
- **Instance counts.** No instance count exists at any level. `evi:datasetCount` counts file
  entities, not observations, samples or images.

### What the crate supports well

Identity and citation (DOI, version, publisher, 47 authors with 40 ORCIDs and affiliations,
full citation string), licensing and access conditions, copyright, funding (5 funders, 9
grant numbers), prohibited uses, biases, limitations, completeness, maintenance and retention
plan, confidentiality level, human-subjects exemption, de-identification status, collection
timeframe, collection modality list, and a nine-member component-dataset inventory with
per-component descriptions, licences, versions, sizes, checksums and repository locations.
The `rai:*` Croissant properties carry most of the ethics-and-limitations content; the
FAIRSCAPE `evi:*` counters carry the scale figures.
