#!/usr/bin/env python3
"""PR #5213 / D76 T5: isolate observer evidence from test-owned stdlib patches.

Inputs: the sibling observer; outputs: unittest results and owned temporary JSON.
2026-11-02. No pytest jobs, production imports, providers or existing evidence writes.
"""
from contextlib import contextmanager
import importlib.util
import json
import os
from pathlib import Path
import socket
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))


@contextmanager
def configured_observer(worker='master'):
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        (root / 'source-before.json').write_text('{}\n')
        decorators = SimpleNamespace(hookimpl=lambda **_kw: lambda function: function)
        spec = importlib.util.spec_from_file_location('_d76_observer_io_contract',
            HERE / 'd76_round3_pytest_observer_20261102.py')
        observer = importlib.util.module_from_spec(spec)
        callbacks = []
        with patch.dict(os.environ, {'D76_TREE': str(root), 'D76_OUTPUT': str(root)}, clear=True), \
                patch.dict(sys.modules, {'pytest': decorators}):
            spec.loader.exec_module(observer)
            with patch.object(sys, 'flags', SimpleNamespace(no_site=True, safe_path=True)), \
                    patch.object(sys, 'dont_write_bytecode', True), \
                    patch.object(sys, 'addaudithook', callbacks.append):
                observer.pytest_configure(SimpleNamespace(workerinput={'workerid': worker}))
            try:
                yield observer, root, callbacks
            finally:
                close = getattr(observer, 'pytest_unconfigure', None)
                if close is not None:
                    close(None)


def report(when, *, index=3, node='case', worker='gw2'):
    return SimpleNamespace(nodeid=node, when=when, item_index=index, worker_id=worker,
        outcome='passed', duration=0.01)


@contextmanager
def patched_io():
    def forbidden(*_args, **_kwargs):
        raise AssertionError('test-owned filesystem/serialization purity sentinel')
    # These remain active during the call-report hook, as a monkeypatch fixture
    # does until teardown. Evidence must use its pre-opened streams/encoder.
    with patch.object(Path, 'open', side_effect=forbidden) as path_open, \
            patch.object(Path, 'resolve', side_effect=forbidden), \
            patch('builtins.open', side_effect=forbidden), \
            patch.object(os, 'open', side_effect=forbidden), \
            patch.object(json, 'dumps', side_effect=forbidden), \
            patch.object(json, 'JSONEncoder', side_effect=forbidden):
        yield path_open


class ObserverIOContracts(unittest.TestCase):
    def test_clean_session_does_not_publish_a_denial_artifact(self):
        with configured_observer() as (observer, root, _):
            observer.pytest_runtest_logreport(report('setup', worker='master'))
            with patch.object(observer.common, 'origins', return_value={}):
                observer.pytest_sessionfinish(None, 0)
            self.assertEqual(list(root.glob('guard-denials-*.jsonl')), [])

    def test_late_audit_denials_survive_session_and_plugin_close(self):
        import io
        with configured_observer() as (observer, root, callbacks):
            with patch.object(observer.common, 'origins', return_value={}):
                observer.pytest_sessionfinish(None, 0)
            for close in (lambda: None, lambda: observer.pytest_unconfigure(None)):
                close()
                with patched_io(), patch.object(io, 'open', side_effect=AssertionError('patched io.open')):
                    with self.assertRaisesRegex(RuntimeError, 'offline guard refuses socket.connect'):
                        callbacks[0]('socket.connect', (SimpleNamespace(family=socket.AF_INET), ('192.0.2.1', 443)))
            files = list(root.glob('guard-denials-*.jsonl'))
            self.assertEqual(len(files), 1)
            self.assertEqual([json.loads(line) for line in files[0].read_text().splitlines()],
                [{'event': 'socket.connect', 'detail': 'non-loopback socket'}] * 2)

    def test_failed_phase_write_or_flush_is_fatal_and_not_credited(self):
        for failure in ('write', 'flush'):
            with self.subTest(failure=failure), configured_observer() as (observer, _root, _):
                def denied(*_args):
                    raise OSError('evidence ' + failure + ' failed')
                stream = SimpleNamespace(closed=False, write=lambda _text: None, flush=lambda: None)
                setattr(stream, failure, denied)
                with patch.object(observer, '_PHASE_STREAM', stream):
                    with self.assertRaisesRegex(OSError, 'evidence ' + failure + ' failed'):
                        observer.pytest_runtest_logreport(report('call'))
                self.assertEqual(observer.LEDGER['reports'], [])

    def test_checkpoint_uses_captured_io_and_atomic_replace(self):
        import io
        with configured_observer('gw1') as (observer, root, _):
            observer.LEDGER['selected'] = ['case']
            with patched_io(), patch.object(io, 'open', side_effect=AssertionError('patched io.open')), \
                    patch.object(os, 'replace', side_effect=AssertionError('patched os.replace')):
                observer.checkpoint()
            self.assertEqual(json.loads((root / 'nodes-gw1.json').read_text()), observer.LEDGER)
            self.assertFalse((root / 'nodes-gw1.json.tmp').exists())

    def test_phase_reports_do_not_reopen_or_use_patched_serialization(self):
        with configured_observer('gw2') as (observer, root, _):
            for when in ('setup', 'call', 'teardown'):
                with patched_io() as sentinel:
                    observer.pytest_runtest_logreport(report(when))
                    sentinel.assert_not_called()
                # Verify the side effect before session close: each row is flushed.
                rows = [json.loads(line) for line in (root / 'phases-gw2.jsonl').read_text().splitlines()]
                self.assertEqual([row['when'] for row in rows],
                    ['setup', 'call', 'teardown'][:len(rows)])
                self.assertEqual(len(rows), ('setup', 'call', 'teardown').index(when) + 1)
            self.assertEqual(rows, observer.LEDGER['reports'])
            self.assertTrue(all(row['item_index'] == 3 and row['worker_id'] == 'gw2' for row in rows))
            self.assertFalse((root / 'phases-master.jsonl').exists())

    def test_guard_denial_is_persisted_under_test_owned_io_patches(self):
        with configured_observer() as (observer, root, callbacks):
            self.assertEqual(len(callbacks), 1)
            with patched_io() as sentinel:
                with self.assertRaisesRegex(RuntimeError, 'offline guard refuses socket.connect'):
                    callbacks[0]('socket.connect', (SimpleNamespace(family=socket.AF_INET), ('192.0.2.1', 443)))
                sentinel.assert_not_called()
            files = list(root.glob('guard-denials-*.jsonl'))
            self.assertEqual(len(files), 1)
            self.assertEqual(json.loads(files[0].read_text()),
                {'event': 'socket.connect', 'detail': 'non-loopback socket'})

    def test_session_close_keeps_checkpoint_and_refuses_late_reports(self):
        with configured_observer() as (observer, root, _):
            observer.pytest_runtest_logreport(report('setup', worker='master'))
            with patch.object(observer.common, 'origins', return_value={}):
                observer.pytest_sessionfinish(None, 0)
            saved = json.loads((root / 'nodes-master.json').read_text())
            self.assertTrue(saved['origins_after'])
            self.assertEqual(len(saved['reports']), 1)
            before = (root / 'phases-master.jsonl').read_bytes()
            with self.assertRaisesRegex(RuntimeError, 'evidence.*closed'):
                observer.pytest_runtest_logreport(report('call', worker='master'))
            self.assertEqual((root / 'phases-master.jsonl').read_bytes(), before)
            self.assertEqual(len(observer.LEDGER['reports']), 1)

    def test_failed_final_origin_proof_closes_streams_without_suppressing_error(self):
        with configured_observer() as (observer, root, _):
            with patch.object(observer.common, 'origins', side_effect=OSError('origin proof unavailable')):
                with self.assertRaisesRegex(OSError, 'origin proof unavailable'):
                    observer.pytest_sessionfinish(None, 1)
            self.assertFalse(json.loads((root / 'nodes-master.json').read_text())['origins_after'])
            with self.assertRaisesRegex(RuntimeError, 'evidence.*closed'):
                observer.pytest_runtest_logreport(report('call', worker='master'))


if __name__ == '__main__':
    unittest.main()
