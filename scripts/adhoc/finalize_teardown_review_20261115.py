"""Issue 6214, 2026-11-15: record dispositions after the final read-only review."""
import json
from pathlib import Path
scratch = Path('/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-callback-teardown-20261115')
p = scratch / 'review-findings.json'
rows = json.loads(p.read_text())
rows[0]['disposition'] = 'Fixed: scope poison check precedes yield; focused regression passed.'
rows[1]['disposition'] = 'Fixed: retained stacks are rooted in sys; focused regression passed.'
extra = [
    dict(id='R5', finding='Real retained source-loader generators emit ignored finalizer errors at interpreter shutdown after sys globals are cleared.', disposition='Report to lead. Both witness processes exited zero; no late close occurred on worker release. No shutdown cleanup is added because it could revoke a live worker.'),
    dict(id='R6', finding='Integration fixtures refuse uncommitted callback source, and the sandbox refuses the Git index lock.', disposition='Per assignment, leave uncommitted for the lead. Preserve failures without bypassing reviewed-commit verification.')]
rows = [row for row in rows if row['id'] not in {item['id'] for item in extra}] + extra
p.write_text(json.dumps(rows, indent=2) + '\n')
print(json.dumps(rows, indent=2))
