#!/usr/bin/env python3
"""Plan/run one unchanged-source G2 metadata-refusal diagnostic, 2026-11-14.

Input: exact incomplete-retention [False] test, reviewed source checkout and
base runner inventory helpers. Output: diagnostic.* files only in exclusive
scratch-g2-20261114/retention-stability-diagnostic. --plan reads/prints only;
--run executes exactly one selected test with four-worker CI scheduling and
--showlocals. No monkeypatch/plugin or project import in this helper. This is
diagnostic provenance, never whole-file acceptance or a weakened stable guard.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

sys.dont_write_bytecode = True
from run_g2_checks_20261114 import ROOT, OUT, PYTHON, cases, python_inventory

PRODUCER = Path(__file__).resolve()
BASE = PRODUCER.with_name('run_g2_checks_20261114.py')
DIRECTORY = OUT / 'retention-stability-diagnostic'
NODE = ('tests/test_native_incomplete_retention.py::'
        'test_public_failed_attempt_retains_records_and_reads_back_exactly[False]')
SOURCE_SCOPE = ('src', 'tests', 'notes/matched_cborg_2026-09-13', 'pyproject.toml',
                'poetry.lock', 'conftest.py', '.github/workflows/main.yaml')
SOURCE_FILES = ('tests/test_native_incomplete_retention.py',
                'tests/test_native_shared_execution.py', 'tests/native_shared_fixture.py',
                'src/data_sheets_schema/native_shared_selection.py',
                'src/data_sheets_schema/schema_snapshot.py',
                'src/data_sheets_schema/schema_view.py')
SCHEDULE = ['-n', '4', '--dist', 'load', '--maxschedchunk=1']
NAMES = {'command': 'diagnostic.command.json', 'log': 'diagnostic.pytest.log',
         'junit': 'diagnostic.junit.xml', 'outcome': 'diagnostic.outcome.json'}


def pin(path):
    raw = path.read_bytes()
    if not raw:
        raise ValueError('empty provenance input: ' + str(path))
    return {'path': str(path), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def save_json(path, value):
    raw = (json.dumps(value, indent=2, sort_keys=True) + '\n').encode()
    with path.open('xb') as stream:
        stream.write(raw)
    if path.read_bytes() != raw:
        raise ValueError('diagnostic provenance readback differs')


def prepare():
    if ROOT.resolve(strict=True) != ROOT or OUT.resolve(strict=True) != OUT:
        raise ValueError('checkout and scratch root must be physical paths')
    if os.path.lexists(DIRECTORY):
        raise ValueError('preserve prior diagnostic directory: ' + str(DIRECTORY))
    if not PYTHON.is_file():
        raise ValueError('assigned interpreter is missing')
    # Extra targets/options must not enter this exact one-unit diagnostic via
    # an inherited pytest setting. Installed default plugins remain unchanged.
    if any(os.environ.get(key) for key in ('PYTEST_ADDOPTS', 'PYTEST_PLUGINS')):
        raise ValueError('diagnostic requires no inherited PYTEST_ADDOPTS or PYTEST_PLUGINS')
    inventory = python_inventory(ROOT, [NODE])
    subprocess.check_call(['git', 'diff', '--exit-code', 'HEAD', '--',
                           *SOURCE_SCOPE, *inventory['selected_paths']], cwd=ROOT)
    environment = {key: value for key, value in os.environ.items()
        if not (key.endswith('_API_KEY') or key in (
            'ANTHROPIC_AUTH_TOKEN', 'CLAUDE_CODE_OAUTH_TOKEN',
            'ANTHROPIC_BASE_URL', 'OPENAI_BASE_URL'))}
    environment.update(PYTHONPATH=str(ROOT / 'src'), PYTHONDONTWRITEBYTECODE='1',
                       PYTHONPYCACHEPREFIX=str(DIRECTORY / 'pycache'), TMPDIR=str(DIRECTORY))
    command = [str(PYTHON), '-m', 'pytest', '-q', '-p', 'no:cacheprovider',
               NODE, '--showlocals', *SCHEDULE,
               '--basetemp=' + str(DIRECTORY / 'cases'),
               '--junitxml=' + str(DIRECTORY / NAMES['junit'])]
    record = {
        'kind': 'g2_retention_stability_diagnostic', 'diagnostic_only': True,
        'acceptance_evidence': False, 'selected_node': NODE, 'command': command,
        'cwd': str(ROOT), 'destination': str(DIRECTORY), 'output_names': NAMES,
        'environment': {key: environment[key] for key in (
            'PYTHONPATH', 'PYTHONDONTWRITEBYTECODE', 'PYTHONPYCACHEPREFIX', 'TMPDIR')},
        'credential_stripping': 'Inherited *_API_KEY and explicit provider auth/endpoint variables are removed; no values are logged.',
        'pytest_environment_overrides_absent': True,
        'head': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        'status_before': subprocess.check_output(['git', 'status', '--short'], cwd=ROOT, text=True),
        'source_scope': list(SOURCE_SCOPE), 'source_inventory': inventory,
        'source_pins': [pin(ROOT / name) for name in SOURCE_FILES],
        'producer': pin(PRODUCER), 'base_runner': pin(BASE), 'scheduling': SCHEDULE,
        'limitations': [
            'Exactly one test parameter is selected; four workers preserve the failed cohort scheduling mode. There is no fanout or follow-on batch.',
            'Only --showlocals is added to test behavior. No test/plugin monkeypatch, assertion, stable/refusal guard, source, clock or limit is changed.',
            'A traceback can retain stable() locals such as path and expected. A current stat cannot recover the exact observed tuple from the original failure.',
            'Diagnostic filenames intentionally prevent automatic acceptance-cohort discovery. A pass does not establish whole-file coverage or erase the original failures.']}
    return record, environment


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument('--plan', action='store_true', help='read/print the exact plan without creating output')
    action.add_argument('--run', action='store_true', help='run the one diagnostic only after separate review')
    args = parser.parse_args()
    record, environment = prepare()
    if args.plan:
        print(json.dumps({'action': 'plan', **record}, indent=2))
        return 0
    DIRECTORY.mkdir(exist_ok=False)
    save_json(DIRECTORY / NAMES['command'], record)
    started = time.monotonic()
    with (DIRECTORY / NAMES['log']).open('xb') as log:
        code = subprocess.call(record['command'], cwd=ROOT, env=environment,
                               stdout=log, stderr=subprocess.STDOUT)
    junit = DIRECTORY / NAMES['junit']
    counts, count_error = None, None
    if junit.is_file():
        try:
            counts = cases(junit)
        except Exception as error:
            count_error = type(error).__name__
    result = {
        'kind': record['kind'], 'diagnostic_only': True, 'acceptance_evidence': False,
        'selected_node': NODE, 'returncode': code, 'seconds': time.monotonic() - started,
        'normal_pytest_completion': code in (0, 1), 'counts': counts,
        'case_count_parse_error': count_error,
        'one_selected_case_reported': counts is not None and counts['total'] == 1,
        'command_evidence': pin(DIRECTORY / NAMES['command']),
        'producer': record['producer'], 'base_runner': record['base_runner'],
        'head': record['head'], 'source_pins': record['source_pins'],
        'artifacts': [pin(path) for path in (DIRECTORY / NAMES['log'], junit)
                      if path.is_file() and path.stat().st_size],
        'limitation': 'Normal completion records process status, not acceptance. No current stat reconstructs the exact original mismatch, and this single diagnostic is not whole-file verification.'}
    save_json(DIRECTORY / NAMES['outcome'], result)
    print(json.dumps({'outcome': pin(DIRECTORY / NAMES['outcome']),
                      'returncode': code, 'counts': counts, 'diagnostic_only': True}, indent=2))
    return code


if __name__ == '__main__':
    raise SystemExit(main())
