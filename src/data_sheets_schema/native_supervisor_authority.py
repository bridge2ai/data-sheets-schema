"""Exact local authority for the neutral supervisor; no live launch authority."""
from __future__ import annotations

from contextlib import contextmanager
import hashlib
import importlib
from pathlib import Path
import subprocess
import sys

from data_sheets_schema import native_attribution_controller as composition
from data_sheets_schema import native_attribution_registration as draft
from data_sheets_schema.resources import git_env

ROOT = composition.ROOT
ADDITIONAL = {
    'prepare_direct': {'path': 'notes/claudecode_direct/prepare_direct.py',
        'sha256': '034c8851f747e0a767a01da8dddb5b6fe3316a6bb7b807fd9cedcbf02218244d'},
    'run_direct_canary': {'path': 'notes/claudecode_direct/run_direct_canary.py',
        'sha256': '0f2e031f30e267b0ecfe2404cc5bf50dd540b4423c3bc66c1b5b77b38f6a1251'},
}


def head():
    return subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT,
        env=git_env(), text=True, timeout=10).strip()


def dependency_identity():
    """Add to, never replace or rewrite, the released controller closure."""
    manifest = composition.controller_sources()
    for name, pin in ADDITIONAL.items():
        if draft._sha((ROOT/pin['path']).read_bytes()) != pin['sha256']:
            raise ValueError(f'additive supervisor dependency differs from released bytes: {name}')
    modules = {**manifest['modules'], **ADDITIONAL}
    for name, pin in modules.items():
        loaded = sys.modules.get(name)
        if loaded is not None and Path(getattr(loaded, '__file__', '')).resolve() != (ROOT/pin['path']).resolve():
            raise ValueError(f'supervisor dependency imported from another origin: {name}')
    for name, loaded in list(sys.modules.items()):
        if name == 'data_sheets_schema' or name.startswith('data_sheets_schema.'):
            source = getattr(loaded, '__file__', None)
            if source and not Path(source).resolve().is_relative_to(ROOT/'src/data_sheets_schema'):
                raise ValueError(f'supervisor package imported from another origin: {name}')
    interpreter = Path(sys.executable)
    return {'source_commit': head(), 'modules': modules,
            'package_sources': draft._code_pins(), 'python': str(interpreter),
            'python_version': sys.version, 'python_sha256': draft._sha(interpreter.read_bytes())}


@contextmanager
def loaded_dependencies(expected):
    """Check bytes AND origins, restoring bare-module and path loader state.

    Imports execute declarations only. No preparer, auth helper, provider
    factory or historical launcher entry point is invoked.
    """
    if draft._encoded(dependency_identity()) != draft._encoded(expected):
        raise ValueError('supervisor dependency identity changed')
    names = set(expected['modules'])
    previous = {name: sys.modules.get(name) for name in names}
    old_path = list(sys.path)
    try:
        controls = composition.load_controls()
        sys.path.insert(0, str(ROOT/'notes/claudecode_direct'))
        extra = {name: importlib.import_module(name) for name in ADDITIONAL}
        if draft._encoded(dependency_identity()) != draft._encoded(expected):
            raise ValueError('loaded supervisor dependency identity changed')
        yield {**controls, **extra}
    finally:
        sys.path[:] = old_path
        for name, module in previous.items():
            if module is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = module


def sha256(raw):
    return hashlib.sha256(raw).hexdigest()
