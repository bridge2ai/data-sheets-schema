#!/usr/bin/env python3
"""
Script to process DOCX files and convert them to structured templates.
"""

import os
import sys
from pathlib import Path
import argparse
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

# Set default encoding to UTF-8
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

# Add parent directory to path to allow importing renderer package
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.renderer.converters import DocxConverter

def main():
    """Process DOCX files to YAML/JSON templates."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description='Process DOCX files to YAML/JSON templates'
    )
    parser.add_argument(
        'input_path',
        help='Path to DOCX file or directory'
    )
    parser.add_argument(
        '--output-dir', '-o',
        help='Output directory (defaults to current directory)'
    )
    parser.add_argument(
        '--format', '-f',
        choices=['yaml', 'json', 'both'],
        default='both',
        help='Output format (default: both)'
    )
    parser.add_argument(
        '--recursive', '-r',
        action='store_true',
        help='Process directories recursively'
    )
    args = parser.parse_args()
    
    # Setup output directory
    output_dir = args.output_dir
    if not output_dir:
        output_dir = os.getcwd()
    os.makedirs(output_dir, exist_ok=True)
    
    # Initialize DocxConverter
    converter = DocxConverter(output_dir=output_dir)
    
    # Process input path
    input_path = args.input_path
    
    if os.path.isdir(input_path):
        # Process directory
        logger.info(f"Processing directory: {input_path}")
        
        if args.format in ['yaml', 'both']:
            logger.info("Generating YAML templates...")
            yaml_paths = converter.process_docx_directory(
                input_path, 
                output_format='yaml',
                recursive=args.recursive
            )
            logger.info(f"Generated {len(yaml_paths)} YAML templates")
        
        if args.format in ['json', 'both']:
            logger.info("Generating JSON templates...")
            json_paths = converter.process_docx_directory(
                input_path, 
                output_format='json',
                recursive=args.recursive
            )
            logger.info(f"Generated {len(json_paths)} JSON templates")
    
    elif os.path.isfile(input_path) and input_path.lower().endswith('.docx'):
        # Process single file
        logger.info(f"Processing file: {input_path}")
        
        if args.format in ['yaml', 'both']:
            yaml_path = converter.convert_docx_to_template(input_path, output_format='yaml')
            if yaml_path:
                logger.info(f"Generated YAML template: {yaml_path}")
            else:
                logger.error(f"Failed to generate YAML template for {input_path}")
        
        if args.format in ['json', 'both']:
            json_path = converter.convert_docx_to_template(input_path, output_format='json')
            if json_path:
                logger.info(f"Generated JSON template: {json_path}")
            else:
                logger.error(f"Failed to generate JSON template for {input_path}")
    
    else:
        logger.error(f"Invalid input path: {input_path}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())