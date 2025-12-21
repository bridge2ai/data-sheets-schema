#!/usr/bin/env python3
"""
Render claudecode_assistant concatenated D4D YAML files to HTML
"""
import os
import sys
from pathlib import Path

# Add src/html to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src" / "html"))

from human_readable_renderer import HumanReadableRenderer
import yaml


def main():
    """Process claudecode_assistant concatenated YAML files and generate HTML"""

    input_dir = Path("data/d4d_concatenated/claudecode_assistant")
    output_dir = Path("data/d4d_html/concatenated/claudecode_assistant")

    # Ensure output directory exists
    output_dir.mkdir(parents=True, exist_ok=True)

    # Find all D4D YAML files
    yaml_files = sorted(input_dir.glob("*_d4d.yaml"))

    if not yaml_files:
        print(f"No D4D YAML files found in {input_dir}")
        return

    print(f"Found {len(yaml_files)} D4D YAML files to render")
    print(f"Output directory: {output_dir}\n")

    renderer = HumanReadableRenderer()
    processed_count = 0

    for yaml_file in yaml_files:
        print(f"Processing: {yaml_file.name}")

        try:
            # Read and parse YAML
            with open(yaml_file, 'r', encoding='utf-8-sig') as f:
                data = yaml.safe_load(f)

            if not data:
                print(f"  ⚠️  No data found in {yaml_file.name}")
                continue

            # Generate output filename
            project_name = yaml_file.stem.replace('_d4d', '')
            output_path = output_dir / f"{project_name}_d4d_human_readable.html"

            # Generate HTML with external CSS
            html_content = renderer.render_to_html(data, f"{project_name} Dataset Documentation")

            # Write output
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(html_content)

            print(f"  ✅ Generated: {output_path}")
            processed_count += 1

        except Exception as e:
            print(f"  ❌ Error processing {yaml_file.name}: {e}")
            import traceback
            traceback.print_exc()

    print(f"\n{'='*60}")
    print(f"Processed {processed_count}/{len(yaml_files)} files successfully")
    print(f"HTML files saved in: {output_dir}")


if __name__ == "__main__":
    main()
