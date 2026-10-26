#!/usr/bin/env python3
"""Compare mixed receipt-policy refusal on exact N1b/baseline source checkouts.

2026-10-23; N1b static compatibility finding, not a counted suite failure.
Inputs: repeated --checkout LABEL ABSOLUTE_PATH EXPECTED_FULL_COMMIT plus an
absolute venv Python interpreter. Fresh children skip site/.pth processing and
append only that interpreter's explicitly verified dependency directory.
Output: JSON to stdout with source/commit proof,
exact errors/traceback paths and public refusal behavior. Read-only: no files,
registrations, provider calls, native binaries, Git mutation or lazy fetch.
Commit this helper before use. The source checkouts must already exist.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib
from importlib.machinery import ModuleSpec, NamespaceLoader
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import traceback
from types import ModuleType


NATIVE_POLICY_SHA = 'de90df8ec7818b645e352fbae6bcc153387c02d7fcf71ef8f2abe409a083b75a'


def encoded(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False,
                      separators=(',', ':')).encode('utf-8')


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def git(root, *arguments, allowed=(0,)):
    env = {key: value for key, value in os.environ.items() if not key.startswith('GIT_')}
    env.update(GIT_OPTIONAL_LOCKS='0', GIT_NO_LAZY_FETCH='1')
    result = subprocess.run(['git', '--no-replace-objects', '-C', str(root), *arguments], env=env,
                            capture_output=True, timeout=20)
    if result.returncode not in allowed:
        raise ValueError('read-only Git command failed: ' + result.stderr.decode('utf-8', 'replace'))
    return result


def capture(operation):
    try:
        value = operation()
        return {'outcome': 'return', 'value': value}
    except Exception as error:
        return {'outcome': 'exception', 'type': type(error).__name__,
                'module': type(error).__module__, 'message': str(error),
                'frames': [{'path': row.filename, 'line': row.lineno, 'function': row.name}
                           for row in traceback.extract_tb(error.__traceback__)]}


class ForbiddenArtifact:
    """No test input path is acquired, even if selection unexpectedly succeeds."""
    def forbidden(self, *args, **kwargs):
        raise AssertionError('probe attempted receipt artifact acquisition')
    __fspath__ = open = read_bytes = read_text = exists = is_file = stat = resolve = forbidden


def native_identity():
    value = {'kind': 'd4d_native_shared_receipt_policy', 'version': 1,
        'registration_id': 'synthetic-n1b-cross-family-probe', 'condition': 'generic_v10',
        'runtime_policy_sha256': NATIVE_POLICY_SHA, 'receipt_instrument_version': 4,
        'coverage_floor': {'state': 'pending', 'mode': 'diagnostic_pilot'}}
    raw = encoded(value)
    return {'sha256': sha(raw), 'raw_json': raw.decode('utf-8')}


def api_registration(cp, policy, version):
    conditions = {1: 'generic_v8', 2: 'generic_v10', 3: 'generic_v10_source_heading_span_v1'}
    value = {'format': 'receipt_completion_registration_v' + str(version),
        'registration_id': 'synthetic-n1b-api-probe', 'condition': conditions[version],
        'runtime_policy_sha256': policy['sha256'], 'receipt_instrument_version': 4,
        'max_output_tokens': 4096, 'max_request_bytes': 1_000_000,
        'context_limit_tokens': 1_000_000,
        'context_limit_basis': 'Synthetic in-memory fixture; not a capacity claim',
        'coverage_floor': {'state': 'pending', 'mode': 'diagnostic_pilot'}}
    raw = encoded(value)
    # This establishes supported format and valid installed runtime policy,
    # without writing a registration or invoking a renderer/provider.
    cp.parse_registration(raw, version=version)
    return value, {'sha256': sha(raw), 'raw_json': raw.decode('utf-8')}


def dependency_environment(interpreter):
    """Locate installed dependencies without executing site or any .pth file."""
    interpreter = Path(interpreter)
    if (not interpreter.is_absolute() or interpreter.parent.name != 'bin'
            or interpreter.parent.resolve(strict=True) != interpreter.parent
            or not interpreter.is_file() or not os.access(interpreter, os.X_OK)):
        raise ValueError('probe requires an existing absolute venv/bin Python interpreter')
    venv = interpreter.parent.parent
    config = venv / 'pyvenv.cfg'
    if config.is_symlink() or not config.is_file() or config.stat().st_size > 64_000:
        raise ValueError('interpreter lacks a bounded regular pyvenv.cfg')
    raw = config.read_bytes()
    versions = re.findall(r'^(?:version_info|version)\s*=\s*(\d+)\.(\d+)(?:\.|\s|$)',
                          raw.decode('utf-8'), flags=re.MULTILINE)
    if not versions or len(set(versions)) != 1:
        raise ValueError('pyvenv.cfg must declare one consistent Python major/minor')
    version = '.'.join(versions[0])
    site_packages = venv / 'lib' / ('python' + version) / 'site-packages'
    if not site_packages.is_dir() or site_packages.resolve(strict=True) != site_packages:
        raise ValueError('dependency site-packages must be the exact interpreter-local directory')
    return {'venv': str(venv), 'site_packages': str(site_packages), 'python_version': version,
            'config_path': str(config), 'config_sha256': sha(raw),
            'scope': 'Existing dependencies only; site/.pth files are not executed; dependency bytes are not pinned.'}


def namespace_source_proof(root, head, name, module):
    """A namespace has no source blob; prove its sole declared search root."""
    spec = getattr(module, '__spec__', None)
    if (type(module) is not ModuleType or type(spec) is not ModuleSpec
            or spec.name != name or module.__name__ != name or module.__package__ != name
            or spec.origin is not None or spec.has_location or spec.cached is not None
            or type(spec.loader) is not NamespaceLoader or module.__loader__ is not spec.loader):
        raise ValueError('project module is not a genuine namespace package: ' + name)
    locations = spec.submodule_search_locations
    if (locations is None or getattr(module, '__path__', None) is not locations
            or getattr(spec.loader, '_path', None) is not locations):
        raise ValueError('namespace package spec/loader/search path disagree: ' + name)
    selected = list(locations)
    expected = root / 'src' / Path(*name.split('.'))
    if (selected != [str(expected)] or expected.resolve(strict=True) != expected
            or not expected.is_dir()):
        raise ValueError('namespace package search roots differ from the sole selected directory: '
                         + name + ': ' + repr(selected))
    relative = expected.relative_to(root).as_posix()
    if git(root, 'cat-file', '-t', head + ':' + relative).stdout != b'tree\n':
        raise ValueError('namespace package is not a committed source directory: ' + relative)
    return {'kind': 'namespace_package', 'path': str(expected), 'relative_path': relative,
            'origin': None, 'search_locations': selected,
            'loader': type(spec.loader).__module__ + '.' + type(spec.loader).__qualname__,
            'git_tree': git(root, 'rev-parse', head + ':' + relative).stdout.decode().strip()}


def loaded_source_proof(root, head):
    sources = {}
    for name, module in sorted(tuple(sys.modules.items())):
        if name != 'data_sheets_schema' and not name.startswith('data_sheets_schema.'):
            continue
        filename = getattr(module, '__file__', None)
        if filename is None:
            sources[name] = namespace_source_proof(root, head, name, module)
            continue
        path = Path(filename).resolve(strict=True)
        relative = path.relative_to(root).as_posix()
        if not path.is_relative_to(root / 'src') or path.suffix != '.py':
            raise ValueError('project module came from outside the selected source tree: ' + name)
        raw = path.read_bytes()
        committed = git(root, 'show', head + ':' + relative).stdout
        if raw != committed:
            raise ValueError('imported source is not the exact selected committed blob: ' + relative)
        sources[name] = {'path': str(path), 'relative_path': relative, 'sha256': sha(raw)}
    return sources


def worker(root, expected, dependency_site, dependency_config_sha256):
    if os.environ.get('PYTHONPATH') != str(root / 'src'):
        raise ValueError('child requires one explicit absolute checkout/src PYTHONPATH')
    if not sys.flags.no_site or not sys.flags.safe_path or not sys.dont_write_bytecode:
        raise ValueError('child requires -S -P -B isolation before imports')
    dependencies = dependency_environment(Path(sys.executable))
    if (dependencies['site_packages'] != dependency_site
            or dependencies['config_sha256'] != dependency_config_sha256
            or dependencies['python_version'] != f'{sys.version_info.major}.{sys.version_info.minor}'):
        raise ValueError('dependency directory/config differs from the actual child interpreter')
    if any(name == 'data_sheets_schema' or name.startswith('data_sheets_schema.') for name in sys.modules):
        raise ValueError('project code was imported before child source isolation')
    # Plain path append deliberately does not run site.addsitedir or .pth hooks.
    # The selected src remains the sole project namespace root; proof below
    # refuses any additional package leg exposed by installed dependencies.
    if dependency_site in sys.path:
        raise ValueError('dependency site-packages was already active before explicit isolation')
    sys.path.append(dependency_site)
    head = git(root, 'rev-parse', 'HEAD').stdout.decode().strip()
    if head != expected:
        raise ValueError('selected checkout HEAD differs from expected commit')
    if git(root, 'diff', '--quiet', '--no-ext-diff', '--no-textconv', 'HEAD', '--', 'src', allowed=(0, 1)).returncode:
        raise ValueError('selected checkout has uncommitted tracked source changes')
    cp = importlib.import_module('data_sheets_schema.receipt_completion_policy')
    completion = importlib.import_module('data_sheets_schema.receipt_completion')
    receipts = importlib.import_module('data_sheets_schema.receipts')
    api = importlib.import_module('data_sheets_schema.api_runner')
    source_before = Path(cp.__file__).resolve(strict=True)
    if source_before != root / 'src/data_sheets_schema/receipt_completion_policy.py':
        raise ValueError('receipt policy import selected another checkout')
    before = source_before.read_bytes()
    native = native_identity()
    result = {'repository': str(root), 'head': head,
        'source_tree': git(root, 'rev-parse', 'HEAD:src').stdout.decode().strip(),
        'python': sys.executable, 'python_version': sys.version,
        'dependency_environment': dependencies,
        'child_flags': {'no_site': sys.flags.no_site, 'safe_path': sys.flags.safe_path,
                        'dont_write_bytecode': sys.dont_write_bytecode},
        'pythonpath': os.environ['PYTHONPATH'], 'policy_source': str(source_before),
        'policy_source_sha256': sha(before), 'native_identity': native,
        'native_identity_dispatch': capture(lambda: cp._identity(native)), 'cases': []}
    for version in (1, 2, 3):
        prepared = capture(lambda: api_registration(cp, completion.policy_identity(version=version), version))
        row = {'api_receipt_version': version, 'registration_precondition': prepared}
        if prepared['outcome'] != 'return':
            row['scope'] = 'version/policy precondition unavailable; not the matching mixed-family baseline'
            result['cases'].append(row)
            continue
        registration, identity = prepared['value']
        spec = {'condition': registration['condition'], 'runtime': api.RUNTIME,
            'render_version': {1: 8, 2: 25, 3: 27}[version],
            'receipt_completion_version': version,
            'receipt_completion_policy_sha256': registration['runtime_policy_sha256'],
            'receipt_completion_registration': identity}
        if version == 1:
            row['positive_api_baseline'] = capture(lambda: cp.select_policy(spec))
            row['scope'] = 'complete passing API-v1 declaration; only receipt identity replaced'
        else:
            spec.update(shared_generation_version=version - 1, api_playbook_version=version)
            row['scope'] = 'minimal negative API axes; no shared registration created; later shared fields absent'
        bad = {**spec, 'receipt_completion_registration': native}
        row['mixed_selection'] = capture(lambda: cp.select_policy(bad))
        row['mixed_recorded_selection'] = capture(
            lambda: cp.select_policy(record={'prompts': {'request': {'spec': bad}}}))
        guarded = ForbiddenArtifact()
        row['public_block'] = capture(lambda: receipts.block_for(full_path=guarded,
            receipt=guarded, bundle=guarded, record_bundle_md5='0' * 32,
            expected=True, receipt_render_spec=bad))
        result['cases'].append(row)
    result['loaded_project_sources'] = loaded_source_proof(root, head)
    if source_before.read_bytes() != before or git(root, 'rev-parse', 'HEAD').stdout.decode().strip() != head:
        raise ValueError('source/HEAD changed during read-only probe')
    if git(root, 'diff', '--quiet', '--no-ext-diff', '--no-textconv', 'HEAD', '--', 'src', allowed=(0, 1)).returncode:
        raise ValueError('tracked source changed during read-only probe')
    result['source_unchanged'] = True
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--checkout', nargs=3, action='append',
                        metavar=('LABEL', 'ABSOLUTE_PATH', 'EXPECTED_FULL_COMMIT'))
    parser.add_argument('--python', default=sys.executable)
    parser.add_argument('--child', action='store_true', help=argparse.SUPPRESS)
    parser.add_argument('--repository', help=argparse.SUPPRESS)
    parser.add_argument('--expect-head', help=argparse.SUPPRESS)
    parser.add_argument('--dependency-site', help=argparse.SUPPRESS)
    parser.add_argument('--dependency-config-sha256', help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.child:
        root = Path(args.repository)
        if not root.is_absolute() or not re.fullmatch('[0-9a-f]{40}', args.expect_head or ''):
            parser.error('child requires an absolute checkout and full commit')
        print(json.dumps(worker(root.resolve(strict=True), args.expect_head,
                                args.dependency_site, args.dependency_config_sha256), sort_keys=True))
        return
    if (not args.checkout or args.repository or args.expect_head
            or args.dependency_site or args.dependency_config_sha256):
        parser.error('supply one or more --checkout LABEL ABSOLUTE_PATH EXPECTED_FULL_COMMIT')
    interpreter = Path(args.python)
    if not interpreter.is_absolute() or not interpreter.is_file():
        parser.error('--python must name the existing absolute Python interpreter')
    dependencies = dependency_environment(interpreter)
    script = Path(__file__).resolve(strict=True)
    outputs = []
    for label, location, expected in args.checkout:
        root = Path(location)
        if not root.is_absolute() or not re.fullmatch('[0-9a-f]{40}', expected):
            parser.error('each checkout needs an absolute path and full commit')
        root = root.resolve(strict=True)
        env = {key: os.environ[key] for key in ('PATH', 'HOME', 'LANG', 'LC_ALL', 'TMPDIR') if key in os.environ}
        env.update(PYTHONPATH=str(root / 'src'), PYTHONDONTWRITEBYTECODE='1', PYTHONNOUSERSITE='1',
                   GIT_OPTIONAL_LOCKS='0', GIT_NO_LAZY_FETCH='1')
        command = [str(interpreter), '-S', '-P', '-B', str(script), '--child',
            '--repository', str(root), '--expect-head', expected,
            '--dependency-site', dependencies['site_packages'],
            '--dependency-config-sha256', dependencies['config_sha256']]
        process = subprocess.run(command, cwd=root, env=env,
            capture_output=True, text=True, timeout=120)
        if process.returncode:
            outputs.append({'label': label, 'repository': str(root), 'expected_head': expected,
                            'command': command, 'probe_error': process.stderr, 'exit_code': process.returncode})
        else:
            outputs.append({'label': label, 'command': command, 'result': json.loads(process.stdout)})
    print(json.dumps({'format': 'native_n1b_receipt_policy_probe_v1',
        'scope': 'offline_static_finding_reproduction_not_suite_failure_count',
        'dependency_environment': dependencies,
        'helper': str(script), 'helper_sha256': sha(script.read_bytes()), 'checkouts': outputs},
        sort_keys=True, indent=2))
    if any('probe_error' in row for row in outputs):
        raise SystemExit(2)


if __name__ == '__main__':
    main()
