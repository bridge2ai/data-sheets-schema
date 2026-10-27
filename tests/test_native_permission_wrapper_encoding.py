"""Exact wrapper-encoding equivalence; fabricated records, no live transport.

The reference preserves the former eager prefix through its metadata gate.
Real member checks run in both paths; a sentinel stops before expensive replay.
One integration case separately retains complete seven-trace verification.
"""
from copy import deepcopy
import json

import pytest

from data_sheets_schema import native_shared_permissions as p
from tests.test_native_shared_permissions import (
    fixture, prohibit_real_transports, put_rows, rows,
)


def encoded(value, ascii_only):
    return json.dumps(value, sort_keys=True, separators=(',', ':'),
                      ensure_ascii=ascii_only, allow_nan=False).encode('utf-8')


def eager_prefix(raw_manifest, expected):
    """The previous prefix, including validation and first-failure ordering."""
    value = p._object(p._json(raw_manifest, p.MAX_WIRE),
        {'kind', 'version', 'origin', 'binding', 'members'}, 'manifest')
    p._need(value['kind'] == p.KIND and type(value['version']) is int
            and value['version'] == p.VERSION and value['origin'] == p.ORIGIN,
            'unknown native shared observation protocol/origin')
    p._need(p._same(value['binding'], expected),
            'manifest binding differs from supplied authority')
    forms = [encoded(value, ascii_only) for ascii_only in (False, True)]
    p._need(raw_manifest in forms, 'manifest wrapper must use canonical JSON encoding')
    ascii_only = raw_manifest == forms[1]
    p._members(value['members'])
    content_wire = sum(len(json.dumps(row['text'], ensure_ascii=ascii_only).encode()) - 2
                       for row in value['members'].values())
    p._need(len(raw_manifest) - content_wire <= p.MAX_METADATA, 'metadata wire exceeds bound')
    p._dependencies()


class ReachedReplay(Exception):
    pass


def stop_before_replay():
    raise ReachedReplay()


def outcome(function, raw, expected):
    try:
        function(raw, expected)
    except ReachedReplay:
        return ('replay',)
    except Exception as error:
        cause = error.__cause__
        return ('error', type(error), str(error),
                None if cause is None else (type(cause), str(cause)))
    pytest.fail('prefix unexpectedly returned without reaching the replay seam')


def unicode_manifest(fixture):
    value = deepcopy(fixture['manifest'])
    name = 'traces/settled/control.jsonl'
    records = rows(value, name)
    records[0]['at'] = 'fabricated café 🧬'
    put_rows(value, name, records)
    return value


@pytest.mark.parametrize('text', ['ASCII only', 'café 🧬'])
@pytest.mark.parametrize('ascii_only', [False, True])
def test_only_the_needed_wrapper_serialization_runs(text, ascii_only, monkeypatch):
    # The deliberately absent roster refuses AFTER the wrapper gate.
    # This isolates its calls without pretending this is permission evidence.
    value = {'kind': p.KIND, 'version': p.VERSION, 'origin': p.ORIGIN,
             'binding': {'text': text}, 'members': {}}
    raw = encoded(value, ascii_only)
    baseline = outcome(eager_prefix, raw, value['binding'])
    assert baseline[0:2] == ('error', ValueError)
    assert 'raw member roster' in baseline[2]
    p._json(raw, p.MAX_WIRE)  # Warm only the existing pure JSON parser guard.
    actual_dumps = json.dumps
    calls = []

    def dumps(current, *args, **kwargs):
        if type(current) is dict and current.get('kind') == p.KIND:
            calls.append(kwargs.get('ensure_ascii', True))
        return actual_dumps(current, *args, **kwargs)

    with monkeypatch.context() as patch:
        patch.setattr(json, 'dumps', dumps)
        assert outcome(p._verify, raw, value['binding']) == baseline
    assert calls == ([False, True] if ascii_only and not text.isascii() else [False])


@pytest.mark.parametrize('ascii_only', [False, True])
def test_exact_metadata_boundary_matches_eager_prefix(fixture, monkeypatch, ascii_only):
    value = unicode_manifest(fixture)
    raw = encoded(value, ascii_only)
    forms = [encoded(value, mode) for mode in (False, True)]
    old_mode = raw == forms[1]
    content_wire = sum(len(json.dumps(row['text'], ensure_ascii=old_mode).encode()) - 2
                       for row in value['members'].values())
    metadata = len(raw) - content_wire
    monkeypatch.setattr(p, '_dependencies', stop_before_replay)
    for limit in (metadata - 1, metadata, metadata + 1):
        monkeypatch.setattr(p, 'MAX_METADATA', limit)
        previous = outcome(eager_prefix, raw, fixture['expected'])
        assert outcome(p._verify, raw, fixture['expected']) == previous
        if limit < metadata:
            assert previous[0:2] == ('error', ValueError)
            assert previous[2] == 'native shared permission: metadata wire exceeds bound'
        else:
            assert previous == ('replay',)


@pytest.mark.parametrize('change', ['whitespace', 'binding', 'member_hash', 'surrogate'])
def test_first_failure_matches_previous_prefix(fixture, monkeypatch, change):
    value = unicode_manifest(fixture)
    if change == 'binding':
        value['binding']['system_sha256'] = '0' * 64
    elif change == 'member_hash':
        value['members']['source.before']['sha256'] = '0' * 64
    elif change == 'surrogate':
        # Also corrupt the hash: malformed Unicode must win before members.
        value['members']['source.before']['text'] = '\ud800'
        value['members']['source.before']['sha256'] = 'not a hash'
    raw = (json.dumps(value, indent=2, ensure_ascii=True).encode()
           if change == 'whitespace' else encoded(value, True))
    monkeypatch.setattr(p, '_dependencies', stop_before_replay)
    previous = outcome(eager_prefix, raw, fixture['expected'])
    assert previous[0:2] == ('error', ValueError)
    assert outcome(p._verify, raw, fixture['expected']) == previous
    if change == 'surrogate':
        assert 'canonical UTF-8 JSON' in previous[2]


def test_both_unicode_wrappers_keep_complete_replay_and_member_identity(fixture):
    value = unicode_manifest(fixture)
    results = []
    for ascii_only in (False, True):
        raw = encoded(value, ascii_only)
        result = p.verify_saved_probe(raw, expected=fixture['expected'])
        assert result['checked'] is result['passed'] is True
        assert len(result['traces']) == 7 and len(result['cases']) == 25
        assert result.pop('manifest') == {'sha256': p._sha(raw), 'bytes': len(raw)}
        results.append(result)
    assert results[0] == results[1]
