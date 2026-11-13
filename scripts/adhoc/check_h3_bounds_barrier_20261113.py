"""2026-11-13 codex197: read one saved packet with the new continuation barrier.

Inputs: unchanged final-format-04 config and packet; outputs: fresh pinned JSON
in owned resume scratch. No builder, validator, binary or network execution.
"""
import argparse
import json
from pathlib import Path

N = Path(__file__).resolve().parents[2]
E = N.parent
SOURCE = N / 'scripts/adhoc/run_h3_gate_stages_20261113.py'
api = dict(__name__='bounds_barrier_readback', __file__=str(SOURCE))
exec(compile(SOURCE.read_bytes(), str(SOURCE), 'exec'), api)
parser = argparse.ArgumentParser()
parser.add_argument('--role', choices=('reference', 'AI_READI', 'CM4AI', 'VOICE', 'VOICE_PEDIATRIC'), required=True)
args = parser.parse_args()
config_path = E / 'scratch-h3-gate-refinements-20261113/tests/final-format-04/stage-config.json'
row = api['authority_bounds_barrier'](json.loads(config_path.read_bytes()), args.role)
old_path = E / 'scratch-h3-gate-refinements-20261113/measurements/final-format-04-authority' / (row['project'] + '.json')
old = json.loads(old_path.read_bytes())
assert row['total_bytes'] == old['selection_authority_including_environment_bytes']
assert row['environment'] == old['environment_manifest']
assert row['within_threshold']
row.update(source=api['pin'](SOURCE), config=api['pin'](config_path), prior=api['pin'](old_path))
out = E / 'scratch-h3-resume-matrix-20261113' / ('barrier-readback-' + args.role + '.json')
print(json.dumps(api['save'](out, row), sort_keys=True))
