#!/usr/bin/env python3
"""Retain G2-REVIEW-ENGINE-FRESHNESS-F1 diagnostics, 2026-11-14.

Inputs: stopped final-engine-dependents cohort, cleanup proof, saved guards and
supplemental timing traces. Outputs: exclusive review-engine-freshness.json and
engine-freshness-review-20261114 evidence in scratch-g2-20261114. No project
imports, tests, signals, source/test edits, clock changes or external writes.
"""
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
SCRATCH = ROOT.parent / 'scratch-g2-20261114'
COHORT = SCRATCH / 'final-engine-dependents'
OUTPUT = SCRATCH / 'engine-freshness-review-20261114'
LEDGER = SCRATCH / 'review-engine-freshness.json'
CLEANUP = SCRATCH / 'final-engine-freshness-interruption/cleanup-1794646795499479000.json'
FILE = 'tests/test_native_shared_execution_failure.py'
REFUSAL = 'subscription pre-reservation freshness margin is insufficient'
CASES = (
    ('test_v2_publication_failure_preserves_first_error[published.json]', 'gw2', 'test_v2_publication_failure_pr0'),
    ('test_v2_injected_transport_timeout_keeps_registered_limit_and_failure', 'gw1', 'test_v2_injected_transport_tim0'),
    ('test_v2_publication_failure_preserves_first_error[final.json]', 'gw0', 'test_v2_publication_failure_pr0'),
)
SOURCES = (FILE, 'tests/test_native_shared_execution.py',
    'tests/utils/native_synthetic_evidence.py',
    'src/data_sheets_schema/native_execution_orchestration.py',
    'src/data_sheets_schema/native_subscription_guard_v2.py',
    'src/data_sheets_schema/native_pre_dispatch_timing.py')


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def pin(path):
    raw = Path(path).read_bytes()
    require(bool(raw), 'empty evidence: ' + str(path))
    return {'path': str(path), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def save(path, raw):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as handle:
        handle.write(raw)
    require(path.read_bytes() == raw, 'saved evidence readback differs')
    return pin(path)


def snapshot(source, destination):
    before = pin(source)
    saved = save(destination, Path(source).read_bytes())
    require(pin(source) == before, 'source evidence changed while copied')
    require((saved['bytes'], saved['sha256']) == (before['bytes'], before['sha256']),
            'snapshot differs from original')
    return {'original': before, 'snapshot': saved}


def json_save(path, value):
    return save(path, (json.dumps(value, indent=2, sort_keys=True) + '\n').encode())


def git(*args):
    return subprocess.run(['git', *args], cwd=ROOT, capture_output=True, check=True).stdout


def stamp_ns(value):
    stamp = datetime.fromisoformat(value.replace('Z', '+00:00'))
    delta = stamp - datetime(1970, 1, 1, tzinfo=timezone.utc)
    return ((delta.days * 86400 + delta.seconds) * 1000000 + delta.microseconds) * 1000


def observed_utc(nanoseconds):
    return datetime.fromtimestamp(nanoseconds / 1000000000, timezone.utc).isoformat()


def inspect_case(name, worker, directory, failure, log):
    root = COHORT / 'cases' / ('popen-' + worker) / directory / 'v2-lifecycle'
    require(root.is_dir() and root.resolve() == root, 'unexpected fixture root')
    target = OUTPUT / 'cases' / (worker + '-' + directory)
    guard_path = root / 'authority/invented-subscription.json'
    guard = json.loads(guard_path.read_bytes())
    identity = guard['registration_sha256']
    registration_path = root / 'synthetic-registration-commits' / ('registration-' + identity + '.json')
    require(pin(registration_path)['sha256'] == identity, 'registration hash differs from guard')
    registration = json.loads(registration_path.read_bytes())['registration']
    trace_path = root / ('host-pre-dispatch-' + identity + '.jsonl')
    traces = [json.loads(line) for line in trace_path.read_bytes().splitlines()]
    require(all(row['registration_sha256'] == identity for row in traces), 'trace registration differs')
    captures = [row for row in traces if row['boundary'] == 'capture_observed']
    ends = [row for row in traces if row['boundary'] == 'reservation' and row.get('phase') == 'end']
    require(len(captures) == len(ends) == 1, 'ambiguous capture/reservation trace')
    capture, end = captures[0], ends[0]
    require(capture['captured_at'] == guard['captured_at'], 'capture time differs from guard')
    require(end.get('error_type') == 'ValueError', 'reservation trace is not a ValueError refusal')
    powers = [row for row in traces if row['boundary'] == 'reservation_power'
              and row['trace_id'] == end['trace_id'] and row['elapsed_ns'] < end['elapsed_ns']]
    require(len(powers) == 1 and powers[0]['passed'] is True, 'missing preceding power reading')
    power = powers[0]
    require(not any(row['boundary'] == 'attempt_reserved' for row in traces), 'trace records reservation')
    captured_ns = stamp_ns(guard['captured_at'])
    ages = [(row['wall_ns'] - captured_ns) / 1000000000 for row in (power, end)]
    max_age, margin = guard['max_age_seconds'], guard['pre_reservation_margin_seconds']
    require((max_age, margin) == (1200, 300), 'registered freshness limits differ')
    require(all(max_age - margin < age < max_age for age in ages),
            'saved adjacent timing boundaries do not establish the expected margin range')
    require(power['wall_ns'] <= end['wall_ns'], 'adjacent wall timestamps reversed')
    inventory_argv = ['rg', '--files', '--hidden', '--no-ignore', '--null', str(root)]
    inventory = subprocess.run(inventory_argv, capture_output=True, check=True)
    paths = sorted(Path(os.fsdecode(item)) for item in inventory.stdout.split(b'\0') if item)
    registered = {}
    for key, leaf in (('attempt_directory', 'native-attempt'), ('evidence_directory', 'native-evidence')):
        path = Path(registration[key])
        require(path == root / leaf, 'unexpected registered artifact directory')
        descendants = [str(item.relative_to(root)) for item in paths if item == path or path in item.parents]
        exists = os.path.lexists(path)
        require(not exists and not descendants, 'registered attempt/evidence artifact exists')
        registered[key] = {'path': str(path), 'lexists': exists, 'inventory_matches': descendants}
    inventory_record = {
        'argv': inventory_argv, 'returncode': inventory.returncode,
        'ignored_and_hidden_files_included': True,
        'scope': str(root), 'files': [str(item.relative_to(root)) for item in paths],
        'registered_artifacts': registered,
        'limitation': 'Absence concerns the exact registered native-attempt/native-evidence directories. Synthetic preparation and capture artifacts are present and retained.'}
    inventory_pin = json_save(target / 'artifact-inventory.json', inventory_record)
    evidence = {
        'guard': snapshot(guard_path, target / 'invented-subscription.json'),
        'registration': snapshot(registration_path, target / 'registration-evidence.json'),
        'reservation_trace': snapshot(trace_path, target / 'host-pre-dispatch.jsonl'),
        'artifact_inventory': inventory_pin}
    # Match the retained traceback to its worker and explicit parameter selection.
    header = re.escape(name)
    section = re.search(r'^_{4,}\s+' + header + r'\s+_{4,}\n(.*?)(?=^_{4,}\s|^=+)', log, re.M | re.S)
    require(section is not None and '[' + worker + ']' in section.group(1), 'worker/traceback mapping differs')
    require('native_subscription_guard_v2.py:470' in section.group(1), 'missing exact refusal site')
    return {
        'nodeid': FILE + '::' + name, 'classname': FILE[:-3].replace('/', '.'),
        'name': name, 'worker': worker, 'fixture_root': str(root),
        'failure': failure, 'evidence': evidence,
        'captured_at': guard['captured_at'], 'max_age_seconds': max_age,
        'pre_reservation_margin_seconds': margin,
        'latest_permitted_reservation_age_seconds': max_age - margin,
        'adjacent_trace_observations': [
            {'boundary': row['boundary'], 'phase': row.get('phase'),
             'wall_ns': row['wall_ns'], 'observed_utc': observed_utc(row['wall_ns']),
             'age_from_saved_capture_seconds': age,
             'remaining_lifetime_seconds': max_age - age}
            for row, age in zip((power, end), ages)],
        'exact_guard_clock_reading_saved': False,
        'timing_scope': 'Adjacent supplemental trace boundaries corroborate the margin refusal. They are not the exact guard _now sample; no internal latency cause, host-load cause, or uninterrupted-clock assumption is established.',
        'reservation_trace_error': end['error_type'], 'refusal': REFUSAL,
        'registered_artifacts': registered}


def main():
    require(not OUTPUT.exists() and not LEDGER.exists(), 'preserve existing evidence outputs')
    command = json.loads((COHORT / 'command.json').read_bytes())
    outcome = json.loads((COHORT / 'outcome.json').read_bytes())
    log = (COHORT / 'pytest.log').read_text()
    cleanup = json.loads(CLEANUP.read_bytes())
    require(cleanup['status'] == 'cleanup-confirmed' and cleanup['safe_to_release_source_freeze'] is True,
            'cleanup was not confirmed')
    require(all(row['original_reaped'] for row in
                [cleanup['runner'], cleanup['coordinator'], *cleanup['workers'], *cleanup['observed_descendants']]),
            'saved owned process identity remains')
    require(outcome['returncode'] == 2, 'interrupted outcome differs')
    summaries = re.findall(r'^3 failed, 237 passed, 52 warnings in .+$', log, re.M)
    require(len(summaries) == 1 and 'KeyboardInterrupt' in log, 'unexpected interrupted summary')
    junit = list(ET.parse(COHORT / 'pytest.xml').iter('testcase'))
    failures = {node.get('name'): {'message': node.find('failure').get('message', ''),
                                 'text': node.find('failure').text or ''}
                for node in junit if node.find('failure') is not None}
    require(all(node.get('classname') == FILE[:-3].replace('/', '.') for node in junit
                if node.find('failure') is not None), 'failed JUnit module differs')
    require(set(failures) == {row[0] for row in CASES}, 'failed case identities differ')
    require(all(REFUSAL in value['text'] for value in failures.values()), 'unexpected failure cause')
    counts = Counter('failed' if node.find('failure') is not None else
                     'error' if node.find('error') is not None else
                     'skipped' if node.find('skipped') is not None else 'no_failure_marker'
                     for node in junit)
    require(len(junit) == 241 and counts == {'failed': 3, 'no_failure_marker': 238}, 'JUnit counts differ')
    require(outcome['counts'] == {'total': 241, 'failed': 3, 'error': 0, 'skipped': 0}, 'runner counts differ')
    for name, expected in cleanup['artifacts'].items():
        require(pin(COHORT / name) == expected, 'cleanup artifact pin differs: ' + name)
    require(command['cwd'] == str(ROOT), 'unexpected source checkout')
    head = git('rev-parse', 'HEAD').decode().strip()
    source_scope = ('src', 'tests', 'notes/matched_cborg_2026-09-13', 'pyproject.toml',
                    'poetry.lock', 'conftest.py', '.github/workflows/main.yaml')
    git('diff', '--exit-code', command['head'], head, '--', *source_scope)
    git('diff', '--exit-code', 'HEAD', '--', *source_scope)
    OUTPUT.mkdir()
    artifacts = {name: snapshot(COHORT / name, OUTPUT / ('cohort-' + name))
                 for name in ('command.json', 'outcome.json', 'pytest.log', 'pytest.xml')}
    cleanup_proof = snapshot(CLEANUP, OUTPUT / 'cleanup-confirmed.json')
    sources = {name: snapshot(ROOT / name, OUTPUT / 'reviewed-source' / name) for name in SOURCES}
    cases = [inspect_case(name, worker, directory, failures[name], log)
             for name, worker, directory in CASES]
    finding = {
        'finding_id': 'G2-REVIEW-ENGINE-FRESHNESS-F1',
        'status': 'open; unresolved required verification failure; unchanged-source serial validation pending',
        'lead_filing_needed': True, 'github_issue_number': None,
        'finding': 'Three required shared execution failure/publication assertions refused at the genuine pre-reservation freshness margin before reaching their injected failure paths.',
        'required_clean_full_file': FILE, 'cases': cases,
        'proven': ['The three saved tracebacks end in guard_v2.py:470 pre-reservation margin ValueError.',
                   'Each saved guard binds max_age_seconds=1200 and pre_reservation_margin_seconds=300.',
                   'The exact registered native-attempt and native-evidence directories are absent in ignored-inclusive inventories and explicit path checks.',
                   'The cohort was interrupted, returned 2, and its retained runner/coordinator/worker identities were subsequently confirmed reaped.'],
        'unknown': ['Why validation took long enough to consume the reservation margin.',
                    'Whether the failures reproduce serially or at another baseline.',
                    'Whether any production regression caused the duration; no host-load or callback-path cause is established.'],
        'baseline_reproduction_established': False, 'internal_or_timing_cause_established': False,
        'source_or_test_correction_applied': False,
        'proposed_unapplied': {
            'option': 'A test-local synthetic subscription _now anchored to the existing saved capture could isolate unrelated publication/transport assertions. A fixture-wide version must retain the expiry test explicit clock advance and separately handle the standalone pre-dispatch publication test.',
            'tradeoff': 'Such cases would no longer measure elapsed wall-clock freshness. It would not fix validation latency or prove a production performance improvement.',
            'decision': 'Unapplied. Root is first running unchanged-source serial validation; limits, clocks, assertions and production refusal remain unchanged.'},
        'verification_plan': 'Require a clean, normally completed source-equivalent whole-file invocation with full census and all three exact failed parameter identities passing. A passing serial canary alone cannot close this finding. Preserve original failures and unresolved cause after any later success.'}
    record = {
        'kind': 'g2_engine_freshness_review', 'producer': pin(Path(__file__).resolve()),
        'recorded_at': datetime.now(timezone.utc).isoformat(),
        'cohort': 'final-engine-dependents', 'source_head': command['head'],
        'current_head_at_recording': head, 'source_scope_unchanged': list(source_scope),
        'artifacts': artifacts, 'cleanup': cleanup_proof, 'reviewed_sources': sources,
        'outcome': outcome, 'pytest_summary': summaries[0],
        'junit_accounting': {'total': len(junit), **dict(counts),
            'pytest_log_completed_passes': 237, 'additional_unconfirmed_entry_count': 1,
            'per_node_pass_acceptance': False,
            'reason': 'Exit 2 and 238 unmarked JUnit entries versus 237 log passes: do not promote an unmarked entry or any partial file to accepted completion.'},
        'findings': [finding], 'tests_run_by_this_helper': [], 'source_or_test_changes': [],
        'clock_or_limit_changes': [], 'signals_sent': [], 'github_writes': []}
    result = json_save(LEDGER, record)
    require(json.loads(LEDGER.read_bytes()) == record, 'ledger readback differs')
    print(json.dumps({'ledger': result, 'finding_id': finding['finding_id'],
        'cases': [{'name': row['name'], 'trace_age_seconds': [x['age_from_saved_capture_seconds']
                   for x in row['adjacent_trace_observations']]} for row in cases]}, indent=2))


if __name__ == '__main__':
    main()
