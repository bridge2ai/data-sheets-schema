# Reconciliation Report — CHORUS

**Version label:** `2026-08-06_claude-opus-5-1m-generic-v3-schema2_rep1`
**Arm:** BASELINE (input documents only)
**Declared input bundle:** `data/preprocessed/concatenated/CHORUS_preprocessed.txt` (4 source files)
**Records reconciled:**

- Full — `data/d4d_concatenated/claudecode_agent/2026-08-06_claude-opus-5-1m-generic-v3-schema2_rep1/CHORUS_d4d.yaml`
- Core — `data/d4d_concatenated/claudecode_agent_core/2026-08-06_claude-opus-5-1m-generic-v3-schema2_rep1/CHORUS_d4d_core.yaml`

**Prior D4D factual reuse:** none. No previously generated D4D record, from any arm or label, was opened or consulted at any phase.

---

## 1. Declared referent

`Dataset` admits one referent. The referent held across both records is:

> **The CHoRUS clinical care dataset** — the multi-modal, controlled-access critical-care dataset assembled by the CHoRUS data generation project, in its **currently released** state as described by `chorus4ai.org` and the September 2025 AIM-AHEAD Cohort 2 webinar.

The NIH award (`OT2OD032701`) is treated as the funding instrument for that dataset, not as the referent. The CHoRUS GitHub organization and its 28 repositories are treated as tooling and documentation *about* the referent, not as the referent; consequently GitHub-level facts populate `machine_annotation_tools`, `external_resources` and `extension_mechanism`, and do not populate dataset-level identity slots. The **anticipated final** dataset (100,000 admissions, 9 modalities, 14 hospitals) is described in `description` as a stated future scope, not asserted as the referent's current composition.

This choice is held identically in both records.

---

## 2. Audit outcome summary

The audit returned 33 findings: 2 high, 12 medium, 15 low, 4 informational. No finding identified a fact lacking any basis in the declared bundle. The defects clustered into four groups:

1. **Paired-record structural divergence** (both high findings, plus five medium omissions) — the same entities typed differently in full and core.
2. **Over-assertion** — determinations imposed on the evidence (PI status, human-subjects status, at-risk designation, coined reviewing organizations, a governance intention recorded as a known bias).
3. **One internal contradiction** — the same acquisition event characterised two ways.
4. **Shape defects** — source commentary inside entity-name fields, multiple entities collapsed into one object, prose in single-value slots.

Changes were made in all four groups. Nine findings were resolved by leaving the record unchanged, with the justification recorded in §5.

---

## 3. Changes to the full record

### 3.1 Internal contradiction

| Slot | Before | After | Reason |
|---|---|---|---|
| `acquisition_methods[0].was_directly_observed` | `true` | *removed* | Contradicted `direct_collection.is_direct: false` for the same event. The bundle says only "Retrospective data collection" and describes extraction from hospital source systems. Whether the underlying clinical measurements count as "directly observed" is a determination the bundle does not make; under prefer-omission the boolean is dropped and `acquisition_details` retains the bundle-stated description of retrospective extraction from EHR, PACS, telemetry and EEG source systems. |

### 3.2 Over-assertion — removals

| Slot | Action | Reason |
|---|---|---|
| `human_subject_research` | **object removed entirely** | `involves_human_subjects: true` was an inference from the data being patient records. No source in the bundle makes an IRB or human-subjects determination about CHoRUS; the only IRB reference is "Navigating IRB, Data Compliance, and Quality Assurance in AI/ML Healthcare Research" as a *training curriculum topic* in the AIM-AHEAD programme. The declared evidencing fields (`irb_approval`, `ethics_review_board`, `regulatory_compliance`) were empty, so the object asserted a determination while carrying none of the structure that would support it. |
| `at_risk_populations` | **object removed entirely** | The bundle states that the released dataset draws from "ICU, PICU, and NICU". It does not designate any of these as an at-risk population and describes no protection specific to at-risk status; `special_protections` restated the general controlled-access terms already carried in `license_and_use_terms`. The ICU/PICU/NICU scope is retained where the bundle places it — in `instances[0].instance_type` and in the released-dataset figures in `description`. |
| `known_biases[1]` (`representation_bias`) | **object removed** | Its `bias_description` recorded that the project intends to "manage privacy and bias" — a governance intention, not a bias identified as present. The bundle nowhere states that representation bias is present in the dataset. The remaining `known_biases` entry, which concerns site-composition/selection effects arising from the 14 contributing hospitals within a 20-centre consortium, is retained; its `mitigation_strategy` now carries the bundle's federated-sampling statement ("Federated access will enable sampling methods to ensure a balanced and diverse cohort"). |
| `sensitive_elements[1]` | **object removed** | Attributed sensitivity to geographic-distance and social-determinant elements. The bundle lists these as contextual elements to be *included* ("data elements feature appropriate contextual factors such as geographic distance to the nearest hospital"); it does not characterise them as sensitive. The elements themselves remain described in the relevant file collection and in `variables`. |

### 3.3 Over-assertion — corrections

**`creators`** — restructured. The bundle names `ROSENTHAL, ERIC S.` as principal investigator of the NIH award. The other five named individuals appear only on a "Bridge2AI CHoRUS Leadership Team" slide, which assigns no PI status.

- `principal_investigator: true` retained on Eric Rosenthal only; removed from Bihorac, Jiang, Strekalova, Rashidi and Kwong.
- Per the v3 rule on class-ranged slots, `affiliations` is now populated on every Creator from the bundle: Massachusetts General Hospital (Rosenthal); University of Florida (Bihorac, Strekalova, Rashidi); UTHealth Houston (Jiang); Tufts University (Kwong).
- `credit_roles` remains unpopulated: the bundle assigns no CRediT-mappable role to any named individual, and the enum admits no value that the leadership-team listing supports.

**`ethical_reviews`** — reduced from two objects to one.

- The second object, whose `reviewing_organization` was the coined label "CHoRUS legal and ethics workstream", was removed.
- On the remaining object, `reviewing_organization` was removed. "Ethics (Ethical and Trustworthy AI)" is named in the NIH abstract as one of three *project pillars*, not as an organization that reviewed the dataset; presenting it as a reviewing organization was the record's framing.
- `review_details` retained and is now the sole content: community-facing ethics focus groups convened to determine what data is appropriate for public sharing, and analysis of the existing legal and regulatory landscape.
- `contact_person` remains empty — the bundle names no ethics contact.

### 3.4 Shape defects

| Slot | Change | Reason |
|---|---|---|
| `conforms_to` | Now `OMOP Common Data Model` | Previously packed five standards into one string. The abstract names OMOP as *the* standardisation target ("standardize data to the OMOP Common Data Model"). The per-modality standards (OHNLP, DICOM, WFDB, EDF+/Persyst) were already correctly carried on the individual collection objects and remain there; the top-level slot is single-valued and now holds a single standard. |
| `status` | Now `released` | Previously multi-sentence narrative. The Administration-directives notice from the website banner is retained in `regulatory_restrictions.regulatory_restrictions`, where it already appeared; the duplicate copy is gone. The released-vs-anticipated scope distinction is carried in `description`. |
| `created_by` | Now `CHoRUS Consortium` | The membership counts ("more than 60 members across 20 institutions") were removed from the creator-identity field. They are bundle-supported and already appear in `description`. |
| `funders[0].grantor` | Now `National Institutes of Health (NIH) Common Fund — Bridge2AI program` | Award recipient, fiscal year and dollar amount were removed from the grantor field. `grants` retains the identifiers `OT2OD032701` and `1OT2OD032701-01`. The award amount ($5,880,300) and fiscal year (2022) were **dropped** rather than relocated: FundingMechanism declares no field for either, and inventing a home for them in `description` would place award-administration facts in a dataset-description slot. |
| `license_and_use_terms.contact_person` | Now `Jared Houghtaling, Tufts Medicine (jared.houghtaling@tuftsmedicine.org)` | The slot declares a person; the previous value was a labelled two-address route. Houghtaling is the one access contact the bundle names as a person (he also appears as a Tufts lecturer in the curriculum table). The second access address, `dbold@emory.edu`, is unattributed in the bundle and is retained in `maintainers`, where it was already recorded. |
| `machine_annotation_tools` | Split from one object into **three** | The slot is multivalued and the previous single object paired three tools to three descriptions positionally. Now one object per tool: (1) OHNLP toolkit — clinical note extraction and tokenisation; (2) `privacy_scan_tool` — privacy scanning of medical records; (3) UF-Geocoding / DeGauss — geocoding of OMOP Location entities. `tool_accuracy` remains empty on all three; the bundle states no accuracy figure for any tool. |
| `maintainers` | Reduced from three objects to two; `role` populated | The object describing the GitHub organization's repository inventory (28 repositories, package status page) was removed: it recorded infrastructure facts, not a maintaining party. That content is retained in `external_resources` and `extension_mechanism`, where it answers the field. The two remaining maintainers now carry `role`: Ciera McCrary (MGH, Program Manager) as `other`, and the CHoRUS consortium access contacts as `academic_institution`. Maintainer declares no name field, so identity necessarily remains within `maintainer_details`. |
| `existing_uses` | Merged from two objects into one | The two objects both concerned the AIM-AHEAD Bridge2AI for Clinical Care Training Program and were not distinct entities. The single object now carries two `examples`: use by trainees in the AIM-AHEAD Bridge2AI for Clinical Care Training Program (Cohort 2, commencing 17 November 2025), and use in publications — both stated in the webinar ("Datasets are being used for training activities and publications"). |
| `missing_data_documentation[0].handling_strategy` | **removed**; `missing_data_patterns` expanded | The previous value described how site submission gaps are tracked and characterization reports returned to sites — a curation-workflow fact, not a strategy for handling missing values in the released data. The bundle states nothing about analytic handling of missing values. `missing_data_patterns` now carries the modality-level gaps the bundle does state: clinical notes stored locally except tokens; imaging limited to 1,000 images with de-identification in process for a larger cohort; EEG extraction in process; metadata "Planned" rather than present for clinical notes, imaging and EEG. The site status-tracking mechanism is retained in `extension_mechanism`. |
| `collection_timeframes[0]` | `start_date` and `end_date` **removed**; `timeframe_details` retained and expanded | `2022-09-01` and `2026-11-30` are the NIH award project start and end dates, not a data collection window. The underlying clinical data are retrospective and the bundle nowhere states their coverage period. `timeframe_details` now states plainly that the award runs 2022-09-01 to 2026-11-30, that collection is retrospective, that the coverage period of the clinical records is not stated in any source, and that the composition figures are an "As of August 2025" snapshot. |

### 3.5 Additions

| Slot | Addition | Reason |
|---|---|---|
| `license_and_use_terms.data_use_permission` | `institution_specific` | The enum field was empty while the free-text `license_terms` carried the constraint. Access requires a `.edu` email address, which the enum's `institution_specific` value expresses directly. No second enum value was added: the signed licensing agreement is a procedural requirement whose substantive terms the bundle does not disclose, so it cannot be mapped to `general_research_use`, `no_commercial_use` or any other declared value. |
| `license_and_use_terms.license_terms` | Clarifying clause added | Now states explicitly that the MIT License named in the bundle governs the CHoRUS software repositories on GitHub and is not the licence under which the dataset is distributed; dataset access is by registration and a signed licensing agreement. See §5 on the omission of top-level `license`. |

---

## 4. Changes to the core record

### 4.1 Structural divergence — the high findings

The audit's two high findings concern the same defect: the nine modality groupings were typed as `file_collections` in the full record and as `resources` in the core record, and the holdout test set — carried in the full record as `subsets` plus `splits` — had been folded into the core record's `resources` list alongside them.

Resolution required checking which slots `CoreDataset` actually declares. It declares `resources` and `subsets`; it does **not** declare `file_collections`, `splits`, `relationships`, `direct_collection`, `participant_privacy` or `third_party_sharing`.

Accordingly:

- **The nine modality groupings remain in `resources` in the core record.** `file_collections` is unavailable in `CoreDataset`, and `resources` (range `Dataset`) is the nearest declared home. This is recorded here as a schema-forced retyping, not a modelling disagreement: the **full record's `file_collections` typing is authoritative**. The nine groupings are, identically in both records: demographics; medication administration; procedures; nursing flowsheets; diagnoses; clinical notes; imaging; waveform telemetry; waveform EEG — each carrying its own `conforms_to` (OMOP / OMOP / OMOP / OMOP with extensions / OMOP / OHNLP / DICOM / WFDB / EDF+ and Persyst) and its access-control and metadata status.
- **The holdout test set was moved out of `resources` and into `subsets` in the core record**, matching its typing in the full record. It is a sequestered evaluation partition ("sequestering holdout datasets for external validation", "provision a holdout test set, accessible for model external validation"), not a component collection of the released data. Its `is_data_split: true` flag is set in both records. This removes the silent retyping the audit identified.
- **`splits` cannot be carried in the core record** because `CoreDataset` does not declare it. The holdout's split semantics are preserved in core through `subsets[…].is_data_split`. The full record retains both `subsets` and `splits`.

### 4.2 Slots present in full and absent from core

Four medium findings concerned core omissions with identical evidence support. All four are schema-forced, not editorial:

| Slot | Status |
|---|---|
| `relationships` | Not declared in `CoreDataset`. Full record retains it (per-admission linkage across modalities; 7,642 of the released admissions carry radiology data). |
| `direct_collection` | Not declared in `CoreDataset`. Full record retains it (`is_direct: false`). |
| `participant_privacy` | Not declared in `CoreDataset`. Full record retains it. |
| `third_party_sharing` | Not declared in `CoreDataset`. Full record retains it (`is_shared: true`). |

No evidence-supported fact was dropped from the core record for any reason other than the absence of a declaring slot.

### 4.3 Changes propagated from §3

Every change in §3 that touches a slot `CoreDataset` declares was applied identically to the core record: removal of `human_subject_research`, `at_risk_populations`, `known_biases[1]` and `sensitive_elements[1]`; the `creators` PI correction and affiliations; the `ethical_reviews` reduction; the `conforms_to`, `status`, `created_by`, `funders[0].grantor` and `license_and_use_terms.contact_person` corrections; the `machine_annotation_tools` split; the `maintainers` reduction; the `existing_uses` merge; the `collection_timeframes` date removal; and the `data_use_permission` and `license_terms` additions.

The two records now carry no divergent factual claim. Every difference between them is an absence in `CoreDataset`.

---

## 5. Findings resolved without change

### 5.1 The 45K / 50K / 100K figures — `instances[0].counts` left at `50000`

The audit flagged the bare integer as silently resolving a source disagreement. On review, the three figures do not disagree — they describe three different things:

- **50,000** — "Current Released Dataset … Patient admissions from ICU, PICU, and NICU" (`chorus4ai.org`).
- **over 45K** — "As of August 2025, covers 14 different hospitals with over 45K unique admissions" (Cohort 2 webinar, September 2025). An earlier snapshot of the same growing release.
- **100,000** — "Anticipated Final Dataset … Patient admissions" (`chorus4ai.org`). A stated future target. The NIH abstract's "more than 100,000 critically ill patients" is the same target.

The declared referent (§1) is the currently released dataset, for which 50,000 is the only figure. `counts` is therefore left at `50000`, and `description` continues to narrate all three figures with their sources and dates so that a reader is not left with an undated single number. No change.

### 5.2 `license` left unpopulated at dataset level

The bundle states, of the `chorus-ai` GitHub organization, "This project is licensed under the MIT License." That statement is scoped to the software repositories: individual repositories in the same listing carry MIT and Apache-2.0 badges, and the dataset itself is described throughout as controlled-access, requiring registration, a `.edu` address and a signed licensing agreement whose terms are not disclosed. Asserting `license: MIT` on the dataset would attach a permissive licence to a resource the bundle describes as restricted. The slot is left empty, and the distinction is now stated explicitly in `license_and_use_terms.license_terms` (§3.5).

### 5.3 `regulatory_restrictions.confidentiality_level: restricted` retained

The bundle's term is "Controlled access", applied uniformly across all nine modalities. `restricted` is the closest of the three declared enum values (`unrestricted`, `restricted`, `confidential`), and the mapping is one-step and non-elaborating. Retained; this report records that the value is a mapping of the bundle's "Controlled access" onto the enum rather than a verbatim source term.

### 5.4 `regulatory_restrictions.hipaa_compliant` left unpopulated

"HIPAA/GDPR compliance for OMOP/FHIR data" appears in the bundle only as a bullet under a training workshop title. It is a curriculum topic, not a compliance determination about CHoRUS. No value — including `under_review` or `not_applicable` — is supported.

### 5.5 `total_file_count` and `total_size_bytes` left unpopulated

The bundle gives "23 Tb — Waveform data" and "1.6 Billion — Rows of EHR OMOP data". Neither is a file count. 23 Tb is a single-modality subtotal, not a dataset total, and row counts are not bytes. Converting either into a dataset-level total would fabricate an aggregate the bundle does not provide. Both figures are retained in `description` and on the relevant modality objects, where they are accurate.

### 5.6 `doi`, `citation`, `download_url`, `version`, `issued` left unpopulated

Checked individually against the bundle. No DOI appears anywhere in the four sources. No recommended citation is given. There is no direct download URL — access is by registration form plus licensing agreement, and that route is recorded in `distribution_formats[…].access_urls` and `license_and_use_terms`, not as a `download_url`. No version identifier is published for the dataset (repository version metadata concerns software packages). No formal issuance date is stated; the dated facts in the bundle are the award period, the "As of August 2025" snapshot and the training-programme calendar, none of which is a dataset publication date.

### 5.7 Consent slots left unpopulated

`collection_consents`, `collection_notifications`, `consent_revocations` and `informed_consent` were each assessed. The bundle describes retrospective use of existing hospital records and "community-facing ethics focus groups to determine what data is appropriate for public sharing" — a community-consultation mechanism, not individual consent. Nothing in any source addresses individual consent, notification of collection, or revocation. All four omitted. The focus-group activity is recorded in `ethical_reviews[0].review_details`, which is what it answers.

### 5.8 `maintainers[*]` identity carried in free text

The `Maintainer` class declares only `maintainer_details` and `role`. There is no name field to populate. The audit's observation is correct but not actionable beyond adding `role`, which was done (§3.4).

---

## 6. Recorded conventions and source defects

**Minted identifiers.** `https://chorus4ai.org/dataset` is a constructed URI. The bundle publishes `https://chorus4ai.org/` as the project homepage and no dataset URI; `https://www.bridge2ai.org/chorus` appears in the GitHub contact block as an alternate project page and is carried in `page`. Child identifiers for the nine modality collections and the holdout subset are fragment identifiers minted under the dataset URI (e.g. `…#waveform-telemetry`). This is a local minting convention for structural addressability and should not be read as a claim that these URIs resolve.

**Transcription of `cmccrary@mgh.havard.edu`.** The maintainer contact is reproduced exactly as it appears in the bundle. The address contains an apparent typographical error in the domain ("havard" for "harvard"). Under the evidence boundary the source string is transcribed as given and not corrected; the defect originates in `chorus4ai.org`.

**`sampling_strategies` placement.** Populated at dataset level, unpopulated on `instances[0]`. This is intentional: the bundle's sampling statements — "sampling to ensure comprehensive sets of patient conditions and clinical treatment strategies" and "Federated access will enable sampling methods to ensure a balanced and diverse cohort" — describe cohort construction across the dataset, not the selection of a particular instance type. `is_representative` is left unset on the strategy object: the bundle states representativeness as an aim, not as an achieved or verified property, and `representative_verification` is correspondingly empty.

---

## 7. Final state

| | Full | Core |
|---|---|---|
| Target class | `Dataset` | `CoreDataset` |
| Populated top-level slots | **58** | **37** |
| Slots removed in Phase 4 | 4 (`human_subject_research`, `at_risk_populations`, plus object-level removals within `known_biases`, `sensitive_elements`, `ethical_reviews`, `maintainers`, `existing_uses`, `machine_annotation_tools` restructuring) | same, less those not declared in `CoreDataset` |
| Slots added in Phase 4 | 1 (`license_and_use_terms.data_use_permission`) | 1 |
| Validation | **passed** — `linkml-validate -s data_sheets_schema_all.yaml -C Dataset` | **passed** — `linkml-validate -s data_sheets_schema_core_all.yaml -C CoreDataset` |

**Reconciliation outcome:** reconciled. Both high findings resolved (holdout retyping corrected in core; `file_collections` / `resources` divergence documented as schema-forced with the full record authoritative). All five core-omission findings resolved as schema-forced and documented. All over-assertion findings resolved by removal or correction. The internal contradiction is resolved. All shape defects corrected. Nine findings resolved without change, each with the justification recorded above. No factual claim now differs between the paired records.