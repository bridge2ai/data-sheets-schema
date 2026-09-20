"""Real audit/shared transitions with durable claim faults; no provider calls."""
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import stat
from types import SimpleNamespace
from concurrent.futures import ThreadPoolExecutor

import pytest
from filelock import FileLock, Timeout

import sequence_claim as claims
import continuation_sequence as shared
from audit_controls import registration as audit
from audit_controls.test_registration import accounting
from test_continuation_sequence import fixture as shared_fixture


@pytest.fixture(params=['audit', 'shared'])
def claim_case(request, tmp_path):
    if request.param == 'audit':
        manifest, _, _, _, registration = request.getfixturevalue('accounting')
        state = Path(manifest['sequence_state'])
    else:
        manifest, registration, state = shared_fixture(tmp_path)
    claims.select(manifest, True)
    manifest['pinned_files'].update({str(p): shared.sha(p) for p in claims.IMPLEMENTATIONS})
    registration.write_bytes(shared.canonical(manifest) + b'\n')
    return SimpleNamespace(kind=request.param, manifest=manifest, registration=registration,
        identity=shared.sha(registration), state=state, directory=registration.parent/'sequence_claim',
        failure=registration.parent/'sequence_claim_failed.json',
        predecessor=state.read_bytes() if state.exists() else None)


@contextmanager
def enter(case):
    if case.kind == 'audit':
        with audit.sequence_guard(case.manifest, case.identity):
            yield None
    else:
        with shared.owned_sequence(case.manifest, case.registration, case.identity) as owner:
            yield owner


def owned_by(case):
    value = shared.read(case.state)
    return (value if case.kind == 'audit' else value['active_tip'])['registration_sha256']


def test_real_transition_preserves_exact_claim_and_origin_before_admission(claim_case, monkeypatch):
    c = claim_case
    frozen = {Path(p): Path(p).read_bytes() for p in c.manifest['pinned_files']}
    synced = set()
    original_sync = claims._fsync
    def fsync(fd):
        info = os.fstat(fd);synced.add((info.st_dev, info.st_ino));original_sync(fd)
    monkeypatch.setattr(claims, '_fsync', fsync)
    original_write = claims._write
    def write_under_existing_lock(path, raw):
        with pytest.raises(Timeout):
            with FileLock(str(c.state)+'.lock', timeout=0): pytest.fail('snapshot wrote without origin lock')
        original_write(path, raw)
    monkeypatch.setattr(claims, '_write', write_under_existing_lock)
    with enter(c):
        owner_bytes = c.state.read_bytes()
        assert (c.directory/'owner.json').read_bytes() == owner_bytes
        proof = shared.read(c.directory/'manifest.json')
        assert proof['canonical_state_path'] == str(c.state)
        assert proof['claiming_registration_sha256'] == c.identity
        assert proof['claiming_registration_path'] == str(c.registration)
        assert proof['owner_sha256'] == hashlib.sha256(owner_bytes).hexdigest()
        assert proof['origin']['ledger_path'] == str(c.state.with_name('billing.json'))
        assert proof['implementation_sha256'] == shared.sha(claims.IMPLEMENTATION)
        assert proof['predecessor_absent'] is (c.predecessor is None)
        if c.predecessor is not None:
            assert (c.directory/'predecessor.json').read_bytes() == c.predecessor
            assert proof['predecessor_sha256'] == hashlib.sha256(c.predecessor).hexdigest()
        for p in [c.state, c.state.parent, c.directory, c.directory.parent, *c.directory.iterdir()]:
            info = p.stat()
            assert (info.st_dev, info.st_ino) in synced
    assert {p: p.read_bytes() for p in frozen} == frozen
    assert owned_by(c) == c.identity
    if c.kind == 'audit':
        with pytest.raises(audit.BudgetStop, match='already consumed'):
            with enter(c): pytest.fail('snapshot authorized audit reuse')
    else:
        before = {p: p.read_bytes() for p in c.directory.iterdir()}
        with enter(c) as owner: owner.verify_admission()
        assert {p: p.read_bytes() for p in c.directory.iterdir()} == before


@pytest.mark.parametrize('fault', ['write', 'file_fsync', 'directory_fsync', 'final_directory_fsync'])
def test_snapshot_failure_consumes_owner_without_any_provider_admission(claim_case, monkeypatch, fault):
    c = claim_case;admitted = []
    predecessor_ledger = Path(c.manifest['budget']['continuation']['checkpoint'])
    before = predecessor_ledger.read_bytes()
    with monkeypatch.context() as changes:
        if fault == 'write':
            real = claims._write
            def fail_write(path, raw):
                if path.name == 'owner.json': raise OSError('synthetic snapshot write failure')
                real(path, raw)
            changes.setattr(claims, '_write', fail_write)
        elif fault == 'final_directory_fsync':
            real = claims._sync
            def fail_last(path):
                if path == c.directory.parent: os.fsync(-1)
                real(path)
            changes.setattr(claims, '_sync', fail_last)
        else:
            real = claims._fsync
            def fail_sync(fd):
                is_dir = stat.S_ISDIR(os.fstat(fd).st_mode)
                if is_dir == (fault == 'directory_fsync'): os.fsync(-1)
                real(fd)
            changes.setattr(claims, '_fsync', fail_sync)
        with pytest.raises(audit.BudgetStop, match='preservation failed'):
            with enter(c): admitted.append('provider admission')
    assert admitted == [] and owned_by(c) == c.identity
    assert predecessor_ledger.read_bytes() == before
    own_ledger = Path(c.manifest['budget']['ledger_path'])
    if own_ledger.exists():
        assert shared.read(own_ledger)['requests'] == shared.read(predecessor_ledger)['requests']
    with pytest.raises(audit.BudgetStop):
        with enter(c): pytest.fail('failed preservation was silently retried')


@pytest.mark.parametrize('boundary', [
    'state_fsync', 'state_dir_fsync', 'claim_mkdir',
    'owner_write', 'owner_fsync', 'owner_publish', 'owner_unlink',
    'predecessor_write', 'predecessor_fsync', 'predecessor_publish', 'predecessor_unlink',
    'manifest_write', 'manifest_fsync', 'manifest_publish', 'manifest_unlink',
    'claim_dir_fsync', 'condition_dir_fsync', 'claim_verify', 'ready_publish'])
def test_each_persistence_failure_blocks_reentry_even_when_failure_receipt_fails(claim_case, monkeypatch, boundary):
    c = claim_case
    if boundary.startswith('predecessor_') and c.predecessor is None:
        pytest.skip('first audit has no predecessor file')
    original_write, original_sync = claims._write, claims._sync
    original_fsync, original_link = claims._fsync, os.link
    original_unlink, original_mkdir, original_verify = Path.unlink, Path.mkdir, claims.verify
    active, hit = [], []
    def fail(name):
        if name == boundary:
            hit.append(name)
            raise OSError('injected persistence boundary: ' + name)
    def write(path, raw):
        if path == c.failure:
            raise OSError('failure receipt also unavailable')
        fail(path.stem + '_write')
        active.append(path.stem + '_fsync')
        try: original_write(path, raw)
        finally: active.pop()
    def sync(path):
        label = {c.state: 'state_fsync', c.state.parent: 'state_dir_fsync',
                 c.directory: 'claim_dir_fsync', c.directory.parent: 'condition_dir_fsync'}[path]
        active.append(label)
        try: original_sync(path)
        finally: active.pop()
    def fsync(fd):
        fail(active[-1]);original_fsync(fd)
    def link(source, destination, **kwargs):
        if Path(destination).parent == c.directory:
            fail(Path(destination).stem + '_publish')
        return original_link(source, destination, **kwargs)
    def unlink(path, *args, **kwargs):
        if path.parent == c.directory:
            fail(path.name.removeprefix('.').removesuffix('.json.tmp') + '_unlink')
        return original_unlink(path, *args, **kwargs)
    def mkdir(path, *args, **kwargs):
        if path == c.directory: fail('claim_mkdir')
        return original_mkdir(path, *args, **kwargs)
    def verify(*args, **kwargs):
        fail('claim_verify');return original_verify(*args, **kwargs)
    with monkeypatch.context() as changes:
        for name, function in (('_write', write), ('_sync', sync), ('_fsync', fsync), ('verify', verify)):
            changes.setattr(claims, name, function)
        changes.setattr(os, 'link', link)
        changes.setattr(Path, 'unlink', unlink);changes.setattr(Path, 'mkdir', mkdir)
        with pytest.raises(audit.BudgetStop, match='preservation failed'):
            with enter(c): pytest.fail('failed preservation admitted')
    assert hit == [boundary] and owned_by(c) == c.identity
    assert not c.failure.exists() and not (c.directory/'ready.json').exists()
    with pytest.raises(audit.BudgetStop):
        with enter(c): pytest.fail('failed claim admitted when failure receipt was lost')


def test_ready_publication_is_last_preservation_operation(claim_case, monkeypatch):
    c = claim_case;published = []
    original_link, original_sync, original_verify = os.link, claims._fsync, claims.verify
    def link(source, destination, **kwargs):
        result = original_link(source, destination, **kwargs)
        if Path(destination) == c.directory/'ready.json': published.append(True)
        return result
    def fsync(fd):
        assert not published, 'post-witness fsync could fail after publishing success'
        original_sync(fd)
    def verify(*args, **kwargs):
        # Shared admission verifies after preservation succeeds. The publisher
        # itself must finish every fallible check before the final link syscall.
        if kwargs.get('complete') is False: assert not published
        return original_verify(*args, **kwargs)
    monkeypatch.setattr(os, 'link', link);monkeypatch.setattr(claims, '_fsync', fsync)
    monkeypatch.setattr(claims, 'verify', verify)
    with enter(c) as owner:
        assert published == [True]
        assert os.path.samefile(c.directory/'manifest.json', c.directory/'ready.json')
        if owner is not None:
            with ThreadPoolExecutor(max_workers=1) as pool: pool.submit(owner.verify_admission).result()


@pytest.mark.parametrize('durable', [False, True])
@pytest.mark.parametrize('race', [False, True])
def test_audit_lock_alias_never_truncates_checkpoint(accounting, monkeypatch, durable, race):
    m, _, _, checkpoint, registration = accounting
    if durable:
        claims.select(m, True)
        m['pinned_files'].update({str(p): shared.sha(p) for p in claims.IMPLEMENTATIONS})
    registration.write_bytes(shared.canonical(m)+b'\n')
    lock = Path(m['sequence_state']+'.lock');before = checkpoint.read_bytes()
    if race:
        original = os.open
        def open_after_alias(path, *args, **kwargs):
            if Path(path) == lock and not lock.exists(): os.link(checkpoint, lock)
            return original(path, *args, **kwargs)
        monkeypatch.setattr(os, 'open', open_after_alias)
    else: os.link(checkpoint, lock)
    with pytest.raises(audit.BudgetStop, match='lock is aliased'):
        with audit.sequence_guard(m, shared.sha(registration)): pytest.fail('aliased lock admitted')
    assert checkpoint.read_bytes() == before and not Path(m['sequence_state']).exists()


def test_audit_lock_replacement_during_acquisition_is_refused(accounting, monkeypatch):
    m, _, _, checkpoint, registration = accounting
    registration.write_bytes(shared.canonical(m)+b'\n')
    lock = Path(m['sequence_state']+'.lock');before = checkpoint.read_bytes()
    original = audit.fcntl.flock
    def flock(fd, operation):
        result = original(fd, operation)
        if operation & audit.fcntl.LOCK_EX:
            lock.unlink();lock.symlink_to(checkpoint)
        return result
    monkeypatch.setattr(audit.fcntl, 'flock', flock)
    with pytest.raises(audit.BudgetStop, match='lock is aliased'):
        with audit.sequence_guard(m, shared.sha(registration)): pytest.fail('replaced lock admitted')
    assert checkpoint.read_bytes() == before and not Path(m['sequence_state']).exists()


def test_existing_foreign_claim_is_never_overwritten(claim_case):
    c = claim_case;c.directory.mkdir();foreign = c.directory/'owner.json';foreign.write_bytes(b'foreign bytes')
    with pytest.raises(audit.BudgetStop):
        with enter(c): pytest.fail('foreign claim admitted')
    assert foreign.read_bytes() == b'foreign bytes'
    assert owned_by(c) == c.identity


def test_symlinked_claim_is_refused_without_touching_target(claim_case, tmp_path):
    c = claim_case;foreign = tmp_path/'foreign';foreign.mkdir();marker = foreign/'owner.json';marker.write_bytes(b'foreign')
    c.directory.symlink_to(foreign, target_is_directory=True)
    with pytest.raises(audit.BudgetStop):
        with enter(c): pytest.fail('symlink admitted')
    assert marker.read_bytes() == b'foreign'
    assert (c.state.read_bytes() if c.state.exists() else None) == c.predecessor


@pytest.mark.parametrize('damage', ['owner', 'predecessor', 'manifest', 'missing', 'symlink',
                                   'missing_ready', 'copied_ready', 'extra_alias'])
def test_shared_same_owner_reentry_checks_existing_claim_without_repair(claim_case, damage, tmp_path):
    c = claim_case
    if c.kind != 'shared': pytest.skip('audit identities are never reentered')
    with enter(c): pass
    target = c.directory/({'owner':'owner.json','predecessor':'predecessor.json'}.get(damage,'manifest.json'))
    if damage == 'missing_ready': (c.directory/'ready.json').unlink()
    elif damage == 'copied_ready':
        ready = c.directory/'ready.json';raw = ready.read_bytes();ready.unlink();ready.write_bytes(raw)
    elif damage == 'extra_alias': os.link(c.directory/'manifest.json', tmp_path/'extra-alias.json')
    elif damage == 'missing': target.unlink()
    elif damage == 'symlink':
        foreign = tmp_path/'foreign-proof.json';foreign.write_bytes(target.read_bytes());target.unlink();target.symlink_to(foreign)
    else: target.write_bytes(target.read_bytes()+b' ')
    before = {p.name: p.read_bytes() for p in c.directory.iterdir()}
    with pytest.raises(audit.BudgetStop):
        with enter(c): pytest.fail('damaged same-owner claim admitted')
    assert {p.name: p.read_bytes() for p in c.directory.iterdir()} == before


@pytest.mark.parametrize('damage', ['missing_pin', 'missing_lock_pin', 'foreign_protocol', 'foreign_registration'])
def test_invalid_protocol_binding_cannot_advance_owner(claim_case, damage):
    c = claim_case
    if damage == 'missing_pin': c.manifest['pinned_files'].pop(str(claims.IMPLEMENTATION))
    elif damage == 'missing_lock_pin': c.manifest['pinned_files'].pop(str(Path(audit.__file__).resolve()))
    elif damage == 'foreign_protocol': c.manifest['sequence_claim']['protocol'] = 'unreviewed'
    else: c.manifest['budget']['ledger_path'] = str(c.registration.parent.parent/'foreign/billing.json')
    c.registration.write_bytes(shared.canonical(c.manifest)+b'\n');c.identity = shared.sha(c.registration)
    with pytest.raises(audit.BudgetStop):
        with enter(c): pytest.fail('unbound claim admitted')
    assert (c.state.read_bytes() if c.state.exists() else None) == c.predecessor


def test_audit_predecessor_snapshot_preserves_original_noncanonical_json_bytes(accounting):
    m, _, _, checkpoint, registration = accounting
    previous = {'schema_version':1,'registration_sha256':shared.read(checkpoint)['manifest_sha256'],
        'source_registration_sha256':shared.sha(m['parent']['registration']),'ledger_path':str(checkpoint)}
    raw = (json.dumps(previous, indent=3)+' \n').encode()
    state = Path(m['sequence_state']);state.write_bytes(raw)
    claims.select(m, True);m['pinned_files'].update({str(p): shared.sha(p) for p in claims.IMPLEMENTATIONS})
    registration.write_bytes(shared.canonical(m)+b'\n')
    with audit.sequence_guard(m, shared.sha(registration)):
        assert (registration.parent/'sequence_claim/predecessor.json').read_bytes() == raw


@pytest.mark.parametrize('value', [None, True, False, {}, {'protocol': 'unknown'}])
def test_only_explicit_known_protocol_is_supported(value):
    with pytest.raises(audit.BudgetStop): claims.enabled({'sequence_claim':value})
    assert claims.enabled({}) is False
