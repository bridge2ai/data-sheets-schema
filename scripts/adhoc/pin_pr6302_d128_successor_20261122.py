"""Activate the separately reviewed PR6302 D128 successor, 2026-11-22.

Inputs: exact local proposal/comparison and an explicitly pinned APPROVE review.
Outputs: one new successor fixture and the unique inactive test-gate SHA literal.
The historical owner fixture is unchanged. No scanner, test, native, network,
commit or reference mutation is performed. Existing successor output refuses.
"""
import argparse
from copy import deepcopy
import importlib.util
import json
import os
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CORE = 'scripts/adhoc/compare_pr6302_d128_successor_20261122.py'
GATE = 'tests/test_native_d128_scanner_comparison.py'
FIXTURE = 'tests/fixtures/native_d128_pr6302_successor.json'
CANDIDATE = '2d4281f87816c22916562091367d4e8503745329'
PROPOSAL_SHA256 = '325bf3b08a67d6da6db0e1a90396d1546aeac3d42d0f0d528f83802974ef3334'
COMPARISON_SHA256 = '1259c7ee91bec73fa0848af24fdde3c1a3e29727513af9797ef5e92243a8a674'
INACTIVE = b'SUCCESSOR_SHA256 = None\n'


def core_module():
    spec = importlib.util.spec_from_file_location('pr6302_d128_successor_activation_core', ROOT / CORE)
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
    parser.add_argument('--proposal', type=Path, required=True)
    parser.add_argument('--proposal-sha256', required=True)
    parser.add_argument('--comparison', type=Path, required=True)
    parser.add_argument('--comparison-sha256', required=True)
    parser.add_argument('--review-file', type=Path, required=True)
    parser.add_argument('--review-sha256', required=True)
    parser.add_argument('--review-reference', required=True)
    args = parser.parse_args()
    core = core_module()
    core.need(args.proposal_sha256 == PROPOSAL_SHA256 and args.comparison_sha256 == COMPARISON_SHA256,
              'activation is restricted to the reviewed immutable proposal and comparison')
    core.need(core.git(ROOT, 'rev-parse', '--verify', 'HEAD^{commit}').decode().strip() == CANDIDATE,
              'source HEAD differs from the reviewed candidate')
    core.need(type(args.review_reference) is str and bool(args.review_reference.strip())
              and chr(64) not in args.review_reference, 'explicit plain review reference required')
    pinned = {}
    for relative in (CORE, GATE, core.HISTORICAL_FIXTURE):
        path = ROOT / relative
        core.need(path.is_file() and not path.is_symlink(), 'source input is not a regular file')
        raw = path.read_bytes()
        core.need(raw == core.git(ROOT, 'show', CANDIDATE + ':' + relative),
                  'source differs from the reviewed candidate: ' + relative)
        pinned[relative] = raw
    core.need(core.sha(pinned[core.HISTORICAL_FIXTURE]) == core.HISTORICAL_SHA,
              'historical owner fixture changed')
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
    core.need(proposal['kind'] == 'pr6302_d128_successor_proposal' and proposal['review_reference'] is None
              and proposal['comparison_evidence_sha256'] == COMPARISON_SHA256
              and proposal['reference_candidate']['commit'] == CANDIDATE
              and proposal['tool_commit'] == CANDIDATE, 'proposal identity differs')
    core.need(comparison['kind'] == 'pr6302_d128_successor_comparison'
              and comparison['status'] == 'complete_diagnostic_pending_review'
              and comparison['historical_fixture_sha256'] == core.HISTORICAL_SHA
              and comparison['historical_evidence_sha256'] == core.EVIDENCE_SHA
              and comparison['historical_owner_decision_changed'] is False,
              'comparison identity differs')
    legs = comparison['comparisons']
    core.need([leg['label'] for leg in legs] == [
        'current_tool_baseline_to_current_candidate',
        'frozen_tool_baseline_to_current_tool_baseline', 'frozen_reference_to_current_candidate']
        and legs[1]['exact_arrays_equal'] is True, 'comparison legs or frozen baseline differ')
    arrays = {name: {key: value for key, value in ledger.items()
                    if key not in ('positional_differences', 'exact_arrays_equal')}
              for name, ledger in legs[0]['arrays'].items()}
    core.need(core.same(arrays, proposal['arrays'])
              and core.same(proposal['reference_candidate'], comparison['source_manifests']['candidate']['identity'])
              and core.same(proposal['tool_assets_sha256'], core.assets(ROOT, CANDIDATE)),
              'proposal differs from the exact comparison or scanner assets')
    reviewed = deepcopy(proposal)
    reviewed.update(kind='pr6302_d128_reviewed_successor', review_reference=args.review_reference)
    core.need(set(reviewed) == set(proposal) and all(core.same(reviewed[key], value)
              for key, value in proposal.items() if key not in ('kind', 'review_reference')),
              'activation changed an unreviewed proposal field')
    raw = (json.dumps(reviewed, indent=2, sort_keys=True, ensure_ascii=True, allow_nan=False)
           .replace(chr(64), '\u0040') + '\n').encode('utf-8')
    fixture_sha = core.sha(raw)
    core.require_successor(raw, fixture_sha, core.decode(pinned[core.HISTORICAL_FIXTURE]))
    changed = original.replace(INACTIVE, ("SUCCESSOR_SHA256 = '" + fixture_sha + "'\n").encode('ascii'))
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
              and core.git(ROOT, 'rev-parse', '--verify', 'HEAD^{commit}').decode().strip() == CANDIDATE,
              'historical approval or source HEAD changed')
    print(json.dumps(dict(candidate_commit=CANDIDATE, fixture_path=FIXTURE,
        fixture_bytes=len(raw), fixture_sha256=fixture_sha, gate_path=GATE,
        gate_before_sha256=core.sha(original), gate_after_sha256=core.sha(changed),
        proposal_sha256=PROPOSAL_SHA256, comparison_sha256=COMPARISON_SHA256,
        review_file=str(args.review_file), review_sha256=args.review_sha256,
        review_reference=args.review_reference, historical_fixture_sha256=core.HISTORICAL_SHA,
        activation_helper_sha256=core.sha(Path(__file__).read_bytes()),
        scope='Explicit reviewed successor selection; final actual-HEAD qualification still required.'),
        sort_keys=True))


if __name__ == '__main__':
    main()
