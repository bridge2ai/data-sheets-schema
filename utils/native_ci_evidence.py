"""Opt-in, post-teardown retention of two explicitly synthetic native cases.

This plugin does not select tests, run a native/provider operation, change their
limits or alter pytest outcomes. It never follows a path declared inside a case.
"""
from contextlib import contextmanager
import hashlib
import io
import json
import os
from pathlib import Path
import re
import stat
import tarfile

import pytest

from utils.native_shared_acceptance import git


ROOT = Path(__file__).resolve().parents[1]
CASES = {
    'tests/test_native_shared_execution.py::test_actual_public_correction_three_workers_and_saved_completion': 'native26',
    'tests/test_native_shared_execution_variant.py::test_actual_public_merged_omissions_and_all_chunk_statuses': 'native26-omissions',
}
MAX_CASE_BYTES = 512 * 1024 * 1024
MAX_CASE_ENTRIES = 10000
SOURCE_FILES = (
    'utils/native_ci_evidence.py', 'utils/native_shared_acceptance.py',
    'tests/test_native_shared_execution.py', 'tests/test_native_shared_execution_variant.py',
    'tests/native_shared_fixture.py', 'tests/native_shared_omission_fixture.py',
    'tests/fixtures/native_shared_execution/fake_cli.py', '.github/workflows/main.yaml',
)
LIMITS = {'attempt_seconds': 900, 'helper_seconds': 180, 'base_fixture_seconds': 120,
          'basis': 'Selected test/peer source declarations, not measured operation durations.'}
KNOWN_ARTIFACTS = (
    'actual-result.json', 'authority/runtime.json', 'authority/runtime-execution.json',
    'authority/selection.json', 'authority/composition-execution.json',
    'native-attempt/registration.json', 'native-attempt/started.json',
    'native-attempt/transcript.jsonl', 'native-attempt/control.jsonl',
    'native-attempt/stderr.txt', 'fresh-attempt/stages/journal.json',
)


def pin(raw):
    return {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def save_new(path, value):
    raw = (json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + '\n').encode()
    with path.open('xb') as handle:
        handle.write(raw)


def source_identity():
    return {'head': git(ROOT, 'rev-parse', 'HEAD').strip(),
            'tree': git(ROOT, 'rev-parse', 'HEAD^{tree}').strip(),
            'files': {name: pin((ROOT / name).read_bytes()) for name in SOURCE_FILES},
            'scope': 'Checkout Git identity and selected working source bytes; not a full imported closure.'}


def _identity(info):
    return (info.st_dev, info.st_ino, info.st_mode, info.st_size,
            info.st_mtime_ns, info.st_ctime_ns)


@contextmanager
def directory(path):
    """Open every absolute directory component without following a symlink."""
    absolute = Path(os.path.abspath(path))
    descriptor = os.open(absolute.anchor, os.O_RDONLY | os.O_DIRECTORY)
    try:
        for part in absolute.parts[1:]:
            child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                            dir_fd=descriptor)
            os.close(descriptor)
            descriptor = child
        yield descriptor
    finally:
        os.close(descriptor)


def snapshot(case, archive=None):
    """Hash mode/bytes; optionally archive those exact bytes via held directory FDs."""
    entries, total = {}, 0
    with directory(case) as descriptor:
        root_info = os.fstat(descriptor)
        entries['.'] = {'type': 'directory', 'mode': stat.S_IMODE(root_info.st_mode)}
        if archive is not None:
            root_member = tarfile.TarInfo('case')
            root_member.type = tarfile.DIRTYPE
            root_member.mode, root_member.mtime = entries['.']['mode'], root_info.st_mtime
            archive.addfile(root_member)
        def visit(parent, prefix):
            nonlocal total
            with os.scandir(parent) as scan:
                names = sorted(entry.name for entry in scan)
            for name in names:
                relative = str(Path(prefix) / name)
                if len(entries) >= MAX_CASE_ENTRIES:
                    raise ValueError('synthetic case entry bound exceeded')
                info = os.stat(name, dir_fd=parent, follow_symlinks=False)
                row = {'mode': stat.S_IMODE(info.st_mode)}
                member = tarfile.TarInfo('case/' + relative)
                member.mode, member.mtime = row['mode'], info.st_mtime
                if stat.S_ISLNK(info.st_mode):
                    target = os.readlink(name, dir_fd=parent)
                    row.update(type='symlink', target=target)
                    member.type, member.linkname = tarfile.SYMTYPE, target
                    if archive is not None:
                        archive.addfile(member)
                elif stat.S_ISDIR(info.st_mode):
                    child = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent)
                    try:
                        if _identity(os.fstat(child)) != _identity(info):
                            raise ValueError('case directory changed during capture')
                        row['type'] = 'directory'
                        entries[relative] = row
                        member.type = tarfile.DIRTYPE
                        if archive is not None:
                            archive.addfile(member)
                        visit(child, relative)
                    finally:
                        os.close(child)
                elif stat.S_ISREG(info.st_mode):
                    # Do not read special files or follow a replaced leaf link.
                    fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
                    with os.fdopen(fd, 'rb') as handle:
                        opened = os.fstat(handle.fileno())
                        if not stat.S_ISREG(opened.st_mode) or _identity(opened) != _identity(info):
                            raise ValueError('case file changed before capture')
                        if total + info.st_size > MAX_CASE_BYTES:
                            raise ValueError('synthetic case byte bound exceeded')
                        raw = handle.read(MAX_CASE_BYTES - total + 1)
                        if len(raw) != info.st_size or _identity(os.fstat(handle.fileno())) != _identity(info):
                            raise ValueError('case file changed during capture')
                    total += len(raw)
                    row.update(type='file', **pin(raw))
                    member.size = len(raw)
                    if archive is not None:
                        archive.addfile(member, io.BytesIO(raw))
                else:
                    raise ValueError('nonregular synthetic case entry')
                if _identity(os.stat(name, dir_fd=parent, follow_symlinks=False)) != _identity(info):
                    raise ValueError('case entry changed during capture')
                entries[relative] = row
        visit(descriptor, '')
    return entries


def capture_case(tmp_path, destination, *, node_id, worker, source, outcome):
    """Publish a new diagnostic only; errors never replace an existing artifact."""
    if node_id not in CASES:
        raise ValueError('only the two named synthetic cases may be retained')
    destination = Path(destination)
    case = None if tmp_path is None else Path(tmp_path) / CASES[node_id]
    if case is not None:
        a, b = destination.resolve(), case.resolve()
        if a == b or a.is_relative_to(b) or b.is_relative_to(a):
            raise ValueError('diagnostic output must be separate from the case')
    destination.mkdir(exist_ok=False)
    manifest = {'format': 'native_ci_synthetic_case_v1', 'node_id': node_id,
                'worker': worker, 'source': source, 'declared_limits': dict(LIMITS),
                'test_outcome': outcome, 'original_case': None if case is None else str(case),
                'status': 'capture_failed', 'before': None, 'archived': None, 'after': None,
                'unchanged': False, 'archive': None,
                'availability': {name: 'not_inspected' for name in KNOWN_ARTIFACTS},
                'case_completeness': 'not_assessed',
                'scientific_acceptance': 'not_assessed',
                'scope': 'Synthetic test files only; retention does not establish acceptance.'}
    try:
        if case is None or not os.path.lexists(case):
            manifest['status'] = 'case_unavailable'
            manifest['availability'] = {name: 'case_unavailable' for name in KNOWN_ARTIFACTS}
        else:
            manifest['before'] = snapshot(case)
            manifest['availability'] = {
                name: manifest['before'].get(name, {}).get('type', 'absent') for name in KNOWN_ARTIFACTS}
            with tarfile.open(destination / 'case.tar.gz', 'x:gz', dereference=False) as archive:
                manifest['archived'] = snapshot(case, archive)
            manifest['after'] = snapshot(case)
            manifest['unchanged'] = manifest['before'] == manifest['archived'] == manifest['after']
            manifest['archive'] = pin((destination / 'case.tar.gz').read_bytes())
            manifest['status'] = 'retained' if manifest['unchanged'] else 'capture_changed'
    except Exception as exc:
        manifest['error'] = {'type': type(exc).__name__, 'message': str(exc)}
    save_new(destination / 'manifest.json', manifest)
    return manifest


def pytest_addoption(parser):
    parser.addoption('--native-ci-evidence-root', default=None,
                     help='Fresh external directory for two synthetic native cases only')


def pytest_configure(config):
    selected = config.getoption('--native-ci-evidence-root')
    if selected is None:
        return
    root = Path(selected).resolve()
    if root == ROOT or root.is_relative_to(ROOT) or ROOT.is_relative_to(root):
        raise pytest.UsageError('native CI evidence must be outside the checkout')
    worker = getattr(config, 'workerinput', {}).get('workerid', 'controller')
    if worker != 'controller' and not re.fullmatch(r'gw[0-9]+', worker):
        raise pytest.UsageError('unexpected native CI evidence worker identity')
    if worker == 'controller':
        root.mkdir(exist_ok=False)
        save_new(root / 'selection.json', {'format': 'native_ci_selection_v1', 'cases': CASES,
            'source': source_identity(), 'scope': 'Only these nodes if collected; no tests selected by this plugin.'})
    worker_root = root / worker
    worker_root.mkdir(exist_ok=False)
    config._native_ci_evidence = {'root': root, 'worker_root': worker_root,
                                 'worker': worker, 'source': source_identity(), 'events': []}


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    report = outcome.get_result()
    state = getattr(item.config, '_native_ci_evidence', None)
    if state is None or item.nodeid not in CASES:
        return
    observed = getattr(item, '_native_ci_outcome', {})
    observed[report.when] = {'outcome': report.outcome, 'duration_seconds': report.duration}
    item._native_ci_outcome = observed
    if report.when != 'teardown':
        # Keep the fixture-owned identity even if teardown clears funcargs.
        item._native_ci_tmp_path = (getattr(item, 'funcargs', None) or {}).get('tmp_path')
        return
    relative = hashlib.sha256(item.nodeid.encode()).hexdigest()
    destination = state['worker_root'] / relative
    event = {'node_id': item.nodeid, 'directory': relative, 'test_outcome': observed}
    try:
        captured = capture_case(getattr(item, '_native_ci_tmp_path', None), destination,
            node_id=item.nodeid, worker=state['worker'], source=state['source'], outcome=observed)
        event['capture_status'] = captured['status']
    except Exception as exc:
        event.update(capture_status='capture_failed', error={'type': type(exc).__name__, 'message': str(exc)})
    state['events'].append(event)


def pytest_sessionfinish(session, exitstatus):
    state = getattr(session.config, '_native_ci_evidence', None)
    if state is None:
        return
    # Preserve pytest's own failure/skip/exit information; capture errors are
    # separate diagnostics, never a replacement success or exception.
    try:
        save_new(state['worker_root'] / 'outcomes.json', {
            'pytest_exitstatus': int(exitstatus), 'events': state['events'],
            'unobserved_nodes': [node for node in CASES
                                 if not any(row['node_id'] == node for row in state['events'])],
            'unobserved_meaning': 'Not observed in this worker; may be unselected, unrun, or run elsewhere.'})
    except Exception as exc:
        reporter = session.config.pluginmanager.getplugin('terminalreporter')
        if reporter is not None:
            reporter.write_line('Native synthetic evidence summary failed: ' + type(exc).__name__)
