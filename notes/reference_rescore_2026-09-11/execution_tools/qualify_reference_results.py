"""Apply the dated Q19 errata to derived reports without changing measurements.

Run from the repository root after regenerating results or the completion summary.
The registered runner and evaluator definitions remain frozen.
"""
import hashlib
import json
from pathlib import Path
import re
import runpy
import sys


START = '<!-- Q19 semantic qualification:start -->'
END = '<!-- Q19 semantic qualification:end -->'
LINK = '[Q19 erratum](semantic_errata.md)'


def qualify(root: Path) -> None:
    plan = root / 'notes/reference_rescore_2026-09-11'
    errata = json.loads((plan / 'semantic_errata.json').read_bytes())
    assert hashlib.sha256((plan / 'manifest.json').read_bytes()).hexdigest() == errata['manifest_sha256']
    cases = errata['cases']
    assert len(cases) == errata['ratings_inspected'] == 24
    assert len({c['job_id'] for c in cases}) == len(cases)
    for case in cases:
        assert hashlib.sha256((root / case['output']).read_bytes()).hexdigest() == case['evaluation_sha256']
        assert hashlib.sha256((root / case['input']).read_bytes()).hexdigest() == case['input_sha256']
    flagged = [c for c in cases if c['status'] == 'requires_adjudication']
    assert len(flagged) == errata['ratings_requiring_adjudication']
    count = len(flagged)
    banner = (
        f'{START}\n'
        f'**Semantic qualification — Q19:** {count} rubric20 rationales contain '
        'representation-related objections requiring adjudication under the frozen text-or-graph rule. '
        'Their Q19 values, recorded totals and summaries containing them are unadjudicated model measurements. '
        'Mechanical acceptance does not certify semantic adherence. No scores were corrected or rerated. '
        f'See the {LINK}, including the full 24-rating inspection and its limits. '
        'Rubric10 repeatability is unaffected by this Q19 erratum.\n'
        f'{END}\n\n'
    )

    def add_banner(text: str) -> str:
        text = re.sub(re.escape(START) + r'.*?' + re.escape(END) + r'\n*', '', text, flags=re.S)
        title, rest = text.split('\n', 1)
        return title + '\n\n' + banner + rest.lstrip('\n')

    report_path = plan / 'results.json'
    report = json.loads(report_path.read_bytes())
    assert report['completed'] == report['planned'] == 56 and not report['pending']
    report['semantic_qualification'] = {
        'issue': errata['issue'], 'source': 'semantic_errata.json',
        'interpretation': errata['qualification'],
        'affected_evaluations': [c['output'] for c in flagged],
        'affected_job_ids': [c['job_id'] for c in flagged],
    }
    report_path.write_text(json.dumps(report, indent=2) + '\n')

    path = plan / 'results.md'
    text = path.read_text().replace(str(root) + '/', '')
    for case in flagged:
        plain = f"| {case['output']} |"
        marked = f"| {case['output']} {LINK} |"
        assert plain in text or marked in text, case['job_id']
        text = text.replace(plain, marked)
    groups = {}
    for case in flagged:
        groups.setdefault((case['project'], case['cohort']), []).append(case['generation_rep'])
    for (project, cohort), reps in groups.items():
        plain = f'| {project} | {cohort} | rubric20-semantic |'
        label = ','.join(f'rep{rep}' for rep in sorted(reps))
        marked = f'| {project} | {cohort} | rubric20-semantic [Q19 erratum: {label}](semantic_errata.md) |'
        assert plain in text or marked in text, (project, cohort)
        text = text.replace(plain, marked)
    path.write_text(add_banner(text))

    path = plan / 'completion_summary.md'
    text = path.read_text()
    for case in flagged:
        record = f"{case['project']} {case['cohort']} rep{case['generation_rep']}"
        text = text.replace(f'| {record} |', f'| {record} {LINK} |')
    path.write_text(add_banner(text))

    lines = [
        '# Q19 semantic errata for the recorded reference measurements', '',
        f"Recorded {errata['recorded_at']} for #{errata['issue']} after review of `{errata['reviewed_measurement_commit']}`.", '',
        errata['scope'], '', errata['qualification'], '',
        f"The [frozen Q19 rule](../../{errata['rule_path']}#L{errata['rule_line']}) permits complete textual provenance as well as a W3C PROV-O graph. Definition SHA256: `{errata['definition_sha256']}`.", '',
        f'{count} of the 24 inspected rationales are flagged. Some combine a representation objection with separate claims about missing relationships, identifiers, versioning or quality. This inspection does not determine whether the recorded Q19 score or total would change after adjudication. It does not establish that the other {len(cases) - count} Q19 scores, other questions, or external source claims are correct.', '',
        'The two original VOICE findings are supported directly by supplied input text: v7 rep3 maps named software to generated feature families at lines 722–731 and links the released features to standardized audio through b2aiprep at lines 780–782. The v7 rep1 external-resource description at lines 935–938 identifies the same raw-waveform-to-feature conversion. The original claim that structured or programmatically traversable provenance is required conflicts with the permitted textual form.', '',
        'All original ratings, candidates, prompts, transcripts, receipts, input bytes and instrument files remain unchanged. The 56-rating completion audit and original-Write binding describe mechanical acceptance and evidence integrity. No replacement scores, point additions, model calls or new instrument are introduced by this erratum.', '',
        '## Full Q19 rationale inspection', '',
        '| Record | Q19 | Recorded total /88 | Inspection status | Evidence |',
        '|---|---|---|---|---|',
    ]
    for case in cases:
        status = 'Requires adjudication' if case in flagged else 'Not flagged by this inspection'
        lines.append(f"| {case['job_id']} | {case['q19_score']} | {case['recorded_total_points']} | {status} | [Q19 rationale](../../{case['output']}#L{case['q19_line']}) |")
    for case in flagged:
        lines += ['', f"## {case['job_id']}", '', case['assessment'], '',
                  f"Recorded Q19: {case['q19_score']}/5; recorded total: {case['recorded_total_points']}/88. These values are preserved, not adjudicated.", '',
                  'Evaluator quality note:', '', '> ' + case['q19_quality_note'], '',
                  'Evaluator semantic analysis:', '', '> ' + case['q19_semantic_analysis'], '',
                  'Supplied input sections: ' + ', '.join(f"[{field['field']}](../../{case['input']}#L{field['line']})" for field in case['input_fields']) + '.', '',
                  f"Evaluation SHA256: `{case['evaluation_sha256']}`. Input SHA256: `{case['input_sha256']}`."]
    lines += ['', '## Regenerating the qualified reports', '',
              'From the repository root, run `python notes/reference_rescore_2026-09-11/execution_tools/qualify_reference_results.py --rebuild` to regenerate the reports with the frozen reporting code and then apply the errata in the same operation. With no flag, this command qualifies already-generated reports. Directly running the original registered report command alone produces its historical unqualified format; apply this qualifier before using that output. The qualifier checks the recorded input/output hashes and adds labels and metadata to derived reports; it does not change numeric arrays or original measurements. The structured annotation is [semantic_errata.json](semantic_errata.json).', '']
    (plan / 'semantic_errata.md').write_text('\n'.join(lines))
    print(f'Qualified {count} Q19 measurements and {len(groups)} generation-replicate rows; scores unchanged.')


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--rebuild', action='store_true', help='Regenerate frozen reports before applying errata.')
    args = parser.parse_args()
    root = Path.cwd()
    if args.rebuild:
        sys.path[:0] = [str(root / 'src'), str(root / 'scripts')]
        import reference_rescore as runner
        manifest = json.loads((runner.PLAN / 'manifest.json').read_bytes())
        runner.verify_frozen(manifest)
        runner.report_results(manifest)
        runpy.run_path(str(Path(__file__).with_name('write_reference_completion.py')), run_name='__main__')
    qualify(root)
