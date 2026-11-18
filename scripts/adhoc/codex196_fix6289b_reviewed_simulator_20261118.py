"""Create the F3 reviewed model with separate tail occupancy sensitivity, 2026-11-18.
Input: initial simulation helper. Output: reusable reviewed simulation helper.
The original helper and its result remain preserved; no code-worktree edit.
"""
from pathlib import Path
source = Path(__file__).with_name('codex196_fix6289b_simulation_20261118.py')
target = Path(__file__).with_name('codex196_fix6289b_simulation_reviewed_20261118.py')
text = source.read_text().replace("default='capacity-simulation-initial'", "default='capacity-simulation-reviewed'")
text = text.replace('candidate-effective-weights.json', 'candidate-effective-weights-reviewed.json')
text = text.replace("    floors = m.load(m.S / 'censored-node-floors.json')", "    heavy_floors = m.load(m.S / 'heavy-case-occupancy-floors.json')\n    all_floors = m.load(m.S / 'censored-node-floors.json')")
old = """    for label, removed in [('current_whole_file', []),
                           ('proposal_four_censored_case_lanes', direct_long),
                           ('sensitivity_all_denials_and_admission_lanes', sorted(set(direct_long + known_denials)))]:
"""
new = """    for label, removed, floors in [
            ('current_whole_file_heavy_minima', [], heavy_floors),
            ('current_whole_file_all_occupancy_sensitivity', [], all_floors),
            ('proposal_four_case_lanes_heavy_minima', direct_long, heavy_floors),
            ('proposal_four_case_lanes_all_occupancy_sensitivity', direct_long, all_floors)]:
"""
if old not in text:
    raise ValueError('scenario anchor differs')
text = text.replace(old, new, 1)
text = text.replace("'censoring_floors': m.pin(m.S / 'censored-node-floors.json'),", "'censoring_floors': m.pin(m.S / 'censored-node-floors.json'),\n            'heavy_case_floors': m.pin(m.S / 'heavy-case-occupancy-floors.json'),")
text = text.replace("'ordinary_occurrences': len(selected), 'profiles': profiles", "'ordinary_occurrences': len(selected), 'includes_unresolved_tail_occupancy': floors is all_floors, 'profiles': profiles")
if chr(64) in text:
    raise ValueError('forbidden character in authored helper')
target.write_text(text)
