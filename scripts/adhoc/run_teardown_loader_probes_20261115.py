"""Issue 6214, 2026-11-15: bounded real-loader probes; scratch JSON evidence."""
import json
import os
from pathlib import Path
import subprocess
import sys
scratch = Path('/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-callback-teardown-20261115')
records = []
for mode in ('normal', 'exception'):
    command = [sys.executable, 'scripts/adhoc/probe_teardown_loader_20261115.py', str(scratch), mode]
    result = subprocess.run(command, env=dict(os.environ, PYTHONPATH=str(Path.cwd() / 'src'), PYTHONDONTWRITEBYTECODE='1'), capture_output=True, text=True, timeout=8)
    records.append(dict(command=command, returncode=result.returncode, stdout=result.stdout, stderr=result.stderr))
    (scratch / 'loader-probes.json').write_text(json.dumps(records, indent=2) + '\n')
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)['loader_alive_during_and_after_worker']
print(json.dumps(records, indent=2))
