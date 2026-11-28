# Detailed Evaluation: VOICE - CLAUDECODE_RELEASE_CORE

Evaluated: 2026-11-25T19:12:48.984229
File: `data/d4d_concatenated/claudecode_release_core/2026-11-25c_claude-fable-5-2-claudecode-generic-v9_rep3/VOICE_d4d_core.yaml`

Instrument: `b38117d96e73987f236d4d3d47da5b84a952401537f9a2ae4d2c44bf981fc064`
Applicability context: `fca403729b83dda36a67c4b749455b0fd864ba992e0e40b9a0f5c65bc039bfad`
Scope: single_dataset
## Overall Scores

- **Rubric10**: 42.0/50 (84.0%)
- **Rubric20**: 62.0/88 (70.5%)

## Rubric10 Element Scores

| ID | Element | Score | Details |
|----|---------|-------|---------|
| 1 | Dataset Discovery and Identification | 5/5 | 5/5 applicable sub-elements present; 0 N/A |
| 2 | Dataset Access and Retrieval | 4/5 | 4/5 applicable sub-elements present; 0 N/A |
| 3 | Data Reuse and Interoperability | 4/5 | 4/5 applicable sub-elements present; 0 N/A |
| 4 | Ethical Use and Privacy Safeguards | 3/5 | 3/5 applicable sub-elements present; 0 N/A |
| 5 | Data Composition and Structure | 4/5 | 4/5 applicable sub-elements present; 0 N/A |
| 6 | Data Provenance and Version Tracking | 4/5 | 4/5 applicable sub-elements present; 0 N/A |
| 7 | Scientific Motivation and Funding Transparency | 5/5 | 5/5 applicable sub-elements present; 0 N/A |
| 8 | Technical Transparency (Data Collection and Processing) | 4/5 | 4/5 applicable sub-elements present; 0 N/A |
| 9 | Dataset Evaluation and Limitations Disclosure | 5/5 | 5/5 applicable sub-elements present; 0 N/A |
| 10 | Cross-Platform and Community Integration | 4/5 | 4/5 applicable sub-elements present; 0 N/A |

### Rubric10 Sub-Element Details


#### 1. Dataset Discovery and Identification

Can a user or system discover and uniquely identify this dataset?

- ✅ **Persistent Identifier (DOI, RRID, or URI)**
  - Applicability: applicable; This item applies to every dataset
  - Found: #/doi: 10.13026/8xbn-nq66
  - Found: #/id: doi:10.13026/37yb-1t42
- ✅ **Dataset Title and Description Completeness**
  - Applicability: applicable; This item applies to every dataset
  - Found: #/title: Bridge2AI-Voice: An ethically-sourced, diverse voice dataset linked to health information
  - Found: #/description: A collection of data derived from voice recordings with corresponding clinical information. Version 
- ✅ **Keywords or Tags for Searchability**
  - Applicability: applicable; This item applies to every dataset
  - Found: #/keywords/0: health
  - Found: #/keywords/1: biomarkers
  - Found: #/keywords/2: bridge2ai
  - Found: #/keywords/3: voice
- ✅ **Landing Page and Resources (page, hierarchical resources)**
  - Applicability: applicable; This item applies to every dataset
  - Found: #/page: https://physionet.org/content/b2ai-voice/3.1.0/
- ✅ **Hierarchical Structure (parent datasets, relationships)**
  - Applicability: applicable; This item applies to every dataset
  - Found: #/related_datasets/0: {'name': 'Bridge2AI-Voice Pediatric Dataset', 'target_dataset': 'https://doi.org/10.13026/mf9s-5r03'

#### 2. Dataset Access and Retrieval

Can the dataset and its associated resources be located, accessed, and downloaded?

- ✅ **Access Policy and IP Restrictions Defined**
  - Applicability: applicable; This item applies to every dataset
  - Found: #/license_and_use_terms: {'license_terms': "Files are licensed under the Bridge2AI Voice Registered Access License. Only cred
- ✅ **Regulatory Compliance and Confidentiality Classification**
  - Applicability: unknown; regulated_access: not declared; retained in the denominator
  - Found: #/regulatory_restrictions: {'confidentiality_level': 'restricted', 'regulatory_restrictions': ['The Data Transfer and Use Agree
- ❌ **Download URL or Platform Link Available**
  - Applicability: applicable; This item applies to every dataset
  - Fields checked: download_url
- ✅ **Distribution Formats and File Types Specified**
  - Applicability: applicable; This item applies to every dataset
  - Found: #/distribution_formats/0: {'name': 'Parquet', 'description': 'Binary files are made available as Parquet, an open-source colum
  - Found: #/distribution_formats/1: {'name': 'Tab-separated values', 'description': 'Plain-text files: the static features and audio qua
  - Found: #/distribution_formats/2: {'name': 'JSON data dictionaries', 'description': 'Each data file is associated with a data dictiona
  - Found: #/distributions/10: {'description': 'One feature per audio recording derived from the raw audio related to quality contr
  - Found: #/distributions/11: {'description': 'Features derived from the raw audio, with one feature per audio recording.', 'forma
  - Found: #/distributions/14: {'format': 'JSON', 'id': 'doi:10.13026/37yb-1t42#phenotype-confounders-confounders.json', 'name': 'c
  - Found: #/distributions/15: {'format': 'TSV', 'id': 'doi:10.13026/37yb-1t42#phenotype-confounders-confounders.tsv', 'name': 'con
  - Found: #/distributions/16: {'format': 'JSON', 'id': 'doi:10.13026/37yb-1t42#phenotype-demographics-demographics.json', 'name': 
  - Found: #/distributions/17: {'format': 'TSV', 'id': 'doi:10.13026/37yb-1t42#phenotype-demographics-demographics.tsv', 'name': 'd
  - Found: #/distributions/18: {'format': 'JSON', 'id': 'doi:10.13026/37yb-1t42#phenotype-diagnosis-airway_stenosis.json', 'name': 
  - Found: #/distributions/19: {'format': 'TSV', 'id': 'doi:10.13026/37yb-1t42#phenotype-diagnosis-airway_stenosis.tsv', 'name': 'a
  - Found: #/distributions/20: {'format': 'JSON', 'id': 'doi:10.13026/37yb-1t42#phenotype-diagnosis-amyotrophic_lateral_sclerosis.j
  - Found: #/distributions/21: {'format': 'TSV', 'id': 'doi:10.13026/37yb-1t42#phenotype-diagnosis-amyotrophic_lateral_sclerosis.ts
  - Found: #/distributions/22: {'format': 'JSON', 'id': 'doi:10.13026/37yb-1t42#phenotype-diagnosis-anxiety.json', 'name': 'anxiety
  - Found: #/distributions/23: {'format': 'TSV', 'id': 'doi:10.13026/37yb-1t42#phenotype-diagnosis-anxiety.tsv', 'name': 'anxiety.t
  - Found: #/distributions/24: {'format': 'JSON', 'id': 'doi:10.13026/37yb-1t42#phenotype-diagnosis-benign_lesions.json', 'name': '
  - Found: #/distributions/25: {'format': 'TSV', 'id': 'doi:10.13026/37yb-1t42#phenotype-diagnosis-benign_lesions.tsv', 'name': 'be
  - Found: #/distributions/26: {'format': 'JSON', 'id': 'doi:10.13026/37yb-1t42#phenotype-diagnosis-bipolar_disorder.json', 'name':
  - Found: #/distributions/27: {'format': 'TSV', 'id': 'doi:10.13026/37yb-1t42#phenotype-diagnosis-bipolar_disorder.tsv', 'name': '
  - Found: #/distributions/28: {'format': 'JSON', 'id': 'doi:10.13026/37yb-1t42#phenotype-diagnosis-cognitive_impairment.json', 'na
  - Found: #/distributions/29: {'format': 'TSV', 'id': 'doi:10.13026/37yb-1t42#phenotype-diagnosis-cognitive_impairment.tsv', 'name
  - Found: #/distributions/30: {'format': 'JSON', 'id': 'doi:10.13026/37yb-1t42#phenotype-diagnosis-control.json', 'name': 'control
  - Found: #/distributions/31: {'format': 'TSV', 'id': 'doi:10.13026/37yb-1t42#phenotype-diagnosis-control.tsv', 'name': 'control.t
  - Found: #/distributions/32: {'format': 'JSON', 'id': 'doi:10.13026/37yb-1t42#phenotype-diagnosis-copd_and_asthma.json', 'name': 
  - Found: #/distributions/33: {'format': 'TSV', 'id': 'doi:10.13026/37yb-1t42#phenotype-diagnosis-copd_and_asthma.tsv', 'name': 'c
  - Found: #/distributions/34: {'format': 'JSON', 'id': 'doi:10.13026/37yb-1t42#phenotype-diagnosis-depression.json', 'name': 'depr
  - Found: #/distributions/35: {'format': 'TSV', 'id': 'doi:10.13026/37yb-1t42#phenotype-diagnosis-depression.tsv', 'name': 'depres
  - Found: #/distributions/36: {'format': 'JSON', 'id': 'doi:10.13026/37yb-1t42#phenotype-diagnosis-glottic_insufficiency.json', 'n
  - Found: #/distributions/37: {'format': 'TSV', 'id': 'doi:10.13026/37yb-1t42#phenotype-diagnosis-glottic_insufficiency.tsv', 'nam
  - Found: #/distributions/38: {'format': 'JSON', 'id': 'doi:10.13026/37yb-1t42#phenotype-diagnosis-laryngeal_cancer.json', 'name':
  - Found: #/distributions/39: {'format': 'TSV', 'id': 'doi:10.13026/37yb-1t42#phenotype-diagnosis-laryngeal_cancer.tsv', 'name': '
  - Found: #/distributions/40: {'format': 'JSON', 'id': 'doi:10.13026/37yb-1t42#phenotype-diagnosis-laryngeal_dystonia.json', 'name
  - Found: #/distributions/41: {'format': 'TSV', 'id': 'doi:10.13026/37yb-1t42#phenotype-diagnosis-laryngeal_dystonia.tsv', 'name':
  - Found: #/distributions/42: {'format': 'JSON', 'id': 'doi:10.13026/37yb-1t42#phenotype-diagnosis-laryngitis.json', 'name': 'lary
  - Found: #/distributions/43: {'format': 'TSV', 'id': 'doi:10.13026/37yb-1t42#phenotype-diagnosis-laryngitis.tsv', 'name': 'laryng
  - Found: #/distributions/44: {'format': 'JSON', 'id': 'doi:10.13026/37yb-1t42#phenotype-diagnosis-muscle_tension_dysphonia.json',
  - Found: #/distributions/45: {'format': 'TSV', 'id': 'doi:10.13026/37yb-1t42#phenotype-diagnosis-muscle_tension_dysphonia.tsv', '
  - Found: #/distributions/46: {'format': 'JSON', 'id': 'doi:10.13026/37yb-1t42#phenotype-diagnosis-parkinsons_disease.json', 'name
  - Found: #/distributions/47: {'format': 'TSV', 'id': 'doi:10.13026/37yb-1t42#phenotype-diagnosis-parkinsons_disease.tsv', 'name':
  - Found: #/distributions/48: {'format': 'JSON', 'id': 'doi:10.13026/37yb-1t42#phenotype-diagnosis-precancerous_lesions.json', 'na
  - Found: #/distributions/49: {'format': 'TSV', 'id': 'doi:10.13026/37yb-1t42#phenotype-diagnosis-precancerous_lesions.tsv', 'name
  - Found: #/distributions/50: {'format': 'JSON', 'id': 'doi:10.13026/37yb-1t42#phenotype-diagnosis-unexplained_chronic_cough.json'
  - Found: #/distributions/51: {'format': 'TSV', 'id': 'doi:10.13026/37yb-1t42#phenotype-diagnosis-unexplained_chronic_cough.tsv', 
  - Found: #/distributions/52: {'format': 'JSON', 'id': 'doi:10.13026/37yb-1t42#phenotype-diagnosis-unilateral_vocal_fold_paralysis
  - Found: #/distributions/53: {'format': 'TSV', 'id': 'doi:10.13026/37yb-1t42#phenotype-diagnosis-unilateral_vocal_fold_paralysis.
  - Found: #/distributions/54: {'format': 'JSON', 'id': 'doi:10.13026/37yb-1t42#phenotype-enrollment-eligibility.json', 'name': 'el
  - Found: #/distributions/55: {'format': 'TSV', 'id': 'doi:10.13026/37yb-1t42#phenotype-enrollment-eligibility.tsv', 'name': 'elig
  - Found: #/distributions/56: {'format': 'JSON', 'id': 'doi:10.13026/37yb-1t42#phenotype-enrollment-enrollment_form.json', 'name':
  - Found: #/distributions/57: {'format': 'TSV', 'id': 'doi:10.13026/37yb-1t42#phenotype-enrollment-enrollment_form.tsv', 'name': '
  - Found: #/distributions/58: {'format': 'JSON', 'id': 'doi:10.13026/37yb-1t42#phenotype-enrollment-participant.json', 'name': 'pa
  - Found: #/distributions/59: {'format': 'TSV', 'id': 'doi:10.13026/37yb-1t42#phenotype-enrollment-participant.tsv', 'name': 'part
  - Found: #/distributions/60: {'format': 'JSON', 'id': 'doi:10.13026/37yb-1t42#phenotype-questionnaire-adhd_adult.json', 'name': '
  - Found: #/distributions/61: {'format': 'TSV', 'id': 'doi:10.13026/37yb-1t42#phenotype-questionnaire-adhd_adult.tsv', 'name': 'ad
  - Found: #/distributions/62: {'format': 'JSON', 'id': 'doi:10.13026/37yb-1t42#phenotype-questionnaire-custom_affect_scale.json', 
  - Found: #/distributions/63: {'format': 'TSV', 'id': 'doi:10.13026/37yb-1t42#phenotype-questionnaire-custom_affect_scale.tsv', 'n
  - Found: #/distributions/64: {'format': 'JSON', 'id': 'doi:10.13026/37yb-1t42#phenotype-questionnaire-dsm5_adult.json', 'name': '
  - Found: #/distributions/65: {'format': 'TSV', 'id': 'doi:10.13026/37yb-1t42#phenotype-questionnaire-dsm5_adult.tsv', 'name': 'ds
  - Found: #/distributions/66: {'format': 'JSON', 'id': 'doi:10.13026/37yb-1t42#phenotype-questionnaire-dyspnea_index.json', 'name'
  - Found: #/distributions/67: {'format': 'TSV', 'id': 'doi:10.13026/37yb-1t42#phenotype-questionnaire-dyspnea_index.tsv', 'name': 
  - Found: #/distributions/68: {'format': 'JSON', 'id': 'doi:10.13026/37yb-1t42#phenotype-questionnaire-gad7_anxiety.json', 'name':
  - Found: #/distributions/69: {'format': 'TSV', 'id': 'doi:10.13026/37yb-1t42#phenotype-questionnaire-gad7_anxiety.tsv', 'name': '
  - Found: #/distributions/70: {'format': 'JSON', 'id': 'doi:10.13026/37yb-1t42#phenotype-questionnaire-leicester_cough_questionnai
  - Found: #/distributions/71: {'format': 'TSV', 'id': 'doi:10.13026/37yb-1t42#phenotype-questionnaire-leicester_cough_questionnair
  - Found: #/distributions/72: {'format': 'JSON', 'id': 'doi:10.13026/37yb-1t42#phenotype-questionnaire-panas.json', 'name': 'panas
  - Found: #/distributions/73: {'format': 'TSV', 'id': 'doi:10.13026/37yb-1t42#phenotype-questionnaire-panas.tsv', 'name': 'panas.t
  - Found: #/distributions/74: {'format': 'JSON', 'id': 'doi:10.13026/37yb-1t42#phenotype-questionnaire-phq9.json', 'name': 'phq9.j
  - Found: #/distributions/75: {'format': 'TSV', 'id': 'doi:10.13026/37yb-1t42#phenotype-questionnaire-phq9.tsv', 'name': 'phq9.tsv
  - Found: #/distributions/76: {'format': 'JSON', 'id': 'doi:10.13026/37yb-1t42#phenotype-questionnaire-productive_vocabulary.json'
  - Found: #/distributions/77: {'format': 'TSV', 'id': 'doi:10.13026/37yb-1t42#phenotype-questionnaire-productive_vocabulary.tsv', 
  - Found: #/distributions/78: {'format': 'JSON', 'id': 'doi:10.13026/37yb-1t42#phenotype-questionnaire-psychiatric_history.json', 
  - Found: #/distributions/79: {'format': 'TSV', 'id': 'doi:10.13026/37yb-1t42#phenotype-questionnaire-psychiatric_history.tsv', 'n
  - Found: #/distributions/80: {'format': 'JSON', 'id': 'doi:10.13026/37yb-1t42#phenotype-questionnaire-ptsd_adult.json', 'name': '
  - Found: #/distributions/81: {'format': 'TSV', 'id': 'doi:10.13026/37yb-1t42#phenotype-questionnaire-ptsd_adult.tsv', 'name': 'pt
  - Found: #/distributions/82: {'format': 'JSON', 'id': 'doi:10.13026/37yb-1t42#phenotype-questionnaire-vhi10.json', 'name': 'vhi10
  - Found: #/distributions/83: {'format': 'TSV', 'id': 'doi:10.13026/37yb-1t42#phenotype-questionnaire-vhi10.tsv', 'name': 'vhi10.t
  - Found: #/distributions/84: {'format': 'JSON', 'id': 'doi:10.13026/37yb-1t42#phenotype-questionnaire-voice_perception.json', 'na
  - Found: #/distributions/85: {'format': 'TSV', 'id': 'doi:10.13026/37yb-1t42#phenotype-questionnaire-voice_perception.tsv', 'name
  - Found: #/distributions/86: {'format': 'JSON', 'id': 'doi:10.13026/37yb-1t42#phenotype-task-acoustic_task.json', 'name': 'acoust
  - Found: #/distributions/87: {'format': 'TSV', 'id': 'doi:10.13026/37yb-1t42#phenotype-task-acoustic_task.tsv', 'name': 'acoustic
  - Found: #/distributions/88: {'format': 'JSON', 'id': 'doi:10.13026/37yb-1t42#phenotype-task-harvard_sentences.json', 'name': 'ha
  - Found: #/distributions/89: {'format': 'TSV', 'id': 'doi:10.13026/37yb-1t42#phenotype-task-harvard_sentences.tsv', 'name': 'harv
  - Found: #/distributions/90: {'format': 'JSON', 'id': 'doi:10.13026/37yb-1t42#phenotype-task-random_item_generation.json', 'name'
  - Found: #/distributions/91: {'format': 'TSV', 'id': 'doi:10.13026/37yb-1t42#phenotype-task-random_item_generation.tsv', 'name': 
  - Found: #/distributions/92: {'format': 'JSON', 'id': 'doi:10.13026/37yb-1t42#phenotype-task-recording.json', 'name': 'recording.
  - Found: #/distributions/93: {'format': 'TSV', 'id': 'doi:10.13026/37yb-1t42#phenotype-task-recording.tsv', 'name': 'recording.ts
  - Found: #/distributions/94: {'format': 'JSON', 'id': 'doi:10.13026/37yb-1t42#phenotype-task-session.json', 'name': 'session.json
  - Found: #/distributions/95: {'format': 'TSV', 'id': 'doi:10.13026/37yb-1t42#phenotype-task-session.tsv', 'name': 'session.tsv', 
  - Found: #/distributions/96: {'format': 'JSON', 'id': 'doi:10.13026/37yb-1t42#phenotype-task-stroop.json', 'name': 'stroop.json',
  - Found: #/distributions/97: {'format': 'TSV', 'id': 'doi:10.13026/37yb-1t42#phenotype-task-stroop.tsv', 'name': 'stroop.tsv', 'p
  - Found: #/distributions/98: {'format': 'JSON', 'id': 'doi:10.13026/37yb-1t42#phenotype-task-winograd.json', 'name': 'winograd.js
  - Found: #/distributions/99: {'format': 'TSV', 'id': 'doi:10.13026/37yb-1t42#phenotype-task-winograd.tsv', 'name': 'winograd.tsv'
  - Found: #/distributions/10/format: TSV
  - Found: #/distributions/11/format: TSV
  - Found: #/distributions/14/format: JSON
  - Found: #/distributions/15/format: TSV
  - Found: #/distributions/16/format: JSON
  - Found: #/distributions/17/format: TSV
  - Found: #/distributions/18/format: JSON
  - Found: #/distributions/19/format: TSV
  - Found: #/distributions/20/format: JSON
  - Found: #/distributions/21/format: TSV
  - Found: #/distributions/22/format: JSON
  - Found: #/distributions/23/format: TSV
  - Found: #/distributions/24/format: JSON
  - Found: #/distributions/25/format: TSV
  - Found: #/distributions/26/format: JSON
  - Found: #/distributions/27/format: TSV
  - Found: #/distributions/28/format: JSON
  - Found: #/distributions/29/format: TSV
  - Found: #/distributions/30/format: JSON
  - Found: #/distributions/31/format: TSV
  - Found: #/distributions/32/format: JSON
  - Found: #/distributions/33/format: TSV
  - Found: #/distributions/34/format: JSON
  - Found: #/distributions/35/format: TSV
  - Found: #/distributions/36/format: JSON
  - Found: #/distributions/37/format: TSV
  - Found: #/distributions/38/format: JSON
  - Found: #/distributions/39/format: TSV
  - Found: #/distributions/40/format: JSON
  - Found: #/distributions/41/format: TSV
  - Found: #/distributions/42/format: JSON
  - Found: #/distributions/43/format: TSV
  - Found: #/distributions/44/format: JSON
  - Found: #/distributions/45/format: TSV
  - Found: #/distributions/46/format: JSON
  - Found: #/distributions/47/format: TSV
  - Found: #/distributions/48/format: JSON
  - Found: #/distributions/49/format: TSV
  - Found: #/distributions/50/format: JSON
  - Found: #/distributions/51/format: TSV
  - Found: #/distributions/52/format: JSON
  - Found: #/distributions/53/format: TSV
  - Found: #/distributions/54/format: JSON
  - Found: #/distributions/55/format: TSV
  - Found: #/distributions/56/format: JSON
  - Found: #/distributions/57/format: TSV
  - Found: #/distributions/58/format: JSON
  - Found: #/distributions/59/format: TSV
  - Found: #/distributions/60/format: JSON
  - Found: #/distributions/61/format: TSV
  - Found: #/distributions/62/format: JSON
  - Found: #/distributions/63/format: TSV
  - Found: #/distributions/64/format: JSON
  - Found: #/distributions/65/format: TSV
  - Found: #/distributions/66/format: JSON
  - Found: #/distributions/67/format: TSV
  - Found: #/distributions/68/format: JSON
  - Found: #/distributions/69/format: TSV
  - Found: #/distributions/70/format: JSON
  - Found: #/distributions/71/format: TSV
  - Found: #/distributions/72/format: JSON
  - Found: #/distributions/73/format: TSV
  - Found: #/distributions/74/format: JSON
  - Found: #/distributions/75/format: TSV
  - Found: #/distributions/76/format: JSON
  - Found: #/distributions/77/format: TSV
  - Found: #/distributions/78/format: JSON
  - Found: #/distributions/79/format: TSV
  - Found: #/distributions/80/format: JSON
  - Found: #/distributions/81/format: TSV
  - Found: #/distributions/82/format: JSON
  - Found: #/distributions/83/format: TSV
  - Found: #/distributions/84/format: JSON
  - Found: #/distributions/85/format: TSV
  - Found: #/distributions/86/format: JSON
  - Found: #/distributions/87/format: TSV
  - Found: #/distributions/88/format: JSON
  - Found: #/distributions/89/format: TSV
  - Found: #/distributions/90/format: JSON
  - Found: #/distributions/91/format: TSV
  - Found: #/distributions/92/format: JSON
  - Found: #/distributions/93/format: TSV
  - Found: #/distributions/94/format: JSON
  - Found: #/distributions/95/format: TSV
  - Found: #/distributions/96/format: JSON
  - Found: #/distributions/97/format: TSV
  - Found: #/distributions/98/format: JSON
  - Found: #/distributions/99/format: TSV
  - Found: #/distribution_formats/0/format: Parquet
  - Found: #/distribution_formats/1/format: TSV
  - Found: #/distribution_formats/2/format: JSON
- ✅ **Related Datasets and External Resources Linked**
  - Applicability: applicable; This item applies to every dataset
  - Found: #/related_datasets/0: {'name': 'Bridge2AI-Voice Pediatric Dataset', 'target_dataset': 'https://doi.org/10.13026/mf9s-5r03'
  - Found: #/external_resources/0: {'name': 'REDCap data dictionary and data acquisition protocols', 'description': 'The supporting RED
  - Found: #/external_resources/1: {'name': 'Protocol development publication', 'description': 'Developing Multi-Disorder Voice Protoco
  - Found: #/external_resources/2: {'name': 'Project documentation', 'description': 'Project website and documentation, with the source

#### 3. Data Reuse and Interoperability

Is sufficient information provided to reuse and integrate the dataset with others?
Note: Evaluate whether the dataset is designed for integration with similar datasets, including: common identifiers for cross-dataset linking, standardized formats for data harmonization, and documented integration procedures.


- ✅ **License Terms Allow Reuse**
  - Applicability: unknown; shared_dataset: not declared; retained in the denominator
  - Found: #/license_and_use_terms: {'license_terms': "Files are licensed under the Bridge2AI Voice Registered Access License. Only cred
- ✅ **Data Formats Are Standardized (encoding, format)**
  - Applicability: unknown; shared_dataset: not declared; retained in the denominator
  - Found: #/distributions/10/format: TSV
  - Found: #/distributions/11/format: TSV
  - Found: #/distributions/14/format: JSON
  - Found: #/distributions/15/format: TSV
  - Found: #/distributions/16/format: JSON
  - Found: #/distributions/17/format: TSV
  - Found: #/distributions/18/format: JSON
  - Found: #/distributions/19/format: TSV
  - Found: #/distributions/20/format: JSON
  - Found: #/distributions/21/format: TSV
  - Found: #/distributions/22/format: JSON
  - Found: #/distributions/23/format: TSV
  - Found: #/distributions/24/format: JSON
  - Found: #/distributions/25/format: TSV
  - Found: #/distributions/26/format: JSON
  - Found: #/distributions/27/format: TSV
  - Found: #/distributions/28/format: JSON
  - Found: #/distributions/29/format: TSV
  - Found: #/distributions/30/format: JSON
  - Found: #/distributions/31/format: TSV
  - Found: #/distributions/32/format: JSON
  - Found: #/distributions/33/format: TSV
  - Found: #/distributions/34/format: JSON
  - Found: #/distributions/35/format: TSV
  - Found: #/distributions/36/format: JSON
  - Found: #/distributions/37/format: TSV
  - Found: #/distributions/38/format: JSON
  - Found: #/distributions/39/format: TSV
  - Found: #/distributions/40/format: JSON
  - Found: #/distributions/41/format: TSV
  - Found: #/distributions/42/format: JSON
  - Found: #/distributions/43/format: TSV
  - Found: #/distributions/44/format: JSON
  - Found: #/distributions/45/format: TSV
  - Found: #/distributions/46/format: JSON
  - Found: #/distributions/47/format: TSV
  - Found: #/distributions/48/format: JSON
  - Found: #/distributions/49/format: TSV
  - Found: #/distributions/50/format: JSON
  - Found: #/distributions/51/format: TSV
  - Found: #/distributions/52/format: JSON
  - Found: #/distributions/53/format: TSV
  - Found: #/distributions/54/format: JSON
  - Found: #/distributions/55/format: TSV
  - Found: #/distributions/56/format: JSON
  - Found: #/distributions/57/format: TSV
  - Found: #/distributions/58/format: JSON
  - Found: #/distributions/59/format: TSV
  - Found: #/distributions/60/format: JSON
  - Found: #/distributions/61/format: TSV
  - Found: #/distributions/62/format: JSON
  - Found: #/distributions/63/format: TSV
  - Found: #/distributions/64/format: JSON
  - Found: #/distributions/65/format: TSV
  - Found: #/distributions/66/format: JSON
  - Found: #/distributions/67/format: TSV
  - Found: #/distributions/68/format: JSON
  - Found: #/distributions/69/format: TSV
  - Found: #/distributions/70/format: JSON
  - Found: #/distributions/71/format: TSV
  - Found: #/distributions/72/format: JSON
  - Found: #/distributions/73/format: TSV
  - Found: #/distributions/74/format: JSON
  - Found: #/distributions/75/format: TSV
  - Found: #/distributions/76/format: JSON
  - Found: #/distributions/77/format: TSV
  - Found: #/distributions/78/format: JSON
  - Found: #/distributions/79/format: TSV
  - Found: #/distributions/80/format: JSON
  - Found: #/distributions/81/format: TSV
  - Found: #/distributions/82/format: JSON
  - Found: #/distributions/83/format: TSV
  - Found: #/distributions/84/format: JSON
  - Found: #/distributions/85/format: TSV
  - Found: #/distributions/86/format: JSON
  - Found: #/distributions/87/format: TSV
  - Found: #/distributions/88/format: JSON
  - Found: #/distributions/89/format: TSV
  - Found: #/distributions/90/format: JSON
  - Found: #/distributions/91/format: TSV
  - Found: #/distributions/92/format: JSON
  - Found: #/distributions/93/format: TSV
  - Found: #/distributions/94/format: JSON
  - Found: #/distributions/95/format: TSV
  - Found: #/distributions/96/format: JSON
  - Found: #/distributions/97/format: TSV
  - Found: #/distributions/98/format: JSON
  - Found: #/distributions/99/format: TSV
  - Found: #/distribution_formats/0/format: Parquet
  - Found: #/distribution_formats/1/format: TSV
  - Found: #/distribution_formats/2/format: JSON
- ✅ **Schema or Ontology Conformance Stated**
  - Applicability: unknown; shared_dataset: not declared; retained in the denominator
  - Found: #/conforms_to: Brain Imaging Data Structure v1.9.0
  - Found: #/conforms_to_schema: src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml
- ❌ **Variable Metadata with Identifiers Defined**
  - Applicability: unknown; shared_dataset: not declared; retained in the denominator
  - Fields checked: variables
- ✅ **Use Guidance Provided (intended, prohibited uses)**
  - Applicability: applicable; This item applies to every dataset
  - Found: #/intended_uses/0: {'examples': ['AI model pretraining', 'AI model fine-tuning', 'AI model benchmarking', 'AI model val
  - Found: #/prohibited_uses/0: {'name': 'Re-identification', 'description': 'The dataset is not to be used to attempt to re-identif
  - Found: #/prohibited_uses/1: {'name': 'Harm or stigmatization', 'description': 'The dataset is not to be used for any purpose tha
  - Found: #/prohibited_uses/2: {'name': 'Restricting access through intellectual property', 'description': 'Intellectual property p
  - Found: #/prohibited_uses/3: {'name': 'Sale of the data', 'description': 'Sale of all or part of the data on any media is not per
  - Found: #/prohibited_uses/4: {'name': 'Contacting data subjects', 'description': 'A recipient of data under the Data Transfer and
  - Found: #/discouraged_uses/0: {'discouragement_details': 'The dataset should not be used for non-research applications, such as hi

#### 4. Ethical Use and Privacy Safeguards

Does the dataset document the ethical oversight, privacy, consent and safeguards that apply to its subjects and governance context? Equivalent local ethics and regulatory frameworks are accepted; HIPAA or an IRB is not a universal requirement.

- ✅ **IRB or Ethics Review and Data Protection Impact**
  - Applicability: unknown; any: human_subjects: not declared; retained in the denominator; regulated_access: not declared; retained in the denominator
  - Found: #/ethical_reviews/0: {'reviewing_organization': 'University of South Florida Institutional Review Board', 'review_details
  - Found: #/ethical_reviews/1: {'review_details': 'The study protocol states that the Canadian institutions (Mount Sinai Hospital, 
  - Found: #/human_subject_research: {'involves_human_subjects': True, 'irb_approval': ['Data collection and sharing was approved by the 
- ✅ **Deidentification Method Described**
  - Applicability: unknown; any: human_subjects: not declared; retained in the denominator; regulated_access: not declared; retained in the denominator
  - Found: #/is_deidentified: {'identifiable_elements_present': False, 'method': 'HIPAA Safe Harbor', 'identifiers_removed': 'HIPA
- ❌ **Privacy Protections and Re-identification Risk Assessment**
  - Applicability: unknown; human_subjects: not declared; retained in the denominator
  - Fields checked: participant_privacy, reidentification_risk
- ✅ **Informed Consent Obtained from Participants**
  - Applicability: unknown; human_subjects: not declared; retained in the denominator
  - Found: #/informed_consent/0: {'consent_obtained': True, 'consent_type': 'Prospective informed consent. The study protocol provide
- ❌ **Vulnerable Populations and Compensation Documented**
  - Applicability: unknown; human_subjects: not declared; retained in the denominator
  - Fields checked: vulnerable_populations, participant_compensation

#### 5. Data Composition and Structure

Can the dataset's structure, modality, and population be understood from metadata?

- ✅ **Cohort or Subpopulations Characteristics Described**
  - Applicability: applicable; This item applies to every dataset
  - Found: #/subpopulations/0: {'subpopulation_elements_present': True, 'identification': 'Age, gender, sex, ethnicity and socioeco
- ✅ **Number of Instances or Samples Reported**
  - Applicability: applicable; This item applies to every dataset
  - Found: #/instances/0: {'name': 'Participants', 'instance_type': 'person (study participant)', 'description': 'Each instanc
- ❌ **Variable-Level Metadata, Tabular Flag, and Data Splits**
  - Applicability: applicable; This item applies to every dataset
  - Fields checked: variables, is_tabular, is_data_split, is_subpopulation
- ✅ **Data Topics or Conditions Represented**
  - Applicability: applicable; This item applies to every dataset
  - Found: #/instances/0: {'name': 'Participants', 'instance_type': 'person (study participant)', 'description': 'Each instanc
- ✅ **Data Quality, Anomalies, and Missing Data Documented**
  - Applicability: applicable; This item applies to every dataset
  - Found: #/anomalies/0: {'anomaly_details': 'Different sites have different collection configurations, and the collection pr
  - Found: #/anomalies/1: {'anomaly_details': 'Confounding factors that might be present in the data: noise artifacts, variati
  - Found: #/anomalies/2: {'anomaly_details': 'As participants may have repeated visits, there may be more than one row per pa
  - Found: #/sampling_strategies/0: {'is_sample': True, 'is_random': False, 'is_representative': False, 'source_data': 'A larger, ongoin
  - Found: #/missing_data_documentation/0: {'description': 'The dataset has been audited internally for missingness and consistency by the data
  - Found: #/missing_data_documentation/1: {'missing_data_patterns': 'Spectrograms, Mel spectrograms, MFC coefficients, PPGs, and EMAs for sens
  - Found: #/missing_data_documentation/2: {'missing_data_patterns': 'Phenotype data files only contain rows for a participant if at least one 

#### 6. Data Provenance and Version Tracking

Can a user determine dataset versions, update history, and provenance?

- ✅ **Dataset Version Number Provided**
  - Applicability: unknown; shared_dataset: not declared; retained in the denominator
  - Found: #/version: 3.1.0
- ✅ **Version Access Methods Documented**
  - Applicability: unknown; shared_dataset: not declared; retained in the denominator
  - Found: #/version_access: {'latest_version_doi': 'doi:10.13026/37yb-1t42', 'versions_available': ['1.0 (Health Data Nexus, htt
- ✅ **Change Descriptions and Errata Provided**
  - Applicability: unknown; shared_dataset: not declared; retained in the denominator
  - Found: #/updates: {'frequency': 'Semi-annual (twice a year)', 'update_details': "The dataset is released as static ver
- ✅ **Update Schedule or Frequency Indicated**
  - Applicability: unknown; shared_dataset: not declared; retained in the denominator
  - Found: #/updates: {'frequency': 'Semi-annual (twice a year)', 'update_details': "The dataset is released as static ver
- ❌ **Provenance, Source Derivation, and Raw Data Sources**
  - Applicability: unknown; shared_dataset: not declared; retained in the denominator
  - Fields checked: was_derived_from, release_notes, raw_data_sources

#### 7. Scientific Motivation and Funding Transparency

Does the metadata clearly state why the dataset exists and who funded it?

- ✅ **Motivation or Purpose for Dataset Creation**
  - Applicability: applicable; This item applies to every dataset
  - Found: #/purposes/0: {'response': 'The project seeks to create an ethically sourced flagship dataset to enable future res
- ✅ **Primary Research Objectives or Tasks**
  - Applicability: applicable; This item applies to every dataset
  - Found: #/tasks/0: {'response': 'Development, benchmarking, or validation of clinically applicable machine-learning mod
- ✅ **Funding Sources and Mechanisms Listed**
  - Applicability: applicable; This item applies to every dataset
  - Found: #/funders/0: {'grantor': 'National Institutes of Health Common Fund', 'description': 'The project is funded by th
- ✅ **Grant IDs or Award Numbers Present**
  - Applicability: applicable; This item applies to every dataset
  - Found: #/funders/0: {'grantor': 'National Institutes of Health Common Fund', 'description': 'The project is funded by th
- ✅ **Creators and Acknowledgements Documented**
  - Applicability: applicable; This item applies to every dataset
  - Found: #/creators/0: {'description': 'Co-principal investigator for the project.', 'principal_investigator': {'id': 'doi:
  - Found: #/creators/1: {'name': 'Alexandros Sigaras', 'description': 'Lead investigator named in the project documentation.
  - Found: #/creators/2: {'name': 'Anais Rameau', 'description': 'Lead investigator named in the project documentation.', 'af
  - Found: #/creators/3: {'description': 'Co-principal investigator for the project.', 'principal_investigator': {'id': 'doi:
  - Found: #/creators/4: {'name': 'Maria Powell', 'description': 'Lead investigator named in the project documentation.', 'af
  - Found: #/creators/5: {'name': 'David Dorr', 'description': 'Lead investigator named in the project documentation.', 'affi
  - Found: #/creators/6: {'name': 'Philip Payne', 'description': 'Lead investigator named in the project documentation.', 'af
  - Found: #/creators/7: {'name': 'Vardit Ravitsky', 'description': 'Lead investigator named in the project documentation.', 
  - Found: #/creators/8: {'name': 'Jean-Christophe Bélisle-Pipon', 'description': 'Lead investigator named in the project doc
  - Found: #/creators/9: {'name': 'Ruth Bahr', 'description': 'Lead investigator named in the project documentation.', 'affil
  - Found: #/creators/10: {'name': 'Stephanie Watts'}
  - Found: #/creators/11: {'name': 'Donald Bolser', 'description': 'Lead investigator named in the project documentation.', 'a
  - Found: #/creators/12: {'name': 'Jennifer Siu', 'description': 'Lead investigator named in the project documentation.', 'af
  - Found: #/creators/13: {'name': 'Jordan Lerner-Ellis', 'description': 'Lead investigator named in the project documentation
  - Found: #/creators/14: {'name': 'Frank Rudzicz', 'description': 'Lead investigator named in the project documentation.', 'a
  - Found: #/creators/15: {'name': 'Micah Boyer'}
  - Found: #/creators/16: {'name': 'Yassmeen Abdel-Aty'}
  - Found: #/creators/17: {'name': 'Toufeeq Ahmed Syed'}
  - Found: #/creators/18: {'name': 'James Anibal'}
  - Found: #/creators/19: {'name': 'Dona Amraei'}
  - Found: #/creators/20: {'name': 'Stephen Aradi'}
  - Found: #/creators/21: {'name': 'Kirollos Armosh'}
  - Found: #/creators/22: {'name': 'Ana Sophia Martinez'}
  - Found: #/creators/23: {'name': 'Shaheen Awan'}
  - Found: #/creators/24: {'name': 'Steven Bedrick'}
  - Found: #/creators/25: {'name': 'Helena Beltran'}
  - Found: #/creators/26: {'name': 'Alexander Bernier'}
  - Found: #/creators/27: {'name': 'Moroni Berrios'}
  - Found: #/creators/28: {'name': 'Isaac Bevers'}
  - Found: #/creators/29: {'name': 'Alden Blatter'}
  - Found: #/creators/30: {'name': 'Rahul Brito'}
  - Found: #/creators/31: {'name': 'Amy Brown'}
  - Found: #/creators/32: {'name': 'Johnathan Brown'}
  - Found: #/creators/33: {'name': 'Léo Cadillac'}
  - Found: #/creators/34: {'name': 'Selina Casalino'}
  - Found: #/creators/35: {'name': 'John Costello'}
  - Found: #/creators/36: {'name': 'Abhijeet Dalal'}
  - Found: #/creators/37: {'name': 'Iris De Santiago'}
  - Found: #/creators/38: {'name': 'Enrique Diaz-Ocampo'}
  - Found: #/creators/39: {'name': 'Amanda Doherty-Kirby'}
  - Found: #/creators/40: {'name': 'Mohamed Ebraheem'}
  - Found: #/creators/41: {'name': 'Ellie Eiseman'}
  - Found: #/creators/42: {'name': 'Mahmoud Elmahdy'}
  - Found: #/creators/43: {'name': 'Renee English'}
  - Found: #/creators/44: {'name': 'Emily Evangelista'}
  - Found: #/creators/45: {'name': 'Kenneth Fletcher'}
  - Found: #/creators/46: {'name': 'Hortense Gallois'}
  - Found: #/creators/47: {'name': 'Gaelyn Garrett'}
  - Found: #/creators/48: {'name': 'Alexander Gelbard'}
  - Found: #/creators/49: {'name': 'Omar Ghaffar'}
  - Found: #/creators/50: {'name': 'Amer Ghavanini'}
  - Found: #/creators/51: {'name': 'Anna Goldenberg'}
  - Found: #/creators/52: {'name': 'Karim Hanna'}
  - Found: #/creators/53: {'name': 'William Hersh'}
  - Found: #/creators/54: {'name': 'Jennifer Jain'}
  - Found: #/creators/55: {'name': 'Lochana Jayachandran'}
  - Found: #/creators/56: {'name': 'Kaley Jenney'}
  - Found: #/creators/57: {'name': 'Kathy Jenkins'}
  - Found: #/creators/58: {'name': 'Stacy Jo'}
  - Found: #/creators/59: {'name': 'Alistair Johnson'}
  - Found: #/creators/60: {'name': 'Ayush Kalia'}
  - Found: #/creators/61: {'name': 'Megha Kalia'}
  - Found: #/creators/62: {'name': 'Zoha Khawa'}
  - Found: #/creators/63: {'name': 'Kenji Kobayashi'}
  - Found: #/creators/64: {'name': 'Cindy Kostelnik'}
  - Found: #/creators/65: {'name': 'Alisa Krause'}
  - Found: #/creators/66: {'name': 'Andrea Krussel'}
  - Found: #/creators/67: {'name': 'Elisa Lapadula'}
  - Found: #/creators/68: {'name': 'Genelle Leo'}
  - Found: #/creators/69: {'name': 'Justin Levinsky'}
  - Found: #/creators/70: {'name': 'Chloe Loewith'}
  - Found: #/creators/71: {'name': 'Radhika Mahajan'}
  - Found: #/creators/72: {'name': 'Vrishni Maharaj'}
  - Found: #/creators/73: {'name': 'Siyu Miao'}
  - Found: #/creators/74: {'name': 'LeAnn Michaels'}
  - Found: #/creators/75: {'name': 'Matthew Mifsud'}
  - Found: #/creators/76: {'name': 'Marian Mikhael'}
  - Found: #/creators/77: {'name': 'Elijah Moothedan'}
  - Found: #/creators/78: {'name': 'Yosef Nafii'}
  - Found: #/creators/79: {'name': 'Tempestt Neal'}
  - Found: #/creators/80: {'name': 'Karlee Newberry'}
  - Found: #/creators/81: {'name': 'Evan Ng'}
  - Found: #/creators/82: {'name': 'Christopher Nickel'}
  - Found: #/creators/83: {'name': 'Amanda Peltier'}
  - Found: #/creators/84: {'name': 'Trevor Pharr'}
  - Found: #/creators/85: {'name': 'Michaela Pnacekova'}
  - Found: #/creators/86: {'name': 'Matthew Pontell'}
  - Found: #/creators/87: {'name': 'Jaiden Potter'}
  - Found: #/creators/88: {'name': 'Claire Premi-Bortolotto'}
  - Found: #/creators/89: {'name': 'Parnaz Rafatjou'}
  - Found: #/creators/90: {'name': 'JM Rahman'}
  - Found: #/creators/91: {'name': 'Gayathiri Rajkumar'}
  - Found: #/creators/92: {'name': 'John Ramos'}
  - Found: #/creators/93: {'name': 'Michael de Riesthal'}
  - Found: #/creators/94: {'name': 'Sarah Rohde'}
  - Found: #/creators/95: {'name': 'Jillian Rossi'}
  - Found: #/creators/96: {'name': 'Laurie Russell'}
  - Found: #/creators/97: {'name': 'Samantha Salvi Cruz'}
  - Found: #/creators/98: {'name': 'Joyce Samuel'}
  - Found: #/creators/99: {'name': 'Suketu Shah'}
  - Found: #/creators/100: {'name': 'Ahmed Shawkat'}
  - Found: #/creators/101: {'name': 'Elizabeth Silberholz'}
  - Found: #/creators/102: {'name': 'John Stark'}
  - Found: #/creators/103: {'name': 'Lala Su'}
  - Found: #/creators/104: {'name': 'Shrramana Ganesh Sudhakar'}
  - Found: #/creators/105: {'name': 'Duncan Sutherland'}
  - Found: #/creators/106: {'name': 'Venkata Swarna Mukhi'}
  - Found: #/creators/107: {'name': 'Jeffrey Tang'}
  - Found: #/creators/108: {'name': 'Luka Taylor'}
  - Found: #/creators/109: {'name': 'Jamie Toghranegar'}
  - Found: #/creators/110: {'name': 'Julie Tu'}
  - Found: #/creators/111: {'name': 'Megan Urbano'}
  - Found: #/creators/112: {'name': 'Gavin Victor'}
  - Found: #/creators/113: {'name': 'Kimberly Vinson'}
  - Found: #/creators/114: {'name': 'Jordan Wilke'}
  - Found: #/creators/115: {'name': 'Claire Wilson'}
  - Found: #/creators/116: {'name': 'Madeleine Zanin'}
  - Found: #/creators/117: {'name': 'Xijie Zeng'}
  - Found: #/creators/118: {'name': 'Theresa Zesiewicz'}
  - Found: #/creators/119: {'name': 'Robin Zhao'}
  - Found: #/creators/120: {'name': 'Pantelis Zisimopoulos'}
  - Found: #/creators/121: {'name': 'Satrajit Ghosh', 'description': 'Lead investigator named in the project documentation.', '
  - Found: #/funders/0: {'grantor': 'National Institutes of Health Common Fund', 'description': 'The project is funded by th

#### 8. Technical Transparency (Data Collection and Processing)

Can data collection and processing steps be replicated or understood?
Note: Preprocessing and collection metadata may be represented as structured text descriptions OR as machine-readable provenance graphs (e.g., W3C PROV-O, workflow graphs). Evaluation should check for: (1) structured text descriptions OR (2) graph representations with entity-activity-agent relationships. Both formats are acceptable.


- ✅ **Collection Mechanisms and Settings Described**
  - Applicability: unknown; data_collection: not declared; retained in the denominator
  - Found: #/collection_mechanisms/0: {'name': 'Bridge2AI-Voice App', 'mechanism_details': "Data collection was conducted using a custom a
  - Found: #/collection_mechanisms/1: {'name': 'Recording hardware', 'mechanism_details': 'Data is collected on iPads (9th or 10th generat
- ✅ **Data Acquisition Methods Listed**
  - Applicability: unknown; data_collection: not declared; retained in the denominator
  - Found: #/acquisition_methods/0: {'was_directly_observed': True, 'was_reported_by_subjects': True, 'was_validated_verified': True, 'a
- ✅ **Preprocessing, Cleaning, Labeling, and Annotation Quality**
  - Applicability: unknown; data_processing: not declared; retained in the denominator
  - Found: #/preprocessing_strategies/0: {'name': 'Audio standardization', 'preprocessing_details': 'Raw audio was preprocessed by converting
  - Found: #/preprocessing_strategies/1: {'name': 'Spectrograms', 'preprocessing_details': 'Time-frequency representations were computed usin
  - Found: #/preprocessing_strategies/2: {'name': 'Mel-frequency cepstral coefficients (MFCC)', 'preprocessing_details': '60 MFCCs were extra
  - Found: #/preprocessing_strategies/3: {'name': 'Mel spectrogram', 'preprocessing_details': 'Computed with the same parameters as the spect
  - Found: #/preprocessing_strategies/4: {'name': 'Articulatory features', 'preprocessing_details': 'Using the Speech Articulatory Coding (sp
  - Found: #/preprocessing_strategies/5: {'name': 'Acoustic features', 'preprocessing_details': 'Acoustic features were extracted using OpenS
  - Found: #/preprocessing_strategies/6: {'name': 'Phonetic and prosodic features', 'preprocessing_details': 'Phonetic and prosodic features 
  - Found: #/preprocessing_strategies/7: {'name': 'Phonetic posteriorgrams (ppgs)', 'preprocessing_details': 'A time-varying categorical dist
  - Found: #/preprocessing_strategies/8: {'name': 'Export and feature pipeline', 'preprocessing_details': 'Data were exported and converted f
  - Found: #/preprocessing_strategies/9: {'name': 'Conversion to the Brain Imaging Data Structure', 'preprocessing_details': 'The raw audio f
  - Found: #/cleaning_strategies/0: {'cleaning_details': 'The documentation describes an audit protocol: generate missingness tables; ch
  - Found: #/cleaning_strategies/1: {'cleaning_details': 'For v3.0.0, the documentation states that raw audio transcripts were reviewed,
  - Found: #/labeling_strategies/0: {'data_annotation_protocol': 'Per Bridge2AI Protocols and ICD-10 codes.', 'annotations_per_item': 1,
  - Found: #/machine_annotation_tools/0: {'tools': ['OpenAI Whisper Large unknown'], 'tool_descriptions': "Transcriptions were generated usin
- ❌ **Software and Tools Documented**
  - Applicability: unknown; processing_software: not declared; retained in the denominator
  - Fields checked: software_and_tools
- ✅ **External Standards, Resources, and Imputation Protocols**
  - Applicability: applicable; This item applies to every dataset
  - Found: #/external_resources/0: {'name': 'REDCap data dictionary and data acquisition protocols', 'description': 'The supporting RED
  - Found: #/external_resources/1: {'name': 'Protocol development publication', 'description': 'Developing Multi-Disorder Voice Protoco
  - Found: #/external_resources/2: {'name': 'Project documentation', 'description': 'Project website and documentation, with the source
  - Found: #/conforms_to: Brain Imaging Data Structure v1.9.0

#### 9. Dataset Evaluation and Limitations Disclosure

Does the metadata communicate known risks, biases, or dataset limitations?

- ✅ **Known Limitations Documented**
  - Applicability: applicable; This item applies to every dataset
  - Found: #/known_limitations/0: {'limitation_description': 'The public data releases do not contain an equal distribution of the dis
  - Found: #/known_limitations/1: {'limitation_description': 'Certain aspects of the data (e.g., transcription) were generated using o
  - Found: #/known_limitations/2: {'limitation_description': 'Changes in diagnostic criteria or practices could be a source of distrib
- ✅ **Biases Categorized Using Standard Taxonomy (RAI-aligned)**
  - Applicability: applicable; This item applies to every dataset
  - Found: #/known_biases/0: {'bias_description': 'Groups that have less trust in the medical system or AI, or that are less prox
  - Found: #/known_biases/1: {'bias_description': 'Participants were screened for different disorders based on site, so they also
- ✅ **Data Anomalies and Quality Issues Noted**
  - Applicability: applicable; This item applies to every dataset
  - Found: #/anomalies/0: {'anomaly_details': 'Different sites have different collection configurations, and the collection pr
  - Found: #/anomalies/1: {'anomaly_details': 'Confounding factors that might be present in the data: noise artifacts, variati
  - Found: #/anomalies/2: {'anomaly_details': 'As participants may have repeated visits, there may be more than one row per pa
- ✅ **Sensitive Content and Warnings Provided**
  - Applicability: applicable; This item applies to every dataset
  - Found: #/sensitive_elements/0: {'sensitive_elements_present': True, 'sensitivity_details': 'The dataset includes race information.'
  - Found: #/sensitive_elements/1: {'sensitive_elements_present': True, 'sensitivity_details': 'The dataset includes sexual orientation
  - Found: #/sensitive_elements/2: {'sensitive_elements_present': True, 'sensitivity_details': 'The dataset includes socioeconomic and 
  - Found: #/content_warnings/0: {'warnings': ["The documentation's Healthsheet states that the dataset includes the transcription of
- ✅ **Ethical Review and Social Impact Analysis**
  - Applicability: applicable; This item applies to every dataset
  - Found: #/ethical_reviews/0: {'reviewing_organization': 'University of South Florida Institutional Review Board', 'review_details
  - Found: #/ethical_reviews/1: {'review_details': 'The study protocol states that the Canadian institutions (Mount Sinai Hospital, 
  - Found: #/future_use_impacts/0: {'impact_details': 'The dataset has skews based on disorder category, site, and other demographic fa

#### 10. Cross-Platform and Community Integration

Does the dataset connect to relevant repositories, communities and standards? A shared dataset needs citation or identifier guidance and a named hosting or preservation route appropriate to its domain.

- ❌ **Dataset Published on a Recognized Platform**
  - Applicability: unknown; shared_dataset: not declared; retained in the denominator
  - Fields checked: publisher
- ✅ **Citation and DOI for Cross-referencing**
  - Applicability: unknown; shared_dataset: not declared; retained in the denominator
  - Found: #/doi: 10.13026/8xbn-nq66
- ✅ **Community Standards or Schema Conformance**
  - Applicability: unknown; shared_dataset: not declared; retained in the denominator
  - Found: #/conforms_to: Brain Imaging Data Structure v1.9.0
- ✅ **Outreach Materials and Documentation Links**
  - Applicability: unknown; shared_dataset: not declared; retained in the denominator
  - Found: #/external_resources/0: {'name': 'REDCap data dictionary and data acquisition protocols', 'description': 'The supporting RED
  - Found: #/external_resources/1: {'name': 'Protocol development publication', 'description': 'Developing Multi-Disorder Voice Protoco
  - Found: #/external_resources/2: {'name': 'Project documentation', 'description': 'Project website and documentation, with the source
  - Found: #/page: https://physionet.org/content/b2ai-voice/3.1.0/
- ✅ **Related Datasets with Typed Relationships**
  - Applicability: unknown; shared_dataset: not declared; retained in the denominator
  - Found: #/related_datasets/0: {'name': 'Bridge2AI-Voice Pediatric Dataset', 'target_dataset': 'https://doi.org/10.13026/mf9s-5r03'

## Rubric20 Question Scores


### Structural Completeness

| ID | Question | Score | Status |
|----|----------|-------|--------|
| 1 | Field Completeness | 3.0/5 | ✅ |
| 2 | Entry Length Adequacy | 5.0/5 | ✅ |
| 3 | Keyword Diversity | 3.0/5 | ✅ |
| 4 | File Enumeration and Type Variety | 3.0/5 | ✅ |
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
| 18 | Reusability, Use Guidance, and Social Impact | 5.0/5 | ✅ |
| 19 | Data Integrity, Provenance Graph, and Quality | 3.0/5 | ✅ |
| 20 | Bias Documentation and Responsible AI Alignment | 5.0/5 | ✅ |

Applicability for Q16: applicable; This item applies to every dataset


Applicability for Q17: unknown; shared_dataset: not declared; retained in the denominator


Applicability for Q18: applicable; This item applies to every dataset


Applicability for Q19: applicable; This item applies to every dataset


Applicability for Q20: applicable; This item applies to every dataset
