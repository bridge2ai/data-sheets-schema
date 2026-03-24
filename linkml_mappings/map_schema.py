#!/usr/bin/env python3

import json
import os
import sys
import yaml
from linkml_runtime.loaders import yaml_loader
from linkml_runtime.dumpers import json_dumper

def extract_properties(obj, path=""):
    """Recursively extract properties from a nested object."""
    properties = {}
    
    if isinstance(obj, dict):
        for key, value in obj.items():
            new_path = f"{path}.{key}" if path else key
            
            # Add this property
            properties[new_path] = {
                "path": new_path,
                "type": type(value).__name__
            }
            
            # If this is an object with properties, add those too
            if isinstance(value, dict) and "properties" in value:
                nested_props = extract_properties(value["properties"], new_path)
                properties.update(nested_props)
            elif isinstance(value, dict) and "items" in value and isinstance(value["items"], dict) and "properties" in value["items"]:
                # Handle array items with properties
                nested_props = extract_properties(value["items"]["properties"], f"{new_path}.items")
                properties.update(nested_props)
    
    return properties

def map_schema(input_schema_path, target_schema_path, output_path):
    """Map a LinkML schema to a target schema and save the results."""
    # Load the source schema
    print(f"Loading source schema: {input_schema_path}")
    with open(input_schema_path, 'r') as f:
        source_schema = yaml.safe_load(f)
    
    # Load the target schema
    print(f"Loading target schema: {target_schema_path}")
    with open(target_schema_path, 'r') as f:
        target_schema = json.load(f)
    
    # Perform the mapping
    print("Performing schema mapping...")
    mapped_result = {
        "mappings": []
    }
    
    # Extract all target properties from RO-Crate schema
    target_props = {}
    if "properties" in target_schema:
        target_props = extract_properties(target_schema["properties"])
    
    # Get source slots and classes
    source_slots = source_schema.get("slots", {})
    source_classes = source_schema.get("classes", {})
    
    # Map slot names to target properties
    for slot_name, slot_def in source_slots.items():
        # Try direct matching by name
        for target_prop_path, target_prop in target_props.items():
            path_parts = target_prop_path.split('.')
            prop_name = path_parts[-1]
            
            # Check if the property name matches the slot name
            if prop_name == slot_name:
                mapped_result["mappings"].append({
                    "source_slot": slot_name,
                    "source_slot_description": slot_def.get("description", ""),
                    "target_property": target_prop_path,
                    "confidence": "medium",
                    "match_type": "name_match"
                })
            
            # Check description similarity (simplified here)
            # In a more advanced implementation, you could use NLP to compare descriptions
            slot_desc = slot_def.get("description", "").lower()
            target_path_lower = target_prop_path.lower()
            
            common_terms = ["title", "name", "description", "identifier", "id", 
                           "version", "date", "license", "author", "contact", 
                           "email", "funding", "size", "keyword"]
            
            for term in common_terms:
                if (term in slot_desc or term in slot_name.lower()) and term in target_path_lower:
                    mapped_result["mappings"].append({
                        "source_slot": slot_name,
                        "source_slot_description": slot_def.get("description", ""),
                        "target_property": target_prop_path,
                        "confidence": "low",
                        "match_type": "term_match",
                        "match_term": term
                    })
    
    # Map classes to objects in the target schema
    for class_name, class_def in source_classes.items():
        class_slots = class_def.get("slots", [])
        
        # Check if this class maps to a top-level section in the target schema
        for section_name in ["overview", "useCases", "composition"]:
            if class_name.lower() in section_name.lower() or section_name.lower() in class_name.lower():
                mapped_result["mappings"].append({
                    "source_class": class_name,
                    "source_class_description": class_def.get("description", ""),
                    "target_section": section_name,
                    "confidence": "medium",
                    "match_type": "section_match"
                })
    
    # Save the result
    print(f"Saving mapping results to: {output_path}")
    with open(output_path, 'w') as f:
        json.dump(mapped_result, f, indent=2)
    
    print(f"Mapping complete: {len(mapped_result['mappings'])} mappings created")
    return mapped_result

if __name__ == "__main__":
    source_schema = "src/data_sheets_schema/schema/data_sheets_schema.yaml"
    target_schema = "data/RO-Crate/datasheet-schema.json"
    output_path = "mapping_results.json"
    
    # Handle command-line arguments if provided
    if len(sys.argv) > 1:
        source_schema = sys.argv[1]
    if len(sys.argv) > 2:
        target_schema = sys.argv[2]
    if len(sys.argv) > 3:
        output_path = sys.argv[3]
        
    # Validate paths
    if not os.path.exists(source_schema):
        print(f"Error: Source schema not found at {source_schema}")
        sys.exit(1)
    
    if not os.path.exists(target_schema):
        print(f"Error: Target schema not found at {target_schema}")
        sys.exit(1)
    
    map_schema(source_schema, target_schema, output_path)