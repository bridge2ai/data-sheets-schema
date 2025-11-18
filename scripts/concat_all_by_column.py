#!/usr/bin/env python3
"""
Concatenate ALL documents in each column directory into one mega-file per column.
This creates directory-level combined files (all AI_READI docs, all CM4AI docs, etc.).
"""
from pathlib import Path
from typing import List


def collect_all_txt_files(column_dir: Path) -> List[Path]:
    """Collect all .txt files in a column directory."""
    txt_files = list(column_dir.glob('*.txt'))
    # Sort by filename for consistent ordering
    return sorted(txt_files, key=lambda f: f.name)


def concatenate_all_files(txt_files: List[Path], column_name: str) -> str:
    """Concatenate all .txt files for a column."""
    content_parts = []

    # Add header
    content_parts.append(f"{'='*100}\n")
    content_parts.append(f"COMBINED DOCUMENT FOR COLUMN: {column_name}\n")
    content_parts.append(f"Total files: {len(txt_files)}\n")
    content_parts.append(f"{'='*100}\n\n")

    for i, txt_file in enumerate(txt_files, 1):
        # Add separator showing which file this content is from
        content_parts.append(f"\n{'-'*100}\n")
        content_parts.append(f"FILE {i}/{len(txt_files)}: {txt_file.name}\n")
        content_parts.append(f"{'-'*100}\n\n")

        # Add the file content
        try:
            with open(txt_file, 'r', encoding='utf-8') as f:
                content_parts.append(f.read())
        except Exception as e:
            content_parts.append(f"[Error reading file: {e}]\n")

        content_parts.append("\n\n")

    return ''.join(content_parts)


def main():
    base_dir = Path('downloads_by_column_enhanced')
    output_dir = Path('downloads_by_column_combined')

    # Create output directory
    output_dir.mkdir(exist_ok=True)

    # Process each column directory
    column_dirs = [d for d in base_dir.iterdir() if d.is_dir()]

    if not column_dirs:
        print("No column directories found!")
        return

    print(f"🔍 Found {len(column_dirs)} column directories\n")

    for column_dir in sorted(column_dirs):
        column_name = column_dir.name

        # Collect all .txt files
        txt_files = collect_all_txt_files(column_dir)

        if not txt_files:
            print(f"⏭️  Skipping {column_name}: No .txt files found")
            continue

        print(f"📂 Processing column: {column_name}")
        print(f"   Files to concatenate: {len(txt_files)}")

        # Concatenate all files
        combined_content = concatenate_all_files(txt_files, column_name)

        # Create output filename
        output_filename = f"{column_name}_all_combined.txt"
        output_path = output_dir / output_filename

        # Write combined file
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(combined_content)

        size_kb = len(combined_content) / 1024
        print(f"   ✅ Created: {output_path}")
        print(f"   Size: {size_kb:.1f} KB ({len(combined_content):,} characters)\n")

    print(f"\n📊 Summary")
    print(f"   Output directory: {output_dir}")
    print(f"\n📁 Created combined files:")
    for combined_file in sorted(output_dir.glob('*_all_combined.txt')):
        size_kb = combined_file.stat().st_size / 1024
        num_lines = sum(1 for _ in open(combined_file, encoding='utf-8'))
        print(f"   {combined_file.name:40s} {size_kb:8.1f} KB, {num_lines:6d} lines")


if __name__ == "__main__":
    main()
