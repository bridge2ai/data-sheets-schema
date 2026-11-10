#!/usr/bin/env python3
"""Prepare the fixed-main U3-M API parity baseline, 2026-11-09.

Inputs: explicit committed current helper/test source; fixed local main 2cfc4666.
Outputs: a fresh private Git repository, detached parity worktree with exactly two
test-only additions, untouched main scanner worktree, fixed fixture root and manifest.
Production bytes remain those of fixed main. No patches, production imports,
provider/native execution, tests, network, shared refs or old evidence writes.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import importlib.util
import json
import os
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location('u3m_parity_local_archive',
    ROOT / 'scripts/adhoc/compose_native_u1u3_20261108.py')
base = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(base)
MAIN = '2cfc4666c2d81003d9cf5f432248b4217ef477e1'
OUT = ROOT.parent / 'scratch-native-u1u3/u3m'
ADDITIONS = ('tests/test_native_u1_api_parity.py',
             'scripts/adhoc/u3m_parity_plugin_20261109.py')
PROTECTED = ('src/data_sheets_schema/shared_generation.py',
             'src/data_sheets_schema/api_runner.py',
             'src/download/prompts/canonical_hashes.yaml',
             'tests/utils/run_spec_boundary_contracts.json')


def save(path, value):
    raw = (json.dumps(value, indent=2, sort_keys=True) + '\n').encode()
    with path.open('xb') as stream:
        stream.write(raw)
    base.need(path.read_bytes() == raw, 'manifest write did not persist exactly')
    return base.sha(raw)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--commit', required=True, help='Full committed current helper/test source SHA')
    args = parser.parse_args()
    base.quiet()
    source = args.commit
    base.need(ROOT.name == 'codex-native-u1u3' and ROOT.resolve(strict=True) == ROOT
              and ROOT.parent.name == 'd4d-executions', 'assigned physical source checkout required')
    base.need(re.fullmatch('[0-9a-f]{40}', source) is not None, 'full source SHA required')
    base.need(base.git('rev-parse', 'HEAD').decode().strip() == source,
              'explicit source is not current HEAD')
    base.need(base.git('branch', '--show-current').decode().strip() == base.BRANCH,
              'not the assigned combined branch')
    base.need(not base.git('status', '--porcelain', '--untracked-files=normal').strip(),
              'source checkout must be committed and clean')
    base.need(base.git('rev-parse', MAIN + '^{commit}').decode().strip() == MAIN,
              'fixed main is unavailable locally')
    helper = str(Path(__file__).resolve().relative_to(ROOT))
    for name in (helper, *ADDITIONS):
        base.need((ROOT / name).read_bytes() == base.strict_blob(source, name),
                  'helper/test is not exactly committed: ' + name)
    existing = base.git('ls-tree', '-r', '--name-only', MAIN, '--', *ADDITIONS).decode().splitlines()
    base.need(not existing, 'fixed main already contains a parity overlay path; review before replacing it')
    for path in (OUT.parent, OUT):
        base.need(not path.is_symlink(), 'scratch root is aliased')
        path.mkdir(exist_ok=True)
        base.need(path.resolve(strict=True) == path, 'scratch root has an aliased ancestor')
    evidence = OUT / ('baseline-parity-' + source[:12])
    worktree = OUT / ('baseline-parity-worktree-' + source[:12])
    scan_baseline = OUT / ('baseline-scan-' + source[:12])
    inputs = OUT / ('parity-inputs-' + source[:12])
    base.need(all(not os.path.lexists(path) for path in (evidence, worktree, scan_baseline, inputs)),
              'baseline, worktrees and parity fixture destinations must all be fresh')
    protected = {path: base.sha(base.strict_blob(MAIN, path)) for path in PROTECTED}
    additions = {name: base.strict_blob(source, name) for name in ADDITIONS}
    evidence.mkdir()
    record = dict(kind='native_u3m_parity_baseline_overlay', version=1,
                  status='incomplete', started_utc=datetime.now(timezone.utc).isoformat(),
                  source_commit=source, source_worktree=str(ROOT), baseline_commit=MAIN,
                  composition_parent=MAIN, worktree=str(worktree), test_root=str(worktree),
                  test_worktree=str(worktree), parity_inputs=str(inputs),
                  scan_baseline=str(scan_baseline), scan_baseline_commit=MAIN,
                  protected_source_sha256=protected,
                  helper_sha256=base.sha(Path(__file__).read_bytes()),
                  inherited_archive_helper_sha256=base.sha(Path(base.__file__).read_bytes()),
                  test_only_additions_sha256={name: base.sha(raw) for name, raw in additions.items()},
                  scope='Offline API parity only; fixed-main production bytes; no packet or native acceptance')
    try:
        archive = evidence / 'source.tar'
        base.git('archive', '--format=tar', '--output=' + str(archive), MAIN)
        base.need(archive.is_file() and archive.stat().st_size > 0, 'fixed-main archive is empty')
        tree = evidence / 'tree'
        tree.mkdir()
        members = base.extract(archive, tree)
        base.git('init', '-q', '--object-format=sha1', cwd=tree)
        objects = Path(base.git('rev-parse', '--path-format=absolute', '--git-path', 'objects').decode().strip())
        base.need(objects.is_absolute() and objects.resolve(strict=True) == objects
                  and objects.is_dir(), 'local alternate object store is not physical')
        (tree / '.git/objects/info/alternates').write_text(str(objects) + '\n')
        base.git('update-ref', '--no-deref', 'HEAD', MAIN, cwd=tree)
        base.git('read-tree', MAIN, cwd=tree)
        base.need(not base.git('remote', cwd=tree).strip(), 'private baseline has a remote')
        base.git('diff-index', '--quiet', 'HEAD', '--', cwd=tree)
        for name, raw in additions.items():
            target = tree / name
            target.parent.mkdir(exist_ok=True, parents=True)
            base.need(not os.path.lexists(target), 'test-only overlay target already exists')
            with target.open('xb') as stream:
                stream.write(raw)
            base.need(target.read_bytes() == raw, 'test-only overlay did not persist')
        base.git('add', '--', *ADDITIONS, cwd=tree)
        staged = base.git('diff', '--cached', '--name-only', MAIN, cwd=tree).decode().splitlines()
        base.need(sorted(staged) == sorted(ADDITIONS), 'baseline index delta is not exactly two test paths')
        tree_sha = base.git('write-tree', cwd=tree).decode().strip()
        for name, raw in additions.items():
            base.need(base.git('show', tree_sha + ':' + name, cwd=tree) == raw,
                      'index transformed a test-only overlay')
        message = ('Offline U3-M fixed-main API parity with identical test-only harness\n\n'
                   'Baseline: ' + MAIN + '\nHarness: ' + source + '\nNo production or packet edits.')
        child = base.git('commit-tree', tree_sha, '-p', MAIN, '-m', message, cwd=tree).decode().strip()
        raw_commit = base.git('cat-file', '-p', child, cwd=tree)
        headers = raw_commit.split(b'\n\n', 1)[0].splitlines()
        base.need(headers[0] == b'tree ' + tree_sha.encode()
                  and [line for line in headers if line.startswith(b'parent ')]
                      == [b'parent ' + MAIN.encode()], 'private baseline commit tree or parent differs')
        base.git('update-ref', '--no-deref', 'HEAD', child, cwd=tree)
        base.git('diff-index', '--quiet', 'HEAD', '--', cwd=tree)
        delta = base.git('diff', '--name-only', MAIN, child, cwd=tree).decode().splitlines()
        base.need(sorted(delta) == sorted(ADDITIONS), 'baseline commit changes production or other files')
        base.git('worktree', 'add', '--detach', str(worktree), child, cwd=tree)
        base.need(worktree.resolve(strict=True) == worktree and (worktree / '.git').is_file(),
                  'baseline test worktree is not a physical detached checkout')
        base.need(not base.git('status', '--porcelain', cwd=worktree).strip(), 'baseline test worktree is dirty')
        common = Path(base.git('rev-parse', '--path-format=absolute', '--git-common-dir', cwd=worktree).decode().strip())
        base.need(common == tree / '.git', 'baseline worktree does not use its private repository')
        base.git('worktree', 'add', '--detach', str(scan_baseline), MAIN, cwd=tree)
        base.need(scan_baseline.resolve(strict=True) == scan_baseline
                  and (scan_baseline / '.git').is_file(),
                  'scanner baseline is not a physical detached checkout')
        base.need(base.git('rev-parse', 'HEAD', cwd=scan_baseline).decode().strip() == MAIN,
                  'scanner baseline HEAD is not fixed main')
        base.need(not base.git('status', '--porcelain', '--untracked-files=all', cwd=scan_baseline).strip(),
                  'scanner baseline is dirty')
        scan_common = Path(base.git('rev-parse', '--path-format=absolute', '--git-common-dir',
                                   cwd=scan_baseline).decode().strip())
        base.need(scan_common == common, 'scanner baseline does not share the private repository')
        base.git('diff-index', '--quiet', MAIN, '--', cwd=scan_baseline)
        base.need(all(not os.path.lexists(scan_baseline / name) for name in ADDITIONS),
                  'test overlays leaked into the untouched scanner baseline')
        for name, digest in protected.items():
            base.need(base.sha((tree / name).read_bytes()) == digest
                      and base.sha((worktree / name).read_bytes()) == digest
                      and base.sha((scan_baseline / name).read_bytes()) == digest,
                      'fixed-main protected production bytes changed: ' + name)
        inputs.mkdir()
        base.need(inputs.resolve(strict=True) == inputs and not any(inputs.iterdir()),
                  'fresh parity input root is not empty and physical')
        with (evidence / 'test-only-overlay.diff').open('xb') as stream:
            stream.write(base.git('diff', '--binary', '--full-index', MAIN, child, cwd=tree))
        with (evidence / 'baseline-commit.txt').open('xb') as stream:
            stream.write(raw_commit)
        record.update(status='composed_not_tested', composition_commit=child,
                      composition_tree=tree_sha, composition_commit_sha256=base.sha(raw_commit),
                      baseline_tree=base.git('rev-parse', MAIN + '^{tree}').decode().strip(),
                      private_git=str(common), private_config_sha256=base.sha((common / 'config').read_bytes()),
                      private_config_mutation='none; no CI URL configured for API-only baseline',
                      archive_sha256=base.file_sha(archive), archive_bytes=archive.stat().st_size,
                      archive_member_count=members, exact_delta_from_baseline=delta,
                      alternate_objects=str(objects),
                      fairscape_gitlink=base.git('ls-tree', MAIN, 'fairscape_models').decode().strip())
        base.need(base.git('rev-parse', 'HEAD').decode().strip() == source
                  and not base.git('status', '--porcelain', '--untracked-files=normal').strip(),
                  'source checkout changed during baseline preparation')
        base.quiet()
    except BaseException as exc:
        record.update(status='refused', error_type=type(exc).__name__, reason=str(exc))
        raise
    finally:
        record['ended_utc'] = datetime.now(timezone.utc).isoformat()
        manifest = evidence / 'composition.json'
        digest = save(manifest, record)
        print(json.dumps(dict(status=record['status'], manifest=str(manifest), sha256=digest)), flush=True)


if __name__ == '__main__':
    main()
