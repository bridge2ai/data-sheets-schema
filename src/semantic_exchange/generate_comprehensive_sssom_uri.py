#!/usr/bin/env python3
"""
Generate comprehensive URI-level SSSOM for ALL D4D slots.

Shows, for every slot name in the schema, the slot_uri the schema declares
(``d4d_slot_uri_current``) and the target the comprehensive table resolves
for it (``d4d_slot_uri_recommended``).

The target comes from the same resolver as ``generate_comprehensive_sssom.py``
(#2935): SKOS alignment TTL, then the schema's slot_uri and ``*_mappings``,
then the URI recommendations, then the keyword heuristics. Both tables
therefore agree on every slot's status, predicate and target. The current
slot_uri is read from every declaration of the slot, not only top-level
``slots:``, so a slot_uri set on a class attribute counts.
"""

import csv
import io
import sys
from datetime import date
from pathlib import Path
from typing import Dict, List, Optional

# Import the comprehensive generator for the shared resolution
sys.path.insert(0, str(Path(__file__).parent))
from generate_comprehensive_sssom import (  # noqa: E402
    ComprehensiveSSSOMGenerator, add_common_arguments, committed_date,
    mapping_tool, report_drift, sssom_object_id,
)

#: The slot_uri-flavoured comment for each (status, source).
URI_COMMENTS = {
    ('mapped', 'ttl'): 'Has SKOS alignment to RO-Crate vocabulary',
    # #2972: the heuristic's guess, not a curated target, so no URI is named
    ('novel_d4d', 'heuristic'): ('Keyword heuristic: probably a novel D4D '
                                 'concept - a d4d: slot_uri would serve; '
                                 'not curated'),
    ('free_text', 'heuristic'): 'Free text/narrative field - no slot_uri needed',
    ('unmapped', 'none'): 'Unmapped - needs vocabulary research for slot_uri',
}


class ComprehensiveURISSSOMGenerator:
    """Generate comprehensive URI-level SSSOM for all D4D slots."""

    FIELDNAMES = [
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
        'mapping_source',
        'other_curated_mappings',
        'heuristic_hint',
        'needs_slot_uri',
        'vocab_crosswalk',
        'author_id',
        'mapping_tool',
        'mapping_date',
        'mapping_set_id',
        'mapping_set_version'
    ]

    def __init__(
        self,
        d4d_schema: Path,
        skos_file: Path,
        recommendations_file: Optional[Path]
    ):
        self.d4d_schema = d4d_schema
        self.skos_file = skos_file
        self.recommendations_file = recommendations_file

        # One resolution for both tables
        self.comp_gen = ComprehensiveSSSOMGenerator(
            d4d_schema, skos_file, recommendations_file
        )

    def _comment(self, res) -> str:
        if res.status == 'mapped' and res.source == 'schema':
            base = f'Declared in the schema ({res.origin})'
        elif res.status == 'recommended':
            rec = self.comp_gen.recommendations.get(res.slot, {})
            base = f"Recommended slot_uri (confidence: {rec.get('confidence', 'unknown')})"
        else:
            base = URI_COMMENTS[(res.status, res.source)]
            if res.status == 'mapped' and res.origin != f'd4d:{res.slot}':
                base += f' ({res.origin})'
        return '; '.join([base] + res.notes)

    def generate_comprehensive_uri_sssom(self, mapping_date: Optional[str] = None
                                         ) -> List[Dict]:
        """Generate URI-level SSSOM for all slots."""
        mapping_date = mapping_date or date.today().isoformat()
        rows = []

        for slot, res in self.comp_gen.resolutions.items():
            current_slot_uri = self.comp_gen.declared_slot_uri(slot)
            target_uri = res.object
            rows.append({
                'd4d_slot_name': slot,
                'd4d_slot_uri_current': current_slot_uri,
                'subject_source': self._get_vocab_source(current_slot_uri),
                'predicate_id': res.predicate,
                'd4d_slot_uri_recommended': target_uri,
                'object_id': sssom_object_id(res),
                'object_label': target_uri.split(':', 1)[1] if ':' in target_uri else target_uri,
                'object_source': self._get_vocab_source(target_uri),
                'confidence': res.confidence,
                'mapping_justification': res.justification,
                'comment': self._comment(res),
                'mapping_status': res.status,
                'mapping_source': res.source,
                'other_curated_mappings': ' | '.join(res.others),
                'heuristic_hint': res.hint,
                'needs_slot_uri': 'yes' if not current_slot_uri and res.status in ['recommended', 'novel_d4d'] else 'no',
                'vocab_crosswalk': self._is_vocab_crosswalk(current_slot_uri, target_uri),
                # #2971: no person on any row (MAPPING_TOOL in generate_comprehensive_sssom.py)
                'author_id': '',
                'mapping_tool': mapping_tool(res),
                'mapping_date': mapping_date,
                'mapping_set_id': 'd4d-rocrate-uri-comprehensive-v1',
                'mapping_set_version': '2.0',
            })

        return rows

    def _get_vocab_source(self, uri: str) -> str:
        """Namespace IRI of a CURIE, as the comprehensive table resolves it."""
        return self.comp_gen._get_vocab_source(uri)

    def _is_vocab_crosswalk(self, current_uri: str, target_uri: str) -> str:
        """Check if mapping requires vocabulary crosswalk."""
        if not current_uri or not target_uri:
            return 'N/A'

        current_ns = current_uri.split(':')[0] if ':' in current_uri else ''
        target_ns = target_uri.split(':')[0] if ':' in target_uri else ''

        return 'true' if current_ns != target_ns else 'false'

    @staticmethod
    def _summary(rows: List[Dict]) -> Dict:
        status_counts: Dict[str, int] = {}
        for row in rows:
            status_counts[row['mapping_status']] = status_counts.get(row['mapping_status'], 0) + 1
        return {
            'status_counts': dict(sorted(status_counts.items())),
            'has_uri': sum(1 for r in rows if r['d4d_slot_uri_current']),
            'needs_uri': sum(1 for r in rows if r['needs_slot_uri'] == 'yes'),
        }

    def render_sssom(self, mapping_date: Optional[str] = None) -> str:
        """The comprehensive URI-level SSSOM TSV, as the file holds it."""
        mapping_date = mapping_date or date.today().isoformat()
        rows = self.generate_comprehensive_uri_sssom(mapping_date)
        s = self._summary(rows)
        n = len(rows)

        out = io.StringIO()
        out.write('# Comprehensive URI-level SSSOM - ALL D4D Slots\n')
        out.write('# Shows the declared and the resolved slot_uri for every schema '
                  'slot name (same resolution as d4d_rocrate_sssom_comprehensive.tsv)\n')
        out.write(f'# Date: {mapping_date}\n')
        out.write(f'# Total attributes: {n}\n')
        out.write('#\n')
        out.write('# Status breakdown:\n')
        for status, count in s['status_counts'].items():
            out.write(f'#   {status}: {count}\n')
        out.write('#\n')
        out.write(f"# Current slot_uri coverage: {s['has_uri']}/{n} ({s['has_uri']/n*100:.1f}%)\n")
        out.write(f"# Attributes needing slot_uri: {s['needs_uri']}/{n} ({s['needs_uri']/n*100:.1f}%)\n")
        out.write('#\n')
        writer = csv.DictWriter(out, fieldnames=self.FIELDNAMES,
                                delimiter='\t', lineterminator='\n')
        writer.writeheader()
        writer.writerows(rows)
        return out.getvalue()

    def write_sssom(self, output_file: Path, mapping_date: Optional[str] = None):
        """Write comprehensive URI-level SSSOM."""
        mapping_date = mapping_date or date.today().isoformat()
        with open(output_file, 'w', encoding='utf-8', newline='') as f:
            f.write(self.render_sssom(mapping_date))

        rows = self.generate_comprehensive_uri_sssom(mapping_date)
        s = self._summary(rows)
        n = len(rows)
        print(f"✓ Wrote {n} comprehensive URI mappings to {output_file}")
        print("\nStatus breakdown:")
        for status, count in s['status_counts'].items():
            print(f"  {status}: {count}")
        print(f"\nCurrent slot_uri coverage: {s['has_uri']}/{n} ({s['has_uri']/n*100:.1f}%)")
        print(f"Attributes needing slot_uri: {s['needs_uri']}/{n} ({s['needs_uri']/n*100:.1f}%)")


def main(argv=None):
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description='Generate comprehensive URI-level SSSOM for ALL D4D slots'
    )
    add_common_arguments(
        parser,
        'src/data_sheets_schema/semantic_exchange/d4d_rocrate_sssom_uri_comprehensive.tsv')
    args = parser.parse_args(argv)

    recommendations = Path(args.recommendations)
    generator = ComprehensiveURISSSOMGenerator(
        Path(args.schema),
        Path(args.skos),
        recommendations if recommendations.exists() else None
    )
    for warning in generator.comp_gen.warnings():
        print(f"WARNING: {warning}", file=sys.stderr)

    output_file = Path(args.output)
    if args.check:
        pinned = committed_date(output_file) if output_file.exists() else args.date
        return report_drift(output_file, generator.render_sssom(pinned),
                            'd4d_slot_name')

    output_file.parent.mkdir(parents=True, exist_ok=True)
    print("\nGenerating comprehensive URI-level SSSOM mapping...")
    generator.write_sssom(output_file, args.date)

    print("\n✓ Comprehensive URI-level SSSOM generation complete")
    return 0


if __name__ == '__main__':
    sys.exit(main())
