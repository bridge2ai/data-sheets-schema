# Deprecated RO-Crate Files

**Date**: 2026-03-19
**Reason**: Migration to FAIRSCAPE Pydantic models

## What Changed

This directory contains deprecated custom RO-Crate JSON-LD files that have been replaced by FAIRSCAPE model-based implementations.

### Deprecated Files

**custom-examples/**
- `d4d-rocrate-minimal.json` - Custom minimal example
- `d4d-rocrate-basic.json` - Custom basic example  
- `d4d-rocrate-complete.json` - Custom complete example

**profile-v1/**
- `profile.json` - Custom profile descriptor

### Migration

These files were replaced by:
- **FAIRSCAPE models**: Python Pydantic models from `fairscape_models/`
- **Validation**: JSON schemas from `fairscape_models/json-schemas/`
- **Integration**: `src/fairscape_integration/` module

### Why Deprecated

1. **Validation**: FAIRSCAPE models provide runtime Pydantic validation
2. **Consistency**: Align with FAIRSCAPE reference implementation (CM4AI)
3. **Maintainability**: Use upstream models instead of custom JSON
4. **Type Safety**: Python type hints throughout
5. **Standards**: Use canonical FAIRSCAPE JSON schemas

### For Users

**Old approach** (deprecated):
```json
{
  "@context": ["https://w3id.org/ro/crate/1.2/context"],
  "@graph": [...]
}
```

**New approach** (use FAIRSCAPE models):
```python
from fairscape_integration import ROCrateV1_2, Dataset

# Create with validation
rocrate = ROCrateV1_2(
    graph=[
        Dataset(
            id="./",
            name="My Dataset",
            ...
        )
    ]
)

# Export to JSON-LD
rocrate_json = rocrate.model_dump_json(indent=2)
```

### References

- FAIRSCAPE models: `fairscape_models/`
- Integration docs: `src/fairscape_integration/README.md`
- Migration plan: `notes/FAIRSCAPE_MIGRATION.md`
