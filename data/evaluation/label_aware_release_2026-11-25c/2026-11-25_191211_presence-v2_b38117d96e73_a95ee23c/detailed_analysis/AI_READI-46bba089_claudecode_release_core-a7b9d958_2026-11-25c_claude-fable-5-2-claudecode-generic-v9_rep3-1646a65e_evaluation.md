# Detailed Evaluation: AI_READI - CLAUDECODE_RELEASE_CORE

Evaluated: 2026-11-25T19:12:21.369138
File: `data/d4d_concatenated/claudecode_release_core/2026-11-25c_claude-fable-5-2-claudecode-generic-v9_rep3/AI_READI_d4d_core.yaml`

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
  - Found: #/description: The AI-READI dataset consists of data collected from individuals with and without Type 2 Diabetes Me
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
  - Found: #/license_and_use_terms: {'name': 'AI-READI Data License Agreement (Version 2.0)', 'license_terms': 'The Licensor, Washington
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
  - Found: #/distributions/1: {'description': 'This is a metadata file based on the Clinical Dataset Structure (CDS) v0.1.1.', 'fo
  - Found: #/distributions/3: {'description': 'The dqd_omop.json file supports OMOP CDM data quality analysis using the OMOP CDM D
  - Found: #/distributions/5: {'description': 'This is a metadata file based on the Clinical Dataset Structure (CDS).', 'format': 
  - Found: #/distributions/7: {'description': 'This is a metadata file based on the Clinical Dataset Structure (CDS).', 'format': 
  - Found: #/distributions/9: {'description': 'This is a metadata file based on the Clinical Dataset Structure (CDS).', 'format': 
  - Found: #/distributions/11: {'description': 'This is a metadata file based on the Clinical Dataset Structure (CDS).', 'format': 
  - Found: #/distributions/13: {'description': 'This is a metadata file based on the Clinical Dataset Structure (CDS).', 'format': 
  - Found: #/distributions/15: {'description': 'This is a metadata file based on the Clinical Dataset Structure (CDS).', 'format': 
  - Found: #/distributions/17: {'description': 'This is a metadata file based on the Clinical Dataset Structure (CDS).', 'format': 
  - Found: #/distributions/19: {'format': 'MD', 'id': 'doi:10.60775/fairhub.3#CHANGELOG.md', 'media_type': 'text/markdown', 'name':
  - Found: #/distributions/20: {'format': 'JSON', 'id': 'doi:10.60775/fairhub.3#dataset_description.json', 'media_type': 'applicati
  - Found: #/distributions/21: {'format': 'JSON', 'id': 'doi:10.60775/fairhub.3#dataset_structure_description.json', 'media_type': 
  - Found: #/distributions/22: {'format': 'MD', 'id': 'doi:10.60775/fairhub.3#healthsheet.md', 'media_type': 'text/markdown', 'name
  - Found: #/distributions/23: {'format': 'TXT', 'id': 'doi:10.60775/fairhub.3#LICENSE.txt', 'media_type': 'text/plain', 'name': 'L
  - Found: #/distributions/24: {'format': 'JSON', 'id': 'doi:10.60775/fairhub.3#participants.json', 'media_type': 'application/json
  - Found: #/distributions/25: {'format': 'TSV', 'id': 'doi:10.60775/fairhub.3#participants.tsv', 'media_type': 'text/tab-separated
  - Found: #/distributions/26: {'format': 'MD', 'id': 'doi:10.60775/fairhub.3#README.md', 'media_type': 'text/markdown', 'name': 'R
  - Found: #/distributions/27: {'format': 'JSON', 'id': 'doi:10.60775/fairhub.3#study_description.json', 'media_type': 'application
  - Found: #/distributions/1/format: TSV
  - Found: #/distributions/3/format: JSON
  - Found: #/distributions/5/format: TSV
  - Found: #/distributions/7/format: TSV
  - Found: #/distributions/9/format: TSV
  - Found: #/distributions/11/format: TSV
  - Found: #/distributions/13/format: TSV
  - Found: #/distributions/15/format: TSV
  - Found: #/distributions/17/format: TSV
  - Found: #/distributions/19/format: MD
  - Found: #/distributions/20/format: JSON
  - Found: #/distributions/21/format: JSON
  - Found: #/distributions/22/format: MD
  - Found: #/distributions/23/format: TXT
  - Found: #/distributions/24/format: JSON
  - Found: #/distributions/25/format: TSV
  - Found: #/distributions/26/format: MD
  - Found: #/distributions/27/format: JSON
  - Found: #/distribution_formats/4/format: WaveForm DataBase (WFDB)
  - Found: #/distributions/1/media_type: text/tab-separated-values
  - Found: #/distributions/3/media_type: application/json
  - Found: #/distributions/5/media_type: text/tab-separated-values
  - Found: #/distributions/7/media_type: text/tab-separated-values
  - Found: #/distributions/9/media_type: text/tab-separated-values
  - Found: #/distributions/11/media_type: text/tab-separated-values
  - Found: #/distributions/13/media_type: text/tab-separated-values
  - Found: #/distributions/15/media_type: text/tab-separated-values
  - Found: #/distributions/17/media_type: text/tab-separated-values
  - Found: #/distributions/19/media_type: text/markdown
  - Found: #/distributions/20/media_type: application/json
  - Found: #/distributions/21/media_type: application/json
  - Found: #/distributions/22/media_type: text/markdown
  - Found: #/distributions/23/media_type: text/plain
  - Found: #/distributions/24/media_type: application/json
  - Found: #/distributions/25/media_type: text/tab-separated-values
  - Found: #/distributions/26/media_type: text/markdown
  - Found: #/distributions/27/media_type: application/json
  - Found: #/distribution_formats/0/media_type: application/dicom
  - Found: #/distribution_formats/1/media_type: text/markdown
  - Found: #/distribution_formats/2/media_type: text/csv
  - Found: #/distribution_formats/3/media_type: application/json
- ✅ **Related Datasets and External Resources Linked**
  - Applicability: applicable; This item applies to every dataset
  - Found: #/external_resources/0: {'name': 'AI-READI dataset documentation', 'description': 'The dataset is self-contained but does re
  - Found: #/external_resources/1: {'name': 'AI-READI project website', 'external_resources': ['https://aireadi.org/']}

#### 3. Data Reuse and Interoperability

Is sufficient information provided to reuse and integrate the dataset with others?
Note: Evaluate whether the dataset is designed for integration with similar datasets, including: common identifiers for cross-dataset linking, standardized formats for data harmonization, and documented integration procedures.


- ✅ **License Terms Allow Reuse**
  - Applicability: unknown; shared_dataset: not declared; retained in the denominator
  - Found: #/license_and_use_terms: {'name': 'AI-READI Data License Agreement (Version 2.0)', 'license_terms': 'The Licensor, Washington
- ✅ **Data Formats Are Standardized (encoding, format)**
  - Applicability: unknown; shared_dataset: not declared; retained in the denominator
  - Found: #/distributions/1/format: TSV
  - Found: #/distributions/3/format: JSON
  - Found: #/distributions/5/format: TSV
  - Found: #/distributions/7/format: TSV
  - Found: #/distributions/9/format: TSV
  - Found: #/distributions/11/format: TSV
  - Found: #/distributions/13/format: TSV
  - Found: #/distributions/15/format: TSV
  - Found: #/distributions/17/format: TSV
  - Found: #/distributions/19/format: MD
  - Found: #/distributions/20/format: JSON
  - Found: #/distributions/21/format: JSON
  - Found: #/distributions/22/format: MD
  - Found: #/distributions/23/format: TXT
  - Found: #/distributions/24/format: JSON
  - Found: #/distributions/25/format: TSV
  - Found: #/distributions/26/format: MD
  - Found: #/distributions/27/format: JSON
  - Found: #/distribution_formats/4/format: WaveForm DataBase (WFDB)
- ✅ **Schema or Ontology Conformance Stated**
  - Applicability: unknown; shared_dataset: not declared; retained in the denominator
  - Found: #/conforms_to: Clinical Dataset Structure (CDS) v0.1.1
  - Found: #/distributions/0/conforms_to_standard/0: WFDB
  - Found: #/distributions/0/conforms_to_standard/1: CDS
  - Found: #/distributions/2/conforms_to_standard/0: OMOP_CDM
  - Found: #/distributions/2/conforms_to_standard/1: CDS
  - Found: #/distributions/4/conforms_to_standard/0: ESDS
  - Found: #/distributions/4/conforms_to_standard/1: CDS
  - Found: #/distributions/6/conforms_to_standard/0: DICOM
  - Found: #/distributions/6/conforms_to_standard/1: CDS
  - Found: #/distributions/8/conforms_to_standard/0: DICOM
  - Found: #/distributions/8/conforms_to_standard/1: CDS
  - Found: #/distributions/10/conforms_to_standard/0: DICOM
  - Found: #/distributions/10/conforms_to_standard/1: CDS
  - Found: #/distributions/12/conforms_to_standard/0: DICOM
  - Found: #/distributions/12/conforms_to_standard/1: CDS
  - Found: #/distributions/14/conforms_to_standard/0: OPEN_MHEALTH
  - Found: #/distributions/14/conforms_to_standard/1: CDS
  - Found: #/distributions/16/conforms_to_standard/0: OPEN_MHEALTH
  - Found: #/distributions/16/conforms_to_standard/1: CDS
  - Found: #/conforms_to_schema: src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml
- ❌ **Variable Metadata with Identifiers Defined**
  - Applicability: unknown; shared_dataset: not declared; retained in the denominator
  - Fields checked: variables
- ✅ **Use Guidance Provided (intended, prohibited uses)**
  - Applicability: applicable; This item applies to every dataset
  - Found: #/intended_uses/0: {'name': 'Type 2 diabetes related research', 'description': 'The public version of the dataset can o
  - Found: #/intended_uses/1: {'name': 'Training, validating and testing AI/ML models', 'description': 'A suggested split for trai
  - Found: #/prohibited_uses/0: {'name': 'Clinical treatment decisions', 'description': 'Licensees shall not make clinical treatment
  - Found: #/prohibited_uses/1: {'name': 'Re-identification or contact of data subjects', 'description': "Licensees shall not use or
  - Found: #/prohibited_uses/2: {'name': 'Conveying the data to non-licensees', 'description': 'Licensees shall not transfer, licens
  - Found: #/prohibited_uses/3: {'name': 'Sharing data with third-party model vendors for training', 'description': 'Licensees shall
  - Found: #/prohibited_uses/4: {'name': 'Reproducing data in publications', 'description': 'Data may not be reproduced in papers, a

#### 4. Ethical Use and Privacy Safeguards

Does the dataset document the ethical oversight, privacy, consent and safeguards that apply to its subjects and governance context? Equivalent local ethics and regulatory frameworks are accepted; HIPAA or an IRB is not a universal requirement.

- ✅ **IRB or Ethics Review and Data Protection Impact**
  - Applicability: unknown; any: human_subjects: not declared; retained in the denominator; regulated_access: not declared; retained in the denominator
  - Found: #/ethical_reviews/0: {'reviewing_organization': 'Institutional Review Board (IRB) of the University of Washington', 'revi
  - Found: #/human_subject_research: {'involves_human_subjects': True, 'irb_approval': ['AI-READI was approved by the Institutional Revie
- ✅ **Deidentification Method Described**
  - Applicability: unknown; any: human_subjects: not declared; retained in the denominator; regulated_access: not declared; retained in the denominator
  - Found: #/is_deidentified: {'identifiable_elements_present': False, 'identifiers_removed': 'Information related to the sex and 
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
  - Found: #/subpopulations/0: {'name': 'Race/ethnicity, sex and diabetes status groups in the suggested split', 'identification': 
- ✅ **Number of Instances or Samples Reported**
  - Applicability: applicable; This item applies to every dataset
  - Found: #/instances/0: {'instance_type': 'individual patient', 'counts': 2280, 'label': False, 'description': 'Each instanc
- ❌ **Variable-Level Metadata, Tabular Flag, and Data Splits**
  - Applicability: applicable; This item applies to every dataset
  - Fields checked: variables, is_tabular, is_data_split, is_subpopulation
- ✅ **Data Topics or Conditions Represented**
  - Applicability: applicable; This item applies to every dataset
  - Found: #/instances/0: {'instance_type': 'individual patient', 'counts': 2280, 'label': False, 'description': 'Each instanc
- ✅ **Data Quality, Anomalies, and Missing Data Documented**
  - Applicability: applicable; This item applies to every dataset
  - Found: #/anomalies/0: {'name': 'Survey data', 'anomaly_details': 'In cases of survey data, skipped questions or incomplete
  - Found: #/anomalies/1: {'name': 'Wearable data', 'anomaly_details': 'In cases of using wearables, improper use and technica
  - Found: #/anomalies/2: {'name': 'Imaging data', 'anomaly_details': 'In cases of imaging data, patient uncooperation, noise 
  - Found: #/sampling_strategies/0: {'name': 'Participant recruitment', 'is_random': False, 'is_representative': False, 'why_not_represe
  - Found: #/missing_data_documentation/0: {'missing_data_patterns': 'Not all modalities are available for all participants.', 'missing_data_ca

#### 6. Data Provenance and Version Tracking

Can a user determine dataset versions, update history, and provenance?

- ✅ **Dataset Version Number Provided**
  - Applicability: unknown; shared_dataset: not declared; retained in the denominator
  - Found: #/version: 3.0.0
- ✅ **Version Access Methods Documented**
  - Applicability: unknown; shared_dataset: not declared; retained in the denominator
  - Found: #/version_access: {'latest_version_doi': 'doi:10.60775/fairhub.3', 'versions_available': ['Version 3.0.0, 10.60775/fai
- ✅ **Change Descriptions and Errata Provided**
  - Applicability: unknown; shared_dataset: not declared; retained in the denominator
  - Found: #/updates: {'frequency': 'approximately once a year', 'update_details': 'The dataset will not be updated. Rathe
- ✅ **Update Schedule or Frequency Indicated**
  - Applicability: unknown; shared_dataset: not declared; retained in the denominator
  - Found: #/updates: {'frequency': 'approximately once a year', 'update_details': 'The dataset will not be updated. Rathe
- ✅ **Provenance, Source Derivation, and Raw Data Sources**
  - Applicability: unknown; shared_dataset: not declared; retained in the denominator
  - Found: #/raw_data_sources/0: {'name': 'Electrocardiograph export', 'source_description': 'Data from the ECG device are exported i
  - Found: #/raw_data_sources/1: {'name': 'MoCA Duo application export', 'source_description': 'Data from the MoCA Duo application (t

#### 7. Scientific Motivation and Funding Transparency

Does the metadata clearly state why the dataset exists and who funded it?

- ✅ **Motivation or Purpose for Dataset Creation**
  - Applicability: applicable; This item applies to every dataset
  - Found: #/purposes/0: {'response': 'The purpose for creating the dataset was to enable future generations of artificial in
- ✅ **Primary Research Objectives or Tasks**
  - Applicability: applicable; This item applies to every dataset
  - Found: #/tasks/0: {'response': 'The multi-modal dataset is being gathered to facilitate downstream pseudotime manifold
- ✅ **Funding Sources and Mechanisms Listed**
  - Applicability: applicable; This item applies to every dataset
  - Found: #/funders/0: {'grantor': 'National Institutes of Health', 'description': 'The creation of the dataset was funded 
  - Found: #/funders/1: {'grantor': 'Research to Prevent Blindness', 'source_caveats': 'Named only in the funding statement 
- ✅ **Grant IDs or Award Numbers Present**
  - Applicability: applicable; This item applies to every dataset
  - Found: #/funders/0: {'grantor': 'National Institutes of Health', 'description': 'The creation of the dataset was funded 
  - Found: #/funders/1: {'grantor': 'Research to Prevent Blindness', 'source_caveats': 'Named only in the funding statement 
- ✅ **Creators and Acknowledgements Documented**
  - Applicability: applicable; This item applies to every dataset
  - Found: #/creators/0: {'name': 'AI-READI Consortium', 'description': 'This dataset was created by members of the AI-READI 
  - Found: #/creators/1: {'principal_investigator': {'id': 'ORCID:0000-0002-7452-1648', 'name': 'Aaron Lee', 'orcid': '0000-0
  - Found: #/creators/2: {'principal_investigator': {'id': 'ORCID:0000-0003-1994-7213', 'name': 'Cecilia Lee', 'orcid': '0000
  - Found: #/creators/3: {'principal_investigator': {'id': 'ORCID:0000-0003-4533-9334', 'name': 'Amir Bahmani', 'orcid': '000
  - Found: #/creators/4: {'principal_investigator': {'id': 'ORCID:0000-0002-5271-7690', 'name': 'Sally L. Baxter', 'orcid': '
  - Found: #/creators/5: {'principal_investigator': {'id': 'ORCID:0000-0001-5437-2545', 'name': 'Christopher G. Chute', 'orci
  - Found: #/creators/6: {'principal_investigator': {'id': 'ORCID:0000-0002-7899-3060', 'name': 'Jorge Contreras', 'orcid': '
  - Found: #/creators/7: {'principal_investigator': {'id': 'ORCID:0000-0002-3330-0224', 'name': 'Nicholas Evans', 'orcid': '0
  - Found: #/creators/8: {'principal_investigator': {'id': 'ORCID:0000-0001-9843-2845', 'name': 'Samantha Hurst', 'orcid': '0
  - Found: #/creators/9: {'principal_investigator': {'id': 'ORCID:0000-0003-2957-0755', 'name': 'T. Y. Alvin Liu', 'orcid': '
  - Found: #/creators/10: {'principal_investigator': {'id': 'ORCID:0000-0001-9592-1133', 'name': 'Gerald McGwin', 'orcid': '00
  - Found: #/creators/11: {'principal_investigator': {'id': 'ORCID:0000-0001-8333-6607', 'name': 'Shannon McWeeney', 'orcid': 
  - Found: #/creators/12: {'principal_investigator': {'id': 'ORCID:0000-0003-3424-011X', 'name': 'Cynthia Owsley', 'orcid': '0
  - Found: #/creators/13: {'principal_investigator': {'id': 'ORCID:0000-0002-0307-262X', 'name': 'Bhavesh Patel', 'orcid': '00
  - Found: #/creators/14: {'principal_investigator': {'id': 'ORCID:0000-0003-0784-7987', 'name': 'Michael Snyder', 'orcid': '0
  - Found: #/creators/15: {'principal_investigator': {'id': 'ORCID:0000-0002-3374-1177', 'name': 'Sara J. Singer', 'orcid': '0
  - Found: #/creators/16: {'principal_investigator': {'id': 'ORCID:0000-0002-1143-5224', 'name': 'Linda M. Zangwill', 'orcid':
  - Found: #/funders/0: {'grantor': 'National Institutes of Health', 'description': 'The creation of the dataset was funded 
  - Found: #/funders/1: {'grantor': 'Research to Prevent Blindness', 'source_caveats': 'Named only in the funding statement 

#### 8. Technical Transparency (Data Collection and Processing)

Can data collection and processing steps be replicated or understood?
Note: Preprocessing and collection metadata may be represented as structured text descriptions OR as machine-readable provenance graphs (e.g., W3C PROV-O, workflow graphs). Evaluation should check for: (1) structured text descriptions OR (2) graph representations with entity-activity-agent relationships. Both formats are acceptable.


- ✅ **Collection Mechanisms and Settings Described**
  - Applicability: unknown; data_collection: not declared; retained in the denominator
  - Found: #/collection_mechanisms/0: {'name': 'REDCap questionnaires and clinical data entry', 'mechanism_details': 'REDCap is used for c
  - Found: #/collection_mechanisms/1: {'name': '12-lead electrocardiogram', 'mechanism_details': 'A 12-lead ECG is performed (Philips Page
  - Found: #/collection_mechanisms/2: {'name': 'Montreal Cognitive Assessment (MoCA)', 'mechanism_details': 'A general cognitive screener 
  - Found: #/collection_mechanisms/3: {'name': 'Monofilament testing for peripheral neuropathy', 'mechanism_details': 'The monofilament te
  - Found: #/collection_mechanisms/4: {'name': 'Visual acuity testing', 'mechanism_details': 'Photopic letter visual acuity is measured wi
  - Found: #/collection_mechanisms/5: {'name': 'Contrast sensitivity testing', 'mechanism_details': 'Photopic letter contrast sensitivity 
  - Found: #/collection_mechanisms/6: {'name': 'Autorefraction', 'mechanism_details': "Autorefraction data for each eye are obtained using
  - Found: #/collection_mechanisms/7: {'name': 'Blood and urine collection for laboratory testing', 'mechanism_details': 'Blood (non-fasti
  - Found: #/collection_mechanisms/8: {'name': 'Optomed Aurora undilated fundus photography', 'mechanism_details': 'The Optomed Aurora IQ 
  - Found: #/collection_mechanisms/9: {'name': 'iCare EIDON dilated fundus photography', 'mechanism_details': 'The iCare EIDON is a widefi
  - Found: #/collection_mechanisms/10: {'name': 'Heidelberg Spectralis HRA', 'mechanism_details': 'The Heidelberg Spectralis HRA+OCT is an 
  - Found: #/collection_mechanisms/11: {'name': 'Topcon DRI OCT Triton', 'mechanism_details': 'The DRI OCT Triton is a device from Topcon H
  - Found: #/collection_mechanisms/12: {'name': 'Topcon Maestro2 3D OCT', 'mechanism_details': 'The Maestro2 is a robotic OCT and color fun
  - Found: #/collection_mechanisms/13: {'name': 'Heidelberg FLIO', 'mechanism_details': 'Fluorescence Lifetime Imaging Ophthalmoscopy (FLIO
  - Found: #/collection_mechanisms/14: {'name': 'Zeiss Cirrus 5000 Angioplex', 'mechanism_details': 'The Zeiss Cirrus 5000 Angioplex is a h
  - Found: #/collection_mechanisms/15: {'name': 'Dexcom G6 continuous glucose monitor', 'mechanism_details': 'The Dexcom G6 is a real-time,
  - Found: #/collection_mechanisms/16: {'name': 'Garmin Vivosmart 5 fitness tracker', 'mechanism_details': 'The Garmin Vivosmart 5 Fitness 
  - Found: #/collection_mechanisms/17: {'name': 'LeeLab Anura environmental sensor', 'mechanism_details': 'Participants are sent home with 
- ✅ **Data Acquisition Methods Listed**
  - Applicability: unknown; data_collection: not declared; retained in the denominator
  - Found: #/acquisition_methods/0: {'was_directly_observed': True, 'was_reported_by_subjects': True, 'was_validated_verified': True, 'a
- ✅ **Preprocessing, Cleaning, Labeling, and Annotation Quality**
  - Applicability: unknown; data_processing: not declared; retained in the denominator
  - Found: #/preprocessing_strategies/0: {'name': 'Mapping to standardized terminologies', 'preprocessing_details': 'Once data were sent from
  - Found: #/preprocessing_strategies/1: {'name': 'Conversion of retinal images to DICOM', 'preprocessing_details': 'All participant images a
  - Found: #/cleaning_strategies/0: {'name': 'Quality control at data entry and acquisition', 'cleaning_details': "Clinical data outside
  - Found: #/cleaning_strategies/1: {'name': 'Site data manager quality control before upload', 'cleaning_details': 'The Data Manager at
- ❌ **Software and Tools Documented**
  - Applicability: unknown; processing_software: not declared; retained in the denominator
  - Fields checked: software_and_tools
- ✅ **External Standards, Resources, and Imputation Protocols**
  - Applicability: applicable; This item applies to every dataset
  - Found: #/external_resources/0: {'name': 'AI-READI dataset documentation', 'description': 'The dataset is self-contained but does re
  - Found: #/external_resources/1: {'name': 'AI-READI project website', 'external_resources': ['https://aireadi.org/']}
  - Found: #/conforms_to: Clinical Dataset Structure (CDS) v0.1.1
  - Found: #/distributions/0/conforms_to_standard/0: WFDB
  - Found: #/distributions/0/conforms_to_standard/1: CDS
  - Found: #/distributions/2/conforms_to_standard/0: OMOP_CDM
  - Found: #/distributions/2/conforms_to_standard/1: CDS
  - Found: #/distributions/4/conforms_to_standard/0: ESDS
  - Found: #/distributions/4/conforms_to_standard/1: CDS
  - Found: #/distributions/6/conforms_to_standard/0: DICOM
  - Found: #/distributions/6/conforms_to_standard/1: CDS
  - Found: #/distributions/8/conforms_to_standard/0: DICOM
  - Found: #/distributions/8/conforms_to_standard/1: CDS
  - Found: #/distributions/10/conforms_to_standard/0: DICOM
  - Found: #/distributions/10/conforms_to_standard/1: CDS
  - Found: #/distributions/12/conforms_to_standard/0: DICOM
  - Found: #/distributions/12/conforms_to_standard/1: CDS
  - Found: #/distributions/14/conforms_to_standard/0: OPEN_MHEALTH
  - Found: #/distributions/14/conforms_to_standard/1: CDS
  - Found: #/distributions/16/conforms_to_standard/0: OPEN_MHEALTH
  - Found: #/distributions/16/conforms_to_standard/1: CDS

#### 9. Dataset Evaluation and Limitations Disclosure

Does the metadata communicate known risks, biases, or dataset limitations?

- ✅ **Known Limitations Documented**
  - Applicability: applicable; This item applies to every dataset
  - Found: #/known_limitations/0: {'name': 'English-language requirement', 'limitation_description': 'Requiring that eligible particip
  - Found: #/known_limitations/1: {'name': 'Urban and hospital-based recruitment', 'limitation_description': 'Factors influencing the 
  - Found: #/known_limitations/2: {'name': 'Races/ethnicities not included', 'limitation_type': 'representativeness_limitation', 'limi
  - Found: #/known_limitations/3: {'name': 'Balanced distribution across groups may not have been achieved', 'limitation_description':
- ✅ **Biases Categorized Using Standard Taxonomy (RAI-aligned)**
  - Applicability: applicable; This item applies to every dataset
  - Found: #/known_biases/0: {'bias_type': 'selection_bias', 'bias_description': 'Participants are volunteers; therefore, there i
- ✅ **Data Anomalies and Quality Issues Noted**
  - Applicability: applicable; This item applies to every dataset
  - Found: #/anomalies/0: {'name': 'Survey data', 'anomaly_details': 'In cases of survey data, skipped questions or incomplete
  - Found: #/anomalies/1: {'name': 'Wearable data', 'anomaly_details': 'In cases of using wearables, improper use and technica
  - Found: #/anomalies/2: {'name': 'Imaging data', 'anomaly_details': 'In cases of imaging data, patient uncooperation, noise 
- ✅ **Sensitive Content and Warnings Provided**
  - Applicability: applicable; This item applies to every dataset
  - Found: #/sensitive_elements/0: {'sensitive_elements_present': False, 'sensitivity_details': 'The public dataset will not contain da
  - Found: #/content_warnings/0: {'content_warnings_present': False}
- ✅ **Ethical Review and Social Impact Analysis**
  - Applicability: applicable; This item applies to every dataset
  - Found: #/ethical_reviews/0: {'reviewing_organization': 'Institutional Review Board (IRB) of the University of Washington', 'revi
  - Found: #/future_use_impacts/0: {'impact_details': "To the extent of the creators' knowledge, no uses of the dataset are currently a

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
  - Found: #/distributions/0/conforms_to_standard/0: WFDB
  - Found: #/distributions/0/conforms_to_standard/1: CDS
  - Found: #/distributions/2/conforms_to_standard/0: OMOP_CDM
  - Found: #/distributions/2/conforms_to_standard/1: CDS
  - Found: #/distributions/4/conforms_to_standard/0: ESDS
  - Found: #/distributions/4/conforms_to_standard/1: CDS
  - Found: #/distributions/6/conforms_to_standard/0: DICOM
  - Found: #/distributions/6/conforms_to_standard/1: CDS
  - Found: #/distributions/8/conforms_to_standard/0: DICOM
  - Found: #/distributions/8/conforms_to_standard/1: CDS
  - Found: #/distributions/10/conforms_to_standard/0: DICOM
  - Found: #/distributions/10/conforms_to_standard/1: CDS
  - Found: #/distributions/12/conforms_to_standard/0: DICOM
  - Found: #/distributions/12/conforms_to_standard/1: CDS
  - Found: #/distributions/14/conforms_to_standard/0: OPEN_MHEALTH
  - Found: #/distributions/14/conforms_to_standard/1: CDS
  - Found: #/distributions/16/conforms_to_standard/0: OPEN_MHEALTH
  - Found: #/distributions/16/conforms_to_standard/1: CDS
- ✅ **Outreach Materials and Documentation Links**
  - Applicability: unknown; shared_dataset: not declared; retained in the denominator
  - Found: #/external_resources/0: {'name': 'AI-READI dataset documentation', 'description': 'The dataset is self-contained but does re
  - Found: #/external_resources/1: {'name': 'AI-READI project website', 'external_resources': ['https://aireadi.org/']}
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
