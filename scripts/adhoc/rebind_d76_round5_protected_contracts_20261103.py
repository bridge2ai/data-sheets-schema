#!/usr/bin/env python3
"""PR #5213 round five: propose the approved protected-contract rebind.

2026-11-03. Inputs: merge-two source, the exact old sidecar and the lead ruling.
Output: one fresh external JSON for review; never modifies the sidecar, checker
or protected source. Retains 21 contracts and permits exactly three changed bodies.
"""
import argparse
import ast
import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess


SHARED = 'src/data_sheets_schema/shared_generation.py'
LATCH = 'src/data_sheets_schema/latch_journal.py'
SIDECAR = 'tests/utils/run_spec_boundary_contracts.json'
CHECKER = 'tests/utils/run_spec_boundaries.py'
MERGE = '5ee008a65f0f4abfb60cda8b13bdff91be6cbd18'
BASE_SIDECAR = '90c31790efb2d8e1068f910551da747bfaf3a495b1d037560331e42323750566'
BASE_SHARED = '8c799066df941dd80d65ffdc23eee225f875383e046bbc1f88656f9897d01e47'
TARGET_SHARED = '94b3cf6845827c8fdf7bf05cc6251e2fb196ceb91ea8ce377f2c9e3b8be3773d'
CHECKER_SHA = 'a379e93a0065dc927835b1417cabcb926e33eeb333416c768237bc50d2dc6237'
RULING_SHA = 'b12186255583dae0adf5dfc40cc68645f7c7aafb14138f49a42d10ef32212c59'
PREFIX = 'data_sheets_schema.shared_generation.'
LATCH_ID = 'data_sheets_schema.latch_journal.refuse_legacy_execution'
IDENTITIES = {PREFIX + name for name in (
    'select', 'capture', 'identity', 'assert_current', 'preflight',
    'generation_context', 'require_generation_context', 'schema_context',
    'require_client', 'plan', 'memo', 'source_raw', 'source_registry',
    'digest_text', 'marked_bundle', 'core_inventory', 'core_text',
    'source_chunks', 'routing_context', 'require_routing_context')} | {LATCH_ID}
CHANGED = {PREFIX + name for name in ('select', 'schema_context', 'plan')}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def regular(path):
    if path.is_symlink() or not path.is_file() or path.resolve(strict=True) != path:
        raise ValueError('physical regular input required: ' + str(path))
    return path.read_bytes()


def unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('duplicate JSON key: ' + key)
        result[key] = value
    return result


def git(source, *args):
    return subprocess.run(['git', '--no-replace-objects', '-c', 'protocol.allow=never',
                           '-C', str(source), *args], check=True,
                          env=dict(os.environ, GIT_NO_LAZY_FETCH='1'),
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE).stdout


def function_pin(raw, name, path):
    matches = [node for node in ast.parse(raw, filename=path).body
               if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
               and node.name == name]
    if len(matches) != 1:
        raise ValueError('one top-level function required: ' + name)
    node = matches[0]
    start = min([node.lineno, *(item.lineno for item in node.decorator_list)])
    body = b''.join(raw.splitlines(keepends=True)[start - 1:node.end_lineno])
    return {'function_start_line': start, 'function_end_line': node.end_lineno,
            'function_bytes': len(body), 'function_sha256': sha(body)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--ruling', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    source = args.source.resolve(strict=True)
    helper = Path(__file__).resolve(strict=True)
    if source != helper.parents[2]:
        raise ValueError('source must be the checkout containing this helper')
    output = args.output
    if (not output.is_absolute() or '..' in output.parts
            or output.exists() or output.is_symlink()
            or output.parent.resolve(strict=True) != output.parent
            or output.is_relative_to(source)):
        raise ValueError('fresh physical absolute output outside source required')
    paths = [source / name for name in (SHARED, LATCH, SIDECAR, CHECKER)]
    paths += [args.ruling, helper]
    snapshot = {path: regular(path) for path in paths}
    old_raw = snapshot[source / SIDECAR]
    sources = {name: snapshot[source / name] for name in (SHARED, LATCH)}
    if (sha(old_raw) != BASE_SIDECAR or sha(sources[SHARED]) != TARGET_SHARED
            or sha(snapshot[source / CHECKER]) != CHECKER_SHA
            or sha(snapshot[args.ruling]) != RULING_SHA):
        raise ValueError('baseline sidecar, target source, checker or ruling pin differs')
    producer_head = git(source, 'rev-parse', 'HEAD').decode().strip()
    git(source, 'merge-base', '--is-ancestor', MERGE, producer_head)
    if git(source, 'show', producer_head + ':' + str(helper.relative_to(source))) != snapshot[helper]:
        raise ValueError('the reviewed proposal producer must be committed unchanged')
    for name, raw in sources.items():
        if git(source, 'show', MERGE + ':' + name) != raw:
            raise ValueError('protected source differs from reviewed merge: ' + name)
    old = json.loads(old_raw, object_pairs_hook=unique)
    rows = old.get('contracts', [])
    if (old.get('schema_version') != 1 or old.get('approval', {}).get('authorized') is not True
            or old.get('shared_generation_sha256') != BASE_SHARED
            or len(rows) != 21 or {row['identity'] for row in rows} != IDENTITIES):
        raise ValueError('original approval or exact 21-identity roster differs')
    result = copy.deepcopy(old)
    changes = []
    for row in result['contracts']:
        identity = row['identity']
        path = LATCH if identity == LATCH_ID else SHARED
        if (row['source_path'] != path or row['proposed_mode'] != 'validated-caller'
                or not isinstance(row['proposed_precondition'], str)
                or not row['proposed_precondition'].strip()):
            raise ValueError('reviewed path/mode/precondition differs: ' + identity)
        before = {key: row[key] for key in (
            'function_start_line', 'function_end_line', 'function_bytes', 'function_sha256')}
        after = function_pin(sources[path], identity.rsplit('.', 1)[1], path)
        body_changed = before['function_sha256'] != after['function_sha256']
        if body_changed != (identity in CHANGED):
            raise ValueError('unexpected changed/unchanged function: ' + identity)
        if not body_changed and before['function_bytes'] != after['function_bytes']:
            raise ValueError('unchanged function byte length differs: ' + identity)
        row.update(after)
        changes.append({'identity': identity, 'body_changed': body_changed,
                        'before': before, 'after': after})
    # Original approval remains unchanged for the strict checker. Its complete
    # provenance is also preserved separately from the new current snapshot.
    historical = {key: copy.deepcopy(old[key]) for key in (
        'approval', 'proposal', 'proposal_sha256', 'producer_sha256', 'source', 'source_sha256')}
    historical['shared_generation_sha256'] = old['shared_generation_sha256']
    result['historical_provenance'] = {'round4': historical}
    result.pop('proposal')
    result.pop('proposal_sha256')
    result['source'] = str(source)
    result['producer_sha256'] = sha(snapshot[helper])
    current_hashes = {name: sha(raw) for name, raw in sources.items()}
    result['source_sha256'] = current_hashes
    result['shared_generation_sha256'] = TARGET_SHARED
    result['round5_rebind'] = {
        'authority': 'Lead ruling for the exact approved round-five variant',
        'ruling_path': str(args.ruling), 'ruling_sha256': RULING_SHA,
        'merge_commit': MERGE, 'baseline_sidecar_sha256': BASE_SIDECAR,
        'producer_commit': producer_head,
        'helper_path': str(helper.relative_to(source)), 'helper_sha256': sha(snapshot[helper]),
        'checker_sha256': CHECKER_SHA, 'current_module_sha256': current_hashes,
        'changed_function_identities': sorted(CHANGED), 'function_pin_updates': changes,
        'latch_hash_scope': 'The whole-module hash is snapshot metadata only. The exact '
                            'refuse_legacy_execution function pin remains unchanged.',
        'limits': 'Proposal only; writes no sidecar/checker/protected source. All 21 '
                  'identities and caller preconditions remain unchanged; no new exemption.',
    }
    raw = (json.dumps(result, indent=2, ensure_ascii=False) + '\n').encode()
    if snapshot != {path: regular(path) for path in paths}:
        raise ValueError('input changed during proposal')
    with output.open('xb') as stream:
        stream.write(raw)
    if regular(output) != raw or snapshot != {path: regular(path) for path in paths}:
        raise ValueError('persisted proposal or input changed')
    print(json.dumps({'proposal': str(output), 'sha256': sha(raw),
                      'contracts': 21, 'changed_function_hashes': 3,
                      'sidecar_modified': False}, indent=2))


if __name__ == '__main__':
    main()
