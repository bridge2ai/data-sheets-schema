#!/usr/bin/env python3
"""Retain U3-D9/D10 synthetic witnesses before transient cleanup, updated 2026-11-08.

Inputs: explicitly named completed runs under scratch-native-u3d. Outputs:
verified relative-path witness copies and a new direct-child JSON inventory.
Includes hidden/ignored files; never follows fixture links or deletes anything.
"""
import argparse
from collections import Counter, defaultdict
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
SCRATCH = ROOT.parent / 'scratch-native-u3d'
LOCK = ROOT.parent / 'plans/native_quiet_window.lock'
BUNDLES = (
    frozenset(('render-digests.json', 'normalized-receipt-render.json', 'new-instruction.txt')),
    frozenset(('cpu-smoke.json', 'cpu-smoke-assembly.json')),
)
WITNESSES = frozenset().union(*BUNDLES)
REQUIRED = ('plan.json', 'pytest.xml', 'pytest.log', 'outcome.json',
            'source-stability.json', 'origins-before.json', 'origins-after.json')


def walk(root, exclude=None):
    """lstat callers classify entries; os.walk never follows symlink dirs."""
    def fail(error):
        raise error
    for parent, directories, names in os.walk(root, followlinks=False, onerror=fail):
        directories.sort()
        names.sort()
        if exclude is not None:
            directories[:] = [name for name in directories if Path(parent) / name != exclude]
        for name in directories + names:
            yield Path(parent) / name


def regular(path, *, keep=False, needle=None):
    """Never block on a FIFO or dereference the final path component."""
    fd = os.open(path, os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW)
    with os.fdopen(fd, 'rb') as stream:
        before = os.fstat(stream.fileno())
        if not stat.S_ISREG(before.st_mode):
            raise ValueError('not a regular file: ' + str(path))
        digest, chunks, tail, found = hashlib.sha256(), [], b'', False
        while chunk := stream.read(1024 * 1024):
            digest.update(chunk)
            if keep:
                chunks.append(chunk)
            if needle is not None:
                found |= needle in tail + chunk
                tail = chunk[-len(needle):]
        after = os.fstat(stream.fileno())
    identity = lambda info: (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns)
    if identity(before) != identity(after) or identity(after) != identity(path.lstat()):
        raise ValueError('file changed while reading: ' + str(path))
    return {'bytes': after.st_size, 'sha256': digest.hexdigest(), 'nlink': after.st_nlink,
            'device': after.st_dev, 'inode': after.st_ino}, b''.join(chunks), found


def completed(directory):
    artifacts, raw = {}, {}
    for name in REQUIRED:
        artifacts[name], raw[name], _ = regular(directory / name, keep=True)
        if not raw[name]:
            raise ValueError('empty completion artifact: ' + name)
    plan = json.loads(raw['plan.json'])
    outcome = json.loads(raw['outcome.json'])
    stability = json.loads(raw['source-stability.json'])
    code = outcome.get('returncode')
    worker = outcome.get('worker') or {}
    if (type(code) is not int or code not in (0, 1)
            or worker.get('returncode') != code or outcome.get('worker_returncode') != code
            or worker.get('source_origin_checks_passed') is not True
            or outcome.get('cleanup_verified') is not True
            or outcome.get('forced_cleanup') is not False
            or outcome.get('interrupted') is not None
            or outcome.get('observed_surviving_pids') != []
            or outcome.get('observation_errors') != []
            or not 0 < outcome.get('seconds', 0) < 3600):
        raise ValueError('incomplete/invalid run; retain basetemp: ' + directory.name)
    before, after = stability.get('before', {}), stability.get('after', {})
    if (stability.get('unchanged') is not True or before != after
            or before.get('head') != plan.get('source_commit')
            or re.fullmatch(r'[0-9a-f]{40}', before.get('head', '')) is None
            or before.get('status') != ''):
        raise ValueError('source stability failed: ' + directory.name)
    counts = Counter()
    for case in ET.fromstring(raw['pytest.xml']).iter('testcase'):
        counts[next((tag for tag in ('error', 'failure', 'skipped')
                     if case.find(tag) is not None), 'passed')] += 1
    return {'source_commit': plan['source_commit'], 'outcome': outcome,
            'source_stable': True, 'counts': dict(counts), 'artifacts': artifacts}


def retain(source, destination, run, expected):
    current = run
    for component in destination.parent.relative_to(run).parts:
        current /= component
        current.mkdir(exist_ok=True)
        if current.resolve(strict=True) != current or not stat.S_ISDIR(current.lstat().st_mode):
            raise ValueError('unsafe retained parent: ' + str(current))
    info, raw, _ = regular(source, keep=True)
    if not raw or info != expected:
        raise ValueError('witness empty or changed: ' + str(source))
    if not os.path.lexists(destination):
        fd = os.open(destination, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        with os.fdopen(fd, 'wb') as stream:
            stream.write(raw)
    copied, _, _ = regular(destination)
    if (copied['bytes'], copied['sha256']) != (info['bytes'], info['sha256']):
        raise ValueError('retained witness differs: ' + str(destination))
    return {'path': str(destination.relative_to(run)), 'bytes': copied['bytes'],
            'sha256': copied['sha256']}


def inventory(name, links):
    directory, target = SCRATCH / name, SCRATCH / name / 'cases'
    for path in (directory, target):
        if path.resolve(strict=True) != path or not stat.S_ISDIR(path.lstat().st_mode):
            raise ValueError('not a literal run/basetemp directory: ' + str(path))
    result = completed(directory)
    handles = subprocess.run(['/usr/sbin/lsof', '+D', str(target)], capture_output=True,
                             text=True, timeout=45)
    if handles.returncode not in (0, 1) or handles.stderr.strip() or handles.stdout.strip():
        raise ValueError('open handles or incomplete lsof observation: ' + str(target))
    inbound = [str(path) for path, resolved in links if not path.is_relative_to(target)
               and (resolved == target or resolved.is_relative_to(target))]
    if inbound:
        raise ValueError('external inbound links: ' + repr(inbound))
    entries, inodes, witnesses = {}, defaultdict(list), []
    for path in walk(target):
        info = path.lstat()
        kind = ('regular' if stat.S_ISREG(info.st_mode) else 'directory' if stat.S_ISDIR(info.st_mode)
                else 'symlink' if stat.S_ISLNK(info.st_mode) else 'special')
        row = {'kind': kind, 'allocated_bytes': info.st_blocks * 512}
        if kind == 'regular':
            row.update(regular(path)[0])
            inodes[(info.st_dev, info.st_ino)].append(path)
        elif kind == 'symlink':
            row['link_text'] = os.readlink(path)
        entries[str(path.relative_to(target))] = row
        if path.name in WITNESSES:
            if kind != 'regular':
                raise ValueError('nonregular witness: ' + str(path))
            witnesses.append(path)
    for paths in inodes.values():
        if paths[0].lstat().st_nlink != len(paths):
            raise ValueError('hard links outside basetemp: ' + repr(paths))
    groups = defaultdict(set)
    for path in witnesses:
        groups[path.parent].add(path.name)
    for parent, names in groups.items():
        for bundle in BUNDLES:
            if names & bundle and not bundle <= names:
                raise ValueError('incomplete witness bundle: ' + str(parent))
    retained = [retain(path, directory / 'retained' / path.relative_to(target), directory,
                       {key: entries[str(path.relative_to(target))][key]
                        for key in ('bytes', 'sha256', 'nlink', 'device', 'inode')})
                for path in witnesses]
    references = []
    for path in walk(directory, exclude=target):
        if stat.S_ISREG(path.lstat().st_mode) and regular(path, needle=str(target).encode())[2]:
            references.append(str(path.relative_to(directory)))
    result.update({'target': str(target), 'inventory': entries, 'retained': retained,
                   'open_handles': [], 'external_inbound_links': [],
                   'reference_scope': str(directory), 'regular_file_references': references,
                   'hidden_and_ignored_files_included': True})
    # Recheck completion artifacts after retaining witnesses, before approval.
    if completed(directory)['artifacts'] != result['artifacts']:
        raise ValueError('completion evidence changed during inventory: ' + name)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runs', nargs='+', required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    if os.path.lexists(LOCK):
        parser.error('quiet-window lock exists')
    if (len(set(args.runs)) != len(args.runs)
            or any(re.fullmatch(r'round(?:9|10)-[a-z0-9-]+', name) is None for name in args.runs)):
        parser.error('runs must be unique literal round9 or round10 names')
    output = args.out.absolute()
    if (output.parent != SCRATCH or output.parent.resolve(strict=True) != SCRATCH
            or os.path.lexists(output)):
        parser.error('manifest must be a new direct child of D scratch')
    links, unresolved = [], []
    for path in walk(SCRATCH):
        if stat.S_ISLNK(path.lstat().st_mode):
            try:
                links.append((path, path.resolve()))
            except (OSError, RuntimeError) as error:
                # Deliberate fixture loops are recorded, never traversed.
                unresolved.append({'path': str(path), 'error': str(error)})
    value = {'kind': 'native_u3d_round9_basetemp_retention', 'version': 1,
             'scope': 'No deletion; completed synthetic basetemps only.',
             'symlink_search_scope': str(SCRATCH), 'unresolved_symlinks': unresolved,
             'runs': {name: inventory(name, links) for name in args.runs}}
    if os.path.lexists(LOCK):
        raise ValueError('quiet-window lock appeared; do not use partial retention as approval')
    raw = (json.dumps(value, indent=2, sort_keys=True) + '\n').encode()
    with output.open('xb') as stream:
        stream.write(raw)
    if regular(output, keep=True)[1] != raw:
        raise ValueError('manifest readback differs')
    print(json.dumps({'manifest': str(output), 'sha256': hashlib.sha256(raw).hexdigest(),
                      'targets': len(value['runs'])}, sort_keys=True))


if __name__ == '__main__':
    main()
