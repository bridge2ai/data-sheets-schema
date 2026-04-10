#!/usr/bin/env python3
"""
Check alignment between description semantics and range types in D4D schema.

Detects cases where:
- Boolean is used where richer types (enum, string, structured) are needed
- Description implies list but multivalued is false
- Description implies structured data but uses primitive type
"""

import yaml
import json
import argparse
import re
from pathlib import Path
from typing import Dict, List, Tuple

def load_schema_module(file_path: Path) -> dict:
    """Load a YAML schema module."""
    with open(file_path, 'r') as f:
        return yaml.safe_load(f)

def analyze_description(description: str) -> dict:
    """
    Analyze description to infer semantic intent.

    Returns dict with:
    - implies_list: bool
    - implies_structured: bool
    - implies_choices: bool
    - implied_type: str
    """
    if not description:
        return {
            'implies_list': False,
            'implies_structured': False,
            'implies_choices': False,
            'implied_type': 'unknown'
        }

    desc_lower = description.lower()

    # Check for list indicators
    list_indicators = [
        'list of', 'multiple', 'array of', 'collection of',
        'one or more', 'set of', '(e.g.,', 'and/or'
    ]
    implies_list = any(ind in desc_lower for ind in list_indicators)

    # Check for structured data indicators
    structured_indicators = [
        'details of', 'information about', 'structured',
        'metadata', 'properties of'
    ]
    implies_structured = any(ind in desc_lower for ind in structured_indicators)

    # Check for choice indicators (should use enum)
    choice_indicators = [
        'whether', 'if', 'type of', 'which', 'one of',
        '(e.g.,', 'such as'
    ]
    implies_choices = any(ind in desc_lower for ind in choice_indicators)

    # Infer implied type
    if 'url' in desc_lower or 'link' in desc_lower or 'http' in desc_lower:
        implied_type = 'uri'
    elif 'date' in desc_lower and 'time' not in desc_lower:
        implied_type = 'date'
    elif 'date' in desc_lower and 'time' in desc_lower:
        implied_type = 'datetime'
    elif implies_choices and not implies_list:
        implied_type = 'enum'
    elif implies_structured:
        implied_type = 'class'
    else:
        implied_type = 'string'

    return {
        'implies_list': implies_list,
        'implies_structured': implies_structured,
        'implies_choices': implies_choices,
        'implied_type': implied_type
    }

def check_range_mismatch(attr_def: dict, attr_name: str) -> Tuple[bool, str]:
    """
    Check if range type matches description semantics.

    Returns (is_mismatch, reason)
    """
    description = attr_def.get('description', '')
    range_type = attr_def.get('range', 'string')
    multivalued = attr_def.get('multivalued', False)

    if not description:
        return False, ''

    analysis = analyze_description(description)

    # Check for boolean reductionism
    if range_type == 'boolean' and (analysis['implies_structured'] or
                                     analysis['implied_type'] not in ['boolean', 'unknown']):
        return True, f"Boolean oversimplifies - description implies {analysis['implied_type']}"

    # Check for missing multivalued
    if analysis['implies_list'] and not multivalued:
        return True, "Description implies list but multivalued=false"

    # Check for primitive type when structured needed
    if analysis['implies_structured'] and range_type in ['string', 'boolean', 'integer', 'float']:
        return True, f"Primitive type '{range_type}' used but description implies structured class"

    # Check for string when enum appropriate
    if (analysis['implies_choices'] and
        range_type == 'string' and
        not multivalued and
        '?' not in description):  # Questions are okay as strings
        return True, "String used but description implies enum (limited choices)"

    # Check for URI field without uri range
    if analysis['implied_type'] == 'uri' and range_type not in ['uri', 'uriorcurie', 'string']:
        return True, f"Description implies URI but range is {range_type}"

    return False, ''

def check_module(module_path: Path) -> List[dict]:
    """Check all attributes in a module for range mismatches."""
    issues = []
    module_name = module_path.stem
    module_data = load_schema_module(module_path)

    # Check classes and their attributes
    classes = module_data.get('classes', {})
    for class_name, class_def in classes.items():
        if not class_def:
            continue

        attributes = class_def.get('attributes', {})
        for attr_name, attr_def in attributes.items():
            if not attr_def:
                continue

            is_mismatch, reason = check_range_mismatch(attr_def, attr_name)

            if is_mismatch:
                issues.append({
                    'module': module_name,
                    'file': module_path.name,
                    'class': class_name,
                    'attribute': attr_name,
                    'description': attr_def.get('description', ''),
                    'range': attr_def.get('range', 'string'),
                    'multivalued': attr_def.get('multivalued', False),
                    'issue': reason,
                    'severity': categorize_severity(reason)
                })

    # Check top-level slots
    slots = module_data.get('slots', {})
    for slot_name, slot_def in slots.items():
        if not slot_def:
            continue

        is_mismatch, reason = check_range_mismatch(slot_def, slot_name)

        if is_mismatch:
            issues.append({
                'module': module_name,
                'file': module_path.name,
                'class': None,
                'attribute': slot_name,
                'description': slot_def.get('description', ''),
                'range': slot_def.get('range', 'string'),
                'multivalued': slot_def.get('multivalued', False),
                'issue': reason,
                'severity': categorize_severity(reason)
            })

    return issues

def categorize_severity(issue_reason: str) -> str:
    """Categorize issue severity based on reason."""
    if 'boolean oversimplifies' in issue_reason.lower():
        return 'HIGH'
    elif 'implies list but' in issue_reason.lower():
        return 'HIGH'
    elif 'implies structured' in issue_reason.lower():
        return 'MEDIUM'
    elif 'implies enum' in issue_reason.lower():
        return 'MEDIUM'
    else:
        return 'LOW'

def generate_report(all_issues: List[dict], output_format: str = 'json') -> str:
    """Generate report of range mismatches."""
    # Group by severity
    by_severity = {}
    for issue in all_issues:
        severity = issue['severity']
        if severity not in by_severity:
            by_severity[severity] = []
        by_severity[severity].append(issue)

    report = {
        'metadata': {
            'tool': 'range_description_checker',
            'total_issues': len(all_issues)
        },
        'summary': {
            severity: len(issues)
            for severity, issues in by_severity.items()
        },
        'issues': all_issues
    }

    if output_format == 'json':
        return json.dumps(report, indent=2)
    else:
        # Text format
        lines = []
        lines.append("=" * 80)
        lines.append("RANGE-DESCRIPTION MISMATCH REPORT")
        lines.append("=" * 80)
        lines.append("")
        lines.append(f"Total issues found: {len(all_issues)}")
        lines.append("")
        for severity in ['HIGH', 'MEDIUM', 'LOW']:
            if severity in by_severity:
                lines.append(f"\n{severity} PRIORITY ({len(by_severity[severity])} issues):")
                lines.append("-" * 80)
                for issue in by_severity[severity]:
                    location = f"{issue['module']}::{issue['class'] or 'slots'}::{issue['attribute']}"
                    lines.append(f"\n  {location}")
                    lines.append(f"    Range: {issue['range']}, Multivalued: {issue['multivalued']}")
                    lines.append(f"    Issue: {issue['issue']}")
                    desc_preview = issue['description'][:70]
                    lines.append(f"    Description: \"{desc_preview}...\"")

        lines.append("")
        lines.append("=" * 80)
        return "\n".join(lines)

def main():
    parser = argparse.ArgumentParser(
        description='Check range-description alignment in D4D schema'
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

    # Check all modules
    all_issues = []
    for module_path in sorted(args.schema_dir.glob('D4D_*.yaml')):
        if module_path.name == 'D4D_Evaluation_Summary.yaml':
            continue

        issues = check_module(module_path)
        all_issues.extend(issues)

    # Generate report
    report = generate_report(all_issues, args.format)

    # Output
    if args.output:
        args.output.write_text(report)
        print(f"Report written to: {args.output}")
    else:
        print(report)

    # Exit with error code if issues found
    return 1 if all_issues else 0

if __name__ == '__main__':
    exit(main())
