"""Apply implementation-only census path optimization, 2026-11-16.

Inputs: assigned worktree source and ancestor witness. Outputs: modified source
and equivalent syscall spy. Serves the Claude lead launch-cost assignment.
"""
from pathlib import Path

root = Path(__file__).resolve().parents[2]
path = root / 'src/data_sheets_schema/native_environment_manifest.py'
text = path.read_text()
start = text.index('    def resolve(self, path, *, strict=True, pending=None):')
end = text.index('\n\ndef _resolve(path, *, strict=True):', start)
replacement = '''    def resolve(self, path, *, strict=True, pending=None):
        path = Path(path)
        if not path.is_absolute():
            path = Path.cwd() / path
        return Path(self._resolve_string(str(path), strict=strict, pending=pending))

    def _resolve_string(self, key, *, strict=True, pending=None):
        if key in self.directories:
            return self.directories[key]
        if pending is None:
            pending = set()
        if key in pending:
            raise ValueError('symlink loop during environment census: ' + key)
        pending.add(key)
        try:
            parent_key, name = os.path.split(key)
            if parent_key == key:
                physical = key
            else:
                parent = self._resolve_string(parent_key, strict=strict, pending=pending)
                physical = os.path.dirname(parent) if name == '..' else os.path.join(parent, name)
            try:
                info = os.lstat(physical)
            except FileNotFoundError:
                if strict:
                    raise
                return physical
            if stat.S_ISLNK(info.st_mode):
                target = os.readlink(physical)
                identity = (_ancestor_identity(info), target)
                previous = self.links.setdefault(physical, identity)
                if previous != identity:
                    raise ValueError('symlink changed during environment census: ' + physical)
                destination = Path(target)
                if not destination.is_absolute():
                    destination = Path(os.path.dirname(physical)) / destination
                resolved = self._resolve_string(str(destination), strict=strict, pending=pending)
                if os.path.isdir(resolved):
                    self.directories[key] = resolved
                return resolved
            if stat.S_ISDIR(info.st_mode):
                identity = _ancestor_identity(info)
                previous = self.identities.setdefault(physical, identity)
                if previous != identity:
                    raise ValueError('ancestor changed during environment census: ' + physical)
                self.directories[key] = physical
            return physical
        finally:
            pending.remove(key)

    def require_stable(self):
        for path, identity in self.identities.items():
            if _ancestor_identity(os.lstat(path)) != identity:
                raise ValueError('ancestor changed during environment census: ' + path)
        for path, identity in self.links.items():
            if (_ancestor_identity(os.lstat(path)), os.readlink(path)) != identity:
                raise ValueError('symlink changed during environment census: ' + path)
'''
text = text[:start] + replacement + text[end:]
text = text.replace('info = Path(path).lstat()', 'info = os.lstat(path)')
path.write_text(text)
test = root / 'tests/test_native_environment_census.py'
text = test.read_text().replace('original, calls = Path.lstat, []', 'original, calls = m.os.lstat, []')
text = text.replace("monkeypatch.setattr(Path, 'lstat', counted)", "monkeypatch.setattr(m.os, 'lstat', counted)")
test.write_text(text)
print('Updated string-based resolver, lstat dispatch and equivalent syscall witness.')
# Preserve pathlib's exact error policy for this infrequent symlink-target probe.
text = path.read_text().replace('if os.path.isdir(resolved):', 'if Path(resolved).is_dir():')
path.write_text(text)
