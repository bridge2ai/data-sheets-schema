#!/usr/bin/env python3
# Purpose: frozen offline validation for #5213/D76, including xdist workers.
# Inputs: detached clean tree/head and explicit targets; outputs: fresh external logs,
# JUnit, source/import attestations and test-node accounting. Date: 2026-10-31.
# Copies the reviewed Wave7 loopback-only policy; no provider/network/installation.
import argparse
from collections import Counter
import hashlib
import importlib.metadata
import importlib.util
import json
import os
from pathlib import Path
import re
import shlex
import subprocess
import sys
import time
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
PROFILE = HERE / 'd76_loopback_only_20261031.sb'
PROFILE_SHA = '3b819cf36924cb66296dc532b6e8f0e589e21100a45fd965bba9c2052a39cb6e'


def bootstrap():
    if not (sys.flags.no_site and sys.flags.safe_path and sys.dont_write_bytecode):
        raise ValueError('run this helper with -S -P -B')
    venv = Path(sys.executable).parent.parent
    site = venv / 'lib' / f'python{sys.version_info.major}.{sys.version_info.minor}' / 'site-packages'
    if not site.is_dir() or site.resolve() != site:
        raise ValueError('existing physical dependency directory required')
    sys.prefix = sys.exec_prefix = str(venv)
    sys.path.append(str(site))
    sys.path.insert(0, str(HERE))
    return site


bootstrap()
import d76_suite_common_20261031 as common


def runtime():
    packages = {}
    for name in ('pytest', 'pytest-xdist', 'pytest-mock', 'pytest-asyncio', 'PyYAML',
                 'linkml', 'linkml-runtime', 'pydantic', 'anthropic', 'httpx'):
        try:
            packages[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            packages[name] = None
    return {'python': sys.version, 'executable': sys.executable, 'packages': packages,
            'site_startup': False, 'pth_execution': False,
            'pytest_plugins': sorted((e.name, e.value) for e in importlib.metadata.entry_points(group='pytest11'))}


def establish_child():
    root = Path(os.environ['D76_TREE'])
    sys.path[:0] = [str(root / 'src'), str(root), str(root / 'scripts')]
    import d76_pytest_observer_20261031 as observer
    observer.install_guard()
    return observer


def worker_bootstrap():
    # execnet appends exactly -u -c <bootstrap code>. Do not run site/.pth first.
    tail = sys.argv[2:]
    if len(tail) != 3 or tail[:2] != ['-u', '-c']:
        raise ValueError('unexpected execnet bootstrap invocation')
    establish_child()
    sys.argv = ['-c']
    exec(compile(tail[2], '<d76-execnet-bootstrap>', 'exec'), {'__name__': '__main__'})


def child():
    establish_child()
    output = Path(os.environ['D76_OUTPUT'])
    common.save(output / 'bootstrap.json', runtime())
    import pytest
    args = json.loads((output / 'pytest-command.json').read_text())['argv']
    return int(pytest.main(args))


def selected_targets(options):
    targets = list(options.target)
    if options.targets_json:
        values = json.loads(options.targets_json.read_text())
        if not isinstance(values, list) or not all(isinstance(value, str) for value in values):
            raise ValueError('--targets-json must contain a list of targets')
        targets.extend(values)
    if not targets or len(targets) != len(set(targets)):
        raise ValueError('distinct explicit targets required')
    for value in targets:
        path = Path(value.split('::', 1)[0])
        if not path.is_absolute():
            path = options.tree / path
        if not path.exists() or '\n' in value or '\0' in value:
            raise ValueError('missing/invalid target: ' + value)
    return targets


def command(options, targets):
    result = [*targets, '-q', '-p', 'no:cacheprovider', '-p', 'd76_pytest_observer_20261031',
              '--rootdir', str(options.tree), '-c', str(options.tree / 'pyproject.toml'),
              '--basetemp', str(options.output / 'cases'), '--junitxml', str(options.output / 'pytest.xml'),
              '--durations=25', '-rfE']
    if options.collect_only:
        result += ['--collect-only']
    if options.workers:
        if options.collect_only:
            raise ValueError('collection-only must be serial')
        result += ['-n', str(options.workers), '--dist=load', '--maxschedchunk=1']
    if options.ci_shard:
        if targets != ['tests'] or options.ci_shard not in range(1, 5):
            raise ValueError('ordinary shard requires targets=[tests], index 1..4')
        result += ['-p', 'utils.pytest_shard', '--ci-lane=ordinary',
                   '--ci-shard=' + str(options.ci_shard) + '/4',
                   '--ci-shard-timings=utils/ci_test_durations.json']
    return result


def scrubbed_environment(options):
    env = dict(os.environ)
    removed = sorted(key for key in env if
        re.search(r'(API_KEY|ACCESS_KEY|SECRET|TOKEN|CREDENTIAL)', key, re.I)
        or key.startswith(('ANTHROPIC_', 'CBORG_', 'OPENAI_', 'AZURE_', 'AWS_', 'GOOGLE_API_',
                           'GEMINI_', 'VERTEX_', 'GIT_', 'D76_'))
        or key.upper().endswith('_PROXY')
        or key in {'D4D_INSTALL_TESTS', 'D4D_PROFILE', 'D4D_RESOURCE_ROOT', 'PYTHONHOME',
                   'PYTHONPATH', 'PYTEST_PLUGINS', 'PYTEST_DISABLE_PLUGIN_AUTOLOAD', 'PYTHONPYCACHEPREFIX'})
    for key in removed:
        env.pop(key)
    env.update(PYTHONDONTWRITEBYTECODE='1', PYTEST_ADDOPTS='', PIP_NO_INDEX='1',
        PIP_DISABLE_PIP_VERSION_CHECK='1', UV_OFFLINE='1', HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1',
        GIT_NO_LAZY_FETCH='1', GIT_CONFIG_GLOBAL='/dev/null', GIT_CONFIG_NOSYSTEM='1',
        GIT_OPTIONAL_LOCKS='0', TMPDIR=str(options.output / 'temporary'),
        PYTHONPYCACHEPREFIX=str(options.output / 'pycache'),
        PYTHONPATH=os.pathsep.join((str(options.tree / 'src'), str(options.tree), str(HERE))),
        D76_TREE=str(options.tree), D76_OUTPUT=str(options.output), D76_RUNNER=str(Path(__file__).resolve()))
    return env, removed


def case_counts(xml):
    cases = list(ET.parse(xml).getroot().iter('testcase')) if xml.is_file() else []
    counts = Counter({'passed': 0, 'failed': 0, 'errors': 0, 'skipped': 0})
    for case in cases:
        kind = ('errors' if case.find('error') is not None else 'failed' if case.find('failure') is not None
                else 'skipped' if case.find('skipped') is not None else 'passed')
        counts[kind] += 1
    return cases, dict(counts)


def run(options):
    if options.output.exists() or options.output.is_relative_to(options.tree):
        raise ValueError('fresh evidence directory outside test tree required')
    if sys.platform != 'darwin' or not Path('/usr/bin/sandbox-exec').is_file():
        raise ValueError('macOS sandbox-exec mandatory; no unwrapped fallback')
    if PROFILE.is_symlink() or common.sha(PROFILE.read_bytes()) != PROFILE_SHA:
        raise ValueError('network profile differs from reviewed policy')
    detached = subprocess.run(['git', '-C', str(options.tree), 'symbolic-ref', '-q', 'HEAD'],
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE).returncode == 1
    if not detached:
        raise ValueError('validation requires a detached checkout')
    before = common.source(options.tree)
    if before['head'] != options.expect_head or not before['tracked_exact'] or common.git(
            options.tree, 'status', '--porcelain=v1', '--untracked-files=all'):
        raise ValueError('clean exact frozen checkout required')
    fairscape = common.fairscape(options.tree, before)
    targets = selected_targets(options)
    argv = command(options, targets)
    options.output.mkdir(parents=True, exist_ok=False)
    (options.output / 'temporary').mkdir()
    common.save(options.output / 'source-before.json', before)
    common.save(options.output / 'pytest-command.json', {'cwd': str(options.tree), 'argv': argv})
    policy = options.output / 'network-profile.sb'
    policy.write_bytes(PROFILE.read_bytes())
    env, removed = scrubbed_environment(options)
    helper_paths = [Path(__file__).resolve(), HERE / 'd76_pytest_observer_20261031.py',
                    HERE / 'd76_suite_common_20261031.py', PROFILE]
    helpers = {str(path): common.sha(path.read_bytes()) for path in helper_paths}
    target_hashes = {}
    for target in targets:
        path = Path(target.split('::', 1)[0])
        if not path.is_absolute():
            path = options.tree / path
        if path.is_file():
            target_hashes[str(path)] = common.sha(path.read_bytes())
    hygiene_args = ('status', '--ignored', '--porcelain=v1', '--untracked-files=all', '--', 'notes/', 'tests/', 'utils/')
    hygiene = common.git(options.tree, *hygiene_args).decode()
    cmd = ['/usr/bin/sandbox-exec', '-D', 'LOCAL_ROOT=' + str(options.output), '-f', str(policy),
           sys.executable, '-S', '-P', '-B', str(Path(__file__).resolve()), '--child']
    common.save(options.output / 'plan.json', {
        'head': options.expect_head, 'git_tree': before['tree'], 'worktree': str(options.tree),
        'detached': detached, 'targets': targets, 'target_sha256': target_hashes,
        'helpers': helpers, 'command': cmd, 'pytest_argv': argv, 'workers': options.workers,
        'collect_only': options.collect_only, 'ci_ordinary_shard_of_4': options.ci_shard,
        'removed_environment_names': removed, 'fairscape': fairscape, 'runtime': runtime(),
        'workflow_sha256': common.sha((options.tree / '.github/workflows/main.yaml').read_bytes()),
        'selector_sha256': common.sha((options.tree / 'utils/pytest_shard.py').read_bytes()),
        'network': 'mandatory OS sandbox in pytest and all descendants; loopback/local IPC only',
        'limits': 'functional macOS/Python3.13 tests; no provider/scientific or Linux/Python3.12 acceptance'})
    started = time.monotonic()
    with (options.output / 'pytest.log').open('xb') as stream:
        code = subprocess.run(cmd, cwd=options.tree, env=env, stdout=stream, stderr=subprocess.STDOUT).returncode
    after = common.source(options.tree)
    common.save(options.output / 'source-after.json', after)
    hygiene_after = common.git(options.tree, *hygiene_args).decode()
    common.save(options.output / 'hygiene.json', {'before': hygiene, 'after': hygiene_after})
    records = {path.stem.removeprefix('nodes-'): json.loads(path.read_text())
               for path in options.output.glob('nodes-*.json')}
    master = records.get('master', {})
    workers = {key: value for key, value in records.items() if key != 'master'}
    observations = list(workers.values()) if options.workers else [master]
    selected = observations[0].get('selected', []) if observations else []
    collected = observations[0].get('collected', []) if observations else []
    same_collection = bool(observations) and all(row.get('selected') == selected and row.get('collected') == collected for row in observations)
    cases, counts = case_counts(options.output / 'pytest.xml')
    reports = master.get('reports', [])
    complete = bool(selected) and Counter(selected) == Counter(row['nodeid'] for row in reports if row['when'] == 'teardown') and len(cases) == len(selected)
    collection_errors = {key: row['collection_errors'] for key, row in records.items() if row.get('collection_errors')}
    origins_ok = bool(observations) and all(row.get('origins_collected') and row.get('origins_after') for row in observations)
    helpers_same = all(common.sha(path.read_bytes()) == helpers[str(path)] for path in helper_paths)
    targets_same = all(common.sha(Path(path).read_bytes()) == digest for path, digest in target_hashes.items())
    sandbox_loaded = (options.output / 'bootstrap.json').is_file() and common.sha(policy.read_bytes()) == PROFILE_SHA
    # A test may catch an audit exception and pass. That still attempted an
    # operation outside this offline contract, and cannot establish acceptance.
    denials = {path.name: {'sha256': common.sha(path.read_bytes()),
                          'events': path.read_text().splitlines()}
               for path in options.output.glob('guard-denials-*.jsonl')}
    denial_count = sum(len(value['events']) for value in denials.values())
    common.save(options.output / 'guard-denials.json', {'files': denials, 'event_count': denial_count,
        'zero_denials': not denials, 'classified_exception_policy': 'none; any denial artifact refuses acceptance'})
    invariant = (before == after and hygiene == hygiene_after and origins_ok and helpers_same and
                 targets_same and sandbox_loaded and same_collection and not denials)
    collection_complete = options.collect_only and bool(selected) and not reports and not cases and not collection_errors and invariant
    result = {'returncode': code, 'counts': counts, 'collected_occurrences': len(collected),
        'selected_occurrences': len(selected), 'selected_unique': len(set(selected)),
        'node_accounting_complete': complete, 'all_worker_collections_identical': same_collection,
        'worker_count': len(workers), 'collection_errors': collection_errors,
        'source_unchanged': before == after, 'hygiene_passed': hygiene == hygiene_after,
        'origins_verified': origins_ok, 'helpers_unchanged': helpers_same, 'targets_unchanged': targets_same,
        'sandbox_loaded': sandbox_loaded, 'wall_seconds': time.monotonic() - started,
        'guard_denial_count': denial_count, 'zero_guard_denials': not denials,
        'collection_complete': collection_complete, 'collection_passed': code == 0 and collection_complete,
        'passed': not options.collect_only and code == 0 and complete and invariant and not collection_errors,
        'expected_failures_not_interpreted': True, 'scientific_acceptance': 'not_assessed'}
    common.save(options.output / 'nodes.json', {'collected': collected, 'selected': selected, 'reports': reports, 'collection_errors': collection_errors})
    common.save(options.output / 'outcome.json', result)
    print(json.dumps(result, sort_keys=True))
    return 0 if (result['collection_passed'] if options.collect_only else result['passed']) else 1


def main():
    if sys.argv[1:] == ['--child']:
        return child()
    if len(sys.argv) > 1 and sys.argv[1] == '--worker-bootstrap':
        worker_bootstrap()
        return 0
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--tree', type=Path, required=True)
    parser.add_argument('--expect-head', required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--target', action='append', default=[])
    parser.add_argument('--targets-json', type=Path)
    parser.add_argument('--workers', type=int, choices=(0, 1, 2, 3, 4), default=0)
    parser.add_argument('--collect-only', action='store_true')
    parser.add_argument('--ci-shard', type=int)
    options = parser.parse_args()
    options.tree = options.tree.resolve(strict=True)
    options.output = options.output.resolve()
    return run(options)


if __name__ == '__main__':
    raise SystemExit(main())
