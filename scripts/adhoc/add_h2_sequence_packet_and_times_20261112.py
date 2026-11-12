#!/usr/bin/env python3
"""Add proposed N1 script-byte retention and delegated time gates, 2026-11-12.
Input/output: native_launch_sequence.py after the reviewed draft repair.
Serves helper-2 launch-sequence Part B; no commands or authority are executed.
"""
from pathlib import Path
path = Path(__file__).resolve().parents[2] / 'src/data_sheets_schema/native_launch_sequence.py'
text = path.read_text()
text = text.replace("START_FILENAME = 'sequence-start.json'", "START_FILENAME = 'sequence-start.json'\nSCRIPT_FILENAME = 'sequence-script.py'")
anchor = '\ndef _path(value):'
addition = '''
def _strict_utc(value):
    if type(value) is not str or re.fullmatch(
            r'[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(?:\\.[0-9]{1,6})?Z', value) is None:
        raise ValueError('delegated start times must be strict UTC timestamps')
    return datetime.fromisoformat(value[:-1] + '+00:00')


def _delegation(direction, confirmation, now):
    if (direction is None) != (confirmation is None):
        raise ValueError('delegated start needs both recorded times')
    if direction is None:
        return
    current = _strict_utc(now)
    for value in (direction, confirmation):
        seconds = (current - _strict_utc(value)).total_seconds()
        if not 0 <= seconds <= 1800:
            raise ValueError('delegated start must be within thirty minutes after both recorded times')

'''
assert text.count(anchor) == 1
text = text.replace(anchor, addition + anchor)
text = text.replace('    return result\n\n\ndef main', "    result.add_argument('--direction-recorded-at', help='Recorded UTC time of the owner direction')\n    result.add_argument('--host-confirmed-at', help='Recorded UTC time of the owner host-state confirmation')\n    return result\n\n\ndef main")
text = text.replace("'capture_manifest': None, 'guard_sha256': None, 'steps': []}",
    "'capture_manifest': None, 'guard_sha256': None, 'steps': [],\n              'direction_recorded_at': args.direction_recorded_at,\n              'host_confirmed_at': args.host_confirmed_at, 'delegation_checked_at': None,\n              'script_path': None}")
text = text.replace("sequence_candidate, packet / START_FILENAME, guard_path]", "sequence_candidate, packet / START_FILENAME, packet / SCRIPT_FILENAME, guard_path]")
text = text.replace('        sequence = sequence_candidate\n', '''        sequence = sequence_candidate
        script_path = packet / SCRIPT_FILENAME
        _write_new(script_path, guard.read_regular(Path(__file__).resolve(), limit=MAX_COMMAND_OUTPUT_BYTES))
        record['script_path'] = str(script_path)
        _delegation(args.direction_recorded_at, args.host_confirmed_at, started)
''')
text = text.replace('        captured = _run_step(COMMANDS[0]', '''        record['delegation_checked_at'] = _utc_now()
        _delegation(args.direction_recorded_at, args.host_confirmed_at, record['delegation_checked_at'])
        captured = _run_step(COMMANDS[0]''')
path.write_text(text)
