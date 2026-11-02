"""PR #5213/#5212 integration ordering, 2026-11-02.

Inputs: real local RunSpecs, invented registrations and unguarded residue.
Outputs: refusal precedence, zero later-boundary calls and unchanged-tree
assertions. No provider calls. The lead's integration ruling keeps D76 before
main's unchanged combined D68/D69 sequence; inspection does not run it.
"""
from dataclasses import replace
import importlib
import json
from pathlib import Path
import socket
from types import SimpleNamespace

from click.testing import CliRunner
import pytest

from data_sheets_schema import api_runner as api, latch_journal as journal
from data_sheets_schema import output_ownership, receipt_completion, run_lock
from data_sheets_schema import shared_generation as shared, usage_ledger as ledger
from data_sheets_schema.cli import cli
from tests.test_d68_legacy_readonly import tree
from tests.test_generation_manifest_identity import external  # noqa: F401
from tests.test_shared_generation_selection import registration_for, selected_spec


module = importlib.import_module('data_sheets_schema.cli.api')
ROUTES = ('execute-resume', 'execute-fresh', 'dry-resume', 'dry-fresh',
          'plan', 'resolve', 'cli-run', 'cli-plan', 'cli-render',
          'cli-batch', 'cli-batch-dry')


@pytest.fixture(autouse=True)
def offline(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(socket.socket, 'connect',
                        lambda *a, **k: pytest.fail('network is forbidden'))
    monkeypatch.setattr(api, 'provider_identity',
                        lambda: {'provider': None, 'base_url': None, 'key_env': None})


def _plain(external, *, label='order_rep2'):
    return replace(external, method='claudecode_api', label=label,
                   condition='generic_v8', registered_input_paths=True)


def _shared_pair(external):
    result = []
    for index in (1, 2):
        base = replace(external, method='claudecode_api', label=f'order_rep{index}')
        reg = registration_for(base)
        reg['registration_path'] = str(external.bundle.absolute().parent / f'registration-{index}.json')
        reg['registration_id'] = f'invented-ordering-{index}'
        reg['receipt']['coverage_floor'] = {'state': 'registered', 'numerator': 1, 'denominator': 2}
        result.append(selected_spec(base, reg))
    return result


def _residue(spec):
    """An actual unknown writer, not a mocked legacy guard or age claim."""
    path = spec.full_path.parent / f'{spec.project}_unowned_{"d" * 64}.tmp'
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b'unguarded prior writer; inspection only\n')
    assert str(path) in journal._legacy_evidence(spec)
    with pytest.raises(ledger.UsageLedgerError, match='artifacts have no journal'):
        journal.refuse_legacy_execution(spec)
    return path


def _mutate(spec, field):
    original = getattr(spec, field)
    assert original is not None
    alias = Path(original).with_name('ordering-alias-' + Path(original).name)
    alias.symlink_to(original)
    setattr(spec, field, alias)
    assert alias.read_bytes() == Path(original).read_bytes()


def _inventory_witness(monkeypatch):
    """Observe real inventory reads without changing their result or refusal."""
    calls = []

    def observed(name, real):
        def delegated(*args, **kwargs):
            calls.append(name)
            return real(*args, **kwargs)
        return delegated

    for name in ('_legacy_evidence', 'owned_artifacts'):
        monkeypatch.setattr(journal, name, observed(name, getattr(journal, name)))
    return calls


def _traps(monkeypatch, *, inspection=False):
    """Independent witnesses; no guard being tested is mocked or wrapped."""
    names = ('count', 'create', 'client', 'authority', 'owner', 'batch-authority',
             'receipt', 'startup', 'launch-head', 'guarded-launch', 'output-lock',
             'batch-lock', 'date', 'execute-body', 'model', 'prompt-body')
    seen = {name: [] for name in names}
    # A premature inventory whose result is discarded must still be visible;
    # unlike a trap, these spies always execute the actual inventory function.
    seen['inventory'] = _inventory_witness(monkeypatch)

    def trap(name):
        def refused(*args, **kwargs):
            seen[name].append((args, kwargs))
            raise AssertionError(f'ordering reached forbidden boundary: {name}')
        return refused

    for owner, attribute, name in (
            (api, '_client', 'client'), (shared, 'assert_current', 'authority'),
            (output_ownership, 'require_selected_resume_owner', 'owner'),
            (module, '_shared_current', 'batch-authority'),
            (receipt_completion, 'registration', 'receipt'),
            (api, '_startup_checks', 'startup'),
            (journal, 'require_launch_head', 'launch-head'),
            (journal, 'guarded_launch', 'guarded-launch'),
            (api, '_exclusive_run', 'output-lock'), (run_lock, 'acquire', 'batch-lock'),
            (api, '_restore_resume_date', 'date'), (api, '_execute', 'execute-body')):
        monkeypatch.setattr(owner, attribute, trap(name))
    if not inspection:
        monkeypatch.setattr(api, '_model_settings', trap('model'))
        monkeypatch.setattr(api, 'prompt_body', trap('prompt-body'))
    fake = SimpleNamespace(messages=SimpleNamespace(count_tokens=trap('count'), create=trap('create')))
    return seen, fake


def _arguments(route, spec, sibling, output, tmp_path):
    common = ['--project', spec.project, '--label', spec.label,
              '--bundle', str(spec.bundle), '--manifest', str(spec.manifest),
              '--chunk-manifest', str(spec.chunk_manifest)]
    shared_options = []
    if spec.shared_generation_version:
        reg = json.loads(spec.shared_generation_registration)
        shared_options = ['--shared-generation-version', str(spec.shared_generation_version),
                          '--shared-generation-registration', reg['registration_path']]
    if route.startswith('cli-batch'):
        common = ['--projects', spec.project, '--label-prefix', 'order', '--replicates', '2',
                  '--project-bundle', f'{spec.project}={spec.bundle}',
                  '--manifest', str(spec.manifest), '--no-branch-guard', '--yes']
        if shared_options:
            rows = [json.loads(value.shared_generation_registration) for value in (sibling, spec)]
            roster = tmp_path / 'ordering-roster.json'
            roster.write_bytes(shared.canonical({'format': 'shared_generation_batch_roster_v1',
                'registrations': [{'project': value['run']['project'], 'label': value['run']['label'],
                                   'registration_path': value['registration_path']} for value in rows]}))
            shared_options[-1] = str(roster)
        return ['api', 'batch', *common, *shared_options,
                *(['--dry-run'] if route.endswith('-dry') else [])]
    command = {'cli-run': 'run', 'cli-plan': 'plan', 'cli-render': 'render-prompt'}[route]
    return ['api', command, *common, *shared_options,
            *(['--yes'] if command == 'run' else []),
            *(['--out', str(output)] if command == 'render-prompt' else [])]


def _invoke(route, spec, sibling, fake, arguments, monkeypatch):
    if route.startswith('cli-'):
        specs = {value.label: value for value in (sibling, spec)}
        assembled = []

        def selected(*args, **kwargs):
            value = specs[args[2]]
            assembled.append(value.label)
            return value
        monkeypatch.setattr(module, '_spec', selected)
        result = CliRunner().invoke(cli, arguments)
        if route.startswith('cli-batch'):
            assert assembled == [sibling.label, spec.label], (assembled, result.output, result.exception)
        return result.exit_code, result.output + str(result.exception)
    try:
        if route.startswith('execute-'):
            api.execute(spec, resume=route == 'execute-resume', client=fake)
        elif route.startswith('dry-'):
            api.execute(spec, dry_run=True, resume=route == 'dry-resume', client=fake)
        elif route == 'plan':
            api.plan(spec)
        else:
            api.resolve_prompt(spec)
    except Exception as exc:
        return 1, str(exc)
    return 0, 'no refusal'


@pytest.mark.parametrize('route', ROUTES)
@pytest.mark.parametrize('field', ['bundle', 'manifest', 'chunk_manifest'])
def test_d76_precedes_combined_refusal_and_every_later_boundary(
        external, tmp_path, monkeypatch, route, field):
    spec = _plain(external)
    sibling = replace(spec, label='order_rep1')
    # Cache a genuine instruction before ordinary caller mutation.
    spec.bind_api_header_values(api._model_settings(spec.condition))
    instruction = spec.instruction
    _residue(spec)
    _mutate(spec, field)
    output = tmp_path / 'must-not-render.txt'
    arguments = _arguments(route, spec, sibling, output, tmp_path) if route.startswith('cli-') else None
    seen, fake = _traps(monkeypatch)
    before = tree(tmp_path)
    status, message = _invoke(route, spec, sibling, fake, arguments, monkeypatch)
    assert status != 0 and 'registered input spelling changed after construction' in message, message
    assert field in message
    assert all(not values for values in seen.values()), seen
    assert tree(tmp_path) == before
    assert not output.exists()
    assert spec.instruction == instruction


@pytest.mark.parametrize('route', ['execute-resume', 'execute-fresh', 'dry-resume', 'dry-fresh', 'plan', 'resolve',
                                 'cli-run', 'cli-plan', 'cli-render', 'cli-batch', 'cli-batch-dry'])
@pytest.mark.parametrize('competing', ['authority', 'owner'])
def test_d76_precedes_shared_authority_and_owner_refusals(
        external, tmp_path, monkeypatch, route, competing):
    sibling, spec = _shared_pair(external)
    if competing == 'authority':
        context = Path(json.loads(spec.shared_generation_registration)['inputs']['context']['path'])
        context.write_bytes(context.read_bytes() + b'\n')
        with pytest.raises(ValueError, match='authority changed'):
            shared.assert_current(spec)
    else:
        spec.full_path.parent.mkdir(parents=True, exist_ok=True)
        spec.full_path.write_text('id: https://example.invalid/unowned\n')
        resume = route not in ('execute-fresh', 'dry-fresh')
        expected = 'ownership' if resume else 'already spent; no-resume'
        with pytest.raises(ValueError, match=expected):
            output_ownership.require_selected_resume_owner(spec, resume=resume)
    _mutate(spec, 'bundle')
    output = tmp_path / 'must-not-render.txt'
    arguments = _arguments(route, spec, sibling, output, tmp_path) if route.startswith('cli-') else None
    seen, fake = _traps(monkeypatch)
    before = tree(tmp_path)
    status, message = _invoke(route, spec, sibling, fake, arguments, monkeypatch)
    assert status != 0 and 'registered input spelling changed after construction' in message, message
    assert all(not values for values in seen.values()), seen
    assert tree(tmp_path) == before and not output.exists()


@pytest.mark.parametrize('resume', [True, False])
@pytest.mark.parametrize('early', ['replay', 'native', 19, 20, 21, 22, 23, 24])
def test_execution_policy_refusals_still_precede_d76(external, tmp_path, monkeypatch, resume, early):
    spec = _plain(external)
    _mutate(spec, 'bundle')
    if early == 'replay':
        spec._replay_only = True
        expected = 'historical prompt replay cannot execute'
    elif early == 'native':
        spec.native_source_attribution_version = 1
        expected = 'native source attribution is offline-only'
    else:
        spec.render_version = early
        expected = f'renderer {early}'
    seen, fake = _traps(monkeypatch)
    before = tree(tmp_path)
    with pytest.raises(ValueError, match=expected):
        api.execute(spec, resume=resume, client=fake)
    assert all(not values for values in seen.values()), seen
    assert tree(tmp_path) == before


@pytest.mark.parametrize('resume', [True, False])
def test_d76_valid_unshared_spec_preserves_combined_refusal_redaction(
        external, tmp_path, monkeypatch, capsys, resume):
    spec = _plain(external)
    _residue(spec)
    capsys.readouterr()
    assert api._require_registered_input_spellings(spec) is None
    seen, fake = _traps(monkeypatch)
    before = tree(tmp_path)
    with pytest.raises(ledger.UsageLedgerError, match='artifacts have no journal') as caught:
        api.execute(spec, resume=resume, client=fake)
    stderr = capsys.readouterr().err
    assert '(not a resume anchor)' in stderr
    assert 'dddddddd…(unverified, not a resume anchor)' in stderr
    assert 'd' * 64 not in stderr and 'd' * 64 not in str(caught.value)
    assert '_legacy_evidence' in seen['inventory'] and 'owned_artifacts' in seen['inventory']
    assert all(not values for name, values in seen.items() if name != 'inventory'), seen
    assert tree(tmp_path) == before


@pytest.mark.parametrize('historical', [False, True])
@pytest.mark.parametrize('entry', ['plan', 'resolve', 'cli-render'])
def test_legacy_directory_remains_available_for_nonspending_inspection(
        external, tmp_path, monkeypatch, historical, entry):
    spec = _plain(external)
    spec.bind_api_header_values(api._model_settings(spec.condition))
    expected = api.resolve_prompt(spec)
    _residue(spec)
    if historical:
        spec = api.RunSpec.from_render_spec(spec.render_spec(), project=spec.project,
                                            method=spec.method, label=spec.label)
    output_dir = tmp_path / 'rendered'
    output_dir.mkdir()
    output = output_dir / 'instruction.txt'
    seen, _ = _traps(monkeypatch, inspection=True)
    monkeypatch.setattr(journal, 'refuse_legacy_execution',
                        lambda *a, **k: pytest.fail('inspection ran the execution inventory'))
    before = tree(tmp_path)
    if entry == 'plan':
        value = api.plan(spec)
        assert value['project'] == spec.project and value['phases']
    elif entry == 'resolve':
        assert api.resolve_prompt(spec) == expected
    else:
        monkeypatch.setattr(module, '_spec', lambda *a, **k: spec)
        arguments = _arguments('cli-render', spec, spec, output, tmp_path)
        result = CliRunner().invoke(cli, arguments)
        assert result.exit_code == 0, (result.output, result.exception)
        assert output.read_text() == expected
    assert all(not values for values in seen.values()), seen
    after = tree(tmp_path)
    # Only the explicitly requested rendering output may change; legacy/input
    # paths and their metadata are preserved even when --out is requested.
    assert {key: value for key, value in after.items() if not key.startswith('rendered')} == {
        key: value for key, value in before.items() if not key.startswith('rendered')}


@pytest.mark.parametrize('entry', ['plan', 'cli-render'])
def test_unchanged_shared_inspection_keeps_its_real_authority_checks(
        external, tmp_path, monkeypatch, entry):
    _, spec = _shared_pair(external)
    spec.bind_api_header_values(api._model_settings(spec.condition))
    expected = api.resolve_prompt(spec)
    _residue(spec)
    rendered = tmp_path / 'rendered'
    rendered.mkdir()
    output = rendered / 'shared.txt'
    calls = []

    def forbidden(*args, **kwargs):
        calls.append('execution')
        raise AssertionError('inspection reached execution/client/lock')

    for owner, name in ((api, '_client'), (api, '_execute'), (api, '_exclusive_run'),
                        (run_lock, 'acquire'), (journal, 'refuse_legacy_execution')):
        monkeypatch.setattr(owner, name, forbidden)
    inventories = _inventory_witness(monkeypatch)
    before = tree(tmp_path)
    if entry == 'plan':
        result = api.plan(spec)
        assert result['shared_generation_version'] == 1 and result['phases']
    else:
        monkeypatch.setattr(module, '_spec', lambda *a, **k: spec)
        arguments = _arguments('cli-render', spec, spec, output, tmp_path)
        result = CliRunner().invoke(cli, arguments)
        assert result.exit_code == 0, (result.output, result.exception)
        assert output.read_text() == expected
    assert calls == []
    assert inventories == []
    after = tree(tmp_path)
    assert {key: value for key, value in after.items() if not key.startswith('rendered')} == {
        key: value for key, value in before.items() if not key.startswith('rendered')}
