"""Activate the separately reviewed PR6325 chained D128 successor, 2026-11-24.

Purpose: write the reviewed successor fixture for PR 6325 and replace the one
inactive pin literal in the D128 gate test. Derived from
pin_pr6325_d128_successor_20261122.py, which is unchanged. The candidate
commit and the proposal and comparison hashes are arguments here, not
constants; the pinned review file must name all three and end with APPROVE.

Inputs: the exact local proposal and comparison written by
compare_pr6325_d128_successor_20261124.py, and an explicitly pinned APPROVE
review by a session that re-ran the scans itself.
Outputs: one new successor fixture and the unique inactive test-gate SHA literal.
The historical owner fixture and the PR6302 successor are unchanged. No
scanner, test, native, network, commit or reference mutation is performed.
Existing successor output refuses.
Serves: PR 6325 under the lead's assignment of 2026-11-24 (STATUS 20:59:12Z, 21:01:28Z).
"""
import argparse
from copy import deepcopy
import importlib.util
import json
import os
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CORE = 'scripts/adhoc/compare_pr6325_d128_successor_20261124.py'
GATE = 'tests/test_native_d128_scanner_comparison.py'
FIXTURE = 'tests/fixtures/native_d128_pr6325_successor.json'
INACTIVE = b'PR6325_SUCCESSOR_SHA256 = None\n'


def core_module():
    spec = importlib.util.spec_from_file_location('pr6325_d128_successor_activation_core', ROOT / CORE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def pinned_input(core, path, expected):
    core.need(path.is_file() and not path.is_symlink(), 'input must be a regular file: ' + str(path))
    raw = path.read_bytes()
    core.need(core.sha(raw) == expected, 'input bytes differ from the explicit review pin: ' + str(path))
    return raw


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--candidate', required=True, help='the reviewed candidate commit; HEAD must be it')
    parser.add_argument('--proposal', type=Path, required=True)
    parser.add_argument('--proposal-sha256', required=True)
    parser.add_argument('--comparison', type=Path, required=True)
    parser.add_argument('--comparison-sha256', required=True)
    parser.add_argument('--review-file', type=Path, required=True)
    parser.add_argument('--review-sha256', required=True)
    parser.add_argument('--review-reference', required=True)
    args = parser.parse_args()
    core = core_module()
    CANDIDATE, PROPOSAL_SHA256, COMPARISON_SHA256 = core.full_sha(args.candidate), args.proposal_sha256, args.comparison_sha256
    core.need(all(type(value) is str and len(value) == 64 and all(c in '0123456789abcdef' for c in value)
                  for value in (PROPOSAL_SHA256, COMPARISON_SHA256, args.review_sha256)),
              'activation requires the explicit proposal, comparison and review hashes')
    core.need(core.git(ROOT, 'rev-parse', '--verify', 'HEAD^{commit}').decode().strip() == CANDIDATE,
              'source HEAD differs from the reviewed candidate')
    core.need(type(args.review_reference) is str and bool(args.review_reference.strip())
              and chr(64) not in args.review_reference, 'explicit plain review reference required')
    pinned = {}
    for relative in (CORE, GATE, core.HISTORICAL_FIXTURE, core.PREDECESSOR_FIXTURE):
        path = ROOT / relative
        core.need(path.is_file() and not path.is_symlink(), 'source input is not a regular file')
        raw = path.read_bytes()
        core.need(raw == core.git(ROOT, 'show', CANDIDATE + ':' + relative),
                  'source differs from the reviewed candidate: ' + relative)
        pinned[relative] = raw
    core.need(core.sha(pinned[core.HISTORICAL_FIXTURE]) == core.HISTORICAL_SHA,
              'historical owner fixture changed')
    historical = core.decode(pinned[core.HISTORICAL_FIXTURE])
    previous = core.predecessor_successor(pinned[core.PREDECESSOR_FIXTURE], approved_for_plan=historical)
    original = pinned[GATE]
    core.need(original.count(INACTIVE) == 1, 'gate must have exactly one inactive successor pin')
    destination = ROOT / FIXTURE
    core.need(not destination.exists() and not destination.is_symlink(), 'preserve existing successor fixture')
    proposal_raw = pinned_input(core, args.proposal, PROPOSAL_SHA256)
    comparison_raw = pinned_input(core, args.comparison, COMPARISON_SHA256)
    review_raw = pinned_input(core, args.review_file, args.review_sha256)
    core.need(review_raw.endswith(b'\nAPPROVE\n') or review_raw.endswith(b'\nAPPROVE')
              or review_raw in (b'APPROVE', b'APPROVE\n'), 'review must end with the exact APPROVE line')
    review_raw.decode('utf-8')
    core.need(all(value.encode('ascii') in review_raw for value in
                  (CANDIDATE, PROPOSAL_SHA256, COMPARISON_SHA256)),
              'review does not explicitly identify all immutable inputs')
    proposal, comparison = core.decode(proposal_raw), core.decode(comparison_raw)
    core.need(proposal['kind'] == 'pr6325_d128_successor_proposal' and proposal['review_reference'] is None
              and proposal['comparison_evidence_sha256'] == COMPARISON_SHA256
              and proposal['reference_candidate']['commit'] == CANDIDATE
              and proposal['tool_commit'] == CANDIDATE, 'proposal identity differs')
    core.need(comparison['kind'] == 'pr6325_d128_successor_comparison'
              and comparison['status'] == 'complete_diagnostic_pending_review'
              and comparison['historical_fixture_sha256'] == core.HISTORICAL_SHA
              and comparison['historical_evidence_sha256'] == core.EVIDENCE_SHA
              and comparison['historical_owner_decision_changed'] is False,
              'comparison identity differs')
    core.need(comparison.get('predecessor_successor_sha256') == core.PREDECESSOR_SHA
              and proposal['predecessor']['successor_sha256'] == core.PREDECESSOR_SHA
              and comparison.get('predecessor_commit') == proposal['predecessor']['commit'],
              'proposal or comparison is not chained after the PR6302 successor')
    legs = comparison['comparisons']
    core.need([leg['label'] for leg in legs] == [
        'current_tool_baseline_to_current_candidate',
        'frozen_tool_baseline_to_current_tool_baseline', 'frozen_reference_to_current_candidate',
        core.DELTA_LABEL]
        and legs[1]['exact_arrays_equal'] is True, 'comparison legs or frozen baseline differ')
    delta = {name: {key: value for key, value in ledger.items()
                    if key not in ('positional_differences', 'exact_arrays_equal')}
             for name, ledger in legs[3]['arrays'].items()}
    core.need(core.same(delta, proposal['predecessor']['delta']), 'proposal delta differs from the exact comparison')
    core.require_stop_rule(delta)
    arrays = {name: {key: value for key, value in ledger.items()
                    if key not in ('positional_differences', 'exact_arrays_equal')}
              for name, ledger in legs[0]['arrays'].items()}
    core.need(core.same(arrays, proposal['arrays'])
              and core.same(proposal['reference_candidate'], comparison['source_manifests']['candidate']['identity'])
              and core.same(proposal['tool_assets_sha256'], core.assets(ROOT, CANDIDATE)),
              'proposal differs from the exact comparison or scanner assets')
    reviewed = deepcopy(proposal)
    reviewed.update(kind='pr6325_d128_reviewed_successor', review_reference=args.review_reference)
    core.need(set(reviewed) == set(proposal) and all(core.same(reviewed[key], value)
              for key, value in proposal.items() if key not in ('kind', 'review_reference')),
              'activation changed an unreviewed proposal field')
    raw = (json.dumps(reviewed, indent=2, sort_keys=True, ensure_ascii=True, allow_nan=False)
           .replace(chr(64), '\u0040') + '\n').encode('utf-8')
    fixture_sha = core.sha(raw)
    core.require_successor(raw, fixture_sha, historical, previous)
    changed = original.replace(INACTIVE, ("PR6325_SUCCESSOR_SHA256 = '" + fixture_sha + "'\n").encode('ascii'))
    core.need((ROOT / GATE).read_bytes() == original, 'gate changed during activation preparation')
    for path, expected in ((args.proposal, proposal_raw), (args.comparison, comparison_raw),
                           (args.review_file, review_raw)):
        core.need(path.read_bytes() == expected, 'review input changed during activation preparation')
    with destination.open('xb') as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    core.need(destination.read_bytes() == raw, 'new successor fixture readback differs')
    # If the gate write fails, the new fixture remains unselected and retained.
    with (ROOT / GATE).open('r+b') as stream:
        core.need(stream.read() == original, 'gate changed before the sole pin edit')
        stream.seek(0)
        stream.write(changed)
        stream.truncate()
        stream.flush()
        os.fsync(stream.fileno())
    core.need((ROOT / GATE).read_bytes() == changed and destination.read_bytes() == raw,
              'activated fixture or gate readback differs')
    core.need((ROOT / core.HISTORICAL_FIXTURE).read_bytes() == pinned[core.HISTORICAL_FIXTURE]
              and (ROOT / core.PREDECESSOR_FIXTURE).read_bytes() == pinned[core.PREDECESSOR_FIXTURE]
              and core.git(ROOT, 'rev-parse', '--verify', 'HEAD^{commit}').decode().strip() == CANDIDATE,
              'historical approval or source HEAD changed')
    print(json.dumps(dict(candidate_commit=CANDIDATE, fixture_path=FIXTURE,
        fixture_bytes=len(raw), fixture_sha256=fixture_sha, gate_path=GATE,
        gate_before_sha256=core.sha(original), gate_after_sha256=core.sha(changed),
        proposal_sha256=PROPOSAL_SHA256, comparison_sha256=COMPARISON_SHA256,
        review_file=str(args.review_file), review_sha256=args.review_sha256,
        review_reference=args.review_reference, historical_fixture_sha256=core.HISTORICAL_SHA,
        predecessor_successor_sha256=core.PREDECESSOR_SHA,
        activation_helper_sha256=core.sha(Path(__file__).read_bytes()),
        scope='Explicit reviewed successor selection; final actual-HEAD qualification still required.'),
        sort_keys=True))


if __name__ == '__main__':
    main()
