"""Real staged preparers and descendant pins, using synthetic offline ancestry.

The imported ancestry fixture stubs historical transcript/accounting ancestry,
independent acceptance, sequence validation/sealing and uncommitted-code
attestation only. These tests exercise the real scientific renderers, preparers,
registration path closure, assembly, typed tool history and finalization pins.
They neither establish scientific acceptance nor claim or spend any budget.
"""
from copy import deepcopy
import json
from pathlib import Path
import shlex
import subprocess
import sys
from types import SimpleNamespace

import pytest

BASE = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(BASE), str(BASE / 'native_controls')]
from audit_controls import native, output_parts as parts, prepare, registration
from audit_controls.test_context_preparation import ancestry, decoded, save
from audit_controls.test_staged_native import Session
from finalization_controls import prepare as final_prepare, registration as final_registration
import native_context as frames


@pytest.fixture(autouse=True)
def actual_renderer_history_root(monkeypatch):
    # A nested development worktree can be misidentified by checkout_at's
    # containing-checkout search. Resolve the definition's actual git checkout
    # in this test only; preserve all production history/rendering checks.
    from data_sheets_schema import agent_pin
    from data_sheets_schema.resources import git_env

    def actual_root(path):
        return Path(subprocess.check_output(
            ['git', '-C', str(Path(path).resolve().parent), 'rev-parse', '--show-toplevel'],
            text=True, env=git_env()).strip())

    monkeypatch.setattr(agent_pin, '_history_root', actual_root)


@pytest.mark.parametrize('recovery', [False, True])
def test_real_staged_preparer_registers_exact_paths_pins_and_recoverable_instructions(ancestry, tmp_path, recovery):
    path = prepare.prepare(**ancestry[0], destination=tmp_path / 'staged',
        staged_audit_output=True, context_recovery=recovery)
    manifest = registration.validate_registration(path)
    job, block = manifest['job'], manifest['audit_output']
    directory = Path(job['output_dir']) / 'audit-parts'
    assert block == {
        'protocol': 'raw_utf8_parts_v1', 'max_parts': 64, 'max_part_bytes': 32768,
        'parts': [str(directory / f'{index:06d}.txt') for index in range(1, 65)],
        'assemble_argv': [sys.executable, '-m', 'audit_controls.output_parts',
                          '--registration', str(path)],
    }
    assert job['audit_path'] == str(Path(job['output_dir']) / 'audit.json')
    implementation = str(Path(parts.__file__).resolve())
    assert manifest['pinned_files'][implementation] == registration.sha(implementation)
    assert set(map(str, registration.required_paths(manifest))) <= set(manifest['pinned_files'])
    assert not set(block['parts']) & set(manifest['pinned_files'])
    assert not set(block['parts']) & set(job['readable_inputs'])
    assert implementation not in job['readable_inputs']
    instruction = Path(job['instruction']).read_text()
    assert instruction == prepare.render_instruction(manifest)
    current = instruction.split('## Current Phase 3 execution instructions\n\n', 1)[1]
    assert parts.instruction(manifest) in current
    assert shlex.join(block['assemble_argv']) in current
    assert shlex.join(job['validator_argv']) in current
    assert current.index(shlex.join(block['assemble_argv'])) < current.index(shlex.join(job['validator_argv']))
    assert 'Write only the complete audit JSON' not in current
    system = Path(job['system_prompt']).read_text()
    assert system == prepare.render_system(manifest)
    assert parts.instruction(manifest) in system
    expected_reads = set(manifest['inputs'].values()) | {job['instruction'], job['system_prompt']}
    if recovery:
        context = manifest['context_recovery']
        expected_reads.update(frames.bounded_paths(context))
        assert decoded(context['documents']['instruction']['frames']['path']) == instruction
        for name in frames.bounded_paths(context):
            assert manifest['pinned_files'][name] == registration.sha(name)
        persistent = system.split('Persistent registered context recovery\n', 1)[1]
        assert shlex.join(block['assemble_argv']) in persistent
        assert shlex.join(job['validator_argv']) in persistent
        assert str(directory) in persistent
        assert 'Write only the new audit at ' not in persistent
    else:
        assert 'context_recovery' not in manifest
    assert set(job['readable_inputs']) == expected_reads
    assert not Path(job['attempt_dir']).exists()
    assert not Path(manifest['budget']['ledger_path']).exists()
    assert ancestry[2] == {name: Path(name).read_bytes() for name in ancestry[2]}


@pytest.mark.parametrize('explicit_false', [False, True], ids=['omitted', 'explicit-false'])
def test_legacy_preparation_omits_staging_and_preserves_default_system(ancestry, tmp_path, explicit_false):
    options = {'staged_audit_output': False} if explicit_false else {}
    path = prepare.prepare(**ancestry[0], destination=tmp_path / 'legacy', **options)
    manifest = registration.validate_registration(path)
    assert 'audit_output' not in manifest
    assert str(Path(parts.__file__).resolve()) not in manifest['pinned_files']
    assert Path(manifest['job']['system_prompt']).read_bytes() == prepare.SYSTEM.encode()
    instruction = Path(manifest['job']['instruction']).read_text()
    current = instruction.split('## Current Phase 3 execution instructions\n\n', 1)[1]
    assert 'Write only the complete audit JSON' in current
    assert 'audit_controls.output_parts' not in current
    assert not Path(manifest['job']['attempt_dir']).exists()
    assert ancestry[2] == {name: Path(name).read_bytes() for name in ancestry[2]}


@pytest.mark.parametrize('value', ['true', 1, None])
def test_staged_flag_requires_boolean_before_creating_condition(tmp_path, value):
    destination = tmp_path / 'uncreated'
    with pytest.raises(registration.BudgetStop, match='explicit boolean'):
        prepare.prepare(parent_registration=None, parent_overlay=None, parent_job_id=None,
            reconciliation_receipt=None, reconciled_checkpoint=None, destination=destination,
            job_id='unused', repository=tmp_path, staged_audit_output=value)
    assert not destination.exists()


class RegisteredSession(Session):
    """Use the preparer's registered metadata in the shared synthetic transport."""
    def emit(self, event):
        event = deepcopy(event)
        manifest = self.c.m
        if event.get('type') == 'system' and event.get('subtype') == 'init':
            event.update(model=manifest['model']['model'],
                         claude_code_version=manifest['native_runtime']['version'].split()[0])
        elif event.get('type') == 'result':
            event['modelUsage'] = {manifest['model']['model']: {
                'contextWindow': manifest['native_runtime']['context_window'],
                'maxOutputTokens': manifest['native_runtime']['max_output_tokens']}}
        super().emit(event)


def staged_accepted_fixture(ancestry, destination):
    path = prepare.prepare(**ancestry[0], destination=destination,
                           staged_audit_output=True, context_recovery=True)
    manifest = registration.read_json(path)
    attempt = Path(manifest['job']['attempt_dir'])
    (Path(manifest['job']['output_dir']) / 'audit-parts').mkdir(parents=True)
    # The renderer ancestry fixture's source uses this exact synthetic quote.
    # Retain the synthetic audit's original-artifact evidence unchanged while
    # binding its source quotations to the supplied fixture bundle/chunks.
    text = Path(ancestry[1]['job']['audit_path']).read_text().replace(
        'The service is planned.', 'A sample dataset is planned.')
    case = SimpleNamespace(m=manifest, reg=path, identity=registration.sha(path),
        policy=native.build_policy(manifest, path), attempt=attempt,
        target=Path(manifest['job']['audit_path']), text=text)
    session = RegisteredSession(case)
    session.prepare_parts()
    session.assemble()
    session.validate()  # Actual pure scientific checker; typed successful result.
    evidence = session.finish()  # Actual complete callback/transcript replay.
    assert evidence['phase3'] == session.history.finish()
    assert evidence['control']['checked'] and evidence['control']['problems'] == []
    assert len(evidence['phase3']['audit_parts']) == 2
    result_path = save(attempt / 'result.json', {
        'status': 'completed_pending_independent_review', 'scope': 'phase3_audit_only',
        'job_id': manifest['job']['id'], 'registration_sha256': case.identity,
        'audit_path': manifest['job']['audit_path'], 'audit_sha256': registration.sha(case.target),
        'validation': evidence['phase3']['validation'], 'evidence': evidence,
    })
    billing = save(manifest['budget']['ledger_path'], {
        'requests': [{'id': 'fixture-settled', 'status': 'settled', 'cost_usd': '1.25'}]})
    acceptance = save(destination / 'synthetic_acceptance.json', {
        'verdict': 'accept', 'registration_sha256': case.identity,
        'result_sha256': registration.sha(result_path), 'ledger_sha256': registration.sha(billing)})
    return case, acceptance, evidence


def test_finalization_pins_staged_provenance_without_active_audit_mode(ancestry, tmp_path):
    case, acceptance, evidence = staged_accepted_fixture(ancestry, tmp_path / 'accepted-staged')
    preserved = {path: path.read_bytes() for path in tmp_path.rglob('*') if path.is_file()}
    path = final_prepare.prepare(accepted_audit_registration=case.reg, acceptance=acceptance,
        destination=tmp_path / 'finalization', job_id='synthetic_final',
        repository=ancestry[0]['repository'], context_recovery=True)
    manifest = final_registration.validate_registration(path)
    provenance = {case.attempt / 'assembly.json', case.attempt / 'assembly_ready.json',
                  *(Path(entry['part']['path']) for entry in evidence['phase3']['audit_parts'])}
    assert 'audit_output' not in manifest
    assert manifest['inputs']['audit'] == str(case.target)
    assert manifest['pinned_files'][str(case.target)] == registration.sha(case.target)
    for source in provenance:
        assert manifest['pinned_files'][str(source)] == registration.sha(source)
        assert str(source) not in manifest['job']['readable_inputs']
        assert str(source) not in manifest['inputs'].values()
    assert set(map(str, final_registration.required_paths(manifest))) <= set(manifest['pinned_files'])
    assert manifest['pinned_files'][str(Path(parts.__file__).resolve())] == registration.sha(parts.__file__)
    expected_reads = set(manifest['inputs'].values()) | {
        manifest['job']['instruction'], manifest['job']['system_prompt'],
        *frames.bounded_paths(manifest['context_recovery'])}
    assert set(manifest['job']['readable_inputs']) == expected_reads
    assert set(manifest['context_recovery']['documents']) == {'instruction', *manifest['inputs']}
    assert decoded(manifest['context_recovery']['documents']['audit']['frames']['path']) == case.target.read_text()
    current = Path(manifest['job']['system_prompt']).read_text()
    assert 'Current stage: Phase 4 finalization only.' in current
    assert 'audit_controls.output_parts' not in current
    assert 'assemble_argv' not in manifest['job']
    assert not Path(manifest['job']['attempt_dir']).exists()
    assert not Path(manifest['budget']['ledger_path']).exists()
    assert all(source.read_bytes() == raw for source, raw in preserved.items())


@pytest.mark.parametrize('damage', ['part', 'receipt'])
def test_finalization_refuses_changed_staged_evidence_before_repinning(ancestry, tmp_path, damage):
    case, acceptance, _ = staged_accepted_fixture(ancestry, tmp_path / 'accepted-staged')
    target = (Path(case.m['audit_output']['parts'][0]) if damage == 'part'
              else case.attempt / 'assembly.json')
    target.write_bytes(target.read_bytes() + b' ')
    # Whitespace leaves the receipt's JSON value unchanged; its retained typed
    # result still binds the original receipt bytes and must prevent repinning.
    before = {path: path.read_bytes() for path in tmp_path.rglob('*') if path.is_file()}
    destination = tmp_path / 'rejected-finalization'
    with pytest.raises(registration.BudgetStop, match='audit parts|accepted result'):
        final_prepare.prepare(accepted_audit_registration=case.reg, acceptance=acceptance,
            destination=destination, job_id='synthetic_final', repository=ancestry[0]['repository'])
    assert not (destination / 'registration.json').exists()
    assert all(source.read_bytes() == raw for source, raw in before.items())
