"""Offline serial pytest timing/profiling helper for #5489/#5490, 2026-11-05.

Inputs: pytest node/file arguments and output prefix. Outputs: log, XML,
collection, per-node cumulative profiles and environment metadata. Each child
has a 3600-second deadline. No provider or network calls are permitted.
"""
import argparse
import cProfile
import importlib.metadata
import json
import os
from pathlib import Path
import pstats
import socket
import subprocess
import sys
import threading
import time


class Evidence:
    def __init__(self, prefix, profile, control, sample):
        self.prefix, self.profile, self.control, self.sample = prefix, profile, control, sample
        self.current = None
        self.index = 0

    def pytest_runtest_call(self, item):
        if not self.control:
            return
        patch = item._request.getfixturevalue('monkeypatch')
        if self.control == 'registration':
            from data_sheets_schema import bc1_registration as reg
            original = reg.check_sizing_record

            def ignored_admission(*args, **kwargs):
                try:
                    return original(*args, **kwargs)
                except ValueError as exc:
                    if 'over allowance' not in str(exc) and 'over per-call room' not in str(exc):
                        raise
            patch.setattr(reg, 'check_sizing_record', ignored_admission)
        else:
            from data_sheets_schema import latch_journal as journal
            original = journal._observations

            def omitted_response_pin(data):
                return {key: value for key, value in original(data).items()
                        if not key.startswith('response:typed_audit:')}
            patch.setattr(journal, '_observations', omitted_response_pin)

    def pytest_collection_finish(self, session):
        self.prefix.with_suffix('.nodes.json').write_text(json.dumps([i.nodeid for i in session.items], indent=2))

    def pytest_runtest_logstart(self, nodeid, location):
        if self.profile:
            self.current = cProfile.Profile()
            self.current.enable()
        if self.sample:
            self.stop = threading.Event()
            self.samples = {}
            self.sample_count = 0
            main_thread = threading.get_ident()

            def sample_stack():
                while not self.stop.wait(0.05):
                    frame = sys._current_frames().get(main_thread)
                    stack = set()
                    while frame is not None:
                        code = frame.f_code
                        stack.add((code.co_filename, code.co_firstlineno, code.co_name))
                        frame = frame.f_back
                    for key in stack:
                        self.samples[key] = self.samples.get(key, 0) + 1
                    self.sample_count += 1

            self.sample_start = time.monotonic()
            self.sampler = threading.Thread(target=sample_stack, daemon=True)
            self.sampler.start()

    def pytest_runtest_logfinish(self, nodeid, location):
        if self.current:
            self.current.disable()
            with Path(f'{self.prefix}.{self.index}.profile.txt').open('w') as stream:
                stream.write(nodeid + '\n')
                pstats.Stats(self.current, stream=stream).sort_stats('cumulative').print_stats(65)
            self.current = None
        if self.sample:
            elapsed = time.monotonic() - self.sample_start
            self.stop.set()
            self.sampler.join()
            rows = [{'file': key[0], 'line': key[1], 'function': key[2], 'samples': count,
                     'cumulative_seconds_estimate': elapsed * count / max(1, self.sample_count)}
                    for key, count in sorted(self.samples.items(), key=lambda row: -row[1])]
            Path(f'{self.prefix}.{self.index}.sample.json').write_text(json.dumps({
                'nodeid': nodeid, 'seconds': elapsed, 'samples': self.sample_count,
                'interval_seconds': 0.05, 'inclusive_stack_samples': rows}, indent=2))
        self.index += 1


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--prefix', type=Path, required=True)
    parser.add_argument('--profile', action='store_true')
    parser.add_argument('--sample', action='store_true')
    parser.add_argument('--child', action='store_true')
    parser.add_argument('--control', choices=('registration', 'journal'))
    parser.add_argument('nodes', nargs='+')
    args = parser.parse_args()
    args.prefix.parent.mkdir(parents=True, exist_ok=True)
    if args.child:
        def forbidden(*a, **kw):
            raise AssertionError('network forbidden in BC1 measurement')
        socket.socket.connect = forbidden
        socket.create_connection = forbidden
        import pytest
        return pytest.main([*args.nodes, '-q', '-p', 'no:cacheprovider', '--durations=0',
                            f'--junitxml={args.prefix}.xml'],
                           plugins=[Evidence(args.prefix, args.profile, args.control, args.sample)])
    env = dict(os.environ, PYTHONPATH=str(Path.cwd() / 'src') + os.pathsep + str(Path.cwd()),
               PYTHONPYCACHEPREFIX='/private/tmp/ci-slow-bc1-pycache')
    for key in tuple(env):
        if key.endswith('API_KEY') or key in ('ANTHROPIC_AUTH_TOKEN',):
            env.pop(key)
    metadata = {'python': sys.version, 'executable': sys.executable,
                'packages': sorted((d.metadata['Name'], d.version) for d in importlib.metadata.distributions()),
                'load_before': os.getloadavg(), 'profile': args.profile, 'sample': args.sample}
    start = time.monotonic()
    with args.prefix.with_suffix('.log').open('w') as log:
        result = subprocess.run([sys.executable, __file__, '--child', *sys.argv[1:]],
                                env=env, stdout=log, stderr=subprocess.STDOUT, timeout=3600)
    metadata.update(seconds=time.monotonic() - start, returncode=result.returncode, load_after=os.getloadavg())
    args.prefix.with_suffix('.environment.json').write_text(json.dumps(metadata, indent=2))
    print(json.dumps({k: v for k, v in metadata.items() if k != 'packages'}), flush=True)
    return result.returncode


if __name__ == '__main__':
    raise SystemExit(main())
