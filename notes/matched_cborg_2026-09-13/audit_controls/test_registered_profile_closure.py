"""Synthetic non-neutral closed histories retain registered locators (#2396).

The model, provider and terminal scientific checker are never invoked. Typed
histories, request accounting, rendering and descendant closure replay are real;
only the separately tested checkpoint document-proof seam supplies a fixture.
"""
import json
import os
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import pytest

from budgeted_cborg import BudgetStop, Ledger, attempt_identity
from data_sheets_schema import profiles, audit_batches, audit_batch_context
from . import batch_native as runtime, batch_output as output, native, registration
from . import batch_registration, worker_checkpoint as checkpoint
from .test_batch_runtime import batch, BatchSession, proposal, close_session, finish_integrator
from .test_worker_checkpoint_runtime import selected_manifest
from .test_batch_downstream import downstream, shared_ancestry, final_registration, sequence
from tests.test_audit_batch_context import staged


@pytest.fixture
def profile_batch(batch, tmp_path, monkeypatch):
    roots = [tmp_path / name for name in ('source-repository', 'successor-repository',
                                          'downstream-repository')]
    relative = Path('src/data_sheets_schema/b2ai_registry_vocabularies.yaml')
    for root in roots:
        path = root / relative
        path.parent.mkdir(parents=True)
        path.write_text('vocabularies: {}\n# Synthetic authority.\n')
        (root / 'pyproject.toml').write_text('[project]\nname = "data-sheets-schema"\n')
    batch.m.update(repository=str(roots[0]), profile='bridge2ai')
    batch.m['pinned_files'][str(roots[0] / relative)] = native.sha(roots[0] / relative)
    batch.m['budget']['ledger_path'] = str(batch.reg.parent / 'profile-billing.json')
    batch.reg.write_text(json.dumps(batch.m))
    batch.identity = native.sha(batch.reg)
    batch.owner = attempt_identity(batch.identity, batch.m['job']['id'])
    batch.ledger = Ledger(batch.m['budget']['ledger_path'], manifest_sha256=batch.identity,
                         total_cap=400, attempt_cap=40, attempt_caps_usd={batch.owner: 40})
    batch.ledger.require_resolved(batch.owner)
    monkeypatch.chdir(roots[0])
    batch.roots, batch.relative_vocabulary = roots, relative
    assert profiles.BRIDGE2AI.pin_path.absolute() == roots[0] / relative
    return batch


def test_closed_worker_replays_from_successor_and_downstream_checkouts(profile_batch, monkeypatch):
    batch = profile_batch
    session = BatchSession(batch, 'worker_0001')
    session.write(json.dumps(proposal(batch, 'worker_0001')))
    assert session.check()['grammar']['passed']
    session.seal()
    closed = close_session(session)
    for root in batch.roots[1:]:
        monkeypatch.chdir(root)
        assert profiles.BRIDGE2AI.pin_path.absolute() == root / batch.relative_vocabulary
        assert runtime.verify_child_closure(batch.m, batch.identity, 'worker_0001') == closed


@pytest.fixture
def complete_profile_batch(profile_batch, staged):
    """Real P7/R23 renderer, policy, grammar, typed history and accounting."""
    b = profile_batch
    b.m.update(render_version=23,
        scientific_contract_transition={'kind': 'frozen_pair_child_navigation_v1'},
        audit_batch_navigation={'kind': 'explicit_child_reads_v1'})
    b.m['inputs'] = {k: str(v) for k, v in staged['files'].items()}
    b.m['pinned_files'].update({str(p): native.sha(p) for p in staged['files'].values()})
    parent = Path(b.m['parent']['registration'])
    value = json.loads(parent.read_bytes()); value['generation']['jobs'][0]['project'] = 'example'
    parent.write_text(json.dumps(value))
    b.plan = staged['plan']
    plan_path = Path(b.m['audit_batches']['plan_path'])
    plan_path.write_bytes(audit_batches.canonical_bytes(b.plan))
    b.m['pinned_files'][str(plan_path)] = native.sha(plan_path)
    b.m['audit_batches'] = output.specification(b.m, b.reg,
        worker_total_cap_usd='24', plan_path=plan_path)
    args = batch_registration.scientific_arguments(b.m)
    for row in b.m['audit_batches']['children']:
        if row['kind'] == 'worker':
            Path(row['instruction']).write_text(audit_batch_context.render_worker_context(
                **args, worker_id=row['id'], audit_batch_navigation='explicit_child_reads_v1'))
        else:
            Path(b.m['audit_batches']['integration_base']).write_text(
                audit_batch_context.render_integration_base_context(**args))
        Path(row['system_prompt']).write_text(batch_registration.child_system(b.m, row['id']))
        b.m['pinned_files'][row['system_prompt']] = native.sha(row['system_prompt'])
    b.m['budget']['ledger_path'] = str(b.reg.parent / 'complete-profile-billing.json')
    b.reg.write_text(json.dumps(b.m)); b.identity = native.sha(b.reg)
    b.owner = attempt_identity(b.identity, b.m['job']['id'])
    b.ledger = Ledger(b.m['budget']['ledger_path'], manifest_sha256=b.identity,
                     total_cap=400, attempt_cap=40, attempt_caps_usd={b.owner: 40})
    b.ledger.require_resolved(b.owner)
    return b


def close_workers(b):
    closed = []
    for worker in b.plan['workers']:
        s = BatchSession(b, worker['id'])
        s.write(json.dumps(proposal(b, worker['id'])))
        assert s.check()['grammar']['passed']; s.seal()
        closed.append(close_session(s))
    return closed


def finish_batch(b, closed):
    runtime.prepare_integration(b.m, b.identity)
    index = audit_batches.build_index(b.plan, output.proposals(b.m))
    case = SimpleNamespace(batch=b, session=BatchSession(b, 'integration'), closed=closed,
        integration={'kind': 'audit_integration_v1', 'proposal_index_sha256': index['sha256'],
            'retain_other_rows_from_index_sha256': index['sha256'], 'row_replacements': [],
            'finding_decisions': [], 'new_findings': [], 'summary': 'Synthetic complete review.'})
    case.result = finish_integrator(case)
    if checkpoint.KEY in b.m:
        case.result['evidence']['worker_checkpoint'] = output.checkpoint_lineage(
            b.m, output.worker_closures(b.m, b.identity))
    return case


def checkpoint_successor(b, closed, tmp_path, monkeypatch):
    """Only the separately tested document-proof seam is replaced, not replay."""
    runtime.prepare_integration(b.m, b.identity)
    workers = b.m['audit_batches']['children'][:-1]
    refs = {r['child_id']: {'path': str(Path(w['attempt_dir']) / 'closed.json'),
            'sha256': r['closure_sha256']} for w, r in zip(workers, closed)}
    path = tmp_path / 'successor-condition/registration.json'; path.parent.mkdir()
    manifest, source = selected_manifest(b.m, path, workers, refs)
    source.sha256 = b.identity
    source.evidence_paths = frozenset(p for p in b.reg.parent.rglob('*') if p.is_file())
    manifest['repository'] = str(b.roots[1])
    manifest['pinned_files'].update({str(p): native.sha(p) for p in source.evidence_paths})
    pin = b.roots[1] / b.relative_vocabulary
    manifest['pinned_files'][str(pin)] = native.sha(pin)
    manifest['audit_worker_checkpoint']['source_ledger'] = {
        'path': str(b.ledger.path), 'sha256': native.sha(b.ledger.path)}
    manifest['job']['validator_argv'] = [manifest['python'], '-m', 'audit_controls.contract',
                                        '--registration', str(path)]
    manifest['budget']['ledger_path'] = str(path.parent / 'billing.json')
    monkeypatch.setattr(checkpoint, 'validate', lambda m, **kw: source)
    row = output.child(manifest, 'integration')
    system = Path(row['system_prompt']); system.parent.mkdir(parents=True)
    system.write_text(batch_registration.child_system(manifest, 'integration'))
    Path(manifest['job']['output_dir']).mkdir(parents=True)
    Path(row['attempt_dir']).parent.mkdir(parents=True)
    path.write_text(json.dumps(manifest)); identity = native.sha(path)
    owner = attempt_identity(identity, manifest['job']['id'])
    ledger = Ledger(manifest['budget']['ledger_path'], manifest_sha256=identity,
                    total_cap=400, attempt_cap=40, attempt_caps_usd={owner: 20})
    ledger.continue_from(b.ledger.path, expected_sha256=native.sha(b.ledger.path),
                         expected_cost_usd=str(len(closed)))
    return SimpleNamespace(m=manifest, reg=path, identity=identity, owner=owner,
        ledger=ledger, plan=b.plan, attempt=Path(manifest['job']['attempt_dir']),
        roots=b.roots, relative_vocabulary=b.relative_vocabulary), source


@pytest.mark.parametrize('inherited', [False, True])
def test_complete_non_neutral_closure_and_descendants_ignore_ambient_checkout(
        complete_profile_batch, tmp_path, monkeypatch, inherited):
    source_batch = complete_profile_batch
    source_closed = close_workers(source_batch)
    b = source_batch
    if inherited:
        b, source = checkpoint_successor(b, source_closed, tmp_path, monkeypatch)
        monkeypatch.chdir(b.roots[1])
        assert output.worker_closures(b.m, b.identity) == source_closed
    case = finish_batch(b, [] if inherited else source_closed)
    expected = runtime.verify_aggregate_closure(b.m, b.reg, case.result)
    phase4, _, _ = downstream(case, tmp_path)
    common, predecessor, shared_paths = shared_ancestry(case, tmp_path)
    paths = expected | shared_paths | {b.reg, b.ledger.path, source_batch.reg, source_batch.ledger.path}
    before = {p: (p.read_bytes(), p.stat().st_ino, p.stat().st_nlink) for p in paths}
    # The third checkout's authority is intentionally different, not just renamed.
    (b.roots[2] / b.relative_vocabulary).write_text('vocabularies: {}\n# Unrelated later authority.\n')
    for root in b.roots[1:]:
        monkeypatch.chdir(root)
        old_cwd = Path.cwd()
        def forbidden_chdir(*args):
            pytest.fail('closure replay must not change cwd')
        with monkeypatch.context() as local:
            local.setattr(os, 'chdir', forbidden_chdir)
            if inherited:
                assert output.worker_closures(b.m, b.identity) == source_closed
            assert runtime.verify_aggregate_closure(b.m, b.reg, case.result) == expected
            assert expected <= final_registration.required_paths(phase4)
            ledger, total, state = sequence._closure(common, predecessor, 'synthetic-lineage')
            assert len(ledger['requests']) == 3 and str(total) == '3'
            assert state == {'synthetic': 'closed prior state'}
            assert Path.cwd() == old_cwd
    assert before == {p: (p.read_bytes(), p.stat().st_ino, p.stat().st_nlink) for p in paths}


@pytest.mark.parametrize('damage', ['changed', 'missing_pin', 'missing_file', 'symlink'])
def test_registered_worker_authority_mutation_still_refuses(profile_batch, monkeypatch, damage):
    b = profile_batch
    s = BatchSession(b, 'worker_0001'); s.write(json.dumps(proposal(b, 'worker_0001')))
    s.check(); s.seal(); close_session(s)
    pin = b.roots[0] / b.relative_vocabulary
    if damage == 'changed': pin.write_text('vocabularies: {}\n# Changed original authority.\n')
    elif damage == 'missing_pin': del b.m['pinned_files'][str(pin)]
    else:
        pin.unlink()
        if damage == 'symlink': pin.symlink_to(b.roots[1] / b.relative_vocabulary)
    monkeypatch.chdir(b.roots[2])
    with pytest.raises((BudgetStop, OSError)):
        runtime.verify_child_closure(b.m, b.identity, 'worker_0001')


def test_absolute_external_profile_and_neutral_semantics_are_preserved(profile_batch, tmp_path, monkeypatch):
    b = profile_batch
    external = tmp_path / 'external-authority.yaml'; external.write_text('vocabularies: {}\n')
    profile = replace(profiles.NEUTRAL, name='synthetic_external', vocabulary_pin=external)
    monkeypatch.setitem(profiles.PROFILES, profile.name, profile)
    b.m['profile'] = profile.name; b.m['pinned_files'][str(external)] = native.sha(external)
    for root in b.roots:
        monkeypatch.chdir(root)
        assert registration.registered_profile(b.m).pin_path == external
        assert external in registration.batch_authority_paths(b.m)
        assert registration.registered_profile({'profile': 'neutral'}) is profiles.NEUTRAL
    assert profiles.PROFILES[profile.name] is profile


def test_same_checkout_policy_and_rendered_bytes_match_legacy_resolver(complete_profile_batch, monkeypatch):
    b = complete_profile_batch
    policy = runtime.build_policy(b.m, b.reg, 'worker_0001')
    args = batch_registration.scientific_arguments(b.m)
    rendered = audit_batch_context.render_worker_context(**args,
        worker_id='worker_0001', audit_batch_navigation='explicit_child_reads_v1')
    base = audit_batch_context.render_integration_base_context(**args)
    original_profile = profiles.BRIDGE2AI
    with monkeypatch.context() as legacy:
        legacy.setattr(registration, 'registered_profile', lambda m: profiles.profile_named(m['profile']))
        legacy.setattr(batch_registration, 'registered_profile', registration.registered_profile)
        old_args = batch_registration.scientific_arguments(b.m)
        assert runtime.build_policy(b.m, b.reg, 'worker_0001') == policy
        assert audit_batch_context.render_worker_context(**old_args,
            worker_id='worker_0001', audit_batch_navigation='explicit_child_reads_v1') == rendered
        assert audit_batch_context.render_integration_base_context(**old_args) == base
    assert profiles.BRIDGE2AI is original_profile and original_profile.tracks_digest_pin


def test_relative_vocabulary_escape_is_not_rebased_or_resolved_ambiently(profile_batch, monkeypatch):
    from data_sheets_schema import schema_digest
    b = profile_batch
    monkeypatch.setattr(schema_digest, 'VOCABULARY_PIN',
        Path('../successor-repository') / b.relative_vocabulary)
    monkeypatch.chdir(b.roots[2])
    with pytest.raises(BudgetStop, match='canonical'):
        registration.registered_profile(b.m)
