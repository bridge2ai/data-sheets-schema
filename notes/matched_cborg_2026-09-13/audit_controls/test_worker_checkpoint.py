"""Synthetic metadata/freeze tests; scanner and typed worker closure have own suites."""
from copy import deepcopy
from decimal import Decimal
import hashlib
import json
import os
from pathlib import Path
import sys
from types import SimpleNamespace
import pytest

BASE = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(BASE), str(BASE / 'native_controls')]
from budgeted_cborg import BudgetStop, attempt_identity
from audit_controls import worker_checkpoint as checkpoint


def save(path, value):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + '\n')
    return path


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def ref(path):
    return {'path': str(path), 'sha256': sha(path)}


def freeze(root):
    files, dirs, links = {}, [], {}
    for folder, names, leaves in os.walk(root):
        dirs.extend(str((Path(folder) / n).relative_to(root)) for n in names)
        for name in leaves:
            p = Path(folder) / name; st = p.stat(); rel = str(p.relative_to(root))
            files[rel] = {'sha256': sha(p), 'bytes': st.st_size, 'links': st.st_nlink}
            links.setdefault((st.st_dev, st.st_ino), []).append(rel)
    return {'kind': checkpoint.INVENTORY_KIND, 'root': str(root), 'files': files,
            'directories': sorted(dirs),
            'hardlink_groups': sorted(sorted(g) for g in links.values() if len(g) > 1)}


def make_fixture(tmp_path, monkeypatch):
    # Only the separately tested zero-check scanner is stubbed. This metadata
    # fixture does not claim scientific acceptance or real typed worker closure.
    from audit_controls import checkpoint_eligibility
    monkeypatch.setattr(checkpoint_eligibility, 'verify', lambda *args: {'zero_terminal_source_check': True})
    root = tmp_path / 'source'; root.mkdir()
    generation = save(tmp_path / 'generation.json', {'budget': {'ledger_path': str(tmp_path/'origin/billing.json')}})
    scientific=[]
    for name in checkpoint.SCIENTIFIC_MODULES:
        target=tmp_path/'src/data_sheets_schema'/name
        target.parent.mkdir(parents=True,exist_ok=True);target.write_text('# synthetic scientific module\n');scientific.append(target)
    for name in ('pyproject.toml','poetry.lock'):
        target=tmp_path/name;target.write_text('# synthetic dependency identity\n');scientific.append(target)
    claim_code=tmp_path/checkpoint.CONTROL_RELATIVE/'sequence_claim.py'
    claim_code.parent.mkdir(parents=True,exist_ok=True);claim_code.write_text('# synthetic claim code\n')
    original = tmp_path / 'input.txt'; original.write_text('wholly synthetic input\n')
    state = tmp_path / 'origin/audit_sequence.json'
    path = root / 'registration.json'; ledger_path = root / 'billing.json'
    job_id = 'synthetic_source'; attempt = root / 'attempts' / job_id
    workers = []
    for index in (1, 2):
        name = f'worker_{index:04d}'; child = attempt / 'children' / name
        proposal = save(child / 'output/proposal.json', {'synthetic': 'not scientific acceptance'})
        workers.append({'id': name, 'kind': 'worker', 'attempt_dir': str(child), 'proposal_path': str(proposal)})
    integration = attempt / 'children/integration'; integration.mkdir(parents=True)
    plan = save(root / 'batch-plan.json', {'workers': [{'id': w['id']} for w in workers]})
    source = {'schema_version': 1, 'kind': 'd4d_native_audit_continuation',
        'protocol_version': 7, 'render_version': 23,
        'scientific_contract_transition': {'kind': 'frozen_pair_child_navigation_v1'},
        'audit_batch_navigation': {'kind': 'explicit_child_reads_v1'},
        'repository': str(tmp_path), 'python': sys.executable,
        'parent': {'registration': str(generation)},
        'inputs': {'original_full': str(original)}, 'model': {'model': 'synthetic'},
        'native_runtime': {'version': 'synthetic'}, 'profile': 'neutral',
        'provider_base_url': 'https://synthetic.invalid', 'provider_context_policy': 'synthetic',
        'sequence_state': str(state), 'sequence_claim': {'protocol': 'durable_sequence_claim_v1'},
        'job': {'id': job_id, 'attempt_dir': str(attempt), 'deadline_seconds': 21600},
        'budget': {'additional_usd': '500', 'per_attempt_usd': '5',
            'per_job_attempt_usd': {job_id: '40'}, 'prices_per_token': {'input': '0.000005'},
            'ledger_path': str(ledger_path), 'continuation': {'sha256': 'a' * 64}},
        'audit_batches': {'kind': 'fresh_context_integrated_v1', 'plan_path': str(plan),
            'worker_total_cap_usd': '36', 'children': [*workers, {'id': 'integration', 'kind': 'integration',
                'attempt_dir': str(integration)}]},
        'pinned_files': {str(p): sha(p) for p in (original, generation, plan, claim_code, *scientific)}}
    ledger = {'additional_cap_usd': '500', 'attempt_cap_usd': '5', 'requests': [
        {'id': 'one', 'status': 'settled', 'cost_usd': '1.25'},
        {'id': 'two', 'status': 'settled', 'cost_usd': '2.50', 'provider_charge_confirmed': False,
         'provider_charge_usd': None, 'provider_usage_is_final': False}]}
    result = {'status': 'stopped', 'scope': 'phase3_audit_only', 'error_type': 'BudgetStop',
        'job_id': job_id, 'runtime': {'proxy_shutdown_complete': True, 'unfinished_handlers': 0}}
    proof = {}; current = {}; inventory_path = tmp_path / 'frozen.json'
    def refresh(*, current_owner=True):
        save(path, source); identity = sha(path); owner_id = attempt_identity(identity, job_id)
        ledger['manifest_sha256'] = identity
        ledger['attempt_caps_usd'] = {owner_id: '40'}
        ledger['stopped_attempts'] = {owner_id: {'paid_request': False, 'denied_reservation_usd': '3'}}
        for row in ledger['requests']:
            row['attempt'] = owner_id
            row.setdefault('attempt_cap_usd', '40'); row.setdefault('stage_cap_usd', '36')
        save(ledger_path, ledger)
        owner = {'schema_version': 1, 'registration_sha256': identity, 'ledger_path': str(ledger_path),
            'parent_checkpoint_sha256': source['budget']['continuation']['sha256'],
            'source_registration_sha256': sha(generation)}
        owner_path = save(root / 'sequence_claim/owner.json', owner)
        previous = save(root / 'sequence_claim/predecessor.json', {'synthetic': 'previous consumed owner'})
        claim_path = save(root / 'sequence_claim/manifest.json', {'schema_version': 1,
            'kind': 'observed_sequence_owner_transition', 'protocol': 'durable_sequence_claim_v1',
            'stage': 'audit', 'claiming_registration_path': str(path),
            'claiming_registration_sha256': identity, 'canonical_state_path': str(state),
            'owner_sha256': sha(owner_path), 'predecessor_absent': False, 'predecessor_sha256': sha(previous),
            'origin': {'registration_sha256':sha(generation),'ledger_path':str(tmp_path/'origin/billing.json')},
            'implementation_sha256':sha(claim_code)})
        ready = root / 'sequence_claim/ready.json'
        if not ready.exists(): os.link(claim_path, ready)
        if current_owner: save(state, owner)
        result['registration_sha256'] = identity
        result_path = save(attempt / 'result.json', result)
        refs = []
        for index, worker in enumerate(workers):
            closure = save(Path(worker['attempt_dir']) / 'closed.json', {
                'status': 'completed_proposal', 'registration_sha256': identity, 'job_id': job_id,
                'child_id': worker['id'], 'billing_attempt': owner_id,
                'runtime': {'exit_code': 0, 'proxy_initialized': True, 'proxy_shutdown_complete': True, 'unfinished_handlers': 0},
                'request_rows': [deepcopy(ledger['requests'][index])]})
            refs.append({'id': worker['id'], 'closure': ref(closure)})
        save(inventory_path, freeze(root))
        proof.clear(); proof.update({'kind': checkpoint.KIND, 'source_registration': ref(path),
            'source_ledger': ref(ledger_path), 'source_owner': ref(owner_path), 'source_claim': ref(claim_path),
            'source_result': ref(result_path), 'source_inventory': ref(inventory_path), 'workers': refs})
        current.clear(); current.update(deepcopy(source)); current[checkpoint.KEY] = deepcopy(proof)
        current['job']['id'] = 'synthetic_integration'
        current['budget']['ledger_path'] = str(tmp_path / 'successor/billing.json')
        current['budget']['per_job_attempt_usd'] = {'synthetic_integration': '20'}
        current['budget']['continuation'] = {'checkpoint': str(ledger_path), 'sha256': sha(ledger_path),
            'cost_usd': str(sum((Decimal(r['cost_usd']) for r in ledger['requests']), Decimal(0)))}
        current['pinned_files'] = {str(p): sha(p) for p in checkpoint.proof_paths(current)}
        return current
    refresh()
    return SimpleNamespace(source=source, manifest=current, proof=proof, ledger=ledger, result=result,
        root=root, source_registration=path, source_ledger=ledger_path, state=state, refresh=refresh,
        inventory=inventory_path, workers=workers)


@pytest.fixture
def example(tmp_path, monkeypatch):
    return make_fixture(tmp_path, monkeypatch)


def test_all_workers_resolve_to_original_provenance_without_writes(example):
    before = freeze(example.root)
    source = checkpoint.validate(example.manifest)
    assert source.sha256 == sha(example.source_registration)
    assert [w['id'] for w in source.workers] == ['worker_0001', 'worker_0002']
    assert source.proposal_refs['worker_0001']['path'] == example.workers[0]['proposal_path']
    assert source.closure_refs == {r['id']: r['closure'] for r in example.proof['workers']}
    assert freeze(example.root) == before
    assert not Path(example.manifest['budget']['ledger_path']).exists()


@pytest.mark.parametrize('value', [None, False, [], {}, 'collective_closed_workers_v1'])
def test_invalid_selection_never_becomes_legacy(value):
    with pytest.raises(BudgetStop): checkpoint.selection(value)


@pytest.mark.parametrize('mutation', [
    lambda m: m[checkpoint.KEY]['workers'].pop(),
    lambda m: m[checkpoint.KEY]['workers'].reverse(),
    lambda m: m[checkpoint.KEY].update(eligible=True),
    lambda m: m['budget']['continuation'].update(reconciliation={}),
    lambda m: m['budget']['continuation'].update(cost_usd='0'),
    lambda m: m['budget'].update(additional_usd='600'),
    lambda m: m['budget']['per_job_attempt_usd'].update(synthetic_integration='41'),
    lambda m: m['native_runtime'].update(version='changed'),
    lambda m: m['model'].update(model='changed'),
    lambda m: m['pinned_files'].clear(),
])
def test_changed_or_partial_successor_refused(example, mutation):
    mutation(example.manifest)
    with pytest.raises(BudgetStop): checkpoint.validate(example.manifest)


@pytest.mark.parametrize('kind', ['hidden_file', 'directory', 'symlink', 'external_hardlink', 'changed_proposal'])
def test_complete_freeze_detects_ignored_additions_links_and_changes(example, tmp_path, kind):
    proposal = Path(example.workers[0]['proposal_path'])
    if kind == 'hidden_file': (example.root / '.ignored').write_text('synthetic')
    elif kind == 'directory': (example.root / '.newdir').mkdir()
    elif kind == 'symlink': (example.root / '.linked').symlink_to(proposal)
    elif kind == 'external_hardlink': os.link(proposal, tmp_path / 'external')
    else: proposal.write_text('changed synthetic bytes')
    with pytest.raises(BudgetStop): checkpoint.validate(example.manifest)


@pytest.mark.parametrize('mutation', [
    lambda e: e.source.update(audit_worker_checkpoint={}),
    lambda e: e.ledger['requests'][0].update(status='pending'),
    lambda e: e.result['runtime'].update(unfinished_handlers=True),
    lambda e: e.result['runtime'].update(proxy_shutdown_complete=False),
    lambda e: e.result.update(status='completed_pending_independent_review'),
])
def test_coherently_resealed_ineligible_source_is_refused(example, mutation):
    mutation(example); example.refresh()
    with pytest.raises(BudgetStop): checkpoint.validate(example.manifest)


def test_scanner_refusal_cannot_be_replaced_by_an_eligibility_boolean(example, monkeypatch):
    from audit_controls import checkpoint_eligibility
    def reject(*args): raise BudgetStop('synthetic checker attempt')
    monkeypatch.setattr(checkpoint_eligibility, 'verify', reject)
    with pytest.raises(BudgetStop, match='checker attempt'): checkpoint.validate(example.manifest)


def test_historical_owner_snapshot_survives_legitimate_tip_advance(example):
    save(example.state, {'synthetic': 'later owner'})
    assert checkpoint.validate(example.manifest).sha256 == sha(example.source_registration)


def test_preparation_pin_collection_needs_no_successor_pins(example):
    example.manifest['pinned_files'] = {}
    assert checkpoint.validate(example.manifest, require_pins=False).workers
    with pytest.raises(BudgetStop): checkpoint.validate(example.manifest)


@pytest.mark.parametrize('mutation', [
    lambda e: e.ledger['requests'][0].update(cost_usd='41'),
    lambda e: e.ledger['requests'][0].update(cost_usd='35'),
    lambda e: e.ledger['requests'][0].update(attempt_cap_usd='50'),
    lambda e: e.ledger['requests'][0].update(stage_cap_usd='40'),
    lambda e: e.ledger['requests'][0].update(settlement_basis='unconfirmed_native_stall_full_reservation'),
])
def test_stopped_source_still_enforces_original_aggregate_limits(example, mutation):
    from budgeted_cborg import STALL_DEBIT_BASIS
    mutation(example)
    if 'settlement_basis' in example.ledger['requests'][0]:
        example.ledger['requests'][0]['settlement_basis'] = STALL_DEBIT_BASIS
    example.refresh()
    with pytest.raises(BudgetStop): checkpoint.validate(example.manifest)


def test_another_parent_job_cannot_reuse_identical_input_bytes(example):
    example.manifest['parent']['job_id'] = 'another_project'
    with pytest.raises(BudgetStop, match='lineage'): checkpoint.validate(example.manifest)


def test_new_plan_must_preserve_every_source_worker_and_original_bytes(example, tmp_path):
    plan = save(tmp_path / 'altered-plan.json', {'workers': [{'id':'worker_0001'}]})
    example.manifest['audit_batches']['plan_path'] = str(plan)
    with pytest.raises(BudgetStop, match='worker plan'): checkpoint.validate(example.manifest)


def test_new_scientific_repository_requires_exact_source_implementation(example, tmp_path):
    import shutil
    target=tmp_path/'new-repository';target.mkdir()
    for name in example.source['pinned_files']:
        p=Path(name)
        if p.is_relative_to(tmp_path):
            rel=p.relative_to(tmp_path)
            if rel.parts[0]=='src' or str(rel) in ('pyproject.toml','poetry.lock'):
                dest=target/rel;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,dest)
    example.manifest['repository']=str(target)
    assert checkpoint.validate(example.manifest).workers
    (target/'src/data_sheets_schema/audit_batch_context.py').write_text('# changed scientific renderer\n')
    with pytest.raises(BudgetStop,match='scientific implementation'):checkpoint.validate(example.manifest)


def test_historical_proof_survives_current_helper_checkout_relocation(example, tmp_path, monkeypatch):
    from audit_controls import checkpoint_eligibility
    moved=tmp_path/'future-control-checkout';moved.mkdir()
    for module in (checkpoint,checkpoint_eligibility):
        original=Path(module.__file__);target=moved/original.name;target.write_bytes(original.read_bytes())
        monkeypatch.setattr(module,'__file__',str(target))
    resolved=checkpoint.validate(example.manifest)
    assert moved/'worker_checkpoint.py' in resolved.evidence_paths
    assert str(moved/'worker_checkpoint.py') not in example.manifest['pinned_files']
