#!/usr/bin/env python3
"""Read-only #6170/#6094 pin proposal after approval refusal, 2026-11-13.
Inputs current power-branch bytes; outputs proposed diffs in the report worktree.
Does not edit controller manifests, authority constants or scanner contracts.
"""
from pathlib import Path
import difflib
import hashlib
import json
import subprocess
R = Path(__file__).resolve().parents[2]
HP = R.parent / 'codex-native-host-power-20261113'
head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=HP, text=True).strip()
rows = []
changes = {}
for version in (1, 2):
    name = f'src/data_sheets_schema/native_controller_sources_v{version}.json'
    raw = (HP / name).read_bytes()
    value = json.loads(raw)
    prior = hashlib.sha256(raw).hexdigest()
    for module in ('native_control', 'run_native_canary'):
        pin = value['modules'][module]
        actual = hashlib.sha256((HP / pin['path']).read_bytes()).hexdigest()
        rows.append({'manifest': name, 'module': module, 'path': pin['path'],
                     'declared_sha256': pin['sha256'], 'actual_sha256': actual})
        pin['sha256'] = actual
    value['source_commit'] = head
    proposed = (json.dumps(value, indent=2) + '\n').encode()
    after = hashlib.sha256(proposed).hexdigest()
    changes[name] = (raw, proposed)
    authorities = ['native_attribution_controller' + ('_v2' if version == 2 else '') + '.py']
    if version == 2: authorities.append('native_shared_authority_wire.py')
    for authority in authorities:
        path = 'src/data_sheets_schema/' + authority
        original = (HP / path).read_bytes()
        assert prior.encode() in original
        changes[path] = (original, original.replace(prior.encode(), after.encode()))
out = R / 'notes/development_efficiency_20261111/handoffs'
record = {'status': 'proposal only; requires approval', 'source_head': head, 'module_mismatches': rows,
          'files': [{'path': name, 'before_sha256': hashlib.sha256(before).hexdigest(),
                     'proposed_sha256': hashlib.sha256(after).hexdigest()}
                    for name, (before, after) in changes.items()]}
with (out / 'codex-h2-controller-pin-proposal-20261113.json').open('x') as stream:
    json.dump(record, stream, indent=2); stream.write('\n')
with (out / 'codex-h2-controller-pin-proposal-20261113.diff').open('x') as stream:
    for name, (before, after) in changes.items():
        stream.writelines(difflib.unified_diff(before.decode().splitlines(True), after.decode().splitlines(True),
                                             fromfile='a/' + name, tofile='b/' + name))
print(json.dumps(record, indent=2))
