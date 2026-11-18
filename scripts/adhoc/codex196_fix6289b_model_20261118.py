"""Build corrected issue 6289 scheduling inputs and bounded forecasts; 2026-11-18.

Inputs: current JUnit artifacts, cancelled logs, retained prior simulation inputs.
Outputs: candidate weights, exact pending inventory, compact simulation evidence.
No code changes, tests, native calls, or provider calls. Censored/failed times
remain explicitly separate from measured successful completion durations.
"""
from collections import Counter, defaultdict
from copy import deepcopy
from decimal import Decimal
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

sys.dont_write_bytecode = True
BASE = Path('/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions')
R = BASE / 'codex-development-efficiency-20261111'
W = BASE / 'codex196-fix6289b-20261118'
S = BASE / 'scratch-codex196-fix6289b-20261118/f3'
OLD = BASE / 'scratch-codex196-fix6289-20261118'


def load(path):
    return json.loads(path.read_bytes())


def encode(value):
    return (json.dumps(value, indent=2, sort_keys=True, allow_nan=False).replace(chr(64), '\\u0040') + '\n').encode()


def pin(path):
    raw = path.read_bytes()
    return {'path': str(path), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def save(name, value):
    target = S / name
    raw = encode(value)
    if target.exists() and target.read_bytes() != raw:
        raise ValueError('refusing overwrite: ' + str(target))
    target.write_bytes(raw)
    return pin(target)


def module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def main():
    sim = module(R / 'scripts/adhoc/codex196_fix6289_simulate_20261118.py', 'capacity_simulator')
    sharder, sharder_path = sim.load_sharder(W)
    previous = load(OLD / 'simulation-final-inputs-001/nominal.json')
    all_nodes = sim.collection(Path(previous['inputs']['collection']['path']))
    ordinary = sharder.partition_lanes(all_nodes)['ordinary']
    node_counts = Counter(ordinary)
    file_counts = Counter(node.split('::', 1)[0] for node in ordinary)
    old_weights = load(Path(previous['inputs']['weights']['path']))['file_seconds']
    assignment = sharder.balanced_files(file_counts, 12, old_weights)
    cancelled = load(S / 'cancelled-shards.json')['shards']
    pending = {}
    floors = {}
    masked_prefix = 'tests/test_native_execution_ci_v2.py::test_repository_configuration_refuses_noncanonical_origin['
    masked_node = masked_prefix + '***github.com/o/r.git]'
    original_node = next(node for node in ordinary if node.startswith(masked_prefix + 'https://user:password'))
    def alias(node):
        return original_node if node == masked_node else node
    for shard, row in cancelled.items():
        selected = Counter(node for node in ordinary if assignment[node.split('::', 1)[0]] == int(shard))
        starts = Counter(alias(item['node']) for item in row['starts'])
        finishes = Counter(alias(item['node']) for item in row['finishes'])
        if sum(selected.values()) != row['items'] or starts - selected or finishes - selected:
            raise ValueError('collection/assignment does not match CI shard ' + shard)
        unstarted = list((selected - starts).elements())
        unfinished = list((starts - finishes).elements())
        pending[shard] = {'collected': row['items'], 'completed': sum(finishes.values()),
                          'unfinished': row['unfinished'], 'unstarted': unstarted,
                          'unfinished_nodeids': unfinished,
                          'not_completed': list((selected - finishes).elements())}
        for item in row['unfinished']:
            floors[item['node']] = item['elapsed_until_cancellation_seconds']
    class_lookup = defaultdict(set)
    for node in ordinary:
        filename, tail = node.split('::', 1)
        before, separator, parameters = tail.partition('[')
        parts = before.split('::')
        classname = filename[:-3].replace('/', '.')
        if len(parts) > 1:
            classname += '.' + '.'.join(parts[:-1])
        testname = parts[-1] + separator + parameters
        class_lookup[(classname, testname)].add(node)
    current = defaultdict(list)
    per_file = defaultdict(Decimal)
    artifact_rows = []
    unmatched = []
    for path in sorted((S / 'artifacts').glob('tests-py3.12-shard*/pytest.xml')):
        shard = int(path.parent.name.split('shard')[1])
        count = 0
        for case in ET.parse(path).iter('testcase'):
            identity = (case.get('classname'), case.get('name'))
            matches = class_lookup[identity]
            if len(matches) != 1:
                unmatched.append({'shard': shard, 'classname': identity[0], 'name': identity[1]})
                continue
            node = next(iter(matches))
            status = ('failed' if case.find('failure') is not None else
                      'error' if case.find('error') is not None else
                      'skipped' if case.find('skipped') is not None else 'passed')
            value = Decimal(case.get('time'))
            per_file[node.split('::', 1)[0]] += value
            current[node].append({'seconds': float(value), 'status': status, 'shard': shard,
                                  'junit': str(path)})
            count += 1
        artifact_rows.append({'shard': shard, 'matched_occurrences': count, 'input': pin(path)})
    if unmatched:
        save('unmatched-current-junit.json', unmatched)
        raise ValueError('unmatched current JUnit cases')
    prior = {node: row['observed_seconds'] for node, row in previous['observed_nodes'].items()}
    durations = dict(prior)
    for node, records in current.items():
        durations[node] = max(record['seconds'] for record in records)
    known = {}
    for node in ordinary:
        old = prior.get(node)
        measured = max((row['seconds'] for row in current.get(node, [])), default=None)
        if measured is not None:
            known[node] = {'seconds': measured, 'basis': 'current_junit', 'occurrences': current[node]}
        elif old is not None:
            known[node] = {'seconds': old, 'basis': 'retained_prior_observation'}
    weights = dict(old_weights)
    weights.update({path: float(max(value, Decimal('0.001'))) for path, value in per_file.items()})
    # A cancelled node is no longer zero or an old low estimate. This is only
    # the observed censoring floor; it is never an estimated completion bound.
    for path in {node.split('::', 1)[0] for node in floors}:
        members = [node for node in ordinary if node.split('::', 1)[0] == path]
        total = sum(max(durations.get(node, 0), floors.get(node, 0)) for node in members)
        weights[path] = max(weights.get(path, 0), round(total, 3))
    # Keep the unmeasured rehearsal sensitivity from the earlier plan.
    for node, value in previous['explicit_node_floors'].items():
        if node not in current and node not in floors and node in ordinary:
            floors[node] = value
    identities = {'producer': pin(Path(__file__)), 'prior_report': pin(OLD / 'simulation-final-inputs-001/nominal.json'),
                  'old_collection': previous['inputs']['collection'], 'sharder': pin(sharder_path),
                  'cancelled_log_analysis': pin(S / 'cancelled-shards.json'), 'artifacts': artifact_rows}
    save('pending-inventory.json', {'shards': pending, 'inputs': identities,
        'scope': 'Exact old-head collection and candidate file assignment verified against each cancelled CI header.'})
    save('current-node-measurements.json', {node: {'seconds': max(row['seconds'] for row in rows),
        'outcomes': [row['status'] for row in rows], 'occurrences': rows} for node, rows in current.items()})
    save('combined-node-seconds.json', {node: row['seconds'] for node, row in known.items()})
    save('censored-node-floors.json', floors)
    save('candidate-effective-weights.json', {'schema_version': 1, 'file_seconds': weights})
    save('file-estimate-provenance.json', {'current_run': 44235627132,
        'current_junit_file_seconds': {path: float(value) for path, value in per_file.items()},
        'censored_floor_adjusted_files': {path: weights[path] for path in weights if
            any(node.startswith(path + '::') for node in floors)},
        'failed_current_nodes': {node: rows for node, rows in current.items() if
            any(row['status'] in ('failed', 'error') for row in rows)},
        'sources': identities,
        'warning': 'Failed-path durations and censoring floors do not establish successful full completion times.'})
    print(encode({'pending': pending, 'current_artifact_count': len(artifact_rows),
                  'current_occurrences': sum(len(rows) for rows in current.values()),
                  'measured_files': len(per_file), 'current_unmatched': unmatched,
                  'censored_floor_files': {path: weights[path] for path in weights if any(
                      node.startswith(path + '::') for node in floors)},
                  'packet_shards': sorted({row['shard'] for node, rows in current.items()
                                          if 'test_native_packet_full_chain.py::' in node for row in rows})}).decode())


if __name__ == '__main__':
    main()
