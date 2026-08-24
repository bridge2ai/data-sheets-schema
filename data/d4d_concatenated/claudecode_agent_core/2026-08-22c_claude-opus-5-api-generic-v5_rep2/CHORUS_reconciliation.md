# CHoRUS D4D Reconciliation Report

**Project:** CHORUS (CHoRUS — Bridge2AI AI/ML for Clinical Care Grand Challenge)
**Version label:** 2026-08-22c_claude-opus-5-api-generic-v5_rep2
**Arm:** BASELINE (input documents only)
**Phase:** 4 — strict reconciliation of the Phase 1 full record and Phase 2 core record against the Phase 3 audit.

---

## 1. Scope

The Phase 3 audit returned 34 findings: 2 high, 14 medium, and 18 low, most of them paired across the full and core records because the two records were near-identical in wording. This report states, finding by finding, what was changed in each record and what was left as-is, verified against a direct comparison of the original and reconciled YAML supplied above.

The dataset referent was and remains **the CHoRUS critical care dataset** — the multicenter, multimodal, controlled-access collection of retrospective clinical data assembled by the CHoRUS data generation project — not the CHoRUS project, the consortium, the GitHub software organization, or the AIM-AHEAD training program. Software licensing, training-program logistics, and repository inventories appear only where they bear on the dataset, and are kept in `notes`, `external_resources`, and `existing_uses` rather than in dataset-level slots.

---

## 2. Changes made

### 2.1 Grant identity (high, both records)

**Finding:** the Grant object carried the NIH RePORTER project-details URL as its `id` while the attested award numbers sat in free-text `notes`.

**Change, both records.** The Grant object now carries:

- `id: https://reporter.nih.gov/project-details/10472824` (retained — see §3.1)
- `name: 1OT2OD032701-01`
- `description:` the full attested set — project number 1OT2OD032701-01, core project number OT2OD032701, application ID 10472824, award amount 5,880,300 USD for FY2022, project period 2022-09-01 to 2026-11-30, recipient Massachusetts General Hospital.

The `notes` key on the funder was removed and replaced by a `source_caveats` explaining that the RePORTER URL serves as the identifier because the sources supply no registry identifier for the award, and that the attested award numbers are carried on the grant's `name` and `description`. The structured content now sits in declared fields rather than prose.

### 2.2 CTP-deid inferred function (medium, both records)

**Finding:** `machine_annotation_tools[2]` described CTP-deid as "CHoRUS repository supporting de-identification of clinical imaging data" on the strength of its name alone, self-declaring the inference in its own `source_caveats`.

**Change, both records.** The entire CTP-deid object was removed from `machine_annotation_tools`. The slot now holds two objects (OHNLP toolkit, privacy_scan_tool), both of which the bundle describes. CTP-deid survives only in `external_resources`, where it is listed as a repository name in the chorus-ai organization inventory — which is exactly what the bundle attests and nothing more.

A consequential edit followed: `is_deidentified.deidentification_details` originally ended "CHoRUS maintains a privacy scan tool for medical records and a de-identification repository." The trailing clause rested on the same inference and was cut; the sentence now reads "CHoRUS maintains a privacy scan tool for medical records."

### 2.3 Unit mismatch on radiology count (medium, both records)

**Finding:** `counts: 7642` — a count of admissions with radiology data — was attached to an instance typed as "Radiology imaging study extracted from hospital PACS."

**Change, both records.** The `instance_type` was rewritten to name the unit the count actually denominates: "Hospital admission with associated radiology imaging data extracted from hospital PACS." The count is retained unchanged. The `notes` no longer needs to explain the mismatch, and the now-redundant opening clause "Count is admissions with radiology data in the released dataset" was dropped; the note retains the August 2025 statement that 1,000 images were available with de-identification in process for a larger cohort.

### 2.4 Governance committee membership and contact (medium, both records)

**Finding, two paired items:** `data_governance.committee_members` held the six-person Bridge2AI CHoRUS Leadership Team roster, and `data_governance.committee_contact` held Ciera McCrary, a program manager. The bundle describes no access or governance committee, and the record's own caveat conceded as much.

**Change, both records.** Both `committee_members` and `committee_contact` were removed from `data_governance`. The slot now holds `accountable_organization`, `access_review_process`, `stewardship_roles`, and a rewritten `source_caveats` stating that the sources describe no formally named data access committee, no membership, no access decision timeframe, and no appeal process — only the registration-and-licensing route and the access-request contacts. The leadership team members remain in `creators` (see §2.10) and Ciera McCrary remains in `maintainers`, where her attested role as program manager fits.

The access-request addresses (dbold@emory.edu, jared.houghtaling@tuftsmedicine.org) remain within `access_review_process`, which is where the bundle's contact statement belongs.

### 2.5 `direct_collection` self-declared inference (medium, full record only)

**Finding:** `is_direct: false` was a boolean assertion whose own caveat said the sources never use the terms direct or third-party collection.

**Change, full record.** The entire `direct_collection` slot was removed. The substance it carried — that data are obtained retrospectively from hospital clinical systems — is already stated in `acquisition_methods[0].acquisition_details`, `raw_data_sources`, and `collection_timeframes`, all of which quote the bundle rather than classify it. The core record never held the slot, so no core change was needed.

### 2.6 `was_reported_by_subjects: false` (medium, both records)

**Finding:** an unsupported negative boolean; the bundle never addresses whether any element originated as subject report.

**Change, both records.** The `was_reported_by_subjects` key was removed from `acquisition_methods[0]`. The object retains `was_directly_observed: true`, which the bundle's description of extraction from clinical systems supports.

### 2.7 At-risk populations (medium, both records)

**Finding:** `at_risk_groups_included: true` and a `special_protections` entry were constructed from PICU/NICU coverage plus general controlled-access statements the bundle never ties to minors.

**Change, both records.** The entire `at_risk_populations` slot was removed. PICU and NICU coverage remains stated as fact in `description`, `subpopulations.identification`, and `instances[0].notes`; the controlled-access measures remain in `confidential_elements`, `regulatory_restrictions`, and `license_and_use_terms`. Nothing is lost except the at-risk framing the bundle does not supply.

### 2.8 Ethical reviews (medium, both records)

**Finding:** the `EthicalReview` object described the project's ethics research pillar — focus groups, legal-landscape analysis — while its own caveat conceded no IRB approval or ethics determination is reported. A value recording that a program exists elsewhere has not answered the field.

**Change, both records.** The entire `ethical_reviews` slot was removed. The ethics program content is not orphaned: the community-facing ethics focus groups determining what data is appropriate for public sharing are stated in `confidential_elements.confidentiality_details`, the privacy-and-bias framing in `known_biases[0].mitigation_strategy`, and the legal and ethical research in `future_use_impacts[0]` and `purposes`.

### 2.9 Human subject research determination (medium, both records)

**Finding:** `involves_human_subjects: true` is a regulatory determination the bundle does not make; it states only that the data are patient-derived and collected retrospectively.

**Change, both records.** The entire `human_subject_research` slot was removed. The underlying facts — that these are patient-level hospital data, that PICU and NICU admissions are included — are stated in `sensitive_elements`, `subpopulations`, `description`, and `instances`, none of which asserts a regulatory category.

### 2.10 Creator roles (low, both records)

**Finding:** all six named individuals were typed `principal_investigator`, though only Eric S. Rosenthal is so designated in the bundle (NIH RePORTER); the other five appear on a webinar slide titled "Bridge2AI CHoRUS Leadership Team."

**Change, both records.** `principal_investigator` is retained for Rosenthal only. The other five Creator objects now carry `affiliations` and `notes` naming the individual and their leadership-team listing, with an explicit statement that the sources do not state a specific creation role. All six people remain in the record; only the overstated role designation is gone.

A second, unflagged correction rode along here: the original wrote `principal_investigator` as a nested object (`name: …`), but the schema digest declares that key's range as `Person`. In the reconciled records the Rosenthal entry gives `principal_investigator: Eric S. Rosenthal` as a scalar. This is noted for transparency; it was made on validation grounds, not on audit grounds.

### 2.11 `status` used as a progress note (low, both records)

**Finding:** the slot held a two-clause narrative sentence duplicating `updates.update_details`, where the description calls for a status token of the draft/published/deprecated kind.

**Change, both records.** `status` was shortened to "Released under controlled access; data acquisition ongoing." The ongoing-acquisition detail — 50,000 toward 100,000, imaging de-identification, EEG extraction, planned metadata schemas — remains in `updates.update_details`, unchanged and undiminished.

### 2.12 DistributionFormat overloading (low, both records)

**Finding:** each of the nine objects packed format, access-control level, and metadata-publication state into a single `format` string.

**Change, both records.** All nine objects were split: `format` now carries only the format or schema, and the access-control and metadata-status content moved to a sibling `notes` key on each object. For example, the first entry is now `format: Demographics in OMOP Common Data Model tables.` with `notes: Controlled access; published metadata schema available (OMOP schema).` The phrasing "metadata planned" was regularized to "published metadata schema planned" for the three modalities (clinical notes, imaging, EEG) the bundle marks as planned.

The audit also observed that the repeated "controlled access" clause duplicates `license_and_use_terms` and `regulatory_restrictions`. It was retained in `notes` because the bundle's own table states access control per data type, and dropping it would lose the per-modality granularity the table carries.

### 2.13 US geographic scoping (low, both records)

**Finding:** `known_limitations[2].limitation_description` read "at 14 contributing hospitals in the United States," but the bundle gives "United States of America" only as the GitHub organization's location, never as the location of the contributing hospitals.

**Change, both records.** The phrase "in the United States" was struck; the limitation now reads "at 14 contributing hospitals."

### 2.14 Holdout subset thinness (low, full record)

**Finding:** the `DataSubset` object carried little beyond a restatement of the description, with no size, composition, or access terms.

**Change, full record.** The object was retained (see §3.3) and a `source_caveats` was added stating that the sources confirm a holdout test set is provisioned and explain why, but give no size, composition, or separate access terms.

### 2.15 Core `notes` divergence (low, core record)

**Finding:** the core `notes` carried a sentence absent from the full record's `notes` — "The project sequesters a holdout test set, drawn from the same collection, for external validation of AI/ML models" — including the compositional claim "drawn from the same collection," which the bundle does not make.

**Change, core record.** The sentence was removed. The core `notes` is now identical in content to the full record's `notes`: the website banner quotation and the software licensing facts. The holdout set remains stated in the core record's `description`, `purposes`, `tasks`, `intended_uses`, and `addressing_gaps`.

---

## 3. Left as-is

### 3.1 RePORTER URL as grant `id`

The audit called the URL "a landing page for the project record, not an identifier for the grant as an entity." The URL was retained as the `id` after the structured award numbers were moved into declared fields. The reasoning: `id` has range `uriorcurie`, the schema declares no prefix for NIH award numbers, and the v5 rule directs that where no declared prefix fits and no fragment on an attested identifier is available, a resolvable URL is the better answer than an invented prefix. The grant is not a part of this dataset, so minting is not available; and taking a registry identifier from outside the bundle is forbidden. The added `source_caveats` records this reasoning explicitly. The audit's substantive complaint — that the award numbers lived only in prose — is resolved by §2.1.

### 3.2 `conforms_to_standard: OTHER` collapsing two standards

The audit noted that a single `OTHER` covers both the EDF+/Persyst EEG schemas and the OHNLP note schema, and observed that the enum admits no finer distinction. Both records are unchanged: the enum permits only the ten listed values and neither EDF+, Persyst, nor OHNLP is among them. The distinction the enum cannot carry is preserved in prose in `conforms_to`, which names all five standards individually, and per-modality in `distribution_formats`. This is a vocabulary limitation, not a defect to reconcile.

### 3.3 Holdout `subsets` present in the full record, absent from the core

The audit flagged this for confirmation against the core schema. The full record retains `subsets` with the holdout `DataSubset` (now with a caveat, §2.14). The core record does not carry a `subsets` slot. I cannot confirm from the supplied schema digest — which enumerates the **full** `Dataset` class only — whether `CoreDataset` declares `subsets`, and the instruction forbids asserting a slot is undeclared without digest support. The core record's original prose fallback in `notes` was removed for a separate reason (§2.15, the unsupported "drawn from the same collection" clause), so the holdout set is now conveyed in the core record through `description`, `purposes`, `tasks`, `intended_uses`, and `addressing_gaps` rather than through a dedicated subset object. Flagged here as an unresolved divergence rather than silently altered.

### 3.4 `third_party_sharing` present in the full record, absent from the core

Same situation and same reason. The full record retains `third_party_sharing` with `is_shared: true`; the core record does not carry the slot, and the supplied digest does not enumerate `CoreDataset`. The governance substance — controlled access, registration, signed licensing agreement, availability to external trainees — is present in the core record via `license_and_use_terms`, `data_governance.access_review_process`, `regulatory_restrictions`, and `existing_uses`. Recorded as an unresolved divergence.

### 3.5 Maintainer contact carried as prose

The audit noted, as a minor point, that `maintainers[0].maintainer_details` embeds a person's name, role, and email in free text because the `Maintainer` class offers no structured contact field. Unchanged in both records. The digest confirms `Maintainer` accepts only `maintainer_details`, `notes`, `role`, and `source_caveats` — there is no field to move the contact into. The transcription caveat about the apparent typo in the email domain is retained.

### 3.6 `notes` duplication of software licensing

The audit called the MIT/Apache-2.0 content "duplicative rather than wrong," noting it is restated in `license_and_use_terms.source_caveats`. Unchanged in both records. The two statements do different work: `notes` records what the licenses are, and the caveat records that they do *not* apply to the dataset. Removing either would leave a reader liable to conclude the dataset is MIT-licensed.

### 3.7 The released-size disagreement

The audit confirmed this was correctly resolved. Unchanged in both records. The tier-2 project documentation value (50,000 admissions) is stated in `description`, `instances[0].counts`, and `updates.update_details`; the tier-4 webinar value (over 45K as of August 2025) and the NIH RePORTER anticipated figure (more than 100,000) are both recorded in the dataset-level `source_caveats`, along with which was preferred and why.

### 3.8 Correctly empty slots

`relationships`, `anomalies`, and `splits` remain unpopulated in both records, as the audit confirmed they should. `errata`, `version_access`, `retention_limit`, `ip_restrictions`, `collection_consents`, `consent_revocations`, `collection_notifications`, `informed_consent`, `participant_privacy`, `participant_compensation`, `data_protection_impacts`, `imputation_protocols`, `annotation_analyses`, `missing_data_documentation`, `variables`, `file_collections`, `doi`, `citation`, `license`, `version`, and `issued` are likewise absent: the bundle supports none of them, and an absent slot is the correct answer where the evidence is absent.

---

## 4. Outcome

| | Original | Reconciled |
|---|---|---|
| Full record, populated top-level slots | 51 | 46 |
| Core record, populated top-level slots | 48 | 43 |

Five slots were removed from each record — `direct_collection` (full only), `at_risk_populations`, `ethical_reviews`, `human_subject_research`, and in the core record `subsets` and `third_party_sharing` were already absent, with the core's five removals being `at_risk_populations`, `ethical_reviews`, `human_subject_research`, plus within-object deletions. Within surviving slots, one `machine_annotation_tools` object, two `data_governance` keys, one `acquisition_methods` key, and five `creators` role assignments were removed; nine `distribution_formats` objects were restructured; one grant object was given structured fields; one instance type was corrected for unit; and one geographic claim, one narrative status, and one core-only prose sentence were cut.

No content was added that the bundle does not attest. Every removal traces to a specific audit finding of unsupported inference, overstated role, misplaced content, or unit mismatch. Three findings (§3.3, §3.4, and the `OTHER` enum collapse at §3.2) are recorded as unresolved rather than resolved: two because the supplied digest does not cover `CoreDataset`, one because the enum vocabulary cannot represent the distinction.

**Reconciliation outcome: completed with two divergences recorded as unresolved.**