#!/usr/bin/env python3
"""Instrument assigned launch/capture boundaries, 2026-11-13.
Inputs: current package and synthetic capture fixture. Outputs: diagnostic-only
contexts at existing operations, with no admission, source pin or order change.
"""
import ast
from pathlib import Path

root = Path(__file__).resolve().parents[2]

def add_import(text):
    anchor = 'from __future__ import annotations\n'
    if anchor in text:
        return text.replace(anchor, anchor + '\nfrom . import native_pre_dispatch_timing as pre_timing\n', 1)
    tree = ast.parse(text)
    end = tree.body[0].end_lineno
    lines = text.splitlines(True)
    lines.insert(end, '\nfrom . import native_pre_dispatch_timing as pre_timing\n')
    return ''.join(lines)

def wrap(text, function, context):
    node = next(n for n in ast.parse(text).body if isinstance(n, ast.FunctionDef) and n.name == function)
    body = node.body[1:] if ast.get_docstring(node) is not None else node.body
    lines = text.splitlines(True)
    start, end = body[0].lineno - 1, body[-1].end_lineno
    lines[start:end] = ['    with ' + context + ':\n'] + [
        '    ' + line if line.strip() else line for line in lines[start:end]]
    return ''.join(lines)

def replace_once(text, old, new):
    assert text.count(old) == 1, old
    return text.replace(old, new)

p = root / 'src/data_sheets_schema/native_shared_registration_orchestration.py'
text = add_import(p.read_text())
text = wrap(text, 'verified', "pre_timing.step('registration.verified')")
old = '        return _require_runtime_observation(value)'
text = replace_once(text, old, '        result = _require_runtime_observation(value)\n'
    '        pre_timing.bind(result)\n        return result')
p.write_text(text)

p = root / 'src/data_sheets_schema/native_shared_execution_orchestration.py'
text = add_import(p.read_text())
for name in ('launch', 'synthetic_launch'):
    text = wrap(text, name, 'pre_timing.scope(registration_raw)')
p.write_text(text)

p = root / 'src/data_sheets_schema/native_execution_orchestration.py'
text = add_import(p.read_text())
text = replace_once(text, '    with controls.loaded_classifier() as classifier_projection:',
    "    with pre_timing.step('admission_with_classifier'), controls.loaded_classifier() as classifier_projection:")
text = replace_once(text, '    adapter = contract.make_controller(value, registration_raw)\n    contract.prewarm_controller(adapter)',
    "    with pre_timing.step('controller_prewarm'):\n"
    "        adapter = contract.make_controller(value, registration_raw)\n        contract.prewarm_controller(adapter)")
text = replace_once(text, '    with reservation_lease():',
    "    with pre_timing.step('reservation'), reservation_lease():")
text = replace_once(text, '        _sync_directory(attempt.parent)\n    durable_new',
    "        _sync_directory(attempt.parent)\n        pre_timing.record('attempt_reserved')\n"
    "    pre_timing.finish()\n    durable_new")
p.write_text(text)

p = root / 'src/data_sheets_schema/native_subscription_capture.py'
text = add_import(p.read_text())
text = wrap(text, '_current_authority', "pre_timing.step('_current_authority')")
text = wrap(text, 'current_guard_preparation',
    "pre_timing.scope(registration_raw), pre_timing.step('current_guard_preparation')")
text = wrap(text, 'capture_subscription', 'pre_timing.scope(registration_raw)')
text = replace_once(text,
    "                                    'event_sha256': sha(bytes(line)), 'event_json': line.decode()})",
    "                                    'event_sha256': sha(bytes(line)), 'event_json': line.decode()})\n"
    "                                pre_timing.record('capture_observed',\n"
    "                                    captured_at=observations[-1]['captured_at'], event_sha256=sha(bytes(line)))")
# The selected capture identity joins repeated captures without trusting this file.
text = replace_once(text, "            event = saved['selected_event']\n",
    "            event = saved['selected_event']\n"
    "            pre_timing.record('capture_selected', captured_at=event['captured_at'],\n"
    "                              event_sha256=event['event_sha256'])\n")
p.write_text(text)

p = root / 'tests/utils/native_synthetic_evidence.py'
text = p.read_text()
text = replace_once(text, "    capture_stamp = capture_now.isoformat().replace('+00:00', 'Z')\n",
    "    capture_stamp = capture_now.isoformat().replace('+00:00', 'Z')\n"
    "    from data_sheets_schema import native_pre_dispatch_timing as pre_timing\n"
    "    with pre_timing.scope(registration_raw):\n"
    "        pre_timing.bind(value)\n"
    "        pre_timing.record('capture_observed', captured_at=capture_stamp, synthetic=True)\n")
p.write_text(text)
