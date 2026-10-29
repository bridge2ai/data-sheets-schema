"""F1, PR #5162 x #5211: current runtime parity, never an optional saved wire."""
import json

from scripts.adhoc.wave6_a14_a17_sizing_20261029 import measure


def test_current_runtime_sizing_matches_every_typed_call(tmp_path, monkeypatch):
    import socket
    def deny(*args, **kwargs):
        raise AssertionError('network forbidden in sizing parity')
    monkeypatch.setattr(socket.socket, 'connect', deny)
    result = measure(tmp_path / 'fixture')
    (tmp_path / 'parity.json').write_text(json.dumps(result, indent=2) + '\n')
    assert result['plan_workers'] == 3
    assert len(result['rows']) == 5
    assert {row['stage']['phase'] for row in result['rows']} == {
        'typed_audit_worker', 'typed_audit_omission', 'typed_audit_integration'}
    for row in result['rows']:
        assert row['carry_allowance_bytes'] >= 0
        assert row['schema_allowance_bytes'] >= 0
        assert row['response_bytes'] >= 0
        assert row['sized_text_bytes'] == row['expected_sized_text_bytes'], row
        assert row['inner_matches'], row
    assert result['passed']
