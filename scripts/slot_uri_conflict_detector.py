#!/usr/bin/env python3
"""
Detect slot_uri conflicts in D4D schema modules.

Identifies when multiple slots map to the same ontology term with different semantics,
which can cause RDF serialization issues and semantic ambiguity.
"""

import yaml
import json
import argparse
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Tuple

def load_schema_module(file_path: Path) -> dict:
    """Load a YAML schema module."""
    with open(file_path, 'r') as f:
        return yaml.safe_load(f)

def extract_slot_uris(module_data: dict, module_name: str) -> List[Tuple[str, str, str, int]]:
    """
    Extract all slot_uri declarations from a module.

    Returns list of (slot_uri, slot_name, description, line_number) tuples.
    """
    slot_uris = []

    # Check classes and their attributes
    classes = module_data.get('classes', {})
    for class_name, class_def in classes.items():
        if not class_def:
            continue

        attributes = class_def.get('attributes', {})
        for attr_name, attr_def in attributes.items():
            if not attr_def:
                continue

            slot_uri = attr_def.get('slot_uri')
            if slot_uri:
                description = attr_def.get('description', '')
                # Line number would require parsing with ruamel.yaml, so we use 0 for now
                slot_uris.append((slot_uri, attr_name, description, 0))

    # Check top-level slots
    slots = module_data.get('slots', {})
    for slot_name, slot_def in slots.items():
        if not slot_def:
            continue

        slot_uri = slot_def.get('slot_uri')
        if slot_uri:
            description = slot_def.get('description', '')
            slot_uris.append((slot_uri, slot_name, description, 0))

    return slot_uris

def find_conflicts(modules_dir: Path) -> Dict[str, List[dict]]:
    """
    Find all slot_uri conflicts across D4D modules.

    Returns dict mapping slot_uri to list of conflicting usages.
    """
    # Map slot_uri to list of (slot_name, module, description) tuples
    uri_map = defaultdict(list)

    # Process all D4D modules
    for module_path in sorted(modules_dir.glob('D4D_*.yaml')):
        if module_path.name == 'D4D_Evaluation_Summary.yaml':
            continue  # Skip evaluation summary schema

        module_name = module_path.stem
        module_data = load_schema_module(module_path)

        slot_uris = extract_slot_uris(module_data, module_name)

        for slot_uri, slot_name, description, line_num in slot_uris:
            uri_map[slot_uri].append({
                'slot_name': slot_name,
                'module': module_name,
                'file': str(module_path.name),
                'description': description,
                'line': line_num
            })

    # Find conflicts (same slot_uri with different slot names)
    conflicts = {}
    for slot_uri, usages in uri_map.items():
        # Group by slot name
        unique_names = set(u['slot_name'] for u in usages)

        if len(unique_names) > 1:
            conflicts[slot_uri] = usages

    return conflicts

def analyze_conflict_severity(slot_uri: str, usages: List[dict]) -> str:
    """
    Analyze conflict severity based on semantic similarity of descriptions.

    Returns: CRITICAL, HIGH, MEDIUM, or LOW
    """
    descriptions = [u['description'].lower() for u in usages if u['description']]

    # If descriptions are very different, it's critical
    # Simple heuristic: check for overlapping keywords
    if len(descriptions) < 2:
        return "HIGH"  # Missing descriptions make it hard to assess

    # Check for semantic similarity (simple keyword overlap)
    words1 = set(descriptions[0].split())
    words2 = set(descriptions[1].split())
    overlap = len(words1 & words2) / len(words1 | words2) if (words1 | words2) else 0

    if overlap < 0.2:
        return "CRITICAL"  # Very different semantics
    elif overlap < 0.4:
        return "HIGH"  # Somewhat different semantics
    elif overlap < 0.6:
        return "MEDIUM"  # Some overlap
    else:
        return "LOW"  # Very similar (might be intentional)

def assess_impact(slot_uri: str, usages: List[dict]) -> dict:
    """Assess the impact of a slot_uri conflict."""
    return {
        'data_corruption_risk': 'low',  # slot_uri changes don't affect data
        'tool_breakage_risk': 'high',  # RDF converters may fail
        'semantic_integrity': 'critical',  # Ambiguous meaning
        'migration_complexity': 'low'  # Just schema changes
    }

def recommend_fix(slot_uri: str, usages: List[dict]) -> dict:
    """Recommend how to fix the conflict."""
    # Analyze which usage seems most aligned with the ontology term
    # For now, provide generic recommendation

    recommendations = []
    for i, usage in enumerate(usages):
        if i == 0:
            # Suggest keeping the first one
            recommendations.append({
                'slot': usage['slot_name'],
                'action': 'keep',
                'new_slot_uri': slot_uri,
                'rationale': 'Appears to match ontology term semantics'
            })
        else:
            # Suggest changing others
            recommendations.append({
                'slot': usage['slot_name'],
                'action': 'change',
                'new_slot_uri': f"d4d:{usage['slot_name']}",
                'rationale': 'Create custom D4D term to avoid conflict'
            })

    return {
        'approach': 'differentiate_mappings',
        'recommendations': recommendations
    }

def generate_report(conflicts: Dict[str, List[dict]], output_format: str = 'json') -> str:
    """Generate conflict report in specified format."""

    report = {
        'metadata': {
            'tool': 'slot_uri_conflict_detector',
            'total_conflicts': len(conflicts)
        },
        'conflicts': []
    }

    for slot_uri, usages in sorted(conflicts.items()):
        severity = analyze_conflict_severity(slot_uri, usages)
        impact = assess_impact(slot_uri, usages)
        fix = recommend_fix(slot_uri, usages)

        conflict_entry = {
            'slot_uri': slot_uri,
            'severity': severity,
            'conflict_count': len(set(u['slot_name'] for u in usages)),
            'usages': usages,
            'impact': impact,
            'recommended_fix': fix
        }

        report['conflicts'].append(conflict_entry)

    if output_format == 'json':
        return json.dumps(report, indent=2)
    else:
        # Text format
        lines = []
        lines.append("=" * 80)
        lines.append("SLOT_URI CONFLICT DETECTION REPORT")
        lines.append("=" * 80)
        lines.append("")
        lines.append(f"Total conflicts found: {len(conflicts)}")
        lines.append("")

        for conflict in sorted(report['conflicts'], key=lambda c: c['severity']):
            lines.append(f"\n[{conflict['severity']}] slot_uri: {conflict['slot_uri']}")
            lines.append(f"  Conflict: {conflict['conflict_count']} different slot names use this URI")
            lines.append(f"  Usages:")
            for usage in conflict['usages']:
                lines.append(f"    - {usage['slot_name']} ({usage['module']})")
                if usage['description']:
                    desc_preview = usage['description'][:60]
                    lines.append(f"      '{desc_preview}...'")
            lines.append(f"  Recommended fix: {conflict['recommended_fix']['approach']}")

        lines.append("")
        lines.append("=" * 80)
        return "\n".join(lines)

def main():
    parser = argparse.ArgumentParser(
        description='Detect slot_uri conflicts in D4D schema modules'
    )
    parser.add_argument(
        '--schema-dir',
        type=Path,
        default=Path('src/data_sheets_schema/schema'),
        help='Directory containing schema modules'
    )
    parser.add_argument(
        '--output',
        type=Path,
        help='Output file path (default: stdout)'
    )
    parser.add_argument(
        '--format',
        choices=['json', 'text'],
        default='json',
        help='Output format'
    )

    args = parser.parse_args()

    # Find conflicts
    conflicts = find_conflicts(args.schema_dir)

    # Generate report
    report = generate_report(conflicts, args.format)

    # Output
    if args.output:
        args.output.write_text(report)
        print(f"Report written to: {args.output}")
    else:
        print(report)

    # Exit with error code if conflicts found
    return 1 if conflicts else 0

if __name__ == '__main__':
    exit(main())
