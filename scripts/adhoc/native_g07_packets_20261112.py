#!/usr/bin/env python3
"""Prepare G07's four reviewed postimages and isolated composition, 2026-11-12.

Inputs: pinned main/native Git objects, retained D127 packets, committed helper.
Outputs: exclusive sibling scratch packets/private Git tree and provenance JSON.
No network, provider/native execution, shared-ref/config or protected branch edit.
"""
from __future__ import annotations
import argparse
import ast
from datetime import datetime, timezone
import difflib
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile

ROOT = Path(__file__).resolve().parents[2]
EXEC = ROOT.parent
SCRATCH = EXEC / 'scratch-native-main-integration-20261112'
D127 = EXEC / 'scratch-native-u1u3/owner-packets/u3h/e0b964b0e182'
MAIN = '7ad8c9e7295f1575ae9108ea62c12c83b1dd4db1'
OLDER_MAIN = '2cfc4666c2d81003d9cf5f432248b4217ef477e1'
NATIVE = '1a137b58860416a31618de44173180d021dfcc61'
BASE = 'a68efbd687e5caa31223415e6397f6a66638f37b'
ROWS = (
 ('shared_generation', 'src/data_sheets_schema/shared_generation.py',
  '2ec18e60316423035f88a2a30263c56385bfbbc587303e84e805a8349ab4f781'),
 ('api_runner_companion', 'src/data_sheets_schema/api_runner.py',
  '3e8b7e5d3cc13c5ebc508e33f865e9ac484056fde16126118719d740656a4fb7'),
 ('canonical_hashes', 'src/download/prompts/canonical_hashes.yaml',
  '543e5cd6dc0da0f622ba2cd11a16a90732e9302a1ed0a4700efb61971299d252'),
 ('run_spec_boundary_contracts', 'tests/utils/run_spec_boundary_contracts.json',
  'b1e0cbd14c533a51b88eacb84b974cb93963e18d8f1fb71ae4ed3228f784d1ce'),
)
SPARSE = ['.claude', '.github', 'src', 'tests', 'utils', 'scripts', 'notes', 'docs',
          'project', 'config', 'configs', 'examples', 'linkml_mappings',
          'data/rubric', 'data/preprocessed', 'data/_wcrate', 'data/ro-crate_packages']
ENV = {'PATH': '/usr/bin:/bin:/usr/sbin:/sbin', 'HOME': '/var/empty', 'LC_ALL': 'C',
       'GIT_CONFIG_GLOBAL': '/dev/null', 'GIT_CONFIG_SYSTEM': '/dev/null',
       'GIT_NO_LAZY_FETCH': '1', 'GIT_TERMINAL_PROMPT': '0', 'GIT_OPTIONAL_LOCKS': '0',
       'GIT_AUTHOR_NAME': 'Offline native packet preparation',
       'GIT_COMMITTER_NAME': 'Offline native packet preparation',
       'GIT_AUTHOR_EMAIL': 'scratch' + chr(64) + 'invalid',
       'GIT_COMMITTER_EMAIL': 'scratch' + chr(64) + 'invalid',
       'GIT_AUTHOR_DATE': '2026-11-12T00:00:00+00:00',
       'GIT_COMMITTER_DATE': '2026-11-12T00:00:00+00:00'}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def quiet():
    if os.path.lexists(EXEC / 'plans/native_quiet_window.lock'):
        raise RuntimeError('quiet-window lock exists; preserve evidence and stop')


def git(*args, cwd=ROOT):
    quiet()
    result = subprocess.run(['/usr/bin/git', '--no-replace-objects', '-c', 'protocol.allow=never',
        '-c', 'core.hooksPath=/dev/null', '-c', 'core.fsmonitor=false', '-c', 'commit.gpgsign=false',
        *args], cwd=cwd, env=ENV, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        timeout=300, check=False)
    if result.returncode:
        raise RuntimeError('local git failed: ' + ' '.join(args) + '\n' + result.stderr.decode())
    quiet()
    return result.stdout


def blob(commit, path):
    return git('show', commit + ':' + path)


def save(path, value):
    raw = (json.dumps(value, indent=2, sort_keys=True) + '\n').encode()
    write(path, raw)
    return sha(raw)


def write(path, raw):
    path.parent.mkdir(parents=True, exist_ok=True)
    assert path.parent.resolve() == path.parent and not path.is_symlink()
    with path.open('xb') as out:
        out.write(raw)
    assert path.read_bytes() == raw


def diff(before, after, target):
    return ''.join(difflib.unified_diff(before.decode().splitlines(keepends=True),
        after.decode().splitlines(keepends=True), fromfile='a/' + target,
        tofile='b/' + target)).encode()


def check_roster(tree, main_raw):
    previous = json.loads(main_raw)
    roster = json.loads((tree / ROWS[3][1]).read_bytes())
    assert len(previous['contracts']) == len(roster['contracts']) == 21
    assert previous['approval'] == roster['approval']
    for old, new in zip(previous['contracts'], roster['contracts']):
        assert {k: v for k, v in old.items() if not k.startswith('function_')} == {
            k: v for k, v in new.items() if not k.startswith('function_')}
        raw = (tree / new['source_path']).read_bytes()
        nodes = [n for n in ast.parse(raw).body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
                 and n.name == new['identity'].rsplit('.', 1)[-1]]
        assert len(nodes) == 1
        node = nodes[0]
        start = min([node.lineno, *[d.lineno for d in node.decorator_list]])
        body = b''.join(raw.splitlines(keepends=True)[start - 1:node.end_lineno])
        expected = {'function_start_line': start, 'function_end_line': node.end_lineno,
                    'function_bytes': len(body), 'function_sha256': sha(body)}
        assert all(new[k] == value for k, value in expected.items()), new['identity']
    for path, digest in roster['source_sha256'].items():
        assert sha((tree / path).read_bytes()) == digest, path
    assert roster['shared_generation_sha256'] == ROWS[0][2]


def prepare(label):
    quiet()
    assert ROOT.name == 'codex-native-main-integration-20261112' and ROOT.resolve() == ROOT
    assert EXEC.name == 'd4d-executions' and EXEC.resolve() == EXEC
    assert label.replace('-', '').isalnum()
    if shutil.disk_usage(ROOT).free < 10 * 1024**3:
        raise RuntimeError('less than 10 GiB free')
    commit = git('rev-parse', 'HEAD').decode().strip()
    git('merge-base', '--is-ancestor', BASE, commit)
    git('diff-index', '--quiet', 'HEAD', '--')
    relative = str(Path(__file__).relative_to(ROOT))
    assert blob(commit, relative) == Path(__file__).read_bytes(), 'commit this exact helper first'
    assert not SCRATCH.is_symlink()
    SCRATCH.mkdir(exist_ok=True)
    assert SCRATCH.resolve() == SCRATCH
    out = SCRATCH / label
    out.mkdir()
    result = {'status': 'incomplete', 'source_commit': commit, 'source_branch':
        git('branch', '--show-current').decode().strip(), 'source_root': str(ROOT),
        'fixed_main': MAIN, 'native_donor': NATIVE, 'started_utc': datetime.now(timezone.utc).isoformat(),
        'helper_sha256': sha(Path(__file__).read_bytes()), 'packets': [],
        'scope': 'offline scratch proposal; protected branch bytes remain main; no publication or launch'}
    try:
        packets = out / 'packets'; packets.mkdir()
        for name, target, approved in ROWS:
            before = blob(MAIN, target)
            assert before == blob(OLDER_MAIN, target) == blob(commit, target) == (ROOT / target).read_bytes()
            accepted = (D127 / (name + '.postimage')).read_bytes()
            assert sha(accepted) == approved
            d127_before = (D127 / (name + '.preimage')).read_bytes()
            post = accepted
            if name == 'api_runner_companion':
                assert sha(d127_before) == 'db9a0f67ba7ace06bc8b39f90a00a3fe98ee72a34e553be6d48f97bff5e6d848'
                donor = blob(NATIVE, target)
                assert sha(donor) == 'b109cb918a3079a384937ccfad7ab9b195a55713a355f11f848da98fab59596a'
                anchor = (b'        if not self.native_shared_generation_version:\n'
                          b'            from .shared_generation import select as select_shared\n'
                          b'            select_shared(self)\n')
                replacement = (b'        from .shared_generation import select as select_shared\n'
                               b'        select_shared(self)\n')
                assert donor.count(anchor) == 1
                post = donor.replace(anchor, replacement, 1)
                assert sha(post) == '830eec1e12e96f807fa76ea26e066a1923b60380013c424cfa99f0012af0a881'
            else:
                assert before == d127_before
            packet = diff(before, post, target)
            write(packets / (name + '.preimage'), before)
            write(packets / (name + '.postimage'), post)
            write(packets / (name + '.patch'), packet)
            write(packets / (name + '.since-d127.diff'), diff(accepted, post, target))
            write(packets / (name + '.main-vs-d127-preimage.diff'), diff(d127_before, before, target))
            trial = out / 'forward-reverse' / name
            write(trial / target, before)
            patch_path = str(packets / (name + '.patch'))
            for options in (('--check',), (), ('--reverse', '--check'), ('--reverse',)):
                git('apply', *options, patch_path, cwd=trial)
            assert (trial / target).read_bytes() == before
            result['packets'].append({'name': name, 'path': target,
                'main_sha256': sha(before), 'postimage_sha256': sha(post),
                'd127_approved_sha256': approved, 'equals_d127': sha(post) == approved,
                'patch': patch_path, 'patch_sha256': sha(packet),
                'since_d127_diff': str(packets / (name + '.since-d127.diff')),
                'forward_reverse_verified': True})
        save(out / 'packet-hashes.json', result)
        tree = out / 'tree'; tree.mkdir()
        git('init', '-q', '--object-format=sha1', cwd=tree)
        objects = git('rev-parse', '--path-format=absolute', '--git-path', 'objects').decode().strip()
        write(tree / '.git/objects/info/alternates', (objects + '\n').encode())
        git('update-ref', '--no-deref', 'HEAD', commit, cwd=tree)
        git('read-tree', commit, cwd=tree)
        git('sparse-checkout', 'set', '--cone', *SPARSE, cwd=tree)
        git('read-tree', '-mu', 'HEAD', cwd=tree)
        assert not git('remote', cwd=tree).strip()
        assert not git('diff', '--name-only', cwd=tree).strip()
        paths = [row['patch'] for row in result['packets']]
        git('apply', '--check', *paths, cwd=tree)
        git('apply', *paths, cwd=tree)
        assert set(git('diff', '--name-only', cwd=tree).decode().splitlines()) == {row[1] for row in ROWS}
        check_roster(tree, blob(MAIN, ROWS[3][1]))
        git('add', '--', *[row[1] for row in ROWS], cwd=tree)
        tree_sha = git('write-tree', cwd=tree).decode().strip()
        private = git('commit-tree', tree_sha, '-p', commit, '-m',
            'Offline G07 four-packet proposal; no protected branch approval or launch authority', cwd=tree).decode().strip()
        git('update-ref', '--no-deref', 'HEAD', private, cwd=tree)
        assert git('rev-parse', '--abbrev-ref', 'HEAD', cwd=tree).decode().strip() == 'HEAD'
        assert not git('diff-index', '--name-only', 'HEAD', '--', cwd=tree).strip()
        config = tree / '.git/config'
        write(config.with_name('config.bak-g07-20261112'), config.read_bytes())
        original_config_sha = sha(config.read_bytes())
        git('config', '--local', 'd4d.ciRepositoryUrl', 'https://github.com/bridge2ai/data-sheets-schema.git', cwd=tree)
        link = git('ls-tree', commit, 'fairscape_models').decode().split()
        assert link[:2] == ['160000', 'commit']
        fairscape_source = EXEC.parent / 'data-sheets-schema/fairscape_models'
        archive = out / 'fairscape.tar'
        git('archive', '--format=tar', '--output=' + str(archive), link[2], cwd=fairscape_source)
        target = tree / 'fairscape_models'; target.mkdir(exist_ok=True)
        with tarfile.open(archive) as stream:
            stream.extractall(target, filter='data')
        assert (target / 'fairscape_models/rocrate.py').read_bytes() == git(
            'show', link[2] + ':fairscape_models/rocrate.py', cwd=fairscape_source)
        for row in result['packets']:
            assert sha((tree / row['path']).read_bytes()) == row['postimage_sha256']
            assert (ROOT / row['path']).read_bytes() == blob(MAIN, row['path'])
        write(out / 'packet-only.diff', git('diff', '--binary', commit, private, cwd=tree))
        result.update(status='composed_not_tested', composition_commit=private,
            composition_tree=tree_sha, tree=str(tree), private_git=str(tree / '.git'),
            sparse_selection=SPARSE, fairscape_commit=link[2],
            config_original_sha256=original_config_sha,
            config_configured_sha256=sha(config.read_bytes()),
            config_restore_pending=True)
    except BaseException as exc:
        result.update(status='refused', error_type=type(exc).__name__, error=str(exc))
        raise
    finally:
        result['ended_utc'] = datetime.now(timezone.utc).isoformat()
        digest = save(out / 'composition.json', result)
        print(json.dumps({'path': str(out / 'composition.json'), 'sha256': digest, 'status': result['status']}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('label')
    prepare(parser.parse_args().label)
