#!/usr/bin/env python3
"""
Test script for YAML extraction.

This script tests the YAML extraction from docx files and outputs the parsed data.
"""

import os
import sys
import json
import yaml
from pathlib import Path
from docx import Document

# Add the parent directory to sys.path to ensure imports work
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.renderer.yaml_parser import extract_yaml_from_text


def main():
    """Test YAML extraction from docx files."""
    repo_root = Path(__file__).parent.parent.parent
    data_dir = repo_root / "data" / "GC_data_sheets"
    
    # Test a specific file
    target_file = data_dir / "D4D - CM4AI.docx"
    
    if not target_file.exists():
        print(f"Error: Test file not found: {target_file}")
        sys.exit(1)
    
    # Extract text while preserving indentation
    doc = Document(target_file)
    full_text = ""
    
    for para in doc.paragraphs:
        text = para.text
        if not text.strip():
            full_text += "\n"
            continue
        
        # For headings, ensure they're properly separated
        if para.style and para.style.name.startswith('Heading'):
            full_text += f"\n{text}\n"
        else:
            full_text += f"{text}\n"
    
    # Save the raw text for inspection
    with open("raw_text.txt", "w", encoding="utf-8") as f:
        f.write(full_text)
    
    # Extract and parse YAML data
    yaml_data = extract_yaml_from_text(full_text)
    
    # Save the parsed data for inspection
    with open("parsed_yaml.json", "w", encoding="utf-8") as f:
        json.dump(yaml_data, f, indent=2)
    
    # For readability, also save as YAML
    with open("parsed_yaml.yaml", "w", encoding="utf-8") as f:
        yaml.dump(yaml_data, f, default_flow_style=False)
    
    print(f"Extracted {len(yaml_data)} top-level keys from {target_file.name}")
    print(f"Output saved to raw_text.txt, parsed_yaml.json, and parsed_yaml.yaml")


if __name__ == "__main__":
    main()