"""Audit and report D148 manifest integration continuation, 2026-11-14.

Inputs: accepted base, owner commits and isolated scratch cohorts. Outputs: JSON
and generated Markdown evidence; optionally prepend the answer-first continuation
to the lead's original handoff. No production imports, network or GitHub writes.
"""
import argparse
import ast
import hashlib
import json
from pathlib import Path
import re
import runpy
import shlex
import subprocess
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
BASE = 'bc2553d8448e0c5664bd6176470f0dc86f5e0390'
CANDIDATE = '8b0cda9085fbc5a14a9270a3dd703cdee9a557e2'
OWNER = 'fe0267e77cab7dfac4e513fc2d8f1bc63251757d'
STAGES = ('manifest', 'manifest-boundaries', 'registration', 'builder', 'retention', 'scanner')
OWNER_COMMITS = {
    'a3a79c06f': 'v3 preparation/execution and manifest propagation',
    '6a4f1ece8': 'bytecode fixture and census transition; superseded by b7003f2a6',
    'eba669867': 'stable metadata, directory and payload census',
    '972789574': 'manifest CLI and dispatch test',
    'ecb628c68': 'restore caller import roots before yielding verified helpers',
    '89aec8288': 'fresh installed payload verification',
    '1ecab7ef1': 'manifest remains v1; single-pass payload identity rechecks',
    'e82ef8a75': 'unowned-file census and explicit excluded roots',
    'b7003f2a6': 'exclude all pyc payload and unowned cache entries',
    '8529be7a1': 'v3 registration, execution and carrier fixtures',
    '69d1cd8ee': 'explicit synthetic bootstrap metadata; retained in continuation runner',
    '8aeb19e0b': 'shared and retention fixtures carry the manifest',
    '36dbca6f8': 'dispatch fixture stays outside capture authority setup',
    '9afd6d64a': 'live metadata drift test preserves registered manifest bytes',
    '0bbc0e438': 'retention module isolation retained from candidate',
}
GATE_COMMITS = ('ecbc7d737', '994ac2ea0', '719d2d226', '28e6d5688', '1b5629f0f')


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def git(*args):
    return subprocess.check_output(['git', '--no-replace-objects', *args], cwd=ROOT)


def at(commit, path):
    return git('show', commit + ':' + path)


def save(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')


def ancestor(commit):
    result = subprocess.run(['git', 'merge-base', '--is-ancestor', commit, 'HEAD'], cwd=ROOT)
    assert result.returncode in (0, 1)
    return result.returncode == 0


def bootstrap(raw):
    function = next(n for n in ast.parse(raw).body
                    if isinstance(n, ast.FunctionDef) and n.name == 'make_test_venv')
    start = next(i for i, n in enumerate(function.body) if isinstance(n, ast.Assign)
                 and isinstance(n.targets[0], ast.Name) and n.targets[0].id == 'metadata')
    end = next(i for i, n in enumerate(function.body) if isinstance(n, ast.Assign)
               and isinstance(n.targets[0], ast.Name) and n.targets[0].id == 'python')
    return [ast.dump(n, include_attributes=False) for n in function.body[start:end]]


def audit():
    helpers = runpy.run_path(str(ROOT / 'scripts/adhoc/audit_manifest_integration_pins_20261114.py'))
    constants, scan = helpers['constants'], helpers['SCAN']
    old_nodes, old_value = constants(at(BASE, scan))
    nodes, value = constants((ROOT / scan).read_bytes())
    rows = []
    for name in (*helpers['SUMMARIES'], '_NATIVE_V3_RENDER_SOURCES'):
        old = old_value(old_nodes[name]) if name in old_nodes else {}
        for path, pin in value(nodes[name]).items():
            actual = sha((ROOT / path).read_bytes())
            historical = name == '_NATIVE_V2_RENDER_SOURCES'
            assert historical or pin == actual, (name, path, pin, actual)
            rows.append({'summary': name, 'path': path, 'before': old.get(path),
                         'after': pin, 'actual': actual, 'historical': historical})
    constant_rows = []
    for path, name, target in helpers['CONSTANTS']:
        b, be = constants(at(BASE, path)); a, ae = constants((ROOT / path).read_bytes())
        row = {'path': path, 'name': name, 'target': target, 'before': be(b[name]),
               'after': ae(a[name]), 'actual': sha((ROOT / target).read_bytes())}
        assert row['after'] == row['actual']
        assert name == 'REVIEWED' or row['before'] == row['after']
        constant_rows.append(row)
    protected = {p: {'candidate': sha(at(CANDIDATE, p)), 'current': sha((ROOT / p).read_bytes())}
                 for p in helpers['PROTECTED']}
    assert all(row['candidate'] == row['current'] for row in protected.values())
    manifests = {}
    for version in ('v1', 'v2'):
        path = f'src/data_sheets_schema/native_controller_sources_{version}.json'
        raw = (ROOT / path).read_bytes()
        assert raw == at(CANDIDATE, path)
        manifests[path] = sha(raw)
    approval_path = 'tests/fixtures/native_d128_approved.json'
    raw = (ROOT / approval_path).read_bytes()
    assert raw == at(CANDIDATE, approval_path)
    d128 = {'fixture_sha256': sha(raw), 'assets': [
        {'path': path, 'approved': pin, 'candidate': sha(at(CANDIDATE, path)),
         'accepted_base': sha(at(BASE, path)), 'current': sha((ROOT / path).read_bytes())}
        for path, pin in json.loads(raw)['tool_assets_sha256'].items()]}
    owner_rows = []
    reconciled = {'src/data_sheets_schema/native_execution_registration_v2.py': 'candidate CI roster',
                  'src/data_sheets_schema/native_shared_authority_wire.py': 'candidate controller pin',
                  'tests/test_native_incomplete_retention.py': 'candidate module isolation',
                  'src/data_sheets_schema/native_shared_registration_orchestration.py': 'candidate pre-dispatch timing wrapper',
                  'tests/test_native_execution_registration_v2.py': 'candidate explicit offline AC host fixture',
                  'tests/test_native_failure_publication.py': 'candidate host-observation failure coverage',
                  'tests/test_native_shared_execution.py': 'candidate helper-cache exclusion assertion'}
    for commit, meaning in OWNER_COMMITS.items():
        assert ancestor(commit), commit
        paths = git('diff-tree', '--no-commit-id', '--name-only', '-r', commit).decode().splitlines()
        kept = [p for p in paths if p.startswith(('src/', 'tests/')) or p == 'scripts/native_environment_manifest.py']
        evidence = []
        for path in kept:
            raw = (ROOT / path).read_bytes()
            owner_raw = at(OWNER, path)
            assert raw == at(BASE, path), ('owner change altered during continuation', path)
            assert raw == owner_raw or path in reconciled, path
            evidence.append({'path': path, 'current_sha256': sha(raw), 'owner_sha256': sha(owner_raw),
                             'disposition': 'exact owner final bytes' if raw == owner_raw else reconciled[path]})
        owner_rows.append({'commit': git('rev-parse', commit).decode().strip(), 'meaning': meaning,
                           'ancestor': True, 'retained_code_and_tests': evidence,
                           'excluded_helpers': [p for p in paths if p not in kept]})
    runner = 'scripts/adhoc/run_manifest_continuation_tests_20261114.py'
    owner_runner = 'scripts/adhoc/run_h3_environment_tests_20261113.py'
    assert bootstrap((ROOT / runner).read_bytes()) == bootstrap(at('69d1cd8ee', owner_runner))
    gates = {commit: ancestor(commit) for commit in GATE_COMMITS}
    assert not any(gates.values())
    pth = ROOT.parents[1] / 'data-sheets-schema/.venv/lib/python3.13/site-packages/data_sheets_schema.pth'
    pth_hash = sha(pth.read_bytes())
    assert pth_hash == '56826535cb8408ac3c905c231aa18fc41627167d31bf06a359b406fe730ec116'
    git('diff', '--check', BASE, 'HEAD')
    return {'head': git('rev-parse', 'HEAD').decode().strip(), 'accepted_base': BASE,
            'pins': rows, 'constants': constant_rows, 'protected': protected,
            'controller_manifests': manifests, 'd128': d128, 'owner_commits': owner_rows,
            'bootstrap_matches_owner_commit': '69d1cd8ee', 'gate_commits_present': gates,
            'primary_pth_sha256': pth_hash,
            'diff_check': {'before': BASE, 'after': 'HEAD', 'passed': True},
            'commits': git('log', '--format=%H %s', BASE + '..HEAD').decode().splitlines()}


def cohorts(scratch):
    results = {}
    for directory in sorted(scratch.iterdir()):
        if not directory.is_dir() or not (directory / 'outcome.json').exists():
            continue
        outcome = json.loads((directory / 'outcome.json').read_bytes())
        plan = json.loads((directory / 'plan.json').read_bytes())
        xml = directory / 'pytest.xml'
        counts = dict(passed=0, failed=0, errors=0, skipped=0)
        cases = []
        junit_seconds = None
        if xml.exists():
            tree = ET.parse(xml)
            junit_seconds = sum(float(suite.get('time', '0')) for suite in tree.iter('testsuite'))
            for case in tree.iter('testcase'):
                child = next((n for n in case if n.tag in ('failure', 'error', 'skipped')), None)
                status = {'failure': 'failed', 'error': 'errors', 'skipped': 'skipped'}.get(
                    child.tag if child is not None else None, 'passed')
                counts[status] += 1
                if child is not None:
                    cases.append({'case': case.get('classname', '') + '::' + case.get('name', ''),
                                  'status': status, 'message': child.get('message', ''),
                                  'detail': child.text or ''})
        results[directory.name] = {'path': str(directory), 'counts': counts, 'outcome': outcome,
                                   'junit_available': xml.exists(),
                                   'junit_seconds': junit_seconds,
                                   'nonpassing': cases,
                                   'source_commit': plan['source_commit'], 'workers': plan['workers']}
    return results


def markdown(data, results, scratch):
    final = {stage: results.get('final-' + stage) for stage in STAGES}
    resume = data.get('registration_resume')
    pending = [stage for stage, row in final.items()
               if (row is None or not row['junit_available'] or not row['outcome']['cleanup_verified'])
               and not (stage == 'registration' and resume and resume['all_cases_completed'])]
    acceptance_rows = [*final.values(), results.get('final-registration-resumed')]
    expected_d128 = ('tests.test_native_d128_scanner_comparison::'
                     'test_d128_final_composition_has_only_the_finite_approved_scanner_differences')
    unexpected = [case for row in acceptance_rows if row for case in row['nonpassing']
                  if case['status'] != 'skipped' and case['case'] != expected_d128]
    retention = final['retention']
    stale_retention = [case for case in retention['nonpassing']
                       if case['status'] == 'failed' and case['message'] ==
                       'ValueError: subscription observation is stale or future-dated'] if retention else []
    verdict = ('Required verification is still incomplete.' if pending else
               'All required stages were rerun; verification has additional failures.' if unexpected else
               'All required cases completed; the inherited D128 approval hold and the initial registration timeout remain recorded.'
               if resume else 'All required stages completed; only the inherited D128 approval hold remains.')
    if stale_retention:
        verdict += (f" Retention has {retention['counts']['passed']} passes and "
                    f"{len(stale_retention)} failures at the existing capture-freshness check; "
                    'timing refresh remains excluded.')
    lines = ['Continuation — the accepted merge remains the base (2 resolved conflicts). '
             'The v3 CLI/preparer structural proof and its separate identity update are committed. '
             'The isolated prefix canary now persists the manifest and reaches the intended dependency stop. '
             + verdict + ' D128 approval remains the lead’s final-head step. '
             'The stage results below are the acceptance evidence.', '',
             f"Branch: `codex/native-manifest-integration-20261114`. Head: `{data['head']}`. "
             f'Worktree: `{ROOT}`. Evidence: `{scratch}`.', '',
             'The interpreter is Python 3.13.12 in each named cohort’s `venv`. The final cohorts use '
             'the declared-dependencies environment: the full installed RECORD payloads of the project’s '
             'declared runtime dependency closure plus pytest, xdist, packaging and psutil, copied at '
             'their primary installed versions without downloads or hard links. The plan, one-package '
             'copy canary and complete hash ledger are retained beside the cohorts. The manifest '
             'still performs its complete fresh payload and unowned-file census over the actual environment. '
             'The bootstrap adds the assigned source checkout and physical dependency site without '
             'executing dependency `.pth` files. '
             'Parent and ordinary child origin witnesses, OS network denial and observed-descendant '
             'cleanup are recorded per cohort. The primary environment was not modified. '
             'These are offline synthetic checks, not production registration or launch approval.', '',
             '| Stage/cohort | Workers | Passed | Failed | Errors | Skipped | Parent seconds | JUnit seconds | Cleanup verified | Evidence |',
             '| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |']
    for name, row in results.items():
        c, out = row['counts'], row['outcome']
        shown = [str(c[k]) if row['junit_available'] else 'unrecorded' for k in ('passed', 'failed', 'errors', 'skipped')]
        evidence = 'JUnit' if row['junit_available'] else 'no JUnit'
        if name == 'final-registration' and resume:
            shown = [str(resume['plan']['completed_log_passes']) + ' logged', '0 logged', '0 logged', '0 logged']
            evidence = 'partial pytest log; deadline, exit 124'
        elif name == 'registration-collection':
            evidence = 'collection only; no test execution'
        junit_time = f"{row['junit_seconds']:.2f}" if row['junit_seconds'] is not None else 'unrecorded'
        lines.append(f"| {name} | {row['workers']} | " + ' | '.join(shown) + ' | '
                     f"{out['seconds']:.2f} | {junit_time} | {out['cleanup_verified']} | {evidence} |")
    lines += ['', 'Parent elapsed time and pytest’s JUnit duration are preserved separately from their '
              'respective saved outputs. They are not interchangeable timing measurements; no performance '
              'comparison is inferred from their differences.']
    if stale_retention:
        preflight = sum('in preflight_current_selection' in case['detail'] for case in stale_retention)
        later = sum('in accept_current_selection' in case['detail'] for case in stale_retention)
        lines += ['', f"Retention finding: {len(stale_retention)} public-finalization cases raise "
                  '`ValueError: subscription observation is stale or future-dated`. '
                  f'{preflight} stop at `preflight_current_selection`; {later} reaches the later '
                  '`accept_current_selection` check after admission/controller preparation. '
                  'Their intended retention assertions are therefore not verified by this cohort. '
                  'The refusal remains intact. The saved synthetic guards and host pre-dispatch traces '
                  'record the observation times and the verification work preceding each refusal; '
                  'the exact stacks are retained in the JUnit and case ledger. '
                  'This is an additional unresolved finding for the lead’s issue filing, separate from D128. '
                  'The earlier instruction to leave timing refresh out still applies; no timestamp, '
                  'freshness limit or assertion was changed to obtain a pass. '
                  'Recommendation: handle verification/capture lifetime in a separate reviewed follow-up '
                  'before treating these public-finalization paths as verified.']
    if 'prefix-canary-builder-serial' in results:
        lines += ['', 'Builder verification uses one worker after a matching one-worker prefix canary. '
                  'Its subprocess checks retain their fixed timeouts, and its module-scoped full-chain '
                  'fixture is constructed once per worker. This avoids concurrent manifest censuses '
                  'within those subprocess limits and duplicate shared-fixture construction. The other '
                  'final execution cohorts use four workers. No timing improvement is claimed from '
                  'these differently scheduled cohorts.']
    if resume:
        p = resume['plan']
        lines += ['', f"Registration collected {p['collected']} exact cases. The first cohort logged "
                  f"{p['completed_log_passes']} passes before its {p['original_seconds']:.2f}-second deadline. "
                  f"The {len(p['pending_nodes'])} unfinished cases are the exact resume roster in "
                  '`registration-resume-plan.json`; input hashes and per-case statuses are in '
                  '`registration-coverage.json`. A logged completed case is distinguished from a JUnit result. '
                  'The original cohort remains a timeout, with forced cleanup and no observed surviving descendants; '
                  'it is not relabeled as a successful whole-suite run. '
                  + ('All collected cases have now passed across the original log and the clean resumed JUnit cohort.'
                     if resume['all_cases_passed'] else 'The complete resumed roster has not yet passed.'), '',
                  'This runtime limit is a finding for the lead’s issue filing. The continuation changes no test '
                  'assertion or production census to reduce it. Initial final-cohort source: '
                  f"`{p['initial_source_commit']}`. The later source differs only in the saved reporting helpers "
                  'and removal of the runner’s extra trailing blank line; production and test sources are unchanged. '
                  'The source-delta ledger is in `continuation-audit.json`.', '',
                  'Read-only review found the trailing blank line; it was corrected between cohorts. '
                  'Report review also restricted the inherited D128 exception to its exact comparison test. '
                  'These findings and the descriptor-barrier finding below are retained for the lead’s issue filing.']
    lines += ['', 'Every stage retains its exact command and environment in `plan.json` and '
              '`pytest-command.json`, with `pytest.log`, available `pytest.xml`, origin witnesses and `outcome.json`. '
              'All cohort results, including failed attempts, are retained in `continuation-results.json`.', '',
              'The initial broad-environment boundary cohort was deliberately interrupted after the '
              'helper-preservation case passed and while dispatch fixture construction was active. '
              'Its quiet-window lock was absent; retained artifacts showed progress. This partial run '
              'is not acceptance evidence and is not counted as zero failures. The final environment '
              'was separately canary-tested before rerunning the complete six-stage roster.', '',
              'The real prefix first exposed an audit-barrier defect: `os.fdopen` was rejected after '
              'exclusive manifest creation. The fix permits wrapping only the exact physical, single-link, '
              'read-only manifest inode under the new output directory. Other descriptors and descriptor '
              'chmod/truncate operations still refuse. The real prefix was re-canary-tested before the matrix. '
              'This finding is recorded here for the lead’s issue filing; no GitHub write was made.', '',
              'Changed/new scanner identities (historical v2 base pins remain unchanged):', '',
              '| Location | Before | After |', '| --- | --- | --- |']
    for row in data['pins']:
        if row['summary'] == '_NATIVE_V3_RENDER_SOURCES' and row['path'] not in (
                'src/data_sheets_schema/native_shared_authority_wire.py',
                'src/data_sheets_schema/native_environment_manifest.py'):
            continue
        if row['before'] != row['after']:
            lines.append(f"| {row['summary']}: {row['path']} | {row['before'] or 'new source contract'} | {row['after']} |")
    for row in data['constants']:
        if row['before'] != row['after']:
            lines.append(f"| {row['path']}: {row['name']} | {row['before']} | {row['after']} |")
    lines += ['', 'The complete identity ledger is `continuation-audit.json`. Controller manifests, '
              'SOURCES_SHA256, CONTROL_SHA and the four protected files still match the accepted candidate. '
              'The D128 approval fixture is unchanged; its original asset mismatch predates this '
              'continuation, and the scanner now also has the explicitly requested v3 changes.', '',
              '| Required owner commit | Retained change | Evidence |', '| --- | --- | --- |']
    for row in data['owner_commits']:
        description = '; '.join(sorted({e['disposition'] for e in row['retained_code_and_tests']}))
        if row['commit'].startswith('69d1cd8ee'):
            description = 'bootstrap AST matches the owner commit in the continuation runner'
        lines.append(f"| {row['commit']} | {row['meaning']} | {description} |")
    lines += ['', 'The owner changes remain in true-merge history and their final code/test bytes '
              'match the owner tree except the recorded candidate reconciliations. '
              'Superseded intermediate behavior is not reintroduced. Unneeded owner helpers remain '
              'excluded from the merge result; the bootstrap metadata change is implemented in '
              'the continuation runner. All five gate-package commits remain outside this branch.', '',
              'Continuation commits, newest first:', '', '```', *data['commits'], '```', '',
              'Reproduction (from the assigned worktree; choose a new output cohort each time):', '', '```bash',
              f'{scratch}/declared-dependencies/bin/python -S -P -B scripts/adhoc/run_manifest_continuation_tests_20261114.py \\',
              f'  --tree {ROOT} \\', f'  --out {scratch}/NEW-COHORT --workers WORKERS --timeout-seconds 14400 --stage STAGE',
              '```', '', 'STAGE is manifest, manifest-boundaries, registration, builder, retention or scanner. '
              'WORKERS is 1 for builder and 4 for the other execution stages. '
              'The runner uses the original explicit test-file roster. No assertion, production refusal, '
              'D128 approval or protected source was weakened.', '',
              'Report provenance:', '', '```bash',
              f'python -B scripts/adhoc/report_manifest_continuation_20261114.py --scratch {scratch}',
              '```', '']
    if resume:
        command = [str(scratch / 'declared-dependencies/bin/python'), '-S', '-P', '-B',
                   'scripts/adhoc/run_manifest_continuation_tests_20261114.py',
                   '--tree', str(ROOT), '--out', str(scratch / 'NEW-REGISTRATION-RESUME'),
                   '--workers', '4', '--timeout-seconds', '14400', *resume['plan']['pending_nodes']]
        lines += ['Registration coverage provenance and exact unfinished-case reproduction:', '', '```bash',
                  f'python -B scripts/adhoc/audit_manifest_registration_resume_20261114.py --scratch {scratch}',
                  shlex.join(command), '```', '']
    lines += ['Nonpassing cases (including retained failed canaries):', '']
    for name, row in results.items():
        for case in row['nonpassing']:
            lines.append(f"- {name}: `{case['case']}` — {case['status']}; {case['message']}")
    return '\n'.join(lines).replace('@', '&#64;') + '\n'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--scratch', type=Path, required=True)
    parser.add_argument('--handoff', type=Path)
    args = parser.parse_args()
    scratch = args.scratch.resolve(strict=True)
    assert scratch == ROOT.parent / 'scratch-native-manifest-integration-20261114/continuation'
    data, results = audit(), cohorts(scratch)
    if (scratch / 'registration-resume-plan.json').exists():
        resume_audit = runpy.run_path(str(ROOT / 'scripts/adhoc/audit_manifest_registration_resume_20261114.py'))['audit']
        resume = resume_audit(scratch)
        save(scratch / 'registration-coverage.json', resume)
        data['registration_resume'] = resume
        before = resume['plan']['initial_source_commit']
        delta = git('diff', '--name-only', before, 'HEAD').decode().splitlines()
        allowed = {'scripts/adhoc/audit_manifest_registration_resume_20261114.py',
                   'scripts/adhoc/report_manifest_continuation_20261114.py',
                   'scripts/adhoc/run_manifest_continuation_tests_20261114.py'}
        assert set(delta) <= allowed, ('verification source changed beyond reporting/formatting', delta)
        runner = 'scripts/adhoc/run_manifest_continuation_tests_20261114.py'
        assert at(before, runner).rstrip() == (ROOT / runner).read_bytes().rstrip()
        data['verification_source_delta'] = {'before': before, 'after': data['head'], 'paths': delta,
                                            'production_and_tests_unchanged': True}
    save(scratch / 'continuation-audit.json', data)
    save(scratch / 'continuation-results.json', results)
    report = markdown(data, results, scratch)
    (scratch / 'continuation.md').write_text(report)
    if args.handoff:
        assert all('final-' + stage in results for stage in STAGES), 'all six final stages must finish before handoff'
        original = scratch / 'accepted-base-handoff.md'
        if not original.exists():
            original.write_bytes(args.handoff.read_bytes())
        args.handoff.write_text(report + '\n---\n\nOriginal accepted-base handoff (historical):\n\n' + original.read_text())
        raw = args.handoff.read_bytes()
        assert b'@' not in raw
        # All literal absolute paths in the generated section must exist.
        paths = re.findall(r'`(/[^`]+)`', report)
        assert all(Path(path).exists() for path in paths), paths
        result = {'handoff': str(args.handoff), 'bytes': len(raw), 'sha256': sha(raw),
                  'original_sha256': sha(original.read_bytes()), 'checked_paths': paths}
        save(scratch / 'handoff-verification.json', result)
        print(json.dumps(result, indent=2))
    else:
        print(json.dumps({'audit': str(scratch / 'continuation-audit.json'),
                          'cohorts': {name: row['counts'] for name, row in results.items()}}, indent=2))


if __name__ == '__main__':
    main()
