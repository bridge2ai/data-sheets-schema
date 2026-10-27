"""Bounded loopback-only scripted Messages transport for #4760.

This is a permission experiment, never a model, generation result or token
measurement. It emits only the fixed case selected by the probe controller.
"""
from __future__ import annotations

from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import threading
import time
from urllib.parse import urlsplit
from .native_subscription_guard import strict_json

MAX_REQUEST = 8 * 1024 * 1024


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
            raw = self.rfile.read(size)
            if len(raw) != size:
                raise ValueError("truncated scripted request")
            path = urlsplit(self.path)
            if (path.path not in ("/v1/messages", "/v1/messages/count_tokens")
                    or path.scheme or path.netloc or path.fragment):
                raise ValueError("unregistered scripted provider endpoint")
            body = strict_json(raw)
            self.server.requests += 1
            if self.server.requests > 256:
                raise ValueError("scripted request count exceeds its bound")
            if path.path.endswith("/count_tokens"):
                # This value is a local protocol stub, never calibration.
                content_type, output = "application/json", b'{"input_tokens":0}'
            else:
                cases = self.server.case_supplier()
                if not cases:
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
        connection.settimeout(max(0.01, min(1.0, self.deadline - time.monotonic())))
        return connection, address


@contextmanager
def local_provider(*, cases, model, deadline, reply=None):
    """Listen only on loopback; close and join on every exit, including errors."""
    server = _Server(("127.0.0.1", 0), _Handler)
    server.case_supplier, server.model, server.deadline = cases, model, deadline
    server.reply = reply
    server.failure, server.requests = None, 0
    thread = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.05},
                              name="d4d-permission-loopback")
    thread.start()
    try:
        yield server, "http://127.0.0.1:" + str(server.server_port)
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
        if thread.is_alive():
            raise RuntimeError("scripted permission provider did not close")
