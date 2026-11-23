"""Embed reviewed PR6302 wire literals, 2026-11-21.

Input: the SHA-pinned approved profile companion. Output: only the marked
literal section of native_shared_permission_wire.py. Raw evidence is unchanged.
"""
import argparse
import base64
import hashlib
import json
from pathlib import Path


COMPANION_SHA256 = '3cc4badc14f30c968f501cb860c00515691e8ec0de7f2c5cdd21f62fb484094a'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('companion', type=Path)
    arguments = parser.parse_args()
    raw = arguments.companion.read_bytes()
    if hashlib.sha256(raw).hexdigest() != COMPANION_SHA256:
        raise ValueError('reviewed profile companion differs')
    document = json.loads(raw)
    frames = {}
    for name in ('ack', 'init', 'assistant_call', 'assistant_completion', 'bash_result', 'terminal'):
        entry = document['wire_frames']['r4'][name]
        raw_frame = base64.b64decode(entry['raw_base64'], validate=True)
        if (len(raw_frame) != entry['decoded_bytes_including_newline']
                or hashlib.sha256(raw_frame).hexdigest() != entry['decoded_sha256_including_newline']):
            raise ValueError('reviewed frame bytes differ: ' + name)
        frames[name] = json.loads(raw_frame)
    target = Path(__file__).resolve().parents[2] / 'src/data_sheets_schema/native_shared_permission_wire.py'
    text = target.read_text()
    start, end = '# reviewed-literals:begin\n', '# reviewed-literals:end'
    head, rest = text.split(start, 1)
    _, tail = rest.split(end, 1)
    literals = json.dumps(frames, sort_keys=True, indent=2, ensure_ascii=True).replace(chr(64), '\\u0040')
    section = '_REVIEWED = json.loads(r\'\'\'\n' + literals + '\n\'\'\')\n'
    target.write_text(head + start + section + end + tail)


if __name__ == '__main__':
    main()
