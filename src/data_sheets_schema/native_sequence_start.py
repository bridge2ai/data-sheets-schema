"""Sequence starts share the existing capture-word journal and authority lock.

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
