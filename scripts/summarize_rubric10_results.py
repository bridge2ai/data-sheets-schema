#!/usr/bin/env python3
"""
Summarize Rubric10 Evaluation Results

Processes rubric10 evaluation JSONs and creates summary tables and reports.

Usage:
    python scripts/summarize_rubric10_results.py

Output:
    - data/evaluation_llm/rubric10/all_scores.csv
    - data/evaluation_llm/rubric10/summary_report.md
    - data/evaluation_llm/rubric10/summary_table.md
"""

import json
import csv
from pathlib import Path
from typing import List, Dict
from datetime import datetime

# Base directory
BASE_DIR = Path(__file__).parent.parent
EVAL_DIR = BASE_DIR / "data" / "evaluation_llm" / "rubric10"


def load_evaluation_results() -> List[Dict]:
    """Load all rubric10 evaluation JSON files."""
    results = []

    # Individual evaluations
    individual_dir = EVAL_DIR / "individual"
    if individual_dir.exists():
        for json_file in individual_dir.glob("**/*_evaluation.json"):
            with open(json_file) as f:
                data = json.load(f)
                data['evaluation_type'] = 'individual'
                results.append(data)

    # Concatenated evaluations
    concat_dir = EVAL_DIR / "concatenated"
    if concat_dir.exists():
        for json_file in concat_dir.glob("*_evaluation.json"):
            with open(json_file) as f:
                data = json.load(f)
                data['evaluation_type'] = 'concatenated'
                results.append(data)

    return results


def create_csv_summary(results: List[Dict]):
    """Create CSV file with all scores."""

    csv_path = EVAL_DIR / "all_scores.csv"

    with open(csv_path, 'w', newline='') as f:
        writer = csv.writer(f)

        # Header
        writer.writerow([
            'project', 'method', 'type', 'file',
            'total_score', 'max_score', 'percentage',
            'elements_passing', 'element_scores'
        ])

        # Data rows
        for result in sorted(results, key=lambda x: (x.get('project', ''), x.get('type', ''), x.get('method', ''))):
            project = result.get('project', 'unknown')
            method = result.get('method', 'unknown')
            eval_type = result.get('evaluation_type', 'unknown')
            file_path = result.get('d4d_file', '')

            overall = result.get('overall_score', {})
            total_score = overall.get('total_points', 0)
            max_score = overall.get('max_points', 50)
            percentage = overall.get('percentage', 0)

            # Count elements passing (score >= 3/5)
            elements = result.get('elements', [])
            elements_passing = sum(1 for el in elements if el.get('element_score', 0) >= 3)

            # Element scores string
            element_scores_str = ','.join([
                f"{el['name'][:20]}:{el.get('element_score', 0)}/{el.get('element_max', 5)}"
                for el in elements[:10]  # Limit to 10 elements
            ])

            writer.writerow([
                project, method, eval_type, file_path,
                total_score, max_score, percentage,
                elements_passing, element_scores_str
            ])

    print(f"✅ CSV summary created: {csv_path}")
    print(f"   Total evaluations: {len(results)}")


def create_markdown_table(results: List[Dict]):
    """Create markdown summary table."""

    # Group by project and type
    table_data = {}
    for result in results:
        project = result.get('project', 'unknown')
        method = result.get('method', 'unknown')
        eval_type = result.get('evaluation_type', 'unknown')

        key = (project, eval_type, method)
        if key not in table_data:
            table_data[key] = []

        table_data[key].append(result)

    # Create markdown table
    md = f"""# Rubric10 Evaluation Summary

**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

**Total Evaluations:** {len(results)}

## Concatenated D4Ds

| Project | Method | Score | Percentage | Elements Passing | Top Element | Weakest Element |
|---------|--------|-------|------------|------------------|-------------|-----------------|
"""

    # Concatenated results
    for project in ['AI_READI', 'CHORUS', 'CM4AI', 'VOICE']:
        for method in ['curated', 'gpt5', 'claudecode', 'claudecode_agent', 'claudecode_assistant']:
            key = (project, 'concatenated', method)
            if key in table_data and table_data[key]:
                result = table_data[key][0]  # Should only be one per key
                overall = result.get('overall_score', {})
                total = overall.get('total_points', 0)
                max_pts = overall.get('max_points', 50)
                pct = overall.get('percentage', 0)

                elements = result.get('elements', [])
                elements_passing = sum(1 for el in elements if el.get('element_score', 0) >= 3)

                # Find top and weakest elements
                top_element = max(elements, key=lambda x: x.get('element_score', 0) / x.get('element_max', 1)) if elements else None
                weak_element = min(elements, key=lambda x: x.get('element_score', 0) / x.get('element_max', 1)) if elements else None

                top_name = f"{top_element['name'][:25]} ({top_element['element_score']}/{top_element['element_max']})" if top_element else "N/A"
                weak_name = f"{weak_element['name'][:25]} ({weak_element['element_score']}/{weak_element['element_max']})" if weak_element else "N/A"

                md += f"| {project} | {method} | {total}/{max_pts} | {pct:.1f}% | {elements_passing}/10 | {top_name} | {weak_name} |\n"

    # Individual results summary
    md += "\n## Individual D4Ds Summary\n\n"
    md += "| Project | Method | Avg Score | Files | Avg Percentage | Avg Elements Passing |\n"
    md += "|---------|--------|-----------|-------|----------------|----------------------|\n"

    for project in ['AI_READI', 'CHORUS', 'CM4AI', 'VOICE']:
        for method in ['gpt5', 'claudecode_agent', 'claudecode_assistant']:
            key = (project, 'individual', method)
            if key in table_data and table_data[key]:
                results_list = table_data[key]
                file_count = len(results_list)

                avg_score = sum(r.get('overall_score', {}).get('total_points', 0) for r in results_list) / file_count
                avg_pct = sum(r.get('overall_score', {}).get('percentage', 0) for r in results_list) / file_count

                avg_passing = sum(
                    sum(1 for el in r.get('elements', []) if el.get('element_score', 0) >= 3)
                    for r in results_list
                ) / file_count

                md += f"| {project} | {method} | {avg_score:.1f}/50 | {file_count} | {avg_pct:.1f}% | {avg_passing:.1f}/10 |\n"

    # Top performers
    md += "\n## Top Performing D4Ds (Score >= 80%)\n\n"
    md += "| Project | Method | Type | Score | File |\n"
    md += "|---------|--------|------|-------|------|\n"

    top_performers = [r for r in results if r.get('overall_score', {}).get('percentage', 0) >= 80]
    top_performers.sort(key=lambda x: x.get('overall_score', {}).get('percentage', 0), reverse=True)

    for result in top_performers[:20]:  # Top 20
        project = result.get('project', 'unknown')
        method = result.get('method', 'unknown')
        eval_type = result.get('evaluation_type', 'unknown')
        overall = result.get('overall_score', {})
        score_str = f"{overall.get('total_points', 0)}/{overall.get('max_points', 50)} ({overall.get('percentage', 0):.1f}%)"
        file_name = Path(result.get('d4d_file', '')).name

        md += f"| {project} | {method} | {eval_type} | {score_str} | {file_name} |\n"

    # Save markdown
    md_path = EVAL_DIR / "summary_table.md"
    with open(md_path, 'w') as f:
        f.write(md)

    print(f"✅ Markdown table created: {md_path}")


def create_detailed_report(results: List[Dict]):
    """Create detailed markdown report."""

    report = f"""# Rubric10 Detailed Evaluation Report

**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**Total Evaluations:** {len(results)}

## Executive Summary

"""

    # Calculate overall statistics
    total_score = sum(r.get('overall_score', {}).get('total_points', 0) for r in results)
    max_possible = len(results) * 50
    avg_percentage = sum(r.get('overall_score', {}).get('percentage', 0) for r in results) / len(results) if results else 0

    report += f"- **Average Score:** {total_score / len(results):.1f}/50 ({avg_percentage:.1f}%)\n"
    report += f"- **Best Score:** {max(results, key=lambda x: x.get('overall_score', {}).get('percentage', 0)).get('overall_score', {}).get('percentage', 0):.1f}%\n" if results else ""
    report += f"- **Worst Score:** {min(results, key=lambda x: x.get('overall_score', {}).get('percentage', 0)).get('overall_score', {}).get('percentage', 0):.1f}%\n" if results else ""

    # Method comparison
    report += "\n## Method Comparison\n\n"

    for method in ['curated', 'gpt5', 'claudecode', 'claudecode_agent', 'claudecode_assistant']:
        method_results = [r for r in results if r.get('method') == method]
        if method_results:
            avg_score = sum(r.get('overall_score', {}).get('total_points', 0) for r in method_results) / len(method_results)
            avg_pct = sum(r.get('overall_score', {}).get('percentage', 0) for r in method_results) / len(method_results)
            report += f"### {method}\n"
            report += f"- Files evaluated: {len(method_results)}\n"
            report += f"- Average score: {avg_score:.1f}/50 ({avg_pct:.1f}%)\n\n"

    # Project comparison
    report += "\n## Project Comparison\n\n"

    for project in ['AI_READI', 'CHORUS', 'CM4AI', 'VOICE']:
        project_results = [r for r in results if r.get('project') == project]
        if project_results:
            avg_score = sum(r.get('overall_score', {}).get('total_points', 0) for r in project_results) / len(project_results)
            avg_pct = sum(r.get('overall_score', {}).get('percentage', 0) for r in project_results) / len(project_results)
            report += f"### {project}\n"
            report += f"- Files evaluated: {len(project_results)}\n"
            report += f"- Average score: {avg_score:.1f}/50 ({avg_pct:.1f}%)\n\n"

    # Save report
    report_path = EVAL_DIR / "summary_report.md"
    with open(report_path, 'w') as f:
        f.write(report)

    print(f"✅ Detailed report created: {report_path}")


if __name__ == "__main__":
    print("=" * 60)
    print("Rubric10 Results Summary Generator")
    print("=" * 60)
    print()

    # Load results
    print("Loading evaluation results...")
    results = load_evaluation_results()

    if not results:
        print("⚠️  No evaluation results found!")
        print("   Run evaluations first using the d4d-rubric10 agent")
        exit(1)

    print(f"Found {len(results)} evaluations")
    print()

    # Create outputs
    create_csv_summary(results)
    create_markdown_table(results)
    create_detailed_report(results)

    print()
    print("=" * 60)
    print("Summary files created successfully!")
    print("=" * 60)
    print()
    print("View results:")
    print("  cat data/evaluation_llm/rubric10/summary_table.md")
    print("  cat data/evaluation_llm/rubric10/summary_report.md")
    print("  open data/evaluation_llm/rubric10/all_scores.csv")
    print()
