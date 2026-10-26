"""Offline safety tests for the recorder baseline driver; no acceptance test runs."""
from contextlib import ExitStack
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
        self.assertNotIn('PYTEST_DISABLE_PLUGIN_AUTOLOAD', enabled)
        self.assertEqual(disabled['PYTEST_DISABLE_PLUGIN_AUTOLOAD'], '1')

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

    def fake_run(self, parent, *, samples=None, after_changed=False, hang=False, idle_only=False):
        tree = parent / 'tree'; tree.mkdir()
        before = {'head': driver.HEADS['current'], 'pristine': True, 'files': {}, 'tree': 'fixture'}
        after = {**before, 'tree': 'changed'} if after_changed else before
        args = SimpleNamespace(tree=tree, python=Path(sys.executable), output=parent,
            trial='trial', target='current', idle_seconds=5, mode='idle', idle_only=idle_only,
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
                return None if hang or self.polls == 1 else 0
            def wait(self, timeout=None):
                self.returncode = 130 if hang else 0
                return self.returncode

        def launch(command, **kwargs):
            launches.append((command, kwargs))
            output = parent / 'trial'
            (output / 'pytest.xml').write_text('<testsuites><testsuite><testcase classname="tests.test_native_shared_execution" name="' + node + '"/></testsuite></testsuites>')
            for name in ('origins-before.json', 'origins-after.json', 'environment-worker.json'):
                (output / name).write_text('{"modules": {}}')
            (output / 'worker-result.json').write_text('{"returncode":0,"pytest_wall_seconds":1}')
            return Process()

        stack = ExitStack()
        stack.enter_context(mock.patch.object(driver, 'source_identity', side_effect=[before, before, after] if not idle_only else [before, after]))
        stack.enter_context(mock.patch.object(driver, 'host_sample', side_effect=samples if samples is not None else lambda _: host()))
        stack.enter_context(mock.patch.object(driver.subprocess, 'Popen', side_effect=launch))
        stack.enter_context(mock.patch.object(driver.time, 'sleep', return_value=None))
        stack.enter_context(mock.patch.dict(sys.modules, {'psutil': SimpleNamespace(cpu_percent=lambda **kw: 0)}))
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
            self.assertEqual(signals, [])
            outcome = json.loads((parent / 'trial/outcome.json').read_bytes())
            self.assertTrue(outcome['source_unchanged'])
            self.assertTrue(outcome['idle_trial_qualified'])
            self.assertEqual(outcome['junit']['tests'], 1)

    def test_idle_only_and_busy_preflight_never_launch_a_test(self):
        for busy in (False, True):
            with self.subTest(busy=busy), tempfile.TemporaryDirectory() as directory:
                parent = Path(directory)
                args, launches, signals, stack = self.fake_run(parent, samples=[host(foreign=99 if busy else None)] * 5, idle_only=True)
                with stack:
                    self.assertEqual(driver.run(args), 3 if busy else 0)
                self.assertEqual(launches, [])
                self.assertFalse((parent / 'trial/cases').exists())

    def test_competing_job_starting_midtrial_does_not_count_as_idle_replication(self):
        with tempfile.TemporaryDirectory() as directory:
            parent = Path(directory)
            args, launches, signals, stack = self.fake_run(parent, samples=[host()] * 5 + [host(foreign=99)])
            with stack:
                self.assertEqual(driver.run(args), 4)
            outcome = json.loads((parent / 'trial/outcome.json').read_bytes())
            self.assertEqual(outcome['status'], 'software_test_passed')
            self.assertFalse(outcome['idle_trial_qualified'])

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


if __name__ == '__main__':
    unittest.main()
