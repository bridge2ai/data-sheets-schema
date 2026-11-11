#!/usr/bin/env python3
"""Preserve only E1/#5755's verified failed partial setup, 2026-11-11.

Inputs: exact first refused manifest/diagnosis and unchanged private index.
Output: exclusive same-parent relocation, unchanged historical bytes/paths in
their records, and a new preservation witness. No deletion, overwrite, source
edit, packet application, test or retry. Run only under the lead's clearance.
"""
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import signal
import stat
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2].parent
SOURCE = ROOT / 'codex-native-u1u3'
PARENT = ROOT / 'scratch-native-u1u3/u3m'
FAILED = PARENT / 'composition-01bdcb22dad6'
RETAINED = PARENT / 'composition-01bdcb22dad6.failed-preparation-0a3d023b4'
HEAD = '01bdcb22dad66da1a167595251b23e6352c97ab7'
MANIFEST_SHA = '985e31929f02cd7ac0e77b57e7f81cc5209747f9896bb810545c75739b2d8d3c'
DIAGNOSIS_SHA = '529e4a80b6c51c1b95cb328c7acf8706bed63678cd638406351c95456296c9aa'
ENV = {'PATH': '/usr/bin:/bin:/usr/sbin:/sbin', 'GIT_NO_LAZY_FETCH': '1',
       'GIT_ALLOW_PROTOCOL': '', 'GIT_OPTIONAL_LOCKS': '0',
       'GIT_CONFIG_SYSTEM': '/dev/null', 'GIT_CONFIG_GLOBAL': '/dev/null'}


def git(cwd, *args):
    return subprocess.check_output(['/usr/bin/git', '--no-replace-objects',
        '-c', 'core.hooksPath=/dev/null', *args], cwd=cwd, env=ENV, timeout=10)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def need(condition, message):
    if not condition:
        raise ValueError(message)


def census(root):
    entries, total = {}, 0
    for directory, directories, files in os.walk(root, followlinks=False):
        for name in [*directories, *files]:
            path = Path(directory) / name
            info = path.lstat()
            need(stat.S_ISDIR(info.st_mode) or stat.S_ISREG(info.st_mode),
                 'unexpected special entry in failed setup')
            if stat.S_ISREG(info.st_mode):
                total += info.st_size
                need(total <= 128 * 1024 * 1024, 'failed-setup census exceeds 128 MiB')
            need(len(entries) < 20000, 'failed-setup census exceeds 20000 entries')
            entries[str(path.relative_to(root))] = dict(device=info.st_dev, inode=info.st_ino,
                mode=info.st_mode, bytes=info.st_size if stat.S_ISREG(info.st_mode) else None,
                sha256=digest(path) if stat.S_ISREG(info.st_mode) else None)
    return entries


def main():
    need(sys.flags.no_site and sys.flags.safe_path and sys.dont_write_bytecode,
         'isolated -I -S -B interpreter required')
    need(not os.path.lexists(ROOT / 'plans/native_quiet_window.lock'), 'quiet-window lock exists')
    need(FAILED.resolve(strict=True) == FAILED and FAILED.is_dir()
         and not os.path.lexists(RETAINED), 'exact fresh preservation destination required')
    need(digest(FAILED / 'composition.json') == MANIFEST_SHA
         and digest(FAILED / 'sparse-index-diagnosis.json') == DIAGNOSIS_SHA,
         'failed evidence identity differs')
    value = json.loads((FAILED / 'composition.json').read_bytes())
    need(value['status'] == 'refused' and value['reason'] == 'sparse index differs from sized selection'
         and value['source_commit'] == HEAD and value['preparation_tools_commit']
         == '0a3d023b4fa0eb29bdc455813d02debeb39a48b0', 'not the one authorized failed setup')
    need(git(SOURCE, 'rev-parse', 'HEAD').decode().strip() == HEAD
         and not git(SOURCE, 'status', '--porcelain').strip(), 'frozen source changed')
    need(all(digest(SOURCE / path) == expected
             for path, expected in value['protected_preimages_sha256'].items()),
         'assigned-source protected preimages differ')
    tree = FAILED / 'tree'
    need(git(tree, 'rev-parse', 'HEAD').decode().strip() == HEAD
         and not git(tree, 'diff', '--cached', '--name-only', HEAD).strip(),
         'private index/HEAD changed after the failed attempt')
    need(not os.path.lexists(tree / '.git/worktrees')
         and not os.path.lexists(PARENT / 'worktree-01bdcb22dad6')
         and not os.path.lexists(PARENT / 'wp1-contract-01bdcb22dad6.json'),
         'a linked tree or contract would be displaced')
    config = git(tree, 'config', '--local', '--null', '--list').split(b'\0')
    need(not any(row.partition(b'\n')[0].lower() == b'd4d.cirepositoryurl' for row in config),
         'private CI configuration was applied')
    before = census(FAILED)
    directory_identity = FAILED.stat()
    helper = SOURCE / 'scripts/adhoc/native_wp1_quiet_20261110.py'
    need(digest(helper) == '787a99a2810c7358a4ba34c272f36c93c892de5d0b22951b5ee81d5847de69fe',
         'reviewed exclusive-rename helper changed')
    cache = PARENT / 'wp1-failed-preservation-cache-01bdcb22dad6'
    need(not os.path.lexists(cache), 'fresh helper cache prefix required')
    sys.pycache_prefix = str(cache)
    spec = importlib.util.spec_from_file_location('wp1_preservation_rename', helper)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    # Existing Darwin RENAME_EXCL helper: no replacement or unlink fallback.
    module._rename_exclusive(FAILED, RETAINED)
    need(not os.path.lexists(FAILED) and RETAINED.is_dir(), 'exclusive relocation did not persist')
    after = census(RETAINED)
    need(before == after and RETAINED.stat().st_ino == directory_identity.st_ino
         and RETAINED.stat().st_dev == directory_identity.st_dev, 'relocated content/identity changed')
    need(digest(RETAINED / 'composition.json') == MANIFEST_SHA
         and digest(RETAINED / 'sparse-index-diagnosis.json') == DIAGNOSIS_SHA,
         'historical evidence changed during preservation')
    witness = dict(original_directory=str(FAILED), retained_directory=str(RETAINED),
        source_commit=HEAD, manifest_sha256=MANIFEST_SHA, diagnosis_sha256=DIAGNOSIS_SHA,
        original_record_paths_unchanged=True, original_status='refused',
        census_unchanged=True, entries=before, source_packet_preimages_unchanged=True,
        helper_sha256=digest(Path(__file__)), ended_utc=datetime.now(timezone.utc).isoformat(),
        scope='Preservation only; no retry, deletion, acceptance or protected installation.')
    target = RETAINED / 'preservation.json'
    with target.open('x') as stream:
        json.dump(witness, stream, indent=2, sort_keys=True)
        stream.write('\n')
    print(str(target) + ' sha256=' + digest(target))


if __name__ == '__main__':
    def expired(number, frame):
        raise TimeoutError('failed-setup preservation exceeded 60 seconds')
    signal.signal(signal.SIGALRM, expired)
    signal.setitimer(signal.ITIMER_REAL, 60)
    main()
