#!/usr/bin/env python3
"""
Generate bidirectional schema mappings between LinkML Data Sheets Schema and RO-Crate Schema
"""

import yaml
import json
from pathlib import Path

def analyze_schemas():
    """Analyze both schemas and generate mapping documentation"""
    
    # Load LinkML schema
    with open('src/data_sheets_schema/schema/data_sheets_schema.yaml', 'r') as f:
        linkml_schema = yaml.safe_load(f)
    
    # Load RO-Crate JSON schema  
    with open('ro-crate/datasheet-schema.json', 'r') as f:
        rocrate_schema = json.load(f)
    
    print("=== LINKML TO RO-CRATE MAPPING ===\n")
    
    # Analyze LinkML classes and their potential RO-Crate mappings
    linkml_classes = linkml_schema.get('classes', {})
    rocrate_props = rocrate_schema.get('properties', {})
    
    mappings = {}
    
    # Key mappings identified from schema analysis
    mappings['Dataset'] = {
        'target': 'overview',
        'field_mappings': {
            'title': 'title',
            'id': 'identifier', 
            'version': 'version',
            'issued': 'datePublished',
            'description': 'description',
            'bytes': 'contentSize',
            'publisher': 'publisher',
            'license': 'license',
            'keywords': 'keywords',
            'doi': 'doi'
        }
    }
    
    mappings['Purpose'] = {
        'target': 'useCases.intendedUses',
        'field_mappings': {
            'response': 'intendedUses'
        }
    }
    
    mappings['DiscouragedUse'] = {
        'target': 'useCases.prohibitedUses',
        'field_mappings': {
            'description': 'prohibitedUses'
        }
    }
    
    mappings['FutureUseImpact'] = {
        'target': 'useCases.potentialSourcesOfBias',
        'field_mappings': {
            'description': 'potentialSourcesOfBias'
        }
    }
    
    mappings['UpdatePlan'] = {
        'target': 'useCases.maintenancePlan',
        'field_mappings': {
            'description': 'maintenancePlan'
        }
    }
    
    mappings['DataSubset'] = {
        'target': 'composition.datasets[]',
        'field_mappings': {
            'title': 'title',
            'id': 'identifier',
            'description': 'description', 
            'bytes': 'size',
            'license': 'license',
            'keywords': 'keywords',
            'doi': 'doi',
            'md5': 'md5'
        }
    }
    
    # Generate LinkML to RO-Crate mapping
    linkml_to_rocrate = {
        'id': 'https://w3id.org/bridge2ai/data-sheets-schema/linkml-to-rocrate-mapping',
        'title': 'LinkML Data Sheets Schema to RO-Crate Schema Mapping',
        'description': 'Bidirectional mapping between LinkML schema and RO-Crate JSON schema',
        'source_schema': 'src/data_sheets_schema/schema/data_sheets_schema.yaml',
        'target_schema': 'ro-crate/datasheet-schema.json',
        'mappings': mappings
    }
    
    # Save LinkML to RO-Crate mapping
    with open('linkml-to-rocrate-mapping.yaml', 'w') as f:
        yaml.dump(linkml_to_rocrate, f, default_flow_style=False, sort_keys=False)
    
    print("Generated: linkml-to-rocrate-mapping.yaml")
    
    # Generate reverse mapping
    reverse_mappings = {}
    
    reverse_mappings['overview'] = {
        'target': 'Dataset',
        'field_mappings': {
            'title': 'title',
            'identifier': 'id',
            'version': 'version', 
            'datePublished': 'issued',
            'description': 'description',
            'contentSize': 'bytes',
            'publisher': 'publisher',
            'license': 'license',
            'keywords': 'keywords',
            'doi': 'doi'
        }
    }
    
    reverse_mappings['useCases'] = {
        'target': 'Purpose, DiscouragedUse, FutureUseImpact, UpdatePlan',
        'field_mappings': {
            'intendedUses': 'Purpose.response',
            'prohibitedUses': 'DiscouragedUse.description',
            'potentialSourcesOfBias': 'FutureUseImpact.description',
            'maintenancePlan': 'UpdatePlan.description'
        }
    }
    
    reverse_mappings['composition.datasets'] = {
        'target': 'DataSubset',
        'field_mappings': {
            'title': 'title',
            'identifier': 'id',
            'description': 'description',
            'size': 'bytes', 
            'license': 'license',
            'keywords': 'keywords',
            'doi': 'doi',
            'md5': 'md5'
        }
    }
    
    rocrate_to_linkml = {
        'id': 'https://w3id.org/bridge2ai/data-sheets-schema/rocrate-to-linkml-mapping',
        'title': 'RO-Crate Schema to LinkML Data Sheets Schema Mapping',
        'description': 'Bidirectional mapping between RO-Crate JSON schema and LinkML schema',
        'source_schema': 'ro-crate/datasheet-schema.json',
        'target_schema': 'src/data_sheets_schema/schema/data_sheets_schema.yaml',
        'mappings': reverse_mappings
    }
    
    # Save RO-Crate to LinkML mapping
    with open('rocrate-to-linkml-mapping.yaml', 'w') as f:
        yaml.dump(rocrate_to_linkml, f, default_flow_style=False, sort_keys=False)
        
    print("Generated: rocrate-to-linkml-mapping.yaml")
    
    print("\n=== MAPPING SUMMARY ===")
    print("Key correspondences identified:")
    print("• LinkML Dataset ↔ RO-Crate overview section")
    print("• LinkML Purpose/Task classes ↔ RO-Crate useCases section") 
    print("• LinkML DataSubset ↔ RO-Crate composition.datasets array")
    print("• Common metadata fields: title, description, license, keywords, DOI")
    print("• Creator/funding info requires complex mapping")
    print("• Ethics/governance fields map to specialized RO-Crate sections")

def generate_mapping_documentation():
    """Generate comprehensive mapping documentation"""
    
    doc = """# Schema Mapping Documentation

## LinkML Data Sheets Schema ↔ RO-Crate Schema Mapping

### Overview
This document describes the bidirectional mapping between the LinkML Data Sheets Schema and the RO-Crate Datasheet JSON Schema.

### Core Mappings

#### 1. Dataset Level (LinkML Dataset → RO-Crate overview)
- `Dataset.title` → `overview.title`
- `Dataset.id` → `overview.identifier`
- `Dataset.version` → `overview.version`
- `Dataset.issued` → `overview.datePublished`
- `Dataset.description` → `overview.description`
- `Dataset.bytes` → `overview.contentSize`
- `Dataset.publisher` → `overview.publisher`
- `Dataset.license` → `overview.license`
- `Dataset.keywords` → `overview.keywords`
- `Dataset.doi` → `overview.doi`

#### 2. Use Cases (LinkML Purpose/Task → RO-Crate useCases)
- `Purpose.response` → `useCases.intendedUses`
- `DiscouragedUse.description` → `useCases.prohibitedUses`
- `FutureUseImpact.description` → `useCases.potentialSourcesOfBias`
- `UpdatePlan.description` → `useCases.maintenancePlan`

#### 3. Dataset Composition (LinkML DataSubset → RO-Crate composition.datasets)
- `DataSubset.title` → `datasets[].title`
- `DataSubset.id` → `datasets[].identifier`
- `DataSubset.description` → `datasets[].description`
- `DataSubset.bytes` → `datasets[].size`
- `DataSubset.license` → `datasets[].license`
- `DataSubset.keywords` → `datasets[].keywords`
- `DataSubset.doi` → `datasets[].doi`
- `DataSubset.md5` → `datasets[].md5`

#### 4. Complex Mappings Requiring Transformation

##### Creator Information
- LinkML: `Dataset.creators` (array of Creator objects)
- RO-Crate: `overview.authors` (string), `overview.principalInvestigator` (string)
- **Transformation**: Concatenate creator names, extract PI from first creator

##### Funding Information  
- LinkML: `Dataset.funders` (array of FundingMechanism objects)
- RO-Crate: `overview.funding` (string)
- **Transformation**: Extract grant numbers and concatenate

##### License and Terms
- LinkML: `Dataset.license_and_use_terms` (array of objects)
- RO-Crate: `overview.termsOfUse` (string)
- **Transformation**: Concatenate all use terms descriptions

##### Ethics and Governance
- LinkML: Multiple classes (EthicalReview, CollectionConsent, etc.)
- RO-Crate: `overview.humanSubjects` (object with specific fields)
- **Transformation**: Map specific ethical review fields to structured format

### Mapping Challenges

1. **Cardinality Differences**: LinkML uses arrays for many fields, RO-Crate often uses single strings
2. **Structural Differences**: LinkML has separate classes for different concepts, RO-Crate groups them
3. **Granularity**: LinkML provides more detailed categorization, RO-Crate is more concise
4. **Terminology**: Some concepts are expressed differently between schemas

### Usage

The mapping files can be used with:
- `linkml-map` for automated schema transformation  
- Custom transformation scripts for data mapping
- Documentation and cross-schema validation

### Files Generated
- `linkml-to-rocrate-mapping.yaml`: LinkML → RO-Crate mapping specification
- `rocrate-to-linkml-mapping.yaml`: RO-Crate → LinkML mapping specification
"""
    
    with open('MAPPING_DOCUMENTATION.md', 'w') as f:
        f.write(doc)
        
    print("Generated: MAPPING_DOCUMENTATION.md")

if __name__ == "__main__":
    analyze_schemas()
    generate_mapping_documentation()