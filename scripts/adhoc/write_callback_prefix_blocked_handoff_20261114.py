"""Issue 6233, 2026-11-14: report a pre-dispatch public canary blocker.

Inputs: persisted suite, base comparison, public canary, CPU summary and pins.
Outputs: preserved previous handoffs and the assigned lead handoff. This never
turns missing public or worker evidence into a successful validation claim.
"""
import json
from pathlib import Path
import subprocess
import sys

from write_callback_prefix_handoff_20261114 import HANDOFF, junit, sha


def git(*args):
    return subprocess.check_output(['git', *args])


def main():
    scratch = Path(sys.argv[1]).resolve()
    root = Path.cwd().resolve()
    base = 'b35e264571a4e8ba6f152b7fc7053c35758d6823'
    head = git('rev-parse', 'HEAD').decode().strip()
    public = scratch / 'prefix-final-correction'
    public_result = junit(public / 'junit.xml')
    assert public_result['counts']['failures'] == 1
    assert 'subscription observation is stale or future-dated' in public_result['failures'][0]['message']
    # pathlib traversal includes hidden and ignored files; absence is exhaustive
    # within this run directory, rather than a gitignore-filtered rg miss.
    metrics = list(public.rglob('callback-cpu.jsonl'))
    assert not metrics
    assert (public / 'exit-status.txt').read_text().strip() == '1'
    pins_path = scratch / 'prefix-pin-proposal.json'
    pins = json.loads(pins_path.read_text())
    assert all(row['base'] == row['current'] for row in pins['protected'].values())
    for row in pins['sources']:
        assert sha((root / row['path']).read_bytes()) == row['current_sha256']
    suites = [junit(scratch / name) for name in (
        'prefix-final-suite-canary.xml', 'prefix-native-final.xml',
        'prefix-candidate-freshness.xml', 'prefix-base-freshness/junit.xml',
        'prefix-base-v4/junit.xml')]
    summary_path = scratch / 'prefix-final-summary.json'
    summaries = json.loads(summary_path.read_text())
    unchanged = []
    for path in ('src/data_sheets_schema/native_subscription_guard_v2.py',
                 'src/data_sheets_schema/native_subscription_admission.py',
                 'src/data_sheets_schema/native_execution_orchestration.py'):
        previous, current = sha(git('show', base + ':' + path)), sha((root / path).read_bytes())
        assert previous == current
        unchanged.append({'path': path, 'base_sha256': previous, 'current_sha256': current})
    evidence = {'head': head, 'base': base, 'public': public_result,
        'callback_metric_files': [str(path) for path in metrics],
        'unchanged_failure_path': unchanged, 'suites': suites,
        'host_load_start': (public / 'host-load-start.txt').read_text().strip(),
        'host_load_end': (public / 'host-load-end.txt').read_text().strip(),
        'public_cases': [
            {'case': 'correction', 'status': 'failed before dispatch; no callback samples'},
            {'case': 'omissions', 'status': 'not run after failed canary'},
            {'case': 'pending', 'status': 'not run after failed canary'}]}
    evidence_path = scratch / 'prefix-blocker-evidence.json'
    evidence_path.write_text(json.dumps(evidence, indent=2, sort_keys=True) + '\n')
    assert json.loads(evidence_path.read_text()) == evidence
    previous = HANDOFF.read_bytes()
    snapshot = HANDOFF.with_name(HANDOFF.stem + '-before-' + sha(previous)[:12] + '.md')
    if snapshot.exists():
        assert snapshot.read_bytes() == previous
    else:
        snapshot.write_bytes(previous)
    measurement = HANDOFF.with_name(HANDOFF.stem + '-measurement.md')
    original = HANDOFF.with_name(HANDOFF.stem + '-measurement-original.md')
    if measurement.exists() and not original.exists():
        original.write_bytes(measurement.read_bytes())
    measurement.write_bytes(previous)
    assert measurement.read_bytes() == previous
    lines = [
        'Per-callback CPU flatness is not established. Correction failed before dispatch with a stale subscription observation and produced no callback CPU records. Omissions and pending were not run after this failed canary. No pin was edited; the changed source hashes and pin proposal are below.', '',
        'Status: implementation and native-suite validation are complete; public performance and real-worker mutation validation remain blocked and this is not a completed performance claim.', '',
        'Public canary and recommendation', '',
        '| Case | Result |', '| --- | --- |']
    for row in evidence['public_cases']:
        lines.append('| ' + row['case'] + ' | ' + row['status'] + ' |')
    lines.extend(['',
        'The unchanged freshness guard raised: ' + public_result['failures'][0]['message'],
        'Public command: ' + (public / 'command.txt').read_text().strip(),
        'Public log: ' + str(public / 'pytest.log'),
        'Public JUnit: ' + str(public / 'junit.xml'),
        'Host load at start: ' + evidence['host_load_start'],
        'Host load at end: ' + evidence['host_load_end'],
        'The trace places the failure in accept_current_selection/load_guard, before dispatch and before the new callback owner is exercised. The high shared-machine load is a plausible contributor to elapsed setup time; this is not a matched idle-host causal experiment.', '',
        'The standing global canary agreement says "Only then fan out" after a verified successful unit. A failed pre-dispatch canary does not authorize treating the remaining public cases as verified. Recommendation to the lead: arrange a quiet execution window, rerun correction unchanged, inspect actual callback records and stage progress, then run omissions and pending separately and run the worker regression harness. Keep every freshness limit, deadline and window unchanged. No new validator-guard ruling is needed.', '',
        'Base comparison of the failure: the three source files in its path are byte-identical to the assignment base, as recorded in ' + str(evidence_path) + '. The existing chronology regression passes with candidate modules and with assignment-base replacements. This is a component comparison, not a matched full public test on the base. The earlier baseline correction run failed later at its deadline and remains a separate measurement.', '',
        'Implementation', '',
        'Local head: ' + head + '. Branch: codex/native-callback-growth-20261114. No push, PR, GitHub write, provider call or native binary call was made. The public fixture uses its existing ordinary-Python synthetic peer.', '',
        'The separate weak-admission owner keeps exact byte anchors, causal observation state, compact completed-stage deltas and exact-input derivations only in controller memory. Every callback still reconstructs admission, checks source/input pins, rereads prior streams and artifacts, and proves exact record/observation prefix extension. Failed suffixes cannot publish checkpoints. Source, binding or limit drift disables reuse for the attempt while retaining byte anchors. Closure clears semantic state and rejects retained transaction access.', '',
        'The closed guard includes verified source identities, composition/policy data, bounds, interpreter identity, effective module/function/class/method bindings, function code/default/keyword-default/closure identities and class methods. Unknown package graph entries refuse. No new binding baseline is adopted after drift.', '',
        'Standalone helpers, saved evidence and final completion retain full replay. No semantic state is stored in a receipt catalog token. Predicted journal bytes are regenerated rather than retained per checkpoint. All protected files, pins, deadlines, observer timeouts, freshness limits and windows remain unchanged.', '',
        'Validation', '', '| Report | Tests | Failures | Errors | Skipped |', '| --- | ---: | ---: | ---: | ---: |'])
    for suite in suites:
        counts = suite['counts']
        lines.append('| ' + suite['path'] + ' | ' + ' | '.join(str(counts[key]) for key in ('tests', 'failures', 'errors', 'skipped')) + ' |')
    lines.extend(['',
        'The native suite includes all fourteen new prefix regressions. They cover extension/full-replay equality, semantically valid coherently rehashed history replacement, failed-suffix rollback, stream and artifact anchors, sticky binding/default/closure/limit drift, newly checked suffixes, completed-stage deltas, compact storage, stale transactions, owner expiry and standalone bound-before-parse order.',
        'The prefix base comparison has thirteen expected failures because the new owner/guard interfaces do not exist on the base; it is not thirteen independent demonstrations of old semantic failures. The standalone bounds regression passes on the base, failed on the draft, and passes after the correction.',
        'The two-worker canary persisted a passing JUnit report before the full suite. The full suite passed; interrupted earlier draft runs are retained but are not counted as completed validation.',
        'Closed graph and stable effective-binding probe: ' + str(scratch / 'validator-graph-v4.json') + '. Timing: ' + str(scratch / 'validator-graph-v4.guard.json') + '. This microbenchmark is not callback CPU evidence.', '',
        'Unverified requirements', '',
        '- Per-callback CPU after the fix, including the requested flatness target.',
        '- Successful correction, omissions and pending public completion under unchanged limits.',
        '- The real-worker alias/default/closure/source/limit mutations, old-artifact mutations and reread counts. The harness is committed at ' + str(root / 'scripts/adhoc/check_callback_prefix_live_20261114.py') + ', but the failed canary produced no usable started attempt. Unit coverage is not a substitute for this real-path check.', '',
        'CPU evidence', '', '| Run | Fit from saved callback rows |', '| --- | --- |'])
    for row in summaries:
        lines.append('| ' + row['case'] + ' | ' + json.dumps(row['fit'], sort_keys=True) + ' |')
    lines.extend(['', 'Full saved summary: ' + str(summary_path),
        'Generated per-callback table: ' + str(scratch / 'prefix-final-summary.md'), '',
        'Pin proposal', '', '| Changed source | Proposed SHA-256 |', '| --- | --- |'])
    for row in pins['sources']:
        lines.append('| ' + row['path'] + ' | ' + row['current_sha256'] + ' |')
    lines.extend(['', 'Full pin audit: ' + str(pins_path),
        'Controller source manifests: ' + json.dumps(pins['controllers'], sort_keys=True),
        'CONTROL_SHA, manifest constants and synthetic peer: ' + json.dumps(pins['constants'], sort_keys=True),
        'Scanner base and integrated summaries: ' + json.dumps(pins['scanner_mismatches'], sort_keys=True),
        'The moved_here field distinguishes this branch from pre-existing scanner mismatches. All four protected-file hashes match the base. Hash-reference searches included hidden and ignored files. No pin rotation was performed.', '',
        'Review and provenance', '',
        'Review findings and fixes: ' + str(root / 'notes/reviews/callback-prefix-review-20261114.md') + '. The lead must file the review findings and this public-canary freshness failure as issues because the helper is prohibited from GitHub writes. No issue filing is claimed.',
        'The final read-only review checked full-replay boundaries, raw rereads, byte anchoring, checkpoint publication and owner lifetime. Public evidence gaps above remain explicit.',
        'Evidence manifest: ' + str(evidence_path),
        'Preserved preceding handoff: ' + str(snapshot),
        'Required preceding-handoff measurement copy: ' + str(measurement),
        'Original measurement preservation: ' + str(original),
        'All helper scripts remain committed under scripts/adhoc. Raw outputs and commands remain under the assigned scratch directory. No test process from this assignment remains running.'])
    output = '\n'.join(lines) + '\n'
    assert chr(64) not in output
    for path in (snapshot, measurement, original, evidence_path, pins_path, summary_path):
        assert path.is_file() and path.stat().st_size
    HANDOFF.write_text(output)
    assert HANDOFF.read_text() == output
    print(json.dumps({'handoff': str(HANDOFF), 'sha256': sha(HANDOFF.read_bytes()), 'head': head}, indent=2))


if __name__ == '__main__':
    main()
