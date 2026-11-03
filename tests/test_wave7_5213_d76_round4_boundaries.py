"""PR #5213 round-four public RunSpec boundary regressions (2026-11-02).

Inputs: real constructed synthetic API/native specs and literal saved render
specs. Outputs: owned temporary requests/registrations only. The four negative
phase/native cases preserve the independent Codex review witnesses; rendering
and valid-spec controls protect the scanner-compatible guard relocation.
"""
from dataclasses import replace
from pathlib import Path

import pytest

from data_sheets_schema import api_runner as api
from data_sheets_schema import native_attribution_registration as native
from data_sheets_schema import shared_generation as shared
from tests.test_generation_manifest_identity import external, snapshot  # noqa: F401
from tests.test_native_source_attribution import case  # noqa: F401
from tests.test_shared_generation_runtime import offline  # noqa: F401
from tests.test_shared_generation_selection import registration_for, selected_spec
from tests.test_source_attribution_preflight import inputs  # noqa: F401


def _trap(reached, name):
    def refused(*args, **kwargs):
        reached.append(name)
        raise AssertionError('later boundary reached before D76: ' + name)
    return refused


def test_public_phase_builder_refuses_before_shared_authority(external, monkeypatch):
    monkeypatch.chdir(external.bundle.parent)
    spec = selected_spec(external, registration_for(external))
    spec.bundle = Path(spec.bundle.name)
    before = snapshot(external.bundle.parent)
    reached = []
    monkeypatch.setattr(shared, 'assert_current', _trap(reached, 'shared-authority'))
    monkeypatch.setattr(api, '_exclusive_run', _trap(reached, 'lock'))
    monkeypatch.setattr(api, '_restore_resume_date', _trap(reached, 'date'))
    error = None
    try:
        api.build_phase(spec, 'full', carry={})
    except BaseException as exc:
        error = exc
    assert reached == [], (reached, repr(error))
    assert snapshot(external.bundle.parent) == before
    assert isinstance(error, ValueError) and 'registered input' in str(error), repr(error)


def test_public_phase_builder_does_not_mix_changed_bundle_with_cached_instruction(external):
    spec = replace(external, registered_input_paths=True)
    frozen = spec.instruction
    original = spec.bundle
    changed = original.with_name('changed-bound-input.txt')
    marker = 'DIFFERENT_BOUND_INPUT_SENTINEL'
    changed.write_text(marker + '\n')
    spec.bundle = changed
    before = snapshot(original.parent)
    error, request = None, None
    try:
        request = api.build_phase(spec, 'full', carry={})
    except BaseException as exc:
        error = exc
    if request is not None:
        print('MIXED_REQUEST_RETURNED', marker in repr(request),
              'instruction_still_original', spec.instruction == frozen,
              'original_path_in_instruction', str(original) in frozen)
    assert snapshot(original.parent) == before
    assert request is None, 'public build_phase returned a request after a bound bundle changed'
    assert isinstance(error, ValueError) and 'registered input' in str(error), repr(error)


@pytest.mark.parametrize('entry', ['registration', 'write_registration'])
def test_native_registration_refuses_drift_before_reading_input_pins(
    case, monkeypatch, tmp_path, entry,
):
    spec = case[0]
    monkeypatch.chdir(spec.bundle.parent)
    assert 'instruction' in vars(spec), 'calibrate a normal already-rendered spec'
    spec.bundle = Path(spec.bundle.name)
    reached = []
    monkeypatch.setattr(native, '_inputs', _trap(reached, 'input-pin-read'))
    destination = tmp_path / 'must-not-publish.json'
    before = snapshot(tmp_path)
    error = None
    try:
        if entry == 'registration':
            native.registration(spec)
        else:
            native.write_registration(spec, destination)
    except BaseException as exc:
        error = exc
    assert reached == [], (reached, repr(error))
    assert not destination.exists()
    assert snapshot(tmp_path) == before
    assert isinstance(error, ValueError) and 'registered input' in str(error), repr(error)


@pytest.mark.parametrize('entry', ['resolve_prompt', 'instruction'])
def test_public_rendering_refuses_drift_before_prompt_or_input_reads(
    external, monkeypatch, entry,
):
    spec = replace(external, registered_input_paths=True)
    assert 'instruction' not in vars(spec)
    spec.bundle = spec.bundle.with_name('unbound-input.txt')
    before = snapshot(external.bundle.parent)
    reached = []
    error = None
    with monkeypatch.context() as patched:
        patched.setattr(api, 'prompt_body', _trap(reached, 'prompt-body'))
        patched.setattr(Path, 'read_bytes', _trap(reached, 'input-bytes'))
        patched.setattr(Path, 'read_text', _trap(reached, 'input-text'))
        try:
            if entry == 'resolve_prompt':
                api.resolve_prompt(spec)
            else:
                spec.instruction
        except BaseException as exc:
            error = exc
    assert reached == [], (reached, repr(error))
    assert 'instruction' not in vars(spec)
    assert snapshot(external.bundle.parent) == before
    assert isinstance(error, ValueError) and 'registered input' in str(error), repr(error)


@pytest.mark.parametrize('historical', [False, True])
def test_valid_phase_inspection_preserves_bound_inputs_and_literal_instruction(external, historical):
    fresh = replace(external, registered_input_paths=True)
    instruction = fresh.instruction
    spec = (api.RunSpec.from_render_spec(fresh.render_spec(), project=fresh.project,
                                        method=fresh.method, label=fresh.label)
            if historical else fresh)
    before = snapshot(external.bundle.parent)
    request = api.build_phase(spec, 'full', carry={})
    assert request.phase == 'full'
    assert spec.instruction == instruction
    assert any(block.get('text') == instruction for block in request.messages[0]['content'])
    assert external.bundle.read_text() in request.cached_blocks[1]['text']
    assert snapshot(external.bundle.parent) == before
    assert not external.out_dir.exists()
    if historical:
        assert spec._replay_only is True
        with pytest.raises(ValueError, match='replay'):
            api.execute(spec)


@pytest.mark.parametrize('entry', ['registration', 'write_registration'])
def test_unchanged_native_spec_retains_valid_registration_and_exclusive_write(case, tmp_path, entry):
    spec, recorded, _ = case
    if entry == 'registration':
        assert native._encoded(native.registration(spec)) == recorded
    else:
        destination = tmp_path / 'new-registration.json'
        result = native.write_registration(spec, destination)
        assert result['path'] == str(destination)
        assert destination.read_bytes() == recorded
        assert destination.stat().st_size > 0
        with pytest.raises(FileExistsError):
            native.write_registration(spec, destination)
        assert destination.read_bytes() == recorded


def test_literal_historical_rendering_retains_recorded_spelling(external):
    fresh = replace(external, registered_input_paths=True)
    instruction = fresh.instruction
    recorded = fresh.render_spec()
    replay = api.RunSpec.from_render_spec(recorded, project=fresh.project,
                                         method=fresh.method, label=fresh.label)
    assert replay._replay_only is True
    assert replay.render_spec() == recorded
    assert api.resolve_prompt(replay) == instruction
    assert replay.instruction == instruction
