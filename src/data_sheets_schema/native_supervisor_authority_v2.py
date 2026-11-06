"""Exact local authority for the neutral supervisor; no live launch authority."""
from __future__ import annotations

from contextlib import contextmanager
import hashlib
import importlib
from pathlib import Path
import subprocess
import sys

from data_sheets_schema import native_attribution_controller_v2 as composition
from data_sheets_schema import native_attribution_registration_v2 as draft
from data_sheets_schema.resources import git_env

ROOT = composition.ROOT
ADDITIONAL = {
    'prepare_direct': {'path': 'notes/claudecode_direct/prepare_direct_v2.py',
        'sha256': '7cde3f2a2d20f97f3cd78f6097152ae1e981f0090dd0f52c3f9a3322bdb90de4'},
    'run_direct_canary': {'path': 'notes/claudecode_direct/run_direct_canary.py',
        'sha256': '41c16b195638c2e46b8f7f8d3d1c65db062e6b2115d8e51f603c392fdce92a3a'},
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
    return {'authority_version': 2, 'controller_sources_sha256': composition.SOURCES_SHA256,
            'source_commit': head(), 'modules': modules,
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
        name = 'prepare_direct'
        if name not in sys.modules:
            selected = importlib.util.spec_from_file_location(name, ROOT / ADDITIONAL[name]['path'])
            module = importlib.util.module_from_spec(selected)
            sys.modules[name] = module
            selected.loader.exec_module(module)
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
