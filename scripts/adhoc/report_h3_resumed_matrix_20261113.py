"""Codex197 handoff, 2026-11-13: read saved matrix and branch evidence.

Inputs: assigned branches, fixed case plan, saved cohorts and bounds measurement.
Outputs: JSON evidence and Markdown handoff; all tables are rendered from JSON.
No validator, provider, native binary or network call; final report verifier is
data-only and uses read-only Git queries. Existing evidence is never overwritten.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import subprocess
import xml.etree.ElementTree as ET

N = Path(__file__).resolve().parents[2]
E = N.parent
G = E / 'codex-native-pin-comparison-20261113'
R = E / 'codex-development-efficiency-20261111'
S = E / 'scratch-h3-resume-matrix-20261113'
OLD = E / 'scratch-h3-gate-refinements-20261113'
CURRENT = 'final-format-07'
HANDOFF = R / 'notes/development_efficiency_20261111/handoffs/codex-h3-final-format-matrix-20261113'
PROTECTED = ['src/data_sheets_schema/shared_generation.py', 'src/data_sheets_schema/api_runner.py',
             'src/download/prompts/canonical_hashes.yaml', 'tests/utils/run_spec_boundary_contracts.json']


def pin(path):
    path = Path(path)
    raw = path.read_bytes()
    return dict(path=str(path), bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())


def read(path):
    return json.loads(Path(path).read_bytes())


def git(root, *args):
    command = ['git', '--no-replace-objects', '-C', str(root), *args]
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    return dict(command=command, returncode=result.returncode, stdout=result.stdout, stderr=result.stderr)


def branch(root):
    commands = {
        'head': ['rev-parse', 'HEAD'], 'branch': ['branch', '--show-current'],
        'status': ['status', '--short', '--untracked-files=all'],
        'merge_base': ['merge-base', '4b1463bc7', 'HEAD'],
        'commits_after_handoff': ['log', '--since=2026-11-13T12:50:00Z', '--format=%H %cI %s'],
        'branch_commits': ['log', '--reverse', '--format=%H %s', '4b1463bc7..HEAD'],
        'production_commits': ['log', '--reverse', '--format=%H %s', '4b1463bc7..HEAD', '--', 'src', 'scripts/native_environment_manifest.py'],
        'files_from_common_base': ['diff', '--name-status', '4b1463bc7...HEAD'],
        'files_against_candidate': ['diff', '--name-status', '4b1463bc7', 'HEAD'],
        'protected': ['diff', '--exit-code', '4b1463bc7', 'HEAD', '--', *PROTECTED],
        'protected_worktree': ['diff', '--exit-code', '4b1463bc7', '--', *PROTECTED],
    }
    return {key: git(root, *args) for key, args in commands.items()}


def cohort(name):
    root = OLD / 'tests' / name
    rows = []
    if root.exists():
        for stage in sorted((root / 'stages').iterdir()):
            path = stage / 'outcome.json'
            row = dict(stage=stage.name, status='incomplete_no_outcome', evidence=[])
            if path.is_file():
                body = read(path)
                row.update(status=body.get('status'), cleanup_verified=body.get('cleanup_verified'), outcome=body)
            for name in ('inputs.json', 'outcome.json', 'result.json', 'stderr.log'):
                if (stage / name).is_file():
                    row['evidence'].append(pin(stage / name))
            rows.append(row)
    return rows


def bounds():
    directory = OLD / 'measurements/final-format-04-authority'
    rows = []
    for project in ('CHORUS', 'AI_READI', 'CM4AI', 'VOICE', 'VOICE_PEDIATRIC'):
        path = directory / (project + '.json')
        body = read(path)
        mismatches = []
        declarations = body['authority_files_including_environment'] + [body[k] for k in
            ('builder_report', 'preparation', 'registration', 'selection', 'environment_manifest')]
        for declared in declarations:
            try:
                if pin(declared['path']) != declared:
                    mismatches.append(declared['path'])
            except OSError as error:
                mismatches.append(str(error))
        total = sum(row['bytes'] for row in body['authority_files_including_environment'])
        if total != body['selection_authority_including_environment_bytes']:
            mismatches.append('declared total differs')
        rows.append(dict(project=project, total_bytes=total, environment=body['environment_manifest'],
                         threshold_bytes=body['threshold_bytes'], margin_bytes=body['threshold_bytes'] - total,
                         all_twelve_bounds_match=body['all_twelve_bounds_match_adopted'],
                         verified=not mismatches, mismatches=mismatches, source=pin(path)))
    return rows


def fresh_bounds():
    helper = R / 'scripts/adhoc/measure_h3_final_authority_20261113.py'
    api = dict(__name__='resumed_authority_readback', __file__=str(helper))
    exec(compile(helper.read_bytes(), str(helper), 'exec'), api)
    api['PACKETS'] = OLD / 'tests' / CURRENT / 'cases/test_final_format_registration0'
    adopted = {row['key']: row['proposed'] for row in read(N / 'scripts/adhoc/h3_gate_bounds_20261113.json')['bounds']}
    rows = []
    for project, role in api['PROJECTS']:
        report = api['PACKETS'] / (role + '-report.json')
        outcome_path = OLD / 'tests' / CURRENT / 'stages' / ('build-' + role) / 'outcome.json'
        if report.exists() and outcome_path.exists() and read(outcome_path).get('status') == 'passed' and read(outcome_path).get('cleanup_verified') is True:
            rows.append(api['project_row'](project, role, adopted))
    return dict(helper=pin(helper), packets_root=str(api['PACKETS']), rows=rows,
                complete=len(rows) == len(api['PROJECTS']),
                within_threshold=bool(rows) and all(row['within_lead_threshold'] for row in rows))


def verify_terminal(stage, demonstration):
    """Do not promote an aggregate before cleanup and postflight finish."""
    outcome = read(stage / 'outcome.json')
    if (outcome.get('status') != 'passed' or outcome.get('returncode') != 0
            or outcome.get('cleanup_verified') is not True
            or any(outcome.get(k) for k in ('proof_error', 'postflight_error', 'interrupted',
                                          'forced_cleanup', 'observed_surviving_pids', 'observation_errors'))):
        raise ValueError('full stage lacks successful cleanup/postflight')
    result_pin = pin(stage / 'result.json')
    if outcome.get('result') != result_pin or outcome.get('demonstration_proof') != pin(demonstration):
        raise ValueError('full outcome/result/demonstration pins differ')
    result = read(stage / 'result.json')
    if (result.get('status') != 'passed' or result.get('action') != 'full' or result.get('role') is not None
            or result.get('outputs') != {'demonstration': pin(demonstration)}
            or result.get('config') != pin(stage.parent.parent / 'stage-config.json')
            or result.get('side_effects') != dict(native_executions=0, model_calls=0, probes_executed=0, captures=0, reservations=0)):
        raise ValueError('full result configuration or outputs differ')
    return dict(status='verified', outcome=pin(stage / 'outcome.json'), result=result_pin)


def command_text(result, empty):
    if result['returncode']:
        return 'INSPECTION FAILED: ' + result['stderr']
    return result['stdout'].strip() or empty


def coverage_preflight():
    rows = []
    for role in ('reference', 'AI_READI', 'CM4AI', 'VOICE', 'VOICE_PEDIATRIC'):
        path = S / 'coverage' / (CURRENT + '-' + role + '.stdout.json')
        body = read(path)
        if pin(body['output']['path']) != body['output']:
            raise ValueError('coverage preflight artifact changed')
        rows.append(dict(role=role, summary=pin(path), **body))
    comparisons = []
    for role in ('AI_READI', 'CM4AI', 'VOICE', 'VOICE_PEDIATRIC'):
        path = S / 'coverage' / (CURRENT + '-reference-vs-' + role + '.stdout.json')
        body = read(path)
        if pin(body['output']['path']) != body['output']:
            raise ValueError('cross-field preflight artifact changed')
        comparisons.append(dict(role=role, summary=pin(path), **body))
    return dict(coverage=rows, comparisons=comparisons,
                readers=[pin(G / 'scripts/adhoc' / name) for name in
                         ('h3_gate_leaf_coverage_20261113.py', 'h3_gate_cross_fields_20261113.py')],
                scope='Data-only field coverage/comparison; no validators or gate workers; not full-matrix acceptance.')


def table(headers, rows):
    return '\n'.join(['| ' + ' | '.join(headers) + ' |', '| ' + ' | '.join(['---'] * len(headers)) + ' |'] +
                     ['| ' + ' | '.join(str(x).replace('|', '\\|') for x in row) + ' |' for row in rows])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--publish-handoff', action='store_true')
    args = parser.parse_args()
    plan_path = G / 'scripts/adhoc/h3_refinement_cases_20261113.json'
    plan = read(plan_path)
    demonstration = OLD / 'demonstrations' / (CURRENT + '-full') / 'demonstration-results.json'
    reporter = G / 'scripts/adhoc/h3_gate_addendum_report_20261113.py'
    namespace = dict(__name__='resumed_report_verifier', __file__=str(reporter))
    exec(compile(reporter.read_bytes(), str(reporter), 'exec'), namespace)
    final, verification, accepted = namespace['assess_final'](demonstration if demonstration.exists() else None)
    try:
        terminal = verify_terminal(OLD / 'tests' / CURRENT / 'stages/full', demonstration)
    except (OSError, ValueError, KeyError) as error:
        terminal = dict(status='held', error=str(error))
        accepted = False
    actual = {row['name']: row for row in (final or {}).get('cases', [])}
    cases = [dict(name=row['name'], expected=row['expected'], actual=actual.get(row['name'], {}).get('status', 'not_run'),
                  accepted=accepted and actual.get(row['name'], {}).get('status') == row['expected']) for row in plan['cases']]
    audit = {name: branch(root) for name, root in [('gate', G), ('environment', N)]}
    tests = []
    bytecode = N / 'scripts/adhoc/h3_bytecode_manifest_20261113.json'
    for name, item in read(bytecode)['cohorts'].items():
        xml = Path(item['xml']['path'])
        doc = ET.fromstring(xml.read_bytes())
        suites = [doc] if doc.tag == 'testsuite' else list(doc.findall('testsuite'))
        counts = {key: sum(int(s.get(key, 0)) for s in suites) for key in ('tests', 'failures', 'errors', 'skipped')}
        tests.append(dict(name=name, xml=pin(xml), counts=counts, pinned_xml_matches=pin(xml) == item['xml']))
    resume_tests = []
    for name in ('reporter-tests', 'barrier-tests'):
        path = S / (name + '.xml')
        doc = ET.fromstring(path.read_bytes())
        suites = [doc] if doc.tag == 'testsuite' else list(doc.findall('testsuite'))
        resume_tests.append(dict(name=name, xml=pin(path), log=pin(S / (name + '.log')),
            counts={key: sum(int(s.get(key, 0)) for s in suites) for key in ('tests', 'failures', 'errors', 'skipped')}))
    gate_tests = []
    for name in ('git-source-core-unit-02', 'rf25-driver-report-unit-02', 'private-import-unit-01', 'private-production-import-canary-01'):
        path = OLD / 'tests' / name / 'pytest.xml'
        doc = ET.fromstring(path.read_bytes())
        suites = [doc] if doc.tag == 'testsuite' else list(doc.findall('testsuite'))
        gate_tests.append(dict(name=name, xml=pin(path),
            counts={key: sum(int(s.get(key, 0)) for s in suites) for key in ('tests', 'failures', 'errors', 'skipped')}))
    value = dict(answer=dict(cases_accepted=sum(row['accepted'] for row in cases), total_cases=len(cases),
                            verifier=verification, terminal=terminal, branch_readiness='reviewable; integration acceptance pending'),
                 cases=cases, case_plan=pin(plan_path), reporter=pin(reporter), bounds=bounds(), fresh_bounds=fresh_bounds(), branches=audit,
                 cohorts={name: cohort(name) for name in ('final-format-04', 'final-format-05', 'final-format-06', CURRENT)},
                 saved_manifest_tests=tests, manifest_test_report=pin(bytecode),
                 saved_gate_tests=gate_tests,
                 coverage_preflight=coverage_preflight(),
                 resume_tests=resume_tests, review_findings=read(N / 'scripts/adhoc/h3_resumed_report_review_findings_20261113.json'),
                 resume_attempt_evidence=[pin(path) for path in sorted(S.glob('*.log'))] +
                     [pin(path) for path in sorted(S.glob('*-readback.json'))] +
                     [pin(path) for path in sorted(S.glob('attempt*/*-readback.json'))],
                 bounds_barrier_readbacks=[pin(S / ('barrier-readback-' + role + '.json')) for role in
                     ('reference', 'AI_READI', 'CM4AI', 'VOICE', 'VOICE_PEDIATRIC')],
                 script=pin(Path(__file__)), fresh_runner=pin(N / 'scripts/adhoc/resume_h3_matrix_20261113.py'),
                 duplication_check=git(G, 'diff', '--exit-code', 'codex/native-environment-manifest-20261113', 'HEAD', '--',
                     'src/data_sheets_schema/native_environment_manifest.py', 'tests/test_native_environment_manifest.py',
                     'tests/test_native_environment_dependencies.py', 'scripts/native_environment_manifest.py'))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('x') as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write('\n')
    value = read(args.output)
    if args.publish_handoff:
        n = value['answer']['cases_accepted']
        bounds_ok = all(row['verified'] and row['total_bytes'] <= row['threshold_bytes'] and row['all_twelve_bounds_match'] for row in value['bounds'])
        lines = [f'Matrix: {n} of {len(cases)} cases accepted by the complete-report verifier. '
                 f'Verifier status: {verification["status"]}. '
                 f'Bounds: saved five-project readback passes: {bounds_ok}; '
                 f'fresh cohort complete: {value["fresh_bounds"]["complete"]}, within threshold: {value["fresh_bounds"]["within_threshold"]}. '
                 'the table below reports independent readback, separate from matrix acceptance. '
                 'Branches are available for the lead’s independent reviews; integrated-candidate acceptance remains pending.', '',
                 'The prior final-format-04 cohort stopped at build-registered without a terminal outcome. '
                 'Its self-canary and completed builders are historical evidence, not an accepted matrix. '
                 'An initial resume bootstrap invocation used the underlying interpreter rather than the required dependency-venv spelling and was refused before cohort creation; its log is retained. '
                 'Fresh final-format-05 bootstrapped but nested sandbox setup failed. '
                 'Fresh final-format-06 was held after an orchestrator refinement made its captured launcher stale. '
                 f'Fresh {CURRENT} uses the existing network-denied builder/validator sandboxes through an escalated outer launch, '
                 'with an authority-size barrier after every main-cohort packet build and before subsequent stages. '
                 'No native binary, provider, model, probe, capture, reservation or GitHub operation was performed.', '',
                 'Verifier readback: ' + json.dumps(verification, sort_keys=True), '',
                 'Terminal cohort readback: ' + json.dumps(terminal, sort_keys=True), '',
                 table(['Case', 'Expected', 'Actual', 'Accepted'], [[r[k] for k in ('name', 'expected', 'actual', 'accepted')] for r in cases]), '',
                 'Selection authority totals below conservatively add the manifest once: its pin is held by preparation. '
                 'All referenced authority, preparation, registration, selection, builder-report and manifest bytes were reread. '
                 'These are the saved interrupted-cohort measurements requested in the assignment.', '',
                 table(['Project', 'Authority plus environment bytes', 'Environment bytes', 'Environment SHA-256', 'Margin', 'Readback verified'],
                       [[r['project'], r['total_bytes'], r['environment']['bytes'], r['environment']['sha256'], r['margin_bytes'], r['verified']] for r in value['bounds']]), '',
                 'Fresh-cohort bounds (only completed packet builders are included):', '',
                 table(['Project', 'Authority plus environment bytes', 'Environment SHA-256', 'Within threshold'],
                       [[r['project'], r['selection_authority_including_environment_bytes'], r['environment_manifest']['sha256'], r['within_lead_threshold']] for r in value['fresh_bounds']['rows']]), '',
                 'Restart and branch evidence:', '']
        for name, info in audit.items():
            lines += [name + ': ' + info['head']['stdout'].strip(), '',
                      'Commits since the prior handoff:', '```text', command_text(info['commits_after_handoff'], '(none)'), '```', '',
                      'Working-tree state (untracked files included):', '```text', command_text(info['status'], '(clean)'), '```', '',
                      'Changes against the candidate, from their common ancestor:', '```text', info['files_from_common_base']['stdout'].strip(), '```', '']
        lines += ['Both branches diverge from the candidate at ' + audit['gate']['merge_base']['stdout'].strip() +
                  '. Integrate commits, not whole trees: direct candidate-to-branch diffs also remove candidate-only changes. '
                  'The JSON twin retains both diff forms. Protected HEAD and worktree checks all pass: ' +
                  str(all(info[key]['returncode'] == 0 for info in audit.values() for key in ('protected', 'protected_worktree'))) +
                  '. No controller pins were rotated in this resume.', '',
                  'For canary registration, the environment branch supplies v3 preparation/execution and manifest propagation '
                  '(a3a79c06f), stability/ownership fixes (6a4f1ece8, eba669867), manifest CLI (972789574), restored import paths '
                  '(ecb628c68), payload verification followed by the version-1 correction (89aec8288 then 1ecab7ef1), '
                  'unowned-file census and bytecode exclusion (e82ef8a75 then b7003f2a6). Keep their fixture companions '
                  '(8529be7a1, 69d1cd8ee, 8aeb19e0b, 36dbca6f8, 9afd6d64a) and retention isolation 0bbc0e438. '
                  'The gate branch does not carry that retention fix.', '',
                  'Gate package support comprises reference-only validation context, actual host paths and HEAD checks '
                  '(ecbc7d737, 994ac2ea0, 719d2d226), canonical project receipt paths (28e6d5688), and carrier module identity '
                  '(1b5629f0f). Review these production-package changes separately. The comparison scripts and closed field '
                  'schema support equivalence verification; they are not needed to construct a v3 registration. '
                  'The adhoc builders, mutations, reports, measurement and stage orchestration are rehearsal tooling. '
                  'Every commit added during this resume is rehearsal, reporting or test tooling; none changes production registration code. '
                  'Avoid duplicate environment carries 64d327090, 5a9f08733 and 6c7237e44. The JSON records the exact duplicate-file check.', '',
                  'Saved manifest validation (historical selections, not summed and not integrated-candidate validation):', '',
                  table(['Cohort', 'Tests', 'Failures', 'Errors', 'Skipped', 'Pinned XML matches'],
                        [[r['name'], *[r['counts'][k] for k in ('tests', 'failures', 'errors', 'skipped')], r['pinned_xml_matches']] for r in tests]), '',
                  'Saved gate validation (historical focused controls; full-format acceptance is reported separately):', '',
                  table(['Cohort', 'Tests', 'Failures', 'Errors', 'Skipped'],
                        [[r['name'], *[r['counts'][k] for k in ('tests', 'failures', 'errors', 'skipped')]] for r in gate_tests]), '',
                  'Resume-tooling tests (overlapping selections, not summed):', '',
                  table(['Cohort', 'Tests', 'Failures', 'Errors', 'Skipped'],
                        [[r['name'], *[r['counts'][k] for k in ('tests', 'failures', 'errors', 'skipped')]] for r in resume_tests]), '',
                  'Fresh data-only coverage preflight, separate from full-matrix acceptance:', '',
                  table(['Packet', 'Leaves', 'Containers', 'Keys', 'Decoded carriers', 'Complete', 'Gaps', 'Unknown'],
                        [[r['role'], *[r['counts'][k] for k in ('leaves', 'containers', 'keys', 'decoded_carriers')], r['complete'], r['gaps'], r['unknown']]
                         for r in value['coverage_preflight']['coverage']]), '',
                  table(['Reference comparison', 'Field differences', 'Unknown'],
                        [[r['role'], r['differences'], r['unknown']] for r in value['coverage_preflight']['comparisons']]), '',
                  'The preflight does not establish production validation, tuple/floor validity or registration equivalence. '
                  'Its readers and exact output pins are retained in the JSON twin.', '',
                  'Local review findings for the lead to file under the no-GitHub-write assignment:', '',
                  table(['Finding', 'Priority', 'Problem', 'Disposition'],
                        [[r['id'], r['priority'], r['finding'], r['disposition']] for r in value['review_findings']['findings']]), '',
                  'The prior retention-prefix timeout remains nonacceptance. Capture/finalization controls remain unexecuted '
                  'under the assignment restriction. No full CI or integrated-candidate acceptance is claimed.', '',
                  'Every table was generated from the JSON evidence by this recorded command (exclusive output; '
                  'choose a new output filename for a rerun):', '```bash',
                  f'{E.parent / "data-sheets-schema/.venv/bin/python"} -I -S -B {Path(__file__)} --output {args.output} --publish-handoff', '```', '',
                  'Evidence: ' + str(args.output), '']
        raw = '\n'.join(lines)
        if chr(64) in raw:
            raise ValueError('handoff must not contain at-sign characters')
        HANDOFF.with_suffix('.md').write_text(raw)
        HANDOFF.with_suffix('.json').write_bytes(args.output.read_bytes())
        print(json.dumps({'handoff': pin(HANDOFF.with_suffix('.md')), 'json': pin(HANDOFF.with_suffix('.json'))}, sort_keys=True))
    else:
        print(json.dumps(pin(args.output), sort_keys=True))


if __name__ == '__main__':
    main()
