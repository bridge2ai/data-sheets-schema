"""Merge the lead's final candidate and apply only authorized pins, 2026-11-15.

Inputs: local accepted manifest branch and candidate f5c7c312f for PR 5968.
Outputs: merge provenance, scanner pin ledger, and saved exact source diffs in
the assigned sibling scratch directory. No fetch, push or live execution.
"""
import argparse
import ast
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
BEFORE = 'd6d26bf8c492d4b9dabfb1169760756425e0fa81'
CANDIDATE = 'f5c7c312f41e555c8023b880eeb3da327aa815cb'
SCRATCH = ROOT.parent / 'scratch-native-manifest-integration-20261114/continuation'
OUT = SCRATCH / 'final-merge-20261115'
SCAN = '.claude/skills/d4d-generation-specificity-audit/scan.py'
AUTHORITY = 'src/data_sheets_schema/native_execution_authority_v2.py'
MANIFEST = 'src/data_sheets_schema/native_environment_manifest.py'


def git(*args, check=True):
    return subprocess.run(['git', '--no-replace-objects', *args], cwd=ROOT,
                          capture_output=True, check=check)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def save(path, value):
    with path.open('x') as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write('\n')


def start():
    assert git('rev-parse', 'HEAD').stdout.decode().strip() == BEFORE
    assert git('branch', '--show-current').stdout.decode().strip() == 'codex/native-manifest-integration-20261114'
    own = str(Path(__file__).relative_to(ROOT))
    assert git('status', '--porcelain').stdout.decode().splitlines() == ['?? ' + own]
    OUT.mkdir()
    result = git('merge', '--no-commit', '--no-ff', CANDIDATE, check=False)
    (OUT / 'merge.stdout').write_bytes(result.stdout)
    (OUT / 'merge.stderr').write_bytes(result.stderr)
    unmerged = git('ls-files', '-u').stdout.decode().splitlines()
    stages = []
    for line in unmerged:
        meta, relative = line.split('\t', 1)
        stage = meta.split()[-1]
        raw = git('show', ':' + stage + ':' + relative).stdout
        target = OUT / 'conflicts' / (relative + '.stage-' + stage)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)
        stages.append({'path': relative, 'stage': stage, 'sha256': sha(raw), 'saved': str(target)})
    data = {'before': BEFORE, 'candidate': CANDIDATE, 'returncode': result.returncode,
            'conflicts': sorted({line.split('\t', 1)[1] for line in unmerged}), 'stages': stages}
    save(OUT / 'merge-start.json', data)
    print(json.dumps(data, indent=2))
    assert result.returncode == 0 or result.returncode == 1 and unmerged


def definitions(raw):
    tree = ast.parse(raw)
    return tree, {node.targets[0].id: node.value for node in tree.body
                  if isinstance(node, ast.Assign) and len(node.targets) == 1
                  and isinstance(node.targets[0], ast.Name) and isinstance(node.value, ast.Dict)}


def pins():
    assert not git('ls-files', '-u').stdout
    path = ROOT / SCAN
    original = path.read_text()
    old_tree, old_maps = definitions(original)
    current = sha((ROOT / AUTHORITY).read_bytes())
    historical = sha(git('show', CANDIDATE + ':' + AUTHORITY).stdout)
    manifest = sha((ROOT / MANIFEST).read_bytes())
    assert current == 'f865fea7736d4c1531742ab5081bfa19b1c43ba123f3d233dc4816d7d5d2b79e'
    assert historical == '00b0f717bc0398b905cfcb81de47c4434f70c2909bbbffb0b92789dbf867047c'
    assert manifest == '72003fcee74562ce8f4a17eda49218830d44a74aebbee3c27b0b33fe987655e6'
    start = original.index('_NATIVE_V2_INTEGRATED_RENDER_SOURCES = {')
    end = original.index('    # The reviewed #5966', start)
    replacement = """_NATIVE_V2_INTEGRATED_RENDER_SOURCES = {
    **_NATIVE_V2_RENDER_SOURCES,
    # Lead-authorized split, 2026-11-15: restore the historical integrated
    # v2 authority (00b0f717). The v3 import-path restoration has its own
    # explicit entry below; each route keeps one complete source identity.
""" + f"    '{AUTHORITY}': '{historical}',\n"
    updated = original[:start] + replacement + original[end:]
    anchor = '_NATIVE_V3_RENDER_SOURCES = {\n    **_NATIVE_V2_INTEGRATED_RENDER_SOURCES,\n'
    assert updated.count(anchor) == 1
    updated = updated.replace(anchor, anchor +
        '    # Lead-authorized split, 2026-11-15: v3 retains f865fea7, whose\n'
        '    # verified loader restores caller import roots before the census.\n'
        '    # This override prevents the historical v2 pin changing v3 authority.\n' +
        f"    '{AUTHORITY}': '{current}',\n", 1)
    old_manifest = '13d4d45e0bd375608d3b8c4808af6ea51cb6489d1053e0415fa799e443f46e7c'
    line = f"    '{MANIFEST}': '{old_manifest}',\n"
    assert updated.count(line) == 1
    updated = updated.replace(line,
        '    # Lead-authorized rotation, 2026-11-15: bind the full/light modes,\n'
        '    # process-local full verification reuse, and RECORD/size live checks.\n' +
        f"    '{MANIFEST}': '{manifest}',\n", 1)
    new_tree, new_maps = definitions(updated)
    allowed = {'_NATIVE_V2_INTEGRATED_RENDER_SOURCES': {AUTHORITY},
               '_NATIVE_V3_RENDER_SOURCES': {AUTHORITY, MANIFEST}}
    # Remove only the three authorized literal entries from both ASTs. All
    # remaining executable scanner syntax must remain exactly unchanged.
    for maps in (old_maps, new_maps):
        for name, paths in allowed.items():
            node = maps[name]
            pairs = [(key, value) for key, value in zip(node.keys, node.values)
                     if not isinstance(key, ast.Constant) or key.value not in paths]
            node.keys = [key for key, _ in pairs]
            node.values = [value for _, value in pairs]
    assert ast.dump(old_tree, include_attributes=False) == ast.dump(new_tree, include_attributes=False)
    path.write_text(updated)
    (OUT / 'scanner-before-pins.py').write_text(original)
    save(OUT / 'pin-changes.json', [
        {'entry': '_NATIVE_V2_INTEGRATED_RENDER_SOURCES', 'path': AUTHORITY,
         'old': current, 'new': historical, 'reason': 'separate historical integrated v2 authority'},
        {'entry': '_NATIVE_V3_RENDER_SOURCES', 'path': AUTHORITY,
         'old': 'inherited ' + current, 'new': current, 'reason': 'explicit current v3 import-path-restoring authority'},
        {'entry': '_NATIVE_V3_RENDER_SOURCES', 'path': MANIFEST,
         'old': old_manifest, 'new': manifest, 'reason': 'accepted explicit full/light manifest implementation'},
    ])
    print(json.dumps({'scanner_sha256': sha(path.read_bytes()), 'manifest': manifest,
                      'historical_authority': historical, 'v3_authority': current,
                      'other_scanner_ast_unchanged': True}, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('start', 'pins'))
    args = parser.parse_args()
    {'start': start, 'pins': pins}[args.action]()
