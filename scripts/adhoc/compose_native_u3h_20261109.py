"""Compose the U3-H four-packet proposal, 2026-11-09 (U3-G review P1/P2).

Inputs: committed assigned HEAD and the frozen four U1 patches. Outputs: a new
private composition under scratch-native-u1u3/u3h and packet images/metadata
under owner-packets/u3h. Only the two U1 registry additions get relative location
metadata. No protected worktree edit, test execution, network, shared ref change
or owner-review prose. The final evidence writer supplies FACTS.json later.
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import yaml

ROOT = Path(__file__).resolve().parents[2]
EXPECTED_CANONICAL_SHA256 = '543e5cd6dc0da0f622ba2cd11a16a90732e9302a1ed0a4700efb61971299d252'
U1_LOCATION = '/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-native-u1/pins-41b7169f6'
U1_ADDITIONS = (
    'src/download/prompts/native_shared_generation_v1.md',
    'src/download/prompts/native_shared_receipt_policy_v1.md',
)


def normalize_u1_additions(c, original, historical):
    """Replace exactly two lines in the exact U1 image; keep old entries intact."""
    c.need(c.sha(original) == c.PACKETS[2][3], 'not the frozen U1 canonical postimage')
    c.need(c.sha(historical) == c.PACKETS[2][2], 'not the frozen historical registry')
    before = yaml.safe_load(original)
    old = yaml.safe_load(historical)
    c.need(set(before['files']) - set(old['files']) == set(U1_ADDITIONS),
           'U1 registry additions differ from the exact two assets')
    c.need(set(old['files']) <= set(before['files']), 'historical registry entries were removed')
    c.need({key: value for key, value in before.items() if key != 'files'} ==
           {key: value for key, value in old.items() if key != 'files'},
           'U1 changed historical registry document metadata')
    for path, row in old['files'].items():
        c.need(before['files'][path] == row, 'U1 changed historical entry: ' + path)
    replacements = []
    for path in U1_ADDITIONS:
        row = before['files'][path]
        c.need(row.get('pinned_in_repository') == U1_LOCATION,
               'unexpected U1 addition repository location: ' + path)
        c.need(row['pinned_at_commit'] == c.PROMPT_COMMIT and row['pinned_blob_path'] == path,
               'U1 asset pin identity differs: ' + path)
        raw = c.strict_blob(row['pinned_at_commit'], row['pinned_blob_path'])
        c.need(c.sha(raw) == row['sha256'] and len(raw) == row['bytes'],
               'relative U1 asset location cannot be verified: ' + path)
        replacements.append(dict(path=path, before=U1_LOCATION, after='.',
            pinned_at_commit=row['pinned_at_commit'], pinned_blob_path=row['pinned_blob_path'],
            pinned_blob_sha256=c.sha(raw)))
    old_line = ('    pinned_in_repository: ' + U1_LOCATION + '\n').encode()
    c.need(original.count(old_line) == 2, 'U1 location must occur on exactly two complete lines')
    after = original.replace(old_line, b'    pinned_in_repository: .\n')
    c.need(c.sha(after) == EXPECTED_CANONICAL_SHA256,
           'two-addition canonical postimage differs from independently reviewed variant')
    parsed = yaml.safe_load(after)
    expected = yaml.safe_load(original)
    for path in U1_ADDITIONS:
        expected['files'][path]['pinned_in_repository'] = '.'
    c.need(parsed == expected, 'canonical packet changed more than the two U1 locations')
    # Byte-level equality everywhere except the two literal location lines.
    before_lines, after_lines = original.splitlines(keepends=True), after.splitlines(keepends=True)
    c.need(len(before_lines) == len(after_lines), 'canonical line roster changed')
    changed = [(left, right) for left, right in zip(before_lines, after_lines) if left != right]
    c.need(changed == [(old_line, b'    pinned_in_repository: .\n')] * 2,
           'historical registry bytes or unrelated formatting changed')
    return after, replacements


def main():
    spec = importlib.util.spec_from_file_location('u3h_base_composer',
        ROOT / 'scripts/adhoc/compose_native_u1u3_20261108.py')
    c = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(c)
    c.quiet()
    c.need(ROOT.parent.name == 'd4d-executions', 'unknown quiet-window location')
    c.need(c.SCRATCH.resolve(strict=True) == c.SCRATCH, 'scratch root is aliased')
    commit = c.git('rev-parse', 'HEAD').decode().strip()
    c.need(c.strict_blob(commit, str(Path(__file__).relative_to(ROOT))) == Path(__file__).read_bytes(),
           'composition helper must be committed')
    parent = c.SCRATCH / 'u3h'
    parent.mkdir(exist_ok=True)
    c.need(parent.resolve(strict=True) == parent, 'composition parent is aliased')
    out = parent / ('composition-' + commit[:12])
    out.mkdir()
    manifest = c.compose(SimpleNamespace(commit=commit, fairscape_source=None), out)
    tree = Path(manifest['tree'])
    target = c.PACKETS[2][1]
    historical = c.strict_blob(commit, target)
    after, replacements = normalize_u1_additions(c, (tree / target).read_bytes(), historical)
    (tree / target).write_bytes(after)
    c.sidecar_check(tree, c.strict_blob(commit, c.PACKETS[-1][1]))
    c.need(c.sha((tree / c.PACKETS[-1][1]).read_bytes()) == c.PACKETS[-1][3],
           'D76 is not the exact recorded U1 packet')
    c.git('add', '--', target, cwd=tree)
    tree_sha = c.git('write-tree', cwd=tree).decode().strip()
    child = c.git('commit-tree', tree_sha, '-p', commit, '-m',
        'Offline U3-H composition: exact U1 hooks and only two new registry locations',
        cwd=tree).decode().strip()
    raw_commit = c.git('cat-file', '-p', child, cwd=tree)
    headers = raw_commit.split(b'\n\n', 1)[0].splitlines()
    c.need([line for line in headers if line.startswith(b'parent ')] == [b'parent ' + commit.encode()],
           'composition parent differs from source')
    c.need(headers[0] == b'tree ' + tree_sha.encode(), 'composition tree header differs')
    c.git('update-ref', '--no-deref', 'HEAD', child, cwd=tree)
    packet_parent = c.SCRATCH
    for component in ('owner-packets', 'u3h'):
        packet_parent = packet_parent / component
        c.need(not packet_parent.is_symlink(), 'packet ancestor is aliased')
        packet_parent.mkdir(exist_ok=True)
        c.need(packet_parent.resolve(strict=True) == packet_parent, 'packet ancestor is aliased')
    bundle = packet_parent / commit[:12]
    bundle.mkdir()
    c.need(bundle.resolve(strict=True) == bundle, 'packet bundle path is aliased')
    packets = []
    for name, path, before_sha, u1_sha, u1_patch_sha in c.PACKETS:
        c.quiet()
        before, post = c.strict_blob(commit, path), (tree / path).read_bytes()
        changed = c.sha(post) != u1_sha
        c.need(changed == (name == 'canonical_hashes'), 'unexpected packet changed from U1: ' + name)
        patch = (c.git('diff', '--binary', '--full-index', commit, child, '--', path, cwd=tree)
                 if changed else c.strict_blob(commit, c.PACKET_DIRECTORY + '/' + name + '.patch'))
        if not changed:
            c.need(c.sha(patch) == u1_patch_sha and c.sha(post) == u1_sha,
                   'unchanged U1 packet identity differs: ' + name)
        for suffix, raw in (('patch', patch), ('preimage', before), ('postimage', post)):
            with (bundle / (name + '.' + suffix)).open('xb') as stream:
                stream.write(raw)
        row = dict(name=name, target=path, preimage_sha256=c.sha(before),
            postimage_sha256=c.sha(post), patch_sha256=c.sha(patch), changed_from_u1=changed,
            u1_postimage_sha256=u1_sha, u1_patch_sha256=u1_patch_sha,
            reason=('Only the two new U1 native asset repository locations become verified dot; '
                    'all historical registry entries and other bytes remain unchanged.' if changed
                    else 'Exact U1 patch and postimage; no additional change.'))
        c.need(row['preimage_sha256'] == before_sha, 'protected preimage changed')
        with (bundle / (name + '.json')).open('x') as stream:
            stream.write(json.dumps(row, indent=2) + '\n')
        packets.append(row)
    diff = c.git('diff', '--binary', '--full-index', commit, child, cwd=tree)
    # The base composer wrote its original U1 commit witnesses inside this new
    # directory. Keep those initial identities before writing the final variant.
    (out / 'packet-only.diff').rename(out / 'u1-packet-only.diff')
    (out / 'composition-commit.txt').rename(out / 'u1-composition-commit.txt')
    with (out / 'packet-only.diff').open('xb') as stream:
        stream.write(diff)
    with (out / 'composition-commit.txt').open('xb') as stream:
        stream.write(raw_commit)
    manifest.update(composition_commit=child, private_head=child, composition_tree=tree_sha,
        composition_commit_sha256=c.sha(raw_commit), packet_only_diff_sha256=c.sha(diff),
        owner_bundle=str(bundle), packets=packets, canonical_repository_path_changes=replacements,
        canonical_historical_entries_unchanged=True, expected_canonical_sha256=EXPECTED_CANONICAL_SHA256,
        status='composed_not_tested', owner_review_status='pending_lead_text_not_written',
        facts_status='pending_final_evidence_writer', helper_sha256=c.sha(Path(__file__).read_bytes()))
    paths = [str(bundle / (row['name'] + '.patch')) for row in packets]
    c.git('apply', '--check', *paths)
    c.git('apply', '--check', '--reverse', *paths, cwd=tree)
    c.need(not c.git('diff-index', '--name-only', 'HEAD', '--', cwd=tree).strip(), 'private tree is dirty')
    c.need(set(c.git('diff', '--name-only', commit, child, cwd=tree).decode().splitlines()) ==
           {row[1] for row in c.PACKETS}, 'unexpected composition paths')
    c.need(all(c.sha((ROOT / row['target']).read_bytes()) == row['preimage_sha256'] for row in packets),
           'protected worktree files changed')
    c.need(c.git('rev-parse', 'HEAD').decode().strip() == commit, 'source HEAD moved during composition')
    c.git('diff-index', '--quiet', 'HEAD', '--')
    manifest.update(forward_check=True, reverse_check=True, worktree_packets_installed=False)
    for path in (out / 'composition.json', bundle / 'manifest.json'):
        with path.open('x') as stream:
            stream.write(json.dumps(manifest, indent=2) + '\n')
    c.quiet()
    print(json.dumps(dict(tree=str(tree), manifest=str(out / 'composition.json'),
        owner_bundle=str(bundle), composition_commit=child, changed_packets=['canonical_hashes'],
        owner_review_status=manifest['owner_review_status'], facts_status=manifest['facts_status'])))


if __name__ == '__main__':
    main()
