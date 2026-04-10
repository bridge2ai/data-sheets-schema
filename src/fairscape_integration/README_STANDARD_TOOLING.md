# Standard SSSOM and LinkML-Map Integration

This document describes the integration with standard `sssom-py` and `linkml-map` packages for D4D ↔ RO-Crate mappings.

## Overview

The FAIRSCAPE integration now supports two approaches:

1. **Standard Packages** (Recommended): Use `sssom-py` and `linkml-map` for SSSOM operations
2. **Custom Implementation**: Fallback to custom `SSSOMReader` when packages unavailable

## Installation

### Install Standard Packages

```bash
# Install development dependencies (includes sssom and linkml-map)
poetry install --with dev

# Or install individually
pip install sssom linkml-map
```

### Verify Installation

```python
from src.fairscape_integration.utils import SSSOMIntegration, LinkMLMapIntegration

# Check if standard packages are available
print(f"SSSOM available: {SSSOMIntegration.is_sssom_available()}")
print(f"LinkML-Map available: {LinkMLMapIntegration.is_available()}")
```

## Usage

### 1. SSSOM Integration

#### Basic Usage

```python
from src.fairscape_integration.utils import SSSOMIntegration

# Load SSSOM file (uses sssom-py if available, falls back to custom reader)
integration = SSSOMIntegration('data/mappings/d4d_rocrate_structural_mapping.sssom.tsv')

# Query mappings
exact_matches = integration.get_exact_matches()
mappings = integration.get_mappings_by_subject('d4d:title')

# Get statistics
stats = integration.get_statistics()
print(f"Total mappings: {stats['total_mappings']}")
print(f"Predicates: {stats['predicate_counts']}")
```

#### Advanced Queries

```python
# Get all subjects and objects
subjects = integration.get_subjects()
objects = integration.get_objects()

# Filter by confidence
high_confidence = integration.filter_by_confidence(0.9)

# Get mappings by predicate
close_matches = integration.get_mappings_by_predicate('skos:closeMatch')
```

#### Export to File (Requires sssom-py)

```python
if SSSOMIntegration.is_sssom_available():
    integration.export_to_file('output.sssom.tsv', format='tsv')
```

### 2. LinkML-Map Integration

#### Schema Transformation

```python
from src.fairscape_integration.utils import LinkMLMapIntegration

# Initialize with schemas and mappings
transformer = LinkMLMapIntegration(
    source_schema='path/to/rocrate_schema.yaml',
    target_schema='src/data_sheets_schema/schema/data_sheets_schema_all.yaml',
    sssom_mappings='data/mappings/d4d_rocrate_structural_mapping.sssom.tsv',
    verbose=True
)

# Transform data
source_data = {
    'name': 'Test Dataset',
    'description': 'A test dataset',
    'keywords': ['test', 'data']
}

transformed = transformer.transform(source_data, target_class='Dataset')
print(transformed)
```

#### File-to-File Transformation

```python
transformer.transform_file(
    input_file='input_rocrate.json',
    output_file='output_d4d.yaml',
    target_class='Dataset',
    input_format='json',
    output_format='yaml'
)
```

### 3. TSV to SSSOM Conversion

Convert legacy TSV mapping files to standard SSSOM format:

```python
from src.fairscape_integration.utils import create_sssom_from_tsv_mapping

create_sssom_from_tsv_mapping(
    tsv_mapping_path='data/ro-crate_mapping/d4d_rocrate_mapping_v2_semantic.tsv',
    output_sssom_path='output.sssom.tsv',
    subject_prefix='d4d',
    object_prefix='rocrate'
)
```

## Implementation Details

### Fallback Behavior

Both integration modules automatically detect if standard packages are available:

- **sssom-py available**: Uses standard `sssom.parsers.parse_sssom_table()`
- **sssom-py unavailable**: Falls back to custom `SSSOMReader` (no external dependencies)
- **linkml-map available**: Full schema transformation capabilities
- **linkml-map unavailable**: Raises informative error with installation instructions

### Custom Reader vs Standard Package

| Feature | Custom Reader | sssom-py |
|---------|--------------|----------|
| Read SSSOM TSV | ✅ | ✅ |
| Query mappings | ✅ | ✅ |
| Filter by confidence | ✅ | ✅ |
| Statistics | ✅ | ✅ |
| Export to file | ❌ | ✅ |
| RDF export | ❌ | ✅ |
| SSSOM validation | ❌ | ✅ |
| External dependencies | None | sssom, pandas |

## Examples

### Example 1: Find All Exact Matches for D4D Field

```python
integration = SSSOMIntegration('data/mappings/d4d_rocrate_structural_mapping.sssom.tsv')

# Get RO-Crate property for D4D field
mappings = integration.get_mappings_by_subject('d4d:Metadata/title')
for mapping in mappings:
    print(f"D4D: {mapping['subject_id']} -> RO-Crate: {mapping['object_id']}")
    print(f"Predicate: {mapping['predicate_id']}")
    print(f"Confidence: {mapping['confidence']}")
```

### Example 2: Generate Mapping Coverage Report

```python
integration = SSSOMIntegration('data/mappings/d4d_rocrate_comprehensive.sssom.tsv')

stats = integration.get_statistics()

print("="*80)
print("SSSOM Mapping Coverage Report")
print("="*80)
print(f"Total mappings: {stats['total_mappings']}")
print(f"Unique D4D fields: {stats['unique_subjects']}")
print(f"Unique RO-Crate properties: {stats['unique_objects']}")
print()
print("Mapping quality:")
for predicate, count in stats['predicate_counts'].items():
    print(f"  {predicate}: {count}")
print()
if 'avg_confidence' in stats:
    print(f"Average confidence: {stats['avg_confidence']:.2%}")
```

### Example 3: Convert TSV Mappings to SSSOM for All Projects

```python
from pathlib import Path

# Find all TSV mapping files
mapping_files = Path('data/ro-crate_mapping').glob('*.tsv')

for tsv_file in mapping_files:
    output_sssom = tsv_file.parent / f"{tsv_file.stem}.sssom.tsv"
    
    print(f"Converting {tsv_file.name}...")
    create_sssom_from_tsv_mapping(
        str(tsv_file),
        str(output_sssom)
    )
    print(f"  → {output_sssom.name}")
```

## CLI Integration

The standard tools are integrated into the `fairscape-cli`:

```bash
# Use SSSOM mappings with transformation
fairscape-cli transform input.json -o output.yaml \
    -m data/mappings/d4d_rocrate_structural_mapping.sssom.tsv \
    --validate

# Merge multiple RO-Crates using SSSOM-guided field resolution
fairscape-cli merge file1.json file2.json \
    -o merged.yaml \
    -m data/mappings/d4d_rocrate_structural_mapping.sssom.tsv \
    --report
```

## Testing

All integration modules include comprehensive tests:

```bash
# Test SSSOM integration (works with or without sssom-py)
python -m unittest tests.test_fairscape_integration.test_sssom_integration

# Test LinkML-Map integration
python -m unittest tests.test_fairscape_integration.test_linkml_map_integration

# Run all integration tests
python -m unittest discover tests/test_fairscape_integration
```

## Benefits of Standard Tooling

1. **Interoperability**: SSSOM files work with other LinkML/semantic web tools
2. **Validation**: Built-in SSSOM validation ensures mapping quality
3. **Export**: Export to multiple formats (TSV, RDF, JSON)
4. **Community**: Standard formats enable sharing with broader community
5. **Features**: Access to advanced features (reasoning, validation, etc.)

## Migration Path

Current users of custom `SSSOMReader` can migrate gradually:

1. **No changes needed**: Existing code continues to work
2. **Install packages**: `poetry install --with dev`
3. **Update imports**: Change to `SSSOMIntegration` (optional)
4. **Test**: All existing functionality preserved
5. **Extend**: Use new features from sssom-py as needed

The integration layer ensures backward compatibility while enabling access to standard tooling.
