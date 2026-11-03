"""D59 baseline controls, 2026-10-28: explicit pytest plugin, offline only.

Inputs: git 8dd00263a and the changed production files. Outputs: pytest results
for selected legacy/scanner failures. Overlay baseline reads/copies in memory;
never edit the checkout, protected files or run inputs. Fixture copies still go
to pytest's caller-selected external basetemp. Use with `pytest -p` explicitly.
"""
import ast
import hashlib
from pathlib import Path
import shutil
import subprocess
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
BASE = '8dd00263a'
PATCHES = []


def pytest_configure(config):
    from data_sheets_schema import api_runner as api
    changed = subprocess.check_output(['git', 'diff', '--name-only', BASE, '--',
        'src', 'scripts/build_api_registrations.py'], cwd=ROOT).decode().splitlines()
    overlay = {str((ROOT / name).resolve()): subprocess.check_output(
        ['git', 'show', f'{BASE}:{name}'], cwd=ROOT) for name in changed}
    raw_bytes, raw_text, copyfile = Path.read_bytes, Path.read_text, shutil.copyfile

    def key(path):
        return str(Path(path).resolve())

    def read_bytes(path):
        return overlay[key(path)] if key(path) in overlay else raw_bytes(path)

    def read_text(path, *args, **kwargs):
        if key(path) in overlay:
            encoding = (args[0] if args else kwargs.get('encoding')) or 'utf-8'
            errors = (args[1] if len(args) > 1 else kwargs.get('errors')) or 'strict'
            return overlay[key(path)].decode(encoding, errors)
        return raw_text(path, *args, **kwargs)

    def copy_file(src, dst, *, follow_symlinks=True):
        if key(src) in overlay:
            target = Path(dst).resolve()
            if target == Path(src).resolve() or target.is_relative_to(ROOT):
                raise RuntimeError('baseline control refuses checkout writes')
            target.write_bytes(overlay[key(src)])
            return dst
        return copyfile(src, dst, follow_symlinks=follow_symlinks)

    raw = overlay[str((ROOT / 'src/data_sheets_schema/api_runner.py').resolve())]
    node = next(n for n in ast.parse(raw).body if isinstance(n, ast.FunctionDef) and n.name == 'build_phase')
    namespace = dict(api.__dict__)
    exec(compile(ast.Module(body=[node], type_ignores=[]), str(api.__file__), 'exec'), namespace)
    for mock in (patch.object(Path, 'read_bytes', read_bytes), patch.object(Path, 'read_text', read_text),
                 patch.object(shutil, 'copyfile', copy_file), patch.object(api, 'build_phase', namespace['build_phase'])):
        mock.start()
        PATCHES.append(mock)
    print(f'Baseline control {BASE}: {len(overlay)} changed production files overlaid for reads/copies; '
          f'build_phase restored; API source SHA256 {hashlib.sha256(raw).hexdigest()}.')


def pytest_unconfigure(config):
    for mock in reversed(PATCHES):
        mock.stop()
