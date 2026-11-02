#!/usr/bin/env python3
"""PR #5213 task7: clone a verified git-archive copy without duplicating data blocks.

2026-11-02. Inputs: SHA-bound archive proof, full head, fresh destination/evidence.
Outputs: independent copy-on-write files, before/after inventories and compatible
archive proof. macOS clonefile only; no fallback, network, cleanup or source edits.
"""
import argparse
import copy
import ctypes
import json
import os
from pathlib import Path
import stat
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import archive_d76_round3_source_20261102 as archive
import d76_suite_common_20261031 as common


def inventory(root):
    def refuse_incomplete(error):
        raise error
    rows = {}
    for directory, dirs, files in os.walk(root, followlinks=False, onerror=refuse_incomplete):
        for name in sorted(dirs + files):
            path = Path(directory) / name
            info = path.lstat()
            key = path.relative_to(root).as_posix()
            if stat.S_ISLNK(info.st_mode):
                rows[key] = {'kind': 'symlink', 'target': os.readlink(path)}
            elif stat.S_ISDIR(info.st_mode):
                rows[key] = {'kind': 'directory', 'mode': stat.S_IMODE(info.st_mode)}
            elif stat.S_ISREG(info.st_mode):
                rows[key] = {'kind': 'file', 'mode': stat.S_IMODE(info.st_mode),
                             'bytes': info.st_size, 'sha256': archive.sha(path)}
            else:
                raise ValueError('special source entry refused: ' + key)
    return rows


def assert_source(root, report):
    for directory, expected in ((root, report), (root / 'fairscape_models', report['fairscape'])):
        snapshot = common.source(directory)
        if (snapshot['head'] != expected['head'] or snapshot['tree'] != expected['git_tree']
                or snapshot['tracked_exact'] is not True):
            raise ValueError('source bytes do not match pinned Git tree')
        # No exclude options: include ignored files when proving the copy has no extras.
        if archive.value(directory, 'ls-files', '--others'):
            raise ValueError('source contains untracked or ignored files')
        if archive.value(directory, 'status', '--porcelain=v1', '--untracked-files=all'):
            raise ValueError('source index or working tree is dirty')


def clone_tree(source, destination, rows):
    if sys.platform != 'darwin':
        raise ValueError('this helper requires macOS clonefile; no copy fallback')
    library = ctypes.CDLL('/usr/lib/libSystem.B.dylib', use_errno=True)
    clone = library.clonefile
    clone.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_int]
    clone.restype = ctypes.c_int
    destination.mkdir(exist_ok=False)
    for name, row in sorted(rows.items(), key=lambda item: (len(Path(item[0]).parts), item[0])):
        original, target = source / name, destination / name
        if row['kind'] == 'directory':
            target.mkdir(mode=row['mode'])
            target.chmod(row['mode'])
        elif row['kind'] == 'symlink':
            target.symlink_to(row['target'])
        else:
            if clone(os.fsencode(original), os.fsencode(target), 0) != 0:
                error = ctypes.get_errno()
                raise OSError(error, os.strerror(error), str(target))
            a, b = original.stat(), target.stat()
            if (a.st_dev, a.st_ino) == (b.st_dev, b.st_ino):
                raise ValueError('clone unexpectedly shares source inode: ' + name)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--proof', type=Path, required=True)
    parser.add_argument('--proof-sha256', required=True)
    parser.add_argument('--head', required=True)
    parser.add_argument('--destination', type=Path, required=True)
    parser.add_argument('--evidence', type=Path, required=True)
    args = parser.parse_args()
    if archive.sha(args.proof) != args.proof_sha256:
        raise ValueError('archive proof digest differs')
    report = copy.deepcopy(json.loads(args.proof.read_text()))
    if (report['head'] != args.head or report['source_method'] !=
            'git archive; metadata initialized afterwards without checkout'):
        raise ValueError('wrong archive source/head')
    source = Path(report['destination'])
    archive.physical_parent(source)
    if source.is_symlink() or not source.is_dir() or source.resolve(strict=True) != source:
        raise ValueError('physical archive source required')
    for path in (args.destination, args.evidence):
        archive.physical_parent(path)
        if path.exists() or path.is_symlink() or path.is_relative_to(source):
            raise ValueError('fresh destination outside source required')
    if args.destination == args.evidence or args.evidence.is_relative_to(args.destination):
        raise ValueError('separate evidence and source directories required')
    for row in (report, report['fairscape']):
        path = Path(row['archive'])
        if path.is_symlink() or archive.sha(path) != row['archive_sha256']:
            raise ValueError('retained archive bytes changed')
    assert_source(source, report)
    before = inventory(source)
    args.evidence.mkdir(exist_ok=False)
    common.save(args.evidence / 'source-inventory-before.json', before)
    clone_tree(source, args.destination, before)
    after, copied = inventory(source), inventory(args.destination)
    common.save(args.evidence / 'source-inventory-after.json', after)
    common.save(args.evidence / 'destination-inventory.json', copied)
    if before != after or before != copied:
        raise ValueError('source changed or cloned bytes/modes differ')
    assert_source(args.destination, report)
    report.update(destination=str(args.destination), status='',
        copy_method='macOS clonefile per regular file; distinct inodes; no fallback',
        copied_from={'path': str(source), 'proof': str(args.proof), 'sha256': args.proof_sha256},
        copy_helper_sha256=archive.sha(Path(__file__).resolve()),
        clone_inventories={name: archive.sha(args.evidence / name) for name in (
            'source-inventory-before.json', 'source-inventory-after.json', 'destination-inventory.json')})
    common.save(args.evidence / 'archive-source.json', report)
    print(args.evidence / 'archive-source.json')
    print(archive.sha(args.evidence / 'archive-source.json'))


if __name__ == '__main__':
    main()
