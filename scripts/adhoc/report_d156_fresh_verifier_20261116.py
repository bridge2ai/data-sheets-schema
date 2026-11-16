"""Report D156 scope-ruling implementation from retained evidence, 2026-11-16.

Inputs: scratch lane XML, JSON summaries, timing JSONL and pin proposals.
Outputs: scratch evidence JSON and a new top section in the lead handoff.
Serves the D156 scope ruling; no network or provider operations.
"""
from datetime import datetime
import hashlib
import json
from pathlib import Path
import subprocess
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
SCRATCH = ROOT.parent / 'scratch-d156-fix-20261116'
HANDOFF = ROOT.parent / 'codex-development-efficiency-20261111/notes/development_efficiency_20261111/handoffs/codex-d156-fix-20261116.md'


def rows(path):
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def main():
    head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    lanes = {}
    for name in ('fresh-scope-canary', 'fresh-worker-sequence', 'fresh-worker-final',
                 'fresh-controls-canary', 'fresh-controls', 'fresh-public-correction',
                 'carrier-canary', 'carrier-worker-final', 'carrier-worker-canonical', 'carrier-controls-canary',
                 'carrier-controls', 'carrier-public-correction'):
        folder = SCRATCH / name
        summary = folder / 'lane_summary.json'
        entry = {'summary': json.loads(summary.read_text()) if summary.exists() else None,
                 'results': {}}
        for path in sorted((folder / 'results').glob('*.xml')):
            cases = list(ET.parse(path).getroot().iter('testcase'))
            failed = [case for case in cases if case.find('failure') is not None]
            errors = [case for case in cases if case.find('error') is not None]
            skipped = [case for case in cases if case.find('skipped') is not None]
            entry['results'][str(path)] = {'passed': len(cases) - len(failed) - len(errors) - len(skipped),
                'failed': len(failed), 'errors': len(errors), 'skipped': len(skipped),
                'stops': [child.get('message') for case in failed + errors for child in case
                          if child.tag in ('failure', 'error')]}
        lanes[name] = entry
    public = SCRATCH / 'carrier-public-correction'
    timing_path = SCRATCH / 'carrier-public-timings.jsonl'
    timings = rows(timing_path) if timing_path.exists() else []
    observers = [row for row in timings if row.get('function') == '_observe_event']
    dispatches = [row for row in timings if row.get('function') == '_admit_subscription_guard']
    artifacts = {name: [str(path) for path in public.rglob(name)] for name in
                 ('capture.json', 'subscription-dispatched.json', 'actual-result.json')}
    traces = [row for path in public.rglob('host-pre-dispatch-*.jsonl') for row in rows(path)]
    captures = [row for row in traces if row.get('boundary') == 'capture_observed']
    capture_to_dispatch = None
    if captures and dispatches:
        stamp = captures[-1].get('captured_at')
        if stamp:
            capture_to_dispatch = dispatches[-1]['completed_wall'] - datetime.fromisoformat(stamp.replace('Z', '+00:00')).timestamp()
    helpers = []
    for path in public.rglob('*stderr*'):
        if not path.is_file():
            continue
        for line in path.read_text(errors='replace').splitlines():
            try:
                row = json.loads(line)
            except ValueError:
                continue
            if isinstance(row, dict) and 'helper_timing' in row:
                helpers.append({'path': str(path), **row['helper_timing']})
    advances = [row for row in helpers if ' advance ' in row.get('command', '')]
    pins_path = SCRATCH / 'carrier-pin-proposals.json'
    pins = json.loads(pins_path.read_text())
    ledger = {'head': head, 'lanes': lanes, 'artifacts': artifacts,
        'capture_to_dispatch_seconds': capture_to_dispatch,
        'peak_final_callback_observe_event_seconds': max((row['seconds'] for row in observers), default=None),
        'late_advance': advances[-1] if advances else None,
        'helper_times': helpers, 'timings': timings, 'capture_traces': captures, 'pins': pins}
    ledger_path = SCRATCH / 'fresh-verifier-evidence.json'
    ledger_path.write_text(json.dumps(ledger, indent=2, sort_keys=True) + '\n')
    public_results = lanes['carrier-public-correction']['results'].values()
    passed = any(row['passed'] == 1 and row['failed'] == 0 and row['errors'] == 0 for row in public_results)
    peak = ledger['peak_final_callback_observe_event_seconds']
    if peak is not None and peak > 75:
        threshold = 'Over 75 seconds: owner ruling 4A-Post triggers issues 4400 and 4550.'
    elif passed and peak is not None and peak <= 60:
        threshold = 'At or under 60 seconds: owner ruling 4A-Post keeps issues 4400 and 4550 deferred.'
    else:
        threshold = 'Neither threshold is established by a completed final-callback result.'
    lines = ['# D156 fresh-process verifier: ' + ('public correction passed' if passed else 'public correction not established'), '',
        'Implemented design A. It touches zero lines in the security-relevant loader; design B would alter ownership and restoration of its nested process-wide scopes. Exact-class checked_value and the verifier import restriction remain unchanged. Every check uses a new interpreter, nonce and exact-input digest over pipes; only an exit-zero matching pass is accepted. Timeout kills the verifier process group. No reusable verdict is persisted.', '',
        'The constructor freshly verifies the registration and compares its census identities with the original full preparation baseline. Later checks freshly validate bytes, HEAD, roster/pins, committed sources, interpreter, preparation/composition, runtime and light census against those identities. Transferred census identities are comparison data and never populate a child full-verification cache. CLI launches carry the registration file path; synthetic byte-only callers retain exact registration-byte binding.', '',
        'Source head: ' + head + '. No push, GitHub write, provider call, Claude binary execution or pin edit.', '',
        '## Validation', '']
    for name, lane in lanes.items():
        for path, result in lane['results'].items():
            lines.append('- ' + name + ': ' + ', '.join(str(result[key]) + ' ' + key for key in ('passed', 'failed', 'errors', 'skipped')) + '. Evidence: ' + path)
            for stop in result['stops']:
                lines.append('  First stop: ' + str(stop))
    lines += ['', 'Capture-to-dispatch seconds: ' + str(capture_to_dispatch) + '.',
        'Peak completed final-callback _observe_event seconds: ' + str(ledger['peak_final_callback_observe_event_seconds']) + '.',
        threshold,
        'Late advance: ' + json.dumps(ledger['late_advance'], sort_keys=True) + '.',
        'Missing timings are unknown and establish neither owner threshold. Artifact discovery includes ignored and hidden files through Path.rglob.', '',
        'The real-loader canary exercises the unmocked constructor and a real child: the parent still refuses verifier-bootstrap imports while the child reaches fresh registration validation. It is an invalid-input refusal witness; the public case supplies the complete acceptance check. Timeout and reply-replay tests are focused simulations.', '',
        'The strengthened constructor assertion initially exposed a noncanonical interpreter spelling in the unit command. The child correctly refused the differing executable strings. The canonical-path rerun retains strict interpreter equality and verifies the actual registration-validation frame, rather than accepting any child refusal.', '',
        '## Integration and review', '',
        'Overlapping-file functions touched: native_prepared_worker._full_preparation_baseline, _verify, PreparedIdentity.__init__, PreparedIdentity._verify, PreparedIdentity.recheck, PreparedIdentity.require_unchanged and exchange. No edits to native_launch_sequence.py or run_native_canary.py.', '',
        'Other production functions touched: native_execution_orchestration.launch, _launch and _launch_prepared; native_shared_execution_orchestration.launch; native_generation.main. New module native_prepared_verifier owns _baseline, verify and main.', '',
        'Also touched native_shared_contract._Carrier.__post_init__: resolve type hints against the defining module globals. The first public run exposed a cold-child CapturedArtifact.pin mismatch because default type-hint resolution used a different live module binding. The real-loader regression now checks both matching carrier lifetimes and both directions of foreign-class refusal. No foreign class is accepted.', '',
        'Read-only review found that a fresh child cannot use the parent process full-census cache. Addressed by carrying comparison identities and checking a fresh census without installing a cached verdict. This finding is retained for the lead issue ledger; helper bounds forbid GitHub issue writes.', '',
        'Pin proposals: ' + str(pins_path) + '. Proposed edits: ' + json.dumps(pins['proposed_edits']) + '. Protected files check: ' + str(pins['protected_files_ok']) + '.',
        'The pin tool also reports existing scanner asset refresh actions; see the JSON for exact computed hashes.', '',
        'Evidence ledger: ' + str(ledger_path) + '. Commands, gate waits, outcomes and cleanliness are preserved in lane summaries. Reporting provenance: ' + str(Path(__file__).resolve()) + '.', '']
    text = '\n'.join(lines)
    if chr(64) in text:
        raise ValueError('handoff contains a forbidden character')
    previous = HANDOFF.read_text()
    HANDOFF.write_text(text + '\n---\n\n' + previous)
    print(str(HANDOFF))
    print(hashlib.sha256(HANDOFF.read_bytes()).hexdigest())


if __name__ == '__main__':
    main()
