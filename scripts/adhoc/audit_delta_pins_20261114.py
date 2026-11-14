"""Audit issue 6236-6240 source hashes and pin references, 2026-11-14.
Inputs: base commit and working tree, including ignored files. Output: JSON stdout.
Read-only; never rotates pins or edits scanner tables.
"""
import hashlib
import json
from pathlib import Path
import subprocess
import ast
from verify_controller_pin_rotation_20261113 import dict_literal, constant

BASE = '4f9ce93e4'
def git(*args):
    return subprocess.check_output(['git', *args])
def sha(raw):
    return hashlib.sha256(raw).hexdigest()

paths = git('diff', '--name-only', BASE, '--', 'src').decode().splitlines()
rows = []
for name in paths:
    old = sha(git('show', BASE + ':' + name))
    search = subprocess.run(['rg', '--hidden', '--no-ignore', '-l', '-F', old,
                             '--glob', '!.git', '.'], capture_output=True, text=True)
    if search.returncode not in (0, 1):
        raise RuntimeError(search.stderr)
    rows.append({'path': name, 'base_sha256': old,
                 'sha256': sha(Path(name).read_bytes()),
                 'old_hash_references_including_ignored': search.stdout.splitlines()})
scanner = Path('.claude/skills/d4d-generation-specificity-audit/scan.py')
tree = ast.parse(scanner.read_text())
scanner_rows = []
for summary in ('_NATIVE_V2_RENDER_SOURCES', '_NATIVE_V2_INTEGRATED_RENDER_SOURCES'):
    for name, pin in dict_literal(tree, summary).items():
        old = sha(git('show', BASE + ':' + name))
        current = sha(Path(name).read_bytes())
        if old != pin or current != pin:
            scanner_rows.append({'summary': summary, 'path': name, 'pinned': pin,
                                 'base': old, 'current': current, 'moved_here': old != current})
profiles = Path('src/data_sheets_schema/native_runtime_profiles.py')
synthetic = constant(profiles, 'SYNTHETIC_PEER_SHA256')
peer = Path('tests/fixtures/native_shared_execution/fake_cli.py')
peers = [str(peer)] if sha(peer.read_bytes()) == synthetic else []
print(json.dumps({'base': git('rev-parse', BASE).decode().strip(), 'sources': rows,
                  'scanner_mismatches': scanner_rows,
                  'synthetic_peer_pin': synthetic, 'matching_peers': peers}, indent=2))
