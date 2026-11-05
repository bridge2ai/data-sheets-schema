#!/usr/bin/env python3
"""#5448/#5494, 2026-11-05: summarize committed fixes and offline evidence.

Inputs: the two assigned committed worktrees, this task's retained results,
the tested #5448 snapshot manifest, and the retained scanner reference.
Outputs: fresh verification.json, 5448.diff, 5494.diff, provider-inventory.txt.
No tests, generation, network, imports from either product, or Git mutations.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import subprocess
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
EXEC = ROOT.parent
WORKS = {'5448': ROOT, '5494': EXEC / 'codex-5494'}
BASE = 'd0974d4bcc0f254272ec5a95e94d83ae801bbd38'
EVIDENCE = EXEC / 'plans/reviews/codex_5448_5494_2026-11-05'
REFERENCE = EXEC / 'plans/reviews/pr5213_main_merge_2026-11-04/scanner/audit.json'
ASSET = 'src/data_sheets_schema/omission_inventory_v1/policy.md'
SCANNER = '.claude/skills/d4d-generation-specificity-audit/scan.py'
DEFAULT_RUNS = ['5448/after-canary', '5448/after-seven', '5448/explicit-and-undo',
                '5448/collection-before', '5448/collection-after',
                '5494/tests-final01/pytest-canary', '5494/tests-final01/pytest-full']
SNAPSHOT_FILES = {'tests/conftest.py', 'tests/test_d69_round4_ownership.py',
                  'tests/test_fairscape_integration/test_nested_dataset_readback.py',
                  'scripts/adhoc/validate_provider_env_5448_20261105.py'}
ENV = {key: value for key, value in os.environ.items()
       if key in {'PATH', 'HOME', 'LANG', 'LC_ALL', 'LC_CTYPE', 'TMPDIR'}}
ENV.update(GIT_NO_LAZY_FETCH='1', GIT_ALLOW_PROTOCOL='', GIT_CONFIG_GLOBAL='/dev/null',
           GIT_CONFIG_NOSYSTEM='1', GIT_OPTIONAL_LOCKS='0', GIT_NO_REPLACE_OBJECTS='1')


def require(value, message):
    if not value:
        raise ValueError(message)


def load(path):
    return json.loads(Path(path).read_bytes())


def digest(raw):
    return {'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw)}


def pin(path):
    path = Path(path)
    return {'path': str(path), **digest(path.read_bytes())}


def git(root, *arguments, acceptable=(0,)):
    result = subprocess.run(['git', '--no-replace-objects', '-c', 'protocol.allow=never',
        '-C', str(root), *arguments], env=ENV, capture_output=True, timeout=120)
    require(result.returncode in acceptable, 'local Git command failed: ' + ' '.join(arguments))
    return result.stdout


def write_new(path, raw):
    with path.open('xb') as output:
        output.write(raw)
    require(path.read_bytes() == raw, 'output did not persist: ' + str(path))


def task_path(value):
    path = EVIDENCE / value
    require(not Path(value).is_absolute() and '..' not in Path(value).parts
            and path.resolve() == path and path.is_relative_to(EVIDENCE), 'task-relative evidence required')
    return path


def check_pin(expected):
    path = Path(expected['path'])
    require(path.resolve() == path and
            (path.is_relative_to(EVIDENCE) or path == REFERENCE
             or path.is_relative_to(EXEC / 'scratch-codex-5448-20261105')),
            'evidence pin outside authorized scope')
    require(pin(path) == expected, 'evidence pin differs: ' + str(path))
    return path


def branch(issue):
    root = WORKS[issue]
    require(root.resolve() == root, 'worktree alias refused')
    head = git(root, 'rev-parse', 'HEAD').decode().strip()
    git(root, 'merge-base', '--is-ancestor', BASE, head)
    status = git(root, 'status', '--porcelain=v1', '--untracked-files=all').decode()
    require(not status and head != BASE, 'commit the finished branch before summarizing: ' + issue)
    paths = git(root, 'diff', '--name-only', '--no-renames', BASE, head).decode().splitlines()
    require(not any(p.startswith(('src/', 'data/', '.claude/agents/', '.claude/commands/', 'prompts/'))
                    or Path(p).name in {'shared_generation.py', 'canonical_hashes.yaml'} for p in paths),
            'protected path changed: ' + issue)
    git(root, 'diff', '--check', BASE, head)
    return {'head': head, 'parents': git(root, 'show', '-s', '--format=%P', head).decode().split(),
            'status': status, 'changed_paths': paths, 'base': BASE,
            'branch': git(root, 'branch', '--show-current').decode().strip()}


def pytest_result(directory):
    result, started = load(directory / 'result.json'), load(directory / 'started.json')
    require(result['identity'] == started['identity'], 'pytest identity mismatch: ' + str(directory))
    xml = ET.parse(directory / 'junit.xml')
    suites = list(xml.iter('testsuite'))
    require([suite.attrib for suite in suites] == result['suites'], 'JUnit/result mismatch')
    counts = {name: sum(int(suite.attrib.get(name, 0)) for suite in suites)
              for name in ('tests', 'errors', 'failures', 'skipped')}
    collected = '--collect-only' in started['command']
    if collected:
        nodes = load(directory / 'collected.json')
        require(isinstance(nodes, list) and all(isinstance(n, str) for n in nodes), 'invalid collection')
        counts.update(collection_occurrences=len(nodes), collection_distinct=len(set(nodes)))
    return {'identity': result['identity'], 'returncode': result['returncode'], 'counts': counts,
            'collect_only': collected, 'seconds': result['seconds'],
            'skips': [{'classname': case.get('classname'), 'name': case.get('name'),
                       'reason': skipped.get('message'), 'type': skipped.get('type')}
                      for case in xml.iter('testcase') for skipped in case.findall('skipped')]}


def reconcile_scanner_run(directory, run):
    """Join executed nodes and JUnit; xdist need not emit a collection ledger."""
    names = ['pytest.log', 'junit.xml', 'events.jsonl']
    for name in names:
        path = directory / name
        require(path.is_file() and path.stat().st_size > 0, 'missing nonempty scanner test artifact: ' + str(path))
    events = [json.loads(line) for line in (directory / 'events.jsonl').read_text().splitlines()]
    require(events and all(isinstance(row, dict) and row.get('outcome') == 'passed'
                          and row.get('when') in {'setup', 'call', 'teardown'}
                          and isinstance(row.get('nodeid'), str) for row in events),
            'scanner test events contain an incomplete or nonpassing phase')
    phases = {phase: Counter(row['nodeid'] for row in events if row['when'] == phase)
              for phase in ('setup', 'call', 'teardown')}
    calls = phases['call']
    require(calls and all(count == 1 for count in calls.values())
            and all(actual == calls for actual in phases.values()),
            'scanner nodes must each have exactly one passing setup/call/teardown')
    test_file = 'tests/test_generation_specificity_skill.py'
    command = load(directory / 'started.json')['command']
    selected = [arg for arg in command if arg == test_file or arg.startswith(test_file + '::')]
    require(selected and all(node.startswith(test_file + '::') for node in calls)
            and (test_file in selected or Counter(selected) == calls),
            'scanner executed nodes differ from the selected file/canary command')
    cases = list(ET.parse(directory / 'junit.xml').iter('testcase'))
    junit_nodes = Counter()
    module = test_file[:-3].replace('/', '.')
    for case in cases:
        classname, name = case.get('classname', ''), case.get('name', '')
        require(classname == module or classname.startswith(module + '.'), 'unexpected scanner JUnit class')
        classes = classname[len(module):].lstrip('.').replace('.', '::')
        junit_nodes[test_file + '::' + (classes + '::' if classes else '') + name] += 1
    require(junit_nodes == calls, 'scanner JUnit identities differ from executed event nodes')
    require(run['returncode'] == 0 and not run['collect_only']
            and all(run['counts'][key] == 0 for key in ('errors', 'failures', 'skipped'))
            and run['counts']['tests'] == len(cases) == len(calls) > 0,
            'scanner JUnit and successful-call counts differ')
    collection_path = directory / 'collected.json'
    available = collection_path.is_file()
    if available:
        nodes = load(collection_path)
        require(isinstance(nodes, list) and nodes and all(isinstance(n, str) and n for n in nodes)
                and Counter(nodes) == calls, 'optional scanner collection differs from executed nodes')
        names.append('collected.json')
    return {'passed': True, 'executed_nodes': len(calls), 'collection_ledger_available': available,
            'collection_occurrences': len(nodes) if available else None,
            'limits': 'Executed-node reconciliation only; no full collection claim when xdist omits its ledger.',
            'phase_counts': {phase: sum(counts.values()) for phase, counts in phases.items()},
            'junit_testcases': len(cases), 'artifacts': {name: pin(directory / name) for name in names}}


def snapshot_binding(run, head):
    identity = load(run / 'result.json')['identity']
    require(identity['commit'] == BASE, 'candidate snapshot base differs')
    path = check_pin(identity['candidate_snapshot'])
    snapshot = load(path)
    require(snapshot['base'] == BASE and set(snapshot['source_files']) == SNAPSHOT_FILES
            and set(snapshot['files']) == SNAPSHOT_FILES, 'candidate file roster differs')
    verified = {}
    for relative in sorted(SNAPSHOT_FILES):
        expected = snapshot['source_files'][relative]
        require(Path(expected['path']) == ROOT / relative, 'snapshot source is not the assigned worktree')
        blob = digest(git(ROOT, 'show', head + ':' + relative))
        require(all(blob[key] == expected[key] == snapshot['files'][relative][key]
                    for key in ('sha256', 'bytes')), 'committed candidate bytes differ: ' + relative)
        verified[relative] = blob
    return {'manifest': pin(path), 'base': BASE, 'committed_head': head, 'verified_blobs': verified,
            'limits': 'Final tested candidate only; superseded untested candidates are not acceptance evidence.'}


def scanner_checks(before_name, after_name, head):
    reference = load(REFERENCE)['violations']
    require(len(reference) == 24, 'retained reference is not 24 findings')
    summaries, reports = {}, {}
    for phase in (before_name, after_name):
        directory = task_path('5494/' + phase)
        summary = load(directory / 'result.json')
        require(summary['base'] == BASE, 'scanner base differs')
        check_pin(summary['reference'])
        phases = {}
        for variant in ('clean', 'planted'):
            selected = summary['results'][variant]
            report_path = check_pin(selected['report'])
            report = load(report_path)
            require(selected['exit'] == report['exit'] == 1
                    and selected['violations'] == len(report['violations']), 'scanner did not complete')
            findings = report['violations']
            added = [row for row in findings if row['path'] == ASSET]
            expect_added = phase == after_name and variant == 'planted'
            require([row for row in findings if row['path'] != ASSET] == reference,
                    'retained scanner findings changed')
            require(len(findings) == (25 if expect_added else 24)
                    and len(added) == (1 if expect_added else 0), 'planted scanner control differs')
            if expect_added:
                require(added[0]['match'] == 'CHORUS' and added[0]['model_facing'] is True
                        and added[0]['violation'] is True, 'planted finding is not the model-facing control')
            started = load(directory / variant / 'started.json')
            if phase == after_name:
                actual = digest(git(WORKS['5494'], 'show', head + ':' + SCANNER))
                require(all(started['scanner'][key] == actual[key] for key in actual),
                        'final scanner is not the committed scanner')
            reports[(phase, variant)] = report
            phases[variant] = {'report': pin(report_path), 'started': pin(directory / variant / 'started.json'),
                'violations': len(findings), 'asset_discovered': selected['asset_discovered'],
                'model_facing_assets': selected.get('model_facing_assets', {})}
        summaries[phase] = {'result': pin(directory / 'result.json'), 'variants': phases}
    require(reports[(before_name, 'clean')]['violations'] == reports[(after_name, 'clean')]['violations'],
            'clean arrays differ')
    return {'reference': pin(REFERENCE), 'phases': summaries, 'clean_arrays_exact': True,
            'comparison': 'Complete violation objects and order; no coordinate normalization.'}


def scanner_test_binding(manifest_path, head):
    manifest = load(manifest_path)
    sources = manifest['copied_sources']
    expected = {SCANNER, '.claude/skills/d4d-generation-specificity-audit/SKILL.md',
                'tests/test_generation_specificity_skill.py',
                'scripts/adhoc/reproduce_scanner_assets_5494_20261105.py'}
    require(manifest['base'] == BASE and set(sources) == expected, 'scanner test snapshot roster differs')
    blobs = {}
    for relative, selected in sources.items():
        require(Path(selected['path']) == WORKS['5494'] / relative, 'scanner source outside assigned worktree')
        blob = digest(git(WORKS['5494'], 'show', head + ':' + relative))
        require(all(blob[key] == selected[key] for key in blob), 'committed scanner test source differs: ' + relative)
        blobs[relative] = blob
    return {'manifest': pin(manifest_path), 'committed_head': head, 'verified_blobs': blobs}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--candidate-run', default='5448/after-seven')
    parser.add_argument('--require-pass', action='append', help='Task-relative completed pytest run; repeat as needed')
    parser.add_argument('--scanner-before', default='before')
    parser.add_argument('--scanner-after', default='after-final')
    parser.add_argument('--scanner-tests', default='5494/tests-final01')
    args = parser.parse_args()
    require(ROOT.name == 'codex-5448' and ROOT.resolve() == ROOT, 'assigned helper checkout required')
    outputs = {name: EVIDENCE / name for name in ('verification.json', '5448.diff', '5494.diff', 'provider-inventory.txt')}
    require(all(not p.exists() for p in outputs.values()), 'summary outputs must be fresh')
    producer = pin(Path(__file__))
    branches = {issue: branch(issue) for issue in WORKS}
    runs = {}
    for issue in WORKS:
        for directory in sorted((EVIDENCE / issue).iterdir()):
            if directory.is_dir() and directory.name not in {'tmp', 'pycache'} and (directory / 'junit.xml').is_file():
                runs[str(directory.relative_to(EVIDENCE))] = pytest_result(directory)
    required = args.require_pass or DEFAULT_RUNS
    for name in required:
        if name not in runs and (task_path(name) / 'result.json').is_file():
            runs[name] = pytest_result(task_path(name))
        require(name in runs, 'required run is absent: ' + name)
        run = runs[name]
        require(run['returncode'] == 0 and all(run['counts'][k] == 0 for k in ('errors', 'failures'))
                and (run['counts']['tests'] > run['counts']['skipped'] or run['collect_only']),
                'required run not successful: ' + name)
        if run['counts']['skipped']:
            reason = "a terminal result and the attempt deadline are the native runtime's"
            require(name == '5448/explicit-and-undo' and len(run['skips']) == run['counts']['skipped']
                    and all(row['classname'] == 'tests.test_canary_controller_receipts'
                            and row['reason'] in {reason, 'Skipped: ' + reason}
                            and row['type'] == 'pytest.skip' for row in run['skips']),
                    'unexpected skipped test in required run: ' + name)
    dummy = runs['5448/before-dummy']
    require(dummy['identity']['commit'] == BASE and dummy['returncode'] == 1
            and dummy['counts'] == {'tests': 7, 'errors': 0, 'failures': 7, 'skipped': 0}, 'dummy baseline differs')
    failed = list(ET.parse(task_path('5448/before-dummy/junit.xml')).iter('failure'))
    require(len(failed) == 7 and all('registered endpoint differs' in (node.text or '') for node in failed),
            'dummy baseline failed for another reason')
    require(runs['5448/before-clean']['returncode'] == 0
            and runs['5448/before-clean']['counts']['tests'] == 7, 'clean baseline differs')
    candidate = snapshot_binding(task_path(args.candidate_run), branches['5448']['head'])
    for name in required:
        if name.startswith('5448/') and name != '5448/collection-before':
            require(runs[name]['identity'].get('candidate_snapshot') == candidate['manifest'],
                    'required run is not the tested final candidate: ' + name)
    collection = load(task_path('5448/collection-comparison.json'))
    for key in ('before', 'after'):
        check_pin(collection[key])
    left, right = load(Path(collection['before']['path'])), load(Path(collection['after']['path']))
    require(collection['equal'] is True and Counter(left) == Counter(right)
            and collection['before_count'] == len(left) and collection['after_count'] == len(right),
            'collection multiplicity changed')
    scanners = scanner_checks(args.scanner_before, args.scanner_after, branches['5494']['head'])
    scanner_tests = scanner_test_binding(task_path(args.scanner_tests + '/manifest.json'), branches['5494']['head'])
    for name in required:
        if name.startswith('5494/'):
            require(runs[name]['identity'].get('snapshot_manifest') == scanner_tests['manifest'],
                    'scanner pytest run uses another snapshot: ' + name)
            runs[name]['acceptance_reconciliation'] = reconcile_scanner_run(task_path(name), runs[name])
    inventory = []
    for label, pattern, scope in (
        ('provider environment reads', r'(environ|getenv|env\.get|source\.get).*(API_KEY|AUTH_TOKEN|BASE_URL|API_BASE|OAUTH_TOKEN)', 'src'),
        ('explicit test key settings', r'setenv\(.*(API_KEY|AUTH_TOKEN|BASE_URL|OAUTH_TOKEN)', 'tests')):
        raw = git(ROOT, 'grep', '-n', '-E', pattern, branches['5448']['head'], '--', scope, acceptable=(0, 1))
        inventory.append(label.encode() + b'\n' + raw + b'\n')
    for issue, branch_info in branches.items():
        write_new(outputs[issue + '.diff'], git(WORKS[issue], 'diff', '--binary', '--no-ext-diff', BASE, branch_info['head']))
    write_new(outputs['provider-inventory.txt'], b''.join(inventory))
    artifacts = {}
    names = {'result.json', 'started.json', 'collected.json', 'junit.xml'}
    for directory in [EVIDENCE, EVIDENCE / '5448', EVIDENCE / '5494', task_path(args.scanner_tests)]:
        for path in sorted(directory.iterdir()):
            if path.is_file() and path.name != 'verification.json':
                artifacts[str(path.relative_to(EVIDENCE))] = pin(path)
    for run in runs:
        for name in names:
            path = task_path(run) / name
            if path.is_file():
                artifacts[str(path.relative_to(EVIDENCE))] = pin(path)
    require(pin(Path(__file__)) == producer, 'summary producer changed')
    result = {'format': 'codex_5448_5494_verification_v1', 'passed': True, 'producer': producer,
        'base': BASE, 'branches': branches, 'pytest_runs': runs, 'candidate_5448': candidate,
        'collection_comparison': pin(task_path('5448/collection-comparison.json')),
        'collection_occurrences': len(left), 'collection_distinct': len(set(left)),
        'scanner': scanners, 'scanner_pytest_snapshot': scanner_tests, 'artifacts': artifacts,
        'limits': 'Retained offline artifacts and committed-byte comparisons; no provider execution or tests run by this summary.'}
    write_new(outputs['verification.json'], (json.dumps(result, sort_keys=True, indent=2) + '\n').encode())


if __name__ == '__main__':
    main()
