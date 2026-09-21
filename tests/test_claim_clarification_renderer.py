"""Renderer 17 clarifies existing rules without changing protocol or old requests."""
from copy import deepcopy
from dataclasses import replace
import hashlib
import importlib.util
import json
from pathlib import Path

import pytest
import yaml

from data_sheets_schema import api_runner as api, chunking, evidence_assertions as evidence
from tests.test_evidence_generation_gate import specification
from tests.test_source_metadata_renderer import LEGACY, fixture as metadata_fixture
from tests.test_source_review import review_for


# Captured from unchanged 20bcd81 before implementing renderer 17.
HISTORICAL = {**LEGACY, 16: 'ea4117e600ebeb3a0bbd940c2c7d9047e5925f68faac2d876a48f6a8e87127d1'}
PROTOCOLS = {
    1: '83019ee2189d7a2e4d09924c96cbba191c76b2e90523c58fb486856d74976637',
    2: '99ba8e9aff1755183023fd23f07c2a1bdd2dfc31c4e41a85cc9e0e839fc1e5b2',
    3: 'ab1ebfce603ac112f845f81b6c7fdf3f10a01777fd3e3760069101e55beb038a',
    4: 'b4f767ec3ada61c97711ff4db4d201f57b3854bd385c116c29bb9f75c4c3b3e2',
    5: '8b57631b3f462fc6fc547530c9b7d5808322ab591e98d810f751abae3a01eda7',
}
RAW = 'description: A sample dataset is planned.\n'


def test_every_historical_assembly_and_protocol_is_unchanged(monkeypatch):
    assert {v: api.assembly_digest(v)['sha256'] for v in HISTORICAL} == HISTORICAL
    root = Path(__file__).resolve().parents[1]
    for version, digest in PROTOCOLS.items():
        assert hashlib.sha256((root / f'src/download/prompts/evidence_protocol_v{version}.md').read_bytes()).hexdigest() == digest
    assert evidence.protocol_for_renderer(17) == evidence.protocol_for_renderer(16) == 5
    current = api.assembly_digest(17)
    assert current['sha256'] not in HISTORICAL.values()
    monkeypatch.setattr(api, 'CLAIM_CLARIFICATION_CONTRACT_V17', api.CLAIM_CLARIFICATION_CONTRACT_V17 + 'Changed.\n')
    assert api.assembly_digest(17) != current
    assert {v: api.assembly_digest(v)['sha256'] for v in HISTORICAL} == HISTORICAL


@pytest.mark.parametrize('runtime', ['Claude API (direct)', 'Claude Code'])
@pytest.mark.parametrize('selection', ['selected', 'absent', 'unused'])
def test_both_arms_replay_explicit17_with_unchanged_authority_and_defaults(tmp_path, runtime, selection):
    old, _ = metadata_fixture(tmp_path, runtime)
    if selection == 'absent':
        old = replace(old, manifest=None)
    elif selection == 'unused':
        old = replace(old, manifest_line='# Source manifest: not used')
    previous = old.instruction
    spec = replace(old, render_version=17)
    assert api.CLAIM_CLARIFICATION_CONTRACT_V17 not in previous
    assert api.CLAIM_CLARIFICATION_CONTRACT_V17 in spec.instruction
    assert api.source_metadata_authority(spec) == api.source_metadata_authority(old)
    assert api.source_metadata_block(spec) == api.source_metadata_block(old)
    assert 'PRIVATE_CURATOR_TEXT_MUST_NOT_BE_EVIDENCE' not in spec.instruction
    assert '## Evidence protocol v5' in spec.instruction
    replay = api.RunSpec.from_render_spec(spec.render_spec(), project=spec.project,
                                         method=spec.method, label=spec.label)
    assert replay.instruction == spec.instruction
    assert old.instruction == previous
    assert replace(spec, render_version=api.AUTO).render_version == (7 if spec.is_agentic else 8)
    if spec.is_agentic:
        command = api.native_evidence_instructions(spec)
        assert '--protocol-version 5' in command
        assert ('--source-manifest' in command) == (selection == 'selected')


@pytest.mark.parametrize('phase', ['audit', 'reconcile_full', 'report'])
def test_actual_api_phase_payload_delivers_clarification_after_artifacts(tmp_path, phase):
    spec = replace(specification(tmp_path), render_version=17)
    carry = {key: ('{"findings": [], "summary": "Synthetic"}' if key == 'Audit findings' else RAW)
             for key in api.PHASE_NEEDS[phase]}
    request = api.build_phase(spec, phase, carry=carry)
    assert request.messages[0]['content'][-1]['text'] == api.phase_instruction(phase, 17)
    assert api.CLAIM_CLARIFICATION_CONTRACT_V17 in request.messages[0]['content'][-1]['text']


@pytest.mark.parametrize('contradictions', [None, [{'kind': 'report_claim', 'detail': 'Synthetic discrepancy'}]])
def test_actual_report_after_repair_and_recheck_requests_keep_clarification(tmp_path, monkeypatch, contradictions):
    spec = replace(specification(tmp_path), render_version=17)
    carry = {key: ('{"findings": [], "summary": "Synthetic"}' if key == 'Audit findings' else RAW)
             for key in api.PHASE_NEEDS['report']}
    seen = []

    def capture(*args, **kwargs):
        seen.append((args, kwargs))
        raise RuntimeError('Synthetic stop at send boundary; no provider or ledger')

    monkeypatch.setattr(api, '_call_with_usage', capture)
    settings = {'name': 'claude-opus-5', 'max_tokens': 64000, 'temperature_applies': False}
    assert api._regenerate_report(spec, None, settings, [], carry, contradictions=contradictions) is False
    assert len(seen) == 1
    args, sent = seen[0]
    assert args[1] == 'report_after_repair'
    instruction = sent['messages'][0]['content'][-1]['text']
    assert instruction == api.phase_instruction('report_regate' if contradictions is not None else 'report', 17)
    assert api.CLAIM_CLARIFICATION_CONTRACT_V17 in instruction
    assert not spec.report_path.exists()


def test_generation_cli_is_explicit_and_keeps_its_default():
    path = Path(__file__).resolve().parents[1] / 'notes/matched_cborg_2026-09-13/prepare_registration.py'
    definition = importlib.util.spec_from_file_location('clarification_generation_prepare', path)
    module = importlib.util.module_from_spec(definition)
    definition.loader.exec_module(module)
    parser = module.build_parser()
    assert parser.parse_args([]).render_version == 9
    assert parser.parse_args(['--render-version', '16']).render_version == 16
    assert parser.parse_args(['--render-version', '17']).render_version == 17
    with pytest.raises(SystemExit):
        parser.parse_args(['--render-version', '18'])


@pytest.mark.parametrize('value', [
    'Alpha', '"Alpha"', 'The label is "Alpha".', "A participant's label.",
    'A path C:\\archive\\sample.', 'A “quoted” label — retained.',
    'The label\nis Alpha.',
])
@pytest.mark.parametrize('phase', ['audit', 'report', 'report_regate', 'report_after_repair'])
def test_real_api_admission_preserves_literal_quotes_and_rejects_extra_wrappers(tmp_path, monkeypatch, value, phase):
    spec = specification(tmp_path)
    spec.bundle.write_text('FILE: protocol.txt\nPATH: protocol.txt\n' + value + '\n')
    spec.chunk_manifest.write_text(chunking.dump_manifest(chunking.build_manifest(spec.bundle)))
    spec = replace(spec, render_version=17)
    raw = yaml.safe_dump({'description': value}, allow_unicode=True)
    chunks, _ = evidence.source_chunks(spec.bundle, spec.chunk_manifest)
    artifact = 'original_full' if phase == 'audit' else 'final_full'
    review = review_for(raw, artifact, chunks=chunks)
    before = deepcopy(review)
    rejected, accepted = [], []

    def reject(s, p, text, usage, out):
        rejected.append(out)
        raise RuntimeError('Synthetic admission refusal; no preservation or ledger write')

    monkeypatch.setattr(api, '_reject_source_response', reject)
    monkeypatch.setattr(api, '_persist_usage', lambda *args: accepted.append(args))
    needed = {key: raw for key in ('Completed full record', 'Original full record',
                                   'Original core record', 'Reconciled full record', 'Completed core record')}

    def deliver(payload):
        body = ({'findings': [], 'summary': 'Synthetic literal review', 'source_review': payload}
                if phase == 'audit' else {'claims': [], 'source_review': payload})
        text = json.dumps(body, ensure_ascii=False)
        if phase != 'audit':
            text = '# Report\n\n## Evidence assertions\n```json\n' + text + '\n```\n'
        usage = {'source_review_admission': {'state': 'pending'}}
        api._admit_source_response(spec, phase, text, 'end_turn', usage, needed)
        return usage

    assert deliver(review)['source_review_admission']['state'] == 'accepted'
    assert len(accepted) == 1 and rejected == [] and review == before
    extra = deepcopy(review)
    extra['values'][0]['claims'][0]['text'] = '"' + value + '"'
    with pytest.raises(RuntimeError, match='Synthetic admission refusal'):
        deliver(extra)
    assert len(accepted) == 1 and len(rejected) == 1
    assert any('claim text must quote this value' in f.get('detail', '') for f in rejected[0]['findings'])
    assert extra['values'][0]['claims'][0]['text'] == '"' + value + '"'
    if '"' in value:
        stripped = deepcopy(review)
        stripped['values'][0]['claims'][0]['text'] = value.replace('"', '')
        with pytest.raises(RuntimeError, match='Synthetic admission refusal'):
            deliver(stripped)
        assert len(accepted) == 1 and len(rejected) == 2


def test_authored_json_example_distinguishes_syntax_from_literal_quote_content():
    contract = api.CLAIM_CLARIFICATION_CONTRACT_V17
    correct, wrong = '{"text": "Alpha"}', r'{"text": "\"Alpha\""}'
    assert correct in contract and wrong in contract
    assert json.loads(correct)['text'] == 'Alpha'
    assert json.loads(wrong)['text'] == '"Alpha"'
    assert api.sent_text_surfaces()['claim_clarification_contract_v17'] == contract
