"""Recoverable worker assignments remain a separately selected audit condition."""
from copy import deepcopy
import json
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest

BASE = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(BASE), str(BASE / 'native_controls')]
from audit_controls import batch_native, batch_output, batch_registration, prepare, registration
from audit_controls.test_batch_registration import CONFIG, empty_prepare
from audit_controls.test_context_preparation import ancestry, save
from audit_controls.test_source_metadata_upgrade import metadata_ancestry
from audit_controls.test_staged_preparation import actual_renderer_history_root
from audit_controls.test_draft_registration import required_cli
from audit_controls.test_batch_downstream import scientific_pair
from data_sheets_schema import api_runner, audit_batch_context, evidence_assertions
from evaluation_controls import registration as evaluation_registration
from finalization_controls import registration as final_registration
from native_file_policy import FileAccess
import run_api_canary

SELECTOR = {'kind': 'explicit_child_reads_v1'}


def select(manifest):
    manifest.update(protocol_version=7, render_version=23, audit_batch_navigation=deepcopy(SELECTOR))
    manifest[registration.TRANSITION] = {'kind': registration.BATCH_CHILD_NAVIGATION_TRANSITION_KIND}


@pytest.mark.parametrize('value', [None, 0, 1, 'true', {}, []])
def test_worker_selection_requires_boolean_before_writes(tmp_path, value):
    with pytest.raises(registration.BudgetStop, match='explicit boolean'):
        empty_prepare(tmp_path, audit_worker_navigation=value)
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize('options', [{}, {'audit_batches': CONFIG},
    {'audit_batches': CONFIG, 'audit_batch_format': True}, {'audit_batch_navigation': True}])
def test_worker_selection_requires_all_prior_modes(tmp_path, options):
    with pytest.raises(registration.BudgetStop, match='requires explicit audit batch'):
        empty_prepare(tmp_path, audit_worker_navigation=True, **options)
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize('enabled', [False, True])
def test_worker_cli_selection_is_explicit(tmp_path, monkeypatch, enabled):
    config = save(tmp_path / 'config.json', CONFIG)
    class Captured(Exception): pass
    def capture(**kwargs):
        assert kwargs['audit_worker_navigation'] is enabled
        assert kwargs['audit_batch_navigation'] is True
        raise Captured
    monkeypatch.setattr(prepare, 'prepare', capture)
    monkeypatch.setattr(sys, 'argv', ['prepare', *required_cli(), '--audit-batches', str(config),
        '--audit-batch-format', '--audit-batch-navigation',
        *(['--audit-worker-navigation'] if enabled else [])])
    with pytest.raises(Captured): prepare.main()


@pytest.mark.parametrize('value', [None, False, True, 0, '', [], {}, {'kind': 'explicit_row_reads_v1'},
                                   {**SELECTOR, 'extra': 1}])
def test_renderer23_rejects_missing_or_wrong_selector(tmp_path, value):
    manifest = {'kind': 'd4d_native_audit_continuation', 'schema_version': 1}
    select(manifest)
    manifest['audit_batch_navigation'] = value
    with pytest.raises(registration.BudgetStop, match='exact explicit audit batch navigation'):
        registration.validate_registration(save(tmp_path / 'registration.json', manifest))
    del manifest['audit_batch_navigation']
    with pytest.raises(registration.BudgetStop, match='exact explicit audit batch navigation'):
        registration.validate_registration(save(tmp_path / 'missing.json', manifest))


def test_worker_selector_cannot_relabel_renderer22(tmp_path):
    manifest = {'kind': 'd4d_native_audit_continuation', 'schema_version': 1,
        'protocol_version': 7, 'render_version': 22, 'audit_batch_navigation': SELECTOR,
        registration.TRANSITION: {'kind': registration.BATCH_NAVIGATION_TRANSITION_KIND}}
    with pytest.raises(registration.BudgetStop, match='exact explicit audit batch navigation'):
        registration.validate_registration(save(tmp_path / 'registration.json', manifest))


def test_preparation_recovery_permissions_and_immutable_replay(metadata_ancestry, tmp_path):
    args, _, preserved, _ = metadata_ancestry
    old_path = prepare.prepare(**args, destination=tmp_path / 'old', audit_batches=CONFIG,
        audit_batch_format=True, audit_batch_navigation=True)
    old = registration.validate_registration(old_path)
    frozen = {p: p.read_bytes() for p in old_path.parent.rglob('*') if p.is_file()}
    path = prepare.prepare(**args, destination=tmp_path / 'new', audit_batches=CONFIG,
        audit_batch_format=True, audit_batch_navigation=True, audit_worker_navigation=True)
    selected = registration.validate_registration(path)
    assert (selected['protocol_version'], selected['render_version']) == (7, 23)
    assert selected['audit_batch_navigation'] == SELECTOR
    assert old['render_version'] == 22 and old['audit_batch_navigation'] == {'kind': 'explicit_row_reads_v1'}
    assert evidence_assertions.protocol_for_renderer(23) == 7
    assert api_runner.phase_instruction('audit', 23) == api_runner.phase_instruction('audit', 22)
    legacy = deepcopy(selected)
    legacy['render_version'] = 22
    legacy['audit_batch_navigation'] = {'kind': 'explicit_row_reads_v1'}
    legacy[registration.TRANSITION] = {'kind': registration.BATCH_NAVIGATION_TRANSITION_KIND}
    assert batch_output.specification(selected, path, worker_total_cap_usd='12') == batch_output.specification(
        legacy, path, worker_total_cap_usd='12')
    arguments = batch_registration.scientific_arguments(selected)
    for child in selected['audit_batches']['children']:
        system = Path(child['system_prompt']).read_text()
        if child['kind'] == 'integration':
            assert system == batch_registration.child_system(legacy, child['id'])
            continue
        text = Path(child['instruction']).read_text()
        assert json.loads(text) == json.loads(audit_batch_context.render_worker_context(
            **arguments, worker_id=child['id']))
        assert system.startswith(batch_registration.child_system(legacy, child['id']) + '\n\n# Registered worker assignment recovery')
        recovery = json.loads(system.rsplit('\n\n', 1)[1])
        assert recovery['worker_id'] == child['id']
        assert recovery['worker_instruction_reads'] == audit_batch_context.worker_navigation_reads(text, Path(child['instruction']))
        policy = batch_native.build_policy(selected, path, child['id'])
        assert policy == batch_native.build_policy(legacy, path, child['id'])
        files = FileAccess(policy)
        for read in [*recovery['worker_instruction_reads'], recovery['batch_plan']]:
            assert read['tool'] == 'Read'
            assert files.classify('Read', read['input'])[0] == 'prescribed'
        assert files.classify('Read', {'file_path': str(Path(child['instruction']).parent)})[0] == 'not_prescribed'
        assert files.classify('Read', {'file_path': str(tmp_path / 'foreign-instruction.md')})[0] == 'not_prescribed'
        assert 'no additional permissions' in system.lower()
        assert 'after successful sealing' in system
    assert frozen == {p: p.read_bytes() for p in frozen}
    assert preserved == {p: Path(p).read_bytes() for p in preserved}
    assert not Path(selected['job']['attempt_dir']).exists()
    assert not Path(selected['budget']['ledger_path']).exists()
    # Rehashing a changed recovery locator still cannot bypass deterministic replay.
    target = Path(selected['audit_batches']['children'][0]['system_prompt'])
    target.write_text(target.read_text().replace('"offset": 1', '"offset": 2'))
    selected['pinned_files'][str(target)] = registration.sha(target)
    save(path, selected)
    with pytest.raises(registration.BudgetStop, match='system differs'):
        registration.validate_registration(path)


def test_continuation_requires_fresh_worker_navigation_selection(metadata_ancestry, tmp_path):
    args = metadata_ancestry[0]
    source = tmp_path / 'stopped'
    previous = {'budget': {'ledger_path': str(source / 'billing.json')},
        'job': {'id': 'stopped', 'attempt_dir': str(source / 'attempts/stopped')}}
    select(previous)
    source_reg = save(source / 'registration.json', previous)
    save(source / 'billing.json', {'synthetic': 'unchanged predecessor ledger'})
    save(source / 'attempts/stopped/result.json', {'synthetic': 'stopped'})
    receipt = save(tmp_path / 'accounting.json', {'synthetic': 'reviewed'})
    path = prepare.prepare(**args, destination=tmp_path / 'new', audit_batches=CONFIG,
        audit_batch_format=True, audit_batch_navigation=True,
        continuation_checkpoint=args['reconciled_checkpoint'],
        continuation_source_registration=source_reg, continuation_reconciliation_receipt=receipt)
    manifest = registration.validate_registration(path)
    assert manifest['render_version'] == 22
    assert manifest['audit_batch_navigation'] == {'kind': 'explicit_row_reads_v1'}


@pytest.mark.parametrize('private', [False, True])
def test_api_generation_refuses23_before_output_lock(monkeypatch, private):
    monkeypatch.setattr(api_runner, '_exclusive_run', lambda *a, **k: pytest.fail('output lock reached'))
    with pytest.raises(ValueError, match='separately registered audit continuation'):
        (api_runner._execute if private else api_runner.execute)(
            SimpleNamespace(render_version=23, _replay_only=False), resume=False, client=object())


@pytest.mark.parametrize('version', [23, '23'])
def test_generation_and_evaluation_refuse23_without_selector(tmp_path, version):
    with pytest.raises(registration.BudgetStop, match='audit-continuation-only'):
        run_api_canary.verify({'generation': {'jobs': [{'render_spec': {'render_version': version}}]}}, tmp_path / 'unused', 'unused')
    with pytest.raises(registration.BudgetStop, match='audit-continuation-only'):
        evaluation_registration.verify_manifest({'render_version': version}, tmp_path / 'unused', 'unused')


def test_other_stage_entries_reject_worker_navigation(tmp_path):
    manifest = {'audit_batch_navigation': SELECTOR}
    path = save(tmp_path / 'registration.json', manifest)
    for verify in (run_api_canary.verify, evaluation_registration.verify_manifest):
        with pytest.raises(registration.BudgetStop, match='audit_batch_navigation is audit-only'):
            verify(manifest, path, 'unused')
    with pytest.raises(registration.BudgetStop, match='audit_batch_navigation is audit-only'):
        final_registration.validate_registration(path)


def test_phase4_binds23_context_without_active_worker_navigation(tmp_path):
    manifest, accepted = scientific_pair(tmp_path)
    select(manifest)
    manifest.pop('audit_batch_navigation')
    for root in (manifest['repository'], accepted['repository']):
        (Path(root) / 'src/data_sheets_schema/audit_batch_format.py').write_text('Synthetic unchanged format.\n')
    final_registration.validate_scientific_identity(manifest, accepted)
    target = Path(manifest['repository']) / 'src/data_sheets_schema/audit_batch_context.py'
    target.write_text('Changed worker navigation.\n')
    manifest['pinned_files'] = {str(target): registration.sha(target)}
    with pytest.raises(registration.BudgetStop, match='audit_batch_context.py'):
        final_registration.validate_scientific_identity(manifest, accepted)
