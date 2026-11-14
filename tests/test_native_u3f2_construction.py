"""U3-F2 real shared RunSpec construction witnesses, 2026-11-09.

The observer corrupts a genuine replay constructor's return, without replacing
source-pinned callables. Real native restoration must refuse before downstream
work. These tests cover the three current shared replay factories, not legacy
attribution CLI construction or the neutral executable. The saved-results case
uses a real captured selection/composition prefix, not a completed execution.
"""
import ast
from contextlib import contextmanager
import sys

import pytest

from data_sheets_schema import native_execution_authority_v2 as authority
from data_sheets_schema import native_shared_contract as c
from data_sheets_schema import native_shared_controller_orchestration as composition
from data_sheets_schema import native_shared_controls_orchestration as controls
from data_sheets_schema import native_shared_evidence as evidence
from data_sheets_schema import native_shared_results as results
from data_sheets_schema import native_shared_selection as selection
from tests.test_native_shared_controller import (
    bound, declaration, inputs, isolated_modules, native_spec, synthetic_declaration,
)
from tests.test_native_execution_registration_v2 import _entries, _files


def _key(frame):
    return (frame.f_globals.get('__name__', '').rsplit('.', 1)[-1],
            frame.f_code.co_name)


@contextmanager
def _corrupt_replay_constructor(factory):
    """Alter only the actual RunSpec constructed directly by this factory.

    A callable profile observer preserves any existing observer and code
    identity. The native restore/check functions remain the real production
    bodies. Identity assertions prevent an unrelated earlier refusal passing.
    """
    previous = sys.getprofile()
    observed = {'constructed': [], 'restored': [], 'input_checked': []}
    forbidden = {
        ('native_shared_controller', 'compose'),
        ('native_shared_controller', 'reconstruct_composition'),
        ('native_shared_capture', '_prefix'),
        ('native_shared_capture', '_binding'),
    }

    def observe(frame, event, argument):
        if previous is not None:
            previous(frame, event, argument)
        name = frame.f_code.co_name
        if event == 'return' and name == '__init__':
            replay = frame.f_back
            caller = None if replay is None else replay.f_back
            if (replay is not None and caller is not None
                    and _key(replay) == ('api_runner', 'from_render_spec')
                    and _key(caller) == factory):
                spec = frame.f_locals.get('self')
                if type(spec).__name__ != 'RunSpec':
                    return  # Path arguments are also constructed in this frame.
                assert spec._replay_only is True
                spec.bundle = spec.bundle.with_name('unbound-replay-construction-witness.txt')
                observed['constructed'].append(spec)
            return
        if event != 'call' or not observed['constructed']:
            return
        if name in ('restore', '_same_spec_inputs'):
            key = _key(frame)
            if key[0] == 'native_shared_render':
                spec = frame.f_locals['spec']
                assert spec is observed['constructed'][-1]
                observed['restored' if name == 'restore' else 'input_checked'].append(spec)
        elif name in ('compose', 'reconstruct_composition', '_prefix', '_binding'):
            if _key(frame) in forbidden:
                pytest.fail('constructed replay escaped its native input guard')
        elif name in ('instruction', 'render_spec'):
            if frame.f_locals.get('self') is observed['constructed'][-1]:
                pytest.fail('constructed replay was consumed before native input refusal')

    sys.setprofile(observe)
    try:
        yield observed
    finally:
        sys.setprofile(previous)


def _assert_constructed_refusal(observed):
    assert len(observed['constructed']) == 1
    spec = observed['constructed'][0]
    assert observed['restored'] == [spec]
    assert observed['input_checked'] == [spec]


@pytest.fixture
def composed(bound):
    source, preparation, raw, instruction = bound
    value = composition.compose(raw, instruction_path=instruction)
    return source, preparation, raw, instruction, value


def test_controller_factory_checks_real_constructed_replay_before_composition(bound):
    source, _, raw, instruction = bound
    before = _files(source['root']), _entries(source['root'])
    with _corrupt_replay_constructor(
            ('native_shared_controller_orchestration', '_compose')) as observed:
        with pytest.raises(ValueError, match='native render input differs from selected bundle'):
            composition.compose(raw, instruction_path=instruction)
    _assert_constructed_refusal(observed)
    assert (_files(source['root']), _entries(source['root'])) == before


def test_registration_factory_checks_real_constructed_replay_with_genuine_controls(composed):
    source, preparation, raw, _, selected = composed
    dependencies = preparation['registration']['dependencies']
    before = _files(source['root']), _entries(source['root'])
    with controls.loaded_controls(dependencies) as projection, \
            authority.loaded_verified_package_module(
                'data_sheets_schema.native_shared_registration',
                package_sources=dependencies['base']['package_sources']) as consumer:
        with _corrupt_replay_constructor(
                ('native_shared_registration', '_selection')) as observed:
            with pytest.raises(ValueError, match='native render input differs from selected bundle'):
                consumer._selection(c.canonical(selected), preparation_raw=raw,
                    classifier_projection=projection)
        _assert_constructed_refusal(observed)
    assert (_files(source['root']), _entries(source['root'])) == before


def test_saved_results_factory_checks_constructed_replay_before_stream_reconstruction(composed):
    source, _, _, _, selected = composed
    captured = selection.capture(source['selection'])
    artifacts = (captured.registration, captured.receipt_policy, *captured.authority,
                 *(artifact for schema in captured.schemas for artifact in schema.sources))
    members = tuple(evidence.read_regular(artifact.pin.path, artifact.pin.role,
                    max_bytes=artifact.pin.bytes) for artifact in artifacts)
    pool = evidence.CapturePool(members, ())
    raw = c.canonical(selected)
    # Only the genuine immutable construction prefix is needed: transcript,
    # start identity and execution evidence must not be consulted on refusal.
    value = {'composition_raw_json': raw.decode('utf-8'), 'composition_sha256': c.sha(raw)}
    assert results._captured_selection(pool, value) == captured
    before = _files(source['root']), _entries(source['root'])
    with _corrupt_replay_constructor(('native_shared_results', 'rebuild')) as observed:
        with pytest.raises(ValueError, match='native render input differs from selected bundle'):
            results.rebuild(pool, value)
    _assert_constructed_refusal(observed)
    assert (_files(source['root']), _entries(source['root'])) == before


def test_registration_scanner_literals_equal_shared_contract():
    """Keep scanner-visible literals tied to their semantic runtime constants."""
    path = authority.ROOT / 'src/data_sheets_schema/native_shared_registration.py'
    tree = ast.parse(path.read_text(encoding='utf-8'), filename=str(path))
    function, = (node for node in tree.body
                 if isinstance(node, ast.FunctionDef) and node.name == '_selection')
    for field, expected in (('condition', c.CONDITION), ('render_version', c.RENDERER)):
        comparisons = [node for node in ast.walk(function)
            if isinstance(node, ast.Compare)
            and isinstance(node.left, ast.Attribute)
            and isinstance(node.left.value, ast.Name)
            and node.left.value.id == 'spec' and node.left.attr == field]
        comparison, = comparisons
        assert len(comparison.ops) == 1 and isinstance(comparison.ops[0], ast.NotEq)
        literal, = comparison.comparators
        assert isinstance(literal, ast.Constant)
        assert type(literal.value) is type(expected) and literal.value == expected
