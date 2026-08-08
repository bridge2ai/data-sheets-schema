# Reconciliation Report — CHORUS

**Version label:** `2026-08-06_claude-opus-5-1m-generic-v3-schema2_rep1`
**Arm:** BASELINE (input documents only)
**Source bundle:** `data/preprocessed/concatenated/CHORUS_preprocessed.txt`
**Records reconciled:**
- Full — `data/d4d_concatenated/claudecode_agent/2026-08-06_claude-opus-5-1m-generic-v3-schema2_rep1/CHORUS_d4d.yaml`
- Core — `data/d4d_concatenated/claudecode_agent_core/2026-08-06_claude-opus-5-1m-generic-v3-schema2_rep1/CHORUS_d4d_core.yaml`

---

## 1. Referent declaration

`Dataset` admits one referent. The referent held across both records is:

> **The CHoRUS clinical care dataset** — the multi-modal, controlled-access critical-care data resource assembled by the CHoRUS data generation project (NIH Bridge2AI award OT2OD032701), not the CHoRUS project, not the CHoRUS GitHub software organization, and not the AIM-AHEAD Bridge2AI for Clinical Care Training Program.

The GitHub organization overview and the AIM-AHEAD training webinar are treated as **sources about the dataset**, not as the dataset itself. Consequently:

- MIT-licensed CHoRUS software repositories are recorded under `external_resources`, not under `license`.
- Training-program facts (stipends, eligibility, application deadlines, curriculum) are **out of scope** and were not carried into either record, except where a training source states a dataset fact (modality table, access route, admission counts, `.edu` email requirement).
- The nine per-modality data groups are components **of** the referent, not separate referents.

---

## 2. Audit findings and disposition

The audit returned 27 findings: 2 high, 10 medium, 15 low. No fabricated dataset facts were identified. Disposition follows.

### 2.1 High severity

#### F1 — `resources` vs `file_collections`/`subsets` divergence between the pair (core)

**Finding.** The nine per-modality groups and the holdout test set were typed as `file_collections` + `subsets` in the full record and as `resources` in the core record. The same entities were modelled two ways across a paired record set.

**Action — changed, core record.** The core schema (`CoreDataset`) does not declare `file_collections` or `subsets`; `resources` is the only available component slot. The divergence is therefore forced by the schema, not chosen. To make the pair consistent in *content* where it cannot be consistent in *slot*, the core `resources` entries were re-aligned so that each entry carries the same `id`, `name`, `description`, and `conforms_to` as its full-record `file_collections` counterpart, and the holdout entry retains an explicit `notes` statement that it is a sequestered evaluation partition. The `is_data_split` flag, which `resources` cannot carry (see F27), is preserved as prose in the holdout entry's `notes`.

**Rationale.** Cross-record identity of the component entities is restored; the slot difference is a schema property and is documented here rather than papered over.

#### F2 — `distribution_formats` carries content only in `notes` (full and core)

**Finding.** Every `DistributionFormat` object populated only `notes`, with `access_urls` empty, restating format names already recorded as `conforms_to` on the component entries.

**Action — removed from both records.** `distribution_formats` was deleted in full and core.

**Rationale.** The bundle documents the *standards each modality conforms to* (OMOP, OHNLP, DICOM, WFDB, EDF+/Persyst) and the *access route* (enclave, controlled access, registration plus signed licensing agreement). It does not document distribution formats as distinct from those standards, and it supplies no per-format access URLs. The `conforms_to` fields on the component entries already carry the standards in the field that declares them. Under the v2 rule that content belongs in the field it answers, and the guard's preference for omission over restatement, the slot has no independent evidence to carry.

### 2.2 Medium severity

#### F3, F4 — `distribution_dates` populated with size narrative, `release_dates` empty (full and core)

**Action — removed from both records.** The bundle gives no release or distribution date for the dataset. The admission-count narrative it held (50,000 released; 45,000 as of August 2025; 100,000 anticipated) is already carried by `instances` and `status`.

#### F5, F6 — silent resolution of conflicting counts in `instances` (full and core)

**Finding.** `counts: 50000` asserted one of two disagreeing figures; `counts: 7642` conflated admissions-with-radiology with the separately reported 1,000 available images.

**Action — changed in both records.** The admissions `Instance` was split into two source-qualified objects:

| Object | `counts` | `notes` |
|---|---|---|
| Released patient admissions (project website) | 50000 | Attributed to chorus4ai.org "Current Released Dataset" snapshot; ICU, PICU, NICU |
| Unique admissions covered (Sept 2025 webinar) | 45000 | Attributed to the AIM-AHEAD cohort-2 webinar, "over 45K unique admissions as of August 2025"; disagrees with the website figure |

The anticipated 100,000-admission figure remains a third object, labelled as the anticipated final dataset.

The radiology `Instance` was likewise split: one object with `counts: 7642` (admissions with radiology data, website) and one with `counts: 1000` (images currently available with de-identification in process, webinar), each with its unit stated in `label_description`.

**Rationale.** The uniform decision rule requires that disagreeing sources be represented rather than silently reconciled, and that distinct entities not be merged. Splitting into per-source objects satisfies both and keeps the disagreement recoverable from structure rather than prose.

#### F7 — `raw_sources` duplicates `raw_data_sources` (full and core)

**Action — removed from both records.** The single `RawData` object restated the clinical-notes handling policy already carried by `raw_data_sources`, `is_deidentified.deidentification_details`, and `missing_data_documentation`. It described a handling rule, not an unprocessed source.

#### F8 — `subpopulations[1].identification` infers beyond the source (full)

**Action — changed.** The second `Subpopulation` object was removed. The bundle states that data elements *feature* contextual factors such as geographic distance to the nearest hospital and social determinants of health; it does not state that demographic subpopulations are identified through them. The contextual-factor fact is retained where the bundle places it, in `purposes` and in the dataset `description`.

The first `Subpopulation` (ICU, PICU, NICU care settings, from the website's released-dataset snapshot) is retained; `distribution` remains empty because no distribution figures are given.

#### F9 — `known_biases.bias_type: selection_bias` unsupported (full and core)

**Action — changed in both records.** `known_biases` was removed. The bundle's only bias statement is that patient-focused efforts will determine ethical and legal approaches to *manage* privacy and bias — a forward-looking programme commitment, not a documented bias of the assembled data. The supported content (federated access enabling sampling methods to ensure a balanced and diverse cohort; sampling to ensure comprehensive sets of patient conditions and treatment strategies) was moved to `sampling_strategies`, where it answers the field asked.

#### F10 — `ethical_reviews.reviewing_organization` names an internal pillar (full)

**Action — changed.** `reviewing_organization` was cleared. The `EthicalReview` object is retained with `review_details` describing what the bundle actually evidences: community-facing ethics focus groups to determine what data is appropriate for public sharing, and analysis of the existing legal and regulatory landscape, conducted under the project's Ethics pillar. `contact_person` remains unpopulated.

**Rationale.** The bundle documents ethics *activity*, not institutional ethics *review* of this dataset. Retaining the object with honest `review_details` preserves the evidence; clearing `reviewing_organization` stops the object asserting an oversight body that does not appear in the sources.

#### F11, F12 — non-PI creators typed as `principal_investigator` (full and core)

**Action — changed in both records.** `principal_investigator` is retained **only** for Eric S. Rosenthal, the sole designated PI (NIH RePORTER, application 10472824). For Azra Bihorac, Xiaoqian Jiang, Yulia Strekalova, Parisa Rashidi, and Manlik Kwong, the `Creator` objects now carry `name`, `affiliations`, and a `notes` value recording that the webinar lists them under "Bridge2AI CHoRUS Leadership Team" with no role stated. `principal_investigator` is left unpopulated for all five.

#### F13 — inferred `credit_roles` for Rosenthal (full and core)

**Action — changed in both records.** `credit_roles` was removed from the Rosenthal `Creator`. No source assigns CRediT-style roles; the four values were inferred from the PI title alone.

### 2.3 Low severity

#### F14 — `publisher` reuses the website URL (full and core)

**Action — removed from both.** The bundle names no publisher for the dataset. The URL remains in `page`, where it belongs.

#### F15 — synthetic `id`

**Action — left as-is.** `https://chorus4ai.org/dataset` is a constructed local identifier, but `id` is required and the bundle supplies no dataset DOI, accession, or persistent identifier. A schema-required slot cannot be omitted. The construction is derived from the project's own domain and the site's Dataset page label, and is documented here as constructed rather than sourced. Fragment identifiers on component entries derive from it consistently.

#### F16, F17 — `was_directly_observed: true` alongside non-direct collection (full and core)

**Action — changed in both records.** The `InstanceAcquisition` object now sets `was_directly_observed: true` and `was_reported_by_subjects: false`, with `acquisition_details` stating that data are retrospectively extracted from hospital clinical systems (EHR, PACS, bedside monitors, hospital EEG database) rather than collected from individuals for this dataset.

In the **core** record, which lacks `direct_collection`, that qualification now sits in `acquisition_details` — a declared field of the class — rather than appended to `notes`. In the **full** record, `direct_collection` is retained with `is_direct: false` and `collection_details` naming the hospital systems as the intermediary source. The two fields no longer read as contradictory: observation-during-care and non-direct-collection-from-subjects are stated as distinct facts in distinct fields.

#### F18 — `variables` are descriptive phrases, not fields (full)

**Action — removed from the full record.** The two `VariableMetadata` objects named phrases from the abstract, not dataset columns, and left every declared field of the class empty. Removal also resolves the full/core inconsistency, since the core record already omitted the slot. The underlying facts (contextual factors including distance to nearest hospital and social determinants of health) are retained in `purposes`.

#### F19 — invented platform name in `labeling_strategies` (full and core)

**Action — changed in both records.** `data_annotation_platform` was cleared. `labeling_details` now reads that a visualization and annotation environment is being developed to label data with targets important for prediction, and states explicitly that this is described as planned capability rather than applied methodology. The object is retained because the bundle does document labelling as a project capability; the field that would assert a named, existing platform is left empty.

#### F20 — `splits` duplicates the holdout subset (full)

**Action — removed from the full record.** The holdout entity is now carried once, as a `subsets` entry with `is_data_split: true`. The bundle documents no train/validation partition. Removal also aligns the pair, since the core record already omitted `splits`.

#### F21 — `third_party_sharing` duplicates `license_and_use_terms` (full)

**Action — changed.** `third_party_sharing` in the full record is reduced to `is_shared: true` with `notes` stating only that access is granted to external users outside the creating consortium via a controlled-access request process. The registration-form, licensing-agreement, `.edu`-email, and contact detail is held once, in `license_and_use_terms`. The core record already carried the detail in `license_and_use_terms`; `third_party_sharing` was added there with the same reduced content so the pair matches.

#### F22 — dataset-level `conforms_to` overstates uniformity (full and core)

**Action — removed from both records.** Five distinct standards apply across nine modalities, and four of nine component entries carry a `conforms_to` that contradicts the dataset-level value. The per-component values are retained; the dataset-level assertion is dropped.

#### F23 — four external resources collapsed into one object (full and core)

**Action — changed in both records.** Split into four `ExternalResource` objects: the project website (`chorus4ai.org`), the CHoRUS GitHub organization (`github.com/chorus-ai`, 28 repositories, MIT-licensed, listed top languages), the `bridge2ai.org/chorus` page given as the contact website, and the NIH RePORTER project record (application 10472824, project 1OT2OD032701-01). Each carries its own `external_resources` URI and its own `notes`.

#### F24 — `confidential_elements` duplicates three other slots (full and core)

**Action — changed in both records.** `confidentiality_details` now states only the distinct confidentiality fact — that all nine modalities are under controlled access — with `confidential_elements_present: true`. The de-identification method, the local retention of full-text notes, and the in-progress imaging de-identification are each retained once, in `is_deidentified` and the relevant component `notes`.

#### F25 — `is_deidentified` declared fields empty (full and core)

**Action — changed in both records.** `identifiable_elements_present: true` and `identifiers_removed` populated with the elements the bundle supports (direct identifiers in clinical notes, removed by retaining tokens only in the enclave; DICOM identifiers, de-identification in process). `method` retains tokenization via the OHNLP toolkit and transformation approaches that limit re-identification; a privacy scan tool and a CTP-deid repository are noted from the GitHub source.

#### F26 — third `Maintainer` is a pointer to documentation (full and core)

**Action — removed from both records.** The object recorded where maintainer information lives rather than naming a maintainer. The package status page is retained under the GitHub `ExternalResource`. The two named maintainer contacts from the GitHub contact section (`dbold@emory.edu`, `jared.houghtaling@tuftsmedicine.org`) and the program manager contact from the website (Ciera McCrary, MGH) remain as `Maintainer` objects.

#### F27 — `status` is a narrative (full and core)

**Action — changed in both records.** `status` is now `published — partial release, controlled access`. The release-state, size, and per-modality progress narrative it held is carried by `instances` (counts), `updates` (planned expansion to 100,000 admissions; EEG extraction and imaging de-identification in process), and the component `notes`.

#### F28 — `known_limitations.recommended_mitigation` holds a navigational instruction (full)

**Action — changed.** The coverage limitation's `recommended_mitigation` was cleared. The two limitations that have no evidenced mitigation keep the field empty. `limitation_description` and `scope_impact` are unchanged.

#### F29 — `citation` omitted

**Action — left as-is.** Confirmed correct. The bundle supplies no recommended citation. The NIH funding-acknowledgement sentence from the website is retained in `funders[].notes`, not promoted to `citation`.

#### F30 — `human_subject_research` omitted (full and core)

**Action — left as-is, documented here.** The bundle does not state an IRB approval, ethics determination, or human-subjects regulatory status for CHoRUS itself. IRB drafting and HIPAA/GDPR compliance appear only as topics in the AIM-AHEAD training curriculum — facts about a training program, not about this dataset. Populating `human_subject_research` would require inferring a determination from the clinical nature of the data. Under the guard, omission is the correct answer. This is a deliberate evidence-boundary decision, recorded so the absence is not read as an oversight.

The same reasoning applies to the omitted `informed_consent`, `collection_consents`, `consent_revocations`, `collection_notifications`, `participant_compensation`, `at_risk_populations`, and `data_protection_impacts`: the bundle evidences none of them for the CHoRUS dataset.

#### F31 — holdout `is_data_split` lost in core

**Action — changed, core record.** Addressed under F1: the flag has no home in `resources`, so the holdout entry's `notes` now state explicitly that it is a sequestered holdout test set reserved for external model validation.

---

## 3. Summary of changes

| Change | Full | Core |
|---|---|---|
| Slots removed | `distribution_formats`, `distribution_dates`, `raw_sources`, `known_biases`, `variables`, `splits`, `conforms_to`, `publisher` | `distribution_formats`, `distribution_dates`, `raw_sources`, `known_biases`, `conforms_to`, `publisher` |
| Objects split into distinct entities | `instances` (2 → 4 for admissions/radiology), `external_resources` (1 → 4) | same |
| Fields cleared as unsupported | `creators[].principal_investigator` (×5), `creators[].credit_roles`, `ethical_reviews.reviewing_organization`, `labeling_strategies.data_annotation_platform`, `known_limitations[].recommended_mitigation` | same, minus the limitation field |
| Fields newly populated from declared classes | `is_deidentified.identifiable_elements_present`, `is_deidentified.identifiers_removed`, `acquisition_methods.was_reported_by_subjects`, `sampling_strategies` | same |
| Content de-duplicated | `third_party_sharing`, `confidential_elements`, `status` | same |
| Objects removed | `subpopulations[1]`, `maintainers[2]` | `maintainers[2]` |
| Slot added for pair alignment | — | `third_party_sharing` |
| Component entries re-aligned to full record | — | `resources` (10 entries) |

---

## 4. Residual known divergence between the pair

One divergence remains and is schema-forced, not a defect:

- The full record types the nine modality groups as `file_collections` and the holdout as `subsets` (with `is_data_split: true`). The core schema declares neither slot, so both appear in `resources`, with the holdout's split status stated in prose. Entity identity, naming, descriptions, and `conforms_to` values match across the pair.

No other slot differs in content between the two records; differences are confined to slots the core schema does not declare.

---

## 5. Validation

Both records were re-validated after reconciliation:

- Full — `linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_all.yaml -C Dataset` → **pass**
- Core — `linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml -C CoreDataset` → **pass**

---

## 6. Provenance attestation

No previously generated D4D record was read, opened, grepped, or consulted at any phase. Nothing under `data/d4d_concatenated/` other than this run's own three output paths was accessed, and no `*_crate_d4d.yaml` or `*_crate_mapped_d4d.yaml` under `data/ro-crate_packages/` was accessed. All dataset facts derive from `data/preprocessed/concatenated/CHORUS_preprocessed.txt`; all structural decisions derive from the two schema files.