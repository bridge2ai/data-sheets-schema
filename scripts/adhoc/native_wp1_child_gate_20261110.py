#!/usr/bin/env python3
"""WP1-L2 one detached sandbox launch handoff, 2026-11-10.

Inputs: two inherited private pipe descriptors, a one-use nonce and the fixed
sandbox command from the pinned WP1 driver. Output: one readiness message to
the outer supervisor; exec the unchanged sandbox command only after its ACK.
No sockets, network, native executable, environment install or source write.
EOF or deadline before ACK exits without starting any test workload.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import re
import select
import signal
import stat
import time


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--ready-fd', required=True, type=int)
    parser.add_argument('--release-fd', required=True, type=int)
    parser.add_argument('--nonce', required=True)
    parser.add_argument('--deadline', required=True, type=float)
    parser.add_argument('command', nargs=argparse.REMAINDER)
    args = parser.parse_args()
    command = args.command[1:] if args.command[:1] == ['--'] else args.command
    if (len(command) < 8 or command[:2] != ['/usr/bin/sandbox-exec', '-f']
            or command[4:6] != ['-P', '-B']
            or not command[6].endswith('/scripts/adhoc/run_native_wp1_20261110.py')
            or command[7] != '--worker'):
        raise ValueError('WP1 gate admits only the unchanged fixed sandbox worker command')
    remaining = args.deadline - time.monotonic()
    if not math.isfinite(remaining) or not 0 < remaining <= 900:
        raise ValueError('WP1 gate deadline is invalid or expired')
    if not re.fullmatch('[0-9a-f]{64}', args.nonce):
        raise ValueError('WP1 gate requires its private invocation nonce')
    if args.ready_fd == args.release_fd or any(
            fd < 3 or not stat.S_ISFIFO(os.fstat(fd).st_mode)
            for fd in (args.ready_fd, args.release_fd)):
        raise ValueError('WP1 gate requires two distinct inherited pipe descriptors')
    pid = os.getpid()
    if os.getpgid(pid) != pid or os.getsid(pid) != pid:
        raise ValueError('WP1 gate must be leader of its new detached session')
    signal.signal(signal.SIGALRM, lambda number, frame: os._exit(124))
    signal.setitimer(signal.ITIMER_REAL, remaining)
    try:
        ready = (json.dumps({'kind': 'wp1_sandbox_ready', 'nonce': args.nonce,
            'pid': pid, 'ppid': os.getppid(), 'pgid': os.getpgid(pid),
            'sid': os.getsid(pid)}, sort_keys=True) + '\n').encode()
        if len(ready) > 1024 or os.write(args.ready_fd, ready) != len(ready):
            raise RuntimeError('WP1 ownership handoff did not persist to its pipe')
        os.close(args.ready_fd)
        args.ready_fd = -1
        available, _, _ = select.select([args.release_fd], [], [],
            max(0, args.deadline - time.monotonic()))
        if not available:
            return 124
        # One atomic, closed ACK. An outer interruption closes the only writer;
        # EOF is a refusal even if the inner driver has already disappeared.
        if os.read(args.release_fd, 256) != (args.nonce + '\n').encode():
            return 125
        os.close(args.release_fd)
        args.release_fd = -1
        if time.monotonic() >= args.deadline:
            return 124
        signal.setitimer(signal.ITIMER_REAL, 0)
        # Only after verified parent ownership: same command, env and session.
        os.execv(command[0], command)
    finally:
        for fd in (args.ready_fd, args.release_fd):
            if fd >= 0:
                os.close(fd)
        signal.setitimer(signal.ITIMER_REAL, 0)
    return 125


if __name__ == '__main__':
    raise SystemExit(main())
