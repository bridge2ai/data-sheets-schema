#!/usr/bin/env python3
"""
Generate comprehensive URI-level SSSOM for ALL D4D attributes.

Shows current and recommended slot_uri for every D4D attribute:
- Attributes with slot_uri (33)
- Recommended slot_uri (97)
- Novel D4D concepts needing d4d: URIs (42)
- Free text fields (no URI needed) (54)
- Unmapped (needs research) (38)
"""

import csv
import sys
import yaml
from pathlib import Path
from typing import Dict, List
from datetime import datetime

# Import the comprehensive generator for categorization logic
sys.path.insert(0, str(Path(__file__).parent))
from generate_comprehensive_sssom import ComprehensiveSSSOMGenerator


class ComprehensiveURISSSOMGenerator:
    """Generate comprehensive URI-level SSSOM for all D4D attributes."""

    def __init__(
        self,
        d4d_schema: Path,
        skos_file: Path,
        recommendations_file: Path
    ):
        self.d4d_schema = d4d_schema
        self.skos_file = skos_file
        self.recommendations_file = recommendations_file

        # Load D4D schema
        with open(d4d_schema) as f:
            schema = yaml.safe_load(f)

        self.base_slots = schema.get('slots', {})

        # Use comprehensive generator for categorization
        self.comp_gen = ComprehensiveSSSOMGenerator(
            d4d_schema, skos_file, recommendations_file
        )

    def generate_comprehensive_uri_sssom(self) -> List[Dict]:
        """Generate URI-level SSSOM for all attributes."""
        rows = []

        for attr_name, attr_info in sorted(self.comp_gen.d4d_attributes.items()):
            # Get current slot_uri if exists
            current_slot_uri = ''
            if attr_name in self.base_slots:
                current_slot_uri = self.base_slots[attr_name].get('slot_uri', '')

            # Get category and recommended mapping
            category = self.comp_gen._categorize_attribute(attr_name, attr_info)

            # Build URI mapping row
            row = {
                'd4d_slot_name': attr_name,
                'd4d_slot_uri_current': current_slot_uri,
                'subject_source': self._get_vocab_source(current_slot_uri) if current_slot_uri else '',
            }

            # Determine recommended/target URI based on category
            if category == 'mapped':
                # Has SKOS mapping
                mapping = self.comp_gen.skos_mappings[attr_name]
                target_uri = mapping['rocrate_uri']
                predicate = f"skos:{mapping['predicate']}"
                confidence = self._get_confidence(mapping['predicate'])
                status = 'mapped'
                comment = 'Has SKOS alignment to RO-Crate vocabulary'

            elif category == 'recommended':
                # Has recommendation
                rec = self.comp_gen.recommendations.get(attr_name, {})
                target_uri = rec.get('suggested_uri', '')
                predicate = 'skos:closeMatch' if target_uri else 'semapv:UnmappedProperty'
                confidence = 0.7 if rec.get('confidence') == 'high' else 0.5
                status = 'recommended'
                comment = f"Recommended slot_uri (confidence: {rec.get('confidence', 'unknown')})"

            elif category == 'novel_d4d':
                # Novel D4D - should use d4d: namespace
                target_uri = f"d4d:{attr_name}"
                predicate = 'skos:exactMatch'
                confidence = 1.0
                status = 'novel_d4d'
                comment = 'Novel D4D concept - should use d4d: namespace'

            elif category == 'free_text':
                # Free text - no URI needed
                target_uri = ''
                predicate = 'semapv:UnmappableProperty'
                confidence = 0.0
                status = 'free_text'
                comment = 'Free text/narrative field - no slot_uri needed'

            else:
                # Unmapped
                target_uri = ''
                predicate = 'semapv:UnmappedProperty'
                confidence = 0.0
                status = 'unmapped'
                comment = 'Unmapped - needs vocabulary research for slot_uri'

            # Add common fields
            row.update({
                'predicate_id': predicate,
                'd4d_slot_uri_recommended': target_uri,
                'object_id': target_uri,
                'object_label': target_uri.split(':')[1] if ':' in target_uri else target_uri,
                'object_source': self._get_vocab_source(target_uri) if target_uri else '',
                'confidence': confidence,
                'mapping_justification': self._get_justification(status),
                'comment': comment,
                'mapping_status': status,
                'author_id': 'https://orcid.org/0000-0000-0000-0000',
                'mapping_date': datetime.now().strftime('%Y-%m-%d'),
                'mapping_set_id': 'd4d-rocrate-uri-comprehensive-v1',
                'mapping_set_version': '1.0',
                'needs_slot_uri': 'yes' if not current_slot_uri and status in ['recommended', 'novel_d4d'] else 'no',
                'vocab_crosswalk': self._is_vocab_crosswalk(current_slot_uri, target_uri)
            })

            rows.append(row)

        return rows

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

    def _get_justification(self, status: str) -> str:
        """Get mapping justification based on status."""
        justifications = {
            'mapped': 'semapv:ManualMappingCuration',
            'recommended': 'semapv:SuggestedMapping',
            'novel_d4d': 'semapv:ManualMappingCuration',
            'free_text': 'semapv:FreeTextProperty',
            'unmapped': 'semapv:RequiresResearch'
        }
        return justifications.get(status, 'semapv:UnspecifiedMatching')

    def _is_vocab_crosswalk(self, current_uri: str, target_uri: str) -> str:
        """Check if mapping requires vocabulary crosswalk."""
        if not current_uri or not target_uri:
            return 'N/A'

        current_ns = current_uri.split(':')[0] if ':' in current_uri else ''
        target_ns = target_uri.split(':')[0] if ':' in target_uri else ''

        return 'true' if current_ns != target_ns else 'false'

    def write_sssom(self, output_file: Path):
        """Write comprehensive URI-level SSSOM."""
        rows = self.generate_comprehensive_uri_sssom()

        if not rows:
            print("No URI mappings to write")
            return

        # SSSOM header
        fieldnames = [
            'd4d_slot_name',
            'd4d_slot_uri_current',
            'subject_source',
            'predicate_id',
            'd4d_slot_uri_recommended',
            'object_id',
            'object_label',
            'object_source',
            'confidence',
            'mapping_justification',
            'comment',
            'mapping_status',
            'needs_slot_uri',
            'vocab_crosswalk',
            'author_id',
            'mapping_date',
            'mapping_set_id',
            'mapping_set_version'
        ]

        with open(output_file, 'w', newline='') as f:
            # Write SSSOM metadata
            f.write('# Comprehensive URI-level SSSOM - ALL D4D Attributes\n')
            f.write('# Shows current and recommended slot_uri for every attribute\n')
            f.write(f'# Date: {datetime.now().isoformat()}\n')
            f.write(f'# Total attributes: {len(rows)}\n')

            # Count by status
            status_counts = {}
            has_uri = 0
            needs_uri = 0

            for row in rows:
                status = row['mapping_status']
                status_counts[status] = status_counts.get(status, 0) + 1

                if row['d4d_slot_uri_current']:
                    has_uri += 1
                if row['needs_slot_uri'] == 'yes':
                    needs_uri += 1

            f.write(f'#\n')
            f.write('# Status breakdown:\n')
            for status, count in sorted(status_counts.items()):
                f.write(f'#   {status}: {count}\n')
            f.write(f'#\n')
            f.write(f'# Current slot_uri coverage: {has_uri}/{len(rows)} ({has_uri/len(rows)*100:.1f}%)\n')
            f.write(f'# Attributes needing slot_uri: {needs_uri}/{len(rows)} ({needs_uri/len(rows)*100:.1f}%)\n')
            f.write('#\n')

            writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter='\t')
            writer.writeheader()
            writer.writerows(rows)

        print(f"✓ Wrote {len(rows)} comprehensive URI mappings to {output_file}")
        print(f"\nStatus breakdown:")
        for status, count in sorted(status_counts.items()):
            print(f"  {status}: {count}")
        print(f"\nCurrent slot_uri coverage: {has_uri}/{len(rows)} ({has_uri/len(rows)*100:.1f}%)")
        print(f"Attributes needing slot_uri: {needs_uri}/{len(rows)} ({needs_uri/len(rows)*100:.1f}%)")


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description='Generate comprehensive URI-level SSSOM for ALL D4D attributes'
    )
    parser.add_argument(
        '--schema',
        default='src/data_sheets_schema/schema/data_sheets_schema_all.yaml',
        help='D4D schema file'
    )
    parser.add_argument(
        '--skos',
        default='src/data_sheets_schema/semantic_exchange/d4d_rocrate_skos_alignment.ttl',
        help='SKOS alignment file'
    )
    parser.add_argument(
        '--recommendations',
        default='notes/D4D_MISSING_URI_RECOMMENDATIONS.tsv',
        help='URI recommendations file'
    )
    parser.add_argument(
        '--output',
        default='src/data_sheets_schema/semantic_exchange/d4d_rocrate_sssom_uri_comprehensive.tsv',
        help='Output comprehensive URI SSSOM file'
    )

    args = parser.parse_args()

    # Generate comprehensive URI SSSOM
    generator = ComprehensiveURISSSOMGenerator(
        Path(args.schema),
        Path(args.skos),
        Path(args.recommendations)
    )

    # Create output directory
    output_file = Path(args.output)
    output_file.parent.mkdir(parents=True, exist_ok=True)

    # Write SSSOM
    print("\nGenerating comprehensive URI-level SSSOM mapping...")
    generator.write_sssom(output_file)

    print("\n✓ Comprehensive URI-level SSSOM generation complete")
    return 0


if __name__ == '__main__':
    sys.exit(main())
