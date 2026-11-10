#!/usr/bin/env python3
"""Build U3-L's private D127 composition and test worktree, 2026-11-09.

Inputs: this committed checkout HEAD and the exact retained D127 canonical
postimage. Outputs: fresh u3l composition/worktree, immutable manifest, and an
adjacent private-config backup. Cleanup restores only that config; it preserves
all evidence and the worktree. No tests, packet regeneration, source installation,
network, native executable, provider, source ref or source Git-config mutation.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import importlib.util
import json
import os
from pathlib import Path
import re
import stat
import sys

ROOT = Path(__file__).resolve().parents[2]
BASE_FILE = ROOT / 'scripts/adhoc/compose_native_u1u3_20261108.py'
spec = importlib.util.spec_from_file_location('u3l_frozen_composer', BASE_FILE)
base = importlib.util.module_from_spec(spec)
spec.loader.exec_module(base)
OUT = base.SCRATCH / 'u3l'
CANONICAL = base.SCRATCH / 'owner-packets/u3h/e0b964b0e182/canonical_hashes.postimage'
CANONICAL_SHA = '543e5cd6dc0da0f622ba2cd11a16a90732e9302a1ed0a4700efb61971299d252'
CI_URL = 'https://github.com/bridge2ai/data-sheets-schema.git'
KEY = 'd4d.cirepositoryurl'


def now():
    return datetime.now(timezone.utc).isoformat()


def save(path, value):
    raw = (json.dumps(value, indent=2, sort_keys=True) + '\n').encode()
    with path.open('xb') as stream:
        stream.write(raw)
    base.need(path.read_bytes() == raw, 'evidence write did not persist')
    return base.sha(raw)


def layout(commit):
    base.quiet()
    base.need(sys.version_info >= (3, 12), 'Python 3.12+ required')
    base.need(re.fullmatch('[0-9a-f]{40}', commit) is not None, 'full lowercase source SHA required')
    base.need(ROOT.name == 'codex-native-u1u3' and ROOT.resolve() == ROOT,
              'assigned physical source worktree required')
    base.need(base.EXECUTIONS.name == 'd4d-executions', 'unexpected executions parent')
    for directory in (base.SCRATCH, OUT):
        base.need(not directory.is_symlink(), 'scratch path is an alias')
        directory.mkdir(exist_ok=True)
        base.need(directory.resolve() == directory, 'scratch path has a physical alias')
    return OUT / ('composition-' + commit[:12]), OUT / ('worktree-' + commit[:12])


def regular(path):
    base.need(path.resolve(strict=True) == path and path.is_file() and not path.is_symlink(),
              'expected a regular physical file: ' + str(path))


def protected_source(commit):
    result = {}
    for _, target, preimage, _, _ in base.PACKETS:
        raw = base.strict_blob(commit, target)
        base.need(base.sha(raw) == preimage and (ROOT / target).read_bytes() == raw,
                  'source protected preimage changed: ' + target)
        result[target] = preimage
    return result


def local_entries(tree):
    return base.git('config', '--local', '--null', '--list', cwd=tree).split(b'\0')[:-1]


def setup(args):
    evidence, worktree = layout(args.commit)
    # Reject a dependency export passed where a Git repository is required
    # before producing a large partial composition. The validation runner uses
    # its separately pinned dependency export when this option is omitted.
    if args.fairscape_source is not None:
        source = Path(args.fairscape_source)
        base.need(source.is_absolute() and source.resolve(strict=True) == source,
                  'FAIRSCAPE source must be a physical absolute Git repository')
        base.need(Path(base.git('rev-parse', '--show-toplevel', cwd=source).decode().strip()) == source,
                  'FAIRSCAPE source must be its own Git repository, not an export')
    helper = str(Path(__file__).resolve().relative_to(ROOT))
    base.need(base.strict_blob(args.commit, helper) == Path(__file__).read_bytes(),
              'this exact helper must be committed at source HEAD')
    base.need(not os.path.lexists(evidence) and not os.path.lexists(worktree),
              'fresh composition and worktree paths required')
    regular(CANONICAL)
    canonical = CANONICAL.read_bytes()
    base.need(base.sha(canonical) == CANONICAL_SHA, 'D127 canonical postimage changed; do not regenerate')
    preimages = protected_source(args.commit)
    evidence.mkdir()
    result = dict(kind='native_u3l_private_composition', version=1, started_utc=now(),
                  status='incomplete', source_commit=args.commit, source_worktree=str(ROOT),
                  helper_sha256=base.sha(Path(__file__).read_bytes()),
                  composer_sha256=base.sha(BASE_FILE.read_bytes()), destination=str(evidence),
                  test_worktree=str(worktree), worktree=str(worktree), protected_preimages_sha256=preimages)
    try:
        # This call retains the frozen D76 exact-function/source checks. Any
        # mismatch stops here; this helper never refreshes a packet or sidecar.
        inherited = base.compose(args, evidence)
        result['original_composition'] = inherited
        tree = Path(inherited['tree'])
        canonical_target = tree / base.PACKETS[2][1]
        canonical_target.write_bytes(canonical)
        expected = {row[1]: (CANONICAL_SHA if row[0] == 'canonical_hashes' else row[3])
                    for row in base.PACKETS}
        base.need(all(base.sha((tree / path).read_bytes()) == digest
                      for path, digest in expected.items()), 'D127 postimage mismatch')
        base.sidecar_check(tree, base.strict_blob(args.commit, base.PACKETS[-1][1]))
        base.need(base.git('diff', '--name-only', cwd=tree).decode().splitlines()
                  == [base.PACKETS[2][1]], 'unexpected second-stage private change')
        base.git('add', '--', base.PACKETS[2][1], cwd=tree)
        final_tree = base.git('write-tree', cwd=tree).decode().strip()
        for path, digest in expected.items():
            base.need(base.sha(base.git('show', final_tree + ':' + path, cwd=tree)) == digest,
                      'index transformed an approved D127 postimage')
        message = ('Offline U3-L private composition of exact D127 postimages\n\n'
                   'Source: ' + args.commit + '\nValidation only; no launch authority.')
        child = base.git('commit-tree', final_tree, '-p', args.commit, '-m', message, cwd=tree).decode().strip()
        base.need(re.fullmatch('[0-9a-f]{40}', child) is not None, 'malformed private commit')
        raw_commit = base.git('cat-file', '-p', child, cwd=tree)
        headers = raw_commit.split(b'\n\n', 1)[0].splitlines()
        base.need(headers[0] == b'tree ' + final_tree.encode()
                  and [line for line in headers if line.startswith(b'parent ')]
                      == [b'parent ' + args.commit.encode()], 'wrong final tree or parent')
        base.git('update-ref', '--no-deref', 'HEAD', child, cwd=tree)
        base.git('diff-index', '--quiet', 'HEAD', '--', cwd=tree)
        base.need(set(base.git('diff', '--name-only', args.commit, child, cwd=tree).decode().splitlines())
                  == set(expected), 'final private composition changed more than four packet targets')
        base.git('worktree', 'add', '--detach', str(worktree), child, cwd=tree)
        base.need(worktree.resolve() == worktree and (worktree / '.git').is_file(),
                  'real private test worktree was not created')
        base.need(base.git('rev-parse', 'HEAD', cwd=worktree).decode().strip() == child,
                  'test worktree has the wrong HEAD')
        common = Path(base.git('rev-parse', '--path-format=absolute', '--git-common-dir', cwd=worktree).decode().strip())
        base.need(common == tree / '.git', 'test worktree is not owned by this private repository')
        base.need(not base.git('status', '--porcelain', cwd=worktree).strip(), 'new test worktree is dirty')
        base.need(all(base.sha((worktree / path).read_bytes()) == digest
                      for path, digest in expected.items()), 'test worktree packet bytes differ')
        base.need(not base.git('remote', cwd=worktree).strip(), 'private test repository has a remote')
        config = common / 'config'
        regular(config)
        backup = common / 'config.bak-u3l-20261109'
        original = config.read_bytes()
        original_entries = local_entries(tree)
        base.need(not any(row.partition(b'\n')[0].lower() == KEY.encode() for row in original_entries),
                  'fresh private repository unexpectedly configures a CI URL')
        with backup.open('xb') as stream:
            stream.write(original)
        base.need(backup.read_bytes() == original, 'config backup did not persist')
        os.chmod(backup, stat.S_IMODE(config.stat().st_mode))
        config_row = dict(path=str(config), backup=str(backup), original_sha256=base.sha(original),
                          original_mode=stat.S_IMODE(config.stat().st_mode), key=KEY, value=CI_URL,
                          restore='cleanup subcommand; exact bytes, no worktree/evidence deletion')
        result['private_config'] = config_row
        base.git('config', '--local', 'd4d.ciRepositoryUrl', CI_URL, cwd=tree)
        config_row['configured_sha256'] = base.sha(config.read_bytes())
        after_entries = local_entries(tree)
        added = KEY.encode() + b'\n' + CI_URL.encode()
        base.need(after_entries == original_entries + [added], 'private config changed beyond the one CI URL')
        base.need(base.git('config', '--local', '--get-all', 'd4d.ciRepositoryUrl', cwd=worktree)
                  == (CI_URL + '\n').encode(), 'worktree did not inherit the one configured CI URL')
        base.need(protected_source(args.commit) == preimages, 'source preimages changed during composition')
        base.need(base.git('rev-parse', 'HEAD').decode().strip() == args.commit, 'source HEAD moved')
        base.git('diff-index', '--quiet', 'HEAD', '--')
        result.update(status='composed_not_tested', source_tree=base.git('rev-parse', args.commit + '^{tree}').decode().strip(),
                      composition_commit=child, composition_parent=args.commit, composition_tree=final_tree,
                      composition_commit_sha256=base.sha(raw_commit), private_git=str(common),
                      packet_postimages_sha256=expected, canonical_source=str(CANONICAL),
                      canonical_source_sha256=CANONICAL_SHA, test_root=str(worktree),
                      scope='private software validation only; no source packet installation or native acceptance')
        with (evidence / 'd127-composition-commit.txt').open('xb') as stream:
            stream.write(raw_commit)
        with (evidence / 'd127-packet-only.diff').open('xb') as stream:
            stream.write(base.git('diff', '--binary', '--full-index', args.commit, child, cwd=tree))
        base.quiet()
    except BaseException as exc:
        result.update(status='refused', error_type=type(exc).__name__, reason=str(exc))
        raise
    finally:
        result['ended_utc'] = now()
        manifest = evidence / 'composition.json'
        digest = save(manifest, result)
        print(json.dumps(dict(status=result['status'], manifest=str(manifest), sha256=digest)), flush=True)


def cleanup(args):
    evidence, worktree = layout(args.commit)
    manifest = evidence / 'composition.json'
    regular(manifest)
    recorded = json.loads(manifest.read_bytes())
    base.need(recorded['source_commit'] == args.commit and recorded['test_worktree'] == str(worktree),
              'cleanup manifest has another source or worktree')
    row = recorded['private_config']
    config, backup = Path(row['path']), Path(row['backup'])
    base.need(config == evidence / 'tree/.git/config'
              and backup == config.with_name('config.bak-u3l-20261109'), 'cleanup paths differ')
    regular(config)
    regular(backup)
    original = backup.read_bytes()
    base.need(base.sha(original) == row['original_sha256'], 'private config backup changed')
    current_sha = base.sha(config.read_bytes())
    base.need(current_sha == row['configured_sha256'], 'private config changed concurrently; preserve and stop')
    report = evidence / 'config-restored.json'
    temporary = config.with_name('config.restore-u3l-20261109')
    base.need(not os.path.lexists(report) and not os.path.lexists(temporary), 'cleanup evidence already exists')
    base.quiet()
    with temporary.open('xb') as stream:
        stream.write(original)
        stream.flush()
        os.fsync(stream.fileno())
    os.chmod(temporary, row['original_mode'])
    os.replace(temporary, config)
    base.need(config.read_bytes() == original and base.sha(config.read_bytes()) == row['original_sha256'],
              'private config was not restored exactly')
    base.need(not any(item.partition(b'\n')[0].lower() == KEY.encode()
                      for item in local_entries(evidence / 'tree')), 'CI URL remained after config restoration')
    restored = dict(status='config_restored_evidence_and_worktree_retained', ended_utc=now(),
                    composition_manifest_sha256=base.sha(manifest.read_bytes()), source_commit=args.commit,
                    configured_sha256=current_sha, restored_sha256=base.sha(config.read_bytes()),
                    backup_sha256=base.sha(backup.read_bytes()), worktree=str(worktree),
                    worktree_preserved=worktree.is_dir(), helper_sha256=base.sha(Path(__file__).read_bytes()))
    digest = save(report, restored)
    print(json.dumps(dict(status=restored['status'], manifest=str(report), sha256=digest)), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('setup', 'cleanup'))
    parser.add_argument('--commit', required=True, help='Full committed assigned source HEAD')
    parser.add_argument('--fairscape-source', help='Optional local repository at the frozen FAIRSCAPE Gitlink')
    args = parser.parse_args()
    {'setup': setup, 'cleanup': cleanup}[args.action](args)


if __name__ == '__main__':
    main()
