"""Compare BC1 test evidence for #5489/#5490, 2026-11-05.

Inputs: measurement directory and baseline Git commit. Outputs: JSON equivalence
and timing evidence plus the exact test diff. Reads local Git only.
"""
import argparse
import ast
import json
from pathlib import Path
import subprocess
import xml.etree.ElementTree as ET


def assertions(source):
    return [ast.dump(node, include_attributes=False) for node in ast.walk(ast.parse(source))
            if isinstance(node, ast.Assert)]


def outcomes(path):
    root = ET.parse(path).getroot()
    return {(case.attrib['classname'], case.attrib['name']):
            next((tag for tag in ('failure', 'error', 'skipped') if case.find(tag) is not None), 'passed')
            for case in root.iter('testcase')}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('directory', type=Path)
    parser.add_argument('--baseline', default='6d6031792e914088823a5204f09fac6c6c1106f6')
    args = parser.parse_args()
    result = {}
    paths = ['tests/test_bc1_registration.py', 'tests/test_bc1_g2_journal.py']
    for path, label in zip(paths, ('registration', 'journal')):
        original = subprocess.check_output(['git', 'show', f'{args.baseline}:{path}'], text=True)
        before = args.directory / f'before-{label}'
        after = args.directory / f'after-{label}'
        old_env = json.loads(before.with_suffix('.environment.json').read_text())
        new_env = json.loads(after.with_suffix('.environment.json').read_text())
        old_outcomes, new_outcomes = outcomes(before.with_suffix('.xml')), outcomes(after.with_suffix('.xml'))
        checks = {
            'assertions_unchanged': assertions(original) == assertions(Path(path).read_text()),
            'node_ids_identical': before.with_suffix('.nodes.json').read_bytes() == after.with_suffix('.nodes.json').read_bytes(),
            'outcomes_identical': old_outcomes == new_outcomes,
            'environment_identical': all(old_env[key] == new_env[key] for key in ('python', 'executable', 'packages', 'profile')),
            'sampling_identical': old_env.get('sample', False) == new_env.get('sample', False),
        }
        result[label] = {**checks, 'count': len(old_outcomes), 'assertion_count': len(assertions(original)),
                         'before_seconds': old_env['seconds'],
                         'after_seconds': new_env['seconds'],
                         'speedup': old_env['seconds'] / new_env['seconds'],
                         'ci_seconds_at_2_7x': new_env['seconds'] * 2.7,
                         'outcomes': {value: list(new_outcomes.values()).count(value) for value in set(new_outcomes.values())}}
        if old_env.get('sample'):
            result[label]['sample_profiles'] = {}
            for mode, prefix in (('before', before), ('after', after)):
                sample = json.loads(Path(f'{prefix}.0.sample.json').read_text())
                result[label]['sample_profiles'][mode] = {
                    'seconds': sample['seconds'], 'samples': sample['samples'],
                    'functions': [row for row in sample['inclusive_stack_samples']
                                  if 'src/data_sheets_schema/' in row['file'] and row['function'] in
                                  ('_rebuild', '_derive', '_schema', '_core_catalog', '_schema_yaml', 'prepare')]}
        assert all(checks.values()), result[label]
    (args.directory / 'equivalence.json').write_text(json.dumps(result, indent=2))
    (args.directory / 'assertion-diff.patch').write_bytes(subprocess.check_output(['git', 'diff', args.baseline, '--', *paths]))
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
