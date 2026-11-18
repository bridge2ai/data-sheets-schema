"""Bind F3 simulations to the exact45 newly collected F1 cases, 2026-11-18.
Inputs: saved pre-change full collection and root's focused collection output.
Outputs: combined node inventory and explicit delta proof. No test execution.
"""
from collections import Counter
import subprocess
import codex196_fix6289b_model_20261118 as m

sim = m.module(m.R / 'scripts/adhoc/codex196_fix6289_simulate_20261118.py', 'final_collection_sim')
old = m.OLD / 'simulation-final-inputs-001/final-nodeids.json'
new = m.S.parent / 'new-test-collection.log'
before, additions = sim.collection(old), sim.collection(new)
if len(additions) != 45 or any(not node.startswith('tests/test_ci_scheduling_estimates.py::') for node in additions):
    raise ValueError('new file collection differs from root report')
if set(before) & set(additions):
    raise ValueError('new test overlaps previous collection')
after = before + additions
after.sort(key=lambda node: node.split('::', 1)[0])
if Counter(after) != Counter(before) + Counter(additions):
    raise ValueError('collection occurrence delta differs')
m.save('final-nodeids.json', after)
m.save('final-collection-delta.json', {'source_head': subprocess.check_output(
    ['git', 'rev-parse', 'HEAD'], cwd=m.W, text=True).strip(),
    'before': m.pin(old), 'new_collected_file': m.pin(new), 'after': m.pin(m.S / 'final-nodeids.json'),
    'before_occurrences': len(before), 'added_occurrences': len(additions), 'after_occurrences': len(after),
    'added_nodeids': additions, 'producer': m.pin(m.Path(__file__)),
    'scope': 'Frozen full collection plus exact newly collected test-file delta; root will compare full collection independently.'})
print(m.encode({'collection': m.pin(m.S / 'final-nodeids.json'),
                'before': len(before), 'added': len(additions), 'after': len(after)}).decode())
