"""Retain A2-SOURCE-1 Write evidence for PR 6302, 2026-11-22.

Inputs: completed round-three A2 trace and four created responses, read-only.
Output: lossless base64 fixture with source pins and exact physical Write rows.
Only stdlib is used. No project imports, native process, provider or network.
Use --check to compare the existing pack without writing any output.
"""

import argparse
import base64
import hashlib
import json
from pathlib import Path
import stat


REPOSITORY = Path(__file__).resolve().parents[2]
SOURCE = REPOSITORY.parent / (
    'scratch-diagnostic-stop-traces-20261122-round3-plan-a-03/'
    'run/CHORUS-settled-canary/settled')
OUTPUT = REPOSITORY / 'tests/fixtures/native_permission_2_1_325/round3_write_results.json'
FILES = ('transcript.jsonl', 'control.jsonl', 'launch.before.json',
         'evidence_root/projection.json')
WRITES = (
    ('response_receipt_write', 14, '49c78aff165b869749321f033642a2db8640cb2de475e71d91fbc17c6996104e'),
    ('response_worker_write', 23, 'db2e4d2ec3d8b9103ec1cf743d2c6d03557d667f0aef258c8b103983b7ac5c49'),
    ('response_omission_write', 32, 'fe620ed788cb52e674dc82921cb9466a3179f524000ebe321c99a8d2e3c9976d'),
    ('response_integration_write', 41, '47d6aa3bdcc21f3209a05a1174124a056205132f42a6cf3e8e808591a12f04b5'),
)


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def identity(raw):
    return {'decoded_bytes': len(raw), 'decoded_sha256': digest(raw)}


def encoded(raw):
    return {**identity(raw), 'encoding': 'base64',
            'raw_base64': base64.b64encode(raw).decode('ascii')}


def read_regular(path):
    info = path.lstat()
    if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
        raise ValueError('expected single-link regular source: ' + str(path))
    return path.read_bytes()


def physical_rows(raw):
    if not raw.endswith(b'\n'):
        raise ValueError('original JSONL has an incomplete final physical row')
    rows = [line + b'\n' for line in raw.split(b'\n')[:-1]]
    if any(not line.strip() or type(json.loads(line)) is not dict for line in rows):
        raise ValueError('original JSONL has a blank or non-object row')
    return rows


def collect():
    captured = {}

    def retain(relative):
        path = SOURCE / relative
        raw = read_regular(path)
        captured[str(path)] = raw
        return {'original_path': str(path), **encoded(raw)}

    files = {name: retain(name) for name in FILES}
    native = physical_rows(captured[str(SOURCE / 'transcript.jsonl')])
    control = physical_rows(captured[str(SOURCE / 'control.jsonl')])
    parent = [json.loads(row) for row in control]

    def frame(relative, number):
        rows = native if relative == 'transcript.jsonl' else control
        return {'source_file': relative, 'physical_line': number,
                'source_sha256': files[relative]['decoded_sha256'],
                **encoded(rows[number - 1])}

    writes = {}
    for ordinal, (name, number, expected_sha) in enumerate(WRITES, 1):
        call = json.loads(native[number - 3])
        callback = json.loads(native[number - 2])
        result = json.loads(native[number - 1])
        block = call['message']['content'][0]
        if (digest(native[number - 1]) != expected_sha or block['id'] != name
                or block['name'] != 'Write'
                or callback['request']['input']['tool_use_id'] != name
                or callback['request']['input']['tool_input'] != block['input']
                or result['message']['content'][0]['tool_use_id'] != name):
            raise ValueError('reviewed physical Write frames or call join changed')
        decisions = [index for index, row in enumerate(parent, 1)
                     if row.get('kind') == 'decision' and row.get('request') == callback]
        if len(decisions) != 1 or parent[decisions[0] - 1]['classification'] != 'prescribed':
            raise ValueError('Write lacks its unique original parent admission')
        relative = 'effect_root/responses/' + str(ordinal).zfill(6) + '.bin'
        response = retain(relative)
        raw = captured[str(SOURCE / relative)]
        if (block['input']['file_path'] != str(SOURCE / relative)
                or block['input']['content'].encode('utf-8') != raw
                or result['tool_use_result']['content'].encode('utf-8') != raw):
            raise ValueError('created response differs from admitted content')
        writes[name] = {
            'call': frame('transcript.jsonl', number - 2),
            'callback': frame('transcript.jsonl', number - 1),
            'result': frame('transcript.jsonl', number),
            'decision': frame('control.jsonl', decisions[0]),
            'response': response,
        }
    before = {path: identity(raw) for path, raw in sorted(captured.items())}
    after = {path: identity(read_regular(Path(path))) for path in sorted(captured)}
    if before != after:
        raise ValueError('original source changed during collection')
    script = Path(__file__).read_bytes()
    if bytes([64]) in script:
        raise ValueError('collector contains a forbidden literal character')
    pack = {
        'kind': 'round3_native_write_results', 'version': 1,
        'interpretation': 'Retained diagnostic frames only; reader recognition is not run acceptance, admission or generation success.',
        'source_root': str(SOURCE), 'source_before': before, 'source_after': after,
        'source_unchanged': True, 'files': files, 'writes': writes,
        'transcript_physical_line_count': len(native),
        'control_physical_line_count': len(control),
        'collector': {'path': 'scripts/adhoc/collect_round3_write_results_20261122.py',
                      'sha256': digest(script), 'original_files_checked_unchanged': len(captured)},
    }
    raw = (json.dumps(pack, indent=2, sort_keys=True, ensure_ascii=True, allow_nan=False) + '\n').encode()
    if bytes([64]) in raw:
        raise ValueError('fixture contains a forbidden literal character')
    return raw


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    raw = collect()
    if args.check:
        if read_regular(OUTPUT) != raw:
            raise ValueError('existing fixture differs from original evidence')
    else:
        with OUTPUT.open('xb') as stream:
            stream.write(raw)
        if read_regular(OUTPUT) != raw:
            raise ValueError('fixture readback differs')
    print(json.dumps({'fixture': str(OUTPUT), **identity(raw),
        'mode': 'checked' if args.check else 'created',
        'original_files_checked_unchanged': 8, 'result_lines': [14, 23, 32, 41]}, sort_keys=True))


if __name__ == '__main__':
    main()
