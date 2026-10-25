"""Offline CLI wiring; the controller's runtime admission is tested separately."""
import sys
from types import ModuleType

import pytest
from click.testing import CliRunner

from data_sheets_schema.cli.prompt import prompt
from data_sheets_schema import native_shared_render as native
from tests.test_native_shared_render import native_spec
from tests.test_native_shared_selection import declaration


@pytest.fixture
def command(native_spec, tmp_path, monkeypatch):
    spec = native_spec
    runtime = tmp_path / 'runtime.json'
    runtime.write_bytes(spec._native_shared_runtime_capture.raw)
    module = ModuleType('data_sheets_schema.native_shared_controller')
    calls = []

    def bind_runtime(selected, runtime_path, allowance):
        calls.append((selected, runtime_path, allowance))
        selected._native_shared_runtime_capture = spec._native_shared_runtime_capture
        selected._native_shared_max_draft_checks = allowance
        native.metadata(selected)
        return selected

    module.bind_runtime = bind_runtime
    monkeypatch.setitem(sys.modules, module.__name__, module)
    args = ['render-native-shared', '--selection', spec._native_shared_generation_capture.registration.pin.path,
        '--runtime-declaration', str(runtime), '--provider', spec.provider,
        '--reasoning-effort', spec.reasoning_effort, '--max-draft-checks', '2',
        '--run-date', spec.run_date]
    return args, calls, module


def test_offline_cli_uses_selected_inputs_and_explicit_runtime_binding(command, native_spec):
    args, calls, _ = command
    result = CliRunner().invoke(prompt, args)
    assert result.exit_code == 0, result.output
    assert len(calls) == 1 and calls[0][2] == 2
    selected = calls[0][0]
    assert selected.render_version == 26 and selected.native_shared_generation_version == 1
    assert selected._native_shared_generation_capture.registration == native_spec._native_shared_generation_capture.registration
    assert selected.instruction in result.output
    assert 'Offline rendering only' in result.output
    assert '--native-shared-selection' in result.output


def test_output_is_new_file_only_and_cannot_occupy_stage_roles(command, native_spec, tmp_path):
    args, _, _ = command
    output = tmp_path / 'instruction.txt'
    first = CliRunner().invoke(prompt, [*args, '--out', str(output)])
    assert first.exit_code == 0, first.output
    raw = output.read_bytes()
    second = CliRunner().invoke(prompt, [*args, '--out', str(output)])
    assert second.exit_code != 0 and output.read_bytes() == raw
    stage_output = native_spec._native_shared_generation_capture.role('phase1_full')
    third = CliRunner().invoke(prompt, [*args, '--out', stage_output])
    assert third.exit_code != 0 and 'outside the mutable native stage root' in third.output


def test_runtime_binding_refusal_cannot_publish_instruction(command, tmp_path):
    args, _, module = command
    def refuse(*args):
        raise ValueError('runtime capture differs from its declaration')
    module.bind_runtime = refuse
    output = tmp_path / 'refused-instruction.txt'
    result = CliRunner().invoke(prompt, [*args, '--out', str(output)])
    assert result.exit_code != 0 and 'runtime capture differs' in result.output
    assert not output.exists()


@pytest.mark.parametrize('option', ['--selection', '--runtime-declaration', '--provider',
    '--reasoning-effort', '--max-draft-checks', '--run-date'])
def test_native_cli_has_no_implicit_selected_input_defaults(command, option):
    args, calls, _ = command
    index = args.index(option)
    result = CliRunner().invoke(prompt, args[:index] + args[index + 2:])
    assert result.exit_code != 0 and option in result.output
    assert calls == []
