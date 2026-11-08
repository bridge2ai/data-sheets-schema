"""Bounded loopback-only scripted Messages transport for #4760.

This is a permission experiment, never a model, generation result or token
measurement. It emits only the fixed case selected by the probe controller.
"""
from __future__ import annotations

from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import math
import socket
import threading
import time
from urllib.parse import urlsplit
from .native_subscription_guard import strict_json

MAX_REQUEST = 8 * 1024 * 1024


def _read_request(handler, size):
    """One raw read per iteration, bounded by the same absolute deadline.

    BufferedReader.read(size) can keep resetting its socket timeout while a
    peer trickles bytes. read1 permits a deadline check after each raw read.
    """
    raw = bytearray()
    while len(raw) < size:
        remaining = handler.server.deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError('permission probe deadline elapsed during request')
        handler.connection.settimeout(min(1.0, remaining))
        part = handler.rfile.read1(min(65536, size - len(raw)))
        if not part:
            raise ValueError('truncated scripted request')
        raw.extend(part)
    if time.monotonic() >= handler.server.deadline:
        raise TimeoutError('permission probe deadline elapsed during request')
    return bytes(raw)


def response_payload(body, cases, model, *, reply=None):
    if type(body) is not dict or body.get("model") != model:
        raise ValueError("scripted probe request model differs")
    messages = body.get("messages")
    if type(messages) is not list:
        raise ValueError("scripted probe request has no messages")
    result_ids = []
    for message in messages:
        if type(message) is not dict:
            raise ValueError("scripted probe message is malformed")
        content = message.get("content", [])
        if isinstance(content, str):
            continue
        if type(content) is not list:
            raise ValueError("scripted probe content is malformed")
        result_ids.extend(block.get("tool_use_id") for block in content
                          if type(block) is dict and block.get("type") == "tool_result")
    if result_ids != [case["id"] for case in cases[:len(result_ids)]]:
        raise ValueError("scripted probe results are missing, duplicated or out of order")
    if len(result_ids) > len(cases):
        raise ValueError("scripted probe has extra results")
    complete = len(result_ids) == len(cases)
    block = reply(cases, len(result_ids)) if reply is not None else (
             {"type": "text", "text": "OFFLINE_COMPLETE"} if complete else
             {"type": "tool_use", "id": cases[len(result_ids)]["id"],
              "name": cases[len(result_ids)]["tool"], "input": cases[len(result_ids)]["input"]})
    return {
        "id": "d4d_permission_" + str(len(result_ids)), "type": "message",
        "role": "assistant", "model": model, "content": [block],
        "stop_reason": "end_turn" if complete else "tool_use", "stop_sequence": None,
        "usage": {"input_tokens": 0, "output_tokens": 0},
    }


def encode_response(payload, streaming):
    if not streaming:
        return "application/json", json.dumps(payload).encode()
    block = payload["content"][0]
    start = {**payload, "content": [], "stop_reason": None}
    initial = ({"type": "text", "text": ""} if block["type"] == "text" else
               {**block, "input": {}})
    delta = ({"type": "text_delta", "text": block["text"]} if block["type"] == "text" else
             {"type": "input_json_delta", "partial_json": json.dumps(block["input"])})
    events = [
        {"type": "message_start", "message": start},
        {"type": "content_block_start", "index": 0, "content_block": initial},
        {"type": "content_block_delta", "index": 0, "delta": delta},
        {"type": "content_block_stop", "index": 0},
        {"type": "message_delta", "delta": {"stop_reason": payload["stop_reason"], "stop_sequence": None},
         "usage": {"output_tokens": 0}},
        {"type": "message_stop"},
    ]
    return "text/event-stream", "".join(
        "event: " + row["type"] + "\ndata: " + json.dumps(row) + "\n\n"
        for row in events).encode()


class _Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, *args):
        pass

    def do_POST(self):
        try:
            if time.monotonic() >= self.server.deadline:
                raise TimeoutError("permission probe deadline elapsed")
            if self.headers.get("Transfer-Encoding"):
                raise ValueError("chunked probe requests are not admitted")
            size = int(self.headers.get("Content-Length", "0"))
            if not 0 < size <= MAX_REQUEST:
                raise ValueError("scripted request exceeds its byte bound")
            raw = _read_request(self, size)
            path = urlsplit(self.path)
            if (path.path not in ("/v1/messages", "/v1/messages/count_tokens")
                    or path.scheme or path.netloc or path.fragment):
                raise ValueError("unregistered scripted provider endpoint")
            body = strict_json(raw)
            self.server.requests += 1
            if self.server.requests > 256:
                raise ValueError("scripted request count exceeds its bound")
            observer = getattr(self.server, 'observation_request', None)
            if observer is not None:
                observer(raw, endpoint=path.path)
            if path.path.endswith("/count_tokens"):
                # This value is a local protocol stub, never calibration.
                content_type, output = "application/json", b'{"input_tokens":0}'
            else:
                cases = self.server.case_supplier()
                if not cases and observer is None:
                    raise ValueError("native initialization has not selected probe cases")
                payload = response_payload(body, cases, self.server.model, reply=self.server.reply)
                content_type, output = encode_response(payload, body.get("stream") is True)
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(output)))
            self.send_header("Connection", "close")
            self.end_headers()
            self.wfile.write(output)
            self.wfile.flush()
        except BaseException as exc:
            self.server.failure = exc
            self.close_connection = True
            try:
                self.send_error(400, "scripted probe refused request")
            except OSError:
                pass
        finally:
            self.close_connection = True


class _Server(HTTPServer):
    def get_request(self):
        connection, address = super().get_request()
        try:
            remaining = self.deadline - time.monotonic()
            if remaining <= 0 or self.stop_requested.is_set():
                raise TimeoutError('permission provider is stopping')
            connection.settimeout(min(1.0, remaining))
            with self.connection_lock:
                if self.stop_requested.is_set():
                    raise OSError('permission provider stopped before request')
                self.active_connection = connection
            return connection, address
        except BaseException:
            connection.close()
            raise

    def shutdown_request(self, request):
        try:
            super().shutdown_request(request)
        finally:
            with self.connection_lock:
                if self.active_connection is request:
                    self.active_connection = None

    def close_active_request(self):
        with self.connection_lock:
            connection, self.active_connection = self.active_connection, None
        if connection is not None:
            try:
                connection.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            finally:
                connection.close()


def _serve(server):
    try:
        while not server.stop_requested.is_set():
            if time.monotonic() >= server.deadline:
                raise TimeoutError('permission provider deadline elapsed')
            server.handle_request()
    except BaseException as exc:
        if not server.stop_requested.is_set() and server.failure is None:
            server.failure = exc
    finally:
        server.stop_requested.set()
        server.close_active_request()


@contextmanager
def local_provider(*, cases, model, deadline, reply=None, observation_request=None):
    """Listen only on loopback; close and join on every exit, including errors."""
    if (type(deadline) not in (int, float) or not math.isfinite(deadline)
            or deadline <= time.monotonic()):
        raise ValueError('permission provider needs a finite future deadline')
    if observation_request is not None and not callable(observation_request):
        raise ValueError('observation request capture must be explicit and callable')
    server = _Server(("127.0.0.1", 0), _Handler)
    thread, started = None, False
    try:
        server.case_supplier, server.model, server.deadline = cases, model, deadline
        server.reply = reply
        server.observation_request = observation_request
        server.failure, server.requests = None, 0
        server.timeout = 0.05
        server.active_connection = None
        server.connection_lock = threading.Lock()
        server.stop_requested = threading.Event()
        thread = threading.Thread(target=_serve, args=(server,), daemon=True,
                                  name="d4d-permission-loopback")
        thread.start()
        started = True
        yield server, "http://127.0.0.1:" + str(server.server_port)
    finally:
        try:
            if hasattr(server, 'stop_requested'):
                server.stop_requested.set()
                server.close_active_request()
        finally:
            server.server_close()
            if started:
                thread.join(timeout=2)
                if thread.is_alive():
                    raise RuntimeError("scripted permission provider did not close")
