#!/usr/bin/env python3
"""
Generate comprehensive SSSOM mapping including ALL D4D attributes.

Extends the existing SKOS-based SSSOM with:
1. Attributes from SKOS alignment (95 mapped)
2. Attributes with recommended URIs (97 could have URIs)
3. Novel D4D concepts (47 need D4D namespace)
4. Free text fields (17 marked as unmapped)
5. Remaining attributes (needs research)
"""

import csv
import json
import re
import sys
import yaml
from pathlib import Path
from typing import Dict, List, Optional, Set
from datetime import datetime

# Add fairscape_models to path
fairscape_path = Path(__file__).parent.parent.parent / 'fairscape_models'
if fairscape_path.exists() and str(fairscape_path) not in sys.path:
    sys.path.insert(0, str(fairscape_path))

try:
    from fairscape_models.rocrate import ROCrateMetadataElem
    FAIRSCAPE_AVAILABLE = True
except ImportError:
    FAIRSCAPE_AVAILABLE = False


class ComprehensiveSSSOMGenerator:
    """Generate comprehensive SSSOM including all D4D attributes."""

    def __init__(
        self,
        d4d_schema: Path,
        skos_file: Path,
        recommendations_file: Optional[Path] = None
    ):
        self.d4d_schema = d4d_schema
        self.skos_file = skos_file
        self.recommendations_file = recommendations_file

        # Load data
        self.d4d_attributes = self._load_d4d_attributes()
        self.skos_mappings = self._parse_skos()
        self.recommendations = self._load_recommendations() if recommendations_file else {}

    def _load_d4d_attributes(self) -> Dict[str, Dict]:
        """Load all D4D attributes from schema."""
        with open(self.d4d_schema) as f:
            schema = yaml.safe_load(f)

        attributes = {}
        for class_name, class_def in schema.get('classes', {}).items():
            attrs = class_def.get('attributes', {})
            for attr_name, attr_def in attrs.items():
                if attr_name not in attributes:
                    attributes[attr_name] = {
                        'description': attr_def.get('description', ''),
                        'range': attr_def.get('range', 'string'),
                        'slot_uri': attr_def.get('slot_uri', ''),
                        'classes': [class_name]
                    }
                else:
                    attributes[attr_name]['classes'].append(class_name)

        return attributes

    def _parse_skos(self) -> Dict[str, Dict]:
        """Parse SKOS alignment."""
        with open(self.skos_file) as f:
            content = f.read()

        mappings = {}
        pattern = r'd4d:(\w+)\s+skos:(\w+Match)\s+(\S+)\s+\.'

        for match in re.finditer(pattern, content):
            d4d_property = match.group(1)
            predicate = match.group(2)
            rocrate_uri = match.group(3)
            mappings[d4d_property] = {
                'predicate': predicate,
                'rocrate_uri': rocrate_uri
            }

        return mappings

    def _load_recommendations(self) -> Dict[str, Dict]:
        """Load URI recommendations from TSV."""
        recommendations = {}

        if not self.recommendations_file.exists():
            return recommendations

        with open(self.recommendations_file) as f:
            reader = csv.DictReader(f, delimiter='\t')
            for row in reader:
                attr = row['attribute']
                recommendations[attr] = {
                    'suggested_uri': row.get('suggested_uri', ''),
                    'confidence': row.get('confidence', 'unknown')
                }

        return recommendations

    def _categorize_attribute(self, attr_name: str, attr_info: Dict) -> str:
        """Categorize attribute type."""
        description = attr_info['description'].lower()
        attr_lower = attr_name.lower()

        # Free text
        if any(kw in attr_lower or kw in description
               for kw in ['description', 'documentation', 'comment', 'notes',
                         'details', 'narrative', 'paragraph']):
            return 'free_text'

        # Novel D4D
        if any(kw in attr_lower or kw in description
               for kw in ['strategies', 'protocol', 'analyses', 'compensation',
                         'governance', 'warnings', 'gaps', 'impacts', 'biases',
                         'imputation', 'deidentif', 'confidential', 'vulnerable',
                         'ethical', 'prohibited', 'retention', 'errata']):
            return 'novel_d4d'

        # Has SKOS mapping
        if attr_name in self.skos_mappings:
            return 'mapped'

        # Has recommendation
        if attr_name in self.recommendations:
            return 'recommended'

        return 'unmapped'

    def generate_comprehensive_sssom(self) -> List[Dict]:
        """Generate comprehensive SSSOM rows for all D4D attributes."""
        rows = []

        for attr_name, attr_info in sorted(self.d4d_attributes.items()):
            category = self._categorize_attribute(attr_name, attr_info)

            # Build SSSOM row
            row = {
                'd4d_schema_path': f"Dataset.{attr_name}",
                'subject_id': f"d4d:{attr_name}",
                'subject_label': attr_name.replace('_', ' ').title(),
                'subject_source': 'https://w3id.org/bridge2ai/data-sheets-schema/',
            }

            # Determine predicate and object based on category
            if category == 'mapped':
                # Has SKOS mapping
                mapping = self.skos_mappings[attr_name]
                row.update({
                    'predicate_id': f"skos:{mapping['predicate']}",
                    'rocrate_json_path': self._get_rocrate_path(mapping['rocrate_uri']),
                    'object_id': mapping['rocrate_uri'],
                    'object_label': mapping['rocrate_uri'].split(':')[1] if ':' in mapping['rocrate_uri'] else mapping['rocrate_uri'],
                    'object_source': self._get_vocab_source(mapping['rocrate_uri']),
                    'confidence': self._get_confidence(mapping['predicate']),
                    'mapping_justification': 'semapv:ManualMappingCuration',
                    'comment': f"Mapped via SKOS alignment",
                    'mapping_status': 'mapped'
                })

            elif category == 'recommended':
                # Has URI recommendation
                rec = self.recommendations[attr_name]
                suggested_uri = rec['suggested_uri']

                row.update({
                    'predicate_id': 'skos:closeMatch' if suggested_uri else 'semapv:UnmappedProperty',
                    'rocrate_json_path': self._get_rocrate_path(suggested_uri) if suggested_uri else '',
                    'object_id': suggested_uri if suggested_uri else '',
                    'object_label': suggested_uri.split(':')[1] if ':' in suggested_uri else suggested_uri,
                    'object_source': self._get_vocab_source(suggested_uri) if suggested_uri else '',
                    'confidence': 0.7 if rec['confidence'] == 'high' else 0.5,
                    'mapping_justification': 'semapv:SuggestedMapping',
                    'comment': f"Recommended mapping (confidence: {rec['confidence']})",
                    'mapping_status': 'recommended'
                })

            elif category == 'novel_d4d':
                # Novel D4D concept - needs D4D namespace
                d4d_uri = f"d4d:{attr_name}"
                row.update({
                    'predicate_id': 'skos:exactMatch',
                    'rocrate_json_path': f"@graph[?@type='Dataset']['{d4d_uri}']",
                    'object_id': d4d_uri,
                    'object_label': attr_name,
                    'object_source': 'https://w3id.org/bridge2ai/data-sheets-schema/',
                    'confidence': 1.0,
                    'mapping_justification': 'semapv:ManualMappingCuration',
                    'comment': 'Novel D4D concept - uses D4D namespace',
                    'mapping_status': 'novel_d4d'
                })

            elif category == 'free_text':
                # Free text field - no mapping needed
                row.update({
                    'predicate_id': 'semapv:UnmappableProperty',
                    'rocrate_json_path': '',
                    'object_id': '',
                    'object_label': '',
                    'object_source': '',
                    'confidence': 0.0,
                    'mapping_justification': 'semapv:FreeTextProperty',
                    'comment': 'Free text/narrative field - no URI needed',
                    'mapping_status': 'free_text'
                })

            else:
                # Unmapped - needs research
                row.update({
                    'predicate_id': 'semapv:UnmappedProperty',
                    'rocrate_json_path': '',
                    'object_id': '',
                    'object_label': '',
                    'object_source': '',
                    'confidence': 0.0,
                    'mapping_justification': 'semapv:RequiresResearch',
                    'comment': 'Unmapped - needs vocabulary research',
                    'mapping_status': 'unmapped'
                })

            # Add common fields
            row.update({
                'author_id': 'https://orcid.org/0000-0000-0000-0000',
                'mapping_date': datetime.now().strftime('%Y-%m-%d'),
                'mapping_set_id': 'd4d-rocrate-comprehensive-v1',
                'mapping_set_version': '1.0',
                'd4d_description': attr_info['description'][:100] + '...' if len(attr_info['description']) > 100 else attr_info['description']
            })

            rows.append(row)

        return rows

    def _get_rocrate_path(self, uri: str) -> str:
        """Get RO-Crate JSON path for a URI."""
        if not uri:
            return ''

        if ':' in uri:
            ns, prop = uri.split(':', 1)
            if ns in ['evi', 'rai', 'd4d']:
                return f"@graph[?@type='Dataset']['{uri}']"
            else:
                return f"@graph[?@type='Dataset']['{prop}']"
        return f"@graph[?@type='Dataset']['{uri}']"

    def _get_vocab_source(self, uri: str) -> str:
        """Get vocabulary source URL."""
        if not uri or ':' not in uri:
            return ''

        namespace = uri.split(':')[0]
        sources = {
            'schema': 'https://schema.org/',
            'dcterms': 'http://purl.org/dc/terms/',
            'dcat': 'https://www.w3.org/ns/dcat#',
            'prov': 'http://www.w3.org/ns/prov#',
            'evi': 'https://w3id.org/EVI#',
            'rai': 'http://mlcommons.org/croissant/RAI/',
            'd4d': 'https://w3id.org/bridge2ai/data-sheets-schema/',
        }
        return sources.get(namespace, 'unknown')

    def _get_confidence(self, predicate: str) -> float:
        """Get confidence based on SKOS predicate."""
        confidence_map = {
            'exactMatch': 1.0,
            'closeMatch': 0.9,
            'relatedMatch': 0.7,
            'narrowMatch': 0.8,
            'broadMatch': 0.8
        }
        return confidence_map.get(predicate, 0.5)

    def write_sssom(self, output_file: Path):
        """Write comprehensive SSSOM TSV."""
        rows = self.generate_comprehensive_sssom()

        if not rows:
            print("No mappings to write")
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
            'mapping_status',
            'd4d_description'
        ]

        with open(output_file, 'w', newline='') as f:
            # Write SSSOM metadata
            f.write('# Comprehensive SSSOM Mapping - ALL D4D Attributes\n')
            f.write('# Includes mapped, recommended, novel, free text, and unmapped attributes\n')
            f.write(f'# Date: {datetime.now().isoformat()}\n')
            f.write(f'# Total attributes: {len(rows)}\n')

            # Count by status
            status_counts = {}
            for row in rows:
                status = row['mapping_status']
                status_counts[status] = status_counts.get(status, 0) + 1

            f.write(f'#\n')
            f.write('# Status breakdown:\n')
            for status, count in sorted(status_counts.items()):
                f.write(f'#   {status}: {count}\n')
            f.write('#\n')

            writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter='\t')
            writer.writeheader()
            writer.writerows(rows)

        print(f"✓ Wrote {len(rows)} comprehensive mappings to {output_file}")
        print(f"\nStatus breakdown:")
        for status, count in sorted(status_counts.items()):
            print(f"  {status}: {count}")


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description='Generate comprehensive SSSOM for ALL D4D attributes'
    )
    parser.add_argument(
        '--schema',
        default='src/data_sheets_schema/schema/data_sheets_schema_all.yaml',
        help='D4D schema file'
    )
    parser.add_argument(
        '--skos',
        default='src/data_sheets_schema/alignment/d4d_rocrate_skos_alignment.ttl',
        help='SKOS alignment file'
    )
    parser.add_argument(
        '--recommendations',
        default='notes/D4D_MISSING_URI_RECOMMENDATIONS.tsv',
        help='URI recommendations file'
    )
    parser.add_argument(
        '--output',
        default='src/data_sheets_schema/alignment/d4d_rocrate_sssom_comprehensive.tsv',
        help='Output comprehensive SSSOM file'
    )

    args = parser.parse_args()

    # Generate comprehensive SSSOM
    generator = ComprehensiveSSSOMGenerator(
        Path(args.schema),
        Path(args.skos),
        Path(args.recommendations) if Path(args.recommendations).exists() else None
    )

    # Create output directory
    output_file = Path(args.output)
    output_file.parent.mkdir(parents=True, exist_ok=True)

    # Write SSSOM
    print("\nGenerating comprehensive SSSOM mapping...")
    generator.write_sssom(output_file)

    print("\n✓ Comprehensive SSSOM generation complete")
    return 0


if __name__ == '__main__':
    sys.exit(main())
