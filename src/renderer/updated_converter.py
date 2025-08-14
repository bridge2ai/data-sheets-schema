#!/usr/bin/env python3
"""
Test script for the updated converter.

This script runs the updated converter on all docx and xlsx files.
"""

import os
import sys
from pathlib import Path

# Add the parent directory to sys.path to ensure imports work
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.renderer.converter import DataSheetConverter


def main():
    """Test the updated converter on a single file."""
    if len(sys.argv) < 2:
        print("Usage: python updated_converter.py <docx_file>")
        sys.exit(1)
    
    input_file = sys.argv[1]
    
    if not os.path.exists(input_file):
        print(f"Error: File not found: {input_file}")
        sys.exit(1)
    
    # Create output directory
    output_dir = Path("test_output")
    output_dir.mkdir(exist_ok=True)
    
    # Run the converter
    try:
        print(f"Processing {os.path.basename(input_file)}...")
        converter = DataSheetConverter(input_file)
        
        # Set the output base to our test directory
        original_output_base = converter.output_base
        filename = os.path.basename(original_output_base)
        converter.output_base = str(output_dir / filename)
        
        # Generate txt file only
        txt_file = converter.generate_txt()
        print(f"Generated: {txt_file}")
        
        # Show the first few lines of the output
        with open(txt_file, 'r', encoding='utf-8') as f:
            content = f.read(1000)
        
        print("\nPreview of the generated text file:")
        print("=" * 50)
        print(content)
        print("..." if len(content) >= 1000 else "")
        print("=" * 50)
        
    except Exception as e:
        print(f"Error processing {input_file}: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()