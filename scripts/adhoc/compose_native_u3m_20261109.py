#!/usr/bin/env python3
"""Derive and compose the offline U3-M packet, 2026-11-09.

Inputs: fixed two-parent main merge, committed helper/source HEAD and retained
D127 packets. Outputs: a fresh owner-packets/u3m/<merge12> proposal, private
composition/worktree and exact config restoration evidence. The new API file
hash remains pending owner approval. No assigned-worktree packet installation,
network, tests, provider/native execution, shared-ref update or evidence removal.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import difflib
import importlib.util
import json
import os
from pathlib import Path
import re
import stat
import sys

ROOT = Path(__file__).resolve().parents[2]
BASE_FILE = ROOT / 'scripts/adhoc/compose_native_u1u3_20261108.py'
spec = importlib.util.spec_from_file_location('u3m_retained_composer', BASE_FILE)
base = importlib.util.module_from_spec(spec)
spec.loader.exec_module(base)
ORIGINAL_GIT, ORIGINAL_BLOB = base.git, base.strict_blob
MAIN = '2cfc4666c2d81003d9cf5f432248b4217ef477e1'
PREVIOUS = 'e4985c1afcef9874be1c1e25736ce9d527af1428'
MERGE = '2bf9eb831cdc62a1e3784d1ed03a996724227c54'
OUT = base.SCRATCH / 'u3m'
PACKET = base.SCRATCH / 'owner-packets/u3m' / MERGE[:12]
D127 = base.SCRATCH / 'owner-packets/u3h/e0b964b0e182'
API = 'src/data_sheets_schema/api_runner.py'
API_PRE = 'b109cb918a3079a384937ccfad7ab9b195a55713a355f11f848da98fab59596a'
API_POST = '830eec1e12e96f807fa76ea26e066a1923b60380013c424cfa99f0012af0a881'
API_PATCH = '996bd9bce74d509033a1daf340ea2a6edfc2a820316e798459892738a989475f'
OLD_API_PRE = base.PACKETS[1][2]
OLD_API_POST = base.PACKETS[1][3]
CANONICAL_POST = '543e5cd6dc0da0f622ba2cd11a16a90732e9302a1ed0a4700efb61971299d252'
CANONICAL_PATCH = '34db8dfd6e925b114d2df2b74d3de8d39b57482b21603241e1a568815e791ff8'
CANONICAL_METADATA = '04e0464368dd9ca9abf428e965ee19b52d6d001846c669a07116be8d82aa7b12'
PACKETS = tuple(
    (name, target, API_PRE, API_POST, API_PATCH) if target == API else
    (name, target, pre, CANONICAL_POST, CANONICAL_PATCH) if name == 'canonical_hashes' else row
    for row in base.PACKETS for name, target, pre, post, patch in [row])
CI_KEY, CI_VALUE = 'd4d.cirepositoryurl', 'https://github.com/bridge2ai/data-sheets-schema.git'


def now():
    return datetime.now(timezone.utc).isoformat()


def regular(path):
    base.need(path.is_absolute() and path.resolve(strict=True) == path
              and path.is_file() and not path.is_symlink(), 'physical regular file required: ' + str(path))


def pinned(path, digest):
    regular(path)
    raw = path.read_bytes()
    base.need(base.sha(raw) == digest, 'pinned input changed: ' + str(path))
    return raw


def write(path, raw):
    base.need(path.parent.resolve(strict=True) == path.parent and not os.path.lexists(path),
              'fresh physical output required: ' + str(path))
    with path.open('xb') as stream:
        stream.write(raw)
    base.need(path.read_bytes() == raw, 'output did not persist exactly: ' + str(path))
    return base.sha(raw)


def save(path, value):
    return write(path, (json.dumps(value, indent=2, sort_keys=True) + '\n').encode())


def physical_directory(path):
    base.need(not path.is_symlink(), 'directory is an alias: ' + str(path))
    path.mkdir(exist_ok=True)
    base.need(path.resolve(strict=True) == path, 'directory has an aliased ancestor: ' + str(path))


def require_source(commit):
    base.quiet()
    base.need(sys.version_info >= (3, 12), 'Python 3.12+ required')
    base.need(ROOT.name == 'codex-native-u1u3' and ROOT.resolve(strict=True) == ROOT
              and ROOT.parent.name == 'd4d-executions', 'assigned physical source worktree required')
    base.need(re.fullmatch('[0-9a-f]{40}', commit) is not None, 'full source commit required')
    base.need(ORIGINAL_GIT('rev-parse', 'HEAD').decode().strip() == commit
              and ORIGINAL_GIT('branch', '--show-current').decode().strip() in (
                  base.BRANCH, 'codex/native-capture-ast-integration-20261111'),
              'source HEAD or branch differs')
    base.need(not ORIGINAL_GIT('status', '--porcelain', '--untracked-files=normal').strip(),
              'source must be committed and clean')
    helper = str(Path(__file__).resolve().relative_to(ROOT))
    base.need(ORIGINAL_BLOB(commit, helper) == Path(__file__).read_bytes(),
              'exact helper must be committed at source HEAD')
    base.need(ORIGINAL_GIT('show', '-s', '--format=%P', MERGE).decode().strip().split()
              == [PREVIOUS, MAIN], 'fixed merge parents differ')
    ORIGINAL_GIT('merge-base', '--is-ancestor', MERGE, commit)
    result = {}
    for _, target, pre, _, _ in PACKETS:
        raw = ORIGINAL_BLOB(MERGE, target)
        base.need(base.sha(raw) == pre and ORIGINAL_BLOB(commit, target) == raw
                  and (ROOT / target).read_bytes() == raw, 'merged protected preimage differs: ' + target)
        result[target] = pre
    for directory in (base.SCRATCH, OUT, base.SCRATCH / 'owner-packets',
                      base.SCRATCH / 'owner-packets/u3m'):
        physical_directory(directory)
    return result


def packet(args):
    preimages = require_source(args.commit)
    base.need(not os.path.lexists(PACKET), 'proposal directory already exists; preserve it')
    old_patch = ORIGINAL_BLOB(PREVIOUS, base.PACKET_DIRECTORY + '/api_runner_companion.patch')
    base.need(base.sha(old_patch) == API_PATCH
              and pinned(D127 / 'api_runner_companion.patch', API_PATCH) == old_patch,
              'D127 API patch identity differs')
    pinned(D127 / 'api_runner_companion.preimage', OLD_API_PRE)
    pinned(D127 / 'api_runner_companion.postimage', OLD_API_POST)
    pre = ORIGINAL_BLOB(MERGE, API)
    before = (b'        if not self.native_shared_generation_version:\n'
              b'            from .shared_generation import select as select_shared\n'
              b'            select_shared(self)\n')
    after = (b'        from .shared_generation import select as select_shared\n'
             b'        select_shared(self)\n')
    base.need(pre.count(before) == 1, 'API insertion anchor is not unique')
    post = pre.replace(before, after, 1)
    patch = ''.join(difflib.unified_diff(pre.decode().splitlines(keepends=True),
        post.decode().splitlines(keepends=True), fromfile='a/' + API, tofile='b/' + API)).encode()
    base.need(base.sha(post) == API_POST and patch == old_patch,
              'derived API postimage or complete D127 patch bytes differ')
    PACKET.mkdir()
    result = dict(kind='native_u3m_owner_packet_facts', version=1, status='incomplete',
                  started_utc=now(), source_commit=args.commit, merge_commit=MERGE,
                  merge_parents=[PREVIOUS, MAIN], fixed_main=MAIN,
                  helper_sha256=base.sha(Path(__file__).read_bytes()),
                  protected_preimages_sha256=preimages,
                  owner_approval='pending_new_api_runner_postimage_not_covered_by_D127',
                  native_acceptance=False, required_cohorts_complete=False)
    try:
        write(PACKET / 'api_runner_companion.preimage', pre)
        write(PACKET / 'api_runner_companion.postimage', post)
        write(PACKET / 'api_runner_companion.patch', patch)
        trial = PACKET / 'forward-reverse'
        target = trial / API
        target.parent.mkdir(parents=True)
        write(target, pre)
        commands = []
        for options in (('--check',), (), ('--check', '--reverse'), ('--reverse',)):
            command = ('apply', *options, str(PACKET / 'api_runner_companion.patch'))
            ORIGINAL_GIT(*command, cwd=trial)
            commands.append(list(command))
            expected = pre if options in (('--check',), ('--reverse',)) else post
            base.need(target.read_bytes() == expected, 'forward/reverse application changed unexpected bytes')
        metadata = dict(name='api_runner_companion', target=API, base=MERGE,
            producer_commit=args.commit, fixed_main=MAIN, preimage_sha256=API_PRE,
            postimage_sha256=API_POST, patch_sha256=API_PATCH,
            prior_preimage_sha256=OLD_API_PRE, prior_postimage_sha256=OLD_API_POST,
            entire_patch_identical_to_D127=True, changed_from_D127=True,
            status='proposal_only_not_applied_to_worktree',
            owner_approval='pending_new_api_runner_postimage_not_covered_by_D127',
            reason='Main changed _multivalued_of below the unchanged selector hunk; whole-file identity changes.',
            forward_reverse=dict(clean=True, commands=commands, restored_preimage_sha256=base.sha(target.read_bytes())))
        metadata_sha = save(PACKET / 'api_runner_companion.json', metadata)
        facts = []
        for name, relative, pre_sha, post_sha, patch_sha in PACKETS:
            facts.append(dict(name=name, target=relative, preimage_sha256=pre_sha,
                              postimage_sha256=post_sha, patch_sha256=patch_sha,
                              source=str(PACKET if relative == API else D127),
                              approval=('pending_new_api_runner_postimage' if relative == API else 'unchanged_D127_packet')))
        base.need(require_source(args.commit) == preimages, 'source changed during proposal derivation')
        result.update(status='proposal_ready_owner_approval_pending', packets=facts,
                      api_metadata_sha256=metadata_sha, forward_reverse_clean=True,
                      entire_api_patch_identical_to_D127=True,
                      affected_validation=['API parity against fixed main', 'D126 pinned instruction lines',
                                           'unchanged D128 gate and fixed-main diagnostic',
                                           'U4b/native execution/policy/registry/specificity/hooks/render/D114',
                                           'U3-K freshness/pre-dispatch and once-only public completion'],
                      scope='Private offline measurement permitted by U3-M; no installation or launch approval.')
    except BaseException as exc:
        result.update(status='refused', error_type=type(exc).__name__, reason=str(exc))
        raise
    finally:
        result['ended_utc'] = now()
        digest = save(PACKET / 'FACTS.json', result)
        print(json.dumps(dict(status=result['status'], packet=str(PACKET), facts_sha256=digest)), flush=True)


def packet_inputs():
    metadata_path = PACKET / 'api_runner_companion.json'
    regular(metadata_path)
    metadata_raw = metadata_path.read_bytes()
    metadata = json.loads(metadata_raw)
    base.need(all(metadata.get(k) == v for k, v in dict(target=API, base=MERGE,
        fixed_main=MAIN, preimage_sha256=API_PRE, postimage_sha256=API_POST,
        patch_sha256=API_PATCH, entire_patch_identical_to_D127=True,
        owner_approval='pending_new_api_runner_postimage_not_covered_by_D127').items()),
        'new API packet metadata differs')
    pinned(PACKET / 'api_runner_companion.preimage', API_PRE)
    pinned(PACKET / 'api_runner_companion.postimage', API_POST)
    api_patch = pinned(PACKET / 'api_runner_companion.patch', API_PATCH)
    base.need(api_patch == ORIGINAL_BLOB(PREVIOUS, base.PACKET_DIRECTORY + '/api_runner_companion.patch'),
              'new API patch is not exactly D127')
    canonical_metadata = D127 / 'canonical_hashes.json'
    canonical_raw = pinned(canonical_metadata, CANONICAL_METADATA)
    canonical = json.loads(canonical_raw)
    expected = dict(target=PACKETS[2][1], preimage_sha256=PACKETS[2][2],
                    postimage_sha256=CANONICAL_POST, patch_sha256=CANONICAL_PATCH)
    base.need(all(canonical.get(k) == v for k, v in expected.items()), 'D127 canonical metadata differs')
    canonical_patch = pinned(D127 / 'canonical_hashes.patch', CANONICAL_PATCH)
    pinned(D127 / 'canonical_hashes.preimage', PACKETS[2][2])
    pinned(D127 / 'canonical_hashes.postimage', CANONICAL_POST)
    facts_path = PACKET / 'FACTS.json'
    regular(facts_path)
    facts = json.loads(facts_path.read_bytes())
    base.need(facts['status'] == 'proposal_ready_owner_approval_pending'
              and facts['merge_commit'] == MERGE and facts['forward_reverse_clean'] is True
              and facts['api_metadata_sha256'] == base.sha(metadata_raw), 'proposal facts differ')
    return {base.PACKET_DIRECTORY + '/api_runner_companion.json': (metadata_path, metadata_raw),
            base.PACKET_DIRECTORY + '/canonical_hashes.json': (canonical_metadata, canonical_raw),
            base.PACKET_DIRECTORY + '/canonical_hashes.patch': (D127 / 'canonical_hashes.patch', canonical_patch)}


def local_entries(tree):
    return ORIGINAL_GIT('config', '--local', '--null', '--list', cwd=tree).split(b'\0')[:-1]


def setup(args):
    preimages = require_source(args.commit)
    overrides = packet_inputs()
    evidence = OUT / ('composition-' + args.commit[:12])
    worktree = OUT / ('worktree-' + args.commit[:12])
    base.need(not os.path.lexists(evidence) and not os.path.lexists(worktree), 'fresh composition/worktree required')
    evidence.mkdir()
    tree = evidence / 'tree'
    apply_calls = []
    original_packet_names = [str(tree / base.PACKET_DIRECTORY / (row[0] + '.patch')) for row in PACKETS]

    def packet_blob(commit, relative):
        if relative in overrides:
            base.need(commit == args.commit, 'packet override requested for another commit')
            path, raw = overrides[relative]
            base.need(pinned(path, base.sha(raw)) == raw, 'packet override changed')
            return raw
        return ORIGINAL_BLOB(commit, relative)

    def packet_git(*command, cwd=ROOT):
        if command and command[0] == 'apply':
            base.need(cwd == tree and list(command) in [
                ['apply', '--check', *original_packet_names], ['apply', *original_packet_names]],
                'unexpected private packet-application command')
            replacement = str(D127 / 'canonical_hashes.patch')
            pinned(Path(replacement), CANONICAL_PATCH)
            redirected = tuple(replacement if value == original_packet_names[2] else value for value in command)
            apply_calls.append(dict(requested=list(command), executed=list(redirected), cwd=str(cwd)))
            return ORIGINAL_GIT(*redirected, cwd=cwd)
        return ORIGINAL_GIT(*command, cwd=cwd)

    result = dict(kind='native_u3m_private_composition', version=1, status='incomplete', started_utc=now(),
        source_commit=args.commit, source_worktree=str(ROOT), merge_commit=MERGE, fixed_main=MAIN,
        helper_sha256=base.sha(Path(__file__).read_bytes()), composer_sha256=base.sha(BASE_FILE.read_bytes()),
        destination=str(evidence), worktree=str(worktree), test_worktree=str(worktree),
        protected_preimages_sha256=preimages, packet_directory=str(PACKET),
        owner_approval='pending_new_api_runner_postimage_not_covered_by_D127',
        packet_input_overrides={relative: dict(path=str(path), sha256=base.sha(raw))
                                for relative, (path, raw) in overrides.items()})
    try:
        base.PACKETS = PACKETS
        base.strict_blob, base.git = packet_blob, packet_git
        inherited = base.compose(args, evidence)
        result['original_composition'] = inherited
        child = inherited['composition_commit']
        expected = {row[1]: row[3] for row in PACKETS}
        base.need(len(apply_calls) == 2 and all(base.sha((tree / path).read_bytes()) == digest
                  for path, digest in expected.items()), 'final four-packet composition differs')
        base.sidecar_check(tree, ORIGINAL_BLOB(args.commit, PACKETS[-1][1]))
        ORIGINAL_GIT('worktree', 'add', '--detach', str(worktree), child, cwd=tree)
        base.need(worktree.resolve(strict=True) == worktree and (worktree / '.git').is_file(),
                  'physical private test worktree required')
        common = Path(ORIGINAL_GIT('rev-parse', '--path-format=absolute', '--git-common-dir', cwd=worktree).decode().strip())
        base.need(common == tree / '.git' and ORIGINAL_GIT('rev-parse', 'HEAD', cwd=worktree).decode().strip() == child
                  and not ORIGINAL_GIT('status', '--porcelain', cwd=worktree).strip()
                  and not ORIGINAL_GIT('remote', cwd=worktree).strip(), 'private worktree identity differs')
        base.need(all(base.sha((worktree / path).read_bytes()) == digest for path, digest in expected.items()),
                  'test worktree packet bytes differ')
        config = common / 'config'
        regular(config)
        backup = common / 'config.bak-u3m-20261109'
        original, entries = config.read_bytes(), local_entries(tree)
        base.need(not any(row.partition(b'\n')[0].lower() == CI_KEY.encode() for row in entries),
                  'fresh private config already contains CI URL')
        write(backup, original)
        os.chmod(backup, stat.S_IMODE(config.stat().st_mode))
        row = dict(path=str(config), backup=str(backup), original_sha256=base.sha(original),
                   original_mode=stat.S_IMODE(config.stat().st_mode), key=CI_KEY, value=CI_VALUE)
        result['private_config'] = row
        ORIGINAL_GIT('config', '--local', 'd4d.ciRepositoryUrl', CI_VALUE, cwd=tree)
        row['configured_sha256'] = base.sha(config.read_bytes())
        base.need(local_entries(tree) == entries + [CI_KEY.encode() + b'\n' + CI_VALUE.encode()],
                  'private config changed beyond the one CI URL')
        base.need(require_source(args.commit) == preimages, 'source preimages changed')
        result.update(status='composed_not_tested', composition_commit=child, composition_parent=args.commit,
            composition_tree=inherited['composition_tree'], composition_commit_sha256=inherited['composition_commit_sha256'],
            private_git=str(common), test_root=str(worktree), packet_postimages_sha256=expected,
            packet_apply_commands=apply_calls,
            scope='Private offline U3-M measurement only; new API postimage owner approval and native acceptance remain pending.')
    except BaseException as exc:
        result.update(status='refused', error_type=type(exc).__name__, reason=str(exc))
        raise
    finally:
        base.strict_blob, base.git = ORIGINAL_BLOB, ORIGINAL_GIT
        result['ended_utc'] = now()
        digest = save(evidence / 'composition.json', result)
        print(json.dumps(dict(status=result['status'], manifest=str(evidence / 'composition.json'), sha256=digest)), flush=True)


def cleanup(args):
    require_source(args.commit)
    evidence = OUT / ('composition-' + args.commit[:12])
    worktree = OUT / ('worktree-' + args.commit[:12])
    manifest = evidence / 'composition.json'
    regular(manifest)
    recorded = json.loads(manifest.read_bytes())
    base.need(recorded['source_commit'] == args.commit and recorded['test_worktree'] == str(worktree),
              'cleanup manifest identity differs')
    row = recorded['private_config']
    config, backup = Path(row['path']), Path(row['backup'])
    base.need(config == evidence / 'tree/.git/config'
              and backup == config.with_name('config.bak-u3m-20261109'), 'cleanup path differs')
    original = pinned(backup, row['original_sha256'])
    pinned(config, row['configured_sha256'])
    report = evidence / 'config-restored.json'
    temporary = config.with_name('config.restore-u3m-20261109')
    base.need(not os.path.lexists(report) and not os.path.lexists(temporary), 'cleanup already started')
    with temporary.open('xb') as stream:
        stream.write(original)
        stream.flush()
        os.fsync(stream.fileno())
    os.chmod(temporary, row['original_mode'])
    os.replace(temporary, config)
    base.need(config.read_bytes() == original and not any(item.partition(b'\n')[0].lower() == CI_KEY.encode()
              for item in local_entries(evidence / 'tree')), 'private config restoration differs')
    restored = dict(status='config_restored_evidence_and_worktree_retained', ended_utc=now(),
                    composition_manifest_sha256=base.sha(manifest.read_bytes()), source_commit=args.commit,
                    restored_sha256=base.sha(config.read_bytes()), backup_sha256=base.sha(backup.read_bytes()),
                    worktree=str(worktree), worktree_preserved=worktree.is_dir(),
                    helper_sha256=base.sha(Path(__file__).read_bytes()))
    digest = save(report, restored)
    print(json.dumps(dict(status=restored['status'], manifest=str(report), sha256=digest)), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('packet', 'setup', 'cleanup'))
    parser.add_argument('--commit', required=True, help='Full current clean source HEAD, including this helper')
    parser.add_argument('--fairscape-source', help='Optional exact local FAIRSCAPE Git repository')
    args = parser.parse_args()
    {'packet': packet, 'setup': setup, 'cleanup': cleanup}[args.action](args)


if __name__ == '__main__':
    main()
