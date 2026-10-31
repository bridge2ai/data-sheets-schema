#!/usr/bin/env python3
"""Archive frozen offline R9b checks and reconcile unique cases (Refs #5157).

Inputs: three preserved /private/tmp validation directories and stdout logs.
Output: exclusive notes/r9b_validation_2026-10-27 plus a byte manifest.
Date: 2026-10-27. No test execution, fixture mutation, network or provider access.
"""
from pathlib import Path
import hashlib
import json
import shutil
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
BATCHES = (
    ('initial_causal', '1a63bcae2f6140559edca973cf80cf6db2d959ea',
     Path('/private/tmp/d4d-r9b-wave2-1a63bcae2/causal'),
     Path('/private/tmp/d4d-r9b-wave2-1a63bcae2-causal.log')),
    ('corrected_corruption', '346919f1f9d648700bcf0b3ccfe578ceb1abe23a',
     Path('/private/tmp/d4d-r9b-wave2-346919f1f/corruption'),
     Path('/private/tmp/d4d-r9b-wave2-346919f1f-corruption.log')),
    ('regression', 'c16b88c7be9ae411f622dfffe5c3e266a1c15388',
     Path('/private/tmp/d4d-r9b-wave2-c16b88c7b/regression'),
     Path('/private/tmp/d4d-r9b-wave2-c16b88c7b-regression.log')),
)
FILES = ('outcome.json', 'source-before.json', 'source-after.json', 'origins-before.json',
         'origins-after.json', 'environment.json', 'command.json', 'pytest.xml')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def cases(path):
    result = {}
    for node in ET.parse(path).iter('testcase'):
        key = node.attrib['classname'] + '::' + node.attrib['name']
        if key in result:
            raise ValueError('Duplicate JUnit case identity: ' + key)
        result[key] = next((tag for tag in ('failure', 'error', 'skipped') if node.find(tag) is not None), 'passed')
    return result


def main():
    prepared = []
    for name, head, directory, log in BATCHES:
        outcome = json.loads((directory / 'outcome.json').read_bytes())
        if outcome['source_unchanged'] is not True:
            raise ValueError('Source preservation failed: ' + name)
        rows = cases(directory / 'pytest.xml')
        prepared.append((name, head, directory, log, outcome, rows))
    initial, corrected, regression = [row[5] for row in prepared]
    failed = {name for name, result in initial.items() if result != 'passed'}
    if (len(initial) != 7 or len(failed) != 1 or set(corrected) != failed
            or set(corrected.values()) != {'passed'} or len(regression) != 230
            or set(regression.values()) != {'passed'} or set(initial) & set(regression)):
        raise ValueError('Unexpected causal correction or regression case partition')
    destination = ROOT / 'notes/r9b_validation_2026-10-27'
    destination.mkdir(exist_ok=False)
    sources, batches = {}, []
    for name, head, directory, log, outcome, rows in prepared:
        target = destination / name
        target.mkdir()
        for source in [*(directory / filename for filename in FILES), log]:
            saved = target / ('stdout.log' if source == log else source.name)
            shutil.copyfile(source, saved)
            sources[str(saved.relative_to(destination))] = {'source': str(source), 'sha256': sha(source),
                'bytes': source.stat().st_size}
            if sha(saved) != sha(source):
                raise ValueError('Copied evidence differs')
        batches.append({'name': name, 'head': head, 'outcome': outcome, 'cases': rows})
    summary = {'format': 'r9b_validation_archive_v1', 'batches': batches,
        'passing_unique_cases': sorted(set(initial) | set(regression)), 'passing_unique_count': 237,
        'causal_unique_count': 7, 'regression_unique_count': 230,
        'initial_failed_case_retained': sorted(failed), 'sources': sources,
        'scope': 'Focused offline verification across recorded heads, not full-suite or scientific acceptance.',
        'helper_sha256': sha(Path(__file__))}
    (destination / 'coverage.json').write_text(json.dumps(summary, indent=2, sort_keys=True) + '\n')
    paths = sorted(path for path in destination.rglob('*') if path.is_file())
    (destination / 'SHA256SUMS').write_text(''.join(f'{sha(path)}  {path.relative_to(destination)}\n' for path in paths))
    print(json.dumps({'archive': str(destination), 'passing_unique_count': 237, 'raw_files': len(sources)}))


if __name__ == '__main__':
    main()
