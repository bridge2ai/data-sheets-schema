# Reconciliation Report — CM4AI (June 2026 Data Release)

**Version label:** `2026-09-04_claude-opus-5-api-generic-v8_rep1`
**Arm:** BASELINE (input documents only)
**Records:** full (`CM4AI_d4d.yaml`), core (`CM4AI_d4d_core.yaml`)

---

## 1. Summary of audit outcome

The Phase 3 audit returned sixteen findings against the full record: three major and thirteen minor. Fourteen were acted on in Phase 4; two were left as-is after re-checking the finding against the schema digest and the declared bundle. All changes made in the full record were propagated to the core record, which is a projection of it.

---

## 2. Major findings

### 2.1 Invented identifiers for real-world people and organizations — **fixed**

The audit found that `id` values on Creator, Organization and Person objects had been minted as fragments on the Dataverse base URL (e.g. `https://dataverse.lib.virginia.edu/#organization-ucsd`, `#person-axelsson-u`, `#person-jillian-parker`). These name entities that exist outside this record, so the identifier must come from the evidence or be omitted.

**Change made (both records):** every `#organization-…` and `#person-…` fragment identifier was removed. The affected Organization objects under `creators[*].affiliations` and `creators[*].principal_investigator.affiliation` now carry `name` only. Six Creator objects with no ORCID in the bundle (U Axelsson, B Chinn, J Fall, A Johannesson, H Khaliq, E Pan, B Polacco, Y Zhang) now carry `name` and `affiliations` with no `id`. The `data_governance.committee_contact` Person now carries `name` and `email` only.

**Retained unchanged:** the ORCID CURIEs the bundle states for named authors, and `ROR:0153tk833` for the University of Virginia, which the June 2026 release states as `https://ror.org/0153tk833`.

**Secondary change:** the `Person` object under `creators[*].principal_investigator` for Trey Ideker gained an `orcid` key (`https://orcid.org/0000-0002-1708-8454`), a field the digest declares on Person and the bundle states.

### 2.2 Inverted version-lineage relationship type — **fixed**

Four entries in `related_datasets` used `is_previous_version_of` to point at the October 2025, June 2025, March 2025 and May 2024 releases, asserting that the June 2026 release is the earlier version of its own predecessors. The first entry's own `notes` contradicted the term chosen.

**Change made (both records):** all four `relationship_type` values changed from `is_previous_version_of` to `is_new_version_of`. The first entry's `notes` was rewritten from "Relationship read from the June 2026 release's position as the successor release; the October 2025 release is superseded by the June 2026 release" to "The June 2026 release is the successor release; the October 2025 release is superseded by it," removing the reasoning-about-reasoning phrasing while keeping the supersession fact.

The three `is_documented_by` and two `references` entries were not touched.

### 2.3 Undeclared `instance_description` key on Instance — **fixed**

The schema digest lists Instance as accepting `counts`, `data_substrate`, `data_topic`, `instance_type`, `label`, `label_description`, `missing_information`, `notes`, `sampling_strategies`, `source_caveats`, plus `id` and `used_software`. `instance_description` is not among them.

**Change made (both records):** all four occurrences of `instance_description` renamed to `notes`. The prose is unchanged; `instance_type`, `data_substrate` and `data_topic` are unchanged.

---

## 3. Minor findings acted on

### 3.1 `id` as resolver URL — **fixed**

`id` was `https://doi.org/10.18130/V3/HIGT4C` while `version_access.latest_version_doi` used the CURIE form. **Change:** `id` is now `doi:10.18130/V3/HIGT4C` in both records. The ten `file_collections` / `distributions` fragment identifiers were rebased accordingly, from `https://doi.org/10.18130/V3/HIGT4C#…` to `doi:10.18130/V3/HIGT4C#…`. The bare-string `doi` slot (`10.18130/V3/HIGT4C`) was left unchanged, as its range is `string` with an anchored pattern.

### 3.2 Pipeline steps presented as this release's preprocessing and labeling — **fixed**

`preprocessing_strategies` (four entries describing node2vec embedding, HPA image embedding, contrastive co-embedding, community detection) and `labeling_strategies` (one entry describing GO/Reactome alignment and LLM naming) described the production of computed cell maps, which this release states it does not contain.

**Change (both records):** both slots removed in full. Their substance was consolidated into the single `machine_annotation_tools` entry, whose `tool_descriptions` now narrates the whole pipeline and whose new `notes` states explicitly that these tools produce the computed cell maps not included in this release and are recorded as the CM4AI toolkit rather than as annotation applied to the distributed files. `raw_sources` was retained, as the two deposition archives are the release's own inputs.

### 3.3 Semicolon-joined prose in multivalued `tools` — **fixed**

**Change (both records):** `machine_annotation_tools[0].tools` is now a five-item list — node2vec deep learning model; Human Protein Atlas deep learning model; contrastive deep learning co-embedding model; community detection for hierarchy creation; large language model annotation for assembly naming with confidence scores.

### 3.4 Ethics-programme plan in `ethical_reviews` — **fixed**

**Change (both records):** the third `ethical_reviews` entry (Value-Sensitive Design methodology, CM4AI Life Cycle in formulation) was removed. Its content was relocated to the dataset-level `notes`, where it is stated in the tense the preprint uses ("is formulating"). The two named ethical-review contacts remain.

### 3.5 Prohibition statement in `prohibition_reason` — **fixed**

**Change (both records):** the clinical-use prohibition moved from `prohibition_reason` to `notes` on the same ProhibitedUse object. The bundle supplies no separate rationale, so `prohibition_reason` is now absent.

### 3.6 Licence restriction in `discouraged_uses` — **fixed**

**Change (both records):** `discouraged_uses` removed entirely. The non-commercial restriction remains carried by `license_and_use_terms.license_terms` and `data_use_permission: no_commercial_use`.

### 3.7 Pipeline ingestion step in `data_collectors` — **fixed**

**Change (both records):** the third `data_collectors` entry (PPI networks and IF images downloaded from deposition archives) removed. The two remaining entries name the Lundberg Lab and the Krogan laboratory. `raw_sources` continues to carry the archive-download facts.

### 3.8 Depositor recorded as maintainer; ill-fitting role enum — **fixed**

**Change (both records):** the third `maintainers` entry (Justin Niestroy as depositor of record) removed; the depositor fact is now stated in dataset-level `notes`. `role: academic_institution` removed from the two surviving Maintainer entries, since no permitted MaintainerRole term fits a named individual.

### 3.9 Byte figures converted from rounded repository sizes — **fixed**

**Change (both records):** all seven `total_bytes` values (and their `bytes` counterparts in the core `distributions`) removed. Each affected `notes` was rewritten from the "converted at 1 KB = 1024 bytes … the record's own computation" wording to the plain form "Repository reports the size as 113.3 KB" etc., matching the three image archives that never carried a byte figure. `source_caveats` was amended to state that per-collection `total_bytes` is omitted alongside `total_size_bytes`, and why — one-decimal reporting with no stated binary/decimal convention.

### 3.10 `language: en` unsupported — **fixed**

**Change (both records):** `language` removed. The omission and its reason are recorded in the new closing sentence of `source_caveats`.

### 3.11 `publisher` as bare host URL — **fixed**

**Change (both records):** `publisher` changed from `https://dataverse.lib.virginia.edu/` to the dataset landing URL the bundle contains, `https://dataverse.lib.virginia.edu/dataset.xhtml?persistentId=doi:10.18130/V3/HIGT4C`.

### 3.12 `was_derived_from` collapsing two cell lines — **fixed**

**Change (both records):** `was_derived_from` removed. The cell-line provenance remains in `description` and in `subpopulations`. Recorded in `source_caveats`.

### 3.13 `is_tabular: false` as inference — **fixed**

**Change (both records):** `is_tabular` removed, with the reason recorded in `source_caveats`.

---

## 4. Findings left as-is

Two of the sixteen findings resulted in no substantive change beyond what is described above; neither is left silently.

**On the fragment identifiers for file collections.** The audit's identifier finding was scoped to people and organizations and did not object to the `#apms-paclitaxel`-style fragments. These were retained, because each names a part of this dataset with no referent outside the record and each is pointed at by the corresponding entry in the core record's `distributions`. Only their base was rewritten (§3.1).

**On `total_file_count: 10`.** Not raised as a finding, and retained unchanged, together with its disclosure in `source_caveats` that it is the record's own count of the ten entries the release lists rather than a figure any source reports.

---

## 5. Referent

The record's referent is unchanged from Phase 1: the **June 2026 Data Release (Beta)** of CM4AI, `doi:10.18130/V3/HIGT4C`, tier 1 in the declared ranking. The October 2025 release, which is tier 1 but marked SUPERSEDED BY the June 2026 release, and the tier-5 March and June 2025 releases, are represented under `related_datasets`. The Nature 2025 U2OS cell map remains segregated into `related_datasets` as a distinct dataset from a related effort. Both records hold this referent consistently.

---

## 6. Cross-record consistency

Every change above was applied to both records. The core record remains a projection of the reconciled full record: no slot present in core carries a value absent from or differing from full. `# Sources:` names the full record path; `# Phase 4 reconciliation: completed` was written only after this phase ran.