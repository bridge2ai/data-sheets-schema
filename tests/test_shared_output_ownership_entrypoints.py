"""Actual CLI/public execute ownership boundaries; no provider or native calls.

Synthetic live ownership is setup evidence, not a generated completed run.
The full genuine eight-wire resume proof is a separate final integration check.
"""
from contextlib import contextmanager
from copy import deepcopy
from dataclasses import replace
import os
from pathlib import Path
import socket

from click.testing import CliRunner
import pytest

from data_sheets_schema import api_runner as api, run_lock, shared_generation as sg, usage_ledger as ledger
from data_sheets_schema.cli import cli
from tests.test_generation_manifest_identity import external
from tests.test_shared_generation_cli import registered, roster, batch, stub_plan, module
from tests.test_shared_generation_selection import selected_spec
from tests.test_shared_generation_batch_authority import specs_for, authority_bytes


@pytest.fixture(autouse=True)
def offline(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(socket.socket, 'connect', lambda *a, **k: pytest.fail('network forbidden'))
    monkeypatch.setattr(api, 'provider_identity', lambda: {'provider': None, 'base_url': None, 'key_env': None})
    assert Path(api.__file__).resolve().parents[1] == Path(__file__).resolve().parents[1] / 'src'


def live_account(spec, *, label=None, run_date=None):
    identity = ledger.run_identity(spec)
    if label is not None:
        identity['label'] = label
    data = {'version': 1, 'identity': identity, 'generation_id': 'synthetic-generation',
        'accept_legacy': False, 'rows': [], 'input_identity': {}}
    if run_date:
        data['input_identity'] = {'instruction': {'spec': {'run_date': run_date}}}
    ledger._write(spec, data)
    return data


def tree(root):
    result = {}
    for directory, dirs, files in os.walk(root, followlinks=False):
        for name in dirs + files:
            path = Path(directory) / name
            if path.is_symlink():
                result[str(path)] = ('symlink', os.readlink(path))
            elif path.is_file():
                result[str(path)] = ('file', path.read_bytes())
    return result


def assert_preserved(before):
    for name, (kind, value) in before.items():
        path = Path(name)
        if kind == 'symlink':
            assert path.is_symlink() and os.readlink(path) == value
        else:
            assert path.read_bytes() == value


def selected_authorities(spec):
    from data_sheets_schema.resources import resource_path
    result = {Path(path): raw for path, raw in sg.capture(spec).files}
    for name in sg.ASSET_HASHES:
        path = resource_path(name)
        result[path] = path.read_bytes()
    return result


def assert_role_conflict(text):
    # Literal diagnostic at frozen47ce; an unrelated exception is not refusal evidence.
    assert 'conflicting output ownership' in text, text


def no_execution(monkeypatch, *, forbid_locks=True):
    seen = []
    def forbidden(*args, **kwargs):
        seen.append('unexpected execution')
        raise AssertionError('no mutation or transport is allowed')
    from filelock import FileLock
    monkeypatch.setattr(api, '_client', forbidden)
    monkeypatch.setattr(api, '_call_with_usage', forbidden)
    monkeypatch.setattr(api, '_save_progress', forbidden)
    monkeypatch.setattr(api, '_snapshot', forbidden)
    monkeypatch.setattr(api, '_execute', forbidden)
    monkeypatch.setattr(FileLock, 'acquire', forbidden)
    monkeypatch.setattr(run_lock, 'acquire', forbidden)
    monkeypatch.setattr(run_lock, 'release', forbidden)
    monkeypatch.setattr(module, '_write_verdict', forbidden)
    if forbid_locks:
        monkeypatch.setattr(api, '_exclusive_run', forbidden)
    # The inside-lock test exempts only its explicit no-real-lock simulation;
    # all real FileLock, transport and run-publication paths remain trapped.
    return seen


@pytest.mark.parametrize('state', ['foreign', 'unknown', 'own_no_resume'])
def test_public_execute_refuses_existing_unowned_state_before_lock(registered, tmp_path, monkeypatch, state):
    base, reg = registered
    spec = selected_spec(base, reg)
    if state in ('foreign', 'own_no_resume'):
        live_account(spec, label='foreign-run' if state == 'foreign' else None)
    else:
        spec.full_path.parent.mkdir(parents=True)
        spec.full_path.write_text('id: https://example.org/synthetic-unowned\n')
    before = tree(tmp_path)
    authorities = {Path(path): raw for path, raw in sg.capture(spec).files}
    seen = no_execution(monkeypatch)
    expected = {'foreign': 'foreign or unknown ledger ownership',
                'unknown': 'no usable live ownership',
                'own_no_resume': 'already spent; no-resume'}[state]
    with pytest.raises(ValueError, match=expected):
        api.execute(spec, resume=state != 'own_no_resume')
    assert seen == []
    assert tree(tmp_path) == before
    assert {path: path.read_bytes() for path in authorities} == authorities


def test_public_execute_rechecks_owner_inside_lock_before_date_restore(registered, tmp_path, monkeypatch):
    base, reg = registered
    spec = selected_spec(base, reg)
    live_account(spec)
    calls = []
    observed = {}
    @contextmanager
    def acquire(current):
        calls.append('acquired')
        live_account(current, label='changed-during-lock-admission')
        observed.update(tree(tmp_path))
        try:
            yield
        finally:
            calls.append('released')
    monkeypatch.setattr(api, '_exclusive_run', acquire)
    monkeypatch.setattr(api, '_restore_resume_date', lambda *a: pytest.fail('foreign owner reached date restoration'))
    seen = no_execution(monkeypatch, forbid_locks=False)
    with pytest.raises(ValueError, match='foreign or unknown ledger ownership'):
        api.execute(spec)
    assert calls == ['acquired', 'released'] and seen == []
    assert tree(tmp_path) == observed


def test_matching_owner_preserves_actual_automatic_date_recovery(registered, tmp_path, monkeypatch):
    base, reg = registered
    # Final real constructor sets the init=False automatic marker itself.
    spec = replace(selected_spec(base, reg), run_date=api.AUTO)
    assert spec._automatic_run_date == spec.run_date
    live_account(spec, run_date='2001-02-03')
    spec.__dict__['instruction'] = 'cached current-day instruction must be discarded'
    before = tree(tmp_path)
    authorities = selected_authorities(spec)
    observed = []
    def execute(current, *, resume, client):
        observed.append((current.run_date, resume, 'instruction' in current.__dict__))
        return {'boundary': 'reached after real owner checks and actual lock/date recovery'}
    monkeypatch.setattr(api, '_execute', execute)
    monkeypatch.setattr(api, '_client', lambda: pytest.fail('provider client forbidden'))
    result = api.execute(spec)
    assert observed == [('2001-02-03', True, False)]
    assert result['boundary'].startswith('reached')
    assert_preserved(before)
    assert {p: p.read_bytes() for p in authorities} == authorities


def test_legacy_public_boundary_is_unchanged(external, tmp_path, monkeypatch):
    spec = external
    spec.full_path.parent.mkdir(parents=True)
    spec.full_path.write_text('legacy partial bytes without selected ownership\n')
    before = tree(tmp_path)
    seen = []
    monkeypatch.setattr(api, '_execute', lambda current, **kw: seen.append(current) or {'legacy': True})
    assert api.execute(spec) == {'legacy': True}
    assert seen == [spec]
    assert_preserved(before)


def alias_pair(specs):
    for first, second in ((specs[0].full_path.parent, specs[1].full_path.parent),
                          (specs[0].core_path.parent, specs[1].core_path.parent)):
        first.mkdir(parents=True, exist_ok=True)
        second.symlink_to(first.absolute(), target_is_directory=True)


def batch_traps(monkeypatch):
    seen = {'lock': [], 'execute': []}
    def forbidden(*args, **kwargs):
        seen['lock'].append(args)
        raise AssertionError('pair conflict reached batch lock')
    from filelock import FileLock
    monkeypatch.setattr(run_lock, 'acquire', forbidden)
    monkeypatch.setattr(run_lock, 'release', forbidden)
    monkeypatch.setattr(FileLock, 'acquire', forbidden)
    monkeypatch.setattr(api, '_exclusive_run', forbidden)
    monkeypatch.setattr(api, '_client', forbidden)
    monkeypatch.setattr(api, '_call_with_usage', forbidden)
    monkeypatch.setattr(api, '_save_progress', forbidden)
    monkeypatch.setattr(api, '_snapshot', forbidden)
    monkeypatch.setattr(module, '_write_verdict', forbidden)
    monkeypatch.setattr(api, 'execute', lambda spec: seen['execute'].append(spec.label) or pytest.fail('pair conflict reached execute'))
    return seen


def test_actual_batch_rejects_same_project_two_labels_before_plan(registered, tmp_path, monkeypatch):
    base, reg = registered
    path, rows = roster(base, reg)
    specs = specs_for(rows)
    alias_pair(specs)
    specs[0].full_path.write_text('id: https://example.org/retained\n')
    before = tree(tmp_path)
    authorities = authority_bytes(path, rows)
    seen = batch_traps(monkeypatch)
    monkeypatch.setattr(api, 'plan', lambda *a: pytest.fail('pair conflict reached plan'))
    result = batch(reg, path)
    assert result.exit_code == 1, result.output
    assert_role_conflict(result.output)
    assert seen == {'lock': [], 'execute': []}
    assert tree(tmp_path) == before
    assert {p: p.read_bytes() for p in authorities} == authorities


def test_actual_batch_rechecks_pair_conflict_after_plan(registered, tmp_path, monkeypatch):
    base, reg = registered
    path, rows = roster(base, reg)
    specs = specs_for(rows)
    observed = {}
    plans = []
    def plan(spec):
        result = stub_plan(spec)
        plans.append(spec.label)
        if spec.label == 'shared_rep2':
            alias_pair(specs)
            observed.update(tree(tmp_path))
        return result
    monkeypatch.setattr(api, 'plan', plan)
    seen = batch_traps(monkeypatch)
    result = batch(reg, path)
    assert result.exit_code == 1 and plans == ['shared_rep1', 'shared_rep2'], result.output
    assert_role_conflict(result.output)
    assert seen == {'lock': [], 'execute': []} and tree(tmp_path) == observed


@pytest.mark.parametrize('projects', [('ONE', 'TWO'), ('A', 'AB')])
def test_actual_batch_allows_disjoint_projects_in_same_label_directory(registered, tmp_path, monkeypatch, projects):
    base, original = registered
    rows = []
    for name in projects:
        reg = deepcopy(original)
        reg['registration_id'] = 'synthetic-' + name
        reg['run']['project'] = name
        reg['inputs']['project'] = name
        reg['inputs']['source_manifest'] = None
        reg['receipt']['coverage_floor'] = {'state': 'registered', 'numerator': 1, 'denominator': 2}
        path = tmp_path / (name + '-registration.json')
        reg['registration_path'] = str(path)
        path.write_bytes(sg.canonical(reg))
        rows.append({'project': name, 'label': reg['run']['label'], 'registration_path': str(path)})
    roster_path = tmp_path / 'multi-project-roster.json'
    roster_path.write_bytes(sg.canonical({'format': 'shared_generation_batch_roster_v1', 'registrations': rows}))
    planned = []
    def plan(spec):
        planned.append(spec)
        return stub_plan(spec)
    monkeypatch.setattr(api, 'plan', plan)
    seen = batch_traps(monkeypatch)
    before = tree(tmp_path)
    result = CliRunner().invoke(cli, ['api', 'batch', '--projects', ','.join(projects),
        '--label-prefix', 'shared', '--replicates', '1', '--shared-generation-version', '1',
        '--shared-generation-registration', str(roster_path), '--no-branch-guard', '--dry-run'])
    assert result.exit_code == 0, result.output
    assert [spec.project for spec in planned] == list(projects)
    assert planned[0].metadata_dir == planned[1].metadata_dir
    assert seen == {'lock': [], 'execute': []} and tree(tmp_path) == before


def test_actual_batch_rechecks_pair_conflict_between_dispatches(registered, tmp_path, monkeypatch):
    from data_sheets_schema import receipt_completion_policy as cp, receipts
    from filelock import FileLock
    base, reg = registered
    path, rows = roster(base, reg)
    specs = specs_for(rows)
    authorities = authority_bytes(path, rows)
    seen, acquired, released, verdicts = [], [], [], []
    after_simulation = {}
    inert_control = tmp_path / 'inert-no-write-control'
    def no_write_acquire(prefix, projects):
        acquired.append((prefix, tuple(projects)))
        return inert_control  # Deliberately no mkdir/open/write/lock operation.
    def forbidden(*args, **kwargs):
        pytest.fail('negative late-check fixture must not execute a real writer or transport')
    monkeypatch.setattr(run_lock, 'acquire', no_write_acquire)
    monkeypatch.setattr(run_lock, 'release', released.append)
    monkeypatch.setattr(FileLock, 'acquire', forbidden)
    monkeypatch.setattr(api, '_exclusive_run', forbidden)
    monkeypatch.setattr(api, '_client', forbidden)
    monkeypatch.setattr(api, '_call_with_usage', forbidden)
    monkeypatch.setattr(api, '_save_progress', forbidden)
    monkeypatch.setattr(api, '_snapshot', forbidden)
    monkeypatch.setattr(module, '_write_verdict', lambda *args: verdicts.append(args[1]['status']))
    monkeypatch.setattr(api, 'plan', stub_plan)
    def execute(spec):
        seen.append(spec.label)
        assert seen == ['shared_rep1'], 'second run must not execute after a physical output collision'
        selected = cp.select_policy(spec.render_spec())
        receipt = {'checked': True, 'expected': True, 'instrument': receipts.RERECEIPTS_INSTRUMENT,
            'slots': {'with_receipt': 3, 'receiptable': 3}, 'findings': [],
            'chunks': {'total': 1, 'reviewed': 1}, 'snippets': {'verified': 1},
            cp.BLOCK_KEY: cp.block_identity(selected)}
        checks = {'receipts': receipt, 'pair': {'ran': True, 'errors': 0},
            'report': {'checked': True, 'claims_checked': 1, 'findings': []},
            'grounding': {'checked': True, 'distinct': {'absent': 0}},
            'form': {'checked': True, 'organisational_fragments': 0,
                     'undeclared_prefix_occurrences': 0, 'british_spellings': 0}}
        # Explicit synthetic state change between calls, not generation evidence.
        alias_pair(specs)
        after_simulation.update(tree(tmp_path))
        return {'usage': [], 'skipped': [], 'validation_problems': [], 'checks': checks,
                'outputs': {'provenance': str(spec.provenance_path)}}
    monkeypatch.setattr(api, 'execute', execute)
    result = batch(reg, path, extra=('--continue-on-error',))
    assert result.exit_code == 1, result.output
    assert_role_conflict(result.output)
    assert 'registered receipt gate passed' in result.output
    assert seen == ['shared_rep1'] and len(acquired) == len(verdicts) == 1
    assert released == [inert_control] and not inert_control.exists()
    assert tree(tmp_path) == after_simulation
    assert {p: p.read_bytes() for p in authorities} == authorities


@pytest.mark.parametrize('other_role', ['own_lock', 'core', 'snapshot'])
def test_public_execute_refuses_same_run_role_alias_before_any_lock(registered, tmp_path, monkeypatch, other_role):
    """No destructive baseline: even a missing guard hits a pre-write trap."""
    base, reg = registered
    spec = selected_spec(base, reg)
    live_account(spec)
    spec.full_path.write_text('id: https://example.org/retained-neutral-record\n')
    if other_role == 'own_lock':
        peer = dict(ledger.output_locks((spec.full_path,)))[spec.full_path.resolve()]
    elif other_role == 'core':
        peer = spec.core_path
    else:
        peer = spec.metadata_dir / 'intermediate' / f'{spec.project}_full.yaml'
        peer.parent.mkdir(parents=True)
    os.link(spec.full_path, peer)
    before = tree(tmp_path)
    authorities = {Path(path): raw for path, raw in sg.capture(spec).files}
    seen = no_execution(monkeypatch)
    with pytest.raises(ValueError, match='conflicting output ownership') as error:
        api.execute(spec)
    assert str(spec.full_path) in str(error.value)
    assert seen == [] and spec.full_path.samefile(peer)
    assert tree(tmp_path) == before
    assert {p: p.read_bytes() for p in authorities} == authorities


@pytest.mark.parametrize('alias', ['symlink', 'hardlink'])
def test_actual_batch_refuses_control_progress_alias_before_plan_or_lock(registered, tmp_path, monkeypatch, alias):
    """Only synthetic setup writes; run_lock.acquire is always trapped."""
    base, reg = registered
    path, rows = roster(base, reg)
    first = specs_for(rows)[0]
    progress = api._progress_path(first)
    progress.parent.mkdir(parents=True)
    progress.write_bytes(sg.canonical({'completed': [], 'label': first.label,
        'run_identity': ledger.run_identity(first), 'generation_id': 'synthetic-generation'}))
    control = run_lock._path_for('shared')
    control.parent.mkdir(parents=True)
    if alias == 'symlink':
        control.symlink_to(progress.absolute())
    else:
        os.link(progress, control)
    before = tree(tmp_path)
    authorities = authority_bytes(path, rows)
    seen = batch_traps(monkeypatch)
    monkeypatch.setattr(api, 'plan', lambda *a: pytest.fail('control collision reached plan'))
    monkeypatch.setattr(run_lock, 'release', lambda *a: pytest.fail('control collision reached release'))
    result = batch(reg, path)
    assert result.exit_code == 1, result.output
    assert_role_conflict(result.output)
    assert 'batch-control' in result.output
    assert seen == {'lock': [], 'execute': []} and control.samefile(progress)
    assert tree(tmp_path) == before
    assert {p: p.read_bytes() for p in authorities} == authorities


def private_inventory(monkeypatch, tmp_path):
    """Route only the global writer to synthetic inventory bytes, never a source copy."""
    from data_sheets_schema import resources, schema_digest
    original = resources.resource_path
    destination = tmp_path / 'private-digest-inventory.yaml'
    destination.write_text('digests: {}\n')
    monkeypatch.setattr(resources, 'resource_path', lambda path: destination
        if path == schema_digest.INVENTORY_LEDGER else original(path))
    return destination


def test_public_execute_refuses_inventory_alias_to_run_data(registered, tmp_path, monkeypatch):
    base, reg = registered
    spec = selected_spec(base, reg)
    live_account(spec)
    inventory = private_inventory(monkeypatch, tmp_path)
    os.link(inventory, spec.full_path)
    before = tree(tmp_path)
    authorities = {Path(path): raw for path, raw in sg.capture(spec).files}
    seen = no_execution(monkeypatch)
    with pytest.raises(ValueError, match='conflicting output ownership') as error:
        api.execute(spec)
    assert 'shared-inventory' in str(error.value)
    assert seen == [] and inventory.samefile(spec.full_path)
    assert tree(tmp_path) == before
    assert {p: p.read_bytes() for p in authorities} == authorities


def test_actual_batch_refuses_inventory_alias_to_control(registered, tmp_path, monkeypatch):
    base, reg = registered
    path, rows = roster(base, reg)
    inventory = private_inventory(monkeypatch, tmp_path)
    control = run_lock._path_for('shared')
    control.parent.mkdir(parents=True)
    control.symlink_to(inventory)
    before = tree(tmp_path)
    authorities = authority_bytes(path, rows)
    seen = batch_traps(monkeypatch)
    monkeypatch.setattr(api, 'plan', lambda *a: pytest.fail('inventory/control collision reached plan'))
    monkeypatch.setattr(run_lock, 'release', lambda *a: pytest.fail('inventory/control collision reached release'))
    result = batch(reg, path)
    assert result.exit_code == 1, result.output
    assert_role_conflict(result.output)
    assert 'shared-inventory' in result.output and 'batch-control' in result.output
    assert seen == {'lock': [], 'execute': []} and control.samefile(inventory)
    assert tree(tmp_path) == before
    assert {p: p.read_bytes() for p in authorities} == authorities
