#!/usr/bin/env python3
"""
Summarize Rubric20 Evaluation Results

Processes rubric20 evaluation JSONs and creates summary tables and reports.

Usage:
    python scripts/summarize_rubric20_results.py

Output:
    - data/evaluation_llm/rubric20/all_scores.csv
    - data/evaluation_llm/rubric20/summary_report.md
    - data/evaluation_llm/rubric20/summary_table.md
"""

import json
import csv
from pathlib import Path
from typing import List, Dict
from datetime import datetime

# Base directory
BASE_DIR = Path(__file__).parent.parent
EVAL_DIR = BASE_DIR / "data" / "evaluation_llm" / "rubric20"


def load_evaluation_results() -> List[Dict]:
    """Load all rubric20 evaluation JSON files."""
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
            'cat1_structural', 'cat2_metadata', 'cat3_technical', 'cat4_fairness',
            'question_scores'
        ])

        # Data rows
        for result in sorted(results, key=lambda x: (x.get('project', ''), x.get('type', ''), x.get('method', ''))):
            project = result.get('project', 'unknown')
            method = result.get('method', 'unknown')
            eval_type = result.get('evaluation_type', 'unknown')
            file_path = result.get('d4d_file', '')

            overall = result.get('overall_score', {})
            total_score = overall.get('total_points', 0)
            max_score = overall.get('max_points', 84)
            percentage = overall.get('percentage', 0)

            # Category scores
            categories = result.get('categories', {})
            cat1 = categories.get('Structural Completeness', {}).get('category_score', 0)
            cat2 = categories.get('Metadata Quality & Content', {}).get('category_score', 0)
            cat3 = categories.get('Technical Documentation', {}).get('category_score', 0)
            cat4 = categories.get('FAIRness & Accessibility', {}).get('category_score', 0)

            # Question scores string
            questions = result.get('questions', [])
            question_scores_str = ','.join([
                f"Q{q['id']}:{q.get('score', 0)}/{q.get('max_score', 5)}"
                for q in sorted(questions, key=lambda x: x.get('id', 0))[:20]
            ])

            writer.writerow([
                project, method, eval_type, file_path,
                total_score, max_score, percentage,
                cat1, cat2, cat3, cat4,
                question_scores_str
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
    md = f"""# Rubric20 Evaluation Summary

**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

**Total Evaluations:** {len(results)}

## Concatenated D4Ds

| Project | Method | Score | Percentage | Cat1 | Cat2 | Cat3 | Cat4 | Top Question | Weakest Question |
|---------|--------|-------|------------|------|------|------|------|--------------|------------------|
"""

    # Concatenated results
    for project in ['AI_READI', 'CHORUS', 'CM4AI', 'VOICE']:
        for method in ['curated', 'gpt5', 'claudecode', 'claudecode_agent', 'claudecode_assistant']:
            key = (project, 'concatenated', method)
            if key in table_data and table_data[key]:
                result = table_data[key][0]  # Should only be one per key
                overall = result.get('overall_score', {})
                total = overall.get('total_points', 0)
                max_pts = overall.get('max_points', 84)
                pct = overall.get('percentage', 0)

                # Category scores
                categories = result.get('categories', {})
                cat1 = categories.get('Structural Completeness', {}).get('category_score', 0)
                cat2 = categories.get('Metadata Quality & Content', {}).get('category_score', 0)
                cat3 = categories.get('Technical Documentation', {}).get('category_score', 0)
                cat4 = categories.get('FAIRness & Accessibility', {}).get('category_score', 0)

                # Find top and weakest questions
                questions = result.get('questions', [])
                if questions:
                    top_q = max(questions, key=lambda x: x.get('score', 0) / max(x.get('max_score', 1), 1))
                    weak_q = min(questions, key=lambda x: x.get('score', 0) / max(x.get('max_score', 1), 1))

                    top_name = f"Q{top_q['id']}: {top_q['name'][:20]}... ({top_q['score']}/{top_q['max_score']})"
                    weak_name = f"Q{weak_q['id']}: {weak_q['name'][:20]}... ({weak_q['score']}/{weak_q['max_score']})"
                else:
                    top_name = "N/A"
                    weak_name = "N/A"

                md += f"| {project} | {method} | {total}/{max_pts} | {pct:.1f}% | {cat1} | {cat2} | {cat3} | {cat4} | {top_name} | {weak_name} |\n"

    # Individual results summary
    md += "\n## Individual D4Ds Summary\n\n"
    md += "| Project | Method | Avg Score | Files | Avg % | Avg Cat1 | Avg Cat2 | Avg Cat3 | Avg Cat4 |\n"
    md += "|---------|--------|-----------|-------|-------|----------|----------|----------|----------|\n"

    for project in ['AI_READI', 'CHORUS', 'CM4AI', 'VOICE']:
        for method in ['gpt5', 'claudecode_agent', 'claudecode_assistant']:
            key = (project, 'individual', method)
            if key in table_data and table_data[key]:
                results_list = table_data[key]
                file_count = len(results_list)

                avg_score = sum(r.get('overall_score', {}).get('total_points', 0) for r in results_list) / file_count
                avg_pct = sum(r.get('overall_score', {}).get('percentage', 0) for r in results_list) / file_count

                avg_cat1 = sum(r.get('categories', {}).get('Structural Completeness', {}).get('category_score', 0) for r in results_list) / file_count
                avg_cat2 = sum(r.get('categories', {}).get('Metadata Quality & Content', {}).get('category_score', 0) for r in results_list) / file_count
                avg_cat3 = sum(r.get('categories', {}).get('Technical Documentation', {}).get('category_score', 0) for r in results_list) / file_count
                avg_cat4 = sum(r.get('categories', {}).get('FAIRness & Accessibility', {}).get('category_score', 0) for r in results_list) / file_count

                md += f"| {project} | {method} | {avg_score:.1f}/84 | {file_count} | {avg_pct:.1f}% | {avg_cat1:.1f} | {avg_cat2:.1f} | {avg_cat3:.1f} | {avg_cat4:.1f} |\n"

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
        score_str = f"{overall.get('total_points', 0)}/{overall.get('max_points', 84)} ({overall.get('percentage', 0):.1f}%)"
        file_name = Path(result.get('d4d_file', '')).name

        md += f"| {project} | {method} | {eval_type} | {score_str} | {file_name} |\n"

    # Save markdown
    md_path = EVAL_DIR / "summary_table.md"
    with open(md_path, 'w') as f:
        f.write(md)

    print(f"✅ Markdown table created: {md_path}")


def create_detailed_report(results: List[Dict]):
    """Create detailed markdown report."""

    report = f"""# Rubric20 Detailed Evaluation Report

**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**Total Evaluations:** {len(results)}

## Executive Summary

"""

    # Calculate overall statistics
    total_score = sum(r.get('overall_score', {}).get('total_points', 0) for r in results)
    max_possible = len(results) * 84
    avg_percentage = sum(r.get('overall_score', {}).get('percentage', 0) for r in results) / len(results) if results else 0

    report += f"- **Average Score:** {total_score / len(results):.1f}/84 ({avg_percentage:.1f}%)\n"
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
            report += f"- Average score: {avg_score:.1f}/84 ({avg_pct:.1f}%)\n\n"

    # Project comparison
    report += "\n## Project Comparison\n\n"

    for project in ['AI_READI', 'CHORUS', 'CM4AI', 'VOICE']:
        project_results = [r for r in results if r.get('project') == project]
        if project_results:
            avg_score = sum(r.get('overall_score', {}).get('total_points', 0) for r in project_results) / len(project_results)
            avg_pct = sum(r.get('overall_score', {}).get('percentage', 0) for r in project_results) / len(project_results)
            report += f"### {project}\n"
            report += f"- Files evaluated: {len(project_results)}\n"
            report += f"- Average score: {avg_score:.1f}/84 ({avg_pct:.1f}%)\n\n"

    # Category analysis
    report += "\n## Category Performance\n\n"

    categories = ['Structural Completeness', 'Metadata Quality & Content', 'Technical Documentation', 'FAIRness & Accessibility']

    for cat_name in categories:
        cat_scores = []
        for r in results:
            cat_data = r.get('categories', {}).get(cat_name, {})
            if cat_data:
                cat_scores.append(cat_data.get('category_score', 0))

        if cat_scores:
            avg_cat_score = sum(cat_scores) / len(cat_scores)
            report += f"### {cat_name}\n"
            report += f"- Average score: {avg_cat_score:.1f}\n\n"

    # Save report
    report_path = EVAL_DIR / "summary_report.md"
    with open(report_path, 'w') as f:
        f.write(report)

    print(f"✅ Detailed report created: {report_path}")


if __name__ == "__main__":
    print("=" * 60)
    print("Rubric20 Results Summary Generator")
    print("=" * 60)
    print()

    # Load results
    print("Loading evaluation results...")
    results = load_evaluation_results()

    if not results:
        print("⚠️  No evaluation results found!")
        print("   Run evaluations first using batch_evaluate_rubric20_hybrid.py")
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
    print("  cat data/evaluation_llm/rubric20/summary_table.md")
    print("  cat data/evaluation_llm/rubric20/summary_report.md")
    print("  open data/evaluation_llm/rubric20/all_scores.csv")
    print()
