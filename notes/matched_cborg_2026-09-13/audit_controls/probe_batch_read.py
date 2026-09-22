"""Pinned native Read-format probe against a scripted, offline-only upstream.

Only synthetic canonical row files are used. No generation registration, actual
ledger, source validator, provider key or provider request is used. The emitted
metadata report deliberately excludes native message bodies and source text.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace

import httpx

BASE = Path(__file__).resolve().parent.parent
for directory in (BASE, BASE / "native_controls"):
    if str(directory) not in sys.path:
        sys.path.insert(0, str(directory))

from budgeted_cborg import BudgetStop, Ledger
from native_control import CONTRACT
from native_file_policy import FileAccess
from native_proxy import NativeProxy
from run_native_canary import execute_child, sha, verified_executable
from data_sheets_schema.audit_batches import canonical_bytes, object_sha256
from audit_controls.batch_history import BatchHistory
from audit_controls.native import _blocks


def stream_response(body, block, ordinal):
    start = dict(block)
    start["input" if block["type"] == "tool_use" else "text"] = {} if block["type"] == "tool_use" else ""
    delta = ({"type": "input_json_delta", "partial_json": json.dumps(block["input"])}
             if block["type"] == "tool_use" else {"type": "text_delta", "text": block["text"]})
    events = [
        {"type": "message_start", "message": {"id": f"offline_row_{ordinal}", "type": "message",
            "role": "assistant", "model": body["model"], "content": [], "stop_reason": None,
            "stop_sequence": None, "usage": {"input_tokens": 100, "output_tokens": 0}}},
        {"type": "content_block_start", "index": 0, "content_block": start},
        {"type": "content_block_delta", "index": 0, "delta": delta},
        {"type": "content_block_stop", "index": 0},
        {"type": "message_delta", "delta": {"stop_reason": "tool_use" if block["type"] == "tool_use" else "end_turn",
            "stop_sequence": None}, "usage": {"output_tokens": 12}},
        {"type": "message_stop"}]
    content = "".join(f"event: {event['type']}\ndata: {json.dumps(event)}\n\n" for event in events).encode()
    return httpx.Response(200, content=content, headers={"content-type": "text/event-stream"})


def run(executable, row_text_size=26):
    if type(row_text_size) is not int or not 1 <= row_text_size <= 100_000:
        raise ValueError("synthetic row size must be 1 to 100000 characters")
    cli = Path(executable).resolve(strict=True)
    overlay = {"claude_executable": str(cli), "pinned_files": {str(cli): sha(cli)}}
    root = Path(tempfile.mkdtemp(prefix="d4d-offline-batch-read-")).resolve()
    work = root / "work";work.mkdir()
    config = root / "config";config.mkdir()
    # Both canonical rows have one JSON line and the mandatory final newline.
    row = {"path": "/synthetic", "claims": [{"text": "λ" + "x" * (row_text_size - 1),
           "verdict": "supported", "attributed_to": [], "claim_status": "fact", "source_status": "fact",
           "evidence": [{"source": "synthetic.txt", "chunk": "c001", "quote": "Synthetic."}],
           "reason": "Synthetic transport format only; no scientific validation."}]}
    raw = canonical_bytes(row)
    files = {name: work / f"{name}.json" for name in ("full", "ranged")}
    for path in files.values():
        path.write_bytes(raw)
    descriptors = {str(path): {"path": str(path), "sha256": hashlib.sha256(raw).hexdigest(),
                   "bytes": len(raw), "row_sha256": object_sha256(row)} for path in files.values()}
    policy = {"version": 1, "pretool_control": CONTRACT, "python": sys.executable,
              "programs": [], "manifest_paths": [], "allowed_tools": ["Read"],
              "batch_row_views": descriptors,
              "readonly_lookups": {"repository": str(work), "inputs": list(descriptors), "output_directories": []}}
    # Deliberately isolate real row-evidence methods from unexercised sealing and
    # source-validation machinery; no synthetic tool result enters these methods.
    history = BatchHistory.__new__(BatchHistory)
    history.integration = True;history.files = FileAccess(policy, config)
    history.policy = policy;history.row_reads = [];history.line = 0
    calls, observations, errors, terminals = {}, [], [], []
    script = [
        ("offline_full", {"file_path": str(files["full"])}),
        ("offline_range_first", {"file_path": str(files["ranged"]), "offset": 1, "limit": 1}),
        ("offline_range_last", {"file_path": str(files["ranged"]), "offset": 2, "limit": 1})]
    upstream_calls = 0

    def respond(request):
        nonlocal upstream_calls
        upstream_calls += 1
        if upstream_calls > 12:
            raise RuntimeError("synthetic upstream request bound")
        body = json.loads(request.content)
        seen = {block.get("tool_use_id") for message in body.get("messages", [])
                if isinstance(message.get("content"), list) for block in message["content"]
                if isinstance(block, dict) and block.get("type") == "tool_result"}
        next_step = next(((identity, payload) for identity, payload in script if identity not in seen), None)
        block = ({"type": "tool_use", "id": next_step[0], "name": "Read", "input": next_step[1]}
                 if body.get("tools") and next_step else {"type": "text", "text": "OFFLINE_READ_FORMAT_COMPLETE"})
        return stream_response(body, block, upstream_calls)

    def observe(event):
        history.line += 1
        for block in _blocks(event):
            if block.get("type") == "tool_use":
                calls[block["id"]] = (history.line, block)
            elif block.get("type") == "tool_result":
                identity = block.get("tool_use_id")
                if identity not in calls:
                    errors.append({"tool": identity, "error": "observed result lacks prior call"});continue
                start, call = calls[identity]
                before = len(history.row_reads)
                failure = None
                try:
                    history._read_row(call, event, block, start)
                except (BudgetStop, ValueError, TypeError, KeyError) as error:
                    failure = f"{type(error).__name__}: {error}"
                    errors.append({"tool": identity, "error": failure})
                metadata = event.get("tool_use_result")
                file = metadata.get("file", {}) if isinstance(metadata, dict) else {}
                try:
                    history._required_row_reads();complete = True
                except BudgetStop:
                    complete = False
                observations.append({"tool": identity, "accepted": len(history.row_reads) == before + 1,
                    "error": failure, "metadata_type": metadata.get("type") if isinstance(metadata, dict) else None,
                    "file_keys": sorted(file) if isinstance(file, dict) else None,
                    "start_line": file.get("startLine"), "num_lines": file.get("numLines"),
                    "total_lines": file.get("totalLines"), "block_is_error": block.get("is_error"),
                    "all_rows_complete_after_read": complete,
                    "block_content_type": type(block.get("content")).__name__,
                    "block_content_bytes": len(block["content"].encode()) if isinstance(block.get("content"), str) else None})
        if event.get("type") == "result":
            terminals.append({key: event.get(key) for key in ("is_error", "terminal_reason", "stop_reason", "num_turns")})

    sdk = SimpleNamespace(messages=SimpleNamespace(count_tokens=lambda **kw: SimpleNamespace(input_tokens=100)))
    ledger = Ledger(root / "synthetic-ledger.json", manifest_sha256="offline-row-format-probe")
    prices = {"input": .000005, "output": .000025, "cache_read": .0000005, "cache_write": .00000625}
    proxy = NativeProxy(sdk=sdk, ledger=ledger, attempt="synthetic", evidence=root / "synthetic-requests",
        model="claude-opus-5", prices=prices, verify=lambda: None, provider_key="offline-fake-provider-key",
        base_url="https://api.cborg.lbl.gov", upstream=httpx.Client(transport=httpx.MockTransport(respond)))
    env = {key: value for key, value in os.environ.items()
           if key in {"PATH", "HOME", "SHELL", "TMPDIR", "LANG", "LC_ALL", "TERM"}}
    env.update(CLAUDE_CONFIG_DIR=str(config), DISABLE_NON_ESSENTIAL_MODEL_CALLS="1", DISABLE_TELEMETRY="1",
               CLAUDE_CODE_DISABLE_EXPERIMENTAL_BETAS="1", ANTHROPIC_API_KEY=proxy.token)
    instruction = root / "instruction.txt"
    instruction.write_text("Perform only the scripted synthetic row Reads and finish.\n")
    status, failure = None, None
    try:
        with proxy.running() as url:
            env["ANTHROPIC_BASE_URL"] = url
            argv = [str(cli), "--print", "--safe-mode", "--restricted", "--strict-mcp-config",
                    "--no-session-persistence", "--model", "claude-opus-5", "--name", "d4d-offline-row-read",
                    "--disable-slash-commands", "--max-budget-usd", "5", "--prompt-suggestions", "false",
                    "--output-format", "stream-json", "--input-format", "stream-json", "--verbose",
                    "--permission-mode", "dontAsk", "--tools", "Read", "--allowedTools", "Read",
                    "--system-prompt", "Synthetic offline row-format probe. Only Read the exact scripted synthetic files and finish."]
            status = execute_child(argv, proxy=proxy, instruction=instruction, attempt=root, cwd=work, env=env,
                deadline_seconds=180, verify_launch=lambda: verified_executable(overlay),
                command_policy=policy, event_observer=observe)
    except Exception as error:
        failure = f"{type(error).__name__}: {error}"
    coverage = False
    try:
        history._required_row_reads();coverage = True
    except BudgetStop as error:
        errors.append({"coverage": str(error)})
    requests = json.loads(ledger.path.read_bytes())["requests"] if ledger.path.exists() else []
    report = {"kind": "native_batch_read_format_probe_v1", "synthetic_only": True,
        "synthetic_row_text_characters": row_text_size, "canonical_row_bytes": len(raw),
        "native_executable_sha256": overlay["pinned_files"][str(cli)], "requested_cli_version": "2.1.272",
        "implementation_sha256": {name: sha(BASE / name) for name in
            ("audit_controls/probe_batch_read.py", "audit_controls/batch_history.py",
             "native_controls/native_file_policy.py", "native_controls/native_control.py",
             "native_controls/run_native_canary.py", "native_controls/native_proxy.py")},
        "exit_code": status, "controller_failure": failure, "proxy_failure": proxy.failure,
        "scripted_upstream_calls": upstream_calls, "real_provider_requests": 0,
        "synthetic_ledger_rows": len(requests), "unsettled_rows": sum(r["status"] != "settled" for r in requests),
        "row_reads": observations, "required_row_reads_passed": coverage, "errors": errors,
        "terminal_results": terminals, "unfinished_handlers": proxy.unfinished_handlers,
        "passed": status == 0 and failure is None and proxy.failure is None and not errors and coverage
                  and len(observations) == 3 and bool(terminals) and terminals[-1]["is_error"] is False
                  and [r["all_rows_complete_after_read"] for r in observations] == [False, False, True]}
    (root / "metadata-report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"report_path": str(root / "metadata-report.json"), **report}, indent=2))
    return int(not report["passed"])


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--executable", type=Path,
                        default=Path.home() / ".local/share/claude/versions/2.1.272")
    parser.add_argument("--row-text-size", type=int, default=26)
    args = parser.parse_args()
    raise SystemExit(run(args.executable, args.row_text_size))
