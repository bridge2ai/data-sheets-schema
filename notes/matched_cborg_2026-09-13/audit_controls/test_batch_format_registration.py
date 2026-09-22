"""Explicit renderer-21 format delivery; synthetic offline registrations only."""
from copy import deepcopy
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest

BASE = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(BASE), str(BASE/'native_controls')]
from audit_controls import batch_output, batch_registration, prepare, registration
from audit_controls.test_batch_registration import CONFIG, empty_prepare
from audit_controls.test_context_preparation import ancestry, save
from audit_controls.test_source_metadata_upgrade import metadata_ancestry
from audit_controls.test_staged_preparation import actual_renderer_history_root
from audit_controls.test_draft_registration import required_cli
from audit_controls.test_batch_downstream import scientific_pair
from finalization_controls import registration as final_registration
from data_sheets_schema import api_runner, evidence_assertions


@pytest.mark.parametrize('value', [None, 0, 1, 'true', {}, []])
def test_format_option_requires_boolean_before_writes(tmp_path, value):
    with pytest.raises(registration.BudgetStop, match='explicit boolean'):
        empty_prepare(tmp_path, audit_batch_format=value)
    assert not list(tmp_path.iterdir())


def test_format_option_requires_explicit_batch_mode_before_writes(tmp_path):
    with pytest.raises(registration.BudgetStop, match='requires explicit audit batches'):
        empty_prepare(tmp_path, audit_batch_format=True)
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize('selected', [False, True])
def test_cli_selects_format_only_when_explicit(tmp_path, monkeypatch, selected):
    path = save(tmp_path/'config.json', CONFIG)
    class Captured(Exception): pass
    def capture(**kwargs):
        assert kwargs['audit_batch_format'] is selected
        assert kwargs['audit_batches'] == batch_registration.selection(CONFIG)
        raise Captured
    monkeypatch.setattr(prepare, 'prepare', capture)
    monkeypatch.setattr(sys, 'argv', ['prepare', *required_cli(), '--audit-batches', str(path),
                                     *(['--audit-batch-format'] if selected else [])])
    with pytest.raises(Captured): prepare.main()


@pytest.mark.parametrize('changes', [
    {registration.TRANSITION: {'kind': registration.BATCH_TRANSITION_KIND}},
    {registration.TRANSITION: {'kind': registration.BATCH_FORMAT_TRANSITION_KIND, 'extra': True}},
    {'protocol_version': 6}, {'render_version': 21.0}, {'render_version': 22}])
def test_format_transition_accepts_only_exact_registered_pair(changes):
    manifest = {'protocol_version': 7, 'render_version': 21,
                registration.TRANSITION: {'kind': registration.BATCH_FORMAT_TRANSITION_KIND}, **changes}
    with pytest.raises(registration.BudgetStop, match='scientific contract transition'):
        registration.scientific_contract(manifest)


def test_format21_requires_batch_selector_at_actual_entry(tmp_path):
    manifest = {'schema_version': 1, 'kind': 'd4d_native_audit_continuation',
                'protocol_version': 7, 'render_version': 21,
                registration.TRANSITION: {'kind': registration.BATCH_FORMAT_TRANSITION_KIND}}
    with pytest.raises(registration.BudgetStop, match='batch registration'):
        registration.validate_registration(save(tmp_path/'registration.json', manifest))


def test_real_preparation_delivers_format_and_preserves20(metadata_ancestry, tmp_path):
    from data_sheets_schema import audit_batch_format
    args, _, preserved, _ = metadata_ancestry
    old_path = prepare.prepare(**args, destination=tmp_path/'old', audit_batches=CONFIG)
    old = registration.validate_registration(old_path)
    old_bytes = {p: p.read_bytes() for p in old_path.parent.rglob('*') if p.is_file()}
    path = prepare.prepare(**args, destination=tmp_path/'new', audit_batches=CONFIG, audit_batch_format=True)
    manifest = registration.validate_registration(path)
    assert (old['protocol_version'], old['render_version']) == (7, 20)
    assert (manifest['protocol_version'], manifest['render_version']) == (7, 21)
    assert manifest[registration.TRANSITION] == {'kind': registration.BATCH_FORMAT_TRANSITION_KIND}
    assert registration.schema_semantic_context(manifest)
    assert Path(old['inputs']['protocol']).read_bytes() == Path(manifest['inputs']['protocol']).read_bytes()
    assert evidence_assertions.protocol_for_renderer(21) == 7
    assert api_runner.phase_instruction('audit', 21) == api_runner.phase_instruction('audit', 20)
    helper = str(Path(manifest['repository'])/'src/data_sheets_schema/audit_batch_format.py')
    assert helper in manifest['pinned_files'] and helper not in old['pinned_files']
    assert helper not in {str(p) for p in registration.implementation_paths(old)}
    block = batch_output.configuration(manifest, path)
    assert block['max_rounds'] == old['audit_batches']['max_rounds'] == 2
    legacy_at_same_paths = deepcopy(manifest)
    legacy_at_same_paths['render_version'] = 20
    legacy_at_same_paths[registration.TRANSITION] = {'kind': registration.BATCH_TRANSITION_KIND}
    for child in block['children']:
        system = Path(child['system_prompt']).read_text()
        legacy_system = batch_registration.child_system(legacy_at_same_paths, child['id'])
        assert system == legacy_system + '\n\n' + audit_batch_format.render(child['kind'])
        assert system == batch_registration.child_system(manifest, child['id'])
        assert system.count(Path(manifest['inputs']['protocol']).read_text()) == 1
    assert '"render_version": 21' in Path(manifest['job']['instruction']).read_text()
    assert manifest['budget']['continuation'] == old['budget']['continuation']
    assert not Path(manifest['job']['attempt_dir']).exists()
    assert not Path(manifest['budget']['ledger_path']).exists()
    assert not (path.parent/'sequence_claim').exists()
    assert preserved == {name: Path(name).read_bytes() for name in preserved}
    assert old_bytes == {p: p.read_bytes() for p in old_bytes}
    # Removing the new pin fails the real validator before any execution.
    del manifest['pinned_files'][helper]
    save(path, manifest)
    with pytest.raises(registration.BudgetStop, match='fully pinned'):
        registration.validate_registration(path)


def test_repinning_format_system_cannot_bypass_replay(metadata_ancestry, tmp_path):
    path = prepare.prepare(**metadata_ancestry[0], destination=tmp_path/'new',
                           audit_batches=CONFIG, audit_batch_format=True)
    manifest = registration.read_json(path)
    target = Path(manifest['audit_batches']['children'][0]['system_prompt'])
    target.write_text(target.read_text()+'\nUnregistered format rule.\n')
    manifest['pinned_files'][str(target)] = registration.sha(target)
    save(path, manifest)
    with pytest.raises(registration.BudgetStop, match='system differs'):
        registration.validate_registration(path)


@pytest.mark.parametrize('private', [False, True])
def test_format_renderer_cannot_execute_generation(tmp_path, monkeypatch, private):
    spec = SimpleNamespace(render_version=21, _replay_only=False)
    monkeypatch.setattr(api_runner, '_exclusive_run', lambda *a, **k: pytest.fail('output lock reached'))
    with pytest.raises(ValueError, match='separately registered audit continuation'):
        (api_runner._execute if private else api_runner.execute)(spec, resume=False, client=object())
    assert not list(tmp_path.iterdir())


def test_phase4_pins_inherited_format_without_activating_batch_mode(tmp_path):
    manifest, accepted = scientific_pair(tmp_path)
    manifest['render_version'] = 21
    manifest[registration.TRANSITION] = {'kind': registration.BATCH_FORMAT_TRANSITION_KIND}
    for root in (manifest['repository'], accepted['repository']):
        (Path(root)/'src/data_sheets_schema/audit_batch_format.py').write_text('synthetic same format\n')
    final_registration.validate_scientific_identity(manifest, accepted)
    assert 'audit_batches' not in manifest
    changed = Path(manifest['repository'])/'src/data_sheets_schema/audit_batch_format.py'
    changed.write_text('changed format\n')
    manifest['pinned_files'] = {str(changed): registration.sha(changed)}
    with pytest.raises(registration.BudgetStop, match='audit_batch_format.py'):
        final_registration.validate_scientific_identity(manifest, accepted)
