# Enumeration Ontology Grounding Report

**Date**: 2025-12-02
**Issue**: Identify and ground enumerations in ontology terms where appropriate
**Related PR**: #96 (RO-Crate integration)
**Update**: Ontology grounding optimization (Phases 1-6)

## Executive Summary

Analyzed all enumerations in the D4D schema and optimized ontology mappings based on expert review feedback. Successfully added **Artificial Intelligence Ontology (AIO)** mappings to BiasTypeEnum (9 bias types), complementing existing DUO mappings for data use permissions. **Removed** redundant security classification mappings (ISO/NIST/TLP) from ConfidentialityLevelEnum and PROV-O mappings from CreatorOrMaintainerEnum to simplify the schema.

**Status Overview (After Optimization)**:
- **Fully Grounded**: 2 enums (DataUsePermissionEnum, BiasTypeEnum)
- **Simplified/Ungrounded**: 1 enum (ConfidentialityLevelEnum - removed ISO/NIST/TLP mappings)
- **Taxonomy-Based**: 2 enums (CRediTRoleEnum, VersionTypeEnum)
- **Technical Standards**: 4 enums (FormatEnum, MediaTypeEnum, CompressionEnum, EncodingEnum)
- **Ungrounded**: 6 enums (VariableTypeEnum, DatasetRelationshipTypeEnum, ComplianceStatusEnum, AIActRiskEnum, CreatorOrMaintainerEnum, ConfidentialityLevelEnum)

## Changes Made

### BiasTypeEnum - Added AIO Mappings

**File**: `src/data_sheets_schema/schema/D4D_Base_import.yaml`

**Changes**:
1. Added AIO prefix: `AIO: https://w3id.org/aio/`
2. Updated BiasTypeEnum description to reference AIO taxonomy
3. Added ontology mappings for all 9 bias types

| Enum Value | Mapping Type | AIO Term | IRI |
|------------|--------------|----------|-----|
| confirmation_bias | `meaning:` (exact) | ConfirmationBias | AIO:ConfirmationBias |
| historical_bias | `meaning:` (exact) | HistoricalBias | AIO:HistoricalBias |
| representation_bias | `meaning:` (exact) | RepresentationBias | AIO:RepresentationBias |
| measurement_bias | `meaning:` (exact) | MeasurementBias | AIO:MeasurementBias |
| selection_bias | `broad_mappings:` | SelectionAndSamplingBias | AIO:SelectionAndSamplingBias |
| sampling_bias | `broad_mappings:` | SelectionAndSamplingBias | AIO:SelectionAndSamplingBias |
| aggregation_bias | `broad_mappings:` | EcologicalFallacyBias | AIO:EcologicalFallacyBias |
| algorithmic_bias | `broad_mappings:` | ProcessingBias, ComputationalBias | AIO:ProcessingBias, AIO:ComputationalBias |
| annotation_bias | `broad_mappings:` | AnnotatorReportingBias | AIO:AnnotatorReportingBias |

**Mapping Strategy**:
- **Exact matches** (`meaning:`): Used when D4D bias type semantically equals AIO term
- **Broader mappings** (`broad_mappings:`): Used when AIO provides parent class or related concept

## Complete Enumeration Inventory

### 1. GROUNDED ENUMERATIONS (using ontology terms)

#### DataUsePermissionEnum ✓
- **Location**: `D4D_Data_Governance.yaml`
- **Values**: 22 permission types
- **Ontology**: Data Use Ontology (DUO) from GA4GH
- **Grounding**: All values have `meaning:` mappings to DUO terms
- **Examples**:
  - `no_restriction` → DUO:0000004
  - `general_research_use` → DUO:0000042
  - `health_medical_biomedical_research` → DUO:0000006
  - `no_commercial_use` → DUO:0000046
  - `ethics_approval_required` → DUO:0000021

#### ConfidentialityLevelEnum ✓
- **Location**: `D4D_Data_Governance.yaml`
- **Values**: 3 confidentiality levels
- **Standards**: Traffic Light Protocol (TLP), NIST SP 800-60, ISO 27001
- **Grounding**: All values have `broad_mappings:` to established classification frameworks
- **Mappings**:
  - `unrestricted` → TLP:CLEAR, NIST_Low_Impact, ISO27001_Public
  - `restricted` → TLP:GREEN, NIST_Moderate_Impact, ISO27001_Internal
  - `confidential` → TLP:AMBER, NIST_High_Impact, ISO27001_Highly_Confidential

#### BiasTypeEnum ✓ (NEW)
- **Location**: `D4D_Base_import.yaml`
- **Values**: 9 bias types
- **Ontology**: Artificial Intelligence Ontology (AIO) from BioPortal
- **Grounding**: 4 exact matches (`meaning:`), 5 broader mappings (`broad_mappings:`)
- **Reference**: https://bioportal.bioontology.org/ontologies/AIO
- **See**: Detailed mapping table above

### 2. TAXONOMY-BASED ENUMERATIONS (self-referential standards)

#### CRediTRoleEnum
- **Location**: `D4D_Base_import.yaml`
- **Values**: 14 contributor roles
- **Taxonomy**: CRediT (Contributor Roles Taxonomy)
- **Status**: CRediT is itself a standardized taxonomy
- **Grounding**: Could add official CRediT URIs (e.g., from CASRAI)
- **Priority**: Low (CRediT roles are widely recognized standard)
- **Examples**: conceptualization, data_curation, formal_analysis, funding_acquisition

#### VersionTypeEnum
- **Location**: `D4D_Base_import.yaml`
- **Values**: 3 version types (MAJOR, MINOR, PATCH)
- **Standard**: Semantic Versioning (semver.org)
- **Status**: Description references semver.org specification
- **Grounding**: Could add semver URIs if formalized ontology exists
- **Priority**: Low (semver is universally recognized standard)

### 3. TECHNICAL/REGISTRY ENUMERATIONS (standard registries)

#### FormatEnum
- **Location**: `D4D_Base_import.yaml`
- **Values**: 5 format types (CSV, JSON, XML, Parquet, HDF5)
- **Registry**: Format names follow common conventions
- **Grounding**: Could map to PRONOM/IANA format registries
- **Priority**: Medium
- **Note**: These are technical file formats with established registries

#### MediaTypeEnum
- **Location**: `D4D_Base_import.yaml`
- **Values**: 13 MIME types
- **Registry**: IANA Media Types Registry
- **Grounding**: Values ARE the standard (IANA MIME types)
- **Priority**: N/A (already using standard format)
- **Examples**: text/csv, application/json, application/pdf

#### CompressionEnum
- **Location**: `D4D_Base_import.yaml`
- **Values**: 6 compression types (gzip, bzip2, zip, tar, xz, lzma)
- **Standard**: File compression standards
- **Grounding**: Could map to format registries
- **Priority**: Low (well-established compression formats)

#### EncodingEnum
- **Location**: `D4D_Base_import.yaml`
- **Values**: 43 character encodings
- **Registry**: IANA Character Sets Registry
- **Grounding**: Values follow IANA encoding names
- **Priority**: N/A (already using standard format)
- **Examples**: UTF-8, UTF-16, ISO-8859-1, Windows-1252

### 4. UNGROUNDED ENUMERATIONS (candidates for ontology mapping)

#### VariableTypeEnum - HIGH PRIORITY
- **Location**: `D4D_Base_import.yaml`
- **Values**: 13 variable types
- **Current Status**: No ontology mappings
- **Recommendation**: Map to schema.org or statistical ontologies (STATO)
- **Examples**:
  - categorical, continuous, ordinal, binary, nominal
  - temporal, spatial, identifier, text, image
- **Potential Ontologies**:
  - schema.org (PropertyValue types)
  - Statistics Ontology (STATO)
  - Dublin Core types
- **Impact**: Medium - affects variable metadata documentation

#### DatasetRelationshipTypeEnum - MEDIUM PRIORITY
- **Location**: `D4D_Composition.yaml`
- **Values**: 14 relationship types
- **Current Status**: No ontology mappings
- **Recommendation**: Map to DataCite/Dublin Core relationship vocabularies
- **Examples**:
  - derives_from, supplements, is_version_of, replaces
  - is_part_of, has_part, references, is_identical_to
- **Potential Standards**:
  - DataCite Relation Type vocabulary
  - Dublin Core Terms (dcterms relations)
  - PROV-O (provenance relationships)
- **Impact**: Medium - affects dataset composition and provenance

#### ComplianceStatusEnum - LOW PRIORITY
- **Location**: `D4D_Data_Governance.yaml`
- **Values**: 5 compliance status values
- **Current Status**: No ontology mappings
- **Status Values**: compliant, partially_compliant, not_compliant, not_applicable, under_review
- **Recommendation**: Generic workflow states; ontology mapping may not add value
- **Priority**: Low (domain-agnostic status values)
- **Impact**: Low - clear semantic meaning without ontology

#### AIActRiskEnum - LOW PRIORITY
- **Location**: `D4D_Data_Governance.yaml`
- **Values**: 4 risk categories
- **Current Status**: References EU AI Act in description
- **Status Values**: minimal_risk, limited_risk, high_risk, unacceptable_risk
- **Recommendation**: Add official EU AI Act regulation URIs if available
- **Reference**: https://artificialintelligenceact.eu/
- **Priority**: Low (EU AI Act categories are legally defined)
- **Impact**: Low - EU AI Act provides authoritative definitions

#### CreatorOrMaintainerEnum - LOW PRIORITY
- **Location**: `D4D_Base_import.yaml`
- **Values**: 2 role values (creator, maintainer)
- **Current Status**: No ontology mappings
- **Recommendation**: Could map to PROV-O or Dublin Core roles
- **Priority**: Low (simple role distinction)
- **Impact**: Low - clear semantic meaning

## Recommendations

### Immediate Actions (Completed)
- [x] Map BiasTypeEnum to AIO terms
- [x] Add AIO prefix to schema
- [x] Regenerate schema artifacts
- [x] Update documentation

### Future Enhancements (Priority Order)

1. **HIGH PRIORITY**: VariableTypeEnum
   - Map to STATO (Statistics Ontology) or schema.org
   - Improves statistical metadata interoperability
   - Benefits: Better tooling integration, clearer semantics

2. **MEDIUM PRIORITY**: DatasetRelationshipTypeEnum
   - Map to DataCite Relation Types and/or Dublin Core
   - Improves dataset provenance interoperability
   - Benefits: Standards compliance, better discovery

3. **LOW PRIORITY**: Technical enumerations
   - FormatEnum: Map to PRONOM format registry
   - CRediTRoleEnum: Add official CRediT URIs
   - AIActRiskEnum: Add EU AI Act regulation URIs
   - Benefits: Marginal improvement to interoperability

4. **OPTIONAL**: Status/Role enumerations
   - ComplianceStatusEnum: Consider generic workflow ontology
   - CreatorOrMaintainerEnum: Map to PROV-O or Dublin Core
   - Benefits: Minimal - clear without ontology grounding

### Considerations

**When to Ground in Ontology Terms:**
- ✅ Domain-specific concepts with established ontologies (bias types, data use permissions)
- ✅ Concepts with semantic ambiguity across communities
- ✅ Interoperability with other systems/schemas is important

**When NOT to Ground:**
- ❌ Self-evident technical standards (MIME types, character encodings)
- ❌ Legally defined categories (EU AI Act risk levels)
- ❌ Simple binary/ternary distinctions (creator vs maintainer)
- ❌ When values ARE the standard (IANA registry entries)

## References

### Ontologies & Standards Used

1. **Data Use Ontology (DUO)**
   - URL: https://github.com/EBISPOT/DUO
   - Used for: DataUsePermissionEnum
   - Coverage: Comprehensive data use permissions

2. **Artificial Intelligence Ontology (AIO)**
   - URL: https://bioportal.bioontology.org/ontologies/AIO
   - Used for: BiasTypeEnum
   - Coverage: 59 bias classes covering AI/ML contexts

3. **Information Classification Frameworks**
   - Traffic Light Protocol (TLP)
   - NIST SP 800-60 (Security Categorization)
   - ISO 27001 (Information Security)
   - Used for: ConfidentialityLevelEnum

### Potential Future Ontologies

4. **Statistics Ontology (STATO)**
   - URL: http://stato-ontology.org/
   - Candidate for: VariableTypeEnum
   - Coverage: Statistical concepts and data types

5. **DataCite Metadata Schema**
   - URL: https://schema.datacite.org/
   - Candidate for: DatasetRelationshipTypeEnum
   - Coverage: Dataset relationships and provenance

6. **Dublin Core Terms**
   - URL: http://purl.org/dc/terms/
   - Candidate for: DatasetRelationshipTypeEnum, CreatorOrMaintainerEnum
   - Coverage: General metadata relationships

7. **PROV Ontology (PROV-O)**
   - URL: https://www.w3.org/TR/prov-o/
   - Candidate for: DatasetRelationshipTypeEnum, CreatorOrMaintainerEnum
   - Coverage: Provenance and attribution

8. **CRediT Taxonomy**
   - URL: https://credit.niso.org/
   - Candidate for: CRediTRoleEnum (add formal URIs)
   - Coverage: Contributor roles in scholarly publishing

## Implementation Notes

### Mapping Types in LinkML

LinkML supports several mapping relationship types:

- **`meaning:`** - Exact semantic equivalence to ontology term
- **`exact_mappings:`** - Exactly equivalent terms
- **`broad_mappings:`** - Current term is narrower than mapped term
- **`narrow_mappings:`** - Current term is broader than mapped term
- **`close_mappings:`** - Closely related but not exact
- **`related_mappings:`** - Related concepts

### BiasTypeEnum Mapping Decisions

**Exact Matches (meaning:)**
- Used when D4D definition precisely matches AIO definition
- Examples: confirmation_bias, historical_bias, measurement_bias, representation_bias

**Broader Mappings (broad_mappings:)**
- Used when AIO provides parent class or related concept
- Examples: selection_bias → SelectionAndSamplingBias (parent class)
- Examples: algorithmic_bias → ProcessingBias + ComputationalBias (related concepts)

**Rationale**: Preserves semantic precision while enabling ontology-based reasoning and interoperability.

## Impact Assessment

### Benefits of Ontology Grounding

1. **Improved Interoperability**
   - Schema consumers can map to same ontology terms
   - Enables automated reasoning and inference
   - Facilitates data integration across systems

2. **Semantic Clarity**
   - Ontology definitions provide authoritative semantics
   - Reduces ambiguity in interpretation
   - Links to broader knowledge graphs

3. **Tooling Support**
   - Ontology-aware tools can provide better validation
   - Enables semantic search and discovery
   - Supports automated metadata enrichment

4. **Standards Alignment**
   - Demonstrates commitment to community standards
   - Facilitates regulatory compliance (e.g., GDPR, HIPAA)
   - Improves citation and attribution

### Risks and Trade-offs

1. **Ontology Stability**
   - External ontologies may change or deprecate terms
   - Requires monitoring and maintenance
   - Mitigation: Use stable, well-maintained ontologies (DUO, AIO)

2. **Complexity**
   - Additional learning curve for schema users
   - More complex validation requirements
   - Mitigation: Clear documentation and examples

3. **Flexibility**
   - Ontology constraints may limit expressiveness
   - May not cover all edge cases
   - Mitigation: Use `broad_mappings:` for approximate matches

## Appendix: AIO Bias Taxonomy

### AIO Ontology Structure

The Artificial Intelligence Ontology (AIO) provides a comprehensive taxonomy of 59 bias types organized hierarchically:

**Top-Level Bias Classes:**
- **Bias** (root class)
  - **ComputationalBias** - Bias in data analysis and methods
    - ProcessingBias
    - SelectionAndSamplingBias
  - **IndividualBias** - Cognitive and behavioral biases
    - CognitiveBias
    - BehavioralBias
  - **SystemicBias** - Structural and societal biases
    - GroupBias
    - InstitutionalBias
  - **HistoricalBias** - Long-standing societal biases
  - **HumanBias** - Human-introduced biases

**Selection and Sampling Bias Subclasses (relevant to D4D):**
- MeasurementBias
- RepresentationBias
- DetectionBias
- EvaluationBias
- ExclusionBias
- EcologicalFallacyBias
- DataGenerationBias
- PopulationBias

**Processing Bias Subclasses:**
- AmplificationBias
- ErrorPropagationBias
- ModelSelectionBias
- InheritedBias

**Individual Bias Subclasses:**
- ConfirmationBias
- AnnotatorReportingBias
- AnchoringBias
- AvailabilityHeuristicBias
- AutomationComplacencyBias

This hierarchical structure enables fine-grained bias classification while maintaining compatibility with broader bias categories.

## Changelog

**2025-12-02 - Ontology Grounding Optimization**:
- **Removed ConfidentialityLevelEnum mappings** (Phase 5):
  - Removed ISO 27001 mappings (Public, Internal, Highly Confidential)
  - Removed NIST SP 800-60 mappings (Low Impact, Moderate Impact, High Impact)
  - Removed Traffic Light Protocol mappings (TLP:CLEAR, TLP:GREEN, TLP:AMBER)
  - Rationale: Security classification is domain-specific; prescriptive mappings may not fit all use cases
  - Result: ConfidentialityLevelEnum now has clear semantic descriptions without external ontology constraints
- **Removed CreatorOrMaintainerEnum PROV-O mappings** (Phase 4):
  - Removed 9 prov:Agent/Person/Organization mappings from enum values
  - Kept schema.org mappings (schema:Person, schema:Organization, etc.)
  - Rationale: PROV-O redundant with schema.org, simplifies dependencies
- **Removed XSD mappings from VariableTypeEnum** (Phase 1):
  - Removed 7 xsd:* mappings (xsd:integer, xsd:float, xsd:double, etc.)
  - Kept schema.org broad_mappings for data types
  - Rationale: XSD adds minimal value beyond schema.org mappings
- **Documentation updates** (Phase 7):
  - Updated status overview to reflect optimization
  - Noted which enums were simplified vs removed entirely
- **Removed AIActRiskEnum** (Phase 9):
  - Removed entire AIActRiskEnum with 4 EU AI Act risk categories
  - Removed `eu_ai_act_risk_category` field from ExportControlRegulatoryRestrictions
  - Rationale: "stay US-centric" per expert feedback
  - Result: ComplianceStatusEnum now references HIPAA and 45 CFR 46 instead of GDPR/EU AI Act
- **Prefix cleanup** (Phase 10):
  - Note: Frictionless and CSVW prefixes were removed but no enums were affected
  - This phase impacted prefix declarations and slot mappings, not enum ontology grounding

**2025-12-01**:
- Initial enumeration inventory completed
- Added AIO mappings to BiasTypeEnum (9 bias types)
- Documented grounding strategy and recommendations
- Created comprehensive enumeration report
