"""Opt-in integration control; synthetic registrations only, no provider calls."""
from copy import deepcopy
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest
from budgeted_cborg import BudgetStop
from native_control import CONTRACT, HISTORY_CONTRACT
from audit_controls import batch_native, native, prepare, registration, transport, worker_checkpoint
from audit_controls.test_batch_runtime import batch
from audit_controls.test_batch_registration import CONFIG, empty_prepare
from audit_controls.test_context_preparation import ancestry, save
from audit_controls.test_source_metadata_upgrade import metadata_ancestry
from audit_controls.test_staged_preparation import actual_renderer_history_root
from audit_controls.test_worker_checkpoint import example
from audit_controls.test_draft_registration import required_cli
from evaluation_controls import registration as evaluation_registration
from finalization_controls import registration as final_registration
import run_api_canary

KEY = 'native_history_control'
SELECTION = {'kind': 'responsive_history_v1'}


def test_absence_and_strict_detached_selection():
    assert registration.native_history_control({}) is None
    m = {'kind': 'd4d_native_audit_continuation', 'audit_batches': {}, KEY: dict(SELECTION)}
    result = registration.native_history_control(m)
    assert result == SELECTION
    result['kind'] = 'changed'
    assert m[KEY] == SELECTION


@pytest.mark.parametrize('value', [None, True, False, [], 'on', {}, {'kind': 'unknown'},
                                  {**SELECTION, 'timeout': 1000}])
def test_invalid_selection_stops_before_any_mutable_setup(value, tmp_path, monkeypatch):
    m = {'kind': 'd4d_native_audit_continuation', 'audit_batches': {}, KEY: value}
    def forbidden(*a, **k): pytest.fail('invalid selection reached mutable or provider setup')
    monkeypatch.setattr(batch_native, 'execute_job', forbidden)
    monkeypatch.setattr(transport, 'Client', forbidden)
    with pytest.raises(BudgetStop, match='history control'):
        native.execute_job(SimpleNamespace(manifest=m))
    with pytest.raises(BudgetStop, match='history control'):
        transport.transport_paths(m)
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize('m', [{KEY: SELECTION},
    {'kind': 'd4d_native_audit_continuation', KEY: SELECTION},
    {'kind': 'other', 'audit_batches': {}, KEY: SELECTION}])
def test_wrong_stage_or_unbatched_rejected(m):
    with pytest.raises(BudgetStop): registration.native_history_control(m)


@pytest.mark.parametrize('value', [None, 1, 'true', {}, []])
def test_prepare_cannot_coerce_an_option(value, tmp_path):
    with pytest.raises(BudgetStop, match='explicit boolean'):
        empty_prepare(tmp_path, audit_batches=CONFIG, native_history_control=value)
    assert not list(tmp_path.iterdir())


def test_prepare_rejects_unbatched_before_reads_or_writes(tmp_path):
    with pytest.raises(BudgetStop, match='explicit audit batches'):
        empty_prepare(tmp_path, native_history_control=True)
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize('selected', [False, True])
def test_cli_explicit_selection(selected, monkeypatch):
    class Captured(Exception): pass
    def capture(**kwargs):
        assert kwargs[KEY] is selected
        raise Captured
    monkeypatch.setattr(prepare, 'prepare', capture)
    monkeypatch.setattr(sys, 'argv', ['prepare', *required_cli(),
        *(['--native-history-control'] if selected else [])])
    with pytest.raises(Captured): prepare.main()


def test_actual_preparation_pins_control_and_preserves_scientific_prompts(metadata_ancestry, tmp_path):
    args = metadata_ancestry[0]
    old_path = prepare.prepare(**args, destination=tmp_path/'legacy', audit_batches=CONFIG)
    new_path = prepare.prepare(**args, destination=tmp_path/'chosen', audit_batches=CONFIG,
                               native_history_control=True)
    old = registration.validate_registration(old_path)
    new = registration.validate_registration(new_path)
    assert KEY not in old and new[KEY] == SELECTION
    assert registration.read_json(new_path.parent/'offline_plan.json')[KEY] == SELECTION
    for key in ('model', 'profile', 'native_runtime', 'protocol_version', 'render_version'):
        assert old[key] == new[key]
    for left, right in zip(old['audit_batches']['children'], new['audit_batches']['children']):
        for key in ('instruction', 'system_prompt'):
            before = left[key]
            after = right[key]
            if key == 'instruction' and left['id'] == 'integration':
                before, after = old['audit_batches']['integration_base'], new['audit_batches']['integration_base']
            actual = Path(after).read_text().replace(str(new_path.parent), str(old_path.parent))
            assert actual == Path(before).read_text()
    assert not Path(new['budget']['ledger_path']).exists()


def test_only_integration_selects_v3_and_old_workers_are_exact(batch, monkeypatch):
    monkeypatch.setattr(batch_native, 'verify_integration', lambda *a: {'row_views': {}})
    original = {r['id']: batch_native.build_policy(batch.m, batch.reg, r['id'])
                for r in batch.m['audit_batches']['children']}
    batch.m[KEY] = dict(SELECTION)
    save(batch.reg, batch.m)
    for child, before in original.items():
        after = batch_native.build_policy(batch.m, batch.reg, child)
        expected = deepcopy(before)
        if child == 'integration': expected['pretool_control'] = HISTORY_CONTRACT
        assert after == expected
        assert after['pretool_control'] == (HISTORY_CONTRACT if child == 'integration' else CONTRACT)


def test_checkpoint_cannot_silently_change_old_control(example):
    example.manifest[KEY] = dict(SELECTION)
    with pytest.raises(BudgetStop, match='registered scientific/runtime settings'):
        worker_checkpoint.validate(example.manifest)


@pytest.mark.parametrize('value', [None, SELECTION])
def test_other_stages_reject_presence_even_null(value, tmp_path):
    manifest = {KEY: value}
    path = save(tmp_path/'registration.json', manifest)
    with pytest.raises(BudgetStop, match='history_control'):
        run_api_canary.verify(manifest, path, registration.sha(path))
    with pytest.raises(BudgetStop, match='history_control'):
        final_registration.validate_registration(path)
    with pytest.raises(BudgetStop, match='history_control'):
        evaluation_registration.verify_manifest(manifest, path, registration.sha(path))
