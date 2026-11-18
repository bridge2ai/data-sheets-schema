"""Apply the reviewed current-CI scheduling estimates for issue 6289; 2026-11-18.

Inputs: the measured base, F1 sidecar, reviewed F3 map and evidence in scratch.
Outputs: updated sidecar plus an application receipt; no measured-history edits.
Failed-path times and censored worker occupancy remain qualified scheduling hints.
"""
import argparse
import hashlib
import json
from pathlib import Path


def pin(path):
    raw = path.read_bytes()
    return {'path': str(path), 'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--evidence', type=Path, required=True)
    parser.add_argument('--receipt', type=Path, required=True)
    args = parser.parse_args()
    base = args.root / 'utils/ci_test_durations.json'
    sidecar = args.root / 'utils/ci_scheduling_estimates.json'
    base_raw = base.read_bytes()
    measured = json.loads(base_raw)['file_seconds']
    before = pin(sidecar)
    value = json.loads(sidecar.read_bytes())
    assert value['base_sha256'] == hashlib.sha256(base_raw).hexdigest()
    candidate = args.evidence / 'candidate-effective-weights-reviewed.json'
    provenance = args.evidence / 'reviewed-estimate-provenance.json'
    inventory = args.evidence / 'pending-inventory.json'
    weights = json.loads(candidate.read_bytes())['file_seconds']
    details = json.loads(provenance.read_bytes())
    assert details['recommended_weights']['sha256'] == pin(candidate)['sha256']
    for row in details['sources']['artifacts']:
        assert pin(Path(row['input']['path'])) == row['input']
    value['file_seconds'] = {key: seconds for key, seconds in sorted(weights.items())
                             if key not in measured or measured[key] != seconds}
    assert {**measured, **value['file_seconds']} == weights
    value['source']['ci_refresh_44235627132_20261118'] = {
        'run_id': 44235627132,
        'source_commit': '7b9497fc17672e9ede94cebdd556085c8119f3cc',
        'method': 'Replace complete ordinary-file estimates with sums of current JUnit case times. Retain earlier estimates for unmeasured files. Raise four unfinished heavy-file estimates to at least observed occupied intervals plus retained sibling work; these are censored hints, not completion bounds.',
        'artifact_xml_inputs': details['sources']['artifacts'],
        'reviewed_provenance': pin(provenance),
        'pending_inventory': pin(inventory),
        'recommended_weights': pin(candidate),
        'heavy_case_occupancy_minima': details['heavy_case_occupancy_minima'],
        'failed_current_nodes': details['failed_current_nodes'],
        'excluded_tail_occupancy_intervals': details['excluded_tail_occupancy_intervals'],
        'limits': 'Read duration belongs to a failed path. Cancelled intervals can include setup and reporting or process stalls. Tiny final-case stalls are excluded from intrinsic estimates and modeled separately. No successful completion time or ten-minute margin is established for either profile.',
    }
    sidecar.write_text(json.dumps(value, indent=2, allow_nan=False).replace(chr(64), '\\u0040') + '\n')
    assert base.read_bytes() == base_raw
    receipt = {'before': before, 'after': pin(sidecar), 'base': pin(base),
               'estimate_count': len(value['file_seconds']), 'effective_map': pin(candidate),
               'method': value['source']['ci_refresh_44235627132_20261118']['method'],
               'helper': pin(Path(__file__))}
    args.receipt.write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps(receipt, indent=2))


if __name__ == '__main__':
    main()
