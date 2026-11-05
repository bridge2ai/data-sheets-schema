#!/usr/bin/env python3
# Purpose: enumerate every model-facing G1 F6/N7 byte change, including embedded JSON.
# Inputs: before/after capture JSON; output: complete delta JSON (argv 1,2,3).
# Generality review N5/N7 byte evidence, 2026-10-29; no normalized payload bytes.
import difflib
import hashlib
import json
from pathlib import Path
import sys

def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()

before, after = [json.loads(Path(p).read_bytes()) for p in sys.argv[1:3]]
rows = []
missing = object()

def compare(a, b, path):
    if a == b:
        return
    if isinstance(a, dict) and isinstance(b, dict):
        for key in sorted(a.keys() | b.keys()):
            compare(a.get(key, missing), b.get(key, missing), path + '/' + key)
    elif isinstance(a, list) and isinstance(b, list) and len(a) == len(b):
        for index, (old, new) in enumerate(zip(a, b)):
            compare(old, new, path + '/' + str(index))
    elif isinstance(a, str) and isinstance(b, str):
        for sep in ('', '\n\n'):
            aa, bb = (['', a], ['', b]) if not sep else (a.split(sep, 1), b.split(sep, 1))
            if len(aa) != 2 or len(bb) != 2 or aa[0] != bb[0]:
                continue
            try:
                av, bv = json.loads(aa[1]), json.loads(bb[1])
            except ValueError:
                continue
            # Embedded JSON is emitted canonically. Refuse to hide whitespace
            # changes by accidentally treating a parsed equivalence as equality.
            if canonical(av).decode() != aa[1] or canonical(bv).decode() != bb[1]:
                continue
            compare(av, bv, path + '/embedded_json')
            return
        if path.endswith('sha256'):
            rows.append({'path': path, 'before': a, 'after': b})
            return
        edits = [{'operation': tag, 'before': a[i:j], 'after': b[k:l]}
                 for tag, i, j, k, l in difflib.SequenceMatcher(None, a, b).get_opcodes()
                 if tag != 'equal']
        rows.append({'path': path, 'before_bytes': len(a.encode()), 'after_bytes': len(b.encode()),
                     'before_sha256': hashlib.sha256(a.encode()).hexdigest(),
                     'after_sha256': hashlib.sha256(b.encode()).hexdigest(), 'edits': edits})
    else:
        rows.append({'path': path, 'before': '<absent>' if a is missing else a,
                     'after': '<absent>' if b is missing else b})

summary = {}
for phase in sorted(before['payloads']):
    a, b = before['payloads'][phase], after['payloads'][phase]
    ab, bb = canonical(a), canonical(b)
    start = len(rows)
    compare(a, b, phase)
    summary[phase] = {'before_bytes': len(ab), 'after_bytes': len(bb), 'delta': len(bb) - len(ab),
                      'before_sha256': hashlib.sha256(ab).hexdigest(),
                      'after_sha256': hashlib.sha256(bb).hexdigest(), 'changed_leaves': len(rows) - start}
expected = set()
for phase, index in [('full', 6), ('reconcile_full', 8), ('report', 14)]:
    expected.add(f'{phase}/messages/0/content/0/text')
    prefix = f'{phase}/messages/0/content/{index}/text/embedded_json/'
    expected.update(prefix + 'schema/sources/0/' + key for key in ('bytes', 'sha256'))
    if phase != 'full':
        expected.add(prefix + 'classes/Instance/data_substrate/description')
prefix = 'typed_audit_omission/messages/0/content/'
expected.update(prefix + '3/text/embedded_json/' + key for key in (
    'classes/Instance/data_substrate/description', 'schema/sources/0/bytes', 'schema/sources/0/sha256'))
expected.update(prefix + '5/text/embedded_json/' + key for key in (
    'inner_request_sha256', 'packet_inner_request_sha256', 'packet_sha256', 'registration_sha256'))
expected.update(prefix + '6/text/embedded_json/' + key for key in (
    'packet_request_sha256', 'request_sha256', 'payload/schema/sources/0/sha256',
    'payload/schema/classes/Instance/slots/data_substrate/definition/description'))
assert {row['path'] for row in rows} == expected, 'unexplained model-facing change'
assert {phase: item['delta'] for phase, item in summary.items()} == {
    'full': 135, 'reconcile_full': 224, 'report': 224, 'typed_audit_omission': 178}
Path(sys.argv[3]).write_text(json.dumps({'phases': summary, 'changes': rows}, indent=2) + '\n')
print(json.dumps(summary, indent=2))
for row in rows:
    detail = row['edits'] if 'edits' in row else {'before': row['before'], 'after': row['after']}
    print(row['path'], json.dumps(detail, ensure_ascii=False))
