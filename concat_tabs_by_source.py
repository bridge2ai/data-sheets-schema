#!/usr/bin/env python3
"""
Concatenate tab files from the same source into combined documents.
Creates source-level combined files (e.g., all Health Data Nexus tabs together).
"""
from pathlib import Path
from typing import List, Dict
import re

# Logical tab orders for different source types
TAB_ORDERS = {
    'dataverse': ['files', 'metadata', 'terms', 'versions'],
    'healthnexus': [
        'abstract', 'description', 'background', 'methods', 'documentation',
        'files', 'metadata', 'ethics', 'acknowledgements', 'usage-notes',
        'release-notes', 'conflicts-of-interest', 'references', 'versions',
        'citationModal', '2'
    ],
    'fairhub': ['access']
}


def identify_source_type(filename: str) -> str:
    """Identify the source type from filename."""
    if 'healthnexus' in filename:
        return 'healthnexus'
    elif 'dataverse' in filename:
        return 'dataverse'
    elif 'fairhub' in filename:
        return 'fairhub'
    return 'unknown'


def extract_base_identifier(filename: str) -> str:
    """Extract the base identifier without tab info or extension."""
    # Remove extension
    name = filename.replace('.txt', '').replace('.html', '')

    # Remove _tab_XXX pattern
    match = re.sub(r'_tab_[^_]+', '', name)
    return match


def group_tab_files(base_dir: Path) -> Dict[str, List[Path]]:
    """Group tab files by their base source identifier."""
    tab_files = {}

    # Find all .txt tab files
    for txt_file in base_dir.rglob('*_tab_*.txt'):
        base_id = extract_base_identifier(txt_file.name)
        column = txt_file.parent.name

        # Create unique key combining column and base_id
        key = f"{column}/{base_id}"

        if key not in tab_files:
            tab_files[key] = []
        tab_files[key].append(txt_file)

    return tab_files


def extract_tab_name(filepath: Path) -> str:
    """Extract the tab name from filename."""
    match = re.search(r'_tab_([^_]+?)_row', filepath.name)
    if match:
        return match.group(1)
    return ''


def sort_tabs_by_logical_order(tab_files: List[Path], source_type: str) -> List[Path]:
    """Sort tab files according to logical order for the source type."""
    order = TAB_ORDERS.get(source_type, [])

    if not order:
        # Fallback to alphabetical
        return sorted(tab_files, key=lambda f: extract_tab_name(f))

    # Create a mapping of tab name to priority
    priority_map = {tab: i for i, tab in enumerate(order)}

    # Sort by priority, with unknown tabs at the end
    def sort_key(filepath):
        tab_name = extract_tab_name(filepath)
        return priority_map.get(tab_name, 999), tab_name

    return sorted(tab_files, key=sort_key)


def concatenate_tabs(tab_files: List[Path], source_type: str) -> str:
    """Concatenate tab files in logical order."""
    sorted_tabs = sort_tabs_by_logical_order(tab_files, source_type)

    content_parts = []
    for tab_file in sorted_tabs:
        tab_name = extract_tab_name(tab_file)

        # Add separator showing which tab this content is from
        content_parts.append(f"\n{'='*80}\n")
        content_parts.append(f"TAB: {tab_name.upper()}\n")
        content_parts.append(f"Source: {tab_file.name}\n")
        content_parts.append(f"{'='*80}\n\n")

        # Add the tab content
        with open(tab_file, 'r', encoding='utf-8') as f:
            content_parts.append(f.read())
        content_parts.append("\n\n")

    return ''.join(content_parts)


def main():
    base_dir = Path('downloads_by_column_enhanced')
    output_base = Path('downloads_by_column_enhanced_combined')

    # Create output directory
    output_base.mkdir(exist_ok=True)

    # Group tab files
    tab_groups = group_tab_files(base_dir)

    print(f"🔍 Found {len(tab_groups)} source groups with tabs\n")

    processed = 0
    for key, tab_files in sorted(tab_groups.items()):
        column, base_id = key.split('/', 1)

        # Determine source type
        source_type = identify_source_type(base_id)

        # Create column subdirectory in output
        output_dir = output_base / column
        output_dir.mkdir(exist_ok=True)

        # Create output filename
        output_filename = f"{base_id}_combined.txt"
        output_path = output_dir / output_filename

        print(f"📄 Processing: {key}")
        print(f"   Source type: {source_type}")
        print(f"   Tab files: {len(tab_files)}")

        # Concatenate tabs
        combined_content = concatenate_tabs(tab_files, source_type)

        # Write combined file
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(combined_content)

        print(f"   ✅ Created: {output_path}")
        print(f"   Size: {len(combined_content):,} characters\n")

        processed += 1

    print(f"\n📊 Summary")
    print(f"   Total groups processed: {processed}")
    print(f"   Output directory: {output_base}")
    print(f"\n📁 Created combined files:")
    for combined_file in sorted(output_base.rglob('*_combined.txt')):
        size_kb = combined_file.stat().st_size / 1024
        print(f"   {combined_file.relative_to(output_base)} ({size_kb:.1f} KB)")


if __name__ == "__main__":
    main()
