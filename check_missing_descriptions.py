#!/usr/bin/env python3
"""
Check for missing descriptions in D4D schema module files.
"""

import yaml
from pathlib import Path

def check_module(module_path):
    """Check a single module for missing descriptions."""
    with open(module_path, 'r') as f:
        data = yaml.safe_load(f)

    issues = []
    module_name = module_path.stem

    # Check module-level description
    if not data.get('description'):
        issues.append(f"Module missing description")

    # Check classes
    classes = data.get('classes', {})
    for class_name, class_def in classes.items():
        if not class_def.get('description'):
            issues.append(f"Class '{class_name}' missing description")

        # Check attributes/slots
        attributes = class_def.get('attributes', {})
        for attr_name, attr_def in attributes.items():
            if attr_def is None or not attr_def.get('description'):
                issues.append(f"Class '{class_name}', attribute '{attr_name}' missing description")

    # Check slots
    slots = data.get('slots', {})
    for slot_name, slot_def in slots.items():
        if slot_def is None or not slot_def.get('description'):
            issues.append(f"Slot '{slot_name}' missing description")

    # Check enums
    enums = data.get('enums', {})
    for enum_name, enum_def in enums.items():
        if enum_def is None or not enum_def.get('description'):
            issues.append(f"Enum '{enum_name}' missing description")

        # Check permissible values
        if enum_def:
            permissible_values = enum_def.get('permissible_values', {})
            for pv_name, pv_def in permissible_values.items():
                if pv_def is None or not pv_def.get('description'):
                    issues.append(f"Enum '{enum_name}', value '{pv_name}' missing description")

    return module_name, issues

def main():
    schema_dir = Path('src/data_sheets_schema/schema')
    d4d_modules = sorted(schema_dir.glob('D4D_*.yaml'))

    all_issues = {}
    total_issues = 0

    for module_path in d4d_modules:
        module_name, issues = check_module(module_path)
        if issues:
            all_issues[module_name] = issues
            total_issues += len(issues)

    # Print summary
    print("=" * 80)
    print("MISSING DESCRIPTIONS REPORT")
    print("=" * 80)
    print()

    if not all_issues:
        print("✅ No missing descriptions found!")
    else:
        print(f"Found {total_issues} missing descriptions across {len(all_issues)} modules:\n")

        for module_name in sorted(all_issues.keys()):
            issues = all_issues[module_name]
            print(f"\n{module_name} ({len(issues)} issues):")
            print("-" * 80)
            for issue in issues:
                print(f"  • {issue}")

    print()
    print("=" * 80)
    return total_issues

if __name__ == '__main__':
    total = main()
    exit(0 if total == 0 else 1)
