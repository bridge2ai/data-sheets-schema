#!/usr/bin/env python3
# Purpose: verify #5210 report-admission composition with A13 on frozen local source.
# Inputs: clean committed merge, A13 base/head pins, three full suites, physical venv.
# Outputs: fresh external basetemp, source/import snapshots, pytest log/XML and outcome.
# Refs #5210/#5157/#5158; 2026-10-28. Adapted from validate_wave3_20261027.py.
"""Offline full suites or one complete CHORUS parity case; hooks supplement the sandbox."""
import argparse
import importlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('wave3_common', Path(__file__).with_name('wave3_validation_common_20261027.py'))
common = importlib.util.module_from_spec(spec)
spec.loader.exec_module(common)
common.ROOT = ROOT
PROTECTED = ('.claude/commands/d4d-uniform-rules-v2.md', 'src/download/prompts/d4d_generic_arm_prompt_v10.md',
             'src/data_sheets_schema/shared_generation.py', 'src/download/prompts/canonical_hashes.yaml',
             'src/data_sheets_schema/api_Generation_v2.py')
MODULES = ('test_download.test_api_runner', 'test_usage_ledger', 'test_report_admission')
EXPECTED_A13 = '04799422669fb2bd9f571bf8c0800dfc4b0ef008'
EXPECTED_REPORT_ADMISSION = 'aaa6f5bec2a0c7832d36143c4c7470d51cb8cee4'
COMPOSITION = 'd72c8085f87f0d6f5b0d83457d2df16f83afb9af'
WIRE_CASE = 'test_chorus_wire_is_byte_identical_to_the_base_and_is_what_was_counted'


def deny_live(event, args):
    if event in {'socket.connect', 'socket.getaddrinfo', 'socket.sendto'}:
        raise RuntimeError('Wave3 offline validation forbids network: ' + event)
    if event == 'subprocess.Popen':
        name = Path(os.fsdecode(args[0])).name
        if name in {'claude', 'gh', 'curl', 'wget', 'ssh'}:
            raise RuntimeError('Wave3 forbids live command: ' + name)


def child(options):
    if not sys.flags.no_site or not sys.flags.safe_path or not sys.dont_write_bytecode:
        raise ValueError('requires -S -P -B')
    venv = Path(sys.executable).parent.parent
    site = venv / 'lib' / ('python' + '.'.join(map(str, sys.version_info[:2]))) / 'site-packages'
    if not (venv / 'pyvenv.cfg').is_file() or not site.is_dir() or site.resolve() != site:
        raise ValueError('physical venv required')
    sys.prefix = sys.exec_prefix = str(venv)
    sys.path.append(str(site))
    sys.addaudithook(deny_live)
    common.save(options.output / 'bootstrap.json', {'python': sys.version, 'executable': sys.executable,
        'site': str(site), 'pth_disabled': True, 'network_hook': True, 'dependency_bytes_attested': False})
    common.MODULES = tuple(options.module)
    for module in options.module:
        importlib.import_module('tests.' + module)
    baseline = json.loads((options.output / 'source-before.json').read_text())
    common.save(options.output / 'origins-before.json', common.origins(baseline))
    import pytest
    selected = (['tests/test_report_admission.py::' + WIRE_CASE] if options.wire_only else
                ['tests/' + module.replace('.', '/') + '.py' for module in options.module])
    args = ['-q', '-p', 'no:cacheprovider', '--basetemp', str(options.output / 'cases'),
            '--junitxml', str(options.output / 'pytest.xml'), *selected]
    common.save(options.output / 'pytest-command.json', {'args': args, 'cwd': str(ROOT)})
    try:
        return int(pytest.main(args))
    finally:
        common.save(options.output / 'origins-after.json', common.origins(baseline))


def run(options):
    if tuple(options.module) != MODULES or options.base != EXPECTED_A13:
        raise ValueError('exact three full suites and reviewed A13 base required')
    parents = common.git('show', '-s', '--format=%P', COMPOSITION).decode().strip().split()
    if parents != [EXPECTED_REPORT_ADMISSION, EXPECTED_A13]:
        raise ValueError('composition does not preserve the expected ordered parents')
    common.git('merge-base', '--is-ancestor', COMPOSITION, 'HEAD')
    output = options.output
    if output.is_relative_to(ROOT):
        raise ValueError('evidence must be outside frozen tree')
    output.mkdir(parents=True, exist_ok=False)
    # Git's remerge-diff computes temporary objects. Some Git versions print
    # an object-directory failure but still exit zero; check stderr as well.
    # Keep temporary writes outside the shared repository object store.
    object_store = Path(common.git('rev-parse', '--path-format=absolute',
                                  '--git-common-dir').decode().strip()) / 'objects'
    git_env = {key: value for key, value in os.environ.items() if not key.startswith('GIT_')}
    with tempfile.TemporaryDirectory(prefix='git-remerge-', dir=output) as object_directory:
        git_env.update(GIT_NO_LAZY_FETCH='1', GIT_OPTIONAL_LOCKS='0',
                       GIT_OBJECT_DIRECTORY=object_directory,
                       GIT_ALTERNATE_OBJECT_DIRECTORIES=str(object_store))
        remerge = subprocess.run(['git', '--no-replace-objects', 'show', '--remerge-diff',
                                  '--format=', COMPOSITION], cwd=ROOT, env=git_env,
                                 capture_output=True)
    if remerge.returncode or remerge.stdout or remerge.stderr:
        raise ValueError('expected successful silent conflict-free remerge: ' +
                         remerge.stderr.decode(errors='replace'))
    before = common.source()
    common.save(output / 'source-before.json', before)
    if before['head'] != options.expect_head or not before['tracked_exact'] or common.git('status', '--porcelain=v1', '--untracked-files=all'):
        raise ValueError('clean exact committed source required')
    changed = common.git('diff', '--name-only', options.base, 'HEAD').decode().splitlines()
    if any(p in PROTECTED or p.startswith(('data/d4d_concatenated/', 'data/ATTIC/')) for p in changed):
        raise ValueError('protected or historical-run path changed against base')
    env = dict(os.environ)
    removed = sorted(k for k in env if k.startswith(('ANTHROPIC_', 'CBORG_', 'OPENAI_', 'GIT_'))
                     or k.endswith(('_API_KEY', '_AUTH_TOKEN', '_ACCESS_TOKEN'))
                     or k in {'CLAUDE_CODE_OAUTH_TOKEN', 'D4D_INSTALL_TESTS', 'PYTHONHOME', 'PYTEST_PLUGINS', 'RECEIPTS_V5_INSTRUMENT'})
    for key in removed:
        env.pop(key)
    env.update(PYTHONDONTWRITEBYTECODE='1', PYTEST_DISABLE_PLUGIN_AUTOLOAD='1', PYTEST_ADDOPTS='',
               PIP_NO_INDEX='1', UV_OFFLINE='1', HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1',
               GIT_NO_LAZY_FETCH='1', PYTHONPATH=os.pathsep.join(str(ROOT / p) for p in ('src', 'scripts', '.')))
    command = [sys.executable, '-S', '-P', '-B', str(Path(__file__).resolve()), '--child', '--output', str(output)]
    if options.wire_only:
        command.append('--wire-only')
    for module in options.module:
        command += ['--module', module]
    common.save(output / 'plan.json', {'command': command, 'head': options.expect_head, 'base': options.base,
        'modules': options.module, 'credential_names_removed': removed, 'changed_paths': changed,
        'composition': {'commit': COMPOSITION, 'parents': parents, 'remerge_diff_bytes': len(remerge.stdout),
                        'remerge_stderr_bytes': len(remerge.stderr), 'remerge_returncode': remerge.returncode,
                        'temporary_objects': 'external directory; common object store read-only alternate'},
        'selection': 'complete affected CHORUS parity test' if options.wire_only else 'three full suites',
        'scope': 'Offline selected modules; Python audit guard does not isolate arbitrary child binaries.'})
    start = time.monotonic()
    with (output / 'pytest.log').open('xb') as log:
        code = subprocess.run(command, cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT).returncode
    after = common.source()
    common.save(output / 'source-after.json', after)
    counts = dict.fromkeys(options.module, 0)
    invalid, skipped, seen = [], [], set()
    if (output / 'pytest.xml').is_file():
        for case in ET.parse(output / 'pytest.xml').getroot().iter('testcase'):
            classname = case.get('classname', '').removeprefix('tests.')
            matches = [name for name in options.module
                       if classname == name or classname.startswith(name + '.')]
            module = matches[0] if len(matches) == 1 else None
            identity = (case.get('classname'), case.get('name'))
            if identity in seen or module not in counts or not case.get('name') or any(case.find(t) is not None for t in ('failure', 'error')):
                invalid.append({'identity': identity, 'tags': [n.tag for n in case]})
            elif case.find('skipped') is not None:
                skipped.append({'identity': identity, 'reason': case.find('skipped').get('message')})
            else:
                counts[module] += 1
            seen.add(identity)
    complete = all((output / f'origins-{stage}.json').is_file() for stage in ('before', 'after'))
    selection_complete = (seen == {('tests.test_report_admission', WIRE_CASE)} and
                          counts == {name: int(name == 'test_report_admission') for name in options.module}
                          if options.wire_only else all(counts.values()))
    outcome = {'returncode': code, 'source_unchanged': before == after, 'wall_seconds': time.monotonic() - start,
               'passed_cases_by_module': counts, 'invalid_junit_cases': invalid, 'skipped': skipped,
               'scientific_acceptance': 'not_assessed',
               'passed': code == 0 and before == after and selection_complete and not invalid and not skipped and complete}
    common.save(output / 'outcome.json', outcome)
    print(json.dumps(outcome, sort_keys=True), flush=True)
    return 0 if outcome['passed'] else 1


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--module', action='append', required=True)
    parser.add_argument('--expect-head')
    parser.add_argument('--base')
    parser.add_argument('--wire-only', action='store_true', help='Run the complete affected CHORUS parity test only.')
    parser.add_argument('--child', action='store_true')
    args = parser.parse_args()
    args.output = args.output.resolve()
    raise SystemExit(child(args) if args.child else run(args))
