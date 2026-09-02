# Reconciliation Report — AI_READI D4D Records

**Version label:** `2026-09-01_claude-opus-5-api-generic-v7_rep3`
**Records reconciled:** full (`Dataset`) and core (`CoreDataset`)
**Audit findings reviewed:** 60

---

## 1. Summary of the audit

The Phase 3 audit found no fabricated facts. Every substantive value traced to the declared bundle; identifiers used declared prefixes correctly (`doi:`, `ORCID:`, `ROR:`, `B2AI_TOPIC:`); all enum values were members of their declared enums. The defects fell into five groups:

1. **Absence-recording values** — slots whose entire content was a statement that something does not exist.
2. **Unexplained arithmetic** — file-count and byte-total discrepancies noted in one place but not at the point of use, or not at all.
3. **Unrecorded source disagreements** — the 4% versus 10% longitudinal follow-up fraction, and three attested license names.
4. **Slot-fit and collapsing problems** — content in a neighbouring field, several entities in one object.
5. **Structural under-representation** — the public/controlled-access split described in prose but not represented as `subsets`.

Both records were revised. The core record is a projection of the reconciled full record, so every change below that touches a slot present in the core schema propagated to the core record; changes to slots absent from the core schema (`splits`, `subsets`, `variables`, `citation`, `total_file_count`, `total_size_bytes`, `collection_consents`, `consent_revocations`, `collection_notifications`, `participant_privacy`, `participant_compensation`, `direct_collection`, `relationships`, `third_party_sharing`, `file_collections`) touched the full record only, except where the core's `distributions` slot mirrors `file_collections`.

---

## 2. Changes made

### 2.1 Absence-recording values removed

Four slots consisted solely of a statement that something does not exist. Under the v2 rule, a value recording absence has not answered the field.

| Slot | Action | Where the content went |
|---|---|---|
| `content_warnings` | **Removed from both records.** | Nothing retained; the healthsheet's negative answer carried no information a reader needs. |
| `data_protection_impacts` | **Removed from both records.** | Nothing retained. |
| `extension_mechanism` | **Removed from both records.** | Nothing retained. |
| `labeling_strategies` | **Removed from both records.** | The substantive fact — the dataset is deliberately hypothesis-agnostic and ships without labels or targets, no annotation performed — was moved into `description`, where it now appears as its own sentence. `instances[0].label: false` already carried the machine-readable form. |

`confidential_elements` was **retained** in both records despite the same shape. The audit itself judged retention defensible here: for a health dataset, the affirmative statement that no personally identifiable information is included is information a reader wants, not merely a null answer.

`retention_limit` and `raw_sources` were likewise **retained**, as the audit recommended: "no limits on retention" is a substantive policy statement, and the raw-sources entry carries the forward-looking fact that raw data may appear in future controlled-access releases.

### 2.2 Arithmetic discrepancies documented

**File counts (finding: high).** The root `source_caveats` item (6) was expanded to enumerate the nine root-level metadata files that account for the 356,334 → 356,343 difference. The `description` now carries a forward reference: "see source_caveats for the arithmetic relationship between these totals and the per-directory figures."

**Byte totals (finding: medium, previously unexplained anywhere).** A **new caveat item (7)** was added to the root `source_caveats`, stating that the nine directory sizes sum to 3,815,974,377,264 bytes against a declared `total_size_bytes` of 3,815,969,779,678 — a difference of 4,597,586 bytes — that the bundle does not explain the discrepancy, and that both figures are recorded as stated. The subsequent caveat items were renumbered.

### 2.3 Source disagreements recorded

**Longitudinal follow-up fraction (4% vs 10%).** Three changes:
- New root caveat item (9) recording that NIH RePORTER and the FAIRhub study description both say 10% while the healthsheet says approximately 4%; since the healthsheet and FAIRhub study description are the same rank, both figures are recorded rather than one selected.
- `collection_timeframes[0].timeframe_details` — the sentence "Approximately 4 percent of participants are expected to undergo a follow-up examination in year 4" was **removed** from the details, and the entry's `source_caveats` now records both figures and why neither is stated in the details.
- `relationships[0]` — the hedged range "approximately 4 to 10 percent" was **removed** from `relationship_details`, which now says only that there is currently one visit per participant; a `source_caveats` on that entry records the two figures and their sources.

**License name (three attested forms).** The scalar `license` slot was left at `AI-READI custom license v2.0` (the tier-1 FAIRhub `rightsName`), but a **new root caveat item (10)** records all three forms and states which was preferred, and `license_and_use_terms.license_terms` now ends with a sentence enumerating all three.

**Data governance institutional conflict (finding: high).** `data_governance` was previously unqualified while the root caveat documented the Washington University in St. Louis / University of Washington conflict. A `source_caveats` was **added to the `data_governance` object** stating that the accountable organization follows the FAIRhub structured metadata, that the conflict is unresolved in the sources, and that it is also recorded at the record root.

**Sensitive elements contradiction (finding: medium).** Both `SensitiveElement` entries were retained — the disagreement is real and same-rank — but their caveats were rewritten. The first now states explicitly that **the healthsheet reading governs** for the question the slot asks, and both caveats now record the audit's observation that the RO-Crate `rai:personalSensitiveInformation` list enumerates *data-source categories* rather than sensitive attributes, which is the likely reason the two appear to disagree.

**Derived enum values (findings: medium).** `regulatory_restrictions` gained a `source_caveats` stating that two values there are derived rather than quoted: `hipaa_compliant: compliant` is inferred from the Safe Harbor de-identification statement (no source uses compliance language), and the newly added `confidentiality_level: restricted` is inferred from the access model (the RO-Crate's own term is "HL7:2N (normal)").

### 2.4 Slot-fit corrections

| Slot | Change |
|---|---|
| `preprocessing_strategies` | The watermarking entry was **removed** (it is a distribution-security control, already carried in `regulatory_restrictions` and `participant_privacy`). The slot now has four entries in both records rather than five. |
| `cleaning_strategies[1]` | The external-audit sentence was **removed**; the entry now covers only central QC and the OMOP DQD file. |
| `ip_restrictions.restrictions[0]` | The trailing absence-recording sentence ("reports no additional third-party intellectual property restrictions") was **removed**. |
| `use_repository[0].repository_details` | The self-contradicting "no repository links papers" statement and the citation requirement were **removed**; the entry now stands on the FAIRhub usage dashboard alone, and its description was expanded with the Dataset Impact panel fields. |
| `distribution_formats` | Two **new entries added at the head**: the FAIRhub platform download route (with `access_urls` for both the dataset page and the access page) and the mini-subset for pipeline development. The four media-type entries were retained but their notes now say explicitly that these are internal file formats within the distributed dataset. |
| `external_resources[0].future_guarantees` | Rewritten: it previously restated self-containment; it now says the bundle states no persistence guarantee and explains why a documentation outage would not render the data unusable. |
| `citation` | The operative requirement — follow the instructions at `docs.aireadi.org/docs/3/citation` — was **added** below the RO-Crate citation string. (Full record only; `citation` is not in the core record.) |
| `notes` (root) | The device-manufacturer loans and discounts were **moved out** to a new `funders` entry; `notes` now carries the repository-review notice and the internship-programme detail. |

### 2.5 Collapsed entities separated

| Slot | Before | After |
|---|---|---|
| `distribution_dates` | One object, one string naming three releases | **Three objects**, each with an ISO date in `release_dates` and its own notes |
| `version_access.versions_available` | One string listing three versions | **Three list entries**, one per version |
| `known_biases[2].affected_subsets` | One string naming two subset families | **Two entries** |
| `anomalies` | Five objects, the fifth mixing three device-specific issues | **Seven objects**: Optomed, Spectralis and FLIO now separate |
| `data_governance.stewardship_roles` | One string | **Three entries** |
| `ethical_reviews[1]` | One object mixing the four named reviewers with the Native Biodata Consortium engagement | **Two objects**; see §2.6 |
| `variables` | Eight objects, unmarked as a subset | **Nine objects** — a ninth scope-marker entry states that this is a representative subset, names what is omitted, and points at the documentation. (Full record only.) |
| `raw_data_sources` | Uneven field population | All nine entries now carry `source_type` and `access_details`; the EHR entry's access note records that it was used for recruitment screening only |

### 2.6 Ethical reviews restructured

The audit flagged `ethical_reviews[1].reviewing_organization: "AI-READI ethics team"` as a coined body name for what the RO-Crate presents as a list of four individuals. The entry was **split into two**:

- The four named reviewers now appear in an entry with **no `reviewing_organization`** (the bundle names no body), a `contact_person` of Camille Nebeker, and a `notes` explaining why no organization name is recorded and why she was chosen as contact.
- The Native Biodata Consortium engagement is now its **own entry** with `reviewing_organization: Native Biodata Consortium`, and its notes state that it concerns prospective governance for American Indian and Alaska Native communities and that no such cohort data are in v3.0.0.

The University of Washington IRB entry was unchanged.

### 2.7 Sampling strategy made coherent

The audit found `sampling_strategies[0]` asserting `is_sample: false` while populating `why_not_representative`, which presupposes a sample. Changes:

- `is_sample` changed from `false` to **`true`** — the cohort is a non-probability sample of the study base already named in `source_data`.
- `strategies` now opens by citing the FAIRhub `samplingMethod: "Non-Probability Sample"` and closes with the healthsheet's "all possible instances" framing scoped correctly to the enrolled cohort.
- `representative_verification` **added**, recording that the healthsheet reports no validation procedure.

### 2.8 Structural additions

**`subsets` added (full record only; not in the core schema's slot set).** Three `DataSubset` entries with minted fragment identifiers:
- `#public` — the release the counts, sizes and DOI describe
- `#controlled_access` — enumerating the held-back variables and the DUA requirement
- `#mini_subset` — the pipeline-development child dataset (FAIRhub child id 4)

This gives the public/controlled distinction a structural home rather than leaving it distributed across five prose fields.

**`is_deidentified` reordered and completed.**
- `method` was reordered so the substantive account (no identifiers collected, Safe Harbor, verification performed) **precedes** the registry code `"NoDeIdentification"`, which previously opened the field and read as a claim that no de-identification occurred.
- `identifiers_removed` **added** as a four-item list, surfacing what was previously only in prose.
- The healthsheet's empty answers are now recorded in a `source_caveats` rather than trailing the details field.

**`related_datasets` completed.** An `is_new_version_of` entry for **version 1.0.0** was added (previously only 2.0.0 was linked). The two publication targets were retained — `is_described_by` is the relationship the bundle attests and `target_dataset` is required — but each description now states explicitly that the target is a journal article rather than a dataset.

**`known_limitations` extended.** A sixth entry, `methodological_limitation`, records the dropping of Snellen visual acuity variables in v3.0.0.

**`funders` extended.** A fourth entry records the device manufacturers' in-kind contributions (loans at no cost, research discounts), moved out of root `notes`.

### 2.9 Smaller corrections

- `acquisition_methods[0].was_inferred_derived` **set to `false`** with the asymmetry explained in `acquisition_details` (the healthsheet answer covers observed and self-reported only).
- `at_risk_populations.at_risk_groups_included` **removed** — the audit noted it was derived from unfilled checkboxes; the `source_caveats` now explains the omission and the three `special_protections` were split into separate entries.
- `subpopulations[0]` — `identification` and `distribution` rewritten to explain why `subpopulation_elements_present: false` coexists with published aggregate counts (cohort-level aggregates, not per-instance labels).
- `splits[0].split_details` expanded with per-split race/ethnicity, sex and diabetes-status counts, so the split figures live here and the cohort figures live in `subpopulations`.
- `variables` — HbA1c now carries the 4.0–6.0% reference range in `quality_notes` with an explanation of why it is not in `minimum_value`/`maximum_value`; MoCA's `maximum_value: 30.0` was **removed** from that field and the 30-point maximum moved to `quality_notes` as an instrument property rather than an observed maximum.
- `creators[0].source_caveats` trimmed to the affiliation conflict alone; the descriptive material moved to a new `notes` field on the same object, expanded with the institutional collaborator list.
- `funders[0].grants[0].name` now includes the award number OT2OD032644, and `notes` states that two RePORTER records exist for the same core project number rather than presenting them as one continuous fact.
- `missing_data_documentation[0].handling_strategy` rewritten to state what happened when a fill was not possible.
- `data_governance.access_review_process` now attributes the "under development" Data Access Committee statement to the BMJ Open protocol paper explicitly and dates it, so it does not read as current.
- `regulatory_restrictions.notes` rewritten to say the HL7 term is recorded "here in prose" now that `confidentiality_level` is populated.
- `participant_compensation[0].notes` gained the IRB protocol's statement that the amount may change in future years.
- `purposes` reduced from four to three: the temporal-atlas purpose was removed as near-verbatim duplicate of `tasks[1]`. `tasks[1]` and `tasks[2]` were tightened; the "no predefined labels" sentence moved to `description`.
- `cleaning_strategies[1]` now describes the DQD tool rather than just the file.
- `file_collections[1]` (clinical_data) gained a `source_caveats` explaining why 7 files is plausible for an OMOP CDM instance.
- Root `source_caveats` gained item (11) noting that consortium membership and reviewer affiliations are given at differing detail across sources with no authoritative roster.

---

## 3. Findings left as-is

| Finding | Why unchanged |
|---|---|
| `conforms_to_standard` enum membership | The audit confirmed all values valid; recorded for completeness only. No defect. |
| `creators[0].affiliations[0]` lacking `id` | The audit confirmed the AI-READI Consortium has no identifier in the bundle; omitting `id` is correct. |
| `funders[0].grants[0].id` as resolver URL | No NIH RePORTER prefix is declared in the schema digest, so a resolvable URL is the correct fallback under the v5 rule. The award number was surfaced in `name` instead. |
| `instances[0].data_substrate` omitted | Confirmed deliberate; a note in `instances[0].notes` now says so explicitly. |
| `human_subject_research.irb_approval` date | Checked against the collection timeframe and award start; consistent, no conflict. |
| `download_url` omitted | The DOI resolver is not a direct data URL and the access page is a gated workflow. The access route is now also carried in `distribution_formats`. |
| `compression` omitted | Nothing in the bundle states a compression format. |
| `existing_uses` omitted | The only evidence is a negative statement; under the v2 rule the slot stays omitted. The sentence was trimmed from `use_repository` instead. |
| `discouraged_uses` omitted | The healthsheet answers the discouraged-use question by pointing at the license restrictions, already in `prohibited_uses`. Split retained. |
| `other_tasks` omitted | Weaker than material already in `tasks` and `intended_uses`. |
| `annotation_analyses`, `machine_annotation_tools` omitted | Consistent with no labeling having been performed. |
| `imputation_protocols` omitted | The fill-from-record step is deterministic and is now recorded once, in `missing_data_documentation.handling_strategy` and `cleaning_strategies[0]`; the audit judged it a borderline call. |
| `parent_datasets`, `resources` omitted | The RO-Crate subcrates are represented as `file_collections`, which the slot description directs. |
| `errata` omitted | The healthsheet's erratum answer was empty in the bundle. |
| `was_derived_from` omitted | The EHR is a recruitment source, not a derivation source; instances were collected prospectively. |
| `created_on`, `last_updated_on`, `modified_by` omitted | The only timestamps in the bundle are the publication date, already in `issued`. |
| `is_tabular: false` | Correct for a mixed-modality dataset. |
| `keywords` normalization | Single normalized "Retinal imaging" entry is correct. |
| `data_governance.committee_contact`, `committee_members`, `appeal_process`, `access_decision_timeframe` | The bundle names a Data Access Committee but gives no membership, contact, appeal route or timeframe. |
| `conforms_to_schema` / `conforms_to_class` | Correctly distinguished from `conforms_to`. |
| `file_collections[*].id` fragments | `id` is required on `FileCollection`, so the fragments must exist. They are now pointed at by the core record's `distributions` entries, which mirror them. |
| `file_collections[*].collection_type: processed_data` | Accurate and consistent across all nine. |
| `file_collections[*].conforms_to` / `conforms_to_standard` pairing | The prose-plus-enum pattern is what the digest asks for; the two agree in every case. |
| `collection_mechanisms` (twelve entries) | Correctly one object per instrument family. |
| `known_biases[*].bias_type`, `known_limitations[*].limitation_type` | All values are declared enum members. |
| `instances[0].data_topic: B2AI_TOPIC:43` | Correct CURIE form, apt term. |
| `instances[0].label: false` | Consistent with the hypothesis-agnostic design. |
| `instances[0].missing_information` omitted | Duplication risk either way; top-level placement retained. |
| `informed_consent[0].consent_type` | Substantive content precedes the registry code; acceptable as ordered. (Minor wording added: "registry consent type".) |
| `version_access.latest_version_doi` | Correct `doi:` CURIE form. |
| `updates.frequency` | Matches both sources. |
| `external_resources[*].archival` omitted | Nothing in the bundle states whether the documentation is archived. |
| `description` totals | Now cross-references the root caveat, which was the audit's suggested remedy. |

---

## 4. Validation

Both files were validated after reconciliation:

- Full record — `linkml-validate -s data_sheets_schema_all.yaml -C Dataset` — **passed**
- Core record — `linkml-validate -s data_sheets_schema_core_all.yaml -C CoreDataset` — **passed**

---

## 5. Outcome

**Reconciled.** All 60 audit findings were dispositioned: those recording a genuine defect were repaired in one or both records; those recorded for completeness or confirming a deliberate omission were left as-is with the reasoning above. The two records remain consistent with one another — the core record is a projection of the reconciled full record, and every slot the core schema shares with the full schema carries the same reconciled content.