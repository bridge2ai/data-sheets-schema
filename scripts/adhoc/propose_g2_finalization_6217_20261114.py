#!/usr/bin/env python3
"""Document #6217's publication decision before changing immutable evidence.
Inputs: saved G2 baseline and issue. Outputs: answer-first proposal and source
trace in assigned scratch, 2026-11-14. No runtime, test or production source edit.
"""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT.parent / 'scratch-g2-20261114'
BASELINE = OUT / 'baseline'


def pin(path):
    raw = path.read_bytes()
    return {'path': str(path), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def main():
    anchors = {
        'native_execution.py': ['def _signals(', 'observed.append(signum)', 'if len(observed) == 1:', 'raise KeyboardInterrupt'],
        'native_execution_orchestration.py': ['with _signals(signals):', 'status = _execute_child(',
            "awake['signals_received'] = list(signals)", "durable_new(attempt/'keep-awake.json'",
            'with host_power.finishing_run(attempt):', '_publication_subscription(',
            'final_raw = draft._encoded(final)', "durable_new(evidence/'final.json'",
            "durable_new(evidence/'published.json'", 'raise first_error from publication_error'],
        'native_host_power.py': ['def finishing_run(', 'finish_run(directory)', 'except Exception as exc:'],
    }
    evidence = []
    for name, patterns in anchors.items():
        path = BASELINE / name
        matches = [{'line': number, 'text': line.strip()} for number, line in enumerate(path.read_text().splitlines(), 1)
                   if any(pattern in line for pattern in patterns)]
        assert matches
        evidence.append({'snapshot': pin(path), 'excerpts': matches})
    decision = {
        'issue': 6217, 'status': 'not fixed', 'defect_confirmed': True,
        'confirmation': 'The first SIGINT or SIGTERM raises KeyboardInterrupt throughout cleanup and publication. Those paths can propagate before the immutable final/publication pair exists.',
        'decision_required': 'Define the last signal observation included in the final decision and how signals after keep-awake persistence are represented without rewriting consumed evidence.',
        'recommendation': [
            'Enter a record-only signal mode in a finally immediately around preparation and transport, before any failure-evidence write, host cleanup or finalization.',
            'Retain the first stop; before final assessment, reconcile all latched signals and fail the runtime gates if any qualifying interruption occurred.',
            'Keep the already persisted keep-awake bytes unchanged. Represent later finalization signals separately in a versioned finalization field whose readback validation is explicitly defined.',
            'Define a decision cutoff before final serialization. Commit final.json and published.json under a short non-raising/deferred signal phase, preserving the same final bytes and restoring previous handlers after persistence.',
            'Signals after that cutoff must have an explicit contract: retain separately and report publication complete, or adopt a broader atomic publication design. Do not silently rewrite final.json or claim all later signals are included in its bytes.',
        ],
        'why_no_partial_patch': 'Changing only the handler can leave late signals absent from the immutable keep-awake snapshot and can certify completion after an unrepresented interruption. The issue requests a failed saved result; choosing its cutoff is an evidence-contract decision reserved to the lead.',
        'proposed_verification': [
            'First SIGINT and SIGTERM during failure-evidence persistence, keep-awake cleanup, host finish and subscription publication: retain both final artifacts, a concrete sticky stop and exact read_final equality.',
            'Repeated signals throughout cleanup and publication must not abort writes; an earlier failure remains first.',
            'Signals at each final/publication write must follow the approved cutoff contract; neither partial nor contradictory immutable evidence may certify completion.',
            'Previous handlers restore on successful and exceptional paths; consumed keep-awake bytes remain identical.',
        ],
        'source_trace': evidence, 'issue_evidence': pin(BASELINE / 'issue-6217.json'),
        'applied_source_changes': [], 'tests_run_for_proposal': [],
    }
    target = OUT / 'issue-6217-proposal.json'
    with target.open('x') as stream:
        stream.write((json.dumps(decision, indent=2) + '\n').replace(chr(64), '\\u0040'))
    lines = ['6217: not fixed. The defect is confirmed; publication semantics need a lead decision.', '',
        decision['confirmation'], '', 'Decision: ' + decision['decision_required'], '', 'Recommendation:', '']
    lines += ['- ' + row for row in decision['recommendation']]
    lines += ['', decision['why_no_partial_patch'], '', 'Verification after the decision:', '']
    lines += ['- ' + row for row in decision['proposed_verification']]
    lines += ['', 'Source trace: `' + str(target) + '`.', 'No production change or test execution is claimed.']
    markdown = OUT / 'issue-6217-proposal.md'
    with markdown.open('x') as stream:
        stream.write('\n'.join(lines) + '\n')
    print(json.dumps({'markdown': pin(markdown), 'json': pin(target)}))


if __name__ == '__main__':
    main()
