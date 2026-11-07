"""Real U3-D consumer census after the round-8 split, 2026-11-07.

AST checks cover direct and deferred imports in every original D consumer.
The unchanged A guard sees actual package bytes and its complete source pins;
no source/module/guard substitution or filtered dependency map is supplied.
Named current C refusals describe this checkpoint, not completed admission.
The separate positive integration requirement deliberately remains executable.
"""
import ast
import hashlib
from importlib.util import resolve_name
import json

import pytest

from data_sheets_schema import native_execution_authority_v2 as authority
from tests.test_native_execution_registration_v2 import isolated_modules  # noqa: F401


PACKAGE = 'data_sheets_schema.'
# D's ten original modules, each already in A's unchanged closed owned roster.
D_CONSUMERS = frozenset(PACKAGE + name for name in (
    'native_execution_engine', 'native_gate_engine', 'native_subscription_guard',
    'native_shared_execution', 'native_shared_gates', 'native_shared_permissions',
    'native_shared_publication', 'native_shared_registration',
    'native_shared_results', 'native_shared_schema_gates',
))
C_INDEPENDENT = frozenset(PACKAGE + name for name in (
    'native_execution_engine', 'native_subscription_guard', 'native_shared_schema_gates',
))
BOOTSTRAP_REFUSAL = (
    'consumer cannot import verifier bootstrap boundary: '
    'data_sheets_schema.native_execution_registration_v2'
)
CURRENT_C_REFUSALS = {
    PACKAGE + 'native_gate_engine': BOOTSTRAP_REFUSAL,
    PACKAGE + 'native_shared_execution': BOOTSTRAP_REFUSAL,
    PACKAGE + 'native_shared_gates': BOOTSTRAP_REFUSAL,
    PACKAGE + 'native_shared_publication': BOOTSTRAP_REFUSAL,
    PACKAGE + 'native_shared_registration': BOOTSTRAP_REFUSAL,
    PACKAGE + 'native_shared_results': BOOTSTRAP_REFUSAL,
    PACKAGE + 'native_shared_permissions': (
        'consumer package import has missing or ambiguous source: '
        'data_sheets_schema.native_shared_permission_protocol'
    ),
}
# These legacy adapters themselves import forbidden execution/attribution
# authority. D uses reviewed neutral primitives or outer orchestration instead.
LEGACY_ADAPTERS = frozenset(PACKAGE + name for name in (
    'native_execution_gates', 'native_supervisor_gates', 'native_attribution_results',
))


def _source(name, pins=None):
    relative = 'src/' + name.replace('.', '/') + '.py'
    path = authority.ROOT / relative
    raw = path.read_bytes()
    assert raw, relative
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


def test_census_roster_covers_each_original_d_consumer_in_unchanged_a_roster():
    assert len(D_CONSUMERS) == 10
    assert D_CONSUMERS <= authority.CONSUMER_OWNED_MODULES
    assert C_INDEPENDENT.isdisjoint(CURRENT_C_REFUSALS)
    assert C_INDEPENDENT | set(CURRENT_C_REFUSALS) == D_CONSUMERS


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


def test_actual_a_guard_accepts_independent_d_graphs_and_names_c_refusals(isolated_modules, record_property):
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
    for name in sorted(C_INDEPENDENT):
        assert outcomes[name]['status'] == 'accepted', (name, outcomes[name])
    for name, reason in sorted(CURRENT_C_REFUSALS.items()):
        assert outcomes[name] == {'status': 'refused', 'reason': reason}, (name, outcomes[name])


def test_real_c_dependent_registration_graph_must_be_accepted_for_integration(isolated_modules):
    """Unmarked requirement: still fails while genuine C edges are unresolved.

    Do not replace this assertion with acceptance of a refusal or a synthetic
    consumer. Once its graph is accepted, full reconstruction/admission still
    has separate requirements, including the explicit classifier handoff.
    """
    name = PACKAGE + 'native_shared_registration'
    pins = authority.dependency_identity()['base']['package_sources']
    graph = authority.refuse_legacy_consumer_imports(
        _source(name, pins), name=name, package_sources=pins)
    assert graph[name] == pins['src/data_sheets_schema/native_shared_registration.py']
