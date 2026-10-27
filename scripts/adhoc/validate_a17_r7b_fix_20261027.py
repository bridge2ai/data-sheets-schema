#!/usr/bin/env python3
# Purpose: validate A17/R7b-F1 registration admission and sizing regressions.
# Inputs: clean committed A17 repair checkout and physical project venv; outputs: fresh external evidence.
# Refs #5211; 2026-10-27. Adapted from the reviewed N2 unit2 closed-import validator.
"""Offline registration-builder validation; no providers or scientific acceptance."""
import argparse
import hashlib
import importlib
import importlib.metadata
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
TARGET = '2172bdd591f64a1a9f0fdd3220a8ff8ce826a6b4'
MODULES = ('test_build_api_registrations', 'test_registration_input_sizing')
BOUNDARY_NODES = tuple('tests/test_build_api_registrations.py::test_profile_covers_equal_or_larger_admission_ceilings_only['
                       + name + ']' for name in ('context_limit_tokens', 'max_input_tokens_per_call', 'max_request_bytes'))
PROTECTED = ('src/data_sheets_schema/shared_generation.py', 'src/data_sheets_schema/api_Generation_v2.py',
             'src/download/prompts/canonical_hashes.yaml')


def git(*args):
    env = {key: value for key, value in os.environ.items() if not key.startswith('GIT_')}
    env.update(GIT_NO_LAZY_FETCH='1', GIT_OPTIONAL_LOCKS='0')
    return subprocess.check_output(['git', '--no-replace-objects', *args], cwd=ROOT, env=env)


def save(path, value):
    with path.open('x') as stream:
        json.dump(value, stream, sort_keys=True, indent=2)
        stream.write('\n')


def source():
    """Check every tracked blob/mode; submodule commits remain explicitly opaque."""
    entries, exact = {}, True
    for row in git('ls-tree', '-rz', 'HEAD').decode().split('\0'):
        if not row:
            continue
        meta, name = row.split('\t', 1)
        mode, kind, oid = meta.split()
        if kind == 'commit':
            entries[name] = {'gitlink': oid, 'contents_attested': False}
            continue
        path = ROOT / name
        if not path.exists() and not path.is_symlink():
            entries[name] = {'missing': True}
            exact = False
            continue
        raw = os.fsencode(os.readlink(path)) if path.is_symlink() else path.read_bytes()
        actual_mode = '120000' if path.is_symlink() else ('100755' if path.stat().st_mode & 0o111 else '100644')
        blob = hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()
        exact = exact and blob == oid and actual_mode == mode
        entries[name] = {'git_blob': blob, 'mode': actual_mode,
                         'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw)}
    return {'head': git('rev-parse', 'HEAD').decode().strip(),
            'tree': git('rev-parse', 'HEAD^{tree}').decode().strip(),
            'tracked_exact': exact, 'entries': entries}


def origins(baseline):
    result = {}
    for name, module in tuple(sys.modules.items()):
        if name == 'data_sheets_schema' or name.startswith('data_sheets_schema.'):
            expected = ROOT / 'src'
        elif name == 'tests' or name.startswith('tests.'):
            expected = ROOT / 'tests'
        elif name == 'scripts' or name.startswith('scripts.'):
            expected = ROOT / 'scripts'
        else:
            continue
        paths = list(getattr(module, '__path__', ()))
        if getattr(module, '__file__', None):
            paths.append(module.__file__)
        if not paths:
            raise ValueError('module has no physical origin: ' + name)
        for path in paths:
            if not Path(path).resolve(strict=True).is_relative_to(expected):
                raise ValueError('foreign project/test module: ' + name + ' -> ' + str(path))
        if getattr(module, '__file__', None):
            path = Path(module.__file__).resolve(strict=True)
            entry = baseline['entries'].get(str(path.relative_to(ROOT)))
            if (not path.is_file() or not isinstance(entry, dict)
                    or entry.get('mode') not in {'100644', '100755'}
                    or hashlib.sha256(path.read_bytes()).hexdigest() != entry.get('sha256')):
                raise ValueError('module origin is not an exact tracked source blob: ' + name)
        result[name] = paths
    for name in MODULES:
        if 'tests.' + name not in result:
            raise ValueError('required test module not loaded: ' + name)
    return result


def child(output, boundaries_only=False):
    if not sys.flags.no_site or not sys.flags.safe_path or not sys.dont_write_bytecode:
        raise ValueError('child requires -S -P -B')
    venv = Path(sys.executable).parent.parent
    site = venv / 'lib' / ('python' + '.'.join(map(str, sys.version_info[:2]))) / 'site-packages'
    if not (venv / 'pyvenv.cfg').is_file() or not site.is_dir() or site.resolve() != site or str(site) in sys.path:
        raise ValueError('physical project venv dependencies required without site startup')
    before = {'prefix': sys.prefix, 'exec_prefix': sys.exec_prefix}
    sys.prefix = sys.exec_prefix = str(venv)
    sys.path.append(str(site))
    save(output / 'bootstrap.json', {'site_startup': 'disabled', 'pth_execution': 'disabled',
        'prefix_before': before, 'prefix': sys.prefix, 'exec_prefix': sys.exec_prefix,
        'base_prefix': sys.base_prefix, 'base_exec_prefix': sys.base_exec_prefix,
        'executable': sys.executable, 'python': sys.version, 'sys_path': list(sys.path),
        'packages': sorted((d.metadata.get('Name', ''), d.version) for d in importlib.metadata.distributions()),
        'dependency_bytes_attested': False})
    for name in MODULES:
        importlib.import_module('tests.' + name)
    baseline = json.loads((output / 'source-before.json').read_text())
    save(output / 'origins-before.json', origins(baseline))
    import pytest
    args = ['-q', '-p', 'no:cacheprovider', '--basetemp', str(output / 'cases'),
            '--junitxml', str(output / 'pytest.xml'),
            *(BOUNDARY_NODES if boundaries_only else ('tests/' + name + '.py' for name in MODULES))]
    save(output / 'pytest-command.json', {'args': args, 'cwd': str(ROOT)})
    try:
        return int(pytest.main(args))
    finally:
        save(output / 'origins-after.json', origins(baseline))


def run(output, expected, boundaries_only=False):
    if output.is_relative_to(ROOT):
        raise ValueError('evidence must be outside frozen source tree')
    output.mkdir(parents=True, exist_ok=False)
    before = source()
    save(output / 'source-before.json', before)
    if before['head'] != expected or not before['tracked_exact'] or git('status', '--porcelain=v1', '--untracked-files=all'):
        raise ValueError('clean committed exact source required')
    for path in PROTECTED:
        if not git('ls-tree', TARGET, '--', path):
            if (ROOT / path).exists() or (ROOT / path).is_symlink():
                raise ValueError('protected path absent at base was created: ' + path)
        elif (ROOT / path).read_bytes() != git('show', TARGET + ':' + path):
            raise ValueError('protected target file differs: ' + path)
    env = dict(os.environ)
    removed = sorted(key for key in env if key.startswith(('ANTHROPIC_', 'CBORG_', 'OPENAI_', 'GIT_', 'D4D_RECORDER_OBSERVER'))
                     or key.endswith(('_API_KEY', '_AUTH_TOKEN', '_ACCESS_TOKEN'))
                     or key in {'CLAUDE_CODE_OAUTH_TOKEN', 'D4D_INSTALL_TESTS', 'PYTHONHOME', 'PYTEST_PLUGINS'})
    for key in removed:
        env.pop(key)
    env.update(PYTHONDONTWRITEBYTECODE='1', PYTEST_DISABLE_PLUGIN_AUTOLOAD='1', PYTEST_ADDOPTS='',
               PIP_NO_INDEX='1', PIP_DISABLE_PIP_VERSION_CHECK='1', UV_OFFLINE='1',
               HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1', GIT_NO_LAZY_FETCH='1',
               PYTHONPATH=os.pathsep.join(str(ROOT / path) for path in ('src', 'scripts', '.')))
    command = [sys.executable, '-S', '-P', '-B', str(Path(__file__).resolve()), '--child', '--output', str(output)]
    if boundaries_only:
        command.append('--boundaries-only')
    save(output / 'plan.json', {'command': command, 'head': expected, 'target': TARGET,
        'modules': MODULES, 'credential_names_removed': removed,
        'selected_nodes': BOUNDARY_NODES if boundaries_only else None,
        'scope': 'Complete builder and affected sizing test modules; secret removal is not a network sandbox.'})
    started = time.monotonic()
    with (output / 'pytest.log').open('xb') as log:
        code = subprocess.run(command, cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT).returncode
    after = source()
    save(output / 'source-after.json', after)
    outcome = {'returncode': code, 'source_unchanged': before == after,
               'wall_seconds': time.monotonic() - started, 'scientific_acceptance': 'not_assessed'}
    counts, invalid, skipped, seen = dict.fromkeys(MODULES, 0), [], [], set()
    if (output / 'pytest.xml').is_file():
        for case in ET.parse(output / 'pytest.xml').getroot().iter('testcase'):
            name = case.get('classname', '').removeprefix('tests.')
            identity = (case.get('classname'), case.get('name'))
            duplicate = identity in seen
            seen.add(identity)
            if duplicate or name not in counts or not case.get('name') or any(case.find(tag) is not None for tag in ('failure', 'error')):
                invalid.append({'classname': case.get('classname'), 'name': case.get('name'),
                                'tags': [node.tag for node in case], 'duplicate_identity': duplicate})
            elif case.find('skipped') is not None:
                skipped.append({'classname': case.get('classname'), 'name': case.get('name'),
                                'reason': case.find('skipped').get('message')})
            else:
                counts[name] += 1
    outcome.update(unmarked_identified_cases_by_module=counts, invalid_junit_cases=invalid, skipped=skipped)
    origin_complete = all((output / name).is_file() for name in ('origins-before.json', 'origins-after.json'))
    if boundaries_only:
        expected_identities = {('tests.test_build_api_registrations', node.split('::')[1]) for node in BOUNDARY_NODES}
        selection_complete = seen == expected_identities and counts == dict(zip(MODULES, (3, 0))) and not skipped
    else:
        selection_complete = all(counts.values())
    outcome['passed'] = code == 0 and before == after and selection_complete and not invalid and origin_complete
    save(output / 'outcome.json', outcome)
    print(json.dumps(outcome, sort_keys=True), flush=True)
    return 0 if outcome['passed'] else 1


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--expect-head')
    parser.add_argument('--child', action='store_true')
    parser.add_argument('--boundaries-only', action='store_true', help='Rerun only the three exact ceiling-boundary cases.')
    options = parser.parse_args()
    raise SystemExit(child(options.output.resolve(), options.boundaries_only) if options.child
                     else run(options.output.resolve(), options.expect_head, options.boundaries_only))
