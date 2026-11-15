"""Issue 6214, 2026-11-15: summarize retained pytest evidence into scratch JSON."""
from collections import Counter, defaultdict
import json
from pathlib import Path
import re
scratch = Path('/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-callback-teardown-20261115')
report = scratch / 'final-required.reports.jsonl'
rows = [json.loads(line) for line in report.read_text().splitlines()] if report.exists() else []
continuation = scratch / 'remaining-required.reports.jsonl'
if continuation.exists():
    rows.extend(json.loads(line) for line in continuation.read_text().splitlines())
by_file = defaultdict(Counter)
failures = []
for row in rows:
    by_file[row['nodeid'].split('::')[0]][row['when'] + ':' + row['outcome']] += 1
    if row['outcome'] == 'failed':
        failures.append(row)
runs = {}
for name in ('canary', 'required', 'collection', 'collection-final', 'final-canary', 'final-required', 'final-collection', 'remaining-required'):
    path = scratch / (name + '.json')
    if path.exists():
        runs[name] = json.loads(path.read_text())
        log = (scratch / (name + '.log')).read_text()
        runs[name]['summary_lines'] = [line for line in log.splitlines() if re.search(r'\d+ (passed|failed|tests collected)', line)]
causes = Counter('uncommitted callback source' if 'consumed source differs from the reviewed commit: src/data_sheets_schema/native_shared_callback_orchestration.py' in row['detail'] else 'other' for row in failures)
totals = Counter(row['when'] + ':' + row['outcome'] for row in rows)
summary = dict(totals=totals, by_file=dict(by_file), failures=failures, failure_causes=causes, runs=runs)
(scratch / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
print(json.dumps(dict(totals=totals, by_file=dict(by_file), failure_causes=causes, completed_runs=list(runs)), indent=2))
collection_log = scratch / 'final-collection.log'
if collection_log.exists():
    expected = Counter(line.split('::')[0] for line in collection_log.read_text().splitlines()
                       if line.startswith('tests/') and '::' in line)
    seen = defaultdict(set)
    for row in rows:
        seen[row['nodeid'].split('::')[0]].add(row['nodeid'])
    remaining = {name: expected[name] - len(seen[name]) for name in sorted(by_file)}
    summary['expected_by_file'] = {name: expected[name] for name in sorted(by_file)}
    summary['remaining_by_file'] = remaining
    (scratch / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    print(json.dumps(dict(remaining_by_file=remaining), indent=2))
    completed_nodes = {row['nodeid'] for row in rows}
    summary['remaining_nodeids'] = [line for line in collection_log.read_text().splitlines()
        if line.startswith('tests/') and '::' in line
        and line.split('::')[0] in by_file and line not in completed_nodes]
    (scratch / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
