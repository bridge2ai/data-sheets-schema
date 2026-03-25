#!/usr/bin/env python3

import os
import sys
import subprocess
import json
import yaml

def convert_json_schema_to_linkml(json_schema_path, output_yaml_path):
    """Convert a JSON Schema to a simplified LinkML compatible format."""
    with open(json_schema_path, 'r') as f:
        json_schema = json.load(f)
    
    # Create a basic LinkML schema structure
    linkml_schema = {
        "id": "https://w3id.org/bridge2ai/ro-crate-schema",
        "name": "ro_crate_schema",
        "title": "RO-Crate Schema",
        "description": f"LinkML conversion of {os.path.basename(json_schema_path)}",
        "imports": ["linkml:types"],
        "prefixes": {
            "linkml": "https://w3id.org/linkml/",
            "rocrate": "https://w3id.org/ro/crate/"
        },
        "default_prefix": "rocrate",
        "classes": {},
        "slots": {}
    }
    
    # Process the JSON Schema properties
    if "properties" in json_schema:
        # Handle top-level sections as classes
        for section_name, section_props in json_schema["properties"].items():
            class_name = section_name.capitalize()
            
            # Create a class for this section
            linkml_schema["classes"][class_name] = {
                "description": f"{class_name} section from RO-Crate schema",
                "slots": []
            }
            
            # If this section has properties, process them
            if "properties" in section_props:
                for prop_name, prop_def in section_props["properties"].items():
                    # Create a slot for this property
                    slot_name = f"{section_name}_{prop_name}"
                    linkml_schema["slots"][slot_name] = {
                        "description": prop_def.get("description", f"Property {prop_name} in {section_name}"),
                        "range": "string"  # Default range
                    }
                    
                    # Add the slot to the class's slot list
                    linkml_schema["classes"][class_name]["slots"].append(slot_name)
    
    # Write the LinkML schema to YAML
    with open(output_yaml_path, 'w') as f:
        yaml.dump(linkml_schema, f, sort_keys=False)
    
    print(f"Converted JSON schema to LinkML: {output_yaml_path}")
    return output_yaml_path

def create_mapping_spec(source_schema, target_schema, output_spec_path):
    """Create a transformation specification for linkml-map."""
    # Load source schema to get classes and slots
    with open(source_schema, 'r') as f:
        source = yaml.safe_load(f)
    
    # Load target schema
    with open(target_schema, 'r') as f:
        target = yaml.safe_load(f)
    
    # Create basic transformation spec
    transform_spec = {
        "source_schema": source_schema,
        "target_schema": target_schema,
        "prefixes": {
            "linkml": "https://w3id.org/linkml/",
            "rdfs": "http://www.w3.org/2000/01/rdf-schema#"
        },
        "class_derivations": {}
    }
    
    # Map source classes to target classes
    source_classes = source.get("classes", {})
    target_classes = target.get("classes", {})
    
    # Find potential class mappings
    for source_class, source_def in source_classes.items():
        transform_spec["class_derivations"][source_class] = {
            "slot_derivations": {}
        }
        
        # Get slots for this class
        class_slots = source_def.get("slots", [])
        
        # Map slots
        for slot in class_slots:
            if slot in source.get("slots", {}):
                # Add the slot to the derivation
                transform_spec["class_derivations"][source_class]["slot_derivations"][slot] = {
                    "annotations": {
                        "comment": f"Mapped from source slot {slot}"
                    }
                }
    
    # Write the transformation spec
    with open(output_spec_path, 'w') as f:
        yaml.dump(transform_spec, f, sort_keys=False)
    
    print(f"Created transformation specification: {output_spec_path}")
    return output_spec_path

def create_linkml_map_manually(source_schema_path, target_schema_path, output_path):
    """Create a manual mapping between the source LinkML schema and target schema without using linkml-map."""
    # Load source schema
    with open(source_schema_path, 'r') as f:
        source_schema = yaml.safe_load(f)
    
    # Load target schema (either JSON or YAML)
    if target_schema_path.endswith('.json'):
        with open(target_schema_path, 'r') as f:
            target_schema = json.load(f)
    else:
        with open(target_schema_path, 'r') as f:
            target_schema = yaml.safe_load(f)
    
    # Create mappings based on name and semantic similarity
    mappings = []
    
    # Extract common fields for direct mapping
    # This focuses on Dataset class slots to RO-Crate overview properties
    common_fields = {
        "title": "overview.title",
        "description": "overview.description",
        "id": "overview.identifier",
        "version": "overview.version",
        "doi": "overview.doi",
        "license": "overview.license",
        "keywords": "overview.keywords",
        "publisher": "overview.publisher",
        "last_updated_on": "overview.datePublished"
    }
    
    # Extract source slots 
    source_slots = source_schema.get("slots", {})
    
    # Map slots by name matching
    for slot_name, slot_def in source_slots.items():
        if slot_name in common_fields:
            mappings.append({
                "source_slot": slot_name,
                "source_slot_description": slot_def.get("description", ""),
                "target_property": common_fields[slot_name],
                "confidence": "high",
                "match_type": "direct_match"
            })
    
    # Extract class slots from source schema
    source_classes = source_schema.get("classes", {})
    slots_by_class = {}
    
    for class_name, class_def in source_classes.items():
        class_slots = class_def.get("slots", [])
        slots_by_class[class_name] = class_slots
    
    # Special targeted mappings based on meaning
    special_mappings = [
        {"class": "Dataset", "slot": "license", "target": "overview.license"},
        {"class": "Dataset", "slot": "title", "target": "overview.title"},
        {"class": "Dataset", "slot": "description", "target": "overview.description"},
        {"class": "DiscouragedUse", "slot": "description", "target": "useCases.prohibitedUses"},
        {"class": "ExistingUse", "slot": "description", "target": "useCases.intendedUses"},
        {"class": "FutureUseImpact", "slot": "description", "target": "useCases.maintenancePlan"},
        {"class": "Creator", "slot": "principal_investigator", "target": "overview.principalInvestigator"},
        {"class": "DataSubset", "slot": "is_data_split", "target": "composition.datasets"},
        {"class": "DatasetCollection", "slot": "resources", "target": "composition.datasets"},
        {"class": "DistributionFormat", "slot": "description", "target": "composition.datasets.items.formats"}
    ]
    
    # Add special mappings if the class and slot exist
    for mapping in special_mappings:
        class_name = mapping["class"]
        slot_name = mapping["slot"]
        
        if class_name in source_classes and slot_name in slots_by_class.get(class_name, []):
            mappings.append({
                "source_class": class_name,
                "source_slot": slot_name,
                "target_property": mapping["target"],
                "confidence": "high",
                "match_type": "semantic_match"
            })
    
    # Create and write mapping file
    mapping_result = {
        "source_schema": source_schema_path,
        "target_schema": target_schema_path,
        "mappings": mappings
    }
    
    with open(output_path, 'w') as f:
        json.dump(mapping_result, f, indent=2)
    
    print(f"Created mapping file with {len(mappings)} mappings: {output_path}")
    return len(mappings) > 0

def map_schemas(source_schema, target_json_schema, output_path):
    """Map a LinkML schema to a target JSON schema."""
    # First convert JSON Schema to LinkML format (this helps with visualization)
    target_linkml_path = "target_schema.yaml"
    convert_json_schema_to_linkml(target_json_schema, target_linkml_path)
    
    # Create manual mapping since linkml-map has issues
    mapping_success = create_linkml_map_manually(
        source_schema,
        target_json_schema,
        output_path
    )
    
    if mapping_success:
        print("Schema mapping completed successfully")
        return True
    else:
        print("Schema mapping failed - no mappings created")
        return False

if __name__ == "__main__":
    # Default paths
    source_schema = "src/data_sheets_schema/schema/data_sheets_schema.yaml"
    target_schema = "data/RO-Crate/datasheet-schema.json"
    output_path = "mapped_schema.yaml"
    
    # Parse command line arguments
    if len(sys.argv) > 1:
        source_schema = sys.argv[1]
    if len(sys.argv) > 2:
        target_schema = sys.argv[2]
    if len(sys.argv) > 3:
        output_path = sys.argv[3]
    
    # Check if files exist
    if not os.path.exists(source_schema):
        print(f"Error: Source schema not found: {source_schema}")
        sys.exit(1)
    
    if not os.path.exists(target_schema):
        print(f"Error: Target schema not found: {target_schema}")
        sys.exit(1)
    
    # Run the mapping
    success = map_schemas(source_schema, target_schema, output_path)
    
    if success:
        print("Schema mapping completed successfully")
    else:
        print("Schema mapping failed")
        sys.exit(1)