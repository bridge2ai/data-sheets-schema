#!/usr/bin/env python3
"""
Analyze actual values in D4D data files to validate schema range types.

Examines D4D YAML files for the four Bridge2AI projects to see:
- What values are present in boolean fields (are they truly boolean?)
- What values are in string fields (should they be enums?)
- Whether single-valued fields contain list-like data
- What types of values are actually used
"""

import yaml
import json
import argparse
from pathlib import Path
from collections import defaultdict
from typing import Any, Dict, List, Set

def load_d4d_file(file_path: Path) -> dict:
    """Load a D4D YAML data file."""
    with open(file_path, 'r') as f:
        return yaml.safe_load(f)

def extract_field_values(data: Any, prefix: str = '') -> Dict[str, Set]:
    """
    Recursively extract all field values from D4D data.

    Returns dict mapping field_path to set of values seen.
    """
    field_values = defaultdict(set)

    if isinstance(data, dict):
        for key, value in data.items():
            field_path = f"{prefix}.{key}" if prefix else key

            if value is None:
                field_values[field_path].add(None)
            elif isinstance(value, (str, int, float, bool)):
                field_values[field_path].add(value)
            elif isinstance(value, list):
                # For lists, record that it's multivalued and extract item values
                field_values[field_path].add(f"__LIST__({len(value)} items)")
                for item in value:
                    if isinstance(item, (str, int, float, bool)):
                        field_values[f"{field_path}[item]"].add(item)
                    elif isinstance(item, dict):
                        sub_values = extract_field_values(item, field_path + "[item]")
                        for sub_key, sub_vals in sub_values.items():
                            field_values[sub_key].update(sub_vals)
            elif isinstance(value, dict):
                sub_values = extract_field_values(value, field_path)
                for sub_key, sub_vals in sub_values.items():
                    field_values[sub_key].update(sub_vals)

    elif isinstance(data, list):
        for item in data:
            sub_values = extract_field_values(item, prefix)
            for sub_key, sub_vals in sub_values.items():
                field_values[sub_key].update(sub_vals)

    return field_values

def analyze_field_type(values: Set) -> dict:
    """
    Analyze the type of values in a field.

    Returns dict with:
    - inferred_type: str
    - is_boolean: bool
    - could_be_enum: bool (if limited value set)
    - is_multivalued: bool
    - value_count: int
    - sample_values: list
    """
    # Filter out None and __LIST__ markers
    real_values = {v for v in values if v is not None and not str(v).startswith('__LIST__')}
    list_markers = {v for v in values if str(v).startswith('__LIST__')}

    value_count = len(real_values)
    is_multivalued = len(list_markers) > 0

    # Infer type
    if not real_values:
        inferred_type = 'unknown'
        is_boolean = False
        could_be_enum = False
    else:
        types = {type(v).__name__ for v in real_values}

        if len(types) == 1:
            inferred_type = list(types)[0]
        else:
            inferred_type = 'mixed'

        # Check if boolean
        is_boolean = (inferred_type == 'bool' or
                      (inferred_type == 'str' and
                       real_values.issubset({'true', 'false', 'True', 'False', 'yes', 'no'})))

        # Check if could be enum (limited value set)
        could_be_enum = (inferred_type in ['str', 'bool'] and
                          1 < value_count <= 20)  # Arbitrary threshold

    return {
        'inferred_type': inferred_type,
        'is_boolean': is_boolean,
        'could_be_enum': could_be_enum,
        'is_multivalued': is_multivalued,
        'value_count': value_count,
        'sample_values': sorted(list(real_values))[:10]
    }

def analyze_d4d_files(data_dir: Path, projects: List[str]) -> Dict[str, dict]:
    """
    Analyze D4D data files for multiple projects.

    Returns dict mapping field_path to analysis results.
    """
    all_field_values = defaultdict(set)

    # Find and analyze D4D files
    for project in projects:
        # Use claudecode_agent method (recommended)
        d4d_file = data_dir / 'claudecode_agent' / f'{project}_d4d.yaml'

        if not d4d_file.exists():
            print(f"Warning: {d4d_file} not found, skipping")
            continue

        print(f"Analyzing: {d4d_file}")
        data = load_d4d_file(d4d_file)
        field_values = extract_field_values(data)

        # Merge with all values
        for field, values in field_values.items():
            all_field_values[field].update(values)

    # Analyze each field
    field_analyses = {}
    for field, values in all_field_values.items():
        field_analyses[field] = analyze_field_type(values)

    return field_analyses

def identify_issues(field_analyses: Dict[str, dict]) -> List[dict]:
    """
    Identify potential schema issues based on actual data values.

    Returns list of issues found.
    """
    issues = []

    for field_path, analysis in field_analyses.items():
        # Skip internal/list item paths
        if '[item]' in field_path:
            continue

        # Issue: Boolean field but multiple distinct string values
        if analysis['inferred_type'] == 'str' and not analysis['is_boolean']:
            if field_path.endswith(('is_', 'has_', 'was_', 'are_')) or 'boolean' in field_path.lower():
                issues.append({
                    'field': field_path,
                    'issue_type': 'boolean_field_has_non_boolean_values',
                    'severity': 'HIGH',
                    'description': f"Field name suggests boolean but contains {analysis['value_count']} string values",
                    'sample_values': analysis['sample_values']
                })

        # Issue: String field with limited value set (could be enum)
        if analysis['could_be_enum'] and not analysis['is_multivalued']:
            issues.append({
                'field': field_path,
                'issue_type': 'string_could_be_enum',
                'severity': 'MEDIUM',
                'description': f"String field with only {analysis['value_count']} distinct values (enum candidate)",
                'sample_values': analysis['sample_values']
            })

        # Issue: Multivalued field in data (check if schema allows)
        if analysis['is_multivalued']:
            issues.append({
                'field': field_path,
                'issue_type': 'multivalued_in_data',
                'severity': 'INFO',
                'description': "Field contains lists in data - verify schema has multivalued: true",
                'sample_values': [str(v) for v in list(analysis['sample_values'])[:5]]
            })

    return issues

def generate_report(field_analyses: Dict[str, dict], issues: List[dict], output_format: str = 'json') -> str:
    """Generate data value analysis report."""
    report = {
        'metadata': {
            'tool': 'data_value_analyzer',
            'total_fields': len(field_analyses),
            'total_issues': len(issues)
        },
        'summary': {
            'fields_analyzed': len(field_analyses),
            'boolean_fields': sum(1 for a in field_analyses.values() if a['is_boolean']),
            'enum_candidates': sum(1 for a in field_analyses.values() if a['could_be_enum']),
            'multivalued_fields': sum(1 for a in field_analyses.values() if a['is_multivalued'])
        },
        'issues': issues,
        'field_analyses': {
            k: v for k, v in sorted(field_analyses.items())
        }
    }

    if output_format == 'json':
        return json.dumps(report, indent=2)
    else:
        # Text format
        lines = []
        lines.append("=" * 80)
        lines.append("D4D DATA VALUE ANALYSIS REPORT")
        lines.append("=" * 80)
        lines.append("")
        lines.append(f"Fields analyzed: {len(field_analyses)}")
        lines.append(f"Issues found: {len(issues)}")
        lines.append("")

        # Group issues by type
        issues_by_type = defaultdict(list)
        for issue in issues:
            issues_by_type[issue['issue_type']].append(issue)

        for issue_type, type_issues in sorted(issues_by_type.items()):
            lines.append(f"\n{issue_type.upper().replace('_', ' ')} ({len(type_issues)} occurrences):")
            lines.append("-" * 80)
            for issue in type_issues[:10]:  # Limit to 10 per type
                lines.append(f"\n  {issue['field']}")
                lines.append(f"    {issue['description']}")
                if issue['sample_values']:
                    vals_preview = ', '.join([str(v)[:30] for v in issue['sample_values'][:5]])
                    lines.append(f"    Sample values: {vals_preview}")

        lines.append("")
        lines.append("=" * 80)
        return "\n".join(lines)

def main():
    parser = argparse.ArgumentParser(
        description='Analyze actual values in D4D data files'
    )
    parser.add_argument(
        '--data-dir',
        type=Path,
        default=Path('data/d4d_concatenated'),
        help='Directory containing D4D data files'
    )
    parser.add_argument(
        '--projects',
        nargs='+',
        default=['AI_READI', 'CHORUS', 'CM4AI', 'VOICE'],
        help='Projects to analyze'
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

    # Analyze D4D files
    field_analyses = analyze_d4d_files(args.data_dir, args.projects)

    # Identify issues
    issues = identify_issues(field_analyses)

    # Generate report
    report = generate_report(field_analyses, issues, args.format)

    # Output
    if args.output:
        args.output.write_text(report)
        print(f"\nReport written to: {args.output}")
    else:
        print(report)

    return 0

if __name__ == '__main__':
    exit(main())
