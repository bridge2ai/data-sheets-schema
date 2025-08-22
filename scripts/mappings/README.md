# Schema Mapping Scripts

This directory contains scripts and utilities for generating bidirectional mappings between the LinkML Data Sheets Schema and RO-Crate Datasheet Schema.

## Quick Start

Run the complete mapping generation process:

```bash
bash scripts/mappings/run_mapping_generation.sh
```

## Scripts Overview

### 1. `run_mapping_generation.sh`
**Master script that orchestrates the complete mapping generation process**

- Checks dependencies and source schemas
- Generates mapping specifications 
- Creates data transformation utilities
- Tests transformations with examples
- Generates documentation and reports

```bash
chmod +x scripts/mappings/run_mapping_generation.sh
./scripts/mappings/run_mapping_generation.sh
```

### 2. `generate_schema_mappings.py`
**Creates the core mapping specifications**

Analyzes both schemas and generates:
- `linkml-to-rocrate-mapping.yaml` - LinkML → RO-Crate mapping rules
- `rocrate-to-linkml-mapping.yaml` - RO-Crate → LinkML mapping rules  
- `MAPPING_DOCUMENTATION.md` - Comprehensive mapping documentation

```bash
python scripts/mappings/generate_schema_mappings.py
```

### 3. `transform_data.py`
**Provides bidirectional data transformation capabilities**

Features:
- `SchemaMapper` class for data transformations
- LinkML data → RO-Crate format conversion
- RO-Crate data → LinkML format conversion
- Example transformations and test cases

```bash
python scripts/mappings/transform_data.py
```

## Generated Files

### Mapping Specifications
- `linkml-to-rocrate-mapping.yaml` - Forward mapping rules
- `rocrate-to-linkml-mapping.yaml` - Reverse mapping rules

### Documentation  
- `MAPPING_DOCUMENTATION.md` - Detailed mapping documentation
- `mapping_generation_report.md` - Generation summary report

### Examples
- `example_rocrate.json` - Example RO-Crate output
- `example_linkml.yaml` - Example LinkML output

## Key Mapping Correspondences

| LinkML Schema | RO-Crate Schema |
|---------------|-----------------|
| `Dataset` | `overview` section |
| `Purpose`, `Task` classes | `useCases` section |
| `DataSubset` | `composition.datasets[]` |
| Common metadata | Direct field mappings |

## Dependencies

### Required
- Python 3.7+
- PyYAML
- linkml-runtime (recommended)

### Optional
- linkml-map (for advanced transformations)
- schema-automator (for schema analysis)

## Usage Examples

### Transform LinkML data to RO-Crate format:

```python
from scripts.mappings.transform_data import SchemaMapper

mapper = SchemaMapper()
linkml_data = {...}  # Your LinkML data
rocrate_result = mapper.transform_linkml_to_rocrate(linkml_data)
```

### Transform RO-Crate data to LinkML format:

```python
rocrate_data = {...}  # Your RO-Crate data  
linkml_result = mapper.transform_rocrate_to_linkml(rocrate_data)
```

## Schema Analysis Process

1. **Schema Examination**: Analyze structure and classes in both schemas
2. **Field Mapping**: Identify corresponding fields and data types
3. **Complex Mapping**: Handle structural differences (arrays vs strings, nested objects)
4. **Transformation Logic**: Create bidirectional conversion rules
5. **Validation**: Test with example data and edge cases

## Customization

To customize the mappings:

1. Edit the mapping dictionaries in `generate_schema_mappings.py`
2. Modify transformation logic in `transform_data.py`  
3. Add new mapping rules or handle additional fields
4. Test changes with `run_mapping_generation.sh`

## Integration

These scripts can be integrated into:
- Data processing pipelines
- Schema validation workflows  
- Cross-format data conversion tools
- Documentation generation systems

## Troubleshooting

### Common Issues

**Missing dependencies**: Install required Python packages
```bash
pip install pyyaml linkml-runtime
```

**Schema file not found**: Ensure schemas exist at expected paths:
- `src/data_sheets_schema/schema/data_sheets_schema.yaml`
- `ro-crate/datasheet-schema.json`

**Transformation errors**: Check data format and required fields

**linkml-map issues**: linkml-map format may not be fully compatible; use custom transformation scripts instead

## Contributing

To contribute improvements:
1. Test your changes with existing data
2. Update documentation if mapping rules change
3. Add test cases for new functionality
4. Run the complete generation process to verify compatibility