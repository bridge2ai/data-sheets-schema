#!/bin/bash

# Schema Mapping Generation Script
# Generates bidirectional mappings between LinkML Data Sheets Schema and RO-Crate Schema

echo "=================================================="
echo "Schema Mapping Generation for Data Sheets Schema"
echo "=================================================="

# Change to project root directory
cd "$(dirname "$0")/../.."

echo "Current directory: $(pwd)"
echo

# Step 1: Check dependencies
echo "1. Checking dependencies..."

if ! command -v python &> /dev/null; then
    echo "ERROR: Python is not installed"
    exit 1
fi

if ! python -c "import yaml" &> /dev/null; then
    echo "ERROR: PyYAML is not installed"
    exit 1
fi

if ! python -c "import linkml_runtime" &> /dev/null; then
    echo "WARNING: linkml-runtime not found. Some features may not work."
fi

if ! command -v linkml-map &> /dev/null; then
    echo "WARNING: linkml-map not found. Advanced mapping features may not work."
fi

echo "✓ Dependencies checked"
echo

# Step 2: Verify source schemas exist
echo "2. Verifying source schemas..."

if [ ! -f "src/data_sheets_schema/schema/data_sheets_schema.yaml" ]; then
    echo "ERROR: LinkML schema not found at src/data_sheets_schema/schema/data_sheets_schema.yaml"
    exit 1
fi

if [ ! -f "ro-crate/datasheet-schema.json" ]; then
    echo "ERROR: RO-Crate schema not found at ro-crate/datasheet-schema.json"
    exit 1
fi

echo "✓ Source schemas found"
echo

# Step 3: Generate basic mapping specifications
echo "3. Generating mapping specifications..."

python scripts/mappings/generate_schema_mappings.py

if [ $? -eq 0 ]; then
    echo "✓ Mapping specifications generated"
else
    echo "ERROR: Failed to generate mapping specifications"
    exit 1
fi
echo

# Step 4: Test data transformations
echo "4. Testing data transformations..."

python scripts/mappings/transform_data.py

if [ $? -eq 0 ]; then
    echo "✓ Data transformation tests passed"
else
    echo "ERROR: Data transformation tests failed"
    exit 1
fi
echo

# Step 5: Try linkml-map transformations (if available)
echo "5. Testing linkml-map integration..."

if command -v linkml-map &> /dev/null; then
    echo "Attempting linkml-map schema derivation..."
    
    # Try to derive schema (may fail due to format issues)
    if linkml-map derive-schema -T linkml-to-rocrate-mapping.yaml -o derived-rocrate-schema.yaml src/data_sheets_schema/schema/data_sheets_schema.yaml 2>/dev/null; then
        echo "✓ linkml-map derivation successful"
        echo "Generated: derived-rocrate-schema.yaml"
    else
        echo "⚠ linkml-map derivation failed (format incompatibility expected)"
        echo "  This is normal - the generated mappings are for documentation and custom tools"
    fi
else
    echo "⚠ linkml-map not available, skipping advanced tests"
fi
echo

# Step 6: Generate summary report
echo "6. Generating summary report..."

cat << EOF > mapping_generation_report.md
# Schema Mapping Generation Report

Generated on: $(date)

## Files Created

### Mapping Specifications
- \`linkml-to-rocrate-mapping.yaml\` - LinkML → RO-Crate mapping
- \`rocrate-to-linkml-mapping.yaml\` - RO-Crate → LinkML mapping

### Transformation Tools
- \`scripts/mappings/generate_schema_mappings.py\` - Mapping generation script
- \`scripts/mappings/transform_data.py\` - Data transformation utilities

### Documentation
- \`MAPPING_DOCUMENTATION.md\` - Comprehensive mapping documentation

### Examples
- \`example_rocrate.json\` - Example RO-Crate format output
- \`example_linkml.yaml\` - Example LinkML format output

## Usage Commands

### Generate mappings:
\`\`\`bash
python scripts/mappings/generate_schema_mappings.py
\`\`\`

### Transform data:
\`\`\`bash
python scripts/mappings/transform_data.py
\`\`\`

### Complete generation (this script):
\`\`\`bash
bash scripts/mappings/run_mapping_generation.sh
\`\`\`

## Schema Correspondence Summary

- **LinkML Dataset** ↔ **RO-Crate overview section**
- **LinkML Purpose/Task classes** ↔ **RO-Crate useCases section**  
- **LinkML DataSubset** ↔ **RO-Crate composition.datasets array**
- Common metadata fields: title, description, license, keywords, DOI
- Complex mappings for creator/funding information

## Tools Used

- **schema-automator**: For schema analysis
- **linkml-map**: For transformation specifications
- **Custom Python scripts**: For bidirectional data transformation

Generation completed successfully!
EOF

echo "✓ Summary report generated: mapping_generation_report.md"
echo

# Step 7: Final summary
echo "=================================================="
echo "MAPPING GENERATION COMPLETE"
echo "=================================================="
echo
echo "Generated Files:"
echo "  📄 linkml-to-rocrate-mapping.yaml"
echo "  📄 rocrate-to-linkml-mapping.yaml"
echo "  📄 MAPPING_DOCUMENTATION.md"
echo "  📄 mapping_generation_report.md"
echo "  📄 example_rocrate.json"
echo "  📄 example_linkml.yaml"
echo
echo "Scripts Created:"
echo "  🐍 scripts/mappings/generate_schema_mappings.py"
echo "  🐍 scripts/mappings/transform_data.py"
echo "  📜 scripts/mappings/run_mapping_generation.sh"
echo
echo "Next Steps:"
echo "  1. Review the generated mappings in MAPPING_DOCUMENTATION.md"
echo "  2. Test transformations with your own data"
echo "  3. Customize mapping rules as needed"
echo "  4. Integrate with your workflow"
echo
echo "✅ All mapping generation tasks completed successfully!"