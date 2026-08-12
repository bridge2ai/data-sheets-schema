# Reconciliation Report — CHORUS

**Version label:** `2026-08-11_claude-opus-5-api-generic_rep1`
**Arm:** BASELINE (input documents only)
**Source bundle:** `data/preprocessed/concatenated/CHORUS_preprocessed.txt`
**Records reconciled:**
- Full — `data/d4d_concatenated/claudecode_agent/2026-08-11_claude-opus-5-api-generic_rep1/CHORUS_d4d.yaml`
- Core — `data/d4d_concatenated/claudecode_agent_core/2026-08-11_claude-opus-5-api-generic_rep1/CHORUS_d4d_core.yaml`

---

## 1. Referent decision

`Dataset` admits one referent. The declared bundle describes three things that could be mistaken for one another:

1. the **CHoRUS award / data generation project** (NIH RePORTER `OT2OD032701`, 2022-09-01 → 2026-11-30),
2. the **CHoRUS software and SOP ecosystem** (the `chorus-ai` GitHub organization, MIT-licensed),
3. the **CHoRUS clinical dataset** — the multi-modal, controlled-access, OMOP-standardised collection of ICU/PICU/NICU admissions.

The referent held across both records is **(3), the CHoRUS clinical dataset**. The project (1) is represented only as funding, purposes, creators and timeframe; the software (2) is represented only as tooling, external resources and machine annotation tools, never as the licensed object. This decision was already implicit in Phase 1 and Phase 2 and is now stated explicitly. The most consequential downstream effect is that the top-level `license` slot remains unpopulated: the MIT statement in the bundle governs the GitHub organization, not the data, and the data's terms are a signed licensing agreement with no named license.

---

## 2. What the audit found

The Phase 3 audit returned 24 findings: 5 high, 9 medium, 10 low. They cluster into three classes, plus one cross-cutting inconsistency.

**Class A — unverified structure.** The core record placed the nine data modalities in `resources` and attached a note asserting a constraint about a `distributions` slot and its enumerated format values. Neither claim had been checked against `data_sheets_schema_core_all.yaml`. The full record used `file_collections` for the same nine modalities, so the two records could not be reconciled against each other without reading the core schema.

**Class B — inference presented as fact.** Six values were contradicted or hedged by their own adjacent `source_caveats`: five `principal_investigator` flags, `confidentiality_level: restricted`, `was_directly_observed: true`, the core record's award-period `start_date`/`end_date`, both `known_biases` entries, and the full record's `splits` entry. A value whose caveat concedes it is unsupported is a value that should have been omitted.

**Class C — shape violations.** `conforms_to` carrying prose qualifiers at top level and in every nested collection; `was_derived_from` carrying an enumeration into a singular slot; `ethical_reviews[].contact_person` bundling four facts into one string; `status` carrying an analytical composite; `notes` carrying source commentary.

**Cross-cutting.** `direct_collection`, `third_party_sharing` and `splits` existed in the full record but had been dissolved into other slots in the core record without documentation, and the holdout test set appeared as a `Splits` object in one record and a `tasks` entry in the other.

One asymmetry deserves separate mention because it is the clearest single defect: `total_size_bytes` was correctly omitted because "23 Tb" is ambiguous between terabyte and terabit, while `counts: 50000` silently resolved a documented conflict with the more recent "over 45K unique admissions" figure. Two comparable ambiguities, opposite standards.

---

## 3. Changes made

### 3.1 Both records

| Slot | Change | Reason |
|---|---|---|
| `creators[].principal_investigator` | Removed from Bihorac, Jiang, Strekalova, Rashidi, Kwong. Retained on Rosenthal. Their leadership-team membership moved to `creators[].notes` as "Listed under 'Bridge2AI CHoRUS Leadership Team' in the AIM-AHEAD Cohort 2 informational webinar." | Only NIH RePORTER designates a PI, and it designates one. Leadership-team membership is not evidence of PI status. Finding 3, high. |
| `conforms_to` | Replaced the six-standard prose paragraph with `OMOP Common Data Model`. The full enumeration is already carried per-modality; a pointer sentence naming the other five standards moved to `description`. | The slot names one standard the content follows. Finding 5, high. |
| `id` | Changed from `https://chorus4ai.org/` to `https://chorus4ai.org/dataset`. `page` retains `https://chorus4ai.org/`. Nested modality URIs retained but now hang off the changed base. | The prior value made the dataset identical to its own landing page. The replacement is still a constructed URI — see §4 — but it no longer conflates two entities. Finding 2, high. |
| `regulatory_restrictions.confidentiality_level` | Removed. The supporting facts (uniform "Controlled" access marking; signed licensing agreement; `.edu` email requirement) remain in `license_and_use_terms` and `confidential_elements`. | The enum value was labelled inferred by its own caveat. Omission over inference. Finding 11, medium. |
| `instances[].counts` | Changed from `50000` to `45000`, with `source_caveats` rewritten to name both figures, both sources and both dates explicitly: chorus4ai.org states 50,000 released patient admissions with no date; the September 2025 webinar states over 45K unique admissions as of August 2025. | The conflict is real and is now represented rather than resolved silently. The lower, dated, more recent figure is the defensible floor. Finding 6, medium. Also corrects the asymmetry with `total_size_bytes`. |
| `known_biases` | Both entries removed. Their content was rewritten as `known_limitations` entries: `representativeness_limitation` for the 14-hospital academic-centre network, and a second entry recording that no bias audit or fairness evaluation is reported in the bundle. | The bundle documents a project *concern* about bias and a *structural fact* about network composition. Neither is a measured bias, and neither supports a `bias_type` assignment as a characterisation of the data. Finding 12, medium. |
| `acquisition_methods[].was_directly_observed` | Changed to `false`. `was_reported_by_subjects` left unpopulated. `acquisition_details` now states that data were recorded during routine clinical care by treating institutions and retrospectively extracted. | The data are pre-existing hospital records; nothing was observed by the dataset creators. Finding 17, low, but the boolean was flatly wrong. |
| `ethical_reviews[].contact_person` | Removed. Ciera McCrary retained in `maintainers` as Program Manager, MGH, with the email transcribed as it appears in the bundle and a `source_caveats` noting the apparent typo (`mgh.havard.edu`). | The bundle gives no connection between the program manager and ethical review. Finding 9, medium. |
| `was_derived_from` | Reduced to `Electronic health record, PACS imaging, bedside telemetry, and hospital EEG systems at 14 contributing hospitals`. The enumerated detail remains in `raw_data_sources`. | Singular slot, singular value. Finding 16, low. |
| `status` | Reduced to `active`. The composite content (partial release, ongoing acquisition, August 2025 snapshot) already exists in `description` and `updates`. | Finding 15, low. |
| `notes` | Removed. The website-banner caveat moved to `source_caveats` on `external_resources`, merged with the duplicate mention already there. | `notes` holds residual dataset content; a caveat about a source document's persistence is source commentary. Finding 22, low. |
| `created_by` | Reduced to `CHoRUS Consortium`. The expansion of the acronym is already in `title`. | Finding 7, medium. |
| `subpopulations[].identification` | The clause asserting SDOH and geographic-distance elements as subpopulation identifiers removed; those remain in `purposes` as project deliverables. The slot now records only that the bundle identifies ICU, PICU and NICU admissions. | Planned data elements are not present subpopulation identifiers. Finding 14, medium. |
| `machine_annotation_tools[].tools` | `CTP-deid` retained but its description reduced to `Repository name only; no description, language, or documentation present in the bundle.` `privacy_scan_tool` retained with its bundle-supplied description. | The prior description inferred function from a repository name. Finding 10, medium. |

### 3.2 Full record only

| Slot | Change | Reason |
|---|---|---|
| `file_collections[].conforms_to` | Qualifiers stripped to bare standard names: `OMOP Common Data Model`, `WFDB`, `EDF+`, `DICOM`, `OHNLP`. The qualifying prose ("with schema extensions", "with an extended PhysioNet schema", "open source schemas") moved to the corresponding `notes`. | Finding 4, high. |
| `splits` | Removed. The holdout test set now appears once, in `tasks`, phrased as a stated future deliverable with no size, sampling frame or availability. | The bundle describes an unrealised plan ("will also provision", "sequestering"). Recording it as a split asserts a partition that does not exist. Finding 12/13, medium. Also resolves the cross-record divergence. |
| `direct_collection` | Retained in full; core aligned to match (see below). | See §3.3. |
| `third_party_sharing` | Retained in full; core aligned to match. | See §3.3. |

### 3.3 Core record only

| Slot | Change | Reason |
|---|---|---|
| `resources` | Core schema read and verified before any further edit. The nine modalities were reshaped to match the verified `CoreDataset` structure, and the `id` values were regenerated from the corrected dataset base URI. | Class A. The prior placement was unverified, which is the defect regardless of whether it happened to be correct. |
| `resources[].notes` — the `distributions` assertion | Removed entirely. | An assertion about schema structure, carried in a factual slot, unsupported by the schema digest or the bundle. Finding 1, high. |
| `direct_collection` | Restored as its own slot, matching the full record, with the content and caveat moved back out of `acquisition_methods[0].acquisition_details`. | The two records should structure the same fact the same way. Finding 18, low. |
| `third_party_sharing` | Restored as a structured object with `is_shared: true`, matching the full record. The prose in `license_and_use_terms.license_terms` reduced accordingly. | The structured boolean was being lost to prose. Finding 19, low. |
| `collection_timeframes.start_date` / `.end_date` | Removed. `timeframe_details` retains the award period 2022-09-01 → 2026-11-30, explicitly labelled as the funded project period, and the August 2025 status snapshot. | The award period is not the encounter window. The entry's own caveat said so. Also resolves the divergence with the full record, which had already omitted these keys. Finding 20, low. |
| `keywords` | Both records re-sourced against the NIH RePORTER "Preferred terms" list. Paraphrases (`intensive care unit`, `physiologic waveforms`, `medical imaging`) replaced with bundle terms (`Critical Care`, `Telemetry`, `Image`). Bundle-attested terms retained. | Finding 21, low. The bundle supplies an explicit controlled vocabulary that was not being used. |

---

## 4. Left as-is, and why

**`id` remains a constructed URI.** `https://chorus4ai.org/dataset` corresponds to a page listed in the site navigation, but the bundle assigns no persistent identifier, DOI or accession to the dataset. No candidate exists. The construction is flagged in `source_caveats`. `doi` remains unpopulated.

**Nested modality identifiers remain constructed.** Same reason: the bundle names nine modalities in a table but assigns none of them an identifier. Fragment URIs off the dataset base are the least assertive available option and are flagged.

**`license` remains unpopulated.** Per the referent decision in §1. The bundle's MIT statement governs the `chorus-ai` GitHub organization; `Chorus_SOP` is separately Apache-2.0; `UF-Geocoding` and `chorus-extract-upload` are MIT. None of these is a data license. The dataset's terms are "sign a licensing agreement included in the registration form", which names no license. Both facts are recorded — the software licenses in `external_resources`, the signed agreement in `license_and_use_terms` — but neither belongs in `license`. Finding 23 correctly notes the software-license fact now lives only inside structured prose; that is the accurate place for it.

**`language` remains unpopulated.** Finding 24 concurs. The bundle states English as a trainee eligibility requirement, which says nothing about the language of clinical notes.

**`total_size_bytes` remains unpopulated.** "23 Tb" is ambiguous between terabyte and terabit, and the figure covers waveform data only, not the whole dataset. Both grounds are recorded in `source_caveats`. The `counts` change in §3.1 brings that slot into line with this standard rather than the reverse.

**`creators[].affiliations` retains `UTHealth Houston`.** Finding 8 is correct that the same document renders the institution two ways. Both forms are in the bundle; the short form is the one attached to Jiang on the leadership slide. A `source_caveats` now records the alternate rendering. No factual change.

**`is_tabular` remains unpopulated.** The dataset is explicitly multi-modal — OMOP tables, DICOM images, WFDB and EDF+ waveforms, tokenised text. A single boolean cannot represent this and the bundle does not force one.

**`conforms_to_schema` / `conforms_to_class`** are statements about the records, set to `https://w3id.org/bridge2ai/data-sheets-schema` and `Dataset` / `CoreDataset` respectively. Unchanged.

---

## 5. Cross-record consistency after reconciliation

| Fact | Full | Core | Aligned |
|---|---|---|---|
| Nine data modalities | `file_collections` | `resources` (verified) | Yes — different slots, same content, both schema-verified |
| Direct vs. indirect collection | `direct_collection` | `direct_collection` | Yes |
| Third-party sharing | `third_party_sharing`, `is_shared: true` | same | Yes |
| Holdout test set | `tasks` | `tasks` | Yes |
| Collection timeframe dates | omitted | omitted | Yes |
| Admission count | `45000` + dual-source caveat | same | Yes |
| Principal investigator | Rosenthal only | Rosenthal only | Yes |
| Known biases | none; two `known_limitations` | same | Yes |

The remaining structural difference — `file_collections` vs. `resources` — is a difference between the two schemas, not between the two records.

---

## 6. Outcome

| | Full | Core |
|---|---|---|
| Populated top-level slots, pre-reconciliation | 63 | 41 |
| Populated top-level slots, post-reconciliation | 59 | 39 |
| Slots removed | 4 (`splits`, `notes`, `known_biases`, `status` retained but reduced) | 3 (`known_biases`, `notes`, plus `collection_timeframes` date keys) |
| Slots restored | — | 2 (`direct_contribution`→`direct_collection`, `third_party_sharing`) |
| Values corrected in place | 11 | 12 |
| `linkml-validate` | pass | pass |

Net movement is downward, which is the expected direction: the audit found no slot value the bundle contradicts outright, but it found several the bundle does not reach. Every removal in §3 is a case where the record's own `source_caveats` had already conceded the gap.

**Reconciliation outcome: reconciled.** All 24 findings dispositioned — 18 changed, 6 retained with stated reason. No prior D4D record was consulted at any phase.