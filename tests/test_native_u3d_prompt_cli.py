"""The offline native render CLI consumes genuine U3-A preparation only."""
from pathlib import Path

import pytest
from click.testing import CliRunner

from data_sheets_schema import native_execution_registration_v2 as preparation
from data_sheets_schema.cli.prompt import render_native_shared
from tests.test_native_execution_registration_v2 import inputs, isolated_modules
from tests.test_native_shared_render import native_spec
from tests.test_native_shared_selection import declaration


def argv(inputs, out):
    return ['--selection', str(inputs['selection']), '--runtime-declaration', str(inputs['runtime_path']),
        '--job-id', inputs['kwargs']['job_id'], '--run-date', inputs['kwargs']['run_date'],
        '--max-draft-checks', str(inputs['kwargs']['max_draft_checks']),
        '--provider', inputs['runtime']['provider'], '--reasoning-effort', inputs['runtime']['effort'],
        '--out', str(out)]


def test_actual_v2_cli_renders_exact_preparation_to_new_file(inputs):
    expected = preparation.prepare(inputs['selection'], inputs['runtime_path'], **inputs['kwargs'])
    out = inputs['root'] / 'instruction.md'
    result = CliRunner().invoke(render_native_shared, argv(inputs, out))
    assert result.exit_code == 0, result.output
    assert out.read_bytes() == expected['registration']['instruction'].encode('utf-8')
    assert expected['registration']['instruction_sha256'] in result.output
    assert 'Offline v2 preparation' in result.output
    before = out.read_bytes()
    repeated = CliRunner().invoke(render_native_shared, argv(inputs, out))
    assert repeated.exit_code != 0
    assert out.read_bytes() == before
    assert all(Path(call[0]).name == 'git' for call in inputs['calls'])


@pytest.mark.parametrize('option', ['--provider', '--reasoning-effort'])
def test_v2_cli_conflicting_runtime_option_refuses_before_write(inputs, option):
    out = inputs['root'] / 'not-created.md'
    args = argv(inputs, out)
    args[args.index(option) + 1] = 'foreign'
    result = CliRunner().invoke(render_native_shared, args)
    assert result.exit_code != 0
    assert 'differ from the sole runtime declaration' in result.output
    assert not out.exists()
