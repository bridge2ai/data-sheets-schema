# CHoRUS — Phase 4 Reconciliation Report

**Project:** CHORUS
**Version label:** `2026-07-31_claude-opus-5-api-generic_rep2`
**Arm:** DE NOVO WITH CRATE (documents + RO-Crate evidence)
**Declared input bundle:** `data/preprocessed/concatenated/CHORUS_preprocessed_with_crate.txt`
**Records reconciled:**
- Full — `data/d4d_concatenated/claudecode_agent_crate/2026-07-31_claude-opus-5-api-generic_rep2/CHORUS_d4d.yaml`
- Core — `data/d4d_concatenated/claudecode_agent_crate_core/2026-07-31_claude-opus-5-api-generic_rep2/CHORUS_d4d_core.yaml`

---

## 1. Referent decision

`Dataset` admits a single referent. Both records are held to:

> **The Bridge2AI CHoRUS for Clinical Care AI Dataset — A Multi-Center, Multi-Modal, High-Resolution Critical Care Dataset, version 1.0 Beta**, identified by DOI `10.18130/V3/XNBOPG`, packaged as the CHoRUS RO-Crate Package (`ark:59853/rocrate-chorus-ro-crate-package/`).

This referent is chosen because the crate JSON-LD is the only artifact in the bundle that names, versions, cites and identifies a dataset as such. The NIH RePORTER record describes the *award* (OT2OD032701), the chorus4ai.org page describes both an anticipated final dataset and a current released dataset, the webinar describes a training-access snapshot as of August 2025, and the GitHub overview describes the *organization and its software*. These are treated as evidence *about* the referent, not as alternative referents. Award, network, software organization and training program are represented only through slots that admit them (`funders`, `creators`, `data_collectors`, `external_resources`, `existing_uses`), never as the dataset itself.

The referent choice was unchanged in Phase 4 and is identical across both records.

---

## 2. What the Phase 3 audit found

Twenty-two findings, none high-severity.

- **No evidence-boundary violation.** Every substantive claim in both records traces to one of the six bundle sources: the NIH RePORTER abstract, the AIM-AHEAD Cohort 2 webinar, chorus4ai.org, the CHoRUS GitHub overview (2025-11-14), the reduced crate JSON-LD, or the AI-readiness self-assessment.
- **No prior-D4D reuse.** No withheld artifact (`CHORUS_crate_d4d.yaml`, `ro-crate-linkml.yaml`, `ro-crate-datasheet.html`) or any record under `data/d4d_concatenated/` was consulted at any phase.
- **Source conflicts were represented, not resolved away.** The admissions conflict (45K vs 50K) and the three-way imaging conflict (1000 images / 7,642 radiology admissions / no DICOM in package) both appear with per-source attribution in both records.
- **Three findings were medium-severity and structural:** two generator-computed quantitative aggregates in the full record; an unverifiable slot in the core record; and a cross-record inconsistency in how the two RO-Crate sub-crates are modelled.
- The remaining nineteen findings were low-severity inferences, slot-fit questions, empty-list absence assertions, and meta-commentary embedded in factual slots.

---

## 3. Changes to the full record

### 3.1 Removed — unsupported quantitative aggregates

| Slot | Prior value | Action |
|---|---|---|
| `total_file_count` | `1477` | **Removed** |
| `total_size_bytes` | `1201585609503` | **Removed** |

`1477` was the denominator of the AI-readiness checksum statement (`99% of files have checksums (1469/1477)`), which counts checksum-bearing entities in the crate graph — a graph whose file inventories the bundle explicitly states are *collapsed*. It is also inconsistent with the adjacent `1468 dataset(s) documented`. `1201585609503` was arithmetic performed by the generator on two unit-suffixed strings (`1.201567472832 tb`, `18.136671 mb`) under an assumed decimal-unit interpretation the bundle never states. Both are inferences dressed as measurements. The evidence-bearing forms — `contentSize: "1.2 tb"` for the package and the two sub-crate `contentSize` strings — are retained verbatim on the corresponding `file_collections` entries and in `distribution_formats`.

### 3.2 Removed — empty lists asserting absence

| Slot | Prior value | Action |
|---|---|---|
| `content_warnings` | `[]` | **Removed** |
| `collection_consents` | `[]` | **Removed** |

An empty list is a positive claim that the category is empty. The bundle makes no statement about content warnings at all, and on consent it says only "IRB approval or waiver as appropriate" alongside a HIPAA exemption-4 determination — which does not establish that no consent was obtained at any of the fourteen contributing sites. Omission is the correct representation of absent evidence.

### 3.3 Reslotted — access URL

`download_url: http://chorus4ai.org/dataset` was **removed** and the URL retained under `page`. The slot definition requires a URL pointing "directly to the data itself"; `rai:conditionsOfAccess` states that access requires governance-committee proposal review, an executed DUA, and confinement to a secure enclave with "no raw data export permitted unless explicitly approved." The crate `contentUrl` is a landing page for a controlled-access request pathway, not a retrieval endpoint. The same URL continues to appear in `distribution_formats` and `license_and_use_terms` access text.

### 3.4 Removed — inferred format characterization

`is_tabular: false` was **removed**. The bundle describes a multimodal dataset containing substantial tabular content (1.6 billion rows of OMOP EHR data; `text/tab-separated-values` among declared formats) alongside WFDB waveforms, DICOM imaging and EDF+/Persyst EEG. It never characterizes the dataset as tabular or non-tabular, and a boolean here forces a claim the evidence does not make.

### 3.5 Removed — packaging conformance attributed to the dataset

`conforms_to: https://w3id.org/ro/crate/1.2` was **removed**. That value is the `conformsTo` of the `ro-crate-metadata.json` packaging descriptor, not of the dataset. Dataset-level standards remain correctly captured in `conforms_to_schema` (OMOP CDM, OHNLP, DICOM, WFDB, EDF+/Persyst, PhysioNet extended, Croissant RAI) as stated in the webinar modality table and the AI-readiness interoperability entry.

### 3.6 Unmerged — creator and publisher

`created_by` was changed from `"The CHoRUS for Clinical Care AI Network (published by B2AI CHoRUS)"` to `"The CHoRUS for Clinical Care AI Network"`. The two facts are distinct crate assertions (citation corporate author vs. `publisher`) and the decision rules forbid merging distinct entities into one claim. `publisher` remains **unpopulated**: its range is `uriorcurie` and the bundle supplies only the literal string `B2AI CHoRUS`, which is not resolvable to a URI or CURIE from the bundle. The publisher fact is carried in `distribution_formats` prose, where a string range admits it.

### 3.7 Corrected — sub-team attribution

`data_collectors` previously read "organized into Standards, Data Acquisition, and Tooling sub-teams under the Data pillar." The GitHub overview places those sub-teams "within the CHoRUS DGP"; the three-pillar framing (Data / Ethics / People) is a separate statement from the NIH abstract. The phrase now reads "sub-teams within the CHoRUS Data Generation Project," removing the generator-supplied join between the two sources.

### 3.8 Corrected — subpopulation qualifier

`subpopulations`: "Adult intensive care unit (ICU) admissions" → "Intensive care unit (ICU) admissions." The website states "50,000 Patient admissions from ICU, PICU, and NICU." The qualifier "Adult" was inferred by contrast with PICU/NICU and is not stated.

### 3.9 Corrected — at-risk population attribution

`at_risk_populations` previously cited Seattle Children's Hospital and Nationwide Children's Hospital / OSU as evidence of pediatric data contribution. The bundle lists these only as *author affiliations* (footnotes 12 and 13 of the crate author string) and nowhere identifies which institutions are among the fourteen Data Acquisition centers. The institutional attribution was **removed**. The substantive claim — that pediatric and neonatal patients are within scope — is retained on its own footing, sourced to the website's "ICU, PICU, and NICU" statement.

### 3.10 Reslotted — de-identification and preprocessing tooling

`machine_annotation_tools` previously listed DeGauss, IbisWorks EICON, RSNA Clinical Trial Processor, `privacy_scan_tool`, and the OHNLP toolkit. Only the OHNLP toolkit is described in the bundle in annotation-adjacent terms ("extracted and tokenized using OHNLP toolkit"). The others were moved:

- RSNA Clinical Trial Processor (imaging metadata de-identification) and IbisWorks EICON (pixel-level de-identification) → `is_deidentified` and `preprocessing_strategies`, matching `rai:dataCollection`.
- DeGauss (geocoding of OMOP Location entities, per the UF-Geocoding repository) → `preprocessing_strategies`.
- `privacy_scan_tool` → `sensitive_elements` handling narrative.

`machine_annotation_tools` now contains the OHNLP toolkit only.

### 3.11 Removed — meta-commentary about the evidence base

Three slots carried statements about the bundle rather than about the dataset:

- `informed_consent`: "The available sources do not describe…"
- `at_risk_populations`: "No population-specific assent procedures are described in the available sources"
- `collection_timeframes`: "Specific clinical encounter date ranges are not stated in the available sources"

All three sentences were **removed**. Where removal emptied the slot's justification, the slot itself was dropped (`informed_consent`); where evidence-bearing content remained, the slot was kept with only that content (`at_risk_populations`, `collection_timeframes` — the latter retaining the crate's `datePublished`/`releaseDate` and the webinar's "as of August 2025" observation point).

### 3.12 Deduplicated — biases, limitations, anomalies

`rai:dataBiases` and `rai:potentialBiases` are byte-identical in the crate, and `rai:dataLimitations` overlaps both. The prior records reproduced the overlap across three slots, so "variable sampling rates," "MNAR missingness," "institutional heterogeneity," and "documentation quality" each appeared two or three times. Reconciled as:

- `known_biases` — the six bias statements, recorded once, with a note that the crate asserts them under two identical properties and that bias assessment is described as ongoing.
- `known_limitations` — the seven limitation statements, with the two that also appear as biases cross-referenced rather than restated.
- `anomalies` — narrowed to the single statement the bundle frames as a data-quality/missing-data finding: variable sampling rates across hospital waveform systems and middleware (`rai:dataCollectionMissingData`, echoed in the AI-readiness `data_quality` entry).

### 3.13 Sharpened — imaging conflict

The imaging entries in `subsets` and `known_limitations` previously juxtaposed three figures without stating their incompatibility. They now carry an explicit statement that the three cannot describe the same artifact, each with its source and date:

- "currently 1000 images available with de-id in process for larger cohort" — Cohort 2 webinar, August 2025 status
- "7,642 Admissions with Radiology Data" — chorus4ai.org, Current Released Dataset
- "No DICOM images are included" — crate `completeness`, v1.0 Beta package

No figure was selected as authoritative.

---

## 4. Changes to the core record

### 4.1 Removed — unverifiable slot

`distributions` was **removed**. It does not appear in the declared `Dataset` slot inventory, and no supplied artifact establishes that `CoreDataset` defines it; its range and required keys are therefore unverified. Its three entries (crate package, EHR sub-crate, waveforms sub-crate) were themselves evidence-backed, so the content was preserved by folding the package-level access and format facts into `distribution_formats` and the two sub-crates into `resources` (§4.3).

### 4.2 Added — citation

`citation` was **added**, carrying the crate string verbatim:

> The CHoRUS for Clinical Care AI Network. The Bridge2AI CHoRUS for Clinical Care AI Dataset: A Multi-Center, Multi-Modal, High-Resolution Critical Care Dataset, version 1.0 Beta. Harvard Dataverse, Apr. 2026.

This was a clearly supported omission: the fact is explicit in the bundle and already present in the full record. Its absence from the core record had no justification.

### 4.3 Resolved — duplicate and divergent sub-crate modelling

The two RO-Crate sub-crates (`08cf7419-…` EHR, `b9b41c72-…` Waveforms) were previously modelled in the core record under *both* `resources` and `distributions`, and in the full record under `file_collections` — three structural roles for two entities across a paired set.

Reconciled as:

- **Core:** the two sub-crates appear once, under `resources` (range `Dataset`, `id` required).
- **Full:** the two sub-crates appear once, under `file_collections` (range `FileCollection`, `id` required), which is the slot the full schema designates for logical file groupings and which carries the per-sub-crate `contentSize` and format facts.

The slots differ because the full schema explicitly directs file groupings to `file_collections` ("For file collections, use the file_collections attribute instead" — `resources` description), while `file_collections` availability in `CoreDataset` is not verifiable from the supplied material. The *referent mapping is identical in both records* — same two UUIDs, same names, same `isPartOf` relationship to the package — and this divergence is recorded here rather than left implicit.

### 4.4 Applied — the full-record corrections that also apply to core

The following Phase 4 changes were applied identically to the core record, for the reasons given in §3: removal of `is_tabular`; `download_url` → `page`; removal of `conforms_to` (RO-Crate profile); subpopulation "Adult" qualifier dropped; children's-hospital attribution dropped from `at_risk_populations`; `machine_annotation_tools` narrowed to the OHNLP toolkit; meta-commentary sentences removed; imaging conflict made explicit.

### 4.5 Added — date ambiguity note

The core record previously presented `issued: 2026-04-03` as a single resolved date with no trace of the conflict. The crate carries `datePublished: "2026-04-03"` on the package, `releaseDate: "03/04/2026"` on the package, and `datePublished: "03/04/2026"` on the EHR sub-crate — the latter two in an ambiguous DD/MM vs MM/DD form. The full record noted this in `distribution_dates`; the same note was **added** to the core record so both surface the ambiguity. The ISO-8601 value is used as the slot value because it is the only unambiguous form in the bundle.

---

## 5. Left as-is, with reasons

**The 45K vs 50K admissions conflict.** The webinar states "As of August 2025, covers 14 different hospitals with over 45K unique admissions"; chorus4ai.org states "50,000 Patient admissions" for the Current Released Dataset and "100,000 Patient admissions" for the Anticipated Final Dataset. All three figures are retained in both records with source and date attribution. They are not merged, averaged, or ranked. The NIH abstract's "more than 100,000 critically ill patients" is retained separately as an award-level target, not as a dataset property.

**Duplicated crate bias properties.** `rai:dataBiases` and `rai:potentialBiases` are identical; `rai:dataReleaseMaintenancePlan` and `rai:maintenancePlan` are likewise identical. Recording each set of statements once, with a note of the duplication, represents the evidence without amplifying a redundancy that is an artifact of the crate's construction.

**Generator-constructed sub-crate IDs.** `urn:uuid:08cf7419-…` and `urn:uuid:b9b41c72-…` are retained. The crate carries these as bare UUID `@id` values; the `uriorcurie` range requires a scheme. The transformation is lossless and mechanically reversible, and the alternative — omitting the sub-crates — would discard evidence. Noted here as generator-constructed rather than bundle-present.

**`publisher` left unpopulated.** See §3.6. Deliberate, not an oversight.

**MIT license (code) kept separate from the Data Use Agreement (data).** The GitHub organization README states "This project is licensed under the MIT License," and individual repositories show MIT and Apache-2.0. The crate states `license: "Data Use Agreement available at 'https://chorus4ai.org/dataset/'"`. These govern different artifacts. `license` and `license_and_use_terms` describe the data terms; the MIT/Apache software licensing appears only in `external_resources` describing the GitHub organization. Not merged.

**Institutional counts.** "14 data contributing hospitals," "20 different institutions," "60+ CHoRUS consortium members," and "20 academic centers, of which 14 will contribute as Data Acquisition centers" are retained as stated. The website and GitHub figures are consistent; no reconciliation was needed.

**Full author list retained in `creators`.** All 39 named investigators with their affiliation footnotes, as given identically in all three crate entities. Long, but verbatim and unambiguous.

**The chorus4ai.org banner** ("This repository is under review for potential modification in compliance with Administration directives") is retained in `status`, as it is an explicit statement about the resource's current standing.

**Enclave / NIST 800-53 / RBAC / audit-logging / no-export controls** retained in full across `confidential_elements`, `sensitive_elements`, `is_deidentified`, and `license_and_use_terms`. Some restatement across these four slots is unavoidable given their overlapping definitions and is not treated as a defect.

---

## 6. Final state

| | Full | Core |
|---|---|---|
| Populated slots before Phase 4 | 61 | 34 |
| Slots removed | 6 | 3 |
| Slots added | 0 | 1 |
| Slots reslotted / value-corrected | 9 | 7 |
| **Populated slots after Phase 4** | **55** | **32** |

**Removed from full:** `total_file_count`, `total_size_bytes`, `content_warnings`, `collection_consents`, `is_tabular`, `conforms_to` (plus `download_url` reslotted to `page`, net-neutral).
**Removed from core:** `distributions`, `is_tabular`, `conforms_to` (plus `download_url` → `page`, net-neutral).
**Added to core:** `citation`.

**Validation:**

- `linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_all.yaml -C Dataset …/CHORUS_d4d.yaml` — **pass**
- `linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml -C CoreDataset …/CHORUS_d4d_core.yaml` — **pass**

**Reconciliation outcome:** reconciled. Referent identical across records; all three medium-severity findings closed; nineteen low-severity findings closed by correction or recorded as deliberate retentions. Both records validate.

**Provenance:** live record written via
`poetry run d4d provenance record --project CHORUS --method claudecode_agent_crate --label 2026-07-31_claude-opus-5-api-generic_rep2 --input-bundle data/preprocessed/concatenated/CHORUS_preprocessed_with_crate.txt`