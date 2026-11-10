#!/usr/bin/env python3
"""Freeze the exact retained U3-F review mutations for U3-L, 2026-11-09.

Input: SHA-pinned retained review script (parsed, never executed).
Output: fresh committed tests/fixtures/native_u3l_review_cases.json.
No source mutation, tests, provider, network, or native executable.
"""
import ast
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT.parent / 'scratch-u3f-review/scripts/run_fixtures_f2.py'
SOURCE_SHA = 'bb16457c501ceb9638ab344bccb548a9e721ca61924c5cc327b439ab83aabf40'
OUT = ROOT / 'tests/fixtures/native_u3l_review_cases.json'
OUTCOMES = {
    'F0': (1, 9),
    'F1_event_parser_token': (2, None),
    'F2a_envelope_control_token': (2, None),
    'F2b_v2_envelope_token': (2, None),
    'F2c_v2_envelope_branch': (2, None),
    'F3a_stage_branch': (2, None),
    'F3a2_stage_branch_no_options': (1, 10),
    'F3b_stage_options_subscript': (2, None),
    'F3c_stage_main_branch': (1, 12),
    'F3d_module_helper_print': (1, 9),
    'B1_typed_alias_restored': (2, None),
    'B2_typed_container_alias_token': (1, 9),
    'B3_typed_container_direct_token': (1, 10),
}


def main():
    if (ROOT.parent / 'plans/native_quiet_window.lock').exists():
        raise RuntimeError('quiet-window lock is active')
    raw = SOURCE.read_bytes()
    if hashlib.sha256(raw).hexdigest() != SOURCE_SHA:
        raise RuntimeError('retained fixture script changed')
    tree = ast.parse(raw)
    values = {}
    for statement in tree.body:
        if (isinstance(statement, ast.Assign) and len(statement.targets) == 1
                and isinstance(statement.targets[0], ast.Name)
                and statement.targets[0].id in {'HINT_MODULE', 'FIXTURES'}):
            name = statement.targets[0].id
            if name in values:
                raise RuntimeError('duplicate retained assignment')
            expression = statement.value
            if name == 'FIXTURES':
                class LiteralHint(ast.NodeTransformer):
                    def visit_Name(self, node):
                        if node.id != 'HINT_MODULE' or type(values.get('HINT_MODULE')) is not str:
                            raise ValueError('unrecognized retained fixture expression')
                        return ast.Constant(value=values['HINT_MODULE'])
                expression = LiteralHint().visit(expression)
            values[name] = ast.literal_eval(expression)
    cases = []
    for name, (code, violations) in OUTCOMES.items():
        edits = values['FIXTURES'][name]
        for relative, before, after in edits:
            if (Path(relative).is_absolute() or '..' in Path(relative).parts
                    or before is not None and type(before) is not str or type(after) is not str):
                raise RuntimeError('unsupported retained mutation')
        cases.append(dict(name=name, edits=edits, expected_exit=code,
            expected_violations=violations,
            known_gap={'F3d_module_helper_print': 'N1',
                       'B2_typed_container_alias_token': '#5657'}.get(name)))
    value = dict(kind='native_u3l_retained_review_fixtures', version=1,
                 source=str(SOURCE), source_sha256=SOURCE_SHA, cases=cases)
    encoded = (json.dumps(value, indent=2, ensure_ascii=False) + '\n').encode()
    with OUT.open('xb') as stream:
        stream.write(encoded)
    if OUT.read_bytes() != encoded:
        raise RuntimeError('fixture output did not persist exactly')
    print(json.dumps(dict(path=str(OUT), sha256=hashlib.sha256(encoded).hexdigest(),
                          bytes=len(encoded), cases=len(cases))))


if __name__ == '__main__':
    main()
