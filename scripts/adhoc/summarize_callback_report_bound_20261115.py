"""Issue 6214, 2026-11-15: summarize saved report tests and audit evidence."""
from collections import Counter
import json
from pathlib import Path

scratch = Path('../scratch-callback-teardown-20261115')
rows = [json.loads(line) for line in (scratch / 'report-required.reports.jsonl').read_text().splitlines()]
counts = Counter(row['when'] + ':' + row['outcome'] for row in rows)
failures = [row for row in rows if row['outcome'] == 'failed']
result = dict(counts=dict(counts), failures=failures)
(scratch / 'report-summary.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(dict(counts=dict(counts), failures=[dict(nodeid=row['nodeid'], when=row['when'], detail=row['detail'][-1800:]) for row in failures]), indent=2).replace(chr(64), '[at]'))
