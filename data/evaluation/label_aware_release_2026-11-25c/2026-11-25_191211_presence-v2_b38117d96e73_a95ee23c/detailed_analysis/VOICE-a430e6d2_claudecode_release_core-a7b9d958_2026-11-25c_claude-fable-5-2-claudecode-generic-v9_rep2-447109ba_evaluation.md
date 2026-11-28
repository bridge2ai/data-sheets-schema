# Detailed Evaluation: VOICE - CLAUDECODE_RELEASE_CORE

Evaluated: 2026-11-25T19:12:47.488457
File: `data/d4d_concatenated/claudecode_release_core/2026-11-25c_claude-fable-5-2-claudecode-generic-v9_rep2/VOICE_d4d_core.yaml`

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
  - Found: #/doi: 10.13026/37yb-1t42
  - Found: #/id: doi:10.13026/37yb-1t42
- ✅ **Dataset Title and Description Completeness**
  - Applicability: applicable; This item applies to every dataset
  - Found: #/title: Bridge2AI-Voice: An ethically-sourced, diverse voice dataset linked to health information
  - Found: #/description: Bridge2AI-Voice is a collection of data derived from voice recordings with corresponding clinical in
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
  - Found: #/related_datasets/0: {'name': 'Bridge2AI-Voice Pediatric Dataset', 'target_dataset': 'doi:10.13026/mf9s-5r03', 'relations

#### 2. Dataset Access and Retrieval

Can the dataset and its associated resources be located, accessed, and downloaded?

- ✅ **Access Policy and IP Restrictions Defined**
  - Applicability: applicable; This item applies to every dataset
  - Found: #/license_and_use_terms: {'license_terms': "Files are released under the Bridge2AI Voice Registered Access License; only cred
  - Found: #/ip_restrictions: {'restrictions': ['Sale of all or part of the Data on any media is not permitted.', 'Users agree not
- ✅ **Regulatory Compliance and Confidentiality Classification**
  - Applicability: unknown; regulated_access: not declared; retained in the denominator
  - Found: #/regulatory_restrictions: {'confidentiality_level': 'restricted', 'other_compliance': 'The Data Transfer and Use Agreement des
- ❌ **Download URL or Platform Link Available**
  - Applicability: applicable; This item applies to every dataset
  - Fields checked: download_url
- ✅ **Distribution Formats and File Types Specified**
  - Applicability: applicable; This item applies to every dataset
  - Found: #/distribution_formats/0: {'format': 'Parquet', 'description': 'Binary files are made available as Parquet, an open-source col
  - Found: #/distribution_formats/1: {'format': 'TSV', 'description': 'Plain-text feature files and the phenotype data files are tab-sepa
  - Found: #/distribution_formats/2: {'format': 'JSON', 'description': 'Each data file has a data dictionary with the same file stem and 
  - Found: #/distributions/10: {'description': 'One feature per audio recording derived from the raw audio related to quality contr
  - Found: #/distributions/11: {'description': 'Features derived from the raw audio, with one feature per audio recording and one r
  - Found: #/distributions/14: {'format': 'JSON', 'id': 'doi:10.13026/37yb-1t42#file-phenotype-confounders-confounders.json', 'medi
  - Found: #/distributions/15: {'format': 'TSV', 'id': 'doi:10.13026/37yb-1t42#file-phenotype-confounders-confounders.tsv', 'media_
  - Found: #/distributions/16: {'format': 'JSON', 'id': 'doi:10.13026/37yb-1t42#file-phenotype-demographics-demographics.json', 'me
  - Found: #/distributions/17: {'format': 'TSV', 'id': 'doi:10.13026/37yb-1t42#file-phenotype-demographics-demographics.tsv', 'medi
  - Found: #/distributions/18: {'format': 'JSON', 'id': 'doi:10.13026/37yb-1t42#file-phenotype-diagnosis-airway_stenosis.json', 'me
  - Found: #/distributions/19: {'format': 'TSV', 'id': 'doi:10.13026/37yb-1t42#file-phenotype-diagnosis-airway_stenosis.tsv', 'medi
  - Found: #/distributions/20: {'format': 'JSON', 'id': 'doi:10.13026/37yb-1t42#file-phenotype-diagnosis-amyotrophic_lateral_sclero
  - Found: #/distributions/21: {'format': 'TSV', 'id': 'doi:10.13026/37yb-1t42#file-phenotype-diagnosis-amyotrophic_lateral_scleros
  - Found: #/distributions/22: {'format': 'JSON', 'id': 'doi:10.13026/37yb-1t42#file-phenotype-diagnosis-anxiety.json', 'media_type
  - Found: #/distributions/23: {'format': 'TSV', 'id': 'doi:10.13026/37yb-1t42#file-phenotype-diagnosis-anxiety.tsv', 'media_type':
  - Found: #/distributions/24: {'format': 'JSON', 'id': 'doi:10.13026/37yb-1t42#file-phenotype-diagnosis-benign_lesions.json', 'med
  - Found: #/distributions/25: {'format': 'TSV', 'id': 'doi:10.13026/37yb-1t42#file-phenotype-diagnosis-benign_lesions.tsv', 'media
  - Found: #/distributions/26: {'format': 'JSON', 'id': 'doi:10.13026/37yb-1t42#file-phenotype-diagnosis-bipolar_disorder.json', 'm
  - Found: #/distributions/27: {'format': 'TSV', 'id': 'doi:10.13026/37yb-1t42#file-phenotype-diagnosis-bipolar_disorder.tsv', 'med
  - Found: #/distributions/28: {'format': 'JSON', 'id': 'doi:10.13026/37yb-1t42#file-phenotype-diagnosis-cognitive_impairment.json'
  - Found: #/distributions/29: {'format': 'TSV', 'id': 'doi:10.13026/37yb-1t42#file-phenotype-diagnosis-cognitive_impairment.tsv', 
  - Found: #/distributions/30: {'format': 'JSON', 'id': 'doi:10.13026/37yb-1t42#file-phenotype-diagnosis-control.json', 'media_type
  - Found: #/distributions/31: {'format': 'TSV', 'id': 'doi:10.13026/37yb-1t42#file-phenotype-diagnosis-control.tsv', 'media_type':
  - Found: #/distributions/32: {'format': 'JSON', 'id': 'doi:10.13026/37yb-1t42#file-phenotype-diagnosis-copd_and_asthma.json', 'me
  - Found: #/distributions/33: {'format': 'TSV', 'id': 'doi:10.13026/37yb-1t42#file-phenotype-diagnosis-copd_and_asthma.tsv', 'medi
  - Found: #/distributions/34: {'format': 'JSON', 'id': 'doi:10.13026/37yb-1t42#file-phenotype-diagnosis-depression.json', 'media_t
  - Found: #/distributions/35: {'format': 'TSV', 'id': 'doi:10.13026/37yb-1t42#file-phenotype-diagnosis-depression.tsv', 'media_typ
  - Found: #/distributions/36: {'format': 'JSON', 'id': 'doi:10.13026/37yb-1t42#file-phenotype-diagnosis-glottic_insufficiency.json
  - Found: #/distributions/37: {'format': 'TSV', 'id': 'doi:10.13026/37yb-1t42#file-phenotype-diagnosis-glottic_insufficiency.tsv',
  - Found: #/distributions/38: {'format': 'JSON', 'id': 'doi:10.13026/37yb-1t42#file-phenotype-diagnosis-laryngeal_cancer.json', 'm
  - Found: #/distributions/39: {'format': 'TSV', 'id': 'doi:10.13026/37yb-1t42#file-phenotype-diagnosis-laryngeal_cancer.tsv', 'med
  - Found: #/distributions/40: {'format': 'JSON', 'id': 'doi:10.13026/37yb-1t42#file-phenotype-diagnosis-laryngeal_dystonia.json', 
  - Found: #/distributions/41: {'format': 'TSV', 'id': 'doi:10.13026/37yb-1t42#file-phenotype-diagnosis-laryngeal_dystonia.tsv', 'm
  - Found: #/distributions/42: {'format': 'JSON', 'id': 'doi:10.13026/37yb-1t42#file-phenotype-diagnosis-laryngitis.json', 'media_t
  - Found: #/distributions/43: {'format': 'TSV', 'id': 'doi:10.13026/37yb-1t42#file-phenotype-diagnosis-laryngitis.tsv', 'media_typ
  - Found: #/distributions/44: {'format': 'JSON', 'id': 'doi:10.13026/37yb-1t42#file-phenotype-diagnosis-muscle_tension_dysphonia.j
  - Found: #/distributions/45: {'format': 'TSV', 'id': 'doi:10.13026/37yb-1t42#file-phenotype-diagnosis-muscle_tension_dysphonia.ts
  - Found: #/distributions/46: {'format': 'JSON', 'id': 'doi:10.13026/37yb-1t42#file-phenotype-diagnosis-parkinsons_disease.json', 
  - Found: #/distributions/47: {'format': 'TSV', 'id': 'doi:10.13026/37yb-1t42#file-phenotype-diagnosis-parkinsons_disease.tsv', 'm
  - Found: #/distributions/48: {'format': 'JSON', 'id': 'doi:10.13026/37yb-1t42#file-phenotype-diagnosis-precancerous_lesions.json'
  - Found: #/distributions/49: {'format': 'TSV', 'id': 'doi:10.13026/37yb-1t42#file-phenotype-diagnosis-precancerous_lesions.tsv', 
  - Found: #/distributions/50: {'format': 'JSON', 'id': 'doi:10.13026/37yb-1t42#file-phenotype-diagnosis-unexplained_chronic_cough.
  - Found: #/distributions/51: {'format': 'TSV', 'id': 'doi:10.13026/37yb-1t42#file-phenotype-diagnosis-unexplained_chronic_cough.t
  - Found: #/distributions/52: {'format': 'JSON', 'id': 'doi:10.13026/37yb-1t42#file-phenotype-diagnosis-unilateral_vocal_fold_para
  - Found: #/distributions/53: {'format': 'TSV', 'id': 'doi:10.13026/37yb-1t42#file-phenotype-diagnosis-unilateral_vocal_fold_paral
  - Found: #/distributions/54: {'format': 'JSON', 'id': 'doi:10.13026/37yb-1t42#file-phenotype-enrollment-eligibility.json', 'media
  - Found: #/distributions/55: {'format': 'TSV', 'id': 'doi:10.13026/37yb-1t42#file-phenotype-enrollment-eligibility.tsv', 'media_t
  - Found: #/distributions/56: {'format': 'JSON', 'id': 'doi:10.13026/37yb-1t42#file-phenotype-enrollment-enrollment_form.json', 'm
  - Found: #/distributions/57: {'format': 'TSV', 'id': 'doi:10.13026/37yb-1t42#file-phenotype-enrollment-enrollment_form.tsv', 'med
  - Found: #/distributions/58: {'format': 'JSON', 'id': 'doi:10.13026/37yb-1t42#file-phenotype-enrollment-participant.json', 'media
  - Found: #/distributions/59: {'format': 'TSV', 'id': 'doi:10.13026/37yb-1t42#file-phenotype-enrollment-participant.tsv', 'media_t
  - Found: #/distributions/60: {'format': 'JSON', 'id': 'doi:10.13026/37yb-1t42#file-phenotype-questionnaire-adhd_adult.json', 'med
  - Found: #/distributions/61: {'format': 'TSV', 'id': 'doi:10.13026/37yb-1t42#file-phenotype-questionnaire-adhd_adult.tsv', 'media
  - Found: #/distributions/62: {'format': 'JSON', 'id': 'doi:10.13026/37yb-1t42#file-phenotype-questionnaire-custom_affect_scale.js
  - Found: #/distributions/63: {'format': 'TSV', 'id': 'doi:10.13026/37yb-1t42#file-phenotype-questionnaire-custom_affect_scale.tsv
  - Found: #/distributions/64: {'format': 'JSON', 'id': 'doi:10.13026/37yb-1t42#file-phenotype-questionnaire-dsm5_adult.json', 'med
  - Found: #/distributions/65: {'format': 'TSV', 'id': 'doi:10.13026/37yb-1t42#file-phenotype-questionnaire-dsm5_adult.tsv', 'media
  - Found: #/distributions/66: {'format': 'JSON', 'id': 'doi:10.13026/37yb-1t42#file-phenotype-questionnaire-dyspnea_index.json', '
  - Found: #/distributions/67: {'format': 'TSV', 'id': 'doi:10.13026/37yb-1t42#file-phenotype-questionnaire-dyspnea_index.tsv', 'me
  - Found: #/distributions/68: {'format': 'JSON', 'id': 'doi:10.13026/37yb-1t42#file-phenotype-questionnaire-gad7_anxiety.json', 'm
  - Found: #/distributions/69: {'format': 'TSV', 'id': 'doi:10.13026/37yb-1t42#file-phenotype-questionnaire-gad7_anxiety.tsv', 'med
  - Found: #/distributions/70: {'format': 'JSON', 'id': 'doi:10.13026/37yb-1t42#file-phenotype-questionnaire-leicester_cough_questi
  - Found: #/distributions/71: {'format': 'TSV', 'id': 'doi:10.13026/37yb-1t42#file-phenotype-questionnaire-leicester_cough_questio
  - Found: #/distributions/72: {'format': 'JSON', 'id': 'doi:10.13026/37yb-1t42#file-phenotype-questionnaire-panas.json', 'media_ty
  - Found: #/distributions/73: {'format': 'TSV', 'id': 'doi:10.13026/37yb-1t42#file-phenotype-questionnaire-panas.tsv', 'media_type
  - Found: #/distributions/74: {'format': 'JSON', 'id': 'doi:10.13026/37yb-1t42#file-phenotype-questionnaire-phq9.json', 'media_typ
  - Found: #/distributions/75: {'format': 'TSV', 'id': 'doi:10.13026/37yb-1t42#file-phenotype-questionnaire-phq9.tsv', 'media_type'
  - Found: #/distributions/76: {'format': 'JSON', 'id': 'doi:10.13026/37yb-1t42#file-phenotype-questionnaire-productive_vocabulary.
  - Found: #/distributions/77: {'format': 'TSV', 'id': 'doi:10.13026/37yb-1t42#file-phenotype-questionnaire-productive_vocabulary.t
  - Found: #/distributions/78: {'format': 'JSON', 'id': 'doi:10.13026/37yb-1t42#file-phenotype-questionnaire-psychiatric_history.js
  - Found: #/distributions/79: {'format': 'TSV', 'id': 'doi:10.13026/37yb-1t42#file-phenotype-questionnaire-psychiatric_history.tsv
  - Found: #/distributions/80: {'format': 'JSON', 'id': 'doi:10.13026/37yb-1t42#file-phenotype-questionnaire-ptsd_adult.json', 'med
  - Found: #/distributions/81: {'format': 'TSV', 'id': 'doi:10.13026/37yb-1t42#file-phenotype-questionnaire-ptsd_adult.tsv', 'media
  - Found: #/distributions/82: {'format': 'JSON', 'id': 'doi:10.13026/37yb-1t42#file-phenotype-questionnaire-vhi10.json', 'media_ty
  - Found: #/distributions/83: {'format': 'TSV', 'id': 'doi:10.13026/37yb-1t42#file-phenotype-questionnaire-vhi10.tsv', 'media_type
  - Found: #/distributions/84: {'format': 'JSON', 'id': 'doi:10.13026/37yb-1t42#file-phenotype-questionnaire-voice_perception.json'
  - Found: #/distributions/85: {'format': 'TSV', 'id': 'doi:10.13026/37yb-1t42#file-phenotype-questionnaire-voice_perception.tsv', 
  - Found: #/distributions/86: {'format': 'JSON', 'id': 'doi:10.13026/37yb-1t42#file-phenotype-task-acoustic_task.json', 'media_typ
  - Found: #/distributions/87: {'format': 'TSV', 'id': 'doi:10.13026/37yb-1t42#file-phenotype-task-acoustic_task.tsv', 'media_type'
  - Found: #/distributions/88: {'format': 'JSON', 'id': 'doi:10.13026/37yb-1t42#file-phenotype-task-harvard_sentences.json', 'media
  - Found: #/distributions/89: {'format': 'TSV', 'id': 'doi:10.13026/37yb-1t42#file-phenotype-task-harvard_sentences.tsv', 'media_t
  - Found: #/distributions/90: {'format': 'JSON', 'id': 'doi:10.13026/37yb-1t42#file-phenotype-task-random_item_generation.json', '
  - Found: #/distributions/91: {'format': 'TSV', 'id': 'doi:10.13026/37yb-1t42#file-phenotype-task-random_item_generation.tsv', 'me
  - Found: #/distributions/92: {'format': 'JSON', 'id': 'doi:10.13026/37yb-1t42#file-phenotype-task-recording.json', 'media_type': 
  - Found: #/distributions/93: {'format': 'TSV', 'id': 'doi:10.13026/37yb-1t42#file-phenotype-task-recording.tsv', 'media_type': 't
  - Found: #/distributions/94: {'format': 'JSON', 'id': 'doi:10.13026/37yb-1t42#file-phenotype-task-session.json', 'media_type': 'a
  - Found: #/distributions/95: {'format': 'TSV', 'id': 'doi:10.13026/37yb-1t42#file-phenotype-task-session.tsv', 'media_type': 'tex
  - Found: #/distributions/96: {'format': 'JSON', 'id': 'doi:10.13026/37yb-1t42#file-phenotype-task-stroop.json', 'media_type': 'ap
  - Found: #/distributions/97: {'format': 'TSV', 'id': 'doi:10.13026/37yb-1t42#file-phenotype-task-stroop.tsv', 'media_type': 'text
  - Found: #/distributions/98: {'format': 'JSON', 'id': 'doi:10.13026/37yb-1t42#file-phenotype-task-winograd.json', 'media_type': '
  - Found: #/distributions/99: {'format': 'TSV', 'id': 'doi:10.13026/37yb-1t42#file-phenotype-task-winograd.tsv', 'media_type': 'te
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
  - Found: #/distributions/10/media_type: text/tab-separated-values
  - Found: #/distributions/11/media_type: text/tab-separated-values
  - Found: #/distributions/14/media_type: application/json
  - Found: #/distributions/15/media_type: text/tab-separated-values
  - Found: #/distributions/16/media_type: application/json
  - Found: #/distributions/17/media_type: text/tab-separated-values
  - Found: #/distributions/18/media_type: application/json
  - Found: #/distributions/19/media_type: text/tab-separated-values
  - Found: #/distributions/20/media_type: application/json
  - Found: #/distributions/21/media_type: text/tab-separated-values
  - Found: #/distributions/22/media_type: application/json
  - Found: #/distributions/23/media_type: text/tab-separated-values
  - Found: #/distributions/24/media_type: application/json
  - Found: #/distributions/25/media_type: text/tab-separated-values
  - Found: #/distributions/26/media_type: application/json
  - Found: #/distributions/27/media_type: text/tab-separated-values
  - Found: #/distributions/28/media_type: application/json
  - Found: #/distributions/29/media_type: text/tab-separated-values
  - Found: #/distributions/30/media_type: application/json
  - Found: #/distributions/31/media_type: text/tab-separated-values
  - Found: #/distributions/32/media_type: application/json
  - Found: #/distributions/33/media_type: text/tab-separated-values
  - Found: #/distributions/34/media_type: application/json
  - Found: #/distributions/35/media_type: text/tab-separated-values
  - Found: #/distributions/36/media_type: application/json
  - Found: #/distributions/37/media_type: text/tab-separated-values
  - Found: #/distributions/38/media_type: application/json
  - Found: #/distributions/39/media_type: text/tab-separated-values
  - Found: #/distributions/40/media_type: application/json
  - Found: #/distributions/41/media_type: text/tab-separated-values
  - Found: #/distributions/42/media_type: application/json
  - Found: #/distributions/43/media_type: text/tab-separated-values
  - Found: #/distributions/44/media_type: application/json
  - Found: #/distributions/45/media_type: text/tab-separated-values
  - Found: #/distributions/46/media_type: application/json
  - Found: #/distributions/47/media_type: text/tab-separated-values
  - Found: #/distributions/48/media_type: application/json
  - Found: #/distributions/49/media_type: text/tab-separated-values
  - Found: #/distributions/50/media_type: application/json
  - Found: #/distributions/51/media_type: text/tab-separated-values
  - Found: #/distributions/52/media_type: application/json
  - Found: #/distributions/53/media_type: text/tab-separated-values
  - Found: #/distributions/54/media_type: application/json
  - Found: #/distributions/55/media_type: text/tab-separated-values
  - Found: #/distributions/56/media_type: application/json
  - Found: #/distributions/57/media_type: text/tab-separated-values
  - Found: #/distributions/58/media_type: application/json
  - Found: #/distributions/59/media_type: text/tab-separated-values
  - Found: #/distributions/60/media_type: application/json
  - Found: #/distributions/61/media_type: text/tab-separated-values
  - Found: #/distributions/62/media_type: application/json
  - Found: #/distributions/63/media_type: text/tab-separated-values
  - Found: #/distributions/64/media_type: application/json
  - Found: #/distributions/65/media_type: text/tab-separated-values
  - Found: #/distributions/66/media_type: application/json
  - Found: #/distributions/67/media_type: text/tab-separated-values
  - Found: #/distributions/68/media_type: application/json
  - Found: #/distributions/69/media_type: text/tab-separated-values
  - Found: #/distributions/70/media_type: application/json
  - Found: #/distributions/71/media_type: text/tab-separated-values
  - Found: #/distributions/72/media_type: application/json
  - Found: #/distributions/73/media_type: text/tab-separated-values
  - Found: #/distributions/74/media_type: application/json
  - Found: #/distributions/75/media_type: text/tab-separated-values
  - Found: #/distributions/76/media_type: application/json
  - Found: #/distributions/77/media_type: text/tab-separated-values
  - Found: #/distributions/78/media_type: application/json
  - Found: #/distributions/79/media_type: text/tab-separated-values
  - Found: #/distributions/80/media_type: application/json
  - Found: #/distributions/81/media_type: text/tab-separated-values
  - Found: #/distributions/82/media_type: application/json
  - Found: #/distributions/83/media_type: text/tab-separated-values
  - Found: #/distributions/84/media_type: application/json
  - Found: #/distributions/85/media_type: text/tab-separated-values
  - Found: #/distributions/86/media_type: application/json
  - Found: #/distributions/87/media_type: text/tab-separated-values
  - Found: #/distributions/88/media_type: application/json
  - Found: #/distributions/89/media_type: text/tab-separated-values
  - Found: #/distributions/90/media_type: application/json
  - Found: #/distributions/91/media_type: text/tab-separated-values
  - Found: #/distributions/92/media_type: application/json
  - Found: #/distributions/93/media_type: text/tab-separated-values
  - Found: #/distributions/94/media_type: application/json
  - Found: #/distributions/95/media_type: text/tab-separated-values
  - Found: #/distributions/96/media_type: application/json
  - Found: #/distributions/97/media_type: text/tab-separated-values
  - Found: #/distributions/98/media_type: application/json
  - Found: #/distributions/99/media_type: text/tab-separated-values
- ✅ **Related Datasets and External Resources Linked**
  - Applicability: applicable; This item applies to every dataset
  - Found: #/related_datasets/0: {'name': 'Bridge2AI-Voice Pediatric Dataset', 'target_dataset': 'doi:10.13026/mf9s-5r03', 'relations
  - Found: #/external_resources/0: {'name': 'REDCap data dictionary, metadata and instrument PDFs', 'external_resources': ['https://git
  - Found: #/external_resources/1: {'name': 'Publication describing protocol development', 'description': 'Developing Multi-Disorder Vo
  - Found: #/external_resources/2: {'name': 'Feasibility study of the data collection application', 'description': 'The Bridge2AI-voice
  - Found: #/external_resources/3: {'name': 'Viewpoint introducing audiomics', 'description': 'Voice as an AI Biomarker of Health—Intro
  - Found: #/external_resources/4: {'name': 'Project documentation', 'description': 'Documentation site of the Voice project and the re
  - Found: #/external_resources/5: {'name': 'Project website', 'external_resources': ['https://b2ai-voice.org/']}

#### 3. Data Reuse and Interoperability

Is sufficient information provided to reuse and integrate the dataset with others?
Note: Evaluate whether the dataset is designed for integration with similar datasets, including: common identifiers for cross-dataset linking, standardized formats for data harmonization, and documented integration procedures.


- ✅ **License Terms Allow Reuse**
  - Applicability: unknown; shared_dataset: not declared; retained in the denominator
  - Found: #/license_and_use_terms: {'license_terms': "Files are released under the Bridge2AI Voice Registered Access License; only cred
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
  - Found: #/intended_uses/0: {'name': 'Research on AI and machine-learning models for healthcare', 'use_category': 'research', 'd
  - Found: #/intended_uses/1: {'name': 'AI model pretraining', 'description': 'The dataset can be used for AI model pretraining.'}
  - Found: #/intended_uses/2: {'name': 'AI model fine-tuning', 'description': 'The dataset can be used for AI model fine-tuning.'}
  - Found: #/intended_uses/3: {'name': 'AI model benchmarking', 'description': 'The dataset can be used for AI model benchmarking.
  - Found: #/intended_uses/4: {'name': 'AI model validation', 'description': 'The dataset can be used for AI model validation.'}
  - Found: #/intended_uses/5: {'name': 'Clinical research through voice biomarkers', 'description': 'The dataset aims to support c
  - Found: #/prohibited_uses/0: {'name': 'Re-identification of research participants', 'description': 'The dataset is not to be used
  - Found: #/prohibited_uses/1: {'name': 'Uses that could cause harm or stigmatization', 'description': 'The dataset is not to be us
  - Found: #/prohibited_uses/2: {'name': 'Contacting data subjects', 'description': 'Under the Data Transfer and Use Agreement, the 
  - Found: #/prohibited_uses/3: {'name': 'Sale of the data', 'description': 'Sale of all or part of the data on any media is not per
  - Found: #/prohibited_uses/4: {'name': 'Disclosure to third parties', 'description': 'Under the Data Transfer and Use Agreement, t
  - Found: #/discouraged_uses/0: {'name': 'Hiring decisions', 'discouragement_details': 'The dataset should not be used for non-resea
  - Found: #/discouraged_uses/1: {'name': 'Insurance premium adjustments', 'discouragement_details': 'The dataset should not be used 
  - Found: #/discouraged_uses/2: {'name': 'Surveillance', 'discouragement_details': 'The dataset should not be used for any form of s

#### 4. Ethical Use and Privacy Safeguards

Does the dataset document the ethical oversight, privacy, consent and safeguards that apply to its subjects and governance context? Equivalent local ethics and regulatory frameworks are accepted; HIPAA or an IRB is not a universal requirement.

- ✅ **IRB or Ethics Review and Data Protection Impact**
  - Applicability: unknown; any: human_subjects: not declared; retained in the denominator; regulated_access: not declared; retained in the denominator
  - Found: #/ethical_reviews/0: {'reviewing_organization': 'University of South Florida Institutional Review Board', 'review_details
  - Found: #/ethical_reviews/1: {'review_details': 'The study protocol states that Canadian institutions do not abide by the single 
  - Found: #/human_subject_research: {'involves_human_subjects': True, 'irb_approval': ['Data collection and sharing was approved by the 
- ✅ **Deidentification Method Described**
  - Applicability: unknown; any: human_subjects: not declared; retained in the denominator; regulated_access: not declared; retained in the denominator
  - Found: #/is_deidentified: {'method': 'HIPAA Safe Harbor', 'identifiers_removed': 'names, geographic locators, date information
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
  - Found: #/subpopulations/0: {'name': 'Voice disorders', 'subpopulation_elements_present': True, 'identification': 'Participants 
  - Found: #/subpopulations/1: {'name': 'Neurological disorders', 'subpopulation_elements_present': True, 'identification': 'Partic
  - Found: #/subpopulations/2: {'name': 'Mood disorders', 'subpopulation_elements_present': True, 'identification': 'Participants s
  - Found: #/subpopulations/3: {'name': 'Respiratory disorders', 'subpopulation_elements_present': True, 'identification': 'Partici
  - Found: #/subpopulations/4: {'name': 'Controls', 'subpopulation_elements_present': True, 'identification': 'The phenotype diagno
  - Found: #/subpopulations/5: {'name': 'Demographic sub-populations', 'subpopulation_elements_present': True, 'identification': 'T
- ✅ **Number of Instances or Samples Reported**
  - Applicability: applicable; This item applies to every dataset
  - Found: #/instances/0: {'name': 'Participant', 'instance_type': 'person (study participant)', 'counts': 833, 'label': True,
  - Found: #/instances/1: {'name': 'Recording', 'instance_type': 'audio recording, represented by features derived from it', '
- ❌ **Variable-Level Metadata, Tabular Flag, and Data Splits**
  - Applicability: applicable; This item applies to every dataset
  - Fields checked: variables, is_tabular, is_data_split, is_subpopulation
- ✅ **Data Topics or Conditions Represented**
  - Applicability: applicable; This item applies to every dataset
  - Found: #/instances/0: {'name': 'Participant', 'instance_type': 'person (study participant)', 'counts': 833, 'label': True,
  - Found: #/instances/1: {'name': 'Recording', 'instance_type': 'audio recording, represented by features derived from it', '
- ✅ **Data Quality, Anomalies, and Missing Data Documented**
  - Applicability: applicable; This item applies to every dataset
  - Found: #/anomalies/0: {'anomaly_details': 'Different sites have different collection configurations. The collection protoc
  - Found: #/anomalies/1: {'anomaly_details': 'As participants may have repeated visits in order to collect data, there may be
  - Found: #/sampling_strategies/0: {'is_sample': True, 'is_random': False, 'is_representative': False, 'source_data': 'A larger, ongoin
  - Found: #/sampling_strategies/1: {'strategies': "Eligibility under the study protocol: being diagnosed and/or treated for a voice, re
  - Found: #/missing_data_documentation/0: {'missing_data_patterns': 'Phenotype data files only contain rows for a participant if at least one 

#### 6. Data Provenance and Version Tracking

Can a user determine dataset versions, update history, and provenance?

- ✅ **Dataset Version Number Provided**
  - Applicability: unknown; shared_dataset: not declared; retained in the denominator
  - Found: #/version: 3.1.0
- ✅ **Version Access Methods Documented**
  - Applicability: unknown; shared_dataset: not declared; retained in the denominator
  - Found: #/version_access: {'latest_version_doi': 'doi:10.13026/37yb-1t42', 'versions_available': ['1.0', '1.1', '2.0.0', '2.0.
- ✅ **Change Descriptions and Errata Provided**
  - Applicability: unknown; shared_dataset: not declared; retained in the denominator
  - Found: #/errata/0: {'erratum_details': 'Version 3.1.0 fixed broken parquet files from the previous release.'}
  - Found: #/errata/1: {'erratum_details': 'Version 2.0.1 made corrections in the authorship list.'}
  - Found: #/errata/2: {'erratum_details': 'Version 2.0 reprocessed spectrograms to fix some minor issues identified in the
  - Found: #/updates: {'frequency': 'Semi-annual (twice a year)', 'update_details': 'The dataset is released as static ver
- ✅ **Update Schedule or Frequency Indicated**
  - Applicability: unknown; shared_dataset: not declared; retained in the denominator
  - Found: #/updates: {'frequency': 'Semi-annual (twice a year)', 'update_details': 'The dataset is released as static ver
- ❌ **Provenance, Source Derivation, and Raw Data Sources**
  - Applicability: unknown; shared_dataset: not declared; retained in the denominator
  - Fields checked: was_derived_from, release_notes, raw_data_sources

#### 7. Scientific Motivation and Funding Transparency

Does the metadata clearly state why the dataset exists and who funded it?

- ✅ **Motivation or Purpose for Dataset Creation**
  - Applicability: applicable; This item applies to every dataset
  - Found: #/purposes/0: {'response': 'The Voice project seeks to create an ethically sourced flagship dataset to enable futu
  - Found: #/purposes/1: {'response': 'The project documentation states that the dataset aims to provide an ethically sourced
  - Found: #/purposes/2: {'response': 'The study protocol states its primary objective as building a large multi-institutiona
- ✅ **Primary Research Objectives or Tasks**
  - Applicability: applicable; This item applies to every dataset
  - Found: #/tasks/0: {'response': 'The project documentation states that the tasks are primarily designed for training ma
  - Found: #/tasks/1: {'response': 'The funded project aims to build predictive models to assist in screening, diagnosis, 
- ✅ **Funding Sources and Mechanisms Listed**
  - Applicability: applicable; This item applies to every dataset
  - Found: #/funders/0: {'name': 'NIH Common Fund Bridge2AI Program', 'grantor': 'NIH Common Fund', 'grants': [{'name': 'Bri
- ✅ **Grant IDs or Award Numbers Present**
  - Applicability: applicable; This item applies to every dataset
  - Found: #/funders/0: {'name': 'NIH Common Fund Bridge2AI Program', 'grantor': 'NIH Common Fund', 'grants': [{'name': 'Bri
- ✅ **Creators and Acknowledgements Documented**
  - Applicability: applicable; This item applies to every dataset
  - Found: #/creators/0: {'name': 'Yael Bensoussan', 'principal_investigator': {'id': 'doi:10.13026/37yb-1t42#person-yael-ben
  - Found: #/creators/1: {'name': 'Alexandros Sigaras', 'affiliations': [{'name': 'Weill Cornell Medicine'}]}
  - Found: #/creators/2: {'name': 'Anais Rameau', 'affiliations': [{'name': 'Weill Cornell Medicine'}]}
  - Found: #/creators/3: {'name': 'Olivier Elemento', 'principal_investigator': {'id': 'doi:10.13026/37yb-1t42#person-olivier
  - Found: #/creators/4: {'name': 'Maria Powell', 'affiliations': [{'name': 'Vanderbilt University Medical Center'}]}
  - Found: #/creators/5: {'name': 'David Dorr', 'affiliations': [{'name': 'Oregon Health & Science University'}]}
  - Found: #/creators/6: {'name': 'Philip Payne', 'affiliations': [{'name': 'Washington University in St. Louis'}]}
  - Found: #/creators/7: {'name': 'Vardit Ravitsky', 'affiliations': [{'name': 'The Hastings Center'}]}
  - Found: #/creators/8: {'name': 'Jean-Christophe Bélisle-Pipon', 'affiliations': [{'name': 'Simon Fraser University'}]}
  - Found: #/creators/9: {'name': 'Ruth Bahr', 'affiliations': [{'name': 'USF Health Morsani College of Medicine'}]}
  - Found: #/creators/10: {'name': 'Stephanie Watts'}
  - Found: #/creators/11: {'name': 'Donald Bolser', 'affiliations': [{'name': 'University of Florida'}], 'source_caveats': 'Th
  - Found: #/creators/12: {'name': 'Jennifer Siu', 'affiliations': [{'name': 'Hospital for Sick Children'}], 'source_caveats':
  - Found: #/creators/13: {'name': 'Jordan Lerner-Ellis', 'affiliations': [{'name': 'Sinai Health'}]}
  - Found: #/creators/14: {'name': 'Frank Rudzicz', 'affiliations': [{'name': 'University of Toronto'}], 'source_caveats': 'Th
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
  - Found: #/creators/121: {'name': 'Satrajit Ghosh', 'affiliations': [{'name': 'Massachusetts Institute of Technology'}]}
  - Found: #/funders/0: {'name': 'NIH Common Fund Bridge2AI Program', 'grantor': 'NIH Common Fund', 'grants': [{'name': 'Bri

#### 8. Technical Transparency (Data Collection and Processing)

Can data collection and processing steps be replicated or understood?
Note: Preprocessing and collection metadata may be represented as structured text descriptions OR as machine-readable provenance graphs (e.g., W3C PROV-O, workflow graphs). Evaluation should check for: (1) structured text descriptions OR (2) graph representations with entity-activity-agent relationships. Both formats are acceptable.


- ✅ **Collection Mechanisms and Settings Described**
  - Applicability: unknown; data_collection: not declared; retained in the denominator
  - Found: #/collection_mechanisms/0: {'name': 'Custom tablet application', 'mechanism_details': 'Data collection was conducted using a cu
  - Found: #/collection_mechanisms/1: {'name': 'Recording hardware', 'mechanism_details': 'Data is collected on iPads (9th or 10th generat
  - Found: #/collection_mechanisms/2: {'name': 'In-clinic collection', 'mechanism_details': 'Data is collected in the clinic with the assi
  - Found: #/collection_mechanisms/3: {'name': 'Acoustic tasks', 'mechanism_details': 'Voice, breathing, cough, and speech data are record
  - Found: #/collection_mechanisms/4: {'name': 'Collection platforms in the study protocol', 'mechanism_details': 'The study protocol stat
- ✅ **Data Acquisition Methods Listed**
  - Applicability: unknown; data_collection: not declared; retained in the denominator
  - Found: #/acquisition_methods/0: {'was_directly_observed': True, 'was_reported_by_subjects': True, 'was_validated_verified': True, 'a
- ✅ **Preprocessing, Cleaning, Labeling, and Annotation Quality**
  - Applicability: unknown; data_processing: not declared; retained in the denominator
  - Found: #/preprocessing_strategies/0: {'name': 'Audio standardization', 'preprocessing_details': 'Raw audio was preprocessed by converting
  - Found: #/preprocessing_strategies/1: {'name': 'Spectrograms', 'preprocessing_details': 'Time-frequency representations were computed usin
  - Found: #/preprocessing_strategies/2: {'name': 'Mel-frequency cepstral coefficients (MFCC)', 'preprocessing_details': '60 Mel-frequency ce
  - Found: #/preprocessing_strategies/3: {'name': 'Mel spectrogram', 'preprocessing_details': 'Mel spectrograms were computed with the same p
  - Found: #/preprocessing_strategies/4: {'name': 'Articulatory features', 'preprocessing_details': 'Using the Speech Articulatory Coding (sp
  - Found: #/preprocessing_strategies/5: {'name': 'Acoustic features', 'preprocessing_details': 'Acoustic features were extracted using OpenS
  - Found: #/preprocessing_strategies/6: {'name': 'Phonetic and prosodic features', 'preprocessing_details': 'Phonetic and prosodic features 
  - Found: #/preprocessing_strategies/7: {'name': 'Phonetic posteriorgrams', 'preprocessing_details': 'Phonetic posteriorgrams, a time-varyin
  - Found: #/preprocessing_strategies/8: {'name': 'Processing toolkits', 'preprocessing_details': 'Data were exported and converted from REDC
  - Found: #/preprocessing_strategies/9: {'name': 'Conversion to the Brain Imaging Data Structure', 'preprocessing_details': 'The raw audio f
  - Found: #/cleaning_strategies/0: {'name': 'Audit protocol', 'cleaning_details': "The project documentation's audit protocol generates
  - Found: #/labeling_strategies/0: {'name': 'Clinical diagnostic labels', 'labeling_details': "Diagnostic labels are the result of a cl
  - Found: #/machine_annotation_tools/0: {'tools': ['OpenAI Whisper Large'], 'tool_descriptions': "Transcriptions were generated using OpenAI
- ❌ **Software and Tools Documented**
  - Applicability: unknown; processing_software: not declared; retained in the denominator
  - Fields checked: software_and_tools
- ✅ **External Standards, Resources, and Imputation Protocols**
  - Applicability: applicable; This item applies to every dataset
  - Found: #/external_resources/0: {'name': 'REDCap data dictionary, metadata and instrument PDFs', 'external_resources': ['https://git
  - Found: #/external_resources/1: {'name': 'Publication describing protocol development', 'description': 'Developing Multi-Disorder Vo
  - Found: #/external_resources/2: {'name': 'Feasibility study of the data collection application', 'description': 'The Bridge2AI-voice
  - Found: #/external_resources/3: {'name': 'Viewpoint introducing audiomics', 'description': 'Voice as an AI Biomarker of Health—Intro
  - Found: #/external_resources/4: {'name': 'Project documentation', 'description': 'Documentation site of the Voice project and the re
  - Found: #/external_resources/5: {'name': 'Project website', 'external_resources': ['https://b2ai-voice.org/']}
  - Found: #/conforms_to: Brain Imaging Data Structure v1.9.0

#### 9. Dataset Evaluation and Limitations Disclosure

Does the metadata communicate known risks, biases, or dataset limitations?

- ✅ **Known Limitations Documented**
  - Applicability: applicable; This item applies to every dataset
  - Found: #/known_limitations/0: {'limitation_description': 'The public data releases do not contain an equal distribution of the dis
  - Found: #/known_limitations/1: {'limitation_description': 'Certain aspects of the data (e.g., transcription) were generated using o
  - Found: #/known_limitations/2: {'limitation_description': 'Distinct iPad devices were used at each site.', 'scope_impact': 'Listed 
  - Found: #/known_limitations/3: {'limitation_description': 'The data were recorded with a head-mounted headset with a microphone tha
  - Found: #/known_limitations/4: {'limitation_description': 'Changes in diagnostic criteria or practices could be a source of distrib
  - Found: #/known_limitations/5: {'limitation_description': 'Confounding factors that might be present in the data: noise artifacts, 
  - Found: #/known_limitations/6: {'limitation_description': 'Some files, whether due to length or other issues, could not generate ce
- ✅ **Biases Categorized Using Standard Taxonomy (RAI-aligned)**
  - Applicability: applicable; This item applies to every dataset
  - Found: #/known_biases/0: {'bias_description': 'Groups that have less trust in the medical system, AI, or are less proximal to
  - Found: #/known_biases/1: {'bias_description': 'Participants were screened for different disorders based on site, so they also
  - Found: #/known_biases/2: {'bias_description': 'The dataset has skews based on disorder category, site, and other demographic 
- ✅ **Data Anomalies and Quality Issues Noted**
  - Applicability: applicable; This item applies to every dataset
  - Found: #/anomalies/0: {'anomaly_details': 'Different sites have different collection configurations. The collection protoc
  - Found: #/anomalies/1: {'anomaly_details': 'As participants may have repeated visits in order to collect data, there may be
- ✅ **Sensitive Content and Warnings Provided**
  - Applicability: applicable; This item applies to every dataset
  - Found: #/sensitive_elements/0: {'sensitive_elements_present': True, 'sensitivity_details': 'The dataset includes race information.'
  - Found: #/sensitive_elements/1: {'sensitive_elements_present': True, 'sensitivity_details': 'The dataset includes sexual orientation
  - Found: #/sensitive_elements/2: {'sensitive_elements_present': True, 'sensitivity_details': 'The dataset includes socioeconomic and 
  - Found: #/content_warnings/0: {'warnings': ['The healthsheet states that the dataset includes the transcription of free speech tas
- ✅ **Ethical Review and Social Impact Analysis**
  - Applicability: applicable; This item applies to every dataset
  - Found: #/ethical_reviews/0: {'reviewing_organization': 'University of South Florida Institutional Review Board', 'review_details
  - Found: #/ethical_reviews/1: {'review_details': 'The study protocol states that Canadian institutions do not abide by the single 
  - Found: #/future_use_impacts/0: {'impact_details': 'The dataset has skews based on disorder category, site, and other demographic fa

#### 10. Cross-Platform and Community Integration

Does the dataset connect to relevant repositories, communities and standards? A shared dataset needs citation or identifier guidance and a named hosting or preservation route appropriate to its domain.

- ❌ **Dataset Published on a Recognized Platform**
  - Applicability: unknown; shared_dataset: not declared; retained in the denominator
  - Fields checked: publisher
- ✅ **Citation and DOI for Cross-referencing**
  - Applicability: unknown; shared_dataset: not declared; retained in the denominator
  - Found: #/doi: 10.13026/37yb-1t42
- ✅ **Community Standards or Schema Conformance**
  - Applicability: unknown; shared_dataset: not declared; retained in the denominator
  - Found: #/conforms_to: Brain Imaging Data Structure v1.9.0
- ✅ **Outreach Materials and Documentation Links**
  - Applicability: unknown; shared_dataset: not declared; retained in the denominator
  - Found: #/external_resources/0: {'name': 'REDCap data dictionary, metadata and instrument PDFs', 'external_resources': ['https://git
  - Found: #/external_resources/1: {'name': 'Publication describing protocol development', 'description': 'Developing Multi-Disorder Vo
  - Found: #/external_resources/2: {'name': 'Feasibility study of the data collection application', 'description': 'The Bridge2AI-voice
  - Found: #/external_resources/3: {'name': 'Viewpoint introducing audiomics', 'description': 'Voice as an AI Biomarker of Health—Intro
  - Found: #/external_resources/4: {'name': 'Project documentation', 'description': 'Documentation site of the Voice project and the re
  - Found: #/external_resources/5: {'name': 'Project website', 'external_resources': ['https://b2ai-voice.org/']}
  - Found: #/page: https://physionet.org/content/b2ai-voice/3.1.0/
- ✅ **Related Datasets with Typed Relationships**
  - Applicability: unknown; shared_dataset: not declared; retained in the denominator
  - Found: #/related_datasets/0: {'name': 'Bridge2AI-Voice Pediatric Dataset', 'target_dataset': 'doi:10.13026/mf9s-5r03', 'relations

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
