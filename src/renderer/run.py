#!/usr/bin/env python3
"""
Run script for the data sheets converter.

This script provides a simple way to run the converter 
on the GC_data_sheets directory.
"""

import os
import sys
import io
from pathlib import Path

# Configure stdout/stderr to use UTF-8
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Add the parent directory to sys.path to ensure imports work
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Fix environment encoding
os.environ['PYTHONIOENCODING'] = 'utf-8'

# Custom docx converter using our safer implementation
def process_docx_files(directory):
    """Process DOCX files with Unicode-safe converter."""
    from src.renderer.converters.docx_converter import DocxConverter
    
    data_dir = Path(directory)
    if not data_dir.exists():
        print(f"Error: Directory not found: {data_dir}")
        return False
    
    # Create output directories
    out_dir = data_dir / "output"
    out_dir.mkdir(exist_ok=True)
    
    # Create converter
    converter = DocxConverter(output_dir=str(out_dir))
    
    # Process all DOCX files
    file_count = 0
    success_count = 0
    
    for docx_file in data_dir.glob("*.docx"):
        file_count += 1
        try:
            # Safely print filename to avoid encoding issues
            safe_name = docx_file.name
            print(f"Processing {safe_name}...")
            
            # Extract text and sanitize Unicode characters
            doc = converter.extract_text_from_docx(docx_file)
            if doc:
                # Replace problematic characters
                doc = doc.replace('\u2022', '*')  # Replace bullet with asterisk
                doc = doc.replace('\u2019', "'")  # Replace curly quote
                doc = doc.replace('\u2018', "'")  # Replace curly quote
                doc = doc.replace('\u201c', '"')  # Replace curly quote
                doc = doc.replace('\u201d', '"')  # Replace curly quote
                
                # Create output file path
                out_file = out_dir / f"{docx_file.stem}.txt"
                
                # Save text to file with explicit UTF-8 encoding
                with open(out_file, 'w', encoding='utf-8') as f:
                    f.write(doc)
                
                print(f"Successfully processed {safe_name} to {out_file}")
                success_count += 1
            else:
                print(f"Error: Could not extract text from {safe_name}")
        except Exception as e:
            print(f"Error processing {docx_file.name}: {str(e)}")
    
    print(f"\nProcessed {file_count} files, {success_count} successful")
    return True

def main():
    """Run the converter on GC_data_sheets directory."""
    # Get the absolute path to the data sheets directory
    script_dir = Path(__file__).parent
    repo_root = script_dir.parent.parent
    data_dir = repo_root / "data" / "GC_data_sheets"
    
    if not data_dir.exists():
        print(f"Error: Data directory not found: {data_dir}")
        sys.exit(1)
    
    print(f"Processing data sheets from: {data_dir}")
    
    # Create safe output directories
    output_dir = data_dir / "output"
    output_dir.mkdir(exist_ok=True)
    
    # Use our safer processing function
    success = process_docx_files(data_dir)
    
    if success:
        print("\nConversion complete. Basic text extraction saved to:")
        print(f"  Output files: {output_dir}")
    else:
        print("\nConversion failed.")
        sys.exit(1)


if __name__ == "__main__":
    main()