# Detailed Evaluation: AI_READI - CLAUDECODE_RELEASE_CORE

Evaluated: 2026-11-25T19:12:18.348808
File: `data/d4d_concatenated/claudecode_release_core/2026-11-25c_claude-fable-5-2-claudecode-generic-v9_rep1/AI_READI_d4d_core.yaml`

Instrument: `b38117d96e73987f236d4d3d47da5b84a952401537f9a2ae4d2c44bf981fc064`
Applicability context: `fca403729b83dda36a67c4b749455b0fd864ba992e0e40b9a0f5c65bc039bfad`
Scope: single_dataset
## Overall Scores

- **Rubric10**: 42.0/50 (84.0%)
- **Rubric20**: 64.0/88 (72.7%)

## Rubric10 Element Scores

| ID | Element | Score | Details |
|----|---------|-------|---------|
| 1 | Dataset Discovery and Identification | 4/5 | 4/5 applicable sub-elements present; 0 N/A |
| 2 | Dataset Access and Retrieval | 4/5 | 4/5 applicable sub-elements present; 0 N/A |
| 3 | Data Reuse and Interoperability | 4/5 | 4/5 applicable sub-elements present; 0 N/A |
| 4 | Ethical Use and Privacy Safeguards | 3/5 | 3/5 applicable sub-elements present; 0 N/A |
| 5 | Data Composition and Structure | 4/5 | 4/5 applicable sub-elements present; 0 N/A |
| 6 | Data Provenance and Version Tracking | 5/5 | 5/5 applicable sub-elements present; 0 N/A |
| 7 | Scientific Motivation and Funding Transparency | 5/5 | 5/5 applicable sub-elements present; 0 N/A |
| 8 | Technical Transparency (Data Collection and Processing) | 4/5 | 4/5 applicable sub-elements present; 0 N/A |
| 9 | Dataset Evaluation and Limitations Disclosure | 5/5 | 5/5 applicable sub-elements present; 0 N/A |
| 10 | Cross-Platform and Community Integration | 4/5 | 4/5 applicable sub-elements present; 0 N/A |

### Rubric10 Sub-Element Details


#### 1. Dataset Discovery and Identification

Can a user or system discover and uniquely identify this dataset?

- ✅ **Persistent Identifier (DOI, RRID, or URI)**
  - Applicability: applicable; This item applies to every dataset
  - Found: #/doi: 10.60775/fairhub.3
  - Found: #/id: doi:10.60775/fairhub.3
- ✅ **Dataset Title and Description Completeness**
  - Applicability: applicable; This item applies to every dataset
  - Found: #/title: Flagship Dataset of Type 2 Diabetes from the AI-READI Project
  - Found: #/description: Version 3.0.0 of the AI-READI dataset, the public release distributed through the FAIRhub platform. 
- ✅ **Keywords or Tags for Searchability**
  - Applicability: applicable; This item applies to every dataset
  - Found: #/keywords/0: Diabetes mellitus
  - Found: #/keywords/1: Machine Learning
  - Found: #/keywords/2: Artificial Intelligence
  - Found: #/keywords/3: Electrocardiography
  - Found: #/keywords/4: Continuous Glucose Monitoring
  - Found: #/keywords/5: Retinal imaging
  - Found: #/keywords/6: Eye exam
- ✅ **Landing Page and Resources (page, hierarchical resources)**
  - Applicability: applicable; This item applies to every dataset
  - Found: #/page: https://fairhub.io/datasets/3
- ❌ **Hierarchical Structure (parent datasets, relationships)**
  - Applicability: applicable; This item applies to every dataset
  - Fields checked: parent_datasets, related_datasets

#### 2. Dataset Access and Retrieval

Can the dataset and its associated resources be located, accessed, and downloaded?

- ✅ **Access Policy and IP Restrictions Defined**
  - Applicability: applicable; This item applies to every dataset
  - Found: #/license_and_use_terms: {'description': 'The FAIRhub metadata give the access type as "PublicDownloadSelfAttestationRequired
  - Found: #/ip_restrictions: {'restrictions': ['Title to the data, and all industrial and intellectual property rights therein, r
- ✅ **Regulatory Compliance and Confidentiality Classification**
  - Applicability: unknown; regulated_access: not declared; retained in the denominator
  - Found: #/regulatory_restrictions: {'regulatory_restrictions': ['The licensee agrees to comply with all data security and privacy stand
- ❌ **Download URL or Platform Link Available**
  - Applicability: applicable; This item applies to every dataset
  - Fields checked: download_url
- ✅ **Distribution Formats and File Types Specified**
  - Applicability: applicable; This item applies to every dataset
  - Found: #/distribution_formats/0: {'media_type': 'application/dicom'}
  - Found: #/distribution_formats/1: {'media_type': 'text/markdown'}
  - Found: #/distribution_formats/2: {'media_type': 'text/csv'}
  - Found: #/distribution_formats/3: {'media_type': 'application/json'}
  - Found: #/distributions/10: {'format': 'MD', 'id': 'doi:10.60775/fairhub.3#CHANGELOG.md', 'media_type': 'text/markdown', 'name':
  - Found: #/distributions/11: {'format': 'JSON', 'id': 'doi:10.60775/fairhub.3#dataset_description.json', 'media_type': 'applicati
  - Found: #/distributions/12: {'format': 'JSON', 'id': 'doi:10.60775/fairhub.3#dataset_structure_description.json', 'media_type': 
  - Found: #/distributions/13: {'format': 'MD', 'id': 'doi:10.60775/fairhub.3#healthsheet.md', 'media_type': 'text/markdown', 'name
  - Found: #/distributions/14: {'format': 'TXT', 'id': 'doi:10.60775/fairhub.3#LICENSE.txt', 'media_type': 'text/plain', 'name': 'L
  - Found: #/distributions/15: {'format': 'JSON', 'id': 'doi:10.60775/fairhub.3#participants.json', 'media_type': 'application/json
  - Found: #/distributions/16: {'format': 'TSV', 'id': 'doi:10.60775/fairhub.3#participants.tsv', 'media_type': 'text/tab-separated
  - Found: #/distributions/17: {'format': 'MD', 'id': 'doi:10.60775/fairhub.3#README.md', 'media_type': 'text/markdown', 'name': 'R
  - Found: #/distributions/18: {'format': 'JSON', 'id': 'doi:10.60775/fairhub.3#study_description.json', 'media_type': 'application
  - Found: #/distributions/10/format: MD
  - Found: #/distributions/11/format: JSON
  - Found: #/distributions/12/format: JSON
  - Found: #/distributions/13/format: MD
  - Found: #/distributions/14/format: TXT
  - Found: #/distributions/15/format: JSON
  - Found: #/distributions/16/format: TSV
  - Found: #/distributions/17/format: MD
  - Found: #/distributions/18/format: JSON
  - Found: #/distributions/10/media_type: text/markdown
  - Found: #/distributions/11/media_type: application/json
  - Found: #/distributions/12/media_type: application/json
  - Found: #/distributions/13/media_type: text/markdown
  - Found: #/distributions/14/media_type: text/plain
  - Found: #/distributions/15/media_type: application/json
  - Found: #/distributions/16/media_type: text/tab-separated-values
  - Found: #/distributions/17/media_type: text/markdown
  - Found: #/distributions/18/media_type: application/json
  - Found: #/distribution_formats/0/media_type: application/dicom
  - Found: #/distribution_formats/1/media_type: text/markdown
  - Found: #/distribution_formats/2/media_type: text/csv
  - Found: #/distribution_formats/3/media_type: application/json
- ✅ **Related Datasets and External Resources Linked**
  - Applicability: applicable; This item applies to every dataset
  - Found: #/external_resources/0: {'name': 'AI-READI dataset documentation', 'external_resources': ['https://docs.aireadi.org/'], 'res
  - Found: #/external_resources/1: {'name': 'AI-READI project website', 'external_resources': ['https://aireadi.org/']}
  - Found: #/external_resources/2: {'name': 'License terms for the AI-READI dataset', 'external_resources': ['https://doi.org/10.5281/z
  - Found: #/external_resources/3: {'name': 'Zenodo community of the AI-READI project', 'external_resources': ['https://zenodo.org/comm
  - Found: #/external_resources/4: {'name': 'GitHub organization of the AI-READI project', 'external_resources': ['https://github.com/A
  - Found: #/external_resources/5: {'name': 'Clinical Dataset Structure (CDS) v0.1.1 specification', 'external_resources': ['https://cd
  - Found: #/external_resources/6: {'name': 'Protocol publication', 'external_resources': ['Owsley C, et al. Cross-sectional design and
  - Found: #/external_resources/7: {'name': 'Project overview publication', 'external_resources': ['AI-READI Consortium. AI-READI: reth

#### 3. Data Reuse and Interoperability

Is sufficient information provided to reuse and integrate the dataset with others?
Note: Evaluate whether the dataset is designed for integration with similar datasets, including: common identifiers for cross-dataset linking, standardized formats for data harmonization, and documented integration procedures.


- ✅ **License Terms Allow Reuse**
  - Applicability: unknown; shared_dataset: not declared; retained in the denominator
  - Found: #/license_and_use_terms: {'description': 'The FAIRhub metadata give the access type as "PublicDownloadSelfAttestationRequired
- ✅ **Data Formats Are Standardized (encoding, format)**
  - Applicability: unknown; shared_dataset: not declared; retained in the denominator
  - Found: #/distributions/10/format: MD
  - Found: #/distributions/11/format: JSON
  - Found: #/distributions/12/format: JSON
  - Found: #/distributions/13/format: MD
  - Found: #/distributions/14/format: TXT
  - Found: #/distributions/15/format: JSON
  - Found: #/distributions/16/format: TSV
  - Found: #/distributions/17/format: MD
  - Found: #/distributions/18/format: JSON
- ✅ **Schema or Ontology Conformance Stated**
  - Applicability: unknown; shared_dataset: not declared; retained in the denominator
  - Found: #/conforms_to: Clinical Dataset Structure (CDS) v0.1.1
  - Found: #/distributions/0/conforms_to: WaveForm DataBase (WFDB)
  - Found: #/distributions/1/conforms_to: The Observational Medical Outcomes Partnership (OMOP) Common Data Model (CDM)
  - Found: #/distributions/2/conforms_to: ASCII File Format Guidelines for Earth Science Data
  - Found: #/distributions/3/conforms_to: Digital Imaging and Communications in Medicine (DICOM)
  - Found: #/distributions/4/conforms_to: Digital Imaging and Communications in Medicine (DICOM)
  - Found: #/distributions/5/conforms_to: Digital Imaging and Communications in Medicine (DICOM)
  - Found: #/distributions/6/conforms_to: Digital Imaging and Communications in Medicine (DICOM)
  - Found: #/distributions/7/conforms_to: Open mHealth
  - Found: #/distributions/8/conforms_to: Open mHealth
  - Found: #/distributions/0/conforms_to_standard/0: WFDB
  - Found: #/distributions/1/conforms_to_standard/0: OMOP_CDM
  - Found: #/distributions/2/conforms_to_standard/0: ESDS
  - Found: #/distributions/3/conforms_to_standard/0: DICOM
  - Found: #/distributions/4/conforms_to_standard/0: DICOM
  - Found: #/distributions/5/conforms_to_standard/0: DICOM
  - Found: #/distributions/6/conforms_to_standard/0: DICOM
  - Found: #/distributions/7/conforms_to_standard/0: OPEN_MHEALTH
  - Found: #/distributions/8/conforms_to_standard/0: OPEN_MHEALTH
  - Found: #/conforms_to_schema: src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml
- ❌ **Variable Metadata with Identifiers Defined**
  - Applicability: unknown; shared_dataset: not declared; retained in the denominator
  - Fields checked: variables
- ✅ **Use Guidance Provided (intended, prohibited uses)**
  - Applicability: applicable; This item applies to every dataset
  - Found: #/intended_uses/0: {'use_category': 'Type 2 diabetes related research', 'usage_notes': 'Access requires agreeing to use
  - Found: #/intended_uses/1: {'use_category': 'Development of AI/ML models', 'usage_notes': 'The license permits the licensee to 
  - Found: #/prohibited_uses/0: {'name': 'Clinical treatment decisions', 'description': 'The licensee shall not make clinical treatm
  - Found: #/prohibited_uses/1: {'name': 'Identification of or harm to data subjects', 'description': "The licensee shall not use or
  - Found: #/prohibited_uses/2: {'name': 'Sharing data with third-party model vendors for training', 'description': "The licensee sh
  - Found: #/prohibited_uses/3: {'name': 'Reproducing data in publications', 'description': 'Data may not be reproduced in papers, a

#### 4. Ethical Use and Privacy Safeguards

Does the dataset document the ethical oversight, privacy, consent and safeguards that apply to its subjects and governance context? Equivalent local ethics and regulatory frameworks are accepted; HIPAA or an IRB is not a universal requirement.

- ✅ **IRB or Ethics Review and Data Protection Impact**
  - Applicability: unknown; any: human_subjects: not declared; retained in the denominator; regulated_access: not declared; retained in the denominator
  - Found: #/ethical_reviews/0: {'reviewing_organization': 'Institutional Review Board of the University of Washington', 'review_det
  - Found: #/human_subject_research: {'involves_human_subjects': True, 'ethics_review_board': 'Institutional Review Board of the Universi
- ✅ **Deidentification Method Described**
  - Applicability: unknown; any: human_subjects: not declared; retained in the denominator; regulated_access: not declared; retained in the denominator
  - Found: #/is_deidentified: {'identifiable_elements_present': False, 'deidentification_details': 'The FAIRhub metadata state tha
- ❌ **Privacy Protections and Re-identification Risk Assessment**
  - Applicability: unknown; human_subjects: not declared; retained in the denominator
  - Fields checked: participant_privacy, reidentification_risk
- ✅ **Informed Consent Obtained from Participants**
  - Applicability: unknown; human_subjects: not declared; retained in the denominator
  - Found: #/informed_consent/0: {'consent_obtained': True, 'consent_type': 'Written informed consent, given electronically (e-consen
- ❌ **Vulnerable Populations and Compensation Documented**
  - Applicability: unknown; human_subjects: not declared; retained in the denominator
  - Fields checked: vulnerable_populations, participant_compensation

#### 5. Data Composition and Structure

Can the dataset's structure, modality, and population be understood from metadata?

- ✅ **Cohort or Subpopulations Characteristics Described**
  - Applicability: applicable; This item applies to every dataset
  - Found: #/subpopulations/0: {'name': 'Demographic subpopulations', 'subpopulation_elements_present': False, 'identification': 'T
  - Found: #/subpopulations/1: {'name': 'Diabetes status study groups', 'identification': 'Four study groups: Healthy (participants
- ✅ **Number of Instances or Samples Reported**
  - Applicability: applicable; This item applies to every dataset
  - Found: #/instances/0: {'instance_type': 'individual patient (study participant)', 'counts': 2280, 'label': False, 'descrip
- ❌ **Variable-Level Metadata, Tabular Flag, and Data Splits**
  - Applicability: applicable; This item applies to every dataset
  - Fields checked: variables, is_tabular, is_data_split, is_subpopulation
- ✅ **Data Topics or Conditions Represented**
  - Applicability: applicable; This item applies to every dataset
  - Found: #/instances/0: {'instance_type': 'individual patient (study participant)', 'counts': 2280, 'label': False, 'descrip
- ✅ **Data Quality, Anomalies, and Missing Data Documented**
  - Applicability: applicable; This item applies to every dataset
  - Found: #/anomalies/0: {'anomaly_details': 'In survey data, skipped questions or incomplete responses are expected.'}
  - Found: #/anomalies/1: {'anomaly_details': 'In data from wearables, improper use and technical failure such as battery fail
  - Found: #/anomalies/2: {'anomaly_details': 'In imaging data, patient uncooperation, noise that may obscure the images, tech
  - Found: #/sampling_strategies/0: {'name': 'Balanced recruitment design', 'strategies': 'Rather than targeting the demographic distrib
  - Found: #/sampling_strategies/1: {'name': 'Recruitment in waves from screened health records', 'strategies': 'Recruitment pools were 
  - Found: #/sampling_strategies/2: {'name': 'Eligibility criteria', 'strategies': 'Inclusion: able to provide consent; 40 years old or 
  - Found: #/missing_data_documentation/0: {'missing_data_patterns': 'Marijuana use was not assessed for participants living in Alabama.', 'mis

#### 6. Data Provenance and Version Tracking

Can a user determine dataset versions, update history, and provenance?

- ✅ **Dataset Version Number Provided**
  - Applicability: unknown; shared_dataset: not declared; retained in the denominator
  - Found: #/version: 3.0.0
- ✅ **Version Access Methods Documented**
  - Applicability: unknown; shared_dataset: not declared; retained in the denominator
  - Found: #/version_access: {'latest_version_doi': 'doi:10.60775/fairhub.3', 'versions_available': ['3.0.0 (10.60775/fairhub.3, 
- ✅ **Change Descriptions and Errata Provided**
  - Applicability: unknown; shared_dataset: not declared; retained in the denominator
  - Found: #/updates: {'frequency': 'There are plans to release new versions of the dataset approximately once a year.', '
- ✅ **Update Schedule or Frequency Indicated**
  - Applicability: unknown; shared_dataset: not declared; retained in the denominator
  - Found: #/updates: {'frequency': 'There are plans to release new versions of the dataset approximately once a year.', '
- ✅ **Provenance, Source Derivation, and Raw Data Sources**
  - Applicability: unknown; shared_dataset: not declared; retained in the denominator
  - Found: #/raw_data_sources/0: {'source_description': 'Electrocardiogram recordings exported from the ECG device to local storage i
  - Found: #/raw_data_sources/1: {'source_description': 'MoCA Duo application exports (total score, section subscores, Memory Index S

#### 7. Scientific Motivation and Funding Transparency

Does the metadata clearly state why the dataset exists and who funded it?

- ✅ **Motivation or Purpose for Dataset Creation**
  - Applicability: applicable; This item applies to every dataset
  - Found: #/purposes/0: {'response': 'The dataset was created to enable future generations of artificial intelligence/machin
  - Found: #/purposes/1: {'response': 'The AI-READI project also aims to establish standards, best practices and guidelines f
- ✅ **Primary Research Objectives or Tasks**
  - Applicability: applicable; This item applies to every dataset
  - Found: #/tasks/0: {'response': 'The multi-modal dataset is being gathered to facilitate downstream pseudotime manifold
- ✅ **Funding Sources and Mechanisms Listed**
  - Applicability: applicable; This item applies to every dataset
  - Found: #/funders/0: {'grantor': 'National Institutes of Health', 'description': 'The healthsheet states that the creatio
  - Found: #/funders/1: {'grantor': 'Research to Prevent Blindness', 'source_caveats': 'Named only in the funding statement 
- ✅ **Grant IDs or Award Numbers Present**
  - Applicability: applicable; This item applies to every dataset
  - Found: #/funders/0: {'grantor': 'National Institutes of Health', 'description': 'The healthsheet states that the creatio
  - Found: #/funders/1: {'grantor': 'Research to Prevent Blindness', 'source_caveats': 'Named only in the funding statement 
- ✅ **Creators and Acknowledgements Documented**
  - Applicability: applicable; This item applies to every dataset
  - Found: #/creators/0: {'name': 'AI-READI Consortium', 'description': 'Organizational creator named in the FAIRhub metadata
  - Found: #/creators/1: {'id': 'ORCID:0000-0003-1994-7213', 'name': 'Cecilia Lee', 'principal_investigator': {'id': 'ORCID:0
  - Found: #/creators/2: {'id': 'ORCID:0000-0003-4533-9334', 'name': 'Amir Bahmani', 'principal_investigator': {'id': 'ORCID:
  - Found: #/creators/3: {'id': 'ORCID:0000-0002-5271-7690', 'name': 'Sally L. Baxter', 'principal_investigator': {'id': 'ORC
  - Found: #/creators/4: {'id': 'ORCID:0000-0001-5437-2545', 'name': 'Christopher G. Chute', 'principal_investigator': {'id':
  - Found: #/creators/5: {'id': 'ORCID:0000-0002-7899-3060', 'name': 'Jorge Contreras', 'principal_investigator': {'id': 'ORC
  - Found: #/creators/6: {'id': 'ORCID:0000-0002-3330-0224', 'name': 'Nicholas Evans', 'principal_investigator': {'id': 'ORCI
  - Found: #/creators/7: {'id': 'ORCID:0000-0001-9843-2845', 'name': 'Samantha Hurst', 'principal_investigator': {'id': 'ORCI
  - Found: #/creators/8: {'id': 'ORCID:0000-0003-2957-0755', 'name': 'T. Y. Alvin Liu', 'principal_investigator': {'id': 'ORC
  - Found: #/creators/9: {'id': 'ORCID:0000-0001-9592-1133', 'name': 'Gerald McGwin', 'principal_investigator': {'id': 'ORCID
  - Found: #/creators/10: {'id': 'ORCID:0000-0001-8333-6607', 'name': 'Shannon McWeeney', 'principal_investigator': {'id': 'OR
  - Found: #/creators/11: {'id': 'ORCID:0000-0003-3424-011X', 'name': 'Cynthia Owsley', 'principal_investigator': {'id': 'ORCI
  - Found: #/creators/12: {'id': 'ORCID:0000-0002-0307-262X', 'name': 'Bhavesh Patel', 'principal_investigator': {'id': 'ORCID
  - Found: #/creators/13: {'id': 'ORCID:0000-0003-0784-7987', 'name': 'Michael Snyder', 'principal_investigator': {'id': 'ORCI
  - Found: #/creators/14: {'id': 'ORCID:0000-0002-3374-1177', 'name': 'Sara J. Singer', 'principal_investigator': {'id': 'ORCI
  - Found: #/creators/15: {'id': 'ORCID:0000-0002-1143-5224', 'name': 'Linda M. Zangwill', 'principal_investigator': {'id': 'O
  - Found: #/creators/16: {'name': 'Hiroshi Ishikawa', 'principal_investigator': {'id': 'doi:10.60775/fairhub.3#person-hiroshi
  - Found: #/creators/17: {'name': 'Camille Nebeker', 'principal_investigator': {'id': 'doi:10.60775/fairhub.3#person-camille-
  - Found: #/creators/18: {'name': 'Jeffrey C. Edberg', 'principal_investigator': {'id': 'doi:10.60775/fairhub.3#person-jeffre
  - Found: #/creators/19: {'name': 'Kadija Ferryman', 'principal_investigator': {'id': 'doi:10.60775/fairhub.3#person-kadija-f
  - Found: #/funders/0: {'grantor': 'National Institutes of Health', 'description': 'The healthsheet states that the creatio
  - Found: #/funders/1: {'grantor': 'Research to Prevent Blindness', 'source_caveats': 'Named only in the funding statement 

#### 8. Technical Transparency (Data Collection and Processing)

Can data collection and processing steps be replicated or understood?
Note: Preprocessing and collection metadata may be represented as structured text descriptions OR as machine-readable provenance graphs (e.g., W3C PROV-O, workflow graphs). Evaluation should check for: (1) structured text descriptions OR (2) graph representations with entity-activity-agent relationships. Both formats are acceptable.


- ✅ **Collection Mechanisms and Settings Described**
  - Applicability: unknown; data_collection: not declared; retained in the denominator
  - Found: #/collection_mechanisms/0: {'name': 'Questionnaires in REDCap', 'mechanism_details': 'REDCap is used for collecting patient-rep
  - Found: #/collection_mechanisms/1: {'name': '12-lead electrocardiogram', 'mechanism_details': 'A 12-lead ECG is performed with a Philip
  - Found: #/collection_mechanisms/2: {'name': 'Monofilament test', 'mechanism_details': 'Peripheral neuropathy is assessed with the monof
  - Found: #/collection_mechanisms/3: {'name': 'Montreal Cognitive Assessment (MoCA)', 'mechanism_details': 'A general cognitive screener 
  - Found: #/collection_mechanisms/4: {'name': 'Visual acuity testing', 'mechanism_details': 'Photopic letter visual acuity is measured wi
  - Found: #/collection_mechanisms/5: {'name': 'Contrast sensitivity testing', 'mechanism_details': 'Photopic letter contrast sensitivity 
  - Found: #/collection_mechanisms/6: {'name': 'Autorefraction', 'mechanism_details': "Autorefraction data for each eye are obtained using
  - Found: #/collection_mechanisms/7: {'name': 'Blood and urine collection for laboratory testing', 'mechanism_details': 'Non-fasting bloo
  - Found: #/collection_mechanisms/8: {'name': 'Optomed Aurora IQ', 'mechanism_details': 'A handheld fundus camera used to take non-mydria
  - Found: #/collection_mechanisms/9: {'name': 'iCare EIDON', 'mechanism_details': 'A widefield TrueColor confocal fundus imaging system; 
  - Found: #/collection_mechanisms/10: {'name': 'Heidelberg Spectralis HRA', 'mechanism_details': 'An ophthalmic imaging system combining o
  - Found: #/collection_mechanisms/11: {'name': 'Topcon DRI OCT Triton', 'mechanism_details': 'A device from Topcon Healthcare combining sw
  - Found: #/collection_mechanisms/12: {'name': 'Topcon Maestro2', 'mechanism_details': 'A robotic OCT and color fundus camera system from 
  - Found: #/collection_mechanisms/13: {'name': 'Heidelberg FLIO', 'mechanism_details': 'Fluorescence Lifetime Imaging Ophthalmoscopy (FLIO
  - Found: #/collection_mechanisms/14: {'name': 'Zeiss Cirrus 5000 Angioplex', 'mechanism_details': 'A high-definition optical coherence to
  - Found: #/collection_mechanisms/15: {'name': 'Dexcom G6 continuous glucose monitor', 'mechanism_details': 'A continuous glucose monitori
  - Found: #/collection_mechanisms/16: {'name': 'Garmin Vivosmart 5', 'mechanism_details': 'A wrist-worn fitness activity tracker used for 
  - Found: #/collection_mechanisms/17: {'name': 'LeeLab Anura environmental sensor', 'mechanism_details': "A custom-designed environmental 
  - Found: #/collection_mechanisms/18: {'name': 'Blood pressure measurement', 'mechanism_details': 'Systolic and diastolic blood pressure a
  - Found: #/collection_mechanisms/19: {'name': 'Lensometry', 'mechanism_details': 'Lensometer devices used across the data acquisition sit
- ✅ **Data Acquisition Methods Listed**
  - Applicability: unknown; data_collection: not declared; retained in the denominator
  - Found: #/acquisition_methods/0: {'acquisition_details': 'The acquisition of data varied by domain; some data were directly observabl
- ✅ **Preprocessing, Cleaning, Labeling, and Annotation Quality**
  - Applicability: unknown; data_processing: not declared; retained in the denominator
  - Found: #/preprocessing_strategies/0: {'preprocessing_details': 'All participant images are exported from imaging devices in their raw for
  - Found: #/preprocessing_strategies/1: {'preprocessing_details': 'Once data were sent from each of the study sites to the central project t
  - Found: #/cleaning_strategies/0: {'cleaning_details': 'The Data Manager at each data site is responsible for the quality control of a
  - Found: #/cleaning_strategies/1: {'cleaning_details': "Quality control at the time of data entry and acquisition: clinical data outsi
  - Found: #/cleaning_strategies/2: {'cleaning_details': 'The dataset has not undergone any formal external audits; it has been reviewed
- ❌ **Software and Tools Documented**
  - Applicability: unknown; processing_software: not declared; retained in the denominator
  - Fields checked: software_and_tools
- ✅ **External Standards, Resources, and Imputation Protocols**
  - Applicability: applicable; This item applies to every dataset
  - Found: #/external_resources/0: {'name': 'AI-READI dataset documentation', 'external_resources': ['https://docs.aireadi.org/'], 'res
  - Found: #/external_resources/1: {'name': 'AI-READI project website', 'external_resources': ['https://aireadi.org/']}
  - Found: #/external_resources/2: {'name': 'License terms for the AI-READI dataset', 'external_resources': ['https://doi.org/10.5281/z
  - Found: #/external_resources/3: {'name': 'Zenodo community of the AI-READI project', 'external_resources': ['https://zenodo.org/comm
  - Found: #/external_resources/4: {'name': 'GitHub organization of the AI-READI project', 'external_resources': ['https://github.com/A
  - Found: #/external_resources/5: {'name': 'Clinical Dataset Structure (CDS) v0.1.1 specification', 'external_resources': ['https://cd
  - Found: #/external_resources/6: {'name': 'Protocol publication', 'external_resources': ['Owsley C, et al. Cross-sectional design and
  - Found: #/external_resources/7: {'name': 'Project overview publication', 'external_resources': ['AI-READI Consortium. AI-READI: reth
  - Found: #/conforms_to: Clinical Dataset Structure (CDS) v0.1.1
  - Found: #/distributions/0/conforms_to: WaveForm DataBase (WFDB)
  - Found: #/distributions/1/conforms_to: The Observational Medical Outcomes Partnership (OMOP) Common Data Model (CDM)
  - Found: #/distributions/2/conforms_to: ASCII File Format Guidelines for Earth Science Data
  - Found: #/distributions/3/conforms_to: Digital Imaging and Communications in Medicine (DICOM)
  - Found: #/distributions/4/conforms_to: Digital Imaging and Communications in Medicine (DICOM)
  - Found: #/distributions/5/conforms_to: Digital Imaging and Communications in Medicine (DICOM)
  - Found: #/distributions/6/conforms_to: Digital Imaging and Communications in Medicine (DICOM)
  - Found: #/distributions/7/conforms_to: Open mHealth
  - Found: #/distributions/8/conforms_to: Open mHealth
  - Found: #/distributions/0/conforms_to_standard/0: WFDB
  - Found: #/distributions/1/conforms_to_standard/0: OMOP_CDM
  - Found: #/distributions/2/conforms_to_standard/0: ESDS
  - Found: #/distributions/3/conforms_to_standard/0: DICOM
  - Found: #/distributions/4/conforms_to_standard/0: DICOM
  - Found: #/distributions/5/conforms_to_standard/0: DICOM
  - Found: #/distributions/6/conforms_to_standard/0: DICOM
  - Found: #/distributions/7/conforms_to_standard/0: OPEN_MHEALTH
  - Found: #/distributions/8/conforms_to_standard/0: OPEN_MHEALTH

#### 9. Dataset Evaluation and Limitations Disclosure

Does the metadata communicate known risks, biases, or dataset limitations?

- ✅ **Known Limitations Documented**
  - Applicability: applicable; This item applies to every dataset
  - Found: #/known_limitations/0: {'limitation_description': 'Eligible participants were required to speak, read and understand Englis
  - Found: #/known_limitations/1: {'limitation_description': 'The overall enrollment goal is a balanced distribution between groups, b
  - Found: #/known_limitations/2: {'limitation_description': 'Recruitment was predominantly urban and hospital-based, which may not fu
  - Found: #/known_limitations/3: {'limitation_type': 'representativeness_limitation', 'limitation_description': 'The study cohort may
- ✅ **Biases Categorized Using Standard Taxonomy (RAI-aligned)**
  - Applicability: applicable; This item applies to every dataset
  - Found: #/known_biases/0: {'bias_type': 'selection_bias', 'bias_description': 'Participants are volunteers; the protocol publi
- ✅ **Data Anomalies and Quality Issues Noted**
  - Applicability: applicable; This item applies to every dataset
  - Found: #/anomalies/0: {'anomaly_details': 'In survey data, skipped questions or incomplete responses are expected.'}
  - Found: #/anomalies/1: {'anomaly_details': 'In data from wearables, improper use and technical failure such as battery fail
  - Found: #/anomalies/2: {'anomaly_details': 'In imaging data, patient uncooperation, noise that may obscure the images, tech
- ✅ **Sensitive Content and Warnings Provided**
  - Applicability: applicable; This item applies to every dataset
  - Found: #/sensitive_elements/0: {'sensitive_elements_present': False, 'sensitivity_details': 'The healthsheet states that the public
  - Found: #/content_warnings/0: {'content_warnings_present': False}
- ✅ **Ethical Review and Social Impact Analysis**
  - Applicability: applicable; This item applies to every dataset
  - Found: #/ethical_reviews/0: {'reviewing_organization': 'Institutional Review Board of the University of Washington', 'review_det
  - Found: #/future_use_impacts/0: {'impact_details': 'The healthsheet states that the creators do not currently anticipate any uses of

#### 10. Cross-Platform and Community Integration

Does the dataset connect to relevant repositories, communities and standards? A shared dataset needs citation or identifier guidance and a named hosting or preservation route appropriate to its domain.

- ✅ **Dataset Published on a Recognized Platform**
  - Applicability: unknown; shared_dataset: not declared; retained in the denominator
  - Found: #/publisher: https://fairhub.io/
- ✅ **Citation and DOI for Cross-referencing**
  - Applicability: unknown; shared_dataset: not declared; retained in the denominator
  - Found: #/doi: 10.60775/fairhub.3
- ✅ **Community Standards or Schema Conformance**
  - Applicability: unknown; shared_dataset: not declared; retained in the denominator
  - Found: #/conforms_to: Clinical Dataset Structure (CDS) v0.1.1
  - Found: #/distributions/0/conforms_to: WaveForm DataBase (WFDB)
  - Found: #/distributions/1/conforms_to: The Observational Medical Outcomes Partnership (OMOP) Common Data Model (CDM)
  - Found: #/distributions/2/conforms_to: ASCII File Format Guidelines for Earth Science Data
  - Found: #/distributions/3/conforms_to: Digital Imaging and Communications in Medicine (DICOM)
  - Found: #/distributions/4/conforms_to: Digital Imaging and Communications in Medicine (DICOM)
  - Found: #/distributions/5/conforms_to: Digital Imaging and Communications in Medicine (DICOM)
  - Found: #/distributions/6/conforms_to: Digital Imaging and Communications in Medicine (DICOM)
  - Found: #/distributions/7/conforms_to: Open mHealth
  - Found: #/distributions/8/conforms_to: Open mHealth
  - Found: #/distributions/0/conforms_to_standard/0: WFDB
  - Found: #/distributions/1/conforms_to_standard/0: OMOP_CDM
  - Found: #/distributions/2/conforms_to_standard/0: ESDS
  - Found: #/distributions/3/conforms_to_standard/0: DICOM
  - Found: #/distributions/4/conforms_to_standard/0: DICOM
  - Found: #/distributions/5/conforms_to_standard/0: DICOM
  - Found: #/distributions/6/conforms_to_standard/0: DICOM
  - Found: #/distributions/7/conforms_to_standard/0: OPEN_MHEALTH
  - Found: #/distributions/8/conforms_to_standard/0: OPEN_MHEALTH
- ✅ **Outreach Materials and Documentation Links**
  - Applicability: unknown; shared_dataset: not declared; retained in the denominator
  - Found: #/external_resources/0: {'name': 'AI-READI dataset documentation', 'external_resources': ['https://docs.aireadi.org/'], 'res
  - Found: #/external_resources/1: {'name': 'AI-READI project website', 'external_resources': ['https://aireadi.org/']}
  - Found: #/external_resources/2: {'name': 'License terms for the AI-READI dataset', 'external_resources': ['https://doi.org/10.5281/z
  - Found: #/external_resources/3: {'name': 'Zenodo community of the AI-READI project', 'external_resources': ['https://zenodo.org/comm
  - Found: #/external_resources/4: {'name': 'GitHub organization of the AI-READI project', 'external_resources': ['https://github.com/A
  - Found: #/external_resources/5: {'name': 'Clinical Dataset Structure (CDS) v0.1.1 specification', 'external_resources': ['https://cd
  - Found: #/external_resources/6: {'name': 'Protocol publication', 'external_resources': ['Owsley C, et al. Cross-sectional design and
  - Found: #/external_resources/7: {'name': 'Project overview publication', 'external_resources': ['AI-READI Consortium. AI-READI: reth
  - Found: #/page: https://fairhub.io/datasets/3
- ❌ **Related Datasets with Typed Relationships**
  - Applicability: unknown; shared_dataset: not declared; retained in the denominator
  - Fields checked: related_datasets

## Rubric20 Question Scores


### Structural Completeness

| ID | Question | Score | Status |
|----|----------|-------|--------|
| 1 | Field Completeness | 3.0/5 | ✅ |
| 2 | Entry Length Adequacy | 5.0/5 | ✅ |
| 3 | Keyword Diversity | 3.0/5 | ✅ |
| 4 | File Enumeration and Type Variety | 5.0/5 | ✅ |
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
| 12 | Collection Protocol Clarity | 5.0/5 | ✅ |
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
| 20 | Bias Documentation and Responsible AI Alignment | 5.0/5 | ✅ |

Applicability for Q16: applicable; This item applies to every dataset


Applicability for Q17: unknown; shared_dataset: not declared; retained in the denominator


Applicability for Q18: applicable; This item applies to every dataset


Applicability for Q19: applicable; This item applies to every dataset


Applicability for Q20: applicable; This item applies to every dataset
