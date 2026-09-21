"""Explicit, pinned TLS transport for CBORG's documented direct endpoint."""
import ssl

from httpx import Client, Timeout

from budgeted_cborg import (BudgetStop, CBORG_ENDPOINTS, LEGACY_UPSTREAM_READ_SECONDS, UPSTREAM_CONNECT_SECONDS,
                            cborg_client)
from .registration import canonical_path, pinned, native_stall_policy, native_upstream_read_timeout


def transport_paths(manifest):
    native_upstream_read_timeout(manifest)
    native_stall_policy(manifest)
    endpoint = manifest.get('provider_base_url')
    if endpoint not in CBORG_ENDPOINTS:
        raise BudgetStop('audit requires a documented CBORG endpoint')
    config = manifest.get('provider_transport')
    if config is None:
        if endpoint != 'https://api.cborg.lbl.gov':
            raise BudgetStop('direct CBORG transport requires registered certificate trust')
        return set()
    if (not isinstance(config, dict) or set(config) != {'kind', 'ca_bundle'} or
            config['kind'] != 'pinned_ca_v1'):
        raise BudgetStop('unknown audit provider transport configuration')
    return {canonical_path(config['ca_bundle'], exists=True)}


def verified_context(manifest):
    paths = transport_paths(manifest)
    if not paths:
        return None
    path = pinned(manifest, str(next(iter(paths))))
    # No environment or OS trust additions: the reviewed bundle is the trust
    # input. PROTOCOL_TLS_CLIENT enforces both chain and hostname verification.
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    context.verify_flags &= ~ssl.VERIFY_X509_PARTIAL_CHAIN
    context.load_verify_locations(cafile=str(path))
    return context


def provider_clients(manifest, api_key):
    """One verified connection policy for SDK counting and raw native streaming."""
    context = verified_context(manifest)
    if context is None:
        return cborg_client(manifest, api_key, max_retries=0), None
    upstream = Client(verify=context, trust_env=False,
        timeout=Timeout(LEGACY_UPSTREAM_READ_SECONDS, connect=UPSTREAM_CONNECT_SECONDS), follow_redirects=False)
    try:
        sdk = cborg_client(manifest, api_key, max_retries=0, http_client=upstream)
    except BaseException:
        upstream.close()
        raise
    return sdk, upstream
