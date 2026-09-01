# CM4AI Datasheet — Phase 4 Reconciliation Report

**Project:** CM4AI (Cell Maps for Artificial Intelligence)
**Label:** 2026-08-31_claude-opus-5-api-generic-v7_rep1
**Arm:** BASELINE (input documents only)
**Referent:** CM4AI data resource as embodied in the June 2026 Data Release (Beta), `doi:10.18130/V3/HIGT4C`

---

## 1. Scope of this report

The Phase 3 audit returned seventeen findings against the full record: two high, eight medium, seven low. Every finding was reviewed against the declared input bundle. Fourteen were acted on in the full record and mirrored into the core record; three were left as-is with reasons stated below.

No finding alleged that a slot asserted a fact the bundle contradicts. The defects were of shape (class-ranged slots populated as prose), scope (project-wide figures placed in release-scoped slots), granularity (distinct entities collapsed into single objects) and one unsupported inference (`publisher`).

---

## 2. Findings acted on

### 2.1 `creators` — declared fields left empty (high)

**Finding.** All 38 Creator objects carried an ORCID `id` and nothing else, leaving `affiliations` and `principal_investigator` empty although the bundle states an affiliation for every author and names Ideker as PI and point of contact.

**Change.** Every Creator entry now carries an `affiliations` list with the organization name as the June 2026 release states it, and a `notes` field naming the author (the release gives the name in its author list but Creator declares no name field). The Ideker entry additionally carries:

```yaml
principal_investigator:
  name: Ideker, Trey
  affiliation: University of California San Diego
```

The affiliation strings are copied from the June 2026 release page — "University of California, San Diego" for some authors and "University of California San Diego" for others, reproduced as the source renders each. No ROR or other organization identifier was added: the bundle names the organizations but supplies registry identifiers for none of them except the ROR string discussed in §2.3, and supplying one from outside the bundle would be an unsupported claim.

Several entries acquired a second sentence in `notes` where the bundle attests a further role: Niestroy as depositor, Thaker as program manager, Ravitsky and Belisle-Pipon as ethical review contacts.

### 2.2 `creators` — nine authors omitted (high)

**Finding.** Nine authors listed on the release (Axelsson U, Chinn B, Fall J, Johannesson A, Khaliq H, Muralidharan M, Pan E, Polacco B, Zhang Y) were dropped for lacking an ORCID, contradicting the `citation` value in the same record.

**Change.** All nine are now present as Creator entries with `affiliations` and a `notes` field of the form "Axelsson U. Listed as an author of the June 2026 release; no ORCID is given for this author in the source." They carry no `id`, which the schema digest permits: Creator has no required keys. The creator list is now 47 entries, matching the citation string.

The `source_caveats` sentence was rewritten from "are not represented as creator entries" to "they are represented as creator entries carrying affiliation and a note rather than an identifier."

### 2.3 `publisher` — unsupported inference (medium)

**Finding.** `publisher: ROR:0153tk833` rested on a string the bundle supplies only inside the June 2026 author-affiliation fields, never as a statement of who publishes the dataset.

**Change.** The slot was removed from both records. A sentence was added to `source_caveats` recording why: the ROR string appears only as an author affiliation, and the bundle names the University of Virginia Dataverse as host without naming a publisher for the slot.

### 2.4 `instances` — project-wide counts in release-scoped slots (medium, two findings)

**Finding.** `counts: 53788` (images) and `counts: 1374` (AP-MS interactions) were project-wide portal figures, and the record's own `notes` said so. The AP-MS figure additionally contradicted the release-scoped AP-MS description in `file_collections`.

**Change.** Both `counts` values were removed, along with the two `notes` fields that flagged them. The images entry now carries only `instance_type`, `data_substrate`, `data_topic` and `label_description`. The AP-MS entry received a replacement note stating the release-level scope: "In the June 2026 release the AP-MS archives cover treated MDA-MB-468 cells only (paclitaxel and vorinostat)." The project-wide figures remain in `description`, where they were already stated and correctly attributed to the portal. A clause was added to `source_caveats` explaining that these counts are stated in description rather than in the release-scoped count slots.

### 2.5 `other_tasks` — empty list (medium)

**Finding.** `other_tasks: []` conveys nothing that omission does not.

**Change.** The slot was removed from both records.

### 2.6 `data_governance` — contact in prose (medium)

**Finding.** The committee contact's name and email sat inside `access_review_process` while the declared `committee_contact` field (range Person) was empty.

**Change.** The contact was moved into the declared field:

```yaml
committee_contact:
  name: Parker, Jillian
  email: jillianparker@health.ucsd.edu
  affiliation: University of California San Diego
```

The opening sentence naming her was removed from `access_review_process`, which now begins with the Data Access Committee's function.

`accountable_organization` was **not** populated — see §3.1.

### 2.7 `ethical_reviews` — contacts in prose (medium)

**Finding.** Both entries left `contact_person` empty while embedding two reviewers' names and emails in `review_details`.

**Change.** The multivalued slot now carries three entries rather than two, since the two named reviewers are distinct entities:

- Ravitsky, with `contact_person` populated (name, email, affiliation "The Hastings Center", which the bundle supplies via her email domain and the release's collaborator list);
- Belisle-Pipon, with `contact_person` populated (name, email, affiliation Simon Fraser University, as the release author list gives it);
- the third entry, unchanged, describing the Ethics Module's Value-Sensitive Design methodology, which names no individual.

`reviewing_organization: CM4AI Ethics Module` is retained on all three.

### 2.8 `external_resources` — `archival` unpopulated (medium)

**Finding.** Six of seven entries left the declared boolean `archival` empty even where the bundle states archival status.

**Change.** `archival: true` was set on the MassIVE, SRA, Figshare and project-software entries; `archival: false` on the CM4AI portal entry, which the bundle describes as a live project website under review for modification. `future_guarantees` was populated on the software entry from the bundle's statements about Zenodo long-term archiving and per-dataset version referencing. A `restrictions` entry was added to the portal entry recording the modification notice. The NDEx entry and the related-publications entry were left without `archival`: the bundle states nothing about the archival status of either.

### 2.9 `related_datasets` — overstated relationship type (low)

**Finding.** `is_new_version_of` applied uniformly across a four-deep release series overstates the pairwise relationship for the older members.

**Change.** All four entries changed to `is_version_of`. Each `description` was extended to say where in the series the target sits — "the immediately preceding quarterly release, superseded by the June 2026 release" for October 2025, "an earlier quarterly release of the same resource" for June 2025 and March 2025, "the first quarterly release of the same resource" for May 2024.

### 2.10 `collection_timeframes` — funding date as collection start (low)

**Finding.** `start_date: '2022-09-01'` is the NIH RePORTER project start, not a collection start.

**Change.** `start_date` was removed. The entry now opens "The bundle does not state when data collection began or ended," retains the surrounding prose about the project period and first-year acquisition, and carries a new object-level `source_caveats` explaining that the available dates are funding-period and deposit boundaries. A matching clause was added to the record-level `source_caveats`.

### 2.11 `sampling_strategies` — two strategies in one object (low)

**Finding.** Target selection and cell-line representativeness were collapsed into a single SamplingStrategy.

**Change.** Split into two objects. The first carries `is_sample: true`, `is_random: false` and the target-selection `strategies` text. The second carries `is_sample: true`, `is_representative: false`, a `strategies` field describing the choice of the two cell lines, and the `why_not_representative` text. `is_random` was not repeated on the second object, and `is_representative` was not repeated on the first: the bundle speaks to each question once.

### 2.12 `file_collections` — `total_bytes` unpopulated (low)

**Finding.** Every collection populated `file_count` but none populated `total_bytes`, although per-file sizes are stated for all ten files.

**Change.** `total_bytes` added to all six collections, computed by summing the per-file sizes as displayed. Each collection carries an object-level `source_caveats` recording the arithmetic and the unit convention (KB as 1000, GB as 1000000000), since the release page gives rounded human-readable sizes rather than exact byte counts. The record-level `source_caveats` notes that per-collection totals are computed this way while `total_size_bytes` remains omitted.

In the core record these appear as `bytes` on the corresponding `distributions` entries, with the caveat text carried across unchanged.

### 2.13 `raw_data_sources` — two deposits in one object, formats unpopulated (low)

**Finding.** The fifth entry conflated the KOLF2.1J and MDA-MB-468 raw sequence deposits, which the bundle lists as two separately embargoed links; `raw_data_format` was unpopulated throughout.

**Change.** The fifth entry was split into two, one per deposit, each with its own `access_details` recording its embargo. `raw_data_format` was added to all six entries — "mass spectrometry raw data files" for the four MassIVE deposits, "single-cell sequencing reads" for the two SRA deposits.

### 2.14 `version` — 2.0 / V2 unreconciled (low)

**Finding.** The record did not note that "Version 2.0" in the page header and "V2" in the citation on the same page are one version rendered two ways.

**Change.** `version: '2.0'` is unchanged. The `source_caveats` sentence on version labelling was rewritten to say the inconsistency exists "both within and across Dataverse pages" and that the two renderings on the June 2026 page "are the same version rendered two ways, not two versions." `version_access.version_details` was rewritten to the same effect.

### 2.15 `known_biases` — selection bias unrecorded (low)

**Finding.** Targeted panel selection and incomplete cross-modality overlap bear on bias, not only on integration limitations.

**Change.** A second DatasetBias entry was added with `bias_type: selection_bias`, describing the targeted selection of ~100 chromatin modifiers and ~100 metabolic enzymes and the incomplete overlap between modalities, with `affected_subsets` and `mitigation_strategy` populated. The integration limitation under `known_limitations` was left in place: the two slots are answering different questions about the same underlying fact.

### 2.16 `labeling_strategies` — protocol in free text (low)

**Finding.** The class declares `data_annotation_protocol`; the two-pronged annotation procedure sat in `labeling_details`.

**Change.** The procedure was moved into `data_annotation_protocol`. `labeling_details` now carries the residual detail about the LLM confidence score. `inter_annotator_agreement` was **not** populated — see §3.3.

---

## 3. Findings left as-is

### 3.1 `data_governance.accountable_organization` (part of finding 2.6)

The audit suggested populating `accountable_organization` from the copyright-holding institutions. Left empty. The bundle names UCSD, Stanford and UCSF as copyright holders for specific data packages, and names UCSD as the governance contact's institution, but it does not state that any of them is the organization accountable for the dataset over time. Populating the slot would require choosing among three on grounds the bundle does not supply. An object-level `source_caveats` was added recording this and pointing to `ip_restrictions`, where the copyright-holder statement lives.

### 3.2 `conforms_to_standard` — under-specification (finding 17)

The audit noted that the single `RO_CRATE` value does not record that the imaging data follow no declared standard, and described the value as "defensible." No change. The enum offers no term for "no standard applies," and the JSON-LD/RDF-XML serializations and the EVI ontology are properties of the provenance packaging already covered by `RO_CRATE` and described in `distribution_formats` and `preprocessing_strategies`.

### 3.3 `labeling_strategies.inter_annotator_agreement` (part of finding 2.16)

The audit suggested the LLM confidence score is "a quality measure the class has fields for." Not placed in `inter_annotator_agreement`. A model's self-assessed confidence in a name it generated is not agreement between annotators; the field would carry a value of the wrong kind. The confidence score is recorded in `labeling_details` instead.

---

## 4. Full-to-core consistency

The core record was re-derived from the reconciled full record. Every change above is reflected in both where the core schema carries the slot:

- `creators`, `funders`, `instances`, `known_biases`, `sampling_strategies`, `raw_data_sources`, `labeling_strategies`, `collection_timeframes`, `data_governance`, `ethical_reviews`, `external_resources`, `related_datasets` — carried across identically.
- `publisher` and `other_tasks` — removed from both.
- `file_collections` → `distributions`: the six collections project to six distribution entries; `total_bytes` projects to `bytes`; `file_count` and `collection_type` have no core counterpart and are dropped by the projection, as before.
- `total_file_count` has no core counterpart and does not appear in the core record; the full record retains it at 10.
- Record-level `source_caveats`, `description` and `notes` are identical in both.

The core header carries `# Sources:` pointing at the full record and `# Phase 4 reconciliation: completed`.

---

## 5. Referent

Unchanged from Phase 1: the record describes the CM4AI data resource as embodied in its current Dataverse release, the June 2026 Data Release (Beta), `doi:10.18130/V3/HIGT4C`. Earlier quarterly releases are recorded under `related_datasets` as versions of the same resource. This choice is stated in `source_caveats` in both records and was not revisited during reconciliation.

---

## 6. Source-ranking decisions carried forward

The following conflicts were resolved in Phase 1 under the declared ranking and were not disturbed:

| Conflict | Sources | Resolution |
|---|---|---|
| Release date | portal (tier 2) says "June 17, 2025"; Dataverse (tier 1) says 2026-06-17 | Dataverse date used |
| IF protein count | 464 (Oct 2025, tier 1); 523 (portal, tier 2); 563 (Mar 2025, tier 5) | 464 used |
| Project period | RePORTER (tier 4) 2022-09-01 to 2026-08-31; Dataverse (tier 1) "November 2026" | Both stated; neither used as a collection date after §2.10 |
| Supersession | Oct 2025 marked SUPERSEDED BY June 2026 | June 2026 is the referent |

---

## 7. Outcome

| | Full | Core |
|---|---|---|
| Top-level slots populated | 55 | 55 |
| Validation | pass | pass |

Findings acted on: 14. Findings left as-is with reasons: 3. No new facts were introduced from outside the declared bundle; the only additions are values the bundle already stated, relocated into the declared fields that ask for them.