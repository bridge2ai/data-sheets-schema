#!/usr/bin/env python3
# Purpose: retain D41 offline validation evidence for #5138/#5142, 2026-10-26.
# Inputs: explicit completed pytest log/XML pairs and an exact parity directory.
# Outputs: exclusive repository evidence directory, unchanged byte copies and pins.
"""Archive observations; never rerun, repair, normalize or approve a generation."""
import argparse
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET


def pin(path):
    return content_pin(path.read_bytes())


def content_pin(raw):
    return {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', action='append', required=True,
                        help='Unique NAME=absolute stem for completed .log/.xml files')
    parser.add_argument('--parity', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    runs = {}
    for value in args.run:
        name, stem = value.split('=', 1)
        if not name or Path(name).name != name or name in runs or not Path(stem).is_absolute():
            raise ValueError('run requires a unique simple name and absolute stem')
        paths = [Path(stem + suffix) for suffix in ('.log', '.xml')]
        for path in paths:
            if not path.is_file() or path.is_symlink():
                raise ValueError(f'missing or nonregular evidence: {path}')
        raws = {p: p.read_bytes() for p in paths}
        document = ET.fromstring(raws[paths[1]])
        runs[name] = {'inputs': {str(p): content_pin(raws[p]) for p in paths},
                      'suites': [dict(s.attrib) for s in document.iter('testsuite')]}
    parity = args.parity.resolve(strict=True)
    summary_raw = (parity / 'summary.json').read_bytes()
    summary = json.loads(summary_raw)
    if summary.get('passed') is not True or not summary.get('rows'):
        raise ValueError('parity summary does not report a completed comparison')
    if not all(row.get('identical') is True for row in summary['rows'].values()):
        raise ValueError('parity summary contains a nonidentical row')
    expected_parity = {parity / 'summary.json': content_pin(summary_raw)}
    for mode in ('baseline', 'candidate'):
        directory = parity / mode
        if not directory.is_dir() or directory.is_symlink():
            raise ValueError(f'missing or nonphysical capture directory: {directory}')
        for record in [summary['captures'][mode],
                       *(row[mode] for row in summary['rows'].values())]:
            source = Path(record['path'])
            if (not source.is_absolute() or source.resolve(strict=True) != source
                    or source.parent != directory or not source.is_file()):
                raise ValueError('capture pin is outside its physical directory')
            expected = {key: record[key] for key in ('bytes', 'sha256')}
            if pin(source) != expected:
                raise ValueError(f'capture differs from summary: {source}')
            expected_parity[source] = expected
        if directory / 'capture.json' not in expected_parity:
            raise ValueError('summary lacks its required capture.json pin')
    args.out.mkdir(parents=True, exist_ok=False)
    retained = {}

    def copy(source, relative, expected=None):
        before = pin(source)
        if expected is not None and before != expected:
            raise ValueError(f'input changed since metadata was parsed: {source}')
        destination = args.out / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        with destination.open('xb') as target:
            target.write(source.read_bytes())
        if pin(source) != before or pin(destination) != before:
            raise ValueError(f'evidence changed during copy: {source}')
        retained[str(relative)] = {'source': str(source), **before}

    for name, run in runs.items():
        for source in run['inputs']:
            path = Path(source)
            copy(path, Path('tests') / (name + path.suffix), run['inputs'][source])
    copy(parity / 'summary.json', Path('parity/summary.json'), expected_parity[parity / 'summary.json'])
    for mode in ('baseline', 'candidate'):
        for source in sorted((parity / mode).rglob('*')):
            if source.is_symlink():
                raise ValueError('symlink in parity capture')
            if source.is_file():
                copy(source, Path('parity') / source.relative_to(parity), expected_parity.get(source))
        copy(parity / (mode + '.log'), Path('parity') / (mode + '.log'))
    result = {'scope': 'Retained offline software evidence; no scientific or launch acceptance',
              'helper': {'path': str(Path(__file__).resolve()), **pin(Path(__file__))},
              'runs': runs, 'parity_scope': summary['scope'], 'retained': retained}
    with (args.out / 'manifest.json').open('x') as stream:
        json.dump(result, stream, sort_keys=True, indent=2)
        stream.write('\n')
    print(str(args.out / 'manifest.json'))


if __name__ == '__main__':
    main()
