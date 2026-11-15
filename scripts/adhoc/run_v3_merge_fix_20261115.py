#!/usr/bin/env python3
"""Offline v3 merge diagnosis for PR 5968, 2026-11-15.

Inputs: assigned checkout, primary dependency Python, explicit pytest nodes.
Outputs: immutable scratch commands, import witnesses, JUnit and outcome files.
Uses an external process-group deadline; never arms an inherited alarm.
Optional path isolation removes only the primary checkout's editable path in
pytest processes, for comparison with CI's current-checkout installation.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
E = ROOT.parent
PRIMARY = E.parent / 'data-sheets-schema'
PYTHON = PRIMARY / '.venv/bin/python'
SCRATCH = E / 'scratch-v3-merge-fix-20261115'
FILES = ['test_native_' + name + '.py' for name in (
    'execution_registration_v2', 'shared_registration', 'shared_execution_failure',
    'shared_callback_preloading', 'environment_manifest', 'canary_packet_builder',
    'u3d_round9_boundaries', 'shared_callback_teardown', 'shared_callback_report_bound',
    'subscription_guard_v2', 'u3d_guard_contract')]


def save(path, value):
    with path.open('x') as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write('\n')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def pytest_configure(config):
    """Record the real namespace; isolate only in explicitly labeled diagnostics."""
    directory = os.environ.get('V3_MERGE_FIX_EVIDENCE')
    if not directory:
        return
    before = list(sys.path)
    removed = []
    if os.environ.get('V3_MERGE_FIX_PATH_ISOLATION') == '1':
        removed = [entry for entry in sys.path if Path(entry).resolve() == PRIMARY / 'src']
        sys.path[:] = [entry for entry in sys.path if entry not in removed]
    import data_sheets_schema
    from data_sheets_schema import native_environment_manifest as manifest
    try:
        manifest._own_source_authority()
        check = 'passed'
    except ValueError as exc:
        check = str(exc)
    site = PRIMARY / '.venv/lib' / ('python' + str(sys.version_info.major) + '.' + str(sys.version_info.minor)) / 'site-packages'
    pth = site / 'data_sheets_schema.pth'
    save(Path(directory) / ('origins-' + str(os.getpid()) + '.json'), dict(
        interpreter=sys.executable, prefix=sys.prefix, pythonpath=os.environ['PYTHONPATH'],
        namespace=list(data_sheets_schema.__path__), manifest_source=manifest.__file__,
        namespace_check=check, sys_path_before=before, sys_path_after=list(sys.path),
        removed_primary_editable_paths=removed, editable_pth=str(pth),
        editable_pth_contents=pth.read_text(), alarm=list(signal.getitimer(signal.ITIMER_REAL))))


def group_exists(pid):
    try:
        os.killpg(pid, 0)
        return True
    except ProcessLookupError:
        return False


def summarize(directory):
    report = directory / 'junit.xml'
    if not report.is_file():
        return
    cases = []
    totals = dict(passed=0, failed=0, errors=0, skipped=0)
    for case in ET.parse(report).getroot().iter('testcase'):
        state = 'passed'
        detail = ''
        for tag, value in (('failure', 'failed'), ('error', 'errors'), ('skipped', 'skipped')):
            node = case.find(tag)
            if node is not None:
                state, detail = value, (node.text or '')
                break
        totals[state] += 1
        category = None
        if state in ('failed', 'errors'):
            category = ('scanner_template' if 'v2 producer module execution is not exact' in detail else
                        'shared_editable_namespace' if 'own distribution exclusion requires the exact pinned project namespace' in detail else 'other')
        cases.append(dict(classname=case.get('classname'), name=case.get('name'),
                          state=state, category=category, detail=detail))
    value = dict(totals=totals, cases=cases)
    save(directory / 'results.json', value)
    return totals


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('label')
    parser.add_argument('nodes', nargs='*')
    parser.add_argument('--isolate-path', action='store_true')
    parser.add_argument('--workers', type=int, choices=range(1, 5), default=4)
    parser.add_argument('--deadline', type=int, default=1800)
    args = parser.parse_args()
    assert ROOT.name == 'codex-v3-merge-fix-20261115'
    assert not (E / 'plans/native_quiet_window.lock').exists()
    assert signal.getitimer(signal.ITIMER_REAL) == (0.0, 0.0)
    directory = SCRATCH / args.label
    if directory != directory.resolve() or directory.parent != SCRATCH:
        parser.error('run label must name one physical scratch directory')
    directory.mkdir(parents=True, exist_ok=False)
    for name in ('home', 'tmp'):
        (directory / name).mkdir()
    profile = directory / 'offline.sb'
    profile.write_text('(version 1)\n(allow default)\n(deny network*)\n'
        '(deny process-exec (regex #"/(claude|codex|gemini|agy)(/|$)"))\n')
    env = dict(PATH=str(PYTHON.parent) + ':/usr/bin:/bin:/usr/sbin:/sbin',
        HOME=str(directory / 'home'), TMPDIR=str(directory / 'tmp'), LANG='en_US.UTF-8',
        PYTHONPATH=str(ROOT / 'src'), PYTHONDONTWRITEBYTECODE='1', PYTHONNOUSERSITE='1',
        PYTEST_DISABLE_PLUGIN_AUTOLOAD='1', PYTEST_ADDOPTS='', UV_OFFLINE='1', PIP_NO_INDEX='1',
        GIT_NO_LAZY_FETCH='1', GIT_ALLOW_PROTOCOL='', GIT_CONFIG_GLOBAL='/dev/null',
        GIT_CONFIG_SYSTEM='/dev/null', GIT_OPTIONAL_LOCKS='0',
        V3_MERGE_FIX_EVIDENCE=str(directory),
        V3_MERGE_FIX_PATH_ISOLATION='1' if args.isolate_path else '0')
    nodes = args.nodes or ['tests/' + name for name in FILES]
    command = ['/usr/bin/sandbox-exec', '-f', str(profile), str(PYTHON), '-B', '-m', 'pytest',
        '-v', '--tb=short', '-o', 'addopts=', '-p', 'no:cacheprovider', '-p', 'xdist.plugin',
        '-p', 'scripts.adhoc.run_v3_merge_fix_20261115', '-n', str(args.workers),
        '--dist', 'load', '--maxschedchunk=1', '--basetemp', str(directory / 'bt'),
        '--junitxml', str(directory / 'junit.xml'), *nodes]
    head = subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=ROOT, check=True, capture_output=True, text=True).stdout.strip()
    save(directory / 'plan.json', dict(command=command, deadline_seconds=args.deadline,
        source_commit=head, helper_sha256=sha(Path(__file__)), pythonpath=env['PYTHONPATH'],
        path_isolation=args.isolate_path, inherited_alarm=False,
        code_patch_sha256=hashlib.sha256(subprocess.run(
            ['git', 'diff', '--binary', 'f10e8ae20', '--',
             'src/data_sheets_schema/native_environment_manifest.py',
             'tests/test_native_environment_manifest.py', 'tests/test_native_u3d_round9_boundaries.py'],
            cwd=ROOT, check=True, capture_output=True).stdout).hexdigest(),
        tracked_diff_sha256=hashlib.sha256(subprocess.run(
            ['git', 'diff', '--binary', 'HEAD'], cwd=ROOT, check=True, capture_output=True).stdout).hexdigest(),
        test_sources={name: sha(ROOT / name) for name in sorted({node.split('::')[0] for node in nodes})}))
    (directory / 'runner-source.txt').write_bytes(Path(__file__).read_bytes())
    started = time.monotonic()
    timed_out = False
    with (directory / 'stdout.log').open('xb') as out, (directory / 'stderr.log').open('xb') as err:
        child = subprocess.Popen(command, cwd=ROOT, env=env, stdout=out, stderr=err, start_new_session=True)
        try:
            code = child.wait(timeout=args.deadline)
        except subprocess.TimeoutExpired:
            timed_out = True
            os.killpg(child.pid, signal.SIGTERM)
            try:
                child.wait(timeout=5)
            except subprocess.TimeoutExpired:
                os.killpg(child.pid, signal.SIGKILL)
                child.wait(timeout=5)
            code = 124
        forced_cleanup = group_exists(child.pid)
        if forced_cleanup:
            os.killpg(child.pid, signal.SIGTERM)
            until = time.monotonic() + 5
            while group_exists(child.pid) and time.monotonic() < until:
                time.sleep(0.1)
            if group_exists(child.pid):
                os.killpg(child.pid, signal.SIGKILL)
    value = dict(returncode=code, timed_out=timed_out, forced_cleanup=forced_cleanup,
        seconds=time.monotonic() - started, process_group_gone=not group_exists(child.pid),
        totals=summarize(directory))
    save(directory / 'outcome.json', value)
    print(json.dumps(value))
    return code


if __name__ == '__main__':
    raise SystemExit(main())
