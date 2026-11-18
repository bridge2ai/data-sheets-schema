"""Audit prior collection versus current CI identities for issue 6289, 2026-11-18.
Inputs: frozen collection, cancelled logs, recorded weights. Output: small audit.
"""
from collections import Counter
import codex196_fix6289b_model_20261118 as m

sim = m.module(m.R / 'scripts/adhoc/codex196_fix6289_simulate_20261118.py', 'inventory_simulator')
sharder, _ = sim.load_sharder(m.W)
previous = m.load(m.OLD / 'simulation-final-inputs-001/nominal.json')
all_nodes = sim.collection(m.Path(previous['inputs']['collection']['path']))
ordinary = sharder.partition_lanes(all_nodes)['ordinary']
weights = m.load(m.Path(previous['inputs']['weights']['path']))['file_seconds']
assignment = sharder.balanced_files(Counter(n.split('::', 1)[0] for n in ordinary), 12, weights)
rows = {}
for shard, row in m.load(m.S / 'cancelled-shards.json')['shards'].items():
    selected = Counter(n for n in ordinary if assignment[n.split('::', 1)[0]] == int(shard))
    starts = Counter(item['node'] for item in row['starts'])
    finishes = Counter(item['node'] for item in row['finishes'])
    rows[shard] = {'model_count': sum(selected.values()), 'ci_count': row['items'],
        'unexpected_starts': list((starts - selected).elements()),
        'unexpected_finishes': list((finishes - selected).elements()),
        'unstarted_expected': list((selected - starts).elements()),
        'not_completed': list((selected - finishes).elements())}
m.save('inventory-check.json', rows)
print(m.encode(rows).decode())
