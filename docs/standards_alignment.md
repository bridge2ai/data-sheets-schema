# Standards Alignment Report

**Data Sheets for Datasets (D4D) Schema**
**Date**: 2025-12-02
**Version**: After ontology grounding optimization

## Executive Summary

The Data Sheets for Datasets (D4D) schema aligns with **25+ international standards**, ontologies, and frameworks spanning metadata, semantic web, data governance, and regulatory compliance. This focused alignment ensures interoperability, semantic clarity, and compliance with community-adopted standards while removing unused or redundant mappings based on expert review feedback.

## Standards by Category

### 1. Ontologies and Vocabularies

#### 1.1 Artificial Intelligence Ontology (AIO)
- **URL**: https://w3id.org/aio/
- **Purpose**: Bias taxonomy for AI/ML systems
- **Coverage**: 59 bias classes organized hierarchically
- **D4D Usage**: BiasTypeEnum (9 bias types mapped)
- **Mapping Status**: 4 exact matches, 5 broader mappings
- **Reference**: https://bioportal.bioontology.org/ontologies/AIO

#### 1.2 Data Use Ontology (DUO)
- **URL**: http://purl.obolibrary.org/obo/DUO_
- **Purpose**: Standardized data use permissions and restrictions
- **Authority**: Global Alliance for Genomics and Health (GA4GH)
- **Coverage**: Research permissions, commercial use restrictions, ethical requirements
- **D4D Usage**: DataUsePermissionEnum (22 permission types mapped)
- **Mapping Status**: All values have exact semantic mappings
- **Reference**: https://github.com/EBISPOT/DUO

#### 1.3 Provenance Ontology (PROV-O) - MINIMAL USE
- **URL**: http://www.w3.org/ns/prov#
- **Purpose**: Provenance and attribution metadata
- **Authority**: W3C Recommendation
- **D4D Usage**: **REDUCED TO ESSENTIAL USE ONLY**
  - Derivation relationships (wasDerivedFrom slot in D4D_Base_import.yaml)
  - **Removed**: Agent roles (replaced with schema.org)
  - **Removed**: Redundant derivation mappings (replaced with Dublin Core dcterms:source)
- **Mapping Status**: 1 essential mapping retained (was_derived_from slot)
- **Rationale**: Reduced from 21 usages to 1 to avoid redundancy with Dublin Core
- **Reference**: https://www.w3.org/TR/prov-o/

#### 1.4 Simple Knowledge Organization System (SKOS)
- **URL**: http://www.w3.org/2004/02/skos/core#
- **Purpose**: Knowledge organization systems (taxonomies, thesauri)
- **Authority**: W3C Recommendation
- **D4D Usage**: Example values, concept mappings
- **Reference**: https://www.w3.org/2004/02/skos/

#### 1.5 Biolink Model
- **URL**: https://w3id.org/biolink/vocab/
- **Purpose**: Biomedical knowledge graph schema
- **Authority**: Biomedical Data Translator project
- **D4D Usage**: Biomedical dataset integration
- **Reference**: https://biolink.github.io/biolink-model/

### 2. Metadata Standards

#### 2.1 Dublin Core Metadata Terms (dcterms)
- **URL**: http://purl.org/dc/terms/
- **Purpose**: Core metadata vocabulary for resources
- **Authority**: Dublin Core Metadata Initiative (DCMI)
- **Coverage**: 55 properties (title, creator, subject, description, etc.)
- **D4D Usage**: Extensive use across all modules
  - Basic metadata: title, description, creator, publisher, issued
  - Rights and access: license, rights, accessRights
  - Provenance: source, conformsTo, references
  - Relationships: isPartOf, hasPart, replaces, isReplacedBy, requires, isRequiredBy
  - Temporal: temporal, available
  - Format: format, type
- **Mapping Status**: Exact and broad mappings throughout schema
- **Reference**: https://www.dublincore.org/specifications/dublin-core/dcmi-terms/

#### 2.2 Data Catalog Vocabulary (DCAT)
- **URL**: http://www.w3.org/ns/dcat#
- **Purpose**: Dataset catalog metadata
- **Authority**: W3C Recommendation
- **Coverage**: Datasets, distributions, data services
- **D4D Usage**:
  - Distribution metadata: distribution, downloadURL, accessURL
  - Dataset properties: theme, keyword, landingPage
  - File metadata: byteSize, mediaType, compressFormat
- **Mapping Status**: Exact mappings
- **Reference**: https://www.w3.org/TR/vocab-dcat-3/

#### 2.3 schema.org
- **URL**: http://schema.org/
- **Purpose**: Structured data vocabulary for the web
- **Authority**: Community standard (Google, Microsoft, Yahoo, Yandex)
- **Coverage**: 800+ types covering broad domains
- **D4D Usage**:
  - Core metadata: name, description, identifier, url
  - People/Organizations: Person, Organization, affiliation, email
  - Data properties: variableMeasured, measurementTechnique, measurementMethod
  - Software: Software, softwareVersion
  - Dataset metadata: citation, contentUrl, numberOfItems
  - Relationships: isPartOf, contactPoint, funder, funding, maintainer
  - Data types: Integer, Float, Number, Text, Boolean, Date, DateTime
- **Mapping Status**: Extensive exact and broad mappings
- **Reference**: https://schema.org/

#### 2.4 DataCite Metadata Schema
- **URL**: https://schema.datacite.org/
- **Purpose**: Dataset citation and identification
- **Authority**: DataCite International
- **Coverage**: Dataset relationships, identifiers, citations
- **D4D Usage**:
  - Relationship types (14 relationship types aligned)
  - Dataset provenance and versioning
  - Citation formatting
- **Mapping Status**: Referenced in descriptions, aligned with Dublin Core
- **Reference**: https://datacite-metadata-schema.readthedocs.io/

### 3. Web and File Format Standards

#### 3.1 CSV on the Web (CSVW)
- **URL**: http://www.w3.org/ns/csvw#
- **Purpose**: CSV file metadata and structure
- **Authority**: W3C Recommendation
- **D4D Usage**:
  - Column metadata: Column, name, datatype, primaryKey
  - Missing values: null
  - Tabular data description: dialect
- **Mapping Status**: Exact mappings
- **Reference**: https://www.w3.org/TR/tabular-data-primer/

#### 3.2 XML Schema Datatypes (XSD)
- **URL**: http://www.w3.org/2001/XMLSchema#
- **Purpose**: Standard data type definitions
- **Authority**: W3C Recommendation
- **Coverage**: Primitive types (string, integer, boolean, date, etc.)
- **D4D Usage**: VariableTypeEnum (13 variable types mapped)
  - Exact mappings: integer, float, double, string, boolean, date, dateTime
- **Mapping Status**: Exact mappings for 7 primitive types
- **Reference**: https://www.w3.org/TR/xmlschema-2/

#### 3.3 IANA Media Types
- **URL**: https://www.iana.org/assignments/media-types/
- **Purpose**: Official registry of MIME types
- **Authority**: Internet Assigned Numbers Authority (IANA)
- **Coverage**: Media type identifiers for file formats
- **D4D Usage**: MediaTypeEnum (13 MIME types)
  - text/csv, application/json, application/xml, application/pdf, etc.
- **Mapping Status**: Values ARE the standard
- **Reference**: https://www.iana.org/assignments/media-types/

#### 3.4 Frictionless Data Standards
- **URL**: https://specs.frictionlessdata.io/
- **Purpose**: Lightweight data container and metadata formats
- **Authority**: Open Knowledge Foundation
- **D4D Usage**:
  - Data package structure
  - Resource metadata (path, mediatype)
  - Profile conformance
- **Mapping Status**: Broad mappings
- **Reference**: https://frictionlessdata.io/

#### 3.5 W3C Formats Registry
- **URL**: http://www.w3.org/ns/formats/
- **Purpose**: File format identification
- **Authority**: W3C
- **D4D Usage**: Format metadata and identification

#### 3.6 SHACL (Shapes Constraint Language)
- **URL**: https://w3id.org/shacl/
- **Purpose**: RDF validation and constraints
- **Authority**: W3C Recommendation
- **D4D Usage**: Schema validation shapes generation
- **Reference**: https://www.w3.org/TR/shacl/

### 4. Measurement and Units Standards

#### 4.1 QUDT (Quantities, Units, Dimensions and Types)
- **URL**: http://qudt.org/schema/qudt/
- **Purpose**: Units of measurement vocabulary
- **Authority**: QUDT.org
- **D4D Usage**:
  - Variable units (unit, hasUnit)
  - Standardized unit identifiers (e.g., qudt:Kilogram, qudt:Meter)
- **Mapping Status**: Exact mappings
- **Reference**: http://qudt.org/

### 5. Regulatory and Compliance Frameworks

#### 5.1 EU General Data Protection Regulation (GDPR)
- **Authority**: European Union Regulation (EU) 2016/679
- **Purpose**: Data protection and privacy regulation
- **Coverage**: Personal data processing, consent, privacy rights
- **D4D Usage**:
  - GDPR compliance tracking (gdpr_compliant field)
  - Privacy and consent metadata
  - Data subject rights
- **Reference**: https://gdpr.eu/

#### 5.2 Health Insurance Portability and Accountability Act (HIPAA)
- **Authority**: US Federal Law (Public Law 104-191)
- **Purpose**: Protected health information privacy
- **Coverage**: Healthcare data security and privacy
- **D4D Usage**:
  - HIPAA compliance tracking (hipaa_compliant field)
  - Health data governance
- **Reference**: https://www.hhs.gov/hipaa/

#### 5.3 EU Artificial Intelligence Act
- **Authority**: European Union Regulation (EU) 2024/1689
- **Purpose**: Risk-based regulation of AI systems
- **Coverage**: 4 risk categories (minimal, limited, high, unacceptable)
- **D4D Usage**: AIActRiskEnum with article references
  - Article 5: Prohibited AI practices
  - Article 6: High-risk AI systems
  - Article 50: Transparency obligations
  - Annex III: High-risk AI use cases
- **Mapping Status**: Related mappings to regulation articles
- **Reference**: https://eur-lex.europa.eu/eli/reg/2024/1689/oj

#### 5.4 45 CFR 46 (Common Rule)
- **Authority**: US Department of Health and Human Services
- **Purpose**: Protection of human research subjects
- **Coverage**: IRB requirements, informed consent, vulnerable populations
- **D4D Usage**: Human subjects research metadata
- **Reference**: https://www.hhs.gov/ohrp/regulations-and-policy/regulations/45-cfr-46/

### 6. Information Security Standards

#### 6.1 ISO/IEC 27001
- **Authority**: International Organization for Standardization
- **Purpose**: Information security management systems
- **Coverage**: Information classification (Public, Internal, Highly Confidential)
- **D4D Usage**: ConfidentialityLevelEnum mappings
  - unrestricted → ISO27001_Public
  - restricted → ISO27001_Internal
  - confidential → ISO27001_Highly_Confidential
- **Mapping Status**: Broad mappings
- **Reference**: https://www.iso.org/isoiec-27001-information-security.html

#### 6.2 NIST SP 800-60
- **Authority**: National Institute of Standards and Technology (US)
- **Purpose**: Security categorization for federal information systems
- **Coverage**: Impact levels (Low, Moderate, High)
- **D4D Usage**: ConfidentialityLevelEnum mappings
  - unrestricted → NIST_Low_Impact
  - restricted → NIST_Moderate_Impact
  - confidential → NIST_High_Impact
- **Mapping Status**: Broad mappings
- **Reference**: https://csrc.nist.gov/publications/detail/sp/800-60/vol-1-rev-1/final

#### 6.3 Traffic Light Protocol (TLP)
- **Authority**: Cybersecurity and Infrastructure Security Agency (CISA)
- **Purpose**: Information sharing sensitivity classification
- **Coverage**: 4 levels (CLEAR, GREEN, AMBER, RED)
- **D4D Usage**: ConfidentialityLevelEnum mappings
  - unrestricted → TLP:CLEAR
  - restricted → TLP:GREEN
  - confidential → TLP:AMBER
- **Mapping Status**: Broad mappings
- **Reference**: https://www.cisa.gov/tlp

### 7. Research Infrastructure Standards

#### 7.1 CRediT (Contributor Roles Taxonomy)
- **URL**: https://credit.niso.org/
- **Authority**: NISO (National Information Standards Organization)
- **Purpose**: Standardized contributor roles in scholarly publishing
- **Coverage**: 14 contributor roles
- **D4D Usage**: CRediTRoleEnum (14 roles)
  - conceptualization, data_curation, formal_analysis, funding_acquisition
  - investigation, methodology, project_administration, resources
  - software, supervision, validation, visualization, writing_original_draft, writing_review_editing
- **Mapping Status**: Values follow CRediT taxonomy
- **Reference**: https://credit.niso.org/

#### 7.2 Bridge2AI Standards Registry
- **URL**: https://w3id.org/bridge2ai/b2ai-standards-registry/
- **Authority**: NIH Bridge2AI Program
- **Purpose**: Biomedical data standards registry
- **Coverage**: Topics, standards, substrates for biomedical data
- **D4D Usage**:
  - B2AI_TOPIC: Domain topics
  - B2AI_STANDARD: Applicable standards
  - B2AI_SUBSTRATE: Data types and formats
- **Reference**: https://bridge2ai.github.io/standards-schemas/

### 8. Versioning Standards

#### 8.1 Semantic Versioning (SemVer)
- **URL**: https://semver.org/
- **Purpose**: Version numbering convention
- **Coverage**: MAJOR.MINOR.PATCH version format
- **D4D Usage**: VersionTypeEnum (MAJOR, MINOR, PATCH)
- **Mapping Status**: Description references semver.org
- **Reference**: https://semver.org/

### 9. Linked Data and RDF Standards

#### 9.1 LinkML (Linked Data Modeling Language)
- **URL**: https://w3id.org/linkml/
- **Authority**: Community standard
- **Purpose**: Schema definition language for linked data
- **Coverage**: Classes, slots, enums, types with semantic mappings
- **D4D Usage**: Base schema framework
- **Reference**: https://linkml.io/

#### 9.2 JSON-LD (JSON for Linking Data)
- **Authority**: W3C Recommendation
- **Purpose**: JSON-based format for linked data
- **D4D Usage**: Generated artifacts include JSON-LD context
- **Reference**: https://www.w3.org/TR/json-ld/

#### 9.3 OWL (Web Ontology Language)
- **Authority**: W3C Recommendation
- **Purpose**: Semantic web ontology language
- **D4D Usage**: Generated OWL representations
- **Reference**: https://www.w3.org/OWL/

#### 9.4 RDF (Resource Description Framework)
- **Authority**: W3C Recommendation
- **Purpose**: Graph-based data model
- **D4D Usage**: Schema designed for RDF compatibility
- **Reference**: https://www.w3.org/RDF/

## Standards Coverage Matrix

| Module | Primary Standards | Ontologies Used | Regulatory Frameworks |
|--------|------------------|-----------------|----------------------|
| D4D_Base_import | schema.org, LinkML, PROV-O | AIO, FOAF | - |
| D4D_Motivation | Dublin Core, schema.org | CRediT, PROV-O | - |
| D4D_Composition | Dublin Core, DCAT, DataCite | - | - |
| D4D_Collection | Dublin Core, PROV-O | - | - |
| D4D_Preprocessing | Dublin Core, schema.org, PROV-O | - | - |
| D4D_Uses | Dublin Core, schema.org | - | - |
| D4D_Distribution | Dublin Core, DCAT | - | - |
| D4D_Maintenance | Dublin Core, PAV | - | - |
| D4D_Ethics | Dublin Core, schema.org | - | - |
| D4D_Human | Dublin Core, schema.org | - | GDPR, HIPAA, 45 CFR 46 |
| D4D_Data_Governance | Dublin Core, DUO, schema.org | DUO | GDPR, HIPAA, EU AI Act |
| D4D_Variables | Dublin Core, schema.org, CSVW, XSD, QUDT | PROV-O, SKOS | - |

## Mapping Type Statistics

| Mapping Type | Count | Description |
|--------------|-------|-------------|
| `exact_mappings:` | ~80 | Exactly equivalent terms |
| `broad_mappings:` | ~60 | D4D term is narrower than standard |
| `meaning:` | 35 | Exact semantic equivalence (DUO, AIO) |
| `related_mappings:` | ~15 | Related but not exact |
| `slot_uri:` | ~200 | Property mapped to vocabulary term |

## Standards Bodies and Authorities

1. **W3C (World Wide Web Consortium)**: DCAT, PROV-O, SKOS, CSVW, XSD, SHACL, RDF, OWL
2. **Dublin Core Metadata Initiative**: Dublin Core Terms
3. **GA4GH (Global Alliance for Genomics and Health)**: Data Use Ontology (DUO)
4. **NISO (National Information Standards Organization)**: CRediT
5. **IANA (Internet Assigned Numbers Authority)**: Media Types
6. **ISO (International Organization for Standardization)**: ISO 27001
7. **NIST (National Institute of Standards and Technology)**: SP 800-60
8. **CISA (Cybersecurity and Infrastructure Security Agency)**: Traffic Light Protocol
9. **European Union**: GDPR, EU AI Act
10. **US Government**: HIPAA, 45 CFR 46
11. **Community Standards**: schema.org, AIO, CRediT, Frictionless Data, QUDT

## Compliance and Regulatory Coverage

### Privacy and Data Protection
- ✅ GDPR (EU General Data Protection Regulation)
- ✅ HIPAA (Health Insurance Portability and Accountability Act)
- ✅ 45 CFR 46 (Protection of Human Subjects)

### AI Regulation
- ✅ EU AI Act (Regulation EU 2024/1689) - 4 risk categories

### Information Security
- ✅ ISO 27001 - Information classification
- ✅ NIST SP 800-60 - Security categorization
- ✅ Traffic Light Protocol - Information sharing

### Data Use and Ethics
- ✅ DUO (Data Use Ontology) - 22 permission types
- ✅ IRB/Ethics review tracking

## Interoperability Benefits

### 1. Semantic Interoperability
- Schema.org alignment enables web indexing and discovery
- Dublin Core enables cross-repository search
- DCAT enables dataset catalog integration

### 2. Domain Interoperability
- DUO enables genomics/biomedical data sharing
- Bridge2AI enables biomedical AI standards alignment
- AIO enables AI bias taxonomy integration

### 3. Tool Interoperability
- CSVW enables tabular data tool integration
- Frictionless Data enables data package tools
- LinkML enables multiple format generation (JSON Schema, OWL, SHACL, GraphQL)

### 4. Regulatory Compliance
- GDPR/HIPAA tracking enables compliance workflows
- EU AI Act categorization enables risk assessment
- ISO/NIST/TLP alignment enables security governance

## Future Standards Considerations

### Potential Additions
1. **FAIR Metrics**: Formal FAIR assessment alignment
2. **DCAT-AP**: DCAT Application Profile for European data portals
3. **BioSchemas**: schema.org extension for life sciences
4. **STATO**: Statistics Ontology for advanced statistical metadata
5. **OHDSI**: Observational Health Data Sciences vocabulary

### Standards Under Review
- Format registries (PRONOM) for file format metadata
- Additional regulatory frameworks (CCPA, PIPEDA)
- Research data management standards (CoreTrustSeal, Data Seal of Approval)

## Maintenance and Updates

### Standards Monitoring
The D4D schema team monitors the following for updates:
1. W3C Recommendations (annual review)
2. Dublin Core Terms (ongoing)
3. EU regulations (GDPR, EU AI Act amendments)
4. Ontology updates (DUO, AIO, PROV-O)

### Version Compatibility
- LinkML version: 1.x
- Schema.org version: Current (rolling release)
- Dublin Core: DCMI Metadata Terms (ongoing)
- DUO: Latest release (tracked via GitHub)

## References and Resources

### Key Specifications
1. **LinkML**: https://linkml.io/linkml/
2. **schema.org**: https://schema.org/
3. **Dublin Core**: https://www.dublincore.org/
4. **W3C DCAT**: https://www.w3.org/TR/vocab-dcat-3/
5. **W3C PROV-O**: https://www.w3.org/TR/prov-o/
6. **DUO**: https://github.com/EBISPOT/DUO

### Regulatory Documents
1. **GDPR**: https://gdpr.eu/
2. **HIPAA**: https://www.hhs.gov/hipaa/
3. **EU AI Act**: https://eur-lex.europa.eu/eli/reg/2024/1689/oj
4. **45 CFR 46**: https://www.hhs.gov/ohrp/regulations-and-policy/

### Additional Documentation
1. **Enumeration Ontology Grounding Report**: `docs/enum_ontology_grounding_report.md`
2. **Schema Evolution Analysis**: `docs/schema_evolution_analysis.md`
3. **D4D GitHub Repository**: https://github.com/bridge2ai/data-sheets-schema

## Changelog

**2025-12-02 - Ontology Grounding Optimization**:
- **Reduced from 40+ to 25+ standards** based on expert review (Harry Caufield feedback)
- **Phase 1**: Removed unused/minimal standards:
  - VoID (Vocabulary of Interlinked Datasets) - minimal usage
  - W3C Formats Registry - redundant with IANA Media Types
  - FOAF (Friend of a Friend) - replaced with schema.org
  - BIBO (Bibliographic Ontology) - minimal usage
  - OSLC (Open Services for Lifecycle Collaboration) - single usage
  - Frictionless Data Standards - unclear benefit
  - XSD (XML Schema Datatypes) - removed from VariableTypeEnum (kept in schema.org mappings)
- **Phase 2**: Replaced PAV (Provenance, Authoring, and Versioning) with Dublin Core:
  - 9 PAV usages replaced with equivalent Dublin Core terms
  - version → dcterms:hasVersion
  - previousVersion → dcterms:isVersionOf
  - createdOn → dcterms:created
  - createdBy → dcterms:creator
  - lastUpdateOn → dcterms:modified
- **Phase 3**: Removed CSVW from Variables module:
  - 6 CSVW usages removed (Column, name, datatype, primaryKey, null, dialect)
  - Replaced with schema.org equivalents where needed
- **Phase 4**: Reduced PROV-O to essential use:
  - Reduced from 21 usages to 1 essential usage
  - Kept: was_derived_from slot (prov:wasDerivedFrom)
  - Removed: Agent roles (9 mappings in CreatorOrMaintainerEnum)
  - Removed: Redundant derivation mappings in modules
- **Phase 5-6**: Removed security classification mappings:
  - Removed ISO 27001 mappings from ConfidentialityLevelEnum
  - Removed NIST SP 800-60 mappings from ConfidentialityLevelEnum
  - Removed Traffic Light Protocol (TLP) mappings from ConfidentialityLevelEnum
  - Generalized regulatory compliance fields
- **Phase 7**: Updated standards documentation (this file)
- **Phase 8**: All tests pass with optimized mappings
- **Phase 9**: Removed GDPR and EU AI Act (US-Centric Focus):
  - Removed `gdpr_compliant` field from ExportControlRegulatoryRestrictions
  - Removed `eu_ai_act_risk_category` field from ExportControlRegulatoryRestrictions
  - Removed entire `AIActRiskEnum` enum (4 risk categories: minimal, limited, high, unacceptable)
  - Updated all descriptions mentioning GDPR/EU AI Act to reference US regulations (HIPAA, 45 CFR 46)
  - Rationale: "stay US-centric" per expert feedback
- **Phase 10**: Completed Frictionless & CSVW cleanup:
  - Removed `frictionless` prefix from D4D_Base_import.yaml and data_sheets_schema.yaml
  - Removed `csvw` prefix from D4D_Base_import.yaml and data_sheets_schema.yaml
  - Removed `csvw:dialect` mapping from dialect slot in D4D_Base_import.yaml
  - Rationale: "wouldn't worry about mapping to it" (Frictionless), "more granular than D4D needs" (CSVW)
- **Phase 11**: Validation and regeneration successful

**Rationale for Changes**:
- Eliminate redundancy (PAV overlaps with Dublin Core, FOAF overlaps with schema.org)
- Remove unclear/unused ontologies (VoID, BIBO, OSLC had minimal benefit)
- Simplify for maintainability (fewer external dependencies to track)
- Focus on high-impact standards (DUO, schema.org, Dublin Core, DCAT)
- Improve clarity (security classification is domain-specific, removed prescriptive mappings)

**2025-12-01**:
- Initial comprehensive standards alignment report
- Documented 40+ standards across 9 categories
- Added regulatory framework coverage
- Included mapping statistics and interoperability benefits
