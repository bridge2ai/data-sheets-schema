"""U3-F2: restore U1 D76 and normalize owner-packet repository paths.

Inputs: committed assigned HEAD and unchanged four U1 packets. Outputs: a new
private composition and owner bundle under scratch-native-u1u3/u3f2. No packets
are installed in a worktree; no network, provider or shared-ref operations.
2026-11-09, independent U3-F review P2-2/P3-7.
"""
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import yaml

ROOT = Path(__file__).resolve().parents[2]


def main():
    spec = importlib.util.spec_from_file_location('u3f2_composer',
        ROOT / 'scripts/adhoc/compose_native_u1u3_20261108.py')
    c = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(c)
    c.quiet()
    c.need(ROOT.parent.name == 'd4d-executions', 'unknown quiet-window location')
    commit = c.git('rev-parse', 'HEAD').decode().strip()
    c.need(c.strict_blob(commit, str(Path(__file__).relative_to(ROOT))) == Path(__file__).read_bytes(),
           'composition helper must be committed')
    parent = c.SCRATCH / 'u3f2'
    parent.mkdir(exist_ok=True)
    out = parent / ('composition-' + commit[:12])
    out.mkdir()
    manifest = c.compose(SimpleNamespace(commit=commit, fairscape_source=None), out)
    tree = Path(manifest['tree'])
    target = c.PACKETS[2][1]
    original = (tree / target).read_bytes()
    document = yaml.safe_load(original)
    replacements = []
    for path, row in document['files'].items():
        location = row.get('pinned_in_repository')
        if isinstance(location, str) and Path(location).is_absolute():
            # The commit and blob already exist in this repository: '.' is a
            # verifiable relative location, not an invented archive reference.
            raw = c.strict_blob(row['pinned_at_commit'], row['pinned_blob_path'])
            c.need(c.sha(raw) == row['sha256'], 'relative-root pin cannot be verified: ' + path)
            replacements.append(dict(path=path, before=location, after='.',
                pinned_at_commit=row['pinned_at_commit'], pinned_blob_path=row['pinned_blob_path'],
                pinned_blob_sha256=c.sha(raw)))
    c.need(bool(replacements), 'expected absolute U1 repository metadata was absent')
    after = original
    for location in sorted({row['before'] for row in replacements}):
        old = ('    pinned_in_repository: ' + location + '\n').encode()
        c.need(after.count(old) == sum(row['before'] == location for row in replacements),
               'canonical path serialization differs')
        after = after.replace(old, b'    pinned_in_repository: .\n')
    parsed = yaml.safe_load(after)
    expected = yaml.safe_load(original)
    for row in replacements:
        expected['files'][row['path']]['pinned_in_repository'] = '.'
    c.need(parsed == expected, 'canonical packet changed more than repository locations')
    for row in parsed['files'].values():
        location = row.get('pinned_in_repository')
        if location is not None:
            c.need(isinstance(location, str) and not Path(location).is_absolute()
                   and '..' not in Path(location).parts, 'nonlocal repository path remains')
    (tree / target).write_bytes(after)
    c.sidecar_check(tree, c.strict_blob(commit, c.PACKETS[-1][1]))
    c.need(c.sha((tree / c.PACKETS[-1][1]).read_bytes()) == c.PACKETS[-1][3],
           'D76 is not the exact recorded U1 packet')
    c.git('add', '--', target, cwd=tree)
    tree_sha = c.git('write-tree', cwd=tree).decode().strip()
    child = c.git('commit-tree', tree_sha, '-p', commit, '-m',
        'Offline U3-F2 composition: U1 D76 and relative canonical packet metadata', cwd=tree).decode().strip()
    c.git('update-ref', '--no-deref', 'HEAD', child, cwd=tree)
    bundle = c.SCRATCH / 'owner-packets/u3f2' / commit[:12]
    bundle.mkdir(parents=True)
    packets = []
    for name, path, before_sha, u1_sha, u1_patch_sha in c.PACKETS:
        before, post = c.strict_blob(commit, path), (tree / path).read_bytes()
        changed = c.sha(post) != u1_sha
        c.need(changed == (name == 'canonical_hashes'), 'unexpected packet changed from U1: ' + name)
        patch = (c.git('diff', '--binary', '--full-index', commit, child, '--', path, cwd=tree)
                 if changed else (ROOT / c.PACKET_DIRECTORY / (name + '.patch')).read_bytes())
        for suffix, raw in (('patch', patch), ('preimage', before), ('postimage', post)):
            (bundle / (name + '.' + suffix)).write_bytes(raw)
        row = dict(name=name, target=path, preimage_sha256=c.sha(before),
            postimage_sha256=c.sha(post), patch_sha256=c.sha(patch), changed_from_u1=changed,
            u1_postimage_sha256=u1_sha, u1_patch_sha256=u1_patch_sha,
            reason=('Only pinned_in_repository absolute paths become verified repository-relative dot.'
                    if changed else 'Exact U1 packet, including recorded D76; no supplemental declarations.'))
        c.need(row['preimage_sha256'] == before_sha, 'protected preimage changed')
        (bundle / (name + '.json')).write_text(json.dumps(row, indent=2) + '\n')
        packets.append(row)
    diff = c.git('diff', '--binary', '--full-index', commit, child, cwd=tree)
    raw_commit = c.git('cat-file', '-p', child, cwd=tree)
    (out / 'packet-only.diff').write_bytes(diff)
    (out / 'composition-commit.txt').write_bytes(raw_commit)
    manifest.update(composition_commit=child, private_head=child, composition_tree=tree_sha,
        composition_commit_sha256=c.sha(raw_commit), packet_only_diff_sha256=c.sha(diff),
        owner_bundle=str(bundle), packets=packets, canonical_repository_path_changes=replacements,
        status='composed_not_tested', helper_sha256=c.sha(Path(__file__).read_bytes()))
    for path in (out / 'composition.json', bundle / 'manifest.json'):
        path.write_text(json.dumps(manifest, indent=2) + '\n')
    paths = [str(bundle / (row['name'] + '.patch')) for row in packets]
    c.git('apply', '--check', *paths)
    c.git('apply', '--check', '--reverse', *paths, cwd=tree)
    c.need(not c.git('diff-index', '--name-only', 'HEAD', '--', cwd=tree).strip(), 'private tree is dirty')
    c.need(set(c.git('diff', '--name-only', commit, child, cwd=tree).decode().splitlines()) ==
           {row[1] for row in c.PACKETS}, 'unexpected composition paths')
    c.need(all(c.sha((ROOT / row['target']).read_bytes()) == row['preimage_sha256'] for row in packets),
           'protected worktree files changed')
    print(json.dumps(dict(tree=str(tree), manifest=str(out / 'composition.json'),
        owner_bundle=str(bundle), composition_commit=child, changed_packets=['canonical_hashes'])))


if __name__ == '__main__':
    main()
