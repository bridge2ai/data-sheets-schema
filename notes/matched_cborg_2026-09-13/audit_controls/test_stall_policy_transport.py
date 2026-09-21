"""The registered policy selects bounded I/O without changing legacy clients."""
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from audit_controls import transport
from audit_controls.test_stall_policy import manifest
from audit_controls.test_transport import certificates


@pytest.mark.parametrize('bypass', [False, True])
@pytest.mark.parametrize('mismatch', [False, True])
def test_actual_bounded_clients_satisfy_proxy_context_policy(tmp_path, bypass, mismatch):
    """Exercise the factory-to-proxy boundary that the selection mocks miss (#2162)."""
    from budgeted_cborg import BudgetStop, Ledger, provider_context_headers
    from native_controls.native_proxy import NativeProxy
    from native_controls.test_native_proxy import PRICES

    selected = manifest(provider_base_url='https://api.cborg.lbl.gov',
        native_upstream_read_timeout_seconds=1200,
        **({'provider_context_policy': 'headroom_bypass_v1'} if bypass else {}))
    sdk, upstream = transport.provider_clients(selected, 'synthetic-key')
    headers = provider_context_headers(selected)
    if mismatch:
        headers = {} if bypass else {'x-headroom-bypass': 'true'}
    ledger = Ledger(tmp_path / 'ledger.json', manifest_sha256='offline', attempt_cap=40)
    try:
        def build():
            return NativeProxy(sdk=sdk, upstream=upstream, ledger=ledger, attempt='offline',
                evidence=tmp_path / 'requests', model='synthetic-model', prices=PRICES,
                verify=lambda: None, provider_key='synthetic-key', base_url=selected['provider_base_url'],
                request_headers=headers, upstream_read_timeout_seconds=1200,
                stall_policy={'count_attempts': 3, 'max_stall_debits': 6})
        if mismatch:
            with pytest.raises(BudgetStop, match='context policies differ'):
                build()
        else:
            proxy = build()
            assert proxy.request_headers == sdk.default_headers == headers
            assert proxy.server is None and proxy.thread is None
    finally:
        sdk.close()
        upstream.close()


def test_policy_selects_both_bounded_clients_with_verified_configuration(certificates, monkeypatch):
    from audit_controls import bounded_stream, bounded_transport
    tls, ca, _, _ = certificates
    selected = manifest(**tls, native_upstream_read_timeout_seconds=1200)
    calls = {}
    metadata = SimpleNamespace(close=lambda: None)

    def ordinary(**kwargs):
        calls['metadata'] = kwargs
        return metadata

    def count(**kwargs):
        calls['count'] = kwargs
        return SimpleNamespace(close=lambda: None)

    def stream(delegate, **kwargs):
        calls['stream'] = (delegate, kwargs)
        return object()

    monkeypatch.setattr(transport, 'Client', ordinary)
    monkeypatch.setattr(bounded_transport, 'BoundedCountClient', count)
    monkeypatch.setattr(bounded_stream, 'BoundedStreamClient', stream)
    monkeypatch.setattr(transport, 'cborg_client', lambda *a, **k: pytest.fail('unbounded counting client selected'))
    sdk, upstream = transport.provider_clients(selected, 'synthetic-key')
    assert sdk is not None and upstream is not None
    assert calls['count'] == {'api_key': 'synthetic-key', 'base_url': tls['provider_base_url'],
        'ca_bundle': str(ca), 'default_headers': {'x-headroom-bypass': 'true'}, 'timeout_seconds': 120}
    assert calls['stream'] == (metadata, {'ca_bundle': str(ca), 'read_timeout_seconds': 1200,
                                        'connect_timeout_seconds': 20})
    assert calls['metadata']['verify'].check_hostname is True
    assert calls['metadata']['trust_env'] is False and calls['metadata']['follow_redirects'] is False


def test_failed_bounded_stream_setup_closes_both_owned_resources(certificates, monkeypatch):
    from audit_controls import bounded_stream, bounded_transport
    tls, _, _, _ = certificates
    closed = []
    monkeypatch.setattr(transport, 'Client', lambda **kwargs: SimpleNamespace(close=lambda: closed.append('metadata')))
    monkeypatch.setattr(bounded_transport, 'BoundedCountClient',
                        lambda **kwargs: SimpleNamespace(close=lambda: closed.append('count')))

    def fail(*args, **kwargs):
        raise RuntimeError('synthetic setup failure')

    monkeypatch.setattr(bounded_stream, 'BoundedStreamClient', fail)
    with pytest.raises(RuntimeError, match='synthetic setup failure'):
        transport.provider_clients(manifest(**tls), 'synthetic-key')
    assert closed == ['count', 'metadata']
