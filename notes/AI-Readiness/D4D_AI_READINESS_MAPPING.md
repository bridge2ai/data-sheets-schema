# D4D Schema to AI-Readiness Criteria Mapping

**Version**: 2025-12-12
**D4D Schema**: Current LinkML implementation
**AI-Readiness Source**: "AI-readiness for Biomedical Data: Bridge2AI Recommendations" (Table 1, pages 10-12)

---

## Quick Reference

This document provides a **precise mapping** between the 26 AI-readiness criteria and specific D4D schema elements (classes, slots, enums). For comprehensive analysis and gap details, see [D4D_AI_READINESS_GAP_ANALYSIS.md](../../D4D_AI_READINESS_GAP_ANALYSIS.md).

### Coverage Legend

- ✅ **FULL**: Criterion comprehensively addressed by D4D schema
- ⚠️ **PARTIAL**: Criterion partially addressed with identifiable gaps
- ❌ **MISSING**: Criterion not addressed (none found)

---

## Dimension 0: FAIRness (4/4 FULL - 100%)

### 0.a Findable: Persistent identifiers, searchable metadata
**Status**: ✅ FULL

| D4D Element | Type | Module | Description |
|-------------|------|--------|-------------|
| `PersistentIdentifierSchemeEnum` | Enum | Base | DOI, ARK, Handle, PURL, URN, etc. |
| `identifier` | Slot | Dataset | Persistent identifier value |
| `doi` | Slot | Dataset | Digital Object Identifier |
| `orcid` | Slot | Person | ORCID researcher identifier (pattern: `^\d{4}-\d{4}-\d{4}-\d{3}[0-9X]$`) |
| `ror` | Slot | Organization | Research Organization Registry ID |
| `title` | Slot | Dataset | Dataset title (searchable) |
| `description` | Slot | Dataset | Dataset description (searchable) |
| `keywords` | Slot | Dataset | Keywords for discovery |
| `topic` | Slot | Dataset | Bridge2AI topic ontology terms |

**Ontology Mappings**:
- `dcat:Dataset` - DCAT catalog vocabulary
- `schema:Dataset` - Schema.org
- `dcterms:identifier` - Dublin Core identifier

---

### 0.b Accessible: Metadata always available
**Status**: ✅ FULL

| D4D Element | Type | Module | Description |
|-------------|------|--------|-------------|
| `AccessMethod` | Class | Distribution | Access URL, protocol, approval requirements |
| `access_url` | Slot | AccessMethod | Direct access endpoint |
| `access_protocol` | Slot | AccessMethod | Transfer protocol |
| `LandingPage` | Class | Base | Persistent metadata landing page |
| `landing_page` | Slot | Dataset | URL for metadata access |

**Ontology Mappings**:
- `dcat:landingPage` - DCAT landing page
- `schema:url` - Schema.org URL

---

### 0.c Interoperable: Formally defined specifications (RDF, JSON-LD)
**Status**: ✅ FULL

| D4D Element | Type | Module | Description |
|-------------|------|--------|-------------|
| **LinkML Framework** | - | - | Generates JSON-LD, RDF, OWL, SHACL |
| **15+ Ontology Integrations** | - | - | See table below |

**Integrated Ontologies**:

| Prefix | Ontology | URI | Usage |
|--------|----------|-----|-------|
| `schema:` | Schema.org | http://schema.org/ | Primary semantic mappings |
| `dcat:` | DCAT | http://www.w3.org/ns/dcat# | Dataset catalog vocabulary |
| `dcterms:` | Dublin Core | http://purl.org/dc/terms/ | Metadata terms |
| `prov:` | PROV-O | http://www.w3.org/ns/prov# | Provenance |
| `skos:` | SKOS | http://www.w3.org/2004/02/skos/core# | Concept schemes |
| `AIO:` | AI Ontology | https://www.ohio.edu/ai-ontology/ | Bias taxonomy |
| `DUO:` | Data Use Ontology | http://purl.obolibrary.org/obo/DUO_ | Usage permissions |
| `B2AI_TOPIC:` | Bridge2AI Topics | https://w3id.org/bridge2ai/b2ai-topics/ | Domain topics |
| `B2AI_SUBSTRATE:` | Bridge2AI Substrates | https://w3id.org/bridge2ai/b2ai-substrates/ | Data types |
| `qudt:` | QUDT | http://qudt.org/schema/qudt/ | Units/quantities |
| `sh:` | SHACL | http://www.w3.org/ns/shacl# | Validation shapes |
| `datacite:` | DataCite | http://purl.org/spar/datacite/ | Citation metadata |
| `foaf:` | FOAF | http://xmlns.com/foaf/0.1/ | People/organizations |
| `OBI:` | OBI | http://purl.obolibrary.org/obo/OBI_ | Biomedical investigations |
| `credit:` | CRediT | https://credit.niso.org/ | Contributor roles |

**Generated Artifacts**:
- `project/jsonld/data_sheets_schema.jsonld` - JSON-LD context
- `project/owl/data_sheets_schema.owl.ttl` - OWL ontology (Turtle)
- `project/shacl/data_sheets_schema.shacl.ttl` - SHACL validation
- `project/jsonschema/data_sheets_schema.schema.json` - JSON Schema

---

### 0.d Reusable: Clear data usage license/DUA
**Status**: ✅ FULL

| D4D Element | Type | Module | Description |
|-------------|------|--------|-------------|
| `LicenseAndUseTerms` | Class | Data_Governance | License, DUA, terms of use |
| `license` | Slot | LicenseAndUseTerms | License type |
| `license_url` | Slot | LicenseAndUseTerms | Machine-readable license URL |
| `data_use_agreement` | Slot | LicenseAndUseTerms | DUA document |
| `DataUsePermissionEnum` | Enum | Data_Governance | **25 DUO-based permissions** |
| `IPRestrictions` | Class | Data_Governance | Intellectual property constraints |

**DataUsePermissionEnum Values** (DUO mappings):
- `general_research_use` → DUO:0000042
- `health_medical_biomedical_research` → DUO:0000006
- `disease_specific_research` → DUO:0000007
- `commercial_use` → DUO:0000017
- `non_profit_use_only` → DUO:0000046
- `ethics_approval_required` → DUO:0000021
- `irb_required` → DUO:0000022
- `geographic_restriction` → DUO:0000022
- `institution_specific_restriction` → DUO:0000028
- `return_to_database_or_resource` → DUO:0000029
- ... *(25 total DUO permissions)*

---

## Dimension 1: Provenance (3/4 FULL, 1/4 PARTIAL - 75%)

### 1.a Transparent: Sources traceable to ground-truth
**Status**: ✅ FULL

| D4D Element | Type | Module | Description |
|-------------|------|--------|-------------|
| `DataSource` | Class | Composition | Source name, URL, DOI |
| `data_source_name` | Slot | DataSource | Source name |
| `data_source_url` | Slot | DataSource | Source URL |
| `data_source_doi` | Slot | DataSource | Source DOI |
| `OriginalDataSource` | Class | Composition | Raw/unprocessed data source |
| `derived_from` | Slot | DatasetRelationship | Source dataset reference |
| `DataCollectionStrategy` | Class | Collection | Ground-truth acquisition method |
| `source_data` | Slot | Dataset | Upstream dataset links |

**Ontology Mappings**:
- `prov:wasDerivedFrom` - PROV-O derivation
- `datacite:IsDerivedFrom` - DataCite relationship

---

### 1.b Traceable: Data transformation steps documented
**Status**: ⚠️ PARTIAL

| D4D Element | Type | Module | Description |
|-------------|------|--------|-------------|
| `PreprocessingStrategy` | Class | Preprocessing | Transformation description |
| `preprocessing_description` | Slot | PreprocessingStrategy | Free-text description |
| `preprocessing_software` | Slot | PreprocessingStrategy | Software references |
| `cleaning_procedures` | Slot | DataManipulation | Cleaning steps |
| `normalization_procedures` | Slot | DataManipulation | Normalization steps |
| `deduplication_procedures` | Slot | DataManipulation | Deduplication steps |
| `DataManipulation` | Class | Preprocessing | Data cleaning/normalization |
| `Software` | Class | Base | Tool name, version, license, URL |

**Gaps**:
- ❌ No formal PROV-O graph structure (Entity→Activity→Agent)
- ❌ No EVI (Evidence Graph) vocabulary support
- ❌ No machine-actionable workflow references (CWL, Nextflow, Snakemake)
- ⚠️ Transformation steps as free text, not structured provenance

**Recommended Addition**: `ProvenanceGraph` class with PROV-O mappings (see gap analysis)

---

### 1.c Interpretable: Software for transformations available
**Status**: ✅ FULL

| D4D Element | Type | Module | Description |
|-------------|------|--------|-------------|
| `Software` | Class | Base | Software metadata |
| `software_name` | Slot | Software | Software name |
| `software_version` | Slot | Software | Version number |
| `software_license` | Slot | Software | License (BSD, MIT, GPL, Apache, etc.) |
| `software_url` | Slot | Software | Source code/documentation URL |
| `software_doi` | Slot | Software | Software DOI for citability |
| `preprocessing_software` | Slot | PreprocessingStrategy | Link to Software instances |

**Ontology Mappings**:
- `schema:SoftwareApplication` - Schema.org
- `qudt:SoftwareSource` - QUDT

---

### 1.d Key Actors Identified: People/organizations responsible
**Status**: ✅ FULL

| D4D Element | Type | Module | Description |
|-------------|------|--------|-------------|
| `Person` | Class | Base | Person metadata |
| `person_name` | Slot | Person | Full name |
| `email` | Slot | Person | Email address |
| `orcid` | Slot | Person | ORCID identifier (pattern validated) |
| `institution` | Slot | Person | Affiliated institution |
| `Organization` | Class | Base | Organization metadata |
| `organization_name` | Slot | Organization | Organization name |
| `organization_url` | Slot | Organization | Organization URL |
| `ror` | Slot | Organization | ROR identifier |
| `CRediTRoleEnum` | Enum | Base | **14 contributor roles** |
| `Grant` | Class | Motivation | Grant metadata |
| `Grantor` | Class | Motivation | Funding organization |

**CRediTRoleEnum Values**:
- `conceptualization` → https://credit.niso.org/contributor-roles/conceptualization/
- `data_curation` → https://credit.niso.org/contributor-roles/data-curation/
- `formal_analysis` → https://credit.niso.org/contributor-roles/formal-analysis/
- `funding_acquisition` → https://credit.niso.org/contributor-roles/funding-acquisition/
- `investigation` → https://credit.niso.org/contributor-roles/investigation/
- `methodology` → https://credit.niso.org/contributor-roles/methodology/
- `project_administration` → https://credit.niso.org/contributor-roles/project-administration/
- `resources` → https://credit.niso.org/contributor-roles/resources/
- `software` → https://credit.niso.org/contributor-roles/software/
- `supervision` → https://credit.niso.org/contributor-roles/supervision/
- `validation` → https://credit.niso.org/contributor-roles/validation/
- `visualization` → https://credit.niso.org/contributor-roles/visualization/
- `writing_original_draft` → https://credit.niso.org/contributor-roles/writing-original-draft/
- `writing_review_editing` → https://credit.niso.org/contributor-roles/writing-review-editing/

**Ontology Mappings**:
- `foaf:Person` - FOAF person
- `schema:Organization` - Schema.org organization
- `prov:Agent` - PROV-O agent

---

## Dimension 2: Characterization (3/5 FULL, 2/5 PARTIAL - 60%)

### 2.a Semantics: Descriptive metadata, keywords, vocabularies
**Status**: ✅ FULL

| D4D Element | Type | Module | Description |
|-------------|------|--------|-------------|
| `title` | Slot | Dataset | Dataset title |
| `description` | Slot | Dataset | Dataset description |
| `abstract` | Slot | Dataset | Dataset abstract |
| `keywords` | Slot | Dataset | Descriptive keywords (list) |
| `topic` | Slot | Dataset | Bridge2AI topic ontology |
| `B2AI_TOPIC` | Prefix | - | Domain topics ontology |
| `B2AI_SUBSTRATE` | Prefix | - | Data types ontology |

**Ontology Mappings**:
- `dcterms:subject` - Dublin Core subject
- `schema:keywords` - Schema.org keywords
- `skos:Concept` - SKOS concept scheme

---

### 2.b Statistics: Statistical characterizations, missing value encoding
**Status**: ⚠️ PARTIAL

| D4D Element | Type | Module | Description |
|-------------|------|--------|-------------|
| `VariableMetadata` | Class | Variables | Field-level metadata |
| `variable_name` | Slot | VariableMetadata | Variable name |
| `variable_description` | Slot | VariableMetadata | Variable description |
| `variable_type` | Slot | VariableMetadata | categorical/continuous/ordinal/binary/datetime/text/identifier |
| `missing_value_code` | Slot | VariableMetadata | Missing value representation |
| `missing_value_description` | Slot | VariableMetadata | Why values missing |
| `allowed_values` | Slot | VariableMetadata | Categorical value list |
| `InstanceDistribution` | Class | Composition | Instance count per class |
| `instance_count` | Slot | InstanceDistribution | Count |
| `LabelDistribution` | Class | Composition | Label count distribution |
| `label_count` | Slot | LabelDistribution | Count |

**Gaps**:
- ❌ No comprehensive `StatisticalSummary` class for:
  - Continuous variables: mean, median, std dev, min, max, quartiles
  - Categorical variables: frequency distributions, mode
  - Missing value percentages/patterns
  - Outlier detection/handling
  - Correlation matrices
- ❌ No STATO (Statistics Ontology) integration
- ⚠️ Field-level statistics exist, but **no dataset-level aggregates**

**Recommended Addition**: `StatisticalSummary` class (see gap analysis)

---

### 2.c Standards: Machine-readable data dictionary/schema
**Status**: ✅ FULL

| D4D Element | Type | Module | Description |
|-------------|------|--------|-------------|
| `VariableMetadata` | Class | Variables | **Complete data dictionary** |
| `variable_name` | Slot | VariableMetadata | Field name |
| `variable_description` | Slot | VariableMetadata | Field description |
| `variable_type` | Slot | VariableMetadata | VariableTypeEnum |
| `variable_measured` | Slot | VariableMetadata | What is measured |
| `variable_unit` | Slot | VariableMetadata | Units (QUDT) |
| `allowed_values` | Slot | VariableMetadata | Allowed values |
| `is_primary_key` | Slot | VariableMetadata | Primary key flag |
| `is_unique` | Slot | VariableMetadata | Uniqueness constraint |
| `FormatDialect` | Class | Distribution | CSV/TSV specification |
| `delimiter` | Slot | FormatDialect | Field delimiter |
| `header` | Slot | FormatDialect | Header row flag |
| `quote_char` | Slot | FormatDialect | Quote character |
| `encoding` | Slot | FormatDialect | Character encoding |
| `null_value_representation` | Slot | FormatDialect | Null representation |

**Ontology Mappings**:
- `schema:PropertyValue` - Schema.org property
- `qudt:Unit` - QUDT units

**Generated Artifacts**:
- `project/jsonschema/data_sheets_schema.schema.json` - Machine-readable JSON Schema

---

### 2.d Potential Sources of Bias: Known biases, assumptions documented
**Status**: ✅ FULL

| D4D Element | Type | Module | Description |
|-------------|------|--------|-------------|
| `DatasetBias` | Class | Composition | Bias documentation |
| `bias_description` | Slot | DatasetBias | Bias description |
| `bias_type` | Slot | DatasetBias | BiasTypeEnum |
| `bias_mitigation_strategy` | Slot | DatasetBias | Mitigation approach |
| `BiasTypeEnum` | Enum | Composition | **9 bias types (AIO mapped)** |
| `Limitation` | Class | Uses | Dataset limitations |
| `limitation_description` | Slot | Limitation | Limitation description |
| `limitation_type` | Slot | Limitation | LimitationTypeEnum |
| `LimitationTypeEnum` | Enum | Uses | **8 limitation types** |
| `assumptions` | Slot | Dataset | Underlying assumptions |
| `BiasMitigationStrategy` | Class | Composition | Remediation approaches |

**BiasTypeEnum Values** (AIO mappings):
- `selection_bias` → AIO:0000001
- `measurement_bias` → AIO:0000002
- `omitted_variable_bias` → AIO:0000003
- `recall_bias` → AIO:0000004
- `reporting_bias` → AIO:0000005
- `systematic_error` → AIO:0000006
- `random_error` → AIO:0000007
- `other_bias`
- `unknown`

**LimitationTypeEnum Values**:
- `data_limitations`
- `methodological_limitations`
- `generalization_limitations`
- `technical_limitations`
- `ethical_limitations`
- `resource_limitations`
- `temporal_limitations`
- `other_limitations`

---

### 2.e Data Quality: QC procedures described
**Status**: ⚠️ PARTIAL

| D4D Element | Type | Module | Description |
|-------------|------|--------|-------------|
| `QualityControlProcedure` | Class | Preprocessing | QC procedures |
| `quality_control_description` | Slot | QualityControlProcedure | QC description |
| `quality_control_software` | Slot | QualityControlProcedure | QC tools |
| `ValidationProcedure` | Class | Preprocessing | Validation procedures |
| `validation_description` | Slot | ValidationProcedure | Validation description |
| `validation_software` | Slot | ValidationProcedure | Validation tools |
| `DataManipulation` | Class | Preprocessing | Cleaning/normalization |
| `cleaning_procedures` | Slot | DataManipulation | Cleaning steps |
| `normalization_procedures` | Slot | DataManipulation | Normalization steps |
| `CollectionMechanism` | Class | Collection | Collection validation |
| `validation_mechanisms` | Slot | CollectionMechanism | Validation mechanisms |

**Gaps**:
- ⚠️ QC elements **scattered across 3 modules** (Collection, Preprocessing, Composition)
- ❌ No consolidated `QualityControl` class with:
  - QC plan/protocol reference
  - Acceptance criteria/thresholds
  - QC metrics/results
  - QC certification/approval
  - QC workflow provenance
- ❌ No IAO (Information Artifact Ontology) quality mappings

**Recommended Addition**: Consolidated `QualityControl` class (see gap analysis)

---

## Dimension 3: Pre-model Explainability (3/3 FULL - 100%)

### 3.a Data Documentation Template: Datasheets/Healthsheets support
**Status**: ✅ FULL

| D4D Element | Type | Module | Description |
|-------------|------|--------|-------------|
| **D4D Schema Itself** | - | - | **IS the datasheet template** |
| `Dataset` | Class | Main | Root datasheet class |
| **10 User-Facing Modules** | - | - | Motivation, Composition, Collection, Preprocessing, Uses, Distribution, Maintenance, Ethics, Human, Data_Governance |
| **57 Gebru Questions** | - | - | All original questions covered |
| **+43% More Modules** | - | - | Ethics, Human, Data_Governance, Variables |

**Extends Gebru et al. (2021)**:
- Original: 7 modules, 57 questions, free-text PDF/Word
- D4D: 10 modules, machine-readable YAML/JSON, ontology-mapped

**Reference**: See `D4D_SCHEMA_EVOLUTION_ANALYSIS.md` for complete Gebru mapping

---

### 3.b Fit for Purpose: Appropriate/inappropriate use cases identified
**Status**: ✅ FULL

| D4D Element | Type | Module | Description |
|-------------|------|--------|-------------|
| `IntendedUse` | Class | Uses | Recommended applications |
| `intended_use_description` | Slot | IntendedUse | Use description |
| `intended_use_rationale` | Slot | IntendedUse | Why intended |
| `DiscouragedUse` | Class | Uses | Not recommended uses |
| `discouraged_use_description` | Slot | DiscouragedUse | Use description |
| `discouraged_use_rationale` | Slot | DiscouragedUse | Why discouraged |
| `ProhibitedUse` | Class | Uses | **Forbidden uses** |
| `prohibited_use_description` | Slot | ProhibitedUse | Use description |
| `prohibited_use_legal_basis` | Slot | ProhibitedUse | Legal enforcement basis |
| `future_use_impacts` | Slot | Dataset | Anticipated future uses |
| `recommended_use_cases` | Slot | Dataset | Suggested applications |
| `task_type` | Slot | Dataset | Task categorization |

**Three-Tier System**:
1. **Intended**: Recommended, rationale provided
2. **Discouraged**: Not recommended, rationale provided
3. **Prohibited**: Legally forbidden, legal basis documented

**Influenced by**: RO-Crate/FAIRSCAPE metadata frameworks

---

### 3.c Verifiable: Data integrity mechanisms (checksums)
**Status**: ✅ FULL

| D4D Element | Type | Module | Description |
|-------------|------|--------|-------------|
| `HashAlgorithmEnum` | Enum | Distribution | Hash algorithm types |
| `hash_value` | Slot | Dataset/FileFormat | Checksum value |
| `hash_algorithm` | Slot | Dataset/FileFormat | Algorithm used |
| `FileFormat` | Class | Distribution | File format with checksum |
| `checksum` | Slot | FileFormat | Checksum value |

**HashAlgorithmEnum Values**:
- `md5` - MD5 checksum
- `sha1` - SHA-1 checksum
- `sha256` - SHA-256 checksum (recommended)
- `sha512` - SHA-512 checksum
- `crc32` - CRC-32 checksum

**Ontology Mappings**:
- `dcat:checksum` - DCAT checksum
- `schema:sha256` - Schema.org SHA-256

---

## Dimension 4: Ethics (4/4 FULL - 100%)

### 4.a Ethically Acquired: Belmont/Menlo/CARE principles
**Status**: ✅ FULL

| D4D Element | Type | Module | Description |
|-------------|------|--------|-------------|
| `EthicalReview` | Class | Ethics | Ethics review documentation |
| `ethics_review_required` | Slot | EthicalReview | Review required flag |
| `ethics_review_received` | Slot | EthicalReview | Review received flag |
| `ethics_review_board` | Slot | EthicalReview | Review board name |
| `ethics_approval_number` | Slot | EthicalReview | Approval number |
| `ethics_review_date` | Slot | EthicalReview | Review date |
| `HumanSubjectResearch` | Class | Human | Human subjects research metadata |
| `human_subjects_research` | Slot | HumanSubjectResearch | Human subjects flag |
| `irb_approval` | Slot | HumanSubjectResearch | IRB approval flag |
| `irb_number` | Slot | HumanSubjectResearch | IRB protocol number |
| `vulnerable_populations` | Slot | HumanSubjectResearch | Vulnerable groups (list) |
| `InformedConsent` | Class | Human | Informed consent documentation |
| `informed_consent_obtained` | Slot | InformedConsent | Consent obtained flag |
| `consent_type` | Slot | InformedConsent | Consent type |
| `consent_withdrawal_mechanism` | Slot | InformedConsent | Withdrawal process |
| `CollectionConsent` | Class | Ethics | Collection-time consent |
| `consent_obtained` | Slot | CollectionConsent | Consent flag |
| `consent_form_url` | Slot | CollectionConsent | Consent form URL |
| `VulnerablePopulations` | Class | Human | Special protections |

**Regulatory Coverage**:
- **45 CFR 46 (Common Rule)**: IRB requirements, informed consent
- **Subpart B**: Pregnant women, fetuses, neonates
- **Subpart C**: Prisoners
- **Subpart D**: Children
- **Belmont Report**: Respect for persons, beneficence, justice
- **CARE Principles**: Collective benefit, authority to control, responsibility, ethics

---

### 4.b Ethically Managed: Privacy protection, ethical lifecycle
**Status**: ✅ FULL

| D4D Element | Type | Module | Description |
|-------------|------|--------|-------------|
| `ParticipantPrivacy` | Class | Human | Privacy protections |
| `privacy_protections` | Slot | ParticipantPrivacy | Protection methods |
| `anonymization_procedures` | Slot | ParticipantPrivacy | Anonymization steps |
| `reidentification_risk` | Slot | ParticipantPrivacy | Risk assessment |
| `privacy_impact_assessment` | Slot | ParticipantPrivacy | PIA document |
| `Deidentification` | Class | Human | Deidentification metadata |
| `deidentification_performed` | Slot | Deidentification | Deidentification flag |
| `deidentification_method` | Slot | Deidentification | Deidentification method |
| `deidentification_standard` | Slot | Deidentification | Standard (HIPAA Safe Harbor, Expert Determination) |
| `reidentification_risk_assessment` | Slot | Deidentification | Risk assessment |
| `DataProtectionImpact` | Class | Ethics | GDPR DPIA |
| `data_protection_impact_assessment_required` | Slot | DataProtectionImpact | DPIA required flag |
| `data_protection_impact_assessment_completed` | Slot | DataProtectionImpact | DPIA completed flag |
| `data_protection_impact_assessment_url` | Slot | DataProtectionImpact | DPIA document URL |
| `CollectionNotification` | Class | Ethics | Notification documentation |
| `individuals_notified` | Slot | CollectionNotification | Notification flag |
| `notification_mechanism` | Slot | CollectionNotification | How notified |
| `ConsentRevocation` | Class | Ethics | Consent withdrawal |
| `revocation_mechanism` | Slot | ConsentRevocation | Revocation process |
| `revocation_process_url` | Slot | ConsentRevocation | Process documentation URL |

**Regulatory Coverage**:
- **GDPR**: DPIA, notification, right to erasure
- **HIPAA**: Safe Harbor, Expert Determination deidentification
- **CCPA**: Privacy impact assessment, consent withdrawal

---

### 4.c Ethically Disseminated: Licensing/DUA, data access committee
**Status**: ✅ FULL

| D4D Element | Type | Module | Description |
|-------------|------|--------|-------------|
| `LicenseAndUseTerms` | Class | Data_Governance | License and DUA |
| `license` | Slot | LicenseAndUseTerms | License type |
| `license_url` | Slot | LicenseAndUseTerms | License URL |
| `data_use_agreement` | Slot | LicenseAndUseTerms | DUA document |
| `DataUsePermissionEnum` | Enum | Data_Governance | **25 DUO permissions** |
| `AccessMethod` | Class | Distribution | Access method metadata |
| `access_requires_approval` | Slot | AccessMethod | Approval required flag |
| `data_access_committee` | Slot | Dataset | Governance body |

**DataUsePermissionEnum** (selected values):
- `general_research_use` → DUO:0000042
- `ethics_approval_required` → DUO:0000021
- `irb_required` → DUO:0000022
- `collaboration_required` → DUO:0000020
- `publication_required` → DUO:0000019
- `geographic_restriction` → DUO:0000022
- `institution_specific_restriction` → DUO:0000028
- `time_limit_on_use` → DUO:0000025
- `user_specific_restriction` → DUO:0000026

**Ontology Mappings**:
- DUO (Data Use Ontology) - Full integration
- GA4GH standards alignment

---

### 4.d Secure: Security requirements specified
**Status**: ✅ FULL

| D4D Element | Type | Module | Description |
|-------------|------|--------|-------------|
| `ConfidentialityLevelEnum` | Enum | Data_Governance | **3-tier classification** |
| `ExportControlRegulatoryRestrictions` | Class | Data_Governance | Export control metadata |
| `export_control_applicable` | Slot | ExportControlRegulatoryRestrictions | Export control flag |
| `export_control_regulations` | Slot | ExportControlRegulatoryRestrictions | Applicable regulations |
| `itar_applicable` | Slot | ExportControlRegulatoryRestrictions | ITAR flag |
| `ear_applicable` | Slot | ExportControlRegulatoryRestrictions | EAR flag |
| `confidentiality_level` | Slot | ExportControlRegulatoryRestrictions | ConfidentialityLevelEnum |
| `governance_committee_contact` | Slot | ExportControlRegulatoryRestrictions | Governance contact |
| `security_requirements` | Slot | Dataset | Security requirements |
| `IPRestrictions` | Class | Data_Governance | IP constraints |

**ConfidentialityLevelEnum Values**:
- `unrestricted`: Public/open access data
- `restricted`: Controlled access requiring approval
- `confidential`: Highly confidential with strict access controls

**Standards Mappings**:
- **ISO 27001**: Public, Internal, Highly Confidential
- **NIST SP 800-60**: Low Impact, Moderate Impact, High Impact
- **Traffic Light Protocol (TLP)**: CLEAR, GREEN, AMBER

**Regulatory Coverage**:
- **ITAR**: International Traffic in Arms Regulations
- **EAR**: Export Administration Regulations
- **ISO 27001**: Information security management
- **NIST SP 800-60**: Security categorization

---

## Dimension 5: Sustainability (2/4 FULL, 2/4 PARTIAL - 50%)

### 5.a Persistent: Unprocessed data preserved
**Status**: ✅ FULL

| D4D Element | Type | Module | Description |
|-------------|------|--------|-------------|
| `OriginalDataSource` | Class | Composition | Raw data references |
| `raw_data_preserved` | Slot | Dataset | Preservation flag |
| `raw_data_location` | Slot | Dataset | Archive location |
| `derived_from` | Slot | DatasetRelationship | Source dataset link |
| `preprocessing_strategy` | Slot | Dataset | Transformations from raw |
| `PersistentIdentifierSchemeEnum` | Enum | Base | DOI, ARK, Handle for raw data |

**Ontology Mappings**:
- `prov:wasDerivedFrom` - PROV-O derivation
- `datacite:IsDerivedFrom` - DataCite relationship

---

### 5.b Domain-appropriate: Deposited in specialist repository
**Status**: ⚠️ PARTIAL

| D4D Element | Type | Module | Description |
|-------------|------|--------|-------------|
| `repository` | Slot | Dataset | Repository name (free text) |
| `repository_url` | Slot | Dataset | Repository URL |
| `access_url` | Slot | AccessMethod | Access endpoint |
| `publisher` | Slot | Dataset | Publisher/repository |

**Gaps**:
- ❌ No `RepositoryTypeEnum` to distinguish:
  - Domain-specific biological (GenBank, PDB, ENA, UniProt)
  - Domain-specific clinical (PhysioNet, MIMIC, dbGaP)
  - Domain-specific imaging (TCIA, OpenfMRI)
  - Domain-specific genomic (GEO, SRA, EGA)
  - Institutional repositories
  - General-purpose (Zenodo, Dataverse, Dryad, OSF)
  - Commercial cloud (AWS Open Data, GCP, Azure)
  - Preprint servers (bioRxiv, medRxiv)
- ❌ No repository certification tracking:
  - CoreTrustSeal
  - ISO 16363
  - FAIRsharing.org registration
  - re3data.org registration

**Recommended Addition**: `RepositoryTypeEnum` (see gap analysis)

---

### 5.c Well-governed: Repository with clear governance
**Status**: ⚠️ PARTIAL

| D4D Element | Type | Module | Description |
|-------------|------|--------|-------------|
| `data_access_committee` | Slot | Dataset | **Dataset** governance body |
| `LicenseAndUseTerms` | Class | Data_Governance | Usage policies |
| `ExportControlRegulatoryRestrictions` | Class | Data_Governance | Regulatory governance |
| `governance_committee_contact` | Slot | ExportControlRegulatoryRestrictions | Governance contact |

**Gaps**:
- ✅ **Dataset governance present**
- ❌ **Repository governance missing**
- ❌ No `RepositoryGovernance` class for:
  - Repository policies (preservation, access, takedown)
  - Repository funding/sustainability model
  - Repository certification (CoreTrustSeal, ISO 16363)
  - Repository succession planning
  - Repository service-level agreements (SLA)
- ❌ No repository accreditation tracking

**Recommended Addition**: `RepositoryGovernance` class (see gap analysis)

---

### 5.d Associated: Project-level connections documented (RO-Crate)
**Status**: ✅ FULL

| D4D Element | Type | Module | Description |
|-------------|------|--------|-------------|
| `DatasetRelationship` | Class | Composition | Typed dataset relationships |
| `related_dataset_id` | Slot | DatasetRelationship | Related dataset ID |
| `relationship_type` | Slot | DatasetRelationship | DatasetRelationshipTypeEnum |
| `relationship_description` | Slot | DatasetRelationship | Relationship description |
| `DatasetRelationshipTypeEnum` | Enum | Composition | **14 DataCite types** |
| `parent_datasets` | Slot | Dataset | Hierarchical composition |
| `related_datasets` | Slot | Dataset | Associative relationships |
| `project_url` | Slot | Dataset | Project homepage |
| `Grant` | Class | Motivation | Funding metadata |
| `Grantor` | Class | Motivation | Funder metadata |

**DatasetRelationshipTypeEnum Values** (DataCite mappings):
- `is_part_of` → datacite:IsPartOf
- `has_part` → datacite:HasPart
- `is_version_of` → datacite:IsVersionOf
- `is_new_version_of` → datacite:IsNewVersionOf
- `is_derived_from` → datacite:IsDerivedFrom
- `is_source_of` → datacite:IsSourceOf
- `cites` → datacite:Cites
- `is_cited_by` → datacite:IsCitedBy
- `supplements` → datacite:Supplements
- `is_supplemented_by` → datacite:IsSupplementedBy
- `continues` → datacite:Continues
- `is_continued_by` → datacite:IsContinuedBy
- `is_identical_to` → datacite:IsIdenticalTo
- `is_required_by` → datacite:IsRequiredBy

**Influenced by**: RO-Crate, FAIRSCAPE metadata frameworks

---

## Dimension 6: Computability (3/4 FULL, 1/4 PARTIAL - 75%)

### 6.a Standardized: Follow established standards
**Status**: ✅ FULL

| D4D Element | Type | Module | Description |
|-------------|------|--------|-------------|
| `FormatEnum` | Enum | Distribution | **18 standard formats** |
| `MediaTypeEnum` | Enum | Distribution | **14 IANA media types** |
| `CompressionEnum` | Enum | Distribution | Compression algorithms |
| `FormatDialect` | Class | Distribution | CSV/TSV specifications |

**FormatEnum Values**:
- **Tabular**: `csv`, `tsv`, `json`, `xml`, `parquet`
- **Hierarchical**: `hdf5`, `netcdf`
- **Scientific**: `fits`, `dicom`, `nifti`
- **Image**: `tiff`, `jpeg`, `png`
- **Audio**: `wav`, `mp3`
- **Genomic**: `fastq`, `bam`, `vcf`

**MediaTypeEnum Values** (IANA):
- `text/csv`, `text/tab-separated-values`
- `application/json`, `application/xml`
- `application/octet-stream`
- `image/tiff`, `image/jpeg`, `image/png`
- `audio/wav`, `audio/mpeg`
- `application/x-hdf5`, `application/netcdf`
- `application/dicom`

**CompressionEnum Values**:
- `gzip`, `bzip2`, `zip`, `tar`, `xz`, `lz4`, `zstd`

**Ontology Mappings**:
- `schema:encodingFormat` - Schema.org
- `dcat:mediaType` - DCAT media type

---

### 6.b Computationally Accessible: API/exchange protocols
**Status**: ✅ FULL

| D4D Element | Type | Module | Description |
|-------------|------|--------|-------------|
| `AccessMethod` | Class | Distribution | Access method metadata |
| `access_url` | Slot | AccessMethod | Access endpoint/API URL |
| `access_protocol` | Slot | AccessMethod | Transfer protocol |
| `access_requires_approval` | Slot | AccessMethod | Gated access flag |
| `DistributionMethod` | Enum | Distribution | **7 distribution types** |

**DistributionMethodEnum Values**:
- `direct_download` - Direct file download
- `api_access` - REST/GraphQL API
- `bulk_download` - Bulk transfer
- `streaming` - Streaming access
- `on_request` - Available on request
- `cloud_storage` - S3/GCS/Azure Blob
- `federated_access` - Federated query

**Ontology Mappings**:
- `dcat:accessURL` - DCAT access URL
- `dcat:downloadURL` - DCAT download URL
- `schema:downloadUrl` - Schema.org
- `schema:contentUrl` - Schema.org

---

### 6.c Portable: Cross-platform compatibility
**Status**: ⚠️ PARTIAL

| D4D Element | Type | Module | Description |
|-------------|------|--------|-------------|
| `FormatEnum` | Enum | Distribution | Cross-platform formats (CSV, JSON, Parquet, HDF5) |
| `Software` | Class | Base | Software with `software_url` for downloads |
| `FormatDialect` | Class | Distribution | Format specifications |
| `encoding` | Slot | FormatDialect | Character encoding (UTF-8, ASCII, etc.) |

**Gaps**:
- ❌ No `ResourceRequirements` class for:
  - CPU architecture (x86_64, ARM, etc.)
  - Memory requirements (RAM, disk space)
  - GPU requirements (CUDA, OpenCL)
  - Operating system compatibility
  - Container images (Docker, Singularity)
  - Environment specifications (conda, venv)
- ❌ No containerization metadata
- ❌ No dependency manifests (requirements.txt, environment.yml)

**Recommended Addition**: `ResourceRequirements` class (see gap analysis)

---

### 6.d Contextualized: Data splits, examples provided
**Status**: ✅ FULL

| D4D Element | Type | Module | Description |
|-------------|------|--------|-------------|
| `DataSplit` | Class | Uses | Train/test/validation splits |
| `split_name` | Slot | DataSplit | Split name (train/test/validation) |
| `split_description` | Slot | DataSplit | Split description |
| `split_size` | Slot | DataSplit | Split size |
| `train_tuning_split` | Slot | Dataset | Training/tuning split reference |
| `test_split` | Slot | Dataset | Test split reference |
| `example_records` | Slot | Dataset | Sample data |
| `representative_sample` | Slot | Dataset | Representative sample flag |
| `SamplingStrategy` | Class | Collection | Sampling methodology |
| `is_random` | Slot | SamplingStrategy | Random sampling flag |
| `is_representative` | Slot | SamplingStrategy | Representative sampling flag |
| `sampling_verification_procedures` | Slot | SamplingStrategy | Verification methods |

---

## Summary Matrix

| ID | Criterion | Status | Key D4D Elements |
|----|-----------|--------|------------------|
| **0. FAIRness** | | | |
| 0.a | Findable | ✅ FULL | PersistentIdentifierSchemeEnum, ORCID, ROR, DCAT, keywords |
| 0.b | Accessible | ✅ FULL | AccessMethod, LandingPage, access_url |
| 0.c | Interoperable | ✅ FULL | 15+ ontologies, JSON-LD/RDF/OWL generation |
| 0.d | Reusable | ✅ FULL | LicenseAndUseTerms, DataUsePermissionEnum (25 DUO) |
| **1. Provenance** | | | |
| 1.a | Transparent | ✅ FULL | DataSource, OriginalDataSource, derived_from |
| 1.b | Traceable | ⚠️ PARTIAL | PreprocessingStrategy, Software (no PROV-O graph) |
| 1.c | Interpretable | ✅ FULL | Software (name, version, license, URL, DOI) |
| 1.d | Key Actors | ✅ FULL | Person (ORCID), Organization (ROR), CRediTRoleEnum (14), Grant |
| **2. Characterization** | | | |
| 2.a | Semantics | ✅ FULL | title, description, keywords, topic, B2AI_TOPIC |
| 2.b | Statistics | ⚠️ PARTIAL | VariableMetadata, missing_value_code (no StatisticalSummary) |
| 2.c | Standards | ✅ FULL | VariableMetadata, FormatDialect, QUDT units |
| 2.d | Bias | ✅ FULL | BiasTypeEnum (9 AIO), LimitationTypeEnum (8), assumptions |
| 2.e | Quality | ⚠️ PARTIAL | QualityControlProcedure, ValidationProcedure (scattered) |
| **3. Pre-model Explainability** | | | |
| 3.a | Template | ✅ FULL | D4D Schema itself (10 modules, 57 Gebru questions) |
| 3.b | Fit for Purpose | ✅ FULL | IntendedUse, DiscouragedUse, ProhibitedUse |
| 3.c | Verifiable | ✅ FULL | HashAlgorithmEnum (MD5, SHA256, etc.), checksum |
| **4. Ethics** | | | |
| 4.a | Ethically Acquired | ✅ FULL | EthicalReview, HumanSubjectResearch, InformedConsent, 45 CFR 46 |
| 4.b | Ethically Managed | ✅ FULL | ParticipantPrivacy, Deidentification, DataProtectionImpact (GDPR) |
| 4.c | Ethically Disseminated | ✅ FULL | LicenseAndUseTerms, DataUsePermissionEnum (25 DUO), access_committee |
| 4.d | Secure | ✅ FULL | ConfidentialityLevelEnum (ISO 27001, NIST, TLP), ExportControl |
| **5. Sustainability** | | | |
| 5.a | Persistent | ✅ FULL | OriginalDataSource, raw_data_preserved, PersistentIdentifier |
| 5.b | Domain-appropriate | ⚠️ PARTIAL | repository, repository_url (no RepositoryTypeEnum) |
| 5.c | Well-governed | ⚠️ PARTIAL | data_access_committee (no RepositoryGovernance) |
| 5.d | Associated | ✅ FULL | DatasetRelationship (14 DataCite types), Grant, project_url |
| **6. Computability** | | | |
| 6.a | Standardized | ✅ FULL | FormatEnum (18), MediaTypeEnum (14 IANA), CompressionEnum |
| 6.b | Computationally Accessible | ✅ FULL | AccessMethod, DistributionMethod (7 types), API support |
| 6.c | Portable | ⚠️ PARTIAL | FormatEnum (cross-platform), Software (no ResourceRequirements) |
| 6.d | Contextualized | ✅ FULL | DataSplit, train_tuning_split, SamplingStrategy |

### Coverage Statistics

- **FULL Coverage**: 22/26 (85%)
- **PARTIAL Coverage**: 4/26 (15%)
- **MISSING Coverage**: 0/26 (0%)

**PARTIAL Criteria**:
1. 1.b Traceable (Provenance)
2. 2.b Statistics (Characterization)
3. 2.e Data Quality (Characterization)
4. 5.b Domain-appropriate (Sustainability)
5. 5.c Well-governed (Sustainability)
6. 6.c Portable (Computability)

---

## Module-to-Dimension Cross-Reference

| D4D Module | AI-Readiness Dimensions Addressed |
|------------|----------------------------------|
| **D4D_Base_import** | 0.a Findable, 0.b Accessible, 1.c Interpretable, 1.d Key Actors |
| **D4D_Motivation** | 1.d Key Actors (Grant, Grantor), 2.a Semantics |
| **D4D_Composition** | 1.a Transparent, 2.a Semantics, 2.b Statistics, 2.d Bias, 5.a Persistent, 5.d Associated |
| **D4D_Collection** | 1.a Transparent, 2.e Quality, 4.a Ethically Acquired, 6.d Contextualized |
| **D4D_Preprocessing** | 1.b Traceable, 1.c Interpretable, 2.e Quality |
| **D4D_Uses** | 2.d Bias (Limitation), 3.b Fit for Purpose, 6.d Contextualized |
| **D4D_Distribution** | 0.b Accessible, 0.d Reusable, 3.c Verifiable, 5.b Domain-appropriate, 6.a Standardized, 6.b Accessible, 6.c Portable |
| **D4D_Maintenance** | - (Future versions, updates - not directly mapped to 26 criteria) |
| **D4D_Ethics** | 4.a Ethically Acquired, 4.b Ethically Managed |
| **D4D_Human** | 4.a Ethically Acquired, 4.b Ethically Managed |
| **D4D_Data_Governance** | 0.d Reusable, 4.c Ethically Disseminated, 4.d Secure, 5.c Well-governed |
| **D4D_Variables** | 2.b Statistics, 2.c Standards |
| **D4D_Metadata** | 0.a Findable, 0.c Interoperable |

---

## Recommended Additions for 100% Coverage

To achieve **100% FULL coverage** of all 26 AI-readiness criteria, add the following 6 classes/enums:

| Addition | Addresses | Priority | Module |
|----------|-----------|----------|--------|
| `ProvenanceGraph` | 1.b Traceable | HIGH | D4D_Preprocessing |
| `StatisticalSummary` | 2.b Statistics | HIGH | D4D_Composition |
| `QualityControl` | 2.e Data Quality | HIGH | D4D_Preprocessing |
| `RepositoryTypeEnum` | 5.b Domain-appropriate | HIGH | D4D_Distribution |
| `RepositoryGovernance` | 5.c Well-governed | HIGH | D4D_Distribution |
| `ResourceRequirements` | 6.c Portable | HIGH | D4D_Composition/Uses |

For complete YAML specifications and integration details, see [D4D_AI_READINESS_GAP_ANALYSIS.md](../../D4D_AI_READINESS_GAP_ANALYSIS.md).

---

## References

1. **AI-Readiness Publication**: "AI-readiness for Biomedical Data: Bridge2AI Recommendations" (2024.10.23.619844v4.full.pdf), Table 1 (pages 10-12)
2. **D4D Gap Analysis**: [D4D_AI_READINESS_GAP_ANALYSIS.md](../../D4D_AI_READINESS_GAP_ANALYSIS.md)
3. **D4D Schema Evolution**: [D4D_SCHEMA_EVOLUTION_ANALYSIS.md](../../D4D_SCHEMA_EVOLUTION_ANALYSIS.md)
4. **Gebru et al. (2021)**: "Datasheets for Datasets", arXiv:1803.09010v8
5. **D4D Schema Files**: `src/data_sheets_schema/schema/`
6. **LinkML Documentation**: https://linkml.io/

---

**Document Metadata**:
- **Generated**: 2025-12-12
- **Format**: Markdown mapping table
- **Purpose**: Quick reference for D4D element to AI-readiness criterion mapping
- **Related**: D4D_AI_READINESS_GAP_ANALYSIS.md (comprehensive analysis)
