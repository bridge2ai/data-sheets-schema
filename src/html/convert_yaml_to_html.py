#!/usr/bin/env python3
"""
Convert YAML files conforming to D4D schema to HTML format
"""

import os
import json
import yaml
from datetime import datetime
from jinja2 import Template, Environment
from pathlib import Path

def organize_data(data_list):
    """Organize data by category for rendering"""
    collections = {
        "Motivation": {},
        "Composition": {},
        "Collection": {},
        "Preprocessing": {},
        "Uses": {},
        "Distribution": {},
        "Maintenance": {},
        "Metadata": {},
    }
    
    # If data is a list, process each item
    if isinstance(data_list, list):
        for item_idx, item in enumerate(data_list):
            if isinstance(item, dict):
                assigned = False
                for key, value in item.items():
                    for collection in collections.keys():
                        if collection == "Metadata":
                            continue
                        if (collection.lower() in key.lower() or
                            (isinstance(value, str) and collection.lower() in value.lower())):
                            collections[collection][f"Item_{item_idx}_{key}"] = item
                            assigned = True
                            break
                    if assigned:
                        break
                if not assigned:
                    collections["Metadata"][f"Item_{item_idx}"] = item
    else:
        # Single item
        collections["Metadata"]["Data"] = data_list
    
    return {k: v for k, v in collections.items() if v}

def render_yaml_to_html(yaml_file_path, output_file_path):
    """Convert YAML file to HTML using LinkML-style template"""
    
    # Load YAML data
    with open(yaml_file_path, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)
    
    # Get filename for title
    title = Path(yaml_file_path).stem
    
    # Organize data
    organized_data = organize_data(data)
    
    # HTML template (based on the LinkML template from extract_docx.py)
    html_template = """
<!DOCTYPE html>
<html>
<head>
    <title>{{ title }} - Data Sheet</title>
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
        .list-item { margin: 5px 0; padding: 5px; background-color: #f8f9fa; border-radius: 3px; }
    </style>
</head>
<body>
    <h1>{{ title }} - Data Sheet</h1>
    <p class="metadata">Generated using Bridge2AI Data Sheets Schema</p>
    <div class="note">
        <p>This report shows data from a YAML file following the Bridge2AI Data Sheets Schema.</p>
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
                {% for item in value %}
                <div class="list-item">
                    {% if item is mapping %}
                        {% for sub_key, sub_value in item.items() %}
                        <div>
                            <span class="slot-name">{{ sub_key }}:</span>
                            {% if sub_value is mapping or (sub_value is iterable and sub_value is not string) %}
                                <pre>{{ sub_value|tojson(indent=2) }}</pre>
                            {% else %}
                                {{ sub_value }}
                            {% endif %}
                        </div>
                        {% endfor %}
                    {% else %}
                        {{ item }}
                    {% endif %}
                </div>
                {% endfor %}
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
    
    # Define custom filter for JSON formatting
    def tojson_filter(obj, indent=None):
        return json.dumps(obj, indent=indent)
    
    # Create template environment with custom filter
    env = Environment()
    env.filters['tojson'] = tojson_filter
    template = env.from_string(html_template)
    
    # Render HTML
    html_content = template.render(
        title=title,
        data=organized_data,
        timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    )
    
    # Write output
    with open(output_file_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print(f"Generated HTML: {output_file_path}")

def main():
    """Convert all YAML files in data/GC_data_sheets/output/ to HTML"""
    
    # Input and output directories
    input_dir = "data/GC_data_sheets/output"
    output_dir = "data/sheets/html_output"
    
    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)
    
    # Find all YAML files
    yaml_files = [
        "D4D - AI-READI FAIRHub_data.yaml",
        "D4D - CM4AI_data.yaml", 
        "D4D - Voice Health Data Nexus_data.yaml",
        "D4D Minimal - Voice Physionet_data.yaml",
        "D4D Collection - AI-READI FAIRHub - All_data.yaml"
    ]
    
    converted_count = 0
    
    for yaml_file in yaml_files:
        yaml_path = os.path.join(input_dir, yaml_file)
        if os.path.exists(yaml_path):
            # Generate output filename
            base_name = yaml_file.replace("_data.yaml", "")
            html_path = os.path.join(output_dir, f"{base_name}.html")
            
            try:
                render_yaml_to_html(yaml_path, html_path)
                converted_count += 1
            except Exception as e:
                print(f"Error converting {yaml_file}: {e}")
        else:
            print(f"File not found: {yaml_path}")
    
    print(f"\nConversion complete! Converted {converted_count} YAML files to HTML format.")
    print(f"HTML files saved in: {output_dir}")

if __name__ == "__main__":
    main()