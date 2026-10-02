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
import html
from pathlib import Path
from typing import List, Dict
from datetime import datetime

# Read each evaluation's recorded denominator and percentage.
from data_sheets_schema.rubric_pooling import (
    denominator_of, pooling_warning, reported_percentage)
from data_sheets_schema.semantic_comparison import (
    discrimination, legacy_record, render_discrimination)

# Base directory
BASE_DIR = Path(__file__).parent.parent
EVAL_DIR = BASE_DIR / "data" / "evaluation_llm" / "rubric20"


def load_evaluation_results() -> List[Dict]:
    """Load the legacy cohort, retaining each evaluation's relative source path.

    Individual evaluations are recursive; concatenated evaluations are only
    the undated directory's direct children. Dated concatenated subdirectories
    are separate historical cohorts, not additional ratings of this cohort.
    """
    results = []
    for kind, pattern in (("individual", "individual/**/*_evaluation.json"),
                          ("concatenated", "concatenated/*_evaluation.json")):
        for json_file in sorted(EVAL_DIR.glob(pattern)):
            with json_file.open(encoding="utf-8") as stream:
                data = json.load(stream)
            data['evaluation_type'] = kind
            data['_evaluation_file'] = json_file.relative_to(EVAL_DIR).as_posix()
            results.append(data)
    return sorted(results, key=result_order)


def result_order(result: Dict):
    """Stable even for repeated ratings of one record, independent of glob order."""
    return tuple(str(result.get(key) or '') for key in (
        'evaluation_type', 'project', 'method', 'd4d_file',
        'evaluation_timestamp', '_evaluation_file')) + (
            json.dumps(result, sort_keys=True, ensure_ascii=False),)


def cohort_key(result: Dict):
    """Separate recorded measurement identities; do not infer missing metadata.

    The full model block includes temperature and evaluator type, not just
    its name. A rubric hash is used verbatim: legacy placeholders are not
    promoted to verified digests. A record hash and evaluator execution ID
    identify individual evaluations, not a scoring instrument.
    """
    metadata = result.get('metadata') or {}
    return (str(result.get('evaluation_type') or 'unknown'),
            str(result.get('rubric') or 'unrecorded'),
            str(result.get('version') or 'unrecorded'),
            json.dumps(result.get('model') or {}, sort_keys=True, ensure_ascii=False),
            str(metadata.get('rubric_hash') or 'unrecorded'),
            denominator_of(result))


def summary_cohorts(results: List[Dict]):
    groups = {}
    for result in sorted(results, key=result_order):
        groups.setdefault(cohort_key(result), []).append(result)
    return sorted(groups.items())


def cell(value) -> str:
    """Keep recorded labels and paths inside one Markdown table cell."""
    return html.escape(str(value), quote=False).replace('|', '&#124;').replace(
        '`', '&#96;').replace('\r\n', '\n').replace('\n', '<br>')


def evaluator_name(result: Dict) -> str:
    return str((result.get('model') or {}).get('name') or 'an unrecorded evaluator')


def cohort_description(key, count: int) -> str:
    kind, rubric, version, settings, rubric_hash, maximum = key
    who = json.loads(settings).get('name') or 'an unrecorded evaluator'
    return (f"### Scored out of {maximum:g} — {cell(kind)} evaluations by {cell(who)}\n\n"
            f"{count} evaluation(s); rubric {cell(rubric)}, version {cell(version)}. "
            f"Recorded rubric hash: {cell(rubric_hash)}.\n\n"
            f"Recorded evaluator settings: {cell(settings)}.\n\n")


def cohort_note(results: List[Dict]) -> str:
    return ("Summaries separate record kind, rubric/version, the complete recorded evaluator "
            "settings, recorded rubric hash and score maximum. Missing metadata stays "
            "unrecorded; recorded hashes (including legacy placeholders) are not verified "
            "instrument digests. Generator identity is not inferred from method names.\n\n"
            "Counts and averages describe evaluations, not distinct files: repeated ratings "
            "are retained and equally weighted. The discrimination blocks separately exclude "
            "records rated more than once within their cohort.\n\n"
            "Cohort selection: recursive `individual/**/*_evaluation.json` and direct "
            "`concatenated/*_evaluation.json` children. Dated concatenated subdirectories "
            "are excluded. `all_scores.csv` lists every selected evaluation and its source "
            "path relative to this directory.\n\n" + pooling_warning(results))


def categories_by_name(result: Dict) -> Dict[str, Dict]:
    """The evaluation's categories as a mapping keyed on category name.

    The hybrid evaluator writes `categories` as that mapping; the
    claude-fable-5 evaluations write a list of entries that each carry their
    `name` (#3524). Every reader below goes through this, so neither shape is
    special-cased where a score is read. An entry with no name, or a name
    listed twice, is refused rather than dropped: a category the summary
    cannot address would otherwise vanish from every table without a trace.
    """
    categories = result.get('categories') or {}
    if isinstance(categories, dict):
        return categories
    by_name: Dict[str, Dict] = {}
    for entry in categories:
        name = entry.get('name')
        if name is None or name in by_name:
            problem = "a category with no name" if name is None else f"category {name!r} twice"
            raise ValueError(f"{result.get('d4d_file', '<no d4d_file>')}: "
                             f"the evaluation lists {problem}")
        by_name[name] = entry
    return by_name


def questions_of(result: Dict) -> List[Dict]:
    """The evaluation's questions, each once.

    The hybrid evaluator lists them at the top level and again under their
    category; the list-shaped evaluations only under their category (#3524).
    Where there is a top-level list it is read alone, as this summary always
    read the mapping-shaped evaluations, so their output is unchanged and no
    question is counted twice; the category lists are read only where there
    is no top-level list.

    This is not how `semantic_comparison.item_scores()` resolves the two
    copies: it reads the union keyed on question id, so where both copies
    of a question exist the category copy wins, and a question listed only
    under a category is kept. The two agree whenever the copies agree, as
    they do in every mapping-shaped evaluation committed at #3524 (#3661).
    """
    if result.get('questions'):
        return list(result['questions'])
    return [q for category in categories_by_name(result).values()
            for q in category.get('questions') or []]


def create_csv_summary(results: List[Dict]):
    """One row per evaluation, with enough identity to separate its cohort."""
    csv_path = EVAL_DIR / "all_scores.csv"
    with csv_path.open('w', newline='', encoding='utf-8') as stream:
        writer = csv.writer(stream, lineterminator='\n')
        writer.writerow([
            'project', 'method', 'type', 'file',
            'total_score', 'max_score', 'percentage',
            'cat1_structural', 'cat2_metadata', 'cat3_technical', 'cat4_fairness',
            'question_scores', 'evaluation_file', 'evaluation_timestamp',
            'rubric', 'rubric_version', 'evaluator', 'evaluator_settings', 'rubric_hash',
        ])
        for result in sorted(results, key=result_order):
            kind, rubric, version, settings, rubric_hash, maximum = cohort_key(result)
            overall = result.get('overall_score') or {}
            categories = categories_by_name(result)
            question_scores = ','.join(
                f"Q{q['id']}:{q.get('score', 0)}/{q.get('max_score', 5)}"
                for q in sorted(questions_of(result), key=lambda q: q.get('id', 0))[:20])
            writer.writerow([
                result.get('project', 'unknown'), result.get('method', 'unknown'),
                kind, result.get('d4d_file', ''), overall.get('total_points', 0),
                maximum, reported_percentage(result),
                *[categories.get(name, {}).get('category_score', 0) for name in CATEGORY_NAMES],
                question_scores, result.get('_evaluation_file', ''),
                result.get('evaluation_timestamp', ''), rubric, version,
                evaluator_name(result), settings, rubric_hash,
            ])
    print(f"CSV summary created: {csv_path} ({len(results)} evaluations)")


CATEGORY_NAMES = ('Structural Completeness', 'Metadata Quality & Content',
                  'Technical Documentation', 'FAIRness & Accessibility')


def table_row(values) -> str:
    return '| ' + ' | '.join(cell(value) for value in values) + ' |\n'


def create_markdown_table(results: List[Dict]):
    """List every concatenated rating and summarize individuals within cohorts."""
    md = ("# Rubric20 Evaluation Summary\n\n"
          f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
          f"**Total Evaluations:** {len(results)}\n\n" + cohort_note(results))
    for kind in sorted({cohort_key(result)[0] for result in results}):
        heading = {'concatenated': 'Concatenated D4Ds',
                   'individual': 'Individual D4Ds Summary'}.get(kind, f'{cell(kind)} D4Ds')
        md += f"## {heading}\n\n"
        for key, group in summary_cohorts(results):
            if key[0] != kind:
                continue
            md += cohort_description(key, len(group))
            if kind == 'individual':
                md += ("| Project | Method | Avg Score | Evaluations | Avg % | Avg Cat1 | Avg Cat2 | Avg Cat3 | Avg Cat4 |\n"
                       "|---|---|---|---|---|---|---|---|---|\n")
                projects_methods = sorted({(str(r.get('project', 'unknown')),
                                           str(r.get('method', 'unknown'))) for r in group})
                for project, method in projects_methods:
                    members = [r for r in group if str(r.get('project', 'unknown')) == project
                               and str(r.get('method', 'unknown')) == method]
                    count = len(members)
                    avg_score = sum(r.get('overall_score', {}).get('total_points', 0)
                                    for r in members) / count
                    avg_pct = sum(reported_percentage(r) for r in members) / count
                    cats = [sum(categories_by_name(r).get(name, {}).get('category_score', 0)
                                for r in members) / count for name in CATEGORY_NAMES]
                    md += table_row([project, method, f'{avg_score:.1f}/{key[-1]:g}', count,
                                     f'{avg_pct:.1f}%', *[f'{value:.1f}' for value in cats]])
            else:
                md += ("| Project | Method | Score | Percentage | Cat1 | Cat2 | Cat3 | Cat4 | Top Question | Weakest Question | D4D File | Evaluation File | Evaluation Time |\n"
                       "|---|---|---|---|---|---|---|---|---|---|---|---|---|\n")
                for result in group:
                    overall = result.get('overall_score') or {}
                    cats = categories_by_name(result)
                    questions = questions_of(result)
                    def question_label(question):
                        return (f"Q{question['id']}: {question['name'][:20]}... "
                                f"({question['score']}/{question['max_score']})")
                    if questions:
                        ratio = lambda q: q.get('score', 0) / max(q.get('max_score', 1), 1)
                        top = question_label(max(questions, key=ratio))
                        weak = question_label(min(questions, key=ratio))
                    else:
                        top = weak = 'N/A'
                    md += table_row([
                        result.get('project', 'unknown'), result.get('method', 'unknown'),
                        f"{overall.get('total_points', 0)}/{key[-1]:g}",
                        f'{reported_percentage(result):.1f}%',
                        *[cats.get(name, {}).get('category_score', 0) for name in CATEGORY_NAMES],
                        top, weak, result.get('d4d_file', ''), result.get('_evaluation_file', 'unrecorded'),
                        result.get('evaluation_timestamp', 'unrecorded'),
                    ])
            md += '\n'

    md += '## Top Performing D4Ds (Score >= 80%)\n\nUp to 20 evaluations per cohort; ties use the stable evaluation identity order.\n'
    for key, group in summary_cohorts(results):
        ranked = sorted((r for r in group if reported_percentage(r) >= 80),
                        key=lambda r: (-reported_percentage(r), result_order(r)))
        if not ranked:
            continue
        md += '\n' + cohort_description(key, len(group))
        md += '| Project | Method | Type | Score | D4D File | Evaluation File |\n|---|---|---|---|---|---|\n'
        for result in ranked[:20]:
            overall = result.get('overall_score') or {}
            md += table_row([result.get('project', 'unknown'), result.get('method', 'unknown'),
                             key[0], f"{overall.get('total_points', 0)}/{key[-1]:g} ({reported_percentage(result):.1f}%)",
                             result.get('d4d_file', ''), result.get('_evaluation_file', 'unrecorded')])
    md_path = EVAL_DIR / 'summary_table.md'
    md_path.write_text(md, encoding='utf-8')
    print(f'Markdown table created: {md_path}')


def create_detailed_report(results: List[Dict]):
    """All aggregates and discrimination use the same recorded cohort identity."""
    report = ('# Rubric20 Detailed Evaluation Report\n\n'
              f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
              f'**Total Evaluations:** {len(results)}\n\n' + cohort_note(results))
    report += '## Executive Summary\n\n'
    cohorts = summary_cohorts(results)
    for key, group in cohorts:
        report += cohort_description(key, len(group))
        avg_score = sum(r.get('overall_score', {}).get('total_points', 0) for r in group) / len(group)
        percentages = [reported_percentage(r) for r in group]
        report += (f'- **Average Score:** {avg_score:.1f}/{key[-1]:g} ({sum(percentages) / len(group):.1f}%)\n'
                   f'- **Best Score:** {max(percentages):.1f}%\n'
                   f'- **Worst Score:** {min(percentages):.1f}%\n\n')

    for field, heading in (('method', 'Method Comparison'), ('project', 'Project Comparison')):
        report += f'## {heading}\n\n'
        for key, group in cohorts:
            report += cohort_description(key, len(group))
            for name in sorted({str(r.get(field, 'unknown')) for r in group}):
                members = [r for r in group if str(r.get(field, 'unknown')) == name]
                count = len(members)
                avg_score = sum(r.get('overall_score', {}).get('total_points', 0) for r in members) / count
                avg_pct = sum(reported_percentage(r) for r in members) / count
                report += (f'#### {cell(name)}\n- Evaluations: {count}\n'
                           f'- Average score: {avg_score:.1f}/{key[-1]:g} '
                           f'({avg_pct:.1f}%) over {count} evaluation(s)\n\n')

    report += '## Category Performance\n\n'
    for key, group in cohorts:
        report += cohort_description(key, len(group))
        for name in CATEGORY_NAMES:
            scores = [categories_by_name(r)[name].get('category_score', 0) for r in group
                      if name in categories_by_name(r)]
            if scores:
                report += (f'#### {name}\n- Average score: {sum(scores) / len(scores):.1f}\n'
                           f'- Evaluations with this category: {len(scores)}\n\n')

    for key, group in cohorts:
        kind, _rubric, _version, _settings, _hash, maximum = key
        who = evaluator_name(group[0])
        report += cohort_description(key, len(group))
        others = len(results) - len(group)
        measured_on = (f'{len(group)} of the {len(results)} evaluations above: the {kind} '
                       f'evaluations by {who} scored out of {maximum:g}, '
                       'with the recorded rubric and evaluator settings stated immediately above'
                       + (f'. The other {others} are in no count in this block' if others else ''))
        report += '\n'.join(render_discrimination(
            discrimination(legacy_record(r) for r in group),
            scope=f', {kind} evaluations by {who} scored out of {maximum:g}',
            evaluator=who, measured_on=measured_on)) + '\n'

    report_path = EVAL_DIR / 'summary_report.md'
    report_path.write_text(report, encoding='utf-8')
    print(f'Detailed report created: {report_path}')


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
