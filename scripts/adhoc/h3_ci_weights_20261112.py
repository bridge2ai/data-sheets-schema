"""H3 timing evidence and native-only weight supplement, 2026-11-12.

Inputs: downloaded CI 42976790438 artifacts, retained AGY analysis helpers,
current partition code and weights. Outputs: scratch JSON, optional weights.
Serves helper3 assignment. Never edits workflow or scanner; no network.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import statistics
import subprocess
from collections import Counter, defaultdict
from datetime import datetime

ROOT = Path(__file__).resolve().parents[2]
E = ROOT.parent
R = E / 'codex-development-efficiency-20261111'
OUT = E / 'scratch-h3-ci-20261112'
ART = Path('/Users/marcin/agent-work/data-sheets-schema/ci-run-42976790438')
def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--write', action='store_true')
    args = parser.parse_args()
    prior = load('h3_prior', R / 'scripts/adhoc/native_ci_shard_time_20261112.py')
    partition = load('h3_partition', ROOT / 'utils/pytest_shard.py')
    updater = load('h3_updater', ROOT / 'utils/update_ci_shard_timings.py')
    tracked = set(subprocess.check_output(['git', '-C', str(ROOT), 'ls-files', 'tests'], text=True).splitlines())
    paths = sorted(p for p in tracked if p.endswith('.py') and Path(p).name.startswith('test_') and p != 'tests/test_renderer.py')
    baseline = json.loads(subprocess.check_output(['git', '-C', str(ROOT), 'show', 'ab07c81fe:utils/ci_test_durations.json']))
    prior_rows = json.loads((R / 'notes/development_efficiency_20261111/handoffs/agy1-native-ci-shard-time-20261112.json').read_text())['measured_file_seconds_all_714']
    measured, evidence, artifacts = {}, {}, []
    for shard in range(1, 9):
        xml = ART / f'tests-py3.12-shard{shard}/pytest.xml'
        source = xml if xml.exists() else ART / f'logs/shard{shard}.log'
        data = prior.parse_junit_xml(source, tracked) if xml.exists() else prior.parse_job_log(source)
        artifacts.append({'path': str(source), 'sha256': sha(source)})
        for path, seconds in data['file_seconds'].items():
            assert path not in measured
            measured[path] = max(.001, round(seconds, 3))
            evidence[path] = {'seconds': measured[path], 'completed_cases': data['file_cases'][path],
                'expected_cases_in_original_run': prior_rows.get(path, {}).get('expected_cases'),
                'source': 'junit' if xml.exists() else 'worker_completion_intervals', 'shard': shard}
    try:
        updater.build(ART, ROOT, 42976790438, '1a137b58860416a31618de44173180d021dfcc61')
    except ValueError as exc:
        updater_refusal = str(exc)
    else:
        raise AssertionError('Expected failed-run refusal')
    native = {p: s for p, s in measured.items() if Path(p).name.startswith('test_native_')}
    weights = {**baseline['file_seconds'], **native}
    fallback = statistics.median(weights[p] for p in paths if p in weights)
    missing = [{'file': p, 'weight': weights.get(p, fallback), 'uses_fallback': p not in weights}
               for p in paths if Path(p).name.startswith('test_native_') and p not in measured]
    models = {'native_only': weights, 'all_measured': {**baseline['file_seconds'], **measured}}
    scanner_cases, previous = [], {}
    scanner_classes = defaultdict(lambda: {'seconds': 0.0, 'outcomes': Counter()})
    log_meta = prior.parse_job_log(ART / 'logs/shard8.log')
    start = datetime.fromisoformat(log_meta['workers_created_timestamp'])
    for raw in (ART / 'logs/shard8.log').read_text().splitlines():
        match = prior.LOG_LINE_RE.match(prior.ANSI_RE.sub('', raw.lstrip('\ufeff')))
        if not match:
            continue
        stamp, body = match.groups()
        row = prior.RESULT_RE.search(body)
        if not row:
            continue
        worker, _, outcome, node = row.groups()
        timestamp = datetime.fromisoformat(stamp.replace('Z', '+00:00'))
        seconds = (timestamp - previous.get(worker, start)).total_seconds()
        previous[worker] = timestamp
        if not node.startswith('tests/test_generation_specificity_skill.py::'):
            continue
        scanner_cases.append({'node': node, 'outcome': outcome, 'seconds': seconds, 'worker': worker})
        group = scanner_classes[node.split('::')[1]]
        group['seconds'] += seconds
        group['outcomes'][outcome] += 1
    predictions = {name: prior.evaluate_partition(partition, paths, [6, 8, 9, 10, 12, 16], values,
                   {**baseline['file_seconds'], **measured}) for name, values in models.items()}
    # Hypothetical equal split: an explicit scenario, not observed test-file timings.
    long = 'tests/test_generation_specificity_skill.py'
    split_paths = [p for p in paths if p != long] + [f'{long}.part{i}.py' for i in range(4)]
    split_weights = {p: s for p, s in models['all_measured'].items() if p != long}
    split_weights.update({f'{long}.part{i}.py': measured[long] / 4 for i in range(4)})
    predictions['all_measured_equal_four_way_scanner_split'] = prior.evaluate_partition(
        partition, split_paths, [8, 9, 10, 12], split_weights, split_weights)
    result = {'artifacts': artifacts, 'updater_refusal': updater_refusal,
        'prior_parser_sha256': sha(R / 'scripts/adhoc/native_ci_shard_time_20261112.py'),
        'partition_sha256': sha(ROOT / 'utils/pytest_shard.py'),
        'workflow_sha256': sha(ROOT / '.github/workflows/main.yaml'),
        'baseline_weight_sha256': hashlib.sha256(subprocess.check_output(['git', '-C', str(ROOT), 'show', 'ab07c81fe:utils/ci_test_durations.json'])).hexdigest(),
        'native_measured_count': len(native), 'new_native_entries': len(set(native) - set(baseline['file_seconds'])),
        'baseline_fallback_seconds': statistics.median(baseline['file_seconds'][p] for p in paths if p in baseline['file_seconds']),
        'scanner_file_observation': evidence['tests/test_generation_specificity_skill.py'],
        'baseline_scanner_weight_seconds': baseline['file_seconds']['tests/test_generation_specificity_skill.py'],
        'scanner_ci_classes': dict(sorted(scanner_classes.items(), key=lambda item: -item[1]['seconds'])),
        'scanner_ci_cases': sorted(scanner_cases, key=lambda row: -row['seconds']),
        'native_measurements': {p: evidence[p] for p in native}, 'native_without_measurement': missing,
        'fallback_seconds': fallback, 'collected_path_model_count': len(paths),
        'path_model_note': 'Tracked test files excluding known zero-case test_renderer; includes repaired test_driver. Full collection has independent missing fairscape submodule errors.',
        'predictions': predictions,
        'measurement_limits': 'Failed run; JUnit failure times are not successful full-path times. Shards 5 and 8 use completion intervals including idle/scheduling gaps, not JUnit durations. Unfinished cases absent. Predictions are summed weights and ideal four-worker averages, never wall-time guarantees.'}
    (OUT / 'weights-analysis.json').write_text(json.dumps(result, indent=2) + '\n')
    if args.write:
        baseline['file_seconds'] = dict(sorted(weights.items()))
        baseline['source']['native_ci_h3_20261112'] = {
            'run_id': 42976790438, 'commit': '1a137b58860416a31618de44173180d021dfcc61',
            'artifacts': artifacts, 'files': {p: evidence[p] for p in sorted(native)},
            'method': result['measurement_limits'], 'updater_refusal': updater_refusal,
            'producer': str(Path(__file__).relative_to(ROOT))}
        (ROOT / 'utils/ci_test_durations.json').write_text(json.dumps(baseline, indent=2) + '\n')
    print(json.dumps({k: result[k] for k in ('native_measured_count', 'new_native_entries', 'fallback_seconds', 'updater_refusal')}, indent=2))
if __name__ == '__main__':
    main()
