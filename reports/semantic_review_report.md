# D4D Schema Semantic Review Report

**Generated:** 2026-04-08 18:00:46
**Review Scope:** All D4D schema modules + actual data from 4 Bridge2AI projects

---

## Executive Summary

**Total Issues Found:** 136

- **CRITICAL:** 9 (Blocks functionality)
- **HIGH:** 54 (Wrong semantics)
- **MEDIUM:** 29 (Reduces clarity)
- **LOW:** 1 (Documentation quality)

### Key Findings

1. **slot_uri Conflicts:** 17 conflicts detected
   - Most severe: `dcterms:description` used by 40 different slots (semantic flattening)
   - Critical: Multiple core mappings (dcat:mediaType, dcterms:license, etc.)

2. **Range-Description Mismatches:** 76 issues
   - HIGH priority: 51 (boolean oversimplification, missing multivalued)
   - MEDIUM priority: 24 (primitives vs structured types)

3. **Data Value Analysis:** 142 fields analyzed across 4 Bridge2AI projects
   - Enum candidates: 75 string fields with limited value sets
   - Multivalued fields: 38 fields containing lists in actual data


---

## Critical Issues (Must Fix)

### C-001: slot_uri Conflict - dcat:accessURL

**Severity:** CRITICAL
**Conflict Count:** 3 different slots

**Usages:**
- `access_urls` in D4D_Distribution.yaml
  - Description: "Details of the distribution channel(s) or format(s)...."
- `erratum_url` in D4D_Maintenance.yaml
  - Description: "URL or access point for the erratum...."
- `access_url` in D4D_Preprocessing.yaml
  - Description: "URL or access point for the raw data...."

**Impact:**
- RDF Serialization: critical
- Tool Breakage Risk: high

**Recommended Fix:**
- **KEEP** `access_urls` → `dcat:accessURL` (correct usage)
- **CHANGE** `erratum_url` → `d4d:erratum_url` (avoid conflict)
- **CHANGE** `access_url` → `d4d:access_url` (avoid conflict)

**Rationale:** Multiple semantic concepts mapped to same ontology term creates ambiguity


### C-002: slot_uri Conflict - dcat:landingPage

**Severity:** CRITICAL
**Conflict Count:** 2 different slots

**Usages:**
- `page` in D4D_Base_import.yaml
  - Description: "A landing page or web page providing access to or information about the resource..."
- `contribution_url` in D4D_Maintenance.yaml
  - Description: "URL for contribution guidelines or process...."

**Impact:**
- RDF Serialization: critical
- Tool Breakage Risk: high

**Recommended Fix:**
- **KEEP** `page` → `dcat:landingPage` (correct usage)
- **CHANGE** `contribution_url` → `d4d:contribution_url` (avoid conflict)

**Rationale:** Multiple semantic concepts mapped to same ontology term creates ambiguity


### C-003: slot_uri Conflict - dcterms:accessRights

**Severity:** CRITICAL
**Conflict Count:** 3 different slots

**Usages:**
- `restrictions` in D4D_Composition.yaml
  - Description: "Description of any restrictions or fees associated with external resources.
..."
- `regulatory_restrictions` in D4D_Data_Governance.yaml
  - Description: "Export or regulatory restrictions on the dataset...."
- `is_shared` in D4D_Distribution.yaml
  - Description: "Boolean indicating whether the dataset is distributed to parties external to the..."

**Impact:**
- RDF Serialization: critical
- Tool Breakage Risk: high

**Recommended Fix:**
- **KEEP** `restrictions` → `dcterms:accessRights` (correct usage)
- **CHANGE** `regulatory_restrictions` → `d4d:regulatory_restrictions` (avoid conflict)
- **CHANGE** `is_shared` → `d4d:is_shared` (avoid conflict)

**Rationale:** Multiple semantic concepts mapped to same ontology term creates ambiguity


### C-004: slot_uri Conflict - dcterms:creator

**Severity:** CRITICAL
**Conflict Count:** 2 different slots

**Usages:**
- `created_by` in D4D_Base_import.yaml
  - Description: "The person or organization primarily responsible for creating the resource...."
- `principal_investigator` in D4D_Motivation.yaml
  - Description: "A key individual (Principal Investigator) responsible for or overseeing dataset ..."

**Impact:**
- RDF Serialization: critical
- Tool Breakage Risk: high

**Recommended Fix:**
- **KEEP** `created_by` → `dcterms:creator` (correct usage)
- **CHANGE** `principal_investigator` → `d4d:principal_investigator` (avoid conflict)

**Rationale:** Multiple semantic concepts mapped to same ontology term creates ambiguity


### C-005: slot_uri Conflict - dcterms:description

**Severity:** CRITICAL
**Conflict Count:** 40 different slots

**Usages:**
- `acquisition_details` in D4D_Collection.yaml
  - Description: "Details on how data was acquired for each instance.
..."
- `mechanism_details` in D4D_Collection.yaml
  - Description: "Details on mechanisms or procedures used to collect the data.
..."
- `collector_details` in D4D_Collection.yaml
  - Description: "Details on who collected the data and their compensation.
..."
- `timeframe_details` in D4D_Collection.yaml
  - Description: "Details on the collection timeframe and relationship to data creation dates.
..."
- `collection_details` in D4D_Collection.yaml
  - Description: "Details on direct vs. indirect collection methods and sources.
..."
- `source_description` in D4D_Collection.yaml
  - Description: "Detailed description of where raw data comes from (e.g., sensors, databases, web..."
- `missing` in D4D_Composition.yaml
  - Description: "Description of the missing data fields or elements.
..."
- `why_missing` in D4D_Composition.yaml
  - Description: "Explanation of why each piece of data is missing.
..."
- `relationship_details` in D4D_Composition.yaml
  - Description: "Details on relationships between instances (e.g., graph edges, ratings).
..."
- `split_details` in D4D_Composition.yaml
  - Description: "Details on recommended data splits and their rationale.
..."
- `anomaly_details` in D4D_Composition.yaml
  - Description: "Details on errors, noise sources, or redundancies in the dataset.
..."
- `bias_description` in D4D_Composition.yaml
  - Description: "Detailed description of how this bias manifests in the dataset, including affect..."
- `limitation_description` in D4D_Composition.yaml
  - Description: "Detailed description of the limitation and its implications.
..."
- `future_guarantees` in D4D_Composition.yaml
  - Description: "Explanation of any commitments that external resources will remain available and..."
- `confidentiality_details` in D4D_Composition.yaml
  - Description: "Details on confidential data elements and handling procedures.
..."
- `warnings` in D4D_Composition.yaml
  - Description: "Specific content warnings describing potentially offensive, insulting, threateni..."
- `identification` in D4D_Composition.yaml
  - Description: "How subpopulations are identified and defined (e.g., by age groups, gender, geog..."
- `distribution` in D4D_Composition.yaml
  - Description: "The distribution of instances across identified subpopulations, including counts..."
- `deidentification_details` in D4D_Composition.yaml
  - Description: "Details on de-identification procedures and residual risks.
..."
- `sensitivity_details` in D4D_Composition.yaml
  - Description: "Details on sensitive data elements present and handling procedures.
..."
- `review_details` in D4D_Ethics.yaml
  - Description: "Details on ethical review processes, outcomes, and supporting documentation.
..."
- `impact_details` in D4D_Ethics.yaml
  - Description: "Details on data protection impact analysis, outcomes, and documentation.
..."
- `notification_details` in D4D_Ethics.yaml
  - Description: "Details on how individuals were notified about data collection.
..."
- `consent_details` in D4D_Ethics.yaml
  - Description: "Details on how consent was requested, provided, and documented.
..."
- `revocation_details` in D4D_Ethics.yaml
  - Description: "Details on consent revocation mechanisms and procedures.
..."
- `maintainer_details` in D4D_Maintenance.yaml
  - Description: "Details on who will support, host, or maintain the dataset.
..."
- `erratum_details` in D4D_Maintenance.yaml
  - Description: "Details on any errata or corrections to the dataset.
..."
- `update_details` in D4D_Maintenance.yaml
  - Description: "Details on update plans, responsible parties, and communication methods.
..."
- `retention_details` in D4D_Maintenance.yaml
  - Description: "Details on data retention limits and enforcement procedures.
..."
- `version_details` in D4D_Maintenance.yaml
  - Description: "Details on version support policies and obsolescence communication.
..."
- `extension_details` in D4D_Maintenance.yaml
  - Description: "Details on extension mechanisms, contribution validation, and communication.
..."
- `response` in D4D_Motivation.yaml
  - Description: "Short explanation describing the primary purpose of creating the dataset...."
- `response` in D4D_Motivation.yaml
  - Description: "Short explanation describing the specific task or tasks for which this dataset w..."
- `response` in D4D_Motivation.yaml
  - Description: "Short explanation of the knowledge or resource gap that this dataset was intende..."
- `preprocessing_details` in D4D_Preprocessing.yaml
  - Description: "Details on preprocessing steps applied to the data.
..."
- `cleaning_details` in D4D_Preprocessing.yaml
  - Description: "Details on data cleaning procedures applied.
..."
- `labeling_details` in D4D_Preprocessing.yaml
  - Description: "Details on labeling/annotation procedures and quality metrics.
..."
- `raw_data_details` in D4D_Preprocessing.yaml
  - Description: "Details on raw data availability and access procedures.
..."
- `repository_details` in D4D_Uses.yaml
  - Description: "Details on the repository of known dataset uses.
..."
- `task_details` in D4D_Uses.yaml
  - Description: "Details on other potential tasks the dataset could be used for.
..."
- `impact_details` in D4D_Uses.yaml
  - Description: "Details on potential impacts, risks, and mitigation strategies.
..."
- `discouragement_details` in D4D_Uses.yaml
  - Description: "Details on tasks for which the dataset should not be used.
..."
- `quality_notes` in D4D_Variables.yaml
  - Description: "Notes about data quality, reliability, or known issues specific to this variable..."

**Impact:**
- RDF Serialization: critical
- Tool Breakage Risk: high

**Recommended Fix:**
- **KEEP** `acquisition_details` → `dcterms:description` (correct usage)
- **CHANGE** `mechanism_details` → `d4d:mechanism_details` (avoid conflict)
- **CHANGE** `collector_details` → `d4d:collector_details` (avoid conflict)
- **CHANGE** `timeframe_details` → `d4d:timeframe_details` (avoid conflict)
- **CHANGE** `collection_details` → `d4d:collection_details` (avoid conflict)
- **CHANGE** `source_description` → `d4d:source_description` (avoid conflict)
- **CHANGE** `missing` → `d4d:missing` (avoid conflict)
- **CHANGE** `why_missing` → `d4d:why_missing` (avoid conflict)
- **CHANGE** `relationship_details` → `d4d:relationship_details` (avoid conflict)
- **CHANGE** `split_details` → `d4d:split_details` (avoid conflict)
- **CHANGE** `anomaly_details` → `d4d:anomaly_details` (avoid conflict)
- **CHANGE** `bias_description` → `d4d:bias_description` (avoid conflict)
- **CHANGE** `limitation_description` → `d4d:limitation_description` (avoid conflict)
- **CHANGE** `future_guarantees` → `d4d:future_guarantees` (avoid conflict)
- **CHANGE** `confidentiality_details` → `d4d:confidentiality_details` (avoid conflict)
- **CHANGE** `warnings` → `d4d:warnings` (avoid conflict)
- **CHANGE** `identification` → `d4d:identification` (avoid conflict)
- **CHANGE** `distribution` → `d4d:distribution` (avoid conflict)
- **CHANGE** `deidentification_details` → `d4d:deidentification_details` (avoid conflict)
- **CHANGE** `sensitivity_details` → `d4d:sensitivity_details` (avoid conflict)
- **CHANGE** `review_details` → `d4d:review_details` (avoid conflict)
- **CHANGE** `impact_details` → `d4d:impact_details` (avoid conflict)
- **CHANGE** `notification_details` → `d4d:notification_details` (avoid conflict)
- **CHANGE** `consent_details` → `d4d:consent_details` (avoid conflict)
- **CHANGE** `revocation_details` → `d4d:revocation_details` (avoid conflict)
- **CHANGE** `maintainer_details` → `d4d:maintainer_details` (avoid conflict)
- **CHANGE** `erratum_details` → `d4d:erratum_details` (avoid conflict)
- **CHANGE** `update_details` → `d4d:update_details` (avoid conflict)
- **CHANGE** `retention_details` → `d4d:retention_details` (avoid conflict)
- **CHANGE** `version_details` → `d4d:version_details` (avoid conflict)
- **CHANGE** `extension_details` → `d4d:extension_details` (avoid conflict)
- **CHANGE** `response` → `d4d:response` (avoid conflict)
- **CHANGE** `response` → `d4d:response` (avoid conflict)
- **CHANGE** `response` → `d4d:response` (avoid conflict)
- **CHANGE** `preprocessing_details` → `d4d:preprocessing_details` (avoid conflict)
- **CHANGE** `cleaning_details` → `d4d:cleaning_details` (avoid conflict)
- **CHANGE** `labeling_details` → `d4d:labeling_details` (avoid conflict)
- **CHANGE** `raw_data_details` → `d4d:raw_data_details` (avoid conflict)
- **CHANGE** `repository_details` → `d4d:repository_details` (avoid conflict)
- **CHANGE** `task_details` → `d4d:task_details` (avoid conflict)
- **CHANGE** `impact_details` → `d4d:impact_details` (avoid conflict)
- **CHANGE** `discouragement_details` → `d4d:discouragement_details` (avoid conflict)
- **CHANGE** `quality_notes` → `d4d:quality_notes` (avoid conflict)

**Rationale:** Overuse of generic description property loses semantic distinction between different types of descriptive text


### C-006: slot_uri Conflict - dcterms:format

**Severity:** CRITICAL
**Conflict Count:** 2 different slots

**Usages:**
- `format` in D4D_Base_import.yaml
  - Description: "The file format, physical medium, or dimensions of a resource. This should be a ..."
- `data_substrate` in D4D_Composition.yaml
  - Description: "Type of data (e.g., raw text, images) from Bridge2AI standards.
..."

**Impact:**
- RDF Serialization: critical
- Tool Breakage Risk: high

**Recommended Fix:**
- **KEEP** `format` → `dcterms:format` (correct usage)
- **CHANGE** `data_substrate` → `d4d:data_substrate` (avoid conflict)

**Rationale:** Multiple semantic concepts mapped to same ontology term creates ambiguity


### C-007: slot_uri Conflict - dcterms:license

**Severity:** CRITICAL
**Conflict Count:** 2 different slots

**Usages:**
- `license` in D4D_Base_import.yaml
  - Description: "The legal license under which the resource is made available (e.g., "MIT", "CC-B..."
- `license_terms` in D4D_Data_Governance.yaml
  - Description: "Description of the dataset's license and terms of use (including links, costs, o..."

**Impact:**
- RDF Serialization: critical
- Tool Breakage Risk: high

**Recommended Fix:**
- **KEEP** `license` → `dcterms:license` (correct usage)
- **CHANGE** `license_terms` → `d4d:license_terms` (avoid conflict)

**Rationale:** License applies to different entities (dataset vs software) and should be differentiated


### C-008: slot_uri Conflict - dcterms:type

**Severity:** CRITICAL
**Conflict Count:** 3 different slots

**Usages:**
- `status` in D4D_Base_import.yaml
  - Description: "The status of the resource (e.g., draft, published, deprecated)...."
- `source_type` in D4D_Collection.yaml
  - Description: "Type of raw source (sensor, database, user input, web scraping, etc.).
..."
- `instance_type` in D4D_Composition.yaml
  - Description: "Multiple types of instances? (e.g., movies, users, and ratings).
..."

**Impact:**
- RDF Serialization: critical
- Tool Breakage Risk: high

**Recommended Fix:**
- **KEEP** `status` → `dcterms:type` (correct usage)
- **CHANGE** `source_type` → `d4d:source_type` (avoid conflict)
- **CHANGE** `instance_type` → `d4d:instance_type` (avoid conflict)

**Rationale:** Multiple semantic concepts mapped to same ontology term creates ambiguity


### C-009: slot_uri Conflict - schema:affiliation

**Severity:** CRITICAL
**Conflict Count:** 2 different slots

**Usages:**
- `affiliation` in D4D_Base_import.yaml
  - Description: "The organization(s) to which the person belongs in the context of this dataset. ..."
- `affiliations` in D4D_Motivation.yaml
  - Description: "Organizations with which the creator or team is affiliated...."

**Impact:**
- RDF Serialization: critical
- Tool Breakage Risk: high

**Recommended Fix:**
- **KEEP** `affiliation` → `schema:affiliation` (correct usage)
- **CHANGE** `affiliations` → `d4d:affiliations` (avoid conflict)

**Rationale:** Multiple semantic concepts mapped to same ontology term creates ambiguity



---

## High Priority Issues (Wrong Semantics)

### H-001: slot_uri Conflict - dcat:mediaType

**Usages:** encoding, media_type
**Files:** D4D_Base_import.yaml

### H-002: slot_uri Conflict - schema:contactPoint

**Usages:** contact_person, governance_committee_contact, contact_person
**Files:** D4D_Data_Governance.yaml, D4D_Ethics.yaml

### H-003: slot_uri Conflict - schema:identifier

**Usages:** id, id, orcid, identifiers_removed, target_dataset, latest_version_doi, grant_number, is_identifier
**Files:** D4D_Base_import.yaml, D4D_Composition.yaml, D4D_Motivation.yaml, D4D_Maintenance.yaml, D4D_Variables.yaml

### H-004: Range Mismatch - D4D_Base_import::Software::version

**Current Range:** `string` (multivalued: False)
**Issue:** Description implies list but multivalued=false
**Description:** "The version identifier of the software (e.g., "1.0.0", "2.3.1-beta")...."

### H-005: Range Mismatch - D4D_Base_import::Software::license

**Current Range:** `string` (multivalued: False)
**Issue:** Description implies list but multivalued=false
**Description:** "The license under which the software is distributed (e.g., "MIT", "Apache-2.0", "GPL-3.0")...."

### H-006: Range Mismatch - D4D_Base_import::Software::url

**Current Range:** `string` (multivalued: False)
**Issue:** Description implies list but multivalued=false
**Description:** "URL where the software can be found (e.g., homepage, repository, or documentation)...."

### H-007: Range Mismatch - D4D_Base_import::FormatDialect::comment_prefix

**Current Range:** `string` (multivalued: False)
**Issue:** Description implies list but multivalued=false
**Description:** "Character(s) used to indicate comment lines (e.g., "#" for CSV comments)...."

### H-008: Range Mismatch - D4D_Base_import::FormatDialect::delimiter

**Current Range:** `string` (multivalued: False)
**Issue:** Description implies list but multivalued=false
**Description:** "Field delimiter character (e.g., "," for CSV, "\t" for TSV)...."

### H-009: Range Mismatch - D4D_Base_import::FormatDialect::quote_char

**Current Range:** `string` (multivalued: False)
**Issue:** Description implies list but multivalued=false
**Description:** "Character used for quoting fields (e.g., '"' for CSV)...."

### H-010: Range Mismatch - D4D_Base_import::slots::dialect

**Current Range:** `string` (multivalued: False)
**Issue:** Description implies list but multivalued=false
**Description:** "Specific format dialect or variation (e.g., CSV dialect, JSON-LD profile)...."

### H-011: Range Mismatch - D4D_Base_import::slots::compression

**Current Range:** `CompressionEnum` (multivalued: False)
**Issue:** Description implies list but multivalued=false
**Description:** "Compression format used, if any (e.g., gzip, bzip2, zip)...."

### H-012: Range Mismatch - D4D_Base_import::slots::license

**Current Range:** `string` (multivalued: False)
**Issue:** Description implies list but multivalued=false
**Description:** "The legal license under which the resource is made available (e.g., "MIT", "CC-BY-4.0")...."

### H-013: Range Mismatch - D4D_Base_import::slots::version

**Current Range:** `string` (multivalued: False)
**Issue:** Description implies list but multivalued=false
**Description:** "The version identifier of the resource (e.g., "1.0", "2.3.1")...."


---

## Data-Driven Insights

Analysis of actual D4D records for AI_READI, CHORUS, CM4AI, and VOICE projects:

### Enum Candidates

Fields with limited value sets that could be enums:

- `id`: String field with only 4 distinct values (enum candidate)
  - Values: "https://chorus4ai.org/", "https://doi.org/10.13026/37yb-1t42", "https://doi.org/10.18130/V3/DXWOS5", "https://fairhub.io/datasets/2"
- `name`: String field with only 4 distinct values (enum candidate)
  - Values: "AI-READI", "Bridge2AI-Voice", "CHoRUS", "CM4AI"
- `title`: String field with only 4 distinct values (enum candidate)
  - Values: "Artificial Intelligence Ready and Equitable Atlas for Diabetes Insights (AI-READI)", "Bridge2AI-Voice - An ethically-sourced, diverse voice dataset linked to health information", "Cell Maps for Artificial Intelligence (CM4AI)", "Patient-Focused Collaborative Hospital Repository Uniting Standards (CHoRUS) for Equitable AI"
- `description`: String field with only 4 distinct values (enum candidate)
  - Values: "CHoRUS for Equitable AI is a Bridge2AI data generation project developing the most diverse, high-resolution, ethically sourced, AI-ready critical care dataset to answer the grand challenge of improving recovery from acute illness. The project spans 20 academic centers (14 data acquisition centers) and creates a publicly available dataset of over 100,000 critically ill patients with multi-modal data including structured EHR, waveform telemetry, medical imaging, EEG, and clinical notes. All data is standardized to the OMOP Common Data Model with additional formats (DICOM, WFDB, OHNLP tokenization) and includes comprehensive metadata schemas. Patient-focused efforts determine ethical and legal approaches to manage privacy and bias while accounting for Social Determinants of Health. A visualization and annotation environment labels data with targets important for prediction. The project emphasizes skills and workforce development for a next generation of diverse academic and community AI scientists through training programs and partnerships with AIM-AHEAD. As of November 2024, the dataset covers 14 different hospitals with 23,400 unique admissions.
", "CM4AI is the Functional Genomics Data Generation Project in the U.S. National Institutes of Health's (NIH) Bridge to Artificial Intelligence (Bridge2AI) program. Its overarching mission is to produce ethical, AI-ready datasets of cell architecture, inferred from multimodal data collected for human cell lines, to enable transformative biomedical AI research. The project delivers machine-readable hierarchical maps of cell architecture as AI-Ready data produced from multimodal interrogation of 100 chromatin modifiers and 100 metabolic enzymes involved in cancer, neuropsychiatric, and cardiac disorders in disease-relevant cell lines under perturbed and unperturbed conditions. Data streams include immunofluorescence (IF) subcellular microscopy for spatial proteomics, affinity purification mass spectroscopy (AP-MS) and size exclusion mass spectroscopy (SEC-MS) for protein-protein interaction (PPI) data, and single-cell CRISPR-Cas perturbation screens by cell type. Input data streams are integrated via the Multi-Scale Integrated Cell (MuSIC) software pipeline employing deep learning models and community detection algorithms, and output cell maps are packaged with provenance graphs and rich metadata as AI-Ready datasets in RO-Crate format using the FAIRSCAPE framework.
", "The AI-READI is a flagship dataset consisting of multimodal data collected from 4,000 individuals with and without Type 2 Diabetes Mellitus (T2DM), harmonized across 3 data collection sites (Birmingham, Alabama; San Diego, California; Seattle, Washington). The dataset was designed with future AI/Machine Learning studies in mind, including recruitment sampling procedures aimed at achieving approximately equal distribution of participants across diabetes severity (triple-balanced by race/ethnicity, biological sex, and T2DM severity), as well as a multi-domain data acquisition protocol (survey data, physical measurements, clinical data, imaging data, wearable device data, environmental sensors, biospecimens) to enable downstream AI/ML analyses that may not be feasible with existing data sources such as claims or electronic health records data. The goal is to better understand salutogenesis (the pathway from disease to health) in T2DM. The study follows FAIR principles and incorporates ethical and equitable data collection and management practices.
", "The Bridge2AI-Voice project seeks to create an ethically sourced flagship dataset to enable future research in artificial intelligence and support critical insights into the use of voice as a biomarker of health. The human voice contains complex acoustic markers which have been linked to important health conditions including dementia, mood disorders, and cancer. When viewed as a biomarker, voice is a promising characteristic to measure as it is simple to collect, cost-effective, and has broad clinical utility. This comprehensive collection provides voice recordings with corresponding clinical information from participants selected based on known conditions which manifest within the voice waveform including voice disorders, neurological disorders, mood disorders, and respiratory disorders. The dataset is designed to fuel voice AI research, establish data standards, and promote ethical and trustworthy AI/ML development for voice biomarkers of health. Data collection occurs through a multi-institutional collaborative effort using standardized protocols, custom smartphone applications, and rigorous ethical oversight. The initial release (v1.0) provides 12,523 recordings for 306 participants collected across five sites in North America, with derived features such as spectrograms, MFCCs, acoustic features, and clinical phenotype data. Raw audio data is available through controlled access to protect participant privacy.
"
- `page`: String field with only 4 distinct values (enum candidate)
  - Values: "https://chorus4ai.org/", "https://docs.b2ai-voice.org", "https://fairhub.io/datasets/2", "https://www.cm4ai.org"
- `license`: String field with only 4 distinct values (enum candidate)
  - Values: "Bridge2AI Voice Registered Access License", "CC BY-NC 4.0", "CC BY-NC-SA 4.0", "Controlled Access with Data Use Agreement"
- `license_and_use_terms.name`: String field with only 4 distinct values (enum candidate)
  - Values: "Bridge2AI Voice Registered Access License", "CHoRUS Controlled Access License", "Creative Commons Attribution Non-Commercial", "Creative Commons Attribution Non-Commercial Share-Alike"
- `license_and_use_terms.description`: String field with only 4 distinct values (enum candidate)
  - Values: "Data licensed for reuse under Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International license (https://creativecommons.org/licenses/by-nc-sa/4.0/). Attribution is required to the copyright holders and the Cell Maps for Artificial Intelligence project. Any publications referencing this data or derived products should cite the bioRxiv article (Clark T, et al. Cell Maps for Artificial Intelligence: AI-Ready Maps of Human Cell Architecture from Disease-Relevant Cell Lines. BioRXiv, May 2024. doi:10.1101/2024.05.21.589311) and directly cite the data collection. Commercial use requires separate license negotiation with copyright holder (UCSD, Stanford, and/or UCSF depending upon specific data package). A Data Access Committee will supervise ethical matters related to dataset distribution and potential dual licensing for commercial use. Copyright (c) 2025 The Regents of the University of California except where otherwise noted. Spatial proteomics raw image data is copyright (c) 2025 The Board of Trustees of the Leland Stanford Junior University.
", "Dataset distributed under controlled access requiring institutional email registration and signed licensing agreement. Access granted after review and approval process. Participants must complete registration form with name, email (institutional, not personal), and institution. Once approved, users receive email with access instructions to CHoRUS secure enclave. Contact for access requests: dbold@emory.edu or jared.houghtaling@tuftsmedicine.org.
", "Public access data distributed under Creative Commons Attribution Non-Commercial (CC BY-NC 4.0) license. Permits others to distribute, remix, adapt, build upon this work non-commercially, and license their derivative works on different terms, provided the original work is properly cited, appropriate credit is given, any changes made indicated, and the use is non-commercial. Controlled access data requires data use agreement. See http://creativecommons.org/licenses/by-nc/4.0/ for full license terms.
", "Public access dataset distributed through PhysioNet under Bridge2AI Voice Registered Access License. Only registered users who sign the specified Data Use Agreement (Bridge2AI Voice Registered Access Agreement) can access files. Data covered under Certificate of Confidentiality which must be asserted against compulsory legal demands. Raw audio data available through controlled access only via Data Access Compliance Office (DACO) requiring distinct application. Recipient must adhere to PhysioNet requirements managed by MIT Laboratory for Computational Physiology, supported by NIBIB under grant R01EB030362.
"
- `updates.name`: String field with only 4 distinct values (enum candidate)
  - Values: "Ongoing data collection and expansion", "Periodic data releases and maintenance plan", "Quarterly Data Releases and Maintenance Plan", "Versioned releases with ongoing data collection"
- `updates.description`: String field with only 4 distinct values (enum candidate)
  - Values: "Dataset regularly updated and augmented through end of project in November 2026. Beta releases on quarterly basis with periodic data augmentation. Initial alpha release (v0.5) provided as supplemental data. March 2025 Beta (V1.4) includes perturb-seq in KOLF2.1J iPSCs, SEC-MS in iPSCs and derivatives, and IF images in MDA-MB-468 under three conditions. June 2025 Beta (V2.1) revision adds RGB IF images, ro-crate metadata corrections, and naming convention changes. Future releases will include computed cell maps and complete integration of all data streams. Long-term preservation in University of Virginia Dataverse with committed institutional support.
", "Dataset updated continuously as data collection progresses at 14 acquisition centers. As of November 2024, covers 14 hospitals with 23,400 unique admissions. Target exceeds 100,000 critically ill patients. Project timeline extends through November 30, 2026 (with approved no-cost extension). Regular status updates tracked through GitHub project management system. Sites provide updates via GitHub interface or Google Form submissions.
", "Dataset updated periodically as enrollment progresses toward target of 4,000 participants by November 2026. Version-specific documentation maintained for each release. Biorepository maintained at UAB CCTS with long-term storage protocols. Data sharing policies under ongoing development by Data Access Committee. Pilot data released May 2024; all data through July 31, 2024 released November 2024.
", "Dataset updated with versioned releases as data collection progresses. Initial release v1.0 published January 17, 2025 with 12,523 recordings from 306 participants. v1.1 released January 17, 2025 adding MFCC features. v2.0.0 released April 16, 2025. v2.0.1 released August 18, 2025. Latest version available at https://doi.org/10.13026/37yb-1t42. Data collection ongoing through November 30, 2026. Version-specific documentation maintained. As of v1.1, only adult cohort data available; pediatric cohort data planned for future releases with additional privacy precautions.
"
- `updates.frequency`: String field with only 4 distinct values (enum candidate)
  - Values: "Continuous updates through November 2026", "Periodic releases with ongoing enrollment; final release planned for late 2026", "Periodic versioned releases during data collection period (2022-2026)", "Quarterly updates through November 2026; long-term preservation thereafter"
- `retention_limit.name`: String field with only 4 distinct values (enum candidate)
  - Values: "Data and biospecimen retention", "Data retention and disposition", "Long-Term Preservation Plan", "Long-term dataset retention"
- `retention_limit.description`: String field with only 4 distinct values (enum candidate)
  - Values: "Data Transfer and Use Agreement specifies retention requirements. Upon termination or expiration of agreement (two years after start date, project completion, or ethics approval expiration), data shall be destroyed per provider instructions with written certification required within 30 days. Recipient may retain one copy to extent necessary to comply with records retention requirements under law, regulation, institutional policy, and for research integrity and verification purposes. Restrictions apply to archival copies as long as recipient holds data.
", "Digital data maintained according to NIH data sharing policies and institutional requirements. Controlled access model ensures long-term availability for research while protecting patient privacy.
", "Digital data maintained according to NIH data sharing policies with long-term preservation in University of Virginia's LibraData repository supported by committed institutional funds. No planned sunset for data availability. Archived RO-Crates with persistent identifiers (ARK, future DOIs) ensure long-term accessibility and citability.
", "Digital data maintained according to NIH data sharing policies. Biospecimen retention subject to institutional policies and consent agreements. Finite number of biospecimen samples available for distribution.
"
- `human_subject_research.name`: String field with only 4 distinct values (enum candidate)
  - Values: "AI-READI Human Subjects Research", "Bridge2AI-Voice Human Subjects Research", "CHoRUS Human Subjects Research", "CM4AI Non-Human Subjects Research"
- `human_subject_research.description`: String field with only 4 distinct values (enum candidate)
  - Values: "CM4AI data are distinctive within Bridge2AI in that they are non-clinical data from tissue cultures and are considered to be de-identified as they cannot be matched, with current knowledge, to a human subject. Both cell lines (MDA-MB-468 and KOLF2.1J) are commercially available, ethically sourced, de-identified cell lines. MDA-MB-468 available from ATCC. KOLF2.1J available from HipSci resource for non-profit organizations via simple MTA. Ethics team developed comprehensive plan for ethical preparation, licensing, dissemination, and data access supervision balancing openness with IP protection and commercialization monitoring.
", "Data collection and sharing approved by University of South Florida Institutional Review Board. Participants provided written informed consent for data collection initiative and data sharing. Consent process includes authorization for voice data collection, access to medical information through EHR platforms for gold standard validation, and permission to share research data. Bioethics guidance integrated throughout study design and conduct. Ethics module develops new guidelines for consenting to voice data collection, voice data sharing, and utilization in context of voice AI technology. Project addresses ethical and trustworthy issues from voice data generation and AI/ML research through clinical adoption and downstream health decisions.
", "Retrospective data collection from critically ill patients approved through institutional review processes. Community-facing ethics focus groups conducted to determine what data is appropriate for public sharing. Legal framework established for collecting data at scale. Patient-focused efforts determine ethical and legal approaches to manage privacy and bias while accounting for Social Determinants of Health. Project draws expertise from law, ethics, health services, biomedical science, engineering, and scientific journal publications disciplines.
", "Study approved by Institutional Review Board (IRB) of University of Washington (approval number STUDY00016228), with reliance agreements from IRBs of University of Alabama at Birmingham and University of California, San Diego. Written informed consent provided by all participants. Bioethics guidance integrated throughout study design. Community Advisory Board of 11 persons with diversity in race and ethnicity contributes to protocol development. Ethical and equitable data collection and management practices implemented.
"

### Multivalued Fields

Fields that contain lists in actual data (verify schema has multivalued: true):

- `keywords`
- `purposes`
- `tasks`
- `addressing_gaps`
- `creators`
- `funders`
- `instances`
- `subsets`
- `sampling_strategies`
- `subpopulations`
- `collection_mechanisms`
- `acquisition_methods`
- `preprocessing_strategies`
- `cleaning_strategies`
- `intended_uses`

---

## Appendices

### A: Files Requiring Changes

Priority-ordered list of schema files needing updates:

1. `src/data_sheets_schema/schema/D4D_Base_import.yaml` (CRITICAL - foundational)
2. `src/data_sheets_schema/schema/D4D_Composition.yaml` (HIGH)
3. `src/data_sheets_schema/schema/D4D_Data_Governance.yaml` (HIGH)
4. `src/data_sheets_schema/schema/D4D_Distribution.yaml` (MEDIUM)
5. `src/data_sheets_schema/schema/D4D_Maintenance.yaml` (MEDIUM)

### B: Validation Tools

Automated validation scripts created:

- `scripts/slot_uri_conflict_detector.py` - Detects slot_uri conflicts
- `scripts/range_description_checker.py` - Checks range-description alignment
- `scripts/data_value_analyzer.py` - Analyzes actual data values

### C: Next Steps

1. Review and prioritize CRITICAL issues
2. Create implementation plan for fixes
3. Coordinate with tool maintainers for breaking changes
4. Develop data migration strategy if needed
5. Update documentation with rationale for changes
