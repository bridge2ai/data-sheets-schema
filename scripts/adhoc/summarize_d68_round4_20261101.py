#!/usr/bin/env python3
"""#5212 round 4, 2026-11-01: summarize retained pytest and writer evidence.

Inputs: offline-runner JSON paths; sibling basetemp trees. Output: concise JSON
on stdout for the task-5 report, preserving failure/skip node identities.
"""
from collections import Counter
import json
from pathlib import Path
import sys

results = {}
for argument in sys.argv[1:]:
    path = Path(argument)
    data = json.loads(path.read_text())
    counts = Counter()
    failed, skipped = [], []
    for row in data['reports']:
        if row['when'] == 'call' or row['outcome'] != 'passed':
            outcome = 'error' if row['outcome'] == 'failed' and row['when'] != 'call' else row['outcome']
            counts[outcome] += 1
        if row['outcome'] == 'failed':
            failed.append({'nodeid': row['nodeid'], 'when': row['when'], 'message': row['message']})
        if row['outcome'] == 'skipped':
            skipped.append({'nodeid': row['nodeid'], 'message': row['message']})
    census = [json.loads(p.read_text()) for p in path.with_suffix('').rglob('artifact-census.json')]
    writers = [json.loads(p.read_text()) for p in path.with_suffix('').rglob('writer-census.json')]
    results[path.stem] = {'exit_code': data['exit_code'], 'selected': len(data['selected']),
        'counts': dict(counts), 'collection_errors': data['collection_errors'],
        'unfinished': sorted(set(data['selected']) - {row['nodeid'] for row in data['reports']
            if row['when'] == 'call' or row['outcome'] != 'passed'}),
        'failures': failed, 'skips': skipped,
        'artifact_census_nodes': len(census), 'artifacts': sum(c['singletons'] for c in census),
        'refusal_checks': sum(c['refusal_checks'] for c in census),
        'writer_counts': [c['count'] for c in writers],
        'unbound_writer_files': [p for c in writers for p in c['unbound']]}
print(json.dumps(results, indent=2))
