"""Policy-only token counts with a hard total deadline (#2159).

The synchronous SDK's timeout limits inactivity, not elapsed request time. A
count-only child gives the parent a cancellable boundary even during DNS or a
slowly arriving response. The child never owns ledger or evidence state.
"""
from __future__ import annotations

import json
import math
from pathlib import Path
import ssl
import subprocess
import sys
import threading
import time
from types import SimpleNamespace


class CountClientClosed(RuntimeError):
    """Admission closed; this is deliberately not a retryable provider error."""


class CountWorkerError(RuntimeError):
    """The count-only child did not return the narrow, reviewed protocol."""


def _positive_seconds(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0:
        raise ValueError('count deadline must be finite positive seconds')
    return float(value)


def _kill_and_wait(child):
    # Kill before waiting: no blocked DNS, socket or SDK cleanup may outlive the
    # parent operation. Popen serializes concurrent wait() calls internally.
    if child.poll() is None:
        try:
            child.kill()
        except ProcessLookupError:
            pass
    child.wait()


def _request():
    import httpx
    # Exception reconstruction needs an SDK request object, not the original
    # request or any operator/provider text.
    return httpx.Request('POST', 'https://registered-count.invalid/v1/messages/count_tokens')


def _raise_result_error(value):
    import anthropic
    import httpx
    category = value.get('error')
    if category == 'timeout' and set(value) == {'error'}:
        raise anthropic.APITimeoutError(request=_request())
    if category == 'connection' and set(value) == {'error'}:
        raise anthropic.APIConnectionError(request=_request())
    if category == 'status' and set(value) == {'error', 'status'}:
        status = value['status']
        if type(status) is not int or not 100 <= status <= 599:
            raise CountWorkerError('count worker returned an invalid status')
        response = httpx.Response(status, request=_request())
        kinds = {400: anthropic.BadRequestError, 401: anthropic.AuthenticationError,
                 403: anthropic.PermissionDeniedError, 404: anthropic.NotFoundError,
                 409: anthropic.ConflictError, 422: anthropic.UnprocessableEntityError,
                 429: anthropic.RateLimitError}
        kind = anthropic.InternalServerError if status >= 500 else kinds.get(status, anthropic.APIStatusError)
        raise kind('registered token count failed', response=response, body=None)
    if category == 'invalid_count' and set(value) == {'error'}:
        raise CountWorkerError('provider returned no usable input count')
    raise CountWorkerError('count worker failed without a usable result')


class BoundedCountClient:
    """Small SDK-shaped count client; selected only by a registered policy.

    Credentials, transport configuration and request fields cross an anonymous
    stdin pipe only. Child stdout contains one typed count or whitelisted error;
    provider exception text and stderr are never returned or archived.
    """
    def __init__(self, *, api_key, base_url, ca_bundle=None, default_headers=None, timeout_seconds=120):
        self.timeout_seconds = _positive_seconds(timeout_seconds)
        if not isinstance(api_key, str) or not api_key or not isinstance(base_url, str) or not base_url:
            raise ValueError('count transport needs its registered key and endpoint')
        if ca_bundle is not None and not isinstance(ca_bundle, (str, Path)):
            raise ValueError('count certificate bundle must be a path')
        if default_headers is not None and (not isinstance(default_headers, dict) or
                any(not isinstance(k, str) or not isinstance(v, str) for k, v in default_headers.items())):
            raise ValueError('count transport headers must be strings')
        self._config = {'api_key': api_key, 'base_url': base_url,
                        'ca_bundle': str(ca_bundle) if ca_bundle is not None else None,
                        'default_headers': dict(default_headers or {})}
        self.messages = self
        self._lock = threading.Lock()
        self._active = set()
        self._closed = False

    @property
    def default_headers(self):
        """Expose the worker's context policy to the proxy's SDK check (#2162)."""
        return dict(self._config['default_headers'])

    def count_tokens(self, *, timeout=None, **fields):
        bound = self.timeout_seconds if timeout is None else min(self.timeout_seconds, _positive_seconds(timeout))
        deadline = time.monotonic() + bound
        payload = json.dumps({'config': self._config, 'fields': fields, 'timeout': bound},
                             allow_nan=False, ensure_ascii=False).encode('utf-8')
        with self._lock:
            if self._closed:
                raise CountClientClosed('native count admission is closed')
            child = subprocess.Popen([sys.executable, '-B', str(Path(__file__).resolve()), '--count-worker'],
                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                # No inherited provider, proxy, Python-path or startup variables.
                env={'PYTHONIOENCODING': 'utf-8', 'PYTHONDONTWRITEBYTECODE': '1'},
                close_fds=True)
            self._active.add(child)
        try:
            try:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise subprocess.TimeoutExpired(child.args, bound)
                output, _ = child.communicate(input=payload, timeout=remaining)
            except subprocess.TimeoutExpired:
                _kill_and_wait(child)
                with self._lock:
                    if self._closed:
                        raise CountClientClosed('native count admission is closed')
                import anthropic
                raise anthropic.APITimeoutError(request=_request()) from None
            with self._lock:
                if self._closed:
                    raise CountClientClosed('native count admission is closed')
            # Include process startup, input/output transfer and response parsing
            # in the same count budget, not just the socket operation.
            if time.monotonic() >= deadline:
                import anthropic
                raise anthropic.APITimeoutError(request=_request())
            if child.returncode != 0 or len(output) > 1024:
                raise CountWorkerError('count worker exited without a usable result')
            try:
                value = json.loads(output)
            except (ValueError, UnicodeError):
                raise CountWorkerError('count worker returned an invalid result') from None
            if not isinstance(value, dict):
                raise CountWorkerError('count worker returned an invalid result')
            if time.monotonic() >= deadline:
                import anthropic
                raise anthropic.APITimeoutError(request=_request())
            if set(value) == {'input_tokens'} and type(value['input_tokens']) is int and value['input_tokens'] >= 0:
                return SimpleNamespace(input_tokens=value['input_tokens'])
            _raise_result_error(value)
        finally:
            _kill_and_wait(child)
            for pipe in (child.stdin, child.stdout):
                if pipe is not None:
                    pipe.close()
            with self._lock:
                self._active.discard(child)

    def close(self):
        with self._lock:
            self._closed = True
            active = tuple(self._active)
        for child in active:
            _kill_and_wait(child)


def _count_once(payload):
    """Child-only: exactly one SDK count, strict trust, and no automatic retry."""
    import anthropic
    import httpx
    config = payload['config']
    if config['ca_bundle'] is None:
        # HTTPX's explicit default trust; trust_env=False excludes environment
        # certificate/proxy additions. Pinned direct transport uses only its CA.
        context = True
    else:
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        context.verify_flags &= ~ssl.VERIFY_X509_PARTIAL_CHAIN
        context.load_verify_locations(cafile=config['ca_bundle'])
    transport = httpx.Client(verify=context, trust_env=False, follow_redirects=False,
                             timeout=payload['timeout'])
    with anthropic.Anthropic(api_key=config['api_key'], base_url=config['base_url'],
            default_headers=config['default_headers'], max_retries=0, http_client=transport) as client:
        count = client.messages.count_tokens(**payload['fields']).input_tokens
    if type(count) is not int or count < 0:
        return {'error': 'invalid_count'}
    return {'input_tokens': count}


def _worker():
    import anthropic
    try:
        payload = json.load(sys.stdin)
        value = _count_once(payload)
    except anthropic.APITimeoutError:
        value = {'error': 'timeout'}
    except anthropic.APIConnectionError:
        value = {'error': 'connection'}
    except anthropic.APIStatusError as exc:
        value = {'error': 'status', 'status': exc.status_code}
    except Exception:
        value = {'error': 'worker'}
    sys.stdout.write(json.dumps(value) + '\n')
    sys.stdout.flush()


if __name__ == '__main__':
    if sys.argv[1:] != ['--count-worker']:
        raise SystemExit('count worker requires its private invocation mode')
    _worker()
