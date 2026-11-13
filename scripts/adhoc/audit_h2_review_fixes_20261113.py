#!/usr/bin/env python3
"""Read-only review-fix audit, 2026-11-13; source/clock/test evidence for handoff.
Inputs three branches, CI export artifacts and local Apple SDK; output JSON.
No authority edits, host probes, network, native binary or provider calls.
"""
from pathlib import Path
import ast
from collections import Counter
import hashlib
import json
import subprocess
import xml.etree.ElementTree as ET

R = Path(__file__).resolve().parents[2]; E = R.parent
B = Path.home() / 'agent-work/data-sheets-schema/helper2-review-fixes-20261113'
candidate = 'f7f8e8bff6ea14006957d8631f66346d91bcddcd'
protected = ['src/data_sheets_schema/shared_generation.py', 'src/data_sheets_schema/api_runner.py',
    'src/download/prompts/canonical_hashes.yaml', 'tests/utils/run_spec_boundary_contracts.json',
    'src/data_sheets_schema/native_subscription_guard.py']
def git(root, *args):
    return subprocess.check_output(['git', *args], cwd=root)
def pin(path):
    raw = path.read_bytes()
    return {'path': str(path), 'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw)}

branches = {}
for name, folder in [('cache', 'codex-native-helper-cache-home-20261112'),
                     ('limits', 'codex-native-production-run-limits-20261112'),
                     ('power', 'codex-native-host-power-20261113')]:
    root = E / folder
    protection = {path: (root / path).read_bytes() == git(root, 'show', candidate + ':' + path) for path in protected}
    assert all(protection.values())
    changes = git(root, 'diff', '--name-only', candidate, 'HEAD').decode().splitlines()
    for path in changes:
        if path.endswith('.py') and (root / path).exists():
            ast.parse((root / path).read_text(), filename=path)
    branches[name] = {'root': str(root), 'branch': git(root, 'branch', '--show-current').decode().strip(),
        'head': git(root, 'rev-parse', 'HEAD').decode().strip(),
        'candidate_is_ancestor': subprocess.run(['git', 'merge-base', '--is-ancestor', candidate, 'HEAD'], cwd=root).returncode == 0,
        'protected_equal_candidate': protection, 'dirty': git(root, 'status', '--porcelain').decode(),
        'diff_check': subprocess.run(['git', 'diff', '--check', candidate, 'HEAD'], cwd=root, capture_output=True, text=True).stdout,
        'commits': git(root, 'log', '--format=%H %s', candidate + '..HEAD').decode().splitlines()}
    paths = ['scripts/adhoc/run_cache_gaps_tests_20261113.py', 'scripts/adhoc/reconcile_cache_ci_12_shards_20261113.py']
    if name == 'power': paths.append('scripts/adhoc/run_host_power_tests_20261113.py')
    if name != 'limits':
        found = subprocess.run(['rg', '--no-ignore', '--hidden', '-n', r'/Users/[^/]+|/home/[^/]+', *paths],
                               cwd=root, capture_output=True, text=True)
        branches[name]['personal_path_search'] = {'includes_hidden_ignored': True, 'paths': paths,
            'returncode': found.returncode, 'matches': found.stdout}
        assert found.returncode == 1 and not found.stdout

cohorts = {}
for folder in sorted((B / 'tests').iterdir()):
    if not (folder / 'outcome.json').exists(): continue
    data = {'outcome': json.loads((folder / 'outcome.json').read_bytes()),
            'outcome_pin': pin(folder / 'outcome.json'), 'plan': json.loads((folder / 'plan.json').read_bytes())}
    if (folder / 'pytest.xml').exists():
        by_file, failed = {}, []
        for case in ET.parse(folder / 'pytest.xml').iter('testcase'):
            status = next((tag for tag in ('failure', 'error', 'skipped') if case.find(tag) is not None), 'passed')
            by_file.setdefault(case.get('classname'), Counter())[status] += 1
            if status in ('failure', 'error'):
                failure = case.find(status)
                failed.append({'class': case.get('classname'), 'name': case.get('name'), 'status': status,
                    'message': failure.get('message'), 'controller_pin_refusal': 'frozen native controller bytes changed' in (failure.text or '')})
        data.update(counts_by_file=by_file, failures=failed, junit_pin=pin(folder / 'pytest.xml'))
    cohorts[folder.name] = data

scanner_comparison = {}
for name in ('scanner', 'scanner-unaffected'):
    path = B / 'tests' / name / 'scanner.md'
    if path.exists():
        section = path.read_text().split('## gc_project violations\n', 1)[1].split('\n## ', 1)[0]
        scanner_comparison[name] = {'report': pin(path), 'violation_rows': [line for line in section.splitlines() if line.startswith('| `')]}
if len(scanner_comparison) == 2:
    scanner_comparison['identical_violation_rows'] = scanner_comparison['scanner']['violation_rows'] == scanner_comparison['scanner-unaffected']['violation_rows']

header = Path('/Library/Developer/CommandLineTools/SDKs/MacOSX.sdk/usr/include/mach/mach_time.h')
lines = header.read_text().splitlines()
clock = {'interface': 'mach_continuous_time with mach_timebase_info integer conversion',
    'documentation': pin(header), 'excerpt': [{'line': i, 'text': line} for i, line in enumerate(lines, 1) if 58 <= i <= 62],
    'source': pin(E / 'codex-native-host-power-20261113/src/data_sheets_schema/native_elapsed.py'),
    'linux_interface': 'clock_gettime_ns(CLOCK_BOOTTIME)', 'fallback': 'none; unavailable clock refuses'}
out = R / 'notes/development_efficiency_20261111/handoffs/codex-h2-review-fixes-audit-20261113.json'
out.write_text(json.dumps({'candidate': candidate, 'branches': branches, 'cohorts': cohorts, 'scanner_comparison': scanner_comparison,
    'clock': clock, 'scope': 'offline only; no pin changes, native execution or public completion'}, indent=2).replace(chr(64), '\\u0040') + '\n')
print(json.dumps(pin(out)))
