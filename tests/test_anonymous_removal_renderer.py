"""Explicit renderer 15 selects protocol 4 without changing historical requests."""
from dataclasses import replace
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from data_sheets_schema import api_runner as api, evidence_assertions as evidence
from tests.test_evidence_generation_gate import specification


# Captured from main 310f2854f before implementation. These bind all historical
# phase instruction/layout bytes, not a comparison between two new-code calls.
HISTORICAL_ASSEMBLY = {
    **{v: '39fadef4fcbd7d25c9e494abd8671d319897ba72ed89d7fa87617e47654285c3' for v in range(1, 10)},
    10: 'efd42e290b8fa347d663fd7953d896d45a12827bca0049df64d9b74dd48c4eba',
    11: 'b7e2f4dcd2db81121c03204f1ce1171682f5e1894b7164f9e37a4d2e6810578d',
    12: '1e3b4d5df240f67f9aae814e4494017b79804ecce06a16504eb0b084f5082a4a',
    13: 'adc8d2982d744dced2505134e18fde58a1b97ea079b40df7cd7e146ffeb549b5',
    14: 'd5f55d9ff58bbcbf94e70a4528e13bd0b2815a9a87e1d8fd0e6ab7a912bdf924',
}


def test_historical_assembly_bytes_and_protocol_selection_are_preserved():
    assert {v: api.assembly_digest(v)['sha256'] for v in HISTORICAL_ASSEMBLY} == HISTORICAL_ASSEMBLY
    assert api.assembly_digest(15)['sha256'] not in HISTORICAL_ASSEMBLY.values()
    assert [evidence.protocol_for_renderer(v) for v in range(9, 16)] == [1, 1, 2, 3, 3, 3, 4]


@pytest.mark.parametrize('runtime', ['Claude Code', 'Claude API (direct)'])
def test_both_arms_receive_and_replay_the_same_explicit_v4_contract(tmp_path, runtime):
    original = replace(specification(tmp_path, runtime), render_version=14)
    recorded = original.render_spec()
    text14 = original.instruction
    spec = replace(original, render_version=15)
    text15 = spec.instruction
    assert '## Evidence protocol v4' in text15
    assert api.ANONYMOUS_REMOVAL_CONTRACT_V15 in text15
    assert 'anonymous_structure_v1' not in text14
    assert original.render_spec() == recorded and original.instruction == text14
    replay = api.RunSpec.from_render_spec(spec.render_spec(), project=spec.project,
                                         method=spec.method, label=spec.label)
    assert replay.instruction == text15
    assert replace(spec, render_version=api.AUTO).render_version == (7 if spec.is_agentic else 8)
    if spec.is_agentic:
        assert "--protocol-version 4" in api.native_evidence_instructions(spec)
    else:
        request = api.build_phase(spec, 'audit', carry={'Completed full record': 'description: A sample dataset is planned.\n'})
        assert api.ANONYMOUS_REMOVAL_CONTRACT_V15 in request.messages[0]['content'][-1]['text']


def test_new_contract_changes_only_its_own_assembly_identity(monkeypatch):
    before = api.assembly_digest(15)
    monkeypatch.setattr(api, 'ANONYMOUS_REMOVAL_CONTRACT_V15', api.ANONYMOUS_REMOVAL_CONTRACT_V15 + '\nChanged.\n')
    assert api.assembly_digest(15) != before
    assert {v: api.assembly_digest(v)['sha256'] for v in HISTORICAL_ASSEMBLY} == HISTORICAL_ASSEMBLY


def test_generation_registration_exposes_explicit_v15_without_changing_its_default():
    path = Path(__file__).resolve().parents[1] / 'notes/matched_cborg_2026-09-13/prepare_registration.py'
    definition = importlib.util.spec_from_file_location('anonymous_renderer_registration', path)
    registration = importlib.util.module_from_spec(definition)
    definition.loader.exec_module(registration)
    parser = registration.build_parser()
    assert parser.parse_args([]).render_version == 9
    assert parser.parse_args(['--render-version', '15']).render_version == 15


@pytest.mark.parametrize('version, expected', [(14, 3), (15, 4)])
@pytest.mark.parametrize('phase', ['audit', 'report', 'report_regate', 'report_after_repair'])
def test_api_admission_dispatches_the_registered_protocol_before_persisting_usage(
        tmp_path, monkeypatch, version, expected, phase):
    spec = replace(specification(tmp_path), render_version=version)
    called = []
    def audit(value, *, artifacts, chunks, protocol_version):
        called.append(protocol_version)
        return {'checked': True, 'findings': []}
    def report(value, *, artifacts, chunks, protocol_version):
        called.append(protocol_version)
        return {'source_review_final': {'findings': []}}
    monkeypatch.setattr(evidence, 'check_audit', audit)
    monkeypatch.setattr(evidence, 'check_report', report)
    monkeypatch.setattr(api, '_persist_usage', lambda *a: None)
    monkeypatch.setattr(api, '_reject_source_response', lambda *a: pytest.fail('valid response rejected'))
    monkeypatch.setattr(api, '_extract', lambda text, kind: text)
    text = json.dumps({'findings': [], 'summary': 'Synthetic dispatch fixture'}) if phase == 'audit' else 'Synthetic report'
    usage = {'source_review_admission': {'state': 'pending'}}
    needed = {key: 'description: fixture\n' for key in ('Completed full record', 'Original full record',
              'Original core record', 'Reconciled full record', 'Completed core record')}
    api._admit_source_response(spec, phase, text, 'end_turn', usage, needed)
    assert called == [expected]
    assert usage['source_review_admission']['state'] == 'accepted'


@pytest.mark.parametrize('version, expected', [(14, 3), (15, 4)])
def test_unusable_source_response_records_the_actual_instrument(tmp_path, monkeypatch, version, expected):
    spec = replace(specification(tmp_path), render_version=version)
    rejected = []
    monkeypatch.setattr(api, '_reject_source_response', lambda s, p, t, u, out: rejected.append(out))
    api._refuse_unusable_source_review(spec, 'audit', 'synthetic rejection', '{}', {})
    assert rejected[0]['instrument'] == evidence.instrument(expected)
    assert rejected[0]['checked'] is False


@pytest.mark.parametrize('report', [False, True])
@pytest.mark.parametrize('mutation', [None, 'retained', 'missing_peer', 'changed_original_bytes'])
def test_api_reconciliation_and_report_bind_anonymous_removal_to_original_bytes(tmp_path, report, mutation):
    from tests.test_evidence_anonymous_removals import file_fixture

    fixture = file_fixture(tmp_path)
    original = fixture['artifacts']['original_full']
    final = fixture['artifacts']['final_full']
    if mutation == 'retained':
        final.write_bytes(original.read_bytes())
    elif mutation == 'missing_peer':
        final.write_text('roles: []\n')
    elif mutation == 'changed_original_bytes':
        original.write_bytes(b'# changed exact original\n' + original.read_bytes())
    core = tmp_path / 'core.yaml'
    core.write_bytes(final.read_bytes())
    spec = SimpleNamespace(render_version=15, bundle=fixture['bundle'],
                           chunk_manifest=fixture['manifest'], full_path=final,
                           core_path=core, report_path=fixture['report'])
    carry = {'Audit findings': fixture['audit'].read_text(),
             'Original full record': original.read_text()}
    result = api.evidence_checks_block(spec, carry, reconciled=True, report=report)
    assert result['checked'] is True
    if mutation is None:
        assert result['findings'] == []
        if report:
            assert result['source_review_final']['claims_checked'] == 1
    elif mutation == 'retained':
        assert any(p['kind'] == 'unsupported_relationship_retained' for p in result['findings'])
    elif mutation == 'missing_peer':
        assert any('unselected' in p['detail'] for p in result['findings'])
    else:
        assert any('digest' in p['detail'] for p in result['findings'])
