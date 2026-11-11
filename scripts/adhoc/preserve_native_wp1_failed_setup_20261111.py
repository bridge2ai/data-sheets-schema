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
RETAINED = PARENT / 'composition-01bdcb22dad6.failed-preparation-c8cc4b711'
HEAD = '01bdcb22dad66da1a167595251b23e6352c97ab7'
PRIVATE_HEAD = '6572481c714772402491198f60cd7e3016acb907'
MANIFEST_SHA = 'e6c2c2667c3e3b3412a53ce5e8de45b2eb0b7174971b17993affc40b79c8c63d'
DIAGNOSIS_SHA = '8cdc060a36d5b40378e642afbb2f2c07df56ebe7ed70c83c12da3e0075b4c6b1'
POSTIMAGES = {
    'src/data_sheets_schema/shared_generation.py': '2ec18e60316423035f88a2a30263c56385bfbbc587303e84e805a8349ab4f781',
    'src/data_sheets_schema/api_runner.py': '830eec1e12e96f807fa76ea26e066a1923b60380013c424cfa99f0012af0a881',
    'src/download/prompts/canonical_hashes.yaml': '543e5cd6dc0da0f622ba2cd11a16a90732e9302a1ed0a4700efb61971299d252',
    'tests/utils/run_spec_boundary_contracts.json': 'b1e0cbd14c533a51b88eacb84b974cb93963e18d8f1fb71ae4ed3228f784d1ce',
}
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
         and digest(FAILED / 'stat-cache-diagnosis.json') == DIAGNOSIS_SHA,
         'failed evidence identity differs')
    value = json.loads((FAILED / 'composition.json').read_bytes())
    need(value['status'] == 'refused' and value['reason'] == 'local Git failed: diff-index --quiet ' + PRIVATE_HEAD + ' --\n'
         and value['source_commit'] == HEAD and value['preparation_tools_commit']
         == 'c8cc4b7113d4a9abee9ba4464b1462a02f5124a1', 'not the one authorized failed setup')
    need(git(SOURCE, 'rev-parse', 'HEAD').decode().strip() == HEAD
         and not git(SOURCE, 'status', '--porcelain').strip(), 'frozen source changed')
    need(all(digest(SOURCE / path) == expected
             for path, expected in value['protected_preimages_sha256'].items()),
         'assigned-source protected preimages differ')
    tree = FAILED / 'tree'
    need(git(tree, 'rev-parse', 'HEAD').decode().strip() == PRIVATE_HEAD
         and not git(tree, 'diff', '--cached', '--name-only', PRIVATE_HEAD).strip()
         and set(git(tree, 'diff', '--cached', '--name-only', HEAD).decode().splitlines()) == set(POSTIMAGES),
         'private index/HEAD changed after the failed attempt')
    need(all(digest(tree / path) == expected
             and hashlib.sha256(git(tree, 'show', PRIVATE_HEAD + ':' + path)).hexdigest() == expected
             for path, expected in POSTIMAGES.items()), 'private four-packet postimages differ')
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
         and digest(RETAINED / 'stat-cache-diagnosis.json') == DIAGNOSIS_SHA,
         'historical evidence changed during preservation')
    witness = dict(original_directory=str(FAILED), retained_directory=str(RETAINED),
        source_commit=HEAD, manifest_sha256=MANIFEST_SHA, diagnosis_sha256=DIAGNOSIS_SHA,
        original_record_paths_unchanged=True, original_status='refused',
        private_head=PRIVATE_HEAD, private_packet_postimages_unchanged=True,
        prior_diagnosis_refreshed_stat_cache=True,
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
