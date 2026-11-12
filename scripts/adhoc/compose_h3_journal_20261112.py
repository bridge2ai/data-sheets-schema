#!/usr/bin/env python3
"""Build the explicitly authorized private public-path proof, 2026-11-12.
Inputs: pinned candidate, seven helper commits, verified four post-images.
Outputs: isolated detached scratch Git tree and immutable composition receipt.
No shared Git writes, protected branch edits, network or native execution.
"""
from pathlib import Path
import importlib.util
import json
import tarfile
import hashlib
E = Path('/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions')
C = E / 'codex-native-main-integration-20261112'
R = E / 'codex-development-efficiency-20261111'
S = E / 'scratch-h3-launch-hardening-20261112'
import argparse
parser = argparse.ArgumentParser()
parser.add_argument('--base', required=True)
parser.add_argument('--name', required=True)
parser.add_argument('--patch', type=Path)
args = parser.parse_args()
base = args.base
commits = []
spec = importlib.util.spec_from_file_location('packets', C / 'scripts/adhoc/native_g07_packets_20261112.py')
h = importlib.util.module_from_spec(spec); spec.loader.exec_module(h)
S.mkdir(exist_ok=True)
out = S / args.name; out.mkdir()
tree = out / 'tree'; tree.mkdir()
record = {'status': 'building', 'candidate': base, 'tree': str(tree), 'applied': [], 'packets': []}
try:
    h.git('cat-file', '-e', base)
    packet_base = E / 'scratch-native-main-integration-20261112/g07-c'
    packet_raw = (packet_base / 'packet-hashes.json').read_bytes()
    record['packet_manifest_sha256'] = h.sha(packet_raw)
    for row in json.loads(packet_raw)['packets']:
        raw = (packet_base / 'packets' / (row['name'] + '.postimage')).read_bytes()
        assert h.sha(raw) == row['postimage_sha256']
        assert h.sha(h.blob(base, row['path'])) == row['main_sha256']
        record['packets'].append(row)
    h.git('init', '-q', '--object-format=sha1', cwd=tree)
    objects = h.git('rev-parse', '--path-format=absolute', '--git-path', 'objects').decode().strip()
    h.write(tree / '.git/objects/info/alternates', (objects + '\n').encode())
    h.git('update-ref', '--no-deref', 'HEAD', base, cwd=tree)
    h.git('sparse-checkout', 'set', '--cone', *h.SPARSE, cwd=tree)
    h.git('read-tree', '-mu', 'HEAD', cwd=tree)
    parent = base
    if args.patch:
        patch = args.patch.resolve(strict=True)
        h.git('apply', '--index', '--check', str(patch), cwd=tree)
        h.git('apply', '--index', str(patch), cwd=tree)
        new_tree = h.git('write-tree', cwd=tree).decode().strip()
        parent = h.git('commit-tree', new_tree, '-p', parent, '-m', 'Offline own working repair rehearsal', cwd=tree).decode().strip()
        h.git('update-ref', '--no-deref', 'HEAD', parent, cwd=tree)
        record['working_patch'] = {'path': str(patch), 'sha256': h.sha(patch.read_bytes())}
    for short in commits:
        commit = h.git('rev-parse', short).decode().strip()
        patch = h.git('diff', '--binary', commit + '^', commit)
        path = out / (short + '.patch'); h.write(path, patch)
        h.git('apply', '--index', '--check', str(path), cwd=tree)
        h.git('apply', '--index', str(path), cwd=tree)
        new_tree = h.git('write-tree', cwd=tree).decode().strip()
        parent = h.git('commit-tree', new_tree, '-p', parent, '-m', 'Offline composition of ' + commit, cwd=tree).decode().strip()
        h.git('update-ref', '--no-deref', 'HEAD', parent, cwd=tree)
        record['applied'].append({'commit': commit, 'patch_sha256': h.sha(patch), 'private_commit': parent})
    for row in record['packets']:
        raw = (packet_base / 'packets' / (row['name'] + '.postimage')).read_bytes()
        (tree / row['path']).write_bytes(raw)
        assert h.sha((tree / row['path']).read_bytes()) == row['postimage_sha256']
    h.check_roster(tree, h.blob(h.MAIN, h.ROWS[3][1]))
    h.git('add', '--', *(row['path'] for row in record['packets']), cwd=tree)
    new_tree = h.git('write-tree', cwd=tree).decode().strip()
    parent = h.git('commit-tree', new_tree, '-p', parent, '-m', 'Authorized offline four-packet public-path composition', cwd=tree).decode().strip()
    h.git('update-ref', '--no-deref', 'HEAD', parent, cwd=tree)
    assert not h.git('remote', cwd=tree).strip()
    assert not h.git('diff', '--name-only', cwd=tree).strip()
    config = tree / '.git/config'
    h.write(config.with_name('config.bak-h3-failure-20261112'), config.read_bytes())
    record['config_original_sha256'] = h.sha(config.read_bytes())
    h.git('config', '--local', 'd4d.ciRepositoryUrl', 'https://github.com/bridge2ai/data-sheets-schema.git', cwd=tree)
    record['config_configured_sha256'] = h.sha(config.read_bytes())
    link = h.git('ls-tree', base, 'fairscape_models').decode().split()
    archive = out / 'fairscape.tar'
    h.git('archive', '--format=tar', '--output=' + str(archive), link[2], cwd=E.parent / 'data-sheets-schema/fairscape_models')
    target = tree / 'fairscape_models'; target.mkdir(exist_ok=True)
    with tarfile.open(archive) as stream: stream.extractall(target, filter='data')
    record.update(status='composed_not_tested', composition_commit=parent, composition_tree=new_tree,
                  private_git=str(tree / '.git'), fairscape_commit=link[2], config_restore_pending=True)
except BaseException as exc:
    record.update(status='refused', error=str(exc), error_type=type(exc).__name__)
    raise
finally:
    h.save(out / 'composition.json', record)
    print(json.dumps(record, indent=2))
