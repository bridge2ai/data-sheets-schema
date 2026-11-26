# Detailed Evaluation: CHORUS - CLAUDECODE_RELEASE

Evaluated: 2026-11-25T19:12:22.757429
File: `data/d4d_concatenated/claudecode_release/2026-11-25c_claude-fable-5-2-claudecode-generic-v9_rep1/CHORUS_d4d.yaml`

Instrument: `b38117d96e73987f236d4d3d47da5b84a952401537f9a2ae4d2c44bf981fc064`
Applicability context: `fca403729b83dda36a67c4b749455b0fd864ba992e0e40b9a0f5c65bc039bfad`
Scope: single_dataset
## Overall Scores

- **Rubric10**: 25.0/50 (50.0%)
- **Rubric20**: 49.0/88 (55.7%)

## Rubric10 Element Scores

| ID | Element | Score | Details |
|----|---------|-------|---------|
| 1 | Dataset Discovery and Identification | 3/5 | 3/5 applicable sub-elements present; 0 N/A |
| 2 | Dataset Access and Retrieval | 4/5 | 4/5 applicable sub-elements present; 0 N/A |
| 3 | Data Reuse and Interoperability | 2/5 | 2/5 applicable sub-elements present; 0 N/A |
| 4 | Ethical Use and Privacy Safeguards | 2/5 | 2/5 applicable sub-elements present; 0 N/A |
| 5 | Data Composition and Structure | 3/5 | 3/5 applicable sub-elements present; 0 N/A |
| 6 | Data Provenance and Version Tracking | 2/5 | 2/5 applicable sub-elements present; 0 N/A |
| 7 | Scientific Motivation and Funding Transparency | 5/5 | 5/5 applicable sub-elements present; 0 N/A |
| 8 | Technical Transparency (Data Collection and Processing) | 3/5 | 3/5 applicable sub-elements present; 0 N/A |
| 9 | Dataset Evaluation and Limitations Disclosure | 0/5 | 0/5 applicable sub-elements present; 0 N/A |
| 10 | Cross-Platform and Community Integration | 1/5 | 1/5 applicable sub-elements present; 0 N/A |

### Rubric10 Sub-Element Details


#### 1. Dataset Discovery and Identification

Can a user or system discover and uniquely identify this dataset?

- ✅ **Persistent Identifier (DOI, RRID, or URI)**
  - Applicability: applicable; This item applies to every dataset
  - Found: #/id: https://chorus4ai.org/
- ✅ **Dataset Title and Description Completeness**
  - Applicability: applicable; This item applies to every dataset
  - Found: #/title: CHoRUS Dataset
  - Found: #/description: The CHoRUS dataset is a multicenter, multimodal and high-resolution clinical care dataset produced b
- ❌ **Keywords or Tags for Searchability**
  - Applicability: applicable; This item applies to every dataset
  - Fields checked: keywords
- ✅ **Landing Page and Resources (page, hierarchical resources)**
  - Applicability: applicable; This item applies to every dataset
  - Found: #/page: https://chorus4ai.org/
- ❌ **Hierarchical Structure (parent datasets, relationships)**
  - Applicability: applicable; This item applies to every dataset
  - Fields checked: parent_datasets, related_datasets

#### 2. Dataset Access and Retrieval

Can the dataset and its associated resources be located, accessed, and downloaded?

- ✅ **Access Policy and IP Restrictions Defined**
  - Applicability: applicable; This item applies to every dataset
  - Found: #/license_and_use_terms: {'license_terms': 'For participants of the AIM-AHEAD Bridge2AI for Clinical Care Training Program, t
- ✅ **Regulatory Compliance and Confidentiality Classification**
  - Applicability: unknown; regulated_access: not declared; retained in the denominator
  - Found: #/regulatory_restrictions: {'confidentiality_level': 'restricted', 'description': 'The September 09, 2025 webinar describes the
- ❌ **Download URL or Platform Link Available**
  - Applicability: applicable; This item applies to every dataset
  - Fields checked: download_url
- ✅ **Distribution Formats and File Types Specified**
  - Applicability: applicable; This item applies to every dataset
  - Found: #/distribution_formats/0: {'name': 'Cloud enclave', 'description': 'The September 09, 2025 webinar states that OMOP and teleme
- ✅ **Related Datasets and External Resources Linked**
  - Applicability: applicable; This item applies to every dataset
  - Found: #/external_resources/0: {'name': 'chorus-ai GitHub organization', 'external_resources': ['https://github.com/chorus-ai'], 'd
  - Found: #/external_resources/1: {'name': 'Bridge2AI CHoRUS website', 'external_resources': ['www.bridge2ai.org/chorus'], 'descriptio

#### 3. Data Reuse and Interoperability

Is sufficient information provided to reuse and integrate the dataset with others?
Note: Evaluate whether the dataset is designed for integration with similar datasets, including: common identifiers for cross-dataset linking, standardized formats for data harmonization, and documented integration procedures.


- ✅ **License Terms Allow Reuse**
  - Applicability: unknown; shared_dataset: not declared; retained in the denominator
  - Found: #/license_and_use_terms: {'license_terms': 'For participants of the AIM-AHEAD Bridge2AI for Clinical Care Training Program, t
- ❌ **Data Formats Are Standardized (encoding, format)**
  - Applicability: unknown; shared_dataset: not declared; retained in the denominator
  - Fields checked: format, encoding
- ❌ **Schema or Ontology Conformance Stated**
  - Applicability: unknown; shared_dataset: not declared; retained in the denominator
  - Fields checked: conforms_to, conforms_to_schema
- ❌ **Variable Metadata with Identifiers Defined**
  - Applicability: unknown; shared_dataset: not declared; retained in the denominator
  - Fields checked: variables
- ✅ **Use Guidance Provided (intended, prohibited uses)**
  - Applicability: applicable; This item applies to every dataset
  - Found: #/intended_uses/0: {'description': 'Planned: a holdout test set accessible for model external validation, to aid market
  - Found: #/intended_uses/1: {'description': 'Hands-on training using the CHoRUS dataset "to support the development of transnati
  - Found: #/intended_uses/2: {'description': 'Building machine-learning (ML) and artificial intelligence (AI)-derived models to i

#### 4. Ethical Use and Privacy Safeguards

Does the dataset document the ethical oversight, privacy, consent and safeguards that apply to its subjects and governance context? Equivalent local ethics and regulatory frameworks are accepted; HIPAA or an IRB is not a universal requirement.

- ❌ **IRB or Ethics Review and Data Protection Impact**
  - Applicability: unknown; any: human_subjects: not declared; retained in the denominator; regulated_access: not declared; retained in the denominator
  - Fields checked: ethical_reviews, human_subject_research, data_protection_impacts
- ✅ **Deidentification Method Described**
  - Applicability: unknown; any: human_subjects: not declared; retained in the denominator; regulated_access: not declared; retained in the denominator
  - Found: #/is_deidentified: {'deidentification_details': 'The September 09, 2025 webinar states that 1000 images are currently a
- ✅ **Privacy Protections and Re-identification Risk Assessment**
  - Applicability: unknown; human_subjects: not declared; retained in the denominator
  - Found: #/participant_privacy/0: {'description': 'Planned: the NIH project abstract states the project will transform data using appr
- ❌ **Informed Consent Obtained from Participants**
  - Applicability: unknown; human_subjects: not declared; retained in the denominator
  - Fields checked: informed_consent
- ❌ **Vulnerable Populations and Compensation Documented**
  - Applicability: unknown; human_subjects: not declared; retained in the denominator
  - Fields checked: vulnerable_populations, participant_compensation

#### 5. Data Composition and Structure

Can the dataset's structure, modality, and population be understood from metadata?

- ❌ **Cohort or Subpopulations Characteristics Described**
  - Applicability: applicable; This item applies to every dataset
  - Fields checked: subpopulations
- ✅ **Number of Instances or Samples Reported**
  - Applicability: applicable; This item applies to every dataset
  - Found: #/instances/0: {'instance_type': 'patient admission', 'counts': 50000, 'description': 'The project website\'s "Curr
  - Found: #/instances/1: {'instance_type': 'row of EHR OMOP data', 'counts': 1600000000, 'description': 'The project website\
  - Found: #/instances/2: {'instance_type': 'admission with radiology data', 'counts': 7642, 'description': 'The project websi
  - Found: #/instances/3: {'instance_type': 'Demographics', 'description': "Data type listed in the webinar's CHoRUS Dataset t
  - Found: #/instances/4: {'instance_type': 'Medication administration', 'description': "Data type listed in the webinar's CHo
  - Found: #/instances/5: {'instance_type': 'Procedures', 'description': "Data type listed in the webinar's CHoRUS Dataset tab
  - Found: #/instances/6: {'instance_type': 'Nursing flowsheets', 'description': "Data type listed in the webinar's CHoRUS Dat
  - Found: #/instances/7: {'instance_type': 'Diagnoses', 'description': "Data type listed in the webinar's CHoRUS Dataset tabl
  - Found: #/instances/8: {'instance_type': 'Clinical notes', 'description': "Data type listed in the webinar's CHoRUS Dataset
  - Found: #/instances/9: {'instance_type': 'Imaging', 'description': "Data type listed in the webinar's CHoRUS Dataset table:
  - Found: #/instances/10: {'instance_type': 'Waveform telemetry', 'description': "Data type listed in the webinar's CHoRUS Dat
  - Found: #/instances/11: {'instance_type': 'Waveform EEG', 'description': "Data type listed in the webinar's CHoRUS Dataset t
- ❌ **Variable-Level Metadata, Tabular Flag, and Data Splits**
  - Applicability: applicable; This item applies to every dataset
  - Fields checked: variables, is_tabular, is_data_split, is_subpopulation
- ✅ **Data Topics or Conditions Represented**
  - Applicability: applicable; This item applies to every dataset
  - Found: #/instances/0: {'instance_type': 'patient admission', 'counts': 50000, 'description': 'The project website\'s "Curr
  - Found: #/instances/1: {'instance_type': 'row of EHR OMOP data', 'counts': 1600000000, 'description': 'The project website\
  - Found: #/instances/2: {'instance_type': 'admission with radiology data', 'counts': 7642, 'description': 'The project websi
  - Found: #/instances/3: {'instance_type': 'Demographics', 'description': "Data type listed in the webinar's CHoRUS Dataset t
  - Found: #/instances/4: {'instance_type': 'Medication administration', 'description': "Data type listed in the webinar's CHo
  - Found: #/instances/5: {'instance_type': 'Procedures', 'description': "Data type listed in the webinar's CHoRUS Dataset tab
  - Found: #/instances/6: {'instance_type': 'Nursing flowsheets', 'description': "Data type listed in the webinar's CHoRUS Dat
  - Found: #/instances/7: {'instance_type': 'Diagnoses', 'description': "Data type listed in the webinar's CHoRUS Dataset tabl
  - Found: #/instances/8: {'instance_type': 'Clinical notes', 'description': "Data type listed in the webinar's CHoRUS Dataset
  - Found: #/instances/9: {'instance_type': 'Imaging', 'description': "Data type listed in the webinar's CHoRUS Dataset table:
  - Found: #/instances/10: {'instance_type': 'Waveform telemetry', 'description': "Data type listed in the webinar's CHoRUS Dat
  - Found: #/instances/11: {'instance_type': 'Waveform EEG', 'description': "Data type listed in the webinar's CHoRUS Dataset t
- ✅ **Data Quality, Anomalies, and Missing Data Documented**
  - Applicability: applicable; This item applies to every dataset
  - Found: #/sampling_strategies/0: {'description': 'Planned: the NIH project abstract describes sampling to ensure comprehensive sets o

#### 6. Data Provenance and Version Tracking

Can a user determine dataset versions, update history, and provenance?

- ❌ **Dataset Version Number Provided**
  - Applicability: unknown; shared_dataset: not declared; retained in the denominator
  - Fields checked: version
- ❌ **Version Access Methods Documented**
  - Applicability: unknown; shared_dataset: not declared; retained in the denominator
  - Fields checked: version_access
- ✅ **Change Descriptions and Errata Provided**
  - Applicability: unknown; shared_dataset: not declared; retained in the denominator
  - Found: #/updates: {'update_details': 'The project website distinguishes a "Current Released Dataset" from an "Anticipa
- ✅ **Update Schedule or Frequency Indicated**
  - Applicability: unknown; shared_dataset: not declared; retained in the denominator
  - Found: #/updates: {'update_details': 'The project website distinguishes a "Current Released Dataset" from an "Anticipa
- ❌ **Provenance, Source Derivation, and Raw Data Sources**
  - Applicability: unknown; shared_dataset: not declared; retained in the denominator
  - Fields checked: was_derived_from, release_notes, raw_data_sources

#### 7. Scientific Motivation and Funding Transparency

Does the metadata clearly state why the dataset exists and who funded it?

- ✅ **Motivation or Purpose for Dataset Creation**
  - Applicability: applicable; This item applies to every dataset
  - Found: #/purposes/0: {'response': 'Generate data for ML/AI applications aimed at characterizing acute and critical care i
  - Found: #/purposes/1: {'response': 'Develop a publicly available, AI-ready critical care dataset, while ensuring the metho
  - Found: #/purposes/2: {'response': 'Develop the most diverse, high-resolution, ethically sourced, AI-ready data set to ans
- ✅ **Primary Research Objectives or Tasks**
  - Applicability: applicable; This item applies to every dataset
  - Found: #/tasks/0: {'response': 'Characterizing acute and critical care illness.'}
  - Found: #/tasks/1: {'response': 'Predicting complications.'}
  - Found: #/tasks/2: {'response': 'Measuring treatment response among patients with acute or critical illness.'}
- ✅ **Funding Sources and Mechanisms Listed**
  - Applicability: applicable; This item applies to every dataset
  - Found: #/funders/0: {'name': 'NIH Common Fund Bridge2AI program', 'grantor': 'National Institutes of Health (NIH)', 'gra
- ✅ **Grant IDs or Award Numbers Present**
  - Applicability: applicable; This item applies to every dataset
  - Found: #/funders/0: {'name': 'NIH Common Fund Bridge2AI program', 'grantor': 'National Institutes of Health (NIH)', 'gra
- ✅ **Creators and Acknowledgements Documented**
  - Applicability: applicable; This item applies to every dataset
  - Found: #/creators/0: {'description': 'Designated principal investigator on the NIH RePORTER project page and listed on th
  - Found: #/creators/1: {'name': 'Azra Bihorac', 'description': 'Listed on the "Bridge2AI CHoRUS Leadership Team" slide of t
  - Found: #/creators/2: {'name': 'Xiaoqian Jiang', 'description': 'Listed on the "Bridge2AI CHoRUS Leadership Team" slide of
  - Found: #/creators/3: {'name': 'Yulia Strekalova', 'description': 'Listed on the "Bridge2AI CHoRUS Leadership Team" slide 
  - Found: #/creators/4: {'name': 'Parisa Rashidi', 'description': 'Listed on the "Bridge2AI CHoRUS Leadership Team" slide of
  - Found: #/creators/5: {'name': 'Manlik Kwong', 'description': 'Listed on the "Bridge2AI CHoRUS Leadership Team" slide of t
  - Found: #/funders/0: {'name': 'NIH Common Fund Bridge2AI program', 'grantor': 'National Institutes of Health (NIH)', 'gra

#### 8. Technical Transparency (Data Collection and Processing)

Can data collection and processing steps be replicated or understood?
Note: Preprocessing and collection metadata may be represented as structured text descriptions OR as machine-readable provenance graphs (e.g., W3C PROV-O, workflow graphs). Evaluation should check for: (1) structured text descriptions OR (2) graph representations with entity-activity-agent relationships. Both formats are acceptable.


- ✅ **Collection Mechanisms and Settings Described**
  - Applicability: unknown; data_collection: not declared; retained in the denominator
  - Found: #/collection_mechanisms/0: {'mechanism_details': 'Retrospective data collection of multi-modal data across 14 different hospita
  - Found: #/collection_mechanisms/1: {'mechanism_details': 'The chorus-ai GitHub overview points data managers at data contributing sites
- ❌ **Data Acquisition Methods Listed**
  - Applicability: unknown; data_collection: not declared; retained in the denominator
  - Fields checked: acquisition_methods
- ✅ **Preprocessing, Cleaning, Labeling, and Annotation Quality**
  - Applicability: unknown; data_processing: not declared; retained in the denominator
  - Found: #/preprocessing_strategies/0: {'preprocessing_details': 'The project website states that the data utilizes ongoing and new standar
  - Found: #/preprocessing_strategies/1: {'preprocessing_details': 'Semantic mapping: the chorus-ai GitHub organization provides validated se
  - Found: #/preprocessing_strategies/2: {'preprocessing_details': 'Clinical notes are extracted and tokenized using the OHNLP toolkit; the w
  - Found: #/labeling_strategies/0: {'description': 'Planned: the NIH project abstract describes developing capabilities to label data, 
- ❌ **Software and Tools Documented**
  - Applicability: unknown; processing_software: not declared; retained in the denominator
  - Fields checked: software_and_tools
- ✅ **External Standards, Resources, and Imputation Protocols**
  - Applicability: applicable; This item applies to every dataset
  - Found: #/external_resources/0: {'name': 'chorus-ai GitHub organization', 'external_resources': ['https://github.com/chorus-ai'], 'd
  - Found: #/external_resources/1: {'name': 'Bridge2AI CHoRUS website', 'external_resources': ['www.bridge2ai.org/chorus'], 'descriptio

#### 9. Dataset Evaluation and Limitations Disclosure

Does the metadata communicate known risks, biases, or dataset limitations?

- ❌ **Known Limitations Documented**
  - Applicability: applicable; This item applies to every dataset
  - Fields checked: known_limitations
- ❌ **Biases Categorized Using Standard Taxonomy (RAI-aligned)**
  - Applicability: applicable; This item applies to every dataset
  - Fields checked: known_biases
- ❌ **Data Anomalies and Quality Issues Noted**
  - Applicability: applicable; This item applies to every dataset
  - Fields checked: anomalies
- ❌ **Sensitive Content and Warnings Provided**
  - Applicability: applicable; This item applies to every dataset
  - Fields checked: sensitive_elements, content_warnings
- ❌ **Ethical Review and Social Impact Analysis**
  - Applicability: applicable; This item applies to every dataset
  - Fields checked: ethical_reviews, future_use_impacts

#### 10. Cross-Platform and Community Integration

Does the dataset connect to relevant repositories, communities and standards? A shared dataset needs citation or identifier guidance and a named hosting or preservation route appropriate to its domain.

- ❌ **Dataset Published on a Recognized Platform**
  - Applicability: unknown; shared_dataset: not declared; retained in the denominator
  - Fields checked: publisher
- ❌ **Citation and DOI for Cross-referencing**
  - Applicability: unknown; shared_dataset: not declared; retained in the denominator
  - Fields checked: citation, doi
- ❌ **Community Standards or Schema Conformance**
  - Applicability: unknown; shared_dataset: not declared; retained in the denominator
  - Fields checked: conforms_to
- ✅ **Outreach Materials and Documentation Links**
  - Applicability: unknown; shared_dataset: not declared; retained in the denominator
  - Found: #/external_resources/0: {'name': 'chorus-ai GitHub organization', 'external_resources': ['https://github.com/chorus-ai'], 'd
  - Found: #/external_resources/1: {'name': 'Bridge2AI CHoRUS website', 'external_resources': ['www.bridge2ai.org/chorus'], 'descriptio
  - Found: #/page: https://chorus4ai.org/
- ❌ **Related Datasets with Typed Relationships**
  - Applicability: unknown; shared_dataset: not declared; retained in the denominator
  - Fields checked: related_datasets

## Rubric20 Question Scores


### Structural Completeness

| ID | Question | Score | Status |
|----|----------|-------|--------|
| 1 | Field Completeness | 3.0/5 | ✅ |
| 2 | Entry Length Adequacy | 5.0/5 | ✅ |
| 3 | Keyword Diversity | 0.0/5 | ❌ |
| 4 | File Enumeration and Type Variety | 0.0/5 | ❌ |
| 5 | Data File Size Availability | Pass | ✅ |

Applicability for Q1: applicable; This item applies to every dataset


Applicability for Q2: applicable; This item applies to every dataset


Applicability for Q3: applicable; This item applies to every dataset


Applicability for Q4: applicable; This item applies to every dataset


Applicability for Q5: applicable; This item applies to every dataset


### Metadata Quality & Content

| ID | Question | Score | Status |
|----|----------|-------|--------|
| 6 | Dataset Identification Metadata | Pass | ✅ |
| 7 | Funding and Acknowledgements Completeness | 5.0/5 | ✅ |
| 8 | Ethical and Privacy Declarations | 3.0/5 | ✅ |
| 9 | Access Requirements and Governance Documentation | 3.0/5 | ✅ |
| 10 | Interoperability, Standardization, and Cross-Platform Integration | 3.0/5 | ✅ |

Applicability for Q6: applicable; This item applies to every dataset


Applicability for Q7: applicable; This item applies to every dataset


Applicability for Q8: unknown; human_subjects: not declared; retained in the denominator


Applicability for Q9: applicable; This item applies to every dataset


Applicability for Q10: unknown; shared_dataset: not declared; retained in the denominator


### Technical Documentation

| ID | Question | Score | Status |
|----|----------|-------|--------|
| 11 | Tool and Software Transparency | 3.0/5 | ✅ |
| 12 | Collection Protocol Clarity | 3.0/5 | ✅ |
| 13 | Version History, Maintenance, and Sustainability | 3.0/5 | ✅ |
| 14 | Associated Publications | 3.0/5 | ✅ |
| 15 | Human Subject Representation | 3.0/5 | ✅ |

Applicability for Q11: unknown; data_processing: not declared; retained in the denominator


Applicability for Q12: unknown; data_collection: not declared; retained in the denominator


Applicability for Q13: unknown; shared_dataset: not declared; retained in the denominator


Applicability for Q14: applicable; This item applies to every dataset


Applicability for Q15: unknown; human_subjects: not declared; retained in the denominator


### FAIRness & Accessibility

| ID | Question | Score | Status |
|----|----------|-------|--------|
| 16 | Findability (Persistent Links) | Pass | ✅ |
| 17 | Accessibility (Access Mechanism) | 3.0/5 | ✅ |
| 18 | Reusability, Use Guidance, and Social Impact | 3.0/5 | ✅ |
| 19 | Data Integrity, Provenance Graph, and Quality | 3.0/5 | ✅ |
| 20 | Bias Documentation and Responsible AI Alignment | 0.0/5 | ❌ |

Applicability for Q16: applicable; This item applies to every dataset


Applicability for Q17: unknown; shared_dataset: not declared; retained in the denominator


Applicability for Q18: applicable; This item applies to every dataset


Applicability for Q19: applicable; This item applies to every dataset


Applicability for Q20: applicable; This item applies to every dataset
