"""PR 5968 field-by-field envelope review evidence, 2026-11-16.

Inputs: frozen v2 and current v3 source. Output: JSON comparison, source hashes,
and parser bodies. No source is imported and no pins are changed.
"""
import ast
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def source(relative):
    path = ROOT / relative
    raw = path.read_bytes()
    tree = ast.parse(raw)
    return raw, tree


def literal(tree, name):
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(isinstance(target, ast.Name) and
                target.id == name for target in node.targets):
            return ast.literal_eval(node.value)
    raise ValueError(name)


def main():
    v2 = 'notes/matched_cborg_2026-09-13/prepare_registration_v2.py'
    v3 = 'src/data_sheets_schema/native_shared_authority_wire.py'
    controller = 'src/data_sheets_schema/native_attribution_controller_v2.py'
    rows = {}
    for relative in (v2, v3):
        raw, tree = source(relative)
        function = next(node for node in tree.body if isinstance(node, ast.FunctionDef)
                        and node.name == 'require_envelope')
        rows[relative] = {'sha256': hashlib.sha256(raw).hexdigest(),
                          'function': ast.get_source_segment(raw.decode(), function)}
    _, frozen = source(controller)
    _, current = source(v3)
    assert literal(frozen, 'SOURCES_SHA256') == literal(current, 'CONTROLLER_SOURCES_SHA256')
    result = {
        'conclusion': 'v3 is at least as strict for v3 envelopes',
        'controller_digest_equal': True,
        'comparison': {
            'outer_mapping': 'v2 accepts dict subclasses; v3 requires exact dict',
            'outer_fields': 'same exact authority_version, controller_sources_sha256, registration set',
            'authority_version': 'both require exact int equal to 2, rejecting bool',
            'controller_digest': 'both require the same frozen controller digest',
            'registration_mapping': 'v2 accepts dict subclasses; v3 requires exact dict',
            'schema_version': 'both require exact int; v3 requires 3 instead of historical 2',
            'kind': 'v2 has no restriction; v3 requires current preparation or execution kind',
            'body_other_fields': 'neither envelope helper validates the remaining body shape',
        },
        'sources': rows,
    }
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
