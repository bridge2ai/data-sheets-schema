#!/usr/bin/env python3
"""#5485, 2026-11-04: refresh every collected file from complete BC1+G2 CI.

Inputs: exact current collection, baseline weights at decf0cab1, SHA256-pinned
saved JUnit and job metadata. Outputs: appended provenance, weights, coverage,
six/four-shard estimates and report tables. G1 is comparison evidence only.
Never combine shards or runs to complete a file. No network or provider calls.
"""
import argparse
from collections import Counter, defaultdict
from datetime import datetime
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
SCRATCH = ROOT.parent / 'scratch-bc1g2-timing'
NOTE = ROOT / 'notes/ci_timing_refresh_2026-11-04'
BASE = 'decf0cab1376d608d2ce411d2d6d8ce3e2ac42ce'
RUNS = {'41735860489': (BASE, [1, 3, 4, 5, 6]),
        '41707437114': ('0ff5c9ba7665eb51b69e597c391cb1ae6a07c44c', [2, 3, 4, 6]),
        '41700664435': ('bc8f981f758c46d5bb027c61294d8a67bf70ed30', [1, 2, 3, 4, 5, 6])}
ORDER = ('41735860489', '41707437114')
TIMING = ROOT / 'utils/ci_test_durations.json'
MANIFEST = NOTE / 'input-manifest.json'
COLLECTION = SCRATCH / 'r3-collection/collection.json'


def git(*args):
    return subprocess.check_output(['git', '--no-replace-objects', *args], cwd=ROOT)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + '\n')
    assert json.loads(path.read_text()) == value


def record(path, **extra):
    return dict(path=str(path.relative_to(ROOT.parent)), sha256=sha(path), **extra)


def pin():
    if MANIFEST.exists():
        raise ValueError('retain the pinned manifest')
    xml, metadata = [], []
    for run, (commit, shards) in RUNS.items():
        directory = SCRATCH / f'run-{run}'
        data = json.loads((directory / 'run_metadata.json').read_text())
        assert str(data['id']) == run and data['head_sha'] == commit
        paths = sorted(directory.glob('tests-py3.12-shard*/pytest.xml'))
        assert sorted(int(p.parent.name.rsplit('shard', 1)[1]) for p in paths) == shards
        xml.extend(record(p, run=run, shard=int(p.parent.name.rsplit('shard', 1)[1])) for p in paths)
        metadata.extend(record(directory / name, run=run) for name in
                        ('run_metadata.json', 'artifacts_roster.json', 'jobs.json'))
    save(MANIFEST, dict(baseline=BASE, baseline_weights_sha256=hashlib.sha256(
        git('show', f'{BASE}:utils/ci_test_durations.json')).hexdigest(),
        collection=record(COLLECTION), xml=xml, metadata=metadata))
    print(f'Pinned {len(xml)} XML files and {len(metadata)} metadata files.')


def build(manifest=MANIFEST):
    pinned = json.loads(manifest.read_text())
    for item in [pinned['collection'], *pinned['xml'], *pinned['metadata']]:
        if sha(ROOT.parent / item['path']) != item['sha256']:
            raise ValueError(f'input SHA256 mismatch: {item["path"]}')
    raw = git('show', f'{BASE}:utils/ci_test_durations.json')
    assert pinned['baseline'] == BASE
    assert hashlib.sha256(raw).hexdigest() == pinned['baseline_weights_sha256']
    collected = json.loads((ROOT.parent / pinned['collection']['path']).read_text())
    assert not collected['errors'] and collected['exit_code'] == 0
    # Collection is at the fixture-fix descendant, with no runtime changes.
    assert subprocess.run(['git', 'merge-base', '--is-ancestor', BASE, collected['head']], cwd=ROOT).returncode == 0
    assert not git('diff', '--name-only', BASE, collected['head'], '--', 'src', 'utils', '.github')
    expected = defaultdict(Counter)
    for node in collected['nodes']:
        expected[node.split('::', 1)[0]][node] += 1
    modules = {p[:-3].replace('/', '.'): p for p in expected}
    records = defaultdict(lambda: defaultdict(dict))
    xmls, seen = {}, set()
    for item in pinned['xml']:
        path = ROOT.parent / item['path']
        identity = (item['run'], item['shard'])
        assert identity not in seen
        seen.add(identity)
        root = ET.parse(path)
        xmls[identity] = root
        files = defaultdict(list)
        for case in root.iter('testcase'):
            classname = case.attrib['classname']
            candidates = [m for m in modules if classname == m or classname.startswith(m + '.')]
            if not candidates:
                raise ValueError(f'unmapped case: {classname}::{case.attrib["name"]}')
            module = max(candidates, key=len)
            file = modules[module]
            suffix = classname[len(module):].lstrip('.').replace('.', '::')
            node = file + '::' + (suffix + '::' if suffix else '') + case.attrib['name']
            seconds = Decimal(case.attrib['time'])
            assert seconds.is_finite() and seconds >= 0
            outcome = next((k for k in ('failure', 'error', 'skipped') if case.find(k) is not None), 'passed')
            files[file].append(dict(nodeid=node, seconds=str(seconds), outcome=outcome))
        records[item['run']][item['shard']] = files
    new = json.loads(raw)
    old = new['file_seconds'].copy()
    audit, selected_cases = [], []
    for file, counts in sorted(expected.items()):
        if file not in old:
            raise ValueError(f'collected file has no baseline weight: {file}')
        coverage, choice = {}, None
        for run in ORDER:
            matches, per_shard = [], []
            for shard, files in records[run].items():
                rows = files.get(file, [])
                if not rows:
                    continue
                actual = Counter(row['nodeid'] for row in rows)
                complete = actual == counts
                per_shard.append(dict(shard=shard, records=len(rows), complete=complete,
                    missing=sum((counts - actual).values()), extra=sum((actual - counts).values())))
                if complete:
                    matches.append((shard, rows))
            if len(matches) > 1:
                raise ValueError(f'duplicate complete measurements: {run}/{file}')
            coverage[run] = per_shard
            if choice is None and matches:
                choice = (run, *matches[0])
        if choice:
            run, shard, rows = choice
            seconds = max(sum((Decimal(r['seconds']) for r in rows), Decimal(0)), Decimal('0.001'))
            selected_cases.extend(dict(r, file=file, run=run, shard=shard) for r in rows)
            source = dict(source=run, shard=shard, value_kind='measured',
                outcomes=dict(Counter(r['outcome'] for r in rows)))
        else:
            seconds = Decimal(str(old[file]))
            source = dict(source='retained-current', value_kind='retained; see earlier provenance')
        new['file_seconds'][file] = float(seconds)
        audit.append(dict(file=file, collected_cases=sum(counts.values()),
            old_seconds=old[file], seconds=float(seconds),
            delta_seconds=float(seconds - Decimal(str(old[file]))), coverage=coverage, **source))
    new['source']['bc1_g2_all_files_20261104'] = dict(baseline=BASE,
        baseline_weights_sha256=pinned['baseline_weights_sha256'],
        collection_head=collected['head'], collection_sha256=pinned['collection']['sha256'],
        manifest=str(MANIFEST.relative_to(ROOT)), manifest_sha256=sha(manifest),
        priority=[*ORDER, 'retained-current'],
        method='Exact collected-case occurrence multiset in one shard XML; sum all outcomes, '
               'floor 0.001 s. No cross-shard or cross-run completion. Retain current otherwise. '
               'G1 XML is comparison-only. A failure duration is a measurement, not a passing run.',
        files={r['file']: {k: v for k, v in r.items() if k not in ('file', 'coverage', 'delta_seconds')}
               for r in audit})
    new['method'] += (' All-file BC1/G2 refresh (2026-11-04): use run 41735860489, then '
        '41707437114, then retain current weight, requiring an exact current case-occurrence '
        'multiset within one shard XML per file. Preserve all earlier provenance. Completed '
        'failures/skips are timing observations. Inputs are SHA256-pinned in the new source block.')
    assert set(new['file_seconds']) == set(old)
    assert all(new['file_seconds'][p] == old[p] for p in old.keys() - expected.keys())
    prior = dict(new['source'])
    prior.pop('bc1_g2_all_files_20261104')
    assert prior == json.loads(raw)['source']
    calibration = []
    for run in ORDER:
        jobs = json.loads((SCRATCH / f'run-{run}/jobs.json').read_text())['jobs']
        for shard in RUNS[run][1]:
            job, = [j for j in jobs if j['name'] == f'Python 3.12 / shard {shard}']
            assert job['status'] == 'completed' and job['conclusion'] in ('success', 'failure')
            wall = Decimal(str((datetime.fromisoformat(job['completedAt'].replace('Z', '+00:00')) -
                               datetime.fromisoformat(job['startedAt'].replace('Z', '+00:00'))).total_seconds()))
            tree = xmls[(run, shard)]
            work = sum((Decimal(c.attrib['time']) for c in tree.iter('testcase')), Decimal(0))
            calibration.append(dict(run=run, shard=shard, conclusion=job['conclusion'],
                case_seconds=float(work), job_wall_seconds=float(wall),
                residual_seconds=float(wall - work / 4)))
    allowance = max(Decimal(0), *(Decimal(str(r['residual_seconds'])) for r in calibration))
    sys.path.insert(0, str(ROOT))
    from utils.pytest_shard import balanced_files, partition_lanes
    lanes = partition_lanes(collected['nodes'])
    ordinary = lanes.pop('ordinary')
    counts = Counter(n.split('::', 1)[0] for n in ordinary)
    plans = []
    for total in (6, 4):
        assigned = balanced_files(counts, total, new['file_seconds'])
        rows, union = [], Counter()
        for shard in range(1, total + 1):
            paths = sorted(p for p in counts if assigned[p] == shard)
            selected = [n for n in ordinary if assigned[n.split('::', 1)[0]] == shard]
            union.update(selected)
            seconds = sum((Decimal(str(new['file_seconds'][p])) for p in paths), Decimal(0))
            projected = seconds / 4 + allowance
            threshold = Decimal(2160 if total == 6 else 2880)
            rows.append(dict(shard=shard, files=len(paths), cases=len(selected),
                case_seconds=float(seconds), ideal_four_worker_seconds=float(seconds / 4),
                projected_job_seconds=float(projected), eighty_percent_seconds=float(threshold),
                margin_seconds=float(threshold - projected),
                largest_files=sorted(paths, key=lambda p: -new['file_seconds'][p])[:5]))
        assert union == Counter(ordinary)
        for dedicated in lanes.values():
            union.update(dedicated)
        assert union == Counter(collected['nodes'])
        plans.append(dict(shards=total, rows=rows, assignments=assigned,
            full_collection_preserved=sum(union.values())))
    admission = []
    for run in RUNS:
        for shard, files in records[run].items():
            rows = files.get('tests/test_report_admission.py', [])
            if rows:
                admission.append(dict(run=run, shard=shard, cases=len(rows),
                    complete=Counter(r['nodeid'] for r in rows) == expected['tests/test_report_admission.py'],
                    seconds=float(sum(Decimal(r['seconds']) for r in rows)),
                    slowest=sorted(rows, key=lambda r: -Decimal(r['seconds']))[:3]))
    result = dict(baseline=BASE, collection_head=collected['head'],
        collected_cases=len(collected['nodes']), collected_files=len(expected), ordinary_cases=len(ordinary),
        source_counts=dict(Counter(r['source'] for r in audit)),
        changed_files=sum(r['seconds'] != r['old_seconds'] for r in audit), files=audit,
        largest_changes=sorted(audit, key=lambda r: -abs(r['delta_seconds']))[:15],
        allowance_seconds=float(allowance), calibration=calibration, plans=plans,
        slowest_cases=sorted(selected_cases, key=lambda r: -Decimal(r['seconds']))[:15],
        admission_ci=admission)
    return new, result, raw


def tables(result):
    lines = ['| Source | Files |', '| --- | ---: |']
    lines.extend(f'| {source} | {count} |' for source, count in result['source_counts'].items())
    lines += ['', '| File (`tests/`) | Previous s | New s | Change s | Source |',
              '| --- | ---: | ---: | ---: | --- |']
    for row in result['largest_changes']:
        lines.append(f"| {row['file'].removeprefix('tests/')} | {row['old_seconds']:.3f} | "
                     f"{row['seconds']:.3f} | {row['delta_seconds']:+.3f} | {row['source']} |")
    lines += ['', '| Run | Shard | Case s | Job wall s | Residual s |',
              '| --- | ---: | ---: | ---: | ---: |']
    for row in result['calibration']:
        lines.append(f"| {row['run']} | {row['shard']} | {row['case_seconds']:.3f} | "
                     f"{row['job_wall_seconds']:.3f} | {row['residual_seconds']:.3f} |")
    lines += ['', '| Plan | Shard | Files | Cases | Case s | Estimated job s | Margin to 80% s |',
              '| --- | ---: | ---: | ---: | ---: | ---: | ---: |']
    for plan in result['plans']:
        for row in plan['rows']:
            lines.append(f"| {'PR' if plan['shards'] == 6 else 'Main'} | {row['shard']} | "
                f"{row['files']} | {row['cases']} | {row['case_seconds']:.3f} | "
                f"{row['projected_job_seconds']:.3f} | {row['margin_seconds']:+.3f} |")
    lines += ['', '| Largest file (`tests/`) | Weight s | Source | PR shard | Main shard |',
              '| --- | ---: | --- | ---: | ---: |']
    for row in sorted(result['files'], key=lambda r: -r['seconds'])[:15]:
        file = row['file']
        lines.append(f"| {file.removeprefix('tests/')} | {row['seconds']:.3f} | {row['source']} | "
                     f"{result['plans'][0]['assignments'][file]} | {result['plans'][1]['assignments'][file]} |")
    lines += ['', '| Retained file (`tests/`): neither BC1+G2 run complete | Weight s | PR shard | Main shard |',
              '| --- | ---: | ---: | ---: |']
    for row in sorted(result['files'], key=lambda r: -r['seconds']):
        if row['source'] != 'retained-current':
            continue
        file = row['file']
        lines.append(f"| {file.removeprefix('tests/')} | {row['seconds']:.3f} | "
                     f"{result['plans'][0]['assignments'][file]} | {result['plans'][1]['assignments'][file]} |")
    lines += ['', '| Three slowest selected cases | Measured s | PR shard | Main shard |',
              '| --- | ---: | ---: | ---: |']
    for row in result['slowest_cases'][:3]:
        lines.append(f"| `{row['nodeid']}` | {Decimal(row['seconds']):.3f} | "
                     f"{result['plans'][0]['assignments'][row['file']]} | "
                     f"{result['plans'][1]['assignments'][row['file']]} |")
    return '\n'.join(lines) + '\n'


def refresh(apply):
    new, result, raw = build()
    encoded = (json.dumps(new, indent=2) + '\n').encode()
    if apply:
        assert TIMING.read_bytes() in (raw, encoded), 'unrelated timing edit'
        save(TIMING, new)
    result['weights_sha256'] = hashlib.sha256(encoded).hexdigest()
    save(SCRATCH / 'r3-timings/proposed.json', new)
    save(NOTE / 'measurement.json', result)
    (NOTE / 'tables.md').write_text(tables(result))
    assert (NOTE / 'tables.md').read_text() == tables(result)
    print(tables(result))
    print('Weights SHA256:', result['weights_sha256'])


def verify():
    new, result, _ = build()
    assert json.loads(TIMING.read_text()) == new
    before = sha(TIMING)
    bad = json.loads(MANIFEST.read_text())
    bad['xml'][0]['sha256'] = '0' * 64
    bad_path = SCRATCH / 'r3-timings/hash-mismatch-manifest.json'
    save(bad_path, bad)
    try:
        build(bad_path)
    except ValueError as exc:
        assert str(exc).startswith('input SHA256 mismatch:')
    else:
        raise AssertionError('altered input hash accepted')
    assert sha(TIMING) == before
    save(NOTE / 'verification.json', dict(weights_sha256=before,
        exact_reproduction=True, prior_provenance_preserved=True,
        hash_mismatch_refused_before_write=True,
        layouts=[dict(shards=p['shards'], cases=p['full_collection_preserved'], missing=0, extra=0)
                 for p in result['plans']]))
    print('Exact reproduction, provenance, collection unions and hash refusal passed.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=('pin', 'refresh', 'verify'))
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    if args.mode == 'pin':
        pin()
    elif args.mode == 'refresh':
        refresh(args.apply)
    else:
        verify()
