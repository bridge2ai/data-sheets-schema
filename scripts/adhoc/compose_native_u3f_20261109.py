"""U3-F four-packet private composition and revised owner bundle, 2026-11-09.

Input: committed current repair HEAD plus frozen U1 packets. Output: exclusive
scratch-native-u1u3/u3f composition and versioned owner-packets/u3f bundle.
No protected worktree edit; no shared ref, network, hook or provider operation.
"""
import ast
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[2]

def load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'scripts/adhoc' / (name+'.py'))
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value

def main():
    c = load('compose_native_u1u3_20261108')
    roster = load('document_native_u3f_boundaries_20261109').CONTRACTS
    c.quiet()
    commit = c.git('rev-parse', 'HEAD').decode().strip()
    out = c.SCRATCH / 'u3f' / ('composition-'+commit[:12])
    out.mkdir()
    manifest = c.compose(SimpleNamespace(commit=commit, fairscape_source=None), out)
    tree = Path(manifest['tree'])
    target = c.PACKETS[-1][1]
    sidecar = json.loads((tree / target).read_bytes())
    declarations = []
    for path in sorted((tree / 'src/data_sheets_schema').rglob('*.py')):
        raw = path.read_bytes()
        syntax = ast.parse(raw)
        relative = path.relative_to(tree).as_posix()
        module = '.'.join(path.relative_to(tree / 'src/data_sheets_schema').with_suffix('').parts)
        def walk(nodes, prefix=''):
            for node in nodes:
                if isinstance(node, ast.ClassDef):
                    walk(node.body, prefix+node.name+'.')
                elif isinstance(node, ast.FunctionDef):
                    identity = module+'.'+prefix+node.name
                    if identity in roster:
                        doc = ast.get_docstring(node)
                        assert 'RunSpec boundary: validated-caller' in doc
                        assert roster[identity] in doc
                        start = min([node.lineno, *[d.lineno for d in node.decorator_list]])
                        body = b''.join(raw.splitlines(keepends=True)[start-1:node.end_lineno])
                        declarations.append(dict(identity='data_sheets_schema.'+identity,
                            source_path=relative, source_sha256=c.sha(raw),
                            function_start_line=start, function_end_line=node.end_lineno,
                            function_sha256=c.sha(body), function_bytes=len(body),
                            proposed_mode='validated-caller', proposed_precondition=roster[identity]))
        walk(syntax.body)
    assert len(declarations) == len(roster)
    # The checker still reads exactly its original 21 protected contracts.
    # Native contracts are executable-source docstrings, not new exemptions.
    # This supplemental owner evidence records their exact reviewed pins and
    # does not extend the historical approval ruling to this pending revision.
    sidecar['native_boundary_declarations'] = {
        'status': 'proposed_u3f_owner_review_required',
        'basis': 'Source docstrings checked by unchanged D76 inventory; not protected-contract exemptions.',
        'source_commit': commit, 'declarations': declarations}
    (tree / target).write_text(json.dumps(sidecar, indent=2)+'\n')
    c.sidecar_check(tree, c.strict_blob(commit, target))
    c.git('add', '--', target, cwd=tree)
    tree_sha = c.git('write-tree', cwd=tree).decode().strip()
    child = c.git('commit-tree', tree_sha, '-p', commit, '-m',
        'Offline U3-F four-packet composition; revised D76 source declarations', cwd=tree).decode().strip()
    c.git('update-ref', '--no-deref', 'HEAD', child, cwd=tree)
    manifest.update(composition_commit=child, private_head=child, composition_tree=tree_sha)
    bundle = c.SCRATCH / 'owner-packets/u3f' / commit[:12]
    bundle.mkdir(parents=True)
    packets = []
    for name, path, before_sha, u1_sha, u1_patch_sha in c.PACKETS:
        before = c.strict_blob(commit, path)
        after = (tree / path).read_bytes()
        patch = c.git('diff', '--binary', '--full-index', commit, child, '--', path, cwd=tree)
        # Preserve unchanged U1 patch bytes rather than reserializing them.
        changed = c.sha(after) != u1_sha
        if not changed:
            patch = (ROOT / c.PACKET_DIRECTORY / (name+'.patch')).read_bytes()
        (bundle / (name+'.patch')).write_bytes(patch)
        (bundle / (name+'.preimage')).write_bytes(before)
        (bundle / (name+'.postimage')).write_bytes(after)
        row = dict(name=name, target=path, preimage_sha256=c.sha(before),
            postimage_sha256=c.sha(after), patch_sha256=c.sha(patch),
            changed_from_u1=changed, u1_postimage_sha256=u1_sha, u1_patch_sha256=u1_patch_sha,
            reason=('Add exact source-declaration evidence for 42 native/factory boundaries; preserve the 21 approved protected identities and unchanged checker.'
                    if changed else 'Unchanged U1 packet; no U4b api_runner delta.'))
        assert row['preimage_sha256'] == before_sha
        (bundle / (name+'.json')).write_text(json.dumps(row, indent=2)+'\n')
        packets.append(row)
    manifest['packets'] = packets
    diff = c.git('diff', '--binary', '--full-index', commit, child, cwd=tree)
    (out / 'packet-only.diff').write_bytes(diff)
    manifest['packet_only_diff_sha256'] = c.sha(diff)
    raw_commit = c.git('cat-file', '-p', child, cwd=tree)
    (out / 'composition-commit.txt').write_bytes(raw_commit)
    manifest['composition_commit_sha256'] = c.sha(raw_commit)
    manifest['owner_bundle'] = str(bundle)
    manifest['status'] = 'composed_not_tested'
    (out / 'composition.json').write_text(json.dumps(manifest, indent=2)+'\n')
    (bundle / 'manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')
    assert not c.git('diff-index', '--name-only', 'HEAD', '--', cwd=tree).strip()
    assert set(c.git('diff', '--name-only', commit, child, cwd=tree).decode().splitlines()) == {p[1] for p in c.PACKETS}
    print(json.dumps(dict(tree=str(tree), manifest=str(out / 'composition.json'), owner_bundle=str(bundle))))

if __name__ == '__main__':
    main()
