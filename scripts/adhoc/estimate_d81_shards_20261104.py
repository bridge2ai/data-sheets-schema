#!/usr/bin/env python3
"""D81 / #5485, 2026-11-04: estimate PR 8/main 6 using unchanged R3 weights.

Inputs: hash-verified R3 CI/collection evidence and weights; current workflow.
Outputs: scratch estimates, job counts, scope proof and Markdown tables. With
--verify-tests, also verify the three requested test files and their artifacts.
No workflow/weights writes, network, provider calls or full-suite execution.
"""
import argparse
from collections import Counter
from copy import deepcopy
from decimal import Decimal
import json
from pathlib import Path
import shutil
import sys
import xml.etree.ElementTree as ET

sys.path.insert(0, str(Path(__file__).parent))
import refresh_ci_timings_r3_20261104 as r3

PARENT = '67647e33db83115f41d32f289a06d5e50b0f5609'
WEIGHTS_SHA256 = '845434a3e72483fb81a16d1634e84b06040d4d5864a3cb6cd2720bcd2c716305'
OUTPUT = r3.SCRATCH / 'd81-shards'
REPORT = r3.ROOT.parent / 'plans/reviews/bc1_g2_ci_r3_2026-11-04.md'


def build():
    import yaml
    weights, measured, _ = r3.build()
    assert r3.sha(r3.TIMING) == WEIGHTS_SHA256
    assert r3.TIMING.read_bytes() == r3.git('show', f'{PARENT}:utils/ci_test_durations.json')
    assert json.loads(r3.TIMING.read_text()) == weights
    assert measured['allowance_seconds'] == 615.2985
    before = yaml.safe_load(r3.git('show', f'{PARENT}:.github/workflows/main.yaml'))
    workflow = yaml.safe_load((r3.ROOT / '.github/workflows/main.yaml').read_text())
    ordinary = workflow['jobs']['python-tests']
    assert ordinary['strategy']['matrix']['shard'] == (
        "${{ fromJSON(github.event_name == 'pull_request' && '[1, 2, 3, 4, 5, 6, 7, 8]' || '[1, 2, 3, 4, 5, 6]') }}")
    old_command = before['jobs']['python-tests']['steps'][3]['run']
    expected_command = old_command.replace("'pull_request' && 6 || 4", "'pull_request' && 8 || 6")
    assert ordinary['steps'][3]['run'] == expected_command
    restored = deepcopy(workflow)
    restored['jobs']['python-tests']['strategy']['matrix']['shard'] = before['jobs']['python-tests']['strategy']['matrix']['shard']
    restored['jobs']['python-tests']['steps'][3]['run'] = old_command
    assert restored == before, 'workflow changes exceed matrix and denominator'
    from utils.pytest_shard import balanced_files, partition_lanes, shard_for
    nodes = json.loads(r3.COLLECTION.read_text())['nodes']
    lanes = partition_lanes(nodes)
    counts = Counter(n.split('::', 1)[0] for n in lanes['ordinary'])
    allowance = Decimal(str(measured['allowance_seconds']))
    plans = []
    for event, total, limit in [('pull_request', 8, 2700), ('main/manual', 6, 3600)]:
        assigned = balanced_files(counts, total, weights['file_seconds'])
        rows, union = [], Counter()
        for shard in range(1, total + 1):
            files = sorted(f for f in counts if assigned[f] == shard)
            cases = [n for n in lanes['ordinary'] if assigned[n.split('::', 1)[0]] == shard]
            union.update(cases)
            work = sum((Decimal(str(weights['file_seconds'][f])) for f in files), Decimal(0))
            estimate = work / 4 + allowance
            rows.append(dict(shard=shard, files=len(files), cases=len(cases),
                case_seconds=float(work), estimated_job_seconds=float(estimate),
                margin_to_eighty_percent_seconds=float(Decimal(limit) * Decimal('.8') - estimate)))
        assert union == Counter(lanes['ordinary'])
        for name, dedicated in lanes.items():
            if name != 'ordinary':
                union.update(dedicated)
        assert union == Counter(nodes)
        api_jobs = len(workflow['jobs']['api-completion']['strategy']['matrix']['case'])
        offline_jobs = sum(name in workflow['jobs'] for name in
                           ('offline-canary', 'offline-audit', 'offline-evaluation'))
        build_jobs = int(event != 'pull_request')
        python_jobs = total + api_jobs + offline_jobs + build_jobs
        plans.append(dict(event=event, shards=total, rows=rows, assignments=assigned,
            heaviest_seconds=max(r['estimated_job_seconds'] for r in rows),
            ordinary_jobs=total, api_jobs=api_jobs, offline_jobs=offline_jobs,
            schema_jobs=build_jobs, python_jobs=python_jobs,
            successes_including_aggregate=python_jobs + 1,
            expected_schema_skips=int(event == 'pull_request'),
            full_r3_occurrences_preserved=sum(union.values())))
    searches = ('d81-count-search.txt', 'd81-expression-search.txt',
                'd81-all-files-search.txt', 'd81-active-doc-candidates.txt')
    fixture_coverage = {}
    for number_of_files in range(16, 65):
        paths = [f'test_{n}.py' if n % 2 else f'{n}_test.py' for n in range(number_of_files)]
        coverage = {str(total): {str(i): sum(shard_for(p + '::test_values', total) == i for p in paths)
                    for i in range(1, total + 1)} for total in (6, 8)}
        if number_of_files == 16 or all(all(c.values()) for c in coverage.values()):
            fixture_coverage[str(number_of_files)] = coverage
        if all(all(c.values()) for c in coverage.values()):
            break
    return dict(parent=PARENT, weights_sha256=WEIGHTS_SHA256,
        r3_manifest_sha256=r3.sha(r3.MANIFEST), allowance_seconds=float(allowance),
        workflow_sha256=r3.sha(r3.ROOT / '.github/workflows/main.yaml'),
        only_matrix_and_denominator_changed=True, plans=plans,
        searches={name: r3.sha(r3.SCRATCH / name) for name in searches},
        synthetic_fixture_hash_coverage=fixture_coverage)


def tests(result):
    initial = r3.SCRATCH / 'd81-contracts'
    initial_rows = list(ET.parse(initial / 'junit.xml').iter('testcase'))
    failures = [c.attrib['name'] for c in initial_rows if c.find('failure') is not None]
    assert set(failures) == {
        'test_shards_cover_the_real_collection_exactly_once_with_xdist[False]',
        'test_explicit_lanes_and_real_shards_equal_full_default_collection[False-8]'}
    assert json.loads((initial / 'execution.json').read_text())['exit_code'] == 1
    result['initial_fixture_failure'] = dict(failed=failures, total=len(initial_rows),
        junit_sha256=r3.sha(initial / 'junit.xml'),
        reason='16 synthetic filenames leave hash shard 6 empty in an eight-shard partition.')
    for label in ('d81-canary-repaired', 'd81-contracts-final'):
        folder = r3.SCRATCH / label
        execution = json.loads((folder / 'execution.json').read_text())
        environment = json.loads((folder / 'environment.json').read_text())
        assert execution['exit_code'] == 0
        assert execution['deadline_seconds'] == 3600
        assert environment['timings_sha256'] == WEIGHTS_SHA256
        rows = list(ET.parse(folder / 'junit.xml').iter('testcase'))
        assert rows and not any(c.find(k) is not None for c in rows for k in ('failure', 'error', 'skipped'))
        counts = Counter(c.attrib['classname'] for c in rows)
        if label == 'd81-canary-repaired':
            assert counts == {'tests.test_ci_sharding': 1}
        else:
            assert counts['tests.test_ci_sharding'] == 48
            assert counts['tests.test_ci_timing_update'] == 13
            assert counts['tests.test_ci_bytecode_hygiene'] == 25
            assert len(counts) == 3
        origins = json.loads((folder / 'module-origins.json').read_text())
        assert all(r3.sha(Path(row['path'])) == row['sha256'] for row in origins.values())
        result[label] = dict(passed=len(rows), by_module=dict(counts),
            wall_seconds=execution['wall_seconds'], deadline_seconds=3600,
            artifacts={name: r3.sha(folder / name) for name in
                ('junit.xml', 'execution.json', 'environment.json', 'module-origins.json')})


def tables(result):
    lines = ['| Event | Shards | Heaviest job (s) | Margin below 80% (s) | Python jobs | Successes including aggregate | Expected skips |',
             '| --- | ---: | ---: | ---: | ---: | ---: | ---: |']
    for plan in result['plans']:
        margin = min(row['margin_to_eighty_percent_seconds'] for row in plan['rows'])
        lines.append(f"| {plan['event']} | {plan['shards']} | {plan['heaviest_seconds']:.6f} | "
            f"{margin:.6f} | {plan['python_jobs']} | {plan['successes_including_aggregate']} | "
            f"{plan['expected_schema_skips']} |")
    lines += ['', '| Event | Shard | Files | Cases (R3 collection) | Case-seconds | Estimated job seconds |',
              '| --- | ---: | ---: | ---: | ---: | ---: |']
    for plan in result['plans']:
        for row in plan['rows']:
            lines.append(f"| {plan['event']} | {row['shard']} | {row['files']} | {row['cases']} | "
                         f"{row['case_seconds']:.6f} | {row['estimated_job_seconds']:.6f} |")
    return '\n'.join(lines) + '\n'


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--verify-tests', action='store_true')
    parser.add_argument('--append-report', action='store_true')
    args = parser.parse_args()
    result = build()
    if args.verify_tests:
        tests(result)
    OUTPUT.mkdir(exist_ok=True)
    saved_report = OUTPUT / 'report-before-follow-up.md'
    if not saved_report.exists():
        shutil.copyfile(REPORT, saved_report)
    assert REPORT.read_bytes().startswith(saved_report.read_bytes())
    result['original_report_sha256'] = r3.sha(saved_report)
    r3.save(OUTPUT / 'estimates.json', result)
    (OUTPUT / 'tables.md').write_text(tables(result))
    assert (OUTPUT / 'tables.md').read_text() == tables(result)
    print(tables(result))
    print('Synthetic fixture hash coverage:', json.dumps(result['synthetic_fixture_hash_coverage']))
    for label in ('d81-canary-repaired', 'd81-contracts-final'):
        if label in result:
            print(label, json.dumps(result[label]))
    if args.append_report:
        assert args.verify_tests
        commit = r3.git('rev-parse', 'HEAD').decode().strip()
        assert r3.git('rev-parse', 'HEAD^').decode().strip() == PARENT
        assert r3.git('log', '-1', '--format=%s').decode().strip() == 'ci: run PRs on 8 shards and main on 6 (D81)'
        assert REPORT.read_bytes() == saved_report.read_bytes(), 'append exactly once to the original report'
        final = result['d81-contracts-final']
        summary = (f"Final validation: **{final['passed']} passed, zero failed/errors/skips**: "
                   "48 sharding, 13 timing-update and 25 bytecode-hygiene cases. "
                   f"Supervised wall time **{final['wall_seconds']:.3f} s**, under the "
                   "3600-second deadline, serial outer pytest / at most two nested workers. "
                   "The one warning is the existing dateutil deprecation. "
                   "Evidence: `scratch-bc1g2-timing/d81-contracts-final/`; "
                   "counts, module-source checks and artifact hashes are in `d81-shards/estimates.json`.")
        draft = (OUTPUT / 'follow-up-draft.md').read_text()
        assert draft.count('COMMIT_SHA') == draft.count('TEST_RESULTS') == 1
        appendix = draft.replace('COMMIT_SHA', commit).replace('TEST_RESULTS', summary)
        REPORT.write_bytes(saved_report.read_bytes() + appendix.encode())
        assert REPORT.read_bytes() == saved_report.read_bytes() + appendix.encode()
        print('Appended D81 report for', commit)
