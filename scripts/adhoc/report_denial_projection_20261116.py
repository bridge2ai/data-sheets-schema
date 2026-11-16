"""Report the denial projection continuation for the Claude lead, 2026-11-16.

Inputs: saved pytest XML/logs, read-only pin proposal, and current git commit.
Outputs: evidence JSON in task scratch and a new top section in the handoff.
Serves the denial_problems assignment for draft PR 5968; makes no remote writes.
"""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT.parent
SCRATCH = BASE / 'scratch-d156-fix-20261116/denial-projection'
HANDOFF = BASE / 'codex-development-efficiency-20261111/notes/development_efficiency_20261111/handoffs/codex-d156-fix-20261116.md'
PYTHON = BASE.parent / 'data-sheets-schema/.venv/bin/python'
PIN_TOOL = BASE.parent / 'data-sheets-schema/scripts/adhoc/compute_pin_chain_20261115.py'


def main():
    if '--namespace-only' in sys.argv:
        import data_sheets_schema
        from data_sheets_schema import native_environment_manifest as environment
        value = {'package_roots': [str(Path(path).resolve()) for path in data_sheets_schema.__path__],
                 'expected_root': str(environment.ROOT / 'src/data_sheets_schema')}
        (SCRATCH / 'namespace.json').write_text(json.dumps(value, indent=2) + '\n')
        print(json.dumps(value, indent=2))
        return
    head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    pins = json.loads((SCRATCH / 'pins.json').read_text())
    runs = {}
    for name in ('canary', 'canary2', 'focused', 'controls', 'controls-canary', 'controls-retry'):
        path = SCRATCH / (name + '.xml')
        assert path.is_file() and path.stat().st_size
        assert (SCRATCH / (name + '.log')).is_file()
        cases = ET.parse(path).findall('.//testcase')
        failed = sum(case.find('failure') is not None for case in cases)
        errors = sum(case.find('error') is not None for case in cases)
        skipped = sum(case.find('skipped') is not None for case in cases)
        runs[name] = {'passed': len(cases) - failed - errors - skipped,
                      'failed': failed, 'errors': errors, 'skipped': skipped,
                      'xml': str(path), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}
    assert all(runs[name]['failed'] == runs[name]['errors'] == 0
               for name in ('canary2', 'controls-canary', 'controls-retry'))
    namespace = json.loads((SCRATCH / 'namespace.json').read_text())
    ledger = {'commit': head, 'runs': runs, 'pin_proposals': pins['proposed_edits'],
              'pin_failures': pins['failures'], 'protected_files_ok': pins['protected_files_ok'],
              'manual_review_actions': pins['manual_review_actions'], 'namespace': namespace}
    ledger_path = SCRATCH / 'evidence.json'
    ledger_path.write_text(json.dumps(ledger, indent=2) + '\n')
    for path in (PYTHON, PIN_TOOL, HANDOFF, Path(__file__), ledger_path):
        assert path.is_file(), path
    lines = [
        '# Denial projection continuation: fixed; shared replay setup limitation retained', '',
        'The pure denial_problems helper is now exposed through the exact native execution capability projection. The only production change adds that member. A saved transcript containing a prescribed Bash denial reaches the real saved validator through the attested projection and returns a checked, failing additional-gate verdict with the expected denial diagnostic.', '',
        'Purity review: the historical function is a list comprehension over caller-supplied classifications, using dictionary reads and string formatting. It performs no I/O, mutation, process action or external helper call. Its source is unchanged.', '',
        'Commit: ' + head + '. Branch: codex/d156-fix-20261116.', '',
        'The first regression canary failed before replay because legacy fixture imports conflicted with the attested loader. The test now temporarily isolates those aliases using the established registration-fixture pattern. The second canary passed with nonempty XML evidence before broader tests ran. It proves saved-denial replay through the actual projection, not public execution or launch readiness.', '',
    ]
    for name, row in runs.items():
        lines.append('- ' + name + ': ' + ', '.join(str(row[key]) + ' ' + key
                     for key in ('passed', 'failed', 'errors', 'skipped')) + '. Evidence: ' + row['xml'])
    lines += ['',
        'All test invocations used PYTHONPATH=$PWD/src and ' + str(PYTHON) + ' -m pytest -q -n 3, with basetemp and junitxml under ' + str(SCRATCH) + '.',
        'The initial native-controls invocation exposed missing historical imports and sandbox-denied loopback binds. The retry and its proxy canary extend PYTHONPATH with $PWD/notes/matched_cborg_2026-09-13 and $PWD/notes/matched_cborg_2026-09-13/native_controls and run with approved sandbox escalation. The canary is test_native_proxy.py::test_finite_reported_cost_retains_exact_decimal_text_only[0]; its nonempty XML proves the mock proxy can bind and finish. The original failed run is retained and is not a product-validation result.',
        'Focused selections: tests/test_native_u3d_round9_capabilities.py, tests/test_native_attribution_results.py, tests/test_native_shared_results.py, tests/test_native_shared_saved_pool_bound.py, tests/test_native_shared_saved_advance.py. Controls selection: notes/matched_cborg_2026-09-13/native_controls. Canary selection: tests/test_native_attribution_results.py::test_recorded_denial_replays_through_execution_projection.', '',
        'The focused run has setup errors in shared saved-replay fixtures: own distribution exclusion requires the exact pinned project namespace. They occur in environment-manifest generation before saved replay. The required primary interpreter exposes these package roots: ' + json.dumps(namespace['package_roots']) + '; expected: ' + namespace['expected_root'] + '. The capability and attribution-results tests, including the new projection regression, pass. The affected shared-replay tests are not verified; their assertions and production environment check remain unchanged. This separate environment finding is retained for the lead issue ledger.',
        'Namespace diagnostic command: PYTHONPATH=$PWD/src ' + str(PYTHON) + ' ' + str(Path(__file__).resolve()) + ' --namespace-only. Output: ' + str(SCRATCH / 'namespace.json') + '.', '',
        'Pin command: ' + str(PYTHON) + ' ' + str(PIN_TOOL) + ' --root ' + str(ROOT) + ' --propose. Saved output: ' + str(SCRATCH / 'pins.json') + '.',
        'Proposed pin edits: ' + json.dumps(pins['proposed_edits']) + '; failures: ' + json.dumps(pins['failures']) + '; protected files intact: ' + str(pins['protected_files_ok']) + '. Existing scanner tool-asset refresh notices remain for the lead; no pin was edited.', '',
        'Read-only adversarial review found no additional defect. The regression replaces the captured legacy control carrier with the actual scoped capability projection and asserts the denial-specific failure, so an unrelated failing verdict cannot satisfy it. The initial fixture-origin failure and its repair are retained above for the lead issue ledger. No GitHub write is permitted in this helper role.', '',
        'No public case, provider call or native binary call was run. No push or pull request was made; the lead owns publication and integration. Issues 4400 and 4550 remain deferred under the assignment ruling.', '',
        'Evidence ledger: ' + str(ledger_path) + '. Reporting command: ' + str(PYTHON) + ' ' + str(Path(__file__).resolve()) + '.', '', '---', '',
    ]
    section = '\n'.join(lines)
    assert chr(64) not in section
    old = HANDOFF.read_text()
    assert chr(64) not in old
    HANDOFF.write_text(section + old)
    print(json.dumps(ledger, indent=2))
    print(str(HANDOFF))
    print(hashlib.sha256(HANDOFF.read_bytes()).hexdigest())


if __name__ == '__main__':
    main()
