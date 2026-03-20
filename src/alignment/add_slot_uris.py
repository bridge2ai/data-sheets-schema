#!/usr/bin/env python3
"""
Add slot_uri definitions to D4D schema based on recommendations.

Processes:
1. High confidence recommendations (schema.org, dcat, prov)
2. Medium confidence recommendations
3. Novel D4D concepts (d4d: namespace)
"""

import csv
import re
from pathlib import Path
from typing import Dict, List

class SlotURIAdder:
    """Add slot_uri definitions to D4D schema files."""

    def __init__(
        self,
        recommendations_file: Path,
        novel_concepts_file: Path,
        schema_dir: Path
    ):
        self.recommendations_file = recommendations_file
        self.novel_concepts_file = novel_concepts_file
        self.schema_dir = schema_dir

        # Load recommendations
        self.high_conf = self._load_recommendations('high')
        self.medium_conf = self._load_recommendations('medium')
        self.novel = self._load_novel_concepts()

    def _load_recommendations(self, confidence: str) -> List[Dict]:
        """Load recommendations by confidence level."""
        recommendations = []

        with open(self.recommendations_file) as f:
            reader = csv.DictReader(f, delimiter='\t')
            for row in reader:
                if row['confidence'] == confidence:
                    recommendations.append({
                        'attribute': row['attribute'],
                        'uri': row['suggested_uri'],
                        'description': row['description']
                    })

        return recommendations

    def _load_novel_concepts(self) -> List[Dict]:
        """Load novel D4D concepts."""
        concepts = []

        with open(self.novel_concepts_file) as f:
            reader = csv.DictReader(f, delimiter='\t')
            for row in reader:
                concepts.append({
                    'attribute': row['attribute'],
                    'uri': f"d4d:{row['attribute']}",
                    'description': row['description']
                })

        return concepts

    def find_attribute_in_schema(self, attr_name: str) -> List[Path]:
        """Find which schema files contain an attribute."""
        found_in = []

        for schema_file in self.schema_dir.glob('D4D_*.yaml'):
            with open(schema_file) as f:
                content = f.read()
                # Look for attribute definition
                if re.search(rf'^\s+{attr_name}:\s*$', content, re.MULTILINE):
                    found_in.append(schema_file)

        return found_in

    def add_slot_uri_to_file(self, schema_file: Path, attr_name: str, slot_uri: str) -> bool:
        """Add slot_uri to an attribute in a schema file."""

        with open(schema_file) as f:
            lines = f.readlines()

        # Find the attribute
        attr_line_idx = None
        indent_level = None

        for i, line in enumerate(lines):
            if re.match(rf'^(\s+){attr_name}:\s*$', line):
                attr_line_idx = i
                indent_level = len(re.match(r'^(\s+)', line).group(1))
                break

        if attr_line_idx is None:
            return False

        # Check if slot_uri already exists
        for j in range(attr_line_idx + 1, min(attr_line_idx + 20, len(lines))):
            line = lines[j]

            # Stop if we hit another attribute at the same level
            if line.strip() and not line.startswith(' ' * (indent_level + 2)):
                break

            if 'slot_uri:' in line:
                print(f"  ⚠ {attr_name} already has slot_uri in {schema_file.name}")
                return False

        # Find where to insert slot_uri (after attribute name, before description or other properties)
        insert_idx = attr_line_idx + 1

        # Skip to after description if it exists
        for j in range(attr_line_idx + 1, min(attr_line_idx + 10, len(lines))):
            line = lines[j]

            if line.strip().startswith('description:'):
                # Skip multiline description
                k = j + 1
                while k < len(lines) and (lines[k].startswith(' ' * (indent_level + 4)) or lines[k].strip() == ''):
                    k += 1
                insert_idx = k
                break
            elif line.strip() and not line.startswith(' ' * (indent_level + 2)):
                # Hit another property at same level
                insert_idx = j
                break

        # Insert slot_uri
        slot_uri_line = ' ' * (indent_level + 2) + f'slot_uri: {slot_uri}\n'
        lines.insert(insert_idx, slot_uri_line)

        # Write back
        with open(schema_file, 'w') as f:
            f.writelines(lines)

        return True

    def add_all_slot_uris(self):
        """Add all recommended slot_uri definitions."""

        print("="*80)
        print("Adding slot_uri definitions to D4D schema")
        print("="*80)

        # Priority 1: High confidence
        print(f"\n=== Priority 1: High Confidence ({len(self.high_conf)} attributes) ===\n")
        added_count = 0

        for rec in self.high_conf:
            attr = rec['attribute']
            uri = rec['uri']

            # Find where this attribute is defined
            found_in = self.find_attribute_in_schema(attr)

            if not found_in:
                print(f"  ⚠ {attr} not found in any schema file")
                continue

            for schema_file in found_in:
                if self.add_slot_uri_to_file(schema_file, attr, uri):
                    print(f"  ✓ Added {attr}: {uri} to {schema_file.name}")
                    added_count += 1

        print(f"\n  Total added: {added_count}")

        # Priority 2: Medium confidence
        print(f"\n=== Priority 2: Medium Confidence ({len(self.medium_conf)} attributes) ===\n")
        added_count = 0

        for rec in self.medium_conf:
            attr = rec['attribute']
            uri = rec['uri']

            found_in = self.find_attribute_in_schema(attr)

            if not found_in:
                print(f"  ⚠ {attr} not found in any schema file")
                continue

            for schema_file in found_in:
                if self.add_slot_uri_to_file(schema_file, attr, uri):
                    print(f"  ✓ Added {attr}: {uri} to {schema_file.name}")
                    added_count += 1

        print(f"\n  Total added: {added_count}")

        # Novel D4D concepts
        print(f"\n=== Novel D4D Concepts ({len(self.novel)} attributes) ===\n")
        added_count = 0

        for concept in self.novel:
            attr = concept['attribute']
            uri = concept['uri']

            found_in = self.find_attribute_in_schema(attr)

            if not found_in:
                print(f"  ⚠ {attr} not found in any schema file")
                continue

            for schema_file in found_in:
                if self.add_slot_uri_to_file(schema_file, attr, uri):
                    print(f"  ✓ Added {attr}: {uri} to {schema_file.name}")
                    added_count += 1

        print(f"\n  Total added: {added_count}")

        print("\n" + "="*80)
        print("✓ slot_uri addition complete")
        print("="*80)


def main():
    """Main entry point."""

    recommendations_file = Path('notes/D4D_MISSING_URI_RECOMMENDATIONS.tsv')
    novel_concepts_file = Path('notes/D4D_NOVEL_CONCEPTS.tsv')
    schema_dir = Path('src/data_sheets_schema/schema')

    adder = SlotURIAdder(recommendations_file, novel_concepts_file, schema_dir)
    adder.add_all_slot_uris()


if __name__ == '__main__':
    main()
