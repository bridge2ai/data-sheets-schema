#!/usr/bin/env python3
# Purpose: observe D76 pytest controller/workers; assert source imports and offline subprocesses.
# Inputs: D76_TREE/OUTPUT/RUNNER supplied by run_d76_validation; outputs: per-process JSON.
# Serves PR #5213/D76 round 3; 2026-11-02. Incremental evidence survives deadlines.
import ipaddress
import io
import json
import os
from pathlib import Path
import shlex
import shutil
import socket
import sys
import pytest
import d76_suite_common_20261031 as common
import d76_round3_hygiene_20261102 as notes_ci

ROOT = Path(os.environ['D76_TREE'])
OUTPUT = Path(os.environ['D76_OUTPUT'])
BASELINE = json.loads((OUTPUT / 'source-before.json').read_text())
LEDGER = {'collected': [], 'selected': [], 'reports': [], 'collection_errors': [],
          'origins_collected': False, 'origins_after': False}
WORKER = 'master'
GUARD_INSTALLED = False
SERIAL_INDEX = -1
SERIAL_NODE_INDEX = {}
# Evidence belongs to the observer, not to the filesystem/serialization API
# under test. Capture callables before test fixtures can replace module globals.
_EVIDENCE_OPEN = io.open
_EVIDENCE_REPLACE = os.replace
_EVIDENCE_ENCODE = json.JSONEncoder(sort_keys=True).encode
_PHASE_STREAM = None
_DENIAL_PATH = None
_CHECKPOINT_PATHS = None


def _append_evidence(stream, value):
    if stream is None or stream.closed:
        raise RuntimeError('D76 evidence stream is not configured or is closed')
    stream.write(_EVIDENCE_ENCODE(value) + '\n')
    stream.flush()  # Preserve each completed row before a deadline/interruption.


def _close_phase_stream():
    if _PHASE_STREAM is not None:
        _PHASE_STREAM.close()


def checkpoint():
    """Atomic current ledger; append-only phase journal remains the raw history."""
    if _CHECKPOINT_PATHS is None:
        raise RuntimeError('D76 evidence checkpoint is not configured')
    temporary, destination = _CHECKPOINT_PATHS
    with _EVIDENCE_OPEN(temporary, 'w', encoding='utf-8') as stream:
        stream.write(_EVIDENCE_ENCODE(LEDGER) + '\n')
    _EVIDENCE_REPLACE(temporary, destination)


def loopback(host):
    if isinstance(host, bytes):
        host = host.decode('ascii', errors='strict')
    if host == 'localhost':
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except (ValueError, TypeError):
        return False


def install_guard():
    global GUARD_INSTALLED
    if GUARD_INSTALLED:
        return
    GUARD_INSTALLED = True
    def deny(event, detail):
        # Audit hooks survive sessionfinish/unconfigure, including atexit. Use
        # the captured C-level opener on demand rather than a closed stream.
        # The runner refuses any denial artifact; clean runs create none.
        with _EVIDENCE_OPEN(_DENIAL_PATH, 'a', encoding='utf-8') as stream:
            _append_evidence(stream, {'event': event, 'detail': detail})
        raise RuntimeError('D76 offline guard refuses ' + event + ': ' + detail)
    def audit(event, args):
        if event in {'socket.connect', 'socket.sendto', 'socket.bind'}:
            if getattr(args[0], 'family', None) == socket.AF_UNIX:
                return
            address = args[-1]
            if not (isinstance(address, tuple) and loopback(address[0])):
                deny(event, 'non-loopback socket')
        elif event in {'socket.getaddrinfo', 'socket.gethostbyname', 'socket.gethostbyaddr'}:
            if not loopback(args[0]):
                deny(event, 'external DNS')
        elif event == 'subprocess.Popen':
            executable, argv, cwd, env = args
            name = Path(os.fsdecode(executable)).name
            if name in {'claude', 'codex', 'gemini', 'gh', 'curl', 'wget', 'ssh'}:
                command = os.fsdecode(executable)
                path = Path(command) if '/' in command else Path(shutil.which(command, path=(env or os.environ).get('PATH')) or '/missing')
                if not path.is_absolute():
                    path = Path(cwd or Path.cwd()) / path
                if not path.resolve().is_relative_to(OUTPUT):
                    deny(event, 'real provider/network executable ' + name)
    sys.addaudithook(audit)


def pytest_configure(config):
    global WORKER, _PHASE_STREAM, _DENIAL_PATH, _CHECKPOINT_PATHS
    WORKER = getattr(config, 'workerinput', {}).get('workerid', 'master')
    if not (sys.flags.no_site and sys.flags.safe_path and sys.dont_write_bytecode):
        raise ValueError('D76 pytest process requires -S -P -B')
    # Configure controller/worker-specific evidence before test-owned patches.
    # Keep the phase stream open; even captured Path.open delegates to io.open.
    _CHECKPOINT_PATHS = (str(OUTPUT / ('nodes-' + WORKER + '.json.tmp')),
                         str(OUTPUT / ('nodes-' + WORKER + '.json')))
    _DENIAL_PATH = str(OUTPUT / ('guard-denials-' + str(os.getpid()) + '.jsonl'))
    try:
        _PHASE_STREAM = _EVIDENCE_OPEN(str(OUTPUT / ('phases-' + WORKER + '.jsonl')),
                                       'a', encoding='utf-8', buffering=1)
        install_guard()
        common.save(OUTPUT / ('runtime-' + WORKER + '.json'), {
            'python': sys.version, 'executable': sys.executable, 'flags': str(sys.flags),
            'pid': os.getpid(), 'site_startup': False, 'pth_execution': False,
            'sys_path': sys.path, 'root': str(ROOT)})
    except BaseException:
        _close_phase_stream()
        raise


@pytest.hookimpl(optionalhook=True)
def pytest_xdist_setupnodes(config, specs):
    launcher = shlex.join([sys.executable, '-S', '-P', '-B', os.environ['D76_RUNNER'], '--worker-bootstrap'])
    for spec in specs:
        spec.python = launcher


@pytest.hookimpl(tryfirst=True)
def pytest_collection_modifyitems(items):
    LEDGER['collected'] = [item.nodeid for item in items]


@pytest.hookimpl(trylast=True)
def pytest_collection_finish(session):
    LEDGER['selected'] = [item.nodeid for item in session.items]
    common.save(OUTPUT / ('origins-collected-' + WORKER + '.json'), common.origins(ROOT, BASELINE))
    if os.environ.get('D76_NOTES_CI_JOB'):
        common.save(OUTPUT / ('notes-origins-collected-' + WORKER + '.json'), notes_ci.notes_origins(ROOT, BASELINE))
    LEDGER['origins_collected'] = True
    checkpoint()


def pytest_collectreport(report):
    if report.failed:
        LEDGER['collection_errors'].append({'nodeid': report.nodeid, 'message': str(report.longrepr)})


def pytest_runtest_logreport(report):
    global SERIAL_INDEX
    index = getattr(report, 'item_index', None)
    if index is None:
        if report.when == 'setup' or report.nodeid not in SERIAL_NODE_INDEX:
            SERIAL_INDEX += 1
            SERIAL_NODE_INDEX[report.nodeid] = SERIAL_INDEX
        index = SERIAL_NODE_INDEX[report.nodeid]
    row = {'nodeid': report.nodeid, 'when': report.when,
                             'item_index': index, 'worker_id': getattr(report, 'worker_id', WORKER),
                             'outcome': report.outcome, 'xfail': getattr(report, 'wasxfail', None),
                             'duration_seconds': report.duration}
    _append_evidence(_PHASE_STREAM, row)
    LEDGER['reports'].append(row)


def pytest_sessionfinish(session, exitstatus):
    try:
        common.save(OUTPUT / ('origins-after-' + WORKER + '.json'), common.origins(ROOT, BASELINE))
        if os.environ.get('D76_NOTES_CI_JOB'):
            common.save(OUTPUT / ('notes-origins-after-' + WORKER + '.json'), notes_ci.notes_origins(ROOT, BASELINE))
        LEDGER['origins_after'] = True
    finally:
        try:
            checkpoint()
        finally:
            _close_phase_stream()


def pytest_unconfigure(config):
    # Also covers configuration/session failures; repeated close is harmless.
    _close_phase_stream()
