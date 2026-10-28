#!/usr/bin/env python3
"""#5212 R1-R9, 2026-10-28: preserve serial offline acceptance evidence.

Inputs: external evidence directory from pr5212_r3_checks_20261028.py.
Outputs: repository archive/manifest, per-module test counts and verified hashes.
Does not alter source evidence, run directories, pins or decision records.
"""
import argparse
import hashlib
import json
from pathlib import Path
import tarfile
import xml.etree.ElementTree as ET


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('destination', type=Path)
    args = parser.parse_args()
    args.destination.mkdir(parents=True, exist_ok=False)
    files = [p for p in sorted(args.source.rglob('*')) if p.is_file() and not p.is_symlink()]
    inventory = {str(p.relative_to(args.source)): {'sha256': sha(p.read_bytes()), 'bytes': p.stat().st_size}
                 for p in files}
    archive = args.destination / 'evidence.tar.gz'
    with tarfile.open(archive, 'w:gz') as stream:
        for path in files:
            stream.add(path, arcname=str(path.relative_to(args.source)), recursive=False)
    with tarfile.open(archive, 'r:gz') as stream:
        restored = {member.name: {'sha256': sha(stream.extractfile(member).read()), 'bytes': member.size}
                    for member in stream if member.isfile()}
    assert restored == inventory and archive.stat().st_size > 0
    root = Path(__file__).resolve().parents[2]
    production = {str(p.relative_to(root)): sha(p.read_bytes())
                  for p in sorted((root / 'src/data_sheets_schema').rglob('*.py'))}
    groups = {}
    for outcome in sorted(args.source.glob('*/outcome.json')):
        value = json.loads(outcome.read_text())
        pinned = json.loads(outcome.with_name('source-pins.json').read_text())
        pinned_production = {name: digest for name, digest in pinned.items()
                             if name.startswith('src/data_sheets_schema/')}
        assert pinned_production == production, f'production source differs from {outcome}'
        value['matches_final_production'] = True
        xml = outcome.with_name('results.xml')
        counts = {}
        if xml.is_file():
            for case in ET.parse(xml).getroot().iter('testcase'):
                row = counts.setdefault(case.get('classname'), {'passed': 0, 'failed': 0, 'skipped': 0})
                kind = ('failed' if case.find('failure') is not None or case.find('error') is not None
                        else 'skipped' if case.find('skipped') is not None else 'passed')
                row[kind] += 1
        groups[value['group']] = {**value, 'modules': counts}
    manifest = {'purpose': '#5212 R1-R9 offline acceptance; no full-suite or CI claim',
                'archive': {'path': archive.name, 'sha256': sha(archive.read_bytes()), 'bytes': archive.stat().st_size},
                'archive_round_trip_verified': True, 'groups': groups, 'files': inventory,
                'production_sources_sha256': sha(json.dumps(production, sort_keys=True).encode())}
    (args.destination / 'manifest.json').write_text(json.dumps(manifest, indent=2, sort_keys=True) + '\n')
    assert json.loads((args.destination / 'manifest.json').read_text()) == manifest
    print(json.dumps({'archive': manifest['archive'], 'groups': groups}, indent=2))


if __name__ == '__main__':
    main()
