#!/usr/bin/env python3
"""H1-420-F1: tighten exact sidecar snapshot contract, 2026-11-13.
Input/output: tests/test_native_shared_execution_failure.py in this branch.
Retains forbidden callbacks and every non-sidecar byte; no production changes.
"""
from pathlib import Path
p = Path(__file__).resolve().parents[2] / 'tests/test_native_shared_execution_failure.py'
s = p.read_text()
s = s.replace('import os\n', 'import os\nimport json\n', 1)
old = """    monkeypatch.chdir(authority.ROOT)
    case = make_case(tmp_path / 'missing-authority')
"""
new = """    from data_sheets_schema import native_pre_dispatch_timing as timing
    monkeypatch.chdir(authority.ROOT)
    traces = []
    handoff = timing._handoff
    def remember(trace):
        traces.append(trace)
        handoff(trace)
    monkeypatch.setattr(timing, '_handoff', remember)
    case = make_case(tmp_path / 'missing-authority')
    # Observe the real asynchronous writer only after preparation returns.
    for trace in traces:
        assert trace._persisted.wait(5)
    traces.clear()
    digest = c.sha(case['raw'])
    sidecar = Path(case['value']['attempt_directory']).parent / (
        'host-pre-dispatch-' + digest + '.jsonl')
    relative_sidecar = str(sidecar.relative_to(case['root']))
"""
assert s.count(old) == 1
s = s.replace(old, new)
old = """    assert {str(item.relative_to(case['root'])): item.read_bytes()
        for item in case['root'].rglob('*') if item.is_file()} == before
"""
new = """    assert len(traces) == 1
    trace = traces[0]
    assert trace._persisted.wait(5)  # Never wait inside admission or its lock.
    assert trace.path == sidecar and trace.identity == digest
    assert not trace.disabled
    after = {str(item.relative_to(case['root'])): item.read_bytes()
        for item in case['root'].rglob('*') if item.is_file()}
    # Exactly one permitted path, with every original byte preserved as prefix.
    original = before.pop(relative_sidecar, b'')
    current = after.pop(relative_sidecar)
    assert after == before
    assert current.startswith(original)
    appended = current[len(original):]
    assert appended and appended.endswith(b'\\n')
    lines = appended.splitlines()
    assert 0 < len(lines) <= timing.MAX_BUFFER
    assert all(len(line) + 1 <= 4096 for line in lines)
    rows = [json.loads(line) for line in lines]
    # Refusal happens before admission/reservation. Only complete verification
    # spans for this launch may be appended; no wildcard telemetry exemption.
    assert len(rows) % 2 == 0
    for index, row in enumerate(rows):
        assert set(row) == {'boundary', 'elapsed_ns', 'wall_ns',
            'registration_sha256', 'pid', 'trace_id', 'phase', 'step_id'} | (
                {'error_type'} if index % 2 else set())
        assert row['boundary'] == 'registration.verified'
        assert row['registration_sha256'] == digest
        assert row['pid'] == os.getpid() and row['trace_id'] == trace.trace_id
        assert row['phase'] == ('end' if index % 2 else 'start')
        assert row['step_id'] == index // 2 + 1
        assert type(row['elapsed_ns']) is int and row['elapsed_ns'] > 0
        assert type(row['wall_ns']) is int and row['wall_ns'] > 0
        if index:
            assert row['elapsed_ns'] >= rows[index - 1]['elapsed_ns']
        if index % 2:
            assert row['error_type'] is None
"""
assert s.count(old) == 1
p.write_text(s.replace(old, new))
