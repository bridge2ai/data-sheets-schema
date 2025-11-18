#!/usr/bin/env python3
"""
Convert debug.txt files with valid YAML to proper .yaml files.
These debug files contain successfully extracted and fixed YAML content.
"""
from pathlib import Path

def convert_debug_to_yaml(debug_file: Path):
    """Convert a debug file to a proper YAML file by removing the header."""
    with open(debug_file, 'r', encoding='utf-8') as f:
        content = f.read()

    # Remove the "=== YAML Fixing Applied ===" header
    if content.startswith("=== YAML Fixing Applied ==="):
        yaml_content = content.replace("=== YAML Fixing Applied ===\n", "", 1)

        # Create new YAML filename
        yaml_file = debug_file.with_suffix('.yaml').with_name(
            debug_file.stem.replace('_d4d_debug', '_d4d')
        )

        with open(yaml_file, 'w', encoding='utf-8') as f:
            f.write(yaml_content)

        print(f"✅ Converted: {debug_file.name} -> {yaml_file.name}")
        return yaml_file
    else:
        print(f"⚠️  Skipped: {debug_file.name} (no YAML fixing header)")
        return None

def main():
    base_dir = Path("data/extracted_by_column_enhanced_rerun")
    debug_files = list(base_dir.rglob("*_d4d_debug.txt"))

    print(f"🔍 Found {len(debug_files)} debug files to convert\n")

    converted = 0
    for debug_file in debug_files:
        if convert_debug_to_yaml(debug_file):
            converted += 1

    print(f"\n📊 Converted {converted}/{len(debug_files)} debug files to YAML")

if __name__ == "__main__":
    main()
