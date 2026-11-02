#!/usr/bin/env python3
"""SG2 stock-CI subprocess deadline contracts, PR #5213, 2026-11-02.

Inputs: sibling stdlib supervisor/profile. Outputs: unittest results and owned
temporary fixtures. No pytest, production imports, providers or network calls.
"""
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch
from types import SimpleNamespace

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import d76_process_deadline_20261102 as deadline


def child(root, mode):
    return ['/usr/bin/sandbox-exec', '-D', 'LOCAL_ROOT=' + str(root), '-f',
            str(HERE / 'd76_loopback_only_20261031.sb'), sys.executable, '-S', '-P', '-B',
            str(Path(__file__).resolve()), mode, str(root)]


class Contracts(unittest.TestCase):
    def execute(self, root, mode, seconds):
        with (root / 'child.log').open('wb') as stream:
            result = deadline.run(child(root, mode), cwd=root, env=dict(os.environ),
                evidence=root / 'supervisor', stream=stream, seconds=seconds)
        return result, json.loads((root / 'supervisor/deadline.json').read_text())

    def test_success_retains_artifacts_without_claiming_timeout(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            result, proof = self.execute(root, '--success', 10)
            self.assertEqual(result.returncode, 0)
            self.assertFalse(result.expired)
            self.assertEqual((root / 'effect.txt').read_text(), 'persisted')
            self.assertFalse(proof['signals'])

    def test_lone_child_is_bounded_and_reaped(self):
        with tempfile.TemporaryDirectory() as temporary:
            result, proof = self.execute(Path(temporary).resolve(), '--wait', 1)
            self.assertTrue(result.expired)
            self.assertNotEqual(result.returncode, 0)
            self.assertTrue(proof['termination_verified'])
            self.assertEqual([row['signal'] for row in proof['signals']], ['SIGTERM', 'SIGKILL'])

    def test_term_ignoring_descendant_cannot_outlive_terminal_result(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            result, proof = self.execute(root, '--spawn', 1)
            self.assertTrue(result.expired)
            self.assertTrue(proof['termination_verified'])
            heartbeat = root / 'heartbeat.txt'
            before = heartbeat.read_bytes()
            self.assertTrue(before)
            time.sleep(0.3)
            self.assertEqual(heartbeat.read_bytes(), before)

    def test_unknown_or_live_group_never_counts_as_retired(self):
        for text, code in [('42 42 Z\n43 42 S\n', 0), ('43 42 Z\n', 0), ('', 1), ('malformed\n', 0)]:
            observation = SimpleNamespace(stdout=text, stderr='', returncode=code)
            with self.subTest(text=text), patch.object(deadline.subprocess, 'run', return_value=observation):
                self.assertFalse(deadline.owned_group_state(42)['all_retired'])

    def test_outer_deadline_retires_nested_group_before_terminal_result(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            result, proof = self.execute(root, '--nested-worker', 2)
            self.assertTrue(result.expired)
            self.assertTrue(proof['termination_verified'])
            nested = json.loads((root / 'nested-supervisor/interruption.json').read_text())
            self.assertTrue(nested['termination_verified'])
            self.assertTrue(nested['group_kill_sent'])
            heartbeat = root / 'heartbeat.txt'
            before = heartbeat.read_bytes()
            self.assertTrue(before)
            time.sleep(0.3)
            self.assertEqual(heartbeat.read_bytes(), before)

    def test_term_during_launch_defers_until_child_ownership_is_available(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            child_process = SimpleNamespace(pid=424242, returncode=None, wait=lambda timeout: -9)

            def launch(*_args, **_kwargs):
                os.kill(os.getpid(), signal.SIGTERM)
                return child_process

            with (root / 'log').open('wb') as stream, \
                    patch.object(deadline.subprocess, 'Popen', side_effect=launch), \
                    patch.object(deadline.os, 'killpg') as kill:
                with self.assertRaises(deadline.ParentTerminated):
                    deadline.run(['fixture'], cwd=root, env={}, evidence=root / 'proof',
                                 stream=stream, seconds=10)
            kill.assert_called_once_with(424242, signal.SIGKILL)
            self.assertTrue(json.loads((root / 'proof/interruption.json').read_text())['termination_verified'])

    def test_term_exception_does_not_take_popens_keyboardinterrupt_reap_path(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()

            class Child:
                pid, returncode, waits = 424242, None, 0

                def wait(self, timeout):
                    self.waits += 1
                    if self.waits == 1:
                        try:
                            os.kill(os.getpid(), signal.SIGTERM)
                        except KeyboardInterrupt:
                            # This is Popen.wait's special path that the custom
                            # TERM exception must never enter before cleanup.
                            self.returncode = 0
                            raise
                    return -9

            child_process = Child()
            with (root / 'log').open('wb') as stream, \
                    patch.object(deadline.subprocess, 'Popen', return_value=child_process), \
                    patch.object(deadline.os, 'killpg') as kill:
                with self.assertRaises(deadline.ParentTerminated):
                    deadline.run(['fixture'], cwd=root, env={}, evidence=root / 'proof',
                                 stream=stream, seconds=10)
            kill.assert_called_once_with(424242, signal.SIGKILL)
            self.assertEqual(child_process.waits, 2)
            self.assertTrue(json.loads((root / 'proof/interruption.json').read_text())['termination_verified'])


if __name__ == '__main__':
    if sys.argv[1:2] == ['--success']:
        (Path(sys.argv[2]) / 'effect.txt').write_text('persisted')
    elif sys.argv[1:2] == ['--wait']:
        time.sleep(30)
    elif sys.argv[1:2] == ['--spawn']:
        subprocess.Popen([sys.executable, '-S', '-P', '-B', str(Path(__file__).resolve()),
                          '--ignore-term', sys.argv[2]])
        time.sleep(30)
    elif sys.argv[1:2] == ['--nested-worker']:
        root = Path(sys.argv[2])
        with (root / 'nested.log').open('wb') as stream:
            deadline.run([sys.executable, '-S', '-P', '-B', str(Path(__file__).resolve()),
                '--spawn', str(root)], cwd=root, env=dict(os.environ),
                evidence=root / 'nested-supervisor', stream=stream, seconds=30)
    elif sys.argv[1:2] == ['--ignore-term']:
        signal.signal(signal.SIGTERM, signal.SIG_IGN)
        while True:
            with (Path(sys.argv[2]) / 'heartbeat.txt').open('a') as stream:
                stream.write('alive\n')
            time.sleep(0.02)
    else:
        unittest.main(verbosity=2)
