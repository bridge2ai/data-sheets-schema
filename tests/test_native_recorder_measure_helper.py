"""Offline safety tests for the recorder baseline driver; no acceptance test runs."""
from contextlib import ExitStack
import errno
import importlib.util
import itertools
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts/adhoc/native_recorder_measure_20261026.py'
MODULE = importlib.util.spec_from_file_location('recorder_measure_helper', SCRIPT)
driver = importlib.util.module_from_spec(MODULE)
MODULE.loader.exec_module(driver)


def host(cpu=0, foreign=None):
    processes = [{'pid': os.getpid(), 'ppid': 1, 'cpu_percent': 99, 'name': 'measurement-driver'}]
    if foreign is not None:
        processes.append({'pid': 999_999, 'ppid': 1, 'cpu_percent': foreign, 'name': 'foreign-python'})
    return {'at': '2026-10-26T00:00:00Z', 'monotonic': 0, 'logical_cpus': 16,
            'cpu_percent': cpu, 'load': [0.1, 0.1, 0.1], 'processes': processes}


def decision(samples):
    return driver.idle_decision(samples, max_mean_cpu=15, max_peak_cpu=35,
        max_load_per_cpu=0.5, max_foreign_process_cpu=5, owned_roots={os.getpid()})


class DriverSafetyTests(unittest.TestCase):
    def test_dependency_bootstrap_restores_venv_without_executing_pth(self):
        with tempfile.TemporaryDirectory() as directory:
            venv = Path(directory).resolve() / 'venv'
            site = venv / 'lib' / ('python' + '.'.join(map(str, sys.version_info[:2]))) / 'site-packages'
            site.mkdir(parents=True)
            (venv / 'pyvenv.cfg').write_text('include-system-site-packages = false\n')
            marker = venv / 'pth-ran'
            (site / 'editable.pth').write_text('import pathlib; pathlib.Path(' + repr(str(marker)) + ').touch()\n')
            with ExitStack() as stack:
                stack.enter_context(mock.patch.object(driver.sys, 'flags', SimpleNamespace(no_site=1, safe_path=True)))
                stack.enter_context(mock.patch.object(driver.sys, 'dont_write_bytecode', True))
                stack.enter_context(mock.patch.object(driver.sys, 'executable', str(venv / 'bin/python')))
                stack.enter_context(mock.patch.object(driver.sys, 'prefix', '/base'))
                stack.enter_context(mock.patch.object(driver.sys, 'exec_prefix', '/base-exec'))
                stack.enter_context(mock.patch.object(driver.sys, 'path', ['/stdlib']))
                observed = driver.initialize_dependencies()
                self.assertEqual(driver.sys.prefix, str(venv))
                self.assertEqual(driver.sys.exec_prefix, str(venv))
                self.assertEqual(driver.sys.path, ['/stdlib', str(site)])
                self.assertEqual(observed['prefix_before'], {'prefix': '/base', 'exec_prefix': '/base-exec'})
                self.assertEqual(observed['pth_execution'], 'disabled')
                self.assertFalse(observed['dependency_bytes_attested'])
                self.assertFalse(marker.exists())
                with self.assertRaisesRegex(ValueError, 'physical venv dependencies'):
                    driver.initialize_dependencies()

    def test_dependency_bootstrap_refuses_missing_isolation_and_foreign_site(self):
        for no_site, safe_path, no_bytecode in ((0, True, True), (1, False, True), (1, True, False)):
            with self.subTest(no_site=no_site, safe_path=safe_path, no_bytecode=no_bytecode):
                with mock.patch.object(driver.sys, 'flags', SimpleNamespace(no_site=no_site, safe_path=safe_path)), \
                        mock.patch.object(driver.sys, 'dont_write_bytecode', no_bytecode):
                    with self.assertRaisesRegex(ValueError, '-S -P -B'):
                        driver.initialize_dependencies()
        with tempfile.TemporaryDirectory() as directory:
            venv = Path(directory).resolve() / 'venv'
            site = venv / 'lib' / ('python' + '.'.join(map(str, sys.version_info[:2]))) / 'site-packages'
            site.mkdir(parents=True)
            (venv / 'pyvenv.cfg').write_text('include-system-site-packages = false\n')
            with ExitStack() as stack:
                stack.enter_context(mock.patch.object(driver.sys, 'flags', SimpleNamespace(no_site=1, safe_path=True)))
                stack.enter_context(mock.patch.object(driver.sys, 'dont_write_bytecode', True))
                stack.enter_context(mock.patch.object(driver.sys, 'executable', str(venv / 'bin/python')))
                stack.enter_context(mock.patch.object(driver.sys, 'path', ['/foreign/site-packages']))
                with self.assertRaisesRegex(ValueError, 'physical venv dependencies'):
                    driver.initialize_dependencies()

    def test_delivery_is_a_distinct_exact_head_not_a_pristine_escape(self):
        exact = {'head': 'be0bd05821256212e89e4d011ba6b30a780e299b', 'pristine': True}
        driver.require_source(exact, 'delivery')
        with self.assertRaises(ValueError):
            driver.require_source({**exact, 'pristine': False}, 'delivery')
        with self.assertRaises(ValueError):
            driver.require_source(exact, 'current')

    def test_single_busy_foreign_core_prevents_idle_qualification_on_large_host(self):
        observed = host(cpu=6, foreign=99)
        self.assertFalse(decision([observed])['idle'])
        self.assertTrue(decision([host(cpu=6)])['idle'])

    def test_process_scope_excludes_only_observed_owned_descendants(self):
        observed = host()
        observed['processes'].extend([
            {'pid': 10, 'ppid': os.getpid(), 'cpu_percent': 80, 'name': 'pytest'},
            {'pid': 11, 'ppid': 10, 'cpu_percent': 80, 'name': 'recorder'},
            {'pid': 12, 'ppid': 1, 'cpu_percent': 80, 'name': 'unrelated'},
        ])
        self.assertEqual([row['pid'] for row in driver.competing_processes(observed, {os.getpid()}, 5)], [12])

    def test_environment_strips_observer_and_named_secrets_without_logging_values(self):
        with mock.patch.dict(os.environ, {'CBORG_API_KEY': 'secret-value',
                'D4D_RECORDER_OBSERVER': '/must/not/load.py', 'ANTHROPIC_AUTH_TOKEN': 'another-secret',
                'HOME': '/fixture-home'}, clear=True):
            env, removed = driver.environment(Path('/tree'), Path('/evidence'))
        self.assertEqual(env['HOME'], '/fixture-home')
        self.assertNotIn('CBORG_API_KEY', env)
        self.assertNotIn('D4D_RECORDER_OBSERVER', env)
        self.assertEqual(set(removed), {'CBORG_API_KEY', 'D4D_RECORDER_OBSERVER', 'ANTHROPIC_AUTH_TOKEN'})
        self.assertNotIn('secret-value', json.dumps(removed))

    def test_git_queries_disable_replacements_and_ambient_repository_overrides(self):
        with mock.patch.dict(os.environ, {'GIT_DIR': '/wrong', 'GIT_REPLACE_REF_BASE': 'refs/other'}, clear=False):
            with mock.patch.object(driver.subprocess, 'check_output', return_value=b'head') as call:
                driver.git(Path('/intended'), 'rev-parse', 'HEAD')
        command = call.call_args.args[0]
        self.assertIn('--no-replace-objects', command)
        self.assertIn('--no-optional-locks', command)
        self.assertNotIn('GIT_DIR', call.call_args.kwargs['env'])
        self.assertNotIn('GIT_REPLACE_REF_BASE', call.call_args.kwargs['env'])

    def test_plugin_autoload_choice_overrides_ambient_setting_explicitly(self):
        with mock.patch.dict(os.environ, {'PYTEST_DISABLE_PLUGIN_AUTOLOAD': '1'}):
            enabled, _ = driver.environment(Path('/tree'), Path('/evidence'), plugin_autoload='enabled')
            disabled, _ = driver.environment(Path('/tree'), Path('/evidence'), plugin_autoload='disabled')
            default, _ = driver.environment(Path('/tree'), Path('/evidence'))
        self.assertNotIn('PYTEST_DISABLE_PLUGIN_AUTOLOAD', enabled)
        self.assertEqual(disabled['PYTEST_DISABLE_PLUGIN_AUTOLOAD'], '1')
        self.assertEqual(default['PYTEST_DISABLE_PLUGIN_AUTOLOAD'], '1')

    def test_exclusive_trial_path_refuses_reuse_and_source_output(self):
        with tempfile.TemporaryDirectory() as directory:
            parent = Path(directory)
            tree = parent / 'tree'; tree.mkdir()
            trial = driver.reserve_output(parent, 'trial-1', tree)
            (trial / 'sentinel').write_text('keep')
            with self.assertRaises(FileExistsError):
                driver.reserve_output(parent, 'trial-1', tree)
            self.assertEqual((trial / 'sentinel').read_text(), 'keep')
            with self.assertRaises(ValueError):
                driver.reserve_output(tree, 'trial-2', tree)
            alias = parent / 'tree-alias'
            alias.symlink_to(tree, target_is_directory=True)
            with self.assertRaises(ValueError):
                driver.reserve_output(alias, 'trial-alias', tree)
            self.assertFalse((tree / 'trial-alias').exists())
            with self.assertRaises(ValueError):
                driver.reserve_output(parent, '../escape', tree)

    def test_source_inventory_sees_ignored_python_and_hidden_nonpython_changes(self):
        with tempfile.TemporaryDirectory() as directory:
            tree = Path(directory)
            env = {**os.environ, 'GIT_CONFIG_GLOBAL': os.devnull, 'GIT_CONFIG_NOSYSTEM': '1'}
            def git(*args):
                return subprocess.run(['git', '-C', str(tree), *args], check=True,
                    capture_output=True, env=env)
            git('init', '-q')
            git('config', 'user.name', 'Offline fixture')
            git('config', 'user.email', 'fixture@example.invalid')
            (tree / 'src/pkg').mkdir(parents=True)
            (tree / 'src/pkg/base.py').write_text('VALUE = 1\n')
            policy = tree / 'src/pkg/policy.json'; policy.write_text('{"value":1}\n')
            (tree / '.gitignore').write_text('ignored.py\n')
            git('add', '.')
            git('commit', '-qm', 'fixture')
            self.assertTrue(driver.source_identity(tree)['pristine'])
            hidden = tree / 'src/pkg/ignored.py'; hidden.write_text('UNTRACKED = True\n')
            observed = driver.source_identity(tree)
            self.assertFalse(observed['pristine'])
            self.assertIn('src/pkg/ignored.py', observed['files'])
            hidden.unlink()
            git('update-index', '--assume-unchanged', 'src/pkg/policy.json')
            old = policy.stat()
            policy.write_text('{"value":2}\n')
            os.utime(policy, ns=(old.st_atime_ns, old.st_mtime_ns))
            changed = driver.source_identity(tree)
            self.assertFalse(changed['pristine'])
            self.assertFalse(changed['files']['src/pkg/policy.json']['committed_exact'])

    def test_origin_proof_refuses_foreign_namespace_and_unpinned_module(self):
        with tempfile.TemporaryDirectory() as directory:
            tree = Path(directory).resolve()
            package = tree / 'src/data_sheets_schema'; package.mkdir(parents=True)
            module = package / 'fixture.py'; module.write_text('VALUE = 1\n')
            inventory = {'files': {'src/data_sheets_schema/fixture.py': {
                'sha256': driver.sha(module.read_bytes()), 'committed_exact': True}}}
            namespace = SimpleNamespace(__file__=None, __path__=[str(package)])
            selected = SimpleNamespace(__file__=str(module))
            proof = driver.origins(tree, inventory, {'data_sheets_schema': namespace,
                'data_sheets_schema.fixture': selected})
            self.assertIn('data_sheets_schema.fixture', proof)
            namespace.__path__.append('/foreign/data_sheets_schema')
            with self.assertRaises(ValueError):
                driver.origins(tree, inventory, {'data_sheets_schema': namespace})
            module.write_text('VALUE = 2\n')
            with self.assertRaises(ValueError):
                driver.origins(tree, inventory, {'data_sheets_schema.fixture': selected})

    def test_gitlinks_pin_commits_without_treating_uninitialized_directories_as_files(self):
        for relative in ('aurelian', 'scripts/vendor'):
            with self.subTest(relative=relative), tempfile.TemporaryDirectory() as directory:
                tree = Path(directory).resolve()
                env = {**os.environ, 'GIT_CONFIG_GLOBAL': os.devnull, 'GIT_CONFIG_NOSYSTEM': '1'}

                def git(*args):
                    return subprocess.run(['git', '-C', str(tree), *args], check=True,
                        capture_output=True, env=env).stdout.decode().strip()

                git('init', '-q')
                git('config', 'user.name', 'Offline fixture')
                git('config', 'user.email', 'fixture@example.invalid')
                (tree / 'src/pkg').mkdir(parents=True)
                (tree / 'src/pkg/base.py').write_text('VALUE = 1\n')
                git('add', '.')
                git('commit', '-qm', 'local gitlink target')
                target = git('rev-parse', 'HEAD')
                # A real local commit object suffices; no submodule operation,
                # remote URL, network access or object fetch is needed.
                git('update-index', '--add', '--cacheinfo', f'160000,{target},{relative}')
                git('commit', '-qm', 'record uninitialized gitlink')
                observed = driver.source_identity(tree)
                # Git reports a physically missing gitlink as deleted. Its
                # identity can be inventoried, but the clean-tree gate stays.
                self.assertFalse(observed['pristine'])
                self.assertEqual(observed['tracked_status'], f' D {relative}\n')
                self.assertNotIn(relative, observed['files'])
                self.assertEqual(observed['gitlinks'][relative], {'mode': '160000', 'kind': 'commit',
                    'git_commit': target, 'worktree_state': 'absent', 'contents_in_byte_inventory': False})
                self.assertIn('submodule contents', observed['inventory_scope'])
                link = tree / relative
                link.mkdir(parents=True)
                empty = driver.source_identity(tree)
                self.assertTrue(empty['pristine'])
                self.assertEqual(empty['gitlinks'][relative]['worktree_state'], 'empty_directory')
                injected = link / 'untracked.sh'
                injected.write_text('#!/bin/sh\nexit 0\n')
                injected.chmod(0o755)
                with self.assertRaisesRegex(ValueError, 'populated gitlink'):
                    driver.source_identity(tree)
                injected.unlink()
                link.rmdir()
                link.symlink_to(tree / 'src/pkg', target_is_directory=True)
                with self.assertRaisesRegex(ValueError, 'symlink gitlink path'):
                    driver.source_identity(tree)
                link.unlink()
                link.write_text('a gitlink cannot be replaced by a regular file\n')
                with self.assertRaisesRegex(ValueError, 'non-directory gitlink path'):
                    driver.source_identity(tree)

    def test_worker_environment_duplicates_import_one_selected_namespace(self):
        with tempfile.TemporaryDirectory() as directory:
            parent = Path(directory).resolve()
            tree = parent / 'tree'
            package = tree / 'src/data_sheets_schema'; package.mkdir(parents=True)
            (tree / 'scripts').mkdir()
            module = package / 'fixture.py'; module.write_text('VALUE = 1\n')
            foreign = parent / 'foreign'; (foreign / 'data_sheets_schema').mkdir(parents=True)
            alias = parent / 'selected-src-alias'; alias.symlink_to(tree / 'src', target_is_directory=True)
            env, _ = driver.environment(tree, parent / 'evidence')
            # A worker inherits these PYTHONPATH entries before adding its
            # own selected roots; symlink spellings must not add a third root.
            inherited = env['PYTHONPATH'].split(os.pathsep)
            paths, removed = driver.isolated_paths(tree,
                [*inherited, *inherited, str(alias), str(foreign), *sys.path])
            self.assertEqual(paths[:3], [str(tree / p) for p in ('src', 'scripts', '.')])
            self.assertEqual(len(paths), len({Path(path).resolve() for path in paths}))
            self.assertIn(str(foreign), removed)
            self.assertNotIn(str(foreign), paths)
            inventory = {'files': {'src/data_sheets_schema/fixture.py': {
                'sha256': driver.sha(module.read_bytes()), 'committed_exact': True}}}
            saved = {name: value for name, value in sys.modules.copy().items()
                     if name == 'data_sheets_schema' or name.startswith('data_sheets_schema.')}
            for name in saved:
                sys.modules.pop(name)
            try:
                with mock.patch.object(sys, 'path', paths), mock.patch.object(sys, 'dont_write_bytecode', True):
                    importlib.invalidate_caches()
                    namespace = importlib.import_module('data_sheets_schema')
                    selected = importlib.import_module('data_sheets_schema.fixture')
                    self.assertEqual(list(namespace.__path__), [str(package)])
                    self.assertEqual(selected.VALUE, 1)
                    proof = driver.origins(tree, inventory, {'data_sheets_schema': namespace,
                        'data_sheets_schema.fixture': selected})
                    self.assertEqual(proof['data_sheets_schema']['paths'], [str(package)])
            finally:
                for name in list(sys.modules):
                    if name == 'data_sheets_schema' or name.startswith('data_sheets_schema.'):
                        sys.modules.pop(name)
                sys.modules.update(saved)
                importlib.invalidate_caches()

    def test_junit_requires_the_exact_single_node_and_preserves_skips(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'result.xml'
            node = '<testcase classname="tests.test_native_shared_execution" name="' + driver.NODE.split('::')[1] + '"><skipped/></testcase>'
            path.write_text('<testsuites><testsuite>' + node + '</testsuite></testsuites>')
            self.assertEqual(driver.junit(path)['skipped'], 1)
            path.write_text('<testsuites><testsuite>' + node * 2 + '</testsuite></testsuites>')
            with self.assertRaises(ValueError):
                driver.junit(path)

    def fake_run(self, parent, *, samples=None, after_changed=False, hang=False, idle_only=False,
                 worker_exit=0, survivor=False, observation_error=False, mode='idle'):
        tree = parent / 'tree'; tree.mkdir()
        target = 'pair-control' if mode == 'cpu-pair' else 'cpu-profile' if mode == 'cpu-profile' else 'current'
        before = {'head': driver.HEADS[target], 'pristine': True, 'files': {}, 'tree': 'fixture'}
        after = {**before, 'tree': 'changed'} if after_changed else before
        args = SimpleNamespace(tree=tree, python=Path(sys.executable), output=parent,
            trial='trial', target=target, idle_seconds=5, mode=mode, idle_only=idle_only,
            host_samples=parent / 'observer.jsonl', host_observer_pid=777_777,
            plugin_autoload='enabled',
            driver_seconds=1800, max_mean_cpu=15, max_peak_cpu=35,
            max_load_per_cpu=0.5, max_foreign_process_cpu=5)
        launches, signals = [], []
        node = driver.NODE.split('::')[1]

        class Process:
            pid = 123_456
            returncode = None
            polls = 0
            def poll(self):
                self.polls += 1
                return None if hang or self.polls == 1 else worker_exit
            def wait(self, timeout=None):
                self.returncode = 130 if hang else worker_exit
                return self.returncode

        class InspectionError(Exception):
            pass

        class NoSuchProcess(InspectionError):
            pass

        class ObservedProcess:
            def __init__(self, pid):
                self.pid = pid
            def create_time(self):
                if observation_error:
                    raise InspectionError('identity unavailable')
                return float(self.pid)
            def children(self, recursive):
                return [ObservedProcess(123_457)] if self.pid == 123_456 else []
            def is_running(self):
                return survivor and self.pid == 123_457

        def launch(command, **kwargs):
            launches.append((command, kwargs))
            output = parent / 'trial'
            (output / 'pytest.xml').write_text('<testsuites><testsuite><testcase classname="tests.test_native_shared_execution" name="' + node + '"/></testsuite></testsuites>')
            for name in ('dependency-bootstrap-worker.json', 'origins-before.json', 'origins-after.json',
                         'environment-worker.json'):
                (output / name).write_text('{"modules": {}}')
            (output / 'worker-result.json').write_text(json.dumps({
                'returncode': max(worker_exit, 0), 'pytest_wall_seconds': 1}))
            return Process()

        stack = ExitStack()
        stack.enter_context(mock.patch.object(driver, 'initialize_dependencies', return_value={
            'site_startup': 'disabled', 'pth_execution': 'disabled', 'site_packages': '/fixture/site-packages'}))
        stack.enter_context(mock.patch.object(driver, 'source_identity', side_effect=[before, before, after] if not idle_only else [before, after]))
        reader = SimpleNamespace(path=args.host_samples, identity=(1, 2),
            sample=mock.Mock(side_effect=samples if samples is not None else lambda: host()))
        reader_factory = stack.enter_context(mock.patch.object(driver, 'HostSampleReader'))
        reader_factory.return_value.__enter__.return_value = reader
        def denied_network(output):
            evidence = {'network_denied': True, 'network_bind_denied': True,
                        'pid': os.getpid(), 'errno': errno.EPERM, 'phase': 'bind'}
            driver.write_new(output / 'network-self-check-driver.json', evidence)
            return evidence
        stack.enter_context(mock.patch.object(driver, 'network_self_check', side_effect=denied_network))
        stack.enter_context(mock.patch.object(driver, 'host_samples_write_denial', return_value={
            'write_open_denied': True, 'errno': errno.EPERM, 'pid': os.getpid()}))
        stack.enter_context(mock.patch.object(driver.subprocess, 'Popen', side_effect=launch))
        elapsed = [0.0]
        def advance(seconds):
            elapsed[0] += seconds
        stack.enter_context(mock.patch.object(driver.time, 'sleep', side_effect=advance))
        stack.enter_context(mock.patch.object(driver.time, 'monotonic', side_effect=lambda: elapsed[0]))
        stack.enter_context(mock.patch.dict(sys.modules, {'psutil': SimpleNamespace(
            cpu_percent=lambda **kw: 0, Process=ObservedProcess,
            Error=InspectionError, NoSuchProcess=NoSuchProcess)}))
        stack.enter_context(mock.patch.object(driver.os, 'killpg', side_effect=lambda pid, sig: signals.append((pid, sig))))
        if hang:
            clock = itertools.count(0, 2000)
            stack.enter_context(mock.patch.object(driver.time, 'monotonic', side_effect=lambda: next(clock)))
        return args, launches, signals, stack

    def test_fake_process_success_launches_one_child_and_retains_origin_junit_source_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            parent = Path(directory)
            args, launches, signals, stack = self.fake_run(parent)
            with stack:
                self.assertEqual(driver.run(args), 0)
            self.assertEqual(len(launches), 1)
            self.assertTrue(launches[0][1]['start_new_session'])
            self.assertEqual(launches[0][0][1:4], ['-S', '-P', '-B'])
            self.assertEqual(signals, [])
            bootstrap = json.loads((parent / 'trial/dependency-bootstrap-driver.json').read_bytes())
            self.assertEqual(bootstrap['pth_execution'], 'disabled')
            outcome = json.loads((parent / 'trial/outcome.json').read_bytes())
            self.assertTrue(outcome['source_unchanged'])
            self.assertTrue(outcome['idle_trial_qualified'])
            self.assertEqual(outcome['junit']['tests'], 1)
            self.assertEqual(outcome['host_observer_identity']['pid'], 777_777)
            self.assertTrue(json.loads((parent / 'trial/network-self-check-driver.json').read_bytes())['network_denied'])
            self.assertTrue(outcome['read_only_host_samples']['write_open_denied'])
            self.assertTrue(outcome['cleanup_verified'])
            self.assertEqual(outcome['observed_owned_processes'], [
                {'pid': 123_456, 'create_time': 123_456.0},
                {'pid': 123_457, 'create_time': 123_457.0}])
            self.assertEqual(outcome['observed_owned_survivors'], [])

    def test_idle_only_and_busy_preflight_never_launch_a_test(self):
        for busy in (False, True):
            with self.subTest(busy=busy), tempfile.TemporaryDirectory() as directory:
                parent = Path(directory)
                args, launches, signals, stack = self.fake_run(parent, samples=[host(foreign=99 if busy else None)] * 5, idle_only=True)
                with stack:
                    self.assertEqual(driver.run(args), 3 if busy else 0)
                self.assertEqual(launches, [])
                self.assertFalse((parent / 'trial/cases').exists())
                outcome = json.loads((parent / 'trial/outcome.json').read_bytes())
                self.assertTrue(outcome['cleanup_verified'])
                self.assertEqual(outcome['cleanup_reason'], 'no_child_launched')

    def test_cpu_profile_busy_host_skips_gate_preserves_software_verdict_and_cleanup(self):
        for worker_exit in (0, 1):
            with self.subTest(worker_exit=worker_exit), tempfile.TemporaryDirectory() as directory:
                parent = Path(directory)
                # One host sample is consumed only after launch; a gate would exhaust it.
                args, launches, signals, stack = self.fake_run(parent, mode='cpu-profile',
                    samples=[host(cpu=99, foreign=99)], worker_exit=worker_exit)
                with stack, mock.patch.object(driver, 'idle_decision',
                        side_effect=AssertionError('CPU profiling must not evaluate the quiet gate')):
                    self.assertEqual(driver.run(args), worker_exit)
                self.assertEqual(len(launches), 1)
                self.assertEqual(signals, [])
                decision = json.loads((parent / 'trial/idle-decision.json').read_bytes())
                self.assertEqual(decision['status'], 'deferred_cpu_profiling')
                self.assertIsNone(decision['idle'])
                self.assertEqual(decision['samples'], 0)
                self.assertTrue(decision['quiet_gate_required_for_wall_claims'])
                self.assertNotIn('elapsed_seconds', decision)
                rows = [json.loads(line) for line in (parent / 'trial/host.jsonl').read_text().splitlines()]
                self.assertEqual([row['stage'] for row in rows], ['test'])
                self.assertEqual(rows[0]['cpu_percent'], 99)
                outcome = json.loads((parent / 'trial/outcome.json').read_bytes())
                plan = json.loads((parent / 'trial/plan.json').read_bytes())
                for document in (plan, outcome):
                    self.assertFalse(document['idle_trial_qualified'])
                    self.assertEqual(document['walltime_scope'], 'contended_diagnostic_not_threshold_evidence')
                    self.assertEqual(document['timing_verdict'], 'not_assessed')
                    self.assertTrue(document['quiet_gate_required_for_wall_claims'])
                    self.assertIn('Lead ruling 2, 2026-11-06', document['protocol_amendment_2'])
                self.assertEqual(outcome['status'],
                    'software_test_passed' if worker_exit == 0 else 'software_test_failed')
                self.assertTrue(outcome['during_test_competing_process_observations'])
                self.assertTrue(outcome['network_self_check']['network_bind_denied'])
                self.assertTrue(outcome['read_only_host_samples']['write_open_denied'])
                self.assertTrue(outcome['source_unchanged'])
                self.assertTrue(outcome['cleanup_verified'])
                self.assertEqual(plan['outer_driver_watchdog_seconds'], 1800)

    def test_causal_pair_mode_retains_original_limits_and_explicit_authority(self):
        with tempfile.TemporaryDirectory() as directory, mock.patch.dict(
                driver.HEADS, {'pair-control': 'f' * 40}):
            parent = Path(directory)
            args, launches, signals, stack = self.fake_run(parent, mode='cpu-pair',
                samples=[host(cpu=99, foreign=99)])
            with stack, mock.patch.object(driver, 'idle_decision',
                    side_effect=AssertionError('CPU pair must not claim an idle gate')):
                self.assertEqual(driver.run(args), 0)
            self.assertEqual(len(launches), 1)
            self.assertEqual(signals, [])
            outcome = json.loads((parent / 'trial/outcome.json').read_bytes())
            self.assertTrue(outcome['cleanup_verified'])
            self.assertFalse(outcome['idle_trial_qualified'])
            self.assertIn('exactly one control/treatment', outcome['causal_pair_authority'])
            self.assertEqual(outcome['timing_verdict'], 'not_assessed')

    def test_idle_mode_still_blocks_same_busy_host_before_worker(self):
        with tempfile.TemporaryDirectory() as directory:
            parent = Path(directory)
            args, launches, _, stack = self.fake_run(parent,
                samples=[host(cpu=99, foreign=99)] * 5)
            with stack:
                self.assertEqual(driver.run(args), 3)
            self.assertEqual(launches, [])
            decision = json.loads((parent / 'trial/idle-decision.json').read_bytes())
            self.assertFalse(decision['idle'])
            self.assertEqual(decision['samples'], 5)
            self.assertEqual(decision['elapsed_seconds'], 5)
            outcome = json.loads((parent / 'trial/outcome.json').read_bytes())
            self.assertEqual(outcome['status'], 'blocked_host_busy')
            self.assertTrue(outcome['cleanup_verified'])

    def test_cpu_profile_idle_only_refused_before_driver_setup(self):
        with mock.patch.object(driver, 'initialize_dependencies') as bootstrap:
            with self.assertRaisesRegex(ValueError, 'not an idle-only gate'):
                driver.run(SimpleNamespace(mode='cpu-profile', idle_only=True))
        bootstrap.assert_not_called()
        with mock.patch.object(driver, 'run') as run, self.assertRaises(SystemExit) as error:
            driver.main(['--tree', '/tree', '--target', 'current', '--output', '/evidence',
                '--mode', 'cpu-profile', '--idle-only'])
        self.assertEqual(error.exception.code, 2)
        run.assert_not_called()

    def test_cpu_profile_parser_is_explicit_and_idle_remains_default(self):
        for option, expected in (([], 'idle'), (['--mode', 'cpu-profile'], 'cpu-profile')):
            with self.subTest(expected=expected), mock.patch.object(driver, 'run', return_value=0) as run:
                self.assertEqual(driver.main(['--tree', '/tree', '--target', 'current',
                    '--output', '/evidence', '--trial', 'neutral', '--python', '/python',
                    '--host-samples', '/samples.jsonl', '--host-observer-pid', '123',
                    '--driver-seconds', '1800', *option]), 0)
            self.assertEqual(run.call_args.args[0].mode, expected)

    def test_cpu_profiling_is_pinned_and_cannot_label_diagnostic_source_as_baseline(self):
        self.assertEqual(driver.HEADS['cpu-profile'], '794901899b9cf4172f0af2cdde9fa62aa330edce')
        for mode, target in [('cpu-profile', 'current'), ('idle', 'cpu-profile'),
                             ('load-diagnostic', 'cpu-profile')]:
            with self.subTest(mode=mode, target=target), mock.patch.object(driver, 'initialize_dependencies') as setup:
                with self.assertRaisesRegex(ValueError, 'exact diagnostic target'):
                    driver.run(SimpleNamespace(mode=mode, target=target, idle_only=False))
                setup.assert_not_called()

    def test_normal_test_failure_can_verify_cleanup_without_claiming_test_success(self):
        with tempfile.TemporaryDirectory() as directory:
            parent = Path(directory)
            args, _, signals, stack = self.fake_run(parent, worker_exit=1)
            with stack:
                self.assertEqual(driver.run(args), 1)
            outcome = json.loads((parent / 'trial/outcome.json').read_bytes())
            self.assertEqual(outcome['status'], 'software_test_failed')
            self.assertTrue(outcome['cleanup_verified'])
            self.assertEqual(signals, [])

    def test_killed_worker_never_verifies_cleanup_even_without_observed_survivors(self):
        with tempfile.TemporaryDirectory() as directory:
            parent = Path(directory)
            args, _, signals, stack = self.fake_run(parent, worker_exit=-9)
            with stack, self.assertRaisesRegex(ValueError, 'worker exit and pytest result disagree'):
                driver.run(args)
            outcome = json.loads((parent / 'trial/outcome.json').read_bytes())
            self.assertEqual(outcome['returncode'], -9)
            self.assertFalse(outcome['cleanup_verified'])
            self.assertEqual(signals, [])

    def test_surviving_observed_peer_or_uncertain_identity_retains_cleanup_gate(self):
        for survivor, uncertain in ((True, False), (False, True)):
            with self.subTest(survivor=survivor), tempfile.TemporaryDirectory() as directory:
                parent = Path(directory)
                args, _, signals, stack = self.fake_run(parent, survivor=survivor,
                                                       observation_error=uncertain)
                with stack:
                    self.assertEqual(driver.run(args), 0)
                outcome = json.loads((parent / 'trial/outcome.json').read_bytes())
                self.assertFalse(outcome['cleanup_verified'])
                self.assertEqual(signals, [])
                if survivor:
                    self.assertEqual(outcome['observed_owned_survivors'], [
                        {'pid': 123_457, 'create_time': 123_457.0}])
                else:
                    self.assertTrue(outcome['process_observation_errors'])

    def test_reused_pid_is_not_an_owned_survivor_or_new_ancestry_root(self):
        class InspectionError(Exception):
            pass
        class NoSuchProcess(InspectionError):
            pass
        process = mock.Mock(pid=42)
        process.create_time.side_effect = [1.0, 2.0, 2.0]
        psutil = SimpleNamespace(Process=lambda pid: process, Error=InspectionError,
                                 NoSuchProcess=NoSuchProcess)
        tracker = driver.TrialProcesses(psutil, 42)
        tracker.observe()
        evidence = tracker.evidence()
        self.assertEqual(evidence['observed_owned_survivors'], [])
        self.assertEqual(evidence['reused_observed_pids'], [{'pid': 42, 'create_time': 1.0}])
        process.children.assert_not_called()
        process.is_running.assert_not_called()

    def test_competing_job_starting_midtrial_does_not_count_as_idle_replication(self):
        with tempfile.TemporaryDirectory() as directory:
            parent = Path(directory)
            args, launches, signals, stack = self.fake_run(parent, samples=[host()] * 5 + [host(foreign=99)])
            with stack:
                self.assertEqual(driver.run(args), 4)
            outcome = json.loads((parent / 'trial/outcome.json').read_bytes())
            self.assertEqual(outcome['status'], 'software_test_passed')
            self.assertFalse(outcome['idle_trial_qualified'])

    def test_host_observer_and_its_children_are_excluded_during_gate_and_test(self):
        observed = host()
        observed['processes'].extend([
            {'pid': 777_777, 'ppid': 1, 'cpu_percent': 80, 'name': 'host-observer'},
            {'pid': 777_778, 'ppid': 777_777, 'cpu_percent': 80, 'name': 'ps'},
        ])
        with tempfile.TemporaryDirectory() as directory:
            parent = Path(directory)
            args, _, _, stack = self.fake_run(parent, samples=[observed] * 6)
            with stack:
                self.assertEqual(driver.run(args), 0)
            outcome = json.loads((parent / 'trial/outcome.json').read_bytes())
            self.assertTrue(outcome['idle_trial_qualified'])

    def test_local_bind_must_receive_eperm_and_always_persists_evidence(self):
        for failure, accepted in ((PermissionError(errno.EPERM, 'denied'), True),
                                  (PermissionError(errno.EACCES, 'wrong refusal'), False),
                                  (None, False)):
            with self.subTest(failure=failure), tempfile.TemporaryDirectory() as directory:
                output = Path(directory)
                with mock.patch.object(driver.socket, 'socket') as factory:
                    factory.return_value.__enter__.return_value.bind.side_effect = failure
                    if accepted:
                        self.assertTrue(driver.network_self_check(output)['network_denied'])
                    else:
                        with self.assertRaisesRegex(RuntimeError, 'did not receive EPERM'):
                            driver.network_self_check(output)
                    factory.return_value.__enter__.return_value.bind.assert_called_once_with(('127.0.0.1', 0))
                evidence = json.loads((output / 'network-self-check-driver.json').read_bytes())
                self.assertEqual(evidence['network_denied'], accepted)
                self.assertEqual(evidence['network_bind_denied'], accepted)
                self.assertEqual(evidence['pid'], os.getpid())

    def test_host_sample_write_open_check_never_truncates_or_writes_and_requires_eperm(self):
        for failure, expected in ((PermissionError(errno.EPERM, 'denied'), True),
                                  (PermissionError(errno.EACCES, 'wrong refusal'), False),
                                  (None, False)):
            with self.subTest(failure=failure), \
                    mock.patch.object(driver.os, 'open', return_value=456, side_effect=failure) as opened, \
                    mock.patch.object(driver.os, 'close') as closed, \
                    mock.patch.object(driver.os, 'write') as written:
                proof = driver.host_samples_write_denial(Path('/fixture/observer.jsonl'))
                self.assertEqual(proof['write_open_denied'], expected)
                opened.assert_called_once_with(Path('/fixture/observer.jsonl'), os.O_WRONLY | os.O_NOFOLLOW)
                written.assert_not_called()
                if failure is None:
                    closed.assert_called_once_with(456)
                else:
                    closed.assert_not_called()

    def test_writable_host_samples_refuse_before_gate_or_worker_and_persist_proof(self):
        with tempfile.TemporaryDirectory() as directory:
            parent = Path(directory)
            args, launches, _, stack = self.fake_run(parent)
            with stack, mock.patch.object(driver, 'host_samples_write_denial', return_value={
                    'write_open_denied': False, 'write_open_succeeded': True}), \
                    self.assertRaisesRegex(ValueError, 'write-open self-check'):
                driver.run(args)
            self.assertEqual(launches, [])
            self.assertFalse((parent / 'trial/idle-decision.json').exists())
            outcome = json.loads((parent / 'trial/outcome.json').read_bytes())
            self.assertFalse(outcome['read_only_host_samples']['write_open_denied'])
            self.assertTrue(outcome['cleanup_verified'])

    def test_source_change_cannot_exit_success_after_passing_junit(self):
        with tempfile.TemporaryDirectory() as directory:
            parent = Path(directory)
            args, launches, signals, stack = self.fake_run(parent, after_changed=True)
            with stack, self.assertRaisesRegex(RuntimeError, 'source preservation failed'):
                driver.run(args)
            self.assertEqual(json.loads((parent / 'trial/outcome.json').read_bytes())['status'], 'source_changed')

    def test_outer_watchdog_is_censoring_and_signals_only_its_own_child_group(self):
        with tempfile.TemporaryDirectory() as directory:
            parent = Path(directory)
            args, launches, signals, stack = self.fake_run(parent, hang=True)
            with stack, self.assertRaisesRegex(TimeoutError, 'outer measurement watchdog'):
                driver.run(args)
            self.assertEqual([pid for pid, _ in signals], [123_456])
            outcome = json.loads((parent / 'trial/outcome.json').read_bytes())
            self.assertEqual(outcome['status'], 'measurement_error')
            self.assertTrue(outcome['source_unchanged'])
            self.assertTrue(outcome['cleanup_forced'])
            self.assertFalse(outcome['cleanup_verified'])


class ExternalHostReaderTests(unittest.TestCase):
    PID = 777_777

    def row(self, sequence=1, monotonic=100.0, **updates):
        row = {**host(), 'kind': 'sample', 'observer_pid': self.PID,
               'sequence': sequence, 'monotonic': monotonic, 'at': driver.now()}
        row['processes'].append({'pid': self.PID, 'ppid': 1, 'cpu_percent': 0, 'name': 'observer'})
        return {**row, **updates}

    def write(self, path, rows, *, append=False):
        with path.open('a' if append else 'w', encoding='utf-8') as stream:
            if not append:
                stream.write(json.dumps({'kind': 'observer_start', 'observer_pid': self.PID}) + '\n')
            for row in rows:
                stream.write(json.dumps(row) + '\n')

    def test_latest_fresh_sample_is_unique_and_sequence_history_is_retained(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'samples.jsonl'
            self.write(path, [self.row(1, 90), self.row(2, 100)])
            with mock.patch.object(driver.time, 'monotonic', return_value=100) as clock, \
                    driver.HostSampleReader(path, self.PID) as reader:
                self.assertEqual(reader.sample()['sequence'], 2)
                self.write(path, [self.row(3, 101)], append=True)
                clock.return_value = 101
                self.assertEqual(reader.sample()['sequence'], 3)
                with mock.patch.object(driver.time, 'monotonic', side_effect=itertools.count(100)), \
                        mock.patch.object(driver.time, 'sleep'):
                    with self.assertRaisesRegex(ValueError, 'missing fresh unique'):
                        reader.sample()

    def test_fresh_prestartup_row_is_history_until_a_poststartup_sample_arrives(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'samples.jsonl'
            self.write(path, [self.row(1, 99.9)])
            elapsed = [100.0]
            def publish_new_sample(seconds):
                elapsed[0] += seconds
                self.write(path, [self.row(2, elapsed[0])], append=True)
            with mock.patch.object(driver.time, 'monotonic', side_effect=lambda: elapsed[0]), \
                    mock.patch.object(driver.time, 'sleep', side_effect=publish_new_sample) as sleep, \
                    driver.HostSampleReader(path, self.PID) as reader:
                observed = reader.sample()
                self.assertEqual(observed['sequence'], 2)
                self.assertGreaterEqual(observed['monotonic'], reader.minimum_monotonic)
                sleep.assert_called_once()

    def test_malformed_stale_future_wrong_pid_and_unordered_samples_fail_closed(self):
        cases = [
            [self.row(monotonic=94)], [self.row(monotonic=101)],
            [self.row(observer_pid=self.PID + 1)], [self.row(sequence=2)],
            [self.row(), self.row(sequence=1, monotonic=100.1)],
            [self.row(monotonic=99), self.row(sequence=2, monotonic=98)],
            [self.row(at='not-an-iso-time')], [self.row(at='2026-01-01T00:00:00')],
            [self.row(at='9999-01-01T00:00:00+00:00')], [self.row(processes=[])],
            [self.row(cpu_percent=float('nan'))], [self.row(logical_cpus=True)],
            [{'kind': 'observer_error', 'observer_pid': self.PID, 'error': 'ps failed'}],
        ]
        for rows in cases:
            with self.subTest(rows=rows), tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / 'samples.jsonl'
                self.write(path, rows)
                with mock.patch.object(driver.time, 'monotonic', side_effect=itertools.chain([90], itertools.repeat(100))), \
                        driver.HostSampleReader(path, self.PID) as reader:
                    with self.assertRaises(ValueError):
                        reader.sample()

    def test_missing_replaced_and_truncated_files_fail_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'samples.jsonl'
            with self.assertRaises(FileNotFoundError):
                driver.HostSampleReader(path, self.PID)
            self.write(path, [self.row()])
            with mock.patch.object(driver.time, 'monotonic', return_value=100), \
                    driver.HostSampleReader(path, self.PID) as reader:
                reader.sample()
                replacement = Path(directory) / 'replacement.jsonl'
                self.write(replacement, [self.row(2)])
                replacement.replace(path)
                with self.assertRaisesRegex(ValueError, 'changed inode'):
                    reader.sample()
            self.write(path, [self.row()])
            with mock.patch.object(driver.time, 'monotonic', return_value=100), \
                    driver.HostSampleReader(path, self.PID) as reader:
                reader.sample()
                path.write_text('')
                with self.assertRaisesRegex(ValueError, 'truncated'):
                    reader.sample()

    def test_read_and_line_sizes_are_bounded(self):
        for limit in ('MAX_READ', 'MAX_LINE'):
            with self.subTest(limit=limit), tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / 'samples.jsonl'
                self.write(path, [self.row()])
                with mock.patch.object(driver.time, 'monotonic', return_value=100), \
                        driver.HostSampleReader(path, self.PID) as reader:
                    setattr(reader, limit, 16)
                    with self.assertRaisesRegex(ValueError, 'bounded byte budget'):
                        reader.sample()

    def test_incomplete_line_is_not_a_sample_and_malformed_json_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'samples.jsonl'
            self.write(path, [])
            with path.open('a') as stream:
                stream.write(json.dumps(self.row()))
            with mock.patch.object(driver.time, 'monotonic', side_effect=itertools.count(100)), \
                    mock.patch.object(driver.time, 'sleep'), \
                    driver.HostSampleReader(path, self.PID) as reader:
                with self.assertRaisesRegex(ValueError, 'missing fresh unique'):
                    reader.sample()
            self.write(path, [])
            with path.open('a') as stream:
                stream.write('{broken json}\n')
            with driver.HostSampleReader(path, self.PID) as reader:
                with self.assertRaises(ValueError):
                    reader.sample()


if __name__ == '__main__':
    unittest.main()
