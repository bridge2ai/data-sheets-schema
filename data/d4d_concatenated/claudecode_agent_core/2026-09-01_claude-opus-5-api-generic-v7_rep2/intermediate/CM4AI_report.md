# CM4AI D4D Reconciliation Report

**Project:** CM4AI (Bridge2AI Functional Genomics Grand Challenge)
**Version label:** 2026-09-01_claude-opus-5-api-generic-v7_rep2
**Referent:** Cell Maps for Artificial Intelligence — June 2026 Data Release (Beta), `doi:10.18130/V3/HIGT4C`
**Records:** full (`Dataset`) and core (`CoreDataset`), both reconciled against the Phase 3 audit.

---

## 1. Referent decision (restated, unchanged)

The declared bundle contains five Dataverse release records in one quarterly series. Under the declared source ranking, `june_2026_dataverse_release` (tier 1) supersedes `october_2025_dataverse_release` (tier 1, marked SUPERSEDED BY), and both outrank the tier-5 historical releases. The record describes the June 2026 release as a single referent; the March 2025, June 2025 and October 2025 releases are carried as `related_datasets` entries with `is_new_version_of`, not merged into the description. This choice was held identically in both records and was not revisited in Phase 4.

The Nature publication (Schaffer et al., U2OS cell map) remains treated as methods evidence for the shared pipeline, not as a CM4AI release; its U2OS-specific figures continue to be excluded from every slot value. Portal-level project totals (1,374 protein interactions, 53,788 images, 7,023 proteins, 11,739 genes, 21.4 TB) likewise remain excluded as project-scope rather than release-scope.

---

## 2. Audit summary

The Phase 3 audit returned twenty findings: three high, six medium, eleven low. Fifteen produced changes to the records; five were left as-is with reasons recorded below.

---

## 3. High-severity findings — all three repaired

### 3.1 `instances[0].instance_details` — invented key (#380)

**Audit:** The `Instance` class in the schema digest declares `counts`, `data_substrate`, `data_topic`, `instance_type`, `label`, `label_description`, `missing_information`, `notes`, `sampling_strategies`, `source_caveats`. `instance_details` is not among them.

**Change (both records):** The `instance_details` key was removed from the first `instances` entry. Its channel/staining prose was merged into the existing `notes` value, which now opens "Each image displays the spatial localization of one protein of interest… DAPI (blue channel); endoplasmic reticulum with a calreticulin antibody (yellow channel); microtubules with tubulin antibody (red channel); and antibody against the protein of interest (green channel)." and continues with the per-release protein counts that `notes` already carried. The accompanying `source_caveats` value on that entry — which flagged the key as possibly undeclared and said the content "belongs in `notes` if the key is not schema-declared" — was dropped, since the condition it hedged against has now been resolved.

No content was lost; only the carrier changed.

### 3.2 `creators[4]` — invented given name and non-CURIE identifier

**Audit:** `id: Uma Axelsson` is neither URI nor CURIE; the given name "Uma" appears nowhere in the bundle, which gives only "Axelsson U (KTH Royal Institute of Technology,)". No ORCID is supplied for this author in any bundle source.

**Change (both records):** The `id` key was removed entirely from this creator. The `name` was changed from `U Axelsson` (an inverted form) to `Axelsson U`, the surname-initial form the bundle actually uses. The `source_caveats` was rewritten to state the ground: "The declared bundle lists this author only as 'Axelsson U' with no personal identifier in any source, so no identifier is supplied and the name is retained in the surname-initial form the bundle uses." The redundant `notes` line that repeated the same fact was dropped.

Under the v5 rule, a person's identifier is a fact about the world: take it from evidence or omit it. Omission was the only correct option, and the schema does not require `id` on `Creator`.

### 3.3 `creators[0].affiliations[0].id` — unsupported ROR identifier

**Audit:** `https://ror.org/0168r3w48` for UCSD is not stated anywhere in the bundle. The only ROR identifier the bundle contains is `https://ror.org/0153tk833` (University of Virginia, in the June 2026 author block). The record's own `source_caveats` conceded the identifier "is not stated in the declared bundle" while emitting it — a direct self-contradiction. The value was also a resolver URL where a CURIE would be required.

**Change (both records):** The UCSD affiliation `id` was removed; the affiliation now carries `name: University of California San Diego` only. The `source_caveats` was rewritten to state the omission as a decision rather than confessing a contradiction: "The declared bundle supplies no organization registry identifier for the University of California San Diego, so the affiliation carries a name only."

**Related change applied at the same time:** the one ROR identifier the bundle *does* supply was put to work. Five creators the bundle affiliates with the University of Virginia — Timothy Clark, Sadnan Al Manir, Maxwell Adam Levinson, Justin Niestroy, Sarah Ratcliffe — now carry `id: ROR:0153tk833` on their affiliation objects, written as a CURIE rather than the resolver URL the bundle uses. This is attested (the June 2026 author block gives `https://ror.org/0153tk833` for each of these authors) and is the v5-required rendering.

---

## 4. Medium-severity findings

### 4.1 `publisher` self-reference — repaired

**Audit:** `publisher: doi:10.18130/V3/HIGT4C` pointed at the dataset itself rather than at the organization making it available.

**Change (both records):** `publisher` is now `ROR:0153tk833` — the University of Virginia, whose Dataverse (LibraData) publishes the release, using the one ROR identifier the bundle attests and rendering it as a CURIE.

### 4.2 `conforms_to` / `conforms_to_standard` — category error, repaired by relocation

**Audit:** RO-Crate is the packaging format for the metadata and provenance graphs, not a standard the imaging, mass-spectrometry or sequencing content follows. The slot description restricts `conforms_to` to standards the dataset's own content follows.

**Change (both records):** Dataset-level `conforms_to: RO-Crate` and `conforms_to_standard: [RO_CRATE]` were removed. Both were moved onto the one component the claim is true of: the `release-metadata` file collection, which now carries `conforms_to: RO-Crate` and `conforms_to_standard: [RO_CRATE]`. The `FileCollection` class accepts both slots per the digest, and the corresponding core `distributions` entry carries them too. A sentence in `source_caveats` records the reasoning.

`conforms_to_schema` and `conforms_to_class` were untouched — they describe the record, not the data, and were already correct.

### 4.3 Inconsistent byte conversions — repaired by omission

**Audit:** Three IF archives used decimal conversion (4.6 GB → 4600000000) while the small archives used binary (113.3 KB → 116019), within a single slot. All were approximations of rounded repository figures.

**Change (both records):** `total_bytes` was removed from all ten `file_collections` entries (and the corresponding `bytes` from all ten core `distributions` entries). Each collection now carries a `source_caveats`: "The repository states file sizes only in rounded human-readable units, so no exact byte count is available and total_bytes is omitted rather than approximated." The human-readable figure remains in `notes` alongside the MD5, where it is a transcription rather than a computed claim.

This applies to `file_collections` the same reasoning the original record had already applied to `total_size_bytes`, which remains omitted. The dataset-level `source_caveats` was extended to say so explicitly.

### 4.4 Sali affiliation — v5 disagreement rule now applied

**Audit:** The emitted value correctly followed the tier-1 source, but the caveat said the sources were "not reconciled by it" rather than recording that the higher-ranked source was preferred.

**Change (both records):** The affiliation value is unchanged (University of California San Diego, per the tier-1 June 2026 release). The `source_caveats` was rewritten to the form the v5 rule requires: it names the disagreement, states what each source said, gives the tier of each, and says which was preferred and why — "The higher-ranked Dataverse release is preferred and its value is stated here."

The parallel caveat on `collection_timeframes` was also revised (see 4.7).

### 4.5 Landing page in `access_urls` — repaired

**Audit:** The Dataverse landing page URL was placed in `access_urls`, a slot for data access rather than description.

**Change (both records):** `access_urls` was removed from the `distribution_formats[0]` entry. The access route it described is now stated in that entry's `notes`, which mentions the 1.9 GB per-file limit and the Dataverse Data Access API for programmatic access.

### 4.6 `page` pointing at the project index — repaired

**Audit:** `page` held `https://cm4ai.org/data-releases/`, the project-wide release index, while the release's own landing page was carried in `access_urls`.

**Change (both records):** `page` is now `https://dataverse.lib.virginia.edu/dataset.xhtml?persistentId=doi:10.18130/V3/HIGT4C`. This is the release's own landing page and, being in a `string`-ranged slot, remains a URL.

### 4.7 `collection_timeframes` — award period no longer stands in for collection dates

**Audit (recorded as low severity, but repaired):** `start_date: 2022-09-01` / `end_date: 2026-08-31` were the NIH award period, not a data collection window. The bundle states no collection window.

**Change (both records):** Both `start_date` and `end_date` were removed. `timeframe_details` now opens by stating that the bundle does not supply collection dates, then records what it does supply: the 2025-02-27 creation date, the November 2026 maintenance horizon, and the RePORTER award period, described as bounding but not defining the collection window. The `source_caveats` was rewritten to explain that neither of the two disagreeing dates is a collection date, so neither was promoted into a date slot.

---

## 5. Low-severity findings — repaired

### 5.1 `created_by` — now the copyright holder

**Change (both records):** `created_by` changed from `Cell Maps for Artificial Intelligence (CM4AI)` (a project name) to `The Regents of the University of California`, the copyright holder the bundle names.

### 5.2 Personal name forms — unattested expansions and inversions corrected

**Change (both records):**
- `Tim Clark` → `Timothy Clark`, the form the bioRxiv preprint gives. A `notes` line records that the release citation gives "Clark T" and the preprint the full form.
- `U Axelsson` → `Axelsson U` (see 3.2).
- `F Ballllosero Navarro` → `Ballllosero Navarro F`
- `J Gao` → `Gao J`
- `Y H Lee` → `Lee YH`
- `A Sigaeva` → `Sigaeva A`

Each of these now matches the surname-initial form the bundle prints, rather than an inversion the bundle does not license. Creators for whom the bundle supplies a full name (Trey Ideker, Mengzhou Hu, Leah Schaffer and the rest) are unchanged.

### 5.3 `external_resources` — MassIVE depositions split

**Audit:** Four distinct MassIVE accessions were collapsed into one object, contrary to the v2 one-object-per-entity rule.

**Change (both records):** The single MassIVE entry became four: SEC-MS in KOLF2.1J iPSCs; SEC-MS in MDA-MB-468; AP-MS in MDA-MB-468 paclitaxel; AP-MS in MDA-MB-468 vorinostat. Each carries `archival: true`. The SRA, Figshare, portal, toolkit, FAIRSCAPE, IMP and NDEx entries are unchanged. The list grew from eight entries to eleven.

### 5.4 `keywords` — Dataverse Subject removed

**Change (both records):** `Medicine, Health and Life Sciences` was dropped from `keywords`. The bundle lists it under "Subject", a distinct field from the twenty-nine "Keyword" values, all of which remain.

### 5.5 Perturb-seq substrate term — more precise term adopted

**Change (both records):** The fourth `instances` entry changed `data_substrate` from `B2AI_SUBSTRATE:63` (Single-cell RNA Sequence Data) to `B2AI_SUBSTRATE:64` (Perturb-seq Data), the exact term for what the entry describes.

### 5.6 `errata` — relocated to the release it concerns

**Audit:** The erratum described a revision to the June 2025 release (`doi:10.18130/V3/F3TD5R`), a different dataset.

**Change (both records):** The `errata` slot was removed. The fact it carried — that the June 2025 release was revised to add RGB immunofluorescent images, correct RO-Crate metadata, and change naming conventions — is now a second sentence in the `notes` of the `related_datasets` entry for that release, where it is a statement about that dataset rather than an erratum against this one.

### 5.7 `existing_uses` — removed, content relocated

**Audit:** Both entries described training and dissemination activities (CodeFest, internship), not research, commercial or analytical uses of the dataset. The bundle states no downstream use of this release.

**Change (both records):** `existing_uses` was removed. The CodeFest and internship descriptions were appended to the dataset-level `notes`, introduced as "Beyond research use, project data and tools have supported training and dissemination activities". A sentence in `source_caveats` records that no downstream use is stated in the bundle and that this is why the slot is omitted.

### 5.8 `at_risk_populations` — asymmetry corrected

**Audit:** `human_subject_research.involves_human_subjects: false` was asserted while the parallel `at_risk_populations.at_risk_groups_included: false` was omitted.

**Change (both records):** `at_risk_populations` was added with `at_risk_groups_included: false` and a `notes` explaining that all data derive from established cell lines rather than living individuals, so no at-risk population protections apply.

### 5.9 `data_governance.committee_name` — synthesized prefix dropped

**Change (both records):** `CM4AI Data Access Committee` → `Data Access Committee`, the term the preprint uses. The `source_caveats` was rewritten to note that the June 2026 release labels its field "Data Governance Committee" and names a contact, while the preprint names the body "A Data Access Committee", and that the emitted name follows the preprint because it is the only term the bundle uses as a name.

---

## 6. Findings left as-is

### 6.1 `total_file_count: 10` (audit 5.14)

Left unchanged. The audit flagged only that no per-collection `file_count` is supplied so the aggregate cannot be verified internally, and confirmed the value is consistent with both the June 2026 file listing and the ten `file_collections` entries. The bundle does not state file counts within archives, so `file_count` remains correctly omitted on each collection.

### 6.2 `download_url` omission (audit 5.20)

Left omitted. The audit called the omission defensible and flagged it only for completeness. The bundle supplies a Data Access API base and a landing page but no direct download URL for the dataset as a whole, and the record correctly notes the dataset is too large to download as a single archive. The API base is described in `distribution_formats[0].notes` rather than promoted into a `uri`-ranged slot it does not fit.

### 6.3 `external_resources` free-text prose (audit 5.13, in part)

The multiple-entities half of this finding was repaired (see 5.3). The prose-carrier half was left as-is: the audit itself confirmed the `ExternalResource` class declares no name or URL key, so `external_resources` is the only carrier available and this is not a schema violation.

### 6.4 Remaining B2AI substrate mappings (audit 5.16, in part)

`B2AI_SUBSTRATE:19` (Image), `:59` (SEC-MS Data) and `:58` (Mass Spectrometry Data) were left unchanged. The audit found no evidence problem with any of them and identified a more precise available term only for Perturb-seq, which was adopted (see 5.5).

---

## 7. Full/core consistency

Every change above was applied identically to both records. The referent, the DOI, the version, the license, the governance contacts, the creator list and its identifiers, the instance typing, the file/distribution inventory and both narrative slots (`notes`, `source_caveats`) are the same in both, allowing for the schema-driven rename of `file_collections`/`total_bytes` to `distributions`/`bytes` in the core record — where `bytes` is now absent in all ten entries, matching the full record's omission of `total_bytes`.

The core record's `conforms_to_class` is `CoreDataset` and its `conforms_to_schema` names the core schema, as required. Its header carries `# Sources:` naming the full record and `# Phase 4 reconciliation: completed`.

---

## 8. Outcome

Twenty findings: fifteen repaired, five left as-is with reasons stated. All three high-severity findings — the invented `instance_details` key, the invented person identifier, and the unsupported ROR identifier — are resolved by removal rather than by substituting a different unsupported value. Two identifier slots (`publisher`, five UVA affiliations) were newly populated using the single ROR identifier the bundle attests, rendered as CURIEs. Net effect on the evidence boundary: the records now assert nothing the declared bundle does not supply, and the two places where the original record's own caveats contradicted its own values are eliminated.