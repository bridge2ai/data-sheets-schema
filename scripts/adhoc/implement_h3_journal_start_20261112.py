"""Apply #5992 approved local journal v2 extension, 2026-11-12.

Inputs/outputs: own native journal, sequence start and capture reader sources.
No journal state, native process, registration, or network operation.
"""
from pathlib import Path

root = Path(__file__).resolve().parents[2] / 'src/data_sheets_schema'
p = root / 'native_capture_words.py'
s = p.read_text()
s = s.replace("KIND = 'd4d_native_capture_word_journal_v1'", "PREVIOUS_KIND = 'd4d_native_capture_word_journal_v1'\nKIND = 'd4d_native_capture_word_journal_v2'\nVERSION = 2")
s = s.replace('def __init__(self, root, header, runtime, policy):', 'def __init__(self, root, header, runtime, policy, *, historical=False):')
s = s.replace('        self.root, self.header, self.runtime, self.policy = root, header, runtime, policy',
              '        self.root, self.header, self.runtime, self.policy = root, header, runtime, policy\n        self.historical = historical')
s = s.replace("            if (set(value) != expected or value['kind'] != KIND or type(value['version']) is not int\n                    or value['version'] != 1", """            if value.get('type') == 'sequence_start' and self.header['version'] == VERSION:
                expected = common | {'direction_identity', 'registration_sha256',
                                     'host_confirmed_at', 'packet_directory'}
            if (set(value) != expected or value['kind'] != self.header['kind'] or type(value['version']) is not int
                    or value['version'] != self.header['version']""")
s = s.replace("            else:\n                raise ValueError('unknown capture journal event')", """            elif value['type'] == 'sequence_start' and self.header['version'] == VERSION:
                direction = value['direction_identity']
                confirmation = value['host_confirmed_at']
                if (not events or events[-1]['word_sha256'] != value['word_sha256']
                        or any(row['type'] == 'limits_refusal' for row in events)
                        or value['registration_sha256'] != self.header['registration_sha256']):
                    raise ValueError('sequence start lacks its current recorded word')
                _path(value['packet_directory'])
                if direction is None:
                    if confirmation is not None:
                        raise ValueError('owner start cannot carry a delegated confirmation')
                else:
                    if normalize_direction(direction) != direction:
                        raise ValueError('sequence direction is not normalized UTC')
                    if any(row['type'] == 'sequence_start' and row['direction_identity'] == direction
                           for row in events):
                        raise ValueError('delegated direction already consumed')
                    if any(not 0 <= moment - _timestamp(stamp, 'delegated start') <= 1800
                           for stamp in (direction, confirmation)):
                        raise ValueError('sequence start is outside its delegated window')
            else:
                raise ValueError('unknown capture journal event')""")
s = s.replace('    def _append(self, payload, now):\n        events = self.events()',
              '    def _append(self, payload, now):\n        self._require_current_format()\n        events = self.events()')
s = s.replace("value = {'kind': KIND, 'version': 1, 'index': len(events) + 1,", "value = {'kind': KIND, 'version': VERSION, 'index': len(events) + 1,")
s = s.replace('    def activate(self, word_raw, review_raw, value, now=None):\n        require_unspent(value)',
              '    def activate(self, word_raw, review_raw, value, now=None):\n        self._require_current_format()\n        require_unspent(value)')
s = s.replace("        if events:\n            last = events[-1]\n            if last['word_sha256'] == sha(word_raw):", "        recorded = [row for row in events if row['type'] == 'word']\n        if recorded:\n            last = recorded[-1]\n            if last['word_sha256'] == sha(word_raw):")
s = s.replace("        if current:\n            if any(row['type'] == 'limits_refusal'", "        if current:\n            self._require_current_format()\n            if any(row['type'] == 'limits_refusal'")
s = s.replace("            if events[-1]['word_sha256'] != sha(word_raw):", "            if [row for row in events if row['type'] == 'word'][-1]['word_sha256'] != sha(word_raw):")
where = '    def refuse_limits(self, word_raw, terminal_raw, capture_path, now=None):'
addition = '''    def _require_current_format(self):
        if self.historical or self.header['kind'] != KIND or self.header['version'] != VERSION:
            raise ValueError('historical journal cannot authorize current activity')

    def start(self, word_raw, *, direction, confirmation, packet, now):
        """Append under the caller's word lock; no state initialization or retry."""
        self._require_current_format()
        self.require(word_raw, now)
        identity = None if direction is None else normalize_direction(direction)
        if (direction is None) != (confirmation is None):
            raise ValueError('delegated direction and confirmation must be paired')
        if identity is not None:
            if any(not 0 <= now - _timestamp(stamp, 'delegated start') <= 1800 for stamp in (identity, confirmation)):
                raise ValueError('sequence start is outside its delegated window')
            if any(row['type'] == 'sequence_start' and row['direction_identity'] == identity
                   for row in self.events()):
                raise ValueError('delegated direction already consumed; a new recorded direction is required')
        return self._append({'type': 'sequence_start', 'word_sha256': sha(word_raw),
            'direction_identity': identity, 'host_confirmed_at': confirmation,
            'registration_sha256': self.header['registration_sha256'],
            'packet_directory': str(_path(packet))}, now)

'''
assert where in s
s = s.replace(where, addition + where + '\n        self._require_current_format()')
s = s.replace('def locked(value, registration_raw, *, create=False):', 'def locked(value, registration_raw, *, create=False, historical=False):')
s = s.replace("    header = {'kind': KIND, 'version': 1,", "    if historical and create:\n        raise ValueError('historical journal access cannot create state')\n    header = {'kind': KIND, 'version': VERSION,")
s = s.replace("        if _read(root / 'authority.json') != canonical(header):", """        authority_raw = _read(root / 'authority.json')
        supplied = strict_json(authority_raw)
        if type(supplied) is dict and supplied.get('kind') == PREVIOUS_KIND:
            if not historical:
                raise ValueError('historical journal cannot authorize current activity')
            header = {**header, 'kind': PREVIOUS_KIND, 'version': 1}
        if authority_raw != canonical(header):""")
s = s.replace("Journal(root, header, value['runtime'], policy)", "Journal(root, header, value['runtime'], policy, historical=historical)")
where = '\ndef _moment(now):'
s = s.replace(where, '''
def normalize_direction(value):
    moment = _timestamp(value, 'direction identity')
    return datetime.fromtimestamp(moment, timezone.utc).isoformat(timespec='microseconds').replace('+00:00', 'Z')

''' + where)
p.write_text(s)
p = root / 'native_sequence_start.py'
p.write_text('''"""Sequence starts share the existing capture-word journal and authority lock.

The journal is local supplied evidence, not authenticated owner authority.
The sequence cannot initialize it. No separate claim directory is maintained.
"""
from . import native_capture_words as words


def claim(registration_raw, *, launch_word_raw, direction, confirmation, packet, started_at):
    """Require a recorded current word, then durably append before any child."""
    value = words.strict_json(registration_raw)['registration']
    with words.locked(value, registration_raw) as journal:
        words.require_unspent(value)
        event = journal.start(launch_word_raw, direction=direction, confirmation=confirmation,
                              packet=packet, now=words._timestamp(started_at, 'sequence start'))
        return str(journal.root / 'events' / f"{event['index']:06d}.json")
''')
p = root / 'native_launch_sequence.py'
s = p.read_text().replace("record['start_claim'] = claim(inputs[Path(args.registration)],", "record['start_claim'] = claim(inputs[Path(args.registration)], launch_word_raw=word_raw,")
assert s != p.read_text()
p.write_text(s)
p = root / 'native_subscription_capture.py'
s = p.read_text().replace('with words.locked(value, registration_raw) as journal:\n            journal.require(launch_word_raw, current=require_current)',
                         'with words.locked(value, registration_raw, historical=not require_current) as journal:\n            journal.require(launch_word_raw, current=require_current)')
assert s != p.read_text()
p.write_text(s)
