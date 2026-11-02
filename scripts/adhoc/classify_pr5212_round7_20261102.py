#!/usr/bin/env python3
"""#5212 round 7, 2026-11-02: compare failures with paired round-6 evidence.

Inputs: --baseline-summary and one or more complete phase ledgers. Output:
JSON classifying each node by the actual exception mechanism and final frame.
Unknown or changed failures require a pinned-main replay, never an automatic
environmental waiver. This helper reads evidence only.
"""
import argparse
from collections import Counter
import json
from pathlib import Path
import re

p = argparse.ArgumentParser()
p.add_argument('--baseline-summary', type=Path, required=True)
p.add_argument('phases', type=Path, nargs='+')
a = p.parse_args()


def signature(node, message):
    frames = re.findall(r'^([^\n]*\.py:\d+): ([A-Za-z]+(?:Error|Exception))\s*$', message, re.M)
    frame = frames[-1] if frames else None
    if 'PermissionError' in message and ('self.socket.bind(' in message or 'unused.bind(' in message):
        cause = 'loopback bind denied'
    elif 'PermissionError' in message and "'ps'" in message:
        cause = 'ps denied'
    elif 'push' in message and ('exit status 125' in message or 'returncode = 125' in message):
        cause = 'offline wrapper refused git push'
    elif (node.startswith('tests/test_run_lock.py::TestAgainstARealProcess::')
          and ('process survived SIGTERM' in message or
               ('Lists differ:' in message and 'Lock(path=' in message and ' != []' in message))):
        # Round 6's retained main replay and the independent forwarding
        # observer establish the denied-ps origin of these two assertions.
        cause = 'ps denied (retained round-6 process-state evidence)'
    else:
        cause = None
    return {'cause': cause, 'frame': frame}


baseline = {}
for name, result in json.loads(a.baseline_summary.read_text()).items():
    if name.startswith('r6-final2-'):
        for row in result['failures']:
            baseline.setdefault(row['nodeid'], []).append(signature(row['nodeid'], row['message']))
results = {}
for path in a.phases:
    phase = json.loads(path.read_text())
    counts, failures = Counter(), []
    for row in phase['reports']:
        if row['when'] == 'call' or row['outcome'] != 'passed':
            outcome = 'error' if row['outcome'] == 'failed' and row['when'] != 'call' else row['outcome']
            counts[outcome] += 1
        if row['outcome'] == 'failed':
            current = signature(row['nodeid'], row['message'])
            prior = baseline.get(row['nodeid'], [])
            known = current['cause'] is not None and current['frame'] is not None and current in prior
            failures.append({'nodeid': row['nodeid'], 'when': row['when'], **current,
                'round6_same_failure': known, 'needs_main_replay': not known,
                'round6_signatures': prior})
    results[path.stem] = {'counts': dict(counts), 'failures': failures,
        'collection_errors': phase['collection_errors'],
        'unfinished': sorted(set(phase['selected']) - {row['nodeid'] for row in phase['reports']
            if row['when'] == 'call' or row['outcome'] != 'passed'})}
print(json.dumps({'round6_evidence': str(a.baseline_summary), 'phases': results}, indent=2))
