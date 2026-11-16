"""Adversarial witnesses for the settled census ruling, 2026-11-15."""
from pathlib import Path
from types import ModuleType

import pytest

from data_sheets_schema import native_environment_manifest as m
from tests.test_native_environment_manifest import installed  # noqa: F401
from tests.test_native_environment_modes import pin_document


def test_import_root_snapshot_is_fresh_at_enumeration(tmp_path):
    root = tmp_path / 'imports'
    root.mkdir()
    resolver = m._CensusResolver()
    resolver.status(root)
    # Bytecode is excluded from the inventory but changes directory metadata.
    (root / 'unrelated.pyc').write_bytes(b'ignored')
    token = m._census_resolver.set(resolver)
    try:
        result = m._require_owned_import_roots([str(root)], [])
        assert result['directories'][root] == m._file_identity(root.lstat())
        assert result['unowned_files'] == []
    finally:
        m._census_resolver.reset(token)


def test_census_allows_unrelated_sibling_creation(installed, monkeypatch):
    check = m._require_stable_payloads
    sibling = installed.root.with_name('unrelated-sibling')
    def create_sibling(captures):
        check(captures)
        sibling.mkdir(exist_ok=True)
    monkeypatch.setattr(m, '_require_stable_payloads', create_sibling)
    m.generate()
    assert sibling.is_dir()


def test_census_allows_unrelated_sibling_removal(installed, monkeypatch):
    check = m._require_stable_payloads
    sibling = installed.root.with_name('unrelated-sibling')
    sibling.mkdir()
    def remove_sibling(captures):
        check(captures)
        if sibling.exists():
            sibling.rmdir()
    monkeypatch.setattr(m, '_require_stable_payloads', remove_sibling)
    m.generate()
    assert not sibling.exists()


def test_census_rechecks_reused_ancestor_after_final_payload_check(installed, monkeypatch):
    check = m._require_stable_payloads
    def replace_ancestor(captures):
        check(captures)
        root = installed.root
        root.rename(root.with_name('replaced'))
        root.mkdir()
    monkeypatch.setattr(m, '_require_stable_payloads', replace_ancestor)
    with pytest.raises(ValueError, match='ancestor changed'):
        m.generate()


def test_census_rechecks_symlink_target_after_final_payload_check(installed, tmp_path, monkeypatch):
    alias = tmp_path / 'alias'
    other = tmp_path / 'other'
    other.mkdir()
    alias.symlink_to(installed.root, target_is_directory=True)
    monkeypatch.setattr(m.sys, 'path', [str(alias)])
    check = m._require_stable_payloads
    def retarget(captures):
        check(captures)
        alias.unlink()
        alias.symlink_to(other, target_is_directory=True)
    monkeypatch.setattr(m, '_require_stable_payloads', retarget)
    with pytest.raises(ValueError, match='changed during environment census'):
        m.generate()


def test_resolver_preserves_symlink_parent_semantics(tmp_path):
    target = tmp_path / 'target' / 'nested'
    target.mkdir(parents=True)
    alias = tmp_path / 'alias'
    alias.symlink_to(target, target_is_directory=True)
    path = alias / '..' / 'missing'
    resolver = m._CensusResolver()
    assert resolver.resolve(path, strict=False) == path.resolve(strict=False)
    resolver.require_stable()


def test_resolver_stats_distinct_ancestors_once_then_revalidates(tmp_path, monkeypatch):
    directory = tmp_path / 'parent'
    directory.mkdir()
    files = [directory / name for name in ('a', 'b', 'c')]
    for path in files:
        path.write_bytes(b'payload')
    original, calls = m.os.lstat, []
    def counted(path, *args, **kwargs):
        calls.append(str(path))
        return original(path, *args, **kwargs)
    monkeypatch.setattr(m.os, 'lstat', counted)
    resolver = m._CensusResolver()
    for path in files:
        assert resolver.resolve(path) == path
    assert calls.count(str(directory)) == 1
    resolver.require_stable()
    assert calls.count(str(directory)) == 2


def test_resolver_checks_reused_link_even_when_parent_identity_is_unchanged(tmp_path):
    target = tmp_path / 'target'
    target.mkdir()
    alias = tmp_path / 'alias'
    alias.symlink_to(target, target_is_directory=True)
    resolver = m._CensusResolver()
    assert resolver.resolve(alias) == target
    alias.unlink()
    alias.symlink_to(tmp_path, target_is_directory=True)
    # Isolate the link check from the parent-directory change witness.
    resolver.identities = {}
    with pytest.raises(ValueError, match='symlink changed'):
        resolver.require_stable()


def test_write_hashes_once_and_later_verify_still_reads_inventory(installed, tmp_path, monkeypatch):
    generate, calls = m.generate, []
    def counted():
        calls.append(True)
        return generate()
    monkeypatch.setattr(m, 'generate', counted)
    pin = m.write(tmp_path / 'manifest.json')
    m.verify(pin)
    assert calls == [True]
    (installed.root / 'file.py').write_bytes(b'SYNTHETIC = None\n')
    with pytest.raises(ValueError, match='payload changed'):
        m.verify(pin)
    assert calls == [True]


def test_seed_refuses_metadata_change(installed, tmp_path):
    pin = m.write(tmp_path / 'manifest.json')
    installed.metadata.replace_header('Version', '9.9.9')
    with pytest.raises(ValueError, match='stale'):
        m.verify(pin)


def test_seed_refuses_record_change(installed, tmp_path):
    pin = m.write(tmp_path / 'manifest.json')
    installed.add_file(Path('new-unhashed.txt'))
    with pytest.raises(ValueError, match='stale'):
        m.verify(pin)


def test_seed_refuses_added_unowned_file(installed, tmp_path):
    pin = m.write(tmp_path / 'manifest.json')
    (installed.root / 'new-unowned.py').write_bytes(b'new')
    with pytest.raises(ValueError, match='unowned file inventory'):
        m.verify(pin)


def test_implementation_change_cannot_reuse_seed(installed, tmp_path):
    pin = m.write(tmp_path / 'manifest.json')
    source = tmp_path / 'changed_implementation.py'
    source.write_bytes(Path(m.__file__).read_bytes() + b'\n# Different implementation bytes.\n')
    alias = ModuleType('data_sheets_schema._changed_census_implementation')
    alias.__package__, alias.__file__ = 'data_sheets_schema', str(source)
    exec(compile(source.read_bytes(), str(source), 'exec'), alias.__dict__)
    alias.ROOT = m.ROOT
    calls = []
    def counted():
        calls.append(True)
        return m.generate()
    alias.generate = counted
    assert alias._verification_key(pin) != m._verification_key(pin)
    assert alias.verify(pin) == m.verify(pin)
    assert calls == [True]


def test_loaded_implementation_refuses_changed_source(installed, tmp_path, monkeypatch):
    pin = m.write(tmp_path / 'manifest.json')
    source = tmp_path / 'changed_source.py'
    source.write_bytes(Path(m.__file__).read_bytes() + b'\n# Changed source.\n')
    monkeypatch.setattr(m, '__file__', str(source))
    with pytest.raises(ValueError, match='implementation changed since loading'):
        m.verify(pin)


def test_write_refuses_edit_after_first_generation(installed, tmp_path, monkeypatch):
    generate = m.generate
    def changed():
        value = generate()
        (installed.root / 'file.py').write_bytes(b'SYNTHETIC = None\n')
        return value
    monkeypatch.setattr(m, 'generate', changed)
    with pytest.raises(ValueError, match='changed during manifest generation'):
        m.write(tmp_path / 'manifest.json')


def test_write_refuses_edit_during_publication(installed, tmp_path, monkeypatch):
    fsync = m.os.fsync
    def changed(fd):
        fsync(fd)
        (installed.root / 'file.py').write_bytes(b'SYNTHETIC = None\n')
    monkeypatch.setattr(m.os, 'fsync', changed)
    with pytest.raises(ValueError, match='payload changed'):
        m.write(tmp_path / 'manifest.json')


def test_write_cannot_replace_existing_refusal_for_identical_pin(installed, tmp_path):
    path = tmp_path / 'manifest.json'
    pin = pin_document(path, m.generate())
    payload = installed.root / 'file.py'
    original = payload.read_bytes()
    payload.write_bytes(b'SYNTHETIC = None\n')
    with pytest.raises(ValueError, match='payload hash'):
        m.verify(pin)
    payload.write_bytes(original)
    path.unlink()
    with pytest.raises(ValueError, match='payload hash'):
        m.write(path)


def test_write_cannot_refresh_existing_full_fingerprints(installed, tmp_path):
    path = tmp_path / 'manifest.json'
    m.write(path)
    payload = installed.root / 'file.py'
    original = payload.read_bytes()
    payload.write_bytes(original)
    path.unlink()
    with pytest.raises(ValueError, match='payload changed since process full verification'):
        m.write(path)


def test_census_resolver_is_discarded_on_success_and_failure(installed, monkeypatch):
    assert m._census_resolver.get() is None
    m.generate()
    assert m._census_resolver.get() is None
    (installed.root / 'file.py').write_bytes(b'SYNTHETIC = None\n')
    with pytest.raises(ValueError):
        m.generate()
    assert m._census_resolver.get() is None


def test_light_census_status_budget_keeps_final_second_look(installed, monkeypatch):
    from collections import Counter
    paths = [installed.root / ('payload-' + str(index)) for index in range(200)]
    for path in paths:
        path.write_bytes(b'payload')
        installed.add_file(Path(path.name))
    value = m.generate()
    calls = Counter()
    original_lstat, original_stat = m.os.lstat, m.os.stat
    def counted_lstat(path, *args, **kwargs):
        calls[str(path)] += 1
        return original_lstat(path, *args, **kwargs)
    def counted_stat(path, *args, **kwargs):
        calls[str(path)] += 1
        return original_stat(path, *args, **kwargs)
    with monkeypatch.context() as patch:
        patch.setattr(m.os, 'lstat', counted_lstat)
        patch.setattr(m.os, 'stat', counted_stat)
        m._light_live(value)
    # One observation shared by resolution/type/ownership, one final recheck.
    assert all(calls[str(path)] == 2 for path in paths)
    assert sum(calls.values()) <= 2 * len(paths) + 100


def test_light_census_does_not_reuse_status_between_calls(installed):
    value = m.generate()
    m._light_live(value)
    (installed.root / 'file.py').write_bytes(b'changed size')
    with pytest.raises(ValueError, match='size or type'):
        m._light_live(value)


def test_light_census_final_payload_second_look_is_fresh(installed, monkeypatch):
    value = m.generate()
    check = m._require_stable_payloads
    def mutate(captures):
        check(captures)
        (installed.root / 'file.py').write_bytes(b'SYNTHETIC = None\n')
    monkeypatch.setattr(m, '_require_stable_payloads', mutate)
    with pytest.raises(ValueError, match='changed during environment census'):
        m._light_live(value)
