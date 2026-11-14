#!/usr/bin/env python3
"""2026-11-12 #5967: audit saved baseline evidence and unchanged success reader.
Inputs: own source/base Git object and offline test outputs; output: JSON proof.
Read-only apart from the new audit receipt in sibling scratch.
"""
import ast
import hashlib
import json
from pathlib import Path
import subprocess

root = Path(__file__).resolve().parents[2]
scratch = root.parent / 'scratch-h3-failure-record-20261112'
path = 'src/data_sheets_schema/native_execution_orchestration.py'
base = subprocess.check_output(['/usr/bin/git', '-C', str(root), 'show',
    'c1ad9baa19a5b938d7976541bed27a73eee32d8c:' + path])
current = (root / path).read_bytes()
def function(raw):
    return next(node for node in ast.parse(raw).body if isinstance(node, ast.FunctionDef) and node.name == 'read_final')
old, new = function(base), function(current)
assert ast.dump(ast.Module(body=old.body[2:], type_ignores=[])) == ast.dump(ast.Module(body=new.body[4:], type_ignores=[]))
cohort = scratch / 'tests/base-public'
artifacts = []
for name in ('started.json', 'registration.json', 'subscription-guard.json', 'subscription-dispatched.json',
             'runtime-observation.json', 'keep-awake.json', 'transcript.jsonl', 'control.jsonl',
             'stderr.txt', 'final.json', 'published.json', 'actual-result.json'):
    for file in (cohort / 'cases').rglob(name):
        if file.parent.name not in ('native-attempt', 'native-evidence', 'native26'):
            continue
        raw = file.read_bytes()
        artifacts.append({'path': str(file), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()})
log = (cohort / 'pytest.log').read_text()
result = {'success_readback_body_after_diagnostic_dispatch_ast_identical_to_base': True,
          'base_failure_completed': (cohort / 'outcome.json').exists(),
          'home_validation_refusal_in_log': 'synthetic HOME must contain no account or configuration artifacts' in log,
          'secondary_publication_refusal_in_log': 'native lifecycle or publication failed after the original error' in log,
          'artifacts': artifacts, 'search': 'Path.rglob includes hidden and gitignored files'}
output = scratch / 'failure-audit.json'
output.write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps({'path': str(output), 'sha256': hashlib.sha256(output.read_bytes()).hexdigest(),
                  **{key: val for key, val in result.items() if key not in ('artifacts', 'search')}}))
