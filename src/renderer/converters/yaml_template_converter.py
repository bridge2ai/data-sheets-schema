#!/usr/bin/env python3
"""
Template converter for Datasheets schema.

This module provides utilities to convert between different datasheet template formats
(YAML, JSON, etc.) and to render templates for display.
"""

import os
import json
import yaml
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class TemplateConverter:
    """Convert between different template formats and render templates for display."""
    
    def __init__(self, template_dir=None):
        """
        Initialize the converter with template directory.
        
        Args:
            template_dir: Directory containing template files. If None, uses default location.
        """
        if template_dir is None:
            # Default to the templates directory relative to this file
            self.template_dir = Path(os.path.dirname(os.path.abspath(__file__))) / '..' / 'templates'
        else:
            self.template_dir = Path(template_dir)
            
        self.yaml_template_path = self.template_dir / 'datasheet_template.yaml'
        self.json_template_path = self.template_dir / 'datasheet_template.json'
        
        # Ensure the template directory exists
        os.makedirs(self.template_dir, exist_ok=True)
        
    def load_yaml_template(self, path=None):
        """
        Load YAML template from file.
        
        Args:
            path: Path to YAML template file. If None, uses default.
            
        Returns:
            dict: Parsed YAML template
        """
        if path is None:
            path = self.yaml_template_path
            
        try:
            with open(path, 'r', encoding='utf-8') as f:
                template = yaml.safe_load(f)
            return template
        except Exception as e:
            logger.error(f"Error loading YAML template from {path}: {e}")
            return None
            
    def load_json_template(self, path=None):
        """
        Load JSON template from file.
        
        Args:
            path: Path to JSON template file. If None, uses default.
            
        Returns:
            dict: Parsed JSON template
        """
        if path is None:
            path = self.json_template_path
            
        try:
            with open(path, 'r', encoding='utf-8') as f:
                template = json.load(f)
            return template
        except Exception as e:
            logger.error(f"Error loading JSON template from {path}: {e}")
            return None
    
    def yaml_to_json(self, yaml_path=None, json_path=None):
        """
        Convert YAML template to JSON.
        
        Args:
            yaml_path: Path to input YAML file. If None, uses default.
            json_path: Path to output JSON file. If None, uses default.
            
        Returns:
            bool: True if conversion was successful, False otherwise
        """
        if yaml_path is None:
            yaml_path = self.yaml_template_path
        if json_path is None:
            json_path = self.json_template_path
            
        try:
            # Load YAML
            template = self.load_yaml_template(yaml_path)
            if template is None:
                return False
                
            # Write JSON with utf-8 encoding
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(template, f, indent=2, ensure_ascii=False)
                
            logger.info(f"Successfully converted YAML template to JSON: {json_path}")
            return True
        except Exception as e:
            logger.error(f"Error converting YAML to JSON: {e}")
            return False
            
    def json_to_yaml(self, json_path=None, yaml_path=None):
        """
        Convert JSON template to YAML.
        
        Args:
            json_path: Path to input JSON file. If None, uses default.
            yaml_path: Path to output YAML file. If None, uses default.
            
        Returns:
            bool: True if conversion was successful, False otherwise
        """
        if json_path is None:
            json_path = self.json_template_path
        if yaml_path is None:
            yaml_path = self.yaml_template_path
            
        try:
            # Load JSON
            template = self.load_json_template(json_path)
            if template is None:
                return False
                
            # Write YAML with utf-8 encoding
            with open(yaml_path, 'w', encoding='utf-8') as f:
                yaml.dump(template, f, default_flow_style=False, sort_keys=False, allow_unicode=True)
                
            logger.info(f"Successfully converted JSON template to YAML: {yaml_path}")
            return True
        except Exception as e:
            logger.error(f"Error converting JSON to YAML: {e}")
            return False
    
    def get_collection_structure(self, template=None):
        """
        Extract collections and questions structure from template.
        
        Args:
            template: Template dictionary. If None, loads from default.
            
        Returns:
            dict: Simplified structure of collections and questions
        """
        if template is None:
            template = self.load_yaml_template()
            if template is None:
                template = self.load_json_template()
                if template is None:
                    return None
        
        # Handle both formats (direct dict or nested under datasheet key)
        if 'datasheet' in template:
            template = template['datasheet']
            
        structure = {}
        
        # Extract collections based on format (YAML vs JSON have different structures)
        collections = {}
        for key, value in template.items():
            if key.startswith('D4D-') or key in ('Metadata', 'metadata', 'collections'):
                if key == 'collections':
                    # JSON format has a 'collections' key with nested collections
                    collections.update(value)
                elif key == 'metadata':
                    # Handle metadata differently - it's not a collection
                    continue
                else:
                    # YAML format has direct collection keys
                    collections[key] = value
        
        for collection_id, collection in collections.items():
            if collection_id == 'Metadata':
                continue  # Skip metadata
                
            collection_name = collection.get('title', collection_id)
            questions = collection.get('questions', {})
            
            structure[collection_id] = {
                'name': collection_name,
                'description': collection.get('description', ''),
                'questions': []
            }
            
            for question_id, question in questions.items():
                structure[collection_id]['questions'].append({
                    'id': question_id,
                    'text': question.get('question', ''),
                    'type': question.get('type', 'text')
                })
                
        return structure

# Example usage
if __name__ == "__main__":
    converter = TemplateConverter()
    
    # Ensure JSON format is up to date with YAML
    converter.yaml_to_json()
    
    # Print structure
    structure = converter.get_collection_structure()
    print(json.dumps(structure, indent=2))