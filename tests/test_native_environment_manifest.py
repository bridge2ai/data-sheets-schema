"""Offline environment-manifest checks; all distribution metadata is synthetic."""
from email.message import Message
import base64
import hashlib
import json
from pathlib import Path

import pytest

from data_sheets_schema import native_environment_manifest as m
from data_sheets_schema import native_shared_contract as c


class Distribution:
    def __init__(self, root, name='Synthetic.Package', version='1.2.3', record=None):
        self.metadata = Message()
        self.metadata['Name'] = name
        self.metadata['Version'] = version
        self.root = root
        self.files = [Path('synthetic.dist-info/RECORD')]
        target = root / self.files[0]
        target.parent.mkdir(parents=True)
        if record is None:
            payload = b'SYNTHETIC = True\n'
            (root / 'file.py').write_bytes(payload)
            encoded = base64.urlsafe_b64encode(hashlib.sha256(payload).digest()).decode().rstrip('=')
            record = ('file.py,sha256=' + encoded + ',' + str(len(payload)) + '\n').encode()
        target.write_bytes(record + b'synthetic.dist-info/RECORD,,\n')

    def add_file(self, item):
        self.files.append(item)
        with self.locate_file(self.files[0]).open('ab') as stream:
            stream.write((str(item) + ',,\n').encode())

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


def test_generate_verifies_installed_payload_and_names_unverified_entries(installed):
    installed.add_file(Path('cached.pyc'))
    installed.add_file(Path('unverified-notes.txt'))
    value = m.generate()
    assert value['version'] == 1
    row = value['distributions'][0]
    assert row['verified_files'] == {'count': 1, 'bytes': len(b'SYNTHETIC = True\n')}
    assert row['unverified_files'] == [
        {'kind': 'other', 'count': 1, 'paths': ['unverified-notes.txt']},
        {'kind': 'record', 'count': 1, 'paths': ['synthetic.dist-info/RECORD']}]


def test_pyc_creation_change_and_removal_preserve_registered_manifest(installed, tmp_path):
    record = installed.locate_file(installed.files[0])
    digest = base64.urlsafe_b64encode(hashlib.sha256(b'old pyc').digest()).decode().rstrip('=')
    with record.open('a') as stream:
        stream.write('hashed.pyc,sha256=' + digest + ',7\nhashless.pyc,,\n')
    record_bytes = record.read_bytes()
    declaration = m.write(tmp_path / 'manifest.json')
    original = m.verify(declaration)
    assert original['distributions'][0]['verified_files'] == {'count': 1, 'bytes': 17}
    assert original['distributions'][0]['unverified_files'] == [
        {'kind': 'record', 'count': 1, 'paths': ['synthetic.dist-info/RECORD']}]
    targets = [installed.root / name for name in ('hashed.pyc', 'hashless.pyc',
               'loose.pyc', '__pycache__/absent.cpython-313-pytest-7.4.4.pyc')]
    observations = []
    for state, contents in (('created', b'SYNTHETIC cache'), ('changed', b'other cached bytes'),
                            ('removed', None)):
        for target in targets:
            if contents is None:
                target.unlink()
            else:
                target.parent.mkdir(exist_ok=True)
                target.write_bytes(contents)
        assert m.verify(declaration) == original
        assert record.read_bytes() == record_bytes
        observations.append({'state': state, 'pyc_files': sum(path.exists() for path in targets),
                             'manifest_unchanged': True})
    # Cache diagnostics are saved outside the registered manifest/import root.
    (tmp_path / 'bytecode-diagnostics.json').write_text(json.dumps(observations))


@pytest.mark.parametrize('recorded_hash,recorded_size', [('sha256=malformed', 'bad'), ('', '')])
def test_pyc_payload_is_not_read_or_counted(installed, monkeypatch, recorded_hash, recorded_size):
    with installed.locate_file(installed.files[0]).open('a') as stream:
        stream.write('ignored.pyc,' + recorded_hash + ',' + recorded_size + '\n')
    target = installed.root / 'ignored.pyc'
    target.write_bytes(b'SYNTHETIC unreadable cache')
    original_open = m.os.open
    def deny_cache(path, flags, *args, **kwargs):
        if Path(path) == target:
            raise AssertionError('excluded bytecode must not be opened')
        return original_open(path, flags, *args, **kwargs)
    monkeypatch.setattr(m.os, 'open', deny_cache)
    value = m.generate()
    assert value['distributions'][0]['verified_files'] == {'count': 1, 'bytes': 17}
    assert not value['unowned_files']


@pytest.mark.parametrize('inventory', ['unowned', 'bytecode', 'other', 'record'])
def test_closed_manifest_refuses_pyc_entries_in_any_inventory(installed, inventory):
    value = m.generate()
    if inventory == 'unowned':
        value['unowned_files'] = [{'root': str(installed.root), 'path': 'excluded.pyc',
                                  'bytes': 0, 'sha256': hashlib.sha256(b'').hexdigest()}]
    else:
        group = {'kind': inventory, 'count': 1, 'paths': ['excluded.pyc']}
        if inventory == 'record':
            value['distributions'][0]['unverified_files'] = [group]
        else:
            value['distributions'][0]['unverified_files'].insert(0, group)
    with pytest.raises(ValueError, match='pyc bytecode is excluded'):
        m.validate(value)


def test_record_metadata_remains_pinned_when_only_pyc_record_row_changes(installed, tmp_path):
    declaration = m.write(tmp_path / 'manifest.json')
    installed.add_file(Path('new.pyc'))
    with pytest.raises(ValueError, match='stale'):
        m.verify(declaration)


def test_pyo_and_files_under_pyc_named_directory_remain_in_scope(installed):
    installed.add_file(Path('legacy.pyo'))
    directory = installed.root / 'data.pyc'
    directory.mkdir()
    (directory / 'payload.txt').write_bytes(b'SYNTHETIC data')
    value = m.generate()
    assert value['distributions'][0]['unverified_files'][0] == {
        'kind': 'bytecode', 'count': 1, 'paths': ['legacy.pyo']}
    assert [item['path'] for item in value['unowned_files']] == ['data.pyc/payload.txt']


@pytest.mark.parametrize('change', ['same_size_content', 'missing', 'size'])
def test_installed_payload_change_refuses_even_with_unchanged_record(installed, tmp_path, change):
    pin = m.write(tmp_path / 'manifest.json')
    target = installed.root / 'file.py'
    record_before = installed.locate_file(installed.files[0]).read_bytes()
    if change == 'missing':
        target.unlink()
    elif change == 'size':
        target.write_bytes(b'changed size')
    else:
        target.write_bytes(b'SYNTHETIC = None\n')
    assert installed.locate_file(installed.files[0]).read_bytes() == record_before
    with pytest.raises(ValueError, match='payload|unreadable'):
        m.verify(pin)


def test_unreadable_installed_payload_refuses(installed, monkeypatch):
    original = m.os.open
    def denied(path, flags, *args, **kwargs):
        if Path(path) == installed.root / 'file.py':
            raise PermissionError('synthetic unreadable payload')
        return original(path, flags, *args, **kwargs)
    monkeypatch.setattr(m.os, 'open', denied)
    with pytest.raises(ValueError, match='unreadable'):
        m.generate()


@pytest.mark.parametrize('digest', ['sha256=synthetic', 'sha256=', 'sha256=AA==', 'unknown=AAAA',
                                   'sha256=++//', 'shake_128=AAAA'])
def test_malformed_installed_record_hash_refuses(installed, digest):
    record = installed.locate_file(installed.files[0])
    record.write_text('file.py,' + digest + ',17\nsynthetic.dist-info/RECORD,,\n')
    with pytest.raises(ValueError, match='RECORD hash'):
        m.generate()


def test_editable_third_party_refuses(installed):
    direct = installed.locate_file(installed.files[0]).parent / 'direct_url.json'
    direct.write_text(json.dumps({'url': installed.root.as_uri(), 'dir_info': {'editable': True}}))
    with pytest.raises(ValueError, match='editable or development'):
        m.generate()


def test_development_egg_link_refuses(installed):
    (installed.root / 'development.egg-link').write_text(str(installed.root))
    with pytest.raises(ValueError, match='editable or development'):
        m.generate()


def test_own_project_excluded_only_with_exact_namespace(installed, monkeypatch, tmp_path):
    own = Distribution(tmp_path / 'own', name='data_sheets_schema', record=b'')
    monkeypatch.setattr(m.metadata, 'distributions', lambda **kwargs: [own, installed])
    value = m.generate()
    assert [row['name'] for row in value['distributions']] == ['synthetic-package']
    package = m.sys.modules['data_sheets_schema']
    monkeypatch.setattr(package, '__path__', [str(tmp_path)])
    with pytest.raises(ValueError, match='exact pinned project namespace'):
        m.generate()


def test_own_distribution_name_cannot_hide_unrelated_payload(installed, monkeypatch, tmp_path):
    own = Distribution(tmp_path / 'own', name='data_sheets_schema')
    monkeypatch.setattr(m.metadata, 'distributions', lambda **kwargs: [own, installed])
    with pytest.raises(ValueError, match='cannot own unrelated package files'):
        m.generate()


def test_old_manifest_shape_is_historical_only(installed):
    old = m.generate()
    old['version'] = 1
    old['distributions'] = [{key: value for key, value in row.items()
                             if key in {'name', 'version', 'record_sha256'}} for row in old['distributions']]
    with pytest.raises(ValueError, match='environment distribution'):
        m.validate(old)


@pytest.mark.parametrize('change', ['count', 'unknown_kind', 'duplicate', 'version'])
def test_payload_inventory_shape_is_closed(installed, change):
    value = m.generate()
    row = value['distributions'][0]
    if change == 'count':
        row['unverified_files'][0]['count'] += 1
    elif change == 'unknown_kind':
        row['unverified_files'][0]['kind'] = 'not_checked'
    elif change == 'duplicate':
        row['unverified_files'].append(dict(row['unverified_files'][0]))
    else:
        row['verified_files']['extra'] = True
    with pytest.raises(ValueError):
        m.validate(value)


def test_payload_changes_during_census_hold(installed, monkeypatch):
    original = m._require_owned_import_roots
    def changed(paths, captures):
        result = original(paths, captures)
        (installed.root / 'file.py').write_bytes(b'SYNTHETIC = None\n')
        return result
    monkeypatch.setattr(m, '_require_owned_import_roots', changed)
    with pytest.raises(ValueError, match='payload'):
        m.generate()


def test_payload_mutation_during_metadata_recapture_holds(installed, monkeypatch):
    original = m._capture_environment
    def changed(paths, *, verify_payloads=True):
        result = original(paths, verify_payloads=verify_payloads)
        if not verify_payloads:
            (installed.root / 'file.py').write_bytes(b'SYNTHETIC = None\n')
        return result
    monkeypatch.setattr(m, '_capture_environment', changed)
    with pytest.raises(ValueError, match='payload changed during environment census'):
        m.generate()


def test_fresh_payload_hashes_once_per_generate_without_cross_call_cache(installed, monkeypatch):
    original = m._verify_payload
    calls = []
    def observed(*args):
        calls.append(args[0])
        return original(*args)
    monkeypatch.setattr(m, '_verify_payload', observed)
    first = m.generate()
    assert len(calls) == 1
    assert m.generate() == first and len(calls) == 2
    (installed.root / 'file.py').write_bytes(b'SYNTHETIC = None\n')
    with pytest.raises(ValueError, match='payload hash'):
        m.generate()
    assert len(calls) == 3


@pytest.mark.parametrize('same_hash', [False, True])
def test_shared_record_ownership_requires_identical_hash(installed, monkeypatch, tmp_path, same_hash):
    raw = (installed.root / 'file.py').read_bytes()
    algorithm = 'sha256' if same_hash else 'md5'
    digest = base64.urlsafe_b64encode(hashlib.new(algorithm, raw).digest()).decode().rstrip('=')
    record = ('../installed/file.py,' + algorithm + '=' + digest + ',' + str(len(raw)) + '\n').encode()
    second = Distribution(tmp_path / 'second', name='Other.Distribution', record=record)
    monkeypatch.setattr(m.metadata, 'distributions', lambda **kwargs: [installed, second])
    if same_hash:
        assert len(m.generate()['distributions']) == 2
    else:
        with pytest.raises(ValueError, match='ambiguous distribution RECORD ownership'):
            m.generate()


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
        record = installed.locate_file(installed.files[0])
        record.write_bytes(record.read_bytes() + b'changed-synthetic.py,,\n')
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


def test_whole_distribution_metadata_absent_is_explicitly_unowned(installed):
    # Existing unrelated metadata must not mask an importable package whose
    # entire dist-info directory is absent, so discovery never reports it.
    package = installed.root / 'unregistered_package'
    package.mkdir()
    (package / '__init__.py').write_text('SYNTHETIC = True\n')
    value = m.generate()
    assert [row['path'] for row in value['unowned_files']] == ['unregistered_package/__init__.py']


def test_namespace_portion_without_record_entry_is_unowned(installed):
    namespace = installed.root / 'shared_namespace'
    namespace.mkdir()
    good = Path('shared_namespace/registered.py')
    (installed.root / good).write_text('SYNTHETIC = True\n')
    installed.add_file(good)
    assert m.generate()
    (namespace / 'unregistered.py').write_text('SYNTHETIC = False\n')
    assert [row['path'] for row in m.generate()['unowned_files']] == ['shared_namespace/unregistered.py']


def test_repository_root_exempt_foreign_checkout_is_not(installed, monkeypatch, tmp_path):
    monkeypatch.setattr(m.sys, 'path', [str(installed.root), str(m.ROOT), str(m.ROOT / 'src')])
    value = m.generate()
    assert value['excluded_roots'] == [
        {'root': str(m.ROOT), 'reason': 'first_party_source_pins'},
        {'root': str(m.ROOT / 'src'), 'reason': 'first_party_source_pins'}]
    foreign = tmp_path / 'foreign_checkout'
    foreign.mkdir()
    (foreign / 'foreign.py').write_text('SYNTHETIC = True\n')
    monkeypatch.setattr(m.sys, 'path', [str(installed.root), str(foreign)])
    value = m.generate()
    assert value['excluded_roots'] == []
    assert [(row['root'], row['path']) for row in value['unowned_files']] == [(str(foreign), 'foreign.py')]


def test_site_packages_not_exempted_by_stdlib_ancestor(installed, monkeypatch):
    monkeypatch.setattr(m, '_stdlib_roots', lambda: {installed.root.parent})
    (installed.root / 'unowned.py').write_text('SYNTHETIC = True\n')
    monkeypatch.setattr(m.sys, 'path', [str(installed.root.parent), str(installed.root)])
    value = m.generate()
    assert value['excluded_roots'] == [{'root': str(installed.root.parent),
                                       'reason': 'standard_library_interpreter_identity'}]
    assert [row['path'] for row in value['unowned_files']] == ['unowned.py']


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
    assert observed == [str(installed.root), str(installed.root)]


@pytest.mark.parametrize('optimization', ['', '.opt-1', '.opt-2'])
def test_standard_bytecode_cache_uses_owned_source(installed, optimization):
    source = Path('registered.py')
    (installed.root / source).write_text('SYNTHETIC = True\n')
    installed.add_file(source)
    cache = installed.root / '__pycache__'
    cache.mkdir()
    (cache / ('registered.' + m.sys.implementation.cache_tag + optimization + '.pyc')).write_bytes(b'synthetic cache')
    assert m.generate()


def test_nonstandard_rewrite_cache_is_excluded(installed):
    cache = installed.root / '__pycache__'
    cache.mkdir()
    # No source or RECORD entry: this is not a standard Python import cache.
    (cache / ('unregistered.' + m.sys.implementation.cache_tag + '-pytest-7.4.4.pyc')).write_bytes(b'synthetic pytest cache')
    assert m.generate()['unowned_files'] == []


def test_loose_unowned_bytecode_is_excluded(installed):
    (installed.root / 'unregistered.pyc').write_bytes(b'synthetic sourceless bytecode')
    assert m.generate()['unowned_files'] == []


def test_standard_cache_without_source_is_excluded(installed):
    cache = installed.root / '__pycache__'
    cache.mkdir()
    (cache / ('unregistered.' + m.sys.implementation.cache_tag + '.pyc')).write_bytes(b'synthetic cache')
    assert m.generate()['unowned_files'] == []


def test_record_changes_during_census_refuse_registered_pin(installed, tmp_path, monkeypatch):
    pin = m.write(tmp_path / 'manifest.json')
    census = m._require_owned_import_roots
    def change_record(paths, captures):
        snapshots = census(paths, captures)
        record = installed.locate_file(installed.files[0])
        record.write_bytes(record.read_bytes() + b'changed-during-census.py,,\n')
        return snapshots
    monkeypatch.setattr(m, '_require_owned_import_roots', change_record)
    with pytest.raises(ValueError, match='changed during environment census'):
        m.verify(pin)


def test_duplicate_distribution_appears_during_census_refuses(installed, tmp_path, monkeypatch):
    duplicate = Distribution(tmp_path / 'duplicate', name='synthetic-package')
    roster = [installed]
    monkeypatch.setattr(m.metadata, 'distributions', lambda **kwargs: list(roster))
    census = m._require_owned_import_roots
    def change_roster(paths, captures):
        snapshots = census(paths, captures)
        roster.append(duplicate)
        return snapshots
    monkeypatch.setattr(m, '_require_owned_import_roots', change_roster)
    with pytest.raises(ValueError, match='sorted and unique'):
        m.generate()


def test_metadata_changes_during_census_refuse(installed, monkeypatch):
    census = m._require_owned_import_roots
    def change_metadata(paths, captures):
        snapshots = census(paths, captures)
        installed.metadata.replace_header('Version', '2.0.0')
        return snapshots
    monkeypatch.setattr(m, '_require_owned_import_roots', change_metadata)
    with pytest.raises(ValueError, match='changed during environment census'):
        m.generate()


def test_import_paths_change_during_census_refuse(installed, tmp_path, monkeypatch):
    new_root = tmp_path / 'new-import-root'
    new_root.mkdir()
    census = m._require_owned_import_roots
    def change_paths(paths, captures):
        snapshots = census(paths, captures)
        m.sys.path.append(str(new_root))
        return snapshots
    monkeypatch.setattr(m, '_require_owned_import_roots', change_paths)
    with pytest.raises(ValueError, match='changed during environment census'):
        m.generate()


def test_unowned_code_added_to_scanned_directory_refuses(installed, monkeypatch):
    census = m._require_owned_import_roots
    def add_code(paths, captures):
        snapshots = census(paths, captures)
        (installed.root / 'late_unowned.py').write_text('SYNTHETIC = True\n')
        return snapshots
    monkeypatch.setattr(m, '_require_owned_import_roots', add_code)
    with pytest.raises(ValueError, match='directory changed during environment census'):
        m.generate()


def test_ownership_comes_from_hashed_record_not_second_files_read(installed):
    code = Path('unrecorded.py')
    (installed.root / code).write_text('SYNTHETIC = True\n')
    # An inconsistent distribution API must not expand the hashed ownership.
    installed.files.append(code)
    assert [row['path'] for row in m.generate()['unowned_files']] == ['unrecorded.py']


def test_unowned_bootstrap_and_data_are_pinned_without_importing(installed, tmp_path):
    # Canary: code is data only, and .pth execution would fail immediately.
    payloads = {'_virtualenv.py': b'raise RuntimeError("must not import")\n',
                '_virtualenv.pth': b'import must_never_execute_this\n',
                'synthetic.dist-info/extra.txt': b'metadata not named by RECORD',
                'data.bin': b'\x00\xff\x00SYNTHETIC'}
    for relative, raw in payloads.items():
        (installed.root / relative).write_bytes(raw)
    value = m.generate()
    assert value['unowned_files'] == [
        {'root': str(installed.root), 'path': relative, 'bytes': len(raw), 'sha256': c.sha(raw)}
        for relative, raw in sorted(payloads.items())]
    assert value['excluded_roots'] == []
    pin = m.write(tmp_path / 'manifest.json')
    assert m.verify(pin) == value


@pytest.mark.parametrize('change', ['changed', 'new', 'deleted'])
def test_unowned_change_invalidates_manifest(installed, tmp_path, change):
    target = installed.root / 'unowned.txt'
    target.write_bytes(b'SYNTHETIC original')
    pin = m.write(tmp_path / 'manifest.json')
    if change == 'changed':
        target.write_bytes(b'SYNTHETIC modified')
    elif change == 'new':
        (installed.root / 'new.pth').write_bytes(b'new-path\n')
    else:
        target.unlink()
    with pytest.raises(ValueError, match='stale'):
        m.verify(pin)


@pytest.mark.parametrize('optimization', ['', '.opt-1', '.opt-2'])
def test_standard_cache_uses_listed_unowned_source(installed, optimization):
    (installed.root / 'unregistered.py').write_bytes(b'SYNTHETIC = True\n')
    cache = installed.root / '__pycache__'
    cache.mkdir()
    (cache / ('unregistered.' + m.sys.implementation.cache_tag + optimization + '.pyc')).write_bytes(b'cache')
    assert [row['path'] for row in m.generate()['unowned_files']] == ['unregistered.py']


def test_nested_import_roots_have_one_deepest_root_representation(installed, monkeypatch):
    nested = installed.root / 'nested'
    nested.mkdir()
    (nested / 'data.txt').write_bytes(b'SYNTHETIC nested data')
    monkeypatch.setattr(m.sys, 'path', [str(nested), str(installed.root), str(nested)])
    first = m.generate()
    assert first['unowned_files'] == [{'root': str(nested), 'path': 'data.txt',
        'bytes': len(b'SYNTHETIC nested data'), 'sha256': c.sha(b'SYNTHETIC nested data')}]
    monkeypatch.setattr(m.sys, 'path', [str(installed.root), str(nested)])
    assert m.generate() == first


def test_symlink_alias_to_owned_file_is_unowned(installed):
    (installed.root / 'different_import.py').symlink_to(installed.root / 'file.py')
    assert [row['path'] for row in m.generate()['unowned_files']] == ['different_import.py']


def test_symlinked_import_directory_holds(installed, tmp_path):
    target = tmp_path / 'elsewhere'
    target.mkdir()
    (installed.root / 'linked').symlink_to(target, target_is_directory=True)
    with pytest.raises(ValueError, match='symlinked'):
        m.generate()


def test_unowned_payload_mutation_during_recapture_holds(installed, monkeypatch):
    target = installed.root / 'unowned.txt'
    target.write_bytes(b'SYNTHETIC original')
    capture = m._capture_environment
    def changed(paths, **kwargs):
        result = capture(paths, **kwargs)
        if kwargs.get('verify_payloads') is False:
            target.write_bytes(b'SYNTHETIC modified')
        return result
    monkeypatch.setattr(m, '_capture_environment', changed)
    with pytest.raises(ValueError, match='payload changed during environment census'):
        m.generate()


def test_unowned_unreadable_file_holds(installed, monkeypatch):
    target = installed.root / 'unowned.txt'
    target.write_bytes(b'SYNTHETIC original')
    original = m.os.open
    def denied(path, *args, **kwargs):
        if Path(path) == target:
            raise PermissionError('SYNTHETIC unreadable')
        return original(path, *args, **kwargs)
    monkeypatch.setattr(m.os, 'open', denied)
    with pytest.raises(ValueError, match='unreadable'):
        m.generate()


def test_unowned_bytes_have_file_and_aggregate_bounds(installed, monkeypatch):
    (installed.root / 'unowned.dat').write_bytes(b'x' * 30)
    monkeypatch.setattr(m, 'MAX_PAYLOAD_BYTES', 20)
    with pytest.raises(ValueError, match='byte bound'):
        m.generate()
    monkeypatch.setattr(m, 'MAX_PAYLOAD_BYTES', 100)
    monkeypatch.setattr(m, 'MAX_VERIFIED_BYTES', 40)
    with pytest.raises(ValueError, match='aggregate byte bound'):
        m.generate()


@pytest.mark.parametrize('change', ['unknown', 'duplicate', 'relative_root', 'absolute_path',
                                   'parent_path', 'dot_path', 'negative_bytes', 'boolean_bytes',
                                   'unknown_exclusion', 'excluded_root'])
def test_unowned_scope_closed_shape(installed, change):
    (installed.root / 'unowned.txt').write_bytes(b'SYNTHETIC')
    value = m.generate()
    row = value['unowned_files'][0]
    if change == 'unknown':
        row['ignored'] = True
    elif change == 'duplicate':
        value['unowned_files'].append(dict(row))
    elif change == 'relative_root':
        row['root'] = 'relative'
    elif change == 'absolute_path':
        row['path'] = '/absolute'
    elif change == 'parent_path':
        row['path'] = '../outside'
    elif change == 'dot_path':
        row['path'] = '.'
    elif change == 'negative_bytes':
        row['bytes'] = -1
    elif change == 'boolean_bytes':
        row['bytes'] = True
    else:
        value['excluded_roots'] = [{'root': row['root'], 'reason':
            'unknown' if change == 'unknown_exclusion' else 'first_party_source_pins'}]
    with pytest.raises(ValueError):
        m.validate(value)


def test_manifest_inside_inventory_root_self_inclusion_holds(installed):
    # No output exemption is invented for a third-party root.
    with pytest.raises(ValueError, match='stale'):
        m.write(installed.root / 'manifest.json')
