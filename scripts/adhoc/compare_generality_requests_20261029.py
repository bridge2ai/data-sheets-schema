#!/usr/bin/env python3
# Purpose: exact G1 CHORUS shared-v1 payload delta, including embedded catalog JSON.
# Inputs: external before/after captures; outputs: external diff and gzip evidence.
# Generality F6 byte proof, 2026-10-29. Does not normalize hashes or payload bytes.
import difflib
import gzip
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT.parent / 'plans/reviews/generality_g1_evidence_2026-10-29'
OUT.mkdir(parents=True, exist_ok=True)
before = json.loads(Path('/private/tmp/g1-request-before.json').read_bytes())
after = json.loads(Path('/private/tmp/g1-request-after.json').read_bytes())
changes = []


def compare(a, b, path='payload'):
    if a == b:
        return
    if isinstance(a, dict) and isinstance(b, dict):
        for key in sorted(a.keys() | b.keys()):
            compare(a.get(key), b.get(key), path + '/' + str(key))
    elif isinstance(a, list) and isinstance(b, list) and len(a) == len(b):
        for i, (old, new) in enumerate(zip(a, b)):
            compare(old, new, path + '/' + str(i))
    elif isinstance(a, str) and isinstance(b, str):
        aa, bb = a.split('\n\n', 1), b.split('\n\n', 1)
        if len(aa) == len(bb) == 2 and aa[0] == bb[0]:
            try:
                old, new = json.loads(aa[1]), json.loads(bb[1])
            except ValueError:
                pass
            else:
                compare(old, new, path + '/embedded_json')
                return
        values = ({'before': a, 'after': b} if max(len(a), len(b)) < 200 else {
            'before_bytes': len(a.encode()), 'after_bytes': len(b.encode()),
            'before_sha256': hashlib.sha256(a.encode()).hexdigest(),
            'after_sha256': hashlib.sha256(b.encode()).hexdigest()})
        changes.append({'path': path, **values,
            'diff': ''.join(difflib.unified_diff(a.splitlines(True), b.splitlines(True),
                                               fromfile='before', tofile='after'))})
    else:
        changes.append({'path': path, 'before': a, 'after': b})


compare(before['payload'], after['payload'])
assert {change['path'] for change in changes} == {
    'payload/messages/0/content/0/text',
    'payload/messages/0/content/6/text/embedded_json/schema/sources/0/bytes',
    'payload/messages/0/content/6/text/embedded_json/schema/sources/0/sha256'}
marker = '`data_substrate` draws from '
inserted = ("a term from EDAM Data, EDAM Format, IANA media types (the source's own identifier, "
            "as an IRI or CURIE, when the documents supply one); ")
assert after['payload']['messages'][0]['content'][0]['text'] == (
    before['payload']['messages'][0]['content'][0]['text'].replace(marker, marker + inserted, 1))
for value in (before, after):
    payload_bytes = json.dumps(value['payload'], sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()
    assert hashlib.sha256(payload_bytes).hexdigest() == value['payload_sha256']
summary = {'before_payload_sha256': before['payload_sha256'],
           'after_payload_sha256': after['payload_sha256'], 'changed_values': changes}
(OUT / 'request_delta.json').write_text(json.dumps(summary, indent=2) + '\n')
for name, value in [('before', before), ('after', after)]:
    raw = json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()
    (OUT / f'request_{name}.json.gz').write_bytes(gzip.compress(raw, mtime=0))
    assert json.loads(gzip.decompress((OUT / f'request_{name}.json.gz').read_bytes())) == value
print(json.dumps({'changed_paths': [row['path'] for row in changes],
                  'before': before['payload_sha256'], 'after': after['payload_sha256']}, indent=2))
