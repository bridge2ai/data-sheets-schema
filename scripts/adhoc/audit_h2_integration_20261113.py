#!/usr/bin/env python3
"""Read-only integration boundary and pin census, issues 6193-6202, 2026-11-13.
Inputs: this checkout and assigned candidate base. Output: exact source hashes,
protected-file comparisons, controller-manifest matches and syntax findings.
No pins are applied, no package modules are imported, no remote access.
"""
import argparse
import ast
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
BASE = '309b58bd34a58ba9871ba4d19e12f90bdefbf664'
PROTECTED = ('src/data_sheets_schema/shared_generation.py', 'src/data_sheets_schema/api_runner.py',
    'src/download/prompts/canonical_hashes.yaml', 'tests/utils/run_spec_boundary_contracts.json',
    'src/data_sheets_schema/native_subscription_guard.py')


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT)


def main(out):
    protected = []
    for name in PROTECTED:
        before, after = git('show', BASE + ':' + name), (ROOT / name).read_bytes()
        assert before == after, name
        protected.append({'path': name, 'sha256': sha(after), 'unchanged': True})
    manifests = []
    for version in (1, 2):
        path = ROOT / f'src/data_sheets_schema/native_controller_sources_v{version}.json'
        value = json.loads(path.read_bytes())
        modules = []
        for name, item in value['modules'].items():
            actual = sha((ROOT / item['path']).read_bytes())
            modules.append({'name': name, **item, 'actual_sha256': actual, 'matches': actual == item['sha256']})
        manifests.append({'path': str(path.relative_to(ROOT)), 'sha256': sha(path.read_bytes()), 'modules': modules})
    changed = git('diff', '--name-only', BASE, 'HEAD').decode().splitlines()
    syntax = []
    for name in changed:
        path = ROOT / name
        if path.suffix == '.py':
            ast.parse(path.read_bytes(), filename=name)
            syntax.append(name)
    record = {'base': BASE, 'head': git('rev-parse', 'HEAD').decode().strip(),
        'protected': protected, 'manifests': manifests,
        'pin_proposal_required': any(not entry['matches'] for m in manifests for entry in m['modules']),
        'syntax_checked': syntax, 'changed': changed}
    with out.open('x') as stream:
        json.dump(record, stream, indent=2); stream.write('\n')
    print(json.dumps({'output': str(out), 'sha256': sha(out.read_bytes()),
                      'pin_proposal_required': record['pin_proposal_required']}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    main(parser.parse_args().output)
