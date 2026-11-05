#!/usr/bin/env python3
"""Extract another fresh D76 copy from retained pinned archives, 2026-11-02.

PR #5213 task7. Inputs: exact SHA-bound archive-source.json, full head, fresh
source/evidence directories. Output: another clean pinned copy and compatible
archive proof. Reuses retained tar bytes; no new archive/fetch or source edits.
"""
import argparse
import copy
import json
from pathlib import Path
import re
import sys
import tarfile

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import archive_d76_round3_source_20261102 as original


def extract(row, destination):
    path = Path(row['archive'])
    if path.is_symlink() or original.sha(path) != row['archive_sha256']:
        raise ValueError('retained archive bytes changed')
    if not re.fullmatch(r'[0-9a-f]{40}', row['head']):
        raise ValueError('full archive head required')
    objects = Path(row['local_object_alternate'])
    if not objects.is_absolute() or objects.resolve(strict=True) != objects or not objects.is_dir():
        raise ValueError('physical local object directory required')
    destination.mkdir(exist_ok=False)
    with tarfile.open(path, 'r:') as archive:
        archive.extractall(destination, members=original.safe_members(archive), filter='data')
    original.git(destination, 'init', '--quiet', '--template=')
    (destination / '.git/objects/info/alternates').write_text(str(objects) + '\n')
    (destination / '.git/HEAD').write_text(row['head'] + '\n')
    original.git(destination, 'read-tree', row['head'])
    if original.value(destination, 'rev-parse', 'HEAD^{tree}') != row['git_tree']:
        raise ValueError('archive head/tree identity differs')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--proof', type=Path, required=True)
    parser.add_argument('--proof-sha256', required=True)
    parser.add_argument('--head', required=True)
    parser.add_argument('--destination', type=Path, required=True)
    parser.add_argument('--evidence', type=Path, required=True)
    args = parser.parse_args()
    if original.sha(args.proof) != args.proof_sha256:
        raise ValueError('source proof differs from supplied SHA256')
    report = copy.deepcopy(json.loads(args.proof.read_text()))
    if report.get('head') != args.head or report.get('source_method') != 'git archive; metadata initialized afterwards without checkout':
        raise ValueError('wrong archive head or preparation method')
    for path in (args.destination, args.evidence):
        original.physical_parent(path)
        if path.exists() or path.is_symlink():
            raise ValueError('fresh physical source/evidence destinations required')
    args.evidence.mkdir(exist_ok=False)
    extract(report, args.destination)
    stage = args.destination / '.d76-fairscape-archive-staging'
    extract(report['fairscape'], stage)
    submodule = args.destination / 'fairscape_models'
    if submodule.exists():
        if submodule.is_symlink() or not submodule.is_dir() or any(submodule.iterdir()):
            raise ValueError('new archive gitlink placeholder unexpectedly nonempty')
        submodule.rmdir()  # Only the newly extracted empty gitlink placeholder.
    stage.rename(submodule)
    link = original.value(args.destination, 'ls-tree', 'HEAD', 'fairscape_models').split()
    if len(link) != 4 or link[2] != report['fairscape']['head']:
        raise ValueError('FAIRSCAPE archive does not match selected gitlink')
    report['destination'] = str(args.destination)
    report['status'] = original.value(args.destination, 'status', '--porcelain=v1', '--untracked-files=all')
    if report['status']:
        raise ValueError('re-extracted source not clean')
    report['reused_proof'] = {'path': str(args.proof), 'sha256': args.proof_sha256}
    report['copy_helper_sha256'] = original.sha(Path(__file__).resolve())
    report['archive_helper_sha256'] = original.sha(Path(original.__file__).resolve())
    with (args.evidence / 'archive-source.json').open('x') as stream:
        json.dump(report, stream, indent=2, sort_keys=True)
        stream.write('\n')
    print(args.evidence / 'archive-source.json')
    print(original.sha(args.evidence / 'archive-source.json'))


if __name__ == '__main__':
    main()
