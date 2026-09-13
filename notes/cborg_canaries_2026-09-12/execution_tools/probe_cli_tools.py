"""Inspect the real CLI tool advertisement using a local rejecting HTTP endpoint.

No model service is contacted. Credentials and the prompt are synthetic. The
endpoint records only tool names and request paths, never headers or bodies.
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
        requests.append({"path": self.path, "tools": [t.get("name") for t in body.get("tools", [])]})
        if "count_tokens" in self.path:
            status, response = 200, {"input_tokens": 1}
        else:
            status, response = 400, {"type": "error", "error": {"type": "invalid_request_error", "message": "offline capability probe: no model call"}}
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
    for bare in (True, False):
        requests.clear()
        with tempfile.TemporaryDirectory(prefix="d4d-offline-tools-") as temp:
            cwd = Path(temp)
            env = adapter.cborg_environment({**os.environ, "CBORG_API_KEY": "offline-probe-key"})
            env["ANTHROPIC_BASE_URL"] = f"http://127.0.0.1:{server.server_port}"
            env["CLAUDE_CONFIG_DIR"] = str(cwd / "config")
            args = [shutil.which("claude"), *(["--bare"] if bare else []), "--print", "--safe-mode", "--restricted",
                    "--no-session-persistence", "--model", "claude-opus-5[1m]", "--effort", "high",
                    "--max-budget-usd", "5", "--output-format", "stream-json", "--verbose", "--permission-mode", "dontAsk",
                    "--tools", "Read,Write,Bash", "--allowedTools", "Read", "Write",
                    "Bash(poetry run python scripts/validate_evaluation_schema.py:*)", "--system-prompt", "Offline capability probe."]
            done = subprocess.run(args, input="Offline capability probe; no evaluator task.", text=True,
                                  env=env, cwd=cwd, capture_output=True, timeout=45)
            events = []
            for line in done.stdout.splitlines():
                try:
                    events.append(json.loads(line))
                except ValueError:
                    pass
            init = [e for e in events if e.get("type") == "system" and e.get("subtype") == "init"]
            assert len(init) == 1, "missing offline initialization"
            row = {"bare": bare, "exit_code": done.returncode, "tools": init[0]["tools"],
                   "api_key_source": init[0].get("apiKeySource"), "cli_version": init[0].get("claude_code_version"),
                   "local_requests": list(requests), "paid_model_calls": 0}
            assert requests and done.returncode != 0, "probe must reach and be rejected by the local endpoint"
            assert ("Write" in row["tools"]) is not bare
            assert row["api_key_source"] == "ANTHROPIC_API_KEY"
            results.append(row)
finally:
    server.shutdown()
    server.server_close()
print(json.dumps({"verification": "real CLI init and tool request against local rejecting server; no model inference", "cases": results}, indent=2))
