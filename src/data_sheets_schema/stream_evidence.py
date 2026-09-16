"""Bounded metadata from SDK-delivered stream events, never their payloads.

The pinned Anthropic SDK filters wire pings and emits synthetic events. These
counts and times describe what the caller saw, not network traffic or provider
liveness. Correlation headers are local diagnostic evidence, not final usage.
"""
from __future__ import annotations

from collections import Counter, deque
import re
import threading
import time


RECENT_EVENTS = 16
CORRELATION_HEADERS = ("request-id", "x-request-id", "x-litellm-call-id", "cf-ray")
EVENT_TYPES = frozenset({
    "message_start", "message_delta", "message_stop", "content_block_start",
    "content_block_delta", "content_block_stop", "text", "thinking",
    "signature", "input_json", "citation", "ping", "error",
})
BLOCK_TYPES = frozenset({
    "text", "thinking", "redacted_thinking", "tool_use", "server_tool_use",
    "web_search_tool_result",
})
STOP_REASONS = frozenset({
    "end_turn", "max_tokens", "stop_sequence", "tool_use", "pause_turn",
    "refusal", "model_context_window_exceeded",
})


def _known(value, allowed):
    return value if isinstance(value, str) and value in allowed else "unknown"


def _identifier(value, limit=160):
    # No arbitrary header values, control characters or unbounded provider text.
    return value if isinstance(value, str) and re.fullmatch(r"[A-Za-z0-9_.:/-]{1," + str(limit) + "}", value) else None


class StreamTrace:
    """One attempt's observation, isolated from late abandoned workers."""

    def __init__(self, started: float):
        self._started = started
        self._lock = threading.Lock()
        self._iterable = None
        self._http_status = None
        self._headers = {}
        self._headers_seconds = None
        self._counts = Counter()
        self._blocks = Counter()
        self._recent = deque(maxlen=RECENT_EVENTS)
        self._first = None
        self._last = None
        self._stop_reason = None

    def response(self, response):
        """Read only an allowlist; never hold the trace lock across SDK access."""
        if response is None:
            return
        try:
            status = getattr(response, "status_code", None)
            headers = getattr(response, "headers", {})
            selected = {name: value for name in CORRELATION_HEADERS
                        if (value := _identifier(headers.get(name))) is not None}
        except Exception:  # Diagnostics cannot replace the original failure.
            return
        with self._lock:
            if self._headers_seconds is None:
                self._headers_seconds = round(time.monotonic() - self._started, 3)
                self._http_status = status if type(status) is int else None
                self._headers = selected

    def enter(self, stream, *, iterable: bool):
        with self._lock:
            self._iterable = iterable
        try:
            self.response(getattr(stream, "response", None))
        except Exception:
            pass

    def observe(self, event):
        kind = _known(getattr(event, "type", None), EVENT_TYPES)
        block = (_known(getattr(getattr(event, "content_block", None), "type", None), BLOCK_TYPES)
                 if kind == "content_block_start" else None)
        reason = getattr(getattr(event, "delta", None), "stop_reason", None) if kind == "message_delta" else None
        elapsed = round(time.monotonic() - self._started, 3)
        with self._lock:
            self._counts[kind] += 1
            self._recent.append({"type": kind, "seconds": elapsed})
            if self._first is None:
                self._first = elapsed
            self._last = elapsed
            if block is not None:
                self._blocks[block] += 1
            if reason is not None:
                self._stop_reason = _known(reason, STOP_REASONS)

    def snapshot(self, *, exception=None, provider_error_type=None):
        # All returned collections are copies. A watchdog may return while its
        # worker is still live; later observations must not rewrite this record.
        with self._lock:
            count = sum(self._counts.values()) if self._iterable else None
            return {
                "version": 1,
                "observation": "sdk_events_not_wire_sse",
                "iterable": self._iterable,
                "http_status": self._http_status,
                "correlation_headers": dict(self._headers),
                "headers_seconds": self._headers_seconds,
                "events": count,
                "event_counts": dict(self._counts),
                "content_block_counts": dict(self._blocks),
                "recent_events": [dict(event) for event in self._recent],
                "earlier_events": max(0, (count or 0) - len(self._recent)),
                "first_event_seconds": self._first,
                "last_event_seconds": self._last,
                "message_start_seen": bool(self._counts["message_start"]) if self._iterable else None,
                "message_delta_seen": bool(self._counts["message_delta"]) if self._iterable else None,
                "message_stop_seen": bool(self._counts["message_stop"]) if self._iterable else None,
                "stop_reason": self._stop_reason,
                "exception_type": _identifier(type(exception).__name__) if exception is not None else None,
                "provider_error_type": _identifier(provider_error_type, limit=64),
            }
