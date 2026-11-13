#!/usr/bin/env python3
"""Re-arm and restore the S382f private composition's Git config for one run.

Purpose: the owner approved one more native `cpu-monitoring` diagnostic on the
  existing 382f contract (D132, 2026-11-11). The code under test reads
  `git config --local d4d.ciRepositoryUrl` in the private composition
  repository, which the composer set at composition time and its write-once
  cleanup removed on 2026-11-11T06:08:07Z. The composer cannot set it again
  and its cleanup (and the reviewed cleanup wrapper) refuse to run twice, so
  this helper repeats exactly those two operations with their own evidence,
  leaving every existing record untouched.
    arm      one `git config --local d4d.ciRepositoryUrl <value>` in the
             private tree, accepted only if the result has the configured
             sha256 the composition recorded; otherwise the original bytes
             are put back and the step fails.
    restore  the composer's own restoration: the backup's bytes to a new
             temporary file, fsync, chmod, atomic replace; accepted only if
             the config then equals the backup and the original sha256.
    status   read-only report.
Inputs: scratch-native-u1u3/u3m/composition-382f0dfd1ce8/composition.json (its
  `private_config` row is the only source of paths, hashes, key and value).
Outputs: scratch-native-u1u3/u3m/lead-config-rearm-382f0dfd1ce8-20261111/
  armed-<UTC>.json and restored-<UTC>.json (one pair per arm and restore,
  never overwritten), plus a line of JSON on stdout. Nothing else is written. Undo of `arm` is `restore`; the backup
  config.bak-u3m-20261109 is never modified.
Serves: owner decision D132; native track, not the API route.
Date: 2026-11-11
"""
from __future__ import annotations

import hashlib
import json
import os
import stat
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

EXEC = Path('/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions')
SCRATCH = EXEC / 'scratch-native-u1u3/u3m'
COMPOSITION = SCRATCH / 'composition-382f0dfd1ce8'
MANIFEST = COMPOSITION / 'composition.json'
MANIFEST_SHA = 'fe782d98b04ce7d35e244cd396c7a341b690a4943962db65d96a627bfdcf3a89'
SOURCE_COMMIT = '382f0dfd1ce863fdf257a77e2bbb2637dbe2f67b'
TREE = COMPOSITION / 'tree'
EVIDENCE = SCRATCH / 'lead-config-rearm-382f0dfd1ce8-20261111'
TEMPORARY_NAME = 'config.restore-lead-20261111'
GIT_ENV = {'PATH': '/usr/bin:/bin:/usr/sbin:/sbin', 'GIT_NO_LAZY_FETCH': '1',
           'GIT_ALLOW_PROTOCOL': '', 'GIT_CONFIG_GLOBAL': '/dev/null',
           'GIT_CONFIG_SYSTEM': '/dev/null', 'GIT_OPTIONAL_LOCKS': '0'}


def need(condition, message):
    if not condition:
        raise ValueError(message)


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def regular(path: Path) -> bytes:
    need(path.is_absolute() and path.resolve(strict=True) == path
         and path.is_file() and not path.is_symlink(), 'physical regular file required: ' + str(path))
    return path.read_bytes()


def row():
    raw = regular(MANIFEST)
    need(sha(raw) == MANIFEST_SHA, 'composition manifest bytes differ')
    recorded = json.loads(raw)
    need(recorded['source_commit'] == SOURCE_COMMIT
         and recorded['kind'] == 'native_u3m_private_composition', 'composition identity differs')
    value = recorded['private_config']
    config, backup = Path(value['path']), Path(value['backup'])
    need(config == TREE / '.git/config' and backup == config.with_name('config.bak-u3m-20261109'),
         'private config path differs')
    need(value['key'] == 'd4d.cirepositoryurl' and value['original_mode'] == 0o644,
         'private config row differs')
    return value, config, backup


def save_once(name: str, value: dict) -> str:
    EVIDENCE.mkdir(exist_ok=True)
    need(EVIDENCE.resolve(strict=True) == EVIDENCE, 'evidence directory is aliased')
    path = EVIDENCE / name
    raw = (json.dumps(value, indent=2, sort_keys=True) + '\n').encode()
    with path.open('xb') as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    need(path.read_bytes() == raw, 'evidence did not persist exactly')
    return sha(raw)


def put_back(config: Path, original: bytes, mode: int) -> None:
    temporary = config.with_name(TEMPORARY_NAME)
    need(not os.path.lexists(temporary), 'a restoration is already in progress: ' + str(temporary))
    with temporary.open('xb') as stream:
        stream.write(original)
        stream.flush()
        os.fsync(stream.fileno())
    os.chmod(temporary, mode)
    os.replace(temporary, config)


def state(value, config, backup) -> dict:
    current, saved = regular(config), regular(backup)
    digest = sha(current)
    label = ('original' if digest == value['original_sha256']
             else 'armed' if digest == value['configured_sha256'] else 'unknown')
    return dict(config_sha256=digest, backup_sha256=sha(saved), state=label,
                mode=oct(stat.S_IMODE(config.stat().st_mode)),
                backup_equals_original=sha(saved) == value['original_sha256'])


def arm() -> int:
    value, config, backup = row()
    before = state(value, config, backup)
    need(before['state'] == 'original' and before['backup_equals_original'],
         'config is not in its original state: ' + json.dumps(before))
    original = regular(backup)
    try:
        subprocess.run(['/usr/bin/git', '--no-replace-objects', '-c', 'core.hooksPath=/dev/null',
                        'config', '--local', 'd4d.ciRepositoryUrl', value['value']],
                       cwd=TREE, env=GIT_ENV, check=True, timeout=20)
        after = state(value, config, backup)
        need(after['state'] == 'armed', 'armed bytes differ from the recorded configured sha256')
    except BaseException:
        if sha(config.read_bytes()) != value['original_sha256']:
            put_back(config, original, value['original_mode'])
        raise
    name = 'armed-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ') + '.json'
    digest = save_once(name, dict(status='config_armed', utc=now(), before=before, after=after,
        key='d4d.ciRepositoryUrl', value=value['value'], composition_manifest_sha256=MANIFEST_SHA,
        source_commit=SOURCE_COMMIT, helper_sha256=sha(Path(__file__).read_bytes()),
        authority='owner decision D132, 2026-11-11T16:11:12Z'))
    print(json.dumps(dict(status='config_armed', evidence=str(EVIDENCE / name), sha256=digest, **after)))
    return 0


def restore() -> int:
    value, config, backup = row()
    before = state(value, config, backup)
    need(before['backup_equals_original'], 'backup differs from the recorded original')
    if before['state'] == 'original':
        print(json.dumps(dict(status='already_original', **before)))
        return 0
    need(before['state'] == 'armed',
         'config is neither original nor armed; not overwritten: ' + json.dumps(before))
    original = regular(backup)
    put_back(config, original, value['original_mode'])
    after = state(value, config, backup)
    need(after['state'] == 'original' and config.read_bytes() == original
         and stat.S_IMODE(config.stat().st_mode) == value['original_mode'],
         'private config restoration differs: ' + json.dumps(after))
    name = 'restored-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ') + '.json'
    digest = save_once(name, dict(status='config_restored', utc=now(), before=before, after=after,
        composition_manifest_sha256=MANIFEST_SHA, source_commit=SOURCE_COMMIT,
        helper_sha256=sha(Path(__file__).read_bytes())))
    print(json.dumps(dict(status='config_restored', evidence=str(EVIDENCE / name), sha256=digest, **after)))
    return 0


def status() -> int:
    value, config, backup = row()
    print(json.dumps(state(value, config, backup)))
    return 0


def main() -> int:
    need(len(sys.argv) == 2 and sys.argv[1] in ('arm', 'restore', 'status'),
         'usage: native_private_config_rearm_restore_20261111.py arm|restore|status')
    return {'arm': arm, 'restore': restore, 'status': status}[sys.argv[1]]()


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except ValueError as exc:
        print(json.dumps(dict(status='refused', reason=str(exc))))
        raise SystemExit(2)
