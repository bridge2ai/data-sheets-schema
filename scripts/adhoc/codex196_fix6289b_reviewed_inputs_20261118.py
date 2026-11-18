"""Separate intrinsic scheduling estimates from unknown tail occupancy, 2026-11-18.
Inputs: F3 JUnit joins, cancelled inventory, prior weights. Outputs: reviewed
candidate weights and distinct heavy-case/tail occupancy sensitivity inputs.
No code worktree change. Serves issue 6289 and PR 5968.
"""
from collections import Counter
import codex196_fix6289b_model_20261118 as m

sim = m.module(m.R / 'scripts/adhoc/codex196_fix6289_simulate_20261118.py', 'reviewed_sim')
prior = m.load(m.OLD / 'simulation-final-inputs-001/nominal.json')
weights = dict(m.load(m.Path(prior['inputs']['weights']['path']))['file_seconds'])
provenance = m.load(m.S / 'file-estimate-provenance.json')
weights.update(provenance['current_junit_file_seconds'])
nodes = sim.collection(m.Path(prior['inputs']['collection']['path']))
observed = m.load(m.S / 'combined-node-seconds.json')
all_floors = m.load(m.S / 'censored-node-floors.json')
heavy, tail = {}, {}
for node, value in all_floors.items():
    (heavy if 'test_native_shared_denials' in node or 'test_native_admission_failure.py::' in node else tail)[node] = value
for path in {node.split('::', 1)[0] for node in heavy}:
    total = sum(max(observed.get(node, 0), heavy.get(node, 0)) for node in nodes
                if node.startswith(path + '::'))
    weights[path] = max(weights.get(path, 0), round(total, 3))
weights = {path: max(0.001, value) for path, value in weights.items()}
m.save('candidate-effective-weights-reviewed.json', {'schema_version': 1, 'file_seconds': weights})
m.save('heavy-case-occupancy-floors.json', heavy)
m.save('unresolved-tail-occupancy.json', {
    'intervals': tail,
    'meaning': 'Logged start without observed call outcome at cancellation; no intrinsic duration conclusion. Can include setup, report-hook, or process stall. Excluded from recommended file estimates; used only as a separate sensitivity.'})
m.save('reviewed-estimate-provenance.json', {
    'sources': provenance['sources'],
    'current_junit_file_seconds': provenance['current_junit_file_seconds'],
    'failed_current_nodes': provenance['failed_current_nodes'],
    'heavy_case_occupancy_minima': heavy,
    'heavy_case_weight_policy': 'Retain prior estimate or observed occupied lower floor, whichever is larger. These are conservative scheduling hints for incomplete cases, never successful completion measurements or upper bounds.',
    'excluded_tail_occupancy_intervals': tail,
    'recommended_weights': m.pin(m.S / 'candidate-effective-weights-reviewed.json'),
    'producer': m.pin(m.Path(__file__))})
print(m.encode({'weights': m.pin(m.S / 'candidate-effective-weights-reviewed.json'),
    'heavy_case_count': len(heavy), 'excluded_tail_case_count': len(tail),
    'heavy_file_estimates': {path: value for path, value in weights.items() if
        any(node.startswith(path + '::') for node in heavy)},
    'denial_read_seconds_failed_path': weights['tests/test_native_shared_denials_read.py'],
    'bash_unclassifiable_measured_seconds': weights['tests/test_native_shared_denials.py']}).decode())
