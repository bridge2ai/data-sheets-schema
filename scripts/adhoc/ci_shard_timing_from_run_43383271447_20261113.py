#!/usr/bin/env python3
"""Measure per-file CI time from run 43383271447 and propose shard weights.

Purpose: the first CI run on 12 pull-request shards (D147) on the native
candidate f7f8e8bff cancelled shards 3 and 10 at the 45-minute limit, and
shards 6, 7 and 12 took 31 to 38 minutes. This script measures where the time
went and raises recorded weights in utils/ci_test_durations.json that are too
low, never lowering one, so that the existing balancer
(utils.pytest_shard.balanced_files) spreads the slow files.

Inputs (all saved locally; nothing is fetched here):
  --junit DIR   the run's ordinary-shard JUnit artifacts, DIR/shardN/pytest.xml
                (completed shards; failed cases still carry their time)
  --logs DIR    job logs DIR/shardN.log for the cancelled shards (3, 10), read
                with the method the timing file already names: elapsed time
                between consecutive results on each xdist worker, the first
                from the worker's first output; a test still running at
                cancellation counts from its worker's last result to the
                cancellation line, as a lower bound
  --collection FILE  `pytest --collect-only -q` output at the candidate
  --timings FILE     utils/ci_test_durations.json to read and (with --write)
                     update
Outputs: a JSON report on stdout (measured seconds by file, the weights it
raises, predicted shard sums before and after); with --write, the raised
weights and a labelled source block, source.ci_12_shards_43383271447_20261113.
Serves: owner decision D147 (12 PR shards) and the lead's CI follow-up for
draft PR 5968. Date: 2026-11-13.
"""
import argparse
from collections import Counter, defaultdict
from datetime import datetime
from decimal import Decimal, ROUND_CEILING
import hashlib
import json
from pathlib import Path
import re
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from utils.pytest_shard import balanced_files, partition_lanes  # noqa: E402

RUN_ID = 43383271447
RUN_COMMIT = 'f7f8e8bff6ea14006957d8631f66346d91bcddcd'
KEY = 'ci_12_shards_43383271447_20261113'
STAMP = re.compile(r'(\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d\.\d+)Z (.*)$')
RESULT = re.compile(r'^\[(gw\d+)\] \[\s*\d+%\] (PASSED|FAILED|ERROR|SKIPPED|XFAIL|XPASS) (\S+)')
STARTED = re.compile(r'^(tests/[^\s:]+\.py::.*?)\s*$')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def junit_seconds(directory):
    seconds, sources = defaultdict(Decimal), {}
    for path in sorted(Path(directory).glob('shard*/pytest.xml')):
        sources[path.parent.name] = sha(path)
        for case in ET.fromstring(path.read_bytes()).iter('testcase'):
            name = case.attrib.get('file')
            if not name:
                classname = case.attrib['classname']
                parts = classname.split('.')
                # tests.test_x.Class -> tests/test_x.py; resolve by existence.
                for cut in range(len(parts), 0, -1):
                    candidate = '/'.join(parts[:cut]) + '.py'
                    if (ROOT / candidate).is_file():
                        name = candidate
                        break
            if not name:
                raise ValueError(f'cannot map JUnit case to a file: {case.attrib}')
            seconds[name] += Decimal(case.attrib.get('time', '0'))
    return seconds, sources


def log_seconds(path):
    """Consecutive-result elapsed time per xdist worker, as the timing file's method says."""
    last, seconds, running, cancel = {}, defaultdict(Decimal), {}, None
    first_output, finished_text = None, []
    for line in Path(path).read_text(errors='replace').splitlines():
        match = STAMP.search(line)
        if not match:
            continue
        when = datetime.fromisoformat(match[1][:26])
        text = match[2]
        if first_output is None and text.startswith('['):
            first_output = when
        if 'Terminate orphan process' in text or 'The operation was canceled' in text:
            cancel = cancel or when
        started = STARTED.match(text)
        if started:
            # xdist prints a node id when a worker starts it; keep the first time.
            running.setdefault(started[1], when)
            continue
        result = RESULT.match(text)
        if not result:
            continue
        worker, node = result[1], result[3]
        finished_text.append(text)
        running.pop(node, None)
        start = last.get(worker, first_output or when)
        seconds[node.split('::', 1)[0]] += Decimal(str((when - start).total_seconds()))
        last[worker] = when
    unfinished = {}
    if cancel is not None:
        for node, start in running.items():
            # A result line may spell a parametrised id differently; any
            # result that contains this id means the test did finish.
            if any(node in text for text in finished_text):
                continue
            # A lower bound: still running when the job was cancelled.
            elapsed = Decimal(str((cancel - start).total_seconds()))
            unfinished[node] = float(elapsed)
            seconds[node.split('::', 1)[0]] += elapsed
    return seconds, last, cancel, unfinished


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--junit', required=True)
    ap.add_argument('--logs', required=True)
    ap.add_argument('--collection', required=True)
    ap.add_argument('--timings', required=True)
    ap.add_argument('--target-minutes', type=float, default=35.0)
    ap.add_argument('--extra-file', action='append', default=[],
                    help='a test file CI collects but this checkout cannot (an uninitialised submodule)')
    ap.add_argument('--suspected-hang', action='append', default=[],
                    help='an unfinished node id whose elapsed time is a stall, not a duration; '
                         'it is reported and never becomes a weight')
    ap.add_argument('--write', action='store_true')
    a = ap.parse_args()
    measured, junit_sources = junit_seconds(a.junit)
    source_of = {name: 'junit' for name in measured}
    cancelled = {}
    for log in sorted(Path(a.logs).glob('shard*.log')):
        seconds, last, cancel, unfinished = log_seconds(log)
        hung = {node: unfinished.pop(node) for node in list(unfinished) if node in a.suspected_hang}
        for node, elapsed in hung.items():
            seconds[node.split('::', 1)[0]] -= Decimal(str(elapsed))
        cancelled[log.stem] = {'sha256': sha(log), 'cancel': cancel.isoformat() if cancel else None,
                               'unfinished_lower_bound_seconds': unfinished,
                               'suspected_hang_seconds': hung,
                               'workers_last_result': {k: v.isoformat() for k, v in last.items()}}
        for name, value in seconds.items():
            if value > measured.get(name, Decimal(0)):
                measured[name] = value
                source_of[name] = 'worker_completion_intervals'
    data = json.loads(Path(a.timings).read_text())
    weights = data['file_seconds']
    nodeids = [line.strip() for line in Path(a.collection).read_text().splitlines()
               if '::' in line and line.strip().startswith('tests/')]
    ordinary = partition_lanes(nodeids)['ordinary']
    files = sorted({node.split('::', 1)[0] for node in ordinary} | set(a.extra_file))
    missing = [name for name in a.extra_file if not (ROOT / name).is_file()]
    if missing:
        raise ValueError(f'extra files not on disk: {missing}')
    raised = {}
    for name in files:
        value = measured.get(name)
        if value is None:
            continue
        ceiling = int(value.to_integral_value(rounding=ROUND_CEILING))
        if ceiling > weights.get(name, 0) * 1.25 and ceiling >= 30:
            raised[name] = {'old': weights.get(name), 'new': ceiling}
    new_weights = {**weights, **{name: row['new'] for name, row in raised.items()}}

    def shard_sums(weight_map, total):
        assignment = balanced_files(files, total, weight_map)
        known = [weight_map[f] for f in files if f in weight_map]
        known.sort()
        fallback = known[len(known) // 2] if known else 1.0
        sums, longest = Counter(), Counter()
        for name, shard in assignment.items():
            value = weight_map.get(name, fallback)
            sums[shard] += value
            longest[shard] = max(longest[shard], value)
        return {shard: {'sum_seconds': round(sums[shard]), 'longest_file_seconds': round(longest[shard]),
                        'files': sum(1 for s in assignment.values() if s == shard)}
                for shard in range(1, total + 1)}, assignment

    before, before_assignment = shard_sums(weights, 12)
    after, after_assignment = shard_sums(new_weights, 12)
    report = {'run_id': RUN_ID, 'run_commit': RUN_COMMIT, 'junit_sha256': junit_sources,
              'cancelled_logs': cancelled, 'collected_ordinary_files': len(files),
              'measured_top': sorted(((n, float(v)) for n, v in measured.items()), key=lambda r: -r[1])[:40],
              'raised': raised, 'pr_shards_before': before, 'pr_shards_after': after,
              'shard3_files_before': sorted(n for n, s in before_assignment.items() if s == 3),
              'shard10_files_before': sorted(n for n, s in before_assignment.items() if s == 10)}
    print(json.dumps(report, indent=1, default=str))
    if a.write and raised:
        if KEY in data['source']:
            raise ValueError(f'{KEY} already recorded: refusing to apply twice')
        data['file_seconds'] = new_weights
        # A labelled source block, like native_ci_h3_20261112: the updater
        # refuses runs with failures, and local_overrides is the closed
        # round-7 population that tests/test_ci_timing_update.py counts.
        data['source'][KEY] = {
            'run_id': RUN_ID, 'commit': RUN_COMMIT,
            'url': f'https://github.com/bridge2ai/data-sheets-schema/actions/runs/{RUN_ID}',
            'conclusion': 'failure; shards 3 and 10 cancelled at the 45-minute limit',
            'updater_refusal': 'use a successful run for timing estimates',
            'method': ('Per-file sums of this run\'s JUnit case times for completed shards '
                       '(source junit); for the cancelled shards 3 and 10, elapsed time between '
                       'consecutive results on each xdist worker from the job log, plus, for a test '
                       'still running at cancellation, the time from its start line to the '
                       'cancellation as a lower bound (source worker_completion_intervals). A weight '
                       'is raised to the measured value, rounded up, only when that exceeds the '
                       'recorded weight by more than 25 percent and is at least 30 s; no weight is '
                       'lowered. A suspected stall is reported and never becomes a weight.'),
            'junit_sha256': junit_sources,
            'log_sha256': {k: v['sha256'] for k, v in cancelled.items()},
            'unfinished_lower_bound_seconds': {k: v['unfinished_lower_bound_seconds']
                                               for k, v in cancelled.items()},
            'suspected_hang_seconds': {k: v['suspected_hang_seconds'] for k, v in cancelled.items()},
            'producer': 'scripts/adhoc/ci_shard_timing_from_run_43383271447_20261113.py',
            'producer_sha256': sha(__file__),
            'files': {name: {'seconds': row['new'], 'previous': row['old'], 'source': source_of[name]}
                      for name, row in sorted(raised.items())}}
        Path(a.timings).write_text(json.dumps(data, indent=2, sort_keys=False) + '\n')


if __name__ == '__main__':
    main()
