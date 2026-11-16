"""Read PR 5968 CI logs and inventory failures for issue 6273, 2026-11-16.

Inputs: saved pr_jobs.json and GitHub read-only job logs. Outputs: scratch logs
and failures.json. Invoke with scratch directory; --fetch downloads missing logs.
"""
import argparse
from collections import Counter
import json
from pathlib import Path
import re
import subprocess


def classify(node, detail, log):
    if 'prepared registration differs from capture authority' in detail:
        return 'known D156', 'Handled by the separate capture-authority work.'
    if 'test_subscription_expiring_during_admission' in node and 'prepared registration differs from capture authority' in log:
        return 'known D156', 'Expected subscription refusal is preempted by capture-authority refusal.'
    if 'test_native_h1_scanner_authority.py' in node or 'test_different_packet_retry_needs_new_direction' in node:
        return 'known base fix', 'Already repaired on the assigned base according to the lead.'
    if 'test_native_d128' in node:
        return 'known D128', 'Lead disposition; untouched.'
    if 'test_native_pending_receipt_gate_rules.py' in node:
        return 'new stale stub', 'Accept and assert the full manifest mode; preserve refusal assertions.'
    if 'test_typed_audit_derivations.py' in node or 'test_typed_audit_captured_assets.py' in node:
        return 'new memo scope defect', 'Bypass process memo for caller-owned derivation caches; retain assertions.'
    if 'test_wire_commit_proof_precedes_any_helper_loading' in node:
        return 'new stale fixture', 'Use the current v3 envelope shape before testing commit-proof ordering.'
    if 'test_wire_still_invokes_pinned_envelope_check' in node:
        return 'new requires lead ruling', 'Current v3 wire omits the frozen v2 envelope checker; do not remove its call assertion.'
    if 'test_launch_requires_all_authority_arguments' in node:
        return 'new CLI validation ordering', 'Check guard-pair or prepared-directory arguments before file reads; retain early-refusal assertion.'
    if 'test_native_catalog_fast_guards.py' in node:
        return 'new test initialization order', 'Reproduced by initializing the loader before catalog import; run unchanged transition assertions in a fresh interpreter.'
    if 'test_typed_json_parse_cache.py' in node:
        return 'new CI-only cache identity refusal', 'Passed unchanged in the local grouped suite; CI worker-state cause remains unresolved. Do not relax identity assertions.'
    return 'new unclassified', 'Requires investigation.'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('scratch', type=Path)
    parser.add_argument('--fetch', action='store_true')
    args = parser.parse_args()
    jobs = json.loads((args.scratch / 'pr_jobs.json').read_text())['jobs']
    rows = []
    for job in jobs:
        if job['conclusion'] != 'failure':
            continue
        path = args.scratch / f"pr_job_{job['id']}.log"
        if args.fetch and (not path.exists() or not path.stat().st_size):
            result = subprocess.run(['gh', 'api', '--allow-escape-sequences',
                f"repos/bridge2ai/data-sheets-schema/actions/jobs/{job['id']}/logs"],
                check=True, capture_output=True)
            if not result.stdout:
                raise RuntimeError(f"Empty log for {job['id']}")
            path.write_bytes(result.stdout)
        log = path.read_text()
        failures = []
        for node, detail in re.findall(r'\bFAILED (tests/[^\n]+?) - ([^\n]+)', log):
            kind, action = classify(node, detail, log)
            failures.append({'node': node, 'detail': detail, 'classification': kind, 'action': action})
        rows.append({'job': job['id'], 'name': job['name'], 'bytes': path.stat().st_size,
                     'failures': failures,
                     'capture_authority_refusal': 'prepared registration differs from capture authority' in log})
    target = args.scratch / 'failures.json'
    target.write_text(json.dumps(rows, indent=2) + '\n')
    summary = {
        'failed_jobs': len(rows),
        'failed_test_occurrences': sum(len(row['failures']) for row in rows),
        'unique_failed_nodes': len({failure['node'] for row in rows for failure in row['failures']}),
        'classifications': dict(Counter(failure['classification'] for row in rows for failure in row['failures'])),
        'pending_jobs': [job['name'] for job in jobs if job['status'] != 'completed'],
        'cancelled_jobs': [job['name'] for job in jobs if job['conclusion'] == 'cancelled'],
        'failed_jobs_without_test_summary': [row['name'] for row in rows if not row['failures']],
    }
    (args.scratch / 'failure-summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    print(json.dumps(rows, indent=2))


if __name__ == '__main__':
    main()
