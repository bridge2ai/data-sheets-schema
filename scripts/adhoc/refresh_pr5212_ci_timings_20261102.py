#!/usr/bin/env python3
"""#5212 round 8, 2026-11-02: audit/refresh measured file scheduling weights.

Inputs: pinned collection, old weights, CI shard XML/log and local missing-shard
XML. Outputs: normalized timing observations, complete provenance, file/node
diagnosis and both plugin partitions. --write installs the measured snapshot.
No network, test execution, lane changes or test-specific weights.
"""
import argparse
from collections import Counter, defaultdict, deque
import csv
from datetime import datetime
from decimal import Decimal
import hashlib
import heapq
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
# Match the prior refresh's no-site bootstrap without importing an editable
# checkout from .pth files. Only pytest is needed by the partition module.
prefix = Path(sys.executable).parent.parent
sys.path[:0] = [str(ROOT), str(prefix / 'lib' /
    f'python{sys.version_info.major}.{sys.version_info.minor}' / 'site-packages')]
from utils.pytest_shard import _estimates, balanced_files, partition_lanes, read_weights
from utils.update_ci_shard_timings import build


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path, value):
    path.write_text(json.dumps(value, indent=2) + '\n')
    assert path.stat().st_size


def modules(tree):
    return {p[:-3].replace('/', '.'): p for p in subprocess.check_output(
        ['git', 'ls-files', 'tests'], cwd=tree, text=True).splitlines() if p.endswith('.py')}


def xml_rows(path, mapping, origin):
    root = ET.parse(path).getroot()
    rows = []
    for case in root.iter('testcase'):
        classname, name = case.attrib['classname'], case.attrib['name']
        module = max((m for m in mapping if classname == m or classname.startswith(m + '.')), key=len)
        suffix = classname[len(module):].lstrip('.').replace('.', '::')
        node = mapping[module] + '::' + (suffix + '::' if suffix else '') + name
        duration = Decimal(case.attrib['time'])
        assert duration.is_finite() and duration >= 0
        outcome = next((k for k in ('failure', 'error', 'skipped') if case.find(k) is not None), 'passed')
        rows.append(dict(nodeid=node, file=mapping[module], classname=classname, name=name,
            seconds=float(duration), outcome=outcome, origin=origin))
    suites = list(root.iter('testsuite'))
    assert len(suites) == 1
    return rows, float(suites[0].attrib['time'])


def log_rows(path):
    completed, starts = [], defaultdict(list)
    previous, first, session, cancelled = {}, None, None, None
    for line in path.read_text().splitlines():
        match = re.search(r'(\d{4}-\d\d-\d\dT[0-9:.]+Z) (.*)', line)
        assert match, line
        stamp = datetime.fromisoformat(match[1].replace('Z', '+00:00'))
        first = first or stamp
        text = match[2].rstrip()
        if 'test session starts' in text:
            assert session is None
            session = stamp
        if 'The operation was canceled.' in text:
            cancelled = stamp
        if text.startswith('tests/'):
            starts[text].append(stamp.isoformat())
        result = re.fullmatch(r'\[(gw\d+)\] \[\s*\d+%\] (PASSED|SKIPPED|FAILED|ERROR|XFAIL|XPASS) (tests/.*)', text)
        if not result:
            continue
        worker, outcome, node = result.groups()
        assert session and outcome in ('PASSED', 'SKIPPED'), (worker, outcome, node)
        begin = previous.get(worker, session)
        assert stamp >= begin
        completed.append(dict(nodeid=node, seconds=(stamp - begin).total_seconds(),
            outcome='passed' if outcome == 'PASSED' else 'skipped',
            origin='ci_worker_completion_interval', worker=worker,
            interval_start=begin.isoformat(), interval_end=stamp.isoformat(),
            printed_start=starts.get(node, [])))
        previous[worker] = stamp
    assert session and cancelled and len(previous) == 4
    return completed, starts, dict(job_start=first.isoformat(), session_start=session.isoformat(),
        cancellation=cancelled.isoformat(), job_wall_seconds=(cancelled-first).total_seconds(),
        pytest_wall_lower_bound_seconds=(cancelled-session).total_seconds(),
        startup_seconds=(session-first).total_seconds(),
        last_worker_result={w: t.isoformat() for w, t in sorted(previous.items())})


def scenario(nodes, weights, measured, total, rows):
    paths = {n.split('::', 1)[0] for n in nodes}
    assignment = balanced_files(paths, total, weights)
    own, fresh = _estimates(paths, weights), _estimates(paths, measured)
    case_times = defaultdict(deque)
    for row in rows:
        case_times[row['nodeid']].append(row['seconds'])
    output = []
    for index in range(1, total + 1):
        selected = [n for n in nodes if assignment[n.split('::', 1)[0]] == index]
        counts = Counter(n.split('::', 1)[0] for n in selected)
        # The plugin recomputes the fallback from this shard's collected files
        # when ordering its cases, after using the full set for assignment.
        priority = _estimates(counts, weights)
        selected.sort(key=lambda n: -priority[n.split('::', 1)[0]] / counts[n.split('::', 1)[0]])
        work = sum(fresh[p] for p in sorted(counts))
        workers = [(0.0, i) for i in range(4)]
        heapq.heapify(workers)
        for node in selected:
            end, worker = heapq.heappop(workers)
            heapq.heappush(workers, (end + case_times[node].popleft(), worker))
        output.append(dict(shard=index, cases=len(selected), files=len(counts),
            own_weight_case_seconds=round(sum(own[p] for p in sorted(counts)), 3),
            own_weight_ideal_four_worker_minutes=round(sum(own[p] for p in counts) / 240, 3),
            refreshed_case_seconds=round(work, 3),
            ideal_four_worker_minutes=round(work / 240, 3),
            simulated_four_worker_minutes=round(max(t for t, _ in workers) / 60, 3)))
    assert not any(case_times.values())
    return dict(shard_count=total, shards=output, assignment=assignment,
        simulation='Four workers, one next case to earliest free worker, plugin file priority and stable case order. '
                   'A scheduling model, not a wall-time guarantee or exact emulation of xdist queues.')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--tree', type=Path, default=ROOT)
    p.add_argument('--collection', type=Path, required=True)
    p.add_argument('--old-weights', type=Path, required=True)
    p.add_argument('--ci-artifacts', type=Path, required=True)
    p.add_argument('--ci-log', type=Path, required=True)
    p.add_argument('--local-xml', type=Path, required=True)
    p.add_argument('--missing-shard', type=int, required=True)
    p.add_argument('--shards', type=int, default=6)
    p.add_argument('--run-id', type=int, required=True)
    p.add_argument('--commit', required=True)
    p.add_argument('--output-dir', type=Path, required=True)
    p.add_argument('--write', action='store_true')
    a = p.parse_args()
    assert not a.output_dir.exists(), 'retain prior evidence; use a fresh output directory'
    a.output_dir.mkdir(parents=True)
    collect = json.loads(a.collection.read_text())
    assert collect['exit_code'] == 0 and not collect['collection_errors']
    full = collect['selected']
    lanes = partition_lanes(full)
    nodes = lanes['ordinary']
    paths = {n.split('::', 1)[0] for n in nodes}
    old_doc = json.loads(a.old_weights.read_text())
    old = read_weights(a.old_weights)
    assignment = balanced_files(paths, a.shards, old)
    expected = {i: Counter(n for n in nodes if assignment[n.split('::', 1)[0]] == i)
                for i in range(1, a.shards + 1)}
    mapping = modules(a.tree)
    normalized = a.output_dir / 'normalized'
    normalized.mkdir()
    rows, artifacts, measured_wall = [], [], {}
    for index in range(1, a.shards + 1):
        if index == a.missing_shard:
            continue
        path = a.ci_artifacts / f'tests-py3.12-shard{index}' / 'pytest.xml'
        observed, wall = xml_rows(path, mapping, 'ci_junit')
        assert all(r['outcome'] in ('passed', 'skipped') for r in observed)
        assert Counter(r['nodeid'] for r in observed) == expected[index], index
        target = normalized / f'ci-shard{index}' / 'pytest.xml'
        target.parent.mkdir()
        shutil.copyfile(path, target)
        assert sha(path) == sha(target)
        artifacts.append(dict(shard=index, path=str(path), sha256=sha(path), cases=len(observed),
            junit_wall_seconds=wall, total_case_seconds=sum(r['seconds'] for r in observed)))
        measured_wall[index] = wall
        rows.extend(observed)
    local, local_wall = xml_rows(a.local_xml, mapping, 'local_junit')
    assert Counter(r['nodeid'] for r in local) == expected[a.missing_shard]
    by_node = defaultdict(deque)
    for row in local:
        by_node[row['nodeid']].append(row)
    observed, starts, log_meta = log_rows(a.ci_log)
    done = Counter(r['nodeid'] for r in observed)
    assert not (done - expected[a.missing_shard]), 'CI log has unexpected/repeated completed cases'
    unfinished = expected[a.missing_shard] - done
    derived = ET.Element('testsuite')
    shard_rows, local_substitutions = [], []
    for row in observed:
        source = by_node[row['nodeid']].popleft()
        row.update({k: source[k] for k in ('classname', 'name', 'file')})
        shard_rows.append(row)
    for node, count in unfinished.items():
        for _ in range(count):
            source = by_node[node].popleft()
            assert source['outcome'] == 'passed', 'local fallback must be a completed pass'
            row = {**source, 'printed_start': starts.get(node, [])}
            shard_rows.append(row)
            local_substitutions.append(row)
    assert not any(by_node.values())
    for row in shard_rows:
        case = ET.SubElement(derived, 'testcase', classname=row['classname'], name=row['name'],
            time=str(row['seconds']), timing_origin=row['origin'])
        if row['outcome'] == 'skipped':
            ET.SubElement(case, 'skipped', message='Observed SKIPPED in the supplied CI log')
    target = normalized / f'derived-shard{a.missing_shard}' / 'pytest.xml'
    target.parent.mkdir()
    ET.ElementTree(derived).write(target, encoding='utf-8', xml_declaration=True)
    rows.extend(shard_rows)
    assert Counter(r['nodeid'] for r in rows) == Counter(nodes)
    measured_wall[a.missing_shard] = log_meta['pytest_wall_lower_bound_seconds']
    # Reuse #5415's unchanged updater: finite durations, duplicate ownership,
    # module mapping and Decimal summation all pass through its original build.
    fresh = build(normalized, a.tree, a.run_id, a.commit)
    measured = fresh['file_seconds']
    assert set(measured) == paths
    fresh['file_seconds'] = dict(sorted({**old, **measured}.items()))
    retained = sorted(old.keys() - measured.keys())
    assert all(fresh['file_seconds'][name] == old[name] for name in retained)
    fresh['source']['supplement'] = dict(
        ci_log_sha256=sha(a.ci_log), local_xml_sha256=sha(a.local_xml),
        derived_artifact=str(target.relative_to(normalized)),
        local_case_seconds={r['nodeid']: r['seconds'] for r in local_substitutions},
        prior_snapshot_sha256=sha(a.old_weights), retained_unmeasured_files=retained,
        provenance='Run/commit supplied by the lead; downloaded XML/log hashes verified locally. '
                   'Cancelled shard supplemented, not certified as a successful CI run.')
    fresh['method'] += (' Missing-shard observations use elapsed time between consecutive results on each CI worker '
        '(first result measured from pytest session start; includes setup, prior teardown and scheduling delay). '
        'Unfinished cases use completed local JUnit times listed in source.supplement. '
        'Unmeasured prior entries retain their exact values.')
    write(a.output_dir / 'timings.json', fresh)
    counts = Counter(n.split('::', 1)[0] for n in nodes)
    before = _estimates(paths, old)
    diagnosis = [dict(file=name, collected_cases=counts[name], old_weight=old.get(name),
        old_effective_seconds=before[name], measured_seconds=measured[name],
        ratio=measured[name]/before[name], delta_seconds=measured[name]-before[name],
        old_shard=assignment[name], previously_unweighted=name not in old,
        nodeids=[n for n in nodes if n.split('::', 1)[0] == name]) for name in sorted(paths)]
    result = dict(run_id=a.run_id, commit=a.commit, collection_sha256=sha(a.collection),
        full_cases=len(full), ordinary_cases=len(nodes), ordinary_files=len(paths),
        dedicated_cases=lanes, missing_weight_files=sorted(paths-old.keys()),
        retained_unmeasured_files=retained, observations=artifacts,
        incomplete_shard=dict(index=a.missing_shard, **log_meta,
            completed=Counter(r['outcome'] for r in observed),
            unfinished=list(unfinished.elements()), local_substitutions=local_substitutions,
            log_sha256=sha(a.ci_log), local_xml_sha256=sha(a.local_xml), local_wall_seconds=local_wall,
            derived_xml_sha256=sha(target)),
        input_node_multiset_matches_plugin_partition=True,
        prior_weights_sha256=sha(a.old_weights), refreshed_weights_sha256=sha(a.output_dir/'timings.json'),
        plugin_sha256=sha(ROOT/'utils/pytest_shard.py'), updater_sha256=sha(ROOT/'utils/update_ci_shard_timings.py'),
        cases=rows, files=diagnosis, scenarios=[])
    result['dedicated_cases'].pop('ordinary')
    for total in (6, 4):
        for label, weights in (('before', old), ('after', fresh['file_seconds'])):
            value = scenario(nodes, weights, measured, total, rows)
            value['weights'] = label
            if total == a.shards and label == 'before':
                for row in value['shards']:
                    row['observed_ci_pytest_minutes'] = measured_wall[row['shard']]/60
            result['scenarios'].append(value)
    original = next(s for s in result['scenarios'] if s['shard_count'] == a.shards and s['weights'] == 'before')
    residual = max(0, *(r['observed_ci_pytest_minutes'] - r['simulated_four_worker_minutes']
        for r in original['shards'] if r['shard'] != a.missing_shard))
    allowance = residual + log_meta['startup_seconds'] / 60
    result['wall_projection'] = dict(completed_ci_max_model_residual_minutes=residual,
        observed_job_startup_minutes=log_meta['startup_seconds']/60, allowance_minutes=allowance,
        method='Add the largest positive completed-CI model residual and the observed cancelled-job startup '
               'to the four-worker model. Held constant for before/after; an empirical estimate, not a guarantee.')
    for s in result['scenarios']:
        for row in s['shards']:
            row['projected_job_minutes'] = round(row['simulated_four_worker_minutes'] + allowance, 3)
            row['eighty_percent_limit_minutes'] = 36 if s['shard_count'] == 6 else 48
            row['within_eighty_percent'] = row['projected_job_minutes'] <= row['eighty_percent_limit_minutes']
    for filename, records, fields in (
        ('files.tsv', diagnosis, ['file', 'collected_cases', 'old_weight', 'old_effective_seconds',
                                 'measured_seconds', 'ratio', 'delta_seconds', 'old_shard', 'previously_unweighted']),
        ('cases.tsv', rows, ['nodeid', 'file', 'seconds', 'origin', 'outcome']),
    ):
        with (a.output_dir / filename).open('w', newline='') as stream:
            writer = csv.DictWriter(stream, fields, delimiter='\t', extrasaction='ignore')
            writer.writeheader()
            writer.writerows(records)
    write(a.output_dir / 'evidence.json', result)
    if a.write:
        (a.tree/'utils/ci_test_durations.json').write_bytes((a.output_dir/'timings.json').read_bytes())
    print(json.dumps(dict(full_cases=len(full), ordinary_cases=len(nodes), files=len(paths),
        missing_weights=result['missing_weight_files'], unfinished=result['incomplete_shard']['unfinished'],
        completed=result['incomplete_shard']['completed'], local_substitutions=local_substitutions,
        total_case_seconds=sum(measured.values()), retained_unmeasured_files=retained,
        largest_underweights=[{k: v for k, v in r.items() if k != 'nodeids'}
            for r in sorted(diagnosis, key=lambda r: r['delta_seconds'], reverse=True)[:20]],
        wall_projection=result['wall_projection'],
        scenarios=[{k: v for k, v in row.items() if k != 'assignment'} for row in result['scenarios']]), indent=2))


if __name__ == '__main__':
    main()
