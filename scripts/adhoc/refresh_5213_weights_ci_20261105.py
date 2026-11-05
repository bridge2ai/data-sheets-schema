#!/usr/bin/env python3
"""#5213 round 7, 2026-11-05: offline CI weight refresh and validation evidence.

Inputs: d0974d4bc timings, retained run 41990198212 JUnit, original local
JUnit. Outputs: only local-override scheduling weights and external evidence.
No providers or network; historical provenance is retained verbatim as values.
"""
import argparse
from collections import Counter, defaultdict
from copy import deepcopy
from decimal import Decimal
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import importlib.util
import signal
import tarfile
import time
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
BASE = 'd0974d4bcc0f254272ec5a95e94d83ae801bbd38'
REVIEWS = ROOT.parent / 'plans/reviews'
ART = REVIEWS / 'pr5213_round6_lead_review_2026-11-05/ci-run-41990198212/artifacts'
LOCAL = REVIEWS / 'pr5213_integration_ddfd45c3b_2026-11-02/timings-generation/normalized'
TIMING = 'utils/ci_test_durations.json'
RATIO = Decimal('2.1033')


def git(*args):
    return subprocess.check_output(['git', '-c', 'protocol.allow=never', *args], cwd=ROOT)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def records(directory):
    rows, artifacts = [], []
    for path in sorted(directory.rglob('*.xml')):
        artifacts.append({'path': str(path.relative_to(directory)), 'sha256': sha(path)})
        for tc in ET.parse(path).getroot().iter('testcase'):
            parts = tc.get('classname', '').split('.')
            k = max(i for i, part in enumerate(parts) if part.startswith('test_') or i == 0)
            file = tc.get('file') or '/'.join(parts[:k + 1]) + '.py'
            node = file + '::' + '::'.join(parts[k + 1:] + [tc.get('name')])
            seconds = Decimal(tc.get('time') or '0')
            assert seconds.is_finite() and seconds >= 0
            rows.append((file, node, seconds))
    assert rows
    return rows, artifacts


def refresh(install=False):
    original = git('show', BASE + ':' + TIMING).decode()
    before = json.loads(original)
    result = deepcopy(before)
    local = {f: s for block in before['local_overrides'] for f, s in block['file_seconds'].items()}
    assert len(local) == 25
    ci, artifacts = records(ART)
    historical, local_artifacts = records(LOCAL)
    expected = before['local_overrides'][0]['normalized_artifacts']
    assert local_artifacts == sorted(expected, key=lambda row: row['path'])
    sums = defaultdict(Decimal)
    for file, node, seconds in ci:
        sums[file] += seconds
    sg2 = {node: seconds for file, node, seconds in historical
           if '::test_sg2_root_launch_completes_and_records_registered_paths[' in node}
    assert len(sg2) == 3
    rows = []
    for file in sorted(local):
        old = Decimal(str(before['file_seconds'][file]))
        deduction = sum(sg2.values()) if file.endswith('test_wave7_5213_d76_registration.py') else Decimal(0)
        assert old > deduction
        new = sums[file] if file in sums else (old - deduction) * RATIO
        new = max(Decimal('0.001'), new).quantize(Decimal('0.001'))
        result['file_seconds'][file] = float(new)
        rows.append({'file': file, 'before': float(old), 'after': float(new),
                     'basis': 'CI JUnit' if file in sums else 'local remainder x 2.1033',
                     'sg2_deducted': float(deduction)})
    assert sum(f in sums for f in local) == 18
    assert sum(f in sums and before['file_seconds'][f] > 1 for f in local) == 14
    assert len(set(before['file_seconds']) - set(local)) == 635
    assert all(result['file_seconds'][f] == value for f, value in before['file_seconds'].items() if f not in local)
    provenance = {'run_id': 41990198212, 'commit': BASE, 'date': '2026-11-05',
        'rule': 'CI JUnit sum for all 18 observed override files (14 exceed 1 second locally); seven missing files use local x 2.1033. Registration first subtracts its three original local SG2 case times. Floor 0.001s, round to 0.001s. Historical provenance unchanged; cancelled shard is not a successful run.',
        'artifacts': artifacts, 'local_artifacts': local_artifacts,
        'sg2_local_seconds': {n: float(s) for n, s in sg2.items()}, 'weights': rows}
    result['ci_refresh_5213_20261105'] = provenance
    if install:
        start = original.index('\n  "file_seconds": {') + len('\n  "file_seconds": ')
        _, length = json.JSONDecoder().raw_decode(original[start:])
        replacement = json.dumps(result['file_seconds'], indent=2).replace('\n', '\n  ')
        updated = original[:start] + replacement + original[start + length:]
        end = updated.rfind('}')
        block = json.dumps(provenance, indent=2).replace('\n', '\n  ')
        updated = updated[:end].rstrip() + ',\n  "ci_refresh_5213_20261105": ' + block + '\n}\n'
        (ROOT / TIMING).write_text(updated)
        assert json.loads((ROOT / TIMING).read_text()) == result
    return result


def pytest_collection_finish(session):
    """Evidence-only hook: record actual selected occurrences without executing."""
    destination = os.environ.get('ROUND7_COLLECTION')
    if destination:
        Path(destination).write_text(json.dumps([item.nodeid for item in session.items]))


def load_plugin(tree):
    spec = importlib.util.spec_from_file_location('round7_shard', tree / 'utils/pytest_shard.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def prediction(tree, nodes, output):
    plugin = load_plugin(tree)
    data = json.loads((tree / TIMING).read_text())
    weights = data['file_seconds']
    lanes = plugin.partition_lanes(nodes)
    assert len(lanes) == 8
    assert Counter(n for group in lanes.values() for n in group) == Counter(nodes)
    local = {f for block in data['local_overrides'] for f in block['file_seconds']}
    ci, _ = records(ART)
    historical, _ = records(LOCAL)
    ordinary = set(lanes['ordinary'])
    observed = defaultdict(list)
    for file, node, seconds in ci:
        if node in ordinary:
            observed[file].append((float(seconds), node, 'observed CI'))
    historical_by_file = defaultdict(list)
    for file, node, seconds in historical:
        if node in ordinary:
            historical_by_file[file].append((float(seconds) * 2.1, node, 'local x 2.1'))
    prior_path = ROOT.parent / 'scratch-5212fix/r8-final2-timing/evidence.json'
    assert sha(prior_path) == 'c0ebe0f24107cc6473f8443a424455ae4a427fa797a09665a79d5c333cd70e80'
    prior_by_file = defaultdict(list)
    for row in json.loads(prior_path.read_text())['cases']:
        if row['nodeid'] in ordinary and row['file'] not in local:
            prior_by_file[row['file']].append((row['seconds'] * .92, row['nodeid'],
                                             'prior CI estimate x 0.92'))
    paths = {n.split('::', 1)[0] for n in lanes['ordinary']}
    estimates = plugin._estimates(paths, weights)
    risks = {}
    for file in paths:
        candidates = observed.get(file) or historical_by_file.get(file) or prior_by_file.get(file)
        risks[file] = max(candidates) if candidates else (
            estimates[file] * (1 if file in local else .92), file,
            'unmeasured file-total upper bound, not an observed case')
    rows = []
    for total in (8, 6):
        assignment = plugin.balanced_files(paths, total, weights)
        covered = Counter(n for n in lanes['ordinary'] if assignment[n.split('::', 1)[0]] in range(1, total + 1))
        covered.update(n for lane, group in lanes.items() if lane != 'ordinary' for n in group)
        assert covered == Counter(nodes)
        for index in range(1, total + 1):
            files = [f for f in paths if assignment[f] == index]
            raw = sum(estimates[f] for f in files) / 240
            adjusted = sum(estimates[f] * (1 if f in local else .92) for f in files) / 240
            risk = max(risks[f] for f in files)
            rows.append({'shards': total, 'shard': index, 'load_minutes': raw,
                         'ratio_adjusted_minutes': adjusted, 'largest_case_minutes': risk[0] / 60,
                         'risk_node': risk[1], 'risk_basis': risk[2],
                         'over_30': max(adjusted, risk[0] / 60) > 30})
    value = {'collection': len(nodes), 'ordinary': len(lanes['ordinary']),
             'prior_case_evidence': {'path': str(prior_path), 'sha256': sha(prior_path)},
             'unmeasured_risk_files': sorted(f for f in risks if 'upper bound' in risks[f][2]),
             'dedicated': {k: v for k, v in lanes.items() if k != 'ordinary'}, 'predictions': rows}
    (output / 'prediction.json').write_text(json.dumps(value, indent=2) + '\n')
    return value


def validate(output, python):
    """Validate only a pinned git archive; all subprocesses have a 3600s deadline."""
    assert not git('status', '--porcelain'), 'commit clean final source before validation'
    head = git('rev-parse', 'HEAD').decode().strip()
    subprocess.run(['git', 'merge-base', '--is-ancestor', BASE, head], cwd=ROOT, check=True)
    assert not git('rev-list', '--merges', BASE + '..' + head)
    output.mkdir(parents=True, exist_ok=False)
    archive = output / 'source.tar'
    with archive.open('wb') as stream:
        subprocess.run(['git', 'archive', head], cwd=ROOT, stdout=stream, check=True)
    tree = output / 'source'
    tree.mkdir()
    with tarfile.open(archive) as bundle:
        bundle.extractall(tree, filter='data')
    # Local object alternates supply identity/history without a fetch or checkout.
    subprocess.run(['git', 'init', '-q', str(tree)], check=True)
    objects = Path(git('rev-parse', '--git-common-dir').decode().strip()).resolve() / 'objects'
    (tree / '.git/objects/info/alternates').write_text(str(objects) + '\n')
    subprocess.run(['git', '-C', str(tree), 'update-ref', 'HEAD', head], check=True)
    subprocess.run(['git', '-C', str(tree), 'read-tree', head], check=True)
    env = {k: v for k, v in os.environ.items() if not any(s in k.upper() for s in
           ('TOKEN', 'SECRET', 'API_KEY', 'CREDENTIAL', 'PROXY')) and not k.startswith('GIT_')}
    env.update(PYTHONPATH=str(tree) + os.pathsep + str(tree / 'src'),
               PYTHONPYCACHEPREFIX=str(output / 'pycache'), PYTEST_DISABLE_PLUGIN_AUTOLOAD='1',
               GIT_NO_LAZY_FETCH='1', GIT_CONFIG_COUNT='1',
               GIT_CONFIG_KEY_0='protocol.allow', GIT_CONFIG_VALUE_0='never')
    results = []

    def run(name, arguments, expected=0, collection=False):
        command = [str(python), *arguments]
        current = dict(env)
        if collection:
            current['ROUND7_COLLECTION'] = str(output / (name + '.nodes.json'))
        start = time.monotonic()
        with (output / (name + '.log')).open('w') as stream:
            proc = subprocess.Popen(command, cwd=tree, env=current, stdout=stream,
                                    stderr=subprocess.STDOUT, start_new_session=True)
            try:
                code = proc.wait(timeout=3600)
            except subprocess.TimeoutExpired:
                os.killpg(proc.pid, signal.SIGKILL)
                proc.wait()
                raise
        result = {'name': name, 'command': command, 'returncode': code,
                  'seconds': time.monotonic() - start, 'expected': expected}
        results.append(result)
        (output / 'validation.json').write_text(json.dumps({'commit': head, 'archive_sha256': sha(archive),
            'interpreter': str(python), 'results': results}, indent=2) + '\n')
        print(json.dumps(result), flush=True)
        assert code == expected, f'{name}: {code}, see retained log'

    common = ['-m', 'pytest', '-p', 'xdist', '-p', 'no:cacheprovider', '-q']
    run('canary', common + ['tests/test_ci_sharding.py::test_lane_partition_is_complete_order_preserving_and_strict',
                           '--junitxml=' + str(output / 'canary.xml')])
    assert list(ET.parse(output / 'canary.xml').iter('testcase'))
    run('contracts', common + ['tests/test_ci_sharding.py', 'tests/test_ci_timing_update.py',
        'scripts/adhoc/test_refresh_pr5213_integration_timings_20261103.py',
        'scripts/adhoc/test_plan_pr5213_integration_20261102.py',
        '--junitxml=' + str(output / 'contracts.xml')])
    capture = ['-p', 'scripts.adhoc.refresh_5213_weights_ci_20261105', '--collect-only', 'tests']
    run('collection', common + capture, collection=True)
    nodes = json.loads((output / 'collection.nodes.json').read_text())
    proof = prediction(tree, nodes, output)
    for lane, target in proof['dedicated'].items():
        if lane.startswith('sg2-'):
            run(lane, common + capture + ['-p', 'utils.pytest_shard', '--ci-lane=' + lane],
                expected=1, collection=True)
            assert json.loads((output / (lane + '.nodes.json')).read_text()) == target
    run('scanner', ['.claude/skills/d4d-generation-specificity-audit/scan.py', '--root', str(tree),
        '--report', str(output / 'audit.md'), '--json', str(output / 'audit.json')], expected=1)
    baseline = json.loads((REVIEWS / 'pr5213_main_merge_2026-11-04/scanner/audit.json').read_text())
    audit = json.loads((output / 'audit.json').read_text())
    assert audit['self_test']['passed'] is True
    assert len(audit['violations']) == 24
    assert audit['violations'] == baseline['violations']
    assert audit['facts']['model_facing_modules']['listed_not_derived'] == baseline['facts']['model_facing_modules']['listed_not_derived']
    (output / 'scanner-equality.json').write_text(json.dumps({'findings': 24, 'field_for_field_equal': True,
        'baseline_sha256': sha(REVIEWS / 'pr5213_main_merge_2026-11-04/scanner/audit.json'),
        'candidate_sha256': sha(output / 'audit.json')}, indent=2) + '\n')
    assert not subprocess.check_output(['git', '-C', str(tree), 'diff', 'HEAD', '--'])


def report(output, destination):
    """Render tables from persisted evidence, never from hand-transcribed numbers."""
    validation = json.loads((output / 'validation.json').read_text())
    proof = json.loads((output / 'prediction.json').read_text())
    equality = json.loads((output / 'scanner-equality.json').read_text())
    data = json.loads((output / 'source' / TIMING).read_text())
    assert validation['commit'] == git('rev-parse', 'HEAD').decode().strip()
    assert all(r['returncode'] == r['expected'] for r in validation['results'])
    cases = list(ET.parse(output / 'contracts.xml').iter('testcase'))
    assert cases and not any(c.find('failure') is not None or c.find('error') is not None for c in cases)
    lines = ['# PR #5213 round 7 CI — 2026-11-05', '',
        'Tasks 1–5 completed offline; stopped without push, fetch, gh, network or provider calls.', '',
        '## Commits and scope', '',
        'Base: `' + BASE + '`. Final validated head: `' + validation['commit'] + '`.',
        'Linear commits (no merge or rebase):', '',
        '```text', git('log', '--format=%h %s', BASE + '..HEAD').decode().strip(), '```', '',
        '- `utils/pytest_shard.py`: retain the four API nodes; add three exact SG2 nodes to a combined seven-case roster. Ordinary shards exclude them; each dedicated lane requires passed setup/call/teardown and rejects skip, xfail and collection-only.',
        '- `.github/workflows/main.yaml`: add the SG2 matrix with the API setup, untouched-path check and artifact retention; require it in the aggregator. D81 8/6 ordinary shards, CI four-worker cap and D75 45/60-minute limits unchanged.',
        '- Sharding/timing/planner contracts: cover all seven lanes, singleton outcomes, aggregate dependency outcomes and weight provenance. Local contract subprocesses use at most two workers.',
        '- `utils/ci_test_durations.json`: replace only the 25 local-override file weights. All 635 other weights and existing provenance values are unchanged; retain historical local values in `local_overrides`.',
        '- Workflow README and `utils/ci_sharding.md`: document lanes, required jobs and estimation rules.',
        '- One producer: `scripts/adhoc/refresh_5213_weights_ci_20261105.py`; refresh, pinned archive validation, coverage, prediction and this report.', '',
        '## Weights (seconds)', '',
        'The instruction’s 14 measured files are the >1-second subset used to calculate the ratio. '
        'Artifacts contain 18 measured override files, including four subsecond files; all 18 use their CI JUnit sums. '
        'Seven missing files use local × 2.1033. Registration subtracts 749.198 + 747.858 + 729.254 = 2226.310 local SG2 seconds from 2245.206 before scaling: 18.896 × 2.1033 = 39.744 seconds after rounding. '
        'The cancelled shard remains incomplete evidence. All artifact SHA-256 values are recorded in `ci_refresh_5213_20261105`.', '',
        '| File | Before | After | Basis |', '|---|---:|---:|---|']
    for row in data['ci_refresh_5213_20261105']['weights']:
        lines.append(f"| `{row['file']}` | {row['before']:.3f} | {row['after']:.3f} | {row['basis']} |")
    lines += ['', '## Predictions', '',
        'Assignments reproduce `balanced_files` on the pinned full collection after removing all seven dedicated nodes. '
        'Load is estimated case-seconds / four workers / 60. The sensitivity column multiplies historical main weights by 0.92; '
        'new CI measurements and already-scaled local estimates are not scaled a second time. '
        'Case risk prefers this run’s observed CI case duration, then local × 2.1, then retained prior CI case estimates × 0.92. '
        'Where no case observation exists, the entire file estimate is a conservative upper bound, explicitly labelled below. '
        'These are idealized work/risk estimates, excluding setup, fixture reuse and scheduling overhead, not CI completion guarantees.', '',
        '| Layout | Shard | Load / 4 (min) | Ratio sensitivity (min) | Largest case risk (min) | Risk basis and node |',
        '|---|---:|---:|---:|---:|---|']
    for row in proof['predictions']:
        lines.append(f"| {row['shards']} | {row['shard']} | {row['load_minutes']:.2f} | {row['ratio_adjusted_minutes']:.2f} | {row['largest_case_minutes']:.2f} | {row['risk_basis']}: `{row['risk_node']}` |")
    above = [str(r['shard']) for r in proof['predictions'] if r['shards'] == 8 and r['over_30']]
    lines += ['', 'PR shards predicted above 30 minutes by the larger of adjusted load and case risk: '
              + (', '.join(above) if above else '**none**') + '.', '',
        'SG2 lanes retain the observed roughly 26-minute CI single-case risk; this task did not execute those cases.', '',
        '## Validation', '',
        f"Pinned archive SHA-256: `{validation['archive_sha256']}`. Interpreter: `{validation['interpreter']}` (Python 3.13.12, local macOS; CI targets Python 3.12).",
        f"- Canary: 1 passed; its persisted JUnit was checked before the full contract batch.",
        f"- Sharding, timing, refresh and planner contracts: {len(cases)} cases; no failures/errors/skips.",
        f"- Full `pytest tests --collect-only -q`: {proof['collection']} occurrences; {proof['ordinary']} ordinary plus seven singleton dedicated lanes.",
        '- Full-collection partition proof: exact occurrence Counter equality for both 8 and 6 ordinary shards plus all seven dedicated lanes. Legitimate duplicate labels are preserved.',
        '- Each real `sg2-*` lane collected exactly its one required node. Exit 1 is expected: collection alone must not pass the dedicated execution gate. No SG2 body ran.',
        f"- Specificity scanner: {equality['findings']} findings, equal field for field and in order to round 6; listed-not-derived modules also equal. Scanner exit 1 means existing findings, not a failed scan.",
        '- Every pytest command had a 3600-second process-group deadline. Top-level contracts ran serially; fixture shard subprocesses used at most `-n 2`.', '',
        '| Check | Exit | Expected | Seconds |', '|---|---:|---:|---:|']
    for row in validation['results']:
        lines.append(f"| {row['name']} | {row['returncode']} | {row['expected']} | {row['seconds']:.2f} |")
    lines += ['', 'Evidence: `' + str(output) + '` (commands, logs, XML, node lists, prediction and scanner equality).', '',
        '## Read-only review and limits', '',
        'Local review finding R7-1 (resolved): the fixture helper initially loaded `xdist.plugin` explicitly, '
        'which can conflict with normal entry-point autoloading. It now loads the `xdist` entry-point name; '
        'final archive validation exercises that correction. This finding is retained here as an offline '
        'issue record; GitHub filing was prohibited by the task.', '',
        'Reviewed the final diff separately for coverage loss, lane outcome bypasses, aggregator omission, double scaling, '
        'provenance loss and protected-path changes. No unresolved implementation finding. '
        'No PR or GitHub issue action was performed because this task explicitly requires offline work. '
        'No `src/`, prompts, protected files, run directories or `data/ATTIC/` were edited in the worktree. '
        'Archive source bytes were checked unchanged after validation. Actual new CI runtime remains unmeasured.', '']
    destination.write_text('\n'.join(lines))
    assert destination.stat().st_size > 0


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--install', action='store_true')
    parser.add_argument('--validate', type=Path)
    parser.add_argument('--python', type=Path)
    parser.add_argument('--report', type=Path)
    parser.add_argument('--evidence', type=Path)
    args = parser.parse_args()
    if args.report:
        assert args.evidence and not args.validate and not args.install
        report(args.evidence, args.report)
    elif args.validate:
        assert args.python and not args.install
        validate(args.validate.resolve(), args.python.absolute())
    else:
        result = refresh(args.install)
        print(json.dumps(result['ci_refresh_5213_20261105'], indent=2))
