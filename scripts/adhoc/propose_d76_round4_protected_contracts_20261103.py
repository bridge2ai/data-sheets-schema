#!/usr/bin/env python3
"""PR #5213 round four: propose exact protected-helper contracts, without admission.

2026-11-03. Inputs: a reviewed contract-proposal JSON and its source tree.
Output: a fresh external JSON with per-function byte pins and the whole protected
shared_generation module pin. Never edits source or enables an inventory waiver.
"""
import argparse
import ast
import hashlib
import json
from pathlib import Path


SHARED = 'src/data_sheets_schema/shared_generation.py'
LATCH = 'src/data_sheets_schema/latch_journal.py'
PROTECTED_IDENTITIES = {
    'data_sheets_schema.shared_generation.' + name for name in (
        'select', 'capture', 'identity', 'assert_current', 'preflight',
        'generation_context', 'require_generation_context', 'schema_context',
        'require_client', 'plan', 'memo', 'source_raw', 'source_registry',
        'digest_text', 'marked_bundle', 'core_inventory', 'core_text',
        'source_chunks', 'routing_context', 'require_routing_context')
} | {'data_sheets_schema.latch_journal.refuse_legacy_execution'}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def regular(path):
    if path.is_symlink() or not path.is_file():
        raise ValueError('regular non-symlink input required: ' + str(path))
    return path.read_bytes()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--proposal', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    source = args.source.resolve(strict=True)
    output = args.output
    if (not output.is_absolute() or '..' in output.parts
            or output.exists() or output.is_symlink()
            or output.parent.resolve(strict=True) != output.parent
            or output.is_relative_to(source)):
        raise ValueError('fresh physical absolute output outside source required')
    proposal_raw = regular(args.proposal)
    proposal = json.loads(proposal_raw)
    rows = [row for row in proposal['candidates'] if row['protected_no_source_edit']]
    if len(rows) != len(PROTECTED_IDENTITIES) or {row['identity'] for row in rows} != PROTECTED_IDENTITIES:
        raise ValueError('proposal differs from the exact 21 reviewed protected identities')
    sources = {path: regular(source / path) for path in (SHARED, LATCH)}
    trees = {path: ast.parse(raw, filename=path) for path, raw in sources.items()}
    pinned = []
    for row in rows:
        path = row['path']
        if path not in sources:
            raise ValueError('unexpected protected source path')
        if proposal['candidate_source_sha256'][path] != sha(sources[path]):
            raise ValueError('proposal source changed: ' + path)
        name = row['identity'].rsplit('.', 1)[1]
        matches = [node for node in trees[path].body
                   if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name]
        if len(matches) != 1:
            raise ValueError('protected function must have one top-level source definition: ' + name)
        node = matches[0]
        start = min([node.lineno, *(item.lineno for item in node.decorator_list)])
        lines = sources[path].splitlines(keepends=True)
        raw = b''.join(lines[start - 1:node.end_lineno])
        if (row['proposed_mode'] != 'validated-caller'
                or not row['proposed_precondition'] or row['classification_pending']):
            raise ValueError('protected proposal lacks its reviewed caller precondition')
        pinned.append({
            'identity': row['identity'], 'source_path': path,
            'function_start_line': start, 'function_end_line': node.end_lineno,
            'function_bytes': len(raw), 'function_sha256': sha(raw),
            'pin_basis': 'Exact complete source lines from first decorator/def through end_lineno, including docstring and terminal newline.',
            'proposed_mode': row['proposed_mode'],
            'proposed_precondition': row['proposed_precondition'],
        })
    if sources != {path: regular(source / path) for path in sources}:
        raise ValueError('protected source changed during proposal')
    result = {
        'status': 'proposal only; not authorized or consulted by inventory checker',
        'source': str(source), 'proposal': str(args.proposal), 'proposal_sha256': sha(proposal_raw),
        'producer_sha256': sha(regular(Path(__file__))),
        'shared_generation_sha256': sha(sources[SHARED]),
        'source_sha256': {path: sha(raw) for path, raw in sources.items()},
        'contracts': sorted(pinned, key=lambda item: item['identity']),
        'limits': [
            'No protected source is edited and no checker acceptance is enabled.',
            'Any eventual exception must bind each exact function; no file-wide waiver is proposed.',
            'A new public protected function remains an unresolved inventory candidate.',
            'The latch function pin includes its docstring; unrelated latch documentation changes do not change that pin.',
        ],
    }
    raw = (json.dumps(result, indent=2, sort_keys=True) + '\n').encode()
    with output.open('xb') as stream:
        stream.write(raw)
    if regular(output) != raw:
        raise ValueError('persisted proposal differs')
    print(json.dumps({'output': str(output), 'sha256': sha(raw), 'contracts': len(pinned),
                      'checker_acceptance_enabled': False}, indent=2))


if __name__ == '__main__':
    main()
