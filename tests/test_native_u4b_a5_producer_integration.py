"""A5/D114 genuine preparation/composition/replay, 2026-11-09 (#4354).

Saved U4b observation bytes are invented fixtures validated by real consumers.
Only local Git subprocesses are allowed; no native or provider execution.
"""
from copy import deepcopy
from pathlib import Path
import sys

import pytest

from data_sheets_schema import api_runner as api
from data_sheets_schema import agentic_runtime as tools
from data_sheets_schema import native_shared_contract as c
from data_sheets_schema import native_execution_registration_v2 as producer
from data_sheets_schema import native_u4b_runtime as runtime
from data_sheets_schema import native_shared_controller_orchestration as composition
from data_sheets_schema import native_shared_controls_orchestration as controls
from data_sheets_schema import native_execution_authority_v2 as authority
from tests.test_native_execution_registration_v2 import (
    inputs, isolated_modules, _prepare, _entries, _files,
)
from tests.test_native_shared_render import native_spec
from tests.test_native_shared_selection import declaration as synthetic_declaration
from tests.test_native_shared_controller import declaration
from tests.test_native_u4b_runtime import runtime_inputs


NATIVE_RESOURCES = {
    '.claude/commands/d4d-agent.md', '.claude/commands/d4d-full-core.md',
    '.claude/commands/d4d-uniform-rules.md', '.claude/agents/d4d-provenance-guard.md',
    '.claude/agents/d4d-validator.md',
    'src/data_sheets_schema/schema/data_sheets_schema_all.yaml',
    'src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml',
}


def select_runtime(inputs, u4b):
    if u4b:
        root = inputs['root'] / 'u4b'
        root.mkdir()
        initial, arguments = runtime_inputs(root)
        selected = runtime.prepare_runtime(initial, **arguments)
        assert runtime.validate_prepared_runtime(selected) == selected
        inputs['runtime_path'].write_bytes(c.canonical(selected))
        inputs['runtime'] = selected
    return inputs


def restored(inputs, body):
    original = inputs['spec']
    return api.RunSpec.from_render_spec(body['render_spec'], project=original.project,
                                       method=original.method, label=original.label)


def test_prepare_captures_and_rechecks_runtime_with_current_source_owned_reader(inputs):
    """Observe both real current-module reads without replacing a pinned callable."""
    from data_sheets_schema.native_shared_evidence import read_regular
    select_runtime(inputs, True)
    previous = sys.getprofile()
    reads = []

    def observe(frame, event, argument):
        if previous is not None:
            previous(frame, event, argument)
        if (event == 'call' and frame.f_code is read_regular.__code__
                and frame.f_back is not None
                and frame.f_back.f_code is producer.prepare.__code__):
            reads.append((frame.f_locals['path'], frame.f_locals['role'],
                          frame.f_locals['max_bytes']))

    sys.setprofile(observe)
    try:
        body = _prepare(inputs)['registration']
    finally:
        sys.setprofile(previous)
    assert reads == [(str(inputs['runtime_path']), 'runtime_declaration',
                      c.HARD_LIMITS['input_bytes'])] * 2
    assert body['runtime']['sha256'] == c.sha(inputs['runtime_path'].read_bytes())
    source = authority.ROOT / 'src/data_sheets_schema/native_execution_registration_v2.py'
    assert body['pinned_files'][str(source)] == c.sha(source.read_bytes())


@pytest.mark.parametrize('u4b', [False, True], ids=['historical', 'u4b'])
def test_prepare_verify_first_instruction_and_recorded_replay(inputs, monkeypatch, u4b):
    select_runtime(inputs, u4b)
    expected = tools.toolchain(native_shared=u4b)
    if u4b:
        assert set(expected['resources']) == NATIVE_RESOURCES
    calls, rendered = [], []
    real_toolchain, resolve = tools.toolchain, api.resolve_prompt

    def enumerate_tools(*args, **kwargs):
        calls.append(kwargs.get('native_shared', False))
        return real_toolchain(*args, **kwargs)

    def first_instruction(spec):
        assert 'instruction' not in spec.__dict__
        assert spec._native_shared_runtime_capture.raw == inputs['runtime_path'].read_bytes()
        assert spec._native_shared_max_draft_checks == 2
        assert spec._agentic_toolchain == expected
        rendered.append(spec)
        return resolve(spec)

    with monkeypatch.context() as spy:
        spy.setattr(tools, 'toolchain', enumerate_tools)
        spy.setattr(api, 'resolve_prompt', first_instruction)
        envelope = _prepare(inputs)
        body = envelope['registration']
        assert len(rendered) == 1
        assert calls == ([False, True] if u4b else [False])
        assert producer.verify_preparer(c.canonical(envelope), job_id=body['job_id']) == body
        assert len(rendered) == 2
        assert calls == ([False, True, False, True] if u4b else [False, False])
    assert body['render_spec']['agentic_toolchain'] == expected
    for name in ('instruction', 'render_spec'):
        raw = body[name].encode() if name == 'instruction' else c.canonical(body[name])
        (inputs['root'] / (name + '.txt')).write_bytes(raw)
    # Replay is recorded-only even when current runtime is unusable.
    inputs['runtime_path'].write_bytes(b'changed live runtime, not JSON\n')
    monkeypatch.setattr(tools, 'toolchain', lambda **kw: pytest.fail('replay enumerated live toolchain'))
    replay = restored(inputs, body)
    assert replay.render_spec() == body['render_spec']
    assert replay.instruction.encode() == body['instruction'].encode()
    assert inputs['calls'] and all(Path(call[0]).name == 'git' for call in inputs['calls'])


@pytest.mark.parametrize('basis', ['historical shared-v1 text', '{"kind":"unrelated"}',
                                  '{"kind":"d4d_native_u4b_runtime_basis_extra"}'])
def test_historical_discriminators_keep_pre_hook_instruction_and_only_d76_recorder_delta(inputs, monkeypatch, basis):
    """D114 leaves old rosters alone; D76 adds one model-facing recorder field.

    Compare the real producer with an independent pre-D114 construction using
    its new default registered-path setting. Keep a separate old-false reference
    and require one exact JSON-field insertion in its embedded recorder command;
    no text or metadata normalization is permitted.
    """
    selected = deepcopy(inputs['runtime'])
    selected['limits_basis'] = basis
    inputs['runtime_path'].write_bytes(c.canonical(selected))
    original = inputs['spec']
    from dataclasses import replace
    from data_sheets_schema.native_shared_evidence import read_regular
    captured = read_regular(str(inputs['runtime_path']), 'runtime_declaration',
                            max_bytes=c.HARD_LIMITS['input_bytes']).captured
    references = []
    for registered in (False, True):
        reference = replace(original, provider=selected['provider'],
            reasoning_effort=selected['effort'], run_date=inputs['kwargs']['run_date'],
            registered_input_paths=registered)
        reference._native_shared_runtime_capture = captured
        reference._native_shared_max_draft_checks = 2
        references.append(reference)
    historical, pre_hook = references
    historical_instruction = historical.instruction
    expected = pre_hook.instruction
    assert 'registered_input_paths' not in historical.render_spec()
    assert pre_hook.render_spec() == {**historical.render_spec(), 'registered_input_paths': True}
    recorder = [line for line in historical_instruction.splitlines() if '--render-spec-json' in line]
    assert len(recorder) == 1 and 'provenance record' in recorder[0]
    anchor = ',"render_version":26,'
    insertion = ',"registered_input_paths":true'
    assert recorder[0].count(anchor) == historical_instruction.count(anchor) == 1
    assert insertion not in historical_instruction
    # Whole-instruction byte equality after exactly this one insertion also
    # forbids an unreported directive, roster, whitespace or other JSON delta.
    assert expected.encode() == historical_instruction.encode().replace(
        anchor.encode(), (insertion + anchor).encode(), 1)
    calls = []
    real = tools.toolchain
    def count(**kwargs):
        calls.append(kwargs)
        return real(**kwargs)
    monkeypatch.setattr(tools, 'toolchain', count)
    body = _prepare(inputs)['registration']
    assert calls == [{}]
    assert body['instruction'] == expected
    assert body['render_spec']['agentic_toolchain'] == historical._agentic_toolchain == pre_hook._agentic_toolchain


@pytest.mark.parametrize('basis', ['{broken', '{"kind":"a","kind":"b"}',
                                  '{"padding":"' + 'x' * 16384 + '"}'])
def test_bad_object_basis_refuses_before_first_instruction(inputs, monkeypatch, basis):
    selected = deepcopy(inputs['runtime'])
    selected['limits_basis'] = basis
    inputs['runtime_path'].write_bytes(c.canonical(selected))
    monkeypatch.setattr(api, 'resolve_prompt', lambda *a: pytest.fail('malformed basis rendered'))
    with pytest.raises(ValueError):
        _prepare(inputs)


@pytest.mark.parametrize('change', ['recorded_toolchain', 'live_runtime'])
def test_verify_preparer_refuses_changed_authority(inputs, change):
    select_runtime(inputs, True)
    envelope = _prepare(inputs)
    body = envelope['registration']
    if change == 'recorded_toolchain':
        body['render_spec']['agentic_toolchain'] = tools.toolchain()
    else:
        selected = deepcopy(inputs['runtime'])
        selected['limits_basis'] = 'changed runtime identity'
        inputs['runtime_path'].write_bytes(c.canonical(selected))
    with pytest.raises(ValueError):
        producer.verify_preparer(c.canonical(envelope), job_id=body['job_id'])


def test_d76_input_mutation_still_refuses_before_hook(inputs, monkeypatch):
    select_runtime(inputs, True)
    post_init = api.RunSpec.__post_init__
    def mutate_after_construction(spec):
        # The frozen constructor does not yet select D76 for shared-v1.
        # Select its public opt-in before construction; never reset a binding.
        spec.registered_input_paths = True
        post_init(spec)
        spec.bundle = spec.bundle.parent / 'changed-bundle.txt'
    monkeypatch.setattr(api.RunSpec, '__post_init__', mutate_after_construction)
    monkeypatch.setattr(api, 'resolve_prompt', lambda *a: pytest.fail('mutated D76 input rendered'))
    with pytest.raises(ValueError, match='input|binding|path|construct'):
        _prepare(inputs)


@pytest.mark.parametrize('u4b', [False, True], ids=['historical', 'u4b'])
def test_default_producer_d76_binding_refuses_mutation_before_runtime_or_hook(inputs, u4b):
    """Observe the genuine constructor; never opt in or replace its binding in the test.

    The installed U1 private composition supplies the real protected hook bodies.
    This regression separately establishes the default producer's D76 selection,
    which the older public-opt-in regression above cannot establish.
    """
    select_runtime(inputs, u4b)
    original = sys.getprofile()
    constructed, checked, enumerated = [], [], []
    before = _files(inputs['root']), _entries(inputs['root'])

    def observe(frame, event, argument):
        if original is not None:
            original(frame, event, argument)
        if event == 'call' and frame.f_code is tools.toolchain.__code__:
            enumerated.append(frame.f_locals['native_shared'])
        if (event == 'return' and frame.f_code.co_name == '__init__'
                and frame.f_back is not None
                and frame.f_back.f_code is producer.prepare.__code__):
            spec = frame.f_locals.get('self')
            if type(spec) is api.RunSpec:
                assert spec.registered_input_paths is True
                assert api._input_binding(spec).spellings is not None
                assert spec._native_shared_runtime_capture is None
                constructed.append(spec)
                spec.bundle = spec.bundle.with_name('unbound-default-native-producer.txt')
        if event != 'call' or not constructed:
            return
        if frame.f_code is api._require_registered_input_spellings.__code__:
            assert frame.f_locals['spec'] is constructed[-1]
            checked.append(frame.f_locals['spec'])
        if frame.f_code.co_name in ('instruction', 'render_spec', 'input_identity'):
            if frame.f_locals.get('self') is constructed[-1]:
                pytest.fail('default native input mutation escaped its entry guard')

    sys.setprofile(observe)
    try:
        with pytest.raises(ValueError, match='registered input spelling changed after construction'):
            _prepare(inputs)
    finally:
        sys.setprofile(original)
    assert len(constructed) == 1
    assert checked == constructed
    assert constructed[0]._native_shared_runtime_capture is None
    assert constructed[0]._native_shared_max_draft_checks is None
    assert enumerated == [False]  # Constructor only; D114 was never reached.
    assert (_files(inputs['root']), _entries(inputs['root'])) == before


@pytest.mark.parametrize('u4b', [False, True], ids=['historical', 'u4b'])
def test_genuine_composition_and_d_reconstruction_roster(inputs, u4b):
    select_runtime(inputs, u4b)
    envelope = _prepare(inputs)
    raw = c.canonical(envelope)
    instruction = inputs['root'] / 'instruction.md'
    instruction.write_text(envelope['registration']['instruction'])
    selected = composition.compose(raw, instruction_path=instruction)
    rebuilt, spec, _ = composition.reconstruct_composition(c.canonical(selected))
    assert rebuilt == selected
    assert spec._agentic_toolchain == tools.toolchain(native_shared=u4b)
    with controls.loaded_controls(selected['dependencies']) as projection, \
            authority.loaded_verified_package_module('data_sheets_schema.native_shared_registration',
                package_sources=selected['dependencies']['base']['package_sources']) as consumer:
        actual, recovered, _, _ = consumer._selection(c.canonical(selected),
            preparation_raw=raw, classifier_projection=projection)
        assert actual == selected
        assert recovered._agentic_toolchain == tools.toolchain(native_shared=u4b)
        # Alter a genuine captured composition, including its preparation copy.
        # Neither live C reconstruction nor D may accept an interchanged roster.
        altered = deepcopy(selected)
        alternate = tools.toolchain(native_shared=not u4b)
        changed_preparation = deepcopy(envelope)
        changed_preparation['registration']['render_spec']['agentic_toolchain'] = alternate
        changed_raw = c.canonical(changed_preparation)
        altered['render_spec']['agentic_toolchain'] = alternate
        altered['preparation_raw_json'] = changed_raw.decode()
        altered['preparation_sha256'] = c.sha(changed_raw)
        with pytest.raises(ValueError):
            consumer._selection(c.canonical(altered), preparation_raw=changed_raw,
                                classifier_projection=projection)
    with pytest.raises(ValueError):
        composition.reconstruct_composition(c.canonical(altered))
