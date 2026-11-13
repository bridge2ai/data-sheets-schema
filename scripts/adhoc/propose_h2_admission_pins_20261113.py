#!/usr/bin/env python3
"""Read-only complete controller pin proposal, 2026-11-13.
Inputs final helper-2 source and all test Python files, including ignored files.
Outputs proposed manifest/constant diffs and test-pin census. Applies nothing.
"""
import ast
import difflib
import hashlib
import json
from pathlib import Path
import re
import subprocess

R = Path(__file__).resolve().parents[2]
HP = R.parent / 'codex-native-host-power-20261113'
out = R / 'notes/development_efficiency_20261111/handoffs'
prefix = 'codex-h2-admission-pin-proposal-20261113'
head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=HP, text=True).strip()
sha = lambda raw: hashlib.sha256(raw).hexdigest()
changes, rows, digests = {}, [], {}
for version in (1, 2):
    name = f'src/data_sheets_schema/native_controller_sources_v{version}.json'
    raw = (HP / name).read_bytes(); value = json.loads(raw)
    prior = sha(raw)
    digests[prior] = name
    for module, pin in value['modules'].items():
        actual = sha((HP / pin['path']).read_bytes())
        digests[pin['sha256']] = pin['path']
        rows.append(dict(manifest=name, module=module, path=pin['path'],
            declared_sha256=pin['sha256'], actual_sha256=actual))
        pin['sha256'] = actual
    value['source_commit'] = head
    proposed = (json.dumps(value, indent=2) + '\n').encode()
    changes[name] = (raw, proposed)
    authorities = ['native_attribution_controller' + ('_v2' if version == 2 else '') + '.py']
    if version == 2: authorities.append('native_shared_authority_wire.py')
    for authority in authorities:
        path = 'src/data_sheets_schema/' + authority
        original = (HP / path).read_bytes()
        assert original.count(prior.encode()) == 1
        changes[path] = (original, original.replace(prior.encode(), sha(proposed).encode()))

census, context = [], []
paths = sorted((HP / 'tests').rglob('*.py'))  # pathlib does not honor gitignore.
for path in paths:
    text = path.read_text()
    for n, line in enumerate(text.splitlines(), 1):
        for digest in re.findall(r'\b[0-9a-f]{64}\b', line):
            if digest in digests:
                module_path = digests[digest]
                actual = sha((HP / module_path).read_bytes())
                census.append(dict(path=str(path.relative_to(HP)), line=n,
                    literal=digest, source=module_path, actual_sha256=actual,
                    action='unchanged; exact current source' if actual == digest else 'review required'))
        if re.search(r'(run_native_canary|native_control|controller_sources).*(sha|digest)|(SHA|sha|digest).*(run_native_canary|native_control|controller_sources)', line):
            context.append(dict(path=str(path.relative_to(HP)), line=n, text=line))
assert all(row['action'].startswith('unchanged') for row in census), census
permission = HP / 'tests/test_native_shared_permission_protocol.py'
node = next(n for n in ast.parse(permission.read_text()).body if isinstance(n, ast.Assign)
            and any(isinstance(t, ast.Name) and t.id == 'CONTROL_SHA' for t in n.targets))
assert node.value.value == sha((HP / 'notes/matched_cborg_2026-09-13/native_controls/native_control.py').read_bytes())
record = dict(status='proposal only; lead applies after review', source_head=head,
    module_census=rows, test_pin_census=census, test_pin_context=context,
    search_includes_hidden_ignored=True, test_python_files_examined=len(paths),
    permission_protocol_test=dict(path=str(permission.relative_to(HP)), line=node.lineno,
        sha256=node.value.value, action='retain; native_control.py did not change in this assignment'),
    historical_provenance='Old protocol prose and saved historical fixtures remain unchanged.',
    files=[dict(path=name, before_sha256=sha(before), proposed_sha256=sha(after))
           for name, (before, after) in changes.items()])
with (out / (prefix + '.json')).open('x') as stream:
    stream.write(json.dumps(record, indent=2).replace(chr(64), '\\u0040') + '\n')
with (out / (prefix + '.diff')).open('x') as stream:
    for name, (before, after) in changes.items():
        stream.writelines(difflib.unified_diff(before.decode().splitlines(True), after.decode().splitlines(True),
            fromfile='a/' + name, tofile='b/' + name))
print(json.dumps(dict(path=str(out / (prefix + '.diff')),
    sha256=sha((out / (prefix + '.diff')).read_bytes()), test_pins=len(census), files=len(changes))))
