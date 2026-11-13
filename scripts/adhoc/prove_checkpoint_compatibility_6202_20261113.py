#!/usr/bin/env python3
"""Issue 6202 reviewed pure-definition compatibility proof, 2026-11-13.

Inputs: accepted fc00ce654 Git source and current source; no imports/execution.
Output: exact-byte hashes for every definition/constant executed by the audit.
This script does not modify the compatibility allowlist or controller pins.
"""
import argparse
import ast
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
PREFIX = 'notes/matched_cborg_2026-09-13/'
AUDIT = PREFIX + 'audit_controls/checkpoint_eligibility.py'
BASE = 'fc00ce654'


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def git_source(path):
    return subprocess.check_output(['git', 'show', BASE + ':' + path], cwd=ROOT)


def segment(raw, node):
    # Include decorator lines and original whitespace, not normalized AST text.
    lines = raw.splitlines(keepends=True)
    start = min([node.lineno] + [d.lineno for d in getattr(node, 'decorator_list', ())])
    return b''.join(lines[start - 1:node.end_lineno])


def selected(raw, names):
    result = {}
    for node in ast.parse(raw).body:
        if isinstance(node, ast.FunctionDef) and node.name in names:
            assert node.name not in result
            result[node.name] = segment(raw, node)
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id in names:
                    assert target.id not in result
                    result[target.id] = segment(raw, node)
    assert set(result) == set(names), (set(result), names)
    return result


def prove():
    old_audit, new_audit = git_source(AUDIT), (ROOT / AUDIT).read_bytes()
    old_exec = selected(old_audit, {'_pure_source_functions'})
    new_exec = selected(new_audit, {'_pure_source_functions'})
    assert old_exec == new_exec, 'audit extractor changed: review required'
    tree = ast.parse(new_exec['_pure_source_functions'])
    function = tree.body[0]
    assignments = {n.targets[0].id: n.value for n in function.body
        if isinstance(n, ast.Assign) and isinstance(n.targets[0], ast.Name)}
    chosen = ast.literal_eval(assignments['chosen'])
    # The extractor adds exactly this optional control_contract and constant.
    chosen['native_controls/native_control.py'] |= {'control_contract', 'CONTRACT', 'INIT_ID', 'HISTORY_CONTRACT'}
    supported = next(n.value for n in ast.parse(old_audit).body if isinstance(n, ast.Assign)
                     and any(isinstance(t, ast.Name) and t.id == 'SUPPORTED_SOURCES' for t in n.targets))
    allowed = {ast.literal_eval(k): ast.literal_eval(v.args[0]) for k, v in zip(supported.keys, supported.values)}
    records = []
    for relative, names in chosen.items():
        path = PREFIX + relative
        before, after = git_source(path), (ROOT / path).read_bytes()
        assert digest(before) in allowed[relative], (path, 'baseline not accepted')
        old, new = selected(before, names), selected(after, names)
        assert old == new, (path, 'executed definitions differ')
        records.append({'path': path, 'accepted_source_sha256': digest(before),
            'candidate_source_sha256': digest(after), 'byte_identical': True,
            'definitions': {name: {'bytes': len(raw), 'sha256': digest(raw)} for name, raw in sorted(old.items())}})
    return {'issue': 6202, 'baseline': BASE, 'audit_extractor_sha256': digest(new_exec['_pure_source_functions']),
            'scope': 'every extracted executable definition and source constant; exact bytes including whitespace',
            'sources': records}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = prove()
    with args.output.open('x') as stream:
        json.dump(result, stream, indent=2)
        stream.write('\n')
    print(json.dumps(result, indent=2))
