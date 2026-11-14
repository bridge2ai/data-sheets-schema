"""U3-D r8, 2026-11-07: extract gate/result/publication layers from pinned Git bytes.

Inputs: local commit 9687dea189faa92cba1b30bdb0c6ee2f476ec747; no imports of
production code. Outputs: the four assigned consumer adapters and three new
neutral/orchestration modules. Existing source donors remain unmodified.
Run once from this worktree; refuses drift and existing new outputs.
"""
from __future__ import annotations

import ast
from pathlib import Path
import subprocess

BASE = '9687dea189faa92cba1b30bdb0c6ee2f476ec747'
ROOT = Path(__file__).resolve().parents[2]
PACKAGE = 'src/data_sheets_schema/'


def source(name):
    return subprocess.run(['git', 'show', BASE + ':' + PACKAGE + name + '.py'],
        cwd=ROOT, check=True, stdout=subprocess.PIPE).stdout.decode()


def pieces(text):
    rows = text.splitlines(keepends=True)
    return {node.name: ''.join(rows[node.lineno - 1:node.end_lineno])
        for node in ast.parse(text).body if isinstance(node, (ast.FunctionDef, ast.ClassDef))}


def remove(text, names):
    rows = text.splitlines(keepends=True)
    for node in reversed(ast.parse(text).body):
        if isinstance(node, (ast.FunctionDef, ast.ClassDef)) and node.name in names:
            del rows[node.lineno - 1:node.end_lineno]
    return ''.join(rows)


def main():
    assigned = ['native_gate_engine', 'native_shared_gates', 'native_shared_results',
                'native_shared_publication']
    new = ['native_shared_gate_primitives', 'native_shared_results_orchestration',
           'native_shared_publication_orchestration']
    original = {name: source(name) for name in assigned}
    for name, raw in original.items():
        if (ROOT / (PACKAGE + name + '.py')).read_text() != raw:
            raise SystemExit('assigned source differs from pinned base: ' + name)
    for name in new:
        if (ROOT / (PACKAGE + name + '.py')).exists():
            raise SystemExit('new output already exists: ' + name)

    draft = pieces(source('native_attribution_registration'))
    gates = pieces(source('native_execution_gates'))
    neutral = '''"""Neutral fixed completion checks, copied from the released native gates.

U3-D r8, 2026-11-07; source commit 9687dea189faa92cba1b30bdb0c6ee2f476ec747.
Only already-bound command maps and captured values are accepted. This module
does not load authority, reconstruct a launch, or import frozen execution code.
Parity with the unedited originals is tested independently.
"""
from __future__ import annotations
from copy import deepcopy
import hashlib
import json
import shlex

GATES = ('terminal', 'shutdown', 'first_stop', 'live_attribution', 'saved_attribution',
         'phase_history', 'tool_history', 'schema', 'pair', 'receipts', 'evidence',
         'observation', 'accounting', 'runtime_authority', 'keep_awake')
RUNTIME_OBSERVATION_BASIS = 'captured_runtime_observation_v1'
CLEANUP_BASIS = 'captured_native_cleanup_v1'
IOKIT_ASSERTIONS = ('PreventUserIdleSystemSleep', 'PreventDiskIdle', 'PreventSystemSleep')
DRAFT_MODULE = 'data_sheets_schema.source_attribution_preflight'

'''
    neutral += '\n\n'.join(draft[name] for name in ('_sha', '_json', '_encoded')) + '\n\n'
    command = draft['command_kind'].replace('expected=None', 'expected')
    command = command.replace('    expected = _commands(spec) if expected is None else expected\n',
        "    if type(expected) is not dict:\n        raise ValueError('helper command map must be explicit')\n")
    command = command.replace('policy.MODULE', 'DRAFT_MODULE')
    neutral += command + '\n\n'
    for name in ('tool_history', 'runtime_observation_result', '_released_assertions', 'cleanup_result'):
        neutral += gates[name].replace('draft.', '') + '\n\n'

    engine = original['native_gate_engine'].replace(
        'from data_sheets_schema import native_execution_gates as legacy',
        'from data_sheets_schema import native_shared_gate_primitives as neutral')
    engine = engine.replace('    draft = legacy.draft\n', '')
    engine = engine.replace('legacy.runtime_observation_result', 'neutral.runtime_observation_result')
    engine = engine.replace('legacy.cleanup_result', 'neutral.cleanup_result')
    engine = engine.replace('draft._encoded', 'neutral._encoded')
    engine = engine.replace('Legacy call-time module fault seams and ordinary result/error fields remain\nunchanged.',
        'Fixed neutral checks retain ordinary result/error fields.')
    shared = original['native_shared_gates'].replace(
        'from .native_execution_gates import GATES', 'from .native_shared_gate_primitives import GATES')
    shared = shared.replace('from .native_execution_gates import tool_history as settled_results',
        'from .native_shared_gate_primitives import tool_history as settled_results')
    shared = remove(shared, {'capture'})

    result_parts = pieces(original['native_shared_results'])
    retained = ('Snapshot', '_member', '_captured_selection', 'rebuild',
                'validate_file_basis', '_read_pool')
    result_consumer = '''"""Bounded captured reconstruction without verifier/bootstrap or frozen v1 imports.

Host capture, replay orchestration and publication live in the explicitly named
native_shared_results_orchestration module. Nothing here imports that layer.
"""
from __future__ import annotations
from dataclasses import replace
from pathlib import Path
from . import native_shared_contract as c
from . import native_shared_capture as capture_api
from . import native_shared_evidence as evidence
from . import native_shared_selection as selection_api

POOL_NAME = 'native-shared-capture.json'
REPORT_KIND = 'native_shared_saved_reconstruction'

'''
    result_consumer += '\n\n'.join(result_parts[name] for name in retained) + '\n'
    result_orchestration = remove(original['native_shared_results'], set(retained))
    result_orchestration = result_orchestration.replace(
        '"""Bounded native shared capture, byte-only reconstruction and saved readback.',
        '"""Host-side native capture, saved replay and publication orchestration.')
    result_orchestration = result_orchestration.replace(
        "POOL_NAME = 'native-shared-capture.json'\nREPORT_KIND = 'native_shared_saved_reconstruction'",
        'from .native_shared_results import (Snapshot, _member, _captured_selection, rebuild,\n'
        '    validate_file_basis, _read_pool, POOL_NAME, REPORT_KIND)')

    pub_parts = pieces(original['native_shared_publication'])
    publication = '''"""Input-only reconstruction of native stage publications.

Durable effects live in native_shared_publication_orchestration. There is no
consumer-to-orchestrator import or compatibility forwarding entry point.
"""
from __future__ import annotations
from pathlib import Path, PurePosixPath
import shlex
from . import native_shared_contract as c
from . import native_shared_stage as stage

'''
    publication += '\n\n'.join(pub_parts[name] for name in ('proposal_publications', '_physical_destination')) + '\n'
    publication_orchestration = remove(original['native_shared_publication'],
        {'proposal_publications', '_physical_destination'})
    publication_orchestration = publication_orchestration.replace(
        'from data_sheets_schema.native_shared_evidence import read_regular',
        'from data_sheets_schema.native_shared_evidence import read_regular\n'
        'from .native_shared_publication import proposal_publications, _physical_destination')

    outputs = {'native_shared_gate_primitives': neutral,
        'native_gate_engine': engine, 'native_shared_gates': shared,
        'native_shared_results': result_consumer,
        'native_shared_results_orchestration': result_orchestration,
        'native_shared_publication': publication,
        'native_shared_publication_orchestration': publication_orchestration}
    for name, raw in outputs.items():
        ast.parse(raw, filename=name + '.py')
    for name, raw in outputs.items():
        (ROOT / (PACKAGE + name + '.py')).write_text(raw)
    print('Wrote the seven bounded U3-D consumer/orchestration source files.')


if __name__ == '__main__':
    main()
