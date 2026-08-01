# D4D Reconciliation Report — CM4AI

- **Version label:** `2026-07-31_claude-opus-5-api-generic_rep1`
- **Arm:** DE NOVO WITH CRATE (documents + RO-Crate evidence)
- **Declared input bundle:** `data/preprocessed/concatenated/CM4AI_preprocessed_with_crate.txt`
- **Full record:** `data/d4d_concatenated/claudecode_agent_crate/2026-07-31_claude-opus-5-api-generic_rep1/CM4AI_d4d.yaml`
- **Core record:** `data/d4d_concatenated/claudecode_agent_crate_core/2026-07-31_claude-opus-5-api-generic_rep1/CM4AI_d4d_core.yaml`

---

## 1. Referent declaration

`Dataset` admits one referent. Both records take as their referent the **June 2026 CM4AI Data Release (Beta)**, DOI `10.18130/V3/HIGT4C`, Dataverse version 2.0, publication date 2026-06-17, version 2 released 2026-07-15T20:28:19Z, ten archive files. This is the release the RO-Crate root entity describes (`rocrate-cell-maps-for-artificial-intelligence-June-2026-data-release`), and it is the release the AI-readiness self-assessment scores.

The bundle also contains three superseded Dataverse deposits (`B35XWX`, `F3TD5R`, `K7TGEM`) and one referenced but not captured (`DXWOS5`). These are treated throughout as **prior versions of the referent**, recorded under `version_access`, `distribution_dates`, and `anomalies` — never as the referent itself. The Nature U2OS paper (`10.1038/s41586-025-08878-3`) describes a **different study on a different cell line** and is treated as a related publication and methodological antecedent, not as part of the referent. This choice is held consistently across both records.

---

## 2. Audit outcome

The Phase 3 audit returned **seventeen findings**: three high, four medium, ten low. No fabricated identifiers, checksums, sizes, dates, or accession numbers were detected. No evidence of prior-D4D reuse was observed. All quantitative values in `file_collections`, `resources`, `raw_data_sources`, and `version_access` traced correctly to the declared bundle.

Findings were dispositioned as follows.

| Severity | Total | Corrected | Left as-is |
|---|---|---|---|
| High | 3 | 3 | 0 |
| Medium | 4 | 4 | 0 |
| Low | 10 | 6 | 4 |

---

## 3. Changes made

### 3.1 High severity — cardinality violations (full record)

Three slots in the full record supplied YAML sequences where the schema digest declares a single-valued object range. This is a structural violation and would have failed `linkml-validate`.

| Slot | Declared range | Was | Now |
|---|---|---|---|
| `license_and_use_terms` | `LicenseAndUseTerms` (no `[many]`) | list of 5 objects | single merged object |
| `ip_restrictions` | `IPRestrictions` (no `[many]`) | list of 4 objects | single merged object |
| `regulatory_restrictions` | `ExportControlRegulatoryRestrictions` (no `[many]`) | list of 4 objects | single merged object |

**Why changed.** The schema digest is unambiguous: none of these three slots carries a `[many]` marker. The core record already supplied each as a single object, so the two records disagreed on cardinality for identical evidence — an internal inconsistency independent of validation.

**How merged.** No evidence was discarded. The five license facets (CC BY-NC-SA 4.0 terms; the crate's `conditionsOfAccess` attribution requirement; the `copyrightNotice` split between UC Regents and Stanford's Board of Trustees for spatial proteomics imagery; the CC0 licensing on the two MassIVE AP-MS sub-crates; and the Dataverse community-norms citation expectation) were consolidated into a single object whose narrative fields carry all five distinctions explicitly. The same approach was applied to `ip_restrictions` (dual copyright holders, non-commercial restriction, separate commercial-license negotiation path, ShareAlike propagation) and `regulatory_restrictions` (no FDA regulation, no human-subjects determination, embargo status on two perturb-seq deposits, and the repository-under-administrative-review notice appearing on all Dataverse and cm4ai.org captures).

The full record now matches the core record on all three slots.

### 3.2 Medium severity — `errata` scope (both records)

Both `errata` entries were removed.

- Entry one described a revision to the **June 2025** release (`10.18130/V3/F3TD5R` — RGB image addition, ro-crate metadata corrections, naming-convention changes). That is a different deposit.
- Entry two described the Publisher Corrections of 2025-04-29 and 2025-10-02 to the **Nature U2OS paper**. That is a different publication about a different cell line.

**Why changed.** The slot is defined as "known errors or corrections to the dataset since publication." Neither item is an erratum of `10.18130/V3/HIGT4C`. Retaining them would have asserted a correction history the referent does not have.

**Where the evidence went.** The F3TD5R revision note is retained under `version_access`, where release-to-release change description belongs. The Nature corrections are retained in the `external_resources` entry for that publication. Nothing was lost; both facts now sit in slots whose definitions they satisfy.

### 3.3 Medium severity — `total_file_count` (full record)

Value `53877` was removed.

**Why changed.** The figure is the crate's `evi:datasetCount` — the number of dataset entities in the provenance graph. The slot is defined as "Total number of files across all file collections in this dataset. Can be aggregated from `file_collections[].file_count`." The record's own `file_collections` slot enumerates exactly ten entries. Asserting 53,877 as the file count over ten collections is inconsistent with both the record's own enumeration and the slot's stated aggregation semantics.

The bundle genuinely supports 53,877 dataset entities. That count is retained verbatim in the `resources` description of the release RO-Crate, attributed to `evi:datasetCount`, where it is correctly scoped. `total_size_bytes` was retained: the crate's `evi:totalContentSizeBytes` (21,051,331,945,400) is a byte total and matches the slot definition.

### 3.4 Medium severity — two unrecorded internal contradictions (both records)

Two conflicts directly detectable within the declared bundle were absent from `anomalies`. Both were added.

**Swapped perturb-seq checksums.** The crate assigns MD5 `cbdb263b1c099396d75e16f00a79a818` to the SRA raw-sequence sub-crate and `1cafefa32a897998e3e2ba0a29a3ef5c` to the perturbation cell atlas sub-crate. The March 2025 Dataverse listing (`B35XWX`) assigns these same two checksums to the opposite objects — `cbdb263b` to `CRISPR Perturbation Cell Atlas/`, `1cafefa3` to `CRISPR Perturbation RNA Sequences - Raw Sequences/`. A new `DataAnomaly` records the swap, names both accession contexts, and notes that the direction of the error cannot be determined from the bundle.

**Stale IF sub-crate metadata.** The June-2026 crate's three IF sub-crates assert `isPartOf` the June 2026 release while carrying March 2025 checksums (`9422486c…`, `0b4d129f…`, `ac577109…`) and March-era content sizes (2.6 / 3.2 / 2.8 GB). The HIGT4C Dataverse archives carry different MD5s (`6c1a8652…`, `6d066e6b…`, `df796327…`) and different sizes (3.8 / 4.6 / 4.2 GB). The pre-existing anomaly noted only that checksums changed between October 2025 and June 2026; it did not record that the crate's own embedded metadata is stale relative to the release it claims membership in. That anomaly was rewritten to state the conflict directly, and the affected `resources` entries were annotated to mark the reproduced figures as crate-asserted and inconsistent with the Dataverse listing.

### 3.5 Low severity — corrections applied

**`language`** — removed from both records. The value `en` appears nowhere in the bundle; it was inferred from the language of the source documents rather than documented as a dataset property. Omission is the correct answer where evidence is absent.

**`machine_annotation_tools`** — the GPT-family attribution was removed from the CM4AI annotation-tool entry. The CM4AI preprint says only "a large language model (LLM) approach that we developed." GPT-4 (v. `gpt-4-1106-preview`) is specified in the Nature U2OS paper — a different study, different cell line. The entry now describes an unspecified LLM-based gene-set naming and confidence-scoring pipeline; the GPT-4 specificity remains where it is sourced, in the `external_resources` entry for the Nature publication.

**`existing_uses`** — the clause reading the Dataverse "Sorry, no citations were found." string as an observed metric was removed. That string appears verbatim inside the static Dataset Citations modal on all four captured Dataverse pages; it is template boilerplate, not a rendered result. The retained portion of the entry (download counts per release, which *are* rendered values) is unaffected.

**`distribution_formats`** — the enumeration of `release-ro-crate-datasheet.html` and per-modality `ro-crate-prov-graph.html` files inside `cm4ai_release_metadata.zip` was removed. That inventory is from the June 2025 (`F3TD5R`) file listing. The HIGT4C table lists `cm4ai_release_metadata.zip` (1.1 MB, MD5 `318deb7c…`) without contents. The entry now states the archive is present and gives its size and checksum without asserting an unverified inventory.

**`data_collectors`** — the Ideker and Sali laboratory entries were removed from this slot. The slot is defined as "individuals or organizations responsible for collecting the data"; the bundle describes both as computational integration contributors (MuSIC pipeline, hierarchy annotation; integrative structure modeling). Both are retained under `creators` with their documented roles. The four wet-lab generators (Krogan/UCSF for SEC-MS and AP-MS, Lundberg/Stanford for IF imaging, Mali/UCSD for perturb-seq, and the UVA/FAIRSCAPE packaging group) remain.

**`related_datasets`** — added to the full record. The slot was unused despite the bundle documenting four prior release DOIs standing in explicit supersession relationships to the referent, plus four MassIVE accessions and one Figshare deposit. Nine `DatasetRelationship` objects were added, each with the required `relationship_type` and `target_dataset` keys. The underlying facts were already present in `version_access` and `raw_data_sources`; this change makes the relationships machine-typed rather than narrative-only.

### 3.6 Low severity — core/full slot divergence

The audit flagged seven slots present in the full record and absent from the core record (`third_party_sharing`, `citation`, `subsets`, `direct_collection`, `relationships`, `total_file_count`, `total_size_bytes`), plus a slot named `distributions` in the core record that does not appear in the supplied `Dataset` inventory.

Each was checked against `src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml`, class `CoreDataset`.

- `third_party_sharing`, `subsets`, `direct_collection`, `relationships`, `total_file_count`, `total_size_bytes` — **not present in `CoreDataset`**. Their absence from the core record is correct schema behaviour, not evidence loss. No change.
- `citation` — **present in `CoreDataset`** and was genuinely missing. Added to the core record, matching the full record verbatim.
- `distributions` — **is** a `CoreDataset` slot (the core schema's counterpart to the full schema's `distribution_formats`). Not an error. No change.

`total_file_count` was independently removed from the full record under §3.3, so the two records now agree on that slot by both being silent.

---

## 4. Findings left as-is

Four low-severity findings were reviewed and not acted on.

**`known_biases` framing (four of six entries).** The audit observed that the target-selection, reagent-availability, cross-modality-coverage, and disease-context entries are analytic framings rather than verbatim source claims — the bundle characterizes only cell-line non-representativeness as a bias in `rai:dataBiases` and the Dataverse "Potential Sources of Bias" block.

Retained. Each of the four rests on facts the bundle states plainly: curated target lists confined to chromatin modifiers and metabolic enzymes; HPA antibody availability governing which proteins are imaged; `rai:dataCollectionMissingData` stating explicitly that the three modalities "interrogate sets of proteins which incompletely overlap"; and exactly two drug conditions plus vehicle control. `DatasetBias` is a characterization slot — it exists to name systematic effects a user should account for. Declining to name a documented coverage restriction because the source did not use the word "bias" would understate a limitation the bundle makes explicit. Each entry was audited to confirm it asserts no fact beyond what the bundle states; the framing is the record's contribution, the facts are the source's.

**`creators` — Sali A composite affiliation.** The audit noted that the HIGT4C author block and the crate `Person` entity record UCSD only, while UCSF appears in the CM4AI preprint and the Nature paper.

Retained as `University of California San Diego / University of California San Francisco`. The uniform decision rules direct that where sources within the declared bundle disagree, the record should represent what the evidence states rather than silently selecting one. All three source affiliations are in the bundle; the composite is the non-selecting representation. Collapsing to UCSD alone would silently discard the preprint and Nature attributions. A note recording the divergence was added to the entry so the composite is not mistaken for a single-source claim.

**`version` — prose value.** The audit observed that `Dataverse dataset version 2.0 (V2); the accompanying RO-Crate release package declares version 1.0` is an explanatory sentence rather than a bare identifier, and that the discrepancy is already documented under `anomalies`.

Retained. The referent has two conflicting declared versions in the bundle, and `version` is single-valued. Reducing to `2.0` would assert the Dataverse value as authoritative when the crate — the primary evidence artifact for this arm — says `1.0`. Reducing to `1.0` inverts the same problem. The prose is the only form of this slot that does not silently pick a side. The machine-readable route remains available through `anomalies`, where the conflict is recorded with both values and both sources named.

**`errata` now empty.** After removing both out-of-scope entries (§3.2), the slot has no members and was omitted rather than emitted as an empty list.

Left omitted deliberately. Under the uniform decision rules, an absent slot is a correct answer when the evidence is absent. The bundle documents no errata for `10.18130/V3/HIGT4C`; the slot correctly reflects that.

---

## 5. Post-reconciliation state

| | Full | Core |
|---|---|---|
| Slots populated | 78 | 51 |
| `linkml-validate` | pass | pass |

Validation commands run:

```
poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_all.yaml \
  -C Dataset data/d4d_concatenated/claudecode_agent_crate/2026-07-31_claude-opus-5-api-generic_rep1/CM4AI_d4d.yaml

poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml \
  -C CoreDataset data/d4d_concatenated/claudecode_agent_crate_core/2026-07-31_claude-opus-5-api-generic_rep1/CM4AI_d4d_core.yaml
```

Both records now agree on referent, on cardinality for the three previously divergent single-valued slots, on the removal of `language`, on the corrected `machine_annotation_tools` and `existing_uses` and `distribution_formats` and `data_collectors` entries, and on the two added anomalies. Remaining slot-inventory differences between the two records are attributable to `CoreDataset` being a strict subset of `Dataset`, verified slot by slot against the core schema.

## 6. Provenance

Live provenance record written after Phase 4:

```
poetry run d4d provenance record \
  --project CM4AI \
  --method claudecode_agent_crate \
  --label 2026-07-31_claude-opus-5-api-generic_rep1 \
  --input-bundle data/preprocessed/concatenated/CM4AI_preprocessed_with_crate.txt
```

No prior D4D record from any arm, label, or date was read, opened, grepped, or consulted at any phase. Factual inputs were the declared bundle and the two schema files only.