#!/usr/bin/env python3
"""Reactivate/restore the exact E4 private config; E1/#5755, 2026-11-11.

Inputs: frozen 3cc113e2606c source, successful canary, retained composition and
backup. Outputs: one fresh activation/restoration witness and config only.
No imports from the source, recomposition, tests, launch or network operation.
Adapted from verify_native_wp1_cleanup_20261111.py's exact config round trip.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
from datetime import datetime, timezone

TOOLS = Path(__file__).resolve().parents[2]
SOURCE = TOOLS.parent / 'codex-native-u1u3'
SCRATCH = TOOLS.parent / 'scratch-native-u1u3/u3m'
HEAD = '3cc113e2606c563236d9c06098c5329ddd027a38'
COMPOSITION = SCRATCH / 'composition-3cc113e2606c'
EVIDENCE = COMPOSITION / 'cpu-diagnostic-config-r2'
CONFIG = COMPOSITION / 'tree/.git/config'
BACKUP = CONFIG.with_name('config.bak-u3m-20261109')
ORIGINAL = '95a1f7d19be439847af9384dfe1a1f7678aa0902b1601b24c56cc60d783388b1'
CONFIGURED = '8a96cf34356a4adffb3c4cf8f07358fcde3857c9a2ed57a1c15cb9822f329b76'
CANARY = SCRATCH / 'wp1-3cc113e2606c-canary-e1-cpu-equivalence-20261111'
PINS = {
    COMPOSITION / 'composition.json': '40ecd24af16c7e28838c7a25da4be61ec1ec2fb8a928287df05e0b962ae30e3d',
    COMPOSITION / 'config-restored.json': 'a03f67b3a2794061a44799ef9a1f65a0f16c535eb3875f8af74de2a192e957c0',
    SCRATCH / 'wp1-contract-3cc113e2606c.json': '14c565b694deefb2a9f91d9de9ef31942be73fe5e1b9c6b1aed15e42bfe06ea7',
    CANARY.with_suffix('.outer.json'): 'd19af6dfb09dbc595a63f4842181c27187dc3f0a30c397c75e3ccc0e36e4dea7',
    CANARY.with_suffix('.supervisor.json'): 'a34e6601fd4150c2e75c7ef316fe9a397646f3837f913aa4c9ac7d79a5f2d262',
    CANARY / 'pytest.xml': '66de5acaf0cb7ece2321ac7363f66fe0337a96c6324d1b4d6ea04043cb78827c',
}
ENV = {'PATH': '/usr/bin:/bin:/usr/sbin:/sbin', 'LANG': 'en_US.UTF-8',
       'GIT_ALLOW_PROTOCOL': '', 'GIT_NO_LAZY_FETCH': '1', 'GIT_OPTIONAL_LOCKS': '0',
       'GIT_CONFIG_SYSTEM': '/dev/null', 'GIT_CONFIG_GLOBAL': '/dev/null'}


def need(value, message):
    if not value:
        raise ValueError(message)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def regular(path):
    need(path.resolve(strict=True) == path and stat.S_ISREG(path.lstat().st_mode),
         'physical regular file required: ' + str(path))
    return path.read_bytes()


def write_new(path, raw):
    with path.open('xb') as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    need(regular(path) == raw, 'written bytes differ: ' + str(path))


def git(*args, cwd=TOOLS):
    return subprocess.check_output(['/usr/bin/git', '--no-replace-objects',
        '--no-optional-locks', '-c', 'core.hooksPath=/dev/null',
        '-c', 'diff.autoRefreshIndex=false', *args], cwd=cwd, env=ENV, timeout=5)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('activate', 'restore'))
    args = parser.parse_args()
    need(sys.flags.no_site and sys.flags.safe_path and sys.dont_write_bytecode,
         '-S -P -B required')
    need(TOOLS.resolve(strict=True) == TOOLS, 'physical tools worktree required')
    tool_head = git('rev-parse', 'HEAD').decode().strip()
    own_path = str(Path(__file__).resolve().relative_to(TOOLS))
    need(not git('status', '--porcelain').strip()
         and git('show', tool_head + ':' + own_path) == regular(Path(__file__).resolve()),
         'clean committed tools required')
    for path, digest in PINS.items():
        need(sha(regular(path)) == digest, 'retained evidence changed: ' + str(path))
    manifest = json.loads(regular(COMPOSITION / 'composition.json'))
    need(manifest['source_commit'] == HEAD and manifest['private_config']['path'] == str(CONFIG)
         and manifest['private_config']['backup'] == str(BACKUP), 'composition identity differs')
    original = regular(BACKUP)
    need(sha(original) == ORIGINAL, 'retained backup differs')
    before = regular(CONFIG)
    identity = CONFIG.stat()
    need(stat.S_IMODE(identity.st_mode) == manifest['private_config']['original_mode'],
         'private config mode differs')
    if args.action == 'activate':
        need(not os.path.lexists(TOOLS.parent / 'plans/native_quiet_window.lock'), 'quiet lock exists')
        need(git('rev-parse', 'HEAD', cwd=SOURCE).decode().strip() == HEAD
             and not git('status', '--porcelain', cwd=SOURCE).strip(), 'native source differs')
        for path, digest in manifest['protected_preimages_sha256'].items():
            need(sha(regular(SOURCE / path)) == digest, 'protected source differs: ' + path)
        need(before == original and not os.path.lexists(EVIDENCE), 'fresh activation required')
        EVIDENCE.mkdir()
        write_new(EVIDENCE / 'config-original.bin', original)
        candidate = EVIDENCE / 'config-configured.bin'
        write_new(candidate, original)
        git('config', '--no-includes', '--file', str(candidate),
            'd4d.ciRepositoryUrl', 'https://github.com/bridge2ai/data-sheets-schema.git')
        target = regular(candidate)
        need(sha(target) == CONFIGURED, 'exact prior configured bytes required')
    else:
        need(EVIDENCE.resolve(strict=True) == EVIDENCE, 'physical activation evidence required')
        activation = json.loads(regular(EVIDENCE / 'activate.json'))
        need(activation['source_commit'] == HEAD and activation['after_sha256'] == CONFIGURED
             and regular(EVIDENCE / 'config-original.bin') == original,
             'activation evidence differs')
        need(sha(before) == CONFIGURED, 'foreign config preserved; cannot restore')
        target = original
    witness = EVIDENCE / (args.action + '.json')
    need(not os.path.lexists(witness), 'operation already recorded')
    temporary = CONFIG.with_name('config.wp1-cpu-' + args.action)
    write_new(temporary, target)
    os.chmod(temporary, stat.S_IMODE(identity.st_mode))
    need(regular(CONFIG) == before and CONFIG.stat().st_ino == identity.st_ino,
         'private config changed before replacement')
    os.replace(temporary, CONFIG)
    need(regular(CONFIG) == target, 'private config replacement did not persist')
    result = dict(action=args.action, source_commit=HEAD, tools_commit=tool_head,
        helper_sha256=sha(regular(Path(__file__).resolve())),
        before_sha256=sha(before), after_sha256=sha(target),
        backup_sha256=sha(original), ended_utc=datetime.now(timezone.utc).isoformat(),
        scope='Exact private diagnostic config only; no source installation or acceptance.')
    write_new(witness, (json.dumps(result, indent=2, sort_keys=True) + '\n').encode())
    print(json.dumps(dict(witness=str(witness), sha256=sha(regular(witness)))))


if __name__ == '__main__':
    main()
