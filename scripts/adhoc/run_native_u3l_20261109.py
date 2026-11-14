#!/usr/bin/env python3
"""U3-L private-composition validation, 2026-11-09.

Inputs: immutable U3L_MANIFEST and the physical installed dependency
venv. Outputs: fresh U3-L scratch logs, dependency links and inherited witnesses.
No installers, editable hooks, production changes or packet changes. Invoke
with the dependency Python -S -P -B. Both child entries use this same adapter.
"""
from __future__ import annotations

import csv
import errno
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
SCRATCH = ROOT.parent / 'scratch-native-u1u3'
MANIFEST = Path(os.environ['U3L_MANIFEST'])
if MANIFEST != MANIFEST.resolve(strict=True) or not MANIFEST.is_relative_to(SCRATCH / 'u3l'):
    raise RuntimeError('U3-L manifest must be a physical fresh composition witness')
MANIFEST_RAW = MANIFEST.read_bytes()
MANIFEST_SHA = hashlib.sha256(MANIFEST_RAW).hexdigest()
if os.environ.get('U3L_MANIFEST_SHA', MANIFEST_SHA) != MANIFEST_SHA:
    raise RuntimeError('parent and child U3-L manifest identity differ')
SELECTION = json.loads(MANIFEST_RAW)
SOURCE_HEAD = SELECTION['source_commit']
if (not re.fullmatch('[0-9a-f]{40}', SOURCE_HEAD)
        or SELECTION['kind'] != 'native_u3l_private_composition'
        or SELECTION['status'] != 'composed_not_tested'
        or MANIFEST != SCRATCH / 'u3l' / ('composition-' + SOURCE_HEAD[:12]) / 'composition.json'):
    raise RuntimeError('U3-L composition witness identity differs')
COMPOSITION = Path(SELECTION['worktree'])
COMPOSITION_HEAD = SELECTION['composition_commit']
D127 = {
    'src/data_sheets_schema/shared_generation.py': '2ec18e60316423035f88a2a30263c56385bfbbc587303e84e805a8349ab4f781',
    'src/data_sheets_schema/api_runner.py': '3e8b7e5d3cc13c5ebc508e33f865e9ac484056fde16126118719d740656a4fb7',
    'src/download/prompts/canonical_hashes.yaml': '543e5cd6dc0da0f622ba2cd11a16a90732e9302a1ed0a4700efb61971299d252',
    'tests/utils/run_spec_boundary_contracts.json': 'b1e0cbd14c533a51b88eacb84b974cb93963e18d8f1fb71ae4ed3228f784d1ce',
}
ENV = {'PATH': '/usr/bin:/bin:/usr/sbin:/sbin', 'GIT_NO_LAZY_FETCH': '1',
       'GIT_ALLOW_PROTOCOL': '', 'GIT_CONFIG_GLOBAL': '/dev/null',
       'GIT_CONFIG_SYSTEM': '/dev/null', 'GIT_OPTIONAL_LOCKS': '0'}


def git(root, *args):
    return subprocess.check_output(['/usr/bin/git', '--no-replace-objects',
        '-c', 'core.hooksPath=/dev/null', *args], cwd=root, env=ENV,
        text=True, timeout=30).strip()


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require_composition():
    if (MANIFEST.read_bytes() != MANIFEST_RAW
            or MANIFEST.resolve(strict=True) != MANIFEST
            or COMPOSITION != COMPOSITION.resolve(strict=True)
            or COMPOSITION != SCRATCH / 'u3l' / ('worktree-' + SOURCE_HEAD[:12])
            or git(COMPOSITION, 'rev-parse', 'HEAD') != COMPOSITION_HEAD
            or Path(git(COMPOSITION, 'rev-parse', '--path-format=absolute', '--git-common-dir'))
                != MANIFEST.parent / 'tree/.git'
            or SELECTION['packet_postimages_sha256'] != D127
            or any((COMPOSITION / path).resolve(strict=True) != COMPOSITION / path
                   or sha(COMPOSITION / path) != digest for path, digest in D127.items())):
        raise RuntimeError('frozen U3-L composition, manifest or D127 bytes changed')


require_composition()
spec = importlib.util.spec_from_file_location('u3i_frozen_h',
    COMPOSITION / 'scripts/adhoc/run_native_u3h_20261109.py')
h = importlib.util.module_from_spec(spec)
spec.loader.exec_module(h)
wrapper = h.g.f.r.w
runner = wrapper.runner
runner.LOCK = ROOT.parent / 'plans/native_quiet_window.lock'
if os.path.lexists(runner.LOCK):
    raise RuntimeError('quiet window is active')
wrapper.__file__ = runner.__file__ = str(Path(__file__).resolve())
original_make_venv = runner.make_test_venv
original_parent = runner.parent
original_environment = runner.clean_environment
original_worker = runner.worker

# Preserve the shared dependency export that failed its final census. Future
# cohorts use a fresh local-Git export, with no test-descendant writes allowed.
# This is harness isolation only; the pinned Gitlink and full census stay exact.
wrapper.dependency.SCRATCH = SCRATCH / 'u3l'
wrapper.dependency.DESTINATION = wrapper.dependency.SCRATCH / 'dependencies' / (
    'fairscape-' + wrapper.dependency.PIN)
def scoped_profile(out):
    """Keep retained evidence and all source trees read-only to descendants."""
    if (not out.is_absolute() or out.resolve() != out or out == SCRATCH / 'u3l'
            or not out.is_relative_to(SCRATCH / 'u3l')):
        raise ValueError('physical U3-L run output required')
    inherited = wrapper.sandbox_profile()
    anchor = '(require-not (subpath ' + json.dumps(str(wrapper.SCRATCH)) + '))'
    if inherited.count(anchor) != 1:
        raise RuntimeError('inherited sandbox output boundary changed')
    return inherited.replace(anchor, '(require-not (subpath ' + json.dumps(str(out)) + '))', 1)


def environment(out, interpreter_directory):
    result = original_environment(out, interpreter_directory)
    result['U3L_MANIFEST'] = str(MANIFEST)
    result['U3L_MANIFEST_SHA'] = MANIFEST_SHA
    canary = os.environ.get('U3L_DEPENDENCY_CANARY', '0')
    if canary not in {'0', '1'}:
        raise ValueError('unknown U3-L dependency canary mode')
    result['U3L_DEPENDENCY_CANARY'] = canary
    return result


def worker(args):
    runner.PROFILE = scoped_profile(args.out)
    if os.environ.get('U3L_DEPENDENCY_CANARY') == '1':
        before = wrapper.dependency.dependency_evidence()
        package = wrapper.dependency.DESTINATION / 'tree/fairscape_models'
        link = Path(sys.prefix) / 'lib' / (
            f'python{sys.version_info.major}.{sys.version_info.minor}'
        ) / 'site-packages/fairscape_models'
        if not link.is_symlink() or link.resolve(strict=True) != package:
            raise RuntimeError('dependency canary requires the exact isolated package link')
        probe = link / '.u3l-write-denial-canary'
        if os.path.lexists(probe):
            raise RuntimeError('dependency write-denial canary path already exists')
        try:
            fd = os.open(probe, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        except OSError as exc:
            if exc.errno not in (errno.EPERM, errno.EACCES):
                raise
            denied_errno = exc.errno
        else:
            os.close(fd)
            raise RuntimeError('dependency write denial failed; preserve probe and stop')
        after = wrapper.dependency.dependency_evidence()
        if before != after or os.path.lexists(probe):
            raise RuntimeError('dependency changed during write-denial canary')
        boundary_probes = []
        for target in (SCRATCH / 'u3l/.retained-evidence-write-denial-canary',
                       COMPOSITION / '.u3l-source-write-denial-canary'):
            if os.path.lexists(target):
                raise RuntimeError('boundary canary path already exists')
            try:
                fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            except OSError as exc:
                if exc.errno not in (errno.EPERM, errno.EACCES):
                    raise
                boundary_probes.append(dict(path=str(target), errno=exc.errno))
            else:
                os.close(fd)
                raise RuntimeError('write boundary failed; preserve probe and stop')
            if os.path.lexists(target):
                raise RuntimeError('refused boundary probe persisted')
        runner.save(args.out / 'dependency-write-denied.json', dict(
            status='write_denied_and_exact_dependency_unchanged', errno=denied_errno,
            probe=str(probe), physical_probe=str(package / probe.name),
            dependency=after, boundary_probes=boundary_probes, policy_sha256=hashlib.sha256(
                runner.PROFILE.encode()).hexdigest()))
    return original_worker(args)


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
    require_composition()
    if git(ROOT, 'status', '--porcelain', '--untracked-files=normal'):
        raise RuntimeError('U3-L harness checkout must be committed and clean')
    head = git(ROOT, 'rev-parse', 'HEAD')
    if head != SOURCE_HEAD:
        raise RuntimeError('source HEAD differs from the frozen composition')
    runner.PROFILE = scoped_profile(args.out)
    code = original_parent(args)
    require_composition()
    if git(ROOT, 'rev-parse', 'HEAD') != head or git(ROOT, 'status', '--porcelain', '--untracked-files=normal'):
        raise RuntimeError('harness checkout changed during validation')
    if args.out.is_dir():
        runner.save(args.out / 'u3l-harness.json', dict(commit=head,
            path=str(Path(__file__).resolve()), sha256=sha(Path(__file__)),
            composition=COMPOSITION_HEAD, source_root=str(COMPOSITION),
            manifest=str(MANIFEST), manifest_sha256=MANIFEST_SHA,
            timing_scope='offline scanner validation; no quiet-host claim'))
    return code


runner.make_test_venv = nested_dependency_venv
runner.clean_environment = environment
runner.parent = parent
runner.worker = worker
if __name__ == '__main__':
    if sys.argv[1:] == ['--hydrate-local-dependency']:
        wrapper.dependency.main()
    else:
        runner.time = wrapper.DeadlineClock()
        raise SystemExit(runner.main())
