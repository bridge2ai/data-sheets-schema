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
    paths = {n.split('::', 1)[0] for n in lanes['ordinary']}
    estimates = plugin._estimates(paths, weights)
    risks = {}
    for file in paths:
        candidates = observed.get(file) or historical_by_file.get(file)
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

    common = ['-m', 'pytest', '-p', 'xdist.plugin', '-p', 'no:cacheprovider', '-q']
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


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--install', action='store_true')
    parser.add_argument('--validate', type=Path)
    parser.add_argument('--python', type=Path)
    args = parser.parse_args()
    if args.validate:
        assert args.python and not args.install
        validate(args.validate.resolve(), args.python.absolute())
    else:
        result = refresh(args.install)
        print(json.dumps(result['ci_refresh_5213_20261105'], indent=2))
