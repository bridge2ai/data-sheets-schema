# Purpose: verify #5508 old-record refusal in the new source environment.
# Input: scratch/v1-replay saved by the exact M7 test; output: replay-refusal.json.
# Date: 2026-11-06. Read-only consumers; no native executable or provider.
import json
from pathlib import Path
from data_sheets_schema import native_attribution_registration as old
from data_sheets_schema import native_attribution_registration_v2 as new
ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT.parent/'scratch-native-u2'
raw = (OUT/'v1-replay/registration.json').read_bytes()
value = old._json(raw)
assert value['code_commit'] == '8bc90e93d736d464f98e9eedffee45f0ad8e5d3f'
assert old._code_pins() != value['checker_source_tree_sha256']
results = {}
for name, module in [('v1_in_new_environment', old), ('v2_given_v1_record', new)]:
    try:
        module.verified(raw)
    except ValueError as exc:
        results[name] = {'refused': True, 'reason': str(exc)}
    else:
        raise AssertionError('old identity was silently retargeted: '+name)
(OUT/'replay-refusal.json').write_text(json.dumps(results, indent=2)+'\n')
print(json.dumps(results))
