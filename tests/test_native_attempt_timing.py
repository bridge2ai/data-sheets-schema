"""#6094: controller timestamps remain supplemental and join by tool identity."""
import importlib.util
import json
from pathlib import Path

from data_sheets_schema.native_attempt_timing import Timing
from tests.test_native_execution_registration_v2 import isolated_modules  # noqa: F401


def test_real_inert_controller_records_dispatch_helper_and_turns(tmp_path, isolated_modules):
    from data_sheets_schema import native_attribution_controller as controller
    controller.load_controls()
    path = Path(__file__).resolve().parents[1] / 'notes/matched_cborg_2026-09-13/native_controls/test_native_control.py'
    spec = importlib.util.spec_from_file_location('timing_inert_fixture', path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    run, root, _, _, _, _ = module.run_case.__wrapped__(tmp_path)
    code, _, checked = run()
    assert code == 0 and checked['problems'] == []
    rows = [json.loads(line) for line in (root / 'host-controller-timing.jsonl').read_text().splitlines()]
    assert rows[0]['boundary'] == 'execute_child_entry'
    dispatch = next(row for row in rows if row['boundary'] == 'child_dispatch')
    assert dispatch['dispatch_elapsed_ns'] >= rows[0]['elapsed_ns']
    assert dispatch['deadline_elapsed_ns'] - dispatch['dispatch_elapsed_ns'] == dispatch['deadline_seconds'] * 10**9
    start = next(row for row in rows if row['boundary'] == 'helper_start')
    end = next(row for row in rows if row['boundary'] == 'helper_end')
    assert start['tool_use_id'] == end['tool_use_id'] == 'synthetic_tool'
    assert start['tool_name'] == end['tool_name'] == 'Bash'
    assert start['elapsed_ns'] <= end['elapsed_ns']
    assert [row['event_type'] for row in rows if row['boundary'] == 'turn_boundary'] == ['assistant', 'user', 'result']


def test_partial_response_is_not_a_helper_start(tmp_path):
    timing = Timing(tmp_path)
    timing.decisions['r'] = {'tool_use_id': 'helper', 'classification': 'prescribed'}
    timing.queued({'type': 'control_response', 'response': {'request_id': 'r'}}, 10)
    timing.written(9)
    assert (tmp_path / 'host-controller-timing.jsonl').read_bytes() == b''
    timing.written(1)
    timing.close()
    assert json.loads((tmp_path / 'host-controller-timing.jsonl').read_bytes())['boundary'] == 'helper_start'


def test_timing_failure_does_not_replace_controller_outcome(tmp_path, monkeypatch):
    import data_sheets_schema.native_attempt_timing as module
    timing = Timing(tmp_path)
    monkeypatch.setattr(module, 'elapsed_ns', lambda: (_ for _ in ()).throw(OSError('synthetic')))
    timing.record('execute_child_entry')
    assert timing.fd is None
    assert json.loads((tmp_path / 'host-observation-error-controller-timing.json').read_bytes())['error_type'] == 'OSError'
