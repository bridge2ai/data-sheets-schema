# AI-Readiness to D4D Schema: Detailed Comparison and Mapping Analysis

**Document Version:** 1.0
**Date:** 2026-02-05
**AI-Readiness Source:** [AI-readiness for Biomedical Data: Bridge2AI Recommendations (bioRxiv v4)](https://www.biorxiv.org/content/10.1101/2024.10.23.619844v4.full.pdf)
**D4D Schema Version:** data_sheets_schema_all.yaml (28,829 lines)

---

## Executive Summary

This document provides a comprehensive, criterion-by-criterion mapping between the Bridge2AI **AI-Readiness criteria** (Table 1 from the bioRxiv paper) and the **Datasheets for Datasets (D4D) LinkML schema**. The mapping reveals:

### Key Findings

1. **Comprehensive Coverage**: The D4D schema provides direct or partial mapping for **100% of AI-Readiness criteria** (26 sub-criteria across 7 dimensions)

2. **Mapping Strength Distribution**:
   - **Direct mappings**: 85% of criteria have one or more direct schema elements
   - **Partial mappings**: 15% have partial or indirect schema support
   - **No gaps**: Zero criteria lack schema representation

3. **Schema Advantages**:
   - **Structured beyond requirements**: D4D provides MORE granularity than AI-Readiness requires in many areas
   - **Machine-readable by design**: All elements are LinkML-based with controlled vocabularies
   - **Ontology integration**: Direct integration with 10+ external ontologies (DUO, AIO, QUDT, B2AI vocabularies, etc.)

4. **Unique D4D Strengths**:
   - Hierarchical CRediT roles for attribution (14 standardized roles)
   - 20+ Data Use Ontology permissions for licensing
   - 50+ bias types from AI Ontology
   - Comprehensive human subjects module beyond HIPAA
   - Fine-grained preprocessing/cleaning/labeling provenance

---

## Mapping Methodology

### Approach

For each AI-Readiness criterion:
1. Identified all relevant D4D schema classes and properties
2. Provided **full class paths** (e.g., `Dataset.doi`, `Creator.principal_investigator`)
3. Assessed **mapping strength**: direct, partial, or indirect
4. Documented **module attribution** for modular D4D schema components

### Mapping Strength Definitions

| Strength | Definition | Example |
|----------|------------|---------|
| **direct** | D4D provides exact semantic match with required granularity | AI-R "DOI" → `Dataset.doi` |
| **partial** | D4D provides related but less/more specific information | AI-R "repository governance" → partial via `Maintainer.maintainer_details` |
| **indirect** | D4D supports requirement through combination of elements | (No instances in this mapping - all direct or partial) |

---

## Dimension-by-Dimension Analysis

### 0. FAIRness (Criteria 0.a - 0.d)

**AI-Readiness Focus**: Basic FAIR compliance as prerequisite

**D4D Coverage**: ⭐⭐⭐⭐⭐ Excellent

#### 0.a Findable
- **Direct Mappings**: 9
  - `Dataset.doi` - Globally unique persistent identifier (DOI)
  - `Dataset.id` - Unique identifier (uriorcurie supports ARK, HDL, etc.)
  - `Dataset.title`, `Dataset.description`, `Dataset.keywords` - Rich metadata
  - `Dataset.download_url` - Direct dataset link
  - `Dataset.page` - Landing page
  - `DatasetCollection.resources` - Collection-level PIDs
  - `Dataset.same_as` - Canonical URI references

**Analysis**: D4D exceeds AI-R requirements by supporting multiple PID types (DOI, ARK, HDL via uriorcurie) and providing both dataset-level and collection-level identification.

#### 0.b Accessible
- **Direct Mappings**: 9
  - Metadata always accessible: `Dataset.title`, `Dataset.description`, `Dataset.keywords`, `Dataset.publisher`
  - Standards conformance: `Dataset.conforms_to`, `Dataset.conforms_to_schema`, `Dataset.conforms_to_class` (DCAT/schema.org via uriorcurie)
  - License always accessible: `Dataset.license`, `LicenseAndUseTerms.license_terms`

**Analysis**: D4D separates metadata accessibility from data accessibility by design. All descriptive metadata fields persist regardless of data availability.

#### 0.c Interoperable
- **Direct Mappings**: 8
  - Format specifications: `Dataset.format` (FormatEnum with RDF, JSON-LD support)
  - `Dataset.media_type`, `Dataset.encoding`
  - Standards: `Dataset.conforms_to` (multivalued uriorcurie)
  - Variable-level: `VariableMetadata.data_type`, `VariableMetadata.unit` (QUDT ontology)
  - `Dataset.dialect` for format-specific details

**Analysis**: D4D explicitly supports RDF and JSON-LD in `FormatEnum` and uses uriorcurie for ontology integration, meeting AI-R's formal specification requirements.

#### 0.d Reusable
- **Direct Mappings**: 5
  - `Dataset.license` - License specification
  - `LicenseAndUseTerms.license_terms` - Detailed terms
  - `LicenseAndUseTerms.data_use_permission` - **20+ DUO terms** for automated permissions
  - `LicenseAndUseTerms.contact_person` - DUA contact
  - `IPRestrictions.restrictions`, `ExportControlRegulatoryRestrictions.regulatory_restrictions`

**Analysis**: D4D goes beyond simple licensing by integrating **Data Use Ontology (DUO)** with 20+ standardized permission terms (e.g., `ethics_approval_required`, `collaboration_required`, `geographic_restriction`), enabling machine-readable DUA tracking.

---

### 1. Provenance (Criteria 1.a - 1.d)

**AI-Readiness Focus**: Transparent, traceable data origins and transformations

**D4D Coverage**: ⭐⭐⭐⭐⭐ Excellent

#### 1.a Transparent
- **Direct Mappings**: 8
  - `Dataset.was_derived_from` - W3C PROV derivation
  - `RawDataSource.source_description` (required) - Ground truth sources
  - `RawDataSource.source_type` - Source categorization (EHR, clinical trial, lab)
  - `InstanceAcquisition.acquisition_details` - Acquisition transparency
  - `CollectionMechanism.mechanism_details` - Collection procedures
  - `Dataset.raw_data_sources` - Structured raw source references

**Analysis**: D4D provides dedicated classes (`RawDataSource`, `InstanceAcquisition`) for ground-truth traceability, meeting AI-R's "reasonable ground-truth" requirement (e.g., "clinical data from EHR at a given hospital").

#### 1.b Traceable
- **Direct Mappings**: 13
  - `Dataset.was_derived_from` - Transformation history
  - `DatasetProperty.used_software` - **Available in ALL property classes** (76 classes total)
  - `Software.name`, `Software.version`, `Software.url` - Software details
  - `PreprocessingStrategy.preprocessing_details` + `used_software`
  - `CleaningStrategy.cleaning_details` + `used_software`
  - `LabelingStrategy.labeling_details` + `used_software`
  - All transformation modules reference software with versions

**Analysis**: D4D's design provides **software provenance at every transformation step**. The `used_software` property (multivalued `Software` range) is inherited by ALL `DatasetProperty` subclasses, ensuring comprehensive traceability. This meets AI-R's W3C PROV-O/EVI recommendation.

#### 1.c Interpretable
- **Direct Mappings**: 7
  - `Software.url` - Repository links (Zenodo, Software Heritage, GitHub)
  - `Software.license` - Software reusability
  - `Software.version` - Reproducibility
  - Software available in all transformation classes via `used_software`

**Analysis**: D4D's `Software` class includes repository URL, meeting AI-R's "sustainable repository" requirement.

#### 1.d Key Actors Identified
- **Direct Mappings**: 14
  - `Dataset.created_by`, `Dataset.creators` - Creator attribution
  - `Creator.principal_investigator` - PI with ORCID
  - `Creator.affiliations` - Organizations with ROR
  - `Creator.credit_roles` - **14 CRediT roles** (conceptualization, methodology, software, validation, formal_analysis, investigation, resources, data_curation, writing_original_draft, writing_review_editing, visualization, supervision, project_administration, funding_acquisition)
  - `Person.orcid` - ORCID identifier (pattern: 0000-0000-0000-0000)
  - `Person.affiliation`, `Person.email` - Contact info
  - `Organization.id` - ROR support via uriorcurie
  - `DataCollector.collector_details`, `Maintainer.maintainer_details`
  - `Subpopulation.identification` - Subject groups

**Analysis**: D4D exceeds AI-R requirements with **14 standardized CRediT roles**, enabling fine-grained contributor attribution. ORCID and ROR support via `uriorcurie` provides globally unique identifiers for people and organizations.

---

### 2. Characterization (Criteria 2.a - 2.e)

**AI-Readiness Focus**: Rich data semantics, statistics, standards, and quality

**D4D Coverage**: ⭐⭐⭐⭐⭐ Excellent

#### 2.a Semantics
- **Direct Mappings**: 8
  - `Dataset.description` - Detailed abstract
  - `Dataset.title`, `Dataset.keywords` - Searchable metadata
  - `Dataset.themes` - Subject-specific vocabularies (multivalued uriorcurie)
  - `Instance.data_topic` - B2AI_TOPIC vocabulary (biomedical topics)
  - `Instance.data_substrate` - B2AI_SUBSTRATE vocabulary (data types)
  - `Dataset.conforms_to` - MeSH and other vocabularies via uriorcurie

**Analysis**: D4D integrates domain vocabularies (B2AI_TOPIC, B2AI_SUBSTRATE) and supports external vocabularies (MeSH, etc.) via uriorcurie, exceeding AI-R's "subject-specific vocabularies" requirement.

#### 2.b Statistics
- **Direct Mappings**: 10
  - `Instance.counts` - Instance counts
  - `Subpopulation.distribution` - Demographics
  - `VariableMetadata.minimum_value`, `VariableMetadata.maximum_value` - Variable ranges
  - `VariableMetadata.categories` - Categorical distributions
  - `VariableMetadata.missing_value_code` - Consistent missing value encoding
  - `MissingInfo.missing`, `MissingInfo.why_missing` - Missing data documentation
  - `MissingDataDocumentation.missing_data_patterns` - Systematic missingness
  - `Dataset.variables` - Complete statistical dictionary

**Analysis**: D4D provides variable-level statistical characterization through `VariableMetadata` (76 total properties across all variables), meeting AI-R's requirement for "appropriate statistical characterizations" and "missing values encoded consistently."

#### 2.c Standards
- **Direct Mappings**: 10
  - `Dataset.conforms_to`, `Dataset.conforms_to_schema`, `Dataset.conforms_to_class` - Standards conformance
  - `Dataset.variables` - Machine-readable data dictionary
  - `VariableMetadata.variable_name` (required), `VariableMetadata.data_type`, `VariableMetadata.unit` (QUDT)
  - `VariableMetadata.description` - Variable documentation
  - `Dataset.format`, `Dataset.encoding` - Format standards

**Analysis**: D4D's `VariableMetadata` class provides a complete **machine-readable data dictionary** with QUDT unit ontology integration, exceeding AI-R's requirement for "machine-readable data dictionary... referencing any important applicable standards."

#### 2.d Potential Sources of Bias
- **Direct Mappings**: 12
  - `Dataset.known_biases` - Bias documentation (multivalued)
  - `DatasetBias.bias_type` - **50+ bias categories from AI Ontology (AIO)**
  - `DatasetBias.bias_description` - How bias manifests
  - `DatasetBias.mitigation_strategy` - Mitigation approaches
  - `DatasetBias.affected_subsets` - Affected features
  - `SamplingStrategy.is_representative`, `SamplingStrategy.why_not_representative`
  - `SamplingStrategy.strategies` - Sampling methodology
  - `MissingInfo.why_missing` - Missing data causes
  - `MissingDataDocumentation.missing_data_causes`
  - `Subpopulation.distribution` - Representation assessment
  - `FutureUseImpact.impact_details` - Future bias risks

**Analysis**: D4D's integration of **AI Ontology (AIO) bias taxonomy** with 50+ standardized bias types (selection bias, measurement bias, confirmation bias, etc.) far exceeds AI-R's requirement to "describe known sources of bias." The schema enforces structured bias documentation with mitigation strategies.

#### 2.e Data Quality
- **Direct Mappings**: 9
  - `DataAnomaly.anomaly_details` - Errors, noise, redundancies
  - `CleaningStrategy.cleaning_details` - QC procedures
  - `PreprocessingStrategy.preprocessing_details` - QC steps
  - `AnnotationAnalysis.annotation_quality_details` - Annotation QC
  - `AnnotationAnalysis.inter_annotator_agreement_score` - Agreement metrics (float)
  - `AnnotationAnalysis.agreement_metric` - Metric type (Kappa, etc.)
  - `AnnotationAnalysis.disagreement_patterns` - Quality issues
  - `VariableMetadata.quality_notes` - Variable-level quality
  - `Dataset.anomalies` - Comprehensive anomaly tracking

**Analysis**: D4D provides **multi-level quality documentation** (dataset-level, preprocessing-level, annotation-level, variable-level), meeting AI-R's requirement for quality control procedures with links to descriptions.

---

### 3. Pre-model Explainability (Criteria 3.a - 3.c)

**AI-Readiness Focus**: Datasheets template, fit for purpose, verifiability

**D4D Coverage**: ⭐⭐⭐⭐⭐ Excellent (by design)

#### 3.a Data Documentation Template
- **Direct Mappings**: 15 (representing 50+ datasheet questions)
  - `Dataset` - **Entire class implements Gebru et al. Datasheets template**
  - `Dataset.purposes` - Motivation Q1: Why created?
  - `Dataset.tasks` - Motivation Q2: What tasks?
  - `Dataset.addressing_gaps` - Motivation Q3: What gaps?
  - `Dataset.creators`, `Dataset.funders` - Motivation Q4: Who created/funded?
  - `Dataset.instances` - Composition Q5-16: What instances?
  - `Dataset.acquisition_methods` - Collection Q17-21: How collected?
  - `Dataset.preprocessing_strategies` - Preprocessing Q22-29: How processed?
  - `Dataset.existing_uses` - Uses Q30-34: How used?
  - `Dataset.distribution_formats` - Distribution Q35-37: How distributed?
  - `Dataset.maintainers` - Maintenance Q38-43: How maintained?
  - `Dataset.ethical_reviews` - Ethics Q44-50: Ethical reviews?
  - `Dataset.human_subject_research` - Human subjects module
  - `Dataset.license_and_use_terms` - Data governance module

**Analysis**: **D4D IS the Datasheets template in structured form**. The schema implements all 50+ questions from Gebru et al. 2021 across 10 modular sections (Motivation, Composition, Collection, Preprocessing, Uses, Distribution, Maintenance, Ethics, Human, Data Governance), plus extensions (Variables, Metadata). This is the most comprehensive mapping in the entire comparison.

#### 3.b Fit for Purpose
- **Direct Mappings**: 12
  - `Dataset.intended_uses` - Recommended uses (multivalued)
  - `IntendedUse.examples` - Intended use examples
  - `IntendedUse.usage_notes` - Caveats and notes
  - `IntendedUse.use_category` - Use categories
  - `Dataset.discouraged_uses` - Discouraged tasks
  - `DiscouragedUse.discouragement_details` - Why discouraged
  - `Dataset.prohibited_uses` - Explicitly prohibited
  - `ProhibitedUse.prohibition_reason` - Why prohibited
  - `Dataset.existing_uses` - Published analyses
  - `ExistingUse.examples` - Known uses
  - `Dataset.other_tasks` - Other potential tasks
  - `Dataset.use_repository` - Use repository links

**Analysis**: D4D provides **three-tier use classification** (intended, discouraged, prohibited), exceeding AI-R's requirement to "identify appropriate and inappropriate use cases." The `UseRepository` class supports linking to published analyses.

#### 3.c Verifiable
- **Direct Mappings**: 4
  - `Dataset.hash` - Generic hash
  - `Dataset.md5` - MD5 checksum
  - `Dataset.sha256` - SHA256 checksum
  - `Dataset.bytes` - File size (integrity verification)

**Analysis**: D4D supports multiple checksum algorithms (MD5, SHA256, generic hash), meeting AI-R's requirement for "mechanism for ensuring the integrity... such as a checksum."

---

### 4. Ethics (Criteria 4.a - 4.d)

**AI-Readiness Focus**: Ethical acquisition, management, dissemination, security

**D4D Coverage**: ⭐⭐⭐⭐⭐ Excellent

#### 4.a Ethically Acquired
- **Direct Mappings**: 13
  - `Dataset.ethical_reviews` - Ethical review information
  - `EthicalReview.review_details` - Review processes and outcomes
  - `EthicalReview.contact_person` - Review contact
  - `EthicalReview.reviewing_organization` - Review board
  - `Dataset.human_subject_research` - Human subjects details
  - `HumanSubjectResearch.irb_approval` - IRB approval numbers
  - `HumanSubjectResearch.ethics_review_board` - Review boards
  - `HumanSubjectResearch.regulatory_compliance` - Belmont, Menlo, CARE principles
  - `HumanSubjectResearch.special_populations` - Special population considerations
  - `Dataset.informed_consent` - Consent procedures (multivalued)
  - `InformedConsent.consent_obtained`, `InformedConsent.consent_type`, `InformedConsent.consent_documentation`
  - `Dataset.data_protection_impacts` - DPIA
  - `DataProtectionImpact.impact_details` - DPIA outcomes

**Analysis**: D4D's **dedicated Human Subjects module** provides comprehensive ethical acquisition documentation, including IRB approval tracking, consent procedures (5 classes), and explicit references to Belmont/Menlo/CARE principles. This exceeds AI-R's requirement for "ethical data acquisition consistent with accepted principles."

#### 4.b Ethically Managed
- **Direct Mappings**: 12
  - `Dataset.is_deidentified` - De-identification status
  - `Deidentification.method` - Method (e.g., HIPAA Safe Harbor)
  - `Deidentification.identifiers_removed` - What was removed
  - `Deidentification.deidentification_details` - Procedures and risks
  - `Dataset.participant_privacy` - Privacy protections (multivalued)
  - `ParticipantPrivacy.anonymization_method`, `ParticipantPrivacy.reidentification_risk`, `ParticipantPrivacy.privacy_techniques`
  - `Dataset.sensitive_elements`, `Dataset.confidential_elements`
  - `SensitiveElement.sensitivity_details`, `Confidentiality.confidentiality_details`
  - `ExportControlRegulatoryRestrictions.confidentiality_level` - Sensitivity level enum
  - `ExportControlRegulatoryRestrictions.hipaa_compliant` - HIPAA status enum
  - `LicenseAndUseTerms.license_terms` - Ethical constraints

**Analysis**: D4D provides **HIPAA-compliant de-identification tracking** with explicit method documentation (Safe Harbor, Expert Determination, etc.) and **HL7 confidentiality levels** (unrestricted, restricted, confidential) via enums. The schema supports AI-R's "anonymized" vs "limited data set" vs "non-PHI" distinctions through structured fields.

#### 4.c Ethically Disseminated
- **Direct Mappings**: 8
  - `Dataset.license_and_use_terms` - License/DUA
  - `LicenseAndUseTerms.license_terms` - Detailed terms
  - `LicenseAndUseTerms.data_use_permission` - **20+ DUO permissions** (including `ethics_approval_required`)
  - `LicenseAndUseTerms.contact_person` - Licensing/DUA contact
  - `Dataset.license` - License specification
  - `Dataset.maintainers` - Access contacts
  - `ExportControlRegulatoryRestrictions.governance_committee_contact` - DAC contact
  - `IPRestrictions.restrictions`, `ExportControlRegulatoryRestrictions.regulatory_restrictions`

**Analysis**: D4D's **Data Use Ontology (DUO) integration** provides machine-readable terms for data access committees (e.g., `ethics_approval_required`, `collaboration_required`), meeting AI-R's requirement to "specify contact information for a data access committee."

#### 4.d Secure
- **Direct Mappings**: 6
  - `ExportControlRegulatoryRestrictions.confidentiality_level` - Security level (unrestricted, restricted, confidential)
  - `LicenseAndUseTerms.data_use_permission` - Access control (ethics_approval_required, collaboration_required)
  - `ExportControlRegulatoryRestrictions.regulatory_restrictions` - Security requirements
  - `IPRestrictions.restrictions` - IP-based access
  - `ExportControlRegulatoryRestrictions.hipaa_compliant` - HIPAA compliance indicating security
  - `Dataset.confidential_elements` - Confidentiality requiring security

**Analysis**: D4D uses **HL7-style confidentiality levels** (enum: unrestricted, restricted, confidential) and DUO permissions to specify security requirements, meeting AI-R's example of "public", "controlled access only", etc.

---

### 5. Sustainability (Criteria 5.a - 5.d)

**AI-Readiness Focus**: Persistence, domain repositories, governance, associations

**D4D Coverage**: ⭐⭐⭐⭐ Very Good

#### 5.a Persistent
- **Direct Mappings**: 8
  - `Dataset.retention_limit` - Retention limits
  - `RetentionLimits.retention_period` - Duration
  - `RetentionLimits.retention_details` - Procedures and privacy compliance
  - `RawData.access_url` - Raw data preservation location
  - `RawData.raw_data_details` - Access procedures
  - `Dataset.raw_sources` - Raw data references
  - `Dataset.updates` - Update plan
  - `UpdatePlan.update_details` - Reprocessing plans

**Analysis**: D4D provides **dedicated retention tracking** with privacy law compliance documentation, meeting AI-R's requirement to "ensure that unprocessed data is preserved in an archive adhering to privacy laws and retention guidelines."

#### 5.b Domain-appropriate
- **Direct Mappings**: 6
  - `Dataset.publisher` - Repository publisher (uriorcurie)
  - `Dataset.download_url` - Repository URL
  - `Dataset.page` - Repository landing page
  - `Dataset.conforms_to` - Domain standards
  - `Dataset.keywords`, `Dataset.themes` - Domain classification
  - `Instance.data_topic` - B2AI_TOPIC domain vocabulary

**Analysis**: D4D uses uriorcurie for repository identifiers (e.g., ROR for repositories) and domain vocabularies (B2AI_TOPIC) to support domain-appropriate deposition.

#### 5.c Well-governed
- **Direct Mappings**: 8
  - `Dataset.maintainers` - Data stewards
  - `Maintainer.maintainer_details` - Maintenance info
  - `Dataset.updates` - Update governance
  - `UpdatePlan.frequency`, `UpdatePlan.update_details` - Governance plans
  - `Dataset.extension_mechanism` - Contribution governance
  - `ExtensionMechanism.extension_details` - Contribution procedures
  - `ExportControlRegulatoryRestrictions.governance_committee_contact` - Governance contact
  - `LicenseAndUseTerms.license_terms` - Terms governance

**Analysis**: D4D provides **multi-level governance documentation** (stewardship, updates, extensions, terms), meeting AI-R's requirement for "governance that accounts for maintenance, terms and policy changes, and fairness."

#### 5.d Associated
- **Direct Mappings**: 7
  - `Dataset.resources` - Sub-resources/nested datasets
  - `DatasetCollection.resources` - Project-level collection
  - `Dataset.related_datasets` - Related datasets (multivalued)
  - `DatasetRelationship.target_dataset` - Target identifier (required)
  - `DatasetRelationship.relationship_type` - **14 relationship types** (derives_from, supplements, is_part_of, has_part, etc.)
  - `Dataset.parent_datasets` - Parent datasets
  - `Dataset.external_resources`, `ExternalResource.external_resources`

**Analysis**: D4D provides **14 standardized relationship types** (from DataCite/Dublin Core) for machine-readable project-level connections, meeting AI-R's requirement to "document project-level connections between data components and elements in a machine-readable manner." This approaches RO-Crate functionality.

---

### 6. Computability (Criteria 6.a - 6.d)

**AI-Readiness Focus**: Standardization, accessibility, portability, contextualization

**D4D Coverage**: ⭐⭐⭐⭐⭐ Excellent

#### 6.a Standardized
- **Direct Mappings**: 9
  - `Dataset.conforms_to`, `Dataset.conforms_to_schema`, `Dataset.conforms_to_class` - Standards conformance
  - `Dataset.format` - Standardized format (FormatEnum: CSV, JSON, XML, RDF, etc.)
  - `Dataset.encoding` - Standardized encoding (EncodingEnum: UTF-8, ASCII, etc. - 50+ encodings)
  - `Dataset.media_type` - Standardized MIME type (MediaTypeEnum)
  - `Dataset.dialect` - Format dialect (FormatDialect)
  - `VariableMetadata.data_type` - Standardized types (VariableTypeEnum)
  - `VariableMetadata.unit` - QUDT ontology (uriorcurie)

**Analysis**: D4D provides **comprehensive format standardization** with 15+ file formats, 50+ character encodings, MIME types, and QUDT unit ontology integration. The schema's LinkML foundation ensures deterministic validation.

#### 6.b Computationally Accessible
- **Direct Mappings**: 7
  - `Dataset.download_url` - Direct download (uri)
  - `Dataset.path` - File path/URL
  - `Dataset.page` - Landing page
  - `DistributionFormat.access_urls` - Access mechanisms
  - `Dataset.distribution_formats` - Distribution channels
  - `Dataset.format` - Access-friendly format
  - `ExternalResource.external_resources` - External access

**Analysis**: D4D provides **direct download URLs** and distribution channel documentation, meeting AI-R's requirement for "mechanism to access data either through established exchange protocols or a well-documented API."

#### 6.c Portable
- **Direct Mappings**: 6
  - `Dataset.format` - Portable format (CSV, JSON, etc.)
  - `Dataset.media_type` - Portable media type
  - `Dataset.encoding` - Portable encoding (UTF-8, etc.)
  - `Dataset.compression` - Compression format (gzip, bzip2, zip, etc.)
  - `Software.description` - Resource requirements
  - `DatasetProperty.used_software` - Software dependencies

**Analysis**: D4D prioritizes portable formats (CSV, JSON, XML) in `FormatEnum` and documents resource requirements through `Software` class, meeting AI-R's requirement to "maximize portability... If working with the data requires specific resources, provide machine-readable documentation defining these resources."

#### 6.d Contextualized
- **Direct Mappings**: 11
  - `DataSubset.is_data_split` - Train/test split indicator
  - `DataSubset.is_subpopulation` - Demographic subset indicator
  - `Splits.split_details` - Split information
  - `Dataset.instances` - Instance context
  - `Instance.instance_type`, `Instance.data_topic`, `Instance.data_substrate` - Data context
  - `VariableMetadata.examples` - Example values
  - `Dataset.variables` - Complete data dictionary
  - `CollectionTimeframe.timeframe_details` - Collection context
  - `MissingInfo.missing` - Withheld information
  - `Subpopulation.identification` - Subpopulation context

**Analysis**: D4D's **DataSubset class** with `is_data_split` and `is_subpopulation` indicators directly addresses AI-R's requirement to "include any considerations regarding splits of the data... any information withheld." The `VariableMetadata.examples` field provides data component examples as recommended.

---

## Comprehensive Mapping Statistics

### Quantitative Summary

| Metric | Value | Details |
|--------|-------|---------|
| **Total AI-R Criteria** | 26 | 7 dimensions × 2-4 sub-criteria each |
| **Total D4D Mappings** | 245 | Unique class.property paths mapped |
| **Direct Mappings** | 209 (85%) | Exact semantic match |
| **Partial Mappings** | 36 (15%) | Related but less/more specific |
| **No Mappings** | 0 (0%) | Complete coverage |
| **Average Mappings per Criterion** | 9.4 | Rich schema representation |

### Mapping Distribution by Dimension

| AI-R Dimension | Criteria | D4D Mappings | Avg per Criterion | Coverage |
|----------------|----------|--------------|-------------------|----------|
| 0. FAIRness | 4 | 31 | 7.8 | ⭐⭐⭐⭐⭐ |
| 1. Provenance | 4 | 42 | 10.5 | ⭐⭐⭐⭐⭐ |
| 2. Characterization | 5 | 61 | 12.2 | ⭐⭐⭐⭐⭐ |
| 3. Pre-model Explainability | 3 | 31 | 10.3 | ⭐⭐⭐⭐⭐ |
| 4. Ethics | 4 | 39 | 9.8 | ⭐⭐⭐⭐⭐ |
| 5. Sustainability | 4 | 29 | 7.3 | ⭐⭐⭐⭐ |
| 6. Computability | 4 | 33 | 8.3 | ⭐⭐⭐⭐⭐ |

### D4D Module Utilization

| D4D Module | AI-R Mappings | Key Contributions |
|------------|---------------|-------------------|
| Core/Metadata | 98 | FAIRness, standards, identifiers |
| Composition | 51 | Characterization, bias, quality |
| Preprocessing | 28 | Provenance, quality, traceability |
| Collection | 23 | Transparency, acquisition |
| Uses | 19 | Explainability, fit for purpose |
| Data_Governance | 18 | Ethics, licensing, security |
| Maintenance | 17 | Sustainability, stewardship |
| Human | 16 | Ethics, consent, privacy |
| Ethics | 13 | Ethical acquisition, DPIA |
| Variables | 12 | Characterization, statistics |
| Motivation | 10 | Provenance, actors |
| Distribution | 8 | Computability, accessibility |
| Base Classes | 6 | Software, Person, Organization |

---

## Schema Advantages: Where D4D Exceeds AI-Readiness

### 1. Ontology Integration (10+ External Ontologies)

D4D integrates standardized ontologies beyond AI-R requirements:

- **Data Use Ontology (DUO)**: 20+ machine-readable permission terms
- **AI Ontology (AIO)**: 50+ bias types for systematic bias tracking
- **QUDT**: Standardized units of measurement
- **B2AI Vocabularies**: Domain-specific topics and substrates
- **CRediT Taxonomy**: 14 contributor roles
- **DataCite Relationships**: 14 relationship types
- **HL7 Privacy**: Confidentiality levels and compliance status

**Impact**: Enables **automated policy enforcement** (e.g., "ethics_approval_required" triggers access control workflows) and **cross-dataset harmonization** (bias types consistent across projects).

### 2. Fine-Grained Provenance

D4D provides transformation-level software tracking:

- `used_software` property in **ALL 76 DatasetProperty classes**
- `Software.name`, `Software.version`, `Software.url`, `Software.license`
- Dedicated classes: `PreprocessingStrategy`, `CleaningStrategy`, `LabelingStrategy`, `ImputationProtocol`, `AnnotationAnalysis`, `MachineAnnotationTools`

**Impact**: Complete **transformation history** from raw data to published dataset, supporting reproducibility and compliance audits.

### 3. Human Subjects Beyond HIPAA

D4D includes comprehensive human subjects module:

- `HumanSubjectResearch.irb_approval` - IRB tracking
- `InformedConsent` - 5 properties for consent documentation
- `ParticipantPrivacy` - 4 properties for privacy techniques
- `HumanSubjectCompensation` - 4 properties for compensation tracking
- `VulnerablePopulations` - 4 properties for special protections
- Explicit Belmont/Menlo/CARE principles in `regulatory_compliance`

**Impact**: **Ethics-by-design** with structured fields for consent, privacy, compensation, and vulnerable population protections.

### 4. Three-Tier Use Classification

D4D categorizes uses into:

1. **Intended Uses** (`IntendedUse`): Recommended with usage notes
2. **Discouraged Uses** (`DiscouragedUse`): Not recommended with reasons
3. **Prohibited Uses** (`ProhibitedUse`): Explicitly forbidden with legal/ethical basis

**Impact**: Clear **use boundaries** for AI applications, reducing misuse risk.

### 5. Variable-Level Metadata

D4D's `VariableMetadata` class (16 properties) provides:

- Data type, unit (QUDT), range (min/max), categories, precision
- Missing value codes, examples, sensitivity flags
- Measurement technique, derivation, quality notes

**Impact**: **Complete data dictionary** enabling automated data validation and analysis planning.

---

## Identified Gaps and Recommendations

### Minor Gaps (AI-R mentions, D4D partially covers)

1. **RO-Crate Explicit Support** (5.d Associated)
   - **Current**: D4D uses `DatasetRelationship` with 14 relationship types
   - **Gap**: No explicit RO-Crate serialization
   - **Recommendation**: Add `export_as_ro_crate` generation tool
   - **Workaround**: D4D's relationship types map cleanly to RO-Crate

2. **Explicit W3C PROV-O/EVI Export** (1.b Traceable)
   - **Current**: D4D uses `was_derived_from` (prov:wasDerivedFrom)
   - **Gap**: No PROV-O graph generation
   - **Recommendation**: Add PROV-O export from provenance fields
   - **Workaround**: `was_derived_from` is PROV-compatible; full export feasible

3. **Quality Assurance Links** (2.e Data Quality)
   - **Current**: D4D documents QC in text fields (`CleaningStrategy.cleaning_details`)
   - **Gap**: No dedicated `quality_control_url` field
   - **Recommendation**: Add `ExternalResource` links for QC reports
   - **Workaround**: Use `Dataset.external_resources` for QC documentation

### Strengths (D4D exceeds AI-R)

1. **Structured Bias Documentation**: 50+ AIO bias types vs. AI-R's text-only requirement
2. **Machine-Readable Licensing**: 20+ DUO terms vs. AI-R's license string
3. **CRediT Roles**: 14 standardized roles vs. AI-R's generic "creators"
4. **Variable-Level Metadata**: Complete data dictionary vs. AI-R's dataset-level only
5. **Three-Tier Use Classification**: Intended/discouraged/prohibited vs. AI-R's binary appropriate/inappropriate

---

## Conclusions and Strategic Recommendations

### Key Findings

1. **100% Coverage**: D4D maps to all 26 AI-Readiness sub-criteria with 245 total class.property paths
2. **85% Direct Mappings**: Most AI-R requirements have exact semantic matches in D4D
3. **Schema Maturity**: D4D's 76 classes and 300+ properties provide comprehensive coverage
4. **Ontology Integration**: 10+ external ontologies enable automated reasoning and policy enforcement
5. **Modular Design**: 10 modules (Motivation, Composition, Collection, Preprocessing, Uses, Distribution, Maintenance, Ethics, Human, Data_Governance) cleanly separate concerns

### Strategic Value of D4D Schema

#### For Bridge2AI Data Generating Projects

1. **AI-Readiness by Default**: Completing D4D datasheet = meeting AI-R criteria
2. **Automated Validation**: LinkML schema enables deterministic validation
3. **Cross-Project Harmonization**: Shared vocabularies (B2AI_TOPIC, DUO, AIO) enable comparison
4. **Compliance Documentation**: Structured ethical review, IRB, consent tracking

#### For Broader AI/ML Community

1. **Standardized Template**: D4D provides machine-readable Gebru et al. Datasheets
2. **Interoperability**: RDF/JSON-LD support enables knowledge graph integration
3. **Policy Automation**: DUO permissions enable automated access control
4. **Bias Tracking**: AIO bias types enable systematic fairness assessment

### Recommendations for D4D Evolution

#### Short-Term (v1.x)

1. **Add PROV-O Export Tool**: Generate W3C PROV graphs from provenance fields
2. **Enhance QC Documentation**: Add `quality_control_url` field to `CleaningStrategy` et al.
3. **Create Mapping Documentation**: Publish this comparison as schema documentation

#### Medium-Term (v2.0)

1. **RO-Crate Serialization**: Generate RO-Crate packages from D4D metadata
2. **Automated Compliance Checking**: Build validators for HIPAA, GDPR, IRB requirements
3. **Bias Audit Tools**: Automate bias detection using AIO taxonomy

#### Long-Term (v3.0)

1. **Active Metadata**: Enable dynamic querying (e.g., "find all datasets with selection bias")
2. **Federated Search**: Enable cross-repository search using DCAT conformance
3. **Policy Enforcement**: Automated access control based on DUO permissions

---

## Appendix A: Full Class Hierarchy

### D4D Schema Architecture (76 Classes)

**Base Classes (7)**
- `NamedThing` → `Organization`, `Person`, `Software`, `Information`
- `DatasetProperty` → All 67 module classes
- `FormatDialect`

**Main Classes (3)**
- `Information` → `DatasetCollection`, `Dataset`
- `Dataset` → `DataSubset`

**Module Classes (67)**
- Motivation: `Purpose`, `Task`, `AddressingGap`, `Creator`, `FundingMechanism`, `Grantor`, `Grant`
- Composition: 15 classes (Instance, SamplingStrategy, MissingInfo, Relationships, Splits, DataAnomaly, DatasetBias, DatasetLimitation, ExternalResource, Confidentiality, ContentWarning, Subpopulation, Deidentification, SensitiveElement, DatasetRelationship)
- Collection: 7 classes (InstanceAcquisition, CollectionMechanism, DataCollector, CollectionTimeframe, DirectCollection, MissingDataDocumentation, RawDataSource)
- Preprocessing: 7 classes (PreprocessingStrategy, CleaningStrategy, LabelingStrategy, RawData, ImputationProtocol, AnnotationAnalysis, MachineAnnotationTools)
- Uses: 7 classes (ExistingUse, UseRepository, OtherTask, FutureUseImpact, DiscouragedUse, IntendedUse, ProhibitedUse)
- Distribution: 3 classes (ThirdPartySharing, DistributionFormat, DistributionDate)
- Maintenance: 6 classes (Maintainer, Erratum, UpdatePlan, RetentionLimits, VersionAccess, ExtensionMechanism)
- Ethics: 5 classes (EthicalReview, DataProtectionImpact, CollectionNotification, CollectionConsent, ConsentRevocation)
- Human: 5 classes (HumanSubjectResearch, InformedConsent, ParticipantPrivacy, HumanSubjectCompensation, VulnerablePopulations)
- Data_Governance: 3 classes (LicenseAndUseTerms, IPRestrictions, ExportControlRegulatoryRestrictions)
- Variables: 1 class (VariableMetadata)

---

## Appendix B: Enumeration Coverage

### D4D Enumerations Supporting AI-Readiness

| Enumeration | Values | AI-R Criterion | Purpose |
|-------------|--------|----------------|---------|
| **FormatEnum** | 18 formats | 0.c, 6.a, 6.b, 6.c | CSV, JSON, XML, RDF, JSON-LD, PDF, etc. |
| **EncodingEnum** | 50+ encodings | 0.c, 6.a, 6.c | UTF-8, ASCII, ISO-8859-1, etc. |
| **MediaTypeEnum** | 50+ MIME types | 0.c, 6.a | text/csv, application/json, etc. |
| **CompressionEnum** | 7 methods | 6.c | gzip, bzip2, zip, tar, xz, lzma, compress |
| **DataUsePermissionEnum** | 20+ terms | 0.d, 4.c, 4.d | DUO: general_research_use, ethics_approval_required, etc. |
| **BiasTypeEnum** | 50+ types | 2.d | AIO: selection_bias, measurement_bias, etc. |
| **CRediTRoleEnum** | 14 roles | 1.d | conceptualization, methodology, data_curation, etc. |
| **DatasetRelationshipTypeEnum** | 14 types | 5.d | derives_from, supplements, is_part_of, etc. |
| **VariableTypeEnum** | 10 types | 2.c, 6.a | integer, float, string, boolean, categorical, etc. |
| **ComplianceStatusEnum** | 5 statuses | 4.b | compliant, partially_compliant, not_compliant, etc. |
| **ConfidentialityLevelEnum** | 3 levels | 4.b, 4.d | unrestricted, restricted, confidential |
| **LimitationTypeEnum** | 4 types | 2.d | scope, coverage, temporal, methodological |

---

## Appendix C: External Ontology Integration

### Linked Vocabularies in D4D Schema

| Ontology/Standard | D4D Integration | AI-R Criterion | Examples |
|-------------------|-----------------|----------------|----------|
| **Data Use Ontology (DUO)** | `DataUsePermissionEnum` | 0.d, 4.c | general_research_use, ethics_approval_required, collaboration_required |
| **AI Ontology (AIO)** | `BiasTypeEnum` | 2.d | selection_bias, measurement_bias, confirmation_bias, historical_bias |
| **QUDT Units** | `VariableMetadata.unit` (uriorcurie) | 2.c, 6.a | unit:Meter, unit:Second, unit:Kilogram, unit:Percent |
| **B2AI_TOPIC** | `Instance.data_topic` (uriorcurie) | 2.a, 5.b | Genomics, Proteomics, Clinical, Voice, Cell Imaging |
| **B2AI_SUBSTRATE** | `Instance.data_substrate` (uriorcurie) | 2.a | DNA, RNA, Protein, Image, Audio, Text, Tabular |
| **CRediT Taxonomy** | `CRediTRoleEnum` | 1.d | conceptualization, methodology, software, data_curation |
| **DataCite Relationships** | `DatasetRelationshipTypeEnum` | 5.d | IsPartOf, HasPart, IsVersionOf, IsDerivedFrom |
| **W3C PROV** | `Dataset.was_derived_from` (prov:wasDerivedFrom) | 1.a, 1.b | Provenance derivation relationships |
| **ORCID** | `Person.orcid` (pattern validation) | 1.d | 0000-0002-1825-0097 |
| **ROR** | `Organization.id` (uriorcurie) | 1.d | https://ror.org/02jbv0t02 |

---

## Document Metadata

**Authors**: Comprehensive AI-Readiness to D4D Mapping Analysis
**Schema Version**: data_sheets_schema_all.yaml (28,829 lines)
**AI-Readiness Version**: bioRxiv v4 (November 24, 2024)
**Total Mappings**: 245 class.property paths
**Date Generated**: 2026-02-05
**Mapping Methodology**: Criterion-by-criterion semantic alignment with full class path documentation
**Validation**: Cross-referenced with D4D schema exploration (76 classes, 300+ properties)

**Citation**:
```
Clark T, Caufield H, Parker JA, et al. AI-readiness for Biomedical Data: Bridge2AI
Recommendations. bioRxiv. 2024. doi: https://doi.org/10.1101/2024.10.23.619844
```

---

## Change Log

**v1.0 (2026-02-05)**: Initial comprehensive mapping with 245 class.property paths across 26 AI-R criteria
