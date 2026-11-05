#!/usr/bin/env python3
"""#5485 follow-up, 2026-11-03: derive six weights using authorized 2.729 ratio.

Inputs: first timing commit, its pinned XML/collection manifest, local/CI paired
measurements. Outputs: six derived weights, scratch plans/proof and report tables.
Preserves the first refresh and all its evidence. No network or provider calls.
"""
import argparse
from collections import Counter
from datetime import datetime
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

sys.path.insert(0, str(Path(__file__).parent))
import refresh_ci_timings_bc1g2_20261103 as base

PARENT = '6e578a6007a60b08bb37c0a29b66581d4dd5c6c4'
RATIO = Decimal('2.729')
FILES = (
    'tests/test_bc1_audit.py', 'tests/test_bc1_g2_journal.py',
    'tests/test_bc1_registration.py', 'tests/test_bc1_runtime.py',
    'tests/test_g2_round2.py', 'tests/test_wave7_bc1_formatter_cache.py',
)
EVIDENCE = ('tests/test_shared_generation_runtime.py', 'tests/test_d42_claude_d55.py')
OUTPUT = base.SCRATCH / 'measured-ratio-scaling'
MANIFEST = base.NOTE / 'input-manifest.json'


def build():
    unscaled, measured, nodes, records = base.measure(MANIFEST)
    raw = base.git('show', f'{PARENT}:utils/ci_test_durations.json')
    original = json.loads(raw)
    if unscaled != original:
        raise ValueError('pinned measurements do not reproduce the first commit')
    selected = {r['file']: r for r in measured['missing_files'] if r['source'] == 'local-with'}
    if set(selected) != set(FILES):
        raise ValueError('local-source file set changed')
    comparisons = {r['file']: r for r in measured['comparisons']}
    xml_hashes = {r['path']: r['sha256'] for r in json.loads(MANIFEST.read_text())['xml']}
    evidence = []
    for file in EVIDENCE:
        if file not in comparisons:
            raise ValueError(f'comparison lacks complete matching collection: {file}')
        pair = dict(file=file)
        for source, label in (('local-with', 'local'), ('bc1g2', 'linux_ci')):
            rows = records[source][file]
            seconds = sum((Decimal(r['seconds_decimal']) for r in rows), Decimal(0))
            pair[label] = dict(measured_seconds=float(seconds), cases=len(rows),
                artifacts=[dict(path=p, sha256=xml_hashes[p])
                           for p in sorted({r['artifact'] for r in rows})])
        quotient = Decimal(str(pair['linux_ci']['measured_seconds'])) / Decimal(str(pair['local']['measured_seconds']))
        pair['observed_ratio'] = str(quotient)
        pair['ratio_rounded_to_three_decimals'] = float(quotient.quantize(Decimal('0.001')))
        evidence.append(pair)
    if max(Decimal(str(p['ratio_rounded_to_three_decimals'])) for p in evidence) != RATIO:
        raise ValueError('observed rounded maximum differs from authorized multiplier')
    new = json.loads(raw)
    derivations = {}
    for file in FILES:
        local_sum = sum((Decimal(r['seconds_decimal']) for r in records['local-with'][file]), Decimal(0))
        if float(local_sum) != original['file_seconds'][file]:
            raise ValueError(f'prior weight differs from local sum: {file}')
        weight = local_sum * RATIO
        derivations[file] = dict(value_kind='derived', local_sum_seconds=float(local_sum),
            applied_ratio=float(RATIO), derived_seconds=float(weight),
            local_artifacts=[dict(path=p, sha256=xml_hashes[p]) for p in selected[file]['artifacts']],
            ratio_evidence=evidence)
        new['file_seconds'][file] = float(weight)
    changed = {p for p in new['file_seconds'] if new['file_seconds'][p] != original['file_seconds'][p]}
    if changed != set(FILES) or set(new['file_seconds']) != set(original['file_seconds']):
        raise ValueError('weight changes exceed the six authorized files')
    new['source']['bc1_g2_measured_ratio_scaling_20261103'] = dict(
        parent_commit=PARENT, parent_weights_sha256=hashlib.sha256(raw).hexdigest(),
        manifest_sha256=base.sha(MANIFEST),
        authorization='Lead follow-up: exactly six local-source weights = local sum x 2.729.',
        method='Use the larger of the two observed complete-file CI/local ratios rounded to '
        'three decimal places as explicitly requested. Values are derived scheduling weights, '
        'not measured Linux runtimes; preserve all other weights and prior measurements.',
        files=derivations)
    new['method'] += (' Follow-up: measured-ratio scaling (2026-11-03) supersedes only the six '
        'initial local-source weights with local sum x 2.729, the larger of two observed '
        'complete-file Linux-CI/local ratios rounded to three decimals, as authorized by the lead. '
        'These six weights are derived, not measured; source.bc1_g2_measured_ratio_scaling_20261103 '
        'records each local sum, multiplier and both paired measurements with XML hashes. '
        'All other weights and the prior measured provenance remain unchanged.')
    sys.path.insert(0, str(base.ROOT))
    from utils.pytest_shard import balanced_files, partition_lanes
    lanes = partition_lanes(nodes)
    ordinary = lanes.pop('ordinary')
    counts = Counter(n.split('::', 1)[0] for n in ordinary)
    # Recompute the same empirical allowance from the already hash-checked input.
    jobs = json.loads((base.SCRATCH / 'run-41707437114/jobs.json').read_text())['jobs']
    residuals = []
    for shard in (2, 3, 4, 6):
        job, = [j for j in jobs if j['name'] == f'Python 3.12 / shard {shard}']
        wall = Decimal(str((datetime.fromisoformat(job['completedAt'].replace('Z', '+00:00')) -
                           datetime.fromisoformat(job['startedAt'].replace('Z', '+00:00'))).total_seconds()))
        path = base.SCRATCH / f'run-41707437114/tests-py3.12-shard{shard}/pytest.xml'
        case_sum = sum((Decimal(c.attrib['time']) for c in ET.parse(path).iter('testcase')), Decimal(0))
        residuals.append(wall - case_sum / 4)
    allowance = max(Decimal(0), *residuals)
    assert allowance == Decimal('330.553')
    plans = []
    for total in (6, 4):
        assigned = balanced_files(counts, total, new['file_seconds'])
        rows, union = [], Counter()
        for shard in range(1, total + 1):
            paths = sorted(p for p in counts if assigned[p] == shard)
            selected_nodes = [n for n in ordinary if assigned[n.split('::', 1)[0]] == shard]
            union.update(selected_nodes)
            seconds = sum((Decimal(str(new['file_seconds'][p])) for p in paths), Decimal(0))
            ideal, threshold = seconds / 4, Decimal(2160 if total == 6 else 2880)
            projected = ideal + allowance
            rows.append(dict(shard=shard, files=len(paths), cases=len(selected_nodes),
                case_seconds=float(seconds), ideal_four_worker_seconds=float(ideal),
                projected_job_seconds=float(projected), eighty_percent_seconds=float(threshold),
                margin_seconds=float(threshold - projected)))
        assert union == Counter(ordinary)
        for dedicated in lanes.values():
            union.update(dedicated)
        assert union == Counter(nodes)
        plans.append(dict(shards=total, rows=rows, assignments=assigned,
                          full_collection_preserved=len(nodes)))
    slowest = measured['slowest_cases'][:3]
    result = dict(parent=PARENT, ratio_evidence=evidence, files=derivations,
        original_weights_preserved=len(original['file_seconds']) - len(FILES),
        allowance_seconds=float(allowance), plans=plans,
        slowest_cases=[dict(nodeid=r['nodeid'], measured_local_seconds=r['seconds'],
            pr_shard=plans[0]['assignments'][r['file']], main_shard=plans[1]['assignments'][r['file']])
            for r in slowest],
        increased_case_seconds=float(sum(Decimal(str(new['file_seconds'][p])) -
            Decimal(str(original['file_seconds'][p])) for p in FILES)))
    return new, result, raw


def tables(result):
    lines = ['| File (`tests/`) | Local sum (s) | Ratio | Derived weight (s) | PR shard | Main shard |',
             '| --- | ---: | ---: | ---: | ---: | ---: |']
    for file, row in result['files'].items():
        lines.append(f"| {file.removeprefix('tests/')} | {row['local_sum_seconds']:.3f} | 2.729 | "
            f"{row['derived_seconds']:.6f} | {result['plans'][0]['assignments'][file]} | "
            f"{result['plans'][1]['assignments'][file]} |")
    lines += ['', '| Plan | Shard | Cases | Case-seconds | Estimated job (s) | Margin below 80% (s) |',
              '| --- | ---: | ---: | ---: | ---: | ---: |']
    for plan in result['plans']:
        for row in plan['rows']:
            label = 'PR / 6' if plan['shards'] == 6 else 'Main / 4'
            lines.append(f"| {label} | {row['shard']} | {row['cases']} | {row['case_seconds']:.6f} | "
                         f"{row['projected_job_seconds']:.6f} | {row['margin_seconds']:.6f} |")
    lines += ['', '| Case | Measured local seconds | PR shard | Main shard |', '| --- | ---: | ---: | ---: |']
    for row in result['slowest_cases']:
        lines.append(f"| `{row['nodeid']}` | {row['measured_local_seconds']:.3f} | {row['pr_shard']} | {row['main_shard']} |")
    return '\n'.join(lines) + '\n'


def verify_tests(result):
    focused = base.SCRATCH / 'scaled-focused'
    execution = json.loads((focused / 'execution.json').read_text())
    environment = json.loads((focused / 'environment.json').read_text())
    assert execution['exit_code'] == 0 and environment['timings_sha256'] == base.sha(base.TIMING)
    cases = list(ET.parse(focused / 'junit.xml').iter('testcase'))
    assert Counter(c.attrib['classname'] for c in cases) == {
        'tests.test_ci_sharding': 48, 'tests.test_ci_timing_update': 13}
    assert not any(c.find(kind) is not None for c in cases for kind in ('failure', 'error', 'skipped'))
    canary = base.SCRATCH / 'scaled-canary'
    assert json.loads((canary / 'execution.json').read_text())['exit_code'] == 0
    assert json.loads((canary / 'environment.json').read_text())['timings_sha256'] == base.sha(base.TIMING)
    canary_cases = list(ET.parse(canary / 'junit.xml').iter('testcase'))
    assert len(canary_cases) == 1 and not any(canary_cases[0].find(kind) is not None
                                            for kind in ('failure', 'error', 'skipped'))
    report = base.ROOT.parent / 'plans/reviews/bc1_g2_ci_timing_2026-11-03.md'
    assert report.read_bytes().startswith((OUTPUT / 'report-before-follow-up.md').read_bytes())
    result['validation'] = dict(passed=len(cases), failed=0, errors=0, skipped=0,
        wall_seconds=execution['wall_seconds'], deadline_seconds=execution['deadline_seconds'],
        junit_sha256=base.sha(focused / 'junit.xml'), weights_sha256=base.sha(base.TIMING),
        canary_passed=1, canary_junit_sha256=base.sha(canary / 'junit.xml'),
        previous_report_preserved_as_prefix=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true')
    parser.add_argument('--verify-tests', action='store_true')
    args = parser.parse_args()
    new, result, original = build()
    encoded = (json.dumps(new, indent=2) + '\n').encode()
    if args.apply:
        if base.TIMING.read_bytes() not in (original, encoded):
            raise ValueError('refuse to overwrite unrelated timing edits')
        base.save(base.TIMING, new)
    if args.verify_tests:
        assert base.TIMING.read_bytes() == encoded
        verify_tests(result)
    result['weights_sha256'] = hashlib.sha256(encoded).hexdigest()
    base.save(OUTPUT / 'proposed-timings.json', new)
    base.save(OUTPUT / 'evidence.json', result)
    (OUTPUT / 'tables.md').write_text(tables(result))
    assert (OUTPUT / 'tables.md').read_text() == tables(result)
    print(tables(result))
    print('Weights SHA256:', result['weights_sha256'])
    print('Additional case-seconds:', result['increased_case_seconds'])
    print('Ratio evidence:', json.dumps(result['ratio_evidence']))
    if 'validation' in result:
        print('Validation:', json.dumps(result['validation']))


if __name__ == '__main__':
    main()
