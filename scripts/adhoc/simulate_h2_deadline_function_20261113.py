#!/usr/bin/env python3
"""#6170 pure-function simulation, not registered controller admission, 2026-11-13.
Inputs exact execute_child AST; outputs synthetic dispatch/suspend outcomes.
No subprocess is started and no authority loader/check is replaced or updated.
Registered integration remains blocked by the unchanged source manifests.
"""
import ast
from contextlib import ExitStack
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

R = Path(__file__).resolve().parents[2]
HP = R.parent / 'codex-native-host-power-20261113'
B = Path.home() / 'agent-work/data-sheets-schema/helper2-review-fixes-20261113'
out = B / 'deadline-function'; out.mkdir(exist_ok=False)
source = HP / 'notes/matched_cborg_2026-09-13/native_controls/run_native_canary.py'
raw = source.read_bytes()
parsed = ast.parse(raw)
nodes = [node for node in parsed.body if isinstance(node, ast.FunctionDef) and node.name in ('execute_child', 'record_then_close')]
assert len(nodes) == 2
class BudgetStop(Exception): pass
class Diagnostic:
    def __init__(self, *a): pass
    def record(self, *a, **k): pass
    def close(self): pass
rows = []
for seconds in (900, 21600, 43200):
    for scenario in ('long_admission', 'suspend_running', 'suspend_exited'):
        root = out / (str(seconds) + '-' + scenario); root.mkdir()
        instruction = root / 'instruction.txt'; instruction.write_text('pure function fixture; no child')
        state = {'elapsed': 0, 'dispatches': 0, 'cleanup': 0, 'closed': 0}
        def clock(): return state['elapsed']
        def verify(): state['elapsed'] += seconds * 10**9 * 10
        def spawn(*a, **k):
            state['dispatches'] += 1
            if scenario.startswith('suspend'): state['elapsed'] += (seconds + 1) * 10**9
            return object()
        def cleanup(process):
            assert process is not None
            state['cleanup'] += 1
        def close(): state['closed'] += 1
        proxy = SimpleNamespace(failed=SimpleNamespace(is_set=lambda: False), close_admission=close)
        namespace = {'Timing': Diagnostic, 'elapsed_ns': clock, 'Path': Path,
            'ExitStack': ExitStack, 'BudgetStop': BudgetStop,
            'subprocess': SimpleNamespace(Popen=spawn, PIPE=-1),
            'exit_check_available': lambda: True,
            'leader_exited': lambda p: scenario != 'suspend_running',
            'terminate_group': cleanup, 'exit_status': lambda p: 0,
            'HISTORY_CONTRACT': {}, 'time': SimpleNamespace(sleep=lambda seconds: None)}
        exec(compile(ast.Module(body=nodes, type_ignores=[]), str(source), 'exec'), namespace)
        caught = None
        try:
            status = namespace['execute_child'](['never-spawned'], proxy=proxy,
                instruction=instruction, attempt=root, cwd=root, env={},
                deadline_seconds=seconds, verify_launch=verify)
        except BudgetStop as exc:
            caught = str(exc); status = None
        assert state['dispatches'] == state['cleanup'] == 1
        if scenario == 'long_admission': assert status == 0 and caught is None
        else: assert caught and 'native attempt deadline elapsed' in caught
        rows.append({'seconds': seconds, 'scenario': scenario, 'status': status,
                     'exception': caught, 'synthetic_state': state, 'passed': True})
record = {'scope': 'Pure execute_child function with synthetic clocks/process objects; NOT source-admitted integration',
          'source_path': str(source), 'source_sha256': hashlib.sha256(raw).hexdigest(), 'rows': rows}
path = out / 'results.json'; path.write_text(json.dumps(record, indent=2) + '\n')
print(json.dumps({'path': str(path), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest(), 'passed': len(rows)}))
