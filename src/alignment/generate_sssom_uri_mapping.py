#!/usr/bin/env python3
"""
Generate URI-level SSSOM mapping between D4D slot URIs and RO-Crate property URIs.

Maps at the semantic/vocabulary level using:
- D4D: slot_uri definitions from LinkML schema
- RO-Crate: JSON-LD property names (aliases) from FAIRSCAPE

Shows semantic alignment between vocabularies (dcterms, dcat, schema.org, etc.)
"""

import csv
import json
import re
import sys
import yaml
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime

# Note: FAIRSCAPE models not required for URI-level SSSOM generation


class SSSOMURIGenerator:
    """Generate URI-level SSSOM mappings from D4D slot URIs to RO-Crate property URIs."""

    def __init__(
        self,
        d4d_schema: Path,
        skos_file: Path,
        rocrate_json: Path
    ):
        self.d4d_schema = d4d_schema
        self.skos_file = skos_file
        self.rocrate_json = rocrate_json

        # Load data
        self.d4d_slots = self._load_d4d_slots()
        self.skos_mappings = self._parse_skos()

    def _load_d4d_slots(self) -> Dict[str, str]:
        """Load D4D slot_uri mappings from schema."""
        with open(self.d4d_schema) as f:
            schema = yaml.safe_load(f)

        slots_with_uri = {}
        for slot_name, slot_def in schema.get('slots', {}).items():
            if 'slot_uri' in slot_def:
                slots_with_uri[slot_name] = slot_def['slot_uri']

        return slots_with_uri

    def _parse_skos(self) -> Dict[str, str]:
        """Parse SKOS alignment to get D4D → RO-Crate property mappings."""
        with open(self.skos_file) as f:
            content = f.read()

        mappings = {}
        # Pattern: d4d:property skos:matchType target:property .
        pattern = r'd4d:(\w+)\s+skos:(\w+Match)\s+(\S+)\s+\.'

        for match in re.finditer(pattern, content):
            d4d_property = match.group(1)
            predicate = match.group(2)
            rocrate_uri = match.group(3)
            mappings[d4d_property] = {
                'rocrate_uri': rocrate_uri,
                'predicate': predicate
            }

        return mappings

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
        return 'semapv:ManualMappingCuration'

    def _determine_match_type(self, d4d_uri: str, rocrate_uri: str) -> tuple[str, float]:
        """Determine match type and confidence between two URIs."""
        # Exact match if URIs are identical
        if d4d_uri == rocrate_uri:
            return 'skos:exactMatch', 1.0

        # Extract namespace and property
        d4d_ns = d4d_uri.split(':')[0] if ':' in d4d_uri else ''
        d4d_prop = d4d_uri.split(':')[1] if ':' in d4d_uri else d4d_uri

        rocrate_ns = rocrate_uri.split(':')[0] if ':' in rocrate_uri else ''
        rocrate_prop = rocrate_uri.split(':')[1] if ':' in rocrate_uri else rocrate_uri

        # Close match if same property, different namespace
        # (e.g., dcterms:title vs schema:name for D4D title)
        if d4d_ns != rocrate_ns:
            # Known vocabulary equivalences
            vocab_equiv = {
                ('dcterms', 'schema'): 'closeMatch',
                ('dcat', 'schema'): 'closeMatch',
                ('dcat', 'evi'): 'closeMatch',
            }

            match_type = vocab_equiv.get((d4d_ns, rocrate_ns), 'relatedMatch')
            confidence = 0.9 if match_type == 'closeMatch' else 0.7
            return f'skos:{match_type}', confidence

        return 'skos:relatedMatch', 0.7

    def generate_sssom(self) -> List[Dict]:
        """Generate URI-level SSSOM mapping rows."""
        rows = []

        for d4d_property, d4d_uri in self.d4d_slots.items():
            # Find corresponding RO-Crate URI from SKOS alignment
            if d4d_property not in self.skos_mappings:
                # No SKOS mapping for this property
                continue

            rocrate_uri = self.skos_mappings[d4d_property]['rocrate_uri']
            skos_predicate = self.skos_mappings[d4d_property]['predicate']

            # Determine match type between URIs
            match_type, confidence = self._determine_match_type(d4d_uri, rocrate_uri)

            # Build SSSOM row
            row = {
                'subject_id': d4d_uri,
                'subject_label': d4d_uri.split(':')[1] if ':' in d4d_uri else d4d_uri,
                'subject_source': self._get_vocab_source(d4d_uri),
                'predicate_id': match_type,
                'object_id': rocrate_uri,
                'object_label': rocrate_uri.split(':')[1] if ':' in rocrate_uri else rocrate_uri,
                'object_source': self._get_vocab_source(rocrate_uri),
                'mapping_justification': self._get_mapping_justification(skos_predicate),
                'confidence': confidence,
                'comment': f"D4D slot '{d4d_property}' (slot_uri: {d4d_uri}) → RO-Crate '{rocrate_uri}'",
                'author_id': 'https://orcid.org/0000-0000-0000-0000',
                'mapping_date': datetime.now().strftime('%Y-%m-%d'),
                'mapping_set_id': 'd4d-rocrate-uri-alignment-v1',
                'mapping_set_version': '1.0',
                'd4d_slot_name': d4d_property,
                'vocab_crosswalk': 'true' if d4d_uri.split(':')[0] != rocrate_uri.split(':')[0] else 'false'
            }

            rows.append(row)

        return rows

    def _get_vocab_source(self, uri: str) -> str:
        """Get source vocabulary URL for a URI."""
        if ':' not in uri:
            return 'unknown'

        namespace = uri.split(':')[0]
        vocab_sources = {
            'schema': 'https://schema.org/',
            'dcterms': 'http://purl.org/dc/terms/',
            'dcat': 'https://www.w3.org/ns/dcat#',
            'prov': 'http://www.w3.org/ns/prov#',
            'evi': 'https://w3id.org/EVI#',
            'rai': 'http://mlcommons.org/croissant/RAI/',
            'd4d': 'https://w3id.org/bridge2ai/data-sheets-schema/',
            'rdf': 'http://www.w3.org/1999/02/22-rdf-syntax-ns#',
            'rdfs': 'http://www.w3.org/2000/01/rdf-schema#'
        }

        return vocab_sources.get(namespace, 'unknown')

    def write_sssom(self, output_file: Path):
        """Write URI-level SSSOM TSV file."""
        rows = self.generate_sssom()

        if not rows:
            print("No URI mappings to write")
            return

        # SSSOM header
        fieldnames = [
            'subject_id',
            'subject_label',
            'subject_source',
            'predicate_id',
            'object_id',
            'object_label',
            'object_source',
            'mapping_justification',
            'confidence',
            'comment',
            'author_id',
            'mapping_date',
            'mapping_set_id',
            'mapping_set_version',
            'd4d_slot_name',
            'vocab_crosswalk'
        ]

        with open(output_file, 'w', newline='') as f:
            # Write SSSOM metadata comments
            f.write('# SSSOM URI-level Mapping (D4D slot URIs ↔ RO-Crate property URIs)\n')
            f.write('# Generated from D4D LinkML schema slot_uri definitions\n')
            f.write(f'# Date: {datetime.now().isoformat()}\n')
            f.write(f'# Total mappings: {len(rows)}\n')
            f.write('#\n')
            f.write('# Maps at the vocabulary/semantic level using:\n')
            f.write('# - D4D: slot_uri from LinkML schema (dcterms, dcat, schema, prov)\n')
            f.write('# - RO-Crate: JSON-LD property URIs (schema.org, EVI, RAI, D4D)\n')
            f.write('#\n')

            writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter='\t')
            writer.writeheader()
            writer.writerows(rows)

        print(f"✓ Wrote {len(rows)} URI-level mappings to {output_file}")


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description='Generate URI-level SSSOM mapping (D4D slot URIs → RO-Crate property URIs)'
    )
    parser.add_argument(
        '--schema',
        default='src/data_sheets_schema/schema/data_sheets_schema_all.yaml',
        help='D4D LinkML schema file'
    )
    parser.add_argument(
        '--skos',
        default='src/data_sheets_schema/alignment/d4d_rocrate_skos_alignment.ttl',
        help='SKOS alignment file'
    )
    parser.add_argument(
        '--rocrate',
        default='data/ro-crate/profiles/fairscape/full-ro-crate-metadata.json',
        help='RO-Crate JSON reference'
    )
    parser.add_argument(
        '--output',
        default='src/data_sheets_schema/alignment/d4d_rocrate_sssom_uri_mapping.tsv',
        help='Output SSSOM URI mapping file'
    )

    args = parser.parse_args()

    # Validate input files
    schema_file = Path(args.schema)
    skos_file = Path(args.skos)
    rocrate_file = Path(args.rocrate)

    if not schema_file.exists():
        print(f"Error: D4D schema not found: {schema_file}")
        return 1

    if not skos_file.exists():
        print(f"Error: SKOS file not found: {skos_file}")
        return 1

    if not rocrate_file.exists():
        print(f"Error: RO-Crate JSON not found: {rocrate_file}")
        return 1

    # Generate URI-level SSSOM
    generator = SSSOMURIGenerator(schema_file, skos_file, rocrate_file)

    # Create output directory
    output_file = Path(args.output)
    output_file.parent.mkdir(parents=True, exist_ok=True)

    # Write SSSOM
    print("\nGenerating URI-level SSSOM mapping...")
    generator.write_sssom(output_file)

    print("\n✓ URI-level SSSOM generation complete")
    return 0


if __name__ == '__main__':
    sys.exit(main())
