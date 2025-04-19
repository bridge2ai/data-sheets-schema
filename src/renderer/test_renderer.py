#!/usr/bin/env python3
"""
Test script for datasheets renderer.

This script demonstrates all output formats for the datasheet renderer:
1. Raw extracted text (_raw.txt)
2. Hierarchical table layout in plain text (.txt)
3. HTML rendered version with styling (.html)
"""

import os
import sys
import shutil
from pathlib import Path
import logging
import argparse
from collections import OrderedDict

# Add proper encoding to handle Unicode characters
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Import our renderers
from simple_extractor import extract_text_from_docx, sanitize_text
from structured_renderer import (
    extract_and_structure_docx,
    merge_structured_data,
    render_as_markdown,
    render_as_html,
    render_as_docx,
    COLLECTION_ORDER,
    COLLECTION_TITLES
)

def render_table_text(data, output_path=None):
    """
    Render data as a hierarchical table in plain text.
    
    Args:
        data: Structured data organized by collection
        output_path: Output file path (optional)
        
    Returns:
        str: Formatted text
    """
    lines = ["===================================="]
    lines.append("DATASHEETS FOR DATASETS")
    lines.append("====================================\n")
    
    # Add each collection
    for collection_id, collection in data.items():
        if not collection.get("questions"):
            continue  # Skip empty collections
            
        # Add collection header
        lines.append("+" + "=" * 78 + "+")
        title = f" {collection['title'].upper()} "
        lines.append("|" + title.center(78) + "|")
        
        # Add description
        desc_lines = [collection['description'][i:i+76] for i in range(0, len(collection['description']), 76)]
        for desc in desc_lines:
            lines.append("|" + " " + desc.ljust(76) + " |")
        
        lines.append("+" + "=" * 78 + "+")
        
        # Add header row for questions
        lines.append("| " + "QUESTION".ljust(35) + " | " + "ANSWER".ljust(39) + " |")
        lines.append("+" + "-" * 37 + "+" + "-" * 40 + "+")
        
        # Add each question and answer
        for question, answer in collection["questions"].items():
            # Split question into lines with max width of 35 chars
            q_lines = [question[i:i+33] for i in range(0, len(question), 33)]
            
            # Split answer into lines with max width of 39 chars
            a_lines = []
            for line in answer.split('\n'):
                a_lines.extend([line[i:i+37] for i in range(0, len(line), 37)])
            
            # Determine number of rows needed
            num_rows = max(len(q_lines), len(a_lines))
            
            # Add rows
            for i in range(num_rows):
                q = q_lines[i] if i < len(q_lines) else ""
                a = a_lines[i] if i < len(a_lines) else ""
                lines.append("| " + q.ljust(35) + " | " + a.ljust(39) + " |")
            
            # Add separator line
            lines.append("+" + "-" * 37 + "+" + "-" * 40 + "+")
            
        lines.append("\n")
    
    # Join lines into text
    formatted_text = "\n".join(lines)
    
    # Save to file if path provided
    if output_path:
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(formatted_text)
            
    return formatted_text

def process_docx_file(docx_path, output_dir):
    """
    Process a single DOCX file and generate all output formats.
    
    Args:
        docx_path: Path to DOCX file
        output_dir: Directory for output files
        
    Returns:
        dict: Paths to output files
    """
    logger.info(f"Processing {docx_path.name}...")
    
    # Create output file paths
    base_name = docx_path.stem
    raw_path = output_dir / f"{base_name}_raw.txt"
    txt_path = output_dir / f"{base_name}.txt"
    html_path = output_dir / f"{base_name}.html"
    
    # Extract raw text
    logger.info(f"Extracting raw text...")
    raw_text = extract_text_from_docx(docx_path)
    if raw_text:
        with open(raw_path, 'w', encoding='utf-8') as f:
            f.write(raw_text)
            
    # Extract structured data
    logger.info(f"Extracting structured data...")
    structured_data = extract_and_structure_docx(docx_path)
    
    if structured_data:
        # Create a dict with just this file's data
        merged_data = OrderedDict()
        for collection in COLLECTION_ORDER:
            merged_data[collection] = {
                "title": COLLECTION_TITLES.get(collection, collection),
                "description": "Questions about this aspect of the dataset",
                "questions": OrderedDict()
            }
        
        # Add the file's questions to the right collection
        collection = structured_data["collection"]
        merged_data[collection]["questions"] = structured_data["questions"]
        
        # Render as text table
        logger.info(f"Rendering as text table...")
        render_table_text(merged_data, txt_path)
        
        # Render as HTML
        logger.info(f"Rendering as HTML...")
        render_as_html(merged_data, html_path)
        
        return {
            "raw": str(raw_path),
            "txt": str(txt_path),
            "html": str(html_path)
        }
    else:
        logger.error(f"Could not extract structured data from {docx_path.name}")
        return {"raw": str(raw_path) if raw_text else None}

def process_directory(input_dir, output_dir):
    """
    Process all DOCX files in a directory.
    
    Args:
        input_dir: Directory containing DOCX files
        output_dir: Directory for output files
        
    Returns:
        dict: Mapping of DOCX files to output files
    """
    # Ensure input directory exists
    input_dir = Path(input_dir)
    if not input_dir.exists() or not input_dir.is_dir():
        logger.error(f"Input directory not found: {input_dir}")
        return {}
    
    # Ensure output directory exists
    output_dir = Path(output_dir)
    output_dir.mkdir(exist_ok=True, parents=True)
    
    # Find DOCX files
    docx_files = list(input_dir.glob("*.docx"))
    logger.info(f"Found {len(docx_files)} DOCX files in {input_dir}")
    
    # Process each file
    results = {}
    for docx_file in docx_files:
        results[str(docx_file)] = process_docx_file(docx_file, output_dir)
    
    return results

def process_all_files(input_dir, output_dir):
    """
    Process all files and create a combined output.
    
    Args:
        input_dir: Directory containing DOCX files
        output_dir: Directory for output files
    """
    # Process individual files
    process_directory(input_dir, output_dir)
    
    # Now create a combined version
    logger.info("Creating combined outputs...")
    
    # Process all files to extract structured data
    docx_files = list(Path(input_dir).glob("*.docx"))
    structured_data_list = []
    
    for docx_file in docx_files:
        data = extract_and_structure_docx(docx_file)
        if data:
            structured_data_list.append(data)
    
    if structured_data_list:
        # Merge data from all files
        logger.info("Merging data from all files...")
        merged_data = merge_structured_data(structured_data_list)
        
        # Create the combined outputs
        combined_raw = output_dir / "all_files_raw.txt"
        combined_txt = output_dir / "all_files.txt"
        combined_html = output_dir / "all_files.html"
        
        # For raw text, simply concatenate all raw texts
        with open(combined_raw, 'w', encoding='utf-8') as f:
            for docx_file in docx_files:
                raw_text = extract_text_from_docx(docx_file)
                if raw_text:
                    f.write(f"=== {docx_file.name} ===\n\n")
                    f.write(raw_text)
                    f.write("\n\n")
        
        # Render combined text table
        render_table_text(merged_data, combined_txt)
        
        # Render combined HTML
        render_as_html(merged_data, combined_html)
        
        logger.info(f"Combined raw text: {combined_raw}")
        logger.info(f"Combined text table: {combined_txt}")
        logger.info(f"Combined HTML: {combined_html}")

def main():
    """Main entry point for the test script."""
    parser = argparse.ArgumentParser(
        description="Test script for datasheets renderer"
    )
    parser.add_argument(
        "input",
        help="Input directory containing DOCX files"
    )
    parser.add_argument(
        "--output", "-o",
        help="Output directory for rendered files"
    )
    parser.add_argument(
        "--file", "-f",
        help="Process only a specific file"
    )
    
    args = parser.parse_args()
    
    # Set up directories
    input_dir = args.input
    output_dir = args.output or os.path.join(input_dir, "test_output")
    
    # Process files
    if args.file:
        # Process a single file
        file_path = Path(args.file)
        if not file_path.exists():
            logger.error(f"File not found: {file_path}")
            return 1
            
        if file_path.suffix.lower() != '.docx':
            logger.error(f"Not a DOCX file: {file_path}")
            return 1
            
        output_dir = Path(output_dir)
        output_dir.mkdir(exist_ok=True, parents=True)
        
        results = process_docx_file(file_path, output_dir)
        
        logger.info("Processing complete. Output files:")
        for format_name, file_path in results.items():
            if file_path:
                logger.info(f"  {format_name.upper()}: {file_path}")
    else:
        # Process all files
        process_all_files(input_dir, output_dir)
    
    return 0

if __name__ == "__main__":
    sys.exit(main())