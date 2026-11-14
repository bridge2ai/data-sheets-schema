#!/usr/bin/env python3
"""Save the resumable G2 final-verification state, 2026-11-14.

Inputs: assigned Git checkout, all direct saved cohort command/outcome/JUnit/log
records, sealed H2 handoffs, current report/closure producers and review ledgers.
Output: exclusive scratch-g2-20261114/checkpoints/current-g2-<UTC>.json.
No project imports, tests, probes, signals, source edits, commits or publishing.
"""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT.parent / 'scratch-g2-20261114'
REPORTS = ROOT.parent / 'codex-development-efficiency-20261111/notes/development_efficiency_20261111/handoffs'
HEAD = '2070a2116ceb5b1f5dd9a870c803ee3311d298b9'
ACTIVE = 'legacy-full-serial'
ACTIVE_SESSION = 56676
CANARY_NODE = 'tests/test_native_execution.py::test_actual_closed_consumer_real_helpers_complete[no_correction]'
LEGACY = ['tests/test_native_execution.py', 'tests/test_native_receipt_origin_reporting.py']
H2_HASHES = {
    'codex-h2-integration-fixes-20261113.md': 'c0036c97463b75f6869d5f6004b55ae6b6aace5cb8bc46890d12334d25575b20',
    'codex-h2-integration-fixes-20261113.json': 'c4a1b52fb3e552b4c5b6677cd4753cb3d4db37b27664539c20a48d31dac0eb68',
}


def pin(path):
    path = Path(path)
    before = path.stat()
    raw = path.read_bytes()
    after = path.stat()
    assert (before.st_size, before.st_mtime_ns) == (after.st_size, after.st_mtime_ns), 'file changed during checkpoint read'
    return {'path': str(path), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def read(path):
    return json.loads(Path(path).read_bytes())


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT, text=True).strip()


def cohort(directory):
    evidence = {name: pin(directory / name) if (directory / name).is_file() else None
                for name in ('command.json', 'outcome.json', 'pytest.xml', 'pytest.log')}
    command = read(directory / 'command.json') if evidence['command.json'] else None
    outcome = read(directory / 'outcome.json') if evidence['outcome.json'] else None
    counts, problems = None, []
    if evidence['pytest.xml']:
        try:
            cases = list(ET.parse(directory / 'pytest.xml').iter('testcase'))
            counts = {'total': len(cases), 'failed': sum(node.find('failure') is not None for node in cases),
                      'error': sum(node.find('error') is not None for node in cases),
                      'skipped': sum(node.find('skipped') is not None for node in cases)}
        except ET.ParseError:
            problems.append('JUnit is incomplete or malformed at checkpoint time')
    summary = None
    if evidence['pytest.log']:
        lines = (directory / 'pytest.log').read_text(errors='replace').splitlines()
        summaries = [line for line in lines if re.search(r'\b\d+ (passed|failed|errors?|skipped)\b', line)
                     and re.search(r'\bin [\d.]+s\b', line)]
        summary = summaries[-1] if summaries else None
    if outcome is None:
        status = 'running; outcome not saved' if directory.name == ACTIVE else 'incomplete; outcome not saved'
    elif outcome.get('returncode') == 2:
        status = 'interrupted; incomplete and ineligible as completed test proof'
    elif outcome.get('returncode') != 0:
        status = 'failed; zero-exit rerun proof is still required'
    elif counts is None or outcome.get('counts') != counts or counts['failed'] or counts['error']:
        status = 'incomplete or inconsistent saved evidence'
    else:
        status = 'completed command with exit zero; issue closure remains separately gated'
    invocation_directory = None
    if command:
        options = [item.split('=', 1)[1] for item in command.get('command', []) if item.startswith('--basetemp=')]
        if len(options) == 1:
            invocation_directory = str(Path(options[0]).parent)
    return {'name': directory.name, 'status': status, 'evidence': evidence,
            'kind': 'saved evidence copy' if invocation_directory and invocation_directory != str(directory) else 'cohort invocation',
            'invocation_directory': invocation_directory, 'command': command, 'outcome': outcome,
            'raw_junit_counts': counts, 'completed_log_summary': summary, 'problems': problems,
            'recorded_source_head': command.get('head') if command else None,
            'same_recorded_head_as_checkpoint': command.get('head') == HEAD if command else False,
            'limit': 'Raw clean JUnit entries from interrupted or failed sessions do not establish individually completed tests or full-file success.'}


def main():
    actual_head = git('rev-parse', 'HEAD')
    assert actual_head == HEAD, 'source HEAD changed; revise the checkpoint plan explicitly'
    active_command = read(OUT / ACTIVE / 'command.json')
    assert all(name in active_command['command'] for name in LEGACY) and '-n' not in active_command['command']
    assert active_command['cwd'] == str(ROOT) and active_command['head'] == HEAD
    canary_outcome = read(OUT / 'legacy-serial-canary/outcome.json')
    assert canary_outcome['returncode'] == 0 and canary_outcome['counts'] == {
        'total': 1, 'failed': 0, 'error': 0, 'skipped': 0}
    canary_evidence = OUT / 'legacy-serial-canary/cases/test_actual_closed_consumer_re0/native/native-evidence'
    canary_final = pin(canary_evidence / 'final.json')
    assert canary_final['sha256'] == '1b3003efc3337581281fd67d99c267133e24ddcb1004e56700a1692a397f3a3b'
    final_value = read(canary_evidence / 'final.json')
    assert final_value['runtime_gates_passed'] is True and final_value['state'] == 'completed_pending_independent_review'
    component_files = read(OUT / 'final-components/command.json')['source_inventory']['selected_paths']
    other_components = [name for name in component_files if name not in LEGACY]
    engine_files = read(OUT / 'engine-admission/command.json')['source_inventory']['selected_paths']
    engine_files = [name for name in engine_files if name not in {
        'tests/test_native_attempt_deadline.py', 'tests/test_native_admission_timer.py',
        'tests/test_native_pre_dispatch_timing.py'}]
    assert len(other_components) == 16 and len(engine_files) == 15
    sealed = []
    for name, digest in H2_HASHES.items():
        item = pin(REPORTS / name)
        assert item['sha256'] == digest, 'sealed H2 handoff changed'
        sealed.append(item)
    assert read(REPORTS / 'codex-h2-integration-fixes-20261113.json')['head'] == '64fa2b4b7ac2d1b0767e2d89a5ca4109c945229b'
    cohorts = [cohort(path) for path in sorted(OUT.iterdir()) if path.is_dir()
               and any((path / name).is_file() for name in ('command.json', 'outcome.json'))]
    helper_paths = [ROOT / 'scripts/adhoc' / name for name in (
        'report_g2_launch_fixes_20261114.py', 'record_g2_final_review_20261114.py',
        'run_g2_checks_20261114.py', 'verify_g2_report_legacy_findings_20261114.py')]
    evidence_paths = [OUT / name for name in (
        'review-legacy-component-failures-v2.json',
        'report-closure-pin-verification-after-legacy-findings/result.json',
        'report-closure-pin-verification-after-legacy-findings/required-files.json',
        'proposal-6207-after-6217/proposal.json', 'review-6207-after-6217.json',
        'review-6217-f3-withdrawn-frozen.json',
        'proposal-6217-implementation/review-6217-superseding.json',
        'engine-admission-interruption-20261114/cleanup-1794630386052545000.json')]
    now = datetime.now(timezone.utc)
    record = {'not_final_handoff': True, 'recorded_at': now.isoformat(),
        'head': actual_head, 'branch': git('branch', '--show-current'),
        'working_tree_status': git('status', '--short'),
        'source_and_test_status': git('status', '--short', '--', 'src', 'tests'),
        'source_status': '6217 is implemented at this HEAD; no issue is declared fixed by this checkpoint before required full proof.',
        'active_cohort': {'name': ACTIVE, 'parent_reported_session': ACTIVE_SESSION,
            'workers': 0, 'exact_files': LEGACY, 'command': active_command,
            'evidence': pin(OUT / ACTIVE / 'command.json'),
            'outcome_present_at_checkpoint': (OUT / ACTIVE / 'outcome.json').is_file(),
            'instruction': 'Resume/poll the existing session; do not launch a duplicate. If its outcome now exists, read it before selecting the next step.'},
        'cohorts': cohorts, 'sealed_h2_handoffs': sealed,
        'completed_serial_canary': {'node': CANARY_NODE, 'outcome': canary_outcome,
            'outcome_evidence': pin(OUT / 'legacy-serial-canary/outcome.json'),
            'final': canary_final, 'published': pin(canary_evidence / 'published.json'),
            'state': final_value['state'], 'runtime_gates_passed': True,
            'limit': 'One serial node passed without source/limit changes; this establishes no timing cause and does not replace whole-file reruns.'},
        'producer_snapshots': [pin(path) for path in helper_paths],
        'producer_hash_scope': 'Point-in-time observed hashes; the report/closure helpers may be under authorized revision. Revalidate their final pure proof after changes.',
        'review_and_proposal_evidence': [pin(path) for path in evidence_paths if path.is_file()],
        'remaining_work': [
            {'order': 1, 'task': 'Await the existing complete legacy-file serial cohort, authorized after the successful no_correction serial canary; preserve any failure and triage without weakening assertions.',
             'session': ACTIVE_SESSION, 'workers': 0, 'files': LEGACY},
            {'order': 2, 'task': 'Rerun the other sixteen component files in a fresh cohort for zero-exit proof; the original failed final-components cohort remains retained.',
             'workers': 4, 'files': other_components},
            {'order': 3, 'task': 'Complete both full publication-signal and attempt-deadline files; canary nodes do not prove full-file coverage.',
             'files': ['tests/test_native_publication_signals.py', 'tests/test_native_attempt_deadline.py']},
            {'order': 4, 'task': 'Run the fifteen required engine-dependent files on current source in a fresh coordinated cohort.', 'files': engine_files},
            {'order': 5, 'task': 'When all cohorts are idle, review and commit provenance/report/closure/checkpoint helpers; do not commit during source-bound test execution.'},
            {'order': 6, 'task': 'Run final source/protected/pin audit at final HEAD; reconcile each finding from actual clean full-file proof, refresh reporter proof if its source changed, then execute closure and answer-first G2 handoff producers.'}],
        'open_findings': {'ledger': str(OUT / 'review-legacy-component-failures-v2.json'),
            'ids': ['G2-REVIEW-LEGACY-F1', 'G2-REVIEW-LEGACY-F2'],
            'requirement': 'Both exact failed/error nodes and their entire files require clean reruns. A serial canary alone closes neither finding.',
            'baseline_reproduction_established': False, 'internal_or_timing_cause_established': False,
            'wording': 'If clean reruns succeed, retain the original failure and undetermined cause; do not call it a code correction.'},
        'proposal_status': {'6207': 'unapplied refreshed proposal and static review, based on current 6217 source; historical proposal/review retained',
                            '6225': 'not fixed; retained coverage/evidence proposal',
                            '6217': 'implemented; old deferral superseded, full verification remains required; F3 false finding is withdrawn with frozen evidence'},
        'constraints': [
            'Only the assigned execution worktree/branch. No source/test changes are authorized during active cohorts; helper-only bookkeeping is allowed.',
            'No real native/provider/model/auth/capture/host-probe calls, CPU-monitoring diagnostics, controller/prompt pin rotation, guard-v1 edits, protected-file changes or GitHub writes.',
            'Use only primary P/.venv/bin/python with worktree/src on PYTHONPATH; all test outputs remain in sibling scratch. At most four workers, one coordinated cohort at a time.',
            'Preserve all failed/interrupted cohorts, old proposals, original ledgers, bytecode and handoffs. No cleanup, deletion, restart or signal is implied.',
            'H2 handoff is sealed at its recorded HEAD and must not be regenerated at the G2 HEAD.',
            'Do not infer host load or root cause from runtime duration. Clean saved proof, not source commits or green partial JUnit, gates issue status.',
            'Lead filing remains necessary for review findings; no mentions, messaging, pushes, PRs or merge are authorized.'],
        'final_handoff': str(REPORTS / 'codex-pr5968-launch-fixes-20261114.md'),
        'final_handoff_json': str(REPORTS / 'codex-pr5968-launch-fixes-20261114.json'),
        'producer': pin(Path(__file__).resolve())}
    directory = OUT / 'checkpoints'
    directory.mkdir(exist_ok=True)
    destination = directory / ('current-g2-' + now.strftime('%Y%m%dT%H%M%S%fZ') + '.json')
    raw = (json.dumps(record, indent=2) + '\n').encode()
    with destination.open('xb') as stream:
        stream.write(raw)
    assert destination.read_bytes() == raw
    print(json.dumps(pin(destination)))


if __name__ == '__main__':
    main()
