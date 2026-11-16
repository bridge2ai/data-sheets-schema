"""Summarize the lead's one-stat continuation, 2026-11-16.

Inputs: retained scratch profiles, public events and test logs. Outputs: JSON,
Markdown evidence and a new handoff section for the launch-cost assignment.
"""
from collections import Counter
from datetime import datetime
import hashlib
import json
from pathlib import Path
import pstats
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
S = ROOT.parent / 'scratch-launch-cost-20261116'
HANDOFF = ROOT.parent / 'codex-development-efficiency-20261111/notes/development_efficiency_20261111/handoffs/codex-launch-cost-20261116.md'


def rows(path):
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def profile(path):
    stats = pstats.Stats(str(path)).stats
    return {kind: sum(value[1] for key, value in stats.items()
                      if key[2] == '<built-in method posix.' + kind + '>')
            for kind in ('stat', 'lstat', 'fstat')}


def seconds(value):
    return 'unavailable' if value is None else f'{value:.3f} seconds'


def main():
    events = rows(S / 'one-stat-public-events.jsonl')
    entries = [row for row in events if row.get('function') == 'launch_case'
               and row['boundary'] == 'start']
    launch = entries[0]['wall_ns'] / 1e9 if entries else float('inf')
    capture = (datetime.fromisoformat(entries[0]['guard']['captured_at'].replace('Z', '+00:00')).timestamp()
               if entries else None)
    spans, starts = [], {}
    for path in (S / 'one-stat-public').rglob('host-pre-dispatch-*.jsonl'):
        for row in rows(path):
            if row['wall_ns'] / 1e9 < launch:
                continue
            key = (row['trace_id'], row.get('step_id'))
            if row.get('phase') == 'start':
                starts[key] = row
            elif row.get('phase') == 'end' and key in starts:
                prior = starts.pop(key)
                spans.append({'phase': row['boundary'], 'start': prior['wall_ns'] / 1e9,
                              'seconds': (row['elapsed_ns'] - prior['elapsed_ns']) / 1e9})
    wanted = {'registration.verified', 'controller_prewarm', 'admission_with_classifier', '_current_authority'}
    spans = sorted((row for row in spans if row['phase'] in wanted), key=lambda row: row['start'])
    if not spans:
        for row in events:
            if row.get('boundary') == 'end' and row['wall_ns'] / 1e9 >= launch:
                name = row.get('function')
                if name in ('verified', '_current_authority'):
                    spans.append({'phase': 'registration.verified' if name == 'verified' else name,
                                  'seconds': row['seconds']})
    dispatch = [row for row in events if row.get('function') == '_admit_subscription_guard'
                and row['boundary'] == 'end']
    callbacks = [row for row in events if row.get('function') in ('_observe_event', 'at_callback')
                 and row['boundary'] == 'end']
    callback_last = {name: next((row['seconds'] for row in reversed(callbacks)
                                if row['function'] == name), None)
                     for name in ('_observe_event', 'at_callback')}
    baseline = json.loads((S / 'baseline/summary.json').read_text())
    before_phases = {(row['phase'], row['call']): row['seconds'] for row in baseline['profiles']}
    tests = {}
    public_errors = []
    for name in ('one-stat-committed-tests', 'one-stat-registration', 'one-stat-focused', 'one-stat-public'):
        path = S / (name + '.xml')
        if path.exists():
            cases = ET.parse(path).getroot().findall('.//testcase')
            tests[name] = {'tests': len(cases), 'failures': sum(row.find('failure') is not None for row in cases),
                           'errors': sum(row.find('error') is not None for row in cases)}
            if name == 'one-stat-public':
                public_errors = [node.get('message', '') for row in cases
                                 for node in list(row) if node.tag in ('failure', 'error')]
    public_status = ('finished' if events[-1].get('boundary') == 'pytest_end' else 'in progress or externally interrupted')
    if 'one-stat-public' in tests:
        public_status = 'failed' if public_errors else 'passed'
    broad_log = (S / 'one-stat-focused.log').read_text()
    broad_bound = next((json.loads(line[line.index('{'):]) for line in reversed(broad_log.splitlines())
                        if '{"command"' in line), None)
    light_spans = [row for row in events if row.get('function') == '_light_live' and row['boundary'] == 'end']
    preparation = [row['seconds'] for row in events if row.get('function') == 'make_case' and row['boundary'] == 'end']
    artifacts = {name: [str(path) for path in (S / 'one-stat-public').rglob(name)
                        if path.is_file() and path.stat().st_size]
                 for name in ('subscription-dispatched.json', 'actual-result.json')}
    result = {'source_commit': '87e2269f01ebec5be636cf739f85d4d7ad56d212', 'public_status': public_status,
              'source_sha256': hashlib.sha256((ROOT / 'src/data_sheets_schema/native_environment_manifest.py').read_bytes()).hexdigest(),
              'before': profile(S / 'light-clean/light.pstats'),
              'after': profile(S / 'one-stat-profile-final/light.pstats'),
              'wall': rows(S / 'one-stat-wall-final.log')[0], 'tests': tests, 'phases': spans,
              'capture_to_launch': launch - capture if capture else None,
              'capture_to_guard_admission': dispatch[0]['wall_ns'] / 1e9 - capture if dispatch and capture else None,
              'capture_to_pytest_end': events[-1]['wall_ns'] / 1e9 - capture
                  if capture and events[-1].get('boundary') == 'pytest_end' else None,
              'public_errors': public_errors,
              'callback_spans': callbacks, 'last_callback_spans': callback_last,
              'broad_bound': broad_bound, 'make_case_seconds': preparation,
              'light_count': len(light_spans), 'artifacts': artifacts, 'last_event': events[-1]}
    (S / 'one-stat-summary.json').write_text(json.dumps(result, indent=2) + '\n')
    before = sum(result['before'][key] for key in ('stat', 'lstat'))
    after = sum(result['after'][key] for key in ('stat', 'lstat'))
    if before <= 0 or after <= 0:
        raise ValueError('profile does not contain expected filesystem call counters')
    text = ['# One-stat continuation: committed candidate and measured limits', '',
            f'The candidate reduces stat/lstat calls from {before} to {after}; the standalone light census took '
            f"{result['wall']['seconds']:.3f} seconds over {result['wall']['fingerprints']} fingerprints. "
            'The two-second and 1.2 calls-per-entry targets are not met. No checks or freshness limits were removed.', '',
            'Public case outcome: ' + ('; '.join(public_errors) if public_errors else public_status) + '. '
            'Dispatch was not reached, so capture-to-dispatch, final-callback observer and callback-verification times are unavailable.', '',
            'Implementation commit: ' + result['source_commit'] + '. No push, GitHub write, provider call, '
            'native binary invocation or pin rotation occurred.', '',
            'Initial path status is shared within each census pass; symlink-following stat has a separate cache. '
            'Full generation clears both caches before its deliberate metadata recapture. Nothing survives between censuses. '
            'The shared-parent traversal from helper commit 8acf20b47 is adopted and credited; its direct os.lstat change was already present.', '',
            'Preserved fresh second looks: RECORD identity after read_regular; descriptor fstat before and after payload reads; '
            'physical and alias lstat after owned and unowned reads; full metadata recapture; '
            '_require_stable_payloads; both directory stability checks; the light fingerprint loop; '
            'and final ancestor/symlink identities and link targets. These prevent the total count approaching one per entry. '
            'importlib.metadata distribution.files also performs its own existence stats; these were not monkeypatched.', '',
            '## Public correction', '',
            'Status: ' + public_status + '.', '',
            'First stop: _launch -> _join_subscription_authority -> SubscriptionGuard -> '
            'before_dispatch(check_only=True) -> _fresh, at the later rejoin after accept_current_selection. '
            'The exact refusal timestamp was not instrumented; the observed stale check exceeds the unchanged 1200-second limit.', '',
            'Completed make_case: ' + ', '.join(seconds(value) for value in preparation) + '.', '',
            'Capture to launch: ' + seconds(result['capture_to_launch']) + '. Capture to completed guard admission: '
            + seconds(result['capture_to_guard_admission']) + '. Unavailable means the boundary was not reached. '
            'Guard admission is before child spawn and is not an exact process-dispatch timestamp.', '',
            'Ignore-independent recursive artifact search: ' + json.dumps(artifacts) + '.', '',
            'Capture to pytest-end envelope: ' + seconds(result['capture_to_pytest_end']) +
            '. This includes failure reporting and teardown and is not dispatch latency.', '',
            'Nested phase times follow; do not sum overlapping rows.', '',
            '| Phase | Call | Baseline seconds | Candidate seconds |', '| --- | ---: | ---: | ---: |']
    counts = Counter()
    for row in spans:
        counts[row['phase']] += 1
        prior = before_phases.get((row['phase'], counts[row['phase']]))
        prior_text = f'{prior:.3f}' if prior is not None else 'not reached'
        text.append(f"| {row['phase']} | {counts[row['phase']]} | {prior_text} | {row['seconds']:.3f} |")
    text += ['', 'Last completed observer and callback-verification spans, in seconds: ' + json.dumps(callback_last) + '.', '',
             'Callback observer and verification spans are retained in one-stat-summary.json. '
             'An empty list means those boundaries were not reached; no callback duration is inferred.', '',
             '## Validation and review', '',
             '; '.join(name + ': ' + str(row['tests']) + ' tests, ' + str(row['failures']) + ' failures, '
                       + str(row['errors']) + ' errors' for name, row in tests.items()) + '.', '',
             'The fixture syscall-count witness requires exactly one initial read and one final read per ordinary payload. '
             'Additional witnesses reject cross-census size changes and same-size edits during the final check.', '',
             'Collection: ' + next(line for line in (S / 'one-stat-collection.log').read_text().splitlines()
                                   if 'tests collected,' in line) + '. The three FAIRSCAPE collection errors are expected.', '',
             'The initial broad suite overlapped source edits and is diagnostic only; its failures are not a committed-source verdict. '
             'It hit the 600-second external bound with return code 124, without a complete JUnit report. '
             'The separate committed registration rederivation passed; use that and the focused committed suite above. '
             'An argument-order error in the standalone profiler accidentally began '
             'preparation against dirty source and refused at require_committed before launch. Evidence is preserved in '
             'one-stat-invalid-preparation and one-stat-profile.log; the corrected standalone run is one-stat-profile-retry.log. '
             'The profiler now rejects an invalid mode or relative output path before creating output.', '',
             'Review findings for the lead issue ledger, since helper GitHub writes are forbidden: the performance targets remain unmet; '
             'the diagnostic accepted a swapped output/mode pair (fixed); DirEntry symlink-following could duplicate the followed stat '
             '(fixed by routing it through the census status helper).', '',
             'The final standalone profile, unprofiled measurement and public case all use the committed candidate. '
             'Host load and concurrent local tests differ across measurements, so the wall-time ratio is not a controlled speedup.', '',
             'Evidence root: ' + str(S) + '. JSON summary, public events, public log/XML, committed test log/XML, '
             'collection log, standalone profile and wall log are retained there. '
             'Pin proposal is one-stat-pins.json; protected files remain intact and the scanner source pin needs lead integration.', '',
             'Reproduce this section with scripts/adhoc/report_one_stat_20261116.py. '
             'Public execution used scripts/adhoc/measure_committed_census_20261115.py through the external process-group watchdog '
             'in scripts/adhoc/profile_public_stale_20261115.py, bounded to 3600 seconds. No inherited alarm.', '']
    text += ['The implementation and measurement helpers are committed in 87e2269f0. '
             'Git refused the worktree index lock when adding the report generator. Per the lead instruction, '
             'the failed add/commit command was not retried or escalated. The lead must commit the remaining file: '
             + str(ROOT / 'scripts/adhoc/report_one_stat_20261116.py') + '.', '']
    required = [S / name for name in (
        'one-stat-public.log', 'one-stat-public.xml', 'one-stat-public-events.jsonl',
        'one-stat-committed-tests.log', 'one-stat-committed-tests.xml',
        'one-stat-registration.log', 'one-stat-registration.xml', 'one-stat-collection.log',
        'one-stat-focused.log', 'one-stat-pins.json', 'one-stat-profile-final/light.pstats',
        'one-stat-wall-final.log', 'one-stat-summary.json')]
    for path in required:
        if not path.is_file() or not path.stat().st_size:
            raise ValueError('missing or empty evidence: ' + str(path))
    text += ['Source SHA-256: ' + result['source_sha256'] + '.', '',
             'Evidence files verified nonempty:', ''] + ['- ' + str(path) for path in required]
    section = '\n'.join(text)
    if chr(64) in section:
        raise ValueError('forbidden character in handoff')
    (S / 'one-stat-report.md').write_text(section)
    old = HANDOFF.read_text()
    marker = '# Candidate reduces path overhead; launch freshness remains unresolved'
    old = old[old.index(marker):]
    HANDOFF.write_text(section + '\n---\n\n' + old)
    print(str(HANDOFF))
    print(hashlib.sha256(HANDOFF.read_bytes()).hexdigest())


if __name__ == '__main__':
    main()
