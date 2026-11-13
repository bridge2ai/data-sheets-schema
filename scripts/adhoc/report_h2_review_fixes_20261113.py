#!/usr/bin/env python3
"""Generate answer-first review-fix handoff from saved audit/results, 2026-11-13.
Inputs audit JSON and pin proposal; outputs assigned Markdown/JSON handoff.
No external writes, authority mutation or execution of native/provider tools.
"""
from pathlib import Path
from collections import Counter
import hashlib
import json

R = Path(__file__).resolve().parents[2]
out = R / 'notes/development_efficiency_20261111/handoffs'
audit_path = out / 'codex-h2-review-fixes-audit-20261113.json'
audit = json.loads(audit_path.read_bytes())
def pin(path):
    return {'path': str(path), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest(), 'bytes': path.stat().st_size}
issues = [
    {'issue': '6167', 'commit': '2c158ddfc', 'branch': 'power',
     'change': 'Supplemental start/stage/end persistence errors retain diagnostics and cannot replace launch errors or interrupt final publication.',
     'tests': 'test_native_failure_publication.py (start/end injected disk errors); test_native_shared_live_capture.py (committed stage with failed clock); test_native_host_power.py (active cleanup exception)'},
    {'issue': '6168', 'commit': 'f377dba1d', 'branch': 'power',
     'change': 'No-sleep requires recognized, ordered, matched events bracketing the interval. Unknown formats, gaps and unmatched events remain unknown; clock divergence stays separate.',
     'tests': 'test_native_host_power.py: timestamped unrecognized, incomplete coverage, DarkWake, unmatched events, covered no-sleep'},
    {'issue': '6169', 'commit': '94378cd62', 'branch': 'limits',
     'change': 'Provisional rejection begins with a valid accepted document, mutates only the pair, checks generic acceptance and pair-specific refusal. Removing the pair check in the test admits the five invalid pairs.',
     'tests': 'test_native_run_limits.py::test_provisional_refusal_depends_on_registered_pair_check (five cases; whole file also run)'},
    {'issue': '6170', 'commit': 'feb1de325', 'branch': 'power',
     'change': 'Declared child deadline begins immediately before Popen after admission, uses suspension-inclusive elapsed time, and checks expiry even if the child exited while suspended. AC is checked last before dispatch.',
     'tests': 'test_native_attempt_deadline.py: six simulated-sleep cases, admission exclusion, macOS integer conversion, AC-to-battery/unknown public refusal. Integrated cases currently stop at controller pin verification.'},
    {'issue': '6171', 'commit': '0df39c077', 'branch': 'limits',
     'change': 'Generated documentation preserves 300-second reservation margin and recorder --render-spec-env D4D_RENDER_SPEC plus --render-spec-sha256. Pair selection changes the visible digest; runtime stays readable.',
     'tests': 'audit_run_limits_20261113.py source inventory regenerated to a new evidence directory; generator and document inspected'},
    {'issue': '6172', 'commit': '916ad3af0', 'branch': 'power',
     'change': 'Both reviewed runners derive local installation paths at runtime; reconciliation helper derives its home path. Sleep fixture is entirely synthetic with 1252-second and 7034-second intervals.',
     'tests': 'test_native_host_power.py synthetic fixture; hidden/ignored-inclusive personal-path search over edited helpers; AST parsing'},
    {'issue': '6172 cache follow-up', 'commit': '9d743c877', 'branch': 'cache',
     'change': 'Required separate cache-branch follow-up fixes the published cache runner and reconciliation helper.',
     'tests': 'Hidden/ignored-inclusive personal-path search and AST parsing; no behavioral cache changes'},
    {'issue': '6094 / assignment item 7', 'commit': 'a4f45bb93', 'branch': 'power',
     'change': 'Bounded supplemental host-controller-timing.jsonl records execute_child entry, dispatch origin/deadline, callback delivery, tool-result intake and model turn frames, joined by tool ID and command digest.',
     'tests': 'test_native_attempt_timing.py: partial-response and persistence-failure units pass; inert controller integration currently stops at exact-source verification'},
]
for issue in issues:
    matching = [line.split()[0] for line in audit['branches'][issue['branch']]['commits'] if line.startswith(issue['commit'])]
    assert len(matching) == 1
    issue['commit'] = matching[0]
cohort_rows = []
for name, cohort in audit['cohorts'].items():
    counts = Counter()
    for values in cohort.get('counts_by_file', {}).values(): counts.update(values)
    cohort_rows.append({'name': name, 'counts': dict(counts),
        'returncode': cohort['outcome']['returncode'], 'seconds': cohort['outcome']['seconds'],
        'commit': cohort['plan']['source_commit'], 'cleanup_verified': cohort['outcome']['cleanup_verified'],
        'all_nonpasses_are_controller_pin_refusals': all(row['controller_pin_refusal'] for row in cohort.get('failures', []))})
proposal = out / 'codex-h2-controller-pin-proposal-20261113.diff'
timing = out / 'codex-h2-6094-timing-20261113.md'
simulation_path = Path.home() / 'agent-work/data-sheets-schema/helper2-review-fixes-20261113/deadline-function/results.json'
simulation = json.loads(simulation_path.read_bytes())
assert all(row['passed'] for row in simulation['rows'])
record = {'answer': 'Local implementation is committed, but the power branch is not ready to integrate: exact controller pins remain unchanged and block integrated deadline/timing validation. Automatic approval review rejected their update. No publication or native run occurred.',
    'first_assignment': pin(timing), 'candidate': audit['candidate'], 'branches': audit['branches'],
    'issues': issues, 'cohorts': cohort_rows, 'clock': audit['clock'], 'audit': pin(audit_path),
    'pure_function_simulations': {'results': pin(simulation_path), 'passed': len(simulation['rows']), 'scope': simulation['scope']},
    'scanner_comparison': audit['scanner_comparison'],
    'pin_proposal': pin(proposal), 'proposal_metadata': pin(out / 'codex-h2-controller-pin-proposal-20261113.json'),
    'approval_rejection': 'Controller manifest and authority digest updates were rejected as security-sensitive trust-pin changes reserved for the lead. No authority/scanner/prompt pin was edited, including in the private exports.',
    'remaining': ['Approve or have the lead apply the five-file pin proposal after source review.',
                  'Repeat the whole touched-file cohort against the admitted composition; start/stage publication failures, simulated deadline, AC-transition and controller timing integration have not yet reached their assertions there. The independent pre-clock end-failure canary passed.',
                  'Any quiet-host public completion run remains for the lead; the existing 900-second declaration is unchanged.'],
    'review': 'Read-only diff review performed separately. No further implementation finding beyond the unapplied controller pins. Integrated behavior remains unverified where source admission stopped. One pre-existing blank EOF line remains in the power proof runner (reported by full-branch diff --check). No GitHub issue or review was written.',
    'timing_limits': 'Helper endpoints measure controller response delivery to result intake, including transport/scheduling; they are not actual subprocess start/exit or CPU time. Model boundaries are received CLI assistant/user/result frames, with message start/stop when supplied, not provider-internal token timing.',
    'provenance_scripts': sorted(str(path) for path in (R / 'scripts/adhoc').glob('*h2*review*fixes*20261113.py')) +
        [str(R / 'scripts/adhoc/prepare_h2_unaffected_fixes_20261113.py'), str(R / 'scripts/adhoc/propose_h2_controller_pins_20261113.py'),
         str(R / 'scripts/adhoc/simulate_h2_deadline_function_20261113.py'),
         str(R / 'scripts/adhoc/bound_h2_failure_canary_20261113.py')],
}
lines = ['# Helper 2: run-limit and power review fixes', '', record['answer'], '',
    'The read-only 6094 timing assignment was completed first: `' + str(timing) + '`, SHA-256 `' + record['first_assignment']['sha256'] + '`.', '',
    '## Branches and integration', '',
    'Fetched origin once as explicitly requested, then merged candidate `' + audit['candidate'] + '` with `git merge --no-ff` into each assigned branch. No rebase, push or GitHub write. All three branches are clean. The four protected files and guard v1 remain byte-identical to that candidate.', '',
    '| Branch | Head |', '| --- | --- |']
for branch in audit['branches'].values(): lines.append('| `' + branch['branch'] + '` | `' + branch['head'] + '` |')
lines += ['', '## Issue commits and proof', '', '| Issue | Commit | Change and proving test |', '| --- | --- | --- |']
for issue in issues:
    lines.append('| ' + issue['issue'] + ' | `' + issue['commit'] + '` | ' + issue['change'] + ' ' + issue['tests'] + ' |')
lines += ['', 'The two 6172 commits are the explicitly requested follow-ups on different branches; their shared edits are identical.', '',
    '## Saved tests', '',
    'Every touched test file ran whole in a network-denied export outside all d4d-executions paths. At most two xdist workers. No real native binary, provider, model call, host probe or public completion run. Test probes use invented local interface bytes. The failure-publication canary stops before peer dispatch; it is not a public completion attempt.', '',
    '| Cohort | Counts | Exit | Seconds | Source commit |', '| --- | --- | ---: | ---: | --- |']
for row in cohort_rows:
    counts = ', '.join(str(v) + ' ' + k for k, v in sorted(row['counts'].items())) or 'scanner (see retained report)'
    lines.append('| ' + row['name'] + ' | ' + counts + ' | ' + str(row['returncode']) + ' | ' + str(row['seconds']) + ' | `' + row['commit'] + '` |')
lines += ['', 'The `fixed` export is the current power/run-limit composition. Every current whole-file failure/error is an unchanged controller hash refusing changed source. The `unaffected` export retains the original controller sources and checks the earlier observation and pair/privacy fixes independently; its passes do not validate the clock/timing changes. All completed cohorts retain origin/network checks and verified owned-process cleanup.', '',
    'The independent end-failure canary passed: after the launch error was already caught, an injected end-sidecar write error preserved that first error, allowed failed-result publication, and retained exact readback. It completed before the optional ten-minute cancellation check; no cancellation signal was sent. Start/stage integration remains to be rerun after source admission is repaired.', '',
    '## Deadline clock and diagnostics', '',
    'macOS uses `mach_continuous_time`, scaled by integer `mach_timebase_info`. Apple SDK header `' + audit['clock']['documentation']['path'] + '` lines 58–62 explicitly states that it advances during sleep; retained header SHA-256 `' + audit['clock']['documentation']['sha256'] + '`. Linux implementation uses `clock_gettime_ns(CLOCK_BOOTTIME)`. No adjustable time-of-day or suspension-excluding fallback is accepted.', '',
    'The origin is immediately before `Popen`, after launch verification and the final AC check. Declared durations remain 900, 21600 and 43200 seconds. '+record['timing_limits'], '',
    str(len(simulation['rows'])) + ' pure-function simulations passed using the exact execute_child AST, fake clocks and fake process objects: long admission, suspension while running, and suspension with an exited child, for each registered duration. This checks the deadline function without changing or replacing any authority loader/check. It is not source-admitted controller integration. Evidence: `' + str(simulation_path) + '`, SHA-256 `' + record['pure_function_simulations']['results']['sha256'] + '`.', '',
    '## Approval boundary and remaining work', '', record['approval_rejection'], '',
    'Reviewable proposal: `' + str(proposal) + '`, SHA-256 `' + record['pin_proposal']['sha256'] + '`. It changes only the two controller manifests and their three exact digest constants; the corresponding JSON lists all old and proposed hashes. The proposal is not applied.', '',
    *[str(i) + '. ' + item for i, item in enumerate(record['remaining'], 1)], '',
    'The whole-source specificity scanner ran without restamping its contracts. Both the current and pre-clock compositions exit 1 with the same nine legacy-controller project-default findings; the native-agentic surface has zero specificity violations. The exact rows and reports are retained in the audit JSON. This task does not authorize a launch or claim the integrated candidate passes.', '',
    '## Review and provenance', '', record['review'], '',
    'Detailed source, privacy, protected-byte, SDK and per-test evidence: `' + str(audit_path) + '`, SHA-256 `' + record['audit']['sha256'] + '`.', '',
    'Provenance helpers retained in R:', '', *['- `' + item + '`' for item in record['provenance_scripts']], '']
for suffix, content in [('json', json.dumps(record, indent=2).replace(chr(64), '\\u0040') + '\n'), ('md', '\n'.join(lines))]:
    assert chr(64) not in content
    path = out / ('codex-h2-run-limits-power-fixes-20261113.' + suffix)
    with path.open('x') as stream: stream.write(content)
    print(json.dumps(pin(path)))
