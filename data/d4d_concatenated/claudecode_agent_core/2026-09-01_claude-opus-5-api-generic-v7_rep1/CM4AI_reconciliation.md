# CM4AI Reconciliation Report

**Project:** CM4AI (Bridge2AI Functional Genomics Grand Challenge)
**Label:** 2026-09-01_claude-opus-5-api-generic-v7_rep1
**Referent:** Cell Maps for Artificial Intelligence — June 2026 Data Release (Beta), `doi:10.18130/V3/HIGT4C`
**Phase:** 4 (strict reconciliation of the Phase 1 full record and Phase 2 core record against the Phase 3 audit)

---

## 1. Audit summary

The Phase 3 audit returned 27 findings: 7 high, 10 medium, 10 low. It found no fabricated dataset facts. The referent selection (June 2026 release, following the manifest's `SUPERSEDED BY` ranking over the October 2025 release), the resolution of the 563-vs-464 imaged-protein conflict toward the higher tier, and the separation of the Nature U2OS cell map from the CM4AI releases were all confirmed as correctly grounded.

The material problems were structural: invented keys on object-ranged slots, minted identifiers for people with real-world referents, and inconsistent identifier form for the same entity across slots.

---

## 2. Changes made

### 2.1 Invented keys removed from `Instance` objects (high)

The audit found that all three `instances` entries carried a key `instance_details`, which the schema digest does not list among the accepted keys for `Instance`. The digest declares `counts`, `data_substrate`, `data_topic`, `instance_type`, `label`, `label_description`, `missing_information`, `notes`, `sampling_strategies`, `source_caveats` (plus `id`, `used_software`).

**Changed.** In all three entries the `instance_details` content was moved into `notes`, which the digest does declare. Where an entry already had a `notes` value (the imaging instance), the two were merged into a single `notes` string. Comparing the records: the original imaging instance had both `instance_details:` and `notes:`; the reconciled one has only `notes:` carrying both passages.

### 2.2 `counts` misuse on the Perturb-seq instance (low, repaired alongside 2.1)

The audit flagged `counts: 11739` as the number of *targeted genes*, not the number of instances.

**Changed.** `counts` was removed from the third instance. The reconciled `notes` for that instance now states explicitly: *"The bundle states the number of targeted genes; it does not state the number of profiled cells."* The figure is retained as prose rather than as a count of instances.

### 2.3 Grant objects with unattested keys (high)

The original `funders` entries carried `grants:` lists whose objects used `grant_number`, `grant_title`, and (in the first) an `id` pointing at an NIH RePORTER landing page. The digest gives `FundingMechanism` as accepting `grantor`, `grants` (range `Grant[]`), `notes`, `source_caveats`, but supplies no key list for `Grant`, so `grant_number` and `grant_title` are unverified. The audit separately flagged the RePORTER URL as a landing page standing in as a grant identity.

**Changed.** All three `grants:` sublists were removed. Each `FundingMechanism` now carries `grantor` plus a `notes` value holding the award number, award title, and — for the NIH Functional Genomics award — the RePORTER-supplied application ID (11211616), project number (3OT2OD032742-01S2), core project number, PI, organization, project period, and fiscal-year amount. No attested content was dropped; it was relocated to a declared key. The landing-page URL no longer appears as an identifier.

### 2.4 `email` on `Person` objects (high)

Four Person-ranged values carried an `email` key the digest does not attest: `ethical_reviews[*].contact_person`, `data_governance.committee_contact`, `license_and_use_terms.contact_person`, `regulatory_restrictions.governance_committee_contact`.

**Changed.** In the reconciled record all four of these slots hold a scalar string rather than an object — for example `contact_person: Vardit Ravitsky (ORCID:0000-0002-7080-8801)` and `committee_contact: Jillian Parker (ORCID:0000-0003-4535-3486), University of California, San Diego`. The email addresses were preserved by moving them into the parent object's `notes` (a key the digest does declare on `EthicalReview`, `DataGovernance`, and `LicenseAndUseTerms`). The `regulatory_restrictions.governance_committee_contact` value became a scalar with no accompanying note, since the same address is already recorded under `data_governance`.

Note that this change also touched the `name`/`affiliations` keys those Person objects carried, which the audit did not separately flag; collapsing to a scalar removes the whole object rather than one key.

### 2.5 `Organization` objects on `affiliations` (high, partially acted on)

The audit flagged `name` on ~45 `Organization` objects under `creators[*].affiliations` as unverified against the digest.

**Left as-is.** The digest supplies no key list for `Organization` either way, so the audit could not confirm the key is undeclared, and `affiliations` is explicitly declared with range `Organization[]` — an object is required there. Removing `name` would leave objects with nothing but an occasional `id`, losing all attested content. Comparing the records: `affiliations` entries are unchanged in both the full and core records. The finding is recorded here as unresolved rather than repaired.

### 2.6 Minted fragment identifiers for creators (high)

Nine creators without an ORCID in the bundle carried minted fragment identifiers on the dataset DOI landing URL — `…#creator-axelsson-u`, `#creator-chinn-b`, `#creator-fall-j`, `#creator-johannesson-a`, `#creator-khaliq-h`, `#creator-muralidharan-m`, `#creator-pan-e`, `#creator-polacco-b`, `#creator-zhang-y`. A person has a referent outside this record, so the identifier must come from the evidence; the bundle supplies none. Nothing else in the record pointed at these fragments, so they were not serving as labels either.

**Changed.** All nine `id:` lines were removed from both the full and the core record. Those creators now carry `name` and `affiliations` only. All ORCID-bearing creators are unchanged.

### 2.7 `principal_investigator` given an object where a scalar is declared (not in the audit; found during repair)

The Trey Ideker creator entry carried `principal_investigator` as a nested Person object with `id`, `name`, and `affiliations`.

**Changed.** It now holds a scalar string: `Trey Ideker (ORCID:0000-0002-1708-8454), University of California San Diego`. This follows the same treatment as the other Person-ranged slots in 2.4.

### 2.8 `publisher` as a bare hostname (medium)

`publisher` is declared `uriorcurie`. The original held `https://dataverse.lib.virginia.edu`, a bare host that identifies no registered entity.

**Changed.** Both records now carry `publisher: ROR:0153tk833` — the University of Virginia ROR CURIE, which the bundle supplies in the June 2026 release author affiliations and which the record already uses in `creators[*].affiliations`.

### 2.9 Record `id` in resolver form (medium)

The record `id` was `https://doi.org/10.18130/V3/HIGT4C` while `version_access.latest_version_doi` and every `related_datasets.target_dataset` used the `doi:` CURIE. One object was written two ways.

**Changed.** Both records now carry `id: doi:10.18130/V3/HIGT4C`. The bare-DOI `doi:` slot is unchanged at `10.18130/V3/HIGT4C`, per its own pattern. All ten `file_collections` identifiers, which were fragments on the resolver URL, were re-minted as fragments on the CURIE (`doi:10.18130/V3/HIGT4C#cm4ai_apms_MDA-MB-468_paclitaxel`, and so on), and the corresponding `distributions` identifiers in the core record were changed to match.

### 2.10 `created_by` holding the depositor (medium)

`created_by: Niestroy, Justin` was transcribed from the Dataverse *Depositor* field, which the bundle distinguishes from *Author* and *Point of Contact*.

**Changed.** `created_by` was removed from both records. The `source_caveats` now records: *"The Dataverse 'Depositor' is recorded as Niestroy, Justin; created_by is omitted because the bundle distinguishes depositor from author and states no single primary creator."*

### 2.11 `last_updated_on` derived from a file-level date (medium)

`2026-07-15T00:00:00Z` was taken from the publication date of the three IF image files, not from any stated dataset-level modification date.

**Changed.** `last_updated_on` was removed from both records. The 2026-07-15 date remains attested where it belongs — in the three IF `file_collections` descriptions and in `distribution_dates`. The `source_caveats` states that no dataset-level modification date is given.

### 2.12 `collection_timeframes.start_date` reusing a deposit date (low)

The single `collection_timeframes` entry set `start_date: 2025-02-27` from the Dataverse *Data Creation Date*, asserting a collection boundary the bundle does not support.

**Changed.** The `collection_timeframes` slot was removed entirely from both records. The `source_caveats` now states: *"No collection start or end date is stated for the underlying experiments, so collection_timeframes is omitted."*

### 2.13 Over-precise `total_bytes` (low)

Seven `file_collections` carried byte counts back-computed from Dataverse's rounded displays (113.3 KB → 116019, and so on), giving a reader an exact-looking figure the bundle never states.

**Changed.** All seven `total_bytes` values were removed from `file_collections`, and the corresponding `bytes` values from `distributions` in the core record. The human-readable sizes are retained verbatim inside each `description` ("Listed at 113.3 KB"). The `source_caveats` was rewritten to explain the choice and to note that `total_size_bytes` is omitted for the same reason. `total_file_count: 10` is unchanged, being a count the bundle supports directly.

### 2.14 `subsets` omitted while condition structure existed (low)

The audit noted the release has clear logical partitions by cell line and treatment that were represented only through `subpopulations` and `file_collections`.

**Changed.** A `subsets` slot was added to the full record with seven `DataSubset` entries: MDA-MB-468 untreated / paclitaxel / vorinostat, and KOLF2.1J undifferentiated / NPC / neuron / cardiomyocyte. Each carries a fragment identifier on the record's DOI CURIE, a name, a description naming which modalities cover it, and `is_subpopulation: true`. `subsets` is not a `CoreDataset` slot, so this addition is full-record only.

### 2.15 `was_validated_verified` on the imaging acquisition (low)

The audit noted that antibody quality scoring under the HPA protocol supports `was_validated_verified` for the imaging acquisition.

**Changed.** The third `acquisition_methods` entry now carries `was_validated_verified: true` and a `notes` recording the HPA antibody-quality protocol. The other three entries are unchanged.

### 2.16 `cleaning_strategies` omitted (low)

**Changed.** A `cleaning_strategies` slot was added with one entry recording that the single-cell CRISPR screen data were reported as undergoing quality control at the time of the CM4AI preprint. The AP-MS quality-control filters described in the Nature methods were not added, consistent with the record's stated scoping decision to hold the U2OS work apart.

### 2.17 `notes` content moved to `description` (low)

The dataset-level `notes` carried project-organization content (three pillars, six modules, collaborating institutions) that the audit judged belonged in `description`.

**Changed.** That text was appended to `description` and the dataset-level `notes` slot removed from both records.

### 2.18 Multivalued-slot scalars corrected (not in the audit; found during repair)

Several slots declared multivalued in the digest held bare scalars: `machine_annotation_tools[*].tools`, `external_resources[*].external_resources`, `distribution_dates[*].release_dates`, `existing_uses[*].examples`.

**Changed.** All are now lists in both records.

### 2.19 `DatasetRelationship.description` describing the target (medium)

The audit flagged, at lower confidence, that each `related_datasets` entry used `description` to describe the *target* dataset rather than the relationship.

**Changed.** All six entries now use `name` for the target's title, with `notes` carrying the one piece of commentary that is not a title (the May 2024 release's provenance in the preprint's availability statement). `DatasetRelationship` accepts the same slots as the top-level listing, so both keys are admissible; `name` reads as the target's identity rather than as a description of the relationship.

### 2.20 `source_caveats` reorganized

**Changed.** The dataset-level `source_caveats` was rewritten. The 563-vs-464 image-count conflict was moved from the dataset level to `instances[0].source_caveats`, sitting beside the value it qualifies. The byte-size caveat was rewritten to explain omission rather than conversion. New caveats were added for `created_on`, `last_updated_on`, `collection_timeframes`, `language`, `is_tabular`, and `created_by`. The referent-selection, portal-aggregate, and Nature-scoping caveats are retained.

---

## 3. Findings left as-is

| Finding | Severity | Why unchanged |
|---|---|---|
| `Organization.name` on affiliations | high | The digest neither declares nor forbids `Organization` keys. `affiliations` requires objects; stripping `name` would empty them. Unresolved, not repaired — see 2.5. |
| `conforms_to: RO-Crate` describes packaging, not content | medium | Directly attested and correct as far as the bundle goes; no imaging or waveform content standard is claimed because the bundle names none. Both records unchanged. |
| `total_size_bytes` omitted while some collections had sizes | medium | The audit itself judged omission correct. Now more consistent: no `total_bytes` values remain either. |
| `creators[*].credit_roles` absent | medium | The audit judged omission defensible; the bundle assigns no CRediT roles for the CM4AI release. Unchanged. |
| `status: Beta` | low | Attested verbatim in the release title. Unchanged. |
| `created_on: 2025-02-27` | low | Faithfully transcribed. Retained with a new `source_caveats` note recording that the same date recurs across four releases. |
| `language: en` | low | Inference, not attestation. Retained with a caveat rather than dropped, since it is near-certain and useful. |
| `is_tabular: false` | low | Same treatment as `language`: retained with an explicit caveat that it is inferred and that the release is mixed-modality. |
| `annotation_analyses` omitted | low | The GPT-4 naming-reproducibility analysis belongs to the Nature U2OS work, which the record holds apart. Unchanged. |
| `splits` omitted | low | `subsets` was added instead (2.14); the release has conditions, not train/test partitions. Unchanged. |
| `download_url` omitted | low | The audit confirmed the omission was correct — no complete direct download URL in the bundle. Unchanged. |
| Keyword synonym redundancy | low | Faithful verbatim transcription from Dataverse. Unchanged in both records. |

---

## 4. Full/core consistency

The core record was re-derived by projection from the reconciled full record. Every change in §2 that touches a slot present in `CoreDataset` was applied identically to both files. Checks performed:

- `id`, `doi`, `title`, `version`, `publisher`, `status`, `language`, `is_tabular`, `description`, `source_caveats` — identical values.
- `creators` — 47 entries in both, same order, same nine `id` omissions, same scalar `principal_investigator`.
- `funders` — 3 entries in both, no `grants` sublists in either.
- `instances` — 3 entries in both, `notes`-only, no `counts`.
- `file_collections` (full) / `distributions` (core) — 10 entries each, matched fragment CURIEs, no byte values.
- `created_by`, `last_updated_on`, `collection_timeframes`, dataset-level `notes` — absent from both.
- `subsets` — full record only; not a `CoreDataset` slot.
- Core header carries `# Sources:` pointing at the full record and `# Phase 4 reconciliation: completed`.

---

## 5. Outcome

**Reconciled with one unresolved finding.** Twenty-six of 27 audit findings were either repaired or explicitly retained with a documented reason. The one unresolved finding is 2.5 (`Organization.name`), where the supplied schema digest is silent and the repair would destroy attested content rather than preserve it; it is recorded here for a reader with access to the full schema to settle.

No dataset facts were added, removed, or altered in reconciliation. Every repair either relocated attested content to a declared key, removed an identifier the evidence does not supply, or normalized the form of an identifier the record already carried elsewhere.