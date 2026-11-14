#!/usr/bin/env python3
"""Apply issue 6216 packet preflight before any output effect, 2026-11-14.
Inputs: committed issue-6208 sequence and copied-package test fixture.
Outputs: packet/reservation separation and copied pure path helper dependency.
No tests, commits, native commands or provider calls are performed.
"""
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
path = ROOT / 'src/data_sheets_schema/native_launch_sequence.py'
raw = path.read_text()
anchor = '\n\ndef _new(path):\n'
helper = '''\n\ndef _require_packet_separation(packet, registration_raw):
    """Read captured entry bytes before any packet creation or journal write."""
    from .native_path_identity import overlaps
    from .native_u4b_policy import registered_policy
    value = guard.strict_json(registration_raw)['registration']
    reservations = [_path(value[name]) for name in ('attempt_directory', 'evidence_directory')]
    reservations.append(Path(registered_policy(value['runtime'])['capture_state_directory']))
    if any(overlaps(packet, reserved) for reserved in reservations):
        raise ValueError('sequence packet overlaps registered reservation or capture state')
'''
assert anchor in raw and 'def _require_packet_separation' not in raw
raw = raw.replace(anchor, helper + anchor, 1)
anchor = "            packet = _path(args.packet_directory)\n"
assert raw.count(anchor) == 1
raw = raw.replace(anchor, anchor + "            _require_packet_separation(packet, entry_inputs[Path(args.registration)])\n", 1)
compile(raw, str(path), 'exec')
path.write_text(raw)
path = ROOT / 'tests/test_native_launch_sequence.py'
raw = path.read_text()
anchor = "                 'native_run_limits',\n"
assert raw.count(anchor) == 1
raw = raw.replace(anchor, "                 'native_run_limits', 'native_path_identity',\n", 1)
compile(raw, str(path), 'exec')
path.write_text(raw)
print('Packet separation inserted before mkdir; no tests executed.')
