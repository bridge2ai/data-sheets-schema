"""Verify F3 final collection against the actual local collection, 2026-11-18.
Inputs: root's full pytest collection log, prior CI-completed inventory, final
simulation inventory. Output: exact multiplicity and order proof, small handoff.
"""
from collections import Counter
import re
import subprocess
import codex196_fix6289b_model_20261118 as m

sim = m.module(m.R / 'scripts/adhoc/codex196_fix6289_simulate_20261118.py', 'full_collection_check')
log = m.S.parent / 'full-collection/logs/unit.log'
from codex196_fix6289b_tree_collection_20261118 import parse_tree
local = parse_tree(log)
errors = re.findall(r'^ERROR (tests/[^\s]+\.py)$', log.read_text(), re.M)
expected_errors = ['tests/test_fairscape_integration/test_canonical_routes.py',
                   'tests/test_fairscape_integration/test_forward_typed_projections.py',
                   'tests/test_fairscape_integration/test_nested_dataset_readback.py']
if sorted(errors) != sorted(expected_errors):
    raise ValueError('local collection error set differs')
before = sim.collection(m.OLD / 'simulation-final-inputs-001/final-nodeids.json')
additions = sim.collection(m.S.parent / 'new-test-collection.log')
old_local = [node for node in before if node.split('::', 1)[0] not in errors]
supplement = [node for node in before if node.split('::', 1)[0] in errors]
if Counter(local) != Counter(old_local) + Counter(additions):
    raise ValueError('actual local collection differs from exact old local plus new cases')
final = sim.collection(m.S / 'final-nodeids.json')
combined = local + supplement
combined.sort(key=lambda node: node.split('::', 1)[0])
if combined != final:
    raise ValueError('actual full collection plus unchanged CI supplement differs in count or order')
if len(local) != 27654 or len(supplement) != 426 or len(final) != 28080:
    raise ValueError('final counts differ from collection receipts')
value = {'head': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=m.W, text=True).strip(),
    'local_occurrences': len(local), 'previous_local_occurrences': len(old_local),
    'added_occurrences': len(additions), 'unchanged_fairscape_supplement_occurrences': len(supplement),
    'final_occurrences': len(final), 'error_files': errors,
    'exact_counter_match': True, 'exact_final_order_match': True,
    'local_collection': m.pin(log), 'prior_full_collection': m.pin(m.OLD / 'simulation-final-inputs-001/final-nodeids.json'),
    'new_file_collection': m.pin(m.S.parent / 'new-test-collection.log'),
    'final_simulation_collection': m.pin(m.S / 'final-nodeids.json'),
    'producer': m.pin(m.Path(__file__))}
m.save('full-collection-verification.json', value)
summary = m.load(m.S / 'capacity-summary-final.json')
summary['actual_full_collection_verification'] = m.pin(m.S / 'full-collection-verification.json')
summary['floor_provenance_verification'] = m.pin(m.S / 'floor-classification-receipt.json')
summary['digest_scope'] = 'GitHub supplies each downloaded ZIP artifact digest; extracted JUnit XML hashes are computed locally, not supplied by GitHub.'
helpers = [
    'codex196_fix6289b_capacity_20261118.py',
    'codex196_fix6289b_model_20261118.py',
    'codex196_fix6289b_inventory_check_20261118.py',
    'codex196_fix6289b_adjust_model_20261118.py',
    'codex196_fix6289b_parameter_join_20261118.py',
    'codex196_fix6289b_packet_current_20261118.py',
    'codex196_fix6289b_simulation_20261118.py',
    'codex196_fix6289b_reviewed_inputs_20261118.py',
    'codex196_fix6289b_reviewed_simulator_20261118.py',
    'codex196_fix6289b_simulation_reviewed_20261118.py',
    'codex196_fix6289b_capacity_summary_20261118.py',
    'codex196_fix6289b_final_collection_20261118.py',
    'codex196_fix6289b_floor_classification_20261118.py',
    'codex196_fix6289b_tree_collection_20261118.py',
    'codex196_fix6289b_verify_full_collection_20261118.py']
summary['helpers'] = [m.pin(m.R / 'scripts/adhoc' / name) for name in helpers]
m.save('final-package-summary.json', summary)
text = (m.S / 'capacity-summary-final.md').read_text()
old = 'The simulation collection input and hashes are retained in the JSON report. If additional tests are added afterward, rerun this script and the model using the final collected node list.'
new = ('Actual full collection verified: 27,654 local occurrences equals the previous local collection plus all45 new cases. '
       'The same426 CI-supplemented FAIRSCAPE occurrences yield28,080 final occurrences; exact multiplicity and final order both match the simulated inventory. '
       'Exactly the three documented FAIRSCAPE collection errors occurred. Proof: ' + str(m.S / 'full-collection-verification.json') + '.')
if old not in text:
    raise ValueError('summary scope sentence differs')
text = text.replace(old, new)
text += '\n\nGitHub artifact ZIP digests were verified. Extracted JUnit XML SHA-256 values were computed locally and are not GitHub-supplied digests.\n'
text += '\nFloor classification proof: four heavy cancelled cases, three unresolved cancelled tails, zero retained unmeasured scenario floors. Eight rehearsal cases now have current JUnit evidence.\n'
text += '\nRecommended sidecar values: ' + str(m.S / 'capacity-summary-final-sidecar-values.json') + '.\n'
text += '\nHelper scripts remain in the designated report worktree and are listed with hashes in ' + str(m.S / 'final-package-summary.json') + '. No source-worktree edits or commits were made by this F3 helper.\n'
text = text.replace('all45', 'all 45').replace('same426', 'same 426').replace('yield28', 'yield 28')
if chr(64) in text:
    raise ValueError('forbidden authored character')
target = m.S / 'f3-handoff.md'
target.write_text(text)
print(m.encode({'collection_proof': m.pin(m.S / 'full-collection-verification.json'),
    'package': m.pin(m.S / 'final-package-summary.json'), 'handoff': m.pin(target),
    'helper_count': len(helpers)}).decode())
