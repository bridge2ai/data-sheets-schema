"""A4/D114 scratch proposal logic, 2026-11-08 (#4354).

Only a synthetic producer fragment executes. The JSON parser is the real pure
contract parser; a closed import stub supplies the synthetic toolchain. These
tests do not execute the producer, API runner, registration or native program.
"""
import builtins
import importlib.util
from pathlib import Path
from types import SimpleNamespace

import pytest

from data_sheets_schema import native_shared_contract as contract

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / 'scripts/adhoc/propose_native_u4b_a4_producer_20261108.py'
SPEC = importlib.util.spec_from_file_location('a4_producer_proposal', PATH)
helper = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(helper)

FRAGMENT = b'''def prepare(spec, runtime, runtime_capture, max_draft_checks):
    _require_registered_input_spellings(spec)
    spec._native_shared_runtime_capture = runtime_capture
    spec._native_shared_max_draft_checks = max_draft_checks
    instruction = spec.instruction
    return instruction
'''


def _fragment(basis):
    """Run only the proposed branch with an explicit non-production import seam."""
    assert Path(contract.__file__).resolve() == ROOT / 'src/data_sheets_schema/native_shared_contract.py'
    events, imports = [], []
    historical = {'resources': {'historical-fixture': 'retained'}}
    selected = {'resources': {'selected-fixture': 'generation-only'}}
    runtime_capture = object()

    class Spec:
        def __init__(self):
            self._agentic_toolchain = historical

        def __setattr__(self, name, value):
            if name == '_native_shared_runtime_capture':
                events.append('runtime-bound')
            elif name == '_native_shared_max_draft_checks':
                events.append('draft-bound')
            object.__setattr__(self, name, value)

        @property
        def instruction(self):
            assert self._native_shared_runtime_capture is runtime_capture
            assert self._native_shared_max_draft_checks == 2
            events.append('instruction')
            return self._agentic_toolchain

    spec = Spec()

    def toolchain(*, native_shared):
        assert native_shared is True
        assert spec._native_shared_runtime_capture is runtime_capture
        assert 'instruction' not in events
        events.append('selected-toolchain')
        return selected

    def closed_import(name, globals=None, locals=None, fromlist=(), level=0):
        assert (name, tuple(fromlist), level) == ('agentic_runtime', ('toolchain',), 1)
        imports.append(name)
        return SimpleNamespace(toolchain=toolchain)

    def guard(value):
        assert value is spec
        events.append('entry-guard')

    namespace = {'__builtins__': {'__import__': closed_import, 'type': builtins.type,
                                'dict': builtins.dict},
                 '__package__': 'synthetic_producer_only',
                 'c': SimpleNamespace(strict_json=contract.strict_json),
                 '_require_registered_input_spellings': guard}
    proposed = helper.prepare(FRAGMENT, expected_sha256=helper.sha(FRAGMENT))
    exec(compile(proposed, 'synthetic-producer-fixture', 'exec'), namespace)
    return namespace['prepare'], spec, runtime_capture, events, imports, historical, selected


@pytest.mark.parametrize('basis', [
    'historical plain text',
    '{"kind":"unrelated_profile","version":3}',
    '{"kind":"d4d_native_u4b_runtime_basis_extra"}',
    '{"kind":"D4D_native_u4b_runtime_basis"}',
    '{"kind":null}', '{}', '[{"kind":"d4d_native_u4b_runtime_basis"}]',
])
def test_historical_basis_retains_original_toolchain_without_another_enumeration(basis):
    run, spec, capture, events, imports, historical, _ = _fragment(basis)
    assert run(spec, {'limits_basis': basis}, capture, 2) is historical
    assert spec._agentic_toolchain is historical
    assert imports == []
    assert events == ['entry-guard', 'runtime-bound', 'draft-bound', 'instruction']


@pytest.mark.parametrize('basis', [
    '{"kind":"d4d_native_u4b_runtime_basis"}',
    ' \n {"kind":"d4d_native_u4b_runtime_basis","version":3}',
])
def test_exact_u4b_basis_binds_once_after_runtime_and_before_first_instruction(basis):
    run, spec, capture, events, imports, _, selected = _fragment(basis)
    assert run(spec, {'limits_basis': basis}, capture, 2) is selected
    assert spec._agentic_toolchain is selected
    assert imports == ['agentic_runtime']
    assert events == ['entry-guard', 'runtime-bound', 'selected-toolchain',
                      'draft-bound', 'instruction']


@pytest.mark.parametrize('basis', [
    '{broken',
    '{"kind":"d4d_native_u4b_runtime_basis","kind":"unrelated"}',
    '{"kind":"d4d_native_u4b_runtime_basis","padding":"' + 'x' * 16384 + '"}',
])
def test_malformed_duplicate_or_oversize_object_basis_refuses_before_rendering(basis):
    run, spec, capture, events, imports, historical, _ = _fragment(basis)
    with pytest.raises(ValueError):
        run(spec, {'limits_basis': basis}, capture, 2)
    assert spec._agentic_toolchain is historical
    assert events == ['entry-guard', 'runtime-bound']
    assert imports == []


@pytest.mark.parametrize('change', ['preimage', 'extra_statement', 'duplicate_anchor',
                                  'guard_order', 'first_instruction_order'])
def test_proposal_refuses_preimage_drift_and_any_nonlocal_or_order_change(change):
    original = FRAGMENT
    if change == 'preimage':
        with pytest.raises(ValueError, match='preimage'):
            helper.prepare(original, expected_sha256='0' * 64)
        return
    if change == 'extra_statement':
        proposed = helper.prepare(original, expected_sha256=helper.sha(original))
        proposed = proposed.replace(b'return instruction', b'return None')
        with pytest.raises(ValueError, match='sole runtime-bound insertion'):
            helper.verify_single_insertion(original, proposed)
        return
    if change == 'duplicate_anchor':
        original = original.replace(helper.ANCHOR, helper.ANCHOR * 2)
    elif change == 'guard_order':
        original = original.replace(b'    _require_registered_input_spellings(spec)\n', b'    pass\n')
    else:
        original = original.replace(b'    instruction = spec.instruction\n', b'    instruction = None\n')
    with pytest.raises(ValueError):
        helper.prepare(original, expected_sha256=helper.sha(original))


def test_current_pinned_source_is_only_read_and_sole_insertion_is_proposed():
    path = ROOT / helper.TARGET
    before = path.read_bytes()
    assert helper.sha(before) == helper.PREIMAGE_SHA256
    proposed = helper.prepare(before)
    helper.verify_single_insertion(before, proposed)
    assert proposed.replace(helper.ANCHOR + helper.INSERTION, helper.ANCHOR, 1) == before
    assert path.read_bytes() == before
    assert proposed != before
    assert b'api_runner.py' not in helper.patch(before, proposed)
    assert helper.TARGET.endswith('/native_execution_registration_v2.py')
    assert any('D76' in entry for entry in helper.FUTURE_TEST_PLAN)
    assert any('replay' in entry for entry in helper.FUTURE_TEST_PLAN)
