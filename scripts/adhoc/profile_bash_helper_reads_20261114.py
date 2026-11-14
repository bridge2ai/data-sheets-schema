"""Issue 6233, 2026-11-14: profile read-only stage reconstruction.

Inputs: stopped attempt directory and fresh output directory. Outputs: cProfile
and outcome JSON. No capture_stage, advance or publication call is made. Two
fresh loads model the invocation/publication read boundaries, not a completion
test. A repeating signal requests termination at the selected diagnostic limit. cProfile
uses process CPU time; wall and resource CPU totals are recorded separately.
The first run's ordinary TimeoutError did not unwind promptly; its partial
profile was retained after manual interrupt. A BaseException deadline avoids
ordinary Exception handlers, and repeats in case an inner boundary swallows it.
"""
import argparse
import cProfile
import json
import os
from pathlib import Path
import pstats
import resource
import signal
import time


class ProfileDeadline(BaseException):
    """A diagnostic cancellation, never an authority or data-validation error."""


def expired(signum, frame):
    raise ProfileDeadline('read-only diagnostic deadline reached')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('attempt', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--timeout-seconds', type=float, default=600)
    args = parser.parse_args()
    if not 0 < args.timeout_seconds <= 600:
        parser.error('diagnostic timeout must be positive and no larger than 600')
    args.output.mkdir(parents=True, exist_ok=False)
    body = json.loads((args.attempt / 'registration.json').read_text())['registration']
    composition = json.loads(body['composition_raw_json'])
    selected = json.loads(composition['selection_raw_json'])['registration_path']
    os.environ.clear()
    os.environ.update(body['environment'])
    os.chdir(body['working_directory'])
    profiler = cProfile.Profile(timer=time.process_time)
    signal.signal(signal.SIGALRM, expired)
    signal.setitimer(signal.ITIMER_REAL, args.timeout_seconds, 1)
    before = time.monotonic()
    cpu_before = resource.getrusage(resource.RUSAGE_SELF)
    error, completed = None, []
    try:
        profiler.enable()
        from data_sheets_schema import native_shared_capture_orchestration as capture
        from data_sheets_schema import native_shared_receipts as receipts
        catalogs = receipts._catalog_context()
        for ordinal in range(2):
            run = capture._load_live(selected, _catalogs=catalogs)
            phase, _ = capture.phase_replay(run)
            decision = run.decision()
            completed.append({'ordinal': ordinal, 'phase_passed': phase['passed'],
                              'decision_state': None if decision is None else decision.state,
                              'elapsed': time.monotonic() - before})
    except BaseException as exc:
        error = type(exc).__name__ + ': ' + str(exc)
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        profiler.disable()
        wall = time.monotonic() - before
        cpu_after = resource.getrusage(resource.RUSAGE_SELF)
        profiler.dump_stats(str(args.output / 'reads.pstats'))
        stats = pstats.Stats(profiler)
        rows = [{'file': key[0], 'line': key[1], 'name': key[2],
                 'calls': counts[1], 'self': counts[2], 'inclusive': counts[3]}
                for key, counts in stats.stats.items()]
        rows.sort(key=lambda row: -row['inclusive'])
        (args.output / 'profile.json').write_text(json.dumps(
            {'wall_seconds': wall,
             'cpu_seconds': cpu_after.ru_utime + cpu_after.ru_stime - cpu_before.ru_utime - cpu_before.ru_stime,
             'requested_timeout_seconds': args.timeout_seconds,
             'profile_timer': 'process_time', 'error': error, 'completed': completed,
             'scope': 'Read-only reconstruction, no stage invocation or publication.',
             'functions': rows}, indent=2))
        with (args.output / 'profile.txt').open('w') as stream:
            stats.stream = stream
            stats.sort_stats('cumulative').print_stats(70)
        print(json.dumps({'wall_seconds': wall, 'error': error, 'completed': completed}))


if __name__ == '__main__':
    main()
