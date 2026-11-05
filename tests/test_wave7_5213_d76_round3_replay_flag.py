"""R3-G1: mutable replay flags cannot erase fresh input authority (#5213).

Inputs: synthetic local registrations; outputs: refusal/no-write assertions.
Separate from the frozen first round-three module for a paired 0fa baseline.
2026-11-02. Offline only; no provider calls.
"""
from dataclasses import replace
import importlib

from click.testing import CliRunner
import pytest

from data_sheets_schema import api_runner as api, receipt_completion, shared_generation as sg
from data_sheets_schema.cli import cli
from tests.test_generation_manifest_identity import external  # noqa: F401
from tests.test_shared_generation_runtime import offline  # noqa: F401
from tests.test_shared_generation_selection import registration_for, selected_spec
from tests.test_wave7_5213_d76_round2_binding import _tree


@pytest.mark.parametrize('shared', [False, True])
@pytest.mark.parametrize('entry', ['plan', 'resolve-prompt', 'render-prompt'])
def test_fresh_registered_spec_cannot_become_literal_replay_by_flag_mutation(
        external, monkeypatch, shared, entry):
    monkeypatch.chdir(external.bundle.parent)
    spec = (selected_spec(external, registration_for(external)) if shared else
            replace(external, condition='generic_v8', registered_input_paths=True))
    # A usable API replay needs the header values captured while still fresh;
    # otherwise a separate missing-header refusal masks the flag bypass.
    spec.bind_api_header_values(api._model_settings(spec.condition))
    original = spec.bundle
    alias = original.with_name('replay-alias-' + original.name)
    alias.symlink_to(original)
    spec.bundle = alias
    spec._replay_only = True
    authorities = []

    def forbidden(*args, **kwargs):
        authorities.append('authority/receipt')
        raise AssertionError('mutable replay flag skipped the input-integrity boundary')

    monkeypatch.setattr(sg, 'capture', forbidden)
    monkeypatch.setattr(sg, 'assert_current', forbidden)
    monkeypatch.setattr(receipt_completion, 'registration', forbidden)
    module = importlib.import_module('data_sheets_schema.cli.api')
    monkeypatch.setattr(module, '_spec', lambda *args, **kwargs: spec)
    output = external.bundle.parent / 'must-not-render.txt'
    before = _tree(external.bundle.parent)
    result, error = None, None
    try:
        if entry == 'plan':
            api.plan(spec)
        elif entry == 'resolve-prompt':
            api.resolve_prompt(spec)
        else:
            result = CliRunner().invoke(cli, ['api', 'render-prompt', '--project', spec.project,
                '--label', spec.label, '--bundle', str(original), '--out', str(output)])
    except BaseException as exc:
        error = exc
    assert authorities == [], (authorities, error, result)
    assert not output.exists()
    assert _tree(external.bundle.parent) == before
    if result is None:
        assert isinstance(error, ValueError), repr(error)
        diagnostic = str(error)
    else:
        assert result.exit_code != 0, result.output
        diagnostic = result.output
    assert 'registered input' in diagnostic and 'replay' in diagnostic
