#!/usr/bin/env python3
"""
Fix YAML syntax errors in D4D debug files.

Common issues:
- Unescaped colons in strings like "TCPS 2: CORE 2022"
- Unescaped colons in URLs like "doi: http://..."
"""

import re
from pathlib import Path
import yaml

def fix_yaml_content(content: str) -> str:
    """Apply common YAML fixes."""
    lines = content.split('\n')
    fixed_lines = []

    for line in lines:
        # Skip header comments and empty lines
        if line.strip().startswith('#') or not line.strip():
            fixed_lines.append(line)
            continue

        # Check if line has unquoted string with multiple colons
        # Pattern: "- key: value with: extra colons"
        # or: "  key: value with: extra colons"
        if ':' in line:
            # Count colons
            colon_count = line.count(':')
            if colon_count > 1:
                # Check if it's a list item or mapping
                stripped = line.lstrip()

                # Pattern 1: List item like "- Required training: TCPS 2: CORE 2022"
                if stripped.startswith('- ') and ':' in stripped[2:]:
                    # Find first colon (the mapping separator)
                    first_colon_idx = stripped.index(':', 2)
                    key_part = stripped[:first_colon_idx + 1]
                    value_part = stripped[first_colon_idx + 1:].strip()

                    # If value has colons, quote it
                    if ':' in value_part and not (value_part.startswith('"') or value_part.startswith("'")):
                        indent = line[:len(line) - len(stripped)]
                        fixed_line = f'{indent}{key_part} "{value_part}"'
                        fixed_lines.append(fixed_line)
                        continue

                # Pattern 2: Regular mapping like "  key: value: with colons"
                elif not stripped.startswith('-'):
                    parts = stripped.split(':', 1)
                    if len(parts) == 2:
                        key = parts[0].strip()
                        value = parts[1].strip()

                        # If value starts with http and has colons, it's likely a URL
                        if ':' in value and not (value.startswith('"') or value.startswith("'")):
                            # Check if it's likely needing quotes
                            if 'http://' in value or 'https://' in value or 'doi:' in value.lower() or \
                               '; ' in value or 'TCPS' in value:
                                indent = line[:len(line) - len(stripped)]
                                fixed_line = f'{indent}{key}: "{value}"'
                                fixed_lines.append(fixed_line)
                                continue

        fixed_lines.append(line)

    return '\n'.join(fixed_lines)


def test_yaml_parse(content: str) -> tuple[bool, str]:
    """Test if YAML can be parsed."""
    try:
        yaml.safe_load(content)
        return True, "Valid YAML"
    except yaml.YAMLError as e:
        return False, str(e)


def process_debug_file(debug_file: Path) -> bool:
    """Process a single debug file and try to fix it."""
    print(f"\n📄 Processing: {debug_file.name}")

    # Read content
    with open(debug_file, 'r', encoding='utf-8') as f:
        original_content = f.read()

    # Test original
    is_valid, error = test_yaml_parse(original_content)
    if is_valid:
        print(f"   ✅ Already valid YAML (unexpected!)")
        return False

    print(f"   ❌ Original error: {error.split(chr(10))[0][:80]}...")

    # Apply fixes
    fixed_content = fix_yaml_content(original_content)

    # Test fixed version
    is_valid, error = test_yaml_parse(fixed_content)
    if is_valid:
        # Save as proper YAML file
        yaml_file = debug_file.with_name(debug_file.name.replace('_d4d_debug.txt', '_d4d.yaml'))
        with open(yaml_file, 'w', encoding='utf-8') as f:
            f.write(fixed_content)
        print(f"   ✅ Fixed and saved as: {yaml_file.name}")
        return True
    else:
        print(f"   ⚠️  Still invalid: {error.split(chr(10))[0][:80]}...")
        return False


def main():
    """Process all debug files."""
    base_dir = Path(__file__).parent / 'data' / 'extracted_by_column_enhanced'
    debug_files = list(base_dir.rglob('*_d4d_debug.txt'))

    print(f"🔧 Found {len(debug_files)} debug files to fix\n")
    print("=" * 60)

    fixed_count = 0
    failed_count = 0

    for debug_file in sorted(debug_files):
        success = process_debug_file(debug_file)
        if success:
            fixed_count += 1
        else:
            failed_count += 1

    print("\n" + "=" * 60)
    print(f"\n📊 Results:")
    print(f"   ✅ Fixed: {fixed_count}")
    print(f"   ❌ Still failing: {failed_count}")
    print(f"   📁 Total: {len(debug_files)}")


if __name__ == '__main__':
    main()
