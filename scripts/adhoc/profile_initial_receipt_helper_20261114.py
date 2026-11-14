"""Issue 6233, 2026-11-14: profile the read-only initial receipt helper.

Inputs: stopped attempt directory, fresh diagnostic output directory.
Outputs: bounded cProfile statistics, command and outcome JSON. Replays only
the initial-structure command (which rejects writes), never a native/provider.
The original synthetic peer's 180-second helper limit is retained.
"""
import argparse
import cProfile
import json
import os
from pathlib import Path
import pstats
import runpy
import shlex
import signal
import sys
import time


def expired(signum, frame):
    raise TimeoutError('diagnostic reached original 180-second helper bound')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('attempt', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    commands = []
    for line in (args.attempt / 'transcript.jsonl').read_text().splitlines():
        for block in json.loads(line).get('message', {}).get('content', []):
            if block.get('type') == 'tool_use' and block.get('name') == 'Bash':
                command = shlex.split(block['input']['command'])
                if '--initial-structure' in command:
                    commands.append(command)
    if len(commands) != 1:
        raise ValueError('expected exactly one initial receipt command')
    command = commands[0]
    if (command[:3] != [sys.executable, '-m', 'data_sheets_schema.cli']
            or command[5:7] != ['receipts', 'check'] or '--write' in command):
        raise ValueError('not the fixed read-only initial receipt command')
    body = json.loads((args.attempt / 'registration.json').read_text())['registration']
    os.environ.clear()
    os.environ.update(body['environment'])
    os.chdir(body['working_directory'])
    sys.argv = ['data_sheets_schema.cli', *command[3:]]
    profiler = cProfile.Profile()
    signal.signal(signal.SIGALRM, expired)
    signal.setitimer(signal.ITIMER_REAL, 180)
    before = time.monotonic()
    error = None
    try:
        profiler.enable()
        runpy.run_module('data_sheets_schema.cli', run_name='__main__')
    except BaseException as exc:
        error = type(exc).__name__ + ': ' + str(exc)
    finally:
        profiler.disable()
        signal.setitimer(signal.ITIMER_REAL, 0)
        wall = time.monotonic() - before
        profiler.dump_stats(str(args.output / 'helper.pstats'))
        stats = pstats.Stats(profiler)
        rows = [{'file': key[0], 'line': key[1], 'name': key[2],
                 'calls': counts[1], 'self': counts[2], 'inclusive': counts[3]}
                for key, counts in stats.stats.items()]
        rows.sort(key=lambda row: -row['inclusive'])
        (args.output / 'profile.json').write_text(json.dumps(
            {'wall_seconds': wall, 'error': error, 'command': command, 'functions': rows}, indent=2))
        with (args.output / 'profile.txt').open('w') as stream:
            stats.stream = stream
            stats.sort_stats('cumulative').print_stats(70)
        print(json.dumps({'wall_seconds': wall, 'error': error}))


if __name__ == '__main__':
    main()
