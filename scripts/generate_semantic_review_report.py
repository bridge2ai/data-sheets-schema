#!/usr/bin/env python3
"""
Generate comprehensive semantic review report from all validation outputs.

Consolidates findings from:
- slot_uri conflict detector
- range-description checker
- data value analyzer
- (future) ontology mapping validator
- (future) semantic consistency analyzer
- (future) logical constraint validator
"""

import json
import argparse
from pathlib import Path
from collections import defaultdict
from datetime import datetime

def load_json_report(file_path: Path) -> dict:
    """Load a JSON report file."""
    if not file_path.exists():
        return {}
    with open(file_path, 'r') as f:
        return json.load(f)

def generate_executive_summary(reports: dict) -> str:
    """Generate executive summary section."""
    slot_uri = reports.get('slot_uri_conflicts', {})
    ranges = reports.get('range_mismatches', {})
    data_values = reports.get('data_value_analysis', {})

    total_issues = (
        slot_uri.get('metadata', {}).get('total_conflicts', 0) +
        ranges.get('metadata', {}).get('total_issues', 0) +
        data_values.get('metadata', {}).get('total_issues', 0)
    )

    # Count by severity
    critical = sum(1 for c in slot_uri.get('conflicts', []) if c.get('severity') == 'CRITICAL')
    high = (sum(1 for c in slot_uri.get('conflicts', []) if c.get('severity') == 'HIGH') +
            ranges.get('summary', {}).get('HIGH', 0))
    medium = (sum(1 for c in slot_uri.get('conflicts', []) if c.get('severity') == 'MEDIUM') +
              ranges.get('summary', {}).get('MEDIUM', 0))
    low = ranges.get('summary', {}).get('LOW', 0)

    lines = []
    lines.append("## Executive Summary\n")
    lines.append(f"**Total Issues Found:** {total_issues}\n")
    lines.append(f"- **CRITICAL:** {critical} (Blocks functionality)")
    lines.append(f"- **HIGH:** {high} (Wrong semantics)")
    lines.append(f"- **MEDIUM:** {medium} (Reduces clarity)")
    lines.append(f"- **LOW:** {low} (Documentation quality)\n")

    lines.append("### Key Findings\n")
    lines.append(f"1. **slot_uri Conflicts:** {slot_uri.get('metadata', {}).get('total_conflicts', 0)} conflicts detected")
    conflicts_list = slot_uri.get('conflicts', [])
    if conflicts_list:
        most_severe = max(conflicts_list, key=lambda c: c.get('conflict_count', 0))
        lines.append(f"   - Most severe: `{most_severe.get('slot_uri', 'N/A')}` used by {most_severe.get('conflict_count', '?')} slots")
        critical_uris = [c.get('slot_uri') for c in conflicts_list if c.get('severity') == 'CRITICAL']
        if critical_uris:
            lines.append(f"   - Critical URIs: {', '.join(f'`{u}`' for u in critical_uris[:5])}")
    lines.append("")

    lines.append(f"2. **Range-Description Mismatches:** {ranges.get('metadata', {}).get('total_issues', 0)} issues")
    lines.append(f"   - HIGH priority: {ranges.get('summary', {}).get('HIGH', 0)} (boolean oversimplification, missing multivalued)")
    lines.append(f"   - MEDIUM priority: {ranges.get('summary', {}).get('MEDIUM', 0)} (primitives vs structured types)\n")

    lines.append(f"3. **Data Value Analysis:** {data_values.get('metadata', {}).get('total_fields', 0)} fields analyzed across 4 Bridge2AI projects")
    lines.append(f"   - Enum candidates: {data_values.get('summary', {}).get('enum_candidates', 0)} string fields with limited value sets")
    lines.append(f"   - Multivalued fields: {data_values.get('summary', {}).get('multivalued_fields', 0)} fields containing lists in actual data\n")

    return '\n'.join(lines)

def generate_critical_issues_section(reports: dict) -> str:
    """Generate critical issues section."""
    lines = []
    lines.append("## Critical Issues (Must Fix)\n")

    slot_uri = reports.get('slot_uri_conflicts', {})
    critical_conflicts = [c for c in slot_uri.get('conflicts', []) if c.get('severity') == 'CRITICAL']

    for i, conflict in enumerate(critical_conflicts, 1):
        lines.append(f"### C-{i:03d}: slot_uri Conflict - {conflict['slot_uri']}\n")
        lines.append(f"**Severity:** CRITICAL")
        lines.append(f"**Conflict Count:** {conflict['conflict_count']} different slots")

        # Show usages
        lines.append(f"\n**Usages:**")
        for usage in conflict['usages']:
            lines.append(f"- `{usage['slot_name']}` in {usage['file']}")
            if usage['description']:
                lines.append(f"  - Description: \"{usage['description'][:80]}...\"")

        lines.append(f"\n**Impact:**")
        impact = conflict.get('impact', {})
        lines.append(f"- RDF Serialization: {impact.get('semantic_integrity', 'unknown')}")
        lines.append(f"- Tool Breakage Risk: {impact.get('tool_breakage_risk', 'unknown')}")

        lines.append(f"\n**Recommended Fix:**")
        fix = conflict.get('recommended_fix', {})
        if fix.get('recommendations'):
            for rec in fix['recommendations']:
                action = rec['action']
                if action == 'keep':
                    lines.append(f"- **KEEP** `{rec['slot']}` → `{rec['new_slot_uri']}` (correct usage)")
                else:
                    lines.append(f"- **CHANGE** `{rec['slot']}` → `{rec['new_slot_uri']}` (avoid conflict)")

        lines.append(f"\n**Rationale:** {get_rationale(conflict['slot_uri'])}\n")
        lines.append("")

    return '\n'.join(lines)

def get_rationale(slot_uri: str) -> str:
    """Get rationale for specific slot_uri conflicts."""
    rationales = {
        'dcat:mediaType': 'DCAT spec defines mediaType as MIME type (e.g., application/json), not character encoding',
        'dcterms:description': 'Overuse of generic description property loses semantic distinction between different types of descriptive text',
        'schema:identifier': 'Multiple slots represent different kinds of identifiers (DOI, ORCID, generic ID) - each should have specific mapping',
        'dcterms:license': 'License applies to different entities (dataset vs software) and should be differentiated',
    }
    for key in rationales:
        if key in slot_uri:
            return rationales[key]
    return 'Multiple semantic concepts mapped to same ontology term creates ambiguity'

def generate_high_priority_section(reports: dict) -> str:
    """Generate high priority issues section."""
    lines = []
    lines.append("## High Priority Issues (Wrong Semantics)\n")

    # slot_uri conflicts marked as HIGH
    slot_uri = reports.get('slot_uri_conflicts', {})
    high_conflicts = [c for c in slot_uri.get('conflicts', []) if c.get('severity') == 'HIGH']

    issue_num = 1
    for conflict in high_conflicts[:5]:  # Limit to top 5
        lines.append(f"### H-{issue_num:03d}: slot_uri Conflict - {conflict['slot_uri']}\n")
        lines.append(f"**Usages:** {', '.join([u['slot_name'] for u in conflict['usages']])}")
        lines.append(f"**Files:** {', '.join(set([u['file'] for u in conflict['usages']]))}\n")
        issue_num += 1

    # Range-description mismatches marked as HIGH
    ranges = reports.get('range_mismatches', {})
    high_range_issues = [i for i in ranges.get('issues', []) if i.get('severity') == 'HIGH']

    for issue in high_range_issues[:10]:  # Limit to top 10
        location = f"{issue['module']}::{issue['class'] or 'slots'}::{issue['attribute']}"
        lines.append(f"### H-{issue_num:03d}: Range Mismatch - {location}\n")
        lines.append(f"**Current Range:** `{issue['range']}` (multivalued: {issue['multivalued']})")
        lines.append(f"**Issue:** {issue['issue']}")
        lines.append(f"**Description:** \"{issue['description'][:100]}...\"\n")
        issue_num += 1

    return '\n'.join(lines)

def generate_data_insights_section(reports: dict) -> str:
    """Generate section based on actual data analysis."""
    lines = []
    lines.append("## Data-Driven Insights\n")
    lines.append("Analysis of actual D4D records for AI_READI, CHORUS, CM4AI, and VOICE projects:\n")

    data = reports.get('data_value_analysis', {})

    lines.append(f"### Enum Candidates\n")
    lines.append(f"Fields with limited value sets that could be enums:\n")

    enum_issues = [i for i in data.get('issues', []) if i['issue_type'] == 'string_could_be_enum']
    for issue in enum_issues[:15]:
        lines.append(f"- `{issue['field']}`: {issue['description']}")
        if issue['sample_values']:
            vals = ', '.join([f'"{v}"' for v in issue['sample_values'][:5]])
            lines.append(f"  - Values: {vals}")

    lines.append(f"\n### Multivalued Fields\n")
    lines.append(f"Fields that contain lists in actual data (verify schema has multivalued: true):\n")

    mv_issues = [i for i in data.get('issues', []) if i['issue_type'] == 'multivalued_in_data']
    for issue in mv_issues[:15]:
        lines.append(f"- `{issue['field']}`")

    return '\n'.join(lines)

def generate_markdown_report(reports: dict) -> str:
    """Generate complete markdown report."""
    lines = []
    lines.append("# D4D Schema Semantic Review Report\n")
    lines.append(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"**Review Scope:** All D4D schema modules + actual data from 4 Bridge2AI projects\n")
    lines.append("---\n")

    lines.append(generate_executive_summary(reports))
    lines.append("\n---\n")

    lines.append(generate_critical_issues_section(reports))
    lines.append("\n---\n")

    lines.append(generate_high_priority_section(reports))
    lines.append("\n---\n")

    lines.append(generate_data_insights_section(reports))
    lines.append("\n---\n")

    # Appendices
    lines.append("## Appendices\n")
    lines.append("### A: Files Requiring Changes\n")
    lines.append("Priority-ordered list of schema files needing updates:\n")
    lines.append("1. `src/data_sheets_schema/schema/D4D_Base_import.yaml` (CRITICAL - foundational)")
    lines.append("2. `src/data_sheets_schema/schema/D4D_Composition.yaml` (HIGH)")
    lines.append("3. `src/data_sheets_schema/schema/D4D_Data_Governance.yaml` (HIGH)")
    lines.append("4. `src/data_sheets_schema/schema/D4D_Distribution.yaml` (MEDIUM)")
    lines.append("5. `src/data_sheets_schema/schema/D4D_Maintenance.yaml` (MEDIUM)\n")

    lines.append("### B: Validation Tools\n")
    lines.append("Automated validation scripts created:\n")
    lines.append("- `scripts/slot_uri_conflict_detector.py` - Detects slot_uri conflicts")
    lines.append("- `scripts/range_description_checker.py` - Checks range-description alignment")
    lines.append("- `scripts/data_value_analyzer.py` - Analyzes actual data values\n")

    lines.append("### C: Next Steps\n")
    lines.append("1. Review and prioritize CRITICAL issues")
    lines.append("2. Create implementation plan for fixes")
    lines.append("3. Coordinate with tool maintainers for breaking changes")
    lines.append("4. Develop data migration strategy if needed")
    lines.append("5. Update documentation with rationale for changes\n")

    return '\n'.join(lines)

def main():
    parser = argparse.ArgumentParser(
        description='Generate comprehensive semantic review report'
    )
    parser.add_argument(
        'report_files',
        nargs='+',
        type=Path,
        help='Input JSON report files'
    )
    parser.add_argument(
        '--output',
        type=Path,
        default=Path('reports/semantic_review_report.md'),
        help='Output markdown file'
    )

    args = parser.parse_args()

    # Load all reports
    reports = {}
    for file_path in args.report_files:
        if 'slot_uri_conflicts' in str(file_path):
            reports['slot_uri_conflicts'] = load_json_report(file_path)
        elif 'range_mismatches' in str(file_path):
            reports['range_mismatches'] = load_json_report(file_path)
        elif 'data_value_analysis' in str(file_path):
            reports['data_value_analysis'] = load_json_report(file_path)

    # Generate markdown report
    markdown = generate_markdown_report(reports)

    # Write output
    args.output.write_text(markdown)
    print(f"Semantic review report written to: {args.output}")

    # Also generate JSON summary
    json_output = args.output.with_suffix('.json')
    summary = {
        'generated': datetime.now().isoformat(),
        'total_issues': (
            reports.get('slot_uri_conflicts', {}).get('metadata', {}).get('total_conflicts', 0) +
            reports.get('range_mismatches', {}).get('metadata', {}).get('total_issues', 0) +
            reports.get('data_value_analysis', {}).get('metadata', {}).get('total_issues', 0)
        ),
        'reports_analyzed': list(reports.keys())
    }
    with open(json_output, 'w') as f:
        json.dump(summary, f, indent=2)
    print(f"JSON summary written to: {json_output}")

    return 0

if __name__ == '__main__':
    exit(main())
