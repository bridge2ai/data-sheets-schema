"""Generate a compact F3 handoff and capacity tables, 2026-11-18.
Inputs: reviewed forecasts and recorded CI evidence. Outputs: compact JSON and
Markdown for the lead's handoff. No code changes or expensive execution.
"""
import argparse
from collections import Counter
import codex196_fix6289b_model_20261118 as m

parser = argparse.ArgumentParser()
parser.add_argument('--simulation', default='capacity-simulation-reviewed.json')
parser.add_argument('--outstem', default='capacity-summary')
args = parser.parse_args()
report = m.load(m.S / args.simulation)
pending = m.load(m.S / 'pending-inventory.json')['shards']
provenance = m.load(m.S / 'reviewed-estimate-provenance.json')
weights = m.load(m.S / 'candidate-effective-weights-reviewed.json')['file_seconds']
measured = m.load(m.W / 'utils/ci_test_durations.json')['file_seconds']
updates = {path: value for path, value in weights.items() if path not in measured or value != measured[path]}
verified_artifacts = []
for receipt_path in sorted((m.S / 'artifacts').glob('*-receipt.json')):
    receipt = m.load(receipt_path)
    archive = m.Path(receipt['archive']['path'])
    digest = m.pin(archive)['sha256']
    if receipt['artifact']['digest'] != 'sha256:' + digest:
        raise ValueError('artifact digest mismatch')
    for doc in receipt['documents']:
        if m.pin(m.Path(doc['path'])) != doc:
            raise ValueError('JUnit document changed')
    verified_artifacts.append({'shard': int(receipt['artifact']['name'].split('shard')[1]),
        'artifact_id': receipt['artifact']['id'], 'sha256': digest,
        'testcase_occurrences': receipt['testcase_occurrences']})
rows = []
for scenario in report['scenarios']:
    for profile in scenario['profiles']:
        worst = max(profile['rows'], key=lambda row: row['predicted_job_seconds'])
        rows.append({'scenario': scenario['label'], 'shards': profile['shards'],
            'worst_shard': worst['shard'], 'worst_seconds': worst['predicted_job_seconds'],
            'minimum_margin_seconds': worst['margin_seconds'],
            'all_shards_meet_600_second_margin': profile['all_shards_meet_margin']})
result = {'answer': 'Whole-file balancing cannot support the requested PR margin on retained current-run occupancy evidence. Four separate heavy-case lanes are the smallest structural alternative for the individual obstructions; unresolved tail stalls and successful Read duration still prevent a capacity claim.',
    'simulation': m.pin(m.S / args.simulation), 'collection': report['collection'],
    'collection_input': report['inputs']['collection'],
    'pending': pending, 'summary_rows': rows,
    'verified_artifacts': verified_artifacts,
    'artifact_occurrences': sum(row['testcase_occurrences'] for row in verified_artifacts),
    'measured_files_current_run': len(provenance['current_junit_file_seconds']),
    'effective_weight_entries': len(weights), 'sidecar_override_entries': len(updates),
    'four_proposed_nodes': report['single_case_obstruction'],
    'current_failed_nodes': provenance['failed_current_nodes'],
    'heavy_case_occupancy_minima': provenance['heavy_case_occupancy_minima'],
    'unresolved_tail_occupancy': provenance['excluded_tail_occupancy_intervals'],
    'maximum_observed_non_pytest_job_seconds': max(row['non_pytest_difference_seconds'] for row in
        report['model']['current_ci_overhead_observations']),
    'recommended_weights': m.pin(m.S / 'candidate-effective-weights-reviewed.json'),
    'provenance': m.pin(m.S / 'reviewed-estimate-provenance.json'),
    'producer': m.pin(m.Path(__file__))}
m.save(args.outstem + '.json', result)
m.save(args.outstem + '-sidecar-values.json', updates)
lines = [result['answer'], '',
    'No test is removed, split, or newly dedicated by this analysis. The lane alternative requires the lead decision.', '',
    '| Scenario | Shards | Worst shard | Predicted seconds | Minimum margin seconds | All margins at least 600 seconds |',
    '|---|---:|---:|---:|---:|---|']
for row in rows:
    lines.append('| ' + ' | '.join(map(str, row.values())) + ' |')
lines += ['', 'Main reviewed scenario, per shard:', '',
    '| Profile | Shard | Predicted seconds | Margin seconds |', '|---|---:|---:|---:|']
for profile in report['scenarios'][0]['profiles']:
    for row in profile['rows']:
        lines.append('| ' + ' | '.join(map(str, (profile['shards'], row['shard'],
            row['predicted_job_seconds'], row['margin_seconds']))) + ' |')
lines += ['', 'Exact cancelled inventory:', '']
for shard, row in sorted(pending.items(), key=lambda pair: int(pair[0])):
    lines += [f"Shard {shard}: {row['completed']} completed of {row['collected']} collected.", '']
    for item in row['unfinished']:
        lines.append(f"- Started without an observed outcome: `{item['node']}`; log-start to cancellation {item['elapsed_until_cancellation_seconds']:.6f} seconds.")
    for node in row['unstarted']:
        lines.append(f'- No observed start: `{node}`.')
    lines.append('')
lines += [f"Downloaded and hash-verified {len(verified_artifacts)} artifacts with {result['artifact_occurrences']} testcase occurrences and {result['measured_files_current_run']} measured files. This includes failed shards; Read is a failed-path duration. The tiny tail intervals are excluded from scheduling estimates and retained only as separate protocol-occupancy sensitivity.", '',
    'Current packet cold setup maximum: 765.20 seconds. Every model uses the real installed xdist load scheduler, the candidate initial-pair ordering, four workers, and 180 seconds of non-test allowance. Missing successful completion times and log buffering/hook stalls remain uncertainty. No full native lifecycle was run.', '',
    'The four proposed case lanes cannot inherit a claimed ten-minute margin from this model: their completed times are not observed. Existing native-public jobs have a 60-minute limit; merely adding these cases to that matrix cannot certify a margin or completion. Dedicated job budget and verification require the lead decision.', '',
    'The simulation collection input and hashes are retained in the JSON report. If additional tests are added afterward, rerun this script and the model using the final collected node list.', '']
text = '\n'.join(lines)
if chr(64) in text:
    raise ValueError('forbidden authored character')
path = m.S / (args.outstem + '.md')
path.write_text(text)
print(m.encode({'summary': m.pin(m.S / (args.outstem + '.json')), 'handoff_fragment': m.pin(path),
    'override_entries': len(updates), 'simulation_rows': rows,
    'max_observed_non_pytest_seconds': result['maximum_observed_non_pytest_job_seconds']}).decode())
