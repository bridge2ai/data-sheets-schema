# CM4AI Reconciliation Report

Phase 4 reconciliation of the paired full and core D4D records for the CM4AI June 2026 Data Release (Beta), `doi:10.18130/V3/HIGT4C`, against the 24 audit findings.

## Scope and method

The referent is held unchanged: the June 2026 Data Release (Beta), version 2.0, published 2026-06-17 in the University of Virginia Dataverse. Both records were reconciled together; every change made in the full record was propagated to the core record where the slot exists there.

## High-severity findings

### 1. Inverted release relationships (`related_datasets`) — changed, both records

The audit is correct. Four entries declared `relationship_type: is_previous_version_of` toward releases that precede this one. All four were changed to `is_new_version_of`:

- `https://doi.org/10.18130/V3/K7TGEM` (October 2025)
- `https://doi.org/10.18130/V3/F3TD5R` (June 2025)
- `https://doi.org/10.18130/V3/B35XWX` (March 2025)
- `https://doi.org/10.18130/V3/DXWOS5` (first release)

The `notes` on each entry are unchanged; only the enum value was corrected. The three non-version relationships (`is_documented_by`, `is_referenced_by`, `references`) were correct and are unchanged.

### 2. `instances[0].instance_description` — changed, both records

The schema digest lists Instance's accepted keys and `instance_description` is not among them. The content was moved verbatim to `label_description`, which the digest does declare. No content was lost.

### 3. `total_size_bytes` arithmetic — changed, full record

The audit's sum is correct. The value was changed from `12601728000` to `12601718300`, matching the ten displayed sizes under the 10^9/10^6/10^3 convention the record's own caveat declares. The `source_caveats` text was expanded to state that the aggregate and every per-file `bytes` value are conversions of rounded displays rather than exact counts. `total_size_bytes` is not present in the core record and required no propagation.

### 4. Minted identifiers for external entities (`creators`, `data_governance`) — changed, both records

Every minted `https://dataverse.lib.virginia.edu/cm4ai#person-*` and `#org-*` identifier was removed. Organization objects now carry `name` alone, which the digest permits since Organization declares no required key. The nine creators who had no attested ORCID (U Axelsson, B Chinn, J Fall, A Johannesson, H Khaliq, M Muralidharan, E Pan, B Polacco, Y Zhang) now carry `name` and `affiliations` without an `id`; they were moved to the end of the creator list.

### 5. Jillian Parker identity split (`data_governance.committee_contact.id`) — changed, both records

The minted fragment was replaced with her attested identifier, `ORCID:0000-0003-4535-3486`, matching her `creators` entry. The same person is now named by one identifier throughout.

## Medium-severity findings

### 6. Resolver URLs in `uriorcurie` slots — changed, both records

All ORCID identifiers in `creators[].id`, `ethical_reviews[].contact_person.id` and `data_governance.committee_contact.id` were converted from `https://orcid.org/0000-...` to `ORCID:0000-...` CURIEs. The `orcid` fields on Person objects were reduced to the bare identifier. The University of Virginia ROR URL is no longer present, since the affiliation objects that carried it now hold `name` only.

### 7. `preprocessing_strategies` subject drift — changed, both records

The two entries describing contrastive co-embedding and multi-resolution community detection, whose stated product is "the final cell map," were removed. The release states cell maps are not included. The two remaining entries (node2vec on PPI networks, Human Protein Atlas model on images) describe processing of modalities the release does contain.

### 8. `labeling_strategies` — removed, both records

The single entry described annotation of cell maps, which this release does not contain. No labeling of the AP-MS, SEC-MS, immunofluorescence or perturb-seq files is attested. The slot was removed from both records.

### 9. `extension_mechanism` — changed, both records

The Nature U2OS toolkit description was replaced with the CM4AI preprint's own statement about software availability under BSD-3 in GitHub or Zenodo, with links packaged in RO-Crates. `contribution_url: https://github.com/idekerlab/cellmaps_pipeline` was added, which the audit noted was available in the bundle.

### 10. `external_resources[].archival` — removed, both records

Every `archival` boolean was removed from all nine entries. The bundle makes no statement about archival status for any of these hosts. The `restrictions: [Embargoed]` values on the two embargoed entries are attested and were retained. The `external_resources` string fields were also converted to single-item lists to match the declared multivalued range.

### 11. `distribution_formats[0].notes` and `access_urls` — changed, full and core

The access-routing content (1.9 GB limit, Data Access API, Wget instructions) was moved to the top-level `notes`. `access_urls`, which held the landing page rather than a distribution access URL, was removed; the landing page remains in `page`. The `notes` on the format object now states only that all ten files are ZIP archives.

### 12. `file_collections[1].description` protein count — changed, full record

The "464 proteins of interest" figure was removed from the image collection description. A collection-level `source_caveats` was added recording that the June 2026 archives carry different MD5 checksums from the October 2025 archives the figure was stated for. The top-level `source_caveats` was updated correspondingly. In the core record this collection appears under `distributions`; the same change was made there.

### 13. Per-file `bytes` rounding — changed, both records

A per-file `source_caveats` was added to each of the ten File objects naming the displayed size the byte value was converted from.

### 14. `ethical_reviews[].review_details` — changed, both records

The Value-Sensitive Design and CM4AI Life Cycle text was removed from the first entry. Both entries now state only what the release attests: that the named individuals are the ethical review contacts for this release. The VSD material was moved to the top-level `notes`, framed as ongoing programme work in the preprint's own tense.

### 15. `prohibited_uses[1]` — removed, both records

The non-commercial restatement was removed. The condition remains in `license_and_use_terms.license_terms`, `license_and_use_terms.data_use_permission` and `ip_restrictions.restrictions`. One entry remains, matching the release's own Prohibited Uses section.

### 16. `regulatory_restrictions` — removed, both records

The slot held only a statement that no restriction applies, plus a governance contact duplicating `data_governance`. The whole slot was removed from both records.

## Low-severity findings

### 17. `creators[45].principal_investigator` self-nesting — changed, both records

The nested Person was removed from Trey Ideker's Creator entry. His entry now carries `id`, `name`, `affiliations` and a `notes` field recording that he is named as principal investigator of the CM4AI Bridge2AI Functional Genomics Data Generation Project and as the point of contact for this release. That `notes` field sits on the Ideker entry, which after the reordering described in finding 4 is `creators[37]` in the full record and `creators[37]` in the core record — not `creators[36]`, as an earlier draft of this report stated.

### 18. `funders[0].notes` conflation — changed, both records

The RePORTER supplement details were split into a separate `funders` entry with `grant_number: 3OT2OD032742-01S2`, carrying the award amount, dates and PI. The first entry now names only 1OT2OD032742-01 as the release states it. The new entry's `notes` records that the two share a core project number but that the sources do not state they are the same award.

### 19. `language` — removed, both records

Not stated anywhere in the bundle. Removed.

### 20. `last_updated_on` — removed, both records

Derived from a file publication date rather than any statement about the dataset's last update. Removed.

### 21. `maintainers[2]` depositor — removed, both records

The depositor entry was removed from `maintainers`. The two remaining entries are the portal contacts the cm4ai.org site names for project inquiries and website support; their `maintainer_details` were expanded to name the individuals.

### 22. `ip_restrictions` provenance — changed, both records

The single restriction string was split into two list entries, separating the commercial-license requirement from the copyright allocation. An `ip_restrictions.source_caveats` was added recording that the copyright allocation comes from tier 5 historical releases and the preprint, and that the June 2026 release does not restate it. The top-level `source_caveats` notes the same.

### 23. `is_tabular` — removed, both records

Inferred from file types rather than stated. Removed.

### 24. `created_by` — added, both records

`created_by: Justin Niestroy` was added, from the Dataverse depositor field.

## Additional structural corrections

Two range mismatches were corrected while reconciling adjacent findings:

- `distribution_dates[0].release_dates` was converted from a string to a single-item list.
- `known_biases[0].scope_impact` was moved to `notes`; `scope_impact` is declared on DatasetLimitation, not DatasetBias.

## Nothing left contested

Every audit finding was acted on. No finding was judged incorrect and left in place.

## Dispositions

| slot | disposition | record | reason |
|---|---|---|---|
| `related_datasets[0].relationship_type` | changed | both | `is_previous_version_of` inverted; the October 2025 release precedes this one |
| `related_datasets[1].relationship_type` | changed | both | Same inversion for the June 2025 release |
| `related_datasets[2].relationship_type` | changed | both | Same inversion for the March 2025 release |
| `related_datasets[3].relationship_type` | changed | both | Same inversion for the first release |
| `instances[0].label_description` | added | both | Content moved from the undeclared `instance_description` key |
| `total_size_bytes` | changed | full | Corrected to 12601718300, matching the sum of its own declared inputs |
| `creators` | changed | both | Minted person and organization identifiers removed; ORCIDs written as CURIEs |
| `data_governance.committee_contact.id` | changed | both | Minted fragment replaced with her attested ORCID CURIE |
| `ethical_reviews[0].contact_person.id` | changed | both | Resolver URL converted to `ORCID:` CURIE |
| `ethical_reviews[1].contact_person.id` | changed | both | Resolver URL converted to `ORCID:` CURIE |
| `preprocessing_strategies` | changed | both | Two cell-map-production entries removed; the release states cell maps are not included |
| `labeling_strategies` | removed | both | Described annotation of a cell map this release does not contain |
| `extension_mechanism.extension_details` | changed | both | Nature U2OS toolkit text replaced with the CM4AI preprint's own software-release statement |
| `extension_mechanism.contribution_url` | added | both | Toolkit repository URL, available in the bundle |
| `external_resources` | changed | both | `archival` booleans removed as unsupported; string fields converted to lists |
| `distribution_formats[0].notes` | changed | both | Access-routing content moved to top-level `notes` |
| `distribution_formats[0].access_urls` | removed | both | Held the landing page, which `page` already carries |
| `file_collections[1].description` | changed | full | 464-protein figure removed; archives differ by checksum from those it was stated for |
| `file_collections[1].source_caveats` | added | full | Records the checksum difference and the withheld protein count |
| `distributions[3].source_caveats` | added | core | Same caveat, projected into the core record |
| `file_collections[0].resources[0].source_caveats` | added | full | Names the displayed size the byte value converts from |
| `distributions[1].source_caveats` | added | core | Same, projected |
| `ethical_reviews[0].review_details` | changed | both | VSD programme text removed; entry now states only the attested contact role |
| `ethical_reviews[1].review_details` | changed | both | Reworded to match, stating only the attested contact role |
| `prohibited_uses` | changed | both | Non-commercial restatement removed as duplicating the license slots |
| `regulatory_restrictions` | removed | both | Held only an absence-of-restriction statement and a duplicated contact |
| `creators[37].notes` | added | both | PI role recorded in prose instead of by self-nesting a Person |
| `funders[0].notes` | changed | both | RePORTER supplement details split out to their own entry |
| `funders[1]` | added | both | Separate entry for `3OT2OD032742-01S2` with its own award details |
| `language` | removed | both | Not stated anywhere in the bundle |
| `last_updated_on` | removed | both | Derived from a file publication date, not from any update statement |
| `maintainers` | changed | both | Depositor entry removed; remaining entries name the portal contacts |
| `ip_restrictions.restrictions` | changed | both | Split into two entries separating license requirement from copyright allocation |
| `ip_restrictions.source_caveats` | added | both | Records that only tier 5 sources and the preprint state the copyright allocation |
| `is_tabular` | removed | both | Inferred from file types rather than stated |
| `created_by` | added | both | Dataverse depositor field |
| `distribution_dates[0].release_dates` | changed | both | Converted to a list to match the declared multivalued range |
| `known_biases[0].notes` | added | both | Content moved from `scope_impact`, which DatasetBias does not declare |
| `source_caveats` | changed | both | Extended to cover rounded byte displays, the withheld protein count and the copyright provenance |
| `notes` | changed | both | Absorbed the access-routing detail and the VSD programme description |

---

**Full record slot count:** 55 top-level slots populated
**Core record slot count:** 54 top-level slots populated
**Validation:** both files validate against their respective schemas
**Reconciliation outcome:** all 24 findings acted upon; none contested