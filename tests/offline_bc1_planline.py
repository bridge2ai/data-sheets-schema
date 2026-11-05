"""Offline BC1 plan-line verification runner, 2026-11-05.

Inputs: mode (pytest, scan, cli) and its arguments; outputs: stdout and requested
reports for the BC1 launch-blocker review. Kept under tests because this task
permits edits only to tests and cli/api.py. No provider credentials are retained.
"""
import os
from pathlib import Path
import runpy
import signal
import sys


def main():
    root = Path(__file__).resolve().parents[1]
    scratch = Path('/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-bc1-planline')
    os.environ.clear()
    os.environ.update(PATH='/usr/bin:/bin', HOME=str(scratch),
                      PYTHONPATH=str(root / 'src') + os.pathsep + str(root),
                      PYTHONPYCACHEPREFIX=str(scratch / 'pycache'))
    sys.pycache_prefix = str(scratch / 'pycache')
    sys.path[:0] = [str(root / 'src'), str(root)]

    def deny_network(event, args):
        if event in {'socket.connect', 'socket.connect_ex', 'socket.getaddrinfo', 'socket.sendto'}:
            raise RuntimeError('network denied by offline BC1 verification runner')
    sys.addaudithook(deny_network)
    signal.alarm(3600)
    mode, *args = sys.argv[1:]
    sys.argv = [mode, *args]
    if mode == 'scan':
        runpy.run_path(str(root / '.claude/skills/d4d-generation-specificity-audit/scan.py'), run_name='__main__')
    elif mode == 'pytest':
        runpy.run_module('pytest', run_name='__main__')
    elif mode == 'cli':
        from data_sheets_schema.cli import cli
        cli()
    else:
        raise ValueError(mode)


if __name__ == '__main__':
    main()
