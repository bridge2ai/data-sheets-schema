"""Real U3-D consumer census after the round-9 integration, 2026-11-07.

AST checks cover direct and deferred imports in every D consumer.
The unchanged A guard sees actual package bytes and its complete source pins;
no source/module/guard substitution or filtered dependency map is supplied.
The complete C/D owned roster and each genuine D graph must now be accepted.
The separate positive integration requirement remains executable.
"""
import ast
import hashlib
from importlib.util import resolve_name
import json

import pytest

from data_sheets_schema import native_execution_authority_v2 as authority
from tests.test_native_execution_registration_v2 import isolated_modules  # noqa: F401


PACKAGE = 'data_sheets_schema.'
# D's ten originals, two neutral extractions, runtime profile and helper-cache routing.
D_CONSUMERS = frozenset(PACKAGE + name for name in (
    'native_execution_engine', 'native_gate_engine', 'native_subscription_guard',
    'native_shared_execution', 'native_shared_gates', 'native_shared_permissions',
    'native_shared_publication', 'native_shared_registration',
    'native_shared_results', 'native_shared_schema_gates',
    'native_shared_gate_primitives', 'native_shared_runtime_values',
    'native_runtime_profiles', 'native_helper_cache',
))
C_CONSUMERS = frozenset(PACKAGE + name for name in (
    'native_shared_attribution', 'native_shared_capture', 'native_shared_controller',
    'native_shared_authority_wire', 'native_shared_controls', 'native_shared_evidence',
    'native_shared_permission_protocol', 'native_shared_runtime_constants',
    'native_shared_current', 'native_shared_effects', 'native_shared_observations',
    'native_shared_phase', 'native_shared_policy', 'native_shared_receipts',
    'native_shared_stage', 'native_shared_streams',
))
# These legacy adapters themselves import forbidden execution/attribution
# authority. D uses reviewed neutral primitives or outer orchestration instead.
LEGACY_ADAPTERS = frozenset(PACKAGE + name for name in (
    'native_execution_gates', 'native_supervisor_gates', 'native_attribution_results',
))


def _source(name, pins=None):
    stem = 'src/' + name.replace('.', '/')
    candidates = [relative for relative in (stem + '.py', stem + '/__init__.py')
                  if (authority.ROOT / relative).is_file()]
    assert len(candidates) == 1, (name, candidates)
    relative = candidates[0]
    path = authority.ROOT / relative
    raw = path.read_bytes()
    assert raw or relative.endswith('/__init__.py'), relative
    if pins is not None:
        assert relative in pins, 'actual source must be in the unfiltered package closure'
        assert hashlib.sha256(raw).hexdigest() == pins[relative], relative
    return raw


def _imports(raw, name):
    """Resolve all static imports, including imports inside deferred functions."""
    imports = []
    for node in ast.walk(ast.parse(raw, filename=name)):
        if isinstance(node, ast.Import):
            imports.extend((alias.name, node.lineno) for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imported = node.module or ''
            if node.level:
                imported = resolve_name('.' * node.level + imported, name.rpartition('.')[0])
            imports.append((imported, node.lineno))
            # Cover `from package import module` and nested module imports.
            imports.extend((imported + '.' + alias.name, node.lineno)
                           for alias in node.names if alias.name != '*')
    return imports


def test_census_roster_covers_exactly_the_current_c_and_d_consumer_layers():
    assert len(D_CONSUMERS) == 14
    assert len(C_CONSUMERS) == 16
    assert C_CONSUMERS.isdisjoint(D_CONSUMERS)
    assert authority.CONSUMER_OWNED_MODULES == C_CONSUMERS | D_CONSUMERS


@pytest.mark.parametrize('name', sorted(D_CONSUMERS))
def test_d_consumer_has_no_direct_or_deferred_authority_or_orchestration_import(name):
    forbidden = (authority._LEGACY_CONSUMER_MODULES
                 | authority._TRUSTED_CONSUMER_BOUNDARIES | LEGACY_ADAPTERS)
    bad = []
    for imported, line in _imports(_source(name), name):
        boundary = any(imported == target or imported.startswith(target + '.')
                       for target in forbidden)
        orchestration = (imported.startswith(PACKAGE)
                         and any(part.endswith('_orchestration') for part in imported.split('.')))
        if boundary or orchestration:
            bad.append((line, imported))
    assert bad == [], {'consumer': name, 'forbidden_imports': bad}


def test_actual_a_guard_accepts_every_current_d_graph(isolated_modules, record_property):
    # This is A's real dependency capture, not a fixture package roster or a
    # source overlay. The isolation fixture only restores ordinary bare aliases.
    pins = authority.dependency_identity()['base']['package_sources']
    outcomes = {}
    for name in sorted(D_CONSUMERS):
        try:
            graph = authority.refuse_legacy_consumer_imports(
                _source(name, pins), name=name, package_sources=pins)
        except ValueError as exc:
            outcomes[name] = {'status': 'refused', 'reason': str(exc)}
        else:
            assert name in graph
            assert graph[name] == pins['src/' + name.replace('.', '/') + '.py']
            outcomes[name] = {'status': 'accepted', 'graph': graph}
    record_property('d_consumer_guard_census', json.dumps(outcomes, sort_keys=True))
    for name in sorted(D_CONSUMERS):
        assert outcomes[name]['status'] == 'accepted', (name, outcomes[name])


def test_real_c_dependent_registration_graph_must_be_accepted_for_integration(isolated_modules):
    """Unmarked requirement: genuine C-dependent reconstruction is admissible.

    Do not replace this assertion with acceptance of a refusal or a synthetic
    consumer. Once its graph is accepted, full reconstruction/admission still
    has separate requirements, including the explicit classifier handoff.
    """
    name = PACKAGE + 'native_shared_registration'
    pins = authority.dependency_identity()['base']['package_sources']
    graph = authority.refuse_legacy_consumer_imports(
        _source(name, pins), name=name, package_sources=pins)
    assert graph[name] == pins['src/data_sheets_schema/native_shared_registration.py']
