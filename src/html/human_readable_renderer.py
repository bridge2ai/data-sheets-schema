#!/usr/bin/env python3
"""
Human-readable HTML renderer for D4D YAML data
Creates natural, document-like HTML without raw JSON structures
"""

import os
import yaml
from datetime import datetime
from jinja2 import Template, Environment
from pathlib import Path

class HumanReadableRenderer:
    """Renders D4D data in a human-readable HTML format"""
    
    def __init__(self):
        self.d4d_sections = {
            "Motivation": {
                "title": "Motivation",
                "description": "Why was the dataset created?",
                "icon": "🎯"
            },
            "Composition": {
                "title": "Composition", 
                "description": "What do the instances represent?",
                "icon": "📊"
            },
            "Collection": {
                "title": "Collection Process",
                "description": "How was the data acquired?", 
                "icon": "🔍"
            },
            "Preprocessing": {
                "title": "Preprocessing/Cleaning/Labeling",
                "description": "Was any preprocessing/cleaning/labeling done?",
                "icon": "🔧"
            },
            "Uses": {
                "title": "Uses",
                "description": "What (other) tasks could the dataset be used for?",
                "icon": "🚀"
            },
            "Distribution": {
                "title": "Distribution",
                "description": "How will the dataset be distributed?",
                "icon": "📤"
            },
            "Maintenance": {
                "title": "Maintenance", 
                "description": "How will the dataset be maintained?",
                "icon": "🔄"
            },
            "Human": {
                "title": "Human Subjects",
                "description": "Does the dataset relate to people?",
                "icon": "👥"
            }
        }
    
    def categorize_data(self, data):
        """Organize data into D4D sections with intelligent categorization"""
        sections = {section: [] for section in self.d4d_sections.keys()}
        
        def get_section_for_key(key):
            """Determine which D4D section a key belongs to"""
            key_lower = key.lower()
            
            # Motivation keywords
            if any(word in key_lower for word in ['purpose', 'goal', 'objective', 'motivation', 'funding', 'funder', 'grantor', 'grant']):
                return "Motivation"
            
            # Composition keywords  
            elif any(word in key_lower for word in ['instance', 'count', 'participant', 'sample', 'subpopulation', 'distribution', 'demographics']):
                return "Composition"
                
            # Collection keywords
            elif any(word in key_lower for word in ['collection', 'acquisition', 'methodology', 'procedure', 'protocol', 'creator', 'issued']):
                return "Collection"
                
            # Uses keywords
            elif any(word in key_lower for word in ['use', 'purpose', 'task', 'application', 'machine learning', 'artificial intelligence']):
                return "Uses"
                
            # Distribution keywords
            elif any(word in key_lower for word in ['license', 'access', 'download', 'doi', 'url', 'availability', 'bytes']):
                return "Distribution"
                
            # Maintenance keywords
            elif any(word in key_lower for word in ['version', 'maintenance', 'update', 'support']):
                return "Maintenance"
                
            # Human subjects keywords
            elif any(word in key_lower for word in ['human', 'participant', 'consent', 'ethics', 'privacy', 'identifier']):
                return "Human"
                
            else:
                return "Collection"  # Default section
        
        def process_item(key, value, parent_context=""):
            """Process a data item and add to appropriate section"""
            section = get_section_for_key(key)
            
            # Create a structured data item
            item = {
                'key': key,
                'value': value,
                'context': parent_context,
                'type': type(value).__name__
            }
            
            sections[section].append(item)
        
        # Process the data structure
        if isinstance(data, dict):
            for key, value in data.items():
                if key == "DatasetCollection" and isinstance(value, dict) and "resources" in value:
                    # Special handling for DatasetCollection resources
                    for resource in value.get("resources", []):
                        if isinstance(resource, dict):
                            for res_key, res_value in resource.items():
                                process_item(res_key, res_value, "Dataset Resource")
                else:
                    process_item(key, value)
        elif isinstance(data, list):
            for i, item in enumerate(data):
                process_item(f"Item {i+1}", item)
        
        # Remove empty sections
        return {k: v for k, v in sections.items() if v}
    
    def format_value(self, value, context=""):
        """Format a value for human-readable display"""
        if isinstance(value, dict):
            return self._format_dict(value)
        elif isinstance(value, list):
            return self._format_list(value)
        elif isinstance(value, str):
            return self._format_string(value)
        elif isinstance(value, (int, float)):
            return self._format_number(value)
        elif isinstance(value, bool):
            return "Yes" if value else "No"
        else:
            return str(value)
    
    def _format_dict(self, d):
        """Format dictionary as nested definition list"""
        if not d:
            return "<em>No information provided</em>"
        
        items = []
        for key, value in d.items():
            formatted_key = self._humanize_key(key)
            formatted_value = self.format_value(value)
            items.append(f"<dt>{formatted_key}</dt><dd>{formatted_value}</dd>")
        
        return f"<dl class='nested-dict'>{''.join(items)}</dl>"
    
    def _format_list(self, lst):
        """Format list as bulleted or numbered list, or as table for structured data"""
        if not lst:
            return "<em>No items</em>"
        
        # Check if this is author/creator/contributor data that should be formatted as a table
        if self._is_author_list(lst):
            return self._format_author_table(lst)
        
        # Check if this is other structured data suitable for table format
        if self._is_tabular_data(lst):
            return self._format_data_table(lst)
        
        # Default list formatting
        is_ordered = all(isinstance(item, dict) and len(item) > 3 for item in lst) if lst else False
        
        list_tag = "ol" if is_ordered else "ul"
        items = []
        
        for item in lst:
            formatted_item = self.format_value(item)
            items.append(f"<li>{formatted_item}</li>")
        
        return f"<{list_tag} class='formatted-list'>{''.join(items)}</{list_tag}>"
    
    def _is_author_list(self, lst):
        """Check if list contains author/creator/contributor data"""
        if not lst or not isinstance(lst, list):
            return False
        
        # Check if items have author-related keys
        author_indicators = ['author', 'principal_investigator', 'creator', 'contributor', 'affiliation']
        return any(
            isinstance(item, dict) and 
            any(key in str(item).lower() for key in author_indicators)
            for item in lst
        )
    
    def _is_tabular_data(self, lst):
        """Check if list contains structured data suitable for table format"""
        if not lst or not isinstance(lst, list) or len(lst) < 2:
            return False
        
        # Check if most items are dictionaries with similar keys
        dict_items = [item for item in lst if isinstance(item, dict)]
        if len(dict_items) < len(lst) * 0.7:  # At least 70% should be dicts
            return False
        
        # Check if items have similar structure (common keys)
        if dict_items:
            first_keys = set(dict_items[0].keys())
            similar_structure = sum(
                len(set(item.keys()) & first_keys) >= len(first_keys) * 0.5
                for item in dict_items
            )
            return similar_structure >= len(dict_items) * 0.7
        
        return False
    
    def _format_author_table(self, lst):
        """Format author/contributor data as a compact table"""
        if not lst:
            return "<em>No authors</em>"
        
        rows = []
        for item in lst:
            if isinstance(item, dict):
                role = ""
                name = ""
                orcid = ""
                affiliation = ""
                
                # Extract role and person info
                if 'principal_investigator' in item:
                    role = "Principal Investigator"
                    person_info = item['principal_investigator']
                elif 'author' in item:
                    role = "Author"
                    person_info = item['author']
                elif 'creator' in item:
                    role = "Creator"
                    person_info = item['creator']
                else:
                    # Try to extract directly from item
                    person_info = item
                    role = "Contributor"
                
                # Extract name and ID
                if isinstance(person_info, dict):
                    name = person_info.get('name', '')
                    person_id = person_info.get('id', '')
                    if person_id and 'orcid.org' in str(person_id):
                        orcid_id = person_id.split('/')[-1] if '/' in person_id else person_id
                        orcid = f'<a href="{person_id}" target="_blank">{orcid_id}</a>'
                    elif person_id:
                        orcid = person_id
                elif isinstance(person_info, str):
                    name = person_info
                
                # Extract affiliation
                if 'affiliation' in item and isinstance(item['affiliation'], dict):
                    affiliation = item['affiliation'].get('name', item['affiliation'].get('id', ''))
                
                rows.append([role, name, orcid or "-", affiliation or "-"])
        
        if not rows:
            return "<em>No author information available</em>"
        
        # Generate table HTML
        table_html = '<table class="data-table"><thead><tr>'
        table_html += '<th>Role</th><th>Name</th><th>ORCID</th><th>Affiliation</th>'
        table_html += '</tr></thead><tbody>'
        
        for row in rows:
            table_html += '<tr>'
            for cell in row:
                table_html += f'<td>{cell}</td>'
            table_html += '</tr>'
        
        table_html += '</tbody></table>'
        return table_html
    
    def _format_data_table(self, lst):
        """Format structured data as a compact table"""
        if not lst:
            return "<em>No data</em>"
        
        dict_items = [item for item in lst if isinstance(item, dict)]
        if not dict_items:
            return self._format_list_fallback(lst)
        
        # Get all unique keys
        all_keys = set()
        for item in dict_items:
            all_keys.update(item.keys())
        
        # Sort keys for consistent column order
        keys = sorted(all_keys)
        
        # Generate table HTML
        table_html = '<table class="data-table"><thead><tr>'
        for key in keys:
            table_html += f'<th>{self._humanize_key(key)}</th>'
        table_html += '</tr></thead><tbody>'
        
        for item in dict_items:
            table_html += '<tr>'
            for key in keys:
                value = item.get(key, '')
                formatted_value = self._format_table_cell(value)
                table_html += f'<td>{formatted_value}</td>'
            table_html += '</tr>'
        
        table_html += '</tbody></table>'
        return table_html
    
    def _format_table_cell(self, value):
        """Format a single table cell value"""
        if isinstance(value, dict):
            # For nested dicts, show key-value pairs compactly
            items = [f"{k}: {v}" for k, v in value.items()]
            return "<br>".join(items[:3])  # Limit to 3 items for readability
        elif isinstance(value, list):
            if len(value) <= 3:
                return ", ".join(str(v) for v in value)
            else:
                return f"{', '.join(str(v) for v in value[:2])}, ... (+{len(value)-2} more)"
        elif isinstance(value, str):
            if len(value) > 100:
                return f"{value[:100]}..."
            return value or "-"
        elif value is None:
            return "-"
        else:
            return str(value)
    
    def _format_list_fallback(self, lst):
        """Fallback formatting for non-tabular lists"""
        items = []
        for item in lst:
            formatted_item = self.format_value(item)
            items.append(f"<li>{formatted_item}</li>")
        return f"<ul class='formatted-list'>{''.join(items)}</ul>"
    
    def _format_string(self, s):
        """Format string with proper emphasis and links"""
        if not s:
            return "<em>Not specified</em>"
        
        # Handle URLs
        if s.startswith(('http://', 'https://', 'doi:')):
            if s.startswith('doi:'):
                url = f"https://doi.org/{s[4:]}"
                return f'<a href="{url}" target="_blank">{s}</a>'
            else:
                return f'<a href="{s}" target="_blank">{s}</a>'
        
        # Handle long descriptions
        if len(s) > 200:
            return f'<div class="long-description">{s}</div>'
        
        return s
    
    def _format_number(self, n):
        """Format numbers with appropriate units and separators"""
        if isinstance(n, int) and n > 1000:
            # Add thousand separators for large numbers
            return f"{n:,}"
        return str(n)
    
    def _humanize_key(self, key):
        """Convert key names to human-readable labels"""
        # Convert snake_case and camelCase to Title Case
        key = key.replace('_', ' ').replace('-', ' ')
        
        # Handle common abbreviations and terms
        replacements = {
            'id': 'ID',
            'url': 'URL', 
            'uri': 'URI',
            'doi': 'DOI',
            'api': 'API',
            'ai': 'AI',
            'ml': 'ML',
            'nih': 'NIH',
            'irb': 'IRB',
            'phi': 'PHI',
            'pii': 'PII'
        }
        
        words = key.split()
        for i, word in enumerate(words):
            if word.lower() in replacements:
                words[i] = replacements[word.lower()]
            else:
                words[i] = word.capitalize()
        
        return ' '.join(words)
    
    def render_to_html(self, data, title, css_file="datasheet-common.css"):
        """Render data to human-readable HTML using external CSS"""
        
        categorized_data = self.categorize_data(data)
        
        # HTML template for human-readable display using external CSS
        template_str = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link rel="stylesheet" href="{{ css_file }}">
    <title>{{ title }} - Datasheet for Dataset</title>
</head>
<body>
    <div class="header">
        <h1>{{ title }}</h1>
        <p class="subtitle">Datasheet for Dataset - Human Readable Format</p>
    </div>
    
    {% if categorized_data %}
        {% for section_name, items in categorized_data.items() %}
            {% if items %}
            <div class="section">
                <div class="section-header">
                    <span class="section-icon">{{ sections[section_name].icon }}</span>
                    <div>
                        <h2 class="section-title">{{ sections[section_name].title }}</h2>
                        <p class="section-description">{{ sections[section_name].description }}</p>
                    </div>
                </div>
                <div class="section-content">
                    {% for item in items %}
                    <div class="data-item">
                        {% if item.context %}
                        <div class="item-context">{{ item.context }}</div>
                        {% endif %}
                        <label class="item-label">{{ humanize_key(item.key) }}</label>
                        <div class="item-value">{{ format_value(item.value)|safe }}</div>
                    </div>
                    {% endfor %}
                </div>
            </div>
            {% endif %}
        {% endfor %}
    {% else %}
        <div class="section">
            <div class="section-content">
                <p><em>No data available to display.</em></p>
            </div>
        </div>
    {% endif %}
    
    <div class="timestamp">
        Generated on {{ timestamp }} using Bridge2AI Data Sheets Schema
    </div>
</body>
</html>
"""
        
        # Create Jinja2 environment with custom functions
        env = Environment()
        env.globals['humanize_key'] = self._humanize_key
        env.globals['format_value'] = self.format_value
        
        template = env.from_string(template_str)
        
        return template.render(
            title=title,
            categorized_data=categorized_data,
            sections=self.d4d_sections,
            css_file=css_file,
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        )

def process_yaml_file(file_path, output_dir):
    """Process a YAML file and generate human-readable HTML"""
    
    renderer = HumanReadableRenderer()
    
    # Read and parse YAML
    with open(file_path, 'r', encoding='utf-8-sig') as f:
        data = yaml.safe_load(f)
    
    if not data:
        print(f"No data found in {file_path}")
        return False
    
    # Generate output filename - remove _data from the stem if present
    base_name = Path(file_path).stem
    if base_name.endswith('_data'):
        base_name = base_name[:-5]  # Remove '_data' suffix
    
    output_path = os.path.join(output_dir, f"{base_name}_human_readable.html")
    
    # Generate HTML with external CSS
    html_content = renderer.render_to_html(data, base_name)
    
    # Write output
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print(f"Generated human-readable HTML: {output_path}")
    return True

def main():
    """Process all YAML files and generate human-readable HTML versions"""
    
    input_dir = "data/sheets/html_output"
    output_dir = "src/html/output"
    
    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)
    
    # Process YAML data files
    yaml_files = [
        "D4D_-_AI-READI_FAIRHub_v3_data.yaml",
        "D4D_-_CM4AI_Dataverse_v3_data.yaml", 
        "D4D_-_VOICE_PhysioNet_v3_data.yaml"
    ]
    
    processed_count = 0
    
    for yaml_file in yaml_files:
        yaml_path = os.path.join(input_dir, yaml_file)
        if os.path.exists(yaml_path):
            if process_yaml_file(yaml_path, output_dir):
                processed_count += 1
        else:
            print(f"File not found: {yaml_path}")
    
    print(f"\nProcessed {processed_count} files.")
    print(f"Human-readable HTML files saved in: {output_dir}")

if __name__ == "__main__":
    main()