"""Apply the settled census ruling after baseline measurement, 2026-11-15.

Input: branch manifest source. Output: scoped resolver and generation memo seed.
Serves the Claude lead public-stale assignment; no external calls.
"""
from pathlib import Path
import hashlib
import sys


path = Path('src/data_sheets_schema/native_environment_manifest.py')
source = path.read_text()
assert hashlib.sha256(source.encode()).hexdigest() == '790040b275d4d67aed40a6805835bb688030ec0ef3e7e004984aadcf4a2c10b7'
resolver = '''
_census_resolver = ContextVar('environment_census_resolver', default=None)
_generation_capture = ContextVar('environment_generation_capture', default=None)
_IMPLEMENTATION_SHA256 = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()


class _CensusResolver:
    """Reuse directory resolution only within one checked live census."""

    def __init__(self):
        self.directories = {}
        self.identities = {}
        self.links = {}

    def resolve(self, path, *, strict=True, pending=None):
        path = Path(path)
        if not path.is_absolute():
            path = Path.cwd() / path
        key = str(path)
        if key in self.directories:
            return self.directories[key]
        if pending is None:
            pending = set()
        if key in pending:
            raise ValueError('symlink loop during environment census: ' + key)
        pending.add(key)
        try:
            if path.parent == path:
                physical = path
            else:
                parent = self.resolve(path.parent, strict=strict, pending=pending)
                physical = parent.parent if path.name == '..' else parent / path.name
            try:
                info = physical.lstat()
            except FileNotFoundError:
                if strict:
                    raise
                return physical
            if stat.S_ISLNK(info.st_mode):
                target = os.readlink(physical)
                identity = (_file_identity(info), target)
                previous = self.links.setdefault(str(physical), identity)
                if previous != identity:
                    raise ValueError('symlink changed during environment census: ' + str(physical))
                destination = Path(target)
                if not destination.is_absolute():
                    destination = physical.parent / destination
                resolved = self.resolve(destination, strict=strict, pending=pending)
                if resolved.is_dir():
                    self.directories[key] = resolved
                return resolved
            if stat.S_ISDIR(info.st_mode):
                identity = _file_identity(info)
                previous = self.identities.setdefault(str(physical), identity)
                if previous != identity:
                    raise ValueError('ancestor changed during environment census: ' + str(physical))
                self.directories[key] = physical
            return physical
        finally:
            pending.remove(key)

    def require_stable(self):
        for path, identity in self.identities.items():
            if _file_identity(Path(path).lstat()) != identity:
                raise ValueError('ancestor changed during environment census: ' + path)
        for path, identity in self.links.items():
            if (_file_identity(Path(path).lstat()), os.readlink(path)) != identity:
                raise ValueError('symlink changed during environment census: ' + path)


def _resolve(path, *, strict=True):
    resolver = _census_resolver.get()
    if resolver is None:
        return Path(path).resolve(strict=strict)
    return resolver.resolve(path, strict=strict)


def _run_census(operation, *args):
    resolver = _CensusResolver()
    token = _census_resolver.set(resolver)
    try:
        result = operation(*args)
        resolver.require_stable()
        return result
    except OSError as exc:
        raise ValueError('environment census path disappeared or became unreadable') from exc
    finally:
        _census_resolver.reset(token)


def _fingerprints(captures, census):
    fingerprints = {path: pin for row in captures for path, pin in row['stat_identities'].items()}
    for row in census['payloads']:
        fingerprints[row['path']] = row['alias_identity']
        fingerprints[row['physical']] = row['identity']
    for capture in captures:
        for row in capture['payloads']:
            fingerprints[row['path']] = row['alias_identity']
            fingerprints[row['physical']] = row['identity']
    return fingerprints

'''
source = source.replace('\ndef _process_state():', '\n' + resolver + '\ndef _process_state():', 1)
replacements = {
    'original.resolve(strict=True)': '_resolve(original, strict=True)',
    'path.resolve(strict=True)': '_resolve(path, strict=True)',
    'Path(distribution.locate_file(records[0])).resolve(strict=True)': '_resolve(distribution.locate_file(records[0]), strict=True)',
    'Path(distribution.locate_file(row[0])).resolve(strict=False)': '_resolve(distribution.locate_file(row[0]), strict=False)',
    'Path(p or os.getcwd()).resolve(strict=True)': '_resolve(p or os.getcwd(), strict=True)',
}
for old, new in replacements.items():
    source = source.replace(old, new)
source = source.replace('def generate():', 'def generate():\n    return _run_census(_generate)\n\n\ndef _generate():', 1)
source = source.replace('        return validate(value)\n', '''        result = validate(value)
        holder = _generation_capture.get()
        if holder is not None:
            holder.append(tuple(sorted(_fingerprints(captures, census).items())))
        return result
''', 1)
source = source.replace('def _light_live(value):', 'def _light_live(value):\n    return _run_census(_light_census, value)\n\n\ndef _light_census(value):', 1)
old = '''        fingerprints = {path: pin for row in captures for path, pin in row['stat_identities'].items()}
        for row in census['payloads']:
            fingerprints[row['path']] = row['alias_identity']
            fingerprints[row['physical']] = row['identity']'''
assert old in source
source = source.replace(old, '        fingerprints = _fingerprints(captures, census)', 1)
source = source.replace("    return (str(ROOT), tuple(sorted(pin.items())),", "    return (_IMPLEMENTATION_SHA256, str(ROOT), tuple(sorted(pin.items())),", 1)
source = source.replace('    executable = Path(sys.executable).resolve(strict=True)\n', '''    implementation = read_regular(str(Path(__file__).resolve(strict=True)),
        'environment_manifest_implementation', max_bytes=MAX_BYTES).captured
    if implementation.pin.sha256 != _IMPLEMENTATION_SHA256:
        raise ValueError('environment manifest implementation changed since loading')
    executable = Path(sys.executable).resolve(strict=True)
''', 1)
source = source.replace('    raw = c.canonical(generate())\n', '''    fingerprints = []
    token = _generation_capture.set(fingerprints)
    try:
        value = generate()
    finally:
        _generation_capture.reset(token)
    raw = c.canonical(value)
    if len(fingerprints) != 1 or _light_live(value) != fingerprints[0]:
        raise ValueError('installed payload changed during manifest generation')
''', 1)
source = source.replace("    verify(pin, mode='full')\n    return pin", '''    state = _process_state()
    with state['lock']:
        key = _verification_key(pin)
        if len(state['full']) >= 64 and key not in state['full']:
            raise ValueError('process environment verification pin bound exceeded')
        if key not in state['full']:
            state['full'][key] = (None, fingerprints[0])
        # Re-read the persisted pin and recheck the live census after publication.
        verify(pin, mode='full')
    return pin''', 1)
output = Path(sys.argv[1]) if len(sys.argv) > 1 else path
output.parent.mkdir(parents=True, exist_ok=True)
output.write_text(source)
