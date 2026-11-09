#!/usr/bin/env python3
"""Propose the A4/D114 runtime-bound producer hook, 2026-11-08 (#4354).

Inputs: one pinned committed producer and its unchanged worktree bytes.
Outputs: a fresh scratch producer.diff and proposal.json, never source edits.
The synthetic tests establish the proposed selection logic only. Genuine
producer, reconstruction, replay and D76 validation remain future work.
"""
from __future__ import annotations

import ast
import difflib
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess

ROOT = Path(__file__).resolve().parents[2]
EXEC = ROOT.parent
TARGET = 'src/data_sheets_schema/native_execution_registration_v2.py'
BASE = 'e8a41e78d80400d460e67ab583b050063dbf70d8'
PREIMAGE_BLOB = '180fb0ce38482c62a768ee17257b3e218b6dfb7f'
PREIMAGE_SHA256 = '5cfbe505286b46ffcd5482d71dfe05509942a17da178357805c67f5fb1ad8173'
OUT = EXEC / 'scratch-native-u4b/a4-producer-proposal'
MAX_SOURCE_BYTES = 1_000_000
ENV = {'PATH': '/usr/bin:/bin:/usr/sbin:/sbin', 'GIT_NO_LAZY_FETCH': '1',
       'GIT_ALLOW_PROTOCOL': '', 'GIT_CONFIG_GLOBAL': '/dev/null',
       'GIT_CONFIG_SYSTEM': '/dev/null', 'GIT_OPTIONAL_LOCKS': '0',
       'GIT_TERMINAL_PROMPT': '0'}
ANCHOR = b'    spec._native_shared_runtime_capture = runtime_capture\n'
INSERTION = b'''    # D114 is an explicit U4b successor; historical shared-native stays literal.
    basis = runtime['limits_basis']
    if basis.lstrip().startswith('{'):
        declared = c.strict_json(basis.encode('utf-8'), 'runtime profile basis', 16384)
        if type(declared) is dict and declared.get('kind') == 'd4d_native_u4b_runtime_basis':
            from .agentic_runtime import toolchain
            spec._agentic_toolchain = toolchain(native_shared=True)
'''

FUTURE_TEST_PLAN = (
    'Genuine prepare plus verify_preparer with a valid U4b runtime: bind the exact '
    'seven-resource toolchain before first instruction, without native or provider calls.',
    'Historical shared-v1 text, unrelated JSON and near-match kind: retain the '
    'original instruction, roster and constructor enumeration count.',
    'Malformed, duplicate-key and over-16384-byte object basis: strict refusal '
    'before instruction rendering, with no historical fallback.',
    'Genuine captured composition and D reconstruction accept matching historical '
    'and U4b rosters and refuse their interchange; no verifier replacements.',
    'Both recorded render_specs replay byte-exactly after live runtime changes '
    'and with live toolchain lookup prohibited.',
    'D76 input mutation still refuses; never reset the construction binding, '
    'replay origin or cached instruction to install this hook.',
    'verify_preparer refuses altered recorded toolchain or changed live runtime; '
    'regenerate preparation and registration against the new source identity.',
)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _dump(node):
    return ast.dump(node, include_attributes=False)


def _statement(text):
    return ast.parse(text).body[0]


def verify_single_insertion(original, proposed):
    """Compare whole modules after inserting only the known producer block."""
    before, after = ast.parse(original), ast.parse(proposed)
    functions = [node for node in before.body
                 if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
                 and node.name == 'prepare']
    if len(functions) != 1 or type(functions[0]) is not ast.FunctionDef:
        raise ValueError('producer requires exactly one ordinary top-level prepare')
    function = functions[0]
    target = _dump(_statement(ANCHOR.decode().strip()))
    positions = [index for index, node in enumerate(function.body) if _dump(node) == target]
    if len(positions) != 1:
        raise ValueError('producer runtime binding is missing or ambiguous')
    index = positions[0]
    required = (
        (-1, '_require_registered_input_spellings(spec)'),
        (1, 'spec._native_shared_max_draft_checks = max_draft_checks'),
        (2, 'instruction = spec.instruction'),
    )
    for offset, expression in required:
        position = index + offset
        if (position < 0 or position >= len(function.body)
                or _dump(function.body[position]) != _dump(_statement(expression))):
            raise ValueError('producer guard, capture and first-instruction order changed')
    insertion = ast.parse(b'def _proposal():\n' + INSERTION).body[0].body
    function.body[index + 1:index + 1] = insertion
    if _dump(before) != _dump(after):
        raise ValueError('proposal changes more than the sole runtime-bound insertion')


def prepare(original, *, expected_sha256=PREIMAGE_SHA256):
    """Build bytes only; callers must separately verify the committed preimage."""
    if (type(original) is not bytes or not original or len(original) > MAX_SOURCE_BYTES
            or sha(original) != expected_sha256):
        raise ValueError('producer preimage differs from the selected bounded bytes')
    if original.count(ANCHOR) != 1:
        raise ValueError('producer requires exactly one literal runtime binding')
    proposed = original.replace(ANCHOR, ANCHOR + INSERTION, 1)
    verify_single_insertion(original, proposed)
    return proposed


def patch(original, proposed):
    return ''.join(difflib.unified_diff(
        original.decode('utf-8').splitlines(keepends=True),
        proposed.decode('utf-8').splitlines(keepends=True),
        fromfile='a/' + TARGET, tofile='b/' + TARGET)).encode('utf-8')


def _git(*args):
    return subprocess.check_output(['/usr/bin/git', '--no-replace-objects',
                                   '-c', 'core.fsmonitor=false', '-c', 'core.hooksPath=/dev/null',
                                   '-c', 'protocol.allow=never', *args],
                                   cwd=ROOT, env=ENV, timeout=60)


def committed_preimage():
    listed = _git('ls-tree', '-l', BASE, '--', TARGET).decode('utf-8').strip()
    metadata, path = listed.split('\t')
    mode, kind, blob, size = metadata.split()
    if (path != TARGET or mode != '100644' or kind != 'blob'
            or blob != PREIMAGE_BLOB or not 0 < int(size) <= MAX_SOURCE_BYTES):
        raise ValueError('committed producer inventory differs from the pinned preimage')
    raw = _git('cat-file', 'blob', blob)
    if len(raw) != int(size) or sha(raw) != PREIMAGE_SHA256:
        raise ValueError('committed producer bytes differ from the pinned preimage')
    return raw


def _read_source():
    path = ROOT / TARGET
    if path.resolve() != path or not stat.S_ISREG(path.lstat().st_mode):
        raise ValueError('producer source must be its ordinary physical file')
    with path.open('rb') as stream:
        raw = stream.read(MAX_SOURCE_BYTES + 1)
    if not raw or len(raw) > MAX_SOURCE_BYTES:
        raise ValueError('producer source exceeds the nonempty byte bound')
    return raw


def main():
    if os.path.lexists(EXEC / 'plans/native_quiet_window.lock'):
        raise RuntimeError('quiet window active; no proposal preparation')
    if ROOT.resolve() != ROOT or OUT.resolve() != OUT or os.path.lexists(OUT):
        raise ValueError('proposal requires its fresh physical assigned scratch directory')
    if not OUT.parent.is_dir():
        raise ValueError('assigned scratch parent must already exist')
    original = committed_preimage()
    if _read_source() != original:
        raise ValueError('worktree producer differs from the committed preimage')
    proposed = prepare(original)
    delta = patch(original, proposed)
    result = {
        'status': 'scratch_proposal_only_not_applied_or_integration_validated',
        'target': TARGET, 'preimage_commit': BASE, 'preimage_git_blob': PREIMAGE_BLOB,
        'generator_head': _git('rev-parse', 'HEAD').decode('ascii').strip(),
        'generator': {'path': str(Path(__file__).resolve()),
                      'sha256': sha(Path(__file__).read_bytes())},
        'preimage_sha256': sha(original), 'postimage_sha256': sha(proposed),
        'diff_sha256': sha(delta),
        'bytes': {'preimage': len(original), 'postimage': len(proposed), 'diff': len(delta)},
        'syntax_and_sole_ast_insertion_verified': True,
        'selection': 'Exact runtime limits_basis.kind d4d_native_u4b_runtime_basis; '
                     'same strict 16384-byte JSON parse as native_shared_registration.',
        'binding_order': ['D76 entry guard', 'captured runtime', 'conditional U4b toolchain',
                          'draft-check allowance', 'first instruction'],
        'historical_behavior': 'No reassignment or second enumeration for other basis kinds; '
                               'replay continues using recorded runtime and toolchain.',
        'untouched': ['production source', 'api_runner.py constructor', 'frozen U1 packets',
                      'protected files', 'D76 binding and replay origins', 'existing evidence'],
        'review_scope': 'Synthetic fragment tests do not establish genuine producer, '
                        'registration, replay, protected-packet composition or native acceptance.',
        'future_test_plan': list(FUTURE_TEST_PLAN),
        'application': 'Requires separate authorization and all genuine integration tests; '
                       'this generator neither imports the producer nor applies its diff.',
    }
    encoded = (json.dumps(result, indent=2, sort_keys=True) + '\n').encode('utf-8')
    if _read_source() != original:
        raise RuntimeError('producer source changed while preparing proposal')
    OUT.mkdir(mode=0o700)
    for name, raw in (('producer.diff', delta), ('proposal.json', encoded)):
        with (OUT / name).open('xb') as stream:
            stream.write(raw)
        if (OUT / name).read_bytes() != raw:
            raise RuntimeError('proposal output readback differs')
    if _read_source() != original:
        raise RuntimeError('producer source changed while retaining proposal')
    print(json.dumps(result, sort_keys=True))


if __name__ == '__main__':
    main()
