"""Issue 6236: producer records first stops at cleanup boundaries, offline."""
from pathlib import Path
from types import SimpleNamespace
import threading
import time

import pytest

from data_sheets_schema import native_permission_probe as probe
from data_sheets_schema import native_probe_provider as provider


def test_cleanup_stop_records_failure_and_never_starts_later_trace(tmp_path, monkeypatch, boundary):
    source = tmp_path / 'source'
    source.write_bytes(b'inert input')
    sources = []
    for name in ('native_permission_probe', 'native_probe_provider', 'native_subscription_guard'):
        path = Path(probe.__file__).with_name(name + '.py')
        raw = path.read_bytes()
        sources.append({'module': 'data_sheets_schema.' + name, 'path': str(path.resolve()),
                        'bytes': len(raw), 'sha256': probe.sha(raw)})
    expected = {'production_sources': sources,
        'source': {'path': str(source), 'sha256': probe.sha(source.read_bytes())},
        'runtime': {'executable': {'path': str(tmp_path / 'binary')}},
        'selection': {'path': str(tmp_path / 'selection')}, 'permission_environment': {},
        'policy': {'readonly_lookups': {'repository': str(tmp_path / 'repository'),
                                      'inputs': [], 'output_directories': []}}}
    consumer = SimpleNamespace(MAX_MEMBER=probe.MAX_STREAM, TRACES=('settled', 'later'),
        recipe_sources=lambda: {'recipe/provider.py': '# inert'})
    directory = tmp_path / 'evidence'
    calls = []
    def stop():
        probe.signal.raise_signal(probe.signal.SIGTERM)
    def version(*args):
        if boundary == 'version':
            with probe._cleanup_signals():
                stop()
                (directory / 'version.stdout').write_bytes(b'retained')
        return b'version'
    def trace(*args):
        calls.append(args[-1])
        if boundary == 'trace':
            with probe._cleanup_signals():
                stop()
                (directory / 'trace-cleanup.json').write_bytes(b'{}')
        else:
            server = object.__new__(provider._Server)
            server.connection_lock = threading.Lock()
            server.active_connection = SimpleNamespace(shutdown=lambda _: stop(), close=lambda: None)
            server.close_active_request()
        pytest.fail('stop was swallowed')
    monkeypatch.setattr(probe, '_identity', lambda *a: None)
    monkeypatch.setattr(probe, '_version', version)
    monkeypatch.setattr(probe, '_trace', trace)
    with pytest.raises(probe.ProbeStopped, match='signal 15'):
        with probe._probe_signals():
            probe._produce_captured(expected, directory, time.monotonic() + 60,
                consumer, {}, {}, object(), {'stage_root': str(tmp_path / 'stage')}, b'{}')
    assert calls == ([] if boundary == 'version' else ['settled'])
    failure = probe.strict_json((directory / 'failure.json').read_bytes())
    assert failure == {'error_type': 'ProbeStopped', 'message': 'permission probe stopped by signal 15'}
    assert not (directory / 'permission-probe.json').exists()
    if boundary == 'version':
        assert (directory / 'version.stdout').read_bytes() == b'retained'
    elif boundary == 'trace':
        assert (directory / 'trace-cleanup.json').read_bytes() == b'{}'


test_cleanup_stop_records_failure_and_never_starts_later_trace = pytest.mark.parametrize(
    'boundary', ['version', 'trace', 'provider'])(
        test_cleanup_stop_records_failure_and_never_starts_later_trace)
