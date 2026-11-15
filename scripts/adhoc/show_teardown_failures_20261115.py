"""Issue 6214, 2026-11-15: read saved pytest failures and print bounded details."""
import json
from pathlib import Path
scratch = Path('/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-callback-teardown-20261115')
path = scratch / 'final-required.reports.jsonl'
if path.exists():
    for line in path.read_text().splitlines():
        row = json.loads(line)
        if row['outcome'] == 'failed':
            print(row['nodeid'], row['when'])
            print(row['detail'][-2000:].replace(chr(64), '[at]'))
