#!/usr/bin/env python3
"""Read-only E1/#5755 second preparation diagnosis, 2026-11-11.

Input: the exact retained c8cc preparation failure. Output: a fresh JSON beside
its manifest. Hash all selected regular bytes against the index, compare Git's
stat-only and content-aware views; never refresh/write the private index.
"""
import hashlib
import json
import os
from pathlib import Path
import signal
import stat
import subprocess

ROOT = Path(__file__).resolve().parents[2].parent
FAILED = ROOT / 'scratch-native-u1u3/u3m/composition-01bdcb22dad6'
EXPECTED_MANIFEST = 'e6c2c2667c3e3b3412a53ce5e8de45b2eb0b7174971b17993affc40b79c8c63d'
EXPECTED_HEAD = '6572481c714772402491198f60cd7e3016acb907'
ENV = {'PATH': '/usr/bin:/bin:/usr/sbin:/sbin', 'GIT_NO_LAZY_FETCH': '1',
       'GIT_ALLOW_PROTOCOL': '', 'GIT_OPTIONAL_LOCKS': '0',
       'GIT_CONFIG_SYSTEM': '/dev/null', 'GIT_CONFIG_GLOBAL': '/dev/null'}


def git(*args):
    return subprocess.check_output(['/usr/bin/git', '--no-replace-objects',
        '--no-optional-locks', '-c', 'core.hooksPath=/dev/null', *args],
        cwd=FAILED / 'tree', env=ENV, timeout=10)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def main():
    if os.path.lexists(ROOT / 'plans/native_quiet_window.lock'):
        raise ValueError('quiet-window lock exists')
    manifest = (FAILED / 'composition.json').read_bytes()
    if sha(manifest) != EXPECTED_MANIFEST or git('rev-parse', 'HEAD').decode().strip() != EXPECTED_HEAD:
        raise ValueError('not the exact retained second failure')
    index = FAILED / 'tree/.git/index'
    before_index = index.read_bytes()
    expected, actual, mismatches, total = set(), set(), [], 0
    value = json.loads(manifest)
    for row in git('ls-tree', '-r', '-z', 'HEAD').split(b'\0'):
        if not row:
            continue
        meta, raw_path = row.split(b'\t', 1)
        mode, kind, oid = meta.split()
        path = raw_path.decode()
        if kind == b'blob' and ('/' not in path or path in value['sparse_controller_files']
                or any(path.startswith(prefix + '/') for prefix in value['sparse_directories'])):
            expected.add(path)
    for row in git('ls-files', '-t', '--stage', '-z').split(b'\0'):
        if not row or row[:2] != b'H ':
            continue
        meta, raw_path = row[2:].split(b'\t', 1)
        mode, oid, stage = meta.split()
        if mode == b'160000':
            continue
        path = raw_path.decode()
        target = FAILED / 'tree' / path
        info = target.lstat()
        if mode not in {b'100644', b'100755'} or stage != b'0' or not stat.S_ISREG(info.st_mode):
            raise ValueError('unexpected selected index entry: ' + path)
        total += info.st_size
        if total > 128 * 1024 * 1024 or len(actual) >= 20000:
            raise ValueError('bounded read census exceeded')
        raw = target.read_bytes()
        observed = hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()
        actual.add(path)
        if observed != oid.decode() or bool(info.st_mode & 0o111) != (mode == b'100755'):
            mismatches.append(path)
    raw_diff = git('diff-index', '--raw', 'HEAD', '--')
    status = git('status', '--porcelain')
    content_diff = git('diff', '--no-ext-diff', '--no-textconv', '--stat')
    debug = git('ls-files', '--debug', '--', 'tests/utils/native_profile_stability.py',
                'src/data_sheets_schema/api_runner.py')
    result = dict(manifest_sha256=EXPECTED_MANIFEST, private_head=EXPECTED_HEAD,
        selected_regular_files=len(actual), selected_bytes=total,
        selected_roster_exact=actual == expected, byte_or_executable_mode_mismatches=mismatches,
        diff_index_raw_entries=len(raw_diff.splitlines()), diff_index_raw_sha256=sha(raw_diff),
        content_aware_status=status.decode(), content_diff_stat=content_diff.decode(),
        index_debug_examples=debug.decode(), index_sha256=sha(before_index),
        index_unchanged=index.read_bytes() == before_index,
        manifest_unchanged=(FAILED / 'composition.json').read_bytes() == manifest,
        script_sha256=sha(Path(__file__).read_bytes()),
        scope='Read-only artifact diagnosis; no index refresh, test, setup or retry.')
    out = FAILED / 'stat-cache-diagnosis.json'
    with out.open('x') as stream:
        json.dump(result, stream, indent=2, sort_keys=True)
        stream.write('\n')
    print(json.dumps(result, indent=2, sort_keys=True))
    print('diagnosis_sha256=' + sha(out.read_bytes()))


if __name__ == '__main__':
    def expired(number, frame):
        raise TimeoutError('read-only diagnosis exceeded 60 seconds')
    signal.signal(signal.SIGALRM, expired)
    signal.setitimer(signal.ITIMER_REAL, 60)
    main()
