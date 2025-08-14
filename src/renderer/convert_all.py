#!/usr/bin/env python3
"""
Script to convert all data sheet files to txt format.

This script runs the converter on all docx and xlsx files
in the data/GC_data_sheets directory, generating txt outputs.
"""

import os
import sys
from pathlib import Path

# Add the parent directory to sys.path to ensure imports work
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.renderer.converter import DataSheetConverter


def main():
    """Convert all data sheet files to txt format."""
    # Get the absolute path to the data sheets directory
    script_dir = Path(__file__).parent
    repo_root = script_dir.parent.parent
    data_dir = repo_root / "data" / "GC_data_sheets"
    output_dir = data_dir / "processed_text"
    
    if not data_dir.exists():
        print(f"Error: Data directory not found: {data_dir}")
        sys.exit(1)
    
    # Create output directory
    output_dir.mkdir(exist_ok=True)
    
    # Process all docx files
    docx_files = list(data_dir.glob("*.docx"))
    xlsx_files = list(data_dir.glob("*.xlsx"))
    total_files = len(docx_files) + len(xlsx_files)
    
    print(f"Found {len(docx_files)} docx files and {len(xlsx_files)} xlsx files")
    print(f"Output will be saved to: {output_dir}")
    
    success_count = 0
    
    # Process docx files
    for file_path in docx_files:
        base_name = file_path.stem
        output_path = output_dir / f"{base_name}.txt"
        
        try:
            print(f"Processing {file_path.name}...")
            converter = DataSheetConverter(str(file_path))
            converter.output_base = str(output_dir / base_name)
            txt_file = converter.generate_txt()
            print(f"  Generated: {txt_file}")
            success_count += 1
        except Exception as e:
            print(f"  Error processing {file_path.name}: {e}")
            import traceback
            traceback.print_exc()
    
    # Process xlsx files
    for file_path in xlsx_files:
        base_name = file_path.stem
        output_path = output_dir / f"{base_name}.txt"
        
        try:
            print(f"Processing {file_path.name}...")
            converter = DataSheetConverter(str(file_path))
            converter.output_base = str(output_dir / base_name)
            txt_file = converter.generate_txt()
            print(f"  Generated: {txt_file}")
            success_count += 1
        except Exception as e:
            print(f"  Error processing {file_path.name}: {e}")
            import traceback
            traceback.print_exc()
    
    print(f"\nConversion complete. Successfully processed {success_count} of {total_files} files.")
    print(f"Outputs saved to: {output_dir}")


if __name__ == "__main__":
    main()