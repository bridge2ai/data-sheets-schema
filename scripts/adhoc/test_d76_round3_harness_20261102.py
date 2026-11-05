#!/usr/bin/env python3
"""Offline contracts for D76 archive/deadline/CI helpers, 2026-11-02.

Inputs: sibling helper files; outputs: unittest results and owned temporary files.
No production imports, providers, remote git, or mutations to existing evidence.
Run with the existing virtualenv interpreter and -S -P -B.
"""
import io
import json
import os
from pathlib import Path
import subprocess
import signal
import sys
import tarfile
import tempfile
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import archive_d76_round3_source_20261102 as archive_source
import run_d76_round3_validation_20261102 as runner
import d76_round3_hygiene_20261102 as hygiene


def options(**changes):
    values = dict(collect_only=False, notes_ci_job=None, tree=Path('/source'),
        output=Path('/evidence'), workers=0, ci_shard=None, ci_lane=None, metrics=False)
    return SimpleNamespace(**(values | changes))


def tar_members(*members):
    raw = io.BytesIO()
    with tarfile.open(fileobj=raw, mode='w') as archive:
        for name, kind, link in members:
            item = tarfile.TarInfo(name)
            item.type = kind
            item.linkname = link
            archive.addfile(item)
    raw.seek(0)
    return tarfile.open(fileobj=raw, mode='r:')


def sandbox_child(root, mode, *args):
    # Match the actual driver: supervisor outside the profile, child and all
    # descendants inside it. Sandboxing the supervisor changes killpg semantics.
    return ['/usr/bin/sandbox-exec', '-D', 'LOCAL_ROOT=' + str(root), '-f', str(runner.PROFILE),
            sys.executable, '-S', '-P', '-B', str(Path(__file__).resolve()), mode, *args]


class ArchiveContracts(unittest.TestCase):
    def test_regular_files_directories_and_internal_symlinks(self):
        with tar_members(('src', tarfile.DIRTYPE, ''), ('src/code.py', tarfile.REGTYPE, ''),
                         ('link.py', tarfile.SYMTYPE, 'src/code.py')) as archive:
            self.assertEqual(len(archive_source.safe_members(archive)), 3)

    def test_absolute_or_traversing_or_git_paths_refuse(self):
        for name in ('/escape', '../escape', '.git/config', 'src/../escape'):
            with self.subTest(name=name), tar_members((name, tarfile.REGTYPE, '')) as archive:
                with self.assertRaises(ValueError):
                    archive_source.safe_members(archive)

    def test_escaping_symlink_refuses(self):
        for link in ('/escape', '../escape'):
            with self.subTest(link=link), tar_members(('link', tarfile.SYMTYPE, link)) as archive:
                with self.assertRaises(ValueError):
                    archive_source.safe_members(archive)

    def test_descendant_beneath_symlink_refuses(self):
        with tar_members(('link', tarfile.SYMTYPE, 'src'), ('link/code.py', tarfile.REGTYPE, '')) as archive:
            with self.assertRaises(ValueError):
                archive_source.safe_members(archive)

    def test_hardlink_and_devices_refuse(self):
        for kind in (tarfile.LNKTYPE, tarfile.CHRTYPE, tarfile.FIFOTYPE):
            with self.subTest(kind=kind), tar_members(('x', kind, 'src')) as archive:
                with self.assertRaises(ValueError):
                    archive_source.safe_members(archive)

    def test_duplicate_member_refuses(self):
        with tar_members(('x', tarfile.REGTYPE, ''), ('x', tarfile.REGTYPE, '')) as archive:
            with self.assertRaises(ValueError):
                archive_source.safe_members(archive)

    def test_local_archive_populates_exact_files_and_detached_index(self):
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary).resolve()
            repository = base / 'repository'
            repository.mkdir()
            archive_source.git(repository, 'init', '--quiet', '--template=')
            source = repository / 'sample.sh'
            source.write_text('#!/bin/sh\nprintf sample\n')
            source.chmod(0o755)
            archive_source.git(repository, 'add', 'sample.sh')
            archive_source.git(repository, '-c', 'user.name=D76 local contract', '-c',
                'user.email=offline@example.invalid', 'commit', '--quiet', '-m', 'local fixture')
            head = archive_source.value(repository, 'rev-parse', 'HEAD')
            destination = base / 'copy'
            report = archive_source.archive_one(repository, head, destination, base / 'source.tar')
            self.assertEqual((destination / 'sample.sh').read_bytes(), source.read_bytes())
            self.assertTrue((destination / 'sample.sh').stat().st_mode & 0o111)
            self.assertEqual(archive_source.value(destination, 'rev-parse', 'HEAD'), head)
            self.assertEqual(archive_source.value(destination, 'status', '--porcelain'), '')
            self.assertEqual(report['archive_sha256'], archive_source.sha(base / 'source.tar'))
            self.assertEqual(runner.archive_sha(base / 'source.tar'), report['archive_sha256'])


class CommandContracts(unittest.TestCase):
    def test_all_six_pr_shards_exact_selector_and_bounded_workers(self):
        for number in range(1, 7):
            argv = runner.command(options(ci_shard=number, workers=3), ['tests'])
            self.assertIn('--ci-shard=' + str(number) + '/6', argv)
            self.assertIn('--ci-lane=ordinary', argv)
            self.assertEqual(argv[argv.index('-n') + 1], '3')
            self.assertIn('--dist=load', argv)
            self.assertIn('--maxschedchunk=1', argv)

    def test_invalid_shard_or_mixed_api_lane_refuses(self):
        for values in ({'ci_shard': 7}, {'ci_shard': 1, 'ci_lane': 'routing-dispatch'}):
            with self.assertRaises(ValueError):
                runner.command(options(**values), ['tests'])

    def test_four_api_lanes_are_serial_without_shard(self):
        for lane in ('routing-dispatch', 'routing-portable', 'routing-regate', 'routing-default-layout'):
            argv = runner.command(options(ci_lane=lane), ['tests'])
            self.assertIn('--ci-lane=' + lane, argv)
            self.assertNotIn('-n', argv)
            with self.assertRaises(ValueError):
                runner.command(options(ci_lane=lane, workers=3), ['tests'])

    def test_notes_rosters_remain_separate(self):
        for job, targets in hygiene.NOTES_TARGETS.items():
            hygiene.validate_targets(job, list(targets))
        with self.assertRaises(ValueError):
            hygiene.validate_targets('ci-offline-evaluation', [hygiene.NOTES_TARGETS['ci-offline-canary-native'][0]])
        self.assertFalse(hygiene.permits_bytecode('ci-offline-evaluation'))
        self.assertEqual(hygiene.ci_paths('ci-offline-canary-budget'), ('src',))
        self.assertNotIn(hygiene.MATCHED + '/evaluation_controls', hygiene.ci_paths('ci-offline-audit'))

    def test_notes_children_start_without_a_bytecode_cache_prefix(self):
        for job in hygiene.NOTES_TARGETS:
            with self.subTest(job=job), patch.dict(os.environ,
                    {'PYTHONPYCACHEPREFIX': '/inherited-cache'}, clear=True):
                env, removed = runner.scrubbed_environment(options(notes_ci_job=job))
                self.assertIn('PYTHONPYCACHEPREFIX', removed)
                self.assertNotIn('PYTHONPYCACHEPREFIX', env)
                self.assertEqual(env['PYTHONDONTWRITEBYTECODE'], '1')
                observed = subprocess.check_output([sys.executable, '-S', '-P', '-B',
                    str(Path(__file__).resolve()), '--cache-prefix-contract'],
                    env=env, text=True)
                self.assertEqual(json.loads(observed),
                    {'prefix': None, 'dont_write_bytecode': True})

    def test_ordinary_children_retain_the_external_cache_prefix(self):
        with patch.dict(os.environ,
                {'PYTHONPYCACHEPREFIX': '/inherited-cache'}, clear=True):
            env, removed = runner.scrubbed_environment(options())
            self.assertIn('PYTHONPYCACHEPREFIX', removed)
            self.assertEqual(env['PYTHONPYCACHEPREFIX'], '/evidence/pycache')
            self.assertEqual(env['PYTHONDONTWRITEBYTECODE'], '1')

    def test_missing_or_partial_junit_does_not_fabricate_passes(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / 'partial.xml'
            self.assertEqual(runner.case_counts(path)[0], [])
            path.write_text('<testsuite><testcase')
            self.assertEqual(runner.case_counts(path)[0], [])

    def test_interrupted_journal_retains_only_complete_rows_and_reports_refusal(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / 'phases-master.jsonl'
            valid = json.dumps({'nodeid': 'one', 'when': 'setup', 'outcome': 'passed'}).encode() + b'\n'
            raw = valid + b'{"nodeid": "one", "when": "ca'
            path.write_bytes(raw)
            rows, proof = runner.phase_journal(path)
            self.assertEqual(len(rows), 1)
            self.assertFalse(proof['passed'])
            self.assertEqual(proof['malformed_rows'][0]['line'], 2)
            self.assertEqual(path.read_bytes(), raw)

    def test_malformed_nonfinal_journal_row_is_not_silently_ignored(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / 'phases-master.jsonl'
            path.write_text('invalid\n' + json.dumps({'nodeid': 'one', 'when': 'setup', 'outcome': 'passed'}) + '\n')
            rows, proof = runner.phase_journal(path)
            self.assertEqual(len(rows), 1)
            self.assertFalse(proof['passed'])
            self.assertEqual(proof['malformed_rows'][0]['line'], 1)

    def test_malformed_shapes_cannot_crash_real_phase_accounting(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / 'phases-master.jsonl'
            valid = {'nodeid': 'one', 'when': 'setup', 'outcome': 'passed', 'item_index': 0}
            malformed = [valid | {'when': []}, valid | {'outcome': []},
                         valid | {'item_index': []}, valid | {'item_index': True},
                         valid | {'item_index': -1}, {'nodeid': 'one', 'when': 'setup'}]
            rows = [*malformed, valid, valid | {'when': 'call'}, valid | {'when': 'teardown'}]
            path.write_text(''.join(json.dumps(row) + '\n' for row in rows))
            accepted, proof = runner.phase_journal(path)
            self.assertEqual(len(proof['malformed_rows']), 6)
            self.assertFalse(proof['passed'])
            self.assertEqual(runner.phase_accounting(['one'], accepted)['counts']['passed'], 1)


class DeadlineContracts(unittest.TestCase):
    def test_owned_child_deadline_is_retained_as_failure(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            config = SimpleNamespace(tree=root, output=root, deadline_seconds=1, metrics=False)
            with (root / 'child.log').open('wb') as stream:
                code, expired = runner.execute_bounded(sandbox_child(root, '--deadline-child'),
                    config, dict(os.environ), stream)
            self.assertTrue(expired)
            self.assertNotEqual(code, 0)
            record = json.loads((root / 'deadline.json').read_text())
            self.assertTrue(record['expired'])
            self.assertEqual(record['signals'][0]['signal'], 'SIGTERM')
            self.assertEqual(record['signals'][-1]['signal'], 'SIGKILL')
            self.assertTrue(record['termination_verified'])
            for entry in record['signals']:
                if 'group_state_before_reap' in entry:
                    self.assertTrue(entry['group_state_before_reap']['all_retired'])
            self.assertIn('started', (root / 'child.log').read_text())

    def test_term_ignoring_descendant_stops_before_terminal_result(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            config = SimpleNamespace(tree=root, output=root, deadline_seconds=1, metrics=False)
            with (root / 'child.log').open('wb') as stream:
                _, expired = runner.execute_bounded(sandbox_child(root, '--deadline-parent', str(root)),
                    config, dict(os.environ), stream)
            self.assertTrue(expired)
            heartbeat = root / 'heartbeat.txt'
            self.assertTrue(heartbeat.is_file())
            first = heartbeat.read_bytes()
            time.sleep(0.3)
            self.assertEqual(heartbeat.read_bytes(), first)
            self.assertIn('SIGKILL', [row['signal'] for row in json.loads((root / 'deadline.json').read_text())['signals']])

    def test_group_observation_requires_owned_leader_and_no_live_members(self):
        for stdout, expected in [('42 42 Z\n43 42 Z\n', True), ('42 42 Z\n43 42 S\n', False),
                                 ('43 42 Z\n', False), ('42 42 R\n', False)]:
            observation = SimpleNamespace(stdout=stdout, stderr='', returncode=0)
            with self.subTest(stdout=stdout), patch.object(runner.subprocess, 'run', return_value=observation):
                self.assertEqual(runner.owned_group_state(42)['all_retired'], expected)

    def test_unavailable_group_observation_never_proves_retirement(self):
        observation = SimpleNamespace(stdout='', stderr='not permitted', returncode=1)
        with patch.object(runner.subprocess, 'run', return_value=observation):
            self.assertFalse(runner.owned_group_state(42)['all_retired'])

    def test_unverified_group_refusal_is_persisted_without_reaping(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            config = SimpleNamespace(tree=root, output=root, deadline_seconds=1, metrics=False)
            from unittest.mock import Mock
            child = Mock(pid=42)
            with (root / 'child.log').open('wb') as stream, \
                    patch.object(runner.subprocess, 'Popen', return_value=child), \
                    patch.object(runner.time, 'monotonic', side_effect=[0, 2]), \
                    patch.object(runner.time, 'sleep'), \
                    patch.object(runner.os, 'killpg', side_effect=[None, PermissionError('denied')]), \
                    patch.object(runner, 'owned_group_state', return_value={'all_retired': False}):
                with self.assertRaisesRegex(RuntimeError, 'retirement is unverified'):
                    runner.execute_bounded(['owned-only-fixture'], config, {}, stream)
            child.wait.assert_not_called()
            self.assertFalse(json.loads((root / 'deadline.json').read_text())['termination_verified'])


if __name__ == '__main__':
    if sys.argv[1:] == ['--cache-prefix-contract']:
        print(json.dumps({'prefix': sys.pycache_prefix,
                          'dont_write_bytecode': sys.dont_write_bytecode}))
    elif sys.argv[1:] == ['--deadline-child']:
        print('started', flush=True)
        time.sleep(5)
    elif sys.argv[1:2] == ['--deadline-parent']:
        subprocess.Popen([sys.executable, '-S', '-P', '-B', str(Path(__file__).resolve()),
                          '--deadline-descendant', sys.argv[2]])
        print('parent started', flush=True)
        time.sleep(30)
    elif sys.argv[1:2] == ['--deadline-descendant']:
        signal.signal(signal.SIGTERM, signal.SIG_IGN)
        heartbeat = Path(sys.argv[2]) / 'heartbeat.txt'
        while True:
            with heartbeat.open('a') as stream:
                stream.write('alive\n')
            time.sleep(0.02)
    else:
        unittest.main()
