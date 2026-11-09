#!/usr/bin/env python3
"""Pin real quota-event fixtures and compare U4b guard routes, 2026-11-08.

Inputs: fixed efbcfffb3 Git objects; current guard; synthetic guard-component
authority. Outputs: one event-only fixture, or one new bounded scratch report.
Serves U4b A4 P1-1. Reuses the read-only inventory/parser comparison approach in
scratch-u4b-review/scripts/{rate_limit_shapes,real_event_shapes_vs_guard_v2}.py,
but reads committed objects and retains exact lines, hashes and per-event reasons.
No native executable, account, provider or network is used. Only `extract` writes
the fixed fixture; `compare` preserves all inputs and writes a fresh report.
"""
from __future__ import annotations

import argparse
from collections import Counter
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import types

ROOT = Path(__file__).resolve().parents[2]
BASE = 'efbcfffb3c553110c6f4783452ba9bb84489ad6a'
GUARD = 'src/data_sheets_schema/native_subscription_guard_v2.py'
FIXTURE = ROOT / 'tests/fixtures/native_u4b_real_events.json'
SCRATCH = ROOT.parent / 'scratch-native-u4b'
MAX_TRANSCRIPT_BYTES = 64 * 1024 * 1024
MAX_TOTAL_BYTES = 512 * 1024 * 1024
MAX_FIXTURE_BYTES = 2 * 1024 * 1024


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def encoded(value):
    return (json.dumps(value, sort_keys=True, ensure_ascii=False, indent=2, allow_nan=False) + '\n').encode()


def git(*arguments):
    env = {'PATH': '/usr/bin:/bin', 'GIT_NO_LAZY_FETCH': '1', 'GIT_TERMINAL_PROMPT': '0',
           'GIT_CONFIG_GLOBAL': '/dev/null', 'GIT_CONFIG_SYSTEM': '/dev/null',
           'GIT_CONFIG_NOSYSTEM': '1', 'GIT_OPTIONAL_LOCKS': '0'}
    return subprocess.run(['/usr/bin/git', '--no-replace-objects', '-c', 'protocol.allow=never',
                           '-c', 'core.fsmonitor=false', '-C', str(ROOT), *arguments], check=True,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env, timeout=30).stdout


def collect():
    inventory = git('ls-tree', '-r', '-l', '-z', BASE, '--', 'notes').split(b'\0')
    selected = []
    for row in inventory:
        if not row:
            continue
        metadata, path_raw = row.split(b'\t', 1)
        path = path_raw.decode()
        if not path.endswith('/transcript.jsonl') or '.local_worktrees' in Path(path).parts:
            continue
        mode, kind, blob, size = metadata.split()
        if mode != b'100644' or kind != b'blob' or int(size) > MAX_TRANSCRIPT_BYTES:
            raise ValueError('transcript is not a bounded regular committed file: ' + path)
        selected.append((path, blob.decode(), int(size)))
    if not 0 < len(selected) <= 256 or sum(size for _, _, size in selected) > MAX_TOTAL_BYTES:
        raise ValueError('committed transcript inventory exceeds extraction bounds')
    sources, events = [], []
    for path, blob, size in sorted(selected):
        raw = git('cat-file', 'blob', blob)
        if len(raw) != size or hashlib.sha1(b'blob ' + str(size).encode() + b'\0' + raw).hexdigest() != blob:
            raise ValueError('transcript differs from its committed blob: ' + path)
        captured = []
        for number, line in enumerate(raw.splitlines(keepends=True), 1):
            if b'rate_limit_event' not in line:
                continue
            event = json.loads(line)
            if type(event) is not dict or event.get('type') != 'rate_limit_event':
                continue
            if not line.endswith(b'\n') or len(line) > 65536:
                raise ValueError('real event is not a complete bounded physical line')
            captured.append({'source_path': path, 'line': number, 'bytes': len(line),
                             'sha256': sha(line), 'raw_json': line.decode()})
        if captured:
            sources.append({'path': path, 'blob_oid': blob, 'bytes': size,
                            'sha256': sha(raw), 'events': len(captured)})
            events.extend(captured)
    if len(sources) != 64 or len(events) != 209:
        raise ValueError(f'review corpus differs: {len(sources)} transcripts, {len(events)} events')
    result = {'kind': 'native_u4b_a4_real_events', 'version': 1, 'source_commit': BASE,
        'scope': 'Every rate_limit_event in committed notes/**/transcript.jsonl; .local_worktrees excluded',
        'scanned_transcripts': len(selected), 'sources': sources, 'events': events}
    if len(encoded(result)) > MAX_FIXTURE_BYTES:
        raise ValueError('event fixture exceeds its byte bound')
    return result


def fixture():
    with FIXTURE.open('rb') as stream:
        raw = stream.read(MAX_FIXTURE_BYTES + 1)
    if len(raw) > MAX_FIXTURE_BYTES:
        raise ValueError('real event fixture exceeds its bound')
    result = json.loads(raw)
    if result.get('source_commit') != BASE or len(result['sources']) != 64 or len(result['events']) != 209:
        raise ValueError('real event fixture has wrong source or inventory')
    sources = {row['path']: row for row in result['sources']}
    if len(sources) != 64:
        raise ValueError('real event source identities are duplicated')
    identities, counts = set(), Counter()
    for row in result['events']:
        event_raw = row['raw_json'].encode()
        identity = row['source_path'], row['line']
        if (identity in identities or row['source_path'] not in sources
                or type(row['line']) is not int or row['line'] <= 0
                or len(event_raw) != row['bytes'] or sha(event_raw) != row['sha256']
                or not event_raw.endswith(b'\n') or len(event_raw) > 65536
                or json.loads(event_raw).get('type') != 'rate_limit_event'):
            raise ValueError('real event fixture line identity differs')
        identities.add(identity)
        counts[row['source_path']] += 1
    if any(counts[path] != row['events'] for path, row in sources.items()):
        raise ValueError('real event source count differs')
    return result


def stamp(epoch):
    return datetime.fromtimestamp(epoch, timezone.utc).isoformat().replace('+00:00', 'Z')


def event_case(case, event_raw):
    """Synthetic authority/clock, byte-exact real quota observation.

    Capture/dispatch time is invented immediately before the earliest emitted
    reset; this exercises parser and guard behavior, not historical freshness.
    No source event, utilization, status, reset, UUID or session is rewritten.
    """
    value = deepcopy(case)
    event = json.loads(event_raw)
    now = min(row['resetsAt'] for row in event['rate_limit_info']['unifiedWindows'].values()) - 60
    word = json.loads(value['word'])
    word['authorized_at'] = stamp(now - 10)
    value['word'] = encoded(word)
    value['now'] = now
    value['document'].update(launch_word_sha256=sha(value['word']), captured_at=stamp(now),
                             event_json=event_raw.decode(), event_sha256=sha(event_raw))
    return value


def make_guard(module, case, *, seed=False):
    document = deepcopy(case['document'])
    if seed:
        # A safe synthetic admission lets every historical event reach observe,
        # including events above today's starting maxima. The historical event
        # itself remains unchanged and is never used to assert account state.
        event = {'type': 'rate_limit_event', 'rate_limit_info': {'status': 'allowed',
            'isUsingOverage': False, 'unifiedWindows': {
                'five_hour': {'utilization': 0.2, 'resetsAt': case['now'] + 3600},
                'seven_day': {'utilization': 0.3, 'resetsAt': case['now'] + 86400}}}}
        raw = module.canonical(event)
        document.update(event_json=raw.decode(), event_sha256=module.sha(raw))
    raw = module.canonical(document)
    return module.SubscriptionGuard(raw, expected_sha256=module.sha(raw),
        registration_raw=case['registration'], runtime=case['runtime'],
        launch_word_raw=case['word'], owner_statement=case['owner'], clock=lambda: case['now'])


def outcome(call):
    try:
        call()
        return {'status': 'admitted', 'reason': None}
    except ValueError as exc:
        return {'status': 'refused', 'reason': str(exc)}


def compare(case_directory):
    saved = fixture()
    if saved != collect():
        raise ValueError('fixture differs from the fixed original committed transcript bytes')
    sys.path[:0] = [str(ROOT / 'src'), str(ROOT)]
    from data_sheets_schema import native_subscription_guard_v2 as after
    from tests.test_native_subscription_guard_v2 import case as guard_case
    if Path(after.__file__).resolve() != ROOT / GUARD:
        raise ValueError('candidate guard was imported from another source tree')
    if (ROOT / GUARD).read_bytes() != git('show', 'HEAD:' + GUARD):
        raise ValueError('candidate guard must be committed before the comparison')
    before_raw = git('show', BASE + ':' + GUARD)
    before = types.ModuleType('data_sheets_schema._a4_baseline_guard')
    before.__file__ = BASE + ':' + GUARD
    # A pure parser component comparison only; no source-loader authority is
    # claimed. Both versions use the same current owner/runtime term validators.
    exec(compile(before_raw, before.__file__, 'exec'), before.__dict__)
    case = guard_case.__wrapped__(case_directory)
    rows, totals = [], {}
    for index, row in enumerate(saved['events'], 1):
        raw = row['raw_json'].encode()
        event = after.strict_json(raw)
        context = event_case(case, raw)
        result = {'index': index, 'source_path': row['source_path'], 'line': row['line'],
                  'event_sha256': row['sha256']}
        for label, module in (('before', before), ('after', after)):
            def observe():
                value = make_guard(module, context, seed=True)
                value.before_dispatch()
                value.observe(event)
            result[label] = {
                'admission_shape': outcome(lambda: module.window_readings(event, require_both=True)),
                'observe_shape': outcome(lambda: module.window_readings(event, require_both=False)),
                'admission': outcome(lambda: make_guard(module, context)),
                'observe': outcome(observe)}
        rows.append(result)
    for label in ('before', 'after'):
        totals[label] = {route: dict(Counter(row[label][route]['status'] for row in rows))
                        for route in ('admission_shape', 'observe_shape', 'admission', 'observe')}
    return {'kind': 'native_u4b_a4_real_event_comparison', 'version': 1,
        'baseline_commit': BASE, 'candidate_commit': git('rev-parse', 'HEAD').decode().strip(),
        'guard_before_sha256': sha(before_raw), 'guard_after_sha256': sha((ROOT / GUARD).read_bytes()),
        'fixture_sha256': sha(FIXTURE.read_bytes()), 'transcripts': 64, 'events': 209,
        'scope': 'Real event bytes, invented component authority and clock; parser compatibility and current thresholds only, not native/account acceptance',
        'totals': totals, 'events_by_status': dict(Counter(json.loads(row['raw_json'])['rate_limit_info']['status']
                                                       for row in saved['events'])),
        'rows': rows}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=('extract', 'compare'))
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    if args.mode == 'extract':
        if args.output is not None:
            raise ValueError('extract writes only the fixed committed fixture path')
        result, output = collect(), FIXTURE
        output.parent.mkdir(parents=True, exist_ok=True)
    else:
        output = args.output
        if (output is None or not output.is_absolute() or output.parent != SCRATCH
                or output.resolve() != output or os.path.lexists(output)
                or output.suffix != '.json'):
            raise ValueError('compare requires a new physical JSON report in assigned U4b scratch')
        case_directory = SCRATCH / (output.stem + '-case')
        case_directory.mkdir(mode=0o700)
        result = compare(case_directory)
    with output.open('xb') as stream:
        stream.write(encoded(result))
    print(json.dumps({'path': str(output), 'sha256': sha(output.read_bytes()),
                      'bytes': output.stat().st_size, 'totals': result.get('totals')}))


if __name__ == '__main__':
    main()
