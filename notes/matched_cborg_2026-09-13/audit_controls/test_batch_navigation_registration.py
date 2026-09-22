"""Explicit renderer22 navigation; all registrations and rows are synthetic."""
from copy import deepcopy
import json
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest

BASE = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(BASE), str(BASE/'native_controls')]
from audit_controls import batch_output, batch_registration, batch_native, prepare, registration
from audit_controls.test_batch_registration import CONFIG, empty_prepare
from audit_controls.test_context_preparation import ancestry, save
from audit_controls.test_source_metadata_upgrade import metadata_ancestry
from audit_controls.test_staged_preparation import actual_renderer_history_root
from audit_controls.test_draft_registration import required_cli
from audit_controls.test_batch_downstream import scientific_pair
from audit_controls.test_batch_runtime import batch, proposal
from finalization_controls import registration as final_registration
from evaluation_controls import registration as evaluation_registration
from data_sheets_schema import api_runner, audit_batch_context, evidence_assertions
from native_file_policy import FileAccess
import run_api_canary

SELECTOR = {'kind': 'explicit_row_reads_v1'}


def select(manifest):
    manifest.update(protocol_version=7, render_version=22, audit_batch_navigation=deepcopy(SELECTOR))
    manifest[registration.TRANSITION] = {'kind': registration.BATCH_NAVIGATION_TRANSITION_KIND}


@pytest.mark.parametrize('value', [None, 0, 1, 'true', {}, []])
def test_navigation_prepare_requires_boolean_before_writes(tmp_path, value):
    with pytest.raises(registration.BudgetStop, match='explicit boolean'):
        empty_prepare(tmp_path, audit_batch_navigation=value)
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize('options', [{}, {'audit_batches': CONFIG}, {'audit_batch_format': True}])
def test_navigation_requires_explicit_format_and_batches(tmp_path, options):
    with pytest.raises(registration.BudgetStop, match='requires explicit audit batch'):
        empty_prepare(tmp_path, audit_batch_navigation=True, **options)
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize('selected', [False, True])
def test_cli_navigation_is_never_implicit(tmp_path, monkeypatch, selected):
    config = save(tmp_path/'config.json', CONFIG)
    class Captured(Exception): pass
    def capture(**kwargs):
        assert kwargs['audit_batch_navigation'] is selected
        assert kwargs['audit_batch_format'] is True
        raise Captured
    monkeypatch.setattr(prepare, 'prepare', capture)
    monkeypatch.setattr(sys, 'argv', ['prepare', *required_cli(), '--audit-batches', str(config),
                                    '--audit-batch-format', *(['--audit-batch-navigation'] if selected else [])])
    with pytest.raises(Captured): prepare.main()


@pytest.mark.parametrize('value', [None, False, True, 0, '', [], {}, {'kind': 'unknown'}, {**SELECTOR, 'extra': 1}])
def test_actual_audit_entry_rejects_malformed_navigation_early(tmp_path, value):
    manifest = {'kind': 'd4d_native_audit_continuation', 'schema_version': 1}
    select(manifest); manifest['audit_batch_navigation'] = value
    with pytest.raises(registration.BudgetStop, match='exact explicit audit batch navigation'):
        registration.validate_registration(save(tmp_path/'registration.json', manifest))


def test_renderer22_cannot_omit_selector_or_batch_mode(tmp_path):
    manifest = {'kind': 'd4d_native_audit_continuation', 'schema_version': 1}; select(manifest)
    missing = deepcopy(manifest); del missing['audit_batch_navigation']
    with pytest.raises(registration.BudgetStop, match='exact explicit audit batch navigation'):
        registration.validate_registration(save(tmp_path/'missing.json', missing))
    with pytest.raises(registration.BudgetStop, match='explicit batch registration'):
        registration.validate_registration(save(tmp_path/'no-batch.json', manifest))


@pytest.mark.parametrize('version,kind', [(20, registration.BATCH_TRANSITION_KIND), (21, registration.BATCH_FORMAT_TRANSITION_KIND)])
def test_navigation_key_cannot_change_historical_renderer(tmp_path, version, kind):
    m = {'kind': 'd4d_native_audit_continuation', 'schema_version': 1, 'protocol_version': 7,
         'render_version': version, registration.TRANSITION: {'kind': kind}, 'audit_batch_navigation': SELECTOR}
    with pytest.raises(registration.BudgetStop, match='requires explicit audit renderer 22'):
        registration.validate_registration(save(tmp_path/'registration.json', m))


def test_real_preparation_preserves21_and_selects22(metadata_ancestry, tmp_path):
    args, _, preserved, _ = metadata_ancestry
    before_path = prepare.prepare(**args, destination=tmp_path/'legacy', audit_batches=CONFIG, audit_batch_format=True)
    before = registration.validate_registration(before_path)
    frozen = {p: p.read_bytes() for p in before_path.parent.rglob('*') if p.is_file()}
    path = prepare.prepare(**args, destination=tmp_path/'selected', audit_batches=CONFIG,
                           audit_batch_format=True, audit_batch_navigation=True)
    selected = registration.validate_registration(path)
    assert selected['audit_batch_navigation'] == SELECTOR
    assert (selected['protocol_version'], selected['render_version']) == (7, 22)
    assert before['render_version'] == 21 and 'audit_batch_navigation' not in before
    assert evidence_assertions.protocol_for_renderer(22) == 7
    assert api_runner.phase_instruction('audit', 22) == api_runner.phase_instruction('audit', 21)
    assert Path(before['inputs']['protocol']).read_bytes() == Path(selected['inputs']['protocol']).read_bytes()
    same_paths = deepcopy(selected); same_paths.pop('audit_batch_navigation'); same_paths['render_version'] = 21
    same_paths[registration.TRANSITION] = {'kind': registration.BATCH_FORMAT_TRANSITION_KIND}
    assert batch_output.specification(selected, path, worker_total_cap_usd='12') == batch_output.specification(same_paths, path, worker_total_cap_usd='12')
    for child in selected['audit_batches']['children']:
        system = Path(child['system_prompt']).read_text()
        legacy = batch_registration.child_system(same_paths, child['id'])
        if child['kind'] == 'worker':
            assert system == legacy
        else:
            assert system.startswith(legacy+'\n\n# Registered integration row navigation\n\n')
            locators = json.loads(system.rsplit('\n\n', 1)[1])
            assert locators == {'integration_instruction': {'tool': 'Read', 'input': {'file_path': child['instruction'], 'offset': 4, 'limit': 200}},
                               'proposal_index': {'tool': 'Read', 'input': {'file_path': selected['audit_batches']['integration_index']}}}
            assert 'including retained rows' in system and 'no additional permissions' in system
            assert 'line-addressable navigation appendix' in system and 'reduce the range' in system
        assert system == batch_registration.child_system(selected, child['id'])
    for name in ('audit_batch_context.py', 'audit_batch_format.py', 'audit_batches.py'):
        helper = str(Path(selected['repository'])/'src/data_sheets_schema'/name)
        assert selected['pinned_files'][helper] == registration.sha(helper)
    assert selected['budget']['continuation'] == before['budget']['continuation']
    assert not Path(selected['job']['attempt_dir']).exists() and not Path(selected['budget']['ledger_path']).exists()
    assert frozen == {p: p.read_bytes() for p in frozen}
    assert preserved == {name: Path(name).read_bytes() for name in preserved}
    # Repinning a static system still cannot bypass replay.
    target = Path(selected['audit_batches']['children'][0]['system_prompt'])
    target.write_text(target.read_text()+'\nAn unregistered instruction.\n')
    selected['pinned_files'][str(target)] = registration.sha(target); save(path, selected)
    with pytest.raises(registration.BudgetStop, match='system differs'):
        registration.validate_registration(path)


def test_continuation_does_not_inherit_navigation(metadata_ancestry, tmp_path):
    args = metadata_ancestry[0]
    source = tmp_path/'stopped'
    predecessor = {'budget': {'ledger_path': str(source/'billing.json')},
                   'job': {'id': 'stopped', 'attempt_dir': str(source/'attempts/stopped')}}
    select(predecessor)
    source_reg = save(source/'registration.json', predecessor)
    save(source/'billing.json', {'synthetic': 'unchanged historical ledger'})
    save(source/'attempts/stopped/result.json', {'synthetic': 'stopped historical result'})
    receipt = save(tmp_path/'accounting.json', {'synthetic': 'prior reviewed accounting'})
    path = prepare.prepare(**args, destination=tmp_path/'successor',
        audit_batches=CONFIG, audit_batch_format=True,
        continuation_checkpoint=args['reconciled_checkpoint'],
        continuation_source_registration=source_reg, continuation_reconciliation_receipt=receipt)
    manifest = registration.validate_registration(path)
    assert manifest['render_version'] == 21 and 'audit_batch_navigation' not in manifest
    assert manifest[registration.TRANSITION] == {'kind': registration.BATCH_FORMAT_TRANSITION_KIND}


@pytest.mark.parametrize('value', [None, False, {}, SELECTOR])
def test_other_stage_entries_refuse_navigation_even_null(tmp_path, value):
    manifest = {'audit_batch_navigation': value}; path = save(tmp_path/'registration.json', manifest)
    for verify in (run_api_canary.verify, evaluation_registration.verify_manifest):
        with pytest.raises(registration.BudgetStop, match='audit_batch_navigation is audit-only'):
            verify(manifest, path, 'unused')
    with pytest.raises(registration.BudgetStop, match='audit_batch_navigation is audit-only'):
        final_registration.validate_registration(path)


@pytest.mark.parametrize('private', [False, True])
def test_api_generation_refuses22_before_output_lock(monkeypatch, private):
    monkeypatch.setattr(api_runner, '_exclusive_run', lambda *a, **k: pytest.fail('output lock reached'))
    with pytest.raises(ValueError, match='separately registered audit continuation'):
        (api_runner._execute if private else api_runner.execute)(SimpleNamespace(render_version=22, _replay_only=False), resume=False, client=object())


@pytest.mark.parametrize('version', [22, '22'])
def test_generation_and_evaluation_refuse_renderer_without_selector(tmp_path, version):
    with pytest.raises(registration.BudgetStop, match='audit-continuation-only'):
        run_api_canary.verify({'generation': {'jobs': [{'render_spec': {'render_version': version}}]}}, tmp_path/'unused', 'unused')
    with pytest.raises(registration.BudgetStop, match='audit-continuation-only'):
        evaluation_registration.verify_manifest({'render_version': version}, tmp_path/'unused', 'unused')


def test_phase4_binds22_instrument_without_active_navigation(tmp_path):
    manifest, accepted = scientific_pair(tmp_path)
    select(manifest); manifest.pop('audit_batch_navigation')
    for root in (manifest['repository'], accepted['repository']):
        (Path(root)/'src/data_sheets_schema/audit_batch_format.py').write_text('Synthetic unchanged format.\n')
    final_registration.validate_scientific_identity(manifest, accepted)
    target = Path(manifest['repository'])/'src/data_sheets_schema/audit_batch_context.py'
    target.write_text('Changed navigation.\n'); manifest['pinned_files'] = {str(target): registration.sha(target)}
    with pytest.raises(registration.BudgetStop, match='audit_batch_context.py'):
        final_registration.validate_scientific_identity(manifest, accepted)


@pytest.mark.parametrize('selected', [False, True])
def test_real_runtime_creation_replay_and_policy_share_navigation_selection(batch, monkeypatch, selected):
    if selected:
        select(batch.m)
        save(batch.reg, batch.m)
        batch.identity = registration.sha(batch.reg)
    seen = []
    (batch.attempt/'children').mkdir()
    monkeypatch.setattr(batch_output, 'worker_closures', lambda *a: None)
    monkeypatch.setattr(batch_output, 'proposals', lambda m: {
        w['id']: json.dumps(proposal(batch, w['id'])).encode() for w in batch.plan['workers']})
    monkeypatch.setattr(batch_registration, 'scientific_arguments', lambda m: {})
    def render(**kwargs):
        seen.append(kwargs.get('audit_batch_navigation'))
        return 'Synthetic navigation '+str(kwargs.get('audit_batch_navigation'))
    monkeypatch.setattr(audit_batch_context, 'render_integration_context', render)
    context = batch_native.prepare_integration(batch.m, batch.identity)
    assert seen == ([registration.BATCH_NAVIGATION_KIND]*2 if selected else [None]*2)
    policy = batch_native.build_policy(batch.m, batch.reg, 'integration')
    files = FileAccess(policy)
    for locator in (batch_output.child(batch.m, 'integration')['instruction'], batch.m['audit_batches']['integration_index']):
        assert files.classify('Read', {'file_path': locator})[0] == 'prescribed'
    assert files.classify('Read', {'file_path': batch_output.child(batch.m, 'integration')['instruction'], 'offset': 4, 'limit': 200})[0] == 'prescribed'
    for path, row in context['row_views'].items():
        assert Path(path).name == row['sha256']+'.json'
        assert files.classify('Read', {'file_path': path})[0] == 'prescribed'
        assert files.classify('Read', {'file_path': str(Path(path).parent)})[0] == 'not_prescribed'
    assert batch_native.verify_integration(batch.m, batch.identity) == context
    target = Path(batch_output.child(batch.m, 'integration')['instruction'])
    target.write_text(target.read_text()+'changed')
    with pytest.raises(registration.BudgetStop, match='index/instruction differs'):
        batch_native.verify_integration(batch.m, batch.identity)
