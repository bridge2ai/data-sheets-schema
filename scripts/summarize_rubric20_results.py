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
import argparse
import hashlib
import io
from pathlib import Path
from typing import List, Dict, NamedTuple
from datetime import datetime

from data_sheets_schema.constants import RUBRIC20_MAX_SCORE
from data_sheets_schema.semantic_comparison import (
    discrimination, excluded_items, legacy_record, render_discrimination, score_bases)

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


class CohortKey(NamedTuple):
    kind: str
    rubric: str
    version: str
    settings: str
    rubric_hash: str
    instrument: str
    context: str
    scope: str
    score_mode: str
    exclusions: str
    fixed_max: float
    adjusted_max: float


def recorded(mapping, name):
    """Canonical recorded JSON, keeping absent distinct from explicit null."""
    return json.dumps(mapping[name], sort_keys=True, ensure_ascii=False) if name in mapping else 'unrecorded'


def bases_of(result):
    return score_bases(result, RUBRIC20_MAX_SCORE)


def score_mode(result):
    overall = result.get('overall_score') or result.get('summary_scores') or {}
    if any(name in overall for name in ('fixed_max_points', 'adjusted_max_points', 'excluded_max_points')):
        return 'fixed_and_adjusted'
    if 'normalized_percentage' in overall or excluded_items(result):
        return 'adjustment_unrecorded'
    return 'legacy_fixed_only'


def exclusions_of(result):
    # Normalize API fixed_max_points/max_points for the existing helper's
    # semantic layout. Never modify the source evaluation (#4214).
    bases = bases_of(result)
    overall = result.get('overall_score') or result.get('summary_scores') or {}
    normalized = {**overall, 'max_points': bases.fixed_max,
                  'adjusted_max_points': bases.adjusted_max}
    return excluded_items({**result, 'overall_score': normalized})


def cohort_key(result: Dict):
    """Use recorded instruments, context/scope and score bases (#4213/4214).

    A record hash and execution ID identify individual evaluations rather
    than scoring instruments. Legacy rubric hashes remain unverified.
    Unknown adjusted applicability is not evidence of comparability.
    """
    metadata = result.get('metadata') or {}
    bases = bases_of(result)
    return CohortKey(
        str(result.get('evaluation_type') or 'unknown'),
        str(result.get('rubric') or 'unrecorded'),
        str(result.get('version') or 'unrecorded'),
        json.dumps(result.get('model') or {}, sort_keys=True, ensure_ascii=False),
        recorded(metadata, 'rubric_hash'), recorded(metadata, 'instrument_sha256'),
        recorded(metadata, 'context_sha256'), recorded(result, 'evaluation_scope'),
        score_mode(result), json.dumps(exclusions_of(result)),
        bases.fixed_max, bases.adjusted_max)


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
    who = json.loads(key.settings).get('name') or 'an unrecorded evaluator'
    exclusions = ('unrecorded' if key.exclusions == 'null' else key.exclusions)
    adjusted = f'{key.adjusted_max:g}' if key.score_mode == 'fixed_and_adjusted' else 'unrecorded'
    return (f"### Scored out of {key.fixed_max:g} — {cell(key.kind)} evaluations by {cell(who)}\n\n"
            f"{count} evaluation(s); rubric {cell(key.rubric)}, version {cell(key.version)}. "
            f"Recorded rubric hash: {cell(key.rubric_hash)}.\n\n"
            f"Recorded evaluator settings: {cell(key.settings)}.\n\n"
            f"Instrument SHA-256: {cell(key.instrument)}; context SHA-256: {cell(key.context)}; "
            f"evaluation scope: {cell(key.scope)}.\n\n"
            f"Score mode: {key.score_mode}; fixed maximum: {key.fixed_max:g}; "
            f"adjusted maximum: {adjusted}; excluded items: {cell(exclusions)}.\n\n")


def cohort_note(results: List[Dict]) -> str:
    maxima = sorted({bases_of(result).fixed_max for result in results})
    warning = (f"> These results span {len(maxima)} different maxima; "
               "scores are never pooled across them.\n\n") if len(maxima) > 1 else ''
    return ("Summaries separate record kind, rubric/version, complete recorded evaluator settings, "
            "rubric hash, authoritative instrument/context pins, evaluation scope, score mode, "
            "both maxima and excluded-item identities. Missing metadata stays unrecorded; "
            "recorded hashes (including legacy placeholders) are not verified here. "
            "Generator identity is not inferred from method names.\n\n"
            "Fixed percentages are recomputed from total/fixed maximum. Adjusted percentages use "
            "the adjusted maximum; zero gives an undefined percentage. Legacy fixed-only records "
            "are not relabeled as recorded adjusted measurements. Adjusted averages and "
            "discrimination are withheld when applicability identities or the adjusted basis are "
            "unrecorded. Top-performing evaluations use the fixed percentage only.\n\n"
            "CSV compatibility: total_score, max_score and percentage describe the fixed basis, "
            "identified by score_basis. Added adjusted columns describe the recorded adjusted "
            "basis; empty adjusted fields mean unrecorded and an empty percentage with maximum "
            "zero means undefined. reported_* columns preserve each original rate as JSON "
            "(empty means absent), including any rounding or disagreement.\n\n"
            "Counts and averages describe evaluations, not distinct files: repeated ratings "
            "are retained and equally weighted. The discrimination blocks separately exclude "
            "records rated more than once within their cohort.\n\n"
            "Cohort selection: recursive `individual/**/*_evaluation.json` and direct "
            "`concatenated/*_evaluation.json` children. Dated concatenated subdirectories "
            "are excluded. `all_scores.csv` lists every selected evaluation and its source "
            "path relative to this directory.\n\n" + warning)


def percentage_label(value):
    return 'undefined' if value is None else f'{value:.1f}%'


def adjusted_label(result):
    if score_mode(result) != 'fixed_and_adjusted':
        return 'unrecorded'
    bases = bases_of(result)
    return f'{bases.total:g}/{bases.adjusted_max:g} ({percentage_label(bases.adjusted_percentage)})'


def average_labels(members):
    """The caller groups first; never derive comparability from an unknown."""
    key = cohort_key(members[0])
    bases = [bases_of(result) for result in members]
    average = sum(b.total for b in bases) / len(bases)
    fixed = f'{average:.1f}/{key.fixed_max:g} ({100 * average / key.fixed_max:.1f}%)'
    if key.score_mode == 'legacy_fixed_only':
        adjusted = 'unrecorded (fixed-only legacy)'
    elif key.score_mode != 'fixed_and_adjusted' or key.exclusions == 'null':
        adjusted = 'withheld (adjusted basis or excluded-item identities unrecorded)'
    else:
        rate = 100 * average / key.adjusted_max if key.adjusted_max else None
        adjusted = f'{average:.1f}/{key.adjusted_max:g} ({percentage_label(rate)})'
    return fixed, adjusted


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


DISCLOSURE_COLUMNS = (
    'model_disclosure_policy', 'disclosure_rating', 'declared_evaluator',
    'evaluator_family', 'generator', 'generator_family', 'same_family',
    'generation_binding', 'evaluation_resolved_path', 'evaluation_sha256',
    'model_disclosure_limitations',
)


def _csv_summary_text(results: List[Dict], *, disclosure_rows=None):
    """Preserve raw rates separately; legacy score columns now name one basis."""
    rows = []
    for result in sorted(results, key=result_order):
        key = cohort_key(result)
        bases = bases_of(result)
        overall = result.get('overall_score') or result.get('summary_scores') or {}
        categories = categories_by_name(result)
        question_scores = ','.join(
            f"Q{q['id']}:{q.get('score', 0)}/{q.get('max_score', 5)}"
            for q in sorted(questions_of(result), key=lambda q: q.get('id', 0))[:20])
        adjusted_recorded = key.score_mode == 'fixed_and_adjusted'
        rows.append([
            result.get('project', 'unknown'), result.get('method', 'unknown'),
            key.kind, result.get('d4d_file', ''), bases.total,
            bases.fixed_max, bases.fixed_percentage,
            *[categories.get(name, {}).get('category_score', 0) for name in CATEGORY_NAMES],
            question_scores, result.get('_evaluation_file', ''),
            result.get('evaluation_timestamp', ''), key.rubric, key.version,
            evaluator_name(result), key.settings,
            (result.get('metadata') or {}).get('rubric_hash', 'unrecorded'),
            'fixed', key.score_mode,
            bases.adjusted_max if adjusted_recorded else '',
            bases.adjusted_percentage if adjusted_recorded else '', key.exclusions,
            *[json.dumps(overall[name], ensure_ascii=False) if name in overall else ''
              for name in ('percentage', 'normalized_percentage', 'fixed_percentage')],
            key.instrument, key.context, key.scope,
        ])
        if disclosure_rows is not None:
            from data_sheets_schema.model_disclosure import DISCLAIMER, VERSION
            declared = disclosure_rows[result['_evaluation_file']]
            values = [VERSION, declared['rating'],
                      *[declared[k] for k in ('evaluator', 'evaluator_family', 'generator',
                                              'generator_family', 'same_family', 'association_status',
                                              'evaluation_resolved_path', 'evaluation_sha256')],
                      DISCLAIMER]
            rows[-1].extend('unknown' if value is None else value for value in values)
    with io.StringIO(newline='') as stream:
        writer = csv.writer(stream, lineterminator='\n')
        columns = [
            'project', 'method', 'type', 'file',
            'total_score', 'max_score', 'percentage',
            'cat1_structural', 'cat2_metadata', 'cat3_technical', 'cat4_fairness',
            'question_scores', 'evaluation_file', 'evaluation_timestamp',
            'rubric', 'rubric_version', 'evaluator', 'evaluator_settings', 'rubric_hash',
            'score_basis', 'score_mode', 'adjusted_max_score', 'adjusted_percentage',
            'excluded_items', 'reported_percentage', 'reported_normalized_percentage',
            'reported_fixed_percentage', 'instrument_sha256', 'context_sha256', 'evaluation_scope',
        ]
        writer.writerow(columns + (list(DISCLOSURE_COLUMNS) if disclosure_rows is not None else []))
        writer.writerows(rows)
        return stream.getvalue()


def create_csv_summary(results: List[Dict]):
    """Write the unchanged default CSV to the historical destination."""
    csv_path = EVAL_DIR / "all_scores.csv"
    text = _csv_summary_text(results)
    with csv_path.open('w', newline='', encoding='utf-8') as stream:
        stream.write(text)
    print(f"CSV summary created: {csv_path} ({len(results)} evaluations)")


CATEGORY_NAMES = ('Structural Completeness', 'Metadata Quality & Content',
                  'Technical Documentation', 'FAIRness & Accessibility')


def table_row(values) -> str:
    return '| ' + ' | '.join(cell(value) for value in values) + ' |\n'


def _markdown_table_text(results: List[Dict]):
    """List every concatenated rating and summarize individuals within cohorts."""
    cohorts = summary_cohorts(results)
    md = ("# Rubric20 Evaluation Summary\n\n"
          f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
          f"**Total Evaluations:** {len(results)}\n\n" + cohort_note(results))
    for kind in sorted({key.kind for key, _group in cohorts}):
        heading = {'concatenated': 'Concatenated D4Ds',
                   'individual': 'Individual D4Ds Summary'}.get(kind, f'{cell(kind)} D4Ds')
        md += f"## {heading}\n\n"
        for key, group in cohorts:
            if key.kind != kind:
                continue
            md += cohort_description(key, len(group))
            if kind == 'individual':
                md += ("| Project | Method | Avg Fixed Score (%) | Evaluations | Avg Adjusted Score (%) | Avg Cat1 | Avg Cat2 | Avg Cat3 | Avg Cat4 |\n"
                       "|---|---|---|---|---|---|---|---|---|\n")
                projects_methods = sorted({(str(r.get('project', 'unknown')),
                                           str(r.get('method', 'unknown'))) for r in group})
                for project, method in projects_methods:
                    members = [r for r in group if str(r.get('project', 'unknown')) == project
                               and str(r.get('method', 'unknown')) == method]
                    fixed, adjusted = average_labels(members)
                    cats = [sum(categories_by_name(r).get(name, {}).get('category_score', 0)
                                for r in members) / len(members) for name in CATEGORY_NAMES]
                    md += table_row([project, method, fixed, len(members), adjusted,
                                     *[f'{value:.1f}' for value in cats]])
            else:
                md += ("| Project | Method | Fixed Score (%) | Adjusted Score (%) | Cat1 | Cat2 | Cat3 | Cat4 | Top Question | Weakest Question | D4D File | Evaluation File | Evaluation Time |\n"
                       "|---|---|---|---|---|---|---|---|---|---|---|---|---|\n")
                for result in group:
                    bases = bases_of(result)
                    cats = categories_by_name(result)
                    excluded = set(exclusions_of(result) or ())
                    questions = [q for q in questions_of(result)
                                 if q.get('score') is not None and q.get('max_score', 0) > 0
                                 and f"Q{q['id']}" not in excluded]
                    def question_label(question):
                        return (f"Q{question['id']}: {question['name'][:20]}... "
                                f"({question['score']}/{question['max_score']})")
                    if questions:
                        ratio = lambda q: q['score'] / q['max_score']
                        top = question_label(max(questions, key=ratio))
                        weak = question_label(min(questions, key=ratio))
                    else:
                        top = weak = 'N/A'
                    md += table_row([
                        result.get('project', 'unknown'), result.get('method', 'unknown'),
                        f'{bases.total:g}/{bases.fixed_max:g} ({bases.fixed_percentage:.1f}%)',
                        adjusted_label(result),
                        *[cats.get(name, {}).get('category_score', 0) for name in CATEGORY_NAMES],
                        top, weak, result.get('d4d_file', ''), result.get('_evaluation_file', 'unrecorded'),
                        result.get('evaluation_timestamp', 'unrecorded'),
                    ])
            md += '\n'

    md += ('## Top Performing D4Ds (Fixed Score >= 80%)\n\n'
           'Up to 20 evaluations per cohort, ranked by total/fixed maximum; '
           'ties use the stable evaluation identity order.\n')
    for key, group in cohorts:
        ranked = sorted((r for r in group if bases_of(r).fixed_percentage >= 80),
                        key=lambda r: (-bases_of(r).fixed_percentage, result_order(r)))
        if not ranked:
            continue
        md += '\n' + cohort_description(key, len(group))
        md += '| Project | Method | Type | Fixed Score (%) | D4D File | Evaluation File |\n|---|---|---|---|---|---|\n'
        for result in ranked[:20]:
            bases = bases_of(result)
            md += table_row([result.get('project', 'unknown'), result.get('method', 'unknown'),
                             key.kind, f'{bases.total:g}/{bases.fixed_max:g} ({bases.fixed_percentage:.1f}%)',
                             result.get('d4d_file', ''), result.get('_evaluation_file', 'unrecorded')])
    return md


def create_markdown_table(results: List[Dict]):
    md_path = EVAL_DIR / 'summary_table.md'
    md_path.write_text(_markdown_table_text(results), encoding='utf-8')
    print(f'Markdown table created: {md_path}')


def _detailed_report_text(results: List[Dict]):
    """All aggregates and discrimination use the same recorded cohort identity."""
    report = ('# Rubric20 Detailed Evaluation Report\n\n'
              f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
              f'**Total Evaluations:** {len(results)}\n\n' + cohort_note(results))
    report += '## Executive Summary\n\n'
    cohorts = summary_cohorts(results)
    for key, group in cohorts:
        report += cohort_description(key, len(group))
        fixed, adjusted = average_labels(group)
        percentages = [bases_of(r).fixed_percentage for r in group]
        report += (f'- **Average Fixed Score:** {fixed}\n'
                   f'- **Average Adjusted Score:** {adjusted}\n'
                   f'- **Best Fixed Score:** {max(percentages):.1f}%\n'
                   f'- **Worst Fixed Score:** {min(percentages):.1f}%\n\n')

    for field, heading in (('method', 'Method Comparison'), ('project', 'Project Comparison')):
        report += f'## {heading}\n\n'
        for key, group in cohorts:
            report += cohort_description(key, len(group))
            for name in sorted({str(r.get(field, 'unknown')) for r in group}):
                members = [r for r in group if str(r.get(field, 'unknown')) == name]
                count = len(members)
                fixed, adjusted = average_labels(members)
                report += (f'#### {cell(name)}\n- Evaluations: {count}\n'
                           f'- Average fixed score: {fixed} over {count} evaluation(s)\n'
                           f'- Average adjusted score: {adjusted}\n\n')

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
        kind, maximum = key.kind, key.fixed_max
        who = evaluator_name(group[0])
        report += cohort_description(key, len(group))
        if key.score_mode == 'adjustment_unrecorded' or key.exclusions == 'null':
            report += ('## Item discrimination and within-project orderings\n\n'
                       'Withheld: adjusted basis or excluded-item identities are unrecorded; '
                       'equal maxima alone do not establish applicability comparability.\n\n')
            continue
        if key.score_mode == 'legacy_fixed_only':
            report += ('The legacy fixed-only records below have no recorded N/A adjustment. '
                       'The discrimination helper’s adjusted column equals its fixed column '
                       'arithmetically; it is not a separately recorded adjusted measurement.\n\n')
        others = len(results) - len(group)
        measured_on = (f'{len(group)} of the {len(results)} evaluations above: the {kind} '
                       f'evaluations by {who} scored out of {maximum:g}, '
                       'with the recorded rubric and evaluator settings stated immediately above'
                       + (f'. The other {others} are in no count in this block' if others else ''))
        report += '\n'.join(render_discrimination(
            discrimination(legacy_record(r) for r in group),
            scope=f', {kind} evaluations by {who} scored out of {maximum:g}',
            evaluator=who, measured_on=measured_on)) + '\n'

    return report


def create_detailed_report(results: List[Dict]):
    report_path = EVAL_DIR / 'summary_report.md'
    report_path.write_text(_detailed_report_text(results), encoding='utf-8')
    print(f'Detailed report created: {report_path}')


def _disclosed_inputs(evaluation_root, bindings, disclosure_root):
    """Keep raw-byte identities separate from loader-only record-kind tags."""
    from data_sheets_schema.model_disclosure import build_report

    captured = []
    for kind, pattern in (("individual", "individual/**/*_evaluation.json"),
                          ("concatenated", "concatenated/*_evaluation.json")):
        for path in sorted(evaluation_root.glob(pattern)):
            resolved = path.resolve()
            raw = path.read_bytes()
            original = json.loads(raw)
            if not isinstance(original, dict):
                raise ValueError(f'{path}: expected an evaluation object')
            # These two keys belong to the summary, never the evaluator's
            # original type declarations or the disclosure authority (#4314).
            result = {**original, 'evaluation_type': kind,
                      '_evaluation_file': path.relative_to(evaluation_root).as_posix()}
            captured.append((result, path, str(resolved), hashlib.sha256(raw).hexdigest()))
    if not captured:
        raise ValueError('no evaluation results found')
    captured.sort(key=lambda row: result_order(row[0]))
    disclosure = build_report([row[1] for row in captured], bindings=bindings,
                              root=disclosure_root)
    results, by_file = [], {}
    for (result, path, resolved, digest), declared in zip(captured, disclosure['rows'], strict=True):
        if (declared['evaluation_resolved_path'] != resolved or
                declared['evaluation_sha256'] != digest):
            raise ValueError(f'{path}: evaluation changed between score and disclosure capture')
        results.append(result)
        by_file[result['_evaluation_file']] = declared
    return results, disclosure, by_file


def _disclosure_appendix(results, disclosure):
    from data_sheets_schema.model_disclosure import render

    text = ['\n## Model disclosure cohort membership\n\n',
            'Each rating below belongs to the exact existing summary cohort stated here. '
            'Family labels do not change scores, grouping, membership or ordering. '
            'An aggregate has no single member’s generator or same-family claim.\n\n',
            '| Disclosure rating | Evaluation file | Resolved evaluation | Evaluation SHA256 | Summary cohort |\n',
            '|---|---|---|---|---|\n']
    for result, declared in zip(results, disclosure['rows'], strict=True):
        text.append(table_row([declared['rating'], result['_evaluation_file'],
                               declared['evaluation_resolved_path'], declared['evaluation_sha256'],
                               json.dumps(cohort_key(result)._asdict(), sort_keys=True, ensure_ascii=False)]))
    text.append('\n')
    text.append('\n'.join('#' + line if line.startswith('#') else line
                          for line in render(disclosure).rstrip('\n').splitlines()) + '\n')
    return ''.join(text)


def write_disclosed_summaries(evaluation_root: Path, output_dir: Path, *,
                              generation_bindings=(), disclosure_root: Path | None = None):
    """Publish a declared-v1 summary set exclusively, retaining partial failures.

    All source captures and report contents are validated before directory
    creation. A publication race leaves any new partial outputs as evidence;
    neither existing files nor another writer's files are removed or replaced.
    """
    evaluation_root, output_dir = Path(evaluation_root), Path(output_dir)
    if output_dir.exists() or output_dir.is_symlink():
        raise ValueError('model disclosure output directory must be new')
    results, disclosure, by_file = _disclosed_inputs(
        evaluation_root, generation_bindings, disclosure_root)
    appendix = _disclosure_appendix(results, disclosure)
    texts = {'all_scores.csv': _csv_summary_text(results, disclosure_rows=by_file),
             'summary_table.md': _markdown_table_text(results) + appendix,
             'summary_report.md': _detailed_report_text(results) + appendix}
    # mkdir without exist_ok also refuses late symlinks or existing directories.
    output_dir.mkdir()
    for name, text in texts.items():
        with (output_dir / name).open('x', encoding='utf-8', newline='') as stream:
            stream.write(text)
    return {'policy': 'declared-v1', 'ratings': len(results),
            'outputs': {name: str(output_dir / name) for name in texts}}


def _legacy_main():
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


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--model-disclosure', choices=('declared-v1',))
    parser.add_argument('--evaluation-root', type=Path,
                        help='rubric20 evaluation directory; same legacy membership rules')
    parser.add_argument('--output-dir', type=Path, help='new directory for the opt-in summaries')
    parser.add_argument('--generation-binding', nargs=3, action='append', type=Path,
                        metavar=('EVALUATION', 'INPUT', 'PROVENANCE'))
    parser.add_argument('--disclosure-root', type=Path,
                        help='explicit root for paths recorded inside generation evidence')
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
    except (ValueError, OSError) as exc:
        parser.error(str(exc))
    print(json.dumps(result, sort_keys=True))


if __name__ == '__main__':
    main()
