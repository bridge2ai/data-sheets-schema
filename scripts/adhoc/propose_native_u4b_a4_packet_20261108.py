#!/usr/bin/env python3
"""Propose D114 as a revision of the frozen U1 API packet, 2026-11-08.

Inputs: current protected API bytes, immutable packet metadata and saved owner
bundle postimage. Outputs: new scratch diffs/metadata only. Never edits the
protected source, packet files or sidecar; never imports/executes API code.
"""
import ast
import difflib
import hashlib
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EXEC = ROOT.parent
TARGET = 'src/data_sheets_schema/api_runner.py'
OUT = EXEC / 'scratch-native-u4b/a4-packet-proposal'
OWNER_PACKET = EXEC / 'scratch-native-u1u3/owner-packets/postimages/api_runner.py'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def patch(old, new):
    return ''.join(difflib.unified_diff(old.decode().splitlines(keepends=True),
        new.decode().splitlines(keepends=True), fromfile='a/' + TARGET, tofile='b/' + TARGET)).encode()


def prepare(original, packet, metadata):
    if sha(original) != metadata['preimage_sha256'] or sha(packet) != metadata['postimage_sha256']:
        raise ValueError('protected source or current packet postimage differs from frozen metadata')
    old = b'            self._agentic_toolchain = toolchain()\n'
    new = b'            self._agentic_toolchain = toolchain(native_shared=self.native_shared_generation_version == 1)\n'
    if packet.count(old) != 1:
        raise ValueError('current packet no longer has exactly one known toolchain call')
    proposed = packet.replace(old, new)
    old_tree, new_tree = ast.parse(packet), ast.parse(proposed)
    calls = [node for node in ast.walk(old_tree) if isinstance(node, ast.Assign)
             and any(isinstance(target, ast.Attribute) and target.attr == '_agentic_toolchain'
                     for target in node.targets)
             and isinstance(node.value, ast.Call) and isinstance(node.value.func, ast.Name)
             and node.value.func.id == 'toolchain']
    if len(calls) != 1 or calls[0].value.args or calls[0].value.keywords:
        raise ValueError('old toolchain AST is ambiguous')
    calls[0].value = ast.parse('toolchain(native_shared=self.native_shared_generation_version == 1)', mode='eval').body
    if ast.dump(old_tree, include_attributes=False) != ast.dump(new_tree, include_attributes=False):
        raise ValueError('proposal changes more than the selected toolchain call')
    return proposed


def main():
    if os.path.lexists(EXEC / 'plans/native_quiet_window.lock'):
        raise RuntimeError('quiet window active; no packet preparation')
    metadata_path = ROOT / 'scripts/adhoc/native_u1_packets/api_runner_companion.json'
    metadata_raw = metadata_path.read_bytes()
    original = (ROOT / TARGET).read_bytes()
    packet = OWNER_PACKET.read_bytes()
    proposed = prepare(original, packet, json.loads(metadata_raw))
    OUT.mkdir(mode=0o700)
    delta, combined = patch(packet, proposed), patch(original, proposed)
    (OUT / 'api_runner_packet_delta.diff').write_bytes(delta)
    (OUT / 'api_runner_companion_with_d114.diff').write_bytes(combined)
    result = {'status': 'proposal_only_not_applied', 'target': TARGET,
        'frozen_metadata': {'path': str(metadata_path), 'sha256': sha(metadata_raw)},
        'current_packet_postimage': {'path': str(OWNER_PACKET), 'sha256': sha(packet)},
        'protected_preimage_sha256': sha(original), 'proposed_postimage_sha256': sha(proposed),
        'packet_delta_sha256': sha(delta), 'combined_proposal_sha256': sha(combined),
        'syntax_and_single_ast_call_change_verified': True,
        'selection': 'native_shared_generation_version == 1; zero retains historical toolchain',
        'resource_rule': 'selected generation playbooks + their two schemas + agents explicitly referenced by those playbooks; provenance-guard and validator only',
        'approval_required': 'revision of the api_runner.py owner packet; no installation or registration readiness claimed',
        'integration_remaining': 'recompute/check D76 sidecar bindings and full frozen four-packet composition after owner approval; existing packet bytes unchanged'}
    (OUT / 'proposal.json').write_text(json.dumps(result, indent=2, sort_keys=True) + '\n')
    if (ROOT / TARGET).read_bytes() != original or OWNER_PACKET.read_bytes() != packet:
        raise RuntimeError('protected or current packet bytes changed while preparing proposal')
    print(json.dumps(result, sort_keys=True))


if __name__ == '__main__':
    main()
