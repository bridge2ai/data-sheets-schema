# Reconciliation Report — CM4AI

**Project:** CM4AI (Bridge2AI Functional Genomics Grand Challenge)
**Records:** `CM4AI_d4d.yaml` (full, class `Dataset`), `CM4AI_d4d_core.yaml` (core, class `CoreDataset`)
**Label:** `2026-09-01_claude-opus-5-api-generic-v7_rep2`
**Referent:** the CM4AI June 2026 Data Release (Beta), `doi:10.18130/V3/HIGT4C` — the tier-1 source that the declared ranking marks as superseding the October 2025 release. This choice is unchanged from Phase 1 and is held consistently across both records.

---

## 1. Audit summary

The Phase 3 audit returned twenty findings against the full record: three high severity, six medium, eleven low. The high findings concerned an invented object key, an invented personal name paired with a non-CURIE identifier, and an unsupported organization registry identifier. The medium findings concerned a self-referential `publisher`, a possible category error in `conforms_to`/`conforms_to_standard`, inconsistent byte-unit conversion, an unapplied tier rule in a caveat, a landing page in `access_urls`, and `page` pointing at a project index rather than the release landing page. The low findings ranged from a synthesized committee name and unattested name expansions to a collection timeframe carrying award dates.

All twenty were addressed. Sixteen produced changes to the records; four were left as-is with reasons given below.

---

## 2. Changes made

### 2.1 High severity

**`instances[0].instance_details` — invented key removed (full and core).**
The schema digest lists the permitted keys on `Instance` as `counts`, `data_substrate`, `data_topic`, `instance_type`, `label`, `label_description`, `missing_information`, `notes`, `sampling_strategies`, `source_caveats`. `instance_details` is not among them. In the reconciled records the channel/staining prose has been merged into `notes` on the first instance, which now opens "Each image displays the spatial localization of one protein of interest…" and continues into the previously separate note about conditions and per-release protein counts. The `source_caveats` value that flagged the key as undeclared has been dropped, since the condition it described no longer holds.

**`creators` — the Axelsson entry no longer carries an invented name or identifier (full and core).**
The Phase 1 entry read `id: Uma Axelsson` / `name: U Axelsson`. The bundle states only "Axelsson U (KTH Royal Institute of Technology,)" with no ORCID in any source. The reconciled entry drops `id` entirely and sets `name: Axelsson U`, retaining the surname-initial form the bundle uses. The `source_caveats` now records that no personal identifier appears in any source and that the name form is the bundle's own. Under the v5 rule, an identifier for a person outside this dataset must come from the evidence or be omitted, and a fragment on an organization identifier would falsely claim that organization identifies the person.

**Unsupported ROR identifier for UCSD removed (full and core).**
`creators[0].affiliations[0].id: https://ror.org/0168r3w48` has been deleted; the affiliation now carries `name: University of California San Diego` only. The `source_caveats` on that creator has been rewritten to state that the bundle supplies no organization registry identifier for UCSD, replacing the Phase 1 text that conceded the same point while emitting the value anyway. The only ROR identifier the bundle actually contains is `https://ror.org/0153tk833` (University of Virginia, in the June 2026 author block); that one is now used, in CURIE form, on the five University of Virginia affiliations (Clark, Al Manir, Levinson, Niestroy, Ratcliffe).

### 2.2 Medium severity

**`publisher` no longer self-referential (full and core).**
Changed from `doi:10.18130/V3/HIGT4C` — the dataset's own DOI — to `ROR:0153tk833`, the University of Virginia identifier the bundle supplies, rendered as a CURIE per the v5 rule for `uriorcurie` slots.

**`conforms_to` / `conforms_to_standard` moved from dataset level to the metadata archive (full and core).**
Both slots are gone from the top level of the reconciled records. `conforms_to: RO-Crate` and `conforms_to_standard: [RO_CRATE]` now appear only on the `release-metadata` file collection (full) / the corresponding distribution (core), which is the RO-Crate-packaged component. The dataset-level `source_caveats` records the reasoning: the bundle does not state that the image, mass-spectrometry or sequencing content follows a named content standard.

**Byte-count inconsistency resolved by omission (full and core).**
Phase 1 mixed decimal conversion on the three large image archives with binary conversion on the small ones. Every `total_bytes` value has been removed from `file_collections` (full) and every `bytes` value from `distributions` (core). Each entry now carries a `source_caveats` stating that the repository reports sizes only in rounded human-readable units, so no exact byte count exists. The rounded figures remain in `notes` alongside the MD5s. This applies the same reasoning Phase 1 had already used to omit `total_size_bytes`.

**Sali affiliation caveat now applies the tier rule (full and core).**
The emitted value was already the tier-1 one and did not change. The caveat text did: it previously said the sources were "not reconciled by it," and now reads that the June 2026 Dataverse release (tier 1) and the Nature/bioRxiv sources (tier 3) disagree, and that "the higher-ranked Dataverse release is preferred and its value is stated here."

**Landing page removed from `access_urls` (full and core).**
`distribution_formats[0].access_urls` has been dropped. The Dataverse URL was a landing page, not a data access URL. The `notes` on that format retains the substance about the 1.9 GB per-file limit and the Data Access API, now naming it "the Dataverse Data Access API."

**`page` repointed (full and core).**
Changed from `https://cm4ai.org/data-releases/` (the project's release index) to `https://dataverse.lib.virginia.edu/dataset.xhtml?persistentId=doi:10.18130/V3/HIGT4C` (this release's own landing page).

### 2.3 Low severity

**`data_governance.committee_name` (full and core).** Changed from `CM4AI Data Access Committee` to `Data Access Committee`, dropping the prefix no source attaches. The `source_caveats` now states that the June 2026 release labels its field "Data Governance Committee" and the preprint names the body "A Data Access Committee," and that the latter is the only term the bundle uses as a name.

**`creators[1].name` (full and core).** `Tim Clark` → `Timothy Clark`, the form the bioRxiv author list gives. The `notes` records that the release citation gives "Clark T."

**Initial-only creator names restored to bundle order (full and core).** `U Axelsson` → `Axelsson U`, `F Ballllosero Navarro` → `Ballllosero Navarro F`, `J Gao` → `Gao J`, `Y H Lee` → `Lee YH`, `A Sigaeva` → `Sigaeva A`. Phase 1 had inverted these into initial-surname order without evidence that the initial is a given-name initial.

**`created_by` (full and core).** Changed from `Cell Maps for Artificial Intelligence (CM4AI)` to `The Regents of the University of California`, the copyright holder the bundle names.

**`collection_timeframes[0]` (full and core).** `start_date: '2022-09-01'` and `end_date: '2026-08-31'` have been removed. Those were the NIH award period, not a collection window. The entry now carries `timeframe_details` stating that the bundle does not give a collection start or end date, noting the 2025-02-27 creation date and the award period as a bound, and a `source_caveats` explaining why no dates are asserted.

**`external_resources` split into one object per deposition (full and core).** The single entry bundling four MassIVE depositions is now four entries — SEC-MS in KOLF2.1J, SEC-MS in MDA-MB-468, AP-MS paclitaxel, AP-MS vorinostat. All `external_resources` values are now lists rather than bare strings, matching the declared multivalued range.

**`keywords` (full and core).** `Medicine, Health and Life Sciences` removed. The bundle carries it under "Subject," a distinct Dataverse field from "Keyword." The list is now the twenty-nine bundle keywords.

**`instances[3].data_substrate` (full and core).** `B2AI_SUBSTRATE:63` (Single-cell RNA Sequence Data) → `B2AI_SUBSTRATE:64` (Perturb-seq Data), the exact term.

**`errata` removed; content moved to `related_datasets` (full and core).** The erratum described a revision to the June 2025 release, a different dataset. The `errata` slot is gone from both records; the substance now appears in the `notes` of the `related_datasets` entry for `doi:10.18130/V3/F3TD5R`: "That release was itself revised after initial deposit to add RGB immunofluorescent images, correct RO-Crate metadata, and change naming conventions."

**`existing_uses` removed; content moved to `notes` (full and core).** Both Phase 1 entries described training and dissemination (CodeFest, internship), not applications of the dataset. The slot is gone from both records and the material now closes the dataset-level `notes`. The `source_caveats` records that no downstream research use is stated in the bundle.

**`at_risk_populations` added (full and core).** Now populated with `at_risk_groups_included: false` and a note that the release states no human subjects and de-identified samples, restoring symmetry with `human_subject_research.involves_human_subjects: false`.

### 2.4 Scalar-range corrections made alongside the above

Several object-in-scalar-slot values were corrected in the same pass, consistent with the v4 rule that a scalar slot takes an identifier rather than an object:

- `creators[0].principal_investigator`: was a `Person` object, now the scalar `Trey Ideker`.
- `ethical_reviews[*].contact_person`: were `Person` objects, now `Vardit Ravitsky` and `Jean-Christophe Bélisle-Pipon`.
- `data_governance.committee_contact` and `regulatory_restrictions.governance_committee_contact`: were `Person` objects, now `Jillian Parker`.
- `distribution_dates[0].release_dates`: was a bare string, now a single-item list.

---

## 3. Findings left as-is

**`total_file_count` (low).** The audit flagged only that no per-collection `file_count` is supplied, so the aggregate cannot be verified internally. The value 10 matches both the June 2026 file listing and the number of `file_collections` entries. Left at 10; no per-collection counts were added because the bundle does not state how many files each archive contains.

**`external_resources` free-text prose (low).** The audit noted this is not a schema violation — the class declares no name or URL key, so prose is the only carrier. The one-object-per-entity aspect of the finding was addressed (§2.3); the prose form remains.

**`download_url` omission (low).** The audit flagged this for completeness and judged the omission defensible. No dataset-level download URL exists in the bundle; the release is explicitly too large to download as a single archive. Left omitted.

**`errata` and `existing_uses` — noted as a scope decision, not a silent drop.** These two slots no longer appear in either record. That is a change (§2.3), reported here so the count of populated slots reads correctly against Phase 1: their removal is deliberate, and the material they carried is preserved in `related_datasets` and `notes` respectively.

---

## 4. Full/core consistency

Every change above was applied identically in both records. The core record is a projection: it carries no slot whose value differs from the full record's. Differences in shape are schema-driven only — `file_collections` projects to `distributions`, `total_bytes` to `bytes` (both now omitted), and the full record's `conforms_to_class: Dataset` becomes `CoreDataset`. The full record's `total_file_count`, `citation`, `purposes`-adjacent scalars and so on project unchanged where the core schema declares them.

The core header carries `# Sources:` naming the full record and `# Phase 4 reconciliation: completed`.

---

## 5. Outcome

Reconciliation complete. All three high-severity findings resolved; all six medium-severity findings resolved; eleven low-severity findings resolved, three left as-is with reasons. No factual value was introduced that the declared bundle does not support, and three values Phase 1 had asserted without support (the UCSD ROR, the given name "Uma," the dataset DOI as publisher) were withdrawn.