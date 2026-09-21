"""The v5 evidence authority reaches real API gates and both prompt arms."""
from copy import deepcopy
from dataclasses import replace
import hashlib
import json
from pathlib import Path

import pytest
import yaml

from data_sheets_schema import api_runner as api, evidence_assertions as evidence, source_review
from tests.test_anonymous_removal_renderer import HISTORICAL_ASSEMBLY
from tests.test_evidence_generation_gate import specification
from tests.test_source_review import review_for


LEGACY = {**HISTORICAL_ASSEMBLY,
          15: '79d0d4a45d908a0f699bf15af53c24854b16c00bce4a94596a5687a584d01097'}
RAW = 'source_caveats: The protocol source has declared tier 2.\n'


def fixture(tmp_path, runtime='Claude API (direct)'):
    base = specification(tmp_path, runtime)
    manifest = tmp_path / 'sources.yaml'
    manifest.write_text(yaml.safe_dump({
        'version': 1, 'source_priority': {2: ['documentation']},
        'curation_note': 'PRIVATE_CURATOR_TEXT_MUST_NOT_BE_EVIDENCE',
        'projects': {'EXAMPLE': [{'id': 'protocol', 'source_type': 'documentation',
                                 'processed_file': 'protocol.txt'}]}}))
    spec = replace(base, manifest=manifest, manifest_line=f'# Source manifest: {manifest}',
                   render_version=16)
    assertion = {'provenance': 'source_manifest',
                 'sha256': hashlib.sha256(manifest.read_bytes()).hexdigest(),
                 'source_id': 'protocol', 'source': 'protocol.txt',
                 'field': 'effective_priority', 'value': 2}
    return spec, assertion


def review(assertion, artifact='original_full'):
    inventory = source_review.inventory(RAW, artifact)
    return {**inventory, 'values': [{'path': '/source_caveats', 'claims': [{
        'text': inventory['values'][0]['text'], 'verdict': 'supported',
        'attributed_to': [], 'claim_status': 'fact', 'source_status': 'fact',
        'evidence': [deepcopy(assertion)],
        'reason': 'This clause reports the declared source priority, not a dataset fact.'}]}]}


def audit(assertion):
    return {'findings': [], 'summary': 'No source defects in this synthetic metadata clause.',
            'source_review': review(assertion)}


def report(assertion):
    return '# Report\n\n## Evidence assertions\n```json\n' + json.dumps({
        'claims': [], 'source_review': review(assertion, 'final_full')}) + '\n```\n'


def test_renderer16_preserves_every_prior_assembly_and_binds_its_new_surfaces(monkeypatch):
    assert {v: api.assembly_digest(v)['sha256'] for v in LEGACY} == LEGACY
    current = api.assembly_digest(16)
    assert current['sha256'] not in LEGACY.values()
    monkeypatch.setattr(api, 'SOURCE_METADATA_HEADER_V16', api.SOURCE_METADATA_HEADER_V16 + 'Changed.\n')
    assert api.assembly_digest(16) != current
    assert {v: api.assembly_digest(v)['sha256'] for v in LEGACY} == LEGACY
    current = api.assembly_digest(16)
    monkeypatch.setattr(api, 'SOURCE_METADATA_CONTRACT_V16', api.SOURCE_METADATA_CONTRACT_V16 + 'Changed.\n')
    assert api.assembly_digest(16) != current
    assert {v: api.assembly_digest(v)['sha256'] for v in LEGACY} == LEGACY


@pytest.mark.parametrize('runtime', ['Claude API (direct)', 'Claude Code'])
def test_both_arms_receive_exact_projection_and_replay_version16(tmp_path, runtime):
    spec, assertion = fixture(tmp_path, runtime)
    text = spec.instruction
    assert '## Evidence protocol v5' in text
    assert api.SOURCE_METADATA_CONTRACT_V16 in text
    assert api.source_metadata_block(spec) in text
    assert assertion['sha256'] in text and '"effective_priority": 2' in text
    assert 'PRIVATE_CURATOR_TEXT_MUST_NOT_BE_EVIDENCE' not in text
    replay = api.RunSpec.from_render_spec(spec.render_spec(), project=spec.project,
                                        method=spec.method, label=spec.label)
    assert replay.instruction == text
    assert replace(spec, render_version=api.AUTO).render_version == (7 if spec.is_agentic else 8)
    if spec.is_agentic:
        command = api.native_evidence_instructions(spec)
        assert '--protocol-version 5' in command
        assert '--source-manifest ' + str(spec.manifest) in command
        assert '--project EXAMPLE' in command
    else:
        payload = api.build_phase(spec, 'audit', carry={'Completed full record': RAW})
        blocks = payload.messages[0]['content']
        assert api.SOURCE_METADATA_CONTRACT_V16 in blocks[-1]['text']
        assert any(api.source_metadata_block(spec) in block['text'] for block in blocks)


def test_explicit_no_manifest_keeps_neutral_v5_document_review_available(tmp_path):
    spec = replace(specification(tmp_path, 'Claude Code'), render_version=16)
    assert api.source_metadata_block(spec).endswith('\n\nnull')
    assert api.source_metadata_authority(spec) == {'source_manifest_raw': None, 'project': None}
    assert '--source-manifest' not in api.native_evidence_instructions(spec)


@pytest.mark.parametrize('runtime', ['Claude API (direct)', 'Claude Code'])
def test_explicitly_unused_manifest_is_not_a_metadata_authority(tmp_path, runtime, monkeypatch):
    selected, _ = fixture(tmp_path, runtime)
    spec = replace(selected, manifest_line='# Source manifest: not used')
    assert spec.manifest is not None and spec.manifest_used is False
    reader = Path.read_bytes
    def read(path):
        if path == spec.manifest:
            pytest.fail('An unused manifest became an evidence source')
        return reader(path)
    monkeypatch.setattr(Path, 'read_bytes', read)
    assert api.source_metadata_block(spec).endswith('\n\nnull')
    assert api.source_metadata_authority(spec) == {'source_manifest_raw': None, 'project': None}
    assert api.source_metadata_block(spec) in spec.instruction
    if spec.is_agentic:
        assert '--source-manifest' not in api.native_evidence_instructions(spec)


@pytest.mark.parametrize('selection', ['absent', 'unused'])
def test_document_only_audit_and_report_pass_without_manifest_authority(tmp_path, selection):
    spec, _ = fixture(tmp_path)
    spec = (replace(spec, manifest=None) if selection == 'absent' else
            replace(spec, manifest_line='# Source manifest: not used'))
    raw = 'description: A sample dataset is planned.\n'
    chunks, _ = evidence.source_chunks(spec.bundle, spec.chunk_manifest)
    original_review = review_for(raw, chunks=chunks)
    final_review = review_for(raw, artifact='final_full', chunks=chunks)
    for reviewed in (original_review, final_review):
        reviewed['values'][0]['claims'][0].update(claim_status='planned', source_status='planned')
    for path in (spec.full_path, spec.core_path):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(raw)
    spec.report_path.write_text('# Report\n\n## Evidence assertions\n```json\n' +
                               json.dumps({'claims': [], 'source_review': final_review}) + '\n```\n')
    carry = {'Original full record': raw, 'Original core record': raw,
             'Audit findings': json.dumps({'findings': [], 'summary': 'No findings.',
                                          'source_review': original_review})}
    out = api.evidence_checks_block(spec, carry, report=True, reconciled=True)
    assert out['checked'] is True and out['findings'] == []
    assert 'source_manifest' not in out['artifact_sha256']


@pytest.mark.parametrize('phase', ['audit', 'report', 'report_regate', 'report_after_repair'])
@pytest.mark.parametrize('mutation', [None, 'changed_bytes', 'wrong_value', 'wrong_project', 'omitted_manifest'])
def test_actual_api_admission_checks_manifest_authority_before_usage_acceptance(
        tmp_path, monkeypatch, phase, mutation):
    spec, assertion = fixture(tmp_path)
    if mutation == 'changed_bytes':
        spec.manifest.write_bytes(spec.manifest.read_bytes() + b'\n# new bytes\n')
    elif mutation == 'wrong_value':
        assertion['value'] = 3
    elif mutation == 'wrong_project':
        spec.project = 'UNDECLARED'
    elif mutation == 'omitted_manifest':
        spec = replace(spec, manifest=None)
    persisted, rejected = [], []
    monkeypatch.setattr(api, '_persist_usage', lambda *args: persisted.append(args))
    def reject(s, p, text, usage, out):
        rejected.append(out)
        raise RuntimeError('Synthetic observed rejection')
    monkeypatch.setattr(api, '_reject_source_response', reject)
    text = json.dumps(audit(assertion)) if phase == 'audit' else report(assertion)
    needed = {key: RAW for key in ('Completed full record', 'Original full record',
               'Original core record', 'Reconciled full record', 'Completed core record')}
    usage = {'source_review_admission': {'state': 'pending'}}
    if mutation is None:
        api._admit_source_response(spec, phase, text, 'end_turn', usage, needed)
        assert usage['source_review_admission']['state'] == 'accepted'
        assert len(persisted) == 1 and rejected == []
    else:
        with pytest.raises(RuntimeError, match='Synthetic observed rejection'):
            api._admit_source_response(spec, phase, text, 'end_turn', usage, needed)
        assert usage['source_review_admission']['state'] == 'pending'
        assert not persisted and rejected[0]['findings']


@pytest.mark.parametrize('with_report', [False, True])
@pytest.mark.parametrize('mutation', [None, 'stale', 'missing'])
def test_real_api_reconciliation_and_report_recheck_the_same_metadata(tmp_path, with_report, mutation):
    spec, assertion = fixture(tmp_path)
    for path in (spec.full_path, spec.core_path):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(RAW)
    spec.report_path.write_text(report(assertion))
    carry = {'Audit findings': json.dumps(audit(assertion)),
             'Original full record': RAW, 'Original core record': RAW}
    if mutation == 'stale':
        spec.manifest.write_bytes(spec.manifest.read_bytes() + b'\n# changed\n')
    elif mutation == 'missing':
        spec.manifest.unlink()
    result = api.evidence_checks_block(spec, carry, reconciled=True, report=with_report)
    if mutation is None:
        assert result['checked'] is True and result['findings'] == []
        assert result['artifact_sha256']['source_manifest'] == assertion['sha256']
        if with_report:
            assert result['source_review_final']['claims_checked'] == 1
    else:
        assert result['findings']


def test_historical_protocol4_file_is_unchanged():
    path = Path(__file__).resolve().parents[1] / 'src/download/prompts/evidence_protocol_v4.md'
    assert hashlib.sha256(path.read_bytes()).hexdigest() == 'b4f767ec3ada61c97711ff4db4d201f57b3854bd385c116c29bb9f75c4c3b3e2'
