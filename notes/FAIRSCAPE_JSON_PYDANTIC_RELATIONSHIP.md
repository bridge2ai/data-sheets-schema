# FAIRSCAPE JSON vs Pydantic Classes Relationship

## Overview

The FAIRSCAPE ecosystem has two complementary components:
1. **JSON files** - Data instances (examples, real datasets)
2. **Pydantic classes** - Schema validators (runtime type safety)

## Our FAIRSCAPE Reference File

**Location:** `data/ro-crate/profiles/fairscape/full-ro-crate-metadata.json`

**Source:** CM4AI (Cell Maps for AI) January 2026 data release

**Purpose:**
- Real-world example of FAIRSCAPE RO-Crate metadata
- Reference implementation for D4D-to-RO-Crate alignment
- Canonical pattern for @context, EVI properties, and metadata structure

**Size:** 15 KB (2 @graph entries: metadata descriptor + root dataset)

**Key Features:**
- Uses FAIRSCAPE @context pattern (dict with @vocab, evi, rai, d4d)
- Includes EVI computational provenance properties
- Contains RAI (Responsible AI) metadata
- Demonstrates additionalProperty with PropertyValue pattern
- Real dataset with 19.1 TB, 647 entities, 330 datasets

## FAIRSCAPE Pydantic Models

**Location:** `fairscape_models/` (git submodule)

**Source:** https://github.com/fairscape/fairscape_models

**Purpose:**
- Runtime validation of RO-Crate metadata
- Type safety and auto-completion
- Programmatic generation of valid RO-Crates
- Ensure conformance to FAIRSCAPE schema

**Available Classes:**
- `ROCrateV1_2` - Top-level container
- `ROCrateMetadataFileElem` - Metadata descriptor
- `ROCrateMetadataElem` - Root dataset entity
- `Dataset`, `Software`, `Computation` - Entity types
- `Annotation`, `Experiment`, `MLModel` - Advanced types
- `IdentifierValue`, `PropertyValue` - Supporting types

**JSON Schema Definitions:** `fairscape_models/json-schemas/` (24 schemas)

**Example RO-Crates:** `fairscape_models/tests/test_rocrates/` (3 examples)

## Relationship Summary

| Aspect | JSON File | Pydantic Classes |
|--------|-----------|------------------|
| **Type** | Data instance | Schema validator |
| **Purpose** | Example/reference | Validation/generation |
| **Static/Dynamic** | Static file | Runtime validation |
| **Validation** | None (manual review) | Automatic (Pydantic) |
| **Usage** | Read as reference | Import and use programmatically |
| **Modification** | Edit JSON directly | Generate via Python code |
| **Type Safety** | No | Yes (Python type hints) |

## Equivalence Test

✅ **Validation:** Our JSON file validates against Pydantic models

```python
from fairscape_integration import ROCrateV1_2

# Load JSON file
with open('data/ro-crate/profiles/fairscape/full-ro-crate-metadata.json') as f:
    fairscape_json = json.load(f)

# Validate with Pydantic
rocrate = ROCrateV1_2(**fairscape_json)  # ✓ PASSES

# Round-trip test
roundtrip = rocrate.model_dump(exclude_none=True, by_alias=True)
# Keys match: {'@context', '@graph'}
```

## Recommendation: Use Both

### Keep `full-ro-crate-metadata.json` for:
- Reference implementation
- Documentation examples
- Manual inspection
- Understanding FAIRSCAPE patterns
- Alignment verification

### Use Pydantic classes for:
- D4D → RO-Crate conversion
- Programmatic generation
- Runtime validation
- Type-safe development
- Automated testing

## Implementation Status

✅ **Completed:**
- Cloned fairscape_models as git submodule
- Created integration module: `src/fairscape_integration/`
- Built D4DToFairscapeConverter using Pydantic models
- Validated VOICE D4D → FAIRSCAPE RO-Crate conversion
- Kept full-ro-crate-metadata.json as accessible reference

✅ **Verified:**
- JSON file validates against Pydantic models
- Round-trip conversion preserves structure
- Generated RO-Crates pass Pydantic validation

🔄 **Next Steps:**
- Refactor transformation scripts to use FAIRSCAPE models
- Generate FAIRSCAPE RO-Crates for all 4 projects (AI_READI, CHORUS, CM4AI, VOICE)
- Update profile documentation with FAIRSCAPE integration guide

## File Paths

### Reference JSON (Keep Accessible)
```
data/ro-crate/profiles/fairscape/full-ro-crate-metadata.json
```
**GitHub:** https://github.com/bridge2ai/data-sheets-schema/blob/semantic_xchange/data/ro-crate/profiles/fairscape/full-ro-crate-metadata.json

### Pydantic Models (Programmatic Use)
```
fairscape_models/fairscape_models/rocrate.py
fairscape_models/fairscape_models/dataset.py
fairscape_models/fairscape_models/fairscape_base.py
```

### Integration Module (Our Converter)
```
src/fairscape_integration/__init__.py
src/fairscape_integration/d4d_to_fairscape.py
```

### Generated Examples
```
data/ro-crate/examples/voice_fairscape_test.json
```

## Additional FAIRSCAPE Examples

The fairscape_models repository includes 3 test examples:
```
fairscape_models/tests/test_rocrates/images/ro-crate-metadata.json
fairscape_models/tests/test_rocrates/release/ro-crate-metadata.json
fairscape_models/tests/test_rocrates/LakeDB/ro-crate-metadata.json
```

These can serve as additional reference patterns for different use cases.
