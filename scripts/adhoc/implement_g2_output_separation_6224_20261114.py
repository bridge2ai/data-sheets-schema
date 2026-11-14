#!/usr/bin/env python3
"""Implement issue 6224 output separation and exact capture root, 2026-11-14.
Inputs: committed issue-6216 preflight and synthetic launch/start/entry fixtures.
Outputs: all output checks before effects and stronger journal-preservation
assertions for the real registered capture-state fixture. Runs no tests/commits.
"""
import ast
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]


def change_function(source, name, changes):
    node, = [node for node in ast.parse(source).body if isinstance(node, ast.FunctionDef) and node.name == name]
    lines = source.splitlines(keepends=True)
    selected = ''.join(lines[node.lineno - 1:node.end_lineno])
    for old, new in changes:
        assert selected.count(old) == 1, (name, old)
        selected = selected.replace(old, new, 1)
    return ''.join(lines[:node.lineno - 1]) + selected + ''.join(lines[node.end_lineno:])


path = ROOT / 'src/data_sheets_schema/native_launch_sequence.py'
raw = path.read_text()
raw = raw.replace('def _require_packet_separation(packet, registration_raw):',
                  'def _require_output_separation(packet, guard_path, capture_root, registration_raw):', 1)
old = '''    reservations.append(Path(registered_policy(value['runtime'])['capture_state_directory']))
    if any(overlaps(packet, reserved) for reserved in reservations):
        raise ValueError('sequence packet overlaps registered reservation or capture state')
'''
new = '''    capture_state = Path(registered_policy(value['runtime'])['capture_state_directory'])
    if any(overlaps(packet, reserved) for reserved in (*reservations, capture_state)):
        raise ValueError('sequence packet overlaps registered reservation or capture state')
    if any(overlaps(guard_path, reserved) for reserved in (*reservations, capture_state)):
        raise ValueError('sequence guard overlaps registered reservation or capture state')
    # Capture intentionally writes inside its registered journal. Only this
    # exact equality is allowed; a sibling, ancestor or descendant is not it.
    if capture_root != capture_state:
        raise ValueError('sequence capture output differs from registered capture state')
    if any(overlaps(capture_root, reserved) for reserved in reservations):
        raise ValueError('sequence capture output overlaps a registered reservation')
'''
assert old in raw
raw = raw.replace(old, new, 1)
raw = raw.replace("            _require_packet_separation(packet, entry_inputs[Path(args.registration)])\n",
                  "            _require_output_separation(packet, guard_path, capture_root,\n                                       entry_inputs[Path(args.registration)])\n", 1)
compile(raw, str(path), 'exec')
path.write_text(raw)

path = ROOT / 'tests/test_native_launch_sequence.py'
raw = path.read_text()
raw = raw.replace('def paths(tmp_path, *, registration_padding=0):',
                  "def paths(tmp_path, *, registration_padding=0, attempt_directory_name='NEVER-RESERVED-ATTEMPT'):", 1)
raw = raw.replace("'attempt_directory': str(base / 'NEVER-RESERVED-ATTEMPT'),",
                  "'attempt_directory': str(base / attempt_directory_name),", 1)
raw = raw.replace("result.update({'output-directory': base / 'captures',", "result.update({'output-directory': base / 'word-state',", 1)
anchor = '\n\ndef argv(paths):\n'
helper = '''\n\ndef capture_state_snapshot(paths):
    """Ignored/hidden entries included; distinguish an absent journal root."""
    root = paths['output-directory']
    if not os.path.lexists(root):
        return None
    return {str(path.relative_to(root)): None if path.is_dir() else path.read_bytes()
            for path in root.rglob('*')}


def assert_capture_state_preserved(paths, before, *, allow_start_events=False):
    """Preserve prior journal bytes and every capture slot; allow only starts."""
    after = capture_state_snapshot(paths)
    if before is None:
        assert after is None
        return
    assert after is not None
    assert all(name in after and after[name] == raw for name, raw in before.items())
    additions = after.keys() - before.keys()
    if allow_start_events:
        for name in additions:
            assert len(Path(name).parts) == 2 and Path(name).parent == Path('events')
            assert after[name] is not None and guard.strict_json(after[name])['type'] == 'sequence_start'
    else:
        assert additions == set()
    capture_rows = lambda rows: {name: raw for name, raw in rows.items()
                                 if name == 'captures' or name.startswith('captures/')}
    assert capture_rows(after) == capture_rows(before)
'''
assert anchor in raw and 'def capture_state_snapshot' not in raw
raw = raw.replace(anchor, helper + anchor, 1)
raw = change_function(raw, 'test_delegated_start_requires_both_independent_windows', [
    ('    p = paths(tmp_path)\n', '    p = paths(tmp_path)\n    capture_before = capture_state_snapshot(p)\n'),
    ("        assert not p['output-directory'].exists()", '        assert_capture_state_preserved(p, capture_before)'),
])
compile(raw, str(path), 'exec')
path.write_text(raw)

path = ROOT / 'tests/test_native_sequence_start.py'
raw = path.read_text()
for name, creation, allow in (
        ('test_owner_start_records_are_repeatable', '    p=fixtures.paths(tmp_path)\n', True),
        ('test_sequence_start_accepts_registration_above_quota_event_limit',
         '    p = fixtures.paths(tmp_path, registration_padding=65536)\n', True),
        ('test_sequence_start_rejects_registration_above_input_limit_before_lock',
         '    p = fixtures.paths(tmp_path)\n', False),
        ('test_claim_latency_cannot_cross_delegated_start_limit', '    p=fixtures.paths(tmp_path)\n', True)):
    replacement = '    fixtures.assert_capture_state_preserved(p, capture_before' + (', allow_start_events=True)' if allow else ')')
    raw = change_function(raw, name, [
        (creation, creation + '    capture_before = fixtures.capture_state_snapshot(p)\n'),
        ("    assert not p['output-directory'].exists()", replacement),
    ])
raw = change_function(raw, 'test_missing_or_replaced_word_state_refuses_before_capture', [
    ('    calls = fixtures.fake_commands(monkeypatch, p)\n',
     '    capture_before = fixtures.capture_state_snapshot(p)\n    calls = fixtures.fake_commands(monkeypatch, p)\n'),
    ("    assert calls == [] and not p['output-directory'].exists()",
     '    assert calls == []\n    fixtures.assert_capture_state_preserved(p, capture_before)'),
])
compile(raw, str(path), 'exec')
path.write_text(raw)

path = ROOT / 'tests/test_native_launch_entry.py'
raw = path.read_text()
raw = change_function(raw, 'test_load_a_replace_with_reviewed_b_refuses_before_execution', [
    ('    p,script=setup_source(tmp_path,monkeypatch,b)\n',
     '    p,script=setup_source(tmp_path,monkeypatch,b)\n    capture_before = fixture.capture_state_snapshot(p)\n'),
    ("    assert not p['output-directory'].exists()", '    fixture.assert_capture_state_preserved(p, capture_before)'),
])
raw = change_function(raw, 'test_imported_body_refuses_even_with_reviewed_retained_bytes', [
    ("    before = {str(path): path.read_bytes() for path in (tmp_path / 'word-state').rglob('*.json')}\n",
     "    capture_before = fixture.capture_state_snapshot(p)\n    before = {str(path): path.read_bytes() for path in (tmp_path / 'word-state').rglob('*.json')}\n"),
    ("    assert not p['output-directory'].exists()", '    fixture.assert_capture_state_preserved(p, capture_before)'),
])
compile(raw, str(path), 'exec')
path.write_text(raw)
print('Output preflight and exact registered capture-state fixtures updated; no tests executed.')
