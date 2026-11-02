#!/usr/bin/env python3
"""Run one isolated SG2 regression with source/phase evidence, 2026-11-02.

PR #5213 task4. Inputs: one approved layout and fresh external evidence path.
Outputs: child JUnit/log-side evidence and source/import assertions. The calling
test enforces the subprocess deadline. Works in stock CI without extra plugins.
No site/.pth startup, providers, real native executables or external networking.
"""
import argparse
import ipaddress
import json
import os
from pathlib import Path
import shutil
import socket
import sys
import time


ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent


def bootstrap():
    if not (sys.flags.no_site and sys.flags.safe_path and sys.dont_write_bytecode):
        raise ValueError('SG2 child requires -S -P -B')
    venv = Path(sys.executable).parent.parent
    site = venv / 'lib' / f'python{sys.version_info.major}.{sys.version_info.minor}' / 'site-packages'
    if not site.is_dir() or site.resolve() != site:
        raise ValueError('physical existing dependency directory required')
    sys.prefix = sys.exec_prefix = str(venv)
    sys.path.append(str(site))
    sys.path[:0] = [str(ROOT / 'src'), str(ROOT), str(HERE)]


def guard(output, denials):
    def local(host):
        if isinstance(host, bytes):
            host = host.decode('ascii', errors='strict')
        if host == 'localhost':
            return True
        try:
            return ipaddress.ip_address(host).is_loopback
        except (TypeError, ValueError):
            return False

    def refuse(event):
        denials.append(event)
        with (output / 'guard-denials.jsonl').open('a') as stream:
            stream.write(json.dumps({'event': event}) + '\n')
        raise RuntimeError('SG2 offline child refuses ' + event)

    def audit(event, args):
        if event in {'socket.connect', 'socket.sendto', 'socket.bind'}:
            if getattr(args[0], 'family', None) == socket.AF_UNIX:
                return
            address = args[-1]
            if not (isinstance(address, tuple) and local(address[0])):
                refuse(event)
        elif event in {'socket.getaddrinfo', 'socket.gethostbyname', 'socket.gethostbyaddr'}:
            if not local(args[0]):
                refuse(event)
        elif event == 'subprocess.Popen':
            executable, argv, cwd, env = args
            name = Path(os.fsdecode(executable)).name
            if name in {'claude', 'codex', 'gemini', 'gh', 'curl', 'wget', 'ssh'}:
                command = os.fsdecode(executable)
                path = Path(command) if '/' in command else Path(shutil.which(command, path=(env or os.environ).get('PATH')) or '/missing')
                if not path.is_absolute():
                    path = Path(cwd or Path.cwd()) / path
                if not path.resolve().is_relative_to(output):
                    refuse(event + ':' + name)
    sys.addaudithook(audit)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--layout', choices=('none', 'explicit', 'conventional'), required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    if output.exists() or output.is_relative_to(ROOT):
        raise ValueError('fresh SG2 child evidence outside checkout required')
    output.mkdir()
    bootstrap()
    import d76_suite_common_20261031 as common
    denials = []
    guard(output, denials)
    before = common.source(ROOT)
    if not before['tracked_exact']:
        raise ValueError('SG2 child source must match its recorded commit')
    common.save(output / 'source-before.json', before)
    node = ('tests/test_wave7_5213_d76_registration.py::'
            'test_sg2_root_launch_completes_and_records_registered_paths[' + args.layout + ']')
    os.environ['D4D_SG2_CHILD_CASE'] = node
    os.environ['D4D_SG2_CHILD_PID'] = str(os.getpid())
    import pytest

    class Evidence:
        selected = []
        reports = []

        def pytest_collection_finish(self, session):
            self.selected = [item.nodeid for item in session.items]
            common.save(output / 'origins-collected.json', common.origins(ROOT, before))

        def pytest_runtest_logreport(self, report):
            self.reports.append({'nodeid': report.nodeid, 'when': report.when,
                'outcome': report.outcome, 'duration_seconds': report.duration,
                'xfail': getattr(report, 'wasxfail', None)})

    observer = Evidence()
    started = time.monotonic()
    result = int(pytest.main([node, '-q', '-p', 'no:cacheprovider', '--rootdir', str(ROOT),
        '-c', str(ROOT / 'pyproject.toml'), '--basetemp', str(output / 'cases'),
        '--junitxml', str(output / 'pytest.xml')], plugins=[observer]))
    after = common.source(ROOT)
    common.save(output / 'source-after.json', after)
    common.save(output / 'origins-after.json', common.origins(ROOT, before))
    complete = (observer.selected == [node] and len(observer.reports) == 3
        and {row['when'] for row in observer.reports} == {'setup', 'call', 'teardown'}
        and all(row['nodeid'] == node and row['outcome'] == 'passed' and row['xfail'] is None
                for row in observer.reports))
    payload = {'nodeid': node, 'head': before['head'], 'pid': os.getpid(),
        'selected': observer.selected, 'reports': observer.reports, 'returncode': result,
        'source_unchanged': before == after and after['tracked_exact'], 'origins_verified': True,
        'zero_guard_denials': not denials, 'wall_seconds': time.monotonic() - started,
        'passed': result == 0 and complete and before == after and before['tracked_exact']
                  and after['tracked_exact'] and not denials,
        'scope': 'one serial SG2 child; inherited OS policy plus Python offline guard; no site/.pth startup'}
    common.save(output / 'outcome.json', payload)
    return 0 if payload['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
