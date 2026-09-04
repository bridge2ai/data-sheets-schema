# CM4AI Reconciliation Report

**Project:** CM4AI (Bridge2AI Functional Genomics Grand Challenge)
**Referent:** Cell Maps for Artificial Intelligence — June 2026 Data Release (Beta), `doi:10.18130/V3/HIGT4C`
**Label:** 2026-09-04_claude-opus-5-api-generic-v8_rep1
**Arm:** BASELINE (input documents only)

---

## 1. Audit summary

The Phase 3 audit returned sixteen findings against the full record: three major (invented identifiers for real-world people and organizations; inverted version-lineage relationship terms; an undeclared `instance_description` key), and thirteen minor (identifier form inconsistency on `id`; pipeline steps attributed to a release that excludes their product; a prose string in a multivalued `tools` slot; a plan lodged in `ethical_reviews`; a prohibition in `prohibition_reason`; a licence restriction in `discouraged_uses`; a pipeline step in `data_collectors`; a depositor recorded as maintainer; derived byte figures on an unstated unit base; and four unsupported or over-precise scalars).

All sixteen were acted on. Fourteen produced edits to the full record; two (the `preprocessing_strategies` / `labeling_strategies` / `machine_annotation_tools` scoping finding and the `machine_annotation_tools[0].tools` finding) were addressed by a single consolidated repair. Every edit was mirrored into the core record by re-projection.

---

## 2. Changes made — full record

### 2.1 Invented identifiers for real-world entities (major — changed)

All `id` values of the form `https://dataverse.lib.virginia.edu/#organization-*` and `https://dataverse.lib.virginia.edu/#person-*` were removed. Comparing the two records:

- Every `Organization` object under `creators[*].affiliations` that previously carried a Dataverse-fragment `id` now carries `name` only — for example `University of California, San Diego`, `Stanford University`, `KTH Royal Institute of Technology`, `University of California San Francisco`, `Yale University`, `University of Montreal`. The four `University of Virginia` affiliations retain `id: ROR:0153tk833`, which the bundle does supply.
- The nine `Creator` objects for whom the bundle states no ORCID (U Axelsson, B Chinn, J Fall, A Johannesson, H Khaliq, M Muralidharan, E Pan, B Polacco, Y Zhang) now carry `name` only; their invented person fragments are gone.
- `creators[Trey Ideker].principal_investigator.affiliation[0]` lost its organization fragment and retains `name`. The `Person` object gained `orcid: 0000-0002-1708-8454` alongside its ORCID CURIE `id`, both attested in the bundle.
- `data_governance.committee_contact.id` changed from `https://dataverse.lib.virginia.edu/#person-jillian-parker` to `ORCID:0000-0003-4535-3486`, the ORCID the bundle states for Jillian Parker in the same release's author list.

Rationale: these identifiers name entities outside this dataset, so the evidence must supply them or they must be omitted. A fragment on a repository base URL identifies neither a person nor an organization.

### 2.2 Inverted version-lineage relationships (major — changed)

The four entries in `related_datasets` naming the October 2025, June 2025, March 2025 and May 2024 releases changed `relationship_type` from `is_previous_version_of` to `is_new_version_of`. The first entry's `notes` was rewritten from "Relationship read from the June 2026 release's position as the successor release; …" to "The June 2026 release is the successor release; the October 2025 release is superseded by it," removing the wording that contradicted the term. The three `is_documented_by` and two `references` entries are unchanged.

### 2.3 Undeclared `instance_description` key (major — changed)

All four `Instance` objects had `instance_description` renamed to `notes`; the prose is otherwise verbatim. `instance_type`, `data_substrate` and `data_topic` are unchanged. The digest lists `notes` among Instance's permitted keys and does not list `instance_description`.

### 2.4 `id` identifier form (minor — changed)

`id` changed from `https://doi.org/10.18130/V3/HIGT4C` to `doi:10.18130/V3/HIGT4C`, matching the `doi:` CURIE already used in `version_access.latest_version_doi`. The `doi` slot itself remains the bare string `10.18130/V3/HIGT4C`, correct for its declared `string` range and pattern.

The ten `file_collections[*].id` fragments were re-based on the same CURIE (`doi:10.18130/V3/HIGT4C#apms-paclitaxel` and so on) so that the record names one thing one way throughout. This was not an audit finding but follows from the same identifier rule; each fragment is still pointed at by a `distributions` entry in the core record.

### 2.5 Pipeline scoping and the `tools` prose string (minor — changed, consolidated)

`preprocessing_strategies` (four entries) and `labeling_strategies` (one entry) were removed entirely from the full record. Their content was consolidated into a single rewritten `machine_annotation_tools` entry that:

- lists five discrete tools as separate list items rather than one semicolon-joined string;
- narrates the node2vec / HPA-model / co-embedding / community-detection / GO-and-Reactome-alignment / LLM-naming sequence in `tool_descriptions`;
- adds a `notes` field stating explicitly that these tools produce the computed cell maps which the June 2026 release states are *not* included, and that they are recorded as the CM4AI toolkit operating on the release's input data streams rather than as annotation applied to the distributed files.

`raw_sources` was retained unchanged, as it describes where the release's own modality data come from rather than a step producing an absent product.

### 2.6 Plan in `ethical_reviews` (minor — changed)

The third `ethical_reviews` entry (Value-Sensitive Design methodology, CM4AI Life Cycle "is formulating") was removed. Its substance was relocated to the record-level `notes`, stated in the source's own forward-looking tense: "…employs a methodology inspired by Value-Sensitive Design (VSD) … and is formulating the CM4AI Life Cycle, a framework intended to elucidate governance milestones …". The two entries naming Vardit Ravitsky and Jean-Christophe Bélisle-Pipon as ethical review contacts are unchanged.

### 2.7 `prohibition_reason` holding the prohibition (minor — changed)

`prohibited_uses[0]` changed from `prohibition_reason: <statement>` to `notes: <same statement>`. The bundle gives no separate rationale, so the reason field is now unpopulated rather than filled with the prohibition itself.

### 2.8 Licence restriction in `discouraged_uses` (minor — changed)

`discouraged_uses` was removed in full. Its single entry restated the CC BY-NC-SA non-commercial restriction, which is already carried in `license_and_use_terms.license_terms` and `data_use_permission: no_commercial_use`.

### 2.9 Pipeline ingestion step in `data_collectors` (minor — changed)

`data_collectors[2]` (PPI networks downloaded from Krogan's archive, IF images from Lundberg's) was removed. The two remaining entries name the Lundberg Lab and the Krogan laboratory as the parties that generated the data. The removed content duplicated `raw_sources`, which is retained.

### 2.10 Depositor as maintainer, and maintainer roles (minor — changed)

`maintainers[2]` (Justin Niestroy as depositor of record) was removed; the depositor fact moved to the record-level `notes`: "Justin Niestroy (University of Virginia) is recorded by the repository as the Depositor of the Dataverse dataset." The `role: academic_institution` value was dropped from both remaining maintainer entries, since no permitted MaintainerRole term fits a named individual.

### 2.11 Derived byte figures (minor — changed)

All seven `total_bytes` values were removed from `file_collections`. Each affected entry's `notes` was rewritten from the "converted at 1 KB = 1024 bytes … the record's own computation" form to the plain form "Repository reports the size as 113.3 KB" (and equivalents), preserving the repository's own string. `source_caveats` was rewritten accordingly: it now explains that both `total_size_bytes` and per-collection `total_bytes` are omitted because the repository reports sizes to one decimal place and does not state whether the units are binary or decimal.

`total_file_count: 10` is retained, with its derivation ("count of the ten file entries the June 2026 Dataverse release lists ('1 to 10 of 10 Files')") still disclosed in `source_caveats`.

### 2.12 Unsupported scalars (minor — changed)

Three slots were removed from the full record:

- `language: en` — no source states a language for the resource.
- `is_tabular: false` — an inference; the release mixes images with tabular mass-spectrometry and perturb-seq output.
- `was_derived_from` — the value named two cell lines in a single-valued string slot; cell-line provenance remains in `description`, `subpopulations` and `direct_collection`.

`source_caveats` gained a closing sentence recording all three omissions and the reason for each.

### 2.13 `publisher` (minor — changed)

`publisher` changed from the bare host `https://dataverse.lib.virginia.edu/` to the dataset landing URL `https://dataverse.lib.virginia.edu/dataset.xhtml?persistentId=doi:10.18130/V3/HIGT4C`, which the bundle does contain and which `distribution_formats[0].access_urls` already carried.

### 2.14 Incidental range corrections

Two list-ranged fields that had been given scalar strings were corrected while making the above edits:

- `distribution_dates[0].release_dates` is now a one-item list rather than a bare string.
- Each `external_resources[*].external_resources` value is now a one-item list rather than a bare string.

---

## 3. Changes made — core record

The core record was re-derived by projection from the reconciled full record. Every change in §2 that touches a slot present in `CoreDataset` is mirrored there:

- Creator and Organization identifiers, and `data_governance.committee_contact.id`, match the full record.
- `related_datasets` relationship terms and the first entry's notes match.
- The four `instances` entries carry `notes` rather than `instance_description`.
- `id` is `doi:10.18130/V3/HIGT4C`; the ten `distributions[*].id` fragments are re-based on that CURIE.
- `bytes` was removed from all seven `distributions` entries that carried it, and the notes rewritten to the repository's own size strings.
- `preprocessing_strategies`, `labeling_strategies`, `discouraged_uses`, `language`, `is_tabular` and `was_derived_from` are absent.
- `machine_annotation_tools[0].tools` is a five-item list with the new `tool_descriptions` and scoping `notes`.
- `ethical_reviews` has two entries; the VSD/Life-Cycle material is in `notes`.
- `prohibited_uses[0]` uses `notes`.
- `data_collectors` has two entries; `maintainers` has two entries with no `role`.
- `publisher` is the landing URL; `source_caveats` and `notes` carry the full record's revised text.

The core header block carries `# Sources:` pointing at the full record and `# Phase 4 reconciliation: completed`.

---

## 4. Findings left as-is

None. All sixteen audit findings produced an edit, though two were resolved by one consolidated repair (§2.5) and several were resolved by relocating content rather than deleting it (§2.6, §2.7, §2.10).

---

## 5. Referent choice

`Dataset` admits one referent. The referent is the **June 2026 Data Release (Beta)** at `doi:10.18130/V3/HIGT4C`, the tier-1 source that supersedes the October 2025 release. Held consistently across both records:

- Composition, file listing, checksums and external links are the June 2026 values.
- The October 2025, June 2025, March 2025 and May 2024 releases appear only in `related_datasets` as versions this one supersedes.
- The Nature 2025 U2OS multimodal cell map and the 2021 MuSIC HEK293 map are distinct datasets and appear only under `related_datasets` with `references`.
- Project-wide aggregate figures from the CM4AI website (1,374 protein interactions; 53,788 images; 7,023 proteins; 11,739 genes; 21.4 TB) describe the project across releases and are excluded from the record's own slots, with the exclusion disclosed in `source_caveats`.

---

## 6. Source disagreements recorded

Preserved in `source_caveats` and `distribution_dates[0].source_caveats`:

| Disagreement | Sources | Resolution |
|---|---|---|
| AP-MS data present in release | June 2026 (tier 1) vs October 2025 (tier 1, superseded) | June 2026 preferred |
| IF archive MD5 checksums | June 2026 vs October 2025 | June 2026 values recorded |
| Release date (June 17 2025 vs 2026-06-17) | cm4ai.org (tier 2) vs Dataverse (tier 1) | Dataverse preferred; both stated |
| IF protein count (563 vs 464) | March 2025 (tier 5) vs June 2025 / October 2025 | No count carried — June 2026 states none |

---

## 7. Validation

| Record | Schema | Class | Result |
|---|---|---|---|
| `CM4AI_d4d.yaml` | `data_sheets_schema_all.yaml` | `Dataset` | Valid |
| `CM4AI_d4d_core.yaml` | `data_sheets_schema_core_all.yaml` | `CoreDataset` | Valid |

**Outcome:** reconciled; both records validate; no finding left unaddressed.