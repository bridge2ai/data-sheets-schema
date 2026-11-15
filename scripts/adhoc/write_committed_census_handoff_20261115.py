"""Write the lead's committed-census measurement handoff, 2026-11-15.

Inputs: saved measurement summary, phase tables and existing handoff.
Output: a new answer-first section in the assigned shared handoff.
"""
import hashlib
import json
from pathlib import Path

root = Path(__file__).resolve().parents[2]
scratch = root.parent / 'scratch-public-stale-20261115'
out = scratch / 'committed-after'
public = scratch / 'committed-public-retry'
handoff = root.parent / 'codex-development-efficiency-20261111/notes/development_efficiency_20261111/handoffs/codex-public-stale-20261115.md'
summary = json.loads((out / 'summary.json').read_text())
comparison = summary['comparison']
intervals = summary['public_intervals']
public_make = next(row['seconds'] for row in summary['public_measurements']
    if row.get('function') == 'make_case' and row['boundary'] == 'end')
manifest = root / 'src/data_sheets_schema/native_environment_manifest.py'
pin = hashlib.sha256(manifest.read_bytes()).hexdigest()
marker = '# Committed census measured: preparation faster, public correction still refuses stale observation'
body = f'''{marker}

Complete make_case passed in {comparison['after_seconds']:.3f} seconds versus the saved {comparison['before_seconds']:.3f} second baseline: {comparison['reduction_seconds']:.3f} seconds less, or {comparison['reduction_percent']:.2f} percent. Both runs made 57 manifest verify calls and 59 light census calls. The public correction case failed before dispatch with `ValueError: subscription observation is stale or future-dated`. The census correction alone does not resolve the public stale-launch failure on this host.

There is no capture-to-dispatch interval: dispatch never occurred. The final-callback observer time, final callback verification time and late advance time are unavailable because those stages were not reached. This run cannot establish that Tier A clears the 120 second observer or 125 second response windows.

Source measured: {(out / 'source-commit.txt').read_text().strip()}. Manifest SHA-256, recomputed for this handoff: `{pin}`. Production source, tests, pins, capture order, freshness values, windows and deadlines were unchanged. No source change is proposed or committed in this continuation.

The public run separately completed its fresh make_case in {public_make:.3f} seconds. JUnit records one failed testcase in {summary['public_test']['seconds']:.3f} seconds; pytest's complete session summary reports 2007.95 seconds. The external watchdog recorded 2013.621 seconds and return code 1, within its 3600 second bound. This was an ordinary test failure, not an external timeout.

First stop: `launch_case -> synthetic_launch -> _launch -> _join_subscription_authority -> SubscriptionGuard.__init__ -> before_dispatch(check_only=True) -> _fresh`. The traceback points to native_execution_orchestration.py line 379 and native_subscription_guard_v2.py line 460. This is the rejoin immediately after accept_current_selection, before reservation and dispatch. There is no final result or published first_stop field; the first uncaught exception above is the observed stop.

The immutable observation was captured at {intervals['capture_timestamp']}. Its age at launch entry was {intervals['capture_to_launch_seconds']:.3f} seconds. At the last saved current-authority completion it was {intervals['capture_to_last_authority_end_seconds']:.3f} seconds; at pytest end it was {intervals['capture_to_pytest_end_seconds']:.3f} seconds. The exact refusal timestamp was not instrumented. The chronological evidence and stale check bound the refusal age above the unchanged {summary['guard_max_age_seconds']} second limit and no later than the pytest-end envelope; do not label that envelope as dispatch age. Launch entry to pytest end was {intervals['launch_to_pytest_end_seconds']:.3f} seconds, including failure reporting and teardown. The standalone phase run's capture-to-ready interval was {summary['capture_to_ready_seconds']:.3f} seconds, also not a dispatch measurement.

Saved launch phase costs:

{(out / 'launch-phases.md').read_text()}
The repeated registration checks and controller prewarm remain substantial. Recommendation for the lead: retain the stale-launch finding and profile those launch phases next. This is a measured follow-up recommendation, not authorization to remove checks or extend freshness. No extra public canary or expensive matrix was run after the failure.

Complete preparation phase comparison:

{(out / 'phases.md').read_text()}
The reduction from four full generations to two is consistent with the accepted publication memo seeding; verification and live census counts are unchanged. Both measurements use the same isolated Python 3.13 environment and phase profiler, but changing host contention prevents treating the ratio as a controlled benchmark. The primary venv was untouched.

Host load: standalone one-minute samples ranged from {summary['host_load_samples']['committed-after']['minimum_one_minute']:.2f} to {summary['host_load_samples']['committed-after']['maximum_one_minute']:.2f}; public samples ranged from {summary['host_load_samples']['committed-public-retry']['minimum_one_minute']:.2f} to {summary['host_load_samples']['committed-public-retry']['maximum_one_minute']:.2f}. Public start averages were 16.36, 18.84 and 17.67. The saved samples include a 34.64 one-minute load. Process inspection was sandbox-blocked, so activity cannot be attributed to Codex tab 196. This helper ran each measurement sequentially without xdist workers or subagents.

Diagnostic limitation and retained failed attempt: the first public harness attempt failed before fixture preparation because PY_UNWIND is not a valid local monitoring event. Its logs and JUnit are preserved under {scratch / 'committed-public'}. Only the new diagnostic helper was corrected to use local PY_RETURN. The real public rerun above used a fresh scratch directory and retained the existing profile-stability guard. It observed entry/normal return events without replacing any production function. An exceptional launch exit has no normal-return duration, which is why the handoff uses saved pre-dispatch steps and the explicitly labelled pytest-end envelope.

Evidence:

- {out / 'run.log'}
- {out / 'phases.jsonl'}
- {out / 'summary.json'}
- {out / 'phases.md'}
- {out / 'launch-phases.md'}
- {public / 'run.log'}
- {public / 'result.xml'}
- {public / 'timing.jsonl'}
- {summary['pre_dispatch_files'][0]}
- Host samples: {out / 'host-start.txt'} and {public / 'host-start.txt'}.

An ignore-independent search of the public scratch tree found no host-controller-timing.jsonl, subscription-dispatched.json or actual-result.json. The summary producer independently checks the missing dispatch marker and controller timing file. Its JSON records hashes of the direct logs, JUnit, immutable guard and pre-dispatch timing evidence.

Reproduce the tables and summary from the worktree root:

```text
{scratch / 'isolated-venv/bin/python3.13'} scripts/adhoc/summarize_committed_census_20261115.py {scratch}
```

Exact watchdog child command arrays and elapsed/return values are saved in each run.log. The standalone bound was 2400 seconds; the public bound was 3600 seconds. No inherited alarm was used. No native binary, provider, production capture, production launch, GitHub write or push occurred. Earlier focused-test and collection results below were not rerun in this measurement-only continuation.

New diagnostic helpers left uncommitted as instructed:

- scripts/adhoc/measure_committed_census_20261115.py
- scripts/adhoc/summarize_committed_census_20261115.py
- scripts/adhoc/write_committed_census_handoff_20261115.py

No commit was attempted. The lead owns integration and any issue publication.
'''
assert chr(64) not in body
old = handoff.read_text()
assert not old.startswith(marker), 'preserve the existing measurement handoff'
handoff.write_text(body + '\n<!-- prior handoff -->\n' + old)
assert handoff.stat().st_size and chr(64) not in handoff.read_text()
print(handoff)
print(hashlib.sha256(handoff.read_bytes()).hexdigest())
