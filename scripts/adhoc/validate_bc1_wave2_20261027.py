#!/usr/bin/env python3
# Purpose: source-attested offline BC1 and affected legacy validation.
# Inputs: clean committed checkout, physical project venv; outputs: fresh external logs/XML/JSON.
# Refs Wave2 BC1/D44/D45; 2026-10-27. Uses committed A17 source/origin attestation helpers.
"""No providers, network or protected writes; hook tests are in-memory simulations."""
import argparse
import importlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
TARGET = '0674193f6d4e1b42a6f3afe6d5475c8635cfbdf2'
GROUPS = {
    'bc1': ('test_bc1_codec', 'test_bc1_audit', 'test_bc1_context',
            'test_bc1_registration', 'test_bc1_selection', 'test_bc1_api_rendering', 'test_bc1_runtime'),
    'legacy': ('test_audit_omissions', 'test_build_api_registrations',
               'test_registration_input_sizing', 'test_shared_generation_selection',
               'test_shared_generation_condition_compatibility', 'test_shared_generation_cli',
               'test_shared_generation_runtime', 'test_receipt_completion_runtime'),
}
helper = ROOT / 'scripts/adhoc/validate_a17_r7b_fix_20261027.py'
descriptor = importlib.util.spec_from_file_location('bc1_validation_support', helper)
support = importlib.util.module_from_spec(descriptor)
descriptor.loader.exec_module(support)


def child(output, modules, nodes):
    if not sys.flags.no_site or not sys.flags.safe_path or not sys.dont_write_bytecode:
        raise ValueError('child requires -S -P -B')
    venv = Path(sys.executable).parent.parent
    site = venv / 'lib' / ('python' + '.'.join(map(str, sys.version_info[:2]))) / 'site-packages'
    if not (venv / 'pyvenv.cfg').is_file() or not site.is_dir() or site.resolve() != site:
        raise ValueError('physical project venv required')
    before_prefix = {'prefix': sys.prefix, 'exec_prefix': sys.exec_prefix}
    sys.prefix = sys.exec_prefix = str(venv)
    sys.path.append(str(site))
    def refuse_network(event, args):
        if event in ('socket.connect', 'socket.getaddrinfo', 'socket.sendto'):
            raise RuntimeError('BC1 offline validation forbids network: ' + event)
    sys.addaudithook(refuse_network)
    support.save(output / 'bootstrap.json', {
        'prefix_before': before_prefix, 'prefix': sys.prefix, 'exec_prefix': sys.exec_prefix,
        'executable': sys.executable, 'python': sys.version, 'sys_path': sys.path,
        'site_startup': 'disabled', 'pth_execution': 'disabled',
        'network_control': 'Python audit hook; not an OS-level subprocess network sandbox',
        'dependency_bytes_attested': False,
        'protected_hook_tests': 'compile exact proposal in memory; disk source stays unchanged; not installed acceptance'})
    support.MODULES = modules
    for name in modules:
        importlib.import_module('tests.' + name)
    baseline = json.loads((output / 'source-before.json').read_text())
    support.save(output / 'origins-before.json', support.origins(baseline))
    import pytest
    args = ['-q', '-p', 'no:cacheprovider', '--basetemp', str(output / 'cases'),
            '--junitxml', str(output / 'pytest.xml'),
            *(nodes or ['tests/' + name + '.py' for name in modules])]
    support.save(output / 'pytest-command.json', {'args': args, 'cwd': str(ROOT)})
    try:
        return int(pytest.main(args))
    finally:
        support.save(output / 'origins-after.json', support.origins(baseline))


def run(output, expected, group, nodes):
    modules = GROUPS[group]
    if nodes:
        if any(not any(node == 'tests/' + m + '.py' or node.startswith('tests/' + m + '.py::')
                       for m in modules) for node in nodes):
            raise ValueError('explicit nodes must belong to the declared group')
        modules = tuple(m for m in modules if any(node.split('::')[0] == 'tests/' + m + '.py' for node in nodes))
    if output.is_relative_to(ROOT):
        raise ValueError('external evidence required')
    output.mkdir(parents=True, exist_ok=False)
    before = support.source()
    support.save(output / 'source-before.json', before)
    if before['head'] != expected or not before['tracked_exact'] or support.git('status', '--porcelain=v1', '--untracked-files=all'):
        raise ValueError('clean committed exact source required')
    for name in support.PROTECTED:
        if support.git('ls-tree', TARGET, '--', name):
            if (ROOT / name).read_bytes() != support.git('show', TARGET + ':' + name):
                raise ValueError('protected source changed: ' + name)
        elif (ROOT / name).exists() or (ROOT / name).is_symlink():
            raise ValueError('absent protected file created: ' + name)
    env = dict(os.environ)
    removed = sorted(k for k in env if k.startswith(('ANTHROPIC_', 'CBORG_', 'OPENAI_', 'GIT_'))
        or k.endswith(('_API_KEY', '_AUTH_TOKEN', '_ACCESS_TOKEN'))
        or k in {'CLAUDE_CODE_OAUTH_TOKEN', 'D4D_INSTALL_TESTS', 'PYTHONHOME', 'PYTEST_PLUGINS'})
    for key in removed:
        env.pop(key)
    env.update(PYTHONDONTWRITEBYTECODE='1', PYTEST_DISABLE_PLUGIN_AUTOLOAD='1', PYTEST_ADDOPTS='',
        PIP_NO_INDEX='1', PIP_DISABLE_PIP_VERSION_CHECK='1', UV_OFFLINE='1',
        HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1', GIT_NO_LAZY_FETCH='1',
        PYTHONPATH=os.pathsep.join(str(ROOT / p) for p in ('src', 'scripts', '.')))
    command = [sys.executable, '-S', '-P', '-B', str(Path(__file__).resolve()),
               '--child', '--output', str(output), '--group', group]
    for node in nodes:
        command.extend(['--node', node])
    support.save(output / 'plan.json', {'command': command, 'head': expected, 'target': TARGET,
        'modules': modules, 'nodes': nodes, 'credential_names_removed': removed})
    started = time.monotonic()
    with (output / 'pytest.log').open('xb') as log:
        code = subprocess.run(command, cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT).returncode
    after = support.source()
    support.save(output / 'source-after.json', after)
    counts = dict.fromkeys(modules, 0)
    seen, invalid, skipped = set(), [], []
    if (output / 'pytest.xml').is_file():
        for case in ET.parse(output / 'pytest.xml').getroot().iter('testcase'):
            identity = (case.get('classname'), case.get('name'))
            module = case.get('classname', '').removeprefix('tests.').split('.')[0]
            if (identity in seen or module not in counts or not case.get('name')
                    or any(case.find(tag) is not None for tag in ('failure', 'error'))):
                invalid.append({'classname': identity[0], 'name': identity[1], 'tags': [c.tag for c in case]})
            elif case.find('skipped') is not None:
                skipped.append({'classname': identity[0], 'name': identity[1],
                                'reason': case.find('skipped').get('message')})
            else:
                counts[module] += 1
            seen.add(identity)
    origin_complete = all((output / n).is_file() for n in ('origins-before.json', 'origins-after.json'))
    result = {'returncode': code, 'source_unchanged': before == after,
        'wall_seconds': time.monotonic() - started, 'passes_by_module': counts,
        'invalid_junit_cases': invalid, 'skipped': skipped,
        'passed': code == 0 and before == after and all(counts.values()) and not invalid and origin_complete,
        'scientific_acceptance': 'not_assessed', 'installed_hook_acceptance': 'not_assessed'}
    support.save(output / 'outcome.json', result)
    print(json.dumps(result, sort_keys=True), flush=True)
    return 0 if result['passed'] else 1


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--expect-head')
    parser.add_argument('--group', choices=GROUPS, default='bc1')
    parser.add_argument('--node', action='append', default=[])
    parser.add_argument('--child', action='store_true')
    options = parser.parse_args()
    selected = GROUPS[options.group]
    if options.node:
        selected = tuple(m for m in selected if any(n.split('::')[0] == 'tests/' + m + '.py' for n in options.node))
    raise SystemExit(child(options.output.resolve(), selected, options.node) if options.child else
                     run(options.output.resolve(), options.expect_head, options.group, options.node))
