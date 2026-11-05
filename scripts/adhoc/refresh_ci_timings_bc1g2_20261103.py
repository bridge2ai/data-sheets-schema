#!/usr/bin/env python3
"""#5485, 2026-11-03: add only missing BC1/G2 timing weights, offline.

Inputs: current collection; saved BC1/G2, G1 and round-2-with JUnit; pinned
input manifest. Outputs: additive timing snapshot and scratch audit/plans.
The run command supervises pytest for 3600 s, serial outside / <=2 nested workers.
"""
import argparse
from collections import Counter, defaultdict
from decimal import Decimal
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
HEAD = '0ff5c9ba7665eb51b69e597c391cb1ae6a07c44c'
G1 = 'bc8f981f758c46d5bb027c61294d8a67bf70ed30'
SCRATCH = ROOT.parent / 'scratch-bc1g2-timing'
LOCAL = ROOT.parent / 'plans/reviews/bc1_g2_integration_2026-11-03/round2/evidence/with'
NOTE = ROOT / 'notes/ci_timing_refresh_2026-11-03'
TIMING = ROOT / 'utils/ci_test_durations.json'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + '\n')
    if json.loads(path.read_text()) != value:
        raise ValueError(f'readback failed: {path}')


def git(*args):
    return subprocess.check_output(['git', '--no-replace-objects', *args], cwd=ROOT)


def run(label, args):
    directory = SCRATCH / label
    directory.mkdir()  # preserve all earlier evidence
    command = [sys.executable, '-S', '-P', '-B', str(Path(__file__).resolve()),
               'worker', '--label', label, '--', *args]
    started = time.monotonic()
    with (directory / 'pytest.log').open('w') as stream:
        child = subprocess.Popen(command, cwd=ROOT, stdout=stream,
                                 stderr=subprocess.STDOUT, start_new_session=True)
        try:
            code = child.wait(timeout=3600)
        except subprocess.TimeoutExpired:
            os.killpg(child.pid, signal.SIGTERM)
            try:
                child.wait(timeout=10)
            except subprocess.TimeoutExpired:
                os.killpg(child.pid, signal.SIGKILL)
                child.wait()
            code = 124
    save(directory / 'execution.json', dict(command=command, exit_code=code,
         deadline_seconds=3600, wall_seconds=time.monotonic() - started))
    print(json.dumps(json.loads((directory / 'execution.json').read_text())))
    return code


def worker(label, args):
    sys.path.insert(0, str(Path(__file__).parent))
    from d41_legacy_controls_20261029 import bootstrap, origins
    directory = SCRATCH / label
    environment = bootstrap(ROOT, directory)
    # Read the already-present pinned submodule; never initialize or fetch it.
    fairscape = ROOT.parent.parent / 'data-sheets-schema/fairscape_models'
    environment['fairscape_commit'] = subprocess.check_output(
        ['git', '-C', str(fairscape), 'rev-parse', 'HEAD'], text=True).strip()
    sys.path.insert(0, str(fairscape))
    os.environ['PYTHONPATH'] += os.pathsep + str(fairscape)
    os.environ['PYTEST_XDIST_AUTO_NUM_WORKERS'] = '2'
    os.environ['PYTEST_ADDOPTS'] = '--rootdir=. -p xdist.plugin'
    os.environ['TMPDIR'] = str(directory / 'temporary')
    import tempfile
    tempfile.tempdir = os.environ['TMPDIR']
    import pytest

    class Observer:
        nodes = []
        errors = []

        def pytest_collection_finish(self, session):
            self.nodes = [item.nodeid for item in session.items]

        def pytest_collectreport(self, report):
            if report.failed:
                self.errors.append(str(report.longrepr))

    observer = Observer()
    environment['head'] = git('rev-parse', 'HEAD').decode().strip()
    environment['timings_sha256'] = sha(TIMING)
    save(directory / 'environment.json', environment)
    code = pytest.main([*args, '-p', 'no:cacheprovider',
        '--basetemp', str(directory / 'temporary/pytest'),
        '--junitxml', str(directory / 'junit.xml')], plugins=[observer])
    save(directory / 'collection.json', dict(nodes=observer.nodes,
        errors=observer.errors, exit_code=int(code), head=environment['head']))
    save(directory / 'module-origins.json', origins(ROOT))
    return int(code)


def inputs():
    """Explicit read-only roots; Path.glob includes gitignored files."""
    roots = {'bc1g2': SCRATCH / 'run-41707437114',
             'g1': SCRATCH / 'run-41700664435', 'local-with': LOCAL}
    records = []
    for source, root in roots.items():
        pattern = 'group-*/junit.xml' if source == 'local-with' else 'tests-py3.12-shard*/pytest.xml'
        for path in sorted(root.glob(pattern)):
            records.append(dict(source=source, path=str(path.relative_to(ROOT.parent)), sha256=sha(path)))
    return records


def pin_inputs():
    collection = SCRATCH / 'collection/collection.json'
    target = SCRATCH / 'input-manifest.json'
    if target.exists():
        raise ValueError('retain the existing manifest')
    metadata = []
    for run_id, commit in ((41707437114, HEAD), (41700664435, G1)):
        root = SCRATCH / f'run-{run_id}'
        data = json.loads((root / 'run_metadata.json').read_text())
        if data['id'] != run_id or data['head_sha'] != commit:
            raise ValueError('saved run identity mismatch')
        for name in ('run_metadata.json', 'artifacts_roster.json', 'jobs.json'):
            path = root / name
            metadata.append(dict(path=str(path.relative_to(ROOT.parent)), sha256=sha(path)))
    save(target, dict(head=HEAD, collection_path=str(collection.relative_to(ROOT.parent)),
        collection_sha256=sha(collection), baseline_sha256=hashlib.sha256(
            git('show', f'{HEAD}:utils/ci_test_durations.json')).hexdigest(),
        xml=inputs(), metadata=metadata))
    print(f'Pinned {len(inputs())} XML inputs in {target}')


def measure(manifest):
    """Verify every pinned input before computing or writing any result."""
    pinned = json.loads(manifest.read_text())
    for item in pinned['xml'] + pinned['metadata'] + [dict(
            path=pinned['collection_path'], sha256=pinned['collection_sha256'])]:
        if sha(ROOT.parent / item['path']) != item['sha256']:
            raise ValueError(f'input SHA256 mismatch: {item["path"]}')
    if pinned['head'] != HEAD:
        raise ValueError('unexpected collection head')
    collected = json.loads((ROOT.parent / pinned['collection_path']).read_text())
    if collected['head'] != HEAD or collected['errors'] or collected['exit_code']:
        raise ValueError('collection is not successful at the requested head')
    raw = git('show', f'{HEAD}:utils/ci_test_durations.json')
    if hashlib.sha256(raw).hexdigest() != pinned['baseline_sha256']:
        raise ValueError('baseline timing SHA256 mismatch')
    old = json.loads(raw)
    expected = defaultdict(Counter)
    for node in collected['nodes']:
        expected[node.split('::', 1)[0]][node] += 1
    missing = sorted(expected.keys() - old['file_seconds'].keys())
    added = git('diff', '--name-only', '--diff-filter=A', 'ddfd45c3b', HEAD, '--', 'tests').decode().splitlines()
    if len(missing) != 28 or set(missing) != set(added) & expected.keys():
        raise ValueError(f'unexpected missing/added file inventory: {missing}')
    g1_files = set(git('ls-tree', '-r', '--name-only', G1, '--', 'tests').decode().splitlines())
    modules = {p[:-3].replace('/', '.'): p for p in expected}
    records = defaultdict(lambda: defaultdict(list))
    seen_paths, seen_hashes = set(), set()
    for item in pinned['xml']:
        path = ROOT.parent / item['path']
        if path.resolve() in seen_paths or item['sha256'] in seen_hashes:
            raise ValueError('repeated/copied XML input')
        seen_paths.add(path.resolve())
        seen_hashes.add(item['sha256'])
        for index, case in enumerate(ET.parse(path).iter('testcase')):
            classname, name = case.attrib['classname'], case.attrib['name']
            candidates = [m for m in modules if classname == m or classname.startswith(m + '.')]
            if not candidates:
                raise ValueError(f'unmapped JUnit case: {classname}::{name}')
            module = max(candidates, key=len)
            file = modules[module]
            suffix = classname[len(module):].lstrip('.').replace('.', '::')
            node = file + '::' + (suffix + '::' if suffix else '') + name
            duration = Decimal(case.attrib['time'])
            if not duration.is_finite() or duration < 0:
                raise ValueError(f'invalid duration: {node}')
            outcome = next((kind for kind in ('failure', 'error', 'skipped') if case.find(kind) is not None), 'passed')
            records[item['source']][file].append(dict(nodeid=node, seconds=float(duration),
                seconds_decimal=str(duration), outcome=outcome, artifact=item['path'], index=index))
    # Within-artifact parameter-label collisions retain all occurrences. Across
    # artifacts the same node must not be accepted twice in one source.
    for files in records.values():
        for rows in files.values():
            owners = defaultdict(set)
            for row in rows:
                owners[row['nodeid']].add(row['artifact'])
            if any(len(paths) != 1 for paths in owners.values()):
                raise ValueError('duplicate case across artifacts')
    audit = []
    selected = []
    for file in missing:
        coverage = {}
        source = None
        for candidate in ('bc1g2', 'g1', 'local-with'):
            rows = records[candidate][file]
            actual = Counter(row['nodeid'] for row in rows)
            complete = actual == expected[file]
            eligible = candidate != 'g1' or file in g1_files
            coverage[candidate] = dict(records=len(rows), complete=complete,
                eligible=eligible, missing=sum((expected[file] - actual).values()),
                extra=sum((actual - expected[file]).values()))
            if source is None and complete and eligible:
                source = candidate
        if source is None:
            raise ValueError(f'no complete source for {file}: {coverage}')
        rows = records[source][file]
        seconds = float(max(sum((Decimal(r['seconds_decimal']) for r in rows), Decimal(0)), Decimal('0.001')))
        selected.extend(dict(row, file=file, source=source) for row in rows)
        audit.append(dict(file=file, collected_cases=sum(expected[file].values()),
            seconds=seconds, source=source, artifacts=sorted({r['artifact'] for r in rows}),
            outcomes=dict(Counter(r['outcome'] for r in rows)), coverage=coverage))
    supplement = dict(date='2026-11-03', head=HEAD,
        manifest='notes/ci_timing_refresh_2026-11-03/input-manifest.json',
        manifest_sha256=sha(manifest), sources={
            'bc1g2': dict(run_id=41707437114, commit=HEAD, shards=[2, 3, 4, 6]),
            'g1': dict(run_id=41700664435, commit=G1, shards=list(range(1, 7))),
            'local-with': dict(round=2, mode='with', python='3.13', workers=2, platform='macOS')},
        files={row['file']: {k: row[k] for k in ('source', 'collected_cases', 'seconds', 'artifacts', 'outcomes')}
               for row in audit})
    new = json.loads(raw)
    new['source']['bc1_g2_additions_20261103'] = supplement
    new['method'] += (' BC1/G2 additions (2026-11-03) only fill previously unweighted files: '
        'sum one complete source per current collected file, preferring run 41707437114, '
        'then run 41700664435 for G1 files, then round-2 local with-mode JUnit '
        '(macOS Python 3.13, two workers). Exact case-occurrence multisets and pinned XML '
        'SHA256 values are checked; 0.001-second floor, no local-time scaling. '
        'Completed failures/skips remain timing observations, not evidence of CI success. '
        'Original provenance and every existing weight are retained.')
    new['file_seconds'].update({row['file']: row['seconds'] for row in audit})
    new['file_seconds'] = dict(sorted(new['file_seconds'].items()))
    if any(new['file_seconds'][p] != v for p, v in old['file_seconds'].items()):
        raise ValueError('existing weight changed')
    comparisons = []
    for file in sorted(expected):
        local = records['local-with'][file]
        ci = records['bc1g2'][file]
        if local and ci and Counter(r['nodeid'] for r in local) == Counter(r['nodeid'] for r in ci) == expected[file]:
            local_sum = sum(Decimal(r['seconds_decimal']) for r in local)
            ci_sum = sum(Decimal(r['seconds_decimal']) for r in ci)
            comparisons.append(dict(file=file, local_seconds=float(local_sum),
                ci_seconds=float(ci_sum), ci_over_local=float(ci_sum / local_sum) if local_sum else None))
    result = dict(head=HEAD, full_cases=len(collected['nodes']), collected_files=len(expected),
        old_weights=len(old['file_seconds']), missing_files=audit, comparisons=comparisons,
        slowest_cases=sorted(selected, key=lambda r: -r['seconds'])[:30],
        registration_cases=[r for r in selected if r['file'] == 'tests/test_bc1_registration.py'],
        added_seconds=sum(row['seconds'] for row in audit))
    return new, result, collected['nodes'], records


def refresh(manifest, apply):
    new, result, nodes, records = measure(manifest)
    sys.path.insert(0, str(ROOT))
    from utils.pytest_shard import balanced_files, partition_lanes
    ordinary = partition_lanes(nodes)['ordinary']
    counts = Counter(node.split('::', 1)[0] for node in ordinary)
    calibration = []
    jobs = json.loads((SCRATCH / 'run-41707437114/jobs.json').read_text())
    if isinstance(jobs, dict):
        jobs = jobs['jobs']
    for item in json.loads(manifest.read_text())['xml']:
        if item['source'] != 'bc1g2':
            continue
        path = ROOT.parent / item['path']
        shard = int(path.parent.name.rsplit('shard', 1)[1])
        cases = list(ET.parse(path).iter('testcase'))
        work = sum(Decimal(case.attrib['time']) for case in cases)
        matches = [j for j in jobs if j['name'] == f'Python 3.12 / shard {shard}']
        if len(matches) != 1:
            raise ValueError(f'cannot identify CI job for shard {shard}')
        job = matches[0]
        wall = (datetime.fromisoformat(job['completedAt'].replace('Z', '+00:00')) -
                datetime.fromisoformat(job['startedAt'].replace('Z', '+00:00'))).total_seconds()
        calibration.append(dict(shard=shard, case_seconds=float(work),
            ideal_four_worker_seconds=float(work / 4),
            junit_wall_seconds=float(ET.parse(path).find('.//testsuite').attrib['time']),
            job_wall_seconds=wall, job_minus_ideal_seconds=wall - float(work / 4),
            matching_jobs=[dict(name=j['name'], started_at=j['startedAt'], completed_at=j['completedAt']) for j in matches]))
    allowance = max(0, *(r['job_minus_ideal_seconds'] for r in calibration))
    plans = []
    for total in (6, 4):
        assignments = balanced_files(counts, total, new['file_seconds'])
        rows = []
        for index in range(1, total + 1):
            files = sorted(p for p in counts if assignments[p] == index)
            seconds = sum(Decimal(str(new['file_seconds'][p])) for p in files)
            ideal = float(seconds / 4)
            threshold = 2160 if total == 6 else 2880
            rows.append(dict(shard=index, files=len(files), cases=sum(counts[p] for p in files),
                case_seconds=float(seconds), ideal_four_worker_seconds=ideal,
                eighty_percent_seconds=threshold, ideal_margin_seconds=threshold - ideal,
                projected_job_seconds=ideal + allowance,
                projected_margin_seconds=threshold - ideal - allowance))
        plans.append(dict(shards=total, rows=rows, assignments=assignments,
            registration_shard=assignments['tests/test_bc1_registration.py']))
    result.update(ordinary_cases=len(ordinary), plans=plans, calibration=calibration,
        allowance_seconds=allowance,
        projection_method='File-weight sum / 4 + maximum positive (job wall time - JUnit case sum / 4) '
        'from completed BC1/G2 CI shards 2,3,4,6. Four CI workers, empirical job/setup/scheduling '
        'allowance; not a guarantee of worker utilization, future queue behavior or Linux runtime '
        'of locally measured files. Local weights are unscaled.')
    save(SCRATCH / 'proposed-timings.json', new)
    save(SCRATCH / 'measurement.json', result)
    if apply:
        original = git('show', f'{HEAD}:utils/ci_test_durations.json')
        if TIMING.read_bytes() not in (original, (SCRATCH / 'proposed-timings.json').read_bytes()):
            raise ValueError('refuse to overwrite an unrelated timing edit')
        save(TIMING, new)
    for row in result['missing_files']:
        print(f"{row['file']}\t{row['collected_cases']}\t{row['seconds']:.3f}\t{row['source']}")
    print('Added seconds:', result['added_seconds'])
    print('Source counts:', dict(Counter(row['source'] for row in result['missing_files'])))
    print('Plans:', json.dumps([{k: v for k, v in p.items() if k != 'assignments'} for p in plans]))
    print('Calibration:', json.dumps(calibration))
    print('Slowest:', json.dumps(result['slowest_cases'][:8]))
    print('Comparisons:', json.dumps(sorted(result['comparisons'], key=lambda r: -r['ci_seconds'])[:12]))


def verify(manifest):
    new, result, nodes, _ = measure(manifest)
    raw = TIMING.read_bytes()
    if json.loads(raw) != new:
        raise ValueError('committed candidate differs from reproduced weights')
    old = json.loads(git('show', f'{HEAD}:utils/ci_test_durations.json'))
    original_source = dict(new['source'])
    original_source.pop('bc1_g2_additions_20261103')
    assert original_source == old['source']
    assert new['method'].startswith(old['method'])
    assert len(new['file_seconds']) - len(old['file_seconds']) == 28
    assert all(new['file_seconds'][p] == v for p, v in old['file_seconds'].items())
    sys.path.insert(0, str(ROOT))
    from utils.pytest_shard import balanced_files, partition_lanes, read_weights
    weights = read_weights(TIMING)
    lanes = partition_lanes(nodes)
    ordinary = lanes.pop('ordinary')
    layouts = []
    for total in (6, 4):
        assigned = balanced_files((n.split('::', 1)[0] for n in ordinary), total, weights)
        union = Counter()
        for shard in range(1, total + 1):
            union.update(n for n in ordinary if assigned[n.split('::', 1)[0]] == shard)
        assert union == Counter(ordinary)
        for dedicated in lanes.values():
            union.update(dedicated)
        assert union == Counter(nodes)
        layouts.append(dict(shards=total, full_occurrences=sum(union.values()),
                            missing=0, extra=0))
    # Mutate a scratch COPY, keep the pinned expected hash, and prove refusal
    # before any write to the candidate timing file.
    bad = json.loads(manifest.read_text())
    copied = SCRATCH / 'deliberately-altered-input.xml'
    copied.write_bytes((ROOT.parent / bad['xml'][0]['path']).read_bytes() + b'\n')
    bad['xml'][0]['path'] = str(copied.relative_to(ROOT.parent))
    bad_manifest = SCRATCH / 'deliberately-altered-manifest.json'
    save(bad_manifest, bad)
    try:
        measure(bad_manifest)
    except ValueError as exc:
        assert 'input SHA256 mismatch:' in str(exc)
        refusal = str(exc)
    else:
        raise AssertionError('modified XML was accepted')
    assert TIMING.read_bytes() == raw
    base = SCRATCH / 'canary'
    assert json.loads((base / 'execution.json').read_text())['exit_code'] == 0
    assert len(list(ET.parse(base / 'junit.xml').iter('testcase'))) == 1
    all_xml = list(base.glob('temporary/pytest/*/all.xml'))
    # pytest retains a convenience symlink to the latest fixture directory.
    all_xml = sorted({p.resolve() for p in all_xml})
    assert len(all_xml) == 1
    directory = all_xml[0].parent
    identity = lambda p: Counter((c.attrib['classname'], c.attrib['name'])
                                 for c in ET.parse(p).iter('testcase'))
    whole, union = identity(all_xml[0]), Counter()
    artifacts = [all_xml[0]]
    for shard in range(1, 5):
        path = directory / f'shard-{shard}.xml'
        assert path.stat().st_size > 0
        union.update(identity(path))
        artifacts.append(path)
    assert whole == union and sum(whole.values()) == 64
    checked = dict(timing_sha256=sha(TIMING), original_weights_unchanged=607,
        additions=28, original_source_unchanged=True, original_method_preserved=True,
        exact_reproduction=True, altered_xml_refusal=refusal,
        timing_unchanged_after_refusal=True, layouts=layouts,
        canary=dict(cases=1, nested_occurrences=64, nested_shards=4,
            worker_limit=2, artifacts=[dict(path=str(p.relative_to(SCRATCH)), sha256=sha(p)) for p in artifacts]))
    focused = SCRATCH / 'focused'
    if (focused / 'execution.json').exists():
        execution = json.loads((focused / 'execution.json').read_text())
        assert execution['exit_code'] == 0
        environment = json.loads((focused / 'environment.json').read_text())
        assert environment['timings_sha256'] == sha(TIMING)
        rows = list(ET.parse(focused / 'junit.xml').iter('testcase'))
        assert rows and not any(c.find(kind) is not None for c in rows
                                for kind in ('failure', 'error', 'skipped'))
        checked['focused'] = dict(passed=len(rows), failed=0, errors=0, skipped=0,
            deadline_seconds=execution['deadline_seconds'], wall_seconds=execution['wall_seconds'],
            junit_sha256=sha(focused / 'junit.xml'),
            modules=dict(Counter(c.attrib['classname'] for c in rows)))
    save(SCRATCH / 'verification.json', checked)
    print(json.dumps(checked, indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=('run', 'worker', 'pin', 'refresh', 'verify'))
    parser.add_argument('--label')
    parser.add_argument('--manifest', type=Path, default=NOTE / 'input-manifest.json')
    parser.add_argument('--apply', action='store_true')
    options, args = parser.parse_known_args()
    if args[:1] == ['--']:
        args = args[1:]
    if options.mode == 'pin':
        pin_inputs()
        return
    if options.mode == 'refresh':
        refresh(options.manifest, options.apply)
        return
    if options.mode == 'verify':
        verify(options.manifest)
        return
    if not options.label or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in options.label):
        parser.error('label must contain only lowercase letters, digits and hyphens')
    raise SystemExit(run(options.label, args) if options.mode == 'run' else worker(options.label, args))


if __name__ == '__main__':
    main()
