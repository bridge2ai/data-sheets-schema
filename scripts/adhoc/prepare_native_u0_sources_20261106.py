#!/usr/bin/env python3
"""Freeze U0 sources for #4354, 2026-11-06.

Inputs: local repository and one named immutable head. Outputs: new sparse
detached worktree, Git source archive, and manifest under d4d-executions.
No existing path is reused, no network/native executable is invoked.
"""
import argparse
from datetime import datetime, timezone
import gzip
import hashlib
import json
import os
from pathlib import Path
import subprocess

EXEC = Path('/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions')
REPO = EXEC.parent / 'data-sheets-schema'
LOCK = EXEC / 'plans/native_quiet_window.lock'
HEADS = {
    'current': '01969cbed8eed93f420c640c1f1c306e5f58b033',
    'original': 'd41282871394dd8abe74e11afb0e80c95d149305',
    'delivery': 'be0bd05821256212e89e4d011ba6b30a780e299b',
}
ROOTS = ('src', 'scripts', 'tests', 'utils', '.claude', 'notes')


def git(root, *args):
    env = {k: v for k, v in os.environ.items() if not k.startswith('GIT_')}
    env.update(GIT_NO_LAZY_FETCH='1', GIT_TERMINAL_PROMPT='0', GIT_CONFIG_GLOBAL=os.devnull)
    return subprocess.check_output([
        'git', '--no-replace-objects', '-c', 'core.hooksPath=/dev/null',
        '-c', 'protocol.allow=never', '-c', 'gc.auto=0', '-C', str(root), *args], env=env)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--target', choices=HEADS, required=True)
    args = p.parse_args()
    if LOCK.exists():
        raise SystemExit('quiet-window lock exists; source preparation must pause')
    base = EXEC / 'native-u0-20261106'
    base.mkdir(exist_ok=True)
    source = base / ('frozen-' + args.target)
    archive = base / (args.target + '-source.tar.gz')
    manifest = base / (args.target + '-source.json')
    if any(path.exists() or path.is_symlink() for path in (source, archive, manifest)):
        raise SystemExit('source/archive/manifest already exists; preserve it')
    head = HEADS[args.target]
    if git(REPO, 'rev-parse', head).decode().strip() != head:
        raise SystemExit('local head differs')
    git(REPO, 'worktree', 'add', '--no-checkout', '--detach', str(source), head)
    git(source, 'sparse-checkout', 'set', *ROOTS)
    git(source, 'read-tree', '-mu', 'HEAD')
    rows = git(source, 'ls-tree', '-r', '-z', 'HEAD').split(b'\0')
    selected, links = [], []
    for row in rows:
        if not row:
            continue
        metadata, name = row.split(b'\t', 1)
        mode, kind, oid = metadata.decode().split()
        name = name.decode()
        if Path(name).parts[0] not in ROOTS and len(Path(name).parts) != 1:
            continue
        if kind == 'commit':
            (source / name).mkdir(exist_ok=True)
            links.append({'path': name, 'commit': oid, 'contents': 'empty'})
        else:
            if not (source / name).is_file():
                raise SystemExit('missing selected source: ' + name)
            selected.append(name)
    status = git(source, 'status', '--porcelain=v1', '--untracked-files=no').decode()
    if status:
        raise SystemExit('fresh source not clean: ' + status[:4000])
    # Stream Git's exact selected committed bytes into a reproducible gzip.
    env = dict(os.environ, GIT_NO_LAZY_FETCH='1', GIT_TERMINAL_PROMPT='0')
    cmd = ['git', '--no-replace-objects', '-C', str(source), 'archive',
           '--format=tar', head, '--', *selected]
    with archive.open('xb') as dest:
        process = subprocess.Popen(cmd, env=env, stdout=subprocess.PIPE)
        with gzip.GzipFile(fileobj=dest, mode='wb', filename='', mtime=0) as zipped:
            while chunk := process.stdout.read(1024 * 1024):
                zipped.write(chunk)
        if process.wait() != 0:
            raise SystemExit('git archive failed; partial archive preserved')
    digest = hashlib.sha256()
    with archive.open('rb') as stream:
        while chunk := stream.read(1024 * 1024):
            digest.update(chunk)
    result = {'created_at': datetime.now(timezone.utc).isoformat(), 'target': args.target,
        'head': head, 'tree': git(source, 'rev-parse', 'HEAD^{tree}').decode().strip(),
        'worktree': str(source), 'tracked_status': status, 'scope': list(ROOTS),
        'root_files_included': True, 'selected_paths': selected, 'gitlinks': links,
        'archive': {'path': str(archive), 'bytes': archive.stat().st_size,
                    'sha256': digest.hexdigest()},
        'exclusions': 'other tracked roots, including corpus data/docs; submodule contents excluded',
        'fixture_basis': 'neutral test synthesizes case data; source authority uses exact Git objects'}
    with manifest.open('x') as stream:
        json.dump(result, stream, indent=2, sort_keys=True)
        stream.write('\n')
    print(json.dumps({key: result[key] for key in ('target', 'head', 'worktree', 'archive')}))


if __name__ == '__main__':
    main()
