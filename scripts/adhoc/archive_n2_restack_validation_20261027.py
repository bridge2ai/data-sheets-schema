#!/usr/bin/env python3
# Purpose: preserve selected completed N2 result files without reinterpreting passes.
# Inputs: explicit completed evidence directories; output: fresh archive/manifest directory.
# Scope: top-level and neutral/omission JSON, log and XML files; cases/cache stay external.
# Refs #4354; 2026-10-27. Read-only inputs; no tests, providers or runtime execution.
"""Archive result evidence, not complete synthetic case trees or acceptance claims."""
from __future__ import annotations

import argparse
import gzip
import hashlib
import io
import json
import os
from pathlib import Path
import stat
import tarfile
import xml.etree.ElementTree as ET

STAGES = frozenset({'neutral', 'omission'})
SUFFIXES = frozenset({'.json', '.log', '.xml'})
MAX_FILE_BYTES = 128_000_000


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def physical(path):
    path = Path(path)
    if not path.is_absolute() or path.resolve(strict=True) != path:
        raise ValueError('physical absolute input required: ' + str(path))
    return path


def read_file(path):
    physical(path)
    before = path.stat(follow_symlinks=False)
    if not stat.S_ISREG(before.st_mode) or before.st_size > MAX_FILE_BYTES:
        raise ValueError('bounded regular evidence file required: ' + str(path))
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(descriptor, 'rb') as stream:
        opened = os.fstat(stream.fileno())
        raw = stream.read(MAX_FILE_BYTES + 1)
        after = os.fstat(stream.fileno())
    def identity(value):
        return (value.st_dev, value.st_ino, value.st_mode, value.st_size,
                value.st_mtime_ns, value.st_ctime_ns)
    if (len(raw) != before.st_size or len(raw) > MAX_FILE_BYTES
            or identity(before) != identity(opened) or identity(before) != identity(after)
            or identity(before) != identity(path.stat(follow_symlinks=False))):
        raise ValueError('evidence changed during read: ' + str(path))
    return {'raw': raw, 'mode': stat.S_IMODE(before.st_mode)}


def select_files(root):
    physical(root)
    if not root.is_dir():
        raise ValueError('evidence root is not a directory')
    files, excluded = {}, []
    folders = [root]
    for folder in folders:
        for path in sorted(folder.iterdir()):
            relative = path.relative_to(root).as_posix()
            if path.is_symlink():
                raise ValueError('symlink at evidence selection boundary: ' + str(path))
            if path.is_dir():
                if folder == root and path.name in STAGES:
                    folders.append(path)
                else:
                    excluded.append({'path': relative, 'kind': 'directory',
                                     'reason': 'not traversed: synthetic cases/cache/other directories stay external'})
            elif path.suffix in SUFFIXES:
                files[relative] = read_file(path)
            else:
                excluded.append({'path': relative, 'kind': 'unselected entry',
                                 'reason': 'only JSON/log/XML result files are selected'})
    if not files:
        raise ValueError('no selected result evidence files')
    return files, excluded


def result_observations(files):
    """Report original status and XML shape, never promote an unmarked case to pass."""
    outcomes, junit = {}, {}
    for name, item in files.items():
        basename = Path(name).name
        if basename in {'outcome.json', 'summary.json'} or basename.endswith('-summary.json'):
            try:
                value = json.loads(item['raw'])
                if not isinstance(value, dict):
                    raise ValueError('result summary is not an object')
                code, status = value.get('returncode'), value.get('status')
                if code is not None and type(code) is not int:
                    classification = 'unrecognized_exit_code'
                elif code not in (None, 0):
                    classification = 'nonzero_exit'
                elif status in {'failed', 'refused', 'interrupted', 'cancelled', 'incomplete', 'started'}:
                    classification = 'reported_' + status
                elif code == 0 or status == 'passed':
                    classification = 'reported_success_not_independently_accepted'
                else:
                    classification = 'no_recognized_terminal_result'
                outcomes[name] = {'classification': classification, 'reported_returncode': code,
                                  'reported_status': status, 'reported_source_unchanged': value.get('source_unchanged'),
                                  'original_summary_preserved_verbatim': True,
                                  'pass_totals_not_recomputed_or_endorsed': True}
            except (ValueError, TypeError, UnicodeError) as error:
                outcomes[name] = {'classification': 'unreadable_summary', 'error_type': type(error).__name__,
                                  'original_summary_preserved_verbatim': True}
        if Path(name).suffix == '.xml':
            try:
                root = ET.fromstring(item['raw'])
                cases = list(root.iter('testcase'))
                identified = [case for case in cases if case.get('name') and case.get('classname')]
                junit[name] = {'testcase_entries': len(cases), 'identified_entries': len(identified),
                               'unnamed_or_unclassified_entries': len(cases) - len(identified),
                               'failure_elements': len(list(root.iter('failure'))),
                               'error_elements': len(list(root.iter('error'))),
                               'skipped_elements': len(list(root.iter('skipped'))),
                               'unmarked_identified_entries': sum(not any(case.find(t) is not None for t in
                                    ('failure', 'error', 'skipped')) for case in identified),
                               'pass_inference': 'not_performed: exit/completeness/status may invalidate unmarked entries'}
            except (ValueError, ET.ParseError) as error:
                junit[name] = {'parse_error': type(error).__name__, 'pass_inference': 'not_performed'}
    return {'outcomes': outcomes, 'junit_shape_only': junit, 'aggregate_pass_claim': 'not_made'}


def write_archive(path, files):
    with path.open('xb') as stream, gzip.GzipFile(fileobj=stream, mode='wb', filename='', mtime=0) as compressed:
        with tarfile.open(fileobj=compressed, mode='w|') as archive:
            for name, item in sorted(files.items()):
                info = tarfile.TarInfo('results/' + name)
                info.size, info.mode, info.mtime = len(item['raw']), item['mode'], 0
                archive.addfile(info, io.BytesIO(item['raw']))
    restored = {}
    with tarfile.open(path, 'r:gz') as archive:
        for item in archive:
            if not item.isfile() or not item.name.startswith('results/'):
                raise ValueError('unexpected archive entry')
            name = item.name[len('results/'):]
            if name in restored:
                raise ValueError('duplicate archive entry')
            restored[name] = {'raw': archive.extractfile(item).read(), 'mode': item.mode}
    if restored != files:
        raise ValueError('archive byte/mode roundtrip differs')


def archive_results(evidence, output):
    roots = [physical(Path(root)) for root in evidence]
    if not roots or len(roots) != len(set(roots)):
        raise ValueError('explicit distinct completed evidence directories required')
    output = Path(output)
    if (not output.is_absolute() or output.resolve() != output or output.exists() or output.is_symlink()
            or any(output.is_relative_to(root) or root.is_relative_to(output) for root in roots)):
        raise ValueError('fresh physical output outside all evidence roots required')
    # Validate every selected source before creating output; never follow excluded trees.
    snapshots = [(root, *select_files(root)) for root in roots]
    output.mkdir(parents=True, exist_ok=False)
    runs = []
    for number, (root, files, excluded) in enumerate(snapshots, 1):
        archive = output / ('run-' + str(number).zfill(2) + '.tar.gz')
        write_archive(archive, files)
        if select_files(root) != (files, excluded):
            raise ValueError('selected original evidence changed during preservation')
        runs.append({'original_root': str(root), 'archive': {'file': archive.name,
                     'bytes': archive.stat().st_size, 'sha256': sha(archive.read_bytes())},
                     'entries': [{'path': name, 'bytes': len(item['raw']), 'sha256': sha(item['raw']),
                                  'mode': item['mode']} for name, item in sorted(files.items())],
                     'excluded': excluded, 'observations': result_observations(files),
                     'archive_bytes_and_modes_verified': True, 'selected_original_bytes_and_modes_unchanged': True})
    # Re-read all selected roots once more, including earlier runs in a multi-run archive.
    for root, files, excluded in snapshots:
        if select_files(root) != (files, excluded):
            raise ValueError('selected original evidence changed before final manifest')
    helper = Path(__file__).resolve()
    manifest = {'scope': 'selected_result_files_only_not_complete_synthetic_case_archive',
                'inputs_declared_completed_by_caller': True,
                'selection': 'top-level and neutral/omission stage JSON/log/XML files; ignored files included',
                'excluded_case_and_cache_directories': 'retained externally; contents not read or attested',
                'metadata': 'file bytes/modes preserved; archive timestamps normalized; directory metadata omitted',
                'aggregate_pass_claim': 'not_made',
                'helper': {'path': str(helper), 'sha256': sha(read_file(helper)['raw'])}, 'runs': runs}
    with (output / 'manifest.json').open('x') as stream:
        json.dump(manifest, stream, indent=2, sort_keys=True)
        stream.write('\n')
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--evidence', type=Path, action='append', required=True,
                        help='Explicit completed result directory; repeat for separate runs')
    parser.add_argument('--output', type=Path, required=True, help='Fresh archive/manifest directory')
    args = parser.parse_args()
    archive_results(args.evidence, args.output)
    print(args.output / 'manifest.json')


if __name__ == '__main__':
    main()
