#!/usr/bin/env python3
"""
Generate HTML for all D4D YAML files in extracted directories
Creates HTML subdirectories alongside YAML files
"""

import os
import sys
from pathlib import Path
import yaml

# Add src/html to path to import renderer
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src', 'html'))
from human_readable_renderer import HumanReadableRenderer

def find_d4d_yaml_files(base_dirs):
    """Find all D4D YAML files in the specified directories"""
    yaml_files = []

    for base_dir in base_dirs:
        if not os.path.exists(base_dir):
            print(f"Directory not found: {base_dir}")
            continue

        for root, dirs, files in os.walk(base_dir):
            for file in files:
                if file.endswith('.yaml') and '_d4d' in file and not file.endswith('_debug.txt'):
                    yaml_path = os.path.join(root, file)
                    yaml_files.append(yaml_path)

    return sorted(yaml_files)

def copy_css_file(target_dir, css_source_path):
    """Copy CSS file to target directory if it doesn't exist"""
    import shutil

    css_target = os.path.join(target_dir, 'datasheet-common.css')

    # Only copy if doesn't exist
    if not os.path.exists(css_target) and os.path.exists(css_source_path):
        shutil.copy2(css_source_path, css_target)
        return True
    return False

def generate_html_for_yaml(yaml_path, css_source_path):
    """Generate HTML for a single YAML file in an html subdirectory"""

    try:
        # Create html subdirectory in the same directory as the YAML file
        yaml_dir = os.path.dirname(yaml_path)
        html_dir = os.path.join(yaml_dir, 'html')
        os.makedirs(html_dir, exist_ok=True)

        # Copy CSS file to html directory
        copy_css_file(html_dir, css_source_path)

        # Read and parse YAML
        with open(yaml_path, 'r', encoding='utf-8-sig') as f:
            data = yaml.safe_load(f)

        if not data:
            print(f"  ⚠️  No data found in {yaml_path}")
            return False

        # Generate output filename
        base_name = Path(yaml_path).stem
        if base_name.endswith('_data'):
            base_name = base_name[:-5]  # Remove '_data' suffix

        output_path = os.path.join(html_dir, f"{base_name}.html")

        # Generate HTML
        renderer = HumanReadableRenderer()
        html_content = renderer.render_to_html(data, base_name, css_file="datasheet-common.css")

        # Write output
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_content)

        # Calculate relative path for display
        rel_path = os.path.relpath(output_path, os.getcwd())
        print(f"  ✅ {rel_path}")
        return True

    except Exception as e:
        print(f"  ❌ Error processing {yaml_path}: {e}")
        return False

def main():
    """Main function to generate HTML for all D4D YAML files"""

    print("=" * 80)
    print("D4D HTML Generator")
    print("=" * 80)
    print()

    # Directories to search for D4D YAML files
    base_dirs = [
        'data/extracted_by_column',
        'data/extracted_by_column_enhanced',
        'data/extracted_claude_code',
        'data/extracted_coding_agent',
        'data/extracted_d4d_agent',
        'data/sheets_concatenated',
        'data/validated_extracted'
    ]

    # CSS source file
    css_source = 'src/html/output/datasheet-common.css'
    if not os.path.exists(css_source):
        print(f"⚠️  Warning: CSS file not found at {css_source}")
        print(f"    HTML files will reference a CSS file that may not exist.")
        print()

    # Find all YAML files
    print("🔍 Finding D4D YAML files...")
    yaml_files = find_d4d_yaml_files(base_dirs)

    print(f"📊 Found {len(yaml_files)} D4D YAML files")
    print()

    if not yaml_files:
        print("❌ No D4D YAML files found!")
        return 1

    # Process each file
    print("🎨 Generating HTML...")
    print()

    success_count = 0
    error_count = 0

    for yaml_path in yaml_files:
        if generate_html_for_yaml(yaml_path, css_source):
            success_count += 1
        else:
            error_count += 1

    # Summary
    print()
    print("=" * 80)
    print("📈 Summary")
    print("=" * 80)
    print(f"✅ Successfully generated: {success_count} HTML files")
    print(f"❌ Errors: {error_count} files")
    print(f"📁 Total processed: {len(yaml_files)} YAML files")
    print()
    print("HTML files created in 'html' subdirectories alongside their YAML sources")
    print("=" * 80)

    return 0 if error_count == 0 else 1

if __name__ == "__main__":
    sys.exit(main())
