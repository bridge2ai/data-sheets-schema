"""Deferred #5094 N2/N3 causal cases, 2026-10-28.

Inputs: read-only committed v4 VOICE evidence and fresh synthetic snapshots.
Outputs: assertions only; no historical writes, backfill application or providers.
"""
from copy import deepcopy
import hashlib
import json
from pathlib import Path

import pytest
import yaml

from data_sheets_schema import api_runner as api, backfill_checks as backfill
from data_sheets_schema import snapshot_store, usage_ledger
from data_sheets_schema.report_audit_totals import check_report_audit_totals
from tests.test_report_audit_totals import _make_v10g_audit

ROOT = Path(__file__).resolve().parents[1]
VOICE = ROOT / 'data/d4d_concatenated/claudecode_agent_core/2026-08-13_claude-opus-5-api-generic-v4_rep1'


def make_spec(root, project='EXAMPLE', label='synthetic-legacy', method='claudecode_api'):
    selected = api.RunSpec(project=project, label=label, method=method, arm='baseline',
                           bundle=root / 'unused.txt', out_dir=root / 'output')
    selected.report_path.parent.mkdir(parents=True, exist_ok=True)
    api._intermediate_dir(selected).mkdir(parents=True, exist_ok=True)
    return selected


def write_record(selected, record):
    selected.provenance_path.write_text(yaml.safe_dump(record), encoding='utf-8')


def synthetic_snapshots(tmp_path, *, identified=True):
    selected = make_spec(tmp_path)
    selected.report_path.write_text('The audit returned 14 findings.', encoding='utf-8')
    first = api._intermediate_dir(selected) / 'EXAMPLE_audit.json'
    second = first.with_name('EXAMPLE_audit_2.json')
    first.write_text(_make_v10g_audit(), encoding='utf-8')
    audit = json.loads(_make_v10g_audit())
    audit['findings'].append({'severity': 'low', 'record': 'full', 'slot': 'extra', 'issue': 'extra'})
    second.write_text(json.dumps(audit), encoding='utf-8')
    record = {'run': usage_ledger.run_identity(selected), 'intermediates': []}
    if identified:
        record['run']['generation_id'] = 'synthetic-generation'
    for path in (first, second):
        row = {'path': str(path), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}
        if identified:
            row.update(phase=first.name, generation_id='synthetic-generation')
        record['intermediates'].append(row)
    write_record(selected, record)
    return selected, record, first, second


def test_committed_voice_ambiguity_is_unchecked_and_preserves_prior(tmp_path):
    """Representative canary: both N2 and N3 use the actual two-snapshot shape."""
    historical = {path: path.read_bytes() for path in (
        VOICE / 'VOICE_provenance.yaml', VOICE / 'VOICE_reconciliation.md',
        VOICE / 'intermediate/VOICE_audit.json', VOICE / 'intermediate/VOICE_audit_2.json')}
    record = yaml.safe_load(historical[VOICE / 'VOICE_provenance.yaml'])
    assert 'generation_id' not in record['run']
    audits = [row for row in record['intermediates'] if Path(row['path']).name in
              {'VOICE_audit.json', 'VOICE_audit_2.json'}]
    assert len(audits) == 2 and all('phase' not in row and 'generation_id' not in row for row in audits)
    selected = make_spec(tmp_path, 'VOICE', record['run']['label'], record['run']['method'])
    selected.report_path.write_bytes(historical[VOICE / 'VOICE_reconciliation.md'])
    for row in audits:
        target = api._intermediate_dir(selected) / Path(row['path']).name
        target.write_bytes(historical[VOICE / 'intermediate' / target.name])
        assert hashlib.sha256(target.read_bytes()).hexdigest() == row['sha256']
        row['path'] = str(target)
    write_record(selected, record)
    first, second = (api._intermediate_dir(selected) / name for name in ('VOICE_audit.json', 'VOICE_audit_2.json'))
    assert api.audit_counts(first.read_text())['total'] == 21
    prior = check_report_audit_totals(selected.report_path, second)
    assert prior['checked'] and prior['status'] == 'consistent' and prior['computed_total'] == 18
    before = {path: path.read_bytes() for path in (selected.provenance_path, selected.report_path, first, second)}
    # Exercise both readers before asserting, so the frozen pre-fix canary
    # captures N2's exception and N3's false 21-versus-18 mismatch together.
    try:
        fresh = api.report_audit_totals_block(selected, record=record)
    except usage_ledger.UsageLedgerError as error:
        fresh = {'raised': type(error).__name__, 'reason': str(error)}
    computed = backfill.compute(selected.provenance_path, only={'report_audit_totals'})['report_audit_totals']
    assert fresh.get('status') == computed['status'] == 'not_checked', {
        'runner': fresh, 'backfill': computed}
    assert fresh['checked'] is False and fresh['status'] == 'not_checked'
    assert 'ambiguous generation ownership' in fresh['reason']
    assert fresh['computed_total'] is None and fresh['findings'] == []
    existing = {**deepcopy(record), 'report_audit_totals': prior}
    assert api._current_report_audit_totals(selected, existing) is prior
    assert computed['checked'] is False and computed['status'] == 'not_checked'
    assert 'ambiguous generation ownership' in computed['reason']
    assert computed['computed_total'] is None and computed['findings'] == []
    assert computed['recorded_by'] == backfill.RECORDED_BY
    assert all(path.read_bytes() == raw for path, raw in before.items())
    assert all(path.read_bytes() == raw for path, raw in historical.items())


@pytest.mark.parametrize('remove_first', [False, True])
def test_backfill_uses_latest_attested_snapshot_without_filename_guessing(tmp_path, remove_first):
    selected, record, first, second = synthetic_snapshots(tmp_path)
    first.with_name('EXAMPLE_audit_99.json').write_text(_make_v10g_audit(), encoding='utf-8')
    if remove_first:
        first.unlink()
    before = selected.provenance_path.read_bytes()
    result = backfill.compute(selected.provenance_path, only={'report_audit_totals'})['report_audit_totals']
    assert result['checked'] and result['status'] == 'consistent' and result['computed_total'] == 14
    runner = api.report_audit_totals_block(selected, record=record)
    assert {key: value for key, value in result.items() if key != 'recorded_by'} == runner
    assert selected.provenance_path.read_bytes() == before


@pytest.mark.parametrize('damage', ['missing', 'changed', 'foreign-generation', 'wrong-project', 'missing-attestation'])
def test_invalid_snapshot_authority_never_falls_back_to_first_audit(tmp_path, damage):
    selected, record, first, second = synthetic_snapshots(tmp_path)
    if damage == 'missing':
        second.unlink()
    elif damage == 'changed':
        second.write_text(_make_v10g_audit(), encoding='utf-8')
    elif damage == 'foreign-generation':
        record['intermediates'][-1]['generation_id'] = 'foreign'
    elif damage == 'wrong-project':
        record['run']['project'] = 'OTHER'
    else:
        record['intermediates'][-1].pop('sha256')
    write_record(selected, record)
    runner = api.report_audit_totals_block(selected, record=record)
    computed = backfill.compute(selected.provenance_path, only={'report_audit_totals'})['report_audit_totals']
    for block in (runner, computed):
        assert block['checked'] is False and block['status'] == 'not_checked'
        assert block['computed_total'] is None and block['findings'] == []
        assert block['reason'].startswith('audit snapshot unavailable: ')
    assert first.exists()  # a readable but unauthorized fallback must not be selected


@pytest.mark.parametrize('with_second', [False, True])
def test_unindexed_legacy_fallback_requires_a_single_snapshot(tmp_path, with_second):
    selected, record, first, second = synthetic_snapshots(tmp_path, identified=False)
    record.pop('intermediates')
    write_record(selected, record)
    selected.report_path.write_text('The audit returned 13 findings.', encoding='utf-8')
    if not with_second:
        second.unlink()
    runner = api.report_audit_totals_block(selected, record=record)
    computed = backfill.compute(selected.provenance_path, only={'report_audit_totals'})['report_audit_totals']
    for block in (runner, computed):
        assert block['checked'] is (not with_second)
        assert block['status'] == ('not_checked' if with_second else 'consistent')
        assert block['computed_total'] == (None if with_second else 13)


def test_latest_attested_malformed_audit_is_not_replaced_by_first(tmp_path):
    selected, record, first, second = synthetic_snapshots(tmp_path)
    second.write_text('{invalid JSON', encoding='utf-8')
    record['intermediates'][-1]['sha256'] = hashlib.sha256(second.read_bytes()).hexdigest()
    write_record(selected, record)
    runner = api.report_audit_totals_block(selected, record=record)
    computed = backfill.compute(selected.provenance_path, only={'report_audit_totals'})['report_audit_totals']
    for block in (runner, computed):
        assert block['checked'] is False and block['status'] == 'not_checked'
        assert block['computed_total'] is None and block['findings'] == []
    assert api.audit_counts(first.read_text())['total'] == 13


def test_explicit_live_carry_does_not_consult_ambiguous_saved_history(tmp_path, monkeypatch):
    selected, record, _, second = synthetic_snapshots(tmp_path, identified=False)
    def forbidden(*args, **kwargs):
        pytest.fail('explicit live carry must not resolve saved snapshots')
    monkeypatch.setattr(snapshot_store, 'read_latest', forbidden)
    result = api.report_audit_totals_block(selected, {'Audit findings': second.read_text()}, record=record)
    assert result['status'] == 'consistent' and result['computed_total'] == 14


def test_default_backfill_discovers_portable_latest_without_first_file(tmp_path):
    selected, record, first, second = synthetic_snapshots(tmp_path)
    first.unlink()
    # A portable snapshot can have a noncanonical filename. The phase pin,
    # not glob discovery of the obsolete first file, advertises this check.
    latest = second.with_name('retained-current-audit.txt')
    second.rename(latest)
    record['intermediates'][-1]['path'] = str(latest)
    write_record(selected, record)
    before = selected.provenance_path.read_bytes()
    computed = backfill.compute(selected.provenance_path)
    assert computed['report_audit_totals']['status'] == 'consistent'
    assert computed['report_audit_totals']['computed_total'] == 14
    assert selected.provenance_path.read_bytes() == before


@pytest.mark.parametrize('index_state', ['absent', 'current', 'previous'])
def test_unregistered_standalone_backfill_keeps_only_safe_legacy_fallback(tmp_path, index_state):
    selected, _, first, second = synthetic_snapshots(tmp_path)
    second.unlink()
    selected.report_path.write_text('The audit returned 13 findings.', encoding='utf-8')
    write_record(selected, {'record_mode': 'historical-helper'})
    if index_state != 'absent':
        name = ('EXAMPLE_snapshot_index.json' if index_state == 'current' else
                'EXAMPLE_snapshot_index.previous-old.json')
        first.with_name(name).write_text('{}', encoding='utf-8')
    result = backfill.compute(selected.provenance_path, only={'report_audit_totals'})['report_audit_totals']
    assert result['checked'] is (index_state == 'absent')
    assert result['computed_total'] == (13 if index_state == 'absent' else None)
    assert result['status'] == ('consistent' if index_state == 'absent' else 'not_checked')
