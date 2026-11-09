"""PR5531 fix C byte consequences, 2026-11-08.

Inputs: main, fix A and current schemas/code; outputs: exact digest/instruction
bytes and JSON under scratch. Historical code loaded from local Git objects.
"""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from types import ModuleType, SimpleNamespace
from data_sheets_schema import profiles, bc1_context as bc
from data_sheets_schema.schema_snapshot import capture_schema

ROOT = Path(__file__).resolve().parents[2]
SCRATCH = ROOT.parent / 'scratch-pr5531-fix'
SCHEMA = ROOT / 'src/data_sheets_schema/schema'
def raw(ref, path):
    return subprocess.check_output(['git', 'show', f'{ref}:{path.relative_to(ROOT)}']) if ref else path.read_bytes()

results = {}
for label, ref in [('main', 'origin/main'), ('fix-b', '75463cb38'), ('fix-c', None)]:
    out = SCRATCH / f'fix-c-bytes-{label}'
    out.mkdir(exist_ok=True)
    path = ROOT / 'src/data_sheets_schema/schema_digest.py'
    module = ModuleType('pr5531_digest_' + label.replace('-', '_'))
    module.__file__ = str(path)
    sys.modules[module.__name__] = module
    exec(compile(raw(ref, path), str(path), 'exec'), module.__dict__)
    snapshots = {}
    for kind in ('full', 'core'):
        path = SCHEMA / ('data_sheets_schema_all.yaml' if kind == 'full' else 'data_sheets_schema_core_all.yaml')
        content = raw(ref, path)
        (out / path.name).write_bytes(content)
        snapshots[kind] = capture_schema(path, content=content, strict=True)
    values = {'bc1-schema-instructions': bc.schema_context(SimpleNamespace(full_schema=snapshots['full'], core_schema=snapshots['core']), None)}
    for profile in (profiles.BRIDGE2AI, profiles.NEUTRAL):
        for cls in ('Dataset', 'CoreDataset'):
            schema = 'data_sheets_schema_all.yaml' if cls == 'Dataset' else 'data_sheets_schema_core_all.yaml'
            values['digest-' + profile.name + '-' + cls] = module.digest_text(cls, out / schema, profile=profile)
    results[label] = {}
    for name, value in values.items():
        data = value.encode()
        (out / (name + '.txt')).write_bytes(data)
        results[label][name] = dict(bytes=len(data), md5=hashlib.md5(data).hexdigest(), sha256=hashlib.sha256(data).hexdigest())
for name in results['fix-c']:
    assert results['fix-b'][name] == results['fix-c'][name]
(SCRATCH / 'fix-c-bytes.json').write_text(json.dumps(results, indent=2) + '\n')
print(json.dumps(results, indent=2))
