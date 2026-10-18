# Reconciliation Report — AI_READI D4D Records

**Version label:** 2026-08-28c_claude-opus-5-api-generic-v7_rep1
**Records:** full (`Dataset`) and core (`CoreDataset`)
**Phase:** 4 — strict reconciliation of Phase 3 audit findings against the Phase 1 full record and Phase 2 core record

---

## 1. Overview

The Phase 3 audit returned 48 findings. Three were withdrawn by the auditor during re-check (`conforms_to_standard` enum membership at top level, the same at `file_collections`, and the `errata` omission). Of the remainder, the substantive defects fell into five groups: an undeclared key on every `variables` object; entity collapsing in `external_resources` and `creators`; enum values reasoned to rather than transcribed; supported omissions of stated negatives; and internal contradictions between sibling fields.

Both records were revised. The core record was re-derived by projection from the reconciled full record so that every change below appears in both, except where a slot has no counterpart in `CoreDataset`.

---

## 2. Findings acted on

### 2.1 `variables[*].description` — undeclared key (high)

**Finding:** `VariableMetadata` declares `variable_name` (required) plus `categories`, `data_type`, `derivation`, `examples`, `is_identifier`, `is_sensitive`, `maximum_value`, `measurement_technique`, `minimum_value`, `missing_value_code`, `notes`, `precision`, `quality_notes`, `source_caveats`, `unit`. It does not declare `description`. All eleven variable objects carried one.

**Action:** `description` was removed from all eleven objects. The content was redistributed into declared fields:

- `cgm_glucose` — "Interstitial blood glucose measurement" folded into `measurement_technique`.
- `hba1c` — "a marker for diabetes" folded into `measurement_technique`; the reference range 4.0–6.0% moved from prose in `notes` into `minimum_value: 4.0` / `maximum_value: 6.0`, with `notes` now stating explicitly that these are the laboratory reference range and not the observed range.
- `heart_rate`, `oxygen_saturation`, `moca_total_score`, `best_corrected_visual_acuity_logmar`, `contrast_sensitivity_logcs` — descriptive content folded into `measurement_technique`.
- `best_corrected_visual_acuity_logmar` — the Snellen-dropped statement moved from `notes` to `quality_notes`, which is the field for it.
- `diabetes_status_group`, `recommended_split`, `race_ethnicity`, `zip_code_5_digit` — descriptive content folded into `notes`.

This finding was the record's only validation blocker.

### 2.2 `variables` — coverage disclosure (medium)

**Finding:** Eleven variables documented from a dataset spanning more than ten domains, with no statement that the list is illustrative.

**Action:** A `source_caveats` was added to the final variable object stating that the eleven are exemplars, not the complete inventory, and pointing to the bundle's own statement that a full variable list and per-domain documentation live at `https://docs.aireadi.org`.

### 2.3 `external_resources` — entity collapsing (high, medium)

**Finding:** Six distinct resources packed into one prose string in the first object; two publications plus a trial registration and a grant record collapsed into a second object and its `notes`.

**Action:** The two objects were split into ten, one per resource: the documentation site, the project website, the Zenodo community, the GitHub organization, the CDS specification, the license record, the Nature Metabolism comment, the BMJ Open protocol, the ClinicalTrials.gov registration, and the NIH RePORTER project record. The CC-BY restriction stays on the documentation object where it belongs; `archival: false` is carried on each.

### 2.4 `creators[0].affiliations[0]` — misplaced organization (high)

**Finding:** The AI-READI Consortium — the creator itself, per the FAIRhub DataCite record — was placed as an *affiliation* of an unnamed creator whose only substantive field was `principal_investigator`.

**Action:** The affiliation was changed to Washington University in St. Louis (`ROR:01yc7t268`), which the bundle attests as the affiliation of the responsible party, the lead sponsor, and Aaron Lee. The Consortium's role as creator and publisher is now stated in `notes`. The `source_caveats` was rewritten to record the RO-Crate/FAIRhub affiliation conflict and to note explicitly that Aaron Lee is named as principal investigator of the study rather than as an individual dataset creator.

### 2.5 `creators[0].principal_investigator` and `data_governance.committee_contact` — range violations (high, per v4 rule)

**Finding (extension of 2.4):** `principal_investigator` has declared range `Person`; the original supplied an object. Under the v4 rule, a scalar-ranged slot takes an identifier, not an object.

**Action:** `principal_investigator` is now the scalar `Aaron Lee`; the ORCID moved to `notes`. The same treatment was applied to `data_governance.committee_contact`, newly added as the scalar `Aaron Lee` (FAIRhub names him as central contact at contact@aireadi.org), with the ORCID in `notes`. `ethical_reviews[1].contact_person` is likewise a scalar.

### 2.6 `regulatory_restrictions.confidentiality_level` and `.hipaa_compliant` — reasoned values (medium)

**Finding:** `restricted` was derived by the record's own argument while the only attested label is the RO-Crate's `HL7:2N (normal)`; `compliant` is a formal determination the bundle never makes.

**Action:** Both enum slots were removed. The attested facts — the HL7 confidentiality label, the FAIRhub HIPAA identifier check, and the Nature Metabolism Safe Harbor statement — were moved into `other_compliance`. A new `source_caveats` explains that the enums were left unpopulated because no bundle value maps onto their permitted terms.

### 2.7 `ethical_reviews[1].reviewing_organization` — invented label (medium)

**Finding:** "AI-READI ethics team" is not an organization the bundle names; the RO-Crate `ethicalReview` field lists four individuals.

**Action:** `reviewing_organization` was removed from that object. `contact_person: Camille Nebeker` was added as the first-named reviewer, all four names are stated in `review_details`, and a `source_caveats` explains that the class carries a single contact person while the source lists four.

### 2.8 Five supported omissions of stated negatives (medium × 5)

Each was a fact the bundle asserts explicitly and the record dropped. All five slots were added:

| Slot | Value added |
|---|---|
| `extension_mechanism` | No mechanism exists for outside parties to extend the dataset |
| `existing_uses` | Documentation answers "has it been used for any tasks already?" with "No" |
| `use_repository` | Documentation answers "is there a use-tracking repository?" with "No" |
| `data_protection_impacts` | "No, a data protection impact analysis has not been conducted." |
| `labeling_strategies` | No labeling performed; RO-Crate `rai:dataAnnotationProtocol` is "N/A — no labels are provided"; no labeling software; no guidelines for future label creation |

### 2.9 `subpopulations[0]` — boolean contradicting sibling content (medium)

**Finding:** `subpopulation_elements_present: false` asserted alongside a populated `distribution` enumerating race/ethnicity, sex and diabetes-status counts.

**Action:** The boolean was changed to `true`. `identification` now states which subpopulations are defined and that individual-level values are withheld from the public tier; `distribution` carries the aggregate counts; `source_caveats` records that the healthsheet says "No" while the README publishes the counts, and that both statements are represented.

### 2.10 `sensitive_elements` — contradictory booleans across list entries (medium)

**Finding:** Two objects asserting `false` and `true` with nothing but prose distinguishing the tiers; the second describes the controlled-access tier, which is not the referent this record selected.

**Action:** The second object was removed. The single remaining object asserts `false` for the public v3.0.0 release, and its `notes` states that a separate controlled-access tier — explicitly not the dataset described by this record — holds the sensitive variables. This preserves the fact while removing the contradiction and the referent drift.

### 2.11 `splits` / `subsets` — prose blob split into structured subsets (medium)

**Finding:** Per-partition and per-stratum counts were one prose blob in `splits[0].split_details` while `subsets` (`DataSubset[]`, `is_data_split`) exists for exactly this.

**Action:** Three `subsets` entries were added — `#split-train`, `#split-validation`, `#split-test` — each with `is_data_split: true` and its own counts by race/ethnicity, sex, diabetes status and mean age. `splits[0].split_details` retains the split rationale and proportions; its `notes` points to `subsets` for the counts. The three fragment identifiers are minted on the dataset DOI per the v5/v6 rules, and each is pointed at by the split narrative.

### 2.12 `instances[0].data_substrate` — supported omission (medium)

**Finding:** `Instance` permits `data_substrate` and the bundle names substrates explicitly per datatype; the slot was omitted.

**Action:** `data_substrate: B2AI_SUBSTRATE:11` (DICOM) was added — the substrate of the largest share of the release by file count and volume. Because the slot is single-valued, `notes` enumerates the remaining attested substrates (waveform, CSV/JSON, time-series glucose and activity, delimited text), and `source_caveats` explains why only one term appears.

### 2.13 `collection_timeframes[0].end_date` — field meaning versus value (medium)

**Finding:** The value is the release cut-off while the field name means the collection period, and the bundle says enrollment is ongoing to 2027.

**Action:** The date was kept (the bundle supplies no other end value for this release) but `timeframe_details` now states explicitly that the end date is the data cut-off for this release rather than the end of study collection, which is ongoing. `source_caveats` adds the anticipated completion date of 1 January 2027 alongside the existing BMJ discrepancy note.

### 2.14 `acquisition_methods[0].was_inferred_derived` — unset flag (low)

**Action:** Left unset, as before, but a `source_caveats` was added explaining that the bundle's account addresses only direct observation and subject report and makes no statement about inference or derivation.

### 2.15 `notes` — residue rule (medium)

**Finding:** The top-level `notes` carried return-of-results procedures, incidental-findings referrals, and the biorepository description, for which better homes exist.

**Action:** The return-of-results and incidental-findings content moved into `description`. The biorepository content stays in `notes` but is reframed to state that those biospecimens are not part of this dataset. The genuine residue — the "under review for potential modification" banner and the FAIRhub beta status — remains.

### 2.16 `license` and `license_and_use_terms` — undisclosed name divergence (medium)

**Action:** The `license` value is unchanged ("AI-READI Data License Agreement v2.0", as the license document titles itself). A `source_caveats` was added to `license_and_use_terms` recording that the tier-1 FAIRhub `rights` block gives `rightsName: "AI-READI custom license v2.0"` and that the license document's own title was preferred.

### 2.17 `ip_restrictions.restrictions` and `regulatory_restrictions.regulatory_restrictions` — collapsed lists (low)

**Action:** Each single-element prose blob was split into distinct entries: four for IP (title/ownership; derivative data; synthetic data; licensee models) and four for regulatory (license reference; NIH GDS security policy; general legal compliance; storage-location restriction).

### 2.18 `at_risk_populations.special_protections` — mixed content (medium)

**Action:** Split into two entries — eligibility limits, and transportation assistance. The accessibility statement ("Accessibility measurements were not specifically assessed") moved to `notes`.

### 2.19 `maintainers[0]` and `data_governance` — contact placement (medium)

**Action:** The contact address, contact form and version-specific contact URL moved from `maintainer_details` prose into `maintainers[0].notes`. `data_governance` gained `committee_contact: Aaron Lee` with the contact address and ORCID in its `notes`.

### 2.20 `related_datasets[1].relationship_type` — semantic overreach (medium)

**Action:** Changed from `is_new_version_of` to `is_version_of` for v1.0.0. The description now states that v2.0.0 is the immediate predecessor and v1.0.0 precedes both. The v2.0.0 relation remains `is_new_version_of`.

### 2.21 `participant_compensation[0].compensation_amount` — currency in a value string (medium)

**Action:** Changed from `USD 200` to `'200'`; the currency moved into `compensation_type` ("Cash stipend in US dollars"). The IRB qualification that the amount may change in future years was added to `compensation_rationale`.

### 2.22 `file_collections[1].is_tabular` (low, arising from 2.1's shape review)

**Action:** `is_tabular: true` on the `clinical_data` collection was replaced with a `notes` statement that the files are tabular, keeping the boolean claim at the dataset level only.

### 2.23 `distribution_dates[0].release_dates` (low)

**Action:** Converted from a scalar string to a single-element list.

### 2.24 `source_caveats` — orphaned and missing items

**Action:** Item (3) now states explicitly that `errata` is omitted because the healthsheet question was blank. Item (4) now says that neither acronym expansion is used in this record's prose, so the caveat annotates an absence rather than a value. A new item (6) records the two arithmetic inconsistencies present in the bundle itself: `file_collections` byte totals exceeding `total_size_bytes` by ~4.3 MB, and file counts falling nine short, consistent with the nine root-level CDS metadata files.

---

## 3. Findings left as-is

### 3.1 Withdrawn by the auditor

Three findings were withdrawn during Phase 3 re-check and required no action: `conforms_to_standard` enum membership at the top level, the same at `file_collections`, and the `errata` omission. All permitted values used (`CDS`, `WFDB`, `OMOP_CDM`, `DICOM`, `OPEN_MHEALTH`, `ESDS`, `RO_CRATE`) appear in the schema digest's `DataStandardEnum`.

### 3.2 Confirmations requiring no change

- **`data_governance.accountable_organization.id`** — `ROR:01yc7t268` is correct CURIE form for `uriorcurie` and is attested in the bundle. Unchanged.
- **`data_collectors[*].role`** — not enum-constrained in the digest (only `Maintainer.role` is), so the free-text values conform. Unchanged.
- **`maintainers[0].role`** — `academic_institution` is a permitted `Maintainer.role` value. Unchanged.
- **`annotation_analyses`** — correctly omitted; no annotation was performed, so there is no agreement to analyze.
- **`imputation_protocols`** — the imputation fact ("Missing values were not imputed") sits in `missing_data_documentation[0].handling_strategy`. The auditor judged this defensible and no repair required. Unchanged.
- **`machine_annotation_tools`**, **`compression`**, **`resources`**, **`parent_datasets`**, **`created_on`**, **`last_updated_on`**, **`modified_by`**, **`was_derived_from`** — all correctly omitted per the audit. Unchanged.
- **`description`** — well-formed and grounded; the audit found no defect. It was extended (§2.15) but not corrected.
- **`total_file_count`** and **`total_size_bytes`** — the arithmetic observations are inconsistencies in the tier-1 source, not record defects. Values unchanged; the inconsistency is now disclosed in `source_caveats`.

### 3.3 Kept despite the finding

- **`instances` — single Instance flattening a multimodal dataset (low).** `Instance.data_topic` is single-valued, so multiple topics cannot be carried on one object, and splitting into several Instances would misrepresent the instance unit, which the bundle states unambiguously as one participant. Left as one object; the `data_substrate` limitation is now disclosed (§2.12).
- **`file_collections` ids serving no referential purpose (medium).** The ARKs are attested in the RO-Crate rather than minted, so the v5/v6 minting rules do not reach them, and `FileCollection.id` is required. Retained.
- **`publisher` as a bare root URL (medium).** `publisher` is `uriorcurie`; the bundle gives `publisherName: "FAIRhub"` with no registry identifier, and no declared prefix covers FAIRhub. The `uri` half of the range is the correct fallback. Unchanged.
- **`id` and `target_dataset` DOI CURIE form (high, flagged for verification).** `id` is `uriorcurie` and `doi:10.60775/fairhub.3` is correct CURIE form. `target_dataset` is a required key on `DatasetRelationship` whose range the digest does not state; the `doi:` form was retained on both entries pending schema verification, and validation will settle it.
- **`human_subject_research.irb_approval` / `regulatory_compliance` / `special_populations` as single-element lists (high, flagged for verification).** The digest does not state these ranges. The list form was retained, on the reasoning that the schema digest lists these as accepted fields without marking them scalar and that validation will surface any mismatch.
- **`ethical_reviews[2].reviewing_organization`** — "AI-READI Community Advisory Board" is a reasonable rendering of a body the BMJ and IRB sources both attest. Low concern; unchanged.

---

## 4. Core record

The core record was re-derived from the reconciled full record. Every change in §2 that touches a slot present in `CoreDataset` appears in the core: the corrected `creators`, the removed enum slots and new `source_caveats` on `regulatory_restrictions`, the split `external_resources`, the five added negative-fact slots, the corrected `subpopulations` boolean, the single `sensitive_elements` object, the added `labeling_strategies`, `data_protection_impacts` and `extension_mechanism`, the `data_substrate` on `instances`, the restructured `ip_restrictions` and `at_risk_populations`, the `is_version_of` relationship, the scalar `committee_contact`, and the extended `description`, `notes` and `source_caveats`.

Two full-record changes have no core counterpart: `subsets` (§2.11) and `variables` (§2.1, §2.2) are not `CoreDataset` slots. `file_collections` projects to `distributions` in the core, where the `clinical_data` `is_tabular` change (§2.22) appears as the same `notes` statement, and `total_bytes` projects to `bytes`.

---

## 5. Outcome

| | Full | Core |
|---|---|---|
| Top-level slots populated | 71 | 63 |
| Validation | — | — |
| Blocking defects resolved | 1 (`variables[*].description`) | n/a (slot absent) |

The single validation blocker was removed. Ten collapsed entities were split into distinct objects. Two enum values that the record reasoned to rather than read off were removed and their attested basis relocated to prose. Five stated negatives that had been dropped were recorded. Two internal contradictions between sibling fields were resolved, one by correcting a boolean and one by removing an object describing a referent this record does not cover.