"""Offline environment-manifest checks; all distribution metadata is synthetic."""
from email.message import Message
from pathlib import Path

import pytest

from data_sheets_schema import native_environment_manifest as m
from data_sheets_schema import native_shared_contract as c


class Distribution:
    def __init__(self, root, name='Synthetic.Package', version='1.2.3', record=b'file.py,sha256=synthetic,10\n'):
        self.metadata = Message()
        self.metadata['Name'] = name
        self.metadata['Version'] = version
        self.root = root
        self.files = [Path('synthetic.dist-info/RECORD')]
        target = root / self.files[0]
        target.parent.mkdir(parents=True)
        target.write_bytes(record)

    def locate_file(self, item):
        return self.root / item


@pytest.fixture
def installed(tmp_path, monkeypatch):
    stdlib_roots = m._stdlib_roots()
    monkeypatch.setattr(m, '_stdlib_roots', lambda: stdlib_roots)
    distribution = Distribution(tmp_path / 'installed')
    monkeypatch.setattr(m.metadata, 'distributions', lambda **kwargs: [distribution])
    monkeypatch.setattr(m.sys, 'path', [str(distribution.root)])
    return distribution


def test_generate_has_sorted_semantic_inventory(installed, monkeypatch, tmp_path):
    second = Distribution(tmp_path / 'second', name='AAA_package')
    monkeypatch.setattr(m.metadata, 'distributions', lambda **kwargs: [installed, second])
    doc = m.generate()
    assert [row['name'] for row in doc['distributions']] == ['aaa-package', 'synthetic-package']
    assert doc['distributions'][1]['record_sha256'] == c.sha(installed.locate_file(installed.files[0]).read_bytes())
    assert set(doc['interpreter']) == {'implementation', 'version', 'build'}
    assert str(tmp_path) not in c.canonical(doc).decode()


def test_write_once_and_verify_exact_bytes(installed, tmp_path):
    path = tmp_path / 'environment.json'
    pin = m.write(path)
    assert path.stat().st_size == pin['bytes'] > 0
    assert pin['sha256'] == c.sha(path.read_bytes())
    assert m.verify(pin) == m.generate()
    with pytest.raises(FileExistsError):
        m.write(path)


@pytest.mark.parametrize('field', ['Name', 'Version'])
def test_missing_or_ambiguous_metadata_refuses(installed, field):
    old = installed.metadata[field]
    del installed.metadata[field]
    with pytest.raises(ValueError, match='missing or ambiguous'):
        m.generate()
    installed.metadata[field] = old
    installed.metadata[field] = old
    with pytest.raises(ValueError, match='missing or ambiguous'):
        m.generate()


@pytest.mark.parametrize('files', [None, [], [Path('a.dist-info/RECORD'), Path('b.dist-info/RECORD')]])
def test_missing_or_ambiguous_record_refuses(installed, files):
    installed.files = files
    with pytest.raises(ValueError, match='RECORD'):
        m.generate()


def test_unreadable_record_refuses(installed, monkeypatch):
    def denied(*args, **kwargs):
        raise PermissionError('synthetic denied RECORD')
    monkeypatch.setattr(m, 'read_regular', denied)
    with pytest.raises(ValueError, match='unreadable'):
        m.generate()


def test_duplicate_normalized_name_refuses(installed, monkeypatch, tmp_path):
    duplicate = Distribution(tmp_path / 'duplicate', name='synthetic_package')
    monkeypatch.setattr(m.metadata, 'distributions', lambda **kwargs: [installed, duplicate])
    with pytest.raises(ValueError, match='sorted and unique'):
        m.generate()


def test_missing_manifest_refuses(installed, tmp_path):
    with pytest.raises(FileNotFoundError):
        m.verify({'path': str(tmp_path / 'absent.json'), 'bytes': 1, 'sha256': '0' * 64})


def test_altered_manifest_refuses(installed, tmp_path):
    pin = m.write(tmp_path / 'manifest.json')
    path = Path(pin['path'])
    path.chmod(0o600)
    path.write_bytes(path.read_bytes() + b' ')
    with pytest.raises(ValueError, match='registered pin'):
        m.verify(pin)


def test_rehashed_altered_manifest_still_refuses(installed, tmp_path):
    pin = m.write(tmp_path / 'manifest.json')
    value = m.generate()
    value['distributions'][0]['version'] = 'forged-synthetic-version'
    raw = c.canonical(value)
    path = Path(pin['path'])
    path.chmod(0o600)
    path.write_bytes(raw)
    replacement = {'path': str(path), 'bytes': len(raw), 'sha256': c.sha(raw)}
    with pytest.raises(ValueError, match='stale'):
        m.verify(replacement)


@pytest.mark.parametrize('change', ['record', 'version', 'interpreter'])
def test_stale_manifest_refuses(installed, tmp_path, monkeypatch, change):
    pin = m.write(tmp_path / 'manifest.json')
    if change == 'record':
        installed.locate_file(installed.files[0]).write_bytes(b'changed synthetic RECORD\n')
    elif change == 'version':
        installed.metadata.replace_header('Version', '2.0.0')
    else:
        monkeypatch.setattr(m.platform, 'python_version', lambda: '0.0.0-synthetic')
    with pytest.raises(ValueError, match='stale'):
        m.verify(pin)


def test_closed_fields_and_exact_version(installed):
    for change in ({'extra': True}, {'version': True}, {'kind': 'other'}):
        doc = {**m.generate(), **change}
        with pytest.raises(ValueError):
            m.validate(doc)


def test_empty_inventory_refuses(monkeypatch):
    monkeypatch.setattr(m.metadata, 'distributions', lambda **kwargs: [])
    monkeypatch.setattr(m.sys, 'path', [])
    with pytest.raises(ValueError, match='nonempty'):
        m.generate()


def test_whole_distribution_metadata_absent_holds(installed):
    # Existing unrelated metadata must not mask an importable package whose
    # entire dist-info directory is absent, so discovery never reports it.
    package = installed.root / 'unregistered_package'
    package.mkdir()
    (package / '__init__.py').write_text('SYNTHETIC = True\n')
    with pytest.raises(ValueError, match='missing distribution RECORD ownership'):
        m.generate()


def test_namespace_portion_needs_its_own_record_entry(installed):
    namespace = installed.root / 'shared_namespace'
    namespace.mkdir()
    good = Path('shared_namespace/registered.py')
    (installed.root / good).write_text('SYNTHETIC = True\n')
    installed.files.append(good)
    assert m.generate()
    (namespace / 'unregistered.py').write_text('SYNTHETIC = False\n')
    with pytest.raises(ValueError, match='missing distribution RECORD ownership'):
        m.generate()


def test_repository_root_exempt_foreign_checkout_is_not(installed, monkeypatch, tmp_path):
    monkeypatch.setattr(m.sys, 'path', [str(installed.root), str(m.ROOT), str(m.ROOT / 'src')])
    assert m.generate()
    foreign = tmp_path / 'foreign_checkout'
    foreign.mkdir()
    (foreign / 'foreign.py').write_text('SYNTHETIC = True\n')
    monkeypatch.setattr(m.sys, 'path', [str(installed.root), str(foreign)])
    with pytest.raises(ValueError, match='missing distribution RECORD ownership'):
        m.generate()


def test_site_packages_not_exempted_by_stdlib_ancestor(installed, monkeypatch):
    monkeypatch.setattr(m, '_stdlib_roots', lambda: {installed.root.parent})
    (installed.root / 'unowned.py').write_text('SYNTHETIC = True\n')
    with pytest.raises(ValueError, match='missing distribution RECORD ownership'):
        m.generate()


def test_archive_import_root_holds(installed, monkeypatch, tmp_path):
    archive = tmp_path / 'foreign.zip'
    archive.write_bytes(b'SYNTHETIC ARCHIVE')
    monkeypatch.setattr(m.sys, 'path', [str(installed.root), str(archive)])
    with pytest.raises(ValueError, match='unsupported archive'):
        m.generate()


def test_duplicate_and_empty_import_path_entries(installed, monkeypatch):
    monkeypatch.chdir(installed.root)
    monkeypatch.setattr(m.sys, 'path', ['', str(installed.root), str(installed.root / '.')])
    observed = []
    def discover(*, path):
        observed.extend(path)
        return [installed]
    monkeypatch.setattr(m.metadata, 'distributions', discover)
    assert m.generate()
    assert observed == [str(installed.root)]
