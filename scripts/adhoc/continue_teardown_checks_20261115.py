"""Issue 6214, 2026-11-15: run only unfinished collected cases; save the plan."""
import json
from pathlib import Path
import subprocess
import sys
scratch = Path('/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-callback-teardown-20261115')
summary = json.loads((scratch / 'summary.json').read_text())
assert summary['runs']['final-required']['timed_out']
nodes = summary['remaining_nodeids']
assert nodes and all(node.startswith('tests/test_generation_specificity_skill.py::') for node in nodes)
command = [sys.executable, 'scripts/adhoc/run_teardown_checks_20261115.py', 'remaining-required', '900', '-q', '-n', '4', *nodes]
(scratch / 'remaining-plan.json').write_text(json.dumps(dict(command=command, nodes=nodes), indent=2) + '\n')
subprocess.run(command, check=True, timeout=930)
