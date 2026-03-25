#!/usr/bin/env python3
"""
Generate comprehensive D4D to RO-Crate interface mapping file.

Creates SSSOM-inspired mapping with 124+ field mappings across 19 categories:
1. Basic Metadata (14 fields)
2. Dates (4 fields)
3. Checksums & Identifiers (5 fields)
4. Relationships (5 fields)
5. Creators & Attribution (3 fields)
6. RAI Use Cases (9 fields)
7. RAI Biases & Limitations (6 fields)
8. Privacy (5 fields)
9. Data Collection (6 fields)
10. Preprocessing (12 fields)
11. Annotation (8 fields)
12. Ethics & Compliance (10 fields)
13. Governance (6 fields)
14. Maintenance (3 fields)
15. FAIRSCAPE EVI (9 fields)
16. D4D-Embedded (5 fields)
17. Quality (4 fields)
18. Format (5 fields)
19. Unmapped (14 fields)

Output format inspired by SSSOM (Simple Standard for Sharing Ontological Mappings)
with additional columns for information loss assessment and transformation details.
"""

import csv
from pathlib import Path
from typing import List, Tuple

# Column headers for interface mapping
HEADERS = [
    'Category',
    'D4D_Full_Path',
    'D4D_Type',
    'Exchange_Layer_URI',
    'RO_Crate_JSON_Path',
    'Mapping_Type',
    'Information_Loss',
    'Example_D4D_Value',
    'Example_RO_Crate_Value',
    'Transformation_Notes'
]

# Mapping data organized by category
# Format: (category, d4d_path, d4d_type, skos_relation, rocrate_path, mapping_type, loss, ex_d4d, ex_rocrate, notes)
MAPPINGS: List[Tuple[str, ...]] = [
    # ====================
    # 1. Basic Metadata
    # ====================
    ('Basic Metadata', 'Dataset.title', 'str', 'd4d:title skos:exactMatch schema:name', '@graph[?@type=\'Dataset\'][\'name\']', 'exactMatch', 'none', '"AI-READI Dataset"', '"AI-READI Dataset"', ''),
    ('Basic Metadata', 'Dataset.description', 'str', 'd4d:description skos:exactMatch schema:description', '@graph[?@type=\'Dataset\'][\'description\']', 'exactMatch', 'none', '"Diabetes research data..."', '"Diabetes research data..."', ''),
    ('Basic Metadata', 'Dataset.keywords', 'List[str]', 'd4d:keywords skos:exactMatch schema:keywords', '@graph[?@type=\'Dataset\'][\'keywords\']', 'exactMatch', 'none', '["diabetes", "AI"]', '["diabetes", "AI"]', ''),
    ('Basic Metadata', 'Dataset.language', 'str', 'd4d:language skos:exactMatch schema:inLanguage', '@graph[?@type=\'Dataset\'][\'inLanguage\']', 'exactMatch', 'none', '"en"', '"en"', ''),
    ('Basic Metadata', 'Dataset.page', 'str', 'd4d:page skos:exactMatch schema:url', '@graph[?@type=\'Dataset\'][\'url\']', 'exactMatch', 'none', '"https://aireadi.org"', '"https://aireadi.org"', ''),
    ('Basic Metadata', 'Dataset.publisher', 'URI', 'd4d:publisher skos:exactMatch schema:publisher', '@graph[?@type=\'Dataset\'][\'publisher\']', 'exactMatch', 'none', '"UCSD"', '"UCSD"', ''),
    ('Basic Metadata', 'Dataset.version', 'str', 'd4d:version skos:exactMatch schema:version', '@graph[?@type=\'Dataset\'][\'version\']', 'exactMatch', 'none', '"1.0"', '"1.0"', ''),
    ('Basic Metadata', 'Dataset.license', 'str', 'd4d:license skos:exactMatch schema:license', '@graph[?@type=\'Dataset\'][\'license\']', 'exactMatch', 'none', '"CC-BY-4.0"', '"CC-BY-4.0"', ''),
    ('Basic Metadata', 'Dataset.status', 'URI', 'd4d:status skos:exactMatch schema:creativeWorkStatus', '@graph[?@type=\'Dataset\'][\'creativeWorkStatus\']', 'exactMatch', 'none', '"Published"', '"Published"', ''),
    ('Basic Metadata', 'Dataset.conforms_to', 'URI', 'd4d:conforms_to skos:exactMatch schema:conformsTo', '@graph[?@type=\'Dataset\'][\'conformsTo\']', 'exactMatch', 'none', '"https://spec.org"', '"https://spec.org"', ''),
    ('Basic Metadata', 'Dataset.download_url', 'str/URI', 'd4d:download_url skos:exactMatch schema:contentUrl', '@graph[?@type=\'Dataset\'][\'contentUrl\']', 'exactMatch', 'none', '"https://data.org/d.zip"', '"https://data.org/d.zip"', ''),
    ('Basic Metadata', 'Dataset.bytes', 'Int', 'd4d:bytes skos:exactMatch schema:contentSize', '@graph[?@type=\'Dataset\'][\'contentSize\']', 'exactMatch', 'none', '1073741824', '1073741824', ''),
    ('Basic Metadata', 'Dataset.encoding', 'str', 'd4d:encoding skos:closeMatch evi:formats', '@graph[?@type=\'Dataset\'][\'evi:formats\']', 'closeMatch', 'minimal', '"UTF-8"', '"text/csv; charset=UTF-8"', 'MIME type transformation'),
    ('Basic Metadata', 'Dataset.path', 'str', 'd4d:path skos:narrowMatch schema:contentUrl', '@graph[?@type=\'Dataset\'][\'contentUrl\']', 'narrowMatch', 'minimal', '"data/file.csv"', '"https://example.org/data/file.csv"', 'Relative to absolute path'),

    # ====================
    # 2. Dates
    # ====================
    ('Dates', 'Dataset.created_on', 'Date', 'd4d:created_on skos:exactMatch schema:dateCreated', '@graph[?@type=\'Dataset\'][\'dateCreated\']', 'exactMatch', 'none', '"2024-01-15"', '"2024-01-15"', ''),
    ('Dates', 'Dataset.issued', 'Date', 'd4d:issued skos:exactMatch schema:datePublished', '@graph[?@type=\'Dataset\'][\'datePublished\']', 'exactMatch', 'none', '"2024-03-01"', '"2024-03-01"', ''),
    ('Dates', 'Dataset.last_updated_on', 'Date', 'd4d:last_updated_on skos:exactMatch schema:dateModified', '@graph[?@type=\'Dataset\'][\'dateModified\']', 'exactMatch', 'none', '"2024-06-01"', '"2024-06-01"', ''),
    ('Dates', 'Dataset.distribution_dates', 'Date', 'd4d:distribution_dates skos:exactMatch schema:dateCreated', '@graph[?@type=\'Dataset\'][\'dateCreated\']', 'exactMatch', 'none', '"2024-03-01"', '"2024-03-01"', ''),

    # ====================
    # 3. Checksums & Identifiers
    # ====================
    ('Checksums & Identifiers', 'Dataset.doi', 'URI', 'd4d:doi skos:exactMatch schema:identifier', '@graph[?@type=\'Dataset\'][\'identifier\']', 'exactMatch', 'none', '"10.5281/zenodo.123456"', '"10.5281/zenodo.123456"', ''),
    ('Checksums & Identifiers', 'Dataset.md5', 'str', 'd4d:md5 skos:exactMatch evi:md5', '@graph[?@type=\'Dataset\'][\'evi:md5\']', 'exactMatch', 'none', '"a1b2c3d4..."', '"a1b2c3d4..."', ''),
    ('Checksums & Identifiers', 'Dataset.sha256', 'str', 'd4d:sha256 skos:exactMatch evi:sha256', '@graph[?@type=\'Dataset\'][\'evi:sha256\']', 'exactMatch', 'none', '"e5f6a7b8..."', '"e5f6a7b8..."', ''),
    ('Checksums & Identifiers', 'Dataset.hash', 'str', 'd4d:hash skos:exactMatch evi:md5', '@graph[?@type=\'Dataset\'][\'evi:md5\']', 'exactMatch', 'none', '"a1b2c3d4..."', '"a1b2c3d4..."', ''),
    ('Checksums & Identifiers', 'Dataset.was_derived_from', 'str', 'd4d:was_derived_from skos:exactMatch schema:isBasedOn', '@graph[?@type=\'Dataset\'][\'isBasedOn\']', 'exactMatch', 'none', '"10.5281/zenodo.111"', '"10.5281/zenodo.111"', ''),

    # ====================
    # 4. Relationships
    # ====================
    ('Relationships', 'Dataset.resources', 'List', 'd4d:resources skos:relatedMatch schema:hasPart', '@graph[?@type=\'Dataset\'][\'hasPart\']', 'relatedMatch', 'moderate', '[{"@type":"Dataset","name":"Subset A"}]', '{"hasPart":[{"@type":"Dataset","name":"Subset A"}]}', 'Collection structure mapping'),
    ('Relationships', 'DatasetCollection.parent_datasets', 'List', 'd4d:parent_datasets skos:relatedMatch schema:isPartOf', '@graph[?@type=\'Dataset\'][\'isPartOf\']', 'relatedMatch', 'minimal', '[{"@id":"doi:10.123/parent"}]', '{"isPartOf":{"@id":"doi:10.123/parent"}}', ''),
    ('Relationships', 'DatasetCollection.related_datasets', 'List', 'd4d:related_datasets skos:relatedMatch schema:relatedLink', '@graph[?@type=\'Dataset\'][\'relatedLink\']', 'relatedMatch', 'minimal', '[{"@id":"doi:10.123/related"}]', '{"relatedLink":{"@id":"doi:10.123/related"}}', ''),
    ('Relationships', 'Dataset.external_resource', 'str', 'd4d:external_resource skos:closeMatch schema:relatedLink', '@graph[?@type=\'Dataset\'][\'relatedLink\']', 'closeMatch', 'minimal', '"https://pubmed.org/123"', '{"@type":"ScholarlyArticle","url":"https://pubmed.org/123"}', ''),
    ('Relationships', 'Dataset.use_repository', 'str', 'd4d:use_repository skos:relatedMatch schema:relatedLink', '@graph[?@type=\'Dataset\'][\'relatedLink\']', 'relatedMatch', 'minimal', '"https://github.com/org/repo"', '"https://github.com/org/repo"', ''),

    # ====================
    # 5. Creators & Attribution
    # ====================
    ('Creators & Attribution', 'Dataset.creators', 'str', 'd4d:creators skos:closeMatch schema:author', '@graph[?@type=\'Dataset\'][\'author\']', 'closeMatch', 'minimal', '"John Doe, Jane Smith"', '[{"@type":"Person","name":"John Doe"},{"@type":"Person","name":"Jane Smith"}]', 'String to Person/Organization array'),
    ('Creators & Attribution', 'Dataset.created_by', 'Creator', 'd4d:created_by skos:closeMatch schema:creator', '@graph[?@type=\'Dataset\'][\'creator\']', 'closeMatch', 'minimal', '"AI-READI Team"', '{"@type":"Organization","name":"AI-READI Team"}', 'String to object transformation'),
    ('Creators & Attribution', 'Dataset.funders', 'str', 'd4d:funders skos:exactMatch schema:funder', '@graph[?@type=\'Dataset\'][\'funder\']', 'exactMatch', 'none', '"NIH, NSF"', '"NIH, NSF"', ''),

    # ====================
    # 6. RAI Use Cases
    # ====================
    ('RAI Use Cases', 'Dataset.purposes', 'str', 'd4d:purposes skos:closeMatch rai:dataUseCases', '@graph[?@type=\'Dataset\'][\'rai:dataUseCases\']', 'closeMatch', 'minimal', '"Research, education"', '"Research, education"', ''),
    ('RAI Use Cases', 'Dataset.tasks', 'str', 'd4d:tasks skos:exactMatch rai:dataUseCases', '@graph[?@type=\'Dataset\'][\'rai:dataUseCases\']', 'exactMatch', 'none', '"Classification, regression"', '"Classification, regression"', ''),
    ('RAI Use Cases', 'Dataset.intended_uses', 'str', 'd4d:intended_uses skos:exactMatch rai:dataUseCases', '@graph[?@type=\'Dataset\'][\'rai:dataUseCases\']', 'exactMatch', 'none', '"Research on diabetes..."', '"Research on diabetes..."', ''),
    ('RAI Use Cases', 'Dataset.existing_uses', 'str', 'd4d:existing_uses skos:exactMatch rai:dataUseCases', '@graph[?@type=\'Dataset\'][\'rai:dataUseCases\']', 'exactMatch', 'none', '"Diabetes prediction models"', '"Diabetes prediction models"', ''),
    ('RAI Use Cases', 'Dataset.other_tasks', 'str', 'd4d:other_tasks skos:exactMatch rai:dataUseCases', '@graph[?@type=\'Dataset\'][\'rai:dataUseCases\']', 'exactMatch', 'none', '"Risk stratification..."', '"Risk stratification..."', ''),
    ('RAI Use Cases', 'Dataset.discouraged_uses', 'str', 'd4d:discouraged_uses skos:exactMatch rai:prohibitedUses', '@graph[?@type=\'Dataset\'][\'rai:prohibitedUses\']', 'exactMatch', 'none', '"Insurance decisions..."', '"Insurance decisions..."', ''),
    ('RAI Use Cases', 'Dataset.prohibited_uses', 'str', 'd4d:prohibited_uses skos:exactMatch rai:prohibitedUses', '@graph[?@type=\'Dataset\'][\'rai:prohibitedUses\']', 'exactMatch', 'none', '"Surveillance, profiling"', '"Surveillance, profiling"', ''),
    ('RAI Use Cases', 'Dataset.future_use_impacts', 'str', 'd4d:future_use_impacts skos:exactMatch rai:dataSocialImpact', '@graph[?@type=\'Dataset\'][\'rai:dataSocialImpact\']', 'exactMatch', 'none', '"Risk of re-identification..."', '"Risk of re-identification..."', ''),
    ('RAI Use Cases', 'Dataset.addressing_gaps', 'str', 'd4d:addressing_gaps skos:exactMatch d4d:addressingGaps', '@graph[?@type=\'Dataset\'][\'d4d:addressingGaps\']', 'exactMatch', 'none', '"Fill data gap in diabetes..."', '"Fill data gap in diabetes..."', ''),

    # ====================
    # 7. RAI Biases & Limitations
    # ====================
    ('RAI Biases & Limitations', 'Dataset.known_biases', 'str', 'd4d:known_biases skos:exactMatch rai:dataBiases', '@graph[?@type=\'Dataset\'][\'rai:dataBiases\']', 'exactMatch', 'none', '"Sampling bias toward..."', '"Sampling bias toward..."', ''),
    ('RAI Biases & Limitations', 'Dataset.known_limitations', 'str', 'd4d:known_limitations skos:exactMatch rai:dataLimitations', '@graph[?@type=\'Dataset\'][\'rai:dataLimitations\']', 'exactMatch', 'none', '"Small sample size..."', '"Small sample size..."', ''),
    ('RAI Biases & Limitations', 'Dataset.anomalies', 'str', 'd4d:anomalies skos:exactMatch d4d:anomalies', '@graph[?@type=\'Dataset\'][\'d4d:anomalies\']', 'exactMatch', 'none', '"5 outliers detected..."', '"5 outliers detected..."', ''),
    ('RAI Biases & Limitations', 'Dataset.content_warnings', 'str', 'd4d:content_warnings skos:exactMatch d4d:contentWarnings', '@graph[?@type=\'Dataset\'][\'d4d:contentWarnings\']', 'exactMatch', 'none', '"Contains medical images"', '"Contains medical images"', ''),
    ('RAI Biases & Limitations', 'Dataset.errata', 'str', 'd4d:errata skos:exactMatch schema:correction', '@graph[?@type=\'Dataset\'][\'correction\']', 'exactMatch', 'none', '"Bug fix in v1.1..."', '"Bug fix in v1.1..."', ''),
    ('RAI Biases & Limitations', 'Dataset.updates', 'str', 'd4d:updates skos:exactMatch rai:dataReleaseMaintenancePlan', '@graph[?@type=\'Dataset\'][\'rai:dataReleaseMaintenancePlan\']', 'exactMatch', 'none', '"Quarterly updates planned"', '"Quarterly updates planned"', ''),

    # ====================
    # 8. Privacy
    # ====================
    ('Privacy', 'Dataset.sensitive_elements', 'str', 'd4d:sensitive_elements skos:exactMatch rai:personalSensitiveInformation', '@graph[?@type=\'Dataset\'][\'rai:personalSensitiveInformation\']', 'exactMatch', 'none', '"Race, ethnicity, health status"', '"Race, ethnicity, health status"', ''),
    ('Privacy', 'Dataset.confidential_elements', 'str', 'd4d:confidential_elements skos:exactMatch rai:personalSensitiveInformation', '@graph[?@type=\'Dataset\'][\'rai:personalSensitiveInformation\']', 'exactMatch', 'none', '"PHI, genetic data"', '"PHI, genetic data"', ''),
    ('Privacy', 'Dataset.is_deidentified', 'bool', 'd4d:is_deidentified skos:narrowMatch rai:confidentialityLevel', '@graph[?@type=\'Dataset\'][\'rai:confidentialityLevel\']', 'narrowMatch', 'minimal', 'true', '"de-identified"', 'Boolean to string'),
    ('Privacy', 'Dataset.data_protection_impacts', 'str', 'd4d:data_protection_impacts skos:exactMatch rai:dataSocialImpact', '@graph[?@type=\'Dataset\'][\'rai:dataSocialImpact\']', 'exactMatch', 'none', '"DPIA completed 2024-01"', '"DPIA completed 2024-01"', ''),
    ('Privacy', 'Dataset.regulatory_restrictions', 'str', 'd4d:regulatory_restrictions skos:closeMatch schema:conditionsOfAccess', '@graph[?@type=\'Dataset\'][\'conditionsOfAccess\']', 'closeMatch', 'minimal', '"HIPAA, GDPR"', '"HIPAA, GDPR"', ''),

    # ====================
    # 9. Data Collection
    # ====================
    ('Data Collection', 'Dataset.acquisition_methods', 'str', 'd4d:acquisition_methods skos:exactMatch rai:dataCollection', '@graph[?@type=\'Dataset\'][\'rai:dataCollection\']', 'exactMatch', 'none', '"Clinical sensors, EHR export"', '"Clinical sensors, EHR export"', ''),
    ('Data Collection', 'Dataset.collection_mechanisms', 'str', 'd4d:collection_mechanisms skos:exactMatch rai:dataCollection', '@graph[?@type=\'Dataset\'][\'rai:dataCollection\']', 'exactMatch', 'none', '"Automated API extraction"', '"Automated API extraction"', ''),
    ('Data Collection', 'Dataset.collection_timeframes', 'str', 'd4d:collection_timeframes skos:exactMatch d4d:dataCollectionTimeframe', '@graph[?@type=\'Dataset\'][\'d4d:dataCollectionTimeframe\']', 'exactMatch', 'none', '"2023-01 to 2024-06"', '"2023-01 to 2024-06"', ''),
    ('Data Collection', 'Dataset.data_collectors', 'List', 'd4d:data_collectors skos:relatedMatch schema:contributor', '@graph[?@type=\'Dataset\'][\'contributor\']', 'relatedMatch', 'moderate', '[{"name":"Research assistants","compensation":"$20/hr"}]', '{"contributor":[{"@type":"Person","name":"Research assistants"}]}', 'Compensation detail lost'),
    ('Data Collection', 'Dataset.raw_data_sources', 'str', 'd4d:raw_data_sources skos:exactMatch rai:dataCollectionRawData', '@graph[?@type=\'Dataset\'][\'rai:dataCollectionRawData\']', 'exactMatch', 'none', '"Epic EHR, lab LIMS"', '"Epic EHR, lab LIMS"', ''),
    ('Data Collection', 'Dataset.missing_data_documentation', 'str', 'd4d:missing_data_documentation skos:exactMatch rai:dataCollectionMissingData', '@graph[?@type=\'Dataset\'][\'rai:dataCollectionMissingData\']', 'exactMatch', 'none', '"15% missing in glucose..."', '"15% missing in glucose..."', ''),

    # ====================
    # 10. Preprocessing
    # ====================
    ('Preprocessing', 'Dataset.cleaning_strategies', 'List[CleaningStrategy]', 'd4d:cleaning_strategies skos:closeMatch rai:dataManipulationProtocol', '@graph[?@type=\'Dataset\'][\'rai:dataManipulationProtocol\']', 'closeMatch', 'minimal', '[{"description":"Removed duplicates","step_type":"data_cleaning"}]', '"Removed duplicate records using MD5 hash"', 'Structured array to string'),
    ('Preprocessing', 'CleaningStrategy.description', 'str', 'd4d:cleaning_strategies[].description', 'rai:dataManipulationProtocol', 'closeMatch', 'moderate', '"Removed duplicates"', 'Flattened into protocol string', 'Array element lost'),
    ('Preprocessing', 'CleaningStrategy.step_type', 'str', 'd4d:cleaning_strategies[].step_type', 'rai:dataManipulationProtocol', 'closeMatch', 'high', '"data_cleaning"', 'Lost in flattening', 'Enumeration lost'),
    ('Preprocessing', 'CleaningStrategy.pipeline_step', 'int', 'd4d:cleaning_strategies[].pipeline_step', 'rai:dataManipulationProtocol', 'closeMatch', 'high', '20', 'Lost in flattening', 'Step order lost'),
    ('Preprocessing', 'Dataset.preprocessing_strategies', 'List[PreprocessingStrategy]', 'd4d:preprocessing_strategies skos:closeMatch rai:dataPreprocessingProtocol', '@graph[?@type=\'Dataset\'][\'rai:dataPreprocessingProtocol\']', 'closeMatch', 'minimal', '[{"description":"Normalized values","step_type":"normalization"}]', '"Normalized glucose values to 0-1 range"', 'Structured array to string'),
    ('Preprocessing', 'PreprocessingStrategy.description', 'str', 'd4d:preprocessing_strategies[].description', 'rai:dataPreprocessingProtocol', 'closeMatch', 'moderate', '"Normalized values"', 'Flattened into protocol string', 'Array element lost'),
    ('Preprocessing', 'PreprocessingStrategy.step_type', 'str', 'd4d:preprocessing_strategies[].step_type', 'rai:dataPreprocessingProtocol', 'closeMatch', 'high', '"normalization"', 'Lost in flattening', 'Enumeration lost'),
    ('Preprocessing', 'PreprocessingStrategy.pipeline_step', 'int', 'd4d:preprocessing_strategies[].pipeline_step', 'rai:dataPreprocessingProtocol', 'closeMatch', 'high', '10', 'Lost in flattening', 'Step order lost'),
    ('Preprocessing', 'Dataset.imputation_protocols', 'str', 'd4d:imputation_protocols skos:exactMatch rai:imputationProtocol', '@graph[?@type=\'Dataset\'][\'rai:imputationProtocol\']', 'exactMatch', 'none', '"MICE for missing values"', '"MICE for missing values"', ''),
    ('Preprocessing', 'Dataset.raw_sources', 'str', 'd4d:raw_sources skos:exactMatch rai:dataCollectionRawData', '@graph[?@type=\'Dataset\'][\'rai:dataCollectionRawData\']', 'exactMatch', 'none', '"Epic EHR, lab LIMS"', '"Epic EHR, lab LIMS"', ''),
    ('Preprocessing', 'Dataset.compression', 'CompressionEnum', 'd4d:compression skos:closeMatch evi:formats', '@graph[?@type=\'Dataset\'][\'evi:formats\']', 'closeMatch', 'minimal', '"gzip"', '"application/gzip"', 'Enum to MIME type'),
    ('Preprocessing', 'Dataset.distribution_formats', 'List[str]', 'd4d:distribution_formats skos:exactMatch evi:formats', '@graph[?@type=\'Dataset\'][\'evi:formats\']', 'exactMatch', 'none', '"CSV, Parquet"', '"CSV, Parquet"', ''),

    # ====================
    # 11. Annotation
    # ====================
    ('Annotation', 'Dataset.labeling_strategies', 'List[LabelingStrategy]', 'd4d:labeling_strategies skos:closeMatch rai:dataAnnotationProtocol', '@graph[?@type=\'Dataset\'][\'rai:dataAnnotationProtocol\']', 'closeMatch', 'minimal', '[{"description":"Manual annotation","annotator_type":"expert"}]', '"Expert clinicians labeled diagnoses"', 'Structured array to string'),
    ('Annotation', 'LabelingStrategy.description', 'str', 'd4d:labeling_strategies[].description', 'rai:dataAnnotationProtocol', 'closeMatch', 'moderate', '"Manual annotation"', 'Flattened into protocol string', 'Array element lost'),
    ('Annotation', 'LabelingStrategy.annotator_type', 'str', 'd4d:labeling_strategies[].annotator_type', 'rai:dataAnnotationProtocol', 'closeMatch', 'high', '"expert"', 'Lost in flattening', 'Annotator type lost'),
    ('Annotation', 'LabelingStrategy.evidence_type', 'ECO', 'd4d:labeling_strategies[].evidence_type', 'rai:dataAnnotationProtocol', 'closeMatch', 'high', 'ECO:0000217', 'Lost - no ECO support in RO-Crate', 'ECO ontology lost'),
    ('Annotation', 'Dataset.annotation_analyses', 'List[AnnotationAnalysis]', 'd4d:annotation_analyses skos:closeMatch rai:dataAnnotationAnalysis', '@graph[?@type=\'Dataset\'][\'rai:dataAnnotationAnalysis\']', 'closeMatch', 'minimal', '[{"description":"Inter-rater reliability 0.89"}]', '"Inter-rater reliability: 0.89 (Cohen\'s kappa)"', 'Structured array to string'),
    ('Annotation', 'AnnotationAnalysis.description', 'str', 'd4d:annotation_analyses[].description', 'rai:dataAnnotationAnalysis', 'closeMatch', 'moderate', '"Inter-rater reliability 0.89"', 'Flattened into analysis string', 'Array element lost'),
    ('Annotation', 'Dataset.machine_annotation_analyses', 'List[MachineAnnotation]', 'd4d:machine_annotation_analyses skos:closeMatch rai:machineAnnotationTools', '@graph[?@type=\'Dataset\'][\'rai:machineAnnotationTools\']', 'closeMatch', 'minimal', '[{"tool_name":"spaCy","version":"3.5"}]', '"spaCy v3.5 for NER"', 'Structured array to string'),
    ('Annotation', 'MachineAnnotation.tool_name', 'str', 'd4d:machine_annotation_analyses[].tool_name', 'rai:machineAnnotationTools', 'closeMatch', 'moderate', '"spaCy"', 'Flattened with version', 'Tool details lost'),

    # ====================
    # 12. Ethics & Compliance
    # ====================
    ('Ethics & Compliance', 'Dataset.ethical_reviews', 'str', 'd4d:ethical_reviews skos:exactMatch rai:ethicalReview', '@graph[?@type=\'Dataset\'][\'rai:ethicalReview\']', 'exactMatch', 'none', '"IRB #2023-456 approved"', '"IRB #2023-456 approved"', ''),
    ('Ethics & Compliance', 'Dataset.human_subject_research', 'str', 'd4d:human_subject_research skos:exactMatch d4d:humanSubject', '@graph[?@type=\'Dataset\'][\'d4d:humanSubject\']', 'exactMatch', 'none', '"Yes, IRB approved"', '"Yes, IRB approved"', ''),
    ('Ethics & Compliance', 'Dataset.at_risk_populations', 'str', 'd4d:at_risk_populations skos:exactMatch d4d:atRiskPopulations', '@graph[?@type=\'Dataset\'][\'d4d:atRiskPopulations\']', 'exactMatch', 'none', '"Children excluded"', '"Children excluded"', ''),
    ('Ethics & Compliance', 'Dataset.informed_consent', 'str', 'd4d:informed_consent skos:exactMatch d4d:informedConsent', '@graph[?@type=\'Dataset\'][\'d4d:informedConsent\']', 'exactMatch', 'none', '"Written consent obtained"', '"Written consent obtained"', ''),
    ('Ethics & Compliance', 'Dataset.license_and_use_terms', 'str', 'd4d:license_and_use_terms skos:closeMatch schema:license', '@graph[?@type=\'Dataset\'][\'license\']', 'closeMatch', 'moderate', '"CC-BY-4.0, attribution required"', '{"license":"CC-BY-4.0","conditionsOfAccess":"Attribution required"}', 'Multi-property merge'),
    ('Ethics & Compliance', 'Dataset.ip_restrictions', 'str', 'd4d:ip_restrictions skos:closeMatch schema:conditionsOfAccess', '@graph[?@type=\'Dataset\'][\'conditionsOfAccess\']', 'closeMatch', 'minimal', '"No commercial use"', '"No commercial use"', ''),
    ('Ethics & Compliance', 'Dataset.extension_mechanism', 'str', 'd4d:extension_mechanism skos:closeMatch schema:license', '@graph[?@type=\'Dataset\'][\'license\']', 'closeMatch', 'moderate', '"GitHub PRs accepted"', '"GitHub PRs accepted"', ''),
    ('Ethics & Compliance', 'Dataset.retention_limit', 'str', 'd4d:retention_limit skos:narrowMatch schema:conditionsOfAccess', '@graph[?@type=\'Dataset\'][\'conditionsOfAccess\']', 'narrowMatch', 'minimal', '"5 years"', '"Data retained for 5 years per IRB protocol"', ''),
    ('Ethics & Compliance', 'EthicalReview.irb_id', 'str', 'd4d:ethical_reviews.irb_id', 'rai:ethicalReview', 'closeMatch', 'moderate', '"IRB-2023-456"', 'Embedded in ethicalReview string', 'Structure lost'),
    ('Ethics & Compliance', 'HumanSubjectResearch.exemption', 'str', 'd4d:human_subject_research.exemption', 'd4d:humanSubject', 'closeMatch', 'moderate', '"45 CFR 46.104(d)(4)"', 'Embedded in humanSubject string', 'Structure lost'),

    # ====================
    # 13. Governance
    # ====================
    ('Governance', 'DatasetCollection.data_governance_committee', 'str', 'd4d:data_governance_committee', '@graph[?@type=\'Dataset\'][\'dataGovernanceCommittee\']', 'exactMatch', 'none', '"Data Governance Board"', '"Data Governance Board"', 'D4D-embedded field'),
    ('Governance', 'DatasetCollection.principal_investigator', 'str', 'd4d:principal_investigator', '@graph[?@type=\'Dataset\'][\'principalInvestigator\']', 'exactMatch', 'none', '"Dr. Jane Doe"', '"Dr. Jane Doe"', 'D4D-embedded field'),
    ('Governance', 'Dataset.modified_by', 'Creator', 'd4d:modified_by skos:closeMatch schema:contributor', '@graph[?@type=\'Dataset\'][\'contributor\']', 'closeMatch', 'minimal', '"Data Team"', '{"@type":"Organization","name":"Data Team"}', 'String to object'),
    ('Governance', 'Dataset.maintainers', 'str', 'd4d:maintainers skos:relatedMatch schema:maintainer', '@graph[?@type=\'Dataset\'][\'maintainer\']', 'relatedMatch', 'minimal', '"Data team at UCSD"', '"Data team at UCSD"', ''),
    ('Governance', 'DatasetCollection.contact_email', 'str', 'd4d:contact_email', '@graph[?@type=\'Dataset\'][\'contactEmail\']', 'exactMatch', 'none', '"data@example.org"', '"data@example.org"', 'D4D-embedded field'),
    ('Governance', 'DatasetCollection.data_sharing_agreement', 'str', 'd4d:data_sharing_agreement', '@graph[?@type=\'Dataset\'][\'dataSharingAgreement\']', 'exactMatch', 'none', '"DUA required"', '"DUA required"', 'D4D-embedded field'),

    # ====================
    # 14. Maintenance
    # ====================
    ('Maintenance', 'Dataset.version_access', 'str', 'd4d:version_access skos:relatedMatch schema:version', '@graph[?@type=\'Dataset\'][\'version\']', 'relatedMatch', 'minimal', '"All versions available"', '"All versions available"', ''),
    ('Maintenance', 'Maintenance.frequency', 'str', 'd4d:maintenance.frequency', 'rai:dataReleaseMaintenancePlan', 'closeMatch', 'moderate', '"Quarterly"', 'Embedded in maintenance plan string', 'Structure lost'),
    ('Maintenance', 'Maintenance.versioning_strategy', 'str', 'd4d:maintenance.versioning_strategy', 'rai:dataReleaseMaintenancePlan', 'closeMatch', 'moderate', '"Semantic versioning"', 'Embedded in maintenance plan string', 'Structure lost'),

    # ====================
    # 15. FAIRSCAPE EVI
    # ====================
    ('FAIRSCAPE EVI', 'EvidenceMetadata.dataset_count', 'int', 'evi:datasetCount', '@graph[?@type=\'ROCrate\'][\'evi:datasetCount\']', 'exactMatch', 'none', '5', '5', 'FAIRSCAPE-specific'),
    ('FAIRSCAPE EVI', 'EvidenceMetadata.computation_count', 'int', 'evi:computationCount', '@graph[?@type=\'ROCrate\'][\'evi:computationCount\']', 'exactMatch', 'none', '10', '10', 'FAIRSCAPE-specific'),
    ('FAIRSCAPE EVI', 'EvidenceMetadata.software_count', 'int', 'evi:softwareCount', '@graph[?@type=\'ROCrate\'][\'evi:softwareCount\']', 'exactMatch', 'none', '3', '3', 'FAIRSCAPE-specific'),
    ('FAIRSCAPE EVI', 'EvidenceMetadata.schema_count', 'int', 'evi:schemaCount', '@graph[?@type=\'ROCrate\'][\'evi:schemaCount\']', 'exactMatch', 'none', '1', '1', 'FAIRSCAPE-specific'),
    ('FAIRSCAPE EVI', 'EvidenceMetadata.total_entities', 'int', 'evi:totalEntities', '@graph[?@type=\'ROCrate\'][\'evi:totalEntities\']', 'exactMatch', 'none', '25', '25', 'FAIRSCAPE-specific'),
    ('FAIRSCAPE EVI', 'EvidenceMetadata.entities_with_summary_stats', 'int', 'evi:entitiesWithSummaryStats', '@graph[?@type=\'ROCrate\'][\'evi:entitiesWithSummaryStats\']', 'exactMatch', 'none', '15', '15', 'FAIRSCAPE-specific'),
    ('FAIRSCAPE EVI', 'EvidenceMetadata.entities_with_checksums', 'int', 'evi:entitiesWithChecksums', '@graph[?@type=\'ROCrate\'][\'evi:entitiesWithChecksums\']', 'exactMatch', 'none', '20', '20', 'FAIRSCAPE-specific'),
    ('FAIRSCAPE EVI', 'EvidenceMetadata.total_content_size_bytes', 'int', 'evi:totalContentSizeBytes', '@graph[?@type=\'ROCrate\'][\'evi:totalContentSizeBytes\']', 'exactMatch', 'none', '10737418240', '10737418240', 'FAIRSCAPE-specific'),
    ('FAIRSCAPE EVI', 'EvidenceMetadata.formats', 'List[str]', 'evi:formats', '@graph[?@type=\'ROCrate\'][\'evi:formats\']', 'exactMatch', 'none', '["CSV", "JSON"]', '["CSV", "JSON"]', 'FAIRSCAPE-specific'),

    # ====================
    # 16. D4D-Embedded
    # ====================
    ('D4D-Embedded', 'DatasetCollection.completeness', 'str', 'd4d:completeness', '@graph[?@type=\'Dataset\'][\'additionalProperty\'][?name=\'Completeness\'][\'value\']', 'exactMatch', 'none', '"95% complete"', '"95% complete"', 'additionalProperty pattern'),
    ('D4D-Embedded', 'DatasetCollection.summary_statistics', 'str', 'd4d:summary_statistics', '@graph[?@type=\'Dataset\'][\'hasSummaryStatistics\']', 'exactMatch', 'none', '"Mean age: 45.2 years"', '"Mean age: 45.2 years"', 'D4D-embedded'),
    ('D4D-Embedded', 'DatasetCollection.quality_control', 'str', 'd4d:quality_control', '@graph[?@type=\'Dataset\'][\'additionalProperty\'][?name=\'Quality Control\'][\'value\']', 'exactMatch', 'none', '"Automated QC checks"', '"Automated QC checks"', 'additionalProperty pattern'),
    ('D4D-Embedded', 'DatasetCollection.funding_and_acknowledgements', 'str', 'd4d:funding_and_acknowledgements', '@graph[?@type=\'Dataset\'][\'funder\']', 'closeMatch', 'minimal', '"NIH R01-123456"', '"NIH R01-123456"', 'Maps to funder'),
    ('D4D-Embedded', 'DatasetCollection.provenance_and_lineage', 'str', 'd4d:provenance_and_lineage', '@graph[?@type=\'Dataset\'][\'generatedBy\']', 'closeMatch', 'minimal', '"Derived from study XYZ"', '{"generatedBy":{"@id":"study-xyz"}}', 'Maps to generatedBy'),

    # ====================
    # 17. Quality
    # ====================
    ('Quality', 'ValidationMetrics.validation_method', 'str', 'd4d:validation_method', '@graph[?@type=\'Dataset\'][\'additionalProperty\'][?name=\'Validation Method\'][\'value\']', 'exactMatch', 'none', '"10-fold cross-validation"', '"10-fold cross-validation"', 'additionalProperty pattern'),
    ('Quality', 'QualityControl.accuracy', 'float', 'd4d:accuracy', '@graph[?@type=\'Dataset\'][\'additionalProperty\'][?name=\'Accuracy\'][\'value\']', 'exactMatch', 'none', '0.95', '0.95', 'additionalProperty pattern'),
    ('Quality', 'QualityControl.data_quality_report', 'str', 'd4d:data_quality_report', '@graph[?@type=\'Dataset\'][\'additionalProperty\'][?name=\'Data Quality Report\'][\'value\']', 'exactMatch', 'none', '"QC report at https://..."', '"QC report at https://..."', 'additionalProperty pattern'),
    ('Quality', 'QualityControl.fda_compliant', 'bool', 'd4d:fda_compliant', '@graph[?@type=\'Dataset\'][\'fdaRegulated\']', 'exactMatch', 'none', 'true', 'true', 'D4D-embedded'),

    # ====================
    # 18. Format
    # ====================
    ('Format', 'Dataset.dialect', 'str', 'd4d:dialect skos:closeMatch schema:encodingFormat', '@graph[?@type=\'Dataset\'][\'encodingFormat\']', 'closeMatch', 'minimal', '{"delimiter":",","header":true}', '"text/csv; header=present; delimiter=,"', 'Structured to MIME parameter'),
    ('Format', 'Dataset.media_type', 'str', 'd4d:media_type skos:closeMatch schema:encodingFormat', '@graph[?@type=\'Dataset\'][\'encodingFormat\']', 'closeMatch', 'minimal', '"text/csv"', '"text/csv"', ''),
    ('Format', 'Dataset.is_tabular', 'bool', 'd4d:is_tabular skos:narrowMatch schema:encodingFormat', '@graph[?@type=\'Dataset\'][\'encodingFormat\']', 'narrowMatch', 'minimal', 'true', '"text/csv"', 'Boolean to format inference'),
    ('Format', 'FormatDialect.delimiter', 'str', 'd4d:dialect.delimiter', 'encodingFormat MIME parameter', 'closeMatch', 'moderate', '","', '"delimiter=,"', 'Nested property lost'),
    ('Format', 'FormatDialect.header', 'bool', 'd4d:dialect.header', 'encodingFormat MIME parameter', 'closeMatch', 'moderate', 'true', '"header=present"', 'Nested property lost'),

    # ====================
    # 19. Unmapped
    # ====================
    ('Unmapped', 'Dataset.variables', 'List[Variable]', 'No mapping', 'N/A', 'unmapped', 'high', '[{"name":"age","type":"integer"}]', 'N/A - No RO-Crate equivalent', 'Complex variable schema'),
    ('Unmapped', 'Dataset.sampling_strategies', 'List[SamplingStrategy]', 'Partial: d4d:samplingStrategy', '@graph[?@type=\'Dataset\'][\'d4d:samplingStrategy\']', 'relatedMatch', 'moderate', '[{"strategy":"stratified","details":"..."}]', '"Stratified sampling"', 'Structured to string'),
    ('Unmapped', 'Dataset.subsets', 'List[Subset]', 'Partial: schema:hasPart', '@graph[?@type=\'Dataset\'][\'hasPart\']', 'relatedMatch', 'high', '[{"is_data_split":"train","is_sub_population":"adults"}]', '{"hasPart":[{"name":"Training set"}]}', 'Complex structure lost'),
    ('Unmapped', 'Dataset.instances', 'Instance', 'Partial: schema:variableMeasured', '@graph[?@type=\'Dataset\'][\'variableMeasured\']', 'relatedMatch', 'high', '{"data_topic":"Patient","instance_type":"record","counts":1000}', '"1000 patient records"', 'Structured to string'),
    ('Unmapped', 'Dataset.subpopulations', 'List[SubpopulationElement]', 'Partial: schema:variableMeasured', '@graph[?@type=\'Dataset\'][\'variableMeasured\']', 'relatedMatch', 'moderate', '[{"subpopulation_elements_present":"age,gender"}]', '"Demographics: age, gender"', 'Structured to string'),
    ('Unmapped', 'Instance.data_topic', 'str', 'No mapping', 'N/A', 'unmapped', 'high', '"Patient"', 'N/A', 'Nested property lost'),
    ('Unmapped', 'Instance.instance_type', 'str', 'No mapping', 'N/A', 'unmapped', 'high', '"record"', 'N/A', 'Nested property lost'),
    ('Unmapped', 'Instance.counts', 'int', 'No mapping', 'N/A', 'unmapped', 'high', '1000', 'N/A', 'Nested property lost'),
    ('Unmapped', 'Subset.is_data_split', 'str', 'No mapping', 'N/A', 'unmapped', 'high', '"train"', 'N/A', 'Nested property lost'),
    ('Unmapped', 'Subset.is_sub_population', 'str', 'No mapping', 'N/A', 'unmapped', 'high', '"adults"', 'N/A', 'Nested property lost'),
    ('Unmapped', 'Variable.name', 'str', 'No mapping', 'N/A', 'unmapped', 'high', '"age"', 'N/A', 'Variable schema unsupported'),
    ('Unmapped', 'Variable.type', 'str', 'No mapping', 'N/A', 'unmapped', 'high', '"integer"', 'N/A', 'Variable schema unsupported'),
    ('Unmapped', 'SamplingStrategy.strategy_type', 'str', 'Partial', 'd4d:samplingStrategy', 'relatedMatch', 'moderate', '"stratified"', 'Embedded in string', 'Type lost'),
    ('Unmapped', 'SamplingStrategy.details', 'str', 'Partial', 'd4d:samplingStrategy', 'relatedMatch', 'moderate', '"Stratified by age groups"', 'Embedded in string', 'Detail lost'),
]


def generate_interface_mapping(output_path: Path):
    """Generate comprehensive interface mapping TSV file."""

    with open(output_path, 'w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f, delimiter='\t')
        writer.writerow(HEADERS)

        for row in MAPPINGS:
            writer.writerow(row)

    print(f"✓ Interface mapping created: {output_path}")
    print(f"  Total mappings: {len(MAPPINGS)}")

    # Calculate statistics
    categories = {}
    mapping_types = {}
    loss_levels = {}

    for row in MAPPINGS:
        category = row[0]
        mapping_type = row[5]
        loss = row[6]

        categories[category] = categories.get(category, 0) + 1
        mapping_types[mapping_type] = mapping_types.get(mapping_type, 0) + 1
        loss_levels[loss] = loss_levels.get(loss, 0) + 1

    print("\n  Categories:")
    for cat, count in sorted(categories.items()):
        print(f"    {cat}: {count} fields")

    print("\n  Mapping types:")
    for mtype, count in sorted(mapping_types.items()):
        pct = (count / len(MAPPINGS)) * 100
        print(f"    {mtype}: {count} ({pct:.1f}%)")

    print("\n  Information loss:")
    for loss, count in sorted(loss_levels.items()):
        pct = (count / len(MAPPINGS)) * 100
        print(f"    {loss}: {count} ({pct:.1f}%)")


if __name__ == '__main__':
    script_dir = Path(__file__).parent
    repo_root = script_dir.parent.parent.parent

    output_file = repo_root / 'data' / 'ro-crate_mapping' / 'd4d_rocrate_interface_mapping.tsv'

    generate_interface_mapping(output_file)
