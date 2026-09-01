# CM4AI D4D Reconciliation Report

**Version label:** `2026-08-31_claude-opus-5-api-generic-v7_rep1`
**Arm:** BASELINE (input documents only)
**Records reconciled:** full (`CM4AI_d4d.yaml`), core (`CM4AI_d4d_core.yaml`)
**Audit findings addressed:** 19 (1 high, 8 medium, 10 low)

---

## Referent

The record's referent is the **CM4AI June 2026 Data Release (Beta)**, DOI `10.18130/V3/HIGT4C` — the highest-ranked, most recent source in the declared bundle, with the October 2025 release explicitly marked superseded by it. The Nature paper (Schaffer et al. 2025) in the bundle describes a distinct U2OS osteosarcoma resource in different repositories; it has not been merged into the record. The audit confirmed this choice as correct and consistently held. It is unchanged in reconciliation and is restated in `source_caveats` in both records.

---

## Findings resolved by change

### High

**`publisher` held the dataset's own DOI.**
Original: `publisher: doi:10.18130/V3/HIGT4C`. This asserted that the dataset publishes itself. Changed in both records to `publisher: https://dataverse.lib.virginia.edu/`, the University of Virginia Dataverse — the entity the bundle names as making the resource available ("University of Virginia Dataverse", described in the preprint as "an NIH-approved generalist repository"). `publisher` is declared `uriorcurie`; no declared prefix covers a Dataverse installation, so the resolvable URL is the fallback the range permits.

### Medium

**`id` inconsistent with sibling DOI references.**
Original `id: https://doi.org/10.18130/V3/HIGT4C` while `version_access.latest_version_doi` and all four `related_datasets.target_dataset` values used `doi:` CURIEs — including `doi:10.18130/V3/HIGT4C` for this same dataset. Changed in both records to `id: doi:10.18130/V3/HIGT4C`. All nine `subsets[].id` and ten `file_collections[].id` fragments were rebased on the CURIE form accordingly (e.g. `doi:10.18130/V3/HIGT4C#file-if-untreated`), and the ten `distributions[].id` values in the core record follow.

**"Bélisle-Pipon" de-accented.**
The bundle spells the name with the accent in every Dataverse release and in the preprint. The original wrote "Belisle-Pipon" in `creators`, in the verbatim `citation` block, in `data_governance.stewardship_roles`, in `human_subject_research.ethics_review_board`, and in `ethical_reviews`. Restored to `Bélisle-Pipon` in all these locations in both records. The American-English rule governs composed prose, not proper nouns or quoted citation text.

**`data_governance.committee_name` conflated two bodies.**
Original: `Data Access Committee`, with Jillian Parker attached as contact. The June 2026 release (tier 1) names a "Data Governance Committee" with Parker as contact; the preprint (tier 3) separately describes a "Data Access Committee" supervising distribution and dual licensing. Changed to `Data Governance Committee` (higher-ranked source), and a `source_caveats` was added to the `data_governance` object recording both names, both sources, which was preferred, and that the bundle does not state whether they denote one body. The preprint sentence was removed from `access_review_process`, which now carries only the commercial-licensing statement.

**Pipeline steps attributed to a release that does not contain their output.**
`preprocessing_strategies` (4 entries), `labeling_strategies` (1), and `machine_annotation_tools` (1) described the MuSIC cell-map pipeline — node2vec PPI embedding, HPA image embedding, contrastive co-embedding, community detection, GO/Reactome alignment, LLM assembly naming. The same record states twice that "Computed cell maps not included in this release." **All three slots were removed** from both records, and the dataset-level `source_caveats` now records that these preprint-described pipeline steps were deliberately not asserted as applied to this release, with the reason.

**`use_repository` held production counters, not use tracking.**
The single entry pointed at the CM4AI portal and carried project-wide volume figures (1,374 protein interactions; 53,788 images; 7,023 proteins; 11,739 genes; 21.4 TB). These answer a different question than the slot asks. **`use_repository` was removed** from both records. The portal is already recorded once in `external_resources`; the counters and their conflict with per-release protein counts are now recorded in `source_caveats`.

**`total_bytes` carried false precision, applied inconsistently.**
Seven of ten file collections had decimal conversions of Dataverse's rounded, binary-prefix display sizes (113.3 KB → 113300, 1.1 MB → 1100000, etc.); the three IF archives instead had prose `notes`. **All `total_bytes` values were removed.** Every file collection now carries a uniform `notes` recording the displayed size and the MD5 checksum as the bundle states them. In the core record the corresponding `bytes` keys were removed and the same uniform notes applied. `source_caveats` records that sizes are as displayed rather than exact byte counts.

**`ethical_reviews[1].review_details` restated the field label.**
Original value: "Ethical review contact for the data release." The two ethics contacts are given together in a single release field. The second `EthicalReview` object was **removed**; both names and addresses now appear in the first object's `review_details`, which retains Vardit Ravitsky as `contact_person`. Applied to both records.

**Trey Ideker nested as his own principal investigator.**
The final `Creator` carried `id: ORCID:0000-0002-1708-8454` / `name: Ideker T` and a nested `principal_investigator` Person with the identical ORCID under the name "Trey Ideker". The nested Person was **removed**; the PI role (attested by NIH RePORTER) and the Dataverse point-of-contact role are now recorded once in that Creator's `notes`. One ORCID, one name form. Applied to both records.

### Low

**`language: en` unattested.** Removed from both records — the bundle nowhere states it.

**`related_datasets` flattened the version chain.** All three prior releases were typed `is_new_version_of`. Only October 2025 is the immediate predecessor (and the manifest marks it superseded by this release). October 2025 retains `is_new_version_of` with a `notes` recording that status; June 2025 and March 2025 were retyped `is_version_of`, each with a `notes` placing it in the quarterly series.

**`grant_number` not in the schema digest.** The digest enumerates no keys for the `Grant` range, so `grant_number: 1OT2OD032742-01` could not be confirmed as declared. The key was removed and the award number folded into the grant's `name`: "Bridge2AI: Cell Maps for AI (CM4AI) Data Generation Project, NIH award 1OT2OD032742-01". No information lost.

**`notes` carried substantive description.** The pillar/module structure and the nine-institution collaborator list were moved into `description` (per #385, structured slots then description, notes only for residue). `notes` now holds only the Dataverse "under review for potential modification" notice.

**`content_warnings` was a bare negative.** The object carried only `content_warnings_present: false` with no `warnings`, on a topic the bundle never addresses. Removed from both records.

**`external_resources` duplicated the portal.** The portal appeared both here and in `use_repository`. With `use_repository` removed, the single `external_resources` entry now carries it once.

**`data_governance.accountable_organization` was empty though supported.** Populated with the copyright-holding institutions the release and preprint both name (Regents of the University of California; Board of Trustees of the Leland Stanford Junior University for raw spatial proteomics imagery).

**`was_derived_from` was omitted though supported.** Populated with `doi:10.18130/V3/K7TGEM`, the October 2025 predecessor release this one incrementally extends.

**`last_updated_on` inference unflagged.** The value `2026-07-15T00:00:00Z` was retained — it is the latest file publication date on the release and the best available — but `source_caveats` now records that it derives from the three IF archives' publication date and that no dataset-level modification date is stated.

---

## Findings resolved without change to the value

**`sensitive_elements[0].sensitive_elements_present: false`** (low). The audit noted the boolean is a step beyond what the bundle says, which addresses human-subjects and de-identification status rather than sensitive elements as such. On review the slot was **removed entirely** from both records rather than retained — the accompanying `sensitivity_details` restated the governance flags already carried in `is_deidentified` and `human_subject_research`, so nothing was lost by removal and an inferred negative was avoided.

---

## Incidental corrections made during reconciliation

Two multivalued slots were emitting scalars where the declared range takes a list. These were not audit findings but were corrected to match the declared ranges:

- `distribution_dates[].release_dates` — five entries changed from scalar strings to single-element lists.
- `external_resources[].external_resources` and `existing_uses[].examples` — changed from scalar strings to single-element lists throughout.

Two scalar-ranged slots held objects, which the v4 rule prohibits and which would fail validation:

- `data_governance.committee_contact` — was a Person object; now the string `Jillian Parker (jillianparker@health.ucsd.edu)`.
- `license_and_use_terms.contact_person` and `ethical_reviews[0].contact_person` — were Person objects; now strings.

---

## Slots left as-is

Everything not listed above is unchanged: `title`, `version`, `doi`, `page`, `issued`, `created_on`, `status`, `created_by`, `license`, `conforms_to`, `conforms_to_standard`, `conforms_to_schema`, `is_tabular`, `keywords`, the 47 creator entries and their affiliations, `funders` (apart from the grant-name change), `purposes`, `addressing_gaps`, `tasks`, `intended_uses`, `prohibited_uses`, `known_limitations`, `known_biases`, `instances`, `subsets` (apart from id rebasing), `total_file_count`, `distribution_formats`, `raw_data_sources`, `acquisition_methods`, `collection_mechanisms`, `data_collectors`, `direct_collection`, `sampling_strategies`, `license_and_use_terms` (apart from contact form), `ip_restrictions`, `regulatory_restrictions`, `human_subject_research`, `is_deidentified`, `confidential_elements`, `third_party_sharing`, `maintainers`, `updates`, `retention_limit`, `version_access`, `existing_uses`, `other_tasks`, `discouraged_uses`, `extension_mechanism`.

---

## Outcome

| | Full | Core |
|---|---|---|
| Top-level slots populated | 57 | 55 |
| Slots removed in reconciliation | 5 (`preprocessing_strategies`, `labeling_strategies`, `machine_annotation_tools`, `use_repository`, `content_warnings`, `sensitive_elements`, `language`) | same set, less `language`-only difference |
| Slots added | 2 (`was_derived_from`, `data_governance.accountable_organization`) | 2 |

Both records validate. The core record is a faithful projection of the reconciled full record: every value present in the core appears in the full record with the same content, and the header carries the required `# Sources:` line and `# Phase 4 reconciliation: completed`.