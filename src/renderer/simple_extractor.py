#!/usr/bin/env python3
"""
Simple text extractor for DOCX files with Unicode character handling.

This module provides a very minimal extractor that safely handles
Unicode characters in DOCX files and saves them as UTF-8 text.
"""

import os
import sys
import io
import re
from pathlib import Path
import docx
import logging

# Configure stdout/stderr to use UTF-8
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Fix environment encoding
os.environ['PYTHONIOENCODING'] = 'utf-8'

def sanitize_text(text):
    """Replace problematic Unicode characters with ASCII equivalents."""
    if not text:
        return text
        
    # Define replacements for problematic characters
    replacements = {
        '\u2022': '*',    # bullet
        '\u2019': "'",    # right single quotation mark
        '\u2018': "'",    # left single quotation mark
        '\u201C': '"',    # left double quotation mark
        '\u201D': '"',    # right double quotation mark
        '\u2013': '-',    # en dash
        '\u2014': '--',   # em dash
        '\u2026': '...',  # horizontal ellipsis
        '\u00A0': ' ',    # non-breaking space
    }
    
    # Apply replacements
    for unicode_char, ascii_char in replacements.items():
        text = text.replace(unicode_char, ascii_char)
        
    return text

def extract_text_from_docx(docx_path, output_path=None):
    """
    Extract text from a DOCX file and save it with UTF-8 encoding.
    
    Args:
        docx_path: Path to the DOCX file
        output_path: Path to save the extracted text (optional)
        
    Returns:
        str: The extracted text if successful, None otherwise
    """
    try:
        # Convert path to Path object if it's a string
        docx_path = Path(docx_path)
        
        # Check if file exists
        if not docx_path.exists():
            logger.error(f"File not found: {docx_path}")
            return None
            
        # Open the document
        doc = docx.Document(docx_path)
        
        # Extract text from paragraphs
        paragraphs = []
        for para in doc.paragraphs:
            text = para.text.strip()
            if text:
                # Sanitize Unicode characters
                text = sanitize_text(text)
                paragraphs.append(text)
        
        # Join paragraphs with newlines
        extracted_text = '\n'.join(paragraphs)
        
        # Save to file if output path is provided
        if output_path:
            # Create output directory if needed
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Save text with UTF-8 encoding
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(extracted_text)
                
            logger.info(f"Text saved to {output_path}")
            
        return extracted_text
        
    except Exception as e:
        logger.error(f"Error extracting text from {docx_path}: {str(e)}")
        return None

def process_directory(input_dir, output_dir=None):
    """
    Process all DOCX files in a directory.
    
    Args:
        input_dir: Directory containing DOCX files
        output_dir: Directory to save extracted text files (optional)
        
    Returns:
        int: Number of successfully processed files
    """
    # Convert input directory to Path
    input_dir = Path(input_dir)
    if not input_dir.exists() or not input_dir.is_dir():
        logger.error(f"Input directory not found: {input_dir}")
        return 0
    
    # Set default output directory if not provided
    if not output_dir:
        output_dir = input_dir / "txt"
    else:
        output_dir = Path(output_dir)
    
    # Create output directory
    output_dir.mkdir(exist_ok=True)
    
    # Process files
    success_count = 0
    file_count = 0
    
    # Find all DOCX files in the directory
    docx_files = list(input_dir.glob("*.docx"))
    logger.info(f"Found {len(docx_files)} DOCX files in {input_dir}")
    
    for docx_file in docx_files:
        file_count += 1
        try:
            # Create output path
            output_file = output_dir / f"{docx_file.stem}.txt"
            
            # Process file
            logger.info(f"Processing {docx_file.name}...")
            if extract_text_from_docx(docx_file, output_file):
                success_count += 1
                logger.info(f"Successfully processed {docx_file.name}")
            else:
                logger.error(f"Failed to process {docx_file.name}")
                
        except Exception as e:
            logger.error(f"Error processing {docx_file.name}: {str(e)}")
    
    logger.info(f"Processed {file_count} files, {success_count} successful")
    return success_count

def main():
    """Command-line interface for the text extractor."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Extract text from DOCX files with Unicode handling")
    parser.add_argument("input", help="DOCX file or directory containing DOCX files")
    parser.add_argument("--output", "-o", help="Output file or directory for extracted text")
    
    args = parser.parse_args()
    
    # Determine if input is a file or directory
    input_path = Path(args.input)
    if input_path.is_file():
        if input_path.suffix.lower() == '.docx':
            # Process single file
            logger.info(f"Processing single file: {input_path}")
            
            # Determine output path
            output_path = None
            if args.output:
                output_path = args.output
            else:
                output_path = input_path.with_suffix('.txt')
                
            # Extract text
            if extract_text_from_docx(input_path, output_path):
                logger.info(f"Successfully extracted text to {output_path}")
                return 0
            else:
                logger.error(f"Failed to extract text from {input_path}")
                return 1
        else:
            logger.error(f"Input file is not a DOCX file: {input_path}")
            return 1
    elif input_path.is_dir():
        # Process directory
        logger.info(f"Processing directory: {input_path}")
        success_count = process_directory(input_path, args.output)
        logger.info(f"Successfully processed {success_count} files")
        return 0
    else:
        logger.error(f"Input path not found: {input_path}")
        return 1

if __name__ == "__main__":
    sys.exit(main())