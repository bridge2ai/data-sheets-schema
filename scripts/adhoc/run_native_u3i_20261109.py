#!/usr/bin/env python3
"""U3-I/U3H-E1 nested-venv harness repair, 2026-11-09.

Inputs: unchanged composition 660b2d884 and the physical installed dependency
venv. Outputs: fresh U3-I scratch logs, dependency links and inherited witnesses.
No installers, editable hooks, production changes or packet changes. Invoke
with the dependency Python -S -P -B. Both child entries use this same adapter.
"""
from __future__ import annotations

import csv
import hashlib
import importlib.util
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
SCRATCH = ROOT.parent / 'scratch-native-u1u3'
COMPOSITION = SCRATCH / 'u3h/composition-e0b964b0e182/tree'
COMPOSITION_HEAD = '660b2d884c3032f0eca61fcfd3ae523fcbbe9614'
ENV = {'PATH': '/usr/bin:/bin:/usr/sbin:/sbin', 'GIT_NO_LAZY_FETCH': '1',
       'GIT_ALLOW_PROTOCOL': '', 'GIT_CONFIG_GLOBAL': '/dev/null',
       'GIT_CONFIG_SYSTEM': '/dev/null', 'GIT_OPTIONAL_LOCKS': '0'}


def git(root, *args):
    return subprocess.check_output(['/usr/bin/git', '--no-replace-objects',
        '-c', 'core.hooksPath=/dev/null', *args], cwd=root, env=ENV,
        text=True, timeout=30).strip()


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


if COMPOSITION != COMPOSITION.resolve(strict=True):
    raise RuntimeError('composition must be a physical path')
if git(COMPOSITION, 'rev-parse', 'HEAD') != COMPOSITION_HEAD:
    raise RuntimeError('frozen composition identity changed')
spec = importlib.util.spec_from_file_location('u3i_frozen_h',
    COMPOSITION / 'scripts/adhoc/run_native_u3h_20261109.py')
h = importlib.util.module_from_spec(spec)
spec.loader.exec_module(h)
wrapper = h.g.f.r.w
runner = wrapper.runner
wrapper.__file__ = runner.__file__ = str(Path(__file__).resolve())
original_make_venv = runner.make_test_venv
original_parent = runner.parent


def excluded(name):
    normalized = name.lower().replace('-', '_')
    return (name.endswith(('.pth', '.egg-link')) or name.startswith('__editable__')
            or normalized.startswith(('data_sheets_schema', 'fairscape_models'))
            or name.split('.', 1)[0] in {'sitecustomize', 'usercustomize'}
            or name in {'__pycache__', 'tests', 'scripts'})


def installed_entries(dependencies):
    """Admit only physical site entries named by installed distribution RECORDs.

    Do not execute .pth files or editable loaders. Record metadata identities;
    these are existing installed dependencies, not freshly installed packages.
    """
    if dependencies != dependencies.resolve(strict=True):
        raise RuntimeError('dependency site must be physical')
    declared = set()
    records = {}
    for record in sorted(dependencies.glob('*.dist-info/RECORD')):
        if excluded(record.parent.name):
            continue
        if not record.resolve(strict=True).is_relative_to(dependencies):
            raise RuntimeError('external distribution RECORD')
        metadata = record.with_name('METADATA')
        if not metadata.resolve(strict=True).is_relative_to(dependencies):
            raise RuntimeError('external distribution METADATA')
        records[record.parent.name] = dict(record_sha256=sha(record),
                                         metadata_sha256=sha(metadata))
        with record.open(newline='', encoding='utf-8') as stream:
            for row in csv.reader(stream):
                path = Path(row[0])
                if not path.is_absolute() and '..' not in path.parts and path.parts:
                    declared.add(path.parts[0])
    admitted = []
    exclusions = {}
    for item in sorted(dependencies.iterdir()):
        if excluded(item.name):
            exclusions[item.name] = 'startup hook, editable marker, project or foreign FAIRSCAPE'
            continue
        if item.name not in declared:
            exclusions[item.name] = 'not named by installed distribution RECORD'
            continue
        resolved = item.resolve(strict=True)
        if not resolved.is_relative_to(dependencies) or not (item.is_file() or item.is_dir()):
            raise RuntimeError('nonphysical installed dependency: ' + item.name)
        admitted.append(item)
    if 'yaml' not in {item.name for item in admitted}:
        raise RuntimeError('installed PyYAML absent from validated dependency entries')
    return admitted, records, exclusions


def nested_dependency_venv(out, dependencies):
    """Expose dependencies to nested fixtures that append this site directory.

    Preserve the inherited controlled bootstrap and origin checks. Only this
    fresh test environment receives links; the dependency venv is read-only.
    """
    python = original_make_venv(out, dependencies)
    site = out / 'venv/lib' / f'python{sys.version_info.major}.{sys.version_info.minor}' / 'site-packages'
    entries, records, exclusions = installed_entries(dependencies)
    links = {}
    evidence = wrapper.dependency.dependency_evidence()
    if not evidence['available']:
        raise RuntimeError('exact pinned FAIRSCAPE dependency unavailable')
    entries.append(Path(evidence['package_root']) / 'fairscape_models')
    for item in entries:
        target = site / item.name
        if os.path.lexists(target):
            raise RuntimeError('fresh test-site collision: ' + item.name)
        target.symlink_to(item, target_is_directory=item.is_dir())
        if target.resolve(strict=True) != item.resolve(strict=True):
            raise RuntimeError('dependency link verification failed')
        links[item.name] = dict(link=str(target), target=str(item.resolve(strict=True)))
    runner.save(out / 'dependency-links.json', dict(links=links,
        installed_distribution_records=records, excluded=exclusions,
        fairscape_dependency=evidence, source_root=str(COMPOSITION),
        source_commit=COMPOSITION_HEAD, harness_sha256=sha(Path(__file__)),
        policy='direct installed dependency entries; no copied startup hooks or editable markers; exact pinned FAIRSCAPE only'))
    return python


def parent(args):
    if git(ROOT, 'status', '--porcelain', '--untracked-files=normal'):
        raise RuntimeError('U3-I harness checkout must be committed and clean')
    head = git(ROOT, 'rev-parse', 'HEAD')
    code = original_parent(args)
    if git(ROOT, 'rev-parse', 'HEAD') != head or git(ROOT, 'status', '--porcelain', '--untracked-files=normal'):
        raise RuntimeError('harness checkout changed during validation')
    if args.out.is_dir():
        runner.save(args.out / 'u3i-harness.json', dict(commit=head,
            path=str(Path(__file__).resolve()), sha256=sha(Path(__file__)),
            composition=COMPOSITION_HEAD, source_root=str(COMPOSITION)))
    return code


runner.make_test_venv = nested_dependency_venv
runner.parent = parent
if __name__ == '__main__':
    runner.time = wrapper.DeadlineClock()
    raise SystemExit(runner.main())
