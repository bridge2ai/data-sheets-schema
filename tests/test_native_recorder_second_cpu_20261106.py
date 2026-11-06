"""Synthetic U0 second-observer guard evidence; 2026-11-06. No recorder run."""
import importlib.util
import json
from pathlib import Path
import sys

import pytest


SCRIPT = Path(__file__).resolve().parents[1] / 'scripts/adhoc/native_recorder_second_cpu_20261106.py'
SPEC = importlib.util.spec_from_file_location('u0_second_observer_tests', SCRIPT)
helper = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(helper)


def load(path, name, monkeypatch):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, name, module)
    spec.loader.exec_module(module)
    return module


def fixture(tmp_path, monkeypatch):
    if not hasattr(sys, 'monitoring'):
        pytest.skip('requires sys.monitoring')
    root = tmp_path / 'source'
    package = root / 'src/data_sheets_schema'
    package.mkdir(parents=True)
    catalog = package / 'native_catalog_reuse.py'
    catalog.write_text('''_READY = object()
_OTHER = object()
_STATE = ((1,), (2,))
_INITIALIZED_STATE = _STATE
mode = 'ready'
state_calls = 0
def _state():
    global state_calls
    state_calls += 1
    if mode == 'raise':
        raise TypeError('synthetic unsupported immutable dependency')
    return ((9,), (2,)) if mode == 'different' else _STATE
def runtime_token():
    if mode == 'other_marker':
        return _OTHER
    try:
        if mode != 'not_ready':
            actual = _state()
            if actual == _STATE or actual == _INITIALIZED_STATE:
                return _READY
    except Exception:
        pass
    return None
''')
    events = package / 'native_schema_event_reuse.py'
    events.write_text('''_BOUND = ((1,),)
mode = 'ready'
binding_calls = 0
def _bindings():
    global binding_calls
    binding_calls += 1
    if mode == 'raise':
        raise TypeError('synthetic parser state refused')
    return ((2,),) if mode == 'different' else _BOUND
def _token(limit):
    try:
        if _BOUND is None or _bindings() != _BOUND:
            return None
        return (limit,)
    except Exception:
        return None
''')
    initialization = package / 'native_catalog_initialization.py'
    initialization.write_text('''_PATH = '/synthetic/linkml/utils/rawloader.py'
SOURCE_SHA256 = 'a' * 64
_root_path = '/synthetic/linkml_runtime/utils/yamlutils.py'
DEFAULT_SOURCE_SHA256 = 'b' * 64
INITIALIZATION_ERROR = None
guard_calls = 0
def marker():
    global guard_calls
    guard_calls += 1
    raise AssertionError('provenance must not call a guard')
''')
    parser = tmp_path / 'yaml_fixture.py'
    parser.write_text('def parse(stream, Loader=None):\n    yield stream\n')
    monkeypatch.setattr(helper.base.Observer, '_origins', lambda self: [])
    monkeypatch.setattr(helper.base, 'process_age', lambda: {'seconds': 0, 'method': 'synthetic'})
    seen = helper.SecondCPUObserver(root, tmp_path / 'evidence', phases={
        'native_catalog_reuse': {'_state': 'state', 'runtime_token': 'token'},
        'native_schema_event_reuse': {'_bindings': 'bindings', '_token': 'parser_token'}},
        cache_targets={}, parser_path=parser,
        closure_checker=lambda root: {'verified': True, 'root': str(root)})
    seen.start(arm_trace=False, periodic=False)
    return seen, load(catalog, 'u0_catalog_synthetic', monkeypatch), load(events, 'u0_events_synthetic', monkeypatch)


def rows(seen):
    return [json.loads(line) for line in (seen.output / 'observer.jsonl').read_text().splitlines()]


def test_second_observer_canary_preserves_actual_guard_returns_and_unwinds(tmp_path, monkeypatch):
    seen, catalog, _ = fixture(tmp_path, monkeypatch)
    original = catalog.runtime_token
    try:
        assert catalog.runtime_token() is catalog._READY
        catalog.mode = 'different'
        assert catalog.runtime_token() is None
        catalog.mode = 'raise'
        assert catalog.runtime_token() is None
        catalog.mode = 'not_ready'
        assert catalog.runtime_token() is None
        assert catalog.runtime_token is original
        assert catalog.state_calls == 3, 'observer must not rerun state production'
    finally:
        seen.close()
    assert seen.valid
    assert seen.stats['native_catalog_reuse:runtime_token']['calls'] == 4
    assert seen.stats['native_catalog_reuse:_state']['calls'] == 3
    assert seen.stats['native_catalog_reuse:_state']['unwinds'] == 1
    assert seen.stats['native_catalog_reuse:_state']['inclusive_thread_cpu_ns'] > 0
    assert not any(key.startswith('runtime_token_') for key in seen.stats['native_catalog_reuse:_state']['counters'])
    reasons = seen.reason_counts
    assert reasons['native_catalog_reuse:runtime_token/token_available'] == 1
    assert reasons['native_catalog_reuse:runtime_token/actual_state_available_refusal'] == 1
    assert reasons['native_catalog_reuse:runtime_token/state_exception_refused'] == 1
    assert reasons['native_catalog_reuse:runtime_token/not_ready_or_unobserved_failure'] == 1
    evidence = rows(seen)
    errors = [row for row in evidence if row['event'] == 'guard_observation' and row['reason'] == 'actual_unwind']
    assert errors[0]['detail']['type'] == 'TypeError'
    assert errors[0]['detail']['primitive_args'] == ['synthetic unsupported immutable dependency']
    assert any(row['target'] == 'native_catalog_reuse:runtime_token' for row in errors[0]['parents'])
    assert evidence[-1]['valid'] and evidence[-1]['guard_reason_counts'] == reasons


def test_both_legitimate_non_null_markers_are_available_without_changing_base_counters(tmp_path, monkeypatch):
    seen, catalog, _ = fixture(tmp_path, monkeypatch)
    try:
        assert catalog.runtime_token() is catalog._READY
        catalog.mode = 'other_marker'
        assert catalog.runtime_token() is catalog._OTHER
    finally:
        seen.close()
    assert seen.valid
    assert seen.reason_counts == {'native_catalog_reuse:runtime_token/token_available': 2}
    assert seen.stats['native_catalog_reuse:runtime_token']['counters'] == {
        'runtime_token_ready': 1, 'runtime_token_other': 1}
    observations = [row for row in rows(seen) if row.get('reason') == 'token_available']
    assert [row['detail']['marker_kind'] for row in observations] == ['initial_READY', 'other_non_null_marker']


def test_parser_token_records_actual_binding_result_and_exception_without_replay(tmp_path, monkeypatch):
    seen, _, events = fixture(tmp_path, monkeypatch)
    try:
        assert events._token(10) == (10,)
        events.mode = 'different'
        assert events._token(10) is None
        events.mode = 'raise'
        assert events._token(10) is None
        events._BOUND = None
        assert events._token(10) is None
        assert events.binding_calls == 3
    finally:
        seen.close()
    assert seen.valid
    assert seen.reason_counts['native_schema_event_reuse:_token/token_available'] == 1
    assert seen.reason_counts['native_schema_event_reuse:_token/initial_binding_unsupported'] == 1
    assert seen.reason_counts['native_schema_event_reuse:_token/bindings_exception_refused'] == 1
    rejected = next(row for row in rows(seen) if row.get('reason') == 'token_none_without_observed_unwind')
    assert rejected['detail']['bindings_result']['equal'] is False
    assert seen.stats['native_schema_event_reuse:_bindings']['calls'] == 3


def test_opaque_difference_never_invokes_user_equality_or_repr():
    class Opaque:
        def __eq__(self, other):
            raise AssertionError('equality must not run')
        def __repr__(self):
            raise AssertionError('repr must not run')
    result = helper.primitive_difference((Opaque(),), (Opaque(),))
    assert result['equal'] is None and result['opaque_or_unclassified']
    mismatch = helper.primitive_difference(((1, 2),), ((1, 3),))
    assert mismatch['equal'] is False and mismatch['first_difference']['path'] == [0, 1]


def test_state_comparison_is_bounded_and_opaque_is_not_a_mismatch():
    result = helper.primitive_difference(tuple(range(1000)), tuple(range(1000)), budget=2)
    assert result['equal'] is None and result['budget_exhausted']
    result = helper.state_components(((1,), object()), ((2,), object()))
    differences = result['nonidentical_or_unclassified_components']
    assert differences[0]['equal'] is False and differences[1]['equal'] is None


def test_reason_details_are_bounded_but_counters_are_complete(tmp_path, monkeypatch):
    seen, catalog, _ = fixture(tmp_path, monkeypatch)
    monkeypatch.setattr(helper, 'MAX_REASON_DETAILS', 3)
    monkeypatch.setattr(helper, 'MAX_REASON_EXAMPLES', 2)
    try:
        catalog.mode = 'raise'
        for _ in range(12):
            assert catalog.runtime_token() is None
    finally:
        seen.close()
    assert seen.valid and catalog.state_calls == 12
    assert seen.reason_details == 3 and seen.reason_details_suppressed == 21
    assert seen.reason_counts['native_catalog_reuse:runtime_token/state_exception_refused'] == 12
    assert len([row for row in rows(seen) if row['event'] == 'guard_observation']) == 3
    assert not seen.guard_observations


def test_exception_reading_does_not_stringify_custom_exception():
    class Hostile(Exception):
        def __str__(self):
            raise AssertionError('str must not run')
    result = helper.exception_evidence(Hostile('x' * 1000, object()))
    assert result['type'] == 'Hostile'
    assert len(result['primitive_args'][0]) == 384
    assert result['primitive_args'][1] == '<opaque argument omitted>'


def test_extension_keeps_existing_phases_and_deduplicates_runtime_target():
    for module, targets in helper.thread.PHASES.items():
        assert targets.items() <= helper.PHASES[module].items()
    assert helper.PHASES['native_catalog_reuse'] == {
        '_state': 'catalog_eligibility_state', 'runtime_token': 'catalog_eligibility'}
    assert 'second-observer-output' in helper.CONFIG_BYTES.decode()
    assert helper.CONFIG_NAME == 'native_recorder_second_cpu_20261106.config.json'


def test_callback_provenance_passively_reads_pinned_naturally_loaded_module(tmp_path, monkeypatch):
    seen, _, _ = fixture(tmp_path, monkeypatch)
    assert seen._initialization_provenance() == {'state': 'not_loaded', 'present_in_source': True}
    path = seen.root / 'src/data_sheets_schema/native_catalog_initialization.py'
    module = load(path, 'data_sheets_schema.native_catalog_initialization', monkeypatch)
    try:
        result = seen._initialization_provenance()
        assert result['state'] == 'loaded'
        assert result['compiled_dependency_sources']['rawloader'] == {
            'path': '/synthetic/linkml/utils/rawloader.py', 'sha256': 'a' * 64}
        assert result['compiled_dependency_sources']['yamlutils']['sha256'] == 'b' * 64
        assert module.guard_calls == 0
        assert 'not reread or attested' in result['scope']
        monkeypatch.setattr(module, '__file__', str(tmp_path / 'foreign.py'))
        with pytest.raises(RuntimeError, match='not the pinned diagnostic source'):
            seen._initialization_provenance()
        monkeypatch.setattr(module, '__file__', str(path))
    finally:
        seen.close()
    assert rows(seen)[-1]['catalog_initialization_provenance'] == result
    assert module.guard_calls == 0


def test_incomplete_initialization_provenance_is_explicit_not_success(tmp_path, monkeypatch):
    seen, _, _ = fixture(tmp_path, monkeypatch)
    path = seen.root / 'src/data_sheets_schema/native_catalog_initialization.py'
    module = load(path, 'data_sheets_schema.native_catalog_initialization', monkeypatch)
    try:
        module.DEFAULT_SOURCE_SHA256 = None
        with pytest.raises(RuntimeError, match='lacks compiled dependency provenance'):
            seen._initialization_provenance()
        module.INITIALIZATION_ERROR = 'PermissionError: synthetic unreadable source'
        result = seen._initialization_provenance()
        assert result['initialization_error'].startswith('PermissionError')
        assert result['compiled_dependency_sources']['yamlutils']['sha256'] is None
    finally:
        seen.close()
    assert module.guard_calls == 0
