#!/usr/bin/env python3
"""
Analyze description quality and coverage across D4D schema modules.

Generates metrics on:
- Description presence/absence
- Description length statistics
- Common quality issues (stub text, formatting)
- Consistency patterns
"""

import yaml
import re
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Any
import json


def load_yaml_file(filepath: Path) -> Dict[str, Any]:
    """Load YAML file."""
    with open(filepath) as f:
        return yaml.safe_load(f)


def analyze_description(desc: str, context: str) -> Dict[str, Any]:
    """Analyze a single description for quality metrics."""
    if not desc:
        return {
            'present': False,
            'length': 0,
            'issues': ['missing'],
            'quality_score': 0
        }

    issues = []
    quality_score = 100  # Start at 100, deduct for issues

    # Check length
    length = len(desc.strip())
    word_count = len(desc.split())

    # Issue detection
    if length < 20:
        issues.append('too_short')
        quality_score -= 30
    elif length < 50:
        issues.append('brief')
        quality_score -= 10

    if length > 500:
        issues.append('very_long')
        quality_score -= 5

    # Check for stub/placeholder text
    stub_patterns = [
        r'^\s*[Tt]odo\s*:',
        r'^\s*[Tt][Bb][Dd]\s*',
        r'^\s*[Ff][Ii][Xx][Mm][Ee]\s*',
        r'description',
        r'placeholder'
    ]

    desc_lower = desc.lower()
    for pattern in stub_patterns:
        if re.search(pattern, desc_lower):
            issues.append('stub_text')
            quality_score -= 40
            break

    # Check for proper sentence structure
    if not desc.strip().endswith(('.', ')', '!', '?')):
        issues.append('no_period')
        quality_score -= 5

    # Check capitalization
    if desc and not desc[0].isupper():
        issues.append('not_capitalized')
        quality_score -= 5

    # Check for examples
    has_examples = bool(re.search(r'\(e\.g\.,|\(for example,|Examples?:', desc))

    # Check for formatting issues
    if '\n\n\n' in desc:
        issues.append('excessive_newlines')
        quality_score -= 5

    # Check for question marks (good for question-based fields)
    has_question = '?' in desc

    return {
        'present': True,
        'length': length,
        'word_count': word_count,
        'has_examples': has_examples,
        'has_question': has_question,
        'issues': issues,
        'quality_score': max(0, quality_score)
    }


def analyze_module(filepath: Path) -> Dict[str, Any]:
    """Analyze description quality in a single module."""
    data = load_yaml_file(filepath)
    module_name = filepath.stem

    results = {
        'module': module_name,
        'module_description': None,
        'classes': {},
        'slots': {},
        'enums': {},
        'stats': defaultdict(int)
    }

    # Analyze module-level description
    if 'description' in data:
        results['module_description'] = analyze_description(
            data.get('description', ''),
            f"{module_name} (module)"
        )

    # Analyze classes
    classes = data.get('classes', {})
    for class_name, class_data in classes.items():
        class_desc = class_data.get('description', '')
        results['classes'][class_name] = {
            'description': analyze_description(class_desc, f"{module_name}.{class_name}"),
            'attributes': {}
        }

        # Analyze attributes/slots within class
        attributes = class_data.get('attributes', {})
        for attr_name, attr_data in attributes.items():
            if isinstance(attr_data, dict):
                attr_desc = attr_data.get('description', '')
                results['classes'][class_name]['attributes'][attr_name] = analyze_description(
                    attr_desc,
                    f"{module_name}.{class_name}.{attr_name}"
                )

    # Analyze top-level slots
    slots = data.get('slots', {})
    for slot_name, slot_data in slots.items():
        if isinstance(slot_data, dict):
            slot_desc = slot_data.get('description', '')
            results['slots'][slot_name] = analyze_description(
                slot_desc,
                f"{module_name}.slots.{slot_name}"
            )

    # Analyze enums
    enums = data.get('enums', {})
    for enum_name, enum_data in enums.items():
        enum_desc = enum_data.get('description', '')
        results['enums'][enum_name] = {
            'description': analyze_description(enum_desc, f"{module_name}.{enum_name}"),
            'values': {}
        }

        # Analyze enum values
        pv = enum_data.get('permissible_values', {})
        for value_name, value_data in pv.items():
            if isinstance(value_data, dict):
                value_desc = value_data.get('description', '')
                results['enums'][enum_name]['values'][value_name] = analyze_description(
                    value_desc,
                    f"{module_name}.{enum_name}.{value_name}"
                )

    # Calculate stats
    def count_stats(items: Dict):
        for item_data in items.values():
            if isinstance(item_data, dict):
                desc_analysis = item_data if 'present' in item_data else item_data.get('description', {})
                if desc_analysis:
                    if desc_analysis.get('present'):
                        results['stats']['total_descriptions'] += 1
                        results['stats']['total_length'] += desc_analysis.get('length', 0)
                        results['stats']['total_words'] += desc_analysis.get('word_count', 0)

                        if desc_analysis.get('has_examples'):
                            results['stats']['with_examples'] += 1

                        for issue in desc_analysis.get('issues', []):
                            results['stats'][f'issue_{issue}'] += 1

                        score = desc_analysis.get('quality_score', 0)
                        if score >= 90:
                            results['stats']['quality_excellent'] += 1
                        elif score >= 70:
                            results['stats']['quality_good'] += 1
                        elif score >= 50:
                            results['stats']['quality_fair'] += 1
                        else:
                            results['stats']['quality_poor'] += 1
                    else:
                        results['stats']['missing_descriptions'] += 1

                # Recurse for nested structures
                if 'attributes' in item_data:
                    count_stats(item_data['attributes'])
                if 'values' in item_data:
                    count_stats(item_data['values'])

    if results['module_description']:
        count_stats({'module': results['module_description']})

    count_stats(results['classes'])
    count_stats(results['slots'])
    count_stats(results['enums'])

    return results


def generate_report(all_results: List[Dict[str, Any]]) -> str:
    """Generate markdown report from analysis results."""

    report = ["# D4D Schema Description Quality Report\n"]
    report.append(f"**Generated:** 2026-04-08\n")
    report.append("---\n\n")

    # Executive Summary
    report.append("## Executive Summary\n\n")

    total_stats = defaultdict(int)
    for module_results in all_results:
        for key, value in module_results['stats'].items():
            total_stats[key] += value

    total_items = total_stats['total_descriptions'] + total_stats['missing_descriptions']
    coverage_pct = (total_stats['total_descriptions'] / total_items * 100) if total_items > 0 else 0

    report.append(f"**Total schema elements:** {total_items}\n")
    report.append(f"**Elements with descriptions:** {total_stats['total_descriptions']} ({coverage_pct:.1f}%)\n")
    report.append(f"**Missing descriptions:** {total_stats['missing_descriptions']}\n\n")

    if total_stats['total_descriptions'] > 0:
        avg_length = total_stats['total_length'] / total_stats['total_descriptions']
        avg_words = total_stats['total_words'] / total_stats['total_descriptions']
        report.append(f"**Average description length:** {avg_length:.0f} characters, {avg_words:.1f} words\n")

        examples_pct = (total_stats['with_examples'] / total_stats['total_descriptions'] * 100)
        report.append(f"**Descriptions with examples:** {total_stats['with_examples']} ({examples_pct:.1f}%)\n\n")

    # Quality Distribution
    report.append("### Quality Distribution\n\n")
    report.append(f"- **Excellent (90-100):** {total_stats['quality_excellent']}\n")
    report.append(f"- **Good (70-89):** {total_stats['quality_good']}\n")
    report.append(f"- **Fair (50-69):** {total_stats['quality_fair']}\n")
    report.append(f"- **Poor (<50):** {total_stats['quality_poor']}\n\n")

    # Common Issues
    report.append("### Common Issues\n\n")
    issue_counts = {k.replace('issue_', ''): v for k, v in total_stats.items() if k.startswith('issue_')}
    if issue_counts:
        sorted_issues = sorted(issue_counts.items(), key=lambda x: x[1], reverse=True)
        for issue, count in sorted_issues:
            pct = (count / total_stats['total_descriptions'] * 100) if total_stats['total_descriptions'] > 0 else 0
            report.append(f"- **{issue.replace('_', ' ').title()}:** {count} ({pct:.1f}%)\n")
    report.append("\n---\n\n")

    # Per-Module Analysis
    report.append("## Per-Module Analysis\n\n")

    for module_results in sorted(all_results, key=lambda x: x['module']):
        module_name = module_results['module']
        stats = module_results['stats']

        report.append(f"### {module_name}\n\n")

        module_total = stats.get('total_descriptions', 0) + stats.get('missing_descriptions', 0)
        if module_total > 0:
            module_coverage = (stats.get('total_descriptions', 0) / module_total * 100)
            report.append(f"**Coverage:** {stats.get('total_descriptions', 0)}/{module_total} ({module_coverage:.1f}%)\n")

        if stats.get('total_descriptions', 0) > 0:
            avg_len = stats.get('total_length', 0) / stats['total_descriptions']
            report.append(f"**Avg length:** {avg_len:.0f} chars\n")

        report.append(f"**Quality:** Excellent: {stats.get('quality_excellent', 0)}, ")
        report.append(f"Good: {stats.get('quality_good', 0)}, ")
        report.append(f"Fair: {stats.get('quality_fair', 0)}, ")
        report.append(f"Poor: {stats.get('quality_poor', 0)}\n")

        # Top issues for this module
        module_issues = {k.replace('issue_', ''): v for k, v in stats.items() if k.startswith('issue_') and v > 0}
        if module_issues:
            sorted_mod_issues = sorted(module_issues.items(), key=lambda x: x[1], reverse=True)[:3]
            report.append(f"**Top issues:** {', '.join([f'{issue} ({count})' for issue, count in sorted_mod_issues])}\n")

        report.append("\n")

    report.append("---\n\n")

    # Recommendations
    report.append("## Recommendations\n\n")

    if total_stats['missing_descriptions'] > 0:
        report.append(f"1. **Add missing descriptions:** {total_stats['missing_descriptions']} elements lack descriptions\n")

    if total_stats.get('issue_too_short', 0) > 10:
        report.append(f"2. **Expand brief descriptions:** {total_stats['issue_too_short']} descriptions under 20 characters\n")

    if total_stats.get('issue_stub_text', 0) > 0:
        report.append(f"3. **Remove stub/placeholder text:** {total_stats['issue_stub_text']} descriptions contain TODO/TBD/placeholders\n")

    if total_stats['quality_poor'] > 0:
        report.append(f"4. **Improve low-quality descriptions:** {total_stats['quality_poor']} descriptions scored <50\n")

    examples_pct = (total_stats['with_examples'] / total_stats['total_descriptions'] * 100) if total_stats['total_descriptions'] > 0 else 0
    if examples_pct < 30:
        report.append(f"5. **Add more examples:** Only {examples_pct:.1f}% of descriptions include examples\n")

    report.append("\n")

    return "".join(report)


def main():
    """Main execution."""
    schema_dir = Path("src/data_sheets_schema/schema")

    # Find all D4D module files
    module_files = sorted(schema_dir.glob("D4D_*.yaml"))

    # Also include main schema
    main_schema = schema_dir / "data_sheets_schema.yaml"
    if main_schema.exists():
        module_files.insert(0, main_schema)

    all_results = []

    print("Analyzing D4D schema modules...")
    for filepath in module_files:
        print(f"  - {filepath.name}")
        results = analyze_module(filepath)
        all_results.append(results)

    # Generate reports
    reports_dir = Path("reports")
    reports_dir.mkdir(exist_ok=True)

    # Markdown report
    markdown_report = generate_report(all_results)
    md_path = reports_dir / "description_quality_report.md"
    with open(md_path, 'w') as f:
        f.write(markdown_report)
    print(f"\nMarkdown report: {md_path}")

    # JSON detailed data
    json_path = reports_dir / "description_quality_data.json"
    with open(json_path, 'w') as f:
        json.dump(all_results, f, indent=2)
    print(f"JSON data: {json_path}")

    print("\nDone!")


if __name__ == "__main__":
    main()
