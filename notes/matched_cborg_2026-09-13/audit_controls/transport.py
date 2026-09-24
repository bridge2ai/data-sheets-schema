"""Explicit, pinned TLS transport for CBORG's documented direct endpoint."""
import ssl

from httpx import Client, Timeout

from budgeted_cborg import (BudgetStop, CBORG_ENDPOINTS, LEGACY_UPSTREAM_READ_SECONDS,
                            POLICY_COUNT_TRY_SECONDS, UPSTREAM_CONNECT_SECONDS,
                            cborg_client, provider_context_headers)
from .registration import (canonical_path, pinned, native_stall_policy,
                           native_upstream_read_timeout, native_response_buffer, native_history_control)


def transport_paths(manifest):
    if 'audit_drafting' in manifest:
        from .draft_output import configuration
        configuration(manifest)
    if 'audit_contract_context' in manifest:
        from .contract_context import enabled
        enabled(manifest)
    native_upstream_read_timeout(manifest)
    native_stall_policy(manifest)
    native_response_buffer(manifest)
    native_history_control(manifest)
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
    if native_stall_policy(manifest) is not None:
        # Only the opt-in audit policy uses killable I/O workers. A per-read
        # HTTPX timeout cannot bound counting or receipt of response headers
        # when the provider continues sending partial data (#2159).
        from .bounded_transport import BoundedCountClient
        from .bounded_stream import BoundedStreamClient
        ca = manifest.get('provider_transport', {}).get('ca_bundle')
        metadata = Client(verify=context if context is not None else True, trust_env=False,
            timeout=Timeout(LEGACY_UPSTREAM_READ_SECONDS, connect=UPSTREAM_CONNECT_SECONDS),
            follow_redirects=False)
        sdk = None
        try:
            sdk = BoundedCountClient(api_key=api_key, base_url=manifest['provider_base_url'],
                ca_bundle=ca, default_headers=provider_context_headers(manifest),
                timeout_seconds=POLICY_COUNT_TRY_SECONDS)
            buffer = native_response_buffer(manifest)
            upstream = BoundedStreamClient(metadata, ca_bundle=ca,
                read_timeout_seconds=native_upstream_read_timeout(manifest) or LEGACY_UPSTREAM_READ_SECONDS,
                connect_timeout_seconds=UPSTREAM_CONNECT_SECONDS,
                **({'total_timeout_seconds': buffer['total_seconds']} if buffer is not None else {}))
        except BaseException:
            if sdk is not None:
                sdk.close()
            metadata.close()
            raise
        return sdk, upstream
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
