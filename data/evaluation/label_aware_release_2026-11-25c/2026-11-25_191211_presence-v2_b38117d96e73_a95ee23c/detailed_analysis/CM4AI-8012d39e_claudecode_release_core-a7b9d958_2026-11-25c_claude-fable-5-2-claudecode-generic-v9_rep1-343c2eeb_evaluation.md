# Detailed Evaluation: CM4AI - CLAUDECODE_RELEASE_CORE

Evaluated: 2026-11-25T19:12:36.158549
File: `data/d4d_concatenated/claudecode_release_core/2026-11-25c_claude-fable-5-2-claudecode-generic-v9_rep1/CM4AI_d4d_core.yaml`

Instrument: `b38117d96e73987f236d4d3d47da5b84a952401537f9a2ae4d2c44bf981fc064`
Applicability context: `fca403729b83dda36a67c4b749455b0fd864ba992e0e40b9a0f5c65bc039bfad`
Scope: single_dataset
## Overall Scores

- **Rubric10**: 33.0/50 (66.0%)
- **Rubric20**: 62.0/88 (70.5%)

## Rubric10 Element Scores

| ID | Element | Score | Details |
|----|---------|-------|---------|
| 1 | Dataset Discovery and Identification | 4/5 | 4/5 applicable sub-elements present; 0 N/A |
| 2 | Dataset Access and Retrieval | 4/5 | 4/5 applicable sub-elements present; 0 N/A |
| 3 | Data Reuse and Interoperability | 4/5 | 4/5 applicable sub-elements present; 0 N/A |
| 4 | Ethical Use and Privacy Safeguards | 2/5 | 2/5 applicable sub-elements present; 0 N/A |
| 5 | Data Composition and Structure | 2/5 | 2/5 applicable sub-elements present; 0 N/A |
| 6 | Data Provenance and Version Tracking | 4/5 | 4/5 applicable sub-elements present; 0 N/A |
| 7 | Scientific Motivation and Funding Transparency | 5/5 | 5/5 applicable sub-elements present; 0 N/A |
| 8 | Technical Transparency (Data Collection and Processing) | 3/5 | 3/5 applicable sub-elements present; 0 N/A |
| 9 | Dataset Evaluation and Limitations Disclosure | 3/5 | 3/5 applicable sub-elements present; 0 N/A |
| 10 | Cross-Platform and Community Integration | 2/5 | 2/5 applicable sub-elements present; 0 N/A |

### Rubric10 Sub-Element Details


#### 1. Dataset Discovery and Identification

Can a user or system discover and uniquely identify this dataset?

- ✅ **Persistent Identifier (DOI, RRID, or URI)**
  - Applicability: applicable; This item applies to every dataset
  - Found: #/id: https://cm4ai.org/
- ✅ **Dataset Title and Description Completeness**
  - Applicability: applicable; This item applies to every dataset
  - Found: #/title: Cell Maps for Artificial Intelligence
  - Found: #/description: CM4AI (Cell Maps for Artificial Intelligence) is the Functional Genomics Grand Challenge in the NIH 
- ✅ **Keywords or Tags for Searchability**
  - Applicability: applicable; This item applies to every dataset
  - Found: #/keywords/0: AI
  - Found: #/keywords/1: affinity purification
  - Found: #/keywords/2: AP-MS
  - Found: #/keywords/3: artificial intelligence
  - Found: #/keywords/4: breast cancer
  - Found: #/keywords/5: Bridge2AI
  - Found: #/keywords/6: cardiomyocyte
  - Found: #/keywords/7: CM4AI
  - Found: #/keywords/8: CRISPR/Cas9
  - Found: #/keywords/9: induced pluripotent stem cell
  - Found: #/keywords/10: iPSC
  - Found: #/keywords/11: KOLF2.1J
  - Found: #/keywords/12: machine learning
  - Found: #/keywords/13: mass spectroscopy
  - Found: #/keywords/14: MDA-MB-468
  - Found: #/keywords/15: neural progenitor cell
  - Found: #/keywords/16: NPC
  - Found: #/keywords/17: neuron
  - Found: #/keywords/18: paclitaxel
  - Found: #/keywords/19: perturb-seq
  - Found: #/keywords/20: perturbation sequencing
  - Found: #/keywords/21: protein-protein interaction
  - Found: #/keywords/22: protein localization
  - Found: #/keywords/23: single-cell RNA sequencing
  - Found: #/keywords/24: scRNAseq
  - Found: #/keywords/25: SEC-MS
  - Found: #/keywords/26: size exclusion chromatography
  - Found: #/keywords/27: subcellular imaging
  - Found: #/keywords/28: vorinostat
- ✅ **Landing Page and Resources (page, hierarchical resources)**
  - Applicability: applicable; This item applies to every dataset
  - Found: #/page: https://cm4ai.org/
  - Found: #/resources/0: {'id': 'doi:10.18130/V3/DXWOS5', 'title': 'Cell Maps for Artificial Intelligence - Data Release', 'd
  - Found: #/resources/1: {'id': 'doi:10.18130/V3/B35XWX', 'title': 'Cell Maps for Artificial Intelligence - March 2025 Data R
  - Found: #/resources/2: {'id': 'doi:10.18130/V3/F3TD5R', 'title': 'Cell Maps for Artificial Intelligence - June 2025 Data Re
  - Found: #/resources/3: {'id': 'doi:10.18130/V3/K7TGEM', 'title': 'Cell Maps for Artificial Intelligence - October 2025 Data
  - Found: #/resources/4: {'id': 'doi:10.18130/V3/HIGT4C', 'title': 'Cell Maps for Artificial Intelligence - June 2026 Data Re
- ❌ **Hierarchical Structure (parent datasets, relationships)**
  - Applicability: applicable; This item applies to every dataset
  - Fields checked: parent_datasets, related_datasets

#### 2. Dataset Access and Retrieval

Can the dataset and its associated resources be located, accessed, and downloaded?

- ✅ **Access Policy and IP Restrictions Defined**
  - Applicability: applicable; This item applies to every dataset
  - Found: #/license_and_use_terms: {'license_terms': 'CC BY-NC-SA 4.0. The dataset is licensed for reuse under the Creative Commons Att
  - Found: #/ip_restrictions: {'restrictions': ['This data is Copyright (c) 2025 The Regents of the University of California excep
- ✅ **Regulatory Compliance and Confidentiality Classification**
  - Applicability: unknown; regulated_access: not declared; retained in the denominator
  - Found: #/data_governance/committee_contact: {'id': 'ORCID:0000-0003-4535-3486', 'name': 'Jillian Parker', 'orcid': '0000-0003-4535-3486', 'email
- ❌ **Download URL or Platform Link Available**
  - Applicability: applicable; This item applies to every dataset
  - Fields checked: download_url
- ✅ **Distribution Formats and File Types Specified**
  - Applicability: applicable; This item applies to every dataset
  - Found: #/distribution_formats/0: {'name': 'ZIP archives on the University of Virginia Dataverse', 'media_type': 'application/zip', 'd
  - Found: #/distribution_formats/1: {'name': 'RO-Crate packages', 'format': 'RO-Crate', 'description': 'The March 2025 Data Release dist
  - Found: #/distributions/1: {'description': 'This dataset represents an expressed genome-scale CRISPRi Perturbation Cell Atlas i
  - Found: #/distributions/2: {'description': 'This dataset represents raw sequence data from an expressed genome-scale CRISPRi Pe
  - Found: #/distributions/3: {'compression': 'zip', 'description': 'This data set displays the spatial localization of 563 protei
  - Found: #/distributions/4: {'compression': 'zip', 'description': 'This data set displays the spatial localization of 563 protei
  - Found: #/distributions/5: {'compression': 'zip', 'description': 'This data set displays the spatial localization of 563 protei
  - Found: #/distributions/6: {'description': 'This dataset was generated by size exclusion chromatography-mass spectroscopy (SEC-
  - Found: #/distributions/8: {'description': 'HTML datasheet summarizing key release information. Size shown: 89.5 KB; published 
  - Found: #/distributions/9: {'description': 'Release RO-Crate with pointers to sub ro-crates. Size shown: 35.0 KB; published Jul
  - Found: #/distributions/10: {'compression': 'zip', 'description': 'This data set displays the spatial localization of 464 protei
  - Found: #/distributions/11: {'compression': 'zip', 'description': 'This data set displays the spatial localization of 464 protei
  - Found: #/distributions/12: {'compression': 'zip', 'description': 'This data set displays the spatial localization of 464 protei
  - Found: #/distributions/13: {'description': 'Provenance graph file. The .html provenance graph files require download to view pr
  - Found: #/distributions/14: {'description': 'Provenance graph file. The .html provenance graph files require download to view pr
  - Found: #/distributions/15: {'description': 'Provenance graph file. The .html provenance graph files require download to view pr
  - Found: #/distributions/16: {'description': 'Provenance graph file. The .html provenance graph files require download to view pr
  - Found: #/distributions/17: {'description': 'Size shown: 343.4 KB; published Jul 1, 2025.', 'format': 'JSON', 'hash': 'md5:3a706
  - Found: #/distributions/19: {'compression': 'zip', 'description': 'This dataset was generated by size exclusion chromatography-m
  - Found: #/distributions/20: {'compression': 'zip', 'description': 'This dataset was generated by size exclusion chromatography-m
  - Found: #/distributions/21: {'compression': 'zip', 'description': 'This dataset represents an expressed genome-scale CRISPRi Per
  - Found: #/distributions/22: {'compression': 'zip', 'description': 'This dataset represents raw sequence data from an expressed g
  - Found: #/distributions/23: {'compression': 'zip', 'description': 'Size shown: 203.5 KB; published Dec 22, 2025.', 'format': 'ZI
  - Found: #/distributions/24: {'compression': 'zip', 'description': 'This data set displays the spatial localization of 464 protei
  - Found: #/distributions/25: {'compression': 'zip', 'description': 'This data set displays the spatial localization of 464 protei
  - Found: #/distributions/26: {'compression': 'zip', 'description': 'This data set displays the spatial localization of 464 protei
  - Found: #/distributions/28: {'compression': 'zip', 'description': 'Size shown: 113.3 KB; published Jun 17, 2026.', 'format': 'ZI
  - Found: #/distributions/29: {'compression': 'zip', 'description': 'Size shown: 135.8 KB; published Jun 17, 2026.', 'format': 'ZI
  - Found: #/distributions/30: {'compression': 'zip', 'description': 'Size shown: 3.8 GB; published Jul 15, 2026.', 'format': 'ZIP'
  - Found: #/distributions/31: {'compression': 'zip', 'description': 'Size shown: 4.6 GB; published Jul 15, 2026.', 'format': 'ZIP'
  - Found: #/distributions/32: {'compression': 'zip', 'description': 'Size shown: 4.2 GB; published Jul 15, 2026.', 'format': 'ZIP'
  - Found: #/distributions/33: {'compression': 'zip', 'description': 'Size shown: 171.8 KB; published Jun 17, 2026.', 'format': 'ZI
  - Found: #/distributions/34: {'compression': 'zip', 'description': 'Size shown: 93.9 KB; published Jun 17, 2026.', 'format': 'ZIP
  - Found: #/distributions/35: {'compression': 'zip', 'description': 'Size shown: 30.2 KB; published Jun 17, 2026.', 'format': 'ZIP
  - Found: #/distributions/36: {'compression': 'zip', 'description': 'Size shown: 73.3 KB; published Jun 17, 2026.', 'format': 'ZIP
  - Found: #/distributions/37: {'compression': 'zip', 'description': 'Size shown: 1.1 MB; published Jun 17, 2026.', 'format': 'ZIP'
  - Found: #/distributions/1/format: JSON
  - Found: #/distributions/2/format: JSON
  - Found: #/distributions/3/format: ZIP
  - Found: #/distributions/4/format: ZIP
  - Found: #/distributions/5/format: ZIP
  - Found: #/distributions/6/format: JSON
  - Found: #/distributions/8/format: HTML
  - Found: #/distributions/9/format: JSON
  - Found: #/distributions/10/format: ZIP
  - Found: #/distributions/11/format: ZIP
  - Found: #/distributions/12/format: ZIP
  - Found: #/distributions/13/format: HTML
  - Found: #/distributions/14/format: HTML
  - Found: #/distributions/15/format: HTML
  - Found: #/distributions/16/format: HTML
  - Found: #/distributions/17/format: JSON
  - Found: #/distributions/19/format: ZIP
  - Found: #/distributions/20/format: ZIP
  - Found: #/distributions/21/format: ZIP
  - Found: #/distributions/22/format: ZIP
  - Found: #/distributions/23/format: ZIP
  - Found: #/distributions/24/format: ZIP
  - Found: #/distributions/25/format: ZIP
  - Found: #/distributions/26/format: ZIP
  - Found: #/distributions/28/format: ZIP
  - Found: #/distributions/29/format: ZIP
  - Found: #/distributions/30/format: ZIP
  - Found: #/distributions/31/format: ZIP
  - Found: #/distributions/32/format: ZIP
  - Found: #/distributions/33/format: ZIP
  - Found: #/distributions/34/format: ZIP
  - Found: #/distributions/35/format: ZIP
  - Found: #/distributions/36/format: ZIP
  - Found: #/distributions/37/format: ZIP
  - Found: #/distribution_formats/1/format: RO-Crate
  - Found: #/distributions/1/media_type: application/json
  - Found: #/distributions/2/media_type: application/json
  - Found: #/distributions/3/media_type: application/zip
  - Found: #/distributions/4/media_type: application/zip
  - Found: #/distributions/5/media_type: application/zip
  - Found: #/distributions/6/media_type: application/json
  - Found: #/distributions/8/media_type: text/html
  - Found: #/distributions/9/media_type: application/json
  - Found: #/distributions/10/media_type: application/zip
  - Found: #/distributions/11/media_type: application/zip
  - Found: #/distributions/12/media_type: application/zip
  - Found: #/distributions/13/media_type: text/html
  - Found: #/distributions/14/media_type: text/html
  - Found: #/distributions/15/media_type: text/html
  - Found: #/distributions/16/media_type: text/html
  - Found: #/distributions/17/media_type: application/json
  - Found: #/distributions/19/media_type: application/zip
  - Found: #/distributions/20/media_type: application/zip
  - Found: #/distributions/21/media_type: application/zip
  - Found: #/distributions/22/media_type: application/zip
  - Found: #/distributions/23/media_type: application/zip
  - Found: #/distributions/24/media_type: application/zip
  - Found: #/distributions/25/media_type: application/zip
  - Found: #/distributions/26/media_type: application/zip
  - Found: #/distributions/28/media_type: application/zip
  - Found: #/distributions/29/media_type: application/zip
  - Found: #/distributions/30/media_type: application/zip
  - Found: #/distributions/31/media_type: application/zip
  - Found: #/distributions/32/media_type: application/zip
  - Found: #/distributions/33/media_type: application/zip
  - Found: #/distributions/34/media_type: application/zip
  - Found: #/distributions/35/media_type: application/zip
  - Found: #/distributions/36/media_type: application/zip
  - Found: #/distributions/37/media_type: application/zip
  - Found: #/distribution_formats/0/media_type: application/zip
- ✅ **Related Datasets and External Resources Linked**
  - Applicability: applicable; This item applies to every dataset
  - Found: #/external_resources/0: {'name': 'Cell Maps for Artificial Intelligence: AI-Ready Maps of Human Cell Architecture from Disea
  - Found: #/external_resources/1: {'name': 'A PERTURBATION CELL ATLAS OF HUMAN INDUCED PLURIPOTENT STEM CELLS', 'description': 'bioRxi
  - Found: #/external_resources/2: {'name': 'CRISPRi Perturbation Atlas of iPSCs', 'description': 'Listed under the External Data Links
  - Found: #/external_resources/3: {'name': 'SEC-MS data in KOLF2.1J iPSCs (undifferentiated, NPC, neuron, and cardiomyocyte)', 'descri
  - Found: #/external_resources/4: {'name': 'SEC-MS data in MDA-MB-468 breast cancer cells (+/- treatment)', 'description': 'Listed und
  - Found: #/external_resources/5: {'name': 'AP-MS data in MDA-MB-468 breast cancer cells (treated with paclitaxel)', 'description': 'L
  - Found: #/external_resources/6: {'name': 'AP-MS data in MDA-MB-468 breast cancer cells (treated with vorinostat)', 'description': 'L

#### 3. Data Reuse and Interoperability

Is sufficient information provided to reuse and integrate the dataset with others?
Note: Evaluate whether the dataset is designed for integration with similar datasets, including: common identifiers for cross-dataset linking, standardized formats for data harmonization, and documented integration procedures.


- ✅ **License Terms Allow Reuse**
  - Applicability: unknown; shared_dataset: not declared; retained in the denominator
  - Found: #/license_and_use_terms: {'license_terms': 'CC BY-NC-SA 4.0. The dataset is licensed for reuse under the Creative Commons Att
- ✅ **Data Formats Are Standardized (encoding, format)**
  - Applicability: unknown; shared_dataset: not declared; retained in the denominator
  - Found: #/distributions/1/format: JSON
  - Found: #/distributions/2/format: JSON
  - Found: #/distributions/3/format: ZIP
  - Found: #/distributions/4/format: ZIP
  - Found: #/distributions/5/format: ZIP
  - Found: #/distributions/6/format: JSON
  - Found: #/distributions/8/format: HTML
  - Found: #/distributions/9/format: JSON
  - Found: #/distributions/10/format: ZIP
  - Found: #/distributions/11/format: ZIP
  - Found: #/distributions/12/format: ZIP
  - Found: #/distributions/13/format: HTML
  - Found: #/distributions/14/format: HTML
  - Found: #/distributions/15/format: HTML
  - Found: #/distributions/16/format: HTML
  - Found: #/distributions/17/format: JSON
  - Found: #/distributions/19/format: ZIP
  - Found: #/distributions/20/format: ZIP
  - Found: #/distributions/21/format: ZIP
  - Found: #/distributions/22/format: ZIP
  - Found: #/distributions/23/format: ZIP
  - Found: #/distributions/24/format: ZIP
  - Found: #/distributions/25/format: ZIP
  - Found: #/distributions/26/format: ZIP
  - Found: #/distributions/28/format: ZIP
  - Found: #/distributions/29/format: ZIP
  - Found: #/distributions/30/format: ZIP
  - Found: #/distributions/31/format: ZIP
  - Found: #/distributions/32/format: ZIP
  - Found: #/distributions/33/format: ZIP
  - Found: #/distributions/34/format: ZIP
  - Found: #/distributions/35/format: ZIP
  - Found: #/distributions/36/format: ZIP
  - Found: #/distributions/37/format: ZIP
  - Found: #/distribution_formats/1/format: RO-Crate
- ✅ **Schema or Ontology Conformance Stated**
  - Applicability: unknown; shared_dataset: not declared; retained in the denominator
  - Found: #/conforms_to: RO-Crate
  - Found: #/conforms_to_schema: src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml
- ❌ **Variable Metadata with Identifiers Defined**
  - Applicability: unknown; shared_dataset: not declared; retained in the denominator
  - Fields checked: variables
- ✅ **Use Guidance Provided (intended, prohibited uses)**
  - Applicability: applicable; This item applies to every dataset
  - Found: #/intended_uses/0: {'name': 'Research in functional genomics', 'description': 'AI-ready datasets to support research in
  - Found: #/intended_uses/1: {'name': 'AI model training', 'description': 'AI model training.'}
  - Found: #/intended_uses/2: {'name': 'Cellular process analysis', 'description': 'Cellular process analysis.'}
  - Found: #/intended_uses/3: {'name': 'Analysis of cell architectural changes and interactions', 'description': 'Cell architectur
  - Found: #/prohibited_uses/0: {'name': 'Clinical decision-making or patient care without regulatory oversight', 'description': 'Th

#### 4. Ethical Use and Privacy Safeguards

Does the dataset document the ethical oversight, privacy, consent and safeguards that apply to its subjects and governance context? Equivalent local ethics and regulatory frameworks are accepted; HIPAA or an IRB is not a universal requirement.

- ✅ **IRB or Ethics Review and Data Protection Impact**
  - Applicability: unknown; any: human_subjects: not declared; retained in the denominator; regulated_access: not declared; retained in the denominator
  - Found: #/ethical_reviews/0: {'contact_person': {'id': 'ORCID:0000-0002-7080-8801', 'name': 'Vardit Ravitsky', 'orcid': '0000-000
  - Found: #/ethical_reviews/1: {'contact_person': {'id': 'ORCID:0000-0002-8965-8153', 'name': 'Jean-Christophe Belisle-Pipon', 'orc
  - Found: #/human_subject_research: {'involves_human_subjects': False, 'description': 'The Data Governance & Ethics section of the June 
- ✅ **Deidentification Method Described**
  - Applicability: unknown; any: human_subjects: not declared; retained in the denominator; regulated_access: not declared; retained in the denominator
  - Found: #/is_deidentified: {'identifiable_elements_present': False, 'deidentification_details': 'The June 2026 Data Release sta
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
  - Found: #/instances/0: {'name': 'Perturb-seq data', 'instance_type': 'Perturb-seq data', 'description': 'Perturb-seq data f
  - Found: #/instances/1: {'name': 'SEC-MS data', 'instance_type': 'SEC-MS data', 'description': 'SEC-MS data for MDA-MB-468 b
  - Found: #/instances/2: {'name': 'AP-MS data', 'instance_type': 'AP-MS data', 'description': 'AP-MS data for MDA-MB-468 brea
  - Found: #/instances/3: {'name': 'IF images', 'instance_type': 'Immunofluorescent image', 'description': 'IF images in MDA-M
- ❌ **Variable-Level Metadata, Tabular Flag, and Data Splits**
  - Applicability: applicable; This item applies to every dataset
  - Fields checked: variables, is_tabular, is_data_split, is_subpopulation
- ✅ **Data Topics or Conditions Represented**
  - Applicability: applicable; This item applies to every dataset
  - Found: #/instances/0: {'name': 'Perturb-seq data', 'instance_type': 'Perturb-seq data', 'description': 'Perturb-seq data f
  - Found: #/instances/1: {'name': 'SEC-MS data', 'instance_type': 'SEC-MS data', 'description': 'SEC-MS data for MDA-MB-468 b
  - Found: #/instances/2: {'name': 'AP-MS data', 'instance_type': 'AP-MS data', 'description': 'AP-MS data for MDA-MB-468 brea
  - Found: #/instances/3: {'name': 'IF images', 'instance_type': 'Immunofluorescent image', 'description': 'IF images in MDA-M
- ❌ **Data Quality, Anomalies, and Missing Data Documented**
  - Applicability: applicable; This item applies to every dataset
  - Fields checked: anomalies, sampling_strategies, missing_data_documentation

#### 6. Data Provenance and Version Tracking

Can a user determine dataset versions, update history, and provenance?

- ❌ **Dataset Version Number Provided**
  - Applicability: unknown; shared_dataset: not declared; retained in the denominator
  - Fields checked: version
- ✅ **Version Access Methods Documented**
  - Applicability: unknown; shared_dataset: not declared; retained in the denominator
  - Found: #/version_access: {'latest_version_doi': 'doi:10.18130/V3/HIGT4C', 'versions_available': ['May 2024 Data Release', 'Ma
- ✅ **Change Descriptions and Errata Provided**
  - Applicability: unknown; shared_dataset: not declared; retained in the denominator
  - Found: #/updates: {'frequency': 'quarterly', 'update_details': 'Dataset will be regularly updated and augmented throug
- ✅ **Update Schedule or Frequency Indicated**
  - Applicability: unknown; shared_dataset: not declared; retained in the denominator
  - Found: #/updates: {'frequency': 'quarterly', 'update_details': 'Dataset will be regularly updated and augmented throug
- ✅ **Provenance, Source Derivation, and Raw Data Sources**
  - Applicability: unknown; shared_dataset: not declared; retained in the denominator
  - Found: #/raw_data_sources/0: {'name': 'MDA-MB-468 cell line', 'source_description': 'MDA-MB-468 (RRID:CVCL_0419) is a triple nega
  - Found: #/raw_data_sources/1: {'name': 'KOLF2.1J iPSC line', 'source_description': 'The KOLF2.1J (RRID:CVCL_B5P3) iPSCs cell line 

#### 7. Scientific Motivation and Funding Transparency

Does the metadata clearly state why the dataset exists and who funded it?

- ✅ **Motivation or Purpose for Dataset Creation**
  - Applicability: applicable; This item applies to every dataset
  - Found: #/purposes/0: {'name': 'Ethical, AI-ready datasets of cell architecture', 'response': 'The overarching mission of 
  - Found: #/purposes/1: {'name': 'Mapping the spatiotemporal architecture of human cells', 'response': 'The CM4AI data gener
- ✅ **Primary Research Objectives or Tasks**
  - Applicability: applicable; This item applies to every dataset
  - Found: #/tasks/0: {'name': 'Interpretable genotype-phenotype learning', 'response': 'The project description states th
- ✅ **Funding Sources and Mechanisms Listed**
  - Applicability: applicable; This item applies to every dataset
  - Found: #/funders/0: {'name': 'NIH Common Fund Bridge2AI program', 'grantor': 'National Institutes of Health', 'grants': 
  - Found: #/funders/1: {'grantor': 'Frederick Thomas Fund of the University of Virginia', 'source_caveats': 'Stated only in
- ✅ **Grant IDs or Award Numbers Present**
  - Applicability: applicable; This item applies to every dataset
  - Found: #/funders/0: {'name': 'NIH Common Fund Bridge2AI program', 'grantor': 'National Institutes of Health', 'grants': 
  - Found: #/funders/1: {'grantor': 'Frederick Thomas Fund of the University of Virginia', 'source_caveats': 'Stated only in
- ✅ **Creators and Acknowledgements Documented**
  - Applicability: applicable; This item applies to every dataset
  - Found: #/creators/0: {'id': 'ORCID:0000-0003-4060-7360', 'name': 'Clark T', 'affiliations': [{'id': 'ROR:0153tk833', 'nam
  - Found: #/creators/1: {'id': 'ORCID:0000-0003-4535-3486', 'name': 'Parker J', 'affiliations': [{'name': 'University of Cal
  - Found: #/creators/2: {'id': 'ORCID:0000-0003-4647-3877', 'name': 'Al Manir S', 'affiliations': [{'id': 'ROR:0153tk833', '
  - Found: #/creators/3: {'name': 'Axelsson U', 'affiliations': [{'name': 'KTH Royal Institute of Technology'}]}
  - Found: #/creators/4: {'id': 'ORCID:0000-0002-4180-422X', 'name': 'Ballllosero Navarro F', 'affiliations': [{'name': 'Stan
  - Found: #/creators/5: {'name': 'Chinn B', 'affiliations': [{'name': 'University of California San Diego'}]}
  - Found: #/creators/6: {'id': 'ORCID:0000-0001-9998-705X', 'name': 'Churas CP', 'affiliations': [{'name': 'University of Ca
  - Found: #/creators/7: {'id': 'ORCID:0000-0002-6711-8260', 'name': 'Dailamy A', 'affiliations': [{'name': 'University of Ca
  - Found: #/creators/8: {'id': 'ORCID:0009-0009-0483-7506', 'name': 'Doctor Y', 'affiliations': [{'name': 'University of Cal
  - Found: #/creators/9: {'name': 'Fall J', 'affiliations': [{'name': 'KTH - Royal Institute of Technology'}]}
  - Found: #/creators/10: {'id': 'ORCID:0000-0003-0223-0312', 'name': 'Forget A', 'affiliations': [{'name': 'University of Cal
  - Found: #/creators/11: {'id': 'ORCID:0000-0002-6311-3526', 'name': 'Gao J', 'affiliations': [{'name': 'University of Califo
  - Found: #/creators/12: {'id': 'ORCID:0000-0002-4650-9094', 'name': 'Hansen JN', 'affiliations': [{'name': 'Stanford Univers
  - Found: #/creators/13: {'id': 'ORCID:0000-0002-1571-8029', 'name': 'Hu M', 'affiliations': [{'name': 'University of Califor
  - Found: #/creators/14: {'name': 'Johannesson A', 'affiliations': [{'name': 'KTH - Royal Institute of Technology'}]}
  - Found: #/creators/15: {'name': 'Khaliq H', 'affiliations': [{'name': 'University of California San Diego'}]}
  - Found: #/creators/16: {'id': 'ORCID:0000-0003-0917-355X', 'name': 'Lee YH', 'affiliations': [{'name': 'University of Calif
  - Found: #/creators/17: {'id': 'ORCID:0000-0001-7252-8638', 'name': 'Lenkiewicz J', 'affiliations': [{'name': 'University of
  - Found: #/creators/18: {'id': 'ORCID:0000-0003-0384-8499', 'name': 'Levinson MA', 'affiliations': [{'id': 'ROR:0153tk833', 
  - Found: #/creators/19: {'id': 'ORCID:0000-0003-3960-420X', 'name': 'Marquez C', 'affiliations': [{'name': 'University of Ca
  - Found: #/creators/20: {'id': 'ORCID:0000-0003-2404-3040', 'name': 'Metallo C', 'affiliations': [{'name': 'University of Ca
  - Found: #/creators/21: {'name': 'Muralidharan M', 'affiliations': [{'name': 'University of California San Francisco'}]}
  - Found: #/creators/22: {'id': 'ORCID:0000-0003-3881-7588', 'name': 'Nourreddine S', 'affiliations': [{'name': 'University o
  - Found: #/creators/23: {'id': 'ORCID:0000-0002-1103-3882', 'name': 'Niestroy J', 'affiliations': [{'id': 'ROR:0153tk833', '
  - Found: #/creators/24: {'id': 'ORCID:0000-0002-4025-1299', 'name': 'Obernier K', 'affiliations': [{'name': 'University of C
  - Found: #/creators/25: {'name': 'Pan E', 'affiliations': [{'name': 'University of California San Diego'}]}
  - Found: #/creators/26: {'name': 'Polacco B', 'affiliations': [{'name': 'University of California San Francisco'}]}
  - Found: #/creators/27: {'id': 'ORCID:0000-0002-1471-9513', 'name': 'Pratt D', 'affiliations': [{'name': 'University of Cali
  - Found: #/creators/28: {'id': 'ORCID:0009-0005-4217-2745', 'name': 'Qian G', 'affiliations': [{'name': 'University of Calif
  - Found: #/creators/29: {'id': 'ORCID:0000-0001-6339-9141', 'name': 'Schaffer L', 'affiliations': [{'name': 'University of C
  - Found: #/creators/30: {'id': 'ORCID:0000-0003-3361-3797', 'name': 'Sigaeva A', 'affiliations': [{'name': 'KTH Royal Instit
  - Found: #/creators/31: {'id': 'ORCID:0000-0001-6730-2773', 'name': 'Thaker S', 'description': 'The project website lists Sw
  - Found: #/creators/32: {'name': 'Zhang Y', 'affiliations': [{'name': 'University of California San Diego'}]}
  - Found: #/creators/33: {'id': 'ORCID:0000-0002-8965-8153', 'name': 'Bélisle-Pipon JC', 'affiliations': [{'name': 'Simon Fra
  - Found: #/creators/34: {'id': 'ORCID:0000-0001-8179-1796', 'name': 'Brandt C', 'affiliations': [{'name': 'Yale University'}
  - Found: #/creators/35: {'id': 'ORCID:0000-0002-6112-415X', 'name': 'Chen JY', 'affiliations': [{'name': 'The University of 
  - Found: #/creators/36: {'id': 'ORCID:0000-0003-2567-2009', 'name': 'Ding Y', 'affiliations': [{'name': 'University of Texas
  - Found: #/creators/37: {'id': 'ORCID:0000-0003-4664-3143', 'name': 'Fodeh S', 'affiliations': [{'name': 'Yale University'}]
  - Found: #/creators/38: {'id': 'ORCID:0000-0003-4902-337X', 'name': 'Krogan N', 'affiliations': [{'name': 'University of Cal
  - Found: #/creators/39: {'id': 'ORCID:0000-0001-7034-0850', 'name': 'Lundberg E', 'affiliations': [{'name': 'Stanford Univer
  - Found: #/creators/40: {'id': 'ORCID:0000-0002-3383-1287', 'name': 'Mali P', 'affiliations': [{'name': 'University of Calif
  - Found: #/creators/41: {'id': 'ORCID:0000-0002-3508-3577', 'name': 'Payne-Foster P', 'affiliations': [{'name': 'University 
  - Found: #/creators/42: {'id': 'ORCID:0000-0002-6644-8284', 'name': 'Ratcliffe S', 'affiliations': [{'id': 'ROR:0153tk833', 
  - Found: #/creators/43: {'id': 'ORCID:0000-0002-7080-8801', 'name': 'Ravitsky V', 'affiliations': [{'name': 'University of M
  - Found: #/creators/44: {'id': 'ORCID:0000-0003-0435-6197', 'name': 'Sali A', 'affiliations': [{'name': 'University of Calif
  - Found: #/creators/45: {'id': 'ORCID:0000-0002-2048-4028', 'name': 'Schulz W', 'affiliations': [{'name': 'Yale University'}
  - Found: #/creators/46: {'id': 'ORCID:0000-0002-1708-8454', 'name': 'Ideker T', 'description': 'Listed as the Point of Conta
  - Found: #/funders/0: {'name': 'NIH Common Fund Bridge2AI program', 'grantor': 'National Institutes of Health', 'grants': 
  - Found: #/funders/1: {'grantor': 'Frederick Thomas Fund of the University of Virginia', 'source_caveats': 'Stated only in

#### 8. Technical Transparency (Data Collection and Processing)

Can data collection and processing steps be replicated or understood?
Note: Preprocessing and collection metadata may be represented as structured text descriptions OR as machine-readable provenance graphs (e.g., W3C PROV-O, workflow graphs). Evaluation should check for: (1) structured text descriptions OR (2) graph representations with entity-activity-agent relationships. Both formats are acceptable.


- ✅ **Collection Mechanisms and Settings Described**
  - Applicability: unknown; data_collection: not declared; retained in the denominator
  - Found: #/collection_mechanisms/0: {'name': 'Immunofluorescence staining and confocal microscopy', 'mechanism_details': 'Spatial locali
  - Found: #/collection_mechanisms/1: {'name': 'Size exclusion chromatography-mass spectroscopy (SEC-MS)', 'mechanism_details': 'SEC-MS da
  - Found: #/collection_mechanisms/2: {'name': 'Affinity purification mass spectroscopy (AP-MS)', 'mechanism_details': 'The June 2026 Data
  - Found: #/collection_mechanisms/3: {'name': 'Perturb-seq (CRISPRi perturbation)', 'mechanism_details': 'The October 2025 Data Release d
- ❌ **Data Acquisition Methods Listed**
  - Applicability: unknown; data_collection: not declared; retained in the denominator
  - Fields checked: acquisition_methods
- ✅ **Preprocessing, Cleaning, Labeling, and Annotation Quality**
  - Applicability: unknown; data_processing: not declared; retained in the denominator
  - Found: #/preprocessing_strategies/0: {'name': 'AI-readiness packaging in RO-Crate format with FAIRSCAPE', 'preprocessing_details': "CM4AI
- ❌ **Software and Tools Documented**
  - Applicability: unknown; processing_software: not declared; retained in the denominator
  - Fields checked: software_and_tools
- ✅ **External Standards, Resources, and Imputation Protocols**
  - Applicability: applicable; This item applies to every dataset
  - Found: #/external_resources/0: {'name': 'Cell Maps for Artificial Intelligence: AI-Ready Maps of Human Cell Architecture from Disea
  - Found: #/external_resources/1: {'name': 'A PERTURBATION CELL ATLAS OF HUMAN INDUCED PLURIPOTENT STEM CELLS', 'description': 'bioRxi
  - Found: #/external_resources/2: {'name': 'CRISPRi Perturbation Atlas of iPSCs', 'description': 'Listed under the External Data Links
  - Found: #/external_resources/3: {'name': 'SEC-MS data in KOLF2.1J iPSCs (undifferentiated, NPC, neuron, and cardiomyocyte)', 'descri
  - Found: #/external_resources/4: {'name': 'SEC-MS data in MDA-MB-468 breast cancer cells (+/- treatment)', 'description': 'Listed und
  - Found: #/external_resources/5: {'name': 'AP-MS data in MDA-MB-468 breast cancer cells (treated with paclitaxel)', 'description': 'L
  - Found: #/external_resources/6: {'name': 'AP-MS data in MDA-MB-468 breast cancer cells (treated with vorinostat)', 'description': 'L
  - Found: #/conforms_to: RO-Crate

#### 9. Dataset Evaluation and Limitations Disclosure

Does the metadata communicate known risks, biases, or dataset limitations?

- ✅ **Known Limitations Documented**
  - Applicability: applicable; This item applies to every dataset
  - Found: #/known_limitations/0: {'name': 'Interim release', 'limitation_description': 'This is an interim release.'}
  - Found: #/known_limitations/1: {'name': 'No predicted cell maps', 'limitation_description': 'The release does not contain predicted
  - Found: #/known_limitations/2: {'name': 'Suitability', 'limitation_description': 'The current release is most suitable for bioinfor
  - Found: #/known_limitations/3: {'name': 'Domain expertise', 'limitation_description': 'Requires domain expertise for meaningful ana
  - Found: #/known_limitations/4: {'name': 'Pre-publication embargo', 'limitation_description': 'Some datasets are under temporary pre
  - Found: #/known_limitations/5: {'name': 'Incompletely overlapping protein sets', 'limitation_description': 'Protein-protein interac
- ✅ **Biases Categorized Using Standard Taxonomy (RAI-aligned)**
  - Applicability: applicable; This item applies to every dataset
  - Found: #/known_biases/0: {'name': 'Commercially available cell lines', 'bias_description': 'Data in this release was derived 
  - Found: #/known_biases/1: {'name': 'Biological variants not represented', 'bias_description': 'Does not represent all biologic
- ❌ **Data Anomalies and Quality Issues Noted**
  - Applicability: applicable; This item applies to every dataset
  - Fields checked: anomalies
- ❌ **Sensitive Content and Warnings Provided**
  - Applicability: applicable; This item applies to every dataset
  - Fields checked: sensitive_elements, content_warnings
- ✅ **Ethical Review and Social Impact Analysis**
  - Applicability: applicable; This item applies to every dataset
  - Found: #/ethical_reviews/0: {'contact_person': {'id': 'ORCID:0000-0002-7080-8801', 'name': 'Vardit Ravitsky', 'orcid': '0000-000
  - Found: #/ethical_reviews/1: {'contact_person': {'id': 'ORCID:0000-0002-8965-8153', 'name': 'Jean-Christophe Belisle-Pipon', 'orc

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
  - Found: #/conforms_to: RO-Crate
- ✅ **Outreach Materials and Documentation Links**
  - Applicability: unknown; shared_dataset: not declared; retained in the denominator
  - Found: #/external_resources/0: {'name': 'Cell Maps for Artificial Intelligence: AI-Ready Maps of Human Cell Architecture from Disea
  - Found: #/external_resources/1: {'name': 'A PERTURBATION CELL ATLAS OF HUMAN INDUCED PLURIPOTENT STEM CELLS', 'description': 'bioRxi
  - Found: #/external_resources/2: {'name': 'CRISPRi Perturbation Atlas of iPSCs', 'description': 'Listed under the External Data Links
  - Found: #/external_resources/3: {'name': 'SEC-MS data in KOLF2.1J iPSCs (undifferentiated, NPC, neuron, and cardiomyocyte)', 'descri
  - Found: #/external_resources/4: {'name': 'SEC-MS data in MDA-MB-468 breast cancer cells (+/- treatment)', 'description': 'Listed und
  - Found: #/external_resources/5: {'name': 'AP-MS data in MDA-MB-468 breast cancer cells (treated with paclitaxel)', 'description': 'L
  - Found: #/external_resources/6: {'name': 'AP-MS data in MDA-MB-468 breast cancer cells (treated with vorinostat)', 'description': 'L
  - Found: #/page: https://cm4ai.org/
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
| 20 | Bias Documentation and Responsible AI Alignment | 3.0/5 | ✅ |

Applicability for Q16: applicable; This item applies to every dataset


Applicability for Q17: unknown; shared_dataset: not declared; retained in the denominator


Applicability for Q18: applicable; This item applies to every dataset


Applicability for Q19: applicable; This item applies to every dataset


Applicability for Q20: applicable; This item applies to every dataset
