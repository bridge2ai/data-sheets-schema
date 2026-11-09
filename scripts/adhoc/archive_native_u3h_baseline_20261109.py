"""Archive literal U3-F2 for U3-H's itemized comparison, 2026-11-09.

Input: fixed local 77bfa2336 commit. Output: exclusive full read-only-source
archive/private Git checkout under u3h. No packet installation or network.
"""
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
COMMIT = '77bfa23368af201b77585f334ed0456ed1d40f01'


def main():
    s = importlib.util.spec_from_file_location('u3h_archive_policy',
        ROOT / 'scripts/adhoc/compose_native_u1u3_20261108.py')
    c = importlib.util.module_from_spec(s)
    s.loader.exec_module(c)
    c.quiet()
    head = c.git('rev-parse', 'HEAD').decode().strip()
    c.need(c.strict_blob(head, str(Path(__file__).relative_to(ROOT))) == Path(__file__).read_bytes(),
           'archive helper must be committed')
    out = c.SCRATCH / 'u3h/f2-literal-77bfa23368af'
    out.mkdir()
    archive = out / 'source.tar'
    c.git('archive', '--format=tar', '--output=' + str(archive), COMMIT)
    tree = out / 'tree'
    tree.mkdir()
    members = c.extract(archive, tree)
    c.git('init', '-q', '--object-format=sha1', cwd=tree)
    objects = c.git('rev-parse', '--path-format=absolute', '--git-path', 'objects').decode().strip()
    (tree / '.git/objects/info/alternates').write_text(objects + '\n')
    c.git('update-ref', '--no-deref', 'HEAD', COMMIT, cwd=tree)
    c.git('read-tree', COMMIT, cwd=tree)
    c.git('diff-index', '--quiet', 'HEAD', '--', cwd=tree)
    c.need(not c.git('remote', cwd=tree).strip(), 'archive must have no remote')
    roster = c.git('ls-tree', '-rz', '--full-tree', COMMIT, cwd=tree)
    (out / 'input-roster.bin').write_bytes(roster)
    row = dict(source_commit=COMMIT, source_tree=c.git('rev-parse', COMMIT + '^{tree}').decode().strip(),
        tree=str(tree), archive_sha256=c.file_sha(archive), archive_bytes=archive.stat().st_size,
        archive_members=members, input_roster_sha256=c.sha(roster),
        helper_sha256=c.sha(Path(__file__).read_bytes()), packets_installed=False,
        scope='Literal F2; derivation refusal is retained and never replaced by a composed baseline.')
    with (out / 'manifest.json').open('x') as f:
        json.dump(row, f, indent=2, sort_keys=True)
        f.write('\n')
    print(json.dumps(row))


if __name__ == '__main__':
    main()
