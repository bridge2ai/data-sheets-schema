# Detailed Evaluation: CHORUS - CLAUDECODE_RELEASE_CORE

Evaluated: 2026-11-25T19:12:28.515564
File: `data/d4d_concatenated/claudecode_release_core/2026-11-25c_claude-fable-5-2-claudecode-generic-v9_rep2/CHORUS_d4d_core.yaml`

Instrument: `b38117d96e73987f236d4d3d47da5b84a952401537f9a2ae4d2c44bf981fc064`
Applicability context: `fca403729b83dda36a67c4b749455b0fd864ba992e0e40b9a0f5c65bc039bfad`
Scope: single_dataset
## Overall Scores

- **Rubric10**: 27.0/50 (54.0%)
- **Rubric20**: 54.0/88 (61.4%)

## Rubric10 Element Scores

| ID | Element | Score | Details |
|----|---------|-------|---------|
| 1 | Dataset Discovery and Identification | 4/5 | 4/5 applicable sub-elements present; 0 N/A |
| 2 | Dataset Access and Retrieval | 3/5 | 3/5 applicable sub-elements present; 0 N/A |
| 3 | Data Reuse and Interoperability | 3/5 | 3/5 applicable sub-elements present; 0 N/A |
| 4 | Ethical Use and Privacy Safeguards | 1/5 | 1/5 applicable sub-elements present; 0 N/A |
| 5 | Data Composition and Structure | 3/5 | 3/5 applicable sub-elements present; 0 N/A |
| 6 | Data Provenance and Version Tracking | 3/5 | 3/5 applicable sub-elements present; 0 N/A |
| 7 | Scientific Motivation and Funding Transparency | 5/5 | 5/5 applicable sub-elements present; 0 N/A |
| 8 | Technical Transparency (Data Collection and Processing) | 3/5 | 3/5 applicable sub-elements present; 0 N/A |
| 9 | Dataset Evaluation and Limitations Disclosure | 0/5 | 0/5 applicable sub-elements present; 0 N/A |
| 10 | Cross-Platform and Community Integration | 2/5 | 2/5 applicable sub-elements present; 0 N/A |

### Rubric10 Sub-Element Details


#### 1. Dataset Discovery and Identification

Can a user or system discover and uniquely identify this dataset?

- ✅ **Persistent Identifier (DOI, RRID, or URI)**
  - Applicability: applicable; This item applies to every dataset
  - Found: #/id: https://chorus4ai.org/
- ✅ **Dataset Title and Description Completeness**
  - Applicability: applicable; This item applies to every dataset
  - Found: #/title: CHoRUS Dataset
  - Found: #/description: The CHoRUS dataset is the multicenter, multimodal and high-resolution clinical care dataset of the C
- ✅ **Keywords or Tags for Searchability**
  - Applicability: applicable; This item applies to every dataset
  - Found: #/keywords/0: Critical Care
  - Found: #/keywords/1: Critical Illness
  - Found: #/keywords/2: Artificial Intelligence
  - Found: #/keywords/3: Bridge to Artificial Intelligence
  - Found: #/keywords/4: Machine Learning
  - Found: #/keywords/5: Electronic Health Record
  - Found: #/keywords/6: Electroencephalography
  - Found: #/keywords/7: Telemetry
  - Found: #/keywords/8: acute care
  - Found: #/keywords/9: data standards
  - Found: #/keywords/10: multimodality
  - Found: #/keywords/11: social health determinants
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
  - Found: #/license_and_use_terms: {'license_terms': 'Controlled access. The September 2025 webinar states that all participants in the
- ❌ **Regulatory Compliance and Confidentiality Classification**
  - Applicability: unknown; regulated_access: not declared; retained in the denominator
  - Fields checked: regulatory_restrictions, confidentiality_level, hipaa_compliant, other_compliance, governance_committee_contact
- ❌ **Download URL or Platform Link Available**
  - Applicability: applicable; This item applies to every dataset
  - Fields checked: download_url
- ✅ **Distribution Formats and File Types Specified**
  - Applicability: applicable; This item applies to every dataset
  - Found: #/distribution_formats/0: {'description': 'The data are held in a cloud enclave. The September 2025 webinar states that OMOP a
- ✅ **Related Datasets and External Resources Linked**
  - Applicability: applicable; This item applies to every dataset
  - Found: #/external_resources/0: {'name': 'CHoRUS for Equitable AI GitHub organization (chorus-ai)', 'external_resources': ['https://
  - Found: #/external_resources/1: {'name': 'Bridge2AI CHoRUS web page', 'external_resources': ['www.bridge2ai.org/chorus']}

#### 3. Data Reuse and Interoperability

Is sufficient information provided to reuse and integrate the dataset with others?
Note: Evaluate whether the dataset is designed for integration with similar datasets, including: common identifiers for cross-dataset linking, standardized formats for data harmonization, and documented integration procedures.


- ✅ **License Terms Allow Reuse**
  - Applicability: unknown; shared_dataset: not declared; retained in the denominator
  - Found: #/license_and_use_terms: {'license_terms': 'Controlled access. The September 2025 webinar states that all participants in the
- ❌ **Data Formats Are Standardized (encoding, format)**
  - Applicability: unknown; shared_dataset: not declared; retained in the denominator
  - Fields checked: format, encoding
- ✅ **Schema or Ontology Conformance Stated**
  - Applicability: unknown; shared_dataset: not declared; retained in the denominator
  - Found: #/conforms_to: OMOP; DICOM; WFDB; OHNLP; EDF+ and Persyst (for waveform EEG, whose extraction was in process at the
  - Found: #/conforms_to_schema: src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml
- ❌ **Variable Metadata with Identifiers Defined**
  - Applicability: unknown; shared_dataset: not declared; retained in the denominator
  - Fields checked: variables
- ✅ **Use Guidance Provided (intended, prohibited uses)**
  - Applicability: applicable; This item applies to every dataset
  - Found: #/intended_uses/0: {'description': 'Building machine-learning (ML) and artificial intelligence (AI)-derived models to i

#### 4. Ethical Use and Privacy Safeguards

Does the dataset document the ethical oversight, privacy, consent and safeguards that apply to its subjects and governance context? Equivalent local ethics and regulatory frameworks are accepted; HIPAA or an IRB is not a universal requirement.

- ❌ **IRB or Ethics Review and Data Protection Impact**
  - Applicability: unknown; any: human_subjects: not declared; retained in the denominator; regulated_access: not declared; retained in the denominator
  - Fields checked: ethical_reviews, human_subject_research, data_protection_impacts
- ✅ **Deidentification Method Described**
  - Applicability: unknown; any: human_subjects: not declared; retained in the denominator; regulated_access: not declared; retained in the denominator
  - Found: #/is_deidentified: {'deidentification_details': 'The 2022 NIH project abstract states that the project will transform d
- ❌ **Privacy Protections and Re-identification Risk Assessment**
  - Applicability: unknown; human_subjects: not declared; retained in the denominator
  - Fields checked: participant_privacy, reidentification_risk
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
  - Found: #/instances/0: {'instance_type': 'Patient admissions', 'counts': 50000, 'description': "The project website's snaps
  - Found: #/instances/1: {'instance_type': 'Demographics', 'description': 'Data standard listed in the webinar table is OMOP.
  - Found: #/instances/2: {'instance_type': 'Medication administration', 'description': 'Dosing time-stamped upon each infusio
  - Found: #/instances/3: {'instance_type': 'Procedures', 'description': 'Documentation by providers.'}
  - Found: #/instances/4: {'instance_type': 'Nursing flowsheets', 'description': 'High-frequency documentation.'}
  - Found: #/instances/5: {'instance_type': 'Diagnoses', 'description': 'Documentation by providers.'}
  - Found: #/instances/6: {'instance_type': 'Clinical notes', 'description': 'Extracted and tokenized using the OHNLP toolkit.
  - Found: #/instances/7: {'instance_type': 'Imaging', 'description': 'Imaging from PACS, with DICOM listed as the data standa
  - Found: #/instances/8: {'instance_type': 'Waveform telemetry', 'description': 'Waveform telemetry from bedside monitors and
  - Found: #/instances/9: {'instance_type': 'Waveform EEG', 'description': 'Waveform EEG from a hospital database, with EDF+ a
- ❌ **Variable-Level Metadata, Tabular Flag, and Data Splits**
  - Applicability: applicable; This item applies to every dataset
  - Fields checked: variables, is_tabular, is_data_split, is_subpopulation
- ✅ **Data Topics or Conditions Represented**
  - Applicability: applicable; This item applies to every dataset
  - Found: #/instances/0: {'instance_type': 'Patient admissions', 'counts': 50000, 'description': "The project website's snaps
  - Found: #/instances/1: {'instance_type': 'Demographics', 'description': 'Data standard listed in the webinar table is OMOP.
  - Found: #/instances/2: {'instance_type': 'Medication administration', 'description': 'Dosing time-stamped upon each infusio
  - Found: #/instances/3: {'instance_type': 'Procedures', 'description': 'Documentation by providers.'}
  - Found: #/instances/4: {'instance_type': 'Nursing flowsheets', 'description': 'High-frequency documentation.'}
  - Found: #/instances/5: {'instance_type': 'Diagnoses', 'description': 'Documentation by providers.'}
  - Found: #/instances/6: {'instance_type': 'Clinical notes', 'description': 'Extracted and tokenized using the OHNLP toolkit.
  - Found: #/instances/7: {'instance_type': 'Imaging', 'description': 'Imaging from PACS, with DICOM listed as the data standa
  - Found: #/instances/8: {'instance_type': 'Waveform telemetry', 'description': 'Waveform telemetry from bedside monitors and
  - Found: #/instances/9: {'instance_type': 'Waveform EEG', 'description': 'Waveform EEG from a hospital database, with EDF+ a
- ✅ **Data Quality, Anomalies, and Missing Data Documented**
  - Applicability: applicable; This item applies to every dataset
  - Found: #/sampling_strategies/0: {'strategies': 'Planned, not reported as applied: the 2022 NIH project abstract states the project w

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
  - Found: #/updates: {'update_details': 'The project website contrasts its current released dataset with an "Anticipated 
- ✅ **Update Schedule or Frequency Indicated**
  - Applicability: unknown; shared_dataset: not declared; retained in the denominator
  - Found: #/updates: {'update_details': 'The project website contrasts its current released dataset with an "Anticipated 
- ✅ **Provenance, Source Derivation, and Raw Data Sources**
  - Applicability: unknown; shared_dataset: not declared; retained in the denominator
  - Found: #/raw_data_sources/0: {'name': 'PACS', 'source_description': 'Imaging is drawn from PACS.'}
  - Found: #/raw_data_sources/1: {'name': 'Bedside monitors and gateway/middleware', 'source_description': 'Waveform telemetry is dra
  - Found: #/raw_data_sources/2: {'name': 'Hospital database', 'source_description': 'Waveform EEG is drawn from a hospital database.

#### 7. Scientific Motivation and Funding Transparency

Does the metadata clearly state why the dataset exists and who funded it?

- ✅ **Motivation or Purpose for Dataset Creation**
  - Applicability: applicable; This item applies to every dataset
  - Found: #/purposes/0: {'name': 'Publicly available, AI-ready critical care dataset', 'response': "The 2022 NIH project abs
  - Found: #/purposes/1: {'name': 'Improving recovery from acute illness', 'response': 'The GitHub organization overview stat
- ✅ **Primary Research Objectives or Tasks**
  - Applicability: applicable; This item applies to every dataset
  - Found: #/tasks/0: {'name': 'Characterizing acute and critical care illness', 'response': 'ML/AI applications aimed at 
  - Found: #/tasks/1: {'name': 'Predicting complications', 'response': 'ML/AI applications aimed at predicting complicatio
  - Found: #/tasks/2: {'name': 'Measuring treatment response', 'response': 'ML/AI applications aimed at measuring treatmen
- ✅ **Funding Sources and Mechanisms Listed**
  - Applicability: applicable; This item applies to every dataset
  - Found: #/funders/0: {'grantor': 'NIH', 'grants': [{'name': 'Bridge2AI: Patient-Focused Collaborative Hospital Repository
- ✅ **Grant IDs or Award Numbers Present**
  - Applicability: applicable; This item applies to every dataset
  - Found: #/funders/0: {'grantor': 'NIH', 'grants': [{'name': 'Bridge2AI: Patient-Focused Collaborative Hospital Repository
- ✅ **Creators and Acknowledgements Documented**
  - Applicability: applicable; This item applies to every dataset
  - Found: #/creators/0: {'principal_investigator': {'id': 'https://chorus4ai.org/#person-eric-s-rosenthal', 'name': 'Eric S.
  - Found: #/creators/1: {'name': 'Azra Bihorac', 'affiliations': [{'name': 'University of Florida'}], 'description': 'Listed
  - Found: #/creators/2: {'name': 'Xiaoqian Jiang', 'affiliations': [{'name': 'UTHealth Houston'}], 'description': 'Listed on
  - Found: #/creators/3: {'name': 'Yulia Strekalova', 'affiliations': [{'name': 'University of Florida'}], 'description': 'Li
  - Found: #/creators/4: {'name': 'Parisa Rashidi', 'affiliations': [{'name': 'University of Florida'}], 'description': 'List
  - Found: #/creators/5: {'name': 'Manlik Kwong', 'affiliations': [{'name': 'Tufts University'}], 'description': 'Listed on t
  - Found: #/funders/0: {'grantor': 'NIH', 'grants': [{'name': 'Bridge2AI: Patient-Focused Collaborative Hospital Repository

#### 8. Technical Transparency (Data Collection and Processing)

Can data collection and processing steps be replicated or understood?
Note: Preprocessing and collection metadata may be represented as structured text descriptions OR as machine-readable provenance graphs (e.g., W3C PROV-O, workflow graphs). Evaluation should check for: (1) structured text descriptions OR (2) graph representations with entity-activity-agent relationships. Both formats are acceptable.


- ✅ **Collection Mechanisms and Settings Described**
  - Applicability: unknown; data_collection: not declared; retained in the denominator
  - Found: #/collection_mechanisms/0: {'name': 'Retrospective data collection', 'mechanism_details': 'The September 2025 webinar describes
- ❌ **Data Acquisition Methods Listed**
  - Applicability: unknown; data_collection: not declared; retained in the denominator
  - Fields checked: acquisition_methods
- ✅ **Preprocessing, Cleaning, Labeling, and Annotation Quality**
  - Applicability: unknown; data_processing: not declared; retained in the denominator
  - Found: #/preprocessing_strategies/0: {'name': 'Standardization to common standards', 'preprocessing_details': "The 2022 NIH project abstr
  - Found: #/preprocessing_strategies/1: {'name': 'Semantic mapping', 'preprocessing_details': 'The GitHub organization overview describes a 
  - Found: #/preprocessing_strategies/2: {'name': 'Clinical note tokenization', 'preprocessing_details': 'Clinical notes are extracted and to
  - Found: #/labeling_strategies/0: {'labeling_details': 'Planned, not reported as applied: the GitHub organization overview states that
- ❌ **Software and Tools Documented**
  - Applicability: unknown; processing_software: not declared; retained in the denominator
  - Fields checked: software_and_tools
- ✅ **External Standards, Resources, and Imputation Protocols**
  - Applicability: applicable; This item applies to every dataset
  - Found: #/external_resources/0: {'name': 'CHoRUS for Equitable AI GitHub organization (chorus-ai)', 'external_resources': ['https://
  - Found: #/external_resources/1: {'name': 'Bridge2AI CHoRUS web page', 'external_resources': ['www.bridge2ai.org/chorus']}
  - Found: #/conforms_to: OMOP; DICOM; WFDB; OHNLP; EDF+ and Persyst (for waveform EEG, whose extraction was in process at the

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
- ✅ **Community Standards or Schema Conformance**
  - Applicability: unknown; shared_dataset: not declared; retained in the denominator
  - Found: #/conforms_to: OMOP; DICOM; WFDB; OHNLP; EDF+ and Persyst (for waveform EEG, whose extraction was in process at the
- ✅ **Outreach Materials and Documentation Links**
  - Applicability: unknown; shared_dataset: not declared; retained in the denominator
  - Found: #/external_resources/0: {'name': 'CHoRUS for Equitable AI GitHub organization (chorus-ai)', 'external_resources': ['https://
  - Found: #/external_resources/1: {'name': 'Bridge2AI CHoRUS web page', 'external_resources': ['www.bridge2ai.org/chorus']}
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
| 3 | Keyword Diversity | 5.0/5 | ✅ |
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
