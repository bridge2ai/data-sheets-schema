"""Issue 6233, 2026-11-14: write the lead handoff from persisted verification.

Inputs: scratch reports, explicit answer, JUnit paths, and source checkout.
Output: assigned handoff with prior handoffs preserved and computed hashes.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import xml.etree.ElementTree as ET


HANDOFF = Path('/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/codex-development-efficiency-20261111/notes/development_efficiency_20261111/handoffs/codex-native-callback-growth-20261114.md')


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def junit(path):
    root = ET.parse(path).getroot()
    suites = [root] if root.tag == 'testsuite' else list(root.findall('testsuite'))
    counts = {key: sum(int(suite.get(key, '0')) for suite in suites)
              for key in ('tests', 'failures', 'errors', 'skipped')}
    failures = [{'case': case.get('classname', '') + '::' + case.get('name', ''),
                 'message': failure.get('message', '')}
                for suite in suites for case in suite.findall('testcase')
                for failure in list(case.findall('failure')) + list(case.findall('error'))]
    return {'path': str(path), 'counts': counts, 'failures': failures, 'sha256': sha(path.read_bytes())}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('scratch', type=Path)
    parser.add_argument('--answer', required=True)
    parser.add_argument('--suite', action='append', required=True, type=Path)
    parser.add_argument('--base', required=True, type=Path)
    parser.add_argument('--live', required=True, type=Path)
    args = parser.parse_args()
    root = Path.cwd().resolve()
    scratch = args.scratch.resolve()
    pins_path = scratch / 'prefix-pin-proposal.json'
    summary_path = scratch / 'prefix-final-summary.json'
    summary_md = scratch / 'prefix-final-summary.md'
    pins = json.loads(pins_path.read_text())
    summaries = json.loads(summary_path.read_text())
    live = json.loads(args.live.read_text())
    suites = [junit(path.resolve()) for path in args.suite]
    base = junit(args.base.resolve())
    head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip()
    protected = all(row['base'] == row['current'] for row in pins['protected'].values())
    assert protected
    for source in pins['sources']:
        assert sha((root / source['path']).read_bytes()) == source['current_sha256']
    public = [row for row in summaries if row['case'].startswith('prefix-final-')]
    assert len(public) == 3 and all(row['junit'] is not None and row['exit_status'] is not None for row in public)
    assert {row['kind'] for row in live['bindings']} == {'alias', 'default', 'closure', 'limit', 'source'}
    assert {row['role'] for row in live['bytes']} == {'transcript', 'control', 'journal', 'record', 'observation', 'response', 'stage'}
    previous = HANDOFF.read_bytes()
    previous_snapshot = HANDOFF.with_name(HANDOFF.stem + '-before-' + sha(previous)[:12] + '.md')
    if previous_snapshot.exists():
        assert previous_snapshot.read_bytes() == previous
    else:
        previous_snapshot.write_bytes(previous)
    measurement = HANDOFF.with_name(HANDOFF.stem + '-measurement.md')
    original_measurement = HANDOFF.with_name(HANDOFF.stem + '-measurement-original.md')
    if measurement.exists() and not original_measurement.exists():
        original_measurement.write_bytes(measurement.read_bytes())
    measurement.write_bytes(previous)
    assert measurement.read_bytes() == previous
    lines = [args.answer, '',
        'Implementation and boundary', '',
        'The separate weak-admission owner retains byte anchors, causal observation state, compact completed-stage deltas and exact-input derivations only in controller memory. Every callback still reconstructs admission, checks source/input pins, rereads stream bytes and referenced artifacts, and proves exact prefix extension. Failed suffixes do not publish semantic checkpoints. Source/binding/limit drift disables semantic reuse for the attempt; restoring bindings cannot establish a new baseline. Owner closure clears semantic state and refuses retained transactions.', '',
        'Standalone helpers, saved-evidence reads and final completion retain full replay. No semantic state is placed in the receipt catalog owner. Predicted journals are regenerated from their exact record prefix instead of retained per checkpoint. No protected file, pin, deadline, observer timeout, window or acceptance rule changed.', '',
        'Local head: ' + head + '. No push, pull request, GitHub write, provider call or native binary call was made. The public fixtures use their existing ordinary-Python synthetic peer.', '',
        'Validation', '',
        'The base comparison substitutes only the assignment-base versions of the changed modules for pure tests. Missing new owner/guard APIs are reported as base failures; this is not a base public-lifetime run.',
        json.dumps({'base_comparison': base}, sort_keys=True), '']
    for suite in suites:
        lines.extend([json.dumps(suite, sort_keys=True), ''])
    lines.extend(['The live regression harness reopens verified admission over the new synthetic evidence and invokes the fixed preloaded callback on a worker. It does not launch another native attempt. It checks full replay after alias/default/closure/limit changes, source refusal, sticky invalidation, complete old-byte rereads, byte-mutation refusals, and owner closure.',
        str(args.live.resolve()), json.dumps(live, sort_keys=True), '',
        'Public callback measurements', '', summary_md.read_text(), '',
        'The instrument retains the original thread-CPU boundary. It now also counts stage functions in the package initializer and newly checked observations; diagnostic overhead is included. The earlier baseline remains a descriptive comparison, not a matched host-load experiment.', '',
        'Pin proposal', '', '| Changed source | Proposed SHA-256 |', '| --- | --- |'])
    for source in pins['sources']:
        lines.append('| ' + source['path'] + ' | ' + source['current_sha256'] + ' |')
    lines.extend(['', 'Complete pin audit: ' + str(pins_path),
        'Controller manifest checks: ' + json.dumps(pins['controllers'], sort_keys=True),
        'CONTROL_SHA, controller-manifest constants and synthetic peer: ' + json.dumps(pins['constants'], sort_keys=True),
        'Scanner summaries, including pre-existing mismatches: ' + json.dumps(pins['scanner_mismatches'], sort_keys=True),
        'All four protected-file hashes match the assignment base. Old-hash searches included hidden and ignored files.', '',
        'Review and provenance', '',
        'Read-only review findings are recorded in ' + str(root / 'notes/reviews/callback-prefix-review-20261114.md') + '. The lead must file the findings because this helper is forbidden from GitHub writes. The handoff does not claim that issues were filed.', '',
        'Preserved preceding handoff: ' + str(previous_snapshot),
        'Required measurement copy of preceding handoff: ' + str(measurement),
        'Original measurement preservation: ' + str(original_measurement), '',
        'Helper scripts are committed on this branch under scripts/adhoc. Commands and raw outputs remain in the assigned scratch directory. Interrupted development runs and pre-fix failures are retained there and are not counted as successful final validation.'])
    text = '\n'.join(lines) + '\n'
    # Logs can contain Python decorators; none may leak into this handoff.
    if chr(64) in text:
        raise ValueError('handoff contains a prohibited character; summarize the offending diagnostic instead')
    HANDOFF.write_text(text)
    assert HANDOFF.read_text() == text
    print(json.dumps({'handoff': str(HANDOFF), 'sha256': sha(HANDOFF.read_bytes()), 'head': head}, indent=2))


if __name__ == '__main__':
    main()
