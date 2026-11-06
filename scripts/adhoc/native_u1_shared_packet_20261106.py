"""U1 #4354, 2026-11-06: exact protected admission proposal; NEVER apply it.
Inputs: unchanged M7 shared_generation.py and candidate api_runner.py.
Outputs: two unified patches and pre/postimage identities for AGY/owner review.
"""
from pathlib import Path
import difflib
import hashlib
import json
import subprocess
ROOT = Path(__file__).resolve().parents[2]
BASE = '8bc90e93d736d464f98e9eedffee45f0ad8e5d3f'
OUT = ROOT / 'scripts/adhoc/native_u1_packets'
OUT.mkdir(exist_ok=True)

def packet(name, target, old, new, rationale):
    assert old != new
    patch = ''.join(difflib.unified_diff(old.decode().splitlines(True), new.decode().splitlines(True), fromfile='a/' + target, tofile='b/' + target)).encode()
    (OUT / (name + '.patch')).write_bytes(patch)
    info = {'status': 'proposal_only_not_applied_or_tested', 'target': target,
            'base': BASE, 'preimage_sha256': hashlib.sha256(old).hexdigest(),
            'postimage_sha256': hashlib.sha256(new).hexdigest(),
            'patch_sha256': hashlib.sha256(patch).hexdigest(), 'rationale': rationale}
    (OUT / (name + '.json')).write_text(json.dumps(info, indent=2) + '\n')
    assert (ROOT / target).read_bytes() == old
    return info

target = 'src/data_sheets_schema/shared_generation.py'
old = (ROOT / target).read_bytes()
assert old == subprocess.check_output(['git', 'show', f'{BASE}:{target}'], cwd=ROOT)
needle = b'    if not version:\n        if (spec.condition in MODES.values()'
assert old.count(needle) == 1
new = old.replace(needle, b'''    if not version:
        if getattr(spec, 'native_shared_generation_version', 0):
            from .native_shared_render import validate_spec
            validate_spec(spec)
            return None
        if (spec.condition in MODES.values()''')
a = packet('shared_generation', target, old, new,
    'Keep the existing BC1 validation and all API v1/v2 refusals. Only a separately validated native selection may return from the disabled API branch. M7 scanner already recognizes this exact dispatch; caller must restore unconditional shared admission. No runtime/provider is called.')
target = 'src/data_sheets_schema/api_runner.py'
old = (ROOT / target).read_bytes()
needle = b'''        if not self.native_shared_generation_version:
            from .shared_generation import select as select_shared
            select_shared(self)
'''
assert old.count(needle) == 1
new = old.replace(needle, b'''        from .shared_generation import select as select_shared
        select_shared(self)
''')
b = packet('api_runner_companion', target, old, new,
    'Restore unconditional final shared selector call, as required by M7 scanner admission proof. Apply only together with the separately approved protected shared-generation patch; without it native selections refuse. Preserve early native validation and existing D76 binding/replay code.')
print(json.dumps([a, b], indent=2))
