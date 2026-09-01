# CM4AI Reconciliation Report

**Project:** CM4AI (Bridge2AI Functional Genomics Grand Challenge)
**Records:** full (`Dataset`) and core (`CoreDataset`)
**Referent:** Cell Maps for Artificial Intelligence — June 2026 Data Release (Beta), DOI `10.18130/V3/HIGT4C`
**Phase:** 4 — strict reconciliation of the Phase 3 audit findings

---

## 1. Audit summary

The Phase 3 audit returned **19 findings** against the full record: 1 high, 8 medium, 10 low. The core record was audited as a projection and produced no findings of its own; every core change below follows mechanically from the corresponding full-record change.

The audit did not challenge the record's referent choice (the June 2026 release rather than the U2OS dataset reported in the Nature paper), and confirmed that the ROR and ORCID CURIEs in `creators` are traceable to identifiers the bundle states.

---

## 2. Findings resolved by change

### 2.1 `publisher` held the dataset's own DOI (high)

**Was:** `publisher: doi:10.18130/V3/HIGT4C`
**Now:** `publisher: https://dataverse.lib.virginia.edu/`

The slot asks for the organization responsible for making the resource available; the old value made the dataset its own publisher. The bundle attests the University of Virginia Dataverse throughout — the release page is served from `dataverse.lib.virginia.edu`, the citation ends "University of Virginia Dataverse, V2", and the preprint describes LibraData as "the University of Virginia's instance of Dataverse, an NIH-approved generalist repository." No ROR or other registry identifier for the repository appears in the bundle, so under the v5 rule (an identifier naming something outside the dataset must come from the evidence) the repository URL is used rather than a minted or recalled CURIE. Applied identically in both records.

### 2.2 `id` written as resolver URL while siblings used the `doi:` CURIE (medium)

**Was:** `id: https://doi.org/10.18130/V3/HIGT4C`
**Now:** `id: doi:10.18130/V3/HIGT4C`

`id` is `uriorcurie`, a `doi:` prefix is in use elsewhere in the same record (`version_access.latest_version_doi`, all four `related_datasets.target_dataset` values), and the same dataset appearing in two identifier forms produces two identities. Changed in both records.

Consequentially, every minted fragment identifier was rebased onto the CURIE so that labels remain traceable to the attested identifier in its canonical form:

- nine `subsets[].id` values, e.g. `https://doi.org/10.18130/V3/HIGT4C#ifimages-untreated` → `doi:10.18130/V3/HIGT4C#ifimages-untreated`;
- ten `file_collections[].id` values, e.g. `…#file-apms-paclitaxel`;
- the same ten identifiers as they appear in the core record's `distributions[].id`.

The `doi` slot itself (`string`, anchored pattern) keeps the bare form `10.18130/V3/HIGT4C` in both records, and the `page` and `distribution_formats[].access_urls` values keep their URL forms — `access_urls` is declared `uri`, and `page` is a landing page. The resolver URL inside `citation` was left untouched as quoted text.

### 2.3 De-accented surname in `creators` and in the verbatim citation (medium)

**Was:** `Belisle-Pipon JC` in `creators`, inside `citation`, in `data_governance.stewardship_roles`, in `human_subject_research.ethics_review_board`, and as an `ethical_reviews` contact name.
**Now:** `Bélisle-Pipon JC` / `Jean-Christophe Bélisle-Pipon` in all of those positions, in both records.

The bundle spells the name with the acute accent in every Dataverse release and in the preprint. The American-English rule governs composed prose, not proper nouns or quoted material — and `citation` reproduces the release's own styled citation, so altering a name inside it was a transcription error. The record was also internally inconsistent: the email address `jean-christophe_belisle-pipon@sfu.ca` retained the source form while the name did not. Email addresses are unchanged (they are literal strings, not names).

### 2.4 `data_governance.committee_name` conflated two bodies (medium)

**Was:** `committee_name: Data Access Committee`, with `access_review_process` opening "A Data Access Committee supervises ethical matters related to dataset distribution and potential dual licensing for commercial use."
**Now:** `committee_name: Data Governance Committee`; `access_review_process` reduced to the commercial-licensing sentence, which the release itself supports; a new `source_caveats` on the `DataGovernance` object records the conflict.

The tier-1 June 2026 release states "Data Governance Committee: Jillian Parker (jillianparker@health.ucsd.edu)"; the tier-3 preprint separately states that "A Data Access Committee will supervise ethical matters related to dataset distribution and potential dual licensing for commercial use." The higher-ranked source's name is used, the disagreement and the preferred value are recorded in the caveat, and the record no longer asserts that the named contact belongs to the preprint's committee. Applied identically in the core record.

### 2.5 MuSIC pipeline attributed as processing applied to this release (medium)

**Removed from both records:** `preprocessing_strategies` (4 objects), `labeling_strategies` (1 object), `machine_annotation_tools` (1 object).

All three slots described node2vec PPI embedding, HPA image embedding, contrastive co-embedding, community detection, GO/Reactome alignment and LLM assembly naming — the pipeline that produces cell maps. The same record states twice, in `known_limitations` and in `source_caveats`, that computed cell maps are **not** included in this release. Attributing those steps to this release's data was a scope error. The pipeline remains described in the record where it is defensible: as a task the dataset supports (`tasks`), as an integrative-modeling activity (`other_tasks`), as tooling (`external_resources`, `extension_mechanism`), and now explicitly in `source_caveats`, which states that these steps "have not been recorded as preprocessing, labeling or machine-annotation applied to this release, because the release itself states that computed cell maps are not included in it."

### 2.6 `use_repository` held production counters, not use tracking (medium)

**Removed from both records:** the single `use_repository` object.

`UseRepository` is declared for repositories or registries tracking how a dataset has been used. The object pointed at the CM4AI data-releases page and carried project-wide production volumes (1,374 protein interactions, 53,788 immunofluorescent images, 7,023 proteins investigated, 11,739 genes targeted, 21.4 TB). Those are output figures, not use tracking, and the page is a release listing. The figures were not discarded: they are now recited in `source_caveats`, where they sit alongside the note that they are project-wide aggregates conflicting with the per-release protein counts, and are explicitly not asserted as properties of this release. This also resolves finding 2.15 below (the duplicate portal reference).

### 2.7 `total_bytes` carried false precision and was applied inconsistently (medium)

**Was:** seven of ten `file_collections` entries carried `total_bytes` converted decimally from Dataverse's rounded display (113.3 KB → 113300, 1.1 MB → 1100000, and so on); the three IF archives instead carried `notes: Reported size 3.8 GB` and no byte count.
**Now:** `total_bytes` removed from all ten entries in the full record and `bytes` removed from all ten in the core record. Every entry carries a uniform `notes` of the form `Dataverse reports the file size as <size>; MD5 <checksum>.`

The bundle attests no exact byte counts; Dataverse displays binary-prefix sizes; the conversions asserted digits the evidence does not contain. Handling is now uniform across all ten files, the displayed sizes are preserved as reported values, and the MD5 checksums — which the bundle does state exactly for every file — have been added, giving the entries verifiable content where the byte counts gave them false precision. `source_caveats` records that file sizes are as Dataverse displays them rather than exact byte counts.

### 2.8 `ethical_reviews[1].review_details` restated the field label (medium)

**Was:** a second `EthicalReview` object whose `review_details` read "Ethical review contact for the data release."
**Now:** that object is removed; Jean-Christophe Bélisle-Pipon is named within the surviving object's `review_details`, which now ends "The June 2026 release names Vardit Ravitsky (ravitskyv@thehastingscenter.org) and Jean-Christophe Bélisle-Pipon (jean-christophe_belisle-pipon@sfu.ca) as the ethical review contacts."

The release names both people together in a single "Ethical Review:" field, so one review record is the correct shape. The `EthicalReview` class declares a single `contact_person`, so the second name is carried in prose rather than dropped; it also remains in `human_subject_research.ethics_review_board` and `data_governance.stewardship_roles`. Applied identically in the core record, which now carries one `ethical_reviews` entry.

### 2.9 Trey Ideker nested as his own principal investigator (medium)

**Was:** the final `Creator` object carried `id: ORCID:0000-0002-1708-8454` / `name: Ideker T` **and** a nested `principal_investigator` Person with the identical ORCID under the name "Trey Ideker".
**Now:** the nested `principal_investigator` is removed; the creator carries a `notes` reading "NIH RePORTER lists Trey Ideker as principal investigator of the CM4AI Data Generation Project (core project OT2OD032742), and the Dataverse release names him as the point of contact for the dataset."

One ORCID bound to two name strings in adjacent values, in a self-referential structure, produced two identities for one person. The PI role is attested and is preserved as prose on the creator it belongs to. `license_and_use_terms.contact_person` still names Trey Ideker without an ORCID — that is a separate contact role attested by the release's "Point of Contact" field, and it is not an identifier claim. Applied identically in the core record.

### 2.10 `language: en` unattested (low)

**Removed from both records.** The bundle nowhere states the language. The inference is safe but is still an assertion the evidence does not carry, and the evidence boundary prefers omission.

### 2.11 `related_datasets` flattened the version chain (low)

**Was:** all three prior releases typed `is_new_version_of`.
**Now:** the October 2025 release retains `is_new_version_of` with a note that the manifest marks it superseded by this release; the June 2025 and March 2025 releases are retyped `is_version_of`, each with a note reading "Earlier release in the CM4AI quarterly data release series."

Only October 2025 is the immediate predecessor. The bundle presents the releases as a quarterly sequence, not as three parallel direct-predecessor relationships. Applied identically in the core record.

### 2.12 `grant_number` not confirmable in the schema digest (low)

**Was:** `funders[0].grants[0]` carried `grant_number: 1OT2OD032742-01` alongside `name` and `id`.
**Now:** the `grant_number` key is removed; the award number is folded into the grant's `name`, which reads "Bridge2AI: Cell Maps for AI (CM4AI) Data Generation Project, NIH award 1OT2OD032742-01".

The supplied digest declares `Grant` only as the range of `FundingMechanism.grants` and does not enumerate its slots, so `grant_number` could not be confirmed as declared. Rather than risk a validation failure on an unverifiable key, the well-attested award number is preserved in a slot that is certain. The `id` (the NIH RePORTER project URL) and the `notes` recording the RePORTER details are unchanged. Applied identically in the core record.

### 2.13 Substantive description carried in `notes` (low)

**Was:** `notes` carried the pillar/module organization, the nine-institution collaborator list, and the Dataverse "under review" notice.
**Now:** the pillar/module structure and the collaborator list are appended to `description`; `notes` retains only the Dataverse and portal "under review for potential modification in compliance with Administration directives" notice, which is genuinely residual.

Per #385, `notes` is for what `description` cannot hold. Applied identically in the core record.

### 2.14 Vacuous `content_warnings` object (low)

**Removed from both records:** the single object carrying only `content_warnings_present: false`.

The bundle makes no statement about content warnings in either direction. A negative assertion on a topic the sources never address conveys nothing that omitting the slot does not.

### 2.15 Portal resource duplicated across two slots (low)

Resolved by 2.6. The CM4AI portal is now described once, in `external_resources`; the `use_repository` entry that also pointed at it is gone.

### 2.16 `data_governance.accountable_organization` empty though supported (low)

**Added to both records:** an `Organization` under `accountable_organization` whose `name` reads "The Regents of the University of California, holding copyright to these datasets except where otherwise indicated, with raw spatial proteomics image data held by The Board of Trustees of the Leland Stanford Junior University."

Both copyright holders are stated in the release and the preprint. The information previously appeared only as prose inside `ip_restrictions`, which remains unchanged — that slot records the restriction; this one records who is accountable. No registry identifier for either institution appears in the bundle, so the object carries `name` only.

### 2.17 `was_derived_from` omitted though supported (low)

**Added to both records:** `was_derived_from: doi:10.18130/V3/K7TGEM`.

The June 2026 release extends the October 2025 release — same DOI family, same file set with AP-MS additions — a relationship previously expressed only through `related_datasets`. The slot is declared `string`, so it carries the predecessor's identifier rather than an object.

### 2.18 `last_updated_on` inferred without a caveat (low)

The value `2026-07-15T00:00:00Z` is **unchanged**; a sentence was added to `source_caveats`: "`last_updated_on` is taken from the publication date of the three immunofluorescence archives (2026-07-15), the latest file date on the release; no dataset-level modification date is stated."

The date is the most recent file publication date the bundle gives for this release and is the best-supported answer available. The audit's objection was to the absence of disclosure, not to the value, so the value stands and the basis is now recorded.

---

## 3. Findings left as-is

### 3.1 `sensitive_elements[0].sensitive_elements_present: false` (low)

**Unchanged in both records.** The audit is right that the bundle addresses human-subject status rather than sensitive elements as such. But unlike `content_warnings` (2.14), this object carries substantive `sensitivity_details` grounded directly in the release's governance block — "Human Subjects: No", "De-identified Samples: Yes" — and the boolean is a short, well-signposted step from those statements about laboratory data derived from commercially available de-identified cell lines. The details field states the basis explicitly, so a reader can see what the boolean rests on. Removing the boolean while keeping the details would leave an object less informative than the evidence supports.

---

## 4. Referent

Unchanged and consistently held across both records: the **June 2026 Data Release (Beta)**, DOI `10.18130/V3/HIGT4C`, the tier-1 source that the manifest marks as superseding the October 2025 release. The U2OS osteosarcoma cell map reported in the Nature paper (Schaffer et al. 2025) is a distinct resource — different cell line, different repositories (NDEx, MassIVE `MSV000097168`, ProteomeXchange `PXD052362`, HPA v23) — and its content has not been merged. `source_caveats` states this explicitly in both records, and the Phase 4 additions to that field strengthen the boundary by recording why the Nature paper's pipeline description is not used to populate this record's processing slots.

---

## 5. Validation

| | Full | Core |
|---|---|---|
| Schema | `data_sheets_schema_all.yaml`, class `Dataset` | `data_sheets_schema_core_all.yaml`, class `CoreDataset` |
| Result | valid | valid |

The core record's header carries `# Phase 4 reconciliation: completed` and the required `# Sources:` line pointing at the full record it was projected from.

---

## 6. Outcome

**Reconciled.** Eighteen of nineteen findings were resolved by change; one (3.1) was examined and deliberately retained with the reasoning recorded above. Six slots were removed entirely from both records (`preprocessing_strategies`, `labeling_strategies`, `machine_annotation_tools`, `use_repository`, `content_warnings`, `language`); two were added (`was_derived_from`, `data_governance.accountable_organization`); the remainder were corrected in place. No fact was introduced that the declared bundle does not state, and every value the audit found unsupported was either removed or given an explicit basis in `source_caveats`.