#!/usr/bin/env python3
"""
Render concatenated/synthesized D4D YAML files to HTML
"""
import os
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from human_readable_renderer import HumanReadableRenderer
import yaml


def main():
    """Process concatenated YAML files and generate human-readable HTML versions"""

    input_dir = "data/concatenated"
    output_dir = "src/html/output/concatenated"

    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)

    # Find all synthesized YAML files
    yaml_files = list(Path(input_dir).glob("*_synthesized.yaml"))

    if not yaml_files:
        print(f"No synthesized YAML files found in {input_dir}")
        return

    print(f"Found {len(yaml_files)} synthesized YAML files to render")
    print(f"Output directory: {output_dir}\n")

    renderer = HumanReadableRenderer()
    processed_count = 0

    for yaml_file in sorted(yaml_files):
        print(f"Processing: {yaml_file.name}")

        try:
            # Read and parse YAML
            with open(yaml_file, 'r', encoding='utf-8-sig') as f:
                data = yaml.safe_load(f)

            if not data:
                print(f"  ⚠️  No data found in {yaml_file.name}")
                continue

            # Generate output filename
            base_name = yaml_file.stem.replace('_synthesized', '')
            output_path = os.path.join(output_dir, f"{base_name}_synthesized.html")

            # Generate HTML with external CSS
            html_content = renderer.render_to_html(data, f"{base_name} (Synthesized)")

            # Write output
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(html_content)

            print(f"  ✅ Generated: {output_path}")
            processed_count += 1

        except Exception as e:
            print(f"  ❌ Error processing {yaml_file.name}: {e}")

    print(f"\n{'='*60}")
    print(f"Processed {processed_count}/{len(yaml_files)} files successfully")
    print(f"HTML files saved in: {output_dir}")


if __name__ == "__main__":
    main()
