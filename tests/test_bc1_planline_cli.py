"""BC1 plan display at actual CLI boundaries; no provider execution."""
import json
from dataclasses import replace
from types import SimpleNamespace

from click.testing import CliRunner
import pytest

from data_sheets_schema import api_runner as api, run_lock, shared_generation as sg
from data_sheets_schema.cli import cli
from tests.test_bc1_selection import registered, simulated_hooks  # noqa: F401
from tests.test_generation_manifest_identity import external as external_fixture
from tests.test_shared_generation_cli import module, offline, roster, batch  # noqa: F401


@pytest.fixture
def external(tmp_path):
    return replace(external_fixture.__wrapped__(tmp_path), method='claudecode_api')


@pytest.fixture
def fake_client(monkeypatch):
    def forbidden(**kwargs):
        pytest.fail('plan display dispatched a provider request')
    client = SimpleNamespace(messages=SimpleNamespace(create=forbidden))
    monkeypatch.setattr(api, '_client', lambda: client)
    return client


def assert_bc1_output(output, spec):
    plan = api.plan(spec)
    assert f"bounded-carry version {plan['bounded_carry']['version']}; fan-in {plan['bounded_carry']['fan_in']}" in output
    assert 'registered maximum roster: ' + json.dumps(plan['registered_maximum_roster'], sort_keys=True) in output
    assert 'explicit audit allowances: ' + json.dumps(plan['registered_audit_allowances'], sort_keys=True) in output
    assert '"aggregate_input_tokens":' in output
    assert 'full-request estimate unavailable for BC1 plans until the full record exists' in output
    assert 'full request ~' not in output


@pytest.mark.parametrize('dry_run', [True, False])
def test_bc1_batch_prints_real_plan(registered, fake_client, monkeypatch, dry_run):
    reg = json.loads(registered.shared_generation_registration)
    path, _ = roster(registered, reg, count=1, pending=True)
    seen = []
    released = []
    def execute(spec):
        seen.append(spec)
        raise ValueError('offline execution boundary reached')
    monkeypatch.setattr(api, 'execute', execute)
    monkeypatch.setattr(run_lock, 'acquire', lambda *a: registered.bundle.parent / 'test-lock')
    monkeypatch.setattr(run_lock, 'release', released.append)
    result = batch(reg, path, count=1, extra=('--dry-run',) if dry_run else ())
    assert result.exit_code == (0 if dry_run else 1), (result.output, result.exception)
    assert_bc1_output(result.output, registered)
    assert len(seen) == (0 if dry_run else 1)
    assert len(released) == (0 if dry_run else 1)
    if not dry_run:
        assert 'offline execution boundary reached' in result.output


@pytest.mark.parametrize('command', ['run', 'plan'])
def test_bc1_single_prints_real_plan(registered, fake_client, monkeypatch, command):
    reg = json.loads(registered.shared_generation_registration)
    seen = []
    def execute(spec):
        seen.append(spec)
        raise ValueError('offline execution boundary reached')
    monkeypatch.setattr(api, 'execute', execute)
    result = CliRunner().invoke(cli, ['api', command, '--project', registered.project,
        '--label', registered.label, '--shared-generation-version', '1',
        '--shared-generation-registration', reg['registration_path'],
        *(['--yes'] if command == 'run' else [])])
    assert result.exit_code == (1 if command == 'run' else 0), (result.output, result.exception)
    assert_bc1_output(result.output, registered)
    assert len(seen) == (1 if command == 'run' else 0)
    if command == 'run':
        assert 'offline execution boundary reached' in result.output


def test_legacy_shared_plan_output_is_byte_identical(capsys):
    module._shared_plan_line({'registered_audit_allowances': {'z': 2, 'a': 1},
                              'full_request_approx_input_tokens': 12345})
    assert capsys.readouterr().out == (
        'dynamic total unavailable; explicit audit allowances: {"a": 1, "z": 2}\n'
        '   full request ~12,345 input tokens\n')
