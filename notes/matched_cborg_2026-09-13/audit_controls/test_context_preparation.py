"""Real offline preparers and renderers; synthetic ancestry, never acceptance.

These fixtures stub historical transcript/accounting ancestry and uncommitted
code attestation only. They retain actual preparers, scientific renderers,
required-path pins, registration recovery validation, readable rosters and
system rendering. No provider, sequence claim or real artifact is involved.
"""
from copy import deepcopy
import json
from pathlib import Path
import sys

import pytest

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))
from audit_controls import prepare as audit_prepare, registration as audit_registration
from audit_controls.test_contract import rendered_fixture
from finalization_controls import prepare as final_prepare, registration as final_registration
import native_context as frames
import native_context_control as recovery


def save(path, value):
    path = Path(path);path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + '\n')
    return path


@pytest.fixture
def ancestry(tmp_path, monkeypatch):
    repository = BASE.parent.parent
    monkeypatch.chdir(repository)
    example, spec = rendered_fixture(tmp_path)
    generation_path = Path(example['parent']['registration'])
    generation = audit_registration.read_json(generation_path)
    job = generation['generation']['jobs'][0]
    job['profile'] = 'neutral'
    job['input_identity'] = {
        role: {'path': str(path), 'sha256': audit_registration.sha(path)}
        for role, path in [('bundle', spec.bundle), ('chunks', spec.chunk_manifest),
                           ('source_manifest', example['inputs']['source_manifest'])]}
    original = Path(job['render_spec']['agentic_artifact_paths']['core']).parent / 'evidence'
    original.mkdir(parents=True)
    for role in ('original_full', 'original_core'):
        (original / (role + '.yaml')).write_bytes(Path(example['inputs'][role]).read_bytes())
    receipt = Path(job['render_spec']['agentic_artifact_paths']['receipt'])
    receipt.parent.mkdir(parents=True, exist_ok=True)
    receipt.write_bytes(Path(example['inputs']['receipt']).read_bytes())
    price = {'input': .000005, 'output': .000025}
    generation.update(pinned_files={}, claude_version='synthetic-native-version',
        model={'model': 'registered-synthetic-model', 'route_model': 'registered-synthetic-route'},
        provider_base_url='https://api.cborg.lbl.gov', provider_context_policy='headroom_bypass_v1',
        budget={'additional_usd': '400', 'per_attempt_usd': '5',
            'per_job_attempt_usd': {job['id']: '20'}, 'prices_per_token': price,
            'ledger_path': str(tmp_path / 'original-billing.json')})
    save(generation_path, generation)
    overlay = save(tmp_path / 'overlay.json', {'pinned_files': {},
        'claude_executable': str(Path(sys.executable).resolve()), 'claude_version': generation['claude_version'],
        'native_limits_observed_offline': {'context_window': 200000, 'max_output_tokens': 64000}})
    checkpoint = save(tmp_path / 'checkpoint.json', {'additional_cap_usd': '400', 'attempt_cap_usd': '5',
        'requests': [{'id': 'fixture-settled', 'status': 'settled', 'cost_usd': '1.25'}]})
    confirmation = save(tmp_path / 'confirmation.json', {'synthetic': 'no real charge confirmation'})
    state = save(tmp_path / 'audit_sequence.json', {'synthetic': 'read-only ancestral state'})
    parent_attempt = generation_path.parent / 'attempts' / job['id']
    for name in ('result.json', 'transcript.jsonl', 'control.jsonl'):
        save(parent_attempt / name, {'synthetic': 'ancestral evidence stub'})
    proof = {'synthetic': 'historical Phase1/2 checks outside this integration test'}
    monkeypatch.setattr(audit_prepare, 'inspect_parent', lambda manifest: deepcopy(proof))
    monkeypatch.setattr(audit_registration, 'inspect_parent', lambda manifest: deepcopy(proof))
    monkeypatch.setattr(audit_registration, 'verify', lambda *args: None)
    monkeypatch.setattr(audit_registration, 'validate_audit_reconciliation', lambda manifest: None)
    monkeypatch.setattr(audit_registration, 'validate_reconciliation', lambda manifest: audit_registration.read_json(checkpoint))
    monkeypatch.setattr(final_registration, 'verify', lambda *args: None)
    monkeypatch.setattr(final_registration.sequence, '_validate', lambda *args: None)
    monkeypatch.setattr(final_prepare, 'seal_document', lambda manifest: {'synthetic': 'no sequence handoff'})
    # Any unmocked model construction would fail this offline fixture.
    import anthropic
    monkeypatch.setattr(anthropic, 'Anthropic', lambda *args, **kwargs: pytest.fail('provider constructed offline'))
    args = dict(parent_registration=generation_path, parent_overlay=overlay,
        parent_job_id=job['id'], reconciliation_receipt=confirmation, reconciled_checkpoint=checkpoint,
        repository=repository, job_id='synthetic_audit')
    preserved = {str(p): p.read_bytes() for p in tmp_path.rglob('*') if p.is_file()}
    return args, example, preserved, state


def audit(ancestry, destination, enabled=False):
    args, _, _, _ = ancestry
    return audit_prepare.prepare(**args, destination=destination, context_recovery=enabled)


def accepted_audit(ancestry, destination):
    registration = audit(ancestry, destination)
    manifest = audit_registration.read_json(registration)
    example = ancestry[1]
    Path(manifest['job']['audit_path']).parent.mkdir(parents=True)
    Path(manifest['job']['audit_path']).write_bytes(Path(example['job']['audit_path']).read_bytes())
    billing = save(manifest['budget']['ledger_path'], {
        'requests': [{'id': 'fixture-settled', 'status': 'settled', 'cost_usd': '1.25'}]})
    result = save(Path(manifest['job']['attempt_dir']) / 'result.json', {
        'status': 'completed_pending_independent_review', 'registration_sha256': audit_registration.sha(registration)})
    acceptance = save(destination / 'synthetic_acceptance.json', {
        'verdict': 'accept', 'registration_sha256': audit_registration.sha(registration),
        'result_sha256': audit_registration.sha(result), 'ledger_sha256': audit_registration.sha(billing)})
    return registration, acceptance


def stage_prepare(stage, ancestry, root, enabled):
    if stage == 'audit':
        path = audit(ancestry, root, enabled)
        return path, audit_prepare, audit_registration
    accepted, acceptance = accepted_audit(ancestry, root.parent / ('accepted_' + root.name))
    path = final_prepare.prepare(accepted_audit_registration=accepted, acceptance=acceptance,
        destination=root, job_id='synthetic_final', repository=ancestry[0]['repository'], context_recovery=enabled)
    return path, final_prepare, final_registration


def decoded(path):
    return ''.join(json.loads(line)['text'] for line in Path(path).read_text().splitlines())


def test_actual_preparer_pins_transitive_runtime_closure_without_model_delivery(ancestry, tmp_path):
    # This fixture stubs historical acceptance, as documented above. Exercise
    # the real preparer and transitive pins; semantic admission is tested in
    # test_runtime_closure using real sequence/accounting validators.
    args, _, _, state = ancestry
    source = tmp_path / 'stopped-audit'
    source_reg = save(source / 'registration.json', {
        'budget': {'ledger_path': str(source / 'billing.json')},
        'job': {'id': 'stopped', 'attempt_dir': str(source / 'attempts/stopped')}})
    save(source / 'billing.json', {'synthetic': 'unchanged pending ledger'})
    save(source / 'attempts/stopped/result.json', {'synthetic': 'historical count-one result'})
    observation = save(tmp_path / 'boot.json', {'synthetic': 'raw OS observation'})
    launch = save(tmp_path / 'launch.json', {'synthetic': 'exact launch observation'})
    ref = lambda p: {'path': str(p), 'sha256': audit_registration.sha(p)}
    proof = save(tmp_path / 'closure.json', {'observation': ref(observation), 'launch_observation': ref(launch)})
    receipt = save(tmp_path / 'audit-accounting.json', {'runtime_closure': ref(proof)})
    before = {p: p.read_bytes() for p in (source_reg, observation, launch, proof, receipt, state)}
    path = audit_prepare.prepare(**args, destination=tmp_path / 'successor',
        continuation_checkpoint=args['reconciled_checkpoint'],
        continuation_source_registration=source_reg, continuation_reconciliation_receipt=receipt)
    manifest = audit_registration.read_json(path)
    for p in (proof, observation, launch):
        assert manifest['pinned_files'][str(p)] == audit_registration.sha(p)
        assert str(p) not in manifest['job']['readable_inputs']
        assert str(p) not in Path(manifest['job']['instruction']).read_text()
    assert all(p.read_bytes() == raw for p, raw in before.items())
    assert not Path(manifest['budget']['ledger_path']).exists()
    observation.write_text('{"synthetic": "changed after preparation"}')
    with pytest.raises(audit_registration.BudgetStop, match='runtime closure evidence changed'):
        audit_registration.required_paths(manifest)


@pytest.mark.parametrize('stage', ['audit', 'finalization'])
def test_actual_preparer_recovery_preserves_complete_instruction_and_input_roles(ancestry, tmp_path, stage):
    path, prepare, registration = stage_prepare(stage, ancestry, tmp_path / 'new_condition', True)
    manifest = registration.validate_registration(path)
    job, block = manifest['job'], manifest['context_recovery']
    expected = {'instruction': job['instruction'], **manifest['inputs']}
    assert set(block['documents']) == set(expected)
    assert 'system' not in block['documents']
    for role, original in expected.items():
        descriptor = block['documents'][role]
        assert descriptor['source'] == {'path': original, 'sha256': audit_registration.sha(original)}
        assert decoded(descriptor['frames']['path']).encode() == Path(original).read_bytes()
    assert set(job['readable_inputs']) == set(manifest['inputs'].values()) | {
        job['instruction'], job['system_prompt'], *frames.bounded_paths(block)}
    assert set(map(str, registration.required_paths(manifest))) <= set(manifest['pinned_files'])
    assert all(manifest['pinned_files'][p] == audit_registration.sha(p) for p in frames.bounded_paths(block))
    system = Path(job['system_prompt']).read_text()
    assert system == prepare.render_system(manifest) and system.startswith(prepare.SYSTEM)
    assert block['index']['path'] in system and block['index']['sha256'] in system
    assert ('Phase 3 audit only' if stage == 'audit' else 'Phase 4 finalization only') in system
    for role in (('audit_path',) if stage == 'audit' else ('full_path', 'core_path', 'report_path')):
        assert job[role] in system
    assert ('audit_controls.contract' if stage == 'audit' else 'finalization_controls.contract') in system
    without = deepcopy(manifest);without.pop('context_recovery')
    assert prepare.render_system(without) == prepare.SYSTEM
    assert prepare.render_instruction(manifest) == prepare.render_instruction(without)
    assert Path(job['instruction']).read_bytes() == prepare.render_instruction(without).encode()
    assert not Path(manifest['budget']['ledger_path']).exists()
    assert not Path(job['attempt_dir']).exists()
    assert ancestry[2] == {p: Path(p).read_bytes() for p in ancestry[2]}


@pytest.mark.parametrize('stage', ['audit', 'finalization'])
def test_default_preparer_system_and_scientific_instruction_remain_exact(ancestry, tmp_path, stage):
    path, prepare, registration = stage_prepare(stage, ancestry, tmp_path / 'default_condition', False)
    manifest = registration.validate_registration(path)
    assert 'context_recovery' not in manifest and not (path.parent / 'recovery').exists()
    assert Path(manifest['job']['system_prompt']).read_bytes() == prepare.SYSTEM.encode()
    # Exact merged defaults at 866c8589462c456d86abf60804260b79f5df400e;
    # this also catches an accidental edit to the shared SYSTEM constant.
    historical = {'audit': 'c7e9e0d18b0ee55a1b3cc276d77eb7605bcfbc2753bda28f24e268d82cfedc8b',
                  'finalization': '0e01aa12d7275210520c8a313bcd9a79e4bb553b19027e6565eeea6713983878'}
    assert audit_registration.sha(manifest['job']['system_prompt']) == historical[stage]
    assert Path(manifest['job']['instruction']).read_bytes() == prepare.render_instruction(manifest).encode()
    assert ancestry[2] == {p: Path(p).read_bytes() for p in ancestry[2]}


@pytest.mark.parametrize('stage', ['audit', 'finalization'])
@pytest.mark.parametrize('damage', ['repinned_replacement', 'missing_read', 'repinned_system'])
def test_full_registration_rejects_rebound_recovery_changes(ancestry, tmp_path, stage, damage):
    path, prepare, registration = stage_prepare(stage, ancestry, tmp_path / 'damaged_condition', True)
    manifest = registration.read_json(path);block = manifest['context_recovery']
    if damage == 'repinned_replacement':
        descriptor = block['documents']['bundle']['frames'];target = Path(descriptor['path'])
        text = 'Coherently pinned but incomplete substitute source'
        raw = frames._encoded(text);target.write_bytes(raw)
        block['documents']['bundle']['frames'] = frames._metadata(target, raw, text)
        index = Path(block['index']['path'])
        text = frames._json({'kind': frames.INDEX_KIND, 'documents': block['documents']})
        raw = frames._encoded(text);index.write_bytes(raw);block['index'] = frames._metadata(index, raw, text)
        for target in (target, index):manifest['pinned_files'][str(target)] = audit_registration.sha(target)
        Path(manifest['job']['system_prompt']).write_text(prepare.render_system(manifest))
        manifest['pinned_files'][manifest['job']['system_prompt']] = audit_registration.sha(manifest['job']['system_prompt'])
    elif damage == 'missing_read':
        manifest['job']['readable_inputs'].remove(block['documents']['bundle']['frames']['path'])
    else:
        system = Path(manifest['job']['system_prompt']);system.write_text(prepare.SYSTEM)
        manifest['pinned_files'][str(system)] = audit_registration.sha(system)
    save(path, manifest)
    with pytest.raises(audit_registration.BudgetStop, match='bounded native context|readable input roster|read scope|system prompt'):
        registration.validate_registration(path)
    assert ancestry[2] == {p: Path(p).read_bytes() for p in ancestry[2]}


@pytest.mark.parametrize('stage', ['audit', 'finalization'])
@pytest.mark.parametrize('value', ['true', 1, None])
def test_opt_in_requires_explicit_boolean_before_destination_creation(tmp_path, stage, value):
    target = tmp_path / 'never_created'
    with pytest.raises(audit_registration.BudgetStop, match='explicit boolean'):
        if stage == 'audit':
            audit_prepare.prepare(parent_registration=None, parent_overlay=None, parent_job_id=None,
                reconciliation_receipt=None, reconciled_checkpoint=None, destination=target,
                job_id='unused', repository=tmp_path, context_recovery=value)
        else:
            final_prepare.prepare(accepted_audit_registration=None, acceptance=None, destination=target,
                job_id='unused', repository=tmp_path, context_recovery=value)
    assert not target.exists()
