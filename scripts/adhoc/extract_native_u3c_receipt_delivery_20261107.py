#!/usr/bin/env python3
"""Extract/adapt only U3-C receipt delivery, 2026-11-07, owner D95.

Input: exact local controller donor. Output: a NEW receipt delivery fragment
in the assigned worktree. U3-B alone supplies the catalog owner section at
merge; this script does not copy or implement it. Remove donor memoized raw
inputs and receipt-completion results, preserving every fresh validation.
"""
from __future__ import annotations

import ast
import hashlib
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DONOR = '0d5bddbc03b02cfa3efdea312c10aca002f6d85c'
PATH = 'src/data_sheets_schema/native_shared_receipts.py'
NAMES = {'ReceiptResult', 'omission_assets', 'output_ceiling', 'policy', 'floor',
         '_inputs', '_raw_inputs', 'check_initial', 'prepare', '_prepare',
         'complete', '_complete', 'check_final', '_check_final', '_DEFAULT_CHECK_FINAL'}
ENV = {'PATH': '/usr/bin:/bin:/usr/sbin:/sbin', 'LC_ALL': 'C',
       'GIT_CONFIG_GLOBAL': '/dev/null', 'GIT_CONFIG_SYSTEM': '/dev/null',
       'GIT_NO_LAZY_FETCH': '1'}

FRESH_INPUTS = '''def _raw_inputs(selection, full_raw, receipt_raw, *, _catalogs=None):
    """Validate each occurrence; only U3-B's schema catalog may be reused."""
    chosen = selection.document()['inputs']
    bounds = selection.bounds()
    for raw in (full_raw, receipt_raw):
        if type(raw) is not bytes:
            raise ValueError('native initial inputs require captured bytes')
        if len(raw) > min(bounds['max_input_bytes'], contract.HARD_LIMITS['original_full_bytes']):
            raise ValueError('phase-1 input exceeds the supplied native byte bound')
    bundle = selection.raw(chosen['bundle']['path'])
    manifest_raw = selection.raw(chosen['chunk_manifest']['path'])
    context_raw = selection.raw(chosen['context']['path'])
    snapshot = schema_snapshot(selection)
    bases, catalog = _catalog_context(_catalogs).schema_data(selection, snapshot)
    full = omissions._mapping(full_raw, 'sealed native full')
    receipt = omissions._mapping(receipt_raw, 'sealed native receipt')
    manifest = omissions._mapping(manifest_raw, 'captured chunks')
    validate_manifest_mapping(manifest, bundle, manifest.get('bundle'))
    md5 = hashlib.md5(bundle).hexdigest()
    if receipt.get('bundle_md5') != md5:
        raise ValueError('native original receipt differs from captured bundle')
    texts = dict(zip((row['id'] for row in manifest['chunks']),
                     chunk_texts(bundle.decode('utf-8'), manifest['chunks'])))
    if len(receipts.populated_leaves(full)) > bounds['max_populated_paths']:
        raise ValueError('complete native populated inventory exceeds the global bound')
    context = omissions._mapping(context_raw, 'scope context', json_only=True)
    owners = omissions._owners(full, catalog, context['vocabulary'])
    scopes = [row['owner'] for row in context['scopes']]
    if scopes.count('') != 1 or len(set(scopes)) != len(scopes) or any(p not in owners for p in scopes):
        raise ValueError('native scope must name distinct existing full-record owners and root once')
    return full, receipt, manifest, texts, md5, bases, catalog, owners
'''


def main():
    branch = subprocess.check_output(['git', 'branch', '--show-current'], cwd=ROOT, env=ENV).decode().strip()
    if branch != 'codex/native-u3c-controller-20261107':
        raise SystemExit('only the assigned U3-C branch may receive this fragment')
    target = ROOT / PATH
    if target.exists() or target.is_symlink():
        raise SystemExit('refusing existing receipt file; preserve the owner context')
    raw = subprocess.check_output(['git', '--no-replace-objects', 'show', DONOR + ':' + PATH],
                                  cwd=ROOT, env=ENV, timeout=30)
    text = raw.decode('utf-8')
    lines = text.splitlines(keepends=True)
    fragments, found = [], set()
    for node in ast.parse(text).body:
        name = getattr(node, 'name', None)
        if isinstance(node, ast.Assign) and len(node.targets) == 1:
            name = getattr(node.targets[0], 'id', None)
        if name not in NAMES:
            continue
        found.add(name)
        first = min([node.lineno] + [d.lineno for d in getattr(node, 'decorator_list', [])])
        fragment = ''.join(lines[first - 1:node.end_lineno])
        if name == '_raw_inputs':
            fragment = FRESH_INPUTS
        if name == '_complete':
            start = fragment.index('    ctx, token, prep_key =')
            end = fragment.index('    request = _prepare(')
            fragment = fragment[:start] + fragment[end:]
            start = fragment.index('    if complete_key is None ')
            end = fragment.index("    listed = request['requested_paths']")
            fragment = fragment[:start] + fragment[end:]
            start = fragment.index('    if complete_key is not None ')
            end = fragment.index('    return built', start)
            fragment = fragment[:start] + fragment[end:]
        fragments.append(fragment.rstrip())
    if found != NAMES:
        raise RuntimeError('donor receipt roster changed: ' + repr(NAMES - found))
    header = '''"""U3-C receipt delivery; U3-B supplies the owner context at integration.

This fragment intentionally does not define the owner-context functions.
It must be combined with the committed U3-B section before stage validation.
"""
from __future__ import annotations

# BEGIN U3-C RECEIPT DELIVERY
from dataclasses import dataclass
import hashlib

import yaml

from . import audit_omissions as omissions, receipts
from . import native_shared_contract as contract
from .chunking import chunk_texts, validate_manifest_mapping
from .receipt_completion_policy import coverage_counts

'''
    output = (header + '\n\n\n'.join(fragments) + '\n# END U3-C RECEIPT DELIVERY\n').encode()
    ast.parse(output)
    with target.open('xb') as stream:
        stream.write(output)
    if target.read_bytes() != output:
        raise RuntimeError('receipt fragment write differs')
    print('donor=' + DONOR + ' donor_sha256=' + hashlib.sha256(raw).hexdigest())
    print('output=' + PATH + ' sha256=' + hashlib.sha256(output).hexdigest())


if __name__ == '__main__':
    main()
