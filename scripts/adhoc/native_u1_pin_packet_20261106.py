"""U1 #4354 2026-11-06: propose (never apply) additive protected prompt pins.
Inputs: M7 canonical registry and U1 prompt bytes. Outputs: exact patch + hashes.
"""
from pathlib import Path
import difflib
import hashlib
import json
import subprocess
ROOT = Path(__file__).resolve().parents[2]
TARGET = 'src/download/prompts/canonical_hashes.yaml'
BASE = '8bc90e93d736d464f98e9eedffee45f0ad8e5d3f'
DONOR = '5d87ea67660e00affcbc6dbae0d35172d85209d7'
old = (ROOT / TARGET).read_bytes()
assert old == subprocess.check_output(['git', 'show', f'{BASE}:{TARGET}'], cwd=ROOT)
rows = ''
for name in ('generation', 'receipt_policy'):
    path = f'src/download/prompts/native_shared_{name}_v1.md'
    raw = (ROOT / path).read_bytes()
    assert raw == subprocess.check_output(['git', 'show', f'{DONOR}:{path}'], cwd=ROOT)
    rows += (f'  {path}:\n    bytes: {len(raw)}\n    pinned_at_commit: {DONOR}\n'
             f'    pinned_blob_path: {path}\n    pinned_on: \'2026-11-06\'\n'
             '    reason: Native U1 shared-v1 declared-difference assets; no API asset rotation (#4354).\n'
             f'    sha256: {hashlib.sha256(raw).hexdigest()}\n')
assert old.count(b'hash_algorithm: sha256\n') == 1
new = old.replace(b'hash_algorithm: sha256\n', rows.encode() + b'hash_algorithm: sha256\n')
out = ROOT / 'scripts/adhoc/native_u1_packets'
out.mkdir(exist_ok=True)
patch = ''.join(difflib.unified_diff(old.decode().splitlines(True), new.decode().splitlines(True), fromfile='a/' + TARGET, tofile='b/' + TARGET)).encode()
(out / 'canonical_hashes.patch').write_bytes(patch)
info = {'status': 'proposal_only_not_applied', 'target': TARGET, 'base': BASE,
        'preimage_sha256': hashlib.sha256(old).hexdigest(), 'postimage_sha256': hashlib.sha256(new).hexdigest(),
        'patch_sha256': hashlib.sha256(patch).hexdigest(),
        'rationale': 'Add exactly two native-only prompt pins. Existing API pins and protected source remain unchanged. AGY/owner approval and application required.'}
(out / 'canonical_hashes.json').write_text(json.dumps(info, indent=2) + '\n')
assert (ROOT / TARGET).read_bytes() == old
print(json.dumps(info, indent=2))
