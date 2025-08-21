#!/usr/bin/env python3
"""
Script to convert a single data sheet file to text, HTML, and PDF.

Usage:
    python convert_file.py <input_file.docx or input_file.xlsx>
"""

import os
import sys
from pathlib import Path

# Add the parent directory to sys.path to ensure imports work
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.renderer.converter import DataSheetConverter


def main():
    """Convert a single data sheet file."""
    if len(sys.argv) < 2:
        print("Usage: python convert_file.py <input_file.docx or input_file.xlsx>")
        sys.exit(1)

    input_file = sys.argv[1]
    
    if not os.path.exists(input_file):
        print(f"Error: File not found: {input_file}")
        sys.exit(1)
        
    file_ext = os.path.splitext(input_file)[1].lower()
    if file_ext not in ('.docx', '.xlsx'):
        print(f"Error: Unsupported file type: {file_ext}")
        print("Supported file types: .docx, .xlsx")
        sys.exit(1)
    
    try:
        print(f"Converting {os.path.basename(input_file)}...")
        converter = DataSheetConverter(input_file)
        output_files = converter.convert()
        print(f"Generated output files:")
        for output_file in output_files:
            print(f"  - {output_file}")
    except Exception as e:
        print(f"Error converting file: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()