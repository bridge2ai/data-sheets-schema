# D4D ↔ RO-Crate Coverage Gap Analysis

**Date**: 2026-03-12
**Mapping Version**: v2 Semantic
**Analysis Scope**: Full D4D LinkML schema to RO-Crate JSON-LD

---

## Executive Summary

**Mapping Coverage**:
- **Total D4D fields analyzed**: 133+ unique paths
- **Mapped fields**: 125 (94.0%)
- **Unmapped/partial fields**: 8 core + 14 nested properties (16.5%)

**Information Loss by Level**:
- **None (lossless)**: 71 fields (53.4%)
- **Minimal loss**: 27 fields (20.3%)
- **Moderate loss**: 19 fields (14.3%)
- **High loss**: 16 fields (12.0%)

**Mapping Quality**:
- **Exact matches (direct 1:1)**: 71 fields (53.4%)
- **Close matches (transformation)**: 37 fields (27.8%)
- **Related matches (complex/partial)**: 13 fields (9.8%)
- **Narrow/broad matches**: 4 fields (3.0%)
- **Unmapped**: 8 fields (6.0%)

---

## 1. D4D Fields NOT Fully Mapped to RO-Crate

### 1.1 High Priority Gaps (8 core fields)

These are top-level D4D fields with no direct RO-Crate equivalent:

| D4D Field | Type | Why Unmapped | Workaround | Impact |
|-----------|------|--------------|------------|--------|
| `Dataset.variables` | List[Variable] | RO-Crate has no variable schema | Use `additionalProperty` pattern | **High** - Loses structured variable metadata |
| `Dataset.sampling_strategies` | List[SamplingStrategy] | Complex structured type | Flatten to `d4d:samplingStrategy` string | **Moderate** - Loses strategy type, details |
| `Dataset.subsets` | List[Subset] | Complex split/population structure | Partial: map to `schema:hasPart` | **High** - Loses split type, population flags |
| `Dataset.instances` | Instance | Complex instance description | Partial: map to `schema:variableMeasured` | **High** - Loses data_topic, instance_type, counts |
| `Dataset.subpopulations` | List[SubpopulationElement] | Complex demographic structure | Partial: flatten to string | **Moderate** - Loses structured subpopulation data |
| `Dataset.use_repository` | str | Not in RO-Crate core | Use `schema:relatedLink` | **Low** - URL preserved, semantics lost |
| `Dataset.version_access` | str | Version policy not in core | Use `schema:version` note | **Low** - Can embed in maintenance plan |
| `Dataset.retention_limit` | str | Data retention policy gap | Use `schema:conditionsOfAccess` | **Low** - Can embed in access conditions |

**Recommendation**: Extend D4D RO-Crate profile with custom namespace (`d4d:`) for these properties. Already partially done for sampling_strategies.

### 1.2 Nested Property Gaps (14 fields)

These are nested properties within complex types that lose structure when flattened:

#### Cleaning/Preprocessing Pipeline Elements
| Nested Field | Parent | Loss Level | Notes |
|--------------|--------|------------|-------|
| `CleaningStrategy.step_type` | cleaning_strategies | **High** | Enumeration (data_cleaning, deduplication, etc.) lost when flattened to string |
| `CleaningStrategy.pipeline_step` | cleaning_strategies | **High** | Step ordering lost in flattening |
| `PreprocessingStrategy.step_type` | preprocessing_strategies | **High** | Enumeration lost |
| `PreprocessingStrategy.pipeline_step` | preprocessing_strategies | **High** | Step ordering lost |

#### Annotation Details
| Nested Field | Parent | Loss Level | Notes |
|--------------|--------|------------|-------|
| `LabelingStrategy.annotator_type` | labeling_strategies | **High** | Annotator type (expert, crowdworker, etc.) lost |
| `LabelingStrategy.evidence_type` | labeling_strategies | **High** | ECO (Evidence & Conclusion Ontology) codes lost - no RO-Crate support |
| `MachineAnnotation.tool_name` | machine_annotation_analyses | **Moderate** | Tool name flattened with version |
| `MachineAnnotation.version` | machine_annotation_analyses | **Moderate** | Version info preserved but structure lost |

#### Instance/Subset Details
| Nested Field | Parent | Loss Level | Notes |
|--------------|--------|------------|-------|
| `Instance.data_topic` | instances | **High** | Topic (Patient, Image, Measurement, etc.) lost |
| `Instance.instance_type` | instances | **High** | Type (record, file, etc.) lost |
| `Instance.counts` | instances | **High** | Instance counts lost |
| `Subset.is_data_split` | subsets | **High** | Split type (train, test, validation) lost |
| `Subset.is_sub_population` | subsets | **High** | Subpopulation flag lost |

#### Variable Schema (No RO-Crate equivalent)
| Nested Field | Parent | Loss Level | Notes |
|--------------|--------|------------|-------|
| `Variable.name` | variables | **High** | Variable name lost |
| `Variable.type` | variables | **High** | Data type lost |

**Recommendation**: For structured arrays (cleaning_strategies, preprocessing_strategies, labeling_strategies), consider:
1. **Option A**: Extend RO-Crate with d4d: namespace for structured arrays
2. **Option B**: Use nested `additionalProperty` arrays with PropertyValue objects
3. **Option C**: Accept information loss for simple use cases, preserve full structure in D4D YAML sidecar

---

## 2. RO-Crate Fields NOT Mapped to D4D

### 2.1 RO-Crate Extensions Not in D4D (11 properties)

| RO-Crate Property | Namespace | Why Not in D4D | Add to D4D? |
|-------------------|-----------|----------------|-------------|
| `temporalCoverage` | schema.org | Temporal scope of dataset | **Recommended** - Useful for timeseries data |
| `spatialCoverage` | schema.org | Geographic scope | **Recommended** - Useful for geospatial data |
| `measurementTechnique` | schema.org | Measurement methods | **Consider** - Could add to collection section |
| `variableMeasured` | schema.org | Variables/properties measured | **Recommended** - Related to D4D variables |

#### FAIRSCAPE-Specific Extensions (7 properties)
| Property | Use Case | Add to D4D? |
|----------|----------|-------------|
| `evi:customProperty` | FAIRSCAPE arbitrary metadata | **No** - Too generic |
| `evi:guidType` | FAIRSCAPE GUID scheme | **No** - Implementation-specific |
| `evi:rocrateProfile` | Profile conformance tracking | **Consider** - Could add for validation |
| `evi:generatedAtTime` | Provenance timestamp | **No** - Covered by dateCreated |
| `evi:usedSoftware` | Software provenance | **Consider** - Could enhance preprocessing section |
| `evi:usedDataset` | Dataset provenance | **No** - Covered by was_derived_from |
| `evi:hadPlan` | Execution plan | **No** - Out of D4D scope |

**Recommendation**: Add `temporalCoverage`, `spatialCoverage`, and `variableMeasured` to D4D schema in future version. Others are FAIRSCAPE-specific and not needed.

---

## 3. Information Loss Analysis

### 3.1 D4D → RO-Crate Transformation

**Primary Loss Mechanisms**:

1. **Object Flattening** (19 fields, **12-14% loss**)
   - Structured arrays → strings
   - Example: `[{"description":"Remove duplicates", "step_type":"data_cleaning", "pipeline_step":20}]` → `"Removed duplicate records"`
   - **Fields affected**: cleaning_strategies, preprocessing_strategies, labeling_strategies, annotation_analyses

2. **Namespace Consolidation** (16 fields, **minimal loss**)
   - Multiple D4D fields → single RO-Crate property
   - Example: `purposes` + `tasks` + `intended_uses` → `rai:dataUseCases`
   - **Fields affected**: All RAI use case fields, multiple purpose fields

3. **Type Coercion** (5 fields, **minimal loss**)
   - Boolean → string, enum → string
   - Example: `is_deidentified: true` → `"de-identified"`
   - **Fields affected**: is_deidentified, is_tabular, compression enum

4. **Evidence Ontology Loss** (1 field, **high loss**)
   - ECO (Evidence & Conclusion Ontology) codes not supported in RO-Crate
   - Example: `LabelingStrategy.evidence_type: ECO:0000217` → lost entirely
   - **Impact**: Loss of formal evidence provenance

**Mitigation Strategies**:
- Include full D4D YAML as `additionalProperty` in RO-Crate
- Use transformation metadata to document what was flattened
- Provide round-trip validation tests to detect unexpected loss

### 3.2 RO-Crate → D4D Transformation

**Primary Loss Mechanisms**:

1. **Structure Inference** (**moderate loss**)
   - Flat strings → structured arrays
   - Example: `"Removed duplicates"` → `[{"description":"Removed duplicates", "step_type":"UNKNOWN"}]`
   - **Impact**: Must infer or prompt for missing structure

2. **FAIRSCAPE Metadata Exclusion** (**low loss**)
   - FAIRSCAPE-specific properties not in D4D
   - Example: `evi:guidType` → dropped
   - **Impact**: Minimal - most FAIRSCAPE metadata is out of D4D scope

3. **Multi-Source Consolidation** (**moderate loss**)
   - Multiple RO-Crate sources → single D4D field
   - Example: Merge `rai:dataUseCases` from multiple files into `Dataset.intended_uses`
   - **Impact**: Potential duplication or conflicts

**Mitigation Strategies**:
- Preserve RO-Crate source provenance in D4D metadata
- Provide merge conflict resolution rules
- Document expected vs. actual round-trip preservation rates

---

## 4. Round-Trip Preservation Estimates

Based on mapping analysis and information loss assessment:

| Transformation Path | Expected Preservation | Actual (Tested) | Notes |
|---------------------|----------------------|-----------------|-------|
| **D4D → RO-Crate → D4D** | 85-90% | TBD (needs tests) | Loss from object flattening |
| **RO-Crate → D4D → RO-Crate** | 90-95% | TBD (needs tests) | Loss from structure inference |
| **Minimal Profile (8 fields)** | 100% | TBD | All required fields preserve |
| **Basic Profile (25 fields)** | 95% | TBD | Minimal loss in RAI fields |
| **Complete Profile (100+ fields)** | 85% | TBD | Structured array loss |

**Fields with Guaranteed Preservation** (71 fields):
- All exactMatch mappings (title, description, keywords, dates, checksums, etc.)
- Basic metadata, identifiers, simple RAI fields

**Fields with Expected Loss** (16 fields):
- Structured arrays (cleaning_strategies, preprocessing_strategies, labeling_strategies)
- Nested properties (step_type, pipeline_step, evidence_type)
- Complex types (instances, subsets, variables)

**Unmapped/High-Risk Fields** (8 fields):
- variables, sampling_strategies, subsets (complex), instances (complex)

---

## 5. Bidirectional Mapping Challenges

### 5.1 Asymmetric Mappings

**D4D fields that map to multiple RO-Crate properties**:
- `license_and_use_terms` → `license` + `conditionsOfAccess`
- `cleaning_strategies` → `rai:dataManipulationProtocol` (loses structure)

**RO-Crate properties that merge into single D4D field**:
- `rai:dataUseCases` ← `purposes` + `tasks` + `intended_uses`

### 5.2 Structural Impedance

**D4D arrays ↔ RO-Crate strings**:
- D4D uses structured arrays for pipelines (cleaning, preprocessing, labeling)
- RO-Crate typically uses plain strings for these
- **Solution**: Use d4d: namespace extension for structured arrays in RO-Crate profile

**D4D enumerations ↔ RO-Crate free text**:
- D4D uses controlled vocabularies (step_type, annotator_type, compression enum)
- RO-Crate often uses free text
- **Solution**: Document expected values in RO-Crate profile specification

---

## 6. Recommendations for Future Work

### 6.1 Schema Enhancements

**Add to D4D Schema** (Priority: High):
1. `temporalCoverage` - Temporal scope (from schema.org)
2. `spatialCoverage` - Geographic scope (from schema.org)
3. `variableMeasured` - Measured variables (from schema.org)

**Clarify in D4D Schema** (Priority: Medium):
1. `variables` - Formalize variable schema structure
2. `sampling_strategies` - Clarify strategy types and structure
3. `subsets` - Standardize split types and subpopulation flags

### 6.2 RO-Crate Profile Enhancements

**Extend D4D RO-Crate Profile** (Priority: High):
1. Define `d4d:cleaningStrategies` as structured array (not flattened string)
2. Define `d4d:preprocessingStrategies` as structured array
3. Define `d4d:labelingStrategies` as structured array with ECO evidence codes
4. Add SHACL shapes for structured array validation

**Document in Profile Spec** (Priority: High):
1. Information loss expectations for each conformance level
2. Round-trip preservation guarantees
3. Extension mechanism for custom properties

### 6.3 Transformation Infrastructure

**Implement** (Priority: High):
1. Round-trip preservation tests (Phase 2)
2. Transformation provenance tracking (Phase 3)
3. Merge conflict resolution for multi-source RO-Crates (Phase 3)

**Document** (Priority: Medium):
1. Expected vs. actual information loss by field
2. Transformation decision rationale
3. User guidelines for minimizing loss

### 6.4 Validation Framework

**Implement** (Priority: High):
1. Profile conformance validation (Level 1/2/3)
2. Round-trip preservation validation
3. Information loss measurement and reporting

---

## 7. Gap Statistics Summary

### 7.1 By Mapping Quality

| Category | Count | Percentage | Information Loss |
|----------|-------|------------|------------------|
| Exact match (lossless) | 71 | 53.4% | None |
| Close match (minimal loss) | 37 | 27.8% | Minimal (string transforms, type coercion) |
| Related match (partial) | 13 | 9.8% | Moderate (structure flattening) |
| Narrow/broad match | 4 | 3.0% | Minimal (scope differences) |
| Unmapped | 8 | 6.0% | High (no equivalent) |
| **Total** | **133** | **100%** | **Average: ~15% information loss** |

### 7.2 By D4D Module/Category

| Category | Mapped | Partial | Unmapped | Total | Coverage % |
|----------|--------|---------|----------|-------|------------|
| Basic Metadata | 14 | 0 | 0 | 14 | 100% |
| Dates | 4 | 0 | 0 | 4 | 100% |
| Checksums & Identifiers | 5 | 0 | 0 | 5 | 100% |
| Relationships | 3 | 2 | 0 | 5 | 100% |
| Creators & Attribution | 3 | 0 | 0 | 3 | 100% |
| RAI Use Cases | 9 | 0 | 0 | 9 | 100% |
| RAI Biases & Limitations | 6 | 0 | 0 | 6 | 100% |
| Privacy | 5 | 0 | 0 | 5 | 100% |
| Data Collection | 5 | 1 | 0 | 6 | 100% |
| **Preprocessing** | 8 | 4 | 0 | 12 | **67%** (nested props lost) |
| **Annotation** | 4 | 4 | 0 | 8 | **50%** (nested props lost) |
| Ethics & Compliance | 8 | 2 | 0 | 10 | 100% |
| Governance | 6 | 0 | 0 | 6 | 100% |
| Maintenance | 2 | 1 | 0 | 3 | 100% |
| FAIRSCAPE EVI | 9 | 0 | 0 | 9 | 100% |
| D4D-Embedded | 5 | 0 | 0 | 5 | 100% |
| Quality | 4 | 0 | 0 | 4 | 100% |
| Format | 3 | 2 | 0 | 5 | 100% |
| **Unmapped/Complex** | 0 | 6 | 8 | 14 | **43%** |
| **Total** | **103** | **22** | **8** | **133** | **94.0%** |

**Key Findings**:
- **Preprocessing** and **Annotation** modules have highest information loss (nested properties)
- **Unmapped/Complex** types (variables, subsets, instances) have lowest coverage
- 94% of D4D fields have at least partial RO-Crate mappings
- Only 6% are truly unmapped (no workaround available)

---

## 8. Conclusions

### Strengths of Current Mapping

1. **High coverage** (94% of D4D fields mapped or partially mapped)
2. **Lossless mapping** for majority of fields (53.4% exact matches)
3. **Comprehensive profile** covering all 10 D4D sections
4. **Clear semantics** via SKOS alignment (exactMatch, closeMatch, etc.)
5. **Extension mechanism** via d4d: namespace and additionalProperty pattern

### Remaining Challenges

1. **Structured array flattening** - Preprocessing, annotation, labeling pipelines lose step order and types
2. **Evidence ontology gap** - ECO codes not supported in RO-Crate
3. **Variable schema gap** - No RO-Crate equivalent for structured variable metadata
4. **Complex type mapping** - Instances, subsets, sampling strategies have partial/lossy mappings

### Path Forward

**Short-term** (Implement now):
- Complete Phase 1: SKOS alignment, enhanced TSV v2, interface mapping ✅
- Complete Phase 2: Validation framework with 4 levels
- Complete Phase 3: Transformation API with provenance tracking

**Medium-term** (Next release):
- Extend D4D RO-Crate profile with structured array support
- Add round-trip preservation tests with acceptance criteria
- Document information loss expectations per conformance level

**Long-term** (Future versions):
- Propose schema.org extensions for variable schemas
- Contribute ECO evidence type support to RO-Crate community
- Develop best practices for lossless D4D ↔ RO-Crate transformation

---

## Appendix A: Complete Unmapped Field List

| D4D Field | Type | Recommendation |
|-----------|------|----------------|
| `Dataset.variables` | List[Variable] | **Add to D4D profile** - Use additionalProperty array |
| `Dataset.sampling_strategies` | List[SamplingStrategy] | **Partially supported** - Extend d4d:samplingStrategy to structured array |
| `Dataset.subsets` | List[Subset] | **Partially supported** - Map to hasPart, document split types |
| `Dataset.instances` | Instance | **Partially supported** - Map to variableMeasured, document structure |
| `Dataset.subpopulations` | List[SubpopulationElement] | **Partially supported** - Flatten to string with documentation |
| `Dataset.use_repository` | str | **Low priority** - Map to relatedLink |
| `Dataset.version_access` | str | **Low priority** - Embed in version or maintenance plan |
| `Dataset.retention_limit` | str | **Low priority** - Embed in conditionsOfAccess |

**Nested properties** (14 fields) - See Section 1.2 for complete list.

---

**Document Version**: 1.0
**Last Updated**: 2026-03-12
**Maintainer**: Bridge2AI Data Standards Core
**Related Files**:
- `d4d_rocrate_mapping_v2_semantic.tsv` - Enhanced mapping with semantic annotations
- `d4d_rocrate_interface_mapping.tsv` - Complete D4D → RO-Crate interface specification
- `d4d_rocrate_skos_alignment.ttl` - SKOS semantic alignment ontology
