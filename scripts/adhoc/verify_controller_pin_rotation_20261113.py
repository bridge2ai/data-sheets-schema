"""Verify a native controller pin rotation against the bytes in this checkout.

Purpose: before the lead commits a controller pin rotation on the native
candidate (draft PR 5968), check every pinned value it touches against the
bytes actually present, independently of the helper that proposed it:

  1. each module listed in native_controller_sources_v1.json and _v2.json
     hashes to its recorded sha256, both in the working tree and at the
     recorded source_commit;
  2. the sha256 of each sources file equals the constant that pins it
     (SOURCES_SHA256 in the two attribution controllers and
     CONTROLLER_SOURCES_SHA256 in native_shared_authority_wire.py);
  3. native_control.py still hashes to CONTROL_SHA in the permission-protocol
     test;
  4. the four protected files keep their owner-approved hashes;
  5. every path the specificity scanner pins in its closed native v2 render
     summaries is compared with the working bytes, so a rotation that moves
     a scanner pin is listed rather than discovered by a refusal.

Inputs: the checkout root (default: the current directory).
Output: a JSON report on stdout; exit 1 if checks 1 to 4 fail. Check 5 is
reported, never fatal, because the scanner pins are rotated in a later step.

Serves: helper 2's admission pin proposal (sha256 f2d7a46a...), issue 6094,
draft PR 5968. Written by the Claude lead, 2026-11-13.
"""
import ast
import hashlib
import json
import subprocess
import sys
from pathlib import Path

PROTECTED = {
    'src/data_sheets_schema/shared_generation.py': '2ec18e60',
    'src/data_sheets_schema/api_runner.py': '830eec1e',
    'src/download/prompts/canonical_hashes.yaml': 'd0de85f3',
    'tests/utils/run_spec_boundary_contracts.json': 'b1e0cbd1',
}
SCAN = '.claude/skills/d4d-generation-specificity-audit/scan.py'
PIN_CONSTANTS = [
    ('src/data_sheets_schema/native_attribution_controller.py', 'SOURCES_SHA256',
     'src/data_sheets_schema/native_controller_sources_v1.json'),
    ('src/data_sheets_schema/native_attribution_controller_v2.py', 'SOURCES_SHA256',
     'src/data_sheets_schema/native_controller_sources_v2.json'),
    ('src/data_sheets_schema/native_shared_authority_wire.py', 'CONTROLLER_SOURCES_SHA256',
     'src/data_sheets_schema/native_controller_sources_v2.json'),
]


def sha(data):
    return hashlib.sha256(data).hexdigest()


def constant(path, name):
    tree = ast.parse(path.read_text(encoding='utf-8'))
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
                isinstance(t, ast.Name) and t.id == name for t in node.targets):
            return ast.literal_eval(node.value)
    raise KeyError(f'{name} not found in {path}')


def dict_literal(tree, name):
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
                isinstance(t, ast.Name) and t.id == name for t in node.targets):
            out = {}
            for key, value in zip(node.value.keys, node.value.values):
                if key is None:  # a ** expansion of another summary
                    out.update(dict_literal(tree, value.id))
                else:
                    out[ast.literal_eval(key)] = ast.literal_eval(value)
            return out
    raise KeyError(name)


def main(root):
    root = Path(root).resolve()
    report = {'root': str(root), 'failures': [], 'modules': {}, 'constants': [],
              'protected': {}, 'scanner_pins': {}}
    for version in ('v1', 'v2'):
        rel = f'src/data_sheets_schema/native_controller_sources_{version}.json'
        data = json.loads((root / rel).read_text(encoding='utf-8'))
        commit = data['source_commit']
        for name, entry in data['modules'].items():
            live = sha((root / entry['path']).read_bytes())
            at_commit = sha(subprocess.run(
                ['git', '-C', str(root), 'show', f'{commit}:{entry["path"]}'],
                check=True, capture_output=True).stdout)
            row = {'path': entry['path'], 'pinned': entry['sha256'],
                   'working': live, 'at_source_commit': at_commit,
                   'source_commit': commit}
            report['modules'][f'{version}:{name}'] = row
            if not (entry['sha256'] == live == at_commit):
                report['failures'].append(f'{version}:{name} pin/working/commit differ')
    for rel, name, target in PIN_CONSTANTS:
        pinned = constant(root / rel, name)
        actual = sha((root / target).read_bytes())
        report['constants'].append({'file': rel, 'constant': name, 'pinned': pinned,
                                    'target': target, 'actual': actual})
        if pinned != actual:
            report['failures'].append(f'{rel}:{name} does not pin {target}')
    control_test = root / 'tests/test_native_shared_permission_protocol.py'
    control_sha = constant(control_test, 'CONTROL_SHA')
    control_actual = sha((root / 'notes/matched_cborg_2026-09-13/native_controls/native_control.py').read_bytes())
    report['control_sha'] = {'pinned': control_sha, 'actual': control_actual}
    if control_sha != control_actual:
        report['failures'].append('CONTROL_SHA does not pin native_control.py')
    for rel, prefix in PROTECTED.items():
        actual = sha((root / rel).read_bytes())
        report['protected'][rel] = actual
        if not actual.startswith(prefix):
            report['failures'].append(f'protected file moved: {rel}')
    tree = ast.parse((root / SCAN).read_text(encoding='utf-8'))
    for summary in ('_NATIVE_V2_RENDER_SOURCES', '_NATIVE_V2_INTEGRATED_RENDER_SOURCES'):
        for rel, pinned in dict_literal(tree, summary).items():
            actual = sha((root / rel).read_bytes())
            if actual != pinned:
                report['scanner_pins'].setdefault(summary, {})[rel] = {
                    'pinned': pinned, 'actual': actual}
    json.dump(report, sys.stdout, indent=1, sort_keys=True)
    print()
    return 1 if report['failures'] else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else '.'))
