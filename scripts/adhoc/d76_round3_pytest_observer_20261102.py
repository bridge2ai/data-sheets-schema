#!/usr/bin/env python3
# Purpose: observe D76 pytest controller/workers; assert source imports and offline subprocesses.
# Inputs: D76_TREE/OUTPUT/RUNNER supplied by run_d76_validation; outputs: per-process JSON.
# Serves PR #5213/D76 round 3; 2026-11-02. Incremental evidence survives deadlines.
import ipaddress
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


def checkpoint():
    """Atomic current ledger; append-only phase journal remains the raw history."""
    destination = OUTPUT / ('nodes-' + WORKER + '.json')
    temporary = OUTPUT / ('nodes-' + WORKER + '.json.tmp')
    temporary.write_text(json.dumps(LEDGER, sort_keys=True) + '\n')
    os.replace(temporary, destination)


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
        with (OUTPUT / ('guard-denials-' + str(os.getpid()) + '.jsonl')).open('a') as stream:
            stream.write(json.dumps({'event': event, 'detail': detail}) + '\n')
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
    global WORKER
    WORKER = getattr(config, 'workerinput', {}).get('workerid', 'master')
    if not (sys.flags.no_site and sys.flags.safe_path and sys.dont_write_bytecode):
        raise ValueError('D76 pytest process requires -S -P -B')
    install_guard()
    common.save(OUTPUT / ('runtime-' + WORKER + '.json'), {
        'python': sys.version, 'executable': sys.executable, 'flags': str(sys.flags),
        'pid': os.getpid(), 'site_startup': False, 'pth_execution': False,
        'sys_path': sys.path, 'root': str(ROOT)})


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
    LEDGER['reports'].append(row)
    with (OUTPUT / ('phases-' + WORKER + '.jsonl')).open('a') as stream:
        stream.write(json.dumps(row, sort_keys=True) + '\n')


def pytest_sessionfinish(session, exitstatus):
    try:
        common.save(OUTPUT / ('origins-after-' + WORKER + '.json'), common.origins(ROOT, BASELINE))
        if os.environ.get('D76_NOTES_CI_JOB'):
            common.save(OUTPUT / ('notes-origins-after-' + WORKER + '.json'), notes_ci.notes_origins(ROOT, BASELINE))
        LEDGER['origins_after'] = True
    finally:
        checkpoint()
