"""Batch evidence survives descendants; active audit modes do not spread.

All records and runtime histories are synthetic. Tests use the real public
entry points and closure helpers, never provider calls or historical evidence.
"""
from copy import deepcopy
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest

BASE = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(BASE), str(BASE/'native_controls')]
from audit_controls import registration, prepare
from audit_controls import batch_output
from audit_controls.test_context_preparation import ancestry, save
from audit_controls.test_batch_runtime import batch, assembled_batch, accepted_batch
from audit_controls.test_source_metadata_upgrade import metadata_ancestry
from audit_controls.test_staged_preparation import actual_renderer_history_root
from evaluation_controls import registration as evaluation_registration
from finalization_controls import registration as final_registration
from data_sheets_schema import api_runner, profiles
import run_api_canary
import run_native_canary
import continuation_sequence as sequence


@pytest.mark.parametrize('value', [None, False, True, 0, '', [], {},
    {'kind': 'fresh_context_integrated_v1'}])
def test_actual_generation_phase4_evaluation_reject_batch_key_presence(tmp_path, value):
    manifest = {'audit_batches': value}
    path = save(tmp_path/'registration.json', manifest)
    before = path.read_bytes()
    for verify in (run_api_canary.verify, evaluation_registration.verify_manifest):
        with pytest.raises(registration.BudgetStop, match='audit_batches is audit-only'):
            verify(manifest, path, 'unused')
    with pytest.raises(registration.BudgetStop, match='audit_batches is audit-only'):
        final_registration.validate_registration(path)
    assert list(tmp_path.iterdir()) == [path] and path.read_bytes() == before


@pytest.mark.parametrize('value', [None, False, {}, {'kind': 'fresh_context_integrated_v1'}])
def test_actual_native_generation_rejects_batch_key_before_runtime_or_ledger(tmp_path, monkeypatch, value):
    base = {'audit_batches': value}
    path = save(tmp_path/'registration.json', base)
    overlay = save(tmp_path/'overlay.json', {'registration': str(path),
        'registration_sha256': registration.sha(path), 'allowed_jobs': ['synthetic'], 'pinned_files': {}})
    review = save(tmp_path/'review.json', {'verdict': 'approve', 'ci_conclusion': 'success',
        'overlay_sha256': registration.sha(overlay), 'allowed_jobs': ['synthetic']})
    monkeypatch.setattr(run_native_canary, 'verify_history', lambda *a, **k: pytest.fail('history setup reached'))
    monkeypatch.setattr(run_native_canary, 'verified_executable', lambda *a, **k: pytest.fail('runtime setup reached'))
    monkeypatch.setattr(run_native_canary, 'open_ledger', lambda *a, **k: pytest.fail('ledger opened'))
    monkeypatch.setattr(sys, 'argv', ['native', '--overlay', str(overlay), '--review', str(review), '--job', 'synthetic'])
    before = {p: p.read_bytes() for p in tmp_path.iterdir()}
    with pytest.raises(registration.BudgetStop, match='audit_batches is audit-only'):
        run_native_canary.main()
    assert before == {p: p.read_bytes() for p in tmp_path.iterdir()}


@pytest.mark.parametrize('version', [20, '20', 21, '21'])
def test_per_job_batch_renderer_cannot_bypass_generation_selector(tmp_path, version):
    manifest = {'generation': {'jobs': [{'id': 'synthetic', 'render_spec': {'render_version': version}}]}}
    path = save(tmp_path/'registration.json', manifest)
    with pytest.raises(registration.BudgetStop, match='audit-continuation-only'):
        run_api_canary.verify(manifest, path, registration.sha(path))


@pytest.mark.parametrize('private', [False, True])
@pytest.mark.parametrize('version', [20, 21])
def test_library_generation_rejects_batch_renderer_before_output_or_provider(tmp_path, monkeypatch, private, version):
    spec = SimpleNamespace(render_version=version, _replay_only=False)
    monkeypatch.setattr(api_runner, '_exclusive_run', lambda *a, **k: pytest.fail('generation output lock reached'))
    with pytest.raises(ValueError, match='separately registered audit continuation'):
        if private:
            api_runner._execute(spec, resume=False, client=object())
        else:
            api_runner.execute(spec, resume=False, client=object())
    assert not list(tmp_path.iterdir())


def scientific_pair(tmp_path):
    roots = [tmp_path/'accepted', tmp_path/'descendant']
    shared = ('api_runner.py', 'evidence_assertions.py', 'source_review.py', 'report_claims.py',
        'derive_core.py', 'd4d_pair_consistency.py', 'profiles.py', 'schema_digest.py',
        'schema_semantics.py', 'anonymous_removals.py', 'source_metadata.py',
        'audit_batches.py', 'audit_batch_context.py', 'audit_grammar.py')
    for root in roots:
        (root/'src/data_sheets_schema').mkdir(parents=True)
        (root/'src/download/prompts').mkdir(parents=True)
        for name in shared:
            (root/'src/data_sheets_schema'/name).write_bytes(b'identical synthetic implementation\n')
        (root/'src/download/prompts/evidence_protocol_v7.md').write_text('Synthetic protocol seven.\n')
    manifest = {'kind': final_registration.KIND, 'schema_version': 1, 'protocol_version': 7,
        'render_version': 20, registration.TRANSITION: {'kind': registration.BATCH_TRANSITION_KIND},
        'repository': str(roots[1])}
    accepted = {'repository': str(roots[0]),
        'inputs': {'protocol': str(roots[0]/'src/download/prompts/evidence_protocol_v7.md')}}
    return manifest, accepted


def test_phase4_preserves_batch_instrument_without_reselecting_active_mode(tmp_path):
    manifest, accepted = scientific_pair(tmp_path)
    final_registration.validate_scientific_identity(manifest, accepted)
    assert 'audit_batches' not in manifest
    assert registration.scientific_contract(manifest)
    assert registration.schema_semantic_context(manifest)


@pytest.mark.parametrize('name', ['audit_batches.py', 'audit_batch_context.py', 'audit_grammar.py'])
def test_phase4_cannot_repin_a_changed_batch_instrument(tmp_path, name):
    manifest, accepted = scientific_pair(tmp_path)
    final_registration.validate_scientific_identity(manifest, accepted)
    changed = Path(manifest['repository'])/'src/data_sheets_schema'/name
    changed.write_text('Changed scientific interpretation or assembly.\n')
    manifest['pinned_files'] = {str(changed): registration.sha(changed)}
    with pytest.raises(registration.BudgetStop, match='batch|'+name):
        final_registration.validate_scientific_identity(manifest, accepted)


def test_batch_authority_pins_external_profile_outside_repository_discovery(metadata_ancestry, tmp_path, monkeypatch):
    path = prepare.prepare(**metadata_ancestry[0], destination=tmp_path/'registration',
        audit_batches={'kind': 'fresh_context_integrated_v1', 'worker_total_cap_usd': '12'})
    manifest = registration.read_json(path)
    external = tmp_path/'external-vocabulary.yaml'
    external.write_text('vocabularies:\n  SYN:\n    SYN:1: Synthetic term.\n')
    profile = profiles.Profile(manifest['profile'], vocabulary_pin=external)
    monkeypatch.setattr(profiles, 'profile_named', lambda name: profile)
    assert external not in registration.implementation_paths(manifest)
    assert external in registration.batch_authority_paths(manifest)
    assert external in registration.required_paths(manifest)
    external.unlink()
    with pytest.raises((OSError, ValueError, registration.BudgetStop)):
        registration.required_paths(manifest)


def downstream(case, tmp_path):
    """Minimal descendant inputs for the real inherited closure collector."""
    b = case.batch
    result = deepcopy(case.result)
    result.update(status='completed_pending_independent_review', scope='phase3_audit_only',
        unresolved_requests=[], audit_path=b.m['job']['audit_path'])
    result_path = save(b.attempt/'result.json', result)
    schema = tmp_path/'schema.yaml'
    schema.write_text('id: https://example.invalid/schema\nname: example\nclasses:\n  Dataset: {}\n  CoreDataset: {}\n')
    instruction = tmp_path/'phase4_instruction.md'; instruction.write_text('Synthetic descendant.\n')
    system = tmp_path/'phase4_system.md'; system.write_text('Synthetic descendant system.\n')
    ref = lambda p: {'path': str(p), 'sha256': registration.sha(p)}
    manifest = {'kind': final_registration.KIND, 'schema_version': 1,
        'protocol_version': 7, 'render_version': 20,
        registration.TRANSITION: {'kind': registration.BATCH_TRANSITION_KIND},
        'repository': b.m['repository'], 'provider_base_url': 'https://api.cborg.lbl.gov',
        'accepted_audit': {'registration': ref(b.reg)},
        'budget_sequence': {'audit_origin': {'result': ref(result_path)}},
        'inputs': {**b.m['inputs'], 'audit': b.m['job']['audit_path'],
            'full_schema': str(schema), 'core_schema': str(schema)},
        'job': {'instruction': str(instruction), 'system_prompt': str(system)},
        'native_runtime': {'executable': str(Path(sys.executable).resolve())},
        'python': sys.executable, 'python_identity': {'resolved_path': str(Path(sys.executable).resolve())}}
    return manifest, result_path, result


def test_real_phase4_collector_inherits_every_assembled_child_artifact(accepted_batch, tmp_path):
    case = accepted_batch; b = case.batch
    manifest, _, result = downstream(case, tmp_path)
    closure = batch_output.closure_paths(b.m, b.reg, result)
    paths = final_registration.required_paths(manifest)
    assert closure <= paths
    assert set(map(Path, b.m['pinned_files'])) <= paths
    assert Path(b.m['audit_batches']['integration_index']) in paths
    assert Path(result['evidence']['assembly']['lineage']['path']) in paths
    for child in b.m['audit_batches']['children']:
        assert Path(child['proposal_path']) in paths
        assert Path(child['attempt_dir'])/'closed.json' in paths
        assert Path(child['rounds'][0]['parts'][0]) in paths
    assert set(Path(case.session.c.attempt).joinpath('rows').iterdir()) <= paths
    # The collector adds evidence to pins, not to the model's scientific inputs.
    assert not set(map(str, closure - {Path(b.m['job']['audit_path'])})) & set(manifest['inputs'].values())


def test_real_phase4_collection_rejects_changed_batch_evidence(accepted_batch, tmp_path):
    case = accepted_batch; b = case.batch
    manifest, result_path, result = downstream(case, tmp_path)
    expected = final_registration.required_paths(manifest)
    # One expensive real child closure is shared across independent mutations.
    # Restore bytes in place (including hardlink witnesses), never copy/re-pin
    # a reconstructed accepted history. Revalidate the intact closure at end.
    for damage in ('proposal', 'row_view', 'index', 'lineage', 'result', 'repinned_result'):
        changed_manifest = deepcopy(manifest)
        target = Path({'proposal': b.m['audit_batches']['children'][0]['proposal_path'],
            'row_view': next((case.session.c.attempt/'rows').iterdir()),
            'index': b.m['audit_batches']['integration_index'],
            'lineage': result['evidence']['assembly']['lineage']['path'],
            'result': result_path, 'repinned_result': result_path}[damage])
        before = target.read_bytes()
        try:
            if damage in ('result', 'repinned_result'):
                changed_result = deepcopy(result)
                changed_result['evidence']['batch_children'].pop()
                save(target, changed_result)
                if damage == 'repinned_result':
                    changed_manifest['budget_sequence']['audit_origin']['result']['sha256'] = registration.sha(target)
            else:
                target.write_text('changed after acceptance\n')
            with pytest.raises((registration.BudgetStop, ValueError)):
                final_registration.required_paths(changed_manifest)
        finally:
            target.write_bytes(before)
    assert final_registration.required_paths(manifest) == expected


def shared_ancestry(case, tmp_path):
    """Real common audit-origin proof used by Phase4 and all evaluation stages."""
    b = case.batch
    manifest, result_path, result = downstream(case, tmp_path)
    closure = batch_output.closure_paths(b.m, b.reg, result)
    artifacts = {b.m['job']['audit_path']: result['audit_sha256']}
    ref = lambda p: {'path': str(p), 'sha256': registration.sha(p)}
    state = save(tmp_path/'audit_state.json', {'synthetic': 'closed prior state'})
    acceptance = save(tmp_path/'acceptance.json', {'verdict': 'accept',
        'registration_sha256': b.identity, 'result_sha256': registration.sha(result_path),
        'ledger_sha256': registration.sha(b.ledger.path), 'artifacts': artifacts})
    predecessor = {'stage': 'audit', 'registration': ref(b.reg), 'ledger': ref(b.ledger.path),
        'result': ref(result_path), 'state': ref(state), 'acceptance': ref(acceptance)}
    pins = closure | {Path(batch_output.__file__).resolve(), b.reg, b.ledger.path,
        result_path, state, acceptance}
    manifest['pinned_files'] = {str(p): registration.sha(p) for p in pins}
    manifest['budget_sequence'] = {'origin': {'registration': ref(b.m['parent']['registration'])},
        'audit_origin': predecessor}
    return manifest, predecessor, closure


def test_common_descendant_accounting_revalidates_exact_full_batch_closure(accepted_batch, tmp_path):
    manifest, predecessor, closure = shared_ancestry(accepted_batch, tmp_path)
    before = {p: p.read_bytes() for p in closure}
    ledger, total, state = sequence._closure(manifest, predecessor, 'synthetic-lineage')
    assert str(total) == '3'
    assert len(ledger['requests']) == 3 and state == {'synthetic': 'closed prior state'}
    assert before == {p: p.read_bytes() for p in before}
    case = accepted_batch; b = case.batch
    missing = {'implementation': Path(batch_output.__file__).resolve(),
        'row_view': next((case.session.c.attempt/'rows').iterdir()),
        'worker_part': Path(b.m['audit_batches']['children'][0]['rounds'][0]['parts'][0]),
        'lineage': Path(case.result['evidence']['assembly']['lineage']['path'])}
    for target in missing.values():
        descendant = deepcopy(manifest)
        del descendant['pinned_files'][str(target)]
        with pytest.raises(registration.BudgetStop, match='batched audit closure'):
            sequence._closure(descendant, predecessor, 'synthetic-lineage')
