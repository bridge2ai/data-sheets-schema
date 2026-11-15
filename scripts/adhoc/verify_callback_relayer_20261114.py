"""Issue 6233, 2026-11-14: persist focused relayer validation commands/results.

Inputs: current checkout and assigned scratch. Outputs: logs, JUnit and JSON.
Runs one real two-worker canary before the affected native and scanner suites.
"""
import json
from pathlib import Path
import subprocess
import sys
import xml.etree.ElementTree as ET


NATIVE = (
    'callback_prefix', 'callback_preloading', 'callback_io', 'capture_split',
    'capture_integration', 'stages', 'saved_advance', 'live_capture',
    'observations', 'streams', 'evidence', 'saved_pool_bound', 'read_repeat',
    'seal_identity', 'receipt_delivery', 'receipt_readers', 'initial_receipts',
    'permissions', 'owner_delivery', 'consumer_census', 'gates', 'results',
    'publication', 'provenance', 'render',
    'controller', 'phase', 'contract', 'record_contract', 'current',
)
SCANNER = (
    'tests/test_native_u1_scanner_contracts.py::test_native_complete_response_roster_derives',
    'tests/test_native_u3l_review_fixtures.py',
    'tests/test_generation_specificity_skill.py::TestApiMeaning',
)


def main():
    root = Path(sys.argv[1])
    root.mkdir(parents=True, exist_ok=True)
    reports = []
    batches = [
        ('suite-canary', ['tests/test_native_shared_callback_prefix.py::test_valid_extension_matches_full_replay_and_only_checks_suffix']),
        ('native', ['tests/test_native_shared_' + name + '.py' for name in NATIVE]),
        ('scanner', list(SCANNER)),
    ]
    for name, nodes in batches:
        command = [sys.executable, '-m', 'pytest', *nodes, '-q', '-n', '2',
            '-p', 'no:cacheprovider', '--basetemp=' + str(root / (name + '-cases')),
            '--junitxml=' + str(root / (name + '.xml'))]
        (root / (name + '-command.json')).write_text(json.dumps(command, indent=2) + '\n')
        with (root / (name + '.log')).open('w') as output:
            result = subprocess.run(command, stdout=output, stderr=subprocess.STDOUT)
        report = root / (name + '.xml')
        assert report.is_file() and report.stat().st_size
        suites = ET.parse(report).getroot().findall('testsuite')
        row = {'name': name, 'command': command, 'exit_code': result.returncode,
            'counts': {key: sum(int(suite.get(key, '0')) for suite in suites)
                       for key in ('tests', 'failures', 'errors', 'skipped')}}
        reports.append(row)
        (root / 'validation.json').write_text(json.dumps(reports, indent=2) + '\n')
        print(json.dumps(row), flush=True)
        if name == 'suite-canary' and result.returncode:
            return result.returncode
    return int(any(row['exit_code'] for row in reports))


if __name__ == '__main__':
    raise SystemExit(main())
