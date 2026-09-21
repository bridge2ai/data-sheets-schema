"""Explicit audit guidance preserves every earlier instrument and launch scope."""
from dataclasses import replace
import json
from types import SimpleNamespace

import pytest
import yaml

from data_sheets_schema import api_runner as api, evidence_assertions, schema_semantics
from tests.test_draft_grammar_protocol import LEGACY
from tests.test_evidence_generation_gate import specification


HISTORICAL = {**LEGACY, 18: '8994bb0d648a354c9d14fc81761a2264f74922ededa9ec4b51fb99072f2f3002'}


def schemas(tmp_path):
    result = []
    for root, name, meaning in [('Dataset', 'full', 'Upper steady current in amperes.'),
                                ('CoreDataset', 'core', 'Cooldown duration in seconds.')]:
        path = tmp_path / (name + '.yaml')
        path.write_text(yaml.safe_dump({
            'id': 'https://example.org/' + name, 'name': name, 'default_range': 'string',
            'prefixes': {'xsd': 'http://www.w3.org/2001/XMLSchema#'},
            'types': {'string': {'base': 'str', 'uri': 'xsd:string'}},
            'classes': {
                root: {'attributes': {'configuration': {'range': 'Envelope', 'inlined': True}}},
                'Envelope': {'description': name + ' operating constraints.',
                             'attributes': {'setting': {'description': meaning}}}}}, sort_keys=False))
        result.append(path)
    return tuple(result)


def carry():
    return {'Completed full record': 'configuration:\n  setting: private_value_full\n',
            'Completed core record': 'configuration:\n  setting: private_value_core\n'}


def guidance_blocks(request):
    return [b['text'] for b in request.messages[0]['content']
            if b['text'].startswith(api.SCHEMA_SEMANTICS_HEADER_V19)]


def test_legacy_assemblies_unchanged_and_new_surfaces_are_bound(monkeypatch):
    assert {v: api.assembly_digest(v)['sha256'] for v in HISTORICAL} == HISTORICAL
    assert evidence_assertions.protocol_for_renderer(19) == 6
    before = api.assembly_digest(19)
    monkeypatch.setattr(api, 'SCHEMA_SEMANTICS_HEADER_V19', api.SCHEMA_SEMANTICS_HEADER_V19 + 'Changed.\n')
    assert api.assembly_digest(19) != before
    before = api.assembly_digest(19)
    monkeypatch.setattr(api, 'SCHEMA_SEMANTICS_CONTRACT_V19', api.SCHEMA_SEMANTICS_CONTRACT_V19 + 'Changed.\n')
    assert api.assembly_digest(19) != before
    assert {v: api.assembly_digest(v)['sha256'] for v in HISTORICAL} == HISTORICAL


@pytest.mark.parametrize('runtime', ['Claude API (direct)', 'Claude Code'])
def test_shared_audit_uses_each_exact_schema_and_omits_record_values_from_guidance(tmp_path, runtime):
    spec = replace(specification(tmp_path, runtime), render_version=19)
    request = api.build_phase(spec, 'audit', carry=carry(), _audit_schema_paths=schemas(tmp_path))
    blocks = guidance_blocks(request)
    assert len(blocks) == 1
    payload = json.loads(blocks[0].removeprefix(api.SCHEMA_SEMANTICS_HEADER_V19))
    assert set(payload['records']) == {'original_full', 'original_core'}
    assert 'Upper steady current in amperes.' in blocks[0]
    assert 'Cooldown duration in seconds.' in blocks[0]
    assert all('private_value' not in text for text in blocks)
    assert request.messages[0]['content'][-1]['text'] == api.phase_instruction('audit', 19)
    assert api.SCHEMA_SEMANTICS_CONTRACT_V19 in spec.instruction
    replay = api.RunSpec.from_render_spec(spec.render_spec(), project=spec.project,
                                        method=spec.method, label=spec.label)
    assert replay.instruction == spec.instruction
    replay_request = api.build_phase(replay, 'audit', carry=carry(), _audit_schema_paths=schemas(tmp_path))
    assert replay_request.messages == request.messages


def test_changed_nested_meaning_moves_actual_new_payload_not_legacy_digest(tmp_path):
    spec = replace(specification(tmp_path), render_version=19)
    paths = schemas(tmp_path)
    before = api.build_phase(spec, 'audit', carry=carry(), _audit_schema_paths=paths)
    paths[0].write_text(paths[0].read_text().replace('Upper steady current in amperes.', 'Maximum pulse duration in seconds.'))
    after = api.build_phase(spec, 'audit', carry=carry(), _audit_schema_paths=paths)
    assert guidance_blocks(after) != guidance_blocks(before)
    assert before.cached_blocks == after.cached_blocks


@pytest.mark.parametrize('version', [14, 17, 18])
def test_legacy_audit_never_invokes_new_helper(tmp_path, monkeypatch, version):
    monkeypatch.setattr(schema_semantics, 'render_pair', lambda *a, **k: pytest.fail('Legacy changed'))
    spec = replace(specification(tmp_path), render_version=version)
    assert guidance_blocks(api.build_phase(spec, 'audit', carry=carry())) == []


@pytest.mark.parametrize('phase', ['reconcile_full', 'report'])
def test_phase4_keeps_ordinary_schema_presentation_and_no_original_shape_claim(tmp_path, monkeypatch, phase):
    monkeypatch.setattr(schema_semantics, 'render_pair', lambda *a, **k: pytest.fail('Audit guidance leaked'))
    spec = replace(specification(tmp_path), render_version=19)
    values = {key: 'description: Synthetic.\n' for key in api.PHASE_NEEDS[phase]}
    assert guidance_blocks(api.build_phase(spec, phase, carry=values)) == []
    assert api.SCHEMA_SEMANTICS_CONTRACT_V19 not in api.evidence_phase_contract(phase, 19)
    assert api.evidence_phase_contract(phase, 19) == api.evidence_phase_contract(phase, 18)


@pytest.mark.parametrize('version,phase,paths', [(18, 'audit', (1, 2)), (19, 'report', (1, 2)),
                                                (19, 'audit', ('single',)), (19, 'audit', ['a', 'b']),
                                                (19, 'audit', ())])
def test_schema_override_cannot_be_silently_ignored(tmp_path, version, phase, paths):
    spec = replace(specification(tmp_path), render_version=version)
    with pytest.raises(ValueError, match='schema paths'):
        api.build_phase(spec, phase, carry=carry(), _audit_schema_paths=paths)


def test_real_builder_rejects_bad_record_while_estimate_uses_enforced_size_bound(tmp_path, monkeypatch):
    spec = replace(specification(tmp_path), render_version=19)
    bad = {key: 'x' * 200 for key in carry()}
    with pytest.raises(schema_semantics.SemanticGuidanceError):
        api.build_phase(spec, 'audit', carry=bad)
    monkeypatch.setattr(schema_semantics, 'render_pair', lambda *a, **k: pytest.fail('Estimated fake record parsed'))
    estimated = api.build_phase(spec, 'audit', carry=bad, _source_review_estimate=True)
    blocks = guidance_blocks(estimated)
    assert len(blocks) == 1
    assert 'ESTIMATE ONLY: ' + 'x' * schema_semantics.MAX_PAIR_RENDER_BYTES in blocks[0]
    monkeypatch.setattr(api, '_carry_sizes', lambda spec: ({key: 200 for key in carry()}, 'synthetic sizes'))
    plan = api.plan(spec)
    assert 'maximum permitted rendered byte size' in plan['estimate_basis']
    assert 'not generation execution' in plan['estimate_basis']


def test_generation19_refused_before_outputs_or_client(tmp_path, monkeypatch):
    spec = replace(specification(tmp_path), render_version=19)
    monkeypatch.setattr(api, '_exclusive_run', lambda *a: pytest.fail('Output/lock boundary crossed'))
    client = SimpleNamespace(messages=SimpleNamespace(create=lambda **k: pytest.fail('Provider contacted')))
    for operation in (lambda: api.execute(spec, client=client),
                      lambda: api._execute(spec, resume=False, client=client)):
        with pytest.raises(ValueError, match='separately registered audit continuation'):
            operation()
    assert not spec.full_path.parent.exists()


def test_new_sent_text_surfaces_are_inventory_visible():
    surfaces = api.sent_text_surfaces()
    assert surfaces['schema_semantics_header_v19'] == api.SCHEMA_SEMANTICS_HEADER_V19
    assert surfaces['schema_semantics_contract_v19'] == api.SCHEMA_SEMANTICS_CONTRACT_V19
