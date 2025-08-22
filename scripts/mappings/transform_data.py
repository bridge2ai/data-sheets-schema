#!/usr/bin/env python3
"""
Transform data between LinkML Data Sheets format and RO-Crate format

This script provides bidirectional data transformation capabilities using the
generated schema mappings.

Usage:
    python scripts/mappings/transform_data.py
"""

import yaml
import json
from typing import Dict, Any, List, Optional
from pathlib import Path

class SchemaMapper:
    def __init__(self):
        # Load mapping specifications
        with open('linkml-to-rocrate-mapping.yaml', 'r') as f:
            self.linkml_to_rocrate = yaml.safe_load(f)
        
        with open('rocrate-to-linkml-mapping.yaml', 'r') as f:
            self.rocrate_to_linkml = yaml.safe_load(f)
    
    def transform_linkml_to_rocrate(self, linkml_data: Dict[str, Any]) -> Dict[str, Any]:
        """Transform LinkML data to RO-Crate format"""
        
        rocrate_data = {
            "overview": {},
            "useCases": {},
            "composition": {
                "datasets": []
            }
        }
        
        # Handle Dataset -> overview mapping
        if 'datasets' in linkml_data:
            for dataset in linkml_data['datasets']:
                overview = self._map_dataset_to_overview(dataset)
                rocrate_data['overview'].update(overview)
                
                # Map use cases from various LinkML classes
                use_cases = self._map_to_use_cases(dataset)
                rocrate_data['useCases'].update(use_cases)
                
                # Map subsets to composition datasets
                if 'subsets' in dataset:
                    for subset in dataset['subsets']:
                        comp_dataset = self._map_subset_to_composition(subset)
                        rocrate_data['composition']['datasets'].append(comp_dataset)
        
        return rocrate_data
    
    def transform_rocrate_to_linkml(self, rocrate_data: Dict[str, Any]) -> Dict[str, Any]:
        """Transform RO-Crate data to LinkML format"""
        
        linkml_data = {
            "datasets": []
        }
        
        # Create main dataset from overview
        dataset = self._map_overview_to_dataset(rocrate_data.get('overview', {}))
        
        # Add use cases information
        if 'useCases' in rocrate_data:
            use_cases_data = self._map_use_cases_to_linkml(rocrate_data['useCases'])
            dataset.update(use_cases_data)
        
        # Add composition datasets as subsets
        if 'composition' in rocrate_data and 'datasets' in rocrate_data['composition']:
            dataset['subsets'] = []
            for comp_dataset in rocrate_data['composition']['datasets']:
                subset = self._map_composition_to_subset(comp_dataset)
                dataset['subsets'].append(subset)
        
        linkml_data['datasets'].append(dataset)
        return linkml_data
    
    def _map_dataset_to_overview(self, dataset: Dict[str, Any]) -> Dict[str, Any]:
        """Map LinkML Dataset to RO-Crate overview"""
        mapping = self.linkml_to_rocrate['mappings']['Dataset']['field_mappings']
        overview = {}
        
        for linkml_field, rocrate_field in mapping.items():
            if linkml_field in dataset:
                overview[rocrate_field] = dataset[linkml_field]
        
        # Handle complex mappings
        if 'creators' in dataset:
            creators = dataset['creators']
            if creators:
                # Concatenate creator names
                overview['authors'] = ', '.join([
                    creator.get('name', '') for creator in creators if creator.get('name')
                ])
                # Get PI from first creator
                if creators[0].get('principal_investigator'):
                    pi = creators[0]['principal_investigator']
                    overview['principalInvestigator'] = pi.get('name', '')
                    overview['contactEmail'] = pi.get('email', '')
        
        if 'funders' in dataset:
            funders = dataset['funders']
            grant_numbers = []
            for funder in funders:
                if 'grant' in funder and 'grant_number' in funder['grant']:
                    grant_numbers.append(funder['grant']['grant_number'])
            if grant_numbers:
                overview['funding'] = ', '.join(grant_numbers)
        
        return overview
    
    def _map_to_use_cases(self, dataset: Dict[str, Any]) -> Dict[str, Any]:
        """Map LinkML dataset to RO-Crate useCases"""
        use_cases = {}
        
        # Map purposes to intended uses
        if 'purposes' in dataset:
            purposes = [p.get('response', '') for p in dataset['purposes'] if p.get('response')]
            if purposes:
                use_cases['intendedUses'] = '; '.join(purposes)
        
        # Map discouraged uses
        if 'discouraged_uses' in dataset:
            discouraged = [d.get('description', '') for d in dataset['discouraged_uses'] if d.get('description')]
            if discouraged:
                use_cases['prohibitedUses'] = '; '.join(discouraged)
        
        # Map future use impacts to bias sources
        if 'future_use_impacts' in dataset:
            impacts = [i.get('description', '') for i in dataset['future_use_impacts'] if i.get('description')]
            if impacts:
                use_cases['potentialSourcesOfBias'] = '; '.join(impacts)
        
        # Map update plan to maintenance
        if 'updates' in dataset and 'description' in dataset['updates']:
            use_cases['maintenancePlan'] = dataset['updates']['description']
        
        return use_cases
    
    def _map_subset_to_composition(self, subset: Dict[str, Any]) -> Dict[str, Any]:
        """Map LinkML DataSubset to RO-Crate composition dataset"""
        mapping = self.linkml_to_rocrate['mappings']['DataSubset']['field_mappings']
        comp_dataset = {}
        
        for linkml_field, rocrate_field in mapping.items():
            if linkml_field in subset:
                comp_dataset[rocrate_field] = subset[linkml_field]
        
        # Add required fields with defaults if missing
        required_fields = ['title', 'identifier', 'description', 'authors', 'size', 'copyright', 'license']
        for field in required_fields:
            if field not in comp_dataset:
                comp_dataset[field] = ""
        
        return comp_dataset
    
    def _map_overview_to_dataset(self, overview: Dict[str, Any]) -> Dict[str, Any]:
        """Map RO-Crate overview to LinkML Dataset"""
        mapping = self.rocrate_to_linkml['mappings']['overview']['field_mappings']
        dataset = {}
        
        for rocrate_field, linkml_field in mapping.items():
            if rocrate_field in overview:
                dataset[linkml_field] = overview[rocrate_field]
        
        # Handle complex reverse mappings
        if 'authors' in overview:
            authors = overview['authors'].split(', ') if overview['authors'] else []
            dataset['creators'] = [{'name': author} for author in authors if author]
        
        if 'principalInvestigator' in overview or 'contactEmail' in overview:
            if 'creators' not in dataset:
                dataset['creators'] = [{}]
            dataset['creators'][0]['principal_investigator'] = {
                'name': overview.get('principalInvestigator', ''),
                'email': overview.get('contactEmail', '')
            }
        
        if 'funding' in overview:
            grant_numbers = overview['funding'].split(', ') if overview['funding'] else []
            dataset['funders'] = [
                {'grant': {'grant_number': gn}} for gn in grant_numbers if gn
            ]
        
        return dataset
    
    def _map_use_cases_to_linkml(self, use_cases: Dict[str, Any]) -> Dict[str, Any]:
        """Map RO-Crate useCases to LinkML classes"""
        linkml_data = {}
        
        if 'intendedUses' in use_cases:
            purposes = use_cases['intendedUses'].split('; ') if use_cases['intendedUses'] else []
            linkml_data['purposes'] = [{'response': p} for p in purposes if p]
        
        if 'prohibitedUses' in use_cases:
            prohibited = use_cases['prohibitedUses'].split('; ') if use_cases['prohibitedUses'] else []
            linkml_data['discouraged_uses'] = [{'description': p} for p in prohibited if p]
        
        if 'potentialSourcesOfBias' in use_cases:
            biases = use_cases['potentialSourcesOfBias'].split('; ') if use_cases['potentialSourcesOfBias'] else []
            linkml_data['future_use_impacts'] = [{'description': b} for b in biases if b]
        
        if 'maintenancePlan' in use_cases:
            linkml_data['updates'] = {'description': use_cases['maintenancePlan']}
        
        return linkml_data
    
    def _map_composition_to_subset(self, comp_dataset: Dict[str, Any]) -> Dict[str, Any]:
        """Map RO-Crate composition dataset to LinkML DataSubset"""
        mapping = self.rocrate_to_linkml['mappings']['composition.datasets']['field_mappings']
        subset = {}
        
        for rocrate_field, linkml_field in mapping.items():
            if rocrate_field in comp_dataset:
                subset[linkml_field] = comp_dataset[rocrate_field]
        
        return subset

def example_usage():
    """Demonstrate the mapping functionality"""
    
    mapper = SchemaMapper()
    
    # Example LinkML data
    linkml_example = {
        "datasets": [{
            "id": "dataset-001",
            "title": "Example Medical Dataset",
            "description": "A comprehensive medical dataset for research",
            "version": "1.0",
            "issued": "2024-01-01",
            "bytes": 1000000,
            "publisher": "Medical Research Institute",
            "license": "https://creativecommons.org/licenses/by/4.0/",
            "keywords": "medical, research, dataset",
            "doi": "https://doi.org/10.1234/example",
            "creators": [{
                "name": "Dr. Jane Smith",
                "principal_investigator": {
                    "name": "Dr. Jane Smith",
                    "email": "jane.smith@example.org"
                }
            }],
            "funders": [{
                "grant": {
                    "grant_number": "NIH-123456"
                }
            }],
            "purposes": [{
                "response": "Medical research and clinical decision support"
            }],
            "discouraged_uses": [{
                "description": "Commercial use without proper licensing"
            }],
            "subsets": [{
                "id": "subset-001",
                "title": "Training Data",
                "description": "Data for model training",
                "bytes": 500000,
                "license": "https://creativecommons.org/licenses/by/4.0/"
            }]
        }]
    }
    
    # Transform to RO-Crate format
    rocrate_result = mapper.transform_linkml_to_rocrate(linkml_example)
    
    print("=== LinkML to RO-Crate Transformation ===")
    print(json.dumps(rocrate_result, indent=2))
    
    # Transform back to LinkML format
    linkml_result = mapper.transform_rocrate_to_linkml(rocrate_result)
    
    print("\n=== RO-Crate to LinkML Transformation ===")
    print(yaml.dump(linkml_result, default_flow_style=False))
    
    # Save examples
    with open('example_rocrate.json', 'w') as f:
        json.dump(rocrate_result, f, indent=2)
    
    with open('example_linkml.yaml', 'w') as f:
        yaml.dump(linkml_result, f, default_flow_style=False)
    
    print("Saved example transformations to example_rocrate.json and example_linkml.yaml")

if __name__ == "__main__":
    example_usage()