"""Inspect CLI model-identity context against a local rejecting endpoint.

Uses a synthetic prompt/key and the public pinned agent definition. Captures
only request model/system/messages/tool names, never HTTP headers. Every
inference request is rejected locally: no model provider is contacted.
"""
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

ROOT = Path(__file__).resolve().parents[3]
spec = importlib.util.spec_from_file_location("cborg_adapter", ROOT / "scripts/reference_rescore_cborg.py")
adapter = importlib.util.module_from_spec(spec)
spec.loader.exec_module(adapter)
requests = []


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers.get("content-length", "0"))))
        requests.append({"path": self.path, "model": body.get("model"), "system": body.get("system"),
                         "messages": body.get("messages"), "tools": [t.get("name") for t in body.get("tools", [])]})
        if "count_tokens" in self.path:
            status, response = 200, {"input_tokens": 1}
        else:
            status, response = 400, {"type": "error", "error": {"type": "invalid_request_error", "message": "offline identity probe: no inference"}}
        payload = json.dumps(response).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)


server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
thread = threading.Thread(target=server.serve_forever, daemon=True)
thread.start()
results = []
try:
    for model in ("claude-opus-5[1m]", "claude-opus-5"):
        requests.clear()
        with tempfile.TemporaryDirectory(prefix="d4d-offline-identity-") as temp:
            cwd = Path(temp)
            env = adapter.cborg_environment({**os.environ, "CBORG_API_KEY": "offline-probe-key"})
            env["ANTHROPIC_BASE_URL"] = f"http://127.0.0.1:{server.server_port}"
            env["CLAUDE_CONFIG_DIR"] = str(cwd / "config")
            args = [shutil.which("claude"), "--print", "--safe-mode", "--restricted", "--no-session-persistence",
                    "--model", model, "--effort", "high", "--max-budget-usd", "5", "--output-format", "stream-json",
                    "--verbose", "--permission-mode", "dontAsk", "--tools", "Read,Write,Bash", "--allowedTools",
                    "Read", "Write", "Bash(poetry run python scripts/validate_evaluation_schema.py:*)",
                    "--system-prompt", (ROOT / ".claude/agents/d4d-rubric10-semantic.md").read_text()]
            done = subprocess.run(args, input="Offline model-identity request inspection. No evaluator task or source record.",
                                  text=True, env=env, cwd=cwd, capture_output=True, timeout=45)
            assert requests and done.returncode != 0
            results.append({"selector": model, "exit_code": done.returncode, "local_requests": list(requests),
                            "paid_model_calls": 0})
finally:
    server.shutdown()
    server.server_close()
print(json.dumps({"verification": "Installed CLI request context captured by local rejecting server; synthetic input/key, zero inference.",
                  "cases": results}, indent=2))
