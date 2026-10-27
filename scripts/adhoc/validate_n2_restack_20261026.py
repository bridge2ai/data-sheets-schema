#!/usr/bin/env python3
# Purpose: retain offline N2 restack test roster, source identity and results.
# Inputs: committed N2 tree, preserved N2 range and selected group; outputs: fresh external evidence.
# Refs #4354 / 2026-10-26 coordination priority 5. Date: 2026-10-27.
"""Functional checks only; no timing causation, native binary or provider acceptance."""
import argparse
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
OLD_BASE = '7c1002caeb776ccb0caebb474e22e5558b7b9602'
OLD_TOP = '8b1daa80f4f970c956dbaf7835c1694abc773abf'
TARGET = 'a0e28d8821c69e2d4fe1b75b14e3c2a2140ae4d5'
POSITIVE = ('tests/test_native_shared_execution.py', 'tests/test_native_shared_execution_variant.py')
LEGACY = tuple('tests/' + name + '.py' for name in (
    'test_schema_snapshot_cache', 'test_schema_snapshot_compatibility',
    'test_shared_generation_selection', 'test_source_heading_runtime',
    'test_source_heading_runtime_api', 'test_receipt_completion_policy',
    'test_receipts', 'test_backfill_checks', 'test_derive_core',
    'test_native_receipt_origin_reporting', 'test_provenance_reasoning_message',
    'test_provenance_reasoning_effort', 'test_provenance_header',
    'test_cli/test_provenance_preserves_validation', 'test_cli/test_provenance_prompt',
    'test_replicate_structure', 'test_report_audit_totals', 'test_generic_v10_r9_enum_criteria'))
PROTECTED = ('src/data_sheets_schema/shared_generation.py', 'src/download/prompts/canonical_hashes.yaml')


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT,
        env=dict(os.environ, GIT_OPTIONAL_LOCKS='0', GIT_NO_LAZY_FETCH='1'))


def save(path, value):
    with path.open('x') as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write('\n')


def roster():
    changed = sorted(p for p in git('diff', '--name-only', OLD_BASE, OLD_TOP, '--', 'tests/').decode().splitlines()
                     if Path(p).name.startswith('test_') and p.endswith('.py'))
    if len(changed) != 74 or not set(POSITIVE).issubset(changed):
        raise ValueError('preserved N2 test roster differs from reviewed 74-module scope')
    groups = {'native': [p for p in changed if p not in POSITIVE],
              'legacy': [p for p in LEGACY if p not in changed],
              'positive': list(POSITIVE)}
    for paths in groups.values():
        for path in paths:
            if not (ROOT / path).is_file():
                raise ValueError('required test file missing: ' + path)
    return groups


def origins():
    result = {}
    for name, module in tuple(sys.modules.items()):
        if name != 'data_sheets_schema' and not name.startswith('data_sheets_schema.'):
            continue
        paths = list(getattr(module, '__path__', ()))
        if getattr(module, '__file__', None):
            paths.append(module.__file__)
        for path in paths:
            actual = Path(path).resolve()
            if not actual.is_relative_to(ROOT / 'src'):
                raise ValueError('foreign project module: ' + name + ' -> ' + str(actual))
        result[name] = paths
    return result


def child(group, output):
    # Namespace packages otherwise inherit the primary editable install's .pth
    # path even when our explicit PYTHONPATH precedes it. Disable site startup,
    # then expose only the interpreter's physical dependency directory.
    if not sys.flags.no_site or not sys.flags.safe_path or not sys.dont_write_bytecode:
        raise ValueError('child requires -S -P -B isolation')
    venv = Path(sys.executable).parent.parent
    site = venv / 'lib' / ('python' + '.'.join(map(str, sys.version_info[:2]))) / 'site-packages'
    if (not (venv / 'pyvenv.cfg').is_file() or not site.is_dir()
            or site.resolve() != site or str(site) in sys.path):
        raise ValueError('expected physical venv dependencies with site startup disabled')
    sys.path.append(str(site))
    save(output / 'dependency-bootstrap.json', {
        'site_startup': 'disabled', 'pth_execution': 'disabled', 'site_packages': str(site),
        'sys_path': list(sys.path), 'dependency_bytes_attested': False})
    for name in ('native_shared_selection', 'native_shared_receipts', 'native_shared_capture', 'native_shared_execution'):
        importlib.import_module('data_sheets_schema.' + name)
    save(output / 'origins-before.json', origins())
    import pytest
    args = ['-q', '-p', 'no:cacheprovider', '--basetemp', str(output / 'cases'),
            '--junitxml', str(output / 'pytest.xml'), *roster()[group]]
    save(output / 'pytest-command.json', {'args': args, 'cwd': str(ROOT)})
    try:
        return int(pytest.main(args))
    finally:
        save(output / 'origins-after.json', origins())


def run(group, output, expected):
    if output.is_relative_to(ROOT):
        raise ValueError('evidence must be outside frozen checkout')
    output.mkdir(parents=True, exist_ok=False)
    sys.path.insert(0, str(ROOT))
    from utils.native_shared_acceptance import source
    before = source(ROOT)
    save(output / 'source-before.json', before)
    if before['head'] != expected or not before['tracked_exact'] or git('status', '--porcelain'):
        raise ValueError('committed clean exact source required')
    for name in PROTECTED:
        if (ROOT / name).read_bytes() != git('show', TARGET + ':' + name):
            raise ValueError('protected target differs: ' + name)
    git('merge-base', '--is-ancestor', TARGET, 'HEAD')
    env = dict(os.environ)
    removed = sorted(k for k in env if k.startswith(('ANTHROPIC_', 'CBORG_', 'OPENAI_', 'D4D_RECORDER_OBSERVER'))
                     or k.endswith(('_API_KEY', '_AUTH_TOKEN', '_ACCESS_TOKEN'))
                     or k in {'CLAUDE_CODE_OAUTH_TOKEN', 'D4D_INSTALL_TESTS', 'PYTHONHOME', 'PYTEST_PLUGINS'})
    for key in removed:
        env.pop(key)
    env.update(PYTHONDONTWRITEBYTECODE='1', PYTEST_DISABLE_PLUGIN_AUTOLOAD='1', PYTEST_ADDOPTS='',
               PIP_NO_INDEX='1', PIP_DISABLE_PIP_VERSION_CHECK='1', UV_OFFLINE='1',
               HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1', GIT_NO_LAZY_FETCH='1',
               PYTHONPATH=os.pathsep.join(str(ROOT / p) for p in ('src', 'scripts', '.')))
    command = [sys.executable, '-S', '-P', '-B', str(Path(__file__).resolve()),
               '--child', '--group', group, '--output', str(output)]
    save(output / 'plan.json', {'group': group, 'groups': roster(), 'head': expected, 'target': TARGET,
        'python': sys.version, 'executable': sys.executable, 'command': command,
        'credential_names_removed': removed, 'plugin_autoload': 'disabled',
        'packages': sorted((d.metadata.get('Name', ''), d.version) for d in importlib.metadata.distributions()),
        'scope': 'functional offline fixtures, not idle-host timing; credential removal is not a network sandbox'})
    started = time.monotonic()
    with (output / 'pytest.log').open('xb') as log:
        code = subprocess.run(command, cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT).returncode
    after = source(ROOT)
    save(output / 'source-after.json', after)
    summary = {'returncode': code, 'source_unchanged': before == after,
               'wall_seconds': time.monotonic() - started, 'scientific_acceptance': 'not_assessed'}
    if (output / 'pytest.xml').is_file():
        cases = list(ET.parse(output / 'pytest.xml').getroot().iter('testcase'))
        summary['junit'] = {key: sum(case.find(tag) is not None for case in cases)
                            for key, tag in (('failures', 'failure'), ('errors', 'error'), ('skipped', 'skipped'))}
        summary['junit']['cases'] = len(cases)
        summary['junit']['passed'] = sum(not any(case.find(t) is not None for t in ('failure', 'error', 'skipped')) for case in cases)
    save(output / 'outcome.json', summary)
    print(json.dumps(summary, sort_keys=True), flush=True)
    return code if before == after else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--group', choices=('native', 'legacy', 'positive'), required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--expected-head')
    parser.add_argument('--child', action='store_true')
    args = parser.parse_args()
    if args.child:
        return child(args.group, args.output.resolve())
    if not args.expected_head:
        parser.error('--expected-head required')
    return run(args.group, args.output.resolve(), args.expected_head)


if __name__ == '__main__':
    raise SystemExit(main())
