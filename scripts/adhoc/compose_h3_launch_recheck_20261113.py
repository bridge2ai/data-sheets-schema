#!/usr/bin/env python3
"""6048/6047, 2026-11-13: compose repairs on the published candidate offline.
Inputs: local candidate and hardening commits. Outputs: private scratch Git
tree, patch and provenance. No shared branch writes, native call or network.
"""
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import tarfile
import sys

E = Path('/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions')
W = E / 'codex-native-launch-sequence-hardening-20261112'
C = E / 'codex-native-main-integration-20261112'
S = E / 'scratch-h3-launch-hardening-20261112'
BASE = '8760de5efe88b5af62e9d77e6335fa7e248017b6'
OLD = 'c39526da9a01c41f4a168e58d45f2dea4ad10c00'


def complete_manifest(out):
    path = out / 'composition.json'
    record = json.loads(path.read_bytes())
    tree = out / 'tree'
    assert record['base'] == BASE and record['tree'] == str(tree)
    head = subprocess.check_output(['git', '-C', str(tree), 'rev-parse', 'HEAD']).decode().strip()
    assert head == record['private_commit']
    assert not subprocess.check_output(['git', '-C', str(tree), 'diff', '--name-only']).strip()
    rows = []
    for relative in ('src/data_sheets_schema/shared_generation.py', 'src/data_sheets_schema/api_runner.py',
                     'src/download/prompts/canonical_hashes.yaml', 'tests/utils/run_spec_boundary_contracts.json'):
        expected = subprocess.check_output(['git', '-C', str(tree), 'show', BASE + ':' + relative])
        assert (tree / relative).read_bytes() == expected
        rows.append({'path': relative, 'postimage_sha256': hashlib.sha256(expected).hexdigest()})
    with (out / 'composition-before-runner-seal.json').open('xb') as backup:
        backup.write(path.read_bytes())
    record.update(status='composed_not_tested', composition_commit=head, packets=rows)
    path.write_text(json.dumps(record, indent=2) + '\n')
    print(json.dumps(record, indent=2))


def apply_working_followup(out):
    """Test the prepared correction without rewriting any shared branch."""
    outcome = json.loads((S / 'tests/recheck-composed-final/outcome.json').read_bytes())
    assert outcome['returncode'] == 0 and outcome['cleanup_verified']
    path = out / 'composition.json'
    record = json.loads(path.read_bytes())
    tree = out / 'tree'
    assert subprocess.check_output(['git', '-C', str(tree), 'rev-parse', 'HEAD']).decode().strip() == record['composition_commit']
    patch = subprocess.check_output(['git', '-C', str(W), 'diff', '--binary'])
    assert patch
    names = subprocess.check_output(['git', '-C', str(W), 'diff', '--name-only']).decode().splitlines()
    assert set(names) == {'src/data_sheets_schema/native_subscription_capture.py',
                         'tests/test_native_sequence_capture_dispatch.py'}
    patch_path = out / 'unspent-followup.patch'
    with patch_path.open('xb') as stream:
        stream.write(patch)
    with (out / 'composition-before-unspent.json').open('xb') as stream:
        stream.write(path.read_bytes())
    env = dict(__import__('os').environ)
    env.update(GIT_CONFIG_GLOBAL='/dev/null', GIT_CONFIG_SYSTEM='/dev/null', GIT_TERMINAL_PROMPT='0')
    def call(*args):
        return subprocess.check_output(['git', '-c', 'core.hooksPath=/dev/null', '-C', str(tree), *args], env=env)
    call('apply', '--index', '--check', str(patch_path))
    call('apply', '--index', str(patch_path))
    new_tree = call('write-tree').decode().strip()
    parent = record['composition_commit']
    head = call('commit-tree', new_tree, '-p', parent, '-m', 'Offline prepared under-lock unspent correction').decode().strip()
    call('update-ref', '--no-deref', 'HEAD', head, parent)
    record.update(composition_commit=head, private_commit=head, full_cohort_commit=parent,
        working_followup={'path': str(patch_path), 'sha256': hashlib.sha256(patch).hexdigest()})
    path.write_text(json.dumps(record, indent=2) + '\n')
    print(json.dumps(record, indent=2))


def main():
    if sys.argv[1:] == ['--complete-manifest']:
        complete_manifest(S / 'recheck-composed')
        return
    if sys.argv[1:] == ['--apply-working-followup']:
        apply_working_followup(S / 'recheck-composed')
        return
    assert not sys.argv[1:]
    spec = importlib.util.spec_from_file_location('packets', C / 'scripts/adhoc/native_g07_packets_20261112.py')
    h = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(h)
    out = S / 'recheck-composed'
    out.mkdir()
    tree = out / 'tree'
    tree.mkdir()
    head = subprocess.check_output(['git', '-C', str(W), 'rev-parse', 'HEAD']).decode().strip()
    assert not subprocess.check_output(['git', '-C', str(W), 'status', '--porcelain']).strip()
    patch = subprocess.check_output(['git', '-C', str(W), 'diff', '--binary', OLD, head])
    patch_path = out / 'repairs.patch'
    patch_path.write_bytes(patch)
    h.git('init', '-q', '--object-format=sha1', cwd=tree)
    objects = h.git('rev-parse', '--path-format=absolute', '--git-path', 'objects').decode().strip()
    h.write(tree / '.git/objects/info/alternates', (objects + '\n').encode())
    h.git('update-ref', '--no-deref', 'HEAD', BASE, cwd=tree)
    h.git('sparse-checkout', 'set', '--cone', *h.SPARSE, cwd=tree)
    h.git('read-tree', '-mu', 'HEAD', cwd=tree)
    h.git('apply', '--index', '--check', str(patch_path), cwd=tree)
    h.git('apply', '--index', str(patch_path), cwd=tree)
    tree_id = h.git('write-tree', cwd=tree).decode().strip()
    commit = h.git('commit-tree', tree_id, '-p', BASE, '-m', 'Offline launch recheck repairs on published candidate', cwd=tree).decode().strip()
    h.git('update-ref', '--no-deref', 'HEAD', commit, cwd=tree)
    assert not h.git('remote', cwd=tree).strip()
    config = tree / '.git/config'
    original = config.read_bytes()
    config.with_name('config.bak-h3-failure-20261112').write_bytes(original)
    h.git('config', '--local', 'd4d.ciRepositoryUrl', 'https://github.com/bridge2ai/data-sheets-schema.git', cwd=tree)
    link = h.git('ls-tree', BASE, 'fairscape_models').decode().split()
    archive = out / 'fairscape.tar'
    h.git('archive', '--format=tar', '--output=' + str(archive), link[2], cwd=E.parent / 'data-sheets-schema/fairscape_models')
    target = tree / 'fairscape_models'
    target.mkdir(exist_ok=True)
    with tarfile.open(archive) as stream:
        stream.extractall(target, filter='data')
    record = {'base': BASE, 'hardening_head': head, 'repair_base': OLD,
        'tree': str(tree), 'private_commit': commit, 'patch_sha256': hashlib.sha256(patch).hexdigest(),
        'config_original_sha256': h.sha(original), 'config_configured_sha256': h.sha(config.read_bytes()),
        'config_restore_pending': True, 'fairscape_commit': link[2], 'no_remote': True}
    h.save(out / 'composition.json', record)
    complete_manifest(out)


if __name__ == '__main__':
    main()
