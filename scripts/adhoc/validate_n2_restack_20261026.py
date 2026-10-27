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
POSITIVE_NODES = (
    ('neutral', POSITIVE[0] + '::test_actual_public_correction_three_workers_and_saved_completion'),
    ('omission', POSITIVE[1] + '::test_actual_public_merged_omissions_and_all_chunk_statuses'),
)
POSITIVE_MODULES = tuple('data_sheets_schema.' + name for name in (
    'native_shared_selection', 'native_shared_receipts', 'native_shared_capture', 'native_shared_execution'))
REPAIR = ('tests/test_native_shared_response_identity.py',
          'tests/test_native_shared_stream_bindings.py',
          'tests/test_native_trace_single_decode.py')
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
              'positive': list(POSITIVE), 'repair': list(REPAIR)}
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


def positive_node(label):
    if label not in dict(POSITIVE_NODES):
        raise ValueError('positive child requires one exact registered test label')
    return dict(POSITIVE_NODES)[label]


def child(group, output, positive_label=None):
    if group == 'positive':
        positive_node(positive_label)
    elif positive_label is not None:
        raise ValueError('positive label is only valid for a positive child')
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
    prefix_before = {'prefix': sys.prefix, 'exec_prefix': sys.exec_prefix}
    # Python 3.13's site.venv normally performs this assignment before loading
    # .pth files. Preserve normal venv metadata without executing those hooks.
    sys.prefix = sys.exec_prefix = str(venv)
    sys.path.append(str(site))
    save(output / 'dependency-bootstrap.json', {
        'site_startup': 'disabled', 'pth_execution': 'disabled', 'site_packages': str(site),
        'prefix_before': prefix_before, 'prefix': sys.prefix, 'exec_prefix': sys.exec_prefix,
        'base_prefix': sys.base_prefix, 'base_exec_prefix': sys.base_exec_prefix,
        'sys_path': list(sys.path), 'dependency_bytes_attested': False})
    for name in ('native_shared_selection', 'native_shared_receipts', 'native_shared_capture', 'native_shared_execution'):
        importlib.import_module('data_sheets_schema.' + name)
    save(output / 'origins-before.json', origins())
    import pytest
    args = ['-q', '-p', 'no:cacheprovider', '--basetemp', str(output / 'cases'),
            '--junitxml', str(output / 'pytest.xml'),
            *([positive_node(positive_label)] if group == 'positive' else roster()[group])]
    save(output / 'pytest-command.json', {'args': args, 'cwd': str(ROOT)})
    try:
        return int(pytest.main(args))
    finally:
        save(output / 'origins-after.json', origins())


def run(group, output, expected, *, positive_label=None):
    if group == 'positive' and positive_label is None:
        return run_positive(output, expected)
    if positive_label is not None:
        if group != 'positive':
            raise ValueError('positive label requires the positive group')
        positive_node(positive_label)
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
    if positive_label is not None:
        command += ['--positive-label', positive_label]
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
        # An interrupted pytest run can emit an anonymous unfinished testcase.
        # Do not promote that unmarked XML entry (or an incomplete run) to a pass.
        identified = [case for case in cases if case.get('name') and case.get('classname')]
        unmarked = sum(not any(case.find(t) is not None for t in ('failure', 'error', 'skipped'))
                       for case in identified)
        summary['junit']['cases_without_identity'] = len(cases) - len(identified)
        summary['junit']['unmarked_identified_cases'] = unmarked
        summary['junit']['passed'] = unmarked if code in (0, 1) and len(identified) == len(cases) else None
    save(output / 'outcome.json', summary)
    print(json.dumps(summary, sort_keys=True), flush=True)
    return code if before == after else 1


def evidence_json(path):
    if path.is_symlink() or not path.is_file():
        raise ValueError('missing regular evidence file: ' + str(path))
    return json.loads(path.read_text())


def positive_gate(output, label, code, baseline):
    """One exact successful test plus completed source/import proof, before next admission."""
    if code != 0:
        raise ValueError(label + ' child did not exit successfully: ' + str(code))
    for name in ('source-before.json', 'source-after.json'):
        if evidence_json(output / name) != baseline:
            raise ValueError(label + ' source evidence differs from the original frozen baseline')
    for name in ('origins-before.json', 'origins-after.json'):
        observed = evidence_json(output / name)
        if not isinstance(observed, dict) or not set(POSITIVE_MODULES).issubset(observed):
            raise ValueError(label + ' lacks required project import origins')
        for module, paths in observed.items():
            if (module != 'data_sheets_schema' and not module.startswith('data_sheets_schema.')):
                raise ValueError(label + ' has an unexpected origin record')
            if not isinstance(paths, list) or not paths:
                raise ValueError(label + ' has empty project import origins')
            for value in paths:
                path = Path(value)
                if (not path.is_absolute() or path.resolve(strict=True) != path
                        or not path.is_relative_to(ROOT / 'src')):
                    raise ValueError(label + ' has a foreign project import origin')
    bootstrap = evidence_json(output / 'dependency-bootstrap.json')
    if bootstrap.get('site_startup') != 'disabled' or bootstrap.get('pth_execution') != 'disabled':
        raise ValueError(label + ' lacks the isolated dependency bootstrap')
    node = positive_node(label)
    path, name = node.split('::')
    junit = output / 'pytest.xml'
    if junit.is_symlink() or not junit.is_file():
        raise ValueError(label + ' lacks regular JUnit evidence')
    root = ET.parse(junit).getroot()
    cases = list(root.iter('testcase'))
    if (len(cases) != 1 or cases[0].get('name') != name
            or cases[0].get('classname') != path.removesuffix('.py').replace('/', '.')
            or any(list(root.iter(tag)) for tag in ('failure', 'error', 'skipped'))
            or any(int(element.get(key, '0')) != 0 for element in root.iter()
                   for key in ('failures', 'errors', 'skipped'))):
        raise ValueError(label + ' must pass exactly its one named test without skips/errors')
    return {'node': node, 'returncode': code, 'exact_single_junit_case': True,
            'source_matches_original_baseline': True, 'import_origins_verified': True}


def run_positive(output, expected):
    """Neutral gates omission; missing/failed evidence leaves omission explicitly pending."""
    if output.is_relative_to(ROOT):
        raise ValueError('evidence must be outside frozen checkout')
    output.mkdir(parents=True, exist_ok=False)
    sys.path.insert(0, str(ROOT))
    from utils.native_shared_acceptance import NODES, source
    summary = {'status': 'failed', 'runtime_gates_passed': False,
               'scientific_acceptance': 'not_assessed', 'source_unchanged': False,
               'stages': {label: {'status': 'pending', 'node': node} for label, node in POSITIVE_NODES}}
    baseline, active = None, None
    try:
        if tuple(NODES) != POSITIVE_NODES:
            raise ValueError('public acceptance node identities changed')
        baseline = source(ROOT)
        save(output / 'source-before.json', baseline)
        if baseline['head'] != expected or not baseline['tracked_exact'] or git('status', '--porcelain'):
            raise ValueError('committed clean exact source required')
        save(output / 'plan.json', {'head': expected, 'target': TARGET, 'nodes': POSITIVE_NODES,
            'order': 'neutral must pass exact result/source/origin gates before omission starts',
            'child_flags': ['-S', '-P', '-B'], 'deadlines_changed': False,
            'scope': 'offline public software fixtures, not real native/scientific acceptance'})
        for label, node in POSITIVE_NODES:
            active = label
            if source(ROOT) != baseline or git('status', '--porcelain'):
                raise ValueError('source changed before ' + label)
            summary['stages'][label]['status'] = 'running'
            code = run('positive', output / label, expected, positive_label=label)
            summary['stages'][label]['returncode'] = code
            proof = positive_gate(output / label, label, code, baseline)
            after = source(ROOT)
            save(output / ('source-after-' + label + '.json'), after)
            if after != baseline or git('status', '--porcelain'):
                raise ValueError('source changed after ' + label)
            summary['stages'][label] = {'status': 'passed', **proof}
        summary['status'] = 'passed'
    except (Exception, KeyboardInterrupt) as error:
        summary['error'] = {'type': type(error).__name__, 'message': str(error)}
        if active is not None and summary['stages'][active]['status'] == 'running':
            summary['stages'][active]['status'] = 'failed'
    finally:
        try:
            final = source(ROOT)
            save(output / 'source-final.json', final)
            summary['source_unchanged'] = baseline is not None and final == baseline and not git('status', '--porcelain')
        except Exception as error:
            summary['final_source_error'] = {'type': type(error).__name__, 'message': str(error)}
        if not summary['source_unchanged']:
            summary['status'] = 'failed'
        if summary['stages']['omission']['status'] == 'pending':
            summary['omission_not_run'] = 'neutral completion and unchanged-source/import/JUnit gates did not all pass'
        summary['runtime_gates_passed'] = summary['status'] == 'passed'
        save(output / 'outcome.json', summary)
    print(json.dumps(summary, sort_keys=True), flush=True)
    return 0 if summary['status'] == 'passed' else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--group', choices=('native', 'legacy', 'positive', 'repair'), required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--expected-head')
    parser.add_argument('--child', action='store_true')
    parser.add_argument('--positive-label', choices=tuple(dict(POSITIVE_NODES)))
    args = parser.parse_args()
    if args.child:
        return child(args.group, args.output.resolve(), args.positive_label)
    if args.positive_label is not None:
        parser.error('--positive-label is only valid for an internal child')
    if not args.expected_head:
        parser.error('--expected-head required')
    return run(args.group, args.output.resolve(), args.expected_head)


if __name__ == '__main__':
    raise SystemExit(main())
