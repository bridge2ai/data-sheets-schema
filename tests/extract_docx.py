#!/usr/bin/env python3
"""
Extract and render JSON from Word documents

This script:
1. Extracts text content from .docx files
2. Searches for JSON content within the extracted text
3. Renders any found JSON data in TXT, HTML, and PDF formats
"""

import os
import sys
import re
import json
import glob
import argparse
from typing import Dict, Any, List, Optional, Union, Tuple
from pathlib import Path
import zipfile
import tempfile
import io
import xml.etree.ElementTree as ET

# For docx handling
try:
    from docx import Document
    HAS_DOCX = True
except ImportError:
    HAS_DOCX = False
    print("python-docx not available. Install with: pip install python-docx")

# For YAML handling
try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False
    print("PyYAML not available. YAML parsing will be disabled.")
    print("Install with: pip install pyyaml")

# For HTML rendering
from datetime import datetime
from jinja2 import Template

# For PDF rendering
try:
    from weasyprint import HTML
    HAS_WEASYPRINT = True
except ImportError:
    HAS_WEASYPRINT = False
    print("WeasyPrint not available. PDF generation will be disabled.")
    print("Install with: pip install weasyprint")

# For LinkML rendering
try:
    # Using linkml-runtime directly for proper rendering
    import os
    import tempfile
    import subprocess
    import io
    from linkml_runtime.utils.schemaview import SchemaView
    from linkml_runtime.dumpers import json_dumper, yaml_dumper
    HAS_LINKML_RUNTIME = True
except ImportError:
    HAS_LINKML_RUNTIME = False
    print("LinkML-runtime not available. LinkML PDF generation will be disabled.")
    print("Install with: pip install linkml-runtime")


class DocxProcessor:
    """Class to extract and process content from Word documents"""
    
    def __init__(self, output_dir: str = "output"):
        """Initialize with output directory"""
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        
    def extract_text_from_docx(self, file_path: str) -> str:
        """Extract text content from a .docx file"""
        if not HAS_DOCX:
            # Fallback method using zipfile if python-docx isn't available
            return self._extract_text_using_zipfile(file_path)
        
        try:
            doc = Document(file_path)
            full_text = []
            
            for para in doc.paragraphs:
                full_text.append(para.text)
                
            # Join text with newlines to preserve paragraph breaks
            return '\n'.join(full_text)
        except Exception as e:
            print(f"Error extracting text from {file_path}: {e}")
            # Try zipfile method as fallback
            return self._extract_text_using_zipfile(file_path)
    
    def _extract_text_using_zipfile(self, file_path: str) -> str:
        """Extract text from docx using zipfile (fallback method)"""
        try:
            text = []
            with zipfile.ZipFile(file_path) as docx_zip:
                if 'word/document.xml' in docx_zip.namelist():
                    content = docx_zip.read('word/document.xml')
                    root = ET.fromstring(content)
                    # This is a simplified extraction - it won't get all formatting
                    for elem in root.iter():
                        if elem.tag.endswith('}t'):  # Text elements
                            if elem.text:
                                text.append(elem.text)
            return '\n'.join(text)
        except Exception as e:
            print(f"Error extracting text with zipfile from {file_path}: {e}")
            return ""

    def extract_data_from_text(self, text: str) -> Tuple[List[Dict[str, Any]], str]:
        """Extract both JSON and YAML data from text content"""
        extracted_data = []
        data_format = "none"
        
        # First try to extract JSON
        json_data = self._extract_json_from_text(text)
        if json_data:
            extracted_data.extend(json_data)
            data_format = "json"
        
        # Then try to extract YAML if available
        if HAS_YAML:
            yaml_data = self._extract_yaml_from_text(text)
            if yaml_data:
                extracted_data.extend(yaml_data)
                data_format = "yaml" if not json_data else "mixed"
        
        return extracted_data, data_format
    
    def _extract_json_from_text(self, text: str) -> List[Dict[str, Any]]:
        """Extract JSON objects from text content"""
        # This regex looks for patterns that might be JSON objects
        json_candidates = []
        
        # Try to find JSON-like structures with different bracket patterns
        patterns = [
            r'\{[^{}]*\{[^{}]*\}[^{}]*\}',  # Nested braces
            r'\{[^{}]*\}',                  # Simple braces
            r'\[[^[\]]*\{[^{}]*\}[^[\]]*\]', # Array with objects
            r'\[\s*\{[^[]*\}\s*\]'          # Simple array of objects
        ]
        
        extracted_jsons = []
        
        for pattern in patterns:
            matches = re.finditer(pattern, text)
            for match in matches:
                json_str = match.group(0)
                # Try to parse the string as JSON
                try:
                    parsed_json = json.loads(json_str)
                    extracted_jsons.append(parsed_json)
                except json.JSONDecodeError:
                    # Try to clean up and try again
                    try:
                        # Remove extra whitespace, fix common issues
                        cleaned = re.sub(r',\s*}', '}', json_str)
                        cleaned = re.sub(r',\s*]', ']', cleaned)
                        parsed_json = json.loads(cleaned)
                        extracted_jsons.append(parsed_json)
                    except json.JSONDecodeError:
                        continue
        
        return extracted_jsons
    
    def _extract_yaml_from_text(self, text: str) -> List[Dict[str, Any]]:
        """Extract YAML objects from text content"""
        if not HAS_YAML:
            return []
            
        # YAML blocks often start with --- and end with ... or just have indentation
        # This is a simplified approach - we'll look for potential YAML blocks
        extracted_yaml = []
        
        # Try to find YAML blocks with --- markers
        yaml_blocks = re.split(r'---\s*\n', text)
        if len(yaml_blocks) > 1:
            # Skip the first block (text before first ---)
            for block in yaml_blocks[1:]:
                # If there's a ... marker, only take up to that
                if '...' in block:
                    block = block.split('...')[0]
                    
                # Try to parse as YAML
                try:
                    parsed_yaml = yaml.safe_load(block)
                    if isinstance(parsed_yaml, dict):
                        extracted_yaml.append(parsed_yaml)
                except Exception:
                    continue
        
        # Also look for indented blocks that might be YAML
        # This is more complex, so we'll use a simplified approach
        lines = text.split('\n')
        potential_yaml_blocks = []
        current_block = []
        in_block = False
        
        for line in lines:
            # If line starts with whitespace, it might be part of a YAML block
            if line.strip() and line[0].isspace():
                if not in_block:
                    in_block = True
                current_block.append(line)
            else:
                # If we were in a block and hit a non-indented line
                if in_block and current_block:
                    potential_yaml_blocks.append('\n'.join(current_block))
                    current_block = []
                    in_block = False
        
        # Don't forget the last block
        if in_block and current_block:
            potential_yaml_blocks.append('\n'.join(current_block))
        
        # Try to parse each potential block
        for block in potential_yaml_blocks:
            try:
                parsed_yaml = yaml.safe_load(block)
                if isinstance(parsed_yaml, dict):
                    extracted_yaml.append(parsed_yaml)
            except Exception:
                continue
        
        return extracted_yaml

    def organize_data(self, data: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        """Organize data by category for rendering"""
        # Define main collection categories
        collections = {
            "Motivation": {},
            "Composition": {},
            "Collection": {},
            "Preprocessing": {},
            "Uses": {},
            "Distribution": {},
            "Maintenance": {},
            "Metadata": {},  # Default category
        }
        
        # Process each data object (could be from JSON or YAML)
        for item_idx, item in enumerate(data):
            if isinstance(item, dict):
                # Use first-level categorization if available
                assigned = False
                
                # Try to categorize based on keys or values
                for key, value in item.items():
                    for collection in collections.keys():
                        # Skip "Metadata" as it's our default
                        if collection == "Metadata":
                            continue
                            
                        # Check if the collection name appears in the key or value
                        if (collection.lower() in key.lower() or
                            (isinstance(value, str) and collection.lower() in value.lower())):
                            collections[collection][f"Item_{item_idx}_{key}"] = item
                            assigned = True
                            break
                    
                    if assigned:
                        break
                
                # If not assigned to a specific collection, put in Metadata
                if not assigned:
                    collections["Metadata"][f"Item_{item_idx}"] = item
            elif isinstance(item, list):
                # For arrays, add each item to the appropriate collection
                collections["Metadata"][f"Array_{item_idx}"] = item
        
        # Remove empty collections
        return {k: v for k, v in collections.items() if v}

    def render_as_text(self, data: Dict[str, Dict[str, Any]], title: str = "Data Sheet") -> str:
        """Render data as hierarchical text"""
        output = []
        output.append(f"{title.upper()} REPORT")
        output.append("=" * 80)
        output.append("")
        
        if not data:
            output.append("No JSON data found in document.")
            return "\n".join(output)
        
        for collection, items in data.items():
            if not items:
                continue
                
            output.append(f"COLLECTION: {collection}")
            output.append("-" * 80)
            
            for key, value in items.items():
                output.append(f"  {key}:")
                
                # Format the value based on its type
                if isinstance(value, dict):
                    for sub_key, sub_value in value.items():
                        formatted_value = json.dumps(sub_value, indent=2) if isinstance(sub_value, (dict, list)) else sub_value
                        output.append(f"    {sub_key}: {formatted_value}")
                elif isinstance(value, list):
                    for i, item in enumerate(value):
                        if isinstance(item, dict):
                            output.append(f"    - Item {i+1}:")
                            for sub_key, sub_value in item.items():
                                formatted_value = json.dumps(sub_value, indent=2) if isinstance(sub_value, (dict, list)) else sub_value
                                output.append(f"      {sub_key}: {formatted_value}")
                        else:
                            output.append(f"    - {item}")
                else:
                    output.append(f"    {value}")
                
                output.append("")
            
            output.append("")
        
        return "\n".join(output)
    
    def render_as_html(self, data: Dict[str, Dict[str, Any]], title: str = "Data Sheet") -> str:
        """Render data as HTML"""
        html_template = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>{{ title }} Report</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 20px; }
                h1 { color: #2c3e50; }
                .collection { margin-bottom: 30px; }
                .collection h2 { 
                    background-color: #3498db; 
                    color: white; 
                    padding: 10px; 
                    border-radius: 5px;
                }
                .item { margin-left: 20px; margin-bottom: 15px; }
                .item h3 { color: #2980b9; }
                .value { margin-left: 20px; }
                .metadata { color: #7f8c8d; font-style: italic; }
                .timestamp { margin-top: 30px; color: #95a5a6; font-size: 0.8em; }
                pre { background-color: #f8f9fa; padding: 10px; border-radius: 5px; overflow-x: auto; }
                .no-data { color: #e74c3c; font-style: italic; }
            </style>
        </head>
        <body>
            <h1>{{ title }} Report</h1>
            
            {% if data %}
                {% for collection_name, items in data.items() %}
                {% if items %}
                <div class="collection">
                    <h2>{{ collection_name }}</h2>
                    
                    {% for key, value in items.items() %}
                    <div class="item">
                        <h3>{{ key }}</h3>
                        <div class="value">
                        {% if value is mapping %}
                            {% for sub_key, sub_value in value.items() %}
                                <p><strong>{{ sub_key }}:</strong> 
                                {% if sub_value is mapping or (sub_value is iterable and sub_value is not string) %}
                                    <pre>{{ sub_value|tojson(indent=2) }}</pre>
                                {% else %}
                                    {{ sub_value }}
                                {% endif %}
                                </p>
                            {% endfor %}
                        {% elif value is iterable and value is not string %}
                            <ul>
                            {% for item in value %}
                                {% if item is mapping %}
                                <li>
                                    {% for sub_key, sub_value in item.items() %}
                                    <p><strong>{{ sub_key }}:</strong>
                                    {% if sub_value is mapping or (sub_value is iterable and sub_value is not string) %}
                                        <pre>{{ sub_value|tojson(indent=2) }}</pre>
                                    {% else %}
                                        {{ sub_value }}
                                    {% endif %}
                                    </p>
                                    {% endfor %}
                                </li>
                                {% else %}
                                <li>{{ item }}</li>
                                {% endif %}
                            {% endfor %}
                            </ul>
                        {% else %}
                            <p>{{ value }}</p>
                        {% endif %}
                        </div>
                    </div>
                    {% endfor %}
                </div>
                {% endif %}
                {% endfor %}
            {% else %}
                <p class="no-data">No JSON data found in document.</p>
            {% endif %}
            
            <div class="timestamp">Generated on: {{ timestamp }}</div>
        </body>
        </html>
        """
        
        # Define custom filter to convert to JSON with indentation
        def tojson_filter(obj, indent=None):
            return json.dumps(obj, indent=indent)
        
        # Create template environment with custom filter
        from jinja2 import Environment
        env = Environment()
        env.filters['tojson'] = tojson_filter
        template = env.from_string(html_template)
        
        return template.render(
            title=title,
            data=data,
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        )
    
    def process_docx_file(self, file_path: str) -> Tuple[bool, List[str]]:
        """Process a docx file and generate output files"""
        # Extract base filename for output
        base_name = os.path.basename(file_path)
        name_without_ext = os.path.splitext(base_name)[0]
        output_base = os.path.join(self.output_dir, name_without_ext)
        
        # Extract text from the docx
        print(f"Extracting text from {file_path}...")
        extracted_text = self.extract_text_from_docx(file_path)
        
        if not extracted_text:
            print(f"No text could be extracted from {file_path}")
            return False, []
        
        # Save the raw extracted text
        with open(f"{output_base}_raw.txt", 'w', encoding='utf-8') as f:
            f.write(extracted_text)
        
        # Extract data (JSON or YAML) from the text
        data, data_format = self.extract_data_from_text(extracted_text)
        
        if not data:
            print(f"No JSON or YAML data found in {file_path}")
            # Still create empty outputs to show we processed the file
            empty_data = {}
            
            with open(f"{output_base}.txt", 'w', encoding='utf-8') as f:
                f.write(self.render_as_text(empty_data, name_without_ext))
            
            with open(f"{output_base}.html", 'w', encoding='utf-8') as f:
                f.write(self.render_as_html(empty_data, name_without_ext))
                
            return False, [f"{output_base}_raw.txt", f"{output_base}.txt", f"{output_base}.html"]
        
        # Save the raw data
        if data_format == "json":
            with open(f"{output_base}_data.json", 'w', encoding='utf-8') as f:
                f.write(json.dumps(data, indent=2))
        elif data_format == "yaml" and HAS_YAML:
            with open(f"{output_base}_data.yaml", 'w', encoding='utf-8') as f:
                yaml.dump(data, f, default_flow_style=False, sort_keys=False)
        elif data_format == "mixed":
            # Save both formats
            with open(f"{output_base}_data.json", 'w', encoding='utf-8') as f:
                f.write(json.dumps(data, indent=2))
            if HAS_YAML:
                with open(f"{output_base}_data.yaml", 'w', encoding='utf-8') as f:
                    yaml.dump(data, f, default_flow_style=False, sort_keys=False)
        
        # Organize data for rendering
        organized_data = self.organize_data(data)
        
        # Render and save text format
        text_output = self.render_as_text(organized_data, name_without_ext)
        with open(f"{output_base}.txt", 'w', encoding='utf-8') as f:
            f.write(text_output)
        
        # Render and save HTML format
        html_output = self.render_as_html(organized_data, name_without_ext)
        with open(f"{output_base}.html", 'w', encoding='utf-8') as f:
            f.write(html_output)
        
        # Generate outputs
        output_files = [f"{output_base}_raw.txt"]
        
        # Add data files to the list
        if data_format in ["json", "mixed"]:
            output_files.append(f"{output_base}_data.json")
        if data_format in ["yaml", "mixed"] and HAS_YAML:
            output_files.append(f"{output_base}_data.yaml")
            
        # Add rendered output files
        output_files.extend([f"{output_base}.txt", f"{output_base}.html"])
        
        # Generate standard PDF if WeasyPrint is available
        if HAS_WEASYPRINT:
            try:
                HTML(string=html_output).write_pdf(f"{output_base}.pdf")
                print(f"Generated PDF: {output_base}.pdf")
                output_files.append(f"{output_base}.pdf")
            except Exception as e:
                print(f"Error generating PDF: {e}")
        
        # Generate a LinkML-based visualization using the real data-sheets-schema
        if HAS_LINKML_RUNTIME and (data_format in ["json", "yaml", "mixed"]):
            try:
                linkml_pdf_path = f"{output_base}_linkml.pdf"
                linkml_html_path = f"{output_base}_linkml.html"
                
                # Use the first data format available 
                data_path = f"{output_base}_data.json" if data_format in ["json", "mixed"] else f"{output_base}_data.yaml"
                
                # Path to the LinkML schema
                schema_path = '/Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/src/data_sheets_schema/schema/data_sheets_schema.yaml'
                
                if os.path.exists(schema_path):
                    # Load schema
                    schema_view = SchemaView(schema_path)
                    
                    # Load the data
                    with open(data_path, 'r') as f:
                        if data_path.endswith('.json'):
                            data_obj = json.load(f)
                        else:
                            data_obj = yaml.safe_load(f)
                
                    # Create a LinkML-compliant HTML template
                    linkml_html_template = """
                    <!DOCTYPE html>
                    <html>
                    <head>
                        <title>{{ title }} - LinkML Report</title>
                        <style>
                            body { font-family: sans-serif; color: #333; line-height: 1.5; margin: 2em; }
                            h1, h2, h3 { color: #2c3e50; }
                            h1 { border-bottom: 2px solid #3498db; padding-bottom: 5px; }
                            h2 { border-bottom: 1px solid #3498db; padding-bottom: 3px; margin-top: 1.5em; }
                            .metadata { font-style: italic; color: #7f8c8d; margin-bottom: 2em; }
                            .class-section { margin-bottom: 20px; padding: 15px; border: 1px solid #ddd; background-color: #f9f9f9; border-radius: 5px; }
                            .class-name { font-weight: bold; color: #2980b9; }
                            .slot { margin: 10px 0; border-left: 3px solid #3498db; padding-left: 10px; }
                            .slot-name { font-weight: bold; color: #16a085; }
                            .slot-value { margin-left: 10px; }
                            .complex-value { margin-left: 20px; border-left: 1px dashed #bdc3c7; padding-left: 10px; }
                            pre { background-color: #f0f0f0; padding: 10px; overflow-x: auto; border-radius: 3px; }
                            .timestamp { margin-top: 30px; color: #95a5a6; font-size: 0.8em; }
                            .note { background-color: #eaf2f8; padding: 10px; border-left: 5px solid #3498db; margin: 15px 0; }
                        </style>
                    </head>
                    <body>
                        <h1>{{ title }} - Data Sheet</h1>
                        <p class="metadata">Generated using Bridge2AI Data Sheets Schema</p>
                        <div class="note">
                            <p>This report shows data from a data sheet document following the Bridge2AI Data Sheets Schema.</p>
                            <p>Schema ID: <code>https://w3id.org/bridge2ai/data-sheets-schema</code></p>
                        </div>
                        
                        {% for section_name, items in data.items() %}
                        <div class="class-section">
                            <h2>{{ section_name }}</h2>
                            
                            {% for key, value in items.items() %}
                            <div class="slot">
                                <h3 class="slot-name">{{ key }}</h3>
                                <div class="slot-value">
                                {% if value is mapping %}
                                    <div class="complex-value">
                                    {% for sub_key, sub_value in value.items() %}
                                        <div>
                                            <span class="slot-name">{{ sub_key }}:</span>
                                            {% if sub_value is mapping or (sub_value is iterable and sub_value is not string) %}
                                                <pre>{{ sub_value|tojson(indent=2) }}</pre>
                                            {% else %}
                                                {{ sub_value }}
                                            {% endif %}
                                        </div>
                                    {% endfor %}
                                    </div>
                                {% elif value is iterable and value is not string %}
                                    <pre>{{ value|tojson(indent=2) }}</pre>
                                {% else %}
                                    {{ value }}
                                {% endif %}
                                </div>
                            </div>
                            {% endfor %}
                        </div>
                        {% endfor %}
                        
                        <div class="timestamp">Generated on: {{ timestamp }}</div>
                    </body>
                    </html>
                    """
                    
                    # Define custom filter to convert to JSON with indentation
                    def tojson_filter(obj, indent=None):
                        return json.dumps(obj, indent=indent)
                    
                    # Create template environment with custom filter
                    from jinja2 import Environment
                    env = Environment()
                    env.filters['tojson'] = tojson_filter
                    template = env.from_string(linkml_html_template)
                    
                    # Render HTML using our organized data and the real schema
                    html_content = template.render(
                        title=name_without_ext,
                        data=organized_data,
                        timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    )
                    
                    with open(linkml_html_path, 'w', encoding='utf-8') as f:
                        f.write(html_content)
                    
                    # Convert the LinkML HTML to PDF using WeasyPrint if available
                    if HAS_WEASYPRINT:
                        HTML(filename=linkml_html_path).write_pdf(linkml_pdf_path)
                        print(f"Generated LinkML PDF: {linkml_pdf_path}")
                        output_files.append(linkml_pdf_path)
                    
                    # Add the LinkML HTML to output files
                    print(f"Generated LinkML HTML: {linkml_html_path}")
                    output_files.append(linkml_html_path)
                else:
                    print(f"Data Sheets Schema not found at {schema_path}")
            except Exception as e:
                print(f"Error generating LinkML output: {e}")
        
        print(f"Processed: {file_path}")
        print(f"  - Raw text: {output_base}_raw.txt")
        print(f"  - Data format: {data_format}")
        if data_format in ["json", "mixed"]:
            print(f"  - JSON data: {output_base}_data.json")
        if data_format in ["yaml", "mixed"] and HAS_YAML:
            print(f"  - YAML data: {output_base}_data.yaml")
        print(f"  - Text report: {output_base}.txt")
        print(f"  - HTML report: {output_base}.html")
        if HAS_WEASYPRINT:
            print(f"  - PDF report: {output_base}.pdf")
        if HAS_LINKML_RUNTIME and (data_format in ["json", "yaml", "mixed"]):
            print(f"  - LinkML HTML report: {output_base}_linkml.html")
            if HAS_WEASYPRINT:
                print(f"  - LinkML PDF report: {output_base}_linkml.pdf")
        
        return True, output_files


def main():
    """Main entry point for the script"""
    parser = argparse.ArgumentParser(description="Extract and render JSON from DOCX files")
    parser.add_argument(
        "--input", 
        "-i", 
        help="Input file or directory containing .docx files", 
        default="/Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/data/GC_data_sheets"
    )
    parser.add_argument(
        "--output", 
        "-o", 
        help="Output directory", 
        default="/Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/data/GC_data_sheets/output"
    )
    parser.add_argument(
        "--pattern", 
        "-p", 
        help="File pattern to match (if input is directory)", 
        default="*.docx"
    )
    args = parser.parse_args()
    
    # Verify output directory exists
    if not os.path.exists(args.output):
        os.makedirs(args.output, exist_ok=True)
    
    processor = DocxProcessor(args.output)
    
    # Process input file or directory
    input_path = args.input
    
    if os.path.isfile(input_path):
        # Process a single file
        if input_path.lower().endswith('.docx'):
            processor.process_docx_file(input_path)
        else:
            print(f"Not a Word document: {input_path}")
            return 1
    elif os.path.isdir(input_path):
        # Process all matching files in the directory
        pattern = os.path.join(input_path, args.pattern)
        files = glob.glob(pattern)
        
        if not files:
            print(f"No files matching {pattern} found")
            return 1
        
        processed = 0
        for file_path in files:
            # Skip temporary files
            if file_path.startswith('~$') or '/output/' in file_path:
                continue
                
            success, _ = processor.process_docx_file(file_path)
            if success:
                processed += 1
        
        print(f"Processed {processed} out of {len(files)} files")
    else:
        print(f"Input not found: {input_path}")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())