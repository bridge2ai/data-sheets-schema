"""Report the D156 binding fix for the Claude lead, 2026-11-16.

Inputs: assigned scratch lane XML, summaries, timing JSONL and pin proposal.
Outputs: scratch evidence ledger and the assigned Markdown handoff.
Uses saved evidence only; no external service calls.
"""
import hashlib
import json
from pathlib import Path
import subprocess
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
SCRATCH = ROOT.parent / 'scratch-d156-fix-20261116'
HANDOFF = ROOT.parent / 'codex-development-efficiency-20261111/notes/development_efficiency_20261111/handoffs/codex-d156-fix-20261116.md'


def main():
    head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    lanes = {}
    for name, relative in (
        ('scope-canary', 'scope-canary/results/unit.xml'),
        ('worker-final', 'worker-final/results/unit.xml'),
        ('controls-canary-budget', 'controls-canary/results/budget.xml'),
        ('controls-canary-native', 'controls-canary/results/native.xml'),
        ('controls-budget', 'controls/results/budget.xml'),
        ('controls-native', 'controls/results/native.xml'),
        ('timing-canary', 'timing-canary/results/unit.xml'),
        ('public-correction', 'public-correction/results/pytest.xml')):
        path = SCRATCH / relative
        if not path.exists():
            lanes[name] = {'completed': False}
            continue
        rows = list(ET.parse(path).getroot().iter('testcase'))
        failures = [row for row in rows if row.find('failure') is not None]
        errors = [row for row in rows if row.find('error') is not None]
        skipped = [row for row in rows if row.find('skipped') is not None]
        lanes[name] = {'completed': True, 'passed': len(rows) - len(failures) - len(errors) - len(skipped),
            'failed': len(failures), 'errors': len(errors), 'skipped': len(skipped), 'path': str(path),
            'stops': [child.get('message') for row in failures + errors for child in row
                      if child.tag in ('failure', 'error')]}
    timings_path = SCRATCH / 'public-timings.jsonl'
    timings = [json.loads(line) for line in timings_path.read_text().splitlines()] if timings_path.exists() else []
    observations = [row for row in timings if row.get('function') == '_observe_event']
    public = SCRATCH / 'public-correction'
    artifacts = {name: [str(path) for path in public.rglob(name)]
                 for name in ('capture.json', 'subscription-dispatched.json', 'actual-result.json')}
    helper_times = []
    for path in public.rglob('*stderr*'):
        if not path.is_file():
            continue
        for line in path.read_text(errors='replace').splitlines():
            try:
                row = json.loads(line)
            except ValueError:
                continue
            if isinstance(row, dict) and 'helper_timing' in row:
                helper_times.append({'path': str(path), **row['helper_timing']})
    advances = [row for row in helper_times if ' advance ' in row['command']]
    pins_path = SCRATCH / 'pin-proposals-final.json'
    pins = json.loads(pins_path.read_text())
    ledger = {'head': head, 'lanes': lanes, 'artifacts': artifacts,
        'peak_observe_event_seconds': max((row['seconds'] for row in observations), default=None),
        'last_observe_event': observations[-1] if observations else None,
        'late_advance': advances[-1] if advances else None, 'helper_times': helper_times,
        'pins': pins, 'lane_summaries': {str(path): json.loads(path.read_text())
            for path in SCRATCH.glob('*/lane_summary.json')}}
    ledger_path = SCRATCH / 'binding-fix-evidence.json'
    ledger_path.write_text(json.dumps(ledger, indent=2, sort_keys=True) + '\n')
    result_lines = ['- ' + name + ': ' + (', '.join(str(row[key]) + ' ' + key
        for key in ('passed', 'failed', 'errors', 'skipped')) + '. Evidence: ' + row['path']
        if row['completed'] else 'no completed report; no pass claimed.') for name, row in lanes.items()]
    public_row = lanes['public-correction']
    body = f'''# D156 binding diagnosis confirmed; attempted fix blocked by callback-scope design

The public correction case failed before capture. Do not integrate the attempted source commit as a completed fix. Moving PreparedIdentity construction after callback preparation removes the earlier class-lifetime mismatch but exposes a verifier-bootstrap import refusal. The required binding fix is incomplete, and the assignment's design-decision stop applies.

The supplied registration bytes are the same along the synthetic fixture and launch paths. The original strict check also compares exact class identity: callback preparation replaces ambient package bindings with a verified consumer scope. The attempted change constructs PreparedIdentity and imports exchange in that later lifetime. Its constructor then imports native_execution_authority_v2, which the consumer finder explicitly forbids. Its fresh recheck method requires that verifier too. Production uses the same preparation block, so this is not a synthetic-registration-only defect. checked_value and the import boundary are unchanged.

Recommended design decision: separate retention of admitted, verified callback objects from the process-wide consumer import scope, allowing main-thread prepared verification to run with its authoritative module bindings while callback admission remains live. Review that ownership/lifetime change before implementation. Do not allow the verifier bootstrap into the consumer graph, accept foreign classes, or replace fresh checks with saved verdicts. The current ordering-only patch is insufficient.

Committed source/test branch head: {head}. The reporting script remains uncommitted: Git index-lock creation was refused twice, including the one retry after ten seconds required by the assignment. No push, GitHub write, provider call or Claude binary execution was made.

## Validation

{chr(10).join(result_lines)}

Public first stop: {json.dumps(public_row.get('stops', []))}.
Peak completed _observe_event seconds: {ledger['peak_observe_event_seconds']}.
Late advance: {json.dumps(ledger['late_advance'])}.
Capture-to-dispatch seconds: unavailable; capture and dispatch were not reached.
Peak final-callback _observe_event seconds: unavailable; no callback was reached.
Late advance seconds: unavailable; no helper execution was reached.
The ignore-independent artifact search found no capture.json, subscription-dispatched.json or actual-result.json in the public lane. Missing measurements do not satisfy either owner threshold: this run neither establishes the at-or-under-60-second deferral condition nor the over-75-second trigger for issues 4400 and 4550.

The scope canary verified that launch creates the exact identity class active after preparation, retains exact registration-byte rejection, and closes preparation on refusal. The controls canary exercised local loopback refusal without a provider. The timing canary persisted observer startup, a completed synthetic mint span and shutdown. It did not itself exercise a final callback.

## Pins and review

Pin proposal: {pins_path}. Proposed pin edits: {json.dumps(pins['proposed_edits'])}. Protected files check: {pins['protected_files_ok']}.
The pin tool also reports pre-existing D128 scanner skill and scan.py asset refresh actions; no pin was edited.

The read-only review found the production regression's old exchange path could otherwise wait for IPC instead of failing promptly. Both module lifetimes now use the test consumer, so an old identity fails at the real strict gate. The public run exposed a second finding: these regressions isolate the constructor and recheck, so they verify class/byte binding order but do not exercise bootstrap import restrictions. The source patch is therefore not a validated integrated fix despite the unit passes. Both findings are recorded here for the lead's issue ledger because the assignment forbids GitHub writes.

An initial unit invocation had an extra option separator and collected no tests. A controls preflight refused uncommitted source; it was rerun after commit. Neither is counted as a passing test.

Evidence ledger: {ledger_path}. Artifact discovery uses Path.rglob, including ignored and hidden files. Commands, environment and gate waits are retained in the lane summaries named in that ledger. The helper script is {Path(__file__).resolve()}.
'''
    if chr(64) in body:
        raise ValueError('handoff contains forbidden character')
    HANDOFF.write_text(body)
    print(str(HANDOFF))
    print(hashlib.sha256(HANDOFF.read_bytes()).hexdigest())


if __name__ == '__main__':
    main()
