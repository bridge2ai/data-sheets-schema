# CHORUS — D4D Full/Core Reconciliation Report

**Version label:** `2026-08-13_claude-opus-5-api-generic_rep1`
**Arm:** BASELINE (input documents only)
**Source bundle:** `data/preprocessed/concatenated/CHORUS_preprocessed.txt` (4 files: NIH RePORTER project 10472824, AIM-AHEAD Cohort 2 informational webinar, chorus4ai.org homepage, chorus-ai GitHub organization overview)
**Records reconciled:**
- Full — `data/d4d_concatenated/claudecode_agent/2026-08-13_claude-opus-5-api-generic_rep1/CHORUS_d4d.yaml`
- Core — `data/d4d_concatenated/claudecode_agent_core/2026-08-13_claude-opus-5-api-generic_rep1/CHORUS_d4d_core.yaml`

---

## 1. Referent decision (held constant across both records)

`Dataset` admits one referent. The bundle describes three candidate referents that are easy to conflate:

1. The **CHoRUS clinical dataset** — the multi-modal, multi-center critical-care data collection held under controlled access in the cloud enclave.
2. The **CHoRUS project / consortium** — the NIH OT2OD032701 data generation project with its Data, Ethics, and People pillars.
3. The **AIM-AHEAD Bridge2AI for Clinical Care Training Program** — a downstream program that provides access to (1).

**Decision: referent is (1), the CHoRUS clinical dataset.** Both records describe the dataset. Project-level facts (award, period, pillars, workforce development) are admitted only where they bear on the dataset — funding, governance, collection timeframe caveats. Training-program facts are admitted only where the program is evidence of dataset use or access conditions.

The audit's findings on `intended_uses[intended-use-education]`, `existing_uses.examples`, and `extension_mechanism` are all failures to hold this line. They are corrected below.

---

## 2. Audit outcome summary

47 findings: 4 high, 24 medium, 19 low. Findings cluster into six classes:

| Class | Findings | Disposition |
|---|---|---|
| Typed assertion outruns evidence | 6 | All corrected — slot removed or downgraded to prose |
| Numeric misattribution | 3 | All corrected |
| Unsupported absence claims | 2 | All corrected (removed) |
| Slot-semantics drift | 9 | 7 corrected, 2 retained with rationale |
| Supported-but-omitted evidence | 3 | All corrected (slots populated) |
| Full/core structural divergence | 4 | All corrected (aligned) |
| Presentation / residual | 20 | 11 corrected, 9 retained with rationale |

Both records validate after changes.

---

## 3. Changes made — high severity

### 3.1 `data_governance.committee_contact` — removed (both records)

**Finding:** Jared Houghtaling placed in a slot whose semantics are "contact for the access committee." The bundle's only statement is a GitHub README line: `Request access: dbold@emory.edu or jared.houghtaling@tuftsmedicine.org`. No committee is described anywhere in the bundle. The choice between two co-equal emails was arbitrary.

**Change:** `committee_contact` removed. `committee_name`, `committee_members`, and `appeal_process` were already absent and remain so. Both access-request emails now appear together in `access_review_process` prose, neither privileged:

> Access requests are directed to one of two contacts listed on the CHoRUS GitHub organization README: dbold@emory.edu or jared.houghtaling@tuftsmedicine.org. The bundle describes no review committee, no decision criteria, and no appeal route.

**Rationale:** The slot's range is `Person` and its meaning is committee-specific. Populating it with a request-routing email asserts an oversight structure the bundle does not evidence. Prose in `access_review_process` carries the same fact without the false structural claim.

### 3.2 `instances[instance-admission].counts` — removed (both records)

**Finding:** `counts: 50000` asserted while the object's own `notes` recorded 45,000 (August 2025) and 100,000 (anticipated). A structured numeric slot was silently resolving a three-way conflict the bundle does not resolve.

**Change:** `counts` removed from the object. All three figures are now stated in `instance_type` and `notes` with their sources and dates attached:

> The chorus4ai.org "Current Released Dataset" panel gives 50,000 patient admissions from ICU, PICU, and NICU. The September 2025 AIM-AHEAD webinar states that as of August 2025 the dataset covers 14 hospitals with over 45,000 unique admissions. The chorus4ai.org "Anticipated Final Dataset" panel gives 100,000 patient admissions. The bundle does not date the website panels or reconcile them with the webinar figure.

**Rationale:** Uniform decision rule — where sources disagree, represent what the evidence states rather than silently selecting one. A single integer cannot do that. Omission of `counts` is the correct answer here; the numbers are not lost, they are recorded with their provenance.

### 3.3 `creators.affiliations` — narrowed and re-scoped (full record)

**Finding:** Four `Organization` entries (MGH, University of Florida, UTHealth Houston, Tufts) presented as the creator's affiliation set, while the bundle states the collaboration spans 20 academic centers of which 14 are Data Acquisition centers. The four are the institutions of the six named leadership individuals, not the consortium.

**Change:** The four organizations are retained but the `Creator` object is restructured so the affiliation list is unambiguously the leadership-team affiliation set, not the consortium roster. `notes` on the Creator now reads:

> The four affiliations listed are the institutions of the six individuals named as the Bridge2AI CHoRUS leadership team in the September 2025 AIM-AHEAD webinar (Eric Rosenthal, Massachusetts General Hospital; Azra Bihorac, Yulia Strekalova, and Parisa Rashidi, University of Florida; Xiaoqian Jiang, UTHealth Houston; Manlik Kwong, Tufts University). They are not the full creator set: the GitHub organization overview states the collaboration spans 20 academic centers, of which 14 contribute as Data Acquisition centers, and chorus4ai.org gives 60+ consortium members across 20 institutions. The bundle does not enumerate the 20 institutions.

**Rationale:** The affiliations are supported; the implied scope was not. The correction is in framing, not in removing evidenced content.

### 3.4 `creators` / `principal_investigator` — split into two claims (both records)

**Finding:** `name: CHoRUS Consortium` paired with `principal_investigator: Rosenthal, Eric S.` joins two distinct source statements. The bundle names Rosenthal PI of NIH application 10472824 (organization: Massachusetts General Hospital); it does not designate him PI of the consortium as a creator entity.

**Change:** `principal_investigator` retained on the Creator object (it is the closest structural home the schema offers and the association is real), but the source of the designation is now stated explicitly in `notes` rather than left implicit:

> Eric S. Rosenthal is recorded as principal investigator of NIH application 10472824 / project 1OT2OD032701-01, organization Massachusetts General Hospital, per the NIH RePORTER record. The webinar lists him first among the Bridge2AI CHoRUS leadership team. The bundle does not use the title "consortium principal investigator."

**Rationale:** Removing the slot would discard a well-evidenced fact. Annotating its exact scope is the proportionate correction.

---

## 4. Changes made — medium severity

### 4.1 `instances[instance-imaging].counts: 7642` — moved to correct unit

**Finding:** 7,642 attached to an object whose `instance_type` is an imaging study. The source says "7,642 Admissions with Radiology Data."

**Change:** `counts` removed from the imaging instance. The figure now appears in `instance_type` / `notes` as an admission-level count:

> chorus4ai.org reports 7,642 admissions with radiology data in the current released dataset. This is a count of admissions, not of imaging studies; the bundle does not state how many imaging studies those admissions comprise. The webinar separately states that as of September 2025 approximately 1,000 images were available, with de-identification in process for a larger cohort.

**Rationale:** Attaching an admission count to a study-level instance is a category error that would corrupt any aggregation over `counts`.

### 4.2 `instances[instance-omop-row].data_substrate` — removed

**Finding:** `B2AI_SUBSTRATE:37` (Relational Database) assigned where the bundle states only that data are standardized to OMOP CDM and held in a cloud enclave.

**Change:** Slot removed. The digest instruction is explicit: *"If no term fits, omit the slot rather than approximate."*

**Rationale:** OMOP CDM is a common data model, not a storage substrate. No bundle statement identifies the physical substrate.

### 4.3 `anomalies: []` — removed (full record)

**Finding:** An empty list asserts that no anomalies are known. The bundle is silent, which is not the same claim.

**Change:** Slot removed entirely. This also resolves a full/core divergence, since the core record had correctly omitted it.

### 4.4 `external_resources.archival: false` ×4 — removed

**Finding:** Four boolean assertions about archival status that the bundle nowhere addresses.

**Change:** All four `archival` keys removed. The four external resources (chorus4ai.org, github.com/chorus-ai, the NIH RePORTER record, the AIM-AHEAD webinar PDF) are retained with `external_resources` URLs and descriptive `notes`.

### 4.5 `known_biases` — downgraded to `DatasetLimitation`

**Finding:** `bias_type: representation_bias` asserted while the object's own `source_caveats` conceded the bundle reports only mitigation intent and design goals — never a measured or observed bias.

**Change:** The `DatasetBias` object is removed. Its evidenced content is relocated to `known_limitations` as a `DatasetLimitation` with `limitation_type: representativeness_limitation`, worded as a stated design concern rather than an observed property:

> The bundle states design intentions bearing on representativeness — federated access enabling sampling methods to ensure a balanced and diverse cohort, sampling to ensure comprehensive sets of patient conditions and treatment strategies, patient-focused efforts to manage privacy and bias while accounting for social determinants of health, and an aim to build the most diverse high-resolution ethically sourced AI-ready dataset. It reports no measurement of representativeness, no cohort demographics, and no evaluation of whether these intentions were met.

**Rationale:** `bias_type` is a typed, queryable term. Emitting it on the strength of a mitigation statement would make the corpus answer "what biases are documented?" with a project aspiration. `DatasetLimitation` with an explicit "no measurement reported" caveat states exactly what is known.

### 4.6 `at_risk_populations.at_risk_groups_included: true` — removed

**Finding:** The boolean was derived from the presence of PICU and NICU admissions. The bundle states cohort composition; it makes no at-risk determination and describes no safeguards, assent, or guardian consent.

**Change:** Entire `at_risk_populations` object removed. The PICU/NICU fact is retained where it belongs — in `subpopulations` (see 4.15) and in the admission instance description.

**Rationale:** The slot exists to record protections for at-risk populations. With `special_protections`, `assent_procedures`, and `guardian_consent` all unevidenced, a lone `true` converts a cohort fact into a governance claim.

### 4.7 `acquisition_methods.was_directly_observed` / `direct_collection.is_direct` — reconciled

**Finding:** Full record asserted `was_directly_observed: true` while its own `direct_collection` prose said data were obtained "rather than through a purpose-built collection from individuals," and left `is_direct` unpopulated.

**Change:** `was_directly_observed` removed. `direct_collection.is_direct: false` now populated, with details:

> Data are retrospectively extracted from existing hospital systems — electronic health records, PACS, bedside monitor and gateway/middleware telemetry, and hospital EEG databases — by staff at the 14 Data Acquisition centers. They are not collected from individuals for the purpose of this dataset.

**Rationale:** Retrospective extraction of records generated during routine care is not direct observation by the dataset creators. Setting `is_direct: false` and dropping the conflicting boolean resolves the contradiction in the direction the prose already supported.

### 4.8 `direct_collection` and `splits` — full/core structural divergence resolved

**Finding:** `splits` present in full, dissolved into `sampling_strategies` prose in core. `direct_collection` present in full, folded into `acquisition_methods` in core.

**Change:** Both slots verified present in the core schema and now populated identically in both records. The holdout-set evidence is carried by `splits` in both:

> The NIH RePORTER abstract states the dataset will provision a holdout test set, accessible for model external validation to aid marketplace adoption of AI-developed models. The bundle gives no split proportions, no partition criteria, and no statement of whether the holdout set exists in the currently released data.

Duplicated holdout text removed from `sampling_strategies` in the core record.

**Rationale:** Paired records must represent the same evidence in the same structural place. Divergence here was generation artifact, not schema constraint.

### 4.9 `license_and_use_terms.data_use_permission` — populated

**Finding:** Slot empty despite enumerable evidence: signed licensing agreement, `.edu` institutional email requirement, program-scoped access route.

**Change:** Populated with `institution_specific`. `license_terms` states the underlying facts:

> Access to the dataset via the AIM-AHEAD Bridge2AI for Clinical Care Training Program requires participants to sign a licensing agreement included in the registration form before access is granted, and requires a ".edu" email address; program administrators state they will assist with this access where needed and that the requirement is not a barrier to acceptance into the program. The bundle does not reproduce the licensing agreement text and does not state the terms governing access outside the training program.

`project_specific` was considered and rejected: the `.edu` requirement is an institutional-affiliation condition, and the bundle does not confine dataset use to a named project.

**Rationale:** The slot exists so the corpus can be queried for use permissions. Leaving it empty while the terms sit in prose defeats that.

### 4.10 `variables` — populated

**Finding:** Slot omitted entirely, though the webinar table is the richest field-level source in the bundle, enumerating nine data types with their standards, access controls, and metadata status.

**Change:** Nine `VariableMetadata` entries added, one per row of the webinar table, each with `variable_name`, `data_type` where the table supports one, and `notes` carrying the standard / access-control / metadata-status triple as printed. Examples:

- `demographics` — OMOP; controlled access; metadata yes (OMOP schema)
- `medication_administration` — OMOP; controlled; metadata yes (OMOP schema); *dosing time-stamped upon each infusion change or dose administration*
- `nursing_flowsheets` — OMOP; controlled; metadata yes (OMOP schema with extensions); *high-frequency documentation*
- `clinical_notes` — OHNLP; controlled; metadata planned; *extracted and tokenized using OHNLP toolkit*
- `imaging` — DICOM; controlled; metadata planned; *from PACS*
- `waveform_telemetry` — WFDB; controlled; metadata yes (PhysioNet schema extended); *bedside monitors, gateway/middleware*
- `waveform_eeg` — EDF+ and Persyst; controlled; metadata yes (open source EDF+ and Persyst schema); *hospital database*

Plus `geographic_distance_to_nearest_hospital` from the NIH abstract's contextual-factors clause.

`source_caveats` on the record notes that the webinar table's column alignment is imperfect in the extracted text and that two `Metadata` cells could not be assigned to a row with confidence.

**Rationale:** These are field-level descriptors and `variables` is the slot for them. Previously they were dispersed across `instances`, `description`, and `subpopulations`, none of which is queryable as a field inventory.

### 4.11 `conforms_to_standard` — bare `OTHER` resolved

**Finding:** A single `OTHER` term standing for three distinct unregistered standards (EDF+, Persyst, OHNLP), which cannot be resolved on query.

**Change:** Registered terms retained: `OMOP_CDM`, `DICOM`, `WFDB`. `OTHER` retained once (the enum offers no per-standard mechanism) but `conforms_to` now names all six standards explicitly and in order, and `source_caveats` states which three the `OTHER` term covers:

> The single OTHER term in conforms_to_standard stands for three standards named in the bundle that the enum does not register: EDF+ and Persyst (EEG waveform) and the OHNLP open-source schema (tokenized clinical notes).

### 4.12 `publisher` — removed

**Finding:** Set to the project website URL, identical to `id` and `page`. No publisher entity is named in the bundle.

**Change:** Slot removed.

### 4.13 `status` — replaced with the source's own statement

**Finding:** Synthesized characterization ("Under active acquisition and phased release") where the bundle's only status statement about the resource is the website banner.

**Change:** `status` now carries the banner verbatim, with its typo preserved and marked:

> This repoitory is under review for potential modification in compliance with Administration directives. [transcribed as printed on chorus4ai.org]

The banner is removed from `notes` (it was duplicated there).

**Rationale:** The generated phrasing was an interpretation. The banner is what the source says about the resource's status.

### 4.14 `data_governance.accountable_organization` — removed

**Finding:** `CHoRUS Consortium` asserted. The bundle names MGH as the NIH awardee organization and states website content is "solely the responsibility of the authors"; it designates no accountable organization for the data.

**Change:** Slot removed. `notes` records the awardee fact:

> The NIH RePORTER record gives Massachusetts General Hospital as the awardee organization for project 1OT2OD032701-01 (award OT2OD032701). The bundle does not designate an organization accountable for the dataset over time.

### 4.15 `subpopulations[subpop-sdoh]` — re-homed

**Finding:** SDoH and geographic-distance data elements recorded as a subpopulation. Variables enabling subgroup characterization are not a represented group.

**Change:** The `subpop-sdoh` object is removed; its content moves to `variables` (see 4.10). The remaining subpopulation object — ICU / PICU / NICU admissions — is retained, since those are genuinely represented groups:

> chorus4ai.org states the current released dataset comprises 50,000 patient admissions from ICU, PICU, and NICU. The bundle gives no breakdown across the three unit types and no demographic distribution.

### 4.16 `machine_annotation_tools` — three of four entries reclassified

**Finding:** OHNLP toolkit, DeGauss, privacy_scan_tool, and CTP-deid grouped as annotation tools. Only OHNLP annotates; the others were also duplicated into `is_deidentified.method` and `preprocessing_strategies`.

**Change:**
- `machine_annotation_tools` retains **OHNLP toolkit only** (clinical notes "extracted and tokenized using OHNLP toolkit").
- DeGauss remains in `preprocessing_strategies` (UF-Geocoding: "Open source code to geocode OMOP Location entities via DeGauss").
- `privacy_scan_tool` and `CTP-deid` remain in `is_deidentified.method` only; duplicate entries elsewhere removed.

### 4.17 `extension_mechanism` — re-scoped to dataset, then removed

**Finding:** Described project contribution workflows (data site SOPs, clinical mapping, software development) rather than mechanisms for extending the dataset.

**Change:** Slot removed. The contribution-workflow content is retained where it is a project fact rather than a dataset-extension fact: in `data_collectors.collector_details` (site extraction and SOP process) and in `external_resources` (the chorus-ai repository space, chorus-mapping, Chorus_SOP).

**Rationale:** Referent discipline. Nothing in the bundle describes how a recipient of the dataset could contribute additions or corrections to it.

### 4.18 `cleaning_strategies` — removed

**Finding:** Cited CHoRUSReports and SOP validation. CHoRUSReports produces characterization reports *returned to sites after submission* — a feedback artifact. No outlier removal, deduplication, or error correction is described anywhere in the bundle.

**Change:** Slot removed. The CHoRUSReports and SOP-validation facts are retained in `data_collectors.collector_details` and `external_resources`, described as what they are.

### 4.19 `data_governance.access_review_process` — two access paths separated

**Finding:** Conflated general dataset access (two request emails) with the training-program route (registration form, licensing agreement, `.edu` email).

**Change:** Rewritten to distinguish them:

> Two access routes appear in the bundle and are not stated to be the same process. (1) The CHoRUS GitHub organization README directs access requests to dbold@emory.edu or jared.houghtaling@tuftsmedicine.org, with no further detail on review. (2) Within the AIM-AHEAD Bridge2AI for Clinical Care Training Program, participants complete a registration form with name, email, and institution, sign a licensing agreement included in that form, and require a ".edu" email address; access and provisioned compute are then confirmed by email. The bundle does not state whether route (2) conditions apply to route (1), and describes no review committee, criteria, decision timeframe, or appeal process for either.

### 4.20 `existing_uses.examples` — narrowed to dataset use

**Finding:** Mixed a supported dataset-use claim with AIM-AHEAD program mechanics (30 trainees, coursework, posters, manuscripts) that describe the program, not dataset use.

**Change:** `examples` reduced to the two evidenced dataset uses:

> The September 2025 AIM-AHEAD webinar states that the datasets are being used for training activities and publications. The bundle names no specific publication, model, or analysis.

Program mechanics removed from this slot; the program's existence as an access and training vehicle is recorded once in `data_governance.access_review_process` and `intended_uses`.

### 4.21 `intended_uses[intended-use-education]` — re-scoped

**Finding:** Described the AIM-AHEAD curriculum (Jupyter notebooks, OHDSI stack, OMOP CDM instruction) as an intended use of the dataset, attributing curriculum design to dataset intent.

**Change:** Rewritten so the dataset's role is the subject:

> The dataset is used as the working material for hands-on AI/ML training. The AIM-AHEAD Bridge2AI for Clinical Care Training Program expands access to CHoRUS data through engagement, training, and mentorship, and trainees apply AI/ML methods to it on the Bridge2AI AI/ML for Clinical Care Collaborative Cloud. The curriculum content described in the bundle (Python, OHDSI tool stack, OMOP common data model, clinical deep learning, ethics of clinical AI) is a property of the training program rather than of the dataset.

The two evidenced dataset-intent uses from the NIH abstract — characterizing acute and critical care illness, predicting complications, measuring treatment response; and external validation via the holdout set — are retained unchanged as separate `IntendedUse` objects.

### 4.22 `maintainers.role: other` — entry restructured

**Finding:** The GitHub-organization entry populated a maintainer slot with infrastructure rather than a maintaining party.

**Change:** The GitHub-organization entry is removed from `maintainers`; the repository space is already recorded in `external_resources`. `maintainers` retains the two entries the bundle supports as parties: the program manager (Ciera McCrary, MGH) and the two access-request contacts. `role` values are left unpopulated, since the enum offers no fitting term for "program manager" or "access contact" and approximation is worse than omission.

### 4.23 `data_collectors.role` — prose moved to `collector_details`

**Finding:** `role` carried multi-clause descriptive prose duplicating `collector_details`.

**Change:** `role` removed (the enum-free `role` here still names a role, not a description; no fitting short designation is available). Full text consolidated into `collector_details`:

> The GitHub organization overview states the collaboration spans 20 academic centers, of which 14 contribute as Data Acquisition centers. Site data managers extract and submit CHoRUS-specific clinical data extracts following validated SOPs hosted in the Chorus_SOP repository, and provide regular status updates tracked in the Standards Project and Data Acquisition Project boards.

### 4.24 `distribution_formats.format` — format values separated from access commentary

**Finding:** `format` values carried access-control and metadata-status commentary rather than format designations.

**Change:** `format` now holds the format alone (`OMOP CDM`, `DICOM`, `WFDB`, `EDF+`, `Persyst`, `OHNLP schema`). Access control and metadata status move to the per-format `notes`, and are additionally carried per-variable in `variables` (4.10). `media_type`, `download_url`, and `access_urls` remain unpopulated — the bundle gives none.

### 4.25 `human_subject_research` — misleading pairing corrected

**Finding:** `involves_human_subjects: true` with `irb_approval`, `ethics_review_board`, and `regulatory_compliance` all empty, while `ethical_reviews` was populated with a pillar-derived object — together implying documented oversight.

**Change:** `involves_human_subjects: true` retained (well supported: the dataset comprises patient records from >100,000 critically ill patients). `notes` now states the gap directly, and the `ethical_reviews` object is corrected per 4.26 so the two slots no longer conflict:

> The bundle states no IRB approval, names no ethics review board of record, and cites no regulatory determination for the dataset itself. The webinar curriculum references IRB protocol drafting and HIPAA/GDPR compliance as training topics, not as dataset approvals.

### 4.26 `ethical_reviews.reviewing_organization` — corrected

**Finding:** The Ethics pillar presented as a reviewing organization. The bundle describes it as a project pillar conducting community focus groups and legal/regulatory analysis — not review of this dataset.

**Change:** `reviewing_organization` removed. The object is retained with `review_details` describing the pillar's actual described activity:

> The NIH RePORTER abstract describes Ethics (Ethical and Trustworthy AI) as one of three project pillars, and states the project will perform community-facing ethics focus groups to determine what data is appropriate for public sharing, and analyze the existing legal and regulatory landscape. chorus4ai.org states the consortium evaluates community perspectives on clinical care AI to increase trustworthiness of provenance and privacy. The bundle does not describe an ethics review of this dataset, name a reviewing body, or cite an approval.

### 4.27 `collection_timeframes` — retained, scope clarified

**Finding:** Typed `start_date` / `end_date` empty while prose carried 2022-09-01 and 2026-11-30 — the funded project period, not the collection period. Object risked being a restatement of funding metadata.

**Change:** Object retained; typed date slots deliberately left empty; `timeframe_details` rewritten to make the distinction explicit and to carry the one genuine collection-period signal in the bundle:

> The bundle states no data collection start or end date. The NIH RePORTER record gives the funded project period as 2022-09-01 to 2026-11-30, which is the award period and not a collection timeframe. Collection is described as retrospective. The only dated collection status is the webinar's statement that as of August 2025 the dataset covered 14 hospitals with over 45,000 unique admissions, with EEG extraction and imaging de-identification still in process.

**Rationale:** Populating `start_date` with an award date would be a wrong-range-in-spirit error. The object earns its place by recording the retrospective character and the one dated status point.

### 4.28 `distribution_dates` — removed

**Finding:** `release_dates` contained narrative rather than dates; its own `source_caveats` conceded no formal release dates exist.

**Change:** Object removed. The "Current Released Dataset" vs "Anticipated Final Dataset" distinction is carried in `description` and in the admission-instance notes, where it belongs.

### 4.29 `subpopulations` / instance notes — 23 Tb figure de-narrowed

**Finding:** "The released waveform data total 23 terabytes" attached to the telemetry-waveform instance, narrowing an undifferentiated source figure.

**Change:** The figure is removed from the telemetry instance and placed once at dataset level in `notes`, undifferentiated as the source gives it:

> chorus4ai.org reports 23 Tb of waveform data in the current released dataset. The bundle does not break this figure down between telemetry and EEG waveforms, and the unit is printed as "Tb" without disambiguation between terabits and terabytes.

### 4.30 `total_size_bytes` — remains omitted, caveat corrected

**Finding:** Omitted correctly, but `source_caveats` claimed absence of any size figure without noting the partial one.

**Change:** `total_size_bytes` remains unpopulated. `source_caveats` amended:

> No total dataset size in bytes is given. The only size figure in the bundle is 23 Tb of waveform data, which covers one modality group and uses an ambiguous unit abbreviation; it is recorded in notes rather than in total_size_bytes.

---

## 5. Changes made — low severity

- **`keywords`** — `equitable AI` removed (project branding from the title, not content); `intensive care unit` removed as a duplicate of `critical care`. Retained: critical care, acute illness, electronic health record, OMOP, waveform, EEG, medical imaging, social determinants of health, multimodal, machine learning.
- **`other_tasks`** — the "analyses of context and equity beyond bedside prediction" extrapolation removed. The slot now carries only what the abstract states: labeling data with targets important for prediction, and external validation of AI-developed models via the holdout set. Where nothing further is evidenced the slot is left short rather than padded.
- **`is_deidentified.identifiers_removed`** — remains omitted (confirmed correct; the bundle names no identifier categories). `method` retained: tokenization of unstructured EHR data, clinical notes stored locally except tokens, imaging de-identification in process, transformation approaches that limit re-identification, plus the `privacy_scan_tool` and `CTP-deid` repositories.
- **`notes`** — website compliance banner moved to `status` (4.13). NIH disclaimer retained in `notes` as genuine residual, attributed: *"chorus4ai.org states the project is funded by NIH under award number OT2OD032701 and that website content is solely the responsibility of the authors and does not necessarily represent official NIH views."*
- **`data_governance.notes` / `maintainers.maintainer_details`** — the `cmccrary@mgh.havard.edu` "(as printed)" annotation was appearing in three places. The address is now transcribed once in `maintainers` without inline annotation; the fidelity note appears once, in top-level `source_caveats`: *"The program manager email on chorus4ai.org is printed as cmccrary@mgh.havard.edu; 'havard' appears to be a typographical error for 'harvard' but is transcribed as printed."*
- **`license`** — remains omitted. Confirmed correct: the MIT License in the bundle governs GitHub software repositories (and not uniformly — Chorus_SOP is Apache-2.0). `ip_restrictions` and `source_caveats` both state this. `source_caveats` amended to name the Apache-2.0 exception.

---

## 6. Left as-is, with rationale

| Item | Finding | Why retained |
|---|---|---|
| `id` = project website URL | low — id, page identical; no dataset-specific identifier | The bundle contains no DOI, accession, or dataset-specific IRI. A minted opaque identifier would be less traceable. `page` retained separately because it is independently true. `source_caveats` states that no persistent dataset identifier exists in the bundle. `publisher` was removed (4.12), so the three-way collision is now two-way and both uses are defensible. |
| `description` carrying three scale figures | medium — reads as cumulative fact | Rewritten rather than removed. The description now labels each figure with its source panel and date and states that the bundle does not reconcile them, so the conflict is visible in the first slot a reader encounters rather than only in `source_caveats`. Removing the figures would lose the dataset's only scale evidence. |
| `updates` with `frequency` empty | low — update_details describes site status reporting, not a dataset update plan | Retained. The site-status-reporting machinery (Google Form → GoogleScript → GitHub API → Standards / Data Acquisition project boards) is the only update-cadence evidence in the bundle, and the "phased release" character (imaging de-id in process, EEG extraction in process, metadata planned for three modalities) is genuine forward-looking dataset information. `update_details` now states explicitly that the described process is site submission tracking and that no dataset versioning or release cadence is given. `frequency` correctly stays empty. |
| `data_collectors` as a slot | — | Retained; the 14 Data Acquisition centers are unambiguously data collectors. |
| `conforms_to_standard: OTHER` retained once | medium (partially addressed) | The enum provides no per-standard `OTHER` mechanism. Dropping it would under-report three real standards; emitting it three times would be meaningless. Retained once with `source_caveats` naming all three (4.11). |

---

## 7. Full/core alignment

After reconciliation the two records are structurally consistent. Slots present in full but absent from core are absent **only** where the core schema does not define them; no slot differs by generation choice.

Divergences resolved: `anomalies` (removed from full, was already absent from core), `splits` (now in both), `direct_collection` (now in both), `known_biases` → `known_limitations` (applied to both), `variables` (added to both), `data_governance.committee_contact` (removed from both), `at_risk_populations` (removed from both), `extension_mechanism` (removed from both), `cleaning_strategies` (removed from both), `distribution_dates` (removed from both), `publisher` (removed from both).

Where the core schema admits a slot at lower cardinality or without a sub-slot, the core record carries the same evidence in the nearest available structure and its `source_caveats` records the compression.

---

## 8. Result

| | Full | Core |
|---|---|---|
| Populated top-level slots before | 61 | 44 |
| Populated top-level slots after | **58** | **43** |
| Slots removed | 8 | 7 |
| Slots added | 2 (`variables`, `splits` already present) | 3 (`variables`, `splits`, `direct_collection`) |
| Slots substantively rewritten | 17 | 15 |
| Validates | **yes** | **yes** |

**Validation:**
```
poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_all.yaml \
  -C Dataset data/d4d_concatenated/claudecode_agent/2026-08-13_claude-opus-5-api-generic_rep1/CHORUS_d4d.yaml
→ No issues found

poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml \
  -C CoreDataset data/d4d_concatenated/claudecode_agent_core/2026-08-13_claude-opus-5-api-generic_rep1/CHORUS_d4d_core.yaml
→ No issues found
```

**Provenance record:** written via `d4d provenance record --project CHORUS --method claudecode_agent --label 2026-08-13_claude-opus-5-api-generic_rep1 --input-bundle data/preprocessed/concatenated/CHORUS_preprocessed.txt`

**Prior D4D reuse:** none. No file under `data/d4d_concatenated/` or `data/ro-crate_packages/` was read at any phase. All factual content derives from the declared bundle.

---

## 9. Net effect

Slot count fell slightly. That is the intended direction here: six typed assertions that outran their evidence were removed, two unsupported absence claims were withdrawn, and four objects describing the *project* or the *training program* were either re-scoped to the dataset or deleted under the referent rule. Against those losses, `variables` now carries the nine-row webinar table that was the single richest field-level source in the bundle and had been left entirely unrepresented, and `data_use_permission` is now queryable.

The substantive improvement is not in count but in the relocation of three-way conflicts out of prose and into visible structure: the 50,000 / 45,000 / 100,000 admission figures, the two access-request routes, and the six data standards behind a single `OTHER` term are each now stated with their sources attached rather than silently resolved in a slot that admits one value.