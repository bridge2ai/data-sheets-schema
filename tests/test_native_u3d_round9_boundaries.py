"""U3-D r9: complete boundary census and unmasked interface parity, 2026-11-07.

The census records every reachable static forbidden edge, independently of the
production guard's first-refusal control flow. Synthetic strings test only the
census algorithm; the integration census reads the actual pinned package tree.
"""
import ast
import hashlib
from importlib.util import resolve_name
import json

import pytest

from data_sheets_schema import native_execution_authority_v2 as authority
from tests.test_native_shared_consumer_census import D_CONSUMERS, LEGACY_ADAPTERS, _source
from tests.test_native_execution_registration_v2 import isolated_modules  # noqa: F401


PACKAGE = 'data_sheets_schema'


def test_all_29_actual_merged_consumers_pass_the_unmodified_guard(isolated_modules, record_property):
    pins = authority.dependency_identity()['base']['package_sources']
    roster = _source_roster(pins)
    outcomes, refused = {}, {}
    for name in sorted(authority.CONSUMER_OWNED_MODULES):
        raw = (authority.ROOT / roster[name]).read_bytes()
        assert hashlib.sha256(raw).hexdigest() == pins[roster[name]]
        try:
            outcomes[name] = authority.refuse_legacy_consumer_imports(raw, name=name, package_sources=pins)
        except ValueError as error:
            refused[name] = str(error)
    record_property('actual_merged_29_graphs', json.dumps({'accepted': outcomes, 'refused': refused}, sort_keys=True))
    assert len(authority.CONSUMER_OWNED_MODULES) == 29
    assert refused == {}
    assert set(outcomes) == set(authority.CONSUMER_OWNED_MODULES)


def _import_nodes(tree, *, owned):
    """Owned modules include deferred bodies; utility dependencies do not."""
    yield tree
    if owned or not isinstance(tree, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
        for child in ast.iter_child_nodes(tree):
            yield from _import_nodes(child, owned=owned)


def _all_forbidden_edges(root, *, sources, read_source, owned, canonical=lambda name: name):
    """Return the full static edge set, without stopping at the first refusal."""
    forbidden = (authority._LEGACY_CONSUMER_MODULES
                 | authority._TRUSTED_CONSUMER_BOUNDARIES | LEGACY_ADAPTERS)
    pending, visited, bad = [root], {}, set()
    while pending:
        module = pending.pop()
        if module in visited:
            continue
        assert module in sources, ('missing source', module)
        relative = sources[module]
        raw = read_source(module)
        visited[module] = hashlib.sha256(raw).hexdigest()
        package = module if relative.endswith('/__init__.py') else module.rpartition('.')[0]
        targets = []
        # Importing a nested module also executes its package initializers.
        parts = module.split('.')
        targets.extend(('.'.join(parts[:length]), 0) for length in range(2, len(parts)))
        for node in _import_nodes(ast.parse(raw, filename=relative), owned=module in owned):
            if isinstance(node, ast.Import):
                targets.extend((canonical(alias.name), node.lineno) for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                imported = node.module or ''
                if node.level:
                    imported = resolve_name('.' * node.level + imported, package)
                imported = canonical(imported)
                if imported == PACKAGE:
                    targets.extend((imported + '.' + alias.name, node.lineno)
                                   for alias in node.names)
                else:
                    targets.append((imported, node.lineno))
                    targets.extend((imported + '.' + alias.name, node.lineno)
                                   for alias in node.names
                                   if imported + '.' + alias.name in sources)
        for target, line in targets:
            target = canonical(target)
            boundary = any(target == item or target.startswith(item + '.') for item in forbidden)
            orchestration = (target.startswith(PACKAGE + '.')
                             and any(part.endswith('_orchestration') for part in target.split('.')))
            if boundary or orchestration or target == PACKAGE:
                bad.add((module, line, target))
            elif target.startswith(PACKAGE + '.'):
                assert target in sources, ('missing source', module, line, target)
                pending.append(target)
    return {'visited': dict(sorted(visited.items())),
            'forbidden_edges': [{'source': source, 'line': line, 'target': target}
                                for source, line, target in sorted(bad)]}


def _source_roster(pins):
    roster = {}
    for path in pins:
        if not path.startswith('src/data_sheets_schema/') or not path.endswith('.py'):
            continue
        name = path.removeprefix('src/').removesuffix('.py').replace('/', '.')
        if name.endswith('.__init__'):
            name = name.removesuffix('.__init__')
        assert name not in roster, ('ambiguous source', name)
        roster[name] = path
    return roster


def test_full_census_reports_each_independent_forbidden_edge_and_package_initializer():
    prefix = PACKAGE + '.'
    raw = {
        prefix + 'root': b'from . import child_a\nfrom .nested import child_b\n',
        prefix + 'child_a': b'from . import native_execution_authority_v2\n'
            b'def deferred():\n    from .native_execution import launch\n',
        prefix + 'nested': b'from .. import native_shared_results_orchestration\n',
        prefix + 'nested.child_b': b'VALUE = 1\n',
    }
    sources = {name: 'src/' + name.replace('.', '/') + '.py' for name in raw}
    sources[prefix + 'nested'] = 'src/data_sheets_schema/nested/__init__.py'
    result = _all_forbidden_edges(prefix + 'root', sources=sources,
        read_source=raw.__getitem__, owned=set(raw))
    assert set(result['visited']) == set(raw)
    assert {(row['source'], row['line'], row['target']) for row in result['forbidden_edges']} == {
        (prefix + 'child_a', 1, prefix + 'native_execution_authority_v2'),
        (prefix + 'child_a', 3, prefix + 'native_execution'),
        (prefix + 'nested', 1, prefix + 'native_shared_results_orchestration'),
    }


def test_full_census_preserves_owned_versus_utility_deferred_body_boundary():
    root, utility = PACKAGE + '.root', PACKAGE + '.utility'
    raw = {root: b'from . import utility\n', utility:
        b'from . import native_execution_authority_v2\n'
        b'def deferred():\n    from .native_execution import launch\n'}
    sources = {name: 'src/' + name.replace('.', '/') + '.py' for name in raw}
    result = _all_forbidden_edges(root, sources=sources, read_source=raw.__getitem__, owned={root})
    assert result['forbidden_edges'] == [{'source': utility, 'line': 1,
                                        'target': PACKAGE + '.native_execution_authority_v2'}]


def test_all_real_d_roots_have_no_reachable_forbidden_edges(isolated_modules, record_property):
    pins = authority.dependency_identity()['base']['package_sources']
    sources = _source_roster(pins)
    census = {name: _all_forbidden_edges(name, sources=sources,
        read_source=lambda module: _source(module, pins), owned=authority.CONSUMER_OWNED_MODULES,
        canonical=authority._canonical_import) for name in sorted(D_CONSUMERS)}
    record_property('d_full_forbidden_edge_census', json.dumps(census, sort_keys=True))
    assert {name: row['forbidden_edges'] for name, row in census.items()
            if row['forbidden_edges']} == {}


@pytest.mark.parametrize('short_name', [
    'native_shared_gate_primitives', 'native_shared_runtime_values', 'native_runtime_profiles'])
def test_new_d_neutral_consumers_refuse_deferred_legacy_edges(short_name, isolated_modules):
    """Mutation of in-memory source must refuse; no mutated module is loaded."""
    name = PACKAGE + '.' + short_name
    relative = 'src/data_sheets_schema/' + short_name + '.py'
    pins = authority.dependency_identity()['base']['package_sources']
    original = _source(name, pins)
    mutated = original + b'\ndef forbidden_deferred_edge():\n    from .native_execution import launch\n'
    pins = {**pins, relative: hashlib.sha256(mutated).hexdigest()}
    assert name in authority.CONSUMER_OWNED_MODULES
    with pytest.raises(ValueError, match='forbidden v1 execution authority'):
        authority.refuse_legacy_consumer_imports(mutated, name=name, package_sources=pins)


def test_unmasked_shared_registration_constants_equal_the_real_a_contract(isolated_modules):
    from data_sheets_schema import native_execution_registration_v2 as registration
    from data_sheets_schema import native_execution_engine as engine
    from data_sheets_schema import native_shared_gate_primitives as primitives
    from data_sheets_schema import native_shared_registration as shared

    assert shared.KIND == registration.EXECUTION_KIND
    assert shared.EXECUTION == registration.EXECUTION_SCOPE
    assert shared.VERSION == shared.AUTHORITY_VERSION == 2
    assert shared.GATES == engine.GATES == primitives.GATES == registration.EXECUTION_GATES


def test_real_stage_package_inventory_pins_the_executed_main_in_its_recipe(isolated_modules):
    """A package's import identity and its ``python -m`` entry stay distinct."""
    from data_sheets_schema import native_shared_permissions as permissions
    from data_sheets_schema import native_shared_registration as shared

    dependencies = authority.dependency_identity()
    pins = dependencies['base']['package_sources']
    rows = shared._production_sources(dependencies)
    by_module = {row['module']: row for row in rows}
    package, entry = PACKAGE + '.native_shared_stage', PACKAGE + '.native_shared_stage.__main__'
    init_path = 'src/data_sheets_schema/native_shared_stage/__init__.py'
    main_path = 'src/data_sheets_schema/native_shared_stage/__main__.py'
    assert package + '.__init__' not in by_module
    assert by_module[package]['path'] == str(authority.ROOT / init_path)
    assert by_module[package]['sha256'] == pins[init_path]
    assert by_module[entry]['path'] == str(authority.ROOT / main_path)
    assert by_module[entry]['sha256'] == pins[main_path]
    assert pins[init_path] != pins[main_path]
    recipe = permissions.recipe({'production_sources': rows})
    stage = next(row for row in recipe['module_map'] if row['module'] == package)
    assert stage['production_sha256'] == pins[main_path]
    assert stage['stub_member'] == 'stubs/data_sheets_schema/native_shared_stage.py'
