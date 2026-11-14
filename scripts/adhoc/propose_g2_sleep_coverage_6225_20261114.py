#!/usr/bin/env python3
"""Document #6225 coverage limits without inventing no-sleep evidence.
Inputs: saved baseline and issue, existing conservative parser tests. Outputs:
proposal/trace in assigned scratch, 2026-11-14. No host probe or source mutation.
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
    source = OUT / 'baseline/native_host_power.py'
    anchors = ['covered = bool(stamps)', "problems.add('recognized log does not cover requested interval')",
        "ending = clock_reading('end')", "events = sleep_events(start['wall_ns'], ending['wall_ns'])",
        "'host_slept': any", "if not covered:"]
    excerpts = [{'line': n, 'text': line.strip()} for n, line in enumerate(source.read_text().splitlines(), 1)
                if any(anchor in line for anchor in anchors)]
    assert len(excerpts) == len(anchors)
    tests = ROOT / 'tests/test_native_host_power.py'
    value = {'issue': 6225, 'status': 'not fixed', 'operational_gap_confirmed': True,
        'confirmation': 'The parser requires a recognized event at or after the sampled run end. When the last recognized event precedes that end, a successful retrieval still yields unknown and host_slept remains null.',
        'qualification': 'The universal wording is too broad: the existing covered-history test can establish no sleep for a bracketed interval. That does not solve ordinary end-of-run coverage.',
        'rejected_shortcut': 'A successful retrieval after the run does not by itself establish that the retained log contains every event through the requested end. The proposed append-only coverage guarantee is not established by the saved evidence.',
        'decision_required': 'Choose a documented, verifiable coverage signal or retain the current conservative unknown result. Removing a field or changing its meaning also changes the diagnostic contract.',
        'recommendation': 'Keep host_slept and its tri-state interpretation unchanged until a coverage source is approved and verified. Preserve positive parsed intervals and independent clock divergence. If no coverage proof is available, document the common unknown result rather than equating retrieval time with complete history.',
        'proposed_verification': ['A last event before the run stays unknown unless an independently verified coverage watermark spans the full interval.',
            'Empty, truncated, rotated, unordered, unsupported, unmatched and clock-reversed histories must never become no-sleep claims.',
            'Covered paired historical intervals still distinguish positive sleep from a covered interval with no overlap.',
            'No host power setting, real pmset probe or acceptance-policy change is needed merely to document the limitation.'],
        'source': {'snapshot': pin(source), 'excerpts': excerpts},
        'existing_regressions': {'source': pin(tests), 'names': [
            'test_covered_darkwake_and_covered_no_sleep_are_distinct',
            'test_unsupported_incomplete_and_unmatched_logs_are_unknown',
            'test_unknown_sleep_log_is_not_a_no_sleep_claim']},
        'issue_evidence': pin(OUT / 'baseline/issue-6225.json'),
        'applied_source_changes': [], 'tests_run_for_proposal': []}
    target = OUT / 'issue-6225-proposal.json'
    with target.open('x') as stream:
        stream.write((json.dumps(value, indent=2) + '\n').replace(chr(64), '\\u0040'))
    lines = ['6225: not fixed. The common coverage gap is confirmed; no-sleep evidence was not weakened.', '',
        value['confirmation'], '', value['qualification'], '', value['rejected_shortcut'], '',
        'Decision: ' + value['decision_required'], '', 'Recommendation: ' + value['recommendation'], '',
        'Verification after the decision:', '']
    lines += ['- ' + row for row in value['proposed_verification']]
    lines += ['', 'Source trace: `' + str(target) + '`.', 'No new host observation or production change is claimed.']
    markdown = OUT / 'issue-6225-proposal.md'
    with markdown.open('x') as stream:
        stream.write('\n'.join(lines) + '\n')
    print(json.dumps({'markdown': pin(markdown), 'json': pin(target)}))


if __name__ == '__main__':
    main()
