"""One-use prepared-worker rendezvous; no native process or observation."""
import os
import sys

import pytest

from data_sheets_schema import native_prepared_worker as worker


def setup_packet(tmp_path, monkeypatch):
    packet = tmp_path / 'packet'
    packet.mkdir()
    ipc = packet / 'worker'
    ipc.mkdir()
    attempt = tmp_path / 'attempt'
    monkeypatch.setattr(worker.time, 'time', lambda: 100.0)
    binding = dict(registration_raw=b'registration', attempt=attempt, max_age_seconds=1200)
    raw = worker.publish_prepared(ipc, **binding,
        source_sha256='a' * 64, environment_sha256='b' * 64)
    guard = tmp_path / 'guard.json'
    guard.write_bytes(b'guard')
    return ipc, binding, raw, guard


def proceed(ipc, raw, guard):
    return worker.publish_proceed(ipc, prepared_raw=raw, guard_path=guard,
                                  guard_sha256=worker.wire.sha(guard.read_bytes()))


def test_one_use_and_attempt_remains_absent(tmp_path, monkeypatch):
    ipc, binding, raw, guard = setup_packet(tmp_path, monkeypatch)
    assert worker.require_prepared(ipc, **binding, pid=os.getpid()) == raw
    proceed(ipc, raw, guard)
    result = worker.wait_proceed(ipc, prepared_raw=raw, **binding)
    assert result['guard_path'] == str(guard)
    assert (ipc / 'consumed.json').stat().st_size > 0
    assert not binding['attempt'].exists()
    with pytest.raises(FileExistsError):
        worker.wait_proceed(ipc, prepared_raw=raw, **binding)
    with pytest.raises(FileExistsError):
        proceed(ipc, raw, guard)


def test_stale_proceed(tmp_path, monkeypatch):
    ipc, binding, raw, guard = setup_packet(tmp_path, monkeypatch)
    proceed(ipc, raw, guard)
    monkeypatch.setattr(worker.time, 'time', lambda: 1300.0)
    with pytest.raises(ValueError, match='stale or foreign'):
        worker.wait_proceed(ipc, prepared_raw=raw, **binding)
    assert not (ipc / 'consumed.json').exists()


def test_timeout_without_proceed(tmp_path, monkeypatch):
    ipc, binding, raw, _ = setup_packet(tmp_path, monkeypatch)
    ticks = iter([0.0, 1200.0])
    monkeypatch.setattr(worker.time, 'monotonic', lambda: next(ticks))
    with pytest.raises(ValueError, match='timed out'):
        worker.wait_proceed(ipc, prepared_raw=raw, **binding)
    assert not binding['attempt'].exists()


def test_foreign_registration_or_process(tmp_path, monkeypatch):
    ipc, binding, _, _ = setup_packet(tmp_path, monkeypatch)
    with pytest.raises(ValueError, match='stale or foreign'):
        worker.require_prepared(ipc, **{**binding, 'registration_raw': b'foreign'}, pid=os.getpid())
    with pytest.raises(ValueError, match='another process'):
        worker.require_prepared(ipc, **binding, pid=os.getpid() + 1)


def test_changed_prepared_bytes(tmp_path, monkeypatch):
    ipc, binding, raw, _ = setup_packet(tmp_path, monkeypatch)
    doc = worker.wire.strict_json(raw)
    doc['source_sha256'] = 'c' * 64
    (ipc / 'prepared.json').write_bytes(worker.wire.canonical(doc))
    with pytest.raises(ValueError, match='identity changed'):
        worker.wait_proceed(ipc, prepared_raw=raw, **binding)


def test_changed_guard_bytes(tmp_path, monkeypatch):
    ipc, binding, raw, guard = setup_packet(tmp_path, monkeypatch)
    proceed(ipc, raw, guard)
    guard.write_bytes(b'changed')
    with pytest.raises(ValueError, match='guard bytes changed'):
        worker.wait_proceed(ipc, prepared_raw=raw, **binding)


def test_foreign_proceed(tmp_path, monkeypatch):
    ipc, binding, raw, guard = setup_packet(tmp_path, monkeypatch)
    proceed(ipc, raw, guard)
    path = ipc / 'proceed.json'
    doc = worker.wire.strict_json(path.read_bytes())
    doc['prepared_sha256'] = '0' * 64
    path.write_bytes(worker.wire.canonical(doc))
    with pytest.raises(ValueError, match='foreign proceed'):
        worker.wait_proceed(ipc, prepared_raw=raw, **binding)


def test_refuse_attempt_as_ipc(tmp_path):
    with pytest.raises(ValueError, match='overlaps'):
        worker.publish_prepared(tmp_path, registration_raw=b'registration', attempt=tmp_path,
            max_age_seconds=1200, source_sha256='a' * 64, environment_sha256='b' * 64)


def identity_fixture(tmp_path, monkeypatch):
    from data_sheets_schema import native_execution_authority_v2 as authority
    from data_sheets_schema import native_shared_controller as controller
    from data_sheets_schema import native_shared_registration_orchestration as registration
    from data_sheets_schema import native_prepared_verifier as verifier
    source = tmp_path / 'source.py'
    source.write_bytes(b'original source')
    review = tmp_path / 'review.json'
    review.write_bytes(b'original review')
    monkeypatch.setattr(authority, 'ROOT', tmp_path)
    monkeypatch.setattr(controller, 'captured_preparation_body', lambda raw:
        {'environment_manifest': {'sha256': 'a' * 64}})
    value = {'dependencies': {'base': {'package_sources': {
        str(source): worker.wire.sha(source.read_bytes())}, 'modules': {}},
        'additional_modules': {}}, 'preparation_raw_json': '{}'}
    monkeypatch.setattr(registration, 'verified', lambda raw: value)
    calls = []
    def recheck(raw, current, *, environment_mode):
        calls.append((raw, current, environment_mode))
        return current
    monkeypatch.setattr(registration, '_recheck_verified', recheck)
    monkeypatch.setattr(verifier, '_baseline', lambda value, full: [('baseline', (1, 2, 3))])
    monkeypatch.setattr(worker, '_full_preparation_baseline', lambda pin: [('baseline', (1, 2, 3))])
    def local_verify(request):
        return verifier.verify({**request, 'interpreter': [sys.executable, sys.version,
            sys.implementation.cache_tag]})
    monkeypatch.setattr(worker, '_verify', local_verify)
    identity = worker.PreparedIdentity(b'registration', value,
        {'inputs': {'review': str(review)}, 'raw': {'review': review.read_bytes()}})
    return identity, source, review, calls


def test_changed_source_refuses_before_live_reconstruction(tmp_path, monkeypatch):
    identity, source, _, calls = identity_fixture(tmp_path, monkeypatch)
    source.write_bytes(b'changed source')
    with pytest.raises(ValueError, match='source bytes changed'):
        identity.recheck()
    assert not calls


def test_changed_authority_refuses(tmp_path, monkeypatch):
    identity, _, review, calls = identity_fixture(tmp_path, monkeypatch)
    review.write_bytes(b'changed review')
    with pytest.raises(ValueError, match='authority bytes changed'):
        identity.recheck()
    assert not calls


def test_each_recheck_requires_fresh_census_against_prepared_baseline(tmp_path, monkeypatch):
    identity, _, _, calls = identity_fixture(tmp_path, monkeypatch)
    first = identity.recheck()
    first['dependencies'].clear()
    second = identity.recheck()
    assert second['dependencies']
    assert len(calls) == 2
    assert all(call[0] == b'registration' and call[2] == 'light' for call in calls)


def test_recheck_rejects_changed_full_census_baseline(tmp_path, monkeypatch):
    identity, _, _, calls = identity_fixture(tmp_path, monkeypatch)
    identity.baseline = [('baseline', (1, 2, 4))]
    with pytest.raises(ValueError, match='changed since full verification'):
        identity.recheck()
    assert len(calls) == 1


def test_empty_pinned_package_initializer_is_valid(tmp_path, monkeypatch):
    identity, source, _, calls = identity_fixture(tmp_path, monkeypatch)
    source.write_bytes(b'')
    identity.sources = ((source, worker.wire.sha(b'')),)
    identity.recheck()
    assert len(calls) == 1


def test_registration_file_and_prepared_record_are_freshly_checked(tmp_path, monkeypatch):
    identity, _, _, calls = identity_fixture(tmp_path, monkeypatch)
    path = tmp_path / 'registration.json'
    path.write_bytes(identity.registration_raw)
    identity.registration_path = str(path)
    identity.recheck()
    path.write_bytes(b'foreign')
    with pytest.raises(ValueError, match='registration file changed'):
        identity.recheck()
    path.write_bytes(identity.registration_raw)
    prepared = tmp_path / 'prepared.json'
    raw = worker.wire.canonical({'registration_sha256': worker.wire.sha(identity.registration_raw)})
    prepared.write_bytes(raw)
    identity.prepared = [str(prepared), raw.decode()]
    identity.recheck()
    prepared.write_bytes(b'foreign')
    with pytest.raises(ValueError, match='record bytes changed'):
        identity.recheck()
    assert len(calls) == 2


def test_constructor_uses_fresh_process_under_real_consumer_import_restriction():
    from data_sheets_schema import native_shared_authority_wire as envelope
    from tests.utils.native_shared_consumer_scope import loaded_consumer
    import importlib
    preparation = dict.fromkeys(envelope.PREPARATION_KEYS)
    preparation.update(kind=envelope.PREPARATION_KIND, schema_version=envelope.VERSION,
        execution=envelope.PREPARATION_SCOPE, environment_manifest={'sha256': 'a' * 64})
    raw = worker.wire.canonical({'authority_version': 2,
        'controller_sources_sha256': envelope.CONTROLLER_SOURCES_SHA256, 'registration': preparation})
    value = {'dependencies': {'base': {'package_sources': {}, 'modules': {}},
        'additional_modules': {}}, 'preparation_raw_json': raw.decode()}
    with loaded_consumer('native_prepared_worker') as scoped:
        assert scoped.PreparedIdentity is not worker.PreparedIdentity
        with pytest.raises(ValueError, match='cannot import verifier bootstrap'):
            importlib.import_module('data_sheets_schema.native_execution_authority_v2')
        # The real constructor and real subprocess must reach fresh validation.
        # Invalid execution bytes refuse there, not at the consumer import wall.
        with pytest.raises(ValueError, match='prepared fresh verifier refused') as refusal:
            scoped.PreparedIdentity(b'invalid registration', value, {'inputs': {}, 'raw': {}})
        assert 'cannot import verifier bootstrap' not in str(refusal.value)
        with pytest.raises(ValueError, match='differs from capture authority'):
            scoped.checked_value(object.__new__(worker.PreparedIdentity), b'invalid registration')


def test_verifier_rejects_replayed_or_nonzero_reply(monkeypatch):
    class Child:
        returncode = 0
        def communicate(self, raw, timeout):
            request = worker.wire.strict_json(raw)
            return worker.wire.canonical({'nonce': 'old nonce',
                'request_sha256': worker.wire.sha(raw), 'passed': True}), b''
    monkeypatch.setattr(worker.subprocess, 'Popen', lambda *args, **kwargs: Child())
    with pytest.raises(ValueError, match='foreign result'):
        worker._verify({})
    Child.returncode = 1
    with pytest.raises(ValueError, match='fresh verifier refused'):
        worker._verify({})


def test_verifier_timeout_kills_group_and_reaps(monkeypatch):
    events = []
    class Child:
        pid = 12345
        def communicate(self, raw, timeout):
            assert timeout == worker.VERIFY_SECONDS
            raise worker.subprocess.TimeoutExpired('verifier', timeout)
        def wait(self):
            events.append('reaped')
    monkeypatch.setattr(worker.subprocess, 'Popen', lambda *args, **kwargs: Child())
    monkeypatch.setattr(worker.os, 'killpg', lambda pid, sig: events.append((pid, sig)))
    with pytest.raises(worker.subprocess.TimeoutExpired):
        worker._verify({})
    assert events == [(12345, worker.signal.SIGKILL), 'reaped']
