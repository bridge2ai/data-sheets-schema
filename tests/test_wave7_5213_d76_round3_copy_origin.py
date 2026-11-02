"""D76 round 3: copied/restored specs cannot invent literal replay origin.

Inputs: local explicit/SG1 registrations and the existing native saved-trace
fixture. Outputs: refusal/no-authority/no-write and replay compatibility
assertions for PR #5213. Freeze unchanged before production repair.
2026-11-02. Offline only; no provider calls or SG2 execution.
"""
import copy
from dataclasses import replace
import importlib
import pickle

from click.testing import CliRunner
import pytest

from data_sheets_schema import api_runner as api, receipt_completion, shared_generation as sg
from data_sheets_schema.cli import cli
from tests.test_generation_manifest_identity import external  # noqa: F401
from tests.test_shared_generation_runtime import offline  # noqa: F401
from tests.test_shared_generation_selection import registration_for, selected_spec
from tests.test_wave7_5213_d76_round2_binding import _trap_client, _tree
from tests.test_native_attribution_results import prepare, trace  # noqa: F401


def _fresh(external, monkeypatch, *, shared=False):
    monkeypatch.chdir(external.bundle.parent)
    spec = (selected_spec(external, registration_for(external)) if shared else
            replace(external, condition='generic_v8', registered_input_paths=True))
    # Otherwise missing API replay headers mask the origin bypass.
    spec.bind_api_header_values(api._model_settings(spec.condition))
    return spec


def _clone(spec, kind):
    if kind == 'deepcopy':
        return copy.deepcopy(spec)
    return pickle.loads(pickle.dumps(spec, protocol=pickle.HIGHEST_PROTOCOL))


@pytest.mark.parametrize('kind', ['deepcopy', 'pickle'])
@pytest.mark.parametrize('shared', [False, True])
@pytest.mark.parametrize('entry', ['plan', 'resolve-prompt', 'render-prompt'])
def test_restored_fresh_spec_cannot_claim_replay_to_bypass_entry_checks(
        external, monkeypatch, kind, shared, entry):
    spec = _fresh(external, monkeypatch, shared=shared)
    original = spec.bundle
    alias = original.with_name('copy-origin-alias-' + original.name)
    alias.symlink_to(original)
    fake, reached = _trap_client(spec, monkeypatch)
    authorities = []

    def forbidden(*args, **kwargs):
        authorities.append('authority/receipt/lock')
        raise AssertionError('copied fresh spec bypassed its input-origin boundary')

    monkeypatch.setattr(sg, 'capture', forbidden)
    monkeypatch.setattr(sg, 'assert_current', forbidden)
    monkeypatch.setattr(receipt_completion, 'registration', forbidden)
    monkeypatch.setattr(api, '_exclusive_run', forbidden)
    module = importlib.import_module('data_sheets_schema.cli.api')
    output = external.bundle.parent / 'must-not-render-copy.txt'
    before = _tree(external.bundle.parent)
    result, error = None, None
    try:
        # A pickle restoration may itself refuse its unproved origin. This is
        # an allowed fail-closed outcome; it must not establish new authority.
        cloned = _clone(spec, kind)
        cloned.bundle = alias
        cloned._replay_only = True
        # Historical execution refusal must retain precedence even for an
        # object that cannot be admitted for inspection as genuine replay.
        with pytest.raises(ValueError, match='historical prompt replay cannot execute'):
            api.execute(cloned, client=fake)
        monkeypatch.setattr(module, '_spec', lambda *args, **kwargs: cloned)
        if entry == 'plan':
            api.plan(cloned)
        elif entry == 'resolve-prompt':
            api.resolve_prompt(cloned)
        else:
            result = CliRunner().invoke(cli, ['api', 'render-prompt',
                '--project', cloned.project, '--label', cloned.label,
                '--bundle', str(original), '--out', str(output)])
    except BaseException as exc:
        error = exc
    assert authorities == [], (authorities, error, result)
    assert reached == {'count': [], 'create': []}
    assert not output.exists()
    assert _tree(external.bundle.parent) == before
    if result is None:
        assert isinstance(error, ValueError), repr(error)
        diagnostic = str(error)
    else:
        assert result.exit_code != 0, result.output
        diagnostic = result.output
    assert 'registered input' in diagnostic or 'construction origin' in diagnostic


@pytest.mark.parametrize('mutated', [False, True])
def test_deepcopy_preserves_the_fresh_binding_without_recapturing_drift(
        external, monkeypatch, mutated):
    spec = _fresh(external, monkeypatch)
    instruction = spec.instruction
    if mutated:
        alias = spec.bundle.with_name('already-mutated-' + spec.bundle.name)
        alias.symlink_to(spec.bundle)
        spec.bundle = alias
    cloned = copy.deepcopy(spec)
    assert cloned is not spec
    assert cloned.bundle == spec.bundle
    assert cloned._api_header_values == spec._api_header_values
    assert cloned._api_header_values is not spec._api_header_values
    # A copy must not discard or re-render the instruction already supplied.
    assert cloned.instruction == instruction
    if mutated:
        with pytest.raises(ValueError, match='registered input'):
            api._require_registered_input_spellings(cloned)
    else:
        assert api._require_registered_input_spellings(cloned) is None


@pytest.mark.parametrize('copy_kind', ['identity', 'shallow', 'deep', 'replace'])
@pytest.mark.parametrize('origin', ['from-render-spec', 'direct-replay-constructor'])
def test_genuine_replay_construction_and_copies_keep_literal_rendering_nonexecutable(
        external, monkeypatch, origin, copy_kind):
    monkeypatch.chdir(external.bundle.parent)
    if origin == 'from-render-spec':
        fresh = _fresh(external, monkeypatch)
        recorded = fresh.render_spec()
        spec = api.RunSpec.from_render_spec(recorded, project=fresh.project,
                                            method=fresh.method, label=fresh.label)
    else:
        # Match the supported direct-arm constructor used by
        # test_claudecode_direct_arm.py, below artifact/toolchain replay axes.
        spec = api.RunSpec(project=external.project, arm='baseline',
            method='claudecode_direct', bundle=external.bundle, label='synthetic',
            condition='generic_v9', manifest=None, chunk_manifest=None,
            render_version=3, run_date='2026-11-02', runtime='Claude Code (direct)',
            provider='Anthropic (Claude subscription, direct)',
            profile='neutral', profile_basis='synthetic replay fixture', _replay_only=True)
        recorded = spec.render_spec()
    expected = api.resolve_prompt(spec)
    cloned = {'identity': lambda value: value, 'shallow': copy.copy,
              'deep': copy.deepcopy, 'replace': replace}[copy_kind](spec)
    assert cloned._replay_only is True
    if copy_kind == 'replace':
        # replace() reconstructs init fields and legitimately drops recorded
        # init=False API headers. It preserves replay origin/nonexecution,
        # not necessarily enough historical substitutions to render again.
        assert cloned is not spec
        assert api._require_registered_input_spellings(cloned) is None
    else:
        assert cloned.render_spec() == recorded
        assert api.resolve_prompt(cloned) == expected
    with pytest.raises(ValueError, match='historical prompt replay cannot execute'):
        api.execute(cloned, client=object())


def test_genuine_replay_origin_cannot_be_demoted_into_fresh_execution(external, monkeypatch):
    fresh = _fresh(external, monkeypatch)
    replay = api.RunSpec.from_render_spec(fresh.render_spec(), project=fresh.project,
                                         method=fresh.method, label=fresh.label)
    fake, reached = _trap_client(fresh, monkeypatch)
    authorities = []

    def forbidden(*args, **kwargs):
        authorities.append('authority/receipt/lock')
        raise AssertionError('demoted genuine replay reached fresh execution authority')

    monkeypatch.setattr(sg, 'capture', forbidden)
    monkeypatch.setattr(sg, 'assert_current', forbidden)
    monkeypatch.setattr(receipt_completion, 'registration', forbidden)
    monkeypatch.setattr(api, '_exclusive_run', forbidden)
    replay._replay_only = False
    before = _tree(external.bundle.parent)
    with pytest.raises(ValueError, match='registered input|construction origin|historical.*execute'):
        api.execute(replay, client=fake)
    assert authorities == []
    assert reached == {'count': [], 'create': []}
    assert _tree(external.bundle.parent) == before


def test_pickle_metadata_cannot_establish_genuine_replay_origin(external, monkeypatch):
    fresh = _fresh(external, monkeypatch)
    replay = api.RunSpec.from_render_spec(fresh.render_spec(), project=fresh.project,
                                         method=fresh.method, label=fresh.label)
    fake, reached = _trap_client(fresh, monkeypatch)
    authorities = []

    def forbidden(*args, **kwargs):
        authorities.append('authority/receipt/lock')
        raise AssertionError('pickle metadata established replay authority')

    monkeypatch.setattr(sg, 'capture', forbidden)
    monkeypatch.setattr(sg, 'assert_current', forbidden)
    monkeypatch.setattr(receipt_completion, 'registration', forbidden)
    monkeypatch.setattr(api, '_exclusive_run', forbidden)
    before = _tree(external.bundle.parent)
    error = None
    try:
        restored = _clone(replay, 'pickle')
        assert restored._replay_only is True
        with pytest.raises(ValueError, match='historical prompt replay cannot execute'):
            api.execute(restored, client=fake)
        # Serialized substitutions and a true flag alone cannot prove this
        # object passed the literal-replay construction boundary.
        api.resolve_prompt(restored)
    except BaseException as exc:
        error = exc
    assert authorities == [], (authorities, error)
    assert reached == {'count': [], 'create': []}
    assert _tree(external.bundle.parent) == before
    assert isinstance(error, ValueError), repr(error)
    assert 'registered input' in str(error) or 'construction origin' in str(error)


def test_native_saved_capture_keeps_prepared_state_deepcopy_compatible(trace):
    # Exercise the real _saved_draft deepcopy at native_attribution_results.py,
    # using its existing local callback fixture and sealed saved-byte capture.
    from data_sheets_schema import native_attribution_results as results
    prepared = prepare(trace)
    original = prepared['state']
    cloned = copy.deepcopy(original)
    assert cloned is not original and cloned.spec is not original.spec
    assert cloned.spec.render_spec() == original.spec.render_spec()
    report = results.check_capture(prepared)
    assert report['additional_gate_passed'], report['problems']
    assert report['generation_acceptance'] == 'not_assessed'
    assert prepared['state'] is original
