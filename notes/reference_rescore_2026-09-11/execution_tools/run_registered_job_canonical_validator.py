"""Execute exactly one already registered reference rating, with the frozen runner."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys

root = Path.cwd()
sys.path[:0] = [str(root / 'src'), str(root / 'scripts')]
import reference_rescore as runner

manifest_path = runner.PLAN / 'manifest.json'
assert runner.digest(manifest_path) == '3ecc08aa6aed274737505e658743729dd1c293438ac8416df42b5c6b533533f6'
manifest = json.loads(manifest_path.read_bytes())
assert manifest['budget_cap_usd_per_attempt'] == 5
job, = [job for job in manifest['jobs'] if job['id'] == sys.argv[1]]
public_commit = '2021bb6eabde8f31bbf1952b95d1bd7577d3d71b'
published_input = subprocess.check_output(['git', 'show', f"{public_commit}:{job['input']}"], cwd=root)
assert hashlib.sha256(published_input).hexdigest() == manifest['pinned_files'][job['input']]
receipt = runner.run_job(manifest, job, '/Users/marcin/.local/bin/claude')
raise SystemExit(0 if receipt['status'] == 'passed' else 1)
