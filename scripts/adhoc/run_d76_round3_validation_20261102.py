#!/usr/bin/env python3
# Purpose: pinned-archive offline round-3 validation for #5213/D76, with deadlines.
# Inputs: detached clean tree/head and explicit targets; outputs: fresh external logs,
# JUnit, source/import attestations and test-node accounting. Date: 2026-11-02.
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
import signal
import subprocess
import sys
import time
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
PROFILE = HERE / 'd76_loopback_only_20261031.sb'
PROFILE_SHA = '3b819cf36924cb66296dc532b6e8f0e589e21100a45fd965bba9c2052a39cb6e'


def archive_sha(path):
    """Archive verification must not allocate the entire retained source tar."""
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


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
from d76_phase_accounting_20261031 import phase_accounting
import d76_round3_hygiene_20261102 as notes_ci


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
    paths = [str(root / value) for value in notes_ci.ci_paths(os.environ['D76_NOTES_CI_JOB'])] if os.environ.get('D76_NOTES_CI_JOB') else [str(root / 'src')]
    sys.path[:0] = [*paths, str(root), str(root / 'scripts')]
    import d76_round3_pytest_observer_20261102 as observer
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
    # Persist node identities as execution progresses so a long final case
    # cannot hide earlier failures until the terminal summary. Collection
    # retains the requested quiet layout; phase/accounting policy is unchanged.
    result = [*targets, '-q' if options.collect_only or options.notes_ci_job else '-v', '-p', 'no:cacheprovider', '-p', 'd76_round3_pytest_observer_20261102',
              '--rootdir', str(options.tree), '-c', str(options.tree / 'pyproject.toml'),
              '--basetemp', str(options.output / 'cases'), '--junitxml', str(options.output / 'pytest.xml'),
              '--durations=25', '-rfE']
    if options.collect_only:
        result += ['--collect-only']
    if options.metrics:
        result += ['-p', 'd76_round3_metrics_20261102']
    if options.workers:
        if options.collect_only:
            raise ValueError('collection-only must be serial')
        result += ['-n', str(options.workers), '--dist=load', '--maxschedchunk=1']
    if options.ci_shard:
        if targets != ['tests'] or options.ci_shard not in range(1, 7) or options.ci_lane:
            raise ValueError('ordinary shard requires targets=[tests], index 1..6, no API lane')
        result += ['-p', 'utils.pytest_shard', '--ci-lane=ordinary',
                   '--ci-shard=' + str(options.ci_shard) + '/6',
                   '--ci-shard-timings=utils/ci_test_durations.json']
    if options.ci_lane:
        if targets != ['tests'] or options.workers:
            raise ValueError('API CI lanes require full tests collection and serial execution')
        result += ['-p', 'utils.pytest_shard', '--ci-lane=' + options.ci_lane]
    return result


def scrubbed_environment(options):
    env = dict(os.environ)
    removed = sorted(key for key in env if
        re.search(r'(API_KEY|ACCESS_KEY|SECRET|TOKEN|CREDENTIAL)', key, re.I)
        or key.startswith(('ANTHROPIC_', 'CBORG_', 'OPENAI_', 'AZURE_', 'AWS_', 'GOOGLE_API_',
                           'GEMINI_', 'VERTEX_', 'GIT_', 'D76_'))
        or key.upper().endswith('_PROXY')
        or key in {'D4D_INSTALL_TESTS', 'D4D_PROFILE', 'D4D_RESOURCE_ROOT', 'PYTHONHOME',
                   'PYTHONPATH', 'PYTEST_PLUGINS', 'PYTEST_DISABLE_PLUGIN_AUTOLOAD', 'PYTHONPYCACHEPREFIX',
                   'D4D_ISOLATED_TEST_REVIEW'})
    for key in removed:
        env.pop(key)
    env.update(PYTHONDONTWRITEBYTECODE='1', PYTEST_ADDOPTS='', PIP_NO_INDEX='1',
        PIP_DISABLE_PIP_VERSION_CHECK='1', UV_OFFLINE='1', HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1',
        GIT_NO_LAZY_FETCH='1', GIT_CONFIG_GLOBAL='/dev/null', GIT_CONFIG_NOSYSTEM='1',
        GIT_OPTIONAL_LOCKS='0', TMPDIR=str(options.output / 'temporary'),
        PYTHONPYCACHEPREFIX=str(options.output / 'pycache'),
        PYTHONPATH=os.pathsep.join((str(options.tree / 'src'), str(options.tree), str(HERE))),
        D76_TREE=str(options.tree), D76_OUTPUT=str(options.output), D76_RUNNER=str(Path(__file__).resolve()))
    if options.notes_ci_job:
        # Match the workflow's notes jobs: pinned transport refuses a cache
        # prefix even when bytecode writes are disabled. Ordinary/API tests
        # retain their external prefix; notes child caches are audited below.
        env.pop('PYTHONPYCACHEPREFIX')
        env['D76_NOTES_CI_JOB'] = options.notes_ci_job
        env['PYTHONPATH'] = os.pathsep.join([
            *(str(options.tree / value) for value in notes_ci.ci_paths(options.notes_ci_job)), str(options.tree), str(HERE)])
    if getattr(options, 'attest_isolated_tests', False):
        adapter = options.tree / 'scripts/adhoc/run_d76_sg2_case_20261102.py'
        env['D4D_ISOLATED_TEST_REVIEW'] = json.dumps({
            'root': str(options.tree), 'runner': str(adapter),
            'sha256': common.sha(adapter.read_bytes()), 'head': options.expect_head}, sort_keys=True)
    return env, removed


def case_counts(xml):
    try:
        cases = list(ET.parse(xml).getroot().iter('testcase')) if xml.is_file() else []
    except ET.ParseError:
        cases = []  # A deadline can leave partial XML; phase ledger stays authoritative.
    counts = Counter({'passed': 0, 'failed': 0, 'errors': 0, 'skipped': 0})
    for case in cases:
        kind = ('errors' if case.find('error') is not None else 'failed' if case.find('failure') is not None
                else 'skipped' if case.find('skipped') is not None else 'passed')
        counts[kind] += 1
    return cases, dict(counts)


def phase_journal(path):
    """Keep interrupted raw journal bytes; never manufacture a terminal phase."""
    raw = path.read_bytes()
    rows, errors = [], []
    for number, line in enumerate(raw.splitlines(keepends=True), 1):
        try:
            if not line.endswith(b'\n'):
                raise ValueError('incomplete unterminated journal row')
            row = json.loads(line)
            if (type(row) is not dict or type(row.get('nodeid')) is not str
                    or type(row.get('when')) is not str or row['when'] not in {'setup', 'call', 'teardown'}
                    or type(row.get('outcome')) is not str or row['outcome'] not in {'passed', 'failed', 'skipped'}
                    or (row.get('item_index') is not None and
                        (type(row['item_index']) is not int or row['item_index'] < 0))):
                raise ValueError('invalid journal phase record')
            rows.append(row)
        except (ValueError, UnicodeError) as exc:
            errors.append({'line': number, 'bytes': len(line), 'sha256': common.sha(line), 'reason': str(exc)})
    return rows, {'path': str(path), 'sha256': common.sha(raw), 'bytes': len(raw),
                  'complete_rows': len(rows), 'malformed_rows': errors, 'passed': not errors}


def owned_group_state(group):
    """Read state only; the unreaped owned leader reserves this group identity."""
    observed = None
    try:
        observed = subprocess.run(['/bin/ps', '-axo', 'pid=,pgid=,state='],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=3)
        members = []
        for line in observed.stdout.splitlines():
            pid, pgid, state = line.split()
            if int(pgid) == group:
                members.append({'pid': int(pid), 'group': int(pgid), 'state': state})
        retired = (observed.returncode == 0 and any(row['pid'] == group for row in members)
                   and all(row['state'].startswith('Z') for row in members))
        return {'observed': observed.returncode == 0, 'members': members, 'all_retired': retired,
                'returncode': observed.returncode, 'stdout': observed.stdout, 'stderr': observed.stderr}
    except (OSError, ValueError, subprocess.TimeoutExpired) as exc:
        return {'observed': False, 'all_retired': False, 'error': repr(exc),
                'stdout': observed.stdout if observed is not None else None,
                'stderr': observed.stderr if observed is not None else None,
                'returncode': observed.returncode if observed is not None else None}


def execute_bounded(cmd, options, env, stream):
    """Deadline owns exactly one new process group; no unrelated process signals."""
    started = time.monotonic()
    child = subprocess.Popen(cmd, cwd=options.tree, env=env, stdout=stream,
                             stderr=subprocess.STDOUT, start_new_session=True)
    timed_out = False
    signals = []
    retirement = None
    common.save(options.output / 'controller.json', {'pid': child.pid, 'process_group': child.pid,
        'deadline_seconds': options.deadline_seconds, 'new_session': True})
    try:
        while True:
            remaining = options.deadline_seconds - (time.monotonic() - started)
            if remaining <= 0:
                raise subprocess.TimeoutExpired(cmd, options.deadline_seconds)
            try:
                code = child.wait(timeout=min(10, remaining))
                break
            except subprocess.TimeoutExpired:
                # Outside the pytest sandbox, read only this owned controller's
                # RSS. Failure to observe is recorded, never bypassed or shimmed.
                if options.metrics:
                    try:
                        sample = subprocess.run(['/bin/ps', '-o', 'pid=,ppid=,rss=,etime=,pcpu=',
                            '-p', str(child.pid)], stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            text=True, timeout=3)
                        observation = {'returncode': sample.returncode, 'stdout': sample.stdout,
                                       'stderr': sample.stderr}
                    except subprocess.TimeoutExpired:
                        observation = {'observation_error': 'owned-controller ps sample timed out'}
                    with (options.output / 'controller-rss.jsonl').open('a') as record:
                        record.write(json.dumps({'monotonic': time.monotonic(), 'pid': child.pid,
                            **observation, 'rss_units': 'KiB'}) + '\n')
    except subprocess.TimeoutExpired:
        timed_out = True
        # The child PID remains owned and unreaped here, so cannot have been reused.
        for sig in (signal.SIGTERM, signal.SIGKILL):
            try:
                os.killpg(child.pid, sig)
                signals.append({'signal': sig.name, 'sent': True})
            except ProcessLookupError:
                signals.append({'signal': sig.name, 'sent': False, 'error': 'ProcessLookupError'})
            except PermissionError as exc:
                # macOS may refuse signals to a zombie-only group. Do not infer
                # that from EPERM: independently inspect the still-owned group.
                retirement = owned_group_state(child.pid)
                signals.append({'signal': sig.name, 'sent': False, 'error': repr(exc),
                                'group_state_before_reap': retirement})
                if sig != signal.SIGKILL or not retirement['all_retired']:
                    common.save(options.output / 'deadline.json', {'expired': True,
                        'seconds': options.deadline_seconds, 'signals': signals,
                        'termination_verified': False, 'controller_pid': child.pid,
                        'policy': 'no source-after or terminal test acceptance before verified retirement'})
                    raise RuntimeError('owned deadline group retirement is unverified; evidence retained') from exc
            if sig == signal.SIGTERM:
                # Never poll/wait/reap the leader during this grace. Even if it
                # exits on TERM, its unreaped PID prevents group-ID reuse while
                # we KILL descendants that ignored TERM. H-R3-1.
                time.sleep(5)
        try:
            code = child.wait(timeout=10)
        except subprocess.TimeoutExpired as exc:
            raise RuntimeError('owned pytest process did not reap after deadline SIGKILL') from exc
    common.save(options.output / 'deadline.json', {'expired': timed_out, 'seconds': options.deadline_seconds,
        'wall_seconds': time.monotonic() - started, 'signals': signals, 'returncode': code,
        'termination_verified': True, 'group_state_before_reap': retirement,
        'limit_scope': 'pytest controller and its new process group; separately sessioned descendants are not claimed; no timing-performance claim'})
    return code, timed_out


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
    proof = json.loads(options.archive_proof.read_text())
    if proof.get('head') != options.expect_head or proof.get('destination') != str(options.tree):
        raise ValueError('archive proof does not bind this source/head')
    if proof.get('git_tree') != before['tree'] or proof.get('source_method') != 'git archive; metadata initialized afterwards without checkout':
        raise ValueError('archive proof source identity differs')
    for artifact in (proof, proof.get('fairscape', {})):
        archive_path = Path(artifact['archive'])
        if archive_path.is_symlink() or archive_sha(archive_path) != artifact['archive_sha256']:
            raise ValueError('retained git archive changed')
    fairscape = common.fairscape(options.tree, before)
    targets = selected_targets(options)
    if options.notes_ci_job:
        notes_ci.validate_targets(options.notes_ci_job, targets)
        if options.ci_shard or options.ci_lane or options.collect_only or options.workers:
            raise ValueError('notes CI sessions cannot be shard or collection-only runs')
    argv = command(options, targets)
    options.output.mkdir(parents=True, exist_ok=False)
    (options.output / 'temporary').mkdir()
    common.save(options.output / 'source-before.json', before)
    common.save(options.output / 'pytest-command.json', {'cwd': str(options.tree), 'argv': argv})
    policy = options.output / 'network-profile.sb'
    policy.write_bytes(PROFILE.read_bytes())
    env, removed = scrubbed_environment(options)
    helper_paths = [Path(__file__).resolve(), HERE / 'd76_round3_pytest_observer_20261102.py',
                    HERE / 'd76_suite_common_20261031.py', HERE / 'd76_phase_accounting_20261031.py',
                    HERE / 'd76_round3_hygiene_20261102.py', HERE / 'd76_round3_metrics_20261102.py', PROFILE]
    if options.attest_isolated_tests:
        helper_paths += [options.tree / 'scripts/adhoc/run_d76_sg2_case_20261102.py',
                         options.tree / 'tests/utils/isolated_pytest.py',
                         options.tree / 'tests/utils/subprocess_deadline.py']
    helpers = {str(path): common.sha(path.read_bytes()) for path in helper_paths}
    target_hashes = {}
    for target in targets:
        path = Path(target.split('::', 1)[0])
        if not path.is_absolute():
            path = options.tree / path
        if path.is_file():
            target_hashes[str(path)] = common.sha(path.read_bytes())
    hygiene_args = ('status', '--ignored', '--porcelain=v1', '--untracked-files=all', '--', 'notes/', 'tests/', 'utils/')
    if options.notes_ci_job:
        hygiene_args = ('status', '--ignored', '--porcelain=v1', '-z', '--untracked-files=all')
    hygiene = common.git(options.tree, *hygiene_args).decode()
    notes_before = notes_ci.cache_scope_listing(options.tree) if options.notes_ci_job else None
    if options.notes_ci_job and hygiene:
        raise ValueError('notes CI mode requires a fresh tree with empty global ignored/untracked status')
    cmd = ['/usr/bin/sandbox-exec', '-D', 'LOCAL_ROOT=' + str(options.output), '-f', str(policy),
           sys.executable, '-S', '-P', '-B', str(Path(__file__).resolve()), '--child']
    common.save(options.output / 'plan.json', {
        'head': options.expect_head, 'git_tree': before['tree'], 'worktree': str(options.tree),
        'archive_proof': str(options.archive_proof), 'archive_proof_sha256': common.sha(options.archive_proof.read_bytes()),
        'detached': detached, 'targets': targets, 'target_sha256': target_hashes,
        'helpers': helpers, 'command': cmd, 'pytest_argv': argv, 'workers': options.workers,
        'collect_only': options.collect_only, 'ci_ordinary_shard_of_6': options.ci_shard,
        'ci_api_lane': options.ci_lane, 'deadline_seconds': options.deadline_seconds, 'metrics': options.metrics,
        'notes_ci_job': options.notes_ci_job,
        'attest_isolated_tests': options.attest_isolated_tests,
        'notes_ci_pythonpath': list(notes_ci.ci_paths(options.notes_ci_job)) if options.notes_ci_job else None,
        'hygiene_mode': 'notes_ci_new_tracked_source_bytecode' if notes_ci.permits_bytecode(options.notes_ci_job) else 'strict_unchanged',
        'child_startup_scope': ('Pytest controller/workers use -S -P -B. Existing CI notes tests may start '
            'whitelisted-environment Python children with normal site startup. OS network sandbox is inherited; '
            'pytest import attestations do not claim every descendant import.' if options.notes_ci_job else None),
        'removed_environment_names': removed, 'fairscape': fairscape, 'runtime': runtime(),
        'workflow_sha256': common.sha((options.tree / '.github/workflows/main.yaml').read_bytes()),
        'selector_sha256': common.sha((options.tree / 'utils/pytest_shard.py').read_bytes()),
        'network': 'mandatory OS sandbox in pytest and all descendants; loopback/local IPC only',
        'limits': 'functional macOS/Python3.13 tests; no provider/scientific or Linux/Python3.12 acceptance'})
    started = time.monotonic()
    with (options.output / 'pytest.log').open('xb') as stream:
        code, timed_out = execute_bounded(cmd, options, env, stream)
    after = common.source(options.tree)
    common.save(options.output / 'source-after.json', after)
    hygiene_after = common.git(options.tree, *hygiene_args).decode()
    hygiene_report = (notes_ci.classify(options.tree, before, notes_before, hygiene, hygiene_after)
        if notes_ci.permits_bytecode(options.notes_ci_job) else {'before': hygiene, 'after': hygiene_after,
            'hygiene_mode': 'strict_unchanged', 'unchanged': hygiene == hygiene_after,
            'passed': hygiene == hygiene_after})
    common.save(options.output / 'hygiene.json', hygiene_report)
    records = {path.stem.removeprefix('nodes-'): json.loads(path.read_text())
               for path in options.output.glob('nodes-*.json')}
    journal_proofs = []
    for path in options.output.glob('phases-*.jsonl'):
        key = path.stem.removeprefix('phases-')
        rows, journal_proof = phase_journal(path)
        records.setdefault(key, {})['reports'] = rows
        journal_proofs.append(journal_proof)
    journal_valid = all(row['passed'] for row in journal_proofs)
    common.save(options.output / 'phase-journals.json', {'files': journal_proofs, 'passed': journal_valid,
        'policy': 'raw journals retained; malformed rows explicitly recorded; any malformed row refuses acceptance'})
    master = records.get('master', {})
    workers = {key: value for key, value in records.items() if key != 'master'}
    observations = list(workers.values()) if options.workers else [master]
    selected = observations[0].get('selected', []) if observations else []
    collected = observations[0].get('collected', []) if observations else []
    same_collection = bool(observations) and all(row.get('selected') == selected and row.get('collected') == collected for row in observations)
    cases, raw_junit_counts = case_counts(options.output / 'pytest.xml')
    reports = master.get('reports', [])
    accounting = phase_accounting(selected, reports)
    common.save(options.output / 'phase-accounting.json', accounting)
    counts = accounting['counts']
    complete = (accounting['all_selected_completed'] and
                Counter(selected) == Counter(row['nodeid'] for row in reports if row['when'] == 'teardown')
                and len(cases) == len(selected))
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
    invariant = (before == after and hygiene_report['passed'] and origins_ok and helpers_same and
                 targets_same and sandbox_loaded and same_collection and not denials and not timed_out and journal_valid)
    collection_complete = options.collect_only and bool(selected) and not reports and not cases and not collection_errors and invariant
    result = {'returncode': code, 'deadline_expired': timed_out, 'phase_journals_valid': journal_valid,
        'counts': counts, 'collected_occurrences': len(collected),
        'counts_basis': 'completed phase-ledger occurrences; interrupted/unstarted separate',
        'raw_junit_counts': raw_junit_counts,
        'selected_occurrences': len(selected), 'selected_unique': len(set(selected)),
        'node_accounting_complete': complete, 'all_worker_collections_identical': same_collection,
        'worker_count': len(workers), 'collection_errors': collection_errors,
        'source_unchanged': before == after, 'hygiene_passed': hygiene_report['passed'],
        'hygiene_unchanged': hygiene_report['unchanged'], 'hygiene_mode': hygiene_report['hygiene_mode'],
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
    parser.add_argument('--archive-proof', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--target', action='append', default=[])
    parser.add_argument('--targets-json', type=Path)
    parser.add_argument('--workers', type=int, choices=(0, 1, 2, 3), default=0)
    parser.add_argument('--collect-only', action='store_true')
    parser.add_argument('--ci-shard', type=int)
    parser.add_argument('--ci-lane', choices=('routing-dispatch', 'routing-portable', 'routing-regate', 'routing-default-layout'))
    parser.add_argument('--deadline-seconds', type=float, default=2700)
    parser.add_argument('--metrics', action='store_true')
    parser.add_argument('--attest-isolated-tests', action='store_true',
                        help='Explicitly attest isolated test children through the pinned review adapter')
    parser.add_argument('--notes-ci-job', choices=tuple(notes_ci.NOTES_TARGETS))
    options = parser.parse_args()
    options.tree = options.tree.resolve(strict=True)
    options.output = options.output.resolve()
    if not 1 <= options.deadline_seconds <= 7200:
        raise ValueError('deadline must be 1..7200 seconds')
    return run(options)


if __name__ == '__main__':
    raise SystemExit(main())
