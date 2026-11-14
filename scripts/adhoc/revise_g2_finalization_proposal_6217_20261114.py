#!/usr/bin/env python3
"""Correct G2-REVIEW-6217-F1's overstated evidence-format prerequisite.
Inputs: original proposal and retained pre-review snapshots. Outputs: revised
proposal, 2026-11-14. No production change, test or policy decision is applied.
"""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT.parent / 'scratch-g2-20261114'


def pin(path):
    raw = path.read_bytes()
    return {'path': str(path), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def main():
    target = OUT / 'issue-6217-proposal.json'
    prior = OUT / 'review-followups-before-fixes/issue-6217-proposal.json'
    assert target.read_bytes() == prior.read_bytes()
    value = json.loads(target.read_bytes())
    value['decision_required'] = 'Define the last signal observation included in the final decision and the policy for signals received after that cutoff while the immutable final/publication pair is persisted.'
    value['recommendation'] = [
        'Enter a record-only signal mode in a finally immediately around preparation and transport, before failure-evidence writes, host cleanup or finalization.',
        'After subscription publication validation, take one explicit signal snapshot. Preserve any earlier first stop; otherwise retain a concrete late interruption in existing first_stop and its failed gate. Mark completion false without rewriting consumed keep-awake bytes.',
        'Use that snapshot as the decision cutoff before final serialization. The existing first_stop field can carry the relevant signal information; a separate structured finalization field is optional, not a prerequisite.',
        'Persist final.json and published.json through a non-raising signal phase, preserving one immutable final value and restoring previous handlers afterward.',
        'The lead must choose how signals after the cutoff are reported: separately retained diagnostics with the completed publication, or a broader atomic publication protocol. They cannot be retroactively included in already persisted final bytes.',
    ]
    value['why_no_partial_patch'] = 'A handler-only patch is insufficient because final completion must also reconcile newly latched signals. The remaining decision is the cutoff and later-signal policy, not a mandatory evidence-schema revision. No policy choice is silently applied in this proposal.'
    value['review_correction'] = {'finding_id': 'G2-REVIEW-6217-F1', 'status': 'corrected',
        'prior_proposal': pin(prior), 'verification': 'The revised recommendation uses the existing first_stop and failed gate; it no longer requires a new versioned field.'}
    target.write_text((json.dumps(value, indent=2) + '\n').replace(chr(64), '\\u0040'))
    lines = ['6217: not fixed. The defect is confirmed; the final decision cutoff needs a lead ruling.', '',
        value['confirmation'], '', 'Decision: ' + value['decision_required'], '', 'Recommendation:', '']
    lines += ['- ' + row for row in value['recommendation']]
    lines += ['', value['why_no_partial_patch'], '', 'Verification after the decision:', '']
    lines += ['- ' + row for row in value['proposed_verification']]
    lines += ['', 'Source trace and review correction: `' + str(target) + '`.',
        'No production change or test execution is claimed.']
    markdown = OUT / 'issue-6217-proposal.md'
    markdown.write_text('\n'.join(lines) + '\n')
    assert 'versioned finalization field' not in markdown
    print(json.dumps({'markdown': pin(markdown), 'json': pin(target)}))


if __name__ == '__main__':
    main()
