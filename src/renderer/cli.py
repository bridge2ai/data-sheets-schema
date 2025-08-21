#!/usr/bin/env python3
"""
Command-line interface for the data sheets converter.

This script provides a command-line interface for converting
data sheets from docx and xlsx formats to human-readable
text-only documents with proper styling.
"""

import os
import sys
import argparse
from pathlib import Path

from .converter import DataSheetConverter, process_directory


def main():
    """Execute the command-line interface."""
    parser = argparse.ArgumentParser(
        description="Convert data sheets to human-readable formats (txt, pdf, html)"
    )
    parser.add_argument(
        "input",
        help="Input file or directory containing docx/xlsx files"
    )
    parser.add_argument(
        "-o", "--output-dir",
        help="Output directory (defaults to same location as input)"
    )
    parser.add_argument(
        "-f", "--formats",
        default="txt,pdf,html",
        help="Output formats (comma-separated, default: txt,pdf,html)"
    )
    parser.add_argument(
        "-r", "--recursive",
        action="store_true",
        help="Process directories recursively"
    )
    
    args = parser.parse_args()
    
    input_path = Path(args.input)
    
    if not input_path.exists():
        print(f"Error: Path does not exist: {input_path}")
        sys.exit(1)
    
    if input_path.is_dir():
        print(f"Processing directory: {input_path}")
        process_directory(str(input_path))
    elif input_path.is_file():
        file_ext = input_path.suffix.lower()
        if file_ext in ('.docx', '.xlsx'):
            try:
                print(f"Processing file: {input_path.name}")
                converter = DataSheetConverter(str(input_path))
                output_files = converter.convert()
                print(f"Generated: {', '.join(output_files)}")
            except Exception as e:
                print(f"Error processing {input_path.name}: {e}")
        else:
            print(f"Unsupported file type: {file_ext}")
    else:
        print(f"Error: Path is neither a file nor a directory: {input_path}")
        sys.exit(1)


if __name__ == "__main__":
    main()