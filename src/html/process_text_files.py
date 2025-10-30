#!/usr/bin/env python3
"""
Process YAML files in data/sheets/ containing D4D data and convert to HTML using LinkML approach
"""

import os
import json
import yaml
from datetime import datetime
from jinja2 import Template, Environment
from pathlib import Path

def organize_data_by_d4d_sections(data):
    """Organize data by D4D sections based on content analysis"""
    sections = {
        "Motivation": {},
        "Composition": {},
        "Collection": {},
        "Preprocessing": {},
        "Uses": {},
        "Distribution": {},
        "Maintenance": {},
        "Human": {},
        "Metadata": {}
    }
    
    def categorize_field(key, value):
        """Categorize a field based on its key and content"""
        key_lower = key.lower()
        
        # Motivation section keywords
        if any(keyword in key_lower for keyword in ['purpose', 'motivation', 'goal', 'objective', 'funding', 'funder', 'grantor']):
            return "Motivation"
        
        # Composition section keywords  
        elif any(keyword in key_lower for keyword in ['instance', 'count', 'subpopulation', 'participant', 'sample', 'data_topic', 'data_substrate']):
            return "Composition"
            
        # Collection section keywords
        elif any(keyword in key_lower for keyword in ['collection', 'acquisition', 'methodology', 'procedure', 'protocol']):
            return "Collection"
            
        # Preprocessing section keywords
        elif any(keyword in key_lower for keyword in ['preprocessing', 'processing', 'cleaning', 'transformation', 'quality']):
            return "Preprocessing"
            
        # Uses section keywords
        elif any(keyword in key_lower for keyword in ['use', 'application', 'task', 'machine learning', 'artificial intelligence']):
            return "Uses"
            
        # Distribution section keywords
        elif any(keyword in key_lower for keyword in ['distribution', 'license', 'access', 'download', 'availability', 'doi', 'url']):
            return "Distribution"
            
        # Maintenance section keywords
        elif any(keyword in key_lower for keyword in ['maintenance', 'update', 'version', 'support', 'contact']):
            return "Maintenance"
            
        # Human subjects keywords
        elif any(keyword in key_lower for keyword in ['human', 'participant', 'consent', 'ethics', 'privacy', 'identifier', 'protected']):
            return "Human"
            
        else:
            return "Metadata"
    
    def process_dict(data_dict, prefix=""):
        """Recursively process dictionary to categorize fields"""
        for key, value in data_dict.items():
            full_key = f"{prefix}_{key}" if prefix else key
            
            if isinstance(value, dict):
                # For nested dictionaries, categorize the whole structure
                section = categorize_field(key, value)
                if section not in sections:
                    section = "Metadata"
                sections[section][full_key] = value
                
                # Also process nested items
                process_dict(value, full_key)
            elif isinstance(value, list):
                # For lists, categorize based on the key
                section = categorize_field(key, value)
                if section not in sections:
                    section = "Metadata"
                sections[section][full_key] = value
            else:
                # For simple values, categorize based on key
                section = categorize_field(key, value)
                if section not in sections:
                    section = "Metadata"
                sections[section][full_key] = value
    
    if isinstance(data, dict):
        process_dict(data)
    elif isinstance(data, list):
        for i, item in enumerate(data):
            if isinstance(item, dict):
                process_dict(item, f"Item_{i}")
            else:
                sections["Metadata"][f"Item_{i}"] = item
    else:
        sections["Metadata"]["Data"] = data
    
    # Remove empty sections
    return {k: v for k, v in sections.items() if v}

def render_data_to_linkml_html(data, title):
    """Render data to HTML using LinkML-style template"""
    
    organized_data = organize_data_by_d4d_sections(data)
    
    # LinkML-style HTML template
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
        .simple-value { margin: 5px 0; }
    </style>
</head>
<body>
    <h1>{{ title }} - Data Sheet</h1>
    <p class="metadata">Generated using Bridge2AI Data Sheets Schema</p>
    <div class="note">
        <p>This report shows data from a text file following the Bridge2AI Data Sheets Schema.</p>
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
                            <span class="simple-value">{{ sub_value }}</span>
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
                                <span class="simple-value">{{ sub_value }}</span>
                            {% endif %}
                        </div>
                        {% endfor %}
                    {% else %}
                        <span class="simple-value">{{ item }}</span>
                    {% endif %}
                </div>
                {% endfor %}
            {% else %}
                <span class="simple-value">{{ value }}</span>
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
    
    return html_content

def process_text_file(file_path, output_dir):
    """Process a single text file and generate HTML output"""
    
    # Read the text file and handle BOM
    with open(file_path, 'r', encoding='utf-8-sig') as f:
        content = f.read()
    
    # Try to parse as YAML
    try:
        data = yaml.safe_load(content)
        data_format = "yaml"
    except yaml.YAMLError:
        try:
            # If YAML fails, try JSON
            data = json.loads(content)
            data_format = "json"
        except json.JSONDecodeError:
            print(f"Could not parse {file_path} as YAML or JSON")
            return False
    
    if not data:
        print(f"No data found in {file_path}")
        return False
    
    # Generate output filename
    base_name = Path(file_path).stem
    output_path = os.path.join(output_dir, f"{base_name}_linkml.html")
    
    # Save extracted data
    data_output_path = os.path.join(output_dir, f"{base_name}_data.{data_format}")
    with open(data_output_path, 'w', encoding='utf-8') as f:
        if data_format == "yaml":
            yaml.dump(data, f, default_flow_style=False, sort_keys=False)
        else:
            json.dump(data, f, indent=2)
    
    # Generate HTML
    html_content = render_data_to_linkml_html(data, base_name)
    
    # Write HTML output
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print(f"Processed: {file_path}")
    print(f"  - Data format: {data_format}")
    print(f"  - Data file: {data_output_path}")
    print(f"  - LinkML HTML: {output_path}")
    
    return True

def main():
    """Process all text files in data/sheets/"""
    
    input_dir = "data/sheets"
    output_dir = "data/sheets/html_output"
    
    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)
    
    # Find YAML files
    yaml_files = [
        "D4D_-_AI-READI_FAIRHub_v3.yaml",
        "D4D_-_CM4AI_Dataverse_v3.yaml",
        "D4D_-_VOICE_PhysioNet_v3.yaml"
    ]
    
    processed_count = 0

    for yaml_file in yaml_files:
        yaml_path = os.path.join(input_dir, yaml_file)
        if os.path.exists(yaml_path):
            if process_text_file(yaml_path, output_dir):
                processed_count += 1
        else:
            print(f"File not found: {yaml_path}")

    print(f"\nProcessing complete! Processed {processed_count} YAML files.")
    print(f"HTML files saved in: {output_dir}")

if __name__ == "__main__":
    main()