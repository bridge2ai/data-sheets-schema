# CM4AI Phase 4 Reconciliation Report

## Scope

The audit examined the Phase 1 full record for the CM4AI June 2026 Data Release (`doi:10.18130/V3/HIGT4C`) against the declared bundle, returning 23 findings: four high, five moderate, fourteen low. The core record was audited as a projection, with no findings of its own; every repair was made in the full record and re-projected.

## High-severity findings

**`instances[0].instance_type_notes` — invented key.** Confirmed against the schema digest, which lists the `Instance` slots as `counts`, `data_substrate`, `data_topic`, `instance_type`, `label`, `label_description`, `missing_information`, `notes`, `sampling_strategies`, `source_caveats` (plus `id` and `used_software`). `instance_type_notes` is not among them, and it carried a null value in both records. Removed from full and core.

**`data_governance.committee_contact.id` — duplicate identity.** The original minted `doi:10.18130/V3/HIGT4C#person-jillian-parker-governance` for a person the bundle identifies by ORCID (`https://orcid.org/0000-0003-4535-3486`, listed against "Parker J" in the June 2026 author list), while `creators` already carried that ORCID for the same person. Changed to `ORCID:0000-0003-4535-3486`, with `orcid: 0000-0003-4535-3486` added beside it and `email` retained. Applied in both records.

**`creators[*].name` — unsupported given names.** The bundle renders authors as surname plus initial throughout the Dataverse author lists; the preprint gives full names for some but not all. Six names were expansions the bundle nowhere states in that form. All 47 creator names were changed to the bundle's surname-plus-initial form (`Clark T`, `Axelsson U`, `Metallo C`, `Sigaeva A`, `Chinn B`, `Ballllosero Navarro F`, and the rest), with the preprint's full form recorded in each entry's `notes` where the preprint supplies one. This also repaired the accent-stripping finding: `Bélisle-Pipon JC` now carries its accent in `creators`. Applied in both records.

**`preprocessing_strategies`, `labeling_strategies`, `machine_annotation_tools` — pipeline stated as applied.** The release page states "Computed cell maps not included in this release" and "Does not contain predicted cell maps, which will be added in future releases". All three slots were removed from full and core; the MuSIC pipeline is now described in `notes` as the project's pipeline, explicitly as the one producing "the computed cell maps that the June 2026 release states are not included in this release."

## Moderate-severity findings

**`use_repository`** — removed from both records. The entry described the CM4AI Publications page and release archive, not a use-tracking registry; the archive content is already in `version_access.versions_available`.

**`parent_datasets`** — removed from the full record. The entry's `id` was a documentation web page, not a dataset; the release lineage is carried in `related_datasets`.

**`regulatory_restrictions.other_compliance`** — removed from both records. It restated `prohibited_uses[0]` verbatim.

**`instances[*].data_substrate`** — changed in both records. `instances[1]` (SEC-MS) from `B2AI_SUBSTRATE:58` to `:59` (Size Exclusion Chromatography-Mass Spectrometry Data); `instances[2]` (perturb-seq) from `:63` to `:64` (Perturb-seq Data). `instances[3]` (AP-MS) was already `:58` and is unchanged.

**`file_collections[*].total_bytes`** — removed from all ten entries in the full record, and the corresponding `bytes` removed from all ten `distributions` entries in the core. The conversions asserted exact integers from stated round figures ("113.3 KB" → 113300) on an unstated decimal basis, and were applied to only seven of ten collections. The bundle's stated sizes remain in each entry's `notes`. `total_size_bytes` was never populated and remains absent.

## Low-severity findings

**`sampling_strategies[0].strategies`** — changed. The 100-modifier/100-enzyme figure is a project objective from the May 2024 preprint; `strategies` now reads "Targeted selection of cell lines and perturbation targets rather than random sampling," with the objective moved to `notes` and marked as a stated project objective the June 2026 release does not restate.

**`citation`** — changed in the full record: `Belisle-Pipon JC` restored to `Bélisle-Pipon JC` as the bundle writes it. The core schema does not declare `citation`.

**`related_datasets[*].target_dataset`** — all seven changed from `https://doi.org/…` to `doi:` CURIE form, matching `id`, `doi` and `version_access.latest_version_doi`. Applied in both records.

**`prohibited_uses[*].prohibition_reason`** — changed in both. Each now states the reason (regulatory oversight not obtained; commercial rights reserved by the copyright holders), with the prohibition text itself moved to `notes` on entry 0.

**`external_resources[*].archival`** — removed from all seven entries in both records. The bundle states nothing about archival status for any of the named resources.

**`conforms_to`** — changed in both. Retained as RO-Crate but now names its provenance: the preprint and the March/June 2025 releases, not the June 2026 page, whose file listing gives only `cm4ai_release_metadata.zip`. `source_caveats` records the same. `conforms_to_standard: [RO_CRATE]` retained.

**`distribution_formats[0]`** — changed in both. The Data Access API pointer moved out of `notes` into `access_urls`, and `notes` shortened accordingly.

**`regulatory_restrictions.regulatory_restrictions[0]`** — changed in both, now reading "The release records FDA Regulated: No; no export control or regulatory restriction is stated for the release," which states the absence rather than presenting it as an entry.

**`language`** — removed from both. Not stated anywhere in the bundle.

**`last_updated_on`** — added to both as `2026-07-15T00:00:00Z`, supported by the three IF image collections' "Published Jul 15, 2026".

**`ethical_reviews[*].contact_person.orcid`** — added to both entries in both records, from the ORCIDs the bundle states.

**`addressing_gaps[1].response`** — changed in both. The Nature-paper framing was replaced with a statement drawn from the CM4AI sources' own description of cell maps as a foundation for variant interpretation.

**`subsets` / `file_collections` cross-reference** — changed in both. Each of the nine `subsets` descriptions now names its distributing file collection by id, and each corresponding `file_collections` entry names the subset it contains, so neither id space stands unreferenced.

**`notes`** — changed in both. The RO-Crate packaging sentence duplicating `conforms_to` was cut; the residual now carries the module structure, the AI-Ready criteria, the FAIRSCAPE ARK/EVI detail, and the MuSIC pipeline description displaced from the removed preprocessing slots.

## Left as-is

Nothing from the audit was declined outright; the two findings that recommended removal of a whole slot on grounds of duplication (`notes`) or misplacement (`regulatory_restrictions[0]`) were addressed by rewriting rather than removal, since the underlying facts are attested and the slots are the right home for them once restated.

## Dispositions

| slot | disposition | record | reason |
|---|---|---|---|
| `instances[0].instance_type_notes` | removed | both | Not a declared `Instance` slot in the schema digest; carried a null value. |
| `data_governance.committee_contact.id` | changed | both | Minted fragment replaced by `ORCID:0000-0003-4535-3486`, the identifier the bundle supplies for this person. |
| `data_governance.committee_contact.orcid` | added | both | Declared `Person` field the bundle supplies. |
| `creators[*].name` | changed | both | Rendered as the bundle states them (surname plus initial); expanded given names the bundle does not state were removed. |
| `creators[*].notes` | added | both | Records the preprint's full-name form where the preprint supplies one. |
| `creators[46].principal_investigator.orcid` | added | both | Declared `Person` field the bundle supplies. |
| `creators[46].principal_investigator.email` | added | both | Corresponding-author address stated in the preprint. |
| `preprocessing_strategies` | removed | both | Describes the MuSIC pipeline producing cell maps the release states are not included. |
| `labeling_strategies` | removed | both | Same: annotation of cell maps absent from this release. |
| `machine_annotation_tools` | removed | both | Same: tools of the cell-map pipeline, not applied to this release's contents. |
| `use_repository` | removed | both | Held a project publications page and version archive, not a use-tracking registry. |
| `parent_datasets` | removed | full | Pointed at a documentation web page rather than a dataset. |
| `regulatory_restrictions.other_compliance` | removed | both | Duplicated `prohibited_uses[0]`. |
| `instances[1].data_substrate` | changed | both | `B2AI_SUBSTRATE:58` → `:59`, the exact SEC-MS term. |
| `instances[2].data_substrate` | changed | both | `B2AI_SUBSTRATE:63` → `:64`, the exact Perturb-seq term. |
| `instances[3].data_substrate` | retained | both | `B2AI_SUBSTRATE:58` is correct for AP-MS. |
| `file_collections[*].total_bytes` | removed | full | Derived integers on an unstated decimal conversion, applied to only seven of ten collections; stated sizes remain in `notes`. |
| `distributions[*].bytes` | removed | core | Projection of the removed `total_bytes`. |
| `sampling_strategies[0].strategies` | changed | both | Project objective moved to `notes`; `strategies` now states the sampling approach. |
| `sampling_strategies[0].notes` | added | both | Records the preprint's 100/100 objective as a stated project objective, not this release's coverage. |
| `citation` | changed | full | `Bélisle-Pipon` accent restored to the bundle's form; not declared in the core schema. |
| `creators[33].name` | changed | both | `Bélisle-Pipon JC` with accent as the bundle writes it. |
| `related_datasets[*].target_dataset` | changed | both | All seven converted from doi.org resolver URLs to `doi:` CURIEs. |
| `prohibited_uses[0].prohibition_reason` | changed | both | Now states the reason; the prohibition text moved to `notes`. |
| `prohibited_uses[0].notes` | added | both | Holds the release's verbatim prohibition statement. |
| `prohibited_uses[1].prohibition_reason` | changed | both | Now states the reason (commercial rights reserved). |
| `external_resources[*].archival` | removed | both | Archival status not stated for any of the seven resources. |
| `conforms_to` | changed | both | Retained as RO-Crate, now naming the preprint and 2025 releases as its source rather than the June 2026 page. |
| `conforms_to_standard` | retained | both | `RO_CRATE` is the term for the standard `conforms_to` names. |
| `distribution_formats[0].access_urls` | added | both | Data Access API route moved from `notes` into the field for access URLs. |
| `distribution_formats[0].notes` | changed | both | Shortened after the access route moved to `access_urls`. |
| `regulatory_restrictions.regulatory_restrictions[0]` | changed | both | Restated to record the absence of a restriction rather than presenting one. |
| `language` | removed | both | Not stated anywhere in the bundle. |
| `last_updated_on` | added | both | Supported by the three IF collections' "Published Jul 15, 2026". |
| `ethical_reviews[0].contact_person.orcid` | added | both | Declared field the bundle supplies. |
| `ethical_reviews[1].contact_person.orcid` | added | both | Declared field the bundle supplies. |
| `ethical_reviews[1].contact_person.name` | changed | both | Rendered as `Belisle-Pipon JC`, the form the governance/ethics contact line uses. |
| `addressing_gaps[1].response` | changed | both | Nature-paper framing replaced with a statement about the referent. |
| `subsets[*].description` | changed | both | Each now names its distributing file collection by id. |
| `file_collections[*].notes` | changed | both | Each now names the subset it contains; stated size retained. |
| `distributions[*].notes` | changed | core | Projection of the changed `file_collections[*].notes`. |
| `notes` | changed | both | RO-Crate duplication cut; MuSIC pipeline description added, scoped as not applied to this release. |
| `source_caveats` | changed | both | Records the `conforms_to` provenance and the surname-plus-initial naming convention. |
| `maintainers` | changed | both | Split the combined UAB contact entry into two entries, one per person. |
| `distribution_dates[0].release_dates` | changed | both | Rendered as a list, matching the declared multivalued range. |
| `external_resources[*].external_resources` | changed | both | Rendered as lists, matching the declared multivalued range. |
| `total_file_count` | retained | full | Ten files, matching the release listing; not declared in the core schema. |