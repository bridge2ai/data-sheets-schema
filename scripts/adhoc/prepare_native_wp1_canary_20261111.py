#!/usr/bin/env python3
"""Prepare a bounded sparse WP1 composition/contract; E1/#5755, 2026-11-11.

Inputs: clean committed native source, retained exact four-packet proposal,
existing dependency interpreter, and explicit private-proposal acknowledgement.
Outputs: fresh sparse private Git trees and M/WP1 manifests, no archive, corpus
copy, dependency export, environment install or test. Execution still requires
lead clearance of the exact protected proposal; the CLI flag is not approval.
Restore private CI config with compose_native_u3m_20261109.py cleanup afterward.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
from pathlib import Path
import re
import signal
import sys

TOOLS_ROOT = Path(__file__).resolve().parents[2]
ROOT = TOOLS_ROOT.parent / 'codex-native-u1u3'
SPARSE = ('src/data_sheets_schema', 'src/download/prompts', 'scripts/adhoc',
          'tests', '.claude', '.github', 'utils')
CONTROLLER_FILES = (
    'notes/claudecode_direct/prepare_direct_v2.py',
    'notes/claudecode_direct/run_direct_canary.py',
    'notes/claudecode_direct/run_direct_canary_awake.py',
    'notes/matched_cborg_2026-09-13/budget_amendment.py',
    'notes/matched_cborg_2026-09-13/budgeted_cborg.py',
    'notes/matched_cborg_2026-09-13/prepare_registration_v2.py',
    'notes/matched_cborg_2026-09-13/run_api_canary.py',
    'notes/matched_cborg_2026-09-13/native_controls/native_command_policy.py',
    'notes/matched_cborg_2026-09-13/native_controls/native_control.py',
    'notes/matched_cborg_2026-09-13/native_controls/native_file_policy.py',
    'notes/matched_cborg_2026-09-13/native_controls/native_phase_history.py',
    'notes/matched_cborg_2026-09-13/native_controls/native_proxy.py',
    'notes/matched_cborg_2026-09-13/native_controls/native_readonly.py',
    'notes/matched_cborg_2026-09-13/native_controls/prepare_overlay_roster.py',
    'notes/matched_cborg_2026-09-13/native_controls/run_native_canary.py',
)
PATTERNS = ('/*', '!/*/', *( '/' + path + '/' for path in SPARSE),
            *('/' + path for path in CONTROLLER_FILES))
MAX_TREE_BYTES = 128 * 1024 * 1024
MAX_TREE_FILES = 20000
PREPARATION_SECONDS = 180


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', required=True)
    parser.add_argument('--acknowledge-private-api-proposal', required=True)
    args = parser.parse_args()
    if not (sys.flags.no_site and sys.flags.safe_path and sys.dont_write_bytecode):
        raise ValueError('existing dependency Python -S -P -B required')
    if not re.fullmatch('[0-9a-f]{40}', args.source):
        raise ValueError('full source commit required')
    # -B prevents writes but not reads of old project caches. Isolate helper
    # imports before the first project file is loaded; this path is never made.
    cache = ROOT.parent / 'scratch-native-u1u3' / ('wp1-preparation-cache-' + args.source[:12])
    if os.path.lexists(cache):
        raise ValueError('preparation cache-prefix path already exists')
    sys.pycache_prefix = str(cache)

    def expired(number, frame):
        raise TimeoutError('WP1 sparse preparation exceeded 180 seconds')

    previous = signal.signal(signal.SIGALRM, expired)
    signal.setitimer(signal.ITIMER_REAL, PREPARATION_SECONDS)
    try:
        prepare(args)
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, previous)


def prepare(args):
    m = load('wp1_sparse_retained_m', ROOT / 'scripts/adhoc/compose_native_u3m_20261109.py')
    b = m.base
    need = b.need
    git = m.ORIGINAL_GIT
    need(args.acknowledge_private_api_proposal == m.API_POST,
         'explicit exact private API proposal acknowledgement required')
    preimages = m.require_source(args.source)
    overrides = m.packet_inputs()  # Verify existing proposal; never regenerate it.
    need(TOOLS_ROOT.name == 'codex-native-wp1-preparation-20261111'
         and TOOLS_ROOT.resolve(strict=True) == TOOLS_ROOT, 'assigned physical tools worktree required')
    tool_commit = git('rev-parse', 'HEAD', cwd=TOOLS_ROOT).decode().strip()
    relative = str(Path(__file__).resolve().relative_to(TOOLS_ROOT))
    need(not git('status', '--porcelain', cwd=TOOLS_ROOT).strip()
         and git('show', tool_commit + ':' + relative, cwd=TOOLS_ROOT) == Path(__file__).read_bytes(),
         'preparation tools must be committed and clean separately from native source')
    validation = load('wp1_sparse_contract', ROOT / 'scripts/adhoc/native_wp1_validation_20261110.py')
    validation.dependency_site()  # Retain logical venv spelling, no imports from it.

    # Exact non-cone selection includes root files, the named source trees and
    # 15 controller files. Never include all notes/ or parent-directory siblings.
    # Size that selection using object metadata before materializing a Git tree.
    selected = []
    for row in git('ls-tree', '-r', '-l', '-z', args.source).split(b'\0'):
        if not row:
            continue
        metadata, raw_path = row.split(b'\t', 1)
        path = raw_path.decode('utf-8')
        mode, kind, oid, size = metadata.split()
        included = ('/' not in path or path in CONTROLLER_FILES
                    or any(path.startswith(prefix + '/') for prefix in SPARSE))
        if included and kind == b'blob':
            need(mode in {b'100644', b'100755'}, 'sparse selection contains a nonregular file: ' + path)
            selected.append((path, int(size)))
    total = sum(size for _, size in selected)
    need(0 < total <= MAX_TREE_BYTES and len(selected) <= MAX_TREE_FILES,
         'sparse source exceeds the fixed 128-MiB/20000-file preparation cap')
    need(set(CONTROLLER_FILES) <= {path for path, _ in selected},
         'a pinned controller source is absent from the sparse selection')
    for name in ('generation', 'receipt_policy'):
        path = 'src/download/prompts/native_shared_' + name + '_v1.md'
        need(m.ORIGINAL_BLOB(args.source, path) == m.ORIGINAL_BLOB(b.PROMPT_COMMIT, path),
             'frozen U1 prompt bytes differ')

    def materialize(path, commit):
        git('read-tree', commit, cwd=path)
        git('sparse-checkout', 'set', '--no-cone', '--no-sparse-index', *PATTERNS, cwd=path)
        rows = git('ls-files', '-t', '-z', cwd=path).split(b'\0')
        need(all(row[:2] in (b'H ', b'S ') for row in rows if row),
             'unexpected sparse index state')
        present = {row[2:].decode() for row in rows if row.startswith(b'H ')}
        # A gitlink has no blob payload and is never hydrated here.
        present.discard('fairscape_models')
        need(present == {name for name, _ in selected}, 'sparse index differs from sized selection')
        # These directories are exclusively new and owned by this preparation.
        # sparse-set may already materialize some entries; force the same pinned
        # bytes there while retaining the default skip-worktree exclusions.
        git('checkout-index', '--all', '--force', cwd=path)

    evidence = m.OUT / ('composition-' + args.source[:12])
    tree = evidence / 'tree'
    worktree = m.OUT / ('worktree-' + args.source[:12])
    contract_path = m.OUT / ('wp1-contract-' + args.source[:12] + '.json')
    need(not any(os.path.lexists(path) for path in (evidence, worktree, contract_path)),
         'fresh preparation paths required; preserve prior outputs')
    evidence.mkdir()
    result = dict(kind='native_u3m_private_composition', version=1, status='incomplete',
        source_commit=args.source, source_worktree=str(ROOT), merge_commit=m.MERGE,
        fixed_main=m.MAIN, started_utc=m.now(), worktree=str(worktree),
        test_worktree=str(worktree), test_root=str(worktree),
        protected_preimages_sha256=preimages, packet_directory=str(m.PACKET),
        owner_approval='pending_new_api_runner_postimage_not_covered_by_D127',
        private_api_proposal_acknowledged=args.acknowledge_private_api_proposal,
        preparation_tools_commit=tool_commit, preparation_tools_worktree=str(TOOLS_ROOT),
        helper_sha256=b.sha(Path(__file__).read_bytes()),
        sparse_directories=list(SPARSE), sparse_controller_files=list(CONTROLLER_FILES),
        sparse_patterns=list(PATTERNS), materialized_source_bytes_per_tree=total,
        materialized_source_files_per_tree=len(selected),
        maximum_source_bytes_per_tree=MAX_TREE_BYTES, preparation_seconds=PREPARATION_SECONDS,
        source_archive_created=False, environment_created=False, dependency_export_created=False)
    try:
        tree.mkdir()
        git('init', '-q', '--object-format=sha1', cwd=tree)
        objects = Path(git('rev-parse', '--path-format=absolute', '--git-path', 'objects').decode().strip())
        need(objects.is_dir() and objects.resolve(strict=True) == objects,
             'physical local object store required')
        m.write(tree / '.git/objects/info/alternates', (str(objects) + '\n').encode())
        git('update-ref', '--no-deref', 'HEAD', args.source, cwd=tree)
        materialize(tree, args.source)
        need(not git('status', '--porcelain', cwd=tree).strip(), 'sparse checkout differs from source')
        patches = []
        for name, target, pre, post, patch_sha in m.PACKETS:
            metadata_path = b.PACKET_DIRECTORY + '/' + name + '.json'
            metadata_raw = (overrides[metadata_path][1] if metadata_path in overrides
                            else m.ORIGINAL_BLOB(args.source, metadata_path))
            metadata = json.loads(metadata_raw)
            need(all(metadata.get(key) == value for key, value in dict(target=target,
                preimage_sha256=pre, postimage_sha256=post, patch_sha256=patch_sha).items()),
                'frozen packet metadata differs: ' + name)
            patch = ((m.PACKET if target == m.API else m.D127) / (name + '.patch'))
            m.pinned(patch, patch_sha)
            need(b.sha((tree / target).read_bytes()) == pre, 'sparse protected preimage differs')
            patches.append(str(patch))
        git('apply', '--check', *patches, cwd=tree)
        git('apply', *patches, cwd=tree)
        expected = {row[1]: row[3] for row in m.PACKETS}
        need(all(b.sha((tree / path).read_bytes()) == digest for path, digest in expected.items()),
             'private packet postimage differs')
        b.PACKETS = m.PACKETS
        b.sidecar_check(tree, m.ORIGINAL_BLOB(args.source, m.PACKETS[-1][1]))
        git('add', '--', *sorted(expected), cwd=tree)
        tree_sha = git('write-tree', cwd=tree).decode().strip()
        need(set(git('diff', '--name-only', args.source, tree_sha, cwd=tree).decode().splitlines())
             == set(expected), 'private full index differs beyond exact four packets')
        need(all(b.sha(git('show', tree_sha + ':' + path, cwd=tree)) == digest
                 for path, digest in expected.items()), 'private index transformed a packet postimage')
        child = git('commit-tree', tree_sha, '-p', args.source, '-m',
                    'Offline WP1 sparse private composition; no production or launch approval.',
                    cwd=tree).decode().strip()
        git('update-ref', '--no-deref', 'HEAD', child, cwd=tree)
        git('diff-index', '--quiet', child, '--', cwd=tree)
        git('worktree', 'add', '--detach', '--no-checkout', str(worktree), child, cwd=tree)
        materialize(worktree, child)
        common = Path(git('rev-parse', '--path-format=absolute', '--git-common-dir',
                          cwd=worktree).decode().strip())
        need(common == tree / '.git' and worktree.resolve(strict=True) == worktree,
             'private sparse worktree identity differs')
        need(not git('status', '--porcelain', cwd=worktree).strip()
             and not git('remote', cwd=tree).strip(), 'private source is dirty or has a remote')
        need(all(b.sha((worktree / path).read_bytes()) == digest for path, digest in expected.items()),
             'sparse test worktree packet identity differs')
        # Same private config/backup format lets the unchanged M cleanup restore
        # exactly these bytes; no primary/source configuration is touched.
        config = common / 'config'
        backup = common / 'config.bak-u3m-20261109'
        raw, entries = config.read_bytes(), m.local_entries(tree)
        need(not any(row.partition(b'\n')[0].lower() == m.CI_KEY.encode() for row in entries),
             'private config already declares a CI URL')
        m.write(backup, raw)
        mode = config.stat().st_mode & 0o777
        os.chmod(backup, mode)
        result['private_config'] = dict(path=str(config), backup=str(backup), original_sha256=b.sha(raw),
            original_mode=mode, key=m.CI_KEY, value=m.CI_VALUE)
        git('config', '--local', 'd4d.ciRepositoryUrl', m.CI_VALUE, cwd=tree)
        result['private_config']['configured_sha256'] = b.sha(config.read_bytes())
        need(m.local_entries(tree) == entries + [m.CI_KEY.encode() + b'\n' + m.CI_VALUE.encode()],
             'private config changed beyond the CI URL')
        need(m.require_source(args.source) == preimages, 'source changed during sparse preparation')
        need(git('rev-parse', 'HEAD', cwd=TOOLS_ROOT).decode().strip() == tool_commit
             and not git('status', '--porcelain', cwd=TOOLS_ROOT).strip(),
             'preparation tools changed')
        result.update(status='composed_not_tested', composition_commit=child,
            composition_parent=args.source, composition_tree=tree_sha, private_git=str(common),
            packet_postimages_sha256=expected, alternate_objects=str(objects),
            packet_input_overrides={key: dict(path=str(path), sha256=b.sha(raw))
                                    for key, (path, raw) in overrides.items()},
            scope='Sparse private validation proposal only; protected source and approval records untouched.')
    except BaseException as exc:
        result.update(status='refused', error_type=type(exc).__name__, reason=str(exc))
        raise
    finally:
        result['ended_utc'] = m.now()
        composition_sha = m.save(evidence / 'composition.json', result)
    contract = dict(kind='native_wp1_measurement', version=1, source_commit=args.source,
        composition_manifest=str(evidence / 'composition.json'),
        composition_manifest_sha256=composition_sha,
        implementation_sha256={path: b.sha((ROOT / path).read_bytes())
                               for path in sorted(validation.REQUIRED_FILES)},
        interpreter=dict(path=str(Path(sys.executable).resolve(strict=True)),
                         sha256=b.sha(Path(sys.executable).resolve(strict=True).read_bytes()),
                         version=sys.version))
    m.save(contract_path, contract)
    os.environ['U3WP1_MANIFEST'] = str(contract_path)
    validation.contract()  # Actual consumer preflight, without importing a test.
    print(str(contract_path), flush=True)


if __name__ == '__main__':
    main()
