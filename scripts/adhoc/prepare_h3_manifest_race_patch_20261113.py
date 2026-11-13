"""Prepare, without applying, the environment census stability patch (2026-11-13).

Inputs: working source and tests. Outputs: scratch copies and unified patch.
Serves the H3 environment-manifest final stability review; no test execution.
"""
from pathlib import Path
import difflib
import hashlib

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT.parent / 'scratch-h3-environment-manifest-20261113'
SOURCE = Path('src/data_sheets_schema/native_environment_manifest.py')
TESTS = Path('tests/test_native_environment_manifest.py')


def replace(text, old, new):
    assert text.count(old) == 1, old[:100]
    return text.replace(old, new)


before_source = (ROOT / SOURCE).read_text()
source = replace(before_source, 'from importlib import metadata\n', 'import csv\nimport io\nfrom importlib import metadata\n')
start = source.index('def _metadata_field(')
end = source.index('\ndef _first_party_roots', start)
source = source[:start] + '''def _metadata_field(message, key):
    values = message.get_all(key, [])
    if len(values) != 1:
        raise ValueError('distribution has missing or ambiguous ' + key + ' metadata')
    return c._text(values[0], 'distribution ' + key)


def _capture_distribution(distribution):
    # Keep Name and Version from one metadata read, and derive ownership only
    # from the exact RECORD bytes whose digest is registered.
    message = distribution.metadata
    name = _name(_metadata_field(message, 'Name'))
    version = _metadata_field(message, 'Version')
    files = distribution.files
    if files is None:
        raise ValueError('distribution is missing installed RECORD metadata: ' + name)
    records = [f for f in files if str(f).endswith('.dist-info/RECORD')]
    if len(records) != 1:
        raise ValueError('distribution has missing or ambiguous installed RECORD: ' + name)
    path = Path(distribution.locate_file(records[0])).resolve(strict=True)
    raw = read_regular(str(path), 'distribution_record', max_bytes=MAX_RECORD_BYTES).captured.raw
    if not raw:
        raise ValueError('distribution has empty installed RECORD: ' + name)
    owned = set()
    for row in csv.reader(io.StringIO(raw.decode('utf-8'), newline=''), strict=True):
        if len(row) != 3 or not row[0] or '\\x00' in row[0]:
            raise ValueError('distribution has malformed installed RECORD: ' + name)
        target = Path(distribution.locate_file(row[0])).resolve(strict=False)
        if target in owned:
            raise ValueError('distribution has duplicate installed RECORD paths: ' + name)
        owned.add(target)
    if path not in owned:
        raise ValueError('distribution RECORD must identify itself: ' + name)
    return {'row': {'name': name, 'version': version, 'record_sha256': c.sha(raw)},
            'record_path': str(path), 'metadata': tuple(message.items()),
            'owned': tuple(sorted(str(item) for item in owned))}


def _capture_environment(paths):
    captures = []
    for distribution in metadata.distributions(path=paths):
        captures.append(_capture_distribution(distribution))
        if len(captures) > MAX_DISTRIBUTIONS:
            raise ValueError('environment exceeds its distribution count bound')
    captures.sort(key=lambda item: (item['row']['name'], item['record_path']))
    names = [item['row']['name'] for item in captures]
    if names != sorted(set(names)):
        raise ValueError('environment distributions must be sorted and unique')
    return captures


def _import_paths():
    return list(dict.fromkeys(str(Path(p or os.getcwd()).resolve(strict=True))
                             for p in sys.path if Path(p or os.getcwd()).exists()))


def _interpreter_identity():
    return {'implementation': sys.implementation.name,
            'version': platform.python_version(), 'build': list(platform.python_build())}


def _directory_identity(path):
    info = path.stat(follow_symlinks=False)
    return (info.st_dev, info.st_ino, info.st_mode, info.st_nlink,
            info.st_size, info.st_mtime_ns, info.st_ctime_ns)


def _require_stable_directories(snapshots):
    for path, expected in snapshots.items():
        if _directory_identity(path) != expected:
            raise ValueError('third-party import directory changed during environment census: ' + str(path))

''' + source[end:]
start = source.index('def _owned_files(')
end = source.index('\ndef _requires_owner', start)
source = source[:start] + '''def _owned_files(captures):
    return {Path(path) for capture in captures for path in capture['owned']}

''' + source[end:]
source = replace(source, 'def _require_owned_import_roots(paths, distributions):', 'def _require_owned_import_roots(paths, captures):')
source = replace(source, '    owned = _owned_files(distributions)\n    visited = set()\n', '    owned = _owned_files(captures)\n    visited = set()\n    snapshots = {}\n')
source = replace(source, '        with os.scandir(directory) as iterator:\n', '        snapshots[directory] = _directory_identity(directory)\n        with os.scandir(directory) as iterator:\n')
source = replace(source, "                raise ValueError('importable code has missing distribution RECORD ownership: ' + str(path))\n", "                raise ValueError('importable code has missing distribution RECORD ownership: ' + str(path))\n    _require_stable_directories(snapshots)\n    return snapshots\n")
start = source.index('    try:\n        rows = []', source.index('def generate():'))
end = source.index('\n\ndef verify', start)
source = source[:start] + '''    try:
        paths = _import_paths()
        identity = _interpreter_identity()
        captures = _capture_environment(paths)
        directories = _require_owned_import_roots(paths, captures)
        # The census may be long. Re-discover the roster, metadata and RECORDs;
        # cached rows from before the census must never establish current state.
        if (_import_paths() != paths or _interpreter_identity() != identity
                or _capture_environment(paths) != captures):
            raise ValueError('interpreter or distribution metadata changed during environment census')
        _require_stable_directories(directories)
        value = {'kind': KIND, 'version': VERSION, 'interpreter': identity,
                 'distributions': [capture['row'] for capture in captures]}
        return validate(value)
    except (OSError, UnicodeError, TypeError, AttributeError, csv.Error) as exc:
        raise ValueError('environment metadata is missing, ambiguous or unreadable') from exc
''' + source[end:]

before_tests = (ROOT / TESTS).read_text()
tests = replace(before_tests, '        target.write_bytes(record)\n', "        target.write_bytes(record + b'synthetic.dist-info/RECORD,,\\n')\n")
tests = replace(tests, '    def locate_file(self, item):\n', '''    def add_file(self, item):
        self.files.append(item)
        with self.locate_file(self.files[0]).open('ab') as stream:
            stream.write((str(item) + ',,\\n').encode())

    def locate_file(self, item):
''')
tests = replace(tests, '    installed.files.append(good)\n', '    installed.add_file(good)\n')
tests = replace(tests, '    installed.files.append(source)\n', '    installed.add_file(source)\n')
tests = replace(tests, '    assert observed == [str(installed.root)]\n', '    assert observed == [str(installed.root), str(installed.root)]\n')
tests = replace(tests, "        installed.locate_file(installed.files[0]).write_bytes(b'changed synthetic RECORD\\n')", "        record = installed.locate_file(installed.files[0])\n        record.write_bytes(record.read_bytes() + b'changed-synthetic.py,,\\n')")
tests += '''

def test_record_changes_during_census_refuse_registered_pin(installed, tmp_path, monkeypatch):
    pin = m.write(tmp_path / 'manifest.json')
    census = m._require_owned_import_roots
    def change_record(paths, captures):
        snapshots = census(paths, captures)
        record = installed.locate_file(installed.files[0])
        record.write_bytes(record.read_bytes() + b'changed-during-census.py,,\\n')
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
        (installed.root / 'late_unowned.py').write_text('SYNTHETIC = True\\n')
        return snapshots
    monkeypatch.setattr(m, '_require_owned_import_roots', add_code)
    with pytest.raises(ValueError, match='directory changed during environment census'):
        m.generate()


def test_ownership_comes_from_hashed_record_not_second_files_read(installed):
    code = Path('unrecorded.py')
    (installed.root / code).write_text('SYNTHETIC = True\\n')
    # An inconsistent distribution API must not expand the hashed ownership.
    installed.files.append(code)
    with pytest.raises(ValueError, match='missing distribution RECORD ownership'):
        m.generate()
'''

OUT.mkdir(parents=True, exist_ok=True)
parts = []
for relative, before, after in ((SOURCE, before_source, source), (TESTS, before_tests, tests)):
    target = OUT / 'race-patch' / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(after)
    parts.extend(difflib.unified_diff(before.splitlines(keepends=True), after.splitlines(keepends=True),
                                    fromfile='a/' + str(relative), tofile='b/' + str(relative)))
patch = OUT / 'manifest-race.patch'
patch.write_text(''.join(parts))
print(str(patch), hashlib.sha256(patch.read_bytes()).hexdigest())
