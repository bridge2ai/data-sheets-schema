#!/usr/bin/env python3
"""Add native selection to current receipt policy without replacing API gates.

D95 U3-D, 2026-11-07. Inputs: current HEAD plus fixed donor's two native-only
functions. Output: receipt_completion_policy.py; stdout records its digest.
Current API registration/floor code stays in place. Refuses edited targets.
"""
import ast
import hashlib
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
REL = 'src/data_sheets_schema/receipt_completion_policy.py'
DONOR = '0d5bddbc03b02cfa3efdea312c10aca002f6d85c'
ENV = {'PATH': '/usr/bin:/bin', 'GIT_NO_LAZY_FETCH': '1',
       'GIT_CONFIG_GLOBAL': '/dev/null', 'GIT_CONFIG_SYSTEM': '/dev/null'}


def git(*args):
    return subprocess.check_output(['/usr/bin/git', '--no-replace-objects', *args],
        cwd=ROOT, env=ENV, timeout=30)


def main():
    if git('branch', '--show-current').decode().strip() != 'codex/native-u3d-integration-20261107':
        raise SystemExit('wrong branch')
    path = ROOT / REL
    raw = path.read_bytes()
    if raw != git('show', 'HEAD:' + REL):
        raise SystemExit('target already edited')
    donor = git('show', DONOR + ':' + REL).decode()
    nodes = {node.name: ast.get_source_segment(donor, node) for node in ast.parse(donor).body
             if isinstance(node, ast.FunctionDef)}
    text = raw.decode()
    def change(old, new):
        nonlocal text
        if text.count(old) != 1:
            raise RuntimeError('current adapter anchor is not unique: ' + old)
        text = text.replace(old, new, 1)
    change('BLOCK_KEY = "receipt_completion_policy"',
           'BLOCK_KEY = "receipt_completion_policy"\nNATIVE_SPEC_KEYS = {"native_shared_generation_version", "native_shared_generation_descriptor",\n'
           '                    "native_shared_generation_registration", "native_shared_generation_context",\n'
           '                    "native_shared_receipt_policy"}')
    change('format_name = json.loads(raw, object_pairs_hook=_pairs, parse_constant=_invalid_constant).get("format")',
           'parsed = json.loads(raw, object_pairs_hook=_pairs, parse_constant=_invalid_constant)\n        format_name = parsed.get("format")')
    change('    version = {FORMAT: 1, "receipt_completion_registration_v2": 2, "receipt_completion_registration_v3": 3}.get(format_name)',
           '''    if parsed.get("kind") == "d4d_native_shared_receipt_policy":
        from .native_shared_contract import parse_receipt_policy
        from .native_shared_selection import RECEIPT_POLICY_SHA256
        if len(raw) > 2_000_000 or hashlib.sha256(raw).hexdigest() != value["sha256"]:
            raise ValueError("native receipt policy bytes differ from their bound or SHA256")
        return parse_receipt_policy(raw, RECEIPT_POLICY_SHA256)
    version = {FORMAT: 1, "receipt_completion_registration_v2": 2, "receipt_completion_registration_v3": 3}.get(format_name)''')
    new = nodes['_native_selection'].replace("'receipt_completion_version', 'removal_repair_version'):",
        "'receipt_completion_version', 'removal_repair_version', 'bounded_carry_version'):")
    change('def _selection(spec):', new + '\n\n\n' + nodes['native_render_declaration'] + '\n\n\ndef _selection(spec):')
    change('    if not SPEC_KEYS.intersection(spec):', '''    if 'native_shared_generation_version' in spec and type(spec['native_shared_generation_version']) is not int:
        raise ValueError('native receipt axis must be an integer')
    if (spec.get('native_shared_generation_version', 0) != 0
            or (NATIVE_SPEC_KEYS - {'native_shared_generation_version'}).intersection(spec)):
        return _native_selection(spec)
    if not SPEC_KEYS.intersection(spec):''')
    change('if registration["format"] !=', 'if registration.get("format") !=')
    change('            selected = recorded', '''            if render_spec is not None and any(key in recorded_spec or key in render_spec
                    for key in NATIVE_SPEC_KEYS - {'native_shared_generation_version'}):
                if any(render_spec.get(key) != recorded_spec.get(key) for key in NATIVE_SPEC_KEYS):
                    raise ValueError('supplied native receipt selection differs from the record declaration')
            selected = recorded''')
    ast.parse(text)
    path.write_text(text)
    if path.read_text() != text:
        raise RuntimeError('written adapter differs')
    print(REL, hashlib.sha256(path.read_bytes()).hexdigest())


if __name__ == '__main__':
    main()
