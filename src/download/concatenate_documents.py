#!/usr/bin/env python3
"""
Concatenate documents from a directory into a single document.

This script merges all documents from a specified directory into a single output file
in a deterministic, reproducible order (alphabetically sorted by filename).
"""

import argparse
import os
from pathlib import Path
from typing import List, Optional
import mimetypes


class DocumentConcatenator:
    """Concatenate documents from a directory in reproducible order."""

    def __init__(self, separator: str = "\n\n" + "="*80 + "\n\n"):
        """
        Initialize the concatenator.

        Args:
            separator: String to insert between documents (default: double newline with separator line)
        """
        self.separator = separator

    def get_files_sorted(self,
                        input_dir: Path,
                        extensions: Optional[List[str]] = None,
                        recursive: bool = False) -> List[Path]:
        """
        Get all files from directory in reproducible sorted order.

        Args:
            input_dir: Directory to read files from
            extensions: List of file extensions to include (e.g., ['.txt', '.md']). None = all files
            recursive: Whether to search subdirectories recursively

        Returns:
            Sorted list of file paths
        """
        if not input_dir.exists():
            raise FileNotFoundError(f"Input directory not found: {input_dir}")

        if not input_dir.is_dir():
            raise NotADirectoryError(f"Input path is not a directory: {input_dir}")

        # Collect files
        files = []

        if recursive:
            # Recursive search
            for file_path in input_dir.rglob('*'):
                if file_path.is_file():
                    if extensions is None or file_path.suffix.lower() in [ext.lower() for ext in extensions]:
                        files.append(file_path)
        else:
            # Non-recursive search
            for file_path in input_dir.iterdir():
                if file_path.is_file():
                    if extensions is None or file_path.suffix.lower() in [ext.lower() for ext in extensions]:
                        files.append(file_path)

        # Sort alphabetically by full path for reproducibility
        # Use relative path from input_dir for consistent sorting
        files.sort(key=lambda p: str(p.relative_to(input_dir.parent)))

        return files

    def read_file_content(self, file_path: Path) -> str:
        """
        Read content from a file.

        Args:
            file_path: Path to file to read

        Returns:
            File content as string
        """
        try:
            # Try UTF-8 first
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except UnicodeDecodeError:
            # Fall back to UTF-8 with BOM signature removal
            try:
                with open(file_path, 'r', encoding='utf-8-sig') as f:
                    return f.read()
            except UnicodeDecodeError:
                # Fall back to latin-1 which accepts all byte values
                with open(file_path, 'r', encoding='latin-1') as f:
                    return f.read()

    def create_file_header(self, file_path: Path, relative_to: Optional[Path] = None) -> str:
        """
        Create a header for a file in the concatenated document.

        Args:
            file_path: Path to the file
            relative_to: Base path to make the filename relative to

        Returns:
            Header string
        """
        if relative_to:
            display_path = file_path.relative_to(relative_to)
        else:
            display_path = file_path.name

        header = f"FILE: {display_path}\n"
        header += f"PATH: {file_path}\n"
        header += f"SIZE: {file_path.stat().st_size} bytes\n"
        header += "-" * 80 + "\n"

        return header

    def concatenate(self,
                   input_dir: Path,
                   output_file: Path,
                   extensions: Optional[List[str]] = None,
                   recursive: bool = False,
                   include_headers: bool = True,
                   include_summary: bool = True) -> dict:
        """
        Concatenate documents from input directory to output file.

        Args:
            input_dir: Directory containing input files
            output_file: Path to output concatenated file
            extensions: List of file extensions to include (None = all files)
            recursive: Whether to search subdirectories recursively
            include_headers: Whether to include file headers in output
            include_summary: Whether to include summary at the beginning

        Returns:
            Dictionary with concatenation statistics
        """
        # Get sorted list of files
        files = self.get_files_sorted(input_dir, extensions, recursive)

        if not files:
            raise ValueError(f"No files found in {input_dir}" +
                           (f" with extensions {extensions}" if extensions else ""))

        print(f"Found {len(files)} files to concatenate")

        # Prepare output
        output_file.parent.mkdir(parents=True, exist_ok=True)

        stats = {
            'total_files': len(files),
            'total_size': 0,
            'files_processed': [],
            'output_file': str(output_file),
            'input_dir': str(input_dir)
        }

        with open(output_file, 'w', encoding='utf-8') as out_f:
            # Write summary header
            if include_summary:
                out_f.write("=" * 80 + "\n")
                out_f.write("CONCATENATED DOCUMENT\n")
                out_f.write("=" * 80 + "\n")
                out_f.write(f"Input Directory: {input_dir}\n")
                out_f.write(f"Total Files: {len(files)}\n")
                out_f.write(f"Extensions: {extensions if extensions else 'All'}\n")
                out_f.write(f"Recursive: {recursive}\n")
                out_f.write("=" * 80 + "\n\n")

                # Write table of contents
                out_f.write("TABLE OF CONTENTS\n")
                out_f.write("-" * 80 + "\n")
                for i, file_path in enumerate(files, 1):
                    rel_path = file_path.relative_to(input_dir)
                    out_f.write(f"{i:3d}. {rel_path}\n")
                out_f.write("=" * 80 + "\n\n")

            # Concatenate files
            for i, file_path in enumerate(files, 1):
                print(f"  [{i}/{len(files)}] Processing: {file_path.name}")

                # Add file header
                if include_headers:
                    header = self.create_file_header(file_path, input_dir)
                    out_f.write(header)
                    out_f.write("\n")

                # Read and write content
                try:
                    content = self.read_file_content(file_path)
                    out_f.write(content)

                    # Add separator between files (except after last file)
                    if i < len(files):
                        out_f.write(self.separator)

                    # Update stats
                    file_size = file_path.stat().st_size
                    stats['total_size'] += file_size
                    stats['files_processed'].append({
                        'path': str(file_path),
                        'size': file_size
                    })

                except Exception as e:
                    error_msg = f"ERROR reading {file_path}: {e}\n"
                    print(f"  ⚠️  {error_msg}")
                    out_f.write(f"\n{error_msg}\n")

        print(f"\n✅ Concatenation complete!")
        print(f"   Output: {output_file}")
        print(f"   Total files: {stats['total_files']}")
        print(f"   Total size: {stats['total_size']:,} bytes")

        return stats


def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(
        description="Concatenate documents from a directory in reproducible order",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Concatenate all text files from a directory
  python concatenate_documents.py -i data/input -o data/concatenated.txt -e .txt .md

  # Concatenate all files recursively
  python concatenate_documents.py -i downloads_by_column/AI_READI -o data/ai_readi_all.txt -r

  # Concatenate without headers
  python concatenate_documents.py -i data/input -o data/output.txt --no-headers
        """
    )

    parser.add_argument(
        '-i', '--input-dir',
        required=True,
        type=Path,
        help='Input directory containing files to concatenate'
    )

    parser.add_argument(
        '-o', '--output',
        required=True,
        type=Path,
        help='Output file path for concatenated document'
    )

    parser.add_argument(
        '-e', '--extensions',
        nargs='+',
        help='File extensions to include (e.g., .txt .md .html). If not specified, all files are included'
    )

    parser.add_argument(
        '-r', '--recursive',
        action='store_true',
        help='Search subdirectories recursively'
    )

    parser.add_argument(
        '--no-headers',
        action='store_true',
        help='Do not include file headers in output'
    )

    parser.add_argument(
        '--no-summary',
        action='store_true',
        help='Do not include summary at the beginning'
    )

    parser.add_argument(
        '-s', '--separator',
        default="\n\n" + "="*80 + "\n\n",
        help='Separator to use between files (default: double newline with separator line)'
    )

    args = parser.parse_args()

    # Create concatenator
    concatenator = DocumentConcatenator(separator=args.separator)

    # Run concatenation
    try:
        stats = concatenator.concatenate(
            input_dir=args.input_dir,
            output_file=args.output,
            extensions=args.extensions,
            recursive=args.recursive,
            include_headers=not args.no_headers,
            include_summary=not args.no_summary
        )

        return 0

    except Exception as e:
        print(f"❌ Error: {e}")
        return 1


if __name__ == "__main__":
    exit(main())
