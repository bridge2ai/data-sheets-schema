# Offline Codex stand-in for issue 6315, 2026-11-25.
# Inputs: sibling case.json and runner stdin/argv. Outputs: synthetic rollout,
# raw evaluation, and invocation evidence. Never imports or calls a model client.
import datetime
import json
import os
from pathlib import Path
import sys


def main():
    if sys.argv[1:] == ["--version"]:
        print("codex-cli 0.170.0-offline-test")
        return 0
    directory = Path(__file__).parent
    case = json.loads((directory / "case.json").read_text())
    prompt = sys.stdin.read()
    (directory / "received-prompt.txt").write_text(prompt)
    (directory / "invocation.json").write_text(json.dumps({
        "argv": sys.argv[1:], "cwd": os.getcwd(),
        "working_files": sorted(p.name for p in Path.cwd().iterdir()),
        "codex_home": os.environ.get("CODEX_HOME"),
        "home": os.environ.get("HOME"),
    }, indent=2))
    output_option = "-o" if "-o" in sys.argv else "--output-last-message"
    raw_path = Path(sys.argv[sys.argv.index(output_option) + 1])
    raw_path.write_text(json.dumps(case["evaluation"]))
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    cwd = os.getcwd()
    thread = "stub-thread"
    entries = [
        {"timestamp": now, "type": "session_meta", "payload": {
            "id": thread, "cwd": cwd, "source": "exec", "originator": "codex_exec",
            "cli_version": "0.170.0-offline-test",
        }},
        {"timestamp": now, "type": "turn_context", "payload": {
            "cwd": cwd, "model": case.get("model", "gpt-6-astra"),
            "effort": case.get("effort", "ultra"),
        }},
    ]
    if case.get("missing_context"):
        entries.pop()
    if case.get("external_tool"):
        entries.append({"timestamp": now, "type": "response_item", "payload": {
            "type": "function_call", "name": "exec_command", "arguments": "{}",
        }})
    if case.get("wrong_cwd"):
        entries[0]["payload"]["cwd"] = str(directory)
    child_id = "00000000-0000-4000-8000-000000000001"
    child_path = "/root/score_check"
    if case.get("child") or case.get("missing_child_log"):
        entries.extend([
            {"timestamp": now, "type": "response_item", "payload": {
                "type": "function_call", "call_id": "spawn-fixture-1", "name": "spawn_agent",
                "arguments": json.dumps({"task_name": "score_check", "message": "Review this same isolated record."}),
            }},
            {"timestamp": now, "type": "response_item", "payload": {
                "type": "function_call_output", "call_id": "spawn-fixture-1",
                "output": json.dumps({"task_name": child_path}),
            }},
        ])
    if not case.get("missing_log"):
        sessions = Path(os.environ["CODEX_HOME"]) / "sessions"
        sessions.mkdir(parents=True, exist_ok=True)
        (sessions / "rollout-stub.jsonl").write_text(
            "".join(json.dumps(entry) + "\n" for entry in entries))
        if case.get("child"):
            parent = case.get("child_parent", thread)
            child = [
                {"timestamp": now, "type": "session_meta", "payload": {
                    "id": child_id, "parent_thread_id": parent, "cwd": cwd,
                    "agent_path": child_path,
                    "source": {"subagent": {"thread_spawn": {
                        "parent_thread_id": parent, "agent_path": child_path}}},
                    "cli_version": "0.170.0-offline-test",
                }},
                # Real delegated rollouts can retain parent metadata and turns.
                *entries[:2],
                {"timestamp": now, "type": "turn_context", "payload": {
                    "cwd": cwd, "model": case.get("child_model", "gpt-6-astra"),
                    "effort": "ultra",
                }},
            ]
            (sessions / "rollout-child.jsonl").write_text(
                "".join(json.dumps(entry) + "\n" for entry in child))
    print(json.dumps({"type": "thread.started", "thread_id": case.get("thread", thread)}))
    return case.get("exit", 0)


if __name__ == "__main__":
    raise SystemExit(main())
