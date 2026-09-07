# Reconciliation Report — CM4AI D4D Records

**Project:** CM4AI (Bridge2AI Functional Genomics Grand Challenge)
**Referent:** Cell Maps for Artificial Intelligence — June 2026 Data Release (Beta), `doi:10.18130/V3/HIGT4C`
**Records:** full (`Dataset`) and core (`CoreDataset`)
**Phase:** 4 — strict reconciliation against the Phase 3 audit

---

## 1. What the audit found

The Phase 3 audit returned nineteen findings against the full record: two high, six medium, eleven low. They fall into a small number of recurring kinds:

- **Shape defects.** One undeclared attribute (`instance_details`) used on every `Instance` object, and one arithmetic inconsistency between a derived total and the record's own inputs.
- **Boundary slippage from outside the bundle.** Two given names supplied from model knowledge rather than the documents.
- **Version-attribution drift.** Facts about the October 2025 image archives stated as facts about the June 2026 archives, and the 464-protein count attributed to a source that does not state it.
- **Subject drift.** MuSIC pipeline stages stated as preprocessing of a release that explicitly excludes their outputs, with one tool name drawn from a different dataset's paper.
- **Field-purpose mismatches.** A prohibition placed in the field asking for its reason; a constructed committee name; a planned activity rendered in the present tense.
- **Identifier form and attribution.** Resolver URLs where the record elsewhere uses `doi:` CURIEs; an unused ROR the bundle supplies; contact and funder attributions the release listing does not make.
- **Two supported omissions.** A ROR identifier and a documented erratum, both present in the bundle and both absent from the record.

The audit also noted, correctly, that the record's core factual spine — the 47-author roster, all ten files with sizes and checksums, licence terms, governance and ethics contacts, the version chain — is faithfully attested.

---

## 2. What was changed, and why

### 2.1 High severity

**`instances[*].instance_details` → `instances[*].notes` (full and core).**
The schema digest lists the `Instance` slots as `counts`, `data_substrate`, `data_topic`, `instance_type`, `label`, `label_description`, `missing_information`, `notes`, `sampling_strategies`, `source_caveats`. `instance_details` is not among them. All three `Instance` objects carried it. In both reconciled records the key has been renamed to `notes` on all three objects; the prose is otherwise preserved, save that the immunofluorescence entry now attributes the channel description to "the corresponding archives of the October 2025 release", which is where the bundle actually states it (see 2.3).

**`total_size_bytes`: 12601604198 → 12601718300 (full).**
The record's own `file_collections[].total_bytes` values (249,100 + 12,600,000,000 + 265,700 + 103,500 + 1,100,000) and its ten `File.bytes` values both sum to 12,601,718,300. The stated total was 114,102 bytes short of that, reachable by neither the decimal conversion the caveat describes nor a binary one. A figure declared as the record's own computation must equal the inputs it names. The value has been corrected and `source_caveats` amended to state explicitly that the total "equals the sum of the per-file bytes and per-collection total_bytes values recorded below". `total_size_bytes` is a full-record slot only; the core record carries per-distribution `bytes` values, which were already internally consistent and are unchanged.

### 2.2 Unsupported given names

**`creators[].name` for Axelsson and Metallo (full and core).**
"Ulrika Axelsson" and "Christian Metallo" were reduced to "Axelsson U" and "Metallo C", the forms the bundle attests. Every other expanded given name in the roster traces to the bioRxiv author list or a governance contact line; these two did not. A correct name the documents do not contain is still an unsupported claim.

### 2.3 Version attribution — the immunofluorescence archives

Three linked changes, all in `file_collections[#collection-ifimages]` (full) and the corresponding `distributions` entry (core):

- **`description`** now reads only what the June 2026 listing supports: three ZIP archives for MDA-MB-468 in untreated, paclitaxel-treated and vorinostat-treated conditions. The 464-protein count, the DAPI/calreticulin/tubulin channel assignments and the Lundberg Lab attribution have been moved out.
- **A collection-level `source_caveats`** has been added recording that description as a fact about the October 2025 archives, and stating that the June 2026 archives carry different MD5 checksums and so are not the same files.
- **The dataset-level `source_caveats`** has been corrected. The original said the count 464 was stated by "the June 2025 and June 2026 releases" and that "the higher-ranked June 2026 release value (464) is used". The June 2026 listing states no protein count at all. The corrected text names the actual attesting sources — March 2025 (tier 5, 563) against June 2025 (tier 5) and October 2025 (tier 1), both 464 — and states that the ranking is decided by the October 2025 release. The preferred value is unchanged; only its provenance is now stated correctly.

### 2.4 Subject drift — the MuSIC pipeline

**`preprocessing_strategies`, `labeling_strategies` and `machine_annotation_tools` removed from both records; the content restated in `notes`.**
The release states plainly that "Computed cell maps not included in this release." The node2vec embedding, the image embedding, the contrastive co-embedding, the community detection, the GO/Reactome alignment and the LLM naming step all produce outputs the referent does not contain. Stating them as preprocessing applied to this dataset misdescribes the release. The `notes` slot in both records now carries the pipeline description with an explicit qualifier: these stages "describe project tooling and planned future releases rather than processing applied to the data released here."

This also disposes of the DenseNet-121 finding. That name came from the Nature U2OS paper, which describes a different dataset; the CM4AI preprint says only "a Human Protein Atlas deep learning model", and that is the wording the `notes` prose now uses.

**`tasks[3]` rewritten (full and core).** The fourth task was "Construction of hierarchical cell maps from fusion of protein interaction and imaging data…" — again an activity whose output this release excludes. It has been replaced with "Bioinformatics analysis of the individual modality datasets, which the release states is what the current release is most suitable for", which is what the release says the data support.

### 2.5 Field-purpose corrections

**`prohibited_uses[0]` (full and core).** The prohibition itself has moved to `notes`; `prohibition_reason` now states the reason — absence of the regulatory oversight and approval that clinical use requires, with the release's own "FDA Regulated: No" record as support.

**`data_governance.committee_name`: "CM4AI Data Access Committee" → "Data Governance Committee" (full and core).** The release page labels the field "Data Governance Committee"; the preprint refers to "A Data Access Committee" without a formal title. The constructed name has been replaced by the attested label.

**`data_governance.access_review_process` (full and core).** The preprint's future tense has been restored: the text now says the release "names a Data Governance Committee contact" and that the preprint "states that a Data Access Committee **will** supervise" — a plan stated as a plan. A `source_caveats` has been added to the `data_governance` object recording both the label and the tense.

### 2.6 Identifier form and supported additions

**`related_datasets[].target_dataset` (full and core).** All seven targets converted from `https://doi.org/…` resolver URLs to `doi:` CURIEs, matching `version_access.latest_version_doi`. One scheme, one identity.

**`ROR:0153tk833` added to the five University of Virginia affiliations (full and core).** The June 2026 release page states this identifier for Clark, Al Manir, Levinson, Niestroy and Ratcliffe. The bundle supplies it, so it is now carried.

**`errata` added (full and core).** The June 2025 release states it was a revision adding RGB immunofluorescent images, making "corrections to ro-crate metadata", and changing naming conventions — a documented correction, and `Erratum` is its declared home.

**`Person.orcid` values de-prefixed (full and core).** In all five `Person` objects the `orcid` attribute now carries the bare identifier (`0000-0002-1708-8454`) rather than the `ORCID:`-prefixed form, while `id` retains the CURIE. The `id` slot is `uriorcurie` and takes the CURIE; `orcid` is a distinct attribute and does not need the prefix repeated.

### 2.7 Diacritic restoration

**`citation` and `creators[].name` (full and core).** "Belisle-Pipon" → "Bélisle-Pipon" in the verbatim Dataverse citation string, in the creator entry, and in the `ethical_reviews[1].contact_person.name`. American-English orthography governs composed prose; it does not govern quoted material or proper nouns.

### 2.8 Attribution corrections

**`license_and_use_terms.contact_person` removed (full and core).** Trey Ideker is attested as the Dataverse Point of Contact and the preprint's corresponding author, but no source names him as the licensing contact. The commercial-licence route the bundle states — negotiation with UCSD, Stanford and/or UCSF — has been folded into `license_terms` instead, and Ideker's role and email are now recorded in `maintainers` where the bundle supports them.

**`funders[1]` and `funders[2]` notes amended (full and core).** Both now state that the Dataverse release listing records only 1OT2OD032742-01 as its own funding, and that these are project-level acknowledgements from the preprint rather than funding attributed to this release. The entries are retained — the preprint does acknowledge them — but the attribution boundary is now explicit.

**`funders[0].notes` amended (full and core).** Now states that 1OT2OD032742-01 "is the funding recorded on the June 2026 Dataverse release itself", distinguishing it from the two project-level entries.

### 2.9 Minor

**`keywords`: "Medicine, Health and Life Sciences" removed (full and core).** This is the Dataverse Subject field value, not a keyword.

**`publisher` changed (full and core).** The constructed base URL `https://dataverse.lib.virginia.edu` has been replaced with the dataset URL the bundle actually states.

**`description` shortened (full and core).** The closing sentence about RO-Crate packaging with provenance graphs via FAIRSCAPE was lifted from the March 2025 description and the preprint's project-level account; the June 2026 description does not contain it. Removed from `description`. `conforms_to: RO-Crate` and `conforms_to_standard: [RO_CRATE]` are retained, as the packaging format is attested project-wide.

**`source_caveats`: author-count clause removed (full and core).** "Sources also disagree on the number of authors and…" asserted a disagreement the caveat never substantiated. The Sali affiliation conflict, which it did substantiate, is retained and now carries tier labels.

**`distribution_dates[0].release_dates` and `external_resources[].external_resources` (full and core).** Both are multivalued in the schema; each scalar string has been wrapped in a single-element list. Not an audit finding, but a shape correction made while editing.

---

## 3. What was left as-is, and why

Nothing in the audit was rejected outright — the two findings marked as supported omissions were both acted on, and every other finding produced some change. Two points are worth recording as deliberate non-changes within changed slots:

- **The 464 figure itself is unchanged.** Only its provenance statement was corrected. The October 2025 release is tier 1 and states 464; the ranking still selects it.
- **The 21.4 TB project-level volume figure is retained in `source_caveats` alongside the derived release total.** The audit did not question it, and recording both without resolving the disagreement is the correct treatment for a figure about the project rather than the release.

---

## 4. Referent consistency

Both records name the same referent throughout: the June 2026 release, `doi:10.18130/V3/HIGT4C`, version 2.0, issued 2026-06-17. The four earlier releases are represented only through `related_datasets`, each with its own DOI and an `is_new_version_of` relationship. The three publications and the U2OS Nature dataset appear only there as well. No fact about another version or another dataset is now stated in a slot of the referent's own, with the single deliberate exception of the immunofluorescence collection's `source_caveats`, which exists precisely to mark the boundary it describes.

---

## Dispositions

| slot | disposition | record | reason |
|---|---|---|---|
| `instances[*].instance_details` | removed | both | Not a declared `Instance` slot in the schema digest; content moved to `notes` on all three objects. |
| `instances[*].notes` | added | both | Declared home for the prose formerly in `instance_details`. |
| `total_size_bytes` | changed | full | Corrected from 12601604198 to 12601718300 to equal the record's own per-file and per-collection byte sums. |
| `source_caveats` | changed | both | Corrected 464-count provenance (October 2025 tier 1, not June 2026); added statement that the derived total equals the recorded inputs; added IF-archive checksum divergence note; removed unsubstantiated author-count clause; added tier labels to the Sali affiliation conflict. |
| `creators[3].name` | changed | both | "Ulrika Axelsson" reduced to "Axelsson U"; given name not in the bundle. |
| `creators[20].name` | changed | both | "Christian Metallo" reduced to "Metallo C"; given name not in the bundle. |
| `creators[33].name` | changed | both | Diacritic restored: "Bélisle-Pipon". |
| `creators[].affiliations[].id` | added | both | `ROR:0153tk833` added to the five University of Virginia affiliations, as stated on the June 2026 release page. |
| `creators[46].principal_investigator.orcid` | changed | both | Bare identifier rather than `ORCID:`-prefixed form; `id` retains the CURIE. |
| `citation` | changed | full | Diacritic restored in "Bélisle-Pipon" within the verbatim Dataverse citation. |
| `file_collections[#collection-ifimages].description` | changed | full | Reduced to what the June 2026 listing supports; October 2025 image-set facts moved out. |
| `file_collections[#collection-ifimages].source_caveats` | added | full | Records the October 2025 description and the checksum divergence showing the archives are not the same files. |
| `distributions[3].description` | changed | core | Same correction as the full record's IF collection description. |
| `distributions[3].source_caveats` | added | core | Same caveat as the full record's IF collection. |
| `preprocessing_strategies` | removed | both | MuSIC stages produce computed cell maps the release states are not included; restated in `notes` as project tooling. |
| `labeling_strategies` | removed | both | Same reason; annotation applies to cell maps absent from this release. |
| `machine_annotation_tools` | removed | both | Same reason; also carried "DenseNet-121", drawn from the Nature U2OS paper describing a different dataset. |
| `notes` | changed | both | Now carries the MuSIC pipeline description with an explicit qualifier that these stages describe project tooling and planned future releases, using the preprint's own "Human Protein Atlas deep learning model" wording. |
| `tasks[3]` | changed | both | Cell-map construction replaced with bioinformatics analysis of the individual datasets, which is what the release states it supports. |
| `prohibited_uses[0].prohibition_reason` | changed | both | Now states the reason; the prohibition itself moved to `notes`. |
| `prohibited_uses[0].notes` | added | both | Holds the prohibited use formerly in `prohibition_reason`. |
| `data_governance.committee_name` | changed | both | Constructed "CM4AI Data Access Committee" replaced with the attested field label "Data Governance Committee". |
| `data_governance.access_review_process` | changed | both | Preprint's future tense restored; the supervisory role is stated as a plan. |
| `data_governance.source_caveats` | added | both | Records the label discrepancy and the tense of the preprint's statement. |
| `data_governance.committee_contact.orcid` | changed | both | Bare identifier rather than `ORCID:`-prefixed form. |
| `related_datasets[].target_dataset` | changed | both | All seven converted from doi.org resolver URLs to `doi:` CURIEs, matching `version_access.latest_version_doi`. |
| `related_datasets[6].notes` | changed | both | "produced with the same AP-MS plus immunofluorescence integration approach" reworded to describe the U2OS dataset's own method without implying shared processing. |
| `errata` | added | both | June 2025 release documents RGB image addition, RO-Crate metadata corrections and naming-convention changes. |
| `license_and_use_terms.contact_person` | removed | both | No source names Ideker as licensing contact; the commercial-licence route is now stated in `license_terms`. |
| `license_and_use_terms.license_terms` | changed | both | Commercial-licence negotiation route folded in from the removed contact. |
| `maintainers[2].maintainer_details` | changed | both | Ideker's email added where the bundle attests it as the Point of Contact. |
| `funders[0].notes` | changed | both | States that this award is the funding recorded on the release itself. |
| `funders[1].notes` | changed | both | States this is project-level preprint acknowledgement, not funding the release listing attributes to itself. |
| `funders[2].notes` | changed | both | Same correction. |
| `keywords` | changed | both | "Medicine, Health and Life Sciences" removed as a Dataverse Subject value rather than a keyword. |
| `publisher` | changed | both | Constructed base URL replaced with the dataset URL the bundle states. |
| `description` | changed | both | RO-Crate/FAIRSCAPE sentence removed; it belongs to the March 2025 description and the preprint's project-level account, not the June 2026 release. |
| `distribution_dates[0].release_dates` | changed | both | Wrapped as a single-element list to match the multivalued declaration. |
| `external_resources[].external_resources` | changed | both | Each wrapped as a single-element list to match the multivalued declaration. |
| `ethical_reviews[].contact_person.orcid` | changed | both | Bare identifiers rather than `ORCID:`-prefixed form. |
| `ethical_reviews[1].contact_person.name` | changed | both | Diacritic restored: "Bélisle-Pipon". |
| `conforms_to` | retained | both | RO-Crate packaging is attested project-wide; only the sentence in `description` was version-specific. |
| `conforms_to_standard` | retained | both | Same reason. |