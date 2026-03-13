# D4D Schema Coverage Analysis: RO-Crate Mapping vs Full Schema

**Generated:** 2026-03-09

This report analyzes the coverage of the D4D (Datasheets for Datasets) schema by the RO-Crate mapping file.

## Section 1: Coverage Summary

- **Total D4D classes**: 74
- **Total D4D attributes**: 680
- **Attributes in RO-Crate mapping**: 82
- **Attributes with coverage**: 272 (40.0%)
- **Attributes with direct mapping**: 238 (35.0%)
- **Attributes requiring transformation**: 34

## Section 2: Classes Completely Covered

**Total**: 0 classes with 100% attribute coverage

*No classes have 100% coverage.*

## Section 3: Classes Partially Covered

**Total**: 73 classes with partial attribute coverage

### Dataset (Core module) - 87.9% coverage
- **Total attributes**: 91
- **Covered**: 80 attributes
- **Missing**: 11 attributes

**Covered attributes** (80):
  - ✓ `acquisition_methods`
  - ✓ `addressing_gaps`
  - ✓ `annotation_analyses`
  - ✓ `anomalies`
  - ✓ `bytes`
  - ✓ `cleaning_strategies`
  - ✓ `collection_mechanisms`
  - ✓ `collection_timeframes`
  - ✓ `compression`
  - ✓ `confidential_elements`
  - ✓ `conforms_to`
  - ✓ `content_warnings`
  - ✓ `created_by`
  - ✓ `created_on`
  - ✓ `creators`
  - ~ `data_collectors`
  - ✓ `data_protection_impacts`
  - ✓ `description`
  - ~ `dialect`
  - ✓ `discouraged_uses`
  - ✓ `distribution_dates`
  - ✓ `distribution_formats`
  - ✓ `doi`
  - ✓ `download_url`
  - ✓ `encoding`
  - ✓ `errata`
  - ✓ `ethical_reviews`
  - ✓ `existing_uses`
  - ~ `extension_mechanism`
  - ✓ `funders`
  - ✓ `future_use_impacts`
  - ✓ `hash`
  - ✓ `human_subject_research`
  - ✓ `imputation_protocols`
  - ✓ `informed_consent`
  - ~ `instances`
  - ✓ `intended_uses`
  - ✓ `ip_restrictions`
  - ~ `is_deidentified`
  - ~ `is_tabular`
  - ✓ `issued`
  - ✓ `keywords`
  - ✓ `known_biases`
  - ✓ `known_limitations`
  - ✓ `labeling_strategies`
  - ✓ `language`
  - ✓ `last_updated_on`
  - ✓ `license`
  - ✓ `license_and_use_terms`
  - ~ `maintainers`
  - ✓ `md5`
  - ~ `media_type`
  - ✓ `missing_data_documentation`
  - ✓ `modified_by`
  - ✓ `other_tasks`
  - ✓ `page`
  - ✓ `path`
  - ✓ `preprocessing_strategies`
  - ✓ `prohibited_uses`
  - ✓ `publisher`
  - ~ `purposes`
  - ✓ `raw_data_sources`
  - ✓ `raw_sources`
  - ✓ `regulatory_restrictions`
  - ~ `resources`
  - ~ `retention_limit`
  - ~ `sampling_strategies`
  - ✓ `sensitive_elements`
  - ✓ `sha256`
  - ✓ `status`
  - ~ `subpopulations`
  - ~ `subsets`
  - ✓ `tasks`
  - ✓ `title`
  - ✓ `updates`
  - ~ `use_repository`
  - ✓ `version`
  - ~ `version_access`
  - ✓ `vulnerable_populations`
  - ✓ `was_derived_from`

**Missing attributes** (11):
  - ✗ `citation`
  - ✗ `conforms_to_class`
  - ✗ `conforms_to_schema`
  - ✗ `external_resources`
  - ✗ `format`
  - ✗ `id`
  - ✗ `machine_annotation_tools`
  - ✗ `name`
  - ✗ `parent_datasets`
  - ✗ `related_datasets`
  - ✗ `variables`

### DataSubset (Core module) - 86.0% coverage
- **Total attributes**: 93
- **Covered**: 80 attributes
- **Missing**: 13 attributes

**Covered attributes** (80):
  - ✓ `acquisition_methods`
  - ✓ `addressing_gaps`
  - ✓ `annotation_analyses`
  - ✓ `anomalies`
  - ✓ `bytes`
  - ✓ `cleaning_strategies`
  - ✓ `collection_mechanisms`
  - ✓ `collection_timeframes`
  - ✓ `compression`
  - ✓ `confidential_elements`
  - ✓ `conforms_to`
  - ✓ `content_warnings`
  - ✓ `created_by`
  - ✓ `created_on`
  - ✓ `creators`
  - ~ `data_collectors`
  - ✓ `data_protection_impacts`
  - ✓ `description`
  - ~ `dialect`
  - ✓ `discouraged_uses`
  - ✓ `distribution_dates`
  - ✓ `distribution_formats`
  - ✓ `doi`
  - ✓ `download_url`
  - ✓ `encoding`
  - ✓ `errata`
  - ✓ `ethical_reviews`
  - ✓ `existing_uses`
  - ~ `extension_mechanism`
  - ✓ `funders`
  - ✓ `future_use_impacts`
  - ✓ `hash`
  - ✓ `human_subject_research`
  - ✓ `imputation_protocols`
  - ✓ `informed_consent`
  - ~ `instances`
  - ✓ `intended_uses`
  - ✓ `ip_restrictions`
  - ~ `is_deidentified`
  - ~ `is_tabular`
  - ✓ `issued`
  - ✓ `keywords`
  - ✓ `known_biases`
  - ✓ `known_limitations`
  - ✓ `labeling_strategies`
  - ✓ `language`
  - ✓ `last_updated_on`
  - ✓ `license`
  - ✓ `license_and_use_terms`
  - ~ `maintainers`
  - ✓ `md5`
  - ~ `media_type`
  - ✓ `missing_data_documentation`
  - ✓ `modified_by`
  - ✓ `other_tasks`
  - ✓ `page`
  - ✓ `path`
  - ✓ `preprocessing_strategies`
  - ✓ `prohibited_uses`
  - ✓ `publisher`
  - ~ `purposes`
  - ✓ `raw_data_sources`
  - ✓ `raw_sources`
  - ✓ `regulatory_restrictions`
  - ~ `resources`
  - ~ `retention_limit`
  - ~ `sampling_strategies`
  - ✓ `sensitive_elements`
  - ✓ `sha256`
  - ✓ `status`
  - ~ `subpopulations`
  - ~ `subsets`
  - ✓ `tasks`
  - ✓ `title`
  - ✓ `updates`
  - ~ `use_repository`
  - ✓ `version`
  - ~ `version_access`
  - ✓ `vulnerable_populations`
  - ✓ `was_derived_from`

**Missing attributes** (13):
  - ✗ `citation`
  - ✗ `conforms_to_class`
  - ✗ `conforms_to_schema`
  - ✗ `external_resources`
  - ✗ `format`
  - ✗ `id`
  - ✗ `is_data_split`
  - ✗ `is_subpopulation`
  - ✗ `machine_annotation_tools`
  - ✗ `name`
  - ✗ `parent_datasets`
  - ✗ `related_datasets`
  - ✗ `variables`

### DatasetCollection (Core module) - 83.3% coverage
- **Total attributes**: 24
- **Covered**: 20 attributes
- **Missing**: 4 attributes

**Covered attributes** (20):
  - ✓ `compression`
  - ✓ `conforms_to`
  - ✓ `created_by`
  - ✓ `created_on`
  - ✓ `description`
  - ✓ `doi`
  - ✓ `download_url`
  - ✓ `issued`
  - ✓ `keywords`
  - ✓ `language`
  - ✓ `last_updated_on`
  - ✓ `license`
  - ✓ `modified_by`
  - ✓ `page`
  - ✓ `publisher`
  - ~ `resources`
  - ✓ `status`
  - ✓ `title`
  - ✓ `version`
  - ✓ `was_derived_from`

**Missing attributes** (4):
  - ✗ `conforms_to_class`
  - ✗ `conforms_to_schema`
  - ✗ `id`
  - ✗ `name`

### Information (Base module) - 82.6% coverage
- **Total attributes**: 23
- **Covered**: 19 attributes
- **Missing**: 4 attributes

**Covered attributes** (19):
  - ✓ `compression`
  - ✓ `conforms_to`
  - ✓ `created_by`
  - ✓ `created_on`
  - ✓ `description`
  - ✓ `doi`
  - ✓ `download_url`
  - ✓ `issued`
  - ✓ `keywords`
  - ✓ `language`
  - ✓ `last_updated_on`
  - ✓ `license`
  - ✓ `modified_by`
  - ✓ `page`
  - ✓ `publisher`
  - ✓ `status`
  - ✓ `title`
  - ✓ `version`
  - ✓ `was_derived_from`

**Missing attributes** (4):
  - ✗ `conforms_to_class`
  - ✗ `conforms_to_schema`
  - ✗ `id`
  - ✗ `name`

### Software (Base module) - 50.0% coverage
- **Total attributes**: 6
- **Covered**: 3 attributes
- **Missing**: 3 attributes

**Covered attributes** (3):
  - ✓ `description`
  - ✓ `license`
  - ✓ `version`

**Missing attributes** (3):
  - ✗ `id`
  - ✗ `name`
  - ✗ `url`

### NamedThing (Base module) - 33.3% coverage
- **Total attributes**: 3
- **Covered**: 1 attributes
- **Missing**: 2 attributes

**Covered attributes** (1):
  - ✓ `description`

**Missing attributes** (2):
  - ✗ `id`
  - ✗ `name`

### Organization (Base module) - 33.3% coverage
- **Total attributes**: 3
- **Covered**: 1 attributes
- **Missing**: 2 attributes

**Covered attributes** (1):
  - ✓ `description`

**Missing attributes** (2):
  - ✗ `id`
  - ✗ `name`

### Grantor (Motivation module) - 33.3% coverage
- **Total attributes**: 3
- **Covered**: 1 attributes
- **Missing**: 2 attributes

**Covered attributes** (1):
  - ✓ `description`

**Missing attributes** (2):
  - ✗ `id`
  - ✗ `name`

### DatasetProperty (Base module) - 25.0% coverage
- **Total attributes**: 4
- **Covered**: 1 attributes
- **Missing**: 3 attributes

**Covered attributes** (1):
  - ✓ `description`

**Missing attributes** (3):
  - ✗ `id`
  - ✗ `name`
  - ✗ `used_software`

### Grant (Motivation module) - 25.0% coverage
- **Total attributes**: 4
- **Covered**: 1 attributes
- **Missing**: 3 attributes

**Covered attributes** (1):
  - ✓ `description`

**Missing attributes** (3):
  - ✗ `grant_number`
  - ✗ `id`
  - ✗ `name`

### ExportControlRegulatoryRestrictions (DataGovernance module) - 22.2% coverage
- **Total attributes**: 9
- **Covered**: 2 attributes
- **Missing**: 7 attributes

**Covered attributes** (2):
  - ✓ `description`
  - ✓ `regulatory_restrictions`

**Missing attributes** (7):
  - ✗ `confidentiality_level`
  - ✗ `governance_committee_contact`
  - ✗ `hipaa_compliant`
  - ✗ `id`
  - ✗ `name`
  - ✗ `other_compliance`
  - ✗ `used_software`

### Purpose (Motivation module) - 20.0% coverage
- **Total attributes**: 5
- **Covered**: 1 attributes
- **Missing**: 4 attributes

**Covered attributes** (1):
  - ✓ `description`

**Missing attributes** (4):
  - ✗ `id`
  - ✗ `name`
  - ✗ `response`
  - ✗ `used_software`

### Task (Motivation module) - 20.0% coverage
- **Total attributes**: 5
- **Covered**: 1 attributes
- **Missing**: 4 attributes

**Covered attributes** (1):
  - ✓ `description`

**Missing attributes** (4):
  - ✗ `id`
  - ✗ `name`
  - ✗ `response`
  - ✗ `used_software`

### AddressingGap (Motivation module) - 20.0% coverage
- **Total attributes**: 5
- **Covered**: 1 attributes
- **Missing**: 4 attributes

**Covered attributes** (1):
  - ✓ `description`

**Missing attributes** (4):
  - ✗ `id`
  - ✗ `name`
  - ✗ `response`
  - ✗ `used_software`

### Relationships (Composition module) - 20.0% coverage
- **Total attributes**: 5
- **Covered**: 1 attributes
- **Missing**: 4 attributes

**Covered attributes** (1):
  - ✓ `description`

**Missing attributes** (4):
  - ✗ `id`
  - ✗ `name`
  - ✗ `relationship_details`
  - ✗ `used_software`

### Splits (Composition module) - 20.0% coverage
- **Total attributes**: 5
- **Covered**: 1 attributes
- **Missing**: 4 attributes

**Covered attributes** (1):
  - ✓ `description`

**Missing attributes** (4):
  - ✗ `id`
  - ✗ `name`
  - ✗ `split_details`
  - ✗ `used_software`

### DataAnomaly (Composition module) - 20.0% coverage
- **Total attributes**: 5
- **Covered**: 1 attributes
- **Missing**: 4 attributes

**Covered attributes** (1):
  - ✓ `description`

**Missing attributes** (4):
  - ✗ `anomaly_details`
  - ✗ `id`
  - ✗ `name`
  - ✗ `used_software`

### CollectionMechanism (Collection module) - 20.0% coverage
- **Total attributes**: 5
- **Covered**: 1 attributes
- **Missing**: 4 attributes

**Covered attributes** (1):
  - ✓ `description`

**Missing attributes** (4):
  - ✗ `id`
  - ✗ `mechanism_details`
  - ✗ `name`
  - ✗ `used_software`

### PreprocessingStrategy (Preprocessing module) - 20.0% coverage
- **Total attributes**: 5
- **Covered**: 1 attributes
- **Missing**: 4 attributes

**Covered attributes** (1):
  - ✓ `description`

**Missing attributes** (4):
  - ✗ `id`
  - ✗ `name`
  - ✗ `preprocessing_details`
  - ✗ `used_software`

### CleaningStrategy (Preprocessing module) - 20.0% coverage
- **Total attributes**: 5
- **Covered**: 1 attributes
- **Missing**: 4 attributes

**Covered attributes** (1):
  - ✓ `description`

**Missing attributes** (4):
  - ✗ `cleaning_details`
  - ✗ `id`
  - ✗ `name`
  - ✗ `used_software`

### ExistingUse (Uses module) - 20.0% coverage
- **Total attributes**: 5
- **Covered**: 1 attributes
- **Missing**: 4 attributes

**Covered attributes** (1):
  - ✓ `description`

**Missing attributes** (4):
  - ✗ `examples`
  - ✗ `id`
  - ✗ `name`
  - ✗ `used_software`

### OtherTask (Uses module) - 20.0% coverage
- **Total attributes**: 5
- **Covered**: 1 attributes
- **Missing**: 4 attributes

**Covered attributes** (1):
  - ✓ `description`

**Missing attributes** (4):
  - ✗ `id`
  - ✗ `name`
  - ✗ `task_details`
  - ✗ `used_software`

### FutureUseImpact (Uses module) - 20.0% coverage
- **Total attributes**: 5
- **Covered**: 1 attributes
- **Missing**: 4 attributes

**Covered attributes** (1):
  - ✓ `description`

**Missing attributes** (4):
  - ✗ `id`
  - ✗ `impact_details`
  - ✗ `name`
  - ✗ `used_software`

### DiscouragedUse (Uses module) - 20.0% coverage
- **Total attributes**: 5
- **Covered**: 1 attributes
- **Missing**: 4 attributes

**Covered attributes** (1):
  - ✓ `description`

**Missing attributes** (4):
  - ✗ `discouragement_details`
  - ✗ `id`
  - ✗ `name`
  - ✗ `used_software`

### ProhibitedUse (Uses module) - 20.0% coverage
- **Total attributes**: 5
- **Covered**: 1 attributes
- **Missing**: 4 attributes

**Covered attributes** (1):
  - ✓ `description`

**Missing attributes** (4):
  - ✗ `id`
  - ✗ `name`
  - ✗ `prohibition_reason`
  - ✗ `used_software`

### ThirdPartySharing (Distribution module) - 20.0% coverage
- **Total attributes**: 5
- **Covered**: 1 attributes
- **Missing**: 4 attributes

**Covered attributes** (1):
  - ✓ `description`

**Missing attributes** (4):
  - ✗ `id`
  - ✗ `is_shared`
  - ✗ `name`
  - ✗ `used_software`

### DistributionFormat (Distribution module) - 20.0% coverage
- **Total attributes**: 5
- **Covered**: 1 attributes
- **Missing**: 4 attributes

**Covered attributes** (1):
  - ✓ `description`

**Missing attributes** (4):
  - ✗ `access_urls`
  - ✗ `id`
  - ✗ `name`
  - ✗ `used_software`

### DistributionDate (Distribution module) - 20.0% coverage
- **Total attributes**: 5
- **Covered**: 1 attributes
- **Missing**: 4 attributes

**Covered attributes** (1):
  - ✓ `description`

**Missing attributes** (4):
  - ✗ `id`
  - ✗ `name`
  - ✗ `release_dates`
  - ✗ `used_software`

### DataProtectionImpact (Ethics module) - 20.0% coverage
- **Total attributes**: 5
- **Covered**: 1 attributes
- **Missing**: 4 attributes

**Covered attributes** (1):
  - ✓ `description`

**Missing attributes** (4):
  - ✗ `id`
  - ✗ `impact_details`
  - ✗ `name`
  - ✗ `used_software`

### CollectionNotification (Ethics module) - 20.0% coverage
- **Total attributes**: 5
- **Covered**: 1 attributes
- **Missing**: 4 attributes

**Covered attributes** (1):
  - ✓ `description`

**Missing attributes** (4):
  - ✗ `id`
  - ✗ `name`
  - ✗ `notification_details`
  - ✗ `used_software`

### CollectionConsent (Ethics module) - 20.0% coverage
- **Total attributes**: 5
- **Covered**: 1 attributes
- **Missing**: 4 attributes

**Covered attributes** (1):
  - ✓ `description`

**Missing attributes** (4):
  - ✗ `consent_details`
  - ✗ `id`
  - ✗ `name`
  - ✗ `used_software`

### ConsentRevocation (Ethics module) - 20.0% coverage
- **Total attributes**: 5
- **Covered**: 1 attributes
- **Missing**: 4 attributes

**Covered attributes** (1):
  - ✓ `description`

**Missing attributes** (4):
  - ✗ `id`
  - ✗ `name`
  - ✗ `revocation_details`
  - ✗ `used_software`

### IPRestrictions (DataGovernance module) - 20.0% coverage
- **Total attributes**: 5
- **Covered**: 1 attributes
- **Missing**: 4 attributes

**Covered attributes** (1):
  - ✓ `description`

**Missing attributes** (4):
  - ✗ `id`
  - ✗ `name`
  - ✗ `restrictions`
  - ✗ `used_software`

### Person (Base module) - 16.7% coverage
- **Total attributes**: 6
- **Covered**: 1 attributes
- **Missing**: 5 attributes

**Covered attributes** (1):
  - ✓ `description`

**Missing attributes** (5):
  - ✗ `affiliation`
  - ✗ `email`
  - ✗ `id`
  - ✗ `name`
  - ✗ `orcid`

### FundingMechanism (Motivation module) - 16.7% coverage
- **Total attributes**: 6
- **Covered**: 1 attributes
- **Missing**: 5 attributes

**Covered attributes** (1):
  - ✓ `description`

**Missing attributes** (5):
  - ✗ `grantor`
  - ✗ `grants`
  - ✗ `id`
  - ✗ `name`
  - ✗ `used_software`

### Instance (Composition module) - 16.7% coverage
- **Total attributes**: 12
- **Covered**: 2 attributes
- **Missing**: 10 attributes

**Covered attributes** (2):
  - ✓ `description`
  - ~ `sampling_strategies`

**Missing attributes** (10):
  - ✗ `counts`
  - ✗ `data_substrate`
  - ✗ `data_topic`
  - ✗ `id`
  - ✗ `instance_type`
  - ✗ `label`
  - ✗ `label_description`
  - ✗ `missing_information`
  - ✗ `name`
  - ✗ `used_software`

### MissingInfo (Composition module) - 16.7% coverage
- **Total attributes**: 6
- **Covered**: 1 attributes
- **Missing**: 5 attributes

**Covered attributes** (1):
  - ✓ `description`

**Missing attributes** (5):
  - ✗ `id`
  - ✗ `missing`
  - ✗ `name`
  - ✗ `used_software`
  - ✗ `why_missing`

### Confidentiality (Composition module) - 16.7% coverage
- **Total attributes**: 6
- **Covered**: 1 attributes
- **Missing**: 5 attributes

**Covered attributes** (1):
  - ✓ `description`

**Missing attributes** (5):
  - ✗ `confidential_elements_present`
  - ✗ `confidentiality_details`
  - ✗ `id`
  - ✗ `name`
  - ✗ `used_software`

### ContentWarning (Composition module) - 16.7% coverage
- **Total attributes**: 6
- **Covered**: 1 attributes
- **Missing**: 5 attributes

**Covered attributes** (1):
  - ✓ `description`

**Missing attributes** (5):
  - ✗ `content_warnings_present`
  - ✗ `id`
  - ✗ `name`
  - ✗ `used_software`
  - ✗ `warnings`

### SensitiveElement (Composition module) - 16.7% coverage
- **Total attributes**: 6
- **Covered**: 1 attributes
- **Missing**: 5 attributes

**Covered attributes** (1):
  - ✓ `description`

**Missing attributes** (5):
  - ✗ `id`
  - ✗ `name`
  - ✗ `sensitive_elements_present`
  - ✗ `sensitivity_details`
  - ✗ `used_software`

### DatasetRelationship (Composition module) - 16.7% coverage
- **Total attributes**: 6
- **Covered**: 1 attributes
- **Missing**: 5 attributes

**Covered attributes** (1):
  - ✓ `description`

**Missing attributes** (5):
  - ✗ `id`
  - ✗ `name`
  - ✗ `relationship_type`
  - ✗ `target_dataset`
  - ✗ `used_software`

### DataCollector (Collection module) - 16.7% coverage
- **Total attributes**: 6
- **Covered**: 1 attributes
- **Missing**: 5 attributes

**Covered attributes** (1):
  - ✓ `description`

**Missing attributes** (5):
  - ✗ `collector_details`
  - ✗ `id`
  - ✗ `name`
  - ✗ `role`
  - ✗ `used_software`

### DirectCollection (Collection module) - 16.7% coverage
- **Total attributes**: 6
- **Covered**: 1 attributes
- **Missing**: 5 attributes

**Covered attributes** (1):
  - ✓ `description`

**Missing attributes** (5):
  - ✗ `collection_details`
  - ✗ `id`
  - ✗ `is_direct`
  - ✗ `name`
  - ✗ `used_software`

### RawData (Preprocessing module) - 16.7% coverage
- **Total attributes**: 6
- **Covered**: 1 attributes
- **Missing**: 5 attributes

**Covered attributes** (1):
  - ✓ `description`

**Missing attributes** (5):
  - ✗ `access_url`
  - ✗ `id`
  - ✗ `name`
  - ✗ `raw_data_details`
  - ✗ `used_software`

### UseRepository (Uses module) - 16.7% coverage
- **Total attributes**: 6
- **Covered**: 1 attributes
- **Missing**: 5 attributes

**Covered attributes** (1):
  - ✓ `description`

**Missing attributes** (5):
  - ✗ `id`
  - ✗ `name`
  - ✗ `repository_details`
  - ✗ `repository_url`
  - ✗ `used_software`

### Maintainer (Maintenance module) - 16.7% coverage
- **Total attributes**: 6
- **Covered**: 1 attributes
- **Missing**: 5 attributes

**Covered attributes** (1):
  - ✓ `description`

**Missing attributes** (5):
  - ✗ `id`
  - ✗ `maintainer_details`
  - ✗ `name`
  - ✗ `role`
  - ✗ `used_software`

### Erratum (Maintenance module) - 16.7% coverage
- **Total attributes**: 6
- **Covered**: 1 attributes
- **Missing**: 5 attributes

**Covered attributes** (1):
  - ✓ `description`

**Missing attributes** (5):
  - ✗ `erratum_details`
  - ✗ `erratum_url`
  - ✗ `id`
  - ✗ `name`
  - ✗ `used_software`

### UpdatePlan (Maintenance module) - 16.7% coverage
- **Total attributes**: 6
- **Covered**: 1 attributes
- **Missing**: 5 attributes

**Covered attributes** (1):
  - ✓ `description`

**Missing attributes** (5):
  - ✗ `frequency`
  - ✗ `id`
  - ✗ `name`
  - ✗ `update_details`
  - ✗ `used_software`

### RetentionLimits (Maintenance module) - 16.7% coverage
- **Total attributes**: 6
- **Covered**: 1 attributes
- **Missing**: 5 attributes

**Covered attributes** (1):
  - ✓ `description`

**Missing attributes** (5):
  - ✗ `id`
  - ✗ `name`
  - ✗ `retention_details`
  - ✗ `retention_period`
  - ✗ `used_software`

### ExtensionMechanism (Maintenance module) - 16.7% coverage
- **Total attributes**: 6
- **Covered**: 1 attributes
- **Missing**: 5 attributes

**Covered attributes** (1):
  - ✓ `description`

**Missing attributes** (5):
  - ✗ `contribution_url`
  - ✗ `extension_details`
  - ✗ `id`
  - ✗ `name`
  - ✗ `used_software`

### Creator (Motivation module) - 14.3% coverage
- **Total attributes**: 7
- **Covered**: 1 attributes
- **Missing**: 6 attributes

**Covered attributes** (1):
  - ✓ `description`

**Missing attributes** (6):
  - ✗ `affiliations`
  - ✗ `credit_roles`
  - ✗ `id`
  - ✗ `name`
  - ✗ `principal_investigator`
  - ✗ `used_software`

### Subpopulation (Composition module) - 14.3% coverage
- **Total attributes**: 7
- **Covered**: 1 attributes
- **Missing**: 6 attributes

**Covered attributes** (1):
  - ✓ `description`

**Missing attributes** (6):
  - ✗ `distribution`
  - ✗ `id`
  - ✗ `identification`
  - ✗ `name`
  - ✗ `subpopulation_elements_present`
  - ✗ `used_software`

### CollectionTimeframe (Collection module) - 14.3% coverage
- **Total attributes**: 7
- **Covered**: 1 attributes
- **Missing**: 6 attributes

**Covered attributes** (1):
  - ✓ `description`

**Missing attributes** (6):
  - ✗ `end_date`
  - ✗ `id`
  - ✗ `name`
  - ✗ `start_date`
  - ✗ `timeframe_details`
  - ✗ `used_software`

### MissingDataDocumentation (Collection module) - 14.3% coverage
- **Total attributes**: 7
- **Covered**: 1 attributes
- **Missing**: 6 attributes

**Covered attributes** (1):
  - ✓ `description`

**Missing attributes** (6):
  - ✗ `handling_strategy`
  - ✗ `id`
  - ✗ `missing_data_causes`
  - ✗ `missing_data_patterns`
  - ✗ `name`
  - ✗ `used_software`

### MachineAnnotationTools (Preprocessing module) - 14.3% coverage
- **Total attributes**: 7
- **Covered**: 1 attributes
- **Missing**: 6 attributes

**Covered attributes** (1):
  - ✓ `description`

**Missing attributes** (6):
  - ✗ `id`
  - ✗ `name`
  - ✗ `tool_accuracy`
  - ✗ `tool_descriptions`
  - ✗ `tools`
  - ✗ `used_software`

### IntendedUse (Uses module) - 14.3% coverage
- **Total attributes**: 7
- **Covered**: 1 attributes
- **Missing**: 6 attributes

**Covered attributes** (1):
  - ✓ `description`

**Missing attributes** (6):
  - ✗ `examples`
  - ✗ `id`
  - ✗ `name`
  - ✗ `usage_notes`
  - ✗ `use_category`
  - ✗ `used_software`

### VersionAccess (Maintenance module) - 14.3% coverage
- **Total attributes**: 7
- **Covered**: 1 attributes
- **Missing**: 6 attributes

**Covered attributes** (1):
  - ✓ `description`

**Missing attributes** (6):
  - ✗ `id`
  - ✗ `latest_version_doi`
  - ✗ `name`
  - ✗ `used_software`
  - ✗ `version_details`
  - ✗ `versions_available`

### EthicalReview (Ethics module) - 14.3% coverage
- **Total attributes**: 7
- **Covered**: 1 attributes
- **Missing**: 6 attributes

**Covered attributes** (1):
  - ✓ `description`

**Missing attributes** (6):
  - ✗ `contact_person`
  - ✗ `id`
  - ✗ `name`
  - ✗ `review_details`
  - ✗ `reviewing_organization`
  - ✗ `used_software`

### LicenseAndUseTerms (DataGovernance module) - 14.3% coverage
- **Total attributes**: 7
- **Covered**: 1 attributes
- **Missing**: 6 attributes

**Covered attributes** (1):
  - ✓ `description`

**Missing attributes** (6):
  - ✗ `contact_person`
  - ✗ `data_use_permission`
  - ✗ `id`
  - ✗ `license_terms`
  - ✗ `name`
  - ✗ `used_software`

### DatasetBias (Composition module) - 12.5% coverage
- **Total attributes**: 8
- **Covered**: 1 attributes
- **Missing**: 7 attributes

**Covered attributes** (1):
  - ✓ `description`

**Missing attributes** (7):
  - ✗ `affected_subsets`
  - ✗ `bias_description`
  - ✗ `bias_type`
  - ✗ `id`
  - ✗ `mitigation_strategy`
  - ✗ `name`
  - ✗ `used_software`

### DatasetLimitation (Composition module) - 12.5% coverage
- **Total attributes**: 8
- **Covered**: 1 attributes
- **Missing**: 7 attributes

**Covered attributes** (1):
  - ✓ `description`

**Missing attributes** (7):
  - ✗ `id`
  - ✗ `limitation_description`
  - ✗ `limitation_type`
  - ✗ `name`
  - ✗ `recommended_mitigation`
  - ✗ `scope_impact`
  - ✗ `used_software`

### ExternalResource (Composition module) - 12.5% coverage
- **Total attributes**: 8
- **Covered**: 1 attributes
- **Missing**: 7 attributes

**Covered attributes** (1):
  - ✓ `description`

**Missing attributes** (7):
  - ✗ `archival`
  - ✗ `external_resources`
  - ✗ `future_guarantees`
  - ✗ `id`
  - ✗ `name`
  - ✗ `restrictions`
  - ✗ `used_software`

### Deidentification (Composition module) - 12.5% coverage
- **Total attributes**: 8
- **Covered**: 1 attributes
- **Missing**: 7 attributes

**Covered attributes** (1):
  - ✓ `description`

**Missing attributes** (7):
  - ✗ `deidentification_details`
  - ✗ `id`
  - ✗ `identifiable_elements_present`
  - ✗ `identifiers_removed`
  - ✗ `method`
  - ✗ `name`
  - ✗ `used_software`

### RawDataSource (Collection module) - 12.5% coverage
- **Total attributes**: 8
- **Covered**: 1 attributes
- **Missing**: 7 attributes

**Covered attributes** (1):
  - ✓ `description`

**Missing attributes** (7):
  - ✗ `access_details`
  - ✗ `id`
  - ✗ `name`
  - ✗ `raw_data_format`
  - ✗ `source_description`
  - ✗ `source_type`
  - ✗ `used_software`

### ImputationProtocol (Preprocessing module) - 12.5% coverage
- **Total attributes**: 8
- **Covered**: 1 attributes
- **Missing**: 7 attributes

**Covered attributes** (1):
  - ✓ `description`

**Missing attributes** (7):
  - ✗ `id`
  - ✗ `imputation_method`
  - ✗ `imputation_rationale`
  - ✗ `imputation_validation`
  - ✗ `imputed_fields`
  - ✗ `name`
  - ✗ `used_software`

### VulnerablePopulations (Human module) - 12.5% coverage
- **Total attributes**: 8
- **Covered**: 1 attributes
- **Missing**: 7 attributes

**Covered attributes** (1):
  - ✓ `description`

**Missing attributes** (7):
  - ✗ `assent_procedures`
  - ✗ `guardian_consent`
  - ✗ `id`
  - ✗ `name`
  - ✗ `special_protections`
  - ✗ `used_software`
  - ✗ `vulnerable_groups_included`

### InstanceAcquisition (Collection module) - 11.1% coverage
- **Total attributes**: 9
- **Covered**: 1 attributes
- **Missing**: 8 attributes

**Covered attributes** (1):
  - ✓ `description`

**Missing attributes** (8):
  - ✗ `acquisition_details`
  - ✗ `id`
  - ✗ `name`
  - ✗ `used_software`
  - ✗ `was_directly_observed`
  - ✗ `was_inferred_derived`
  - ✗ `was_reported_by_subjects`
  - ✗ `was_validated_verified`

### AnnotationAnalysis (Preprocessing module) - 11.1% coverage
- **Total attributes**: 9
- **Covered**: 1 attributes
- **Missing**: 8 attributes

**Covered attributes** (1):
  - ✓ `description`

**Missing attributes** (8):
  - ✗ `agreement_metric`
  - ✗ `analysis_method`
  - ✗ `annotation_quality_details`
  - ✗ `disagreement_patterns`
  - ✗ `id`
  - ✗ `inter_annotator_agreement_score`
  - ✗ `name`
  - ✗ `used_software`

### HumanSubjectResearch (Human module) - 11.1% coverage
- **Total attributes**: 9
- **Covered**: 1 attributes
- **Missing**: 8 attributes

**Covered attributes** (1):
  - ✓ `description`

**Missing attributes** (8):
  - ✗ `ethics_review_board`
  - ✗ `id`
  - ✗ `involves_human_subjects`
  - ✗ `irb_approval`
  - ✗ `name`
  - ✗ `regulatory_compliance`
  - ✗ `special_populations`
  - ✗ `used_software`

### InformedConsent (Human module) - 11.1% coverage
- **Total attributes**: 9
- **Covered**: 1 attributes
- **Missing**: 8 attributes

**Covered attributes** (1):
  - ✓ `description`

**Missing attributes** (8):
  - ✗ `consent_documentation`
  - ✗ `consent_obtained`
  - ✗ `consent_scope`
  - ✗ `consent_type`
  - ✗ `id`
  - ✗ `name`
  - ✗ `used_software`
  - ✗ `withdrawal_mechanism`

### LabelingStrategy (Preprocessing module) - 10.0% coverage
- **Total attributes**: 10
- **Covered**: 1 attributes
- **Missing**: 9 attributes

**Covered attributes** (1):
  - ✓ `description`

**Missing attributes** (9):
  - ✗ `annotations_per_item`
  - ✗ `annotator_demographics`
  - ✗ `data_annotation_platform`
  - ✗ `data_annotation_protocol`
  - ✗ `id`
  - ✗ `inter_annotator_agreement`
  - ✗ `labeling_details`
  - ✗ `name`
  - ✗ `used_software`

### SamplingStrategy (Composition module) - 9.1% coverage
- **Total attributes**: 11
- **Covered**: 1 attributes
- **Missing**: 10 attributes

**Covered attributes** (1):
  - ✓ `description`

**Missing attributes** (10):
  - ✗ `id`
  - ✗ `is_random`
  - ✗ `is_representative`
  - ✗ `is_sample`
  - ✗ `name`
  - ✗ `representative_verification`
  - ✗ `source_data`
  - ✗ `strategies`
  - ✗ `used_software`
  - ✗ `why_not_representative`

### VariableMetadata (Variables module) - 5.6% coverage
- **Total attributes**: 18
- **Covered**: 1 attributes
- **Missing**: 17 attributes

**Covered attributes** (1):
  - ✓ `description`

**Missing attributes** (17):
  - ✗ `categories`
  - ✗ `data_type`
  - ✗ `derivation`
  - ✗ `examples`
  - ✗ `id`
  - ✗ `is_identifier`
  - ✗ `is_sensitive`
  - ✗ `maximum_value`
  - ✗ `measurement_technique`
  - ✗ `minimum_value`
  - ✗ `missing_value_code`
  - ✗ `name`
  - ✗ `precision`
  - ✗ `quality_notes`
  - ✗ `unit`
  - ✗ `used_software`
  - ✗ `variable_name`

## Section 4: Classes NOT Covered

**Total**: 1 classes with ZERO attribute coverage

### Base Module (1 uncovered classes)

**FormatDialect** (5 attributes)
  - Attributes: comment_prefix, delimiter, double_quote, header, quote_char

## Section 5: Critical Gaps Analysis

This section identifies what functionality would be lost in a D4D Slim schema based on RO-Crate mapping.

### Workflow Process

**11 classes affected**

- **DatasetCollection** (83% covered) - 24 attributes
- **CollectionMechanism** (20% covered) - 5 attributes
- **PreprocessingStrategy** (20% covered) - 5 attributes
- **CleaningStrategy** (20% covered) - 5 attributes
- **CollectionNotification** (20% covered) - 5 attributes
- **CollectionConsent** (20% covered) - 5 attributes
- **DirectCollection** (17% covered) - 6 attributes
- **CollectionTimeframe** (14% covered) - 7 attributes
- **MachineAnnotationTools** (14% covered) - 7 attributes
- **AnnotationAnalysis** (11% covered) - 9 attributes
- **LabelingStrategy** (10% covered) - 10 attributes

### Quality Validation

**5 classes affected**

- **DataAnomaly** (20% covered) - 5 attributes
- **MissingInfo** (17% covered) - 6 attributes
- **MissingDataDocumentation** (14% covered) - 7 attributes
- **DatasetBias** (12% covered) - 8 attributes
- **DatasetLimitation** (12% covered) - 8 attributes

### Ethical Compliance

**6 classes affected**

- **DataProtectionImpact** (20% covered) - 5 attributes
- **CollectionConsent** (20% covered) - 5 attributes
- **ConsentRevocation** (20% covered) - 5 attributes
- **EthicalReview** (14% covered) - 7 attributes
- **VulnerablePopulations** (12% covered) - 8 attributes
- **InformedConsent** (11% covered) - 9 attributes

### Technical Metadata

**3 classes affected**

- **FormatDialect** (0% covered) - 5 attributes
- **Information** (83% covered) - 23 attributes
- **DistributionFormat** (20% covered) - 5 attributes

### Distribution Access

**7 classes affected**

- **ExportControlRegulatoryRestrictions** (22% covered) - 9 attributes
- **ThirdPartySharing** (20% covered) - 5 attributes
- **DistributionFormat** (20% covered) - 5 attributes
- **DistributionDate** (20% covered) - 5 attributes
- **IPRestrictions** (20% covered) - 5 attributes
- **VersionAccess** (14% covered) - 7 attributes
- **LicenseAndUseTerms** (14% covered) - 7 attributes

## Section 6: Recommendations for D4D Slim Schema

### Option 1: Strict Mapping-Only Approach

- Include only the 272 attributes present in RO-Crate mapping
- Coverage: 40.0% of full schema
- **Pros**: Direct transformation, no guessing
- **Cons**: Missing critical workflow, quality, and ethics documentation

### Option 2: Complete-Class Approach (>50% threshold)

- Include all attributes from classes with ≥50% coverage
- Would include: 5 classes
- Total attributes: ~237
- **Pros**: More coherent class structure, better documentation completeness
- **Cons**: Some attributes without direct RO-Crate mappings

### Option 3: Minimal + Critical Stubs

- Include all mapped attributes (Option 1)
- Add stub classes for critical gaps:
  - `AnnotationAnalysis` (Preprocessing module)
  - `CleaningStrategy` (Preprocessing module)
  - `CollectionConsent` (Ethics module)
  - `CollectionMechanism` (Collection module)
  - `CollectionNotification` (Ethics module)
  - `CollectionTimeframe` (Collection module)
  - `ConsentRevocation` (Ethics module)
  - `DataAnomaly` (Composition module)
  - `DataProtectionImpact` (Ethics module)
  - `DatasetBias` (Composition module)
  - `DatasetCollection` (Core module)
  - `DatasetLimitation` (Composition module)
  - `DirectCollection` (Collection module)
  - `EthicalReview` (Ethics module)
  - `InformedConsent` (Human module)
  - `LabelingStrategy` (Preprocessing module)
  - `MachineAnnotationTools` (Preprocessing module)
  - `MissingDataDocumentation` (Collection module)
  - `MissingInfo` (Composition module)
  - `PreprocessingStrategy` (Preprocessing module)
  - `VulnerablePopulations` (Human module)

- **Pros**: Maintains critical documentation structure, acknowledges limitations
- **Cons**: Stubs may be empty/minimal in practice

### Recommended Approach: Option 2 (Complete-Class)

**Rationale:**
- RO-Crate already covers most Dataset-level attributes (83 fields)
- Missing classes are primarily nested/complex types for detailed documentation
- Including complete classes maintains schema coherence
- Allows progressive enhancement as RO-Crate coverage expands
- Provides clear migration path: map what's available, document what's missing

**Implementation:**
1. Start with all attributes from RO-Crate mapping
2. Include complete classes where coverage ≥ 50%
3. Document unmapped attributes as 'future work' in comments
4. Provide examples showing both full and partial population

## Appendix: Coverage Statistics by Module

| Module | Total Classes | Fully Covered | Partially Covered | Uncovered |
|--------|--------------|---------------|-------------------|-----------|
| Base | 7 | 0 | 6 | 1 |
| Collection | 7 | 0 | 7 | 0 |
| Composition | 15 | 0 | 15 | 0 |
| Core | 3 | 0 | 3 | 0 |
| DataGovernance | 3 | 0 | 3 | 0 |
| Distribution | 3 | 0 | 3 | 0 |
| Ethics | 5 | 0 | 5 | 0 |
| Human | 3 | 0 | 3 | 0 |
| Maintenance | 6 | 0 | 6 | 0 |
| Motivation | 7 | 0 | 7 | 0 |
| Preprocessing | 7 | 0 | 7 | 0 |
| Uses | 7 | 0 | 7 | 0 |
| Variables | 1 | 0 | 1 | 0 |
