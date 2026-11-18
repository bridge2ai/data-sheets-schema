"""Verify F3 floor provenance and separate any retained scenarios, 2026-11-18.
Inputs: exact cancellation inventory and model floors. Output: classification
receipt. No source change and no reinterpretation of incomplete outcomes.
"""
import codex196_fix6289b_model_20261118 as m
pending = m.load(m.S / 'pending-inventory.json')['shards']
actual = {item['node']: item['elapsed_until_cancellation_seconds']
          for row in pending.values() for item in row['unfinished']}
floors = m.load(m.S / 'censored-node-floors.json')
heavy = m.load(m.S / 'heavy-case-occupancy-floors.json')
tails = m.load(m.S / 'unresolved-tail-occupancy.json')['intervals']
retained_scenarios = {node: value for node, value in floors.items() if node not in actual}
if any(floors.get(node) != value for node, value in actual.items()):
    raise ValueError('censored floor does not match its actual log interval')
if set(heavy) & set(tails) or set(heavy) | set(tails) != set(actual):
    raise ValueError('heavy/tail classification must partition exact cancelled observations')
if set(tails) & set(retained_scenarios):
    raise ValueError('unmeasured scenario mislabelled as cancelled tail')
measured = m.load(m.S / 'current-node-measurements.json')
rehearsal = {node: {'seconds': row['seconds'], 'outcomes': row['outcomes']}
             for node, row in measured.items() if 'test_native_canary_packet_rehearsal.py::' in node}
value = {'heavy_cancelled_nodes': heavy, 'unresolved_cancelled_tail_nodes': tails,
    'retained_unmeasured_scenarios': retained_scenarios,
    'rehearsal_current_junit': rehearsal,
    'scope': 'Retained prior unmeasured scenarios are separate from logged cancellation occupancy. Current inputs contain no retained unmeasured rehearsal floor because all rehearsal cases have current JUnit.',
    'inputs': [m.pin(m.S / name) for name in ('pending-inventory.json', 'censored-node-floors.json',
        'heavy-case-occupancy-floors.json', 'unresolved-tail-occupancy.json', 'current-node-measurements.json')],
    'producer': m.pin(m.Path(__file__))}
m.save('floor-classification-receipt.json', value)
print(m.encode({'receipt': m.pin(m.S / 'floor-classification-receipt.json'),
    'heavy': len(heavy), 'tails': len(tails), 'retained_scenarios': len(retained_scenarios),
    'rehearsal_cases_with_current_junit': len(rehearsal)}).decode())
