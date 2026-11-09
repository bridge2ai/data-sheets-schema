"""Apply #5517 D104, 2026-11-08; inputs: local context/bundle/chunk and live pin.
Outputs: bounded context/test/live-pin edits and scratch r4-audit.json.
Default verifies and plans; --apply writes. No historical registrations change.
"""
import hashlib
import json
from pathlib import Path
import sys

import yaml
from data_sheets_schema.evaluation_context import context_digest

ROOT = Path(__file__).resolve().parents[2]
SCRATCH = ROOT.parent / 'scratch-codex-5517'
assert not (ROOT.parent / 'plans/native_quiet_window.lock').exists()
quote = 'clinical data outside of expected min/max ranges were flagged in REDCap, which was visible in reports viewed by clinical research coordinators (CRCs) and Data Managers'
bundle = ROOT / 'data/preprocessed/concatenated/AI_READI_preprocessed.txt'
raw = bundle.read_bytes()
manifest = yaml.safe_load((ROOT / 'data/preprocessed/chunks/AI_READI_chunks.yaml').read_text())
assert hashlib.sha256(raw).hexdigest() == manifest['bundle_sha256']
lines = raw.splitlines(keepends=True)
chunk = next(c for c in manifest['chunks'] if c['id'] == 'c018')
chunk_raw = b''.join(lines[chunk['lines'][0]-1:chunk['lines'][1]])
assert hashlib.sha256(chunk_raw).hexdigest() == chunk['sha256']
assert quote in lines[4366].decode() and quote in chunk_raw.decode()
path = ROOT / 'data/context/ai_readi_context.yaml'
old = path.read_text()
context = yaml.safe_load(old)
old_pin = context_digest(context)
assert context['processing_software']['value'] is True
old_evidence = context['processing_software']['evidence']
assert old_evidence.startswith('[needs_owner: true]')
evidence = '[chunks: c018] ' + json.dumps(quote)
new = old.replace('  # chunks: [c007, c018]', '  # chunks: [c018]')
new = new.replace(json.dumps(old_evidence), json.dumps(evidence))
expected = yaml.safe_load(old)
expected['processing_software']['evidence'] = evidence
assert yaml.safe_load(new) == expected
new_pin = context_digest(expected)
pin_path = ROOT / 'notes/reviews/v10_human_decisions_and_context_review_2026-10-20.md'
pin_text = pin_path.read_text()
assert pin_text.count(old_pin) == 1
test_path = ROOT / 'tests/test_context_evidence_verbatim.py'
test = test_path.read_text()
changes = {
    "NEEDS_OWNER = {('ai_readi_context', 'processing_software')}": 'NEEDS_OWNER = set()',
    "assert counts['quoted'] == 40": "assert counts['quoted'] == 41",
    "assert counts['needs_owner'] == 1": "assert counts['needs_owner'] == 0",
}
for before, after in changes.items():
    assert test.count(before) == 1
    test = test.replace(before, after)
audit = dict(quote=quote, bundle=str(bundle.relative_to(ROOT)), line=4367,
             chunk='c018', bundle_sha256=manifest['bundle_sha256'],
             chunk_sha256=chunk['sha256'], old_pin=old_pin, new_pin=new_pin,
             inventory=dict(quoted=41, absence_supported=1, needs_owner=0))
if sys.argv[1:] == ['--apply']:
    for target, content in [(path, new), (pin_path, pin_text.replace(old_pin, new_pin)), (test_path, test)]:
        target.write_text(content)
        assert target.read_text() == content
    (SCRATCH / 'r4-audit.json').write_text(json.dumps(audit, indent=2) + '\n')
else:
    assert not sys.argv[1:]
print(json.dumps(audit, indent=2))
