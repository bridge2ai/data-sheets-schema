"""Lead cost ruling: explicit full/light checks and process-only reuse, 2026-11-14."""
import json
import os
from pathlib import Path
from types import ModuleType

import pytest

from data_sheets_schema import native_environment_manifest as m
from data_sheets_schema import native_shared_contract as c
from tests.test_native_environment_manifest import installed  # noqa: F401


def pin_document(path, value):
    raw = c.canonical(value)
    path.write_bytes(raw)
    return {'path': str(path), 'bytes': len(raw), 'sha256': c.sha(raw)}


def forbid(*args, **kwargs):
    raise AssertionError('payload hashing or regeneration must not occur')


def test_light_mode_never_hashes_payload_and_documents_same_size_limit(installed, tmp_path, monkeypatch):
    loose = installed.root / 'unowned.py'
    loose.write_bytes(b'old')
    pin = pin_document(tmp_path / 'manifest.json', m.generate())
    (installed.root / 'file.py').write_bytes(b'SYNTHETIC = None\n')
    loose.write_bytes(b'new')
    monkeypatch.setattr(m, 'generate', forbid)
    monkeypatch.setattr(m, '_verify_payload', forbid)
    monkeypatch.setattr(m, '_capture_unowned_file', forbid)
    assert m.verify(pin, mode='light')['kind'] == m.KIND


def test_full_mode_hashes_payload_and_refuses_same_size_edit(installed, tmp_path):
    pin = pin_document(tmp_path / 'manifest.json', m.generate())
    (installed.root / 'file.py').write_bytes(b'SYNTHETIC = None\n')
    with pytest.raises(ValueError, match='payload hash'):
        m.verify(pin, mode='full')


def test_full_result_cannot_cache_payload_changed_after_regeneration(installed, tmp_path, monkeypatch):
    pin = pin_document(tmp_path / 'manifest.json', m.generate())
    generate, calls = m.generate, []
    def mutate_after_generate():
        result = generate()
        calls.append(True)
        (installed.root / 'file.py').write_bytes(b'SYNTHETIC = None\n')
        return result
    monkeypatch.setattr(m, 'generate', mutate_after_generate)
    for _ in range(2):
        with pytest.raises(ValueError, match='payload changed during process full verification'):
            m.verify(pin, mode='full')
    assert calls == [True]


def test_light_record_mutation_after_read_refuses(installed, tmp_path, monkeypatch):
    pin = pin_document(tmp_path / 'manifest.json', m.generate())
    read = m.read_regular
    def mutate(path, role, **kwargs):
        result = read(path, role, **kwargs)
        if role == 'distribution_record':
            target = Path(path)
            target.write_bytes(target.read_bytes().replace(b'file.py', b'FILE.py'))
        return result
    monkeypatch.setattr(m, 'read_regular', mutate)
    with pytest.raises(ValueError, match='RECORD changed during environment census'):
        m.verify(pin, mode='light')


@pytest.mark.parametrize('change', ['record', 'size', 'missing', 'type', 'unowned_size',
                                   'unowned_add', 'unowned_remove', 'unhashed_size'])
def test_light_mode_rechecks_record_and_every_included_lstat(installed, tmp_path, change, monkeypatch):
    loose = installed.root / 'unowned.py'
    loose.write_bytes(b'old')
    unhashed = installed.root / 'unhashed.txt'
    unhashed.write_bytes(b'old')
    installed.add_file(Path('unhashed.txt'))
    pin = pin_document(tmp_path / 'manifest.json', m.generate())
    payload = installed.root / 'file.py'
    if change == 'record':
        installed.add_file(Path('missing.txt'))
    elif change == 'size':
        payload.write_bytes(b'different size')
    elif change == 'missing':
        payload.unlink()
    elif change == 'type':
        payload.unlink()
        payload.symlink_to(loose)
    elif change == 'unowned_size':
        loose.write_bytes(b'longer')
    elif change == 'unowned_add':
        (installed.root / 'added.py').write_bytes(b'new')
    elif change == 'unowned_remove':
        loose.unlink()
    else:
        unhashed.write_bytes(b'longer')
    monkeypatch.setattr(m, 'generate', forbid)
    monkeypatch.setattr(m, '_verify_payload', forbid)
    monkeypatch.setattr(m, '_capture_unowned_file', forbid)
    with pytest.raises(ValueError):
        m.verify(pin, mode='light')


def test_full_regeneration_once_across_module_instances_and_live_rechecks(installed, tmp_path, monkeypatch):
    pin = pin_document(tmp_path / 'manifest.json', m.generate())
    generate, calls = m.generate, []
    def count():
        calls.append(os.getpid())
        return generate()
    monkeypatch.setattr(m, 'generate', count)
    expected = m.verify(pin)  # default is full
    assert m.verify(pin, mode='full') == expected
    alias = ModuleType('data_sheets_schema._manifest_mode_test')
    alias.__package__, alias.__file__ = 'data_sheets_schema', m.__file__
    exec(compile(Path(m.__file__).read_bytes(), m.__file__, 'exec'), alias.__dict__)
    alias.generate = forbid
    assert alias.verify(pin, mode='full') == expected
    assert calls == [os.getpid()]
    with m.verification_scope(mode='light'):
        assert alias.preparation_mode() == 'light'
    assert alias.preparation_mode() == 'full'
    (installed.root / 'file.py').write_bytes(b'SYNTHETIC = None\n')
    with pytest.raises(ValueError, match='payload changed'):
        m.verify(pin, mode='full')
    assert calls == [os.getpid()]


def test_concurrent_full_calls_regenerate_once(installed, tmp_path, monkeypatch):
    from concurrent.futures import ThreadPoolExecutor
    import sys
    import threading
    import time

    pin = pin_document(tmp_path / 'manifest.json', m.generate())
    monkeypatch.delattr(sys, m._PROCESS_STATE_NAME, raising=False)
    generate, calls = m.generate, []
    ready = threading.Barrier(3)
    def count():
        calls.append(threading.get_ident())
        time.sleep(0.05)  # Let the other caller contend while regeneration runs.
        return generate()
    def check():
        ready.wait(timeout=10)
        return m.verify(pin, mode='full')
    monkeypatch.setattr(m, 'generate', count)
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(check) for _ in range(2)]
        ready.wait(timeout=10)
        values = [future.result(timeout=30) for future in futures]
    assert values[0] == values[1]
    assert len(calls) == 1


def test_full_result_not_inherited_by_fork(installed, tmp_path, monkeypatch):
    pin = pin_document(tmp_path / 'manifest.json', m.generate())
    generate, calls = m.generate, []
    def count():
        calls.append(os.getpid())
        return generate()
    monkeypatch.setattr(m, 'generate', count)
    m.verify(pin, mode='full')
    read_fd, write_fd = os.pipe()
    pid = os.fork()
    if pid == 0:
        try:
            os.close(read_fd)
            m.verify(pin, mode='full')
            os.write(write_fd, json.dumps(calls).encode())
            os._exit(0)
        except BaseException:
            os._exit(1)
    os.close(write_fd)
    try:
        actual = json.loads(os.read(read_fd, 4096))
    finally:
        os.close(read_fd)
        _, status = os.waitpid(pid, 0)
    assert status == 0
    assert actual == [os.getpid(), pid]
    assert calls == [os.getpid()]


def test_cached_full_still_checks_pin_and_interpreter(installed, tmp_path, monkeypatch):
    pin = pin_document(tmp_path / 'manifest.json', m.generate())
    m.verify(pin, mode='full')
    actual = m._interpreter_identity()
    monkeypatch.setattr(m, '_interpreter_identity', lambda: {**actual, 'version': 'changed'})
    with pytest.raises(ValueError, match='stale'):
        m.verify(pin, mode='full')
    Path(pin['path']).write_bytes(b'changed')
    with pytest.raises(ValueError, match='registered pin'):
        m.verify(pin, mode='light')


def test_light_scope_does_not_change_full_api_default(installed, tmp_path, monkeypatch):
    pin = pin_document(tmp_path / 'manifest.json', m.generate())
    monkeypatch.setattr(m, 'generate', forbid)
    with m.verification_scope(mode='light'):
        with pytest.raises(AssertionError, match='regeneration'):
            m.verify(pin)
    assert m.preparation_mode() == 'full'
    with pytest.raises(ValueError, match='unknown environment verification mode'):
        m.verify(pin, mode='unknown')


def test_dispatch_forces_full_even_inside_light_scope(tmp_path, monkeypatch):
    from data_sheets_schema import native_shared_registration_orchestration as r
    monkeypatch.chdir(r.authority.ROOT)
    preparation = {'environment_manifest': {'path': '/synthetic', 'bytes': 1, 'sha256': '0' * 64}}
    raw_preparation = c.canonical(preparation)
    body = {'schema_version': r.VERSION, 'dependencies': {}, 'working_directory': str(r.authority.ROOT),
            'preparation_raw_json': raw_preparation.decode(), 'preparation_sha256': c.sha(raw_preparation),
            **dict.fromkeys(('composition', 'system_path', 'permission_probe', 'attempt_id',
                             'attempt_directory', 'evidence_directory', 'max_draft_checks'))}
    raw = c.canonical({'authority_version': r.AUTHORITY_VERSION,
                       'controller_sources_sha256': r.authority.neutral.composition.SOURCES_SHA256,
                       'registration': body})
    monkeypatch.setattr(r, '_require_integrated_gate_implementation', lambda: None)
    monkeypatch.setattr(r.execution_v2, '_closed_execution', lambda body: None)
    monkeypatch.setattr(r.authority, 'dependency_identity', lambda: {})
    monkeypatch.setattr(r.authority, 'require_committed', lambda deps: None)
    monkeypatch.setattr(r.consumer, 'controller_sources', lambda: {})
    monkeypatch.setattr(r.consumer, 'validate_arguments', lambda *args, **kwargs: {})
    monkeypatch.setattr(r.captured_composition, 'captured_preparation_body', lambda raw: preparation)
    observed = []
    def stop(pin, *, mode):
        observed.append(mode)
        raise RuntimeError('stop at manifest boundary, before effects')
    monkeypatch.setattr(m, 'verify', stop)
    with m.verification_scope(mode='light'), pytest.raises(RuntimeError, match='before effects'):
        r._recheck_verified(raw, body)
    assert observed == ['full']


@pytest.mark.parametrize('entry,expected', [('capture_stage', 'light'), ('live_receipt_block', 'light'),
                                           ('live_provenance_block', 'full')])
def test_helper_and_recording_modes_are_explicit(entry, expected, monkeypatch):
    from data_sheets_schema import native_shared_capture_orchestration as host
    observed = []
    def stop(*args, _manifest_mode='full', **kwargs):
        observed.append(_manifest_mode)
        raise RuntimeError('stop at capture boundary')
    monkeypatch.setattr(host, '_load_live', stop)
    kwargs = {'full_path': '/full', 'receipt_path': '/receipt'} if entry == 'live_receipt_block' else {}
    with pytest.raises(RuntimeError, match='capture boundary'):
        getattr(host, entry)('/synthetic-selection', **kwargs)
    assert observed == [expected]
