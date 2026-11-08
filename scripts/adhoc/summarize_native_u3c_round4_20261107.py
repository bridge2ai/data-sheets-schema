#!/usr/bin/env python3
"""U3-C4 saved-run summary, 2026-11-07: scratch runs -> new JSON manifest.

Retain B cpu-smoke*.json before cases cleanup. Never overwrite or delete;
never run tests, production code, Git, native executables or network calls.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET

SCRATCH = Path(__file__).resolve().parents[3] / 'scratch-native-u3c-r4'


def pin(path):
    if path.is_symlink() or not path.is_file():
        raise ValueError('not regular evidence: ' + str(path))
    raw = path.read_bytes()
    return {'path': str(path), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def save(path, raw):
    if not path.parent.resolve().is_relative_to(SCRATCH.resolve()):
        raise ValueError('output must stay inside C4 scratch')
    with path.open('xb') as stream:
        stream.write(raw)
    assert path.read_bytes() == raw


def encoded(value):
    return (json.dumps(value, sort_keys=True, indent=2) + '\n').encode()


def retain(run):
    cases, retained = run / 'cases', run / 'retained-smoke'
    manifest = retained / 'manifest.json'
    if manifest.exists():
        rows = json.loads(manifest.read_bytes())
        for row in rows:
            path = retained / row['relative']
            if not path.resolve().is_relative_to(retained.resolve()) or pin(path) != row['artifact']:
                raise ValueError('retained smoke evidence differs')
        return {'manifest': pin(manifest), 'files': rows}
    rows = []
    for source in sorted(cases.rglob('cpu-smoke*.json')) if cases.exists() else ():
        if source.is_symlink() or not source.resolve().is_relative_to(cases.resolve()):
            raise ValueError('smoke evidence leaves cases')
        relative = source.relative_to(cases)
        target = retained / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        raw = source.read_bytes()
        json.loads(raw)
        save(target, raw)
        rows.append({'relative': str(relative), 'source': pin(source), 'artifact': pin(target)})
    if rows:
        save(manifest, encoded(rows))
    return {'manifest': pin(manifest) if rows else None, 'files': rows, 'cases_present': cases.exists()}


def summarize(run):
    outcome = json.loads((run / 'outcome.json').read_bytes())
    counts, failures = Counter(), []
    xml = run / 'pytest.xml'
    if xml.exists():
        for case in ET.fromstring(xml.read_bytes()).iter('testcase'):
            tags = [node.tag for node in case if node.tag in ('error', 'failure', 'skipped')]
            counts.update(tags or ['passed'])
            if tags:
                failures.append({'classname': case.get('classname'), 'name': case.get('name'),
                                 'statuses': tags, 'details': [node.text for node in case if node.tag in tags]})
    files = [p for p in run.iterdir() if p.is_file() and p.suffix in ('.json', '.xml', '.log')]
    census = run / 'graph-census/census.json'
    if census.exists(): files.append(census)
    return {'run': run.name, 'outcome': outcome, 'xml_present': xml.exists(),
            'counts': dict(counts), 'nonpassing_testcases': failures,
            'artifacts': [pin(p) for p in sorted(files)], 'retained_smoke': retain(run)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    runs = [summarize(p) for p in sorted(SCRATCH.iterdir())
            if p.is_dir() and not p.is_symlink() and (p / 'outcome.json').is_file()]
    value = {'runs': runs, 'scope': 'Immediate completed run directories only; no cross-run count sum; '
             'exit zero alone is not a pass; absent retained smoke after cases removal proves nothing.'}
    save(args.out, encoded(value))
    print(json.dumps(pin(args.out), sort_keys=True))


if __name__ == '__main__':
    main()
