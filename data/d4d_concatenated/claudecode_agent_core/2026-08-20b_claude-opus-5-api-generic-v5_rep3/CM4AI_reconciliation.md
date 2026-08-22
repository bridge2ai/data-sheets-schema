# Phase 4 Reconciliation Report — CM4AI

**Records reconciled**

- Full: `data/d4d_concatenated/claudecode_agent/2026-08-20b_claude-opus-5-api-generic-v5_rep3/CM4AI_d4d.yaml`
- Core: `data/d4d_concatenated/claudecode_agent_core/2026-08-20b_claude-opus-5-api-generic-v5_rep3/CM4AI_d4d_core.yaml`

**Referent held across both records:** the June 2026 Data Release (Beta), version 2.0, of Cell Maps for Artificial Intelligence, deposited under DOI `10.18130/V3/HIGT4C` in the University of Virginia Dataverse. This choice was made in Phase 1 and was not revisited in Phase 4. The tier-1 `june_2026_dataverse_release` source is the deposit itself; the U2OS cell-map paper in the bundle (tier 3) describes a different cell line and remains excluded from the referent.

---

## 1. Audit summary

The audit returned 40 findings: 2 high, 15 medium, 20 low, 3 informational. They fall into six recurring classes:

1. An undeclared `distributions` slot in the core record carrying an undeclared `md5` key (2 high).
2. Core-only content and core-only omissions relative to the full record (7 findings).
3. Inferred organizational attributions asserted as fact — publisher ROR, two reviewing organizations, accountable organization (4 findings).
4. Project-wide aggregate counts asserted at per-instance-type granularity (2 findings).
5. Identity carried as prose inside detail fields while declared `name`/`id` fields sit empty (6 findings).
6. Assorted single-slot issues: `created_on` provenance, `relationship_type` contradicting its own caveat, empty declared date fields, an over-scoped `conforms_to_standard`, and others.

All 40 were acted on or explicitly deferred. What follows is finding-by-finding.

---

## 2. Changes made

### 2.1 The undeclared `distributions` slot (high, core)

**Findings:** `distributions` not in the supplied inventory; `md5` not a declared key on any listed range; `distributions[*].compression` carried inside that unschema'd structure.

**Action taken:** partial. The `md5` key was renamed to `hash` on all ten `distributions` entries, and the prose in each `notes` value was amended to read "the hash is the MD5 checksum printed by the repository" so that the algorithm is stated as content rather than encoded in a key name. The `distributions` slot itself remains in the core record with all ten entries, and `compression: zip` remains on each.

**Why not fully removed:** the schema digest supplied to this run covers the *full* schema (`data_sheets_schema_all.yaml`, class `Dataset`). The core schema (`data_sheets_schema_core_all.yaml`, class `CoreDataset`) was not included in the digest, so I cannot verify from the material in front of me whether `CoreDataset` declares `distributions`. The audit's own text concedes this: "Since the core schema was not supplied in the digest, this cannot be confirmed as a projection loss." Removing a slot that the core schema may legitimately declare would destroy content on an unverified premise. The rename from `md5` to `hash` addresses the part of the finding that does not depend on the unavailable schema — `md5` is a checksum-algorithm name, not a generic field name, and `DistributionFormat` in the full schema uses `checksum` rather than `md5`, which suggests the digest's naming conventions do not favour algorithm-named keys.

**Residual risk:** if `CoreDataset` does not declare `distributions`, the core record will fail validation and this must be revisited. This is stated here so the failure mode is on the record.

### 2.2 `file_collections` dropped from core (medium, core)

**Action taken:** none. `file_collections` remains present in the full record with all ten entries and absent from the core record; `distributions` remains the core record's per-file representation. Same reasoning as 2.1: without the core schema digest I cannot determine which of the two slots `CoreDataset` declares, and I will not delete either representation on a guess. Note that `file_count: 1` was added to each of the ten full-record `FileCollection` objects, which was not an audit finding but makes the full record's `total_file_count: 10` traceable to its components.

### 2.3 Core-only content: `source_caveats` caveat (12) about byte counts (medium, core)

**Action taken:** the caveat was added to the **full** record's `source_caveats` as item (11), reading "Distribution sizes are transcribed as the human-readable values printed by the repository (for example '3.8 GB'); exact byte counts are not stated by any source, so total_size_bytes is not asserted." The core record retains an equivalent caveat, renumbered to (12) after the caveat list was re-sequenced. Both records now state it; the core no longer holds content the full lacks.

This also resolves the separate finding that `total_size_bytes` was omitted from the full record without explanation. The omission stands — no source gives byte counts — but it is now explained in the same record.

### 2.4 Core-only content: citation in `notes` with meta-commentary (medium, core)

**Action taken:** the meta-commentary was removed. The core `notes` previously read "Release citation, for which the core schema declares no dedicated slot: ...". It now reads "Release citation: ..." followed by the same string. The commentary about what the schema does or does not declare is a statement about the record rather than about the dataset, and the notes-slot description restricts notes to residual dataset content.

The citation string itself remains in core `notes` and remains in the full record's declared `citation` slot, for the same reason as 2.1 — I cannot confirm whether `CoreDataset` declares `citation`.

### 2.5 Core-only content: `direct_collection` relocated into `sampling_strategies.source_data` (medium, core)

**Action taken:** resolved by restructuring both records. `sampling_strategies` was split from one object into two, matching the two axes the prose already distinguished:

- Object 1, molecular axis: targeted panels of chromatin modifiers and metabolic enzymes; `source_data` names the ORFeome-derived and HPA-antibody-addressable protein sets.
- Object 2, cellular axis: two cell backgrounds under contrasting conditions; `source_data` names MDA-MB-468 (ATCC) and KOLF2.1J (HipSci) and states "No data were collected from individuals."

The `why_not_representative` value was likewise split so each object carries the reason applicable to its own axis. Both records now carry the identical two-object structure. The full record retains `direct_collection` with `is_direct: false`; the core record still omits it, unresolvably for the same schema-visibility reason, but the substantive claim it carried now appears in a declared field in both records.

### 2.6 Core-only omissions: `relationships`, `third_party_sharing`, `total_file_count`, `citation` (low, core)

**Action taken:** none. All four remain present in the full record and absent from the core. Deferred on the same grounds: the core schema digest was not supplied, so I cannot distinguish an unexplained projection loss from a correct projection against a narrower class. Flagged here for a run that has the core digest available.

### 2.7 Creators carry no `name` (medium, both)

**Action taken:** every `Creator` object in both records now carries a `name`. Thirty-seven ORCID-bearing creators gained the full name printed in the Dataverse author list and release citation — Timothy Clark, Jillian Parker, Sadnan Al Manir, and so on through Trey Ideker.

Nine further creators were **added** to both records: U Axelsson, B Chinn, J Fall, A Johannesson, H Khaliq, M Muralidharan, E Pan, B Polacco, Y Zhang. These are named in the release citation and in the Dataverse author list with affiliations but no persistent identifier. The original records excluded them from `creators` entirely and mentioned them only in a caveat; they are now represented as `Creator` objects with `name`, `affiliations` and a per-object `source_caveats` recording that no identifier is given in any source. The dataset-level caveat about them was reworded accordingly (from "represented only in the citation string and not as structured creator entries" to "recorded by name without an identifier"). Creator count rose from 37 to 46 in both records.

### 2.8 Self-referential `principal_investigator` on the Ideker Creator (medium, both)

**Action taken:** the nested `principal_investigator` Person, which carried the same ORCID as the enclosing Creator, was removed from both records. In its place the Ideker Creator now carries `credit_roles: [supervision, funding_acquisition]` — both drawn from the enum the digest declares for that key — and a `source_caveats` recording that NIH RePORTER names this person as principal investigator of OT2OD032742 and that the Dataverse record names them as point of contact. The PI fact is preserved; the circular structure is gone.

### 2.9 `publisher` set to an inferred ROR (medium, both)

**Action taken:** the `publisher` slot was removed from both records. The audit is correct that the ror.org string in the June 2026 record appears only inside author *affiliation* fields, never as an identifier for the publishing institution in that role. Under the v5 rule, an identifier naming an organization outside the dataset must be taken from evidence stating it, and no source states this one as the publisher.

The consequential change: every `affiliations` entry across all creators that previously carried `id: ROR:0153tk833` alongside `name: University of Virginia` now carries the name alone. The four affected creators are Clark, Al Manir, Levinson, Niestroy and Ratcliffe. The bundle does state the ror.org string in affiliation fields, but recording it as a `ROR:` CURIE on an `Organization` `id` asserts an identifier-to-organization binding that the raw affiliation string does not supply on its own; the name alone is what the evidence unambiguously gives. The publishing institution remains identified by name throughout `retention_limit`, `maintainers` and `version_access`, and caveat (10) in both records now records why no identifier is asserted.

### 2.10 Inferred reviewing organizations (medium, both — three findings)

**Action taken:** `reviewing_organization` was removed from all three `EthicalReview` objects in both records.

- **Ravitsky:** was `The Hastings Center`, inferred from an email domain. Removed; the `review_details` prose now states the email domain and the University of Montreal affiliation and says explicitly that the record does not state a reviewing organization.
- **Belisle-Pipon:** was `Simon Fraser University`, inferred from an sfu.ca domain with no caveat at all. Removed; `review_details` now states the domain and the SFU affiliation and the same absence.
- **Ethics module:** was `Cell Maps for Artificial Intelligence Ethics module` — a project module in a slot that asks for the body that conducted review. Removed; the module's activities are retained in `review_details`, reworded to open "The CM4AI project's Ethics module works with..." so the subject is clear without the organization field.

The per-object `source_caveats` on the Ravitsky entry, which had disclosed the inference, is now redundant and was dropped; the dataset-level caveat (6) was rewritten to state that the record does not name a reviewing body and that none is asserted.

### 2.11 `data_governance.accountable_organization` (medium, both)

**Action taken:** removed from both records. The original `source_caveats` on that object conceded "the sources do not use the phrase 'accountable organization' themselves"; a value the record itself flags as unsupported should be omitted rather than caveated. The caveat text was amended to "does not name an accountable organization; none is asserted here." The committee name, contact, access-review process and stewardship prose are unchanged.

### 2.12 Instance counts from project-wide aggregates (medium, both — two findings)

**Action taken:** `counts: 53788` was removed from the immunofluorescence `Instance` and `counts: 1374` from the AP-MS `Instance`, in both records. Both figures are cumulative cm4ai.org project totals spanning all cell lines and all releases; neither source apportions them by modality or by release. Each object's `source_caveats` was rewritten to open "No instance count is asserted" and to explain what the project-wide figure covers and why it does not transfer. The figures remain in the dataset-level `description`, correctly labelled there as project-wide, and dataset-level caveat (3) was extended to state that they are not apportioned and are therefore not attached to instance types.

### 2.13 `created_on` from a deposit date (medium, both)

**Action taken:** `created_on: 2025-02-27T00:00:00Z` was removed from both records. The Dataverse fields "Data Creation Date" and "Deposit Date" both read 2025-02-27, which describes the deposit workflow; the underlying data generation began in the project's first year, with NIH RePORTER giving a project start of 2022-09-01. A creation date the evidence contradicts is worse than no creation date.

The generation period is now recorded where it belongs. `collection_timeframes` gained the declared `start_date: 2022-09-01` and `end_date: 2026-08-31` fields (see 2.16), and its `timeframe_details` explains that the Dataverse dates describe deposit rather than generation. Dataset-level caveat (12) records the reasoning in the full record, (13) in the core.

### 2.14 `status` packing three states (low, both)

**Action taken:** narrowed from `published (beta, interim release)` to `published` in both records. The beta and interim qualifications were already carried by `known_limitations` (a `scope_limitation` reading "This is an interim release") and by the title itself; the word "interim beta" was also added to the `description`'s account of the release so nothing is lost.

### 2.15 `created_by` as prose (low, both)

**Action taken:** reduced from a three-clause sentence to `Cell Maps for Artificial Intelligence (CM4AI)`. The programme membership and institutional lead that the sentence carried are stated at length in `description` and in `funders`.

### 2.16 `CollectionTimeframe` with empty declared date fields (low, both)

**Action taken:** `start_date: '2022-09-01'` and `end_date: '2026-08-31'` were added, both `date`-ranged per the digest and both transcribed from the NIH RePORTER project period. The `timeframe_details` prose was rewritten to lead with the funded period, note the first-year start of data generation and the November 2026 completion, and explain the Dataverse date fields.

### 2.17 `related_datasets` typed `is_new_version_of` against its own caveat (low, both)

**Action taken:** all four entries were retyped from `is_new_version_of` to `continues` in both records. The original caveat conceded these are "separate Dataverse deposits with distinct DOIs rather than successive versions of one deposit," which `is_new_version_of` directly contradicts; `continues` is in the declared enum and fits a quarterly series of distinct deposits. The caveat on the fourth entry was reworded to match ("recorded as continuation of a quarterly series rather than as versioning").

### 2.18 `DatasetRelationship` objects with no `name` (low, both)

**Action taken:** each of the four entries gained a `name` giving the target release's full title as the bundle states it — "Cell Maps for Artificial Intelligence - October 2025 Data Release (Beta)" and so on. For the May 2024 release the bundle gives only the preprint citation's shortened title; the full record records this in the entry's `description` and the core record in a `notes` field, with both flagging it in `source_caveats`.

### 2.19 `Grant` objects carrying only an award number in `name` (low, both)

**Action taken:** each Grant now carries `name` (a descriptive grant title), `id` (the award number) and `description`. The 1OT2OD032742-01 entry's description carries the core project number, recipient organization, PI, project period, fiscal-year award amount of 5,289,382 US dollars, application ID 11211616 and project number 3OT2OD032742-01S2 — all previously relegated to the funder-level `source_caveats` prose, which was correspondingly emptied of that material. The 5U54HG012513-02 entry's description records that it is named only in the preprint.

### 2.20 `conforms_to_standard: RO_CRATE` over-scoped (low, both)

**Action taken:** `conforms_to_standard` was left as `[RO_CRATE]`, but the `conforms_to` prose was rewritten to bound the claim: "Released metadata and provenance packages are built as RO-Crates ... the measurement archives themselves are distributed as ZIP files referenced from those crates." The enum value is retained because the release metadata package genuinely is an RO-Crate and the term is what makes the record queryable; the prose now prevents a reader from inferring that every ZIP is one.

### 2.21 `Maintainer` objects with identity only in prose (low, both)

**Action taken:** all five maintainers now carry `name`, and three carry `id`: Ideker (`ORCID:0000-0002-1708-8454`), Thaker (`ORCID:0000-0001-6730-2773`), Niestroy (`ORCID:0000-0002-1103-3882`). The University of Virginia Dataverse and Zhandos Sembay carry names without identifiers, none being given. The maintainer count rose from four to five because Thaker and Sembay, previously bundled in one object, are now separate — two people in one object populated the slot without representing both. `maintainer_details` on each was trimmed to the role description now that identity has moved to its own fields.

### 2.22 `DataCollector` objects with identity only in prose (low, both)

**Action taken:** all five collectors now carry `name` (laboratory or module plus institution), and four carry the `id` of the laboratory head as given in the Dataverse author list, each with a `source_caveats` noting that the bundle names the laboratory rather than assigning it a separate identifier. The CM4AI Standards Module carries a name without an identifier.

### 2.23 `RawData` objects with `access_url` unpopulated (low, both)

**Action taken:** four of the six MassIVE-deposited entries gained `access_url: https://massive.ucsd.edu/`, each with a `source_caveats` stating that the June 2026 record links the deposit by name without printing the accession. A seventh entry was **added** for the Figshare CRISPRi Perturbation Atlas deposit, with `access_url: https://figshare.com/`. The two embargoed perturb-seq entries carry no URL, none being available. `raw_sources` count rose from six to seven in both records.

### 2.24 `RawDataSource.access_details` without identifiers (low, both)

**Action taken:** the RRIDs were moved from mid-sentence in `source_description` to the front of the description and repeated at the end of `access_details`, so `RRID:CVCL_0419` and `RRID:CVCL_B5P3` are each locatable in the field concerned with how to obtain the material.

### 2.25 Keyword ontology URIs dropped (low, both)

**Action taken:** the full set of keyword-to-ontology-term mappings was added to `notes` in both records — NCIT_C16309 for AI and artificial intelligence, CHEBI_45863 for paclitaxel, CL_0000746 for cardiomyocyte, and seventeen more. The `keywords` slot is `string`-ranged and cannot carry URIs; `notes` is where residual content goes when no fitting slot exists, which is the case here.

### 2.26 Dataset-level `compression: zip` flattening a mixed release (low, both)

**Action taken:** removed from the core record; **retained** in the full record. All ten June 2026 components are ZIP archives, so the value is accurate for this deposit, and per-collection `compression: zip` in `file_collections` makes the scope explicit in the full record. In the core record, where `file_collections` is absent, the dataset-level scalar had no per-component context, and `distribution_formats` already states "All ten release components are distributed as ZIP archives." The two records now differ on this slot; the difference is deliberate and noted here rather than concealed.

### 2.27 `Instance.sampling_strategies` declared but unpopulated (low, both)

**Action taken:** two of the four `Instance` objects gained a nested `SamplingStrategy`. The immunofluorescence instance records that imaged proteins are those addressable by validated HPA antibodies within the targeted panels, with the highest-scoring antibody per protein selected. The perturb-seq instance records `is_sample: false` with the genome-scale KOLF2.1J coverage (11,739 genes, six guides each) against the targeted MDA-MB-468 panel. The two mass-spectrometry instances gained none; the bundle does not describe modality-specific selection for them beyond the dataset-level axes.

### 2.28 `relationships` bundling two relation kinds (low, full)

**Action taken:** the single `Relationships` object in the full record was split into two — one for cross-modality keying by protein and gene identity, one for within-interaction-data bait-prey and co-elution edges. The core record still omits `relationships` (see 2.6).

### 2.29 U2OS Nature paper in `external_resources` (low, both)

**Action taken:** the entry was removed from both records. Its own caveat stated that it is "related methodology rather than ... documentation of this dataset," and the referent decision excludes U2OS. Its presence in a slot for resources referenced *by* this dataset, alongside a note saying it does not document this dataset, weakened the slot. The paper remains addressed in dataset-level `source_caveats` (9 in the full record, 10 in the core), where the reasoning for excluding it from the referent belongs. `external_resources` count fell from eleven to ten in both records.

### 2.30 `external_resources` entries as bare strings

**Not an audit finding; corrected in passing.** The digest gives `ExternalResource.external_resources` no scalar range but the slot is multivalued; every entry in both records now wraps its value in a list. The same was done for `DistributionDate.release_dates` and `ExistingUse.examples`, which were bare strings in the originals.

### 2.31 Scalar-ranged slots holding objects

**Not an audit finding; corrected in passing.** Three slots whose declared range is scalar held nested objects in the originals: `license_and_use_terms.contact_person`, `data_governance.committee_contact`, and `EthicalReview.contact_person`. Per the v4 rule, each now holds a string naming the person with the ORCID in parentheses — e.g. `Trey Ideker (ORCID:0000-0002-1708-8454)`.

### 2.32 British spellings

**Not an audit finding; corrected in passing.** `analysed` → `analyzed` in `existing_uses` in both records. Quoted titles and citation strings were left exactly as their sources print them.

---

## 3. Findings left as-is

| Finding | Record | Why |
|---|---|---|
| `distributions` slot undeclared | core | Core schema digest unavailable; `md5` → `hash` addressed the verifiable part. See 2.1. |
| `distributions[*].compression` | core | Same. |
| `file_collections` dropped from core | core | Same. See 2.2. |
| `citation` absent from core as a slot | core | Same; the meta-commentary around it was removed. See 2.4. |
| `direct_collection` absent from core | core | Same; substance relocated to a declared field in both. See 2.5. |
| `relationships` absent from core | core | Same. |
| `third_party_sharing` absent from core | core | Same. |
| `total_file_count` absent from core | core | Same. |
| `last_updated_on` derived from file rows | both | Value retained. It is the latest publication date stated anywhere in the deposit, the derivation is disclosed in caveat (4), and no dataset-level modification date exists to replace it. |
| `id` as `doi:` CURIE, `doi` slot bare | both | Informational. Confirmed correct against the digest and the v5 identifier rule. |
| Fragment-minted `file_collections` ids and CURIE `target_dataset` values | both | Informational. Confirmed correct: fragments on the attested dataset DOI for parts that exist only in this record, attested DOIs in CURIE form for external targets. |

---

## 4. Divergences between the two records after reconciliation

Three remain, all deliberate:

1. **Per-file representation.** Full uses `file_collections` (ten objects); core uses `distributions` (ten objects). Unresolved pending the core schema digest.
2. **`compression`.** Present at dataset level in full, absent in core. Reasoned at 2.26.
3. **Slots present in full only:** `citation`, `publisher` (removed from both), `total_file_count`, `relationships`, `direct_collection`, `third_party_sharing`. Unresolved pending the core schema digest.

No content now appears in the core record that does not appear in the full record. That was true of four items before reconciliation and is true of none after.

---

## 5. Caveat renumbering

Both records' dataset-level `source_caveats` were re-sequenced. Full: 13 items (was 11). Core: 14 items (was 12). The additions are the byte-count caveat (full only, new), the `created_on` provenance caveat (both, new) and the release-series relationship caveat (both, new); the publisher caveat and the reviewing-organization caveat were rewritten rather than added. The core carries one more than the full because its unidentified-authors caveat and the full's differ in wording after the nine authors were promoted to `Creator` objects.