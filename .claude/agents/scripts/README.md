# RO-Crate to D4D Transformation Scripts

This directory contains Python scripts for transforming RO-Crate JSON-LD metadata into D4D YAML datasheets.

## Scripts

### 1. `rocrate_to_d4d.py` (Main Orchestrator)

**Purpose:** Main CLI script that orchestrates the complete transformation pipeline.

**Usage:**
```bash
poetry run python rocrate_to_d4d.py \
  --input ro-crate-metadata.json \
  --output d4d.yaml \
  --mapping mapping.tsv \
  --validate
```

**Options:**
- `-i, --input` - Path to RO-Crate JSON-LD file (required)
- `-o, --output` - Path for output D4D YAML (required)
- `-m, --mapping` - Path to mapping TSV file (required)
- `-s, --schema` - Path to D4D schema (default: data_sheets_schema_all.yaml)
- `--validate` - Validate output against D4D schema
- `--strict` - Fail on missing required fields
- `--no-report` - Skip transformation report

**Output Files:**
- `{output}.yaml` - Generated D4D YAML datasheet
- `transformation_report.txt` - Coverage statistics and unmapped fields
- `{output}_validation_errors.txt` - Schema validation errors (if any)

### 2. `mapping_loader.py` (TSV Mapping Parser)

**Purpose:** Loads and parses the authoritative D4D to RO-Crate field mapping from TSV file.

**Key Functions:**
- `get_covered_fields()` - Get list of D4D fields with FAIRSCAPE coverage
- `get_rocrate_to_d4d_mapping()` - Get RO-Crate → D4D lookup dict
- `get_d4d_to_rocrate_mapping()` - Get D4D → RO-Crate lookup dict
- `is_direct_mapping(field)` - Check if field has 1:1 mapping
- `get_mapping_info(field)` - Get complete mapping details

**Test Usage:**
```bash
poetry run python mapping_loader.py mapping.tsv
```

**Expected Output:**
```
Loaded 82 total mappings
Found 81 FAIRSCAPE-covered mappings
Created 81 D4D→RO-Crate lookups
Created 66 RO-Crate→D4D lookups
```

### 3. `rocrate_parser.py` (JSON-LD Parser)

**Purpose:** Parses RO-Crate JSON-LD structure and extracts metadata properties.

**Key Functions:**
- `get_root_dataset()` - Extract root Dataset entity from @graph
- `get_property(path)` - Get property using dot-notation (e.g., `author[0].name`)
- `extract_all_properties()` - Flatten all properties to dict
- `get_unmapped_properties(mapped)` - Find properties not in mapping
- `get_entities_by_type(type)` - Get all entities of a specific @type

**Test Usage:**
```bash
poetry run python rocrate_parser.py ro-crate-metadata.json
```

**Expected Output:**
```
=== Root Dataset ===
@id: ./
@type: Dataset
name: Dataset Name
description: Dataset description
```

### 4. `d4d_builder.py` (D4D YAML Builder)

**Purpose:** Builds D4D YAML structure by applying mappings and transformations to RO-Crate data.

**Key Functions:**
- `build_dataset(parser)` - Build complete D4D Dataset from RO-Crate
- `apply_field_transformation(field, value)` - Transform values based on field type
- `set_field(field, value)` - Manually set a D4D field
- `get_dataset()` - Get complete D4D dataset dict

**Transformations:**
- **Dates:** ISO 8601 → YYYY-MM-DD
- **Integers:** String → int
- **Lists:** Handle arrays and extract from complex objects
- **Enums:** Map to D4D enum values (e.g., compression formats)
- **URIs:** Ensure proper URI format
- **Person/Org:** Extract names from entities
- **Booleans:** String → bool

**Test Usage:**
```bash
poetry run python d4d_builder.py mapping.tsv ro-crate-metadata.json
```

**Expected Output:**
```
Building D4D dataset from 81 mapped fields...
Successfully mapped 28/81 fields

=== Built D4D Dataset ===
Total fields: 28
Sample fields:
  title: Dataset Name
  description: Dataset description
  ...
```

### 5. `validator.py` (Schema Validator Wrapper)

**Purpose:** Wraps `linkml-validate` for D4D YAML schema validation with error parsing and fix suggestions.

**Key Functions:**
- `validate_d4d_yaml(file)` - Validate D4D YAML against schema
- `parse_validation_errors(output)` - Parse error messages
- `suggest_fixes(errors)` - Suggest fixes for common errors
- `get_validation_summary(is_valid, output)` - Generate summary

**Error Types Detected:**
- `missing_required` - Required fields not present
- `type_mismatch` - Wrong data type (e.g., string vs array)
- `invalid_enum` - Value not in permissible values
- `format_error` - Invalid format (e.g., date, URI)

**Test Usage:**
```bash
poetry run python validator.py schema.yaml d4d.yaml
```

**Expected Output:**
```
✓ Validation passed - D4D YAML is valid against schema
```

or

```
✗ Validation failed

Found 3 error(s):

1. 'title' is a required field
2. '2024-01-15' is not a 'date-time' in /created_on
3. 'invalid' is not in permissible values [GZIP, TAR, ZIP]

Suggested fixes:

1. Add required field 'title' to your D4D YAML
2. Fix date format for 'created_on'. Use YYYY-MM-DD format.
3. Fix enum value for 'compression'. Use one of the permissible values.
```

## Dependencies

All scripts require:
```bash
poetry add pyyaml linkml-runtime linkml
```

## Testing

Each script can be tested independently with sample data:

```bash
# Test mapping loader
poetry run python mapping_loader.py \
  "data/ro-crate_mapping/D4D - RO-Crate - RAI Mappings.xlsx - Class Alignment.tsv"

# Test RO-Crate parser
poetry run python rocrate_parser.py \
  data/test/minimal-ro-crate.json

# Test D4D builder
poetry run python d4d_builder.py \
  "data/ro-crate_mapping/D4D - RO-Crate - RAI Mappings.xlsx - Class Alignment.tsv" \
  data/test/minimal-ro-crate.json

# Test validator
poetry run python validator.py \
  src/data_sheets_schema/schema/data_sheets_schema_all.yaml \
  data/test/minimal_d4d.yaml

# Test full transformation
poetry run python rocrate_to_d4d.py \
  --input data/test/minimal-ro-crate.json \
  --output data/test/minimal_d4d.yaml \
  --mapping "data/ro-crate_mapping/D4D - RO-Crate - RAI Mappings.xlsx - Class Alignment.tsv" \
  --validate
```

## Makefile Integration

Instead of running scripts directly, use Makefile targets:

```bash
# Transform RO-Crate to D4D
make rocrate-to-d4d INPUT=rocrate.json OUTPUT=d4d.yaml

# Test transformation with minimal example
make test-rocrate-transform
```

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│ rocrate_to_d4d.py (Main Orchestrator)                       │
│   ├─ CLI argument parsing                                   │
│   ├─ Coordinate transformation pipeline                     │
│   └─ Generate reports and validation                        │
└────────────────┬────────────────────────────────────────────┘
                 │
        ┌────────┴────────┬────────────┬────────────┐
        │                 │            │            │
        ▼                 ▼            ▼            ▼
┌───────────────┐  ┌──────────┐  ┌─────────┐  ┌──────────┐
│mapping_loader │  │rocrate_  │  │d4d_     │  │validator │
│              │  │parser    │  │builder  │  │         │
│- Load TSV    │  │- Parse   │  │- Build  │  │- Validate│
│- Filter      │  │  JSON-LD │  │  D4D    │  │- Parse   │
│- Lookups     │  │- Extract │  │- Apply  │  │  errors  │
│              │  │  props   │  │  xforms │  │- Suggest │
└───────────────┘  └──────────┘  └─────────┘  └──────────┘
```

## Extension Points

### Adding New Field Transformations

Edit `d4d_builder.py`, add to `apply_field_transformation()`:

```python
if field_name == 'custom_field':
    return custom_transformation(value)
```

### Adding New RO-Crate Properties

Edit TSV mapping file:
```tsv
Dataset  new_field  str  ...  new_rocrate_property  1  1  0
```

### Adding Custom Validation Rules

Edit `validator.py`, add to `parse_validation_errors()`:

```python
patterns.append(r"your custom error pattern")
```

## Performance

- Small RO-Crates (<1KB): ~2 seconds
- Typical RO-Crates (~1MB): ~2-15 seconds
- Large RO-Crates (>10MB): ~10-30 seconds

**Bottlenecks:**
- JSON parsing: ~20% of time
- Property extraction: ~30% of time
- Transformation: ~30% of time
- Validation: ~20% of time

**Optimization tips:**
- Cache `MappingLoader` for batch processing
- Skip validation for large batches
- Use `--no-report` to skip unmapped field report

## Known Issues

1. **Schema Type Mismatches:** Some D4D fields expect arrays, transformation returns strings
   - Affected: `tasks`, `acquisition_methods`, `collection_mechanisms`, etc.
   - Fix: Update `d4d_builder.py` to check D4D schema for expected types

2. **Date Format:** D4D expects `date-time` (ISO 8601), transformation produces `date` (YYYY-MM-DD)
   - Affected: `created_on`, `issued`
   - Fix: Either preserve ISO 8601 or update D4D schema

3. **Missing `id` Field:** D4D requires `id`, not in RO-Crate mapping
   - Fix: Generate `id` automatically from DOI or title

See `notes/ROCRATE_IMPLEMENTATION_SUMMARY.md` for complete details.

## Documentation

- **Skill file:** `.claude/agents/d4d-rocrate.md`
- **Mapping file:** `data/ro-crate_mapping/D4D - RO-Crate - RAI Mappings.xlsx - Class Alignment.tsv`
- **Implementation summary:** `notes/ROCRATE_IMPLEMENTATION_SUMMARY.md`
- **Usage guide:** `CLAUDE.md` (RO-Crate section)

## Support

For issues or questions:
1. Check skill documentation: `.claude/agents/d4d-rocrate.md`
2. Review implementation summary: `notes/ROCRATE_IMPLEMENTATION_SUMMARY.md`
3. Test individual scripts with sample data
4. Check validation errors in output files
