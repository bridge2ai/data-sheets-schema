"""A3 command routing/refusal, 2026-11-08; explicit producer isolation.

These tests exercise the real CLI's saved-input and intent checks, then stop at
the producer boundary. They are not probe, registration or native acceptance.
"""
import json
from pathlib import Path

import pytest

from data_sheets_schema import native_generation as cli
from data_sheets_schema import native_permission_probe as legacy
from data_sheets_schema import native_u4b_probe_sequence as sequence
from data_sheets_schema import native_u4b_runtime as runtime_module
from tests.test_native_generation_frontdoor import choice_document
from tests.test_native_u4b_runtime import runtime_inputs


@pytest.mark.parametrize('command', ['observation-probe', 'bound-permission-probe'])
@pytest.mark.parametrize('valid_choice', [True, False])
def test_two_phase_cli_binds_supplied_inputs_before_producer(tmp_path, monkeypatch, capsys,
                                                           command, valid_choice):
    initial, arguments = runtime_inputs(tmp_path)
    observation = Path(arguments['observation_probe_path'])
    root = observation.parent.parent
    if command == 'observation-probe':
        runtime_path = root / 'provisional-runtime.json'
        subject = json.loads(runtime_path.read_bytes())
        runtime = subject
        subject_path, option = runtime_path, '--runtime'
    else:
        runtime = runtime_module.prepare_runtime(initial, **arguments)
        subject = {'runtime': runtime, 'scope': 'isolated upstream expectation'}
        subject_path, option = tmp_path / 'expectation.json', '--expectation'
        subject_path.write_bytes(cli.guard.canonical(subject))
    subject_raw = subject_path.read_bytes()
    choice = choice_document(subject_raw, runtime)
    if not valid_choice:
        choice['runtime_sha256'] = '0' * 64
    choice_path = tmp_path / 'choice.json'
    choice_path.write_bytes(cli.guard.canonical(choice))
    authorization_path = root / 'authorization.json'
    authorization_raw = authorization_path.read_bytes()
    calls = []

    def boundary(raw, document):
        assert raw == authorization_raw and document == subject
        calls.append(command)
        result = tmp_path / 'isolated-result.json'
        result.write_bytes(b'{"scope":"routing only, no probe"}')
        return result

    name = 'produce_observation' if command == 'observation-probe' else 'produce_bound_probe'
    monkeypatch.setattr(sequence, name, boundary)
    monkeypatch.setattr(legacy, 'produce_saved_probe', lambda *a, **k: pytest.fail('legacy route invoked'))
    argv = [command, option, str(subject_path), '--authorization', str(authorization_path),
            '--account-choice', str(choice_path)]
    if not valid_choice:
        with pytest.raises(ValueError, match='account choice'):
            cli.main(argv)
        assert calls == []
        assert not (tmp_path / 'isolated-result.json').exists()
    else:
        assert cli.main(argv) == 0
        result = json.loads(capsys.readouterr().out)
        assert calls == [command]
        assert result['command'] == command
        assert result['result']['sha256'] == cli.guard.sha((tmp_path / 'isolated-result.json').read_bytes())
        assert 'not account or launch acceptance' in result['verification_scope']


def test_current_model_cannot_use_unbound_legacy_probe_cli(tmp_path, monkeypatch):
    initial, arguments = runtime_inputs(tmp_path)
    runtime = runtime_module.prepare_runtime(initial, **arguments)
    expected = {'runtime': runtime}
    path = tmp_path / 'expectation.json'
    raw = cli.guard.canonical(expected)
    path.write_bytes(raw)
    choice = tmp_path / 'choice.json'
    choice.write_bytes(cli.guard.canonical(choice_document(raw, runtime)))
    monkeypatch.setattr(legacy, 'require_u4_expectation', lambda value: None)
    monkeypatch.setattr(legacy, 'produce_saved_probe', lambda *a, **k: pytest.fail('unbound current probe ran'))
    with pytest.raises(ValueError, match='authorized observation/bound'):
        cli.main(['permission-probe', '--expectation', str(path), '--account-choice', str(choice),
                  '--output-directory', str(tmp_path / 'forbidden'), '--deadline-seconds', '30'])
    assert not (tmp_path / 'forbidden').exists()
