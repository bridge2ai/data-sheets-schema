#!/usr/bin/env python3
"""
Check quality of descriptions in D4D schema module files.

Analyzes descriptions against style guide criteria and generates
a prioritized report of quality issues with specific recommendations.
"""

import yaml
import json
import argparse
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Tuple, Optional

# Quality thresholds from style guide
BREVITY_THRESHOLD = 5  # words
TARGET_WITH_EXAMPLES = {
    'attribute': 0.40,  # 40% of attributes should have examples
    'slot': 0.20,       # 20% of slots should have examples
}

def count_words(text: str) -> int:
    """Count words in a description."""
    if not text:
        return 0
    return len(text.split())

def has_example(text: str) -> bool:
    """Check if description contains an example."""
    if not text:
        return False
    indicators = ['e.g.', 'for example', '(e.g.,', 'such as']
    text_lower = text.lower()
    return any(indicator in text_lower for indicator in indicators) or '(' in text

def is_complete_sentence(text: str) -> bool:
    """Check if text appears to be a complete sentence."""
    if not text:
        return False
    # Must end with period, question mark, or be very short (enum values)
    return text.rstrip().endswith(('.', '?', '!')) or count_words(text) <= 5

def check_description_quality(description: str, element_type: str, element_name: str) -> List[str]:
    """
    Check description quality against style guide criteria.

    Returns list of issue codes:
    - TOO_BRIEF: Less than 5 words
    - MISSING_PERIOD: Attributes/slots should end with period
    - CONSIDER_EXAMPLE: Attributes should have examples
    """
    issues = []

    if not description:
        return ['MISSING']  # Shouldn't happen, but check anyway

    word_count = count_words(description)

    # Check brevity (applies to all types)
    if word_count < BREVITY_THRESHOLD:
        issues.append('TOO_BRIEF')

    # Check complete sentence for attributes and slots
    if element_type in ['attribute', 'slot']:
        if not is_complete_sentence(description):
            # Check if it ends with period
            if not description.rstrip().endswith('.'):
                issues.append('MISSING_PERIOD')

    # Check for examples in attributes
    if element_type == 'attribute':
        if not has_example(description):
            # Only suggest example if description is substantial enough
            if word_count >= BREVITY_THRESHOLD:
                issues.append('CONSIDER_EXAMPLE')

    return issues

def analyze_module(module_path: Path) -> Dict:
    """Analyze a single module for description quality."""
    with open(module_path, 'r') as f:
        data = yaml.safe_load(f)

    module_name = module_path.stem
    results = {
        'module': module_name,
        'issues': [],
        'stats': defaultdict(int),
        'quality_metrics': {}
    }

    # Track elements for metrics
    elements_by_type = defaultdict(list)

    # Check module-level description
    if data.get('description'):
        elements_by_type['module'].append({
            'name': 'module',
            'description': data['description'],
            'line': 1
        })

    # Check classes
    classes = data.get('classes', {})
    for class_name, class_def in classes.items():
        if not class_def:
            continue

        desc = class_def.get('description', '')
        elements_by_type['class'].append({
            'name': class_name,
            'description': desc,
            'line': None
        })

        issues = check_description_quality(desc, 'class', class_name)
        for issue in issues:
            results['issues'].append({
                'type': issue,
                'element_type': 'class',
                'element_name': class_name,
                'location': f"{module_name}::classes::{class_name}",
                'description': desc,
                'priority': 'HIGH' if issue == 'TOO_BRIEF' else 'MEDIUM'
            })

        # Check attributes
        attributes = class_def.get('attributes', {})
        for attr_name, attr_def in attributes.items():
            if not attr_def:
                continue

            desc = attr_def.get('description', '')
            elements_by_type['attribute'].append({
                'name': attr_name,
                'description': desc,
                'line': None
            })

            issues = check_description_quality(desc, 'attribute', attr_name)
            for issue in issues:
                results['issues'].append({
                    'type': issue,
                    'element_type': 'attribute',
                    'element_name': f"{class_name}.{attr_name}",
                    'location': f"{module_name}::classes::{class_name}::attributes::{attr_name}",
                    'description': desc,
                    'priority': 'HIGH' if issue == 'TOO_BRIEF' else 'LOW'
                })

    # Check slots
    slots = data.get('slots', {})
    for slot_name, slot_def in slots.items():
        if not slot_def:
            continue

        desc = slot_def.get('description', '')
        elements_by_type['slot'].append({
            'name': slot_name,
            'description': desc,
            'line': None
        })

        issues = check_description_quality(desc, 'slot', slot_name)
        for issue in issues:
            results['issues'].append({
                'type': issue,
                'element_type': 'slot',
                'element_name': slot_name,
                'location': f"{module_name}::slots::{slot_name}",
                'description': desc,
                'priority': 'HIGH' if issue == 'TOO_BRIEF' else 'MEDIUM'
            })

    # Check enums
    enums = data.get('enums', {})
    for enum_name, enum_def in enums.items():
        if not enum_def:
            continue

        desc = enum_def.get('description', '')
        elements_by_type['enum'].append({
            'name': enum_name,
            'description': desc,
            'line': None
        })

        issues = check_description_quality(desc, 'enum', enum_name)
        for issue in issues:
            results['issues'].append({
                'type': issue,
                'element_type': 'enum',
                'element_name': enum_name,
                'location': f"{module_name}::enums::{enum_name}",
                'description': desc,
                'priority': 'MEDIUM'
            })

        # Check permissible values
        permissible_values = enum_def.get('permissible_values', {})
        for pv_name, pv_def in permissible_values.items():
            if not pv_def:
                continue

            desc = pv_def.get('description', '')
            elements_by_type['enum_value'].append({
                'name': pv_name,
                'description': desc,
                'line': None
            })

            issues = check_description_quality(desc, 'enum_value', pv_name)
            # Enum values can be brief, so only flag severe issues
            for issue in issues:
                if issue == 'TOO_BRIEF' and count_words(desc) <= 2:
                    results['issues'].append({
                        'type': issue,
                        'element_type': 'enum_value',
                        'element_name': f"{enum_name}.{pv_name}",
                        'location': f"{module_name}::enums::{enum_name}::permissible_values::{pv_name}",
                        'description': desc,
                        'priority': 'LOW'
                    })

    # Calculate quality metrics
    for elem_type, elements in elements_by_type.items():
        total = len(elements)
        if total == 0:
            continue

        with_examples = sum(1 for e in elements if has_example(e['description']))
        complete_sentences = sum(1 for e in elements if is_complete_sentence(e['description']))
        brief = sum(1 for e in elements if count_words(e['description']) < BREVITY_THRESHOLD)

        results['quality_metrics'][elem_type] = {
            'total': total,
            'with_examples': with_examples,
            'with_examples_pct': (with_examples / total * 100) if total > 0 else 0,
            'complete_sentences': complete_sentences,
            'complete_sentences_pct': (complete_sentences / total * 100) if total > 0 else 0,
            'too_brief': brief,
            'too_brief_pct': (brief / total * 100) if total > 0 else 0,
        }

    return results

def generate_report(all_results: List[Dict], output_format: str = 'text') -> str:
    """Generate quality report in specified format."""

    # Aggregate statistics
    total_issues = sum(len(r['issues']) for r in all_results)
    issues_by_type = defaultdict(int)
    issues_by_priority = defaultdict(int)

    for result in all_results:
        for issue in result['issues']:
            issues_by_type[issue['type']] += 1
            issues_by_priority[issue['priority']] += 1

    if output_format == 'json':
        return json.dumps({
            'summary': {
                'total_issues': total_issues,
                'by_type': dict(issues_by_type),
                'by_priority': dict(issues_by_priority)
            },
            'modules': all_results
        }, indent=2)

    # Text format
    lines = []
    lines.append("=" * 80)
    lines.append("D4D SCHEMA DESCRIPTION QUALITY REPORT")
    lines.append("=" * 80)
    lines.append("")

    # Summary
    lines.append("SUMMARY")
    lines.append("-" * 80)
    lines.append(f"Total issues found: {total_issues}")
    lines.append("")

    lines.append("By Issue Type:")
    for issue_type in sorted(issues_by_type.keys()):
        count = issues_by_type[issue_type]
        lines.append(f"  {issue_type}: {count}")
    lines.append("")

    lines.append("By Priority:")
    for priority in ['HIGH', 'MEDIUM', 'LOW']:
        count = issues_by_priority.get(priority, 0)
        lines.append(f"  {priority}: {count}")
    lines.append("")

    # Quality metrics by module
    lines.append("QUALITY METRICS BY MODULE")
    lines.append("-" * 80)
    for result in all_results:
        lines.append(f"\n{result['module']}:")
        for elem_type, metrics in result.get('quality_metrics', {}).items():
            lines.append(f"  {elem_type}:")
            lines.append(f"    Total: {metrics['total']}")
            lines.append(f"    Complete sentences: {metrics['complete_sentences']} ({metrics['complete_sentences_pct']:.1f}%)")
            lines.append(f"    With examples: {metrics['with_examples']} ({metrics['with_examples_pct']:.1f}%)")
            lines.append(f"    Too brief: {metrics['too_brief']} ({metrics['too_brief_pct']:.1f}%)")
    lines.append("")

    # Detailed issues by priority
    lines.append("DETAILED ISSUES")
    lines.append("-" * 80)

    for priority in ['HIGH', 'MEDIUM', 'LOW']:
        priority_issues = []
        for result in all_results:
            priority_issues.extend([i for i in result['issues'] if i['priority'] == priority])

        if priority_issues:
            lines.append(f"\n{priority} PRIORITY ({len(priority_issues)} issues):")
            lines.append("-" * 80)

            # Group by type
            by_type = defaultdict(list)
            for issue in priority_issues:
                by_type[issue['type']].append(issue)

            for issue_type, issues in sorted(by_type.items()):
                lines.append(f"\n  {issue_type} ({len(issues)} occurrences):")
                for issue in issues[:10]:  # Limit to first 10 per type
                    lines.append(f"    • {issue['location']}")
                    if issue.get('description'):
                        desc_preview = issue['description'][:60]
                        if len(issue['description']) > 60:
                            desc_preview += "..."
                        lines.append(f"      Current: \"{desc_preview}\"")
                if len(issues) > 10:
                    lines.append(f"    ... and {len(issues) - 10} more")

    lines.append("")
    lines.append("=" * 80)

    return "\n".join(lines)

def main():
    parser = argparse.ArgumentParser(description='Check D4D schema description quality')
    parser.add_argument('--report', help='Output report to JSON file')
    parser.add_argument('--format', choices=['text', 'json'], default='text',
                        help='Output format (default: text)')
    args = parser.parse_args()

    schema_dir = Path('src/data_sheets_schema/schema')
    d4d_modules = sorted(schema_dir.glob('D4D_*.yaml'))

    all_results = []
    for module_path in d4d_modules:
        results = analyze_module(module_path)
        all_results.append(results)

    # Generate report
    report = generate_report(all_results, output_format=args.format)

    # Output report
    if args.report:
        with open(args.report, 'w') as f:
            f.write(report)
        print(f"Report saved to: {args.report}")
    else:
        print(report)

    # Exit with error code if high-priority issues found
    high_priority_count = sum(
        len([i for i in r['issues'] if i['priority'] == 'HIGH'])
        for r in all_results
    )

    return 0 if high_priority_count == 0 else 1

if __name__ == '__main__':
    exit(main())
