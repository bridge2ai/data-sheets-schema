# Phase 4 Reconciliation Report — CM4AI

## Scope

The audit returned nineteen findings against the full record: two high, six medium, eleven low. Each was assessed against the declared input bundle and the schema digest. Fifteen produced changes to the full record; where the changed slot is declared in the core schema, the same change was projected into the core record. Four findings were left as-is with reasons given below.

---

## High-severity findings

### 1. `instances[*].instance_details` — undeclared key (changed, both)

The schema digest lists the accepted keys for `Instance` as `counts`, `data_substrate`, `data_topic`, `instance_type`, `label`, `label_description`, `missing_information`, `notes`, `sampling_strategies`, `source_caveats`. `instance_details` is not among them. All three Instance objects carried it in both records.

**Change:** in every Instance object in both records, the key `instance_details` was renamed to `notes`, retaining the prose. The image-instance note additionally now attributes the channel description to the October 2025 release, since that is where the bundle states it (see finding 5).

### 2. `total_size_bytes` — arithmetic inconsistency (changed, full)

The record's own `file_collections[].total_bytes` values (249,100 + 12,600,000,000 + 265,700 + 103,500 + 1,100,000) sum to 12,601,718,300, as do the ten `File.bytes` values. The stated `total_size_bytes` was 12,601,604,198 — a discrepancy of 114,102 bytes reachable by no stated conversion.

**Change:** `total_size_bytes` was corrected to `12601718300`. The `source_caveats` text was extended to state that the figure equals the sum of the per-file `bytes` and per-collection `total_bytes` values recorded in the record, so the arithmetic is now checkable from within the record. `total_size_bytes` is not declared in the core schema, so this change is full-record only; the core record's per-distribution `bytes` values were already consistent and are unchanged.

---

## Medium-severity findings

### 3. Given names not in the bundle — Axelsson, Metallo (changed, both)

The bundle attests only `Axelsson U (KTH Royal Institute of Technology,)` and `Metallo C (University of California San Diego)`. Neither "Ulrika" nor "Christian" appears anywhere in the bundle; both were supplied from outside it. Every other expanded given name in the roster (Timothy Clark, Jillian Parker, Sadnan Al Manir, Amir Dailamy, Antoine Forget, Kirsten Obernier, and the rest) traces to the bioRxiv preprint author list or the governance contact lines.

**Change:** in both records, `creators[].name` for these two entries was reduced to the attested surname-plus-initial form: `Axelsson U` and `Metallo C`.

### 4. Misattributed provenance for the 464-protein IF count (changed, both)

The original caveat stated that "the June 2025 and June 2026 releases state 464" and that "the higher-ranked June 2026 release value (464) is used". The June 2026 release listing in the bundle carries no per-file descriptions and no protein count at all. The value 464 is attested by the June 2025 release (tier 5) and the October 2025 release (tier 1); the value 563 is attested by the March 2025 release (tier 5).

**Change:** the `source_caveats` in both records now states that the June 2026 listing carries no per-file descriptions and no protein count, that 464 is attested by the June 2025 (tier 5) and October 2025 (tier 1) releases, and that the ranking is therefore decided by the October 2025 release, whose value is preferred. The preferred value is unchanged; only the reasoning that names its source was corrected.

### 5. IF collection description imported from a different file set (changed, both)

The June 2026 IF archives carry MD5 checksums `6c1a8652…`, `6d066e6b…`, `df796327…`; the October 2025 archives carry `0d972b80…`, `a98affcc…`, `ad4e68cc…`. They are not the same files. The original description — 464 proteins, DAPI/calreticulin/tubulin channel assignments, Lundberg Lab attribution — is the October 2025 listing's text, stated as a fact about these files.

**Change:** in the full record, `file_collections[#collection-ifimages].description` was reduced to what the June 2026 listing supports (three archives, three treatment conditions), and a `source_caveats` was added to that collection recording the October 2025 description in full, noting the checksum difference, and stating that the description is not carried over. The core record's corresponding `distributions` entry received the same reduced description and the same `source_caveats`.

### 6. `prohibited_uses[0].prohibition_reason` held the prohibition, not the reason (changed, both)

**Change:** in both records, the prohibited use itself was moved to `notes` on the ProhibitedUse object, and `prohibition_reason` now states why the use is forbidden: the absence of the regulatory oversight and approval that clinical decision-making requires, together with the release's own records that the data are not FDA regulated and derive from laboratory cell lines.

### 7. MuSIC pipeline stages stated as preprocessing of this release (changed, both)

The release states plainly that "Computed cell maps not included in this release". The node2vec embedding, HPA image embedding, contrastive co-embedding, community detection, GO/Reactome alignment and LLM naming all produce outputs that are absent from the referent. They describe project tooling and planned future releases.

**Change:** `preprocessing_strategies`, `labeling_strategies` and `machine_annotation_tools` were removed from both records. The pipeline is instead described in `notes` on both records, in a form that states what the project's tooling does and then states explicitly that computed cell maps are not in this release, so those stages describe tooling and planned future releases rather than processing applied to the data released here.

### 8. `machine_annotation_tools[0].tools` contained DenseNet-121 (changed, both)

DenseNet-121 is named in the Nature U2OS paper, which describes a different dataset; the CM4AI preprint says only "a Human Protein Atlas deep learning model".

**Change:** the slot was removed from both records as part of finding 7. The `notes` prose that replaces it says "a Human Protein Atlas deep learning model", which is what the CM4AI preprint states; DenseNet-121 does not appear in either reconciled record.

---

## Low-severity findings

### 9. Diacritic stripped from "Bélisle-Pipon" (changed, both)

The Dataverse citation and the preprint both write `Bélisle-Pipon`. American-English orthography governs composed prose, not quoted text or proper nouns.

**Change:** the diacritic was restored in the verbatim `citation` string (full record), in `creators[].name` (both records), and in `ethical_reviews[1].contact_person.name` (both records).

### 10. Constructed committee name and a plan in the present tense (changed, both)

The release labels the field "Data Governance Committee"; "CM4AI Data Access Committee" was constructed. The preprint says a Data Access Committee "will supervise", not that it does.

**Change:** in both records, `data_governance.committee_name` is now `Data Governance Committee`; `access_review_process` now attributes the supervisory role to the preprint in the future tense as a plan; and a `source_caveats` was added to the DataGovernance object recording both points.

### 11. Resolver URLs in `related_datasets[].target_dataset` (changed, both)

All six (in fact seven) targets were doi.org resolver URLs while `version_access.latest_version_doi` correctly used the CURIE form.

**Change:** all seven `target_dataset` values in both records were converted to `doi:` CURIEs, matching the form used elsewhere in the records.

### 12. ROR identifier supplied by the bundle but unused (added, both)

The June 2026 release page states `https://ror.org/0153tk833` for the University of Virginia affiliations.

**Change:** `id: ROR:0153tk833` was added to the University of Virginia `Organization` objects for Clark, Al Manir, Levinson, Niestroy and Ratcliffe in both records. No other organization carries a registry identifier in the bundle, and none was supplied. The `source_caveats` sentence about registry identifiers was amended accordingly.

### 13. RO-Crate/FAIRSCAPE sentence in `description` (changed, both)

The closing sentence is from the March 2025 release description and the preprint's project-level account; the June 2026 release description does not contain it.

**Change:** the sentence was removed from `description` in both records. The `conforms_to: RO-Crate` and `conforms_to_standard: [RO_CRATE]` slots are retained, since RO-Crate packaging is attested for CM4AI outputs across multiple sources.

### 14. Subject term in `keywords` (changed, both)

`Medicine, Health and Life Sciences` is the Dataverse Subject field value, not a keyword.

**Change:** removed from the `keywords` list in both records. The remaining 29 keywords are exactly the release's Keyword list.

### 15. Unsubstantiated author-count clause in `source_caveats` (changed, both)

The clause "Sources also disagree on the number of authors and the affiliation of one author" asserted an author-count disagreement that was never quantified.

**Change:** the clause now reads "Sources also disagree on the affiliation of one author", and the Sali affiliation conflict is described as before with tier labels added.

### 16. Constructed `publisher` base URL (changed, both)

`https://dataverse.lib.virginia.edu` is a bare host not attested as the publisher's identifier.

**Change:** in both records, `publisher` now carries the dataset-level Dataverse URL the bundle supplies. This is the closest attested URI; the publisher's name, "University of Virginia Dataverse", appears in the `citation` and in `retention_limit`.

### 17. `license_and_use_terms.contact_person` (removed, both)

No source names Trey Ideker as the licensing contact. The bundle routes commercial-licence questions to the copyright-holding institutions and access questions to the governance contact.

**Change:** `contact_person` was removed from `license_and_use_terms` in both records. The commercial-licensing route (separate negotiation with UCSD, Stanford and/or UCSF) was folded into `license_terms`, where the bundle states it. Ideker's email is retained in `maintainers`, where the bundle attests him as the release's Point of Contact.

### 18. Project-level funders attributed to this release (changed, both)

**Change:** the two funders retained as `funders` entries. Their `notes` now state that these awards are acknowledged in the preprint as funding the work described there, that the Dataverse release listing records only 1OT2OD032742-01 as its own funding, and that they are recorded as project-level funding rather than as funding attributed to this release. The first funder's `notes` also now states that 1OT2OD032742-01 is the funding recorded on the release itself.

### 19. `errata` — supported omission (added, both)

The June 2025 release states it was a revision that added RGB immunofluorescent images, made "corrections to ro-crate metadata", and changed naming conventions.

**Change:** an `errata` list with one `Erratum` object was added to both records, carrying `erratum_details` and an `erratum_url` pointing at the June 2025 release page.

---

## Findings left as-is

**Finding 8's tool list — partially.** The audit flagged DenseNet-121 specifically. The reconciliation removed the whole slot rather than the one entry, because finding 7 established that the annotation tooling describes work not applied to this release. The narrower repair was not taken.

**`related_datasets` relationship types.** The audit did not question them and they were not changed. `is_new_version_of` is used for all four prior CM4AI releases including the May 2024 one, which is a defensible reading of a quarterly release series.

**`tasks[3]`.** The original fourth task described cell-map construction via self-supervised embedding and community detection. This is the same problem as finding 7 — a task the pipeline performs, not one this release supports — and although the audit did not raise it, it was changed for consistency with finding 7: it now states bioinformatics analysis of the individual modality datasets, which the release names as what the current release is most suitable for. This is a change beyond the audit's findings and is recorded here for that reason.

**`conforms_to: RO-Crate`.** Retained in both records despite finding 13's removal of the RO-Crate sentence from `description`. RO-Crate packaging of CM4AI outputs is attested by the preprint, by the March 2025 release description, and by the presence of `ro-crate-metadata.json` files in the March 2025 and June 2025 release file listings.

---

## Dispositions

| slot | disposition | record | reason |
|---|---|---|---|
| `instances[0].instance_details` | removed | both | Not a declared `Instance` key in the schema digest; prose moved to `notes`. |
| `instances[1].instance_details` | removed | both | Same. |
| `instances[2].instance_details` | removed | both | Same. |
| `instances[0].notes` | added | both | Receives the image-instance prose, with the October 2025 attribution added. |
| `instances[1].notes` | added | both | Receives the PPI-instance prose. |
| `instances[2].notes` | added | both | Receives the perturb-seq-instance prose. |
| `total_size_bytes` | changed | full | Corrected to 12,601,718,300 to equal the record's own per-file and per-collection sums. |
| `source_caveats` | changed | both | Arithmetic statement corrected; 464-protein provenance corrected to name the October 2025 release; IF-checksum note added; author-count clause dropped; registry-identifier sentence amended for the ROR. |
| `creators[3].name` | changed | both | "Ulrika Axelsson" reduced to attested `Axelsson U`. |
| `creators[20].name` | changed | both | "Christian Metallo" reduced to attested `Metallo C`. |
| `creators[33].name` | changed | both | Diacritic restored: `Jean-Christophe Bélisle-Pipon`. |
| `creators[0].affiliations[0].id` | added | both | ROR:0153tk833, stated by the June 2026 release page. |
| `creators[2].affiliations[0].id` | added | both | Same. |
| `creators[18].affiliations[0].id` | added | both | Same. |
| `creators[23].affiliations[0].id` | added | both | Same. |
| `creators[42].affiliations[0].id` | added | both | Same. |
| `citation` | changed | full | Diacritic restored in quoted citation string. |
| `keywords` | changed | both | Dataverse Subject value removed from the keyword list. |
| `description` | changed | both | RO-Crate/FAIRSCAPE sentence removed as not stated by the June 2026 release description. |
| `publisher` | changed | both | Bare host replaced by the dataset-level Dataverse URL the bundle supplies. |
| `file_collections[1].description` | changed | full | Reduced to what the June 2026 listing supports. |
| `file_collections[1].source_caveats` | added | full | Records the October 2025 description, the checksum difference, and that it is not carried over. |
| `distributions[3].description` | changed | core | Same reduction as the full record's IF collection. |
| `distributions[3].source_caveats` | added | core | Same caveat as the full record's IF collection. |
| `prohibited_uses[0].prohibition_reason` | changed | both | Now states the reason; the prohibition itself moved to `notes`. |
| `prohibited_uses[0].notes` | added | both | Carries the prohibited use. |
| `preprocessing_strategies` | removed | both | Describes pipeline stages producing outputs absent from this release. |
| `labeling_strategies` | removed | both | Same. |
| `machine_annotation_tools` | removed | both | Same; also carried DenseNet-121, attested only for the Nature U2OS dataset. |
| `notes` | changed | both | Now describes the MuSIC pipeline as project tooling and states that computed cell maps are not in this release. |
| `tasks[3]` | changed | both | Cell-map construction replaced by bioinformatics analysis of the individual datasets, consistent with the release's own statement. |
| `data_governance.committee_name` | changed | both | Constructed name replaced by the release's field label. |
| `data_governance.access_review_process` | changed | both | Preprint's future-tense plan no longer rendered as present practice. |
| `data_governance.source_caveats` | added | both | Records the naming and tense points. |
| `license_and_use_terms.contact_person` | removed | both | No source names Ideker as the licensing contact. |
| `license_and_use_terms.license_terms` | changed | both | Absorbs the commercial-negotiation route the bundle states. |
| `related_datasets[0].target_dataset` | changed | both | Resolver URL converted to `doi:` CURIE. |
| `related_datasets[1].target_dataset` | changed | both | Same. |
| `related_datasets[2].target_dataset` | changed | both | Same. |
| `related_datasets[3].target_dataset` | changed | both | Same. |
| `related_datasets[4].target_dataset` | changed | both | Same. |
| `related_datasets[5].target_dataset` | changed | both | Same. |
| `related_datasets[6].target_dataset` | changed | both | Same. |
| `related_datasets[6].notes` | changed | both | "the same AP-MS plus immunofluorescence integration approach" reworded to state the method without asserting identity with this release's approach. |
| `ethical_reviews[1].contact_person.name` | changed | both | Diacritic restored. |
| `funders[0].notes` | changed | both | States that this award is the funding recorded on the release itself. |
| `funders[1].notes` | changed | both | Marked as project-level funding acknowledged in the preprint, not release funding. |
| `funders[2].notes` | changed | both | Same. |
| `errata` | added | both | June 2025 release's documented corrections, which Erratum is the declared home for. |
| `maintainers[2].maintainer_details` | changed | both | Ideker's email added here, where the bundle attests him as Point of Contact. |
| `conforms_to` | retained | both | RO-Crate packaging attested by preprint and by ro-crate-metadata.json files in prior release listings. |
| `conforms_to_standard` | retained | both | Same. |
| `related_datasets[0].relationship_type` | retained | both | Not questioned by the audit; `is_new_version_of` is a defensible reading of the release series. |