#!/usr/bin/env python3
"""#5212 round 6, 2026-11-02: hold an existing sidecar in a real second process.

Input: absolute existing sidecar path, or --exit/--wait diagnostic fixture mode.
Output: READY, then wait for stdin EOF; diagnostic modes exercise wait failures.
Never removes/replaces the inode; no source edits, provider or network use.
"""
from pathlib import Path
import sys

from filelock import FileLock

if sys.argv[1] in ('--exit', '--wait'):
    print('child diagnostic', file=sys.stderr, flush=True)
    if sys.argv[1] == '--exit':
        raise SystemExit(7)
    sys.stdin.read()
    raise SystemExit(0)

path = Path(sys.argv[1])
assert path.is_absolute() and path.is_file() and not path.is_symlink()
with FileLock(path, timeout=0):
    print('READY', flush=True)
    sys.stdin.read()
