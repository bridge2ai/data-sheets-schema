"""#5517 / PR #5532 stop-condition evidence, 2026-11-08.

Inputs: pinned AI-READI bundle and chunk manifest. Outputs: exact c019 bytes,
line-numbered term hits and JSON audit in the sole authorized scratch directory.
Standard library only; direct byte reads include ignored files. No source edits.
"""
import hashlib
import json
import os
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(os.environ.get('D4D_5517_SCRATCH', ROOT.parent / 'scratch-5517'))
assert not (ROOT.parent / 'plans/native_quiet_window.lock').exists()
manifest = (ROOT / 'data/preprocessed/chunks/AI_READI_chunks.yaml').read_text()
bundle = ROOT / 'data/preprocessed/concatenated/AI_READI_preprocessed.txt'
raw = bundle.read_bytes()
digest = hashlib.sha256(raw).hexdigest()
assert digest == re.search(r'^bundle_sha256: (\w+)$', manifest, re.M)[1]
record = re.search(r'^- id: c019\n(.*?)(?=^- id:)', manifest, re.M | re.S)[1]
first, last = map(int, re.search(r'  lines:\n  - (\d+)\n  - (\d+)', record).groups())
lines = raw.splitlines(keepends=True)
chunk = b''.join(lines[first - 1:last])
chunk_digest = hashlib.sha256(chunk).hexdigest()
assert chunk_digest == re.search(r'  sha256: (\w+)', record)[1]
assert len(chunk) == int(re.search(r'  bytes: (\d+)', record)[1])
pattern = r'software|REDCap|process|automat|clean|standard|tool|pipeline|code'
hits = b''.join(str(n).encode() + b':' + line for n, line in
                enumerate(lines[first - 1:last], first)
                if re.search(pattern, line.decode('utf-8'), re.I))
quote = 'All of our data files are in formats that are accessible with free software commonly used for such data types so no specific software is required.'
assert quote.encode() in chunk
d104 = 'clinical data outside of expected min/max ranges were flagged in REDCap, which was visible in reports viewed by clinical research coordinators (CRCs) and Data Managers'
assert d104.encode() in lines[4366]
assert d104.encode() not in chunk
audit = dict(bundle=str(bundle.relative_to(ROOT)), bundle_sha256=digest,
             chunk='c019', lines=[first, last], bytes=len(chunk), sha256=chunk_digest,
             search_pattern=pattern, search_flags='re.IGNORECASE',
             search_scope='entire c019 read directly, independent of gitignore',
             software_accessibility_quote=quote, d104_line=4367,
             d104_quote=d104, d104_quote_in_c019=False)
OUT.mkdir(exist_ok=True)
for name, content in [('r5-ai-readi-c019.txt', chunk), ('r5-c019-search.txt', hits),
                      ('r5-stop-audit.json', (json.dumps(audit, indent=2) + '\n').encode())]:
    target = OUT / name
    assert not target.exists(), target
    target.write_bytes(content)
    assert target.read_bytes() == content and content
print(json.dumps(audit, indent=2))
