#!/usr/bin/env python3
"""
Data Sheets Schema Test Script

This script:
1. Reads and extracts JSON data from data sheet files
2. Validates the JSON data
3. Renders the data as hierarchical tables in TXT, HTML, and PDF formats
4. Saves the raw and formatted output files
"""

import os
import sys
import json
import glob
import argparse
from pathlib import Path
from typing import Dict, Any, List, Optional, Union

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

# Import the generated data model
# We're using a try/except block to handle potential import issues
try:
    from data_sheets_schema.datamodel.data_sheets_schema import (
        Dataset, 
        DatasetCollection,
        Information
    )
    HAS_DATAMODEL = True
except ImportError:
    HAS_DATAMODEL = False
    print("Data sheets schema model not available. Schema validation will be disabled.")
    print("Make sure the data_sheets_schema package is installed or in your PYTHONPATH.")


class DataSheetRenderer:
    """Class to handle reading, validating, and rendering data sheets"""
    
    # Define subsets/collections based on schema
    COLLECTIONS = [
        "Motivation",
        "Composition",
        "Collection",
        "Preprocessing-Cleaning-Labeling",
        "Uses", 
        "Distribution",
        "Maintenance"
    ]
    
    def __init__(self, output_dir: str = "output"):
        """Initialize the renderer with an output directory"""
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
    
    def read_json_file(self, file_path: str) -> Dict[str, Any]:
        """Read and parse a JSON file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                data = json.loads(content)
                return data
        except json.JSONDecodeError:
            print(f"Error: {file_path} is not valid JSON")
            return {}
        except Exception as e:
            print(f"Error reading {file_path}: {e}")
            return {}
    
    def validate_data(self, data: Dict[str, Any]) -> bool:
        """Validate data against the schema if available"""
        if not HAS_DATAMODEL:
            # Can't validate, assume it's valid
            return True
        
        try:
            # Determine the data type and validate accordingly
            data_type = data.get("@type")
            if data_type == "Dataset":
                Dataset(**data)
            elif data_type == "DatasetCollection":
                DatasetCollection(**data)
            elif isinstance(data, dict):
                # Generic validation for any object
                Information(**data)
            return True
        except Exception as e:
            print(f"Validation error: {e}")
            return False
    
    def organize_by_collection(self, data: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
        """Organize data by collection"""
        collections = {coll: {} for coll in self.COLLECTIONS}
        
        # Process all keys in the data
        for key, value in data.items():
            # Skip metadata and type fields
            if key.startswith('@') or key == 'id':
                continue
                
            # Determine which collection this belongs to
            assigned = False
            for collection in self.COLLECTIONS:
                # This is a simplified way to associate keys with collections
                # In a real implementation, you'd use the schema to determine this
                if collection.lower() in key.lower():
                    collections[collection][key] = value
                    assigned = True
                    break
            
            # If not assigned to any collection, put in a default category
            if not assigned:
                if "Metadata" not in collections:
                    collections["Metadata"] = {}
                collections["Metadata"][key] = value
        
        # Remove empty collections
        return {k: v for k, v in collections.items() if v}
    
    def render_as_text(self, data: Dict[str, Dict[str, Any]]) -> str:
        """Render data as hierarchical text"""
        output = []
        output.append("DATA SHEET REPORT")
        output.append("=" * 80)
        output.append("")
        
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
                        output.append(f"    {sub_key}: {sub_value}")
                elif isinstance(value, list):
                    for item in value:
                        if isinstance(item, dict):
                            for sub_key, sub_value in item.items():
                                output.append(f"    - {sub_key}: {sub_value}")
                        else:
                            output.append(f"    - {item}")
                else:
                    output.append(f"    {value}")
                
                output.append("")
            
            output.append("")
        
        return "\n".join(output)
    
    def render_as_html(self, data: Dict[str, Dict[str, Any]]) -> str:
        """Render data as HTML"""
        html_template = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Data Sheet Report</title>
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
            </style>
        </head>
        <body>
            <h1>Data Sheet Report</h1>
            
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
                        <p><strong>{{ sub_key }}:</strong> {{ sub_value }}</p>
                        {% endfor %}
                    {% elif value is iterable and value is not string %}
                        <ul>
                        {% for item in value %}
                            {% if item is mapping %}
                            <li>
                                {% for sub_key, sub_value in item.items() %}
                                <p><strong>{{ sub_key }}:</strong> {{ sub_value }}</p>
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
            
            <div class="timestamp">Generated on: {{ timestamp }}</div>
        </body>
        </html>
        """
        
        template = Template(html_template)
        return template.render(
            data=data,
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        )
    
    def process_file(self, file_path: str) -> bool:
        """Process a single file and generate all outputs"""
        # Extract base filename
        base_name = os.path.basename(file_path)
        name_without_ext = os.path.splitext(base_name)[0]
        output_base = os.path.join(self.output_dir, name_without_ext)
        
        # Read and validate the JSON data
        data = self.read_json_file(file_path)
        if not data:
            return False
            
        if not self.validate_data(data):
            print(f"Validation failed for {file_path}")
            return False
        
        # Save the raw JSON
        with open(f"{output_base}_raw.txt", 'w', encoding='utf-8') as f:
            f.write(json.dumps(data, indent=2))
        
        # Organize data by collection
        organized_data = self.organize_by_collection(data)
        
        # Render and save text format
        text_output = self.render_as_text(organized_data)
        with open(f"{output_base}.txt", 'w', encoding='utf-8') as f:
            f.write(text_output)
        
        # Render and save HTML format
        html_output = self.render_as_html(organized_data)
        with open(f"{output_base}.html", 'w', encoding='utf-8') as f:
            f.write(html_output)
        
        # Generate PDF if WeasyPrint is available
        if HAS_WEASYPRINT:
            try:
                HTML(string=html_output).write_pdf(f"{output_base}.pdf")
                print(f"Generated PDF: {output_base}.pdf")
            except Exception as e:
                print(f"Error generating PDF: {e}")
        
        print(f"Processed: {file_path}")
        print(f"  - Output: {output_base}.txt")
        print(f"  - Output: {output_base}.html")
        
        return True


def main():
    """Main entry point for the script"""
    parser = argparse.ArgumentParser(description="Data Sheets Schema Test Script")
    parser.add_argument(
        "--input", 
        "-i", 
        help="Input file or directory", 
        default="examples/output"
    )
    parser.add_argument(
        "--output", 
        "-o", 
        help="Output directory", 
        default="test_output"
    )
    parser.add_argument(
        "--pattern", 
        "-p", 
        help="File pattern to match (if input is directory)", 
        default="*.json"
    )
    args = parser.parse_args()
    
    renderer = DataSheetRenderer(args.output)
    
    # Determine input type (file or directory)
    input_path = args.input
    if os.path.isfile(input_path):
        # Process a single file
        renderer.process_file(input_path)
    elif os.path.isdir(input_path):
        # Process a directory of files
        pattern = os.path.join(input_path, args.pattern)
        files = glob.glob(pattern)
        
        if not files:
            print(f"No files matching {pattern} found")
            return 1
        
        processed = 0
        for file_path in files:
            if renderer.process_file(file_path):
                processed += 1
        
        print(f"Processed {processed} out of {len(files)} files")
    else:
        print(f"Input not found: {input_path}")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())