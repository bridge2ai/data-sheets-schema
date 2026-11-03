#!/usr/bin/env python3
# Purpose: prepare/check the atomic protected hooks + provenance repin for agy.
# Inputs: exact G1 source and reviewed transformer; outputs: external proposal
# packet, never a live protected-source edit. Integration tasks 5/6, 2026-11-03.
import argparse
import ast
import difflib
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
SOURCE = 'src/data_sheets_schema/shared_generation.py'
NOTE = 'notes/bc1_shared_generation_patch_2026-10-27'
BASE = '8c799066df941dd80d65ffdc23eee225f875383e046bbc1f88656f9897d01e47'
CANDIDATE = '94b3cf6845827c8fdf7bf05cc6251e2fb196ceb91ea8ce377f2c9e3b8be3773d'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def diff(path, before, after):
    return ''.join(difflib.unified_diff(before.decode().splitlines(True), after.decode().splitlines(True),
                   fromfile='a/' + path, tofile='b/' + path)).encode()


def generate(output):
    output.mkdir(parents=True, exist_ok=True)
    assert not any(output.iterdir()), 'refuse to overwrite an existing packet'
    base = (ROOT / SOURCE).read_bytes()
    assert sha(base) == BASE
    helper = ROOT / 'scripts/adhoc/prepare_wave7_bc1_shared_proposal_20261029.py'
    spec = importlib.util.spec_from_file_location('reviewed_hooks', helper)
    hooks = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(hooks)
    candidate = hooks.transform(base.decode()).encode()
    assert hooks.transform(candidate.decode(), remove=True).encode() == base
    assert sha(candidate) == CANDIDATE
    ast.parse(candidate)
    patch = diff(SOURCE, base, candidate)
    additions = sum(line.startswith('+') and not line.startswith('+++') for line in patch.decode().splitlines())
    deletions = sum(line.startswith('-') and not line.startswith('---') for line in patch.decode().splitlines())
    assert (additions, deletions) == (16, 1)
    note = json.loads((ROOT / (NOTE + '.json')).read_bytes())
    note.update(applied=True, base_sha256=BASE, proposed_source_sha256=CANDIDATE, proposal_sha256=sha(patch),
                scope='BC1 hooks on final D41/G1; main journal and canonical assets retained unchanged')
    note_raw = json.dumps(note, indent=2, sort_keys=True).encode() + b'\n'
    after = {SOURCE: candidate, NOTE + '.diff': patch, NOTE + '.json': note_raw}
    before = {name: (ROOT / name).read_bytes() for name in after}
    combined = b''.join(diff(name, before[name], raw) for name, raw in after.items())
    files = {'shared_generation.proposal.diff': patch, 'atomic-protected-and-repin.diff': combined,
             'bc1_shared_generation_patch_2026-10-27.json': note_raw,
             'bc1_shared_generation_patch_2026-10-27.diff': patch}
    for name, raw in files.items():
        (output / name).write_bytes(raw)
    packet = {'base': BASE, 'candidate': CANDIDATE, 'additions': additions, 'deletions': deletions,
              'transformer_sha256': sha(helper.read_bytes()),
              'before': {name: sha(raw) for name, raw in before.items()},
              'after': {name: sha(raw) for name, raw in after.items()},
              'artifacts': {name: sha(raw) for name, raw in files.items()}}
    packet_raw = json.dumps(packet, sort_keys=True, indent=2).encode() + b'\n'
    (output / 'packet.json').write_bytes(packet_raw)
    own = Path(__file__).read_bytes()
    (output / 'apply_packet.py').write_bytes(own)
    shell = f'''#!/bin/sh
# Apply reviewed hooks and repin together; inspect and commit all three files
# in ONE commit afterward. Inputs: checkout path; offline, no Git publication.
set -eu
packet_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
cd "$packet_dir"
printf '%s\\n' '{sha(packet_raw)}  packet.json' '{sha(own)}  apply_packet.py' | shasum -a 256 -c -
exec python3 -S -B "$packet_dir/apply_packet.py" apply "$1" --packet "$packet_dir"
'''
    (output / 'apply_protected.sh').write_text(shell)
    (output / 'apply_protected.sh').chmod(0o755)
    assert all((output / name).read_bytes() == raw for name, raw in files.items())
    print(json.dumps(packet, indent=2))


def apply(root, packet_dir):
    root, packet_dir = root.resolve(), packet_dir.resolve()
    packet = json.loads((packet_dir / 'packet.json').read_bytes())
    for name, expected in packet['artifacts'].items():
        assert sha((packet_dir / name).read_bytes()) == expected, ('artifact mismatch', name)
    for name, expected in packet['before'].items():
        assert sha((root / name).read_bytes()) == expected, ('base mismatch', name)
    patch = str(packet_dir / 'atomic-protected-and-repin.diff')
    subprocess.run(['git', 'apply', '--check', patch], cwd=root, check=True)
    # git apply without --reject checks every hunk before writing any file.
    subprocess.run(['git', 'apply', patch], cwd=root, check=True)
    for name, expected in packet['after'].items():
        assert sha((root / name).read_bytes()) == expected, ('result mismatch', name)
    print('Verified all three files. Commit hooks and both provenance files together.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=('generate', 'apply'))
    parser.add_argument('path', type=Path)
    parser.add_argument('--packet', type=Path)
    args = parser.parse_args()
    generate(args.path) if args.action == 'generate' else apply(args.path, args.packet)
