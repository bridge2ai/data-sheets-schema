#!/usr/bin/env python3
"""Inspect only rollout identity structure for issue 6346, 2026-11-25.

Inputs: explicitly named local JSONL rollouts, never authentication files.
Output: metadata and turn/event key shapes; no messages, prompts or tool output.
"""
import argparse
import hashlib
import json
from pathlib import Path


def inspect(path):
    raw = path.read_bytes()
    all_rows = [json.loads(line) for line in raw.splitlines()]
    boundary = all_rows[0].get("payload", {}).get("subagent_history_start_ordinal")
    boundary_rows = []
    if isinstance(boundary, int):
        for offset in range(max(0, boundary - 4), min(len(all_rows), boundary + 10)):
            row = all_rows[offset]
            payload = row.get("payload", {})
            boundary_rows.append({"zero_based_ordinal": offset, "line": offset + 1,
                                  "type": row.get("type"), "payload_type": payload.get("type"),
                                  "role": payload.get("role"), "turn_id": payload.get("turn_id"),
                                  "payload_keys": sorted(payload)})
    output = []
    for index, line in enumerate(raw.splitlines(), 1):
        row = json.loads(line)
        payload = row.get("payload", {})
        if not isinstance(payload, dict):
            continue
        kind = row.get("type")
        item = {"line": index, "timestamp": row.get("timestamp"), "type": kind,
                "payload_keys": sorted(payload)}
        if kind == "session_meta":
            item["identity"] = {key: payload[key] for key in (
                "id", "parent_thread_id", "agent_path", "timestamp", "cwd", "cli_version",
                "subagent_history_start_ordinal", "history_mode", "forked_from_id")
                                if key in payload}
            source = payload.get("source")
            item["source"] = source if isinstance(source, (str, dict)) else None
        elif kind == "turn_context":
            item["identity"] = {key: payload[key] for key in (
                "turn_id", "thread_id", "session_id", "root_turn_id", "model", "effort", "cwd") if key in payload}
        elif kind == "event_msg" and payload.get("type") in (
                "task_started", "task_complete", "turn_started", "turn_complete",
                "turn_aborted", "model_reroute", "model_changed", "thread_settings_applied"):
            item["identity"] = {key: payload[key] for key in (
                "type", "turn_id", "thread_id", "session_id", "root_turn_id", "model", "effort") if key in payload}
            attribution = payload.get("turn_attribution")
            if isinstance(attribution, dict):
                item["attribution_keys"] = sorted(attribution)
                item["attribution"] = {key: attribution[key] for key in (
                    "initiating_agent_path", "parent_turn_id", "root_turn_id", "turn_id", "turn_trigger")
                                       if key in attribution}
            settings = payload.get("thread_settings")
            if isinstance(settings, dict):
                item["settings_keys"] = sorted(settings)
                item["settings_identity"] = {key: settings[key] for key in (
                    "model", "effort", "reasoning_effort", "model_reasoning_effort", "cwd") if key in settings}
        elif kind == "response_item" and payload.get("type") == "message" and payload.get("model"):
            item["identity"] = {key: payload[key] for key in (
                "type", "role", "turn_id", "thread_id", "session_id", "model") if key in payload}
        else:
            continue
        output.append(item)
    return {"path": str(path), "sha256": hashlib.sha256(raw).hexdigest(),
            "boundary_rows": boundary_rows, "rows": output}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--log", type=Path, action="append", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    with args.output.open("x") as handle:
        json.dump({"logs": [inspect(path) for path in args.log]}, handle, indent=2, sort_keys=True)
        handle.write("\n")
    print(args.output)


if __name__ == "__main__":
    main()
