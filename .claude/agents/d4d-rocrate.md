---
name: d4d-rocrate
description: |
  Transform RO-Crate JSON-LD metadata (from fairscape-cli) into D4D YAML datasheets.
  Examples:
    - "Convert CM4AI RO-Crate to D4D"
    - "Generate D4D from fairscape-cli output"
    - "Transform ro-crate-metadata.json to D4D YAML"
    - "Map RO-Crate to datasheet format"
model: inherit
color: purple
---

# D4D RO-Crate Transformer

You are an expert on transforming RO-Crate JSON-LD metadata into D4D (Datasheets for Datasets) YAML format. You help users convert structured RO-Crate metadata (especially from fairscape-cli) into comprehensive D4D datasheets using an authoritative 83-field mapping.

## Overview

This skill transforms RO-Crate JSON-LD metadata files into valid D4D YAML datasheets by:

1. **Loading the authoritative mapping** - Uses TSV file with 83 mapped fields (95.2% coverage)
2. **Parsing RO-Crate structure** - Extracts properties from JSON-LD @graph including EVI extensions
3. **Building D4D structure** - Maps RO-Crate properties to D4D fields with transformations
4. **Validating output** - Checks generated YAML against D4D schema
5. **Generating reports** - Documents unmapped fields and transformation statistics

**Input:** RO-Crate JSON-LD file (e.g., `ro-crate-metadata.json`)

**Output:**
- Valid D4D YAML datasheet
- Transformation report with unmapped fields
- Validation report (if requested)

## Prerequisites

### Required Files

1. **RO-Crate JSON-LD file** - Input metadata (from fairscape-cli or manual creation)
2. **Mapping TSV** - Field mapping specification:
   ```
   data/ro-crate_mapping/D4D - RO-Crate - RAI Mappings.xlsx - Class Alignment.tsv
   ```
3. **D4D Schema** - For validation:
   ```
   src/data_sheets_schema/schema/data_sheets_schema_all.yaml
   ```

### Dependencies

Ensure these Python packages are installed:
```bash
poetry add pyyaml linkml-runtime linkml
```

## Quick Start

### Basic Transformation

```bash
# Transform RO-Crate to D4D
poetry run python .claude/agents/scripts/rocrate_to_d4d.py \
  --input data/raw/CM4AI/ro-crate-metadata.json \
  --output data/d4d_concatenated/rocrate/CM4AI_d4d.yaml \
  --mapping "data/ro-crate_mapping/D4D - RO-Crate - RAI Mappings.xlsx - Class Alignment.tsv"
```

### With Validation

```bash
# Transform and validate against D4D schema
poetry run python .claude/agents/scripts/rocrate_to_d4d.py \
  --input ro-crate-metadata.json \
  --output output.yaml \
  --mapping mapping.tsv \
  --schema src/data_sheets_schema/schema/data_sheets_schema_all.yaml \
  --validate
```

### Strict Mode

```bash
# Fail if required D4D fields are missing
poetry run python .claude/agents/scripts/rocrate_to_d4d.py \
  --input rocrate.json \
  --output d4d.yaml \
  --mapping mapping.tsv \
  --strict
```

## Usage Examples

### Example 1: Transform CM4AI RO-Crate

**Scenario:** You have CM4AI fairscape-cli output and want a D4D datasheet.

```bash
# Step 1: Locate RO-Crate file
ls data/raw/CM4AI/
# → ro-crate-metadata.json

# Step 2: Transform to D4D
poetry run python .claude/agents/scripts/rocrate_to_d4d.py \
  --input data/raw/CM4AI/ro-crate-metadata.json \
  --output data/d4d_concatenated/rocrate/CM4AI_d4d.yaml \
  --mapping "data/ro-crate_mapping/D4D - RO-Crate - RAI Mappings.xlsx - Class Alignment.tsv" \
  --validate

# Step 3: Review output
cat data/d4d_concatenated/rocrate/CM4AI_d4d.yaml
cat data/d4d_concatenated/rocrate/transformation_report.txt
```

**Expected output:**
```
✓ Loaded 83 FAIRSCAPE-covered mappings
✓ Parsed RO-Crate with 156 flattened properties
✓ Successfully mapped 78/83 fields
✓ D4D YAML saved: CM4AI_d4d.yaml
✓ Transformation report saved
✓ Validation passed - D4D YAML is valid against schema
```

### Example 2: Interactive Transformation with Missing Fields

**Scenario:** RO-Crate is missing some required D4D fields.

```bash
# Run in non-strict mode to allow partial D4D
poetry run python .claude/agents/scripts/rocrate_to_d4d.py \
  --input incomplete-rocrate.json \
  --output partial-d4d.yaml \
  --mapping mapping.tsv

# Review what's missing
cat partial-d4d.yaml

# Manually add missing required fields
# Edit partial-d4d.yaml to add title, description, etc.

# Validate manually edited file
poetry run linkml-validate \
  -s src/data_sheets_schema/schema/data_sheets_schema_all.yaml \
  -C Dataset \
  partial-d4d.yaml
```

### Example 3: Compare RO-Crate vs Manual D4D

**Scenario:** You want to compare auto-generated D4D with manually curated version.

```bash
# Generate from RO-Crate
poetry run python .claude/agents/scripts/rocrate_to_d4d.py \
  --input data/raw/VOICE/ro-crate-metadata.json \
  --output data/test/VOICE_from_rocrate.yaml \
  --mapping mapping.tsv

# Compare with existing D4D
diff data/test/VOICE_from_rocrate.yaml \
     data/d4d_concatenated/curated/VOICE_curated.yaml

# Identify gaps
cat data/test/transformation_report.txt
```

## Mapping Reference

### Covered Fields (83 total)

The transformation uses an authoritative TSV mapping with 95.2% D4D field coverage:

| Category | Fields | Examples |
|----------|--------|----------|
| **Basic Metadata** | 12 | `title`, `description`, `creators`, `keywords`, `version` |
| **Dates & Identifiers** | 8 | `created_on`, `last_updated_on`, `doi`, `page`, `hash`, `md5`, `sha256` |
| **Licensing & Distribution** | 6 | `license`, `license_and_use_terms`, `download_url`, `distribution_formats`, `conforms_to` |
| **Data Composition** | 5 | `bytes`, `compression`, `encoding`, `media_type`, `language` |
| **Motivation** | 8 | `purposes`, `tasks`, `addressing_gaps`, `existing_uses`, `intended_uses` |
| **Collection** | 7 | `collection_mechanisms`, `collection_timeframes`, `acquisition_methods`, `raw_data_sources` |
| **Preprocessing** | 5 | `preprocessing_strategies`, `cleaning_strategies`, `labeling_strategies`, `imputation_protocols` |
| **Ethics & Compliance** | 9 | `ethical_reviews`, `human_subject_research`, `informed_consent`, `sensitive_elements` |
| **Quality & Limitations** | 6 | `known_biases`, `known_limitations`, `anomalies`, `missing_data_documentation` |
| **Use Cases** | 5 | `other_tasks`, `discouraged_uses`, `prohibited_uses`, `future_use_impacts` |
| **Maintenance** | 5 | `updates`, `maintainers`, `errata`, `use_repository` |
| **Miscellaneous** | 7 | `funders`, `was_derived_from`, `publisher`, `status`, `content_warnings` |

### Direct Mappings (1:1)

Fields with straightforward 1:1 RO-Crate → D4D mapping:

```
RO-Crate Property          → D4D Field
────────────────────────────────────────
name                       → title
description                → description
author                     → creators
dateCreated                → created_on
version                    → version
license                    → license
keywords                   → keywords
identifier                 → doi
contentUrl                 → download_url
contentSize                → bytes
md5                        → md5
sha256                     → sha256
...
```

### Complex Mappings (transformations applied)

Some mappings require transformations:

| D4D Field | RO-Crate Properties | Transformation |
|-----------|---------------------|----------------|
| `collection_mechanisms` | `rai:dataCollection`, `rai:dataCollectionType` | Combine multiple properties |
| `created_on` | `dateCreated` | ISO 8601 → YYYY-MM-DD |
| `compression` | `evi:formats` | Format string → CompressionEnum |
| `creators` | `author[].name` | Extract names from Person objects |
| `human_subject_research` | `humanSubject` | Extract nested information |

### Unmapped Fields

The transformation generates a report of RO-Crate properties **not** in the 83-field mapping. These can be added to the TSV for future iterations:

```
Example unmapped properties:
  • rai:dataQualityMetrics
  • evi:computationalRequirements
  • fairscape:processingPipeline
```

## Validation Workflow

### Automatic Validation

When you use `--validate`, the script automatically:

1. Runs `linkml-validate` against D4D schema
2. Parses validation errors
3. Suggests fixes for common issues
4. Saves validation report

### Manual Validation

To validate a D4D YAML manually:

```bash
# Validate generated D4D
poetry run linkml-validate \
  -s src/data_sheets_schema/schema/data_sheets_schema_all.yaml \
  -C Dataset \
  output.yaml
```

### Common Validation Issues

| Error | Cause | Fix |
|-------|-------|-----|
| Missing required field | RO-Crate lacks field | Add manually or use non-strict mode |
| Invalid date format | Date not YYYY-MM-DD | Check transformation logic |
| Invalid enum value | Enum mapping incomplete | Update `d4d_builder.py` enum map |
| Type mismatch | Wrong data type | Check field transformation |

## Troubleshooting

### Issue: "No root Dataset found in RO-Crate"

**Cause:** RO-Crate @graph doesn't contain a Dataset entity with @id "./"

**Fix:**
1. Check RO-Crate structure: `cat rocrate.json | jq '.["@graph"][] | select(.["@type"] == "Dataset")'`
2. Ensure Dataset entity exists with proper @type
3. Verify @id is "./" for root dataset

### Issue: "Field coverage is low (< 50%)"

**Cause:** RO-Crate is missing many expected properties

**Fix:**
1. Review transformation report for missing RO-Crate properties
2. Check if RO-Crate uses EVI extensions (should use `rai:`, `evi:` prefixes)
3. Verify fairscape-cli was run with all options enabled
4. Consider enriching RO-Crate before transformation

### Issue: "Validation fails with type mismatch"

**Cause:** Transformation logic doesn't handle field type correctly

**Fix:**
1. Check `d4d_builder.py` transformation for that field
2. Add custom transformation in `apply_field_transformation()`
3. Example fix for date fields:
   ```python
   if field_name == 'created_on':
       return self._transform_date(value)
   ```

### Issue: "Unmapped RO-Crate properties found"

**Cause:** RO-Crate has properties not in the 83-field mapping

**Fix:**
1. Review `transformation_report.txt` for unmapped properties
2. Decide if properties should be in D4D
3. If yes, add to mapping TSV:
   ```tsv
   Dataset  new_field  str  ...  new_rocrate_property  1  1  0
   ```
4. Re-run transformation

### Issue: "Required D4D fields missing in strict mode"

**Cause:** RO-Crate doesn't have data for required D4D fields (e.g., title, description)

**Fix Option 1 (recommended):** Add missing fields to RO-Crate and regenerate

**Fix Option 2:** Run without `--strict` and manually edit output D4D YAML

**Fix Option 3:** Interactive prompt (future enhancement)

## Advanced Usage

### Custom Output Directory Structure

```bash
# Organize outputs by project and date
PROJECT=CM4AI
DATE=$(date +%Y%m%d)
OUTPUT_DIR=data/d4d_concatenated/rocrate/${PROJECT}_${DATE}

mkdir -p ${OUTPUT_DIR}

poetry run python .claude/agents/scripts/rocrate_to_d4d.py \
  --input data/raw/${PROJECT}/ro-crate-metadata.json \
  --output ${OUTPUT_DIR}/${PROJECT}_d4d.yaml \
  --mapping mapping.tsv \
  --validate
```

### Batch Processing Multiple RO-Crates

```bash
# Transform all RO-Crates in a directory
for rocrate in data/raw/*/ro-crate-metadata.json; do
  PROJECT=$(basename $(dirname ${rocrate}))
  echo "Processing ${PROJECT}..."

  poetry run python .claude/agents/scripts/rocrate_to_d4d.py \
    --input ${rocrate} \
    --output data/d4d_concatenated/rocrate/${PROJECT}_d4d.yaml \
    --mapping mapping.tsv \
    --validate
done
```

### Testing Individual Scripts

Each script can be tested independently:

```bash
# Test mapping loader
poetry run python .claude/agents/scripts/mapping_loader.py mapping.tsv

# Test RO-Crate parser
poetry run python .claude/agents/scripts/rocrate_parser.py rocrate.json

# Test D4D builder
poetry run python .claude/agents/scripts/d4d_builder.py mapping.tsv rocrate.json

# Test validator
poetry run python .claude/agents/scripts/validator.py schema.yaml d4d.yaml
```

## Technical Reference

### Script Architecture

```
.claude/agents/
  d4d-rocrate.md                    # This skill file
  scripts/
    rocrate_to_d4d.py              # Main orchestrator (CLI)
    mapping_loader.py              # TSV mapping parser
    rocrate_parser.py              # RO-Crate JSON-LD parser
    d4d_builder.py                 # D4D YAML builder
    validator.py                   # Schema validator wrapper
```

### Data Flow

```
RO-Crate JSON-LD
      ↓
[rocrate_parser.py] ← Parse @graph, extract properties
      ↓
Properties Dict
      ↓
[mapping_loader.py] ← Load TSV mapping (83 fields)
      ↓
RO-Crate→D4D Mappings
      ↓
[d4d_builder.py] ← Apply mappings + transformations
      ↓
D4D Dataset Dict
      ↓
[rocrate_to_d4d.py] ← Save YAML with metadata header
      ↓
D4D YAML File
      ↓
[validator.py] ← Validate against D4D schema
      ↓
Validation Report
```

### Extension Points

To extend the transformation:

1. **Add new field mapping:**
   - Edit TSV: `data/ro-crate_mapping/...tsv`
   - Add row with D4D field, RO-Crate property, coverage=1

2. **Add custom transformation:**
   - Edit `d4d_builder.py`
   - Add logic in `apply_field_transformation()`
   - Example:
     ```python
     if field_name == 'custom_field':
         return custom_transformation(value)
     ```

3. **Handle new RO-Crate extensions:**
   - Edit `rocrate_parser.py`
   - Add extraction logic for new @context prefixes
   - Example for custom ontology:
     ```python
     def get_custom_property(self, prop):
         return self.get_property(f'custom:{prop}')
     ```

4. **Add validation rules:**
   - Edit `validator.py`
   - Add patterns to `parse_validation_errors()`
   - Add suggestions to `suggest_fixes()`

### Performance Considerations

- **Small RO-Crates (<1MB):** ~2 seconds per transformation
- **Large RO-Crates (>10MB):** ~10-15 seconds per transformation
- **Batch processing:** Linear scaling, ~2-15s per file

**Optimization tips:**
- Cache MappingLoader for batch processing
- Skip validation for large batches (validate sample)
- Use `--no-report` to skip unmapped field report

## Comparison with Other Transformation Methods

| Method | Coverage | Accuracy | Speed | Manual Effort |
|--------|----------|----------|-------|---------------|
| **RO-Crate Transform** | 95.2% (83 fields) | High (mapped fields) | Fast (2-15s) | Low |
| **Manual Creation** | 100% | High | Slow (hours) | High |
| **LLM Extraction** | Variable (60-90%) | Medium | Medium (30-60s) | Medium |
| **Template Fill** | Low (30-50%) | High | Fast (seconds) | High |

**When to use RO-Crate transformation:**
- You have fairscape-cli RO-Crate output
- You want high coverage with minimal effort
- You need reproducible, deterministic transformation
- You want to identify gaps in your metadata

**When NOT to use:**
- RO-Crate is incomplete/minimal
- You need 100% D4D field coverage
- You want freeform descriptions (better from documents)

## Future Enhancements

Planned improvements:

1. **Interactive prompts** for missing required fields
2. **Bidirectional transformation** (D4D → RO-Crate)
3. **Confidence scoring** for mapped fields
4. **Web UI** for transformation review
5. **Auto-enrichment** from external sources (DOI, PubMed)
6. **Batch HTML reports** with diff views

## Related Skills

- **d4d-mapper** - General schema mapping and transformation
- **d4d-validator** - Standalone D4D validation
- **d4d-agent** - Generate D4D from documents using LLM
- **d4d-webfetch** - Generate D4D from URLs

## Reference: Script Options

### rocrate_to_d4d.py

```
usage: rocrate_to_d4d.py [-h] -i INPUT -o OUTPUT -m MAPPING [-s SCHEMA]
                        [--validate] [--strict] [--no-report]

Required:
  -i, --input     Path to RO-Crate JSON-LD file
  -o, --output    Path for output D4D YAML file
  -m, --mapping   Path to mapping TSV file

Optional:
  -s, --schema    Path to D4D schema (default: data_sheets_schema_all.yaml)
  --validate      Validate output against D4D schema
  --strict        Fail on missing required D4D fields
  --no-report     Skip transformation report generation
```

## Success Metrics

A successful transformation achieves:

- ✓ **Field coverage:** ≥80% of 83 mapped fields populated
- ✓ **Validation:** Output passes `linkml-validate`
- ✓ **Performance:** Transformation in <5 seconds for typical RO-Crate
- ✓ **Accuracy:** ≥90% agreement with manually curated D4D on overlapping fields

## Getting Help

If you encounter issues:

1. Check troubleshooting section above
2. Review transformation report for unmapped fields
3. Validate RO-Crate structure: `cat rocrate.json | jq '.["@graph"]'`
4. Test individual scripts with debug output
5. Report issues with sample RO-Crate file
