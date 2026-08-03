# CHoRUS — D4D Reconciliation Report

**Version label:** `2026-08-02_claude-opus-5-bare_rep2`
**Arm:** BASELINE (input documents only)
**Declared bundle:** `data/preprocessed/concatenated/CHORUS_preprocessed.txt` (4 files: NIH RePORTER project page, AIM-AHEAD Cohort 2 webinar deck, chorus4ai.org project site, chorus-ai GitHub organization overview)
**Records reconciled:**

- Full — `data/d4d_concatenated/claudecode_agent/2026-08-02_claude-opus-5-bare_rep2/CHORUS_d4d.yaml`
- Core — `data/d4d_concatenated/claudecode_agent_core/2026-08-02_claude-opus-5-bare_rep2/CHORUS_d4d_core.yaml`

---

## 1. Referent decision

`Dataset` admits one referent. The declared bundle describes at least three candidate objects: the CHoRUS **clinical dataset** (the multi-modal, controlled-access critical-care corpus), the **chorus-ai GitHub organization** (28 repositories of tooling, SOPs and mappings), and the **AIM-AHEAD Bridge2AI for Clinical Care training program** (a workforce activity that consumes the dataset).

Both records take the **CHoRUS clinical dataset** as the referent. The GitHub organization is represented only where it documents how the dataset was produced, standardised or accessed; the training program is represented only as an existing use and an access route. This choice is held identically across the pair and drove several of the Phase 4 removals below.

---

## 2. What the audit found

The audit returned **17 findings**: 0 high, 4 medium, 13 low. No fabricated entities were detected and no facts from outside the declared bundle were found. Every named person, institution, award number, modality count, file format, repository name and contact address in both records traces to the bundle.

Findings clustered into three kinds:

| Kind | Count | Description |
|---|---|---|
| Pair-structural | 2 | Same content filed under different slots in the two records; core-record omissions without stated justification |
| Slot-fit | 6 | Supported facts filed against fields they do not answer, including one duplication across two slots |
| Over-reach | 9 | Claims running slightly ahead of the evidence, or fields answered with adjacent material |

The audit also recorded correct restraint that Phase 4 preserved: `license`, `doi`, `version`, `citation`, `total_size_bytes`, `collection_consents`, `anomalies` and `errata` remain unpopulated because the bundle does not support them. In particular the MIT license stated in the GitHub README is scoped to the software repositories, not to the clinical dataset, and was **not** promoted to the dataset-level `license` slot in either record.

---

## 3. Changes applied to the **full** record

### 3.1 Over-reach corrected

| Slot | Change | Reason |
|---|---|---|
| `collection_timeframes` | **Removed.** The NIH award period (2022-09-01 → 2026-11-30) relocated to `funders` as the award period of OT2OD032701. | Award period is not a collection timeframe. Collection is described as retrospective and the bundle never states the timeframe of the underlying clinical records. A timeframe object carrying no supported timeframe answers nothing, so the slot is omitted rather than filled. |
| `preprocessing_strategies` | Entry asserting geocoding of OMOP Location entities via DeGauss **removed**; the `UF-Geocoding` repository relocated to `external_resources`. | The bundle establishes only that the repository exists in the chorus-ai organization, and that it is a fork of `bihorac-LAB/Exposome` with no CHoRUS-specific application statement. Existence of a repository does not establish that the transformation was applied to the released data. |
| `is_deidentified` | Assertion that the `CTP-deid` repository was applied **removed**. Retained: imaging de-identification "in process" for the larger cohort, clinical notes extracted and tokenized via the OHNLP toolkit, notes stored locally except tokens, and the NIH abstract's statement that data are transformed "using approaches that limit re-identification". | `CTP-deid` appears in the bundle as a repository name with no description. The retained statements are all directly attested. |
| `labeling_strategies` | **Removed.** The visualization-and-annotation-environment aim retained under `purposes`. | The only supporting text is future-tense NIH abstract language ("A visualization and annotation environment **will** label data with targets important for prediction"). No annotation procedure, annotator qualification or quality control appears anywhere in the bundle. Rendering a stated intention as an applied methodology overstates the evidence. |
| `at_risk_populations` | **Removed.** | The bundle states the released cohort includes PICU and NICU admissions. "Therefore includes minors" is deduction from unit names, and no safeguard or assent procedure specific to at-risk populations is documented. |
| `human_subject_research` | **Removed.** Cohort composition retained in `instances` and `subpopulations`. | The field asks for IRB approval, ethics review determination and regulatory compliance status. The bundle contains no IRB or ethics-committee determination for CHoRUS. The slot was answered with adjacent governance framing; omission is the correct answer. |
| `is_tabular` | **Removed.** | The dataset mixes 1.6 billion rows of tabular OMOP data with DICOM imaging and WFDB / EDF+ / Persyst waveforms. The boolean forces a single answer the bundle does not supply for the dataset as a whole. |
| `created_by` | Softened to name Massachusetts General Hospital strictly as the awardee organization of record for OT2OD032701, with Eric S. Rosenthal as principal investigator. | The prior value said MGH "leads" the consortium. RePORTER establishes the awardee organization and PI; it does not establish consortium leadership. |
| `status` | Value now reproduces the site notice verbatim, including the source's "repoitory" spelling, marked `[sic]`. | The value is presented as a direct quotation and was silently normalised. |

### 3.2 Slot-fit corrected

| Slot | Change | Reason |
|---|---|---|
| `machine_annotation_tools` | Reduced to the **OHNLP toolkit** alone. The privacy scan tool remains under `is_deidentified`; DeGauss geocoding removed with §3.1. | A privacy screening utility is not an automated annotation tool, and it was already represented elsewhere. Only OHNLP (extraction and tokenization of clinical notes) answers this field. |
| `collection_mechanisms` | `chorus-container-apps` entry **removed** and relocated to `external_resources`. | Dockerized container applications deployed to support CHoRUS services on Azure are hosting and service infrastructure, not an instrument used to collect data. |
| `acquisition_methods` | Federated-access / balanced-cohort sampling entry **removed**; retained solely in `sampling_strategies`. | The statement is a sampling and access description, not an acquisition method, and it was duplicated in substance across both slots. Populating two slots with one fact answers neither distinctly. |
| `cleaning_strategies` | Site status-tracking entry **removed**; retained in `extension_mechanism` and `updates`. | Project management of extract delivery is not a data cleaning or quality-control procedure applied to the data. The `CHoRUSReports` characterization-report entry is retained here because it is described as returning characterization reports to sites following data submissions. |
| `distribution_dates` | AIM-AHEAD training-program period (2025-11-17 → 2026-07-31) **removed**. | These are program start and end dates, not dataset release dates. The access-provision fact is already carried by `existing_uses` and by `license_and_use_terms` (registration form, signed licensing agreement, `.edu` email requirement, provisioned compute). |

### 3.3 Left in place after review

- **The two conflicting admission counts are preserved side by side.** The webinar states "As of August 2025, covers 14 different hospitals with over 45K unique admissions"; the project website states a Current Released Dataset of 50,000 patient admissions from ICU, PICU and NICU, alongside an Anticipated Final Dataset of 100,000, and the NIH abstract speaks of "more than 100,000 critically ill patients". Both attested figures, and the anticipated/current distinction, are stated as such. No figure was selected over another and none were merged.
- **`creators` retained as six separate `Creator` objects** — Rosenthal (Massachusetts General Hospital), Bihorac (University of Florida), Jiang (UTHealth Houston), Strekalova (University of Florida), Rashidi (University of Florida), Kwong (Tufts University) — one object per person, affiliations verbatim. Descriptions now state plainly that these individuals are listed in the bundle as the Bridge2AI CHoRUS Leadership Team, and that Rosenthal is separately identified as NIH principal investigator. No `credit_roles` are asserted, because the bundle maps no individual to any contribution.
- **Synthesised subset identifiers retained.** `DataSubset` requires `id`, and the bundle mints no identifiers for the nine modalities. The nine `id` values are locally minted and are documented here as such: they are not source-attested resolvable addresses.
- **Nine modalities retained as nine distinct objects**, one per row of the webinar's data-type table (demographics; medication administration; procedures; nursing flowsheets; diagnoses; clinical notes; imaging; waveform telemetry; waveform EEG), each carrying its own data standard (OMOP, OHNLP, DICOM, WFDB, EDF+/Persyst), access control (controlled, all nine) and metadata status (Yes / Planned). This matches the bundle's own "9 different data modalities" count.

---

## 4. Changes applied to the **core** record

### 4.1 The `subsets` / `resources` divergence — resolved and documented

The audit flagged that the nine modality entries appear under `subsets` (range `DataSubset`) in the full record and under `resources` (range `Dataset`) in the core record.

Inspection of `src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml` confirms that **`CoreDataset` does not declare `subsets`**. `resources` (range `Dataset`) is the nearest available container in the core schema. The divergence is therefore schema-forced, not an arbitrary inconsistency — but it was previously silent. Two corrections were made:

1. The nine core `resources` entries were re-aligned so that their names, data standards, access controls and metadata statuses match the nine full-record `subsets` entries field for field, with identical identifiers.
2. The divergence is recorded here rather than left for a reader to discover.

### 4.2 Core-record omissions — resolved

The audit flagged four full-record slots absent from the core: `splits`, `participant_privacy`, `third_party_sharing`, `direct_collection`. Inspection confirms **none of the four is declared on `CoreDataset`**. The omissions are therefore schema-forced. Where the underlying fact is supported and a core slot answers it, the fact was relocated rather than dropped:

| Full-record slot | Fact | Disposition in core |
|---|---|---|
| `splits` | A holdout test set is provisioned, accessible for external model validation to aid marketplace adoption. | Already carried by `purposes`, `tasks` and `intended_uses`; confirmed present and left there. |
| `participant_privacy` | Data held in a controlled-access cloud enclave; all nine modalities controlled access; clinical notes stored locally except tokens. | **Relocated** into `confidential_elements` and `license_and_use_terms` in the core record. Previously dropped outright. |
| `third_party_sharing` | Holdout set made available externally for model validation; dataset access extended to AIM-AHEAD trainees under a signed licensing agreement. | **Relocated** into `license_and_use_terms` and `existing_uses`. Previously dropped outright. |
| `direct_collection` | Data are retrospective clinical records acquired from 14 contributing hospital sites, not collected directly from individuals for this purpose. | **Relocated** into `acquisition_methods`. Previously dropped outright. |

### 4.3 Corrections mirrored from the full record

All §3.1 and §3.2 corrections were applied identically to the core record for every slot the core schema declares. Specifically: `collection_timeframes`, `at_risk_populations`, `human_subject_research`, `is_tabular` and `labeling_strategies` are now absent from both records; the DeGauss and CTP-deid application claims are gone from both; `machine_annotation_tools` carries the OHNLP toolkit alone in both; `created_by` and `status` carry identical corrected text in both.

---

## 5. What was deliberately left unpopulated

Recorded so that absence is legible as a decision rather than an oversight:

- `license`, `license` at dataset level — the MIT license is attested for the GitHub code only.
- `doi`, `version`, `citation`, `issued` — no dataset DOI, version string, recommended citation or formal issuance date appears in the bundle.
- `total_size_bytes`, `total_file_count` — "23 Tb waveform data" is a modality-level figure stated in the source's own units, not an audited byte total across all collections; it is retained as descriptive text on the waveform telemetry entry rather than converted into an integer byte count.
- `collection_consents`, `informed_consent`, `consent_revocations`, `collection_notifications` — the bundle describes community-facing ethics focus groups to determine what data is appropriate for public sharing, which is recorded under `ethical_reviews`, but states nothing about participant consent, notification or revocation.
- `ethical_reviews` retains only the attested focus-group and legal/regulatory-analysis activity; no IRB determination is asserted.
- `anomalies`, `errata`, `known_biases` as findings — the bundle states that ethical and legal work will "manage privacy and bias" and that curriculum content addresses "EHR data limitations", both of which are recorded as aims under `purposes` and `existing_uses`. No specific bias or anomaly in the delivered data is documented, so no `DatasetBias` or `DataAnomaly` object was invented.
- `download_url` — no direct data URL exists; access runs through registration, a signed licensing agreement, and the contacts `dbold@emory.edu` / `jared.houghtaling@tuftsmedicine.org`, all of which sit in `license_and_use_terms` and `maintainers`.

---

## 6. Outcome

| | Full | Core |
|---|---|---|
| Populated slots after reconciliation | **49** | **28** |
| Slots removed in Phase 4 | 9 | 9 |
| Slots relocated in Phase 4 | 4 | 3 |
| Validates | **yes** | **yes** |

Validation commands run:

```
poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_all.yaml -C Dataset \
  data/d4d_concatenated/claudecode_agent/2026-08-02_claude-opus-5-bare_rep2/CHORUS_d4d.yaml

poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml -C CoreDataset \
  data/d4d_concatenated/claudecode_agent_core/2026-08-02_claude-opus-5-bare_rep2/CHORUS_d4d_core.yaml
```

Both pass. Provenance recorded via `d4d provenance record` for project CHORUS, method `claudecode_agent`, label `2026-08-02_claude-opus-5-bare_rep2`.

**Reconciliation outcome: resolved.** No high-severity findings. All 4 medium findings are closed — two by relocating facts into slots the core schema declares and documenting the two schema-forced divergences, two by removing claims that exceeded the evidence. All 13 low findings are closed by removal, relocation or explicit retention-with-reason. No prior D4D record of any arm, label or date was consulted at any phase; the declared bundle and the two schema files were the sole inputs.