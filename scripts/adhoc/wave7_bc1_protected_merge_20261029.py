#!/usr/bin/env python3
# Purpose: guard BC1 packet merges without changing protected shared-generation bytes.
# Inputs: assigned real Git heads and one exact attributes file; outputs: fresh merge evidence.
# Refs BC1/Wave7 Task5, #5158/#5162/#5164/#5210/#5212/#5211; 2026-10-29. Offline only.
"""Read-only pre/post checks and a keep-first merge driver that never writes %A."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess

PROTECTED = 'src/data_sheets_schema/shared_generation.py'
BLOB = '91105618cd25e33962b1c2d30f20b37101530bb2'
SHA = '1c4436b5ea689fcd674c848a722dd9a86495692ad83401682f3d805f49acb6d6'
DRIVER = 'bc1-keep-first'
ROOT = Path(__file__).resolve().parents[2]
ATTRS = ROOT / 'scripts/adhoc/wave7_bc1_keep_first_20261029.attributes'
LOG = Path('/private/tmp/d4d-wave7-bc1-merge-evidence-20261029/driver.jsonl')
HEADS = {
    'cd07f2a3738e146eeaa30ae86d35d3161eb3413b',
    '8b885ee68262474275316755c3fc55dc05517dcb',
    '90312e30e8d957e3b79510abe9ea768967983224',
    'fba016d92fd292c66d580006e848b8c43eb59505',
    '20def9d63a3131ef9b56eca39b61fbf5f6aaab49',
    '3c41133fcdcdb6db4d09564dc365b8b42b39c390',
}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def git(*args, ok=(0,)):
    result = subprocess.run(['git', '-C', str(ROOT), *args], capture_output=True)
    if result.returncode not in ok:
        raise RuntimeError(result.stderr.decode('utf-8', 'replace'))
    return result.stdout.decode()


def raw_file(path):
    if not stat.S_ISREG(path.lstat().st_mode):
        raise ValueError('regular nonsymlink file required: ' + str(path))
    return path.read_bytes()


def tree_row(ref):
    line = git('ls-tree', ref, '--', PROTECTED).strip()
    left, name = line.split('\t')
    mode, kind, blob = left.split()
    if name != PROTECTED or (mode, kind) != ('100644', 'blob'):
        raise ValueError('protected path has an unexpected tree mode/type')
    return {'ref': ref, 'mode': mode, 'blob': blob}


def protected_state():
    head = git('rev-parse', 'HEAD').strip()
    current = tree_row(head)
    index = git('ls-files', '--stage', '--', PROTECTED).strip()
    if current['blob'] != BLOB or index != '100644 ' + BLOB + ' 0\t' + PROTECTED:
        raise ValueError('protected HEAD/index differs; stop without restoring')
    raw = raw_file(ROOT / PROTECTED)
    if sha(raw) != SHA or git('hash-object', str(ROOT / PROTECTED)).strip() != BLOB:
        raise ValueError('protected working bytes differ; stop without restoring')
    attrs_raw = raw_file(ATTRS)
    if attrs_raw != (PROTECTED + ' merge=' + DRIVER + '\n').encode():
        raise ValueError('unexpected scoped attributes file')
    query = git('-c', 'core.attributesFile=' + str(ATTRS), 'check-attr', '-z',
                'merge', 'filter', 'text', 'eol', 'working-tree-encoding', '--', PROTECTED).split('\0')
    attributes = {query[i + 1]: query[i + 2] for i in range(0, len(query) - 1, 3)}
    if attributes != {'merge': DRIVER, 'filter': 'unspecified', 'text': 'unspecified',
                      'eol': 'unspecified', 'working-tree-encoding': 'unspecified'}:
        raise ValueError('effective protected-path attributes differ: ' + repr(attributes))
    return {'head': head, 'protected_blob': BLOB, 'protected_sha256': SHA,
            'protected_mode': '100644', 'attributes': attributes,
            'helper_sha256': sha(raw_file(Path(__file__).resolve())),
            'attributes_sha256': sha(attrs_raw)}


def write_new(path, result):
    path = Path(path)
    if not path.is_absolute() or path.resolve() != path or path.exists():
        raise ValueError('fresh absolute physical evidence path required')
    if path.is_relative_to(ROOT):
        raise ValueError('active merge evidence must be outside the worktree')
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x') as stream:
        json.dump(result, stream, indent=2, sort_keys=True)
        stream.write('\n')


def preflight(args):
    state = protected_state()
    if git('status', '--porcelain=v1') or git('rev-parse', '-q', '--verify', 'MERGE_HEAD', ok=(0, 1)):
        raise ValueError('preflight requires a clean tree and no active merge')
    incoming = tree_row(args.incoming)
    bases = [tree_row(ref) for ref in git('merge-base', '--all', 'HEAD', args.incoming).splitlines()]
    if not bases or args.effective_base_blob not in {row['blob'] for row in bases}:
        raise ValueError('declared effective file base must be one of the actual merge-base blobs')
    if len(bases) == 1 and bases[0]['blob'] != args.effective_base_blob:
        raise ValueError('single merge base differs')
    if len(bases) > 1 and not args.virtual_basis:
        raise ValueError('multiple bases require a separately reviewed file-level union explanation')
    if args.effective_base_blob == BLOB and incoming['blob'] != BLOB:
        raise ValueError('trivial fast path would bypass keep-first driver; stop')
    state.update(incoming=incoming, merge_bases=bases, effective_base_blob=args.effective_base_blob,
                 virtual_base_basis=args.virtual_basis,
                 expected_behavior=('incoming equals effective base; preserve current bytes without file merge'
                    if incoming['blob'] == args.effective_base_blob else 'three-way file merge invokes keep-first driver'),
                 scope='preflight only; no merge or source edit')
    write_new(args.output, state)
    print(json.dumps(state, sort_keys=True))


def postflight(args):
    state = protected_state()
    conflicts = git('diff', '--name-only', '--diff-filter=U').splitlines()
    captured = {}
    for name in conflicts:
        lines = raw_file(ROOT / name).decode().splitlines(keepends=True)
        hunks, start = [], None
        for number, line in enumerate(lines):
            if line.startswith('<<<<<<< '):
                start = number
            elif start is not None and line.startswith('>>>>>>> '):
                hunks.append({'line': start + 1, 'text': ''.join(lines[start:number + 1])})
                start = None
        captured[name] = {'index_stages': git('ls-files', '--unmerged', '--', name), 'hunks': hunks}
    state.update(merge_head=git('rev-parse', '-q', '--verify', 'MERGE_HEAD', ok=(0, 1)).strip() or None,
                 conflicts=captured, scope='protected postcheck and verbatim ordinary conflict evidence')
    write_new(args.output, state)
    print(json.dumps({'head': state['head'], 'merge_head': state['merge_head'],
                      'conflicts': list(captured), 'protected_sha256': SHA}, sort_keys=True))


def keep_first(args):
    if args.path != PROTECTED or sha(raw_file(Path(args.current))) != SHA:
        raise ValueError('driver did not receive the exact protected first-parent bytes')
    row = {'path': args.path, 'base_sha256': sha(raw_file(Path(args.base))),
           'current_sha256': SHA, 'incoming_sha256': sha(raw_file(Path(args.incoming_file))),
           'action': 'return success without opening current for writing'}
    if not LOG.parent.is_dir() or LOG.parent.is_symlink() or (LOG.exists() and LOG.is_symlink()):
        raise ValueError('driver evidence directory must already exist and be physical')
    fd = os.open(LOG, os.O_WRONLY | os.O_APPEND | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'a') as stream:
        stream.write(json.dumps(row, sort_keys=True) + '\n')
    if sha(raw_file(Path(args.current))) != SHA:
        raise ValueError('protected current bytes changed during driver')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_subparsers(dest='mode', required=True)
    pre = modes.add_parser('preflight')
    pre.add_argument('--incoming', choices=sorted(HEADS), required=True)
    pre.add_argument('--effective-base-blob', required=True)
    pre.add_argument('--virtual-basis')
    pre.add_argument('--output', required=True)
    pre.set_defaults(function=preflight)
    post = modes.add_parser('postflight')
    post.add_argument('--output', required=True)
    post.set_defaults(function=postflight)
    driver = modes.add_parser('keep-first')
    for name in ('base', 'current', 'incoming_file', 'path'):
        driver.add_argument(name)
    driver.set_defaults(function=keep_first)
    args = parser.parse_args()
    args.function(args)


if __name__ == '__main__':
    main()
