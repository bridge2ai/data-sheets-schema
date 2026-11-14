"""U3-E 2026-11-08 final single-entry codex handoff.
Input: scratch/status-entry.md; output: one primary STATUS insertion plus exact
before/after evidence in assigned scratch. Run only after final report verification.
"""
from pathlib import Path
import os
import stat
ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT.parent / 'scratch-native-u1u3'
TARGET = ROOT.parent.parent / 'data-sheets-schema/notes/coordination/STATUS.md'
MARKER = 'U3-E combined assembly handoff'
def main():
    entry = (OUT / 'status-entry.md').read_text()
    assert entry.startswith('- ') and entry.count('\n- ') == 0 and MARKER in entry and '@' not in entry
    before = TARGET.read_bytes()
    info = TARGET.stat()
    header = b'\n### codex\n'
    assert before.count(header) == 1 and MARKER.encode() not in before
    addition = ('\n' + entry.rstrip() + '\n').encode()
    after = before.replace(header, header + addition, 1)
    with (OUT / 'status-before.md').open('xb') as stream:
        stream.write(before)
    pending = OUT / 'status-pending.md'
    with pending.open('xb') as stream:
        stream.write(after)
        stream.flush()
        os.fsync(stream.fileno())
    os.chmod(pending, stat.S_IMODE(info.st_mode))
    assert TARGET.stat().st_mtime_ns == info.st_mtime_ns and TARGET.read_bytes() == before
    assert pending.stat().st_dev == TARGET.stat().st_dev
    os.replace(pending, TARGET)
    actual = TARGET.read_bytes()
    assert actual == after and actual.count(MARKER.encode()) == 1
    (OUT / 'status-after.md').write_bytes(actual)
    print('Verified exactly one codex STATUS entry; stop.')
if __name__ == '__main__':
    main()

