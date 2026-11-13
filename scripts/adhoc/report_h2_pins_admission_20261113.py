#!/usr/bin/env python3
"""Generate assigned answer-first handoff from saved evidence, 2026-11-13.
Inputs completed cohort XML/outcomes, source audit and unapplied pin proposal.
Outputs Markdown/JSON in R; no execution, pin changes or external writes.
"""
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import re
import subprocess
import xml.etree.ElementTree as ET

R = Path(__file__).resolve().parents[2]; E = R.parent
B = Path.home() / 'agent-work/data-sheets-schema/helper2-pins-admission-20261113'
H = R / 'notes/development_efficiency_20261111/handoffs'
HP = E / 'codex-native-host-power-20261113'
sha = lambda raw: hashlib.sha256(raw).hexdigest()
def pin(path): return dict(path=str(path), sha256=sha(path.read_bytes()), bytes=path.stat().st_size)
def read(path): return json.loads(path.read_bytes())
def cohort(name):
    root = B / 'tests' / name
    outcome = read(root / 'outcome.json')
    counts, failures = defaultdict(Counter), []
    completed_nodes = {json.loads(line)['node'] for path in root.glob('timing*.jsonl')
                       for line in path.read_text().splitlines()}
    incomplete_nodes = []
    xml = root / 'pytest.xml'
    if xml.exists():
        for case in ET.parse(xml).iter('testcase'):
            if name == 'generation-guards' and case.get('name') is None:
                incomplete_nodes.append({'unreported_junit_entry': dict(case.attrib)})
                continue
            parts = case.get('classname', 'unknown').split('.')
            index = next((i for i, part in enumerate(parts) if part.startswith('test_')), len(parts)-1)
            filename = case.get('file') or '/'.join(parts[:index+1]) + '.py'
            status = next((tag for tag in ('failure', 'error', 'skipped') if case.find(tag) is not None), 'passed')
            node = filename + '::' + '::'.join(parts[index+1:] + [case.get('name', '<unreported>')])
            if name == 'generation-guards' and status == 'passed' and node not in completed_nodes:
                status = 'incomplete'
                incomplete_nodes.append(node)
            counts[filename][status] += 1
            if status in ('failure', 'error'):
                child = case.find(status)
                text = child.text or ''
                failures.append(dict(file=filename, test=case.get('name'), status=status,
                    message=child.get('message'), tail=text[-2000:],
                    mentions_scanner_contract_refusal='v2 envelope authority source changed' in text,
                    mentions_controller_pin_refusal='frozen native controller bytes changed: run_native_canary' in text))
    assert outcome['cleanup_verified'] and not outcome['observed_surviving_pids'], name
    if name == 'generation-guards':
        reported = int(re.findall(r'\b(\d+) passed\b', (root / 'pytest.log').read_text())[-1])
        assert sum(value['passed'] for value in counts.values()) == reported
    return dict(outcome=pin(root / 'outcome.json'), returncode=outcome['returncode'],
        junit=pin(xml) if xml.exists() else None,
        teardown_records=[pin(path) for path in sorted(root.glob('timing*.jsonl'))],
        complete=name != 'generation-guards',
        incomplete_junit_entries=incomplete_nodes,
        seconds=outcome['seconds'], cleanup_verified=outcome['cleanup_verified'],
        origins_passed=outcome['worker']['source_origin_checks_passed'],
        plan=read(root / 'plan.json'), counts_by_file=dict(counts), failures=failures,
        log=pin(root / 'pytest.log') if (root / 'pytest.log').exists() else None)

names = ('pin-canary', 'admitted-touched-files', 'admission-alarm-canary', 'new-unit-files',
         'publication-awaiting-pins', 'specificity', 'generation-guards', 'admitted-scanner-baseline')
cohorts = {name: cohort(name) for name in names}
audit = read(B / 'source-audit.json')
proposal = H / 'codex-h2-admission-pin-proposal-20261113.diff'
metadata = read(proposal.with_suffix('.json'))
for row in metadata['module_census']:
    assert sha((HP / row['path']).read_bytes()) == row['actual_sha256']
    saved = subprocess.check_output(['git', 'show', metadata['source_head'] + ':' + row['path']], cwd=HP)
    assert sha(saved) == row['actual_sha256']
simulation = read(B / 'admission-function/results.json')
assert all(row['passed'] for row in simulation['rows'])
scanner = B / 'tests/specificity/scanner.md'
scan_text = scanner.read_text() if scanner.exists() else ''
violation_rows = scan_text.split('## gc_project violations', 1)[-1].split('## Tracked categories', 1)[0]
violation_rows = [line for line in violation_rows.splitlines() if line.startswith('| `')]
scan_log = (B / 'tests/specificity/pytest.log').read_text().strip()
baseline_log = (B / 'tests/admitted-scanner-baseline/pytest.log').read_text().strip()
authority_path = 'src/data_sheets_schema/native_attribution_controller_v2.py'
authority_hashes = {name: sha((B / name / authority_path).read_bytes()) for name in ('fixed', 'unaffected')}
scanner_note = ('The specificity scan did not happen (exit 2): its frozen v2-envelope authority contract '
    'rejects native_attribution_controller_v2.py. The same source bytes occur in the lead-admitted export '
    'and the new-source export. The baseline comparison reproduces the refusal: '
    + str(scan_log == baseline_log) + '. The scanner expects source hash '
    '1e1cc08057523bb6d6c0d2da660af6a1b68a43b5b08bf9e43993c0b17ee75722 at scan.py:13003; '
    'both exports contain ' + authority_hashes['fixed'] + '. This requires scanner-instrument review '
    'after the controller pin rotations; no scanner pin was changed. No clean specificity result is claimed.')
totals = Counter()
for counts in cohorts['admitted-touched-files']['counts_by_file'].values(): totals.update(counts)
answer = ('Lead pins were fast-forwarded into the power branch and the admitted eight-file cohort completed: '
    + ', '.join(str(v) + ' ' + k for k, v in sorted(totals.items()))
    + '. Admission, documentation, personal-path and pre-reservation diagnostic changes are committed locally. '
    'The new controller pin proposal is unapplied; the stalled-verification publication integration awaits lead admission. '
    'The specificity scanner also needs review of its frozen authority-source contract. '
    'The supplementary generation guard suite was stopped after repeated contract refusals; its reported counts are partial. '
    'Nothing was pushed or published; no live native/provider/model call or public completion test ran.')
admission = ('900 seconds, as assigned: the earlier timing evidence lacks a measured admission interval that supports '
    'a different value. The bound starts at execute_child entry and ends at the dispatch origin on the existing '
    'suspension-inclusive elapsed clock. It consumes none of the 900, 21600 or 43200 child seconds. A 0.1-second '
    'periodic POSIX alarm checks that clock and raises AdmissionExpired through interruptible Python syscalls; '
    'the exception bypasses broad Exception handlers. A synchronous check at dispatch refuses an expired bound '
    'even before alarm delivery. Signal ownership is exclusive and restored after admission. Existing controller '
    'cleanup, keep-awake cleanup and failure publication retain the distinct reason: native admission deadline '
    'elapsed; child was not dispatched. Cleanup/publication themselves lie outside the admission interval.')
limits = ('This in-process mechanism cannot preempt an uninterruptible kernel call or a C extension that never '
    'services Python signals; alarm handling resumes when the host and Python run again. The exact dispatch '
    'check remains fail-closed. Earlier pre-reservation verification is outside this timer. The real FIFO-open '
    'tests exercise interruptible syscall cancellation, not a universal hard-real-time cleanup guarantee.')
capture = ('The new host-pre-dispatch-<registration-sha256>.jsonl lives beside the attempt, outside the closed '
    'capture tree. Timestamps are buffered until a freshly verified registration supplies the canonical existing '
    'parent. Explicit capture, current guard preparation and public launch scopes append capture observation, '
    'current_guard_preparation, every active registration.verified call, admission with classifier, controller '
    'construction/prewarm, _current_authority and reservation start/end, plus attempt_reserved. The synthetic '
    'fixture records its invented capture at minting. Step IDs, trace IDs, process IDs and registration digest '
    'join rows; capture timestamps/digests distinguish captures. It uses the same continuous clock and is never '
    'read for admission. It stops after reservation. Byte/row buffering is bounded; failed/contended writes disable '
    'observation. Missing rows mean unknown timing. Synchronous diagnostic I/O can add latency; it is not claimed '
    'to have zero runtime effect. No newly instrumented public duration is claimed before pins are admitted.')
reorder = ('A later capture is possible in principle without changing the 1200-second maximum age or 300-second '
    'margin. Source-only registration, review/word/protocol validation, classifier derivation and controller '
    'prewarm do not need the captured quota event. _current_authority reconstructs those inputs; its quota '
    'request validation does not inspect an observed event. Current guard preparation and latest-claim selection '
    'do need the capture and cannot simply move before it. Proposed for the lead: a reviewed preparation phase '
    'finishes cold source/controller work, then takes one fresh capture, constructs its current guard, rechecks '
    'exact source/input identities and the current word/latest claim under the existing lock, and reserves. '
    'Keep all final freshness, source, word and dispatch checks; do not reuse a previously verified value as '
    'launch authority. Current consumer-loader scopes cannot simply be held across bootstrap orchestration. '
    'Measure the remaining fresh reconstruction before promising that it fits 900 seconds. This needs an '
    'explicit two-phase interface/source review; no reordering, retimestamping, recapture or limit relaxation '
    'was implemented.')
record = dict(answer=answer, lead_pin_commit='a2db8ab6b403e5c70f1020c927dd6185fe8a574c',
    report_generator=pin(Path(__file__).resolve()),
    branches=audit['heads'], admitted_export=read(B / 'fixed.json'),
    new_source_export=read(B / 'unaffected.json'), cohorts=cohorts,
    test_duration_basis='Runner seconds use time.monotonic, not the continuous admission clock. They are not capture-to-reservation measurements or evidence of a quiet, unsuspended host.',
    guard_failure_contract_mentions=sum(item['mentions_scanner_contract_refusal']
        for item in cohorts['generation-guards']['failures']),
    source_audit=pin(B / 'source-audit.json'), admission=dict(seconds=900, mechanism=admission, limitations=limits),
    source_function_checks=dict(results=pin(B / 'admission-function/results.json'), passed=len(simulation['rows'])),
    capture_timing=capture, capture_reordering_proposal_only=reorder,
    new_pin_proposal=pin(proposal), pin_metadata=pin(proposal.with_suffix('.json')),
    controller_sources_equal_proposal_head=True,
    scanner=dict(report=pin(scanner) if scanner.exists() else None, violation_rows=violation_rows,
        status='scan refused; no surface classification', diagnostic=scan_log,
        baseline_diagnostic=baseline_log, same_refusal=scan_log == baseline_log,
        authority_hashes=authority_hashes, assessment=scanner_note),
    documentation=dict(audit=pin(B / 'docs-audit/run-limit-audit.json'),
        anchor_refusal=pin(B / 'docs-anchor-refusal.log'), historical_references_retained=True),
    daemon_recovery=dict(receipt=pin(B / 'queue-recovery.json'),
        note='The active admitted rerun survived daemon restart and was not restarted. Only its idle waiting validation driver was identity-checked and restarted with durable stdout. Saved worker/outcome files establish completion and cleanup.'),
    supplementary_guard_interruption=dict(receipt=pin(B / 'blocked-guards-interruption.json'),
        note='Only the supplementary generation-guard pytest controller received SIGINT after repeated source-contract failures. Pytest retained partial XML/logs, returned normally with interruption status, and the owner runner verified cleanup without forced termination. These counts are not a completed guard suite.'),
    integration_note='The final power-head delta after the unit export and proposal is only the stalled-publication test clock setup; all controller bytes are identical. That integration test remains unverified until new pins are applied.',
    merge_review='Automatic approval review rejected an additional power-to-limits branch merge as lacking explicit merge authorization. It was not retried. The documentation generator reads both source packets explicitly; their branches remain separate for lead integration.',
    review='Separate read-only diff review completed. Pending controller admission, the scanner authority-source contract refusal, and interruptibility limits are explicit findings for the lead; no review issue was published under the offline constraint. No authority, scanner or prompt pin was restamped.',
    remaining=['Lead review/apply the new pin proposal, retaining the unchanged permission-protocol test CONTROL_SHA.',
        'Review the scanner frozen authority-source contract against the final approved pin rotation; rerun the scanner and affected guards without a blind restamp.',
        'On admitted new code, run the stalled-verification publication test and touched orchestration/capture/controller integration files.',
        'Lead decides whether to implement the proposed later-capture workflow; D138 limits remain unchanged.'])
lines = ['# Helper 2: pins, admission and capture timing', '', answer, '', '| Branch | Head |', '| --- | --- |']
for name, head in audit['heads'].items(): lines.append('| ' + name + ' | `' + head + '` |')
lines += ['', 'The requested pin merge was a fast-forward. The four protected files and guard v1 remain equal to '
    'candidate f7f8e8bff; no primary-checkout edits. The cache branch has no new commit in this assignment; '
    'the three remaining runner fixes are in the power packet.', '',
    'The admitted rerun used export commit `' + record['admitted_export']['commit'] + '`, composed from power `'
    + record['admitted_export']['power'] + '` and limits `' + record['admitted_export']['limits'] + '`. '
    'The new unit checks used source `' + record['new_source_export']['commit'] + '` with unchanged pins. '
    'The admitted rerun does not certify the subsequent admission-controller change.', '',
    'Admitted rerun counts, derived from its saved JUnit XML:', '',
    '| File | Passed | Failures | Errors | Skipped |', '| --- | ---: | ---: | ---: | ---: |']
for name, counts in sorted(cohorts['admitted-touched-files']['counts_by_file'].items()):
    lines.append('| `' + name + '` | ' + ' | '.join(str(counts.get(k, 0)) for k in ('passed','failure','error','skipped')) + ' |')
lines += ['', 'Other saved checks:', '', '| Cohort | Counts | Runner seconds (monotonic) |', '| --- | --- | ---: |']
for name, row in cohorts.items():
    if name == 'admitted-touched-files': continue
    count = Counter()
    for item in row['counts_by_file'].values(): count.update(item)
    label = name + (' (partial)' if not row['complete'] else '')
    lines.append('| ' + label + ' | ' + (', '.join(str(v) + ' ' + k for k,v in sorted(count.items())) or 'scanner exit ' + str(row['returncode'])) + ' | ' + str(row['seconds']) + ' |')
lines += ['', 'All cohorts use outside-execution exports, denied network/native execution and at most two xdist workers; '
    'origin and owned-process cleanup checks are saved. The actual-source FIFO canary proves alarm interruption. '
    'The additional ' + str(len(simulation['rows'])) + ' pure execute_child checks prove refusal, descriptor cleanup '
    'and child-clock separation without loading or admitting a registered controller. They do not prove failure publication.', '',
    record['test_duration_basis'], '',
    admission, '', limits, '', capture, '', reorder, '',
    'Review-only pin proposal: `' + str(proposal) + '`. SHA-256 `' + record['new_pin_proposal']['sha256'] + '`. '
    'It contains both manifest rotations and their three authority constants. The test census includes ignored/hidden '
    'files and explicitly checks CONTROL_SHA. native_control.py is unchanged, so that live test digest is retained. '
    'Historical protocol prose and fixture evidence are not restamped.', '', record['integration_note'], '',
    'Documentation and generator describe continuous dispatch origin and the separate admission budget. The negative '
    'anchor test refuses before writing; historical draft-v12 references and the 300-second margin remain. '
    'run_helper_cache_tests_20261112.py, run_native_h2_tests_20261112.py and run_native_h2_sequence_tests_20261112.py '
    'now discover home, NVM and PATH locations without executing the binaries. Other helpers’ runners were untouched.', '',
    scanner_note, '',
    record['merge_review'], '', record['review'], '',
    record['daemon_recovery']['note'], '',
    record['supplementary_guard_interruption']['note'], '',
    str(record['guard_failure_contract_mentions']) + ' recorded guard failures/errors mention the frozen scanner contract refusal. '
    'There are no completed results in this supplementary run for test_neutral_generation_schema.py, test_profiles.py '
    'or test_external_dataset_onboarding.py; those checks remain pending. Two unnamed interrupted JUnit entries '
    'are retained separately and are not counted as passes.', '',
    *[str(i) + '. ' + item for i,item in enumerate(record['remaining'],1)], '',
    'Detailed source checks: `' + str(B / 'source-audit.json') + '`, SHA-256 `' + record['source_audit']['sha256'] + '`.']
body = '\n'.join(lines) + '\n'
assert chr(64) not in body
prefix = H / 'codex-h2-pins-admission-20261113'
prefix.with_suffix('.md').write_text(body)
prefix.with_suffix('.json').write_text(json.dumps(record, indent=2).replace(chr(64), '\\u0040') + '\n')
print(json.dumps(dict(markdown=pin(prefix.with_suffix('.md')), json=pin(prefix.with_suffix('.json')))))
