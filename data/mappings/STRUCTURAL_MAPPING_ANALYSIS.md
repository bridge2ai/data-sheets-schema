# D4D ↔ RO-Crate Schema-Structure-Aware Mapping Analysis

## Overview

This document describes the schema-structure-aware mapping between D4D (Datasheets for Datasets) and RO-Crate FAIRSCAPE implementation.

**Generation Date**: 2026-03-20  
**Method**: Automated structural analysis  
**Script**: `src/alignment/generate_structural_mapping.py`  
**Total Mappings**: 142

## Mapping Quality Metrics

| Metric | Count | Percentage |
|--------|-------|------------|
| **Total mappings** | 142 | 100% |
| **Exact matches** (confidence = 1.0) | 130 | 91.5% |
| **Close matches** (confidence < 1.0) | 12 | 8.5% |
| **Type-compatible mappings** | 142 | 100% |
| **Mappings with warnings** | 0 | 0% |

## Structural Awareness Features

### 1. Inheritance Hierarchy Analysis ✅

The mapper identifies all classes that inherit from `DatasetProperty` and applies consistent mapping patterns:

**Example**:
```
Purpose (is_a: DatasetProperty)
  ├─ Purpose.name → name (exactMatch, confidence: 1.0)
  ├─ Purpose.description → description (exactMatch, confidence: 1.0)
  └─ Purpose.id → identifier (filtered out - low similarity)

Task (is_a: DatasetProperty)
  ├─ Task.name → name (exactMatch, confidence: 1.0)
  ├─ Task.description → description (exactMatch, confidence: 1.0)
  └─ Task.id → identifier (filtered out - low similarity)
```

**Total DatasetProperty subclasses mapped**: 50+

### 2. Composition Path Tracing ✅

The mapper follows composition relationships where slots have class ranges:

**Example**:
```
Creator.principal_investigator (range: Person)
  └─ → principalInvestigator (exactMatch, confidence: 1.0)

FundingMechanism.grantor (range: Grantor)
  └─ → funder (composition path traced)
```

### 3. Module Semantic Grouping ✅

The mapper groups classes by LinkML module and maps to corresponding RO-Crate namespaces:

| D4D Module | RO-Crate Namespace | Mappings |
|------------|-------------------|----------|
| Motivation | d4d:, schema: | ~20 |
| Composition | d4d:, schema: | ~25 |
| Collection | rai:, schema: | ~18 |
| Preprocessing | rai: | ~15 |

### 4. Type Compatibility Validation ✅

The mapper validates that source and target types are compatible:

**Validation Rules**:
- ❌ `boolean` cannot map to relationship properties (e.g., `prov:wasDerivedFrom`)
- ❌ `boolean` cannot map to date properties (e.g., `schema:date`)
- ❌ Multivalued slots cannot map to single-value properties
- ❌ Literal values cannot map to semantic relationships
- ✅ All generated mappings passed validation

## Example Mappings by Category

### Exact Name Matches (confidence = 1.0)

```sssom
d4d:Purpose/name → name (skos:exactMatch)
d4d:Purpose/description → description (skos:exactMatch)
d4d:Creator/principal_investigator → principalInvestigator (skos:exactMatch)
d4d:Dataset/identifier → identifier (skos:exactMatch)
d4d:Dataset/version → version (skos:exactMatch)
d4d:Dataset/license → license (skos:exactMatch)
d4d:Dataset/keywords → keywords (skos:exactMatch)
```

### Semantic Matches (confidence < 1.0)

```sssom
d4d:DataSubset/bytes → contentSize (skos:closeMatch, confidence: 0.7)
d4d:Dataset/issued → datePublished (skos:closeMatch, confidence: 0.7)
```

### Composition Paths

```sssom
d4d:Creator/principal_investigator → principalInvestigator
  (Traces: Creator.principal_investigator (Person) → principalInvestigator)
```

### Module-Based Mappings

**Motivation Module → d4d: namespace**:
```sssom
d4d:Purpose/response → d4d:purpose (via module semantic grouping)
d4d:AddressingGap/response → d4d:addressingGaps (via module semantic grouping)
```

**Collection Module → rai: namespace**:
```sssom
d4d:CollectionProcess/* → rai:dataCollection* (via module semantic grouping)
d4d:LabelingStrategy/* → rai:dataAnnotation* (via module semantic grouping)
```

## Comparison with Previous Approach

| Aspect | Old Mapping (mappings/*.yaml) | New Structural Mapping |
|--------|------------------------------|----------------------|
| **Method** | Manual hardcoded field-level | Automated structural analysis |
| **Class awareness** | Yes (hardcoded per class) | Yes (via inheritance) |
| **Hierarchy awareness** | No | **Yes** (DatasetProperty lineage) |
| **Composition awareness** | No | **Yes** (follows range: Person) |
| **Module awareness** | Partial (manual sections) | **Yes** (automated grouping) |
| **Type validation** | No | **Yes** (prevents semantic mismatches) |
| **Deduplication** | Manual | **Automatic** |
| **Maintainability** | Low (manual updates) | **High** (regenerates from schema) |
| **Coverage** | ~47 mappings | **142 mappings** |

## Prevented Errors

The structural mapper prevented the following types of errors that occurred in PR #134:

1. **Boolean → Relationship**:
   ```
   ❌ was_inferred_derived (boolean) → prov:wasDerivedFrom (relationship)
   ✅ Prevented by type validation
   ```

2. **String → Date**:
   ```
   ❌ representative_verification (string) → schema:date
   ✅ Prevented by semantic domain checking
   ```

3. **Multivalued → Single**:
   ```
   ❌ missing_value_code (string[]) → schema:variableMeasured (single)
   ✅ Prevented by cardinality validation
   ```

## Usage

### Generate Mappings

```bash
poetry run python src/alignment/generate_structural_mapping.py
```

**Outputs**:
- `data/mappings/d4d_rocrate_structural_mapping.sssom.tsv` - SSSOM format
- `data/mappings/d4d_rocrate_structural_mapping_summary.md` - Human-readable summary

### Read Mappings

```python
import pandas as pd

df = pd.read_csv("data/mappings/d4d_rocrate_structural_mapping.sssom.tsv", sep="\t")

# Filter exact matches
exact = df[df["predicate_id"] == "skos:exactMatch"]

# Filter by confidence
high_conf = df[df["confidence"] >= 0.9]

# Filter by namespace
rai_mappings = df[df["object_id"].str.startswith("rai:")]
```

## Future Enhancements

1. **Ontology Integration**: Fetch formal definitions from LOV for deeper semantic validation
2. **Inverse Mappings**: Generate RO-Crate → D4D mappings
3. **Transformation Templates**: Generate actual data transformation code
4. **Mapping Refinement**: User feedback loop to adjust similarity thresholds
5. **Cross-Schema Validation**: Compare against other D4D implementations

## References

- **SSSOM Specification**: https://mapping-commons.github.io/sssom/
- **D4D Schema**: src/data_sheets_schema/schema/
- **RO-Crate 1.2**: https://www.researchobject.org/ro-crate/1.2-DRAFT/
- **FAIRSCAPE**: data/ro-crate/profiles/fairscape/
