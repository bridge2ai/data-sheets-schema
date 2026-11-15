"""Issue 6214, 2026-11-15: pin and CI audit; writes scratch JSON and grep evidence."""
import hashlib
import json
from pathlib import Path
import subprocess

scratch = Path('/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-callback-teardown-20261115')
source = 'src/data_sheets_schema/native_shared_callback_orchestration.py'
old = hashlib.sha256(subprocess.check_output(['git', 'show', 'HEAD:' + source])).hexdigest()
new = hashlib.sha256(Path(source).read_bytes()).hexdigest()
command = ['grep', '-rl', '--exclude-dir=.git', old, '.']
result = subprocess.run(command, capture_output=True, text=True, timeout=180)
(scratch / 'pin-hash-search.txt').write_text(result.stdout)
(scratch / 'pin-hash-search.stderr').write_text(result.stderr)
assert result.returncode in (0, 1), result.stderr
node = 'tests/test_native_shared_denials.py::test_denial_live_and_saved[Read-not_prescribed]'
from utils import pytest_shard
assert node not in pytest_shard.DEDICATED_CASE_LANES.values()
timings = json.loads(Path('utils/ci_test_durations.json').read_text())
report = dict(source=source, old=old, new=new, command=command,
    hash_references=result.stdout.splitlines(), path_references=(scratch / 'pin-path-search.txt').read_text().splitlines(),
    read_node=node, lane='ordinary', ci_pull_request_minutes=45, ci_other_minutes=60,
    synthetic_attempt_deadline_seconds=7200)
(scratch / 'audit.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2))
