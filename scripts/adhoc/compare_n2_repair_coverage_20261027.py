#!/usr/bin/env python3
# Purpose: compare exact completed N2 JUnit identities before/after fixture-only repairs.
# Inputs: two retained run directories and their local Git repository; output: fresh JSON.
# Refs #4354, N2 restack verification; 2026-10-27. Read-only inputs, no test execution.
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import subprocess
import xml.etree.ElementTree as ET

BASE = '9ea9b70a3b333554bc132f00af7ef22a8cea6094'
REPAIR = '9e1ac52272ded77eb73f1656ff1b88e6d073439e'
MODULES = (
    'tests/test_native_shared_response_identity.py',
    'tests/test_native_shared_stream_bindings.py',
    'tests/test_native_trace_single_decode.py',
)
TARGET = 'a0e28d8821c69e2d4fe1b75b14e3c2a2140ae4d5'
PROTECTED = ('src/data_sheets_schema/shared_generation.py', 'src/download/prompts/canonical_hashes.yaml')
INPUTS = ('pytest.xml', 'outcome.json', 'plan.json', 'source-before.json', 'source-after.json',
          'origins-before.json', 'origins-after.json', 'dependency-bootstrap.json', 'pytest-command.json')


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def read_run(root, expected, code):
    raw = {}
    for name in INPUTS:
        path = root / name
        if path.is_symlink() or not path.is_file():
            raise ValueError('nonregular/missing evidence: ' + str(path))
        raw[name] = path.read_bytes()
    documents = {name: json.loads(value) for name, value in raw.items() if name.endswith('.json')}
    before, after = documents['source-before.json'], documents['source-after.json']
    outcome, plan = documents['outcome.json'], documents['plan.json']
    if before != after or before['head'] != expected or not before['tracked_exact']:
        raise ValueError('frozen source proof differs')
    if plan['head'] != expected or outcome['returncode'] != code or not outcome['source_unchanged']:
        raise ValueError('run completion/source status differs')
    if documents['dependency-bootstrap.json']['site_startup'] != 'disabled' or documents['dependency-bootstrap.json']['pth_execution'] != 'disabled':
        raise ValueError('closed import bootstrap absent')
    checkout = Path(documents['pytest-command.json']['cwd'])
    for label in ('origins-before.json', 'origins-after.json'):
        origins = documents[label]
        if not origins:
            raise ValueError('empty import origin proof')
        for name, paths in origins.items():
            if not (name == 'data_sheets_schema' or name.startswith('data_sheets_schema.')) or not paths:
                raise ValueError('unexpected/empty project origin')
            if any(not Path(path).is_relative_to(checkout / 'src') for path in paths):
                raise ValueError('foreign project import path')
    cases = {}
    for case in ET.fromstring(raw['pytest.xml']).iter('testcase'):
        identity = (case.get('classname'), case.get('name'))
        if not all(identity) or identity in cases:
            raise ValueError('anonymous/duplicate case identity')
        states = [tag for tag in ('failure', 'error', 'skipped') if case.find(tag) is not None]
        if len(states) > 1:
            raise ValueError('ambiguous JUnit case state')
        cases[identity] = states[0] if states else 'passed'
    count = Counter(cases.values())
    recorded = outcome['junit']
    if any(recorded[key] != count.get(tag, 0) for key, tag in
           (('passed', 'passed'), ('failures', 'failure'), ('errors', 'error'), ('skipped', 'skipped'))):
        raise ValueError('XML and outcome counts differ')
    if recorded['cases'] != len(cases) or recorded['cases_without_identity'] != 0:
        raise ValueError('XML and outcome identities differ')
    return cases, documents, raw


def module_for(identity):
    # These three test modules use module-level tests; classes elsewhere are retained verbatim.
    for path in MODULES:
        name = path.removesuffix('.py').replace('/', '.')
        if identity[0] == name or identity[0].startswith(name + '.'):
            return path
    return None


def rows(cases):
    return [{'classname': key[0], 'name': key[1], 'status': value}
            for key, value in sorted(cases.items())]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repository', type=Path, required=True)
    parser.add_argument('--original', type=Path, required=True)
    parser.add_argument('--repair', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    repo, original_root, repair_root = (p.resolve(strict=True) for p in (args.repository, args.original, args.repair))
    if args.output.exists() or args.output.is_symlink():
        raise ValueError('fresh output required')
    env = {key: value for key, value in os.environ.items() if not key.startswith('GIT_')}
    env.update(GIT_NO_LAZY_FETCH='1', GIT_OPTIONAL_LOCKS='0')
    def git(*words):
        return subprocess.check_output(['git', '--no-replace-objects', *words], cwd=repo, env=env)
    def search_checkout():
        state = {'head': git('rev-parse', 'HEAD').decode().strip(),
                 'tracked_status': git('status', '--porcelain', '--untracked-files=no').decode()}
        if state['head'] != REPAIR or state['tracked_status']:
            raise ValueError('reference search requires the exact repair HEAD and clean tracked bytes')
        return state
    original, odoc, oraw = read_run(original_root, BASE, 1)
    repaired, rdoc, rraw = read_run(repair_root, REPAIR, 0)
    if odoc['plan.json']['groups']['native'] != rdoc['plan.json']['groups']['native']:
        raise ValueError('native module roster changed')
    if rdoc['plan.json']['groups']['repair'] != list(MODULES):
        raise ValueError('repair module roster differs')
    if any(value != 'passed' for value in repaired.values()) or any(module_for(key) is None for key in repaired):
        raise ValueError('repair has a nonpass or unexpected module')
    originals_replaced = {key: val for key, val in original.items() if module_for(key)}
    unaffected = {key: val for key, val in original.items() if not module_for(key)}
    missing = set(originals_replaced) - set(repaired)
    added = set(repaired) - set(original)
    if missing or any(value != 'passed' for value in unaffected.values()):
        raise ValueError('uncovered old case or nonpass outside repaired modules')
    if any(not key[1].startswith('test_later_cache_state_is_checked_without_hiding_other_fields[') for key in added):
        raise ValueError('unexpected newly collected repair test')
    if set(unaffected) & set(repaired):
        raise ValueError('composed case sets overlap')
    changed = git('diff', '--name-only', BASE, REPAIR).decode().splitlines()
    production_changed = git('diff', '--name-only', BASE, REPAIR, '--', 'src', 'utils', 'tests/conftest.py', 'pyproject.toml', 'pytest.ini', 'setup.cfg').decode().splitlines()
    if production_changed:
        raise ValueError('production, shared test helper or pytest configuration changed: ' + repr(production_changed))
    native_roster = odoc['plan.json']['groups']['native']
    unchanged_modules = [path for path in native_roster if path not in MODULES]
    if any(git('show', BASE + ':' + path) != git('show', REPAIR + ':' + path) for path in unchanged_modules):
        raise ValueError('unrepaired native test module changed')
    for path in PROTECTED:
        if git('show', BASE + ':' + path) != git('show', TARGET + ':' + path) or git('show', REPAIR + ':' + path) != git('show', TARGET + ':' + path):
            raise ValueError('protected bytes changed')
    needles = [Path(path).stem for path in MODULES] + ['native_shared_observations_0125eebbc', 'SettledResponse', 'trace_state', 'CACHE_METHODS']
    command = ['rg', '--no-ignore', '--hidden', '--files-with-matches', '--null', '--fixed-strings']
    for needle in needles:
        command += ['-e', needle]
    command += ['--glob', '!.git', '--glob', '!**/__pycache__/**', '--glob', '!**/*.xml', '--glob', '!**/*.log', '.']
    search_before = search_checkout()
    result = subprocess.run(command, cwd=repo, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    search_after = search_checkout()
    if search_after != search_before:
        raise ValueError('reference search checkout changed')
    if result.returncode not in (0, 1):
        raise ValueError('reference search failed')
    references = sorted(path.decode().removeprefix('./') for path in result.stdout.split(b'\0') if path)
    runtime_refs = [path for path in references if path.startswith(('src/', 'tests/', 'utils/')) and path not in MODULES]
    if runtime_refs:
        raise ValueError('additional runtime/test references require review: ' + repr(runtime_refs))
    package_equal = odoc['plan.json']['packages'] == rdoc['plan.json']['packages']
    if not package_equal or odoc['plan.json']['python'] != rdoc['plan.json']['python']:
        raise ValueError('recorded interpreter/package roster differs')
    report = {
        'scope': 'Composed functional case coverage across two frozen runs; NOT one fresh full-suite pass, interaction replay, timing or scientific acceptance.',
        'helper': {'path': str(Path(__file__).resolve()), 'sha256': sha(Path(__file__).read_bytes())},
        'heads': {'original': BASE, 'repair': REPAIR, 'protected_target': TARGET},
        'original_counts': dict(Counter(original.values())),
        'old_repaired_module_counts': dict(Counter(originals_replaced.values())),
        'unchanged_cases': len(unaffected), 'unchanged_native_test_modules': len(unchanged_modules),
        'repair_cases': len(repaired), 'new_case_count': len(added),
        'composed_unique_passing_cases': len(unaffected) + len(repaired),
        'all_old_identities_covered': set(original) <= set(unaffected) | set(repaired),
        'all_original_nonpasses_reran_and_passed': all(key in repaired for key, val in original.items() if val != 'passed'),
        'source_proof': {'frozen_before_after_both_runs': True, 'production_utils_shared_conftest_config_unchanged': True,
                         'all_unrepaired_native_test_modules_byte_identical': True, 'protected_equal_target': True,
                         'same_recorded_python_and_package_roster': True, 'third_party_package_bytes_attested': False},
        'changed_paths': changed,
        'reference_search': {'command': command, 'cwd': str(repo), 'ignored_files_included': True,
                             'checkout_before': search_before, 'checkout_after': search_after,
                             'exact_repair_head_and_clean_tracked_bytes_unchanged': True,
                             'excluded': ['Git internals', 'bytecode caches', 'log/XML evidence'],
                             'matching_files': references, 'additional_runtime_or_test_references': runtime_refs,
                             'limit': 'Literal module/API reference search, not proof against computed dynamic imports or arbitrary runtime coupling.'},
        'per_repaired_module': {path: {'original': dict(Counter(val for key, val in originals_replaced.items() if module_for(key) == path)),
                                     'repair': dict(Counter(val for key, val in repaired.items() if module_for(key) == path))} for path in MODULES},
        'new_cases': rows({key: repaired[key] for key in added}),
        'replaced_original_cases': rows(originals_replaced),
        'composed_cases': rows({**unaffected, **repaired}),
        'input_pins': {label: [{'path': str(root / name), 'bytes': len(raw), 'sha256': sha(raw)} for name, raw in values.items()]
                       for label, root, values in (('original', original_root, oraw), ('repair', repair_root, rraw))},
    }
    # Confirm that even read-only comparison did not race a writer to retained input files.
    for root, values in ((original_root, oraw), (repair_root, rraw)):
        if any((root / name).read_bytes() != raw for name, raw in values.items()):
            raise ValueError('retained evidence changed during comparison')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('x') as stream:
        json.dump(report, stream, indent=2, sort_keys=True)
        stream.write('\n')
    print(json.dumps({key: report[key] for key in ('unchanged_cases', 'repair_cases', 'new_case_count', 'composed_unique_passing_cases', 'all_old_identities_covered')}))


if __name__ == '__main__':
    main()
