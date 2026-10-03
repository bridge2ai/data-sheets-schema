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
import argparse
import hashlib
import io
from pathlib import Path
from typing import List, Dict
from datetime import datetime
from data_sheets_schema.rubric_pooling import MissingPercentage, reported_percentage
from data_sheets_schema.semantic_comparison import render_legacy_discrimination

# Base directory
BASE_DIR = Path(__file__).parent.parent
EVAL_DIR = BASE_DIR / "data" / "evaluation_llm" / "rubric10"
PROJECTS = ('AI_READI', 'CHORUS', 'CM4AI', 'VOICE')
CONCAT_METHODS = ('curated', 'gpt5', 'claudecode', 'claudecode_agent', 'claudecode_assistant')
INDIVIDUAL_METHODS = ('gpt5', 'claudecode_agent', 'claudecode_assistant')
DISCLOSURE_COLUMNS = (
    'model_disclosure_policy', 'disclosure_rating', 'evaluation_file',
    'evaluation_resolved_path', 'evaluation_sha256', 'declared_evaluator',
    'evaluator_family', 'generator', 'generator_family', 'same_family',
    'generation_binding', 'model_disclosure_limitations',
)


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


def _write_csv(results, stream, *, disclosures=None):
    """The legacy row order and score cells, with optional external identity."""
    writer = csv.writer(stream)

    # Header
    writer.writerow([
        'project', 'method', 'type', 'file',
        'total_score', 'max_score', 'percentage',
        'elements_passing', 'element_scores'
    ] + (list(DISCLOSURE_COLUMNS) if disclosures is not None else []))

    # Data rows
    for result in sorted(results, key=lambda x: (x.get('project', ''), x.get('type', ''), x.get('method', ''))):
        project = result.get('project', 'unknown')
        method = result.get('method', 'unknown')
        eval_type = result.get('evaluation_type', 'unknown')
        file_path = result.get('d4d_file', '')

        overall = result.get('overall_score', {})
        total_score = overall.get('total_points', 0)
        max_score = overall.get('max_points', 50)
        percentage = reported_percentage({'overall_score': overall})

        # Count elements passing (score >= 3/5)
        elements = result.get('elements', [])
        elements_passing = sum(1 for el in elements if el.get('element_score', 0) >= 3)

        # Element scores string
        element_scores_str = ','.join([
            f"{el['name'][:20]}:{el.get('element_score', 0)}/{el.get('element_max', 5)}"
            for el in elements[:10]  # Limit to 10 elements
        ])

        row = [
            project, method, eval_type, file_path,
            total_score, max_score, percentage,
            elements_passing, element_scores_str
        ]
        if disclosures is not None:
            from data_sheets_schema.model_disclosure import DISCLAIMER, VERSION
            captured, declared = disclosures[id(result)]
            values = [VERSION, declared['rating'], captured['evaluation_file'],
                      *[declared[key] for key in ('evaluation_resolved_path', 'evaluation_sha256',
                          'evaluator', 'evaluator_family', 'generator', 'generator_family',
                          'same_family', 'association_status')], DISCLAIMER]
            row.extend('unknown' if value is None else value for value in values)
        writer.writerow(row)


def create_csv_summary(results: List[Dict]):
    """Create CSV file with all scores at the unchanged historical destination."""
    csv_path = EVAL_DIR / "all_scores.csv"
    with open(csv_path, 'w', newline='') as stream:
        _write_csv(results, stream)
    print(f"✅ CSV summary created: {csv_path}")
    print(f"   Total evaluations: {len(results)}")


def _csv_summary_text(results, *, disclosures=None):
    with io.StringIO(newline='') as stream:
        _write_csv(results, stream, disclosures=disclosures)
        return stream.getvalue()


def _markdown_table_text(results: List[Dict]):
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
    for project in PROJECTS:
        for method in CONCAT_METHODS:
            key = (project, 'concatenated', method)
            if key in table_data and table_data[key]:
                result = table_data[key][0]  # Should only be one per key
                overall = result.get('overall_score', {})
                total = overall.get('total_points', 0)
                max_pts = overall.get('max_points', 50)
                pct = reported_percentage({'overall_score': overall})

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

    for project in PROJECTS:
        for method in INDIVIDUAL_METHODS:
            key = (project, 'individual', method)
            if key in table_data and table_data[key]:
                results_list = table_data[key]
                file_count = len(results_list)

                avg_score = sum(r.get('overall_score', {}).get('total_points', 0) for r in results_list) / file_count
                avg_pct = sum(reported_percentage(r) for r in results_list) / file_count

                avg_passing = sum(
                    sum(1 for el in r.get('elements', []) if el.get('element_score', 0) >= 3)
                    for r in results_list
                ) / file_count

                md += f"| {project} | {method} | {avg_score:.1f}/50 | {file_count} | {avg_pct:.1f}% | {avg_passing:.1f}/10 |\n"

    # Top performers
    md += "\n## Top Performing D4Ds (Score >= 80%)\n\n"
    md += "| Project | Method | Type | Score | File |\n"
    md += "|---------|--------|------|-------|------|\n"

    for result in _top_performers(results):  # Top 20
        project = result.get('project', 'unknown')
        method = result.get('method', 'unknown')
        eval_type = result.get('evaluation_type', 'unknown')
        overall = result.get('overall_score', {})
        score_str = f"{overall.get('total_points', 0)}/{overall.get('max_points', 50)} ({reported_percentage({'overall_score': overall}):.1f}%)"
        file_name = Path(result.get('d4d_file', '')).name

        md += f"| {project} | {method} | {eval_type} | {score_str} | {file_name} |\n"

    return md


def _top_performers(results):
    selected = [r for r in results if reported_percentage(r) >= 80]
    selected.sort(key=lambda result: reported_percentage(result), reverse=True)
    return selected[:20]


def create_markdown_table(results: List[Dict]):
    md = _markdown_table_text(results)
    md_path = EVAL_DIR / "summary_table.md"
    with open(md_path, 'w') as f:
        f.write(md)

    print(f"✅ Markdown table created: {md_path}")


def _detailed_report_text(results: List[Dict]):
    """Create detailed markdown report."""

    report = f"""# Rubric10 Detailed Evaluation Report

**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**Total Evaluations:** {len(results)}

## Executive Summary

"""

    # Calculate overall statistics
    total_score = sum(r.get('overall_score', {}).get('total_points', 0) for r in results)
    max_possible = len(results) * 50
    avg_percentage = sum(reported_percentage(r) for r in results) / len(results) if results else 0

    report += f"- **Average Score:** {total_score / len(results):.1f}/50 ({avg_percentage:.1f}%)\n"
    report += f"- **Best Score:** {reported_percentage(max(results, key=reported_percentage)):.1f}%\n" if results else ""
    report += f"- **Worst Score:** {reported_percentage(min(results, key=reported_percentage)):.1f}%\n" if results else ""

    # Method comparison
    report += "\n## Method Comparison\n\n"

    for method in CONCAT_METHODS:
        method_results = [r for r in results if r.get('method') == method]
        if method_results:
            avg_score = sum(r.get('overall_score', {}).get('total_points', 0) for r in method_results) / len(method_results)
            avg_pct = sum(reported_percentage(r) for r in method_results) / len(method_results)
            report += f"### {method}\n"
            report += f"- Files evaluated: {len(method_results)}\n"
            report += f"- Average score: {avg_score:.1f}/50 ({avg_pct:.1f}%)\n\n"

    # Project comparison
    report += "\n## Project Comparison\n\n"

    for project in PROJECTS:
        project_results = [r for r in results if r.get('project') == project]
        if project_results:
            avg_score = sum(r.get('overall_score', {}).get('total_points', 0) for r in project_results) / len(project_results)
            avg_pct = sum(reported_percentage(r) for r in project_results) / len(project_results)
            report += f"### {project}\n"
            report += f"- Files evaluated: {len(project_results)}\n"
            report += f"- Average score: {avg_score:.1f}/50 ({avg_pct:.1f}%)\n\n"

    # Item discrimination per cohort (#3281), as the semantic reports have
    # had since #2927: which items separate no record, and which projects
    # have too few distinct totals to order their records at all.
    report += "\n" + "\n".join(render_legacy_discrimination(results))

    return report


def create_detailed_report(results: List[Dict]):
    report = _detailed_report_text(results)
    report_path = EVAL_DIR / "summary_report.md"
    with open(report_path, 'w') as f:
        f.write(report)

    print(f"✅ Detailed report created: {report_path}")


def _disclosed_inputs(evaluation_root, bindings, disclosure_root):
    """Capture in legacy enumeration order; keep identity outside score dicts."""
    from data_sheets_schema.model_disclosure import build_report

    captures = []
    for kind, pattern in (("individual", "**/*_evaluation.json"),
                          ("concatenated", "*_evaluation.json")):
        directory = evaluation_root / kind
        if not directory.exists():
            continue
        for path in directory.glob(pattern):
            resolved = str(path.resolve())
            raw = path.read_bytes()
            original = json.loads(raw)
            if not isinstance(original, dict):
                raise ValueError(f'{path}: expected an evaluation object')
            captures.append({'result': {**original, 'evaluation_type': kind},
                             'path': path,
                             'evaluation_file': path.relative_to(evaluation_root).as_posix(),
                             'resolved': resolved, 'sha256': hashlib.sha256(raw).hexdigest()})
    if not captures:
        raise ValueError('no evaluation results found')
    report = build_report([capture['path'] for capture in captures], bindings=bindings,
                          root=disclosure_root)
    by_identity = {}
    for capture, row in zip(captures, report['rows'], strict=True):
        if (capture['resolved'] != row['evaluation_resolved_path'] or
                capture['sha256'] != row['evaluation_sha256']):
            raise ValueError(f"{capture['path']}: evaluation changed between score and disclosure capture")
        by_identity[id(capture['result'])] = (capture, row)
    return [capture['result'] for capture in captures], report, by_identity


def _membership(results, disclosures):
    """Expose existing table selections, without defining comparable cohorts."""
    first = {}
    for result in results:
        key = tuple(result.get(k, 'unknown') for k in ('project', 'evaluation_type', 'method'))
        first.setdefault(key, id(result))
    top = {id(result): rank for rank, result in enumerate(_top_performers(results), 1)}
    csv_order = sorted(results, key=lambda r: (r.get('project', ''), r.get('type', ''), r.get('method', '')))
    csv_rows = {id(result): row for row, result in enumerate(csv_order, 1)}
    rows = []
    for result in results:
        captured, declared = disclosures[id(result)]
        project, kind, method = (result.get(k, 'unknown')
                                 for k in ('project', 'evaluation_type', 'method'))
        if kind != 'concatenated':
            concatenated = 'not_concatenated'
        elif project not in PROJECTS or method not in CONCAT_METHODS:
            concatenated = 'unshown_project_or_method'
        elif first[(project, kind, method)] == id(result):
            concatenated = 'selected_first_rating'
        else:
            concatenated = 'unshown_repeat'
        if kind != 'individual':
            individual = 'not_individual'
        else:
            individual = ('included_in_legacy_average' if project in PROJECTS and method in INDIVIDUAL_METHODS
                          else 'unshown_project_or_method')
        top_state = ('selected' if id(result) in top else
                     'unshown_beyond_top20' if reported_percentage(result) >= 80 else 'below_threshold')
        rows.append({'disclosure_rating': declared['rating'], 'csv_row': csv_rows[id(result)],
                     'evaluation_file': captured['evaluation_file'],
                     'evaluation_resolved_path': declared['evaluation_resolved_path'],
                     'evaluation_sha256': declared['evaluation_sha256'],
                     'legacy_group': {'project': project, 'record_kind': kind, 'method': method},
                     'concatenated_table': concatenated, 'individual_table': individual,
                     'top_performers': top_state, 'top_rank': top.get(id(result)),
                     'executive_summary': 'included',
                     'method_summary': 'included' if method in CONCAT_METHODS else 'unshown_method',
                     'project_summary': 'included' if project in PROJECTS else 'unshown_project'})
    return rows


def _disclosure_appendix(results, report, disclosures):
    from data_sheets_schema.model_disclosure import render
    import html

    def cell(value):
        # JSON keeps membership structure explicit without introducing Markdown.
        text = json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False)
        return html.escape(text, quote=False).replace('|', '&#124;').replace('`', '&#96;')

    text = ['\n## Per-rating disclosure and legacy table membership\n\n',
            'The preceding score sections retain their existing aggregation and selection rules. '
            'Project/method groups are not certified as comparable instruments. Family labels '
            'apply to individual captured ratings, not pooled rows. Every selected input appears '
            'below, including ratings unshown in a legacy table. CSV rows are numbered after the header; '
            'disclosure indices follow the captured loader order. The existing discrimination '
            'helper retains its own cohort and duplicate policy.\n\n',
            '| Disclosure rating | CSV row | Evaluation file | Resolved evaluation | SHA256 | Legacy membership |\n',
            '|---|---|---|---|---|---|\n']
    for row in _membership(results, disclosures):
        identity = ('disclosure_rating', 'csv_row', 'evaluation_file', 'evaluation_resolved_path', 'evaluation_sha256')
        membership = {key: value for key, value in row.items() if key not in identity}
        text.append('| ' + ' | '.join(cell(row[key]) for key in identity) + ' | ' + cell(membership) + ' |\n')
    text.append('\n')
    text.append('\n'.join('#' + line if line.startswith('#') else line
                          for line in render(report).rstrip('\n').splitlines()) + '\n')
    return ''.join(text)


def write_disclosed_summaries(evaluation_root: Path, output_dir: Path, *,
                              generation_bindings=(), disclosure_root: Path | None = None):
    """Prepare all content, then create a fresh set; retain partial failures."""
    evaluation_root, output_dir = Path(evaluation_root), Path(output_dir)
    if output_dir.exists() or output_dir.is_symlink():
        raise ValueError('model disclosure output directory must be new')
    results, report, disclosures = _disclosed_inputs(evaluation_root, generation_bindings, disclosure_root)
    appendix = _disclosure_appendix(results, report, disclosures)
    texts = {'all_scores.csv': _csv_summary_text(results, disclosures=disclosures),
             'summary_table.md': _markdown_table_text(results) + appendix,
             'summary_report.md': _detailed_report_text(results) + appendix}
    output_dir.mkdir()
    for name, text in texts.items():
        with (output_dir / name).open('x', encoding='utf-8', newline='') as stream:
            stream.write(text)
    return {'policy': 'declared-v1', 'ratings': len(results),
            'outputs': {name: str(output_dir / name) for name in texts}}


def _legacy_main():
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


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--model-disclosure', choices=('declared-v1',))
    parser.add_argument('--evaluation-root', type=Path)
    parser.add_argument('--output-dir', type=Path, help='new directory for the opt-in summaries')
    parser.add_argument('--generation-binding', nargs=3, action='append', type=Path,
                        metavar=('EVALUATION', 'INPUT', 'PROVENANCE'))
    parser.add_argument('--disclosure-root', type=Path,
                        help='root for paths recorded inside generation evidence')
    args = parser.parse_args(argv)
    if args.model_disclosure is None:
        if any(value is not None for value in (args.evaluation_root, args.output_dir,
                                               args.generation_binding, args.disclosure_root)):
            parser.error('disclosure options require --model-disclosure declared-v1')
        return _legacy_main()
    if args.output_dir is None:
        parser.error('model disclosure requires --output-dir naming a new directory')
    from data_sheets_schema.model_disclosure import GenerationBinding
    try:
        result = write_disclosed_summaries(args.evaluation_root or EVAL_DIR, args.output_dir,
            generation_bindings=[GenerationBinding(*triple) for triple in args.generation_binding or ()],
            disclosure_root=args.disclosure_root)
    except (ValueError, OSError, MissingPercentage) as exc:
        parser.error(str(exc))
    print(json.dumps(result, sort_keys=True))


if __name__ == '__main__':
    main()
