"""Read-only C4 basetemp preflight that never opens FIFO fixtures, 2026-11-07.

Inputs: nine completed, explicitly named C4 test runs. Output: a new scratch
inventory of handles, links, special files and regular-file references. No
deletion, Git mutation, network or worktree write. Hidden files are included.
"""
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess

ROOT = Path(__file__).resolve().parents[2]
SCRATCH = ROOT.parent / 'scratch-native-u3c-r4'
RUNS = ('a-core', 'b-focused', 'c-followup', 'c', 'canary-final',
        'canary-migration-final', 'canary-migration', 'canary-protocol', 'canary-stream-final')


def files(root):
    for parent, directories, names in os.walk(root, followlinks=False):
        for name in directories + names:
            yield Path(parent) / name


def regular_bytes(path):
    fd = os.open(path, os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW)
    with os.fdopen(fd, 'rb') as stream:
        if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
            raise ValueError('nonregular file changed during reference scan')
        return stream.read(16 * 1024 * 1024 + 1)


def main():
    all_links = [path for path in files(SCRATCH) if path.is_symlink()]
    rows = []
    for run in RUNS:
        parent, target = SCRATCH / run, SCRATCH / run / 'cases'
        if target != target.resolve(strict=True) or not stat.S_ISDIR(target.lstat().st_mode):
            raise ValueError('not an exact basetemp directory: ' + str(target))
        outcome = json.loads((parent / 'outcome.json').read_bytes())
        if not outcome['cleanup_verified'] or outcome['observed_surviving_pids']:
            raise ValueError('validation descendants remain: ' + run)
        for required in ('pytest.xml', 'pytest.log', 'source-stability.json'):
            if not (parent / required).is_file() or not (parent / required).stat().st_size:
                raise ValueError('missing retained run artifact: ' + run + '/' + required)
        handles = subprocess.run(['/usr/sbin/lsof', '+D', str(target)],
            capture_output=True, text=True, timeout=45)
        if handles.returncode not in (0, 1):
            raise ValueError('lsof failed: ' + run)
        opened = handles.stdout.splitlines()[1:]
        if opened:
            raise ValueError('open basetemp handles: ' + run)
        inbound, internal = [], 0
        for path in all_links:
            resolved = Path(os.path.realpath(path))
            if resolved == target or resolved.is_relative_to(target):
                if path.is_relative_to(target): internal += 1
                else: inbound.append(str(path))
        if inbound:
            raise ValueError('external inbound symlink: ' + repr(inbound))
        kinds, hardlinked, allocated = {}, [], 0
        for path in files(target):
            info = path.lstat()
            kind = ('symlink' if stat.S_ISLNK(info.st_mode) else 'regular' if stat.S_ISREG(info.st_mode)
                    else 'directory' if stat.S_ISDIR(info.st_mode) else 'special')
            kinds[kind] = kinds.get(kind, 0) + 1
            allocated += info.st_blocks * 512
            if kind == 'regular' and info.st_nlink > 1: hardlinked.append(str(path))
        references, skipped = [], []
        needle = str(target).encode()
        for path in files(parent):
            if path.is_relative_to(target) or not stat.S_ISREG(path.lstat().st_mode): continue
            raw = regular_bytes(path)
            if len(raw) > 16 * 1024 * 1024: skipped.append(str(path)); continue
            if needle in raw: references.append(str(path))
        rows.append({'target': str(target), 'open_handles': opened, 'external_inbound_links': inbound,
            'internal_links_removed_together': internal, 'file_kinds': kinds,
            'allocated_bytes_not_exclusive': allocated, 'hardlinked_files': hardlinked,
            'regular_file_references': references, 'large_reference_files_skipped': skipped,
            'reference_scope': str(parent), 'hidden_and_ignored_files_included': True})
    result = {'targets': rows, 'scope': 'Completed synthetic basetemps only; no deletion performed.'}
    output = SCRATCH / 'cleanup-inventory.json'
    raw = (json.dumps(result, indent=2, sort_keys=True) + '\n').encode()
    with output.open('xb') as stream: stream.write(raw)
    assert output.read_bytes() == raw
    print(json.dumps({'path': str(output), 'sha256': hashlib.sha256(raw).hexdigest(),
                      'targets': len(rows)}, sort_keys=True))


if __name__ == '__main__':
    main()
