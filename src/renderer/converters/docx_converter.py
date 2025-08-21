#!/usr/bin/env python3
"""
DOCX converter for Datasheets schema.

This module provides utilities to extract YAML-like content from Word documents
and convert it to structured template data.
"""

import os
import re
import json
import yaml
import sys

# Set default encoding to UTF-8
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')
if sys.stderr.encoding != 'utf-8':
    sys.stderr.reconfigure(encoding='utf-8')
from pathlib import Path
import logging
import docx
from docx.opc.exceptions import PackageNotFoundError

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class DocxConverter:
    """Extract and convert content from DOCX files to structured template data."""
    
    def __init__(self, output_dir=None):
        """
        Initialize the converter with output directory.
        
        Args:
            output_dir: Directory for output files. If None, uses default location.
        """
        if output_dir is None:
            # Default to output directory relative to this file
            self.output_dir = Path(os.path.dirname(os.path.abspath(__file__))) / '..' / '..' / 'output'
        else:
            self.output_dir = Path(output_dir)
            
        # Ensure output directory exists
        os.makedirs(self.output_dir, exist_ok=True)
        
    def extract_text_from_docx(self, docx_path):
        """
        Extract text content from a DOCX file.
        
        Args:
            docx_path: Path to the DOCX file.
            
        Returns:
            str: Text content of the DOCX file
        """
        try:
            doc = docx.Document(docx_path)
            
            # Extract text from paragraphs with character replacement for problematic Unicode
            paragraphs = []
            for para in doc.paragraphs:
                # Get the text and sanitize problematic characters
                text = para.text.strip()
                
                # Replace problematic characters with ASCII equivalents
                text = text.replace('\u2022', '*')  # Replace bullet with asterisk
                text = text.replace('\u2019', "'")  # Replace right single quotation mark with straight apostrophe
                text = text.replace('\u2018', "'")  # Replace left single quotation mark with straight apostrophe
                text = text.replace('\u201C', '"')  # Replace left double quotation mark with straight quote
                text = text.replace('\u201D', '"')  # Replace right double quotation mark with straight quote
                text = text.replace('\u2013', '-')  # Replace en dash with hyphen
                text = text.replace('\u2014', '--')  # Replace em dash with double hyphen
                text = text.replace('\u2026', '...')  # Replace ellipsis with three dots
                
                if text:
                    paragraphs.append(text)
            
            return '\n'.join(paragraphs)
        except PackageNotFoundError:
            logger.error(f"File is not a valid DOCX file: {docx_path}")
            return None
        except Exception as e:
            logger.error(f"Error extracting text from DOCX file {docx_path}: {e}")
            return None
    
    def extract_yaml_like_content(self, text):
        """
        Extract YAML-like content from text.
        
        Args:
            text: Text content to extract YAML-like content from.
            
        Returns:
            str: YAML-like content
        """
        if not text:
            return None
            
        # Sanitize any unicode characters that might be problematic
        # (in case they were missed in text extraction)
        text = text.replace('\u2022', '*')  # Replace bullet with asterisk
        text = text.replace('\u2019', "'")  # Replace right single quotation mark
        text = text.replace('\u2018', "'")  # Replace left single quotation mark
        text = text.replace('\u201C', '"')  # Replace left double quotation mark
        text = text.replace('\u201D', '"')  # Replace right double quotation mark
        text = text.replace('\u2013', '-')  # Replace en dash
        text = text.replace('\u2014', '--')  # Replace em dash
        text = text.replace('\u2026', '...')  # Replace ellipsis
            
        # Extract content between "---" markers
        yaml_pattern = r"---\s*\n(.*?)---"
        yaml_matches = re.findall(yaml_pattern, text, re.DOTALL)
        
        if yaml_matches:
            # Use the first YAML block found
            return yaml_matches[0].strip()
        
        # If no YAML blocks are found, try to infer structure from headings
        lines = text.split('\n')
        yaml_content = []
        current_section = None
        
        for line in lines:
            # Sanitize each line (again, just to be sure)
            line = line.strip()
            line = line.replace('\u2022', '*')
            line = line.replace('\u2019', "'")
            
            if not line:
                continue
                
            # Check if line might be a heading
            if re.match(r"^#+\s+", line) or line.isupper() or line.endswith(':'):
                # This looks like a heading
                heading = line.lstrip('#').strip().rstrip(':')
                yaml_content.append(f"\n{heading}:")
                current_section = heading
            elif current_section:
                # Indent content under current section
                yaml_content.append(f"  {line}")
        
        return '\n'.join(yaml_content).strip()
    
    def parse_yaml_content(self, yaml_content):
        """
        Parse YAML-like content to a structured dictionary.
        
        Args:
            yaml_content: YAML-like content to parse.
            
        Returns:
            dict: Parsed YAML content as a dictionary
        """
        if not yaml_content:
            return None
            
        try:
            # Try to parse as valid YAML
            parsed_content = yaml.safe_load(yaml_content)
            if isinstance(parsed_content, dict):
                return parsed_content
        except Exception as e:
            logger.warning(f"Failed to parse as valid YAML: {e}")
            
        # If parsing as YAML fails, attempt more liberal parsing
        sections = {}
        current_section = None
        current_content = []
        
        lines = yaml_content.split('\n')
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Check if line might be a section heading
            if not line.startswith(' '):
                if current_section and current_content:
                    sections[current_section] = '\n'.join(current_content).strip()
                current_section = line.rstrip(':')
                current_content = []
            else:
                if current_section:
                    current_content.append(line)
        
        # Add the last section
        if current_section and current_content:
            sections[current_section] = '\n'.join(current_content).strip()
            
        return sections
    
    def convert_docx_to_template(self, docx_path, output_format='yaml'):
        """
        Convert a DOCX file to a structured template.
        
        Args:
            docx_path: Path to the DOCX file.
            output_format: Output format ('yaml' or 'json').
            
        Returns:
            str: Path to the generated file or None if error
        """
        try:
            # Extract text content
            text_content = self.extract_text_from_docx(docx_path)
            if not text_content:
                return None
                
            # Extract YAML-like content
            yaml_content = self.extract_yaml_like_content(text_content)
            if not yaml_content:
                logger.warning(f"No YAML-like content found in {docx_path}")
                return None
                
            # Parse YAML content
            parsed_content = self.parse_yaml_content(yaml_content)
            if not parsed_content:
                logger.warning(f"Failed to parse YAML content from {docx_path}")
                return None
                
            # Determine output path
            docx_name = Path(docx_path).stem
            if output_format.lower() == 'json':
                output_path = self.output_dir / f"{docx_name}.json"
                
                # Write JSON
                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump(parsed_content, f, indent=2, ensure_ascii=False)
            else:
                output_path = self.output_dir / f"{docx_name}.yaml"
                
                # Write YAML
                with open(output_path, 'w', encoding='utf-8') as f:
                    yaml.dump(parsed_content, f, default_flow_style=False, 
                             sort_keys=False, allow_unicode=True)
                
            logger.info(f"Successfully converted {docx_path} to {output_path}")
            return str(output_path)
        except Exception as e:
            logger.error(f"Error converting DOCX file {docx_path}: {e}")
            return None
    
    def process_docx_directory(self, directory_path, output_format='yaml', recursive=False):
        """
        Process all DOCX files in a directory.
        
        Args:
            directory_path: Path to the directory containing DOCX files.
            output_format: Output format ('yaml' or 'json').
            recursive: Whether to process subdirectories.
            
        Returns:
            list: Paths to the generated files
        """
        directory_path = Path(directory_path)
        if not directory_path.exists() or not directory_path.is_dir():
            logger.error(f"Directory not found: {directory_path}")
            return []
            
        output_paths = []
        pattern = '**/*.docx' if recursive else '*.docx'
        
        for docx_path in directory_path.glob(pattern):
            # Handle file name as a Path object to avoid encoding issues
            file_name = docx_path.name
            try:
                # Safely print to console with encoding handling
                logger.info(f"Processing {file_name}...")
                
                output_path = self.convert_docx_to_template(docx_path, output_format)
                if output_path:
                    output_paths.append(output_path)
                    logger.info(f"Successfully processed {file_name}")
                else:
                    logger.error(f"Failed to process {file_name}")
            except UnicodeEncodeError as e:
                # Handle unicode encoding errors specially
                logger.error(f"Unicode encoding error processing {file_name}: {str(e)}")
                
                # Try to sanitize problematic characters in file content
                try:
                    # Extract text content with special character handling
                    text_content = self.extract_text_from_docx(docx_path)
                    if text_content:
                        # Sanitize text by replacing problematic characters
                        text_content = text_content.replace('\u2022', '*')  # Replace bullet with asterisk
                        text_content.replace('\u2019', "'")  # Replace curly apostrophe with straight one
                        
                        # Continue processing with sanitized text
                        yaml_content = self.extract_yaml_like_content(text_content)
                        if yaml_content:
                            parsed_content = self.parse_yaml_content(yaml_content)
                            if parsed_content:
                                # Determine output path
                                docx_name = Path(docx_path).stem
                                if output_format.lower() == 'json':
                                    output_path = self.output_dir / f"{docx_name}.json"
                                    
                                    # Write JSON
                                    with open(output_path, 'w', encoding='utf-8') as f:
                                        json.dump(parsed_content, f, indent=2, ensure_ascii=False)
                                else:
                                    output_path = self.output_dir / f"{docx_name}.yaml"
                                    
                                    # Write YAML
                                    with open(output_path, 'w', encoding='utf-8') as f:
                                        yaml.dump(parsed_content, f, default_flow_style=False, 
                                                 sort_keys=False, allow_unicode=True)
                                
                                logger.info(f"Successfully processed {file_name} with character sanitization")
                                output_paths.append(str(output_path))
                except Exception as e2:
                    logger.error(f"Failed even with character sanitization for {file_name}: {str(e2)}")
            except Exception as e:
                # Handle other errors
                logger.error(f"Error processing {file_name}: {str(e)}")
                
        return output_paths

# Example usage
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python docx_converter.py <docx_path_or_directory> [--json] [--recursive]")
        sys.exit(1)
        
    path = sys.argv[1]
    output_format = 'json' if '--json' in sys.argv else 'yaml'
    recursive = '--recursive' in sys.argv
    
    converter = DocxConverter()
    
    if os.path.isdir(path):
        output_paths = converter.process_docx_directory(path, output_format, recursive)
        print(f"Processed {len(output_paths)} DOCX files.")
    else:
        output_path = converter.convert_docx_to_template(path, output_format)
        if output_path:
            print(f"Converted {path} to {output_path}")