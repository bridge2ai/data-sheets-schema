#!/usr/bin/env python3
"""
Generate SSSOM (Simple Standard for Sharing Ontology Mappings) from D4D SKOS alignment.

Validates mappings against:
1. RO-Crate JSON reference implementation
2. FAIRSCAPE Pydantic classes

Outputs:
- Full SSSOM mapping (all SKOS mappings)
- Subset SSSOM mapping (fields from d4d_rocrate_interface_mapping.tsv)
"""

import csv
import json
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime

# Add fairscape_models to path
fairscape_path = Path(__file__).parent.parent.parent / 'fairscape_models'
if fairscape_path.exists() and str(fairscape_path) not in sys.path:
    sys.path.insert(0, str(fairscape_path))

try:
    from fairscape_models.rocrate import ROCrateMetadataElem
    from fairscape_models.dataset import Dataset
    FAIRSCAPE_AVAILABLE = True
except ImportError:
    FAIRSCAPE_AVAILABLE = False
    print("Warning: FAIRSCAPE models not available")


class SSSOMGenerator:
    """Generate SSSOM mappings from SKOS alignment."""

    def __init__(
        self,
        skos_file: Path,
        rocrate_json: Path,
        mapping_tsv: Optional[Path] = None
    ):
        self.skos_file = skos_file
        self.rocrate_json = rocrate_json
        self.mapping_tsv = mapping_tsv

        # Load data
        self.skos_mappings = self._parse_skos()
        self.rocrate_data = self._load_rocrate_json()
        self.rocrate_properties = self._extract_rocrate_properties()
        self.pydantic_properties = self._extract_pydantic_properties()
        self.interface_fields = self._load_interface_mapping() if mapping_tsv else set()
        self.interface_paths = self._load_interface_paths() if mapping_tsv else {}

    def _parse_skos(self) -> List[Dict]:
        """Parse SKOS alignment TTL file."""
        with open(self.skos_file) as f:
            content = f.read()

        mappings = []

        # Pattern: d4d:property skos:matchType target:property .
        pattern = r'd4d:(\w+)\s+skos:(\w+Match)\s+(\S+)\s+\.'

        for match in re.finditer(pattern, content):
            subject = match.group(1)
            predicate = match.group(2)
            object_uri = match.group(3)

            mappings.append({
                'subject': subject,
                'predicate': predicate,
                'object': object_uri
            })

        return mappings

    def _load_rocrate_json(self) -> Dict:
        """Load RO-Crate JSON reference."""
        with open(self.rocrate_json) as f:
            return json.load(f)

    def _extract_rocrate_properties(self) -> set:
        """Extract all properties used in RO-Crate JSON."""
        properties = set()

        def extract_keys(obj):
            if isinstance(obj, dict):
                properties.update(obj.keys())
                for value in obj.values():
                    extract_keys(value)
            elif isinstance(obj, list):
                for item in obj:
                    extract_keys(item)

        extract_keys(self.rocrate_data)
        return properties

    def _extract_pydantic_properties(self) -> set:
        """Extract properties from FAIRSCAPE Pydantic models."""
        if not FAIRSCAPE_AVAILABLE:
            return set()

        properties = set()

        # Get fields from ROCrateMetadataElem (Dataset)
        for field_name, field_info in ROCrateMetadataElem.model_fields.items():
            properties.add(field_name)
            # Add alias if different
            if hasattr(field_info, 'alias') and field_info.alias:
                properties.add(field_info.alias)

        return properties

    def _load_interface_mapping(self) -> set:
        """Load D4D field names from interface mapping TSV."""
        fields = set()

        with open(self.mapping_tsv) as f:
            reader = csv.DictReader(f, delimiter='\t')
            for row in reader:
                # Extract field name from D4D_Full_Path (e.g., "Dataset.title" -> "title")
                if 'D4D_Full_Path' in row:
                    full_path = row['D4D_Full_Path']
                    if '.' in full_path:
                        field_name = full_path.split('.')[-1]
                        fields.add(field_name)
                # Fallback to D4D_Field if present
                elif 'D4D_Field' in row:
                    fields.add(row['D4D_Field'])

        return fields

    def _load_interface_paths(self) -> Dict[str, Dict[str, str]]:
        """Load D4D and RO-Crate path information from interface mapping TSV."""
        paths = {}

        with open(self.mapping_tsv) as f:
            reader = csv.DictReader(f, delimiter='\t')
            for row in reader:
                if 'D4D_Full_Path' not in row or 'RO_Crate_JSON_Path' not in row:
                    continue

                # Extract field name from D4D_Full_Path (e.g., "Dataset.title" -> "title")
                full_path = row['D4D_Full_Path']
                if '.' in full_path:
                    field_name = full_path.split('.')[-1]

                    # Prefer Dataset.{field} over other classes (e.g., Dataset.description
                    # over AnnotationAnalysis.description)
                    if field_name not in paths or full_path.startswith('Dataset.'):
                        paths[field_name] = {
                            'd4d_path': full_path,
                            'rocrate_path': row['RO_Crate_JSON_Path']
                        }

        return paths

    def _validate_mapping(self, mapping: Dict) -> Dict:
        """Validate mapping against RO-Crate JSON and Pydantic classes."""
        subject = mapping['subject']
        object_uri = mapping['object']

        # Extract property name from object URI
        if ':' in object_uri:
            object_prop = object_uri.split(':')[1]
        else:
            object_prop = object_uri

        # Check presence in sources
        in_json = object_prop in self.rocrate_properties
        in_pydantic = object_prop in self.pydantic_properties
        in_interface = subject in self.interface_fields

        # Determine source
        if in_json and in_pydantic:
            source = "RO-Crate JSON + Pydantic"
        elif in_json:
            source = "RO-Crate JSON"
        elif in_pydantic:
            source = "Pydantic"
        else:
            source = "Specification"

        return {
            'in_json': in_json,
            'in_pydantic': in_pydantic,
            'in_interface': in_interface,
            'source': source
        }

    def _get_mapping_confidence(self, predicate: str) -> float:
        """Get confidence score based on SKOS predicate."""
        confidence_map = {
            'exactMatch': 1.0,
            'closeMatch': 0.9,
            'relatedMatch': 0.7,
            'narrowMatch': 0.8,
            'broadMatch': 0.8
        }
        return confidence_map.get(predicate, 0.5)

    def _get_mapping_justification(self, predicate: str) -> str:
        """Get mapping justification based on SKOS predicate."""
        justification_map = {
            'exactMatch': 'semapv:ManualMappingCuration',
            'closeMatch': 'semapv:ManualMappingCuration',
            'relatedMatch': 'semapv:ManualMappingCuration',
            'narrowMatch': 'semapv:ManualMappingCuration',
            'broadMatch': 'semapv:ManualMappingCuration'
        }
        return justification_map.get(predicate, 'semapv:UnspecifiedMatching')

    def generate_sssom(self, subset: bool = False) -> List[Dict]:
        """Generate SSSOM mapping rows."""
        rows = []

        for mapping in self.skos_mappings:
            validation = self._validate_mapping(mapping)

            # Filter for subset if requested
            if subset and not validation['in_interface']:
                continue

            subject = mapping['subject']
            predicate = mapping['predicate']
            object_uri = mapping['object']

            # Build SSSOM row
            row = {
                'd4d_schema_path': self._get_d4d_schema_path(subject),
                'subject_id': f"d4d:{subject}",
                'subject_label': subject.replace('_', ' ').title(),
                'predicate_id': f"skos:{predicate}",
                'rocrate_json_path': self._get_rocrate_json_path(object_uri),
                'object_id': object_uri,
                'object_label': object_uri.split(':')[1] if ':' in object_uri else object_uri,
                'mapping_justification': self._get_mapping_justification(predicate),
                'confidence': self._get_mapping_confidence(predicate),
                'comment': f"Source: {validation['source']}",
                'author_id': 'https://orcid.org/0000-0000-0000-0000',  # Placeholder
                'mapping_date': datetime.now().strftime('%Y-%m-%d'),
                'subject_source': 'https://w3id.org/bridge2ai/data-sheets-schema/',
                'object_source': self._get_object_source(object_uri),
                'mapping_set_id': 'd4d-rocrate-alignment-v1',
                'mapping_set_version': '1.0',
                'in_rocrate_json': 'true' if validation['in_json'] else 'false',
                'in_pydantic_model': 'true' if validation['in_pydantic'] else 'false',
                'in_interface_mapping': 'true' if validation['in_interface'] else 'false'
            }

            rows.append(row)

        return rows

    def _get_d4d_schema_path(self, subject: str) -> str:
        """Get full D4D schema path for a property."""
        # Check if we have it in the interface mapping
        if subject in self.interface_paths:
            return self.interface_paths[subject]['d4d_path']

        # Default to Dataset.{property}
        return f"Dataset.{subject}"

    def _get_rocrate_json_path(self, object_uri: str) -> str:
        """Get full RO-Crate JSON path for a property."""
        # Extract property name from URI
        if ':' in object_uri:
            namespace, prop = object_uri.split(':', 1)
        else:
            namespace = 'schema'
            prop = object_uri

        # Check if we have it in the interface mapping (look up by property name in values)
        for field_name, path_info in self.interface_paths.items():
            rocrate_path = path_info['rocrate_path']
            # Check if this path contains the property we're looking for
            if f"['{prop}']" in rocrate_path or f"[\"{prop}\"]" in rocrate_path:
                return rocrate_path

        # Default path based on namespace
        if namespace == 'schema':
            return f"@graph[?@type='Dataset']['{prop}']"
        elif namespace in ['evi', 'rai', 'd4d']:
            return f"@graph[?@type='Dataset']['{namespace}:{prop}']"
        elif namespace == 'rdf':
            return f"@graph[?@type='Dataset']['@{prop.lower()}']"
        else:
            return f"@graph[?@type='Dataset']['{object_uri}']"

    def _get_object_source(self, object_uri: str) -> str:
        """Get source vocabulary for object URI."""
        if object_uri.startswith('schema:'):
            return 'https://schema.org/'
        elif object_uri.startswith('evi:'):
            return 'https://w3id.org/EVI#'
        elif object_uri.startswith('rai:'):
            return 'http://mlcommons.org/croissant/RAI/'
        elif object_uri.startswith('d4d:'):
            return 'https://w3id.org/bridge2ai/data-sheets-schema/'
        else:
            return 'unknown'

    def write_sssom(self, output_file: Path, subset: bool = False):
        """Write SSSOM TSV file."""
        rows = self.generate_sssom(subset=subset)

        if not rows:
            print(f"No mappings to write for {'subset' if subset else 'full'} SSSOM")
            return

        # SSSOM header
        fieldnames = [
            'd4d_schema_path',
            'subject_id',
            'subject_label',
            'predicate_id',
            'rocrate_json_path',
            'object_id',
            'object_label',
            'mapping_justification',
            'confidence',
            'comment',
            'author_id',
            'mapping_date',
            'subject_source',
            'object_source',
            'mapping_set_id',
            'mapping_set_version',
            'in_rocrate_json',
            'in_pydantic_model',
            'in_interface_mapping'
        ]

        with open(output_file, 'w', newline='') as f:
            # Write SSSOM metadata comments
            f.write('# SSSOM (Simple Standard for Sharing Ontology Mappings)\n')
            f.write('# Generated from D4D SKOS alignment\n')
            f.write(f'# Date: {datetime.now().isoformat()}\n')
            f.write(f'# Subset: {subset}\n')
            f.write(f'# Total mappings: {len(rows)}\n')
            f.write('#\n')

            writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter='\t')
            writer.writeheader()
            writer.writerows(rows)

        print(f"✓ Wrote {len(rows)} mappings to {output_file}")


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description='Generate SSSOM mapping from D4D SKOS alignment')
    parser.add_argument('--skos', default='src/data_sheets_schema/alignment/d4d_rocrate_skos_alignment.ttl',
                        help='SKOS alignment TTL file')
    parser.add_argument('--rocrate', default='data/ro-crate/profiles/fairscape/full-ro-crate-metadata.json',
                        help='RO-Crate JSON reference')
    parser.add_argument('--mapping', default='data/ro-crate_mapping/d4d_rocrate_interface_mapping.tsv',
                        help='Interface mapping TSV file')
    parser.add_argument('--output', default='src/data_sheets_schema/alignment/d4d_rocrate_sssom_mapping.tsv',
                        help='Output SSSOM file (full)')
    parser.add_argument('--output-subset', default='src/data_sheets_schema/alignment/d4d_rocrate_sssom_mapping_subset.tsv',
                        help='Output SSSOM file (subset)')

    args = parser.parse_args()

    # Validate input files
    skos_file = Path(args.skos)
    rocrate_file = Path(args.rocrate)
    mapping_file = Path(args.mapping)

    if not skos_file.exists():
        print(f"Error: SKOS file not found: {skos_file}")
        return 1

    if not rocrate_file.exists():
        print(f"Error: RO-Crate JSON not found: {rocrate_file}")
        return 1

    if not mapping_file.exists():
        print(f"Warning: Interface mapping not found: {mapping_file}")
        mapping_file = None

    # Generate SSSOM
    generator = SSSOMGenerator(skos_file, rocrate_file, mapping_file)

    # Create output directories
    output_file = Path(args.output)
    output_subset_file = Path(args.output_subset)

    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_subset_file.parent.mkdir(parents=True, exist_ok=True)

    # Write full SSSOM
    print("\nGenerating full SSSOM mapping...")
    generator.write_sssom(output_file, subset=False)

    # Write subset SSSOM
    if mapping_file:
        print("\nGenerating subset SSSOM mapping (interface fields only)...")
        generator.write_sssom(output_subset_file, subset=True)

    print("\n✓ SSSOM generation complete")
    return 0


if __name__ == '__main__':
    sys.exit(main())
