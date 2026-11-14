"""Issue 6233, 2026-11-14: profile read-only stage reconstruction.

Inputs: stopped attempt directory and fresh output directory. Outputs: cProfile
and outcome JSON. No capture_stage, advance or publication call is made. Two
fresh loads model the invocation/publication read boundaries, not a completion
test. The original helper's 180-second limit bounds this diagnostic too.
"""
import argparse
import cProfile
import json
import os
from pathlib import Path
import pstats
import signal
import time


def expired(signum, frame):
    raise TimeoutError('read-only diagnostic reached original 180-second helper bound')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('attempt', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    body = json.loads((args.attempt / 'registration.json').read_text())['registration']
    composition = json.loads(body['composition_raw_json'])
    selected = json.loads(composition['selection_raw_json'])['registration_path']
    os.environ.clear()
    os.environ.update(body['environment'])
    os.chdir(body['working_directory'])
    profiler = cProfile.Profile()
    signal.signal(signal.SIGALRM, expired)
    signal.setitimer(signal.ITIMER_REAL, 180)
    before = time.monotonic()
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
        profiler.disable()
        signal.setitimer(signal.ITIMER_REAL, 0)
        wall = time.monotonic() - before
        profiler.dump_stats(str(args.output / 'reads.pstats'))
        stats = pstats.Stats(profiler)
        rows = [{'file': key[0], 'line': key[1], 'name': key[2],
                 'calls': counts[1], 'self': counts[2], 'inclusive': counts[3]}
                for key, counts in stats.stats.items()]
        rows.sort(key=lambda row: -row['inclusive'])
        (args.output / 'profile.json').write_text(json.dumps(
            {'wall_seconds': wall, 'error': error, 'completed': completed,
             'scope': 'Read-only reconstruction, no stage invocation or publication.',
             'functions': rows}, indent=2))
        with (args.output / 'profile.txt').open('w') as stream:
            stats.stream = stream
            stats.sort_stats('cumulative').print_stats(70)
        print(json.dumps({'wall_seconds': wall, 'error': error, 'completed': completed}))


if __name__ == '__main__':
    main()
