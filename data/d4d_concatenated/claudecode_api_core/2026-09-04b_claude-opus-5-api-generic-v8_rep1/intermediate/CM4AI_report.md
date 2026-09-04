# CM4AI Reconciliation Report

**Project:** CM4AI (Bridge2AI Functional Genomics Grand Challenge)
**Referent:** Cell Maps for Artificial Intelligence — June 2026 Data Release (Beta), `doi:10.18130/V3/HIGT4C`
**Records:** full (`Dataset`) and core (`CoreDataset`), both regenerated at Phase 4.

---

## 1. What the audit found

The Phase 3 audit returned 24 findings against the full record: four high, thirteen medium, seven low. They clustered as follows.

**Structural and semantic errors (high).** Four `related_datasets` entries declared the June 2026 release to be `is_previous_version_of` each release that in fact precedes it. `instances[0]` carried a key, `instance_description`, that the `Instance` class does not declare — the digest lists only `counts`, `data_substrate`, `data_topic`, `instance_type`, `label`, `label_description`, `missing_information`, `notes`, `sampling_strategies`, `source_caveats`. `total_size_bytes` was 9,700 higher than the sum of the inputs its own caveat named. And roughly twenty identifiers of the form `https://dataverse.lib.virginia.edu/cm4ai#person-…` and `#org-…` were minted for people and organizations that exist outside this dataset, one of which split Jillian Parker's identity between a minted fragment and her attested ORCID.

**Subject drift (medium).** `preprocessing_strategies` entries 3 and 4 and the whole of `labeling_strategies` described production and annotation of the cell map, which the release states it does not contain. `extension_mechanism` drew its text from the Nature U2OS study — a different dataset — and described software availability rather than a contribution route.

**Unsupported or transferred values (medium).** `external_resources[].archival` booleans were inferred from host type. Per-file `bytes` presented rounded Dataverse displays as exact counts. The "464 proteins" figure was carried onto image archives whose MD5 checksums differ from the archives that figure was stated for.

**Neighbouring-field placement (medium).** Access-route detail sat in a `DistributionFormat` note; license terms were restated as a second `prohibited_uses` entry; `regulatory_restrictions` recorded the absence of a restriction.

**Identifier form and provenance hygiene (medium/low).** ORCIDs and one ROR were written as resolver URLs in `uriorcurie` slots. `funders[0]` conflated two distinct NIH records. `language`, `is_tabular` and `last_updated_on` were inferences the sources do not state. `maintainers[2]` recorded a depositor as a maintainer while `created_by` — which the depositor fact answers directly — sat empty. `ip_restrictions` carried a copyright allocation from tier-5 sources without disclosing it. `creators[45]` nested Trey Ideker inside his own Creator entry.

---

## 2. What changed, and why

### 2.1 `related_datasets` relationship direction — changed (both)

All four inter-release entries now read `relationship_type: is_new_version_of` where they previously read `is_previous_version_of`. The record is the June 2026 release; K7TGEM (2025-10-31), F3TD5R (2025-07-01), B35XWX (2025-03-03) and DXWOS5 all precede it. The three non-release entries (`is_documented_by`, `is_referenced_by`, `references`) were already correct and are unchanged.

### 2.2 `instances[0].instance_description` → `label_description` — changed (both)

The prose ("Each image records the spatial localization of one protein of interest…") is retained verbatim under `label_description`, a key the digest does declare on `Instance`. The undeclared key is gone from both records.

### 2.3 `total_size_bytes` — changed (full)

Recomputed as **12,601,718,300**, replacing 12,601,728,000. The sum of 3.8e9 + 4.6e9 + 4.2e9 + 113,300 + 135,800 + 171,800 + 93,900 + 30,200 + 73,300 + 1,100,000 under the 10^9/10^6/10^3 convention the caveat declares. The caveat is extended to state that the aggregate *and* every per-file `bytes` are conversions of rounded displays.

### 2.4 Minted identifiers for external entities — removed (both)

Every `https://dataverse.lib.virginia.edu/cm4ai#person-…` and `#org-…` identifier is gone. Two consequences:

- **Organizations.** `Organization` declares no required `id`, so all `affiliations` entries now carry `name` alone. `https://ror.org/0153tk833` for the University of Virginia is also gone — it was a resolver URL in a `uriorcurie` slot, and with the `id` removed the question is moot.
- **People without an attested ORCID.** Nine creators (Axelsson, Chinn, Fall, Johannesson, Khaliq, Muralidharan, Pan, Polacco, Zhang) now appear as `Creator` objects carrying `name` and `affiliations` and no `id`. `Creator` declares no required `id`, so this validates. They are moved to the end of the `creators` list so the ORCID-bearing entries read contiguously.

### 2.5 Jillian Parker identity split — changed (both)

`data_governance.committee_contact.id` and `regulatory_restrictions.governance_committee_contact.id` now carry `ORCID:0000-0003-4535-3486`, matching the `creators` entry. One person, one identifier.

### 2.6 ORCID CURIE form — changed (both)

Every ORCID in a `uriorcurie` slot is now written `ORCID:0000-…` rather than `https://orcid.org/0000-…`. This covers `creators[].id`, `ethical_reviews[].contact_person.id` and `.orcid`, `data_governance.committee_contact.id` and `.orcid`, and `regulatory_restrictions.governance_committee_contact.id` and `.orcid`.

### 2.7 `preprocessing_strategies` — changed (both)

Entries 3 (contrastive co-embedding) and 4 (community detection producing "the final cell map") are removed. Both described stages whose product the release states it does not contain. The two node2vec and Human Protein Atlas embedding entries are retained: those are dimensionality reduction applied to the input modalities.

### 2.8 `labeling_strategies` — removed (both)

Removed in its entirety. Its subject was annotation of the cell map; no labeling of the AP-MS, SEC-MS, immunofluorescence or perturb-seq files in this release is attested.

### 2.9 `extension_mechanism` — changed (full and core)

The Nature-derived toolkit prose is replaced with text grounded in the CM4AI preprint's own software-availability statement (BSD-3, GitHub for alpha tools, Zenodo for production tools, links packaged in RO-Crates). `contribution_url: https://github.com/idekerlab/cellmaps_pipeline` is now populated; the slot's declared range is `uri`, so a URL is correct there.

### 2.10 `external_resources[].archival` — removed (both)

The boolean is dropped from all nine entries. No source states archival status or future guarantees for MassIVE, Figshare, cm4ai.org or NDEx. `restrictions: [Embargoed]` on the two perturb-seq entries is retained: that is attested.

### 2.11 `distribution_formats[0]` — changed (both)

`access_urls` (the landing page, already in `page`) is removed. The note is reduced to "All ten files in the release are distributed as ZIP archives." The download-limit, Data Access API and Wget routing has moved to top-level `notes`.

### 2.12 Image collection protein count — changed (both)

`file_collections[1].description` (full) / the corresponding `distributions` entry (core) no longer asserts 464 proteins. The description now states the staining protocol and imaging lab without a count, and a per-collection `source_caveats` records that the June 2026 archives carry different MD5 checksums from the October 2025 archives for which 464 was stated.

### 2.13 Per-file `bytes` — changed (both)

Every `File` in `file_collections` (full) and every file-level `distributions` entry (core) now carries its own `source_caveats` naming the displayed size it was converted from. The values themselves are unchanged.

### 2.14 `ethical_reviews[0].review_details` — changed (both)

Rewritten to state only what the release attests: that the named individual is an ethical review contact listed under Data Governance and Ethics. The Value-Sensitive Design and CM4AI Life Cycle material has moved to top-level `notes`, framed there as ongoing programme work rather than a review of this release. Entry 1's `review_details` is aligned to the same wording.

### 2.15 `prohibited_uses[1]` — removed (both)

The CC BY-NC-SA restatement is dropped. The non-commercial condition is already carried three times over: `license_and_use_terms.license_terms`, `license_and_use_terms.data_use_permission: no_commercial_use`, and `ip_restrictions.restrictions[0]`. One `prohibited_uses` entry remains, matching the release's own single-item list.

### 2.16 `regulatory_restrictions.regulatory_restrictions` — removed (both)

The slot `regulatory_restrictions` (the inner list) is removed; the outer `ExportControlRegulatoryRestrictions` object survives carrying `governance_committee_contact`. "FDA Regulated: No" is a determination of non-applicability, not a restriction, and it is already recorded in `human_subject_research.notes`.

### 2.17 `creators[45].principal_investigator` — removed (both)

The self-nesting is gone. Trey Ideker's Creator entry now carries a `notes` field recording that he is named PI of the Bridge2AI Functional Genomics project and point of contact for this release — the role, without duplicating the identity.

### 2.18 `funders` — changed (both)

Split into four entries where there were three. The 1OT2OD032742-01 entry (the release's own funding line) now carries only a note that the release names it. A new second entry carries `3OT2OD032742-01S2` with the RePORTER application number, award amount, dates and PI, and a note that the two share a core project number but that no source states they are the same award. The Bridge Center and Frederick Thomas Fund entries are unchanged.

### 2.19 `maintainers` — changed (both)

Reduced from three entries to two. The depositor entry is removed. The two remaining entries now name the individuals the CM4AI portal lists (Swathi Thaker, Zhandos Sembay) rather than describing the roles anonymously.

### 2.20 `created_by` — added (both)

Now `Justin Niestroy`, from the Dataverse metadata "Depositor: Niestroy, Justin". The range is `string`, so the name is correct here.

### 2.21 `ip_restrictions` — changed (both)

The single restriction string is split into two: the commercial-negotiation requirement and the copyright allocation. A `source_caveats` on the object discloses that the allocation comes from tier-5 historical releases and the preprint, not from the June 2026 release. Top-level `source_caveats` repeats the point.

### 2.22 `language`, `is_tabular`, `last_updated_on` — removed (both)

All three were inferences no source states. `language: en` was read off the prose; `is_tabular: false` off the file types; `last_updated_on` off a file-table publication date rather than any update statement. The image archives' `2026-07-15T00:00:00Z` publication dates survive on the individual `File` objects and in `distribution_dates`, where they are attested.

---

## 3. What was left as-is

**Nothing.** Every one of the 24 findings produced a change in at least one record. The closest thing to a partial disposition is `preprocessing_strategies`, where two of four entries were removed and two retained — but the slot did change, so it is recorded as `changed` rather than `retained`.

Two things worth noting that the audit did *not* raise and that were not altered:

- The **referent choice** is unchanged. Both records describe the June 2026 release as a single dataset, with the U2OS Nature study held at arm's length in `related_datasets` with an explicit note that it is a separate dataset in a different cell line. The audit affirmed this handling.
- The **project-wide aggregates** from cm4ai.org (1,374 interactions, 53,788 images, 7,023 proteins, 11,739 genes, 21.4 TB) remain excluded from the record's own counts, with the exclusion stated in `source_caveats`.

---

## 4. Core record

The core record is a projection of the reconciled full record. Every change above propagates to it except where the slot has no `CoreDataset` counterpart. Specifically:

- `total_size_bytes` and `total_file_count` are full-only; the recomputed byte total appears only in the full record, though the caveat describing it appears in both.
- `file_collections` projects to `distributions` as a flattened list of collections and files; the removed protein count, the added per-file `source_caveats` and the added collection-level `source_caveats` all carry across.
- `direct_collection` and `third_party_sharing` are full-only and were not audited findings.

The core header carries `# Phase 4 reconciliation: completed` and the required `# Sources:` line pointing at the full record.

---

## 5. Outcome

| | full | core |
|---|---|---|
| Populated top-level slots | 60 | 57 |
| LinkML validation | pass (`Dataset`) | pass (`CoreDataset`) |

Findings addressed: 24 of 24. Findings left as-is: 0.

---

## Dispositions

| slot | disposition | record | reason |
|---|---|---|---|
| `related_datasets[0].relationship_type` | changed | both | `is_previous_version_of` → `is_new_version_of`; K7TGEM (2025-10-31) precedes this release. |
| `related_datasets[1].relationship_type` | changed | both | `is_previous_version_of` → `is_new_version_of`; F3TD5R (2025-07-01) precedes this release. |
| `related_datasets[2].relationship_type` | changed | both | `is_previous_version_of` → `is_new_version_of`; B35XWX (2025-03-03) precedes this release. |
| `related_datasets[3].relationship_type` | changed | both | `is_previous_version_of` → `is_new_version_of`; DXWOS5 is the first CM4AI release. |
| `instances[0].label_description` | added | both | Content moved here from the undeclared `instance_description` key. |
| `total_size_bytes` | changed | full | Recomputed to 12,601,718,300 from the ten displayed sizes; prior value exceeded its own inputs by 9,700. |
| `creators[].affiliations` | changed | both | Minted `#org-…` identifiers and the UVA ROR resolver URL removed; entries now carry `name` alone. |
| `creators[].id` | changed | both | ORCIDs rewritten as `ORCID:` CURIEs; minted `#person-…` identifiers removed, leaving nine creators with `name` and `affiliations` only. |
| `data_governance.committee_contact.id` | changed | both | Minted fragment replaced by `ORCID:0000-0003-4535-3486`, ending the identity split for Jillian Parker. |
| `data_governance.committee_contact.orcid` | changed | both | Resolver URL rewritten as `ORCID:` CURIE. |
| `regulatory_restrictions.governance_committee_contact.id` | changed | both | Minted fragment replaced by the attested ORCID CURIE. |
| `regulatory_restrictions.governance_committee_contact.orcid` | changed | both | Resolver URL rewritten as `ORCID:` CURIE. |
| `ethical_reviews[0].contact_person.id` | changed | both | Resolver URL rewritten as `ORCID:` CURIE. |
| `ethical_reviews[1].contact_person.id` | changed | both | Resolver URL rewritten as `ORCID:` CURIE. |
| `preprocessing_strategies` | changed | both | Co-embedding and community-detection entries removed; their product is the cell map, which the release states it does not contain. |
| `labeling_strategies` | removed | both | Subject was cell-map annotation, not labeling of the distributed files. |
| `extension_mechanism.extension_details` | changed | both | Nature U2OS toolkit prose replaced by the CM4AI preprint's own software-availability statement. |
| `extension_mechanism.contribution_url` | added | both | Cell Mapping Toolkit repository URL, which the bundle states; range is `uri`. |
| `external_resources` | changed | both | `archival` boolean removed from all nine entries; no source states archival status. |
| `distribution_formats[0].notes` | changed | both | Reduced to the format statement; access-route detail moved to top-level `notes`. |
| `distribution_formats[0].access_urls` | removed | both | Value was the landing page, already carried in `page`; not an access URL for the distribution. |
| `file_collections[1].description` | changed | full | Protein count removed; June 2026 archives carry different checksums from those for which 464 was stated. |
| `file_collections[1].source_caveats` | added | full | Discloses the checksum difference and the withheld protein count. |
| `file_collections[].resources[].source_caveats` | added | full | Each file records the rounded display size its `bytes` was converted from. |
| `distributions[].source_caveats` | added | core | Same per-file and per-collection caveats as the full record's `file_collections`. |
| `ethical_reviews[0].review_details` | changed | both | Reduced to the attested fact that the person is a named ethical review contact; VSD/Life Cycle material moved to `notes`. |
| `ethical_reviews[1].review_details` | changed | both | Aligned to the same attested wording. |
| `prohibited_uses` | changed | both | Second entry restating CC BY-NC-SA removed; license terms already carried in three other slots. |
| `regulatory_restrictions.regulatory_restrictions` | removed | both | Recorded the absence of a restriction rather than a restriction. |
| `creators[36].notes` | added | both | Records Ideker's PI role and point-of-contact status in place of the removed self-nested `principal_investigator`. |
| `funders` | changed | both | Split into four entries; 1OT2OD032742-01 and 3OT2OD032742-01S2 now recorded separately with the shared core project disclosed. |
| `maintainers` | changed | both | Depositor entry removed; the two portal contacts are now named. |
| `created_by` | added | both | `Justin Niestroy`, from the Dataverse depositor field. |
| `ip_restrictions.restrictions` | changed | both | Split into commercial-negotiation and copyright-allocation entries. |
| `ip_restrictions.source_caveats` | added | both | Discloses that the copyright allocation comes from tier-5 releases and the preprint, not from the June 2026 release. |
| `language` | removed | both | Inferred from the prose; no source states it. |
| `is_tabular` | removed | both | Inferred from file types; no source states the structural form. |
| `last_updated_on` | removed | both | Derived from a file-table publication date, not from any update statement. |
| `notes` | changed | both | Absorbed the access-route detail and the Ethics-module programme description, the latter framed as ongoing work. |
| `source_caveats` | changed | both | Recomputed byte total, rounded-display disclosure extended to per-file values, protein-count conflict resolution restated, copyright-provenance caveat added. |