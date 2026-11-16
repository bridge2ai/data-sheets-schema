"""Write evidence-backed launch-cost handoff for the Claude lead, 2026-11-16.

Inputs: saved profiles, events, test logs and candidate diff. Outputs: metrics
JSON and the assigned handoff. No GitHub writes or source/pin changes.
"""
from collections import Counter
from datetime import datetime
import hashlib
import json
from pathlib import Path
import pstats
import subprocess
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
S = ROOT.parent / 'scratch-launch-cost-20261116'
H = ROOT.parent / 'codex-development-efficiency-20261111/notes/development_efficiency_20261111/handoffs/codex-launch-cost-20261116.md'


def main():
    data = json.loads((S / 'baseline/summary.json').read_text())
    events = [json.loads(line) for line in (S / 'baseline/events.jsonl').read_text().splitlines()]
    entry = next(row for row in events if row['event'] == 'launch_entry')
    error = next(row for row in events if row['event'] == 'launch_error')
    captured = datetime.fromisoformat(entry['guard']['captured_at'].replace('Z', '+00:00')).timestamp()
    before = json.loads((S / 'light-clean/result.json').read_text())['seconds']
    after = json.loads((S / 'light-final/result.json').read_text())['seconds']
    wall = json.loads((S / 'light-wall-final.log').read_text().splitlines()[0])
    factor = after / before
    lights = [row for row in events if row['event'] == 'call_end' and row.get('function') == '_light_live' and row.get('phase') == 'launch']
    light_seconds = sum(row['seconds'] for row in lights)
    projected_prefix = error['time'] - captured - light_seconds * (1 - factor)
    profiles = {}
    for name, relative in [('before', 'light-clean/light.pstats'), ('after', 'light-final/light.pstats')]:
        stats = pstats.Stats(str(S / relative))
        profiles[name] = {'total_calls': stats.total_calls,
            'stat_calls': sum(value[1] for key, value in stats.stats.items()
                              if key[2] in ('<built-in method posix.stat>', '<built-in method posix.lstat>')),
            'hash_calls': {key[2]: value[1] for key, value in stats.stats.items()
                           if 'hashlib' in key[2] or "'digest'" in key[2] or "'hexdigest'" in key[2]}}
    authority_span = next(row for row in data['profiles'] if row['phase'] == '_current_authority')
    authority_light = sum(row['seconds'] for row in lights if authority_span['start'] <= row['time'] <= authority_span['end'])
    projected_authority = authority_span['seconds'] - authority_light * (1 - factor)
    metrics = {'capture_to_launch': entry['time'] - captured,
        'launch_to_error': error['time'] - entry['time'], 'capture_to_error': error['time'] - captured,
        'census_profile_before': before, 'census_profile_after': after, 'census_wall_after': wall,
        'launch_light_calls': len(lights), 'launch_light_seconds': light_seconds,
        'profile_ratio': factor, 'projected_capture_to_same_failure_boundary': projected_prefix,
        'profiles': profiles, 'conditional_capture_before_reservation': projected_prefix + projected_authority}
    (S / 'metrics.json').write_text(json.dumps(metrics, indent=2) + '\n')
    junit = ET.parse(S / 'focused-final.xml').getroot()
    suites = list(junit.iter('testsuite'))
    tests = sum(int(row.attrib['tests']) for row in suites)
    failures = sum(int(row.attrib['failures']) + int(row.attrib['errors']) for row in suites)
    statuses = [json.loads(line) for line in (S / 'ci-public-status.jsonl').read_text().splitlines()]
    source = ROOT / 'src/data_sheets_schema/native_environment_manifest.py'
    source_hash = hashlib.sha256(source.read_bytes()).hexdigest()
    lines = [
        '# Candidate reduces path overhead; launch freshness remains unresolved', '',
        f'The two-second census target is not met: the final candidate took {wall["seconds"]:.3f} seconds without a profiler. '
        f'The unchanged baseline failed before dispatch at an observation age of {metrics["capture_to_error"]:.3f} seconds. '
        f'The final candidate passes {tests} focused tests with {failures} failures or errors. '
        'The candidate is left for lead review, not claimed as a launch fix.', '',
        'Git refused the worktree index lock for the candidate. No full after-launch run was attempted against dirty source: '
        'the launch path requires committed source authority. No pins were rotated. The proposal tool identifies a scanner-source pin update, '
        'so integration and any reuse decision remain with the lead. No push, GitHub write, provider call or native binary invocation occurred.', '',
        '## Measurements and limits', '',
        f'Capture-to-launch: {metrics["capture_to_launch"]:.3f} seconds. Launch-entry to observed exception: '
        f'{metrics["launch_to_error"]:.3f} seconds. Capture-to-exception: {metrics["capture_to_error"]:.3f} seconds against '
        f'the unchanged {entry["guard"]["max_age_seconds"]} second maximum. These are failure-boundary measurements, not dispatch times. '
        'The stop was accept_current_selection -> load_current -> load_guard -> SubscriptionGuard -> before_dispatch(check_only=True) -> _fresh.', '',
        'An ignore-independent search of the baseline case found the pre-dispatch timing file but no subscription-dispatched marker or actual-result file. '
        'The baseline reaches six outer registration checks and one current-authority span; the prior assignment records seven and two because '
        'its failure occurred after capture acceptance at the subsequent join. Unreached checks have no timings in this run.', '',
        '| Census measurement | Before | Final candidate |', '| --- | ---: | ---: |',
        f'| Clean cProfile wall seconds | {before:.3f} | {after:.3f} |',
        f'| Total profiled calls | {profiles["before"]["total_calls"]} | {profiles["after"]["total_calls"]} |',
        f'| Combined stat and lstat calls | {profiles["before"]["stat_calls"]} | {profiles["after"]["stat_calls"]} |',
        f'| Unprofiled standalone seconds | Not measured | {wall["seconds"]:.3f} |', '',
        'The first sampled baseline census took ' + f'{next(row["seconds"] for row in events if row["event"] == "call_end" and row.get("function") == "_light_live"):.3f}' +
        ' seconds. Profiling and host contention differ between measurements; the cProfile ratio is not a controlled speedup claim. '
        'The original post-launch profile included sampler-thread activity and is retained under baseline/light-profile.txt; use light-clean and light-final for deterministic comparison.', '',
        '## Phase costs and explicitly estimated after values', '',
        'There is no measured after value for any launch phase. The table estimates each observed phase by replacing only its light-census time '
        'with that time multiplied by the standalone cProfile after/before ratio. Other work is held constant. Nested spans overlap and must not be added. '
        'This is a sensitivity calculation, not a dispatch forecast.', '',
        '| Phase | Call | Before seconds | Estimated after seconds |', '| --- | ---: | ---: | ---: |']
    for span in data['profiles']:
        if span['phase'] == 'one_light_census':
            continue
        enclosed = sum(row['seconds'] for row in lights if span['start'] <= row['time'] <= span['end'])
        estimate = span['seconds'] - enclosed * (1 - factor)
        lines.append(f'| {span["phase"]} | {span["call"]} | {span["seconds"]:.3f} | {estimate:.3f} |')
    lines.extend(['', f'The same calculation gives {projected_prefix:.3f} seconds from capture to the observed failure boundary, '
        f'using {len(lights)} light censuses totaling {light_seconds:.3f} seconds during launch. '
        'Any additional work required to reach dispatch is excluded. A defensible full capture-to-dispatch estimate remains unavailable; '
        'the lead needs a committed candidate and fresh end-to-end measurement. '
        f'If the unreached second current-authority check costs the same as the modeled reached check, the projected age is already '
        f'{projected_prefix + projected_authority:.3f} seconds before reservation, with dispatch work still excluded. '
        'This conditional scenario exceeds the freshness limit; it is not an observed result. The two-second target and freshness closure remain open.', '',
        '## Stack-level costs', '',
        'Per-call leaf and inclusive stack rankings are in the generated baseline/profile.md, covering controller prewarm, classifier admission, '
        'each reached outer registration verification, current authority and one light census. The associated stacks.jsonl contains complete sampled stacks. '
        'Sampling fractions are not exact self times and may favor calls that release the interpreter lock.', '',
        '| Phase | Call | Main census stack fraction | Top leaf | Leaf fraction |', '| --- | ---: | ---: | --- | ---: |'])
    for row in data['profiles']:
        count = dict(row['inclusive']).get('native_environment_manifest.py:_light_live', 0)
        leaf, leaf_count = row['leaves'][0]
        lines.append(f'| {row["phase"]} | {row["call"]} | {count / row["samples"]:.3f} | {leaf} | {leaf_count / row["samples"]:.3f} |')
    lines.extend(['', '## Verification boundaries and reuse proposals', '',
        'The original seven outer registration calls protect, in order: public entry before profile/runtime/attempt selection; '
        'the fixed generic engine before capabilities; the common launch body before authorization; current capture authority inspection; '
        'unchanged execution/evidence before admission; '
        'current capture acceptance after controller prewarm; and the later current-authority rejoin before reservation. '
        'This run reaches the first six and fails during acceptance, so the final rejoin is absent. The exact observed caller stacks are retained in events.jsonl.', '',
        'For the 57 preparation manifest verifications: two write-publication checks verify the just-written pin and seed the full memo; '
        '19 environment-pin checks bind the supplied manifest to the preparation inputs; 19 final preparation checks recheck the environment after rendering '
        'and selected-input/source rereads, split between five ordinary and fourteen synthetic preparations; 17 verify_preparer checks validate the submitted '
        'environment before reconstructing its preparation. The generated caller-inventory table in baseline/profile.md records these counts directly. '
        'During this launch, repeated reconstruction contributes 18 calls at each of environment-pin, final synthetic preparation, and verify_preparer, '
        'plus two full-mode recheck_verified calls at controller boundaries.', '',
        'No whole-verification reuse is justified merely by equal registration bytes: other processes can change the filesystem between synchronous calls. '
        'The before/after preparation checks intentionally detect those changes. Do not collapse them into a passed flag.', '',
        'Propose only invocation-local reuse of pure parsing/canonicalization of the same immutable bytes, with all live reads, stat comparisons, '
        'RECORD hashing and mode checks retained. Proof obligations: exact raw-byte equality and parser/limit identity; no mutable parsed object escaping '
        'or aliasing a caller; no widening across source-loader, classifier, admission or callback lifetimes; identical malformed-input refusals; '
        'all live filesystem checks still occur in their original order. A frozen intermediate value or private defensive copy is needed. '
        'No such reuse was implemented. Any broader verification token requires a separate lead design decision and mutation adversaries.', '',
        '## Implementation, review and validation', '',
        'The resolver retains normalized public Path input/output but uses string paths for its recursive directory walk and memo. '
        'Ancestor and symlink identities and final checks are unchanged. _lstat now calls os.lstat directly. No census result is reused across calls. '
        'The ancestor-count witness observes the syscall rather than the former Path method and keeps the same assertions. '
        'The local census canary accepted the same saved manifest before and after. Aggregate stat/lstat and hashing-call counts are identical, '
        'as recorded in metrics.json; this does not exercise all concurrent mutation schedules or establish launch freshness.', '',
        'Read-only review finding for the lead issue ledger: os.path.isdir suppresses a broader set of errors than the original Path.is_dir on this runtime. '
        'The draft optimization used it for the symlink-target directory probe; the final candidate restores Path.is_dir. '
        'This is addressed in the candidate. No GitHub issue was filed because the helper assignment forbids GitHub writes. '
        'A separate open finding is that the speedup does not meet the two-second target or establish freshness closure.', '',
        f'Final candidate source SHA-256, computed from disk: {source_hash}.', '',
        f'Focused suite: {tests} tests, {failures} failures or errors. See focused-final.log and focused-final.xml. '
        'Collection: ' + next(line for line in (S / 'collection.log').read_text().splitlines() if 'tests collected,' in line) + '. '
        'The three expected FAIRSCAPE submodule errors are not repaired by this helper.', '',
        'Pin computation command: python3 /Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/scripts/adhoc/compute_pin_chain_20261115.py '
        '--root ' + str(ROOT) + ' --propose --compact. Output: ' + str(S / 'pin-proposals-final.json') + '.', '',
        'All test/profile runs use the copied isolated Python environment and the external process-group watchdog in profile_public_stale_20261115.py. '
        'There is no inherited alarm. The primary environment was not changed. The isolated editable-path file has an adjacent backup named '
        'data_sheets_schema.pth.bak-launch-cost-20261116; restoring it undoes that isolated configuration change.', '',
        '## CI status', '',
        'The saved CI status at report generation is:', '', '| Case | Job | Status | Conclusion |', '| --- | ---: | --- | --- |'])
    for row in statuses:
        lines.append(f'| {row["name"]} | {row["id"]} | {row["status"]} | {row["conclusion"]} |')
    lines.extend(['', 'The early-stop condition has not been established while these jobs remain in progress. '
        'No clean-runner timing or pass is inferred from pending jobs. The direct correction job record confirms its public-test step is still running. '
        'The lead should read the completed job logs using the assignment command when available.', '',
        '## Files and reproduction', '',
        'Two diagnostic commits succeeded before index-lock refusal: ' +
        subprocess.check_output(['git', 'log', '-2', '--format=%H %s'], cwd=ROOT, text=True).strip().replace('\n', '; ') + '.', '',
        'Uncommitted files are listed in git-status.txt. The lead owns the commit and publication. No branch was merged or deleted.', '',
        'Regenerate the stack tables with the isolated Python and scripts/adhoc/summarize_launch_cost_20261116.py followed by the baseline directory. '
        'Regenerate this handoff and its metrics with scripts/adhoc/report_launch_cost_20261116.py. All tables above are generated from saved JSON or profiles.', ''])
    evidence = [S / name for name in ['baseline.log', 'baseline/events.jsonl', 'baseline/stacks.jsonl', 'baseline/profile.md',
        'baseline/summary.json', 'light-clean/light-profile.txt', 'light-final/light-profile.txt', 'light-wall-final.log',
        'focused-final.log', 'focused-final.xml', 'collection.log', 'pin-proposals-final.json', 'ci-public-status.jsonl',
        'ci-correction-job.json', 'metrics.json', 'git-status.txt', 'candidate.diff']]
    evidence += [ROOT / name for name in ['scripts/adhoc/profile_launch_cost_20261116.py', 'scripts/adhoc/summarize_launch_cost_20261116.py',
        'scripts/adhoc/optimize_census_paths_20261116.py', 'scripts/adhoc/measure_light_wall_20261116.py', 'scripts/adhoc/report_launch_cost_20261116.py',
        'src/data_sheets_schema/native_environment_manifest.py', 'tests/test_native_environment_census.py',
        'scripts/adhoc/finalize_launch_report_20261116.py']]
    for path in evidence:
        if not path.is_file() or not path.stat().st_size:
            raise ValueError('missing or empty evidence: ' + str(path))
        lines.append('- ' + str(path))
    body = '\n'.join(lines) + '\n'
    if chr(64) in body:
        raise ValueError('forbidden character in handoff')
    H.write_text(body)
    digest = hashlib.sha256(H.read_bytes()).hexdigest()
    print(str(H))
    print('SHA-256 ' + digest)
    print(json.dumps(metrics, indent=2))


if __name__ == '__main__':
    main()
