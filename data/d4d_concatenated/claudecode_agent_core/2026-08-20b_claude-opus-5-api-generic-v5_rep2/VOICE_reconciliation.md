# Reconciliation Report — VOICE

**Project:** VOICE
**Version label:** 2026-08-20b_claude-opus-5-api-generic-v5_rep2
**Arm:** BASELINE (input documents only)
**Full record:** `data/d4d_concatenated/claudecode_agent/2026-08-20b_claude-opus-5-api-generic-v5_rep2/VOICE_d4d.yaml`
**Core record:** `data/d4d_concatenated/claudecode_agent_core/2026-08-20b_claude-opus-5-api-generic-v5_rep2/VOICE_d4d_core.yaml`

---

## 1. Audit summary

The Phase 3 audit returned 25 findings: 6 high, 8 medium, 11 low. The dominant defect class was Phase-4 divergence — content present in the core record that the full record does not state — followed by role-fidelity problems in `creators` and `data_collectors`, and a semantic mismatch in how the five disease cohorts were typed.

The audit found no fabricated identifiers: no ROR, ORCID or other registry codes were invented for the twenty named creators or the twelve collaborating institutions, and the five cross-source conflicts flagged in the bundle (hosting platform, award number, recording totals, compensation, healthsheet version lag) were already recorded in `source_caveats`.

---

## 2. Changes made

### 2.1 Divergence: content in core that full did not state

Six findings concerned content the core record introduced without a counterpart in the full record. All six were resolved.

**`other_tasks` (high) — resolved by adding to the full record.** The core record carried an `other_tasks` entry on pediatric developmental norms and early screening tools. Rather than deleting it, the entry was added to the full record, because the pediatric-gap material is attested in the bundle (the pediatric PhysioNet background section and the full record's own `addressing_gaps[4]`). Both records now carry the same single-entry `other_tasks`.

**`raw_sources` (high) — resolved by adding to the full record.** The core record carried a one-entry `raw_sources`; the full record populated only `raw_data_sources`. `raw_sources` was added to the full record with two entries (WAV audio via Synapse; REDCap/ReproSchema responses), and the core record's single entry was expanded to match. Both records now carry the identical two-entry list.

**`ethical_reviews[3].contact_person` (high) — removed.** The core record asserted `contact_person: {name: Yael Bensoussan}` on the USF IRB review of the feasibility study. The bundle names Bensoussan as corresponding author of the feasibility publication, not as IRB contact. The key has been removed from the core record; the fourth `ethical_reviews` entry is now identical in both records.

**`data_governance.committee_contact` and `regulatory_restrictions.governance_committee_contact` (medium) — removed.** Both were Person objects populated with only `email: DACO@b2ai-voice.org` — an office mailbox, not a person, and absent from the full record. Both keys have been removed from the core record. In their place, a `notes` key was added to `data_governance` and to `regulatory_restrictions` in **both** records, recording that the bundle names the DACO mailbox but names no individual, which is why the contact fields are omitted. The mailbox address remains in `access_review_process` prose in both records.

**`distributions` (high) — removed.** The core record carried a `distributions` slot with three entries and sub-keys `format`, `media_type`, `path`, `conforms_to`, `conforms_to_standard`, `notes`. Two of the format/media-type pairs were unsupported by the bundle: `ZIP` / `application/zip` for the features folder (PhysioNet distributes individual `.parquet` and `.tsv` files, with no zip archive stated anywhere) and `JSON` / `application/json` for the metadata folder (the bundle describes it as "a binary file made available as Parquet and its corresponding data dictionary"). The `conforms_to_standard: BIDS` value was also written as a scalar where the digest declares it multivalued. The slot has been removed. The path and directory-structure content it carried has been folded into the `notes` of the corresponding `distribution_formats` entries, which both records already had — the Parquet entry now lists the nine feature files and the metadata folder, and the TSV entry now names the `phenotype/` subfolders and their BIDS conformance.

### 2.2 Direct contradiction between records

**`data_collectors[*].role` (high) — full record's values adopted.** The full record used `researcher`, `academic_institution`, `third_party`; the core record used free prose (`Site research teams`, `Clinicians and physicians`, `Hospital staff`). The digest declares no enum on `DataCollector.role`, so both were structurally valid, but the two records disagreed on the same slot for the same three collectors. The core record has been changed to the full record's three values. The descriptive prose the core record had placed in `role` was already present in `collector_details` in both records, so nothing was lost.

### 2.3 Semantic mismatch: `subsets` vs `resources`

**(medium) — resolved in favour of `subsets`.** The full record placed the five disease cohorts in `subsets` (DataSubset, `is_subpopulation: true`, `is_data_split: false`); the core record placed them in `resources` (Dataset). A cohort is a subpopulation of this dataset, not a component sub-resource, so the full record's typing is correct. `subsets` is not in the core schema, so the core record's `resources` block has been removed and the five cohort descriptions moved into core `notes`, prefaced by an explicit statement that they are subpopulations rather than separate component resources. The full record's `subsets` block is unchanged.

### 2.4 Role fidelity in `creators`

**(medium) — corrected in both records.** All twenty Creator objects used `principal_investigator` for every named individual, including Isaac Bevers (a software developer) and Micah Boyer (no leadership role stated). The bundle names only Bensoussan and Elemento as co-principal investigators.

In both records, `principal_investigator` is now populated for those two only, and as a **string** (the person's name) rather than a Person object — the core schema declares this slot with a scalar range, and the same form was applied to the full record for consistency across the pair. The remaining eighteen creators retain their `affiliations` and `credit_roles`, with the individual's name and stated consortium role moved into `notes` (for example, "Anais Rameau, co-lead of the data acquisition module"). No name was dropped.

### 2.5 Identifier and caveat additions

**`id` version-DOI vs concept-DOI (medium) — caveat added.** `id` remains `doi:10.13026/8xbn-nq66` (the v3.1.0 DOI) while `related_datasets` declares `is_version_of` against the concept DOI `10.13026/37yb-1t42`. This is defensible — the record describes that specific release — but was undocumented. A sentence has been added to `source_caveats` in both records explaining the choice and pointing to where the concept DOI appears.

**Four further caveats added to both records.** `source_caveats` now also records: (6) the language tension between the English-only released cohort and the IRB's English-or-Spanish inclusion criteria; (7) why only BIDS appears in `conforms_to_standard` when the consortium also publishes FHIR profiles (those are a consortium output, not a standard the released content follows); (9) that only two individuals are named by the bundle as co-PIs, explaining the `creators` treatment above; and, in the full record only, (8) that the `variables` list is representative rather than complete.

**`variables` partiality (low) — caveat added, full record only.** Nineteen VariableMetadata entries are supplied against far more documented columns. The list was not expanded; a caveat now records that the authoritative and complete column-level documentation is the set of per-file JSON data dictionaries shipped with the dataset.

**`instances[0]` ontology-term choices (low) — caveat added to both records.** A `source_caveats` key was added to the first Instance recording that `B2AI_TOPIC:25` (Phenotype) was the closest single term where Demographics and Voice were equally applicable, and that `B2AI_SUBSTRATE:41` records the substrate in which the participant record is realized rather than a property of the participant.

**`collection_timeframes[0]` (low) — caveat extended in both records.** A sentence was added distinguishing the 5 June – 28 July 2023 window (which belongs to the feasibility study, recorded in `ethical_reviews[3]`) from the dataset collection window, which the bundle leaves undated.

**`file_collections` record counts (medium/noted) — moved onto the collection, full record only.** The audit noted that per-feature record counts sat in `instances[1].notes` rather than on the collection. A `notes` key was added to `file_collections[0]` carrying those nine counts and stating that the bundle gives no file sizes, which is why `total_bytes` and `total_size_bytes` are omitted. The counts remain in `instances[1].notes` as well.

**`file_collections[1]` BIDS conformance (structural) — added, full record only.** `conforms_to` and `conforms_to_standard: [BIDS]` were added to the phenotype FileCollection, which the bundle explicitly describes as BIDS-conformant.

### 2.6 Multivalued-range corrections

Several slots whose declared ranges are multivalued were carrying scalars in one or both records. These were converted to single-item lists: `machine_annotation_tools[0].tools`, `existing_uses[0].examples`, every `external_resources[*].external_resources`, and every `distribution_dates[*].release_dates`. This is a shape correction rather than a content change; no value text was altered.

---

## 3. Findings left as-is

**`creators[*].affiliations[*]` missing identifiers (medium).** Every Organization object carries `name` only. This is correct under the evidence boundary — the bundle names no ROR identifiers — and supplying them from outside knowledge would be a fabrication. A caveat now records the gap; no identifiers were added.

**`publisher` as a bare origin URL (medium).** `publisher: https://physionet.org` remains. The slot's range is `uriorcurie`, no declared prefix covers PhysioNet, and the bundle supplies no organizational identifier for it. A resolver URL is the permitted fallback; the site root is weak but is what the evidence supports.

**`license` scope (low).** `license: Bridge2AI Voice Registered Access License` remains as a scalar naming the registered-access tier only. The controlled-access instruments governing raw audio remain in `license_and_use_terms.license_terms`. A caveat now records the boundary rather than the scalar being changed, because that license name is what PhysioNet attests verbatim for both the adult and pediatric datasets.

**`created_on` / `last_updated_on` omitted (low).** Both remain omitted. The bundle supports no creation or modification timestamp; `issued` carries the v3.1.0 publication date. The audit raised this only to confirm the omission was deliberate. It was.

**`download_url` omitted at top level (low).** Remains omitted. The files sit behind credentialed access and PhysioNet exposes no direct download URI; the landing pages are carried in `distribution_formats[*].access_urls`, whose declared range is `uri`, which is the correct placement.

**`language: en` (low).** Unchanged. The released cohort is English-only, which is what the scalar should reflect; the IRB's broader eligibility is now recorded in `source_caveats`.

**Core `notes` absorbing structured content (low).** The core `notes` continues to carry participant compensation, splits and instance relationships — content the full record holds in `participant_compensation`, `splits` and `relationships`. Those three slots are not in the core schema, so `notes` is the correct fallback. The block has grown, since the five cohort descriptions moved there too, but every item in it corresponds to a full-record slot the core schema does not offer.

---

## 4. Outcome

| | Full | Core |
|---|---|---|
| Top-level slots populated | 68 | 62 |
| Validates against schema | yes | yes |

Every fact in the core record now has a counterpart in the full record. The six divergences are closed: two by adding the content to the full record where the bundle supported it (`other_tasks`, `raw_sources`), three by removing unsupported content from the core record (`contact_person`, two `Person`-ranged mailbox objects), and one by removing an unverifiable slot and relocating its supportable content (`distributions` → `distribution_formats[*].notes`). The `data_collectors.role` contradiction is resolved in one direction. The cohort typing is consistent: `subsets` in the full record, prose in core `notes` with an explicit statement of what they are.

No identifier was supplied that the declared bundle does not state. No prior D4D record was consulted.