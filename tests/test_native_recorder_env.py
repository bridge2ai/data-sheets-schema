"""6065: literal environment names keep the registered recorder reproducible."""
import json
import shlex
import hashlib

from click.testing import CliRunner
import pytest
import yaml

from data_sheets_schema.cli import cli
from data_sheets_schema import native_shared_render as render
from data_sheets_schema import native_shared_registration as registration
from data_sheets_schema import native_shared_contract as c
from tests.test_native_shared_selection import artifact
from tests.test_native_shared_render import native_spec, declaration  # noqa: F401
from tests.test_native_registered_provenance import native  # noqa: F401


def env_command(command):
    command = list(command)
    index = command.index('--render-spec-json')
    raw = command[index + 1]
    command[index:index + 2] = ['--render-spec-env', 'D4D_RENDER_SPEC',
        '--render-spec-sha256', hashlib.sha256(raw.encode()).hexdigest()]
    return command, raw


def test_native26_model_line_and_controller_environment(native_spec, tmp_path):
    command = render.commands(native_spec)['recorder']
    line = shlex.join(command)
    assert '--render-spec-env D4D_RENDER_SPEC' in line
    assert '--render-spec-json' not in line and '${' not in line
    assert line in native_spec.instruction
    config = tmp_path / 'attempt' / 'config'
    runtime = {'environment': {'HOME': str(tmp_path / 'home'),
        'BASH_DEFAULT_TIMEOUT_MS': '600000', 'BASH_MAX_TIMEOUT_MS': '600000', 'PYSTOW_HOME': str(config.parent / 'helper-cache')}}
    env = registration.environment(runtime, {'instruction_path': str(tmp_path / 'instruction')}, native_spec, config)
    assert json.loads(env['D4D_RENDER_SPEC']) == native_spec.render_spec()
    captured = native_spec._native_shared_runtime_capture
    changed = c.strict_json(captured.raw)
    changed['limits_basis'] = "owner's synthetic declaration"
    native_spec._native_shared_runtime_capture = artifact('runtime_declaration', captured.pin.path, c.canonical(changed))
    changed_command = render.commands(native_spec)['recorder']
    digest_index = command.index('--render-spec-sha256') + 1
    assert changed_command[digest_index] != command[digest_index]
    assert changed_command[:digest_index] == command[:digest_index]
    assert changed_command[digest_index + 1:] == command[digest_index + 1:]
    assert "owner's" not in shlex.join(changed_command)
    (tmp_path / 'recorder-line.txt').write_text(line + '\n')
    (tmp_path / 'recorder-line-length.json').write_text(json.dumps({'characters': len(line), 'bytes': len(line.encode())}))


def test_public_recorder_reads_env_and_preserves_registered_spec(native, monkeypatch):
    spec, sent, original = native
    command, raw = env_command(original)
    monkeypatch.setenv('D4D_RENDER_SPEC', raw)
    result = CliRunner().invoke(cli, command)
    assert result.exit_code == 0, (result.output, result.exception)
    saved = yaml.safe_load(spec.provenance_path.read_text())
    assert saved['prompts']['request']['spec'] == spec.render_spec()
    assert spec.provenance_path.stat().st_size > 0


@pytest.mark.parametrize('rehash_command', [False, True])
def test_native26_hidden_runtime_change_cannot_match_saved_instruction(native_spec, tmp_path, monkeypatch, rehash_command):
    command = list(render.commands(native_spec)['recorder'][3:])
    instruction = tmp_path / 'registered-instruction.txt'
    instruction.write_text(native_spec.instruction)
    recorded = native_spec.render_spec()
    runtime = recorded['native_shared_runtime_declaration']
    value = json.loads(runtime['raw_json'])
    value['limits_basis'] = 'coherently altered non-header runtime declaration'
    runtime['raw_json'] = c.canonical(value).decode()
    runtime['sha256'] = c.sha(runtime['raw_json'].encode())
    raw = c.canonical(recorded)
    monkeypatch.setenv('D4D_RENDER_SPEC', raw.decode())
    monkeypatch.setenv('D4D_LAUNCH_INSTRUCTION', str(instruction))
    if rehash_command:
        command[command.index('--render-spec-sha256') + 1] = c.sha(raw)
    result = CliRunner().invoke(cli, command)
    assert result.exit_code != 0
    expected = ('does not reproduce the supplied instruction' if rehash_command
                else 'differs from --render-spec-sha256')
    assert expected in result.output
    assert not native_spec.provenance_path.exists()


@pytest.mark.parametrize('mutation', ['missing', 'empty', 'whitespace', 'altered', 'malformed', 'foreign_name', 'both', 'missing_digest', 'wrong_digest'])
def test_spec_environment_refuses_before_publication(native, monkeypatch, mutation):
    spec, sent, original = native
    command, raw = env_command(original)
    if mutation == 'missing':
        monkeypatch.delenv('D4D_RENDER_SPEC', raising=False)
    else:
        value = raw
        if mutation == 'empty': value = ''
        if mutation == 'whitespace': value = '  '
        if mutation == 'malformed': value = '{'
        if mutation == 'altered':
            value = json.loads(raw)
            value['render_version'] = 7
            value = json.dumps(value)
        monkeypatch.setenv('D4D_RENDER_SPEC', value)
    if mutation == 'foreign_name':
        command[command.index('--render-spec-env') + 1] = 'PRIVATE_SECRET'
        monkeypatch.setenv('PRIVATE_SECRET', 'must never be exposed')
    if mutation == 'both':
        command += ['--render-spec-json', raw]
    if mutation == 'missing_digest':
        i = command.index('--render-spec-sha256')
        del command[i:i + 2]
    if mutation == 'wrong_digest':
        command[command.index('--render-spec-sha256') + 1] = '0' * 64
    result = CliRunner().invoke(cli, command)
    assert result.exit_code != 0
    if mutation in ('missing', 'empty', 'whitespace'):
        assert 'D4D_RENDER_SPEC is not set' in result.output
    if mutation == 'foreign_name':
        assert 'accepts only D4D_RENDER_SPEC' in result.output
    if mutation == 'both':
        assert 'are exclusive' in result.output
    assert 'must never be exposed' not in result.output
    assert not spec.provenance_path.exists()
