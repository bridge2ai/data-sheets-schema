"""Transport identities, TLS verification and SDK/raw parity without a provider."""
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import socket
import ssl
import sys
import threading

import httpx
import pytest
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from audit_controls import transport as t
from audit_controls.registration import sha
from budgeted_cborg import BudgetStop

DIRECT = 'https://api-local.cborg.lbl.gov'


@pytest.fixture
def certificates(tmp_path):
    now = datetime.now(timezone.utc)
    ca_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, 'Offline synthetic test CA')])
    ca = (x509.CertificateBuilder().subject_name(name).issuer_name(name).public_key(ca_key.public_key())
        .serial_number(x509.random_serial_number()).not_valid_before(now - timedelta(days=1))
        .not_valid_after(now + timedelta(days=1)).add_extension(x509.BasicConstraints(ca=True, path_length=0), True)
        .add_extension(x509.KeyUsage(False, False, False, False, False, True, True, False, False), True)
        .sign(ca_key, hashes.SHA256()))
    server_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    server = (x509.CertificateBuilder().subject_name(x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, 'localhost')]))
        .issuer_name(name).public_key(server_key.public_key()).serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(days=1)).not_valid_after(now + timedelta(days=1))
        .add_extension(x509.SubjectAlternativeName([x509.DNSName('localhost')]), False)
        .add_extension(x509.BasicConstraints(ca=False, path_length=None), True).sign(ca_key, hashes.SHA256()))
    ca_path, cert_path, key_path = (tmp_path / name for name in ('ca.pem', 'server.pem', 'key.pem'))
    ca_path.write_bytes(ca.public_bytes(serialization.Encoding.PEM))
    cert_path.write_bytes(server.public_bytes(serialization.Encoding.PEM))
    key_path.write_bytes(server_key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption()))
    manifest = {'provider_base_url': DIRECT, 'provider_context_policy': 'headroom_bypass_v1',
        'provider_transport': {'kind': 'pinned_ca_v1', 'ca_bundle': str(ca_path)},
        'pinned_files': {str(ca_path): sha(ca_path)}}
    return manifest, ca_path, cert_path, key_path


def test_pinned_chain_and_hostname_are_enforced_by_real_tls(certificates):
    m, _, cert, key = certificates
    context = t.verified_context(m)
    assert context.verify_mode == ssl.CERT_REQUIRED and context.check_hostname is True
    assert not context.verify_flags & ssl.VERIFY_X509_PARTIAL_CHAIN
    assert context.minimum_version >= ssl.TLSVersion.TLSv1_2
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args): pass
    server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    server_tls = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    server_tls.load_cert_chain(str(cert), str(key))
    server.socket = server_tls.wrap_socket(server.socket, server_side=True)
    thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
    try:
        with socket.create_connection(server.server_address, timeout=3) as raw:
            with context.wrap_socket(raw, server_hostname='localhost') as verified:
                assert verified.getpeercert()
        with socket.create_connection(server.server_address, timeout=3) as raw:
            with pytest.raises(ssl.SSLCertVerificationError): context.wrap_socket(raw, server_hostname='wrong.invalid')
        untrusted = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        with socket.create_connection(server.server_address, timeout=3) as raw:
            with pytest.raises(ssl.SSLCertVerificationError): untrusted.wrap_socket(raw, server_hostname='localhost')
    finally:
        server.shutdown(); server.server_close(); thread.join(timeout=3)


def test_counting_and_streaming_share_verified_client_and_context_headers(certificates, monkeypatch):
    m, _, _, _ = certificates
    real_client, observed, calls = httpx.Client, {}, []
    def response(request):
        calls.append(request)
        assert request.url.host == 'api-local.cborg.lbl.gov'
        assert request.headers['x-api-key'] == 'offline-key'
        assert request.headers['x-headroom-bypass'] == 'true'
        return httpx.Response(200, json={'input_tokens': 12})
    def factory(**kwargs):
        observed.update(kwargs)
        return real_client(transport=httpx.MockTransport(response), **kwargs)
    monkeypatch.setattr(t, 'Client', factory)
    sdk, upstream = t.provider_clients(m, 'offline-key')
    try:
        result = sdk.messages.count_tokens(model='offline-model', messages=[{'role':'user','content':'synthetic'}])
        assert result.input_tokens == 12
        upstream.post(DIRECT+'/v1/messages', json={'stream':True},
            headers={'x-api-key':'offline-key','x-headroom-bypass':'true'})
        assert sdk._client is upstream
        assert observed['trust_env'] is False and observed['follow_redirects'] is False
        assert observed['verify'].verify_mode == ssl.CERT_REQUIRED and observed['verify'].check_hostname is True
        assert observed['timeout'].read == 1800 and sdk.max_retries == 0
        assert [call.url.path for call in calls] == ['/v1/messages/count_tokens', '/v1/messages']
    finally: sdk.close()
    assert upstream.is_closed


@pytest.mark.parametrize('endpoint', ['http://api-local.cborg.lbl.gov', 'https://api-local.cborg.lbl.gov/',
    'https://api-local.cborg.lbl.gov.evil.invalid', 'https://user@api-local.cborg.lbl.gov',
    'https://api-local.cborg.lbl.gov:443', 'https://api-local.cborg.lbl.gov/v1'])
def test_endpoint_variants_are_refused_before_client_creation(certificates, monkeypatch, endpoint):
    m, _, _, _ = certificates; m['provider_base_url'] = endpoint
    monkeypatch.setattr(t, 'Client', lambda **kw: pytest.fail('client created before validation'))
    with pytest.raises(BudgetStop): t.provider_clients(m, 'offline-key')


@pytest.mark.parametrize('change', ['changed_ca', 'missing_pin', 'missing_config', 'unknown_kind', 'extra_config', 'alias'])
def test_direct_trust_must_be_explicit_and_unchanged(certificates, monkeypatch, change):
    m, ca, _, _ = certificates
    if change == 'changed_ca': ca.write_bytes(ca.read_bytes()+b'\n')
    elif change == 'missing_pin': m['pinned_files'] = {}
    elif change == 'missing_config': del m['provider_transport']
    elif change == 'unknown_kind': m['provider_transport']['kind'] = 'ambient'
    elif change == 'extra_config': m['provider_transport']['verify'] = False
    elif change == 'alias':
        alias = ca.with_name('alias.pem'); alias.symlink_to(ca); m['provider_transport']['ca_bundle'] = str(alias)
    monkeypatch.setattr(t, 'Client', lambda **kw: pytest.fail('client created with unverified trust'))
    with pytest.raises(BudgetStop): t.provider_clients(m, 'offline-key')


def test_historical_public_registration_has_no_new_trust_requirement(monkeypatch):
    m = {'provider_base_url':'https://api.cborg.lbl.gov'}
    sentinel = object()
    monkeypatch.setattr(t, 'cborg_client', lambda manifest,key,max_retries:sentinel)
    assert t.transport_paths(m) == set()
    assert t.provider_clients(m,'offline-key') == (sentinel,None)


def test_sdk_setup_failure_closes_verified_client(certificates, monkeypatch):
    m, _, _, _ = certificates
    client = httpx.Client(transport=httpx.MockTransport(lambda request:httpx.Response(200)))
    monkeypatch.setattr(t,'Client',lambda **kwargs:client)
    def fail(*args,**kwargs): raise RuntimeError('synthetic SDK setup failure')
    monkeypatch.setattr(t,'cborg_client',fail)
    with pytest.raises(RuntimeError,match='synthetic'):t.provider_clients(m,'offline-key')
    assert client.is_closed
