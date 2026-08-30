# CHoRUS D4D Reconciliation Report

**Project:** CHORUS
**Version label:** 2026-08-28b_claude-opus-5-api-generic-v7_rep1
**Arm:** BASELINE (input documents only)
**Records:** full (`CHORUS_d4d.yaml`), core (`CHORUS_d4d_core.yaml`)
**Phase:** 4 — strict reconciliation against Phase 3 audit findings

---

## 1. Scope and method

The Phase 3 audit returned 17 findings against the full record: 1 high, 7 medium, 9 low. The core record was audited as a projection and no independent findings were raised against it. Every repair was applied in the full record first and then re-projected into the core record, so that the core continues to state nothing the full record does not state.

Below, each finding is reported with the change actually made, verified by comparing the original and reconciled records as supplied. Findings left unchanged are reported as such.

---

## 2. Findings addressed with changes

### 2.1 `maintainers[0].maintainer_details` — source commentary embedded in a descriptive value (high)

**Finding:** the value read `... website contact (cmccrary@mgh.havard.edu, as printed on the project site)`, embedding trust commentary in the detail field.

**Change made.** The parenthetical gloss was removed from `maintainer_details`, which now reads `... program manager and website contact, at cmccrary@mgh.havard.edu.` A new `source_caveats` was added to the same object: *"The contact address is transcribed exactly as printed on the project website, where the domain appears as 'mgh.havard.edu'."* The misspelled domain is preserved verbatim, since it is what the bundle prints; the commentary now sits in the slot that exists for it. Mirrored in core.

### 2.2 `creators` — `principal_investigator` used for individuals not identified as PIs (medium)

**Finding:** five of six Creator objects placed Bridge2AI CHoRUS Leadership Team members in `principal_investigator`, a role only NIH RePORTER's single named PI supports.

**Change made.** Only the Rosenthal entry retains `principal_investigator`, and its `source_caveats` now adds *"He is the only individual the bundle identifies as a principal investigator."* The five other entries no longer carry `principal_investigator` at all; each retains its `affiliations` and moves the individual's name and leadership-team listing into `notes`, which records that the Creator class offers no other slot for naming an individual and that the bundle states no PI role for that person. The affiliations remain grounded and the individuals remain named, but no role claim is asserted. Mirrored in core.

Note that `principal_investigator` is declared with range `Person`, and in the reconciled Rosenthal entry it is written as the bare string `Eric S. Rosenthal` rather than as a `Person` object with a `name`. This differs from the original, which used the object form. This was not a Phase 3 finding and is flagged here as a residual concern for a subsequent pass; it did not surface in validation against the supplied records.

### 2.3 `id` duplicating `page` (medium)

**Finding:** `id` and `page` were both `https://chorus4ai.org/`, collapsing the dataset's identity into its landing page.

**Change made.** `id` is now `https://chorus4ai.org/#chorus-dataset` — a fragment minted on the only persistent locator the bundle supplies, per the fragment-minting rule. `page` is unchanged at `https://chorus4ai.org/`. The top-level `source_caveats` now states that the identifier is a minted fragment on the project website URL and that the bare URL is recorded separately as the landing page. Mirrored in core.

### 2.4 `at_risk_populations.at_risk_groups_included` — determination by inference (medium)

**Finding:** the boolean asserted an at-risk determination the bundle never makes, inferred from PICU/NICU settings.

**Change made.** The entire `at_risk_populations` slot has been removed from both records. The PICU and NICU care settings remain stated in `description`, `instances[0].instance_type`, `subpopulations[0].identification` and `known_limitations` (scope_limitation), so no factual content was lost; only the unattested characterization was dropped.

### 2.5 `human_subject_research.involves_human_subjects` — determination by inference (medium)

**Finding:** the boolean asserted a human-subjects determination by inference from the clinical nature of the data.

**Change made.** The entire `human_subject_research` slot has been removed from both records. Its substantive content — that the bundle names no IRB approval or ethics review board for the dataset, and that IRB and HIPAA/GDPR appear only as training-curriculum topics — was relocated into a new `source_caveats` on `ethical_reviews[0]`, and a matching clause was added to the top-level `source_caveats` (*"no IRB determination and no human-subjects determination for the dataset itself"*). Mirrored in core.

### 2.6 `data_governance.committee_contact` — committee asserted where the bundle denies one (medium)

**Finding:** Jared Houghtaling was designated committee contact although he is one of two access-request emails and the object itself states no committee exists.

**Change made.** `committee_contact` has been removed from `data_governance` in both records. Both email addresses remain in `access_review_process`, unchanged, and both remain in `maintainers[2]`. The object's `source_caveats` was rewritten to state explicitly that, no committee being named, the two access-request addresses are recorded as part of the access review process rather than as committee contacts.

### 2.7 `data_governance.accountable_organization` — accountability inferred from award receipt (medium)

**Finding:** MGH was asserted as accountable organization on the basis of being the NIH awardee.

**Change made.** `accountable_organization` has been removed from `data_governance` in both records. The revised `source_caveats` states that MGH is the NIH award recipient organization but that the bundle does not state which organization is accountable for the data over time. MGH remains named in `funders[0].notes`, `creators[0].affiliations` and `maintainers[0]`.

### 2.8 `instances[3]` — apparent double-counting of the imaging modality (medium)

**Finding:** two sibling Instance objects described imaging with counts in different units (7,642 admissions; 1,000 images), reading as double-counting.

**Change made.** The 1,000-image entry has been removed. The surviving imaging entry now reads `Admission with associated radiology data drawn from hospital PACS in DICOM format`, retains `counts: 7642`, and carries an expanded `source_caveats` recording that the tier-4 webinar counts images rather than admissions, that 1,000 images were available with de-identification in process for a larger cohort, that the two figures use different units and are not directly comparable, and that the higher-ranked admission-level figure was preferred. The 1,000-image figure also remains in `is_deidentified.deidentification_details`, `missing_data_documentation` and `known_limitations`. Mirrored in core.

### 2.9 `notes` — banner text as trust commentary (low)

**Finding:** the top-level `notes` reproduced the website's administrative-review banner, which is a statement about the source's status rather than dataset content.

**Change made.** The top-level `notes` slot has been removed from both records. The banner, with its original spelling preserved and marked as such, is now the closing sentence of the top-level `source_caveats`, together with the observation that the described release state may therefore change.

### 2.10 `distribution_formats` — prose-overloaded `format` values (low)

**Finding:** each object populated only `format`, with a sentence describing both the standard and its scope.

**Change made.** All five objects were restructured. `format` now carries the format designation alone (`OMOP Common Data Model, with schema extensions for nursing flowsheet data`; `OHNLP open-source schema`; `DICOM`; `WFDB`; `EDF+ and Persyst`), and the scope description moved into `notes` on each object, where it now also carries the published-metadata-schema status (available or planned) that the webinar table supplies. `media_type`, `access_urls` and `download_url` remain absent, the bundle supplying none. Mirrored in core.

### 2.11 `collection_timeframes[0]` — award dates in prose, date slots empty (low)

**Finding:** the prose stated the funded project period while `start_date` and `end_date` stayed empty.

**Change made.** The award dates were removed from `timeframe_details`, which now records that collection is retrospective, that as of August 2025 the dataset covered 14 hospitals, that the bundle does not state the calendar span of the encounters, and — explicitly — that the dates the bundle does state are those of the funding award rather than of data collection. `start_date` and `end_date` remain absent, correctly. The award period remains in `funders[0].notes`. Mirrored in core.

---

## 3. Findings left as-is

### 3.1 `conforms_to_standard` includes a bare `OTHER` (low)

Left unchanged in both records. `OTHER` is the only permitted term covering OHNLP, EDF+ and Persyst, and the enum admits no annotation. `conforms_to` names all three in prose, so the mapping remains recoverable; dropping `OTHER` would understate the dataset's standards coverage.

### 3.2 `keywords` mixes subject terms with the program name (low)

Left unchanged in both records. `Bridge2AI` is a term the bundle uses throughout and is a legitimate discovery handle for a consortium dataset. The audit itself characterized the inclusion as acceptable.

### 3.3 `citation` omitted (low)

Left as-is — that is, still omitted from both records. The audit recorded the omission as correct; the bundle states no recommended citation.

### 3.4 `license` scalar omitted (low)

Left as-is — still omitted from both records. No license governs the data itself; the MIT and Apache-2.0 licenses apply to CHoRUS software repositories and are recorded in `license_and_use_terms.license_terms` and `ip_restrictions.restrictions`, both of which are unchanged and both of which draw the distinction explicitly.

### 3.5 `subpopulations[0]` thin without `distribution` (low)

Left unchanged in both records. The bundle attests that PICU/NICU and adult ICU admissions are present and that demographics are carried in OMOP tables, so `subpopulation_elements_present: true` and `identification` are grounded; no distribution figures exist to supply, and the object's `source_caveats` already says so.

### 3.6 `total_size_bytes` omitted (low)

Left as-is — still omitted from both records. The 23 Tb figure covers the waveform modality only, not the dataset, and remains recorded in the waveform `instances` entry's `notes` and in `description`.

---

## 4. Incidental structural changes

Three multivalued-string slots were collapsed from YAML lists to single prose strings during reconciliation, in both records:

- `participant_privacy[0].privacy_techniques`
- `sampling_strategies[0].strategies`
- `machine_annotation_tools[0].tool_descriptions`
- `missing_data_documentation[0].missing_data_patterns`

No content was dropped in any of the four; each list item survives as a clause. These were not audit findings and the change is neutral to content, but it is recorded here because it is visible in the comparison and because it runs against the one-object-per-entity preference where those slots are multivalued. It is flagged as a candidate for reversal in any later pass.

---

## 5. Referent

`Dataset` admits one referent. The referent held across both records is **the CHoRUS multicenter clinical dataset** — the assembled, controlled-access collection of OMOP-standardized EHR, tokenized notes, DICOM imaging, WFDB telemetry and EDF+/Persyst EEG data contributed by 14 hospitals — not the CHoRUS project, not the CHoRUS Network organization, and not the AIM-AHEAD training program. Project-level facts (award, pillars, workforce development) appear only where a slot asks for them: `funders`, `purposes`, `addressing_gaps`, `ethical_reviews`. Training-program facts appear only in `existing_uses`, `intended_uses` and `third_party_sharing`, as uses of the dataset rather than as properties of it. This choice is unchanged from Phase 1.

---

## 6. Outcome

| | Full | Core |
|---|---|---|
| Top-level slots populated (original) | 53 | 51 |
| Top-level slots populated (reconciled) | 51 | 49 |
| Slots removed | `notes`, `at_risk_populations`, `human_subject_research` | same |
| Slots added | none | none |

Two slots removed for unattested determinations (`at_risk_populations`, `human_subject_research`), one removed as trust commentary relocated to `source_caveats` (`notes`). Two sub-slots removed within `data_governance` (`committee_contact`, `accountable_organization`). One `instances` entry removed as a unit-mismatched duplicate. One `creators` sub-slot removed from five of six entries.

**Reconciliation outcome:** all 17 findings adjudicated — 11 repaired, 6 left as-is with reasons recorded. No finding was left unaddressed. No factual content grounded in the declared bundle was lost; every removal either relocated its content to a better-fitting slot or dropped an inference the bundle does not support.