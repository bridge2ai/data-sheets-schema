#!/usr/bin/env python3
"""Separate PR6302 pure replay from host diagnostics, 2026-11-21.

Inputs: exact diagnostic/producer source and their offline tests in this branch.
Outputs: host classes/entry moved to producer; pure validator keeps its API.
No native execution, evidence rewriting or authority-policy relaxation.
"""
import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DIAGNOSTIC = ROOT / 'src/data_sheets_schema/native_stage_root_diagnostic.py'
PRODUCER = ROOT / 'src/data_sheets_schema/native_permission_probe.py'


def main():
    raw = DIAGNOSTIC.read_text()
    lines = raw.splitlines(keepends=True)
    names = {'GrantCapture', '_BoundaryObserver', 'produce_boundary'}
    nodes = [node for node in ast.parse(raw).body if getattr(node, 'name', None) in names]
    if not nodes and names <= {getattr(node, 'name', None) for node in ast.parse(PRODUCER.read_text()).body}:
        DIAGNOSTIC.write_text(raw.rstrip() + '\n')
        PRODUCER.write_text(PRODUCER.read_text().rstrip() + '\n')
        return
    if {node.name for node in nodes} != names:
        raise ValueError('diagnostic split input differs')
    blocks = [''.join(lines[node.lineno - 1:node.end_lineno]) for node in nodes]
    removed = {number for node in nodes for number in range(node.lineno - 1, node.end_lineno)}
    pure = ''.join(line for number, line in enumerate(lines) if number not in removed)
    pure = pure.replace('from copy import deepcopy\n', '')
    pure = pure.replace('canonical, read_regular, sha, strict_json', 'canonical, sha, strict_json')
    host = PRODUCER.read_text()
    host = host.replace('from .native_stage_root_diagnostic import GrantCapture, require_fixture',
                        'from .native_stage_root_diagnostic import require_fixture')
    host = host.replace('    from .native_stage_root_diagnostic import produce_boundary\n', '')
    imports = ('from .native_stage_root_diagnostic import (\n'
               '    MARKER, FIXTURE, MARKER_PATHS, MARKER_BYTES, MAX_CAPTURE, SENTINEL_BYTES,\n'
               '    _pin, _has_marker, boundary_case, boundary_policy, validate_boundary_diagnostic,\n'
               ')\n')
    host = host.replace('from .native_path_identity import overlaps\n',
                        'from .native_path_identity import overlaps\n' + imports, 1)
    host += '\n\n' + '\n\n\n'.join(blocks) + '\n'
    ast.parse(pure)
    ast.parse(host)
    DIAGNOSTIC.write_text(pure.rstrip() + '\n')
    PRODUCER.write_text(host.rstrip() + '\n')
    for name in ('test_native_stage_root_diagnostic.py', 'test_native_stage_root_boundary.py'):
        path = ROOT / 'tests' / name
        text = path.read_text()
        text = text.replace('from data_sheets_schema import native_stage_root_diagnostic as diagnostic\n',
                            'from data_sheets_schema import native_stage_root_diagnostic as diagnostic\n'
                            'from data_sheets_schema import native_permission_probe as probe\n')
        text = text.replace('diagnostic.GrantCapture', 'probe.GrantCapture')
        text = text.replace('diagnostic._BoundaryObserver', 'probe._BoundaryObserver')
        text = text.replace("monkeypatch.setattr(diagnostic, 'MAX_CAPTURE', 1)",
                            "monkeypatch.setattr(probe, 'MAX_CAPTURE', 1)")
        ast.parse(text)
        path.write_text(text)


if __name__ == '__main__':
    main()
