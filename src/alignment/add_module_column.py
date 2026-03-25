#!/usr/bin/env python3
"""
Add d4d_module column to SSSOM mapping files.

Reads the D4D schema to determine which module each attribute belongs to,
then adds a d4d_module column to all SSSOM TSV files.
"""

import csv
import re
from pathlib import Path
from typing import Dict

import yaml


def extract_attribute_to_module_mapping(schema_file: Path) -> Dict[str, str]:
    """
    Extract mapping from D4D attributes and classes to their modules.

    Parses the main schema file which has comments like:
    # Motivation module classes
    # Composition module classes
    etc.

    Returns mapping with keys like:
    - 'purposes' -> 'D4D_Motivation' (for attributes)
    - '_class_Purpose' -> 'D4D_Motivation' (for classes)
    """
    with open(schema_file) as f:
        schema = yaml.safe_load(f)

    # Mapping from attribute name to module
    attr_to_module = {}

    # Get Dataset class attributes
    dataset_class = schema.get('classes', {}).get('Dataset', {})
    attributes = dataset_class.get('attributes', {})

    # Read the YAML file as text to preserve comments
    with open(schema_file) as f:
        lines = f.readlines()

    # Parse to find module comments and subsequent attributes
    current_module = None
    in_attributes = False

    for i, line in enumerate(lines):
        # Check for module comments
        if '# Motivation module' in line:
            current_module = 'D4D_Motivation'
        elif '# Composition module' in line:
            current_module = 'D4D_Composition'
        elif '# Collection module' in line:
            current_module = 'D4D_Collection'
        elif '# Ethics module' in line:
            current_module = 'D4D_Ethics'
        elif '# Human subjects module' in line:
            current_module = 'D4D_Human'
        elif '# Preprocessing module' in line:
            current_module = 'D4D_Preprocessing'
        elif '# Uses module' in line:
            current_module = 'D4D_Uses'
        elif '# Distribution module' in line:
            current_module = 'D4D_Distribution'
        elif '# Data Governance module' in line:
            current_module = 'D4D_Data_Governance'
        elif '# Maintenance module' in line:
            current_module = 'D4D_Maintenance'
        elif '# Variable/field metadata' in line:
            current_module = 'D4D_Variables'
        elif '# Other attributes' in line or '# Dataset citation' in line:
            current_module = 'D4D_Base'

        # Check if we're in the attributes section
        if line.strip() == 'attributes:':
            in_attributes = True
            continue

        # Extract attribute names (lines that start with spaces and attribute name followed by :)
        if in_attributes and current_module:
            # Match attribute definition: "      attribute_name:"
            match = re.match(r'^      (\w+):', line)
            if match:
                attr_name = match.group(1)
                attr_to_module[attr_name] = current_module

    # Add base Dataset properties that aren't in attributes section
    base_props = [
        'bytes', 'dialect', 'encoding', 'format', 'hash', 'md5', 'media_type',
        'path', 'sha256', 'external_resources', 'resources', 'is_tabular',
        'citation', 'parent_datasets', 'related_datasets'
    ]
    for prop in base_props:
        if prop not in attr_to_module:
            attr_to_module[prop] = 'D4D_Base'

    # Add DatasetCollection properties
    attr_to_module['resources'] = 'D4D_Base'

    # Add class-to-module mappings by reading module files
    schema_dir = schema_file.parent
    module_files = {
        'D4D_Motivation': 'D4D_Motivation.yaml',
        'D4D_Composition': 'D4D_Composition.yaml',
        'D4D_Collection': 'D4D_Collection.yaml',
        'D4D_Preprocessing': 'D4D_Preprocessing.yaml',
        'D4D_Uses': 'D4D_Uses.yaml',
        'D4D_Distribution': 'D4D_Distribution.yaml',
        'D4D_Maintenance': 'D4D_Maintenance.yaml',
        'D4D_Ethics': 'D4D_Ethics.yaml',
        'D4D_Human': 'D4D_Human.yaml',
        'D4D_Data_Governance': 'D4D_Data_Governance.yaml',
        'D4D_Variables': 'D4D_Variables.yaml',
        'D4D_Base_import': 'D4D_Base_import.yaml',
    }

    for module_name, module_file in module_files.items():
        module_path = schema_dir / module_file
        if module_path.exists():
            with open(module_path) as f:
                try:
                    module_schema = yaml.safe_load(f)
                    classes = module_schema.get('classes', {})
                    for class_name in classes.keys():
                        # Add mapping for class
                        attr_to_module[f'_class_{class_name}'] = module_name
                except Exception as e:
                    print(f"Warning: Could not parse {module_file}: {e}")

    return attr_to_module


def add_module_column_to_sssom(sssom_file: Path, attr_to_module: Dict[str, str]):
    """
    Add d4d_module column to an SSSOM TSV file.
    """
    print(f"\nProcessing: {sssom_file.name}")

    # Read the file
    with open(sssom_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    # Separate header comments from data
    header_comments = []
    data_start_idx = 0

    for i, line in enumerate(lines):
        if line.startswith('#'):
            header_comments.append(line)
        else:
            data_start_idx = i
            break

    # Read TSV data
    reader = csv.DictReader(lines[data_start_idx:], delimiter='\t')
    rows = list(reader)

    if not rows:
        print(f"  ⚠️  No data rows found")
        return

    # Check if d4d_module column already exists
    if 'd4d_module' in rows[0]:
        print(f"  ⚠️  d4d_module column already exists, skipping")
        return

    # Determine column to use for attribute lookup
    path_column = None
    for col in ['d4d_schema_path', 'd4d_slot_name', 'subject_id', 'subject_label']:
        if col in rows[0]:
            path_column = col
            break

    if not path_column:
        print(f"  ⚠️  No suitable column found for attribute lookup")
        print(f"  Available columns: {list(rows[0].keys())[:5]}")
        return

    print(f"  Using column: {path_column}")

    # Add d4d_module column
    rows_with_module = []
    module_counts = {}

    for row in rows:
        # Extract attribute name from path (Dataset.attribute_name -> attribute_name)
        path_value = row.get(path_column, '')

        if path_column == 'd4d_schema_path':
            # Format: Dataset.attribute_name or DatasetCollection.resources
            if '.' in path_value:
                attr_name = path_value.split('.', 1)[1]
            else:
                attr_name = path_value
        elif path_column == 'd4d_slot_name':
            # Format: attribute_name (already in correct format)
            attr_name = path_value
        elif path_column == 'subject_id':
            # Format: d4d:attribute_name or d4d:ClassName/attribute_name
            if ':' in path_value:
                attr_part = path_value.split(':', 1)[1]
                # Handle ClassName/attribute_name format
                if '/' in attr_part:
                    # This is a class attribute, get the class name
                    class_name = attr_part.split('/')[0]
                    # Map class names to modules
                    attr_name = f"_class_{class_name}"
                else:
                    attr_name = attr_part
            else:
                attr_name = path_value
        else:
            # Use as-is for subject_label
            attr_name = path_value.lower().replace(' ', '_')

        # Look up module
        module = attr_to_module.get(attr_name, 'Unknown')

        # If still unknown, try to match by checking if attr_name appears in any key
        if module == 'Unknown' and not attr_name.startswith('_class_'):
            # Try exact match with underscores normalized
            normalized_attr = attr_name.lower().replace('-', '_')
            for key, val in attr_to_module.items():
                if key.lower().replace('-', '_') == normalized_attr:
                    module = val
                    break

        row['d4d_module'] = module

        # Count modules
        module_counts[module] = module_counts.get(module, 0) + 1

        rows_with_module.append(row)

    # Prepare new fieldnames with d4d_module after subject columns
    fieldnames = list(rows[0].keys())

    # Insert d4d_module after the first few subject-related columns
    insert_position = 1
    for i, field in enumerate(fieldnames):
        if field in ['d4d_schema_path', 'subject_id', 'subject_label', 'subject_category']:
            insert_position = i + 1

    fieldnames.insert(insert_position, 'd4d_module')

    # Write back to file
    with open(sssom_file, 'w', encoding='utf-8', newline='') as f:
        # Write header comments
        for comment in header_comments:
            f.write(comment)

        # Add note about module column
        f.write('# d4d_module: D4D schema module containing this attribute\n')
        f.write('#\n')

        # Write TSV data with new column
        writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter='\t', extrasaction='ignore')
        writer.writeheader()
        writer.writerows(rows_with_module)

    print(f"  ✓ Added d4d_module column to {len(rows_with_module)} rows")
    print(f"  Module breakdown:")
    for module, count in sorted(module_counts.items(), key=lambda x: -x[1]):
        print(f"    {module}: {count}")


def main():
    """Main entry point."""
    # Paths
    repo_root = Path(__file__).parent.parent.parent
    schema_file = repo_root / 'src/data_sheets_schema/schema/data_sheets_schema.yaml'
    mappings_dir = repo_root / 'data/mappings'

    print("=" * 80)
    print("Adding d4d_module column to SSSOM files")
    print("=" * 80)

    # Extract attribute to module mapping
    print("\n📖 Reading D4D schema...")
    attr_to_module = extract_attribute_to_module_mapping(schema_file)
    print(f"   Found {len(attr_to_module)} attribute-to-module mappings")

    # Process all SSSOM files
    sssom_files = list(mappings_dir.glob('*sssom*.tsv'))
    print(f"\n📁 Found {len(sssom_files)} SSSOM files")

    for sssom_file in sorted(sssom_files):
        add_module_column_to_sssom(sssom_file, attr_to_module)

    print("\n" + "=" * 80)
    print("✓ Complete!")
    print("=" * 80)


if __name__ == '__main__':
    main()
