#!/usr/bin/env python3
"""Pure execute_child checks with the real alarm, 2026-11-13.
Inputs exact controller AST and admission/clock modules. Outputs saved clock,
refusal and descriptor-cleanup results. No authority loader, source repinning,
subprocess, provider or model. This is NOT registered failure publication.
"""
import ast
from contextlib import ExitStack
import fcntl
import hashlib
import json
import os
from pathlib import Path
import sys
from types import SimpleNamespace

R = Path(__file__).resolve().parents[2]
HP = R.parent / 'codex-native-host-power-20261113'
B = Path.home() / 'agent-work/data-sheets-schema/helper2-pins-admission-20261113'
sys.path.insert(0, str(HP / 'src'))
from data_sheets_schema.native_admission_timer import AdmissionTimer, AdmissionRefused
from data_sheets_schema.native_elapsed import elapsed_ns
out = B / 'admission-function'; out.mkdir(exist_ok=False)
source = HP / 'notes/matched_cborg_2026-09-13/native_controls/run_native_canary.py'
raw = source.read_bytes()
nodes = [n for n in ast.parse(raw).body if isinstance(n, ast.FunctionDef)
         and n.name in ('execute_child', 'record_then_close')]
assert len(nodes) == 2
class BudgetStop(Exception): pass
class Diagnostic:
    def __init__(self, *args): pass
    def record(self, *args, **kwargs): pass
    def close(self): pass
rows = []
cases = [(seconds, scenario) for seconds in (900, 21600, 43200)
         for scenario in ('within_admission', 'expired_admission', 'suspend_running', 'suspend_exited')]
cases.append((900, 'blocked_fifo'))
for seconds, scenario in cases:
    directory = out / (str(seconds) + '-' + scenario); directory.mkdir()
    instruction = directory / 'instruction'; instruction.write_text('inert source-function test')
    state = {'elapsed': 0, 'dispatches': 0, 'closed': 0, 'cleanup': []}
    descriptors, stops = [], []
    class Stack(ExitStack):
        def enter_context(self, cm):
            result = super().enter_context(cm)
            descriptors.append(result.fileno())
            return result
    def clock():
        return elapsed_ns() if scenario == 'blocked_fifo' else state['elapsed']
    def verify():
        if scenario == 'blocked_fifo':
            state['entered_fifo'] = True
            fd = os.open(directory / 'fifo', os.O_RDONLY)
            os.close(fd)
            raise AssertionError('unwritten FIFO returned')
        state['elapsed'] += (900 if scenario == 'expired_admission' else 899) * 10**9
    def spawn(*args, **kwargs):
        state['dispatches'] += 1
        if scenario.startswith('suspend'):
            state['elapsed'] += (seconds + 1) * 10**9
        return object()
    def close(): state['closed'] += 1
    if scenario == 'blocked_fifo': os.mkfifo(directory / 'fifo')
    proxy = SimpleNamespace(failed=SimpleNamespace(is_set=lambda: False), close_admission=close)
    namespace = dict(Timing=Diagnostic, elapsed_ns=clock, Path=Path, ExitStack=Stack,
        BudgetStop=BudgetStop, AdmissionTimer=AdmissionTimer, AdmissionRefused=AdmissionRefused,
        ADMISSION_SECONDS=.2 if scenario == 'blocked_fifo' else 900,
        subprocess=SimpleNamespace(Popen=spawn, PIPE=-1), exit_check_available=lambda: True,
        leader_exited=lambda process: scenario != 'suspend_running',
        terminate_group=lambda process: state['cleanup'].append(process is not None),
        exit_status=lambda process: 0, HISTORY_CONTRACT={}, time=SimpleNamespace(sleep=lambda seconds: None))
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(source), 'exec'), namespace)
    caught = None
    try:
        status = namespace['execute_child'](['never-spawned'], proxy=proxy, instruction=instruction,
            attempt=directory, cwd=directory, env={}, deadline_seconds=seconds,
            verify_launch=verify, record_stop=stops.append)
    except (BudgetStop, AdmissionRefused) as exc:
        caught = str(exc); status = None
    for fd in descriptors:
        try: fcntl.fcntl(fd, fcntl.F_GETFD)
        except OSError: pass
        else: raise AssertionError('controller file descriptor remained open')
    if scenario in ('expired_admission', 'blocked_fifo'):
        assert state['dispatches'] == 0 and state['cleanup'] == [False]
        assert caught == 'native admission deadline elapsed; child was not dispatched'
        assert stops == [caught]
    else:
        assert state['dispatches'] == 1 and state['cleanup'] == [True]
        if scenario == 'within_admission': assert status == 0 and caught is None
        else: assert 'native attempt deadline elapsed' in caught
    rows.append(dict(seconds=seconds, scenario=scenario, status=status, exception=caught,
        state=state, stops=stops, descriptors_closed=len(descriptors), passed=True))
record = dict(scope='Pure source-function test; NOT source-admitted integration or failure publication',
    source_sha256=hashlib.sha256(raw).hexdigest(), rows=rows)
path = out / 'results.json'; path.write_text(json.dumps(record, indent=2) + '\n')
print(json.dumps(dict(path=str(path), sha256=hashlib.sha256(path.read_bytes()).hexdigest(), passed=len(rows))))
