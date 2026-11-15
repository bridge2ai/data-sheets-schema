"""Focused final manifest integration checks and handoff, 2026-11-15.

Inputs: merged candidate f5c7c312f, authorized scanner identities, local physical
dependencies. Outputs: bounded cohort logs/JUnit, pin verifier output, identity
audit and a new top section in the assigned handoff for PR 5968. No live matrix.
"""
import argparse
import ast
import hashlib
import json
from pathlib import Path
import re
import runpy
import subprocess
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
MERGE = '38469f270ebb2f476c663d0640911d95ea73f504'
BEFORE = 'd6d26bf8c492d4b9dabfb1169760756425e0fa81'
CANDIDATE = 'f5c7c312f41e555c8023b880eeb3da327aa815cb'
SCRATCH = ROOT.parent / 'scratch-native-manifest-integration-20261114/continuation'
OUT = SCRATCH / 'final-merge-20261115'
HANDOFF = ROOT.parent / 'codex-development-efficiency-20261111/notes/development_efficiency_20261111/handoffs/codex-native-manifest-integration-20261114.md'
SCAN = '.claude/skills/d4d-generation-specificity-audit/scan.py'
AUTHORITY = 'src/data_sheets_schema/native_execution_authority_v2.py'
MANIFEST = 'src/data_sheets_schema/native_environment_manifest.py'
PREVIOUS = runpy.run_path(str(ROOT / 'scripts/adhoc/check_manifest_candidate_20261114.py'))
COHORTS = {name: nodes for name, nodes in PREVIOUS['cohorts']().items() if name not in ('scanner', 'canary')}
COHORTS = {'canary': ['tests/test_native_environment_scanner_modes.py::test_same_scanner_derives_historical_v2_and_current_v3'], **COHORTS,
    'scanner': ['tests/' + name + '.py' for name in (
        'test_native_environment_scanner_modes', 'test_native_u1_scanner_contracts',
        'test_native_u3l_scanner', 'test_native_u5_scanner', 'test_native_h1_scanner_authority',
        'test_native_u5_scanner_comparison', 'test_native_d128_scanner_comparison')],
    'ci-canary': ['tests/test_ci_sharding.py::test_failure_and_empty_selection_cannot_pass[False]'],
    'ci-sharding': ['tests/test_ci_sharding.py']}


def git(*args, check=True):
    return subprocess.run(['git', '--no-replace-objects', *args], cwd=ROOT,
                          capture_output=True, check=check)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def save(path, value):
    with path.open('x') as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write('\n')


def load(path):
    return json.loads(path.read_bytes())


def frozen():
    assert not git('status', '--porcelain').stdout
    assert git('merge-base', '--is-ancestor', MERGE, 'HEAD', check=False).returncode == 0
    return git('rev-parse', 'HEAD').stdout.decode().strip()


def cohort_out(name):
    return SCRATCH / ('final-merge-20261115-' + name)


def reporting_only_since(tested, delivery):
    changed = git('diff', '--name-only', tested, delivery).stdout.decode().splitlines()
    assert set(changed) <= {'scripts/adhoc/check_manifest_final_20261115.py'}, changed
    return changed


def completed_ci_nodes():
    log = (cohort_out('ci-sharding') / 'pytest.log').read_text()
    matches = re.findall(r'^(tests/test_ci_sharding\.py::.+) (PASSED|FAILED|ERROR|SKIPPED|XFAIL|XPASS) \[\s*\d+%\]$', log, re.M)
    assert matches and all(status == 'PASSED' for _, status in matches), matches
    nodes = [node for node, _ in matches]
    assert len(nodes) == len(set(nodes))
    return nodes


def resume_ci():
    """Resume only cases lacking a completed result after the bounded run."""
    head = frozen()
    tested = load(OUT / 'audit.json')['head']
    changed = reporting_only_since(tested, head)
    original = load(cohort_out('ci-sharding') / 'outcome.json')
    assert original['returncode'] == 124 and original['interrupted'] == 'deadline'
    assert not original['observed_surviving_pids'] and not original['observation_errors']
    canary = load(cohort_out('ci-canary') / 'outcome.json')
    assert canary['returncode'] == 0 and canary['cleanup_verified']
    assert load(cohort_out('ci-canary') / 'plan.json')['source_commit'] == tested
    base = [str(SCRATCH / 'declared-dependencies/bin/python'), '-S', '-P', '-B',
            str(ROOT / 'scripts/adhoc/run_manifest_continuation_tests_20261114.py'),
            '--tree', str(ROOT), '--workers', '0', '--timeout-seconds', '3600']
    directory = cohort_out('ci-remaining-collect')
    command = [*base, '--out', str(directory), '--collect-only', 'tests/test_ci_sharding.py']
    save(OUT / 'ci-remaining-collect-launch.json', {'head': head, 'command': command})
    result = subprocess.run(command, cwd=ROOT)
    assert result.returncode == 0 and load(directory / 'outcome.json')['cleanup_verified']
    log = (directory / 'pytest.log').read_text()
    count = int(re.search(r'collected (\d+) items', log).group(1))
    nodes = ['tests/test_ci_sharding.py::' + name
             for name in re.findall(r'^\s*<Function (.+)>$', log, re.M)]
    assert len(nodes) == len(set(nodes)) == count
    completed = completed_ci_nodes()
    assert set(completed) <= set(nodes)
    pending = [node for node in nodes if node not in set(completed)]
    assert pending
    command = [*base, '--out', str(cohort_out('ci-remaining')), *pending]
    save(OUT / 'ci-resume-plan.json', {'head': head, 'original_head': tested,
         'reporting_only_changes': changed, 'all_nodes': nodes, 'completed_nodes': completed,
         'pending_nodes': pending, 'command': command,
         'original_outcome_sha256': sha((cohort_out('ci-sharding') / 'outcome.json').read_bytes()),
         'collection_log_sha256': sha(log.encode())})
    print(json.dumps({'completed': len(completed), 'remaining': len(pending), 'total': count}), flush=True)
    result = subprocess.run(command, cwd=ROOT)
    assert frozen() == head
    return result.returncode


def cohort(name, collect=False):
    head = frozen()
    if not collect and name != 'canary':
        required = 'ci-canary' if name == 'ci-sharding' else 'canary'
        proof = load(cohort_out(required) / 'outcome.json')
        assert proof['returncode'] == 0 and proof['cleanup_verified']
        assert (cohort_out(required) / 'pytest.xml').stat().st_size > 0
        assert load(cohort_out(required) / 'plan.json')['source_commit'] == head
    # CI units themselves spawn two-worker synthetic pytest runs. Keeping the
    # outer CI process serial stays within the four-worker total ceiling.
    workers = 0 if name.startswith('ci-') else 4
    timeout = 3600 if name == 'ci-sharding' else 1800
    label = name + ('-collect' if collect else '')
    command = [str(SCRATCH / 'declared-dependencies/bin/python'), '-S', '-P', '-B',
        str(ROOT / 'scripts/adhoc/run_manifest_continuation_tests_20261114.py'),
        '--tree', str(ROOT), '--out', str(cohort_out(label)), '--workers', str(workers),
        '--timeout-seconds', str(timeout)]
    if collect:
        command.append('--collect-only')
    command += COHORTS[name]
    save(OUT / (label + '-launch.json'), {'head': head, 'command': command})
    result = subprocess.run(command, cwd=ROOT)
    assert frozen() == head
    return result.returncode


def roster(raw):
    result = {}
    for node in ast.parse(raw).body:
        if isinstance(node, ast.FunctionDef) and node.name == 'required_checks':
            result[node.name] = ast.dump(node, include_attributes=False)
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id in ('_COMMON_CHECKS', '_LONG_CHECKS'):
                    result[target.id] = ast.dump(node, include_attributes=False)
    assert len(result) == 3
    return result


def audit():
    head = frozen()
    verifier_path = ROOT / 'scripts/adhoc/verify_controller_pin_rotation_20261113.py'
    verifier = runpy.run_path(str(verifier_path))
    identities = []
    protected = (*PREVIOUS['PROTECTED'], 'src/data_sheets_schema/native_controller_sources_v1.json',
                 'src/data_sheets_schema/native_controller_sources_v2.json', 'tests/fixtures/native_d128_approved.json')
    for relative in protected:
        row = {'path': relative, 'working': sha((ROOT / relative).read_bytes())}
        row.update({name: sha(git('show', commit + ':' + relative).stdout)
                    for name, commit in (('accepted', BEFORE), ('candidate', CANDIDATE), ('head', head))})
        assert len({row[key] for key in ('working', 'accepted', 'candidate', 'head')}) == 1, row
        identities.append(row)
    tree = ast.parse((ROOT / SCAN).read_bytes())
    maps = {name: verifier['dict_literal'](tree, name) for name in (
        '_NATIVE_V2_RENDER_SOURCES', '_NATIVE_V2_INTEGRATED_RENDER_SOURCES', '_NATIVE_V3_RENDER_SOURCES')}
    for relative, digest in maps['_NATIVE_V3_RENDER_SOURCES'].items():
        assert sha((ROOT / relative).read_bytes()) == digest, relative
    assert maps['_NATIVE_V2_INTEGRATED_RENDER_SOURCES'][AUTHORITY] == sha(git('show', CANDIDATE + ':' + AUTHORITY).stdout)
    registration = 'src/data_sheets_schema/native_execution_registration_v2.py'
    assert roster((ROOT / registration).read_bytes()) == roster(git('show', CANDIDATE + ':' + registration).stdout)
    assert b'VERSION = 3\n' in (ROOT / registration).read_bytes()
    for parent in (BEFORE, CANDIDATE, MERGE):
        (OUT / ('scanner-diff-' + parent[:9] + '.patch')).write_bytes(git('diff', parent, head, '--', SCAN).stdout)
    check = git('diff', '--check', CANDIDATE, head, check=False)
    assert check.returncode == 0, check.stdout
    command = [str(SCRATCH / 'declared-dependencies/bin/python'), '-S', '-P', '-B', str(verifier_path), str(ROOT)]
    result = subprocess.run(command, cwd=ROOT, capture_output=True)
    (OUT / 'pin-verifier.stdout.json').write_bytes(result.stdout)
    (OUT / 'pin-verifier.stderr').write_bytes(result.stderr)
    document = json.loads(result.stdout)
    save(OUT / 'pin-verifier-result.json', {'head': head, 'command': command,
         'returncode': result.returncode, 'failures': document['failures'],
         'report_sha256': sha(result.stdout), 'verifier_sha256': sha(verifier_path.read_bytes())})
    save(OUT / 'audit.json', {'head': head, 'merge': MERGE, 'candidate': CANDIDATE,
        'merge_parents': git('show', '-s', '--format=%P', MERGE).stdout.decode().strip().split(),
        'conflicts': load(OUT / 'merge-start.json')['conflicts'], 'protected': identities,
        'per_event_roster_identical_to_candidate': True, 'v3_registration_retained': True,
        'v3_source_pins_match_working_bytes': True, 'scanner_pins': maps,
        'scanner_sha256': sha((ROOT / SCAN).read_bytes()), 'cohorts': COHORTS})
    assert frozen() == head
    print(json.dumps({'head': head, 'pin_verifier_exit': result.returncode,
                      'pin_verifier_failures': document['failures'], 'scanner_pins': maps}, indent=2))


def report():
    head = frozen()
    audit_data = load(OUT / 'audit.json')
    tested = audit_data['head']
    reporting_changes = reporting_only_since(tested, head)
    results = []
    resumed = (OUT / 'ci-resume-plan.json').exists()
    names = [*COHORTS, *(['ci-remaining'] if resumed else [])]
    for name in names:
        directory = cohort_out(name)
        plan, outcome = load(directory / 'plan.json'), load(directory / 'outcome.json')
        assert plan['source_commit'] == (head if name == 'ci-remaining' else tested)
        log = (directory / 'pytest.log').read_text()
        match = re.search(r'(?:workers? \[|collected )(\d+) items?', log)
        assert match, name
        collected = int(match.group(1))
        if name == 'ci-sharding' and outcome['returncode'] == 124:
            assert resumed and outcome['interrupted'] == 'deadline'
            assert not outcome['observed_surviving_pids'] and not outcome['observation_errors']
            completed = completed_ci_nodes()
            results.append({'name': name, 'collected': collected, 'passed': len(completed),
                'failed': 0, 'errors': 0, 'skipped': 0, 'unfinished': collected - len(completed),
                'returncode': outcome['returncode'], 'seconds': outcome['seconds'],
                'workers': plan['workers'], 'cleanup_verified': outcome['cleanup_verified'],
                'failures': [], 'output': str(directory), 'command': plan['command'],
                'source_commit': plan['source_commit'], 'proof': 'completed verbose pytest result lines; interrupted case excluded',
                'completed_nodes': completed})
            continue
        cases = list(ET.parse(directory / 'pytest.xml').iter('testcase'))
        failures = [{'node': case.get('classname') + '.' + case.get('name'),
                     'type': item.tag, 'message': item.get('message'), 'detail': item.text}
                    for case in cases for item in case if item.tag in ('failure', 'error')]
        failed = sum(case.find('failure') is not None for case in cases)
        errors = sum(case.find('error') is not None for case in cases)
        skipped = sum(case.find('skipped') is not None for case in cases)
        assert outcome['returncode'] in (0, 1) and len(cases) == collected, (name, outcome)
        results.append({'name': name, 'collected': collected, 'passed': len(cases) - failed - errors - skipped,
                        'failed': failed, 'errors': errors, 'skipped': skipped,
                        'unfinished': 0, 'source_commit': plan['source_commit'], 'proof': 'complete JUnit and ordinary pytest exit',
                        'returncode': outcome['returncode'], 'seconds': outcome['seconds'],
                        'workers': plan['workers'], 'cleanup_verified': outcome['cleanup_verified'],
                        'failures': failures, 'output': str(directory), 'command': plan['command']})
    completion = None
    if resumed:
        resume = load(OUT / 'ci-resume-plan.json')
        assert resume['head'] == head and resume['original_head'] == tested
        assert resume['completed_nodes'] == completed_ci_nodes()
        cases = list(ET.parse(cohort_out('ci-remaining') / 'pytest.xml').iter('testcase'))
        assert all(case.get('classname') == 'tests.test_ci_sharding' for case in cases)
        actual = ['tests/test_ci_sharding.py::' + case.get('name') for case in cases]
        assert len(actual) == len(set(actual)) and set(actual) == set(resume['pending_nodes'])
        assert not set(actual) & set(resume['completed_nodes'])
        assert set(actual) | set(resume['completed_nodes']) == set(resume['all_nodes'])
        initial, remaining = [row for row in results if row['name'] in ('ci-sharding', 'ci-remaining')]
        completion = {'total_unique_cases': len(resume['all_nodes']),
            'passed': initial['passed'] + remaining['passed'], 'failed': remaining['failed'],
            'errors': remaining['errors'], 'skipped': remaining['skipped'], 'unfinished': 0,
            'initial_exit': initial['returncode'], 'resume_exit': remaining['returncode'],
            'repeated_completed_cases': 0, 'initial_head': tested, 'resume_head': head}
        save(OUT / 'ci-full-coverage.json', completion)
    save(OUT / 'results.json', results)
    pin_result, pin_document = load(OUT / 'pin-verifier-result.json'), load(OUT / 'pin-verifier.stdout.json')
    pins = load(OUT / 'pin-changes.json')
    lines = ['# Final candidate merge — 2026-11-15', '',
        f'**Answer: merged head `{head}`; merge commit `{MERGE}`, with candidate `{CANDIDATE}` as its second parent. No merge conflicts. Both authorized scanner proposals are applied.**', '',
        'The merged registration retains v3 manifest checks and the candidate per-event CI roster. The scanner changes after the merge are limited to the authorized manifest and v2/v3 authority entries, with comments for each. Runtime-profile identity from the candidate is retained.', '',
        '| Authorized scanner entry | Old | Applied | Reason |', '|---|---|---|---|']
    for row in pins:
        lines.append(f"| `{row['entry']}:{row['path']}` | `{row['old']}` | `{row['new']}` | {row['reason']} |")
    profile = 'src/data_sheets_schema/native_runtime_profiles.py'
    lines += ['', f"Retained candidate runtime-profile pin: `{audit_data['scanner_pins']['_NATIVE_V3_RENDER_SOURCES'][profile]}`. Every v3 source pin matches the merged bytes; the v2 authority pin matches the candidate's historical authority bytes.", '',
        '| Focused cohort | Passed | Failed | Errors | Skipped | Unfinished in run | Exit | Seconds | Outer workers | Cleanup verified |',
        '|---|---:|---:|---:|---:|---:|---:|---:|---:|---|']
    for row in results:
        lines.append(f"| {row['name']} | {row['passed']} | {row['failed']} | {row['errors']} | {row['skipped']} | {row['unfinished']} | {row['returncode']} | {row['seconds']:.3f} | {row['workers']} | {row['cleanup_verified']} |")
    if completion:
        lines += ['', f"CI file coverage across the original run and its continuation: **{completion['total_unique_cases']} unique cases, {completion['passed']} passed, {completion['failed']} failed, {completion['errors']} errors, {completion['skipped']} skipped, {completion['unfinished']} unfinished**. No completed case was rerun. The original run reached its 3,600-second deadline and exited 124; its completed verbose result lines count only cases explicitly marked PASSED. The interrupted case was excluded and then resumed. The runner forcibly stopped its observed descendants and reported none surviving, with no observation errors; this is not classified as verified normal cleanup. The continuation has its own complete JUnit and cleanup outcome."]
    if reporting_changes:
        lines += ['', f"Core cohorts and the initial CI run tested `{tested}`. The delivery head changes only `{reporting_changes[0]}` to resume unfinished CI cases and report partial evidence accurately. All runtime, scanner, test and other source bytes remain identical; the continuation tested the delivery head. The source audit and lead pin verifier therefore retain their original tested-head identity."]
    lines += ['', f"Lead pin verifier: exit **{pin_result['returncode']}**, {len(pin_result['failures'])} failures. The verifier's stdout is saved unchanged. Its historical v2 scanner-pin differences are advisory; the v3 closure is separately checked against the working bytes.", '',
              '## Merge and review', '',
              '- Git merged without conflicts; no manual conflict resolution was needed.',
              '- An AST comparison verifies that `_COMMON_CHECKS`, `_LONG_CHECKS`, and `required_checks` exactly retain the candidate roster while the registration stays at version 3.',
              '- Removing only the three authorized literal pin entries from the before/after scanner ASTs leaves identical executable syntax. No other scanner entry or logic was changed after the merge.',
              '- The four protected files, both controller source manifests and the D128 approval fixture are unchanged across both parents and this head. The candidate-relative whitespace check passes.',
              '- The scanner tests now check the committed manifest pin, refusal under the historical pin, exact mode forwarding, positive historical v2 and current v3 derivation using the same scanner, and refusal when authority pins are crossed between versions.', '',
              '## Validation scope and remaining findings', '',
              'Cohorts ran serially. Ordinary and scanner cohorts used four xdist workers. CI sharding ran without outer xdist because its synthetic subprocesses use two workers. No more than four pytest workers ran concurrently. Canary outputs, nonempty JUnit and verified cleanup were checked before dependent cohorts; each canary used the same launcher, isolation and worker mode as its cohort. These prove local synthetic/static execution and persistence, not live timing or acceptance.', '',
              'No long live-boundary or full-registration matrix, installed-environment cost measurement, native binary, provider or model ran. Full callback/recording/dispatch/acceptance paths and the real builder prefix remain for CI. This assignment did not rerun the complete finding-array comparison; the historical D128 asset/finite-findings approval is unchanged.', '']
    for row in results:
        for failure in row['failures']:
            lines.append(f"- `{row['name']}` / `{failure['node']}`: {failure['message']}")
    if not any(row['failures'] for row in results):
        lines.append('No focused cohort failures.')
    for failure in pin_result['failures']:
        lines.append('- Pin verifier: ' + failure)
    lines += ['', 'Findings are handed to the lead for disposition and issue filing; no GitHub write or push was made. At-signs in displayed test parameters are spelled [at-sign]; raw evidence remains unchanged.', '',
              '## Evidence and reproduction', '',
              f'- Evidence root: `{OUT}`.',
              f'- Merge record: `{OUT / "merge-start.json"}`; pin changes: `{OUT / "pin-changes.json"}`; source audit: `{OUT / "audit.json"}`.',
              f'- Cohort results: `{OUT / "results.json"}`; each row names its saved plan, command, JUnit/log directory and cleanup outcome.',
              f'- Lead verifier output: `{OUT / "pin-verifier.stdout.json"}`; invocation and result: `{OUT / "pin-verifier-result.json"}`.',
              f'- Helpers: `{ROOT / "scripts/adhoc/merge_manifest_final_20261115.py"}` and `{Path(__file__).resolve()}`.',
              '- Invoke the check helper with the declared-dependencies Python and `-S -P -B`: `collect canary`, `cohort canary`, then the named cohorts in results.json. Run `cohort ci-canary` before `cohort ci-sharding`. If the CI run reaches its deadline, `resume-ci` recollects the file and runs exactly the cases without completed results. `audit` runs the exact lead verifier. `report` generates these tables from saved JSON/JUnit and the explicitly identified partial-run log. Output paths are exclusive-create; replay requires fresh assigned evidence paths.',
              *([f'- CI continuation selection and command: `{OUT / "ci-resume-plan.json"}`; complete unique coverage: `{OUT / "ci-full-coverage.json"}`.'] if resumed else []), '',
              '---', '', 'Earlier integration handoff follows unchanged.', '']
    text = '\n'.join(lines).replace(chr(64), '[at-sign]')
    original = HANDOFF.read_bytes()
    with (OUT / 'handoff-before.md').open('xb') as stream:
        stream.write(original)
    HANDOFF.write_bytes(text.encode() + original)
    raw = HANDOFF.read_bytes()
    assert raw.startswith(text.encode()) and raw.endswith(original)
    save(OUT / 'handoff-identity.json', {'path': str(HANDOFF), 'head': head, 'sha256': sha(raw),
         'bytes': len(raw), 'previous_sha256': sha(original)})
    print(json.dumps(load(OUT / 'handoff-identity.json'), indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('cohort', 'collect', 'audit', 'report', 'resume-ci'))
    parser.add_argument('name', nargs='?', choices=tuple(COHORTS))
    args = parser.parse_args()
    if args.action in ('cohort', 'collect'):
        assert args.name
        raise SystemExit(cohort(args.name, collect=args.action == 'collect'))
    assert args.name is None
    if args.action == 'resume-ci':
        raise SystemExit(resume_ci())
    {'audit': audit, 'report': report}[args.action]()
