# Detailed Evaluation: AI_READI - CLAUDECODE_RELEASE

Evaluated: 2026-11-25T19:12:15.185718
File: `data/d4d_concatenated/claudecode_release/2026-11-25c_claude-fable-5-2-claudecode-generic-v9_rep2/AI_READI_d4d.yaml`

Instrument: `b38117d96e73987f236d4d3d47da5b84a952401537f9a2ae4d2c44bf981fc064`
Applicability context: `fca403729b83dda36a67c4b749455b0fd864ba992e0e40b9a0f5c65bc039bfad`
Scope: single_dataset
## Overall Scores

- **Rubric10**: 46.0/50 (92.0%)
- **Rubric20**: 64.0/88 (72.7%)

## Rubric10 Element Scores

| ID | Element | Score | Details |
|----|---------|-------|---------|
| 1 | Dataset Discovery and Identification | 5/5 | 5/5 applicable sub-elements present; 0 N/A |
| 2 | Dataset Access and Retrieval | 4/5 | 4/5 applicable sub-elements present; 0 N/A |
| 3 | Data Reuse and Interoperability | 4/5 | 4/5 applicable sub-elements present; 0 N/A |
| 4 | Ethical Use and Privacy Safeguards | 5/5 | 5/5 applicable sub-elements present; 0 N/A |
| 5 | Data Composition and Structure | 4/5 | 4/5 applicable sub-elements present; 0 N/A |
| 6 | Data Provenance and Version Tracking | 5/5 | 5/5 applicable sub-elements present; 0 N/A |
| 7 | Scientific Motivation and Funding Transparency | 5/5 | 5/5 applicable sub-elements present; 0 N/A |
| 8 | Technical Transparency (Data Collection and Processing) | 4/5 | 4/5 applicable sub-elements present; 0 N/A |
| 9 | Dataset Evaluation and Limitations Disclosure | 5/5 | 5/5 applicable sub-elements present; 0 N/A |
| 10 | Cross-Platform and Community Integration | 5/5 | 5/5 applicable sub-elements present; 0 N/A |

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
  - Found: #/description: Version 3.0.0 of the AI-READI dataset, a dataset of data collected from individuals with and without
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
- ✅ **Hierarchical Structure (parent datasets, relationships)**
  - Applicability: applicable; This item applies to every dataset
  - Found: #/related_datasets/0: {'target_dataset': 'doi:10.60775/fairhub.2', 'relationship_type': 'is_new_version_of', 'description'
  - Found: #/related_datasets/1: {'target_dataset': 'doi:10.60775/fairhub.1', 'relationship_type': 'is_new_version_of', 'description'
  - Found: #/related_datasets/2: {'target_dataset': 'AI-READI controlled access dataset', 'relationship_type': 'is_part_of', 'descrip

#### 2. Dataset Access and Retrieval

Can the dataset and its associated resources be located, accessed, and downloaded?

- ✅ **Access Policy and IP Restrictions Defined**
  - Applicability: applicable; This item applies to every dataset
  - Found: #/license_and_use_terms: {'data_use_permission': ['disease_specific_research'], 'license_terms': 'The dataset is licensed und
  - Found: #/ip_restrictions: {'restrictions': ['Title to the Data, and all industrial and intellectual property rights therein, r
- ✅ **Regulatory Compliance and Confidentiality Classification**
  - Applicability: unknown; regulated_access: not declared; retained in the denominator
  - Found: #/regulatory_restrictions: {'regulatory_restrictions': ['Licensees agree to comply with all data security and privacy standards
- ❌ **Download URL or Platform Link Available**
  - Applicability: applicable; This item applies to every dataset
  - Fields checked: download_url
- ✅ **Distribution Formats and File Types Specified**
  - Applicability: applicable; This item applies to every dataset
  - Found: #/distribution_formats/0: {'media_type': 'application/dicom'}
  - Found: #/distribution_formats/1: {'media_type': 'text/markdown'}
  - Found: #/distribution_formats/2: {'media_type': 'text/csv'}
  - Found: #/distribution_formats/3: {'media_type': 'application/json'}
  - Found: #/distribution_formats/4: {'format': 'WaveForm DataBase (WFDB)'}
  - Found: #/distribution_formats/4/format: WaveForm DataBase (WFDB)
  - Found: #/file_collections/0/resources/0/format: TSV
  - Found: #/file_collections/1/resources/0/format: JSON
  - Found: #/file_collections/2/resources/0/format: TSV
  - Found: #/file_collections/3/resources/0/format: TSV
  - Found: #/file_collections/4/resources/0/format: TSV
  - Found: #/file_collections/5/resources/0/format: TSV
  - Found: #/file_collections/6/resources/0/format: TSV
  - Found: #/file_collections/7/resources/0/format: TSV
  - Found: #/file_collections/8/resources/0/format: TSV
  - Found: #/file_collections/9/resources/0/format: MD
  - Found: #/file_collections/9/resources/1/format: JSON
  - Found: #/file_collections/9/resources/2/format: JSON
  - Found: #/file_collections/9/resources/3/format: MD
  - Found: #/file_collections/9/resources/4/format: TXT
  - Found: #/file_collections/9/resources/5/format: JSON
  - Found: #/file_collections/9/resources/6/format: TSV
  - Found: #/file_collections/9/resources/7/format: MD
  - Found: #/file_collections/9/resources/8/format: JSON
  - Found: #/distribution_formats/0/media_type: application/dicom
  - Found: #/distribution_formats/1/media_type: text/markdown
  - Found: #/distribution_formats/2/media_type: text/csv
  - Found: #/distribution_formats/3/media_type: application/json
- ✅ **Related Datasets and External Resources Linked**
  - Applicability: applicable; This item applies to every dataset
  - Found: #/related_datasets/0: {'target_dataset': 'doi:10.60775/fairhub.2', 'relationship_type': 'is_new_version_of', 'description'
  - Found: #/related_datasets/1: {'target_dataset': 'doi:10.60775/fairhub.1', 'relationship_type': 'is_new_version_of', 'description'
  - Found: #/related_datasets/2: {'target_dataset': 'AI-READI controlled access dataset', 'relationship_type': 'is_part_of', 'descrip
  - Found: #/external_resources/0: {'name': 'Protocol publication', 'description': 'Owsley C, et al. Cross-sectional design and protoco
  - Found: #/external_resources/1: {'name': 'Project overview publication', 'description': 'AI-READI Consortium. AI-READI: rethinking A
  - Found: #/external_resources/2: {'name': 'AI-READI dataset documentation', 'description': 'Documentation of the AI-READI dataset. Th
  - Found: #/external_resources/3: {'name': 'AI-READI project website', 'external_resources': ['https://aireadi.org/']}
  - Found: #/external_resources/4: {'name': 'Zenodo community of the AI-READI project', 'external_resources': ['https://zenodo.org/comm
  - Found: #/external_resources/5: {'name': 'GitHub organization of the AI-READI project', 'external_resources': ['https://github.com/A
  - Found: #/external_resources/6: {'name': 'ClinicalTrials.gov registration', 'description': 'ClinicalTrials.gov identifier NCT0600204

#### 3. Data Reuse and Interoperability

Is sufficient information provided to reuse and integrate the dataset with others?
Note: Evaluate whether the dataset is designed for integration with similar datasets, including: common identifiers for cross-dataset linking, standardized formats for data harmonization, and documented integration procedures.


- ✅ **License Terms Allow Reuse**
  - Applicability: unknown; shared_dataset: not declared; retained in the denominator
  - Found: #/license_and_use_terms: {'data_use_permission': ['disease_specific_research'], 'license_terms': 'The dataset is licensed und
- ✅ **Data Formats Are Standardized (encoding, format)**
  - Applicability: unknown; shared_dataset: not declared; retained in the denominator
  - Found: #/distribution_formats/4/format: WaveForm DataBase (WFDB)
  - Found: #/file_collections/0/resources/0/format: TSV
  - Found: #/file_collections/1/resources/0/format: JSON
  - Found: #/file_collections/2/resources/0/format: TSV
  - Found: #/file_collections/3/resources/0/format: TSV
  - Found: #/file_collections/4/resources/0/format: TSV
  - Found: #/file_collections/5/resources/0/format: TSV
  - Found: #/file_collections/6/resources/0/format: TSV
  - Found: #/file_collections/7/resources/0/format: TSV
  - Found: #/file_collections/8/resources/0/format: TSV
  - Found: #/file_collections/9/resources/0/format: MD
  - Found: #/file_collections/9/resources/1/format: JSON
  - Found: #/file_collections/9/resources/2/format: JSON
  - Found: #/file_collections/9/resources/3/format: MD
  - Found: #/file_collections/9/resources/4/format: TXT
  - Found: #/file_collections/9/resources/5/format: JSON
  - Found: #/file_collections/9/resources/6/format: TSV
  - Found: #/file_collections/9/resources/7/format: MD
  - Found: #/file_collections/9/resources/8/format: JSON
- ✅ **Schema or Ontology Conformance Stated**
  - Applicability: unknown; shared_dataset: not declared; retained in the denominator
  - Found: #/conforms_to: Clinical Dataset Structure (CDS) v0.1.1 for the organization of the dataset; per data type, the data
- ❌ **Variable Metadata with Identifiers Defined**
  - Applicability: unknown; shared_dataset: not declared; retained in the denominator
  - Fields checked: variables
- ✅ **Use Guidance Provided (intended, prohibited uses)**
  - Applicability: applicable; This item applies to every dataset
  - Found: #/intended_uses/0: {'use_category': 'research', 'description': 'Type 2 diabetes related research: accessing the public 
  - Found: #/intended_uses/1: {'description': 'Future creation of artificial intelligence/machine learning (AI/ML) algorithms aime
  - Found: #/prohibited_uses/0: {'description': 'Making clinical treatment decisions based on the Data.', 'prohibition_reason': 'The
  - Found: #/prohibited_uses/1: {'description': 'Using the Data, alone or in concert with other information, to compromise or otherw
  - Found: #/prohibited_uses/2: {'description': 'Using the Data to invade or compromise the privacy of any Data Subject.'}
  - Found: #/prohibited_uses/3: {'description': 'Attempting to identify or contact any Data Subject or group of Data Subjects.'}
  - Found: #/prohibited_uses/4: {'description': 'Extracting or extrapolating any identifying information about a Data Subject.'}
  - Found: #/prohibited_uses/5: {'description': "Establishing a Data Subject's membership in a particular group of persons."}
  - Found: #/prohibited_uses/6: {'description': 'Otherwise causing harm or injury to any Data Subject.'}
  - Found: #/prohibited_uses/7: {'description': 'Transferring, licensing, sublicensing, selling, assigning, displaying, sharing or o
  - Found: #/prohibited_uses/8: {'description': 'Sharing or distributing Data with any third party model vendor or developer for tra
  - Found: #/prohibited_uses/9: {'description': 'Reproducing Data in papers, articles, presentations, analyses, reports or publicati
  - Found: #/prohibited_uses/10: {'description': 'Removing, obscuring, altering or masking the watermarking of the Data.'}

#### 4. Ethical Use and Privacy Safeguards

Does the dataset document the ethical oversight, privacy, consent and safeguards that apply to its subjects and governance context? Equivalent local ethics and regulatory frameworks are accepted; HIPAA or an IRB is not a universal requirement.

- ✅ **IRB or Ethics Review and Data Protection Impact**
  - Applicability: unknown; any: human_subjects: not declared; retained in the denominator; regulated_access: not declared; retained in the denominator
  - Found: #/ethical_reviews/0: {'reviewing_organization': 'Institutional Review Board of the University of Washington', 'review_det
  - Found: #/human_subject_research: {'involves_human_subjects': True, 'ethics_review_board': 'Institutional Review Board of the Universi
- ✅ **Deidentification Method Described**
  - Applicability: unknown; any: human_subjects: not declared; retained in the denominator; regulated_access: not declared; retained in the denominator
  - Found: #/is_deidentified: {'identifiable_elements_present': False, 'deidentification_details': 'No identifiers were collected,
- ✅ **Privacy Protections and Re-identification Risk Assessment**
  - Applicability: unknown; human_subjects: not declared; retained in the denominator
  - Found: #/participant_privacy/0: {'privacy_techniques': 'The environmental sensor and the fitness tracker were chosen with participan
  - Found: #/participant_privacy/1: {'privacy_techniques': 'To prevent re-identification attempts, the consortium described implementing
  - Found: #/participant_privacy/2: {'privacy_techniques': 'The IRB protocol states that all study data and identifiable information wil
- ✅ **Informed Consent Obtained from Participants**
  - Applicability: unknown; human_subjects: not declared; retained in the denominator
  - Found: #/informed_consent/0: {'consent_obtained': True, 'consent_type': 'Written informed consent, given electronically (e-consen
- ✅ **Vulnerable Populations and Compensation Documented**
  - Applicability: unknown; human_subjects: not declared; retained in the denominator
  - Found: #/participant_compensation/0: {'compensation_provided': True, 'compensation_type': 'Monetary stipend', 'compensation_amount': '$20

#### 5. Data Composition and Structure

Can the dataset's structure, modality, and population be understood from metadata?

- ✅ **Cohort or Subpopulations Characteristics Described**
  - Applicability: applicable; This item applies to every dataset
  - Found: #/subpopulations/0: {'name': 'Race/ethnicity', 'subpopulation_elements_present': False, 'identification': 'Self-reported
  - Found: #/subpopulations/1: {'name': 'Sex', 'subpopulation_elements_present': False, 'identification': 'Sex data are not release
  - Found: #/subpopulations/2: {'name': 'Diabetes status', 'identification': 'Four study groups: participants who do not have Type 
- ✅ **Number of Instances or Samples Reported**
  - Applicability: applicable; This item applies to every dataset
  - Found: #/instances/0: {'instance_type': 'individual patient (study participant)', 'data_topic': 'B2AI_TOPIC:43', 'counts':
- ❌ **Variable-Level Metadata, Tabular Flag, and Data Splits**
  - Applicability: applicable; This item applies to every dataset
  - Fields checked: variables, is_tabular, is_data_split, is_subpopulation
- ✅ **Data Topics or Conditions Represented**
  - Applicability: applicable; This item applies to every dataset
  - Found: #/instances/0: {'instance_type': 'individual patient (study participant)', 'data_topic': 'B2AI_TOPIC:43', 'counts':
- ✅ **Data Quality, Anomalies, and Missing Data Documented**
  - Applicability: applicable; This item applies to every dataset
  - Found: #/anomalies/0: {'anomaly_details': 'In survey data, skipped questions or incomplete responses are expected.'}
  - Found: #/anomalies/1: {'anomaly_details': 'With wearables, improper use and technical failure such as battery failure or s
  - Found: #/anomalies/2: {'anomaly_details': 'In imaging data, patient uncooperation, noise that may obscure the images, tech
  - Found: #/sampling_strategies/0: {'is_sample': False, 'is_random': False, 'is_representative': False, 'why_not_representative': 'Rath

#### 6. Data Provenance and Version Tracking

Can a user determine dataset versions, update history, and provenance?

- ✅ **Dataset Version Number Provided**
  - Applicability: unknown; shared_dataset: not declared; retained in the denominator
  - Found: #/version: 3.0.0
- ✅ **Version Access Methods Documented**
  - Applicability: unknown; shared_dataset: not declared; retained in the denominator
  - Found: #/version_access: {'latest_version_doi': 'doi:10.60775/fairhub.3', 'versions_available': ['3.0.0'], 'version_details':
- ✅ **Change Descriptions and Errata Provided**
  - Applicability: unknown; shared_dataset: not declared; retained in the denominator
  - Found: #/updates: {'frequency': 'Approximately once a year', 'update_details': 'The dataset is released as static vers
- ✅ **Update Schedule or Frequency Indicated**
  - Applicability: unknown; shared_dataset: not declared; retained in the denominator
  - Found: #/updates: {'frequency': 'Approximately once a year', 'update_details': 'The dataset is released as static vers
- ✅ **Provenance, Source Derivation, and Raw Data Sources**
  - Applicability: unknown; shared_dataset: not declared; retained in the denominator
  - Found: #/raw_data_sources/0: {'source_description': 'ECG device data exported in raw format to local storage.', 'raw_data_format'
  - Found: #/raw_data_sources/1: {'source_description': 'MoCA Duo application export (total score, section subscores, Memory Index Sc

#### 7. Scientific Motivation and Funding Transparency

Does the metadata clearly state why the dataset exists and who funded it?

- ✅ **Motivation or Purpose for Dataset Creation**
  - Applicability: applicable; This item applies to every dataset
  - Found: #/purposes/0: {'response': 'The dataset was created to enable future generations of artificial intelligence/machin
  - Found: #/purposes/1: {'response': 'An additional aim of the AI-READI project is to share its blueprint for collecting and
- ✅ **Primary Research Objectives or Tasks**
  - Applicability: applicable; This item applies to every dataset
  - Found: #/tasks/0: {'response': 'The multimodal dataset is being gathered to facilitate downstream pseudotime manifold 
- ✅ **Funding Sources and Mechanisms Listed**
  - Applicability: applicable; This item applies to every dataset
  - Found: #/funders/0: {'id': 'ROR:01cwqze88', 'grantor': 'National Institutes of Health', 'description': 'The creation of 
  - Found: #/funders/1: {'grantor': 'Research to Prevent Blindness', 'source_caveats': 'Named only in the funding statement 
- ✅ **Grant IDs or Award Numbers Present**
  - Applicability: applicable; This item applies to every dataset
  - Found: #/funders/0: {'id': 'ROR:01cwqze88', 'grantor': 'National Institutes of Health', 'description': 'The creation of 
  - Found: #/funders/1: {'grantor': 'Research to Prevent Blindness', 'source_caveats': 'Named only in the funding statement 
- ✅ **Creators and Acknowledgements Documented**
  - Applicability: applicable; This item applies to every dataset
  - Found: #/creators/0: {'name': 'AI-READI Consortium', 'description': 'The dataset was created by members of the AI-READI p
  - Found: #/creators/1: {'principal_investigator': {'id': 'ORCID:0000-0003-1994-7213', 'name': 'Cecilia Lee', 'orcid': '0000
  - Found: #/creators/2: {'principal_investigator': {'id': 'ORCID:0000-0003-4533-9334', 'name': 'Amir Bahmani', 'orcid': '000
  - Found: #/creators/3: {'principal_investigator': {'id': 'ORCID:0000-0002-5271-7690', 'name': 'Sally L. Baxter', 'orcid': '
  - Found: #/creators/4: {'principal_investigator': {'id': 'ORCID:0000-0001-5437-2545', 'name': 'Christopher G. Chute', 'orci
  - Found: #/creators/5: {'principal_investigator': {'id': 'ORCID:0000-0002-7899-3060', 'name': 'Jorge Contreras', 'orcid': '
  - Found: #/creators/6: {'principal_investigator': {'id': 'ORCID:0000-0002-3330-0224', 'name': 'Nicholas Evans', 'orcid': '0
  - Found: #/creators/7: {'principal_investigator': {'id': 'ORCID:0000-0001-9843-2845', 'name': 'Samantha Hurst', 'orcid': '0
  - Found: #/creators/8: {'principal_investigator': {'id': 'ORCID:0000-0003-2957-0755', 'name': 'T. Y. Alvin Liu', 'orcid': '
  - Found: #/creators/9: {'principal_investigator': {'id': 'ORCID:0000-0001-9592-1133', 'name': 'Gerald McGwin', 'orcid': '00
  - Found: #/creators/10: {'principal_investigator': {'id': 'ORCID:0000-0001-8333-6607', 'name': 'Shannon McWeeney', 'orcid': 
  - Found: #/creators/11: {'principal_investigator': {'id': 'ORCID:0000-0003-3424-011X', 'name': 'Cynthia Owsley', 'orcid': '0
  - Found: #/creators/12: {'principal_investigator': {'id': 'ORCID:0000-0002-0307-262X', 'name': 'Bhavesh Patel', 'orcid': '00
  - Found: #/creators/13: {'principal_investigator': {'id': 'ORCID:0000-0003-0784-7987', 'name': 'Michael Snyder', 'orcid': '0
  - Found: #/creators/14: {'principal_investigator': {'id': 'ORCID:0000-0002-3374-1177', 'name': 'Sara J. Singer', 'orcid': '0
  - Found: #/creators/15: {'principal_investigator': {'id': 'ORCID:0000-0002-1143-5224', 'name': 'Linda M. Zangwill', 'orcid':
  - Found: #/creators/16: {'principal_investigator': {'id': 'doi:10.60775/fairhub.3#person-hiroshi-ishikawa', 'name': 'Hiroshi
  - Found: #/creators/17: {'principal_investigator': {'id': 'doi:10.60775/fairhub.3#person-camille-nebeker', 'name': 'Camille 
  - Found: #/creators/18: {'principal_investigator': {'id': 'doi:10.60775/fairhub.3#person-jeffrey-c-edberg', 'name': 'Jeffrey
  - Found: #/creators/19: {'principal_investigator': {'id': 'doi:10.60775/fairhub.3#person-kadija-ferryman', 'name': 'Kadija F
  - Found: #/funders/0: {'id': 'ROR:01cwqze88', 'grantor': 'National Institutes of Health', 'description': 'The creation of 
  - Found: #/funders/1: {'grantor': 'Research to Prevent Blindness', 'source_caveats': 'Named only in the funding statement 

#### 8. Technical Transparency (Data Collection and Processing)

Can data collection and processing steps be replicated or understood?
Note: Preprocessing and collection metadata may be represented as structured text descriptions OR as machine-readable provenance graphs (e.g., W3C PROV-O, workflow graphs). Evaluation should check for: (1) structured text descriptions OR (2) graph representations with entity-activity-agent relationships. Both formats are acceptable.


- ✅ **Collection Mechanisms and Settings Described**
  - Applicability: unknown; data_collection: not declared; retained in the denominator
  - Found: #/collection_mechanisms/0: {'name': 'Questionnaires in REDCap', 'mechanism_details': 'REDCap is used for collecting patient-rep
  - Found: #/collection_mechanisms/1: {'name': '12-lead electrocardiogram', 'mechanism_details': 'A 12-lead ECG is performed with a Philip
  - Found: #/collection_mechanisms/2: {'name': 'Monofilament test for peripheral neuropathy', 'mechanism_details': 'A standard 10 g monofi
  - Found: #/collection_mechanisms/3: {'name': 'Montreal Cognitive Assessment (MoCA)', 'mechanism_details': "Research staff administer the
  - Found: #/collection_mechanisms/4: {'name': 'Visual acuity testing', 'mechanism_details': 'Letter visual acuity is measured with the M&
  - Found: #/collection_mechanisms/5: {'name': 'Contrast sensitivity testing', 'mechanism_details': 'The MARS Letter Contrast Sensitivity 
  - Found: #/collection_mechanisms/6: {'name': 'Autorefraction', 'mechanism_details': 'Autorefraction data for each eye are obtained with 
  - Found: #/collection_mechanisms/7: {'name': 'Blood and urine collection', 'mechanism_details': 'Blood (non-fasting; 53 mL per the BMJ O
  - Found: #/collection_mechanisms/8: {'name': 'Undilated fundus photography (Optomed Aurora)', 'mechanism_details': 'The Optomed Aurora I
  - Found: #/collection_mechanisms/9: {'name': 'Home environmental sensor', 'mechanism_details': "A custom-designed environmental sensor u
  - Found: #/collection_mechanisms/10: {'name': 'Wearable activity monitor (Garmin Vivosmart 5)', 'mechanism_details': 'The Garmin Vivosmar
  - Found: #/collection_mechanisms/11: {'name': 'Continuous glucose monitor (Dexcom G6)', 'mechanism_details': 'The Dexcom G6, a real-time 
  - Found: #/collection_mechanisms/12: {'name': 'Blood pressure measurement', 'mechanism_details': 'Blood pressure devices used across the 
  - Found: #/collection_mechanisms/13: {'name': 'Lensometry', 'mechanism_details': 'Lensometer devices used at data acquisition sites inclu
  - Found: #/collection_mechanisms/14: {'name': 'Dilated fundus photography (iCare EIDON)', 'mechanism_details': 'The iCare EIDON is a wide
  - Found: #/collection_mechanisms/15: {'name': 'Heidelberg Spectralis HRA', 'mechanism_details': 'Imaging with the Heidelberg Spectralis H
  - Found: #/collection_mechanisms/16: {'name': 'Topcon Triton DRI OCT', 'mechanism_details': 'The DRI OCT Triton from Topcon Healthcare co
  - Found: #/collection_mechanisms/17: {'name': 'Topcon Maestro2 3D OCT', 'mechanism_details': 'The Maestro2 is a robotic OCT and color fun
  - Found: #/collection_mechanisms/18: {'name': 'Fluorescence lifetime imaging ophthalmoscopy (Heidelberg FLIO)', 'mechanism_details': 'FLI
  - Found: #/collection_mechanisms/19: {'name': 'Zeiss Cirrus 5000 Angioplex', 'mechanism_details': 'The Zeiss Cirrus 5000 Angioplex is a h
- ✅ **Data Acquisition Methods Listed**
  - Applicability: unknown; data_collection: not declared; retained in the denominator
  - Found: #/acquisition_methods/0: {'was_directly_observed': True, 'acquisition_details': 'Some data were directly observable, such as 
  - Found: #/acquisition_methods/1: {'was_reported_by_subjects': True, 'was_validated_verified': True, 'acquisition_details': 'Other dat
- ✅ **Preprocessing, Cleaning, Labeling, and Annotation Quality**
  - Applicability: unknown; data_processing: not declared; retained in the denominator
  - Found: #/preprocessing_strategies/0: {'preprocessing_details': 'All data were mapped to standardized terminologies when possible, such as
  - Found: #/preprocessing_strategies/1: {'preprocessing_details': "Images are exported from imaging devices in their raw format, and some im
  - Found: #/preprocessing_strategies/2: {'preprocessing_details': "The BMJ Open protocol paper's monitoring device table lists an export in 
  - Found: #/cleaning_strategies/0: {'cleaning_details': 'The Data Manager at each data site is responsible for the quality control of a
  - Found: #/cleaning_strategies/1: {'cleaning_details': 'Quality control at the time of data entry/acquisition: clinical data outside o
  - Found: #/cleaning_strategies/2: {'cleaning_details': 'The dataset has not undergone any formal external audits, but has been reviewe
- ❌ **Software and Tools Documented**
  - Applicability: unknown; processing_software: not declared; retained in the denominator
  - Fields checked: software_and_tools
- ✅ **External Standards, Resources, and Imputation Protocols**
  - Applicability: applicable; This item applies to every dataset
  - Found: #/external_resources/0: {'name': 'Protocol publication', 'description': 'Owsley C, et al. Cross-sectional design and protoco
  - Found: #/external_resources/1: {'name': 'Project overview publication', 'description': 'AI-READI Consortium. AI-READI: rethinking A
  - Found: #/external_resources/2: {'name': 'AI-READI dataset documentation', 'description': 'Documentation of the AI-READI dataset. Th
  - Found: #/external_resources/3: {'name': 'AI-READI project website', 'external_resources': ['https://aireadi.org/']}
  - Found: #/external_resources/4: {'name': 'Zenodo community of the AI-READI project', 'external_resources': ['https://zenodo.org/comm
  - Found: #/external_resources/5: {'name': 'GitHub organization of the AI-READI project', 'external_resources': ['https://github.com/A
  - Found: #/external_resources/6: {'name': 'ClinicalTrials.gov registration', 'description': 'ClinicalTrials.gov identifier NCT0600204
  - Found: #/conforms_to: Clinical Dataset Structure (CDS) v0.1.1 for the organization of the dataset; per data type, the data

#### 9. Dataset Evaluation and Limitations Disclosure

Does the metadata communicate known risks, biases, or dataset limitations?

- ✅ **Known Limitations Documented**
  - Applicability: applicable; This item applies to every dataset
  - Found: #/known_limitations/0: {'limitation_description': 'The overall enrollment goal is a balanced distribution between groups, b
  - Found: #/known_limitations/1: {'limitation_type': 'representativeness_limitation', 'limitation_description': 'The study cohort may
  - Found: #/known_limitations/2: {'limitation_description': 'Participants must speak and read English; the BMJ Open protocol paper no
- ✅ **Biases Categorized Using Standard Taxonomy (RAI-aligned)**
  - Applicability: applicable; This item applies to every dataset
  - Found: #/known_biases/0: {'bias_type': 'selection_bias', 'bias_description': 'Participants are volunteers, so there is select
  - Found: #/known_biases/1: {'bias_description': 'Recruitment was predominantly urban and hospital-based, which may not fully ca
- ✅ **Data Anomalies and Quality Issues Noted**
  - Applicability: applicable; This item applies to every dataset
  - Found: #/anomalies/0: {'anomaly_details': 'In survey data, skipped questions or incomplete responses are expected.'}
  - Found: #/anomalies/1: {'anomaly_details': 'With wearables, improper use and technical failure such as battery failure or s
  - Found: #/anomalies/2: {'anomaly_details': 'In imaging data, patient uncooperation, noise that may obscure the images, tech
- ✅ **Sensitive Content and Warnings Provided**
  - Applicability: applicable; This item applies to every dataset
  - Found: #/sensitive_elements/0: {'sensitive_elements_present': False, 'sensitivity_details': 'The healthsheet states that the public
  - Found: #/content_warnings/0: {'content_warnings_present': False}
- ✅ **Ethical Review and Social Impact Analysis**
  - Applicability: applicable; This item applies to every dataset
  - Found: #/ethical_reviews/0: {'reviewing_organization': 'Institutional Review Board of the University of Washington', 'review_det
  - Found: #/future_use_impacts/0: {'impact_details': 'The creators do not currently anticipate any uses of the dataset that could resu

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
  - Found: #/conforms_to: Clinical Dataset Structure (CDS) v0.1.1 for the organization of the dataset; per data type, the data
- ✅ **Outreach Materials and Documentation Links**
  - Applicability: unknown; shared_dataset: not declared; retained in the denominator
  - Found: #/external_resources/0: {'name': 'Protocol publication', 'description': 'Owsley C, et al. Cross-sectional design and protoco
  - Found: #/external_resources/1: {'name': 'Project overview publication', 'description': 'AI-READI Consortium. AI-READI: rethinking A
  - Found: #/external_resources/2: {'name': 'AI-READI dataset documentation', 'description': 'Documentation of the AI-READI dataset. Th
  - Found: #/external_resources/3: {'name': 'AI-READI project website', 'external_resources': ['https://aireadi.org/']}
  - Found: #/external_resources/4: {'name': 'Zenodo community of the AI-READI project', 'external_resources': ['https://zenodo.org/comm
  - Found: #/external_resources/5: {'name': 'GitHub organization of the AI-READI project', 'external_resources': ['https://github.com/A
  - Found: #/external_resources/6: {'name': 'ClinicalTrials.gov registration', 'description': 'ClinicalTrials.gov identifier NCT0600204
  - Found: #/page: https://fairhub.io/datasets/3
- ✅ **Related Datasets with Typed Relationships**
  - Applicability: unknown; shared_dataset: not declared; retained in the denominator
  - Found: #/related_datasets/0: {'target_dataset': 'doi:10.60775/fairhub.2', 'relationship_type': 'is_new_version_of', 'description'
  - Found: #/related_datasets/1: {'target_dataset': 'doi:10.60775/fairhub.1', 'relationship_type': 'is_new_version_of', 'description'
  - Found: #/related_datasets/2: {'target_dataset': 'AI-READI controlled access dataset', 'relationship_type': 'is_part_of', 'descrip

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
