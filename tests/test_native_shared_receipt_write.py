"""Native write adapter tests; the capture stub is not native runtime evidence."""
import copy
import hashlib
from pathlib import Path

from click.testing import CliRunner
import pytest
import yaml

import data_sheets_schema
from data_sheets_schema import backfill_checks as bc, receipts as rc
from tests.test_native_shared_selection import declaration
from tests.test_native_shared_receipt_readers import routed


@pytest.fixture
def write_case(routed):
    cap, spec, cli, paths, receipt, calls, result = routed
    md5 = hashlib.md5(cap.raw('bundle')).hexdigest()
    full = {'name': 'Synthetic', 'description': 'Entire selected source.'}
    original = {'bundle_md5': md5, 'chunks': [{'id': 'chunk-1', 'status': 'extracted',
        'extracted': [{'slot': 'name', 'snippet': 'Synthetic'}]}]}
    effective = copy.deepcopy(original)
    effective['chunks'][0]['extracted'].append(
        {'slot': 'description', 'snippet': 'Entire selected source.', 'origin': 'rereceipt'})
    paths['full'].write_text(yaml.safe_dump(full), encoding='utf-8')
    receipt.write_text(yaml.safe_dump(original), encoding='utf-8')
    record = {'run': cap.document()['run'], 'prompts': {'request': {'spec': spec}},
        'inputs': {'bundle_path': cap.document()['inputs']['bundle']['path'],
                   'bundle_md5': md5, 'receipt_expected': True},
        'untouched': {'meaning': 'retained original provenance'}}
    paths['provenance'].write_text(yaml.safe_dump(record), encoding='utf-8')
    claims_path = rc.claims_path(paths['core_dir'], 'SYNTHETIC')
    claims_path.write_bytes(b'old_sidecar: preserve until capture succeeds\n')
    result.update(native_receipt_stage='final', final_stage_complete=True)
    expected_claims = rc.claim_receipts(effective, full, identifier_bases=())
    before = {p: p.read_bytes() for p in (*paths.values(), receipt, claims_path) if p.is_file()}
    return cap, cli, paths, receipt, calls, result, record, claims_path, expected_claims, before


def args_for(cap, explicit):
    args = ['--method', 'claudecode_direct', '--label', 'offline-test',
            '--project', 'SYNTHETIC', '--write']
    if explicit:
        args += ['--native-shared-selection', cap.registration.pin.path]
    return args


@pytest.mark.parametrize('explicit', [False, True], ids=['saved-record', 'explicit-and-saved'])
def test_native_write_uses_effective_claims_before_changing_either_output(write_case, monkeypatch, explicit):
    cap, cli, paths, receipt, calls, checked, record, claims_path, expected_claims, before = write_case
    order = []
    expected_block = copy.deepcopy(checked)

    def captured_claims(spec, *, record, full_path, receipt_path, expected_block):
        assert spec is None
        assert record == yaml.safe_load(before[paths['provenance']])
        assert (full_path, receipt_path) == (paths['full'], receipt)
        assert expected_block == checked and 'recorded_by' not in expected_block
        assert {p: p.read_bytes() for p in before} == before
        order.append('claims')
        return copy.deepcopy(expected_claims)

    monkeypatch.setattr(data_sheets_schema.native_shared_capture, 'recorded_receipt_claims',
                        captured_claims, raising=False)
    original_apply = bc.apply

    def apply(*args, **kwargs):
        assert order == ['claims']
        order.append('apply')
        return original_apply(*args, **kwargs)

    monkeypatch.setattr(bc, 'apply', apply)
    monkeypatch.setattr(rc, 'load_receipt', lambda *a, **k: pytest.fail('native CLI reread original receipt'))
    outcome = CliRunner().invoke(cli.check, args_for(cap, explicit))
    assert outcome.exit_code == 0, (outcome.output, outcome.exception)
    assert order == ['claims', 'apply']
    assert calls == [('recorded', None, {'record': record, 'full_path': paths['full'], 'receipt_path': receipt})]
    saved = yaml.safe_load(paths['provenance'].read_bytes())
    assert saved == {**record, 'receipts': {**expected_block, 'recorded_by': 'd4d receipts check'}}
    assert yaml.safe_load(claims_path.read_bytes()) == expected_claims
    assert 'description' in expected_claims['slots']  # Absent from the ordinary original receipt.
    assert {p: p.read_bytes() for p in (paths['full'], receipt)} == {
        p: before[p] for p in (paths['full'], receipt)}


@pytest.mark.parametrize('failure', ['changed-authority', 'missing-artifact', 'serialization'])
@pytest.mark.parametrize('explicit', [False, True], ids=['saved-record', 'explicit-and-saved'])
def test_native_claims_refusal_preserves_both_outputs(write_case, monkeypatch, explicit, failure):
    cap, cli, paths, receipt, _, _, _, claims_path, _, before = write_case

    def refused(*args, **kwargs):
        assert {p: p.read_bytes() for p in before} == before
        if failure == 'changed-authority':
            raise ValueError('recomputed receipt block differs')
        if failure == 'missing-artifact':
            raise OSError('captured effective receipt is unavailable')
        return {'unserializable': object()}

    monkeypatch.setattr(data_sheets_schema.native_shared_capture, 'recorded_receipt_claims', refused, raising=False)
    monkeypatch.setattr(bc, 'apply', lambda *a, **k: pytest.fail('provenance changed before claims refusal'))
    original_write = Path.write_text

    def guarded_write(path, *args, **kwargs):
        assert path not in {paths['provenance'], claims_path}, 'output changed before claims refusal'
        return original_write(path, *args, **kwargs)

    monkeypatch.setattr(Path, 'write_text', guarded_write)
    outcome = CliRunner().invoke(cli.check, args_for(cap, explicit))
    assert outcome.exit_code == 1 and 'native receipt claims refused:' in outcome.output, outcome.output
    assert {p: p.read_bytes() for p in before} == before


def test_native_write_still_requires_record_before_any_claim_capture(routed, monkeypatch):
    cap, _, cli, paths, receipt, calls, _ = routed
    before = {p: p.read_bytes() for p in (paths['full'], receipt)}
    monkeypatch.setattr(data_sheets_schema.native_shared_capture, 'recorded_receipt_claims',
                        lambda *a, **k: pytest.fail('claims captured before record exists'), raising=False)
    outcome = CliRunner().invoke(cli.check, args_for(cap, True))
    assert outcome.exit_code == 1 and 'no provenance record' in outcome.output
    assert calls == [] and not paths['provenance'].exists()
    assert {p: p.read_bytes() for p in before} == before
