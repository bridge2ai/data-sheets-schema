"""Issue 6233, 2026-11-14: assemble the measured callback-growth handoff.

Inputs: persisted baseline, callback summaries, profiles, persistence checks.
Outputs: assigned Markdown handoff and a JSON manifest of verified file hashes.
This reports the design stop explicitly; it never claims an implemented fix.
"""
import hashlib
import json
from pathlib import Path
import subprocess
import sys

root = Path(__file__).resolve().parents[2]
scratch = Path(sys.argv[1]).resolve(strict=True)
handoff = Path(sys.argv[2]).resolve(strict=True)
profile_case = scratch / 'omissions-profile-canary'
summary = json.loads((scratch / 'callback-summary.json').read_text())
baseline = json.loads((scratch / 'baseline-verification.json').read_text())
costs = json.loads((profile_case / 'function-costs.json').read_text())
persistence = json.loads((profile_case / 'timing-persistence-verification.json').read_text())
correction = next(case for case in summary if case['case'] == 'correction-canary2')
omissions = next(case for case in summary if case['case'] == 'omissions-profile-canary')
callbacks = [row for row in costs['callbacks'] if not row['unwound']]
profiled = [row for row in callbacks if row.get('cprofile_enabled')]
assert {row['calls'] for row in profiled} >= {18, 19}, 'two selected observer profiles are required'
assert (profile_case / 'exit-status.txt').is_file(), 'do not report a running measurement as complete'
baseline_snapshot = scratch / 'baseline-handoff-before-fix.md'
if not baseline_snapshot.exists():
    baseline_snapshot.write_bytes(handoff.read_bytes())

evidence = [scratch / name for name in (
    'callback-summary.json', 'callback-summary.md', 'baseline-verification.json',
    'baseline-handoff-before-fix.md', 'saved-boundary.json', 'host-load-during-canary.txt')]
evidence += [profile_case / name for name in (
    'callback-cpu.jsonl', 'function-costs.json', 'function-costs.md',
    'timing-persistence-verification.json', 'exit-status.txt', 'command.txt',
    'diagnostic-source.sha256', 'case/actual-result.json')]
evidence += [Path(profile['path']) for profile in costs['profiles']]
evidence += sorted(root.glob('scripts/adhoc/*callback*20261114*'))
source_refs = [root / ('src/data_sheets_schema/' + name) for name in (
    'native_shared_capture.py', 'native_shared_capture_orchestration.py',
    'native_shared_controller_orchestration.py', 'native_shared_stage/__init__.py',
    'native_shared_receipts.py', 'native_catalog_reuse.py', 'native_execution_authority_v2.py')]
context = handoff.parent.parent / 'assignments/claude-lead-helper-context-20261113.md'
evidence += source_refs + [context]
for path in evidence:
    assert path.is_file() and path.stat().st_size, str(path)
manifest = {str(path): hashlib.sha256(path.read_bytes()).hexdigest() for path in evidence}
manifest_path = scratch / 'handoff-evidence-sha256.json'
manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + '\n')
head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root, text=True).strip()
peak = baseline['largest_callbacks'][0]
fit = correction['fits']['_observe_event']
measured_functions = []
for row in callbacks:
    value = row.get('functions', {}).get('native_shared_capture.py:_checked_observations')
    if value:
        measured_functions.append((row['calls'], value['thread_cpu'], row.get('cprofile_enabled', False)))

text = f"""Yes: per-callback observer CPU grows with history. Repeated observation and stage reconstruction contributes to the growth; contention alone is not the explanation. No production fix was applied: this handoff stops at the verifier-state design decision required by the helper context. Public results: correction failed at the synthetic attempt deadline; the omissions API profiling diagnostic is reported separately below and is not a public pytest result; omissions and pending public tests were not run after a fix because there is no fix.

The baseline was written to this handoff before any production edit. Its preserved snapshot is {baseline_snapshot}. The source candidate remains a3da7fcb20661e9d2bd4029300e504574d91569c; current local head is {head}. Only diagnostic scripts were authored. No protected file, controller source, manifest, pin, deadline or acceptance rule changed. No GitHub write or push occurred. No pin rotation is proposed.

Measured answer

Correction PreToolUse observers 1–10 took {baseline['early_observer_cpu_min']:.6f} to {baseline['early_observer_cpu_max']:.6f} thread CPU seconds. The largest was callback {peak['calls']}: {peak['thread_cpu']:.6f} CPU seconds and {peak['wall']:.6f} wall seconds. The descriptive linear fit across the observed correction callbacks is {fit['slope_cpu_seconds_per_callback']:.6f} CPU seconds per callback index, with R squared {fit['r_squared']:.6f}. Stage transitions make this a descriptive trend, not a universal scaling law. Do not extrapolate this short run into a safe hundreds-of-calls budget.

The baseline verifies {baseline['verified_timing_rows']} independent metric rows against exact transcript lines and tool identities. Tables below contain thread CPU, process CPU, wall time and repeated capture counts. The classifier remains much smaller than the observer. Ordered assistant and tool-result observer barriers can also delay the next permission response; they are shown separately and must not be charged to the preceding permission grant.

Function evidence

The omissions diagnostic measures inclusive thread CPU in Admission.reconstruct, _loaded and _checked_observations. It profiles actual NativeControl._observe_event and _classify_frame for indices 18 and 19, selected because those were the two largest PreToolUse observers in the correction baseline. These are corresponding callbacks in a fresh omissions run, not a rerun of the exact correction invocation. The profile tables report elapsed time and call counts; independent thread clocks report CPU. Profiler overhead is included in profiled rows, which are excluded from slope fits. Nested inclusive times overlap and must not be summed.

The selective span instrumentation matches native_shared module basenames; stage functions in __init__.py are therefore absent from the span table. Their actual calls remain visible in cProfile. An absent selective span is not a zero cost. The installed profiler also records concurrent controller service activity, and its cumulative elapsed values contain inconsistent parent/child totals. Those raw values are preserved but are not reliable function cost allocation. Use the call counts to identify repeated work and the independent monitoring clocks for CPU comparisons. A clean thread-isolated function timing profile remains outstanding.

The code path explains the growth: _loaded calls _checked_observations over every durable observation; old advance_settled observations invoke _check_advance_acknowledgement; that function reconstructs before and after stage histories through _Replay, _check_response and _decision_at. _phase_state separately reconstructs the current decision on every event. _history_prefix also enumerates historical journal prefixes with only per-capture reuse. Exact function profiles below quantify the observed calls without attributing all wall delay to CPU.

Evidence and diagnostic limitations

Saved attempts were read only. The cold constructor probe stopped at get_type_hints with NameError for ArtifactPin before observation; this is not claimed as a production defect. Separately, the live adapter uses one-use admission and initialization and publishes into the saved absolute stage paths. Safely calling it on those spent, read-only attempts would require a new admission boundary. The assignment's fresh synthetic fallback was used. It calls the real controller observer and classifier with the ordinary Python synthetic peer, without a provider, model or native executable.

The first diagnostic failed before pytest because a PY_UNWIND monitoring callback returned an unsupported DISABLE value. The corrected correction diagnostic ran the actual public test, but its combined host timing file was damaged by the diagnostic opening a second append descriptor while the original controller descriptor was not append-only. The independent CPU JSONL is intact and checked against the transcript. The damaged file is preserved and is not presented as repaired evidence. That first version did not count live transcript extents; the table says not instrumented.

The omissions diagnostic uses the controller's Timing.record method and its persistence was verified. Any after-close supplement is explicitly labelled callback_cpu_after_close and records when it was appended after process exit; it does not pretend to be an original controller completion timestamp. The verification document is {profile_case / 'timing-persistence-verification.json'}. Exact contents: {json.dumps(persistence, sort_keys=True)}.

The correction launcher itself returned status 2 after pytest finished because the executing shell script was edited while Bash was still consuming it. Its recovered wrapper status is separate from the actual pytest failure. The omissions launcher and measurement script were left unchanged throughout their run, and its saved source hash identifies the instrument used. Read-only diagnostic review found the timing-writer collision, running-launcher edit, missing selective stage spans and concurrent cProfile aggregation limitation documented here. Review also found that the after-close supplement checker initially verified only append length and preservation of old bytes; it now rereads and compares every persisted measurement field. No GitHub issues were filed because helper GitHub writes are prohibited; these findings are handed to the lead for issue tracking.

Design decision and recommendation

The helper context at {context} says: “If a task needs a design decision, stop there and report the choice with your recommendation.” The required decision is the lifetime and validator-state identity of a new verified-prefix owner. An exact evidence hash proves unchanged bytes; it does not alone prove that the same effective validator, mutable limits and grammar settings would still accept them. The existing native_catalog_reuse.runtime_token covers catalog producers, not the full observation/stage validator graph. module_source_identity explicitly does not prove arbitrary interpreter globals. Reusing that token for acceptance checkpoints would claim a guarantee it does not provide.

Recommendation: introduce a separate bounded prefix owner tied weakly to the active Admission, with a closed validator-state guard. Do not place verified observations, stage decisions or acceptance results in _ReceiptCatalogContext. Keep fresh admission reconstruction and source/pin checking on every callback. Before reuse, read and hash all accepted earlier stream bytes and every referenced artifact again, and prove the journal-record and observation sequences extend the exact prior prefixes. Reject changed earlier bytes, including coherently rehashed replacement histories. A verifier-state change must discard semantic checkpoints and fully reverify while retaining earlier byte anchors, so invalidation cannot silently accept replaced evidence.

Resume causal observation state only for the new suffix. Add compact completed-stage checkpoints and exact-input packet/request derivations, so a new observation does not replay all old stages. Bound storage linearly; do not save a full replay/history snapshot per stage or every complete journal prefix. The canonical journal changes its head field on append, so its whole-file hash is not a simple extendable transcript hash. Standalone helpers, saved evidence and final completion should retain independent full replay.

Required follow-up tests: unchanged prefix plus valid extension equals full replay; old transcript, control, journal, stage, observation and response mutations are refused at the next real callback; coherently rehashed old histories also fail; new suffix failures never commit a checkpoint; source/validator/limit changes trigger refusal or full revalidation; memory remains bounded; semantic work tracks only newly verified records while fresh byte-read counts remain complete. Then run correction, omissions and pending public tests alone using the same launcher nodes and unchanged deadlines. None of these fix-specific claims is verified here.

Canary recommendation: do not interpret this run as evidence that a long native canary fits the 125-second window. The observed CPU growth needs the prefix fix and its mutation tests first. All assignment work after this design stop remains outstanding; this is not a completed fix or a three-test pass.

Reproduction and artifacts

Use the assigned interpreter and PYTHONPATH with scripts/adhoc/run_callback_growth_20261114.sh. The diagnostic invocation is saved in {profile_case / 'command.txt'}. Run summarize_callback_growth_20261114.py on {scratch}, summarize_callback_profiles_20261114.py on {profile_case}, and verify_callback_timing_persistence_20261114.py on the same case. This handoff is generated by write_callback_growth_handoff_20261114.py. Every table below comes from the saved JSON through those scripts. File existence and SHA-256 values are recorded in {manifest_path}. The scripts are retained on the assigned local branch for the lead to review and publish.

"""
text += (scratch / 'callback-summary.md').read_text()
text += '\nFunction measurements and real cProfile tables\n\n'
text += (profile_case / 'function-costs.md').read_text()
assert chr(64) not in text
handoff.write_text(text)
assert handoff.stat().st_size
print(json.dumps({'handoff': str(handoff), 'sha256': hashlib.sha256(handoff.read_bytes()).hexdigest(),
                  'evidence_manifest': str(manifest_path), 'profiled_observers': [r['calls'] for r in profiled],
                  'correction_results': correction['results'], 'omissions_diagnostic_results': omissions['results']}, indent=2))
