# Croissant RAI Properties Gap Analysis
## Bridge2AI D4D Schema Compliance Review

**Report Date**: December 17, 2025
**Issue Reference**: [#105 - Update Croissant RAI Properties in Bridge2AI D4Ds](https://github.com/bridge2ai/data-sheets-schema/issues/105)
**Author**: Mónica Muñoz Torres (@monicacecilia)
**Analysis**: Claude Code (Sonnet 4.5)

---

## Executive Summary

Bridge2AI's Datasheets for Datasets (D4D) schema has **incomplete and partially incorrect** implementation of MLCommons' Croissant Responsible AI (RAI) specification. This gap analysis reveals:

### Key Findings

- **Coverage**: 14 of 20 properties implemented (70% coverage)
- **Missing**: 6 critical properties absent (30% gap)
- **Naming Issues**: 3 properties incorrectly named
- **Documentation Error**: D4D claims 24 properties, but official spec defines only 20

### Impact

- **Standards Compliance**: Moderate compliance with Croissant RAI specification
- **Interoperability**: Limited compatibility with Croissant-compliant systems
- **Transparency**: Gaps in data lifecycle and annotation process documentation

### Required Actions

1. **Immediate**: Fix 3 naming mismatches
2. **High Priority**: Add 6 missing properties
3. **Medium Priority**: Add explicit `exact_mappings` to Croissant RAI URIs
4. **Long-term**: Establish governance process for maintaining Croissant RAI alignment

---

## 1. Issue Background

### Problem Statement

From issue #105 (opened 2025-12-16):

> The information about our implementation of the Croissant Responsible AI specification in Bridge2AI Datasheets for Datasets is **incomplete**, and three of the properties that we did include are **incorrectly named**.

### Specific Problems

1. **Incorrect Documentation**: D4D documentation states 24 Croissant RAI properties exist, but [MLCommons spec](https://docs.mlcommons.org/croissant/docs/croissant-rai-spec.html) defines only **20 properties**

2. **Incomplete Implementation**: Bridge2AI D4D implements only **14 properties** (70% coverage)

3. **Naming Mismatches**: Three properties have incorrect names:
   - `rai:annotationPlatform` → should be `rai:dataAnnotationPlatform`
   - `rai:annotationProtocol` → should be `rai:dataAnnotationProtocol`
   - `rai:dataReleaseMaintenance` → should be `rai:dataReleaseMaintenancePlan`

### Stakeholders

- **Issue Reporter**: @monicacecilia (Mónica Muñoz Torres)
- **Tagged**: @justaddcoffee (Harry Caufield)
- **Target Audience**: Ethics and Standards Working Group
- **Implementers**: Harry and Marcin

---

## 2. Croissant RAI Specification Overview

### What is Croissant RAI?

The **Croissant Responsible AI (RAI) Specification Version 1.0** extends the Croissant dataset format with machine-readable metadata for ethical AI dataset documentation. It builds on schema.org/Dataset and uses the namespace `http://mlcommons.org/croissant/RAI/`.

### Official Property Count: 20 (Not 24)

The specification defines exactly **20 properties** organized across five use case categories:

| Use Case Category | Property Count |
|-------------------|----------------|
| Data Life Cycle | 7 properties |
| Data Labeling | 6 properties |
| Compliance | 3 properties |
| AI Safety and Fairness Evaluation | 4 properties |
| (No specific category) | 0 properties |

**Note**: D4D documentation incorrectly states 24 properties.

---

## 3. Complete Croissant RAI Property Reference

### All 20 Official Properties

| # | Property | Expected Type | Use Case | Cardinality | Description |
|---|----------|---------------|----------|-------------|-------------|
| 1 | `rai:annotationsPerItem` | sc:Text | Data labeling | ONE | Number of human labels per dataset item |
| 2 | `rai:annotatorDemographics` | sc:Text | Data labeling | MANY | Demographics specifications of annotators |
| 3 | `rai:dataAnnotationAnalysis` | sc:Text | Data labeling | ONE | Analysis of annotation agreement/quality |
| 4 | `rai:dataAnnotationPlatform` | sc:Text | Data labeling | ONE | Platform/tool used for annotation |
| 5 | `rai:dataAnnotationProtocol` | sc:DateTime | Data labeling | MANY | Annotation methodology and tasks |
| 6 | `rai:dataBiases` | sc:Text | AI safety | MANY | Description of dataset biases |
| 7 | `rai:dataCollection` | sc:Text | Data life cycle | ONE | Data collection process description |
| 8 | `rai:dataCollectionMissingData` | sc:Text | Data life cycle | ONE | Missing data documentation |
| 9 | `rai:dataCollectionRawData` | sc:Text | Data life cycle | ONE | Raw data source description |
| 10 | `rai:dataCollectionTimeframe` | sc:Text | Data life cycle | MANY | Collection start/end dates |
| 11 | `rai:dataCollectionType` | sc:Text | Data life cycle | MANY | Collection method (survey, web scraping, etc.) |
| 12 | `rai:dataImputationProtocol` | sc:Text | Data life cycle | ONE | Data imputation process |
| 13 | `rai:dataLimitations` | sc:Text | AI safety | MANY | Known limitations and constraints |
| 14 | `rai:dataManipulationProtocol` | sc:Text | Data life cycle | MANY | Data transformation procedures |
| 15 | `rai:dataPreprocessingProtocol` | sc:Text | Compliance | MANY | Preprocessing steps for ML |
| 16 | `rai:dataReleaseMaintenancePlan` | sc:Text | Compliance | ONE | Versioning and deprecation policies |
| 17 | `rai:dataSocialImpact` | sc:Text | AI safety | MANY | Social impact discussion |
| 18 | `rai:dataUseCases` | sc:Text | AI safety | MANY | Intended uses and guidelines |
| 19 | `rai:machineAnnotationTools` | sc:Text | Data labeling | MANY | Automated annotation tools |
| 20 | `rai:personalSensitiveInformation` | sc:Text | Compliance | MANY | Sensitive attributes (gender, age, etc.) |

---

## 4. Current D4D Implementation Status

### Implementation Summary

| Status | Count | Percentage |
|--------|-------|------------|
| ✓ Correctly Implemented | 11 | 55% |
| ⚠️ Implemented with Naming Issue | 3 | 15% |
| ❌ Missing | 6 | 30% |
| **TOTAL** | **20** | **100%** |

### 4.1 Correctly Implemented Properties (11)

| # | Croissant RAI Property | D4D Module | D4D Class/Slot | Notes |
|---|------------------------|------------|----------------|-------|
| 1 | `rai:annotationsPerItem` | D4D_Preprocessing | LabelingStrategy.annotations_per_item | ✓ Correct |
| 2 | `rai:annotatorDemographics` | D4D_Preprocessing | LabelingStrategy.annotator_demographics | ✓ Correct |
| 3 | `rai:dataBiases` | D4D_Composition | DatasetBias class | ✓ Semantic match |
| 4 | `rai:dataCollection` | D4D_Collection | CollectionMechanism class | ✓ Semantic match |
| 5 | `rai:dataCollectionType` | D4D_Collection | CollectionMechanism | ✓ Inferred from mechanism |
| 6 | `rai:dataLimitations` | D4D_Composition | DatasetLimitation class | ✓ Semantic match |
| 7 | `rai:dataManipulationProtocol` | D4D_Preprocessing | CleaningStrategy concept | ✓ Semantic match |
| 8 | `rai:dataPreprocessingProtocol` | D4D_Preprocessing | PreprocessingStrategy | ✓ Semantic match |
| 9 | `rai:dataSocialImpact` | D4D_Uses | FutureUseImpact concept | ✓ Semantic match |
| 10 | `rai:dataUseCases` | D4D_Uses | IntendedUse class | ✓ Semantic match |
| 11 | `rai:personalSensitiveInformation` | D4D_Composition | SensitiveElement class | ✓ Semantic match |

### 4.2 Implemented with Naming Issues (3)

| # | Current D4D Name | Should Be | D4D Module | Fix Required |
|---|------------------|-----------|------------|--------------|
| 1 | `rai:annotationPlatform` | `rai:dataAnnotationPlatform` | D4D_Preprocessing | Add "data" prefix |
| 2 | `rai:annotationProtocol` | `rai:dataAnnotationProtocol` | D4D_Preprocessing | Add "data" prefix |
| 3 | `rai:dataReleaseMaintenance` | `rai:dataReleaseMaintenancePlan` | D4D_Maintenance | Add "Plan" suffix |

**Impact**: These naming mismatches prevent proper automated mapping to Croissant RAI properties and reduce interoperability.

### 4.3 Missing Properties (6)

| # | Missing Property | Use Case | Recommended D4D Module | Priority |
|---|------------------|----------|------------------------|----------|
| 1 | `rai:dataCollectionMissingData` | Data life cycle | D4D_Collection | High |
| 2 | `rai:dataCollectionRawData` | Data life cycle | D4D_Collection | High |
| 3 | `rai:dataCollectionTimeframe` | Data life cycle | D4D_Collection | Medium* |
| 4 | `rai:dataImputationProtocol` | Data life cycle | D4D_Preprocessing | Medium |
| 5 | `rai:dataAnnotationAnalysis` | Data labeling | D4D_Preprocessing | Low |
| 6 | `rai:machineAnnotationTools` | Data labeling | D4D_Preprocessing | Low |

*Note: `dataCollectionTimeframe` is partially implemented as `CollectionTimeframe` class but lacks proper Croissant RAI mapping.

---

## 5. Detailed Implementation Analysis

### 5.1 D4D Schema Architecture

**Current Structure:**
- **Modular Design**: Properties distributed across 7 D4D modules
- **Class-Based**: D4D uses semantic classes (e.g., `DatasetBias`, `LabelingStrategy`)
- **No RAI Namespace**: No explicit `rai:` prefix or Croissant RAI namespace declarations
- **No Central Mapping**: No dedicated Croissant RAI section or mapping file

**Module Distribution:**

| D4D Module | RAI Properties | File Location |
|------------|----------------|---------------|
| D4D_Preprocessing | 6 properties | `src/data_sheets_schema/schema/D4D_Preprocessing.yaml` |
| D4D_Composition | 3 properties | `src/data_sheets_schema/schema/D4D_Composition.yaml` |
| D4D_Collection | 3 properties | `src/data_sheets_schema/schema/D4D_Collection.yaml` |
| D4D_Uses | 2 properties | `src/data_sheets_schema/schema/D4D_Uses.yaml` |
| D4D_Maintenance | 1 property | `src/data_sheets_schema/schema/D4D_Maintenance.yaml` |
| D4D_Data_Governance | 0 properties | `src/data_sheets_schema/schema/D4D_Data_Governance.yaml` |
| D4D_Ethics | 0 properties | `src/data_sheets_schema/schema/D4D_Ethics.yaml` |

### 5.2 Architectural Mismatch

**Croissant RAI Approach:**
- Property-based model with `rai:` prefix
- Direct sc:Text/sc:DateTime types
- Flat structure with namespace mappings

**D4D Approach:**
- Class-based model inheriting from `DatasetProperty`
- Complex nested structures
- Semantic organization by D4D module

**Example Contrast:**

```yaml
# Croissant RAI Style (expected)
"rai:dataBiases": [
  "Selection bias in training data",
  "Temporal bias due to data collection period"
]

# D4D Style (current)
dataset_biases:
  - id: dataset:bias:1
    description: "Selection bias in training data"
    bias_type: Selection Bias
    mitigation_strategy: "Resampling techniques applied"
    affected_subsets:
      - training_set
```

This semantic richness is a **D4D strength** but creates **mapping challenges** for Croissant RAI compliance.

---

## 6. Gap Analysis by Use Case Category

### Data Life Cycle (7 properties)

| Property | Status | Notes |
|----------|--------|-------|
| `rai:dataCollection` | ✓ | Via CollectionMechanism |
| `rai:dataCollectionType` | ✓ | Via CollectionMechanism |
| `rai:dataCollectionMissingData` | ❌ | **Missing** - No class for missing data |
| `rai:dataCollectionRawData` | ❌ | **Missing** - RawData class exists but unmapped |
| `rai:dataCollectionTimeframe` | ❌ | **Partial** - CollectionTimeframe exists but unmapped |
| `rai:dataManipulationProtocol` | ✓ | Via CleaningStrategy |
| `rai:dataImputationProtocol` | ❌ | **Missing** - No imputation class |

**Gap Score**: 3/7 complete (43%)

### Data Labeling (6 properties)

| Property | Status | Notes |
|----------|--------|-------|
| `rai:annotationsPerItem` | ✓ | Correct implementation |
| `rai:annotatorDemographics` | ✓ | Correct implementation |
| `rai:dataAnnotationAnalysis` | ❌ | **Missing** - No annotation quality class |
| `rai:dataAnnotationPlatform` | ⚠️ | **Naming issue** (missing "data" prefix) |
| `rai:dataAnnotationProtocol` | ⚠️ | **Naming issue** (missing "data" prefix) |
| `rai:machineAnnotationTools` | ❌ | **Missing** - No automated annotation class |

**Gap Score**: 2/6 complete (33%)

### Compliance (3 properties)

| Property | Status | Notes |
|----------|--------|-------|
| `rai:dataPreprocessingProtocol` | ✓ | Via PreprocessingStrategy |
| `rai:dataReleaseMaintenancePlan` | ⚠️ | **Naming issue** (missing "Plan" suffix) |
| `rai:personalSensitiveInformation` | ✓ | Via SensitiveElement |

**Gap Score**: 2/3 complete (67%)

### AI Safety and Fairness (4 properties)

| Property | Status | Notes |
|----------|--------|-------|
| `rai:dataBiases` | ✓ | Via DatasetBias |
| `rai:dataLimitations` | ✓ | Via DatasetLimitation |
| `rai:dataSocialImpact` | ✓ | Via FutureUseImpact |
| `rai:dataUseCases` | ✓ | Via IntendedUse |

**Gap Score**: 4/4 complete (100%)

---

## 7. Impact Assessment

### Standards Compliance Impact

**Current State:**
- 70% property coverage (14/20)
- 78% naming accuracy (11/14 correct names)
- No explicit Croissant RAI namespace mapping

**Implications:**
- ❌ Cannot claim full Croissant RAI conformance
- ❌ Automated Croissant RAI validators will fail
- ⚠️ Manual mapping required for Croissant export
- ✓ Semantic coverage is reasonably strong

### Interoperability Impact

**Affected Systems:**
- MLCommons Croissant ecosystem
- Hugging Face Datasets (supports Croissant)
- OpenML (Croissant-compatible)
- Kaggle Datasets (Croissant metadata)

**Consequences:**
- Bridge2AI datasets cannot be automatically discovered via Croissant RAI properties
- Export to Croissant format requires custom transformation logic
- RAI metadata not machine-readable in standard Croissant tools

### Documentation Impact

**Current Documentation Issues:**
1. **Inaccurate property count**: States 24 properties (should be 20)
2. **Missing property table**: No complete comparison table
3. **No mapping guidance**: Unclear how to use D4D for Croissant RAI compliance

**Impact on Users:**
- Confusion about Croissant RAI support
- Unclear which D4D fields map to which RAI properties
- Difficult to generate Croissant-compliant metadata

---

## 8. Recommendations

### 8.1 Immediate Actions (High Priority)

#### 1. Fix Naming Mismatches (Quick Wins)

**File**: `src/data_sheets_schema/schema/D4D_Preprocessing.yaml`

```yaml
# Current (INCORRECT)
annotation_platform:
  range: string
  slot_uri: schema:instrument

annotation_protocol:
  range: string

# Proposed (CORRECT)
data_annotation_platform:
  range: string
  slot_uri: schema:instrument
  exact_mappings:
    - rai:dataAnnotationPlatform

data_annotation_protocol:
  range: string
  exact_mappings:
    - rai:dataAnnotationProtocol
```

**File**: `src/data_sheets_schema/schema/D4D_Maintenance.yaml`

```yaml
# Current (INCORRECT)
data_release_maintenance:
  range: UpdatePlan

# Proposed (CORRECT)
data_release_maintenance_plan:
  range: UpdatePlan
  exact_mappings:
    - rai:dataReleaseMaintenancePlan
```

**Effort**: 2-4 hours
**Impact**: High (fixes 15% of properties)

#### 2. Add Missing Properties

**a) Data Collection Properties** (File: `D4D_Collection.yaml`)

```yaml
classes:
  MissingDataDocumentation:
    is_a: DatasetProperty
    description: Documentation of missing data in the dataset
    attributes:
      missing_data_patterns:
        range: string
        multivalued: true
      handling_strategy:
        range: string
    exact_mappings:
      - rai:dataCollectionMissingData

  RawDataSource:
    is_a: DatasetProperty
    description: Description of raw data sources
    attributes:
      source_description:
        range: string
      access_details:
        range: string
    exact_mappings:
      - rai:dataCollectionRawData
```

**b) Preprocessing Properties** (File: `D4D_Preprocessing.yaml`)

```yaml
classes:
  ImputationProtocol:
    is_a: DatasetProperty
    description: Data imputation methodology
    attributes:
      imputation_method:
        range: string
      imputed_fields:
        range: string
        multivalued: true
    exact_mappings:
      - rai:dataImputationProtocol

  AnnotationAnalysis:
    is_a: DatasetProperty
    description: Analysis of annotation quality and agreement
    attributes:
      inter_annotator_agreement:
        range: float
      analysis_method:
        range: string
    exact_mappings:
      - rai:dataAnnotationAnalysis

  MachineAnnotationTools:
    is_a: DatasetProperty
    description: Automated annotation tools used
    attributes:
      tool_name:
        range: string
      tool_version:
        range: string
    exact_mappings:
      - rai:machineAnnotationTools
```

**Effort**: 8-12 hours
**Impact**: Very High (adds 30% coverage)

#### 3. Add Explicit Mappings to All Properties

Add `exact_mappings` to all 14 existing Croissant RAI-related properties:

```yaml
# Example for DatasetBias class
DatasetBias:
  is_a: DatasetProperty
  description: Documented biases in the dataset
  exact_mappings:
    - rai:dataBiases
  # ... rest of class definition
```

**Effort**: 3-5 hours
**Impact**: High (enables automated Croissant mapping)

### 8.2 Medium Priority Actions

#### 4. Update Documentation

**File**: `data/schema_comparison/schemas/croissant_rai/croissant_rai_spec.md`

- Correct property count from 24 to **20**
- Add complete property mapping table (use table from this report)
- Document D4D-to-Croissant transformation guidance

**Effort**: 2-3 hours

#### 5. Create Croissant Export Utility

Develop Python script to export D4D YAML to Croissant JSON-LD with RAI properties:

```python
# croissant_exporter.py
def export_to_croissant(d4d_yaml_path, output_json_path):
    """Convert D4D YAML to Croissant JSON-LD with RAI properties"""
    # Map D4D classes to rai: properties
    # Generate conformant JSON-LD
    pass
```

**Effort**: 16-20 hours

### 8.3 Long-term Improvements

#### 6. Consider D4D_Croissant Module

Create dedicated module for Croissant RAI alignment:

```yaml
# src/data_sheets_schema/schema/D4D_Croissant.yaml
id: https://w3id.org/bridge2ai/data-sheets-schema/D4D_Croissant
name: D4D_Croissant
description: Croissant RAI property mappings for D4D

prefixes:
  rai: http://mlcommons.org/croissant/RAI/

# Centralized Croissant RAI property definitions
```

**Effort**: 24-32 hours

#### 7. Add Croissant RAI Validation

Create LinkML validation rule to ensure Croissant RAI compliance:

```yaml
# In schema rules
rules:
  - preconditions:
      slot_conditions:
        conformsTo:
          equals_string: "http://mlcommons.org/croissant/RAI/1.0"
    postconditions:
      slot_conditions:
        # Ensure all 20 RAI properties are addressable
```

**Effort**: 8-12 hours

#### 8. Establish Governance Process

**Action Items:**
1. Designate Croissant RAI compliance owner
2. Create quarterly review schedule for Croissant spec updates
3. Add Croissant RAI to CI/CD validation pipeline
4. Establish communication channel with MLCommons Croissant team

---

## 9. Discussion Questions for Ethics & Standards WG

As noted in issue #105, the complete property list should be reviewed with the Ethics and Standards Working Group. Key discussion points:

### 9.1 Mapping Philosophy

**Question**: Should D4D maintain strict 1:1 mapping with Croissant RAI, or is semantic equivalence sufficient?

**Options:**
- **Option A (Strict)**: Every `rai:` property has exact corresponding D4D field
  - Pros: Perfect interoperability, automated mapping
  - Cons: Less semantic flexibility, may duplicate D4D concepts

- **Option B (Semantic)**: D4D classes can represent multiple `rai:` properties
  - Pros: Richer semantics, reduces redundancy
  - Cons: Requires custom mapping logic, harder to automate

**Recommendation**: Hybrid approach - maintain exact mappings via `exact_mappings` annotations while preserving D4D's richer semantic structure.

### 9.2 Missing Property Prioritization

**Question**: Which of the 6 missing properties are most critical for Bridge2AI projects?

**Priority Assessment:**

| Property | Bridge2AI Relevance | Recommendation |
|----------|---------------------|----------------|
| `dataCollectionMissingData` | High - common in biomedical data | **Must add** |
| `dataCollectionRawData` | High - critical for reproducibility | **Must add** |
| `dataCollectionTimeframe` | Medium - already partially implemented | Add mapping |
| `dataImputationProtocol` | Medium - relevant for some projects | Add if feasible |
| `dataAnnotationAnalysis` | Low - niche use case | Optional |
| `machineAnnotationTools` | Low - not widely used | Optional |

### 9.3 Architectural Decision

**Question**: Should Croissant RAI properties be:
1. Scattered across existing D4D modules (current approach)?
2. Consolidated in a new `D4D_Croissant.yaml` module?
3. Maintained as a separate mapping layer?

**Trade-offs:**
- **Scattered**: Natural D4D organization, but harder to maintain RAI compliance
- **Consolidated**: Easy Croissant mapping, but creates artificial separation
- **Mapping layer**: Preserves both structures, but adds complexity

### 9.4 Maintenance Commitment

**Question**: What level of ongoing commitment can Bridge2AI make to Croissant RAI alignment?

**Options:**
- **Full commitment**: Track all Croissant spec updates, maintain 100% compliance
- **Best effort**: Align when practical, document gaps
- **Snapshot**: Implement current spec (v1.0), revisit at major versions

---

## 10. Action Plan Summary

### Phase 1: Immediate Fixes (1-2 weeks)

| Task | Effort | Priority | Owner |
|------|--------|----------|-------|
| Fix 3 naming mismatches | 2-4 hours | P0 | TBD |
| Add `exact_mappings` to existing properties | 3-5 hours | P0 | TBD |
| Update documentation (property count) | 2-3 hours | P1 | TBD |

**Deliverable**: 14 properties with correct names and mappings (70% coverage)

### Phase 2: Fill Gaps (2-4 weeks)

| Task | Effort | Priority | Owner |
|------|--------|----------|-------|
| Add `dataCollectionMissingData` | 2 hours | P1 | TBD |
| Add `dataCollectionRawData` | 2 hours | P1 | TBD |
| Map `dataCollectionTimeframe` | 1 hour | P1 | TBD |
| Add `dataImputationProtocol` | 2 hours | P2 | TBD |
| Add `dataAnnotationAnalysis` | 2 hours | P2 | TBD |
| Add `machineAnnotationTools` | 2 hours | P2 | TBD |

**Deliverable**: 20 properties fully implemented (100% coverage)

### Phase 3: Tooling & Validation (4-6 weeks)

| Task | Effort | Priority | Owner |
|------|--------|----------|-------|
| Create Croissant exporter | 16-20 hours | P2 | TBD |
| Add Croissant RAI validation | 8-12 hours | P2 | TBD |
| Update user documentation | 8 hours | P2 | TBD |

**Deliverable**: Automated Croissant export and validation

### Phase 4: Governance (Ongoing)

| Task | Effort | Priority | Owner |
|------|--------|----------|-------|
| Present to Ethics & Standards WG | 2 hours | P0 | @monicacecilia |
| Establish maintenance process | 4 hours | P1 | TBD |
| Create Croissant compliance CI check | 8 hours | P2 | TBD |

**Deliverable**: Sustainable Croissant RAI alignment process

---

## 11. Conclusion

Bridge2AI's D4D schema has made significant progress toward Croissant RAI compliance (70% coverage), but **gaps and naming issues prevent full conformance**. The recommended three-phase approach—fix naming issues, add missing properties, and establish governance—will achieve 100% compliance while preserving D4D's semantic richness.

### Key Takeaways

1. **Quick Wins Available**: Fixing 3 naming issues improves compliance from 55% to 70% correct properties
2. **Manageable Gaps**: Adding 6 missing properties is feasible (estimated 12-16 hours total effort)
3. **Architectural Strength**: D4D's class-based approach provides richer semantics than flat Croissant properties
4. **Governance Critical**: Ongoing alignment requires designated owner and review process

### Next Steps

1. **Immediate**: Review this analysis with @monicacecilia, @justaddcoffee, Harry, and Marcin
2. **This Week**: Schedule Ethics & Standards WG discussion
3. **This Month**: Implement Phase 1 (naming fixes and mappings)
4. **Next Quarter**: Complete Phases 2-3 (full property coverage and tooling)

---

## Appendices

### Appendix A: Complete Property Mapping Table

| # | Croissant RAI Property | Status | D4D Module | D4D Implementation | Notes |
|---|------------------------|--------|------------|-------------------|-------|
| 1 | `rai:annotationsPerItem` | ✓ | Preprocessing | LabelingStrategy.annotations_per_item | Correct |
| 2 | `rai:annotatorDemographics` | ✓ | Preprocessing | LabelingStrategy.annotator_demographics | Correct |
| 3 | `rai:dataAnnotationAnalysis` | ❌ | — | Missing | **Add to Preprocessing** |
| 4 | `rai:dataAnnotationPlatform` | ⚠️ | Preprocessing | LabelingStrategy.annotation_platform | **Rename** (add "data" prefix) |
| 5 | `rai:dataAnnotationProtocol` | ⚠️ | Preprocessing | Inferred from LabelingStrategy | **Rename** (add "data" prefix) |
| 6 | `rai:dataBiases` | ✓ | Composition | DatasetBias class | Correct (semantic) |
| 7 | `rai:dataCollection` | ✓ | Collection | CollectionMechanism class | Correct (semantic) |
| 8 | `rai:dataCollectionMissingData` | ❌ | — | Missing | **Add to Collection** |
| 9 | `rai:dataCollectionRawData` | ❌ | — | Partial (RawData class) | **Add mapping to Collection** |
| 10 | `rai:dataCollectionTimeframe` | ❌ | Collection | CollectionTimeframe (unmapped) | **Add mapping** |
| 11 | `rai:dataCollectionType` | ✓ | Collection | CollectionMechanism | Correct (inferred) |
| 12 | `rai:dataImputationProtocol` | ❌ | — | Missing | **Add to Preprocessing** |
| 13 | `rai:dataLimitations` | ✓ | Composition | DatasetLimitation class | Correct (semantic) |
| 14 | `rai:dataManipulationProtocol` | ✓ | Preprocessing | CleaningStrategy concept | Correct (semantic) |
| 15 | `rai:dataPreprocessingProtocol` | ✓ | Preprocessing | PreprocessingStrategy | Correct |
| 16 | `rai:dataReleaseMaintenancePlan` | ⚠️ | Maintenance | UpdatePlan (as dataReleaseMaintenance) | **Rename** (add "Plan" suffix) |
| 17 | `rai:dataSocialImpact` | ✓ | Uses | FutureUseImpact concept | Correct (semantic) |
| 18 | `rai:dataUseCases` | ✓ | Uses | IntendedUse class | Correct (semantic) |
| 19 | `rai:machineAnnotationTools` | ❌ | — | Missing | **Add to Preprocessing** |
| 20 | `rai:personalSensitiveInformation` | ✓ | Composition | SensitiveElement class | Correct (semantic) |

**Legend:**
- ✓ = Correctly implemented
- ⚠️ = Implemented with naming issue
- ❌ = Missing

### Appendix B: References

1. **MLCommons Croissant RAI Specification v1.0**
   https://docs.mlcommons.org/croissant/docs/croissant-rai-spec.html

2. **Bridge2AI D4D Schema Repository**
   https://github.com/bridge2ai/data-sheets-schema

3. **GitHub Issue #105**
   https://github.com/bridge2ai/data-sheets-schema/issues/105

4. **Google Sheets Comparison**
   https://docs.google.com/spreadsheets/d/1fE-vNHiUaYwgW20BSxRP0I7nXagPweCjWmcsX3KyzH4/edit

5. **Croissant Format Specification**
   https://github.com/mlcommons/croissant

6. **D4D Current Croissant Documentation**
   `data/schema_comparison/schemas/croissant_rai/croissant_rai_spec.md`

---

**Report Generated**: 2025-12-17
**Analysis Tool**: Claude Code (Sonnet 4.5)
**Report Location**: `data/schema_comparison/schemas/croissant_rai/gap_analysis_2025-12.md`
