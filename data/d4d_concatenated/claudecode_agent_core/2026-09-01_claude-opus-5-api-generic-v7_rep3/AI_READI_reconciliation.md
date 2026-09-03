# AI-READI D4D Reconciliation Report

**Version label:** `2026-09-01_claude-opus-5-api-generic-v7_rep3`
**Arm:** BASELINE (input documents only)
**Records reconciled:** full (`AI_READI_d4d.yaml`), core (`AI_READI_d4d_core.yaml`)
**Phase 4 status:** completed

---

## 1. What the audit found

The Phase 3 audit returned 61 findings against the full record. No fabricated facts were identified: every substantive value traced to the declared bundle, all enum members were valid against their declared enums, all `uriorcurie` values used declared prefixes correctly, and the root `source_caveats` already handled seven genuine source disagreements with explicit ranking justification.

The findings clustered into six groups:

1. **Absence-recording values** — slots whose entire content was a statement that something does not exist, which under the v2 rule has not answered the field.
2. **Arithmetic left unexplained at the point of use** — file counts and byte totals that do not reconcile against their per-collection components.
3. **Unrecorded or hedged source disagreements** — the 4%/10% longitudinal follow-up fraction and the three attested license names.
4. **Slot-fit problems** — content placed in a neighbouring field rather than the field it answers.
5. **Collapsed entities** — several distinct things in one object where the range is multivalued.
6. **Structural under-representation** — the public/controlled-access/mini-subset distinction described in prose across five fields with no `subsets` entries.

A number of findings were explicitly recorded by the auditor as confirmations that an omission or a value was deliberate and correct. Those are listed in §4.

---

## 2. Changes made to the full record

### 2.1 Absence-recording values

| Slot | Change |
|---|---|
| `content_warnings` | **Removed.** The single object's entire content was `content_warnings_present: false` plus a restatement of the healthsheet negative. |
| `data_protection_impacts` | **Removed.** The single object stated only that no DPIA had been conducted. |
| `extension_mechanism` | **Retained.** See §3. |
| `labeling_strategies` | **Removed.** The substantive fact — that the dataset is deliberately hypothesis-agnostic and ships without labels — was moved into `description`, which now reads "The dataset is deliberately hypothesis-agnostic and ships without labels or targets: no explicit label is associated with any instance, and no annotation or labeling was performed…". `instances[0].label: false` continues to carry the machine-readable form. |
| `confidential_elements` | **Retained.** See §3. |
| `retention_limit` | **Retained and strengthened.** See §3. |

### 2.2 Arithmetic

- **`source_caveats` (root), item 6** — expanded to enumerate the nine root-level metadata files that account for the 356,343 vs. 356,334 difference.
- **`source_caveats` (root), new item 7** — added, recording that the nine per-directory `total_bytes` values sum to 3,815,974,377,264 against a declared `total_size_bytes` of 3,815,969,779,678, a difference of 4,597,586 bytes that the bundle does not explain. Both figures are recorded as stated.
- **`description`** — now carries a forward reference: "…then device, then participant; see source_caveats for the arithmetic relationship between these totals and the per-directory figures."
- The subsequent root caveat items were renumbered accordingly (former item 7, release scope, is now item 8).

### 2.3 Source disagreements

- **Longitudinal follow-up fraction (4% vs. 10%)** — added as root caveat item 9. `collection_timeframes[0].timeframe_details` no longer states "Approximately 4 percent…"; its `source_caveats` now records that the healthsheet (4%) and the FAIRhub study description (10%) are of the same rank and that neither figure is stated in the details. `relationships[0]` no longer hedges as "approximately 4 to 10 percent"; the details now state only the single-visit fact, with a `source_caveats` recording both figures.
- **License name** — added as root caveat item 10. `license_and_use_terms.license_terms` now closes by naming all three attested forms and identifying which source gives each. The scalar `license` slot retains `AI-READI custom license v2.0` (FAIRhub `rightsName`), with the preference now stated.
- **Ethics reviewer / consortium roster detail** — added as root caveat item 11, recording that no single authoritative roster appears in the bundle.

### 2.4 Slot-fit corrections

| Slot | Change |
|---|---|
| `distribution_formats` | Two entries **added** at the head of the list: "FAIRhub platform download with self-attestation" (with `access_urls` for the dataset and access pages) and "Mini-subset for pipeline development". The four media-type entries were retained but each `notes` now says explicitly that it is one of the four media types recorded in the FAIRhub `format` array and describes internal use. |
| `preprocessing_strategies` | The watermarking entry was **removed** from this slot; watermarking remains in `regulatory_restrictions.regulatory_restrictions` and `participant_privacy.privacy_techniques`. |
| `cleaning_strategies[1]` | The audit-history sentence ("has not undergone any formal external audits, but has been reviewed internally…") was **removed**. The dqd_omop.json data-quality-dashboard fact was retained and expanded. |
| `use_repository[0].repository_details` | The two absence statements (no known uses; no repository links papers) were **removed**; the entry now stands on the FAIRhub usage dashboard alone, with the Dataset Impact panel added. `existing_uses` was left unpopulated. |
| `ip_restrictions.restrictions` | The trailing "reports no additional third-party intellectual property restrictions" sentence was **removed**. |
| `is_deidentified.method` | **Reordered.** The substantive method (no identifiers collected, verification performed, Safe Harbor) now precedes the FAIRhub registry code `NoDeIdentification`, which is now framed as following from it. |
| `is_deidentified.identifiers_removed` | **Added**, enumerating HIPAA Safe Harbor identifiers, sex, race and ethnicity, and medications. |
| `is_deidentified.source_caveats` | **Added**, recording that the two relevant healthsheet items returned empty and naming the sources the account was assembled from instead. |
| `external_resources[0].future_guarantees` | **Rewritten.** Previously carried a self-containment statement; now states that the bundle gives no persistence guarantee and explains why an outage would not render the data unusable. |
| `notes` (root) | The device-manufacturer loans and discounts were **moved** to `funders` as a fourth entry ("Device manufacturers providing in-kind contributions"). `notes` retains the repository-review notice and gains the internship-cohort detail. |

### 2.5 Collapsed entities separated

| Slot | Change |
|---|---|
| `distribution_dates` | One object holding all three release dates became **three objects**, each with a single ISO date in `release_dates` and a `notes` naming the version, DOI and contents. |
| `version_access.versions_available` | One string became **three list entries**, one per version. |
| `known_biases[2].affected_subsets` | One combined string became **two entries** (race/ethnicity groups; diabetes severity groups). |
| `anomalies` | The fifth entry, which bundled three device-specific issues, became **three entries** (Optomed handheld variability; Spectralis operator dependence; FLIO position in the visit and movement sensitivity). Total anomalies: 5 → 7. |
| `data_governance.stewardship_roles` | One combined string became **three entries**. |
| `at_risk_populations.special_protections` | One combined string became **three entries**. |
| `ethical_reviews` | The second entry, which bundled the four named reviewers with the Native Biodata Consortium engagement, became **two entries**. Total: 2 → 3. |

### 2.6 Structural additions

- **`subsets`** — **added** with three `DataSubset` entries: `#public`, `#controlled_access`, `#mini_subset`, each with `is_data_split: false` and `is_subpopulation: false`. This replaces reliance on prose scattered across `description`, `data_governance`, `participant_privacy`, `known_limitations` and `is_deidentified`.
- **`related_datasets`** — a fourth entry **added** for version 1.0.0 (`doi:10.60775/fairhub.1`, `is_new_version_of`), matching the treatment already given to 2.0.0. The two publication targets were retained, each with an added sentence acknowledging that the target is a journal article rather than a dataset and that `is_described_by` is the relationship the bundle attests.
- **`known_limitations`** — a sixth entry **added** (`methodological_limitation`) recording the removal of the Snellen visual acuity variables in v3.0.0.
- **`splits[0].split_details`** — **expanded** from aggregate proportions to per-split race/ethnicity, sex, diabetes-status counts and mean ages, reducing the overlap with `subpopulations[0].distribution`, which now carries only cohort-level figures and states explicitly that they are dataset-level aggregates rather than per-instance labels.
- **`variables`** — a ninth entry **added**, "Representative subset marker", explicitly flagging the preceding eight as illustrative and pointing at the full documentation. Each of the eight now carries a `notes` cross-referencing that marker. The HbA1c reference range (4.0–6.0 %) was added to `quality_notes` with an explanation of why it is not placed in `minimum_value`/`maximum_value`; the MoCA `maximum_value: 30.0` was **removed** from the numeric field and restated in `quality_notes` as an instrument property rather than an observed maximum.

### 2.7 Other corrections

| Slot | Change |
|---|---|
| `creators[0].source_caveats` | **Trimmed** to the affiliation conflict only. The descriptive material about consortium membership and institutional collaborators was moved to a new `creators[0].notes`. |
| `creators[0].principal_investigator` | **Changed** from an object with `id` and `name` to the string `Aaron Lee (ORCID:0000-0002-7452-1648)`. The v4 rule requires a scalar-ranged slot to hold an identifier reference rather than an object. |
| `funders[0].notes` | **Rewritten** to state explicitly that two RePORTER records exist for the same core project number and to distinguish them. `funders[0].grants[0].name` now carries the award number OT2OD032644 alongside the project title. |
| `acquisition_methods[0].was_inferred_derived` | **Added** as `false`, resolving the asymmetry with three populated siblings; the details now state that the healthsheet answer covers observed and self-reported acquisition only. |
| `sampling_strategies[0].is_sample` | **Changed** from `false` to `true`, resolving the contradiction with the populated `why_not_representative`. The healthsheet "all possible instances" framing was moved into `strategies` as a statement about the release within the enrolled cohort. |
| `sampling_strategies[0].representative_verification` | **Added**, recording that no verification is reported. |
| `sampling_strategies[0].strategies` | Now names the FAIRhub `samplingMethod` value "Non-Probability Sample" explicitly. |
| `raw_data_sources` | Population **evened out**: every entry now carries `source_type` and `access_details` where the bundle supports them. The EHR entry's `access_details` now states that the EHR was a recruitment-screening source, not the source of released instance data. |
| `regulatory_restrictions.confidentiality_level` | **Added** as `restricted`, derived from the access model. |
| `regulatory_restrictions.source_caveats` | **Added**, marking both `confidentiality_level` and `hipaa_compliant` as derived rather than quoted, and naming what each was derived from. |
| `data_governance.source_caveats` | **Added**, pointing at the Washington University in St. Louis / University of Washington conflict at the point where the accountable organization is asserted. |
| `data_governance.access_review_process` | **Reworded** so the current FAIRhub `PublicDownloadSelfAttestationRequired` flow is stated first and the BMJ Open "under development" statement is explicitly attributed to the protocol paper "describing the position as of its writing". |
| `at_risk_populations.at_risk_groups_included` | **Removed.** The boolean was an inference from unfilled IRB checkboxes; the `source_caveats` now says so and explains the omission. |
| `sensitive_elements` | Both entries **retained** (see §3) but their caveats rewritten: the first now states that the healthsheet reading governs for the question the slot asks, and explains that the RO-Crate list enumerates data-source categories rather than sensitive attributes, which is the likely reason the two appear to disagree. |
| `missing_data_documentation[0].handling_strategy` | **Reworded** to describe the deterministic fill-from-record procedure directly, reducing the three-way overlap with `cleaning_strategies` that prompted the `imputation_protocols` finding. |
| `citation` | **Extended** with a second paragraph recording that the operative requirement is to follow the citation instructions at `docs.aireadi.org/docs/3/citation`, and that the fixed string is the RO-Crate `associatedPublication` form. |
| `purposes` / `tasks` | The near-verbatim temporal-atlas duplication was **reduced**: `purposes` dropped from four to three entries (the foundational-dataset/temporal-atlas entry was removed, that content being carried by `tasks[1]`), and `tasks[2]` was trimmed of the label restatement now carried by `description` and `instances[0].label`. |
| `instances[0].notes` | **Extended** with a sentence stating that `data_substrate` is omitted because no single B2AI substrate term covers a multimodal instance. |
| `file_collections[1]` (clinical_data) | **`source_caveats` added**, explaining why the file count of 7 is small relative to the described content. |
| `file_collections[0]` (cardiac_ecg) | `description` extended with the ECG/EKG interchangeability note from the source. |
| `retention_limit.retention_details` | **Extended** to state that participants were not told data would be retained for a fixed period, answering the question the healthsheet was asked. |

---

## 3. Findings left as-is, and why

**`extension_mechanism`** — flagged as an absence-recording value. Retained. Unlike `content_warnings` and `data_protection_impacts`, "there is currently no mechanism for others to extend or augment the dataset outside of those involved in the project" is a positive governance statement: it tells a would-be contributor that the route does not exist and that the project team is closed. Removing it would leave a reader unable to distinguish "no mechanism" from "not documented".

**`confidential_elements`** — flagged with the same pattern. Retained on the auditor's own reasoning: for a health dataset, an explicit affirmation that no personally identifiable information is included carries information a reader wants stated rather than inferred.

**`retention_limit`** — the auditor judged retention justified here and it was retained, and additionally strengthened (§2.7).

**`raw_sources`** — flagged as absence-shaped. Retained on the auditor's own reasoning: it carries the forward-looking fact that raw data may appear in future controlled-access releases, which is substantive.

**`sensitive_elements` two contradictory booleans** — both entries retained. The two are tier-1 sources of equal rank; the uniform decision rules direct representing what the evidence states rather than selecting one. The caveats were rewritten to say which reading governs for the slot's question and to record the auditor's observation about what each source is enumerating.

**`discouraged_uses`** — omission confirmed. The healthsheet answers the discouraged-use question by pointing at licence restrictions already captured in `prohibited_uses`; populating both would duplicate.

**`other_tasks`** — omission confirmed. The material is weaker than what `tasks` and `intended_uses` already carry.

**`existing_uses`** — remains omitted. Per the v2 rule, a value recording that no uses exist has not answered the field; the negative statement was removed from `use_repository` rather than relocated.

**`imputation_protocols`** — remains omitted. The deterministic fill-from-record procedure is a quality-control step rather than a statistical imputation protocol; the three-way overlap was reduced by rewording `missing_data_documentation.handling_strategy` instead.

**`download_url`** — remains omitted. The DOI resolver is not a direct data URL and the access page is a gated workflow. The access route is now carried in `distribution_formats[0].access_urls` as well as `data_governance`.

**`compression`, `errata`, `was_derived_from`, `created_on`, `last_updated_on`, `modified_by`, `annotation_analyses`, `machine_annotation_tools`, `parent_datasets`, `resources`, `data_governance.committee_contact` / `committee_members` / `appeal_process` / `access_decision_timeframe`** — all omissions confirmed by the audit as correct. No change.

**`file_collections[*].id` fragments** — the v6 concern was that no value pointed at them. `id` is required on `FileCollection`, so they cannot simply be dropped; the fragments remain the least-bad way to satisfy the requirement while keeping the label traceable to the attested dataset DOI. The same minting pattern was applied to the new `subsets` entries for consistency.

**`total_file_count` / `total_size_bytes` values themselves** — unchanged. Both are as the tier-1 FAIRhub API states them. Only the explanation of the arithmetic was added.

**`hipaa_compliant: compliant`** — retained rather than omitted, with a `source_caveats` recording that it is derived from the stated Safe Harbor de-identification rather than from an explicit compliance determination.

**`participant_compensation[0].compensation_amount`** — retained as `200 US dollars`. The IRB caveat that the amount may change in future years was added to `notes`.

**`is_tabular: false`, `instances[0].data_topic`, `instances[0].label`, `conforms_to_schema` / `conforms_to_class`, all `bias_type` and `limitation_type` enum values, `version_access.latest_version_doi` CURIE form, `keywords` normalization, `file_collections[*].collection_type`, `file_collections[*].conforms_to` + `conforms_to_standard` pairing, `creators[0].affiliations[0]` without `id`, `funders[0].grants[0].id` as a resolver URL, `human_subject_research.irb_approval` date, `collection_mechanisms` non-collapsing, `informed_consent[0].consent_type` ordering, `updates.frequency`** — all confirmed correct by the audit. No change.

---

## 4. Core record

The core record was re-derived by projection from the reconciled full record. Every change listed in §2 that touches a slot present in `CoreDataset` propagates identically. Specifically the core record now carries: the seven-entry `anomalies` list; three-entry `distribution_dates`; three-entry `versions_available`; the six-entry `known_limitations`; the split `affected_subsets`; the three-entry `stewardship_roles` and `special_protections`; the three-entry `ethical_reviews`; the six-entry `distribution_formats` including the two access-route entries; `is_deidentified.identifiers_removed` and its `source_caveats`; `regulatory_restrictions.confidentiality_level` and its `source_caveats`; `data_governance.source_caveats`; `sampling_strategies.is_sample: true` and `representative_verification`; `acquisition_methods.was_inferred_derived: false`; the evened-out `raw_data_sources`; the fourth `funders` entry; the four-entry `related_datasets`; the expanded root `source_caveats` and `description`; and the removal of `content_warnings`, `data_protection_impacts`, `labeling_strategies`, `extension_mechanism`'s… — correction: `extension_mechanism` was retained in the full record and is **absent** from the reconciled core record, as `subsets`, `splits`, `variables`, `purposes`-adjacent trims and other full-only material are handled per the core schema's slot inventory.

Slots present in the full record but not projected into core in this pass: `subsets`, `splits`, `variables`, `notes`-only content that has no core counterpart, and `extension_mechanism`.

---

## 5. Validation

| Record | Class | Result |
|---|---|---|
| `AI_READI_d4d.yaml` | `Dataset` | valid |
| `AI_READI_d4d_core.yaml` | `CoreDataset` | valid |

---

## 6. Outcome

| Metric | Value |
|---|---|
| Full record populated slots | 74 |
| Core record populated slots | 55 |
| Findings addressed by change | 43 |
| Findings left as-is with rationale | 18 |
| Fabricated facts found | 0 |
| Both records validate | yes |