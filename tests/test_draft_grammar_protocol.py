"""Protocol 6 changes registered drafting, never terminal scientific checks."""
from copy import deepcopy
from dataclasses import replace
import hashlib
import json
from pathlib import Path

import pytest

from data_sheets_schema import api_runner as api, evidence_assertions as evidence, source_review
from tests.test_claim_clarification_renderer import HISTORICAL, PROTOCOLS
from tests.test_evidence_anonymous_removals import file_fixture
from tests.test_evidence_generation_gate import specification
from tests.test_source_metadata_renderer import fixture as metadata_fixture, audit, report, RAW
from tests.test_source_review import review_for, CHUNKS


LEGACY = {**HISTORICAL, 17: '083b90de0c82ea464686e6f9d46e6cefb09cce7c98bb55aab2d6054037a4045a'}


def test_historical_bytes_and_defaults_stay_fixed(monkeypatch):
    assert {v: api.assembly_digest(v)['sha256'] for v in LEGACY} == LEGACY
    root = Path(__file__).resolve().parents[1]
    for v, digest in PROTOCOLS.items():
        assert hashlib.sha256((root / f'src/download/prompts/evidence_protocol_v{v}.md').read_bytes()).hexdigest() == digest
    assert evidence.protocol_for_renderer(17) == 5
    assert evidence.protocol_for_renderer(18) == 6
    before = api.assembly_digest(18)
    monkeypatch.setattr(api, 'DRAFT_GRAMMAR_CONTRACT_V18', api.DRAFT_GRAMMAR_CONTRACT_V18 + '\nChanged.\n')
    assert api.assembly_digest(18) != before
    assert {v: api.assembly_digest(v)['sha256'] for v in LEGACY} == LEGACY


def test_protocol_carries_all_prior_scientific_text_and_explicit_permission_boundary():
    prompts = Path(__file__).resolve().parents[1] / 'src/download/prompts'
    old = (prompts / 'evidence_protocol_v5.md').read_text()
    new = (prompts / 'evidence_protocol_v6.md').read_text()
    scientific_heading = '### Relationships and document attribution'
    assert new.split(scientific_heading, 1)[1].replace(
        '### Required source review (v6 / source_review v2; unchanged scientific requirements)',
        '### Required source review (v5 / source_review v2)') == old.split(scientific_heading, 1)[1]
    assert 'A failed source review is terminal for this attempt' in new
    assert 'Protocol v6 and renderer 18 alone grant no draft or retry permission.' in new
    assert 'only if its grammar check fails' in new
    assert 'A second grammar failure stops the attempt.' in new
    assert 'does not invoke an evidence or source-review validator' in new
    assert api.sent_text_surfaces()['draft_grammar_contract_v18'] == api.DRAFT_GRAMMAR_CONTRACT_V18


@pytest.mark.parametrize('runtime', ['Claude API (direct)', 'Claude Code'])
@pytest.mark.parametrize('selection', ['selected', 'absent', 'unused'])
def test_both_arms_explicit18_replay_and_authority(tmp_path, runtime, selection):
    original, _ = metadata_fixture(tmp_path, runtime)
    if selection == 'absent':
        original = replace(original, manifest=None)
    elif selection == 'unused':
        original = replace(original, manifest_line='# Source manifest: not used')
    original = replace(original, render_version=17)
    old_instruction = original.instruction
    spec = replace(original, render_version=18)
    assert '## Evidence protocol v6' in spec.instruction
    assert api.DRAFT_GRAMMAR_CONTRACT_V18 in spec.instruction
    assert api.source_metadata_authority(spec) == api.source_metadata_authority(original)
    assert api.source_metadata_block(spec) == api.source_metadata_block(original)
    assert 'PRIVATE_CURATOR_TEXT_MUST_NOT_BE_EVIDENCE' not in spec.instruction
    replay = api.RunSpec.from_render_spec(spec.render_spec(), project=spec.project,
                                        method=spec.method, label=spec.label)
    assert replay.instruction == spec.instruction and original.instruction == old_instruction
    assert replace(spec, render_version=api.AUTO).render_version == (7 if spec.is_agentic else 8)
    if spec.is_agentic:
        command = api.native_evidence_instructions(spec)
        assert '--protocol-version 6' in command
        assert ('--source-manifest' in command) == (selection == 'selected')


@pytest.mark.parametrize('phase', ['audit', 'reconcile_full', 'report', 'report_regate'])
def test_new_draft_contract_is_audit_only_while_other_phases_keep_science(tmp_path, phase):
    contract = api.evidence_phase_contract(phase, 18)
    assert (api.DRAFT_GRAMMAR_CONTRACT_V18 in contract) == (phase == 'audit')
    assert api.CLAIM_CLARIFICATION_CONTRACT_V17 in contract
    if phase != 'report_regate':
        spec = replace(specification(tmp_path), render_version=18)
        carry = {key: ('{"findings": [], "summary": "Synthetic"}' if key == 'Audit findings'
                       else 'description: A sample dataset is planned.\n')
                 for key in api.PHASE_NEEDS[phase]}
        request = api.build_phase(spec, phase, carry=carry)
        assert request.messages[0]['content'][-1]['text'] == api.phase_instruction(phase, 18)


@pytest.mark.parametrize('mutation', [None, 'status', 'quote', 'missing_row', 'wrong_hash',
                                     'artifact_evidence', 'unlinked_revision', 'false_link'])
def test_source_review6_is_exactly5_for_positive_and_negative_scientific_cases(mutation):
    raw = 'description: The project plans an independent validation set.\n'
    review = review_for(raw)
    claim = review['values'][0]['claims'][0]
    claim.update(claim_status='planned', source_status='planned')
    findings = []
    if mutation == 'status':
        claim['claim_status'] = 'applied'
    elif mutation == 'quote':
        claim['text'] = '"' + claim['text'] + '"'
    elif mutation == 'missing_row':
        review['values'] = []
    elif mutation == 'wrong_hash':
        review['sha256'] = '0' * 64
    elif mutation == 'artifact_evidence':
        claim['evidence'] = [{'artifact': 'original_full', 'path': '/description',
                              'op': 'contains', 'quote': claim['text']}]
    elif mutation == 'unlinked_revision':
        claim['verdict'] = 'revise'
    elif mutation == 'false_link':
        findings = [{'review_paths': ['/description']}]
    before = deepcopy(review)
    results = [source_review.check(review, raw=raw, artifact='original_full', chunks=CHUNKS,
                                   audit_findings=findings, protocol_version=v) for v in (5, 6)]
    assert results[0] == results[1] and review == before
    assert bool(results[1]['findings']) == (mutation is not None)


@pytest.mark.parametrize('phase', ['audit', 'report', 'report_regate', 'report_after_repair'])
@pytest.mark.parametrize('mutation', [None, 'wrong_value', 'changed_bytes', 'missing_authority', 'wrong_project'])
def test_real_api6_terminal_admission_uses_exact_authority_without_draft_repair(
        tmp_path, monkeypatch, phase, mutation):
    old, assertion = metadata_fixture(tmp_path)
    spec = replace(old, render_version=18)
    if mutation == 'wrong_value':
        assertion['value'] = 9
    elif mutation == 'changed_bytes':
        spec.manifest.write_bytes(spec.manifest.read_bytes() + b'\n# changed bytes\n')
    elif mutation == 'missing_authority':
        spec = replace(spec, manifest=None)
    elif mutation == 'wrong_project':
        spec.project = 'UNDECLARED'
    persisted, rejected = [], []
    monkeypatch.setattr(api, '_persist_usage', lambda *a: persisted.append(a))
    def reject(s, p, text, usage, result):
        rejected.append(result)
        raise RuntimeError('Synthetic terminal refusal; no paid call or ledger')
    monkeypatch.setattr(api, '_reject_source_response', reject)
    text = json.dumps(audit(assertion)) if phase == 'audit' else report(assertion)
    needed = {k: RAW for k in ('Completed full record', 'Original full record',
              'Original core record', 'Reconciled full record', 'Completed core record')}
    usage = {'source_review_admission': {'state': 'pending'}}
    if mutation is None:
        api._admit_source_response(spec, phase, text, 'end_turn', usage, needed)
        assert usage['source_review_admission']['state'] == 'accepted'
        assert len(persisted) == 1 and rejected == []
    else:
        with pytest.raises(RuntimeError, match='Synthetic terminal refusal'):
            api._admit_source_response(spec, phase, text, 'end_turn', usage, needed)
        assert persisted == [] and len(rejected) == 1
        assert rejected[0]['findings'] and rejected[0]['instrument'] == evidence.instrument(6)
        assert usage['source_review_admission']['state'] == 'pending'


@pytest.mark.parametrize('mutation', [None, 'retained', 'missing_peer', 'changed_original_bytes'])
def test_real_file_checker6_preserves_audit_projection_final_removal_and_report(tmp_path, mutation):
    fixture = file_fixture(tmp_path)
    original, final = (fixture['artifacts'][name] for name in ('original_full', 'final_full'))
    if mutation == 'retained':
        final.write_bytes(original.read_bytes())
    elif mutation == 'missing_peer':
        final.write_text('roles: []\n')
    elif mutation == 'changed_original_bytes':
        original.write_bytes(b'# changed raw original\n' + original.read_bytes())
    outputs = [evidence.check_files(**{**fixture, 'protocol_version': v}) for v in (5, 6)]
    assert outputs[0].pop('instrument') == evidence.instrument(5)
    assert outputs[1].pop('instrument') == evidence.instrument(6)
    assert outputs[0] == outputs[1]
    assert bool(outputs[1]['findings']) == (mutation is not None)


@pytest.mark.parametrize('mutation', [None, 'wrong_metadata_value'])
def test_actual_cli6_accepts_only_valid_original_authority(tmp_path, capsys, mutation):
    spec, assertion = metadata_fixture(tmp_path)
    if mutation:
        assertion['value'] = 9
    original = tmp_path / 'original.yaml'
    original.write_text(RAW)
    path = tmp_path / 'audit.json'
    path.write_text(json.dumps(audit(assertion)))
    code = evidence.main(['--protocol-version', '6', '--audit', str(path),
        '--original-full', str(original), '--bundle', str(spec.bundle), '--manifest', str(spec.chunk_manifest),
        '--source-manifest', str(spec.manifest), '--project', spec.project])
    result = json.loads(capsys.readouterr().out)
    assert code == (1 if mutation else 0)
    assert result['instrument'] == evidence.instrument(6)
    assert result['artifact_sha256']['source_manifest'] == hashlib.sha256(spec.manifest.read_bytes()).hexdigest()
    assert bool(result['findings']) == bool(mutation)


@pytest.mark.parametrize('phase', ['audit', 'report'])
@pytest.mark.parametrize('mutation', ['status', 'artifact_evidence', 'quote'])
def test_actual_api_response_still_stops_on_contract_errors(tmp_path, monkeypatch, phase, mutation):
    spec = replace(specification(tmp_path), render_version=18)
    raw = 'description: A sample dataset is planned.\n'
    chunks, _ = evidence.source_chunks(spec.bundle, spec.chunk_manifest)
    review = review_for(raw, 'original_full' if phase == 'audit' else 'final_full', chunks=chunks)
    claim = review['values'][0]['claims'][0]
    if mutation == 'status':
        claim.update(claim_status='applied', source_status='planned')
    elif mutation == 'artifact_evidence':
        claim['evidence'] = [{'artifact': 'original_full', 'path': '/description',
                              'op': 'contains', 'quote': claim['text']}]
    else:
        claim['text'] = '"' + claim['text'] + '"'
    body = ({'findings': [], 'summary': 'Synthetic', 'source_review': review} if phase == 'audit'
            else {'claims': [], 'source_review': review})
    text = json.dumps(body)
    if phase == 'report':
        text = '# Report\n\n## Evidence assertions\n```json\n' + text + '\n```\n'
    rejected = []
    def reject(*args):
        rejected.append(args[-1])
        raise RuntimeError('Synthetic terminal contract failure')
    monkeypatch.setattr(api, '_reject_source_response', reject)
    monkeypatch.setattr(api, '_persist_usage', lambda *a: pytest.fail('A failed review was admitted'))
    needed = {k: raw for k in ('Completed full record', 'Original full record',
              'Original core record', 'Reconciled full record', 'Completed core record')}
    usage = {'source_review_admission': {'state': 'pending'}}
    before = deepcopy(body)
    with pytest.raises(RuntimeError, match='Synthetic terminal contract failure'):
        api._admit_source_response(spec, phase, text, 'end_turn', usage, needed)
    assert len(rejected) == 1 and rejected[0]['findings']
    assert body == before and usage['source_review_admission']['state'] == 'pending'


@pytest.mark.parametrize('value', [None, True, False, 6.0, '6', 8])
def test_bad_protocol_selectors_remain_rejected(value):
    with pytest.raises(ValueError, match='unsupported'):
        evidence.instrument(value)
    with pytest.raises(ValueError, match='unsupported'):
        source_review.check(None, raw='description: example\n', artifact='original_full',
                            chunks={}, protocol_version=value)
