# Reconciliation Report — CHORUS

**Version label:** `2026-08-05_claude-opus-5-1m-generic-v3_rep1`
**Arm:** BASELINE (input documents only)
**Declared bundle:** `data/preprocessed/concatenated/CHORUS_preprocessed.txt` (4 sources: NIH RePORTER project 10472824; AIM-AHEAD Bridge2AI for Clinical Care Cohort 2 webinar; chorus4ai.org project site; chorus-ai GitHub organisation overview, 2025-11-14)
**Records reconciled:**
- Full — `data/d4d_concatenated/claudecode_agent/2026-08-05_claude-opus-5-1m-generic-v3_rep1/CHORUS_d4d.yaml`
- Core — `data/d4d_concatenated/claudecode_agent_core/2026-08-05_claude-opus-5-1m-generic-v3_rep1/CHORUS_d4d_core.yaml`

---

## 1. Referent decision

`Dataset` admits one referent. The declared bundle describes three separable things: (a) the CHoRUS **dataset** — the multi-modal, controlled-access critical-care data collection; (b) the CHoRUS **project/network** — the Bridge2AI data generation project with its Data, Ethics and People pillars; and (c) the CHoRUS **GitHub software organisation** — 28 repositories of tooling, SOPs and mappings.

Both records take **(a), the CHoRUS dataset**, as the referent. Project- and organisation-level facts are admitted only where they characterise the dataset (funding, collectors, ethics posture, access route); the GitHub organisation is represented as an `external_resources` entry and as the source of `ip_restrictions`, not as the record subject. This choice is now applied identically in both records; the audit's high-severity findings were in substantial part a failure to hold it consistently.

---

## 2. What the audit found

Twenty-six findings: 3 high, 6 medium, 17 low. No substantial fabrication was detected. One unsupported identifier was found. The dominant defects were **structural** — slot selection and full/core divergence — rather than factual.

| Class of defect | Count | Disposition |
|---|---|---|
| Slot mis-selection (core `resources` vs `subsets`/`splits`) | 3 high | Changed |
| Unreconciled full/core divergence | 3 medium | 2 changed, 1 documented |
| Unsupported identifier | 1 medium | Changed |
| Declared field empty while evidence sits in prose (v3 rule) | 4 (1 medium, 3 low) | Changed |
| Empty multivalued slot | 1 medium | Changed |
| Silent resolution of a documented source disagreement | 1 medium | Changed |
| Invented collective labels / editorial annotation in values | 3 low | Changed |
| Coined labels in free-text fields, unpopulated enums where bundle is silent | 6 low | Left as-is, documented |
| Verified-correct omissions | 5 low | Left as-is, documented |

---

## 3. Changes applied

### 3.1 High severity — structural realignment of the core record

**`resources` removed from core.** The core record had placed the five modality partitions in `resources` (range `Dataset`, described as sub-resources or component datasets) and had added a sixth entry, `#holdout`, duplicating the full record's `splits` content. The modality partitions are logical partitions of the dataset's composition, not component datasets; the holdout is a split. The slot is now absent from both records.

**`subsets` added to core.** The five modality partitions — OMOP structured EHR, tokenized clinical notes (OHNLP), imaging (DICOM), waveform telemetry (WFDB), waveform EEG (EDF+/Persyst) — are now carried in `subsets` in core, matching the full record entry-for-entry. Evidence: the webinar's nine-row data-type table giving, per modality, the data standard, access control and metadata status.

**`splits` added to core.** Restored from the NIH abstract ("The dataset will also provision a holdout test set, accessible for model external validation to aid marketplace adoption of AI-developed models") and the GitHub overview ("sequestering holdout datasets for external validation"). Now identical in both records.

Net effect: the two records now represent the same evidence at the same slots. Core gains 2 slots and loses 1.

### 3.2 Medium severity

**`related_datasets.target_dataset` — unsupported identifier replaced (full).** The value `https://www.bridge2ai.org/` appears nowhere in the bundle; the bundle gives `www.bridge2ai.org/chorus` (GitHub contact line) and the named entity "Bridge2AI Consortium". The relationship itself is well supported ("The CHoRUS project is one data generation project of four in the National Institute of Health (NIH) funded Bridge2AI consortium"). `target_dataset` now carries the attested entity name rather than a constructed URL; `relationship_type: is_part_of` is unchanged.

**`related_datasets` added to core.** Core had expressed the Bridge2AI relationship as a fourth `external_resources` entry while full used `related_datasets`. `related_datasets` is now present and identical in both; the redundant `external_resources` entry was removed from core.

**`other_tasks: []` removed from full.** An empty multivalued slot asserts nothing while occupying a populated-slot position. Core already omitted it; both now omit it.

**`instances.counts` removed from both.** The bundle supplies three irreconcilable admission figures from three sources: "over 45K unique admissions" as of August 2025 (webinar), "50,000 patient admissions from ICU, PICU, and NICU" as the current released dataset (website), and 100,000 as the anticipated final figure (website) / "more than 100,000 critically ill patients" (NIH abstract). The structured `counts` field can hold only one and was silently resolving the disagreement in favour of 50,000. The field is now omitted and all three figures remain in `instances.description`, each attributed to its source and its scope (snapshot / current release / anticipated final). This follows the rule that disagreement is represented, not silently arbitrated.

**`collection_timeframes.start_date` / `end_date` populated in full.** `CollectionTimeframe` declares both fields and NIH RePORTER states both explicitly (project start `2022-09-01`, project end `2026-11-30`). Full had carried them only in `timeframe_details` prose; core had them correct. Both records now populate the declared date fields, with `timeframe_details` retained for the qualification that these are the award period rather than an attested data-collection window.

### 3.3 Low severity — declared fields populated (v3 rule)

**`funders.grants` populated (both).** The identifiers the field exists to carry were in `description` prose: core project number `OT2OD032701`, project number `1OT2OD032701-01`, application ID `10472824`. All three now sit in `grants`; `grantor` (NIH / NIH Common Fund Bridge2AI program) is unchanged.

**`external_resources.external_resources` populated (both).** URLs were embedded in `description` prose. The locators — `https://github.com/chorus-ai`, `https://chorus4ai.org/` — now sit in the declared field.

**`license_and_use_terms.contact_person` cleaned (both).** The value was a compound `"Access requests: dbold@emory.edu or jared.houghtaling@tuftsmedicine.org"` — a label plus two addresses in a single-valued person field. It now carries one named contact, Jared Houghtaling (`jared.houghtaling@tuftsmedicine.org`), named in both the GitHub contact section and the webinar curriculum table; the second access address is retained in the access-route description alongside the registration, licensing-agreement and `.edu`-address requirements.

**`maintainers` renamed (both).** Two of three `name` values were invented collective labels ("CHoRUS data access contacts", "CHoRUS software contributors") holding the bundle's actual named contacts in `maintainer_details` prose. The access-contact object is replaced by two objects: one named **Jared Houghtaling** (Tufts Medicine), and one identified by the attested address `dbold@emory.edu`, for which the bundle supplies no personal name. The software-contributor object is retained but reframed against what the bundle states — the chorus-developer web guide and the package status page giving versions and maintainers — rather than a coined collective name.

**Editorial annotation removed (both).** The Ciera McCrary contact value carried the qualifier "as printed on the site" about the apparent typo in `cmccrary@mgh.havard.edu`. The address is retained verbatim as the bundle gives it; the annotation is removed, being commentary about the source rather than dataset fact.

**`ethical_reviews.reviewing_organization` removed (both).** The value ("CHoRUS consortium ethics activity (Ethics pillar of the CHoRUS data generation project)") was a descriptive construction, not a named reviewing body; the bundle names no IRB or ethics committee for this dataset. The substance — community-facing ethics focus groups determining what data is appropriate for public sharing, and analysis of the existing legal and regulatory landscape — is retained in `review_details`. The webinar's "Navigating IRB, Data Compliance and Quality Assurance" item was confirmed to be training-curriculum content and is not treated as a review of this dataset.

**`creators` — collective aggregate removed (both).** The seventh entry, "CHoRUS Consortium", was a collective of a different kind from the six named individuals (Rosenthal, Bihorac, Jiang, Strekalova, Rashidi, Kwong) and carried organisational-scope commentary ("more than 60 CHoRUS consortium members across 20 different institutions") in place of authorship information. It is removed. The 20-institution / 14-acquisition-centre scope is already carried, correctly, in `data_collectors`. Rosenthal retains `principal_investigator: true` per NIH RePORTER; affiliations are unchanged.

**`status` narrowed (both).** The value combined the award period with the website's "under review for potential modification in compliance with Administration directives" banner. The banner concerns the web page, not the dataset resource, and is now retained verbatim and attributed in the top-level `description`. `status` carries the resource status only.

**`distribution_dates` removed (both).** The object populated only `description` and left the declared `release_dates` empty, because the bundle supplies no release date — only "as of August 2025" snapshot language. Under the rule that a slot must answer the field rather than record that the answer is pending, the slot is omitted; the August 2025 snapshot is retained where it belongs, in the composition description.

**`at_risk_populations.at_risk_groups_included` tightened (both).** The value now quotes the attested phrase — admissions from ICU, PICU and NICU — without asserting that minors are included, which the bundle nowhere states. `special_protections`, `guardian_consent` and `assent_procedures` remain empty.

---

## 4. Left as-is, with reasons

**`direct_collection` in full only — documented divergence, not corrected.** Full carries a `DirectCollection` object with `is_direct` populated (data extracted from hospital EHR, PACS, monitor-gateway and EEG systems by contributing sites, not collected from individuals). Core carries the same fact through `acquisition_methods` (`was_directly_observed` / `was_reported_by_subjects`). Both are faithful to the evidence and neither is wrong; the profiles differ in granularity, not in claim. Recorded here rather than forced into artificial identity.

**`known_biases.bias_type` left unpopulated.** The bundle documents bias as a risk being managed ("determine the ethical and legal approaches to manage privacy and bias"; "sampling methods to ensure a balanced and diverse cohort") but never names a bias category. Selecting from the enum — `selection_bias`, `representation_bias`, `sampling_bias` — would be the agent's classification, not the bundle's. The object is retained for its `mitigation_strategy` content, with `bias_description` stating plainly that this is an anticipated risk under active management rather than a bias observed in the delivered data.

**`license_and_use_terms.data_use_permission` left unpopulated.** The registration form, signed licensing agreement and `.edu`-address requirement plausibly suggest `institution_specific`, but no source states a permission category. The conservative omission stands; the concrete requirements are recorded in `license_terms`.

**`maintainers[].role` left unpopulated.** The bundle gives affiliations and job titles ("MGH, Program Manager") that do not map onto the enum's categories without invention. Omitted rather than shrugged into `other`.

**`intended_uses[].use_category` retained as coined labels.** `IntendedUse` declares no enum for this slot, so "research", "model validation" and "training and education" are shape-valid free text. They are agent-coined groupings of bundle-attested uses (external validation of AI models; training activities and publications; the AIM-AHEAD trainee programme). Retained, with the note that the labels are organisational rather than quoted.

**`data_collectors[].role` retained as free text.** Not enum-constrained. "clinical validation and semantic mapping" describes an activity rather than a role, but it is what the bundle attests of the clinical collaborators.

**`human_subject_research` — siblings left empty.** `involves_human_subjects: true` is well supported (hospital admissions, critically ill patients, de-identification in process). `irb_approval`, `ethics_review_board`, `regulatory_compliance` and `special_populations` are absent from the bundle and remain empty. Recorded so the gap is not read as oversight.

**`variables` omitted.** The webinar's nine-row table is a modality inventory, not a variable/column inventory; its content is fully carried by `subsets` and `distribution_formats`. Borderline, resolved toward omission.

**Verified-correct omissions.** `doi` — none in the bundle; the NIH award number was not repurposed as one. `download_url` — the dataset is controlled-access via registration and enclave provisioning; the access route is in `license_and_use_terms`, the field it answers, not in a URL field. `is_tabular` — the dataset is explicitly multimodal (OMOP tables, DICOM, WFDB, EDF+/Persyst, tokenized text), so neither `true` nor `false` is supportable. Top-level `license` — the MIT License in the GitHub overview governs the software organisation, not the dataset; it is confined to `ip_restrictions`, where it is scoped to the CHoRUS code repositories. Each is a deliberate, evidence-driven omission.

---

## 5. Outcome

| | Full | Core |
|---|---|---|
| Populated slots before reconciliation | 46 | 32 |
| Populated slots after reconciliation | 44 | 33 |
| Slots added | 0 | `subsets`, `splits`, `related_datasets` |
| Slots removed | `other_tasks`, `distribution_dates` | `resources`, `distribution_dates` |
| Values corrected in place | 9 | 8 |
| Validates | yes | yes |

Full: `linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_all.yaml -C Dataset` — **pass**.
Core: `linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml -C CoreDataset` — **pass**.

**Reconciliation outcome: reconciled.** The one unsupported identifier is removed. All three high-severity structural findings are resolved and the records now express the same evidence at the same slots, with a single documented and justified divergence (`direct_collection`). No factual claim in either record now rests on anything outside the declared bundle, and no content was drawn from any prior D4D record.