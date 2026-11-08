#!/usr/bin/env python3
"""Split D registration/execution from pinned round-six source, 2026-11-07.

Inputs: local Git objects at 9687dea18; outputs: the assigned D source modules.
Serves native U3-D round 8. No imports of project code or network operations.
Run once before tests; this intentionally does not manufacture C's interface.
"""
import ast
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
BASE = '9687dea189faa92cba1b30bdb0c6ee2f476ec747'
PACKAGE = ROOT / 'src/data_sheets_schema'
ENV = {'PATH': '/usr/bin:/bin', 'GIT_NO_LAZY_FETCH': '1',
       'GIT_ALLOW_PROTOCOL': '', 'GIT_CONFIG_GLOBAL': '/dev/null',
       'GIT_CONFIG_SYSTEM': '/dev/null'}


def source(name):
    return subprocess.check_output(['git', '--no-replace-objects', 'show',
        BASE + ':src/data_sheets_schema/' + name + '.py'], cwd=ROOT, env=ENV,
        timeout=30).decode()


def functions(raw):
    return {node.name: ast.get_source_segment(raw, node) for node in ast.parse(raw).body
            if isinstance(node, (ast.FunctionDef, ast.ClassDef))}


def change(raw, before, after, count=1):
    assert raw.count(before) == count, (before, raw.count(before))
    return raw.replace(before, after)


def write(name, raw):
    ast.parse(raw)
    (PACKAGE / (name + '.py')).write_text(raw)


def main():
    assert not os.path.lexists(ROOT.parent / 'plans/native_quiet_window.lock')
    assert subprocess.check_output(['git', 'branch', '--show-current'], cwd=ROOT,
        env=ENV).decode().strip() == 'codex/native-u3d-integration-20261107'
    for name in ('native_execution_orchestration', 'native_shared_execution_orchestration',
                 'native_shared_registration_orchestration'):
        assert not (PACKAGE / (name + '.py')).exists(), name

    engine = source('native_execution_engine')
    constants = engine[engine.index('GATES = '):engine.index('@dataclass')]
    write('native_execution_engine', '''"""Input-only execution identities shared by D consumers and orchestration.

Admission, actuation, signal handling and saved authority verification live in
native_execution_orchestration. No consumer imports that orchestration module.
"""
''' + constants)
    engine = change(engine, 'Private single-attempt lifetime for the explicit shared v2 route.',
        'Orchestration for the explicit shared v2 route; never an A3 consumer.')
    engine = change(engine, constants,
        'from .native_execution_engine import GATES, UNASSESSED\n\n\n')
    engine = change(engine, "'native_shared_registration', 'native_shared_controller',",
        "'native_shared_registration_orchestration', 'native_shared_controller',")
    engine = change(engine, "'native_shared_results', 'native_shared_results'),",
        "'native_shared_results_orchestration', 'native_shared_results_orchestration'),")
    engine = change(engine, 'prepared = gates.capture(value, controls,',
        'prepared = replay.capture(value, controls,')
    write('native_execution_orchestration', engine)

    execution = source('native_shared_execution')
    execution = change(execution, 'Explicit one-use native26 execution through the fixed common lifetime.',
        'Public orchestration for one-use native26 execution; not a consumer.')
    execution = change(execution, 'from . import native_shared_registration as registration',
        'from . import native_shared_registration_orchestration as registration')
    execution = change(execution, 'from . import native_shared_results as results',
        'from . import native_shared_results_orchestration as results')
    execution = change(execution, 'from .native_execution_engine import ',
        'from .native_execution_orchestration import ', count=4)
    write('native_shared_execution_orchestration', execution)
    write('native_shared_execution', '''"""Pure implementation census for D's execution consumer.

Public launch/readback moved to native_shared_execution_orchestration. No
backward import wrapper is provided: that would reintroduce verifier authority
into A3's consumer graph. This census grants no dispatch capability.
"""
from . import native_shared_contract as c
from .native_execution_engine import GATES, UNASSESSED

KIND = c.KINDS['attempt']
VERSION = 1


def require_gate_implementations():
    from .native_gate_engine import check
    from .native_shared_schema_gates import check_schemas, check_pair
    from .native_shared_receipts import schema_snapshot, _catalog_context
    from .native_subscription_guard import load_guard, validate_saved_observations
    if not all(callable(item) for item in (check, check_schemas, check_pair,
            schema_snapshot, _catalog_context, load_guard, validate_saved_observations)):
        raise ValueError('native shared execution gate implementation is incomplete')
''')

    raw = source('native_shared_registration')
    funcs = functions(raw)
    header = '''"""Input-only D reconstruction from verified preparation and explicit C inputs.

Proposal/envelope verification belongs to native_shared_registration_orchestration.
The fixed A entry keeps its exact signature and refuses the unresolved explicit
projection handoff; it never borrows ambient modules or invents C authority.
"""
from __future__ import annotations
from pathlib import Path
import re
import sys

from . import native_shared_contract as c
from . import native_shared_controller as composition
from . import native_shared_policy as policy
from . import native_shared_controls as pure_controls
from .native_shared_runtime_values import validate_runtime, POLICY_ENV, FLAGS
from .native_shared_evidence import read_regular
from .native_execution_engine import GATES

ROOT = Path(__file__).resolve().parents[2]
AUTHORITY_VERSION = 2
KIND = 'd4d_native_shared_execution_registration_v2'
VERSION = 2
EXECUTION = 'requires_exact_independent_review_ci_permission_and_owner_launch_evidence'
'''
    kept = []
    for name in ('environment', 'command', '_read', '_selection', '_production_sources',
                 'permission_expectation', '_paths'):
        fn = funcs[name].replace('authority.ROOT', 'ROOT')
        if name == 'command':
            fn = change(fn, ', attempt_id, controls):', ', attempt_id):')
            fn = change(fn, "    return [runtime['executable']['path']",
                "    from .native_shared_permissions import _permission_protocol\n    protocol = _permission_protocol()\n    return [runtime['executable']['path']")
            fn = change(fn, "controls['native_command_policy'].permission_arguments(selected['policy'])",
                "protocol.permission_arguments(selected['policy'])")
        kept.append(fn)
    body = funcs['_registration_body']
    body = change(body, 'max_draft_checks, receipt_origin_version=0):',
        'max_draft_checks, preparation_raw, controls, controller_sources, receipt_origin_version=0):')
    body = change(body, '    if type(receipt_origin_version)',
        '    pure_controls.require_controls(controls)\n    if type(receipt_origin_version)')
    start = body.index("    preparation_raw = selected['preparation_raw_json']")
    end = body.index("    if dependencies != preparation['dependencies']", start)
    body = body[:start] + '''    if selected['preparation_raw_json'].encode('utf-8') != preparation_raw:
        raise ValueError('composition differs from caller-verified preparation bytes')
    preparation = composition.captured_preparation_body(preparation_raw)
    dependencies = preparation['dependencies']
''' + body[end:]
    body = change(body, 'checked = verify_saved_probe(probe, expected=expected)',
        'checked = verify_saved_probe(probe, expected=expected, controls=controls,\n        controller_sources=controller_sources)')
    body = change(body, '''    with authority.loaded_dependencies(dependencies) as controls:
        argv = command(runtime, selected, effective, attempt_id, controls)''',
        '    argv = command(runtime, selected, effective, attempt_id)')
    body = change(body, 'list(execution_v2.EXECUTION_GATES)', 'list(GATES)')
    body = change(body, '''            or c.canonical(dependencies) != c.canonical(authority.dependency_identity())
            or preparation != execution_v2.verify_preparer(preparation_raw, job_id=preparation['job_id'])):''',
        "            or preparation != composition.captured_preparation_body(preparation_raw)):")
    body = change(body, '    return value',
        '    pure_controls.require_controls(controls)\n    return value')
    kept.append(body)
    kept.append('''def _require_integrated_gate_implementation():
    try:
        from .native_shared_execution import require_gate_implementations
        require_gate_implementations()
    except (ImportError, AttributeError) as exc:
        raise ValueError('native shared execution gate implementation is incomplete') from exc''')
    rebuild = funcs['rebuild_v2_body']
    begin = rebuild.index('    _require_integrated_gate_implementation()')
    rebuild = rebuild[:begin] + '''    # A has verified preparation_raw before this fixed entry, but supplies no
    # live C classifier projection. Never deserialize a carrier, consult hidden
    # process state or weaken permission reconstruction to manufacture one.
    raise ValueError('fixed A3 rebuild has no explicit C classifier projection handoff')
'''
    rebuild = rebuild.replace('A\'s source guard still refuses that graph before loading this implementation.',
        'The explicit C classifier handoff remains an unmet integration requirement.')
    kept += [rebuild, funcs['execution_paths_v2']]
    write('native_shared_registration', header + '\n\n\n' + '\n\n\n'.join(kept) + '\n')

    wrapper = '''"""D proposal and verification orchestration, outside A's consumer graph.

Only this layer obtains fresh verifier identities and a live C projection.
No authority is placed in serialized preparation or hidden process state.
"""
from . import native_execution_authority_v2 as authority
from . import native_execution_registration_v2 as execution_v2
from . import native_shared_contract as c
from . import native_shared_controller as composition
from . import native_shared_registration as consumer
from . import native_shared_permission_orchestration as permission_inputs
from .native_shared_registration import (
    AUTHORITY_VERSION, KIND, VERSION, EXECUTION, environment, command,
    permission_expectation, execution_paths_v2, _paths,
)


def _registration_body(composition_path, system_path, **kwargs):
    raw = consumer._read(composition_path, 'composition', c.HARD_LIMITS['request_bytes'])
    selected, _, _ = composition.reconstruct_composition(raw)
    preparation_raw = selected['preparation_raw_json'].encode('utf-8')
    job_id = composition.captured_preparation_body(preparation_raw)['job_id']
    prepared = execution_v2.verify_preparer(preparation_raw, job_id=job_id)
    dependencies = authority.dependency_identity()
    if prepared['dependencies'] != dependencies or selected['dependencies'] != dependencies:
        raise ValueError('execution preparation differs from current v2 authority')
    consumer._require_integrated_gate_implementation()
    with permission_inputs.loaded_permission_inputs() as (controls, controller_sources):
        value = consumer._registration_body(composition_path, system_path,
            preparation_raw=preparation_raw, controls=controls,
            controller_sources=controller_sources, **kwargs)
    if (authority.dependency_identity() != dependencies
            or execution_v2.verify_preparer(preparation_raw, job_id=job_id) != prepared):
        raise ValueError('execution authority changed during capture')
    return value
'''
    verified_body = funcs['verified_v2_body'].replace('list(execution_v2.EXECUTION_GATES)', 'list(consumer.GATES)')
    verified_body = change(verified_body,
        'expected = rebuild_v2_body(preparation_raw=preparation_raw,',
        'expected = _registration_body(')
    wrapper += '\n\n' + funcs['registration'] + '\n\n' + verified_body + '\n\n' + funcs['verified'] + '\n'
    write('native_shared_registration_orchestration', wrapper)

    # Public D tests use the new real orchestration entry, preserving assertions.
    for filename in ('test_native_shared_registration.py', 'test_native_shared_execution.py',
                     'test_native_shared_execution_failure.py', 'test_native_shared_live_capture.py',
                     'test_native_execution_engine.py'):
        path = ROOT / 'tests' / filename
        text = path.read_text()
        text = text.replace('import native_shared_registration as ',
            'import native_shared_registration_orchestration as ')
        text = text.replace('import native_shared_execution as ',
            'import native_shared_execution_orchestration as ')
        text = text.replace('import native_execution_engine as ',
            'import native_execution_orchestration as ')
        path.write_text(text)


if __name__ == '__main__':
    main()
