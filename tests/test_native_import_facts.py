"""Pure syntax reuse with live graph checks; no native execution, 2026-11-11."""
import ast
import builtins
import collections
import sys
from types import SimpleNamespace

import pytest

from data_sheets_schema import native_execution_authority_v2 as authority
from tests.test_native_execution_verified_loader_v2 import graph_fixture, pin


NAME = 'data_sheets_schema.native_shared_registration'
CHILD = 'data_sheets_schema.synthetic_dependency'
RETENTION_SUPPORTED = sys.version_info >= (3, 10)  # effective function.__builtins__
retention_only = pytest.mark.skipif(not RETENTION_SUPPORTED,
    reason='Python 3.9 retains original cold graph behavior; no effective-builtins cache claim')


@pytest.fixture(autouse=True)
def empty_fact_cache():
    with authority._IMPORT_FACT_LOCK:
        authority._IMPORT_FACTS.clear()
        authority._IMPORT_FACT_TOTALS = (0, 0, 0)
    yield
    with authority._IMPORT_FACT_LOCK:
        authority._IMPORT_FACTS.clear()
        authority._IMPORT_FACT_TOTALS = (0, 0, 0)


def graph(tmp_path, monkeypatch, source=b'from . import synthetic_dependency\n', *, sized=True):
    child = b'def value():\n    return 1\n'
    if sized:
        # Substantive AST work, rather than comments/padding, keeps warm-path
        # mutation witnesses above the conservative small-source cutoff.
        statements = b''.join((f'metadata_value_{n} = {n} + 1\n').encode() for n in range(180))
        source += statements
        child += statements
    pins = graph_fixture(tmp_path, monkeypatch, {NAME: source, CHILD: child})
    return source, pins


def check(source, pins):
    return authority.refuse_legacy_consumer_imports(source, name=NAME, package_sources=pins)


@retention_only
def test_real_graph_reuses_facts_while_reapplying_lint_and_resolution(tmp_path, monkeypatch):
    source, pins = graph(tmp_path, monkeypatch)
    assert authority._current_import_facts(), (
        'positive witness requires the actual supported producer', authority._IMPORT_FACT_BINDING_ERROR,
        authority._IMPORT_FACT_FUNCTIONS.ready)
    expected = {NAME: pin(source), CHILD: pins['src/data_sheets_schema/synthetic_dependency.py']}
    assert check(source, pins) == expected
    retained = {key: value[0] for key, value in authority._IMPORT_FACTS.items()}
    assert len(retained) == 2
    seen = []
    original = authority._fact_targets

    def observe(facts, **kwargs):
        seen.append(facts)
        return original(facts, **kwargs)

    # Observe the live consumer, not a parser replacement that disables reuse.
    monkeypatch.setattr(authority, '_fact_targets', observe)
    assert check(source, pins) == expected
    assert len(seen) == 2
    assert all(any(facts is prior for prior in retained.values()) for facts in seen)
    assert all(type(facts) is tuple for facts in seen)


def test_original_graph_result_survives_unavailable_optional_reuse(tmp_path, monkeypatch):
    source, pins = graph(tmp_path, monkeypatch)
    monkeypatch.setattr(authority._IMPORT_FACT_FUNCTIONS, 'ready', False)
    assert check(source, pins) == {NAME: pin(source), CHILD: pins['src/data_sheets_schema/synthetic_dependency.py']}
    assert not authority._IMPORT_FACTS


def test_warm_graph_still_reads_changed_dependency_and_updated_pin(tmp_path, monkeypatch):
    source, pins = graph(tmp_path, monkeypatch)
    check(source, pins)
    relative = 'src/data_sheets_schema/synthetic_dependency.py'
    changed = b'from .native_execution import launch\n'
    (tmp_path / relative).write_bytes(changed)
    with pytest.raises(ValueError, match='source bytes differ'):
        check(source, pins)
    pins[relative] = pin(changed)
    with pytest.raises(ValueError, match='forbidden v1 execution authority'):
        check(source, pins)


def test_warm_facts_do_not_cache_live_pathfinder_origin(tmp_path, monkeypatch):
    source, pins = graph(tmp_path, monkeypatch, b'import native_execution\n')
    external = tmp_path / 'external'
    external.mkdir()
    (external / 'native_execution.py').write_text('VALUE = "ordinary external module"\n')
    package = tmp_path / 'src/data_sheets_schema'
    (package / 'native_execution.py').write_text('VALUE = "forbidden checkout origin"\n')
    monkeypatch.syspath_prepend(str(external))
    assert check(source, pins) == {NAME: pin(source)}
    assert bool(authority._IMPORT_FACTS) is RETENTION_SUPPORTED
    monkeypatch.syspath_prepend(str(package))
    with pytest.raises(ValueError, match='forbidden v1 execution authority'):
        check(source, pins)


@pytest.mark.parametrize('producer', ['parse', 'walk', 'iter_child_nodes', 'compile', 'parse_code'])
@pytest.mark.parametrize('warm', [False, True])
def test_changed_effective_producer_takes_original_cold_refusal(tmp_path, monkeypatch, producer, warm):
    source, pins = graph(tmp_path, monkeypatch)
    if warm:
        check(source, pins)
        assert bool(authority._IMPORT_FACTS) is RETENTION_SUPPORTED
    original_parse = ast.parse
    forbidden = b'import data_sheets_schema.native_execution\n'
    if producer == 'parse':
        monkeypatch.setattr(ast, 'parse', lambda *args, **kwargs: original_parse(forbidden))
    elif producer == 'walk':
        monkeypatch.setattr(ast, 'walk', lambda tree: iter(original_parse(forbidden).body))
    elif producer == 'iter_child_nodes':
        original_children = ast.iter_child_nodes

        def changed_children(node):
            if isinstance(node, ast.Module):
                return iter(original_parse(forbidden).body)
            return original_children(node)

        monkeypatch.setattr(ast, 'iter_child_nodes', changed_children)
    elif producer == 'compile':
        def changed_compile(source, filename, mode, flags=0, **kwargs):
            return builtins.compile(forbidden, filename, mode, flags, **kwargs)

        monkeypatch.setattr(ast, 'compile', changed_compile, raising=False)
    else:
        def changed_parse(source, filename='<unknown>', mode='exec', **kwargs):
            raise ValueError('changed parser code')

        monkeypatch.setattr(ast.parse, '__code__', changed_parse.__code__)
    with pytest.raises(ValueError, match=('no inspectable import graph' if producer == 'parse_code'
                                         else 'forbidden v1 execution authority')):
        check(source, pins)
    assert not authority._IMPORT_FACTS


def test_changed_ast_fields_preserve_actual_cold_result(tmp_path, monkeypatch):
    source, pins = graph(tmp_path, monkeypatch)
    assert CHILD in check(source, pins)
    monkeypatch.setattr(ast.Module, '_fields', ())
    # Cold ast.walk now visits no imports. The cache must not keep old edges.
    assert check(source, pins) == {NAME: pin(source)}
    assert not authority._IMPORT_FACTS


def test_changed_parse_defaults_keep_cold_syntax_error(tmp_path, monkeypatch):
    source, pins = graph(tmp_path, monkeypatch)
    check(source, pins)
    monkeypatch.setattr(ast.parse, '__defaults__', ('<unknown>', 'eval'))
    with pytest.raises(ValueError, match='no inspectable import graph'):
        check(source, pins)
    assert not authority._IMPORT_FACTS


@pytest.mark.parametrize('warm', [False, True])
def test_effective_import_hook_cannot_reuse_previous_traversal(tmp_path, monkeypatch, warm):
    source, pins = graph(tmp_path, monkeypatch)
    if warm:
        check(source, pins)
        assert bool(authority._IMPORT_FACTS) is RETENTION_SUPPORTED
    forbidden = ast.parse('import data_sheets_schema.native_execution\n')
    original = builtins.__import__
    original_deque = collections.deque
    substituted = SimpleNamespace(deque=lambda values: original_deque([forbidden]))

    def changed_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name == 'collections' and 'deque' in fromlist:
            return substituted
        return original(name, globals, locals, fromlist, level)

    # ast.walk's import changes while collections/deque/sys.modules do not.
    monkeypatch.setattr(builtins, '__import__', changed_import)
    with pytest.raises(ValueError, match='forbidden v1 execution authority'):
        check(source, pins)
    assert collections.deque is original_deque
    assert not authority._IMPORT_FACTS


@pytest.mark.parametrize('warm', [False, True])
def test_equal_looking_flags_keep_effective_cold_compile_behavior(tmp_path, monkeypatch, warm):
    source, pins = graph(tmp_path, monkeypatch)
    if warm:
        check(source, pins)
        assert bool(authority._IMPORT_FACTS) is RETENTION_SUPPORTED
    original = ast.PyCF_ONLY_AST

    class EqualFlag:
        def __eq__(self, other):
            return other == original

        def __index__(self):
            return 0

    flag = EqualFlag()
    assert flag == original
    monkeypatch.setattr(ast, 'PyCF_ONLY_AST', flag)
    # With flags=0 cold compile returns code, so ast.walk fails as before.
    with pytest.raises(AttributeError, match='_fields'):
        check(source, pins)
    assert not authority._IMPORT_FACTS


def test_changed_import_time_visitor_is_not_hidden_by_facts(tmp_path, monkeypatch):
    source, pins = graph(tmp_path, monkeypatch)
    check(source, pins)
    forbidden = ast.parse('import data_sheets_schema.native_execution\n')
    monkeypatch.setattr(authority, '_import_time_nodes', lambda tree: iter(forbidden.body))
    with pytest.raises(ValueError, match='forbidden v1 execution authority'):
        check(source, pins)
    assert not authority._IMPORT_FACTS


def test_owned_traversal_mode_is_part_of_fact_key(tmp_path, monkeypatch):
    source, pins = graph(tmp_path, monkeypatch, b'def deferred():\n    exec("1")\n')
    with pytest.raises(ValueError, match='dynamic loading or evaluation'):
        check(source, pins)
    assert bool(authority._IMPORT_FACTS) is RETENTION_SUPPORTED  # Syntax only; never a refusal.
    monkeypatch.setattr(authority, 'CONSUMER_OWNED_MODULES',
                        authority.CONSUMER_OWNED_MODULES - {NAME})
    assert check(source, pins) == {NAME: pin(source)}


def test_current_lint_policy_is_reapplied_to_retained_syntax(tmp_path, monkeypatch):
    source, pins = graph(tmp_path, monkeypatch, b'import json\nVALUE = json.value\n')
    assert check(source, pins) == {NAME: pin(source)}
    retained = tuple(value[0] for value in authority._IMPORT_FACTS.values())
    assert bool(retained) is RETENTION_SUPPORTED
    monkeypatch.setattr(authority, '_LEGACY_CONSUMER_MODULES',
                        authority._LEGACY_CONSUMER_MODULES | {'json.value'})
    with pytest.raises(ValueError, match='forbidden v1 execution authority'):
        check(source, pins)
    assert all(any(facts is row[0] for row in authority._IMPORT_FACTS.values())
               for facts in retained)


@retention_only
def test_fact_retention_is_bounded_and_parse_failure_is_not_published(tmp_path, monkeypatch):
    monkeypatch.setattr(authority, '_IMPORT_FACT_LIMITS', (2, 100_000, 10_000, 100_000))
    for number in range(3):
        source, pins = graph(tmp_path, monkeypatch, ('VALUE = ' + str(number) + '\n').encode())
        assert check(source, pins) == {NAME: pin(source)}
    assert len(authority._IMPORT_FACTS) == 2
    assert all(total <= bound for total, bound in
               zip(authority._IMPORT_FACT_TOTALS, authority._IMPORT_FACT_LIMITS[1:]))
    retained = tuple(authority._IMPORT_FACTS.items())
    source, pins = graph(tmp_path, monkeypatch, b'if !!!\n')
    with pytest.raises(ValueError, match='no inspectable import graph'):
        check(source, pins)
    assert tuple(authority._IMPORT_FACTS.items()) == retained


@pytest.mark.parametrize('bad, message', [
    (b'from .native_execution import launch\n', 'forbidden v1 execution authority'),
    (b'exec("1")\n', 'dynamic loading or evaluation'),
    (b'if !!!\n', 'no inspectable import graph'),
])
def test_small_sources_use_original_graph_without_guard_or_extraction(tmp_path, monkeypatch, bad, message):
    def unexpected(*args, **kwargs):
        raise AssertionError('small source reached optional producer guard or extraction')

    monkeypatch.setattr(authority, '_current_import_facts', unexpected)
    monkeypatch.setattr(authority, '_import_facts', unexpected)
    source, pins = graph(tmp_path, monkeypatch, sized=False)
    assert check(source, pins) == {
        NAME: pin(source), CHILD: pins['src/data_sheets_schema/synthetic_dependency.py']}
    assert not authority._IMPORT_FACTS
    source, pins = graph(tmp_path, monkeypatch, bad, sized=False)
    with pytest.raises(ValueError, match=message):
        check(source, pins)
    assert not authority._IMPORT_FACTS
