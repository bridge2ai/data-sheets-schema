"""PR5531: measure digest and complete BC1 instruction bytes; 2026-11-08.

Inputs: current checkout schemas/code. Outputs: JSON and exact text in supplied
scratch directory. Run before and after fix A with the same absolute paths.
"""
import hashlib
import json
from pathlib import Path
import sys
import subprocess
from types import SimpleNamespace
from data_sheets_schema import schema_digest as digest, profiles, bc1_context as bc
from data_sheets_schema.schema_snapshot import capture_schema

out = Path(sys.argv[1])
out.mkdir(parents=True, exist_ok=True)
root = Path(__file__).resolve().parents[2]
schema = root / 'src/data_sheets_schema/schema'
values = {}
ref = sys.argv[2] if len(sys.argv) > 2 else None
if ref is None:
    for profile in (profiles.BRIDGE2AI, profiles.NEUTRAL):
        values['digest-' + profile.name] = digest.digest_text('Dataset', profile=profile)

def snapshot(name):
    path = schema / name
    raw = (subprocess.check_output(['git', 'show', f'{ref}:{path.relative_to(root)}'], cwd=root)
           if ref else path.read_bytes())
    return capture_schema(path, content=raw, strict=True)

captured = SimpleNamespace(
    full_schema=snapshot('data_sheets_schema_all.yaml'),
    core_schema=snapshot('data_sheets_schema_core_all.yaml'))
values['bc1-schema-instructions'] = bc.schema_context(captured, None)
result = {}
for name, value in values.items():
    raw = value.encode()
    (out / (name + '.txt')).write_bytes(raw)
    result[name] = dict(bytes=len(raw), md5=hashlib.md5(raw).hexdigest(), sha256=hashlib.sha256(raw).hexdigest())
(out / 'measurements.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(result, indent=2))
