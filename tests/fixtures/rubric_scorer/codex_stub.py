# Offline Codex stand-in for issue 6315, 2026-11-25.
# Inputs: sibling case.json and runner stdin/argv. Outputs: synthetic rollout,
# raw evaluation, and invocation evidence. Never imports or calls a model client.
import datetime
import json
import os
from pathlib import Path
import stat
import sys
import time


def main():
    if sys.argv[1:] == ["--version"]:
        print("codex-cli synthetic-v2-owned-turn-test")
        return 0
    directory = Path(__file__).parent
    case = json.loads((directory / "case.json").read_text())
    prompt = sys.stdin.read()
    (directory / "received-prompt.txt").write_text(prompt)
    (directory / "invocation.json").write_text(json.dumps({
        "argv": sys.argv[1:], "cwd": os.getcwd(),
        "pid": os.getpid(), "pgid": os.getpgrp(),
        "working_files": sorted(p.name for p in Path.cwd().iterdir()),
        "codex_home": os.environ.get("CODEX_HOME"),
        "home": os.environ.get("HOME"),
        "copied_auth_present": (Path(os.environ["CODEX_HOME"]) / "auth.json").is_file(),
        "copied_auth_mode": stat.S_IMODE((Path(os.environ["CODEX_HOME"]) / "auth.json").stat().st_mode),
    }, indent=2))
    if case.get("sleep_seconds"):
        time.sleep(case["sleep_seconds"])
    output_option = "-o" if "-o" in sys.argv else "--output-last-message"
    raw_path = Path(sys.argv[sys.argv.index(output_option) + 1])
    raw_path.write_text(json.dumps(case["evaluation"]))
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    cwd = os.getcwd()
    thread = "stub-thread"
    root_turn = "stub-root-turn"
    entries = [
        {"timestamp": now, "type": "session_meta", "payload": {
            "id": thread, "cwd": cwd, "source": "exec", "originator": "codex_exec",
            "cli_version": "synthetic-v2-owned-turn-test",
        }},
        {"timestamp": now, "type": "event_msg", "payload": {
            "type": "task_started", "turn_id": root_turn, "root_turn_id": root_turn,
        }},
        {"timestamp": now, "type": "turn_context", "payload": {
            "cwd": cwd, "model": case.get("model", "gpt-6-astra"),
            "effort": case.get("effort", "ultra"), "turn_id": root_turn,
            "root_turn_id": root_turn,
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
    if case.get("root_assistant_model"):
        entries.append({"timestamp": now, "type": "response_item", "payload": {
            "type": "message", "role": "assistant", "model": case["root_assistant_model"], "content": [],
        }})
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
    if case.get("orphan_output") == "root":
        entries.append({"timestamp": now, "type": "response_item", "payload": {
            "type": "function_call_output", "call_id": "orphan-root-result", "output": "synthetic",
        }})
    if case.get("missing_spawn_output"):
        entries = [row for row in entries if row.get("payload", {}).get("type") != "function_call_output"]
    moved_output = None
    if case.get("move_spawn_output_to_child"):
        moved_output = next(row for row in entries if row.get("payload", {}).get("type") == "function_call_output")
        entries.remove(moved_output)
    if not case.get("missing_log"):
        sessions = Path(os.environ["CODEX_HOME"]) / "sessions"
        sessions.mkdir(parents=True, exist_ok=True)
        (sessions / "rollout-stub.jsonl").write_text(
            "".join(json.dumps(entry) + "\n" for entry in entries))
        if case.get("child"):
            parent = case.get("child_parent", thread)
            inherited = entries[:3]
            child_turn = "stub-child-turn"
            child = [
                {"timestamp": now, "type": "session_meta", "payload": {
                    "id": child_id, "parent_thread_id": parent, "cwd": cwd,
                    "agent_path": child_path,
                    "subagent_history_start_ordinal": len(inherited) + 1,
                    "source": {"subagent": {"thread_spawn": {
                        "parent_thread_id": parent, "agent_path": child_path}}},
                    "cli_version": "synthetic-v2-owned-turn-test",
                }},
                # Real delegated rollouts can retain parent metadata and turns.
                *inherited,
                {"timestamp": now, "type": "event_msg", "payload": {
                    "type": "thread_settings_applied", "thread_id": child_id,
                    "thread_settings": {"model": "gpt-6-astra", "reasoning_effort": "ultra", "cwd": cwd},
                }},
                {"timestamp": now, "type": "event_msg", "payload": {
                    "type": "task_started", "turn_id": child_turn, "root_turn_id": root_turn,
                }},
                {"timestamp": now, "type": "turn_context", "payload": {
                    "cwd": case.get("child_cwd", cwd), "model": case.get("child_model", "gpt-6-astra"),
                    "effort": case.get("child_effort", "ultra"),
                    "turn_id": case.get("child_turn", child_turn), "root_turn_id": root_turn,
                }},
            ]
            if case.get("child_inherited_only"):
                child.pop()
            if case.get("child_boundary_missing"):
                child[0]["payload"].pop("subagent_history_start_ordinal")
            if case.get("child_marker_missing"):
                child[len(inherited) + 1]["payload"]["type"] = "unrecognized_settings_event"
            if "child_boundary" in case:
                child[0]["payload"]["subagent_history_start_ordinal"] = case["child_boundary"]
            if case.get("child_settings_thread"):
                child[len(inherited) + 1]["payload"]["thread_id"] = case["child_settings_thread"]
            if case.get("child_assistant_model"):
                child.append({"timestamp": now, "type": "response_item", "payload": {
                    "type": "message", "role": "assistant", "model": case["child_assistant_model"], "content": [],
                }})
            if case.get("orphan_output") == "child":
                child.append({"timestamp": now, "type": "response_item", "payload": {
                    "type": "function_call_output", "call_id": "orphan-child-result", "output": "synthetic",
                }})
            if case.get("child_custom_tool"):
                child.append({"timestamp": now, "type": "response_item", "payload": {
                    "type": "custom_tool_call", "name": "unrecognized_external_tool",
                    "call_id": "outside-child", "input": "synthetic",
                }})
            if case.get("inherited_orphan_output"):
                boundary = child[0]["payload"]["subagent_history_start_ordinal"]
                child.insert(boundary, {"timestamp": now, "type": "response_item", "payload": {
                    "type": "function_call_output", "call_id": "unpaired-inherited-result", "output": "synthetic",
                }})
                child[0]["payload"]["subagent_history_start_ordinal"] += 1
            if moved_output is not None:
                child.append(moved_output)
            (sessions / "rollout-child.jsonl").write_text(
                "".join(json.dumps(entry) + "\n" for entry in child))
    print(json.dumps({"type": "thread.started", "thread_id": case.get("thread", thread)}))
    return case.get("exit", 0)


if __name__ == "__main__":
    raise SystemExit(main())
