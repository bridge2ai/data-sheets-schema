"""Sequential final measurements with verified first-unit canary and bounds.

Input/output: assigned scratch. Lead parse-cache assignment, 2026-11-15.
Each child uses the same bounded launcher and retained fixture as the canary.
"""
import json
from pathlib import Path
import subprocess
import sys

scratch = Path(sys.argv[1]).resolve()
version = sys.argv[2] if len(sys.argv) > 2 else 'v3'
if not version.isalnum():
    raise ValueError('measurement version must be an alphanumeric directory suffix')
source = scratch / 'variant-profile-v3/consumed-integration.pickle'
for mode, profile in (('response', 'plain'), ('response', 'profile'),
                      ('publication', 'plain'), ('publication', 'profile')):
    name = 'cache-after-' + version + '-' + mode + ('-profile' if profile == 'profile' else '')
    out = scratch / name
    subprocess.run([sys.executable, 'scripts/adhoc/bounded_variant_command_20261115.py',
                    str(scratch / (name + '-run')), '900', sys.executable,
                    'scripts/adhoc/measure_parse_cache_20261115.py', str(source), str(out), mode, profile],
                   check=True, timeout=930)
    metrics = json.loads((out / 'metrics.json').read_text())
    assert metrics['parse_cache']['hits'] > 0
    assert metrics['state'] == ('checked' if mode == 'response' else 'assembly_complete')
    if mode == 'publication':
        assert metrics['published_files'] == 6
    print(json.dumps(metrics), flush=True)
