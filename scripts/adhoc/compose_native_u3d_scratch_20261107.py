#!/usr/bin/env python3
"""Compose committed U3-D with the exact four U1 packets, 2026-11-07.

Inputs: an explicit full local D commit and optionally a local FAIRSCAPE repo.
Outputs: one exclusive scratch-native-u3d/<name> evidence directory containing
an archive, private-Git composition commit and manifest. Never edits an existing
worktree/shared ref, downloads, launches tests/native programs or regenerates a
packet. The private commit contains only the four authorized packet postimages.
Run only after this helper and the final D source have been committed.
"""
from __future__ import annotations

import argparse
import ast
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import signal
import subprocess
import sys
import tarfile
import time

ROOT = Path(__file__).resolve().parents[2]
EXECUTIONS = ROOT.parent
SCRATCH = EXECUTIONS / 'scratch-native-u3d'
LOCK = EXECUTIONS / 'plans/native_quiet_window.lock'
BRANCH = 'codex/native-u3d-integration-20261107'
PACKET_DIRECTORY = 'scripts/adhoc/native_u1_packets'
PROMPT_COMMIT = '41b7169f6296c69201fc46389082c441e7d7165c'
CHECKER = 'tests/utils/run_spec_boundaries.py'
CHECKER_SHA = 'a379e93a0065dc927835b1417cabcb926e33eeb333416c768237bc50d2dc6237'
PACKETS = (
    ('shared_generation', 'src/data_sheets_schema/shared_generation.py',
     '94b3cf6845827c8fdf7bf05cc6251e2fb196ceb91ea8ce377f2c9e3b8be3773d',
     '2ec18e60316423035f88a2a30263c56385bfbbc587303e84e805a8349ab4f781',
     '22b81b6cd63a708d82bfbd038b7e1d9aaf340bf1d86828f138b56dd9ef4756c5'),
    ('api_runner_companion', 'src/data_sheets_schema/api_runner.py',
     'db9a0f67ba7ace06bc8b39f90a00a3fe98ee72a34e553be6d48f97bff5e6d848',
     '3e8b7e5d3cc13c5ebc508e33f865e9ac484056fde16126118719d740656a4fb7',
     '996bd9bce74d509033a1daf340ea2a6edfc2a820316e798459892738a989475f'),
    ('canonical_hashes', 'src/download/prompts/canonical_hashes.yaml',
     '39b93c009457681a1d8d8b8afee5a869bbd6f5e70b6f4332522db5d7e22d0584',
     '9efd980d77415a6a33f26928f01ff787855dfc1654356a96e5e76560b200fb99',
     'f26d093b88eeb04bdd984d859554b47b78894c53739dc18ba81cbebae1e9f85e'),
    ('run_spec_boundary_contracts', 'tests/utils/run_spec_boundary_contracts.json',
     'a7f96a253a37e994f0c62c7d9b2ab21b0a94d4f342975f84103cd274ef11af72',
     'b1e0cbd14c533a51b88eacb84b974cb93963e18d8f1fb71ae4ed3228f784d1ce',
     'dc58e99f73fe5de1a4f6179639dd2cfd2215c0dd665319e8d15b148b1824509f'),
)
ENV = {'PATH': '/usr/bin:/bin:/usr/sbin:/sbin', 'LANG': 'C', 'LC_ALL': 'C',
       'GIT_CONFIG_GLOBAL': '/dev/null', 'GIT_CONFIG_SYSTEM': '/dev/null',
       'GIT_CONFIG_NOSYSTEM': '1', 'GIT_NO_LAZY_FETCH': '1',
       'GIT_TERMINAL_PROMPT': '0', 'GIT_OPTIONAL_LOCKS': '0',
       'GIT_PROTOCOL_FROM_USER': '0', 'GIT_ASKPASS': '/usr/bin/false',
       'GIT_SSH_COMMAND': '/usr/bin/false',
       'GIT_AUTHOR_NAME': 'D4D offline scratch validation',
       'GIT_AUTHOR_EMAIL': 'scratch@invalid',
       'GIT_COMMITTER_NAME': 'D4D offline scratch validation',
       'GIT_COMMITTER_EMAIL': 'scratch@invalid',
       'GIT_AUTHOR_DATE': '2026-11-07T00:00:00+00:00',
       'GIT_COMMITTER_DATE': '2026-11-07T00:00:00+00:00'}
GIT = ['/usr/bin/git', '--no-replace-objects', '-c', 'protocol.allow=never',
       '-c', 'core.hooksPath=/dev/null', '-c', 'core.fsmonitor=false',
       '-c', 'commit.gpgSign=false']


def need(condition, message):
    if not condition:
        raise ValueError(message)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def quiet():
    # Broken symlinks are also occupied locks. Never remove or poll a lock.
    if os.path.lexists(LOCK):
        raise RuntimeError('quiet-window lock exists; retain artifacts and stop')


def git(*args, cwd=ROOT):
    """Only explicit local Git commands, bounded and interrupted on a quiet lock."""
    quiet()
    child = subprocess.Popen([*GIT, *args], cwd=cwd, env=ENV,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True)
    deadline = time.monotonic() + 300
    try:
        while True:
            try:
                out, err = child.communicate(timeout=1)
                break
            except subprocess.TimeoutExpired:
                quiet()
                if time.monotonic() >= deadline:
                    raise TimeoutError('local Git command exceeded 300 seconds: ' + args[0])
        need(child.returncode == 0, 'local Git failed: ' + ' '.join(args) + '\n' + err.decode(errors='replace'))
        quiet()
        return out
    except BaseException:
        if child.poll() is None:
            os.killpg(child.pid, signal.SIGTERM)
            try:
                child.communicate(timeout=5)
            except subprocess.TimeoutExpired:
                os.killpg(child.pid, signal.SIGKILL)
                child.communicate()
        raise


def file_sha(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        while raw := stream.read(1 << 20):
            quiet()
            digest.update(raw)
    return digest.hexdigest()


def extract(archive, destination):
    """Git archive only; reject escapes, special files and archive Git metadata."""
    names = set()
    with tarfile.open(archive) as stream:
        for member in stream:
            quiet()
            path = PurePosixPath(member.name)
            need(not path.is_absolute() and '..' not in path.parts and '.git' not in path.parts,
                 'unsafe archive path: ' + member.name)
            need(member.name not in names, 'duplicate archive path: ' + member.name)
            names.add(member.name)
            need(member.isdir() or member.isfile() or member.issym(), 'unsupported archive member')
            stream.extract(member, destination, filter='data')
    return len(names)


def strict_blob(commit, relative):
    return git('show', commit + ':' + relative)


def sidecar_check(tree, before):
    after = json.loads((tree / PACKETS[-1][1]).read_bytes())
    old = json.loads(before)
    need(len(old['contracts']) == len(after['contracts']) == 21, 'D76 contract roster changed')
    need(old['approval'] == after['approval'], 'D76 approval changed')
    for left, right in zip(old['contracts'], after['contracts']):
        need({k: v for k, v in left.items() if not k.startswith('function_')} ==
             {k: v for k, v in right.items() if not k.startswith('function_')},
             'D76 identity, mode or caller precondition changed')
        raw = (tree / right['source_path']).read_bytes()
        nodes = [n for n in ast.parse(raw).body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
                 and n.name == right['identity'].rsplit('.', 1)[1]]
        need(len(nodes) == 1, 'D76 function identity is not unique')
        node = nodes[0]
        start = min([node.lineno, *[d.lineno for d in node.decorator_list]])
        body = b''.join(raw.splitlines(keepends=True)[start - 1:node.end_lineno])
        expected = {'function_start_line': start, 'function_end_line': node.end_lineno,
                    'function_bytes': len(body), 'function_sha256': sha(body)}
        need(all(right[key] == value for key, value in expected.items()), 'D76 exact function pin changed')
    need(after['shared_generation_sha256'] == PACKETS[0][3], 'D76 shared-generation pin differs')
    for path, digest in after['source_sha256'].items():
        need(sha((tree / path).read_bytes()) == digest, 'D76 source pin differs: ' + path)
    need(sha((tree / CHECKER).read_bytes()) == CHECKER_SHA, 'D76 checker changed')


def compose(args, evidence):
    commit = args.commit
    need(git('branch', '--show-current').decode().strip() == BRANCH, 'not the assigned D worktree')
    need(git('rev-parse', 'HEAD').decode().strip() == commit, 'explicit commit is not current D HEAD')
    need(git('rev-parse', commit + '^{commit}').decode().strip() == commit, 'not a full local commit')
    git('diff-index', '--quiet', 'HEAD', '--')
    helper = str(Path(__file__).resolve().relative_to(ROOT))
    need(strict_blob(commit, helper) == Path(__file__).read_bytes(), 'this exact helper is not committed at D HEAD')
    protected = {}
    packets = []
    for name, target, preimage, postimage, patch_sha in PACKETS:
        quiet()
        raw = strict_blob(commit, target)
        need(sha(raw) == preimage, 'packet preimage mismatch: ' + target
             + ' expected=' + preimage + ' actual=' + sha(raw))
        need((ROOT / target).read_bytes() == raw, 'source worktree target differs from its commit: ' + target)
        protected[target] = raw
        metadata_raw = strict_blob(commit, PACKET_DIRECTORY + '/' + name + '.json')
        metadata = json.loads(metadata_raw)
        expected = {'target': target, 'preimage_sha256': preimage,
                    'postimage_sha256': postimage, 'patch_sha256': patch_sha}
        need(all(metadata.get(k) == v for k, v in expected.items()), 'frozen packet metadata differs: ' + name)
        patch = strict_blob(commit, PACKET_DIRECTORY + '/' + name + '.patch')
        need(sha(patch) == patch_sha, 'frozen packet bytes differ: ' + name
             + ' expected=' + patch_sha + ' actual=' + sha(patch))
        packets.append({'name': name, **expected, 'metadata_sha256': sha(metadata_raw)})
    need(sha(strict_blob(commit, CHECKER)) == CHECKER_SHA, 'committed D76 checker differs')
    for name in ('generation', 'receipt_policy'):
        path = 'src/download/prompts/native_shared_' + name + '_v1.md'
        need(strict_blob(commit, path) == strict_blob(PROMPT_COMMIT, path), 'U1 prompt commit bytes differ')
    archive = evidence / 'source.tar'
    git('archive', '--format=tar', '--output=' + str(archive), commit)
    need(archive.stat().st_size > 0, 'empty committed source archive')
    tree = evidence / 'tree'
    tree.mkdir()
    member_count = extract(archive, tree)
    git('init', '-q', '--object-format=sha1', cwd=tree)
    objects = Path(git('rev-parse', '--path-format=absolute', '--git-path', 'objects').decode().strip())
    need(objects.is_absolute() and objects.is_dir(), 'missing local object store')
    (tree / '.git/objects/info/alternates').write_text(str(objects) + '\n')
    git('update-ref', '--no-deref', 'HEAD', commit, cwd=tree)
    git('read-tree', commit, cwd=tree)
    need(not git('remote', cwd=tree).strip(), 'private archive repository has a remote')
    need(not git('diff', '--name-only', cwd=tree).strip(), 'archive differs from the committed D tree before composition')
    paths = [str(tree / PACKET_DIRECTORY / (row['name'] + '.patch')) for row in packets]
    git('apply', '--check', *paths, cwd=tree)
    git('apply', *paths, cwd=tree)
    for row in packets:
        actual = sha((tree / row['target']).read_bytes())
        need(actual == row['postimage_sha256'], 'exact composed postimage mismatch: '
             + row['target'] + ' expected=' + row['postimage_sha256'] + ' actual=' + actual)
    sidecar_check(tree, protected[PACKETS[-1][1]])
    changed = set(git('diff', '--name-only', cwd=tree).decode().splitlines())
    need(changed == set(protected), 'composition changed paths beyond the exact four packets')
    # U3-A's complete-package proof requires these exact source postimages to
    # be committed. Write objects/HEAD only in this new private repository;
    # the donor object store remains a read-only alternate and no branch moves.
    private_objects = Path(git('rev-parse', '--path-format=absolute', '--git-path', 'objects', cwd=tree).decode().strip())
    need(private_objects == tree / '.git/objects', 'composition objects are not private')
    need(git('rev-parse', '--abbrev-ref', 'HEAD', cwd=tree).decode().strip() == 'HEAD', 'private HEAD is not detached')
    git('add', '--', *sorted(protected), cwd=tree)
    staged = set(git('diff', '--cached', '--name-only', cwd=tree).decode().splitlines())
    need(staged == set(protected), 'private index contains more than the four packet targets')
    tree_sha = git('write-tree', cwd=tree).decode().strip()
    for row in packets:
        need(sha(git('show', tree_sha + ':' + row['target'], cwd=tree)) == row['postimage_sha256'],
             'private index transformed a packet postimage')
    message = 'Offline U3-D scratch composition of four exact U1 packets\n\nParent D: ' + commit + '\nValidation only; no protected worktree approval or launch authority.'
    child = git('commit-tree', tree_sha, '-p', commit, '-m', message, cwd=tree).decode().strip()
    need(re.fullmatch('[0-9a-f]{40}', child) is not None, 'private composition commit is malformed')
    commit_raw = git('cat-file', '-p', child, cwd=tree)
    headers = commit_raw.split(b'\n\n', 1)[0].splitlines()
    need([line for line in headers if line.startswith(b'parent ')] == [b'parent ' + commit.encode()],
         'private composition commit has a different parent')
    need(headers[0] == b'tree ' + tree_sha.encode(), 'private composition commit has a different tree')
    git('update-ref', '--no-deref', 'HEAD', child, cwd=tree)
    need(not git('diff-index', '--name-only', 'HEAD', '--', cwd=tree).strip(), 'private composed tree differs from its commit')
    need(set(git('diff', '--name-only', commit, child, cwd=tree).decode().splitlines()) == set(protected),
         'private composition commit changed more than the packet roster')
    diff = git('diff', '--binary', '--full-index', commit, child, cwd=tree)
    need(bool(diff), 'missing packet-only commit diff witness')
    with (evidence / 'packet-only.diff').open('xb') as stream:
        stream.write(diff)
    with (evidence / 'composition-commit.txt').open('xb') as stream:
        stream.write(commit_raw)
    result = {'source_commit': commit, 'tree': str(tree), 'archive_sha256': file_sha(archive),
        'archive_bytes': archive.stat().st_size, 'archive_members': member_count, 'packets': packets,
        'alternate_objects': str(objects), 'alternate_policy': 'read through Git alternates; no write to source object store',
        'private_head': git('rev-parse', 'HEAD', cwd=tree).decode().strip(),
        'composition_commit': child, 'composition_parent': commit, 'composition_tree': tree_sha,
        'composition_commit_sha256': sha(commit_raw), 'packet_only_diff_sha256': sha(diff),
        'commit_policy': 'new private detached HEAD only; deterministic local identity/date; no hooks, signature or shared refs',
        'tracked_packet_delta': sorted(changed), 'test_overlays': [],
        'scope': 'scratch composition only; no protected worktree approval, acceptance, launch or publication'}
    row = git('ls-tree', commit, 'fairscape_models').decode().split()
    need(len(row) == 4 and row[:2] == ['160000', 'commit'] and row[3] == 'fairscape_models',
         'FAIRSCAPE is not the expected committed Gitlink')
    result['fairscape'] = {'gitlink_commit': row[2], 'populated': False}
    if args.fairscape_source is not None:
        source = Path(args.fairscape_source)
        need(source.is_absolute() and source.resolve(strict=True) == source, 'FAIRSCAPE source must be canonical')
        need(Path(git('rev-parse', '--show-toplevel', cwd=source).decode().strip()).resolve() == source,
             'FAIRSCAPE source is not its own local repository')
        need(git('rev-parse', 'HEAD', cwd=source).decode().strip() == row[2], 'local FAIRSCAPE HEAD differs from Gitlink')
        subarchive = evidence / 'fairscape.tar'
        git('archive', '--format=tar', '--output=' + str(subarchive), row[2], cwd=source)
        target = tree / 'fairscape_models'
        need(not target.is_symlink() and target.is_dir() and not any(target.iterdir()), 'FAIRSCAPE archive destination is not empty')
        submembers = extract(subarchive, target)
        expected = git('show', row[2] + ':fairscape_models/rocrate.py', cwd=source)
        need(expected and (target / 'fairscape_models/rocrate.py').read_bytes() == expected, 'FAIRSCAPE module differs from pinned Gitlink')
        result['fairscape'].update(populated=True, source=str(source), archive_sha256=file_sha(subarchive),
            archive_bytes=subarchive.stat().st_size, archive_members=submembers,
            scope='separate local Gitlink archive, not a change to the D source commit')
    need(all((ROOT / path).read_bytes() == raw for path, raw in protected.items()), 'protected worktree bytes changed')
    need(sha((ROOT / CHECKER).read_bytes()) == CHECKER_SHA, 'source D76 checker changed')
    need(git('rev-parse', 'HEAD').decode().strip() == commit, 'source HEAD moved during composition')
    git('diff-index', '--quiet', 'HEAD', '--')
    quiet()
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--commit', required=True, help='Full committed D HEAD SHA; this helper must be included')
    parser.add_argument('--name', help='New exclusive evidence directory name under scratch-native-u3d')
    parser.add_argument('--fairscape-source', help='Optional exact local FAIRSCAPE repository at the pinned Gitlink')
    args = parser.parse_args()
    need(sys.version_info >= (3, 12), 'Python 3.12+ required for safe archive extraction')
    need(re.fullmatch('[0-9a-f]{40}', args.commit) is not None, 'full lowercase commit SHA required')
    name = args.name or 'composed-' + args.commit[:12]
    need(re.fullmatch('[a-zA-Z0-9][a-zA-Z0-9_-]{0,100}', name) is not None, 'unsafe scratch name')
    quiet()
    need(EXECUTIONS.name == 'd4d-executions' and EXECUTIONS.resolve() == EXECUTIONS,
         'helper must run from the assigned physical executions worktree')
    need(not SCRATCH.is_symlink(), 'scratch root must not be a symlink')
    SCRATCH.mkdir(exist_ok=True)
    need(SCRATCH.resolve() == SCRATCH, 'scratch root has a physical alias')
    destination = SCRATCH / name
    destination.mkdir()  # Exclusive: never reuse or erase an earlier result.
    started = datetime.now(timezone.utc).isoformat()
    result = {'started_utc': started, 'requested_commit': args.commit,
        'helper_sha256': sha(Path(__file__).read_bytes()), 'status': 'incomplete',
        'destination': str(destination)}
    try:
        result.update(compose(args, destination), status='composed_not_tested')
    except BaseException as exc:
        result.update(status='refused', error_type=type(exc).__name__, reason=str(exc))
        raise
    finally:
        result['ended_utc'] = datetime.now(timezone.utc).isoformat()
        manifest = destination / 'composition.json'
        with manifest.open('x') as stream:
            json.dump(result, stream, indent=2, sort_keys=True)
            stream.write('\n')
        print(json.dumps({'status': result['status'], 'manifest': str(manifest),
            'sha256': sha(manifest.read_bytes())}, sort_keys=True), flush=True)


if __name__ == '__main__':
    main()
