#!/usr/bin/env python3
"""#5485, 2026-11-04: compare one offline admission case at two exact commits.

Inputs: local Git objects and existing dependencies. Outputs: source archives,
verified scratch snapshots, JUnit, cProfile data and normalized function stats.
No production edits; serial, credential-free, 3600-second process-group deadline.
"""
import argparse
import cProfile
import hashlib
import json
import os
from pathlib import Path
import pstats
import signal
import subprocess
import sys
import tarfile
import time

ROOT = Path(__file__).resolve().parents[2]
SCRATCH = ROOT.parent / 'scratch-bc1g2-timing'
COMMITS = {'g1': 'bc8f981f758c46d5bb027c61294d8a67bf70ed30',
           'bc1g2': 'decf0cab1376d608d2ce411d2d6d8ce3e2ac42ce'}
CASE = ('tests/test_report_admission.py::'
        'test_chorus_wire_is_byte_identical_without_admission_and_is_what_was_counted')
PATHS = ['src', 'tests', 'scripts', 'utils', 'config', 'configs', '.claude',
         '.github', 'project', 'data/preprocessed', 'data/rubric',
         'pyproject.toml', 'poetry.lock', 'conftest.py']


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, value):
    path.write_text(json.dumps(value, indent=2) + '\n')
    assert json.loads(path.read_text()) == value


def prepare(label):
    directory = SCRATCH / f'r3-profile-{label}'
    directory.mkdir()
    archive = directory / 'source.tar'
    # G1 predates config/audit_partitions.yaml; never import newer resources.
    tracked = subprocess.check_output(['git', 'ls-tree', '-r', '--name-only',
        COMMITS[label]], cwd=ROOT, text=True).splitlines()
    included = [p for p in PATHS if any(f == p or f.startswith(p + '/') for f in tracked)]
    with archive.open('wb') as stream:
        subprocess.run(['git', '--no-replace-objects', 'archive', COMMITS[label],
                        *included], cwd=ROOT, stdout=stream, check=True)
    tree = directory / 'tree'
    tree.mkdir()
    with tarfile.open(archive) as source:
        source.extractall(tree, filter='data')
    inventory = {str(p.relative_to(tree)): sha(p)
                 for p in sorted(tree.rglob('*')) if p.is_file()}
    assert inventory and inventory['tests/test_report_admission.py']
    save(directory / 'snapshot.json', dict(commit=COMMITS[label],
        archive_sha256=sha(archive), included_paths=included, files=inventory))
    return directory


def run(label):
    directory = prepare(label)
    command = [sys.executable, '-S', '-P', '-B', str(Path(__file__).resolve()),
               'worker', label]
    start = time.monotonic()
    with (directory / 'pytest.log').open('w') as stream:
        child = subprocess.Popen(command, cwd=ROOT, stdout=stream,
                                 stderr=subprocess.STDOUT, start_new_session=True)
        try:
            code = child.wait(timeout=3600)
        except subprocess.TimeoutExpired:
            os.killpg(child.pid, signal.SIGTERM)
            try:
                child.wait(timeout=10)
            except subprocess.TimeoutExpired:
                os.killpg(child.pid, signal.SIGKILL)
                child.wait()
            code = 124
    result = dict(command=command, exit_code=code, deadline_seconds=3600,
                  wall_seconds=time.monotonic() - start)
    save(directory / 'execution.json', result)
    print(json.dumps(result))
    return code


def worker(label):
    directory = SCRATCH / f'r3-profile-{label}'
    tree = directory / 'tree'
    snapshot = json.loads((directory / 'snapshot.json').read_text())
    assert snapshot['commit'] == COMMITS[label]
    assert sha(directory / 'source.tar') == snapshot['archive_sha256']
    assert all(sha(tree / p) == digest for p, digest in snapshot['files'].items())
    sys.path.insert(0, str(Path(__file__).parent))
    from d41_legacy_controls_20261029 import bootstrap, origins
    env = bootstrap(tree, directory)
    fairscape = ROOT.parent.parent / 'data-sheets-schema/fairscape_models'
    sys.path.insert(0, str(fairscape))
    os.environ['PYTHONPATH'] += os.pathsep + str(fairscape)
    os.environ['PYTEST_XDIST_AUTO_NUM_WORKERS'] = '2'
    os.environ['PYTEST_ADDOPTS'] = '--rootdir=. -p xdist.plugin'
    import tempfile
    tempfile.tempdir = os.environ['TMPDIR']
    import pytest
    env.update(commit=COMMITS[label], case=CASE, load_average_before=list(os.getloadavg()),
               snapshot_sha256=sha(directory / 'snapshot.json'))
    save(directory / 'environment.json', env)
    profiler = cProfile.Profile()
    wall, cpu = time.monotonic(), time.process_time()
    profiler.enable()
    try:
        code = pytest.main([CASE, '-q', '--durations=5', '-p', 'no:cacheprovider',
            '--basetemp', str(directory / 'temporary/pytest'),
            '--junitxml', str(directory / 'junit.xml')])
    finally:
        profiler.disable()
        profiler.dump_stats(str(directory / 'profile.pstats'))
    elapsed, cpu_elapsed = time.monotonic() - wall, time.process_time() - cpu
    stats = pstats.Stats(profiler)

    def key(function):
        filename, line, name = function
        return f'{filename.replace(str(tree), "<tree>")}:{line}:{name}'

    rows = [dict(function=key(func), primitive_calls=value[0], calls=value[1],
                 self_seconds=value[2], cumulative_seconds=value[3],
                 callers={key(k): list(v) for k, v in value[4].items()})
            for func, value in stats.stats.items()]
    rows.sort(key=lambda row: -row['cumulative_seconds'])
    save(directory / 'profile.json', dict(commit=COMMITS[label], case=CASE,
        exit_code=int(code), wall_seconds=elapsed, cpu_seconds=cpu_elapsed,
        load_average_after=list(os.getloadavg()), total_calls=stats.total_calls,
        profile_sha256=sha(directory / 'profile.pstats'), functions=rows))
    save(directory / 'module-origins.json', origins(tree))
    assert all(sha(tree / p) == digest for p, digest in snapshot['files'].items())
    return int(code)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=('run', 'worker'))
    parser.add_argument('label', choices=COMMITS)
    args = parser.parse_args()
    raise SystemExit(run(args.label) if args.mode == 'run' else worker(args.label))
